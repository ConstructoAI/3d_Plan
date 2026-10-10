"""Compter les carreaux (croisillons) d'une fenêtre d'élévation.

Usage : python carreaux.py VUE u0 v0 u1 v1
Cherche les châssis (quadrilatères w=0.54 de plus de 0.8 pi) et les barres minces (w<=0.3, largeur < 0.06 pi)
dans la zone, puis compte, pour chaque châssis « feuille » (qui ne contient pas d'autre châssis),
le nombre de colonnes et de rangées de carreaux.
"""
import sys

import outils_releve as O


def analyse(vue, u0, v0, u1, v1, bavard=True):
    umin, umax = sorted((u0, u1))
    vmin, vmax = sorted((v0, v1))
    Q = []
    for s in O.traces(vue.page):
        if s[0] not in ("qu", "re", "l"):
            continue
        ua, va = vue.uv(s[1], s[2])
        ub, vb = vue.uv(s[3], s[4])
        a0, a1 = sorted((ua, ub))
        b0, b1 = sorted((va, vb))
        if umin - 0.01 <= a0 and a1 <= umax + 0.01 and vmin - 0.01 <= b0 and b1 <= vmax + 0.01:
            Q.append((s[0], a0, b0, a1, b1, s[5]))
    chassis = [q for q in Q if q[0] in ("qu", "re") and q[5] >= 0.5 and (q[3] - q[1]) > 0.8 and (q[4] - q[2]) > 0.5]
    # dédoublonner
    uniq = []
    for c in chassis:
        if not any(abs(c[1] - d[1]) < 0.01 and abs(c[2] - d[2]) < 0.01 and abs(c[3] - d[3]) < 0.01
                   and abs(c[4] - d[4]) < 0.01 for d in uniq):
            uniq.append(c)
    chassis = uniq

    def contient(a, b):
        return a[1] <= b[1] + 0.005 and a[2] <= b[2] + 0.005 and a[3] >= b[3] - 0.005 and a[4] >= b[4] - 0.005

    feuilles = [c for c in chassis if not any(d is not c and contient(c, d) and
                                              ((d[3] - d[1]) * (d[4] - d[2]) < 0.9 * (c[3] - c[1]) * (c[4] - c[2]))
                                              for d in chassis)]
    barres = [q for q in Q if q[5] <= 0.31 and (min(q[3] - q[1], q[4] - q[2]) < 0.06)]
    res = []
    for f in sorted(feuilles, key=lambda c: (-c[4], c[1])):
        dedans = [b for b in barres if contient(f, b)]
        nv = len({round((b[1] + b[3]) / 2, 2) for b in dedans if (b[4] - b[2]) > (b[3] - b[1]) and (b[4] - b[2]) > 0.3})
        nh = len({round((b[2] + b[4]) / 2, 2) for b in dedans if (b[3] - b[1]) > (b[4] - b[2]) and (b[3] - b[1]) > 0.3})
        # une barre = deux traits parallèles rapprochés : regrouper à 0.06 pi
        xs = sorted({round((b[1] + b[3]) / 2, 3) for b in dedans if (b[4] - b[2]) > (b[3] - b[1]) and (b[4] - b[2]) > 0.3})
        ys = sorted({round((b[2] + b[4]) / 2, 3) for b in dedans if (b[3] - b[1]) > (b[4] - b[2]) and (b[3] - b[1]) > 0.3})

        def grouper(vals):
            g = []
            for v in vals:
                if g and v - g[-1][-1] < 0.08:
                    g[-1].append(v)
                else:
                    g.append([v])
            return len(g)

        nv, nh = grouper(xs), grouper(ys)
        res.append((f, nv + 1, nh + 1))
        if bavard:
            print(f"  châssis {vue.nom_u} {f[1]:7.3f}..{f[3]:7.3f}  Z {f[2]:7.3f}..{f[4]:7.3f} "
                  f"({O.pi_po(f[3] - f[1])} x {O.pi_po(f[4] - f[2])}) : {nv + 1} col. x {nh + 1} rangée(s)")
    return res


if __name__ == "__main__":
    vue = getattr(O, sys.argv[1].upper())
    analyse(vue, *(float(a) for a in sys.argv[2:6]))
