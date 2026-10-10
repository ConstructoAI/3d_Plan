# -*- coding: utf-8 -*-
"""Test 1 (dans Blender, -b --factory-startup) : version, chemins de ressources, Python embarqué, modules,
et PROVENANCE de chaque DLL chargée dans le processus (aucun rendu, aucun GPU).

  blender.exe -b --factory-startup --python test_env_blender.py -- <sortie.json>
"""
import bpy
import ctypes
import importlib
import json
import os
import site
import struct
import sys
import time
from ctypes import wintypes

t0 = time.time()
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SORTIE = argv[0] if argv else None
RACINE = os.path.dirname(os.path.abspath(bpy.app.binary_path))
SYS32 = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")

r = {}
r["version"] = bpy.app.version_string
r["build_hash"] = bpy.app.build_hash.decode() if isinstance(bpy.app.build_hash, bytes) else bpy.app.build_hash
r["build_date"] = bpy.app.build_date.decode() if isinstance(bpy.app.build_date, bytes) else bpy.app.build_date
r["binary_path"] = bpy.app.binary_path
r["background"] = bpy.app.background
r["factory_startup"] = bpy.app.factory_startup
r["resource_path"] = {k: bpy.utils.resource_path(k) for k in ("LOCAL", "USER", "SYSTEM")}
r["user_resource"] = {k: bpy.utils.user_resource(k) for k in ("CONFIG", "SCRIPTS", "DATAFILES", "EXTENSIONS")}
r["script_paths"] = bpy.utils.script_paths()
r["script_path_user"] = bpy.utils.script_path_user()
r["tempdir"] = bpy.app.tempdir
r["cachedir (chemin seulement)"] = bpy.app.cachedir
r["cwd"] = os.getcwd()
r["python"] = {
    "version": sys.version,
    "executable": sys.executable,
    "prefix": sys.prefix,
    "base_prefix": sys.base_prefix,
    "path": sys.path,
    "ENABLE_USER_SITE": site.ENABLE_USER_SITE,
    "USER_SITE": site.getusersitepackages(),
    "USER_SITE_dans_sys_path": any(p.lower() == site.getusersitepackages().lower() for p in sys.path),
    "flags.isolated": sys.flags.isolated,
    "flags.ignore_environment": sys.flags.ignore_environment,
    "flags.no_user_site": sys.flags.no_user_site,
    "dont_write_bytecode": sys.dont_write_bytecode,
    "pycache_prefix": sys.pycache_prefix,
}
r["env"] = {k: os.environ.get(k) for k in ("PATH", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP", "USERPROFILE",
                                           "BLENDER_USER_RESOURCES", "PYTHONPATH", "PYTHONHOME")}

# --- modules Python (bibliothèque standard compilée + paquets embarqués)
mods = {}
for nom in ["numpy", "ssl", "sqlite3", "ctypes", "lzma", "bz2", "decimal", "xml.etree.ElementTree", "pyexpat",
            "hashlib", "socket", "select", "asyncio", "uuid", "zoneinfo", "unicodedata", "multiprocessing",
            "concurrent.futures", "zstandard", "requests", "certifi", "urllib3", "PyOpenColorIO", "OpenImageIO",
            "MaterialX", "pxr.Usd", "openvdb", "oslquery", "_cycles", "bmesh", "mathutils", "aud",
            "addon_utils", "bl_pkg"]:
    try:
        m = importlib.import_module(nom)
        mods[nom] = {"ok": True, "version": str(getattr(m, "__version__", "") or getattr(m, "VERSION", "") or ""),
                     "fichier": getattr(m, "__file__", None)}
    except Exception as ex:  # noqa: BLE001
        mods[nom] = {"ok": False, "erreur": repr(ex)}
r["modules"] = mods

# --- essais fonctionnels légers
import numpy as np  # noqa: E402
a = np.random.default_rng(0).random((60, 60))
x = np.linalg.solve(a @ a.T + np.eye(60), np.ones(60))
try:
    blas = np.show_config(mode="dicts").get("Build Dependencies", {}).get("blas", {}).get("name")
except Exception as ex:  # noqa: BLE001
    blas = repr(ex)
r["numpy_essai"] = {"residu": float(np.abs((a @ a.T + np.eye(60)) @ x - 1).max()), "blas": blas}
import ssl  # noqa: E402
r["ssl"] = ssl.OPENSSL_VERSION
import sqlite3  # noqa: E402
con = sqlite3.connect(":memory:")
r["sqlite"] = con.execute("select sqlite_version()").fetchone()[0]
con.close()
import mathutils  # noqa: E402
r["mathutils"] = str(mathutils.Matrix.Rotation(0.5, 3, "Z") @ mathutils.Vector((1, 0, 0)))
# opérations bpy de base (sans contexte d'écran)
me = bpy.data.meshes.new("essai")
import bmesh  # noqa: E402
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=2.0)
bm.to_mesh(me)
bm.free()
ob = bpy.data.objects.new("essai", me)
bpy.context.scene.collection.objects.link(ob)
mod = ob.modifiers.new("biseau", "BEVEL")
mod.width = 0.1
dg = bpy.context.evaluated_depsgraph_get()
r["bmesh_modificateur"] = {"sommets_cube": len(me.vertices),
                           "sommets_apres_biseau": len(ob.evaluated_get(dg).data.vertices)}

# --- provenance des DLL chargées
psapi = ctypes.WinDLL("psapi")
k32 = ctypes.WinDLL("kernel32")
k32.GetCurrentProcess.restype = wintypes.HANDLE
psapi.EnumProcessModulesEx.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_void_p), wintypes.DWORD,
                                       ctypes.POINTER(wintypes.DWORD), wintypes.DWORD]
psapi.GetModuleFileNameExW.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.LPWSTR, wintypes.DWORD]
ver = ctypes.WinDLL("version")
ver.GetFileVersionInfoSizeW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD)]
ver.GetFileVersionInfoW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]
ver.VerQueryValueW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p),
                               ctypes.POINTER(wintypes.UINT)]


def produit(path):
    n = ver.GetFileVersionInfoSizeW(path, None)
    if not n:
        return ""
    buf = ctypes.create_string_buffer(n)
    if not ver.GetFileVersionInfoW(path, 0, n, buf):
        return ""
    p, ln = ctypes.c_void_p(), wintypes.UINT()
    cles = []
    if ver.VerQueryValueW(buf, r"\VarFileInfo\Translation", ctypes.byref(p), ctypes.byref(ln)) and ln.value >= 4:
        lang, cp = struct.unpack("<HH", ctypes.string_at(p.value, 4))
        cles.append("%04x%04x" % (lang, cp))
    cles += ["040904b0", "040904e4", "000004b0"]
    for k in cles:
        if ver.VerQueryValueW(buf, "\\StringFileInfo\\%s\\ProductName" % k, ctypes.byref(p), ctypes.byref(ln)) \
                and ln.value:
            return ctypes.wstring_at(p.value, ln.value).rstrip("\0")
    return ""


h = k32.GetCurrentProcess()
arr = (ctypes.c_void_p * 4096)()
need = wintypes.DWORD()
psapi.EnumProcessModulesEx(h, arr, ctypes.sizeof(arr), ctypes.byref(need), 3)
buf = ctypes.create_unicode_buffer(32768)
dlls = []
for i in range(need.value // ctypes.sizeof(ctypes.c_void_p)):
    psapi.GetModuleFileNameExW(h, arr[i], buf, 32768)
    dlls.append(buf.value)
classes = {}
for p in dlls:
    pl = p.lower()
    if pl.startswith(RACINE.lower() + os.sep):
        c = "portable"
    elif pl.startswith(SYS32.lower() + os.sep) or pl.startswith(os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                                                                            "WinSxS").lower()):
        pr = produit(p)
        if "Visual Studio" in pr or "Visual C++" in pr:
            c = "SYSTEME-REDISTRIBUABLE"
        elif ("Windows" in pr) or ("Internet Explorer" in pr) or (pr == "" and "microsoft" in pl):
            c = "windows"
        else:
            c = "SYSTEME-TIERS (%s)" % pr
    else:
        c = "AILLEURS"
    classes.setdefault(c, []).append(p)
r["dll_chargees"] = {"nombre": len(dlls), "par_classe": {k: len(v) for k, v in classes.items()},
                     "hors_portable_et_windows": {k: v for k, v in classes.items() if k not in ("portable", "windows")},
                     "portable_crt": sorted(os.path.basename(p) for p in classes.get("portable", [])
                                            if "blender.crt" in p.lower()),
                     "liste_windows": sorted(os.path.basename(p).lower() for p in classes.get("windows", []))}
r["duree_s"] = round(time.time() - t0, 2)

txt = json.dumps(r, ensure_ascii=False, indent=1)
if SORTIE:
    with open(SORTIE, "w", encoding="utf-8") as f:
        f.write(txt)
print("=== TEST_ENV_BLENDER ===")
print("version", r["version"], "| USER =", r["resource_path"]["USER"], "| LOCAL =", r["resource_path"]["LOCAL"])
print("python", sys.version.split()[0], "| numpy", mods["numpy"].get("version"), "| user site actif :",
      r["python"]["ENABLE_USER_SITE"], "| dans sys.path :", r["python"]["USER_SITE_dans_sys_path"])
print("modules en échec :", [k for k, v in mods.items() if not v["ok"]])
print("DLL chargées :", r["dll_chargees"]["par_classe"])
for k, v in r["dll_chargees"]["hors_portable_et_windows"].items():
    print("  ", k, ":", v)
print("=== FIN (%.2f s) ===" % r["duree_s"])
