# -*- coding: utf-8 -*-
r"""
inventaire_imports.py : inventaire des imports Python des scripts du poste (LECTURE SEULE, module ast).

Usage
    python inventaire_imports.py [racine ...] [--json sortie.json] [--detail]

    Sans racine, on analyse :
      - dans blender-main : Rendu3D_ERP, .claude, Soumission_client, modeles, outils\diagnostic
        (jamais le code source de Blender : source\, scripts\, tools\...) ;
      - les projets freres de blender-main : <parent>\*_Blender et <parent>\Immeuble_65_logements.
    La racine de blender-main se deduit de l'emplacement de ce fichier (outils\diagnostic\..\..).

    --json F   ecrit l'inventaire complet (par module et par fichier) dans F ;
    --detail   imprime aussi, pour chaque paquet tiers, les fichiers qui l'importent.

Classement de chaque import (nom de tete : « a » pour « import a.b.c »)
    stdlib       bibliotheque standard (sys.stdlib_module_names) ;
    blender      module qui vit dans le Python de Blender (bpy, bmesh, mathutils, gpu...) ;
    local        import relatif, ou module defini dans l'arborescence du meme projet ;
    autre_projet module defini dans un AUTRE projet analyse (sys.path bricole) ;
    tiers        paquet installe dans l'interpreteur qui execute ce script : distribution pip et version ;
    introuvable  rien de tout cela (module d'un autre depot ajoute a sys.path, faute de frappe...).

    Marques : « optionnel » (dans un try dont un except attrape ImportError, ModuleNotFoundError,
    Exception ou tout), « paresseux » (dans une fonction), « typage » (sous if TYPE_CHECKING),
    « blender » (le fichier importe bpy : c'est le Python de Blender qui fournira le paquet).
    Imports dynamiques releves : importlib.import_module, __import__, runpy.run_path/run_module,
    spec_from_file_location, SourceFileLoader, exec(open(...)). Aussi : sys.path.insert/append,
    et les chaines qui ecrivent en dur un chemin d'outil (Python313, Program Files, AppData).

Le resultat depend de l'interpreteur qui l'execute : lance par la copie portable
(outils\python\python.exe), il donne les versions de la copie portable.
Code de sortie : 0 ; 3 s'il reste des imports « introuvable » non optionnels.
"""
import ast
import glob
import importlib.machinery
import importlib.metadata as md
import importlib.util
import json
import os
import re
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(ICI, "..", ".."))

SOUS_DOSSIERS_RACINE = ["Rendu3D_ERP", ".claude", "Soumission_client", "modeles",
                        os.path.join("outils", "diagnostic")]
DOSSIERS_IGNORES = {"__pycache__", ".git", "node_modules", "sysroot", "site-packages",
                    ".venv", "venv", "env", ".mypy_cache", ".pytest_cache", ".ruff_cache"}

# Modules fournis par Blender lui-meme (pas par pip) : ils n'existent que dans son Python.
BLENDER = {
    "bpy", "_bpy", "bpy_types", "bpy_extras", "bpy_restrict_state", "_bpy_path", "bmesh",
    "mathutils", "gpu", "gpu_extras", "bgl", "blf", "bl_math", "aud", "idprop", "imbuf",
    "freestyle", "_freestyle", "cycles", "_cycles", "rna_prop_ui", "rna_info", "rna_keymap_ui",
    "rna_xml", "addon_utils", "nodeitems_utils", "keyingsets_utils", "keyingsets_builtins",
    "graphviz_export", "console_python", "console_shell", "animsys_refactor", "sys_info",
    "bl_ui", "bl_operators", "bl_keymap_utils", "bl_app_override", "bl_app_template_utils",
    "bl_previews_utils", "bl_i18n_utils", "bl_console_utils", "bl_rna_utils", "bl_text_utils",
    "bl_ext", "bl_pkg", "_bpy_internal",
}
PREFIXES_BLENDER = ("bl_", "io_", "bpy")

EXC_IMPORT = {"ImportError", "ModuleNotFoundError", "Exception", "BaseException"}
ORDRE_FAMILLES = ("introuvable", "tiers", "autre_projet", "local", "blender", "stdlib")
RE_CHEMIN_OUTIL = re.compile(r"(Python3\d\d|Program Files|AppData[\\/]+(Local|Roaming)|"
                             r"Blender Foundation|ODAFileConverter|ODA Viewer|nodejs)", re.I)


def racines_par_defaut():
    r = [os.path.join(RACINE, s) for s in SOUS_DOSSIERS_RACINE]
    parent = os.path.dirname(RACINE)
    r += sorted(glob.glob(os.path.join(parent, "*_Blender")))
    r.append(os.path.join(parent, "Immeuble_65_logements"))
    return [x for x in r if os.path.isdir(x)]


def fichiers_py(racine):
    for d, sous, fichiers in os.walk(racine):
        sous[:] = [s for s in sous if s not in DOSSIERS_IGNORES]
        for f in fichiers:
            if f.lower().endswith(".py"):
                yield os.path.join(d, f)


def noms_locaux(racine):
    """Noms de modules definis dans une arborescence : fichiers .py et dossiers qui en contiennent."""
    noms = set()
    for chemin in fichiers_py(racine):
        noms.add(os.path.splitext(os.path.basename(chemin))[0])
        d = os.path.dirname(chemin)
        while len(d) > len(racine):
            noms.add(os.path.basename(d))
            d = os.path.dirname(d)
    # Extensions compilees (.pyd) posees dans le projet
    for d, sous, fichiers in os.walk(racine):
        sous[:] = [s for s in sous if s not in DOSSIERS_IGNORES]
        for f in fichiers:
            if f.lower().endswith(".pyd"):
                noms.add(f.split(".")[0])
    return noms


def lire_source(chemin):
    with open(chemin, "rb") as f:
        brut = f.read()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return brut.decode(enc)
        except UnicodeDecodeError:
            continue
    return brut.decode("latin-1", "replace")


def attrape_import(handler):
    t = handler.type
    if t is None:
        return True
    elts = t.elts if isinstance(t, ast.Tuple) else [t]
    for e in elts:
        nom = e.attr if isinstance(e, ast.Attribute) else getattr(e, "id", None)
        if nom in EXC_IMPORT:
            return True
    return False


def court(noeud, n=120):
    try:
        s = ast.unparse(noeud)
    except Exception:
        s = "?"
    return s if len(s) <= n else s[:n] + "..."


class Visiteur(ast.NodeVisitor):
    def __init__(self):
        self.imports = []      # (nom_complet, niveau, ligne, marques)
        self.dynamiques = []   # (ligne, forme, argument)
        self.sys_path = []     # (ligne, code)
        self.chemins = []      # (ligne, chaine)
        self._try = 0
        self._fonction = 0
        self._typage = 0

    def _marques(self):
        m = []
        if self._try:
            m.append("optionnel")
        if self._fonction:
            m.append("paresseux")
        if self._typage:
            m.append("typage")
        return m

    def visit_Import(self, n):
        for a in n.names:
            self.imports.append((a.name, 0, n.lineno, self._marques()))

    def visit_ImportFrom(self, n):
        nom = n.module or ""
        if n.level == 0 and nom == "__future__":
            return
        if n.level > 0 and not nom:
            # from . import x : x est un module local
            for a in n.names:
                self.imports.append((a.name, n.level, n.lineno, self._marques()))
        else:
            self.imports.append((nom, n.level, n.lineno, self._marques()))

    def visit_Try(self, n):
        protege = any(attrape_import(h) for h in n.handlers)
        if protege:
            self._try += 1
        for x in n.body:
            self.visit(x)
        for h in n.handlers:
            self.visit(h)
        if protege:
            self._try -= 1
        for x in n.orelse + n.finalbody:
            self.visit(x)

    visit_TryStar = visit_Try

    def _fonc(self, n):
        self._fonction += 1
        self.generic_visit(n)
        self._fonction -= 1

    visit_FunctionDef = _fonc
    visit_AsyncFunctionDef = _fonc
    visit_Lambda = _fonc

    def visit_If(self, n):
        t = n.test
        typage = (isinstance(t, ast.Name) and t.id == "TYPE_CHECKING") or \
                 (isinstance(t, ast.Attribute) and t.attr == "TYPE_CHECKING")
        if typage:
            self._typage += 1
            for x in n.body:
                self.visit(x)
            self._typage -= 1
            for x in n.orelse:
                self.visit(x)
        else:
            self.generic_visit(n)

    def visit_Call(self, n):
        f = n.func
        nom = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
        arg = n.args[0] if n.args else None
        if nom in ("import_module", "__import__", "run_path", "run_module",
                   "spec_from_file_location", "SourceFileLoader", "load_source"):
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                val = arg.value
            elif nom == "spec_from_file_location" and len(n.args) > 1:
                val = court(n.args[1])
            else:
                val = court(arg) if arg is not None else ""
            self.dynamiques.append((n.lineno, nom, val))
        elif nom == "exec" and arg is not None and "open(" in court(arg, 400):
            self.dynamiques.append((n.lineno, "exec(open)", court(arg)))
        if isinstance(f, ast.Attribute) and f.attr in ("insert", "append", "extend") and \
                isinstance(f.value, ast.Attribute) and f.value.attr == "path" and \
                isinstance(f.value.value, ast.Name) and f.value.value.id == "sys":
            self.sys_path.append((n.lineno, court(n)))
        self.generic_visit(n)

    def visit_Constant(self, n):
        if isinstance(n.value, str) and len(n.value) < 400 and RE_CHEMIN_OUTIL.search(n.value) \
                and re.search(r"[A-Za-z]:[\\/]", n.value):
            self.chemins.append((getattr(n, "lineno", 0), n.value))


def versions_distributions():
    return {(d.metadata["Name"] or "?"): d.version for d in md.distributions()}


_INDEX = {}


def index_fichiers():
    """chemin absolu normalise d'un fichier installe -> nom de distribution (construit a la demande :
    c'est lent, plusieurs dizaines de secondes sur 375 distributions)."""
    if not _INDEX:
        for dist in md.distributions():
            nom = dist.metadata["Name"] or "?"
            try:
                fichiers = dist.files or []
            except Exception:
                fichiers = []
            for f in fichiers:
                try:
                    p = os.path.normcase(os.path.abspath(str(dist.locate_file(f))))
                except Exception:
                    continue
                _INDEX.setdefault(p, nom)
    return _INDEX


def trouver_spec(tete):
    chemins = [p for p in sys.path if p and os.path.normcase(os.path.abspath(p)) != os.path.normcase(ICI)]
    try:
        return importlib.machinery.PathFinder.find_spec(tete, chemins) or importlib.util.find_spec(tete)
    except (ImportError, ValueError):
        return None


def distribution_de(tete, spec, pd):
    if tete in pd:
        return pd[tete]
    par_fichier = index_fichiers()
    candidats = []
    if spec is not None:
        if spec.origin and spec.origin not in ("built-in", "frozen", None):
            candidats.append(spec.origin)
        for loc in (spec.submodule_search_locations or []):
            init = os.path.join(loc, "__init__.py")
            candidats.append(init if os.path.exists(init) else loc)
    for c in candidats:
        p = os.path.normcase(os.path.abspath(c))
        if p in par_fichier:
            return [par_fichier[p]]
        # dossier de paquet : un fichier quelconque dessous
        prefixe = p.rstrip("\\/") + os.sep
        for f, dist in par_fichier.items():
            if f.startswith(prefixe):
                return [dist]
    return []


def site_packages_blender():
    motifs = [os.path.join(RACINE, "outils", "blender", "**", "python", "lib", "site-packages"),
              r"C:\Program Files\Blender Foundation\Blender *\*\python\lib\site-packages"]
    env = os.environ.get("BM_BLENDER")
    if env:
        motifs.insert(0, os.path.join(os.path.dirname(env), "*", "python", "lib", "site-packages"))
    for m in motifs:
        r = sorted(glob.glob(m, recursive=True))
        if r:
            return r[-1]
    return None


def noms_blender_site(sp):
    noms = set()
    if not sp:
        return noms
    for f in os.listdir(sp):
        if f.endswith((".dist-info", ".egg-info", ".pth", ".txt")) or f == "__pycache__":
            continue
        noms.add(f.split(".")[0])
    return noms


def main(argv):
    try:
        sys.stdout.reconfigure(errors="replace")   # console cp850/cp1252 : jamais de plantage
    except Exception:
        pass
    args = [a for a in argv if not a.startswith("--")]
    sortie_json = None
    if "--json" in argv:
        i = argv.index("--json")
        sortie_json = argv[i + 1]
        args = [a for a in args if a != sortie_json]
    detail = "--detail" in argv
    racines = [os.path.abspath(a) for a in args] or racines_par_defaut()

    stdlib = set(sys.stdlib_module_names)
    locaux = {r: noms_locaux(r) for r in racines}
    versions = versions_distributions()
    pd = md.packages_distributions()
    sp_blender = site_packages_blender()
    fournis_blender = noms_blender_site(sp_blender)

    modules = {}      # tete -> infos
    par_fichier_py = {}
    erreurs = []
    n_fichiers = 0
    for r in racines:
        for chemin in sorted(fichiers_py(r)):
            n_fichiers += 1
            try:
                arbre = ast.parse(lire_source(chemin), filename=chemin)
            except SyntaxError as e:
                erreurs.append((chemin, "SyntaxError ligne %s : %s" % (e.lineno, e.msg)))
                continue
            v = Visiteur()
            v.visit(arbre)
            tetes = {nom.split(".")[0] for nom, niveau, _, _ in v.imports if niveau == 0 and nom}
            est_blender = bool(tetes & {"bpy", "bmesh", "mathutils", "gpu", "bpy_extras"})
            rel = os.path.relpath(chemin, os.path.dirname(RACINE))
            par_fichier_py[rel] = {"blender": est_blender, "imports": [],
                                   "dynamiques": v.dynamiques, "sys_path": v.sys_path,
                                   "chemins_en_dur": v.chemins}
            for nom, niveau, ligne, marques in v.imports:
                tete = nom.split(".")[0] if nom else nom
                if niveau > 0:
                    famille = "local"
                elif tete in stdlib:
                    famille = "stdlib"
                elif tete in BLENDER or tete.startswith(PREFIXES_BLENDER):
                    famille = "blender"
                elif tete in locaux[r]:
                    famille = "local"
                elif any(tete in locaux[a] for a in racines if a != r):
                    famille = "autre_projet"
                else:
                    famille = None
                cle = tete if niveau == 0 else "." * niveau + (nom or "")
                par_fichier_py[rel]["imports"].append([nom, niveau, ligne, marques])
                m = modules.setdefault(cle, {"familles": {}, "fichiers": {}, "toujours_optionnel": True,
                                             "hors_blender": False, "dans_blender": False})
                # Un meme nom peut etre local dans un projet et introuvable dans un autre : famille par fichier.
                m["familles"].setdefault(famille or "a_resoudre", {}).setdefault(rel, []).append(ligne)
                m["fichiers"].setdefault(rel, []).append(ligne)
                if "optionnel" not in marques and "typage" not in marques:
                    m["toujours_optionnel"] = False
                if est_blender:
                    m["dans_blender"] = True
                else:
                    m["hors_blender"] = True
                if famille == "autre_projet":
                    m["projets"] = sorted({os.path.basename(a) for a in racines if tete in locaux[a]})

    # Resolution des noms restants : tiers (installe dans cet interpreteur) ou introuvable
    for tete, m in modules.items():
        if "a_resoudre" in m["familles"]:
            fichiers = m["familles"].pop("a_resoudre")
            spec = trouver_spec(tete)
            if spec is None:
                m["familles"]["introuvable"] = fichiers
            else:
                m["familles"]["tiers"] = fichiers
                dists = distribution_de(tete, spec, pd)
                m["distributions"] = {d: versions.get(d, "?") for d in dists}
                m["origine"] = spec.origin if spec.origin not in (None, "built-in", "frozen") else \
                    (list(spec.submodule_search_locations or [""])[0] if spec.submodule_search_locations
                     else spec.origin)
                m["fourni_par_blender"] = tete in fournis_blender
        # famille principale (la plus parlante) : introuvable > tiers > autre_projet > local > blender > stdlib
        m["famille"] = next(f for f in ORDRE_FAMILLES if f in m["familles"])

    # ---- Rapport texte
    print("Interpreteur :", sys.executable, sys.version.split()[0])
    print("Racines analysees (%d) :" % len(racines))
    for r in racines:
        print("   ", r)
    print("Fichiers .py : %d ; illisibles : %d" % (n_fichiers, len(erreurs)))
    for c, e in erreurs:
        print("    ILLISIBLE", c, e)
    print("site-packages de Blender :", sp_blender or "introuvable")
    fam = {}
    for tete, m in modules.items():
        for f in m["familles"]:
            fam.setdefault(f, []).append(tete)
    for f in ("stdlib", "blender", "local", "autre_projet", "tiers", "introuvable"):
        noms = sorted(fam.get(f, []), key=str.lower)
        print("\n== %s (%d)" % (f, len(noms)))
        if f == "tiers":
            dist_vues = {}
            for t in noms:
                m = modules[t]
                for d, ver in m.get("distributions", {}).items():
                    dist_vues.setdefault((d, ver), []).append(t)
                ou = []
                if m["hors_blender"]:
                    ou.append("Python systeme")
                if m["dans_blender"]:
                    ou.append("Blender" + ("" if m["fourni_par_blender"] else " (NON fourni par Blender !)"))
                opt = " [toujours optionnel]" if m["toujours_optionnel"] else ""
                dd = ", ".join("%s %s" % (d, v) for d, v in m.get("distributions", {}).items()) or "sans distribution"
                n_fi = len(m["familles"][f])
                print("   %-22s %-38s %3d fichier(s) ; %s%s" % (t, dd, n_fi, " + ".join(ou), opt))
                if detail:
                    for fi in sorted(m["familles"][f]):
                        print("        ", fi, m["familles"][f][fi])
            print("\n   Distributions pip necessaires (%d) :" % len(dist_vues))
            for (d, ver), ts in sorted(dist_vues.items(), key=lambda x: x[0][0].lower()):
                print("     %s==%s   (%s)" % (d, ver, ", ".join(sorted(ts))))
        elif f in ("introuvable", "autre_projet"):
            for t in noms:
                m = modules[t]
                opt = " [toujours optionnel]" if m["toujours_optionnel"] else ""
                extra = (" <- " + ", ".join(m.get("projets", []))) if f == "autre_projet" else ""
                print("   %-28s%s%s" % (t, opt, extra))
                fichiers = m["familles"][f]
                for fi in sorted(fichiers)[:6]:
                    print("        ", fi, fichiers[fi])
                if len(fichiers) > 6:
                    print("         ... et %d autre(s)" % (len(fichiers) - 6))
        else:
            print("   " + ", ".join(noms))

    dyn = [(f, d) for f, x in par_fichier_py.items() for d in x["dynamiques"]]
    print("\n== imports dynamiques (%d)" % len(dyn))
    for f, (ligne, forme, val) in dyn:
        print("   %s:%d  %s(%s)" % (f, ligne, forme, val))
    sp = [(f, s) for f, x in par_fichier_py.items() for s in x["sys_path"]]
    print("\n== sys.path modifie (%d)" % len(sp))
    for f, (ligne, code) in sp:
        print("   %s:%d  %s" % (f, ligne, code))
    ch = [(f, c) for f, x in par_fichier_py.items() for c in x["chemins_en_dur"]]
    print("\n== chemins d'outils ecrits en dur (%d)" % len(ch))
    for f, (ligne, s) in ch:
        print("   %s:%d  %s" % (f, ligne, s))

    if sortie_json:
        with open(sortie_json, "w", encoding="utf-8", newline="\n") as fo:
            json.dump({"interpreteur": sys.executable, "version": sys.version.split()[0],
                       "racines": racines, "site_packages_blender": sp_blender,
                       "modules": modules, "fichiers": par_fichier_py,
                       "illisibles": erreurs}, fo, ensure_ascii=False, indent=1, sort_keys=True)
        print("\nJSON :", sortie_json)
    # NB : un nom « introuvable » peut etre normal (module d'un autre depot, ex. cad_script du clone de
    # l'ERP ajoute a sys.path) : le rapport dit ou il est importe.
    manque = [t for t in fam.get("introuvable", []) if not modules[t]["toujours_optionnel"]]
    return 3 if manque else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
