"""Extraire les mots et les tracés vectoriels de chaque page en JSON.

Écrit reference/pages/mots_page_NN.json : [x0, y0, x1, y1, "mot", bloc, ligne, rang] en points PDF
et reference/pages/traces_page_NN.json : segments (x0, y0, x1, y1, largeur, couleur, remplissage).
Les coordonnées sont en points (1/72 po), origine en haut à gauche, y vers le bas.
À l'échelle 1/4" = 1'-0", 18 points = 1 pied.
⚠️ Page tournée (page.rotation ≠ 0) : ces coordonnées sont dans le repère NON tourné ; la version adaptée
aux pages tournées est celle de Maison_Bungalow_Blender\\reference\\ (voir modeles\\LISEZMOI.md).
Le PDF : variable PLAN_PDF, sinon l'unique .pdf de ce dossier (voir plan_pdf.py).
"""
import json
from pathlib import Path

import fitz

from plan_pdf import chemin_pdf

ICI = Path(__file__).resolve().parent
PDF = chemin_pdf(ICI)
SORTIE = ICI / "pages"
SORTIE.mkdir(exist_ok=True)

doc = fitz.open(PDF)
for i, page in enumerate(doc):
    mots = page.get_text("words")
    (SORTIE / f"mots_page_{i + 1:02d}.json").write_text(
        json.dumps([[round(m[0], 2), round(m[1], 2), round(m[2], 2), round(m[3], 2), m[4], m[5], m[6], m[7]] for m in mots],
                   ensure_ascii=False),
        encoding="utf-8",
    )
    segments = []
    for d in page.get_drawings():
        largeur = d.get("width") or 0
        couleur = d.get("color")
        rempl = d.get("fill")
        for item in d["items"]:
            if item[0] == "l":
                p, q = item[1], item[2]
                segments.append(["l", round(p.x, 3), round(p.y, 3), round(q.x, 3), round(q.y, 3),
                                 round(largeur, 3), couleur, rempl])
            elif item[0] == "re":
                r = item[1]
                segments.append(["re", round(r.x0, 3), round(r.y0, 3), round(r.x1, 3), round(r.y1, 3),
                                 round(largeur, 3), couleur, rempl])
            elif item[0] == "c":
                p, q = item[1], item[4]
                segments.append(["c", round(p.x, 3), round(p.y, 3), round(q.x, 3), round(q.y, 3),
                                 round(largeur, 3), couleur, rempl])
            elif item[0] == "qu":
                qd = item[1]
                segments.append(["qu", round(qd.ul.x, 3), round(qd.ul.y, 3), round(qd.lr.x, 3), round(qd.lr.y, 3),
                                 round(largeur, 3), couleur, rempl])
    (SORTIE / f"traces_page_{i + 1:02d}.json").write_text(json.dumps(segments), encoding="utf-8")
    print(f"page {i + 1} : {len(mots)} mots, {len(segments)} segments")
