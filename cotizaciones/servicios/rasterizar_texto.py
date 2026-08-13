# cotizaciones/servicios/rasterizar_texto.py
from playwright.sync_api import sync_playwright

def generar_png_transparente(cotizacion_id, selector, output_path, bloque="viajesonado_captura", scale=2):
    """
    Versión función de generar_captura_transparente.py -- misma técnica
    exacta (fondo transparente vía omit_background), pero invocable
    desde código en vez de consola.
    """
    url = f"http://127.0.0.1:8000/cotizaciones/preview/{cotizacion_id}/{bloque}/"

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=scale,
        )
        page.goto(url, wait_until="networkidle")
        page.add_style_tag(content="""
            html, body, .lusso-page {
                background: transparent !important;
            }
        """)
        page.locator(selector).screenshot(path=output_path, omit_background=True)
        browser.close()

    return output_path