# -*- coding: utf-8 -*-
"""apercu_u3d.py — dessine ce que CONTIENT un PDF 3D, vue par vue, sans lecteur PDF.

    python apercu_u3d.py fichier.pdf --sortie dossier [--largeur 1524] [--vues 1,2] [--planche]

À QUOI ÇA SERT. Tant qu'aucun lecteur n'a affiché le fichier, on n'a que des contrôles de
structure. Cet outil relit le U3D avec le lecteur à part (lire_u3d.py), applique la hiérarchie et
les matrices, les matières, puis la caméra de chaque vue du PDF (/C2W, /P, lus selon
ISO 32000-1 §13.6.5), et peint les triangles du plus loin au plus près. Une pièce posée de
travers, une matrice transposée, une vue en miroir ou qui regarde ailleurs : ça se VOIT.

CE QUE CE N'EST PAS : le rendu d'Acrobat ou de PDF-XChange. C'est NOTRE lecture du fichier. Si
elle est fausse de la même façon que nos écrivains, l'image sera belle et le lecteur vide : seul
un vrai lecteur tranche (voir_dans_lecteur.ps1).

Rend aussi une mesure utile : la part des faces dont la normale ÉCRITE regarde du même côté que
la face géométrique (une normale à l'envers donne une pièce noire dans le lecteur).
"""
import math
import os
import re
import sys
import unicodedata

import numpy as np
from PIL import Image, ImageDraw

sys.dont_write_bytecode = True          # pas de __pycache__ dans le dossier de l'outil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lire_u3d  # noqa: E402
import controle_pdf3d  # noqa: E402


def lire_pdf(chemin):
    """Rend (octets du U3D, liste des vues, taille du cadre)."""
    import fitz
    doc = fitz.open(chemin)
    cle = doc.xref_get_key
    flux = annot = None
    for x in range(1, doc.xref_length()):
        try:
            src = doc.xref_object(x, compressed=True)
        except Exception:
            continue
        if re.search(r"/Subtype\s*/U3D\b", src):
            flux = x
        if re.search(r"/Subtype\s*/3D\b", src) and re.search(r"/Type\s*/Annot\b", src):
            annot = x
    if flux is None:
        raise ValueError("aucun flux U3D dans %s" % chemin)
    u3d = doc.xref_stream(flux)
    rect = controle_pdf3d._nombres(cle(annot, "Rect")[1]) if annot else [0, 0, 762, 405]
    cadre = (rect[2] - rect[0], rect[3] - rect[1])
    vues = []
    va = cle(flux, "VA")
    for xv in [int(x) for x in re.findall(r"(\d+) 0 R", va[1])] if va[0] == "array" else []:
        v = {"nom": controle_pdf3d._texte_pdf(cle(xv, "XN")[1]), "objet": xv}
        if cle(xv, "MS")[1] == "/M":
            v["c2w"] = controle_pdf3d._nombres(cle(xv, "C2W")[1])
        v["projection"] = cle(xv, "P/Subtype")[1].lstrip("/")
        f = cle(xv, "P/FOV")
        v["fov"] = controle_pdf3d._nombres(f[1])[0] if f[0] != "null" else 90.0
        o = cle(xv, "P/OS")
        v["os"] = controle_pdf3d._nombres(o[1])[0] if o[0] != "null" else 1.0
        v["ob"] = cle(xv, "P/OB")[1].lstrip("/")
        bg = cle(xv, "BG/C")
        v["fond"] = controle_pdf3d._nombres(bg[1]) if bg[0] == "array" else [1, 1, 1]
        na = cle(xv, "NA")
        v["noeuds"] = {}
        if na[0] in ("array", "xref"):
            src = doc.xref_object(int(na[1].split()[0]), compressed=True) if na[0] == "xref" else na[1]
            for m in re.finditer(r"<<(.*?)>>", src, re.S):
                d = m.group(1)
                n = re.search(r"/N\s*(\((?:[^()\\]|\\.)*\)|<[0-9A-Fa-f\s]*>)", d)
                if not n:
                    continue
                vis = re.search(r"/V\s+(true|false)", d)
                v["noeuds"][controle_pdf3d._texte_pdf(n.group(1))] = None if not vis else vis.group(1) == "true"
        vues.append(v)
    doc.close()
    return u3d, vues, cadre


def scene_du_u3d(R):
    """Aplati la scène relue : triangles monde, couleur, normale écrite, nœud d'origine."""
    N = R["noeuds"]
    P, C, NF, QUI = [], [], [], []
    noms = []
    accord = [0, 0]
    for nom, d in N.items():
        if d["type"] != "modele":
            continue
        res = R["ressources"].get(d["ressource"], {})
        dn = res.get("donnees")
        if dn is None or not len(dn["faces"]):
            continue
        couleurs = []
        for i in range(max(1, len(res.get("tranches", [])))):
            c = (0.75, 0.75, 0.75, 1.0)
            if d["nuanceurs"] and i < len(d["nuanceurs"]) and d["nuanceurs"][i]:
                s = R["nuanceurs"].get(d["nuanceurs"][i][0])
                m = R["materiaux"].get(s["materiau"]) if s else None
                if m:
                    c = tuple(m["diffus"]) + (m["opacite"],)
            couleurs.append(c)
        couleurs = np.array(couleurs)
        for M in R["matrices_monde"].get(nom, []):
            w = dn["positions"] @ M[:3, :3].T + M[:3, 3]
            tri = w[dn["faces"]]                       # (nf, 3, 3)
            P.append(tri)
            C.append(couleurs[np.minimum(dn["tranches"], len(couleurs) - 1)])
            g = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
            if dn["faces_normales"] is not None and len(dn["normales"]):
                nn = dn["normales"][dn["faces_normales"]].mean(axis=1) @ M[:3, :3].T
                # la matrice peut retourner la pièce (miroir) : le sens des faces s'inverse avec elle
                signe = 1.0 if np.linalg.det(M[:3, :3]) >= 0 else -1.0
                ok = (np.einsum("ij,ij->i", nn, g) * signe) > 0
                accord[0] += int(ok.sum())
                accord[1] += len(ok)
                NF.append(nn)
            else:
                NF.append(g)
            QUI.append(np.full(len(tri), len(noms)))
            noms.append(nom)
    if not P:
        return None
    return {"tri": np.concatenate(P), "couleur": np.concatenate(C), "normale": np.concatenate(NF),
            "qui": np.concatenate(QUI), "noms": noms, "accord_normales": accord}


def visibles(R, vue):
    """Noms des nœuds de modèle montrés par la vue (un nœud masqué masque ses descendants)."""
    N = R["noeuds"]
    regle = vue.get("noeuds") or {}
    memo = {}

    def vis(nom):
        if nom == "" or nom not in N:
            return True
        if nom in memo:
            return memo[nom]
        v = regle.get(nom)
        if v is None:
            v = all(vis(p) for p, _ in N[nom]["parents"]) if N[nom]["parents"] else True
        elif v:
            v = True
        memo[nom] = v
        return v

    return {n for n, d in N.items() if d["type"] == "modele" and vis(n)}


def peindre(scene, R, vue, cadre, largeur=1524, sur=2, seuil=28.0):
    """Rend une image PIL de la vue.

    Les triangles sont peints du plus loin au plus près (algorithme du peintre). Deux grands
    triangles qui se croisent en profondeur se recouvriraient à tort : on DÉCOUPE donc en quatre,
    autant de fois qu'il faut, tout triangle dont un côté dépasse `seuil` pixels à l'écran."""
    L = int(largeur) * sur
    H = int(round(largeur * cadre[1] / cadre[0])) * sur
    fond = tuple(int(round(255 * x)) for x in vue["fond"][:3])
    img = Image.new("RGB", (L, H), fond)
    if "c2w" not in vue:
        return img.resize((L // sur, H // sur), Image.LANCZOS), "vue sans /C2W : cadrage laissé au lecteur, non dessinée"
    c = np.array(vue["c2w"], dtype=float)
    droite, haut, regard, pos = c[0:3], c[3:6], c[6:9], c[9:12]
    garde = visibles(R, vue)
    masque = np.array([n in garde for n in scene["noms"]])[scene["qui"]]
    tri = scene["tri"][masque]
    coul = scene["couleur"][masque]
    if not len(tri):
        return img.resize((L // sur, H // sur), Image.LANCZOS), "rien de visible"
    n_origine = len(tri)
    # éclairage : une lampe près de la caméra et un peu d'ambiant ; faces vues des deux côtés
    g = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    lon = np.linalg.norm(g, axis=1)
    lon[lon == 0] = 1
    g = g / lon[:, None]
    cle_l = -regard + 0.35 * haut - 0.25 * droite
    cle_l /= np.linalg.norm(cle_l)
    lum = 0.30 + 0.70 * np.abs(g @ cle_l)
    rgb = np.clip(coul[:, :3] * lum[:, None] + 0.06, 0, 1)
    f = np.array(fond) / 255.0
    a = coul[:, 3:4]
    rgb = rgb * a + f * (1 - a)                      # transparence simulée sur le fond
    rgb = (rgb * 255).astype(np.uint8)
    petit = min(L, H)

    def projeter(t3):
        v = t3 - pos
        x = v @ droite
        y = v @ haut
        z = v @ regard
        if vue["projection"] == "O":
            k = vue["os"] * (petit if vue.get("ob") in ("Min", "W", "H", "Max") else sur * largeur / cadre[0])
            return L / 2 + x * k, H / 2 - y * k, z, np.ones(len(t3), bool)
        t = math.tan(math.radians(vue["fov"]) / 2)
        devant = (z > 1e-6).all(axis=1)
        zz = np.where(z > 1e-6, z, 1e-6)
        return L / 2 + (x / zz) / t * (petit / 2), H / 2 - (y / zz) / t * (petit / 2), z, devant

    for _ in range(8):
        sx, sy, z, devant = projeter(tri)
        cote = np.zeros(len(tri))
        for i, j in ((0, 1), (1, 2), (2, 0)):
            cote = np.maximum(cote, np.hypot(sx[:, i] - sx[:, j], sy[:, i] - sy[:, j]))
        visible = devant & (sx.max(axis=1) >= 0) & (sx.min(axis=1) <= L) & (sy.max(axis=1) >= 0) & (sy.min(axis=1) <= H)
        # « gros » = grande SURFACE à l'écran (ou côté démesuré) : un barreau long et fin n'a pas
        # besoin d'être découpé, un pan de mur si
        aire = 0.5 * np.abs((sx[:, 1] - sx[:, 0]) * (sy[:, 2] - sy[:, 0]) - (sx[:, 2] - sx[:, 0]) * (sy[:, 1] - sy[:, 0]))
        gros = ((aire > 0.5 * (seuil * sur) ** 2) | (cote > 8 * seuil * sur)) & visible
        if not gros.any() or len(tri) + 3 * int(gros.sum()) > 3_000_000:
            break
        t = tri[gros]
        m01 = (t[:, 0] + t[:, 1]) / 2
        m12 = (t[:, 1] + t[:, 2]) / 2
        m20 = (t[:, 2] + t[:, 0]) / 2
        petits = np.concatenate([np.stack([t[:, 0], m01, m20], axis=1), np.stack([m01, t[:, 1], m12], axis=1),
                                 np.stack([m20, m12, t[:, 2]], axis=1), np.stack([m01, m12, m20], axis=1)])
        tri = np.concatenate([tri[~gros], petits])
        rgb = np.concatenate([rgb[~gros], np.tile(rgb[gros], (4, 1))])
    sx, sy, z, devant = projeter(tri)
    prof = z.mean(axis=1)
    ordre = np.argsort(-prof)
    ordre = ordre[devant[ordre]]
    d = ImageDraw.Draw(img)
    pts = np.stack([sx, sy], axis=2)
    for i in ordre:
        q = pts[i]
        d.polygon([(q[0, 0], q[0, 1]), (q[1, 0], q[1, 1]), (q[2, 0], q[2, 1])], fill=tuple(int(k) for k in rgb[i]))
    v0 = scene["tri"][masque] - pos
    if vue["projection"] == "O":
        dans_tout = np.ones(n_origine, bool)
    else:
        dans_tout = ((v0 @ regard) > 1e-6).all(axis=1)
    ox, oy, _, _ = projeter(scene["tri"][masque])
    dans = ((ox >= 0) & (ox <= L) & (oy >= 0) & (oy <= H)).all(axis=1) & dans_tout
    note = "%d triangles (%d peints après découpe), %.1f %% entièrement dans le cadre" % (
        n_origine, len(ordre), 100.0 * dans.mean())
    return img.resize((L // sur, H // sur), Image.LANCZOS), note


def principal(argv):
    args = [a for a in argv if not a.startswith("--")]
    if not args or "--sortie" not in argv:
        print(__doc__)
        return 2
    chemin = args[0]
    sortie = argv[argv.index("--sortie") + 1]
    largeur = int(argv[argv.index("--largeur") + 1]) if "--largeur" in argv else 1524
    choix = None
    if "--vues" in argv:
        choix = {int(x) for x in argv[argv.index("--vues") + 1].split(",")}
    os.makedirs(sortie, exist_ok=True)
    u3d, vues, cadre = lire_pdf(chemin)
    R = lire_u3d.lire(u3d)
    if R["anomalies"]:
        print("ATTENTION : %d anomalie(s) dans le U3D (voir lire_u3d.py)" % len(R["anomalies"]))
    scene = scene_du_u3d(R)
    if scene is None:
        print("APERCU_ERREUR aucun triangle décodé")
        return 1
    a = scene["accord_normales"]
    if a[1]:
        print("normales écrites du même côté que la face : %d sur %d (%.2f %%)" % (a[0], a[1], 100.0 * a[0] / a[1]))
    else:
        print("aucune normale écrite (le lecteur les calcule)")
    base = os.path.splitext(os.path.basename(chemin))[0]
    images = []
    for i, v in enumerate(vues, 1):
        if choix and i not in choix:
            continue
        img, note = peindre(scene, R, v, cadre, largeur)
        sans = "".join(ch for ch in unicodedata.normalize("NFD", v["nom"]) if unicodedata.category(ch) != "Mn")
        nom = re.sub(r"[^A-Za-z0-9_-]+", "_", sans)
        nom = re.sub(r"_+", "_", nom).strip("_") or "vue"
        f = os.path.join(sortie, "%s_vue%02d_%s.png" % (base, i, nom))
        img.save(f)
        images.append((v["nom"], img))
        print("vue %d « %s » (%s) : %s -> %s" % (i, v["nom"], "ortho" if v["projection"] == "O" else "perspective %g°" % v["fov"], note, f))
    if "--planche" in argv and images:
        n = len(images)
        cols = 2 if n > 1 else 1
        rangs = (n + cols - 1) // cols
        w, h = images[0][1].size
        e = 2
        pl = Image.new("RGB", (cols * (w // e) + (cols + 1) * 8, rangs * (h // e + 26) + 8), (255, 255, 255))
        d = ImageDraw.Draw(pl)
        try:
            from PIL import ImageFont
            police = ImageFont.truetype("arial.ttf", 14)
        except Exception:
            police = None
        for k, (nom, im) in enumerate(images):
            x0 = 8 + (k % cols) * (w // e + 8)
            y0 = 8 + (k // cols) * (h // e + 26)
            pl.paste(im.resize((w // e, h // e), Image.LANCZOS), (x0, y0 + 18))
            etq = "%d. %s" % (k + 1, nom)
            if police is None:
                etq = etq.encode("ascii", "replace").decode()
            d.text((x0, y0 + 1), etq, fill=(0, 0, 0), font=police)
        f = os.path.join(sortie, "%s_planche.png" % base)
        pl.save(f)
        print("planche -> %s" % f)
    print("APERCU_OK")
    return 0


if __name__ == "__main__":
    sys.exit(principal(sys.argv[1:]))
