"""Quadrilatères et rectangles d'une zone d'une vue (u0 v0 u1 v1 en pieds), triés par taille.

Usage : python quads_zone.py VUE u0 v0 u1 v1 [taille_min]
"""
import sys

import outils_releve as O

vue = getattr(O, sys.argv[1].upper())
u0, v0, u1, v1 = (float(a) for a in sys.argv[2:6])
tmin = float(sys.argv[6]) if len(sys.argv) > 6 else 0.3
umin, umax = sorted((u0, u1))
vmin, vmax = sorted((v0, v1))
vus = set()
res = []
for s in O.traces(vue.page):
    if s[0] not in ("qu", "re"):
        continue
    ua, va = vue.uv(s[1], s[2])
    ub, vb = vue.uv(s[3], s[4])
    a0, a1 = sorted((ua, ub))
    b0, b1 = sorted((va, vb))
    if not (umin <= a0 and a1 <= umax and vmin <= b0 and b1 <= vmax):
        continue
    if max(a1 - a0, b1 - b0) < tmin:
        continue
    k = (round(a0, 3), round(b0, 3), round(a1, 3), round(b1, 3), s[5])
    if k in vus:
        continue
    vus.add(k)
    res.append((a0, b0, a1, b1, s[5], s[7]))
res.sort(key=lambda r: -((r[2] - r[0]) * (r[3] - r[1])))
for a0, b0, a1, b1, w, f in res:
    print(f"  {vue.nom_u} {a0:8.3f}..{a1:8.3f} ({O.pi_po(a1 - a0):>12})  {vue.nom_v} {b0:8.3f}..{b1:8.3f} "
          f"({O.pi_po(b1 - b0):>12})  w={w} fill={f}")
