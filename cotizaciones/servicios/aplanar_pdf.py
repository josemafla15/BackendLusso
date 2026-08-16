import shutil
import subprocess


def _detectar_binario_ghostscript():
    """
    En Windows el ejecutable de consola se llama gswin64c (o gswin32c
    en sistemas de 32 bits). En Linux (como el contenedor de Railway)
    se llama simplemente gs. Probamos en ese orden.
    """
    for nombre in ("gswin64c", "gswin32c", "gs"):
        ruta = shutil.which(nombre)
        if ruta:
            return ruta
    raise RuntimeError(
        "No se encontró Ghostscript instalado (probé gswin64c, gswin32c, gs). "
        "En Windows: instalalo desde ghostscript.com/releases. "
        "En Railway: agregá nixpacks.toml con aptPkgs = ['...', 'ghostscript']."
    )


def aplanar_transparencia_pdf(path_entrada, path_salida):
    """
    Usa Ghostscript para resolver (aplanar) las capas de transparencia
    de un PDF, sin convertir las páginas en imágenes completas -- el
    texto sigue siendo texto real y las imágenes normales no se tocan.
    Esto acelera el scroll en Chrome (que recalcula SMask en tiempo
    real) sin perjudicar la compatibilidad con Canva, a diferencia de
    aplanar cada página entera a imagen.
    """
    binario = _detectar_binario_ghostscript()

    comando = [
        binario,
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.3",
        "-dPDFSETTINGS=/prepress",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        f"-sOutputFile={path_salida}",
        path_entrada,
    ]

    resultado = subprocess.run(comando, capture_output=True, text=True)

    if resultado.returncode != 0:
        raise RuntimeError(
            f"Ghostscript falló (código {resultado.returncode}): {resultado.stderr}"
        )

    return path_salida