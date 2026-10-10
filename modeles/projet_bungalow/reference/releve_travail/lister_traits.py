"""Lister les traits d'une vue filtrés par largeur : lister_traits.py VUE wmin wmax [u0 v0 u1 v1] [lmin]"""
import sys
import outils_releve as O
vue = getattr(O, sys.argv[1].upper())
wmin, wmax = float(sys.argv[2]), float(sys.argv[3])
z = [float(a) for a in sys.argv[4:8]] if len(sys.argv) >= 8 else [-40, -20, 80, 70]
lmin = float(sys.argv[8]) if len(sys.argv) > 8 else 0.0
H, V, A = [], [], []
for t, ua, va, ub, vb, w, c, f, s in vue.segments(*z, wmin=wmin, wmax=wmax):
    L = ((ub - ua) ** 2 + (vb - va) ** 2) ** 0.5
    if L < lmin:
        continue
    if t == "qu":
        A.append(("qu", [round(vue.uv(s[8 + 2 * i], s[9 + 2 * i])[j], 3) for i in range(4) for j in range(2)], w))
        continue
    if abs(vb - va) < 0.01:
        H.append((round(va, 3), round(min(ua, ub), 3), round(max(ua, ub), 3), w, t))
    elif abs(ub - ua) < 0.01:
        V.append((round(ua, 3), round(min(va, vb), 3), round(max(va, vb), 3), w, t))
    else:
        A.append((t, (round(ua, 3), round(va, 3), round(ub, 3), round(vb, 3)), w))
print("HORIZONTAUX (Y ; X de .. à ; largeur)")
for y, a, b, w, t in sorted(H):
    print(f"  Y={y:8.3f}  X {a:8.3f} .. {b:8.3f}  (L {b - a:6.3f})  w={w} {t}")
print("VERTICAUX (X ; Y de .. à)")
for x, a, b, w, t in sorted(V):
    print(f"  X={x:8.3f}  Y {a:8.3f} .. {b:8.3f}  (L {b - a:6.3f})  w={w} {t}")
print("AUTRES")
for a in A:
    print("  ", a)
