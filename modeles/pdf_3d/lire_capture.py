# -*- coding: utf-8 -*-
"""lire_capture.py — dit en une ligne ce que montre une capture de PDF-XChange (voir_dans_lecteur.ps1).

    python lire_capture.py capture.png

Deux constats, mesurés sur les pixels :
  - BANDEAU JAUNE de sécurité (« Le contenu 3D a été désactivé… ») : présent ou non ;
  - le CADRE 3D montre-t-il autre chose que le message de repli gris ? (part des pixels de la page
    qui ne sont ni blancs, ni du gris clair du repli, ni du gris du texte)
Ce n'est qu'un tri rapide : pour JUGER l'affichage, il faut regarder l'image.
Code de sortie : 0 modèle probablement affiché ; 3 bandeau présent ; 4 ni bandeau ni modèle.
"""
import sys

import numpy as np
from PIL import Image


def analyser(chemin):
    im = np.asarray(Image.open(chemin).convert("RGB")).astype(int)
    h, w, _ = im.shape
    r, g, b = im[:, :, 0], im[:, :, 1], im[:, :, 2]
    # bandeau : une bande jaune pâle sur presque toute la largeur, dans le haut de la fenêtre
    jaune = (r > 235) & (g > 205) & (g < 245) & (b > 110) & (b < 200) & (r - b > 50)
    haut = jaune[: int(h * 0.35)]
    lignes = haut.mean(axis=1) > 0.5
    # Le bandeau est une BANDE : une quarantaine de lignes jaunes d'affilée sur une capture de 2 110 de haut (2 % de
    # la hauteur). Le lecteur trace aussi, sans bandeau, deux liserés jaunes de 3 lignes sous les onglets (0,14 %) :
    # une 1re version comptait les lignes sans exiger qu'elles se suivent et voyait un bandeau partout. Mesuré le
    # 2026-10-09 sur 7 captures (5 avec bandeau : suites de 41 à 44 lignes ; 2 sans : suites de 3).
    suite = plus_longue = 0
    for v in lignes:
        suite = suite + 1 if v else 0
        plus_longue = max(plus_longue, suite)
    bandeau = bool(plus_longue >= max(8, 0.008 * h))
    # la page : la plus grande zone blanche ; on regarde ce qui n'y est ni blanc ni gris neutre
    neutre = (abs(r - g) < 10) & (abs(g - b) < 10)
    colore = ~neutre & ~jaune
    zone = im[int(h * 0.12): int(h * 0.97), int(w * 0.05): int(w * 0.95)]
    zr, zg, zb = zone[:, :, 0], zone[:, :, 1], zone[:, :, 2]
    zneutre = (abs(zr - zg) < 10) & (abs(zg - zb) < 10)
    part_coloree = float((~zneutre).mean() * 100)
    sombre = float(((zr + zg + zb) / 3 < 110).mean() * 100)
    return {"bandeau": bandeau, "pixels_colores_pct": round(part_coloree, 2), "pixels_sombres_pct": round(sombre, 2),
            "taille": (w, h), "colore_total_pct": round(float(colore.mean() * 100), 2)}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    a = analyser(sys.argv[1])
    print("capture %d x %d ; bandeau jaune « contenu 3D désactivé » : %s ; pixels colorés dans la page : %.2f %% ; "
          "pixels sombres : %.2f %%" % (a["taille"][0], a["taille"][1], "OUI" if a["bandeau"] else "non",
                                        a["pixels_colores_pct"], a["pixels_sombres_pct"]))
    if a["bandeau"]:
        print("=> le lecteur a BLOQUÉ le contenu 3D : affichage NON VÉRIFIÉ (un humain doit l'autoriser)")
        sys.exit(3)
    if a["pixels_colores_pct"] > 0.8 or a["pixels_sombres_pct"] > 1.5:
        print("=> pas de bandeau et la page porte autre chose que du gris : le modèle est probablement affiché (REGARDER l'image)")
        sys.exit(0)
    print("=> ni bandeau ni modèle visible : regarder l'image")
    sys.exit(4)
