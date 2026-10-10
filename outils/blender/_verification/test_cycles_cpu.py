# -*- coding: utf-8 -*-
"""Test 4 (dans Blender, -b --factory-startup) : rendu Cycles MINUSCULE sur le PROCESSEUR (64 x 48, 1 échantillon,
2 fils), puis liste des périphériques CUDA VUS (énumération seulement : aucun contexte, aucun rendu GPU).

  blender.exe -b --factory-startup --python test_cycles_cpu.py -- <image.png> <sortie.json>
"""
import bpy
import json
import os
import sys
import time

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
IMAGE, SORTIE = argv[0], (argv[1] if len(argv) > 1 else None)
sc = bpy.context.scene
sc.render.engine = "CYCLES"
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = "NONE"          # aucun périphérique de calcul GPU
sc.cycles.device = "CPU"
sc.cycles.samples = 1
sc.cycles.use_adaptive_sampling = False
sc.cycles.use_denoising = False
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 64, 48, 100
sc.render.threads_mode = "FIXED"
sc.render.threads = 2
sc.render.image_settings.file_format = "PNG"
sc.render.filepath = IMAGE
if os.path.exists(IMAGE):
    os.remove(IMAGE)
t0 = time.time()
bpy.ops.render.render(write_still=True)
duree = time.time() - t0
img = bpy.data.images.load(IMAGE)
px = img.pixels[:]
n = len(px) // 4
lum = sum(0.2126 * px[4 * i] + 0.7152 * px[4 * i + 1] + 0.0722 * px[4 * i + 2] for i in range(n)) / n
distincts = len({tuple(round(c, 3) for c in px[4 * i:4 * i + 3]) for i in range(n)})

import _cycles  # noqa: E402
vus = _cycles.available_devices("CUDA")     # énumération (cuInit + attributs) : ne rend rien sur le GPU
r = {"image": IMAGE, "taille": list(img.size), "octets": os.path.getsize(IMAGE), "duree_rendu_s": round(duree, 2),
     "luminance_moyenne": round(lum, 4), "couleurs_distinctes": distincts,
     "device_rendu": sc.cycles.device, "compute_device_type": prefs.compute_device_type,
     "peripheriques_vus_CUDA": [list(map(str, d[:3])) for d in vus]}
r["ok"] = bool(img.size[0] == 64 and img.size[1] == 48 and distincts > 1 and sc.cycles.device == "CPU")
if SORTIE:
    with open(SORTIE, "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False, indent=1)
print("=== TEST_CYCLES_CPU ===", json.dumps(r, ensure_ascii=False))
