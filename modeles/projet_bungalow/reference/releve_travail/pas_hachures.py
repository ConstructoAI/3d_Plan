"""Pas des hachures de revêtement dans une zone d'élévation.

Usage : python pas_hachures.py VUE u0 v0 u1 v1 H|V [wmin wmax] [lmin]
H = lignes horizontales (déclin, planches couchées) : pas mesuré en Z.
V = lignes verticales (lattes, joints de tôle) : pas mesuré en u.
Affiche les positions, les écarts successifs et leur médiane.
"""
import statistics
import sys

import outils_releve as O

vue = getattr(O, sys.argv[1].upper())
u0, v0, u1, v1 = (float(a) for a in sys.argv[2:6])
sens = sys.argv[6]
wmin = float(sys.argv[7]) if len(sys.argv) > 7 else 0.3
wmax = float(sys.argv[8]) if len(sys.argv) > 8 else 0.8
lmin = float(sys.argv[9]) if len(sys.argv) > 9 else 0.5
pos = {}
umin, umax = sorted((u0, u1))
vmin, vmax = sorted((v0, v1))
for s in O.traces(vue.page):
    if s[0] != "l" or not (wmin <= s[5] <= wmax):
        continue
    ua, va = vue.uv(s[1], s[2])
    ub, vb = vue.uv(s[3], s[4])
    if sens == "H" and abs(vb - va) < 0.01 and vmin <= va <= vmax:
        a, b = max(min(ua, ub), umin), min(max(ua, ub), umax)   # partie dans la zone
        if b - a >= lmin:
            k = round(va, 3)
            pos[k] = pos.get(k, 0) + (b - a)
    elif sens == "V" and abs(ub - ua) < 0.01 and umin <= ua <= umax:
        a, b = max(min(va, vb), vmin), min(max(va, vb), vmax)
        if b - a >= lmin:
            k = round(ua, 3)
            pos[k] = pos.get(k, 0) + (b - a)
xs = sorted(pos)
d = [round(b - a, 3) for a, b in zip(xs, xs[1:])]
print("positions :", xs)
print("écarts (po) :", [round(x * 12, 2) for x in d])
if d:
    print(f"médiane {statistics.median(d) * 12:.2f} po ; n = {len(xs)} lignes")
