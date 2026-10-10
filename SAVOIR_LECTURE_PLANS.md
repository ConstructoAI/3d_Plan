# Savoir vivant : lire un plan, en tirer un BEAU 3D et un jeu de plans 2D BIEN DÉTAILLÉ

> **Édition publique** (une gracieuseté de Sylvain Leduc, Constructo AI inc.) : noms de clients, adresses et données internes retirés ; les projets de référence portent des noms génériques (« Bungalow », « Agrandissement », « Saint-Exemple »). Certains fichiers cités n'existent que sur le poste d'origine : voir `README.md`, « Ce que le dépôt ne contient pas ».

Demandé par Sylvain le 2026-09-24 :
- « apprends de ce plan et mets ton savoir dans un fichier vivant, afin de t'améliorer de session en session » ;
- puis « je veux qu'il puisse faire de beaux 3D et des plans 2D bien détaillés ».

Mode d'emploi :
- **À LIRE avant tout relevé de plan** (PDF, image, numérisation), **avant tout modèle** et **avant tout jeu de plans**.
  - Les agents `modelisation` et `dao` y sont renvoyés par leur fiche : § 6 pour le 3D, § 7 pour les plans 2D.
- **À ENRICHIR à la fin de chaque projet** : méthode, conventions, pièges, écarts, standards, galerie, et une entrée au journal (§ 9).
- **Chaque plan que Sylvain fournit est une leçon** : protocole du § 8 (étude de style, galerie, comparaison avec notre jeu).
- Complète `CLAUDE.md` : lui garde les outils et les chemins ; les pièges d'API sont dans `SAVOIR_BLENDER.md` et `SAVOIR_DAO_DWG.md`. Ici vivent le SAVOIR et les
  STANDARDS de qualité.
- Légende : ✅ vérifié sur un vrai projet · ◐ standard fixé ou déduit, à confirmer au prochain projet (on passe alors ◐ → ✅).

## 0. Règles d'or
1. **Mesurer dans les tracés vectoriels, recouper avec les cotes écrites, puis entre les vues.**
   - Une cote mesurable ne se lit jamais « à l'œil ».
   - Un plan fait à l'ordinateur est à l'échelle exacte : pentes de 12,00/12, 6,00/12 et 3,00/12 au centième ; niveaux à ±0,1". ✅
2. **Fixer UN repère avant de déléguer**, avec son origine, ses axes, ses unités et l'origine en points PDF de chaque feuille. Puis
   l'écrire dans les paramètres ET dans chaque brief d'agent. ✅
3. **Une seule source de vérité** : `parametres_<projet>.py`, qui recalcule ses propres contrôles dans `controles()`.
   - Égouts, faîtes, raccords et aires sont recalculés et comparés aux mesures.
   - Si ça ne ferme pas à ½" près, la lecture est fausse. ✅
4. **Règle 5 AVANT de livrer** : chaque écart entre pages est signalé à Sylvain et jamais tranché en silence (§ 5).
5. **L'original n'est jamais touché**. On le copie dans `C:\Dev\<Projet>\reference\` : il peut être sur OneDrive
   (attribut ReparsePoint), et un chemin contenant `$` exige des guillemets simples et `-LiteralPath`. ✅
6. **Beau ET juste** :
   - le 3D et les plans sortent des MÊMES paramètres ;
   - un détail inventé pour la beauté (mobilier, aménagement, gouttières…) est marqué « indicatif », et Sylvain le sait. ◐
7. **L'existant marqué « TEL QUEL » reste sans détail**, en 2D comme en 3D : ni noms de pièces, ni mobilier, ni appareils,
   sauf ce que le plan d'origine dessine déjà. Consigne de Sylvain du 2026-09-24, même quand il donne l'usage des pièces. ✅

## 1. Méthode éprouvée, dans l'ordre (Agrandissement : PDF → gabarit contrôlé en 23 min) ✅
1. **Inventaire** : `analyse_pdf.py` donne les pages, le format, le nombre de tracés vectoriels et d'images, et le début du texte. Il
   écrit un aperçu de chaque page à 60 dpi, qu'on lit ensuite avec Read.
   - Des milliers de tracés et du texte = un PDF **vectoriel**, exploitable.
   - Peu de tracés et une grosse image = une **numérisation** : il faut la méthode photo de CLAUDE.md (points de fuite, calage).
2. **Tout extraire une fois** : `extraire_mots.py` écrit les mots et les segments de chaque page en JSON (`pages\`).
3. **Échelle** : lire « ÉCHELLE » sous chaque vue.
   - En points par pied : 1/4" = 1'-0" → **18** ; 1/8" → 9 ; 1/2" → 36 ; 1" → 72.
   - Vérifier sur deux cotes entre axes : A-B mesuré 334,5 pt = 18'-7" écrit. ✅
4. **Axes** : `grilles.py PAGE`. Les bulles sont des mots d'un seul caractère, hauts d'environ 10 pt.
   - Le centre du texte tombe sur l'axe à ±0,7 pt.
   - **Confirmer l'origine sur un mur connu** (`remplis.py`) : l'écart doit être ≤ 0,05". ✅
5. **Murs en plan** : `remplis.py PAGE X0 Y0 [zone] [teinte]` convertit les surfaces remplies en pieds-pouces.
   - D'abord le relevé des teintes (Counter), ensuite l'association avec la légende.
   - Les trous dans une suite de remplissages le long d'un mur sont les ouvertures, avec leur largeur exacte. ✅
   - **Murs existants en maçonnerie** : aucun remplissage. Lire les **traits de face** (1,44 pt). La trame grise de l'existant
     est décalée d'environ 5/8" vers l'intérieur et découpée en bandes : elle ne donne PAS les positions.
     Cette erreur avait faussé le gabarit de ¼" à ½" ; les traits de face redonnent la chaîne écrite et le faîte calculé. ✅
6. **Élévations** : un repère (H0, Z0) par vue.
   - H0 vient des bulles d'axes.
   - Z0 vient des lignes de niveau. Une ligne en tirets est une grappe d'au moins 5 petits segments à la même hauteur.
   - Vérifier que TOUS les niveaux de la vue tombent juste. ✅
   - Sens de l'axe horizontal : vue EST, Y croît vers la droite ; vue OUEST, Y décroît ; vue SUD, X croît ; vue NORD, X décroît.
     L'ordre des bulles le confirme toujours. ✅
7. **Toits** : `segments_zone.py PAGE zone H0 Z0 18 [largeur_min] [longueur_min] [sens]`.
   - Il donne chaque segment en (h, Z) avec sa pente sur 12.
   - Le contour se trace de 0,84 à 1,44 pt, les lignes intérieures à 0,3 pt.
   - Faîtes, égouts et coupures de croupe : les horizontales épaisses. ✅
8. **Sol fini** : c'est la bordure des hachures, un trait de largeur 0. On le lit dans le JSON ou dans l'image (`sol_elevations.py`
   n'a rien trouvé en filtrant par largeur). ✅
9. **Implantation** : l'angle d'un long mur sur la feuille d'implantation donne la rotation par rapport au nord. Ici −8,22°, et les
   3 murs mesurés concordent à 0,01°. ✅
10. **Hauteurs affichées** :
    - « Hauteur du bâtiment » = faîte moins le sol avant ; calcul 25'-6" contre 25'-5" écrit. ✅
    - « Hauteur maximum » est la limite du règlement, pas une cote du dessin. ◐
11. **Contrôle final du relevé** : superposer le relevé à l'image du PDF, une image par vue (les deux plans et les
    4 élévations). Chaque ouverture, chaque luminaire doit tomber sur le dessin. ✅
12. **Trouver les éléments neufs** : comparer les élévations existantes au 1/8" avec les proposées. C'est ainsi qu'une marquise
    neuve est apparue au-dessus d'une fenêtre existante. ✅
12 bis. 🔴 **Lire les vues EXISTANT AVANT de relever l'agrandissement, et trouver ce qui est DÉMOLI.**
    - Formule de la Règle 5 : RDC existant ≈ RDC proposé − RDC neuf + démoli.
    - Sur Agrandissement, elle révélait en une ligne une annexe d'environ 658 pi², démolie au complet (confirmé par Sylvain).
    - Relevé, modèle, plans et métré l'avaient TOUS oubliée ; seule la vérification finale l'a trouvée. ✅
13. **Délégation** :
    - le chef relève le **gabarit** (axes, niveaux, emprises, toits, sol) ;
    - un agent `dao` relève le **détail** (ouvertures, intérieur, escaliers, appareils, mobilier dessiné, finis de plancher,
      fondations, écarts), dans des `releve_*.py` que les paramètres importent ;
    - la modélisation et le cadre des plans démarrent sur le gabarit, sans attendre. ✅

## 2. Boîte à outils (modèles PORTABLES : `modeles\releve_pdf\` du poste, à COPIER dans le projet suivant ; origine : Agrandissement)
| Script | Rôle |
|---|---|
| `analyse_pdf.py [dpi]` | Inventaire, texte de chaque page, aperçus `pages\page_NN.png` |
| `extraire_mots.py` | `pages\mots_page_NN.json` (mots avec leur boîte) et `traces_page_NN.json` (segments, largeur, couleur, remplissage) |
| `zoom.py PAGE X0 Y0 X1 Y1 [DPI] [NOM]` | Agrandissement d'une zone, avec les coordonnées de l'aperçu 2000 × 1333 affiché par Read. De 150 à 260 dpi, les cotes se lisent |
| `grilles.py PAGE` | Bulles d'axes et longues lignes alignées |
| `remplis.py PAGE X0 Y0 [zone] [teinte]` | Surfaces remplies en pieds-pouces (murs, ouvertures) |
| `mots_zone.py PAGE zone [regex]` | Mots d'une zone (cotes, niveaux, libellés) |
| `segments_zone.py …` | Segments d'une zone en coordonnées de vue, avec leur pente (toits, niveaux, cadres) |
| `sol_elevations.py` | Essai de lecture du sol : à refaire, puisque le sol est une bordure de hachures |
| `reference\releve_travail\` (agent de relevé) | Outils de relevé des ouvertures, des vantaux et des croisillons, et images de contrôle superposées au PDF (`zooms\controle_*.png`) |
| `plans\outils\releve_implantation.py` (agent des plans) | Lot, rue en arc, marges et services de la feuille d'implantation. Calage page → plan sur 13 coins, écart moyen 0,32" |
| `modeles\projet_bungalow\reference\` ✅ (origine : Bungalow) | Mêmes outils, **adaptés aux pages TOURNÉES** (repère affiché par `page.rotation_matrix` ; `zoom.py` rend la page entière puis découpe) et à une échelle quelconque (paramètre ECH) |
| `modeles\projet_bungalow\reference\chaines.py PAGE X0 Y0 [ECH]` ✅ | Toutes les chaînes de cotes d'une feuille : tics regroupés, positions en pieds, écart mesuré contre la cote écrite. Donne le gabarit d'une maison en quelques minutes |
| `modeles\projet_bungalow\reference\carte_traits.py` ✅ | Une couleur par épaisseur de trait, une image par feuille : décode en une image un dessinateur « tout en noir » |

## 3. Conventions vues sur un jeu québécois (technologue OTPQ, rénovation-agrandissement)
**Jeu de feuilles** ✅
- A001 ou A100 : implantation au 1/8" ;
- A100 : fondations et détails ;
- A101 : RDC proposé au 1/4", avec l'existant au 1/8" ;
- A102 : étage, de la même façon ;
- A200 : élévations avant et latérale gauche ;
- A201 : élévations arrière et latérale droite ;
- A300 : coupe « synoptique », compositions et détails.

Chaque feuille porte un cartouche (sommaire, révisions, sceau, titre, concepteur, feuille), des notes générales et une légende.

**Niveaux** ✅
- Repère « ±0'-0" DESSUS DE L'EMPATTEMENT ».
- Marques dans un cercle : PLANCHER DU RC, PLAFOND DU RC, PL. DE L'ÉTAGE, DESSUS DE LA SABLIÈRE, DESSUS DE LA DALLE, MURS DE FONDATIONS.
- **Les vues de l'existant ont LEUR propre repère** (plancher du RC = 100'-0", ici décalé de 92'-4").
- Au plan, « 84" Hauteur Libre » ; « plafond en pente » marque la zone sous les rampants.

**Libellés d'ouvertures** ✅
- En plan, dans un cadre : « Fenêtre à guill. 36"x60" » (guillotine), « Fenêtre à auvent 62"x54" », « Porte ouv. 36"x84" »,
  « PORTE GARAGE (108"x84") ».
- En élévation, au coin de la fenêtre : « 36/54 » = largeur/hauteur en pouces ; « 32/82 » pour une porte.
- « TEL QUEL » = existant conservé.
- « Fenêtres à 7'-0" ht » = tête des fenêtres à 7'-0" au-dessus du plancher (texte vertical en marge).

**Portes, en plan** ✅
- Codes à 4 chiffres = largeur puis hauteur en pouces : « 3280 » = 32" × 80".
- « p.pochette » = porte à pochette ; « p.pliantes » = porte pliante (« 5480 » : 4 panneaux de 13½").
- Vantail = quadrilatère tourné, tracé à 0,54 pt, dont le grand côté égale la largeur de la porte.
- ◐ « vt » dans une douche = verre trempé.

**Traits, pour lire vite** (ce jeu ; à relever pour chaque dessinateur) ✅
| Où | Élément | Trait |
|---|---|---|
| En plan | Cloisons | 1,02 pt, par paires : à 4½" pour C1, à 8" pour M/F |
| En plan | Nez de marche | 0,84 pt |
| En plan | Appareils | 0,3 pt |
| En plan | Mobilier | gris 50 % |
| En élévation | Cadre des fenêtres | 1,14, 1,02 ou 0,84 pt |
| En élévation | Moulure | 0,42 pt, 2" autour |
| En élévation | Châssis | 0,54 pt |
- Un croisillon = deux quadrilatères de 0,3 pt, espacés de ½". La flèche d'une guillotine est un trait seul, pas un
  croisillon.
- Deux chaînes de cotes sur une même façade : l'une à l'axe des baies, l'autre aux jambages. Elles se recoupent.
- Symboles « WF » (prises extérieures) : des dessins absents du texte, des cercles de 3" à 0,54 pt. Pieux vissés : polygones
  de 33 segments dans un cercle en tirets de 1'.
- ◐ En fondation, une zone hachurée dans un mur = dessus abaissé sous une porte (57" ; 39" sous la porte de garage).

**Escaliers** ✅
- « E.H. 16 c.m. » = escalier qui MONTE, 16 contremarches.
- « E.B. » = escalier qui DESCEND.
- Preuve : le même escalier porte E.H. à son étage du bas et E.B. à son étage du haut.

**Étiquettes et renvois** ✅
- Hexagones M1, M2, M/F, C-1 = types de murs. Cercles gris T1, T2, P0, P0G, P1, P/F = toits et planchers. Leurs compositions sont
  sur A300.
- « D-3 101/300 » = détail D-3, dessiné sur A300 et appelé depuis A101.
- Coupe « A 102/300 ».
- Boîtes « AIRE HABITABLE ».

**Légende de rénovation** ✅
- Mur existant à conserver : trame grise claire. Neuf : gris foncé plein. À démolir : tirets.
- Dans ce PDF, les teintes de remplissage sont 0,502 (neuf), 0,929 (existant) et 0,498 (hachures). Elles varient d'un dessinateur
  à l'autre : toujours les relever.

**Toits** ✅
- Symbole de pente : un petit triangle « 12 / 6 » = 6 de montée sur 12 de course.
- **Reconnaître une demi-croupe** (pignon tronqué par une croupe) :
  - en vue de pignon : un mur en pentagone (verticales, puis « épaules » à la pente du versant), coiffé d'un triangle de tôle
    (la croupe) ;
  - en vue de long pan : un trapèze dont les côtés sont verticaux en bas (rives vues de bout), puis inclinés (croupes).
- **Lucarnes et avancées à pente plus faible** : leurs lignes (6/12) débordent du profil 12/12 dans les vues de bout. Ne pas les
  prendre pour la pente du toit principal.
- **Un toit plat d'agrandissement qui bute sur un toit en pente** s'arrête à l'isoligne de son dessus. Elle se calcule par
  (Z_dessus − Z_coupure) / pente : 16'-9½" calculés contre 16'-9½" dessinés. ✅

**Toit plat neuf contre un toit existant** ✅ (vérification du projet Agrandissement). À noter « voir ingénieur (OIQ) » et à chiffrer :
- chevrons existants coupés à reprendre ;
- mur existant abaissé ou chargé ;
- congères contre le toit plus haut ;
- neige qui glisse d'une tôle raide sur le toit plat (CNB 4.1.6), d'où des arrêts de neige ;
- drains à définir.

**Coupe « synoptique »** ◐ : elle est composite. Ne pas supposer un plan de coupe droit : confronter la ligne de coupe au contenu
de la coupe.

**Conventions d'un 2e dessinateur** ✅ (un autre technologue, bungalow neuf sur sous-sol, 6 feuilles Lettre, 2026)
- Cartouche en colonne étroite à droite, avec une boîte **SUPERFICIES** (sous-sol, RDC, garage : aires BRUTES aux faces
  extérieures ; le garage s'arrête aux faces côté garage des murs mitoyens).
- **Légende des niveaux par hachure** : au plan des fondations, le motif du mur dit la hauteur de son dessus (pointillé
  8'-4", oblique 5'-8", croisé 5'-4"). Une **loupe** (médaillon) cote une tablette de 2" (« 8" = 6" + 2" »). Marque « NIV »
  en demi-disque. Utile au métré par hauteur.
- Ouvertures « 96Lx108H » (largeur × hauteur, en pouces) au plan ET en élévation ; « imposte 24" » ne donne que la hauteur ;
  portes intérieures par leur largeur seule.
- Fermes typées A à D au plan, d'appui à appui, plus leurs profils cotés (portées, débords de 10", talon de 1'-6") ;
  « POUTRELLES 12" @ 16" C/C » par travée ; poutres LVL en tirets-points ; poteaux Paralam.
- Cotes de la face extérieure à l'axe des cloisons (vérifié sur 50 cotes). Notes générales encadrées avec ombre, liste
  « PRÉVOIR ».
- Un dessin tout en noir se lit à l'ÉPAISSEUR des traits : 1,08 pt murs et cloisons ; 0,72 fenêtres et appareils ; 0,84
  poutres ; 0,48 tirets et garde-corps ; 0,375 cotes et hachures ; 0,24 niveaux et vitrages en élévation.

**Notes de code fréquentes** ✅
- Radon : dépressurisation sous la dalle.
- Garage : cloison hermétique, portes pleines avec ferme-porte, fosse de retenue de 18"×24"×18" reliée au sanitaire, détecteurs
  de CO près des portes du garage.
- « L'entrepreneur doit vérifier les dimensions ».

## 4. Pièges de lecture (payés)
- **Jeu institutionnel à deux professionnels** (architecte et ingénieur, plus un devis ; projet Saint-Exemple, immeuble d'habitation, 54 feuilles
  et 41 pages, 2026-10-08) ✅ :
  - l'architecture et la structure n'ont pas le même REPÈRE : l'axe A est au nu extérieur du mur aux feuilles de
    structure, et 53 mm dans le mur à l'architecture ; les longueurs d'un même balcon diffèrent de 19 mm (9 640 contre
    9 621). Ramener tout au nu du mur avant de comparer une cote ;
  - le même élément est « existant » sur une feuille et « neuf » sur l'autre (colonnes, bases), rond sur un plan et carré
    dans une note : faire un tableau « élément, feuille, ce qu'elle dit », et poser la question ;
  - un profilé écrit au plan peut ne pas exister en laminé (cornière L76x51x3.2) : vérifier chaque profilé au manuel
    avant de le reporter ;
  - le devis contredit le plan sur une finition (caillebotis « galvanisé » au plan, « galvanisé peint » au devis) : lire
    le devis EN ENTIER, il impose aussi le sceau, les essais et les normes ;
  - les pages de structure sont tournées de 90° : rendre la page entière, puis découper ;
  - **les mesures prises au chantier priment** (« les dimensions existantes sont approximatives », note de l'architecte) :
    un étage mesurait 155 mm de plus que le plan. Comparer chaque mesure de chantier à la cote du plan dès l'analyse ;
  - sortir trois documents : une demande d'information à l'architecte (27 points), une fiche des mesures à prendre au
    chantier, une liste de questions à celui qui fabrique.
- **L'extraction de texte coupe les fractions** : « 12'-21 | 2" » = 12'-2 1/2", « 23'-412" » = 23'-4 1/2". ✅
- **Les lettres d'axes changent d'une feuille à l'autre dans le même jeu** : la face est de la maison est « D » au RDC et « F » à
  l'étage ; la face sud est l'axe 6 au RDC et l'axe 7 à l'étage. Faire une table de correspondance, puis dessiner NOTRE jeu avec
  une seule grille. ✅
- **Le numéro d'une bulle ne suffit pas** : toujours vérifier son écart aux autres axes contre les cotes. ✅
- **Les petites vues de l'existant au 1/8"** montrent souvent plus clairement les toits existants que les grandes vues
  proposées. ✅
- PowerShell : `Select-Object -First N` derrière `python` rend le code 255 (tube fermé), mais la sortie est complète.
  `importlib.util` exige `import importlib.util`. ✅
- Read réduit les images à 2000 px de large : les facteurs d'échelle sont donnés sous l'image. `zoom.py` travaille dans les
  coordonnées de l'aperçu 2000 × 1333 pour passer directement de la vue d'ensemble au détail. ✅
- `extraire_mots.py` ne garde que 2 coins d'un quadrilatère (`qu`) : pour les vantaux, relire `page.get_drawings()`. ✅
- **La légende d'un original peut contredire son propre dessin** : ici, l'existant est hachuré dans la légende mais gris uni
  dans le dessin. Vérifier à 300 dpi avant d'imiter. ✅
- **La cote de marge avant d'un original n'est pas forcément au coin le plus proche** : ici 52'-4¼" au coin sud-est, contre
  52'-1 15/16" au nord-est. Recalculer la marge à chaque coin. ✅
- L'implantation d'origine coupe le lot au bord du cadre. Dire ce qui n'est pas dessiné et demander le certificat de
  localisation. ✅
- Pour ajuster une courbe en tirets (arc de rue), il faut filtrer les traits par angle. Sinon l'erreur passe de 0,03" à 33". ✅
- La coupe « synoptique » est confirmée composite : sa ligne est à Y 19'-3½" à l'étage, mais le RDC coupé est à Y ≈ 9'. Elle
  emploie les lettres d'axes de l'existant. ✅
- Pour un escalier vu de côté en élévation, les dents de scie sont 1½" sous le dessus des marches : se fier aux cotes de
  hauteur. ✅
- **Page tournée** (Bungalow, 270°) : mots et tracés sortent dans le repère NON tourné. Tout ramener au repère affiché
  (`page.rotation_matrix`) avant de mesurer. ✅
- **Feuille réduite** (grand format imprimé en Lettre) : l'échelle écrite est FAUSSE. La mesurer sur deux longues chaînes.
  Les traits gardent leur épaisseur réelle, seuls les textes rapetissent. `get_text("dict")` donne le corps de la police,
  pas la hauteur des capitales. ✅
- **Tics d'architecte en parallélogrammes pleins** : centre = milieu de la boîte de tous leurs segments (union-find). Des
  tics voisins (cotes de 6") fusionnent si on regroupe trop large : faux écarts de 3". ✅
- **Pas des hachures** : rogner les longues lignes sur la zone, sinon on ne mesure rien. Le pas change exactement à la
  limite du produit : il identifie le produit. ✅
- **Repère d'élévation** : contrôle simple, les seuils au niveau du plancher doivent tomber pile sur le plancher. ✅

## 5. Écarts à chercher SYSTÉMATIQUEMENT (Règle 5), tous vus sur un vrai plan ✅
- Aire d'un titre contre le tableau de la même feuille : RC 1 467,4 contre 1 445,6 pi² ; garage 336,6 contre 310 pi².
- Aire existante d'une feuille à l'autre : étage 1 043 pi² contre 1 233 pi².
- Cote écrite contre cote écrite : 34'-3¼" contre 34'-3½" ; et contre le tracé (34'-3").
- Numérotation des feuilles : deux feuilles « A100 », alors que le sommaire annonce « A001 » pour l'implantation.
- Lettres d'axes différentes d'une feuille à l'autre (§ 4).
- Erreur de terme dans la légende : « monoxide de carbone CO2 » au lieu de « monoxyde de carbone (CO) ».
- **Toujours recalculer les emprises depuis la géométrie** et les comparer aux tableaux : ici maison + avancée 1 096,9 pi²,
  pile le chiffre du plan. Ajout 707,2 pi².
- Un même axe porte deux noms **sur une même feuille** (7 et 6 à Y 0 ; E et G au même X).
- Coquille dans une coupe : « 57'-0" » pour 57".
- Chaîne écrite contre dessin : 1⅛" pour une fenêtre. Libellé de pièce faux : « Garage 15'-10" » contre 17'-11" mesuré.
- **Plan contre élévation, pour une même ouverture** : type différent (auvent ou guillotine), hauteur différente (82" ou 84"),
  vantail différent (34" ou 32").
- **Composition contre fondation** : « dalle existante » dans P0 et P0G, contre une dalle armée neuve sur la feuille des
  fondations.
- **Les services aussi** : fils aériens à l'implantation, compteur souterrain au RDC, « ajustement du mât » dans la coupe.
  La Règle 5 couvre les services, pas seulement les cotes.
- L'original n'a **aucun tableau des portes et fenêtres** : les étiquettes en cadre le remplacent. Notre jeu garde les
  étiquettes et ajoute le tableau.
- **Contradictions de construction à trancher AVANT un métré**, toutes trouvées par l'agent `estimation` sur Agrandissement :
  - dalle neuve (A100) ou existante (A300) ;
  - montants 2x6 (A101) ou 2x4 (détail D-1) ;
  - isolant XPS 4" ou EPS 1" ;
  - contremarche écrite de 7 1/2", calculée à 7 11/16". Prendre le calcul et le signaler.
- **Vus sur Bungalow (2026-09-25)** :
  - **coupe de mur « type » générique** : 2 étages et 6/12 pour un plain-pied à 4/12. On garde ses compositions, jamais sa
    géométrie ;
  - **chaîne de niveaux qui ne ferme pas** : 1'-0" non coté entre la fondation et le plancher, alors que lisse + poutrelles
    12" + contreplaqué font environ 1'-2" ;
  - **texte contre dessin** : « dalle de béton 6" » écrit là où les élévations dessinent un plancher de bois sur poteaux.
    Les vrais chiffres de l'entreprise ont donné raison au TEXTE (dalle de béton sur sonotubes). Règle : une note écrite de
    construction l'emporte sur un trait d'élévation. On la recommande, et on signale l'écart ;
  - **portée de ferme contre plan** : ferme C dessinée pour un appui à 27'-8", poutre du plan à 26'-8". Dresser la TABLE
    DES APPUIS de chaque type de ferme : elle révèle aussi les charges cachées (fermes A qui portent sur la poutre du patio) ;
  - **linteau impossible** : tête de fenêtre à 2" sous la sablière ; porte de garage de 12' sans linteau indiqué ;
  - **Code** : main courante dessinée à 2'-8" (CNB 34" à 38") ; détecteur de garage et CO exigés par les notes mais non
    dessinés ;
  - **légende** qui annonce un symbole jamais employé ; **renvois de coupe** écrits à l'envers de leur propre diagramme ;
  - **une couche de composition absente du métré** (membrane d'étanchéité du mur de fondation) : croiser chaque couche de
    chaque composition avec le bordereau, comme on cherche l'existant démoli ;
  - **la région administrative** du chantier (facteur de prix) : la vérifier sur Québec.ca, jamais de mémoire ;
  - **structure cachée par la géométrie** (vérification 2B), à mettre sur la liste de l'ingénieur :
    - **garage sur fondation basse** : les murs porteurs y ont des montants très hauts (2x6 de 12'-10" sur une fondation
      à 5'-8"). Les comparer au tableau 9.23.10.1 du CNB ;
    - **détail type appliqué hors de sa portée** : un linteau de fondation de 6" dessiné pour une fenêtre de 48" est repris
      sous des baies de 96", 72" et 60" ;
  - **élément dessiné sur un appui absent du plan des fondations** : cheminée « béton apparent dessous » aux élévations,
    sans aucune fondation au plan (écart 3.10). Le 3D suit les élévations (massif de béton jusqu'à la semelle), et
    l'écart part à l'ingénieur.
- **Vus sur l'escalier flottant (2026-09-28), entre NOS livrables** :
  - **type d'ouverture** : une PORTE dans les paramètres et le 3D, une BAIE sans battant sur le plan, avec les mêmes
    cotes. La Règle 5 compare aussi la NATURE de l'élément, pas seulement ses cotes ;
  - **un appui corrigé en crée un autre** : sorti du vide, le poteau est aussi sorti de l'emprise du palier, qui porte
    alors sur une plaque en porte-à-faux. Refaire le cheminement des charges après chaque correction de structure ;
  - **fiche d'empreinte des rendus** : un livrable refait après elle (la planche) la rend fausse. Régénérer la fiche en
    même temps que le livrable.

**Pour le métré, ce que le plan cache** ✅ :
- **Deux hauteurs coexistent** : le mur extérieur, de la fondation à la sablière (8'-2", coté aux élévations), et la hauteur libre
  du RDC, qui décide le gypse (9'-1").
- **Un agrandissement change l'existant** : des murs de maçonnerie existants deviennent intérieurs, et leur fini est à mesurer ;
  un toit neuf qui chevauche la maison (101 pi²) implique une démolition en zone B.
- Toit plat : drains, pentes et hauteur du parapet ne sont pas cotés. « VOIR ING. » veut dire chiffré à la main.
- **Recoupement à trois sources** (paramètres, modèle 3D, DXF) : il révèle les artefacts du modèle, par exemple des pièces
  prolongées de 0,12 pi dans un mur.

## 6. Faire un BEAU 3D : standard « présentation client », pour l'agent `modelisation`
Un rendu est beau quand il est **juste** (cotes, ouvertures, matériaux du plan), **détaillé** là où l'œil va, et **bien éclairé
et bien cadré**. Les pièges d'API et de rendu déjà payés sont dans `SAVOIR_BLENDER.md` (« Pièges vérifiés — rendu ») : ne pas les refaire.

**Niveau de détail minimal de l'enveloppe** ◐, à lire à la distance de la caméra principale :
- **Murs** :
  - épaisseur réelle, d'où des tableaux (retours) visibles aux ouvertures ;
  - planches cornières ;
  - soubassement ou fondation apparente jusqu'au sol, avec la bonne texture.
- **Fenêtres** :
  - cadre et moulure extérieure d'environ 3½", châssis, allège saillante, vitrage réfléchissant ;
  - **croisillons conformes au plan** (« 2x3 », etc.) et même type (guillotine, auvent, fixe) ;
  - un fond derrière la vitre : plafond, mur ou rideau, légèrement éclairé. Jamais une boîte vide qu'on voit à travers.
- **Portes** :
  - panneaux, vitrages, poignée ;
  - porte de garage avec ses sections et sa rangée de fenêtres ;
  - seuil.
- **Revêtements en GÉOMÉTRIE quand la caméra est proche**, en relief (bump) sinon :
  - lattes verticales avec couvre-joints à l'entraxe réel ;
  - déclin horizontal à son exposition réelle (environ 6-7") ;
  - brique en appareil courant, 8" × 2⅝", joints en creux ;
  - stucco en bruit fin.
- **Toit** :
  - tôle à joints debout à l'entraxe réel (environ 16"), en géométrie ;
  - faîtières et arêtiers ;
  - fascia, soffite ventilé, larmier ;
  - membrane et parapet pour un toit plat.
- **Escaliers et garde-corps** :
  - limons, marches, contremarches s'il y en a, poteaux ;
  - barreaux espacés de 4" au plus ;
  - mains courantes à 36" et garde-corps à 42", comme au plan.
- **Luminaires, compteur, mât, borne** : tout ce qui est dessiné au plan est posé.
- **Rien d'inventé sans le dire** :
  - gouttières, entrée d'auto et aménagement paysager sont du CONTEXTE, dans une collection à part, non exportée en DWG ;
  - ils sont signalés à Sylvain.

**Lumière et caméra** :
- ✅ Garage : Cycles CUDA, AgX « Medium High Contrast », exposition 0,2, soleil 8,5, ciel d'éclairage à 0,6 teinté bleu, fond
  caméra à 1,1.
- ✅ Garage : 6 rebonds (3 diffus, 3 brillants), seuil adaptatif 0,02.
- ◐ Orientation vraie du soleil (rotation du site), soleil d'après-midi ou de fin de journée. Angle solaire de 0,5 à 1°, pour des
  ombres nettes mais pas tranchantes.
- ◐ **Perspective à 2 points** : caméra de niveau (verticales verticales), puis décalage `shift_y` pour cadrer. Hauteur d'œil
  5'-6" pour les vues de rue ; focale de 35 à 50 mm équivalent.
- ◐ Vue aérienne aux 3/4, de 30 à 40° de plongée.
- ◐ Une vue de crépuscule, avec les lanternes et l'intérieur allumés, fait souvent la plus belle image.
- ✅ Fond opaque, jamais `film_transparent` : une photo hyperréaliste Gemini peut en être tirée (`Rendu3D_ERP`), avec une consigne
  qui énumère les détails à garder.

**Des vues 2D aux volumes : recettes vérifiées** (Agrandissement, 1 196 objets, 15 700 faces, construction en 8 s) ✅
- **Demi-croupe** : le toit est le MINIMUM de 4 plans (versants E et O ; croupes S et N, qui ne partent qu'au-dessus de la
  coupure).
  - Le dessus est fait des zones où chaque plan est le plus bas (découpe par demi-plans). Ces zones sont relevées, soudées,
    puis extrudées de l'épaisseur verticale.
  - Le matériau se choisit par la normale : tôle, fascia, soffite.
  - Le pignon est un pentagone dont le dessus suit le toit, moins une demi-épaisseur.
- **Toit à cassure** (6/12 puis 3/12) : c'est un MAXIMUM de plans. Il faut donc des zones explicites.
- **Lucarne sur un versant plus raide** : ses joues vont jusqu'au croisement des deux pentes, trouvé par bissection. Son faîte
  s'arrête sur la ligne du faîte principal.
- **Toit plat contre des pentes** :
  - le prolonger dans le comble jusqu'aux lignes de niveau de son dessus sur chaque versant ;
  - retrancher le toit existant sous lui par booléens ;
  - fermer le triangle au-dessus de la croupe par le caisson.
- **Revêtements** : le pas du déclin, des lattes, des rangs de brique et des joints de tôle se MESURE sur les hachures des
  élévations. Ici déclin 4", lattes 8", brique 2,67", tôle 8,8", et le bord du toit plat de 1'-8" au lieu de 6".
  - Quand paramètres et élévations divergent, l'aspect suit les élévations et les cotes suivent les paramètres. Chaque cas est
    écrit en écart.
- **Coupes 3D (« plans 3D ») par booléen EXACT** :
  - un coupeur qui rencontre des pièces fusionnées qui se chevauchent crée un plan de coiffe géant, et le rendu sort noir ;
  - correctif : `use_self`, `use_hole_tolerant` et un coupeur borné au bâtiment ; trouver le plan fantôme avec `scene.ray_cast`
    depuis la caméra ;
  - coût : de 17 à 26 s de booléens par coupe.

**Recettes de beauté vérifiées** ✅
- Verre : mélange Transparent/Glossy selon Fresnel.
- Fonds derrière les vitres : émission de 0,12 le jour et de 4,0 au crépuscule.
- Crépuscule : soleil caché, verre sans ombre portée, exposition +0,9 au lieu de -0,35 le jour. Lanternes allumées.
- Soleil réel : date, heure et rotation du site. La façade est au matin (10 h), le sud vers 13 h 30, l'ouest vers 17 h.
- Chambranle : le faire chevaucher la baie de ¼". En retrait de ¼", il est coplanaire avec la coupe du revêtement.
- Tôle à joints debout : les bouts plats des joints font des tirets blancs au soleil. Les chanfreiner à 45° (métal 0,1,
  rugosité 0,45).
- Terrain et route à la même cote se chevauchent : abaisser le terrain de 3" sous la route. Des feuillages lointains en
  boules passent pour des rochers : mettre de vrais arbres, clairsemés.
- **Cadrer par le CALCUL, dès la 1re passe** ✅ (Agrandissement, 2e passe) :
  - projeter les sommets du bâtiment ; trouver par dichotomie la distance qui donne 70 % de la largeur ; centrer par le lacet ;
  - vues de niveau : œil à 5'-6" ; décentrement vertical (0,5 − 1/3) × H/W pour mettre l'horizon au tiers bas ; verticales
    verticales ;
  - aucun essai visuel nécessaire. En 1re passe, la maison n'occupait que le tiers de l'image.
- **Gazon** ✅ :
  - trois échelles de bruit à faible contraste, sans grandes plaques ;
  - au premier plan, les brins forment UN SEUL maillage numpy (1,2 à 2 M de triangles), invisible aux rayons diffus et brillants :
    coût presque nul (41 s au lieu de 40,5 s) ;
  - poser les brins un par un sur les faces du terrain, avec un test au pied de chaque brin près des sols couverts, sinon le bord
    fait des escaliers ;
  - les brins sont en CONTEXTE, créés au rendu et jamais enregistrés dans le `.blend`.
  - Légère brume au-delà de 45 m.
- ✅ `scene.ray_cast` dans une scène à environ un million de feuilles instanciées : quelques milliers de rayons prennent plus de
  400 s. `BVHTree.FromPolygons` sur les 20 à 70 objets proches du sol prend 0,1 s.
- ✅ Contact de pièces : pour que le contrôle DWG le voie, noyer la pièce de ¼". Un contact tangent, ou face contre face, ne
  compte pas.

**Recettes vérifiées sur Bungalow (2026-09-25)** ✅
- **Toits en gradins de même pente** (3 pignons avant emboîtés, patio) : aucune noue. Le dessus est l'enveloppe la plus
  HAUTE des toits, par tranches de X. Le toit bas se prolonge SOUS le débord du toit haut jusqu'au mur pignon, et la rive
  du toit haut se pose SUR le toit voisin. Les versants d'un même côté sont un seul plan : c'est un contrôle
  (`controles()` : chaque faîte tombe sur le versant du toit principal).
- **Revêtements : relever le pas ET la phase** (où tombe le premier joint). Avec la phase, la superposition tombe ligne pour
  ligne.
- **Zéro face coplanaire par construction** : poser les couches l'une SUR l'autre (fond continu, puis panneaux ; tôle, puis
  nervures) et décaler par l'index les pièces répétées qui se croisent (0,0013 × k). 370 paires visibles tombées à 0.
- **Sans implantation** : choisir une orientation qui éclaire les 4 façades à des heures plausibles, la dire indicative ;
  rendre les arbres de cadrage vue par vue.
- **Patio de bois** : modéliser d'emblée une charpente minimale (poutre sur poteaux, solives, lisse d'appui, rampes attachées
  aux poteaux), marquée indicative. Sinon le contrôle « aucune pièce flottante » du DWG la réclame.
- **Barreaux** : vide ≤ 3 7/8" (sphère de 100 mm), donc entraxe ≤ 4 1/4" pour des barreaux de 3/4", nombre arrondi vers le
  HAUT (`ceil(L / pas) − 1`). **Mains courantes** : comme au plan, mais signaler tout ce qui sort de 34" à 38".
- **Plan 3D du sous-sol** : laisser entier ce qui dépasse le plan de coupe de moins de 6" (sonotubes) et cacher le niveau du
  dessus (patio), sinon des taches noires apparaissent.
- Standards passés de ◐ à ✅ : niveau de détail de l'enveloppe (sauf gouttières non dessinées), perspective à 2 points, vue
  aérienne à 32°, crépuscule, superposition orthographique sur les 4 élévations, série type de 10 vues. Reste ◐ :
  l'orientation vraie du soleil, impossible sans implantation.

**Recettes vérifiées sur l'escalier flottant d'après photo (2026-09-28)** ✅
- **Projeter les paramètres sur la photo AVANT de modéliser** : 30 lignes de Pillow avec la caméra calée
  (`reference\superposition_gabarit.py`). On y a vu, avant tout rendu, la trémie ouverte sous le palier, la poutre de rive
  absente sur une voie et le sabot posé au nu de la rive.
- **Circulation** : un contrôle géométrique ne voit pas qu'un verre ferme l'ENTRÉE d'une volée. C'est Sylvain qui l'a
  trouvé sur la vue héros. Chaque volée doit garder libres son entrée et son arrivée : c'est un contrôle des paramètres.
- **Escalier flottant, niveau de détail qui a plu** :
  - marches chanfreinées au fil long : cernes autour de l'axe long, en coordonnées objet, avec un décalage aléatoire par
    objet ;
  - limon en crémaillère extrudé depuis un profil unique, partagé avec le 2D ;
  - verre en géométrie avec chant vert, fixations fût et tête, sabots en U ;
  - main courante sur supports ronds collés au verre.
- **Forêt vue de l'intérieur (M2)** :
  - lisière de pré, arbustes, gaules, étage moyen ;
  - grands arbres de 20 à 26 m pour remplir les fenêtres hautes ;
  - voile de distance par « Camera Data > View Distance » (15 à 90 m) ;
  - versions simplifiées au-delà de 30 m ;
  - vraies feuilles polygonales, sans transparence ;
  - rien à moins de 3 m des murs.
- **Mobilier relevé sur une photo grand-angle calée (M2)** :
  - rétroprojeter les points d'appui au sol (pieds), jamais les dessus ;
  - l'orientation se lit sur les traverses horizontales dans l'image ;
  - le rapport de largeur de deux pièces identiques donne leur profondeur relative sans dépendre de l'horizon.
- **Fond d'un grand-angle (111°)** : la rétroprojection y dérive d'environ 5'. Seule compte la vue calée : on garde
  l'architecture des paramètres.
- **Post-production** : sur les images BRUTES, hors du rendu (halo discret, point blanc neutre, courbe en S, vignette
  légère). Garder toujours la version brute, qui sert à la photo IA.
- **Teintes contre la photo** : blancs neutres, céramique marbrée plus foncée, plancher à fil marqué et écarts entre
  lames. Une ambiance pêche ou beige trahit le rendu.
- **Chant de verre** : il doit se lire vert pâle. En Cycles, un chant transmissif à 100 % sort noir : le rendre en
  partie diffus (poids de transmission de 0,25 sur le chant, avec un diffus vert pâle).
- **Une texture se juge à la résolution FINALE**, sur un gros plan rendu en fenêtre (`use_border`, environ 1 min),
  jamais sur un aperçu de 1 000 px : le fil du plancher y disparaissait ou y faisait du velours côtelé.

**Contrôles avant de montrer** :
- ✅ **superposition** de l'élévation du PDF (en rouge) sur la vue orthographique du modèle : le contrôle le plus probant
  (`superposer_elevations.py` du projet Agrandissement, 4 façades concordantes) ;
- ✅ empreinte par objet (sommets, boîte, sommes) : en 6 s, elle prouve qu'un changement caché n'exige pas de refaire les rendus.
  Elle reste aveugle aux changements symétriques ;
- ✅ relancer le détecteur de coplanaires après CHAQUE changement, même caché : amincir une pièce cachée peut découvrir un ancien
  recouvrement ;
- ✅ détecteur de faces coplanaires : 0 paire de même sens visible ;
- ✅ **ce qui porte doit toucher le sol**, maçonnerie comprise : une cheminée dessinée « béton apparent dessous » flottait
  à 1'-6" dans les rendus, alors que le DWG passait le contrôle « aucune pièce flottante » (vérification 2B de Bungalow) ;
- ✅ **figer les rendus au gel**, comme les sources : `rendus\EMPREINTE_RENDUS.txt` (empreinte, sha256 de chaque image,
  heure). Sinon le dossier mélange deux versions du modèle. Un diff de pixels entre deux gels localise la seule zone qui a
  changé (562 pixels, tous au patio) ;
- ✅ gros plans au téléobjectif sur les jonctions toit-mur, toit-toit, égouts, tableaux de fenêtres, escalier ;
- ✅ **masque Workbench** (couleurs plates) de tout élément transparent ajouté, avant les longs rendus : il prouve dans
  quelles vues l'élément paraît (verre du palier de l'escalier : 4 vues sur 5) ;
- ✅ **présence d'un garde-corps sur chaque rive qui a une chute**, contrôlée dans les paramètres, et pas seulement
  l'absence de verre aux entrées des volées ;
- ◐ superposition d'une vue orthographique du modèle à l'élévation du plan : aucune ouverture, aucun niveau ne doit différer ;
- ◐ série type : vue héros aux 3/4 depuis la rue, chaque façade, arrière aux 3/4, aérienne, crépuscule, puis vues en coupe
  « plans 3D » de chaque étage. Aperçus EEVEE, puis finales Cycles.

## 7. Faire un plan 2D BIEN DÉTAILLÉ : standard « jeu de construction », pour l'agent `dao`
Un plan est bien détaillé quand un entrepreneur peut construire et chiffrer avec, sans deviner : tout y est coté, identifié et
référencé, et il reste lisible. Les pièges ezdxf et ODA déjà payés sont dans `SAVOIR_DAO_DWG.md` (« DXF / DWG avec ezdxf » et « Plans 2D
cotés ») : ne pas les refaire.

**Plans d'étage** ◐ :
- **Poché** : murs coupés remplis. Neuf en gris foncé, existant conservé en trame claire, à démolir en tirets.
- **Épaisseurs de trait par calque**, fixées pour l'impression : murs coupés environ 0,50-0,70 mm ; cloisons 0,35 ; portes,
  fenêtres et appareils 0,25 ; cotes, textes de cote et hachures 0,18 ; caché et débords en tirets 0,18.
- **Étiquettes de type de mur** (M1, M2, C1…) renvoyant aux compositions.
- **Portes** : arc d'ouverture et battant, cadre, largeur, repère renvoyant au tableau.
- **Fenêtres** : double trait avec l'allège, repère renvoyant au tableau des ouvertures.
- **Escaliers** : marches, flèche MONTE/DESCEND, « 14 c.m. », ligne de coupe en zigzag, garde-corps et mains courantes.
- **Appareils sanitaires en silhouette** : toilette, lavabo ou vanité, douche avec ses dimensions, bain.
- **Électroménagers identifiés** : FRIG, CUIS., LV, SÉCH., L.V. ; armoires de cuisine avec l'évier ; penderies (tringle, tablette).
- **Pièces** : nom, dimensions intérieures, superficie, fini de plancher (vinyle, céramique, béton chauffant) et hauteur de plafond.
- **Électricité et sécurité**, quand l'original les montre : panneau, D.F. et détecteurs de CO, prises extérieures, borne de
  recharge.
- **Cotes** :
  - 3 chaînes extérieures sur chaque face (ouvertures au centre ou aux bords, décrochés et murs, hors tout) ;
  - cotes intérieures jusqu'aux cloisons ;
  - cotes d'axes, avec les bulles d'axes aux deux bouts.
- **Renvois** : coupes (A-A, avec feuille et numéro), détails (D-1…), nord, échelle graphique et échelle écrite, titre de vue.

**Tableaux** ◐ :
- **tableau des portes et fenêtres** (repère, type, largeur × hauteur, allège, tête, quantité, existant ou neuf) ;
- tableau des aires par étage, calculées sur la géométrie ;
- légende des symboles ; notes générales.

**Élévations** ◐ :
- Line Art du modèle, avec :
  - hachures de matériaux (brique en appareil, lignes de déclin, joints de tôle) ;
  - cercles de niveaux (plancher, plafond, sablière, dalle, empattement) ;
  - notes de matériaux avec flèches ;
  - repères de fenêtres ;
  - ligne de sol hachurée et fondation cachée en tirets ;
  - triangles de pente ;
  - hauteur du bâtiment.

**Coupe** ◐ :
- éléments coupés en trait fort et en poché, éléments au-delà en trait fin ;
- étiquettes de composition ;
- niveaux ;
- escalier ;
- structure du toit ;
- semelles et drain ;
- isolant symbolisé.

**Plan de toiture** ◐ : pentes avec flèches, faîtes, arêtiers et noues, débords, lucarnes, drains et membrane des toits plats.

**Implantation** ◐ :
- lignes de lot cotées ;
- marges de recul ;
- bâtiment hachuré ;
- nord ;
- rue ;
- services (fils aériens, champ d'épuration) ;
- entrée d'auto, si elle est connue.

**Mise en page** :
- ✅ ARCH D ; présentations avec fenêtres verrouillées sur un calque qui ne s'imprime pas ;
- ✅ une seule grille d'axes sur toutes les feuilles ;
- ✅ cartouche honnête : redessiné par une IA, à valider et sceller par un professionnel, AUCUN sceau ;
- ◐ index des feuilles sur la première ;
- ◐ blocs pour tout ce qui se répète (fenêtres, appareils, bulles).

**Contrôles avant de livrer** :
- ✅ `doc.audit()` à 0 erreur ; relecture ODA ; aperçus PNG et zooms sur cotes, notes et bords ;
- ✅ aucun texte qui se chevauche, rien hors du cadre ;
- ◐ Règle 5 entre les feuilles et avec le 3D : même nombre d'ouvertures par façade, mêmes niveaux, mêmes aires.
- ✅ **Cotes écrites de l'original contre les nôtres** (vérification 2B de Bungalow) :
  - lister chaque cote écrite de chaque feuille d'origine, puis la chercher sur la nôtre, à 1/4" près ;
  - ce contrôle a trouvé en quelques secondes 13 cotes intérieures oubliées sur A-102 et 26 sur A-101 ;
  - si notre relevé diffère d'une cote ÉCRITE, c'est lui qu'on corrige : la cote écrite prime sur le dessin mesuré.
- ✅ **Contrôle « texte sur un trait » AVEC les lignes des cotes** : sans elles, l'agent voyait 1 étiquette barrée sur A-102,
  alors qu'il y en avait 8 (13 sur le jeu).
- ✅ **Une cote « TYPE » = une seule arête de référence, écrite dans les paramètres** (`DEBORD_FASCIA`, face du fascia).
  Sur A-103, une chaîne partait du fascia et l'autre du bord de la tôle : elles différaient de 2".
- ✅ **Tête et allège depuis le plancher de LEUR pièce** : les portes du garage se cotent depuis la dalle du garage, pas
  depuis le plancher du RDC.
- ✅ **Aucun texte interne sur une feuille** : ni « modèle 3D en cours », ni la liste des livrables, ni un nom de fichier,
  ni une convention de PRIX ou de métré (« sous-sol compté à 100 % », produits du métré). Le plan porte l'architecture.

**Cotes intérieures, méthode vérifiée sur Bungalow (39 cotes ajoutées, 2026-09-25)** ✅ :
- Les cotes intérieures de l'original visent les axes des cloisons ET leurs bouts : baie sans porte, fin d'un muret vitré.
  Leurs lignes d'attache s'arrêtent parfois avant l'élément (le comptoir du frigo) : limiter la recherche à 2'.
- Poser les chaînes intérieures AVANT les libellés, comme un dessinateur, et glisser le texte de chaque cote le long de
  son segment. En 5 essais, les chaînes sans place sont passées de 20 sur 39 à 0.
- **La cote écrite prime, géométriquement** : chaque segment affiche la valeur écrite quand notre relevé la donne à 1/4"
  près ; sinon il garde notre valeur, et l'écart est signalé. Résultat : 38 sur 39.
- Une étiquette d'ouverture doit éviter la ligne d'attache qui n'existe pas encore (du milieu de l'ouverture vers sa
  chaîne) : la déclarer comme obstacle avant de poser les chaînes.
- Un écart INTERNE de l'original (4'-2" écrit, 4'-2 3/8" dessiné) ne se règle que par le relevé. Ne pas refaire un gel
  pour 1/2" : l'écrire dans les écarts.
- Deux paramètres pour un débord : l'un coté (face du fascia), l'autre pour la géométrie (bord de la tôle). La valeur
  écrite (10") est affichée partout, et les chaînes se ferment sur elle.

**Ajouts exigés par la vérification finale du projet Agrandissement** ✅ (faits le 2026-09-25) :
- **sens et entraxe des poutrelles et des fermes**, poutres et linteaux LVL, recopiés de l'original. Sans eux, le linteau de la
  porte de garage ne peut pas être dimensionné ;
- les **notes générales de l'original** recopiées fidèlement, 12 plus 3 (nous n'en avions que 5) ;
- le **tableau des aires habitables par étage**, calculé sur la géométrie, avec l'écart aux chiffres de l'original ;
- les **vues de l'existant** et la **légende de démolition** ;
- les **cotes insécables** dans les tableaux : « 5'-3 3/8" » ne se coupe jamais ;
- ◐ contrôle de masse des cotes : `DIMENSION.get_measurement()` comparé au texte forcé, en 1 s (231 sur 231 justes).

**Vérifié sur Agrandissement** (A-100 à A-104, 2 366 entités, 134 cotes, 0 erreur ODA, 0 chevauchement) ✅ :
- poché neuf et trame de l'existant « tel quel », grille unique avec bulles aux deux bouts ;
- **tableau des portes et fenêtres généré depuis le relevé**, repères F1xx et P1xx ; le recomptage par façade et par niveau
  devient un contrôle automatique (34 sur 34) ;
- les ouvertures existantes y figurent aussi, avec « ≈ » quand la cote est lue à l'échelle ;
- tableau des pièces (aire, fini, plafond), hexagones de murs, escaliers MONTE/DESCEND numérotés ;
- 3 chaînes de cotes ; plan de toiture ajouté ; tailles de texte : notes 1/8", pièces 5/32", cotes 3/32", titres 1/4".

Méthodes ✅ :
- **Pièces** : les calculer comme l'espace libre entre les murs, portes fermées. Deux pièces ouvertes l'une sur l'autre se
  départagent par les contours du relevé.
- **Libellés** : les poser APRÈS les cotes et les axes, avec un essai à blanc qui réduit le texte à 3/32" s'il n'y a pas de
  place. Résultat : 0 chevauchement sur 5 feuilles.
- **Chaque étiquette de pièce d'origine se compare au contour mesuré** : ici « salon 14'-0" x 11'-6" » ne couvre qu'une partie
  d'une pièce ouverte de 26'-10⅞".
- **Toit plat butant sur plusieurs versants** : sa limite est une ligne de niveau différente sur chaque versant. La valeur lue à
  l'élévation (23'-9") contredisait le calcul (26'-3 7/16") : vérifier les deux.

**Vérifié sur Bungalow** (9 feuilles, 5 147 entités, 188 cotes, 0 erreur ODA, 43 contrôles de Règle 5 entre les feuilles) ✅ :
- **À ajouter à chaque jeu** : un **plan clé** sur A-001 (renvois des élévations et des coupes) ; un **tableau des niveaux**
  avec l'origine de chaque valeur (écrite, relevée, calculée, mesurée) ; un **tableau des revêtements** par produit, avec
  le pas mesuré ; les écarts de Règle 5 écrits sur les feuilles, jamais tranchés en silence.
- **Redessiner TOUS les détails d'origine** et recopier leurs textes entre guillemets. Un détail oublié (le 3/5) était visé
  par un renvoi du plan des fondations.
- **Coupe au 1/2" sur ARCH D** : une maison de 44' ne tient qu'avec les niveaux d'un seul côté. Ligne de sol seulement
  à l'extérieur des faces des fondations, jamais à travers le garage.
- **Pose des textes** : réserver la place des cotes avant les notes de matériaux ; une ligne de rappel part du point du texte
  le plus proche de sa cible et ne traverse aucun texte ; couper les joints de revêtement et les niveaux sous les textes.
- **Pièges** : un mur poché est une HACHURE, ignorée comme obstacle par le placement (un libellé a atterri dans un mur de
  8") ; une hachure trop dense a pris 7,5 Go à l'aperçu. Garde-fou : diagonale ÷ espacement < 3 000 lignes.

**Jeu d'un escalier (escalier flottant d'après photo, 7 feuilles, 143 cotes, 2026-09-28)** ✅
- **Feuilles** :
  - A-001 : tableau de l'escalier, avec les valeurs du Code « à valider » ; tableau des vérifications tiré des contrôles
    des paramètres ; nomenclature des verres (hors tout, fixations, sabots) ; plan clé avec repères de coupe et point de
    vue de la photo ;
  - plans des niveaux au 1/2" ;
  - coupes des deux voies et coupe transversale au palier ;
  - détails de marche, fixation, sabot, main courante, pieds et arrivées de limons, nez de palier.
- **Conventions** :
  - la flèche MONTE ou DESCEND suit le sens de la marche DEPUIS le niveau du plan (au sous-sol : MONTE) ;
  - l'entrée d'une volée à la rive d'une trémie est notée et reste ouverte ;
  - la ligne d'échappée minimale est dessinée dans les coupes ;
  - un tableau des nez de marches donne X, dessus, dessous et côté.
- **Nuages de conflit et marques rouges pilotés par les données** : ils disparaissent d'eux-mêmes quand les paramètres sont
  corrigés.
- **Nouveau standard** : chaque fixation doit être DANS la pièce qu'elle tient, à la distance exigée des bords et des
  joints. La détection des interpénétrations ne voit pas une fixation « dans le vide ».
- **Passés de ◐ à ✅** : index des feuilles ; Règle 5 entre les feuilles, relue dans le DXF (`plans\regle5.py` : niveaux,
  contremarches, échappées, largeur, garde-corps, index) ; coupes (poché, au-delà, niveaux, escalier) ; escaliers en plan
  (numérotation, ligne de coupure).
- **Une coupe se place là où elle MONTRE ce qu'elle doit montrer** : vérifier qu'aucun élément coupé plus proche ne le
  cache. À sa 1re position, la coupe 3-3 passait dans le mur nord, qui cachait le verre ajouté du palier et le poteau.
- **PDF cherchable** sans toucher au rendu : les textes posés, invisibles, sous les tracés (CLAUDE.md).
- 🔴 **Mise en page lisible dans l'ERP (et dans AutoCAD)** ✅ (escalier, 2026-09-28, après les captures de Sylvain dans
  `/cad`) :
  - l'ESPACE OBJET ne porte que les vues à l'échelle, rangées serré : une bande par feuille dans l'ordre de l'index,
    20' à 30' de vide, coin en (0, 0) ; 3 bandes par rangée pour un écran 16:9 ;
  - l'ESPACE PAPIER porte le cartouche et TOUS les tableaux, notes, légendes, index et hypothèses ;
  - aucune fenêtre pleine page ;
  - drapeaux des fenêtres `0xC000` (0x8000 « toujours posé » + 0x4000 verrouillée), `0x20000` à 0. Sinon, l'afficheur
    de l'ERP tient la fenêtre pour éteinte ;
  - contrôles : écart entre fenêtres, entités orphelines, collisions entre l'espace papier et les vues, drapeaux et
    statut, et une comparaison avant/après entité par entité (`plans\verifier_compactage.py` de l'escalier).
- 🔴 **Livrable PDF, TOUJOURS** ✅ (standard de Sylvain, 2026-09-28 : « TOUJOURS faire le plan pdf comme dans ce
  projet ») : UN PDF de toutes les feuilles, dans l'ordre de l'index, au format réel et à l'échelle, noir sur blanc,
  poché gris, conflits en rouge, texte cherchable. Il est tiré du DXF final. Outil : `modeles\plans_pdf\plans_pdf.py`.
  - Un jeu livré AVANT cette règle se rattrape après coup : vérifier que l'empreinte écrite dans les propriétés du DXF est
    celle du DWG livré, puis lancer `plans_pdf.py` sur ce DXF. Agrandissement (2026-09-29) : 10 feuilles, 594 s, 0 défaut.
  - Un jeu sans feuille A-001 (Agrandissement : l'index est sur A-100) sort dans l'ordre des onglets : vérifier que cet ordre
    est celui de la liste des feuilles.
- **Relevé d'après photo** : le « nord » est CONVENTIONNEL (le fond de la photo). Le dire dans la note générale et sous
  la flèche du plan clé.

## 8. Apprendre des plans que Sylvain fournit (protocole, demandé le 2026-09-24)
Sylvain fournira d'autres plans au fil des sessions : **« qu'il s'en inspire, je veux qu'il apprenne de ceux-ci »**. Chaque plan
reçu est donc à la fois un MANDAT (le 3D, les plans) et une LEÇON. Il sert à améliorer le relevé (§ 1-5), le 3D (§ 6) et les plans
2D (§ 7).

À chaque plan fourni :
1. **Relevé** selon le § 1, avec les écarts de Règle 5 (§ 5).
2. **Étude de style**, faite par l'agent `dao` en 15 à 30 minutes et consignée dans `reference\etude_style.md` du projet.
   On y note ce qu'un professionnel a fait et que notre jeu doit imiter :
   - mise en page de la feuille : zones, colonne de notes, cartouche, index, révisions ;
   - légendes et symboles ; hachures de matériaux ; épaisseurs de trait ;
   - style des cotes (flèches, texte, chaînes) ; marques de niveau ;
   - repères de détails et de coupes ; tableaux (aires, compositions, ouvertures) ;
   - notes types ; niveau de détail de chaque vue.
   On y note aussi ce qui est à éviter : incohérences, surcharges, fautes.
   Des **agrandissements exemplaires** (`reference\zooms\`) illustrent chaque point.
3. **Galerie** : ajouter au § 8.1 une ligne par élément exemplaire (quoi, quel plan, chemin de l'image). Au prochain jeu, l'agent
   `dao` s'en inspire AVANT de dessiner.
4. **Comparaison finale** : notre jeu à côté de l'original, feuille par feuille (aperçus côte à côte).
   - Chaque manque devient une ligne du § 7 (standard) ou du § 8.2 (progrès à faire).
   - Chaque progrès confirmé passe de ◐ à ✅.
5. **Journal** (§ 9) : ce que ce plan a appris et ce qui s'est amélioré par rapport au précédent (mesuré : nombre d'éléments,
   durée, écarts).

### 8.1 Galerie de références (éléments exemplaires à imiter)
| Élément | Plan d'origine | Image de référence |
|---|---|---|
| Colonne de droite : notes générales, « l'entrepreneur doit », révisions, sceau, titre, concepteur, feuille | Agrandissement | `C:\Dev\Maison_Agrandissement_Blender\reference\pages\page_03.png` |
| Marques de niveau en cercle, chaînes de cotes à gauche des élévations | Agrandissement | `…\reference\zooms\elev_est_propose.png` |
| Repères de fenêtres « 36/54 » en élévation, notes de revêtement avec flèches | Agrandissement | `…\reference\zooms\elev_sud_propose.png` |
| Coupe synoptique, étiquettes de composition en cercles gris, notes de gestion de l'eau | Agrandissement | `…\reference\zooms\coupe_AA.png` |
| Plan proposé et vue de l'existant au 1/8" sur la même feuille | Agrandissement | `…\reference\zooms\etage_propose.png` |
| Légende encadrée avec ombre portée | Agrandissement | `…\reference\zooms\style_legende_A101.png` |
| Pièces avec pictogramme, étiquettes de fenêtres en cadre, hexagones de types de murs | Agrandissement | `…\reference\zooms\style_rdc_murs_etiquettes.png` |
| Chaînes de cotes à 3 niveaux | Agrandissement | `…\reference\zooms\style_rdc_chaines_cotes.png` |
| Escalier à contremarches numérotées, salle de bain en silhouette | Agrandissement | `…\reference\zooms\style_etage_escalier_sdb.png` |
| Détails dans des cadres arrondis, bulle de renvoi ovale | Agrandissement | `…\reference\zooms\style_fondation_details_D1_D2.png` |
| Encadré « Description des matériaux » | Agrandissement | `…\reference\zooms\style_elev_description_materiaux.png` |
| Liste des compositions en colonne | Agrandissement | `…\reference\zooms\style_coupe_compositions.png` |
| Niveaux en demi-cercle, notes soulignées avec flèche | Agrandissement | `…\reference\zooms\style_elev_niveaux_notes.png` |
| Cartouche vertical avec SUPERFICIES, légende de structure, diagramme des coupes | Bungalow (plan d'origine) | `C:\Dev\Maison_Bungalow_Blender\reference\zooms\style_cartouche_haut_superficies_legendes.png` |
| Légende des niveaux par hachure (dessus des murs de fondation) | Bungalow (plan d'origine) | `…\Maison_Bungalow_Blender\reference\zooms\style_cartouche_legendes_niveaux_structure_coupes.png` |
| Loupe sur le plan : mur de 8" = 6" + 2", deux marques NIV | Bungalow (plan d'origine) | `…\Maison_Bungalow_Blender\reference\zooms\style_fondation_loupe_mur.png` |
| Poutre LVL, poteaux Paralam, poutrelles par travée, renvoi de coupe | Bungalow (plan d'origine) | `…\Maison_Bungalow_Blender\reference\zooms\style_fondation_coupe_poutre_poutrelles.png` |
| Profils de fermes cotés (portées, talon, débords, appuis) | Bungalow (plan d'origine) | `…\Maison_Bungalow_Blender\reference\zooms\style_coupes_ferme_type_A.png` |
| Cuisine, buanderie, salle de bain identifiées | Bungalow (plan d'origine) | `…\Maison_Bungalow_Blender\reference\zooms\style_rdc_cuisine_buanderie_sdb.png` |
| Coupe de mur type : compositions, coupures, hachures de matériaux | Bungalow (plan d'origine) | `…\Maison_Bungalow_Blender\reference\zooms\style_coupe_mur_haut.png` |
| NOTRE jeu : plan clé, tableau des niveaux et de leur origine, tableau des revêtements | Bungalow (notre jeu) | `C:\Dev\Maison_Bungalow_Blender\plans\apercu_A-001.png`, `apercu_A-302.png` |

L'étude de style complète est dans `C:\Dev\Maison_Agrandissement_Blender\reference\etude_style.md` :
- traits de 0,11 à 0,51 mm, police Times, neuf en gris 50 %, existant en gris 93 % ;
- ce qu'il faut imiter et ce qu'il faut éviter.

### 8.2 Progrès à faire (écarts entre notre jeu et les originaux)
Comparaison côte à côte du projet Agrandissement (`plans\comparaison_A-*.png`, 2026-09-24).

Ce que l'original a et que nous n'avons pas encore :
- **Vue de l'existant au 1/8"** sur les feuilles de plan et d'élévation (demander à Sylvain s'il la veut).
- **Feuille de détails** : D-1 à D-5, et murs types M1, M2, M/F, C1 au 1" = 1'-0".
- **Boîte « aire habitable »** par étage ; sens des solives.
- **Numéros des contremarches** en élévation et en coupe ; cotes de l'escalier et du palier.
- Cotes « Fenêtres à 7'-0" ht » et « fenêtre = 5'-11" » en élévation.
- **Coupe** : structure (fermes, solives), isolant, drain, notes de drainage et de ventilation, échappée.

Ce que nous avons ajouté et que l'original n'a pas :
- tableaux des ouvertures et des pièces ;
- 3 chaînes de cotes ;
- plan de toiture ;
- coupes VRAIES (A-A et B-B) ;
- hachures au pas mesuré ;
- niveaux des deux côtés ;
- index des feuilles.

**Recettes vérifiées pour les élévations et les coupes** ✅ :
- **Coupe vraie par Line Art** : caméra orthographique devant le plan de coupe, `clip_start` exactement sur le plan (0 point
  devant). Le poché se calcule à part, par intersection maillage-plan, en chaînant les points par ARÊTE (paire d'indices de
  sommets), jamais par coordonnées arrondies. Décaler le plan de 0,006" pour qu'aucun sommet ne tombe dessus.
- **Hachures de matériaux** : une carte des matériaux, construite par un rayon par pouce depuis la caméra, dit où poser chaque
  hachure. Les lignes de planches du modèle vérifient le pas et calent le départ : 2D et 3D tombent ensemble.
  - Pour mesurer un pas sur du Line Art, apparier d'abord les deux arêtes de chaque couvre-joint ou joint, sinon on lit 7" au
    lieu de 8".
- **Tableau des compositions** : dans les vecteurs du PDF, les marques d'arborescence séparent les lignes de couche des lignes
  de suite. Le recopier fidèlement veut dire garder les coquilles.
- **Notes d'élévation** : l'original en place sous la ligne de sol. Le permettre (en évitant la bande de terre et le caché) a
  été nécessaire pour poser 11 notes sur la façade sud.
- ◐ Repères de coupe dans la colonne des bulles d'axes : plan compact, mais la ligne de coupe doit rester à 3' ou plus de tout
  axe.
- ◐ Un tableau des compositions occupe une demi-feuille ARCH D (2 colonnes d'environ 50 lignes).

## 9. Journal des projets
- **2026-09-24, Maison Agrandissement** (plans d'un technologue, rév. 4, 7 feuilles ARCH D vectorielles ; projet
  `C:\Dev\Maison_Agrandissement_Blender\`).
  - Maison de 1½ étage en maçonnerie avec toit à demi-croupe 12/12, lucarne et avancée 6/12 et 3/12. Agrandissement en L de
    2 étages à toit plat.
  - Gabarit relevé et contrôlé en 23 min par le chef.
  - Détail délégué à un agent `dao` ; modèle 3D et cadre des plans lancés en parallèle.
  - Standards des § 6 et 7 posés à la demande de Sylvain. Ce projet doit les vérifier : passer ◐ → ✅ ou corriger.
  - **Relevé détaillé** (agent `dao`) : 60 min, 228 appels d'outils.
    - 34 ouvertures, avec croisillons exacts ; même nombre au plan et aux élévations.
    - 33 cloisons, 20 portes, 3 escaliers, 16 appareils, 8 meubles, 10 pièces.
    - Tout l'extérieur ; 6 images de contrôle superposées au PDF.
    - Il a corrigé le gabarit du chef de ¼" à ½" (§ 1.5).
  - **Plans, étape 1** (agent `dao`) : 38 min, étude de style comprise (environ 25 min). La chaîne A-100 complète prend 40 s.
    Relue par ODA : 0 erreur, 0 chevauchement.
  - **3D** (agent `modelisation`) : 1 196 objets, 34 ouvertures sur 34. Les 4 élévations du PDF se superposent au modèle.
    9 rendus Cycles, dont le crépuscule et 2 coupes 3D. 1re passe en 2 h 27 ; 2e passe en 1 h 40, pour le cadrage calculé
    et l'herbe en brins.
  - **Jeu 2D** : 9 feuilles (A-100 à A-104, A-201, A-202, A-301, A-302), 230 cotes, 0 erreur ODA, 0 chevauchement, plus
    la comparaison côte à côte avec l'original. Puis A-105 « Existant et démolition », à la demande de Sylvain.
  - **DWG 3D** : 121 MESH, 1,09 Mo, même empreinte que le 2D et le métré.
  - **Vérification finale** (34 min) : « livrable après corrections ».
    - Défaut grave : l'annexe démolie, oubliée par TOUS (§ 1, 12 bis).
    - Défauts moyens : charpente de l'étage non dessinée ; raccord de structure ; notes générales incomplètes ; tableau des
      aires ; vues de l'existant.
    - Corrigé le 2026-09-25, puis A-105 « Existant et démolition » ajoutée : jeu final de 10 feuilles.
  - **2026-09-29** : PDF du jeu, à la demande de Sylvain (`plans\agrandissement_plans.pdf`, 10 pages, 3 749 textes
    cherchables). Tiré après coup du DXF final, sans rien régénérer (§ 7, « Livrable PDF »).

- **2026-09-25, Maison Bungalow** (plans d'un technologue, rév. 1, 6 feuilles Lettre tournées et réduites ;
  bungalow neuf sur sous-sol ; projet `C:\Dev\Maison_Bungalow_Blender\`). C'est le plan de l'étalonnage du métré.
  - Gabarit du chef en environ 1 h, avec l'adaptation des outils à la rotation : toutes les chaînes de cotes et les
    4 élévations se recoupent au dixième de pouce ; 4 toits en gradins vérifiés par `controles()`.
  - Étude de style : 20 min. Relevé détaillé : 57 min, 18 ouvertures sur 18 concordantes, 6 superpositions ; il a corrigé
    le gabarit (dalle du garage à 5'-2").
  - 3D : 71 objets, 10 vues Cycles, superposition exacte sur les 4 élévations, 0 coplanaire visible ; photo hyperréaliste.
  - Jeu 2D : 9 feuilles, 188 cotes, comparaison côte à côte avec l'original. DWG 3D : 103 MESH, 0 pièce flottante.
  - Vérification, 1re passe : région administrative fausse et membrane d'étanchéité oubliée, tous deux corrigés.
  - Progrès sur Agrandissement : l'agent de relevé a vérifié la recherche d'existant (§ 1, 12 bis) dès le départ ; les
    décisions de Sylvain ont été demandées tôt, en 4 questions à la fois ; l'empreinte commune est un module partagé.
  - **Après-midi, passes 2B, 3 et 3B**. Le jeu est livrable, sur le gel F4.
    - 39 cotes intérieures de l'original ajoutées ; 38 affichent la valeur écrite.
    - 8 éléments recalés sur les cotes ÉCRITES : cloisons, conduit, drain, poteaux sur leurs sonotubes.
    - Massif sous la cheminée, cote de débord unique ; « hypothèse retenue » et non « décision du propriétaire ».
    - Aucune convention de prix sur les feuilles ; 0 texte posé sur un trait.
    - La comparaison « cotes écrites contre relevé » a été LA découverte de la journée (§ 7).

- **2026-09-28, Escalier flottant en U, d'après une PHOTO immobilière** (capture de 1528 × 1143, aucune cote ; projet
  `C:\Dev\Escalier_flottant_Blender\`). C'est le 1er relevé d'un INTÉRIEUR d'après photo.
  - Relevé et calage du chef en environ 1 h 20 : le plan frontal donne contremarche/giron, puis un calage libre suivi
    d'un calage sur des cotes conformes (7 3/4" × 8 1/2").
  - Équipe de 4 agents : M1 (modèle et rendus), M2 (décor et forêt), D (jeu 2D de 7 feuilles), V (vérification).
  - Sylvain a relevé sur son téléphone un verre qui fermait l'entrée de la volée du sous-sol. D'où le contrôle de
    circulation.
  - La vérification (47 min, « livrable après corrections ») a trouvé la rive nord du palier sans garde-corps, oubliée par
    tous, puis 5 points et 13 remarques. Tout a été corrigé dans les paramètres v7 ; gel F2.
  - Photos IA : la recette « re-photographie chaque surface » marche pour les deux vues ; une phrase « garde chaque
    verre » de trop rend une copie du rendu.
  - 2e vérification (17 min) : « LIVRABLE ». Il restait la porte du sous-sol dessinée en baie (Règle 5 sur le type
    d'ouverture) et 4 points de structure (poteau excentré, plaque de tête, chaise, verre ancré dans une rive de 7"), tous
    ajoutés à la liste de l'ingénieur. Livré le 2026-09-28 vers 16 h 15 : 2 photos réalistes, la planche, le PDF des
    plans, les DWG 2D et 3D.
  - Demande de Sylvain en fin de projet : « TOUJOURS faire le plan PDF comme dans ce projet » (§ 7,
    `modeles\plans_pdf\plans_pdf.py`).
- **2026-10-08 et 09, Escalier arrière Saint-Exemple** (immeuble d'habitation ; architecture de 41 feuilles,
  structure de 13 feuilles tournées, devis de 41 pages, une photo de mesures de chantier ; projet
  `C:\Dev\Escalier_Saint-Exemple_Blender\`). Premier projet de charpente métallique de FABRICATION : tout son savoir est
  dans `SAVOIR_CHARPENTE_METALLIQUE.md` (absent de l'édition publique).
  - Analyse du chef en 1 h 30 : inventaire des 4 documents, titres des feuilles, zooms, comparaison des mesures de
    chantier aux cotes du plan ; 24 écarts relevés, dont un étage plus haut de 155 mm que le plan.
  - Ce que ce jeu a appris de la LECTURE : § 4 (jeu à deux professionnels). Ce qu'il a appris du DESSIN de fabrication
    et de la vérification : le savoir de la charpente métallique, § 5 à § 9.
  - Livré le 2026-10-09 : assemblage général (9 feuilles), dessins d'atelier (204 feuilles), dossier laser, demande
    d'information de 27 points, fiche de chantier, questions à l'atelier ; 3 tours de vérification, 5 gels.

## 10. À faire au prochain plan
- Relire ce fichier en entier, surtout les § 6, 7 et 8, puis la galerie (§ 8.1) et les progrès à faire (§ 8.2).
- Commencer par le § 1, avec les scripts du § 2 copiés dans `reference\`, puis appliquer le protocole du § 8.
- Demander d'emblée à Sylvain :
  - la maison est-elle construite telle que dessinée ?
  - veut-il l'état proposé seulement, ou aussi l'existant ?
  - quel usage ont les pièces non nommées ?
  - veut-il un dépôt dans /cad ? une photo hyperréaliste ?
- Vérifier d'emblée : la rotation des pages et l'échelle réelle (chaînes de cotes) ; la région administrative (Québec.ca) ;
  la table des appuis de chaque ferme ; chaque couche de chaque composition contre le métré.
- Sylvain tranche vite quand on lui présente 4 questions à la fois, recommandation en premier. Par défaut, le 2D et le 3D
  suivent le dessin ; le MÉTRÉ suit la pratique réelle de l'entreprise (`SAVOIR_METRE.md` § 0.5, absent de l'édition publique).
- Demander d'emblée s'il existe de VRAIS CHIFFRES (bordereau réel, heures, devis) pour ce plan ou pour un plan semblable.
- **Dès le relevé**, et pas seulement à la vérification : comparer TOUTES les cotes écrites de l'original à nos relevés,
  avec l'outil `modeles\projet_bungalow\plans\outils\comparer_cotes_interieures.py`. La
  cote écrite prime ; un écart de plus de 1/4" se corrige dans le relevé, avant le 1er gel. On évite ainsi un gel de plus.
- **D'après une photo** (escalier, 2026-09-28) :
  - caler la caméra d'abord librement, puis sur des cotes conformes au Code ;
  - projeter les paramètres sur la photo avant de modéliser ;
  - avant de fermer une rive par un garde-corps, vérifier la circulation : l'entrée et l'arrivée de chaque volée doivent
    rester libres ;
  - vérifier aussi l'inverse : chaque rive dont la chute dépasse 600 mm a un garde-corps (valeur à valider). La rive nord
    du palier, au-dessus de la cuisine, n'en avait pas, et seule la vérification l'a vu ;
  - chaque arrivée de volée doit mener quelque part (porte, passage) ; chaque appui (poteau, chaise, limon) repose EN
    ENTIER sur une pièce porteuse, au niveau réel de cette pièce ;
  - montrer tôt des aperçus : Sylvain les regarde sur son téléphone et relève vite ce qui cloche à l'usage.
- Ajouter ici toute convention nouvelle, tout piège et tout standard, marqués ✅ ou ◐.
