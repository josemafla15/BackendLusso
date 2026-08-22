import mimetypes
import os
import tempfile
import uuid

import requests
from django.conf import settings
from PIL import Image

MAX_LADO = 1600  # px -- suficiente para las cajas más grandes del diseño (~900px), con margen


def _comprimir_antes_de_subir(local_path):
    """
    Si la imagen excede MAX_LADO en su lado más largo, crea una COPIA
    comprimida en un archivo temporal y devuelve esa ruta nueva -- el
    archivo original en local_path NUNCA se modifica ni se sobreescribe.
    """
    img = Image.open(local_path)
    ancho, alto = img.size
    lado_mayor = max(ancho, alto)

    if lado_mayor <= MAX_LADO:
        return local_path  # ya está en un tamaño razonable, se usa tal cual

    factor = MAX_LADO / lado_mayor
    nuevo_tamano = (int(ancho * factor), int(alto * factor))
    img_redimensionada = img.convert("RGB").resize(nuevo_tamano, Image.LANCZOS)

    fd, ruta_temporal = tempfile.mkstemp(suffix=".jpg")
    os.close(fd)
    img_redimensionada.save(ruta_temporal, format="JPEG", quality=85)
    return ruta_temporal

def subir_a_supabase(local_path, remote_path):
    """
    Sube un archivo local a Supabase Storage (bucket público) y devuelve
    la URL pública resultante. Si la imagen es muy grande, se comprime
    en una COPIA temporal antes de subir -- el archivo original que le
    pasaste en local_path nunca se toca.
    """
    ruta_a_subir = local_path
    es_copia_temporal = False

    if local_path.lower().endswith((".jpg", ".jpeg", ".png")):
        ruta_comprimida = _comprimir_antes_de_subir(local_path)
        if ruta_comprimida != local_path:
            ruta_a_subir = ruta_comprimida
            es_copia_temporal = True

    content_type = mimetypes.guess_type(ruta_a_subir)[0] or "application/octet-stream"

    upload_url = (
        f"{settings.SUPABASE_URL}/storage/v1/object/"
        f"{settings.SUPABASE_BUCKET}/{remote_path}"
    )

    try:
        with open(ruta_a_subir, "rb") as f:
            response = requests.post(
                upload_url,
                data=f,
                headers={
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                    "apikey": settings.SUPABASE_SERVICE_KEY,
                    "Content-Type": content_type,
                    "x-upsert": "true",
                },
                timeout=30,
            )
        response.raise_for_status()
    finally:
        if es_copia_temporal:
            os.remove(ruta_a_subir)

    return (
        f"{settings.SUPABASE_URL}/storage/v1/object/public/"
        f"{settings.SUPABASE_BUCKET}/{remote_path}"
    )

def subir_archivo_temporal(uploaded_file, carpeta="uploads"):
    """
    Recibe un archivo subido vía API (request.FILES) y lo sube a Supabase
    Storage, devolviendo la URL pública. Usado por el endpoint genérico
    de subida cuando el front prefiere que el backend maneje el upload
    en vez de subir directo desde el navegador.
    """
    extension = os.path.splitext(uploaded_file.name)[1] or ".jpg"
    nombre_unico = f"{uuid.uuid4()}{extension}"

    with tempfile.TemporaryDirectory() as tmp:
        local_path = os.path.join(tmp, nombre_unico)
        with open(local_path, "wb") as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        return subir_a_supabase(local_path, f"{carpeta}/{nombre_unico}")