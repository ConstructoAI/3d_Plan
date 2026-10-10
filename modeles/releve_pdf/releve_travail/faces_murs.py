"""Lister les segments alignés sur une face de mur (plan), pour trouver les baies (interruptions).

Usage : python faces_murs.py VUE H|V COORD [tol] [a0 a1] [lmin]
  H COORD : lignes horizontales à Y = COORD (pieds) ; V : lignes verticales à X = COORD.
  a0 a1 : étendue le long du mur ; lmin : longueur minimale (défaut 0.05 pi)
"""
import sys

import outils_releve as O

vue = getattr(O, sys.argv[1].upper())
sens = sys.argv[2].upper()
c = float(sys.argv[3])
tol = float(sys.argv[4]) if len(sys.argv) > 4 else 0.02
a0, a1 = (float(sys.argv[5]), float(sys.argv[6])) if len(sys.argv) > 6 else (-1e9, 1e9)
lmin = float(sys.argv[7]) if len(sys.argv) > 7 else 0.05

res = []
for s in O.traces(vue.page):
    if s[0] not in ("l",):
        continue
    ua, va = vue.uv(s[1], s[2])
    ub, vb = vue.uv(s[3], s[4])
    if sens == "H" and abs(va - vb) < 0.004 and abs(va - c) <= tol:
        lo, hi = sorted((ua, ub))
        if hi >= a0 and lo <= a1 and hi - lo >= lmin:
            res.append((lo, hi, va, s[5], s[6]))
    if sens == "V" and abs(ua - ub) < 0.004 and abs(ua - c) <= tol:
        lo, hi = sorted((va, vb))
        if hi >= a0 and lo <= a1 and hi - lo >= lmin:
            res.append((lo, hi, ua, s[5], s[6]))
for lo, hi, k, w, col in sorted(set((round(a, 3), round(b, 3), round(k, 3), w, tuple(col) if col else None)
                                    for a, b, k, w, col in res)):
    print(f"  {lo:8.3f} .. {hi:8.3f}  (L {O.pi_po(hi - lo)})  à {k:8.3f}  w={w} col={col}")
