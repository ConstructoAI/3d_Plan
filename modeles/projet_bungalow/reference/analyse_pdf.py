"""Premier examen du plan PDF : pages, formats, texte, vectoriel ou image.

Usage : python analyse_pdf.py [dpi]
Écrit reference/pages/page_NN.png (aperçus) et reference/pages/texte_page_NN.txt.
"""
import sys
from pathlib import Path

import fitz  # PyMuPDF

ICI = Path(__file__).resolve().parent
from plan_pdf import chemin_pdf  # noqa: E402  (PLAN_PDF, sinon l'unique .pdf de ce dossier)
PDF = chemin_pdf(ICI)
SORTIE = ICI / "pages"
SORTIE.mkdir(exist_ok=True)
DPI = int(sys.argv[1]) if len(sys.argv) > 1 else 60

doc = fitz.open(PDF)
print(f"Pages : {doc.page_count}")
print(f"Métadonnées : {doc.metadata}")
for i, page in enumerate(doc):
    r = page.rect
    n_dessins = len(page.get_drawings())
    images = page.get_images(full=True)
    texte = page.get_text("text")
    mots = page.get_text("words")
    print(
        f"--- page {i + 1} : {r.width / 72:.2f} x {r.height / 72:.2f} po "
        f"(rotation {page.rotation}), {n_dessins} tracés vectoriels, "
        f"{len(images)} images, {len(mots)} mots"
    )
    for im in images[:5]:
        print(f"    image xref={im[0]} {im[2]}x{im[3]} px")
    lignes = [l.strip() for l in texte.splitlines() if l.strip()]
    print("    texte (début) :", " | ".join(lignes[:40]))
    (SORTIE / f"texte_page_{i + 1:02d}.txt").write_text(texte, encoding="utf-8")
    pix = page.get_pixmap(dpi=DPI)
    pix.save(SORTIE / f"page_{i + 1:02d}.png")
