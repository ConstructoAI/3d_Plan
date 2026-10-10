# PDF 3D — d'un `.blend` à un PDF dont le modèle se manipule à la souris

Outil du poste Blender, écrit le 2026-10-09 pour l'escalier Saint-Exemple (charpente métallique
de fabrication) et fait pour **tous les projets** : maison, garage, équipement, charpente.
Un « PDF 3D » est un PDF ordinaire dont une page porte une annotation 3D : dans Adobe Acrobat
Reader ou PDF-XChange Editor, on fait tourner le modèle, on le mesure, on isole une pièce.

## La commande

```powershell
& $env:BM_PYTHON -X utf8 -s modeles\pdf_3d\pdf_3d.py <fichier.blend> --sortie x.pdf --titre "…"
```

Elle lance elle-même Blender en arrière-plan (extraction, sans carte graphique), puis Node
(écriture), **relit ce qu'elle a produit** et finit par `PDF_3D_OK <chemin>`, ou par un code de
sortie non nul avec la cause en clair (`PDF_3D_ERREUR (code n) : …`).
**L'outil n'ouvre JAMAIS le lecteur PDF de lui-même** : ni `pdf_3d.py`, ni les bancs, ni les
contrôles n'ouvrent de fenêtre. Seul `voir_dans_lecteur.ps1 … -Prevenu`, lancé À LA MAIN, ouvre une
fenêtre sur le poste : **prévenir l'utilisateur avant**, une capture par fichier, jamais en série.
Le `.blend` n'est **jamais** modifié ni enregistré ; donner une copie si un autre agent y travaille.
Aucun chemin en dur : Blender, Node et Python viennent de `outils\chemins.py` (ou de `BM_BLENDER`,
`BM_NODE`). Rien à installer : ni `npm install`, ni `pip`.

| Code | Cause |
|---|---|
| 0 | `PDF_3D_OK` |
| 2 | arguments (fichier absent, `--simple` avec `--unite mm`, vue mal écrite…) |
| 3 | Blender ou Node introuvable |
| 4 | l'extraction par Blender a échoué, ou rien à écrire |
| 5 | trop de triangles pour le plafond (le message donne le tableau par collection) |
| 6 | l'écriture par Node a échoué |
| 7 | le PDF est écrit mais un contrôle échoue (voir le rapport) |
| 8 | plus de 7 lignes sous le cadre (les suivantes seraient perdues sans un mot) |

Durées mesurées (poste i5-3470, avec d'autres agents qui tournent) : escalier de 2 711 pièces et
324 088 triangles, 13 à 26 s par PDF, contrôle compris (extraction 5 à 15 s ; le lecteur à part
décode le U3D compressé en 2 à 4 s) ; garage de 39 pièces, 13 à 16 s (dont 12 s d'extraction : le
`.blend` porte 431 686 instances de feuilles, écartées mais évaluées).

## Pour un nouveau projet : la recette

1. **Le modèle.** N'importe quel `.blend` du poste. Si un autre agent y travaille, en donner une
   COPIE (la commande ne l'enregistre jamais, mais elle doit le lire en entier).
2. **La commande**, sans option : la version « de fabrication ». Lire ce qu'elle dit avoir écarté
   (décor, particules, objets masqués) : c'est dit, jamais fait en silence. Ajouter `--titre`, des
   `--ligne` (projet, adresse, client, référence du gel des sources, unité) et, si le modèle n'est
   pas « de face côté −Y », des `--vue "Nom=azimut,élévation[,ortho]"`.
3. **`PDF_3D_OK`** et le rapport `x.controle.txt` : 0 échec. Mettre dans `--interdit` le jargon
   de l'équipe (codes de gel, rôles, prénoms, extensions de fichiers de travail) : le contrôle
   cherche dans la page, les propriétés du PDF, les vues, l'arbre et les fiches.
4. **Un lecteur tiers** : `lecteur_tiers.py x.pdf --sortie dossier` (2 min). Il doit CHARGER le
   fichier, et son image (une silhouette vue de dessus) doit ressembler au modèle.
5. **Le vrai lecteur**, seulement si l'utilisateur est PRÉVENU (une fenêtre s'ouvre devant lui) :
   `voir_dans_lecteur.ps1 … -Prevenu`, UNE fois par fichier, puis regarder la capture. Si le
   bandeau jaune est là, l'écrire (« affichage non vérifié sur ce poste : activer le contenu 3D »)
   et le demander au client ; ne jamais toucher à ses réglages. Sinon, s'en tenir à la structure
   (étapes 3 et 4) et le dire.
6. **Le montrer** : le PDF, et la planche de `apercu_u3d.py --planche` (ce que contient le fichier,
   vue par vue), en disant ce qu'elle est : notre lecture, pas le rendu d'un lecteur PDF.
7. **Un projet à catalogue de pièces** (marques, assemblages, boulonnerie) : copier le dossier
   `pdf3d\` de `C:\Dev\Escalier_Saint-Exemple_Blender\` — `produire_pdf3d.py` (titre, lignes, vues,
   garde-fou « le .blend est-il du bon gel », écriture provisoire puis publication),
   `etiquettes_escalier.py` (libellés et fiches tirés du catalogue), `controler_escalier.py`
   (pièces par marque, assemblages et boulons face au catalogue ; les deux codages comparés).
   Les objets du `.blend` doivent porter les propriétés `marque`, `assemblage`, `repere`, `boulon`.

## Deux versions

| | `--simple` | par défaut : « de fabrication » |
|---|---|---|
| Écrivain | **les fichiers de l'ERP, inchangés** (`erp\atelier\exportPdf3d.ts`, `u3dWriter.ts`) | `u3dWriterMulti.ts` et `exportPdf3dMulti.ts`, écrits à côté |
| Modèle | UN maillage, sommets fusionnés à 0,01 mm | une pièce par objet du `.blend` |
| Arbre du modèle | un seul nœud | groupes (collections ou assemblages) puis pièces |
| Couleurs | aucune matière : gris du lecteur | la matière de chaque objet (diffus, ambiant, opacité) |
| Maillages | tout est recopié | un maillage posé 300 fois n'est écrit qu'une fois |
| Normales | laissées au lecteur | celles de Blender (arêtes vives conservées) |
| Vues | une, cadrage laissé au lecteur | plusieurs, nommées, avec caméra, rendu, éclairage, fond |
| Fiche d'une pièce | non | oui (propriétés de l'objet, `--etiquettes`) |
| Codage du U3D | **sans compression** (profil `0x04`) : dans la norme, mais un lecteur tiers au moins le refuse (voir plus bas) | **compressé** (codeur arithmétique de la norme, chap. 10), comme tous les fichiers U3D courants ; `--compat compresse=0` redonne la forme de l'ERP |
| Flux 3D dans le PDF | brut | Flate |
| Propriétés du PDF | aucune (l'ERP n'en écrit pas) | titre, auteur « Préparé par une IA (Claude) », sujet ; rien d'autre |
| Unité | mètre, toujours | `--unite m`, `mm` ou `po` |
| Plafond | 400 000 triangles (`MAX_TRIANGLES_PDF3D` de l'ERP) | 2 000 000 (`--plafond`) |
| Escalier Saint-Exemple (2 711 pièces, 324 088 triangles) | 7,23 Mo | 0,52 Mo (0,54 Mo avec `--compat compresse=0`) |

La page est la même dans les deux cas : A4 paysage, titre, cadre 3D, lignes de texte, et la même
apparence de repli (le message gris qu'affichent les lecteurs sans 3D et l'impression). C'est
prouvé à l'octet par `noeud\banc_multi.mjs`.

## Les options

**La page**
- `--titre "…"` : titre en haut de la page (défaut : le nom du `.blend`).
- `--ligne "…"` (répétable, 7 au plus, mention comprise) : lignes sous le cadre. `{faces}`,
  `{sommets}`, `{objets}`, `{groupes}`, `{maillages}`, `{unite}` y sont remplacés par les comptes
  RÉELS du fichier. Sans `--ligne`, une ligne de comptes (et une ligne d'aide en fabrication).
- `--mention "…"` : dernière ligne. Défaut : « PRÉPARÉ PAR UNE IA (CLAUDE) — document de travail, à
  valider et à sceller par un professionnel. Aucun sceau. » `--mention ""` l'ôte.
- `--auteur "…"`, `--sujet "…"` (version de fabrication) : les propriétés du PDF, celles que montre
  « Fichier > Propriétés » du lecteur. Le titre est celui de la page ; l'auteur vaut par défaut
  « Préparé par une IA (Claude) » et le sujet, la mention. Une valeur `""` n'est pas écrite. Rien
  d'autre n'y va : ni nom d'outil, ni date, ni flux XMP (deux exports du même modèle donnent le
  même fichier). `--simple` n'en écrit aucune, comme l'ERP.
- `--interdit "terme"` (répétable) : le contrôle échoue si ce terme paraît dans le PDF (page,
  propriétés, vues, noms et fiches du modèle), sans tenir compte de la casse. Y mettre le jargon de
  l'équipe : codes de gel, rôles, prénoms, extensions de fichiers de travail.

**Ce qu'on garde du `.blend`**
- `--exclure-collections A,B` / `--inclure-collections A,B` : par nom, descendantes comprises.
- `--tout-garder` (ou `--avec-decor`) : ne jamais écarter le décor de soi-même (voir plus bas).
- `--plafond N` : nombre de triangles posés au plus.
- `--particules` : garder les instances de particules (une forêt = des millions de faces).
- `--caches` : garder les objets masqués au rendu ou invisibles pour la caméra.

**L'arbre du modèle** (version de fabrication)
- `--arbre auto` (défaut) : les collections du `.blend` (un groupe par collection, imbriquées
  comme elles le sont) ; si des objets portent la propriété `assemblage`, l'arbre devient
  `assemblage` → `repere` → pièce, et le reste va sous sa collection (la boulonnerie par `boulon`).
- `--arbre collections` : toujours les collections. `--arbre p1,p2,…` : ces propriétés d'objet.
  Règle unique : un objet qui porte la 1re propriété est rangé sous les valeurs de celles qu'il
  porte ; sinon sous sa collection, puis sous les valeurs des suivantes.
- `--nom-prop marque` (défaut) : la propriété qui nomme la pièce. Le nœud s'appelle
  « marque · nom de l'objet » (les noms de nœud d'un U3D sont uniques, d'où le nom de l'objet).
- `--etiquettes fichier.json` : `{"etiquettes": {clé: libellé}, "fiches": {clé: {titre: valeur}}}`.
  La clé est une valeur de propriété (une marque, un assemblage, un groupe de boulons) ou un nom
  de collection. Le libellé remplace la clé dans l'arbre, la fiche s'ajoute à celle du nœud.
  Exemple complet : `C:\Dev\Escalier_Saint-Exemple_Blender\pdf3d\etiquettes_escalier.py`.
- `--sans-fiches` : ne pas écrire les fiches (métadonnées U3D des nœuds).

**Les vues** (version de fabrication)
- `--vue "Nom=azimut,élévation[,ortho]"` (répétable). Azimut 0 : la caméra est DEVANT (côté −Y)
  et regarde vers +Y ; 90 : à droite (+X) ; 180 : derrière ; −90 : à gauche. Élévation 90 : du
  dessus. Défaut : Isométrique (45, 30), Face (0, 0), Côté (90, 0), Dessus (0, 90), les trois
  dernières en orthographique. Chaque vue cadre tout le modèle.
- `--cameras` : une vue par caméra du `.blend` (cadrage approché, voir « Limites »).
- `--vues-par-groupe` : une vue « Isoler : X » par groupe de 1er niveau (les autres sont masqués).
- `--vue-defaut N` ou `--vue-defaut "Nom"` : la vue d'ouverture.
- `--rendu Solid` (ou `SolidOutline`, `Illustration`, `SolidWireframe`…), `--eclairage CAD` (ou
  `Day`, `White`, `Headlamp`, `Hard`…), `--fond r,v,b`.
- `--sans-arbre-ouvert` : ne pas demander l'ouverture de l'arbre du modèle à l'activation.

**Divers**
- `--unite m|mm|po` : unité des coordonnées écrites ; l'unité du `.blend` se lit dans la scène.
- `--sans-normales` : laisser le lecteur calculer les normales (fichier plus petit).
- `--sans-compression` : flux 3D du PDF sans Flate, comme l'ERP (à ne pas confondre avec le
  codage du U3D lui-même, ci-dessous).
- `--compat "compresse=0,priorite=0,…"` : coupe un à un les choix d'écriture du U3D (voir plus
  bas), pour chercher ce qui gênerait un lecteur. Ne change pas la géométrie. `compresse=0` :
  U3D sans compression, la forme qu'écrit l'ERP ; `zeroFinal=1` (sans compression seulement),
  `chainesDeGroupe=0`, `fiches=0`, `unitesDefinies=0`, `attributsNuancage=15`.
- `--travail dossier` : garder `scene.json`, `scene.bin`, `ecriture.json` et les journaux.
- `--u3d fichier.u3d` : écrire aussi le U3D seul. `--controle rapport.txt` : où écrire le rapport
  (défaut : `<sortie>.controle.txt`).

## Ce qui est pris, ce qui est écarté — et c'est toujours DIT

- On prend ce que le **rendu** montrerait : objets et collections non masqués au rendu,
  modificateurs appliqués avec leurs réglages de rendu (maillage évalué), instances de collection.
- Écartés par défaut, avec leur compte dans le journal : instances de **particules**, objets
  masqués au rendu, objets invisibles pour la caméra (aides d'éclairage), caméras, lumières.
- **Décor** : une collection dont le nom dit du décor (`TERRAIN`, `SOL`, `GAZON`, `VEGETATION`,
  `ARBRES`, `DECOR`, `CONTEXTE…`, `CTX-…`, `VOISINS`, `CIEL`, `Aménagement paysager`… : listes
  `DECOR` et `DECOR_DEBUTS` de `pdf_3d.py`, sans casse ni accents) est écartée **seulement si elle
  écrase le modèle** : elle en multiplie l'étendue par plus de 3, elle pèse à elle seule plus de
  triangles que tout le reste, ou le plafond est dépassé. Le journal et le rapport donnent la
  collection et la raison. `--tout-garder` l'interdit. Mesuré sur cinq `.blend` du poste :

  | `.blend` | Écarté de soi-même | Reste |
  |---|---|---|
  | Garage rouge | `TERRAIN` (étendue 240 → 1 983 m), `VEGETATION` ; 431 686 instances de feuilles | 39 pièces, 8 140 triangles |
  | Maison Bungalow | `CONTEXTE` (25 → 1 364 m) ; 103 069 instances | 70 pièces, 37 918 triangles |
  | Maison québécoise | `Aménagement paysager` (21 → 205 m) ; 23 144 instances | 58 pièces, 20 388 triangles |
  | Escalier flottant | `CONTEXTE-EXTERIEUR` (20 → 341 m : une forêt de 119 millions de triangles en 2 127 instances) | 101 pièces, 169 300 triangles |
  | Escalier Saint-Exemple | rien (le contexte `CTX-…` n'écrase rien ; le projet l'écarte par `--exclure-collections`) | 2 711 pièces, 324 088 triangles |
- Triangles dégénérés et sommets orphelins retirés (le lecteur cadre sur l'étendue des sommets).
- Couleur d'une matière : la couleur de base du Principled ; si elle vient d'une texture, la
  couleur d'affichage du matériau. Convertie de linéaire en sRGB. Opacité : l'alpha du Principled
  et de la couleur d'affichage ; 0,35 pour un verre (transmission, Glass, Transparent).
  Les textures ne sont pas écrites.

## Les contrôles (faits à chaque appel)

`controle_pdf3d.py` relit le PDF de trois façons indépendantes des écrivains :
1. le fichier brut : en-tête, table `xref` (chaque décalage tombe sur son objet), `startxref` ;
2. PyMuPDF : ouverture sans réparation, annotation `/Subtype /3D` complète (`/3DD`, `/3DV`, `/3DA`,
   `/AP`), flux `/Type /3D /Subtype /U3D` dont la longueur est celle que le U3D annonce, vues bien
   formées (caméra orthonormée et NON en miroir, `/CO`, projection, rendu, éclairage), apparence de
   repli non blanche, textes attendus sur la page, **propriétés du document** (celles voulues et
   aucune autre : ni outil, ni date, ni XMP) ; puis **pypdf en mode strict**, un second lecteur de
   PDF : aucun avertissement, le même U3D à l'octet, les mêmes noms de vues, les mêmes propriétés ;
3. le U3D relu par `lire_u3d.py`, un **lecteur à part écrit d'après la norme** (ECMA-363) :
   alignement, tailles, taille des déclarations, noms référencés tous définis (parent, ressource,
   nuanceur, matériau), indices dans les bornes, hiérarchie sans cycle. Il lit les deux codages :
   son **décodeur arithmétique**, porté du côté LECTURE de la norme (chap. 10, annexe A), redonne
   les faces d'un U3D compressé — c'est lui qui prouve que ce qu'on a compressé se relit.
Puis les comptes (pièces, maillages, triangles) et la **boîte englobante** sont confrontés à ce
que Blender a fourni, et l'arbre à ce qui était voulu, nœud par nœud.

Autres outils :
- `apercu_u3d.py x.pdf --sortie dossier --planche` : dessine ce que CONTIENT le PDF, vue par vue
  (notre lecture du fichier : hiérarchie, matrices, matières, caméras). Ce n'est pas le rendu
  d'un lecteur PDF ; ça montre une pièce posée de travers ou une vue qui regarde ailleurs.
- `lecteur_tiers.py x.pdf|x.u3d --sortie dossier` : fait lire le U3D par Aspose.CAD (paquet
  `aspose-cad` du Python du poste, sans licence : image estampillée, silhouette noire vue de
  dessus). Un lecteur écrit par d'autres : s'il charge le fichier et dessine la bonne forme, le
  codage est juste pour quelqu'un d'autre que nous. Il ne lit QUE les U3D compressés.
- `banc_outil.py` (48 essais, 60 s, sans Blender) : scènes relues, compressé contre non compressé
  (9 000 faces, 17 000 positions, une face), 29 mutations que les contrôles doivent VOIR (U3D dans
  les deux codages, PDF, propriétés du document), et la preuve que le mini-banc des tests de
  l'ERP peut rougir.
- `noeud\banc_erp.mjs` : rejoue les **37 tests de l'ERP** sur `u3dWriter.ts` et `exportPdf3d.ts`
  (fichiers de test copiés tels quels ; `sceneTriangles.test.ts` ne l'est pas : il lui faut
  three.js). `noeud\banc_multi.mjs` : 27 essais des écrivains multi-pièces, dont un à RÉPONSE
  CONNUE (le codeur rend, bit pour bit, les octets de l'encodeur d'Adobe pour le cube de
  `dice.u3d`).

```powershell
& $env:BM_NODE --import ./noeud/crochet_ts.mjs ./noeud/banc_erp.mjs     # depuis modeles\pdf_3d
& $env:BM_PYTHON -X utf8 -s modeles\pdf_3d\banc_outil.py
```

## Ce qui est prouvé, ce qui ne l'est pas (état au 2026-10-09)

| Affirmation | Preuve, ou son absence |
|---|---|
| Le PDF est bien formé | fichier brut, PyMuPDF sans réparation, pypdf en mode strict : à chaque appel |
| Le U3D est bien formé | lecteur à part (`lire_u3d.py`) : à chaque appel ; 29 mutations vues par les bancs |
| La géométrie est celle du `.blend` | comptes et boîte englobante face à Blender : à chaque appel |
| Les pièces sont celles du catalogue | contrôle du projet (Saint-Exemple : pièces par marque, assemblages, boulons) |
| Le U3D COMPRESSÉ se décode | notre codeur rend les octets de l'encodeur d'Adobe bit pour bit (47 160 symboles rejoués) ; notre décodeur, éprouvé sur ce même fichier d'Adobe (22 surfaces fermées) ; compressé = non compressé sur 50 scènes et les cas limites ; **Aspose.CAD le charge et dessine la bonne forme**, escalier entier compris |
| Le U3D NON compressé se décode | notre lecteur ; le décodeur de référence d'Intel l'accepte (lu dans son code) ; **Aspose.CAD le REFUSE**, celui de l'ERP compris |
| PDF-XChange AFFICHE la version de fabrication, U3D non compressé | **OUI, capture** du 2026-10-09 à 13 h 19 (escalier Saint-Exemple, 2 711 pièces) : pas de bandeau, modèle debout (Z en haut), cadré comme notre aperçu de la vue d'ouverture, en couleurs |
| PDF-XChange AFFICHE la version de fabrication, U3D COMPRESSÉ | **OUI, capture** de 13 h 20 : la même image que la précédente |
| PDF-XChange AFFICHE la version `--simple` (écrivain de l'ERP) | **non vérifié** : la capture de 13 h 22 montre le bandeau jaune. Le contenu 3D n'était autorisé que fichier par fichier (un PDF jamais ouvert montrait aussi le bandeau à 13 h 24) : rien ne dit si ce fichier-là manquait de confiance ou si le lecteur refuse cette forme |
| L'arbre des pièces, le menu des vues, les vues orthographiques dans un lecteur PDF | non vérifié : il faut un clic, et on ne clique pas. La vue d'ouverture (perspective) est conforme à notre aperçu ; les autres vues sortent du même calcul |
| Adobe Acrobat Reader, Foxit | non vérifié : aucun des deux n'est installé sur ce poste. Indices pour Acrobat : notre codage compressé est, bit pour bit, celui de l'encodeur d'Adobe |

Mettre cette table à jour à chaque capture qui apprend quelque chose : fichier, codage, lecteur.

## Vérifier dans un vrai lecteur (PDF-XChange Editor)

Aucun contrôle ci-dessus ne prouve qu'un lecteur AFFICHE le modèle. Pour le voir :

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File modeles\pdf_3d\voir_dans_lecteur.ps1 `
    -Pdf C:\…\x.pdf -Sortie C:\…\capture.png -Attente 30 -Prevenu
& $env:BM_PYTHON -X utf8 -s modeles\pdf_3d\lire_capture.py C:\…\capture.png
```

**Ce script ouvre une fenêtre sur le poste, devant l'utilisateur, pendant toute l'attente.** Il ne
se lance qu'à la main, après l'avoir PRÉVENU : sans `-Prevenu` il refuse (code 7) et n'ouvre rien.
Une capture par fichier, jamais en série : le 2026-10-09, six ouvertures en sept minutes pendant
que l'utilisateur travaillait lui ont fait demander pourquoi le PDF 3D n'arrêtait pas de s'ouvrir.

Le script ouvre le PDF, attend, capture la fenêtre (PrintWindow, rendu complet), puis referme le
lecteur QU'IL a lancé (il refuse de démarrer si PDF-XChange tourne déjà : code 4 ; si le lecteur
se referme avant la capture, il le dit avec son code de sortie : code 6). Regarder ensuite l'image
avec l'outil Read. `lire_capture.py` dit en une ligne si le bandeau jaune est là (une BANDE d'une
quarantaine de lignes ; deux liserés de 3 lignes sous les onglets n'en sont pas un).

- **Bandeau jaune « Le contenu 3D a été désactivé »** : PDF-XChange bloque la 3D par sécurité.
  C'est à l'utilisateur de l'autoriser, jamais à nous : Fichier → Préférences → « Multimédia 3D »
  → « Activer le contenu 3D » (réglage global, le seul qui vaille pour les fichiers à venir), ou
  bandeau → Options → faire confiance à ce document (une fois, ou toujours : ne vaut que pour LE
  fichier cliqué). On ne touche pas à ce réglage par le registre. Tant que le bandeau est là,
  écrire dans le rapport : « affichage non vérifié sur ce poste : activer le contenu 3D ».
- Le lecteur tourne déjà (l'utilisateur regarde un PDF) : `voir_dans_lecteur.ps1` refuse (code 4)
  pour ne pas fermer sa session ; `capturer_fenetre_lecteur.ps1 -Sortie x.png` capture SA fenêtre
  sans rien lancer ni fermer (et ne restaure pas une fenêtre réduite).
- Le lecteur se trouve par `-Lecteur`, par `BM_LECTEUR_PDF3D`, puis par le registre (App Paths) et
  les dossiers d'installation habituels.
- PDF-XChange 11.1 a son PROPRE lecteur U3D (ce n'est pas la bibliothèque d'Intel) : arbre du
  modèle (masquer, isoler, zoom sur la pièce, transparence), vues avec visibilité des nœuds,
  mesure qui « utilise l'échelle et les unités du modèle », coupes. Il ne lit pas le PRC.

## D'où viennent les fichiers de l'ERP

Copies **inchangées**, prises le 2026-10-09 dans
le module DAO de l'ERP Constructo AI
(fichiers datés du 2026-10-06) :

| Copie (`erp\`) | sha256 |
|---|---|
| `atelier\u3dWriter.ts` | `15d031c05e2ed720fb215a2285249aab9edf99c70056e351258ac5a508e6fc63` |
| `atelier\exportPdf3d.ts` | `ec1145942d3523dd1e8cca4c0c315e15d02417ac2593212f5700c4e353b38124` |
| `atelier\sceneTriangles.ts` | `116307c00b4a1ea9a97841b57d2368549000156b71b3b6bf83f067db305b0752` |
| `__tests__\u3dWriter.test.ts` | `278f3cfc42eb0246d1c45a22b22ebbbc95dd2fdb129d9e59e5fecbf913355a23` |
| `__tests__\u3dInvariants.test.ts` | `296cc75be5653e0754bb97143d0191ddf97a3f9251a54d7ef8929901c557e27a` |
| `__tests__\exportPdf3d.test.ts` | `83cf91d72795d51172cb1e0fd8c19c0028d895a99f23bcd332992f7b811f09b0` |
| `__tests__\sceneTriangles.test.ts` | `b53a25b59cfc10d5cd2c000dfc2806b2f6c11a690233f0659052a49ed55bfead` |

`sceneTriangles.ts` n'est pas exécuté (il importe three.js) : on y LIT le plafond
`MAX_TRIANGLES_PDF3D`. Si l'ERP change ces fichiers, les recopier, mettre les sha256 à jour et
relancer les deux bancs. Ne jamais les retoucher ici : `--simple` doit rester « tel que l'ERP ».

Node 22.18 exécute ce TypeScript tel quel (types effacés). Ses imports sans extension
(`from './u3dWriter'`) sont résolus par `noeud\crochet_ts.mjs` (`--import`), sans toucher aux
fichiers ; `package.json` ne sert qu'à dire que ce dossier est en modules ES.

## Ce que la version de l'ERP fait, et ne fait pas

Elle écrit un U3D (ECMA-363) **sans compression** (profil `0x04`, plus `0x08` : unités définies,
1 unité = 1 mètre) : un nœud de modèle rattaché au monde, une ressource de maillage, les sommets
dédoublonnés à 0,01 mm, les faces. Puis un PDF 1.6 d'une page A4 paysage, avec l'annotation 3D,
une vue sans caméra (le lecteur cadre) et l'apparence de repli.
Elle ne fait pas : de matière (le modèle sort gris, sans relief entre les pièces), d'arbre (un
seul nœud : on ne peut ni isoler ni masquer une pièce), de normales (au lecteur de les calculer :
comme les sommets de pièces qui se touchent sont FUSIONNÉS, il peut lisser à travers deux
pièces), de vues nommées, de partage (300 barreaux = 300 copies), d'unité autre que le mètre.
Elle refuse au-delà de 400 000 triangles.

**À savoir sur le programme de l'ERP (mesuré le 2026-10-09, rien n'y a été modifié).** Son U3D est
écrit « sans compression ». C'est permis par la norme (profil `0x04`, depuis la 1re édition) et le
décodeur de référence d'Intel l'honore (`CIFXAuthorCLODDecoder.cpp`, `SetNoCompressionMode`) : un
lecteur de cette lignée, comme Acrobat, devrait l'afficher. Mais **un lecteur tiers le refuse** :
Aspose.CAD 26.6 (le paquet `aspose-cad` du Python du poste) lit et dessine l'échantillon public
`dice.u3d` et nos U3D compressés, et échoue sur TOUT U3D non compressé — celui de l'écrivain de
l'ERP inchangé comme les nôtres (« The given key … was not present in the dictionary » : il
décode comme si le fichier était compressé). Tous les fichiers U3D qu'on trouve dans la nature
sont compressés ; un lecteur a donc pu n'être jamais éprouvé sur l'autre forme. La version
`--simple` reste telle que l'ERP la fait, c'est sa raison d'être ; pour un PDF qui doit s'ouvrir
partout, prendre la version de fabrication. Rejouer l'essai (2 min) :
`& $env:BM_PYTHON -X utf8 -s modeles\pdf_3d\lecteur_tiers.py x_simple.pdf x.pdf --sortie dossier`
(« REFUSÉ » pour le premier, « CHARGÉ » pour le second). Ce qu'on ne sait pas encore : ce qu'en
font PDF-XChange et Acrobat, faute d'avoir pu regarder (voir « Ce qui est prouvé… »).

## Ce que la version « de fabrication » ajoute (blocs U3D vérifiés dans la norme)

| Bloc | Type | Rôle |
|---|---|---|
| Nœud de groupe | `0xFFFFFF21` | un assemblage, une collection |
| Nœud de modèle | `0xFFFFFF22` | une pièce : sa matrice, le nom de sa ressource |
| Modificateur de nuançage | `0xFFFFFF45` | dans la chaîne du NŒUD : un nuanceur par tranche de matière |
| Nuanceur | `0xFFFFFF53` | éclairage activé, mélange alpha, nom du matériau |
| Matériau | `0xFFFFFF54` | ambiant, diffus, spéculaire, émissif, réflectivité, opacité |
| Mise à jour de priorité | `0xFFFFFF15` | 256, avant les blocs de suite (comme la référence d'Intel) |

Chaque disposition a été relue dans ECMA-363 (4e édition) et dans le code de référence d'Intel
(« Universal 3D Sample Software »). Un écart entre les deux, écrit dans `u3dWriterMulti.ts` : la
référence compte le 1er bloc de suite dans la « taille des déclarations » (on suit la norme). Les
réglages `compat` de `buildU3DMulti` (option `--compat` de la commande) coupent les choix
d'écriture un à un, pour CHERCHER ce qui gênerait un lecteur (`noeud\ecrire_scene_json.mjs` écrit
une petite scène d'essai).

**Le codage compressé (par défaut).** Dans un U3D courant, les faces d'un maillage (tranche de
matière, indices de position et de normale) passent par un codeur arithmétique : contexte
dynamique pour la tranche (un histogramme qui s'adapte, avec un symbole d'échappement), contextes
statiques pour les indices (tous équiprobables parmi le nombre de positions), et un U32 nul pour
finir (§10.4.10 : il pousse dehors les derniers bits). `u3dWriterMulti.ts` porte l'écrivain ligne
à ligne depuis la référence (`CIFXBitStreamX.cpp`) et l'annexe A ; `lire_u3d.py` porte le
décodeur, à part. Ce qui le prouve, dans l'ordre où on peut s'y fier :
0. **réponse connue** : rejoués par notre codeur, les 47 160 symboles des 22 maillages de
   `dice.u3d` redonnent les octets de l'encodeur d'Adobe SANS UN BIT d'écart (296 473 bits utiles,
   vidange comprise ; Adobe ajoute ensuite 4 octets nuls que la norme ne demande pas). Le cube est
   resté dans `noeud\banc_multi.mjs` ;
1. le décodeur relit un fichier qu'on n'a PAS écrit : `dice.u3d` (Adobe), 22 maillages, 4 716
   faces, et chaque maillage redevient une surface FERMÉE et orientée (chaque arête partagée par
   deux faces, en sens opposés) — un décodage faux ne donne jamais cela ;
2. ce décodeur relit nos fichiers compressés en données identiques aux non compressés : 50 scènes
   au hasard et les cas limites (plus de 8 191 faces : l'histogramme est divisé par deux ; plus de
   16 382 positions : les indices sont écrits en clair mais passent toujours par le codeur) ;
3. un **lecteur tiers** les charge et dessine la bonne forme (`lecteur_tiers.py`, Aspose.CAD) :
   une plaque en L de 15 000 faces sort en L, un cadre de 16 900 positions garde son trou ;
4. les bancs le rejouent (`banc_outil.py`), mutations comprises : un octet faussé dans le flux
   compressé est signalé.
Les maillages de l'escalier Saint-Exemple sont petits (2 026 faces et 963 positions au plus) : ils
n'emploient que les chemins du codeur que `dice.u3d` éprouve.

**Face à un vrai fichier.** `lire_u3d.py` a relu `dice.u3d`, l'échantillon public des paquets
LaTeX movie15 et media9 (CTAN), écrit par le convertisseur 3DIF d'Adobe et affiché par Acrobat
depuis vingt ans : 23 groupes, 22 modèles, 22 modificateurs de nuançage, 7 nuanceurs, 7
matériaux, tous décodés sans erreur. Sa structure est celle qu'on écrit : chaînes de nœuds (groupes
compris), puis chaînes de ressources, nuanceurs (éclairage activé, test alpha `0x617`, mélange
`0x606`), matériaux (attributs `0x3F`), priorité 256 avant les suites. Ce qu'il fait autrement, et
qu'un lecteur tolère donc : sa « taille des déclarations » ne couvre que l'en-tête, une priorité 0
précède ses déclarations, ses modificateurs de nuançage ont des attributs à 0. Il est compressé,
comme ce qu'on écrit par défaut ; ses blocs de maillage laissent 66 à 73 bits après la dernière
face, les nôtres 32 à 44 (le U32 nul de la norme, sans plus). Pour séparer les causes devant un
lecteur muet : `noeud\envelopper_u3d.mjs fichier.u3d sortie.pdf` met un U3D qu'on sait bon dans
NOTRE page.
Côté PDF (ISO 32000-1 §13.6) : `/VA` de vues `/MS /M` avec `/C2W` et `/CO`, `/P`, `/BG`, `/RM`,
`/LS`, `/NA` (visibilité des nœuds), `/3DA /NP true` (arbre du modèle), `/OpenAction … /Fit`.

## Limites

- **Ce que l'outil ne prouve pas** : l'affichage dans un lecteur PDF. Voir « Ce qui est prouvé,
  ce qui ne l'est pas ».
- Pas de textures, pas d'arêtes dessinées, pas de cotes, pas d'animation.
- Vues tirées des caméras : le cadre du PDF (762 × 405 points) n'a pas les proportions du rendu,
  un objectif décentré est remplacé par une caméra ré-orientée (les verticales fuient un peu), et
  le plan de coupe proche (`clip_start`) n'est pas repris : une caméra qui « traverse » un mur
  voisin grâce à lui montrera ce mur.
- Les matières des métaux sont rendues par un diffus un peu éclairci et un reflet : un lecteur
  PDF n'a pas d'environnement à refléter.
- `--simple` : mètres seulement, 400 000 triangles au plus, une seule vue.
- 7 lignes sous le cadre, tronquées à la largeur de la page.
- La page est en A4 paysage, comme l'ERP.

## Pièges payés

- **Heredoc Bash et guillemets triples** : un script Python passé par `<<'EOF'` avec des `'''` a
  cassé le shell. Écrire le script avec l'outil Write.
- **Vitest sans l'installer** : `noeud\vitest_minimal.mjs` remplace `describe`, `it`, `expect`
  (les comparateurs que les tests de l'ERP emploient, pas un de plus : un comparateur inconnu
  lève une erreur au lieu de passer). Prouvé capable de rougir (3 copies abîmées de l'écrivain).
- **Un oracle peut avoir tort** : le 1er essai « même maillage que l'ERP » accusait le code ; c'est
  l'essai qui numérotait les sommets autrement que l'ERP (à leur 1re apparition dans la soupe).
- **Painter et grands triangles** : `apercu_u3d.py` peint du plus loin au plus près ; il découpe
  les grands triangles (par SURFACE à l'écran, pas par longueur : sinon 300 000 barreaux fins
  deviennent 2 800 000 triangles et 2 min).
- **Décor** : sans la règle du décor, le garage est un point au milieu d'un terrain de 1 400 m,
  et le gabarit des particules (posé à z = −100) étire encore la boîte.
- **Caméra en miroir** : `/C2W` = [droite, haut, regard, position] est un trièdre INDIRECT ; le
  contrôle le vérifie (déterminant −1).
- **PDF-XChange bloque la 3D** par défaut : la capture montre le message de repli et un bandeau
  jaune ; ce n'est pas un défaut du fichier.
- **Sortie de PyMuPDF** : les espaces insécables des nombres (« 321 750 ») ne ressortent pas tels
  quels à l'extraction ; comparer après avoir ramené toute espace à une espace simple.
- **Une chaîne modifiée par `sed` ou par un script change le fichier « sous » l'outil Edit** :
  relire avant de retoucher.
- **« Dans la norme » ne veut pas dire « lu partout »** : le U3D sans compression est permis depuis
  2004 et un lecteur tiers le refuse. Quand une forme est rare dans la nature, écrire la forme
  courante. Et chercher un lecteur tiers DÉJÀ sur le poste avant de conclure « non vérifiable » :
  `aspose-cad` lisait le U3D, il a suffi de le lui demander (`lecteur_tiers.py`, 2 min).
- **Le « zéro final » du maillage** : lu d'abord comme une habitude de l'encodeur de référence, à
  imiter ; c'est la vidange du codeur compressé (§10.4.10), qui n'a pas lieu d'être sans
  compression. Lire la norme jusqu'au bout avant d'imiter un octet.
- **Un contrôle qui compte doit suivre le modèle** : la boulonnerie du modèle a gagné des rondelles
  biseautées portant `type_boulon` ; le contrôle du projet les a comptées comme des boulons (715
  au lieu de 665). C'est la répétition sur le nouveau modèle, avant la livraison, qui l'a montré.
- **Le lecteur déjà ouvert par quelqu'un** : `voir_dans_lecteur.ps1` refuse alors de démarrer ;
  `capturer_fenetre_lecteur.ps1` capture sa fenêtre sans rien lancer ni fermer. Une « confiance
  pour cette fois » donnée par l'utilisateur ne vaut que pour SA fenêtre : le bandeau revient à
  l'ouverture suivante.
- **Des captures en série sur un poste où quelqu'un travaille** : six fenêtres de lecteur en sept
  minutes, et l'utilisateur demande pourquoi le PDF n'arrête pas de s'ouvrir. Une vérification
  qui s'affiche chez quelqu'un se fait UNE fois, annoncée ; le reste se prouve par la structure.
  D'où l'option `-Prevenu`, obligatoire.
- **Un outil de tri jamais éprouvé sur le cas « bon »** : `lire_capture.py` n'avait vu que des
  captures à bandeau ; à la première capture sans bandeau il en a vu un quand même (deux liserés
  jaunes sous les onglets). Un détecteur s'éprouve sur les deux cas avant qu'on s'y fie.

## Fichiers

| Fichier | Rôle |
|---|---|
| `pdf_3d.py` | LA commande : extraction, arbre, vues, écriture, contrôle |
| `extraire_blend.py` | tourne dans Blender : maillages distincts, objets, matières, caméras |
| `noeud\ecrire_pdf3d.mjs`, `noeud\fabrication.mjs` | écriture par Node (simple : ERP ; fabrication) |
| `u3dWriterMulti.ts`, `exportPdf3dMulti.ts` | les écrivains multi-pièces, à côté de ceux de l'ERP |
| `erp\` | copies inchangées de l'ERP (voir plus haut) |
| `lire_u3d.py` | lecteur U3D à part, d'après la norme |
| `controle_pdf3d.py` | contrôle d'un PDF 3D |
| `apercu_u3d.py` | images de ce que contient un PDF 3D |
| `voir_dans_lecteur.ps1`, `capturer_fenetre_lecteur.ps1`, `lire_capture.py` | essai dans PDF-XChange (ouvrir, capturer, refermer ; ou capturer une fenêtre déjà ouverte), tri des captures |
| `lecteur_tiers.py` | faire lire le U3D par un lecteur tiers (Aspose.CAD) et en tirer une image |
| `banc_outil.py`, `noeud\banc_erp.mjs`, `noeud\banc_multi.mjs` | les bancs |
| `noeud\crochet_ts.mjs`, `crochet_resolution.mjs`, `vitest_minimal.mjs` | plomberie Node |
| `noeud\ecrire_scene_json.mjs`, `noeud\envelopper_u3d.mjs` | petite scène d'essai en JSON ; U3D existant mis dans notre page |
