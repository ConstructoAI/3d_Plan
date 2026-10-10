# -*- coding: utf-8 -*-
"""
Export AutoCAD 3D d'un projet Blender (DXF 2018 + DWG par ODA File Converter) : MODÈLE du poste portable
=======================================================================================================
Modèle tiré de Garage_rouge_Blender\\exporter_autocad.py (voir modeles\\LISEZMOI.md). Blender et ODA File
Converter sont trouvés par outils\\chemins.py (copies portables du poste) : aucun chemin écrit en dur.

À copier à la racine du projet, à côté de build_<projet>.py. Avec le Python du poste (outils\\python) :
    python exporter_autocad.py                        -> <projet>_3d.dxf / .dwg (pouces, architectural)
    python exporter_autocad.py --build build_x.py     -> script du modèle imposé (défaut : l'unique build_*.py d'ici)
    python exporter_autocad.py --nom maison           -> nom de base des fichiers (défaut : tiré de build_<nom>.py)
    python exporter_autocad.py --sortie dwg           -> dossier de sortie (défaut : ce dossier)
    python exporter_autocad.py --avec-vegetation      -> + VEGETATION (allégée à 20 %, sans les feuilles instanciées)
    python exporter_autocad.py --avec-vegetation --vegetation-complete   -> végétation non allégée (lourd)
    python exporter_autocad.py --metres               -> unités en mètres (<projet>_3d_m.*)
    python exporter_autocad.py --borne-pi 40,100      -> écarte les morceaux qui sortent de l'emprise 40' x 100'
                                                         (+ 20' de marge), centrée sur l'origine : objets inventés
                                                         « hors champ » (défaut : on exporte tout)
    python exporter_autocad.py --angle-pli 30         -> angle (degrés) au-delà duquel une arête est VIVE : ses
                                                         sommets sont dédoublés (défaut 30 ; 180 = tout soudé, comme
                                                         avant le 2026-09-28)

1. Blender (arrière-plan) reconstruit la scène avec build_<projet>.py (sans argument, donc sans rendu ni
   sauvegarde) et extrait la géométrie évaluée (modificateurs appliqués) en coordonnées monde. Les collections
   non exportées (TERRAIN, CAMERAS, VEGETATION par défaut) sont exclues du calque de vue AVANT l'évaluation :
   feuilles instanciées et terrain ne sont jamais calculés.
2. UN CALQUE PAR COLLECTION (sauf le fond sombre des découpes, matériau « Intérieur sombre », mis sur
   OUVERTURES-FOND pour ne pas être métré avec le revêtement) : le script du modèle range ses objets dans des
   collections qui portent les noms des calques de Sylvain (MURS-EXT, MURS-INT, TOIT, OUVERTURES, MENUISERIE,
   VITRAGE, DALLE, FONDATION, MOBILIER…). CAMERAS et les gabarits de particules (« _gabarit … ») sont ignorés.
   Une collection inconnue devient un calque au même format (MAJUSCULES, tirets, sans accents).
3. Le bâtiment est exporté complet, sans simplification. Le terrain de Blender est remplacé par une dalle de sol
   simple autour de l'emprise exportée (calque TERRAIN), au niveau D_SOL du script du modèle s'il le définit
   (en mètres), sinon au plus bas point exporté.
4. Sommets confondus soudés, puis DÉDOUBLÉS le long des arêtes vives (2026-09-28, d'après l'escalier flottant) : un
   MESH ne porte pas de normales, et le visualiseur de l'ERP (module CAD) les calcule en moyennant TOUTES les faces
   autour d'un sommet, sans angle de pli ; une boîte soudée s'y arrondit « en coussin ». Les sommets ne restent donc
   partagés qu'entre faces d'angle faible (≤ --angle-pli, 30° par défaut) : boîtes nettes, surfaces courbes lisses.
   Une arête à plus de 2 faces est traitée comme vive. La géométrie (positions, faces, ordre) est inchangée ; seuls
   les indices de sommets diffèrent : un MESH n'est plus connexe par ses indices (souder par POSITION avant de
   chercher des îlots).
5. Transparence d'entité (code 440, conservée par ODA et appliquée par le visualiseur de l'ERP) : 1 − alpha
   d'affichage du matériau (Blender : Viewport Display > Color ; verre 0,35 → 0,65). Un matériau de verre (nom en
   « verre », « vitr » ou « glass ») reste entre 0,60 et 0,80, et reçoit TRANSPARENCE_VERRE (0,65) si son alpha
   d'affichage est resté à 1.
   Matériau « Global » (celui de tous les calques) mis « par objet », comme celui d'AutoCAD : ezdxf le crée avec un
   diffus IMPOSÉ BLANC, et le visualiseur de l'ERP rendait alors tout le modèle gris.
6. ezdxf écrit des entités MESH (n-gones > 4 triangulés), couleurs vraies tirées des matériaux, en pouces
   ($INSUNITS=1, $LUNITS=4), étendues réelles, style de cote architectural par défaut, vue d'ouverture isométrique
   ombrée ; ODA File Converter produit le DWG 2018, relu pour contrôle (transparences comprises). Un DWG ouvert dans
   une application ou modifié après la dernière génération n'est jamais écrasé : on écrit à côté (_v2, _v3…).
"""
import glob
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unicodedata
from collections import Counter, defaultdict

import ezdxf
from ezdxf import bbox as ezbbox

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


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


def _option(nom, defaut=None):
    """Valeur d'une option « --nom valeur » de la ligne de commande."""
    if nom in sys.argv:
        i = sys.argv.index(nom)
        if i + 1 >= len(sys.argv):
            raise SystemExit("%s : valeur manquante" % nom)
        return sys.argv[i + 1]
    return defaut


def _build_du_projet():
    impose = _option("--build")
    if impose:
        return os.path.abspath(impose)
    trouves = sorted(glob.glob(os.path.join(HERE, "build_*.py")))
    if len(trouves) == 1:
        return trouves[0]
    raise SystemExit("Script du modèle : %s ici ; préciser --build build_<projet>.py"
                     % ("aucun build_*.py" if not trouves else "plusieurs (" + ", ".join(
                         os.path.basename(t) for t in trouves) + ")"))


METRES = "--metres" in sys.argv
AVEC_VEG = "--avec-vegetation" in sys.argv
VEG_COMPLETE = "--vegetation-complete" in sys.argv
BORNE_PI = _option("--borne-pi")                     # « largeur,longueur » en pieds ; défaut : tout exporter
SCALE = 1.0 if METRES else 39.37007874015748          # m -> po
FT = 0.3048                                           # m par pied
MARGE_SOL = 20.0                                      # pi : dalle de sol autour de l'emprise (représentation)
COULEUR_SOL = (111, 138, 74)                          # gazon

LAYERS = {   # calque : (couleur ACI, description) — conventions de Sylvain (CLAUDE.md, « Préférences »)
    "MURS-EXT": (7, "Murs exterieurs et revetements"),
    "MURS-INT": (8, "Cloisons et murs interieurs"),
    "TOIT": (9, "Toiture, bordures de rive et d'egout"),
    "OUVERTURES": (3, "Portes et fenetres"),
    "OUVERTURES-FOND": (8, "Fond sombre derriere les baies (aide au rendu, a ne pas metrer)"),
    "MENUISERIE": (5, "Cadrages, moulures, solins"),
    "VITRAGE": (140, "Vitrages"),
    "DALLE": (8, "Dalles, tabliers et marches de beton"),
    "FONDATION": (253, "Fondations et murets de beton"),
    "ACCESSOIRES": (30, "Accessoires (mat electrique, compteur, affiche...)"),
    "MOBILIER": (6, "Mobilier et appareils"),
    "TERRAIN": (94, "Dalle de sol simple autour du batiment (representation)"),
    "VEGETATION": (96, "Arbustes et arbres (alleges, option --avec-vegetation)"),
    "FENETRES-PRES": (8, "Fenetres de presentation (non imprimees)"),
}
IGNORER = {"CAMERAS"}
CALQUE_MATIERE = {"Intérieur sombre": "OUVERTURES-FOND"}   # matériau -> calque (faces du fond des découpes)
SOUDURE = 1e-5                                              # m : sommets confondus soudés (textes convertis)
ANGLE_PLI = float(_option("--angle-pli", "30"))            # degrés : arête vive au-delà (sommets dédoublés)
TRANSPARENCE_VERRE = 0.65                                   # verre dont l'alpha d'affichage est resté à 1
VERRE_BORNES = (0.60, 0.80)                                 # un verre reste de 60 à 80 % transparent
TRANSPARENCE_MAX = 0.90                                     # autre matériau transparent : jamais invisible
MOTIF_VERRE = re.compile(r"verre|vitr|glass", re.I)         # noms de matériaux de verre
CALQUES_VERRE = {"VITRAGE", "GARDE-CORPS-VERRE"}            # un MESH opaque sur ces calques est signalé

# ----------------------------------------------------------------------------- partie Blender
BLENDER_SNIPPET = r'''
import bpy, bmesh, json, math, sys, time
t0 = time.time()
args = sys.argv[sys.argv.index("--") + 1:]
src, out, opts = args[0], args[1], json.loads(args[2])
sys.argv = [sys.argv[0]]                       # script du modèle sans argument : construction seule
g = {"__name__": "__main__", "__file__": src}
exec(compile(open(src, encoding="utf-8-sig").read(), src, "exec"), g)   # utf-8-sig : tolère un BOM
t_build = time.time() - t0

exclure = set(opts["exclure"])
for lc in bpy.context.view_layer.layer_collection.children:
    if lc.name in exclure:
        lc.exclude = True                      # jamais évaluées (particules, terrain)

parent = {}
for c in bpy.data.collections:
    for ch in c.children:
        parent[ch.name] = c.name

def calque(ob):
    for c in ob.users_collection:
        n = c.name
        while n is not None:
            if n in opts["connus"] or n in exclure:
                return n
            n = parent.get(n)
    return ob.users_collection[0].name if ob.users_collection else None

def srgb(c):
    c = max(0.0, min(1.0, c))
    return c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055

objets = []
for ob in bpy.data.objects:
    if ob.type not in ("MESH", "FONT", "CURVE", "SURFACE", "META") or ob.name.startswith("_gabarit"):
        continue
    if ob.hide_render:
        continue
    lay = calque(ob)
    if lay is None or lay in exclure:
        continue
    if lay == "VEGETATION" and ob.type == "MESH":
        for md in ob.modifiers:                # feuilles instanciées (particules) : jamais exportées
            if md.type == "PARTICLE_SYSTEM":
                md.show_viewport = md.show_render = False
        if not opts["veg_complete"]:
            dec = ob.modifiers.new("Allègement DAO", "DECIMATE")
            dec.ratio = 0.2
    objets.append((ob, lay))

dg = bpy.context.evaluated_depsgraph_get()
parts, retires, soudes = [], [], []
pli = math.radians(opts["angle_pli"])
vives = {"objets": 0, "aretes": 0, "non_manifold": 0, "sommets_avant": 0, "sommets_apres": 0}
for ob, lay in objets:
    ev = ob.evaluated_get(dg)
    mats = [s.material for s in ob.material_slots]
    me = bpy.data.meshes.new_from_object(ev)   # maillage évalué (modificateurs ; textes et courbes convertis)
    if not mats:
        mats = list(me.materials)
    me.transform(ob.matrix_world)
    bm = bmesh.new()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    n_av = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=opts["soudure"])   # doublons (textes convertis)
    if len(bm.verts) < n_av:
        soudes.append([ob.name, n_av, len(bm.verts)])
    hc = opts["hors_champ"]
    if hc:                                     # morceaux connexes sortant de la dalle de sol : écartés
        bm.faces.ensure_lookup_table()
        bm.faces.index_update()
        vus, dehors = set(), []
        for f0 in bm.faces:
            if f0.index in vus:
                continue
            pile, comp = [f0], []
            vus.add(f0.index)
            while pile:
                f1 = pile.pop()
                comp.append(f1)
                for v in f1.verts:
                    for f2 in v.link_faces:
                        if f2.index not in vus:
                            vus.add(f2.index)
                            pile.append(f2)
            if any(abs(v.co.x) > hc[0] or abs(v.co.y) > hc[1] for f1 in comp for v in f1.verts):
                dehors.append(comp)
        if dehors:
            nv = len({v.index for comp in dehors for f1 in comp for v in f1.verts})
            retires.append([ob.name, len(dehors), nv])
            bmesh.ops.delete(bm, geom=[f1 for comp in dehors for f1 in comp], context="FACES")
        if not bm.faces:
            bm.free()
            continue
    ngons = [f for f in bm.faces if len(f.verts) > 4]
    if ngons:
        bmesh.ops.triangulate(bm, faces=ngons, quad_method="BEAUTY", ngon_method="BEAUTY")
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
                    verts.append([round(c, 5) for c in v.co])
                idx.append(vmap[v.index])
            flist.append(idx)
        col = [int(round(srgb(c) * 255)) for c in (mat.diffuse_color[:3] if mat else (0.8, 0.8, 0.8))]
        lay_g = opts["calque_matiere"].get(mat.name, lay) if mat else lay
        parts.append({"name": ob.name + (" / " + mat.name if mat else ""), "layer": lay_g, "color": col,
                      "mat": mat.name if mat else "", "alpha": round(mat.diffuse_color[3], 4) if mat else 1.0,
                      "verts": verts, "faces": flist})
    bm.free()
meta = {"D_SOL": g.get("D_SOL"), "t_build": round(t_build, 1), "t_total": round(time.time() - t0, 1),
        "retires": retires, "soudes": soudes, "aretes_vives": vives, "blender": bpy.app.version_string}
json.dump({"meta": meta, "parts": parts}, open(out, "w", encoding="utf-8"))
print("EXPORT_OK", len(parts), sum(len(p["faces"]) for p in parts), json.dumps(meta))
'''


def nom_calque(n):
    """Nom de collection -> calque au format de Sylvain (MAJUSCULES, tirets, sans accents)."""
    s = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode()
    return "-".join(s.upper().replace("_", " ").split()) or "DIVERS"


def blender_dump(build, json_path):
    exclure = sorted(IGNORER | {"TERRAIN"} | (set() if AVEC_VEG else {"VEGETATION"}))
    borne = None
    if BORNE_PI:
        larg, long_ = (float(v) for v in BORNE_PI.split(","))
        borne = [(larg / 2 + MARGE_SOL) * FT, (long_ / 2 + MARGE_SOL) * FT]
    opts = {"connus": [k for k in LAYERS if k != "FENETRES-PRES"], "exclure": exclure,
            "veg_complete": VEG_COMPLETE, "hors_champ": borne, "soudure": SOUDURE,
            "calque_matiere": CALQUE_MATIERE, "angle_pli": ANGLE_PLI}
    ch = _chemins()
    blender = ch.blender_exe()
    # Environnement de la copie portable de Blender (ressources système, cache CUDA, variables BLENDER_USER_*
    # héritées retirées), si le module de chemins le fournit ; sinon l'environnement courant.
    env = ch.env_blender() if callable(getattr(ch, "env_blender", None)) else None
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(BLENDER_SNIPPET)
        snippet = f.name
    t0 = time.time()
    try:
        r = subprocess.run([blender, "-b", "--factory-startup", "--python", snippet, "--", build, json_path,
                            json.dumps(opts)], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           cwd=os.path.dirname(build), env=env)
    finally:
        os.remove(snippet)
    ok = [l for l in r.stdout.splitlines() if l.startswith("EXPORT_OK")]
    if not ok:
        print(r.stdout[-3000:], r.stderr[-3000:])
        raise SystemExit("Échec de l'extraction Blender")
    print(f"Blender {blender} ({time.time() - t0:.0f} s) :", ok[0], "| collections exclues :", exclure)


def transparence(p):
    """Transparence d'entité (0 opaque … 1 invisible) : 1 − alpha d'affichage du matériau, bornée à VERRE_BORNES pour
    un verre (nom en « verre », « vitr », « glass ») ; verre resté à l'alpha 1 : TRANSPARENCE_VERRE ; sinon 0 (opaque,
    aucun code 440 écrit)."""
    a = p.get("alpha", 1.0)
    verre = bool(MOTIF_VERRE.search(p.get("mat", "")))
    if a < 0.999:
        bas, haut = VERRE_BORNES if verre else (0.0, TRANSPARENCE_MAX)
        return round(min(max(1.0 - a, bas), haut), 2)
    return TRANSPARENCE_VERRE if verre else 0.0


def build_dxf(parts, d_sol, path):
    doc = ezdxf.new("R2018", setup=True)
    h = doc.header
    if METRES:
        h["$INSUNITS"], h["$LUNITS"], h["$MEASUREMENT"], h["$LUPREC"] = 6, 2, 1, 3
    else:
        h["$INSUNITS"], h["$LUNITS"], h["$MEASUREMENT"], h["$LUPREC"] = 1, 4, 0, 4
    # style de cote architectural par défaut (aucune cote ici, mais un DIMSTYLE courant valide)
    ds = doc.dimstyles.add("ARCH-48")
    for k, v in dict(dimscale=48, dimtxt=3 / 32, dimasz=3 / 32, dimexo=1 / 16, dimexe=1 / 8, dimdle=1 / 16,
                     dimgap=1 / 32, dimtad=1, dimtih=0, dimtoh=0, dimlunit=4, dimdec=4, dimzin=3, dimfrac=2).items():
        setattr(ds.dxf, k, v)
    ds.set_arrows(blk=ezdxf.ARROWS.architectural_tick)
    h["$DIMSTYLE"] = "ARCH-48"
    for k, v in dict(DIMSCALE=48, DIMLUNIT=4, DIMDEC=4, DIMZIN=3, DIMFRAC=2, DIMTXT=3 / 32, DIMASZ=3 / 32,
                     DIMTAD=1, DIMBLK="_ARCHTICK").items():
        h["$" + k] = v
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
    msp = doc.modelspace()
    for p in parts:
        lay = p["layer"] if p["layer"] in LAYERS else nom_calque(p["layer"])
        if lay not in doc.layers:
            doc.layers.add(lay, color=7).description = "Collection Blender : " + p["layer"]
        mesh = msp.add_mesh(dxfattribs={"layer": lay})
        mesh.rgb = tuple(p["color"])
        t = transparence(p)
        if t > 0.0:
            mesh.transparency = t                      # code 440 (verre : le visualiseur de l'ERP le respecte)
        with mesh.edit_data() as data:
            data.vertices = [(x * SCALE, y * SCALE, z * SCALE) for x, y, z in p["verts"]]
            data.faces = p["faces"]
    # emprise du bâtiment exporté (m), avant la dalle de sol
    xs = [v[0] for p in parts for v in p["verts"]]
    ys = [v[1] for p in parts for v in p["verts"]]
    zs_ = [v[2] for p in parts for v in p["verts"]]
    if not xs:
        raise SystemExit("Aucune géométrie exportée (collections vides ou toutes exclues).")
    x0, x1, y0, y1, z0, z1 = min(xs), max(xs), min(ys), max(ys), min(zs_), max(zs_)
    # dalle de sol simple autour de l'emprise (au lieu du terrain Blender), au niveau D_SOL (sinon le plus bas point)
    m = MARGE_SOL * FT
    zs = (d_sol if d_sol is not None else z0) * SCALE
    sol = msp.add_mesh(dxfattribs={"layer": "TERRAIN"})
    sol.rgb = COULEUR_SOL
    with sol.edit_data() as data:
        data.vertices = [((x0 - m) * SCALE, (y0 - m) * SCALE, zs), ((x1 + m) * SCALE, (y0 - m) * SCALE, zs),
                         ((x1 + m) * SCALE, (y1 + m) * SCALE, zs), ((x0 - m) * SCALE, (y1 + m) * SCALE, zs)]
        data.faces = [[0, 1, 2, 3]]
    # étendues réelles (ezdxf écrit $EXTMIN/$EXTMAX depuis msp.dxf à l'enregistrement)
    ext = ezbbox.extents(msp)
    msp.dxf.extmin, msp.dxf.extmax = tuple(ext.extmin), tuple(ext.extmax)
    # vue d'ouverture : isométrique depuis l'avant-gauche, ombrée, cadrée sur le bâtiment exporté
    styles = doc.rootdict.get("ACAD_VISUALSTYLE")
    ombre = styles["Shaded"] if styles is not None and "Shaded" in styles else None
    for vp in doc.viewports.get_config("*Active"):
        vp.dxf.target = ((x0 + x1) / 2 * SCALE, (y0 + y1) / 2 * SCALE, (z0 + z1) / 2 * SCALE)
        vp.dxf.direction = (-1.0, -1.0, 0.8)
        vp.dxf.center = (0.0, 0.0)
        vp.dxf.height = max(x1 - x0, y1 - y0, z1 - z0) * SCALE * 0.75
        vp.dxf.render_mode = 4
        if ombre is not None:                          # sans style visuel, ODA remet la vue en fil de fer
            vp.dxf.visual_style_handle = ombre.dxf.handle
    for lay in doc.layouts:                            # fenêtres des présentations : calque non imprimé
        if lay.name != "Model":
            for v in lay.query("VIEWPORT"):
                v.dxf.layer = "FENETRES-PRES"
    aud = doc.audit()
    doc.saveas(path)
    return doc, ext, aud


def find_odafc():
    """ODA File Converter du poste (copie portable d'abord), déclaré à ezdxf ; None s'il est introuvable."""
    try:
        exe = _chemins().configurer_ezdxf_odafc()
    except (Exception, SystemExit) as e:  # noqa: BLE001 - le DXF reste utile sans DWG
        print("  ODA File Converter :", e)
        return None
    if not exe:
        from ezdxf.addons import odafc
        exe = odafc.get_win_exec_path() or None
    return exe


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
        print(f"  {os.path.basename(cand)} : {'ouvert dans une application' if verrou else 'modifié'} -> on écrit à côté")
        k += 1
        cand = f"{base}_v{k}{ext}"
    return cand


def comptes_par_calque(doc):
    """{calque: [entités, sommets, faces, entités transparentes (code 440), {transparences}]} des MESH de l'espace
    objet."""
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


def main():
    build = _build_du_projet()
    if not os.path.exists(build):
        raise SystemExit("Script du modèle introuvable : %s" % build)
    nom = _option("--nom") or os.path.splitext(os.path.basename(build))[0].replace("build_", "", 1)
    sortie = os.path.abspath(_option("--sortie", HERE))
    os.makedirs(sortie, exist_ok=True)
    out_base = os.path.join(sortie, nom + "_3d" + ("_vegetation" if AVEC_VEG else "") + ("_m" if METRES else ""))
    json_path = os.path.join(tempfile.gettempdir(), "%s_geometrie_%d.json" % (nom, os.getpid()))
    blender_dump(build, json_path)
    data = json.load(open(json_path, encoding="utf-8"))
    os.remove(json_path)
    parts, meta = data["parts"], data["meta"]
    print("  Blender %s : construction %.0f s, total %.0f s ; D_SOL = %s" % (
        meta.get("blender", "?"), meta["t_build"], meta["t_total"],
        "%.4f m" % meta["D_SOL"] if meta["D_SOL"] is not None else "non défini (plus bas point)"))
    for nom, n_morceaux, n_sommets in meta.get("retires", []):
        print(f"  hors champ écarté : {nom} ({n_morceaux} morceau(x), {n_sommets} sommets)")
    for nom, n0, n1 in meta.get("soudes", []):
        print(f"  sommets soudés : {nom} {n0} -> {n1}")
    av = meta.get("aretes_vives", {})
    if ANGLE_PLI >= 180.0:
        print("  arêtes vives : AUCUNE (--angle-pli %g : tout soudé, comme avant le 2026-09-28)" % ANGLE_PLI)
    else:
        print("  arêtes vives (> %g°) : %d arêtes dédoublées dans %d objets (dont %d à plus de 2 faces) ; sommets "
              "%d -> %d" % (ANGLE_PLI, av.get("aretes", 0), av.get("objets", 0), av.get("non_manifold", 0),
                            av.get("sommets_avant", 0), av.get("sommets_apres", 0)))
    transp = defaultdict(lambda: [0, set()])
    for p in parts:
        t = transparence(p)
        if t > 0.0:
            transp[(p["mat"], t)][0] += 1
            transp[(p["mat"], t)][1].add(p["layer"])
        elif p["layer"] in CALQUES_VERRE:
            print(f"  AVERTISSEMENT : « {p['name']} » sur {p['layer']} reste OPAQUE (matériau « {p['mat']} », "
                  f"alpha {p.get('alpha')})")
    print("  transparence d'entité (code 440) :", "; ".join(
        f"{m} {t:.2f} ({n} MESH, {', '.join(sorted(ls))})" for (m, t), (n, ls) in sorted(transp.items())) or "aucune")
    dxf_path = chemin_libre(out_base + ".dxf")
    ref = os.path.getmtime(dxf_path) if os.path.exists(dxf_path) else None
    doc, ext, aud = build_dxf(parts, meta["D_SOL"], dxf_path)
    u = "m" if METRES else "po"
    print(f"DXF : {dxf_path}  ({os.path.getsize(dxf_path) / 2**20:.1f} Mio ; audit : {len(aud.errors)} erreur(s))")
    print(f"Étendue ({u}) : {[round(v, 1) for v in ext.extmin]} -> {[round(v, 1) for v in ext.extmax]}")
    exe = find_odafc()
    if not exe:
        print("DWG : ODA File Converter introuvable -> DXF seulement.")
        return
    from ezdxf.addons import odafc
    ezdxf.options.set("odafc-addon", "win_exec_path", exe)
    print("  ODA File Converter :", exe)
    dwg_path = chemin_libre(out_base + ".dwg", ref)
    odafc.export_dwg(doc, dwg_path, version="R2018", replace=True)
    d2 = odafc.readfile(dwg_path)
    hd = d2.header
    print(f"DWG : {dwg_path}  ({os.path.getsize(dwg_path) / 2**20:.2f} Mio ; relu par ODA, version {d2.dxfversion},"
          f" audit {len(d2.audit().errors)} erreur(s))")
    print(f"  en-tête : INSUNITS {hd.get('$INSUNITS')} LUNITS {hd.get('$LUNITS')} DIMSTYLE {hd.get('$DIMSTYLE')} "
          f"EXTMIN {[round(v, 1) for v in hd.get('$EXTMIN')]} EXTMAX {[round(v, 1) for v in hd.get('$EXTMAX')]}")
    print("  calques créés par ODA :", sorted({l.dxf.name for l in d2.layers} - {l.dxf.name for l in doc.layers})
          or "aucun")
    c = comptes_par_calque(d2)
    tot = [sum(v[i] for v in c.values()) for i in range(4)]
    print("  %-18s %8s %9s %9s  %s" % ("calque", "entités", "sommets", "faces", "transparentes (code 440 relu)"))
    for k in sorted(c, key=lambda k: -c[k][1]):
        print("  %-18s %8d %9d %9d  %s" % (k, *c[k][:3], ("%d : %s" % (c[k][3], sorted(c[k][4]))) if c[k][3] else "-"))
    print("  %-18s %8d %9d %9d  %d" % ("TOTAL", *tot))
    ecrites = sum(1 for e in doc.modelspace().query("MESH") if e.dxf.hasattr("transparency"))
    print(f"  transparences : {ecrites} écrites dans le DXF, {tot[3]} relues dans le DWG"
          + ("" if ecrites == tot[3] else "  <<< ÉCART : transparence perdue par ODA"))
    g2 = d2.materials.get("Global")
    methode = g2.dxf.get("diffuse_color_method", 0) if g2 is not None else None   # absent = 0 (défaut DXF)
    print(f"  matériau Global relu : diffus {'par objet' if methode == 0 else 'IMPOSÉ (méthode %s)' % methode}")
    print("  types :", dict(Counter(e.dxftype() for e in d2.modelspace())))
    # Ligne de synthèse, lisible par un script (test d'autonomie)
    print("EXPORT_AUTOCAD_OK " + json.dumps({"dxf": dxf_path, "dwg": dwg_path, "mesh": tot[0], "sommets": tot[1],
                                             "faces": tot[2], "transparents": tot[3], "angle_pli": ANGLE_PLI,
                                             "global_par_objet": methode == 0, "audit_dwg": len(d2.audit().errors),
                                             "version": d2.dxfversion, "oda": exe}, ensure_ascii=False))


if __name__ == "__main__":
    main()
