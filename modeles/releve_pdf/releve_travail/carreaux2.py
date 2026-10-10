"""Compter les barres de croisillons au-dessus et au-dessous du rail de rencontre d'une fenêtre.
Usage : python carreaux2.py VUE u0 v0 u1 v1 [nb_unites]
Les barres sont les éléments minces (qu/re/l de w<=0.31) ; une barre = 2 traits à < 0.08 pi.
"""
import sys
import outils_releve as O
vue = getattr(O, sys.argv[1].upper())
u0, v0, u1, v1 = (float(a) for a in sys.argv[2:6])
umin, umax = sorted((u0, u1)); vmin, vmax = sorted((v0, v1))
B = []
for s in O.traces(vue.page):
    if s[0] not in ("qu", "re", "l") or s[5] > 0.31:
        continue
    ua, va = vue.uv(s[1], s[2]); ub, vb = vue.uv(s[3], s[4])
    a0, a1 = sorted((ua, ub)); b0, b1 = sorted((va, vb))
    if umin <= a0 and a1 <= umax and vmin <= b0 and b1 <= vmax:
        B.append((a0, b0, a1, b1))
def grouper(vals):
    g = []
    for v in sorted(vals):
        if g and v - g[-1][-1] < 0.08: g[-1].append(v)
        else: g.append([v])
    return [round(sum(x)/len(x), 3) for x in g]
verts = [((b[0]+b[2])/2, b[1], b[3]) for b in B if (b[3]-b[1]) > 0.3 and (b[2]-b[0]) < 0.06]
hors = [((b[1]+b[3])/2, b[0], b[2]) for b in B if (b[2]-b[0]) > 0.3 and (b[3]-b[1]) < 0.06]
# regrouper les verticales par plage de Z
for nom, lst in (("V", verts), ("H", hors)):
    plages = {}
    for c, a, b in lst:
        k = (round(a, 1), round(b, 1))
        plages.setdefault(k, []).append(c)
    for k in sorted(plages):
        print(f"  {nom} plage {k} : barres à {grouper(plages[k])}")
