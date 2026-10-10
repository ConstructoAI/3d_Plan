# -*- coding: utf-8 -*-
r"""Comparaison du rendu de la caméra « photo » avec la PHOTO : côte à côte, superposition et IoU des silhouettes.

MODÈLE tiré de Bruleur_Natcom_Blender\comparaison_photo.py (2026-09-24 ; voir modeles\LISEZMOI.md), rendu GÉNÉRIQUE :
  - la photo : --photo, sinon photo.py (variable PHOTO, sinon l'unique .jpg de reference\ du projet) ;
  - le masque de la photo (objet = NOIR sur blanc) : --masque-photo MASQUE.png, fait à la main ou par un autre script, pour
    une photo d'extérieur (ciel, gazon, arbres) ; sinon le masque AUTOMATIQUE d'un fond clair et neutre relié au bord de
    l'image (photo de catalogue sur fond blanc : le cas du brûleur), réglé par --fond-lum et --fond-sat, et par --sol-y,
    --sol-lum, --sol-sat pour l'ombre douce du sol (brûleur : --sol-y 480 --sol-lum 160 --sol-sat 12) ;
  - la silhouette du modèle : --silhouette RENDU.png, le rendu de la caméra « photo » en émission noire sur fond blanc
    (view_layer.material_override, monde blanc, 1 échantillon ; CLAUDE.md, « Pièges vérifiés — rendu »).
Python du poste (Pillow, numpy, scipy) ; aucun outil lancé : pas d'amorce outils\chemins.py.
Rappel (CLAUDE.md) : l'IoU des silhouettes ne voit PAS les défauts intérieurs (une plaque masquait la volute avec une IoU de
0,92) : toujours ajouter controle_reperes.py.
Usage : python comparaison_photo.py RENDU_PHOTO.png [--silhouette S.png] [--masque-photo M.png] [--photo P.jpg]
                                    [--sortie DOSSIER] [--suffixe s] [--zone x0,y0,x1,y1]
Écrit dans --sortie (défaut : rendus\ à côté de ce script) : comparaison_photo.png (côte à côte, x 2),
superposition_photo.png (rendu à 50 % sur la photo, contour de la photo en VERT, du modèle en ROUGE), _masque_photo.png
et, avec --silhouette, ecarts_silhouette.png (vert = photo seule, rouge = modèle seul) ; l'IoU est affiché.
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ICI = os.path.dirname(os.path.abspath(__file__))


def trouver_photo(choix):
    """--photo, sinon photo.py de reference\\ (ou de ce dossier) : variable PHOTO, sinon l'unique .jpg du dossier."""
    if choix:
        return os.path.abspath(choix)
    for d in (os.path.join(ICI, "reference"), ICI):
        if os.path.isfile(os.path.join(d, "photo.py")):
            sys.path.insert(0, d)
            from photo import chemin_photo
            return str(chemin_photo(d))
    raise SystemExit("photo.py introuvable (dans reference\\ ou à côté de ce script) : passer --photo PHOTO.jpg")


def masque_photo(photo, a):
    """Objet = tout ce qui n'est pas le fond clair et neutre relié au bord (photo de catalogue sur fond blanc)."""
    im = np.asarray(Image.open(photo).convert("RGB")).astype(float)
    lum = im.mean(axis=2)
    sat = im.max(axis=2) - im.min(axis=2)
    clair = (lum > a.fond_lum) & (sat < a.fond_sat)
    if a.sol_y >= 0:          # sol sous y : l'ombre douce est un gris NEUTRE, comptée comme fond sous l'objet seulement
        sol = np.zeros_like(clair)
        sol[a.sol_y:] = True
        clair |= sol & (lum > a.sol_lum) & (sat < a.sol_sat)
    lab, n = ndimage.label(clair)
    bord = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    m = ~np.isin(lab, list(bord))
    m = ndimage.binary_opening(m, iterations=1)
    m = ndimage.binary_fill_holes(m)
    lab, n = ndimage.label(m)
    if n > 1:
        tailles = ndimage.sum(m, lab, range(1, n + 1))
        m = np.isin(lab, 1 + np.nonzero(tailles >= 30)[0])
    return m


def masque_noir(chemin, taille):
    """Masque d'une image « objet noir sur blanc », mise à la taille de la photo."""
    im = Image.open(chemin).convert("L").resize(taille, Image.LANCZOS)
    return ndimage.binary_fill_holes(np.asarray(im) < 128)


def contour(m):
    return m & ~ndimage.binary_erosion(m, iterations=1)


def main():
    ap = argparse.ArgumentParser(description="Rendu de la caméra « photo » contre la photo : côte à côte, superposition, "
                                             "IoU des silhouettes.")
    ap.add_argument("rendu", help="rendu de la caméra « photo » (même cadrage que la photo)")
    ap.add_argument("--silhouette", default="", help="rendu de la silhouette du modèle (objet noir sur blanc)")
    ap.add_argument("--masque-photo", default="", help="masque de la photo (objet noir sur blanc) ; sinon automatique")
    ap.add_argument("--photo", default="", help="photo (sinon variable PHOTO, ou l'unique .jpg de reference\\)")
    ap.add_argument("--sortie", default=os.path.join(ICI, "rendus"))
    ap.add_argument("--suffixe", default="")
    ap.add_argument("--zone", default="", help="x0,y0,x1,y1 (px de la photo) : IoU restreint à une zone")
    ap.add_argument("--fond-lum", type=float, default=205.0, help="masque automatique : luminance mini du fond")
    ap.add_argument("--fond-sat", type=float, default=16.0, help="masque automatique : saturation maxi du fond")
    ap.add_argument("--sol-y", type=int, default=-1, help="masque automatique : y (px) sous lequel l'ombre du sol est "
                                                          "du fond (-1 : aucun ; brûleur : 480)")
    ap.add_argument("--sol-lum", type=float, default=160.0)
    ap.add_argument("--sol-sat", type=float, default=12.0)
    a = ap.parse_args()
    photo = trouver_photo(a.photo)
    ph = Image.open(photo).convert("RGB")
    W, H = ph.size
    rd = Image.open(a.rendu).convert("RGB")
    k = 2
    ph2 = ph.resize((W * k, H * k), Image.LANCZOS)
    rd2 = rd.resize((W * k, H * k), Image.LANCZOS)
    cote = Image.new("RGB", (W * k * 2 + 20, H * k + 60), (255, 255, 255))
    cote.paste(ph2, (0, 60))
    cote.paste(rd2, (W * k + 20, 60))
    d = ImageDraw.Draw(cote)
    d.text((10, 20), "PHOTO (%d x %d)" % (W, H), fill=(0, 0, 0))
    d.text((W * k + 30, 20), "MODELE BLENDER - camera 'photo' calee (meme cadrage)", fill=(0, 0, 0))
    os.makedirs(a.sortie, exist_ok=True)
    p1 = os.path.join(a.sortie, "comparaison_photo%s.png" % a.suffixe)
    cote.save(p1)
    mp = masque_noir(a.masque_photo, (W, H)) if a.masque_photo else masque_photo(photo, a)
    Image.fromarray((mp * 255).astype(np.uint8)).save(os.path.join(a.sortie, "_masque_photo%s.png" % a.suffixe))
    sup = Image.blend(ph2, rd2, 0.5)
    arr = np.asarray(sup).copy()
    mp2 = np.asarray(Image.fromarray(mp.astype(np.uint8) * 255).resize((W * k, H * k), Image.NEAREST)) > 0
    arr[contour(mp2)] = (0, 200, 0)
    if a.silhouette:
        mr = masque_noir(a.silhouette, (W, H))
        mr2 = np.asarray(Image.fromarray(mr.astype(np.uint8) * 255).resize((W * k, H * k), Image.NEAREST)) > 0
        arr[contour(mr2)] = (230, 0, 0)
        if a.zone:
            x0, y0, x1, y1 = (int(v) for v in a.zone.split(","))
            z = np.zeros_like(mp)
            z[y0:y1, x0:x1] = True
            mp, mr = mp & z, mr & z
        inter, union = (mp & mr).sum(), (mp | mr).sum()
        iou = inter / union if union else 0.0
        # carte des écarts : vert = photo seule, rouge = modèle seul
        ec = np.full((H, W, 3), 255, np.uint8)
        ec[mp & mr] = (180, 180, 180)
        ec[mp & ~mr] = (0, 170, 0)
        ec[~mp & mr] = (220, 0, 0)
        Image.fromarray(ec).resize((W * k, H * k), Image.NEAREST).save(
            os.path.join(a.sortie, "ecarts_silhouette%s.png" % a.suffixe))
        print("IoU silhouettes = %.4f   (photo %d px, modèle %d px, commun %d px, photo seule %d, modèle seul %d)"
              % (iou, mp.sum(), mr.sum(), inter, (mp & ~mr).sum(), (~mp & mr).sum()))
    p2 = os.path.join(a.sortie, "superposition_photo%s.png" % a.suffixe)
    Image.fromarray(arr).save(p2)
    print("Écrit :", p1, "|", p2)


if __name__ == "__main__":
    main()
