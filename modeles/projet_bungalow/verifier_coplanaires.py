# -*- coding: utf-8 -*-
"""Maison Bungalow — recherche des faces coplanaires qui se recouvrent (cause des taches noires de Cycles).
MODÈLE tiré de Maison_Bungalow_Blender (version finale du 2026-09-25 ; voir modeles\\LISEZMOI.md), lui-même adapté
de Garage_rouge_Blender\\verifier_coplanaires.py. Version plus simple, qui lance Blender elle-même :
modeles\\rendu_controles\\verifier_coplanaires.py.

À lancer APRÈS build_bungalow.py, dans le même Blender (aucun rendu). Blender portable : $env:BM_BLENDER (posé par
outils\\chemins.cmd ou chemins.ps1), sinon <racine>\\outils\\blender\\blender.exe :
  & $env:BM_BLENDER -b --factory-startup `
      --python build_bungalow.py --python verifier_coplanaires.py -- --sans-vegetation --no-json

Pour chaque paire de faces (objets différents, ou îlots différents d'un même objet) situées dans le même plan
(normales parallèles à 0,005 % près, écart ≤ 0,3 mm) : aire de recouvrement exacte (triangles découpés deux à deux).
  MÊME SENS    : les deux faces regardent du même côté -> tache noire possible si la zone est visible ;
  SENS OPPOSÉS : pièces jointives dos à dos (zone enfermée entre deux solides) -> sans effet.
Visibilité : on teste un point décalé de 0,4 mm devant la zone ; s'il est à l'intérieur d'un autre solide fermé,
la zone est « cachée ». Le terrain et la végétation sont exclus ; les fonds intérieurs (CONTEXTE) sont inclus.
Sortie : résumé à l'écran, détail dans coplanaires_rapport.txt (à côté du script).
"""
import os

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

COLLS = ["MURS-EXT", "MURS-INT", "OUVERTURES", "TOIT", "MENUISERIE", "VITRAGE", "DALLE", "FONDATION", "ESCALIERS",
         "MOBILIER", "INDICATIF", "CONTEXTE"]
EXCLUS = ("_gabarit", "Arbre", "Conifère", "Arbuste", "Terrain", "Rue ", "Clôtures", "Gazon")
TOL_D = 0.0003        # m
TOL_N = 0.99995
AIRE_MIN = 2e-6       # m² (2 mm²)
FT = 0.3048

bpy.context.view_layer.update()
faces = []            # (objet, îlot, normale, [triangles 3D])
bvh = {}
for cn in COLLS:
    coll = bpy.data.collections.get(cn)
    if coll is None:
        continue
    for ob in coll.all_objects:
        if ob.type != "MESH" or ob.name.startswith(EXCLUS):
            continue
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
        for il, polys in par_ilot.items():
            if len(polys) >= 4:
                bvh[(ob.name, il)] = BVHTree.FromPolygons(verts, polys)

F = len(faces)
print(f"Faces examinées : {F} ; solides : {len(bvh)}")
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
    for cle, t in bvh.items():
        if cle in sauf:
            continue
        n_hits, o, d = 0, Vector(pt), Vector((0.3141, 0.5926, 0.7415)).normalized()
        for _ in range(64):
            loc, nrm, idx, dist = t.ray_cast(o, d)
            if loc is None:
                break
            n_hits += 1
            o = loc + d * 1e-5
        if n_hits % 2 == 1:
            return cle[0]
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
            aire_, best, cen = 0.0, 0.0, None
            for qa in ti:
                for qb in tj:
                    c = clip(qa, qb)
                    if len(c) >= 3:
                        s = abs(area(c))
                        aire_ += s
                        if s > best:
                            best = s
                            cen = (sum(p[0] for p in c) / len(c), sum(p[1] for p in c) / len(c))
            if aire_ < AIRE_MIN:
                continue
            meme = sg[i] == sg[j]
            p3 = r * d[a] + u * cen[0] + v * cen[1]
            cache = dedans(tuple(p3 + fi[2] * 0.0004), {(fi[0], fi[1]), (fj[0], fj[1])}) if meme else None
            resultats.append((meme, aire_, fi[0], fj[0], d[b] - d[a], p3, fi[2], cache))

resultats.sort(key=lambda t: (not t[0], t[7] is not None, -t[1]))
n_meme = sum(1 for t in resultats if t[0])
n_vis = sum(1 for t in resultats if t[0] and t[7] is None)
lignes = ["=== Faces coplanaires qui se recouvrent : %d paires (%d de MÊME SENS dont %d VISIBLES, %d dos à dos) ==="
          % (len(resultats), n_meme, n_vis, len(resultats) - n_meme)]
groupes = {}
for meme, aire_, a, b, gap, p3, n, cache in resultats:
    etat = ("MÊME SENS - VISIBLE" if cache is None else "même sens - caché") if meme else "dos à dos"
    g = groupes.setdefault((etat, tuple(sorted((a, b)))), [0, 0.0, p3, n, cache])
    g[0] += 1
    g[1] += aire_
lignes.append("Par paire d'objets (nombre de paires de faces, aire totale, un exemple en PIEDS) :")
for (etat, (a, b)), (nb, aire_, p3, n, cache) in sorted(
        groupes.items(), key=lambda t: (t[0][0] != "MÊME SENS - VISIBLE", t[0][0] == "dos à dos", -t[1][1])):
    lignes.append("  %-19s %4d x %9.1f cm²  n=(%+.2f,%+.2f,%+.2f)  ex. (%.2f, %.2f, %.2f) pi%s  |  %s  /  %s"
                  % (etat, nb, aire_ * 1e4, n[0], n[1], n[2], p3[0] / FT, p3[1] / FT, p3[2] / FT,
                     ("  [dans %s]" % cache) if cache else "", a, b))
print("\n".join(lignes[:2] + [l for l in lignes[2:] if "VISIBLE" in l][:60]))
chemin = os.path.join(os.path.dirname(bpy.data.filepath) if bpy.data.filepath else
                      os.getcwd(), "coplanaires_rapport.txt")          # (le projet d'origine avait ici un chemin en dur)
try:
    chemin = os.path.join(os.path.dirname(os.path.abspath(__file__)), "coplanaires_rapport.txt")
except NameError:
    pass
with open(chemin, "w", encoding="utf-8") as f:
    f.write("\n".join(lignes) + "\n")
print("Rapport :", chemin)
