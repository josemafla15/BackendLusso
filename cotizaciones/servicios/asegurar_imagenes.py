import os
import tempfile

from .rasterizar_texto import capturar_selector, generar_png_transparente
from ..storage import subir_a_supabase


def asegurar_imagenes_viajesonado(cotizacion, page=None):
    """
    Si se pasa `page`, NO guarda en la base (el navegador sigue abierto
    -- guardar acá dentro rompe con SynchronousOnlyOperation). En ese
    caso, solo actualiza los campos en memoria; quien llama es
    responsable de hacer cotizacion.save() después de cerrar Playwright.
    Si no se pasa `page` (uso standalone), guarda normal como siempre.
    """
    pares = [
        ("viaje_sonado_intro_texto", "viaje_sonado_intro_imagen", ".v-intro"),
        ("viaje_sonado_texto1", "viaje_sonado_texto1_imagen", ".v-block .v-text"),
    ]

    cambios = False
    for campo_texto, campo_imagen, selector in pares:
        texto = getattr(cotizacion, campo_texto)
        if not texto:
            continue

        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, f"{campo_imagen}.png")
            if page is not None:
                capturar_selector(page, selector, output_path)
            else:
                generar_png_transparente(cotizacion.id, selector, output_path)
            url_publica = subir_a_supabase(output_path, f"cotizaciones/{cotizacion.id}/{campo_imagen}.png")
            setattr(cotizacion, campo_imagen, url_publica)
            cambios = True

    if cambios and page is None:
        cotizacion.save(update_fields=["viaje_sonado_intro_imagen", "viaje_sonado_texto1_imagen"])


def asegurar_imagenes_despertar_bienvenidos(cotizacion, page=None):
    """Mismo criterio que asegurar_imagenes_viajesonado -- ver docstring de arriba."""
    pares = [
        ("descripcion_destino", "descripcion_destino_imagen", ".d-body-captura"),
        ("bienvenida_descripcion", "bienvenida_descripcion_imagen", ".b-body-captura"),
    ]

    cambios = False
    for campo_texto, campo_imagen, selector in pares:
        texto = getattr(cotizacion, campo_texto)
        if not texto:
            continue

        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, f"{campo_imagen}.png")
            if page is not None:
                capturar_selector(page, selector, output_path)
            else:
                generar_png_transparente(cotizacion.id, selector, output_path)
            url_publica = subir_a_supabase(output_path, f"cotizaciones/{cotizacion.id}/{campo_imagen}.png")
            setattr(cotizacion, campo_imagen, url_publica)
            cambios = True

    if cambios and page is None:
        cotizacion.save(update_fields=["descripcion_destino_imagen", "bienvenida_descripcion_imagen"])


def asegurar_imagenes_portada_buenviaje(cotizacion, page=None):
    """Mismo criterio que asegurar_imagenes_viajesonado -- ver docstring de arriba."""
    cambios = []

    if cotizacion.fecha_inicio and cotizacion.fecha_fin:
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "fecha_viaje_imagen.png")
            if page is not None:
                capturar_selector(page, ".captura-fecha", output_path)
            else:
                generar_png_transparente(cotizacion.id, ".captura-fecha", output_path)
            url_publica = subir_a_supabase(output_path, f"cotizaciones/{cotizacion.id}/fecha_viaje_imagen.png")
            cotizacion.fecha_viaje_imagen = url_publica
            cambios.append("fecha_viaje_imagen")

    nombre_para_imagen = cotizacion.nombre_cliente or (cotizacion.lead.nombre if cotizacion.lead else "")
    if nombre_para_imagen:
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "lead_nombre_imagen.png")
            if page is not None:
                capturar_selector(page, ".captura-nombre", output_path)
            else:
                generar_png_transparente(cotizacion.id, ".captura-nombre", output_path)
            url_publica = subir_a_supabase(output_path, f"cotizaciones/{cotizacion.id}/lead_nombre_imagen.png")
            cotizacion.lead_nombre_imagen = url_publica
            cambios.append("lead_nombre_imagen")

    if cotizacion.destino:
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "destino_portada_imagen.png")
            if page is not None:
                capturar_selector(page, ".captura-destino-portada", output_path)
            else:
                generar_png_transparente(cotizacion.id, ".captura-destino-portada", output_path)
            url_publica = subir_a_supabase(output_path, f"cotizaciones/{cotizacion.id}/destino_portada_imagen.png")
            cotizacion.destino_portada_imagen = url_publica
            cambios.append("destino_portada_imagen")

        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "destino_buenviaje_imagen.png")
            if page is not None:
                capturar_selector(page, ".captura-destino-buenviaje", output_path)
            else:
                generar_png_transparente(cotizacion.id, ".captura-destino-buenviaje", output_path)
            url_publica = subir_a_supabase(output_path, f"cotizaciones/{cotizacion.id}/destino_buenviaje_imagen.png")
            cotizacion.destino_buenviaje_imagen = url_publica
            cambios.append("destino_buenviaje_imagen")

    if cambios and page is None:
        cotizacion.save(update_fields=cambios)