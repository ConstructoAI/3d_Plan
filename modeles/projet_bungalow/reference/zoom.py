"""Agrandir une zone d'une page du plan PDF (repère AFFICHÉ, pages tournées de 270°).

Usage : python zoom.py PAGE X0 Y0 X1 Y1 [DPI] [NOM]
  PAGE        : numéro de page (1 à 6)
  X0 Y0 X1 Y1 : coins de la zone en POINTS affichés (page 792 x 612 pt, origine en haut à gauche).
                Depuis l'aperçu pages/page_NN_180.png (1980 x 1530 px) : points = pixels ÷ 2,5.
  DPI         : résolution du rendu (défaut 300)
  NOM         : nom du fichier de sortie (défaut zoom_pPAGE_X0_Y0.png)
Le fichier est écrit dans reference/zooms/. On rend la page entière (tournée comme à l'écran), puis on découpe :
aucune ambiguïté sur le repère du paramètre clip de PyMuPDF pour une page tournée.
"""
import sys
from pathlib import Path

import fitz
from PIL import Image

ICI = Path(__file__).resolve().parent
from plan_pdf import chemin_pdf  # noqa: E402  (PLAN_PDF, sinon l'unique .pdf de ce dossier)
PDF = chemin_pdf(ICI)
SORTIE = ICI / "zooms"
SORTIE.mkdir(exist_ok=True)

page_no = int(sys.argv[1])
x0, y0, x1, y1 = (float(v) for v in sys.argv[2:6])
dpi = int(sys.argv[6]) if len(sys.argv) > 6 else 300
nom = sys.argv[7] if len(sys.argv) > 7 else f"zoom_p{page_no}_{int(x0)}_{int(y0)}.png"

doc = fitz.open(PDF)
page = doc[page_no - 1]
pix = page.get_pixmap(dpi=dpi)
img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
k = dpi / 72.0
boite = (int(round(x0 * k)), int(round(y0 * k)), int(round(x1 * k)), int(round(y1 * k)))
img.crop(boite).save(SORTIE / nom)
print(f"{nom} : {boite[2] - boite[0]} x {boite[3] - boite[1]} px à {dpi} dpi ; zone ({x0}, {y0}) → ({x1}, {y1}) pt ; "
      f"1 pt = {k:.4f} px")
