@echo off
setlocal
title 3D Plan - installation du poste
cd /d "%~dp0"

rem =============================================================================
rem  3D PLAN - INSTALLER CE QUI MANQUE, puis verifier le poste
rem =============================================================================
rem
rem  A double-cliquer UNE fois, avant Demarrer-Blender.bat.
rem
rem    1. inventaire : Python, ses paquets, Blender, ODA File Converter, Git,
rem       Node.js et Claude Code ;
rem    2. UNE question, pour tout le lot ; Entree seule vaut NON ;
rem    3. installation de ce qui manque, par winget (fourni avec Windows 10 et 11) ;
rem    4. le diagnostic du lanceur, qui dit outil par outil ce qui est trouve.
rem
rem  Installer.bat /essai   inventaire seulement : dit ce qui serait installe,
rem                         et n'installe RIEN.
rem
rem  Ce que ce fichier n'installe PAS, et pourquoi :
rem    - ODA File Converter : sa licence s'accepte sur le site de l'Open Design
rem      Alliance ; le fichier ouvre la page, vous installez ;
rem    - votre abonnement Claude (Max 20x) et votre connexion : Claude Code les
rem      demande a son premier lancement ;
rem    - votre cle d'API Google Gemini (photo hyperrealiste) : voir README.md.
rem
rem  Python et Claude Code s'installent pour VOTRE compte, sans droits
rem  d'administrateur. Blender, Git et Node.js s'installent pour toute la
rem  machine : Windows affichera une invite, que vous pouvez refuser.
rem
rem  Messages sans accents : cmd.exe demarre en page de codes 850 ou 437, et un
rem  message accentue s'y affiche en charabia.
rem
rem  Essais (ne sert qu'a eprouver ce fichier) : la variable
rem  BM_INSTALL_SIMULER_ABSENT, par exemple "PYTHON BLENDER", fait compter ces
rem  programmes comme absents. A employer avec /essai.
rem =============================================================================

set "RACINE=%~dp0"
set "PS_EXE=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
set "WHERE_EXE=%SystemRoot%\System32\where.exe"
set "CURL_EXE=%SystemRoot%\System32\curl.exe"
set "URL_ODA=https://www.opendesign.com/guestfiles/oda_file_converter"
set "MODE_ESSAI="
if /i "%~1"=="/essai" set "MODE_ESSAI=1"

echo.
echo   ============================================================
echo      3D PLAN  -  installation du poste
echo.
echo      Une gracieusete de Sylvain Leduc - Constructo AI inc.
echo      www.constructoai.ca
echo   ============================================================
echo.
if defined MODE_ESSAI echo   MODE ESSAI : rien ne sera installe.
if defined MODE_ESSAI echo.

if not exist "%RACINE%Demarrer-Blender.bat" echo   ERREUR : Demarrer-Blender.bat est absent. Lancez ce fichier depuis le dossier du depot.
if not exist "%RACINE%Demarrer-Blender.bat" goto echec

rem ---------------------------------------------------------------------------
rem  [1/4] Inventaire
rem ---------------------------------------------------------------------------
echo   [1/4] Inventaire du poste...
echo.

set "A_WINGET="
%WHERE_EXE% winget >nul 2>&1 && set "A_WINGET=1"

call :trouver_python
call :trouver_blender
call :trouver_oda
call :trouver_git
call :trouver_node
call :trouver_claude
call :simuler_absents
call :verifier_paquets

set "MANQUE_PYTHON="
set "MANQUE_PAQUETS="
set "MANQUE_BLENDER="
set "MANQUE_ODA="
set "MANQUE_GIT="
set "MANQUE_NODE="
set "MANQUE_CLAUDE="
if not defined PY set "MANQUE_PYTHON=1"
if not defined PAQUETS_OK set "MANQUE_PAQUETS=1"
if not defined BLENDER_EXE set "MANQUE_BLENDER=1"
if not defined ODA_EXE set "MANQUE_ODA=1"
if not defined GIT_BASH set "MANQUE_GIT=1"
if not defined NODE_EXE set "MANQUE_NODE=1"
if not defined CLAUDE_EXE set "MANQUE_CLAUDE=1"

call :ligne "Python 3" PY
if defined PY if defined PAQUETS_OK echo     [ok]     paquets Python - ezdxf, PyMuPDF, Pillow, numpy, scipy, reportlab
if defined PY if not defined PAQUETS_OK echo     [MANQUE] paquets Python - requirements.txt
call :ligne "Blender" BLENDER_EXE
call :ligne "ODA File Converter" ODA_EXE
call :ligne "Git pour Windows" GIT_BASH
call :ligne "Node.js - facultatif, PDF 3D" NODE_EXE
call :ligne "Claude Code" CLAUDE_EXE
echo.

set "A_INSTALLER="
if defined MANQUE_PYTHON set "A_INSTALLER=1"
if defined MANQUE_PAQUETS set "A_INSTALLER=1"
if defined MANQUE_BLENDER set "A_INSTALLER=1"
if defined MANQUE_GIT set "A_INSTALLER=1"
if defined MANQUE_NODE set "A_INSTALLER=1"
if defined MANQUE_CLAUDE set "A_INSTALLER=1"

if not defined A_INSTALLER if not defined MANQUE_ODA echo   Tout est deja en place. Rien a installer.
if not defined A_INSTALLER if not defined MANQUE_ODA goto diagnostic
if not defined A_INSTALLER goto etape_oda

rem ---------------------------------------------------------------------------
rem  [2/4] Une seule question, pour tout le lot
rem ---------------------------------------------------------------------------
echo   [2/4] Ce qui sera installe :
echo.
if defined MANQUE_PYTHON  echo     - Python 3.13          winget Python.Python.3.13, pour votre compte
if defined MANQUE_PAQUETS echo     - paquets Python       pip install -r requirements.txt
if defined MANQUE_BLENDER echo     - Blender              winget %ID_BLENDER%
if defined MANQUE_GIT     echo     - Git pour Windows     winget Git.Git
if defined MANQUE_NODE    echo     - Node.js              winget OpenJS.NodeJS.22 ; facultatif
if defined MANQUE_CLAUDE  echo     - Claude Code          installateur officiel, pour votre compte
echo.
echo   Blender, Git et Node.js s'installent pour toute la machine : Windows
echo   affichera une invite pour chacun. Vous pouvez la refuser.
echo.

if not defined A_WINGET echo   ATTENTION : winget est absent de ce poste. Il vient avec
if not defined A_WINGET echo   l'application "Programme d'installation d'application" du Microsoft
if not defined A_WINGET echo   Store. Sans lui, seuls Claude Code et les paquets Python peuvent
if not defined A_WINGET echo   s'installer d'ici ; le reste s'installe a la main, voir README.md.
if not defined A_WINGET echo.

if defined MODE_ESSAI echo   MODE ESSAI : on s'arrete ici, rien n'a ete installe.
if defined MODE_ESSAI goto fin_essai

rem  Pre-remplie a N : si l'entree est redirigee, set /p laisse la variable
rem  inchangee. On n'installe alors RIEN plutot que d'installer sans accord.
set "REPONSE=N"
echo   Tapez O puis Entree. ENTREE SEULE VAUT NON.
set /p "REPONSE=Installer maintenant ? [O/N, defaut N] "
echo.
set "REPONSE=%REPONSE:"=%"
if not defined REPONSE set "REPONSE=N"
set "ACCORD="
if /i "%REPONSE%"=="O" set "ACCORD=1"
if /i "%REPONSE%"=="OUI" set "ACCORD=1"
if /i "%REPONSE%"=="Y" set "ACCORD=1"
if /i "%REPONSE%"=="YES" set "ACCORD=1"
if not defined ACCORD echo   Rien n'a ete installe.
if not defined ACCORD echo.
if not defined ACCORD goto diagnostic

rem ---------------------------------------------------------------------------
rem  [3/4] Installation
rem ---------------------------------------------------------------------------
echo   [3/4] Installation...
echo.

rem --- Python ----------------------------------------------------------------
if not defined MANQUE_PYTHON goto installer_paquets
echo   Python 3.13...
if defined A_WINGET winget install -e --id Python.Python.3.13 --scope user --source winget --silent --accept-source-agreements --accept-package-agreements
if not defined A_WINGET echo   winget est absent : Python ne peut pas etre installe d'ici.
call :trouver_python
if defined PY echo   Python installe : %PY%
if not defined PY echo   Python n'a pas pu etre installe. Installez-le depuis www.python.org,
if not defined PY echo   version 3.13, en cochant "Add python.exe to PATH", puis relancez ce fichier.
echo.

rem --- paquets Python --------------------------------------------------------
:installer_paquets
if not defined PY goto installer_blender
call :verifier_paquets
if defined PAQUETS_OK goto installer_blender
echo   Paquets Python - une seule fois, quelques minutes...
"%PY%" -m pip install --disable-pip-version-check -r "%RACINE%requirements.txt"
call :verifier_paquets
if defined PAQUETS_OK echo   Paquets Python installes.
if not defined PAQUETS_OK echo   L'installation des paquets a echoue. Cause frequente : pas de connexion,
if not defined PAQUETS_OK echo   ou un pare-feu d'entreprise. A relancer a la main :
if not defined PAQUETS_OK echo       "%PY%" -m pip install -r requirements.txt
echo.

rem --- Blender ---------------------------------------------------------------
:installer_blender
if not defined MANQUE_BLENDER goto installer_git
echo   Blender - une invite de Windows va s'afficher...
if defined A_WINGET winget install -e --id %ID_BLENDER% --source winget --silent --accept-source-agreements --accept-package-agreements
if not defined A_WINGET echo   winget est absent : Blender ne peut pas etre installe d'ici.
call :trouver_blender
if defined BLENDER_EXE echo   Blender installe : %BLENDER_EXE%
if not defined BLENDER_EXE echo   Blender n'a pas pu etre installe. Telechargez Blender 5.2 LTS :
if not defined BLENDER_EXE echo       https://www.blender.org/download/lts/
echo.

rem --- Git pour Windows ------------------------------------------------------
:installer_git
if not defined MANQUE_GIT goto installer_node
echo   Git pour Windows - une invite de Windows va s'afficher...
if defined A_WINGET winget install -e --id Git.Git --source winget --silent --accept-source-agreements --accept-package-agreements
if not defined A_WINGET echo   winget est absent : Git ne peut pas etre installe d'ici.
call :trouver_git
if defined GIT_BASH echo   Git installe : %GIT_BASH%
if not defined GIT_BASH echo   Git n'a pas pu etre installe. Ce n'est pas bloquant : Claude Code
if not defined GIT_BASH echo   utilisera PowerShell. Plus tard : https://git-scm.com/downloads/win
echo.

rem --- Node.js ---------------------------------------------------------------
:installer_node
if not defined MANQUE_NODE goto installer_claude
echo   Node.js - facultatif ; une invite de Windows va s'afficher...
if defined A_WINGET winget install -e --id OpenJS.NodeJS.22 --source winget --silent --accept-source-agreements --accept-package-agreements
if not defined A_WINGET echo   winget est absent : Node.js ne peut pas etre installe d'ici.
call :trouver_node
if defined NODE_EXE echo   Node.js installe : %NODE_EXE%
if not defined NODE_EXE echo   Node.js n'est pas installe. Seul le PDF 3D en a besoin.
echo.

rem --- Claude Code -----------------------------------------------------------
:installer_claude
if not defined MANQUE_CLAUDE goto etape_oda
echo   Claude Code...
rem  Voie 1 : installateur officiel, par curl. Chemins ABSOLUS : on ne veut pas
rem  telecharger puis executer un installateur dans le dossier du depot.
if not exist "%CURL_EXE%" goto claude_voie2
if not exist "%TEMP%\" goto claude_voie2
"%CURL_EXE%" -fsSL https://claude.ai/install.cmd -o "%TEMP%\cc_install.cmd"
if exist "%TEMP%\cc_install.cmd" call "%TEMP%\cc_install.cmd"
del "%TEMP%\cc_install.cmd" >nul 2>&1
call :trouver_claude
if defined CLAUDE_EXE goto claude_ok
:claude_voie2
rem  Voie 2 : installateur officiel, par PowerShell.
if exist "%PS_EXE%" "%PS_EXE%" -NoProfile -ExecutionPolicy Bypass -Command "irm https://claude.ai/install.ps1 | iex"
call :trouver_claude
if defined CLAUDE_EXE goto claude_ok
rem  Voie 3 : winget. Une installation winget ne se met pas a jour toute seule.
if defined A_WINGET winget install -e --id Anthropic.ClaudeCode --source winget --silent --accept-source-agreements --accept-package-agreements
call :trouver_claude
if defined CLAUDE_EXE goto claude_ok
echo   Claude Code n'a pas pu etre installe. Installez-le a la main, puis
echo   relancez ce fichier :  https://code.claude.com/docs/en/setup
echo.
goto etape_oda
:claude_ok
echo   Claude Code installe : %CLAUDE_EXE%
echo   A son premier lancement, il demandera de vous connecter : il faut un
echo   compte Claude Max 20x.
echo.

rem ---------------------------------------------------------------------------
rem  ODA File Converter : a la main, parce que sa licence s'accepte sur son site
rem ---------------------------------------------------------------------------
:etape_oda
if not defined MODE_ESSAI call :trouver_oda
if defined ODA_EXE goto diagnostic
echo   ------------------------------------------------------------
echo   ODA FILE CONVERTER - a installer a la main
echo   Il convertit les DXF en DWG. Il est gratuit ; sa licence s'accepte
echo   sur le site de l'Open Design Alliance :
echo       %URL_ODA%
echo   Prenez la version Windows 64 bits, installez-la a l'emplacement
echo   propose, puis relancez ce fichier. Sans lui, le poste produit des
echo   DXF, pas des DWG.
echo   ------------------------------------------------------------
echo.
if defined MODE_ESSAI goto fin_essai
set "REPONSE=N"
set /p "REPONSE=Ouvrir cette page dans le navigateur ? [O/N, defaut N] "
echo.
set "REPONSE=%REPONSE:"=%"
if not defined REPONSE set "REPONSE=N"
if /i "%REPONSE%"=="O" start "" "%URL_ODA%"
if /i "%REPONSE%"=="OUI" start "" "%URL_ODA%"

rem ---------------------------------------------------------------------------
rem  [4/4] Le diagnostic du lanceur
rem ---------------------------------------------------------------------------
:diagnostic
echo.
echo   [4/4] Diagnostic du poste - Demarrer-Blender.bat /verifier
echo.
call "%RACINE%Demarrer-Blender.bat" /verifier
echo.
echo   ============================================================
echo      Pour travailler : double-cliquez Demarrer-Blender.bat
echo.
echo      A prevoir : un compte Claude Max 20x - la session tourne en
echo      Opus 5.5, effort max - et, pour la photo hyperrealiste, un
echo      compte Google et sa cle d'API Gemini : voir README.md.
echo   ============================================================
echo.
endlocal
exit /b 0

:fin_essai
echo.
echo   Fin de l'essai. Rien n'a ete installe ni modifie.
echo.
endlocal
exit /b 0

:echec
echo.
pause
endlocal
exit /b 1

rem =============================================================================
rem  Sous-routines. Style a plat, sans bloc entre parentheses autour d'un chemin :
rem  un chemin qui contient une parenthese, comme Program Files (x86), casserait
rem  un bloc.
rem =============================================================================

rem  :ligne "Libelle" VARIABLE  - affiche l'etat d'un programme.
:ligne
setlocal EnableDelayedExpansion
set "_V=!%~2!"
if defined _V echo     [ok]     %~1 : !_V!
if not defined _V echo     [MANQUE] %~1
endlocal
goto :eof

rem  Python : une vraie installation, jamais l'amorce du Microsoft Store
rem  (%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe), qui ouvre le Store.
:trouver_python
set "PY="
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if defined PY goto :eof
if exist "%ProgramFiles%\Python313\python.exe" set "PY=%ProgramFiles%\Python313\python.exe"
if defined PY goto :eof
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do if exist "%%~fD\python.exe" set "PY=%%~fD\python.exe"
if defined PY goto :eof
for /d %%D in ("%ProgramFiles%\Python3*") do if exist "%%~fD\python.exe" set "PY=%%~fD\python.exe"
if defined PY goto :eof
for /f "delims=" %%P in ('%WHERE_EXE% python.exe 2^>nul') do call :retenir_python "%%~fP"
goto :eof

:retenir_python
if defined PY goto :eof
set "_P=%~1"
if not "%_P:WindowsApps=%"=="%_P%" goto :eof
set "PY=%_P%"
goto :eof

rem  Les paquets dont le poste ne peut pas se passer.
:verifier_paquets
set "PAQUETS_OK="
if not defined PY goto :eof
if defined SIMULER_PAQUETS goto :eof
"%PY%" -c "import ezdxf, fitz, PIL, numpy, scipy, reportlab" >nul 2>&1
if not errorlevel 1 set "PAQUETS_OK=1"
goto :eof

rem  Blender : la version la plus haute sous Program Files. ID_BLENDER est le
rem  paquet winget installe s'il manque : la version courante de Blender (5.2
rem  au 2026-10-10, celle avec laquelle le poste est eprouve).
:trouver_blender
set "ID_BLENDER=BlenderFoundation.Blender"
set "BLENDER_EXE="
for /d %%D in ("%ProgramFiles%\Blender Foundation\Blender*") do if exist "%%~fD\blender.exe" set "BLENDER_EXE=%%~fD\blender.exe"
goto :eof

:trouver_oda
set "ODA_EXE="
for /d %%D in ("%ProgramFiles%\ODA\ODAFileConverter*") do if exist "%%~fD\ODAFileConverter.exe" set "ODA_EXE=%%~fD\ODAFileConverter.exe"
goto :eof

:trouver_git
set "GIT_BASH="
if exist "%ProgramFiles%\Git\bin\bash.exe" set "GIT_BASH=%ProgramFiles%\Git\bin\bash.exe"
if not defined GIT_BASH if exist "%LOCALAPPDATA%\Programs\Git\bin\bash.exe" set "GIT_BASH=%LOCALAPPDATA%\Programs\Git\bin\bash.exe"
goto :eof

:trouver_node
set "NODE_EXE="
if exist "%ProgramFiles%\nodejs\node.exe" set "NODE_EXE=%ProgramFiles%\nodejs\node.exe"
if defined NODE_EXE goto :eof
for /f "delims=" %%P in ('%WHERE_EXE% node.exe 2^>nul') do if not defined NODE_EXE set "NODE_EXE=%%~fP"
goto :eof

rem  Claude Code : memes emplacements que le lanceur.
:trouver_claude
set "CLAUDE_EXE="
if exist "%USERPROFILE%\.local\bin\claude.exe" set "CLAUDE_EXE=%USERPROFILE%\.local\bin\claude.exe"
if defined CLAUDE_EXE goto :eof
for /f "delims=" %%C in ('%WHERE_EXE% claude.cmd 2^>nul') do if not defined CLAUDE_EXE set "CLAUDE_EXE=%%~fC"
if defined CLAUDE_EXE goto :eof
for /f "delims=" %%C in ('%WHERE_EXE% claude.exe 2^>nul') do if not defined CLAUDE_EXE set "CLAUDE_EXE=%%~fC"
if defined CLAUDE_EXE goto :eof
if exist "%APPDATA%\npm\claude.cmd" set "CLAUDE_EXE=%APPDATA%\npm\claude.cmd"
goto :eof

rem  Essais seulement : compter comme absents les programmes nommes dans
rem  BM_INSTALL_SIMULER_ABSENT. Sans effet hors du mode /essai : on n'installe
rem  jamais par-dessus un programme qui est la.
:simuler_absents
set "SIMULER_PAQUETS="
if not defined BM_INSTALL_SIMULER_ABSENT goto :eof
if not defined MODE_ESSAI echo   BM_INSTALL_SIMULER_ABSENT est ignoree hors du mode /essai.
if not defined MODE_ESSAI goto :eof
echo   ESSAI : programmes comptes comme absents : %BM_INSTALL_SIMULER_ABSENT%
echo.
for %%N in (%BM_INSTALL_SIMULER_ABSENT%) do call :simuler_un %%N
goto :eof

:simuler_un
if /i "%~1"=="PYTHON" set "PY="
if /i "%~1"=="PAQUETS" set "SIMULER_PAQUETS=1"
if /i "%~1"=="BLENDER" set "BLENDER_EXE="
if /i "%~1"=="ODA" set "ODA_EXE="
if /i "%~1"=="GIT" set "GIT_BASH="
if /i "%~1"=="NODE" set "NODE_EXE="
if /i "%~1"=="CLAUDE" set "CLAUDE_EXE="
goto :eof
