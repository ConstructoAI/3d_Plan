"""
ERP React - Module PUR d'appel a l'image Google Gemini ("Nano Banana")
======================================================================

Helpers SANS dependance DB/auth, PARTAGES par plusieurs appelants.

Ce module est la SOURCE UNIQUE de la cle GOOGLE_GEMINI_API_KEY (lue une seule fois
au chargement) et du contrat d'appel Gemini generateContent. Chaque appelant importe
ces symboles ; ce qu'il fait du cout brut renvoye (suivi, facturation) lui appartient.

Le code provient de cao.py (extraction SANS changement de comportement) : seuls les
noms perdent leur underscore de prefixe (ce sont les symboles publics du module
partage) et le prefixe de log devient [GEMINI] (le module n'est plus propre au DAO).
"""

import os
import logging

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Cle API Google Gemini, lue une fois au chargement (jamais exposee au client).
# A configurer dans l'environnement : GOOGLE_GEMINI_API_KEY.
GEMINI_API_KEY = os.getenv("GOOGLE_GEMINI_API_KEY", "")
# v1beta : surface documentee pour la generation d'image + responseModalities.
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

# Tiers de qualite -> modele Gemini. "pro" = defaut (meilleur rendu).
GEMINI_IMAGE_MODELS = {
    "pro": "gemini-3-pro-image",        # Nano Banana Pro
    "standard": "gemini-3.1-flash-image",  # Nano Banana 2
    "fast": "gemini-2.5-flash-image",   # Nano Banana
}
# Cout BRUT par TOKEN d'image en sortie (USD), par tier — facturation au PLUS JUSTE
# (le nb de tokens varie avec la resolution : ~1120 a 1K, ~2000 a 4K). Calibre sur
# l'observe (Pro : 0.134$/1120 tok a 1K, 0.24$/2000 tok a 4K -> ~1.2e-4 $/tok ;
# Flash 2.5 ~ 30$/Mtok). La facturation appartient a l'appelant.
GEMINI_OUTPUT_USD_PER_TOKEN = {"pro": 1.2e-4, "standard": 6e-5, "fast": 3e-5}
# Repli si usageMetadata absent : prix brut forfaitaire par image (USD), par tier.
GEMINI_IMAGE_RAW_USD = {"pro": 0.14, "standard": 0.06, "fast": 0.04}

# Resolutions de sortie supportees (imageConfig.imageSize). Pro et Standard font le
# 4K reel ; le tier Rapide (gemini-2.5-flash) plafonne ~1K (ignore le 4K) -> on
# facture alors les tokens REELS via usageMetadata (donc pas de surfacturation).
GEMINI_RESOLUTIONS = ("1K", "2K", "4K")

# Plafonds de jetons d'image par resolution : des BORNES, pas des mesures.
GEMINI_TOKENS_MAX_PAR_RESOLUTION = {"1K": 1500, "2K": 2200, "4K": 3000}

# Jetons d'image NOMINAUX -- ce qu'un appel coute D'ORDINAIRE. A ne pas confondre
# avec les plafonds ci-dessus. 1 120 a 1K est une mesure (2026-08-24) ; 2 000 a 4K
# est un observe ; le 2K n'est releve nulle part, on lui donne donc le meme
# nominal que le 1K.
GEMINI_TOKENS_NOMINAL_PAR_RESOLUTION = {"1K": 1120, "2K": 1120, "4K": 2000}

# Garde de taille de l'image d'entree (base64 decode).
MAX_RENDER_IMAGE_BYTES = 12 * 1024 * 1024  # 12 MB


def build_render_prompt(details: str, render_kind: str = "exterior") -> str:
    """Prompt de rendu ultra-photorealiste preservant la GEOMETRIE du modele.

    render_kind pilote le contexte de rendu :
      - exterior (defaut + valeur inconnue) : rendu architectural exterieur ;
      - interior : rendu interieur photorealiste (materiaux + eclairage interieur) ;
      - object   : rendu produit/objet (fond studio ou contextuel) ;
      - mechanical : equipement industriel / mecanique (skid, machine, tuyauterie).

    ⚠️ POURQUOI `mechanical` EXISTE (2026-08-13, demande de Sylvain sur capture). Le DAO
    n'envoyait rien et retombait donc sur `exterior`, dont l'invite demande explicitement « murs
    de brique ou stucco, toiture en bardeaux, ciel degage, entree de garage et amenagement
    paysager ». Applique a un skid de brûleur industriel, ce contexte ne decrit RIEN de ce qui
    est a l'ecran : le modele est pousse a inventer un batiment autour d'une machine. Le champ
    de details portait le meme biais dans son exemple.
    """
    if render_kind == "mechanical":
        base = (
            "Ultra-photorealistic INDUSTRIAL EQUIPMENT rendering of this 3D mechanical "
            "assembly. PRESERVE EXACTLY the geometry, proportions, and the position of every "
            "pipe, valve, flange, fitting, gauge and structural member shown in the image. "
            "Replace the flat CAD shading with realistic industrial materials: painted steel "
            "(machine enamel with subtle orange-peel texture), galvanized and stainless steel "
            "piping with visible weld seams, brass and bronze fittings, cast-iron valve bodies, "
            "black rubber hose, and colour-coded painted pipework. Add realistic detail that "
            "does NOT change geometry: bolted flange hardware, nameplates and tags, conduit "
            "and cable glands, gauge faces. Light it as a plant floor or fabrication shop — "
            "high-bay lighting with soft shadows on a sealed concrete floor. Industrial "
            "equipment catalogue / technical documentation quality, sharp and highly detailed. "
            "Do NOT add, remove or move any component; do NOT add buildings, landscaping, sky "
            "or vegetation; keep the same camera viewpoint."
        )
    elif render_kind == "interior":
        base = (
            "Ultra-photorealistic architectural INTERIOR rendering of this 3D model. "
            "PRESERVE EXACTLY the geometry, proportions, wall layout, and the "
            "placement of every window and door shown in the image. Replace the flat "
            "CAD shading with realistic interior materials (painted drywall, wood or "
            "tile flooring, trim), realistic interior lighting (soft natural light "
            "from the windows + warm artificial fill), and tasteful furniture/decor. "
            "Do NOT add, remove, or move any structural element; keep the same camera "
            "viewpoint."
        )
    elif render_kind == "object":
        base = (
            "Ultra-photorealistic product rendering of this 3D object. PRESERVE "
            "EXACTLY the geometry, proportions and details shown in the image. "
            "Replace the flat CAD shading with realistic materials and finishes, "
            "professional studio lighting with soft shadows and a clean neutral "
            "studio backdrop (or a tasteful contextual setting). Marketing / "
            "product-catalog render quality, sharp and highly detailed. Do NOT add, "
            "remove or move any element; keep the same camera viewpoint."
        )
    else:  # exterior = defaut + valeur inconnue
        base = (
            "Ultra-photorealistic architectural exterior rendering of this 3D building "
            "model. PRESERVE EXACTLY the geometry, proportions, rooflines, and the "
            "placement of every window and door shown in the image. Replace the flat "
            "CAD shading with realistic building materials (siding, brick or stucco "
            "walls; shingled or standing-seam metal roof), natural daylight with soft "
            "realistic shadows, a clear sky, and realistic ground, driveway and "
            "landscaping context. Professional real-estate / marketing render quality, "
            "sharp and highly detailed. Do NOT add, remove, or move any structural "
            "element; keep the same camera viewpoint."
        )
    extra = (details or "").strip()
    if extra:
        base += "\n\nAdditional client details to incorporate: " + extra
    return base


def split_data_url(image: str) -> tuple[str, str]:
    """Retourne (mime, base64) depuis une data URL ou du base64 brut (PNG defaut)."""
    if image.startswith("data:"):
        try:
            header, b64 = image.split(",", 1)
            mime = header[5: header.index(";")] or "image/png"
            return mime, b64
        except Exception:
            raise HTTPException(status_code=400, detail="Image (data URL) invalide")
    return "image/png", image


def image_output_tokens(data: dict) -> int:
    """Nombre de tokens d'IMAGE en sortie (usageMetadata), pour la facturation."""
    um = data.get("usageMetadata") or {}
    for det in um.get("candidatesTokensDetails") or []:
        if det.get("modality") == "IMAGE":
            try:
                return int(det.get("tokenCount") or 0)
            except (TypeError, ValueError):
                return 0
    try:
        return int(um.get("candidatesTokenCount") or 0)
    except (TypeError, ValueError):
        return 0


def call_gemini_image(
    model: str, prompt: str, in_b64: str, in_mime: str, resolution: str
) -> tuple[str, str, int]:
    """Appel SYNCHRONE (a lancer via asyncio.to_thread) a Gemini generateContent.
    Renvoie (base64_image_sortie, mime_sortie, tokens_image_sortie). Leve
    HTTPException sur echec."""
    url = f"{GEMINI_BASE_URL}/{model}:generateContent"
    body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": in_mime, "data": in_b64}},
                ]
            }
        ],
        # Sortie IMAGE explicite + resolution (imageSize : 1K/2K/4K).
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "imageConfig": {"imageSize": resolution},
        },
    }
    headers = {"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"}
    try:
        resp = httpx.post(url, json=body, headers=headers, timeout=120.0)
    except httpx.HTTPError as exc:
        logger.error("[GEMINI] transport error: %s", exc)
        raise HTTPException(status_code=504, detail="Le service de rendu n'a pas repondu")
    if resp.status_code != 200:
        logger.error("[GEMINI] %s: %s", resp.status_code, resp.text[:400])
        raise HTTPException(status_code=502, detail="Le service de rendu a echoue")
    try:
        data = resp.json()
    except ValueError:
        raise HTTPException(status_code=502, detail="Reponse de rendu illisible")
    tokens = image_output_tokens(data)
    # Extrait la 1ere partie image des candidates (inlineData ou inline_data).
    for cand in data.get("candidates") or []:
        for part in ((cand.get("content") or {}).get("parts") or []):
            inj = part.get("inlineData") or part.get("inline_data")
            if inj and inj.get("data"):
                out_mime = inj.get("mimeType") or inj.get("mime_type") or "image/png"
                return inj["data"], out_mime, tokens
    # Pas d'image : souvent un blocage de securite (promptFeedback).
    block = (data.get("promptFeedback") or {}).get("blockReason")
    logger.warning("[GEMINI] sans image (blockReason=%s)", block)
    raise HTTPException(status_code=502, detail="Aucune image generee par le service de rendu")


def call_gemini_text_to_image(
    model: str, prompt: str, resolution: str
) -> tuple[str, str, int]:
    """Appel SYNCHRONE (a lancer via asyncio.to_thread) a Gemini generateContent, SANS
    image d'entree. Renvoie (base64_image_sortie, mime_sortie, tokens_image_sortie).
    Leve HTTPException sur echec.

    POURQUOI UNE SECONDE FONCTION PLUTOT QU'UN PARAMETRE OPTIONNEL SUR LA PREMIERE :
    `call_gemini_image` a DEUX appelants en PRODUCTION (deux points d'acces
    distincts) dont le contrat est « je fournis une image, tu me
    rends la meme geometrie rendue ». Rendre son image d'entree facultative ferait
    silencieusement basculer ces deux chemins vers de la generation LIBRE le jour ou un
    appelant passerait une chaine vide -- un rendu invente au lieu du modele du client,
    sans aucune erreur. Deux fonctions, deux contrats : celui qui veut une scene a partir
    d'un texte seul le DIT.

    Le reste (URL, en-tetes, generationConfig, timeout, gestion d'erreur, extraction de
    la partie image, comptage des tokens) est identique a `call_gemini_image` : c'est la
    MEME surface Gemini, seule la composition de `contents.parts` change.
    """
    url = f"{GEMINI_BASE_URL}/{model}:generateContent"
    body = {
        # Aucune `inline_data` : c'est toute la difference avec l'appel image->image.
        "contents": [{"parts": [{"text": prompt}]}],
        # Sortie IMAGE explicite + resolution (imageSize : 1K/2K/4K).
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "imageConfig": {"imageSize": resolution},
        },
    }
    headers = {"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"}
    try:
        resp = httpx.post(url, json=body, headers=headers, timeout=120.0)
    except httpx.HTTPError as exc:
        logger.error("[GEMINI] transport error (text2img): %s", exc)
        raise HTTPException(status_code=504, detail="Le service de rendu n'a pas repondu")
    if resp.status_code != 200:
        logger.error("[GEMINI] text2img %s: %s", resp.status_code, resp.text[:400])
        raise HTTPException(status_code=502, detail="Le service de rendu a echoue")
    try:
        data = resp.json()
    except ValueError:
        raise HTTPException(status_code=502, detail="Reponse de rendu illisible")
    tokens = image_output_tokens(data)
    # Extrait la 1ere partie image des candidates (inlineData ou inline_data).
    for cand in data.get("candidates") or []:
        for part in ((cand.get("content") or {}).get("parts") or []):
            inj = part.get("inlineData") or part.get("inline_data")
            if inj and inj.get("data"):
                out_mime = inj.get("mimeType") or inj.get("mime_type") or "image/png"
                return inj["data"], out_mime, tokens
    # Pas d'image : souvent un blocage de securite (promptFeedback).
    block = (data.get("promptFeedback") or {}).get("blockReason")
    logger.warning("[GEMINI] text2img sans image (blockReason=%s)", block)
    raise HTTPException(status_code=502, detail="Aucune image generee par le service de rendu")
