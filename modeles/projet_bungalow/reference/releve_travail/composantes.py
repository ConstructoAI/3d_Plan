"""Composantes connexes des traits fins d'une vue (appareils, meubles, marches, battants).

Usage : python composantes.py VUE wmin wmax u0 v0 u1 v1 [tol] [nmin]
Deux traits sont reliés si un bout de l'un est à moins de `tol` pied d'un point de l'autre (bouts seulement).
Affiche la boîte et le nombre de traits de chaque composante, triées par Y décroissant puis X.
"""
import math
import sys

import outils_releve as O


def composantes(vue, wmin, wmax, zone, tol=0.03, types=("l", "qu", "re")):
    segs = []
    for t, ua, va, ub, vb, w, c, f, s in vue.segments(*zone, types=types, wmin=wmin, wmax=wmax):
        if t == "qu":
            pts = [vue.uv(s[8 + 2 * i], s[9 + 2 * i]) for i in range(4)]
            pts = [pts[0], pts[1], pts[3], pts[2]]
            for i in range(4):
                segs.append((pts[i][0], pts[i][1], pts[(i + 1) % 4][0], pts[(i + 1) % 4][1], w))
        elif t == "re":
            segs += [(ua, va, ub, va, w), (ub, va, ub, vb, w), (ub, vb, ua, vb, w), (ua, vb, ua, va, w)]
        else:
            segs.append((ua, va, ub, vb, w))
    n = len(segs)
    parent = list(range(n))

    def f(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    # grille spatiale sur les bouts
    cell = {}
    for i, (a, b, c, d, w) in enumerate(segs):
        for (x, y) in ((a, b), (c, d)):
            cell.setdefault((round(x / tol), round(y / tol)), []).append(i)
    for (cx, cy), lst in cell.items():
        voisins = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                voisins += cell.get((cx + dx, cy + dy), [])
        for j in voisins:
            ri, rj = f(lst[0]), f(j)
            if ri != rj:
                parent[ri] = rj
        for j in lst[1:]:
            ri, rj = f(lst[0]), f(j)
            if ri != rj:
                parent[ri] = rj
    comp = {}
    for i in range(n):
        comp.setdefault(f(i), []).append(segs[i])
    out = []
    for k, ss in comp.items():
        xs = [p for s in ss for p in (s[0], s[2])]
        ys = [p for s in ss for p in (s[1], s[3])]
        L = sum(math.hypot(s[2] - s[0], s[3] - s[1]) for s in ss)
        ws = sorted(set(s[4] for s in ss))
        out.append((min(xs), min(ys), max(xs), max(ys), len(ss), L, ws))
    return out


if __name__ == "__main__":
    vue = getattr(O, sys.argv[1].upper())
    wmin, wmax = float(sys.argv[2]), float(sys.argv[3])
    zone = [float(a) for a in sys.argv[4:8]]
    tol = float(sys.argv[8]) if len(sys.argv) > 8 else 0.03
    nmin = int(sys.argv[9]) if len(sys.argv) > 9 else 2
    res = composantes(vue, wmin, wmax, zone, tol)
    for x0, y0, x1, y1, n, L, ws in sorted(res, key=lambda r: (-round(r[3]), r[0])):
        if n < nmin:
            continue
        print(f"X {x0:7.3f}..{x1:7.3f}  Y {y0:7.3f}..{y1:7.3f}  ({x1 - x0:5.2f} x {y1 - y0:5.2f})  {n:4d} traits  L={L:6.1f}  w={ws}")
