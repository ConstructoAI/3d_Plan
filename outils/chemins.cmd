@echo off
rem =============================================================================
rem  outils\chemins.cmd - pose les chemins des outils pour la session (cmd.exe)
rem =============================================================================
rem
rem  Appel :  call "<racine>\outils\chemins.cmd"            (depuis un .bat)
rem           call "<racine>\outils\chemins.cmd" /versions  (le lanceur : ajoute
rem           _BM_V_<X>, versions lues dans les .exe, et _BM_V_EZDXF)
rem
rem  Pose :   BM_RACINE, BM_PYTHON, BM_BLENDER, BM_ODA_CONVERTISSEUR,
rem           BM_ODA_VISIONNEUSE, BM_NODE, BM_NAVIGATEUR, BM_POSTGRES (le DOSSIER
rem           bin de PostgreSQL 18), BM_GIT_BASH (bash.exe de Git for Windows),
rem           BM_GH (gh.exe), BM_PROJET, et pour chacun BM_ORIGINE_<X> : portable,
rem           systeme, variable ou absent. Et CLAUDE_CODE_GIT_BASH_PATH = BM_GIT_BASH.
rem  PATH :   met en TETE le dossier de Python, celui de Node et celui d'ODA File
rem           Converter (ezdxf le cherche d'abord dans le PATH), puis le dossier cmd
rem           de Git et celui de gh. Jamais le Scripts du Python portable : ses
rem           lanceurs .exe visent l'ancien Python, on passe par python -m pip et
rem           python -m pytest. Jamais PostgreSQL, ni bin ou usr\bin de Git.
rem  Copies PORTABLES seulement (consignes verifiees des agents, outils\*\PRET.txt) :
rem           Python : PYTHONNOUSERSITE=1, sans PYTHONHOME ni PYTHONPATH herites ;
rem           Blender : BLENDER_SYSTEM_RESOURCES et CUDA_CACHE_PATH, sans les
rem           BLENDER_USER_* ni BLENDER_SYSTEM_* herites ; ODA : sans QT_PLUGIN_PATH
rem           ni QT_QPA_PLATFORM_PLUGIN_PATH ; Node : sans NODE_OPTIONS ni NODE_PATH.
rem           Tout Node trouve : npm_config_update_notifier=false, sauf s'il est pose.
rem
rem  La logique est dans chemins.ps1 (la meme que chemins.py) : ce fichier ne fait
rem  que recopier ses lignes NOM=valeur dans la session. Sans PowerShell, repli
rem  minimal : la racine et les copies portables seulement.
rem
rem  Pas de setlocal : les variables doivent survivre dans le script appelant.
rem  Les variables de travail commencent par _BM_ et sont effacees a la fin.
rem  Pas d'accents : cmd.exe demarre en page de codes 850 ou 437.
rem =============================================================================

set "_BM_PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
set "_BM_PS1=%~dp0chemins.ps1"
set "_BM_ICI=%~dp0"
set "_BM_OPT="
set "_BM_OK="
if /i "%~1"=="/versions" set "_BM_OPT=-Versions"
if "%BM_TEST_SANS_POWERSHELL%"=="1" goto _bm_sans_powershell
if not exist "%_BM_PS%" goto _bm_sans_powershell
if not exist "%_BM_PS1%" goto _bm_sans_powershell

rem  "call" en tete et pourcents doubles : c'est le cmd enfant qui developpe les deux
rem  chemins, ce qui protege ceux qui contiennent des parentheses ou des espaces.
rem  (_BM_OPT, lui, est developpe ici : vide, il resterait ecrit tel quel chez l'enfant.)
for /f "tokens=1,* delims==" %%A in ('call "%%_BM_PS%%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%%_BM_PS1%%" -Sortie cmd %_BM_OPT%') do (
  set "%%A=%%B"
  set "_BM_OK=1"
)
if defined _BM_OK goto _bm_fin
echo   [attention] outils\chemins.cmd : PowerShell n'a rien rendu - copies portables seulement.

:_bm_sans_powershell
for %%I in ("%_BM_ICI%..") do set "BM_RACINE=%%~fI"
call :_bm_portable PYTHON "python\python.exe"
call :_bm_portable BLENDER "blender\blender.exe"
call :_bm_portable ODA_CONVERTISSEUR "oda\convertisseur\ODAFileConverter.exe"
call :_bm_portable ODA_VISIONNEUSE "oda\visionneuse\ODAViewer.exe"
call :_bm_portable NODE "node\node.exe"
call :_bm_portable POSTGRES "postgresql\bin\pg_ctl.exe"
if defined BM_POSTGRES set "BM_POSTGRES=%_BM_ICI%postgresql\bin"
call :_bm_portable GIT_BASH "git\bin\bash.exe"
call :_bm_portable GH "gh\gh.exe"
set "BM_NAVIGATEUR="
set "BM_ORIGINE_NAVIGATEUR=absent"
set "BM_PROJET="
set "BM_ORIGINE_PROJET=absent"
if defined BM_GIT_BASH set "CLAUDE_CODE_GIT_BASH_PATH=%BM_GIT_BASH%"
rem  _bm_tete ajoute EN TETE : appels dans l'ordre inverse du PATH voulu.
if defined BM_GH call :_bm_tete "%_BM_ICI%gh"
if defined BM_GIT_BASH if exist "%_BM_ICI%git\cmd\" call :_bm_tete "%_BM_ICI%git\cmd"
if defined BM_ODA_CONVERTISSEUR call :_bm_tete "%_BM_ICI%oda\convertisseur"
if defined BM_NODE call :_bm_tete "%_BM_ICI%node"
if defined BM_PYTHON call :_bm_tete "%_BM_ICI%python"
rem  Copies portables : memes consignes que chemins.ps1 (outils\*\PRET.txt).
if defined BM_PYTHON set "PYTHONHOME="
if defined BM_PYTHON set "PYTHONPATH="
if defined BM_PYTHON set "PYTHONNOUSERSITE=1"
if defined BM_ODA_CONVERTISSEUR set "QT_PLUGIN_PATH="
if defined BM_ODA_CONVERTISSEUR set "QT_QPA_PLATFORM_PLUGIN_PATH="
if defined BM_ODA_VISIONNEUSE set "QT_PLUGIN_PATH="
if defined BM_ODA_VISIONNEUSE set "QT_QPA_PLATFORM_PLUGIN_PATH="
if defined BM_NODE set "NODE_OPTIONS="
if defined BM_NODE set "NODE_PATH="
if defined BM_NODE if not defined npm_config_update_notifier set "npm_config_update_notifier=false"
call :_bm_config_claude
if not defined BM_BLENDER goto _bm_fin
for /f "delims==" %%V in ('set BLENDER_USER_ 2^>nul') do set "%%V="
for /f "delims==" %%V in ('set BLENDER_SYSTEM_ 2^>nul') do set "%%V="
for /d %%D in ("%_BM_ICI%blender\*") do if exist "%%D\python\bin\python.exe" set "BLENDER_SYSTEM_RESOURCES=%%~fD"
set "CUDA_CACHE_PATH=%_BM_ICI%blender\portable\cuda_cache"
goto _bm_fin

:_bm_portable
set "BM_%~1="
set "BM_ORIGINE_%~1=absent"
if exist "%_BM_ICI%%~2" set "BM_%~1=%_BM_ICI%%~2"
if exist "%_BM_ICI%%~2" set "BM_ORIGINE_%~1=portable"
goto :eof

:_bm_tete
set "PATH=%~1;%PATH%"
goto :eof

rem  Zero trace : CLAUDE_CONFIG_DIR = outils\claude\config s'il existe ;
rem  BM_CLAUDE_CONFIG=profil : retour au profil de l'utilisateur ; un dossier : celui-la.
:_bm_config_claude
if /i "%BM_CLAUDE_CONFIG%"=="profil" set "CLAUDE_CONFIG_DIR="
if /i "%BM_CLAUDE_CONFIG%"=="profil" goto :eof
if defined BM_CLAUDE_CONFIG for %%I in ("%BM_CLAUDE_CONFIG%") do set "CLAUDE_CONFIG_DIR=%%~fI"
if defined BM_CLAUDE_CONFIG goto :eof
if exist "%_BM_ICI%claude\config\" set "CLAUDE_CONFIG_DIR=%_BM_ICI%claude\config"
goto :eof

:_bm_fin
set "_BM_PS="
set "_BM_PS1="
set "_BM_ICI="
set "_BM_OPT="
set "_BM_OK="
goto :eof
