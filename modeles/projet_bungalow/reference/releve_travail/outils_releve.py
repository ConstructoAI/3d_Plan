"""Outils de relevé de l'agent DAO n° 2 (détail) — Maison Bungalow.

MODÈLE tiré de Maison_Bungalow_Blender\\reference\\releve_travail\\ (voir modeles\\LISEZMOI.md). Le PDF : variable
PLAN_PDF, sinon l'unique .pdf du dossier parent (reference\\), par ..\\plan_pdf.py. Définir les vues du projet en bas.

Repère commun de l'exemple (REPERE.md de Bungalow), en PIEDS :
  Plan (pages 4 et 5, superposables) : X = (x_pt - 205,86) / 8,6013 ; Y = (505,14 - y_pt) / 8,6013.
  X croît vers la façade AVANT (droite de la page) ; Y croît vers le côté « DROIT » (haut de la page).
  Z = 0 au dessus de la semelle principale.
Les tracés et les mots sont dans le repère AFFICHÉ (792 x 612 pt, origine en haut à gauche, y vers le bas) :
voir reference/extraire_mots.py.

Une VUE = (page, origine en points, échelle, sens) ; u, v = coordonnées du modèle visibles dans la vue.
Les zooms rendent la PAGE ENTIÈRE (tournée comme à l'écran) puis découpent : pas d'ambiguïté de repère.
"""
import json
import math
from functools import lru_cache
from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageFont

ICI = Path(__file__).resolve().parent
REF = ICI.parent
import sys  # noqa: E402
sys.path.insert(0, str(REF))
from plan_pdf import chemin_pdf  # noqa: E402
PDF = chemin_pdf(REF)          # PLAN_PDF, sinon l'unique .pdf de reference\
ZOOMS = ICI / "zooms"
ZOOMS.mkdir(exist_ok=True)
ECH = 8.6013  # points par pied (feuilles réduites)

_doc = None


def doc():
    global _doc
    if _doc is None:
        _doc = fitz.open(PDF)
    return _doc


@lru_cache(maxsize=None)
def mots(page):
    return json.loads((REF / "pages" / f"mots_page_{page:02d}.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def traces(page):
    return json.loads((REF / "pages" / f"traces_page_{page:02d}.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=8)
def image_page(page, dpi):
    pix = doc()[page - 1].get_pixmap(dpi=dpi)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def pi_po(v, frac=16):
    """Pieds décimaux -> texte pieds-pouces au 1/16 (forme 10'-0 11/16")."""
    if v is None:
        return "-"
    s = "-" if v < 0 else ""
    tot = round(abs(v) * 12 * frac)
    pi, reste = divmod(tot, 12 * frac)
    po, f = divmod(reste, frac)
    if f:
        g = math.gcd(f, frac)
        return f"{s}{pi}'-{po} {f // g}/{frac // g}\""
    return f"{s}{pi}'-{po}\""


def po(v):
    """Pieds -> pouces (texte court au 1/16)."""
    tot = round(v * 12 * 16)
    p, f = divmod(abs(tot), 16)
    s = "-" if tot < 0 else ""
    if f:
        g = math.gcd(f, 16)
        return f"{s}{p} {f // g}/{16 // g}\""
    return f"{s}{p}\""


class Vue:
    """Vue orthogonale : u = (x - x0) * su / ech ; v = (y - y0) * sv / ech (x, y en points affichés)."""

    def __init__(self, nom, page, x0, y0, ech=ECH, su=1, sv=-1, nom_u="X", nom_v="Y"):
        self.nom, self.page, self.x0, self.y0, self.ech = nom, page, x0, y0, ech
        self.su, self.sv, self.nom_u, self.nom_v = su, sv, nom_u, nom_v

    def uv(self, x, y):
        return (x - self.x0) * self.su / self.ech, (y - self.y0) * self.sv / self.ech

    def pt(self, u, v):
        return self.x0 + u * self.ech / self.su, self.y0 + v * self.ech / self.sv

    def zoom(self, u0, v0, u1, v1, dpi=300, nom=None, pas=1.0, etiquettes=True, grille=True):
        """Rend la zone (u0..u1, v0..v1) en pieds, avec une grille aux `pas` pieds, dans zooms/."""
        xa, ya = self.pt(u0, v0)
        xb, yb = self.pt(u1, v1)
        x0, x1 = sorted((xa, xb))
        y0, y1 = sorted((ya, yb))
        k = dpi / 72.0
        im = image_page(self.page, dpi).crop((int(x0 * k), int(y0 * k), int(x1 * k), int(y1 * k))).copy()
        if grille:
            dr = ImageDraw.Draw(im, "RGBA")
            try:
                fnt = ImageFont.truetype("arial.ttf", max(10, int(dpi / 20)))
            except OSError:
                fnt = ImageFont.load_default()
            umin, umax = sorted((u0, u1))
            vmin, vmax = sorted((v0, v1))
            u = math.ceil(umin / pas) * pas
            while u <= umax + 1e-9:
                x, _ = self.pt(u, 0)
                px = (x - int(x0 * k) / k) * k
                fort = abs(u - round(u / 5) * 5) < 1e-6
                dr.line([(px, 0), (px, im.height)], fill=(255, 0, 0, 120 if fort else 50), width=1)
                if etiquettes:
                    dr.text((px + 2, 2), f"{self.nom_u}{u:g}", fill=(220, 0, 0, 255), font=fnt)
                u += pas
            v = math.ceil(vmin / pas) * pas
            while v <= vmax + 1e-9:
                _, y = self.pt(0, v)
                py = (y - int(y0 * k) / k) * k
                fort = abs(v - round(v / 5) * 5) < 1e-6
                dr.line([(0, py), (im.width, py)], fill=(0, 0, 255, 120 if fort else 50), width=1)
                if etiquettes:
                    dr.text((2, py + 1), f"{self.nom_v}{v:g}", fill=(0, 0, 220, 255), font=fnt)
                v += pas
        nom = nom or f"{self.nom}_{u0:g}_{v0:g}.png"
        im.save(ZOOMS / nom)
        return ZOOMS / nom

    def segments(self, u0, v0, u1, v1, types=("l", "re", "c", "qu"), wmin=None, wmax=None):
        """Segments dont les deux bouts sont dans la zone, convertis en (u, v).
        Retour : (type, ua, va, ub, vb, largeur, couleur, remplissage, brut)."""
        out = []
        umin, umax = sorted((u0, u1))
        vmin, vmax = sorted((v0, v1))
        for s in traces(self.page):
            if s[0] not in types:
                continue
            if wmin is not None and s[5] < wmin:
                continue
            if wmax is not None and s[5] > wmax:
                continue
            ua, va = self.uv(s[1], s[2])
            ub, vb = self.uv(s[3], s[4])
            if umin <= ua <= umax and umin <= ub <= umax and vmin <= va <= vmax and vmin <= vb <= vmax:
                out.append((s[0], ua, va, ub, vb, s[5], s[6], s[7], s))
        return out

    def mots(self, u0, v0, u1, v1):
        out = []
        umin, umax = sorted((u0, u1))
        vmin, vmax = sorted((v0, v1))
        for m in mots(self.page):
            cu, cv = self.uv((m[0] + m[2]) / 2, (m[1] + m[3]) / 2)
            if umin <= cu <= umax and vmin <= cv <= vmax:
                out.append((round(cu, 3), round(cv, 3), m[4], m))
        return out


# ---------------------------------------------------------------------------------------------------
# VUES DU PROJET : à établir pour chaque plan (origine = point du repère commun, en points AFFICHÉS ; ECH = points par
# pied, à MESURER sur deux longues chaînes de cotes : une feuille réduite a une échelle écrite fausse).
# Exemple : les vues établies pour Bungalow (6 feuilles Lettre réduites, tournées de 270°, ECH 8,6013) ;
# elles ne valent que pour ce PDF.
#
# SS = Vue("ss", 4, 205.86, 505.14)      # page 4 : plan des fondations (sous-sol)
# RDC = Vue("rdc", 5, 205.86, 505.14)    # page 5 : plan du rez-de-chaussée
# # Élévations : u = coordonnée horizontale du modèle (Y ou X), v = Z (Z0 = dessus des semelles en tirets).
# FACADE = Vue("facade", 2, 179.52, 280.92, ECH, 1, -1, "Y", "Z")     # vue de l'avant (+X), Y croît vers la droite
# DROIT = Vue("droit", 2, 534.29, 565.92, ECH, -1, -1, "X", "Z")      # vue du côté +Y, X croît vers la gauche
# ARRIERE = Vue("arriere", 3, 533.52, 271.68, ECH, -1, -1, "Y", "Z")  # vue de l'arrière (-X), Y croît vers la gauche
# GAUCHE = Vue("gauche", 3, 149.16, 561.84, ECH, 1, -1, "X", "Z")     # vue du côté -Y, X croît vers la droite
# ---------------------------------------------------------------------------------------------------


def __getattr__(nom):
    """Vue demandée par un script voisin (getattr(O, "RDC")) mais pas encore définie ci-dessus."""
    if nom.isupper():
        raise AttributeError(f"Vue « {nom.lower()} » non définie : la définir en bas de outils_releve.py "
                             f"(voir l'exemple commenté de Bungalow).")
    raise AttributeError(nom)
