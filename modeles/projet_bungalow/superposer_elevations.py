"""Maison Bungalow — superpose les élévations du plan (traits en rouge) aux vues orthographiques du modèle.

Contrôle du § 6 de SAVOIR_LECTURE_PLANS.md : aucune ouverture, aucun niveau, aucune pente ne doit différer.
MODÈLE tiré de Maison_Bungalow_Blender (version finale du 2026-09-25 ; voir modeles\\LISEZMOI.md), lui-même copié
de Maison_Agrandissement_Blender\\superposer_elevations.py puis adapté (repères VUES du chef).
1. Rendre les vues orthographiques (caméras ortho_* de build_bungalow.py) avec le Blender portable ($env:BM_BLENDER) :
   & $env:BM_BLENDER -b --factory-startup `
       --python build_bungalow.py -- --sans-vegetation --no-json --render rendus\\controle `
       --engine eevee --res 1600x1200 --samples 8 --views ortho_facade,ortho_droit,ortho_arriere,ortho_gauche
2. python superposer_elevations.py   (Python du poste, outils\\python : PyMuPDF + Pillow)
   -> rendus\\controle\\superposition_{facade,droit,arriere,gauche}.png
Repère d'une élévation (parametres_bungalow.VUES) : x_pt = H0 + sens × h × ECH ; y_pt = Z0 − Z × ECH, en points
AFFICHÉS (page tournée comme à l'écran). La page est rendue entière puis découpée (aucune ambiguïté de rotation).
"""
import sys
from pathlib import Path

import fitz
from PIL import Image, ImageOps

sys.dont_write_bytecode = True
ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import parametres_bungalow as P  # noqa: E402

W, H = 1600, 1200
DOSSIER = ICI / "rendus" / "controle"
PDF = ICI / "reference" / "plan_maison_bungalow.pdf"
DPI = 600
# vue : (rendu du modèle, clé de P.VUES, centre h (pi), centre z (pi), largeur couverte (pi)) — ORTHO de build_bungalow.py
VUES = {
    "facade": ("ortho_facade.png", "FACADE", 22.0, 15.0, 62.0),
    "droit": ("ortho_droit.png", "DROIT", 19.0, 15.0, 66.0),
    "arriere": ("ortho_arriere.png", "ARRIERE", 22.0, 15.0, 62.0),
    "gauche": ("ortho_gauche.png", "GAUCHE", 19.0, 15.0, 66.0),
}


def main():
    doc = fitz.open(PDF)
    pages = {}
    ech = P.ECH_PT_PAR_PI
    for nom, (fic, cle, hc, zc, larg) in VUES.items():
        src = DOSSIER / fic
        if not src.exists():
            print("absent :", src)
            continue
        v = P.VUES[cle]
        haut = larg * H / W
        x0 = v["H0"] + v["sens"] * hc * ech - larg / 2 * ech
        x1 = x0 + larg * ech
        y0 = v["Z0"] - (zc + haut / 2) * ech
        y1 = y0 + haut * ech
        if v["page"] not in pages:
            pix = doc[v["page"] - 1].get_pixmap(dpi=DPI)
            pages[v["page"]] = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        k = DPI / 72.0
        plan = pages[v["page"]].crop((round(x0 * k), round(y0 * k), round(x1 * k), round(y1 * k))).resize((W, H))
        modele = Image.open(src).convert("RGB").resize((W, H))
        masque = ImageOps.grayscale(plan).point(lambda g: 255 if g < 150 else 0)
        fond = Image.blend(modele, Image.new("RGB", (W, H), "white"), 0.35)
        fond.paste(Image.new("RGB", (W, H), (230, 0, 0)), (0, 0), masque)
        out = DOSSIER / f"superposition_{nom}.png"
        fond.save(out)
        print(nom, "->", out)


if __name__ == "__main__":
    main()
