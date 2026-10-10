# -*- coding: utf-8 -*-
"""extraire_blend.py — tourne DANS Blender : sort la géométrie d'un .blend pour le PDF 3D.

    blender -b --factory-startup <fichier.blend> --python extraire_blend.py -- <options.json>

Lancé par pdf_3d.py (ne pas l'appeler à la main, sauf pour déboguer). LECTURE SEULE : le .blend
n'est jamais enregistré ; tout ce qui est modifié ici (visibilités, exclusions) l'est en mémoire.

CE QUI SORT
  <travail>/scene.json : objets (nom, matrice monde 4x4 en colonnes, maillage, matériaux par
      tranche, collections, propriétés personnalisées), maillages DISTINCTS (comptes et
      positions dans le binaire), matériaux (couleur, opacité), caméras, collections, écartés.
  <travail>/scene.bin  : pour chaque maillage distinct, à la suite et en little-endian :
      positions float32 (nv x 3, repère LOCAL de l'objet, en unités de sortie),
      indices uint32 (nt x 3), tranche de matériau uint32 (nt),
      normales float32 (nn x 3), indices de normale uint32 (nt x 3).

RÈGLES (toutes dites dans le journal)
  - on prend ce que le RENDU montrerait : objets et collections non masqués au rendu ; les
    modificateurs sont appliqués (maillage évalué), avec leurs réglages de rendu ;
  - les objets invisibles pour la caméra (aides d'éclairage) sont écartés, sauf option ;
  - les instances de particules sont écartées, sauf option (une forêt = des millions de faces) ;
  - deux objets qui portent le même maillage (même bloc de données sans modificateur, ou même
    contenu) PARTAGENT une seule ressource : c'est ce qui rend le PDF 3D léger ;
  - les triangles dégénérés et les sommets orphelins sont retirés (le lecteur cadre sur l'étendue).
"""
import hashlib
import json
import math
import os
import sys
import time

import bpy
import numpy as np

T0 = time.time()
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if not argv:
    print("EXTRACTION_ERREUR options.json manquant")
    sys.exit(2)
with open(argv[0], encoding="utf-8") as f:
    OPT = json.load(f)

TRAVAIL = OPT["travail"]
EXCLURE = set(OPT.get("exclure_collections") or [])
INCLURE = set(OPT.get("inclure_collections") or [])
AVEC_PARTICULES = bool(OPT.get("particules"))
AVEC_CACHES = bool(OPT.get("caches"))
ECHELLE_SORTIE = float(OPT.get("metres_par_unite_sortie") or 1.0)   # 1 = mètre, 0.001 = mm
TYPES_MAILLABLES = {"MESH", "CURVE", "SURFACE", "FONT", "META"}
RACINE = "(racine de la scène)"

sc = bpy.context.scene
vl = bpy.context.view_layer
journal = []


def dire(msg):
    journal.append(msg)
    print("[extraction] " + msg)


# ------------------------------------------------------------------ unités du .blend
us = sc.unit_settings
metres_par_ub = float(us.scale_length) if us.system != "NONE" else 1.0
if metres_par_ub <= 0:
    metres_par_ub = 1.0
FACTEUR = metres_par_ub / ECHELLE_SORTIE      # unité Blender -> unité de sortie
dire("unités du .blend : système %s, %.6g m par unité Blender ; sortie : %.6g m par unité ; facteur %.6g"
     % (us.system, metres_par_ub, ECHELLE_SORTIE, FACTEUR))

# ------------------------------------------------------------------ collections
parent_de = {}          # nom de collection -> nom du parent ('' = racine de la scène)


def parcourir(col, parent):
    for c in col.children:
        if c.name not in parent_de:
            parent_de[c.name] = parent
            parcourir(c, c.name)


parcourir(sc.collection, "")


def chemin_collection(nom):
    out = []
    while nom:
        out.append(nom)
        nom = parent_de.get(nom, "")
    return out[::-1]


def gardee(nom):
    """La collection (par son nom) est-elle retenue, compte tenu de ses ancêtres ?"""
    ch = chemin_collection(nom)
    if any(a in EXCLURE for a in ch):
        return False
    if INCLURE and not any(a in INCLURE for a in ch):
        return False
    return True


inconnues = sorted((EXCLURE | INCLURE) - set(parent_de))
if inconnues:
    dire("ATTENTION collections demandées mais absentes du .blend : %s" % ", ".join(inconnues))
descendantes = {n: [d for d in parent_de if n in chemin_collection(d)] for n in parent_de}
non_gardees = sorted(n for n in parent_de if not gardee(n))


def couches(lc):
    yield lc
    for c in lc.children:
        yield from couches(c)


# visibilité « comme au rendu », en mémoire seulement
for c in bpy.data.collections:
    try:
        c.hide_viewport = c.hide_render
    except Exception:
        pass
deja_exclues_couche = []
for lc in list(couches(vl.layer_collection)):
    if lc.collection is sc.collection:
        continue
    if lc.exclude:
        deja_exclues_couche.append(lc.name)
        continue
    lc.hide_viewport = False
    nom = lc.collection.name
    # exclure de la couche AVANT l'évaluation ce dont rien n'est gardé : ce n'est jamais calculé
    if nom in parent_de and not any(gardee(d) for d in descendantes.get(nom, [nom])):
        lc.exclude = True
if deja_exclues_couche:
    dire("collections déjà exclues de la couche de vue dans le .blend (non rendues) : %s"
         % ", ".join(sorted(set(deja_exclues_couche))))

n_modifs = 0
for ob in sc.objects:
    try:
        ob.hide_viewport = ob.hide_render
        if ob.name in vl.objects:
            ob.hide_set(False)
    except Exception:
        pass
    for md in ob.modifiers:
        try:
            if md.show_viewport != md.show_render:
                md.show_viewport = md.show_render
                n_modifs += 1
            if md.type in {"SUBSURF", "MULTIRES"} and md.levels != md.render_levels:
                md.levels = md.render_levels
                n_modifs += 1
        except Exception:
            pass
if n_modifs:
    dire("%d réglage(s) de modificateur alignés sur ceux du rendu (en mémoire)" % n_modifs)

vl.update()
dg = bpy.context.evaluated_depsgraph_get()

# ------------------------------------------------------------------ matériaux


def srgb(c):
    return 12.92 * c if c <= 0.0031308 else 1.055 * (max(c, 0.0) ** (1 / 2.4)) - 0.055


def lire_materiau(m):
    """Couleur de base et opacité d'un matériau Blender, avec leur provenance."""
    d = {"nom": m.name}
    couleur = [float(x) for x in m.diffuse_color[:3]]
    alpha_affichage = float(m.diffuse_color[3])
    source = "couleur d'affichage"
    opacite = 1.0
    metal = 0.0
    rugosite = 0.5
    verre = False
    arbre = m.node_tree if getattr(m, "node_tree", None) else None
    if arbre:
        principled = None
        for n in arbre.nodes:
            if n.type == "BSDF_PRINCIPLED" and principled is None:
                principled = n
            if n.type in {"BSDF_GLASS", "BSDF_REFRACTION", "BSDF_TRANSPARENT"}:
                verre = True
        if principled is not None:
            e = {s.name: s for s in principled.inputs}
            bc = e.get("Base Color")
            if bc is not None and not bc.is_linked:
                couleur = [float(x) for x in bc.default_value[:3]]
                source = "couleur de base du Principled"
            elif bc is not None:
                source = "couleur d'affichage (la couleur de base du Principled vient d'une texture)"
            a = e.get("Alpha")
            if a is not None and not a.is_linked:
                opacite = float(a.default_value)
            t = e.get("Transmission Weight") or e.get("Transmission")
            if t is not None and not t.is_linked and float(t.default_value) > 0.5:
                verre = True
            mt = e.get("Metallic")
            if mt is not None and not mt.is_linked:
                metal = float(mt.default_value)
            r = e.get("Roughness")
            if r is not None and not r.is_linked:
                rugosite = float(r.default_value)
    opacite = min(opacite, alpha_affichage)
    if verre:
        opacite = min(opacite, 0.35)
    d["couleur_lineaire"] = [round(x, 5) for x in couleur]
    d["couleur"] = [round(min(1.0, max(0.0, srgb(x))), 5) for x in couleur]
    d["opacite"] = round(min(1.0, max(0.0, opacite)), 4)
    d["metal"] = round(metal, 3)
    d["rugosite"] = round(rugosite, 3)
    d["verre"] = verre
    d["source"] = source
    return d


SANS_MATERIAU = "(sans matériau)"
materiaux = {}


def enregistrer_materiau(m):
    if m is None:
        if SANS_MATERIAU not in materiaux:
            materiaux[SANS_MATERIAU] = {"nom": SANS_MATERIAU, "couleur_lineaire": [0.6, 0.6, 0.6],
                                        "couleur": [round(srgb(0.6), 5)] * 3, "opacite": 1.0,
                                        "metal": 0.0, "rugosite": 0.5, "verre": False,
                                        "source": "aucun matériau : gris neutre"}
        return SANS_MATERIAU
    if m.name not in materiaux:
        materiaux[m.name] = lire_materiau(m)
    return m.name


# ------------------------------------------------------------------ maillages
bin_morceaux = []
bin_taille = 0
maillages = []                 # descriptions (ordre = indice)
positions_mem = []             # positions float64 de chaque maillage distinct (boîte exacte)
par_cle_donnee = {}            # (nom du bloc, nb d'emplacements) -> (indice, tranches utilisées)
par_empreinte = {}             # sha1 du contenu -> indice
ecartes = {"particules": 0, "caches_au_rendu": [], "invisibles_camera": [], "sans_face": [],
           "hors_collections": 0, "types_non_maillables": {}, "erreurs": [],
           "triangles_degeneres": 0, "sommets_orphelins": 0}


def ajouter_bin(a):
    global bin_taille
    b = np.ascontiguousarray(a).tobytes()
    pos = bin_taille
    bin_morceaux.append(b)
    bin_taille += len(b)
    return pos


def maillage_de(ob_eval, nom_donnee):
    """Rend (indice du maillage distinct, tranches de matériau utilisées) ou None si aucune face."""
    me = ob_eval.to_mesh()
    try:
        me.calc_loop_triangles()
        nt = len(me.loop_triangles)
        nv = len(me.vertices)
        if nt < 1 or nv < 3:
            return None
        co = np.empty(nv * 3, np.float32)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3).astype(np.float64) * FACTEUR
        tri = np.empty(nt * 3, np.int32)
        me.loop_triangles.foreach_get("vertices", tri)
        tri = tri.reshape(-1, 3).astype(np.int64)
        coins = np.empty(nt * 3, np.int32)
        me.loop_triangles.foreach_get("loops", coins)
        mi = np.empty(nt, np.int32)
        me.loop_triangles.foreach_get("material_index", mi)
        nl = len(me.loops)
        cn = np.empty(nl * 3, np.float32)
        try:
            me.corner_normals.foreach_get("vector", cn)
        except Exception:
            cn = None                       # repli plus bas : normale géométrique du triangle
        # triangles dégénérés (deux coins sur le même sommet) : retirés
        bon = (tri[:, 0] != tri[:, 1]) & (tri[:, 1] != tri[:, 2]) & (tri[:, 0] != tri[:, 2])
        if not bon.all():
            ecartes["triangles_degeneres"] += int((~bon).sum())
            tri = tri[bon]
            mi = mi[bon]
            coins = coins.reshape(-1, 3)[bon].reshape(-1)
        nt = len(tri)
        if nt < 1:
            return None
        if not np.isfinite(co).all():
            raise ValueError("coordonnées non finies")
        # sommets orphelins : on ne garde que ceux qu'une face emploie
        utiles, inverse = np.unique(tri.reshape(-1), return_inverse=True)
        ecartes["sommets_orphelins"] += int(len(co) - len(utiles))
        co = co[utiles]
        tri = np.asarray(inverse).reshape(-1, 3)
        # normales par coin, dédoublonnées
        if cn is not None:
            n = cn.reshape(-1, 3)[coins].astype(np.float64)
        else:
            a = co[tri[:, 0]]
            fn = np.cross(co[tri[:, 1]] - a, co[tri[:, 2]] - a)
            n = np.repeat(fn, 3, axis=0)
        lon = np.linalg.norm(n, axis=1)
        lon[lon == 0] = 1.0
        n = n / lon[:, None]
        nq = np.round(n, 4) + 0.0          # +0.0 : pas de zéro négatif
        nuniq, ninv = np.unique(nq, axis=0, return_inverse=True)
        ninv = np.asarray(ninv).reshape(-1, 3)
        # tranches de matériau compactées
        tr_utiles, tr_inv = np.unique(mi, return_inverse=True)
        co32 = co.astype(np.float32)
        tri32 = tri.astype(np.uint32)
        sh32 = np.asarray(tr_inv).reshape(-1).astype(np.uint32)
        n32 = nuniq.astype(np.float32)
        ni32 = ninv.astype(np.uint32)
        h = hashlib.sha1()
        for a in (co32, tri32, sh32, n32, ni32):
            h.update(np.ascontiguousarray(a).tobytes())
            h.update(b"|")
        emp = h.hexdigest()
        tranches = [int(x) for x in tr_utiles]
        if emp in par_empreinte:
            return par_empreinte[emp], tranches
        i = len(maillages)
        par_empreinte[emp] = i
        d = {
            "nom": nom_donnee, "sha1": emp,
            "sommets": int(len(co32)), "triangles": int(nt), "normales": int(len(n32)),
            "tranches": int(len(tr_utiles)),
            "pos_positions": ajouter_bin(co32), "pos_indices": ajouter_bin(tri32),
            "pos_tranches": ajouter_bin(sh32), "pos_normales": ajouter_bin(n32),
            "pos_indices_normales": ajouter_bin(ni32),
        }
        maillages.append(d)
        positions_mem.append(co32.astype(np.float64))
        return i, tranches
    finally:
        ob_eval.to_mesh_clear()


# ------------------------------------------------------------------ objets


def proprietes(ob):
    out = {}
    for k in ob.keys():
        if k.startswith("_"):
            continue
        v = ob[k]
        if isinstance(v, (bool, int, float, str)):
            out[k] = v
    return out


def collections_de(ob):
    """Noms des collections de la scène qui contiennent directement l'objet."""
    return [c.name for c in ob.users_collection if c.name in parent_de]


def collection_principale(ob):
    """Chemin (liste de noms) de la collection RETENUE la plus profonde qui porte l'objet."""
    candidats = [n for n in collections_de(ob) if gardee(n)]
    if not candidats:
        return []
    candidats.sort(key=lambda n: (len(chemin_collection(n)), n))
    return chemin_collection(candidats[-1])


def objet_garde(ob):
    cols = collections_de(ob)
    if not cols:                       # objet posé à la racine de la scène
        return not INCLURE
    return any(gardee(n) for n in cols)


objets = []
noms_pris = set()
boite = [np.array([np.inf] * 3), np.array([-np.inf] * 3)]
compte_instances = {}

for inst in dg.object_instances:
    ob = inst.object
    orig = ob.original
    if ob.type not in TYPES_MAILLABLES:
        if ob.type not in {"CAMERA", "LIGHT", "EMPTY", "LIGHT_PROBE", "SPEAKER", "ARMATURE", "LATTICE"}:
            ecartes["types_non_maillables"][ob.type] = ecartes["types_non_maillables"].get(ob.type, 0) + 1
        continue
    est_instance = bool(inst.is_instance)
    porteur = inst.parent.original if (est_instance and inst.parent is not None) else orig
    if est_instance:
        if inst.particle_system is not None and not AVEC_PARTICULES:
            ecartes["particules"] += 1
            continue
    else:
        if not inst.show_self:
            continue
    if not objet_garde(porteur):
        ecartes["hors_collections"] += 1
        continue
    if not AVEC_CACHES:
        if porteur.hide_render or orig.hide_render:
            if len(ecartes["caches_au_rendu"]) < 200:
                ecartes["caches_au_rendu"].append(porteur.name)
            continue
        if not getattr(porteur, "visible_camera", True) or not getattr(orig, "visible_camera", True):
            if len(ecartes["invisibles_camera"]) < 200:
                ecartes["invisibles_camera"].append(porteur.name)
            continue
    # clé de partage : même bloc de données, sans modificateur ni clé de forme
    simple = (orig.type == "MESH" and len(orig.modifiers) == 0
              and not (orig.data.shape_keys and len(orig.data.shape_keys.key_blocks) > 1))
    cle = (orig.data.name, len(orig.material_slots)) if simple else None
    try:
        if cle is not None and cle in par_cle_donnee:
            r = par_cle_donnee[cle]
        else:
            r = maillage_de(ob, orig.data.name)
            if cle is not None:
                par_cle_donnee[cle] = r
    except Exception as e:                      # un objet illisible n'emporte pas tout le modèle
        ecartes["erreurs"].append("%s : %s" % (orig.name, e))
        continue
    if r is None:
        if len(ecartes["sans_face"]) < 200:
            ecartes["sans_face"].append(orig.name)
        continue
    i_maillage, tranches = r
    # matériaux par tranche (les liaisons « objet » priment : on lit les emplacements de l'objet)
    mats = []
    emplacements = ob.material_slots
    for t in tranches:
        m = emplacements[t].material if t < len(emplacements) else None
        mats.append(enregistrer_materiau(m.original if m is not None else None))
    # nom unique
    if est_instance:
        base = "%s ‹%s›" % (orig.name, porteur.name)
        k = compte_instances.get(base, 0) + 1
        compte_instances[base] = k
        nom = "%s #%d" % (base, k)
    else:
        nom = orig.name
    while nom in noms_pris:
        nom += "'"
    noms_pris.add(nom)
    M = np.array(inst.matrix_world, dtype=np.float64)        # 4x4, lignes
    M[:3, 3] *= FACTEUR
    w = positions_mem[i_maillage] @ M[:3, :3].T + M[:3, 3]   # boîte EXACTE, tous les sommets
    boite[0] = np.minimum(boite[0], w.min(axis=0))
    boite[1] = np.maximum(boite[1], w.max(axis=0))
    objets.append({
        "nom": nom,
        "objet": orig.name,
        "instance_de": porteur.name if est_instance else None,
        "type": orig.type,
        "maillage": i_maillage,
        "matrice": [float(M[r_, c_]) for c_ in range(4) for r_ in range(4)],   # colonnes d'abord
        "materiaux": mats,
        "collections": collection_principale(porteur),
        "proprietes": proprietes(porteur if est_instance else orig),
        "boite": [[float(x) for x in w.min(axis=0)], [float(x) for x in w.max(axis=0)]],
    })

# ------------------------------------------------------------------ caméras
cameras = []
for ob in sc.objects:
    if ob.type != "CAMERA":
        continue
    cam = ob.data
    M = np.array(ob.matrix_world, dtype=np.float64)
    rx = sc.render.resolution_x * sc.render.pixel_aspect_x
    ry = sc.render.resolution_y * sc.render.pixel_aspect_y
    d = {
        "nom": ob.name,
        "position": [float(x) * FACTEUR for x in M[:3, 3]],
        "droite": [float(x) for x in M[:3, 0]],
        "haut": [float(x) for x in M[:3, 1]],
        "regard": [float(-x) for x in M[:3, 2]],          # une caméra Blender regarde vers -Z local
        "type": cam.type,
        "rendu": [int(sc.render.resolution_x), int(sc.render.resolution_y)],
        "decentrement": [float(cam.shift_x), float(cam.shift_y)],
        "active": sc.camera is ob,
    }
    fit = cam.sensor_fit
    if fit == "AUTO":
        fit = "HORIZONTAL" if rx >= ry else "VERTICAL"
    d["ajustement"] = fit
    if cam.type == "ORTHO":
        d["echelle_ortho"] = float(cam.ortho_scale) * FACTEUR
    else:
        if fit == "HORIZONTAL":
            ah = 2 * math.atan(cam.sensor_width / (2 * cam.lens))
            av = 2 * math.atan(math.tan(ah / 2) * ry / rx)
        else:
            av = 2 * math.atan(cam.sensor_height / (2 * cam.lens))
            ah = 2 * math.atan(math.tan(av / 2) * rx / ry)
        d["champ_h_deg"] = math.degrees(ah)
        d["champ_v_deg"] = math.degrees(av)
    cameras.append(d)

# ------------------------------------------------------------------ bilan par collection
par_col = {}
for o in objets:
    cle_col = o["collections"][0] if o["collections"] else RACINE
    e = par_col.setdefault(cle_col, {"objets": 0, "triangles": 0})
    e["objets"] += 1
    e["triangles"] += maillages[o["maillage"]]["triangles"]

tri_total = sum(maillages[o["maillage"]]["triangles"] for o in objets)
tri_distincts = sum(m["triangles"] for m in maillages)

os.makedirs(TRAVAIL, exist_ok=True)
with open(os.path.join(TRAVAIL, "scene.bin"), "wb") as f:
    for b in bin_morceaux:
        f.write(b)

proprietes_scene = {}
for k in sc.keys():
    v = sc[k]
    if isinstance(v, (bool, int, float, str)) and not k.startswith("_"):
        proprietes_scene[k] = v

scene = {
    "format": "pdf3d-scene-1",
    "blend": bpy.data.filepath,
    "blender": bpy.app.version_string,
    "scene": sc.name,
    "metres_par_unite_blender": metres_par_ub,
    "metres_par_unite_sortie": ECHELLE_SORTIE,
    "proprietes_scene": proprietes_scene,
    "collections": [{"nom": n, "chemin": chemin_collection(n), "gardee": gardee(n)} for n in parent_de],
    "collections_non_gardees": non_gardees,
    "objets": objets,
    "maillages": maillages,
    "materiaux": list(materiaux.values()),
    "cameras": cameras,
    "boite": [[float(x) for x in boite[0]], [float(x) for x in boite[1]]] if objets else None,
    "triangles": tri_total,
    "triangles_distincts": tri_distincts,
    "par_collection": par_col,
    "ecartes": ecartes,
    "octets_bin": bin_taille,
    "journal": journal,
    "duree_s": round(time.time() - T0, 2),
}
dire("%d objet(s), %d maillage(s) distinct(s), %d triangles posés (%d dans les maillages distincts), %d matériau(x), %d caméra(s)"
     % (len(objets), len(maillages), tri_total, tri_distincts, len(materiaux), len(cameras)))
if ecartes["particules"]:
    dire("%d instance(s) de particules écartées (option --particules pour les garder)" % ecartes["particules"])
if ecartes["caches_au_rendu"]:
    dire("%d objet(s) masqués au rendu écartés" % len(ecartes["caches_au_rendu"]))
if ecartes["invisibles_camera"]:
    dire("%d objet(s) invisibles pour la caméra écartés" % len(ecartes["invisibles_camera"]))
if ecartes["erreurs"]:
    dire("%d objet(s) illisibles : %s" % (len(ecartes["erreurs"]), "; ".join(ecartes["erreurs"][:5])))
with open(os.path.join(TRAVAIL, "scene.json"), "w", encoding="utf-8", newline="\n") as f:
    json.dump(scene, f, ensure_ascii=False)

print("EXTRACTION_OK %s" % os.path.join(TRAVAIL, "scene.json"))
