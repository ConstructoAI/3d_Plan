# -*- coding: utf-8 -*-
"""Lance un programme SOUS DEBOGUEUR et releve le chemin reel de chaque DLL
chargee (LOAD_DLL_DEBUG_EVENT), y compris les modules charges a la volee.

Usage : python trace_dll.py --racine <dossier portable> [--env-propre] [--json f]
                            [--delai s] [--cwd d] -- programme.exe arg1 arg2 ...

Classement de chaque DLL chargee :
  portable  sous la racine portable
  windows   composant de Windows (System32, WinSxS...), ProductName ~ Windows
  vcredist  runtime Visual C++ pris HORS de la racine (dependance cachee !)
  autre     tout le reste (tiers, pilotes...) : a examiner
Code de sortie : celui du programme ; 99 si le delai est depasse (tue).
"""
import ctypes
import ctypes.wintypes as wt
import json
import os
import subprocess
import sys
import time

import pefile

k32 = ctypes.WinDLL("kernel32", use_last_error=True)

DEBUG_ONLY_THIS_PROCESS = 0x2
CREATE_UNICODE_ENVIRONMENT = 0x400
CREATE_NO_WINDOW = 0x08000000
DBG_CONTINUE = 0x00010002
DBG_EXCEPTION_NOT_HANDLED = 0x80010001
STARTF_USESHOWWINDOW = 0x1
SW_HIDE = 0

EXCEPTION_DEBUG_EVENT = 1
CREATE_PROCESS_DEBUG_EVENT = 3
EXIT_PROCESS_DEBUG_EVENT = 5
LOAD_DLL_DEBUG_EVENT = 6


class EXCEPTION_RECORD(ctypes.Structure):
    _fields_ = [("ExceptionCode", wt.DWORD), ("ExceptionFlags", wt.DWORD),
                ("ExceptionRecord", ctypes.c_void_p),
                ("ExceptionAddress", ctypes.c_void_p),
                ("NumberParameters", wt.DWORD),
                ("ExceptionInformation", ctypes.c_size_t * 15)]


class EXCEPTION_DEBUG_INFO(ctypes.Structure):
    _fields_ = [("ExceptionRecord", EXCEPTION_RECORD), ("dwFirstChance", wt.DWORD)]


class CREATE_PROCESS_DEBUG_INFO(ctypes.Structure):
    _fields_ = [("hFile", wt.HANDLE), ("hProcess", wt.HANDLE), ("hThread", wt.HANDLE),
                ("lpBaseOfImage", ctypes.c_void_p), ("dwDebugInfoFileOffset", wt.DWORD),
                ("nDebugInfoSize", wt.DWORD), ("lpThreadLocalBase", ctypes.c_void_p),
                ("lpStartAddress", ctypes.c_void_p), ("lpImageName", ctypes.c_void_p),
                ("fUnicode", wt.WORD)]


class EXIT_PROCESS_DEBUG_INFO(ctypes.Structure):
    _fields_ = [("dwExitCode", wt.DWORD)]


class LOAD_DLL_DEBUG_INFO(ctypes.Structure):
    _fields_ = [("hFile", wt.HANDLE), ("lpBaseOfDll", ctypes.c_void_p),
                ("dwDebugInfoFileOffset", wt.DWORD), ("nDebugInfoSize", wt.DWORD),
                ("lpImageName", ctypes.c_void_p), ("fUnicode", wt.WORD)]


class _U(ctypes.Union):
    _fields_ = [("Exception", EXCEPTION_DEBUG_INFO),
                ("CreateProcessInfo", CREATE_PROCESS_DEBUG_INFO),
                ("ExitProcess", EXIT_PROCESS_DEBUG_INFO),
                ("LoadDll", LOAD_DLL_DEBUG_INFO)]


class DEBUG_EVENT(ctypes.Structure):
    _fields_ = [("dwDebugEventCode", wt.DWORD), ("dwProcessId", wt.DWORD),
                ("dwThreadId", wt.DWORD), ("u", _U)]


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [("cb", wt.DWORD), ("lpReserved", wt.LPWSTR), ("lpDesktop", wt.LPWSTR),
                ("lpTitle", wt.LPWSTR), ("dwX", wt.DWORD), ("dwY", wt.DWORD),
                ("dwXSize", wt.DWORD), ("dwYSize", wt.DWORD), ("dwXCountChars", wt.DWORD),
                ("dwYCountChars", wt.DWORD), ("dwFillAttribute", wt.DWORD),
                ("dwFlags", wt.DWORD), ("wShowWindow", wt.WORD), ("cbReserved2", wt.WORD),
                ("lpReserved2", ctypes.c_void_p), ("hStdInput", wt.HANDLE),
                ("hStdOutput", wt.HANDLE), ("hStdError", wt.HANDLE)]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [("hProcess", wt.HANDLE), ("hThread", wt.HANDLE),
                ("dwProcessId", wt.DWORD), ("dwThreadId", wt.DWORD)]


assert ctypes.sizeof(DEBUG_EVENT) == 176, ctypes.sizeof(DEBUG_EVENT)

k32.CreateProcessW.argtypes = [wt.LPCWSTR, wt.LPWSTR, ctypes.c_void_p, ctypes.c_void_p,
                               wt.BOOL, wt.DWORD, ctypes.c_void_p, wt.LPCWSTR,
                               ctypes.POINTER(STARTUPINFOW),
                               ctypes.POINTER(PROCESS_INFORMATION)]
k32.WaitForDebugEvent.argtypes = [ctypes.POINTER(DEBUG_EVENT), wt.DWORD]
k32.ContinueDebugEvent.argtypes = [wt.DWORD, wt.DWORD, wt.DWORD]
k32.GetFinalPathNameByHandleW.argtypes = [wt.HANDLE, wt.LPWSTR, wt.DWORD, wt.DWORD]
k32.GetFinalPathNameByHandleW.restype = wt.DWORD
k32.K32GetMappedFileNameW.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.LPWSTR, wt.DWORD]
k32.CloseHandle.argtypes = [wt.HANDLE]
k32.TerminateProcess.argtypes = [wt.HANDLE, wt.UINT]


def env_propre(base_tmp):
    """Environnement d'un poste vierge : variables standard de Windows seulement,
    PATH = System32 + Windows, profils et TEMP detournes vers le bloc-notes."""
    garder = ["SystemRoot", "windir", "SystemDrive", "ComSpec", "PATHEXT",
              "USERNAME", "USERDOMAIN", "COMPUTERNAME", "PROCESSOR_ARCHITECTURE",
              "NUMBER_OF_PROCESSORS", "OS", "ProgramData", "ProgramFiles",
              "ProgramFiles(x86)", "ProgramW6432", "CommonProgramFiles",
              "CommonProgramFiles(x86)", "CommonProgramW6432", "PUBLIC",
              "ALLUSERSPROFILE", "HOMEDRIVE", "HOMEPATH", "USERPROFILE",
              "APPDATA", "LOCALAPPDATA"]
    env = {}
    low = {k.lower(): v for k, v in os.environ.items()}
    for k in garder:
        if k.lower() in low:
            env[k] = low[k.lower()]
    sr = env.get("SystemRoot", r"C:\Windows")
    env["PATH"] = sr + r"\System32;" + sr
    tmp = os.path.join(base_tmp, "tmp")
    os.makedirs(tmp, exist_ok=True)
    env["TEMP"] = env["TMP"] = tmp
    for k, sous in (("APPDATA", "profil\\Roaming"), ("LOCALAPPDATA", "profil\\Local")):
        p = os.path.join(base_tmp, sous)
        os.makedirs(p, exist_ok=True)
        env[k] = p
    env["_NO_DEBUG_HEAP"] = "1"
    return env


def bloc_env(env):
    s = "".join("%s=%s\0" % (k, env[k]) for k in sorted(env, key=str.upper)) + "\0"
    return (ctypes.c_wchar * len(s))(*s)


def chemin_handle(h, hproc=None, base=None):
    buf = ctypes.create_unicode_buffer(1024)
    if h:
        n = k32.GetFinalPathNameByHandleW(h, buf, 1024, 0)
        if n:
            p = buf.value
            return p[4:] if p.startswith("\\\\?\\") else p
    if hproc and base:
        n = k32.K32GetMappedFileNameW(hproc, base, buf, 1024)
        if n:
            return buf.value
    return "?"


_cache = {}


def classer(p, racine):
    pl = p.lower()
    if pl.startswith(racine.lower().rstrip("\\") + "\\"):
        return "portable"
    b = os.path.basename(pl)
    if b.startswith(("msvcp1", "vcruntime1", "concrt1", "vccorlib1", "vcomp1", "mfc1",
                     "mfcm1", "msvcr1", "atl1", "vcamp1")):
        return "vcredist"
    if p in _cache:
        return _cache[p]
    res = "autre"
    try:
        pe = pefile.PE(p, fast_load=True)
        pe.parse_data_directories(directories=[
            pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]])
        infos = {}
        for fi in getattr(pe, "FileInfo", []) or []:
            for bloc in fi:
                for st in getattr(bloc, "StringTable", []) or []:
                    for k, v in st.entries.items():
                        infos[k.decode("latin-1")] = v.decode("latin-1", "replace")
        pe.close()
        if "Microsoft" in infos.get("CompanyName", "") and "Windows" in infos.get("ProductName", ""):
            res = "windows"
    except Exception:  # noqa: BLE001
        pass
    _cache[p] = res
    return res


def tracer(argv, racine, env=None, cwd=None, delai=120.0, cacher=True):
    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(si)
    if cacher:
        si.dwFlags = STARTF_USESHOWWINDOW
        si.wShowWindow = SW_HIDE
    pi = PROCESS_INFORMATION()
    flags = DEBUG_ONLY_THIS_PROCESS | CREATE_UNICODE_ENVIRONMENT | CREATE_NO_WINDOW
    envb = bloc_env(env) if env is not None else None
    cmd = ctypes.create_unicode_buffer(subprocess.list2cmdline(argv))
    ok = k32.CreateProcessW(argv[0], cmd, None, None, False, flags,
                            ctypes.cast(envb, ctypes.c_void_p) if envb is not None else None,
                            cwd, ctypes.byref(si), ctypes.byref(pi))
    if not ok:
        raise OSError(ctypes.get_last_error(), "CreateProcessW a echoue")
    dlls, exceptions = [], {}
    code_sortie, tue = None, False
    t0 = time.time()
    ev = DEBUG_EVENT()
    hproc = pi.hProcess
    premiere_bp = True
    while True:
        if time.time() - t0 > delai:
            k32.TerminateProcess(hproc, 99)
            tue = True
        if not k32.WaitForDebugEvent(ctypes.byref(ev), 500):
            continue
        statut = DBG_CONTINUE
        c = ev.dwDebugEventCode
        if c == CREATE_PROCESS_DEBUG_EVENT:
            info = ev.u.CreateProcessInfo
            dlls.append(chemin_handle(info.hFile))
            if info.hFile:
                k32.CloseHandle(info.hFile)
        elif c == LOAD_DLL_DEBUG_EVENT:
            info = ev.u.LoadDll
            dlls.append(chemin_handle(info.hFile, hproc, info.lpBaseOfDll))
            if info.hFile:
                k32.CloseHandle(info.hFile)
        elif c == EXCEPTION_DEBUG_EVENT:
            code = ev.u.Exception.ExceptionRecord.ExceptionCode
            if code == 0x80000003 and premiere_bp:
                premiere_bp = False  # point d'arret initial du chargeur
            else:
                statut = DBG_EXCEPTION_NOT_HANDLED
                if ev.u.Exception.dwFirstChance:
                    exceptions[hex(code)] = exceptions.get(hex(code), 0) + 1
        elif c == EXIT_PROCESS_DEBUG_EVENT:
            code_sortie = ev.u.ExitProcess.dwExitCode
            k32.ContinueDebugEvent(ev.dwProcessId, ev.dwThreadId, DBG_CONTINUE)
            break
        k32.ContinueDebugEvent(ev.dwProcessId, ev.dwThreadId, statut)
    k32.CloseHandle(pi.hThread)
    k32.CloseHandle(pi.hProcess)
    classes = {}
    vus = []
    for p in dlls:
        if p in vus:
            continue
        vus.append(p)
        classes.setdefault(classer(p, racine), []).append(p)
    return {"commande": argv, "code_sortie": code_sortie, "tue_apres_delai": tue,
            "duree_s": round(time.time() - t0, 2), "nb_dll": len(vus),
            "classes": classes, "exceptions_1re_chance": exceptions}


def main():
    a = sys.argv[1:]
    if "--" not in a:
        print(__doc__)
        return 2
    i = a.index("--")
    opts, prog = a[:i], a[i + 1:]

    def opt(nom, defaut=None):
        return opts[opts.index(nom) + 1] if nom in opts else defaut
    racine = os.path.abspath(opt("--racine", os.path.dirname(prog[0])))
    env = None
    if "--env-propre" in opts:
        env = env_propre(os.path.dirname(os.path.abspath(__file__)))
    r = tracer(prog, racine, env=env, cwd=opt("--cwd"), delai=float(opt("--delai", "120")))
    if opt("--json"):
        with open(opt("--json"), "w", encoding="utf-8") as f:
            json.dump(r, f, ensure_ascii=False, indent=1)
    print("Commande   :", subprocess.list2cmdline(prog))
    print("Code sortie:", r["code_sortie"], " tue:", r["tue_apres_delai"], " duree:", r["duree_s"], "s")
    print("DLL chargees:", r["nb_dll"])
    for k in ("portable", "windows", "vcredist", "autre"):
        v = r["classes"].get(k, [])
        if k in ("portable", "windows"):
            print("  %-9s %3d" % (k, len(v)))
        else:
            print("  %-9s %3d : %s" % (k, len(v), "; ".join(v)))
    if r["exceptions_1re_chance"]:
        print("Exceptions de 1re chance :", r["exceptions_1re_chance"])
    return 0 if r["code_sortie"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
