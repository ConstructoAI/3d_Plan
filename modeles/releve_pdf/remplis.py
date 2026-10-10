"""Lister les surfaces remplies (murs, fenêtres…) d'une vue en plan, en pieds.

Usage : python remplis.py PAGE X_AXE_A Y_AXE_6 [xmin ymin xmax ymax]
  X_AXE_A, Y_AXE_6 : origine (points PDF) ; X vers la droite (est), Y vers le haut (nord)
  xmin… : fenêtre de recherche en points PDF (défaut : toute la page)
Échelle 1/4" = 1'-0" : 18 points = 1 pied (ECH ci-dessous ; la mesurer sur deux longues chaînes de cotes
si la feuille a été réduite : SAVOIR_LECTURE_PLANS.md).
Le PDF : variable PLAN_PDF, sinon l'unique .pdf de ce dossier (voir plan_pdf.py).
"""
import sys
from collections import Counter
from pathlib import Path

import fitz

from plan_pdf import chemin_pdf

ICI = Path(__file__).resolve().parent
doc = fitz.open(chemin_pdf(ICI))
page_no = int(sys.argv[1])
X0, Y0 = float(sys.argv[2]), float(sys.argv[3])
zone = [float(v) for v in sys.argv[4:8]] if len(sys.argv) >= 8 else [0, 0, 1e9, 1e9]
page = doc[page_no - 1]
ECH = 18.0


def pi_po(v):
    s = "-" if v < 0 else ""
    v = abs(v) * 12
    pi, po = int(v // 12), v - 12 * int(v // 12)
    return f"{s}{pi}'-{po:.2f}\""


teintes = Counter()
for d in page.get_drawings():
    f = d.get("fill")
    if f is None:
        continue
    r = d["rect"]
    if not (r.x0 >= zone[0] and r.y0 >= zone[1] and r.x1 <= zone[2] and r.y1 <= zone[3]):
        continue
    cle = tuple(round(c, 3) for c in f)
    teintes[cle] += 1
print("Teintes de remplissage dans la zone :", teintes.most_common(12))

cible = sys.argv[8] if len(sys.argv) > 8 else None
for d in page.get_drawings():
    f = d.get("fill")
    if f is None:
        continue
    r = d["rect"]
    if not (r.x0 >= zone[0] and r.y0 >= zone[1] and r.x1 <= zone[2] and r.y1 <= zone[3]):
        continue
    cle = tuple(round(c, 3) for c in f)
    if cible and str(cle[0]) != cible:
        continue
    xa, xb = (r.x0 - X0) / ECH, (r.x1 - X0) / ECH
    ya, yb = (Y0 - r.y1) / ECH, (Y0 - r.y0) / ECH
    n = len(d["items"])
    print(f"  remplissage {cle} : X {pi_po(xa)} → {pi_po(xb)} ; Y {pi_po(ya)} → {pi_po(yb)} "
          f"(larg {pi_po(xb - xa)}, haut {pi_po(yb - ya)}) {n} éléments")
