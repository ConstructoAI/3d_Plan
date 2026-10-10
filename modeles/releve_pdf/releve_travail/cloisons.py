"""Détecter les cloisons d'un plan : paires de traits parallèles (w >= wmin) espacés de 0,25 à 0,75 pi.

Usage : python cloisons.py VUE u0 v0 u1 v1 [wmin] [wmax]
Sortie : une ligne par cloison (sens, axe, épaisseur, étendue), fusionnées quand elles se prolongent.
"""
import sys

import outils_releve as O


def detecter(vue, zone, wmin=0.95, wmax=1.1, emin=0.25, emax=0.75, recouvre_min=0.15):
    segs = vue.segments(*zone, types=("l",))
    H, V = [], []
    for t, a, b, c, d, w, col, f in segs:
        if not (wmin <= w <= wmax):
            continue
        if abs(b - d) < 0.004 and abs(c - a) > 0.1:
            H.append((b, min(a, c), max(a, c)))
        elif abs(a - c) < 0.004 and abs(d - b) > 0.1:
            V.append((a, min(b, d), max(b, d)))
    murs = []
    for sens, L in (("H", H), ("V", V)):
        L = sorted(set((round(k, 3), round(p, 3), round(q, 3)) for k, p, q in L))
        for i, (k1, p1, q1) in enumerate(L):
            for k2, p2, q2 in L[i + 1:]:
                e = k2 - k1
                if e < emin:
                    continue
                if e > emax:
                    break
                lo, hi = max(p1, p2), min(q1, q2)
                if hi - lo >= recouvre_min:
                    murs.append((sens, round((k1 + k2) / 2, 3), round(e, 3), round(lo, 3), round(hi, 3)))
    # fusion des morceaux colinéaires qui se touchent
    murs.sort()
    fus = []
    for m in murs:
        if fus and fus[-1][0] == m[0] and abs(fus[-1][1] - m[1]) < 0.01 and abs(fus[-1][2] - m[2]) < 0.01 \
                and m[3] <= fus[-1][4] + 0.02:
            s, k, e, lo, hi = fus[-1]
            fus[-1] = (s, k, e, lo, max(hi, m[4]))
        else:
            fus.append(m)
    return fus


if __name__ == "__main__":
    vue = getattr(O, sys.argv[1].upper())
    zone = [float(a) for a in sys.argv[2:6]]
    wmin = float(sys.argv[6]) if len(sys.argv) > 6 else 0.95
    wmax = float(sys.argv[7]) if len(sys.argv) > 7 else 1.1
    for s, k, e, lo, hi in detecter(vue, zone, wmin, wmax):
        ax = "Y" if s == "H" else "X"
        le = "X" if s == "H" else "Y"
        print(f"  {s} axe {ax}={k:7.3f} ép. {O.pi_po(e):>10}  {le} {lo:7.3f} -> {hi:7.3f}  (L {O.pi_po(hi - lo)})")
