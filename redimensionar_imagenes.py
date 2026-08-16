import io

import fitz
from PIL import Image

CAP = 1600  # lado más largo permitido, en px -- ajustable

doc = fitz.open("cotizacion_completa_e84f2a8e.pdf")

for pagina in doc:
    for img in pagina.get_images(full=True):
        xref = img[0]
        smask_xref = img[1]  # 0 si no tiene máscara de transparencia

        base = doc.extract_image(xref)
        ancho, alto = base["width"], base["height"]
        lado_mayor = max(ancho, alto)

        if lado_mayor <= CAP:
            continue  # ya está en un tamaño razonable, no la tocamos

        factor = CAP / lado_mayor
        nuevo_ancho = int(ancho * factor)
        nuevo_alto = int(alto * factor)

        pil_img = Image.open(io.BytesIO(base["image"]))

        if smask_xref:
            # Tiene transparencia -- la preservamos, guardamos como PNG
            smask_base = doc.extract_image(smask_xref)
            smask_img = Image.open(io.BytesIO(smask_base["image"])).convert("L")
            pil_img = pil_img.convert("RGB")
            pil_img.putalpha(smask_img.resize(pil_img.size))
            pil_img = pil_img.resize((nuevo_ancho, nuevo_alto), Image.LANCZOS)
            buffer = io.BytesIO()
            pil_img.save(buffer, format="PNG", optimize=True)
        else:
            # Sin transparencia -- comprimimos como JPEG, más liviano
            pil_img = pil_img.convert("RGB").resize((nuevo_ancho, nuevo_alto), Image.LANCZOS)
            buffer = io.BytesIO()
            pil_img.save(buffer, format="JPEG", quality=85)

        pagina.replace_image(xref, stream=buffer.getvalue())

doc.save("cotizacion_completa_e84f2a8e_resized.pdf")
doc.close()
print("Listo: cotizacion_completa_e84f2a8e_resized.pdf")