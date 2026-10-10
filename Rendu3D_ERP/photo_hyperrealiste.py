#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Photo hyperrealiste a partir d'un rendu Blender : le MEME appel que le module Rendu 3D de l'ERP.

Chaine reproduite (Constructo AI) :

  1. Navigateur   Rendu3DDropzone.tsx:77-94 (rasterToDataUrl) : image ramenee a 2048 px de
                  cote au plus, re-encodee en JPEG qualite 0,92, envoyee en data URL.
  2. Point d'acces POST /api/erp/v1/cao/render, cao.py:1461-1541 :
                  palier -> modele, resolution, type de rendu, bornes de taille, invite.
  3. Service      gemini_image.call_gemini_image : POST generateContent de Google Gemini.

CE SCRIPT N'A PAS SA PROPRE COPIE DE L'INVITE NI DU CORPS DE LA REQUETE. Il charge les
constantes et les fonctions du fichier copie ERP_REACT/backend/routers/gemini_image.py
(build_render_prompt, split_data_url, image_output_tokens, call_gemini_image) et n'en
remplace que le transport : httpx -> urllib (bibliotheque standard). Recopier gemini_image.py
depuis le depot suffit donc a suivre une evolution de l'ERP.

Emploi :
  python photo_hyperrealiste.py rendu.png --sortie photo.png
         [--type exterior|interior|object|mechanical] [--qualite pro|standard|fast]
         [--resolution 1K|2K|4K] [--consigne "texte libre"] [--essai-a-blanc]

Cle : variable GOOGLE_GEMINI_API_KEY, lue dans l'environnement du processus puis, a defaut,
dans HKCU\\Environment (une session ouverte avant l'ajout de la variable ne la voit pas).
Dependance : Pillow (redimensionnement identique au navigateur). Aucune autre.
"""
from __future__ import annotations

import argparse
import ast
import base64
import builtins
import copy
import hashlib
import http.client
import io
import json
import logging
import math
import operator
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ICI = Path(__file__).resolve().parent
MODULE_ERP = ICI / "ERP_REACT" / "backend" / "routers" / "gemini_image.py"

# Nom EXACT de la variable lue par le backend (gemini_image.py, GEMINI_API_KEY).
NOM_VARIABLE_CLE = "GOOGLE_GEMINI_API_KEY"

# --- Ce qui ne vit PAS dans gemini_image.py : recopie du navigateur et du point d'acces ---
COTE_MAX_NAVIGATEUR = 2048                         # Rendu3DDropzone.tsx:65 MAX_IMAGE_SIDE
QUALITE_JPEG_NAVIGATEUR = 0.92                     # Rendu3DDropzone.tsx:90 toDataURL('image/jpeg', 0.92)
FORMATS_IMAGE = ("png", "jpg", "jpeg", "webp")     # Rendu3DDropzone.tsx:58 FORMATS_IMG
LONGUEUR_IMAGE_MIN, LONGUEUR_IMAGE_MAX = 32, 22_000_000   # cao.py:1466 Field(min_length, max_length)
LONGUEUR_DETAILS_MAX = 2000                        # cao.py:1468 Field(max_length=2000)
TYPES_ACCEPTES = ("exterior", "interior", "object", "mechanical")   # cao.py:1522
SOURCE = "render3d"                                # api/rendu3d.ts:64 source: 'render3d'
# Defauts de la page Rendu 3D : Rendu3DControls.tsx:78 (pro) et :81 (4K) ; type « exterieur »
# pour une image deja faite (Rendu3DPage.tsx:116).
DEFAUT_QUALITE, DEFAUT_RESOLUTION, DEFAUT_TYPE = "pro", "4K", "exterior"

CONSTANTES_ERP = ("GEMINI_BASE_URL", "GEMINI_IMAGE_MODELS", "GEMINI_OUTPUT_USD_PER_TOKEN",
                  "GEMINI_IMAGE_RAW_USD", "GEMINI_RESOLUTIONS",
                  "GEMINI_TOKENS_NOMINAL_PAR_RESOLUTION", "MAX_RENDER_IMAGE_BYTES")
FONCTIONS_ERP = ("build_render_prompt", "split_data_url", "image_output_tokens",
                 "call_gemini_image")

ALIAS_TYPE = {"exterieur": "exterior", "extérieur": "exterior", "interieur": "interior",
              "intérieur": "interior", "objet": "object", "mecanique": "mechanical",
              "mécanique": "mechanical"}
ALIAS_QUALITE = {"rapide": "fast"}
EXTENSION_PAR_MIME = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}

_DUMPS = json.dumps
journal = logging.getLogger("photo_hyperrealiste")


class ErreurERP(Exception):
    """Equivalent de fastapi.HTTPException : meme code, meme message que le backend."""

    def __init__(self, status_code: int, detail: str = "") -> None:
        super().__init__(f"{status_code} {detail}")
        self.status_code = status_code
        self.detail = detail


class ErreurUtilisation(Exception):
    """Entree refusee avant tout appel (fichier, format, option)."""


class EssaiABlanc(Exception):
    """Levee par le transport en essai a blanc : la requete est construite, pas envoyee."""


# =============================================================================================
# 1. Chargement des pieces du backend (sans importer httpx ni fastapi)
# =============================================================================================

_OPERATIONS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
               ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv}


def _valeur_constante(noeud: ast.AST):
    """Evalue une expression CONSTANTE (litteraux, tuples, dicts, + - * /) et rien d'autre."""
    if isinstance(noeud, ast.Constant):
        return noeud.value
    if isinstance(noeud, (ast.Tuple, ast.List)):
        valeurs = [_valeur_constante(e) for e in noeud.elts]
        return tuple(valeurs) if isinstance(noeud, ast.Tuple) else valeurs
    if isinstance(noeud, ast.Dict) and None not in noeud.keys:
        return {_valeur_constante(k): _valeur_constante(v) for k, v in zip(noeud.keys, noeud.values)}
    if isinstance(noeud, ast.UnaryOp) and isinstance(noeud.op, (ast.USub, ast.UAdd)):
        valeur = _valeur_constante(noeud.operand)
        return -valeur if isinstance(noeud.op, ast.USub) else valeur
    if isinstance(noeud, ast.BinOp) and type(noeud.op) in _OPERATIONS:
        return _OPERATIONS[type(noeud.op)](_valeur_constante(noeud.left),
                                           _valeur_constante(noeud.right))
    raise ValueError(f"expression non constante (ligne {getattr(noeud, 'lineno', '?')})")


def charger_module_erp(chemin: Path = MODULE_ERP) -> dict:
    """Espace de noms contenant les constantes et les fonctions du gemini_image.py copie.

    Seuls les noms listes dans CONSTANTES_ERP et FONCTIONS_ERP sont pris ; le reste du fichier
    (imports httpx/fastapi, lecture de la cle au chargement) n'est PAS execute. `httpx`,
    `HTTPException`, `logger` et `GEMINI_API_KEY` sont fournis par ce script.
    """
    if not chemin.is_file():
        raise ErreurUtilisation(f"module du backend introuvable : {chemin}")
    arbre = ast.parse(chemin.read_text(encoding="utf-8"), filename=str(chemin))
    espace: dict = {"__builtins__": builtins, "__name__": "gemini_image_erp",
                    "HTTPException": ErreurERP, "logger": logging.getLogger("gemini_image"),
                    "httpx": None, "GEMINI_API_KEY": ""}
    fonctions = []
    for noeud in arbre.body:
        if (isinstance(noeud, ast.Assign) and len(noeud.targets) == 1
                and isinstance(noeud.targets[0], ast.Name)
                and noeud.targets[0].id in CONSTANTES_ERP):
            espace[noeud.targets[0].id] = _valeur_constante(noeud.value)
        elif isinstance(noeud, ast.FunctionDef) and noeud.name in FONCTIONS_ERP:
            fonctions.append(noeud)
    exec(compile(ast.Module(body=fonctions, type_ignores=[]), str(chemin), "exec"), espace)
    manquants = [nom for nom in CONSTANTES_ERP + FONCTIONS_ERP if nom not in espace]
    if manquants:
        raise ErreurUtilisation(f"{chemin.name} ne contient plus : {', '.join(manquants)}")
    return espace


# =============================================================================================
# 2. Transport : remplace le module httpx dans call_gemini_image
# =============================================================================================

class _ReponseHttp:
    """Ce dont call_gemini_image se sert dans une reponse httpx : status_code, text, json()."""

    def __init__(self, status_code: int, contenu: bytes) -> None:
        self.status_code = status_code
        self.contenu = contenu

    @property
    def text(self) -> str:
        return self.contenu.decode("utf-8", errors="replace")

    def json(self):
        return json.loads(self.contenu)  # JSONDecodeError est un ValueError, comme chez httpx


class TransportUrllib:
    """Meme signature que httpx.post(url, json=, headers=, timeout=), en bibliotheque standard.

    Le corps est serialise comme httpx 0.28 (UTF-8, separateurs compacts). Comme httpx, une
    reponse 4xx/5xx est RENDUE (pas levee) : c'est call_gemini_image qui la traite.
    """

    class HTTPError(Exception):
        """Equivalent de httpx.HTTPError : echec de transport (DNS, TLS, delai depasse)."""

    def __init__(self, essai_a_blanc: bool = False, ouvrir=None) -> None:
        self.essai_a_blanc = essai_a_blanc
        self._ouvrir = ouvrir or urllib.request.urlopen
        self.derniere_requete: dict | None = None
        self.derniere_reponse: _ReponseHttp | None = None

    def post(self, url, json=None, headers=None, timeout=None):  # noqa: A002 (nom impose par httpx)
        corps = _DUMPS(json, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
        entetes = dict(headers or {})
        self.derniere_requete = {"method": "POST", "url": url, "headers": entetes,
                                 "json": json, "timeout": timeout, "corps": corps}
        if self.essai_a_blanc:
            raise EssaiABlanc()
        requete = urllib.request.Request(url, data=corps, headers=entetes, method="POST")
        try:
            with self._ouvrir(requete, timeout=timeout) as reponse:
                resultat = _ReponseHttp(reponse.status, reponse.read())
        except urllib.error.HTTPError as exc:
            try:
                contenu = exc.read() or b""
            except Exception:  # noqa: BLE001
                contenu = b""
            resultat = _ReponseHttp(exc.code, contenu)
        except (urllib.error.URLError, http.client.HTTPException, OSError) as exc:
            raise self.HTTPError(str(exc)) from exc
        self.derniere_reponse = resultat
        return resultat


# =============================================================================================
# 3. Navigateur : Rendu3DDropzone.rasterToDataUrl
# =============================================================================================

@dataclass
class ImagePreparee:
    data_url: str
    format_source: str
    taille_source: tuple
    taille: tuple
    octets_source: int
    octets_jpeg: int
    transparence_aplatie: bool


def _arrondi_js(valeur: float) -> int:
    """Math.round de JavaScript (demi vers +infini), pas l'arrondi bancaire de Python."""
    return math.floor(valeur + 0.5)


def preparer_image_comme_le_navigateur(chemin: Path) -> ImagePreparee:
    """Rendu3DDropzone.tsx:77-94 : cote max 2048 px, JPEG 0,92, data URL.

    Le canevas du navigateur compose les pixels transparents sur du NOIR avant l'encodage JPEG
    (norme HTML de toDataURL) : on fait de meme. L'orientation EXIF est appliquee, comme a
    l'affichage. Le lissage du redimensionnement est celui de Pillow (LANCZOS), pas celui du
    navigateur : seul ce detail de pixels peut differer.
    """
    if not chemin.is_file():
        raise ErreurUtilisation(f"fichier introuvable : {chemin}")
    extension = chemin.suffix.lower().lstrip(".")
    if extension not in FORMATS_IMAGE:
        raise ErreurUtilisation("Format de fichier non pris en charge. "
                                f"(accepte : {', '.join(FORMATS_IMAGE)})")
    try:
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise ErreurUtilisation("Pillow manque (python -m pip install pillow) : ce script ne "
                                "l'installe pas lui-meme.") from exc
    try:
        with Image.open(chemin) as ouverte:
            ouverte.load()
            format_source = ouverte.format or extension.upper()
            image = ImageOps.exif_transpose(ouverte)
    except Exception as exc:  # noqa: BLE001
        raise ErreurUtilisation("Format de fichier non pris en charge. (image illisible : "
                                f"{exc})") from exc
    largeur0, hauteur0 = image.size
    cote = max(largeur0, hauteur0)
    echelle = COTE_MAX_NAVIGATEUR / cote if cote > COTE_MAX_NAVIGATEUR else 1
    largeur = max(1, _arrondi_js(largeur0 * echelle))
    hauteur = max(1, _arrondi_js(hauteur0 * echelle))
    rgba = image.convert("RGBA")
    transparence = rgba.getextrema()[3][0] < 255
    rgb = Image.alpha_composite(Image.new("RGBA", rgba.size, (0, 0, 0, 255)), rgba).convert("RGB")
    if (largeur, hauteur) != (largeur0, hauteur0):
        rgb = rgb.resize((largeur, hauteur), Image.Resampling.LANCZOS)
    tampon = io.BytesIO()
    rgb.save(tampon, format="JPEG", quality=round(QUALITE_JPEG_NAVIGATEUR * 100))
    jpeg = tampon.getvalue()
    return ImagePreparee(
        data_url="data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii"),
        format_source=format_source, taille_source=(largeur0, hauteur0),
        taille=(largeur, hauteur), octets_source=chemin.stat().st_size,
        octets_jpeg=len(jpeg), transparence_aplatie=transparence)


# =============================================================================================
# 4. Point d'acces : cao.py render_realistic, jusqu'a l'appel Gemini
# =============================================================================================

@dataclass
class AppelGemini:
    tier: str
    model: str
    resolution: str
    render_kind: str
    feature: str
    in_mime: str
    in_b64: str
    prompt: str


def corps_requete_erp(data_url: str, consigne: str, qualite: str, resolution: str,
                      type_rendu: str) -> dict:
    """Le JSON que la page Rendu 3D poste a /cao/render (api/rendu3d.ts:62-66 ; l'intercepteur
    axios change renderKind en render_kind)."""
    return {"image": data_url, "details": consigne, "quality": qualite,
            "resolution": resolution, "render_kind": type_rendu, "source": SOURCE}


def point_d_acces_cao_render(erp: dict, corps: dict) -> AppelGemini:
    """Recopie de cao.py:1461-1541 (CaoRenderRequest + render_realistic avant l'appel Gemini).
    Les gardes d'argent (credits, reservation) n'ont pas d'objet ici : la cle est la votre."""
    image, details = corps["image"], corps["details"]
    if not LONGUEUR_IMAGE_MIN <= len(image) <= LONGUEUR_IMAGE_MAX:           # cao.py:1466
        raise ErreurERP(422, f"image : {len(image)} caracteres (bornes {LONGUEUR_IMAGE_MIN}"
                             f"-{LONGUEUR_IMAGE_MAX})")
    if len(details) > LONGUEUR_DETAILS_MAX:                                   # cao.py:1468
        raise ErreurERP(422, f"details : {len(details)} caracteres (max {LONGUEUR_DETAILS_MAX})")
    modeles = erp["GEMINI_IMAGE_MODELS"]
    tier = corps["quality"] if corps["quality"] in modeles else "pro"         # cao.py:1517
    model = modeles[tier]                                                     # cao.py:1518
    resolution = (corps["resolution"] if corps["resolution"] in erp["GEMINI_RESOLUTIONS"]
                  else "2K")                                                  # cao.py:1519
    render_kind = (corps["render_kind"] if corps["render_kind"] in TYPES_ACCEPTES
                   else "exterior")                                           # cao.py:1521-1523
    feature = "render3d" if corps.get("source") == "render3d" else "cao_render"   # cao.py:1525
    in_mime, in_b64 = erp["split_data_url"](image)                           # cao.py:1527
    maximum = erp["MAX_RENDER_IMAGE_BYTES"]
    if len(in_b64) > int(maximum * 1.4):                                      # cao.py:1532-1533
        raise ErreurERP(413, "Image trop volumineuse")
    try:
        brut = base64.b64decode(in_b64, validate=True)                        # cao.py:1534-1537
    except Exception:  # noqa: BLE001
        raise ErreurERP(400, "Image invalide (base64)")
    if len(brut) > maximum:                                                   # cao.py:1538-1539
        raise ErreurERP(413, "Image trop volumineuse")
    prompt = erp["build_render_prompt"](details, render_kind)                 # cao.py:1541
    return AppelGemini(tier, model, resolution, render_kind, feature, in_mime, in_b64, prompt)


def cout_usd(erp: dict, tier: str, jetons: int) -> tuple:
    """(cout brut, meme cout arrondi comme au point d'acces) en USD : cao.py:1580-1584."""
    if jetons > 0:
        brut = jetons * erp["GEMINI_OUTPUT_USD_PER_TOKEN"].get(tier, 1.2e-4)
    else:
        brut = erp["GEMINI_IMAGE_RAW_USD"].get(tier, 0.14)
    return brut, round(brut, 6)


# =============================================================================================
# 5. Cle, sortie, affichage
# =============================================================================================

def lire_cle() -> tuple:
    """(cle, provenance). Environnement du processus d'abord, puis HKCU\\Environment."""
    cle = (os.environ.get(NOM_VARIABLE_CLE) or "").strip()
    if cle:
        return cle, "environnement du processus"
    try:
        import winreg
    except ImportError:
        return "", ""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as registre:
            valeur, genre = winreg.QueryValueEx(registre, NOM_VARIABLE_CLE)
    except OSError:
        return "", ""
    if genre == winreg.REG_EXPAND_SZ:
        valeur = winreg.ExpandEnvironmentStrings(valeur)
    valeur = str(valeur or "").strip()
    return (valeur, "registre HKCU\\Environment") if valeur else ("", "")


def chemin_de_sortie(demande: Path | None, source: Path, mime: str) -> tuple:
    """(chemin, remarques). Extension conforme au type rendu ; JAMAIS d'ecrasement (_v2, _v3...)."""
    remarques = []
    extension = EXTENSION_PAR_MIME.get(mime, ".png")
    if demande is None:
        cible = source.with_name(f"{source.stem}_photo_hyperrealiste{extension}")
    else:
        cible = demande
        permises = {extension, ".jpeg"} if extension == ".jpg" else {extension}
        if cible.suffix.lower() not in permises:
            remarques.append(f"le service a rendu {mime} : extension {cible.suffix or '(aucune)'} "
                             f"remplacee par {extension}")
            cible = cible.with_suffix(extension)
    if cible.exists():
        rang = 2
        while (autre := cible.with_name(f"{cible.stem}_v{rang}{cible.suffix}")).exists():
            rang += 1
        remarques.append(f"{cible.name} existe deja : rien n'est ecrase, ecriture sous {autre.name}")
        cible = autre
    return cible, remarques


def _corps_sans_base64(corps: dict, description: str) -> dict:
    copie = copy.deepcopy(corps)
    for contenu in copie.get("contents") or []:
        for partie in contenu.get("parts") or []:
            donnees = partie.get("inline_data") or partie.get("inlineData")
            if isinstance(donnees, dict) and "data" in donnees:
                donnees["data"] = description
    return copie


def _milliers(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def afficher_essai_a_blanc(source: Path, image: ImagePreparee, corps_erp: dict,
                           appel: AppelGemini, requete: dict, erp: dict,
                           remarques: list) -> None:
    b64 = appel.in_b64
    octets = base64.b64decode(b64)
    empreinte = hashlib.sha256(octets).hexdigest()[:16]
    print("=== ESSAI A BLANC : rien n'est envoye, la cle n'est pas lue ===")
    print(f"Source         : {source} ({image.format_source} {image.taille_source[0]}x"
          f"{image.taille_source[1]}, {_milliers(image.octets_source)} o)")
    print(f"Navigateur     : cote max {COTE_MAX_NAVIGATEUR} px + JPEG {QUALITE_JPEG_NAVIGATEUR} -> "
          f"{image.taille[0]}x{image.taille[1]}, {_milliers(image.octets_jpeg)} o"
          + ("  (transparence aplatie sur noir)" if image.transparence_aplatie else ""))
    for remarque in remarques:
        print(f"Remarque       : {remarque}")
    print()
    print("--- Requete ERP equivalente : POST /api/erp/v1/cao/render")
    affiche = dict(corps_erp, image=f"<data URL {appel.in_mime} : {_milliers(len(corps_erp['image']))} caracteres>")
    print(json.dumps(affiche, indent=2, ensure_ascii=False))
    print()
    print("--- Requete Google (construite par call_gemini_image du backend, transport urllib)")
    print(f"{requete['method']} {requete['url']}")
    for nom, valeur in requete["headers"].items():
        print(f"  {nom}: {'<cle non lue : essai a blanc>' if nom.lower() == 'x-goog-api-key' else valeur}")
    print(f"  delai : {requete['timeout']} s ; corps : {_milliers(len(requete['corps']))} octets")
    description = (f"<base64 retire : {_milliers(len(b64))} caracteres = "
                   f"{_milliers(len(octets))} octets {appel.in_mime}, sha256 {empreinte}...>")
    print(json.dumps(_corps_sans_base64(requete["json"], description), indent=2, ensure_ascii=False))
    print()
    print("--- Invite envoyee (texte exact)")
    print(appel.prompt)
    print("---")
    nominal = erp["GEMINI_TOKENS_NOMINAL_PAR_RESOLUTION"].get(appel.resolution, 0)
    brut, _ = cout_usd(erp, appel.tier, nominal)
    print(f"Modele {appel.model} (palier {appel.tier}), resolution {appel.resolution}, "
          f"type {appel.render_kind}.")
    print(f"Cout nominal (bareme, ~{nominal} jetons) : {brut:.3f} $ US, facture par Google au compte "
          f"de la cle.")


# =============================================================================================
# 6. Ligne de commande
# =============================================================================================

def _type(valeur: str) -> str:
    v = ALIAS_TYPE.get(valeur.strip().lower(), valeur.strip().lower())
    if v not in TYPES_ACCEPTES:
        raise argparse.ArgumentTypeError(f"type inconnu : {valeur} (choix : {', '.join(TYPES_ACCEPTES)})")
    return v


def _qualite(valeur: str) -> str:
    v = ALIAS_QUALITE.get(valeur.strip().lower(), valeur.strip().lower())
    if v not in ("pro", "standard", "fast"):
        raise argparse.ArgumentTypeError(f"qualite inconnue : {valeur} (choix : pro, standard, fast)")
    return v


def _resolution(valeur: str) -> str:
    v = valeur.strip().upper()
    if v not in ("1K", "2K", "4K"):
        raise argparse.ArgumentTypeError(f"resolution inconnue : {valeur} (choix : 1K, 2K, 4K)")
    return v


def construire_analyseur() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="photo_hyperrealiste.py",
        description="Photo hyperrealiste d'un rendu Blender, par le meme appel Google Gemini que "
                    "le module Rendu 3D de l'ERP (voir LISEZMOI.md).")
    p.add_argument("image", type=Path, help="rendu Blender (PNG, JPG, JPEG ou WEBP)")
    p.add_argument("--sortie", type=Path, default=None,
                   help="fichier produit (defaut : <image>_photo_hyperrealiste.png a cote de la source ; "
                        "jamais d'ecrasement)")
    p.add_argument("--type", "--style", dest="type_rendu", type=_type, default=DEFAUT_TYPE,
                   help="exterior (defaut) | interior | object | mechanical -- seul « style » du backend "
                        "(accepte aussi exterieur, interieur, objet, mecanique)")
    p.add_argument("--qualite", type=_qualite, default=DEFAUT_QUALITE,
                   help="pro (defaut, gemini-3-pro-image) | standard | fast (alias : rapide)")
    p.add_argument("--resolution", type=_resolution, default=None,
                   help="1K | 2K | 4K (defaut 4K comme la page ; 2K si --qualite fast)")
    p.add_argument("--consigne", "--details", dest="consigne", default="",
                   help="details libres ajoutes a l'invite (materiaux, eclairage, saison...), "
                        f"{LONGUEUR_DETAILS_MAX} caracteres au plus")
    p.add_argument("--reference", type=Path, default=None,
                   help="NON DISPONIBLE : le backend n'accepte qu'UNE image (voir LISEZMOI.md)")
    p.add_argument("--essai-a-blanc", action="store_true",
                   help="affiche la requete (sans le base64) et sort, sans lire la cle ni rien envoyer")
    return p


def main(argv=None) -> int:
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(errors="replace")
        except Exception:  # noqa: BLE001
            pass
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    args = construire_analyseur().parse_args(argv)

    if args.reference is not None:
        print("Erreur : --reference n'est pas disponible. Le point d'acces de l'ERP (/cao/render) "
              "n'accepte qu'UNE image (champ `image`, cao.py:1466) et call_gemini_image n'envoie "
              "qu'une partie inline_data (voir gemini_image.py). Ajouter une photo de reference "
              "serait une EXTENSION du backend, pas une reproduction : voir LISEZMOI.md.",
              file=sys.stderr)
        return 2

    remarques = []
    resolution = args.resolution or DEFAUT_RESOLUTION
    if args.qualite == "fast" and resolution == "4K":
        # Rendu3DControls.tsx:192 et :216 : le palier Rapide plafonne ~1K, l'interface bascule en 2K.
        resolution = "2K"
        remarques.append("qualite fast : resolution ramenee a 2K, comme l'interface "
                         "(Rendu3DControls.tsx:192)")

    transport = None
    try:
        erp = charger_module_erp()
        image = preparer_image_comme_le_navigateur(args.image)
        corps_erp = corps_requete_erp(image.data_url, args.consigne, args.qualite, resolution,
                                      args.type_rendu)
        appel = point_d_acces_cao_render(erp, corps_erp)
        transport = TransportUrllib(essai_a_blanc=args.essai_a_blanc)
        erp["httpx"] = transport
        if args.essai_a_blanc:
            erp["GEMINI_API_KEY"] = "<cle non lue : essai a blanc>"
        else:
            cle, provenance = lire_cle()
            if not cle:
                print("Erreur 503 : Rendu IA non configure (cle manquante).", file=sys.stderr)
                print(f"Poser la variable {NOM_VARIABLE_CLE} une fois, dans PowerShell :\n"
                      f"  [Environment]::SetEnvironmentVariable(\"{NOM_VARIABLE_CLE}\", \"<cle>\", \"User\")",
                      file=sys.stderr)
                return 1
            erp["GEMINI_API_KEY"] = cle
            for remarque in remarques:
                print(f"Remarque : {remarque}")
            print(f"Cle lue ({provenance}). Appel PAYANT, facture au compte Google de la cle.")
            print(f"Envoi : {appel.model}, {appel.resolution}, type {appel.render_kind}, image "
                  f"{image.taille[0]}x{image.taille[1]} JPEG ({_milliers(image.octets_jpeg)} o)...")
        debut = time.time()
        out_b64, out_mime, jetons = erp["call_gemini_image"](
            appel.model, appel.prompt, appel.in_b64, appel.in_mime, appel.resolution)
    except EssaiABlanc:
        afficher_essai_a_blanc(args.image, image, corps_erp, appel, transport.derniere_requete,
                               erp, remarques)
        if args.sortie:
            print(f"Sortie prevue : {args.sortie} (extension ajustee au type rendu par le service)")
        return 0
    except ErreurUtilisation as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 2
    except ErreurERP as exc:
        print(f"Erreur {exc.status_code} : {exc.detail}", file=sys.stderr)
        derniere = transport.derniere_reponse if transport is not None else None
        if derniere is not None and exc.status_code == 502 and derniere.status_code == 200:
            try:
                donnees = derniere.json()
                motif = (donnees.get("promptFeedback") or {}).get("blockReason")
                fins = [c.get("finishReason") for c in donnees.get("candidates") or []]
                print(f"  blockReason={motif} finishReason={fins}", file=sys.stderr)
            except Exception:  # noqa: BLE001
                pass
        return 1

    duree = time.time() - debut
    contenu = base64.b64decode(out_b64)
    cible, notes = chemin_de_sortie(args.sortie, args.image, out_mime)
    cible.parent.mkdir(parents=True, exist_ok=True)
    cible.write_bytes(contenu)
    brut, _ = cout_usd(erp, appel.tier, jetons)
    for note in notes:
        print(f"Remarque : {note}")
    print(f"Photo ecrite : {cible} ({out_mime}, {_milliers(len(contenu))} o) en {duree:.1f} s")
    print(f"Jetons d'image : {jetons} ; cout (bareme) : {brut:.4f} $ US, facture par Google au compte "
          f"de la cle.")
    try:
        textes = [p.get("text") for c in (transport.derniere_reponse.json().get("candidates") or [])
                  for p in ((c.get("content") or {}).get("parts") or []) if p.get("text")]
        if textes:
            print("Texte joint par le modele : " + " ".join(t.strip() for t in textes))
    except Exception:  # noqa: BLE001
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
