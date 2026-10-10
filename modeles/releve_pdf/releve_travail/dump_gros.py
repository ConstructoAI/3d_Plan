"""Surfaces remplies d'une teinte donnée, dont les deux côtés dépassent un seuil (pieds)."""
import sys
import outils_releve as O
vue = getattr(O, sys.argv[1].upper())
t_cible = float(sys.argv[2])
seuil = float(sys.argv[3]) if len(sys.argv) > 3 else 0.2
zone = [float(v) for v in sys.argv[4:8]] if len(sys.argv) >= 8 else [-20, -20, 80, 80]
page = O.doc()[vue.page - 1]
vus = set()
for d in page.get_drawings():
    f = d.get("fill")
    if f is None or abs(f[0] - t_cible) > 0.0015:
        continue
    r = d["rect"]
    ua, va = vue.uv(r.x0, r.y1)
    ub, vb = vue.uv(r.x1, r.y0)
    if ua > ub: ua, ub = ub, ua
    if va > vb: va, vb = vb, va
    if not (zone[0] <= ua and ub <= zone[2] and zone[1] <= va and vb <= zone[3]):
        continue
    if (ub - ua) < seuil and (vb - va) < seuil:
        continue
    if (ub - ua) < 0.02 or (vb - va) < 0.02:
        continue
    cle = (round(ua, 2), round(va, 2), round(ub, 2), round(vb, 2))
    if cle in vus:
        continue
    vus.add(cle)
    print(f"U {ua:8.3f}..{ub:8.3f}  V {va:8.3f}..{vb:8.3f}   ({O.pi_po(ub-ua)} x {O.pi_po(vb-va)})  n={len(d['items'])}")
