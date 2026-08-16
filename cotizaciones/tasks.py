import logging
import os
import tempfile

from celery import shared_task
from django.utils.text import slugify

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def generar_pdf_cotizacion_task(self, cotizacion_id, nombre_archivo):
    """
    Genera el PDF final de una cotización (14 páginas, Playwright) y lo
    sube a Supabase Storage, en el mismo bucket que las imágenes
    (lusso-cotizaciones), bajo pdfs/<cotizacion_id>/<nombre_archivo>.pdf

    Antes de renderizar, se asegura de que los párrafos ligados al
    destino (despertar, bienvenidos, viaje soñado) ya tengan su imagen
    transparente generada -- si el texto cambió desde la última vez,
    se regenera acá mismo.
    """
    from playwright.sync_api import sync_playwright

    from .models import Cotizacion
    from .servicios.asegurar_imagenes import (
        asegurar_imagenes_despertar_bienvenidos,
        asegurar_imagenes_viajesonado,
    )
    from .storage import subir_a_supabase

    try:
        cotizacion = Cotizacion.objects.get(id=cotizacion_id)

        asegurar_imagenes_viajesonado(cotizacion)
        asegurar_imagenes_despertar_bienvenidos(cotizacion)

        base_url = os.environ.get("SITE_URL", "http://127.0.0.1:8000")
        url = f"{base_url}/cotizaciones/preview/{cotizacion_id}/completa/"

        nombre_limpio = slugify(nombre_archivo.rsplit(".pdf", 1)[0]) or str(cotizacion_id)
        remote_path = f"pdfs/{cotizacion_id}/{nombre_limpio}.pdf"

        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, f"{nombre_limpio}.pdf")

            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": 1920, "height": 1080})
                page.goto(url, wait_until="networkidle")
                page.pdf(
                    path=output_path,
                    width="20in",
                    height="11.25in",
                    print_background=True,
                    margin={"top": "0px", "bottom": "0px", "left": "0px", "right": "0px"},
                )
                browser.close()

            url_publica = subir_a_supabase(output_path, remote_path)

        cotizacion.pdf_url = url_publica
        cotizacion.estado = Cotizacion.Estado.GENERADA
        cotizacion.save(update_fields=["pdf_url", "estado"])

    except Exception as exc:
        logger.exception("Error generando PDF para cotización %s", cotizacion_id)
        raise self.retry(exc=exc)