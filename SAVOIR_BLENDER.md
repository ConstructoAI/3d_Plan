# Savoir vivant — Blender 5.2 par scripts : API et rendu

> **Édition publique** (une gracieuseté de Sylvain Leduc, Constructo AI inc.) : noms de clients, adresses et données internes retirés ; les projets de référence portent des noms génériques (« Bungalow », « Agrandissement », « Saint-Exemple »). Certains fichiers cités n'existent que sur le poste d'origine : voir `README.md`, « Ce que le dépôt ne contient pas ».

Sorti de `CLAUDE.md` le 2026-10-10 (le fichier vivant dépassait sa limite de 150 000 caractères) : le texte des
sections est celui d'origine (noms rendus génériques, passages internes retirés).
**À lire AVANT** d'écrire ou de corriger un script Blender (modèle, matériaux, caméra, Line Art, compositeur) et
avant de lancer ou de juger un rendu (EEVEE, Cycles, Freestyle, studio).
**À enrichir** à la fin de chaque session : les pièges vérifiés et les durées mesurées de ce sujet vont ICI, plus dans
`CLAUDE.md`. Corriger ou retirer ce qui devient faux.
Voir aussi :
`SAVOIR_DAO_DWG.md` (plans tirés du modèle).

## Pièges vérifiés — API Blender 5.2

- Moteur EEVEE : `"BLENDER_EEVEE"` (plus de `BLENDER_EEVEE_NEXT`). Un nouveau matériau a déjà son arbre de nœuds ;
  `Material.use_nodes` est déprécié (avertissement).
- **`ShaderNodeMix`** : sockets homonymes par type → passer par les identifiants `Factor_Float`, `A_Color`, `B_Color`,
  sortie `Result_Color`.
- Principled : `Base Color, Metallic, Roughness, Specular IOR Level, Transmission Weight, Subsurface Weight,
  Emission Color, Coat Weight`… Ciel : `SINGLE_SCATTERING, MULTIPLE_SCATTERING, PREETHAM, HOSEK_WILKIE` (plus de NISHITA).
- Looks AgX : `"AgX - Medium High Contrast"`, `"AgX - Punchy"`… (énumération dynamique : `enum_items` ne montre que NONE ;
  un `look="xxx"` invalide liste les valeurs dans le message d'erreur).
- Booléens en arrière-plan : modificateur `BOOLEAN`, `operand_type="COLLECTION"`, puis figer avec
  `bpy.data.meshes.new_from_object(ob.evaluated_get(depsgraph))` (pas besoin de contexte d'opérateur).
- bmesh : `create_icosphere(radius=)`, `create_cone(radius1=, radius2=, depth=, segments=, cap_ends=)`,
  `create_grid(x_segments=, y_segments=, size=)` ; `recalc_face_normals` sur des pièces fermées.
- **Particules « cheveux » rendues en objets : échelle de l'instance = `particle_size × hair_length`** → `hair_length=1`.
  `rotation_mode="NOR"` : ⚠️ deux constats contradictoires, à trancher par un essai dédié.
  - Maison québécoise : axe X de l'instance sur la normale, feuilles modélisées dans le plan YZ, rendu correct.
  - Agrandissement, 2026-09-24 : l'agent a mesuré l'axe **Y** local sur la normale, en lisant les matrices de
    `depsgraph.object_instances` pour des brins d'herbe.
  Le gabarit peut rester à z=-100 (l'emplacement du gabarit est ignoré). `display_percentage` allège la vue 3D.
- Textures « legacy » (`bpy.data.textures.new(..., "CLOUDS")`) + modificateur DISPLACE : fonctionnent toujours.
- Monde : le nœud Light Path « Is Camera Ray » marche en Cycles mais **est ignoré par EEVEE** pour le fond.
- Perspective architecturale à 1 point (comme une illustration) : caméra `rotation=(90°,0,0)` et
  `shift_x/y = (Δ/profondeur) × (focale/largeur_capteur)`.
- Régler la vue 3D en arrière-plan (sauvée dans le .blend) : `bpy.data.screens` → aires `VIEW_3D` →
  `space.shading.type="MATERIAL"`, `region_3d.view_perspective="CAMERA"`. Sauver avec `compress=True`.
- Cycles GPU : `prefs=bpy.context.preferences.addons["cycles"].preferences ; prefs.compute_device_type="CUDA" ;
  prefs.get_devices()`. L'avertissement « HIPEW initialization failed » est sans conséquence.
- `ParticleSettings.use_render_emitter` n'existe plus (AttributeError) : cacher l'émetteur avec
  `ob.show_instancer_for_render = False` (et `show_instancer_for_viewport`).
- Une texture procédurale sans vecteur branché prend les coordonnées « Generated » (boîte englobante de l'objet) :
  sur un terrain de 1 400 m, le gravier devient énorme → brancher `ShaderNodeNewGeometry.Position` (échelle en 1/m).
- Objet texte → maillage en arrière-plan : `new_from_object(ob.evaluated_get(dg))` puis `me.transform(matrix_world)`.
- Attributs de sommets `FLOAT_VECTOR` sur `POINT` (`foreach_set("vector", …)`), lus par le nœud Attribute : masques de
  matériau liés à la géométrie (ex. herbe au bord des tabliers), OK en Cycles. `ShaderNodeMapRange` : entrées par
  identifiant (`Value`, `From Min`, `From Max`, `To Min`, `To Max`), sortie `Result`.
- Mesurer un objet dans l'image : projeter TOUS ses sommets (min/max) avec `world_to_camera_view` à la résolution de
  la photo ; un point choisi au jugé a donné un faux écart de 12 px.
- **Pas d'exporteur Freestyle SVG** dans 5.2 (seul `io_curve_svg`, un importeur). **Line Art existe** :
  `bpy.data.grease_pencils.new()` (type `GreasePencil`, v3) + `ob.modifiers.new(..., "LINEART")`
  (`source_type, target_layer, target_material, use_contour, use_crease, use_intersection, use_material, use_edge_mark,
  crease_threshold, use_loose`).
- **Objets créés par script** : `matrix_world` n'est à jour qu'après `bpy.context.view_layer.update()`. Sans cet
  appel, un contrôle lancé dans la même session voit les instances à l'origine (93 511 fausses paires coplanaires).
- **Rendu de catalogue recadré** (brûleur) :
  - laisser le point principal LIBRE au calage : les coins d'une boîte s'ajustent à tout, ce sont les rapports
    d'ellipses et les points de fuite qui le fixent ;
  - décentrement (`sensor_fit` HORIZONTAL) : `shift_x = 0.5 − px0/W` et `shift_y = (py0 − H/2)/W` (0,8 px près) ;
  - direction d'une pièce : comparer la pente sous-pixel de ses arêtes à celle de chaque point de fuite. L'axe du
    ventilateur se révélait selon X, et non selon Y comme lu à l'œil.
- **Rétroprojeter un pixel sur le plan de POSE de la pièce**, jamais sur un plan voisin : 2,5 po d'écart de plan, sur
  une face vue de biais, laissaient des tubes dans le vide (4 px). Un plan horizontal proche de la hauteur de la
  caméra est mal conditionné.
- **Prouver qu'une pièce reste cachée** : `scene.ray_cast(depsgraph, o, d)` pour chaque pixel. Les directions se
  tirent de `cam.data.view_frame(scene=sc)`. Environ 2 min pour 651 × 658 px.
- ✅ **Compositeur 5.2** (escalier, 2026-09-28) :
  - il se branche par `scene.compositing_node_group` (un `CompositorNodeTree`), plus `interface.new_socket(...)` et un
    `NodeGroupOutput` ;
  - `CompositorNodeComposite`, `MixRGB` et `Math` n'existent plus : `ShaderNodeMix` et `ShaderNodeMath` marchent dans cet
    arbre ;
  - les menus se règlent par leur nom affiché (« Fog Glow », « White Point »).
  - Le compositeur voit l'image AVANT l'exposition de la vue : à +5 EV, un seuil de halo touche tout l'intérieur.
    Post-production à part, sur les images brutes (`post_production.py` de l'escalier, 4 à 8 s par image, processeur).
  - Nœud File Output : `format.media_type = "IMAGE"` AVANT `file_format = "PNG"`.
- ✅ **Balance des blancs** :
  - `view_settings.use_white_balance`, `white_balance_temperature` et `_tint` ;
  - Color Balance en Lift/Gamma/Gain vire au bleu pour un rien : prendre le mode « White Point ».
  - Essayer des réglages de vue sans refaire le rendu : `bpy.data.images["Render Result"].save_render(chemin, scene=sc)`.
- ✅ **EEVEE Next, intérieur** :
  - `bpy.ops.object.lightprobe_cache_bake(subset="ALL")` fonctionne en `-b` (46 à 69 s). Sans sonde volumique, l'image
    sort plate et bleue ;
  - feuilles : `material.thickness_mode = "SLAB"` ; globe de verre : `Thin Wall` ;
  - un verre transmissif montre la sonde du monde, donc le ciel : une sortie de matériau EEVEE à part ;
  - « Shadow buffer full » : `eevee.shadow_pool_size = "1024"`.
- ✅ `ShaderNodeMix` : `n.inputs["A_Color"]` lève une KeyError, car la clé est le NOM. Utiliser
  `next(s for s in n.inputs if s.identifier == "A_Color")`. `bmesh.ops.bevel` refuse une arête passée deux fois :
  `dict.fromkeys(aretes)`.
- ✅ **Fausse postérisation** : Read affiche un grand PNG 8 bits avec des aplats qui n'existent pas dans le fichier. Juger
  à 1:1, sur un recadrage Pillow.

## Pièges vérifiés — rendu

- ✅ **Détecteur de faces coplanaires SANS rendu** : `modeles\rendu_controles\verifier_coplanaires.py` (il démarre Blender lui-même)
  (`blender -b --factory-startup --python build_garage.py --python verifier_coplanaires.py`, environ 15 s).
  - Il liste les paires de faces dans le même plan qui se recouvrent, leur sens et leur visibilité.
  - Garage : 52 paires de même sens (19 visibles) → 0.
  - Tolérance 0,3 mm (à 1,5 mm, les couches minces réelles sortent à tort). Tester pièce par pièce.
  - Une pièce CACHÉE dont les bouts affleurent les bouchons de la pièce qui la couvre (rail dans un capot) donne un
    carré noir pur : l'œil l'a pris pour une ouverture. Raccourcir les pièces cachées d'au moins 1 po ; décaler les
    recouvrements de 0,1 à 0,5 po, jamais au nu.
- **Cycles noircit les faces coplanaires qui se chevauchent** (ombres auto-intersectées) : planches cornières superposées,
  poutres qui se croisent, faîtière au nu de la rive, linteau posé sur les montants, dessus d'un poteau = dessus du chapiteau.
  Toujours décaler (≥ 1 cm) ou rendre les pièces jointives. EEVEE ne montre pas le défaut : vérifier en Cycles avec des
  gros plans au téléobjectif depuis la caméra de rendu.
- Freestyle : exclure la végétation par `lineset.select_by_collection` + `collection_negation="EXCLUSIVE"` ; les gabarits
  d'instances doivent être **dans** la collection exclue ; **subdiviser un grand plan de sol** (sinon des arêtes sous le sol
  sont dessinées) ; EEVEE + Freestyle a produit un coin noir → Cycles + Freestyle est plus propre.
- Arbres crédibles : couronne continue (icosphère subdiv 5 déformée par 2 bruits) + feuilles en particules posées à plat ;
  des amas de sphères donnent un effet « chou-fleur ».
- **Rendu comparable à une photo** (garage, Cycles) : soleil 8,5 ; ciel d'éclairage 0,6 teinté bleu, fond caméra à 1,1
  (Is Camera Ray) ; AgX Medium High Contrast, exposition 0,2. Comparer par **médianes de zones** avec Pillow
  (rouge au soleil, façade à l'ombre, portes, ciel) ; EEVEE ne suffit pas pour juger.
- **Cycles plus rapide** : 6 rebonds au total, 3 en diffus, 3 en brillant, seuil adaptatif 0,02. La vue 1600×1205 à
  128 échantillons passe de 201 s à 114-152 s. Lot de 5 vues ≈ 10 min ; gros plan 600×450 @64 ≈ 30-46 s.
  Scène du garage : 3-7 s de construction (terrain de 179 000 sommets, 1,6 M de feuilles instanciées).
- **Studio blanc de catalogue** (brûleur) :
  - transformée « Standard », exposition -0,8 en EEVEE et -0,6 en Cycles. Avec AgX à 0, le fond sort gris (201) ;
  - cyclorama dont l'émission croît avec Z. En Cycles, la multiplier par « Is Camera Ray », sinon elle inonde l'objet ;
  - pièce à l'ombre d'un porte-à-faux : spot sur la droite caméra-pièce. Sa réponse est linéaire en watts, donc
    2 essais suffisent ;
  - un réglage de couleur fait en demi-résolution à 64 échantillons dérive de 3 à 5 % en pleine résolution à 128.
- **L'IoU des silhouettes ne voit PAS les défauts intérieurs** : une plaque masquait la volute avec une IoU de 0,92.
  - Toujours ajouter un tableau de repères INTÉRIEURS projetés (33 repères, 5 px au plus).
  - Mesurer les repères par code (centroïde des pixels blancs d'un cadran), jamais contre son propre relevé, sinon
    le contrôle est circulaire.
  - Silhouette exacte : `view_layer.material_override` avec une émission noire, un monde blanc, 1 échantillon.
  - Masque de la photo : l'ombre au sol est un gris neutre (saturation 0-8, luminance 165-235), à ne compter comme
    fond que sous l'objet.
- **Durées mesurées (brûleur, 59 000 sommets)** :
  - Cycles CUDA à 128 échantillons : 1302 × 1316 en 125 à 157 s, 1600 × 1200 en 134 à 193 s, 5 vues en 12 à 14 min ;
  - EEVEE : 3 à 10 s par vue ; gros plan 600 × 450 à 32 échantillons : 15 à 26 s ;
  - un Chrome d'une AUTRE session prenait 47 % du GPU et a doublé un rendu : regarder `nvidia-smi` avant de juger
    une durée.

