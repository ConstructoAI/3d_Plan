# -*- coding: utf-8 -*-
r"""pdf_3d.py — d'un .blend à un PDF 3D (le modèle se manipule à la souris dans le lecteur PDF).

UNE commande, depuis n'importe quel .blend du poste (maison, garage, équipement, charpente) :

    & $env:BM_PYTHON -X utf8 -s modeles\pdf_3d\pdf_3d.py <fichier.blend> --sortie x.pdf --titre "…"
        [--ligne "…" (répétable)] [--mention "…"] [--auteur "…"] [--sujet "…"] [--simple]
        [--unite m|mm|po]
        [--exclure-collections A,B,…] [--inclure-collections A,B,…] [--plafond N] [--tout-garder]
        [--arbre auto|collections|prop1,prop2,…] [--nom-prop marque] [--etiquettes fichier.json]
        [--vue "Nom=azimut,élévation[,ortho]" (répétable)] [--cameras] [--vues-par-groupe]
        [--vue-defaut N] [--rendu Solid] [--eclairage CAD] [--fond r,v,b]
        [--sans-normales] [--sans-arbre-ouvert] [--sans-compression] [--sans-fiches]
        [--particules] [--caches] [--interdit "terme" (répétable)]
        [--travail dossier] [--u3d fichier.u3d] [--controle rapport.txt]

Elle lance elle-même Blender en arrière-plan (extraction, sans carte graphique), puis Node
(écriture), relit ce qu'elle a produit (structure du PDF, U3D relu par un lecteur à part, comptes
et boîte englobante face à Blender) et finit par la ligne  PDF_3D_OK  — ou par un code de sortie
non nul avec la cause :
    2 arguments ; 3 outil introuvable ; 4 extraction ; 5 trop de triangles ; 6 écriture ;
    7 contrôle en échec ; 8 lignes trop nombreuses pour la page.

Deux versions :
  --simple     le PDF 3D TEL QUE L'ERP LE FAIT (ses fichiers, copiés tels quels dans erp\) : un
               seul maillage gris, pas d'arbre, cadrage laissé au lecteur ; plafond de l'ERP.
  (défaut)     la version « de fabrication » : une pièce par objet dans l'arbre du modèle,
               maillages partagés, couleurs des matériaux, vues nommées, fiche de chaque pièce.

Le .blend n'est JAMAIS modifié ni enregistré. Aucun chemin en dur : Blender, Node et Python
viennent de outils\chemins.py (ou des variables BM_BLENDER, BM_NODE du lanceur).
Mode d'emploi complet : LISEZMOI.md, à côté de ce fichier.
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata

sys.dont_write_bytecode = True          # pas de __pycache__ dans le dossier de l'outil
ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.environ.get("BM_RACINE") or os.path.abspath(os.path.join(ICI, "..", ".."))
sys.path.insert(0, ICI)

MENTION_DEFAUT = ("PRÉPARÉ PAR UNE IA (CLAUDE) — document de travail, à valider et à sceller par un "
                  "professionnel. Aucun sceau.")
# Propriétés du document (« Fichier > Propriétés » du lecteur) : l'auteur dit ce qui est vrai.
AUTEUR_DEFAUT = "Préparé par une IA (Claude)"
REPLI_1 = "Modèle 3D — ouvrez ce fichier avec Adobe Acrobat Reader, PDF-XChange Editor ou Foxit,"
REPLI_2 = "autorisez le contenu 3D si le lecteur le demande, puis cliquez ici pour le faire pivoter à la souris."
UNITES = {"m": (1.0, "mètre"), "mm": (0.001, "millimètre"), "po": (0.0254, "pouce")}
# noms de collections tenus pour du DÉCOR (cherchés sans casse ni accents, en mot entier)
DECOR = ["sol", "ctx", "ciel", "fond", "rue", "route", "studio", "haie", "jardin", "amenagement",
         "amenagements", "sky", "ground", "background"]
# … et débuts de mot : « paysag » prend paysage, paysager, paysagement ; « arbr » arbre(s) ; etc.
DECOR_DEBUTS = ["terrain", "gazon", "pelous", "herbe", "vegeta", "arbr", "arbust", "plante", "plantation",
                "foret", "bosquet", "decor", "context", "environ", "paysag", "voisin", "landscap", "tree",
                "grass"]
PLAFOND_FABRICATION = 2_000_000
LIGNES_MAX = 7           # ce que la page de l'ERP peut porter sous le cadre (mesuré dans exportPdf3d.ts)
META_EXCLUES = {"agent"}


class Arret(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def dire(msg=""):
    print(msg, flush=True)


def sans_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def cle_naturelle(s):
    return [int(x) if x.isdigit() else sans_accents(x).lower() for x in re.split(r"(\d+)", str(s))]


def nombre(n):
    return re.sub(r"(?<=\d)(?=(\d{3})+$)", " ", str(int(round(n))))


# ------------------------------------------------------------------------------ outils


def trouver_outils():
    """Blender, Node : par outils\\chemins.py d'abord, sinon par les variables du lanceur."""
    env_blender = dict(os.environ)
    blender = node = None
    origine = "variables BM_*"
    try:
        sys.path.insert(0, os.path.join(RACINE, "outils"))
        import chemins  # noqa
        blender = chemins.blender_exe()
        node = chemins.node_exe()
        env_blender = chemins.env_blender()
        origine = "outils\\chemins.py"
    except Exception as e:        # poste sans module de chemins : les variables suffisent
        blender = os.environ.get("BM_BLENDER")
        node = os.environ.get("BM_NODE")
        origine = "variables BM_* (chemins.py indisponible : %s)" % str(e).splitlines()[0][:80]
    for nom, exe in (("Blender", blender), ("Node", node)):
        if not exe or not os.path.isfile(exe):
            raise Arret(3, "%s introuvable (%s). Lancez la session par Demarrer-Blender.bat, ou posez "
                           "BM_BLENDER et BM_NODE." % (nom, exe))
    env_blender["CUDA_VISIBLE_DEVICES"] = "-1"        # l'extraction n'a pas besoin de la carte graphique
    env_blender["PYTHONIOENCODING"] = "utf-8"
    return blender, node, env_blender, origine


def lancer(cmd, env, journal, delai):
    t0 = time.time()
    p = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=delai)
    sortie = p.stdout.decode("utf-8", errors="replace")
    with open(journal, "w", encoding="utf-8", newline="\n") as f:
        f.write(sortie)
    return p.returncode, sortie, time.time() - t0


# ------------------------------------------------------------------------------ arbre du modèle


def est_decor(nom):
    mots = re.split(r"[^a-z0-9]+", sans_accents(nom).lower())
    return any(m in DECOR or any(m.startswith(d) for d in DECOR_DEBUTS) for m in mots if m)


def groupe_decor(o):
    """La collection de DÉCOR (la plus haute) qui porte l'objet, ou None."""
    for nom in o["collections"]:
        if est_decor(nom):
            return nom
    return None


def ecarter_decor(scene, plafond, unite_nom):
    """Choisit les collections de décor à écarter. Rend (liste, masque des objets gardés).

    Une collection de décor (terrain, végétation, contexte… : voir DECOR) n'est écartée QUE si
    elle écrase le modèle : elle en multiplie l'étendue par plus de 3 (le bâtiment ne serait
    qu'un point dans le cadre), elle pèse à elle seule plus de triangles que tout le reste, ou le
    plafond de triangles est dépassé. Chaque écart est rendu avec sa raison, pour être DIT."""
    import numpy as np
    objs = scene["objets"]
    tris = np.array([scene["maillages"][o["maillage"]]["triangles"] for o in objs], dtype=np.int64)
    bb = np.array([o["boite"] for o in objs], dtype=float)
    grp = [groupe_decor(o) for o in objs]
    garde = np.ones(len(objs), bool)
    ecartes = []

    def diag(m):
        if not m.any():
            return 0.0
        return float(np.linalg.norm(bb[m][:, 1, :].max(axis=0) - bb[m][:, 0, :].min(axis=0)))

    while True:
        total = int(tris[garde].sum())
        d_tout = diag(garde)
        meilleur = None
        for nom in sorted({g for g, k in zip(grp, garde) if g and k}):
            m = np.array([g == nom for g in grp]) & garde
            reste = garde & ~m
            if not reste.any():
                continue                    # ne jamais tout écarter
            t = int(tris[m].sum())
            d_sans = diag(reste)
            if d_sans > 0 and d_tout > 3 * d_sans:
                raison = "elle porterait l'étendue du modèle de %.1f à %.1f %ss" % (d_sans, d_tout, unite_nom)
                poids = 1e12 * d_tout / d_sans
            elif t > total - t:
                raison = "elle pèse à elle seule %d %% des triangles" % round(100.0 * t / total)
                poids = 1e6 + t
            elif total > plafond:
                raison = "le plafond de %s triangles est dépassé" % nombre(plafond)
                poids = t
            else:
                continue
            if meilleur is None or poids > meilleur[0]:
                meilleur = (poids, nom, m, raison, t)
        if meilleur is None:
            break
        _, nom, m, raison, t = meilleur
        ecartes.append((nom, int(m.sum()), t, raison))
        garde &= ~m
    return ecartes, garde


def choisir_niveaux(scene, arbre):
    """Les propriétés d'objet qui font les niveaux de l'arbre ; [] = les collections seules."""
    if arbre == "collections":
        return []
    if arbre != "auto":
        return [x.strip() for x in arbre.split(",") if x.strip()]
    if any("assemblage" in o["proprietes"] for o in scene["objets"]):
        return ["assemblage", "repere", "boulon"]
    return []


def chemin_objet(o, niveaux):
    """Suite des étiquettes de groupe qui mènent à l'objet.

    Règle unique : si l'objet porte la 1re propriété de la liste, son chemin est fait des valeurs
    des propriétés présentes ; sinon c'est sa collection, puis les valeurs des propriétés suivantes
    qu'il porte. Deux étiquettes identiques de suite n'en font qu'une."""
    p = o["proprietes"]
    brut = []
    if niveaux and niveaux[0] in p:
        brut = [str(p[n]) for n in niveaux if n in p and str(p[n]) != ""]
    else:
        brut = list(o["collections"]) + [str(p[n]) for n in niveaux[1:] if n in p and str(p[n]) != ""]
    out = []
    for x in brut:
        if not out or out[-1] != x:
            out.append(x)
    return out


def construire_arbre(scene, niveaux, nom_prop, etiquettes, fiches, avec_fiches):
    """Rend les nœuds (parents d'abord), les ressources et les matériaux, noms uniques."""
    pris = set()

    def unique(nom):
        nom = nom.strip() or "sans nom"
        if nom not in pris:
            pris.add(nom)
            return nom
        k = 2
        while "%s (%d)" % (nom, k) in pris:
            k += 1
        nom = "%s (%d)" % (nom, k)
        pris.add(nom)
        return nom

    # 1. groupes : un par chemin distinct
    chemins = {}
    for i, o in enumerate(scene["objets"]):
        ch = tuple(chemin_objet(o, niveaux))
        for k in range(1, len(ch) + 1):
            chemins.setdefault(ch[:k], None)
        o["_chemin"] = ch
    noeuds = []
    nom_groupe = {(): ""}
    for ch in sorted(chemins, key=lambda c: [cle_naturelle(x) for x in c]):
        etq = etiquettes.get(ch[-1], ch[-1])
        nom = unique(etq)
        nom_groupe[ch] = nom
        meta = {}
        if avec_fiches and ch[-1] in fiches:
            meta.update({str(k): str(v) for k, v in fiches[ch[-1]].items()})
        noeuds.append({"nom": nom, "parent": nom_groupe[ch[:-1]], "type": "groupe", "cle": ch[-1],
                       "chemin": list(ch), "meta": meta})
    # 2. ressources : un nom par maillage employé
    employes = sorted({o["maillage"] for o in scene["objets"]})
    pris_res = set()
    nom_res = {}
    for i in employes:
        base = scene["maillages"][i]["nom"] or "maillage"
        nom = base
        k = 2
        while nom in pris_res:
            nom = "%s #%d" % (base, k)
            k += 1
        pris_res.add(nom)
        nom_res[i] = nom
    ressources = [{"nom": nom_res[i], "maillage": i} for i in employes]
    # 3. modèles
    ordre = sorted(range(len(scene["objets"])),
                   key=lambda i: ([cle_naturelle(x) for x in scene["objets"][i]["_chemin"]],
                                  cle_naturelle(scene["objets"][i]["nom"])))
    for i in ordre:
        o = scene["objets"][i]
        p = o["proprietes"]
        if nom_prop and nom_prop in p and str(p[nom_prop]) != "":
            v = str(p[nom_prop])
            nom = "%s · %s" % (etiquettes.get(v, v), o["nom"])
        else:
            v = None
            nom = etiquettes.get(o["nom"], o["nom"])
        meta = {}
        if avec_fiches:
            meta["Objet"] = o["nom"]
            for k, val in p.items():
                if k not in META_EXCLUES:
                    meta[k] = str(val)
            if v is not None and v in fiches:
                meta.update({str(k): str(x) for k, x in fiches[v].items()})
            meta["Matériau"] = " + ".join(o["materiaux"])
        noeuds.append({"nom": unique(nom), "parent": nom_groupe[o["_chemin"]], "type": "modele",
                       "objet": i, "ressource": nom_res[o["maillage"]], "nuanceurs": list(o["materiaux"]),
                       "matrice": o["matrice"], "meta": meta, "cle": v})
    # 4. matériaux employés
    employes_mat = []
    for o in scene["objets"]:
        for m in o["materiaux"]:
            if m not in employes_mat:
                employes_mat.append(m)
    par_nom = {m["nom"]: m for m in scene["materiaux"]}
    materiaux = []
    for nom in sorted(employes_mat, key=cle_naturelle):
        m = par_nom[nom]
        c = m["couleur"]
        # un métal nu reflète son environnement : dans un lecteur PDF il n'y en a pas, on
        # l'éclaircit donc un peu pour qu'il ne sorte pas noir, et on lui donne un reflet
        metal = float(m.get("metal", 0.0))
        diffus = [min(1.0, x * (1.0 + 0.12 * metal)) for x in c]
        spec = 0.10 + 0.35 * metal * (1.0 - float(m.get("rugosite", 0.5)))
        materiaux.append({
            "nom": nom, "diffus": [round(x, 5) for x in diffus],
            "ambiant": [round(x, 5) for x in diffus],
            "speculaire": [round(spec, 4)] * 3, "emissif": [0.0, 0.0, 0.0],
            "reflectivite": round(0.15 + 0.35 * (1.0 - float(m.get("rugosite", 0.5))), 4),
            "opacite": m["opacite"], "source": m["source"], "couleur_blender": m["couleur_lineaire"],
        })
    for o in scene["objets"]:
        o.pop("_chemin", None)
    return noeuds, ressources, materiaux


# ------------------------------------------------------------------------------ vues


def _norme(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def _vect(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def _scal(a, b):
    return sum(x * y for x, y in zip(a, b))


def coins_boite(b):
    return [[x, y, z] for x in (b[0][0], b[1][0]) for y in (b[0][1], b[1][1]) for z in (b[0][2], b[1][2])]


def vue_orbite(nom, azimut, elevation, boite, cadre, fov=30.0, ortho=False, marge=1.06, points=None):
    """Vue qui cadre le modèle depuis une direction donnée.

    azimut 0 : la caméra est DEVANT (côté -Y) et regarde vers +Y ; 90 : à droite (+X) ; 180 :
    derrière (+Y) ; -90 : à gauche. élévation : angle au-dessus de l'horizon ; 90 = du dessus.
    Repère de la caméra d'un PDF (ISO 32000-1, 13.6.5) : x à droite, y en haut, elle regarde
    vers +z ; /C2W = [droite, haut, regard, position], un trièdre INDIRECT dans un monde direct.
    `points` : ce qu'il faut voir en entier (défaut : les 8 coins de la boîte) ; on y passe les
    coins des boîtes de chaque pièce, pour un cadrage plus serré que la boîte d'ensemble."""
    import numpy as np
    az = math.radians(azimut)
    el = math.radians(elevation)
    vers_cam = [math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)]
    regard = [-x for x in vers_cam]
    h = [-math.sin(az), math.cos(az), 0.0]              # avant de la vue, à plat
    if abs(math.cos(el)) < 1e-6:
        haut = [x * (1 if el > 0 else -1) for x in h]
    else:
        z = [0.0, 0.0, 1.0]
        k = _scal(z, regard)
        haut = _norme([z[i] - k * regard[i] for i in range(3)])
    droite = _norme(_vect(regard, haut))
    haut = _norme(_vect(droite, regard))
    pts = np.array(points if points is not None else coins_boite(boite), dtype=float)
    larg, haut_c = cadre
    if larg >= haut_c:
        tan_v = math.tan(math.radians(fov) / 2)
        tan_h = tan_v * larg / haut_c
    else:
        tan_h = math.tan(math.radians(fov) / 2)
        tan_v = tan_h * haut_c / larg
    # on centre la vue sur le milieu de ce qu'elle montre (et non sur le centre de la boîte)
    px = pts @ np.array(droite)
    py = pts @ np.array(haut)
    pz = pts @ np.array(regard)
    mx, my, mz = (px.min() + px.max()) / 2, (py.min() + py.max()) / 2, (pz.min() + pz.max()) / 2
    c = [mx * droite[i] + my * haut[i] + mz * regard[i] for i in range(3)]
    x = np.abs(px - mx)
    y = np.abs(py - my)
    z = pz - mz
    rayon = float(np.sqrt(((pts.max(axis=0) - pts.min(axis=0)) ** 2).sum())) / 2 or 1.0
    d = float(np.maximum(x / tan_h - z, y / tan_v - z).max())
    d = max(d * marge, rayon * 0.05, float(-z.min()) * 1.02 + rayon * 0.01)
    pos = [c[i] + d * vers_cam[i] for i in range(3)]
    vue = {"nom": nom, "c2w": [round(v, 6) for v in droite + haut + regard] + [round(v, 5) for v in pos],
           "co": round(d, 5), "projection": "O" if ortho else "P", "fov": fov}
    if ortho:
        # échelle orthographique : la plus petite dimension du cadre couvre cette étendue (unités)
        ex, ey = float(x.max()) * 2, float(y.max()) * 2
        if larg >= haut_c:
            etendue = max(ey, ex * haut_c / larg)
        else:
            etendue = max(ex, ey * larg / haut_c)
        vue["etendue_ortho"] = round(max(etendue * marge, 1e-6), 5)
    return vue


def vue_camera(cam, boite, cadre):
    """Vue tirée d'une caméra du .blend.

    Cadrage APPROCHÉ, et il faut le savoir : le cadre du PDF n'a pas les proportions du rendu, et
    une vue de PDF ne sait pas DÉCENTRER l'objectif. Une caméra d'architecture (de niveau, décentrée
    vers le haut pour garder les verticales droites) est donc ré-orientée vers le centre de son
    image : on voit la même chose, avec des verticales qui fuient un peu."""
    c = [(boite[0][i] + boite[1][i]) / 2 for i in range(3)]
    pos = list(cam["position"])
    regard = _norme(cam["regard"])
    droite = _norme(cam["droite"])
    haut = _norme(_vect(droite, regard))
    sx, sy = cam.get("decentrement", [0.0, 0.0])
    rx, ry = cam["rendu"]
    vue = {"nom": cam["nom"], "source": "caméra du .blend"}
    if cam["type"] == "ORTHO":
        ech = cam["echelle_ortho"]                       # étendue de la plus grande dimension du rendu
        pos = [pos[i] + sx * ech * droite[i] + sy * ech * haut[i] for i in range(3)]
        vertical = ech * (ry / rx if rx >= ry else 1.0)
        horizontal = ech * (1.0 if rx >= ry else rx / ry)
        vue["projection"] = "O"
        vue["etendue_ortho"] = round(vertical if cadre[0] >= cadre[1] else horizontal, 5)
    else:
        if sx or sy:
            k = 2 * math.tan(math.radians(cam["champ_h_deg" if cam.get("ajustement", "HORIZONTAL") == "HORIZONTAL"
                                              else "champ_v_deg"]) / 2)
            regard = _norme([regard[i] + sx * k * droite[i] + sy * k * haut[i] for i in range(3)])
            droite = _norme(_vect(regard, haut))
            haut = _norme(_vect(droite, regard))
        vue["projection"] = "P"
        vue["fov"] = round(cam["champ_v_deg"] if cadre[0] >= cadre[1] else cam["champ_h_deg"], 3)
    co = max(_scal([c[i] - pos[i] for i in range(3)], regard), 0.25)
    vue["c2w"] = [round(x, 6) for x in droite + haut + regard] + [round(x, 5) for x in pos]
    vue["co"] = round(co, 5)
    return vue


def lire_vue(texte):
    m = re.match(r"^\s*(.+?)\s*=\s*(-?[\d.]+)\s*[,;]\s*(-?[\d.]+)\s*(?:[,;]\s*(ortho|perspective))?\s*$", texte)
    if not m:
        raise Arret(2, "--vue « %s » : attendu « Nom=azimut,élévation » ou « Nom=azimut,élévation,ortho »" % texte)
    return m.group(1), float(m.group(2)), float(m.group(3)), m.group(4) == "ortho"


# ------------------------------------------------------------------------------ principal


def analyser(argv):
    p = argparse.ArgumentParser(prog="pdf_3d.py", add_help=True,
                                description="D'un .blend à un PDF 3D (voir LISEZMOI.md).")
    p.add_argument("blend", help="le fichier .blend (il n'est ni modifié ni enregistré)")
    p.add_argument("--sortie", required=True, help="le PDF à écrire")
    p.add_argument("--titre", default=None, help="titre en haut de la page (défaut : le nom du .blend)")
    p.add_argument("--ligne", action="append", default=[], help="ligne sous le cadre, répétable ; "
                   "{faces} {sommets} {objets} {groupes} {maillages} {unite} y sont remplacés")
    p.add_argument("--mention", default=MENTION_DEFAUT, help="dernière ligne (responsabilité) ; \"\" pour l'ôter")
    p.add_argument("--auteur", default=None, help="propriété « Auteur » du PDF (défaut : « %s ») ; "
                   "\"\" pour ne pas l'écrire" % AUTEUR_DEFAUT)
    p.add_argument("--sujet", default=None, help="propriété « Sujet » du PDF (défaut : la mention) ; "
                   "\"\" pour ne pas l'écrire")
    p.add_argument("--simple", action="store_true", help="le PDF 3D tel que l'ERP le fait (un maillage gris)")
    p.add_argument("--unite", choices=sorted(UNITES), default="m", help="unité des coordonnées écrites (défaut m)")
    p.add_argument("--exclure-collections", default="", help="collections à écarter, séparées par des virgules")
    p.add_argument("--inclure-collections", default="", help="ne garder QUE ces collections")
    p.add_argument("--plafond", type=int, default=None, help="triangles posés au plus (défaut : celui de l'ERP "
                   "en --simple, %d sinon)" % PLAFOND_FABRICATION)
    p.add_argument("--tout-garder", "--avec-decor", dest="tout_garder", action="store_true",
                   help="ne jamais écarter le décor (terrain, végétation, contexte) de soi-même")
    p.add_argument("--particules", action="store_true", help="garder les instances de particules")
    p.add_argument("--caches", action="store_true", help="garder les objets masqués au rendu ou à la caméra")
    p.add_argument("--arbre", default="auto", help="auto, collections, ou propriétés d'objet « p1,p2,… »")
    p.add_argument("--nom-prop", default="marque", help="propriété d'objet qui nomme la pièce (défaut marque)")
    p.add_argument("--etiquettes", default=None, help="JSON {etiquettes:{clé:libellé}, fiches:{clé:{…}}}")
    p.add_argument("--sans-fiches", action="store_true", help="ne pas écrire la fiche (métadonnées) des pièces")
    p.add_argument("--vue", action="append", default=[], help="« Nom=azimut,élévation[,ortho] », répétable")
    p.add_argument("--cameras", action="store_true", help="ajouter une vue par caméra du .blend")
    p.add_argument("--vues-par-groupe", action="store_true", help="ajouter une vue qui isole chaque groupe de 1er niveau")
    p.add_argument("--vue-defaut", default="1", help="numéro (à partir de 1) ou nom de la vue d'ouverture")
    p.add_argument("--rendu", default="Solid", help="mode de rendu des vues (Solid, SolidOutline, Illustration…)")
    p.add_argument("--eclairage", default="CAD", help="éclairage des vues (CAD, Day, White, Headlamp…)")
    p.add_argument("--fond", default="0.96,0.96,0.97", help="couleur de fond r,v,b entre 0 et 1")
    p.add_argument("--sans-normales", action="store_true", help="laisser le lecteur calculer les normales")
    p.add_argument("--sans-arbre-ouvert", action="store_true", help="ne pas demander l'ouverture de l'arbre du modèle")
    p.add_argument("--sans-compression", action="store_true", help="flux 3D sans Flate (comme l'ERP)")
    p.add_argument("--interdit", action="append", default=[], help="terme qui ne doit pas paraître dans le PDF, répétable")
    p.add_argument("--travail", default=None, help="dossier des fichiers intermédiaires (gardés)")
    p.add_argument("--u3d", default=None, help="écrire aussi le U3D seul")
    p.add_argument("--controle", default=None, help="fichier du rapport de contrôle (défaut : <sortie>.controle.txt)")
    p.add_argument("--delai", type=int, default=1800, help="délai de Blender, en secondes")
    p.add_argument("--compat", default="", help="réglages de compatibilité du U3D, pour chercher ce qui gêne un "
                   "lecteur : « compresse=0,priorite=0,zeroFinal=1,chainesDeGroupe=0,fiches=0,unitesDefinies=0,"
                   "attributsNuancage=15 » (compresse=0 : U3D sans compression, la forme qu'écrit l'ERP)")
    try:
        return p.parse_args(argv)
    except SystemExit as e:
        raise Arret(2 if e.code else 0, "arguments refusés")


def principal(argv):
    a = analyser(argv)
    t_debut = time.time()
    blend = os.path.abspath(a.blend)
    if not os.path.isfile(blend):
        raise Arret(2, "fichier introuvable : %s" % blend)
    sortie = os.path.abspath(a.sortie)
    os.makedirs(os.path.dirname(sortie), exist_ok=True)
    mode = "simple" if a.simple else "fabrication"
    metres, unite_nom = UNITES[a.unite]
    if a.simple and a.unite != "m":
        raise Arret(2, "--simple écrit toujours en mètres (l'écrivain de l'ERP déclare « 1 unité = 1 mètre ») ; "
                       "retirez --unite, ou retirez --simple")
    blender, node, env_blender, origine = trouver_outils()
    titre = a.titre or os.path.splitext(os.path.basename(blend))[0]
    lignes = list(a.ligne)
    if not lignes:
        lignes = ["{faces} faces — {objets} pièce(s) — unité : {unite}"]
        if not a.simple:
            lignes.append("Arbre du modèle : un clic droit sur une pièce l'isole, la masque ou zoome dessus. "
                          "Vues : menu de la barre d'outils 3D.")
    if a.mention:
        lignes.append(a.mention)
    if len(lignes) > LIGNES_MAX:
        raise Arret(8, "%d lignes demandées, la page en porte %d sous le cadre : les suivantes seraient "
                       "perdues sans un mot. Regroupez des lignes." % (len(lignes), LIGNES_MAX))
    garder = bool(a.travail)
    travail = os.path.abspath(a.travail) if a.travail else tempfile.mkdtemp(prefix="pdf3d_")
    os.makedirs(travail, exist_ok=True)
    dire("PDF 3D — %s — mode %s" % (os.path.basename(blend), "« tel que l'ERP » (--simple)" if a.simple else "« de fabrication »"))
    dire("  outils : %s" % origine)
    try:
        # ---------------------------------------------------------------- 1. extraction
        opt = {"travail": travail,
               "exclure_collections": [x.strip() for x in a.exclure_collections.split(",") if x.strip()],
               "inclure_collections": [x.strip() for x in a.inclure_collections.split(",") if x.strip()],
               "particules": a.particules, "caches": a.caches, "metres_par_unite_sortie": metres}
        f_opt = os.path.join(travail, "options_extraction.json")
        with open(f_opt, "w", encoding="utf-8", newline="\n") as f:
            json.dump(opt, f, ensure_ascii=False)
        cmd = [blender, "-b", "--factory-startup", blend, "--python", os.path.join(ICI, "extraire_blend.py"),
               "--", f_opt]
        code, sortie_b, duree = lancer(cmd, env_blender, os.path.join(travail, "journal_blender.txt"), a.delai)
        if code != 0 or "EXTRACTION_OK" not in sortie_b:
            queue = "\n".join(sortie_b.strip().splitlines()[-12:])
            raise Arret(4, "l'extraction par Blender a échoué (code %d) :\n%s" % (code, queue))
        for l_ in sortie_b.splitlines():
            if l_.startswith("[extraction] "):
                dire("  " + l_[13:])
        with open(os.path.join(travail, "scene.json"), encoding="utf-8") as f:
            scene = json.load(f)
        dire("  extraction : %.1f s" % duree)
        if not scene["objets"]:
            raise Arret(4, "rien à écrire : aucun objet à faces dans ce qui est retenu du .blend")

        # ---------------------------------------------------------------- 2. plafond et décor
        plafond_erp = None
        if a.simple:
            src = open(os.path.join(ICI, "erp", "atelier", "sceneTriangles.ts"), encoding="utf-8").read()
            m = re.search(r"MAX_TRIANGLES_PDF3D\s*=\s*([\d_]+)", src)
            if not m:
                raise Arret(6, "MAX_TRIANGLES_PDF3D introuvable dans erp\\atelier\\sceneTriangles.ts")
            plafond_erp = int(m.group(1).replace("_", ""))
        plafond = a.plafond if a.plafond else (plafond_erp if a.simple else PLAFOND_FABRICATION)
        tri = scene["triangles"]
        dire("  triangles posés : %s ; plafond : %s%s" % (nombre(tri), nombre(plafond),
             " (celui de l'ERP, MAX_TRIANGLES_PDF3D)" if a.simple and not a.plafond else ""))
        ecartes_decor = []
        if not a.tout_garder:
            ecartes_decor, garde = ecarter_decor(scene, plafond, unite_nom)
            if ecartes_decor:
                dire("  ATTENTION — DÉCOR ÉCARTÉ de moi-même (option --tout-garder pour tout garder) :")
                for nom, nobj, ntri, raison in ecartes_decor:
                    dire("      collection %s (%d objet(s), %s triangles) : %s" % (nom, nobj, nombre(ntri), raison))
                import numpy as np
                scene["objets"] = [o for o, k in zip(scene["objets"], garde) if k]
                scene["triangles"] = sum(scene["maillages"][o["maillage"]]["triangles"] for o in scene["objets"])
                employes = {o["maillage"] for o in scene["objets"]}
                scene["triangles_distincts"] = sum(scene["maillages"][i]["triangles"] for i in employes)
                bb = np.array([o["boite"] for o in scene["objets"]])
                scene["boite"] = [bb[:, 0, :].min(axis=0).tolist(), bb[:, 1, :].max(axis=0).tolist()]
                par_col = {}
                for o in scene["objets"]:
                    c_ = par_col.setdefault(o["collections"][0] if o["collections"] else "(racine de la scène)",
                                            {"objets": 0, "triangles": 0})
                    c_["objets"] += 1
                    c_["triangles"] += scene["maillages"][o["maillage"]]["triangles"]
                scene["par_collection"] = par_col
                with open(os.path.join(travail, "scene.json"), "w", encoding="utf-8", newline="\n") as f:
                    json.dump(scene, f, ensure_ascii=False)
                tri = scene["triangles"]
                dire("  reste : %d objet(s), %s triangles posés" % (len(scene["objets"]), nombre(tri)))
        if tri > plafond:
            par_col = sorted(scene["par_collection"].items(), key=lambda kv: -kv[1]["triangles"])
            tableau = "\n".join("      %-40s %10s triangles, %6d objet(s)%s" % (
                n, nombre(d["triangles"]), d["objets"], "  [décor]" if est_decor(n) else "") for n, d in par_col[:25])
            raise Arret(5, "trop de triangles : %s posés pour un plafond de %s, soit %s de trop%s.\n"
                           "    Par collection :\n%s\n    Écartez des collections (--exclure-collections A,B) ou "
                           "relevez --plafond." % (
                               nombre(tri), nombre(plafond), nombre(tri - plafond),
                               "" if not ecartes_decor else " même sans le décor (%s)" % ", ".join(x[0] for x in ecartes_decor),
                               tableau))
        e = scene["ecartes"]
        if e["caches_au_rendu"] or e["invisibles_camera"]:
            dire("  écartés : %d objet(s) masqué(s) au rendu, %d invisible(s) pour la caméra%s" % (
                len(e["caches_au_rendu"]), len(e["invisibles_camera"]),
                " (ex. %s)" % ", ".join((e["caches_au_rendu"] + e["invisibles_camera"])[:3])))
        if e["erreurs"]:
            dire("  ATTENTION — %d objet(s) illisible(s), ABSENTS du PDF : %s" % (len(e["erreurs"]), "; ".join(e["erreurs"][:5])))

        # ---------------------------------------------------------------- 3. ce qu'on demande à Node
        cadre = (762.0, 405.0)             # le cadre 3D de la page de l'ERP, en points
        ecriture = {
            "mode": mode, "scene_json": os.path.join(travail, "scene.json"),
            "scene_bin": os.path.join(travail, "scene.bin"), "sortie": sortie, "sortie_u3d": a.u3d and os.path.abspath(a.u3d),
            "rapport_json": os.path.join(travail, "rapport_ecriture.json"),
            "titre": titre, "lignes": lignes, "unite_nom": unite_nom, "metres_par_unite": metres,
            "message_repli_1": REPLI_1, "message_repli_2": REPLI_2,
        }
        attendu = {"mode": mode, "unite_nom": unite_nom, "interdits": list(a.interdit),
                   "textes": [titre if len(titre) < 80 else titre[:60]]}
        # propriétés du document : la version de fabrication les écrit ; l'ERP n'en écrit aucune
        if a.simple:
            attendu["compresse"] = False       # l'écrivain de l'ERP écrit sans compression (profil 0x04)
            attendu["proprietes"] = {}
            if a.auteur or a.sujet:
                dire("  note : --auteur et --sujet sont sans effet avec --simple (l'ERP n'écrit aucune "
                     "propriété de document)")
        else:
            proprietes = {"titre": titre,
                          "auteur": AUTEUR_DEFAUT if a.auteur is None else a.auteur,
                          "sujet": (a.mention or "") if a.sujet is None else a.sujet}
            proprietes = {k: v.strip() for k, v in proprietes.items() if v and v.strip()}
            ecriture["proprietes"] = proprietes
            attendu["proprietes"] = proprietes
        if not a.simple:
            etiquettes, fiches = {}, {}
            if a.etiquettes:
                with open(a.etiquettes, encoding="utf-8") as f:
                    j = json.load(f)
                etiquettes = {str(k): str(v) for k, v in (j.get("etiquettes") or {}).items()}
                fiches = j.get("fiches") or {}
            niveaux = choisir_niveaux(scene, a.arbre)
            noeuds, ressources, materiaux = construire_arbre(scene, niveaux, a.nom_prop, etiquettes, fiches,
                                                             not a.sans_fiches)
            groupes = [n for n in noeuds if n["type"] == "groupe"]
            dire("  arbre : %s ; %d groupe(s), %d pièce(s), %d maillage(s) partagé(s), %d matériau(x)" % (
                "collections du .blend" if not niveaux else "propriétés %s (sinon la collection)" % ", ".join(niveaux),
                len(groupes), len(noeuds) - len(groupes), len(ressources), len(materiaux)))
            for m in materiaux:
                dire("      matériau %-48s diffus %s opacité %.2f  [%s]" % (m["nom"][:48], m["diffus"], m["opacite"], m["source"]))
            # vues
            boite = scene["boite"]
            vues = []
            demandes = [lire_vue(v) for v in a.vue] or [("Isométrique", 45.0, 30.0, False), ("Face", 0.0, 0.0, True),
                                                        ("Côté", 90.0, 0.0, True), ("Dessus", 0.0, 90.0, True)]
            points = [q for o in scene["objets"] for q in coins_boite(o["boite"])]
            for nom, az, el, ortho in demandes:
                vues.append(vue_orbite(nom, az, el, boite, cadre, ortho=ortho, points=points))
            if a.cameras:
                for cam in sorted(scene["cameras"], key=lambda c: (not c["active"], cle_naturelle(c["nom"]))):
                    vues.append(vue_camera(cam, boite, cadre))
            if a.vues_par_groupe:
                import numpy as np
                premiers = [n for n in groupes if n["parent"] == ""]
                parent = {n["nom"]: n["parent"] for n in noeuds}

                def racine_de(nom):
                    while parent.get(nom, "") != "":
                        nom = parent[nom]
                    return nom

                boites = {}
                for n in noeuds:
                    if n["type"] != "modele":
                        continue
                    r_ = racine_de(n["nom"])
                    b_ = np.array(scene["objets"][n["objet"]]["boite"])
                    if r_ in boites:
                        boites[r_] = np.array([np.minimum(boites[r_][0], b_[0]), np.maximum(boites[r_][1], b_[1])])
                    else:
                        boites[r_] = b_
                racines_modeles = [n["nom"] for n in noeuds if n["type"] == "modele" and n["parent"] == ""]
                for g in premiers:
                    if g["nom"] not in boites:
                        continue
                    v = vue_orbite("Isoler : %s" % g["cle"], demandes[0][1], demandes[0][2], boites[g["nom"]].tolist(), cadre)
                    v["noeuds"] = [{"nom": h["nom"], "visible": h["nom"] == g["nom"]} for h in premiers]
                    v["noeuds"] += [{"nom": x, "visible": False} for x in racines_modeles]
                    vues.append(v)
            defaut = 0
            if a.vue_defaut.isdigit():
                defaut = max(0, min(len(vues) - 1, int(a.vue_defaut) - 1))
            else:
                noms_v = [v["nom"] for v in vues]
                if a.vue_defaut not in noms_v:
                    raise Arret(2, "--vue-defaut « %s » : vues connues : %s" % (a.vue_defaut, ", ".join(noms_v)))
                defaut = noms_v.index(a.vue_defaut)
            try:
                fond = [float(x) for x in a.fond.split(",")]
                assert len(fond) == 3 and all(0 <= x <= 1 for x in fond)
            except Exception:
                raise Arret(2, "--fond « %s » : attendu trois nombres entre 0 et 1, « r,v,b »" % a.fond)
            dire("  vues : %s ; ouverture sur « %s »" % (", ".join("« %s »" % v["nom"] for v in vues[:8])
                 + (" … (%d en tout)" % len(vues) if len(vues) > 8 else ""), vues[defaut]["nom"]))
            ecriture.update({"noeuds": noeuds, "ressources": ressources, "materiaux": materiaux, "vues": vues,
                             "vue_defaut": defaut, "rendu": a.rendu, "eclairage": a.eclairage, "fond": fond,
                             "normales": not a.sans_normales, "arbre_ouvert": not a.sans_arbre_ouvert,
                             "compression": not a.sans_compression, "cadre": cadre})
            if a.compat:
                compat = {}
                for morceau in a.compat.split(","):
                    k, _, v = morceau.partition("=")
                    k, v = k.strip(), v.strip()
                    if k not in ("compresse", "priorite", "zeroFinal", "chainesDeGroupe", "fiches", "unitesDefinies",
                                 "attributsNuancage"):
                        raise Arret(2, "--compat : réglage inconnu « %s »" % k)
                    compat[k] = int(v) if k == "attributsNuancage" else v not in ("0", "non", "false", "faux", "")
                ecriture["compat"] = compat
                dire("  réglages de compatibilité : %s" % compat)
            # le U3D de la version de fabrication est COMPRESSÉ par défaut (comme tous les fichiers U3D courants)
            attendu["compresse"] = bool(ecriture.get("compat", {}).get("compresse", True))
            attendu["noeuds"] = {n["nom"]: {"parent": n["parent"], "type": n["type"], "ressource": n.get("ressource"),
                                            "nuanceurs": n.get("nuanceurs")} for n in noeuds}
            attendu["materiaux"] = {m["nom"]: {"diffus": m["diffus"], "opacite": m["opacite"]} for m in materiaux}
        f_ecr = os.path.join(travail, "ecriture.json")
        with open(f_ecr, "w", encoding="utf-8", newline="\n") as f:
            json.dump(ecriture, f, ensure_ascii=False)

        # ---------------------------------------------------------------- 4. écriture par Node
        env_node = dict(os.environ)
        for k in ("NODE_OPTIONS", "NODE_PATH"):
            env_node.pop(k, None)
        cmd = [node, "--max-old-space-size=4096", "--import", "./noeud/crochet_ts.mjs", "./noeud/ecrire_pdf3d.mjs", f_ecr]
        t0 = time.time()
        p = subprocess.run(cmd, env=env_node, cwd=ICI, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=a.delai)
        sortie_n = p.stdout.decode("utf-8", errors="replace")
        with open(os.path.join(travail, "journal_node.txt"), "w", encoding="utf-8", newline="\n") as f:
            f.write(sortie_n)
        if p.returncode != 0 or "ECRITURE_OK" not in sortie_n:
            raise Arret(6, "l'écriture par Node a échoué (code %d) :\n%s" % (p.returncode, "\n".join(sortie_n.strip().splitlines()[-15:])))
        with open(ecriture["rapport_json"], encoding="utf-8") as f:
            rapport = json.load(f)
        dire("  écriture : %.1f s ; %s faces, %s sommets ; U3D %s octets ; PDF %s octets (%.2f Mo)" % (
            time.time() - t0, nombre(rapport["faces"]), nombre(rapport["sommets"]), nombre(rapport["octets_u3d"]),
            nombre(rapport["octets_pdf"]), rapport["octets_pdf"] / 1e6))

        # ---------------------------------------------------------------- 5. contrôle
        import controle_pdf3d
        attendu["textes"] += [l_ for l_ in rapport.get("lignes", []) if len(l_) < 140][:LIGNES_MAX]
        L, KO, M = controle_pdf3d.controler(sortie, scene, attendu)
        entete = [
            "CONTRÔLE DU PDF 3D — %s" % time.strftime("%Y-%m-%d %H:%M:%S"),
            "source : %s" % os.path.basename(blend),
            "mode : %s" % ("simple, tel que l'ERP le fait (erp\\atelier\\exportPdf3d.ts et u3dWriter.ts, inchangés)"
                           if a.simple else "de fabrication (u3dWriterMulti.ts, exportPdf3dMulti.ts)"),
            "retenu : %d objet(s), %d maillage(s) distinct(s), %s triangles posés ; unité : %s" % (
                len(scene["objets"]), len({o["maillage"] for o in scene["objets"]}), nombre(scene["triangles"]), unite_nom),
        ]
        if scene["collections_non_gardees"]:
            entete.append("collections écartées sur demande : %s" % ", ".join(scene["collections_non_gardees"]))
        for nom, nobj, ntri, raison in ecartes_decor:
            entete.append("décor écarté de soi-même : collection %s, %d objet(s), %s triangles — %s" % (nom, nobj, nombre(ntri), raison))
        if e["particules"]:
            entete.append("instances de particules écartées : %s" % nombre(e["particules"]))
        entete.append("écrit : %s faces, %s sommets, U3D de %s octets" % (nombre(rapport["faces"]), nombre(rapport["sommets"]),
                                                                           nombre(rapport["octets_u3d"])))
        entete.append("")
        pied = ["", "RÉSULTAT : %d contrôle(s) en échec sur %d" % (len(KO), sum(1 for x in L if x.startswith("  OK") or x.startswith("  ÉCHEC"))),
                "NON PROUVÉ ICI : qu'un lecteur affiche le modèle (voir_dans_lecteur.ps1, puis un œil humain)."]
        f_ctl = os.path.abspath(a.controle) if a.controle else os.path.splitext(sortie)[0] + ".controle.txt"
        with open(f_ctl, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(entete + L + pied) + "\n")
        for x in L:
            if x.startswith("  ÉCHEC"):
                dire(x)
        dire("  contrôle : %d vérification(s), %d échec(s) ; rapport : %s" % (
            sum(1 for x in L if x.startswith("  OK") or x.startswith("  ÉCHEC")), len(KO), f_ctl))
        if KO:
            raise Arret(7, "le PDF est écrit mais %d contrôle(s) échouent (voir %s)" % (len(KO), f_ctl))
        dire("  durée totale : %.1f s" % (time.time() - t_debut))
        dire("PDF_3D_OK %s" % sortie)
        return 0
    finally:
        if not garder:
            shutil.rmtree(travail, ignore_errors=True)


if __name__ == "__main__":
    try:
        sys.exit(principal(sys.argv[1:]))
    except Arret as arret:
        if arret.code:
            print("PDF_3D_ERREUR (code %d) : %s" % (arret.code, arret), flush=True)
        sys.exit(arret.code)
    except subprocess.TimeoutExpired as ex:
        print("PDF_3D_ERREUR (code 4) : délai dépassé (%s)" % ex, flush=True)
        sys.exit(4)
