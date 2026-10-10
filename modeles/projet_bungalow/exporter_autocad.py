# -*- coding: utf-8 -*-
"""
Maison Bungalow — DWG 3D (discipline A, maquette 3D) : DXF 2018 + DWG par ODA File Converter
====================================================================================================
MODÈLE tiré de Maison_Bungalow_Blender\\exporter_autocad.py (version finale du 2026-09-25, gel F4 ;
voir modeles\\LISEZMOI.md). Blender et ODA File Converter sont trouvés par outils\\chemins.py (copies portables du
poste d'abord) : aucun chemin écrit en dur. Pour un nouveau projet : remplacer « bungalow » par le nom du projet
(BUILD, empreinte_<projet>, noms de sortie), et les calques par ceux du build.
Adapté à l'origine de Maison_Agrandissement_Blender\\exporter_autocad.py.

Utilisation (Python du poste, outils\\python, avec ezdxf) :
    python exporter_autocad.py              EXPORT FINAL depuis la copie figée sources_figees\\ (empreinte_bungalow)
    python exporter_autocad.py --figer      fige d'abord les sources (figer_sources du chef : 2 min de calme), puis exporte
    python exporter_autocad.py --essai      ESSAI sur les fichiers VIVANTS : instantané copié dans %TEMP%, sorties dans
                                            dwg\\essais\\ (bungalow_3d_essai.*), marqué ESSAI dans les propriétés
    options : --build <chemin>   autre script de modèle (essai seulement) ; --sans-rendu ; --sans-dwg ; --sans-contacts ;
              --angle-pli 30     arête VIVE au-delà de cet angle (sommets dédoublés) ; 180 = tout soudé (avant 2026-09-28)

Sorties (dossier dwg\\) : bungalow_3d.dxf et .dwg (R2018), apercu_3d_*.png (Cycles CPU), controle_3d.txt.
Un fichier ouvert dans une application, ou modifié après la dernière génération, n'est jamais écrasé : _v2, _v3...

0. SOURCES : empreinte COMMUNE aux 3 DWG (plans 2D, 3D, métré) = empreinte_bungalow.empreinte_sources() (module du
   chef, importé, jamais recopié) sur build_bungalow.py + parametres_bungalow.py + releve_*.py. L'export final part de
   la copie figée sources_figees\\ ; l'empreinte est revérifiée à la fin (copie figée ET fichiers vivants).
1. BLENDER (arrière-plan, CPU SEULEMENT) exécute le build depuis la copie, exclut CONTEXTE (et CAMERAS, LUMIERES,
   TERRAIN s'ils existent) du calque de vue AVANT evaluated_depsgraph_get, puis extrait la géométrie évaluée
   (modificateurs appliqués) en coordonnées monde : sommets confondus soudés, n-gones de plus de 4 côtés triangulés,
   faces d'aire nulle retirées, un groupe par (objet, matériau). Unités du modèle DÉTECTÉES sur l'étendue du bâtiment
   (47 pi de long : 14,3 m si le modèle est en mètres, 47 s'il est en pieds) et vérifiées contre scene.unit_settings.
   ARÊTES VIVES (2026-09-28, d'après l'escalier flottant) : les sommets sont DÉDOUBLÉS le long des arêtes dont les 2
   faces font plus de ANGLE_PLI (30° ; option --angle-pli, 180 = tout soudé comme avant) et des arêtes à plus de 2
   faces. Un MESH ne porte pas de normales : le visualiseur de l'ERP (module CAD) les calcule en moyennant TOUTES les
   faces d'un sommet, sans angle de pli, et une boîte soudée s'y arrondit « en coussin ». Géométrie inchangée
   (positions, faces, ordre) ; seuls les indices de sommets diffèrent.
2. EZDXF : un MESH par groupe, UN CALQUE PAR COLLECTION (FONDATION, DALLE, MURS-EXT, MURS-INT, OUVERTURES, VITRAGE,
   MENUISERIE, TOIT, ESCALIERS, MOBILIER, INDICATIF), couleur vraie du matériau (Base Color du Principled, sinon couleur
   d'affichage), nom de l'objet et du matériau en XDATA, pouces ($INSUNITS=1, $LUNITS=4), vue d'ouverture
   isométrique OMBRÉE (visual_style_handle), étendues dans msp.dxf.extmin/extmax, empreinte dans les propriétés.
   INDICATIF (couleur neutre 252) : ce que le modèle ajoute et que le plan ne prévoit pas (finis de plancher, dalle
   « supposée » de la chambre froide, charpente du patio...) ; calque distinct, jamais mêlé aux calques de construction.
   Transparence d'entité (code 440, gardée par ODA, appliquée par le visualiseur de l'ERP) = 1 − alpha d'affichage du
   matériau ; un verre (« verre », « vitr », « glass ») reste entre 0,60 et 0,80, et reçoit TRANSPARENCE_VERRE (0,65)
   si son alpha d'affichage est resté à 1 (ici, Vitrage et Verre intérieur à l'alpha 0,6 : 0,60). Matériau « Global »
   mis « par objet » comme celui d'AutoCAD (ezdxf l'écrit avec un diffus IMPOSÉ BLANC : modèle gris dans l'ERP).
3. CONTRÔLES : audit (0 erreur exigée) ; relecture ODA ; comptes par calque ; taille (12 Mo au plus) ; pièces hors de
   l'enveloppe du bâtiment ; pièces FLOTTANTES (graphe des contacts entre les MESH RELUS du DWG, RESSOUDÉS PAR POSITION
   dans l'OBJ de contrôle puisque les arêtes vives les découpent, dans Blender, à 1/2" près ; « posé au sol » = dessous
   au plus 3" au-dessus du sol fini), l'INDICATIF compris, puisqu'il porte des pièces
   (la charpente du patio porte les rampes) ; CONTRE-ESSAI sans le calque INDICATIF : les pièces de construction qui
   décrochent alors ne tiennent que par de l'indicatif (signalées, à faire valider) ; aperçus Cycles CPU (aucun GPU).
"""
import glob
import hashlib
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
from collections import Counter, defaultdict

import ezdxf
from ezdxf import bbox as ezbbox

sys.dont_write_bytecode = True                         # aucun __pycache__ chez les autres agents
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import empreinte_bungalow as EMP  # noqa: E402  (module du chef : empreinte_sources, figer_sources, SOURCES_FIGEES)


def _chemins():
    """Module outils\\chemins.py du poste portable, trouvé sans chemin écrit en dur :
    1. la variable BM_RACINE ; 2. en remontant depuis ce script, puis depuis l'interpréteur (le Python
    portable est DANS la racine) ; 3. un dossier « blender-main » rencontré en remontant (projets voisins)."""
    import importlib.util
    deja = sys.modules.get("chemins")
    if deja is not None and hasattr(deja, "blender_exe"):
        return deja
    candidats = []
    if os.environ.get("BM_RACINE"):
        r = os.environ["BM_RACINE"]
        if not os.path.isfile(os.path.join(r, "outils", "chemins.py")):
            raise SystemExit("BM_RACINE = %s ne contient pas outils\\chemins.py" % r)
        candidats.append(r)
    for depart in (os.path.dirname(os.path.abspath(__file__)), os.path.dirname(os.path.abspath(sys.executable))):
        d = depart
        while True:
            candidats += [d, os.path.join(d, "blender-main")]
            parent = os.path.dirname(d)
            if parent == d:
                break
            d = parent
    for c in candidats:
        f = os.path.join(c, "outils", "chemins.py")
        if os.path.isfile(f):
            spec = importlib.util.spec_from_file_location("chemins", f)
            mod = importlib.util.module_from_spec(spec)
            sys.modules["chemins"] = mod
            spec.loader.exec_module(mod)
            return mod
    raise SystemExit("outils\\chemins.py introuvable : définir BM_RACINE (le dossier qui contient outils\\).")


DWG_DIR = os.path.join(HERE, "dwg")
_CH = _chemins()
BLENDER = _CH.blender_exe()                            # copie portable du poste (outils\blender) d'abord
# Environnement de la copie portable de Blender (ressources système, cache CUDA, BLENDER_USER_* retirées)
ENV_BLENDER = _CH.env_blender() if callable(getattr(_CH, "env_blender", None)) else None
BUILD = "build_bungalow.py"
SOUDURE_M = 1e-5                                       # m : sommets confondus soudés (converti selon l'unité du modèle)
ANGLE_PLI = float(sys.argv[sys.argv.index("--angle-pli") + 1]) if "--angle-pli" in sys.argv else 30.0   # degrés
TRANSPARENCE_VERRE = 0.65                              # verre dont l'alpha d'affichage est resté à 1
VERRE_BORNES = (0.60, 0.80)                            # un verre reste de 60 à 80 % transparent
TRANSPARENCE_MAX = 0.90                                # autre matériau transparent : jamais invisible
MOTIF_VERRE = re.compile(r"verre|vitr|glass", re.I)    # noms de matériaux de verre
TAILLE_MAX_MO = 12.0
EXCLURE = ["CONTEXTE", "CAMERAS", "LUMIERES", "TERRAIN"]
LAYERS = {   # calque : (couleur ACI, description) — noms des collections de build_bungalow.py
    "FONDATION": (253, "Murs de fondation, semelles, sonotubes, chambre froide"),
    "DALLE": (8, "Dalles (sous-sol, garage, perron, patio) et planchers"),
    "MURS-EXT": (7, "Murs exterieurs et revetements (Isoroc, Vicwest Bellara, metallique MAC)"),
    "MURS-INT": (8, "Cloisons et portes interieures"),
    "OUVERTURES": (3, "Portes et fenetres : cadres, chassis, vantaux, porte de garage, impostes"),
    "VITRAGE": (140, "Vitrages des fenetres et des portes"),
    "MENUISERIE": (32, "Moulures, appuis, seuils, fascias, soffites, garde-corps de bois"),
    "TOIT": (9, "Toitures en tole d'acier (A, B, C, D), faitieres, cheminee au-dessus du toit"),
    "ESCALIERS": (7, "Escaliers interieur et exterieurs, perron, patio, garde-corps"),
    "MOBILIER": (8, "Appareils, electromenagers, armoires et mobilier (indicatif)"),
    "INDICATIF": (252, "Indicatif, non prévu au plan"),
    "FENETRES-PRES": (8, "Fenetres de presentation (non imprimees)"),
}
CALQUE_INDICATIF = "INDICATIF"                          # exporté, mais retiré au contre-essai des contacts
APPID = "BUNGALOW"
PIED_M = 0.3048


def log(*a):
    print(*a, flush=True)


def sha(path, n=None):
    with open(path, "rb") as fh:
        h = hashlib.sha256(fh.read()).hexdigest()
    return h[:n] if n else h


# ============================================================================ 0. sources
def instantane_vivant(build_autre=None):
    """Essai : copie des fichiers VIVANTS (build, paramètres, relevés) dans %TEMP% ; rien n'est écrit dans le projet."""
    dest = os.path.join(tempfile.gettempdir(), "bungalow_dwg3d_essai_sources")
    os.makedirs(dest, exist_ok=True)
    for f in glob.glob(os.path.join(dest, "*")):
        if os.path.isfile(f):
            os.remove(f)
    for f in EMP.fichiers_sources(HERE):
        shutil.copy2(f, dest)
    if build_autre:
        shutil.copy2(build_autre, os.path.join(dest, BUILD))
    return dest


def importer_parametres(dossier):
    """Importe parametres_bungalow (et ses releve_*) DEPUIS le dossier de sources choisi."""
    sys.path.insert(0, dossier)
    for n in [n for n in list(sys.modules) if n.startswith(("parametres_", "releve_"))]:
        del sys.modules[n]
    import parametres_bungalow as P  # noqa: E402
    if os.path.normcase(os.path.dirname(os.path.abspath(P.__file__))) != os.path.normcase(os.path.abspath(dossier)):
        raise SystemExit(f"parametres_bungalow importé ailleurs que dans {dossier} : {P.__file__}")
    return P


# ============================================================================ 1. partie Blender
BLENDER_EXTRACTION = r'''
import bpy, bmesh, json, math, os, sys, time
from mathutils import Vector
sys.dont_write_bytecode = True
t0 = time.time()
args = sys.argv[sys.argv.index("--") + 1:]
src, out, opts = args[0], args[1], json.loads(args[2])
sys.path.insert(0, os.path.dirname(src))
os.chdir(os.path.dirname(src))
sys.argv = [src, "--"] + opts["args_build"]
g = {"__name__": "__main__", "__file__": src}
exec(compile(open(src, encoding="utf-8").read(), src, "exec"), g)
t_build = time.time() - t0
exclure = set(opts["exclure"])
vl = bpy.context.view_layer
for lc in vl.layer_collection.children:
    if lc.name in exclure:
        lc.exclude = True                      # AVANT evaluated_depsgraph_get : jamais évaluées
parent = {}
for c in bpy.data.collections:
    for ch in c.children:
        parent[ch.name] = c.name
racines = [lc.name for lc in vl.layer_collection.children]
def calque(ob):
    for c in ob.users_collection:
        n = c.name
        while n is not None:
            if n in racines:
                return n
            n = parent.get(n)
    return None
def srgb(c):
    c = max(0.0, min(1.0, c))
    return c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
def couleur(mat):
    if mat is None:
        return None, "aucun matériau"
    nt = getattr(mat, "node_tree", None)
    if nt is not None:
        for n in nt.nodes:
            if n.type == "BSDF_PRINCIPLED":
                s = n.inputs.get("Base Color")
                if s is not None and not s.is_linked:
                    return [int(round(srgb(v) * 255)) for v in s.default_value[:3]], "Base Color (Principled)"
                break
    return [int(round(srgb(v) * 255)) for v in mat.diffuse_color[:3]], "couleur d'affichage"
par_coll, objets = {}, []
ignores = {"caches": 0, "exclus": 0, "types": 0, "sans_collection": 0}
for ob in bpy.data.objects:
    lay = calque(ob)
    par_coll[lay or "?"] = par_coll.get(lay or "?", 0) + 1
    if ob.type not in ("MESH", "FONT", "CURVE", "SURFACE", "META"):
        ignores["types"] += 1
        continue
    if lay is None:
        ignores["sans_collection"] += 1
        continue
    if lay in exclure:
        ignores["exclus"] += 1
        continue
    if ob.hide_render:
        ignores["caches"] += 1
        continue
    objets.append((ob, lay))
vl.update()
dg = bpy.context.evaluated_depsgraph_get()
# unités : étendue du bâtiment (objets exportés) dans l'unité de Blender
mn = [1e30] * 3
mx = [-1e30] * 3
for ob, lay in objets:
    for v in ob.evaluated_get(dg).bound_box:
        w = ob.matrix_world @ Vector(v)
        for k in range(3):
            mn[k] = min(mn[k], w[k]); mx[k] = max(mx[k], w[k])
us = bpy.context.scene.unit_settings
grand = max(mx[0] - mn[0], mx[1] - mn[1])       # le bâtiment fait 47 pi de long (sans les débords)
unite = "pi" if 35.0 <= grand <= 90.0 else ("m" if 10.0 <= grand <= 28.0 else "?")
soudure = opts["soudure_m"] / (opts["pied_m"] if unite == "pi" else 1.0)
parts, soudes, mats_vus, alphas = [], [], {}, {}
n_tri = n_nulles = 0
pli = math.radians(opts["angle_pli"])
vives = {"objets": 0, "aretes": 0, "non_manifold": 0, "sommets_avant": 0, "sommets_apres": 0}
for ob, lay in objets:
    ev = ob.evaluated_get(dg)
    mats = [s.material for s in ob.material_slots]
    me = bpy.data.meshes.new_from_object(ev)
    if not mats:
        mats = list(me.materials)
    me.transform(ob.matrix_world)
    bm = bmesh.new()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    if not bm.faces:
        bm.free()
        continue
    n_av = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=soudure)
    if len(bm.verts) < n_av:
        soudes.append([ob.name, n_av, len(bm.verts)])
    ngons = [f for f in bm.faces if len(f.verts) > 4]
    if ngons:
        n_tri += len(ngons)
        bmesh.ops.triangulate(bm, faces=ngons, quad_method="BEAUTY", ngon_method="BEAUTY")
    nulles = [f for f in bm.faces if f.calc_area() < 1e-12]
    if nulles:
        n_nulles += len(nulles)
        bmesh.ops.delete(bm, geom=nulles, context="FACES_ONLY")
    # Arêtes VIVES : sommets dédoublés (le visualiseur de l'ERP moyenne les normales de toutes les faces d'un sommet,
    # sans angle de pli). Vive = angle entre les 2 faces > angle_pli, ou plus de 2 faces sur l'arête.
    if opts["angle_pli"] < 180.0:
        bm.normal_update()
        a_couper, nm = [], 0
        for e in bm.edges:
            lf = e.link_faces
            if len(lf) > 2:
                a_couper.append(e)
                nm += 1
            elif len(lf) == 2 and lf[0].normal.angle(lf[1].normal, 0.0) > pli:
                a_couper.append(e)
        if a_couper:
            n_av = len(bm.verts)
            bmesh.ops.split_edges(bm, edges=a_couper)
            vives["objets"] += 1
            vives["aretes"] += len(a_couper)
            vives["non_manifold"] += nm
            vives["sommets_avant"] += n_av
            vives["sommets_apres"] += len(bm.verts)
    bm.verts.index_update()
    groupes = {}
    for f in bm.faces:
        groupes.setdefault(f.material_index, []).append(f)
    for mi, faces in groupes.items():
        mat = mats[mi] if mi < len(mats) else None
        vmap, verts, flist = {}, [], []
        for f in faces:
            idx = []
            for v in f.verts:
                if v.index not in vmap:
                    vmap[v.index] = len(verts)
                    verts.append([round(c, 6) for c in v.co])
                idx.append(vmap[v.index])
            flist.append(idx)
        nom_mat = mat.name if mat else ""
        if nom_mat not in mats_vus:
            mats_vus[nom_mat] = couleur(mat)
            alphas[nom_mat] = round(mat.diffuse_color[3], 4) if mat else 1.0      # alpha d'affichage
        parts.append({"objet": ob.name, "calque": lay, "materiau": nom_mat, "verts": verts, "faces": flist})
    bm.free()
meta = {"t_build": round(t_build, 1), "t_total": round(time.time() - t0, 1), "soudes": soudes,
        "objets_par_collection": par_coll, "ignores": ignores, "ngons_triangules": n_tri, "faces_nulles": n_nulles,
        "aretes_vives": vives, "alphas": alphas,
        "objets_exportes": len(objets), "materiaux": mats_vus, "bbox_blender": [mn, mx], "unite": unite,
        "unit_settings": {"system": us.system, "length_unit": us.length_unit, "scale_length": us.scale_length},
        "collections_racines": racines}
json.dump({"meta": meta, "parts": parts}, open(out, "w", encoding="utf-8"))
print("EXPORT_OK", len(parts), sum(len(p["faces"]) for p in parts), round(time.time() - t0, 1))
'''


def args_build(build_src):
    """Options du build : seulement celles qu'il connaît (un argparse refuse les options inconnues après --)."""
    opts = []
    for o in ("--no-json", "--sans-vegetation", "--sans-brins", "--sans-contexte", "--dao"):
        if f'"{o}"' in build_src or f"'{o}'" in build_src:
            opts.append(o)
    return opts


def extraire(build_path, json_path):
    src = open(build_path, encoding="utf-8").read()
    opts = {"exclure": EXCLURE, "soudure_m": SOUDURE_M, "pied_m": PIED_M, "args_build": args_build(src),
            "angle_pli": ANGLE_PLI}
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(BLENDER_EXTRACTION)
        snippet = f.name
    t0 = time.time()
    try:
        r = subprocess.run([BLENDER, "-b", "--factory-startup", "--python", snippet, "--", build_path, json_path,
                            json.dumps(opts)], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env=ENV_BLENDER)
    finally:
        os.remove(snippet)
    ok = [ligne for ligne in r.stdout.splitlines() if ligne.startswith("EXPORT_OK")]
    if not ok:
        log(r.stdout[-4000:], r.stderr[-4000:])
        raise SystemExit("Échec de l'extraction Blender")
    signales = [ligne.strip() for ligne in r.stdout.splitlines() if "ÉCART" in ligne or "AVERTISSEMENT" in ligne]
    log(f"Blender ({time.time() - t0:.0f} s) : {ok[0]} | options du build : {opts['args_build']} | "
        f"collections exclues : {EXCLURE}")
    return time.time() - t0, signales


def unite_du_modele(meta):
    """Détecte l'unité du modèle : longueur du bâtiment (47 pi) = 14,3 si mètres, 47 si pieds."""
    (x0, y0, _), (x1, y1, _) = meta["bbox_blender"]
    lx, ly = x1 - x0, y1 - y0
    us = meta["unit_settings"]
    if meta["unite"] == "pi":
        return "pi", 12.0, f"étendue {lx:.2f} x {ly:.2f} unités Blender : PIEDS (unit_settings {us})"
    if meta["unite"] == "m":
        return "m", 1 / 0.0254, f"étendue {lx:.2f} x {ly:.2f} unités Blender : MÈTRES (unit_settings {us})"
    raise SystemExit(f"Unité du modèle indéterminée : étendue {lx:.2f} x {ly:.2f} (unit_settings {us})")


# ============================================================================ 2. DXF
def nom_calque(n):
    s = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode()
    return "-".join(s.upper().replace("_", " ").split()) or "DIVERS"


def transparence(nom_mat, alpha):
    """Transparence d'entité (0 opaque … 1 invisible) : 1 − alpha d'affichage du matériau, bornée à VERRE_BORNES pour
    un verre (nom en « verre », « vitr », « glass ») ; verre resté à l'alpha 1 : TRANSPARENCE_VERRE ; sinon 0 (opaque,
    aucun code 440 écrit)."""
    verre = bool(MOTIF_VERRE.search(nom_mat or ""))
    if alpha is not None and alpha < 0.999:
        bas, haut = VERRE_BORNES if verre else (0.0, TRANSPARENCE_MAX)
        return round(min(max(1.0 - alpha, bas), haut), 2)
    return TRANSPARENCE_VERRE if verre else 0.0


def construire_dxf(parts, couleurs, scale, proprietes, path, alphas=None):
    alphas = alphas or {}
    doc = ezdxf.new("R2018", setup=True)
    h = doc.header
    h["$INSUNITS"], h["$LUNITS"], h["$MEASUREMENT"], h["$LUPREC"] = 1, 4, 0, 4
    ds = doc.dimstyles.add("ARCH-48")                   # style de cote architectural courant (aucune cote ici)
    for k, v in dict(dimscale=48, dimtxt=3 / 32, dimasz=3 / 32, dimexo=1 / 16, dimexe=1 / 8, dimdle=1 / 16,
                     dimgap=1 / 32, dimtad=1, dimtih=0, dimtoh=0, dimlunit=4, dimdec=4, dimzin=3, dimfrac=2).items():
        setattr(ds.dxf, k, v)
    ds.set_arrows(blk=ezdxf.ARROWS.architectural_tick)
    h["$DIMSTYLE"] = "ARCH-48"                          # ezdxf.new laisse « ISO-25 » absent (piège CLAUDE.md)
    for name, (aci, desc) in LAYERS.items():
        lay = doc.layers.add(name, color=aci)
        lay.description = desc
        if name == "FENETRES-PRES":
            lay.dxf.plot = 0
    # Matériau « Global » « par objet » (71 = 0), comme celui d'AutoCAD. ezdxf le crée avec un diffus IMPOSÉ BLANC
    # (71 = 1, 0xC2FFFFFF), gardé par ODA : le visualiseur de l'ERP rendait alors tout gris.
    mat_global = doc.materials.get("Global")
    if mat_global is not None:
        mat_global.dxf.diffuse_color_method = 0
    doc.appids.add(APPID)
    msp = doc.modelspace()
    sans_couleur = Counter()
    for p in parts:
        lay = p["calque"] if p["calque"] in LAYERS else nom_calque(p["calque"])
        if lay not in doc.layers:
            doc.layers.add(lay, color=7).description = "Collection Blender : " + p["calque"]
        mesh = msp.add_mesh(dxfattribs={"layer": lay})
        c = couleurs.get(p["materiau"])
        if c is None:
            sans_couleur[p["materiau"]] += 1
            c = (200, 200, 200)
        mesh.rgb = tuple(c)
        t = transparence(p["materiau"], alphas.get(p["materiau"]))
        if t > 0.0:
            mesh.transparency = t                      # code 440 (verre : le visualiseur de l'ERP le respecte)
        with mesh.edit_data() as data:
            data.vertices = [(x * scale, y * scale, z * scale) for x, y, z in p["verts"]]
            data.faces = p["faces"]
        mesh.set_xdata(APPID, [(1000, p["objet"][:250]), (1000, p["materiau"][:250])])
    ext = ezbbox.extents(msp)
    msp.dxf.extmin, msp.dxf.extmax = tuple(ext.extmin), tuple(ext.extmax)   # $EXTMIN/$EXTMAX écrasés par ezdxf
    # vue d'ouverture : isométrique depuis l'avant-gauche (façade avant +X, côté gauche -Y : garage), OMBRÉE
    cx, cy, cz = [(a + b) / 2 for a, b in zip(ext.extmin, ext.extmax)]
    styles = doc.rootdict.get("ACAD_VISUALSTYLE")
    ombre = styles["Shaded"] if styles is not None and "Shaded" in styles else None
    for vp in doc.viewports.get_config("*Active"):
        vp.dxf.target = (cx, cy, cz)
        vp.dxf.direction = (1.0, -1.0, 0.8)
        vp.dxf.center = (0.0, 0.0)
        vp.dxf.height = (ext.extmax[1] - ext.extmin[1]) * 1.1
        vp.dxf.render_mode = 4
        if ombre is not None:                          # sans style visuel, ODA remet la vue en fil de fer
            vp.dxf.visual_style_handle = ombre.dxf.handle
    for lay in doc.layouts:
        if lay.name != "Model":
            for v in lay.query("VIEWPORT"):
                v.dxf.layer = "FENETRES-PRES"
    for k, v in proprietes:
        doc.header.custom_vars.append(k, v)
    aud = doc.audit()
    doc.saveas(path)
    return doc, ext, aud, sans_couleur


def find_odafc():
    """ODA File Converter du poste (copie portable d'abord, par outils\\chemins.py), déclaré à ezdxf ; None sinon."""
    try:
        return _CH.configurer_ezdxf_odafc()
    except Exception as e:  # noqa: BLE001
        log(f"ODA File Converter : {e}")
        return None


def chemin_libre(path, ref_mtime=None):
    """Jamais d'écrasement d'un fichier ouvert (verrouillé) ou modifié après notre dernière génération."""
    base, ext = os.path.splitext(path)
    cand, k = path, 1
    while os.path.exists(cand):
        try:
            with open(cand, "r+b"):
                verrou = False
        except OSError:
            verrou = True
        modifie = ref_mtime is not None and os.path.getmtime(cand) > ref_mtime + 60
        if not verrou and not modifie:
            return cand
        log(f"  {os.path.basename(cand)} : {'ouvert dans une application' if verrou else 'modifié'} -> on écrit à côté")
        k += 1
        cand = f"{base}_v{k}{ext}"
    return cand


def comptes_par_calque(doc):
    """{calque: [MESH, sommets, faces, MESH transparents (code 440), {transparences}]}"""
    c = defaultdict(lambda: [0, 0, 0, 0, set()])
    for e in doc.modelspace():
        if e.dxftype() == "MESH":
            c[e.dxf.layer][0] += 1
            c[e.dxf.layer][1] += len(e.vertices)
            c[e.dxf.layer][2] += len(e.faces)
            if e.dxf.hasattr("transparency") and e.transparency > 0.0:
                c[e.dxf.layer][3] += 1
                c[e.dxf.layer][4].add(round(e.transparency, 2))
    return dict(c)


# ============================================================================ 3. contrôles
def enveloppe(P):
    """Boîte du bâtiment et de ses annexes dessinées (pieds) : emprise, patio et escaliers, toits et débords, marge 1'."""
    xs = [x for x, _ in P.EMPRISE_RDC] + list(P.PATIO["X"])
    ys = [y for _, y in P.EMPRISE_RDC] + list(P.PATIO["Y"])
    for t in P.TOITS.values():
        xs += list(t["X"])
        ys += list(t["egouts_Y"])
    RI = getattr(P, "RI", None)
    if RI is not None:
        for e in RI.ESCALIERS:
            for v in e["volees"]:
                xs += [v["emprise"][0], v["emprise"][2]]
                ys += [v["emprise"][1], v["emprise"][3]]
    ys += list(P.CHEMINEE["Y"])
    z1 = max(t["Z_faite"] for t in P.TOITS.values()) + 3.0          # cheminée, chapeau et mitre au-dessus du faîte
    marge = 1.0
    return (min(xs) - marge, min(ys) - marge, -P.EP_SEMELLE - marge), (max(xs) + marge, max(ys) + marge, z1)


def hors_enveloppe(doc, env):
    (x0, y0, z0), (x1, y1, z1) = env
    hors = []
    for e in doc.modelspace().query("MESH"):
        v = list(e.vertices)
        if not v:
            continue
        bx0, by0, bz0 = (min(p[i] for p in v) / 12 for i in range(3))
        bx1, by1, bz1 = (max(p[i] for p in v) / 12 for i in range(3))
        if bx0 < x0 or by0 < y0 or bz0 < z0 or bx1 > x1 or by1 > y1 or bz1 > z1:
            xd = e.get_xdata(APPID) if e.has_xdata(APPID) else []
            hors.append((xd[0].value if xd else "?", e.dxf.layer, (round(bx0, 2), round(by0, 2), round(bz0, 2)),
                         (round(bx1, 2), round(by1, 2), round(bz1, 2))))
    return hors


def ecrire_obj(doc, obj_path, mtl_path):
    """MESH relus -> OBJ + MTL (MÈTRES, Kd linéaires) pour le graphe de contacts et les aperçus."""
    def lin(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    mats = {}
    lignes, off = [f"mtllib {os.path.basename(mtl_path)}"], 1
    for i, e in enumerate(doc.modelspace().query("MESH")):
        xd = e.get_xdata(APPID) if e.has_xdata(APPID) else []
        nom = (xd[0].value if xd else f"mesh{i}") + (" / " + xd[1].value if len(xd) > 1 and xd[1].value else "")
        nom = nom.replace(" ", "_")
        rgb = e.rgb or (200, 200, 200)
        cle = "c%02x%02x%02x" % tuple(rgb)
        mats[cle] = rgb
        lignes.append(f"o {i:05d}|{e.dxf.layer}|{nom}")
        lignes.append(f"usemtl {cle}")
        # sommets dédoublés aux arêtes vives : RESSOUDÉS PAR POSITION, sinon chaque face deviendrait un îlot du graphe
        # des contacts (et la parité « pièce contenue » n'aurait plus de sens sur une face seule)
        vs, ref, remap = [], {}, []
        for p in e.vertices:
            k = (round(p[0], 6), round(p[1], 6), round(p[2], 6))
            if k not in ref:
                ref[k] = len(vs)
                vs.append(p)
            remap.append(ref[k])
        for p in vs:
            lignes.append("v %.5f %.5f %.5f" % (p[0] * 0.0254, p[1] * 0.0254, p[2] * 0.0254))
        for f in e.faces:
            lignes.append("f " + " ".join(str(off + remap[k]) for k in f))
        off += len(vs)
    with open(obj_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lignes) + "\n")
    with open(mtl_path, "w", encoding="utf-8") as f:
        for cle, rgb in mats.items():
            r, g, b = (lin(c) for c in rgb)
            f.write(f"newmtl {cle}\nKd {r:.5f} {g:.5f} {b:.5f}\nKs 0.05 0.05 0.05\nNs 10\nd 1.0\n\n")


BLENDER_CONTROLE = r'''
import bpy, json, math, sys, time
from collections import Counter
from mathutils import Vector
from mathutils.bvhtree import BVHTree
args = sys.argv[sys.argv.index("--") + 1:]
obj, mode, sortie = args[0], args[1], args[2]
t0 = time.time()
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.obj_import(filepath=obj, forward_axis="Y", up_axis="Z")
obs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
mn = Vector((min(v[0] for o in obs for v in o.bound_box), min(v[1] for o in obs for v in o.bound_box),
             min(v[2] for o in obs for v in o.bound_box)))
mx = Vector((max(v[0] for o in obs for v in o.bound_box), max(v[1] for o in obs for v in o.bound_box),
             max(v[2] for o in obs for v in o.bound_box)))
res = {"objets": len(obs), "bbox_m": [list(mn), list(mx)], "t_import": round(time.time() - t0, 1)}
if mode == "contacts":
    TOL = 0.0127                                       # 1/2" : deux pièces se touchent à 1/2" près
    Z_SOL = float(args[3])                             # m : sol fini + 3"
    iles = []
    for o in obs:
        me = o.data
        par = list(range(len(me.vertices)))
        def rac(a):
            while par[a] != a:
                par[a] = par[par[a]]
                a = par[a]
            return a
        for p in me.polygons:
            r0 = rac(p.vertices[0])
            for v in p.vertices[1:]:
                rv = rac(v)
                if rv != r0:
                    par[rv] = r0
        groupes = {}
        for p in me.polygons:
            groupes.setdefault(rac(p.vertices[0]), []).append(p)
        co = me.vertices
        for k, polys in enumerate(groupes.values()):
            idx = sorted({v for p in polys for v in p.vertices})
            rem = {v: n for n, v in enumerate(idx)}
            pts = [co[v].co.copy() for v in idx]
            b0 = Vector((min(q.x for q in pts), min(q.y for q in pts), min(q.z for q in pts)))
            b1 = Vector((max(q.x for q in pts), max(q.y for q in pts), max(q.z for q in pts)))
            bvh = BVHTree.FromPolygons(pts, [[rem[v] for v in p.vertices] for p in polys], epsilon=0.0)
            iles.append((o.name, k, b0, b1, bvh, pts[::max(1, len(pts) // 60)]))
    n = len(iles)
    DIR = Vector((0.5773, 0.5774, 0.5775)).normalized()
    def dedans(bvh, p):
        """Parité des intersections d'un rayon oblique : impair = le point est à l'intérieur de la pièce."""
        n_hits, o = 0, p.copy()
        for _ in range(64):
            hit = bvh.ray_cast(o, DIR)
            if hit[0] is None:
                break
            n_hits += 1
            o = hit[0] + DIR * 1e-6
        return n_hits % 2 == 1
    def composantes(sous_ensemble):
        """Union-find des îlots du sous-ensemble (contact à TOL près, ou îlot contenu dans l'autre)."""
        parent = {i: i for i in sous_ensemble}
        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a
        contenus = paires = 0
        ordre = sorted(sous_ensemble, key=lambda i: iles[i][2].x)
        for ii, i in enumerate(ordre):
            _, _, a0, a1, ba, sa = iles[i]
            for j in ordre[ii + 1:]:
                _, _, c0, c1, bb, sb = iles[j]
                if c0.x > a1.x + TOL:
                    break
                if c0.y > a1.y + TOL or c1.y < a0.y - TOL or c0.z > a1.z + TOL or c1.z < a0.z - TOL:
                    continue
                if find(i) == find(j):
                    continue
                paires += 1
                touche = bool(ba.overlap(bb))
                if not touche:
                    touche = any(bb.find_nearest(q, TOL)[0] is not None for q in sa)
                if not touche:
                    touche = any(ba.find_nearest(q, TOL)[0] is not None for q in sb)
                if not touche:                          # pièce CONTENUE dans l'autre (vitrage dans un cadre...)
                    touche = dedans(bb, sa[0]) or dedans(ba, sb[0])
                    contenus += int(touche)
                if touche:
                    parent[find(i)] = find(j)
        comp = {}
        for i in sous_ensemble:
            comp.setdefault(find(i), []).append(i)
        return sorted(comp.values(), key=len, reverse=True), paires, contenus
    def desc(g):
        noms = Counter(iles[i][0] for i in g)
        b0 = [min(iles[i][2][k] for i in g) for k in range(3)]
        b1 = [max(iles[i][3][k] for i in g) for k in range(3)]
        return {"iles": len(g), "objets": dict(noms.most_common(4)), "bbox_pi": [[round(v / 0.3048, 2) for v in b0],
                [round(v / 0.3048, 2) for v in b1]], "au_sol": b0[2] <= Z_SOL + TOL}
    groupes, paires, contenus = composantes(list(range(n)))
    res["iles"] = n
    res["paires_testees"] = paires
    res["contacts_par_inclusion"] = contenus
    res["composantes"] = len(groupes)
    res["principale"] = desc(groupes[0])
    res["flottantes"] = [desc(g) for g in groupes[1:] if not desc(g)["au_sol"]]
    res["au_sol_separees"] = [desc(g) for g in groupes[1:] if desc(g)["au_sol"]]
    # CONTRE-ESSAI : sans les pièces du calque INDICATIF (nom d'objet OBJ « 00042|CALQUE|nom »)
    calque_ind = args[4] if len(args) > 4 else "INDICATIF"
    ind = {i for i in range(n) if iles[i][0].split("|")[1:2] == [calque_ind]}
    res["iles_indicatif"] = len(ind)
    if ind:
        g2, _p2, _c2 = composantes([i for i in range(n) if i not in ind])
        res["sans_indicatif_composantes"] = len(g2)
        res["portees_par_indicatif"] = [desc(g) for g in g2[1:] if not desc(g)["au_sol"]]
        res["au_sol_sans_indicatif"] = [desc(g) for g in g2[1:] if desc(g)["au_sol"]]
    res["t_contacts"] = round(time.time() - t0, 1)
else:
    # Aperçus en CYCLES SUR CPU (aucun GPU : consigne de l'équipe)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = int(args[4]) if len(args) > 4 else 12
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 3
    sc.render.resolution_x, sc.render.resolution_y = 1400, 940
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "Standard"
    w = bpy.data.worlds.new("Monde")
    sc.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.13, 0.14, 0.16, 1.0)
    w.node_tree.nodes["Background"].inputs[1].default_value = 1.0
    sol = bpy.data.lights.new("Soleil", "SUN")
    sol.energy = 3.0
    so = bpy.data.objects.new("Soleil", sol)
    sc.collection.objects.link(so)
    ctr = (mn + mx) / 2
    cam = bpy.data.cameras.new("Cam")
    cam.type = "ORTHO"
    co = bpy.data.objects.new("Cam", cam)
    sc.collection.objects.link(co)
    sc.camera = co
    vues = json.loads(args[3])
    for nom, d, taille, dec_az, haut in vues:
        dv = Vector(d).normalized()
        az = math.atan2(dv.y, dv.x) + math.radians(dec_az)
        s_ = Vector((math.cos(az), math.sin(az), haut)).normalized()
        so.rotation_euler = (-s_).to_track_quat("-Z", "Y").to_euler()
        co.location = ctr + dv * 60.0
        co.rotation_euler = (-dv).to_track_quat("-Z", "Y").to_euler()
        cam.ortho_scale = taille
        cam.clip_end = 300.0
        sc.render.filepath = nom
        bpy.ops.render.render(write_still=True)
    res["t_rendu"] = round(time.time() - t0, 1)
json.dump(res, open(sortie, "w", encoding="utf-8"))
print("CONTROLE_OK", json.dumps({k: v for k, v in res.items() if k not in ("flottantes", "au_sol_separees",
                                                                           "portees_par_indicatif",
                                                                           "au_sol_sans_indicatif")}))
'''


def blender_controle(obj_path, mode, vues=None, extra=None, echantillons=None, extra2=None):
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(BLENDER_CONTROLE)
        snippet = f.name
    sortie = os.path.join(tempfile.gettempdir(), f"bungalow_controle_{mode}.json")
    cmd = [BLENDER, "-b", "--factory-startup", "--python", snippet, "--", obj_path, mode, sortie]
    if vues is not None:
        cmd.append(json.dumps(vues))
    if extra is not None:
        cmd.append(extra)
    if echantillons is not None:
        cmd.append(str(echantillons))
    if extra2 is not None:
        cmd.append(extra2)
    t0 = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENV_BLENDER)
    finally:
        os.remove(snippet)
    if "CONTROLE_OK" not in r.stdout:
        log(r.stdout[-4000:], r.stderr[-4000:])
        raise SystemExit(f"Échec du contrôle Blender ({mode})")
    with open(sortie, encoding="utf-8") as fh:
        res = json.load(fh)
    os.remove(sortie)
    res["t_session"] = round(time.time() - t0, 1)
    return res


# ============================================================================ chaîne
def main():
    t_debut = time.time()
    essai = "--essai" in sys.argv
    build_autre = sys.argv[sys.argv.index("--build") + 1] if "--build" in sys.argv else None
    if build_autre and not essai:
        raise SystemExit("--build n'est permis qu'en --essai (l'export final part toujours de la copie figée).")
    sortie_dir = os.path.join(DWG_DIR, "essais") if essai else DWG_DIR
    os.makedirs(sortie_dir, exist_ok=True)
    out_base = os.path.join(sortie_dir, "bungalow_3d_essai" if essai else "bungalow_3d")
    rapport = []

    def note(s=""):
        log(s)
        rapport.append(s)

    # 0. sources
    if essai:
        dossier = instantane_vivant(build_autre)
        note(f"ESSAI sur les fichiers VIVANTS (instantané {dossier})" + (f" ; build remplacé par {build_autre}"
                                                                          if build_autre else ""))
    else:
        if "--figer" in sys.argv:
            EMP.figer_sources()
        dossier = EMP.SOURCES_FIGEES
        if not os.path.exists(os.path.join(dossier, BUILD)):
            raise SystemExit(f"Aucune copie figée de {BUILD} dans {dossier} : lancer avec --figer quand le modèle est "
                             f"déclaré final (ou --essai pour un essai).")
    build_path = os.path.join(dossier, BUILD)
    if not os.path.exists(build_path):
        raise SystemExit(f"{BUILD} introuvable dans {dossier} (le modèle n'est pas encore écrit ?)")
    emp = EMP.empreinte_sources(dossier)
    emp_build = sha(build_path, 12)
    emp_fichier = None
    f_emp = os.path.join(dossier, "EMPREINTE.txt")
    if not essai and os.path.exists(f_emp):
        with open(f_emp, encoding="utf-8") as fh:
            emp_fichier = [ligne.split()[1] for ligne in fh if ligne.startswith("empreinte ")][0]
        if emp_fichier != emp:
            raise SystemExit(f"La copie figée a changé depuis son figeage ({emp_fichier} -> {emp}) : refiger.")
    note(f"Empreinte des sources (empreinte_bungalow.empreinte_sources) : {emp}"
         + (f" (EMPREINTE.txt : {emp_fichier})" if emp_fichier else "") + f" ; build sha256 {emp_build}")
    P = importer_parametres(dossier)

    # 1. extraction Blender (l'unité est détectée dans Blender, avant la soudure qui en dépend)
    json_path = os.path.join(tempfile.gettempdir(), "bungalow_geometrie.json")
    t_blender, signales = extraire(build_path, json_path)
    with open(json_path, encoding="utf-8") as fh:
        data = json.load(fh)
    unite, scale, texte_unite = unite_du_modele(data["meta"])
    os.remove(json_path)
    parts, meta = data["parts"], data["meta"]
    note(f"Unité du modèle : {texte_unite} -> facteur {scale:.5f} vers les pouces")
    note(f"Blender : construction {meta['t_build']} s, extraction totale {meta['t_total']} s ; objets exportés "
         f"{meta['objets_exportes']} ; groupes (objet, matériau) {len(parts)} ; n-gones triangulés "
         f"{meta['ngons_triangules']} ; faces d'aire nulle retirées {meta['faces_nulles']} ; ignorés {meta['ignores']}")
    note("Objets par collection (scène complète) : " + ", ".join(f"{k} {v}" for k, v in
                                                               sorted(meta["objets_par_collection"].items())))
    inconnues = [c for c in meta["collections_racines"] if c not in LAYERS and c not in EXCLURE]
    manquantes = [c for c in LAYERS if c != "FENETRES-PRES" and c not in meta["collections_racines"]]
    note(f"Collections hors liste (calque dérivé du nom) : {inconnues or 'aucune'} ; calques attendus sans "
         f"collection : {manquantes or 'aucun'}")
    note(f"Sommets soudés dans {len(meta['soudes'])} objet(s)")
    av = meta.get("aretes_vives", {})
    if ANGLE_PLI >= 180.0:
        note(f"Arêtes vives : AUCUNE (--angle-pli {ANGLE_PLI:g} : tout soudé, comme avant le 2026-09-28)")
    else:
        note(f"Arêtes vives (> {ANGLE_PLI:g}°) : {av.get('aretes', 0)} arêtes dédoublées dans {av.get('objets', 0)} "
             f"objets (dont {av.get('non_manifold', 0)} à plus de 2 faces) ; sommets {av.get('sommets_avant', 0)} -> "
             f"{av.get('sommets_apres', 0)}")
    couleurs = {nom: tuple(c) for nom, (c, _) in meta["materiaux"].items() if c is not None}
    alphas = meta.get("alphas", {})
    note("Couleurs vraies par matériau (et transparence d'entité, code 440) :")
    for nom in sorted(meta["materiaux"]):
        c, origine = meta["materiaux"][nom]
        t = transparence(nom, alphas.get(nom))
        note(f"  {nom or '(aucun)':<40} {'#%02X%02X%02X' % tuple(c) if c else '(gris 200)':<9} ({origine})"
             + (f" ; transparence {t:.2f}" if t > 0.0 else ""))
    for p in parts:
        if p["calque"] == "VITRAGE" and transparence(p["materiau"], alphas.get(p["materiau"])) == 0.0:
            note(f"  AVERTISSEMENT : « {p['objet']} » sur VITRAGE reste OPAQUE (matériau « {p['materiau']} »)")

    # 2. DXF
    date = time.strftime("%Y-%m-%d %H:%M")
    proprietes = [
        ("Projet", "Maison Bungalow - maquette 3D (discipline A)"),       # adresse retirée du modèle
        ("Source", f"build_bungalow.py + parametres_bungalow.py + releve_*.py ; empreinte {emp}"
                   + (" (ESSAI sur fichiers vivants)" if essai else " (copie figee sources_figees)")),
        ("Empreinte", emp),
        ("Modele", f"{BUILD} sha256 {emp_build} ; unite du modele : {unite}"),
        ("Revision", "ESSAI - NE PAS DIFFUSER" if essai else "A - POUR INFORMATION"),
        ("Date", date),
        ("Auteur", "Exporte par une IA (Claude, agent DAO) d'apres les plans du technologue, rev. 1 du 24 aout 2026"),
        ("Statut", "Document de travail : a valider et a sceller par un professionnel. Aucun sceau."),
        ("Unites", "pouces (INSUNITS=1), affichage architectural"),
    ]
    dxf_path = chemin_libre(out_base + ".dxf")
    ref = os.path.getmtime(dxf_path) if os.path.exists(dxf_path) else None
    doc, ext, aud, sans_couleur = construire_dxf(parts, couleurs, scale, proprietes, dxf_path, alphas)
    note(f"DXF : {dxf_path} ({os.path.getsize(dxf_path) / 1e6:.2f} Mo ; audit {len(aud.errors)} erreur(s), "
         f"{len(aud.fixes)} correction(s))")
    if aud.errors:
        raise SystemExit("Audit du DXF en erreur : rien n'est converti.")
    if sans_couleur:
        note(f"  groupes sans couleur (gris) : {dict(sans_couleur)}")
    note(f"Étendue (pi) : {[round(v / 12, 2) for v in ext.extmin]} -> {[round(v / 12, 2) for v in ext.extmax]}")
    if "--sans-dwg" in sys.argv:
        return
    exe = find_odafc()
    if not exe:
        raise SystemExit("ODA File Converter introuvable")
    from ezdxf.addons import odafc
    ezdxf.options.set("odafc-addon", "win_exec_path", exe)
    dwg_path = chemin_libre(out_base + ".dwg", ref)
    t0 = time.time()
    odafc.export_dwg(doc, dwg_path, version="R2018", replace=True)
    t_oda = time.time() - t0
    d2 = odafc.readfile(dwg_path)
    a2 = d2.audit()
    taille = os.path.getsize(dwg_path)
    note(f"DWG : {dwg_path} ({taille / 1e6:.2f} Mo ; plafond {TAILLE_MAX_MO} Mo : "
         f"{'OK' if taille / 1e6 <= TAILLE_MAX_MO else 'DÉPASSÉ'}) ; ODA {t_oda:.0f} s ; relu version "
         f"{d2.dxfversion}, audit {len(a2.errors)} erreur(s)")
    hd = d2.header
    note(f"  en-tête : INSUNITS {hd.get('$INSUNITS')} LUNITS {hd.get('$LUNITS')} DIMSTYLE {hd.get('$DIMSTYLE')}")
    vpa = d2.viewports.get_config("*Active")[0]
    note(f"  vue d'ouverture : direction {tuple(round(v, 2) for v in vpa.dxf.direction)}, render_mode "
         f"{vpa.dxf.get('render_mode')}, style visuel {'oui' if vpa.dxf.get('visual_style_handle') else 'NON'}")
    pr = dict(d2.header.custom_vars)
    note(f"  propriétés relues : Empreinte = {pr.get('Empreinte')!r} ; Revision = {pr.get('Revision')!r} ; "
         f"Modele = {pr.get('Modele')!r}")
    if pr.get("Empreinte") != emp:
        raise SystemExit("L'empreinte relue dans le DWG ne correspond pas.")
    nouveaux = sorted({ly.dxf.name for ly in d2.layers} - {ly.dxf.name for ly in doc.layers})
    note("  calques créés par ODA : " + (", ".join(nouveaux) if nouveaux else "aucun"))
    c = comptes_par_calque(d2)
    tot = [sum(v[i] for v in c.values()) for i in range(4)]
    note("  %-12s %8s %10s %10s  %s" % ("calque", "MESH", "sommets", "faces", "transparents (code 440 relu)"))
    for k in sorted(c, key=lambda k: -c[k][1]):
        note("  %-12s %8d %10d %10d  %s" % (k, *c[k][:3], ("%d : %s" % (c[k][3], sorted(c[k][4]))) if c[k][3] else "-"))
    note("  %-12s %8d %10d %10d  %d" % ("TOTAL", *tot))
    ecrites = sum(1 for e in doc.modelspace().query("MESH") if e.dxf.hasattr("transparency"))
    note(f"  transparences : {ecrites} écrites dans le DXF, {tot[3]} relues dans le DWG"
         + ("" if ecrites == tot[3] else "  <<< ÉCART : transparence perdue par ODA"))
    g2 = d2.materials.get("Global")
    methode = g2.dxf.get("diffuse_color_method", 0) if g2 is not None else None   # absent = 0 (défaut DXF)
    note(f"  matériau Global relu : diffus {'par objet' if methode == 0 else 'IMPOSÉ (méthode %s)' % methode}")
    note(f"  types d'entités : {dict(Counter(e.dxftype() for e in d2.modelspace()))} ; "
         f"XDATA {APPID} : {sum(1 for e in d2.modelspace().query('MESH') if e.has_xdata(APPID))}")

    # 3. contrôles
    env = enveloppe(P)
    hors = hors_enveloppe(d2, env)
    note(f"Pièces hors de l'enveloppe du bâtiment {tuple(round(v, 1) for v in env[0])} -> "
         f"{tuple(round(v, 1) for v in env[1])} (pi) : {len(hors)}")
    for h_ in hors[:20]:
        note(f"  HORS : {h_}")
    obj_path = os.path.join(tempfile.gettempdir(), "bungalow_controle_3d.obj")
    mtl_path = os.path.join(tempfile.gettempdir(), "bungalow_controle_3d.mtl")
    ecrire_obj(d2, obj_path, mtl_path)
    if "--sans-contacts" not in sys.argv:
        z_sol = P.Z_SOL + 0.25                         # pi : sol fini + 3"
        rc = blender_controle(obj_path, "contacts", extra=str(z_sol * PIED_M), extra2=CALQUE_INDICATIF)
        note(f"Pièces flottantes : {rc['objets']} MESH relus découpés en {rc['iles']} îlots ; {rc['paires_testees']} "
             f"paires testées (contact à 1/2\" près, ou pièce contenue dans l'autre : {rc['contacts_par_inclusion']}) ; "
             f"{rc['composantes']} composante(s) ; « posé au sol » = dessous à {z_sol:.2f} pi au plus ; {rc['t_session']} s")
        note(f"  principale : {rc['principale']['iles']} îlots, étendue (pi) {rc['principale']['bbox_pi']}")
        note(f"  composantes FLOTTANTES (ni contact ni sol) : {len(rc['flottantes'])}")
        for g in rc["flottantes"][:40]:
            note(f"    FLOTTANTE : {g}")
        note(f"  composantes posées au sol sans contact avec le bâtiment : {len(rc['au_sol_separees'])}")
        for g in rc["au_sol_separees"][:40]:
            note(f"    AU SOL, SÉPARÉE : {g}")
        if rc.get("iles_indicatif"):
            note(f"  CONTRE-ESSAI sans le calque {CALQUE_INDICATIF} ({rc['iles_indicatif']} îlots retirés) : "
                 f"{rc['sans_indicatif_composantes']} composante(s) ; pièces de construction qui ne tiennent QUE par de "
                 f"l'indicatif : {len(rc['portees_par_indicatif'])} ; posées au sol et séparées : "
                 f"{len(rc['au_sol_sans_indicatif'])}")
            for g in rc["portees_par_indicatif"][:40]:
                note(f"    PORTÉE PAR L'INDICATIF SEULEMENT : {g}")
            for g in rc["au_sol_sans_indicatif"][:12]:
                note(f"    au sol, séparée sans l'indicatif : {g['objets']} ; étendue (pi) {g['bbox_pi']}")
        else:
            note(f"  contre-essai sans le calque {CALQUE_INDICATIF} : aucun îlot sur ce calque (sans objet)")
    if "--sans-rendu" not in sys.argv:
        with open(obj_path, encoding="utf-8") as fh:
            vs = [tuple(map(float, ligne.split()[1:4])) for ligne in fh if ligne.startswith("v ")]
        x0, y0 = min(v[0] for v in vs), min(v[1] for v in vs)
        x1, y1 = max(v[0] for v in vs), max(v[1] for v in vs)
        diag = math.hypot(x1 - x0, y1 - y0)
        prefixe = "apercu_3d_essai" if essai else "apercu_3d"
        vues = [[os.path.join(sortie_dir, f"{prefixe}_avant_gauche.png"), [1.0, -1.0, 0.75], diag * 1.02, 35.0, 1.1],
                [os.path.join(sortie_dir, f"{prefixe}_arriere_droit.png"), [-1.0, 1.0, 0.75], diag * 1.02, 35.0, 1.1]]
        rr = blender_controle(obj_path, "rendu", vues, echantillons=12)
        note(f"Aperçus Cycles CPU ({rr['t_session']} s) : " + ", ".join(os.path.basename(v[0]) for v in vues))
    for f in (obj_path, mtl_path):
        if os.path.exists(f):
            os.remove(f)
    # revérification de l'empreinte
    emp_fin = EMP.empreinte_sources(dossier)
    emp_vivant = EMP.empreinte_sources(HERE)
    note(f"Empreinte de la copie utilisée à la fin : {emp_fin} ({'inchangée' if emp_fin == emp else 'CHANGÉE'}) ; "
         f"fichiers vivants : {emp_vivant} ({'identiques' if emp_vivant == emp else 'modifiés depuis (normal en essai)'})")
    note(f"Durées : Blender {t_blender:.0f} s ; total {time.time() - t_debut:.0f} s")
    if signales:
        note("Signalé par le build : " + " | ".join(signales[:10]))
    with open(os.path.join(sortie_dir, "controle_3d_essai.txt" if essai else "controle_3d.txt"), "w",
              encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(rapport) + "\n")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:                                  # noqa: BLE001
        pass
    main()
