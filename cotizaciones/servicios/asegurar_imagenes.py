import os
import tempfile

from .rasterizar_texto import generar_png_transparente
from ..storage import subir_a_supabase


def asegurar_imagenes_viajesonado(cotizacion):
    """
    Llamar ANTES de renderizar cotizacion_completa.html / generar el PDF.
    Si el texto está presente pero la imagen no (o quedó vieja), la
    regenera. Si el texto está vacío, no genera nada (deja el campo
    imagen vacío -- el template simplemente no mostrará esa imagen).
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
            generar_png_transparente(cotizacion.id, selector, output_path)
            url_publica = subir_a_supabase(output_path, f"cotizaciones/{cotizacion.id}/{campo_imagen}.png")
            setattr(cotizacion, campo_imagen, url_publica)
            cambios = True

    if cambios:
        cotizacion.save(update_fields=["viaje_sonado_intro_imagen", "viaje_sonado_texto1_imagen"])


def asegurar_imagenes_despertar_bienvenidos(cotizacion):
    """
    Igual que asegurar_imagenes_viajesonado, pero para los párrafos de
    'Imagina despertar aquí' y 'Bienvenidos a [destino]'.
    """
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
            generar_png_transparente(cotizacion.id, selector, output_path)
            url_publica = subir_a_supabase(output_path, f"cotizaciones/{cotizacion.id}/{campo_imagen}.png")
            setattr(cotizacion, campo_imagen, url_publica)
            cambios = True

    if cambios:
        cotizacion.save(update_fields=["descripcion_destino_imagen", "bienvenida_descripcion_imagen"])

def asegurar_imagenes_portada_buenviaje(cotizacion):
    """
    Genera las imágenes de fecha/nombre/destino usadas en portada y
    buenviaje. Fecha y nombre se comparten entre las 2 páginas (mismo
    estilo); destino tiene una versión por página (itálica en portada,
    normal en buenviaje).
    """
    cambios = []

    if cotizacion.fecha_inicio and cotizacion.fecha_fin:
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "fecha_viaje_imagen.png")
            generar_png_transparente(cotizacion.id, ".captura-fecha", output_path)
            url_publica = subir_a_supabase(output_path, f"cotizaciones/{cotizacion.id}/fecha_viaje_imagen.png")
            cotizacion.fecha_viaje_imagen = url_publica
            cambios.append("fecha_viaje_imagen")

    if cotizacion.lead_id and cotizacion.lead.nombre:
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "lead_nombre_imagen.png")
            generar_png_transparente(cotizacion.id, ".captura-nombre", output_path)
            url_publica = subir_a_supabase(output_path, f"cotizaciones/{cotizacion.id}/lead_nombre_imagen.png")
            cotizacion.lead_nombre_imagen = url_publica
            cambios.append("lead_nombre_imagen")

    if cotizacion.destino:
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "destino_portada_imagen.png")
            generar_png_transparente(cotizacion.id, ".captura-destino-portada", output_path)
            url_publica = subir_a_supabase(output_path, f"cotizaciones/{cotizacion.id}/destino_portada_imagen.png")
            cotizacion.destino_portada_imagen = url_publica
            cambios.append("destino_portada_imagen")

        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "destino_buenviaje_imagen.png")
            generar_png_transparente(cotizacion.id, ".captura-destino-buenviaje", output_path)
            url_publica = subir_a_supabase(output_path, f"cotizaciones/{cotizacion.id}/destino_buenviaje_imagen.png")
            cotizacion.destino_buenviaje_imagen = url_publica
            cambios.append("destino_buenviaje_imagen")

    if cambios:
        cotizacion.save(update_fields=cambios)