"""
Script standalone para exportar una página de preview a PDF con Playwright.

USO:
    python generar_pdf.py <bloque> [cotizacion_id]

    Ejemplos:
        python generar_pdf.py completa
        python generar_pdf.py completa a1b2c3d4-...-xyz

    Si no pasas cotizacion_id, usa la cotización de prueba de Coveñas por defecto.

Requiere que el servidor de Django esté corriendo
(python manage.py runserver) en otra terminal.
"""

import sys

from playwright.sync_api import sync_playwright

COTIZACION_ID_DEFAULT = "7ac00c34-9dbb-48ab-859b-ab5f9922dcba"


def generar_pdf(bloque, cotizacion_id):
    url = f"http://127.0.0.1:8000/cotizaciones/preview/{cotizacion_id}/{bloque}/"
    output = f"cotizacion_{bloque}_{cotizacion_id[:8]}.pdf"

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto(url, wait_until="networkidle")

        page.pdf(
    path=output,
    width="20in",     # 1920px / 96dpi
    height="11.25in", # 1080px / 96dpi
    print_background=True,
    margin={"top": "0px", "bottom": "0px", "left": "0px", "right": "0px"},
)
        browser.close()

    print(f"PDF generado: {output}")


if __name__ == "__main__":
    bloque = sys.argv[1] if len(sys.argv) > 1 else "portada"
    cotizacion_id = sys.argv[2] if len(sys.argv) > 2 else COTIZACION_ID_DEFAULT
    generar_pdf(bloque, cotizacion_id)