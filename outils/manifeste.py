# -*- coding: utf-8 -*-
r"""
outils\manifeste.py -- manifeste d'une COPIE du dossier du poste (2026-09-25, soir).

Chaque fichier copié : chemin relatif, taille et SHA-256. Le manifeste est calculé sur la SOURCE
par outils\copier_vers_poste.ps1, puis relu sur le poste d'arrivée par outils\verifier_copie.ps1 :
un fichier absent, tronqué ou abîmé en route se voit, fichier par fichier.

Tout est haché (et pas seulement les .exe, .dll et .pyd) : mesuré le 2026-09-25 sur ce poste,
environ 5 Go et 140 000 fichiers en quelques minutes avec 8 fils (hashlib relâche le verrou de
Python pendant le calcul). Les binaires et les fichiers de savoir sont en plus comptés à part
dans le résumé.

Usage (le Python du dossier : outils\python\python.exe -s -X utf8 outils\manifeste.py ...)
  ecrire   <racine> <manifeste.json> [--exclure-dossier NOM]... [--exclure-fichier MOTIF]...
                                     [--exclure-chemin CHEMIN_RELATIF]...
  verifier <racine> <manifeste.json> [--rapport rapport.json] [--rapide]
                                     (--rapide : SHA-256 des .exe, .dll, .pyd et des fichiers de savoir et
                                     de réglage seulement ; la TAILLE suffit pour les autres)
  lister   <racine> [mêmes exclusions]      nombre de fichiers et octets, sans hacher
  marques  <racine> [--liste f.txt]         fichiers marqués « venu d'Internet » (Zone.Identifier)

Exclusions (les MÊMES pour robocopy et pour le manifeste ; enregistrées dans le manifeste, et
reprises telles quelles par « verifier ») :
  --exclure-dossier  nom de dossier, à toute profondeur, sans tenir compte de la casse
                     (__pycache__, .pytest_cache) ;
  --exclure-fichier  motif de nom de fichier, à toute profondeur (PRET_*.txt, ETAT_*.txt) ;
  --exclure-chemin   chemin relatif précis, fichier ou dossier (Metre\donnees\pgdata.log).
Le manifeste lui-même (outils\manifeste_copie.json) n'y figure jamais.

Codes de sortie : 0 conforme (ou écrit) ; 1 différences ; 2 erreur d'usage ou de lecture.
Pur Python standard, 3.9 et plus.
"""
import argparse
import concurrent.futures
import datetime
import fnmatch
import hashlib
import json
import os
import sys
import time

NOM_MANIFESTE = os.path.join("outils", "manifeste_copie.json")
BINAIRES = (".exe", ".dll", ".pyd")
SAVOIR = (".md", ".txt", ".json", ".py", ".ps1", ".cmd", ".bat", ".toml", ".cfg", ".ini", ".yml", ".yaml", ".conf",
          ".env")


def _cle(p):
    return p.replace("/", "\\").strip("\\").lower()


class Exclusions:
    def __init__(self, dossiers=(), fichiers=(), chemins=()):
        self.dossiers = sorted({d.lower() for d in dossiers})
        self.fichiers = sorted({f.lower() for f in fichiers})
        self.chemins = sorted({_cle(c) for c in chemins} | {_cle(NOM_MANIFESTE)})

    def en_dict(self):
        return {"dossiers": self.dossiers, "fichiers": self.fichiers, "chemins": self.chemins}

    @classmethod
    def depuis(cls, d):
        return cls(d.get("dossiers", ()), d.get("fichiers", ()), d.get("chemins", ()))

    def dossier_exclu(self, nom, rel):
        return nom.lower() in self.dossiers or _cle(rel) in self.chemins

    def fichier_exclu(self, nom, rel):
        n = nom.lower()
        return _cle(rel) in self.chemins or any(fnmatch.fnmatchcase(n, m) for m in self.fichiers)


def parcourir(racine, excl):
    """-> liste de (chemin relatif, chemin complet, taille). Les liens et jonctions ne sont pas suivis."""
    res, pile = [], [""]
    while pile:
        rel_d = pile.pop()
        d = os.path.join(racine, rel_d) if rel_d else racine
        try:
            entrees = list(os.scandir(d))
        except OSError:
            continue
        for e in entrees:
            rel = os.path.join(rel_d, e.name) if rel_d else e.name
            try:
                if e.is_dir(follow_symlinks=False):
                    if not e.is_symlink() and not excl.dossier_exclu(e.name, rel):
                        pile.append(rel)
                elif e.is_file(follow_symlinks=False):
                    if not excl.fichier_exclu(e.name, rel):
                        res.append((rel, e.path, e.stat(follow_symlinks=False).st_size))
            except OSError:
                continue
    res.sort(key=lambda t: t[0].lower())
    return res


def sha256(chemin, taille_bloc=1 << 20):
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        while True:
            b = f.read(taille_bloc)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def hacher(fichiers, fils=8):
    """{chemin relatif: (taille, sha256 ou 'ILLISIBLE: ...')}."""
    out = {}

    def un(t):
        rel, plein, taille = t
        try:
            return rel, taille, sha256(plein)
        except OSError as e:
            return rel, taille, "ILLISIBLE: %s" % e.strerror

    with concurrent.futures.ThreadPoolExecutor(max_workers=fils) as ex:
        for rel, taille, h in ex.map(un, fichiers, chunksize=64):
            out[rel] = (taille, h)
    return out


def resume(fichiers):
    n_bin = sum(1 for f in fichiers if f.lower().endswith(BINAIRES))
    n_sav = sum(1 for f in fichiers if f.lower().endswith(SAVOIR))
    return n_bin, n_sav


def cmd_ecrire(a):
    excl = Exclusions(a.exclure_dossier, a.exclure_fichier, a.exclure_chemin)
    t0 = time.time()
    liste = parcourir(a.racine, excl)
    t1 = time.time()
    h = hacher(liste, a.fils)
    t2 = time.time()
    illisibles = sorted(r for r, (_, x) in h.items() if x.startswith("ILLISIBLE"))
    octets = sum(t for t, _ in h.values())
    n_bin, n_sav = resume(h)
    doc = {"format": "manifeste_copie v1", "algorithme": "sha256",
           "cree_le": datetime.datetime.now().isoformat(timespec="seconds"),
           "poste": os.environ.get("COMPUTERNAME", ""), "racine_source": os.path.abspath(a.racine),
           "nb_fichiers": len(h), "octets": octets, "binaires": n_bin, "fichiers_de_savoir": n_sav,
           "illisibles": illisibles, "exclusions": excl.en_dict(),
           "fichiers": {r: [t, x] for r, (t, x) in sorted(h.items(), key=lambda kv: kv[0].lower())}}
    os.makedirs(os.path.dirname(os.path.abspath(a.manifeste)), exist_ok=True)
    tmp = a.manifeste + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, indent=0)
    os.replace(tmp, a.manifeste)
    print("MANIFESTE_ECRIT fichiers=%d octets=%d binaires=%d savoir=%d illisibles=%d parcours_s=%.1f hachage_s=%.1f"
          % (len(h), octets, n_bin, n_sav, len(illisibles), t1 - t0, t2 - t1))
    for r in illisibles[:20]:
        print("  illisible : %s (%s)" % (r, h[r][1]))
    return 2 if illisibles else 0


def cmd_verifier(a):
    try:
        with open(a.manifeste, encoding="utf-8") as f:
            doc = json.load(f)
    except (OSError, ValueError) as e:
        print("MANIFESTE_ILLISIBLE %s" % e)
        return 2
    excl = Exclusions.depuis(doc.get("exclusions", {}))
    attendu = doc.get("fichiers", {})
    t0 = time.time()
    liste = parcourir(a.racine, excl)
    presents = {r: (p, t) for r, p, t in liste}
    cle_pres = {r.lower(): r for r in presents}
    manquants, tailles, differents = [], [], []
    a_hacher = []
    tailles_seules = 0
    for rel, (taille, h) in attendu.items():
        r = cle_pres.get(rel.lower())
        if r is None:
            manquants.append(rel)
        elif presents[r][1] != taille:
            tailles.append(rel)
        elif a.rapide and not rel.lower().endswith(BINAIRES + SAVOIR):
            tailles_seules += 1           # --rapide : la taille suffit pour les fichiers de données
        else:
            a_hacher.append((r, presents[r][0], taille))
    h = hacher(a_hacher, a.fils)
    attendu_min = {k.lower(): v for k, v in attendu.items()}
    for r, (taille, x) in h.items():
        if x != attendu_min[r.lower()][1]:
            differents.append(r)
    en_trop = sorted(r for r in presents if r.lower() not in attendu_min)
    rapport = {"racine": os.path.abspath(a.racine), "manifeste": os.path.abspath(a.manifeste),
               "attendus": len(attendu), "verifies": len(h), "tailles_seules": tailles_seules,
               "manquants": sorted(manquants),
               "tailles_differentes": sorted(tailles), "contenus_differents": sorted(differents),
               "en_trop": en_trop, "secondes": round(time.time() - t0, 1)}
    if a.rapport:
        with open(a.rapport, "w", encoding="utf-8") as f:
            json.dump(rapport, f, ensure_ascii=False, indent=1)
    ok = not (manquants or tailles or differents)
    print("MANIFESTE_%s attendus=%d verifies=%d tailles_seules=%d manquants=%d tailles=%d contenus=%d en_trop=%d "
          "secondes=%.1f" % ("CONFORME" if ok else "DIFFERENCES", len(attendu), len(h), tailles_seules, len(manquants),
                             len(tailles), len(differents), len(en_trop), rapport["secondes"]))
    for titre, liste_ in (("manquant", manquants), ("taille differente", tailles), ("contenu different", differents),
                          ("en trop (pas dans le manifeste)", en_trop)):
        for r in sorted(liste_)[:15]:
            print("  %s : %s" % (titre, r))
        if len(liste_) > 15:
            print("  ... et %d autre(s) (%s)" % (len(liste_) - 15, titre))
    return 0 if ok else 1


def _flux_existe():
    """Fonction (chemin -> bool) : le flux « chemin:Zone.Identifier » existe-t-il ?

    PIÈGE MESURÉ (2026-09-25, Windows 11, CPython 3.13) : os.path.exists / os.stat sur « fichier:flux »
    répondent PARFOIS vrai, avec la taille du fichier lui-même, alors que le flux n'existe pas (99 308 faux
    positifs sur 158 270 fichiers). GetFileAttributesW, lui, échoue bien (erreur 2) quand le flux manque."""
    import ctypes
    from ctypes import wintypes
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.GetFileAttributesW.argtypes = [wintypes.LPCWSTR]
    k32.GetFileAttributesW.restype = wintypes.DWORD
    return lambda p: k32.GetFileAttributesW(p + ":Zone.Identifier") != 0xFFFFFFFF


def cmd_marques(a):
    """Fichiers qui portent la marque « venu d'Internet » (flux Zone.Identifier : ZIP téléchargé, courriel).
    Liste écrite en UTF-8 dans --liste (les chemins peuvent être accentués) ; verifier_copie.ps1 lance
    ensuite Unblock-File sur eux seuls (Get-Item -Stream sur 120 000 fichiers prendrait 2 à 3 min)."""
    t0 = time.time()
    existe = _flux_existe()
    n, marques = 0, []
    for rac, _, fichiers in os.walk(a.racine):
        for f in fichiers:
            p = os.path.join(rac, f)
            n += 1
            if existe(p):
                marques.append(p)
    if a.liste:
        with open(a.liste, "w", encoding="utf-8", newline="\n") as f:
            f.write("".join(p + "\n" for p in marques))
    print("MARQUES fichiers=%d marques=%d secondes=%.1f" % (n, len(marques), time.time() - t0))
    return 0


def cmd_lister(a):
    excl = Exclusions(a.exclure_dossier, a.exclure_fichier, a.exclure_chemin)
    t0 = time.time()
    liste = parcourir(a.racine, excl)
    n_bin, n_sav = resume([r for r, _, _ in liste])
    print("LISTE fichiers=%d octets=%d binaires=%d savoir=%d parcours_s=%.1f" % (
        len(liste), sum(t for _, _, t in liste), n_bin, n_sav, time.time() - t0))
    return 0


def main(argv=None):
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(errors="replace")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(description="Manifeste d'une copie du dossier du poste (sha256).")
    ap.add_argument("action", choices=("ecrire", "verifier", "lister", "marques"))
    ap.add_argument("racine")
    ap.add_argument("manifeste", nargs="?")
    ap.add_argument("--exclure-dossier", action="append", default=[])
    ap.add_argument("--exclure-fichier", action="append", default=[])
    ap.add_argument("--exclure-chemin", action="append", default=[])
    ap.add_argument("--rapport")
    ap.add_argument("--rapide", action="store_true",
                    help="verifier : SHA-256 des binaires et des fichiers de savoir seulement, taille pour le reste")
    ap.add_argument("--liste", help="marques : fichier UTF-8 où écrire les chemins marqués")
    ap.add_argument("--fils", type=int, default=8)
    a = ap.parse_args(argv)
    if a.action in ("ecrire", "verifier") and not a.manifeste:
        ap.error("le chemin du manifeste est requis")
    if not os.path.isdir(a.racine):
        print("racine introuvable : %s" % a.racine)
        return 2
    return {"ecrire": cmd_ecrire, "verifier": cmd_verifier, "lister": cmd_lister,
            "marques": cmd_marques}[a.action](a)


if __name__ == "__main__":
    sys.exit(main())
