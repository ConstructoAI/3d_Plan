r"""PLANS EN PDF — standard de Sylvain (2026-09-28) : « TOUJOURS faire le plan PDF comme dans ce projet ».

Transforme un jeu de plans DXF (une présentation = une feuille) en UN PDF vectoriel de toutes les feuilles, comme le
jeu de l'escalier flottant (C:\Dev\Escalier_flottant_Blender\plans\escalier_plans.pdf, 2026-09-28) :
- une page par présentation, dans l'ordre des onglets (A-001 d'abord), au FORMAT RÉEL de la feuille (ARCH D 36" x 24"
  en général) et à l'échelle : il s'imprime à 100 % ;
- fond blanc, traits NOIRS aux épaisseurs de trait des calques, poché gris gardé, types de ligne rendus (tirets
  éclatés en segments), dans l'espace objet vu par les fenêtres comme dans l'espace papier (tableaux et légendes
  posés dans l'espace papier : pris en charge depuis le 2026-09-28 au soir) ; les calques de conflit (ECARTS :
  nuages, cercles) restent en COULEUR (rouge) ;
- texte CHERCHABLE et sélectionnable : chaque texte de la feuille (cartouche, notes, tableaux, cotes vues par les
  fenêtres) est posé, invisible, sous son tracé ;
- rendu REPRODUCTIBLE : le moteur d'ezdxf décale AU HASARD l'origine des motifs de hachure à chaque rendu
  (jiggle_origin) ; ce décalage est rendu FIXE (motifs_sans_hasard) : le même DXF donne le même dessin, quel que soit
  l'ordre de ses entités (2026-09-28 soir) ;
- métadonnées : titre, « Préparé par une IA (Claude) », « à valider et à sceller par un professionnel » ;
- n'écrase jamais un PDF ouvert dans une application : il écrit _v2 à côté.

Origine : fonctions de plans\plans_escalier.py (agent DAO, projet Escalier flottant, 2026-09-28), rendues
indépendantes du projet : motifs des types de ligne et format des feuilles lus dans le DXF lui-même.

Usage : python plans_pdf.py <jeu.dxf> [--sortie jeu.pdf] [--feuilles A-001,A-100] [--titre "Projet - jeu de plans 2D"]
                           [--sujet "..."] [--calques-couleur ECARTS] [--processus 3]
En module : from plans_pdf import pdf_jeu ; chemin, n_pages, n_textes = pdf_jeu(dxf, feuilles, chemin_pdf, titre=...)
Dans le générateur du jeu 2D, l'appeler APRÈS l'écriture du DXF final (même empreinte que le DWG).
Durée : environ 2 min pour 7 feuilles ARCH D (3 processus) ; jusqu'à 3 fois plus si Blender tourne à côté.
"""
import argparse
import json
import math
import os
import sys
import time

import ezdxf

ARCH_D = (36.0, 24.0)                                  # format par défaut (pouces) si la présentation n'en déclare pas
SUJET = "Document de travail : à valider et à sceller par un professionnel"


def chemin_libre(path):
    """Ne jamais écraser un fichier ouvert (verrouillé) dans une application : _v2, _v3..."""
    base, ext = os.path.splitext(path)
    cand, k = path, 1
    while os.path.exists(cand):
        try:
            with open(cand, "r+b"):
                return cand
        except OSError:
            print(f"  {os.path.basename(cand)} : ouvert dans une application -> à côté")
        k += 1
        cand = f"{base}_v{k}{ext}"
    return cand


def motifs_types_de_ligne(doc):
    """{NOM: [longueur totale, élément 1, élément 2...]} lus dans la table LTYPE (codes 40 et 49 : trait > 0, espace < 0,
    point = 0), comme les motifs d'acad.lin."""
    out = {}
    for lt in doc.linetypes:
        tags = lt.pattern_tags.tags if lt.pattern_tags is not None else None
        if not tags:
            continue
        elems = [float(t.value) for t in tags if t.code == 49]
        tot = [float(t.value) for t in tags if t.code == 40]
        if elems and any(abs(v) > 1e-12 for v in elems):
            out[lt.dxf.name.upper()] = [tot[0] if tot else sum(abs(v) for v in elems)] + elems
    return out


def eclater_tirets(doc):
    """PDF SEULEMENT (copie en mémoire) : le rendu ezdxf des fenêtres ignore les types de ligne ; on remplace les
    lignes, polylignes, arcs et cercles à motif par des segments continus, dans l'espace objet ET dans l'espace papier
    des présentations (tableaux, légendes et leurs échantillons en tirets posés dans l'espace papier ; tirets = motif
    x $LTSCALE x échelle de l'entité, comme dans AutoCAD). Ajout du 2026-09-28 au soir (escalier : tableaux passés
    dans l'espace papier) ; sans effet sur un jeu dont l'espace papier n'a aucun trait à motif."""
    espaces = [doc.modelspace()] + [doc.layouts.get(nom) for nom in doc.layout_names() if nom.lower() != "model"]
    return sum(_eclater_tirets_espace(doc, esp) for esp in espaces)


def _eclater_tirets_espace(doc, msp):
    motifs = motifs_types_de_ligne(doc)
    lts = doc.header.get("$LTSCALE", 1.0)
    n = 0
    for e in list(msp):
        t = e.dxftype()
        if t not in ("LINE", "LWPOLYLINE", "ARC", "CIRCLE"):
            continue
        lt = e.dxf.get("linetype", "BYLAYER").upper()
        if lt == "BYLAYER":
            try:
                lt = doc.layers.get(e.dxf.layer).dxf.linetype.upper()
            except Exception:                                  # noqa: BLE001
                continue
        pat = motifs.get(lt)
        if not pat:
            continue
        if t == "LINE":
            pts = [(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)]
        elif t in ("ARC", "CIRCLE"):
            c, r = e.dxf.center, e.dxf.radius
            a0, a1 = (e.dxf.start_angle, e.dxf.end_angle) if t == "ARC" else (0.0, 360.0)
            if a1 < a0:
                a1 += 360.0
            k = max(16, int(math.radians(a1 - a0) * r / 1.0))
            pts = [(c.x + r * math.cos(math.radians(a0 + (a1 - a0) * i / k)),
                    c.y + r * math.sin(math.radians(a0 + (a1 - a0) * i / k))) for i in range(k + 1)]
        else:
            pts = [(x, y) for x, y in e.get_points("xy")]
            if e.closed:
                pts.append(pts[0])
        kk = lts * e.dxf.get("ltscale", 1.0)
        elems = [v * kk for v in pat[1:]]
        if sum(abs(v) for v in elems) < 1e-9:                 # motif de longueur nulle (points seuls) : laissé tel quel
            continue
        att = {"layer": e.dxf.layer, "color": e.dxf.get("color", 256), "linetype": "Continuous"}
        if e.dxf.hasattr("lineweight"):
            att["lineweight"] = e.dxf.lineweight
        # Un POINT du motif (élément nul) est dessiné comme un trait de 0,02 x échelle, mais n'occupe AUCUNE longueur du
        # motif, comme dans AutoCAD (corrigé le 2026-09-28 au soir : « or 0.02 * kk » faisait dériver les tirets le long
        # des lignes en tirets-points, et le PDF de l'outil différait de celui du générateur de l'escalier).
        i, reste = 0, abs(elems[0])
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            ls = math.hypot(x1 - x0, y1 - y0)
            if ls < 1e-9:
                continue
            ux, uy = (x1 - x0) / ls, (y1 - y0) / ls
            s = 0.0
            while s < ls - 1e-9:
                pas = min(reste, ls - s)
                if elems[i] > 0:
                    msp.add_line((x0 + ux * s, y0 + uy * s), (x0 + ux * (s + pas), y0 + uy * (s + pas)), dxfattribs=att)
                elif elems[i] == 0:
                    msp.add_line((x0 + ux * s, y0 + uy * s), (x0 + ux * (s + 0.02 * kk), y0 + uy * (s + 0.02 * kk)),
                                 dxfattribs=att)
                s += pas
                reste -= pas
                if reste <= 1e-9:
                    i = (i + 1) % len(elems)
                    reste = abs(elems[i])
        msp.delete_entity(e)
        n += 1
    return n


def motifs_sans_hasard():
    """Rendu REPRODUCTIBLE des hachures à motif : le moteur de rendu d'ezdxf décale l'origine de chaque motif d'une
    quantité TIRÉE AU HASARD (jiggle_origin, 0,0003 à 0,001 du pas), pour éviter les coins ; deux rendus du même dessin
    différaient donc au bord des hachures, et selon l'ordre des entités. Décalage FIXE, au milieu de sa plage : même
    DXF -> même PDF, quel que soit l'ordre des entités (2026-09-28 au soir). Fonction privée d'ezdxf 1.4.4 ; sinon,
    graine fixe."""
    try:
        from ezdxf.render import hatching as _hatching
        if hasattr(_hatching, "_jiggle_factor"):
            _hatching._jiggle_factor = lambda: 0.00065
            return
    except Exception:                                          # noqa: BLE001
        pass
    import random
    random.seed(0)


def format_feuille(lay):
    """(largeur, hauteur) de la feuille en mm et facteur « unité de l'espace papier -> mm », lus dans la présentation."""
    from ezdxf.addons.drawing import layout
    try:
        pg = layout.Page.from_dxf_layout(lay)
        (x0, y0), (x1, y1) = lay.get_paper_limits()
        if pg.width > 0 and pg.height > 0 and x1 > x0:
            fx = pg.width_in_mm / (x1 - x0)
            return pg.width_in_mm, pg.height_in_mm, fx
    except Exception:                                          # noqa: BLE001
        pass
    return ARCH_D[0] * 25.4, ARCH_D[1] * 25.4, 25.4


def _pdf_une_page(args):
    """Une feuille en PDF vectoriel (moteur PyMuPDF d'ezdxf) : fond blanc, tout en noir sauf les calques de conflit,
    poché gris conservé, épaisseurs de trait absolues. Rend (octets du PDF, textes à poser)."""
    dxf_path, nom, calques_couleur = args
    from ezdxf.addons.drawing import Frontend, RenderContext, pymupdf, layout
    from ezdxf.addons.drawing.config import Configuration, ColorPolicy, BackgroundPolicy, LineweightPolicy
    doc = ezdxf.readfile(dxf_path)
    eclater_tirets(doc)
    garder = {c.upper() for c in calques_couleur}
    for la in doc.layers:
        if la.dxf.name.upper() not in garder:                  # nuages et cercles de conflit : en couleur, même imprimés
            la.dxf.color = 7
    for e in doc.modelspace():
        if e.dxftype() == "HATCH":                             # poché : gris gardé
            continue
        if e.dxf.hasattr("color") and e.dxf.color not in (0, 256) and e.dxf.layer.upper() not in garder:
            e.dxf.color = 256
    for ds in doc.dimstyles:
        for k in ("dimclrd", "dimclre", "dimclrt"):
            try:
                setattr(ds.dxf, k, 256)
            except Exception:                                  # noqa: BLE001
                pass
    lay = doc.layouts.get(nom)
    for e in lay:                                              # espace papier : comme l'espace objet (poché gris gardé)
        if e.dxftype() not in ("VIEWPORT", "HATCH") and e.dxf.hasattr("color") and e.dxf.color not in (0, 256) \
                and e.dxf.layer.upper() not in garder:
            e.dxf.color = 256
    cfg = Configuration(color_policy=ColorPolicy.COLOR, background_policy=BackgroundPolicy.WHITE,
                        lineweight_policy=LineweightPolicy.ABSOLUTE, lineweight_scaling=1.0)
    ctx = RenderContext(doc)
    be = pymupdf.PyMuPdfBackend()
    motifs_sans_hasard()
    Frontend(ctx, be, config=cfg).draw_layout(lay, finalize=True)
    l_mm, h_mm, fx = format_feuille(lay)
    page = layout.Page(l_mm, h_mm, layout.Units.mm, margins=layout.Margins.all(0))
    st = layout.Settings(fit_page=False, scale=fx)            # 1 unité de l'espace papier = fx mm dans le PDF
    return be.get_pdf_bytes(page, settings=st), textes_pdf(doc, lay, fx / 25.4)


def textes_pdf(doc, lay, pouces_par_unite=1.0):
    """Textes de la présentation (espace papier) et de l'espace objet vu par ses fenêtres, pour un calque de texte
    INVISIBLE dans le PDF. Rend [(texte, x_po, y_po, hauteur_po, angle, h_align, v_align)] en pouces papier."""
    out = []
    u = pouces_par_unite

    def lire(e):
        """(texte, point d'ancrage, hauteur, angle, h_align 0/1/2, v_align 0..3) d'un TEXT ou d'un MTEXT."""
        if e.dxftype() == "TEXT":
            ha, va = e.dxf.get("halign", 0), e.dxf.get("valign", 0)
            p = e.dxf.align_point if (ha or va) else e.dxf.insert
            return e.dxf.text, (p[0], p[1]), e.dxf.height, e.dxf.get("rotation", 0.0), min(ha, 2), va
        if e.dxftype() == "MTEXT":
            ap = e.dxf.get("attachment_point", 1)             # 1..9 : haut, milieu, bas x gauche, centre, droite
            ha, va = (ap - 1) % 3, {0: 3, 1: 2, 2: 1}[(ap - 1) // 3]
            # get_rotation() : rotation OU direction du texte (un MTEXT déplacé par ezdxf, p. ex. dans le bloc d'une
            # cote déplacée, porte sa direction et plus sa rotation : lu par dxf.rotation, il sortait horizontal)
            return e.plain_text(), (e.dxf.insert[0], e.dxf.insert[1]), e.dxf.char_height, e.get_rotation(), ha, va
        return None

    for e in lay:                                           # espace papier : cartouche, titres, tableaux
        if e.dxftype() in ("TEXT", "MTEXT"):
            r = lire(e)
            if r and r[0].strip():
                out.append((r[0], r[1][0] * u, r[1][1] * u, r[2] * u, r[3], r[4], r[5]))
    vps = []                                               # fenêtres : (échelle, centre objet, centre papier, demi-tailles)
    for vp in lay.query("VIEWPORT"):
        if vp.dxf.id == 1 or vp.dxf.view_height <= 0:
            continue
        k = vp.dxf.height / vp.dxf.view_height
        vps.append((k, vp.dxf.view_center_point[0], vp.dxf.view_center_point[1], vp.dxf.center[0], vp.dxf.center[1],
                    vp.dxf.width / 2 / k, vp.dxf.height / 2 / k))

    def fenetre_de(x, y, marge=1.0):
        for f in vps:
            if abs(x - f[1]) <= f[5] * marge and abs(y - f[2]) <= f[6] * marge:
                return f
        return None

    for e in doc.modelspace():
        t = e.dxftype()
        if t in ("TEXT", "MTEXT"):
            sous = [e]
        elif t == "DIMENSION":
            p = e.dxf.defpoint
            if fenetre_de(p[0], p[1], 1.3) is None:          # cote d'une autre feuille : ignorée sans la développer
                continue
            try:
                sous = [v for v in e.virtual_entities() if v.dxftype() in ("TEXT", "MTEXT")]
            except Exception:                               # noqa: BLE001
                continue
        else:
            continue
        for tx in sous:
            r = lire(tx)
            if not r or not r[0].strip():
                continue
            (x, y) = r[1]
            f = fenetre_de(x, y)
            if f is None:
                continue
            k, cx, cy, px, py = f[:5]
            out.append((r[0], (px + (x - cx) * k) * u, (py + (y - cy) * k) * u, r[2] * k * u, r[3], r[4], r[5]))
    return out


def poser_textes_invisibles(page, textes):
    """Ajoute les textes (pouces papier) à la page PDF en mode invisible (render_mode 3), police Helvetica."""
    import fitz
    H = page.rect.height
    n = 0
    for s, x, y, h, ang, ha, va in textes:
        s = s.replace("\n", " ").replace("≈", "~").replace("≥", ">=").replace("≤", "<=")
        taille = max(h * 72.0, 1.0)
        w = fitz.get_text_length(s, fontname="helv", fontsize=taille) / 72.0
        dx = -w * (0.0, 0.5, 1.0)[ha]
        dy = -h * {0: 0.0, 1: 0.0, 2: 0.5, 3: 1.0}.get(va, 0.0)
        a = math.radians(ang)
        bx = x + dx * math.cos(a) - dy * math.sin(a)       # début de la ligne de base (pouces papier)
        by = y + dx * math.sin(a) + dy * math.cos(a)
        rot = int(round(ang / 90.0)) % 4 * 90
        try:
            page.insert_text(fitz.Point(bx * 72.0, H - by * 72.0), s, fontsize=taille, fontname="helv",
                             render_mode=3, rotate=rot)
            n += 1
        except Exception:                                   # noqa: BLE001
            pass
    return n


def feuilles_du_jeu(dxf_path):
    """Présentations dans l'ordre des onglets (l'espace objet exclu)."""
    doc = ezdxf.readfile(dxf_path)
    return [n for n in doc.layouts.names_in_taborder() if n.lower() != "model"]


def pdf_jeu(dxf_path, feuilles=None, chemin_pdf=None, titre=None, sujet=SUJET, calques_couleur=("ECARTS",),
            n_proc=3):
    """UN PDF de toutes les feuilles. Rend (chemin écrit, nombre de pages, nombre de textes cherchables)."""
    import fitz
    from concurrent.futures import ProcessPoolExecutor
    feuilles = list(feuilles or feuilles_du_jeu(dxf_path))
    chemin_pdf = chemin_pdf or os.path.splitext(dxf_path)[0] + ".pdf"
    taches = [(dxf_path, n, tuple(calques_couleur)) for n in feuilles]
    if n_proc > 1 and len(taches) > 1:
        with ProcessPoolExecutor(max_workers=min(n_proc, len(taches))) as ex:
            pages = list(ex.map(_pdf_une_page, taches))
    else:
        pages = [_pdf_une_page(t) for t in taches]
    out = fitz.open()
    n_txt = 0
    for b, textes in pages:
        src = fitz.open("pdf", b)
        out.insert_pdf(src)
        n_txt += poser_textes_invisibles(out[-1], textes)
    titre = titre or os.path.splitext(os.path.basename(dxf_path))[0] + " - jeu de plans 2D"
    out.set_metadata({"title": titre, "author": "Préparé par une IA (Claude)", "subject": sujet,
                      "creator": "ezdxf + PyMuPDF"})         # aucun nom de script : un PDF de plans va au client
    chemin = chemin_libre(chemin_pdf)
    out.save(chemin, garbage=3, deflate=True)
    return chemin, out.page_count, n_txt


def controler_pdf(chemin, feuilles, dxf_path):
    """Relit le PDF : une page par feuille, au format de sa présentation, et du texte cherchable sur chaque page."""
    import fitz
    doc = ezdxf.readfile(dxf_path)
    pdf = fitz.open(chemin)
    defauts, pages = [], []
    if pdf.page_count != len(feuilles):
        defauts.append(f"{pdf.page_count} pages pour {len(feuilles)} feuilles")
    for i, nom in enumerate(feuilles[:pdf.page_count]):
        pg = pdf[i]
        l_mm, h_mm, _ = format_feuille(doc.layouts.get(nom))
        l_po, h_po = pg.rect.width / 72.0, pg.rect.height / 72.0
        mots = len(pg.get_text("words"))
        pages.append({"feuille": nom, "format_po": [round(l_po, 2), round(h_po, 2)], "mots": mots})
        if abs(l_po - l_mm / 25.4) > 0.05 or abs(h_po - h_mm / 25.4) > 0.05:
            defauts.append(f"{nom} : page de {l_po:.2f} x {h_po:.2f} po au lieu de {l_mm / 25.4:.2f} x {h_mm / 25.4:.2f}")
        if mots == 0:
            defauts.append(f"{nom} : aucun texte cherchable")
    return {"pages": pages, "defauts": defauts}


def main():
    ap = argparse.ArgumentParser(description="Jeu de plans DXF -> UN PDF vectoriel, noir sur blanc, cherchable.")
    ap.add_argument("dxf")
    ap.add_argument("--sortie", help="PDF à écrire (défaut : même nom que le DXF)")
    ap.add_argument("--feuilles", help="présentations, séparées par des virgules (défaut : toutes, ordre des onglets)")
    ap.add_argument("--titre")
    ap.add_argument("--sujet", default=SUJET)
    ap.add_argument("--calques-couleur", default="ECARTS", help="calques gardés en couleur (virgules)")
    ap.add_argument("--processus", type=int, default=3)
    a = ap.parse_args()
    t0 = time.time()
    feuilles = [f.strip() for f in a.feuilles.split(",")] if a.feuilles else feuilles_du_jeu(a.dxf)
    chemin, n_pages, n_txt = pdf_jeu(a.dxf, feuilles, a.sortie, a.titre, a.sujet,
                                     [c.strip() for c in a.calques_couleur.split(",") if c.strip()], a.processus)
    ctl = controler_pdf(chemin, feuilles, a.dxf)
    duree = time.time() - t0
    print(f"PDF : {chemin}  ({n_pages} pages, {os.path.getsize(chemin) / 1e6:.2f} Mo, {n_txt} textes cherchables, "
          f"{duree:.0f} s)")
    for p in ctl["pages"]:
        print(f"  {p['feuille']:<10} {p['format_po'][0]:g} x {p['format_po'][1]:g} po, {p['mots']} mots cherchables")
    for d in ctl["defauts"]:
        print("  DÉFAUT :", d)
    print(("PLANS_PDF_OK " if not ctl["defauts"] else "PLANS_PDF_DEFAUTS ") + json.dumps(
        {"pdf": chemin, "pages": n_pages, "textes": n_txt, "defauts": len(ctl["defauts"]), "duree_s": round(duree)},
        ensure_ascii=False))
    return 0 if not ctl["defauts"] else 1


if __name__ == "__main__":
    sys.exit(main())
