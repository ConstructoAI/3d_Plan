"""Outils de relevé (brouillon de l'agent DAO) : zooms en points PDF avec grille du repère commun.

Modèle tiré de Maison_Agrandissement_Blender\\reference\\releve_travail\\ (voir modeles\\LISEZMOI.md).
Le PDF : variable PLAN_PDF, sinon l'unique .pdf du dossier parent (reference\\), par ..\\plan_pdf.py.

Repère commun : à écrire dans REPERE.md du projet (ex. Agrandissement : X vers l'est depuis l'axe A,
Y vers le nord depuis la face ext. du mur sud de l'agrandissement, Z depuis le dessus de l'empattement).

Une VUE = (page, fonction points -> (u, v) en pieds, fonction inverse), où (u, v) sont les deux
coordonnées du modèle visibles dans la vue (plan : X, Y ; élévation sud : X, Z ; etc.).
Les scripts voisins (cloisons.py, vantaux.py, carreaux.py…) prennent le NOM d'une vue définie en bas de
ce fichier : `python cloisons.py rdc u0 v0 u1 v1` lit la vue RDC.
"""
import json
import math
import sys
from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageFont

ICI = Path(__file__).resolve().parent
REF = ICI.parent
sys.path.insert(0, str(REF))
from plan_pdf import chemin_pdf  # noqa: E402

PDF = chemin_pdf(REF)
ZOOMS = ICI / "zooms"
ZOOMS.mkdir(exist_ok=True)

_doc = None


def doc():
    global _doc
    if _doc is None:
        _doc = fitz.open(PDF)
    return _doc


def mots(page):
    return json.loads((REF / "pages" / f"mots_page_{page:02d}.json").read_text(encoding="utf-8"))


def traces(page):
    return json.loads((REF / "pages" / f"traces_page_{page:02d}.json").read_text(encoding="utf-8"))


def pi_po(v, frac=16):
    """Pieds décimaux -> texte pieds-pouces au 1/16 (forme 10'-0 11/16")."""
    s = "-" if v < 0 else ""
    tot = round(abs(v) * 12 * frac)  # en 1/16 po
    pi, reste = divmod(tot, 12 * frac)
    po, f = divmod(reste, frac)
    if f:
        g = math.gcd(f, frac)
        return f"{s}{pi}'-{po} {f // g}/{frac // g}\""
    return f"{s}{pi}'-{po}\""


class Vue:
    """Vue orthogonale : u = (x - x0) * su / ech ; v = (y - y0) * sv / ech (x, y en points PDF)."""

    def __init__(self, nom, page, x0, y0, ech, su=1, sv=-1, nom_u="X", nom_v="Y"):
        self.nom, self.page, self.x0, self.y0, self.ech = nom, page, x0, y0, ech
        self.su, self.sv, self.nom_u, self.nom_v = su, sv, nom_u, nom_v

    def uv(self, x, y):
        return (x - self.x0) * self.su / self.ech, (y - self.y0) * self.sv / self.ech

    def pt(self, u, v):
        return self.x0 + u * self.ech / self.su, self.y0 + v * self.ech / self.sv

    def zoom(self, u0, v0, u1, v1, dpi=200, nom=None, pas=1.0, etiquettes=True):
        """Rend la zone (u0..u1, v0..v1) en pieds, avec grille aux `pas` pieds, dans zooms/."""
        xa, ya = self.pt(u0, v0)
        xb, yb = self.pt(u1, v1)
        clip = fitz.Rect(min(xa, xb), min(ya, yb), max(xa, xb), max(ya, yb))
        page = doc()[self.page - 1]
        pix = page.get_pixmap(dpi=dpi, clip=clip)
        im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        dr = ImageDraw.Draw(im, "RGBA")
        k = dpi / 72.0
        try:
            fnt = ImageFont.truetype("arial.ttf", max(10, int(dpi / 16)))
        except OSError:
            fnt = ImageFont.load_default()
        umin, umax = sorted((u0, u1))
        vmin, vmax = sorted((v0, v1))
        u = math.ceil(umin / pas) * pas
        while u <= umax + 1e-9:
            x, _ = self.pt(u, 0)
            px = (x - clip.x0) * k
            fort = abs(u - round(u / 5) * 5) < 1e-6
            dr.line([(px, 0), (px, im.height)], fill=(255, 0, 0, 110 if fort else 55), width=1)
            if etiquettes:
                dr.text((px + 2, 2), f"{self.nom_u}{u:g}", fill=(220, 0, 0, 255), font=fnt)
            u += pas
        v = math.ceil(vmin / pas) * pas
        while v <= vmax + 1e-9:
            _, y = self.pt(0, v)
            py = (y - clip.y0) * k
            fort = abs(v - round(v / 5) * 5) < 1e-6
            dr.line([(0, py), (im.width, py)], fill=(0, 0, 255, 110 if fort else 55), width=1)
            if etiquettes:
                dr.text((2, py + 1), f"{self.nom_v}{v:g}", fill=(0, 0, 220, 255), font=fnt)
            v += pas
        nom = nom or f"{self.nom}_{u0:g}_{v0:g}.png"
        im.save(ZOOMS / nom)
        return ZOOMS / nom

    def segments(self, u0, v0, u1, v1, types=("l", "re", "c", "qu")):
        """Segments des tracés dont les deux bouts sont dans la zone, convertis en (u, v)."""
        out = []
        umin, umax = sorted((u0, u1))
        vmin, vmax = sorted((v0, v1))
        for s in traces(self.page):
            if s[0] not in types:
                continue
            ua, va = self.uv(s[1], s[2])
            ub, vb = self.uv(s[3], s[4])
            if umin <= ua <= umax and umin <= ub <= umax and vmin <= va <= vmax and vmin <= vb <= vmax:
                out.append((s[0], ua, va, ub, vb, s[5], s[6], s[7]))
        return out

    def mots(self, u0, v0, u1, v1):
        out = []
        umin, umax = sorted((u0, u1))
        vmin, vmax = sorted((v0, v1))
        for m in mots(self.page):
            cu, cv = self.uv((m[0] + m[2]) / 2, (m[1] + m[3]) / 2)
            if umin <= cu <= umax and vmin <= cv <= vmax:
                out.append((round(cu, 3), round(cv, 3), m[4]))
        return out


# ---------------------------------------------------------------------------------------------------
# VUES DU PROJET : à établir pour chaque plan (origine = point du repère commun lu sur la page, en points
# PDF ; ech = points par pied, 18 au 1/4"). Vérifier chaque origine sur les murs et les lignes de niveau.
# Exemple : les vues établies pour Agrandissement (plan rév. 4, ARCH D, 1/4") ; les décommenter
# ne sert à rien ailleurs, elles ne valent que pour ce PDF.
#
# RDC = Vue("rdc", 3, 454.88, 1101.14, 18.0)            # A101, plan du RDC proposé, 1/4"
# ETAGE = Vue("etage", 4, 585.56, 1102.28, 18.0)        # A102, plan de l'étage proposé, 1/4"
# FOND = Vue("fond", 2, 523.28, 1155.62, 18.0)          # A100, fondations proposé/existant, 1/4"
# # Élévations : u = coordonnée horizontale du modèle, v = Z (dessus de l'empattement = 0)
# SUD = Vue("sud", 5, 524.96, 837.02, 18.0, 1, -1, "X", "Z")      # A200 haut, vue du sud (ouest à gauche)
# EST = Vue("est", 5, 1001.12, 1576.88, 18.0, 1, -1, "Y", "Z")    # A200 bas, vue de l'est (sud à gauche)
# OUEST = Vue("ouest", 6, 1888.88, 958.88, 18.0, -1, -1, "Y", "Z")  # A201 haut, vue de l'ouest (nord à gauche)
# NORD = Vue("nord", 6, 1156.70, 1566.86, 18.0, -1, -1, "X", "Z")  # A201 bas, vue du nord (est à gauche)
# COUPE = Vue("coupe", 7, 1073.90, 714.74, 18.0, 1, -1, "X", "Z")  # A300 coupe AA (à vérifier)
# ---------------------------------------------------------------------------------------------------


def __getattr__(nom):
    """Vue demandée par un script voisin (getattr(O, "RDC")) mais pas encore définie ci-dessus."""
    if nom.isupper():
        raise AttributeError(f"Vue « {nom.lower()} » non définie : la définir en bas de outils_releve.py "
                             f"(voir l'exemple commenté du projet Agrandissement).")
    raise AttributeError(nom)
