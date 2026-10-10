r"""Maison Bungalow — planche de présentation des rendus : rendus\planche_rendus.png.

Mise en page équilibrée, sans rangée d'une seule image : en-tête (projet, adresse, date, avertissement), 2 grandes vues
(vue principale et crépuscule), puis 2 rangées de 4 vues. Les rendus viennent de build_bungalow.py (Cycles 1600 x 1200).
MODÈLE tiré de Maison_Bungalow_Blender\planche_rendus.py (version finale du 2026-09-25 ; voir modeles\LISEZMOI.md) :
adresse des travaux remplacée par un gabarit ; polices Arial prises dans %SystemRoot%\Fonts (aucun chemin en dur).
Usage : python planche_rendus.py [--date AAAA-MM-JJ]
"""
import argparse
import datetime
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.dont_write_bytecode = True
ICI = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(ICI, "rendus")
GRANDES = [("avant_3q", "Vue principale, 3/4 avant"), ("crepuscule", "Crépuscule")]
PETITES = [("facade", "Façade avant"), ("droit", "Côté droit (cheminée)"), ("arriere", "Arrière (patio couvert)"),
           ("gauche", "Côté gauche (garage)"), ("arriere_3q", "3/4 arrière"), ("aerienne", "Vue aérienne"),
           ("coupe_rdc", "Plan 3D du rez-de-chaussée"), ("coupe_ss", "Plan 3D du sous-sol")]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre",
        "décembre"]

W = 2400                    # largeur de la planche
MARGE, GOUT = 40, 24        # marge extérieure, gouttière entre les vues
LEG = 46                    # hauteur de la légende sous chaque vue
ENCRE, GRIS, FOND = (28, 30, 34), (96, 100, 108), (255, 255, 255)


def police(nom, taille):
    for f in (nom, os.path.join(os.environ.get("SystemRoot") or os.environ.get("WINDIR", ""), "Fonts", nom)):
        try:
            return ImageFont.truetype(f, taille)
        except OSError:
            continue
    return ImageFont.load_default()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    a = ap.parse_args()
    d = datetime.date.fromisoformat(a.date)
    date_txt = f"{d.day} {MOIS[d.month - 1]} {d.year}"
    manquants = [v for v, _ in GRANDES + PETITES if not os.path.exists(os.path.join(R, v + ".png"))]
    if manquants:
        sys.exit(f"rendus absents : {manquants}")
    f_titre, f_sous, f_note = police("arialbd.ttf", 46), police("arial.ttf", 28), police("ariali.ttf", 26)
    f_leg = police("arial.ttf", 26)
    lg = (W - 2 * MARGE - GOUT) // 2                 # grandes vues : 2 par rangée
    hg = lg * 3 // 4
    lp = (W - 2 * MARGE - 3 * GOUT) // 4             # petites vues : 4 par rangée
    hp = lp * 3 // 4
    H_TETE = 228
    H = MARGE + H_TETE + (hg + LEG) + GOUT + 2 * (hp + LEG) + GOUT + MARGE
    im = Image.new("RGB", (W, H), FOND)
    dr = ImageDraw.Draw(im)
    # en-tête
    y = MARGE
    dr.text((MARGE, y), "Maison Bungalow : bungalow neuf sur sous-sol fini, garage attaché", fill=ENCRE,
            font=f_titre)
    y += 64
    dr.text((MARGE, y), "<adresse des travaux>   ·   plans du technologue, révision 1 du "
            "24 août 2026   ·   illustrations du " + date_txt, fill=GRIS, font=f_sous)
    y += 44
    dr.text((MARGE, y), "Illustrations indicatives ; contexte, mobilier et luminaires non prévus au plan.", fill=ENCRE,
            font=f_note)
    y += 38
    dr.text((MARGE, y), "Couleurs d'après la perspective de la page 1 (au choix du propriétaire au plan). Modèle 3D "
            "fait par IA d'après les plans, à valider par un professionnel.", fill=GRIS, font=f_note)
    y = MARGE + H_TETE - 18
    dr.line((MARGE, y, W - MARGE, y), fill=(200, 202, 206), width=3)
    y = MARGE + H_TETE

    def vue(nom, titre, x, y, l, h):
        im.paste(Image.open(os.path.join(R, nom + ".png")).convert("RGB").resize((l, h), Image.LANCZOS), (x, y))
        dr.text((x + 4, y + h + 10), titre, fill=ENCRE, font=f_leg)

    for i, (nom, titre) in enumerate(GRANDES):
        vue(nom, titre, MARGE + i * (lg + GOUT), y, lg, hg)
    y += hg + LEG + GOUT
    for r in range(2):
        for c in range(4):
            nom, titre = PETITES[r * 4 + c]
            vue(nom, titre, MARGE + c * (lp + GOUT), y, lp, hp)
        y += hp + LEG + GOUT
    out = os.path.join(R, "planche_rendus.png")
    im.save(out)
    print(out, im.size)


if __name__ == "__main__":
    main()
