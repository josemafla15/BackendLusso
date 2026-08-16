import fitz

doc = fitz.open("cotizacion_completa_e84f2a8e.pdf")

total_imagenes = 0
for num_pagina, pagina in enumerate(doc, start=1):
    imagenes = pagina.get_images(full=True)
    print(f"Página {num_pagina}: {len(imagenes)} imágenes")
    for img in imagenes:
        xref = img[0]
        pix = fitz.Pixmap(doc, xref)
        peso_kb = len(doc.xref_stream_raw(xref)) / 1024
        alpha = "CON alpha" if pix.alpha else "sin alpha"
        print(f"    {pix.width}x{pix.height}px, {peso_kb:.0f} KB, {alpha}")
        pix = None
    total_imagenes += len(imagenes)

print(f"\nTotal de imágenes en el documento: {total_imagenes}")
print(f"Total de páginas: {doc.page_count}")
doc.close()