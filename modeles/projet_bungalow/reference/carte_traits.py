"""Carte des épaisseurs de trait : chaque classe de largeur dans sa couleur, sur fond blanc.

Usage : python carte_traits.py PAGE [X0 Y0 X1 Y1] [echelle_px_par_pt]
Écrit carte_pNN[_zone].png dans reference\\zooms\\ (lit reference\\pages\\traces_page_NN.json d'extraire_mots.py).
Modèle tiré de Maison_Bungalow_Blender\\reference\\carte_traits.py (voir modeles\\LISEZMOI.md).
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ICI = Path(__file__).resolve().parent
REF = ICI                     # dossier reference\ du projet (le projet d'origine avait ici un chemin en dur)
page = int(sys.argv[1])
zone = [float(v) for v in sys.argv[2:6]] if len(sys.argv) >= 6 else [0, 0, 792, 612]
k = float(sys.argv[6]) if len(sys.argv) > 6 else 2.5
traces = json.loads((REF / "pages" / f"traces_page_{page:02d}.json").read_text(encoding="utf-8"))

COUL = {
    0.24: (0, 170, 255),     # bleu clair
    0.36: (0, 200, 120),     # vert
    0.375: (150, 150, 150),  # gris
    0.48: (0, 120, 0),       # vert foncé
    0.72: (0, 0, 0),         # noir
    0.84: (255, 140, 0),     # orange
    1.08: (220, 0, 0),       # rouge
    1.56: (160, 0, 200),     # violet
    1.68: (255, 0, 255),     # magenta
    2.04: (120, 60, 0),      # brun
}
W = int((zone[2] - zone[0]) * k)
H = int((zone[3] - zone[1]) * k)
img = Image.new("RGB", (W, H), (255, 255, 255))
d = ImageDraw.Draw(img)


def P(x, y):
    return ((x - zone[0]) * k, (y - zone[1]) * k)


for s in traces:
    t, x0, y0, x1, y1, w = s[0], s[1], s[2], s[3], s[4], s[5]
    if w == 0:
        # surfaces pleines : on les montre en jaune pâle
        if t == "qu":
            c = s[8:16]
            pts = [P(c[0], c[1]), P(c[2], c[3]), P(c[6], c[7]), P(c[4], c[5])]
            d.polygon(pts, fill=(255, 230, 120))
        elif t == "re":
            d.rectangle([P(x0, y0), P(x1, y1)], fill=(255, 230, 120))
        else:
            d.line([P(x0, y0), P(x1, y1)], fill=(230, 200, 60), width=1)
        continue
    col = COUL.get(w, (255, 0, 0))
    lw = max(1, int(round(w * k * 0.9)))
    if t == "l" or t == "c":
        d.line([P(x0, y0), P(x1, y1)], fill=col, width=lw)
    elif t == "re":
        d.rectangle([P(x0, y0), P(x1, y1)], outline=col, width=lw)
    elif t == "qu":
        c = s[8:16]
        pts = [P(c[0], c[1]), P(c[2], c[3]), P(c[6], c[7]), P(c[4], c[5]), P(c[0], c[1])]
        d.line(pts, fill=col, width=lw)
# légende
y = 5
for w, col in COUL.items():
    d.rectangle([5, y, 25, y + 10], fill=col)
    d.text((30, y), f"{w} pt = {w * 0.3528:.3f} mm", fill=(0, 0, 0))
    y += 14
nom = f"carte_p{page:02d}" + ("" if len(sys.argv) < 6 else f"_{int(zone[0])}_{int(zone[1])}") + ".png"
(ICI / "zooms").mkdir(exist_ok=True)
img.save(ICI / "zooms" / nom)
print(nom, img.size)
