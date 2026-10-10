"""Carte des traits d'une zone, colorés par épaisseur. Usage : carte_traits.py VUE u0 v0 u1 v1 [px_par_pied] [nom]"""
import sys
from PIL import Image, ImageDraw, ImageFont
import outils_releve as O

vue = getattr(O, sys.argv[1].upper())
u0, v0, u1, v1 = (float(a) for a in sys.argv[2:6])
k = float(sys.argv[6]) if len(sys.argv) > 6 else 40.0
nom = sys.argv[7] if len(sys.argv) > 7 else f"carte_{vue.nom}_{u0:g}_{v0:g}.png"
COUL = {0: (150, 150, 150), 0.375: (0, 150, 0), 0.36: (0, 200, 200), 0.48: (0, 0, 255), 0.72: (0, 0, 0),
        0.84: (255, 140, 0), 1.08: (255, 0, 0), 1.56: (160, 0, 160), 1.68: (160, 0, 160), 2.04: (160, 0, 160)}
W, H = int(abs(u1 - u0) * k), int(abs(v1 - v0) * k)
im = Image.new("RGB", (W, H), (255, 255, 255))
dr = ImageDraw.Draw(im)
umin, vmax = min(u0, u1), max(v0, v1)
def P(u, v):
    return ((u - umin) * k, (vmax - v) * k)
for t, ua, va, ub, vb, w, c, f, s in vue.segments(u0, v0, u1, v1):
    col = COUL.get(w, (255, 0, 255))
    if t == "qu":
        pts = [vue.uv(s[8 + 2 * i], s[9 + 2 * i]) for i in range(4)]
        pts = [pts[0], pts[1], pts[3], pts[2]]
        dr.polygon([P(*p) for p in pts], outline=col)
    elif t == "re":
        dr.rectangle([P(min(ua, ub), max(va, vb)), P(max(ua, ub), min(va, vb))], outline=col)
    else:
        dr.line([P(ua, va), P(ub, vb)], fill=col, width=2 if w >= 1 else 1)
# grille
fnt = ImageFont.truetype("arial.ttf", 12)
import math
for u in range(math.ceil(min(u0, u1)), int(max(u0, u1)) + 1):
    x = (u - umin) * k
    dr.line([(x, 0), (x, H)], fill=(255, 200, 200) if u % 5 else (255, 120, 120))
    dr.text((x + 1, 1), f"{u}", fill=(200, 0, 0), font=fnt)
for v in range(math.ceil(min(v0, v1)), int(max(v0, v1)) + 1):
    y = (vmax - v) * k
    dr.line([(0, y), (W, y)], fill=(200, 200, 255) if v % 5 else (120, 120, 255))
    dr.text((1, y + 1), f"{v}", fill=(0, 0, 200), font=fnt)
im.save(O.ZOOMS / nom)
print(O.ZOOMS / nom, im.size)
