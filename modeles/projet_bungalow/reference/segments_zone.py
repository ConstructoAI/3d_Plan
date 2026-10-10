"""Lister les segments d'une zone, convertis en coordonnées de vue (pieds).

Usage : python segments_zone.py PAGE XMIN YMIN XMAX YMAX H0 Z0 ECH [largeur_min] [longueur_min_pi] [sens]
  H0 : x (points) où la coordonnée horizontale vaut 0 ; Z0 : y (points) où Z vaut 0
  ECH : points par pied (18 au 1/4") ; sens : +1 si h croît vers la droite, -1 sinon
Sortie : h0 z0 → h1 z1 (pieds), largeur du trait, longueur, pente (montée/12).
"""
import json
import math
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
page_no = int(sys.argv[1])
xmin, ymin, xmax, ymax = (float(v) for v in sys.argv[2:6])
H0, Z0, ECH = (float(v) for v in sys.argv[6:9])
lmin = float(sys.argv[9]) if len(sys.argv) > 9 else 0.5
Lmin = float(sys.argv[10]) if len(sys.argv) > 10 else 1.0
sens = float(sys.argv[11]) if len(sys.argv) > 11 else 1.0
traces = json.loads((ICI / "pages" / f"traces_page_{page_no:02d}.json").read_text(encoding="utf-8"))


def pp(v):
    s = "-" if v < 0 else ""
    v = abs(v) * 12
    return f"{s}{int(v // 12)}'-{v - 12 * int(v // 12):.1f}\""


out = []
for s in traces:
    if s[0] != "l":
        continue
    x0, y0, x1, y1, w = s[1], s[2], s[3], s[4], s[5]
    if w < lmin:
        continue
    if not (xmin <= min(x0, x1) and max(x0, x1) <= xmax and ymin <= min(y0, y1) and max(y0, y1) <= ymax):
        continue
    h0, h1 = sens * (x0 - H0) / ECH, sens * (x1 - H0) / ECH
    z0, z1 = (Z0 - y0) / ECH, (Z0 - y1) / ECH
    L = math.hypot(h1 - h0, z1 - z0)
    if L < Lmin:
        continue
    if h1 < h0:
        h0, h1, z0, z1 = h1, h0, z1, z0
    pente = (z1 - z0) / (h1 - h0) * 12 if abs(h1 - h0) > 1e-6 else float("inf")
    out.append((h0, z0, h1, z1, w, L, pente))
for h0, z0, h1, z1, w, L, p in sorted(out, key=lambda t: (-t[5])):
    ps = "vert." if p == float("inf") else f"{p:+.2f}/12"
    print(f"({pp(h0):>10}, {pp(z0):>10}) → ({pp(h1):>10}, {pp(z1):>10})  w={w:.2f}  L={pp(L):>10}  pente {ps}")
