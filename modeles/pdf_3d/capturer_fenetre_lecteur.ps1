# capturer_fenetre_lecteur.ps1 -- CAPTURE la fenetre d'un lecteur PDF DEJA OUVERT, sans rien lancer,
# sans rien fermer, sans clic ni mise au premier plan. ASCII seulement (PowerShell 5.1).
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File capturer_fenetre_lecteur.ps1 `
#       -Sortie C:\...\capture.png [-Nom PXCEditor] [-Ecran]
#
# A employer quand le lecteur tourne deja dans la session de quelqu'un (voir_dans_lecteur.ps1 refuse
# alors de demarrer, code 4) : on regarde ce que SA fenetre montre, on n'y touche pas.
# Une fenetre reduite dans la barre des taches n'est PAS restauree : le script le dit (code 6).
# Codes : 0 capture ecrite ; 5 aucun lecteur ouvert ou pas de fenetre ; 6 fenetre reduite.
param(
  [Parameter(Mandatory = $true)][string]$Sortie,
  [string]$Nom = "PXCEditor",
  [switch]$Ecran
)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class FenetreP3DLecture {
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr hwnd, IntPtr hdc, uint flags);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hwnd, out RECT r);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr hwnd);
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
}
"@
[void][FenetreP3DLecture]::SetProcessDPIAware()

$procs = @(Get-Process -Name $Nom -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne [IntPtr]::Zero })
if ($procs.Count -eq 0) { Write-Output ("aucune fenetre de {0} ouverte." -f $Nom); exit 5 }
$p = $procs[0]
$h = $p.MainWindowHandle
Write-Output ("fenetre de {0} PID {1}, demarre a {2:HH:mm:ss} ; titre : {3}" -f $p.ProcessName, $p.Id, $p.StartTime, $p.MainWindowTitle)
if ([FenetreP3DLecture]::IsIconic($h)) { Write-Output "fenetre REDUITE dans la barre des taches : je ne la restaure pas."; exit 6 }

$r = New-Object FenetreP3DLecture+RECT
[void][FenetreP3DLecture]::GetWindowRect($h, [ref]$r)
$w = [Math]::Max(1, $r.R - $r.L); $ht = [Math]::Max(1, $r.B - $r.T)
$dossier = Split-Path -Parent $Sortie
if ($dossier -and -not (Test-Path -LiteralPath $dossier)) { New-Item -ItemType Directory -Force -Path $dossier | Out-Null }
$bmp = New-Object System.Drawing.Bitmap $w, $ht
$g = [System.Drawing.Graphics]::FromImage($bmp)
$hdc = $g.GetHdc()
$ok = [FenetreP3DLecture]::PrintWindow($h, $hdc, 2)
$g.ReleaseHdc($hdc)
$g.Dispose()
$bmp.Save($Sortie, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
Write-Output ("capture {0} x {1} (PrintWindow, rendu complet = {2}) : {3}" -f $w, $ht, $ok, $Sortie)
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
exit 0
