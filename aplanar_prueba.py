import io
import fitz
from PIL import Image

doc = fitz.open("cotizacion_completa_e84f2a8e.pdf")
doc_nuevo = fitz.open()

for pagina in doc:
    pix = pagina.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=80)
    img_bytes = buffer.getvalue()

    pagina_nueva = doc_nuevo.new_page(width=pagina.rect.width, height=pagina.rect.height)
    pagina_nueva.insert_image(pagina_nueva.rect, stream=img_bytes)

doc_nuevo.save("cotizacion_completa_e84f2a8e_jpg.pdf")
doc_nuevo.close()
doc.close()
print("Listo: cotizacion_completa_e84f2a8e_jpg.pdf")