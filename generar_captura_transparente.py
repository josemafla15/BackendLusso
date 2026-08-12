"""
Script standalone para capturar UN ELEMENTO específico de una página
de preview como PNG con fondo transparente, usando Playwright.

No pasa por Canva ni por ninguna herramienta de recorte de fondo:
Chrome renderiza directamente con canal alfa.

USO:
    python generar_captura_transparente.py <bloque> <selector_css> <output.png> [cotizacion_id]

    Ejemplo:
        python generar_captura_transparente.py artevivir ".a-headline" arte_de_vivir_headline.png

Requiere que el servidor de Django esté corriendo
(python manage.py runserver) en otra terminal.
"""

import sys

from playwright.sync_api import sync_playwright

COTIZACION_ID_DEFAULT = "7ac00c34-9dbb-48ab-859b-ab5f9922dcba"


def generar_captura(bloque, selector, output, cotizacion_id, scale=2):
    url = f"http://127.0.0.1:8000/cotizaciones/preview/{cotizacion_id}/{bloque}/"

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=scale,  # 2 o 3 -> exporta a mayor resolución real
        )
        page.goto(url, wait_until="networkidle")

        # Inyectamos CSS extra DESPUÉS de que la página cargó, solo para esta
        # captura. No toca tu template ni afecta a generar_pdf.py.
        # Ponemos transparente el fondo de .lusso-page (y del <html>/<body>
        # por si acaso) para que no se filtre el color crema/verde/etc.
        # detrás del elemento que estamos recortando.
        page.add_style_tag(content="""
            html, body, .lusso-page {
                background: transparent !important;
            }
        """)

        # Capturamos SOLO el elemento pedido, no la página completa.
        # omit_background=True le dice a Chrome que renderice con canal alfa
        # en vez de rellenar con blanco/color de fondo por defecto.
        locator = page.locator(selector)
        locator.screenshot(path=output, omit_background=True)

        browser.close()

    print(f"Captura generada: {output}")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Uso: python generar_captura_transparente.py <bloque> <selector_css> <output.png> [cotizacion_id]")
        sys.exit(1)

    bloque = sys.argv[1]
    selector = sys.argv[2]
    output = sys.argv[3]
    cotizacion_id = sys.argv[4] if len(sys.argv) > 4 else COTIZACION_ID_DEFAULT

    generar_captura(bloque, selector, output, cotizacion_id)