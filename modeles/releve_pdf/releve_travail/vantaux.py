"""Vantaux de portes (quadrilatères tournés) et arcs de débattement d'une zone de plan.

Usage : python vantaux.py VUE u0 v0 u1 v1
Pour chaque quadrilatère non aligné sur les axes (angle > 5°) : ses 4 coins en pieds, sa longueur (grand côté),
son angle ; les deux coins du petit côté le plus proche d'un jambage donnent le pivot.
"""
import math
import sys

import outils_releve as O

vue = getattr(O, sys.argv[1].upper())
u0, v0, u1, v1 = (float(a) for a in sys.argv[2:6])
umin, umax = sorted((u0, u1))
vmin, vmax = sorted((v0, v1))
page = O.doc()[vue.page - 1]
for d in page.get_drawings():
    for it in d["items"]:
        if it[0] != "qu":
            continue
        q = it[1]
        pts = [vue.uv(p.x, p.y) for p in (q.ul, q.ur, q.lr, q.ll)]
        cx = sum(p[0] for p in pts) / 4
        cy = sum(p[1] for p in pts) / 4
        if not (umin <= cx <= umax and vmin <= cy <= vmax):
            continue
        cotes = [(pts[i], pts[(i + 1) % 4]) for i in range(4)]
        longs = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in cotes]
        i = max(range(4), key=lambda k: longs[k])
        a, b = cotes[i]
        ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180
        if min(ang, 180 - ang) < 5 or abs(ang - 90) < 5:
            continue
        if longs[i] < 1.0:
            continue
        # extrémités de l'axe du vantail (milieux des petits côtés)
        j = (i + 1) % 4
        c1 = cotes[j]
        c2 = cotes[(i + 3) % 4]
        m1 = ((c1[0][0] + c1[1][0]) / 2, (c1[0][1] + c1[1][1]) / 2)
        m2 = ((c2[0][0] + c2[1][0]) / 2, (c2[0][1] + c2[1][1]) / 2)
        print(f"  vantail L={longs[i]:.3f} ({O.pi_po(longs[i])}) ép={min(longs):.3f} angle={ang:5.1f}°  "
              f"bouts ({m1[0]:.3f}, {m1[1]:.3f}) et ({m2[0]:.3f}, {m2[1]:.3f})  w={d.get('width')}")
