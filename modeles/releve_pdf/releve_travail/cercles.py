"""Petits cercles (symboles) d'une vue en plan : chaque dessin PyMuPDF fait de courbes 'c' fermées.
Usage : python cercles.py VUE u0 v0 u1 v1 [rmin] [rmax]"""
import sys
import outils_releve as O
vue = getattr(O, sys.argv[1].upper())
u0, v0, u1, v1 = (float(a) for a in sys.argv[2:6])
rmin = float(sys.argv[6]) if len(sys.argv) > 6 else 0.1
rmax = float(sys.argv[7]) if len(sys.argv) > 7 else 0.6
page = O.doc()[vue.page - 1]
vus = []
for d in page.get_drawings():
    items = d["items"]
    if not items or not all(it[0] == "c" for it in items) or len(items) < 4:
        continue
    r = d["rect"]
    a0, b1 = vue.uv(r.x0, r.y0); a1, b0 = vue.uv(r.x1, r.y1)
    a0, a1 = sorted((a0, a1)); b0, b1 = sorted((b0, b1))
    cu, cv = (a0 + a1) / 2, (b0 + b1) / 2
    rr = (a1 - a0 + b1 - b0) / 4
    if not (min(u0,u1) <= cu <= max(u0,u1) and min(v0,v1) <= cv <= max(v0,v1)) or not (rmin <= rr <= rmax):
        continue
    if any(abs(cu - x) < 0.02 and abs(cv - y) < 0.02 for x, y in vus):
        continue
    vus.append((cu, cv))
    print(f"  cercle centre ({cu:7.3f}, {cv:7.3f}) r={rr:5.3f} (diam {O.pi_po(2*rr)}) w={d.get('width')} fill={d.get('fill')}")
