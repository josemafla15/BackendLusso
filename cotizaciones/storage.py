import mimetypes

import requests
from django.conf import settings


def subir_a_supabase(local_path, remote_path):
    """
    Sube un archivo local a Supabase Storage (bucket público) y devuelve
    la URL pública resultante.

    local_path:  ruta local del archivo a subir (ej. un PNG temporal)
    remote_path: ruta destino DENTRO del bucket (ej. "cotizaciones/<id>/viaje_sonado_intro_imagen.png")
    """
    content_type = mimetypes.guess_type(local_path)[0] or "application/octet-stream"

    upload_url = (
        f"{settings.SUPABASE_URL}/storage/v1/object/"
        f"{settings.SUPABASE_BUCKET}/{remote_path}"
    )

    with open(local_path, "rb") as f:
        response = requests.post(
            upload_url,
            data=f,
            headers={
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                "apikey": settings.SUPABASE_SERVICE_KEY,
                "Content-Type": content_type,
                "x-upsert": "true",  # crea si no existe, sobreescribe si ya existe
            },
        )

    response.raise_for_status()

    return (
        f"{settings.SUPABASE_URL}/storage/v1/object/public/"
        f"{settings.SUPABASE_BUCKET}/{remote_path}"
    )