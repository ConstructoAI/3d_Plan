"""Ouvertures d'une élévation : vitrages (0,24 pt) regroupés, puis cadre 0,72 pt qui les entoure et divisions.

Usage : python ouvertures_elevation.py VUE [u0 v0 u1 v1]
Pour chaque groupe de vitrages voisins (écart < 0,6 pi) : boîte du vitrage, cadre extérieur (traits de 0,72 pt les plus
proches à l'extérieur, à moins de 0,6 pi), meneaux et traverses (traits de 0,72 pt à l'intérieur du cadre).
Les contours de vitrages = rectangles fermés de 0,24 pt (4 traits ou quadrilatère).
"""
import sys

import outils_releve as O
from composantes import composantes


def groupes_vitrages(vue, zone):
    comps = [c for c in composantes(vue, 0.2, 0.25, zone, 0.02) if c[4] >= 4 and (c[2] - c[0]) > 0.2 and (c[3] - c[1]) > 0.2]
    # regrouper les vitrages voisins (même ouverture : meneaux et traverses de moins de 0,6 pi)
    grp = []
    for c in comps:
        for g in grp:
            if c[0] < g[2] + 0.6 and c[2] > g[0] - 0.6 and c[1] < g[3] + 0.6 and c[3] > g[1] - 0.6:
                g[0] = min(g[0], c[0]); g[1] = min(g[1], c[1]); g[2] = max(g[2], c[2]); g[3] = max(g[3], c[3])
                g[4].append(c)
                break
        else:
            grp.append([c[0], c[1], c[2], c[3], [c]])
    # fusion itérative
    change = True
    while change:
        change = False
        for i in range(len(grp)):
            for j in range(i + 1, len(grp)):
                a, b = grp[i], grp[j]
                if a[0] < b[2] + 0.6 and a[2] > b[0] - 0.6 and a[1] < b[3] + 0.6 and a[3] > b[1] - 0.6:
                    a[0] = min(a[0], b[0]); a[1] = min(a[1], b[1]); a[2] = max(a[2], b[2]); a[3] = max(a[3], b[3])
                    a[4] += b[4]
                    del grp[j]
                    change = True
                    break
            if change:
                break
    return grp


def cadre(vue, g, marge=0.6):
    u0, v0, u1, v1 = g[0], g[1], g[2], g[3]
    segs = vue.segments(u0 - marge - 0.05, v0 - marge - 0.05, u1 + marge + 0.05, v1 + marge + 0.05,
                        types=("l",), wmin=0.7, wmax=0.75)
    V = [(ua, min(va, vb), max(va, vb)) for t, ua, va, ub, vb, *_ in segs if abs(ub - ua) < 0.01 and abs(vb - va) > 0.3]
    H = [(va, min(ua, ub), max(ua, ub)) for t, ua, va, ub, vb, *_ in segs if abs(vb - va) < 0.01 and abs(ub - ua) > 0.3]
    hauteur = v1 - v0
    largeur = u1 - u0
    # verticaux qui couvrent au moins la moitié de la hauteur du vitrage
    Vg = [u for u, a, b in V if u <= u0 + 0.02 and min(b, v1) - max(a, v0) > 0.3 * hauteur]
    Vd = [u for u, a, b in V if u >= u1 - 0.02 and min(b, v1) - max(a, v0) > 0.3 * hauteur]
    Hb = [v for v, a, b in H if v <= v0 + 0.02 and min(b, u1) - max(a, u0) > 0.3 * largeur]
    Hh = [v for v, a, b in H if v >= v1 - 0.02 and min(b, u1) - max(a, u0) > 0.3 * largeur]
    fu0 = min(Vg) if Vg else None
    fu1 = max(Vd) if Vd else None
    fv0 = min(Hb) if Hb else None
    fv1 = max(Hh) if Hh else None
    # divisions intérieures
    mene = sorted(set(round(u, 3) for u, a, b in V if u0 + 0.05 < u < u1 - 0.05 and min(b, v1) - max(a, v0) > 0.3))
    trav = sorted(set(round(v, 3) for v, a, b in H if v0 + 0.05 < v < v1 - 0.05 and min(b, u1) - max(a, u0) > 0.3))
    return fu0, fv0, fu1, fv1, mene, trav


if __name__ == "__main__":
    vue = getattr(O, sys.argv[1].upper())
    zone = [float(a) for a in sys.argv[2:6]] if len(sys.argv) >= 6 else [-20, -2, 52, 30]
    for g in sorted(groupes_vitrages(vue, zone), key=lambda g: g[0]):
        fu0, fv0, fu1, fv1, mene, trav = cadre(vue, g)
        n = len(g[4])
        print(f"vitrage {vue.nom_u} {g[0]:7.3f}..{g[2]:7.3f}  Z {g[1]:7.3f}..{g[3]:7.3f}  ({n} carreaux)")
        if None not in (fu0, fu1, fv0, fv1):
            print(f"   cadre {vue.nom_u} {fu0:7.3f}..{fu1:7.3f} ({O.pi_po(fu1 - fu0)} = {(fu1 - fu0) * 12:.2f}\")  "
                  f"Z {fv0:7.3f}..{fv1:7.3f} ({O.pi_po(fv1 - fv0)} = {(fv1 - fv0) * 12:.2f}\")  centre {(fu0 + fu1) / 2:.3f}")
        else:
            print(f"   cadre incomplet : {fu0} {fu1} {fv0} {fv1}")
        print(f"   meneaux {mene}  traverses {trav}")
        for c in sorted(g[4], key=lambda c: (-c[1], c[0])):
            print(f"      carreau {c[0]:7.3f}..{c[2]:7.3f} x Z {c[1]:7.3f}..{c[3]:7.3f}  ({(c[2] - c[0]) * 12:.1f}\" x {(c[3] - c[1]) * 12:.1f}\")")
