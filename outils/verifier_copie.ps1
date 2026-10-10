<#
.SYNOPSIS
  Vérifie, sur le poste d'arrivée, une COPIE du dossier du poste, et rend un verdict clair en français.

.DESCRIPTION
  2026-09-25, soir. Aucun chemin écrit en dur : la racine vérifiée est le dossier qui contient outils\
  (le parent du dossier de ce script), sauf -Racine.

  Dans l'ordre :
    1. la LONGUEUR du chemin de la racine : 110 caractères au plus (Blender refuse les chemins longs) ;
    2. le DÉBLOCAGE des fichiers (Unblock-File) : un dossier venu d'un ZIP téléchargé ou d'un courriel
       porte sur chaque fichier la marque « venu d'Internet », qui bloque scripts et programmes ;
    3. la comparaison au MANIFESTE (outils\manifeste_copie.json, écrit par copier_vers_poste.ps1) :
       chaque fichier, sa taille et son SHA-256 (outils\manifeste.py, par le Python de la copie) ;
    4. Demarrer-Blender.bat /verifier : les outils de la copie, sans ouvrir Claude ;
    5. le VERDICT.

  Si les scripts sont bloqués sur ce poste :
    powershell -ExecutionPolicy Bypass -File <copie>\outils\verifier_copie.ps1

.PARAMETER Racine
  Autre dossier à vérifier (défaut : celui de ce script).

.PARAMETER SansDeblocage
  Ne pas lancer Unblock-File.

.PARAMETER SansLanceur
  Ne pas lancer Demarrer-Blender.bat /verifier.

.PARAMETER Rapide
  SHA-256 des .exe, .dll, .pyd et des fichiers de savoir et de réglage seulement ; la TAILLE suffit pour les
  autres. Mesuré sur une copie de 119 386 fichiers : la relecture complète prend environ 9 min à froid
  (lectures et antivirus), 1 min 30 quand les fichiers viennent d'être écrits.
#>
param(
    [string]$Racine = '',
    [switch]$SansDeblocage,
    [switch]$SansLanceur,
    [switch]$Rapide
)

$ErrorActionPreference = 'Stop'
if (-not $Racine) { $Racine = Join-Path $PSScriptRoot '..' }
$Racine = [IO.Path]::GetFullPath($Racine).TrimEnd('\')
$outils = Join-Path $Racine 'outils'
$sys32 = Join-Path $env:SystemRoot 'System32'
$defauts = New-Object System.Collections.ArrayList
$remarques = New-Object System.Collections.ArrayList

function Titre([string]$t) { Write-Host ''; Write-Host "  $t" -ForegroundColor Cyan }
function Ok([string]$t) { Write-Host "  [ok]     $t" -ForegroundColor Green }
function Info([string]$t) { Write-Host "           $t" }
function Defaut([string]$t) { Write-Host "  [DÉFAUT] $t" -ForegroundColor Red; [void]$defauts.Add($t) }
function Remarque([string]$t) { Write-Host "  [remarque] $t" -ForegroundColor Yellow; [void]$remarques.Add($t) }

Write-Host ''
Write-Host '  VÉRIFICATION D''UNE COPIE DU DOSSIER DU POSTE'
Write-Host "  Racine : $Racine"

if (-not (Test-Path -LiteralPath (Join-Path $outils 'chemins.ps1'))) {
    Defaut "Ce n'est pas le dossier du poste : outils\chemins.ps1 est absent."
    exit 1
}

# ------------------------------------------------------------------ 1. longueur du chemin
Titre '1. Longueur du chemin de la racine'
if ($Racine.Length -le 110) { Ok ("{0} caractères (110 au plus)." -f $Racine.Length) }
else {
    Defaut ("{0} caractères : plus de 110. Blender refuse les chemins longs ; rapprocher le dossier de la racine du disque (ex. X:\Poste-Blender)." -f $Racine.Length)
}
if ($Racine.StartsWith('\\')) { Defaut 'Partage réseau : cmd.exe ne sait pas s''y placer. Copier le dossier sur un disque local.' }

# ------------------------------------------------------------------ 2. déblocage
Titre '2. Déblocage des fichiers (marque « venu d''Internet »)'
$py = Join-Path $outils 'python\python.exe'
if ($SansDeblocage) { Info 'sauté (-SansDeblocage).' }
else {
    $t0 = Get-Date
    $liste = Join-Path ([IO.Path]::GetTempPath()) ('marques_{0}.txt' -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
    $marques = $null
    if (Test-Path -LiteralPath $py) {
        # Détection rapide par le Python de la copie (un exécutable marqué se lance quand même par un script).
        & $py -s -E -X utf8 -B (Join-Path $outils 'manifeste.py') marques $Racine --liste $liste | Out-Null
        if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $liste)) {
            $marques = @(Get-Content -LiteralPath $liste -Encoding UTF8 | Where-Object { $_ })
        }
    }
    if ($null -eq $marques) {
        # Repli : Unblock-File sur tout (environ 40 s pour 120 000 fichiers).
        Get-ChildItem -LiteralPath $Racine -Recurse -File -Force -ErrorAction SilentlyContinue | Unblock-File
        Ok ("Unblock-File passé sur tous les fichiers ({0:N0} s)." -f ((Get-Date) - $t0).TotalSeconds)
    } elseif ($marques.Count -gt 0) {
        foreach ($m in $marques) { Unblock-File -LiteralPath $m }
        Ok ("{0} fichier(s) marqué(s), débloqué(s) par Unblock-File en {1:N0} s." -f $marques.Count, ((Get-Date) - $t0).TotalSeconds)
    } else {
        Ok ("Aucun fichier marqué : rien à débloquer ({0:N0} s)." -f ((Get-Date) - $t0).TotalSeconds)
    }
}

# ------------------------------------------------------------------ 3. manifeste
Titre '3. Comparaison au manifeste (taille et SHA-256 de chaque fichier)'
$manifeste = Join-Path $outils 'manifeste_copie.json'
if (-not (Test-Path -LiteralPath $manifeste)) {
    Remarque 'Pas de manifeste (outils\manifeste_copie.json) : copie faite à la main ? Contenu non vérifié.'
} elseif (-not (Test-Path -LiteralPath $py)) {
    Defaut 'Le Python de la copie (outils\python\python.exe) est absent : copie incomplète.'
} else {
    $rapport = Join-Path ([IO.Path]::GetTempPath()) ('verifier_copie_{0}.json' -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
    $t0 = Get-Date
    $option = @()
    if ($Rapide) { $option = @('--rapide'); Info 'mode rapide : SHA-256 des binaires et des fichiers de savoir, taille pour le reste.' }
    & $py -s -E -X utf8 -B (Join-Path $outils 'manifeste.py') verifier $Racine $manifeste --rapport $rapport @option
    $code = $LASTEXITCODE
    $duree = ((Get-Date) - $t0).TotalSeconds
    if ($code -eq 0) { Ok ("Copie conforme au manifeste ({0:N0} s)." -f $duree) }
    elseif ($code -eq 1) { Defaut "Des fichiers manquent ou diffèrent (détail ci-dessus ; rapport : $rapport). Recopier." }
    else { Defaut "Vérification impossible (code $code)." }
}

# ------------------------------------------------------------------ 4. le lanceur, en diagnostic
$lignesOk = 0; $replis = @(); $manques = @()
if ($SansLanceur) { Titre '4. Demarrer-Blender.bat /verifier : sauté (-SansLanceur)' }
else {
    Titre '4. Demarrer-Blender.bat /verifier (outils de la copie, sans ouvrir Claude)'
    $bat = Join-Path $Racine 'Demarrer-Blender.bat'
    if (-not (Test-Path -LiteralPath $bat)) { Defaut 'Demarrer-Blender.bat est absent.' }
    else {
        $t0 = Get-Date
        $sortie = & (Join-Path $sys32 'cmd.exe') /d /c ('call "{0}" /verifier <nul' -f $bat) 2>&1 | ForEach-Object { "$_" }
        $code = $LASTEXITCODE
        foreach ($l in $sortie) {
            if ($l -match '^\s+\[(ok|repli|MANQUE|info)\]') {
                Write-Host "  $l"
                if ($l -match '\[ok\]') { $lignesOk++ }
                if ($l -match '\[repli\]') { $replis += $l.Trim() }
                if ($l -match '\[MANQUE\]') { $manques += $l.Trim() }
            }
        }
        Info ("code {0}, {1:N0} s ; {2} [ok], {3} [repli], {4} [MANQUE]" -f $code, ((Get-Date) - $t0).TotalSeconds,
              $lignesOk, $replis.Count, $manques.Count)
        foreach ($m in $manques) { Defaut ("Le lanceur signale un manque : " + ($m -replace '^\[MANQUE\]\s*', '')) }
        foreach ($r in $replis) { Remarque ("Outil pris sur le poste, pas dans la copie : " + ($r -replace '^\[repli\]\s*', '')) }
        if ($code -ne 0) { Defaut "Demarrer-Blender.bat /verifier rend le code $code." }
    }
}

# ------------------------------------------------------------------ 5. verdict
Write-Host ''
Write-Host '  ============================================================'
if ($defauts.Count -eq 0 -and $remarques.Count -eq 0) {
    Write-Host '     VERDICT : COPIE CONFORME, POSTE PRÊT' -ForegroundColor Green
    Write-Host '     Double-cliquer Demarrer-Blender.bat.'
    $sortieCode = 0
} elseif ($defauts.Count -eq 0) {
    Write-Host '     VERDICT : COPIE CONFORME, POSTE UTILISABLE (avec remarques)' -ForegroundColor Yellow
    foreach ($r in $remarques) { Write-Host "     - $r" }
    $sortieCode = 0
} else {
    Write-Host '     VERDICT : À CORRIGER AVANT USAGE' -ForegroundColor Red
    foreach ($d in $defauts) { Write-Host "     - $d" }
    $sortieCode = 1
}
Write-Host '     Rappel : Claude demande de se connecter une fois sur un nouveau poste.'
Write-Host '  ============================================================'
Write-Host ''
exit $sortieCode
