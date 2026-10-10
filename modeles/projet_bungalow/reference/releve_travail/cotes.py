"""Cotes d'une vue en plan : texte écrit contre longueur mesurée entre les tics (Règle 5).

Usage : python cotes.py VUE [u0 v0 u1 v1]
Méthode : les lignes de cote sont des traits de 0,375 pt ; les tics d'architecte sont de petits parallélogrammes remplis
(traits de largeur 0). Pour chaque texte de cote (forme 12'-6", 8", 3'-91 2" = 3'-9 1/2"), on cherche la ligne de cote
parallèle la plus proche sous le texte, puis les deux tics qui l'encadrent.
"""
import math
import re
import sys
from collections import defaultdict

import outils_releve as O

RE_COTE = re.compile(r"^(\d+)'-(\d+)(?:(\d)(\d{1,2}))?\"?$|^(\d+)\"$")


def valeur(txt):
    t = txt.replace("''", '"').strip()
    m = re.match(r"^(\d+)'-(\d+)\"$", t)
    if m:
        return int(m.group(1)) + int(m.group(2)) / 12
    m = re.match(r"^(\d+)'-(\d+)(\d)$", t)  # fraction coupée : 3'-91 (puis « 2" » plus loin)
    if m:
        return None
    m = re.match(r"^(\d+)\"$", t)
    if m:
        return int(m.group(1)) / 12
    return None


def tics(vue, zone):
    """Centres des tics : milieu de la boîte de chaque grappe de traits de largeur 0 remplis (parallélogrammes)."""
    segs = []
    for t, ua, va, ub, vb, w, c, f, s in vue.segments(*zone, types=("l",)):
        if w == 0 and f is not None and math.hypot(ub - ua, vb - va) < 0.8:
            segs.append((ua, va, ub, vb))
    grappes = []   # [xmin, ymin, xmax, ymax, n]
    for ua, va, ub, vb in segs:
        cx, cy = (ua + ub) / 2, (va + vb) / 2
        for g in grappes:
            if g[0] - 0.3 <= cx <= g[2] + 0.3 and g[1] - 0.3 <= cy <= g[3] + 0.3:
                g[0] = min(g[0], ua, ub); g[1] = min(g[1], va, vb)
                g[2] = max(g[2], ua, ub); g[3] = max(g[3], va, vb); g[4] += 1
                break
        else:
            grappes.append([min(ua, ub), min(va, vb), max(ua, ub), max(va, vb), 1])
    return [((g[0] + g[2]) / 2, (g[1] + g[3]) / 2, g[4]) for g in grappes if g[4] >= 3]


def lignes_cote(vue, zone):
    """Lignes de cote (0,375 pt) fusionnées par coordonnée : une ligne coupée par son texte redevient une seule."""
    h, v = defaultdict(list), defaultdict(list)
    for t, ua, va, ub, vb, w, c, f, s in vue.segments(*zone, types=("l",), wmin=0.37, wmax=0.38):
        if abs(vb - va) < 0.01:
            h[round(va, 2)].append((min(ua, ub), max(ua, ub)))
        elif abs(ub - ua) < 0.01:
            v[round(ua, 2)].append((min(va, vb), max(va, vb)))

    def fusion(d):
        out = []
        for c, segs in d.items():
            segs.sort()
            a, b = segs[0]
            for x, y in segs[1:]:
                if x <= b + 2.5:   # trou du texte (au plus 2'-6")
                    b = max(b, y)
                else:
                    out.append((c, a, b))
                    a, b = x, y
            out.append((c, a, b))
        return out
    return fusion(h), fusion(v)


def cotes(vue, zone=(-40, -20, 80, 70)):
    T = tics(vue, zone)
    H, V = lignes_cote(vue, zone)
    out = []
    # regrouper les mots par ligne de texte
    g = defaultdict(list)
    for u, v, t, m in vue.mots(*zone):
        g[(m[5], m[6])].append(m)
    for k, ms in g.items():
        ms.sort(key=lambda m: (m[0], m[1]))
        x0 = min(m[0] for m in ms); y0 = min(m[1] for m in ms)
        x1 = max(m[2] for m in ms); y1 = max(m[3] for m in ms)
        txt = "".join(m[4] for m in ms)
        vert = (y1 - y0) > (x1 - x0)
        if vert:
            txt = "".join(m[4] for m in sorted(ms, key=lambda m: -m[1]))
        if not re.search(r"\d+'-\d+|^\d+\"$", txt):
            continue
        cu, cv = vue.uv((x0 + x1) / 2, (y0 + y1) / 2)
        cand = []
        if not vert:
            for y, a, b in H:
                if a - 0.2 <= cu <= b + 0.2 and abs(y - cv) < 0.9:
                    cand.append((abs(y - cv), y, a, b))
        else:
            for x, a, b in V:
                if a - 0.2 <= cv <= b + 0.2 and abs(x - cu) < 0.9:
                    cand.append((abs(x - cu), x, a, b))
        if not cand:
            out.append((txt, vert, cu, cv, None, None, None, valeur(txt)))
            continue
        cand.sort()
        _, c0, a, b = cand[0]
        if not vert:
            sur = sorted(t[0] for t in T if abs(t[1] - c0) < 0.2 and a - 0.3 <= t[0] <= b + 0.3)
            g_ = [s for s in sur if s < cu]
            d_ = [s for s in sur if s > cu]
        else:
            sur = sorted(t[1] for t in T if abs(t[0] - c0) < 0.2 and a - 0.3 <= t[1] <= b + 0.3)
            g_ = [s for s in sur if s < cv]
            d_ = [s for s in sur if s > cv]
        if g_ and d_:
            out.append((txt, vert, cu, cv, c0, g_[-1], d_[0], valeur(txt)))
        else:
            out.append((txt, vert, cu, cv, c0, None, None, valeur(txt)))
    return out


if __name__ == "__main__":
    vue = getattr(O, sys.argv[1].upper())
    zone = [float(a) for a in sys.argv[2:6]] if len(sys.argv) >= 6 else [-40, -20, 80, 70]
    for txt, vert, cu, cv, c0, a, b, val in sorted(cotes(vue, zone), key=lambda r: (r[1], -r[3], r[2])):
        if a is None:
            print(f"{'V' if vert else 'H'} {txt:>10}  au ({cu:6.2f}, {cv:6.2f})  ligne {c0}  -> tics non trouvés")
            continue
        L = b - a
        ecart = "" if val is None else f"écart {(L - val) * 12:+.2f}\""
        axe = "Y" if vert else "X"
        print(f"{'V' if vert else 'H'} {txt:>10}  ligne {'X' if vert else 'Y'}={c0:7.3f}  {axe} {a:7.3f} -> {b:7.3f}  "
              f"mesuré {O.pi_po(L):>12}  {ecart}")
