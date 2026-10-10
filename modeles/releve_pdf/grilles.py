"""Repérer les axes de la grille (bulles A-G et 1-7) et les cotes d'une page.

Usage : python grilles.py PAGE
Affiche les bulles (lettre ou chiffre seul entouré d'un cercle) et leur position en points,
puis les segments longs en tirets (axes) qui passent par ces bulles.
"""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ICI = Path(__file__).resolve().parent
page_no = int(sys.argv[1])
mots = json.loads((ICI / "pages" / f"mots_page_{page_no:02d}.json").read_text(encoding="utf-8"))
traces = json.loads((ICI / "pages" / f"traces_page_{page_no:02d}.json").read_text(encoding="utf-8"))

# Cercles : courbes de Bézier ('c') regroupées ; on cherche plutôt les mots seuls
bulles = [m for m in mots if m[4] in list("ABCDEFG") + [str(i) for i in range(1, 8)]]
print("Mots d'un seul caractère candidats (x centre, y centre, taille) :")
for m in sorted(bulles, key=lambda m: (m[4], m[0])):
    cx, cy = (m[0] + m[2]) / 2, (m[1] + m[3]) / 2
    print(f"  {m[4]:>2}  x={cx:8.2f}  y={cy:8.2f}  h={m[3] - m[1]:5.2f}")

# Segments quasi verticaux ou horizontaux longs (> 200 pt)
longs = []
for s in traces:
    if s[0] != "l":
        continue
    x0, y0, x1, y1 = s[1:5]
    L = math.hypot(x1 - x0, y1 - y0)
    if L < 40:
        continue
    if abs(x1 - x0) < 0.2:
        longs.append(("V", round(x0, 2), min(y0, y1), max(y0, y1), s[5], s[6]))
    elif abs(y1 - y0) < 0.2:
        longs.append(("H", round(y0, 2), min(x0, x1), max(x0, x1), s[5], s[6]))

# Regrouper par coordonnée : un axe en tirets = beaucoup de petits segments alignés
groupes = defaultdict(list)
for o, c, a, b, w, col in longs:
    groupes[(o, c)].append((a, b, w, col))
print("\nAlignements verticaux/horizontaux (étendue > 300 pt) :")
for (o, c), segs in sorted(groupes.items()):
    a = min(s[0] for s in segs)
    b = max(s[1] for s in segs)
    if b - a > 300:
        print(f"  {o} {c:8.2f}  de {a:8.2f} à {b:8.2f}  ({len(segs)} seg., largeur {segs[0][2]}, couleur {segs[0][3]})")
