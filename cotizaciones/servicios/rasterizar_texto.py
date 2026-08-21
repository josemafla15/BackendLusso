from playwright.sync_api import sync_playwright


def generar_png_transparente(cotizacion_id, selector, output_path, bloque="viajesonado_captura", scale=2):
    """
    Versión standalone (abre y cierra su propio navegador) -- se
    mantiene para compatibilidad con usos puntuales/manuales por
    shell. Para generar varias capturas seguidas, usar
    abrir_pagina_captura + capturar_selector en su lugar (mucho más
    rápido, reutiliza el mismo navegador).
    """
    url = f"http://127.0.0.1:8000/cotizaciones/preview/{cotizacion_id}/{bloque}/"

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=scale,
        )
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.add_style_tag(content="""
            html, body, .lusso-page {
                background: transparent !important;
            }
        """)
        page.locator(selector).screenshot(path=output_path, omit_background=True)
        browser.close()

    return output_path


def abrir_pagina_captura(cotizacion_id, bloque="viajesonado_captura", scale=2):
    """
    Abre UN SOLO navegador y navega UNA SOLA VEZ a la página de
    captura. Devuelve (playwright_ctx, browser, page) -- quien llama
    es responsable de cerrar browser y playwright_ctx cuando termine
    de sacar todas las capturas que necesite.
    """
    import os

    base_url = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")
    url = f"{base_url}/cotizaciones/preview/{cotizacion_id}/{bloque}/"

    playwright_ctx = sync_playwright().start()
    browser = playwright_ctx.chromium.launch()
    page = browser.new_page(
        viewport={"width": 1920, "height": 1080},
        device_scale_factor=scale,
    )
    page.goto(url, wait_until="networkidle", timeout=60000)
    page.add_style_tag(content="""
        html, body, .lusso-page {
            background: transparent !important;
        }
    """)
    return playwright_ctx, browser, page


def capturar_selector(page, selector, output_path):
    """Saca UNA captura de un selector, sobre una página ya cargada."""
    page.locator(selector).screenshot(path=output_path, omit_background=True)
    return output_path