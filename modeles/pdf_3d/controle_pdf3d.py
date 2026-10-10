# -*- coding: utf-8 -*-
"""controle_pdf3d.py — relit un PDF 3D et dit ce qui ne tient pas.

Trois regards INDÉPENDANTS des écrivains :
  1. le fichier brut : en-tête, table xref (chaque décalage tombe sur son objet), startxref, %%EOF ;
  2. PyMuPDF : le document s'ouvre sans réparation, une page, une annotation /Subtype /3D complète
     (/3DD, /3DV, /3DA, /AP), un flux /Type /3D /Subtype /U3D dont la longueur est la bonne, des
     vues bien formées, une apparence de repli qui n'est pas blanche, le texte attendu sur la page ;
  3. le U3D lui-même, relu par lire_u3d.py (écrit d'après la norme) : structure, références, boîte.
Puis les comptes et la boîte sont confrontés à ce que Blender a fourni (scene.json).

CE QUE CE CONTRÔLE NE PROUVE PAS : qu'un lecteur affiche le modèle. Voir voir_dans_lecteur.ps1.

    python controle_pdf3d.py fichier.pdf [--scene scene.json] [--attendu attendu.json]

Dans un script : lignes, echecs, mesures = controle_pdf3d.controler(pdf, scene, attendu)
"""
import json
import math
import os
import re
import sys

import numpy as np

sys.dont_write_bytecode = True          # pas de __pycache__ dans le dossier de l'outil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lire_u3d  # noqa: E402

MODES_RENDU = {"Solid", "SolidWireframe", "Transparent", "TransparentWireframe", "BoundingBox",
               "TransparentBoundingBox", "TransparentBoundingBoxOutline", "Wireframe",
               "ShadedWireframe", "HiddenWireframe", "Vertices", "ShadedVertices", "Illustration",
               "SolidOutline", "ShadedIllustration"}
ECLAIRAGES = {"Artwork", "None", "White", "Day", "Night", "Hard", "Primary", "Blue", "Red", "Cube",
              "CAD", "Headlamp"}


def _texte_pdf(valeur):
    """Décode une chaîne PDF rendue par PyMuPDF : « (…) » ou « <FEFF…> »."""
    v = valeur.strip()
    if v.startswith("<") and v.endswith(">") and not v.startswith("<<"):
        h = re.sub(r"\s+", "", v[1:-1])
        b = bytes.fromhex(h)
        if b.startswith(b"\xfe\xff"):
            return b[2:].decode("utf-16-be")
        return b.decode("latin-1")
    if v.startswith("(") and v.endswith(")"):
        s = v[1:-1]
        s = re.sub(r"\\([\\()])", r"\1", s)
        return s
    return v


def _nombres(valeur):
    return [float(x) for x in re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", valeur)]


def controle_brut(octets):
    """Le fichier, sans bibliothèque : en-tête, xref, startxref, fin."""
    ok, ko = [], []
    if octets[:7] == b"%PDF-1.":
        ok.append("en-tête %s" % octets[:8].decode("latin-1"))
    else:
        ko.append("le fichier ne commence pas par %PDF-1.x")
    if octets.rstrip(b"\r\n").endswith(b"%%EOF"):
        ok.append("fin de fichier %%EOF")
    else:
        ko.append("le fichier ne finit pas par %%EOF")
    m = list(re.finditer(rb"startxref\s+(\d+)\s+%%EOF", octets))
    if not m:
        ko.append("startxref introuvable")
        return ok, ko, {}
    pos = int(m[-1].group(1))
    if octets[pos:pos + 4] != b"xref":
        ko.append("startxref (%d) ne pointe pas sur la table xref" % pos)
        return ok, ko, {}
    t = re.match(rb"xref\s+0\s+(\d+)\s*\n", octets[pos:pos + 40])
    if not t:
        ko.append("en-tête de la table xref illisible")
        return ok, ko, {}
    n = int(t.group(1))
    debut = pos + t.end()
    mauvais = 0
    objets = {}
    for i in range(n):
        ligne = octets[debut + 20 * i: debut + 20 * i + 20]
        if len(ligne) < 20 or not re.match(rb"\d{10} \d{5} [nf][ \r][\r\n]", ligne):
            ko.append("entrée xref %d mal formée : %r" % (i, ligne))
            mauvais += 1
            continue
        if i == 0:
            if not ligne.startswith(b"0000000000 65535 f"):
                ko.append("l'entrée 0 de la table xref n'est pas l'entrée libre")
            continue
        p = int(ligne[:10])
        attendu = b"%d 0 obj" % i
        if octets[p:p + len(attendu)] != attendu:
            ko.append("xref : l'objet %d n'est pas à la position %d" % (i, p))
            mauvais += 1
        objets[i] = p
    if not mauvais:
        ok.append("table xref : %d objets, chaque décalage tombe sur son objet ; startxref = %d" % (n - 1, pos))
    queue = octets[debut + 20 * n: debut + 20 * n + 300]
    if b"/Root" not in queue or b"/Size %d" % n not in queue:
        ko.append("trailer sans /Root ou avec un /Size différent de %d" % n)
    return ok, ko, {"objets": n - 1, "startxref": pos}


def controler(chemin_pdf, scene=None, attendu=None):
    """Rend (lignes du rapport, liste des échecs, mesures)."""
    import fitz
    attendu = attendu or {}
    L, KO, M = [], [], {}

    def dire(ok, texte):
        L.append(("  OK    " if ok else "  ÉCHEC ") + texte)
        if not ok:
            KO.append(texte)

    with open(chemin_pdf, "rb") as f:
        octets = f.read()
    M["octets_pdf"] = len(octets)
    L.append("FICHIER %s — %d octets (%.2f Mo)" % (os.path.basename(chemin_pdf), len(octets), len(octets) / 1e6))

    # ------------------------------------------------------------ 1. brut
    L.append("1. Fichier brut")
    ok, ko, m1 = controle_brut(octets)
    for x in ok:
        dire(True, x)
    for x in ko:
        dire(False, x)
    M.update(m1)

    # ------------------------------------------------------------ 2. PyMuPDF
    L.append("2. Structure relue par PyMuPDF %s" % fitz.VersionBind)
    fitz.TOOLS.mupdf_warnings()
    doc = fitz.open(chemin_pdf)
    avert = fitz.TOOLS.mupdf_warnings()
    dire(not avert, "ouverture sans avertissement ni réparation" + (" : %s" % avert[:200] if avert else ""))
    dire(not doc.is_repaired, "document non réparé à l'ouverture")
    dire(doc.page_count == 1, "une page (trouvé : %d)" % doc.page_count)
    page = doc[0]
    M["page"] = [round(page.rect.width, 1), round(page.rect.height, 1)]
    dire(True, "page de %.0f × %.0f points (%.1f × %.1f mm)" % (page.rect.width, page.rect.height,
                                                                 page.rect.width / 72 * 25.4, page.rect.height / 72 * 25.4))
    # annotations 3D
    annots = []
    flux3d = []
    vues = []
    for x in range(1, doc.xref_length()):
        try:
            src = doc.xref_object(x, compressed=True)
        except Exception:
            continue
        if re.search(r"/Subtype\s*/3D\b", src) and re.search(r"/Type\s*/Annot\b", src):
            annots.append(x)
        if re.search(r"/Subtype\s*/U3D\b", src):
            flux3d.append(x)
        if re.search(r"/Type\s*/3DView\b", src):
            vues.append(x)
    dire(len(annots) == 1, "une annotation /Type /Annot /Subtype /3D (trouvé : %d)" % len(annots))
    dire(len(flux3d) == 1, "un flux /Subtype /U3D (trouvé : %d)" % len(flux3d))
    u3d = None
    if annots and flux3d:
        a = annots[0]
        s = flux3d[0]
        cle = doc.xref_get_key
        dire(cle(a, "3DD") == ("xref", "%d 0 R" % s), "/3DD de l'annotation pointe le flux 3D (objet %d)" % s)
        page_annots = cle(page.xref, "Annots")[1]
        dire(("%d 0 R" % a) in page_annots, "la page référence l'annotation dans /Annots")
        t3da = cle(a, "3DA")
        dire(t3da[0] == "dict" and "/A" in t3da[1], "/3DA présent avec /A (activation) : %s" % t3da[1].replace("\n", " ")[:90])
        rect = _nombres(cle(a, "Rect")[1])
        dire(len(rect) == 4 and rect[2] > rect[0] and rect[3] > rect[1], "/Rect valide : %s" % rect)
        M["rect"] = rect
        # apparence de repli
        ap = cle(a, "AP/N")
        okap = ap[0] == "xref"
        dire(okap, "/AP /N (apparence de repli) présent")
        if okap:
            xa = int(ap[1].split()[0])
            bbox = _nombres(cle(xa, "BBox")[1])
            dire(len(bbox) == 4 and abs(bbox[2] - (rect[2] - rect[0])) < 0.5 and abs(bbox[3] - (rect[3] - rect[1])) < 0.5,
                 "/BBox de l'apparence = taille du /Rect (%s)" % bbox)
            contenu = doc.xref_stream(xa) or b""
            dire(b"Tj" in contenu, "l'apparence de repli porte du texte (%d octets)" % len(contenu))
        # le flux 3D
        dire(cle(s, "Type")[1] == "/3D", "flux : /Type /3D")
        dire(doc.xref_is_stream(s), "l'objet %d est bien un flux" % s)
        brut = doc.xref_stream_raw(s)
        u3d = doc.xref_stream(s)
        longueur = int(_nombres(cle(s, "Length")[1])[0])
        filtre = cle(s, "Filter")[1]
        M["octets_u3d"] = len(u3d)
        M["octets_flux"] = len(brut)
        M["filtre"] = filtre if filtre != "null" else None
        dire(longueur == len(brut), "/Length (%d) = longueur réelle du flux (%d)%s"
             % (longueur, len(brut), "" if filtre == "null" else " ; filtre %s" % filtre))
        dire(u3d[:4] == b"\x55\x33\x44\x00", "le flux commence par l'en-tête U3D (55 33 44 00)")
        # positions exactes dans le fichier brut : « stream » … « endstream »
        mm = re.search(rb"%d 0 obj\b" % s, octets)
        if mm:
            d0 = octets.find(b"stream\n", mm.start()) + 7
            dire(octets[d0 + longueur: d0 + longueur + 10] == b"\nendstream", "le flux se termine exactement à « endstream »")
        # vues
        va = cle(s, "VA")
        nv = len(re.findall(r"\d+ 0 R", va[1])) if va[0] == "array" else 0
        dire(nv >= 1, "/VA liste %d vue(s)" % nv)
        dv = cle(s, "DV")
        v3 = cle(a, "3DV")
        refs_va = set(re.findall(r"(\d+) 0 R", va[1])) if va[0] == "array" else set()
        for nomcle, val in (("/DV du flux", dv), ("/3DV de l'annotation", v3)):
            if val[0] == "xref":
                dire(val[1].split()[0] in refs_va, "%s désigne une vue de /VA (%s)" % (nomcle, val[1]))
            elif val[0] in ("int", "string", "name"):
                dire(True, "%s = %s" % (nomcle, val[1]))
            else:
                dire(False, "%s absent ou d'un type inattendu (%s)" % (nomcle, val[0]))
        M["vues"] = []
        for xv in [int(x) for x in re.findall(r"(\d+) 0 R", va[1])] if va[0] == "array" else []:
            nom = _texte_pdf(cle(xv, "XN")[1])
            d = {"nom": nom, "objet": xv}
            ms = cle(xv, "MS")[1]
            proj = cle(xv, "P/Subtype")[1]
            soucis = []
            if cle(xv, "Type")[1] != "/3DView":
                soucis.append("/Type n'est pas /3DView")
            if cle(xv, "XN")[0] != "string":
                soucis.append("/XN absent")
            if proj not in ("/P", "/O"):
                soucis.append("/P /Subtype = %s (attendu /P ou /O)" % proj)
            if proj == "/P":
                fov = _nombres(cle(xv, "P/FOV")[1])
                if not fov or not 0 < fov[0] < 180:
                    soucis.append("/FOV absent ou hors de ]0, 180[")
                d["fov"] = fov[0] if fov else None
            if ms == "/M":
                c2w = _nombres(cle(xv, "C2W")[1])
                if len(c2w) != 12 or not all(math.isfinite(x) for x in c2w):
                    soucis.append("/C2W n'a pas 12 nombres finis")
                else:
                    R = np.array(c2w[:9]).reshape(3, 3)
                    if not np.allclose(R @ R.T, np.eye(3), atol=1e-3):
                        soucis.append("/C2W : les axes de la caméra ne sont pas orthonormés")
                    det = float(np.linalg.det(R))
                    d["determinant"] = round(det, 4)
                    d["position"] = c2w[9:]
                    d["regard"] = [round(x, 4) for x in c2w[6:9]]
                    d["haut"] = [round(x, 4) for x in c2w[3:6]]
                    # ISO 32000-1 13.6.5 : la caméra regarde vers +z, x à droite, y en haut :
                    # dans un monde direct, (droite, haut, regard) est un trièdre INDIRECT
                    if det > 0:
                        soucis.append("/C2W : trièdre direct (image en miroir) ; attendu indirect, déterminant -1")
                co = _nombres(cle(xv, "CO")[1]) if cle(xv, "CO")[0] != "null" else []
                if not co or co[0] <= 0:
                    soucis.append("/CO absent ou non positif")
                d["co"] = co[0] if co else None
            elif ms == "/U3D":
                if cle(xv, "U3DPath")[0] == "null":
                    soucis.append("/MS /U3D sans /U3DPath")
            rm = cle(xv, "RM/Subtype")[1]
            if rm != "null" and rm.lstrip("/") not in MODES_RENDU:
                soucis.append("mode de rendu %s inconnu de la norme" % rm)
            ls = cle(xv, "LS/Subtype")[1]
            if ls != "null" and ls.lstrip("/") not in ECLAIRAGES:
                soucis.append("éclairage %s inconnu de la norme" % ls)
            d["rendu"] = rm.lstrip("/") if rm != "null" else None
            d["eclairage"] = ls.lstrip("/") if ls != "null" else None
            bg = cle(xv, "BG/C")
            d["fond"] = _nombres(bg[1]) if bg[0] == "array" else None
            na = cle(xv, "NA")
            d["noeuds"] = None
            if na[0] in ("array", "xref"):
                src = doc.xref_object(int(na[1].split()[0]), compressed=True) if na[0] == "xref" else na[1]
                noms = [_texte_pdf(x) for x in re.findall(r"/N\s*(\((?:[^()\\]|\\.)*\)|<[0-9A-Fa-f\s]*>)", src)]
                d["noeuds"] = noms
            d["soucis"] = soucis
            M["vues"].append(d)
            dire(not soucis, "vue « %s »%s%s" % (nom, " : " if soucis else "", " ; ".join(soucis))
                 if soucis else "vue « %s » : %s%s%s" % (
                     nom, "caméra explicite" if ms == "/M" else "cadrage laissé au lecteur",
                     ", %s" % ("perspective" if proj == "/P" else "orthographique"),
                     (", %d nœud(s) réglé(s)" % len(d["noeuds"])) if d["noeuds"] else ""))
    # texte de la page
    texte = page.get_text("text")
    M["texte_page"] = texte

    def aplati(s):
        # espaces insécables, fines, retours : tout devient une espace simple (l'extraction de
        # texte ne garde pas ces nuances, la comparaison ne doit pas en dépendre)
        return re.sub(r"\s+", " ", s.replace("\u00a0", " ").replace("\u202f", " ")).strip()

    texte_aplati = aplati(texte)
    for attendu_txt in attendu.get("textes", []):
        dire(aplati(attendu_txt) in texte_aplati,
             "la page porte le texte « %s »" % (attendu_txt if len(attendu_txt) < 90 else attendu_txt[:87] + "..."))
    # apparence de repli : ce que montre un lecteur SANS 3D (PyMuPDF n'en a pas)
    if M.get("rect"):
        pm = page.get_pixmap(dpi=50, alpha=False)
        img = np.frombuffer(pm.samples, dtype=np.uint8).reshape(pm.height, pm.width, pm.n)[:, :, :3]
        r_ = M["rect"]
        k = 50 / 72.0
        x0, x1 = int(r_[0] * k) + 2, int(r_[2] * k) - 2
        y0, y1 = int((page.rect.height - r_[3]) * k) + 2, int((page.rect.height - r_[1]) * k) - 2
        zone = img[y0:y1, x0:x1].astype(int)
        fond = np.median(zone.reshape(-1, 3), axis=0)
        ecart = (np.abs(zone - fond).sum(axis=2) > 60).mean() * 100
        M["repli_pixels_differents_pct"] = round(float(ecart), 3)
        dire(ecart > 0.3, "sans moteur 3D, le cadre montre un message et non du vide : %.2f %% de pixels écrits" % ecart)

    # propriétés du document (dictionnaire /Info, flux XMP) : ce que montre « Fichier > Propriétés »
    NOMS_PROP = (("title", "titre", "Titre"), ("author", "auteur", "Auteur"), ("subject", "sujet", "Sujet"),
                 ("keywords", None, "Mots-clés"), ("creator", None, "Créé par"), ("producer", None, "Producteur"),
                 ("creationDate", None, "Date de création"), ("modDate", None, "Date de modification"),
                 ("trapped", None, "Trapped"))
    meta = doc.metadata or {}
    xmp = doc.get_xml_metadata() or ""
    lues = {cle: str(meta.get(cle) or "") for cle, _, _ in NOMS_PROP}
    M["proprietes"] = {k: v for k, v in lues.items() if v}
    M["xmp"] = xmp
    resume_prop = " ; ".join("%s « %s »" % (etq, lues[cle] if len(lues[cle]) < 110 else lues[cle][:107] + "...")
                            for cle, _, etq in NOMS_PROP if lues[cle]) or "aucune"
    att_prop = attendu.get("proprietes")
    if att_prop is None:
        L.append("          propriétés du document : %s%s" % (resume_prop, "" if not xmp else " ; flux XMP de %d caractères" % len(xmp)))
    else:
        voulues = {cle: str(att_prop.get(nom) or "") if nom else "" for cle, nom, _ in NOMS_PROP}
        ecarts_prop = ["%s : lu « %s », voulu « %s »" % (etq, lues[cle][:60], voulues[cle][:60])
                       for cle, _, etq in NOMS_PROP if lues[cle] != voulues[cle]]
        dire(not ecarts_prop and not xmp,
             "propriétés du document : %s — celles voulues, et aucune autre (ni outil, ni date, ni flux XMP)%s"
             % (resume_prop, "" if not (ecarts_prop or xmp) else " — ÉCARTS : %s%s" % (
                 " | ".join(ecarts_prop[:4]), " ; flux XMP présent" if xmp else "")))

    # ------------------------------------------------------------ 2 bis. un second lecteur de PDF
    try:
        import io
        import logging
        import pypdf
        journal = io.StringIO()
        prise = logging.StreamHandler(journal)
        logging.getLogger("pypdf").addHandler(prise)
        try:
            lecteur = pypdf.PdfReader(chemin_pdf, strict=True)
            pg = lecteur.pages[0]
            a3 = [x.get_object() for x in (pg.get("/Annots") or [])]
            a3 = [x for x in a3 if x.get("/Subtype") == "/3D"]
            flux = a3[0]["/3DD"].get_object() if a3 else None
            octets2 = flux.get_data() if flux is not None else b""
            vues2 = [v.get_object().get("/XN") for v in (flux.get("/VA") or [])] if flux is not None else []
            info2 = lecteur.metadata or {}
            prop2 = {cle: str(info2.get(nom) or "") for cle, nom in (("title", "/Title"), ("author", "/Author"),
                                                                        ("subject", "/Subject"))}
            autres2 = sorted(str(k) for k in info2 if str(k) not in ("/Title", "/Author", "/Subject"))
        finally:
            logging.getLogger("pypdf").removeHandler(prise)
        plaintes = journal.getvalue().strip()
        L.append("2 bis. Recoupement par un second lecteur de PDF (pypdf %s, mode strict)" % pypdf.__version__)
        dire(not plaintes, "lecture stricte sans avertissement" + ("" if not plaintes else " : %s" % plaintes[:160]))
        dire(len(a3) == 1 and flux is not None and flux.get("/Subtype") == "/U3D",
             "il trouve lui aussi une annotation 3D et son flux /U3D")
        dire(u3d is not None and bytes(octets2) == bytes(u3d),
             "il rend le même U3D que PyMuPDF, octet pour octet (%d octets)" % len(octets2))
        dire([str(x) for x in vues2] == [v["nom"] for v in M.get("vues", [])],
             "il lit les mêmes noms de vues (%d)" % len(vues2))
        dire(prop2 == {k: lues[k] for k in prop2} and not autres2,
             "il lit les mêmes propriétés du document (titre, auteur, sujet), et aucune autre%s"
             % ("" if not autres2 else " — en trop : %s" % autres2))
    except ImportError:
        L.append("2 bis. (pypdf absent : pas de recoupement par un second lecteur de PDF)")
    except Exception as ex:
        L.append("2 bis. Recoupement par un second lecteur de PDF (pypdf)")
        dire(False, "pypdf n'a pas pu lire le fichier : %s" % str(ex)[:200])

    # ------------------------------------------------------------ 3. le U3D
    L.append("3. Le U3D relu par le lecteur à part (lire_u3d.py, écrit d'après ECMA-363)")
    R = None
    if u3d is not None:
        R = lire_u3d.lire(u3d)
        e = R["entete"] or {}
        dire(e.get("taille_fichier") == len(u3d), "longueur du flux 3D (%d) = taille que le U3D annonce (%s)"
             % (len(u3d), e.get("taille_fichier")))
        dire(e.get("taille_declarations") == R.get("fin_declarations_mesuree"),
             "taille des déclarations annoncée (%s) = en-tête + blocs de déclaration mesurés (%s)"
             % (e.get("taille_declarations"), R.get("fin_declarations_mesuree")))
        sans_c = bool(e.get("profil", 0) & 0x4)
        voulu_c = attendu.get("compresse")
        dire(voulu_c is None or voulu_c == (not sans_c), "profil 0x%X : %s%s%s" % (
            e.get("profil", 0),
            "SANS compression (la forme qu'écrit l'ERP)" if sans_c else
            "COMPRESSÉ (codage arithmétique de la norme, chap. 10 ; faces décodées par le lecteur à part)",
            ", unités définies (%.6g m par unité)" % e["echelle"] if e.get("echelle") else "",
            "" if voulu_c is None or voulu_c == (not sans_c) else " — ATTENDU : %s" % ("compressé" if voulu_c else "sans compression")))
        dire(not R["anomalies"], "structure, alignement sur 4 octets, tailles, références et indices : %d anomalie(s)"
             % len(R["anomalies"]))
        for x in R["anomalies"][:25]:
            L.append("          - " + x)
        for x in R["remarques"][:8]:
            L.append("          remarque : " + x)
        c = R.get("comptes") or {}
        M["u3d"] = {"comptes": c, "boite": R.get("boite"), "types": R["types"], "entete": e}
        L.append("          blocs : " + ", ".join("%s × %d" % kv for kv in sorted(R["types"].items())))
        if c:
            L.append("          nœuds %d (groupes %d, modèles %d, profondeur %d) ; ressources %d ; nuanceurs %d ; matériaux %d"
                     % (c["noeuds"], c["groupes"], c["modeles"], c["profondeur"], c["ressources"], c["nuanceurs"], c["materiaux"]))
            L.append("          triangles : %d posés, %d dans les ressources ; sommets des ressources : %d"
                     % (c["triangles_poses"], c["triangles_ressources"], c["sommets_ressources"]))
        # vues : les nœuds nommés existent-ils dans le U3D ?
        for v in M.get("vues", []):
            if v.get("noeuds"):
                absents = [n for n in v["noeuds"] if n not in R["noeuds"]]
                dire(not absents, "vue « %s » : ses %d nœuds existent tous dans le U3D%s"
                     % (v["nom"], len(v["noeuds"]), "" if not absents else " — absents : %s" % absents[:5]))
    else:
        dire(False, "aucun flux U3D à relire")

    # ------------------------------------------------------------ 4. face à Blender
    if scene is not None and R is not None and R.get("comptes"):
        L.append("4. Le fichier face à ce que Blender a fourni")
        c = R["comptes"]
        tri_blender = int(scene["triangles"])
        mode = attendu.get("mode")
        if mode == "simple":
            ecart = tri_blender - c["triangles_poses"]
            tol = attendu.get("tolerance_faces_ecartees", 0.002)
            dire(0 <= ecart <= max(2, tri_blender * tol),
                 "faces du fichier : %d ; triangles fournis par Blender : %d ; écart %d (triangles devenus "
                 "dégénérés après la fusion des sommets à 0,01 mm par l'écrivain de l'ERP)"
                 % (c["triangles_poses"], tri_blender, ecart))
            dire(c["modeles"] == 1 and c["ressources"] == 1 and c["materiaux"] == 0,
                 "un seul nœud, une seule ressource, aucun matériau (comme l'ERP le fait)")
        else:
            dire(c["triangles_poses"] == tri_blender, "triangles posés : %d dans le fichier, %d fournis par Blender"
                 % (c["triangles_poses"], tri_blender))
            dire(c["modeles"] == len(scene["objets"]), "nœuds de modèle : %d ; objets de Blender : %d"
                 % (c["modeles"], len(scene["objets"])))
            employes = len({o["maillage"] for o in scene["objets"]})
            dire(c["ressources"] == employes, "ressources de maillage : %d ; maillages distincts de Blender : %d"
                 % (c["ressources"], employes))
            dire(c["triangles_ressources"] == int(scene["triangles_distincts"]),
                 "triangles des ressources : %d ; des maillages distincts de Blender : %d"
                 % (c["triangles_ressources"], int(scene["triangles_distincts"])))
            dire(c["modeles_poses"] == c["modeles"], "chaque nœud de modèle est relié au monde une seule fois (%d poses)"
                 % c["modeles_poses"])
            if attendu.get("noeuds") is not None:
                att = attendu["noeuds"]            # nom -> {parent, type, ressource, nuanceurs}
                manque = [n for n in att if n not in R["noeuds"]]
                trop = [n for n in R["noeuds"] if n not in att]
                dire(not manque and not trop, "les %d nœuds attendus y sont, et eux seuls%s"
                     % (len(att), "" if not (manque or trop) else " — manquants %s ; en trop %s" % (manque[:4], trop[:4])))
                faux = []
                for n, a_ in att.items():
                    d = R["noeuds"].get(n)
                    if d is None:
                        continue
                    if [p for p, _ in d["parents"]] != [a_["parent"]]:
                        faux.append("%s : parent %s" % (n, [p for p, _ in d["parents"]]))
                    elif a_["type"] != d["type"]:
                        faux.append("%s : type %s" % (n, d["type"]))
                    elif a_["type"] == "modele" and (d["ressource"] != a_["ressource"]
                                                     or (d["nuanceurs"] or []) != [[s] for s in a_["nuanceurs"]]):
                        faux.append("%s : ressource ou nuanceurs" % n)
                dire(not faux, "parent, type, ressource et nuanceurs de chaque nœud conformes à l'arbre voulu%s"
                     % ("" if not faux else " — %d écart(s) : %s" % (len(faux), faux[:3])))
            if attendu.get("materiaux") is not None:
                att = attendu["materiaux"]
                ecarts = []
                for nom, m in att.items():
                    d = R["materiaux"].get(nom)
                    if d is None:
                        ecarts.append("%s absent" % nom)
                    elif max(abs(a_ - b_) for a_, b_ in zip(d["diffus"], m["diffus"])) > 2e-4 or abs(d["opacite"] - m["opacite"]) > 2e-4:
                        ecarts.append("%s : diffus %s, opacité %s" % (nom, d["diffus"], d["opacite"]))
                dire(not ecarts and len(R["materiaux"]) == len(att),
                     "matériaux : %d, couleurs diffuses et opacités conformes%s"
                     % (len(R["materiaux"]), "" if not ecarts else " — %s" % ecarts[:3]))
        # boîte englobante
        if scene.get("boite") and R.get("boite"):
            a_ = np.array(scene["boite"])
            b_ = np.array(R["boite"])
            taille = float(np.linalg.norm(a_[1] - a_[0])) or 1.0
            ecart = float(np.abs(a_ - b_).max())
            unite = attendu.get("unite_nom", "unité")
            dire(ecart <= max(2e-5 * taille, 1e-5 * max(1.0, np.abs(a_).max())) + 1.5e-5,
                 "boîte englobante du U3D = celle du modèle Blender à %.2g %s près : X %.4f à %.4f, Y %.4f à %.4f, Z %.4f à %.4f"
                 % (ecart, unite, b_[0][0], b_[1][0], b_[0][1], b_[1][1], b_[0][2], b_[1][2]))
            M["boite_blender"] = scene["boite"]
            M["ecart_boite"] = ecart
    # ------------------------------------------------------------ 5. interdits
    interdits = attendu.get("interdits") or []
    if interdits:
        L.append("5. Aucun terme interne dans le PDF (texte de la page, propriétés du document, vues, noms et "
                 "fiches du U3D)")
        corpus = [M.get("texte_page", "")]
        corpus += list(M.get("proprietes", {}).values()) + [M.get("xmp", "")]
        corpus += [v["nom"] for v in M.get("vues", [])]
        if R is not None:
            corpus += list(R["noeuds"]) + list(R["ressources"]) + list(R["materiaux"]) + list(R["nuanceurs"])
            for d in R["noeuds"].values():
                corpus += ["%s=%s" % kv for kv in d["meta"].items() if isinstance(kv[1], str)]
        gros = "\n".join(corpus).lower()
        trouves = [t for t in interdits if t.lower() in gros]
        dire(not trouves, "%d terme(s) cherché(s) sans tenir compte de la casse, %d trouvé(s)%s"
             % (len(interdits), len(trouves), "" if not trouves else " : %s" % trouves))
    doc.close()
    return L, KO, M


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        sys.exit(2)
    sc = at = None
    if "--scene" in sys.argv:
        with open(sys.argv[sys.argv.index("--scene") + 1], encoding="utf-8") as f:
            sc = json.load(f)
    if "--attendu" in sys.argv:
        with open(sys.argv[sys.argv.index("--attendu") + 1], encoding="utf-8") as f:
            at = json.load(f)
    lignes, echecs, _ = controler(args[0], sc, at)
    print("\n".join(lignes))
    print("CONTRÔLE : %d échec(s)" % len(echecs))
    sys.exit(1 if echecs else 0)
