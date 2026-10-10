# -*- coding: utf-8 -*-
"""Recherche systématique des faces coplanaires qui se recouvrent (cause des taches noires de Cycles).

Modèle tiré de Garage_rouge_Blender\\verifier_coplanaires.py (voir modeles\\LISEZMOI.md). Aucun rendu, aucun GPU.

Deux façons de le lancer, sans aucun chemin écrit en dur :
  1. Avec le Python du poste, qui démarre lui-même Blender (trouvé par outils\\chemins.py) :
       python verifier_coplanaires.py build_projet.py [--rapport coplanaires_rapport.txt]
  2. Directement dans Blender, APRÈS le script du modèle (même session) :
       & $env:BM_BLENDER -b --factory-startup --python build_projet.py --python verifier_coplanaires.py

Collections contrôlées : toutes celles qui contiennent des maillages, sauf COLLECTIONS_EXCLUES (caméras, terrain,
végétation, éclairage) ; la variable COPLANAIRES_COLLECTIONS (« MURS-EXT,TOIT,… ») impose une liste.

Pour chaque paire de faces (objets différents, ou îlots différents d'un même objet) situées dans le même plan
(normales parallèles à 0,005 % près, écart ≤ 0,3 mm) : aire de recouvrement exacte (triangles découpés deux à deux).
  MÊME SENS    : les deux faces regardent du même côté -> tache noire possible si la zone est visible ;
  SENS OPPOSÉS : pièces jointives dos à dos (zone enfermée entre deux solides) -> sans effet.
Visibilité : on teste un point décalé de 0,4 mm devant la zone ; s'il est à l'intérieur d'un autre solide fermé,
la zone est « cachée ».
"""
import os
import sys

try:
    import bpy
except ImportError:          # lancé par le Python du poste : on démarre Blender, qui relira ce fichier
    bpy = None


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


def _lancer_blender():
    """Mode lanceur : python verifier_coplanaires.py build_projet.py [--rapport FICHIER]"""
    import subprocess
    args = sys.argv[1:]
    if not args or args[0].startswith("-"):
        raise SystemExit(__doc__)
    build = os.path.abspath(args[0])
    if not os.path.isfile(build):
        raise SystemExit("Script du modèle introuvable : %s" % build)
    ch = _chemins()
    blender = ch.blender_exe()
    # Environnement de la copie portable de Blender (ressources système, cache CUDA, BLENDER_USER_* retirées),
    # si le module de chemins le fournit ; sinon l'environnement courant.
    env = ch.env_blender() if callable(getattr(ch, "env_blender", None)) else dict(os.environ)
    if "--rapport" in args:
        env["COPLANAIRES_RAPPORT"] = os.path.abspath(args[args.index("--rapport") + 1])
    cmd = [blender, "-b", "--factory-startup", "--python", build, "--python", os.path.abspath(__file__)]
    print("Blender :", blender)
    r = subprocess.run(cmd, env=env, cwd=os.path.dirname(build))
    raise SystemExit(r.returncode)


if bpy is None:
    if __name__ == "__main__":
        _lancer_blender()
    raise SystemExit("verifier_coplanaires.py : à lancer comme script (python ou Blender), pas à importer.")

import math  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

COLLECTIONS_EXCLUES = {"CAMERAS", "CAMERA", "TERRAIN", "VEGETATION", "ECLAIRAGE", "LUMIERES", "STUDIO"}
if os.environ.get("COPLANAIRES_COLLECTIONS"):
    COLLS = [c.strip() for c in os.environ["COPLANAIRES_COLLECTIONS"].split(",") if c.strip()]
else:
    COLLS = sorted(c.name for c in bpy.data.collections
                   if c.name.upper() not in COLLECTIONS_EXCLUES and not c.name.startswith("_")
                   and any(o.type == "MESH" for o in c.objects))
bpy.context.view_layer.update()   # matrix_world à jour pour les objets créés par script (piège CLAUDE.md)
TOL_D = 0.0003        # m (au-delà, ce sont des couches minces réelles, sans effet)
TOL_N = 0.99995
AIRE_MIN = 2e-6       # m² (2 mm²)

faces = []            # (objet, îlot, normale, [triangles 3D])
bvh = {}
objets = {}           # un objet n'est vu qu'une fois, même s'il est dans une collection et sa sous-collection
for cn in COLLS:
    coll = bpy.data.collections.get(cn)
    if coll is None:
        continue
    for ob in coll.all_objects:
        if ob.type == "MESH" and not ob.name.startswith("_gabarit"):
            objets.setdefault(ob.name, ob)
print("Collections contrôlées :", COLLS, "|", len(objets), "objets maillés")
for ob in objets.values():
    if True:  # corps d'origine inchangé (même indentation que la boucle par collection du garage)
        me = ob.data
        mw = ob.matrix_world
        co = np.array([tuple(mw @ v.co) for v in me.vertices])
        parent = list(range(len(me.vertices)))

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a
        for e in me.edges:
            a, b = find(e.vertices[0]), find(e.vertices[1])
            if a != b:
                parent[a] = b
        me.calc_loop_triangles()
        tris = {}
        for lt in me.loop_triangles:
            tris.setdefault(lt.polygon_index, []).append(co[list(lt.vertices)])
        nm = mw.to_3x3().inverted().transposed()
        for p in me.polygons:
            n = (nm @ p.normal)
            if n.length < 1e-9:
                continue
            n = np.array(tuple(n.normalized()))
            if p.index in tris:
                faces.append((ob.name, find(p.vertices[0]), n, tris[p.index]))
        verts = [tuple(v) for v in co]
        par_ilot = {}
        for p in me.polygons:
            par_ilot.setdefault(find(p.vertices[0]), []).append(tuple(p.vertices))
        for il, polys in par_ilot.items():          # un solide par îlot (une pièce d'un objet peut en cacher une autre)
            if len(polys) >= 4:
                bvh[(ob.name, il)] = BVHTree.FromPolygons(verts, polys)

F = len(faces)
N = np.array([f[2] for f in faces])
cl = -np.ones(F, dtype=int)
sg = np.zeros(F)
reps = []
for i in range(F):
    if cl[i] >= 0:
        continue
    dots = N @ N[i]
    sel = (np.abs(dots) > TOL_N) & (cl < 0)
    cl[sel] = len(reps)
    sg[sel] = np.sign(dots[sel])
    reps.append(N[i])


def area(poly):
    s = 0.0
    for k in range(len(poly)):
        x1, y1 = poly[k]
        x2, y2 = poly[(k + 1) % len(poly)]
        s += x1 * y2 - x2 * y1
    return s / 2.0


def clip(subj, clipper):
    out = subj
    for k in range(len(clipper)):
        a, b = clipper[k], clipper[(k + 1) % len(clipper)]
        inp, out = out, []
        if not inp:
            break

        def inside(p):
            return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) >= 0.0

        def inter(p, q):
            x1, y1 = p
            x2, y2 = q
            x3, y3 = a
            x4, y4 = b
            den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
            if abs(den) < 1e-20:
                return q
            t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
            return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
        s = inp[-1]
        for e in inp:
            if inside(e):
                if not inside(s):
                    out.append(inter(s, e))
                out.append(e)
            elif inside(s):
                out.append(inter(s, e))
            s = e
    return out


def dedans(pt, sauf):
    """Point à l'intérieur d'un solide fermé (parité des traversées d'un rayon), autre que `sauf`."""
    for cle, t in bvh.items():
        if cle in sauf:
            continue
        name = cle[0]
        n_hits, o, d = 0, Vector(pt), Vector((0.3141, 0.5926, 0.7415)).normalized()
        for _ in range(64):
            loc, nrm, idx, dist = t.ray_cast(o, d)
            if loc is None:
                break
            n_hits += 1
            o = loc + d * 1e-5
        if n_hits % 2 == 1:
            return name
    return None


resultats = []
for k, r in enumerate(reps):
    idx = np.where(cl == k)[0]
    if len(idx) < 2:
        continue
    r = np.array(r)
    d = np.array([float(r @ faces[i][3][0][0]) for i in idx])
    order = np.argsort(d)
    idx, d = idx[order], d[order]
    u = np.cross(r, [1.0, 0.0, 0.0] if abs(r[0]) < 0.9 else [0.0, 1.0, 0.0])
    u /= np.linalg.norm(u)
    v = np.cross(r, u)
    proj = {}

    def P2(i):
        if i not in proj:
            tl = []
            for t in faces[i][3]:
                q = [(float(p @ u), float(p @ v)) for p in t]
                if area(q) < 0:
                    q = q[::-1]
                tl.append(q)
            xs = [p[0] for q in tl for p in q]
            ys = [p[1] for q in tl for p in q]
            proj[i] = (tl, (min(xs), max(xs), min(ys), max(ys)))
        return proj[i]
    for a in range(len(idx)):
        for b in range(a + 1, len(idx)):
            if d[b] - d[a] > TOL_D:
                break
            i, j = idx[a], idx[b]
            fi, fj = faces[i], faces[j]
            if fi[0] == fj[0] and fi[1] == fj[1]:
                continue
            ti, bi = P2(i)
            tj, bj = P2(j)
            if bi[1] <= bj[0] or bj[1] <= bi[0] or bi[3] <= bj[2] or bj[3] <= bi[2]:
                continue
            aire, best, cen = 0.0, 0.0, None
            for qa in ti:
                for qb in tj:
                    c = clip(qa, qb)
                    if len(c) >= 3:
                        s = abs(area(c))
                        aire += s
                        if s > best:
                            best = s
                            cx = sum(p[0] for p in c) / len(c)
                            cy = sum(p[1] for p in c) / len(c)
                            cen = (cx, cy)
            if aire < AIRE_MIN:
                continue
            meme = sg[i] == sg[j]
            p3 = r * d[a] + u * cen[0] + v * cen[1]
            n_vue = fi[2]                       # côté d'où la face i est vue
            cache = dedans(tuple(p3 + n_vue * 0.0004), {(fi[0], fi[1]), (fj[0], fj[1])}) if meme else None
            resultats.append((meme, aire, fi[0], fj[0], d[b] - d[a], p3, fi[2], cache))

LIGNES = []


def dire(texte):
    print(texte)
    LIGNES.append(texte)


resultats.sort(key=lambda t: (not t[0], t[7] is not None, -t[1]))
n_meme = sum(1 for t in resultats if t[0])
n_vis = sum(1 for t in resultats if t[0] and t[7] is None)
dire("\n=== Faces coplanaires qui se recouvrent : %d paires (%d de MÊME SENS dont %d VISIBLES, %d dos à dos) ==="
     % (len(resultats), n_meme, n_vis, len(resultats) - n_meme))
groupes = {}
for meme, aire, a, b, gap, p3, n, cache in resultats:
    etat = ("MÊME SENS - VISIBLE" if cache is None else "même sens - caché") if meme else "dos à dos"
    g = groupes.setdefault((etat, tuple(sorted((a, b)))), [0, 0.0, p3, n, cache])
    g[0] += 1
    g[1] += aire
dire("Par paire d'objets (nombre de paires de faces, aire totale, un exemple) :")
for (etat, (a, b)), (nb, aire, p3, n, cache) in sorted(
        groupes.items(), key=lambda t: (t[0][0] != "MÊME SENS - VISIBLE", t[0][0] == "dos à dos", -t[1][1])):
    dire("  %-19s %4d x %9.1f cm²  n=(%+.2f,%+.2f,%+.2f)  ex. (%.3f, %.3f, %.3f)%s  |  %s  /  %s"
         % (etat, nb, aire * 1e4, n[0], n[1], n[2], p3[0], p3[1], p3[2],
            ("  [dans %s]" % cache) if cache else "", a, b))
# Ligne de synthèse, lisible par un script (test d'autonomie, contrôle avant rendu)
dire("COPLANAIRES_RESUME paires=%d meme_sens=%d visibles=%d dos_a_dos=%d objets=%d"
     % (len(resultats), n_meme, n_vis, len(resultats) - n_meme, len(objets)))
if os.environ.get("COPLANAIRES_RAPPORT"):
    with open(os.environ["COPLANAIRES_RAPPORT"], "w", encoding="utf-8") as fh:
        fh.write("\n".join(LIGNES) + "\n")
    print("Rapport écrit :", os.environ["COPLANAIRES_RAPPORT"])
