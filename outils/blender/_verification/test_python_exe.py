# -*- coding: utf-8 -*-
"""Test 2 : le python.exe EMBARQUÉ de Blender (5.2\\python\\bin\\python.exe), hors de Blender.
Il sert à blender_system_info.cmd, à pip, et à tout sous-processus lancé par sys.executable depuis Blender
(multiprocessing, concurrent.futures.ProcessPoolExecutor).
Vérifie les modules compilés et la PROVENANCE de chaque DLL chargée.

  <blender>\\5.2\\python\\bin\\python.exe -I test_python_exe.py <racine_blender> [sortie.json]
"""
import ctypes
import importlib
import json
import os
import struct
import sys
import time
from ctypes import wintypes

SYSROOT = os.environ.get("SystemRoot", r"C:\Windows")
SYS32 = os.path.join(SYSROOT, "System32")


def produit(path):
    ver = ctypes.WinDLL("version")
    ver.GetFileVersionInfoSizeW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD)]
    ver.GetFileVersionInfoW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]
    ver.VerQueryValueW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p),
                                   ctypes.POINTER(wintypes.UINT)]
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


def dll_chargees(racine):
    psapi = ctypes.WinDLL("psapi")
    k32 = ctypes.WinDLL("kernel32")
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.EnumProcessModulesEx.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_void_p), wintypes.DWORD,
                                           ctypes.POINTER(wintypes.DWORD), wintypes.DWORD]
    psapi.GetModuleFileNameExW.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.LPWSTR, wintypes.DWORD]
    h = k32.GetCurrentProcess()
    arr = (ctypes.c_void_p * 4096)()
    need = wintypes.DWORD()
    psapi.EnumProcessModulesEx(h, arr, ctypes.sizeof(arr), ctypes.byref(need), 3)
    buf = ctypes.create_unicode_buffer(32768)
    classes = {}
    for i in range(need.value // ctypes.sizeof(ctypes.c_void_p)):
        psapi.GetModuleFileNameExW(h, arr[i], buf, 32768)
        p = buf.value
        pl = p.lower()
        if pl.startswith(racine.lower() + os.sep):
            c = "portable"
        elif pl.startswith(SYS32.lower() + os.sep) or pl.startswith(os.path.join(SYSROOT, "WinSxS").lower()):
            pr = produit(p)
            if "Visual Studio" in pr or "Visual C++" in pr:
                c = "SYSTEME-REDISTRIBUABLE"
            elif "Windows" in pr or "Internet Explorer" in pr:
                c = "windows"
            else:
                c = "SYSTEME-TIERS (%s)" % pr
        else:
            c = "AILLEURS"
        classes.setdefault(c, []).append(p)
    return classes


def main():
    t0 = time.time()
    racine = os.path.abspath(sys.argv[1])
    sortie = sys.argv[2] if len(sys.argv) > 2 else None
    r = {"executable": sys.executable, "version": sys.version, "prefix": sys.prefix, "isolated": sys.flags.isolated}
    mods = {}
    for nom in ["numpy", "ssl", "sqlite3", "ctypes", "lzma", "bz2", "decimal", "xml.etree.ElementTree", "hashlib",
                "socket", "select", "asyncio", "uuid", "zoneinfo", "unicodedata", "multiprocessing", "zstandard",
                "requests"]:
        try:
            m = importlib.import_module(nom)
            mods[nom] = {"ok": True, "version": str(getattr(m, "__version__", "") or "")}
        except Exception as ex:  # noqa: BLE001
            mods[nom] = {"ok": False, "erreur": repr(ex)}
    r["modules"] = mods
    import numpy as np
    a = np.random.default_rng(0).random((60, 60))
    m = a @ a.T + np.eye(60)
    r["numpy_residu"] = float(np.abs(m @ np.linalg.solve(m, np.ones(60)) - 1).max())
    # sous-processus (cas d'un ProcessPoolExecutor lancé depuis un script : il relance sys.executable)
    import concurrent.futures as cf
    with cf.ProcessPoolExecutor(max_workers=2) as ex:
        r["multiprocessing"] = sorted(ex.map(pow, [2, 3], [10, 5]))
    classes = dll_chargees(racine)
    r["dll_par_classe"] = {k: len(v) for k, v in classes.items()}
    r["dll_hors_portable_et_windows"] = {k: v for k, v in classes.items() if k not in ("portable", "windows")}
    r["dll_runtime_vc"] = sorted(p for p in classes.get("portable", []) + classes.get("SYSTEME-REDISTRIBUABLE", [])
                                 if os.path.basename(p).lower().startswith(("vcruntime", "msvcp", "concrt")))
    r["duree_s"] = round(time.time() - t0, 2)
    r["ok"] = all(v["ok"] for v in mods.values()) and not r["dll_hors_portable_et_windows"] \
        and r["multiprocessing"] == [243, 1024]
    if sortie:
        with open(sortie, "w", encoding="utf-8") as f:
            json.dump(r, f, ensure_ascii=False, indent=1)
    print("=== TEST_PYTHON_EXE ===", json.dumps({k: r[k] for k in ("version", "dll_par_classe", "dll_runtime_vc",
                                                                    "dll_hors_portable_et_windows", "multiprocessing",
                                                                    "ok", "duree_s")}, ensure_ascii=False))
    print("modules en échec :", [k for k, v in mods.items() if not v["ok"]])


if __name__ == "__main__":
    main()
