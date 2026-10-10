# -*- coding: utf-8 -*-
r"""
outils\diagnostic\test_chemins.py -- tests du module de chemins (agent D, 2026-09-25).

Lancer, depuis la racine du poste :
    outils\python\python.exe outils\diagnostic\test_chemins.py        (unittest)
    outils\python\python.exe -m pytest outils\diagnostic\test_chemins.py

Tous les essais travaillent sur des dossiers TEMPORAIRES où de faux outils (fichiers
vides) jouent les copies portables et les installations du système : rien n'est
écrit dans le poste. Base temporaire : BM_TESTS_TEMP si elle est posée, sinon celle
du système.

Ce qui est vérifié :
  - la racine déduite de l'emplacement du module, et un dossier DÉPLACÉ ailleurs ;
  - les variables BM_* prioritaires, et BM_RACINE ;
  - la copie portable avant l'installation du système, puis le repli sur le système
    (version visée d'abord, puis la plus récente, tri numérique : 26.12 > 26.4) ;
  - un message clair en français quand rien n'existe ;
  - le navigateur (Edge par défaut, Chrome sur demande), Claude Code, le projet en cours ;
  - verifier() ; configurer_ezdxf_odafc() ;
  - la MÊME réponse de chemins.py, chemins.ps1 et chemins.cmd, y compris le PATH,
    avec des chemins qui contiennent des espaces et des parenthèses ;
  - le repli de chemins.cmd sans PowerShell ;
  - la compatibilité Python 3.9, et aucun chemin écrit en dur.

BM_TESTS_COMPLETS=1 ajoute : Blender -b qui importe le module, et le lanceur en
mode /verifier sur un « poste neuf » simulé (système caché).
"""

import ast
import contextlib
import importlib.util
import itertools
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

ICI = os.path.dirname(os.path.abspath(__file__))
OUTILS = os.path.dirname(ICI)
RACINE_REELLE = os.path.dirname(OUTILS)
FICHIERS = ("chemins.py", "chemins.ps1", "chemins.cmd")
SYSROOT = os.environ.get("SYSTEMROOT") or os.environ.get("SystemRoot") or r"C:\Windows"
POWERSHELL = os.path.join(SYSROOT, "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
WINDOWS = os.name == "nt"
COMPTEUR = itertools.count(1)
CLES_SESSION = ["BM_RACINE"] + [p + c for c in ("PYTHON", "BLENDER", "ODA_CONVERTISSEUR", "ODA_VISIONNEUSE",
                                                "NODE", "NAVIGATEUR", "POSTGRES", "GIT_BASH", "GH")
                                 for p in ("BM_", "BM_ORIGINE_")] \
    + ["BM_PROJET", "BM_ORIGINE_PROJET", "CLAUDE_CODE_GIT_BASH_PATH"]
# Blender PORTABLE seulement (consignes de l'agent B) ; BLENDER_USER_CONFIG et
# BLENDER_SYSTEM_SCRIPTS jouent des variables héritées du poste, à retirer.
CLES_BLENDER = ["BLENDER_SYSTEM_RESOURCES", "CUDA_CACHE_PATH", "BLENDER_USER_CONFIG", "BLENDER_SYSTEM_SCRIPTS"]
# Autres copies portables (consignes des agents A et C).
CLES_AUTRES = ["PYTHONHOME", "PYTHONPATH", "PYTHONNOUSERSITE", "QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH",
               "NODE_OPTIONS", "NODE_PATH", "NPM_CONFIG_UPDATE_NOTIFIER", "CLAUDE_CONFIG_DIR"]


def base_temporaire():
    base = os.environ.get("BM_TESTS_TEMP") or tempfile.gettempdir()
    os.makedirs(base, exist_ok=True)
    return tempfile.mkdtemp(prefix="bm_chemins_", dir=base)


def toucher(p):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb"):
        pass
    return p


def norm(p):
    return os.path.normcase(os.path.abspath(p)) if p else p


def fabriquer_poste(base, nom="poste", portables=()):
    """Un faux poste : <base>\\<nom>\\outils\\ avec les 3 fichiers de chemins et de faux .exe."""
    rac = os.path.join(base, nom)
    outils = os.path.join(rac, "outils")
    os.makedirs(outils)
    for f in FICHIERS:
        shutil.copy2(os.path.join(OUTILS, f), outils)
    for rel in portables:
        toucher(os.path.join(outils, rel))
    return rac


def env_isole(base, extra=None):
    """Environnement où le « système » est un faux dossier : rien du vrai poste n'est trouvé."""
    e = {k.upper(): v for k, v in os.environ.items()
         if not k.upper().startswith(("BM_", "_BM_")) and k.upper() != "PYTHONPATH"}
    s = os.path.join(base, "sys")
    for k, rel in (("PROGRAMFILES", "PF"), ("PROGRAMW6432", "PF"), ("PROGRAMFILES(X86)", "PF (x86)"),
                   ("LOCALAPPDATA", "LAD"), ("APPDATA", "AD"), ("USERPROFILE", "UP")):
        e[k] = os.path.join(s, rel)
        os.makedirs(e[k], exist_ok=True)
    os.makedirs(os.path.join(s, "BIN"), exist_ok=True)
    e["PATH"] = ";".join([os.path.join(s, "BIN"), os.path.join(SYSROOT, "System32"), SYSROOT,
                          os.path.join(SYSROOT, "System32", "WindowsPowerShell", "v1.0")])
    t = os.path.join(base, "tmp")
    os.makedirs(t, exist_ok=True)
    e["TEMP"] = e["TMP"] = t
    e["PYTHONIOENCODING"] = "utf-8"
    for k, v in (extra or {}).items():
        if v is None:
            e.pop(k.upper(), None)
        else:
            e[k.upper()] = v
    return e


@contextlib.contextmanager
def environnement(e):
    ancien = dict(os.environ)
    os.environ.clear()
    os.environ.update(e)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(ancien)


def charger(rac):
    """Importe <rac>\\outils\\chemins.py sous un nom unique."""
    chemin = os.path.join(rac, "outils", "chemins.py")
    spec = importlib.util.spec_from_file_location("chemins_essai_%d" % next(COMPTEUR), chemin)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def lignes_vers_dict(texte):
    d = {}
    for ligne in texte.splitlines():
        if "=" in ligne and not ligne.startswith("="):
            k, v = ligne.split("=", 1)
            d[k.strip().upper()] = v
    return d


def oem():
    if WINDOWS:
        try:
            import ctypes
            return "cp%d" % ctypes.windll.kernel32.GetOEMCP()
        except Exception:
            pass
    return "utf-8"


def lancer(args, env, delai=120):
    r = subprocess.run(args, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       stdin=subprocess.DEVNULL, timeout=delai)
    return r


def vars_python(rac, env):
    # -E : un PYTHONHOME ou un PYTHONPATH hérité (essais) ne doit pas casser CE Python ;
    # os.environ les contient quand même, et chemins.py les voit.
    r = lancer([sys.executable, "-E", "-X", "utf8", "-B", os.path.join(rac, "outils", "chemins.py"), "--variables"], env)
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")
    return lignes_vers_dict(r.stdout.decode("utf-8"))


def vars_powershell(rac, env):
    r = lancer([POWERSHELL, "-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                "-File", os.path.join(rac, "outils", "chemins.ps1"), "-Sortie", "cmd"], env)
    assert r.returncode == 0, r.stderr.decode(oem(), "replace")
    return lignes_vers_dict(r.stdout.decode(oem()))


def vars_cmd(rac, env):
    r = lancer(["cmd", "/d", "/c", "call", os.path.join(rac, "outils", "chemins.cmd"), "&&", "set"], env)
    assert r.returncode == 0, r.stderr.decode(oem(), "replace")
    return lignes_vers_dict(r.stdout.decode(oem())), r.stderr.decode(oem(), "replace")


class Base(unittest.TestCase):
    def setUp(self):
        self.base = base_temporaire()

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)

    def systeme(self, rel):
        """Crée un faux exécutable dans le faux système (rel commence par PF, PF (x86), LAD, AD, UP ou BIN)."""
        return toucher(os.path.join(self.base, "sys", rel))


# =============================================================================== racine

class TestRacine(Base):
    def test_racine_deduite_de_l_emplacement(self):
        rac = fabriquer_poste(self.base, "poste A")
        with environnement(env_isole(self.base)):
            mod = charger(rac)
            self.assertEqual(norm(mod.racine()), norm(rac))
            self.assertNotIn(":\\dev\\blender-main", norm(mod.racine()))

    def test_dossier_deplace_ailleurs(self):
        a = fabriquer_poste(self.base, "poste A", portables=[r"blender\blender.exe"])
        b = os.path.join(self.base, "ailleurs (2)", "Autre nom")
        shutil.copytree(a, b)
        with environnement(env_isole(self.base)):
            mod_a, mod_b = charger(a), charger(b)
            self.assertEqual(norm(mod_b.racine()), norm(b))
            self.assertEqual(norm(mod_b.blender_exe()), norm(os.path.join(b, "outils", "blender", "blender.exe")))
            self.assertEqual(norm(mod_a.blender_exe()), norm(os.path.join(a, "outils", "blender", "blender.exe")))

    def test_bm_racine_prioritaire(self):
        a = fabriquer_poste(self.base, "A")
        b = fabriquer_poste(self.base, "B", portables=[r"node\node.exe"])
        with environnement(env_isole(self.base, {"BM_RACINE": b})):
            mod = charger(a)
            self.assertEqual(norm(mod.racine()), norm(b))
            self.assertEqual(norm(mod.node_exe()), norm(os.path.join(b, "outils", "node", "node.exe")))

    def test_bm_racine_invalide(self):
        a = fabriquer_poste(self.base, "A")
        with environnement(env_isole(self.base, {"BM_RACINE": os.path.join(self.base, "nulle part")})):
            mod = charger(a)
            with self.assertRaises(mod.OutilIntrouvable) as ctx:
                mod.racine()
            self.assertIn("BM_RACINE", str(ctx.exception))


# =============================================================================== résolution

class TestResolution(Base):
    def test_portable_avant_systeme(self):
        rac = fabriquer_poste(self.base, portables=[r"blender\blender.exe", r"oda\convertisseur\ODAFileConverter.exe"])
        self.systeme(r"PF\Blender Foundation\Blender 5.2\blender.exe")
        self.systeme(r"PF\ODA\ODAFileConverter 27.1.0\ODAFileConverter.exe")
        with environnement(env_isole(self.base)):
            mod = charger(rac)
            chemin, origine = mod.resoudre("blender")
            self.assertEqual(origine, "portable")
            self.assertTrue(norm(chemin).startswith(norm(rac)))
            self.assertEqual(mod.resoudre("oda_convertisseur")[1], "portable")

    def test_variable_prioritaire(self):
        rac = fabriquer_poste(self.base, portables=[r"blender\blender.exe"])
        autre = toucher(os.path.join(self.base, "ailleurs", "mon blender", "blender.exe"))
        with environnement(env_isole(self.base, {"BM_BLENDER": autre})):
            mod = charger(rac)
            self.assertEqual(mod.resoudre("blender"), (os.path.abspath(autre), "variable"))
            self.assertEqual(norm(mod.blender_exe()), norm(autre))

    def test_variable_invalide_message_clair(self):
        rac = fabriquer_poste(self.base, portables=[r"blender\blender.exe"])
        with environnement(env_isole(self.base, {"BM_BLENDER": os.path.join(self.base, "absent.exe")})):
            mod = charger(rac)
            with self.assertRaises(mod.OutilIntrouvable) as ctx:
                mod.blender_exe()
            msg = str(ctx.exception)
            self.assertIn("BM_BLENDER", msg)
            self.assertIn("n'existe pas", msg)
            self.assertIsInstance(ctx.exception, FileNotFoundError)

    def test_repli_systeme_versions(self):
        rac = fabriquer_poste(self.base)
        for rel in (r"PF\Blender Foundation\Blender 4.5\blender.exe",
                    r"PF\Blender Foundation\Blender 5.2\blender.exe",
                    r"PF\Blender Foundation\Blender 5.3\blender.exe",
                    r"PF\ODA\ODAFileConverter 26.4.0\ODAFileConverter.exe",
                    r"PF\ODA\ODAFileConverter 26.12.0\ODAFileConverter.exe",
                    r"PF (x86)\ODA\ODA Viewer 25.12.0\ODAViewer.exe",
                    r"PF\ODA\ODA Viewer 27.1.0\ODAViewer.exe",
                    r"LAD\Programs\Python\Python39\python.exe",
                    r"LAD\Programs\Python\Python312\python.exe",
                    r"LAD\Programs\Python\Python313-32\python.exe",
                    r"LAD\Programs\Python\Python313\python.exe",
                    r"LAD\Programs\Python\Python314\python.exe",
                    r"PF\nodejs\node.exe",
                    r"PF\PostgreSQL\16\bin\pg_ctl.exe",
                    r"PF\PostgreSQL\18\bin\pg_ctl.exe",
                    r"PF\PostgreSQL\19\bin\pg_ctl.exe",
                    r"PF\Git\bin\bash.exe", r"PF\Git\cmd\git.exe",
                    r"PF\GitHub CLI\gh.exe"):
            self.systeme(rel)
        with environnement(env_isole(self.base)):
            mod = charger(rac)
            s = os.path.join(self.base, "sys")
            attendu = {
                "blender": r"PF\Blender Foundation\Blender 5.2\blender.exe",       # version visée
                "oda_convertisseur": r"PF\ODA\ODAFileConverter 26.12.0\ODAFileConverter.exe",  # 26.12 > 26.4
                "oda_visionneuse": r"PF\ODA\ODA Viewer 27.1.0\ODAViewer.exe",
                "python": r"LAD\Programs\Python\Python313\python.exe",            # visée, 64 bits
                "node": r"PF\nodejs\node.exe",
                "postgres": r"PF\PostgreSQL\18\bin\pg_ctl.exe",                   # 18 visée, pas 19
                "git_bash": r"PF\Git\bin\bash.exe",
                "gh": r"PF\GitHub CLI\gh.exe",
            }
            for outil, rel in attendu.items():
                chemin, origine = mod.resoudre(outil)
                self.assertEqual(origine, "systeme", outil)
                self.assertEqual(norm(chemin), norm(os.path.join(s, rel)), outil)
            self.assertEqual(norm(mod.postgres_bin()), norm(os.path.join(s, r"PF\PostgreSQL\18\bin")))
            self.assertEqual(norm(mod.git_exe()), norm(os.path.join(s, r"PF\Git\cmd\git.exe")))
            self.assertEqual(norm(mod.gh_exe()), norm(os.path.join(s, r"PF\GitHub CLI\gh.exe")))

    def test_postgres_git_variables_dossier(self):
        """BM_POSTGRES : le dossier bin, la racine de PostgreSQL ou un .exe de bin ; BM_GIT_BASH : un dossier aussi."""
        rac = fabriquer_poste(self.base, portables=[r"postgresql\bin\pg_ctl.exe", r"git\bin\bash.exe",
                                                     r"git\cmd\git.exe"])
        pg = os.path.join(self.base, "Mon PG (17)")
        exe = toucher(os.path.join(pg, "bin", "pg_ctl.exe"))
        toucher(os.path.join(pg, "bin", "psql.exe"))
        for valeur in (os.path.join(pg, "bin"), pg, os.path.join(pg, "bin", "psql.exe"), exe):
            with environnement(env_isole(self.base, {"BM_POSTGRES": valeur})):
                mod = charger(rac)
                self.assertEqual(mod.resoudre("postgres"), (os.path.abspath(exe), "variable"), valeur)
                self.assertEqual(norm(mod.postgres_bin()), norm(os.path.join(pg, "bin")))
        with environnement(env_isole(self.base, {"BM_POSTGRES": os.path.join(self.base, "vide")})):
            os.makedirs(os.path.join(self.base, "vide"), exist_ok=True)
            mod = charger(rac)
            with self.assertRaises(mod.OutilIntrouvable) as ctx:
                mod.postgres_bin()
            self.assertIn("BM_POSTGRES", str(ctx.exception))
        git = os.path.join(self.base, "Autre Git")
        bash = toucher(os.path.join(git, "bin", "bash.exe"))
        toucher(os.path.join(git, "cmd", "git.exe"))
        with environnement(env_isole(self.base, {"BM_GIT_BASH": git})):
            mod = charger(rac)
            self.assertEqual(mod.resoudre("git_bash"), (os.path.abspath(bash), "variable"))
            self.assertEqual(norm(mod.git_exe()), norm(os.path.join(git, "cmd", "git.exe")))
        with environnement(env_isole(self.base)):          # sans variable : les copies portables
            mod = charger(rac)
            o = os.path.join(rac, "outils")
            self.assertEqual(norm(mod.postgres_bin()), norm(os.path.join(o, "postgresql", "bin")))
            self.assertEqual(mod.resoudre("git_bash"), (os.path.join(o, "git", "bin", "bash.exe"), "portable"))
            self.assertEqual(norm(mod.git_exe()), norm(os.path.join(o, "git", "cmd", "git.exe")))

    def test_git_bash_par_le_git_du_path_jamais_le_bash_de_wsl(self):
        rac = fabriquer_poste(self.base)
        self.systeme(r"BIN\bash.exe")                 # joue le bash.exe de System32 (WSL) : à ignorer
        e = env_isole(self.base)
        with environnement(e):
            mod = charger(rac)
            with self.assertRaises(mod.OutilIntrouvable):
                mod.git_bash()
        pgit = os.path.join(self.base, "sys", "LAD", "Outils", "PortableGit")
        bash = toucher(os.path.join(pgit, "bin", "bash.exe"))
        toucher(os.path.join(pgit, "cmd", "git.exe"))
        e["PATH"] = os.path.join(pgit, "cmd") + ";" + e["PATH"]
        with environnement(e):
            mod = charger(rac)
            self.assertEqual(mod.resoudre("git_bash"), (os.path.abspath(bash), "systeme"))
            v = mod.variables_session()
            self.assertEqual(norm(v["CLAUDE_CODE_GIT_BASH_PATH"]), norm(bash))
            self.assertEqual(mod.path_session(v, e["PATH"]).split(";")[0], os.path.join(pgit, "cmd"))

    def test_repli_path_sans_alias_windowsapps(self):
        rac = fabriquer_poste(self.base)
        wa = os.path.join(self.base, "sys", "LAD", "Microsoft", "WindowsApps")
        toucher(os.path.join(wa, "python.exe"))
        e = env_isole(self.base)
        e["PATH"] = wa + ";" + e["PATH"]
        with environnement(e):
            mod = charger(rac)
            with self.assertRaises(mod.OutilIntrouvable):
                mod.python_exe()
            bon = self.systeme(r"BIN\python.exe")
            self.assertEqual(norm(mod.python_exe()), norm(bon))

    def test_message_clair_quand_rien_n_existe(self):
        rac = fabriquer_poste(self.base)
        with environnement(env_isole(self.base)):
            mod = charger(rac)
            for outil, var, dossier in (("python", "BM_PYTHON", "python"), ("blender", "BM_BLENDER", "blender"),
                                        ("oda_convertisseur", "BM_ODA_CONVERTISSEUR", "convertisseur"),
                                        ("oda_visionneuse", "BM_ODA_VISIONNEUSE", "visionneuse"),
                                        ("node", "BM_NODE", "node"), ("navigateur", "BM_NAVIGATEUR", None),
                                        ("claude", "BM_CLAUDE", "claude"), ("postgres", "BM_POSTGRES", "postgresql"),
                                        ("git_bash", "BM_GIT_BASH", "git"), ("gh", "BM_GH", "gh")):
                with self.assertRaises(mod.OutilIntrouvable) as ctx:
                    mod.resoudre(outil)
                msg = str(ctx.exception)
                self.assertIn("introuvable", msg, outil)
                self.assertIn("Cherché", msg, outil)
                self.assertIn(var, msg, outil)
                self.assertIn("LISEZMOI", msg, outil)
                if dossier:
                    self.assertIn(os.path.join(rac, "outils"), msg, outil)
            self.assertRaises(mod.OutilIntrouvable, mod.python_exe)
            for f in (mod.postgres_bin, mod.git_bash, mod.git_exe, mod.gh_exe):
                self.assertRaises(mod.OutilIntrouvable, f)
            self.assertRaises(ValueError, mod.resoudre, "autocad")

    def test_navigateur_edge_par_defaut_chrome_en_option(self):
        rac = fabriquer_poste(self.base)
        edge = self.systeme(r"PF (x86)\Microsoft\Edge\Application\msedge.exe")
        chrome = self.systeme(r"PF\Google\Chrome\Application\chrome.exe")
        with environnement(env_isole(self.base)):
            mod = charger(rac)
            self.assertEqual(norm(mod.navigateur_pdf()), norm(edge))
            self.assertEqual(norm(mod.navigateur_pdf("chrome")), norm(chrome))
            self.assertEqual(norm(mod.navigateur_pdf("Edge")), norm(edge))
        with environnement(env_isole(self.base, {"BM_NAVIGATEUR": "chrome"})):
            mod = charger(rac)
            self.assertEqual(mod.resoudre("navigateur"), (os.path.abspath(chrome), "variable"))
        autre = toucher(os.path.join(self.base, "Firefox", "firefox.exe"))
        with environnement(env_isole(self.base, {"BM_NAVIGATEUR": autre})):
            self.assertEqual(norm(charger(rac).navigateur_pdf()), norm(autre))
        os.remove(edge)
        with environnement(env_isole(self.base)):
            self.assertEqual(norm(charger(rac).navigateur_pdf()), norm(chrome))

    def test_claude_poste_puis_copie_portable(self):
        rac = fabriquer_poste(self.base, portables=[r"claude\claude.exe"])
        shim = self.systeme(r"AD\npm\claude.cmd")
        exe = self.systeme(r"AD\npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe")
        e = env_isole(self.base)
        e["PATH"] = os.path.dirname(shim) + ";" + e["PATH"]
        with environnement(e):
            mod = charger(rac)
            self.assertEqual(mod.resoudre("claude"), (os.path.abspath(exe), "systeme"))
        with environnement(env_isole(self.base)):   # npm hors du PATH : trouvé par %APPDATA%\npm
            self.assertEqual(charger(rac).resoudre("claude"), (os.path.abspath(exe), "systeme"))
        shutil.rmtree(os.path.join(self.base, "sys", "AD", "npm"))
        with environnement(env_isole(self.base)):
            chemin, origine = charger(rac).resoudre("claude")
            self.assertEqual(origine, "portable")
            self.assertEqual(norm(chemin), norm(os.path.join(rac, "outils", "claude", "claude.exe")))

    def test_projet_en_cours(self):
        rac = fabriquer_poste(self.base, "poste")
        p1 = os.path.join(self.base, "Maison_X")
        p2 = os.path.join(self.base, "Garage_Y")
        toucher(os.path.join(p1, "parametres_x.py"))
        toucher(os.path.join(p2, "parametres_y.py"))
        os.utime(os.path.join(p1, "parametres_x.py"), (1_700_000_000, 1_700_000_000))
        os.utime(os.path.join(p2, "parametres_y.py"), (1_800_000_000, 1_800_000_000))
        fichier = os.path.join(rac, "outils", "projet_en_cours.txt")
        with environnement(env_isole(self.base)):
            mod = charger(rac)
            self.assertEqual(mod.projet_en_cours(True), (os.path.abspath(p2), "recent"))
            with open(fichier, "w", encoding="utf-8") as f:
                f.write("# commentaire\n\n..\\Maison_X\n")
            self.assertEqual(mod.projet_en_cours(True), (os.path.abspath(p1), "fichier"))
            with open(fichier, "w", encoding="utf-8") as f:
                f.write("../Maison_X\n")
            self.assertEqual(norm(mod.projet_en_cours()), norm(p1))
            with open(fichier, "w", encoding="utf-8") as f:
                f.write(p1 + "\n")
            self.assertEqual(norm(mod.projet_en_cours()), norm(p1))
            with open(fichier, "w", encoding="utf-8") as f:
                f.write("..\\Projet_disparu\n")
            self.assertEqual(mod.projet_en_cours(True), (os.path.abspath(p2), "recent-fichier-invalide"))
            os.remove(fichier)
            shutil.rmtree(p1)
            shutil.rmtree(p2)
            self.assertEqual(mod.projet_en_cours(True), (None, "absent"))

    def test_verifier_structure(self):
        rac = fabriquer_poste(self.base, portables=[r"python\python.exe", r"blender\blender.exe"])
        with environnement(env_isole(self.base)):
            mod = charger(rac)
            res = mod.verifier()
            noms = [r[0] for r in res]
            self.assertEqual(noms, ["python", "ezdxf", "blender", "oda_convertisseur", "oda_visionneuse",
                                    "node", "postgres", "git_bash", "gh", "navigateur", "claude"])
            for r in res:
                self.assertEqual(len(r), 4)
                outil, chemin, ok, version = r                      # 4-uplet, comme l'interface
                self.assertIsInstance(ok, bool)
                self.assertIn(r.origine, ("portable", "systeme", "variable", "absent"))
                self.assertIsInstance(r.en_dict(), dict)
            d = {r.outil: r for r in res}
            self.assertFalse(d["python"].ok)              # faux python.exe : ne démarre pas
            self.assertEqual(d["python"].origine, "portable")
            self.assertFalse(d["blender"].ok)             # faux .exe : pas de version lisible
            self.assertEqual(d["node"].origine, "absent")
            self.assertIn("introuvable", d["node"].detail)

    def test_configurer_ezdxf_odafc(self):
        try:
            import ezdxf
        except ImportError:
            self.skipTest("ezdxf absent de ce Python")
        rac = fabriquer_poste(self.base, portables=[r"oda\convertisseur\ODAFileConverter.exe"])
        avant = ezdxf.options.get("odafc-addon", "win_exec_path")
        try:
            with environnement(env_isole(self.base)):
                mod = charger(rac)
                exe = mod.configurer_ezdxf_odafc()
                self.assertEqual(norm(exe), norm(os.path.join(rac, "outils", "oda", "convertisseur",
                                                              "ODAFileConverter.exe")))
                self.assertEqual(ezdxf.options.get("odafc-addon", "win_exec_path").strip('"'), exe)
                from ezdxf.addons import odafc
                self.assertEqual(odafc.get_win_exec_path(), exe)
            # Un AUTRE ODA dans le PATH : ezdxf le prendrait d'abord (shutil.which) ; le module le déjoue.
            autre = toucher(os.path.join(self.base, "sys", "BIN", "ODAFileConverter.exe"))
            with environnement(env_isole(self.base)):
                self.assertEqual(norm(shutil.which("ODAFileConverter")), norm(autre))
                exe = charger(rac).configurer_ezdxf_odafc()
                self.assertEqual(norm(shutil.which("ODAFileConverter")), norm(exe))
                from ezdxf.addons import odafc
                if hasattr(odafc, "_get_odafc_path"):
                    self.assertEqual(norm(odafc._get_odafc_path("Windows")), norm(exe))
        finally:
            ezdxf.options.set("odafc-addon", "win_exec_path", avant)

    def test_session_recalcule_les_variables_d_une_autre_session(self):
        a = fabriquer_poste(self.base, "A", portables=[r"blender\blender.exe", r"node\node.exe"])
        b = os.path.join(self.base, "B deplace")
        shutil.copytree(a, b)
        perso = toucher(os.path.join(self.base, "perso", "node.exe"))
        heritees = {"BM_RACINE": a,
                    "BM_BLENDER": os.path.join(a, "outils", "blender", "blender.exe"),
                    "BM_ORIGINE_BLENDER": "portable",
                    "BM_NODE": perso}                      # posée à la main : gardée
        with environnement(env_isole(self.base, heritees)):
            v = charger(b).variables_session()
        self.assertEqual(norm(v["BM_RACINE"]), norm(b))
        self.assertEqual(norm(v["BM_BLENDER"]), norm(os.path.join(b, "outils", "blender", "blender.exe")))
        self.assertEqual(v["BM_ORIGINE_BLENDER"], "portable")
        self.assertEqual(norm(v["BM_NODE"]), norm(perso))
        self.assertEqual(v["BM_ORIGINE_NODE"], "variable")

    def test_env_blender(self):
        rac = fabriquer_poste(self.base, portables=[r"blender\blender.exe", r"blender\5.2\python\bin\python.exe",
                                                     r"blender\portable\LISEZMOI.txt"])
        e = env_isole(self.base, {"BLENDER_USER_CONFIG": "x", "BLENDER_SYSTEM_SCRIPTS": "y", "CUDA_CACHE_PATH": "z"})
        with environnement(e):
            env = charger(rac).env_blender()
        o = os.path.join(rac, "outils", "blender")
        cles = {k.upper() for k in env}
        self.assertNotIn("BLENDER_USER_CONFIG", cles)
        self.assertNotIn("BLENDER_SYSTEM_SCRIPTS", cles)
        self.assertEqual(env["BLENDER_SYSTEM_RESOURCES"], os.path.join(o, "5.2"))
        self.assertEqual(env["CUDA_CACHE_PATH"], os.path.join(o, "portable", "cuda_cache"))
        # Blender du système : l'environnement reste celui du poste
        rac2 = fabriquer_poste(self.base, "sans blender portable")
        self.systeme(r"PF\Blender Foundation\Blender 5.2\blender.exe")
        with environnement(e):
            env2 = charger(rac2).env_blender()
        self.assertEqual(env2.get("BLENDER_USER_CONFIG"), "x")
        self.assertEqual(env2.get("CUDA_CACHE_PATH"), "z")
        self.assertNotIn("BLENDER_SYSTEM_RESOURCES", env2)

    def test_path_session(self):
        rac = fabriquer_poste(self.base, portables=[r"python\python.exe", r"python\Scripts\pip.exe",
                                                     r"node\node.exe"])
        with environnement(env_isole(self.base)):
            mod = charger(rac)
            v = mod.variables_session()
            o = os.path.join(rac, "outils")
            # outils\python\Scripts : jamais dans le PATH (ses lanceurs visent l'ancien Python), même hérité
            ancien = (os.path.join(o, "node") + ";C:\\A;;" + os.path.join(o, "python") + "\\;"
                      + os.path.join(o, "python", "Scripts") + "\\;C:\\B")
            p = mod.path_session(v, ancien).split(";")
            self.assertEqual(p[:2], [os.path.join(o, "python"), os.path.join(o, "node")])
            self.assertEqual(p[2:], ["C:\\A", "C:\\B"])
            # un Python du SYSTÈME garde son Scripts (ses lanceurs sont justes)
            v2 = dict(v, BM_ORIGINE_PYTHON="systeme", BM_PYTHON=r"C:\Py\python.exe")
            self.assertIn(r"C:\Py\Scripts", mod.path_session(v2, r"C:\Py\Scripts;C:\B").split(";"))


# =============================================================================== même réponse partout

@unittest.skipUnless(WINDOWS and os.path.isfile(POWERSHELL), "Windows et PowerShell requis")
class TestCoherencePythonPowerShellCmd(Base):
    def scenario_mixte(self, nom_poste="poste"):
        rac = fabriquer_poste(self.base, nom_poste, portables=[r"python\python.exe", r"python\Scripts\pip.exe",
                                                               r"blender\blender.exe",
                                                               r"blender\5.2\python\bin\python.exe",
                                                               r"blender\portable\LISEZMOI.txt"])
        for rel in (r"PF\ODA\ODAFileConverter 26.4.0\ODAFileConverter.exe",
                    r"PF\ODA\ODAFileConverter 26.12.0\ODAFileConverter.exe",
                    r"PF (x86)\ODA\ODA Viewer 27.1.0\ODAViewer.exe",
                    r"PF\nodejs\node.exe",
                    r"PF (x86)\Microsoft\Edge\Application\msedge.exe",
                    r"PF\Google\Chrome\Application\chrome.exe",
                    r"PF\Blender Foundation\Blender 5.2\blender.exe",
                    r"PF\PostgreSQL\17\bin\pg_ctl.exe", r"PF\PostgreSQL\18\bin\pg_ctl.exe",
                    r"PF\Git\bin\bash.exe", r"PF\Git\cmd\git.exe", r"PF\GitHub CLI\gh.exe"):
            self.systeme(rel)
        toucher(os.path.join(self.base, "Maison_Z", "parametres_z.py"))
        with open(os.path.join(rac, "outils", "projet_en_cours.txt"), "w", encoding="utf-8") as f:
            f.write("# projet\n..\\Maison_Z\n")
        return rac

    def comparer(self, rac, env, attendu=None):
        """Valeur EFFECTIVE de chaque variable après chemins.* : Python et PowerShell n'écrivent
        que ce qui change (le reste garde sa valeur héritée) ; cmd montre la session obtenue."""
        py = vars_python(rac, env)
        ps = vars_powershell(rac, env)
        cm, err = vars_cmd(rac, env)
        effectif = {}
        for cle in CLES_SESSION + CLES_BLENDER + CLES_AUTRES + ["PATH"]:
            herite = env.get(cle, "")
            v_py, v_ps = py.get(cle, herite), ps.get(cle, herite)
            self.assertEqual(v_ps, v_py, "PowerShell et Python different sur " + cle)
            self.assertEqual(cm.get(cle, ""), v_py, "cmd et Python different sur " + cle)
            effectif[cle] = v_py
        for cle, val in (attendu or {}).items():
            self.assertEqual(effectif.get(cle, ""), val, cle)
        return effectif

    def test_scenario_mixte(self):
        rac = self.scenario_mixte()
        o = os.path.join(rac, "outils")
        s = os.path.join(self.base, "sys")
        heritees = {"BLENDER_USER_CONFIG": os.path.join(self.base, "cfg"),
                    "BLENDER_SYSTEM_SCRIPTS": os.path.join(self.base, "scr"),
                    "PYTHONHOME": os.path.join(self.base, "autre python"), "PYTHONPATH": os.path.join(self.base, "lib"),
                    "NODE_OPTIONS": "--max-old-space-size=4096", "QT_PLUGIN_PATH": os.path.join(self.base, "qt")}
        env = env_isole(self.base, heritees)
        env["PATH"] = os.path.join(o, "python", "Scripts") + ";" + env["PATH"]   # hérité : doit disparaître
        py = self.comparer(rac, env, {
            "BLENDER_SYSTEM_RESOURCES": os.path.join(o, "blender", "5.2"),
            "CUDA_CACHE_PATH": os.path.join(o, "blender", "portable", "cuda_cache"),
            "BLENDER_USER_CONFIG": "", "BLENDER_SYSTEM_SCRIPTS": "",
            # Python portable : sans PYTHONHOME ni PYTHONPATH, site utilisateur coupé
            "PYTHONHOME": "", "PYTHONPATH": "", "PYTHONNOUSERSITE": "1",
            # Node et ODA viennent du système : leur environnement reste celui du poste
            "NODE_OPTIONS": "--max-old-space-size=4096", "QT_PLUGIN_PATH": heritees["QT_PLUGIN_PATH"],
            "NPM_CONFIG_UPDATE_NOTIFIER": "false",
            "BM_RACINE": rac,
            "BM_PYTHON": os.path.join(o, "python", "python.exe"), "BM_ORIGINE_PYTHON": "portable",
            "BM_BLENDER": os.path.join(o, "blender", "blender.exe"), "BM_ORIGINE_BLENDER": "portable",
            "BM_ODA_CONVERTISSEUR": os.path.join(s, "PF", "ODA", "ODAFileConverter 26.12.0", "ODAFileConverter.exe"),
            "BM_ORIGINE_ODA_CONVERTISSEUR": "systeme",
            "BM_ODA_VISIONNEUSE": os.path.join(s, "PF (x86)", "ODA", "ODA Viewer 27.1.0", "ODAViewer.exe"),
            "BM_NODE": os.path.join(s, "PF", "nodejs", "node.exe"), "BM_ORIGINE_NODE": "systeme",
            "BM_NAVIGATEUR": os.path.join(s, "PF (x86)", "Microsoft", "Edge", "Application", "msedge.exe"),
            "BM_PROJET": os.path.join(self.base, "Maison_Z"), "BM_ORIGINE_PROJET": "fichier",
            # PostgreSQL : le DOSSIER bin de la version visée (18, pas 17) ; Git et gh du système
            "BM_POSTGRES": os.path.join(s, "PF", "PostgreSQL", "18", "bin"), "BM_ORIGINE_POSTGRES": "systeme",
            "BM_GIT_BASH": os.path.join(s, "PF", "Git", "bin", "bash.exe"), "BM_ORIGINE_GIT_BASH": "systeme",
            "CLAUDE_CODE_GIT_BASH_PATH": os.path.join(s, "PF", "Git", "bin", "bash.exe"),
            "BM_GH": os.path.join(s, "PF", "GitHub CLI", "gh.exe"), "BM_ORIGINE_GH": "systeme",
        })
        tete = py["PATH"].split(";")[:5]
        self.assertEqual(tete, [os.path.join(o, "python"), os.path.join(s, "PF", "nodejs"),
                                os.path.join(s, "PF", "ODA", "ODAFileConverter 26.12.0"),
                                os.path.join(s, "PF", "Git", "cmd"), os.path.join(s, "PF", "GitHub CLI")])
        self.assertNotIn(os.path.join(o, "python", "Scripts").lower(), py["PATH"].lower().split(";"))
        self.assertNotIn("postgresql", py["PATH"].lower())       # jamais PostgreSQL dans le PATH

    def test_tout_portable(self):
        rac = fabriquer_poste(self.base, "tout portable", portables=[
            r"python\python.exe", r"python\Scripts\pip.exe", r"blender\blender.exe",
            r"blender\5.2\python\bin\python.exe", r"oda\convertisseur\ODAFileConverter.exe",
            r"oda\visionneuse\ODAViewer.exe", r"node\node.exe", r"postgresql\bin\pg_ctl.exe",
            r"git\bin\bash.exe", r"git\cmd\git.exe", r"git\usr\bin\bash.exe", r"gh\gh.exe"])
        o = os.path.join(rac, "outils")
        os.makedirs(os.path.join(o, "claude", "config"))           # configuration de Claude dans le dossier
        self.systeme(r"PF\PostgreSQL\18\bin\pg_ctl.exe")          # le système existe : la copie passe avant
        heritees = {"QT_PLUGIN_PATH": os.path.join(self.base, "qt"), "QT_QPA_PLATFORM_PLUGIN_PATH": "x",
                    "NODE_OPTIONS": "--inspect", "NODE_PATH": os.path.join(self.base, "nm"),
                    "npm_config_update_notifier": "true",          # posée par l'utilisateur : gardée
                    "CLAUDE_CODE_GIT_BASH_PATH": os.path.join(self.base, "ancien", "bash.exe")}   # remplacée
        env = env_isole(self.base, heritees)
        env["PATH"] = env["PATH"] + ";" + os.path.join(o, "python", "Scripts")   # hérité : doit disparaître
        py = self.comparer(rac, env, {
            "QT_PLUGIN_PATH": "", "QT_QPA_PLATFORM_PLUGIN_PATH": "", "NODE_OPTIONS": "", "NODE_PATH": "",
            "NPM_CONFIG_UPDATE_NOTIFIER": "true", "PYTHONNOUSERSITE": "1",
            "BM_ORIGINE_ODA_CONVERTISSEUR": "portable", "BM_ORIGINE_NODE": "portable",
            "BM_POSTGRES": os.path.join(o, "postgresql", "bin"), "BM_ORIGINE_POSTGRES": "portable",
            "BM_GIT_BASH": os.path.join(o, "git", "bin", "bash.exe"), "BM_ORIGINE_GIT_BASH": "portable",
            "CLAUDE_CODE_GIT_BASH_PATH": os.path.join(o, "git", "bin", "bash.exe"),
            "BM_GH": os.path.join(o, "gh", "gh.exe"), "BM_ORIGINE_GH": "portable",
            "CLAUDE_CONFIG_DIR": os.path.join(o, "claude", "config")})
        self.assertEqual(py["PATH"].split(";")[:5], [os.path.join(o, "python"), os.path.join(o, "node"),
                                                     os.path.join(o, "oda", "convertisseur"),
                                                     os.path.join(o, "git", "cmd"), os.path.join(o, "gh")])
        for mauvais in (os.path.join(o, "git", "bin"), os.path.join(o, "git", "usr", "bin"), os.path.join(o, "postgresql", "bin")):
            self.assertNotIn(mauvais.lower(), py["PATH"].lower().split(";"))
        self.assertNotIn(os.path.join(o, "python", "Scripts").lower(), py["PATH"].lower().split(";"))

    def test_blender_du_systeme_garde_l_environnement_du_poste(self):
        rac = fabriquer_poste(self.base, portables=[r"python\python.exe"])
        self.systeme(r"PF\Blender Foundation\Blender 5.2\blender.exe")
        heritees = {"BLENDER_USER_CONFIG": os.path.join(self.base, "cfg")}
        self.comparer(rac, env_isole(self.base, heritees), {
            "BM_ORIGINE_BLENDER": "systeme", "BLENDER_USER_CONFIG": heritees["BLENDER_USER_CONFIG"],
            "BLENDER_SYSTEM_RESOURCES": "", "CUDA_CACHE_PATH": ""})

    def test_config_claude_du_dossier_et_retour_arriere(self):
        """CLAUDE_CONFIG_DIR : le dossier outils\\claude\\config s'il existe ; BM_CLAUDE_CONFIG=profil le retire ;
        sans dossier ni variable, la valeur héritée reste ; BM_CLAUDE_CONFIG=<dossier> l'emporte."""
        rac = fabriquer_poste(self.base, "poste cc")
        cfg = os.path.join(rac, "outils", "claude", "config")
        ailleurs = os.path.join(self.base, "cfg heritee")      # ASCII : cmd relit selon la page de codes
        self.comparer(rac, env_isole(self.base, {"CLAUDE_CONFIG_DIR": ailleurs}), {"CLAUDE_CONFIG_DIR": ailleurs})
        os.makedirs(cfg)
        self.comparer(rac, env_isole(self.base, {"CLAUDE_CONFIG_DIR": ailleurs}), {"CLAUDE_CONFIG_DIR": cfg})
        self.comparer(rac, env_isole(self.base, {"CLAUDE_CONFIG_DIR": ailleurs, "BM_CLAUDE_CONFIG": "Profil"}),
                      {"CLAUDE_CONFIG_DIR": ""})
        autre = os.path.join(self.base, "Autre config (2)")
        self.comparer(rac, env_isole(self.base, {"BM_CLAUDE_CONFIG": autre}), {"CLAUDE_CONFIG_DIR": autre})
        with environnement(env_isole(self.base)):
            self.assertEqual(norm(charger(rac).config_claude()), norm(cfg))

    def test_rien_nulle_part(self):
        rac = fabriquer_poste(self.base)
        env = env_isole(self.base)
        py = self.comparer(rac, env, {"BM_PYTHON": "", "BM_ORIGINE_PYTHON": "absent",
                                      "BM_NAVIGATEUR": "", "BM_ORIGINE_NAVIGATEUR": "absent",
                                      "BM_ORIGINE_PROJET": "absent"})
        self.assertEqual(py["PATH"], env["PATH"])

    def test_espaces_et_parentheses(self):
        rac = self.scenario_mixte(nom_poste="Copie (2) du poste & co")
        self.comparer(rac, env_isole(self.base), {"BM_RACINE": rac, "BM_ORIGINE_PYTHON": "portable"})

    def test_variables_heritees_d_un_dossier_deplace(self):
        a = self.scenario_mixte("A")
        b = os.path.join(self.base, "B, ailleurs")
        shutil.copytree(a, b)
        perso = toucher(os.path.join(self.base, "perso", "node.exe"))
        heritees = {"BM_RACINE": a, "BM_PYTHON": os.path.join(a, "outils", "python", "python.exe"),
                    "BM_ORIGINE_PYTHON": "portable", "BM_NODE": perso,
                    "BM_ORIGINE_PROJET": "fichier", "BM_PROJET": a}
        self.comparer(b, env_isole(self.base, heritees), {
            "BM_RACINE": b, "BM_PYTHON": os.path.join(b, "outils", "python", "python.exe"),
            "BM_NODE": perso, "BM_ORIGINE_NODE": "variable"})

    def test_variable_invalide_ignoree_par_la_session(self):
        rac = self.scenario_mixte()
        env = env_isole(self.base, {"BM_BLENDER": os.path.join(self.base, "absent", "blender.exe")})
        self.comparer(rac, env, {"BM_ORIGINE_BLENDER": "portable"})
        _, err = vars_cmd(rac, env)
        self.assertIn("BM_BLENDER", err)          # l'avertissement s'affiche dans la fenêtre

    def test_cmd_sans_powershell(self):
        rac = fabriquer_poste(self.base, portables=[r"python\python.exe", r"python\Scripts\pip.exe",
                                                     r"node\node.exe", r"oda\visionneuse\ODAViewer.exe",
                                                     r"postgresql\bin\pg_ctl.exe", r"git\bin\bash.exe",
                                                     r"git\cmd\git.exe", r"gh\gh.exe"])
        self.systeme(r"PF\Blender Foundation\Blender 5.2\blender.exe")   # ignoré : repli minimal
        env = env_isole(self.base, {"BM_TEST_SANS_POWERSHELL": "1",
                                    "BLENDER_USER_CONFIG": os.path.join(self.base, "cfg"),
                                    "PYTHONHOME": os.path.join(self.base, "autre"), "NODE_OPTIONS": "--inspect",
                                    "QT_PLUGIN_PATH": os.path.join(self.base, "qt")})
        cm, _ = vars_cmd(rac, env)
        self.assertEqual(cm["BLENDER_USER_CONFIG"], env["BLENDER_USER_CONFIG"])   # pas de Blender portable
        self.assertNotIn("BLENDER_SYSTEM_RESOURCES", cm)
        self.assertNotIn("PYTHONHOME", cm)
        self.assertEqual(cm["PYTHONNOUSERSITE"], "1")
        self.assertNotIn("NODE_OPTIONS", cm)
        self.assertNotIn("QT_PLUGIN_PATH", cm)                    # la visionneuse ODA est portable
        self.assertEqual(cm["NPM_CONFIG_UPDATE_NOTIFIER"], "false")
        # avec un Blender portable : mêmes consignes que chemins.ps1
        for rel in (r"blender\blender.exe", r"blender\5.2\python\bin\python.exe"):
            toucher(os.path.join(rac, "outils", rel))
        cm2, _ = vars_cmd(rac, env)
        self.assertNotIn("BLENDER_USER_CONFIG", cm2)
        self.assertEqual(cm2["BLENDER_SYSTEM_RESOURCES"], os.path.join(rac, "outils", "blender", "5.2"))
        self.assertEqual(cm2["CUDA_CACHE_PATH"], os.path.join(rac, "outils", "blender", "portable", "cuda_cache"))
        o = os.path.join(rac, "outils")
        self.assertEqual(cm["BM_RACINE"], rac)
        self.assertEqual(cm["BM_PYTHON"], os.path.join(o, "python", "python.exe"))
        self.assertEqual(cm["BM_ORIGINE_PYTHON"], "portable")
        self.assertEqual(cm["BM_ODA_VISIONNEUSE"], os.path.join(o, "oda", "visionneuse", "ODAViewer.exe"))
        self.assertNotIn("BM_BLENDER", cm)
        self.assertEqual(cm["BM_ORIGINE_BLENDER"], "absent")
        self.assertEqual(cm["BM_POSTGRES"], os.path.join(o, "postgresql", "bin"))
        self.assertEqual(cm["BM_ORIGINE_POSTGRES"], "portable")
        self.assertEqual(cm["BM_GIT_BASH"], os.path.join(o, "git", "bin", "bash.exe"))
        self.assertEqual(cm["CLAUDE_CODE_GIT_BASH_PATH"], os.path.join(o, "git", "bin", "bash.exe"))
        self.assertEqual(cm["BM_GH"], os.path.join(o, "gh", "gh.exe"))
        self.assertEqual(cm["PATH"].split(";")[:4], [os.path.join(o, "python"), os.path.join(o, "node"),
                                                     os.path.join(o, "git", "cmd"), os.path.join(o, "gh")])
        self.assertNotIn(os.path.join(o, "python", "Scripts").lower(), cm["PATH"].lower().split(";"))


# =============================================================================== le code lui-même

class TestCode(unittest.TestCase):
    def test_compatible_python_39(self):
        with open(os.path.join(OUTILS, "chemins.py"), encoding="utf-8") as f:
            ast.parse(f.read(), filename="chemins.py", feature_version=(3, 9))

    def test_aucun_chemin_en_dur(self):
        interdits = ("c:\\dev", "c:/dev", "program files\\blender", "python313\\",
                     "\\odafileconverter 27", "\\oda viewer 27", "\\appdata\\roaming\\npm\\node_modules", "c:\\users\\")
        for f in [os.path.join(OUTILS, n) for n in FICHIERS] + [os.path.join(RACINE_REELLE, "Demarrer-Blender.bat")]:
            if not os.path.isfile(f):
                continue
            with open(f, encoding="utf-8", errors="replace") as h:
                texte = h.read().lower()
            for mot in interdits:
                self.assertFalse(mot in texte, "%s contient %r" % (os.path.basename(f), mot))

    def test_fichiers_cmd_en_crlf_et_ascii(self):
        for f in (os.path.join(OUTILS, "chemins.cmd"), os.path.join(OUTILS, "chemins.ps1"),
                  os.path.join(RACINE_REELLE, "Demarrer-Blender.bat")):
            if not os.path.isfile(f):
                continue
            with open(f, "rb") as h:
                octets = h.read()
            self.assertTrue(all(b < 128 for b in octets), "%s : caractere non ASCII" % f)
            if f.lower().endswith((".cmd", ".bat")):
                self.assertEqual(octets.count(b"\n"), octets.count(b"\r\n"),
                                 "%s : fins de ligne LF seules (cmd.exe perd alors ses etiquettes)" % f)

    def test_module_reel_s_importe_et_rend_la_racine(self):
        with environnement({k: v for k, v in os.environ.items() if not k.upper().startswith(("BM_", "_BM_"))}):
            mod = charger(RACINE_REELLE)
            self.assertEqual(norm(mod.racine()), norm(RACINE_REELLE))


@unittest.skipUnless(WINDOWS, "Windows requis")
class TestAvecLesVraisOutils(unittest.TestCase):
    """Sur le vrai poste, en lecture seule : Python de Blender, puis (BM_TESTS_COMPLETS=1)
    Blender -b et le lanceur /verifier sur un poste neuf simulé."""

    def setUp(self):
        env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("BM_", "_BM_"))}
        with environnement(env):
            self.mod = charger(RACINE_REELLE)
            try:
                self.blender = self.mod.blender_exe()
            except self.mod.OutilIntrouvable:
                self.blender = None

    def test_import_depuis_le_python_de_blender(self):
        if not self.blender:
            self.skipTest("Blender introuvable")
        d = os.path.dirname(self.blender)
        candidats = [os.path.join(d, n, "python", "bin", "python.exe") for n in sorted(os.listdir(d))]
        py_blender = next((c for c in candidats if os.path.isfile(c)), None)
        if not py_blender:
            self.skipTest("Python embarque de Blender introuvable")
        code = ("import sys; sys.path.insert(0, %r); import chemins; "
                "print(chemins.racine()); print(chemins.blender_exe()); print(sys.version.split()[0])" % OUTILS)
        env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("BM_", "_BM_"))}
        # -X utf8 : sortie lue en UTF-8 ; sans lui, un dossier accentué devient illisible dans un tube (cp1252).
        r = lancer([py_blender, "-X", "utf8", "-B", "-c", code], env)
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace"))
        lignes = r.stdout.decode("utf-8", "replace").splitlines()
        self.assertEqual(norm(lignes[0]), norm(RACINE_REELLE))
        self.assertEqual(norm(lignes[1]), norm(self.blender))

    @unittest.skipUnless(os.environ.get("BM_TESTS_COMPLETS") == "1", "BM_TESTS_COMPLETS=1 pour lancer Blender")
    def test_blender_b_importe_le_module(self):
        if not self.blender:
            self.skipTest("Blender introuvable")
        expr = ("import sys; sys.path.insert(0, %r); import chemins; print('RACINE=' + chemins.racine()); "
                "print('PYTHON=' + chemins.python_exe())" % OUTILS)
        env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("BM_", "_BM_"))}
        r = lancer([self.blender, "-b", "--factory-startup", "--python-expr", expr], env, delai=300)
        sortie = r.stdout.decode("utf-8", "replace")
        self.assertIn("RACINE=" + RACINE_REELLE, sortie)
        self.assertIn("PYTHON=", sortie)

    @unittest.skipUnless(os.environ.get("BM_TESTS_COMPLETS") == "1", "BM_TESTS_COMPLETS=1 pour le lanceur")
    def test_lanceur_verifier_sur_poste_neuf_simule(self):
        """Le système est caché (ProgramFiles, LOCALAPPDATA... vides ; PATH = Windows seul) :
        tout ce qui marche vient du dossier."""
        base = base_temporaire()
        try:
            env = env_isole(base)
            lanceur = os.path.join(RACINE_REELLE, "Demarrer-Blender.bat")
            r = lancer(["cmd", "/d", "/c", "call", lanceur, "/verifier"], env, delai=600)
            sortie = r.stdout.decode(oem(), "replace")
            self.assertEqual(r.returncode, 0, sortie[-2000:])
            self.assertIn("Diagnostic termine", sortie)
            self.assertNotIn("[repli]", sortie)
            for n in ("Python", "Blender", "ODA File Converter", "Node.js"):
                self.assertRegex(sortie, r"\[ok\]\s+%s .*copie portable" % n.replace(".", r"\."))
        finally:
            shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
