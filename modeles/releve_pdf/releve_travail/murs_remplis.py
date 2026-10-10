"""Dump des surfaces remplies d'une vue en plan, en pieds (repère commun).

Usage : python murs_remplis.py VUE [umin vmin umax vmax] [teinte]
VUE : rdc | etage | fond
"""
import sys

import fitz

import outils_releve as O

vue = getattr(O, sys.argv[1].upper())
zone = [float(v) for v in sys.argv[2:6]] if len(sys.argv) >= 6 else [-20, -20, 80, 80]
cible = sys.argv[6] if len(sys.argv) > 6 else None
page = O.doc()[vue.page - 1]

for d in page.get_drawings():
    f = d.get("fill")
    if f is None:
        continue
    t = round(f[0], 3)
    if cible and str(t) != cible:
        continue
    r = d["rect"]
    ua, va = vue.uv(r.x0, r.y1)
    ub, vb = vue.uv(r.x1, r.y0)
    if not (zone[0] <= ua and ub <= zone[2] and zone[1] <= va and vb <= zone[3]):
        continue
    pts = []
    for it in d["items"]:
        if it[0] == "l":
            for p in (it[1], it[2]):
                pts.append(vue.uv(p.x, p.y))
        elif it[0] == "re":
            rr = it[1]
            pts += [vue.uv(rr.x0, rr.y0), vue.uv(rr.x1, rr.y1)]
        elif it[0] == "qu":
            q = it[1]
            pts += [vue.uv(q.ul.x, q.ul.y), vue.uv(q.lr.x, q.lr.y)]
    # sommets uniques dans l'ordre
    uniq = []
    for p in pts:
        p = (round(p[0], 3), round(p[1], 3))
        if not uniq or uniq[-1] != p:
            uniq.append(p)
    print(f"t={t} X {ua:8.3f}..{ub:8.3f} Y {va:8.3f}..{vb:8.3f}  ({O.pi_po(ub-ua)} x {O.pi_po(vb-va)}) "
          f"n={len(d['items'])} w={d.get('width')} col={d.get('color')}")
    if len(uniq) <= 12:
        print("      ", uniq)
