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