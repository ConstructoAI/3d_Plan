---
name: freecad
description: Piloter FreeCAD par script Python via le pont MCP local — modélisation BIM/Arch (murs, toitures, ouvertures, escaliers, mobilier), quantités, export STEP/glTF/IFC, et mise en plan TechDraw cotée. Use when the user wants to draw, model, or produce technical drawings in FreeCAD, automate FreeCAD from Python, extract quantities from a model, or debug FreeCAD scripting. Contient des pièges d'API vérifiés qui contredisent la documentation en ligne.
user-invocable: true
---

# FreeCAD — pilotage par script

Tout ce document est **vérifié par exécution** contre FreeCAD **1.1.2 / Windows**, sauf mention contraire. Les pièges listés ne sont pas dans la documentation officielle : plusieurs la contredisent.

## 1. Démarrage — automatique

**Il n'y a rien à lancer.** `run_fc.py` et les outils MCP détectent que FreeCAD ne répond pas, le démarrent avec le pont et attendent qu'il soit prêt. Le premier appel d'une session prend une vingtaine de secondes de plus ; les suivants sont immédiats.

```
[pont] FreeCAD ne repond pas — demarrage automatique...
[pont] pret apres ~15 s
```

Lancement manuel si besoin (ou pour avoir la fenêtre ouverte d'emblée) :

```powershell
C:\Dev\freecad-mcp\start_freecad.bat        # ~25 s avant que le port reponde
```

Contrôle en cas de doute : `python C:\Dev\freecad-mcp\test_bridge.py` → doit afficher `=== TOUT EST PASSE ===`. Il indique aussi quelle étape casse si quelque chose ne va plus.

**Si le démarrage automatique échoue**, le message donne le chemin du lanceur et la commande de diagnostic. Causes possibles : FreeCAD désinstallé, ou une instance déjà lancée **sans** le pont — dans ce cas la fermer et repartir du `.bat`.

Binaire : `%LOCALAPPDATA%\Programs\FreeCAD 1.1\bin\freecad.exe` (installation par utilisateur, pas dans `Program Files`). Le `.bat` le détecte seul ; ce chemin sert si la détection échoue.

Environnement : FreeCAD embarque **Python 3.11** ; le serveur MCP tourne dans le Python **3.13** de l'utilisateur. Les deux sont indépendants — installer un paquet dans l'un ne le rend pas visible dans l'autre.

## 1 bis. Deux façons de piloter

### Le chemin garanti : `run_fc.py`

**Il fonctionne toujours**, dès que FreeCAD tourne avec le pont. C'est le mode de travail par défaut.

```powershell
python C:\Dev\freecad-mcp\run_fc.py mon_script.py --shot sortie.png --view iso
```

Un fichier par étape : le script reste sur disque, se relit, se corrige et se rejoue. Après `--shot`, **lire le PNG** — c'est la règle d'or ②.

### Le confort optionnel : les outils MCP

Un serveur MCP `freecad` peut être déclaré, exposant les outils ci-dessous. **Ils ne sont pas toujours disponibles** — une session où ils n'apparaissent pas n'a rien d'anormal, `run_fc.py` couvre tout. Leur avantage : les images arrivent **directement dans la conversation**, sans passer par un fichier.

| Outil | Usage |
|---|---|
| `freecad_exec(code)` | Exécute du Python dans la session. Espace de noms **persistant** entre appels. `App`, `Gui`, `Part`, `Draft`, `Arch`, `Sketcher`, `Mesh`, `Import` déjà importés. |
| `freecad_screenshot(view,…)` | Rend la vue 3D → image visible directement. `view` : iso, front, rear, top, bottom, left, right. |
| `freecad_window()` | Capture la fenêtre entière (arbre, propriétés, vue rapport). Pour **diagnostiquer**, pas pour juger la géométrie. |
| `freecad_inspect(detail,…)` | Objets, volumes, surfaces, boîtes englobantes, validité. `detail="full"` ajoute propriétés et dépendances. |
| `freecad_document(action,…)` | new / open / save / save_as / close / list |
| `freecad_export(path,…)` | Format déduit de l'extension, via le registre FreeCAD |
| `freecad_undo(steps)` | Retour arrière après une erreur de construction |
| `freecad_planches(dossier,…)` | **Mise en plan automatique** : plans par niveau + élévations cotées, SVG + PDF |
| `freecad_status()` | Diagnostic de la liaison — **à appeler en premier en cas de doute** |

S'ils sont là : `freecad_exec` pour l'exploration et les corrections ponctuelles, `freecad_screenshot` pour voir le résultat sans détour par un fichier. Sinon, tout passe par `run_fc.py`.

### Où poser les scripts

Dans un dossier de travail dédié au projet, **jamais** dans le dossier d'installation de FreeCAD ni dans un dépôt source. Par exemple `C:\Dev\<projet>\`. Y enregistrer aussi le `.FCStd` et les exports.

## 2. Les trois règles d'or

**① Sonder l'instance qui tourne, jamais le code source.**
Un dépôt source FreeCAD peut exister sur la machine (par ex. `C:\Dev\FreeCAD-main`, qui est en **26.3.0-dev**) alors que le binaire installé est en **1.1.2**. Ils divergent réellement : des fonctions et des presets présents dans le source **n'existent pas** dans le binaire. Avant d'utiliser une API incertaine :

```python
print(Arch.WindowPresets)                    # liste réelle
print([n for n in dir(TechDraw) if "Dim" in n])
print(o.isDerivedFrom("TechDraw::DrawViewPart"))
```

**② Dessiner, regarder, corriger.** Un script FreeCAD peut se terminer sans la moindre erreur en ayant produit un modèle faux. Lors d'une session réelle, quatre bugs sur quatre n'ont été trouvés qu'**en regardant les captures** — dont des dalles flottant à 5 m du bâtiment, signalées par aucun message. Après chaque étape : capture, lecture de l'image, correction. Ne jamais enchaîner deux étapes sans vérifier.

**③ Mesurer au lieu de supposer.** Quand une géométrie est mal placée, ne pas deviner la convention : afficher les `BoundBox` et comparer au placement demandé. Les conventions de FreeCAD sont irrégulières (voir `references/pieges.md`).

## 3. Méthode de travail

Découper en étapes courtes, un fichier par étape, chacune vérifiée visuellement :

```
01_structure.py   murs + dalles      → capture iso
02_toit.py        toiture            → capture iso
03_ouvertures.py  portes + fenêtres  → capture iso
04_mobilier.py    mobilier           → capture
05_vues.py        visibilité         → captures plans
06_final.py       exports + quantités
```

**La mise en plan ne s'écrit plus à la main.** `C:\Dev\freecad-mcp\planches.py`
(outil MCP `freecad_planches`) analyse le modèle, détecte les niveaux à
l'altitude des murs, bâtit les chaînes de cotes sur les nus de cloisons en
enjambant les épaisseurs, échelonne les cotes qui se recouvriraient, remplit le
cartouche et exporte SVG + PDF. Il **compare chaque cotation à une valeur
calculée** et signale les planches hors échelle.

```python
import sys; sys.path.insert(0, r"C:\Dev\freecad-mcp")
import planches
planches.mise_en_plan(r"C:\Dev\<projet>\plans", echelle=50,
                      elevations=("sud", "nord", "est", "ouest"))
```

Écrire une mise en plan à la main ne se justifie que pour une planche
particulière que le module ne couvre pas (coupe, détail). Les pièges TechDraw
restent utiles à connaître : ils sont tous levés dans `planches.py`, et lire
son code est la façon la plus rapide de les voir à l'œuvre.

Chaque script se termine en affichant un bilan chiffré (nombre d'objets, formes invalides, cotes hors tolérance). **Toujours vérifier `Shape.isValid()`** — une forme invalide se propage silencieusement.

Un exemple complet et fonctionnel de maison à deux étages avec mise en plan cotée se trouve dans `C:\Dev\freecad-mcp\maison\` : structure, toit à 4 versants, 27 ouvertures, 45 meubles, 3 planches A3 à 1:50 avec 25 cotations vérifiées.

## 4. Repères d'API

Unités internes : **millimètres** et **degrés**. Après toute modification : `doc.recompute()`.

| Besoin | Appel |
|---|---|
| Mur | `Arch.makeWall(baseobj, width, height, align="Center")` |
| Étage / bâtiment | `Arch.makeFloor([objs])`, `Arch.makeBuilding([etages])` |
| Toit | `Arch.makeRoof(contour, facenr, angles, run, idrel, thickness, overhang)` |
| Escalier | `Arch.makeStairs(length, width, height, steps)` |
| Fenêtre / porte | `Arch.makeWindowPreset(type, width, height, h1,h2,h3,w1,w2,o1,o2, placement)` |
| Percer le mur | `fenetre.Hosts = [mur]` |
| Plan de coupe | `Arch.makeSectionPlane([objs])` |
| Export universel | `App.getExportType(ext)` → nom de module → `__import__(mod).export(objs, path)` |

Le module bâtiment s'importe sous le nom **`Arch`** (le dossier s'appelle `BIM`, la fonction `Arch.makeWall` vit dans `src/Mod/BIM/Arch.py`).

### Unités impériales

Le contexte de travail est québécois : les demandes arrivent souvent en **pieds-pouces**, FreeCAD ne connaît que les millimètres. Convertir **à l'entrée**, et redonner les résultats dans l'unité de la question.

```python
def pi_po(pieds, pouces=0.0):
    return (pieds * 12.0 + pouces) * 25.4      # -> mm

pi_po(32)        # 9753.6   -> arrondir a 9750 ou 10000 selon l'intention
pi_po(8, 6)      # 2590.8   -> hauteur libre ~2600
```

Repères courants : 8′ = 2438 mm, 8′-6″ = 2591 mm, 2×6 nominal ≈ 140 mm, mur extérieur fini ≈ 250 mm, cloison ≈ 100 mm.
Si l'utilisateur travaille dans Constructo AI, l'outil `cao_pi_po_vers_m` fait déjà cette conversion — s'y référer pour rester cohérent avec ses données.

## 4 bis. Dès qu'il est question d'argent → charger `entrepreneur-qc`

Si la demande porte sur une **estimation, un prix, un budget, une soumission ou
un devis** — y compris quand elle surgit au milieu d'une séance de modélisation
(« et ça coûte combien ? ») — **charger le skill `entrepreneur-qc`** et suivre
son profil métier. Il tient les règles de chiffrage : gamme par défaut,
cost-plus à marge fixe, aires brutes, traitement du garage, contingences, taxes.

Ne jamais improviser un prix à partir d'un modèle FreeCAD. La géométrie donne
les quantités ; le profil entrepreneur donne le prix, et il a des règles
strictes qu'on ne devine pas.

Conversion à connaître : FreeCAD est en **millimètres**, le profil en **pieds
carrés**. `1 pi² = 92 903 mm²`.

```python
# aire brute d'un etage, en pi2, depuis une bbox de modele
pi2 = (bb.XLength * bb.YLength) / 92903.04
```

## 5. Avant d'aller plus loin

**Lire `references/pieges.md`** dès que la tâche touche : le placement d'objets Arch, la visibilité, les ouvertures, ou TechDraw. Ces quatre domaines contiennent des comportements contre-intuitifs qui coûtent des heures s'ils sont découverts en direct.

**Lire `references/recettes.md`** pour des extraits de code fonctionnels — placement de menuiseries centrées dans un mur, plan d'étage par filtre de visibilité, cotation TechDraw fiable.

## 6. Limites à annoncer honnêtement

- **Un processus FreeCAD = une session.** Le noyau porte des singletons non synchronisés (`Base::Type`, `Base::Console`, `SequencerBase`) et le GIL sérialise le recalcul. Pour du parallèle : plusieurs FreeCAD sur des ports distincts via `FREECAD_MCP_PORT`.
- **FreeCAD peut planter** sur une géométrie pathologique. Le pont y survit et le signale ; il faut relancer FreeCAD. Enregistrer souvent.
- **La mise en plan exige l'interface graphique.** `savePDF` / `saveSVG` / `saveDXF` vivent côté GUI et prennent un `ViewProviderPage*`. En mode console (`FreeCADCmd`), l'export PDF des planches est perdu.
- **`freecad_exec` exécute du Python arbitraire** sur la machine hôte. Acceptable en local ; à isoler en conteneur si un jour exposé à des tiers.
