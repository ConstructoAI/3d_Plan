# -*- coding: utf-8 -*-
"""
Cotes ÉCRITES du plan d'origine (feuilles 3 et 4) contre NOS relevés, entre les mêmes faces : Règle 5.

    python plans\\outils\\comparer_cotes_interieures.py [--sources DOSSIER] [--dxf plans\\bungalow_plans.dxf]
                                                         [--sortie FICHIER.md] [--figer]
    -> plans\\comparaison_cotes_interieures.md ; --figer : plans\\outils\\cotes_origine.json

Méthode :
  1. les cotes écrites et leurs deux tics viennent de l'outil du relevé (reference\\releve_travail\\cotes.py, lecture
     seule) : texte, sens, ligne de cote, positions des tics en pieds du repère du projet. Deux cotes dont l'outil ne
     trouve pas les tics (6'-1" et 2'-0" de la cuisine, feuille 4) sont lues sur un zoom (MANUELLES) ;
  2. chaque tic est rattaché à l'élément de NOS relevés qui passe à cet endroit, perpendiculairement à la cote :
     face extérieure ou intérieure d'un mur, face ou axe d'une cloison, bout d'une cloison (baie sans porte, panneaux
     vitrés), axe d'une ouverture, d'une poutre, d'un poteau ou d'un sonotube, mur de la chambre froide (convention de
     l'original : ossature et faces, axes des ouvertures) ;
  3. notre valeur = distance entre ces deux éléments, dans nos relevés ; écart = notre valeur − valeur écrite ;
  4. « chez nous » : la même valeur est-elle écrite sur NOTRE feuille (A-101 ou A-102) ?
Plus de 1/4" d'écart = écart de Règle 5 : la cote écrite prime, c'est notre relevé qu'il faudrait corriger (fichiers de
l'agent dao n° 2 : ce script ne les modifie pas).

Le générateur du jeu 2D importe ce module (elements, rattacher_el, cotes_figees) : aucun import du PDF au niveau du
module ; les outils du relevé ne sont chargés que pour relire le PDF (lire_cotes, --figer).
"""
import argparse
import json
import math
import os
import re
import sys

sys.dont_write_bytecode = True
ICI = os.path.dirname(os.path.abspath(__file__))
PLANS = os.path.dirname(ICI)
PROJET = os.path.dirname(PLANS)
JSON_FIGE = os.path.join(ICI, "cotes_origine.json")
args = None
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", default=PROJET)
    ap.add_argument("--dxf", default=os.path.join(PLANS, "bungalow_plans.dxf"))
    ap.add_argument("--sortie", default=os.path.join(PLANS, "comparaison_cotes_interieures.md"))
    ap.add_argument("--figer", action="store_true", help="écrit cotes_origine.json (lecture du PDF)")
    args = ap.parse_args()
    sys.path.insert(0, PROJET)
    if os.path.normcase(os.path.abspath(args.sources)) != os.path.normcase(PROJET):
        sys.path.insert(0, os.path.abspath(args.sources))

import parametres_bungalow as P                       # noqa: E402  (le module déjà chargé par le générateur, s'il y a lieu)

RO, RI, RS = P.RO, P.RI, P.RS
TOL = 0.25                                            # 3" : rattachement d'un tic à un élément

# Cotes dont reference\releve_travail\cotes.py ne trouve pas les tics : lues sur un zoom de la feuille 4 (vue RDC),
# grille au pied (dao n° 1, 2026-09-25). Même forme que cotes.cotes() : (texte, vertical, u_texte, v_texte, ligne, a, b,
# valeur en pieds). 6'-1" : face ext. du mur arrière (X 5'-0") -> axe de la cloison C-RDC-10 (X 11'-1") ; 2'-0" : axe
# de C-RDC-10 -> axe de C-RDC-08 ; même chaîne que le 8'-5" (ligne Y ≈ 26'-7").
MANUELLES = {
    "RDC": [("6'-1\"", False, 9.055, 27.129, 26.6, 5.0, 11.083, 6 + 1 / 12),
            ("2'-0\"", False, 12.071, 26.627, 26.6, 11.083, 13.083, 2.0)],
    "SS": [],
}


def _pdf():
    """Outils du relevé (lecture seule), chargés à la demande : ils lisent le PDF d'origine."""
    chemin = os.path.join(PROJET, "reference", "releve_travail")
    if chemin not in sys.path:
        sys.path.append(chemin)                        # APRÈS les sources
    import outils_releve as O                          # noqa: E402
    import cotes as CO                                 # noqa: E402
    return O, CO


def ftin(v):
    s16 = int(round(abs(v) * 12 * 16))
    ft, r = divmod(s16, 192)
    inch, f16 = divmod(r, 16)
    fr = ""
    if f16:
        g = math.gcd(f16, 16)
        fr = f" {f16 // g}/{16 // g}"
    return (f"{ft}'-{inch}{fr}\"" if ft else f"{inch}{fr}\"")


def ecart_txt(e):
    s = "+" if e >= 0 else "−"
    return s + ftin(abs(e))


# ------------------------------------------------------------------------------------------ éléments de nos relevés
def elements(niveau):
    """Références perpendiculaires aux cotes : (sens, coord, a, b, nom) ; sens 'X' = élément à X constant (pour les
    cotes horizontales), 'Y' = à Y constant. a, b : étendue le long de l'élément."""
    out = []

    def seg(x0, y0, x1, y1, nom):
        if abs(x1 - x0) < 1e-6:
            out.append(("X", x0, min(y0, y1), max(y0, y1), nom))
        elif abs(y1 - y0) < 1e-6:
            out.append(("Y", y0, min(x0, x1), max(x0, x1), nom))

    emp = P.EMPRISE_RDC if niveau == "RDC" else P.EMPRISE_SOUS_SOL
    for i in range(len(emp)):
        (x0, y0), (x1, y1) = emp[i], emp[(i + 1) % len(emp)]
        seg(x0, y0, x1, y1, f"face ext. du mur ({'X' if abs(x1 - x0) < 1e-6 else 'Y'} {ftin(x0 if abs(x1 - x0) < 1e-6 else y0)})")
    if niveau == "SS":
        for m in RS.MURS_FONDATION:
            seg(*m["face_ext"], f"face ext. {m['id']}")
            seg(*m["face_int"], f"face int. {m['id']}")
            for oa, ob, nat in m.get("ouvertures", []):
                x0, y0, x1, y1 = m["face_ext"]
                c = (oa + ob) / 2
                if abs(y1 - y0) < 1e-6:
                    out.append(("X", c, y0 - 1, y0 + 1, f"axe de l'ouverture ({nat.split('«')[0].strip()[:28]})"))
                    out.append(("X", oa, y0 - 1, y0 + 1, f"arête de l'ouverture ({nat[:20]})"))
                    out.append(("X", ob, y0 - 1, y0 + 1, f"arête de l'ouverture ({nat[:20]})"))
                else:
                    out.append(("Y", c, x0 - 1, x0 + 1, f"axe de l'ouverture ({nat.split('«')[0].strip()[:28]})"))
                    out.append(("Y", oa, x0 - 1, x0 + 1, f"arête de l'ouverture ({nat[:20]})"))
                    out.append(("Y", ob, x0 - 1, x0 + 1, f"arête de l'ouverture ({nat[:20]})"))
        for p in RS.POUTRES:
            if p["niveau"] == "SS":
                seg(*p["axe"], f"axe de la poutre {p['id']}")
        for p in RS.POTEAUX:
            cx, cy = p["centre"]
            out.append(("X", cx, cy - 1, cy + 1, f"axe du poteau {p['id']}"))
            out.append(("Y", cy, cx - 1, cx + 1, f"axe du poteau {p['id']}"))
        for t in RS.SONOTUBES:
            cx, cy = t["centre"]
            out.append(("X", cx, cy - 1, cy + 1, f"axe du sonotube {t['id']}"))
            out.append(("Y", cy, cx - 1, cx + 1, f"axe du sonotube {t['id']}"))
    else:
        for p in RS.POTEAUX:
            if p["niveau"] == "RDC":
                cx, cy = p["centre"]
                out.append(("X", cx, cy - 1, cy + 1, f"axe du poteau {p['id']}"))
                out.append(("Y", cy, cx - 1, cx + 1, f"axe du poteau {p['id']}"))
        for t in RS.SONOTUBES:
            cx, cy = t["centre"]
            out.append(("X", cx, cy - 1, cy + 1, f"axe du sonotube {t['id']}"))
            out.append(("Y", cy, cx - 1, cx + 1, f"axe du sonotube {t['id']}"))
    for c in RI.CLOISONS:
        if c["niveau"] != niveau or c["epaisseur"] <= 0:
            continue
        x0, y0, x1, y1 = c["axe"]
        e = c["epaisseur"] / 2
        if abs(y1 - y0) < 1e-6:
            a, b = min(x0, x1), max(x0, x1)
            out += [("Y", y0, a, b, f"axe de {c['id']}"), ("Y", y0 - e, a, b, f"face −Y de {c['id']}"),
                    ("Y", y0 + e, a, b, f"face +Y de {c['id']}")]
        else:
            a, b = min(y0, y1), max(y0, y1)
            out += [("X", x0, a, b, f"axe de {c['id']}"), ("X", x0 - e, a, b, f"face −X de {c['id']}"),
                    ("X", x0 + e, a, b, f"face +X de {c['id']}")]
        # bouts de cloison : baies sans porte et fin des panneaux vitrés (ex. C-SS-09 : muret 36" + panneaux vitrés,
        # puis baie de 5'-0" sans porte ; c'est le repère des cotes 4'-0" et 5'-0" de la feuille 3)
        for cle, quoi in (("baies", "bord de la baie sans porte de"), ("vitre", "bout des panneaux vitrés de")):
            for u0, u1 in (c.get(cle) or []):
                for u in (u0, u1):
                    if abs(y1 - y0) < 1e-6:
                        out.append(("X", u, y0 - e, y0 + e, f"{quoi} {c['id']}"))
                    else:
                        out.append(("Y", u, x0 - e, x0 + e, f"{quoi} {c['id']}"))

    def rect(x0, y0, x1, y1, nom):
        seg(x0, y0, x0, y1, nom + " (bord −X)")
        seg(x1, y0, x1, y1, nom + " (bord +X)")
        seg(x0, y0, x1, y0, nom + " (bord −Y)")
        seg(x0, y1, x1, y1, nom + " (bord +Y)")

    px, py = P.PATIO["X"], P.PATIO["Y"]
    rect(px[0], py[0], px[1], py[1], "patio")
    cf = getattr(P, "CHAMBRE_FROIDE", None)
    if cf:            # mur de la chambre froide, sous la galerie avant : cotes 9'-8", 16'-4", 4'-10", 8'-2" des 2 feuilles
        rect(cf["X"][0], cf["Y"][0], cf["X"][1], cf["Y"][1], "chambre froide, face ext. du mur")
        if cf.get("interieur"):
            (xa, xb), (ya, yb) = cf["interieur"]
            rect(xa, ya, xb, yb, "chambre froide, face int. du mur")
    ch = P.CHEMINEE
    rect(ch["X"][0], ch["Y"][0], ch["X"][1], ch["Y"][1], "cheminée")
    cd = (P.RE.CHEMINEE.get("conduit_plan") if P.RE else None) or {}
    if cd.get("centre"):
        cx, cy = cd["centre"]
        out.append(("X", cx, cy - 30, cy + 1, "axe du conduit de la cheminée"))
    for e in (RI.ESCALIERS if RI else []):
        x0, y0, x1, y1 = e["volees"][0]["emprise"]
        rect(x0, y0, x1, y1, f"escalier {e['id']}")
    for a in list(getattr(RI, "APPAREILS", [])) + list(getattr(RI, "RANGEMENTS", [])):
        if a.get("niveau") == niveau and a.get("emprise"):
            rect(*a["emprise"], f"{a['id']}")
    for eq in (getattr(RS, "EQUIPEMENTS_TECHNIQUES", []) if niveau == "SS" else []):
        if eq.get("position") and "drain" in eq["nom"]:
            cx, cy = eq["position"]
            out.append(("X", cx, cy - 1, cy + 1, "centre du drain de plancher du garage"))
            out.append(("Y", cy, cx - 1, cx + 1, "centre du drain de plancher du garage"))
    for o in (RO.OUVERTURES if RO else []):
        if o["niveau"] != niveau or o.get("plan") is None:
            continue
        a, b = o["plan"]
        x0, y0, x1, y1 = o["mur"]
        if o["axe"] == "X":
            out.append(("X", (a + b) / 2, y0 - 1.5, y0 + 1.5, f"axe de {o['id']}"))
        else:
            out.append(("Y", (a + b) / 2, x0 - 1.5, x0 + 1.5, f"axe de {o['id']}"))
    return out


def rattacher_el(els, sens, pos, ligne):
    """Élément le plus proche du tic (sens de l'élément = perpendiculaire à la cote), qui passe près de la ligne :
    le tuple (sens, coord, a, b, nom), ou None."""
    best = None
    for el in els:
        s, c, a, b, nom = el
        if s != sens or abs(c - pos) > TOL:
            continue
        d_ext = 0.0 if a - 0.5 <= ligne <= b + 0.5 else min(abs(ligne - a), abs(ligne - b))
        cle = (abs(c - pos) + 0.02 * d_ext, nom)
        if best is None or cle < best[0]:
            best = (cle, el)
    return best[1] if best else None


def rattacher(els, sens, pos, ligne):
    el = rattacher_el(els, sens, pos, ligne)
    return (el[1], el[4]) if el else (None, None)


# Rattachements tranchés par le relevé (gel F4, releve_ecarts.md § 6) quand deux éléments de nos relevés sont à moins de
# 1/2" du tic : (niveau, texte, ligne arrondie au 1/10', bout « a » ou « b ») -> nom de l'élément.
FORCES = {
    ("SS", "6'-6\"", 23.3, "a"): "face int. MF-08",   # le 6'-6" part de la face intérieure de MF-08, pas de C-SS-01
}


def rattacher_cote(els, niveau, txt, vert, c0, pos, bout):
    """Élément visé par le tic « bout » (a ou b) d'une cote écrite : FORCES d'abord, sinon le plus proche."""
    sens = "Y" if vert else "X"
    nom = FORCES.get((niveau, txt, round(c0, 1), bout))
    if nom:
        for el in els:
            if el[0] == sens and el[4] == nom:
                return el
    return rattacher_el(els, sens, pos, c0)


# ------------------------------------------------------------------------------------------ cotes de l'original
def cotes_origine(niveau):
    """Cotes écrites de la vue (feuille 4 : RDC ; feuille 3 : SS), lues dans le PDF, plus les MANUELLES."""
    O, CO = _pdf()
    vue = O.RDC if niveau == "RDC" else O.SS
    return list(CO.cotes(vue)) + list(MANUELLES.get(niveau, []))


def interieure(vert, c0, a, b):
    from shapely.geometry import Point as _Pt, Polygon as _Pg
    mid = (c0, (a + b) / 2) if vert else ((a + b) / 2, c0)
    return _Pg(P.EMPRISE_RDC).buffer(-0.3).contains(_Pt(*mid))


def cotes_figees(niveau, chemin=JSON_FIGE):
    """Cotes de l'original figées dans cotes_origine.json (le générateur du 2D n'ouvre pas le PDF)."""
    with open(chemin, encoding="utf-8") as fh:
        return json.load(fh)[niveau]


def figer_json(dest=JSON_FIGE):
    data = {}
    for niv in ("RDC", "SS"):
        man = {id(t) for t in MANUELLES.get(niv, [])}
        lst = []
        for t in cotes_origine(niv):
            txt, vert, cu, cv, c0, a, b, val = t
            if val is None or a is None or abs(val * 12 - abs(b - a) * 12) > 12:
                continue
            lst.append(dict(txt=txt, vert=bool(vert), c0=round(c0, 4), a=round(min(a, b), 4), b=round(max(a, b), 4),
                            val=round(val, 6), interieur=interieure(vert, c0, a, b),
                            source="zoom (MANUELLES)" if id(t) in man else "cotes.py (tics)"))
        data[niv] = lst
    tmp = dest + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, dest)
    print(dest, {k: len(v) for k, v in data.items()})


def lire_cotes(niveau):
    """Cotes écrites de l'original rattachées à NOS éléments : liste de dict (txt, val, vert, c0, a, b, ca, cb, na, nb,
    interieur). ca/cb : coordonnées de nos éléments (None si non trouvés)."""
    els = elements(niveau)
    out = []
    for txt, vert, cu, cv, c0, a, b, val in cotes_origine(niveau):
        if val is None or a is None or abs(val * 12 - abs(b - a) * 12) > 12:
            continue
        ea = rattacher_cote(els, niveau, txt, vert, c0, a, "a")
        eb = rattacher_cote(els, niveau, txt, vert, c0, b, "b")
        ca, na = (ea[1], ea[4]) if ea else (None, None)
        cb, nb = (eb[1], eb[4]) if eb else (None, None)
        out.append(dict(txt=txt, val=val, vert=vert, c0=c0, a=a, b=b, ca=ca, cb=cb, na=na, nb=nb,
                        interieur=interieure(vert, c0, a, b)))
    return out


# ------------------------------------------------------------------------------------------ nos cotes (DXF)
def cotes_de_nos_feuilles(chemin):
    """Textes des cotes de NOS feuilles A-101 et A-102 (régions de l'espace objet du registre : 3000' par feuille,
    arrondi au plus près : le patio est à X négatif, dans la région de sa feuille)."""
    out = {"A-101": set(), "A-102": set()}
    if not os.path.exists(chemin):
        return out
    import ezdxf
    doc = ezdxf.readfile(chemin)
    for d in doc.modelspace().query("DIMENSION"):
        x = d.dxf.defpoint.x / 12
        t = (d.dxf.text or "").replace("≈", "").strip()
        k = int(round(x / 3000))
        nom = {1: "A-101", 2: "A-102"}.get(k)
        if nom:
            out[nom].add(t)
    return out


def normal(t):
    t = t.replace("''", '"').replace(" ", "")
    m = re.match(r"^(\d+)\"$", t)
    if m:
        v = int(m.group(1))
        return f"{v // 12}'-{v % 12}\"" if v >= 12 else f"{v}\""
    return t


def _empreinte():
    try:
        import empreinte_bungalow as EM
        src = os.path.abspath(args.sources)
        return EM.empreinte_sources(src) if os.path.normcase(src) != os.path.normcase(PROJET) else EM.empreinte_sources()
    except Exception as ex:                            # noqa: BLE001
        return f"(non calculée : {ex})"


def _maintenant():
    import time
    return time.strftime("%Y-%m-%d %H:%M")


def main():
    if args.figer:
        figer_json()
    nos = cotes_de_nos_feuilles(args.dxf)
    lignes = ["# Cotes écrites de l'original contre nos relevés (feuilles 3 et 4) — Règle 5", "",
              "Généré par `plans\\outils\\comparer_cotes_interieures.py` (lecture seule des relevés). Sources lues : "
              f"`{os.path.relpath(os.path.abspath(args.sources), PROJET) or '.'}` (projet). Faces : convention de "
              "l'original (faces extérieures de l'ossature ou du béton, faces ou axes des cloisons, axes des ouvertures, "
              "des poutres, des poteaux et des sonotubes), déduites des tics de chaque cote. **Plus de 1/4\" d'écart = "
              "écart de Règle 5 : la cote écrite prime, c'est notre relevé qu'il faudrait corriger** (fichiers de "
              "l'agent dao n° 2, non modifiés ici).", "",
              f"Empreinte des sources lues : **{_empreinte()}** (le {_maintenant()}).", "",
              f"Colonne « Chez nous » : la même valeur est-elle écrite sur NOTRE feuille (A-101 pour la feuille 3, A-102 "
              f"pour la feuille 4) dans `{os.path.relpath(os.path.abspath(args.dxf), PROJET)}` ?", ""]
    resume = []
    for feuille, niveau, notre in (("4", "RDC", "A-102"), ("3", "SS", "A-101")):
        els = elements(niveau)
        rangs = []
        for txt, vert, cu, cv, c0, a, b, val in cotes_origine(niveau):
            if val is None or a is None:
                continue
            sens = "Y" if vert else "X"                     # sens des éléments visés (perpendiculaires à la cote)
            if abs(val * 12 - abs(b - a) * 12) > 12:        # texte de légende attribué par erreur à une ligne de cote
                continue
            interieur = interieure(vert, c0, a, b)
            ea = rattacher_cote(els, niveau, txt, vert, c0, a, "a")
            eb = rattacher_cote(els, niveau, txt, vert, c0, b, "b")
            ca, na = (ea[1], ea[4]) if ea else (None, None)
            cb, nb = (eb[1], eb[4]) if eb else (None, None)
            if ca is None or cb is None:
                notre_v, ec, faces = None, None, f"{'Y' if vert else 'X'} {ftin(a)} → {ftin(b)} : " + \
                    ("élément non trouvé dans nos relevés" if ca is None and cb is None else
                     f"{na or '(rien dans nos relevés)'} → {nb or '(rien dans nos relevés)'}")
            else:
                notre_v = abs(cb - ca)
                ec = notre_v - val
                faces = f"{na} → {nb}"
                loin = [(n_, abs(c_ - t_)) for n_, c_, t_ in ((na, ca, a), (nb, cb, b)) if abs(c_ - t_) > 1 / 12]
                if loin:
                    faces += " — ⚠ tic à " + ", ".join(f"{ftin(d_)} de « {n_} »" for n_, d_ in loin) + \
                        " (l'original vise sans doute une face ou un bord que nos relevés n'ont pas)"
            present = normal(txt) in {normal(t) for t in nos[notre]}
            rangs.append((interieur, vert, c0, min(a, b), txt, faces, val, notre_v, ec, present))
        rangs.sort(key=lambda r: (not r[0], r[1], -r[2], r[3]))
        n_int = sum(1 for r in rangs if r[0])
        n_abs = sum(1 for r in rangs if not r[9])
        n_r5 = sum(1 for r in rangs if r[8] is not None and abs(r[8]) > 0.25 / 12 + 1e-9)
        resume.append((feuille, notre, len(rangs), n_int, n_abs, n_r5))
        lignes += [f"## Feuille {feuille} d'origine ({'plan du rez-de-chaussée' if niveau == 'RDC' else 'plan des fondations et du sous-sol'}) → notre {notre}", "",
                   "| Où | Valeur écrite | Faces visées (convention de l'original) | Notre valeur (relevés) | Écart | Chez nous |",
                   "|---|---|---|---|---|---|"]
        for interieur, vert, c0, a0, txt, faces, val, notre_v, ec, present in rangs:
            ou = ("intérieure" if interieur else "extérieure") + (f", ligne X {ftin(c0)}" if vert else f", ligne Y {ftin(c0)}")
            nv = ftin(notre_v) if notre_v is not None else "—"
            if ec is None:
                e = "—"
            elif abs(ec) > 0.25 / 12 + 1e-9:
                e = f"**{ecart_txt(ec)} (Règle 5)**"
            else:
                e = ecart_txt(ec) if abs(ec) >= 1 / 192 else "0\""
            lignes.append(f"| {ou} | {normal(txt)} | {faces} | {nv} | {e} | {'oui' if present else '**non**'} |")
        lignes.append("")
    lignes += ["## Résumé", "", "| Feuille d'origine | Notre feuille | Cotes écrites lues | Intérieures | Absentes chez nous | Écarts > 1/4\" |",
               "|---|---|---|---|---|---|"]
    for f, n, t, i, a_, r in resume:
        lignes.append(f"| {f} | {n} | {t} | {i} | {a_} | {r} |")
    lignes += ["", "Cotes sans tics retrouvés (hauteurs des légendes de niveau, étiquettes « 30\" » des portes, textes de "
               "note) : non comparées, sauf 6'-1\" et 2'-0\" de la cuisine (feuille 4), lues sur un zoom. Les écarts de "
               "ces tableaux ne corrigent rien : ils sont à trancher avant le gel F4."]
    dest = args.sortie
    with open(dest, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lignes) + "\n")
    print(dest)
    for r in resume:
        print(r)


if __name__ == "__main__":
    main()
