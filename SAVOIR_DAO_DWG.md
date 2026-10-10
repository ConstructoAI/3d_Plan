# Savoir vivant — DXF, DWG et plans 2D cotés (ezdxf, ODA, Line Art, présentations, aperçus)

> **Édition publique** (une gracieuseté de Sylvain Leduc, Constructo AI inc.) : noms de clients, adresses et données internes retirés ; les projets de référence portent des noms génériques (« Bungalow », « Agrandissement », « Saint-Exemple »). Certains fichiers cités n'existent que sur le poste d'origine : voir `README.md`, « Ce que le dépôt ne contient pas ».

Sorti de `CLAUDE.md` le 2026-10-10 (le fichier vivant dépassait sa limite de 150 000 caractères) : le texte des
sections est celui d'origine (noms rendus génériques, passages internes retirés).
**À lire AVANT** de produire ou de corriger un DXF, un DWG, un jeu de plans 2D ou son PDF.
**À enrichir** à la fin de chaque session : les pièges vérifiés et les durées mesurées de ce sujet vont ICI, plus dans
`CLAUDE.md`. Corriger ou retirer ce qui devient faux.
Voir aussi : « Préférences » de `CLAUDE.md` (calques, unités, PLAN PDF TOUJOURS, PDF 3D), `SAVOIR_LECTURE_PLANS.md` § 7
(standard du plan 2D détaillé).

## DXF / DWG avec ezdxf (vérifié)

- 3D : entités **MESH** (`msp.add_mesh()` + `with mesh.edit_data() as d: d.vertices=...; d.faces=...`), couleur vraie
  `mesh.rgb=(r,g,b)`. Trianguler les n-gones > 4 avant export. `doc.audit()` pour valider (0 erreur attendue).
- En-tête : `$INSUNITS=1, $LUNITS=4, $MEASUREMENT=0, $LUPREC=4` (pouces, architectural, 1/16").
- Vue d'ouverture : `for vp in doc.viewports.get_config("*Active"): vp.dxf.direction/target/height/render_mode`.
- Vérifier un DXF sans AutoCAD : le relire (ezdxf) → OBJ + MTL → import Blender (`bpy.ops.wm.obj_import`) → rendu iso.
- **Export 3D par collections** (`modeles\rendu_controles\exporter_autocad.py`, générique ; complet : `modeles\projet_bungalow\exporter_autocad.py`) : 12 s pour le garage.
  - Exclure les collections non exportées (`layer_collection.exclude = True`) AVANT `evaluated_depsgraph_get()` :
    le terrain et 1,6 M de feuilles ne sont alors jamais évalués.
  - DWG du garage : 50 MESH, 6 956 sommets, 0,40 Mo (le texte de l'affiche pèse à lui seul ~5 100 sommets).
- Vue d'ouverture OMBRÉE en DWG : ODA remet `render_mode` à 0 si la vue n'a pas de style visuel → poser
  `vp.dxf.visual_style_handle = doc.rootdict["ACAD_VISUALSTYLE"]["Shaded"].dxf.handle`.
- OBJ de vérification : couleurs `Kd` du MTL en LINÉAIRE (sinon Blender éclaircit) ;
  `obj_import(forward_axis="Y", up_axis="Z")`.
- Objets inventés hors champ (poteau électrique du câble, par ex.) : les exclure du DWG. Ils flottent et gonflent
  les étendues, et donc le « zoom étendu » du module CAD de l'ERP.
- **aspose-cad 26.6** est dans le Python du poste (copié dans `outils\python`) : c'est un 2e lecteur DWG, indépendant
  d'ODA, pour recouper.
- **ODA File Converter injecte dans TOUT DWG** un DETAILVIEWSTYLE « Imperial24 » et un SECTIONVIEWSTYLE qui
  contiennent des gabarits `%<\AcVar ViewType…>%`. Ce sont des objets AutoCAD standards, pas des FIELD : sans
  conséquence.
- `$EXTMIN/$EXTMAX` : ezdxf écrase ces variables d'en-tête à l'enregistrement (±1e20). Renseigner
  `msp.dxf.extmin/extmax` à la place.
- Une cote dont les points sont saisis à l'envers met son texte SOUS la ligne.
- `ezdxf.new(setup=False)` laisse `$DIMSTYLE` pointer sur « ISO-25 », qui n'existe pas (ODA le remplace par Standard,
  décimal) : désigner le style architectural comme style courant.
- **Propriétés du DWG** : `doc.header.custom_vars.append(clé, valeur)` survit à ODA. Y écrire l'empreinte des sources
  (sha256, 12 caractères), la même dans le 2D et le 3D : la Règle 5 entre eux devient automatique.
- DWG relu :
  - `MESH.vertices` sont des tableaux numpy (`v[0]`, pas `v.x`) ;
  - `Matrix44(*lignes)`, et une matrice Blender se transpose.
- Poids d'un MESH en R2018 : environ 67 octets par sommet, donc 12 Mo ≈ 180 000 sommets.
- **« Aucune pièce flottante » dans un DWG** :
  - recharger ses MESH dans Blender ;
  - îlots de géométrie (union-find), puis `BVHTree` (`overlap`, `find_nearest`, parité de `ray_cast`) de proche en
    proche jusqu'au sol ;
  - valider par un contre-essai (retirer un support).
- aspose-cad sans licence ne lit que 100 entités : inutile pour recouper un gros DWG. Un DWG lu PENDANT qu'un autre
  agent l'écrit donne l'ancienne version.
- ✅ **DWG 3D pour l'afficheur de l'ERP (`/cad`)**, mesuré le 2026-09-28 sur son vrai afficheur :
  - **arêtes vives** : l'afficheur calcule ses normales en faisant la moyenne des faces autour de chaque sommet ;
    - des sommets soudés à travers une arête vive donnent un rendu « en coussin » ;
    - nos exportateurs dédoublent maintenant les sommets aux arêtes de plus de 30° (`--angle-pli`, 180 = ancienne
      soudure), pour environ +25 octets par sommet ajouté (+35 à +60 % de poids) ;
    - un MESH dédoublé n'est plus connexe par ses indices : ressouder par position avant de chercher des îlots ;
  - **verre** : `mesh.transparency` de 0,65 à 0,70 (code 440, relu par ODA sur 8 bits). L'afficheur la rend ;
  - **couleurs** : poser le matériau « Global » « par objet » (`doc.materials.get("Global").dxf.diffuse_color_method =
    0`), sinon l'afficheur de production (avant correction) peint tout en gris. ezdxf crée ce matériau avec un
    diffus forcé à blanc ;
  - **copie de présentation** : éteindre l'enveloppe (MURS-EXT, PLAFONDS, OUVERTURES, VITRAGE) dans une COPIE déposée
    dans l'ERP, pour que l'escalier se voie à l'ouverture. Le livrable local reste complet.

## Plans 2D cotés depuis le modèle 3D (vérifié — `plans_autocad.py`)

- **Élévations = Line Art** (lignes cachées supprimées) : `gpd=bpy.data.grease_pencils.new(n)` ;
  `gpd.layers.new("Traits").frames.new(scene.frame_current)` ; matériau `bpy.data.materials.create_gpencil_data(mat)` ;
  modificateur `LINEART` (`source_type="SCENE"`, contour/crease/intersection/loose, `crease_threshold=radians(145)` :
  les versants courbes restent lisses, les boîtes donnent leurs arêtes). Caméra **ORTHO** par vue ; après chaque
  changement de caméra : `gp.update_tag(); view_layer.update()`, puis lire
  `gp.evaluated_get(dg).data.layers[].frames[].drawing.strokes[].points[].position` et projeter (avant (x,z),
  arrière (-x,z), gauche (-y,z), droite (y,z)). 4 vues ≈ 13 s. Exclure la végétation (`layer_collection.exclude`),
  couper sous le sol, simplifier (Ramer-Douglas-Peucker 1 mm). **Un cylindre lisse perd ses contours** → le remplacer
  par une boîte avant le calcul.
- **Cotes ezdxf** : le rendu ezdxf ignore `dimlunit=4` (texte décimal « 346,4567 ») → passer `text=` avec un
  formateur pieds-pouces maison (au 1/16, forme `10'-0 11/16"`). Flèches `ds.set_arrows(blk=ezdxf.ARROWS.architectural_tick)`.
  Styles de cote : `dimscale` 48 (1/4"=1'-0") ou 64 (3/16"=1'-0"), `dimtxt=dimasz=3/32`.
- **Présentations** : `doc.layouts.new(nom)` + `page_setup(size=(36,24), units="inch")` +
  `add_viewport(center, size, view_center_point, view_height=hauteur_papier × échelle)` ; calque des fenêtres
  `plot=0` ; supprimer la présentation vide « Layout1 ». Feuille ARCH D : 4 élévations tiennent à 3/16", pas à 1/4".
- **Aperçus PNG** : `ezdxf.addons.drawing.matplotlib.qsave(layout, png, bg="#1F2329",
  config=Configuration(color_policy=ColorPolicy.COLOR))` (fond sombre comme AutoCAD ; `MONOCHROME_LIGHT_BG` rend le
  jaune et le cyan illisibles). La police de l'aperçu est plus large qu'Arial : prévoir de la marge pour les notes.
- `build_maison_quebecoise.py` remplit la liste globale **`OPENINGS`** (nom, type, position, mur, largeur, hauteur) :
  le plan s'en sert. Les murs du modèle sont pleins : le plan suppose des murs de 8".
- **Plans dessinés depuis les paramètres** (garage, `plans_garage.py`, environ 30 s, 1 118 entités dont 78 cotes) :
  - Bâtiment long sur ARCH D : **tourner le plan de 90°** permet le 1/4". Choisir l'échelle en mesurant ce qui est
    dessiné (`ezdxf.bbox.extents`), en essayant 1/4 puis 3/16 puis 1/8.
  - Types de ligne : les motifs de `ezdxf.new(setup=True)` sont métriques. Avec les motifs impériaux d'acad.lin,
    `$LTSCALE=24` et `$PSLTSCALE=0` donnent des tirets de 1/4" au 1/4".
  - L'aperçu ezdxf d'une **présentation** ignore les types de ligne vus par une fenêtre (tout sort continu) : découper
    les tirets dans une COPIE réservée à l'aperçu.
  - L'aperçu ne rend pas le masque d'un MTEXT (`set_bg_color`) mais rend celui du texte des cotes (`dimtfill=1`).
    Sur des nervures ou une hachure : TEXT, plus trou dans la hachure (`add_polyline_path(..., flags=0)`).
  - Largeur réelle d'un texte : `ezdxf.fonts.fonts.make_font("arial.ttf", h).text_width(s)`, plus 12 % pour l'aperçu.
  - La fenêtre principale de chaque présentation ezdxf (id 1) est sur un calque `VIEWPORTS` non déclaré, qu'ODA crée
    blanc et imprimable. Mettre TOUTES les fenêtres sur un calque déclaré `plot=0` (ex. `FENETRES-PRES`).
  - Petites cotes : ezdxf repousse leur texte sur les lignes d'attache. Toujours appeler `set_location()`
    (`leader=True` pour un texte déporté avec ligne de repère), et trier p1 → p2, surtout sur un plan tourné.
  - Ouvrir le DWG sur une feuille : `$TILEMODE=0` + `doc.layouts.set_active_layout(nom)`.
    Verrouiller une fenêtre : `vp.dxf.flags |= 0x4000`.
  - Hachure trouée : l'aperçu dessine encore le motif dans les îlots. Découper en rectangles juxtaposés, et créer
    les cotes APRÈS la hachure.
  - Les scripts n'écrasent jamais un DXF/DWG ouvert ou modifié à la main : ils écrivent `_v2` à côté.
- **Plan d'équipement tiré du modèle** (brûleur, `plans_bruleur.py`, 3 à 6 min, Line Art de 6 vues en 27 s) :
  - **Line Art par collection** : un modificateur en source SCÈNE, puis un par collection (`source_type="COLLECTION"`,
    `use_cache=True`). La somme est exacte, en un seul calcul. `collection.lineart_usage` perd les intersections
    entre collections ;
  - `stroke_depth_offset` vaut 0,05 m par défaut : le mettre à 0 pour attribuer les points aux objets. Et
    `use_crease_on_smooth=True`, sinon les pièces lissées perdent leurs arêtes ;
  - lecture rapide : `drawing.attributes["position"].data.foreach_get("vector", a)` et
    `drawing.curve_offsets.foreach_get("value", a)` ;
  - vue isométrique : caméra orthographique de rotation (54,7356°, 0, 45°) ;
  - cotes hors tout : lignes d'attache depuis le point VISIBLE extrême des traits (ici un manomètre), pas depuis les
    coins de la boîte englobante ;
  - rappels et bulles : grille d'occupation avec le propriétaire de chaque case ; pénaliser le franchissement d'un
    autre repère ou d'une cote. Le texte d'une cote de diamètre n'est pas centré : mesurer sa boîte sur un rendu de
    brouillon ;
  - aperçu : `draw_layout(finalize=True)` réduit la figure → `fig.set_size_inches(36, 24)`, puis `savefig(dpi=110)` ;
  - un script de modèle en argparse refuse les options inconnues après `--` : passer celles d'un script enchaîné par
    variables d'environnement.

