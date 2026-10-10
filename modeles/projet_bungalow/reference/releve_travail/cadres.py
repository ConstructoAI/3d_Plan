"""Traits d'une zone d'élévation (u, Z) regroupés : horizontaux et verticaux de largeur >= wmin et longueur >= lmin."""
import sys
import outils_releve as O
vue = getattr(O, sys.argv[1].upper())
u0, v0, u1, v1 = (float(a) for a in sys.argv[2:6])
wmin = float(sys.argv[6]) if len(sys.argv) > 6 else 0.7
lmin = float(sys.argv[7]) if len(sys.argv) > 7 else 0.4
wmax = float(sys.argv[8]) if len(sys.argv) > 8 else 3
H, V = [], []
for t, ua, va, ub, vb, w, c, f, s in vue.segments(u0, v0, u1, v1, types=("l", "qu"), wmin=wmin, wmax=wmax):
    if t == "qu":
        pts = [vue.uv(s[8 + 2 * i], s[9 + 2 * i]) for i in range(4)]
        us = [p[0] for p in pts]; vs = [p[1] for p in pts]
        print(f"  quad w={w} u {min(us):7.3f}..{max(us):7.3f}  Z {min(vs):7.3f}..{max(vs):7.3f}")
        continue
    L = ((ub - ua) ** 2 + (vb - va) ** 2) ** 0.5
    if L < lmin:
        continue
    if abs(vb - va) < 0.01:
        H.append((round(va, 3), round(min(ua, ub), 3), round(max(ua, ub), 3), w))
    elif abs(ub - ua) < 0.01:
        V.append((round(ua, 3), round(min(va, vb), 3), round(max(va, vb), 3), w))
print("H (Z ; u de .. à)")
for z, a, b, w in sorted(H, key=lambda h: (-h[0], h[1])):
    print(f"  Z={z:7.3f}  u {a:7.3f} .. {b:7.3f} (L {b - a:6.3f}) w={w}")
print("V (u ; Z de .. à)")
for u, a, b, w in sorted(V):
    print(f"  u={u:7.3f}  Z {a:7.3f} .. {b:7.3f} (L {b - a:6.3f}) w={w}")
