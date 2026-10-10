# -*- coding: utf-8 -*-
"""Test 3 (dans Blender, -b --factory-startup) : Line Art (calcul CPU), lecture des traits.
Scène d'usine : cube de 2 m centré, vu de face par une caméra ORTHO -> un carré de 2 x 2 m attendu.

  blender.exe -b --factory-startup --python test_lineart.py -- <sortie.json>
"""
import bpy
import json
import math
import sys
import time

t0 = time.time()
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SORTIE = argv[0] if argv else None
sc = bpy.context.scene
cube = bpy.data.objects["Cube"]
cam = sc.camera
cam.data.type = "ORTHO"
cam.data.ortho_scale = 4.0
cam.location = (0.0, -10.0, 0.0)
cam.rotation_euler = (math.radians(90), 0.0, 0.0)
# un 2e objet devant le cube, pour vérifier les lignes cachées (le cube est partiellement masqué)
bpy.ops.mesh.primitive_cube_add(size=0.5, location=(0.0, -2.0, 0.0))

gpd = bpy.data.grease_pencils.new("LineArt")
calque = gpd.layers.new("Traits")
calque.frames.new(sc.frame_current)
mat = bpy.data.materials.new("Traits")
bpy.data.materials.create_gpencil_data(mat)
gpd.materials.append(mat)
ob = bpy.data.objects.new("LineArt", gpd)
sc.collection.objects.link(ob)
mod = ob.modifiers.new("LA", "LINEART")
mod.source_type = "SCENE"
mod.target_layer = "Traits"
mod.target_material = mat
mod.use_contour = True
mod.use_crease = True
mod.use_intersection = True
mod.use_loose = True
mod.crease_threshold = math.radians(145)
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
ev = ob.evaluated_get(dg)
n_traits = n_points = 0
xs, zs = [], []
for L in ev.data.layers:
    for fr in L.frames:
        d = fr.drawing
        for s in d.strokes:
            n_traits += 1
            for p in s.points:
                n_points += 1
                xs.append(p.position.x)
                zs.append(p.position.z)
r = {"traits": n_traits, "points": n_points,
     "boite_x": [round(min(xs), 4), round(max(xs), 4)] if xs else None,
     "boite_z": [round(min(zs), 4), round(max(zs), 4)] if zs else None,
     "duree_s": round(time.time() - t0, 2)}
r["ok"] = bool(n_traits >= 2 and r["boite_x"] == [-1.0, 1.0] and r["boite_z"] == [-1.0, 1.0])
if SORTIE:
    with open(SORTIE, "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False, indent=1)
print("=== TEST_LINEART ===", json.dumps(r, ensure_ascii=False))
