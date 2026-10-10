# -*- coding: utf-8 -*-
r"""Dimensions du garage rouge a partir de la photo (2000x1506).

MODÈLE tiré de Garage_rouge_Blender\reference\analyse_photo.py (2026-09-23 ; voir modeles\LISEZMOI.md) : 1er relevé
d'un bâtiment d'après UNE photo, par les points de fuite. Adapté : la photo est trouvée par photo.py (variable PHOTO,
sinon l'unique .jpg du dossier), plus aucun chemin écrit en dur. Le calcul est inchangé.
Ce qui est PROPRE À LA PHOTO DU GARAGE (à remplacer pour un nouveau projet) : les zones de balayage (u, v), les points
relevés à la main (A_top, B_base, PEAK, portes...) et les échelles essayées (portes de 12 pi, porte de 36 po). On les
relève sur des zooms à grille de pixels (Pillow), puis on relance.
Mise en garde (CLAUDE.md, « Chaîne de production », étape 1) : sans les dimensions connues du client, ce relevé a donné
44' x 96' pour un garage de 40' x 100'. DEMANDER D'ABORD les dimensions connues ; elles priment sur la photo et
servent de contraintes au calage final (resection2.py).
Usage : python analyse_photo.py          (Python du poste : Pillow)

Texte d'origine :

Constat : les verticales du batiment sont paralleles dans l'image (coins A, B, C) -> camera de niveau,
point principal decale verticalement (horizon = ligne des points de fuite). On mesure les deux points de fuite
horizontaux, on en deduit la focale (orthogonalite des deux faces), puis on reconstruit les faces dans le plan
vertical de chaque mur. Echelle : largeur des portes de garage (hypothese 12 pi), controlee par la porte pietonne.
"""
import math
from pathlib import Path

from PIL import Image

from photo import chemin_photo

SRC = chemin_photo(Path(__file__).resolve().parent)   # variable PHOTO, sinon l'unique .jpg de ce dossier
im = Image.open(SRC).convert("RGB")
px = im.load()
W_IMG, H_IMG = im.size
CX = W_IMG / 2


def fit_line(pts, it=3, tol=1.5):
    """v = a + b*u, moindres carres avec rejet des aberrants."""
    P = list(pts)
    for _ in range(it):
        n = len(P)
        su = sum(p[0] for p in P); sv = sum(p[1] for p in P)
        suu = sum(p[0] ** 2 for p in P); suv = sum(p[0] * p[1] for p in P)
        b = (n * suv - su * sv) / (n * suu - su * su)
        a = (sv - b * su) / n
        res = [abs(p[1] - (a + b * p[0])) for p in P]
        keep = [p for p, r in zip(P, res) if r <= tol]
        if len(keep) == len(P) or len(keep) < 5:
            break
        P = keep
    rms = math.sqrt(sum((p[1] - (a + b * p[0])) ** 2 for p in P) / len(P))
    return a, b, len(P), rms


def is_sky(c):
    r, g, b = c
    return (b - r) > 45 and b > 150


def is_red(c, k=35):
    r, g, b = c
    return (r - g) > k and (r - b) > k - 10


# ======================================================================================================================
# EXEMPLE : photo du garage rouge (2000 x 1506). Toutes les zones (u, v) de balayage ci-dessous et les points relevés
# à la main plus bas sont PROPRES À CETTE PHOTO : les remplacer par ceux de la vôtre.
# ======================================================================================================================
# (a) Rive d'egout du long pan (ciel -> bordure blanche), u 230..950
fascia = []
for u in range(230, 955, 5):
    for v in range(380, 800):
        if not is_sky(px[u, v]) and not is_sky(px[u, v + 1]) and not is_sky(px[u, v + 2]):
            fascia.append((u, v)); break
# (c) Facade : transition gris (pignon) -> rouge, u 1010..1645
rouge = []
for u in range(1010, 1648, 5):
    for v in range(460, 720):
        if all((px[u, v + k][0] - px[u, v + k][1]) > 15 and px[u, v + k][0] > px[u, v + k][2] for k in range(4)):
            rouge.append((u, v)); break
# Rives du pignon (ciel -> bordure) : gauche u 1010..1415, droite u 1445..1675
rive_g, rive_d = [], []
for u in range(1010, 1416, 5):
    for v in range(300, 700):
        if not is_sky(px[u, v]) and not is_sky(px[u, v + 1]) and not is_sky(px[u, v + 2]):
            rive_g.append((u, v)); break
for u in range(1445, 1676, 5):
    for v in range(300, 700):
        if not is_sky(px[u, v]) and not is_sky(px[u, v + 1]) and not is_sky(px[u, v + 2]):
            rive_d.append((u, v)); break

La = fit_line(fascia)
Lc = fit_line(rouge)
Lg = fit_line(rive_g)
Ld = fit_line(rive_d)
print("rive d'egout long pan : v = %.2f + %.5f u  (n=%d, rms=%.2f px)" % La)
print("transition gris/rouge : v = %.2f + %.5f u  (n=%d, rms=%.2f px)" % Lc)
print("rive pignon gauche    : v = %.2f + %.5f u  (n=%d, rms=%.2f px)" % Lg)
print("rive pignon droite    : v = %.2f + %.5f u  (n=%d, rms=%.2f px)" % Ld)

# Points releves a la main (zooms)
A_top, A_base = (1000, 488), (1000, 1047)     # coin avant-gauche : haut du rouge (facade), bas du bardage
B_top, B_base = (1656, 630), (1657, 980)      # coin avant-droit
C_top, C_base = (213, 720), (213, 926)        # coin arriere (long pan) : sous-face, bas du bardage
PEAK = (1428, 370)                            # sommet du pignon (bordure)


def line2(p, q):
    b = (q[1] - p[1]) / (q[0] - p[0]); return p[1] - b * p[0], b


def inter(l1, l2):
    a1, b1 = l1[:2]; a2, b2 = l2[:2]
    u = (a2 - a1) / (b1 - b2); return u, a1 + b1 * u


baseL = line2(A_base, C_base)
baseR = line2(A_base, B_base)
p1t = line2((1218, 703), (1413, 722))
p2t = line2((1476, 686), (1608, 702))
VPL = inter(La, baseL)
VPR_list = [inter(Lc, baseR), inter(Lc, p1t), inter(baseR, p1t), inter(baseR, p2t), inter(Lc, p2t)]
print("VP gauche (egout x base) :", ["%.1f" % t for t in VPL])
for k in VPR_list:
    print("VP droit candidat :", ["%.1f" % t for t in k])
VPR = inter(Lc, baseR)
vh = (VPL[1] + VPR[1]) / 2
uL, uR = VPL[0], VPR[0]
f = math.sqrt((CX - uL) * (uR - CX))
print("horizon v_h = %.1f (VPL %.1f / VPR %.1f), focale f = %.0f px, champ horizontal = %.1f deg"
      % (vh, VPL[1], VPR[1], f, 2 * math.degrees(math.atan(W_IMG / 2 / f))))

# Repere camera : x droite, y bas, z avant ; camera de niveau, point principal (CX, vh)
def norm(v):
    m = math.sqrt(sum(t * t for t in v)); return tuple(t / m for t in v)


eR = norm((uR - CX, 0.0, f))    # le long de la facade, de A vers B
eL = norm((uL - CX, 0.0, f))    # le long du long pan, de A vers l'arriere (C)
UP = (0.0, -1.0, 0.0)
dot = lambda a, b: sum(x * y for x, y in zip(a, b))
sub = lambda a, b: tuple(x - y for x, y in zip(a, b))
print("orthogonalite eR.eL = %.2e" % dot(eR, eL))

h = 1.0  # hauteur de la camera au-dessus du plan du bas du bardage (unite provisoire)


def ground(p):
    u, v = p; t = h / (v - vh); return (t * (u - CX), h, t * f)


A3 = ground(A_base)


def on_plane(p, normal):
    u, v = p; r = (u - CX, v - vh, f)
    t = dot(normal, A3) / dot(normal, r)
    X = tuple(t * c for c in r)
    return X


def facade(p):   # plan de la facade (pignon avant) : normale eL ; (s le long de A->B, z hauteur)
    X = on_plane(p, eL); d = sub(X, A3); return dot(d, eR), dot(d, UP)


def longpan(p):  # plan du long pan : normale eR ; (s de A vers l'arriere, z hauteur)
    X = on_plane(p, eR); d = sub(X, A3); return dot(d, eL), dot(d, UP)


Wf = facade(B_base)[0]
Lg_ = longpan(C_base)[0]
Lg_top = longpan(C_top)[0]
print("largeur facade (A->B, base) = %.3f h ; longueur (A->C, base) = %.3f h ; (A->C, haut) = %.3f h"
      % (Wf, Lg_, Lg_top))
print("haut du rouge en A = %.3f h ; en B = %.3f h ; sous-face en C = %.3f h"
      % (facade(A_top)[1], facade(B_top)[1], longpan(C_top)[1]))
pk = facade(PEAK)
print("sommet pignon : s = %.3f h (milieu = %.3f h), z = %.3f h" % (pk[0], Wf / 2, pk[1]))

# Portes (bords verticaux ramenes sur la ligne de base de la facade)
def base_at(u):
    a, b = baseR; return (u, a + b * u)


p1 = (facade(base_at(1218))[0], facade(base_at(1414))[0])
p2 = (facade(base_at(1476))[0], facade(base_at(1609))[0])
pp = (facade(base_at(1083))[0], facade(base_at(1138))[0])
print("porte 1 : s %.3f -> %.3f (larg %.3f h) ; porte 2 : s %.3f -> %.3f (larg %.3f h)"
      % (p1[0], p1[1], p1[1] - p1[0], p2[0], p2[1], p2[1] - p2[0]))
print("porte pietonne : s %.3f -> %.3f (larg %.3f h)" % (pp[0], pp[1], pp[1] - pp[0]))
# hauteurs (points sur la facade)
d1_top = facade((1218, 703))[1]; d1_bot = facade((1222, 1046))[1]
d2_top = facade((1476, 686))[1]; d2_bot = facade((1480, 1003))[1]
pp_top = facade((1110, 851))[1]; pp_bot = facade((1110, 1050))[1]
print("porte 1 : z %.3f -> %.3f (haut %.3f h) ; porte 2 : z %.3f -> %.3f ; pietonne : z %.3f -> %.3f (haut %.3f h)"
      % (d1_bot, d1_top, d1_top - d1_bot, d2_bot, d2_top, pp_bot, pp_top, pp_top - pp_bot))

# Long pan : fenetre, porte coulissante, capot
def base_long(u):
    a, b = baseL; return (u, a + b * u)


fen = [longpan(base_long(588))[0], longpan(base_long(665))[0]]
fz = [longpan((588, 850))[1], longpan((588, 919))[1]]
coul = longpan(base_long(349))[0]
capot = [longpan(base_long(228))[0], longpan(base_long(355))[0]]
print("fenetre : s %.3f -> %.3f (larg %.3f h), z %.3f -> %.3f"
      % (fen[0], fen[1], fen[1] - fen[0], fz[1], fz[0]))
print("porte coulissante : bord a s = %.3f h (C a %.3f h) ; capot s %.3f -> %.3f" % (coul, Lg_, capot[0], capot[1]))

# Echelle : portes de garage 12 pi (3,6576 m) de large (EXEMPLE : prendre les dimensions CONNUES du projet)
FT = 0.3048
for label, scale in [("portes 12 pi", 12 * FT / ((p1[1] - p1[0] + p2[1] - p2[0]) / 2)),
                     ("porte pietonne 36 po", 3 * FT / (pp[1] - pp[0])),
                     ("porte pietonne 80 po de haut", 80 * 0.0254 / (pp_top - pp_bot))]:
    m = lambda x: x * scale
    print("\n== echelle %s : h = %.3f m" % (label, scale))
    print("  facade %.2f m (%.1f pi), long pan %.2f m (%.1f pi)" % (m(Wf), m(Wf) / FT, m(Lg_), m(Lg_) / FT))
    print("  haut du rouge (A) %.2f m (%.1f pi) au-dessus du bas du bardage ; sommet %.2f m (%.1f pi)"
          % (m(facade(A_top)[1]), m(facade(A_top)[1]) / FT, m(pk[1]), m(pk[1]) / FT))
    print("  porte 1 : %.2f x %.2f m (%.1f x %.1f pi), bas a %.2f m ; porte 2 larg %.2f m ; pietonne %.2f x %.2f m"
          % (m(p1[1] - p1[0]), m(d1_top - d1_bot), m(p1[1] - p1[0]) / FT, m(d1_top - d1_bot) / FT, m(d1_bot),
             m(p2[1] - p2[0]), m(pp[1] - pp[0]), m(pp_top - pp_bot)))
    print("  positions (depuis A, pi) : pietonne %.1f-%.1f, porte1 %.1f-%.1f, porte2 %.1f-%.1f, B %.1f"
          % tuple(m(x) / FT for x in (pp[0], pp[1], p1[0], p1[1], p2[0], p2[1], Wf)))
    print("  fenetre long pan : %.1f-%.1f pi depuis A, z %.1f-%.1f pi ; coulissante bord a %.1f pi (reste %.1f pi jusqu'au coin C)"
          % (m(fen[0]) / FT, m(fen[1]) / FT, m(fz[1]) / FT, m(fz[0]) / FT, m(coul) / FT, m(Lg_ - coul) / FT))
    rise = pk[1] - facade(A_top)[1]
    print("  pente approx (sommet - haut du rouge)/(demi-facade) = %.3f -> %.1f/12" % (rise / (Wf / 2), 12 * rise / (Wf / 2)))

