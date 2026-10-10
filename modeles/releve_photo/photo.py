# -*- coding: utf-8 -*-
r"""Trouver la photo du projet, sans nom ni chemin écrit en dur (modèle, poste portable).

Ordre :
  1. la variable PHOTO (chemin absolu, ou relatif au dossier donné) ;
  2. sinon l'UNIQUE photo .jpg ou .jpeg du dossier (le dossier reference\ du projet) ;
  3. sinon, s'il n'y a aucun .jpg, l'UNIQUE .png, .tif ou .tiff du dossier ;
  4. sinon une erreur claire (aucune photo, ou plusieurs : choisir avec PHOTO).
Règle d'or : l'original n'est jamais touché. On COPIE la photo dans reference\ (depuis OneDrive ou un téléphone, la copier
d'abord), puis on travaille sur la copie. Les zooms et les aperçus s'écrivent ailleurs (zooms\, rendus\).
Modèle ajouté le 2026-09-25 (modeles\releve_photo, voir modeles\LISEZMOI.md), sur le patron de releve_pdf\plan_pdf.py.
"""
import os
from pathlib import Path

PHOTOS = (".jpg", ".jpeg")
IMAGES = (".png", ".tif", ".tiff")


def chemin_photo(dossier):
    dossier = Path(dossier).resolve()
    choisi = os.environ.get("PHOTO", "").strip().strip('"')
    if choisi:
        p = Path(choisi)
        p = p if p.is_absolute() else dossier / p
        if not p.is_file():
            raise SystemExit("PHOTO=%s : fichier introuvable." % p)
        return p
    for extensions in (PHOTOS, IMAGES):
        trouves = sorted(f for f in dossier.iterdir() if f.is_file() and f.suffix.lower() in extensions)
        if len(trouves) == 1:
            return trouves[0]
        if len(trouves) > 1:
            raise SystemExit("Plusieurs photos dans %s (%s) : choisir avec la variable PHOTO, par exemple "
                             "$env:PHOTO = \"%s\"." % (dossier, ", ".join(f.name for f in trouves), trouves[0].name))
    raise SystemExit("Aucune photo (.jpg, .jpeg, .png, .tif) dans %s : y COPIER la photo du projet, ou poser la "
                     "variable PHOTO." % dossier)


if __name__ == "__main__":
    print(chemin_photo(Path(__file__).resolve().parent))
