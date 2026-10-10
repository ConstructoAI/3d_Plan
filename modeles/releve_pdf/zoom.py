"""Agrandir une zone d'une page du plan PDF.

Usage : python zoom.py PAGE X0 Y0 X1 Y1 [DPI] [NOM]
  PAGE      : numéro de page (1 à 7)
  X0 Y0 X1 Y1 : coins de la zone en pixels de l'aperçu 2000 x 1333 (celui qu'affiche Read)
  DPI       : résolution du rendu (défaut 200)
  NOM       : nom du fichier de sortie (défaut zoom_pPAGE_X0_Y0.png)
Le fichier est écrit dans reference/zooms/. Il affiche aussi la zone en points PDF.
Le PDF : variable PLAN_PDF, sinon l'unique .pdf de ce dossier (voir plan_pdf.py).
⚠️ Page tournée : le `clip` de get_pixmap est ambigu ; rendre la page entière puis découper (version Bungalow).
"""
import sys
from pathlib import Path

import fitz

from plan_pdf import chemin_pdf

ICI = Path(__file__).resolve().parent
PDF = chemin_pdf(ICI)
SORTIE = ICI / "zooms"
SORTIE.mkdir(exist_ok=True)

page_no = int(sys.argv[1])
x0, y0, x1, y1 = (float(v) for v in sys.argv[2:6])
dpi = int(sys.argv[6]) if len(sys.argv) > 6 else 200
nom = sys.argv[7] if len(sys.argv) > 7 else f"zoom_p{page_no}_{int(x0)}_{int(y0)}.png"

doc = fitz.open(PDF)
page = doc[page_no - 1]
W, H = page.rect.width, page.rect.height
clip = fitz.Rect(x0 / 2000 * W, y0 / 1333 * H, x1 / 2000 * W, y1 / 1333 * H)
pix = page.get_pixmap(dpi=dpi, clip=clip)
pix.save(SORTIE / nom)
print(f"{nom} : {pix.width} x {pix.height} px ; zone PDF {clip} (points)")
