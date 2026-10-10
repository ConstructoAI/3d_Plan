# -*- coding: utf-8 -*-
"""Trouver le plan PDF du projet, sans nom ni chemin écrit en dur (modèle, poste portable).

Ordre :
  1. la variable PLAN_PDF (chemin absolu, ou relatif au dossier de ce script) ;
  2. sinon l'UNIQUE fichier .pdf du dossier de ce script (le dossier reference\\ du projet) ;
  3. sinon une erreur claire (aucun PDF, ou plusieurs : choisir avec PLAN_PDF).

Règle d'or (SAVOIR_LECTURE_PLANS.md, § 0) : l'original n'est jamais touché. On COPIE le PDF dans
reference\\ (s'il est sur OneDrive, le copier d'abord), puis on travaille sur la copie.
"""
import os
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent


def chemin_pdf(dossier=ICI):
    dossier = Path(dossier)
    v = os.environ.get("PLAN_PDF")
    if v:
        p = Path(v)
        if not p.is_absolute():
            p = dossier / p
        if not p.is_file():
            sys.exit(f"PLAN_PDF = {v} : fichier introuvable.")
        return p
    pdfs = sorted(dossier.glob("*.pdf"))
    if len(pdfs) == 1:
        return pdfs[0]
    if not pdfs:
        sys.exit(f"Aucun PDF dans {dossier} : y copier le plan (jamais l'original), ou définir PLAN_PDF.")
    sys.exit(f"Plusieurs PDF dans {dossier} : choisir avec la variable PLAN_PDF ("
             + ", ".join(p.name for p in pdfs) + ").")


if __name__ == "__main__":
    print(chemin_pdf())
