# -*- coding: utf-8 -*-
r"""
outils\chemins.py -- où sont les outils du poste Blender (dossier AUTONOME).

Le dossier du poste (celui qui contient outils\) se colle n'importe où : D:\, un
autre nom, un autre poste. AUCUN chemin n'est écrit en dur ici : la racine se
déduit de l'emplacement de ce fichier.

Ordre de résolution de chaque outil
  1. la variable BM_* si elle est posée (BM_PYTHON, BM_BLENDER, ...) ;
  2. la copie PORTABLE sous outils\ ;
  3. l'installation du SYSTÈME (repli : tout marche pendant la migration) ;
  4. sinon l'exception OutilIntrouvable, avec un message clair en français.
Exception voulue : Claude Code cherche d'abord l'installation du poste (elle se
met à jour toute seule), puis la copie portable outils\claude\claude.exe.

Interface fixée pour l'équipe : racine(), python_exe(), blender_exe(),
oda_convertisseur(), oda_visionneuse(), node_exe(), navigateur_pdf(),
configurer_ezdxf_odafc(), verifier().
En plus : resoudre(), claude_exe(), projet_en_cours(), env_blender(),
variables_session(), path_session(), OutilIntrouvable, Verification ;
et (2026-09-25, soir) postgres_bin(), git_bash(), git_exe(), gh_exe(), config_claude().

Claude Code, « zéro trace » : la session reçoit CLAUDE_CONFIG_DIR = <racine>\\outils\\claude\\config
quand ce dossier existe (BM_CLAUDE_CONFIG=profil : retour au profil de l'utilisateur).

Particularités des outils ajoutés le 2026-09-25 au soir :
  - PostgreSQL : BM_POSTGRES est le DOSSIER bin (initdb, pg_ctl, psql, pg_dump...).
    La variable posée à la main peut désigner ce dossier, la racine de PostgreSQL ou
    un exécutable de bin. Version visée : 18 (celle du cluster du programme Métré).
  - Git : BM_GIT_BASH est le bash.exe de Git for Windows ; git_exe() est le git.exe
    du MÊME Git. Jamais le bash.exe de System32 (c'est WSL). Pour la session :
    CLAUDE_CODE_GIT_BASH_PATH (Claude Code trouve Git Bash par elle) et le dossier cmd
    du Git dans le PATH.
  - GitHub CLI : BM_GH (gh.exe), son dossier dans le PATH de la session.

La même logique existe en PowerShell (chemins.ps1, que chemins.cmd appelle) ;
outils\diagnostic\test_chemins.py vérifie que les deux rendent la même chose.

Pur Python standard, 3.9 et plus. S'importe aussi depuis le Python embarqué de
Blender : ni bpy ni ezdxf ne sont requis à l'import.

En ligne de commande
  python chemins.py              tableau de vérification
  python chemins.py --complet    idem, en lançant aussi blender/node/claude --version
  python chemins.py --json       le tableau en JSON
  python chemins.py --ascii      sortie sans accents (console cmd.exe)
  python chemins.py --projet     le dossier du projet en cours
  python chemins.py --variables  les BM_* et le PATH qu'un lanceur poserait (NOM=valeur)

Dans un script (la session lancée par Demarrer-Blender.bat porte BM_RACINE)
  import os, sys
  sys.path.insert(0, os.path.join(os.environ["BM_RACINE"], "outils"))
  import chemins
  subprocess.run([chemins.blender_exe(), "-b", "--factory-startup", "--python", "x.py"])
"""

import glob
import json
import os
import re
import shutil
import struct
import subprocess
import sys

VERSION_PYTHON_VISEE = (3, 13)
VERSION_BLENDER_VISEE = (5, 2)
# Le cluster du programme Métré (Metre\donnees\pgdata) est en PostgreSQL 18 : un autre
# numéro majeur refuserait de l'ouvrir.
VERSION_POSTGRES_VISEE = (18,)
# blender.exe n'est pas « longPathAware » ; son plus long fichier fait 113 caractères
# sous outils\blender (mesuré par l'agent B) : la racine doit rester courte.
LONGUEUR_RACINE_MAX = 120

# Dossier de CE fichier (outils\), figé à l'import : un chdir ultérieur n'y change rien.
_ICI = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else ""

# Outils posés par chemins.cmd / chemins.ps1 pour une session, dans cet ordre.
OUTILS_SESSION = ("python", "blender", "oda_convertisseur", "oda_visionneuse", "node", "navigateur",
                  "postgres", "git_bash", "gh")

_BASES_PF = ("ProgramW6432", "ProgramFiles", "ProgramFiles(x86)")

_DEFS = {
    "python": {
        "cle": "PYTHON", "nom": "Python", "portable": "python", "exe": "python.exe",
        "motifs": [("LOCALAPPDATA", r"Programs\Python", "Python3*")]
                  + [(b, "", "Python3*") for b in _BASES_PF],
        "prefixe": "Python", "visee": VERSION_PYTHON_VISEE, "fixes": [], "path": ["python.exe"],
        "aide": "copier le Python 3.13 du poste, avec ezdxf, dans outils\\python\\",
    },
    "blender": {
        "cle": "BLENDER", "nom": "Blender", "portable": "blender", "exe": "blender.exe",
        "motifs": [(b, "Blender Foundation", "Blender*") for b in _BASES_PF],
        "prefixe": "Blender", "visee": VERSION_BLENDER_VISEE, "fixes": [], "path": ["blender.exe"],
        "aide": "copier Blender 5.2 dans outils\\blender\\",
    },
    "oda_convertisseur": {
        "cle": "ODA_CONVERTISSEUR", "nom": "ODA File Converter", "portable": "oda\\convertisseur",
        "exe": "ODAFileConverter.exe",
        "motifs": [(b, "ODA", "ODAFileConverter*") for b in _BASES_PF],
        "prefixe": "ODAFileConverter", "visee": None, "fixes": [], "path": ["ODAFileConverter.exe"],
        "aide": "copier ODA File Converter dans outils\\oda\\convertisseur\\",
    },
    "oda_visionneuse": {
        "cle": "ODA_VISIONNEUSE", "nom": "ODA Viewer", "portable": "oda\\visionneuse", "exe": "ODAViewer.exe",
        "motifs": [(b, "ODA", "ODA Viewer*") for b in _BASES_PF],
        "prefixe": "ODA Viewer", "visee": None, "fixes": [], "path": ["ODAViewer.exe"],
        "aide": "copier ODA Viewer dans outils\\oda\\visionneuse\\",
    },
    "node": {
        "cle": "NODE", "nom": "Node.js", "portable": "node", "exe": "node.exe",
        "motifs": [], "prefixe": "", "visee": None,
        "fixes": [(b, r"nodejs\node.exe") for b in _BASES_PF], "path": ["node.exe"],
        "aide": "copier Node.js dans outils\\node\\",
    },
    "navigateur": {
        "cle": "NAVIGATEUR", "nom": "Navigateur (PDF)", "portable": None, "exe": None,
        "motifs": [], "prefixe": "", "visee": None, "fixes": [], "path": [],
        "aide": "Edge est normalement fourni par Windows ; sinon installer Edge ou Chrome",
    },
    "claude": {
        "cle": "CLAUDE", "nom": "Claude Code", "portable": "claude", "exe": "claude.exe",
        "motifs": [], "prefixe": "", "visee": None, "fixes": [], "path": [],
        "ordre": ("systeme", "portable"),
        "aide": "installer Claude Code (npm install -g @anthropic-ai/claude-code), "
                "ou garder la copie portable outils\\claude\\claude.exe",
    },
    # PostgreSQL : on résout pg_ctl.exe, mais la variable de session est le DOSSIER bin.
    "postgres": {
        "cle": "POSTGRES", "nom": "PostgreSQL", "portable": "postgresql", "exe": "bin\\pg_ctl.exe",
        "motifs": [(b, "PostgreSQL", "*") for b in _BASES_PF],
        "prefixe": "", "visee": VERSION_POSTGRES_VISEE, "fixes": [], "path": ["pg_ctl.exe"],
        "dossier": True, "variable_dossier": True,
        "aide": "copier les dossiers bin, lib et share de PostgreSQL 18 dans outils\\postgresql\\",
    },
    # Git Bash : jamais cherché par son nom dans le PATH (le bash.exe de System32 est celui
    # de WSL) ; à défaut des emplacements connus, on part du git.exe du PATH.
    "git_bash": {
        "cle": "GIT_BASH", "nom": "Git Bash", "portable": "git", "exe": "bin\\bash.exe",
        "motifs": [], "prefixe": "", "visee": None,
        "fixes": [(b, r"Git\bin\bash.exe") for b in _BASES_PF] + [("LOCALAPPDATA", r"Programs\Git\bin\bash.exe")],
        "path": [], "git_du_path": True, "variable_dossier": True,
        "aide": "copier Git for Windows (le dossier Git de Program Files, en entier) dans outils\\git\\",
    },
    "gh": {
        "cle": "GH", "nom": "GitHub CLI", "portable": "gh", "exe": "gh.exe",
        "motifs": [], "prefixe": "", "visee": None,
        "fixes": [(b, r"GitHub CLI\gh.exe") for b in _BASES_PF], "path": ["gh.exe"],
        "aide": "copier GitHub CLI (gh.exe) dans outils\\gh\\",
    },
}

_EDGE = [(b, r"Microsoft\Edge\Application\msedge.exe") for b in ("ProgramFiles(x86)", "ProgramW6432", "ProgramFiles")] \
    + [("LOCALAPPDATA", r"Microsoft\Edge\Application\msedge.exe")]
_CHROME = [(b, r"Google\Chrome\Application\chrome.exe") for b in _BASES_PF] \
    + [("LOCALAPPDATA", r"Google\Chrome\Application\chrome.exe")]


class OutilIntrouvable(FileNotFoundError):
    """Un outil du poste est introuvable ; le message dit où on a cherché et quoi faire."""


class Verification(tuple):
    """Résultat de verifier() : un 4-uplet (outil, chemin, ok, version).

    Il porte en plus .origine ('portable', 'systeme', 'variable' ou 'absent') et
    .detail (la cause, quand ok est faux, ou une remarque)."""

    def __new__(cls, outil, chemin, ok, version, origine="", detail=""):
        obj = tuple.__new__(cls, (outil, chemin, bool(ok), version))
        obj.origine = origine
        obj.detail = detail
        return obj

    def __getnewargs__(self):
        return (self[0], self[1], self[2], self[3], self.origine, self.detail)

    outil = property(lambda self: self[0])
    chemin = property(lambda self: self[1])
    ok = property(lambda self: self[2])
    version = property(lambda self: self[3])

    def en_dict(self):
        return {"outil": self[0], "chemin": self[1], "ok": self[2], "version": self[3],
                "origine": self.origine, "detail": self.detail}

    def __repr__(self):
        return "Verification(%r, %r, %r, %r, origine=%r, detail=%r)" % (
            self[0], self[1], self[2], self[3], self.origine, self.detail)


# --------------------------------------------------------------------------- petits outils

def _env(nom):
    v = os.environ.get(nom)
    return v.strip().strip('"') if v else ""


def _est_fichier(p):
    try:
        return bool(p) and os.path.isfile(p)
    except (OSError, ValueError):
        return False


def _est_dossier(p):
    try:
        return bool(p) and os.path.isdir(p)
    except (OSError, ValueError):
        return False


def _norm(p):
    """Clé de comparaison d'un chemin : casse et séparateurs normalisés, sans barre finale."""
    return os.path.normcase(os.path.abspath(p)).rstrip("\\/")


def _sous(chemin, dossier):
    """Vrai si chemin est dans dossier (ou est dossier)."""
    if not chemin or not dossier:
        return False
    c, d = _norm(chemin), _norm(dossier)
    return c == d or c.startswith(d + os.sep)


def _racine_module():
    if not _ICI:
        raise OutilIntrouvable(
            "Racine du poste inconnue : chemins.py a été chargé sans __file__. "
            "Posez BM_RACINE (le dossier qui contient outils\\).")
    return os.path.dirname(_ICI)


def _version_nom(nom, prefixe):
    """Numéros tirés du nom d'un dossier versionné.

    'Blender 5.2' -> (5, 2) ; 'ODAFileConverter 27.1.0' -> (27, 1, 0) ; 'Python313' -> (3, 13)."""
    suite = nom[len(prefixe):] if prefixe and nom.lower().startswith(prefixe.lower()) else nom
    m = re.search(r"\d+(?:\.\d+)*", suite)
    if not m:
        return ()
    txt = m.group(0)
    if prefixe.lower() == "python" and "." not in txt and len(txt) >= 2:
        return (int(txt[0]), int(txt[1:]))
    return tuple(int(x) for x in txt.split("."))


def _cle_tri(version, visee, nom, index):
    """Clé de tri (décroissant) : la version visée d'abord, puis la plus récente,
    le 64 bits avant le 32 bits (« -32 »), puis l'ordre de découverte."""
    v4 = (tuple(version) + (0, 0, 0, 0))[:4]
    vise = 1 if (visee and len(version) >= len(visee) and tuple(version[:len(visee)]) == tuple(visee)) else 0
    n64 = 0 if nom.lower().endswith("-32") else 1
    return (vise, v4, n64, -index)


def _nettoyer_version(v):
    v = (v or "").strip()
    return re.sub(r"^(\d+\.\d+\.\d+)\.0$", r"\1", v) or None


def _dans_path(exe):
    """Premier exe trouvé dans le PATH, sans les alias du Microsoft Store (WindowsApps)."""
    for d in os.environ.get("PATH", "").split(os.pathsep):
        d = d.strip().strip('"')
        if not d:
            continue
        if "windowsapps" in os.path.normcase(d).replace("/", "\\").split("\\"):
            continue
        p = os.path.join(d, exe)
        if _est_fichier(p):
            return os.path.abspath(p)
    return None


def _chercher_versionne(motifs, exe, prefixe, visee):
    """Cherche exe dans les sous-dossiers versionnés (motifs) ; rend le meilleur."""
    candidats = []
    bases_vues = set()
    index = 0
    for var, sous, motif in motifs:
        base = _env(var)
        if not base:
            continue
        dossier = os.path.join(base, sous) if sous else base
        cle_base = (_norm(dossier), motif.lower())
        if cle_base in bases_vues:
            continue
        bases_vues.add(cle_base)
        if not _est_dossier(dossier):
            continue
        trouves = [p for p in glob.glob(os.path.join(glob.escape(dossier), motif)) if _est_dossier(p)]
        for d in sorted(trouves, key=lambda p: os.path.basename(p).lower()):
            p = os.path.join(d, exe)
            if _est_fichier(p):
                nom = os.path.basename(d)
                candidats.append((_cle_tri(_version_nom(nom, prefixe), visee, nom, index), os.path.abspath(p)))
            index += 1
    if not candidats:
        return None
    candidats.sort(key=lambda c: c[0], reverse=True)
    return candidats[0][1]


def _chercher_fixes(fixes):
    for var, rel in fixes:
        base = _env(var)
        if base:
            p = os.path.join(base, rel)
            if _est_fichier(p):
                return os.path.abspath(p)
    return None


def _portable(d, rac):
    if not d.get("portable"):
        return None
    base = os.path.join(rac, "outils", d["portable"])
    p = os.path.join(base, d["exe"])
    if _est_fichier(p):
        return os.path.abspath(p)
    if _est_dossier(base):
        sous = [os.path.join(base, n) for n in os.listdir(base)]
        for s in sorted((x for x in sous if _est_dossier(x)), key=lambda x: os.path.basename(x).lower()):
            q = os.path.join(s, d["exe"])
            if _est_fichier(q):
                return os.path.abspath(q)
    return None


def _claude_systeme():
    p = _dans_path("claude.cmd")
    if p:
        exe = os.path.join(os.path.dirname(p), "node_modules", "@anthropic-ai", "claude-code", "bin", "claude.exe")
        return os.path.abspath(exe) if _est_fichier(exe) else p
    p = _dans_path("claude.exe")
    if p:
        return p
    for var, rel in (("USERPROFILE", r".local\bin\claude.exe"),
                     ("APPDATA", r"npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe"),
                     ("APPDATA", r"npm\claude.cmd")):
        base = _env(var)
        if base and _est_fichier(os.path.join(base, rel)):
            return os.path.abspath(os.path.join(base, rel))
    return None


def _bash_du_git():
    """bash.exe du Git for Windows dont le git.exe est dans le PATH (<Git>\\cmd, <Git>\\bin
    ou <Git>\\mingw64\\bin) : <Git>\\bin\\bash.exe."""
    g = _dans_path("git.exe")
    if not g:
        return None
    d = os.path.dirname(g)
    for c in (os.path.join(os.path.dirname(d), "bin", "bash.exe"),
              os.path.join(os.path.dirname(os.path.dirname(d)), "bin", "bash.exe")):
        if _est_fichier(c):
            return os.path.abspath(c)
    return None


def _exe_du_dossier(valeur, d):
    """Une variable BM_* posée à la main peut désigner un DOSSIER (outils « variable_dossier ») :
    le dossier de l'exécutable ou la racine de l'outil ; pour PostgreSQL, aussi un autre
    exécutable de bin. Rend le chemin de l'exécutable attendu (tel quel s'il n'y est pas :
    le message d'erreur dira alors qu'il n'existe pas)."""
    nom = os.path.basename(d["exe"])
    if _est_dossier(valeur):
        for c in (os.path.join(valeur, nom), os.path.join(valeur, d["exe"])):
            if _est_fichier(c):
                return c
        return os.path.join(valeur, nom)
    if d.get("dossier") and _est_fichier(valeur) and os.path.basename(valeur).lower() != nom.lower():
        c = os.path.join(os.path.dirname(valeur), nom)
        if _est_fichier(c):
            return c
    return valeur


def _systeme(outil, d, prefere):
    if outil == "navigateur":
        listes = (_CHROME, _EDGE) if prefere == "chrome" else (_EDGE, _CHROME)
        for liste in listes:
            p = _chercher_fixes(liste)
            if p:
                return p
        return None
    if outil == "claude":
        return _claude_systeme()
    p = None
    if d["motifs"]:
        p = _chercher_versionne(d["motifs"], d["exe"], d["prefixe"], d["visee"])
    if not p and d["fixes"]:
        p = _chercher_fixes(d["fixes"])
    if not p:
        for exe in d["path"]:
            p = _dans_path(exe)
            if p:
                break
    if not p and d.get("git_du_path"):
        p = _bash_du_git()
    return p


def _definition(outil):
    try:
        return _DEFS[outil]
    except KeyError:
        raise ValueError("Outil inconnu : %r (connus : %s)" % (outil, ", ".join(sorted(_DEFS))))


def _lieux_systeme(outil, d, prefere):
    """Texte des lieux du système fouillés, pour le message d'erreur."""
    lieux = []
    if outil == "navigateur":
        for var, rel in ((_CHROME + _EDGE) if prefere == "chrome" else (_EDGE + _CHROME)):
            base = _env(var)
            if base:
                lieux.append(os.path.join(base, rel))
    elif outil == "claude":
        lieux.append("claude.cmd ou claude.exe dans le PATH, %USERPROFILE%\\.local\\bin, %APPDATA%\\npm")
    else:
        for var, sous, motif in d["motifs"]:
            base = _env(var)
            if base:
                lieux.append(os.path.join(base, sous, motif, d["exe"]) if sous else os.path.join(base, motif, d["exe"]))
        for var, rel in d["fixes"]:
            base = _env(var)
            if base:
                lieux.append(os.path.join(base, rel))
        if d["path"]:
            lieux.append("le PATH (%s)" % ", ".join(d["path"]))
        if d.get("git_du_path"):
            lieux.append("le git.exe du PATH (son voisin bin\\bash.exe)")
    vus, uniques = set(), []
    for l in lieux:
        k = l.lower()
        if k not in vus:
            vus.add(k)
            uniques.append(l)
    return uniques or ["(aucune variable ProgramFiles / LOCALAPPDATA posée)"]


def _message_absent(outil, d, rac, prefere):
    var = "BM_" + d["cle"]
    lignes = ["%s introuvable." % d["nom"], "Cherché, dans l'ordre :"]
    n = 1
    etapes = d.get("ordre", ("portable", "systeme"))
    lignes.append("  %d. la variable %s : non posée ;" % (n, var))
    for etape in etapes:
        n += 1
        if etape == "portable":
            if d.get("portable"):
                lignes.append("  %d. la copie portable : %s ;" % (n, os.path.join(rac, "outils", d["portable"], d["exe"])))
            else:
                lignes.append("  %d. (pas de copie portable prévue pour cet outil) ;" % n)
        else:
            lignes.append("  %d. l'installation du poste : %s." % (n, " ; ".join(_lieux_systeme(outil, d, prefere))))
    lignes.append("Que faire : %s (voir outils\\LISEZMOI.md), ou poser la variable %s "
                  "(chemin complet de l'exécutable)." % (d["aide"], var))
    return "\n".join(lignes)


def _resoudre(outil, prefere, rac, session):
    """Cœur de la résolution. session=True reproduit chemins.ps1 / chemins.cmd :
    une BM_* posée par une session précédente (BM_ORIGINE_* autre que 'variable')
    est recalculée, et une BM_* invalide est ignorée au lieu de lever."""
    d = _definition(outil)
    var = "BM_" + d["cle"]
    valeur = _env(var)
    auto = _env("BM_ORIGINE_" + d["cle"])
    if session and valeur and auto and auto != "variable":
        valeur = ""
    if prefere:
        prefere = str(prefere).strip().lower()
    mot_cle = False
    if outil == "navigateur" and valeur.lower() in ("edge", "chrome"):
        prefere, valeur, mot_cle = valeur.lower(), "", True
    if valeur and d.get("variable_dossier"):
        valeur = _exe_du_dossier(valeur, d)
    if valeur:
        if _est_fichier(valeur):
            chemin = os.path.abspath(valeur)
            if _sous(chemin, rac):
                return chemin, "portable"
            if not session and auto == "systeme":
                return chemin, "systeme"
            return chemin, "variable"
        if not session:
            raise OutilIntrouvable(
                "%s : la variable %s pointe vers « %s », qui n'existe pas.\n"
                "Corrigez-la, ou effacez-la : on prend alors la copie portable (outils\\%s), "
                "puis l'installation du poste." % (d["nom"], var, valeur, d.get("portable") or "..."))
    for etape in d.get("ordre", ("portable", "systeme")):
        if etape == "portable":
            p = _portable(d, rac)
            if p:
                return p, "portable"
        else:
            p = _systeme(outil, d, prefere)
            if p:
                return p, ("variable" if mot_cle else "systeme")
    raise OutilIntrouvable(_message_absent(outil, d, rac, prefere))


# --------------------------------------------------------------------------- interface

def racine():
    """Dossier du poste (celui qui contient outils\\). BM_RACINE a priorité ;
    sinon il se déduit de l'emplacement de ce fichier."""
    v = _env("BM_RACINE")
    if v:
        if not _est_dossier(v):
            raise OutilIntrouvable(
                "La variable BM_RACINE pointe vers « %s », qui n'est pas un dossier.\n"
                "Corrigez-la, ou effacez-la : la racine se déduit alors de l'emplacement "
                "de outils\\chemins.py." % v)
        return os.path.abspath(v)
    return _racine_module()


def resoudre(outil, prefere=None):
    """Rend (chemin, origine) de l'outil ; origine : 'variable', 'portable' ou 'systeme'.

    outil : 'python', 'blender', 'oda_convertisseur', 'oda_visionneuse', 'node',
    'navigateur' ou 'claude'. Lève OutilIntrouvable si rien n'est trouvé."""
    return _resoudre(outil, prefere, racine(), False)


def python_exe():
    """Le Python du poste (celui qui a ezdxf) — pas celui de Blender."""
    return resoudre("python")[0]


def blender_exe():
    return resoudre("blender")[0]


def oda_convertisseur():
    return resoudre("oda_convertisseur")[0]


def oda_visionneuse():
    return resoudre("oda_visionneuse")[0]


def node_exe():
    return resoudre("node")[0]


def navigateur_pdf(prefere=None):
    """Navigateur pour produire ou montrer un PDF : Edge par défaut (fourni par
    Windows), Chrome sur demande (prefere='chrome', ou BM_NAVIGATEUR=chrome).
    BM_NAVIGATEUR peut aussi donner le chemin complet d'un exécutable."""
    return resoudre("navigateur", prefere)[0]


def claude_exe():
    """Claude Code : l'installation du poste d'abord, sinon outils\\claude\\claude.exe."""
    return resoudre("claude")[0]


def postgres_bin():
    """Dossier bin de PostgreSQL 18 (initdb, pg_ctl, postgres, psql, pg_dump, pg_restore,
    pg_isready...) : BM_POSTGRES, puis outils\\postgresql\\bin, puis le PostgreSQL du poste."""
    return os.path.dirname(resoudre("postgres")[0])


def git_bash():
    """bash.exe de Git for Windows (Git Bash) : BM_GIT_BASH, puis outils\\git\\bin\\bash.exe,
    puis le Git du poste. C'est ce chemin que Claude Code attend dans CLAUDE_CODE_GIT_BASH_PATH."""
    return resoudre("git_bash")[0]


def _git_du_bash(bash):
    racine_git = os.path.dirname(os.path.dirname(bash))
    for rel in (r"cmd\git.exe", r"bin\git.exe", r"mingw64\bin\git.exe"):
        p = os.path.join(racine_git, rel)
        if _est_fichier(p):
            return os.path.abspath(p)
    return None


def git_exe():
    """git.exe du MÊME Git que git_bash() : <Git>\\cmd\\git.exe (à défaut bin ou mingw64\\bin)."""
    bash = git_bash()
    p = _git_du_bash(bash)
    if not p:
        raise OutilIntrouvable("git.exe introuvable à côté de %s (cherché dans cmd, bin et mingw64\\bin).\n"
                               "Que faire : recopier Git for Windows en entier dans outils\\git\\ "
                               "(voir outils\\LISEZMOI.md), ou poser BM_GIT_BASH." % bash)
    return p


def gh_exe():
    """GitHub CLI : BM_GH, puis outils\\gh\\gh.exe, puis le gh du poste. Sa connexion à GitHub
    (gh auth login) reste celle de l'utilisateur Windows : rien n'est rangé dans le dossier."""
    return resoudre("gh")[0]


def configurer_ezdxf_odafc(chemin=None):
    """Dit à ezdxf où est ODA File Converter (en mémoire seulement : rien n'est
    écrit dans la configuration d'ezdxf). Rend le chemin retenu.

    ezdxf essaie D'ABORD shutil.which("ODAFileConverter"), puis seulement win_exec_path
    (vérifié par l'agent C) : si le PATH mène à un AUTRE ODA, le dossier retenu est mis
    en tête du PATH de ce processus ; s'il en reste un autre, un avertissement le dit."""
    exe = os.path.abspath(chemin or oda_convertisseur())
    trouve = shutil.which("ODAFileConverter")
    if trouve and _norm(trouve) != _norm(exe):
        os.environ["PATH"] = os.path.dirname(exe) + os.pathsep + os.environ.get("PATH", "")
        trouve = shutil.which("ODAFileConverter")
        if trouve and _norm(trouve) != _norm(exe):
            import warnings
            warnings.warn("ezdxf prendra %s (trouvé dans le PATH) et non %s" % (trouve, exe), RuntimeWarning)
    try:
        import ezdxf
    except ImportError:
        try:
            conseil = python_exe()
        except OutilIntrouvable:
            conseil = "(introuvable)"
        raise ImportError(
            "ezdxf n'est pas installé dans ce Python (%s). Lancez le script avec le "
            "Python du poste : %s" % (sys.executable, conseil))
    ezdxf.options.set("odafc-addon", "win_exec_path", exe)
    try:  # anciennes versions d'ezdxf : variable de module
        from ezdxf.addons import odafc
        if hasattr(odafc, "win_exec_path"):
            odafc.win_exec_path = exe
    except Exception:
        pass
    return exe


def projet_en_cours(detail=False):
    """Dossier du projet en cours, ou None.

    1. outils\\projet_en_cours.txt : première ligne utile (ni vide ni « # »), chemin
       relatif à la racine (..\\Maison_X) ou absolu ;
    2. sinon le dossier voisin de la racine dont un parametres_*.py est le plus récent.
    detail=True rend (chemin, origine) ; origine : 'fichier', 'recent',
    'recent-fichier-invalide' ou 'absent'."""
    return _projet(racine(), detail)


def _projet(rac, detail):
    fichier = os.path.join(rac, "outils", "projet_en_cours.txt")
    invalide = False
    if _est_fichier(fichier):
        valeur = ""
        try:
            with open(fichier, "r", encoding="utf-8-sig") as f:
                for ligne in f:
                    ligne = ligne.strip().strip('"')
                    if ligne and not ligne.startswith("#"):
                        valeur = ligne
                        break
        except OSError:
            valeur = ""
        if valeur:
            # join : un chemin absolu l'emporte (même règle que [IO.Path]::Combine dans chemins.ps1).
            p = os.path.normpath(os.path.abspath(os.path.join(rac, valeur)))
            if _est_dossier(p):
                return (p, "fichier") if detail else p
        invalide = True
    parent = os.path.dirname(os.path.abspath(rac)) or rac  # racine au bord d'un lecteur : elle-même
    meilleur = None
    try:
        noms = os.listdir(parent)
    except OSError:
        noms = []
    for nom in noms:
        dossier = os.path.join(parent, nom)
        if not _est_dossier(dossier) or _norm(dossier) == _norm(rac):
            continue
        for f in glob.glob(os.path.join(glob.escape(dossier), "parametres_*.py")):
            try:
                t = os.path.getmtime(f)
            except OSError:
                continue
            cle = (t, dossier.lower())
            if meilleur is None or cle[0] > meilleur[0][0] or (cle[0] == meilleur[0][0] and cle[1] < meilleur[0][1]):
                meilleur = (cle, os.path.abspath(dossier))
    if meilleur:
        origine = "recent-fichier-invalide" if invalide else "recent"
        return (meilleur[1], origine) if detail else meilleur[1]
    return (None, "absent") if detail else None


def _env_blender_portable(blender, environ):
    """Variables à poser (valeur '' = à retirer) pour la copie PORTABLE de Blender.

    Consignes vérifiées par l'agent B (outils\\blender\\PRET.txt) :
    - les BLENDER_USER_* et BLENDER_SYSTEM_* héritées primeraient sur outils\\blender\\portable ;
    - BLENDER_SYSTEM_RESOURCES = dossier de version (5.2) à côté de blender.exe : sinon un
      C:\\ProgramData\\Blender Foundation\\Blender\\<v> passerait avant les ressources embarquées ;
    - CUDA_CACHE_PATH = outils\\blender\\portable\\cuda_cache : sinon le pilote NVIDIA écrit
      dans %APPDATA%\\NVIDIA\\ComputeCache."""
    e = {}
    for k in sorted(k.upper() for k in environ):
        if re.match(r"^BLENDER_(USER|SYSTEM)_", k):
            e[k] = ""
    d = os.path.dirname(blender)
    versions = []
    try:
        noms = os.listdir(d)
    except OSError:
        noms = []
    for n in noms:
        if re.match(r"^\d+\.\d+$", n) and _est_dossier(os.path.join(d, n)):
            versions.append((tuple(int(x) for x in n.split(".")), n))
    if versions:
        e["BLENDER_SYSTEM_RESOURCES"] = os.path.abspath(os.path.join(d, max(versions)[1]))
    e["CUDA_CACHE_PATH"] = os.path.join(d, "portable", "cuda_cache")
    return e


def _definies(environ):
    """Noms (en majuscules) des variables posées et non vides."""
    return {k.upper() for k, v in environ.items() if v}


def _env_portables(v, environ):
    """Variables propres aux copies PORTABLES (valeur '' = à retirer), d'après les consignes
    vérifiées des agents (outils\\*\\PRET.txt) :
    - Python : PYTHONNOUSERSITE=1, sans PYTHONHOME ni PYTHONPATH hérités (sinon le site
      utilisateur ou un autre Python passerait avant la copie) ;
    - Blender : voir _env_blender_portable ;
    - ODA : sans QT_PLUGIN_PATH ni QT_QPA_PLATFORM_PLUGIN_PATH hérités (Qt irait ailleurs) ;
    - Node : sans NODE_OPTIONS ni NODE_PATH hérités ; et, pour tout Node trouvé,
      npm_config_update_notifier=false (sinon, sur un profil neuf, la 1re commande npm
      interroge le registre en ligne et bloque environ 45 s), sauf si elle est déjà posée."""
    definies = _definies(environ)
    e = {}
    if v.get("BM_ORIGINE_PYTHON") == "portable":
        for k in ("PYTHONHOME", "PYTHONPATH"):
            if k in definies:
                e[k] = ""
        e["PYTHONNOUSERSITE"] = "1"
    if v.get("BM_ORIGINE_BLENDER") == "portable":
        e.update(_env_blender_portable(v["BM_BLENDER"], environ))
    if "portable" in (v.get("BM_ORIGINE_ODA_CONVERTISSEUR"), v.get("BM_ORIGINE_ODA_VISIONNEUSE")):
        for k in ("QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH"):
            if k in definies:
                e[k] = ""
    if v.get("BM_ORIGINE_NODE") == "portable":
        for k in ("NODE_OPTIONS", "NODE_PATH"):
            if k in definies:
                e[k] = ""
    if v.get("BM_NODE") and "NPM_CONFIG_UPDATE_NOTIFIER" not in definies:
        e["npm_config_update_notifier"] = "false"
    # Claude Code trouve Git Bash par cette variable (Windows) : le Git retenu, portable d'abord.
    # Pour en changer, poser BM_GIT_BASH, qui a priorité.
    if v.get("BM_GIT_BASH"):
        e["CLAUDE_CODE_GIT_BASH_PATH"] = v["BM_GIT_BASH"]
    return e


def _config_claude(rac, environ=None):
    """Variable CLAUDE_CONFIG_DIR de la session (valeur '' = à retirer), ou {} si rien à poser.

    « Zéro trace » (2026-09-25) : la configuration de Claude Code (réglages, compétences, plugins,
    mémoire, sessions, .claude.json, identifiants après la 1re connexion) vit dans
    <racine>\\outils\\claude\\config, s'il existe (créé par outils\\claude_config.py migrer).
    BM_CLAUDE_CONFIG=profil : retour arrière, le profil de l'utilisateur (%USERPROFILE%\\.claude) ;
    BM_CLAUDE_CONFIG=<dossier> : ce dossier-là."""
    environ = os.environ if environ is None else environ
    v = (environ.get("BM_CLAUDE_CONFIG") or "").strip().strip('"')
    if v.lower() == "profil":
        return {"CLAUDE_CONFIG_DIR": ""} if "CLAUDE_CONFIG_DIR" in _definies(environ) else {}
    if v:
        return {"CLAUDE_CONFIG_DIR": os.path.abspath(v)}
    d = os.path.join(rac, "outils", "claude", "config")
    if _est_dossier(d):
        return {"CLAUDE_CONFIG_DIR": d}
    return {}


def config_claude():
    """Le dossier de configuration de Claude Code que le lanceur pose, ou None (profil de l'utilisateur)."""
    return _config_claude(racine()).get("CLAUDE_CONFIG_DIR") or None


def env_blender(base=None):
    """Environnement pour lancer blender_exe() hors d'une session du lanceur :
    copie de os.environ (ou de base), corrigée pour la copie portable de Blender.

        subprocess.run([chemins.blender_exe(), "-b", ...], env=chemins.env_blender())"""
    env = dict(os.environ if base is None else base)
    chemin, origine = resoudre("blender")
    if origine == "portable":
        for k, v in _env_blender_portable(chemin, env).items():
            for existante in [x for x in env if x.upper() == k]:
                del env[existante]
            if v:
                env[k] = v
    return env


def variables_session():
    """Les variables qu'un lanceur poserait maintenant (même logique que chemins.ps1) :
    BM_RACINE (toujours l'emplacement de ce fichier), BM_<OUTIL> et BM_ORIGINE_<OUTIL>
    ('portable', 'systeme', 'variable' ou 'absent'), BM_PROJET et BM_ORIGINE_PROJET ;
    puis celles des copies portables (_env_portables : valeur vide = à retirer).
    BM_POSTGRES est le DOSSIER bin ; BM_GIT_BASH le bash.exe de Git (et CLAUDE_CODE_GIT_BASH_PATH)."""
    rac = _racine_module()
    r = {"BM_RACINE": rac}
    for outil in OUTILS_SESSION:
        cle = _DEFS[outil]["cle"]
        try:
            chemin, origine = _resoudre(outil, None, rac, True)
        except OutilIntrouvable:
            chemin, origine = "", "absent"
        if chemin and _DEFS[outil].get("dossier"):
            chemin = os.path.dirname(chemin)
        r["BM_" + cle] = chemin
        r["BM_ORIGINE_" + cle] = origine
    p, o = _projet(rac, True)
    r["BM_PROJET"] = p or ""
    r["BM_ORIGINE_PROJET"] = o
    r.update(_env_portables(r, os.environ))
    r.update(_config_claude(rac))
    return r


def path_session(variables=None, path_actuel=None):
    """Le PATH d'une session : dossier de Python, de Node et d'ODA File Converter, puis le
    dossier cmd de Git et celui de GitHub CLI, en TÊTE, puis l'ancien PATH sans ces mêmes
    dossiers (ni entrées vides). PostgreSQL n'y est PAS : ses scripts l'appellent par
    BM_POSTGRES, et ses DLL (libpq, OpenSSL...) ne doivent pas passer devant d'autres.
    Git : son dossier cmd seulement (git.exe) ; jamais bin ni usr\\bin, dont les find.exe,
    sort.exe... masqueraient ceux de Windows.

    - PAS le Scripts du Python portable (décision du chef, 2026-09-25) : ses lanceurs
      pip.exe, pytest.exe… gardent en dur le chemin de l'ANCIEN Python (agent A). Il est
      même retiré de l'ancien PATH. On passe par « python -m pip » et « python -m pytest ».
    - ODA y est parce qu'ezdxf essaie shutil.which("ODAFileConverter") AVANT son réglage
      win_exec_path : un autre ODA du PATH passerait sinon avant la copie portable."""
    v = variables if variables is not None else variables_session()
    ancien = os.environ.get("PATH", "") if path_actuel is None else path_actuel

    def cle(p):
        return p.strip().strip('"').replace("/", "\\").rstrip("\\").lower()

    tete, exclus = [], set()
    py = v.get("BM_PYTHON")
    if py:
        d = os.path.dirname(py)
        tete.append(d)
        if v.get("BM_ORIGINE_PYTHON") == "portable":
            exclus.add(cle(os.path.join(d, "Scripts")))
    nd = v.get("BM_NODE")
    if nd:
        tete.append(os.path.dirname(nd))
    oda = v.get("BM_ODA_CONVERTISSEUR")
    if oda:
        tete.append(os.path.dirname(oda))
    bash = v.get("BM_GIT_BASH")
    if bash:
        cmd_git = os.path.join(os.path.dirname(os.path.dirname(bash)), "cmd")
        if _est_dossier(cmd_git):
            tete.append(cmd_git)
    gh = v.get("BM_GH")
    if gh:
        tete.append(os.path.dirname(gh))

    vus, uniques = set(), []
    for t in tete:
        if cle(t) not in vus:
            vus.add(cle(t))
            uniques.append(t)
    reste = [p for p in ancien.split(";") if p.strip() and cle(p) not in vus and cle(p) not in exclus]
    return ";".join(uniques + reste)


# --------------------------------------------------------------------------- vérification

def _version_fichier(chemin):
    """Version inscrite dans l'exécutable (ressource VERSIONINFO), sans le lancer."""
    if os.name != "nt" or not _est_fichier(chemin):
        return None
    try:
        import ctypes
        from ctypes import wintypes
        dll = ctypes.WinDLL("version")
        dll.GetFileVersionInfoSizeW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD)]
        dll.GetFileVersionInfoSizeW.restype = wintypes.DWORD
        dll.GetFileVersionInfoW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]
        dll.GetFileVersionInfoW.restype = wintypes.BOOL
        dll.VerQueryValueW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR,
                                       ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.UINT)]
        dll.VerQueryValueW.restype = wintypes.BOOL
        taille = dll.GetFileVersionInfoSizeW(chemin, None)
        if not taille:
            return None
        tampon = ctypes.create_string_buffer(taille)
        adresse = ctypes.cast(tampon, ctypes.c_void_p)
        if not dll.GetFileVersionInfoW(chemin, 0, taille, adresse):
            return None
        ptr, lg = ctypes.c_void_p(), wintypes.UINT()
        if dll.VerQueryValueW(adresse, "\\VarFileInfo\\Translation", ctypes.byref(ptr), ctypes.byref(lg)) \
                and lg.value >= 4 and ptr.value:
            langue, page = struct.unpack("<HH", ctypes.string_at(ptr.value, 4))
            for cle in ("ProductVersion", "FileVersion"):
                p2, l2 = ctypes.c_void_p(), wintypes.UINT()
                sous = "\\StringFileInfo\\%04x%04x\\%s" % (langue, page, cle)
                if dll.VerQueryValueW(adresse, sous, ctypes.byref(p2), ctypes.byref(l2)) and l2.value and p2.value:
                    txt = ctypes.wstring_at(p2.value, l2.value).split("\x00")[0].strip()
                    if txt:
                        return _nettoyer_version(txt)
        if dll.VerQueryValueW(adresse, "\\", ctypes.byref(ptr), ctypes.byref(lg)) and lg.value >= 16 and ptr.value:
            sig, _struc, ms, ls = struct.unpack("<IIII", ctypes.string_at(ptr.value, 16))
            if sig == 0xFEEF04BD:
                return _nettoyer_version("%d.%d.%d.%d" % (ms >> 16, ms & 0xFFFF, ls >> 16, ls & 0xFFFF))
    except Exception:
        return None
    return None


def _executer(args, delai=120):
    """Lance une commande courte ; rend (code, sortie ASCII, erreur ASCII) ou (None, '', message)."""
    options = {}
    if os.name == "nt":
        options["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    try:
        r = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           stdin=subprocess.DEVNULL, timeout=delai, **options)
    except (OSError, subprocess.SubprocessError) as e:
        return None, "", "%s: %s" % (type(e).__name__, e)
    return (r.returncode, r.stdout.decode("ascii", "replace").strip(),
            r.stderr.decode("ascii", "replace").strip())


_SONDE_PYTHON = (
    "import sys\n"
    "print('PY=' + sys.version.split()[0])\n"
    "try:\n"
    "    import ezdxf\n"
    "    print('EZDXF=' + ezdxf.__version__)\n"
    "except Exception as e:\n"
    "    print(('EZDXF_ERREUR=' + type(e).__name__ + ': ' + str(e)).encode('ascii', 'backslashreplace').decode())\n"
)


def _sonder_python(py, strict):
    """Lance le Python trouvé : sa version et celle d'ezdxf. strict (copie portable) :
    -E -s, pour prouver qu'il marche sans rien du profil de l'utilisateur."""
    args = [py] + (["-E", "-s"] if strict else []) + ["-c", _SONDE_PYTHON]
    code, sortie, err = _executer(args)
    v_py = v_ez = None
    erreur_ez = ""
    for ligne in sortie.splitlines():
        if ligne.startswith("PY="):
            v_py = ligne[3:].strip()
        elif ligne.startswith("EZDXF="):
            v_ez = ligne[6:].strip()
        elif ligne.startswith("EZDXF_ERREUR="):
            erreur_ez = ligne[13:].strip()
    if not v_py:
        return False, None, None, "ne démarre pas (%s)" % (err.splitlines()[-1] if err else "code %s" % code), ""
    return True, v_py, v_ez, "", erreur_ez or ("" if v_ez else "ezdxf absent")


def _version_executee(outil, chemin):
    if not chemin.lower().endswith(".exe"):
        return None, "pas un .exe"
    args = [chemin, "--version"]
    if outil == "blender":   # contrôle rapide conseillé par l'agent B
        args = [chemin, "-b", "--factory-startup", "--version"]
    elif outil == "git_bash":   # la version de Git, par le git.exe du même Git
        g = _git_du_bash(chemin)
        if not g:
            return None, "git.exe introuvable à côté de bash.exe"
        args = [g, "--version"]
    code, sortie, err = _executer(args, delai=120)
    if code != 0 or not sortie:
        return None, "ne démarre pas (%s)" % ((err.splitlines() or ["code %s" % code])[-1])
    premiere = sortie.splitlines()[0].strip()
    if outil == "blender":
        premiere = re.sub(r"\s*\(hash.*$", "", re.sub(r"^Blender\s+", "", premiere))
    elif outil == "node":
        premiere = premiere.lstrip("v")
    elif outil == "claude":
        premiere = premiere.replace("(Claude Code)", "").strip()
    elif outil == "postgres":      # « pg_ctl (PostgreSQL) 18.1 »
        premiere = premiere.split()[-1]
    elif outil == "git_bash":      # « git version 2.50.1.windows.1 »
        premiere = premiere.replace("git version", "").strip()
    elif outil == "gh":            # « gh version 2.83.0 (2025-11-04) »
        premiere = (premiere.replace("gh version", "").split() or [""])[0]
    return premiere, ""


def verifier(complet=False):
    """Vérifie chaque outil ; rend une liste de Verification, des 4-uplets
    (outil, chemin, ok, version) qui portent aussi .origine et .detail.

    Outils : python, ezdxf, blender, oda_convertisseur, oda_visionneuse, node,
    postgres, git_bash, gh, navigateur, claude. Sans `complet`, seul Python est lancé
    (pour ezdxf) ; les autres versions sont lues dans les .exe. Avec `complet`, blender,
    node, postgres (pg_ctl), git, gh et claude sont lancés avec --version (quelques
    secondes). ODA n'est jamais lancé : sans arguments, il ouvre une fenêtre.
    Le chemin rendu pour postgres est le DOSSIER bin (comme BM_POSTGRES)."""
    res = []
    try:
        py, org = resoudre("python")
        ok, v_py, v_ez, err_py, err_ez = _sonder_python(py, org == "portable")
        res.append(Verification("python", py, ok, v_py, org, err_py))
        detail_ez = err_ez if not v_ez else ""
        res.append(Verification("ezdxf", py, bool(v_ez), v_ez, org, detail_ez))
    except OutilIntrouvable as e:
        res.append(Verification("python", None, False, None, "absent", str(e)))
        res.append(Verification("ezdxf", None, False, None, "absent", "pas de Python du poste"))
    for outil in ("blender", "oda_convertisseur", "oda_visionneuse", "node", "postgres", "git_bash", "gh",
                  "navigateur", "claude"):
        try:
            chemin, org = resoudre(outil)
        except OutilIntrouvable as e:
            res.append(Verification(outil, None, False, None, "absent", str(e)))
            continue
        version = _version_fichier(chemin)
        ok, detail = version is not None, ""
        if not ok:
            detail = "version illisible dans l'exécutable (fichier abîmé ou incomplet ?)"
        if complet and outil in ("blender", "node", "postgres", "git_bash", "gh", "claude"):
            v2, err = _version_executee(outil, chemin)
            if v2:
                version, ok, detail = v2, True, ""
            else:
                ok, detail = False, err
        if ok and outil == "postgres" and version and not version.startswith("%d." % VERSION_POSTGRES_VISEE[0]):
            detail = "le cluster du programme Métré est en PostgreSQL %d" % VERSION_POSTGRES_VISEE[0]
        if outil == "postgres":
            chemin = os.path.dirname(chemin)
        if ok and outil == "blender" and version and not version.startswith("%d.%d" % VERSION_BLENDER_VISEE):
            detail = "les scripts du poste sont écrits pour Blender %d.%d" % VERSION_BLENDER_VISEE
        if outil == "blender" and org == "portable" and len(racine()) > LONGUEUR_RACINE_MAX:
            detail = ("racine de %d caractères : blender.exe n'accepte pas les chemins longs, "
                      "gardez-la sous %d" % (len(racine()), LONGUEUR_RACINE_MAX))
        if outil == "navigateur":
            nom = os.path.basename(chemin).lower()
            detail = detail or ("Edge" if nom == "msedge.exe" else "Chrome" if nom == "chrome.exe" else nom)
        res.append(Verification(outil, chemin, ok, version, org, detail))
    return res


# --------------------------------------------------------------------------- ligne de commande

_ESSENTIELS = ("python", "ezdxf", "blender", "oda_convertisseur")


def _ascii(texte):
    import unicodedata
    t = unicodedata.normalize("NFKD", str(texte))
    t = t.replace("«", '"').replace("»", '"').replace("’", "'").replace("—", "-").replace("–", "-")
    return t.encode("ascii", "ignore").decode("ascii")


def _tableau(resultats, rac, projet, en_ascii):
    sortie = []
    ecrire = sortie.append
    ecrire("Poste Blender - vérification des outils (outils\\chemins.py)")
    ecrire("Racine : %s" % rac)
    if projet[0]:
        ecrire("Projet en cours : %s  (%s)" % projet)
    else:
        ecrire("Projet en cours : aucun")
    ecrire("")
    ecrire("  %-18s %-6s %-16s %-9s %s" % ("outil", "état", "version", "origine", "chemin"))
    for r in resultats:
        etat = "ok" if r.ok else "MANQUE"
        chemin = r.chemin or "-"
        if r.outil == "ezdxf" and r.chemin:
            chemin = "(dans ce Python)"
        ecrire("  %-18s %-6s %-16s %-9s %s" % (r.outil, etat, r.version or "-", r.origine or "-", chemin))
        if r.detail and (not r.ok or r.outil in ("blender", "navigateur", "postgres")):
            for ligne in str(r.detail).splitlines():
                ecrire("  %-18s        %s" % ("", ligne))
    replis = [r.outil for r in resultats
              if r.origine == "systeme" and r.outil not in ("navigateur", "claude", "ezdxf")]
    manques = [r.outil for r in resultats if not r.ok and r.outil in _ESSENTIELS]
    ecrire("")
    if replis:
        ecrire("Repli sur l'installation du poste : %s (pas encore de copie portable)." % ", ".join(replis))
    else:
        ecrire("Aucun repli sur l'installation du poste pour les outils de travail.")
    if manques:
        ecrire("MANQUE : %s." % ", ".join(manques))
    texte = "\n".join(sortie)
    return _ascii(texte) if en_ascii else texte


def _main(argv):
    args = list(argv)
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(errors="replace")
        except Exception:
            pass
    en_ascii = "--ascii" in args
    try:
        if "--projet" in args:
            p = projet_en_cours()
            print(p or "")
            return 0 if p else 1
        if "--variables" in args:
            v = variables_session()
            for k, val in v.items():
                print("%s=%s" % (k, val))
            print("PATH=%s" % path_session(v))
            return 0
        rac = racine()
        resultats = verifier(complet="--complet" in args)
        projet = _projet(rac, True)
        if "--json" in args:
            print(json.dumps({"racine": rac, "projet": projet[0], "origine_projet": projet[1],
                              "outils": [r.en_dict() for r in resultats]}, ensure_ascii=en_ascii, indent=2))
        else:
            print(_tableau(resultats, rac, projet, en_ascii))
        manque = any(not r.ok for r in resultats if r.outil in _ESSENTIELS)
        return 1 if manque else 0
    except OutilIntrouvable as e:
        print(_ascii(e) if en_ascii else str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
