r"""EMPREINTE COMMUNE des sources — Maison Bungalow (module du chef, partagé par les 3 DWG : plans 2D, DWG 3D, métré).

Règle 5 automatique entre les livrables (CLAUDE.md, « Pièges vérifiés — équipe d'agents », « Exports DAO ») :
- les sources = le script du modèle et ses données : build_bungalow.py, parametres_bungalow.py, releve_*.py ;
- empreinte = sha256 (12 caractères) de « nom|octets » de chaque fichier, dans l'ordre alphabétique ;
- figer_sources() attend 2 min sans modification, copie les sources dans `sources_figees\`, puis vérifie que la copie
  et les fichiers vivants relus APRÈS la copie ont la même empreinte. Chaque générateur exporte DEPUIS la copie figée,
  écrit l'empreinte dans les propriétés du DWG (doc.header.custom_vars) et la revérifie à la fin.

Usage : python empreinte_bungalow.py            → affiche l'empreinte des fichiers vivants
        python empreinte_bungalow.py --figer    → fige les sources et affiche l'empreinte figée
En module : from empreinte_bungalow import empreinte_sources, figer_sources, SOURCES_FIGEES
"""
import glob
import hashlib
import os
import sys
import time

ICI = os.path.dirname(os.path.abspath(__file__))
SOURCES_FIGEES = os.path.join(ICI, "sources_figees")
MOTIFS = ("build_bungalow.py", "parametres_bungalow.py", "releve_*.py")


def fichiers_sources(dossier=None):
    dossier = dossier or ICI
    fichiers = []
    for m in MOTIFS:
        fichiers += glob.glob(os.path.join(dossier, m))
    return sorted(set(fichiers), key=lambda f: os.path.basename(f).lower())


def empreinte_sources(dossier=None):
    h = hashlib.sha256()
    for f in fichiers_sources(dossier):
        with open(f, "rb") as fh:
            h.update(os.path.basename(f).encode() + b"|" + fh.read())
    return h.hexdigest()[:12]


def figer_sources(dest=SOURCES_FIGEES, calme_s=120, attente_max_s=900):
    import shutil
    t0 = time.time()
    while True:
        vivants = fichiers_sources(ICI)
        age = time.time() - max(os.path.getmtime(f) for f in vivants)
        if age >= calme_s:
            break
        if time.time() - t0 > attente_max_s:
            raise SystemExit(f"Sources encore modifiées depuis {attente_max_s} s : rien n'est figé.")
        print(f"  dernière modification il y a {age:.0f} s : attente du calme ({calme_s} s)")
        time.sleep(min(15.0, calme_s - age + 1.0))
    emp_avant = empreinte_sources(ICI)
    os.makedirs(dest, exist_ok=True)
    for f in glob.glob(os.path.join(dest, "*")):
        if os.path.isfile(f):
            os.remove(f)
    extra = [f for f in (os.path.join(ICI, "releve_ecarts.md"),) if os.path.exists(f)]
    for f in vivants + extra:
        shutil.copy2(f, os.path.join(dest, os.path.basename(f)))
    emp_copie, emp_apres = empreinte_sources(dest), empreinte_sources(ICI)
    if not (emp_avant == emp_copie == emp_apres):
        raise SystemExit(f"Sources modifiées pendant la copie ({emp_avant} / {emp_copie} / {emp_apres}) : relancer.")
    lignes = [time.strftime("%Y-%m-%d %H:%M:%S"), f"empreinte {emp_copie}"]
    for f in fichiers_sources(dest):
        with open(f, "rb") as fh:
            lignes.append(f"{hashlib.sha256(fh.read()).hexdigest()}  {os.path.basename(f)}")
    with open(os.path.join(dest, "EMPREINTE.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lignes) + "\n")
    return emp_copie


if __name__ == "__main__":
    if "--figer" in sys.argv:
        print("Sources figées dans", SOURCES_FIGEES, ": empreinte", figer_sources())
    else:
        print("Fichiers :", [os.path.basename(f) for f in fichiers_sources()])
        print("Empreinte des fichiers vivants :", empreinte_sources())
