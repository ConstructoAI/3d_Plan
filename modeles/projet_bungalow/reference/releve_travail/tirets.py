"""Lignes en tirets d'une vue : grappes de petits traits colinéaires (horizontaux ou verticaux).

Usage : python tirets.py VUE wmin wmax u0 v0 u1 v1 [lmax_trait] [n_min] [trou_max]
Sortie : orientation, coordonnée, étendue, nombre de tirets, longueur moyenne d'un tiret et du pas.
"""
import sys
from collections import defaultdict

import outils_releve as O


def tirets(vue, wmin, wmax, zone, lmax=1.2, nmin=4, trou=1.2):
    h, v = defaultdict(list), defaultdict(list)
    for t, ua, va, ub, vb, w, c, f, s in vue.segments(*zone, types=("l",), wmin=wmin, wmax=wmax):
        L = ((ub - ua) ** 2 + (vb - va) ** 2) ** 0.5
        if L > lmax:
            continue
        if abs(vb - va) < 0.005:
            h[round(va, 2)].append((min(ua, ub), max(ua, ub)))
        elif abs(ub - ua) < 0.005:
            v[round(ua, 2)].append((min(va, vb), max(va, vb)))
    out = []
    for nom, d in (("H", h), ("V", v)):
        for c, segs in d.items():
            segs.sort()
            groupe = [segs[0]]
            for s in segs[1:]:
                if s[0] - groupe[-1][1] <= trou:
                    groupe.append(s)
                else:
                    if len(groupe) >= nmin:
                        out.append((nom, c, groupe))
                    groupe = [s]
            if len(groupe) >= nmin:
                out.append((nom, c, groupe))
    return out


if __name__ == "__main__":
    vue = getattr(O, sys.argv[1].upper())
    wmin, wmax = float(sys.argv[2]), float(sys.argv[3])
    zone = [float(a) for a in sys.argv[4:8]]
    lmax = float(sys.argv[8]) if len(sys.argv) > 8 else 1.2
    nmin = int(sys.argv[9]) if len(sys.argv) > 9 else 4
    trou = float(sys.argv[10]) if len(sys.argv) > 10 else 1.2
    for nom, c, g in sorted(tirets(vue, wmin, wmax, zone, lmax, nmin, trou)):
        lm = sum(b - a for a, b in g) / len(g)
        pas = (g[-1][0] - g[0][0]) / (len(g) - 1) if len(g) > 1 else 0
        print(f"{nom} {'Y' if nom == 'H' else 'X'}={c:8.3f}  de {g[0][0]:8.3f} à {g[-1][1]:8.3f}  "
              f"({len(g):3d} tirets de {lm:.3f}, pas {pas:.3f})")
