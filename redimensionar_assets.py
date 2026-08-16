import os
from PIL import Image

CARPETA = r"cotizaciones\static\cotizaciones\assets"
MAX_LADO = 1200  # px -- de sobra para cualquier logo/decorativo del diseño

for nombre in os.listdir(CARPETA):
    if not nombre.lower().endswith((".png", ".jpg", ".jpeg")):
        continue

    ruta = os.path.join(CARPETA, nombre)
    img = Image.open(ruta)
    ancho, alto = img.size
    lado_mayor = max(ancho, alto)

    if lado_mayor <= MAX_LADO:
        print(f"OK, ya está bien: {nombre} ({ancho}x{alto})")
        continue

    factor = MAX_LADO / lado_mayor
    nuevo_tamano = (int(ancho * factor), int(alto * factor))

    # Preserva transparencia si la imagen la tiene (logos/decorativos con
    # fondo transparente), en vez de forzar todo a RGB/JPEG.
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        img_redim = img.convert("RGBA").resize(nuevo_tamano, Image.LANCZOS)
        img_redim.save(ruta, format="PNG", optimize=True)
    else:
        img_redim = img.convert("RGB").resize(nuevo_tamano, Image.LANCZOS)
        img_redim.save(ruta, format="PNG", optimize=True)

    print(f"Redimensionado: {nombre} de {ancho}x{alto} -> {nuevo_tamano[0]}x{nuevo_tamano[1]}")