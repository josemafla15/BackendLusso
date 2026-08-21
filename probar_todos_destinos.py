import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from playwright.sync_api import sync_playwright

from cotizaciones.models import Cotizacion, DestinoContenido
from cotizaciones.servicios.asegurar_imagenes import (
    asegurar_imagenes_despertar_bienvenidos,
    asegurar_imagenes_portada_buenviaje,
    asegurar_imagenes_viajesonado,
)

User = get_user_model()
user = User.objects.filter(is_staff=True).first()
client = Client()

resp_login = client.post(
    "/api/auth/login/",
    {"username": user.username, "password": "prueba12345"},
    content_type="application/json",
)
access_token = resp_login.json()["access"]
headers = {"HTTP_AUTHORIZATION": f"Bearer {access_token}"}

destinos = DestinoContenido.objects.all().order_by("nombre")
print(f"Se van a generar {destinos.count()} cotizaciones de prueba, una por destino.\n")

for destino in destinos:
    print(f"=== {destino.nombre} ===")

    resp = client.post(
        "/api/cotizaciones/",
        {"destino": destino.nombre, "nombre_cliente": f"Prueba {destino.nombre}"},
        content_type="application/json",
        **headers,
    )

    if resp.status_code != 201:
        print(f"  ERROR al crear: {resp.status_code} - {resp.json()}")
        continue

    cotizacion_id = resp.json()["id"]
    cotizacion = Cotizacion.objects.get(id=cotizacion_id)

    asegurar_imagenes_viajesonado(cotizacion)
    asegurar_imagenes_despertar_bienvenidos(cotizacion)
    asegurar_imagenes_portada_buenviaje(cotizacion)

    url_preview = f"http://127.0.0.1:8000/cotizaciones/preview/{cotizacion_id}/completa/"
    slug = destino.nombre.lower().replace(" ", "_").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    output = f"prueba_{slug}.pdf"

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto(url_preview, wait_until="networkidle")
        page.pdf(
            path=output,
            width="20in",
            height="11.25in",
            print_background=True,
            margin={"top": "0px", "bottom": "0px", "left": "0px", "right": "0px"},
        )
        browser.close()

    print(f"  PDF generado: {output}\n")

print("Listo. Todos los PDFs de prueba quedaron en la carpeta actual.")