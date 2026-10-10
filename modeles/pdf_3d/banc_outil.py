# -*- coding: utf-8 -*-
r"""banc_outil.py — le banc de l'outil PDF 3D : ce qu'il écrit se relit, et ses contrôles VOIENT.

    & $env:BM_PYTHON -X utf8 -s modeles\pdf_3d\banc_outil.py [--verbeux]

Quatre familles d'essais, sans Blender (quelques secondes) :
  1. SCÈNES RELUES. De petites scènes sont écrites par u3dWriterMulti.ts (Node) puis relues par
     lire_u3d.py (Python, écrit d'après la norme) : hiérarchie à trois niveaux, matrices composées
     (la boîte englobante attendue est calculée ICI, à la main, depuis la définition de la scène),
     maillage partagé, deux matières, fiches accentuées, unités en millimètres, normales.
  2. MUTATIONS DU U3D. Un fichier juste est abîmé de dix façons (taille des déclarations, parent
     renommé, indice hors bornes, bourrage non nul…) : le lecteur à part DOIT signaler chacune.
     Un contrôle qui ne rougit jamais ne prouve rien.
  3. MUTATIONS DU PDF. Idem pour controle_pdf3d.py (xref décalée, /Length faux, /AP retiré, caméra
     en miroir, nœud de vue inexistant…).
  4. LE MINI-BANC DES TESTS DE L'ERP PEUT ROUGIR. Les tests de l'ERP sont rejoués par un petit
     remplaçant de vitest : on vérifie, sur trois copies abîmées de u3dWriter.ts, qu'il échoue.
  5. L'ARBRE ET LES VUES de pdf_3d.py : noms uniques, règle des chemins, caméras bien formées.

Code de sortie 0 si tout passe. Dernière ligne : TOTAL : n sur m.
"""
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile

import fitz
import numpy as np

sys.dont_write_bytecode = True          # pas de __pycache__ dans le dossier de l'outil
fitz.TOOLS.mupdf_display_errors(False)      # les PDF abîmés exprès font parler MuPDF : on le fait taire
ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import controle_pdf3d  # noqa: E402
import lire_u3d  # noqa: E402
import pdf_3d  # noqa: E402

VERBEUX = "--verbeux" in sys.argv
passes, echecs = 0, []


def essai(nom, fn):
    global passes
    try:
        fn()
        passes += 1
        print("  OK    " + nom)
    except Exception as e:
        echecs.append(nom)
        print("  ECHEC %s\n        -> %s" % (nom, str(e)[:400]))


def exige(cond, message):
    if not cond:
        raise AssertionError(message)


def node():
    try:
        sys.path.insert(0, os.path.join(pdf_3d.RACINE, "outils"))
        import chemins
        return chemins.node_exe()
    except Exception:
        return os.environ["BM_NODE"]


NODE = node()
TRAVAIL = tempfile.mkdtemp(prefix="banc_pdf3d_")


def ecrire(scene, nom, pdf=False):
    """Écrit la scène par Node. Rend (octets du U3D, chemin du PDF ou None, sortie)."""
    fj = os.path.join(TRAVAIL, nom + ".json")
    fu = os.path.join(TRAVAIL, nom + ".u3d")
    fp = os.path.join(TRAVAIL, nom + ".pdf")
    with open(fj, "w", encoding="utf-8") as f:
        json.dump(scene, f, ensure_ascii=False)
    cmd = [NODE, "--import", "./noeud/crochet_ts.mjs", "./noeud/ecrire_scene_json.mjs", fj, fu] + ([fp] if pdf else [])
    r = subprocess.run(cmd, cwd=ICI, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    s = r.stdout.decode("utf-8", errors="replace")
    if r.returncode:
        raise AssertionError("écriture refusée : " + s.strip()[-300:])
    with open(fu, "rb") as f:
        return f.read(), (fp if pdf else None), s


# ------------------------------------------------------------------ une scène de référence
def boite_maillage(dx, dy, dz):
    """Une boîte [0,dx]x[0,dy]x[0,dz], 12 triangles, 2 tranches (dessus = tranche 1)."""
    P = [[0, 0, 0], [dx, 0, 0], [dx, dy, 0], [0, dy, 0], [0, 0, dz], [dx, 0, dz], [dx, dy, dz], [0, dy, dz]]
    F = [[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7], [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5], [2, 3, 7], [2, 7, 6],
         [3, 0, 4], [3, 4, 7]]
    T = [0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0]
    NORM = [[0, 0, -1], [0, 0, 1], [0, -1, 0], [1, 0, 0], [0, 1, 0], [-1, 0, 0]]
    NI = [[0] * 3, [0] * 3, [1] * 3, [1] * 3, [2] * 3, [2] * 3, [3] * 3, [3] * 3, [4] * 3, [4] * 3, [5] * 3, [5] * 3]
    return {"positions": [c for p in P for c in p], "indices": [i for f in F for i in f], "tranches": T, "nbTranches": 2,
            "normales": [c for n in NORM for c in n], "indicesNormales": [i for f in NI for i in f]}, np.array(P, float)


def colonnes(M):
    """Matrice numpy 4x4 -> 16 nombres, colonnes d'abord (ce que demande l'écrivain)."""
    return [float(M[r, c]) for c in range(4) for r in range(4)]


def translation(x, y, z):
    M = np.eye(4)
    M[:3, 3] = [x, y, z]
    return M


def rotation_z(deg):
    a = math.radians(deg)
    M = np.eye(4)
    M[0, 0], M[0, 1], M[1, 0], M[1, 1] = math.cos(a), -math.sin(a), math.sin(a), math.cos(a)
    return M


M_BOITE, P_BOITE = boite_maillage(2.0, 1.0, 0.5)
MG1 = translation(10, 0, 0)
MG2 = translation(0, 5, 0) @ rotation_z(90)
MA = translation(1, 2, 3)
MB = translation(-4, 0, 0) @ np.diag([2.0, 2.0, 2.0, 1.0])
MAT = [{"nom": "Acier peint", "ambiant": [0.2, 0.3, 0.25], "diffus": [0.2, 0.3, 0.25], "speculaire": [0.1, 0.1, 0.1],
        "emissif": [0, 0, 0], "reflectivite": 0.3, "opacite": 1.0},
       {"nom": "Vitre", "ambiant": [0.5, 0.6, 0.7], "diffus": [0.5, 0.6, 0.7], "speculaire": [0.4, 0.4, 0.4],
        "emissif": [0, 0, 0], "reflectivite": 0.6, "opacite": 0.35}]
VUE = {"nom": "Vue d'essai é", "c2w": [1, 0, 0, 0, 0, 1, 0, 1, 0, 3, -30, 2], "co": 30, "projection": "P", "fov": 30}


def scene_reference(**plus):
    s = {
        "noeuds": [
            {"nom": "Étage 1", "parent": "", "matrice": colonnes(MG1), "meta": {"Rôle": "groupe de tête"}},
            {"nom": "Travée nord", "parent": "Étage 1", "matrice": colonnes(MG2)},
            {"nom": "Pièce A — é", "parent": "Travée nord", "matrice": colonnes(MA), "maillage": "boite",
             "nuanceurs": ["Acier peint", "Vitre"], "meta": {"marque": "c101", "Désignation": "C310x31 × 4499 — côté « cour »"}},
            {"nom": "Pièce B", "parent": "", "matrice": colonnes(MB), "maillage": "boite",
             "nuanceurs": ["Vitre", "Acier peint"]},
        ],
        "maillages": [dict(M_BOITE, nom="boite")],
        "materiaux": MAT,
        "metresParUnite": 0.001,
        "pdf": {"titre": "Banc — scène de référence", "lignes": ["ligne 1", "ligne 2"], "vues": [
            VUE, dict(VUE, nom="Isoler A", noeuds=[{"nom": "Pièce B", "visible": False}, {"nom": "Étage 1", "visible": True}])],
            "vueDefaut": 0, "compression": False},
    }
    s.update(plus)
    return s


def boite_attendue():
    pts = []
    for M in (MG1 @ MG2 @ MA, MB):
        pts.append(P_BOITE @ M[:3, :3].T + M[:3, 3])
    pts = np.concatenate(pts)
    return pts.min(axis=0), pts.max(axis=0)


print("1. Scènes écrites par u3dWriterMulti.ts, relues par lire_u3d.py")
U_REF, PDF_REF, _ = ecrire(scene_reference(), "reference", pdf=True)
R_REF = lire_u3d.lire(U_REF)


def t_structure():
    exige(not R_REF["anomalies"], "anomalies : %s" % R_REF["anomalies"][:3])
    c = R_REF["comptes"]
    exige((c["groupes"], c["modeles"], c["ressources"], c["materiaux"], c["nuanceurs"]) == (2, 2, 1, 2, 2), str(c))
    exige(c["triangles_poses"] == 24 and c["triangles_ressources"] == 12, "triangles %s" % c)
    exige(c["profondeur"] == 3, "profondeur %s" % c["profondeur"])


def t_hierarchie():
    N = R_REF["noeuds"]
    exige([p for p, _ in N["Pièce A — é"]["parents"]] == ["Travée nord"], "parent de A")
    exige([p for p, _ in N["Travée nord"]["parents"]] == ["Étage 1"], "parent de la travée")
    exige([p for p, _ in N["Étage 1"]["parents"]] == [""], "parent de l'étage")
    exige(N["Pièce A — é"]["ressource"] == "boite" == N["Pièce B"]["ressource"], "ressource partagée")
    exige(N["Pièce A — é"]["visibilite"] == 3, "visibilité des deux côtés")


def t_matrices():
    lo, hi = boite_attendue()
    b = np.array(R_REF["boite"])
    exige(np.abs(b[0] - lo).max() < 1e-5 and np.abs(b[1] - hi).max() < 1e-5,
          "boîte relue %s, attendue %s %s" % (b.tolist(), lo.tolist(), hi.tolist()))
    M = R_REF["matrices_monde"]["Pièce A — é"][0]
    exige(np.abs(M - MG1 @ MG2 @ MA).max() < 1e-5, "matrice monde de A")


def t_matieres():
    N = R_REF["noeuds"]
    exige(N["Pièce A — é"]["nuanceurs"] == [["Acier peint"], ["Vitre"]], str(N["Pièce A — é"]["nuanceurs"]))
    exige(N["Pièce B"]["nuanceurs"] == [["Vitre"], ["Acier peint"]], "matières de B (même maillage, autre ordre)")
    m = R_REF["materiaux"]["Vitre"]
    exige(abs(m["opacite"] - 0.35) < 1e-6 and abs(m["diffus"][2] - 0.7) < 1e-6 and m["attributs"] == 0x3F, str(m))
    s = R_REF["nuanceurs"]["Vitre"]
    exige(s["materiau"] == "Vitre" and s["attributs"] == 1 and s["test_alpha"] == 0x617 and s["melange"] == 0x606
          and s["passes"] == 1 and s["canaux"] == 0, str(s))
    exige(R_REF["ressources"]["boite"]["donnees"]["tranches"].tolist() == M_BOITE["tranches"], "tranches des faces")


def t_fiches():
    m = R_REF["noeuds"]["Pièce A — é"]["meta"]
    exige(m == {"marque": "c101", "Désignation": "C310x31 × 4499 — côté « cour »"}, str(m))
    exige(R_REF["noeuds"]["Étage 1"]["meta"] == {"Rôle": "groupe de tête"}, "fiche du groupe")
    exige(R_REF["noeuds"]["Pièce B"]["meta"] == {}, "B n'a pas de fiche")


def t_entete():
    e = R_REF["entete"]
    # par défaut : COMPRESSÉ (pas de bit 0x04), unités définies (0x08)
    exige(e["profil"] == 0x8 and abs(e["echelle"] - 0.001) < 1e-12 and e["encodage"] == 106, str(e))
    exige(R_REF["compresse"] is True, "le fichier de référence devrait être compressé")
    exige(R_REF.get("priorites") == [256], "mise à jour de priorité : %s" % R_REF.get("priorites"))
    bits = R_REF["ressources"]["boite"].get("bits_apres_faces")
    exige(bits is not None and 16 <= bits <= 96, "bits restant après la dernière face (le U32 nul final) : %s" % bits)


def t_non_compresse():
    """Le MÊME contenu sans compression (la forme de l'ERP) : mêmes données relues, profil 0xC, pas de zéro final."""
    u, _, _ = ecrire(scene_reference(compat={"compresse": False}), "non_compresse")
    r = lire_u3d.lire(u)
    exige(not r["anomalies"], str(r["anomalies"][:3]))
    exige(r["entete"]["profil"] == 0xC and r["compresse"] is False, "profil %s" % r["entete"])
    exige(r["ressources"]["boite"].get("zero_final") is None, "pas de zéro final sans compression (10.4.10)")
    a, b = R_REF["ressources"]["boite"]["donnees"], r["ressources"]["boite"]["donnees"]
    for cle in ("positions", "normales", "faces", "faces_normales", "tranches"):
        exige(np.array_equal(a[cle], b[cle]), "%s : la version compressée et la non compressée diffèrent" % cle)
    exige(len(U_REF) < len(u), "le fichier compressé (%d octets) devrait être plus court que l'autre (%d)" % (len(U_REF), len(u)))
    u2, _, _ = ecrire(scene_reference(compat={"compresse": False, "zeroFinal": True}), "non_compresse_zero")
    r2 = lire_u3d.lire(u2)
    exige(not r2["anomalies"] and r2["ressources"]["boite"].get("zero_final") is True and len(u2) == len(u) + 4,
          "réglage zeroFinal : %s" % r2["anomalies"][:2])


def t_gros_maillages():
    """Compressé contre non compressé sur les cas qui changent le codage : plus de 8 191 faces (l'histogramme
    des tranches est divisé par deux, 10.4.9), plus de 16 382 positions (indices écrits en clair, 10.4)."""
    import random
    rnd = random.Random(7)
    for nom, nf, npos, nnor, ntr in (("9000_faces", 9000, 300, 40, 3), ("17000_positions", 6000, 17000, 0, 2),
                                     ("une_face", 1, 3, 1, 1)):
        libres = list(range(npos))
        rnd.shuffle(libres)
        idx = []
        for _ in range(nf):
            tri = []
            while len(tri) < 3:
                v = libres.pop() if libres else rnd.randrange(npos)
                if v not in tri:
                    tri.append(v)
            idx += tri
        m = {"nom": "g", "positions": [round(rnd.uniform(-9, 9), 3) for _ in range(npos * 3)], "indices": idx,
             "nbTranches": ntr, "tranches": [(i // 700) % ntr if i % 5 else rnd.randrange(ntr) for i in range(nf)]}
        if nnor:
            m["normales"] = [0.0, 0.0, 1.0] * nnor
            m["indicesNormales"] = [rnd.randrange(nnor) for _ in range(nf * 3)]
        sc = {"noeuds": [{"nom": "n", "parent": "", "maillage": "g"}], "maillages": [m], "materiaux": []}
        lus = []
        for compresse in (True, False):
            u, _, _ = ecrire(dict(sc, compat={"compresse": compresse}), "gros_%s_%d" % (nom, compresse))
            r = lire_u3d.lire(u)
            exige(not r["anomalies"], "%s (compressé=%s) : %s" % (nom, compresse, r["anomalies"][:2]))
            lus.append(r["ressources"]["g"]["donnees"])
        d = lus[0]
        exige(d["faces"].reshape(-1).tolist() == idx, "%s : faces relues différentes des faces données" % nom)
        exige(d["tranches"].tolist() == m["tranches"], "%s : tranches relues différentes" % nom)
        if nnor:
            exige(d["faces_normales"].reshape(-1).tolist() == m["indicesNormales"], "%s : indices de normales" % nom)
        for cle in ("positions", "faces", "tranches"):
            exige(np.array_equal(lus[0][cle], lus[1][cle]), "%s : %s diffèrent entre les deux codages" % (nom, cle))


def t_normales():
    d = R_REF["ressources"]["boite"]["donnees"]
    exige(d["normales"].shape == (6, 3) and d["faces_normales"].tolist() == np.array(M_BOITE["indicesNormales"]).reshape(-1, 3).tolist(),
          "normales et leurs indices")
    exige(np.abs(d["positions"] - P_BOITE).max() < 1e-6, "positions")
    exige(d["faces"].tolist() == np.array(M_BOITE["indices"]).reshape(-1, 3).tolist(), "faces")


def t_sans_normales():
    m = {k: v for k, v in M_BOITE.items() if k not in ("normales", "indicesNormales")}
    u, _, _ = ecrire(scene_reference(maillages=[dict(m, nom="boite")]), "sans_normales")
    r = lire_u3d.lire(u)
    exige(not r["anomalies"], str(r["anomalies"][:3]))
    exige(r["ressources"]["boite"]["exclut_normales"] and r["ressources"]["boite"]["normales"] == 0, "normales exclues")
    exige(r["ressources"]["boite"]["donnees"]["faces"].tolist() == np.array(M_BOITE["indices"]).reshape(-1, 3).tolist(), "faces")


def t_compat():
    for compat in ({"priorite": False}, {"compresse": False}, {"compresse": False, "zeroFinal": True}, {"chainesDeGroupe": False},
                   {"fiches": False}, {"unitesDefinies": False}, {"compresse": False, "unitesDefinies": False},
                   {"attributsNuancage": 15}, {"priorite": False, "zeroFinal": False, "chainesDeGroupe": False, "fiches": False}):
        u, _, _ = ecrire(scene_reference(compat=compat), "compat")
        r = lire_u3d.lire(u)
        exige(not r["anomalies"], "%s -> %s" % (compat, r["anomalies"][:2]))
        exige(r["comptes"]["triangles_poses"] == 24, "%s : triangles" % compat)
        b = np.array(r["boite"])
        lo, hi = boite_attendue()
        exige(np.abs(b[0] - lo).max() < 1e-5, "%s : boîte" % compat)
        if compat.get("fiches") is False:
            exige(r["comptes"]["noeuds_avec_metadonnees"] == 0, "fiches coupées")


essai("structure : 0 anomalie, 2 groupes, 2 pièces, 1 maillage partagé, 2 matières", t_structure)
essai("hiérarchie à trois niveaux et ressource partagée", t_hierarchie)
essai("matrices composées : boîte englobante = celle calculée à la main (translation, rotation, échelle)", t_matrices)
essai("matières par nœud et par tranche (même maillage, matières différentes)", t_matieres)
essai("fiches (métadonnées) accentuées, relues à l'identique", t_fiches)
essai("en-tête : compressé, unités en mm, UTF-8 ; priorité 256 ; bits du U32 nul final", t_entete)
essai("sans compression (la forme de l'ERP) : mêmes données relues, profil 0xC, zéro final sur demande", t_non_compresse)
essai("compressé = non compressé sur 9 000 faces, 17 000 positions, une seule face", t_gros_maillages)
essai("normales écrites et indices par coin", t_normales)
essai("variante sans normales (le lecteur les calcule)", t_sans_normales)
essai("les réglages de compatibilité donnent tous un fichier juste", t_compat)


# ------------------------------------------------------------------ 2. mutations du U3D
print("2. Mutations du U3D : le lecteur à part doit signaler chacune")


def remplacer(octets, ancien, nouveau, rang=0):
    """Remplace la rang-ième occurrence de `ancien` (même longueur)."""
    assert len(ancien) == len(nouveau)
    p = -1
    for _ in range(rang + 1):
        p = octets.find(ancien, p + 1)
        if p < 0:
            raise AssertionError("motif introuvable : %r" % ancien)
    return octets[:p] + nouveau + octets[p + len(ancien):]


def chaine_u3d(s):
    b = s.encode("utf-8")
    return struct.pack("<H", len(b)) + b


def doit_signaler(nom, mutant, motif):
    def fn():
        r = lire_u3d.lire(mutant)
        exige(r["anomalies"], "aucune anomalie signalée")
        exige(any(re.search(motif, x) for x in r["anomalies"]), "anomalies sans rapport : %s" % r["anomalies"][:3])
    essai(nom, fn)


U = U_REF
doit_signaler("taille des déclarations faussée (+4)", U[:20] + struct.pack("<I", struct.unpack("<I", U[20:24])[0] + 4) + U[24:], r"déclarations")
doit_signaler("taille du fichier faussée", U[:24] + struct.pack("<Q", len(U) + 8) + U[32:], r"annonce")
doit_signaler("fichier tronqué de 8 octets", U[:-8], r"déborde|annonce|orphelin")
doit_signaler("parent renommé dans un nœud (« Étage 1 » -> « Étage 9 »)",
              remplacer(U, chaine_u3d("Étage 1"), chaine_u3d("Étage 9"), rang=2), r"parent .* jamais défini")
doit_signaler("ressource renommée dans un nœud de modèle",
              remplacer(U, chaine_u3d("boite") + struct.pack("<I", 3), chaine_u3d("boitX") + struct.pack("<I", 3)), r"ressource .* jamais définie")
doit_signaler("nuanceur renommé dans un modificateur de nuançage",
              remplacer(U, struct.pack("<I", 1) + chaine_u3d("Vitre"), struct.pack("<I", 1) + chaine_u3d("Vitrx")), r"nuanceur .* jamais défini")
p_mat = U.find(chaine_u3d("Vitre") + struct.pack("<I", 0x3F))
doit_signaler("matériau renommé (le nuanceur le cherche)",
              U[:p_mat] + chaine_u3d("Vitrz") + U[p_mat + 7:], r"matériau .* jamais défini")
# SANS compression (la forme de l'ERP), les faces sont des U32 en clair : le dernier indice de position de la
# dernière face est 12 octets avant la fin (suivi de l'indice de normale et du zéro final demandé)
U_NC, _, _ = ecrire(scene_reference(compat={"compresse": False, "zeroFinal": True}), "reference_nc")
fin = len(U_NC) - 4
doit_signaler("sans compression : indice de sommet hors bornes dans une face",
              U_NC[:fin - 8] + struct.pack("<I", 999) + U_NC[fin - 4:], r"hors bornes")
# COMPRESSÉ : le flux des faces est à la fin du fichier (bloc de suite du seul maillage). Un octet faussé au
# milieu désynchronise le décodeur ; la fin du flux mise à zéro lui retire ses derniers bits.
p_suite = U.rfind(struct.pack("<I", 0xFFFFFF3B))
n_suite = struct.unpack("<I", U[p_suite + 4:p_suite + 8])[0]
d_faces = p_suite + 12 + n_suite - 24            # dans les 24 derniers octets du bloc : le flux des faces
doit_signaler("compressé : un octet du flux des faces inversé",
              U[:d_faces] + bytes([U[d_faces] ^ 0xFF]) + U[d_faces + 1:], r".")
doit_signaler("compressé : les 12 derniers octets du flux des faces mis à 0xFF",
              U[:p_suite + 12 + n_suite - 12] + b"\xff" * 12 + U[p_suite + 12 + n_suite:], r".")
# une taille de bloc augmentée d'un octet : tout ce qui suit se décale
doit_signaler("taille de données du 1er bloc de chaîne augmentée de 1", U[:48] + struct.pack("<I", struct.unpack("<I", U[48:52])[0] + 1) + U[52:],
              r"align|déborde|illisible|non lus|bourrage|orphelin|déclarations")
p_nom = U.find(chaine_u3d("Étage 1"))
doit_signaler("nom de nœud vidé (le nom vide est le monde)", U[:p_nom] + struct.pack("<H", 0) + b"\x00" * 8 + U[p_nom + 10:], r".")
essai("témoin : le fichier non abîmé ne signale rien", lambda: exige(not lire_u3d.lire(U)["anomalies"], "anomalies sur le témoin"))

# ------------------------------------------------------------------ 3. mutations du PDF
print("3. Mutations du PDF : controle_pdf3d.py doit signaler chacune")
with open(PDF_REF, "rb") as f:
    PDF = f.read()
ATTENDU = {"mode": "fabrication", "textes": ["Banc — scène de référence", "ligne 2"]}


def controle(octets, nom="m"):
    f = os.path.join(TRAVAIL, nom + ".pdf")
    with open(f, "wb") as fh:
        fh.write(octets)
    return controle_pdf3d.controler(f, None, ATTENDU)


def pdf_doit_signaler(nom, mutant, motif):
    def fn():
        try:
            L, KO, _ = controle(mutant)
        except Exception as e:          # un PDF trop abîmé pour être ouvert : c'est aussi un signalement
            KO = ["exception : %s" % e]
        exige(KO, "aucun échec signalé")
        exige(any(re.search(motif, x) for x in KO), "échecs sans rapport : %s" % KO[:3])
    essai(nom, fn)


def t_temoin_pdf():
    L, KO, M = controle(PDF, "temoin")
    exige(not KO, "échecs sur le témoin : %s" % KO[:3])
    exige(len(M["vues"]) == 2 and M["vues"][0]["nom"] == "Vue d'essai é", "vues relues : %s" % [v["nom"] for v in M["vues"]])
    exige(M["vues"][1]["noeuds"] == ["Pièce B", "Étage 1"], "nœuds de la vue : %s" % M["vues"][1]["noeuds"])
    exige(M["octets_u3d"] == len(U_REF), "longueur du flux")


essai("témoin : le PDF non abîmé passe, vues et nœuds relus (noms accentués)", t_temoin_pdf)
m = re.search(rb"xref\n0 \d+\n", PDF)
p_ligne = m.end() + 20 * 6               # entrée de l'objet 6 (le flux 3D)
dec = int(PDF[p_ligne:p_ligne + 10]) + 1
pdf_doit_signaler("xref : décalage de l'objet 6 faussé d'un octet", PDF[:p_ligne] + b"%010d" % dec + PDF[p_ligne + 10:], r"xref|flux|3D|exception")
ml = re.search(rb"/Length (\d+) >>\nstream\n\x55\x33\x44\x00", PDF)
pdf_doit_signaler("/Length du flux 3D diminué de 4", PDF[:ml.start(1)] + (b"%d" % (int(ml.group(1)) - 4)).rjust(len(ml.group(1))) + PDF[ml.end(1):],
                  r"Length|endstream|annonce|anomalie|exception")
pdf_doit_signaler("/Subtype /3D de l'annotation abîmé", PDF.replace(b"/Type /Annot /Subtype /3D ", b"/Type /Annot /Subtype /3X "), r"annotation")
pdf_doit_signaler("/AP retiré de l'annotation", PDF.replace(b"/AP << /N 8 0 R >>", b"/AQ << /N 8 0 R >>"), r"/AP|repli")
# (haut et regard échangés : même longueur en octets, mais le trièdre devient direct)
pdf_doit_signaler("caméra en miroir (haut et regard échangés dans /C2W)", PDF.replace(b"/C2W [1 0 0 0 0 1 0 1 0 ", b"/C2W [1 0 0 0 1 0 0 0 1 "), r"miroir|direct")
pdf_doit_signaler("nœud de vue inexistant dans le U3D", PDF.replace(b"FEFF005000690", b"FEFF005800690"), r"nœuds existent|absents")
pdf_doit_signaler("mode de rendu inconnu de la norme", PDF.replace(b"/Subtype /Solid >>", b"/Subtype /Solyd >>"), r"rendu")
pdf_doit_signaler("texte attendu absent de la page", PDF.replace(b"(ligne 2)", b"(ligne X)"), r"texte")
pdf_doit_signaler("/3DD de l'annotation pointé ailleurs", PDF.replace(b"/3DD 6 0 R", b"/3DD 5 0 R"), r"3DD")

# propriétés du document (« Fichier > Propriétés ») : un second PDF de référence, qui en porte
PROP = {"titre": "Banc — propriétés", "auteur": "Préparé par une IA (Claude)", "sujet": "RÉF. 0123456789ab — à valider"}
_, PDF_PROP, _ = ecrire(scene_reference(pdf=dict(scene_reference()["pdf"], proprietes=PROP)), "proprietes", pdf=True)
with open(PDF_PROP, "rb") as f:
    PDFP = f.read()


def controle_prop(octets, voulues, interdits=(), nom="p"):
    f = os.path.join(TRAVAIL, nom + ".pdf")
    with open(f, "wb") as fh:
        fh.write(octets)
    return controle_pdf3d.controler(f, None, dict(ATTENDU, proprietes=voulues, interdits=list(interdits)))


def t_proprietes():
    L, KO, M = controle_prop(PDFP, PROP, nom="prop_temoin")
    exige(not KO, "échecs sur le témoin : %s" % KO[:3])
    exige(M["proprietes"] == {"title": PROP["titre"], "author": PROP["auteur"], "subject": PROP["sujet"]},
          "propriétés relues : %s" % M["proprietes"])
    L, KO, M = controle_prop(PDF, {}, nom="prop_aucune")
    exige(not KO and M["proprietes"] == {}, "le PDF sans propriétés devrait passer quand on n'en veut aucune : %s" % KO[:3])
    # /Info est le DERNIER objet (le 11e ici) : les dix premiers sont ceux du PDF sans propriétés
    i, j = PDFP.find(b"\n11 0 obj\n"), PDF.find(b"xref\n0 11\n")
    exige(i > 0 and j > 0 and PDFP[:i + 1] == PDF[:j], "les objets qui précèdent /Info devraient être ceux du PDF sans propriétés")


def prop_doit_signaler(nom, octets, voulues, motif, interdits=()):
    def fn():
        L, KO, _ = controle_prop(octets, voulues, interdits)
        exige(KO, "aucun échec signalé")
        exige(any(re.search(motif, x) for x in KO), "échecs sans rapport : %s" % KO[:3])
    essai(nom, fn)


essai("propriétés : titre, auteur et sujet accentués relus à l'identique ; aucune quand on n'en veut aucune", t_proprietes)
prop_doit_signaler("propriétés : un auteur autre que celui voulu", PDFP, dict(PROP, auteur="Quelqu'un d'autre"), r"propriétés")
prop_doit_signaler("propriétés : présentes alors qu'on n'en veut aucune (version simple)", PDFP, {}, r"propriétés")
prop_doit_signaler("propriétés : absentes alors qu'on les veut", PDF, PROP, r"propriétés")
# (/Subject et /Creator ont la même longueur : le sujet passe sous « Créé par », une propriété non voulue)
prop_doit_signaler("propriétés : une clé non voulue (/Creator)", PDFP.replace(b"/Subject <", b"/Creator <"), PROP, r"propriétés")
prop_doit_signaler("terme interdit présent dans une propriété seulement", PDFP, PROP, r"terme", interdits=["0123456789ab"])

# ------------------------------------------------------------------ 4. le mini-banc de l'ERP peut rougir
print("4. Le remplaçant de vitest échoue bien sur un écrivain abîmé (3 mutations de u3dWriter.ts)")
MUTATIONS = [
    ("nœud sans parent (le défaut muet de l'ERP)", "    c.u32(1);            // UN parent : le monde", "    c.u32(0);"),
    ("bourrage supprimé (alignement)", "  return (4 - (n % 4)) % 4;", "  return 0;"),
    ("axes non convertis", "const x = mx; const y = mz === 0 ? 0 : -mz; const z = my;", "const x = mx; const y = my; const z = mz;"),
]


def banc_erp_dans(dossier):
    r = subprocess.run([NODE, "--import", "./noeud/crochet_ts.mjs", "./noeud/banc_erp.mjs"], cwd=dossier,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    s = r.stdout.decode("utf-8", errors="replace")
    m = re.search(r"TOTAL : (\d+) sur (\d+)", s)
    return r.returncode, (int(m.group(1)), int(m.group(2))) if m else None


for nom, ancien, nouveau in MUTATIONS:
    def fn(ancien=ancien, nouveau=nouveau):
        d = os.path.join(TRAVAIL, "mutant_erp")
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d)
        shutil.copytree(os.path.join(ICI, "erp"), os.path.join(d, "erp"))
        shutil.copytree(os.path.join(ICI, "noeud"), os.path.join(d, "noeud"))
        shutil.copy(os.path.join(ICI, "package.json"), d)
        f = os.path.join(d, "erp", "atelier", "u3dWriter.ts")
        src = open(f, encoding="utf-8").read()
        exige(src.count(ancien) == 1, "la ligne à abîmer n'est plus dans u3dWriter.ts (la copie de l'ERP a changé ?)")
        open(f, "w", encoding="utf-8", newline="\n").write(src.replace(ancien, nouveau))
        code, total = banc_erp_dans(d)
        exige(code != 0 and total is not None and total[0] < total[1], "le banc reste vert sur le mutant (%s, code %s)" % (total, code))
    essai("mutant « %s » : le banc rougit" % nom, fn)


def t_banc_erp_vert():
    code, total = banc_erp_dans(ICI)
    exige(code == 0 and total == (37, 37), "banc de l'ERP sur les copies inchangées : %s, code %s" % (total, code))


essai("témoin : sur les copies inchangées de l'ERP, 37 tests sur 37", t_banc_erp_vert)

# ------------------------------------------------------------------ 5. l'arbre et les vues
print("5. L'arbre du modèle et les vues (pdf_3d.py)")


def objet(nom, collections=(), **props):
    return {"nom": nom, "objet": nom, "maillage": 0, "matrice": colonnes(np.eye(4)), "materiaux": ["m"],
            "collections": list(collections), "proprietes": props, "boite": [[0, 0, 0], [1, 1, 1]]}


def scene_arbre(objets):
    return {"objets": objets, "maillages": [{"nom": "cube", "triangles": 12}],
            "materiaux": [{"nom": "m", "couleur": [0.5, 0.5, 0.5], "couleur_lineaire": [0.2, 0.2, 0.2], "opacite": 1.0,
                           "metal": 0.0, "rugosite": 0.5, "source": "essai"}]}


def t_arbre_collections():
    sc = scene_arbre([objet("Mur nord", ["MURS-EXT"]), objet("Mur sud", ["MURS-EXT"]), objet("Toit", ["TOIT", "PENTES"]),
                      objet("MURS-EXT", ["DIVERS"]), objet("Seul")])
    n, r, m = pdf_3d.construire_arbre(sc, [], "marque", {}, {}, True)
    noms = [x["nom"] for x in n]
    exige(len(noms) == len(set(noms)), "noms en double : %s" % noms)
    par_nom = {x["nom"]: x for x in n}
    exige(par_nom["Mur nord"]["parent"] == "MURS-EXT" and par_nom["PENTES"]["parent"] == "TOIT", "collections imbriquées")
    exige(par_nom["Seul"]["parent"] == "", "objet à la racine")
    exige("MURS-EXT (2)" in par_nom and par_nom["MURS-EXT (2)"]["type"] == "modele", "objet du même nom qu'un groupe : %s" % noms)
    ordre = {x["nom"]: i for i, x in enumerate(n)}
    exige(all(x["parent"] == "" or ordre[x["parent"]] < ordre[x["nom"]] for x in n), "un parent après son enfant")


def t_arbre_proprietes():
    sc = scene_arbre([
        objet("V1.1.c101.1", ["ESC-LIMONS"], marque="c101", assemblage="V1", repere="V1"),
        objet("GB1.1.b112.1", ["GC-BARREAUX"], marque="b112", assemblage="GB1", repere="GB1-N1"),
        objet("GB1.1.b112.2", ["GC-BARREAUX"], marque="b112", assemblage="GB1", repere="GB1-N1"),
        objet("GB1.2.b112.1", ["GC-BARREAUX"], marque="b112", assemblage="GB1", repere="GB1-N2"),
        objet("B0001.1", ["BOULONNERIE"], boulon="B0001", type_boulon="boulon", agent="M"),
        objet("Mur", ["CTX-MUR"]),
    ])
    niveaux = pdf_3d.choisir_niveaux(sc, "auto")
    exige(niveaux == ["assemblage", "repere", "boulon"], str(niveaux))
    n, r, m = pdf_3d.construire_arbre(sc, niveaux, "marque", {"GB1": "GB1 — garde-corps", "b112": "b112 — barreau"},
                                      {"b112": {"Profilé": "RB13"}}, True)
    par_nom = {x["nom"]: x for x in n}
    exige(len(par_nom) == len(n), "noms en double")
    exige(par_nom["c101 · V1.1.c101.1"]["parent"] == "V1", "V1/V1 doit se réduire à V1")
    exige(par_nom["b112 — barreau · GB1.1.b112.2"]["parent"] == "GB1-N1" and par_nom["GB1-N1"]["parent"] == "GB1 — garde-corps", "assemblage puis repère")
    exige(par_nom["B0001.1"]["parent"] == "B0001" and par_nom["B0001"]["parent"] == "BOULONNERIE", "boulon sous sa collection puis son groupe")
    exige(par_nom["Mur"]["parent"] == "CTX-MUR", "objet sans propriété : sa collection")
    f = par_nom["b112 — barreau · GB1.1.b112.2"]["meta"]
    exige(f.get("Profilé") == "RB13" and f.get("marque") == "b112" and f.get("Objet") == "GB1.1.b112.2", str(f))
    exige("agent" not in par_nom["B0001.1"]["meta"], "la propriété « agent » ne doit pas sortir")


def t_vues():
    boite = [[-5.0, -2.0, 0.0], [5.0, 5.0, 11.0]]
    coins = np.array(pdf_3d.coins_boite(boite))
    for cadre in ((762.0, 405.0), (400.0, 700.0)):
        for az, el, ortho in ((45, 30, False), (0, 0, True), (90, 0, True), (180, 90, True), (-135, 25, False), (10, -90, False), (200, 60, True)):
            v = pdf_3d.vue_orbite("v", az, el, boite, cadre, ortho=ortho)
            c = np.array(v["c2w"])
            Rm = c[:9].reshape(3, 3)
            exige(np.allclose(Rm @ Rm.T, np.eye(3), atol=1e-4), "axes non orthonormés (%s, %s)" % (az, el))
            exige(np.linalg.det(Rm) < -0.99, "trièdre direct (%s, %s) : image en miroir" % (az, el))
            x = (coins - c[9:]) @ Rm[0]
            y = (coins - c[9:]) @ Rm[1]
            z = (coins - c[9:]) @ Rm[2]
            petit = min(cadre)
            if ortho:
                k = petit / v["etendue_ortho"]
                sx, sy = x * k, y * k
            else:
                exige((z > 0).all(), "un coin derrière la caméra (%s, %s)" % (az, el))
                t = math.tan(math.radians(v["fov"]) / 2)
                sx, sy = x / z / t * petit / 2, y / z / t * petit / 2
            exige(np.abs(sx).max() <= cadre[0] / 2 + 1e-6 and np.abs(sy).max() <= cadre[1] / 2 + 1e-6,
                  "la boîte sort du cadre (%s, %s, ortho=%s) : %.1f x %.1f" % (az, el, ortho, np.abs(sx).max() * 2, np.abs(sy).max() * 2))
            plein = max(np.abs(sx).max() / (cadre[0] / 2), np.abs(sy).max() / (cadre[1] / 2))
            exige(plein > 0.80, "cadrage trop lâche (%s, %s) : %.0f %% du cadre" % (az, el, plein * 100))
            exige(v["co"] > 0, "/CO non positif")
    v = pdf_3d.vue_orbite("dessus", 0, 90, boite, (762.0, 405.0), ortho=True)
    exige(np.allclose(v["c2w"][3:6], [0, 1, 0], atol=1e-6), "vue de dessus : le haut de l'image doit être +Y, trouvé %s" % v["c2w"][3:6])
    v = pdf_3d.vue_orbite("face", 0, 0, boite, (762.0, 405.0))
    exige(np.allclose(v["c2w"][0:9], [1, 0, 0, 0, 0, 1, 0, 1, 0], atol=1e-6), "vue de face : %s" % v["c2w"][:9])


def t_decor():
    def o(nom, col, n, boite):
        return {"nom": nom, "collections": [col], "maillage": n, "boite": boite, "proprietes": {}, "materiaux": []}
    sc = {"objets": [o("maison", "MURS-EXT", 0, [[0, 0, 0], [10, 8, 6]]), o("terrain", "TERRAIN", 1, [[-500, -500, -1], [500, 500, 0]]),
                     o("haie", "VEGETATION", 2, [[-2, -2, 0], [12, 10, 2]]), o("arbre", "VEGETATION", 3, [[11, 0, 0], [14, 3, 8]])],
          "maillages": [{"triangles": 5000}, {"triangles": 2}, {"triangles": 300}, {"triangles": 900}]}
    ecartes, garde = pdf_3d.ecarter_decor(sc, 2_000_000, "mètre")
    exige([x[0] for x in ecartes] == ["TERRAIN"], "seul le terrain (étendue) doit partir : %s" % ecartes)
    exige(garde.tolist() == [True, False, True, True], str(garde.tolist()))
    sc["maillages"][3]["triangles"] = 900000
    ecartes, garde = pdf_3d.ecarter_decor(sc, 2_000_000, "mètre")
    exige([x[0] for x in ecartes] == ["TERRAIN", "VEGETATION"], "la végétation pèse plus que tout le reste : %s" % ecartes)
    sc2 = {"objets": [o("sol", "SOL", 0, [[0, 0, 0], [5, 5, 0]]), o("herbe", "HERBE", 1, [[0, 0, 0], [5, 5, 1]])],
           "maillages": [{"triangles": 10}, {"triangles": 10}]}
    ecartes, garde = pdf_3d.ecarter_decor(sc2, 5, "mètre")
    exige(garde.any(), "tout a été écarté : il ne doit jamais rester rien")
    exige(pdf_3d.est_decor("CTX-MUR") and pdf_3d.est_decor("Végétation") and not pdf_3d.est_decor("FONDATION")
          and not pdf_3d.est_decor("SOLIVES") and not pdf_3d.est_decor("MURS-EXT") and pdf_3d.est_decor("Aménagement paysager")
          and pdf_3d.est_decor("Arbres lointains") and not pdf_3d.est_decor("Terrasse") and not pdf_3d.est_decor("Plancher"),
          "reconnaissance des noms de décor")


essai("arbre par collections : noms uniques, parents d'abord, objet du même nom qu'un groupe", t_arbre_collections)
essai("arbre par propriétés : assemblage, repère, boulon ; libellés et fiches ; « agent » écarté", t_arbre_proprietes)
essai("vues : trièdre indirect, tout le modèle dans le cadre, cadrage serré, dessus et face orientés", t_vues)
essai("décor : écarté seulement s'il écrase le modèle, jamais tout", t_decor)

shutil.rmtree(TRAVAIL, ignore_errors=True)
print("TOTAL : %d sur %d essai(s) passent ; %d échec(s)" % (passes, passes + len(echecs), len(echecs)))
sys.exit(1 if echecs else 0)
