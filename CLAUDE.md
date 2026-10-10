# Poste de pilotage Blender (et export AutoCAD) — fichier vivant

Les sessions ouvertes ici pilotent **Blender 5.2 par scripts Python** et produisent des fichiers AutoCAD (DXF/DWG).
Tout ce qui suit est **vérifié sur ce poste** : ne pas le ré-explorer.
**Mettre ce fichier à jour à la fin de chaque session** (voir la dernière section).
Depuis le 2026-10-10, le DÉTAIL (pièges vérifiés) est dans les savoirs de la racine : voir « Savoirs détaillés ». Ce fichier reste sous 100 000 caractères.

> **Édition publique — une gracieuseté de Sylvain Leduc, président de Constructo AI inc.** (www.constructoai.ca)
> - Ce fichier est le « fichier vivant » d'un vrai poste de travail : « Sylvain » y désigne son auteur et premier
>   utilisateur. Adaptez les préférences aux vôtres ; Claude tient ce fichier à jour pour vous.
> - Les noms de clients, les adresses et les données internes ont été retirés ; les projets de référence portent des
>   noms génériques (« Bungalow », « Agrandissement », « Saint-Exemple »).
> - Certains fichiers cités n'existent que sur le poste d'origine : les programmes portables de `outils\`, le programme
>   Métré et `SAVOIR_METRE.md`, le format de soumission d'un entrepreneur, les études de cas et les dossiers
>   `C:\Dev\<Projet>\`, le savoir de la charpente métallique, le pont `freecad-mcp`, la compétence `courriels`.
>   `SAVOIR_PROJETS.md`, `JOURNAL_SESSIONS.md` et `outils\projet_en_cours.txt` sont à créer au premier projet.
>   Voir `README.md`, « Ce que le dépôt ne contient pas ».
> - Exigences : un compte **Claude Max 20x** (session en **Opus 5.5, effort max**) ; un compte Google et sa clé d'API
>   **Gemini** pour la photo hyperréaliste.

## À savoir en premier

- **Lanceur : `Demarrer-Blender.bat`** (double-clic) → vérifie ce fichier, les 5 profils et les outils, met Claude
  Code à jour (une fois par jour), puis ouvre la session en **Opus 5.5 contexte 1M (`claude-opus-5-5[1m]`), effort
  max**, en chef d'orchestre (modèle vérifié le 2026-09-23 par `claude -p ... --output-format json`).
  - **Menu**, dans l'esprit du START.bat d'OpenClaude (2026-09-25) ; le choix 1 part seul après 10 s :
    - 1) session du chef d'orchestre ; 2) reprendre la dernière session ;
    - 3) programme Métré ; 4) vérifier le poste ; 5) copier vers un autre poste ; 6) quitter ;
    - 7) reprendre une session d'AVANT le profil « zéro trace ».
  - Options : `/metre` (le Métré seul), `/choix N` (un choix du menu, puis sortie), `/verifier` (diagnostic seul) et
    `/verifier complet` (plus les essais de Blender portable, 80 s).
  - **Profils** (`.claude\agents\`, tous `model: inherit` + `effort: max` — ne jamais passer `model`/`effort` à
    l'outil Agent) : `modelisation` (Blender, rendus) · `dao` (DWG 3D, élévations, plans cotés) · `verification`
    (lecture seule, avant toute livraison) · `estimation` (Constructo AI, ✅ Agrandissement et Bungalow) · `bim-freecad`
    (○, jamais servi).

- ✅ **DOSSIER AUTONOME** (demande de Sylvain : « tout dans le même dossier, qui pourra être collé d'un poste à un autre
  sans rien » ; fait le 2026-09-25 par une équipe de 5 agents).
  - **Contenu** :
    - tous les programmes sont dans `outils\` (4,9 Go occupés sur le disque, mesurés par `du` le 2026-09-25 au soir) :
      - `python\` (3.13, 375 paquets, 2,5 Go), `blender\` (5.2 en mode portable) ;
      - `oda\convertisseur\` et `oda\visionneuse\` ;
      - `node\` (22.18) et `claude\` (Claude Code, exe natif) ;
      - depuis le soir du 2026-09-25 : `postgresql\` (18.1, 104 Mo, base du Métré), `git\` (Git et Git Bash 2.50.1,
        430 Mo, l'outil Bash de Claude) et `gh\` (GitHub CLI 2.83.0, 54 Mo) ;
      - `claude\config\` : le PROFIL de Claude (voir « Zéro trace ») ;
    - les scripts de référence d'un nouveau projet sont dans `modeles\`, avec leur `LISEZMOI.md` ;
    - le mode d'emploi pour Sylvain est `outils\LISEZMOI.md`.
  - **Preuve** (faite sur le poste d'origine ; cet essai n'est pas publié) : `outils\diagnostic\test_autonomie.ps1`, qui simule un poste neuf (PATH réduit, profil et TEMP
    redirigés, `CUDA_VISIBLE_DEVICES=-1`), donne **AUTONOME**.
    - 1re preuve : 85 OK, 0 échec, 3 replis prévus (Edge, qui fait partie de Windows), en 4 min 23 s.
    - ✅ **Soir du 2026-09-25**, lancé DEPUIS une vraie copie au chemin accentué (`…\blender-main copie é`) : 119 OK,
      3 replis prévus, 0 échec.
    - Le relevé des DLL réellement chargées ne montre AUCUNE DLL du redistribuable Visual C++ du poste : les copies
      portent les leurs.
  - ✅ **Transfert vers un autre poste** :
    - `outils\copier_vers_poste.ps1` arrête la base du Métré, copie, écrit le manifeste SHA-256 de chaque fichier, puis
      relance la base ;
    - `outils\verifier_copie.ps1` vérifie sur le poste d'arrivée (`-Rapide` : environ 35 s, au lieu de 8 à 9 min) ;
    - essai réel : « COPIE CONFORME, POSTE PRÊT », 120 069 fichiers.
  - ✅ **Zéro trace** (comme `C:\Dev\OpenClaude-Portable`, demande de Sylvain du 2026-09-25) :
    - `CLAUDE_CONFIG_DIR` = `outils\claude\config`, posé SEULEMENT si ce dossier existe ;
    - le profil y a été COPIÉ (680 fichiers) : réglages, skills, plugins, et les serveurs MCP de `.claude.json`
      (`freecad`, et `constructo-direct` sous la clé du projet) ;
    - ni identifiants, ni transcriptions, ni historique. `%USERPROFILE%\.claude` est resté intact ;
    - si le dossier est collé ailleurs, le lanceur recopie la mémoire du projet vers la nouvelle clé de chemin ;
    - **1er lancement** : Sylvain se connecte UNE fois, et sa connexion est ensuite rangée DANS le dossier. Traiter le
      dossier comme une clé. `/chrome` sera peut-être à refaire une fois (clé `claudeInChromeDefaultEnabled` non
      migrée) ;
    - **retour arrière** : `set BM_CLAUDE_CONFIG=profil`, ou renommer `outils\claude\config`. Le choix 7 du menu
      reprend une session d'avant.
    - Jamais éprouvé dans une vraie session au moment de l'écrire : la connexion, l'outil Bash avec le Git portable,
      Chrome.
  - **Lanceur** : il trouve chaque outil par `outils\chemins.cmd`. Il prend la copie PORTABLE d'abord, puis
    l'installation du poste en repli (affichée `[repli]`). Il pose, pour la session :
    - `BM_RACINE`, `BM_PYTHON`, `BM_BLENDER`, `BM_ODA_CONVERTISSEUR`, `BM_ODA_VISIONNEUSE`, `BM_NODE`,
      `BM_NAVIGATEUR` (Edge ; `BM_NAVIGATEUR=chrome` pour Chrome), `BM_PROJET` et `BM_ORIGINE_*` ;
    - `BM_POSTGRES` (le DOSSIER bin, jamais dans le PATH), `BM_GIT_BASH`, `BM_GH`, `CLAUDE_CODE_GIT_BASH_PATH` (le
      Git Bash portable pour l'outil Bash de Claude) et `CLAUDE_CONFIG_DIR` ; `outils\git\cmd` et `outils\gh` vont dans
      le PATH, après Python, Node et ODA ;
    - un PATH qui commence par Python, Node et ODA File Converter (ezdxf cherche d'abord `ODAFileConverter` dans le
      PATH) ;
    - pour les copies portables : `PYTHONNOUSERSITE=1` (sans `PYTHONHOME` ni `PYTHONPATH`),
      `npm_config_update_notifier=false`, `BLENDER_SYSTEM_RESOURCES` et `CUDA_CACHE_PATH` ;
    - il retire les `BLENDER_USER_*`, `BLENDER_SYSTEM_*`, `QT_*`, `NODE_OPTIONS` et `NODE_PATH` hérités.
    - `outils\python\Scripts` n'est JAMAIS dans le PATH (ses `.exe` visent l'ancien Python).
  - **Appeler les outils par ces variables** (`& $env:BM_BLENDER …`, `& $env:BM_PYTHON …`), ou par le module
    `outils\chemins.py`, JAMAIS par un chemin écrit en dur.
    - Fonctions du module : `blender_exe()`, `python_exe()`, `oda_convertisseur()`, `oda_visionneuse()`,
      `node_exe()`, `navigateur_pdf()`, `configurer_ezdxf_odafc()`, `env_blender()`, `verifier()`,
      `projet_en_cours()`, `postgres_bin()`, `git_bash()`, `git_exe()`, `gh_exe()` et `config_claude()`.
    - Dans un script : `sys.path.insert(0, os.path.join(os.environ["BM_RACINE"], "outils")); import chemins`.
    - Hors du lanceur : `. .\outils\chemins.ps1`.
  - **pip et pytest : toujours `& $env:BM_PYTHON -s -m pip …` et `-m pytest`.** Sur ce poste, un `pip` tapé seul
    trouverait celui du Python du système.
  - **Projet en cours** : `outils\projet_en_cours.txt`, une ligne `..\<Projet>`, à tenir à jour.
  - **Claude Code** : l'installation du poste d'abord, sinon la copie `outils\claude\claude.exe`, que le lanceur
    rafraîchit après chaque `claude update`.
  - **Vérifier** : `Demarrer-Blender.bat /verifier` ; `& $env:BM_PYTHON outils\chemins.py --complet` ;
    `outils\diagnostic\test_chemins.py` (36 essais) ; `outils\diagnostic\dependances_dll.py <dossier> --symboles`.
  - **Limites dites à Sylvain** :
    - la connexion à Claude se refait UNE fois par poste (zéro trace) ; celle de GitHub (`gh auth login`) reste par
      utilisateur Windows ; les clés d'API sont des variables de l'utilisateur, que le lanceur lit dans le registre
      sans jamais les écrire ;
    - le pilote de la carte graphique ne voyage pas (sans lui, rendu sur le processeur) ;
    - licence d'ODA : usage interne à l'entreprise ;
    - chemin du dossier : 110 caractères au plus ; après un transfert par ZIP, débloquer les fichiers ;
    - FreeCAD n'est pas dans le dossier : le serveur MCP `freecad` pointe hors du dossier.
  - **Décidé par Sylvain (2026-09-25)** :
    - `.claude\settings.json` du projet pose `CLAUDE_CODE_USE_POWERSHELL_TOOL=1`, pour une session ouverte sans le
      lanceur ;
    - le Python portable reste COMPLET (375 paquets, 2,5 Go) : pas d'allègement ;
    - pas de `.mcp.json` : FreeCAD n'est pas portable, et `constructo-direct` demande une connexion.
  - `modeles\` : les outils de référence d'un nouveau projet (relevé d'un plan PDF ou d'une photo, contrôles de rendu,
    DWG 3D, PDF du jeu, PDF 3D, prix budgétaire) ; voir `modeles\LISEZMOI.md`.
- 🔴 **PROFIL À INCARNER** (demandé par Sylvain le 2026-09-23) : `ENTREPRENEUR_GENERAL_QC_profil.txt` (racine du poste).
  - Le lire AU COMPLET au début de chaque session : environ 3 500 lignes et 75 000 jetons, par tranches de 738 lignes.
  - Tu es un **entrepreneur général chevronné du Québec** : 40 ans de métier, RBQ, multilogements.
  - Conventions de dessin OAQ/OTPQ :
    - trait épais pour les murs extérieurs et porteurs, trait fin pour les cloisons, pointillé pour le caché ;
    - fenêtre en double trait, porte en arc, escalier MONTE/DESCEND avec ligne de coupe ;
    - sanitaires en silhouette, électroménagers identifiés FRIG, CUIS., LV, SÉCH.
  - Jeu complet : implantation, un plan par étage, une élévation par façade, coupes, détails.
  - **Règle 5, la cohérence entre les pages** (superficies, hauteurs, ouvertures, compositions) : la vérifier et
    signaler les écarts AVANT de livrer.
  - Cartouche honnête : dessin fait par une IA, à valider et sceller par un professionnel. Ne JAMAIS simuler un sceau.
  - Budget : méthode cost-plus du profil.
    - Gamme **Économique** par défaut. Coût de base × 1,30 × 1,14975 en résidentiel neuf.
    - Poids par étage : RDC 100 %, étage intermédiaire 80 %, dernier étage 85 %. Rien d'inventé.
    - L'outil `calculer_prix_construction` du profil n'est PAS dans le MCP branché ici : faire le calcul étape par
      étape et l'afficher.
  - Présentation professionnelle en colonnes, titres en gras.
  - Deux autres profils métier ajoutés par Sylvain le 2026-09-23 (149 lignes chacun, génériques) :
    - `ARCHITECTE_profil.txt` → incarné par l'agent `dao`, qui dessine plans, élévations et coupes ;
    - `INGENIEUR_STRUCTURE_profil.txt` → incarné par l'agent `verification` (structure et cohérence).
    - Le chef d'orchestre reste l'entrepreneur général.
    - Ces profils disent « membre OAQ / OIQ » : on en prend l'expertise, JAMAIS le titre.
- 🔴 **SAVOIR VIVANT DE LECTURE DE PLANS** (demandé par Sylvain le 2026-09-24) :
  `SAVOIR_LECTURE_PLANS.md`.
  - Le lire AVANT tout relevé de plan (PDF, image, numérisation) : méthode éprouvée, boîte à outils, conventions des plans
    québécois, pièges et écarts de Règle 5 à chercher.
  - L'ENRICHIR à la fin de chaque projet : nouvelles conventions, pièges, écarts et une entrée au journal. Chaque plan lu
    doit rendre la session suivante meilleure.
  - Scripts de relevé de référence, à copier dans le projet suivant : `modeles\releve_pdf\` (plan PDF),
    `modeles\projet_bungalow\reference\` (pages tournées ou réduites), `modeles\releve_photo\` (d'après photo).
- 🔴 **PRIX BUDGÉTAIRE** : Sylvain veut qu'on refasse ce qui a été fait pour Agrandissement (2026-09-25).
  - Méthode du profil d'entrepreneur général, UN SEUL total, calcul affiché :
    - demander d'abord le mandat (règle 1) et les points qui changent le prix (garage chauffé ou froid, démolitions) ;
    - gamme Économique par défaut.
  - Calculateur : copier `modeles\projet_bungalow\estimation\prix_budgetaire.py` (entrées en JSON, exemple `entrees_exemple.json`,
    méthode des LIGNES AFFICHÉES : chaque ligne au cent, HT = somme des lignes).
  - 🔴 **Région administrative : la vérifier sur Québec.ca**, jamais de mémoire. Des MRC de la Montérégie, par exemple, sont passées à l'**Estrie** le 28 juillet 2021 (profil : 0,90 à 0,95).
- **Aucun MCP Blender** n'est branché (vérifié le 2026-09-23). On pilote Blender en ligne de commande :
  `& $env:BM_BLENDER -b --factory-startup --python script.py -- <args>`. C'est la copie portable
  `outils\blender\blender.exe` ; en Python, `chemins.blender_exe()` avec `env=chemins.env_blender()`.
  Pour montrer le résultat à l'utilisateur : `Start-Process $env:BM_BLENDER "<fichier.blend>"`.
- Blender 5.2.0 LTS ; le script de projet est la source de vérité, pas le .blend.
- Tous les autres outils disponibles (MCP, skills, agents, web) : voir **« Inventaire des outils »** ci-dessous.
- **Chaîne complète demandée par Sylvain** (photo → Blender → rendus → photo hyperréaliste → plans DWG → module CAD de
  l'ERP) : voir **« Chaîne de production »**. Projet modèle : `C:\Dev\Garage_rouge_Blender\`.
- **Python du poste** (3.13, ezdxf 1.4.4, Pillow 12) : `$env:BM_PYTHON`, copie portable `outils\python\python.exe`.
  Le Python de Blender n'a pas ezdxf : Blender extrait la géométrie en JSON, le Python du poste écrit le DXF.
  L'ancien Python installé (`%LOCALAPPDATA%\Programs\Python\Python313`) reste le repli de CE poste.
- **AutoCAD 2018 n'est PAS installé** (dossier résiduel sans `acad.exe` ni `accoreconsole.exe`) ; DWG TrueView non plus.
  L'association `.dwg` pointe vers eDrawings / un progid AutoCAD absent.
- **ODA File Converter 27.1** : `$env:BM_ODA_CONVERTISSEUR`, copie portable `outils\oda\convertisseur\`.
  DXF → DWG : `chemins.configurer_ezdxf_odafc()` (il pose `win_exec_path` ET met la bonne copie en tête du PATH,
  parce qu'ezdxf essaie `shutil.which` d'abord), puis
  `ezdxf.addons.odafc.export_dwg(doc, "x.dwg", version="R2018", replace=True)` ; relecture : `odafc.readfile("x.dwg")`.
- **ODA Viewer 27.1** : `$env:BM_ODA_VISIONNEUSE`, copie portable `outils\oda\visionneuse\`. Il **ignore** le fichier
  passé en argument : l'utilisateur doit faire FILE > Open lui-même.
- Matériel : GTX 1050 Ti 4 Go (Cycles **CUDA** ; OptiX listé mais plus lent), i5-3470 4 fils, 16 Go.
  Durées mesurées : EEVEE 1000×750 @16 éch. ≈ 15-20 s (1re compilation des shaders ≈ 90 s) ;
  Cycles 1600×1200 @192 ≈ 2-3 min ; Cycles + Freestyle 1600×1200 @96 ≈ 4,5 min. Ne jamais lancer 2 rendus GPU à la fois.

## Savoirs détaillés : lus AU BESOIN, pas chargés d'office (rangés ainsi le 2026-10-10)

Ce fichier ne porte plus que ce qui vaut pour TOUTES les sessions. Le détail vérifié est dans les fichiers ci-dessous, à la
racine du poste : **lire celui de la tâche AVANT de la commencer** (un agent lit celui que nomme sa fiche), et y verser
ce que la session apprend. Rien n'a été perdu en les sortant d'ici : leur texte est celui d'origine.

| Fichier | Ce qu'il contient | Le lire AVANT de… |
|---|---|---|
| `SAVOIR_BLENDER.md` | pièges vérifiés de l'API Blender 5.2 et du rendu (EEVEE, Cycles, Freestyle, compositeur, studio blanc), durées mesurées | écrire un script Blender ; lancer ou juger un rendu |
| `SAVOIR_DAO_DWG.md` | DXF et DWG avec ezdxf et ODA ; plans 2D cotés tirés du modèle (Line Art, cotes, présentations, aperçus) ; DWG 3D pour l'afficheur de l'ERP | produire ou corriger un DXF, un DWG, un jeu 2D ou son PDF |
| `SAVOIR_EQUIPE_AGENTS.md` | équipes d'agents : contrat d'interface, verrou GPU, gels et empreintes, relectures à trois regards, successeurs, dépôt et livraison | lancer ou reprendre une équipe ; geler ; faire relire avant de livrer |
| `SAVOIR_POSTE.md` | Windows, PowerShell, Git Bash, encodages, attentes en arrière-plan ; pièges du dossier autonome et des outils portables | écrire une commande délicate ; toucher au lanceur ou aux outils portables |
| `SAVOIR_LECTURE_PLANS.md` | les savoirs de métier (voir « À savoir en premier ») | un relevé de plan |

## Inventaire des outils (relevé le 2026-09-23)

Légende : ✅ utilisé et vérifié dans une session · ○ présent dans la liste d'outils, **pas encore testé ici**
(le tester avant de s'y fier, puis mettre à jour cette ligne).

**Outils de base de Claude Code**
- ✅ `PowerShell` (principal) et `Bash` (Git Bash) · ✅ `Read` (lit aussi les **images PNG** : c'est ainsi qu'on vérifie
  les rendus et les plans) · ✅ `Write` / `Edit` / `Grep` / `Glob`.
- ✅ Tâches longues : `run_in_background` + `Monitor` (le sommeil au premier plan est bloqué) · ✅ `TaskStop`.
- ✅ `AskUserQuestion` (décisions : installation, écrasement de fichier) · ✅ `WebFetch` (pages de téléchargement ODA).
- ✅ `Agent` (profils `modelisation` + `dao` en parallèle, `Explore` pour fouiller l'ERP, `general-purpose` pour une copie
  de module) · ✅ `SendMessage` : corriger un agent EN COURS (il lit le message à son prochain appel d'outil) — utilisé
  pour lui pousser de nouvelles dimensions ; ses scripts lisent `parametres_*.py`, donc rien à réécrire.
  - ✅ **Équipe de 5 profils** (brûleur, 2026-09-24) : `modelisation` × 2, `dao` × 2, `verification`.
  - `SendMessage` REPREND aussi un agent qui a fini, avec tout son contexte. C'est ainsi qu'on fait « prépare ta
    chaîne sur le modèle provisoire », puis « le modèle est final, relance ».
  - ✅ Dans l'autre sens (Bungalow, 2026-09-25) :
    - l'agent `estimation` (tous les outils) peut écrire à `main` en cours de travail : « gel prêt » ;
    - les agents `dao`, `modelisation` et `verification` n'ont pas `SendMessage` : ils ne parlent qu'en fin de tour.
    - Pour recevoir un résultat intermédiaire, leur faire ÉCRIRE un fichier, et l'attendre côté chef par
      `until [ -f f ] && [ âge ≥ 60 s ]` en arrière-plan. Ainsi, le tableau des cotes intérieures est arrivé pendant
      que l'agent continuait.
  - Méthode : voir `SAVOIR_EQUIPE_AGENTS.md`.
- ✅ **`SendUserFile`** (2026-09-24, Agrandissement) : c'est LA façon de MONTRER à Sylvain.
  - Images PNG et PDF en `display: "render"` (affichés dans le panneau) ; classeur .xlsx en `"attach"`.
  - `status: "proactive"` quand on lui pousse un livrable.
- ✅ **Équipe de 6 agents** sur Agrandissement : `dao` × 2 (relevé puis DWG 3D et DWG de métré ; jeu 2D), `modelisation`,
  `estimation` (premier usage : métré, puis estimation en PDF) et `verification` (contrôle final, qui a trouvé l'annexe
  démolie oubliée par tous).
- ✅ `WebSearch` (2026-09-25 : région administrative vérifiée sur Québec.ca et Statistique Québec) · ○ `Plan` · ○ `Artifact` (publier une page HTML privée sur claude.ai, p. ex. une présentation des rendus)
  · ○ `Workflow` (multi-agents : **seulement si l'utilisateur le demande**) · ○ `ScheduleWakeup` / `CronCreate` (tâches
  récurrentes).
- **Outils « différés »** (MCP et plusieurs outils ci-dessus) : les charger d'abord avec
  `ToolSearch` → `select:Nom1,Nom2` (un seul appel pour tous), sinon l'appel échoue.

**MCP branchés**
- ○ **FreeCAD** (`mcp__freecad__*` : `freecad_exec`, `freecad_document`, `freecad_inspect`, `freecad_export`,
  `freecad_planches`, `freecad_screenshot`, `freecad_status`, `freecad_undo`, `freecad_window`). Pont local
  `C:\Dev\freecad-mcp` (lire son `CLAUDE.md`) ; **charger le skill `freecad` avant tout travail FreeCAD**.
  Utile pour : BIM/Arch, mise en plan TechDraw cotée, export IFC/STEP (alternative à ezdxf).
- ○ **Constructo AI** (facultatif) : l'ERP de construction de l'auteur (`https://app.constructoai.ca`) offre à ses clients
  un connecteur MCP (CAO web `cao_*`, éditeur DWG `cad_*`, calculateurs, métré). Le poste fonctionne sans lui ;
  **aucune écriture dans un ERP sans l'accord explicite de l'utilisateur**.
- ✅ **Claude in Chrome** (`mcp__claude-in-chrome__*`) : l'ouverture d'onglet marche ; **la capture d'écran de `/cad` a échoué 3 fois** (« page busy », scène 3D lourde) → lui demander
  de regarder lui-même. Ne jamais saisir de mot de passe. ○ **Claude Docs** (documents vivants sur claude.ai).

**Skills** (outil `Skill`)
- ✅ `pdf` : chargé le 2026-09-24. L'estimation en PDF est faite avec reportlab 4.2.5, déjà installé, et les polices Arial
  TTF du système pour les accents.
- ✅ `entrepreneur-qc` : chargé par l'agent `estimation`.
- ○ `freecad` · ○ `courriels` (courriels dans Constructo) · ○ `dataviz` · ○ `artifact-design` · ○ `docx` / `pptx` /
  `xlsx` (openpyxl est installé et a servi au bordereau) · ○ `deep-research` · ○ `schedule` / `loop` · ○ `code-review` /
  `simplify` · ○ `skill-creator`.

**Enchaînements prometteurs (idées, non testées)** : quantités du modèle Blender (m² de déclin et de tôle,
nombre d'ouvertures) → `calculer_toiture` / `calculer_peinture` / skill `entrepreneur-qc` pour une soumission ;
mise en plan TechDraw via FreeCAD ; page `Artifact` des rendus. (Fait : la maison recréée dans la CAO Constructo.)

## Clés d'API (jamais dans un fichier)

- **Aucune clé n'est écrite dans ce dossier, et aucune ne doit l'être.** Chaque clé est une variable d'environnement de
  l'UTILISATEUR Windows : le lanceur la lit dans le registre (`HKCU\Environment`), sans jamais l'afficher ni l'écrire.
- `GOOGLE_GEMINI_API_KEY` : la clé d'API Google Gemini (compte Google, facturée à l'usage), pour la photo hyperréaliste
  (`Rendu3D_ERP\photo_hyperrealiste.py`). La créer sur `https://aistudio.google.com/apikey`, puis, une fois par poste,
  la faire SAISIR par l'utilisateur dans PowerShell (ainsi elle ne reste pas dans l'historique des commandes) :
  `$cle = Read-Host 'Cle Gemini' ; [Environment]::SetEnvironmentVariable('GOOGLE_GEMINI_API_KEY', $cle, 'User')`.
- Claude Code se connecte par le compte Claude de l'utilisateur (forfait Max 20x) : aucune clé d'API Anthropic.
- Ne jamais recopier une clé dans un script, un dépôt git, un commit ou un document partagé.

## Préférences de l'utilisateur (Sylvain)

- Français (Québec), construction résidentielle (Constructo AI). Il aime **voir les rendus** : les lui montrer.
- DAO : **pouces** (`$INSUNITS=1`), **affichage architectural** (`$LUNITS=4`), calques en MAJUSCULES avec tirets :
  `MURS-EXT, MURS-INT, OUVERTURES, TOIT, MENUISERIE, VITRAGE, COTES, TEXTE, DALLE, MOBILIER`.
- 🔴 **PLAN PDF, TOUJOURS** : demande de Sylvain du 2026-09-28 (« peux-tu TOUJOURS faire le plan pdf comme tu as fait
  dans ce projet pour les prochains projets »). Chaque jeu 2D sort AUSSI en UN PDF, comme
  `C:\Dev\Escalier_flottant_Blender\plans\escalier_plans.pdf` :
  - toutes les feuilles dans l'ordre de l'index, A-001 d'abord (index, notes, hypothèses, tableaux, plan clé) ;
  - au format réel (ARCH D 36" × 24") et à l'échelle : il s'imprime à 100 % ;
  - vectoriel : fond blanc, traits noirs aux épaisseurs des calques, poché gris, nuages de conflit en rouge ;
  - texte CHERCHABLE (posé, invisible, sous les tracés) ;
  - cartouche « PRÉPARÉ PAR UNE IA (CLAUDE) », aucun sceau, « à valider et à sceller par un professionnel » ;
  - tiré du DXF FINAL, dans la même génération que le DWG (même empreinte des sources) ;
  - outil : `modeles\plans_pdf\plans_pdf.py <jeu.dxf>`, ou sa fonction `pdf_jeu()` appelée par le générateur. Il se
    contrôle lui-même (une page par feuille, format, texte cherchable) ;
  - le montrer à Sylvain par `SendUserFile` (`display: "render"`), avec les aperçus ;
  - un jeu livré AVANT cette règle se rattrape après coup, sans rien régénérer : `plans_pdf.py` sur le DXF final, une fois
    vérifié que son empreinte (propriétés du fichier) est celle du DWG livré. Agrandissement, 2026-09-29 : 10 feuilles en
    594 s, avec 2 agents qui tournaient à côté ;
- ✅ **PDF 3D** (Sylvain, 2026-10-09 : « me donner aussi le PDF 3D, il existe déjà un programme à cet effet dans mon
  ERP module DAO », puis « le mettre dans le programme Blender pour les futurs projets ») : `modeles\pdf_3d\` (lire son
  `LISEZMOI.md`, « Pour un nouveau projet : la recette », et sa table « prouvé, pas prouvé »).
  - UNE commande, depuis n'importe quel `.blend` :
    `& $env:BM_PYTHON -X utf8 -s modeles\pdf_3d\pdf_3d.py <fichier.blend> --sortie x.pdf --titre "…" [--simple]`
    → Blender en arrière-plan sans carte graphique, Node, contrôles, puis `PDF_3D_OK`. AUCUNE fenêtre. 13 à 26 s pour
    l'escalier de Saint-Exemple (2 711 objets, 324 000 triangles, PDF de 0,5 Mo).
  - Par défaut, version « de fabrication » : une pièce par objet dans l'arbre du modèle, maillages partagés, couleurs,
    vues nommées, propriétés du PDF, U3D COMPRESSÉ. `--simple` : tel que l'ERP le fait (ses `u3dWriter.ts` et
    `exportPdf3d.ts`, copiés INCHANGÉS dans `modeles\pdf_3d\erp\` : un seul maillage gris, U3D non compressé, 7 Mo).
  - Projet à catalogue de pièces : copier `pdf3d\` de Saint-Exemple (garde-fou du gel, libellés tirés du catalogue).
  - Le joindre au 3D livré d'un projet de fabrication (mon interprétation : Sylvain a demandé l'outil « pour les futurs
    projets », il n'a pas dit « toujours »).
  - 🔴 U3D non compressé : dans la norme, mais un lecteur tiers (aspose-cad 26.6) le REFUSE et lit le compressé. Le
    module de l'ERP écrit sans compression : dit à Sylvain, RIEN n'a été modifié dans l'ERP (`<dépôt de l'ERP>`
    lu seulement).
  - 🔴 PDF-XChange Editor 11.1 (le seul lecteur PDF 3D du poste) bloque le contenu 3D par défaut (bandeau jaune) et la
    confiance se donne fichier par fichier ; Sylvain l'active LUI-MÊME (« J'active la 3D moi-même ») : ne jamais
    toucher aux réglages du lecteur. Vu sur capture : la version de fabrication s'affiche dans ses deux codages ; la
    version `--simple` n'a PAS été vue (bandeau) : ne pas la remettre à un client sans l'avoir vue.
- 🔴 **AUCUNE FENÊTRE SUR LE POSTE SANS PRÉVENIR SYLVAIN** (2026-10-09 : « Pourquoi le PDF3d n'arrête pas de
  s'ouvrir ? », après six ouvertures du lecteur en sept minutes par un agent, pendant qu'il travaillait). Ni lecteur
  PDF, ni Blender graphique, ni visionneuse : une vérification qui s'affiche chez lui se fait UNE fois, annoncée ; le
  reste se prouve par la structure des fichiers et par un lecteur tiers. La règle est écrite dans les 5 fiches
  d'agents (`.claude\agents\`) ; pour un agent `general-purpose`, l'écrire dans sa consigne.
  `modeles\pdf_3d\voir_dans_lecteur.ps1` refuse sans `-Prevenu`.
- Chaque projet dans `C:\Dev\<Projet>\`. Dans le dossier du poste, rien d'autre que :
  - ce fichier ;
  - `SAVOIR_LECTURE_PLANS.md`, le savoir vivant de la lecture de plans ;
  - les savoirs détaillés : `SAVOIR_BLENDER.md`, `SAVOIR_DAO_DWG.md`, `SAVOIR_EQUIPE_AGENTS.md` et `SAVOIR_POSTE.md` ;
  - les profils métier `*_profil.txt` qu'il a déposés ;
  - `Rendu3D_ERP\`, la copie du module Rendu 3D de l'ERP, demandée le 2026-09-23 ;
  - `outils\`, les programmes PORTABLES et le module de chemins (dossier autonome demandé le 2026-09-25, voir
    `outils\LISEZMOI.md`) ;
  - `modeles\`, les scripts de référence copiés des projets ;
  - `Demarrer-Blender.bat`, le lanceur.
- **Apprendre de chaque plan** (demande du 2026-09-24) : ce qu'un plan apprend va dans `SAVOIR_LECTURE_PLANS.md`, pas
  seulement dans le projet.
  - Demander aux agents une section « Ce que ce plan m'a appris » dans leur rapport, puis l'arbitrer et l'y verser.
  - Sylvain fournira d'autres plans au fil des sessions : « qu'il s'en inspire, je veux qu'il apprenne de ceux-ci ».
    Protocole au § 8 du fichier vivant : étude de style, galerie des éléments à imiter, comparaison avec notre jeu.
- **De beaux 3D et des plans 2D bien détaillés** (demande du 2026-09-24) : ce sont des STANDARDS, écrits aux § 6 et 7 de
  `SAVOIR_LECTURE_PLANS.md`. Les fiches des agents `modelisation` et `dao` y renvoient.
- **Demander avant d'installer un logiciel** ; ne jamais écraser un fichier ouvert dans une appli (il a choisi « v2 à côté »).
- **Lui demander d'emblée les dimensions qu'il connaît** (emprise, portes) : il les a, et elles priment sur la photo.
  Il veut des dimensions en **pieds ronds**.
- **Sous-sol fini compté à 100 %**, comme habitable (Sylvain, 2026-09-25). Le profil se contredit : « compté comme
  habitable » (ligne 248) contre « ajouter 60 % » (section 1). Garage « tel que plan » : isolé au plan → chauffé.
- 🔴 **AU PLUS 5 AGENTS EN MÊME TEMPS** (Sylvain, 2026-10-10 : « ayant testé avant, avec 5 agents IA c'est correct »), le
  chef non compté, par vagues.
  - Un agent au contexte lourd coûte son contexte ENTIER à chaque appel d'outil : lire le vrai contexte dans sa
    transcription (outil `chef\etat_agents.py` des projets Saint-Exemple ; le chiffre des notifications de fin est plus
    bas que le vrai), remplacer un agent au-dessus de 700 000 jetons, et lancer SOI-MÊME les passages mécaniques
    (répétitions, générations officielles, gels) en une tâche de fond qui écrit un résumé.
  - Compter les agents actifs avant chaque lancement ; les agents de vérification comptent dans
    ces 5. Règle d'avant, pour mémoire (2026-09-28 : « Il faudrait pas plus de 7 ») : avec 9 agents, le poste (4 fils)
    peinait déjà.

## Chaîne de production (workflow demandé par Sylvain le 2026-09-23)

Photo (ou dimensions) → modèle Blender → rendus → **1 photo hyperréaliste** (même moteur que le module Rendu 3D de
l'ERP) → **plans 2D DWG** (+ DWG 3D) → **dépôt dans le module CAD** (`/cad`, PAS la DAO `/cao2`) de l'ERP React.
La session principale orchestre ; profils entre parenthèses. Exemple complet : `C:\Dev\Garage_rouge_Blender\`.

1. **Relevé** (chef d'orchestre). Dimensions connues d'abord (voir Préférences). Photo → zooms Pillow à grille de
   pixels → `analyse_photo.py` (points de fuite) → `resection2.py` (modèles dans `modeles\releve_photo\` ; calage de caméra par moindres
   carrés, numpy + scipy déjà installés, dimensions connues en contraintes) → **`parametres_<projet>.py`** = SOURCE DE
   VÉRITÉ unique, en pieds : gabarit, ouvertures, caméra `photo`, repères en pixels. Lu par Blender ET par les plans :
   changer une dimension = une ligne, puis relancer les scripts. ✅
2. **Modèle + rendus** (`modelisation`) : `build_<projet>.py` importe les paramètres (aucune cote en dur), collections
   nommées comme les calques DAO, caméra `photo` qui reproduit la photo + `rendus/comparaison_photo.png`, aperçus
   EEVEE puis Cycles CUDA ; `verifier_coplanaires.py` avant les rendus finaux. ✅ (garage : 5 vues)
3. **Photo hyperréaliste** : `Rendu3D_ERP\`, à la racine du poste = copie du module Rendu 3D de l'ERP (voir son `LISEZMOI.md`). Outil, lancé par le Python du poste :
   `& $env:BM_PYTHON Rendu3D_ERP\photo_hyperrealiste.py rendu.png --sortie photo.png
   [--type exterior|interior|object|mechanical] [--qualite pro|standard|fast] [--resolution 1K|2K|4K] [--consigne "…"]
   [--essai-a-blanc]`. Il envoie à Google Gemini (REST `generateContent`) la même requête que l'ERP, vérifiée à l'octet
   près ; 13 essais hors ligne dans `test_cao_rendu_domaine.py`.
   - Modèles : `gemini-3-pro-image` (pro, par défaut, 4K), `gemini-3.1-flash-image`, `gemini-2.5-flash-image`.
   - **UNE seule image** en entrée, pas d'image de référence. Aucune option de style : tout passe par `--consigne`
     (2000 caractères au plus).
   - Coût ≈ 0,24 $ US par image en Pro 4K. Rendu Blender à fond OPAQUE (pas de `film_transparent` : le JPEG le noircit).
   - Clé : `GOOGLE_GEMINI_API_KEY`, lue dans l'environnement puis dans `HKCU\Environment`. ✅ Posée le 2026-09-23
     (voir « Clés d'API »).
   - ✅ **Premier appel réel le 2026-09-23** : `gemini-3-pro-image`, 4K, 32 s, 0,24 $ US. En entrée, le rendu
     Cycles 1600×1205 ; en sortie, un JPEG de 4760×3584 (10 Mo). L'extension est corrigée en `.jpg` automatiquement.
   - Gazon, gravier, arbres et lumière deviennent photographiques, et la géométrie est conservée.
   - **Mais sans consigne, le modèle « améliore » les détails** : porte de service devenue blanche, portes de garage à
     2 rangées de grands carreaux au lieu d'une rangée de 4 hublots, fenêtre changée, texte de l'affiche illisible.
     → Toujours passer une `--consigne` qui décrit les éléments à garder tels quels.
   - ✅ **Avec une consigne en anglais** (1 206 caractères : « Preserve the building exactly… Keep these details
     faithful: (1)… (7)… Setting: … »), l'image est **fidèle** : portes, porte de service, affiche, fenêtre et mât sont
     conservés, et le gazon devient réaliste. 37 s, 0,24 $ US. Modèle de consigne :
     `C:\Dev\Garage_rouge_Blender\rendus\consigne_photo_hyperrealiste.txt` (le passer par `--consigne (Get-Content …)`).
4. **Plans DWG** (`dao`) : `plans_<projet>.py`, A-101 plan coté + A-201 élévations dessinées DIRECTEMENT depuis les
   paramètres (pas de Line Art pour un bâtiment simple) ; `exporter_autocad.py` pour le DWG 3D (MESH, un calque par
   collection, sommets soudés, objets hors champ exclus) ; DWG R2018 par ODA ; aperçus PNG. ✅
5. **Vérification** (`verification`) avant toute livraison, puis montrer les images à Sylvain. ✅ Deux passes pour le
   garage : 0 erreur, 78 puis 82 cotes justes, baies à 0" près.
6. **Dépôt dans le module CAD de l'ERP Constructo AI** (facultatif, réservé aux clients de l'ERP).

## Journal des sessions (UNE ligne par session)

Le lanceur affiche la date de la DERNIÈRE ligne qui commence par « - **20 » : garder l'ordre des dates.
- **2026-10-10** — Édition publique du poste : votre journal commence ici.

## Maintenir ce fichier

🔴 **TAILLE** (Sylvain, 2026-10-10 : « il va falloir diminuer » ; le fichier faisait 212 000 caractères pour une limite de
150 000) : il est chargé à chaque session ET par chaque agent. Le tenir **sous 100 000 caractères**
(`(Get-Item CLAUDE.md).Length`) : ici, seulement ce qui vaut pour toutes les sessions ; tout le reste va dans un savoir.

À la fin de chaque session :
- ICI : les outils installés, les préférences exprimées par Sylvain, l'état du projet EN COURS,
  et UNE ligne au journal, qui commence par « - **AAAA-MM-JJ** » (le lanceur lit la dernière).
- Les **pièges vérifiés** et les **durées mesurées** nouveaux : dans le savoir de leur sujet (table « Savoirs
  détaillés ») ; la fiche d'un projet fini : dans `SAVOIR_PROJETS.md` ; l'entrée détaillée : dans `JOURNAL_SESSIONS.md` (deux fichiers à créer : absents de l'édition publique).
- Si un plan a été lu, enrichir aussi `SAVOIR_LECTURE_PLANS.md` (méthode, conventions, pièges, écarts de Règle 5, journal
  des plans lus).
- Quand un outil marqué ○ a servi, le passer à ✅ avec ce qui a été vérifié (et ses pièges). Corriger ou supprimer ce
  qui devient faux. Rester concis : ce fichier est chargé à chaque session ouverte dans le dossier du poste, où qu'il
  soit collé (et, par import, dans `C:\Dev\Maison_quebecoise_Blender` et `C:\Dev\Garage_rouge_Blender`).
- Quand le projet en cours change : mettre à jour `outils\projet_en_cours.txt` (une ligne, `..\<Projet>`). Le lanceur
  l'affiche et le donne à la session (`BM_PROJET`).
