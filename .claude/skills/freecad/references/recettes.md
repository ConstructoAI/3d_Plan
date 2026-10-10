# Recettes FreeCAD — code vérifié

Extraits tirés d'une session où ils ont réellement tourné (FreeCAD 1.1.2). Unités : **millimètres**, **degrés**.

Modèle de référence complet : `C:\Dev\freecad-mcp\maison\`.

---

## Squelette d'un script

```python
# -*- coding: utf-8 -*-
import FreeCAD as App
import Draft, Arch
from FreeCAD import Vector, Rotation

doc = App.ActiveDocument or App.newDocument("projet")

# ... construction ...

doc.recompute()

# bilan chiffre : indispensable, un script peut reussir en produisant du faux
murs = [o for o in doc.Objects if getattr(o, "IfcType", "") == "Wall"]
invalides = [o.Label for o in doc.Objects
             if getattr(o, "Shape", None) and not o.Shape.isNull()
             and not o.Shape.isValid()]
print(f"murs {len(murs)} | invalides : {invalides or 'aucun'}")
```

---

## Murs et dalles

```python
def mur(p1, p2, ep, z, h, nom):
    ligne = Draft.make_line(Vector(p1[0], p1[1], z), Vector(p2[0], p2[1], z))
    ligne.Label = "axe_" + nom                 # a masquer dans les vues
    w = Arch.makeWall(ligne, width=ep, height=h, align="Center")
    w.Label = nom
    return w

def dalle(x, y, lx, ly, z, ep, nom):
    # Part::Box et non makeStructure nu : origine au coin minimum, previsible
    b = doc.addObject("Part::Box", "boite_" + nom)
    b.Length, b.Width, b.Height = lx, ly, ep
    b.Placement.Base = Vector(x, y, z)
    s = Arch.makeStructure(b)
    s.Label = nom
    s.IfcType = "Slab"
    return s
```

Épaisseurs usuelles au Québec : extérieurs **250 mm** (2×6 + parement), cloisons **100 mm**, hauteur libre **2600 mm**.

**Dalle : dépend du bâtiment**, ne pas prendre un chiffre par défaut. Plancher de maison ≈ 200 mm ; **garage détaché ou remise : 100 à 150 mm**. Appliquer 200 à un garage gonfle la commande de béton d'environ un tiers. En cas de doute, **le demander**, et si l'on tranche seul, l'annoncer explicitement dans le bilan.

Regroupement BIM :

```python
rdc = Arch.makeFloor(objets_rdc);   rdc.Label = "Rez-de-chaussee"
et  = Arch.makeFloor(objets_etage); et.Label  = "Etage"
bat = Arch.makeBuilding([rdc, et]); bat.Label = "Maison"
```

---

## Toiture à 4 versants

```python
contour = Draft.make_rectangle(LARG, PROF)
contour.Label = "Contour_toit"
contour.Placement.Base = Vector(0, 0, Z_HAUT_MURS)
doc.recompute()

toit = Arch.makeRoof(
    contour, facenr=0,
    angles=[30.0] * 4,          # ~7/12, adapte a la neige quebecoise
    run=[PROF / 2.0] * 4,       # croupes sur les 4 cotes
    idrel=[-1] * 4,
    thickness=[250.0] * 4,
    overhang=[600.0] * 4,       # debord ~2'
)
```

**Masquer `Contour_toit` ensuite** : c'est une face pleine qui couvre tout le bâtiment en vue de dessus.

---

## Toiture à deux versants (pignon)

Le toit le plus courant en résidentiel québécois. Même fonction, mais les arêtes
**perpendiculaires au faîtage** reçoivent `angle=90, run=0` : elles deviennent
verticales, ce qui crée les pignons.

Paramètres relevés sur un modèle qui fonctionne (garage 24′ × 20′, pente 30°,
débord 2′, faîtage parallèle au côté de 24′) :

```python
toit = Arch.makeRoof(
    contour, facenr=0,
    angles=[90.0, 30.0, 90.0, 30.0],      # 90 = pignon, 30 = versant
    run=[0.0, 3048.0, 0.0, 3048.0],       # run = demi-portee sous les versants
    idrel=[-1] * 4,
    thickness=[250.0] * 4,
    overhang=[609.6] * 4,                 # 2' sur les 4 cotes
)
```

⚠️ **L'ordre des arêtes du rectangle Draft n'est pas garanti.** Ne pas recopier
`[90, 30, 90, 30]` à l'aveugle : sonder d'abord quelles arêtes sont
perpendiculaires au faîtage voulu.

```python
for i, e in enumerate(contour.Shape.Edges):
    d = e.Vertexes[1].Point - e.Vertexes[0].Point
    print(i, "selon X" if abs(d.x) > abs(d.y) else "selon Y", f"{e.Length:.0f} mm")
```

Contrôle : la hauteur du faîtage vaut `demi-portee × tan(pente)` au-dessus du
haut des murs, **plus** l'épaisseur divisée par `cos(pente)` — l'épaisseur du
toit se mesure **perpendiculairement à la pente**, pas verticalement. Oublier
ce terme fait échouer toute prédiction de bbox.

---

## Mur pignon

`Arch.makeWall` ne produit que des murs rectangulaires : rien ne remplit le
triangle sous les versants. Construire le solide, puis l'habiller en BIM.

```python
import Part

def pignon(nom, pts, y, ep, ):
    """pts : sommets du triangle dans le plan XZ, en coordonnees modele."""
    profil = Part.makePolygon([App.Vector(x, y, z) for x, z in pts]
                              + [App.Vector(pts[0][0], y, pts[0][1])])
    solide = doc.addObject("Part::Feature", "solide_" + nom)
    solide.Shape = Part.Face(profil).extrude(App.Vector(0, ep, 0))
    m = Arch.makeStructure(solide)
    m.Label = nom
    m.IfcType = "Wall"            # compte alors dans les metres de murs
    return m

# exemple : pignon de 6096 mm de portee, haut des murs 2438, faitage 4198
pignon("Pignon_avant",
       [(0, 2438), (6096, 2438), (3048, 4198)],
       y=0, ep=250)
```

---

## Angles de murs — le piège de l'encoche

Tracer les quatre axes de mur sur les coins du rectangle laisse une **encoche
de `ep/2 × ep/2`** à chaque angle (125 × 125 mm pour des murs de 250). Aucune
erreur, volumes plausibles, défaut visible seulement à l'œil sur une capture.

Deux murs **filants** sur toute la longueur, deux murs **insérés** entre eux :

```python
# murs lateraux filants sur toute la profondeur
mur((0, 0), (0, PROF), EP, z, h, "Mur_Ouest")
mur((LARG, 0), (LARG, PROF), EP, z, h, "Mur_Est")
# murs d'extremite inseres, retraits d'une demi-epaisseur de chaque cote
mur((EP / 2, 0), (LARG - EP / 2, 0), EP, z, h, "Mur_Sud")
mur((EP / 2, PROF), (LARG - EP / 2, PROF), EP, z, h, "Mur_Nord")
```

Bénéfice annexe : plus aucun recouvrement, donc les volumes s'additionnent sans
double comptage. Contrôle : comparer la somme des volumes à celui de l'union
booléenne — l'écart doit être nul.

```python
u = solides[0].Shape
for s in solides[1:]:
    u = u.fuse(s.Shape)
somme = sum(s.Shape.Volume for s in solides)
print(f"somme {somme/1e9:.3f} | union {u.Volume/1e9:.3f} m3")
```

---

## Menuiseries centrées dans le mur

```python
def ouverture(nom, mur, axe, pos, fixe, z, larg, haut, preset="Open 2-pane"):
    """axe : 'X' si le mur court selon X, 'Y' sinon.
    pos  : abscisse de depart le long du mur.
    fixe : coordonnee constante de l'axe du mur.
    z    : altitude d'allege (absolue)."""
    demi = 100.0                       # menuiserie = 200 mm de profondeur
    if axe == "X":
        rot = Rotation(Vector(1, 0, 0), 90)
        base = Vector(pos, fixe - demi, z)
    else:
        rot = Rotation(Vector(0, 0, 1), 90).multiply(Rotation(Vector(1, 0, 0), 90))
        base = Vector(fixe + demi, pos, z)

    w = Arch.makeWindowPreset(preset, width=larg, height=haut,
                              h1=100, h2=100, h3=100, w1=100, w2=100,
                              o1=0, o2=100,
                              placement=App.Placement(base, rot))
    w.Label = nom
    w.Hosts = [mur]                    # declenche le percement
    return w
```

Toujours valider le preset contre l'instance :

```python
assert preset in set(Arch.WindowPresets), f"preset absent : {preset}"
```

Contrôle du percement : un mur percé a bien plus de 6 faces (18 pour un mur à 3 ouvertures).

---

## Vues par niveau (pilotage de la visibilité)

```python
CONTENEURS = ("App::GeometryPython", "App::DocumentObjectGroup", "App::Part")
Z_PLAFOND_BAS, Z_PLANCHER_HAUT = 2500.0, 2750.0   # deux seuils distincts

conteneurs = [o for o in doc.Objects if o.TypeId in CONTENEURS]
feuilles   = [o for o in doc.Objects
              if hasattr(o, "ViewObject") and o.TypeId not in CONTENEURS]

for c in conteneurs:                       # 1) conteneurs ouverts d'abord
    c.ViewObject.Visibility = True

for o in feuilles:                         # 2) feuilles ensuite : elles gagnent
    z = o.Shape.BoundBox.ZMin if (o.Shape and not o.Shape.isNull()) else None
    if z is None:
        continue
    o.ViewObject.Visibility = (z >= Z_PLANCHER_HAUT) if niveau == "haut" \
                              else (z < Z_PLAFOND_BAS)

for o in feuilles:                         # 3) geometrie d'appui toujours masquee
    if o.Label.startswith("axe_") or o.Label == "Contour_toit":
        o.ViewObject.Visibility = False

doc.recompute()
Gui.updateGui()
```

---

## Mise en plan cotée

```python
import time, TechDraw, TechDrawGui
import FreeCADGui as Gui

def attendre_geometrie(v, secondes=240):
    """Le HLR est asynchrone. Coter une vue vide fait planter FreeCAD."""
    fin = time.time() + secondes
    while time.time() < fin:
        Gui.updateGui()
        try:
            if v.getVisibleEdges():
                return True
        except Exception:
            pass
        time.sleep(0.15)
    return False

def vue(page, nom, sources, direction, x, y, echelle=0.02):
    v = doc.addObject("TechDraw::DrawViewPart", nom)
    page.addView(v)
    v.Source = sources
    v.Direction = App.Vector(*direction)      # (0,0,1) plan | (0,-1,0) facade sud
    v.ScaleType = "Custom"
    v.Scale = echelle                          # 0.02 = 1:50
    v.X, v.Y = x, y
    v.Perspective = False
    doc.recompute()
    if not attendre_geometrie(v):
        raise RuntimeError(f"{nom} : pas de geometrie apres attente du HLR")
    return v

def cote(page, v, pts, typ, pa, pb, dx, dy, nom, tol=400.0):
    """pts = carte_sommets(v, sources) ; pa/pb = points MODELE cibles."""
    def proche(a, b):
        best, bd = None, None
        for i, (x, y) in pts.items():
            d = (x - a) ** 2 + (y - b) ** 2
            if bd is None or d < bd:
                bd, best = d, i
        return best if (bd is not None and bd <= tol * tol) else None

    ia, ib = proche(*pa), proche(*pb)
    if ia is None or ib is None:
        print(f"   !! {nom} : sommet introuvable")
        return None
    d = doc.addObject("TechDraw::DrawViewDimension", "Dim")
    page.addView(d)
    d.References2D = [(v, f"Vertex{ia}"), (v, f"Vertex{ib}")]
    d.Type = typ                               # DistanceX | DistanceY | Distance
    d.X, d.Y = dx, dy
    d.Label = nom
    return d
```

`carte_sommets` : voir `pieges.md` § D3.

**Ne pas utiliser** `TechDraw.makeDistanceDim` ni `makeDistanceDim3d` : elles tracent à 1:1 et ignorent l'échelle de la vue (§ D2).

Contrôle final, à faire systématiquement :

```python
for d in [o for o in doc.Objects if o.TypeId == "TechDraw::DrawViewDimension"]:
    print(f"{d.Label:<24} {d.getRawValue():8.0f} mm")   # getRawValue, pas autre chose
```

Et vérifier que la planche n'est pas hors échelle :

```python
coords = []
for dd in re.findall(r'\sd="([^"]+)"', open(svg, encoding="utf-8").read()):
    coords += [abs(float(x)) for x in re.findall(r"[-+]?\d+\.?\d*", dd)]
assert max(coords) < 6000, "planche hors echelle"   # A3 = 4200 unites de large
```

---

## Regarder une planche — ne pas perdre de temps sur la fenêtre

Piège coûteux : vouloir capturer la planche depuis la fenêtre FreeCAD. La
sous-fenêtre MDI se maximise séparément de la fenêtre principale, celle-ci peut
déborder de l'écran, et une capture ne saisit que la partie visible. **Passer par
un export, pas par l'écran.**

```python
import TechDrawGui
TechDrawGui.exportPageAsSvg(page, r"...\planche.svg")   # rendu fidele
TechDrawGui.exportPageAsPdf(page, r"...\planche.pdf")   # livrable
```

Le SVG est ensuite **lisible et vérifiable en texte** : valeurs de cotes, échelle,
contenu. C'est plus fiable qu'un examen visuel.

```python
import re
txt = open(svg, encoding="utf-8", errors="replace").read()
print("valeurs cotees :", re.findall(r">\s*([0-9]{3,6})\s*<", txt))
```

Attention : ce relevé attrape aussi les repères du cadre ISO 5457 (100 à 500).
Recouper avec `getRawValue()` sur chaque cotation, qui est la source sûre.

Un PDF anormalement lourd (centaines de Ko pour une planche simple) est le signe
d'une géométrie hors échelle — voir `pieges.md` § D2. Une planche correcte à
1:50 pèse une dizaine de Ko.

---

## Enregistrement et exports

```python
doc.saveAs(r"C:\<dossier_projet>\projet.FCStd")   # chemin a adapter

solides = [o for o in doc.Objects
           if getattr(o, "Shape", None) and not o.Shape.isNull() and o.Shape.Solids]

for ext in ("step", "glb", "ifc"):
    mod = App.getExportType(ext)
    if isinstance(mod, (list, tuple)):
        mod = mod[0] if mod else None
    if mod:
        __import__(mod).export(solides, f"projet.{ext}")
```

`.glb` est le format à viser pour un affichage web (three.js / react-three-fiber).

---

## Quantités

```python
for o in doc.Objects:
    if getattr(o, "IfcType", "") == "Wall" and o.Shape and not o.Shape.isNull():
        print(f"{o.Label:<22} {o.Shape.Volume/1e9:7.2f} m3  "
              f"{o.Shape.Area/1e6:7.2f} m2  valide={o.Shape.isValid()}")
```

Ordre de grandeur de contrôle : une maison de 10 × 8 m sur deux niveaux, murs 250/100 mm → **≈ 50 m³** de murs, 160 m² brut de plancher.
