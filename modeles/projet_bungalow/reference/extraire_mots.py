"""Extraire les mots et les tracés vectoriels de chaque page en JSON, dans le repère AFFICHÉ.

Les pages de ce PDF sont tournées de 270° (format Lettre à l'italienne, 792 x 612 pt affichés).
PyMuPDF rend les mots et les tracés dans le repère NON tourné (612 x 792) : on les ramène ici au repère
affiché avec page.rotation_matrix, pour qu'ils tombent sur les aperçus (page_NN_180.png : 1 pt = 2,5 px).

Écrit reference/pages/mots_page_NN.json : [x0, y0, x1, y1, "mot", bloc, ligne, rang] en points affichés
et reference/pages/traces_page_NN.json : segments [type, x0, y0, x1, y1, largeur, couleur, remplissage]
(type l = ligne, re = rectangle, c = courbe de Bézier (extrémités), qu = quadrilatère : 4 coins
x_ul, y_ul, x_ur, y_ur, x_ll, y_ll, x_lr, y_lr après la couleur et le remplissage).
Origine en haut à gauche, y vers le bas. L'échelle se mesure sur les cotes (≈ 8,6 pt par pied ici).
"""
import json
from pathlib import Path

import fitz

ICI = Path(__file__).resolve().parent
from plan_pdf import chemin_pdf  # noqa: E402  (PLAN_PDF, sinon l'unique .pdf de ce dossier)
PDF = chemin_pdf(ICI)
SORTIE = ICI / "pages"
SORTIE.mkdir(exist_ok=True)


def pt(p, m):
    q = fitz.Point(p) * m
    return round(q.x, 3), round(q.y, 3)


doc = fitz.open(PDF)
for i, page in enumerate(doc):
    m = page.rotation_matrix
    mots = []
    for w in page.get_text("words"):
        r = fitz.Rect(w[:4]) * m
        mots.append([round(r.x0, 2), round(r.y0, 2), round(r.x1, 2), round(r.y1, 2), w[4], w[5], w[6], w[7]])
    (SORTIE / f"mots_page_{i + 1:02d}.json").write_text(json.dumps(mots, ensure_ascii=False), encoding="utf-8")
    segments = []
    for d in page.get_drawings():
        largeur = d.get("width") or 0
        couleur = d.get("color")
        rempl = d.get("fill")
        for item in d["items"]:
            if item[0] == "l":
                (a, b), (c, e) = pt(item[1], m), pt(item[2], m)
                segments.append(["l", a, b, c, e, round(largeur, 3), couleur, rempl])
            elif item[0] == "re":
                r = fitz.Rect(item[1]) * m
                segments.append(["re", round(r.x0, 3), round(r.y0, 3), round(r.x1, 3), round(r.y1, 3),
                                 round(largeur, 3), couleur, rempl])
            elif item[0] == "c":
                (a, b), (c, e) = pt(item[1], m), pt(item[4], m)
                segments.append(["c", a, b, c, e, round(largeur, 3), couleur, rempl])
            elif item[0] == "qu":
                qd = item[1]
                coins = [v for p in (qd.ul, qd.ur, qd.ll, qd.lr) for v in pt(p, m)]
                bx = fitz.Rect(qd.rect) * m
                segments.append(["qu", round(bx.x0, 3), round(bx.y0, 3), round(bx.x1, 3), round(bx.y1, 3),
                                 round(largeur, 3), couleur, rempl] + coins)
    (SORTIE / f"traces_page_{i + 1:02d}.json").write_text(json.dumps(segments), encoding="utf-8")
    print(f"page {i + 1} : {len(mots)} mots, {len(segments)} segments")
