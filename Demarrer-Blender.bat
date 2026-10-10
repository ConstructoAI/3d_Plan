@echo off
setlocal
title Poste Blender - session Claude
cd /d "%~dp0"

rem =============================================================================
rem  POSTE BLENDER / DAO - LE fichier a double-cliquer
rem =============================================================================
rem
rem  Verifie le fichier vivant et les profils, fait l'inventaire des outils du
rem  poste, puis propose un MENU (2026-09-25, soir ; esprit du START.bat
rem  d'OpenClaude) - le choix 1 part tout seul apres 10 s :
rem    1) session du chef d'orchestre (Opus 5.5, effort max) ;
rem    2) reprendre la derniere session (claude --continue) ;
rem    3) programme Metre (demarrer, puis ouvrir le navigateur) ;
rem    4) verifier le poste ; 5) copier vers un autre poste ; 6) quitter ;
rem    7) (transition) reprendre une session d'AVANT le changement de
rem       configuration, tant que le profil de l'utilisateur en garde.
rem  Claude Code est mis a jour UNE fois par jour (outils\claude\
rem  derniere_verification.txt).
rem
rem  ZERO TRACE : la configuration de Claude (reglages, competences, plugins,
rem  memoire, sessions, et la connexion apres la 1re fois) est dans
rem  outils\claude\config : chemins.cmd pose CLAUDE_CONFIG_DIR. Retour au
rem  profil de l'utilisateur : set BM_CLAUDE_CONFIG=profil avant de lancer.
rem
rem  POURQUOI CE DOSSIER : Claude Code charge tout seul le CLAUDE.md du dossier
rem  ou il demarre, et les profils de .claude\agents\. Lance ailleurs, la session
rem  repartirait de zero et re-explorerait tous les outils.
rem
rem  DOSSIER AUTONOME, 2026-09-25 : aucun chemin n'est ecrit en dur ici. La racine
rem  est le dossier de ce fichier. outils\chemins.cmd trouve chaque outil : d'abord
rem  sa copie PORTABLE sous outils\, sinon l'installation du poste - ce repli est
rem  signale a l'ecran. Il pose les variables BM_* dont la session Claude herite.
rem  Le dossier entier se colle d'un poste a l'autre : voir outils\LISEZMOI.md.
rem
rem  Diagnostic seul, sans lancer Claude :   Demarrer-Blender.bat /verifier
rem  Idem, plus les essais de Blender portable, environ 1 min :
rem                                          Demarrer-Blender.bat /verifier complet
rem  Programme Metre seul (base, serveur, interface, puis le navigateur), sans
rem  lancer Claude :                         Demarrer-Blender.bat /metre
rem  Le lanceur VERIFIE le programme Metre a chaque demarrage, mais ne le
rem  demarre jamais d'office.
rem  Un choix du menu directement, puis sortie (raccourcis, essais) :
rem                                          Demarrer-Blender.bat /choix 3
rem  Essais a blanc : set BM_LANCEUR_A_BLANC=1 (Metre et copie seulement
rem  annonces, date de mise a jour non ecrite).
rem
rem  Messages sans accents : cmd.exe demarre en page de codes 850 ou 437, et un
rem  message accentue s'y affiche en charabia. Meme regle pour la consigne
rem  passee a Claude a l'etape 4.
rem =============================================================================

set "RACINE=%~dp0"
set "WHERE_EXE=%SystemRoot%\System32\where.exe"
set "FINDSTR_EXE=%SystemRoot%\System32\findstr.exe"
set "REG_EXE=%SystemRoot%\System32\reg.exe"
set "ROBOCOPY_EXE=%SystemRoot%\System32\robocopy.exe"
set "CURL_EXE=%SystemRoot%\System32\curl.exe"
set "CHOICE_EXE=%SystemRoot%\System32\choice.exe"
set "PS_EXE=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
set "MODE_VERIFIER="
set "MODE_METRE="
set "CHOIX_IMPOSE="
set "MENU_AUTO="
if /i "%~1"=="/verifier" set "MODE_VERIFIER=1"
if /i "%~1"=="/metre" set "MODE_METRE=1"
if /i "%~1"=="/choix" set "CHOIX_IMPOSE=%~2"

echo.
echo   ============================================================
echo      POSTE BLENDER - DAO   -   dossier autonome
echo.
echo      Blender 5.2, rendus, AutoCAD (DWG par ODA), plans cotes.
echo      Claude charge le fichier vivant CLAUDE.md et 5 profils.
echo.
echo      Une gracieusete de Sylvain Leduc - Constructo AI inc.
echo      www.constructoai.ca
echo.
echo      EXIGE : un compte Claude Max 20x - session en Opus 5.5,
echo      effort max. Photo hyperrealiste : un compte Google et sa
echo      cle d'API Gemini.
echo   ============================================================
echo.

rem  Les chemins des outils, pour ce lanceur ET pour la session Claude qui les
rem  herite : BM_RACINE, BM_PYTHON, BM_BLENDER, BM_ODA_CONVERTISSEUR,
rem  BM_ODA_VISIONNEUSE, BM_NODE, BM_NAVIGATEUR, BM_PROJET, et BM_ORIGINE_* :
rem  portable, systeme, variable ou absent. Le PATH commence par Python, Node et
rem  ODA, jamais par outils\python\Scripts : ses lanceurs visent l'ancien Python,
rem  on passe par python -m pip. Pour les copies portables, il pose aussi les
rem  consignes des copies portables. /versions ajoute les numeros de
rem  version, pour l'affichage.
if exist "%RACINE%outils\chemins.cmd" call "%RACINE%outils\chemins.cmd" /versions
if not exist "%RACINE%outils\chemins.cmd" echo   [attention] outils\chemins.cmd est absent : aucun outil ne sera trouve.

rem ---------------------------------------------------------------------------
rem  [1/4] Le fichier vivant et les profils
rem ---------------------------------------------------------------------------
rem  Sans CLAUDE.md on n'arrete pas tout de suite pour rien : on arrete parce
rem  qu'une session sans lui refait toute l'exploration du 2026-09-23 (MCP
rem  Blender absent, AutoCAD absent, ODA, pieges Cycles...). C'est le seul
rem  manque bloquant de ce lanceur, avec Claude Code lui-meme.
echo   [1/4] Fichier vivant et profils...
echo.

if not exist "CLAUDE.md" (
  echo   ERREUR : CLAUDE.md est absent de ce dossier.
  echo   C'est le fichier vivant : sans lui, la session repart de zero.
  goto echec
)
echo     [ok]     CLAUDE.md - fichier vivant

rem  La derniere ligne du journal dit ou on en etait.
for /f "tokens=*" %%L in ('%FINDSTR_EXE% /B /L /C:"- **20" CLAUDE.md') do set "DERNIERE_SESSION=%%L"
if defined DERNIERE_SESSION echo              derniere session : %DERNIERE_SESSION:~4,10%

set /a NB_PROFILS=0
for %%P in (modelisation dao verification estimation bim-freecad) do (
  if exist ".claude\agents\%%P.md" (
    echo     [ok]     profil %%P
    set /a NB_PROFILS+=1
  ) else (
    echo     [MANQUE] profil %%P - fichier .claude\agents\%%P.md
  )
)
if %NB_PROFILS% LSS 5 (
  echo.
  echo   Attention : il manque des profils. Claude demarre quand meme,
  echo   mais il ne pourra pas deleguer a ceux qui manquent.
)

rem  Le profil IA que Claude INCARNE (demande de Sylvain, 2026-09-23).
if exist "ENTREPRENEUR_GENERAL_QC_profil.txt" (
  echo     [ok]     profil IA a incarner : entrepreneur general QC
) else (
  echo     [MANQUE] profil IA ENTREPRENEUR_GENERAL_QC_profil.txt - Claude ne pourra pas l'incarner
)

rem  Projet en cours : outils\projet_en_cours.txt, tenu a jour par le chef
rem  d'orchestre ; a defaut, le dossier voisin dont un parametres_*.py est le
rem  plus recent. Calcule par chemins.cmd, dans BM_PROJET.
call :afficher_projet

rem ---------------------------------------------------------------------------
rem  [2/4] Inventaire des outils : copie PORTABLE d'abord
rem ---------------------------------------------------------------------------
rem  Un outil absent n'empeche pas de demarrer : Claude saura quoi faire, et
rem  le dire a l'ecran vaut mieux qu'une session qui le decouvre en cours de
rem  travail. [repli] = l'outil vient de l'installation du poste, pas du dossier.
echo.
echo   [2/4] Outils du poste - copie portable sous outils\ d'abord...
echo.

rem  blender.exe n'accepte pas les chemins longs : son plus long fichier fait 113
rem  caracteres sous outils\blender. La racine doit rester sous environ 120.
if not "%RACINE:~120,1%"=="" echo     [attention] le chemin de ce dossier depasse 120 caracteres : Blender refuse les chemins longs.
if not "%RACINE:~120,1%"=="" echo                 Rapprochez le dossier de la racine du disque, par exemple D:\Poste-Blender.

set "MANQUE_OUTIL="
set "REPLI_OUTIL="
call :ligne_outil PYTHON "Python" 1 "python" ""
call :ligne_ezdxf
call :ligne_outil BLENDER "Blender" 1 "blender" ""
call :ligne_outil ODA_CONVERTISSEUR "ODA File Converter" 1 "oda\convertisseur" " ; DXF vers DWG"
call :ligne_outil ODA_VISIONNEUSE "ODA Viewer" 0 "oda\visionneuse" " ; pour regarder les DWG"
call :ligne_outil NODE "Node.js" 0 "node" ""
call :ligne_outil POSTGRES "PostgreSQL" 0 "postgresql" " ; base du programme Metre"
call :ligne_outil GIT_BASH "Git" 0 "git" " ; git et outil Bash de Claude"
if not defined BM_GIT_BASH echo              sans Git Bash, l'outil Bash de Claude manquera ; PowerShell reste
call :ligne_outil GH "GitHub CLI" 0 "gh" " ; gh"
call :ligne_gh_connexion
call :ligne_navigateur
call :ligne_freecad
call :ligne_metre
call :ligne_config_claude

call :trouver_claude
if not defined CLAUDE_CMD goto sans_claude
set "CLAUDE_VERSION="
for /f "tokens=1" %%V in ('call "%%CLAUDE_CMD%%" --version 2^>nul') do if not defined CLAUDE_VERSION set "CLAUDE_VERSION=%%V"
if "%CLAUDE_ORIGINE%"=="poste" echo     [ok]     Claude Code %CLAUDE_VERSION% - installation du poste
if "%CLAUDE_ORIGINE%"=="portable" echo     [ok]     Claude Code %CLAUDE_VERSION% - copie portable outils\claude : pas installe sur ce poste

echo.
echo     Cles d'API - variables de l'utilisateur, jamais dans un fichier :
set "CLE_MANQUE="
call :cle GOOGLE_GEMINI_API_KEY "photo hyperrealiste, Gemini"
if defined CLE_MANQUE call :aide_cles

if defined REPLI_OUTIL (
  echo.
  echo   [repli] = pas de copie portable : l'outil vient de l'installation du poste.
  echo   Pour lui, le dossier n'est pas encore autonome - voir outils\LISEZMOI.md.
)
if defined MANQUE_OUTIL (
  echo.
  echo   Des outils manquent. Claude demarre quand meme : demandez-lui de
  echo   regarder, la marche a suivre est dans CLAUDE.md et outils\LISEZMOI.md.
)

if defined MODE_METRE goto demarrer_metre
if not defined MODE_VERIFIER goto avant_menu
call :verifier_detail %2
echo.
echo   Diagnostic termine. Claude n'a pas ete lance.
endlocal
exit /b 0

rem ---------------------------------------------------------------------------
rem  Avant tout lancement de Claude : la configuration du dossier SUIT le dossier
rem  (memoire et reglages du projet ranges sous son chemin absolu), et on
rem  regarde s'il reste des sessions d'AVANT le changement dans le profil.
rem ---------------------------------------------------------------------------
:avant_menu
call :suivre_config

rem ---------------------------------------------------------------------------
rem  LE MENU (esprit du START.bat d'OpenClaude) : choix 1 par defaut apres 10 s.
rem  Apres 3, 4 ou 5, on revient au menu, sans delai cette fois.
rem  /choix N (essais, raccourcis) : ce choix-la directement, puis on sort.
rem ---------------------------------------------------------------------------
set "MENU_DELAI=/t 10 /d 1"
:menu
set "CHOIX="
if defined CHOIX_IMPOSE set "CHOIX=%CHOIX_IMPOSE%"
if defined CHOIX_IMPOSE set "MENU_AUTO=1"
set "CHOIX_IMPOSE="
if defined CHOIX goto menu_choix
echo.
echo   ============================================================
echo      QUE VOULEZ-VOUS FAIRE ?
echo.
echo      1) Session du chef d'orchestre - Opus 5.5, effort max
echo      2) Reprendre la derniere session - claude --continue
echo      3) Programme Metre - demarrer, puis ouvrir le navigateur
echo      4) Verifier le poste
echo      5) Copier vers un autre poste
echo      6) Quitter
if defined ANCIEN_PROFIL echo      7) Reprendre une session d'AVANT le changement de configuration
echo   ============================================================
set "TOUCHES=123456"
if defined ANCIEN_PROFIL set "TOUCHES=1234567"
if defined MENU_DELAI echo   Sans reponse, le choix 1 part dans 10 secondes.
<nul set /p "=  Votre choix : "
"%CHOICE_EXE%" /c %TOUCHES% /n %MENU_DELAI%
set "CHOIX=%errorlevel%"
echo.
:menu_choix
set "MENU_DELAI="
if "%CHOIX%"=="1" goto choix_session
if "%CHOIX%"=="2" goto choix_reprendre
if "%CHOIX%"=="3" goto choix_metre
if "%CHOIX%"=="4" goto choix_verifier
if "%CHOIX%"=="5" goto choix_copier
if "%CHOIX%"=="6" goto choix_quitter
if "%CHOIX%"=="7" goto choix_ancien
rem  choice.exe rend 0 ou 255 quand il ne peut pas lire le clavier : on sort
rem  plutot que de tourner en rond.
echo   Choix impossible a lire (%CHOIX%) : fin.
goto fin

:choix_session
call :explication_connexion
call :maj_quotidienne
goto demarrage

:choix_reprendre
call :explication_connexion
call :maj_quotidienne
echo.
echo   [4/4] Reprise de la derniere session de ce dossier...
echo.
if not defined CLAUDE_CODE_USE_POWERSHELL_TOOL set "CLAUDE_CODE_USE_POWERSHELL_TOOL=1"
call "%CLAUDE_CMD%" --continue --dangerously-skip-permissions --model "claude-opus-5-5[1m]" --effort max
goto fin

rem  Transition : les sessions d'avant le changement vivent dans le profil de
rem  l'utilisateur. On y retourne le temps d'une reprise, sans CLAUDE_CONFIG_DIR.
:choix_ancien
echo.
echo   Reprise d'une session d'AVANT le changement : profil de l'utilisateur,
echo   sans la configuration du dossier.
echo.
set "CLAUDE_CONFIG_DIR="
if not defined CLAUDE_CODE_USE_POWERSHELL_TOOL set "CLAUDE_CODE_USE_POWERSHELL_TOOL=1"
call "%CLAUDE_CMD%" --continue --dangerously-skip-permissions --model "claude-opus-5-5[1m]" --effort max
goto fin

:choix_metre
call :lancer_metre
if defined MENU_AUTO goto fin
goto menu

:choix_verifier
call :verifier_detail
if defined MENU_AUTO goto fin
goto menu

:choix_copier
call :copier_poste
if defined MENU_AUTO goto fin
goto menu

:choix_quitter
echo   Au revoir.
goto fin

:fin
endlocal
exit /b 0

rem ---------------------------------------------------------------------------
rem  [4/4] UNE session, les cinq profils. C'est vous qui decidez en cours de
rem        route, sans relancer quoi que ce soit.
rem ---------------------------------------------------------------------------
rem  Meme reglage que Pilotage.bat : les profils portent model:inherit et
rem  effort:max, et la consigne interdit de les surcharger - un override
rem  ferait perdre aux agents le contexte 1M de la session.
rem  CLAUDE_CODE_USE_POWERSHELL_TOOL : l'outil PowerShell, principal dans
rem  CLAUDE.md. Il est active dans les reglages de l'utilisateur de ce poste,
rem  qui ne suivent pas le dossier : on le pose ici pour un poste neuf.
:demarrage
echo.
echo   [4/4] Demarrage : Opus 5.5 contexte 1M, effort MAX, autonomie complete.
echo.
if not defined CLAUDE_CODE_USE_POWERSHELL_TOOL set "CLAUDE_CODE_USE_POWERSHELL_TOOL=1"
for %%V in (PYTHON BLENDER ODA_CONVERTISSEUR ODA_VISIONNEUSE NODE NAVIGATEUR EZDXF POSTGRES GIT_BASH GH) do set "_BM_V_%%V="
set "PROJET_TXT=aucun projet en cours trouve"
if defined BM_PROJET set "PROJET_TXT=%BM_PROJET%"

call "%CLAUDE_CMD%" --dangerously-skip-permissions --model "claude-opus-5-5[1m]" --effort max "Session du poste Blender / DAO. Le fichier vivant CLAUDE.md de ce dossier est deja charge : c'est ta base de connaissances verifiee - outils, chemins, pieges deja payes, preferences, etat du projet. Ne re-explore pas ce qui y est ecrit. INCARNE le profil IA ENTREPRENEUR_GENERAL_QC_profil.txt de ce dossier : lis-le AU COMPLET avant ta premiere reponse (outil Read, 3529 lignes, par tranches de 738) - tu es un entrepreneur general chevronne du Quebec : conventions de dessin OAQ/OTPQ, regle 5 de coherence entre les pages avant toute livraison, estimation cost-plus en gamme Economique par defaut. Tu es aussi le CHEF D'ORCHESTRE : CINQ PROFILS sont definis dans .claude/agents/ et tu les lances avec l'outil Agent. IMPORTANT : ne passe JAMAIS de parametre model ni effort a l'outil Agent - leurs fiches portent deja model:inherit et effort:max. 'modelisation' pour Blender, modeles et rendus ; 'dao' pour AutoCAD, DWG 3D, elevations et plans cotes ; 'verification' pour le controle qualite en lecture seule, a faire passer AVANT toute livraison ; 'estimation' pour les quantites et les couts avec Constructo AI, jamais d'ecriture dans l'ERP sans mon accord ; 'bim-freecad' pour FreeCAD. Chaque profil verifie ses outils a son premier usage. Une petite demande, fais-la toi-meme ; delegue ce qui est long ou se parallelise. CE QUI RESTE A TOI : arbitrer les rapports des agents sans les prendre pour argent comptant, me montrer les images et les apercus, obtenir mon accord avant toute installation et avant d'ecraser un de mes fichiers, et METTRE A JOUR CLAUDE.md a la fin de la session - pieges nouveaux, durees mesurees, outils passes de o a ok, une ligne au journal. OUTILS : le dossier est autonome ; les chemins des programmes sont dans les variables d'environnement BM_PYTHON, BM_BLENDER, BM_ODA_CONVERTISSEUR, BM_ODA_VISIONNEUSE, BM_NODE et BM_NAVIGATEUR, copie portable sous outils\ d'abord (module outils\chemins.py, mode d'emploi outils\LISEZMOI.md) : sers-t'en plutot que des chemins ecrits en dur. Projet en cours : %PROJET_TXT%. NE LANCE RIEN TOUT DE SUITE : dis-moi bonjour en deux lignes en entrepreneur general, confirme que tu as lu le profil IA, rappelle-moi tes cinq profils et l'etat du projet en trois lignes, puis attends ma demande."

endlocal
exit /b 0

rem ---------------------------------------------------------------------------
rem  /metre : le programme Metre seul (Metre\demarrer.bat), sans session Claude
rem ---------------------------------------------------------------------------
:demarrer_metre
echo.
echo   Programme Metre : base, serveur et interface, puis le navigateur.
echo.
if not exist "%RACINE%Metre\demarrer.bat" goto metre_absent
call "%RACINE%Metre\demarrer.bat"
set "_RC=%errorlevel%"
endlocal & exit /b %_RC%

:metre_absent
echo   ERREUR : Metre\demarrer.bat est absent de ce dossier.
goto echec

:sans_claude
echo.
echo   ERREUR : Claude Code est introuvable - ni installe sur ce poste, ni en
echo   copie portable dans outils\claude\. Voir outils\LISEZMOI.md.
goto echec

:echec
echo.
echo   ============================================================
echo      DEMARRAGE INTERROMPU
echo      Le message ci-dessus dit ou ca a bloque.
echo   ============================================================
echo.
pause
endlocal
exit /b 1

rem =============================================================================
rem  Sous-routines. Style a plat, sans bloc entre parentheses autour d'un chemin :
rem  un chemin qui contient une parenthese, comme Program Files (x86), casserait
rem  un bloc. Les chemins affiches passent par l'expansion retardee.
rem =============================================================================

rem  Verification detaillee (/verifier et choix 4) : outils\chemins.py lance
rem  chaque outil ; "complet" ajoute les essais de Blender portable.
:verifier_detail
echo.
echo   Verification detaillee - outils\chemins.py, qui lance aussi chaque outil :
echo.
if defined BM_PYTHON "%BM_PYTHON%" "%RACINE%outils\chemins.py" --complet --ascii
if not defined BM_PYTHON echo     impossible : aucun Python trouve.
if /i not "%~1"=="complet" goto :eof
echo.
echo   Essais de Blender portable - agent B, environ 80 s, sans GPU :
if /i not "%BM_ORIGINE_BLENDER%"=="portable" echo     impossible : le Blender trouve n'est pas la copie portable.
if /i not "%BM_ORIGINE_BLENDER%"=="portable" goto :eof
if not exist "%RACINE%outils\blender\_verification\verifier.py" echo     impossible : outils\blender\_verification\verifier.py est absent.
if not exist "%RACINE%outils\blender\_verification\verifier.py" goto :eof
"%BLENDER_SYSTEM_RESOURCES%\python\bin\python.exe" -I "%RACINE%outils\blender\_verification\verifier.py"
if errorlevel 1 echo     [MANQUE] un essai de Blender a echoue - voir ci-dessus.
if not errorlevel 1 echo     [ok]     tous les essais de Blender passent.
goto :eof

rem  La configuration de Claude dans le dossier (CLAUDE_CONFIG_DIR, posee par
rem  chemins.cmd quand outils\claude\config existe) suit le dossier s'il a ete
rem  colle ailleurs ; ANCIEN_PROFIL = il reste des sessions de ce dossier dans le
rem  profil de l'utilisateur (choix 7 du menu).
:suivre_config
set "ANCIEN_PROFIL="
if not defined CLAUDE_CONFIG_DIR goto :eof
if not defined BM_PYTHON goto :eof
if not exist "%RACINE%outils\claude_config.py" goto :eof
for /f "usebackq tokens=1,* delims= " %%A in (`call "%%BM_PYTHON%%" -s -B "%%RACINE%%outils\claude_config.py" suivre --lanceur`) do (
  if "%%A"=="ANCIEN_PROFIL" set "ANCIEN_PROFIL=1"
  if "%%A"=="SUIVRE_DEPLACE" echo     [info]   dossier deplace : %%B
)
goto :eof

rem  Premier lancement avec la configuration du dossier : pas encore de connexion.
:explication_connexion
if not defined CLAUDE_CONFIG_DIR goto :eof
if exist "%CLAUDE_CONFIG_DIR%\.credentials.json" goto :eof
echo.
echo   ------------------------------------------------------------
echo   PREMIER LANCEMENT AVEC LA CONFIGURATION DU DOSSIER
echo   Claude va demander de se connecter : suivre ses indications
echo   ^(le navigateur s'ouvre^), avec le compte habituel. UNE SEULE
echo   FOIS : la connexion est ensuite rangee dans outils\claude\config.
echo   Reglages, competences, plugins et serveurs MCP y sont deja.
echo   Retour au profil de l'utilisateur : set BM_CLAUDE_CONFIG=profil
echo   avant de lancer ; voir outils\LISEZMOI.md, section Claude Code.
echo   ------------------------------------------------------------
goto :eof

rem  [3/4] Mise a jour de Claude Code : UNE fois par jour, l'heure de la derniere
rem  verification dans outils\claude\derniere_verification.txt. La copie
rem  portable ne se met pas a jour en ligne (DISABLE_AUTOUPDATER).
:maj_quotidienne
echo.
echo   [3/4] Mise a jour de Claude Code - une fois par jour...
if "%CLAUDE_ORIGINE%"=="portable" goto maj_portable
set "MAJ_FICHIER=%RACINE%outils\claude\derniere_verification.txt"
set "AUJOURDHUI="
for /f "usebackq delims=" %%D in (`call "%%PS_EXE%%" -NoProfile -Command "Get-Date -Format yyyy-MM-dd"`) do set "AUJOURDHUI=%%D"
rem  Valeur par defaut OBLIGATOIRE : %X:~0,10% d'une variable non definie casse
rem  la ligne (? goto etait inattendu ?, mesure au premier lancement).
set "DERNIERE=jamais"
if exist "%MAJ_FICHIER%" set /p "DERNIERE=" < "%MAJ_FICHIER%"
if not defined DERNIERE set "DERNIERE=jamais"
if defined AUJOURDHUI if "%DERNIERE:~0,10%"=="%AUJOURDHUI%" goto maj_deja_faite
echo.
call "%CLAUDE_CMD%" update
if errorlevel 1 echo   La mise a jour n'a pas abouti - une autre session ouverte ? On garde la version en place.
call :rafraichir_copie_portable
if defined BM_LANCEUR_A_BLANC echo   A BLANC : date de la verification non ecrite.
if defined BM_LANCEUR_A_BLANC goto :eof
if not exist "%RACINE%outils\claude\" goto :eof
for /f "usebackq delims=" %%D in (`call "%%PS_EXE%%" -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd HH:mm'"`) do > "%MAJ_FICHIER%" echo %%D
goto :eof
:maj_deja_faite
echo   Deja verifiee aujourd'hui, a %DERNIERE:~11,5% : pas de nouvelle verification.
goto :eof
:maj_portable
set "DISABLE_AUTOUPDATER=1"
echo   Copie portable de Claude Code : pas de mise a jour ici.
echo   Pour la mettre a jour : outils\LISEZMOI.md, section Claude Code.
goto :eof

rem  Choix 3 : le programme Metre (Metre\demarrer.bat ouvre ses deux fenetres,
rem  attend l'interface, puis le navigateur).
:lancer_metre
if not exist "%RACINE%Metre\demarrer.bat" echo   Metre\demarrer.bat est absent de ce dossier.
if not exist "%RACINE%Metre\demarrer.bat" goto :eof
if defined BM_LANCEUR_A_BLANC echo   A BLANC : call "%RACINE%Metre\demarrer.bat"
if defined BM_LANCEUR_A_BLANC goto :eof
call "%RACINE%Metre\demarrer.bat"
cd /d "%RACINE%"
goto :eof

rem  Choix 5 : copier le dossier vers un autre poste (outils\copier_vers_poste.ps1).
rem  D'abord la liste de ce qui serait copie (-Essai), puis confirmation.
:copier_poste
echo.
echo   COPIER LE DOSSIER DU POSTE VERS UN AUTRE EMPLACEMENT
echo   Cle USB, disque externe, autre dossier... La base du Metre est
echo   arretee pendant la copie, puis relancee. Chemin court conseille.
set "DEST_COPIE="
set /p "DEST_COPIE=  Dossier de destination, vide pour annuler : "
if not defined DEST_COPIE echo   Annule.
if not defined DEST_COPIE goto :eof
if "%DEST_COPIE:~-1%"=="\" set "DEST_COPIE=%DEST_COPIE:~0,-1%"
set "COPIER_PS1=%RACINE%outils\copier_vers_poste.ps1"
"%PS_EXE%" -NoProfile -ExecutionPolicy Bypass -File "%COPIER_PS1%" "%DEST_COPIE%" -Essai
if errorlevel 1 goto :eof
set "OK_COPIE="
set /p "OK_COPIE=  Copier maintenant ? O pour oui : "
if /i not "%OK_COPIE%"=="O" echo   Pas de copie.
if /i not "%OK_COPIE%"=="O" goto :eof
if defined BM_LANCEUR_A_BLANC echo   A BLANC : copie vers %DEST_COPIE% sautee.
if defined BM_LANCEUR_A_BLANC goto :eof
"%PS_EXE%" -NoProfile -ExecutionPolicy Bypass -File "%COPIER_PS1%" "%DEST_COPIE%"
goto :eof

rem  La configuration de Claude : dans le dossier (zero trace) ou le profil.
:ligne_config_claude
if not defined CLAUDE_CONFIG_DIR echo     [info]   configuration de Claude : profil de l'utilisateur, pas le dossier
if not defined CLAUDE_CONFIG_DIR goto :eof
set "_CC=pas encore connecte : Claude demandera de se connecter une fois"
if exist "%CLAUDE_CONFIG_DIR%\.credentials.json" set "_CC=connexion rangee dans le dossier"
echo     [ok]     configuration de Claude dans outils\claude\config - %_CC%
set "_CC="
goto :eof

:afficher_projet
if /i "%BM_ORIGINE_PROJET%"=="fichier" echo     [ok]     projet en cours : %BM_PROJET%
if /i "%BM_ORIGINE_PROJET%"=="recent" echo     [ok]     projet en cours : %BM_PROJET% - le plus recent, outils\projet_en_cours.txt absent
if /i "%BM_ORIGINE_PROJET%"=="recent-fichier-invalide" echo     [info]   outils\projet_en_cours.txt vise un dossier absent ; projet le plus recent : %BM_PROJET%
if /i "%BM_ORIGINE_PROJET%"=="absent" echo     [info]   aucun projet en cours trouve - rien de bloquant
if not defined BM_ORIGINE_PROJET echo     [info]   projet en cours inconnu - outils\chemins.cmd n'a pas tourne
goto :eof

rem  :ligne_outil CLE "Libelle" essentiel(1/0) "dossier sous outils" " ; role"
:ligne_outil
setlocal EnableDelayedExpansion
set "_C=!BM_%~1!"
set "_O=!BM_ORIGINE_%~1!"
set "_V=!_BM_V_%~1!"
set "_L=%~2"
if defined _V set "_L=%~2 !_V!"
set "_E="
if /i "!_O!"=="portable" echo     [ok]     !_L! - copie portable%~5
if /i "!_O!"=="variable" echo     [ok]     !_L! - variable BM_%~1 : !_C!%~5
if /i "!_O!"=="systeme" echo     [repli]  !_L! - installation du poste : !_C!%~5
if /i "!_O!"=="systeme" set "_E=R"
if /i "!_O!"=="absent" set "_E=M"
if not defined _O set "_E=M"
if "!_E!"=="M" if "%~3"=="1" echo     [MANQUE] %~2 - ni copie portable dans outils\%~4, ni installation du poste
if "!_E!"=="M" if not "%~3"=="1" echo     [info]   %~2 absent - ni copie portable dans outils\%~4, ni installation du poste
endlocal & set "_BM_ETAT=%_E%"
if "%_BM_ETAT%"=="R" set "REPLI_OUTIL=1"
if "%_BM_ETAT%"=="M" if "%~3"=="1" set "MANQUE_OUTIL=1"
set "_BM_ETAT="
goto :eof

:ligne_ezdxf
if not defined BM_PYTHON goto :eof
if not defined _BM_V_EZDXF echo     [info]   ezdxf non verifie - PowerShell n'a pas repondu
if not defined _BM_V_EZDXF goto :eof
if /i "%_BM_V_EZDXF%"=="ABSENT" echo     [MANQUE] ezdxf dans ce Python - ni DXF ni DWG possibles
if /i "%_BM_V_EZDXF%"=="ABSENT" set "MANQUE_OUTIL=1"
if /i not "%_BM_V_EZDXF%"=="ABSENT" echo     [ok]     ezdxf %_BM_V_EZDXF% - DXF, et DWG par ODA
goto :eof

:ligne_navigateur
if not defined BM_NAVIGATEUR echo     [info]   aucun navigateur pour les PDF - ni Edge ni Chrome
if not defined BM_NAVIGATEUR goto :eof
set "_NAV="
for %%I in ("%BM_NAVIGATEUR%") do set "_NAV=%%~nI"
if /i "%_NAV%"=="msedge" set "_NAV=Edge"
if /i "%_NAV%"=="chrome" set "_NAV=Chrome"
if /i "%BM_ORIGINE_NAVIGATEUR%"=="variable" echo     [ok]     Navigateur %_NAV% %_BM_V_NAVIGATEUR% - PDF, choisi par BM_NAVIGATEUR
if /i not "%BM_ORIGINE_NAVIGATEUR%"=="variable" echo     [ok]     Navigateur %_NAV% %_BM_V_NAVIGATEUR% - PDF, fourni par Windows ou le poste
set "_NAV="
goto :eof

rem  Git : BM_GIT_BASH et CLAUDE_CODE_GIT_BASH_PATH sont poses par chemins.cmd
rem  (copie portable outils\git d'abord) ; la session Claude en herite.

rem  GitHub CLI : sa connexion reste celle de l'utilisateur Windows (jeton dans le
rem  gestionnaire d'identifiants). On demande a gh le NOM du compte configure, hors
rem  ligne (gh config get user) : aucun jeton n'est lu ni ecrit par ce lanceur.
:ligne_gh_connexion
if not defined BM_GH goto :eof
set "_GHU="
for /f "delims=" %%U in ('call "%%BM_GH%%" config get user -h github.com 2^>nul') do if not defined _GHU set "_GHU=%%U"
if defined _GHU echo              compte GitHub configure : %_GHU% - connexion de l'utilisateur Windows
if not defined _GHU echo     [info]   GitHub CLI pas connecte : taper  gh auth login  une fois, dans une fenetre
set "_GHU="
goto :eof

rem  Le programme Metre : verifie, jamais demarre d'office (option /metre).
:ligne_metre
if not exist "%RACINE%Metre\demarrer.bat" echo     [info]   programme Metre absent de ce dossier
if not exist "%RACINE%Metre\demarrer.bat" goto :eof
set "_ME="
if not exist "%RACINE%Metre\donnees\pgdata\PG_VERSION" set "_ME=pas de base dans Metre\donnees\pgdata"
if not exist "%RACINE%Metre\frontend\node_modules" set "_ME=interface non installee, voir Metre\installer.bat"
if not defined BM_POSTGRES set "_ME=PostgreSQL introuvable"
if defined _ME echo     [MANQUE] programme Metre - %_ME%
if defined _ME goto metre_ligne_fin
set "_MEP=arrete ; Demarrer-Blender.bat /metre le demarre"
if exist "%CURL_EXE%" "%CURL_EXE%" -s -o nul --max-time 2 "http://127.0.0.1:8000/health" && set "_MEP=en marche : http://localhost:5174"
echo     [ok]     programme Metre - base dans Metre\donnees\pgdata ; %_MEP%
:metre_ligne_fin
set "_ME="
set "_MEP="
goto :eof

:ligne_freecad
set "_FC="
for %%I in ("%RACINE%..\freecad-mcp\mcp_freecad.py") do set "_FC=%%~fI"
if exist "%_FC%" echo     [ok]     pont MCP FreeCAD - profil bim-freecad
if not exist "%_FC%" echo     [info]   pont MCP FreeCAD absent - profil bim-freecad inutilisable
set "_FC="
goto :eof

rem  Claude Code : l'installation du poste d'abord (elle se met a jour), sinon la
rem  copie portable outils\claude\claude.exe.
:trouver_claude
set "CLAUDE_CMD="
set "CLAUDE_ORIGINE="
for /f "delims=" %%C in ('%WHERE_EXE% claude.cmd 2^>nul') do if not defined CLAUDE_CMD set "CLAUDE_CMD=%%C"
if not defined CLAUDE_CMD for /f "delims=" %%C in ('%WHERE_EXE% claude.exe 2^>nul') do if not defined CLAUDE_CMD set "CLAUDE_CMD=%%C"
if not defined CLAUDE_CMD if exist "%USERPROFILE%\.local\bin\claude.exe" set "CLAUDE_CMD=%USERPROFILE%\.local\bin\claude.exe"
if not defined CLAUDE_CMD if exist "%APPDATA%\npm\claude.cmd" set "CLAUDE_CMD=%APPDATA%\npm\claude.cmd"
if defined CLAUDE_CMD set "CLAUDE_ORIGINE=poste"
if not defined CLAUDE_CMD if exist "%RACINE%outils\claude\claude.exe" set "CLAUDE_ORIGINE=portable"
if not defined CLAUDE_CMD if exist "%RACINE%outils\claude\claude.exe" set "CLAUDE_CMD=%RACINE%outils\claude\claude.exe"
goto :eof

rem  Garde outils\claude\claude.exe au niveau de l'installation du poste, apres sa
rem  mise a jour. Seulement si la copie portable existe deja : la supprimer arrete
rem  ce rafraichissement. /XO : jamais remplacer une copie plus recente.
:rafraichir_copie_portable
if not exist "%RACINE%outils\claude\claude.exe" goto :eof
set "_SRC="
for %%I in ("%CLAUDE_CMD%") do if /i "%%~xI"==".cmd" set "_SRC=%%~dpInode_modules\@anthropic-ai\claude-code\bin"
for %%I in ("%CLAUDE_CMD%") do if /i "%%~xI"==".exe" set "_SRC=%%~dpI"
if not defined _SRC goto :eof
if "%_SRC:~-1%"=="\" set "_SRC=%_SRC:~0,-1%"
if not exist "%_SRC%\claude.exe" goto rafraichir_fin
"%ROBOCOPY_EXE%" "%_SRC%" "%RACINE%outils\claude" claude.exe /XO /R:1 /W:1 /NJH /NJS /NFL /NDL /NP >nul
set "_RC=%errorlevel%"
if %_RC% GEQ 8 echo   [info]   copie portable outils\claude non rafraichie - peut-etre en cours d'usage
if %_RC% GEQ 1 if %_RC% LSS 8 echo   [ok]     copie portable outils\claude rafraichie : nouvelle version de Claude Code
set "_RC="
:rafraichir_fin
set "_SRC="
goto :eof

rem  :cle NOM "usage" - une cle posee pour l'utilisateur mais absente de cette
rem  fenetre est lue dans le registre, pour que la session la voie. Jamais affichee.
:cle
if defined %~1 echo     [ok]     %~1 - %~2
if defined %~1 goto :eof
for /f "tokens=1,2,*" %%a in ('%REG_EXE% query HKCU\Environment /v %~1 2^>nul') do if /i "%%a"=="%~1" set "%~1=%%c"
if defined %~1 echo     [ok]     %~1 - %~2 - lue dans le registre de l'utilisateur
if defined %~1 goto :eof
echo     [MANQUE] %~1 - %~2
set "CLE_MANQUE=1"
goto :eof

:aide_cles
echo.
echo     Pour poser une cle manquante, une seule fois par poste :
echo       1. ouvrez PowerShell ;
echo       2. tapez, en remplacant NOM et VALEUR :
echo          [Environment]::SetEnvironmentVariable('NOM', 'VALEUR', 'User')
echo       3. fermez cette fenetre et relancez Demarrer-Blender.bat.
echo     Cle Google Gemini : https://aistudio.google.com/apikey - voir README.md.
echo     Ne les recopiez dans aucun autre fichier.
goto :eof
