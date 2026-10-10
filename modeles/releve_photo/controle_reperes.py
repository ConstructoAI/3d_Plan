# -*- coding: utf-8 -*-
r"""Contrôle des repères INTÉRIEURS de la vue « photo » : chaque point 3D du modèle, projeté par la caméra calée sur la
photo, contre le pixel relevé sur la photo. Complète l'IoU des silhouettes (comparaison_photo.py), qui ne voit pas les
défauts intérieurs.

MODÈLE tiré de Bruleur_Natcom_Blender\controle_reperes.py (2026-09-24 ; voir modeles\LISEZMOI.md), rendu GÉNÉRIQUE : la
liste des repères n'est plus écrite ici. Elle vient d'un module du PROJET, reperes_photo.py (patron :
exemple_reperes_photo.py), qui définit :
  CAMERA   = "Caméra photo"            nom de l'objet caméra calée sur la photo ;
  IMAGE_PX = (largeur, hauteur)        taille de la photo, en px ;
  REPERES  = [(nom, (x, y, z) en MÈTRES, (u, v) en px de la photo, origine en haut à gauche), ...] ;
  PHOTO    = r"reference\photo.jpg"    facultatif : image de contrôle avec les croix (chemin relatif à ce module) ;
  SEUIL_PX = 5.0                       facultatif : écart admis (5 px au plus sur le brûleur) ;
  def supplementaires(projeter): ...   facultatif : lignes de plus (contours échantillonnés, etc.), projeter(p3) -> (u, v)
                                       rend les px d'un point 3D ; retourner [(nom, (u, v) photo, (pu, pv) modèle, écart)].
Module trouvé, dans l'ordre : la variable REPERES_PHOTO (chemin du .py) ; sinon reperes_photo.py à côté du script du
modèle passé à Blender par --python (ou -P) ; sinon dans le dossier courant.
À lancer APRÈS le script du modèle, dans le même Blender (aucun rendu, aucun GPU) :
  & $env:BM_BLENDER -b --factory-startup --python build_<projet>.py --python controle_reperes.py
($env:BM_BLENDER est posé par outils\chemins.cmd ou chemins.ps1 ; sinon <racine>\outils\blender\blender.exe.)
Écrit, dans le dossier du module des repères : rendus\reperes_interieurs.txt (tableau) et rendus\reperes_interieurs.png
(photo avec une croix VERTE au relevé et une croix ROUGE au modèle). Code de sortie 1 si un repère dépasse SEUIL_PX.
Leçons du brûleur (CLAUDE.md, « Pièges vérifiés — rendu ») : mesurer les pixels de la photo PAR CODE (centroïde des
pixels d'un cadran, profils de luminance), jamais contre son propre relevé, sinon le contrôle est circulaire ; appeler
view_layer.update() avant de lire matrix_world (fait ici).
"""
import importlib.util
import math
import os
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector


def trouver_module():
    choix = os.environ.get("REPERES_PHOTO", "").strip().strip('"')
    if choix:
        if not os.path.isfile(choix):
            raise SystemExit("REPERES_PHOTO=%s : fichier introuvable." % choix)
        return os.path.abspath(choix)
    args = sys.argv
    scripts = [args[i + 1] for i, a in enumerate(args[:-1]) if a in ("--python", "-P")]
    for s in scripts:
        if os.path.basename(s).lower() != "controle_reperes.py":
            f = os.path.join(os.path.dirname(os.path.abspath(s)), "reperes_photo.py")
            if os.path.isfile(f):
                return f
    f = os.path.join(os.getcwd(), "reperes_photo.py")
    if os.path.isfile(f):
        return f
    raise SystemExit("reperes_photo.py introuvable (à côté du script du modèle ou dans le dossier courant) : le créer "
                     "d'après exemple_reperes_photo.py, ou poser la variable REPERES_PHOTO.")


FICHIER = trouver_module()
DOSSIER = os.path.dirname(FICHIER)
sys.path.insert(0, DOSSIER)                     # le module des repères peut importer parametres_<projet>.py
spec = importlib.util.spec_from_file_location("reperes_photo", FICHIER)
RP = importlib.util.module_from_spec(spec)
spec.loader.exec_module(RP)
SEUIL = float(getattr(RP, "SEUIL_PX", 5.0))

sc = bpy.context.scene
bpy.context.view_layer.update()                 # matrix_world à jour (objets créés par script)
if RP.CAMERA not in bpy.data.objects:
    raise SystemExit("caméra « %s » absente de la scène (CAMERA de %s)" % (RP.CAMERA, FICHIER))
cam = bpy.data.objects[RP.CAMERA]
W, H = RP.IMAGE_PX
ancien = (sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage)
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100


def projeter(p3):
    c = world_to_camera_view(sc, cam, Vector(p3))
    return c.x * W, (1 - c.y) * H


lignes = []
for nom, p3, (u, v) in RP.REPERES:
    pu, pv = projeter(p3)
    lignes.append((nom, (u, v), (pu, pv), math.hypot(pu - u, pv - v)))
if callable(getattr(RP, "supplementaires", None)):
    lignes += list(RP.supplementaires(projeter))
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = ancien
if not lignes:
    raise SystemExit("aucun repère dans %s" % FICHIER)

txt = ["| Repère | Photo (px) | Modèle (px) | Écart (px) |", "|---|---|---|---|"]
for nom, (u, v), (pu, pv), e in lignes:
    txt.append("| %s | (%.1f ; %.1f) | (%.1f ; %.1f) | %.1f |" % (nom, u, v, pu, pv, e))
es = [l[3] for l in lignes]
txt.append("")
txt.append("Écart moyen %.1f px, médian %.1f px, maximal %.1f px ; %d repères sur %d à %g px au plus."
           % (sum(es) / len(es), sorted(es)[len(es) // 2], max(es), sum(1 for e in es if e <= SEUIL), len(es), SEUIL))
print("\n=== Repères intérieurs de la vue photo (%s) ===" % os.path.basename(FICHIER))
print("\n".join(txt))
os.makedirs(os.path.join(DOSSIER, "rendus"), exist_ok=True)
with open(os.path.join(DOSSIER, "rendus", "reperes_interieurs.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(txt) + "\n")
print("CONTROLE_REPERES_RESUME repères=%d max_px=%.2f hors_seuil=%d" % (len(es), max(es), sum(1 for e in es if e > SEUIL)))

# Image de contrôle (Pillow n'est pas dans le Python de Blender : API image de Blender + numpy)
photo = getattr(RP, "PHOTO", "")
if photo:
    try:
        import numpy as np
        img = bpy.data.images.load(photo if os.path.isabs(photo) else os.path.join(DOSSIER, photo))
        w, h = img.size
        px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)

        def croix(u, v, col, t=5):
            x, y = int(round(u)), int(round(h - 1 - v))
            for d in range(-t, t + 1):
                for (xx, yy) in ((x + d, y), (x, y + d)):
                    if 0 <= xx < w and 0 <= yy < h:
                        px[yy, xx, :3] = col
        for _, (u, v), (pu, pv), _ in lignes:
            croix(u, v, (0.0, 0.8, 0.0))
            croix(pu, pv, (1.0, 0.0, 0.0), 3)
        out = bpy.data.images.new("reperes", w, h)
        out.pixels[:] = px.ravel()
        out.filepath_raw = os.path.join(DOSSIER, "rendus", "reperes_interieurs.png")
        out.file_format = "PNG"
        out.save()
        print("Écrit : rendus\\reperes_interieurs.png et rendus\\reperes_interieurs.txt")
    except Exception as ex:  # noqa: BLE001
        print("Image de contrôle non écrite :", ex)
if any(e > SEUIL for e in es):
    sys.exit(1)
