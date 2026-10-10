"""Tous les segments d'une zone (toutes orientations), avec largeur de trait, en pieds de la vue.
Usage : python tous_segments.py VUE u0 v0 u1 v1 [wmin] [lmin]"""
import math, sys
import outils_releve as O
vue = getattr(O, sys.argv[1].upper())
u0, v0, u1, v1 = (float(a) for a in sys.argv[2:6])
wmin = float(sys.argv[6]) if len(sys.argv) > 6 else 0.5
lmin = float(sys.argv[7]) if len(sys.argv) > 7 else 0.3
vus = set()
for t, a, b, c, d, w, col, f in vue.segments(u0, v0, u1, v1, types=("l", "c")):
    L = math.hypot(c - a, d - b)
    if w < wmin or L < lmin:
        continue
    k = (round(a, 2), round(b, 2), round(c, 2), round(d, 2))
    if k in vus: continue
    vus.add(k)
    ang = math.degrees(math.atan2(d - b, c - a)) % 180
    print(f"  {t} ({a:7.3f},{b:7.3f}) -> ({c:7.3f},{d:7.3f})  L={L:6.3f} ang={ang:5.1f} w={w}")
