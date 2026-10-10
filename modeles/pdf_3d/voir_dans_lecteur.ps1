# voir_dans_lecteur.ps1 -- ouvre un PDF 3D dans un lecteur capable de 3D, CAPTURE sa fenetre, puis
# referme le lecteur qu'IL a lance. ASCII seulement (PowerShell 5.1 lit un .ps1 sans BOM en ANSI).
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File voir_dans_lecteur.ps1 `
#       -Pdf C:\...\x.pdf -Sortie C:\...\capture.png -Prevenu [-Attente 20] [-Laisser] [-Lecteur C:\...\exe]
#
# ATTENTION : CE SCRIPT OUVRE UNE FENETRE SUR LE POSTE, devant l'utilisateur, pendant toute l'attente.
# Rien, dans cet outil, ne l'appelle de lui-meme : il se lance A LA MAIN, UNE fois par fichier, et
# seulement apres avoir PREVENU l'utilisateur. D'ou l'option -Prevenu, obligatoire : sans elle le script
# refuse (code 7) et n'ouvre rien.
# (Le 2026-10-09, six ouvertures en sept minutes pendant que l'utilisateur travaillait : il a demande
# pourquoi le PDF 3D n'arretait pas de s'ouvrir. Une capture par fichier, annoncee, jamais en serie.)
#
# Le lecteur : -Lecteur, sinon la variable BM_LECTEUR_PDF3D, sinon PDF-XChange Editor cherche dans
# le registre (App Paths) puis dans les dossiers d'installation habituels. Aucun chemin n'est
# impose : sur un poste sans lecteur 3D, le script sort avec le code 3 et le dit.
#
# CE QUE LA CAPTURE PROUVE : ce que la fenetre montrait a cet instant. Le script ne clique sur
# rien : si le lecteur attend un clic (bandeau de securite, activation du contenu 3D), l'image le
# montre et c'est a un humain de cliquer.
#
# Codes de sortie : 0 capture ecrite ; 2 PDF absent ; 3 lecteur introuvable ; 4 un lecteur du
# meme nom tournait deja (on ne touche pas a la session de quelqu'un : fermez-le ou passez -Forcer) ;
# 5 pas de fenetre. 7 option -Prevenu absente (rien n'est ouvert). 6 le lecteur s'est referme avant la capture (son code de sortie est donne).
param(
  [Parameter(Mandatory = $true)][string]$Pdf,
  [Parameter(Mandatory = $true)][string]$Sortie,
  [int]$Attente = 20,
  [string]$Lecteur = "",
  [switch]$Laisser,
  [switch]$Prevenu,
  [switch]$Forcer,
  [switch]$Ecran
)
$ErrorActionPreference = "Stop"

function Trouver-Lecteur {
  param([string]$Demande)
  if ($Demande -and (Test-Path -LiteralPath $Demande)) { return (Resolve-Path -LiteralPath $Demande).Path }
  if ($env:BM_LECTEUR_PDF3D -and (Test-Path -LiteralPath $env:BM_LECTEUR_PDF3D)) { return $env:BM_LECTEUR_PDF3D }
  foreach ($nom in @("PXCEditor.exe", "PDFXEdit.exe")) {
    foreach ($racine in @("HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths",
                          "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths")) {
      $cle = Join-Path $racine $nom
      if (Test-Path $cle) {
        $v = (Get-ItemProperty -Path $cle)."(default)"
        if ($v) { $v = $v.Trim('"'); if (Test-Path -LiteralPath $v) { return $v } }
      }
    }
  }
  $bases = @($env:ProgramFiles, ${env:ProgramFiles(x86)}) | Where-Object { $_ }
  foreach ($b in $bases) {
    foreach ($rel in @("PDF-XChange\PDF Editor\PXCEditor.exe",
                       "Tracker Software\PDF Editor\PDFXEdit.exe",
                       "Tracker Software\PDF Editor\PXCEditor.exe")) {
      $c = Join-Path $b $rel
      if (Test-Path -LiteralPath $c) { return $c }
    }
  }
  return $null
}

if (-not $Prevenu) {
  Write-Output "REFUS : ce script ouvre une fenetre de lecteur PDF sur le poste. Prevenez l'utilisateur, puis relancez avec -Prevenu. Rien n'a ete ouvert."
  exit 7
}
if (-not (Test-Path -LiteralPath $Pdf)) { Write-Output ("PDF absent : {0}" -f $Pdf); exit 2 }
$Pdf = (Resolve-Path -LiteralPath $Pdf).Path
$exe = Trouver-Lecteur -Demande $Lecteur
if (-not $exe) {
  Write-Output "LECTEUR INTROUVABLE : ni -Lecteur, ni BM_LECTEUR_PDF3D, ni PDF-XChange Editor installe."
  exit 3
}
$nomProc = [IO.Path]::GetFileNameWithoutExtension($exe)
$deja = @(Get-Process -Name $nomProc -ErrorAction SilentlyContinue)
if ($deja.Count -gt 0 -and -not $Forcer) {
  Write-Output ("{0} tourne deja (PID {1}) : je n'y touche pas. Fermez-le, ou relancez avec -Forcer (le PDF s'ouvrira alors dans cette session-la et ne sera PAS referme)." -f $nomProc, (($deja | ForEach-Object { $_.Id }) -join ", "))
  exit 4
}

Add-Type -AssemblyName System.Drawing
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class FenetreP3D {
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr hwnd, IntPtr hdc, uint flags);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hwnd, out RECT r);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr hwnd);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hwnd, int cmd);
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
}
"@
[void][FenetreP3D]::SetProcessDPIAware()

$avant = @(Get-Process -Name $nomProc -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
$p = Start-Process -FilePath $exe -ArgumentList ('"{0}"' -f $Pdf) -PassThru
$null = $p.Handle    # garder la poignee : sans elle, le code de sortie du processus est perdu
Write-Output ("lecteur : {0}" -f $exe)
Write-Output ("lance   : PID {0}, attente {1} s" -f $p.Id, $Attente)

# la fenetre principale peut appartenir a un processus fils du meme nom
$h = [IntPtr]::Zero
$fin = (Get-Date).AddSeconds([Math]::Max(5, $Attente))
$proc = $null
$debut = Get-Date
$vu = $false
while ((Get-Date) -lt $fin) {
  Start-Sleep -Milliseconds 500
  $cands = @(Get-Process -Name $nomProc -ErrorAction SilentlyContinue | Where-Object { $avant -notcontains $_.Id -or $Forcer })
  foreach ($c in $cands) {
    $c.Refresh()
    if ($c.MainWindowHandle -ne [IntPtr]::Zero) { $h = $c.MainWindowHandle; $proc = $c; $vu = $true }
  }
  # le lecteur lance s'est-il referme tout seul (ou a-t-il ete ferme par quelqu'un) avant la capture ?
  if ($vu -and $cands.Count -eq 0) {
    $code = '?'
    try { $p.Refresh(); if ($p.HasExited) { $code = ('0x{0:X}' -f $p.ExitCode) } } catch {}
    Write-Output ("LE LECTEUR S'EST FERME AVANT LA CAPTURE, au bout de {0:N0} s (code de sortie {1} ; 0x0 = fermeture normale, par quelqu'un ou par lui-meme ; autre = plantage). Aucune capture." -f ((Get-Date) - $debut).TotalSeconds, $code)
    exit 6
  }
  # on attend TOUTE la duree demandee, fenetre trouvee ou non : le lecteur doit avoir le temps
  # de lire le modele et de le dessiner avant la capture
}
if ($h -eq [IntPtr]::Zero) {
  Write-Output "PAS DE FENETRE apres l'attente."
  if (-not $Laisser) { Get-Process -Name $nomProc -ErrorAction SilentlyContinue | Where-Object { $avant -notcontains $_.Id } | Stop-Process -Force -ErrorAction SilentlyContinue }
  exit 5
}
if ([FenetreP3D]::IsIconic($h)) { [void][FenetreP3D]::ShowWindow($h, 9); Start-Sleep -Seconds 2 }

$r = New-Object FenetreP3D+RECT
[void][FenetreP3D]::GetWindowRect($h, [ref]$r)
$w = [Math]::Max(1, $r.R - $r.L); $ht = [Math]::Max(1, $r.B - $r.T)
$titre = $proc.MainWindowTitle
Write-Output ("fenetre : {0} x {1} a ({2},{3}) ; titre : {4}" -f $w, $ht, $r.L, $r.T, $titre)

$dossier = Split-Path -Parent $Sortie
if ($dossier -and -not (Test-Path -LiteralPath $dossier)) { New-Item -ItemType Directory -Force -Path $dossier | Out-Null }

# 1) PrintWindow avec PW_RENDERFULLCONTENT (2) : rend aussi les surfaces composees par le GPU
$bmp = New-Object System.Drawing.Bitmap $w, $ht
$g = [System.Drawing.Graphics]::FromImage($bmp)
$hdc = $g.GetHdc()
$ok = [FenetreP3D]::PrintWindow($h, $hdc, 2)
$g.ReleaseHdc($hdc)
$g.Dispose()
$bmp.Save($Sortie, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
Write-Output ("capture (PrintWindow, rendu complet = {0}) : {1}" -f $ok, $Sortie)

# 2) sur demande, la meme zone copiee de l'ECRAN (la fenetre doit etre visible et au premier plan)
if ($Ecran) {
  $s2 = [IO.Path]::ChangeExtension($Sortie, $null).TrimEnd('.') + "_ecran.png"
  $bmp2 = New-Object System.Drawing.Bitmap $w, $ht
  $g2 = [System.Drawing.Graphics]::FromImage($bmp2)
  $g2.CopyFromScreen($r.L, $r.T, 0, 0, (New-Object System.Drawing.Size $w, $ht))
  $g2.Dispose()
  $bmp2.Save($s2, [System.Drawing.Imaging.ImageFormat]::Png)
  $bmp2.Dispose()
  Write-Output ("capture (ecran) : {0}" -f $s2)
}

if ($Laisser) {
  Write-Output "lecteur laisse ouvert (-Laisser)."
} else {
  $miens = @(Get-Process -Name $nomProc -ErrorAction SilentlyContinue | Where-Object { $avant -notcontains $_.Id })
  foreach ($m in $miens) { Stop-Process -Id $m.Id -Force -ErrorAction SilentlyContinue }
  Write-Output ("lecteur referme : {0} processus arrete(s) (ceux lances par ce script seulement)." -f $miens.Count)
}
exit 0
