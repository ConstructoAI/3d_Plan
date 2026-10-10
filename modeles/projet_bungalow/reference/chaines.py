"""Lister les chaînes de cotes d'une page : tics regroupés, positions en pieds, textes de cote attribués.

Usage : python chaines.py PAGE X0 Y0 [ECH] [--h|--v]
  X0, Y0 : origine du repère en points affichés (plan : X0 = 205.86, Y0 = 505.14) ; ECH défaut 8.6013
  Une chaîne horizontale : ligne de cote fine à y constant, tics (petits traits obliques groupés) le long.
  Sortie : pour chaque chaîne, sa position (y en points et Y en pieds), puis les tics en X (pieds) et, entre deux
  tics, l'écart mesuré et le texte de cote trouvé au-dessus du segment.
"""
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

ICI = Path(__file__).resolve().parent
page = int(sys.argv[1])
X0, Y0 = float(sys.argv[2]), float(sys.argv[3])
ECH = float(sys.argv[4]) if len(sys.argv) > 4 and not sys.argv[4].startswith("--") else 8.6013
mode = [a for a in sys.argv if a in ("--h", "--v")]
tr = json.loads((ICI / "pages" / f"traces_page_{page:02d}.json").read_text(encoding="utf-8"))
mots = json.loads((ICI / "pages" / f"mots_page_{page:02d}.json").read_text(encoding="utf-8"))
COTE = re.compile(r"^\d+'-\d")


def pp(v):
    s = "-" if v < 0 else ""
    v = abs(v) * 12
    pi = int(v // 12)
    po = v - 12 * pi
    if po > 11.97:
        pi, po = pi + 1, 0.0
    return f"{s}{pi}'-{po:.2f}\""


# tics : petits traits obliques (0,5 à 6 pt), regroupés en amas connexes (union-find sur les milieux) ;
# le centre d'un tic = milieu de la boîte de TOUTES ses extrémités (un tic est symétrique autour du point coté).
tics = []
for s in tr:
    if s[0] != "l":
        continue
    L = math.hypot(s[3] - s[1], s[4] - s[2])
    if 0.5 < L < 6 and abs(s[3] - s[1]) > 0.3 and abs(s[4] - s[2]) > 0.3:
        tics.append(s)
parent = list(range(len(tics)))


def trouve(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


mil = [((s[1] + s[3]) / 2, (s[2] + s[4]) / 2) for s in tics]
grille = defaultdict(list)
for i, (x, y) in enumerate(mil):
    grille[(int(x // 3), int(y // 3))].append(i)
for i, (x, y) in enumerate(mil):
    gx, gy = int(x // 3), int(y // 3)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for j in grille[(gx + dx, gy + dy)]:
                if j > i and abs(mil[j][0] - x) < 1.6 and abs(mil[j][1] - y) < 1.6:
                    parent[trouve(i)] = trouve(j)
groupes = defaultdict(list)
for i in range(len(tics)):
    groupes[trouve(i)].append(tics[i])
centres = []
for g in groupes.values():
    if len(g) < 2:
        continue
    xs = [v for s in g for v in (s[1], s[3])]
    ys = [v for s in g for v in (s[2], s[4])]
    centres.append(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2))

# lignes de cote fines
horiz = defaultdict(list)
vert = defaultdict(list)
for s in tr:
    if s[0] != "l" or s[5] > 0.5:
        continue
    if abs(s[2] - s[4]) < 0.05 and abs(s[3] - s[1]) > 3:
        horiz[round(s[2], 1)].append((min(s[1], s[3]), max(s[1], s[3])))
    elif abs(s[1] - s[3]) < 0.05 and abs(s[4] - s[2]) > 3:
        vert[round(s[1], 1)].append((min(s[2], s[4]), max(s[2], s[4])))


def texte_pres(x, y, horizontal):
    best = None
    for m in mots:
        if not COTE.match(m[4]):
            continue
        cx, cy = (m[0] + m[2]) / 2, (m[1] + m[3]) / 2
        d = math.hypot(cx - x, cy - y)
        if d < 9 and (best is None or d < best[0]):
            best = (d, m[4])
    return best[1] if best else ""


if not mode or "--h" in mode:
    print("=== CHAÎNES HORIZONTALES (X en pieds) ===")
    for y, segs in sorted(horiz.items()):
        a, b = min(s[0] for s in segs), max(s[1] for s in segs)
        t = sorted(c[0] for c in centres if abs(c[1] - y) < 1.2 and a - 1.5 <= c[0] <= b + 1.5)
        if len(t) < 2:
            continue
        print(f"y={y:7.2f} pt (Y={(Y0 - y) / ECH:7.3f} pi) : tics X = " + ", ".join(pp((x - X0) / ECH) for x in t))
        for u, v in zip(t, t[1:]):
            print(f"      {pp((u - X0) / ECH):>11} → {pp((v - X0) / ECH):>11} : {pp((v - u) / ECH):>11}   "
                  f"écrit {texte_pres((u + v) / 2, y, True)}")
if not mode or "--v" in mode:
    print("=== CHAÎNES VERTICALES (Y en pieds) ===")
    for x, segs in sorted(vert.items()):
        a, b = min(s[0] for s in segs), max(s[1] for s in segs)
        t = sorted((c[1] for c in centres if abs(c[0] - x) < 1.2 and a - 1.5 <= c[1] <= b + 1.5), reverse=True)
        if len(t) < 2:
            continue
        print(f"x={x:7.2f} pt (X={(x - X0) / ECH:7.3f} pi) : tics Y = " + ", ".join(pp((Y0 - y) / ECH) for y in t))
        for u, v in zip(t, t[1:]):
            print(f"      {pp((Y0 - u) / ECH):>11} → {pp((Y0 - v) / ECH):>11} : {pp((u - v) / ECH):>11}   "
                  f"écrit {texte_pres(x, (u + v) / 2, False)}")
