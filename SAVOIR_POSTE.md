# Savoir vivant — le poste : Windows, PowerShell, Git Bash, encodages, dossier autonome

> **Édition publique** (une gracieuseté de Sylvain Leduc, Constructo AI inc.) : noms de clients, adresses et données internes retirés ; les projets de référence portent des noms génériques (« Bungalow », « Agrandissement », « Saint-Exemple »). Certains fichiers cités n'existent que sur le poste d'origine : voir `README.md`, « Ce que le dépôt ne contient pas ».

Sorti de `CLAUDE.md` le 2026-10-10 (le fichier vivant dépassait sa limite de 150 000 caractères) : le texte des
sections est celui d'origine (noms rendus génériques, passages internes retirés).
**À lire AVANT** d'écrire une commande délicate (chemins à espaces ou à `$`, heredoc, encodages, attentes en
arrière-plan), de toucher au lanceur, aux outils portables de `outils\` ou à la copie du dossier vers un autre poste.
**À enrichir** à la fin de chaque session : les pièges vérifiés et les durées mesurées de ce sujet vont ICI, plus dans
`CLAUDE.md`. Corriger ou retirer ce qui devient faux.
Voir aussi : `outils\LISEZMOI.md` (mode d'emploi du dossier autonome), `SAVOIR_EQUIPE_AGENTS.md`.

## Pièges vérifiés — Windows et outils de session

- **PowerShell : mélanger des types d'objets dans une même sortie en masque une partie** (ex. `Get-Item` puis
  `Get-CimInstance` : les processus n'apparaissent pas) → toujours formater en chaînes (`"{0} {1}" -f ...`).
  C'est ce qui a fait croire à tort que Blender était fermé.
- Bash : un heredoc contenant `'''` + guillemets imbriqués a échoué (« unexpected EOF »), même avec `<<'EOF'` (revérifié
  le 2026-09-23) → écrire le script avec Write.
- Console Windows en cp1252 : un `print` Python contenant « ≤ » plante → `PYTHONIOENCODING=utf-8` (`-X utf8`
  avec le Python portable ; `python.exe -I` ignore `PYTHONIOENCODING`).
- Impossible de piloter une fenêtre graphique depuis le shell (SetForegroundWindow/SendKeys refusés, même avec l'astuce Alt).
  La **capture d'écran d'une fenêtre fonctionne** avec `PrintWindow` (user32) + System.Drawing, puis Read de l'image.
- Rendus longs : `run_in_background` + `Monitor` (boucle `until` sur l'apparition du fichier) ; le seuil d'heure d'un
  `find -newermt` doit être antérieur au lancement.
- Les accents peuvent s'afficher mal dans la sortie des outils (cp1252) : sans conséquence sur les fichiers.
- `git fetch` écrit sa progression sur stderr : PowerShell 5.1 l'affiche en rouge (`NativeCommandError`) alors que la
  commande a réussi. Lire la dernière ligne (`a..b main -> origin/main`).
- PowerShell 5.1 : un `git grep` dont le motif contient `"`, `\(` ou `@` échoue à l'analyse → passer par Bash.
  `git archive` du clone Constructo sort en CRLF : normaliser les fins de ligne avant de comparer une copie.
- Python du poste (`outils\python`, copie de celui du système, 375 paquets ;
  voir `requirements.txt`) : aussi httpx 0.28.1, fastapi 0.115.6, pydantic 2.13.4, pytest 8.4.2,
  numpy 2.1.3, scipy 1.14.1, psycopg2 2.9.11, psycopg 3.3.2, PyMuPDF 1.26.4, reportlab 4.2.5, openpyxl 3.1.5,
  shapely 2.1.2, matplotlib 3.10.1.
- PowerShell 5.1 : lancer Blender avec `*> journal.log` puis `Select-String`, pour éviter le NativeCommandError de
  `2>&1`. Pillow 12 : `Image.getdata()` est déprécié → `get_flattened_data()`.
- Photo de téléphone (Pixel) : les verticales sont parallèles dans l'image → caméra de niveau, avec un point principal
  décalé vers le bas (horizon à v ≈ 855-880 sur 1506 px). En Blender : `rotation=(90°, 0, lacet)`, `shift_y = (v_h − H/2) / W`.
- **Encodage** :
  - `Get-Content` sans `-Encoding UTF8` affiche mal l'UTF-8 sans BOM ;
  - un script avec BOM fait échouer `exec(compile(open(f, encoding="utf-8").read()))` : lire en `utf-8-sig` ;
  - écrire sans BOM : `[IO.File]::WriteAllText(p, $c, (New-Object Text.UTF8Encoding $false))`.
- Heredoc Bash : une apostrophe peut le casser, et le `\t` d'un chemin Windows en chaîne Python devient une
  tabulation → Write, ou chaînes brutes.
- Dans un `python -c "..."` entre guillemets DOUBLES, sous Bash, les accents graves `` `...` `` sont EXÉCUTÉS par le shell
  (texte Markdown abîmé en silence, le 2026-09-29) : écrire le script avec Write, ou modifier par Edit.
- Plusieurs bases PostgreSQL jetables sur le poste (agents en parallèle) : vérifier `SELECT
  current_setting('data_directory')` avant de lancer des bancs. Un `pg_ctl start` qui échoue laisse `psql` se connecter
  à la base d'un AUTRE agent.
- `sleep` au premier plan est refusé, mais `until [ ! -f f ]; do sleep 5; done` passe (bascule en arrière-plan après
  600 s). `Measure-Object -Line` ignore les lignes vides.
- Un Python dont la sortie est redirigée vers un fichier la garde en TAMPON : le journal reste vide jusqu'à la fin (PDF
  du projet Agrandissement, 10 min sans une ligne). Lancer avec `-u` pour le suivre ; attendre la fin par
  `until grep -q "^code " journal; do sleep 10; done`.
- Le bloc-notes (scratchpad) de la session est PARTAGÉ par tous les agents : un sous-dossier par agent.

## Pièges vérifiés — dossier autonome (2026-09-25)

Le détail est dans `outils\LISEZMOI.md`.
- ✅ **Réduire le PATH ne simule pas un poste vierge** : System32, où vit le redistribuable Visual C++, reste dans l'ordre
  de recherche. Seul le relevé des DLL réellement CHARGÉES (`outils\diagnostic\trace_dll.py`, EnumProcessModulesEx)
  prouve leur provenance.
  - Il manquait `msvcp140.dll` à PyMuPDF, `vcruntime140_1.dll` à ODA, et le runtime du `python.exe` embarqué de Blender.
- ✅ **Une DLL fait partie de Windows selon son ÉDITEUR** (Microsoft Corporation), pas selon son nom de produit :
  `ze_loader.dll` d'Intel se dit « for Windows(R) ». Les modules d'ODA sont des DLL en `.tx*`.
- ✅ Copie de Python :
  - elle voit encore le site utilisateur du poste : lancer avec `-s` ;
  - les `Scripts\*.exe` gardent l'ancien interpréteur ;
  - l'antivirus inspecte chaque fichier neuf à sa première ouverture (parcours de 1 222 s la 1re fois).
- ✅ Blender portable :
  - c'est le dossier `outils\blender\portable\` qui déclenche le mode ;
  - `C:\ProgramData\Blender Foundation\…` passerait avant lui : parade `BLENDER_SYSTEM_RESOURCES` ;
  - énumérer CUDA crée `%APPDATA%\NVIDIA\ComputeCache` : parade `CUDA_CACHE_PATH` ;
  - le 1er lancement d'une copie neuve prend 23,5 s (.pyc).
- ✅ ezdxf `odafc` essaie `shutil.which("ODAFileConverter")` AVANT `win_exec_path` : mettre la copie portable en tête du
  PATH.
- ✅ Edge sans tête : `--virtual-time-budget`, un profil temporaire UNIQUE par impression (code 21 = profil déjà pris),
  attendre `%%EOF` puis `taskkill /T /F`. Cela fait 2,7 s par PDF, au lieu de 3 à 110 s.
- ✅ npm : `npm_config_update_notifier=false` (sinon la 1re commande bloque 45 s) ; `npm.cmd` préfère un npm de
  `%APPDATA%\npm`.
- ✅ Batch :
  - l'outil Write écrit en LF, et un .cmd en LF fait échouer `call :etiquette` : toujours du CRLF ;
  - Claude Code pose `NoDefaultCurrentDirectoryInExePath=1` : donner le chemin complet d'un .cmd ;
  - une parenthèse dans un chemin casse `for /f ... in (...)`.
- ✅ PowerShell 5.1 lit un .ps1 sans BOM en ANSI : ASCII, ou UTF-8 AVEC BOM.
- ✅ Claude Code 2.1 (npm) est un exe natif de 242 Mo, sans Node : il se copie tel quel. La connexion au compte reste par
  utilisateur Windows.
- ✅ Tester un dossier déplacé par liens physiques (`os.link`), jamais par jonction : un `Remove-Item -Recurse` sur une
  jonction peut vider la cible.
- ✅ **Chercher des données internes ou des noms de personnes TOUJOURS sans tenir compte de la casse**. Les cartouches et
  les notes des DWG sont en MAJUSCULES : les noms des clients y avaient échappé à une 1re recherche. `\bPrenom\b` ne
  trouve pas `rejouer_prenom`, parce que le souligné compte comme une lettre.
- ✅ Garde-fou « aucun fournisseur réel » tiré du fichier des prix réels : l'entreprise elle-même y figure comme
  fournisseur. L'exclure, sinon chaque page déclenche une alerte.
- ✅ Un script de relevé lit sa photo dans `reference\` du projet, jamais dans le bloc-notes d'une session (l'ancien
  `analyse_photo.py` lisait `%TEMP%\claude\<session>\images\1.jpg`).
- ✅ De `resection2.py` à la caméra Blender : position = (Xc, Yc, Zc) × 0,3048 ; rotation = (90°, 0, alpha − 90°) ;
  focale en mm = f × 36 / largeur ; shift_y = (v0 − H/2) / W.
- ✅ Blender en arrière-plan sans rendu, avec `CUDA_VISIBLE_DEVICES=-1`, prend 2 s et ne touche pas au GPU : on peut le
  lancer pendant qu'un autre agent rend.
- ✅ PowerShell 5.1 : `*> fichier.log` écrit en UTF-16, et la sortie UTF-8 d'un sous-processus y devient illisible.
  Passer par `Out-File -Encoding utf8`.
- ✅ **Soir du 2026-09-25**, en ajoutant PostgreSQL, Git et gh, puis en testant depuis une copie au chemin ACCENTUÉ :
  - Dans un environnement épuré, Python écrit dans un tube en cp1252. Tout chemin accentué oblige à lancer avec
    `-X utf8`, ou `chcp 65001` côté cmd. C'était la cause de 4 des 6 échecs du 1er passage, tous venus des essais
    eux-mêmes.
  - `os.path.exists("fichier:Zone.Identifier")` donne des faux positifs sur ce Windows (99 308 fichiers sur 158 270).
    `GetFileAttributesW` donne la bonne réponse.
  - Dans un `.bat`, `%X:~0,10%` sur une variable non définie casse la ligne (« goto était inattendu »).
  - Edge refuse un profil au-delà de 260 caractères : un bac à sable trop profond le fait échouer.
  - Le `bash.exe` de System32 est celui de WSL : ne jamais le prendre pour Git Bash.
  - La connexion de `gh` ne voyage pas : `hosts.yml` est dans `%APPDATA%` et le jeton dans le gestionnaire
    d'identifiants. Le lanceur ne demande que le NOM du compte, hors ligne (`gh config get user -h github.com`).
  - Un passage réussi lancé DEPUIS une copie d'essai disparaît avec elle. Le dernier fichier de résultats du dossier
    (20 h 13) montrait encore 2 échecs, déjà corrigés : rejouer le point en cause avant de conclure.

