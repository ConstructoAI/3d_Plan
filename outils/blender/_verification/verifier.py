# -*- coding: utf-8 -*-
r"""
Vérification du Blender PORTABLE (outils\blender) : à relancer sur tout nouveau poste.

Usage (n'importe quel Python 3.9+, y compris celui de Blender lui-même) :
    outils\blender\5.2\python\bin\python.exe -I outils\blender\_verification\verifier.py [normal] [propre]
                                                                                   [--sortie DOSSIER]
    normal : environnement tel quel ;
    propre : environnement NETTOYÉ, comme un poste neuf : PATH = System32;Windows, APPDATA, LOCALAPPDATA et TEMP
             redirigés vers des dossiers vides, aucune autre variable que celles de Windows.
    (sans argument : les deux)
    --sortie : dossier (vide ou inexistant) des résultats ; par défaut, un dossier neuf sous %TEMP%.

Aucun GPU : Blender en arrière-plan (-b), rendu Cycles sur le PROCESSEUR en 64 x 48 et 1 échantillon ; les
périphériques CUDA sont seulement énumérés. Rien n'est écrit dans outils\ ni dans les projets : les résultats vont
dans le dossier de sortie, dont le chemin est affiché. Code de sortie : 0 si tout passe, 1 sinon.
Durée mesurée sur le poste d'origine (i5-3470) : environ 80 s pour les deux modes.

Essais : 1. chemins et mode portable, Python embarqué, modules, PROVENANCE de chaque DLL chargée ;
         2. python.exe embarqué hors de Blender (+ multiprocessing) ;  3. Line Art ;  4. Cycles CPU ;
         5. vrai script de projet, sur une COPIE : ..\Garage_rouge_Blender (build + faces coplanaires), s'il existe.
Écrit par l'agent B (poste Blender autonome), le 2026-09-25.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

ICI = os.path.dirname(os.path.abspath(__file__))
BLENDER = os.path.dirname(ICI)                                  # ...\outils\blender
POSTE = os.path.dirname(os.path.dirname(BLENDER))               # ...\blender-main (celui qui contient outils\)
GARAGE = os.path.join(os.path.dirname(POSTE), "Garage_rouge_Blender")
GARAGE_FICHIERS = ["build_garage.py", "parametres_garage.py", "verifier_coplanaires.py"]
GARDER = ["SystemRoot", "windir", "SystemDrive", "ComSpec", "PATHEXT", "OS", "PROCESSOR_ARCHITECTURE",
          "PROCESSOR_IDENTIFIER", "PROCESSOR_LEVEL", "PROCESSOR_REVISION", "NUMBER_OF_PROCESSORS", "USERNAME",
          "USERDOMAIN", "USERPROFILE", "HOMEDRIVE", "HOMEPATH", "ProgramData", "ALLUSERSPROFILE", "PUBLIC",
          "ProgramFiles", "ProgramFiles(x86)", "ProgramW6432", "CommonProgramFiles", "CommonProgramFiles(x86)",
          "CommonProgramW6432", "COMPUTERNAME"]


def inventaire(d):
    out = set()
    if os.path.isdir(d):
        for r, sd, fs in os.walk(d):
            out.update(os.path.relpath(os.path.join(r, x), d) for x in fs)
            out.update(os.path.relpath(os.path.join(r, x), d) + os.sep for x in sd)
    return out


def env_propre(base):
    env = {k: os.environ[k] for k in GARDER if k in os.environ}
    sysroot = env.get("SystemRoot", r"C:\Windows")
    env["PATH"] = os.path.join(sysroot, "System32") + ";" + sysroot
    env["APPDATA"] = os.path.join(base, "Roaming")
    env["LOCALAPPDATA"] = os.path.join(base, "Local")
    env["TEMP"] = env["TMP"] = os.path.join(base, "Local", "Temp")
    for k in ("APPDATA", "LOCALAPPDATA", "TEMP"):
        os.makedirs(env[k], exist_ok=True)
    return env


def lancer(cmd, env, cwd, journal, delai=900):
    t0 = time.time()
    with open(journal, "w", encoding="utf-8", errors="replace") as f:
        p = subprocess.run(cmd, env=env, cwd=cwd, stdout=f, stderr=subprocess.STDOUT, timeout=delai)
    return p.returncode, round(time.time() - t0, 1)


def lire_json(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception as ex:  # noqa: BLE001
        return {"erreur_lecture": repr(ex)}


def un_mode(mode, sortie):
    res = os.path.join(sortie, mode)
    os.makedirs(res)
    base_vide = None
    if mode == "propre":
        base_vide = os.path.join(sortie, "env_vide")
        env = env_propre(base_vide)
    else:
        env = dict(os.environ)
    exe = os.path.join(BLENDER, "blender.exe")
    pyexe = os.path.join(BLENDER, "5.2", "python", "bin", "python.exe")
    avant_portable = inventaire(os.path.join(BLENDER, "portable"))
    ok, notes, b = [], [], {"mode": mode}

    j = os.path.join(res, "env.json")
    rc, dt = lancer([exe, "-b", "--factory-startup", "--python", os.path.join(ICI, "test_env_blender.py"), "--", j],
                    env, res, os.path.join(res, "env.log"))
    e = lire_json(j)
    dl = e.get("dll_chargees", {})
    hors = dl.get("hors_portable_et_windows", {}) or {}
    fuites = [p for c, lst in hors.items() for p in lst
              if c.startswith("SYSTEME-REDISTRIBUABLE") or re.search(r"blender|python", p, re.I)]
    user = e.get("resource_path", {}).get("USER") or ""
    b["1_env"] = {"code": rc, "duree_s": dt, "version": e.get("version"), "USER": user,
                  "modules_en_echec": [k for k, v in e.get("modules", {}).items() if not v.get("ok")],
                  "dll_par_classe": dl.get("par_classe"), "dll_hors": hors, "fuites": fuites}
    ok.append(("1 chemins, modules et DLL", rc == 0 and os.path.normcase(user) == os.path.normcase(
        os.path.join(BLENDER, "portable")) and not b["1_env"]["modules_en_echec"] and not fuites))
    if hors and not fuites:
        notes.append("DLL hors du dossier, tolérées (antivirus, etc.) : %s" % hors)

    j = os.path.join(res, "python_exe.json")
    rc, dt = lancer([pyexe, "-I", os.path.join(ICI, "test_python_exe.py"), BLENDER, j], env, res,
                    os.path.join(res, "python_exe.log"))
    p = lire_json(j)
    b["2_python_exe"] = {"code": rc, "duree_s": dt, "ok": p.get("ok"), "runtime_vc": p.get("dll_runtime_vc"),
                         "hors": p.get("dll_hors_portable_et_windows")}
    ok.append(("2 python.exe embarqué", rc == 0 and bool(p.get("ok"))))

    j = os.path.join(res, "lineart.json")
    rc, dt = lancer([exe, "-b", "--factory-startup", "--python", os.path.join(ICI, "test_lineart.py"), "--", j],
                    env, res, os.path.join(res, "lineart.log"))
    b["3_lineart"] = dict(lire_json(j), code=rc, duree_totale_s=dt)
    ok.append(("3 Line Art", rc == 0 and bool(b["3_lineart"].get("ok"))))

    j = os.path.join(res, "cycles_cpu.json")
    rc, dt = lancer([exe, "-b", "--factory-startup", "--python", os.path.join(ICI, "test_cycles_cpu.py"), "--",
                     os.path.join(res, "cycles_cpu_64x48.png"), j], env, res, os.path.join(res, "cycles_cpu.log"))
    b["4_cycles_cpu"] = dict(lire_json(j), code=rc, duree_totale_s=dt)
    ok.append(("4 Cycles CPU", rc == 0 and bool(b["4_cycles_cpu"].get("ok"))))

    if all(os.path.isfile(os.path.join(GARAGE, f)) for f in GARAGE_FICHIERS):
        gdir = os.path.join(res, "garage")
        os.makedirs(gdir)
        for f in GARAGE_FICHIERS:
            shutil.copy2(os.path.join(GARAGE, f), os.path.join(gdir, f))
        journal = os.path.join(res, "garage.log")
        rc, dt = lancer([exe, "-b", "--factory-startup", "--python", os.path.join(gdir, "build_garage.py"),
                         "--python", os.path.join(gdir, "verifier_coplanaires.py")], env, gdir, journal)
        log = open(journal, encoding="utf-8", errors="replace").read()
        m = re.search(r"=== Faces coplanaires qui se recouvrent : (\d+) paires \((\d+) de M.ME SENS dont (\d+) "
                      r"VISIBLES", log)
        b["5_garage"] = {"code": rc, "duree_s": dt, "coplanaires": m.groups() if m else None,
                         "traceback": "Traceback" in log}
        ok.append(("5 script de projet (garage)", rc == 0 and m is not None and "Traceback" not in log))
    else:
        b["5_garage"] = "sauté : %s absent" % GARAGE
        notes.append(b["5_garage"])

    nouveaux = sorted(inventaire(os.path.join(BLENDER, "portable")) - avant_portable)
    b["6_portable_nouveaux"] = nouveaux
    if base_vide:
        b["6_ecrit_dans_env_vide"] = sorted(x for x in inventaire(base_vide) if x not in
                                            ("Roaming" + os.sep, "Local" + os.sep, os.path.join("Local", "Temp") + os.sep))
        if b["6_ecrit_dans_env_vide"]:
            notes.append("écrit sous APPDATA/LOCALAPPDATA redirigés : %s (NVIDIA\\ComputeCache = pilote CUDA, "
                         "évitable par CUDA_CACHE_PATH)" % b["6_ecrit_dans_env_vide"])
    b["verdict"] = {nom: v for nom, v in ok}
    b["notes"] = notes
    return b


def main():
    try:
        sys.stdout.reconfigure(errors="replace")   # console cp1252 : un caractère hors page de codes ne plante pas
    except Exception:  # noqa: BLE001
        pass
    modes = [m for m in sys.argv[1:] if m in ("normal", "propre")] or ["normal", "propre"]
    if "--sortie" in sys.argv:
        sortie = os.path.abspath(sys.argv[sys.argv.index("--sortie") + 1])
        os.makedirs(sortie, exist_ok=True)
        if os.listdir(sortie):
            print("--sortie doit désigner un dossier vide :", sortie)
            return 2
    else:
        sortie = tempfile.mkdtemp(prefix="verif_blender_portable_")
    print("Blender portable :", BLENDER)
    print("Résultats dans   :", sortie)
    t0 = time.time()
    tout = {}
    for mode in modes:
        tout[mode] = un_mode(mode, sortie)
        print("\n== mode %s ==" % mode)
        for nom, v in tout[mode]["verdict"].items():
            print("  %-30s %s" % (nom, "OK" if v else "ÉCHEC"))
        for n in tout[mode]["notes"]:
            print("  note :", n)
    with open(os.path.join(sortie, "bilan.json"), "w", encoding="utf-8") as f:
        json.dump(tout, f, ensure_ascii=False, indent=1)
    reussi = all(all(b["verdict"].values()) for b in tout.values())
    print("\nVERDICT : %s (%.0f s) ; détail : %s" % ("TOUT PASSE" if reussi else "ÉCHEC", time.time() - t0,
                                                   os.path.join(sortie, "bilan.json")))
    return 0 if reussi else 1


if __name__ == "__main__":
    sys.exit(main())
