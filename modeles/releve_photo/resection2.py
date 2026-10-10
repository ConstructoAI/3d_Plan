# -*- coding: utf-8 -*-
r"""Calage avec TOUTES les donnees de Sylvain : 40' x 100', PG1 12'x12', PG2 12'x14'.

MODÈLE tiré de Garage_rouge_Blender\reference\resection2.py (2026-09-23 ; voir modeles\LISEZMOI.md) : calage de la
caméra de la photo par MOINDRES CARRÉS (numpy, scipy), les dimensions CONNUES du client en contraintes. Aucun chemin,
aucun fichier lu : les données sont dans le script. Tout ce qui suit « DONNÉES » est l'EXEMPLE du garage rouge
(repère : origine au centre du bâtiment au sol, X le long de la façade, Y en profondeur, Z en haut, en PIEDS) :
  W, L, FOND, DEB_E, DEB_R : dimensions connues et débords ; U0, IMG_W, IMG_H : photo (point principal horizontal au
  centre : caméra de niveau, verticales parallèles) ; LINES : droites ajustées par analyse_photo.py (v = a + b u) ;
  PTS : pixels relevés et leur point 3D (fonction des inconnues q) ; NAMES et x0 : inconnues et départ.
Sortie : Xc, Yc, Zc (position, pi), alpha (azimut de visée depuis +X, degrés), f (focale en px), v0 (horizon, px),
puis les écarts en px de chaque repère. Report dans parametres_<projet>.py (caméra « photo », en mètres ; conversion
vérifiée sur le garage, CAMERA_PHOTO de parametres_garage.py) :
  position = (Xc, Yc, Zc) x 0,3048 ; rotation_deg = (90, 0, alpha - 90) ;
  focale_mm = f x capteur_mm / IMG_W (capteur 36 mm, sensor_fit HORIZONTAL) ;
  shift_x = (U0 - IMG_W / 2) / IMG_W ; shift_y = (v0 - IMG_H / 2) / IMG_W.
Un écart résiduel de 8 à 10 px peut être le compromis entre les dimensions données et la photo : ajuster la caméra,
JAMAIS les dimensions données par le client.
Usage : python resection2.py [W] [k1]     (W : largeur de façade à essayer ; k1 : ajouter la distorsion radiale)

Texte d'origine :
Inconnues supplementaires : centres X1, X2 des portes. On regarde les residus : si la photo ne peut pas
satisfaire a la fois 40' de facade et des portes de 12', ca se verra ici.
Variante : pixels non carres interdits ; on teste aussi une distorsion radiale k1 (objectif de telephone)."""
import math, sys
import numpy as np
from scipy.optimize import least_squares

# ================================= DONNÉES : EXEMPLE du garage rouge (à remplacer) =================================
W, L = float(sys.argv[1]) if len(sys.argv) > 1 else 40.0, 100.0
USE_K1 = len(sys.argv) > 2 and sys.argv[2] == "k1"
FOND = 10 / 12.0
DEB_E, DEB_R = 1.0, 1.0
U0, IMG_W, IMG_H = 1000.0, 2000, 1506

LINES = {
    "egout_long_pan": ((778.79, -0.32714), (230, 950)),
    "haut_rouge_facade": ((257.06, 0.22878), (1010, 1645)),
    "rive_gauche": ((629.57, -0.17923), (1010, 1415)),
    "rive_droite": ((-1006.68, 0.96591), (1445, 1675)),
}
PTS = [
    ("A_base", (1000, 1047), lambda q: (-W / 2, -L / 2, FOND)),
    ("B_base", (1657, 980), lambda q: (W / 2, -L / 2, FOND)),
    ("C_base", (213, 926), lambda q: (-W / 2, L / 2, FOND)),
    ("A_top", (1000, 488), lambda q: (-W / 2, -L / 2, q["H"])),
    ("B_top", (1656, 630), lambda q: (W / 2, -L / 2, q["H"])),
    ("C_top", (213, 720), lambda q: (-W / 2, L / 2, q["H"] + 0.3)),
    ("sommet", (1428, 370), lambda q: (0.0, -L / 2 - DEB_R, q["Zr"])),
    ("PG1_hg", (1218, 703), lambda q: (-W / 2 + q["X1"] - 6, -L / 2, 12.0)),
    ("PG1_hd", (1413, 722), lambda q: (-W / 2 + q["X1"] + 6, -L / 2, 12.0)),
    ("PG1_bg", (1222, 1046), lambda q: (-W / 2 + q["X1"] - 6, -L / 2, 0.0)),
    ("PG2_hg", (1476, 686), lambda q: (-W / 2 + q["X2"] - 6, -L / 2, 14.0)),
    ("PG2_hd", (1608, 702), lambda q: (-W / 2 + q["X2"] + 6, -L / 2, 14.0)),
]
NAMES = ["Xc", "Yc", "Zc", "alpha", "f", "v0", "H", "Hf", "p", "Zr", "X1", "X2"] + (["k1"] if USE_K1 else [])
# ========================================== fin des DONNÉES de l'exemple ==========================================


def unpack(x):
    return dict(zip(NAMES, x))


def project(q, P):
    a = math.radians(q["alpha"])
    F = (math.cos(a), math.sin(a)); R = (math.sin(a), -math.cos(a))
    d = (P[0] - q["Xc"], P[1] - q["Yc"], P[2] - q["Zc"])
    zc = d[0] * F[0] + d[1] * F[1]; xc = d[0] * R[0] + d[1] * R[1]
    x, y = xc / zc, -d[2] / zc          # coordonnees normalisees (y vers le bas), centre = point principal
    if USE_K1:                          # distorsion radiale autour du CENTRE de l'image
        cx, cy = (U0 - IMG_W / 2) / q["f"], (q["v0"] - IMG_H / 2) / q["f"]
        xr, yr = x + cx, y + cy
        r2 = xr * xr + yr * yr
        s = 1 + q["k1"] * r2
        x, y = xr * s - cx, yr * s - cy
    return U0 + q["f"] * x, q["v0"] + q["f"] * y


def line_3d(q, name, t):
    if name == "egout_long_pan":
        return (-W / 2 - DEB_E, -L / 2 - DEB_R + t * (L + 2 * DEB_R), q["Hf"])
    if name == "haut_rouge_facade":
        return (-W / 2 + t * W, -L / 2, q["H"])
    half = W / 2 + DEB_R
    X = -half + t * half if name == "rive_gauche" else t * half
    return (X, -L / 2 - DEB_R, q["Zr"] - q["p"] * abs(X))


def residuals(x, verbose=False):
    q = unpack(x); r = []
    for name, uv, P in PTS:
        u, v = project(q, P(q))
        r += [(u - uv[0]) / 2.0, (v - uv[1]) / 2.0]
        if verbose:
            print("  %-7s mesure (%6.1f, %6.1f)  modele (%7.1f, %7.1f)  ecart (%+5.1f, %+5.1f)"
                  % (name, uv[0], uv[1], u, v, u - uv[0], v - uv[1]))
    for name, ((a, b), (umin, umax)) in LINES.items():
        res = []
        for t in np.linspace(0, 1, 41):
            u, v = project(q, line_3d(q, name, t))
            if umin <= u <= umax:
                res.append(v - (a + b * u))
        idx = np.linspace(0, len(res) - 1, 5).round().astype(int)
        sel = [res[i] for i in idx]
        r += list(np.array(sel) / 1.0)
        if verbose:
            print("  droite %-18s ecarts v : %s" % (name, " ".join("%+.1f" % s for s in sel)))
    return np.array(r)


# Point de départ (EXEMPLE du garage) : position et azimut tirés d'analyse_photo.py, f et v0 des points de fuite
x0 = [-46.4, -80.8, 6.48, 49.5, 1420.0, 854.0, 16.9, 17.6, 0.323, 24.35, 15.0, 30.4] + ([0.0] if USE_K1 else [])
sol = least_squares(residuals, np.array(x0), x_scale=[5, 5, 1, 2, 100, 20, 1, 1, 0.05, 1, 1, 1] + ([0.02] if USE_K1 else []))
q = unpack(sol.x)
print("W=%g L=%g %s -> cout %.2f" % (W, L, "(avec k1)" if USE_K1 else "", sol.cost))
print("  " + "  ".join("%s=%.3f" % (k, q[k]) for k in NAMES))
residuals(sol.x, verbose=True)
print("  PG1 : %.2f -> %.2f depuis A ; PG2 : %.2f -> %.2f ; ecart entre portes %.2f ; marge droite %.2f"
      % (q["X1"] - 6, q["X1"] + 6, q["X2"] - 6, q["X2"] + 6, (q["X2"] - 6) - (q["X1"] + 6), W - (q["X2"] + 6)))
