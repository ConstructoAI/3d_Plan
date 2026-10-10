<#
.SYNOPSIS
  Copie le dossier du poste (blender-main) vers un autre emplacement ou un autre poste, avec un manifeste.

.DESCRIPTION
  2026-09-25, soir. Aucun chemin écrit en dur : la source est le dossier qui contient outils\ (le parent
  du dossier de ce script).

  Dans l'ordre :
    1. ARRÊTE la base du programme Métré (Metre\scripts\pg-local.ps1 arreter, pg_ctl stop en mode fast),
       si elle tourne : un cluster PostgreSQL copié en marche est corrompu. Si elle ne s'arrête pas, rien
       n'est copié. Le serveur du Métré, lui, peut rester ouvert : il se reconnecte seul après.
    2. Copie TOUT par robocopy /E (plusieurs fils, jonctions non suivies) ; codes de sortie 0 à 7 =
       réussite, 8 et plus = échec. Rien n'est jamais effacé à la destination.
    3. Écrit à la destination outils\manifeste_copie.json : chemin relatif, taille et SHA-256 de CHAQUE
       fichier copié (outils\manifeste.py, 8 fils). Mesuré sur ce poste : 119 397 fichiers, 5,3 Go ;
       410 s à froid, 86 s quand les fichiers viennent d'être lus (c'est le cas juste après la copie).
    4. Relance la base du Métré à l'origine, si c'est lui qui l'avait arrêtée (même en cas d'échec).

  Exclus (les MÊMES pour robocopy et pour le manifeste) :
    - les dossiers __pycache__ et .pytest_cache (Python recompile au premier usage) ;
    - les fichiers de session PRET_* et ETAT_* (rapports d'agents, état des services de CE poste) et les
      résultats des tests d'autonomie (outils\diagnostic\resultats_autonomie_*) ;
    - les journaux temporaires : Metre\donnees\pgdata.log (journal du serveur) et postmaster.pid ;
    - la connexion de Claude Code (outils\claude\config\.credentials.json), sauf -AvecConnexionClaude :
      une copie sur une clé USB ne doit pas emporter un jeton actif. On se reconnecte une fois à l'arrivée.

  Sur le poste d'arrivée : powershell -ExecutionPolicy Bypass -File <copie>\outils\verifier_copie.ps1

.PARAMETER Destination
  Le dossier de destination (créé s'il n'existe pas), par exemple X:\Poste-Blender, X étant la lettre de la clé ou du disque.
  Chemin court conseillé : 110 caractères au plus (Blender refuse les chemins longs).

.PARAMETER Essai
  Liste seulement : ce qui serait copié et exclu, le nombre de fichiers et d'octets. Ne copie rien, n'arrête
  pas la base.

.PARAMETER AvecConnexionClaude
  Copie aussi la connexion de Claude Code (déconseillé hors de l'entreprise).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File outils\copier_vers_poste.ps1 X:\Poste-Blender -Essai
.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File outils\copier_vers_poste.ps1 X:\Poste-Blender
#>
param(
    [Parameter(Mandatory = $true, Position = 0)][string]$Destination,
    [switch]$Essai,
    [switch]$AvecConnexionClaude
)

$ErrorActionPreference = 'Stop'

$outils = $PSScriptRoot
$racine = [IO.Path]::GetFullPath((Join-Path $outils '..')).TrimEnd('\')
$dest = [IO.Path]::GetFullPath($Destination).TrimEnd('\')
$sys32 = Join-Path $env:SystemRoot 'System32'
$robocopy = Join-Path $sys32 'robocopy.exe'
$psexe = Join-Path $sys32 'WindowsPowerShell\v1.0\powershell.exe'
$pgLocal = Join-Path $racine 'Metre\scripts\pg-local.ps1'
$pgData = Join-Path $racine 'Metre\donnees\pgdata'

function Titre([string]$t) { Write-Host ''; Write-Host "  $t" -ForegroundColor Cyan }
function Ok([string]$t) { Write-Host "  [ok]     $t" -ForegroundColor Green }
function Info([string]$t) { Write-Host "           $t" }
function Avis([string]$t) { Write-Host "  [attention] $t" -ForegroundColor Yellow }
function Echec([string]$t) { Write-Host "  [ÉCHEC]  $t" -ForegroundColor Red }

Write-Host ''
Write-Host '  COPIE DU DOSSIER DU POSTE VERS UN AUTRE EMPLACEMENT'
Write-Host "  Source      : $racine"
Write-Host "  Destination : $dest"
if ($Essai) { Write-Host '  Mode ESSAI : rien ne sera copié ni arrêté.' -ForegroundColor Yellow }

# ------------------------------------------------------------------ garde-fous
$cleS = $racine.ToLowerInvariant() + '\'
$cleD = $dest.ToLowerInvariant() + '\'
if ($cleD -eq $cleS) { Echec 'La destination est la source elle-même.'; exit 2 }
if ($cleD.StartsWith($cleS)) { Echec 'La destination est DANS la source : la copie se copierait elle-même.'; exit 2 }
if ($cleS.StartsWith($cleD)) { Echec 'La source est dans la destination : choisir un autre dossier.'; exit 2 }
if ($dest.Length -gt 110) {
    Avis ("Chemin de destination de {0} caractères : plus de 110. Blender refuse les chemins longs ;" -f $dest.Length)
    Info 'rapprocher la copie de la racine du disque (ex. X:\Poste-Blender).'
}
if ($dest.StartsWith('\\')) { Avis "Partage réseau : bon pour transporter, pas pour travailler (cmd.exe ne s'y place pas)." }

# Le Python du dossier, pour le manifeste
$py = Join-Path $outils 'python\python.exe'
if (-not (Test-Path -LiteralPath $py)) {
    . (Join-Path $outils 'chemins.ps1')
    $py = $env:BM_PYTHON
}
if (-not $py -or -not (Test-Path -LiteralPath $py)) { Echec 'Aucun Python pour calculer le manifeste.'; exit 2 }
$manifestePy = Join-Path $outils 'manifeste.py'

# ------------------------------------------------------------------ exclusions (une seule liste, deux usages)
$exDossiers = @('__pycache__', '.pytest_cache')
$exFichiers = @('PRET_*', 'ETAT_*', 'resultats_autonomie_*')
$exChemins = @('Metre\donnees\pgdata.log', 'Metre\donnees\pgdata\postmaster.pid', 'outils\manifeste_copie.json')
if (-not $AvecConnexionClaude) { $exChemins += 'outils\claude\config\.credentials.json' }

$argsManifeste = @()
foreach ($d in $exDossiers) { $argsManifeste += @('--exclure-dossier', $d) }
foreach ($f in $exFichiers) { $argsManifeste += @('--exclure-fichier', $f) }
foreach ($c in $exChemins) { $argsManifeste += @('--exclure-chemin', $c) }

$argsRobo = @($racine, $dest, '/E', '/COPY:DAT', '/DCOPY:DAT', '/R:1', '/W:1', '/MT:8', '/XJ', '/NP', '/NFL', '/NDL')
$argsRobo += '/XD'; $argsRobo += $exDossiers
$argsRobo += '/XF'; $argsRobo += $exFichiers; $argsRobo += @($exChemins | ForEach-Object { Join-Path $racine $_ })

Titre 'Exclus de la copie'
Info ('dossiers : ' + ($exDossiers -join ', '))
Info ('fichiers : ' + ($exFichiers -join ', '))
Info ('chemins  : ' + ($exChemins -join ', '))

$journal = Join-Path ([IO.Path]::GetTempPath()) ('copier_vers_poste_{0}.log' -f (Get-Date -Format 'yyyyMMdd_HHmmss'))

if ($Essai) {
    Titre 'Ce qui serait copié (robocopy /L, rien n''est écrit)'
    & $robocopy @argsRobo /L /NJH "/UNILOG:$journal" | Out-Null
    $code = $LASTEXITCODE
    Get-Content -LiteralPath $journal -Encoding Unicode | Select-Object -Last 9 | ForEach-Object { Info $_ }
    & $py -s -X utf8 -B $manifestePy lister $racine @argsManifeste
    Info "robocopy /L : code $code ; journal : $journal"
    Write-Host ''
    Write-Host '  ESSAI TERMINÉ : rien n''a été copié ni arrêté.'
    exit 0
}

# ------------------------------------------------------------------ 1. arrêter la base du Métré
$baseArretee = $false
if ((Test-Path -LiteralPath (Join-Path $pgData 'postmaster.pid')) -and (Test-Path -LiteralPath $pgLocal)) {
    Titre '1. Arrêt de la base du programme Métré (un cluster copié en marche est corrompu)'
    & $psexe -NoProfile -ExecutionPolicy Bypass -File $pgLocal arreter
    $code = $LASTEXITCODE
    if ($code -ne 0 -or (Test-Path -LiteralPath (Join-Path $pgData 'postmaster.pid'))) {
        Echec "La base du Métré ne s'est pas arrêtée (code $code). Rien n'est copié."
        exit 1
    }
    $baseArretee = $true
    Ok 'Base arrêtée ; elle sera relancée à la fin.'
} else {
    Titre '1. Base du programme Métré : déjà arrêtée (ou absente), rien à faire'
}

$codeSortie = 1
try {
    # -------------------------------------------------------------- 2. robocopy
    Titre '2. Copie (robocopy /E, 8 fils)'
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    $t0 = Get-Date
    & $robocopy @argsRobo "/UNILOG:$journal" | Out-Null
    $code = $LASTEXITCODE
    $duree = ((Get-Date) - $t0).TotalSeconds
    Get-Content -LiteralPath $journal -Encoding Unicode | Select-Object -Last 9 | ForEach-Object { Info $_ }
    if ($code -ge 8) {
        Echec "robocopy a échoué (code $code) après $([int]$duree) s. Journal : $journal"
    } else {
        Ok ("Copie faite en {0:N0} s (robocopy code {1} : réussite). Journal : {2}" -f $duree, $code, $journal)

        # ---------------------------------------------------------- 3. manifeste (sha256 de la SOURCE)
        Titre '3. Manifeste : taille et SHA-256 de chaque fichier de la source'
        $manifeste = Join-Path $dest 'outils\manifeste_copie.json'
        $t0 = Get-Date
        & $py -s -X utf8 -B $manifestePy ecrire $racine $manifeste @argsManifeste
        $code = $LASTEXITCODE
        if ($code -ne 0) {
            Echec "Manifeste incomplet (code $code) : voir les fichiers illisibles ci-dessus."
        } else {
            Ok ("Manifeste écrit en {0:N0} s : {1}" -f ((Get-Date) - $t0).TotalSeconds, $manifeste)
            $codeSortie = 0
        }
    }
}
finally {
    # -------------------------------------------------------------- 4. relancer la base
    if ($baseArretee) {
        Titre '4. Relance de la base du programme Métré, à l''origine'
        # Start-Process : le serveur ne doit hériter d'aucune poignée de cette fenêtre.
        $p = Start-Process -FilePath $psexe -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                ('"{0}"' -f $pgLocal), 'demarrer') -WindowStyle Hidden -PassThru
        $null = $p.Handle
        if ($p.WaitForExit(180000) -and $p.ExitCode -eq 0) { Ok 'Base du Métré relancée.' }
        else { Echec 'La base du Métré ne s''est pas relancée : Metre\scripts\pg-local.ps1 demarrer' }
    }
}

Write-Host ''
if ($codeSortie -eq 0) {
    Write-Host '  COPIE TERMINÉE.' -ForegroundColor Green
    Write-Host '  Sur le poste d''arrivée, pour vérifier la copie et le poste :'
    Write-Host ("    powershell -ExecutionPolicy Bypass -File ""{0}""" -f (Join-Path $dest 'outils\verifier_copie.ps1'))
}
exit $codeSortie
