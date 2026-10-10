"""Lister les surfaces remplies (murs, fondations…) d'une vue en plan, en pieds (repère AFFICHÉ).

Usage : python remplis.py PAGE X0 Y0 ECH [xmin ymin xmax ymax] [teinte]
  X0, Y0 : origine du plan en points affichés ; X vers la droite, Y vers le HAUT de la page
  ECH    : points par pied, mesuré sur les cotes (≈ 8,6 ici, les feuilles Lettre étant réduites)
  xmin… : fenêtre de recherche en points affichés (défaut : toute la page)
  teinte : ne garder que ce remplissage (1re composante arrondie à 3 décimales)
"""
import sys
from collections import Counter
from pathlib import Path

import fitz

ICI = Path(__file__).resolve().parent
from plan_pdf import chemin_pdf  # noqa: E402  (PLAN_PDF, sinon l'unique .pdf de ce dossier)
doc = fitz.open(chemin_pdf(ICI))
page_no = int(sys.argv[1])
X0, Y0, ECH = float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
zone = [float(v) for v in sys.argv[5:9]] if len(sys.argv) >= 9 else [0, 0, 1e9, 1e9]
cible = sys.argv[9] if len(sys.argv) > 9 else None
page = doc[page_no - 1]
M = page.rotation_matrix


def pi_po(v):
    s = "-" if v < 0 else ""
    v = abs(v) * 12
    pi, po = int(v // 12), v - 12 * int(v // 12)
    return f"{s}{pi}'-{po:.2f}\""


dessins = []
for d in page.get_drawings():
    f = d.get("fill")
    if f is None:
        continue
    r = fitz.Rect(d["rect"]) * M
    if not (r.x0 >= zone[0] and r.y0 >= zone[1] and r.x1 <= zone[2] and r.y1 <= zone[3]):
        continue
    dessins.append((tuple(round(c, 3) for c in f), r, len(d["items"])))

print("Teintes de remplissage dans la zone :", Counter(t for t, _, _ in dessins).most_common(12))
for cle, r, n in dessins:
    if cible and str(cle[0]) != cible:
        continue
    xa, xb = (r.x0 - X0) / ECH, (r.x1 - X0) / ECH
    ya, yb = (Y0 - r.y1) / ECH, (Y0 - r.y0) / ECH
    print(f"  remplissage {cle} : X {pi_po(xa)} → {pi_po(xb)} ; Y {pi_po(ya)} → {pi_po(yb)} "
          f"(larg {pi_po(xb - xa)}, haut {pi_po(yb - ya)}) {n} éléments")
