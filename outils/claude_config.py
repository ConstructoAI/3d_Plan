# -*- coding: utf-8 -*-
r"""
outils\claude_config.py -- la configuration de Claude Code DANS le dossier du poste (« zéro trace »).

2026-09-25, soir. Le lanceur pose CLAUDE_CONFIG_DIR = <racine>\outils\claude\config : réglages,
compétences (skills), plugins, mémoire des projets, sessions, .claude.json (serveurs MCP) et, après la
PREMIÈRE connexion, les identifiants, tout y est rangé au lieu de %USERPROFILE%\.claude.

Vérifié le 2026-09-25 (Claude Code 2.1.283, dossier temporaire, commandes non interactives) :
  - « claude auth status » rend configDirectory = CLAUDE_CONFIG_DIR et projectsDirectory = ...\projects ;
  - .claude.json est lu et écrit DANS CLAUDE_CONFIG_DIR (un serveur MCP qu'on y écrit apparaît
    comme « User config »), avec des sauvegardes dans ...\backups ;
  - sans identifiants dans ce dossier : « loggedIn: false » (ceux du profil ne sont PAS repris) ;
  - « claude --version » n'écrit rien.

Actions
  migrer  : COPIE depuis le profil de l'utilisateur (jamais déplacé ni modifié), sans rien écraser :
            settings.json, settings.local.json, skills\, plugins\ (chemins absolus réécrits), la mémoire
            du projet (projects\<clé>\memory\), et s'ils existent agents\, commands\, output-styles\,
            keybindings.json, CLAUDE.md ; dans .claude.json, SEULEMENT les serveurs MCP de
            l'utilisateur et, pour le projet du dossier, mcpServers, hasTrustDialogAccepted,
            allowedTools, enabledMcpjsonServers, disabledMcpjsonServers,
            hasClaudeMdExternalIncludesApproved. JAMAIS : les identifiants (.credentials.json),
            oauthAccount, userID, machineID, les caches, les transcriptions des sessions,
            file-history\, history.jsonl (il peut contenir des clés tapées).
  suivre  : à chaque lancement (rapide). La mémoire d'un projet et son entrée de .claude.json sont
            rangées sous le CHEMIN ABSOLU du dossier (clé « C--Dev-blender-main »). Si le dossier a été
            collé ailleurs, recopie la mémoire de l'ancienne clé vers la nouvelle et reprend l'entrée
            du projet (sans rien effacer), puis note la nouvelle clé dans outils\claude\cle_projet.txt.
  etat    : ce qui est en place (sans jamais ouvrir les identifiants : leur présence seulement).

Usage : outils\python\python.exe -s -X utf8 outils\claude_config.py migrer|suivre|etat [--profil DOSSIER]
Retour arrière : sans CLAUDE_CONFIG_DIR (BM_CLAUDE_CONFIG=profil, ou dossier config renommé), Claude
reprend %USERPROFILE%\.claude et %USERPROFILE%\.claude.json, intacts.
"""
import argparse
import datetime
import json
import os
import re
import shutil
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
CONFIG = os.path.join(ICI, "claude", "config")
FICHIER_CLE = os.path.join(ICI, "claude", "cle_projet.txt")
RAPPORT_MIGRATION = os.path.join(ICI, "claude", "migration_config.json")

CLES_PROJET = ("mcpServers", "hasTrustDialogAccepted", "allowedTools", "enabledMcpjsonServers",
               "disabledMcpjsonServers", "hasClaudeMdExternalIncludesApproved")
FICHIERS = ("settings.json", "settings.local.json", "keybindings.json", "CLAUDE.md")
DOSSIERS = ("skills", "plugins", "agents", "commands", "output-styles")
JAMAIS = (".credentials.json", "history.jsonl")


def cle_memoire(chemin):
    """Clé d'un projet sous projects\\ : chaque caractère hors [A-Za-z0-9] devient « - »
    (C:\\Dev\\blender-main -> C--Dev-blender-main), comme Claude Code."""
    return re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(chemin).rstrip("\\/"))


def cle_json(chemin):
    """Clé du projet dans .claude.json : le chemin avec des barres obliques (C:/Dev/blender-main)."""
    return os.path.abspath(chemin).rstrip("\\/").replace("\\", "/")


def lire_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def ecrire_json(p, doc):
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)


def copier_sans_ecraser(src, dst, journal):
    """Copie l'arborescence src dans dst ; un fichier déjà présent dans dst n'est jamais remplacé."""
    n = 0
    for rac, dossiers, fichiers in os.walk(src):
        dossiers[:] = [d for d in dossiers if d != "__pycache__"]
        rel = os.path.relpath(rac, src)
        cible = os.path.join(dst, rel) if rel != "." else dst
        os.makedirs(cible, exist_ok=True)
        for f in fichiers:
            if f in JAMAIS:
                continue
            d = os.path.join(cible, f)
            if not os.path.exists(d):
                shutil.copy2(os.path.join(rac, f), d)
                n += 1
    journal.append("%s -> %s : %d fichier(s)" % (src, dst, n))
    return n


def chemins_absolus(txt):
    return sorted(set(re.findall(r"[A-Za-z]:(?:\\\\|\\|/)[^\"\n]{0,120}", txt)))


def reecrire_plugins(dst_plugins, ancien_profil, journal):
    """installLocation / installPath des plugins : l'ancien dossier du profil -> le dossier config."""
    for nom in ("known_marketplaces.json", "installed_plugins.json"):
        p = os.path.join(dst_plugins, nom)
        if not os.path.isfile(p):
            continue
        txt = open(p, encoding="utf-8").read()
        ancien = json.dumps(ancien_profil)[1:-1]          # forme échappée pour JSON (\\)
        nouveau = json.dumps(CONFIG)[1:-1]
        if ancien.lower() in txt.lower():
            txt = re.sub(re.escape(ancien), lambda m: nouveau, txt, flags=re.I)
            with open(p, "w", encoding="utf-8", newline="\n") as f:
                f.write(txt)
            journal.append("%s : chemins réécrits vers %s" % (nom, CONFIG))
        reste = [c for c in chemins_absolus(txt) if ancien_profil.lower() in c.lower().replace("\\\\", "\\")]
        if reste:
            journal.append("%s : chemins de l'ancien profil encore présents : %s" % (nom, reste))


def migrer(a):
    profil = os.path.abspath(a.profil)
    json_profil = os.path.join(os.path.dirname(profil), ".claude.json")
    os.makedirs(CONFIG, exist_ok=True)
    journal, signalements = [], []
    for f in FICHIERS:
        s = os.path.join(profil, f)
        if os.path.isfile(s):
            d = os.path.join(CONFIG, f)
            if os.path.exists(d):
                journal.append("%s : déjà dans le dossier, gardé" % f)
            else:
                shutil.copy2(s, d)
                journal.append("%s : copié" % f)
            abs_ = chemins_absolus(open(s, encoding="utf-8", errors="replace").read())
            if abs_:
                signalements.append("%s contient des chemins absolus : %s" % (f, abs_))
        else:
            journal.append("%s : absent du profil" % f)
    for d in DOSSIERS:
        s = os.path.join(profil, d)
        if os.path.isdir(s):
            copier_sans_ecraser(s, os.path.join(CONFIG, d), journal)
        else:
            journal.append("%s\\ : absent du profil" % d)
    reecrire_plugins(os.path.join(CONFIG, "plugins"), profil, journal)
    # Mémoire du projet (sous la clé du chemin ACTUEL du dossier)
    cle = cle_memoire(RACINE)
    mem = os.path.join(profil, "projects", cle, "memory")
    if os.path.isdir(mem):
        copier_sans_ecraser(mem, os.path.join(CONFIG, "projects", cle, "memory"), journal)
    else:
        journal.append("mémoire du projet (projects\\%s\\memory) : ABSENTE du profil, rien à copier" % cle)
    # .claude.json : seulement les clés voulues
    cible = os.path.join(CONFIG, ".claude.json")
    doc = lire_json(cible) if os.path.isfile(cible) else {}
    if os.path.isfile(json_profil):
        ancien = lire_json(json_profil)
        mcp = ancien.get("mcpServers") or {}
        if mcp:
            doc.setdefault("mcpServers", {})
            for nom, v in mcp.items():
                if nom not in doc["mcpServers"]:
                    doc["mcpServers"][nom] = v
            journal.append(".claude.json : serveurs MCP de l'utilisateur repris : %s" % ", ".join(sorted(mcp)))
            for nom, v in mcp.items():
                for c in chemins_absolus(json.dumps(v)):
                    if not c.lower().replace("\\\\", "\\").startswith(RACINE.lower()):
                        signalements.append("serveur MCP « %s » : chemin HORS du dossier (%s) : il ne suivra "
                                            "pas une copie sur un autre poste" % (nom, c.replace("\\\\", "\\")))
        projets = ancien.get("projects") or {}
        src = projets.get(cle_json(RACINE)) or next(
            (v for k, v in projets.items() if k.replace("\\", "/").lower() == cle_json(RACINE).lower()), None)
        if src:
            entree = doc.setdefault("projects", {}).setdefault(cle_json(RACINE), {})
            prises = [k for k in CLES_PROJET if k in src and k not in entree]
            for k in prises:
                entree[k] = src[k]
            journal.append(".claude.json : projet %s : %s" % (cle_json(RACINE), ", ".join(prises) or "rien de neuf"))
        else:
            journal.append(".claude.json : aucune entrée pour le projet %s dans le profil" % cle_json(RACINE))
        ecrire_json(cible, doc)
    else:
        journal.append(".claude.json du profil absent")
    with open(FICHIER_CLE, "w", encoding="utf-8", newline="\n") as f:
        f.write(RACINE + "\n")
    rapport = {"date": datetime.datetime.now().isoformat(timespec="seconds"), "profil_source": profil,
               "config": CONFIG, "racine": RACINE, "cle_memoire": cle, "journal": journal,
               "signalements": signalements,
               "jamais_copie": [".credentials.json (identifiants)", "oauthAccount, userID, machineID, caches",
                                "projects\\*\\*.jsonl (transcriptions)", "file-history\\", "history.jsonl"]}
    ecrire_json(RAPPORT_MIGRATION, rapport)
    for l in journal:
        print("  " + l)
    for s in signalements:
        print("  [à savoir] " + s)
    print("MIGRATION_FAITE config=%s" % CONFIG)
    return 0


def sessions_ancien_profil(profil):
    """Nombre de sessions (transcriptions .jsonl) de CE dossier restées dans le profil de l'utilisateur."""
    if os.path.normcase(os.path.abspath(profil)) == os.path.normcase(CONFIG):
        return 0
    d = os.path.join(profil, "projects", cle_memoire(RACINE))
    try:
        return sum(1 for f in os.listdir(d) if f.endswith(".jsonl"))
    except OSError:
        return 0


def suivre(a):
    """Le dossier a-t-il changé de place depuis le dernier lancement ? Si oui, suivre la mémoire et le projet.
    --lanceur : lignes ASCII pour Demarrer-Blender.bat (SUIVRE_RIEN, SUIVRE_DEPLACE <texte>, ANCIEN_PROFIL <n>)."""
    code = suivre_sans_rapport(a)
    if a.lanceur:
        n = sessions_ancien_profil(a.profil)
        if n:
            print("ANCIEN_PROFIL %d" % n)
    return code


def suivre_sans_rapport(a):
    if not os.path.isdir(CONFIG):
        print("SUIVRE_RIEN" if a.lanceur else "SUIVRE pas de configuration dans le dossier : rien à faire")
        return 0
    avant = ""
    if os.path.isfile(FICHIER_CLE):
        avant = open(FICHIER_CLE, encoding="utf-8").read().strip()
    if avant and os.path.normcase(os.path.abspath(avant)) == os.path.normcase(RACINE):
        print("SUIVRE_RIEN" if a.lanceur else "SUIVRE même emplacement : rien à faire")
        return 0
    faits = []
    if avant:
        ancienne, nouvelle = cle_memoire(avant), cle_memoire(RACINE)
        src = os.path.join(CONFIG, "projects", ancienne, "memory")
        if os.path.isdir(src) and ancienne != nouvelle:
            dst = os.path.join(CONFIG, "projects", nouvelle, "memory")
            n = 0
            for f in os.listdir(src):
                s, d = os.path.join(src, f), os.path.join(dst, f)
                if os.path.isfile(s) and (not os.path.exists(d) or os.path.getmtime(s) > os.path.getmtime(d)):
                    os.makedirs(dst, exist_ok=True)
                    shutil.copy2(s, d)
                    n += 1
            faits.append("mémoire %s -> %s : %d fichier(s)" % (ancienne, nouvelle, n))
        cj = os.path.join(CONFIG, ".claude.json")
        if os.path.isfile(cj):
            doc = lire_json(cj)
            projets = doc.get("projects") or {}
            ancien = projets.get(cle_json(avant))
            if ancien and cle_json(RACINE) not in projets:
                projets[cle_json(RACINE)] = {k: ancien[k] for k in CLES_PROJET if k in ancien}
                doc["projects"] = projets
                shutil.copy2(cj, cj + ".avant_deplacement")
                ecrire_json(cj, doc)
                faits.append(".claude.json : projet repris de %s vers %s" % (cle_json(avant), cle_json(RACINE)))
    with open(FICHIER_CLE, "w", encoding="utf-8", newline="\n") as f:
        f.write(RACINE + "\n")
    if a.lanceur:
        # ASCII : la fenêtre de cmd.exe l'affiche telle quelle.
        texte = "%s -> %s ; memoire et reglages du projet repris" % (avant or "(inconnu)", RACINE)
        print("SUIVRE_DEPLACE " + texte.encode("ascii", "replace").decode("ascii"))
    else:
        print("SUIVRE dossier %s -> %s ; %s" % (avant or "(inconnu)", RACINE, " ; ".join(faits) or "rien à reprendre"))
    return 0


def etat(a):
    print("configuration : %s (%s)" % (CONFIG, "présente" if os.path.isdir(CONFIG) else "ABSENTE"))
    print("connecté : %s" % ("oui (identifiants présents dans le dossier)"
                             if os.path.isfile(os.path.join(CONFIG, ".credentials.json"))
                             else "non : Claude demandera de se connecter une fois"))
    print("clé de mémoire du dossier : %s" % cle_memoire(RACINE))
    m = os.path.join(CONFIG, "projects", cle_memoire(RACINE), "memory")
    print("mémoire du projet : %s" % (", ".join(sorted(os.listdir(m))) if os.path.isdir(m) else "aucune"))
    if os.path.isfile(os.path.join(CONFIG, ".claude.json")):
        doc = lire_json(os.path.join(CONFIG, ".claude.json"))
        print("serveurs MCP de l'utilisateur : %s" % ", ".join(sorted(doc.get("mcpServers") or {})))
        p = (doc.get("projects") or {}).get(cle_json(RACINE)) or {}
        print("serveurs MCP du projet : %s" % ", ".join(sorted(p.get("mcpServers") or {})))
    return 0


def main(argv=None):
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(errors="replace")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(description="Configuration de Claude Code dans le dossier du poste.")
    ap.add_argument("action", choices=("migrer", "suivre", "etat"))
    ap.add_argument("--profil", default=os.path.join(os.environ.get("USERPROFILE", ""), ".claude"),
                    help="profil Claude de l'utilisateur à copier (défaut : %%USERPROFILE%%\\.claude)")
    ap.add_argument("--config", help="essais : un autre dossier de configuration que outils\\claude\\config "
                                     "(cle_projet.txt et le rapport vont alors à côté de lui)")
    ap.add_argument("--lanceur", action="store_true", help="suivre : sortie ASCII pour Demarrer-Blender.bat")
    a = ap.parse_args(argv)
    if a.config:
        global CONFIG, FICHIER_CLE, RAPPORT_MIGRATION
        CONFIG = os.path.abspath(a.config)
        FICHIER_CLE = os.path.join(os.path.dirname(CONFIG), "cle_projet.txt")
        RAPPORT_MIGRATION = os.path.join(os.path.dirname(CONFIG), "migration_config.json")
    return {"migrer": migrer, "suivre": suivre, "etat": etat}[a.action](a)


if __name__ == "__main__":
    sys.exit(main())
