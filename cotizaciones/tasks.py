import logging
import os
import tempfile
import time

from celery import shared_task
from django.utils.text import slugify

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def generar_pdf_cotizacion_task(self, cotizacion_id, nombre_archivo):
    from playwright.sync_api import sync_playwright

    from .models import Cotizacion
    from .servicios.asegurar_imagenes import (
        asegurar_imagenes_despertar_bienvenidos,
        asegurar_imagenes_portada_buenviaje,
        asegurar_imagenes_viajesonado,
    )
    from .servicios.rasterizar_texto import abrir_pagina_captura
    from .storage import subir_a_supabase

    inicio = time.time()

    try:
        cotizacion = Cotizacion.objects.get(id=cotizacion_id)

        # Un solo navegador, una sola navegación, para TODAS las capturas
        # de texto (antes: hasta 8 navegadores separados).
        t0 = time.time()
        playwright_ctx, browser, page = abrir_pagina_captura(cotizacion.id)
        try:
            asegurar_imagenes_viajesonado(cotizacion, page=page)
            asegurar_imagenes_despertar_bienvenidos(cotizacion, page=page)
            asegurar_imagenes_portada_buenviaje(cotizacion, page=page)
        finally:
            browser.close()
            playwright_ctx.stop()

        # El save() de todos los campos de imagen recién ahora, con
        # Playwright ya completamente cerrado -- guardar mientras el
        # navegador seguía abierto en el mismo hilo causaba
        # SynchronousOnlyOperation (Django detecta un event loop async
        # activo y bloquea el acceso sincrónico a la base de datos).
        cotizacion.save()
        logger.info("Capturas de texto: %.1fs", time.time() - t0)

        base_url = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")
        url = f"{base_url}/cotizaciones/preview/{cotizacion_id}/completa/"

        nombre_limpio = slugify(nombre_archivo.rsplit(".pdf", 1)[0]) or str(cotizacion_id)
        remote_path = f"pdfs/{cotizacion_id}/{nombre_limpio}.pdf"

        t1 = time.time()
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, f"{nombre_limpio}.pdf")

            with sync_playwright() as p:
                browser2 = p.chromium.launch()
                page2 = browser2.new_page(viewport={"width": 1920, "height": 1080})
                page2.goto(url, wait_until="networkidle", timeout=60000)
                page2.pdf(
                    path=output_path,
                    width="20in",
                    height="11.25in",
                    print_background=True,
                    margin={"top": "0px", "bottom": "0px", "left": "0px", "right": "0px"},
                )
                browser2.close()

            url_publica = subir_a_supabase(output_path, remote_path)
        logger.info("PDF final: %.1fs", time.time() - t1)

        cotizacion.pdf_url = url_publica
        cotizacion.estado = Cotizacion.Estado.GENERADA
        cotizacion.save(update_fields=["pdf_url", "estado"])

        logger.info("TOTAL generación PDF %s: %.1fs", cotizacion_id, time.time() - inicio)

    except Exception as exc:
        logger.exception("Error generando PDF para cotización %s", cotizacion_id)
        raise self.retry(exc=exc)