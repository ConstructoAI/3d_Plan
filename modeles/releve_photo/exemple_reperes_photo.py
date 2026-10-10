# -*- coding: utf-8 -*-
r"""PATRON du module des repères de la vue « photo », lu par controle_reperes.py (modeles\releve_photo).

Pour un projet : copier ce fichier À CÔTÉ du script du modèle sous le nom reperes_photo.py, puis le remplir.
- Les points 3D viennent des PARAMÈTRES du projet (jamais recopiés à la main) : import parametres_<projet> as P.
- Les pixels viennent de la PHOTO, mesurés par code (centroïde des pixels d'un cadran, profils de luminance, gros plans
  gradués), jamais relus sur notre propre rendu : sinon le contrôle est circulaire.
- Viser des repères INTÉRIEURS (cadrans, brides, coins d'armoires, trappes), pas seulement la silhouette.
Sur le brûleur (2026-09-24) : 33 repères, 5 px au plus, dont des contours échantillonnés finement (fonction
supplementaires). Les valeurs ci-dessous montrent la FORME (ordre de grandeur du garage rouge) : ce n'est pas un relevé
vérifié, ne pas s'en servir comme données.
"""
# import parametres_monprojet as P       # points 3D tirés des paramètres du projet (mètres)

CAMERA = "Caméra photo"                 # nom de l'objet caméra calée sur la photo (build_<projet>.py)
IMAGE_PX = (2000, 1500)                 # taille de la photo, en px
PHOTO = r"reference\photo.jpg"          # facultatif : image de contrôle avec les croix (relatif à ce fichier)
SEUIL_PX = 5.0                          # écart admis, en px

REPERES = [
    # (nom, point 3D en MÈTRES dans le repère du modèle, pixel relevé sur la photo (u vers la droite, v vers le bas))
    ("Coin avant-gauche, bas du revêtement", (-6.10, -15.24, 0.25), (1000.0, 1047.0)),
    ("Coin avant-gauche, haut du mur", (-6.10, -15.24, 5.31), (1000.0, 488.0)),
    ("Sommet du pignon", (0.00, -15.54, 7.63), (1428.0, 370.0)),
]


def supplementaires(projeter):
    """Facultatif : repères de plus, calculés (contours échantillonnés, point le plus haut d'une bride...).
    projeter((x, y, z)) rend (u, v) en px de la photo. Retourner [(nom, (u, v) photo, (pu, pv) modèle, écart en px)]."""
    return []
