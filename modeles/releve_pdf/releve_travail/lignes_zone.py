"""Lignes horizontales et verticales d'une zone d'une vue (u0 v0 u1 v1 en pieds).

Usage : python lignes_zone.py VUE u0 v0 u1 v1 [wmin] [lmin]
"""
import sys

import outils_releve as O

vue = getattr(O, sys.argv[1].upper())
u0, v0, u1, v1 = (float(a) for a in sys.argv[2:6])
wmin = float(sys.argv[6]) if len(sys.argv) > 6 else 0.5
lmin = float(sys.argv[7]) if len(sys.argv) > 7 else 0.8
segs = vue.segments(u0, v0, u1, v1, types=("l", "qu", "re"))
H, V = set(), set()
for t, a, b, c, d, w, col, f in segs:
    if w < wmin:
        continue
    if t in ("qu", "re"):
        a0, a1 = sorted((a, c))
        b0, b1 = sorted((b, d))
        for bb in (b0, b1):
            if a1 - a0 >= lmin:
                H.add((round(bb, 3), round(a0, 3), round(a1, 3), w, "q"))
        for aa in (a0, a1):
            if b1 - b0 >= lmin:
                V.add((round(aa, 3), round(b0, 3), round(b1, 3), w, "q"))
        continue
    if abs(b - d) < 0.004 and abs(c - a) >= lmin:
        H.add((round(b, 3), round(min(a, c), 3), round(max(a, c), 3), w, "l"))
    if abs(a - c) < 0.004 and abs(d - b) >= lmin:
        V.add((round(a, 3), round(min(b, d), 3), round(max(b, d), 3), w, "l"))
print(f"H ({vue.nom_v} ; {vue.nom_u}0..{vue.nom_u}1 ; w) :")
for h in sorted(H):
    print("  ", h, O.pi_po(h[0]))
print(f"V ({vue.nom_u} ; {vue.nom_v}0..{vue.nom_v}1 ; w) :")
for v in sorted(V):
    print("  ", v, O.pi_po(v[0]))
