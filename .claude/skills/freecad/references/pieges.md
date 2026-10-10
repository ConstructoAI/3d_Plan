# Pièges d'API FreeCAD — vérifiés par exécution

Tous constatés sur **FreeCAD 1.1.2 / Windows**. Chacun a coûté au moins une itération de débogage en session réelle. Plusieurs **contredisent la documentation en ligne** ou le code source d'une version plus récente.

Re-vérifier si la version change : la colonne « comment vérifier » donne la sonde.

---

## A. Le source installé n'est pas le binaire

| | |
|---|---|
| **Symptôme** | `Arch: Unknown window type` sur un preset qui existe pourtant dans le code source lu sur disque. |
| **Cause** | Le dépôt source présent sur la machine est en 26.3.0-dev ; le binaire installé est en 1.1.2. `"Sliding door"` a été ajouté **après** la 1.1.2. |
| **Règle** | Ne jamais déduire une API du code source local. Interroger l'instance qui tourne. |
| **Vérifier** | `print(Arch.WindowPresets)` |

Liste réelle en 1.1.2 : `Fixed, Open 1-pane, Open 2-pane, Sash 2-pane, Sliding 2-pane, Simple door, Glass door, Sliding 4-pane, Awning, Opening only`.

**Corollaire** : la propriété de type d'un objet Arch est **`IfcType`** en 1.1.2 (`o.IfcType == "Wall"`), pas `Type`. Filtrer sur `Type` renvoie zéro murs, silencieusement.

---

## B. Placement — conventions irrégulières

### B1. `Arch.makeStructure` sans objet de base

| | |
|---|---|
| **Symptôme** | Dalle décalée de la moitié de sa longueur, flottant à côté du bâtiment. Aucune erreur. |
| **Cause** | L'origine est au **minimum en X**, mais **centrée en Y et Z**. Convention incohérente entre les axes. |
| **Contournement** | Utiliser une `Part::Box` (origine au coin minimum sur les trois axes), puis `Arch.makeStructure(boite)`. |

```python
b = doc.addObject("Part::Box", "b")
b.Length, b.Width, b.Height = lx, ly, ep
b.Placement.Base = Vector(x, y, z)          # coin minimum, prévisible
s = Arch.makeStructure(b)
s.IfcType = "Slab"
```

### B2. Menuiseries — le point de placement est un coin, pas un centre

Mesuré : placement `(2000, 0, 900)`, fenêtre 1200 × 1400 → bbox `X[2000,3200] Y[0,200] Z[900,2300]`.

- largeur → **+X**, hauteur → **+Z**
- épaisseur de menuiserie = **200 mm**, orientée **+Y** (mur courant selon X) ou **−X** (mur courant selon Y)

Un mur Arch de 250 mm est **centré sur son axe** (`Y[−125,+125]`). Sans décalage, la fenêtre déborde. Il faut donc décaler de 100 mm :

```python
# mur courant selon X, d'axe y = Y0
base = Vector(x_depart, Y0 - 100, z_allege)
rot  = Rotation(Vector(1, 0, 0), 90)

# mur courant selon Y, d'axe x = X0
base = Vector(X0 + 100, y_depart, z_allege)
rot  = Rotation(Vector(0,0,1), 90).multiply(Rotation(Vector(1,0,0), 90))
```

`fenetre.Hosts = [mur]` déclenche le percement.

### B3. `Arch.makeStairs`

Mesuré : placement `(6400, 1200, 0)`, longueur 3200 largeur 1000 → bbox `X[6400,9600] Y[200,1200]`. La largeur se développe en **−Y** depuis le placement.

---

## C. Visibilité

### C1. Les BuildingParts propagent leur visibilité aux enfants

| | |
|---|---|
| **Symptôme** | Un plan d'étage affiche l'étage du dessus ; régler la visibilité objet par objet n'a aucun effet. |
| **Cause** | `Arch.makeFloor` crée un **BuildingPart** (`App::GeometryPython`). Basculer sa visibilité la propage à tous ses enfants. Comme les étages sont créés **après** les murs, une boucle dans l'ordre du document les traite en dernier : leur cascade écrase tous les réglages précédents. |
| **Règle** | Forcer les conteneurs à `True` **d'abord**, régler les feuilles **ensuite**. |

```python
CONTENEURS = ("App::GeometryPython", "App::DocumentObjectGroup", "App::Part")
for c in [o for o in doc.Objects if o.TypeId in CONTENEURS]:
    c.ViewObject.Visibility = True          # d'abord
for o in feuilles:
    o.ViewObject.Visibility = regle(o)      # ensuite : ils ont le dernier mot
```

### C2. La géométrie de construction masque tout

Le rectangle Draft servant de base à une toiture (`Arch.makeRoof`) reste **visible** et porte une **face pleine**. Sur une maison de 10 × 8 m, c'est une surface de 80 m² au sommet du bâtiment : en vue de dessus elle masque l'intégralité du modèle. Le mobilier était bien là, simplement caché derrière.

Masquer systématiquement les axes de murs et les contours de toiture avant toute vue de dessus.

### C3. Seuils de coupe entre niveaux

Le plancher de l'étage (par ex. z 2600–2800) est **sous** le niveau des murs de l'étage (2800). Un seuil unique le laisse visible dans la vue du bas, où il masque tout le rez-de-chaussée. Utiliser **deux seuils distincts** : `< 2500` pour le niveau bas, `>= 2750` pour le niveau haut.

---

## D. TechDraw — le domaine le plus piégeux

### D1. Le calcul de lignes cachées est ASYNCHRONE

| | |
|---|---|
| **Symptôme** | `getVisibleEdges()` renvoie une liste vide juste après `recompute()`. Pire : coter une vue vide **fait planter FreeCAD** (`RuntimeError: Access violation`). |
| **Cause** | Le HLR tourne sur un thread de travail. `recompute()` rend la main avant la fin. |
| **Règle** | Attendre explicitement, en pompant la boucle Qt. |

```python
def attendre_geometrie(v, secondes=240):
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
```

### D2. `makeDistanceDim` et `makeDistanceDim3d` sont inutilisables

Deux défauts cumulés :

1. **Elles renvoient `None`** tout en créant bel et bien la cotation. Se fier au retour fait conclure à tort à un échec.
2. **Elles tracent à 1:1 et ignorent l'échelle de la vue.** Sur une planche A3 à 1:50, les lignes d'attache d'un mur de 10 m partent à **100 000 unités** au lieu de 200. La planche paraît vide parce que le dessin est écrasé à la taille d'un timbre par des cotes mille fois trop grandes. Les PDF pèsent alors 869 Ko au lieu de 12 Ko.

**Diagnostic rapide** : exporter la planche en SVG et mesurer la coordonnée maximale dans les attributs `d="..."` — uniquement là, sinon les codes couleur (`#212529`) sont comptés comme des nombres. Une planche A3 correcte reste sous ~4200 unités.

**Solution** : construire le `DrawViewDimension` à la main, comme le fait l'interface.

```python
d = doc.addObject("TechDraw::DrawViewDimension", "Dim")
page.addView(d)
d.References2D = [(vue, f"Vertex{ia}"), (vue, f"Vertex{ib}")]
d.Type = "DistanceX"        # Distance, DistanceX, DistanceY, DistanceZ,
                            # Radius, Diameter, Angle, Angle3Pt, Area
d.X, d.Y = dx, dy
```

### D3. Trouver les bons sommets

`v.getVertexByIndex(i)` renvoie un **`Part.Vertex`** (la coordonnée est dans `.Point`, pas `.x`), exprimé dans le **repère de la vue, origine au centroïde de la vue**.

Reconstruire une carte sommet → coordonnée modèle, puis coter sur des points connus :

```python
def carte_sommets(v, sources, axes=("x", "y")):
    bb = None
    for o in sources:
        if o.Shape and not o.Shape.isNull():
            bb = o.Shape.BoundBox if bb is None else bb.united(o.Shape.BoundBox)
    mn = {"x": bb.XMin, "y": bb.YMin, "z": bb.ZMin}
    mx = {"x": bb.XMax, "y": bb.YMax, "z": bb.ZMax}
    ca = (mn[axes[0]] + mx[axes[0]]) / 2.0
    cb = (mn[axes[1]] + mx[axes[1]]) / 2.0
    pts, i = {}, 0
    while True:
        try:
            p = v.getVertexByIndex(i)
        except Exception:
            break
        if p is None:
            break
        q = getattr(p, "Point", p)
        pts[i] = (q.x + ca, q.y + cb)
        i += 1
    return pts
```

Pour une élévation, passer `axes=("x", "z")`.

Les sommets disponibles sont les **coins de murs projetés**. Coter sur des faces de murs (par ex. 5950 au lieu de 6000 d'axe en axe) — c'est de toute façon la convention architecturale.

### D4. La vue native BIM n'est pas cotable

| Type | dérive de `DrawViewPart` | a de la géométrie | cotable |
|---|---|---|---|
| `TechDraw::DrawViewArch` | **non** | **non** | **non** |
| `TechDraw::DrawViewSection` | oui | oui | oui |
| `TechDraw::DrawViewPart` | oui | oui | oui |

`DrawViewArch` produit du SVG via le moteur de rendu Draft : rien à quoi accrocher une cote. Elle est plus fidèle visuellement (poché BIM) mais exclut toute cotation TechDraw. Dès que des cotes sont demandées, prendre `DrawViewSection` (vrai trait de coupe hachuré **et** cotable) ou `DrawViewPart`.

### D5. Lire la valeur d'une cotation

L'accesseur est **`d.getRawValue()`** en 1.1.2. Ni `getDimensionValue()` ni `getDatumValue()` n'existent — les appeler lève `AttributeError` et fait conclure à tort que la cotation est cassée.

### D6. Export

- `TechDrawGui.exportPageAsPdf(page, chemin)` et `exportPageAsSvg(page, chemin)` — **exigent l'interface graphique**.
- Côté App seulement (donc sans GUI) : `writeDXFPage`, `viewPartAsSvg`, `projectToDXF`, `exportSVGEdges`.
- Modèles de cartouche : `<ressources>/Mod/TechDraw/Templates/`. En 1.1.2, un A3 paysage ISO 5457 se trouve dans le sous-dossier `ISO/`.

---

### D7. 🔴 `DrawSVGTemplate.Template` accepte un DOSSIER sans lever d'erreur

Mesuré le 2026-08-18. Un chemin qui n'est pas un fichier SVG — ici le **répertoire**
`.../Templates/ASME`, choisi par un `os.listdir()[0]` malheureux — est accepté **en silence** :

```
Template = .../Mod/TechDraw/Templates/ASME      (un DOSSIER)   aucune erreur, aucun avertissement
   SVG exporte : width="0mm"   height="0mm"     PDF :   3 287 octets
apres correction (A3_Landscape_ISO5457_minimal.svg)
   SVG exporte : width="420mm" height="297mm"   PDF : 328 999 octets
```

⚠️ **Les vues et les cotes sont dessinées CORRECTEMENT dans les deux cas** — le contenu est juste,
la feuille fait zéro. Vérifié : les 7 valeurs de cote sont présentes dans le SVG à 0 mm comme dans
celui à 420 mm. **Le seul symptôme est la taille du fichier — un facteur 100 sur le PDF.** Une
planche livrée ainsi s'ouvre et paraît vide.

Garde : `assert os.path.isfile(tpl.Template)` après affectation, et contrôler que le PDF dépasse
quelques dizaines de ko.

### D8. Les axes d'une vue sont CENTRÉS SUR ZÉRO, et la verticale est DIRECTE

Mesuré sur une vue de `Direction = (0,-1,0)`, échelle 0,12, modèle 1698,4 × 1212,0 mm :

```
sommets bruts : h de -849,20 a +849,20   w de -606,00 a +606,00
                -> les deux axes sont CENTRES sur l'origine de la vue
                -> les etendues valent EXACTEMENT celles du modele (l'echelle n'y entre pas)
x_modele = h + centre_x        z_modele = w + centre_z        (verticale DIRECTE, non inversee)
```

⚠️ **Ne pas supposer le sens vertical** : je l'ai supposé inversé et mes 4 premières cotes ont
échoué en « sommet introuvable ». Le trancher par un **discriminant physique** — prendre un sommet
dont on connaît la position par une autre voie (ici le plus à gauche, qui appartient forcément à
une platine, donc z = −12) et regarder laquelle des deux hypothèses le rend :

```
hypothese DIRECTE  z = w + 594,0  ->  -12,0   ✅
hypothese INVERSEE z = 594,0 - w  ->  1200,0  ❌
```

💡 Et le bon mode d'échec : une cote posée sur un sommet introuvable **refuse**, elle ne rend pas
un faux nombre. Poser les cotes par recherche de coordonnée modèle plutôt que par index (cf. F4)
transforme une erreur de calibrage en refus visible.

### D9. 🔴 L'ORDRE compte : rattacher le gabarit à la page AVANT de lui donner son fichier

Mesuré le 2026-08-18, **même code, seul l'ordre change** :

```python
# FAUX
tpl.Template = chemin ; page.Template = tpl      ->  1 006 octets,  0 texte   CARTOUCHE ABSENT
# JUSTE
page.Template = tpl ; tpl.Template = chemin      -> 11 894 octets, 57 textes  cartouche present
```

⚠️ **Les vues et les cotes se dessinent correctement dans les deux cas.** Sur une planche réelle :
19 808 octets / **8 textes** (les 8 cotes seules) contre 30 697 octets / **65 textes**
(8 cotes + 57 du gabarit) après correction. Le cadre, le cartouche et les repères de pliage sont
**absents en silence** — et `page.Template` pointe pourtant bien sur le bon objet.

Réparation sur une page déjà construite : `tpl.Template = ""` puis réassigner le chemin.
Les valeurs de `EditableTexts` survivent au rechargement (12 non vides conservées sur 13).

💡 **Garde à écrire** : après export, compter les `<text>` du SVG. Moins de ~20 sur un gabarit
ISO = le cartouche n'est pas là.

### D10. Les noms des champs de cartouche dépendent du GABARIT

Sur `A3_Landscape_ISO5457_minimal.svg`, les 16 champs `freecad:editable` sont en **minuscules
ISO 5457** :

```
title  creator  drawing_number  part_material  scale  sheet_number  date_of_issue
revision_index  general_tolerances  language_code  legal_owner_1..4  document_type
approval_person
```

⚠️ Ce ne sont **pas** les noms `FC-Title` / `FC-SC` / `FC-SH` des anciens gabarits FreeCAD.
Écrire dans `EditableTexts` avec les mauvaises clés **ne lève rien** : mesuré, **0 champ rempli
sur 16**, et l'export inchangé à l'octet près. Toujours lire `dict(tpl.EditableTexts).keys()`
avant d'écrire.

## E. Divers vérifiés

| Point | Fait |
|---|---|
| Export glTF | Enregistré vers `ImportGui` — **exige le GUI**. `.glb` d'une maison complète ≈ 780 Ko. |
| Export universel | `App.getExportType(ext)` → nom de module → charger avec **`importlib.import_module`**, voir E3. |
| `DrawViewPart` | N'a **pas** d'attribut `Shape`. Utiliser `getVisibleEdges()`. |
| Suppression TechDraw | Supprimer dans l'ordre : cotations → vues → gabarits → pages. Les cotations référencent les vues. |
| Fenêtre FreeCAD | `showMaximized()` de Qt peut rester sans effet ; la sous-fenêtre MDI se maximise séparément via `QMdiArea.activeSubWindow().showMaximized()`. |

### E3. `__import__` casse l'export IFC — le nom de module est POINTÉ

| | |
|---|---|
| **Symptôme** | `module 'importers' has no attribute 'export'`. STEP et glTF passent, l'IFC seul échoue. |
| **Cause** | `App.getExportType("ifc")` rend `['importers.exportIFC']`. `__import__("importers.exportIFC")` rend le **paquet racine** `importers`, pas le sous-module. |
| **Règle** | `importlib.import_module(mod).export(...)`. La recette `__import__(mod).export(...)` ne marche que pour les noms sans point (`Import`, `ImportGui`). |

Vérifié : avec `importlib`, l'IFC d'une maison 2 étages sort à ~310 Ko.

### E4. Ne jamais forcer la visibilité à `True` en masse

| | |
|---|---|
| **Symptôme** | Des fils parasites traversent toutes les vues — wires de garde-corps d'escalier, esquisses de menuiseries. Ils réapparaissent après chaque réglage de visibilité. |
| **Fausse piste** | J'ai d'abord conclu à un bug de `Arch.makeStairs` (garde-corps hors repère) et de `makeWindowPreset` (esquisse laissée visible). **C'est faux, vérifié par mesure** : sur un escalier neuf, `RailingWire` est créé avec `Visibility = False`, les mains courantes (`Pipe`) sont correctement placées, et l'esquisse d'une fenêtre neuve est aussi à `False`. |
| **Cause réelle** | Une boucle de pilotage de visibilité du type `for o in doc.Objects: o.ViewObject.Visibility = regle(o)` **écrase les choix de FreeCAD**. Elle rallume la géométrie d'appui que le moteur avait délibérément cachée. |
| **Règle** | Un objet caché par FreeCAD l'est pour une raison. Ne jamais le remonter à `True` sans savoir laquelle. |

Mémoriser l'état natif **avant** toute manipulation, et ne jamais dépasser :

```python
NATIF = {o.Name: o.ViewObject.Visibility          # a capturer AVANT de toucher
         for o in doc.Objects if hasattr(o, "ViewObject")}

def montrer(o, veut):
    o.ViewObject.Visibility = veut and NATIF.get(o.Name, True)
```

Complément utile, indépendant de l'état natif : **ce qui n'a pas de solide n'est pas de la construction** — lignes d'axe Draft, contours de toiture, esquisses, wires de base.

```python
def est_appui(o):
    sh = getattr(o, "Shape", None)
    return sh is not None and not sh.isNull() and not sh.Solids
```

Le rectangle Draft d'une toiture reste le cas le plus coûteux : il porte une **face pleine** (80 m² sur une maison de 10 × 8 m) qui masque tout le modèle en vue de dessus.

### E6. Le schéma d'unités fausse les cotes ≥ 10 000 mm

Trois défauts qui se cumulent, chacun silencieux :

1. Le schéma par défaut (`Internal`) **bascule en mètres** au-delà de 10 000 mm. Sur une planche en millimètres, le hors-tout sort `10,25 m` au milieu de cotes en mm. Avec `FormatSpec="%.0f"` par-dessus, il devient **`10`** — un plan faux d'un facteur 1000.
2. `Units.setSchema(6)` **ne persiste pas** : le schéma retombe à `Internal` en cours de script. Il faut écrire **aussi** la préférence.
3. Le texte d'une cotation est **mis en cache** : changer le schéma ne le rafraîchit pas, et `recompute()` non plus. Il faut `touch()` chaque cotation.

```python
App.ParamGet("User parameter:BaseApp/Preferences/Units").SetInt("UserSchema", 6)  # MmMin
Units.setSchema(6)
for d in cotations:
    d.touch()
doc.recompute()
assert "mm" in App.Units.Quantity(10250, App.Units.Length).UserString
```

Schémas utiles en 1.1.2 : **6 `MmMin`** et **8 `FEM`** gardent tout en mm ; **5 `ImperialBuilding`** donne le pieds-pouces québécois (`10250 → 33' 7" + 1/2"`).

### E7. Coter contre une valeur attendue, sinon l'erreur passe

Une cotation qui s'accroche au mauvais sommet affiche un nombre **plausible**. Mesuré : coter le haut des murs (z=5400) avec une tolérance de 400 mm attrapait le bas du débord de toit (z=5054) et affichait **2254 au lieu de 2600** — sans le moindre avertissement.

Deux garde-fous, tous deux nécessaires :

- tolérance de recherche à **200 mm**, pas 400 ;
- chaque cote déclare sa **valeur attendue**, comparée à `getRawValue()` après création.

Corollaire : sur une élévation, le haut des murs n'est **pas** un sommet visible — il est caché par le débord. Coter ce que le dessin montre vraiment : ligne d'égout et faîtage.

### E1. Capturer la vue 3D quand une planche est ouverte

Après avoir ouvert une planche TechDraw, `Gui.ActiveDocument.ActiveView` renvoie un **`MDIViewPagePy`**, qui **n'a pas de `saveImage`**. Toute capture échoue alors sur *« Aucune vue 3D active »* — sans que rien n'indique que le problème vient de la planche restée au premier plan.

Ne pas se fier à la vue **active** : chercher une vue 3D parmi **toutes** celles du document.

```python
vues = Gui.ActiveDocument.mdiViewsOfType("Gui::View3DInventor")
vue = next((v for v in vues if hasattr(v, "saveImage")), None)
if vue is None:
    Gui.ActiveDocument.createView("Gui::View3DInventor")
    vue = Gui.ActiveDocument.mdiViewsOfType("Gui::View3DInventor")[0]
vue.saveImage(chemin, largeur, hauteur, "Current")
```

`freecad_screenshot` du pont MCP applique déjà ce repli (corrigé le 2026-07-29) : il trouve ou crée une vue 3D quelle que soit la vue active.

### E1bis. La transition de caméra est ANIMÉE

| | |
|---|---|
| **Symptôme** | `--view front` rend une vue oblique. On croit à un problème de caméra ou à une méthode absente. |
| **Cause** | `viewFront()` **lance une animation** et rend la main immédiatement. `saveImage()` capture pendant que la caméra bouge encore. La **première capture après tout changement de vue est fausse**, silencieusement. |
| **Coût constaté** | 3 allers-retours de diagnostic en session froide. |

Corrigé dans `freecad_bridge.py` (2026-07-29) : le pont rejoue l'orientation, laisse tourner la boucle Qt entre les deux et marque une pause de stabilisation. Le piège subsiste si l'on appelle `saveImage()` soi-même.

```python
for _ in range(2):
    view.viewFront()
    QtCore.QCoreApplication.processEvents()
    view.fitAll()
    QtCore.QCoreApplication.processEvents()
```

### E1ter. La caméra est en PERSPECTIVE par défaut

Les noms de vue ne règlent que la **direction**, pas le type de projection. Une « élévation » sort donc avec des fuyantes — inexploitable en architecture, et difficile à voir sur une façade simple.

```python
view.setCameraType("Orthographic")     # avant toute vue droite
print(view.getCameraType())            # verifier
```

`freecad_screenshot` force désormais l'orthographique sur toutes les vues droites (front, rear, top, bottom, left, right) et le laisse libre en iso. Paramètre `ortho` pour imposer.

### E1quater. Le preset `Opening only` produit une forme NULLE

Mesuré sur un percement fonctionnel :

```
Porte_garage    isNull=True   solides=0   BoundBox = ±1.797e308
```

Le percement du mur **fonctionne parfaitement** — mais l'objet menuiserie n'a aucune forme propre. `isNull()` le signale correctement (contrairement à ce qu'on pourrait croire), donc les contrôles de validité standards le traitent bien.

Le danger réel est la **BoundBox aberrante** : toute logique qui lit `BoundBox` sans tester `isNull()` d'abord récolte ±1,797e308, ce qui empoisonne une union de bbox, un tri par altitude ou un filtre de visibilité. **Toujours `isNull()` avant `BoundBox`.**

### E2. Un script d'essai ne doit jamais écrire dans le modèle de l'utilisateur

`App.ActiveDocument or App.newDocument(...)` réutilise le document ouvert : un test de fumée lancé pendant une session de travail **ajoute ses objets au projet en cours**, silencieusement. Toujours créer un document jetable, puis le refermer et rendre la main au précédent.

---

### E8. 🔴 Le SUFFIXE AUTOMATIQUE des libellés détruit toute information portée par des chiffres

Mesuré **deux fois** les 2026-08-18/19, dans les deux sens opposés.

**a) Il DÉTRUIT** — `Part.show(shape, "T1")` puis `Part.show(shape, "T2")` :

```
libelles obtenus : T1, T001, T2, T002, T003, T004, T005, T006
```

Le compteur est **partagé** : FreeCAD retire les chiffres finaux du nom de base avant d'ajouter son
suffixe. **`T001` peut venir de `T1` OU de `T2`** — l'identifiant est perdu. Conséquence mesurée :
un plan de débit a fusionné deux repères en un seul, **un repère entier disparaissait en silence**,
et la planche restait plausible.

**b) Il DÉDOUBLE** — sur un STEP de production, une pièce nommée `P14_coude_90` :

```
P14_coude_90    <- le nom d'origine ('90' fait partie du nom, 2 chiffres)
P14_coude_001 … P14_coude_023   <- les copies, suffixe auto a 3 chiffres
```

Un découpage `^(P\d+)_(.+?)(\d{3})?$` rend alors **deux noms** pour un seul repère
(`coude_90` et `coude_`) → **45 repères comptés 46**. *Un coude à 90° s'appelle naturellement
« coude_90 » : le cas n'a rien d'exotique.*

**La parade — porter l'identifiant dans une propriété, jamais dans le libellé :**

```python
o.addProperty("App::PropertyString","Repere","Debit").Repere = "T2"
```

Relevé après : libellés auto **fusionnés** (`Piece, Piece001, Piece002…`), repères **intacts**.

⚠️ Si on n'a que des noms (cas d'un STEP importé), **seul le PRÉFIXE est sûr** : `P14` est stable,
`coude_90` ne l'est pas. Et le contrôle qui attrape les deux cas est une **assertion sur
l'ensemble attendu**, pas une vérification de forme :

```python
assert set(reperes) == {"P1","PL1","T1","T2"}, "reperes inattendus : %s" % sorted(reperes)
```

## F. Part / mécano-soudé — vérifiés le 2026-08-18 (FreeCAD 1.1.2, OCC 7.8.1)

Domaine neuf par rapport aux sections A–E : balayage, booléens, sélection d'entités, assemblage.
Chaque piège ci-dessous a été **mesuré**, et chaque mesure est recoupée à un calcul fermé.

### F1. `MakePipeShell` — un seul mode est sain, et deux rendent un solide FAUX sans erreur

Balayage d'un profil de 4 sommets le long d'une hélice discrétisée en 29 points :

| mode | temps | solide |
|---|---|---|
| `setFrenetMode(True)` | 0,143 s | valide |
| `setFrenetMode(False)` (repère corrigé) | 0,140 s | valide, **même volume** |
| `setBiNormalMode(Vector(0,0,1))` | 0,169 s | ⚠️ **INVALIDE**, volume faux de **4,9 %** |
| `setAuxiliarySpine(axe, True, 0)` | **10,03 s** | ⚠️ **INVALIDE** |

⚠️ **`setAuxiliarySpine` est pathologique** : 10 s sur 29 points, et sur **225 points il fige
FreeCAD** — relevé 737 s de CPU, processus vivant, `Responding=False`, tué à la main après
12 minutes. Croissance très superlinéaire. **Ne jamais l'appeler dans une boucle.**

Sur une hélice, **`setFrenetMode(True)`**. Point.

### F2. Les quadrilatères entre deux anneaux d'un balayage hélicoïdal sont GAUCHES

```
Part.Face(Part.makePolygon([A[k], A[k2], B[k2], B[k], A[k]]))
  -> OCCError: Failed to create face from wire
```

Dès que le chemin vrille, deux sections consécutives ne sont pas coplanaires. **Il faut
trianguler** (2 triangles par quad). Le volume se calcule ensuite très bien par le théorème de la
divergence, sans passer par OpenCascade — et le maillage reste fermé (chaque arête parcourue une
fois dans chaque sens), vérifié de 6 à 64 segments par tour.

### F3. ⚠️ `Compound.Volume` est une SOMME — il compte deux fois les recouvrements

Mesuré sur une couronne de 171 buses à Ø1400 (entraxe 25,72 mm, collerette Ø44, donc
interpénétration de 18,28 mm) :

```
Part.Compound(pieces).Volume  = 3 229 720,6 mm3
somme des 171 volumes unitaires= 3 229 730,4 mm3   <- identique
volume REEL (union)            = 2 658 114,7 mm3
                                 -> SUREVALUATION de +21,50 %   (+4,49 kg d'acier)
```

`isValid()` = True, l'image est correcte, la nomenclature s'additionne. **Rien ne le signale.**
Dès qu'on multiplie un volume par une densité, toute interpénétration devient de la matière
facturée qui n'existe pas — et en mécano-soudé les pièces se touchent par construction.

Parade la moins chère : pour chaque paire dont les `BoundBox` se croisent, mesurer
`a.common(b).Volume` et avertir si non nul (45 ms par paire sur cet exemple).

### F4. ⚠️ Les index d'entités changent APRÈS chaque feature — et ils se RÉORDONNENT

Plaque 200×150×12, 4 trous Ø14, puis chanfrein 2 mm sur 4 arêtes :

```
avant : 24 aretes, aretes de trou = [9, 10, 11, 12, 16, 17, 18, 19]
apres : 32 aretes, aretes de trou = [12, 13, 14, 15, 23, 24, 25, 26]
```

Aucun index ne survit. Pire qu'un décalage : **l'ordre s'inverse** — `[9..12]` étaient les cercles
du dessus (z = 12), `[12..15]` sont ceux du dessous (z = 0). Un code qui prend « les 4 premières
arêtes de trou » désigne le dessus avant la feature et le dessous après, sans jamais planter.

Et le cas dangereux, chiffré — chanfrein 1 mm posé sur les index périmés `[9,10,11,12]` :

```
index perimes : REUSSIT, solide VALIDE, retire 199,36 mm3   (+8,167 % / calcul ferme)
predicat      : retire 184,31 mm3                           (+0,002 % / calcul ferme)
```

**Le prédicat de coordonnées, relu frais, coûte < 0,1 ms sur 32 arêtes.** Le cache d'index est un
pur passif :

```python
def aretes_circulaires(forme, rayon, axe=(0,0,1), tol=1e-6):
    ax = Vector(*axe)
    return [i for i, e in enumerate(forme.Edges)
            if isinstance(e.Curve, Part.Circle)
            and abs(e.Curve.Radius - rayon) < tol
            and abs(abs(e.Curve.Axis.dot(ax)) - 1.0) < tol]
```

### F5. `Rotation(Vector(0,1,0), -90)` envoie la section sur x ∈ [−c, 0], pas [0, c]

Un tube construit couché (`makeBox(L, c, c)`) puis redressé par cette rotation se retrouve décalé
de **−c** en X. Mesuré sur un HSS 4×4 : **101,6 mm** exactement, soit le côté du tube.

⚠️ **Le volume ne dépend pas du placement** : une nomenclature de débit reste juste **au bit près**
(226,399 kg, mêmes cinq lignes) pendant que les platines flottent à côté des poteaux.
`isValid()` : 0 invalide. **C'est l'image qui l'a vu.**

Parade structurelle — construire chaque profilé directement dans son axe, jamais le tourner après :

```python
dims = {"x": (L,c,c), "y": (c,L,c), "z": (c,c,L)}[axe]
```

### F6. Le volume ne distingue PAS une hélice d'une pile d'anneaux

Un filet hélicoïdal et un empilement de gorges annulaires ont **le même volume**, et la vue
**iso** d'un filet fin ressemble à une pile de disques.

Mesuré le 2026-08-18, les deux construits avec **exactement le même profil de sillon**, seule
différence hélicoïdal contre annulaire :

```
HELICE  V = 8069,1350   ecart au calcul ferme (Pappus) -0,0119 %   helicoidal = True
ANNEAUX V = 8069,1302   ecart au calcul ferme (Pappus) -0,0119 %   helicoidal = False
ecart des deux volumes : -0,0048 mm3  =  -0,0001 %
```

⚠️ **Le même écart de Pappus au chiffre près.** Un contrôle analytique de volume — même exact,
même recoupé à une formule fermée — **ne distingue pas les deux formes.**

Le test qui tranche, et il est bon marché :

```python
tourne = forme.copy()
tourne.Placement = Placement(centre, Rotation(Vector(0,0,1), 180))
forme.cut(tourne).Volume / forme.Volume      # ~0 = revolution ; >0 = helice
```

Relevé : **9,88 %**. Contrôle direct complémentaire : l'altitude du sillon avance d'exactement
**P/4 par quart de tour** (1,6949 → 2,3199 → 0,4449 → 1,0699 sur un pas de 2,5).

### F7. La leçon qui les recouvre toutes : `isValid()` + volume + image ne suffisent pas

Sur une séance de sept exercices, **quatre modèles faux** ont passé les trois contrôles :
un angle de flanc aplati (volume plausible), une pile d'anneaux prise pour un filet (volume juste
à 10⁻⁸), un chanfrein au mauvais endroit (volume à +8 %, plausible), un assemblage décalé de
101,6 mm (nomenclature identique au bit près).

**Ce qui a tranché à chaque fois : une invariante que la forme JUSTE possède et que la FAUSSE n'a
pas** — Pappus-Guldin contre le volume, symétrie de révolution contre hélice, périodicité P/4,
écart de centrage. Une assertion doit comparer **deux grandeurs du modèle**, jamais le modèle à un
nombre écrit à la main : un nombre écrit à la main ne vérifie que la capacité à recopier son
intention.

### F8. Les booléens mangent **94,5 %** du temps — le « 77 % » comptait mal

Filet M20×2,5×30 mm. **Deux constructions différentes, deux protocoles, la même conclusion** :

| phase | 2026-08-18 (tir unique) | **2026-08-19 (protocole F31)** |
|---|---|---|
| hélice | 0,001 s — 0,1 % | 0,0005 s — 0,1 % |
| balayage | 0,062 s — 5,0 % | 0,0360 s — 5,4 % |
| **booléen (`fuse`)** | 0,95 s — **77,0 %** | 0,3489 s — **52,8 %** |
| **rognage (`common`)** | 0,22 s — 17,8 % | 0,2758 s — **41,7 %** |
| total | 1,23 s | **0,6612 s** |

🔴 **Le « 77 % » ne tient pas : la fusion seule vaut 52,8 %.** Mais le chiffre était mal découpé —
**le rognage est un booléen lui aussi**. En les additionnant :

```
2026-08-18 :  77,0 + 17,8 = 94,8 %          2026-08-19 :  52,8 + 41,7 = 94,5 %
```

> ✅ **La part BOOLÉENNE est la même à 0,3 point près, sur deux constructions et deux protocoles.**
> C'est elle qui est robuste ; la répartition entre `fuse` et `common` ne l'est pas.
> ➜ **Toute borne de performance doit compter les booléens, pas les formes** — et la borne est
> **~95 %**, pas 77 %.

⚠️ **Réserve honnête** : ma construction de 2026-08-19 n'est pas celle de 2026-08-18 (volume final
**7 046,695 mm³** contre 8 069,135 mm³ pour `patrons.filetage_iso()`). Les phases ne sont donc pas
strictement comparables une à une — seule la part booléenne globale l'est, et c'est justement elle
qui concorde.

⚠️ Le total a chuté de **1,23 s à 0,661 s** : les composantes de 2026-08-18 étaient toutes
sous-secondes, donc dans le régime contaminé de **F31**. À titre de comparaison,
un tube creux par soustraction coûte 0,008 s, un congé sur 4 arêtes 0,026 s, un chanfrein 0,009 s.

### F8bis. La LOI de coût du booléen — linéaire, et le lot vaut 10 à 17×

Mesuré le 2026-08-18 : plaque percée **un trou à la fois** jusqu'à 200 trous, chaque `cut`
chronométré avec le nombre de faces déjà présentes.

```
modele LINEAIRE    : temps_ms = 0,77 + 0,3878 x faces      R2 = 0,9935
modele QUADRATIQUE : temps_ms = 2,39e-03 x faces^2         residu 42,9x PIRE
```

**Un booléen coûte O(faces), pas O(faces²)** — ~0,39 ms par face déjà là, plus 0,8 ms fixe.
200 `cut` enchaînés : 8,93 s, forme finale valide, 206 faces.

**Le vrai levier est le groupage.** Même plaque, 60 outils :

| opération | un-à-un | en lot (`Part.Compound`) | rapport |
|---|---|---|---|
| `cut` | 875,8 ms | **89,5 ms** | **9,8×** |
| `fuse` | 1 774,9 ms | **103,5 ms** | **17,2×** |

Topologie et volume **identiques** (46 faces, mêmes arêtes, mêmes sommets, écart 0,00e+00,
calcul fermé à −2·10⁻¹³ %).

### F9. ⚠️ `common` sur un compound n'est PAS un `common` itéré

Un `Part.Compound` se comporte comme l'**UNION** de ses membres. Donc :

| | équivalence |
|---|---|
| `cut` | A∖(B∪C) = (A∖B)∖C → **lot équivalent**, écart 0,00e+00 |
| `fuse` | A∪(B∪C) = (A∪B)∪C → **lot équivalent**, écart 0,00e+00 |
| `common` | A∩(B∪C) **≠** (A∩B)∩C → **autre opération** |

Mesuré sur 3 cylindres **disjoints** dans une boîte :

```
common ITERE   A n B n C  :  V = 0,0000     0 solide
common sur LOT A n (BuC)  :  V = 6 785,84   3 solides   = exactement 3 bouchons
```

⚠️ Substituer un compound à une boucle de `common` change le résultat **sans lever d'erreur** —
et ça ressemble à une optimisation. Garde : les deux doivent rendre le même volume.

### F10. Muter le banc — deux règles apprises en le faisant

Un banc de contrôles ne vaut que ce qu'il attrape. Vérifié en injectant, dans un filetage M20
sain, les deux fautes réellement commises en séance :

| mutation injectée | écart Pappus | test de symétrie | verdict |
|---|---|---|---|
| flanc aplati (profil enfoncé radialement) | **+1,700 %** | True | ✅ attrapée par le volume |
| pile d'anneaux (profil **identique**) | **−0,0119 %** | **False** | ⚠️ **le volume SURVIT** |

**a) Un contrôle de GRANDEUR est aveugle aux fautes de STRUCTURE.** Volume, aire, longueur
attrapent les fautes de dimension. Hélicoïdal contre annulaire, placement, orientation, adjacence
leur échappent entièrement. Il faut une invariante de **forme** — symétrie, périodicité, centrage.

**b) ⚠️ Une mutation qui change DEUX choses ne prouve rien sur aucune des deux.** Ma première pile
d'anneaux écartait de **+3,996 %** et j'ai failli la déclarer attrapée : elle portait le profil
rétréci *en plus* des anneaux, et c'était le profil qui était détecté. Isolée proprement, la
mutation passe. **Muter une seule chose à la fois**, sinon le banc a l'air meilleur qu'il n'est.

### F11. Facettisation d'un cercle — la loi, et le SIGNE qui s'inverse

Mesuré le 2026-08-18, polygone **inscrit** de n côtés contre le cercle exact (barre D100 × 100) :

| n | écart mesuré | loi asymptotique −2π²/3n² |
|---|---|---|
| 6 | **−17,3007 %** | −18,2770 |
| 12 | −4,5070 % | −4,5693 |
| 16 | −2,5505 % | −2,5702 |
| 24 | −1,1384 % | −1,1423 |
| 32 | −0,6413 % | −0,6426 |
| 64 | −0,1606 % | −0,1606 |
| 128 | −0,0402 % | −0,0402 |

**La loi colle à la 4ᵉ décimale dès n = 24** ; en dessous elle sur-estime l'erreur — borne
conservatrice, pas valeur.

⚠️ **Le signe dépend de ce que la courbe borne.**

- **matière** (barre ronde) : polygone inscrit plus petit → volume **sous-estimé** ;
- **vide** (plaque percée d'un trou rond) : le trou polygonal retire **moins** → volume
  **sur-estimé**. Mesuré sur une plaque 300×300×100 percée D100 : **+0,4309 %** à n = 12,
  soit **+35 398 mm³** de matière fantôme.

⚠️ **Sur un tube, les deux ne se compensent pas** : extérieur et intérieur portent le **même**
facteur k, donc l'écart du tube est exactement celui de la barre pleine (−4,5070 % à n = 12).

**Règle** : *chaque frontière circulaire multiplie par k l'aire qu'elle borne* — négatif pour la
matière, positif pour un vide dans de la matière à bords droits.

**Règle inverse**, vérifiée en mesurant la flèche obtenue : `n_min = π·√(r / 2δ)`.

| rayon | δ=0,5 mm | 0,2 mm | 0,1 mm | 0,05 mm |
|---|---|---|---|---|
| 12,7 | 12 | 18 | 26 | 36 |
| 50 | 23 | 36 | 50 | 71 |
| 350 | 59 | 93 | 132 | 186 |

⚠️ **`n` dépend du RAYON, pas de la pièce.** Un réglage fixe à 64 segments donne 0,06 mm de flèche
sur un Ø100 et 0,42 mm sur une virole Ø700 — **sept fois pire**. Une borne qui tient partout se
pose sur la **flèche en mm**, jamais sur le nombre de segments.

⚠️ **F11 décrit le polygone INSCRIT — ce n'est pas la seule convention.** Vérifié le 2026-08-18 :
le module DAO de Constructo construit un polygone **à AIRE PRÉSERVÉE**, dont le circonrayon est
gonflé par `R = r·√(θ/sin θ)` (θ = 2π/n). Mesuré par shoelace sur ses points : l'aire vaut
**πr² exactement** de 12 à 256 côtés, donc **aucune** erreur de volume.

**Toujours mesurer l'aire des points AVANT d'appliquer la loi inscrite.** Une seule ligne :

```python
A = abs(sum(P[i][0]*P[(i+1)%n][1] - P[(i+1)%n][0]*P[i][1] for i in range(n)))/2
```

⚠️ Et la compensation a un prix, sur une AUTRE grandeur : le polygone à aire préservée **chevauche**
le cercle. Sur une barre Ø100 à 12 côtés — mesuré :

```
sommet a sommet   102,3327 mm
meplat a meplat    98,8458 mm
                   -> etendue 3,487 mm sur un nominal de 100
```

L'aire est exacte, **la cote ne l'est pas**. Pour un ajustement, c'est l'étendue qui compte.
Écart maximal du polygone à aire préservée = **flèche inscrite / 1,5** (rapport mesuré convergeant :
1,4607 à n=12 → 1,4997 à n=128), donc `n_min = π√(r/2δ)` sur-estime **n** d'un facteur √(3/2) = 1,2247.

### F12. Deux fautes de raisonnement que ce poste a payées le même jour

**a) Une observation compatible avec deux mécanismes n'en établit aucun.** J'ai vu `volume_m3`
identique de 6 à 256 segments et j'en ai conclu « le métré facture la métadonnée `circle` ».
L'autre hypothèse — « le polygone a déjà l'aire du cercle » — prédisait la **même** observation,
et c'était elle la bonne. Une ligne de shoelace les départageait.

**b) Une mutation qui change deux choses ne prouve rien sur aucune des deux.** Cf. F10.

Les deux ont la même forme : **conclure sans isoler**. Le remède est le même — mesurer le
mécanisme, pas seulement sa sortie.

### F13. `section()` — le coût suit le TYPE de surface, pas le nombre de faces

Mesuré le 2026-08-18 :

| joint | faces | temps |
|---|---|---|
| plaque sur plaque (plan/plan) | 12 | 2,51 ms |
| tube rond sur tôle | 9 | 1,69 ms |
| HSS sur HSS (tout facettes) | 20 | 9,67 ms |
| **selle tube D60 sur D100** | **6** | **57,57 ms** |
| **tube traversant (2 courbes)** | **6** | **87,96 ms** |

⚠️ **Le cas le plus cher a le moins de faces.** Cylindre ∩ cylindre n'a pas de solution rationnelle
fermée : OCC y va numériquement. Sur des **polyèdres**, en revanche, c'est linéaire :
`ms = 0,56 + 0,2595 × faces` (R² = 0,9973), soit ~33 % moins cher par face qu'un `cut`.

⚠️ **Et ce n'est pas « courbe » qui coûte, c'est la B-SPLINE.** Mesuré le 2026-08-19 sur une pièce
industrielle réelle (313 paires, 48,7 s) :

```
plan     n plan        2,51 ms
cylindre n plan        1,69 ms
cylindre n cylindre   57,57 ms
B-spline n B-spline  2 350 ms      -> ~1 000x un joint plan
```

Une bride à **95,7 % de faces courbes** (44 cylindres) est **rapide** ; un couvercle bombé à
4 B-splines est **lent**. Le nombre de faces ne l'explique pas : 43 en moyenne chez les lentes
contre 27 chez les autres — **1,6× d'écart pour 63× de coût**.

💡 **La composition se lit en microsecondes** (`type(f.Surface).__name__`) : une `BSplineSurface`
des deux côtés annonce ~2 s. **Le budget est prévisible avant de payer.**

⚠️ **Et la distribution est très asymétrique** : médiane **37,2 ms**, moyenne **156 ms**, p99
**1 727 ms**, max **2 355 ms**. Les **10 % les plus lentes pèsent 63 %** du temps total. *Une borne
posée sur la moyenne se trompe sur presque toutes les paires et n'attrape pas celles qui coûtent.*

⚠️ **`distToShape` n'est PAS un pré-test bon marché — mais le rapport S'INVERSE selon le cas, et
mon chiffre d'origine le masquait.** Corrigé le 2026-08-20, protocole **F31** (≥ 2 s par mesure),
sur trois configurations séparées au lieu d'une moyenne sur 313 paires mélangées :

| cas | `distToShape` | `common`+`section` | **boîte englobante** | rapport |
|---|---|---|---|---|
| se **touchent** (about) | **6,763 ms** | 11,370 ms | 0,08719 ms | **0,59** |
| se **coupent** | **14,796 ms** | 25,109 ms | 0,09021 ms | **0,59** |
| **loin** (2 m) | 4,393 ms | 3,324 ms | 0,08562 ms | 1,32 |

🔴 **Quand les formes sont proches ou se touchent, `distToShape` est 1,7 × PLUS RAPIDE** que le
booléen — l'inverse de ce que j'avais publié (« 1,5 × plus lent »). Il n'est plus lent que sur les
paires **lointaines**, là où le booléen se court-circuite sur les boîtes.

> ➜ **Le chiffre d'origine (43,9 contre 28,9 ms) moyennait des cas de natures opposées.** Séparer
> les configurations retourne la conclusion sur deux tiers d'entre elles.

✅ **Ce qui tient, et sur une base ferme cette fois** : la **boîte englobante** coûte **0,087 ms**,
soit **37 à 49 ×** moins que l'un ou l'autre. C'est le seul pré-filtre qui vaut quelque chose —
`distToShape` coûte **131 %** du travail qu'il prétend éviter sur une paire lointaine.

### F14. ✅ Deux cylindres de MÊME diamètre à axes concourants se coupent selon deux ELLIPSES PLANES

Écart des points de la courbe à leur plan moyen, mesuré :

```
D60 sur D60 a 90 deg, axes concourants   1,4e-13 mm   PLAN
D60 sur D60 a 45 deg, axes concourants   9,2e-13 mm   PLAN
D60 sur D100 a 90 deg                    1,81 mm      non plan
D60/D60 a 90 deg, axes DECALES de 15 mm  19,3 mm      non plan
```

**Les deux conditions sont nécessaires** — et le décalage d'axes est **dix fois pire** que
l'inégalité de diamètre.

Forme fermée, vérifiée sur les demi-axes mesurés à 90°, 60°, 45° et 30° :

```
demi-petit axe = r            (exact dans les quatre cas)
demi-grand axe = r / sin(a)   ou 2a est l'angle entre les axes
```

Recoupée par le périmètre de Ramanujan : à 90°, 2 × 229,212 = **458,424 mm**, exactement ce que
rend `section()`.

➜ Utile pour tout moteur sans B-rep : le joint tubulaire à diamètres égaux (châssis, garde-corps,
charpente) se calcule **analytiquement**, sans intersection de surfaces.

### F15. ⚠️ Une section sur MAILLAGE ne sous-estime pas « toujours » — le biais suit la convention

Erreur que j'avais commise en la raisonnant au lieu de la mesurer. Selle D60/D100, contre la
référence B-rep de 193,6271 mm :

| n | polygone inscrit | polygone à aire préservée |
|---|---|---|
| 12 | −0,481 % | **+1,841 %** |
| 16 | **+0,000 %** | +1,300 % |
| 32 | −0,064 % | +0,258 % |
| 64 | −0,007 % | +0,073 % |

L'inscrit **n'est pas monotone** ; l'aire-préservée **sur-estime toujours**. L'intersection de deux
polyèdres est une ligne brisée entre facettes, qui peut zigzaguer **plus long** que la courbe lisse.

✅ En revanche c'est **stable** : en faisant tourner une pièce sur tout un pas de facette (n=32,
7 phases), l'étendue est de **0,0156 mm = 0,008 %**. Biais connu, pas bruit.

### F16. 🔴 Après un import STEP, FreeCAD CRÉE des plans et axes **infinis** — et ils passent tous les contrôles

⚠️ **Ils ne viennent PAS du fichier STEP** (je l'avais d'abord écrit, c'était faux). L'importateur
crée un conteneur **`App::Part` par nœud d'assemblage**, et chaque `App::Part` porte un
**`App::Origin`** avec 3 `App::Line` et 3 `App::Plane` **infinies**. Mesuré : sur `as1-ac-214.stp`,
**10 `App::Part` → 10 `App::Origin` → exactement 60 entités**, et les chaînes « Axe X » / « Plan XY »
apparaissent **0 fois** dans le `.stp` (alors qu'« AXIS » y est 123 fois). Les libellés suivent la
langue de l'interface.

➜ **C'est un piège du pilotage de FreeCAD, pas un danger de l'échange STEP.** Un lecteur STEP qui
ne construit pas d'`App::Part` ne les rencontrera jamais.

Mesuré le 2026-08-18 sur une pièce industrielle réelle (2,9 Mo, AP203, 211 objets) :

```
Axe X / Axe Y / Axe Z     Edge   valide=True  null=False  etendue 2,000e+100 mm
Plan XY / Plan XZ / Plan YZ Face  valide=True  null=False  aire    8,000e+100 mm2
```

⚠️ **Ce n'est PAS le piège `isNull()` de la section E** (preset `Opening only`, ±1,797e308 mais
signalé par `isNull()`). Ici **`isNull()` rend False** : la forme existe, elle est **infinie**.

| grandeur | effet |
|---|---|
| boîte englobante de la scène | ❌ **détruite** — 2·10¹⁰⁰ au lieu de 4 310 mm |
| aire totale | ❌ détruite |
| volume / masse | ✅ intact (ni plan ni arête n'ont de volume) |
| `isValid()` / `isNull()` | ✅ **ne signalent rien** |

Filtre qui marche — le critère du **solide** suffit ici, le seuil est la ceinture :

```python
ABERRANT = 1e9   # mm
sains = [o for o in objets
         if len(o.Shape.Solids) > 0
         and max(o.Shape.BoundBox.XLength, o.Shape.BoundBox.YLength,
                 o.Shape.BoundBox.ZLength) < ABERRANT]
```

### F17. Coût et fidélité d'un import STEP réel

Même pièce, 2 900 973 octets :

```
import        4,69 s          (~620 ko/s)
topologie     203 solides, 2 281 faces, 4 983 aretes, 3 156 sommets
invalides     0
volume        617 994 580 mm3  ->  4 851,3 kg d'acier
encombrement  4 310 x 4 335 x 1 934 mm
surfaces      51,8 % planes | 36,1 % cylindres | 4,9 % B-splines | 4,7 % tores | 2,5 % cones
```

⚠️ **Ces chiffres ont d'abord ete publies DOUBLES** — voir F18, c'est le piege du meme jour.

**48,2 % des faces d'une pièce mécano-soudée réelle sont courbes.**

**Peser le maillage** (`MeshPart.meshFromShape`, volume du maillage contre volume B-rep) :

| déflexion | triangles | écart de masse | temps |
|---|---|---|---|
| 5,0 mm | 92 030 | **−0,1611 %** (−7,9 kg) | 2,49 s |
| 1,0 mm | 174 020 | −0,0883 % | 3,43 s |
| 0,2 mm | 623 452 | −0,0186 % (−0,9 kg) | 10,19 s |

⚠️ **Bien meilleur que ne le prédirait F11** : l'erreur est **diluée par la part plane** (51,8 %
des faces sont exactes). Ne pas transporter ce chiffre sur une pièce entièrement tournée.

⚠️ **La finesse pour PESER et la finesse pour COTER diffèrent d'un facteur ~50.** 5 mm de déflexion
pèse à 0,16 % près et cote à 5 mm près. Un réglage unique force forcément l'un des deux à être faux.

### F18. 🔴 Sommer un ARBRE d'objets double le résultat — `App::Part` agrège ses enfants

⚠️ Comme F16, c'est une structure **créée par FreeCAD** à l'import, pas une propriété du fichier.
Relevé sur quatre assemblages : le doublement est **exact (×2) dans les quatre**, et **absent des
deux fichiers ne portant qu'une pièce**.

Le piège qui m'a fait publier une masse **exactement double** le 2026-08-18.

Après un import STEP, `doc.Objects` contient **à la fois** le conteneur et ses enfants :

```
objet 'Bruleur_industriel_AP203'   type = App::Part
   Shape : Compound, 203 solides
   enfants : 203      dont pieces nommees : 203 / 203
```

Itérer `doc.Objects` et sommer `.Shape.Volume` compte **chaque solide deux fois**.
`isValid()` est vrai partout, le volume est plausible, l'image est correcte. **Rien ne le signale.**

Les deux traversées correctes concordent (écart 0,0005 %) :

```
par RACINES  (conteneurs seuls) :   1 objet, 617 991 521 mm3 -> 4 851,2 kg
par FEUILLES (les 203 enfants)  : 203 objets, 617 994 580 mm3 -> 4 851,3 kg
en sommant TOUT                 : 406 solides,               -> 9 702,5 kg   FAUX
```

```python
# une SEULE des deux, jamais les deux
feuilles = [o for o in objets if not (getattr(o, "Group", None) or [])]
racines  = [o for o in objets if not any(o in (getattr(p,"Group",None) or []) for p in objets)]
```

**Le contrôle qui l'attrape** — compter les solides par les deux traversées et exiger l'égalité :
203 contre 203 ✅ ; 406 contre 203 ❌.

⚠️ Même famille que F3 (`Compound.Volume` est une somme) : *un volume qui additionne sans savoir
ce qu'il additionne*.

### F19. Interpénétrations d'une VRAIE pièce — l'ordre de grandeur

Brûleur industriel, 203 solides, **20 503 paires** :

```
pre-filtre par boites englobantes   2,55 s   ->  313 candidates (1,53 %)
intersection reelle des 313         31,7 s   (101 ms/paire, aucune troncature)
paires en interpenetration REELLE   72
volume compte deux fois             2 595 622 mm3 = +0,4200 % = +20,38 kg sur 4 851,3
```

Les plus grosses sont **légitimes** (un piquage qui traverse une paroi : 11,88 kg). Sur un cas
synthétique trop dense, F3 donnait +21,50 % — **la réalité est 50× plus douce**.

⚠️ Le pré-filtre est en **O(n²) naïf** : 2,55 s ici, ~23 s sur une pièce 3× plus grosse. Il lui
faut un index spatial au-delà.

💡 **Les 72 paires qui se touchent sont aussi la liste des soudures à faire.**

### F20. Relevé d'imports STEP — ce qui est universel et ce qui ne l'est pas

Six fichiers, 2026-08-18 :

| fichier | ko | s | objets | à 10¹⁰⁰ | solides (tout) | (feuilles) | double ? |
|---|---|---|---|---|---|---|---|
| `cube_100mm.step` | 7 | 0,03 | 1 | **0** | 1 | 1 | **non** |
| `geometry_out.stp` | 2 | 0,00 | **0** | 0 | 0 | 0 | non |
| `as1-ac-214.stp` | 81 | 0,41 | 98 | **60** | 65 | 18 | **oui** |
| `Escalier_limons_lateraux` | 365 | 0,66 | 84 | 6 | 152 | 76 | **oui** |
| `Escalier_limon_central` | 513 | 1,20 | 137 | 6 | 258 | 129 | **oui** |
| `Bruleur_AP203` | 2 833 | 4,69 | 211 | 6 | 406 | 203 | **oui** |

**Doublement exact (×2) dans les quatre assemblages, absent des deux pièces seules.**
**Entités à 10¹⁰⁰ = 6 × le nombre de nœuds d'assemblage** (1 pour le brûleur, **10** pour as1).

⚠️ **`geometry_out.stp` s'importe en ZÉRO objet sans lever d'erreur.** Un STEP qui ne rend rien est
un cas à traiter, sinon on affiche une scène vide en annonçant un succès.

✅ **Unités** : `cube_100mm.step` rend bbox 100,0 × 100,0 × 100,0 mm et **V = 1 000 000 mm³
exactement**. Les unités traversent juste.

💡 **Un banc d'importateur a besoin d'un ASSEMBLAGE** : une fixture à une seule pièce ne peut
révéler ni F16 ni F18.

### F21. `Face.revolve()` REFUSE net dès que le profil traverse l'axe — et la bascule est au micron

Mesuré le 2026-08-19. Section carrée 100 mm révolutionnée de 90° autour de l'axe Z :

```
R = 52,000 mm  ->  solide OUI   V = 816 814,1     ecart Pappus -0,00000 %
R = 50,500 mm  ->  solide OUI   V = 793 252,1     ecart Pappus +0,00000 %
R = 50,000 mm  ->  solide OUI   V = 785 398,2     ecart Pappus +0,00000 %   <- tangent a l'axe
R = 49,999 mm  ->  solide NON   OCCError: BRep_API: command not done
R = 45,000 mm  ->  solide NON   OCCError: BRep_API: command not done
```

> **Tant que le profil reste du même côté de l'axe, Pappus est EXACT — +0,00000 % à cinq rayons.**
> Dès que son bord intérieur passe de l'autre côté, OpenCascade **refuse de fermer le solide.**

✅ **C'est le bon mode d'échec** : une exception franche, pas un solide invalide ni un volume
plausible. À opposer à F1 (`setBiNormalMode` rend un solide **invalide** sans rien dire) et à F3
(`Compound.Volume` rend une somme fausse sans rien dire).

⚠️ **Ne pas transporter cette borne sur un BALAYAGE** : `revolve` et `MakePipeShell` sont deux
opérations différentes. La limite « le profil ne traverse pas le centre de courbure » est
géométrique et vaut pour les deux, mais **le comportement au-delà n'est pas garanti identique** —
à mesurer séparément.

### F22. 🔴 `MakePipeShell` ne refuse PAS un coude impossible — il rend un solide INVALIDE

Le pendant de F21, mesuré le 2026-08-19. Même géométrie (section 100 mm, coude 90°), mais en
**balayage** au lieu de révolution, sur un **vrai arc** :

```
R/c = 2,00 / 1,00 / 0,60   ->  construit, isValid()=True,  volume exact (+0,0000 % Pappus)
R/c = 0,50                 ->  OCCError: BRepOffsetAPI_MakePipeShell::MakeSolid
R/c = 0,49 ... 0,20        ->  CONSTRUIT, isValid()=FALSE, volume = Pappus, exact
```

⚠️ **`revolve` refuse (F21) ; `MakePipeShell` bâtit.** Le solide replié est produit sans exception,
et son `Volume` vaut **exactement** l'intégrale signée — donc un nombre plausible. **Le seul signal
est `isValid() = False`.**

⚠️ **La panne n'est pas monotone** : le cas TANGENT (R/c = 0,50) lève une exception, alors que les
cas nettement impossibles (0,49 et en dessous) passent. Ne pas déduire une borne d'un essai unique.

💡 Même famille que F1 (`setBiNormalMode` : solide invalide, volume faux de 4,9 %) et F18 (somme
d'arbre : masse doublée). **Trois fois, le signal existait et n'était pas lu.** `Shape.isValid()`
n'est pas une formalité de fin de script — c'est parfois la seule chose qui distingue une forme
d'un nombre.

---

### F23. 🔴 `arete.cut(solide)` efface une arête posée SUR la frontière — il rend **0,00 mm**

Pour savoir quelle part d'un contact reste soudable, la tentation est de soustraire la matière
de l'assemblage : `arete.cut(fusion)`. **C'est 55× plus rapide que l'échantillonnage et 100 %
faux.** Mesuré le 2026-08-19 sur un nœud poteau/poutre/gousset :

```
echantillonnage 0,25 mm   expose 2212,0682 mm   8940 points   5,341 s
arete.cut(fusion)         expose    0,0000 mm     15 aretes   0,0964 s
```

Une arête issue de `a.section(b)` est **exactement sur la peau** du solide fusionné, et `cut`
traite la frontière comme de la matière : tout disparaît. Rien ne signale l'erreur — pas
d'exception, un résultat plausible en apparence (« rien n'est accessible »).

> **La bonne forme : ne soustraire que les pièces TIERCES.** Une arête produite par la paire
> (A, B) ne peut être enterrée que par une troisième pièce ; A et B la *portent*.

```python
tiers = [s for k, (_, s) in enumerate(pieces) if k not in (i, j)]
reste = e
for s in tiers:
    r = reste.cut(s)
    reste = r if r.Edges else None
```

Exact, et **95,3 × plus rapide** que l'échantillonnage — **0,0559 s contre 5,3241 s, mesurés
dans LA MÊME course**, 7 tirs chacun, estimateur du tiers bas.
⚠️ J'avais d'abord publié **104 ×** en comparant un chrono frais à un chrono **d'une autre
exécution** : sur une machine partagée, ça ne vaut rien. Voir **F31**.
Implémenté dans `labo-dao/patrons.py` → `cordons_exposes()`.

---

### F24. `Shape.isInside` coûte **597 µs par point** — l'échantillonnage ne passe pas à l'échelle

Mesuré : 8 940 points en 5,341 s. Et **la réponse dépend du pas**, ce qui la rend impropre à
un contrôle de régression :

| pas | longueur exposée |
|---|---|
| 2,00 mm | 2 211,8880 mm |
| 0,50 mm | 2 212,5687 mm |
| 0,25 mm | 2 212,0682 mm |
| 0,10 mm | 2 212,1683 mm |

Étalement de 0,68 mm, soit 0,03 % — stable, mais jamais exact. Le booléen sur les tiers (F23)
donne 2 212,0800 mm **sans pas d'échantillonnage**.

⚠️ **Ordre de grandeur à connaître avant d'en poser un** : une charpente de 200 membrures avec
~400 contacts de 500 mm échantillonnés à 0,25 mm demande 800 000 appels ≈ **8 minutes**.

---

### F25. Le namespace du pont est **PERSISTANT** — `import` rend un module PÉRIMÉ

`freecad_exec` et `run_fc.py` partagent un espace de noms qui survit d'un appel à l'autre.
C'est ce qui rend l'exploration agréable — et c'est un piège dès qu'on édite un module :

```python
import patrons          # <- rend la version CHARGEE AU PREMIER APPEL, pas celle du disque
```

Symptôme vécu : une assertion ajoutée au banc ne s'exécutait pas, et le banc annonçait
sereinement « 7 vérifications passées » — l'ancien compte, sur l'ancien code. Aucune erreur.

```python
import importlib, patrons
importlib.reload(patrons)      # obligatoire apres toute edition
```

> C'est la même famille que **F18** et que la faute d'attribution mesurée le 2026-08-19 :
> *une mesure juste, rapportée au mauvais état de la cible.*

---

### F26. ✅ *(corrigé dans le pont)* Un seul caractère non-ASCII tuait tout le bilan

`run_fc.py` imprimait `stdout` à travers la console Windows en **cp1252** : un `⚠`, une flèche
ou un degré levait `UnicodeEncodeError` **après** que le script ait tourné — le travail était
fait, l'affichage perdu. Corrigé le 2026-08-19 par `sys.stdout.reconfigure(encoding="utf-8",
errors="replace")` dans `run_fc.py`. Vérifié : `⚠ → ° é` passent sans `PYTHONIOENCODING`.

---

### F27. Le coût d'un booléen est **LINÉAIRE** en faces — et les trois opérations coûtent pareil

Mesuré le 2026-08-19, deux prismes à n côtés qui se recouvrent, n de 3 à 256 (topologie identique
à tout n, donc SEULES les faces varient) :

```
fuse    t = -0,0225 + 1,578e-3 x faces   s    exposant mesure 0,9875
cut     t = -0,0299 + 1,534e-3 x faces   s    exposant mesure 1,0384
common  t = -0,0195 + 1,417e-3 x faces   s    exposant mesure 1,0471
```

**Trois opérations indépendantes, trois exposants qui encadrent 1.** Et le modèle linéaire bat le
modèle puissance sur le `t` brut les trois fois (R² 0,967/0,968/0,982 contre 0,931/0,932/0,971).

⚠️ **Choisir `common` plutôt que `fuse` ne gagne que ~10 %.** Il n'y a pas d'opération booléenne
bon marché à préférer.

⚠️ **La PENTE dépend de la géométrie, pas la loi** : 1,58 ms/face ici, 0,388 ms/face sur d'autres
formes la veille — un facteur 4. Transporter la loi, jamais la pente.

🔴 **DEUX FAUTES DE MESURE À NE PAS REFAIRE — je les ai faites toutes les deux le même jour :**

1. **Ne faire varier qu'un opérande.** En fusionnant une boîte CONSTANTE de 6 faces dans un
   accumulateur qui grossit, j'ai mesuré un exposant de **0,810** et publié « sous-linéaire ».
   *Un exposant mesuré en ne faisant varier qu'un opérande décrit le montage, pas l'opération.*
2. **Comparer un R² log-log à un R² linéaire.** Mon 0,9733 était ajusté en log ; le 0,9935 qu'il
   « battait » était en linéaire. **Deux R² calculés dans des espaces différents ne se comparent
   pas.** Ajuster les deux modèles sur le même jeu et les noter sur la grandeur BRUTE.

⚠️ **Et pour un volume, le calcul fermé donne la même réponse à 2,7·10⁻¹⁵ en microsecondes.**
Fusionner 47 barres coûte 30,92 s. Le B-rep prouve la formule une fois ; il ne répond pas à chaque
appel.

---

### F28. 🔴 `run_fc.py --shot` capture la VUE ACTIVE — pas ce que le script vient de construire

**C'est la règle d'or ② retournée contre elle-même.** Un script qui construit des formes avec
`Part.*` sans les ajouter à un document ne change rien à la vue 3D. La capture rend alors **le
modèle précédent**, qui est valide, plausible, et n'a aucun rapport.

Mesuré le 2026-08-19 : un balayage de 4 000 × 20 × 400 mm a rendu une capture montrant un nœud
poteau/poutre/gousset construit **deux heures plus tôt**. Rien ne le signalait — ni erreur, ni
avertissement, et l'image avait l'air d'une confirmation.

> **Une image périmée est pire que pas d'image** : elle a la forme d'une preuve.

Le remède, en tête de tout script destiné à être capturé :

```python
for d in list(App.listDocuments()):
    App.closeDocument(d)
doc = App.newDocument("mon_essai")
...
o = doc.addObject("Part::Feature", "NOM_PARLANT"); o.Shape = s   # sinon rien n'est visible
doc.recompute()
import FreeCADGui; FreeCADGui.SendMsgToActiveView("ViewFit")
```

Et **terminer le bilan par le compte d'objets affichés** — un `0 objets` dans le texte à côté
d'une belle image est le seul signal qui reste.

⚠️ Corollaire : les objets nommés `Part::Feature` prennent un **nom parlant** justement pour que la
capture soit auto-descriptive. Voir aussi **E8** (le suffixe automatique détruit les identifiants).

---

### F29. 🔴 Un tir unique de chronométrage est INUTILISABLE — dispersion mesurée **2,6 ×**

Mesuré le 2026-08-19 : le **même** appel `section()`, relancé, a rendu **13,68 ms** puis
**4,65 ms**. Sur 7 tirs par cas, le rapport max/min atteint **2,6 ×** :

```
cylindre / boite     min  5,05   med 10,95   max 12,98   ->  2,6 x
sphere / cylindre    min  3,73   med  4,48   max  9,82   ->  2,6 x
cylindre / cylindre  min 75,07   med 75,37   max 76,30   ->  1,0 x
```

⚠️ **La dispersion est pire sur les cas RAPIDES** — exactement ceux qu'on compare à un facteur
près. J'ai failli publier « sphère/boîte = 4,7 × la référence » et « = 1,6 × » depuis deux passes
du même script.

🔴 **ET LA RÈGLE « TOUJOURS LA MÉDIANE » EST FAUSSE — je l'ai corrigée le 2026-08-19 même.**
Le bon réducteur dépend de la **forme de la contamination**, et elle se diagnostique en une ligne :

```
sigma sur TOUS les tirs .............. 9,53 %
sigma sur la MOITIE LA PLUS RAPIDE ... 2,82 %      rapport 3,4 x
autocorrelation au decalage 1 ........ +0,025      <-- ⚠ CE CHIFFRE NE VAUT RIEN, voir plus bas
```

🔴 **N'UTILISE PAS L'AUTOCORRÉLATION COMME CRITÈRE À 40 TIRS.** Mesuré par permutation
(2 000 mélanges de la série réelle, 2026-08-19) :

```
ecart-type de r1 sous l'hypothese nulle ... 0,1385
intervalle nul a 95 % ..................... [-0,240 , +0,277]
r1 d'une SECONDE serie, meme code ......... +0,1675   (contre +0,025 la premiere)
```

**Je ne reproduis même pas ma propre valeur**, et les deux sont au fond de l'intervalle nul.
À 40 tirs, `r1` ne détecte qu'une **rafale forte** (|r1| > ~0,28) ; il **ne peut pas certifier
l'absence** de structure temporelle. Il faudrait ~400 tirs pour le resserrer à ±0,05.

> ⚠️ Deux mesures de `r1` proches ne se **confirment** pas l'une l'autre quand elles valent toutes
> deux ≈ 0 : elles rapportent chacune le résultat NUL. Une coïncidence à trois décimales entre deux
> instruments n'est pas une preuve de cause commune.

✅ **Le critère fiable est le RAPPORT DES SIGMA**, lui : 3,4 × et 6,65 × mesurés sur deux moteurs,
très loin de 1. C'est lui qui porte le diagnostic, pas `r1`.

➜ **Rapport > ~2,5 : la contamination est UNILATÉRALE** — une queue de pics lents (préemption CPU),
jamais de tirs anormalement rapides. Le fond stationnaire est à **1,30 %** ; la médiane le noie
dans la queue. Il faut alors une **statistique basse** : minimum, ou moyenne du tiers le plus
rapide.
➜ **Rapport ≈ 1 : dispersion symétrique** — la médiane est le bon choix.

> **Diagnostiquer la forme AVANT de choisir le réducteur.** Sur ma grille, le verdict de
> séparabilité passait de `INDISCERNABLE` à `ÉCART RÉEL` selon ce seul choix.

⚠️ **Le minimum « flatte le cache » — c'est vrai, et ce n'est pas une raison de l'exclure** quand la
contamination mesurée est unilatérale : il est alors l'échantillon le moins contaminé. Ce qui
l'interdit, c'est un effet de **chauffe systématique** (premiers tirs lents par construction), qui
se voit à une autocorrélation forte ou à une dérive monotone.

### F30. 🎯 Le coût de `section()` suit la COURBE d'intersection, pas les surfaces

Même paire sphère + cylindre, seule la position change (2026-08-19, 7 tirs, médiane) :

```
axe passant par le centre   ->  Circle        5,16 ms     3,3 x le tout-plans
axe decentre de 40 mm       ->  BSplineCurve 131,73 ms    85,3 x
```

**Facteur 25,5 sans changer une seule surface.** Idem cylindre/cylindre : parallèles
(`Circle`+`Line`) **17,99 ms**, gauches (`BSplineCurve`) **117,73 ms**.

> Dès qu'OpenCascade doit rendre une **`BSplineCurve`** au lieu d'une conique analytique, le coût
> est multiplié par **15 à 25**.

✅ **Et ça se diagnostique après coup, sans profileur** :

```python
types = {e.Curve.TypeId for e in forme.section(autre).Edges}
# 'Part::GeomBSplineCurve' present  ->  tu paies ~20 x
```

Sur des polyèdres la loi en faces est **linéaire** (exposant remesuré **1,0002**, 0,738 ms/face),
mais ⚠️ la **pente dépend de la géométrie** : 0,2595 ms/face mesuré la veille sur d'autres formes.
Transporter la loi, jamais la pente. Voir **F27**.


---

### F31. 🎯 CE SONT LES MESURES **COURTES** QUI SONT CONTAMINÉES — la parade est d'allonger, pas de répéter

Mesuré le 2026-08-19, **deux méthodes chronométrées dans la même course**, 7 tirs chacune :

```
le PATRON            56 ms    ->  sigma relatif  7,3 %
l'ECHANTILLONNAGE   5,3 s     ->  sigma relatif  0,4 %
```

**Un facteur 18 sur le bruit relatif, pour la même machine au même instant.** Une mesure longue
moyenne la contention toute seule ; quelques dizaines de millisecondes la subissent en plein.

> ➜ **Ne chronomètre jamais une opération de moins d'une seconde.** Répète l'opération **À
> L'INTÉRIEUR** du chronomètre — pas autour de lui — jusqu'à ce que la mesure dure des secondes.

🔴 **ET L'OPÉRATION RÉPÉTÉE DOIT ÊTRE PURE — la règle est fausse sans cette clause.** Mesuré le
2026-08-20 en essayant de la suivre sur une fusion dans un accumulateur qui grossit :

```
F31 tel quel, operation A ETAT ....... 119,06 ms          <- ne decrit AUCUN etat
le vrai cout, etat par etat .......... 37,51 -> 81,64 ms  (18 -> 66 faces)
la moyenne est HORS de la plage, 46 % au-dessus du dernier etat
```

L'accumulateur passe de **26 à 164 faces** pendant la mesure : le chiffre rendu est la moyenne d'un
coût qui a varié d'un facteur **6,3**, et **rien ne prévient**.

> **La parade** : faire avancer l'état **HORS** du chronomètre, et chronométrer une opération
> **pure** à chaque état.
> ```python
> for k in etats:
>     t = chrono(lambda: acc.fuse(cible))   # PUR : on ne reaffecte pas acc
>     acc = acc.fuse(cible)                 # l'etat avance HORS du chrono
> ```

⚠️ *Ce défaut est de la famille que la session A a nommée le 2026-08-19 : **un conseil juste dont
l'application est impossible dans un cas qu'il ne distingue pas.** On ne le voit qu'en ESSAYANT de
suivre le conseil — une relecture le trouve impeccable.*

À 5,3 s le bruit tombe à 0,4 %, et **plus rien de ce qui suit n'a d'importance** : ni le choix du
réducteur (F29), ni le plancher de bruit, ni la charge des autres processus.

⚠️ **Contexte à connaître de ce poste** : la machine porte **2 processus `claude`, 2 Chrome et
FreeCAD sur 4 cœurs logiques**. Deux sessions y chronomètrent en même temps. Aucune mesure de temps
n'y est propre si elle ne dure pas.

⚠️ **Et comparer deux chronos de DEUX COURSES différentes n'a aucune validité ici.** J'ai publié
« 104 × » ainsi ; refait en une course, c'est **95,3 ×**. L'erreur était de 8 % — cette fois. Le
contrôle mécanique est dans `labo-dao/chiffres_en_dur.py` : il détecte les mesures antérieures
recopiées dans un calcul (discriminant : ≥ 4 chiffres significatifs), et il est testé par mutation.

---

### F32. ✅ OpenCascade est **déterministe au bit près** — sauf si l'ORDRE des booléens change

Mesuré le 2026-08-19 sur un modèle à 29 faces (tubes creux + révolution + cylindre oblique,
22 362 795,285304215 mm³) :

```
rejeu x5 dans la MEME session ............ identique au bit pres (9 champs)
rejeu apres KILL + relance du processus .. identique au bit pres (diff mecanique)
ORDRE des fusions change ................. 3 ordres sur 5 DIFFERENT
```

Les écarts d'ordre sont **exactement ±1 et ±2 ULP**, vérifié par `math.ulp` — multiples **entiers**,
résidu nul :

```
math.ulp(V) ............ 3,725290e-09 mm3        ULP relatif  1,665843e-16
ecarts mesures ......... 0, +1, -2, -1, 0 ULP    residu 0,000
topologie .............. 29 faces / 75 aretes / 50 sommets dans TOUS les ordres
```

➜ **Ce n'est pas « du bruit au plancher » : c'est la plus petite différence qu'un double puisse
représenter.** Le pipeline géométrique est exact jusqu'à l'arrondi final ; seul le dernier arrondi
diffère selon l'ordre.

> ✅ **Un script rejoué rend exactement le même solide**, même dans un autre processus. C'est ce
> qui rend une archive de scripts équivalente à une archive de géométrie.
> ⚠️ **Mais ne compare jamais deux modèles construits dans des ordres différents au bit près** :
> ils diffèrent légitimement dans les derniers bits. Compare à une tolérance relative de ~1e-15.

⚠️ **Méthode pour ce genre de test** : écrire la signature dans un FICHIER depuis le script, puis
`diff` — jamais transcrire un chiffre soi-même d'une sortie vers un autre script. Voir
`labo-dao/chiffres_en_dur.py`.

---

### F33. 🔴 Une session de pont VIEILLIE tourne **1,6 à 1,7 × plus lentement** — uniformément

Mesuré le 2026-08-20 par comparaison mécanique (mêmes cas écrits dans un fichier, `diff` ; aucun
chiffre transcrit à la main) entre une session ayant servi toute la journée et un processus neuf :

```
                    session agee   processus neuf   rapport
boite / boite           5,9063 ms       3,6391 ms     x1,62
sphere / cylindre       6,1793 ms       3,6213 ms     x1,71
cylindre / cylindre   128,3694 ms      75,9120 ms     x1,69
sphere / boite          5,5334 ms       3,5255 ms     x1,57
```

**Le ralentissement est UNIFORME** — le même facteur sur des cas allant de 3,5 à 128 ms, soit un
rapport de magnitude de **35**. Ce n'est donc pas du bruit par cas : c'est un **multiplicateur
global du processus**.

État de la session âgée, relevé au moment de la mesure :

```
166 noms vivants dans l'espace de noms du pont
32 formes B-rep retenues (369 faces)      memoire privee 1 585 Mo
```

🔴 **ET LA CAUSE N'EST PAS CE RELEVÉ — je l'avais attribuée sans la mesurer.** Corrigé le
2026-08-20, sur session fraîche :

```
session fraiche .......................... 3,6002 ms
apres 40 SOLIDES RETENUS (400 faces) ..... 3,5918 ms   x0,998   <- AUCUN ralentissement
apres `del` + gc.collect() ............... 3,5977 ms   x0,999   0 objet ramasse
```

**Retenir autant de géométrie que la session âgée en portait ne produit aucun ralentissement.**
Et ~1 650 appels `section()` non plus. Le ralentissement est donc **réel et reproductible**
(×1,6–1,7 par comparaison mécanique avec un processus neuf) mais **son mécanisme n'est pas établi**
— ni la rétention de formes, ni le simple volume d'appels. Une session âgée a fait des heures de
travail VARIÉ : documents ouverts et fermés, rendus GUI, balayages, révolutions, TechDraw.

⚠️ **La version précédente de ce piège conseillait de libérer les formes.** Mesuré : **0 % de
récupération**. Ce conseil est retiré.

> ### Ce qui reste vrai, et c'est ce qui compte
> 1. 🔴 **Un temps ABSOLU n'est pas comparable d'une session à l'autre.** **Redémarrer FreeCAD**
>    avant toute campagne de chronométrage — c'est la seule parade mesurée (~35 s) — et le dire.
> 2. ✅ **Les RATIOS de deux mesures prises CÔTE À CÔTE survivent**, le multiplicateur étant
>    uniforme sur 35× de magnitude.
> 3. ⚠️ **Mais PAS un rapport de mesures prises à des instants ÉLOIGNÉS** — voir la mise en garde
>    de la session A du 2026-08-19 : une dérive monotone et un ordre de visite régulier se
>    composent en un artefact *flatteur*. Il faut **mélanger l'ordre des cellules**.

➜ C'est la même structure que **F27** et **F31** : *la forme se transporte, la constante non.*
Ici la « constante » est l'âge du processus.

---

### F34. 🔴 `Responding=False` NE VEUT PAS DIRE « figé » — la consigne du poste tuerait un calcul légitime

**C'est architectural, pas un défaut** : dans `freecad_bridge.py`, un `QTimer` appelle `_pump`
toutes les 50 ms **sur le thread Qt**, et `_dispatch` y exécute le code. **Toute opération longue
bloque donc l'interface**, et Windows la déclare non-répondante.

Mesuré le 2026-08-20, les deux cas côte à côte :

```
calcul LEGITIME (fusion de 150 membrures)   Responding=False   CPU +10,0 s en 10 s
etat REELLEMENT COINCE                      Responding=False   CPU  +0,1 s en  8 s
                                                               ---------------------
                                                               un facteur 100
```

> ➜ **Le discriminant n'est pas `Responding`, c'est la PENTE du CPU.** Deux échantillons suffisent.

```powershell
$p = Get-Process freecad; $a = $p.CPU
Start-Sleep -Seconds 10; $p.Refresh()
if (($p.CPU - $a) -gt 5) { "IL TRAVAILLE — ne pas tuer" } else { "coince — tuer" }
```

⚠️ **La consigne d'entretien du poste dit « si `Responding=False`, tue-le ».** Prise au pied de la
lettre elle tue une fusion de 200 membrures, qui prend **40 s** légitimement (voir la loi d'échelle
de M50). **Toujours échantillonner le CPU avant de tuer.**

⚠️ **Et l'état coincé a été atteint en TUANT `run_fc.py` pendant une requête longue** (dépassement
du délai de 2 min du client). Le pont a un délai de 300 s côté `_handle`, mais le client, lui, part
sans prévenir. **Le mécanisme exact du blocage n'est pas établi** — je le note comme fait
reproductible, pas comme cause expliquée.
➜ **Parade** : lancer toute mesure longue **en tâche de fond**, jamais dans un appel qui peut
expirer côté client.

---

### F35. Le PLANCHER de bruit d'un rapport : la formule d'indépendance ne vaut que pour des cellules LONGUES

Quand on juge un rapport de plusieurs mesures (une identité, un facteur d'accélération), il faut un
**plancher** en dessous duquel aucun verdict n'est dû. Deux façons de l'obtenir, et elles ne
coïncident pas.

**Par formule** — σ intra-cellule, propagé en quadrature sur les *k* mesures du rapport :

```python
plancher = 100 * math.sqrt(k) * sigma_moyen / math.sqrt(2 * n_tirs / math.pi)
```

⚠️ **Elle suppose les cellules INDÉPENDANTES**, et la dérive du processus les **corrèle** par
l'ordre de visite.

**Par mesure** — plusieurs **permutations** de l'ordre de visite, chacune dans un **processus neuf**
(F33). Mesuré le 2026-08-20, 4 permutations, cellules de 0,1 à 3 s :

```
medians selon la seule permutation ... 1,16   1,67   2,00   4,19 %      etalement x3,6
plancher EMPIRIQUE (moy + 2 sigma) ... 4,93 %
plancher par la FORMULE .............. 5,88 %                            -> x0,84
```

> ➜ Sur des cellules **assez longues**, la formule est **conservatrice** (elle sur-estime de 19 %
> ici). Sur des cellules **courtes** elle sous-estime : la session A mesure un étalement de **×12**
> sur des cellules de **1,2 ms**. **Plus la cellule est courte, plus la dérive domine et corrèle.**

C'est **F31 remontée d'un étage** : la durée de la mesure ne gouverne pas seulement le bruit, elle
gouverne **la validité du modèle de bruit**.

⚠️ 4 permutations, c'est peu pour un écart-type — mon 4,93 % est grossier. Ce qui est certain est
plus étroit : *aucune des quatre ne produit d'écart qui sorte du bruit.*

---

### F36. 🎯 L'erreur de volume d'un maillage suit la **DIMENSION DE COURBURE**, pas le nombre de triangles

Mesuré le 2026-08-20, oracle **analytique** (volume exact en forme close, pas un autre calcul du
même moteur), exposant ajusté sur tous les points :

| forme | courbure | exposant | R² | **triangles pour 0,1 %** |
|---|---|---|---|---|
| cylindre | **1 direction** | **−1,959** | 0,99998 | **320** |
| sphère | **2 directions** | **−0,979** | 0,99996 | **14 750** |
| tore | **2 directions** | **−0,864** | 0,99435 | **43 898** |

**Le mécanisme, et il explique les deux exposants** : la loi de fond est toujours
`erreur ∝ 1/segments²`. Sur une surface **réglée**, le nombre de triangles croît comme les
segments → `1/n²`. Sur une surface à **double courbure**, il croît comme leur **carré** → `1/n`.

> ➜ **Un facteur 137 entre un tube et un coude pour la même précision.** Un GLB de catalogue
> représentant un coude a besoin de **~44 000 triangles** pour peser à 0,1 % près ; un tube s'en
> tire avec **320**.

⚠️ Le maillage **sous-estime toujours** (tessellation inscrite) : tous les écarts mesurés sont
négatifs, de −4,70 % à −0,08 %.

⚠️ **ET LA MÊME LOI FRAPPE UNE RÉVOLUTION FACETTÉE, même quand la FORMULE est exacte.** Le second
théorème de Pappus donne le volume de la révolution **CONTINUE** — vérifié au dernier chiffre
contre `revolve(360)` : 311 017,6727 mm³ des deux côtés. Mais le solide réellement **facetté** en
*n* secteurs plans en diffère :

```
 6 facettes  -17,301 %      24 facettes  -1,138 %
12 facettes   -4,507 %      64 facettes  -0,161 %      (ecart x n2 -> constante)
```

➜ **Une formule paramétrique exacte et un solide affiché faux ne se contredisent pas** : ils
décrivent deux objets. Si quelqu'un pèse le rendu et quelqu'un d'autre applique la formule, les
deux ont raison et les nombres diffèrent — **de 4,5 % à 12 facettes.**

✅ **ET L'ÉCART A UNE FORME CLOSE, INDÉPENDANTE DU PROFIL** :

```
ecart = (n / 2pi) * sin(2pi / n) - 1
```

Vérifié sur **4 profils × 4 facettages** (rectangle, trapèze, L mince, triangle — des centroïdes
très différents) : écart maximal entre la mesure B-rep et la formule **2,2·10⁻¹³ point**.

**Pourquoi l'indépendance est nécessaire, pas fortuite** : le facettage remplace le cercle décrit
par *chaque* point du profil par un polygone inscrit à *n* côtés. Le rapport d'aire d'un polygone
régulier inscrit à son cercle vaut `(n/2π)·sin(2π/n)` **quel que soit le rayon** — donc tous les
points du profil subissent le **même** facteur, et le volume entier avec eux.

| n | écart | | n | écart |
|---|---|---|---|---|
| 6 | −17,301 % | | 24 | −1,138 % |
| 8 | −9,968 % | | 32 | −0,641 % |
| 12 | **−4,507 %** | | 64 | **−0,161 %** |
| 16 | −2,551 % | | 128 | −0,040 % |

---

### F37. ⚠️ `LinearDeflection` est SILENCIEUSEMENT plafonné par `AngularDeflection`

Mesuré le 2026-08-20 sur une sphère R80, `MeshPart.meshFromShape` :

```
   lineaire   angulaire   triangles
      10,00        0,50         304
       1,00        0,50         826
       0,10        0,50       7 964     <- la lineaire mord
      10,00        0,20       2 020
       1,00        0,20       2 020     <- l'ANGULAIRE mord, la lineaire ne fait RIEN
       0,10        0,20       7 964
      10,00        0,05      32 202
       1,00        0,05      32 202
       0,10        0,05      32 202     <- l'angulaire mord TOUJOURS : la lineaire est inerte
```

**Les deux paramètres sont en concurrence et le plus strict gagne.** Qui n'ajuste que
`LinearDeflection` peut se retrouver plafonné sans aucun signal : à `AngularDeflection=0,05`, faire
varier la linéaire d'un facteur **100** ne change **rien** au maillage.

➜ **Toujours faire varier les deux, et vérifier que `CountFacets` bouge**, sinon on croit régler
une finesse qu'on ne règle pas. C'est ce qui rendait mes trois premières déflexions (10 / 5 / 2)
strictement identiques en M54.
