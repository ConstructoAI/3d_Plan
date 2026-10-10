#Requires -Version 3
<#
.SYNOPSIS
  outils\chemins.ps1 - chemins des outils du poste Blender (dossier AUTONOME).

.DESCRIPTION
  Pose BM_RACINE et les BM_* de la session, et met en TETE du PATH le dossier de
  Python, celui de Node et celui d'ODA File Converter (ezdxf le cherche d'abord dans
  le PATH). Jamais le Scripts du Python portable : ses lanceurs .exe visent l'ancien
  Python ; on passe par python -m pip. Pour les copies PORTABLES, applique les consignes
  verifiees des agents (outils\*\PRET.txt) : PYTHONNOUSERSITE=1 sans PYTHONHOME ni
  PYTHONPATH ; BLENDER_SYSTEM_RESOURCES et CUDA_CACHE_PATH sans BLENDER_USER_* ni
  BLENDER_SYSTEM_* ; sans QT_PLUGIN_PATH ni QT_QPA_PLATFORM_PLUGIN_PATH (ODA) ; sans
  NODE_OPTIONS ni NODE_PATH ; et npm_config_update_notifier=false pour tout Node.

  Ordre de resolution de chaque outil (meme logique que outils\chemins.py) :
    1. la variable BM_* posee A LA MAIN (BM_PYTHON, BM_BLENDER, ...) ;
    2. la copie PORTABLE sous outils\ ;
    3. l'installation du SYSTEME (repli, pour que tout marche pendant la migration) ;
    4. sinon la variable reste vide et BM_ORIGINE_<X> vaut "absent".

  BM_RACINE est TOUJOURS le dossier parent de ce fichier : le dossier se colle
  n'importe ou (D:\, un autre nom, un autre poste). Une BM_* posee par une session
  precedente (BM_ORIGINE_<X> = portable, systeme ou absent) est recalculee : un
  dossier deplace ne garde pas les chemins de son ancienne place.

  Variables posees :
    BM_RACINE, BM_PYTHON, BM_BLENDER, BM_ODA_CONVERTISSEUR, BM_ODA_VISIONNEUSE,
    BM_NODE, BM_NAVIGATEUR, BM_POSTGRES, BM_GIT_BASH, BM_GH, BM_PROJET ; et
    BM_ORIGINE_<X> pour chacun : portable, systeme, variable ou absent (projet :
    fichier, recent, recent-fichier-invalide ou absent).
    BM_POSTGRES est le DOSSIER bin de PostgreSQL 18 (version visee : celle du cluster
    du programme Metre). BM_GIT_BASH est le bash.exe de Git for Windows (jamais celui
    de System32, qui est WSL) ; CLAUDE_CODE_GIT_BASH_PATH le recopie pour Claude Code.
    PATH : apres Python, Node et ODA, le dossier cmd de Git et celui de gh. Jamais
    PostgreSQL (ses DLL ne doivent passer devant personne), ni bin ou usr\bin de Git.

  Fichier sans accents : PowerShell 5.1 lit un .ps1 sans BOM en ANSI.

.PARAMETER Sortie
  session : pose les variables dans la session courante (dot-source) - defaut ;
  cmd     : ecrit des lignes NOM=valeur (lues par chemins.cmd), sans rien poser ;
  texte   : affiche un tableau, sans rien poser.

.PARAMETER Versions
  Ajoute _BM_V_<X> (version lue dans chaque .exe, sans le lancer) et
  _BM_V_EZDXF (version d'ezdxf dans le Python trouve, ou ABSENT).

.EXAMPLE
  . "C:\...\blender-main\outils\chemins.ps1"
  Dans une fenetre PowerShell : pose les variables pour cette fenetre.
  Si les scripts sont bloques : Set-ExecutionPolicy -Scope Process Bypass -Force

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File outils\chemins.ps1 -Sortie texte
#>
[CmdletBinding()]
param(
  [ValidateSet('session', 'cmd', 'texte')]
  [string]$Sortie = 'session',
  [switch]$Versions
)

& {
  param([string]$Sortie, [bool]$AvecVersions, [string]$Ici)

  # ------------------------------------------------------------------ petits outils
  function Get-Val([string]$nom) {
    $v = [Environment]::GetEnvironmentVariable($nom, 'Process')
    if ($null -eq $v) { return '' }
    return $v.Trim().Trim('"')
  }
  function Test-Fichier([string]$p) {
    if ([string]::IsNullOrWhiteSpace($p)) { return $false }
    try { return [IO.File]::Exists($p) } catch { return $false }
  }
  function Test-Dossier([string]$p) {
    if ([string]::IsNullOrWhiteSpace($p)) { return $false }
    try { return [IO.Directory]::Exists($p) } catch { return $false }
  }
  function Get-Plein([string]$p) { return [IO.Path]::GetFullPath($p) }
  function Get-Cle([string]$p) {
    return (Get-Plein $p).Replace('/', '\').TrimEnd('\').ToLowerInvariant()
  }
  function Test-Sous([string]$chemin, [string]$dossier) {
    if (-not $chemin -or -not $dossier) { return $false }
    $c = Get-Cle $chemin; $d = Get-Cle $dossier
    return ($c -eq $d -or $c.StartsWith($d + '\'))
  }
  function Write-Alerte([string]$msg) {
    if ($Sortie -eq 'session') { Write-Warning $msg } else { [Console]::Error.WriteLine('  [attention] ' + $msg) }
  }
  function Get-VersionNom([string]$nom, [string]$prefixe) {
    $suite = $nom
    if ($prefixe -and $nom.ToLowerInvariant().StartsWith($prefixe.ToLowerInvariant())) { $suite = $nom.Substring($prefixe.Length) }
    $m = [regex]::Match($suite, '\d+(\.\d+)*')
    if (-not $m.Success) { return ,@() }
    $t = $m.Value
    if ($prefixe -ieq 'Python' -and $t -notmatch '\.' -and $t.Length -ge 2) {
      return ,@([long]$t.Substring(0, 1), [long]$t.Substring(1))
    }
    return ,@($t.Split('.') | ForEach-Object { [long]$_ })
  }
  # Cle de tri (decroissant) : version visee d'abord, puis la plus recente, le 64 bits
  # avant le 32 bits (-32), puis l'ordre de decouverte. Meme regle que _cle_tri (py).
  function Get-CleTri($version, $visee, [string]$nom, [int]$index) {
    $v4 = @(0, 0, 0, 0)
    for ($i = 0; $i -lt [Math]::Min(4, $version.Count); $i++) { $v4[$i] = $version[$i] }
    $vise = 0
    if ($visee -and $version.Count -ge $visee.Count) {
      $vise = 1
      for ($i = 0; $i -lt $visee.Count; $i++) { if ($version[$i] -ne $visee[$i]) { $vise = 0 } }
    }
    $n64 = 1; if ($nom.ToLowerInvariant().EndsWith('-32')) { $n64 = 0 }
    return ('{0}|{1:D9}.{2:D9}.{3:D9}.{4:D9}|{5}|{6:D9}' -f $vise, $v4[0], $v4[1], $v4[2], $v4[3], $n64, (999999999 - $index))
  }
  function Find-DansPath([string]$exe) {
    foreach ($d in (Get-Val 'PATH').Split(';')) {
      $d = $d.Trim().Trim('"')
      if (-not $d) { continue }
      if ($d.Replace('/', '\') -match '(^|\\)windowsapps(\\|$)') { continue }
      $p = Join-Path $d $exe
      if (Test-Fichier $p) { return (Get-Plein $p) }
    }
    return $null
  }
  function Find-Versionne($motifs, [string]$exe, [string]$prefixe, $visee) {
    $cands = New-Object System.Collections.ArrayList
    $vues = @{}
    $index = 0
    foreach ($m in $motifs) {
      $base = Get-Val $m[0]
      if (-not $base) { continue }
      $dossier = $base
      if ($m[1]) { $dossier = Join-Path $base $m[1] }
      $k = (Get-Cle $dossier) + '|' + $m[2].ToLowerInvariant()
      if ($vues.ContainsKey($k)) { continue }
      $vues[$k] = $true
      if (-not (Test-Dossier $dossier)) { continue }
      $dirs = @(Get-ChildItem -LiteralPath $dossier -Directory -Force -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -like $m[2] } | Sort-Object { $_.Name.ToLowerInvariant() })
      foreach ($d in $dirs) {
        $p = Join-Path $d.FullName $exe
        if (Test-Fichier $p) {
          $cle = Get-CleTri (Get-VersionNom $d.Name $prefixe) $visee $d.Name $index
          [void]$cands.Add((New-Object PSObject -Property @{ Chemin = (Get-Plein $p); Cle = $cle }))
        }
        $index++
      }
    }
    if ($cands.Count -eq 0) { return $null }
    return ($cands | Sort-Object Cle -Descending | Select-Object -First 1).Chemin
  }
  function Find-Fixes($fixes) {
    foreach ($f in $fixes) {
      $base = Get-Val $f[0]
      if ($base) {
        $p = Join-Path $base $f[1]
        if (Test-Fichier $p) { return (Get-Plein $p) }
      }
    }
    return $null
  }
  # bash.exe du Git dont le git.exe est dans le PATH (<Git>\cmd, bin ou mingw64\bin).
  function Find-BashDuGit {
    $g = Find-DansPath 'git.exe'
    if (-not $g) { return $null }
    $d = Split-Path -Parent $g
    $p1 = Split-Path -Parent $d
    $cands = @()
    if ($p1) { $cands += (Join-Path $p1 'bin\bash.exe'); $p2 = Split-Path -Parent $p1; if ($p2) { $cands += (Join-Path $p2 'bin\bash.exe') } }
    foreach ($c in $cands) { if (Test-Fichier $c) { return (Get-Plein $c) } }
    return $null
  }
  # Variable posee a la main qui designe un DOSSIER (PostgreSQL, Git) : le dossier de
  # l'executable ou la racine de l'outil ; pour PostgreSQL, aussi un autre .exe de bin.
  # Meme regle que _exe_du_dossier (py).
  function Get-ExeDuDossier([string]$valeur, $def) {
    $nom = Split-Path -Leaf $def.Exe
    if (Test-Dossier $valeur) {
      foreach ($c in @((Join-Path $valeur $nom), (Join-Path $valeur $def.Exe))) { if (Test-Fichier $c) { return $c } }
      return (Join-Path $valeur $nom)
    }
    if ($def.Dossier -and (Test-Fichier $valeur) -and ((Split-Path -Leaf $valeur) -ine $nom)) {
      $c = Join-Path (Split-Path -Parent $valeur) $nom
      if (Test-Fichier $c) { return $c }
    }
    return $valeur
  }
  function Find-Portable([string]$outils, $def) {
    if (-not $def.Portable) { return $null }
    $base = Join-Path $outils $def.Portable
    $p = Join-Path $base $def.Exe
    if (Test-Fichier $p) { return (Get-Plein $p) }
    if (Test-Dossier $base) {
      $sous = @(Get-ChildItem -LiteralPath $base -Directory -Force -ErrorAction SilentlyContinue |
                Sort-Object { $_.Name.ToLowerInvariant() })
      foreach ($s in $sous) {
        $q = Join-Path $s.FullName $def.Exe
        if (Test-Fichier $q) { return (Get-Plein $q) }
      }
    }
    return $null
  }

  # ------------------------------------------------------------------ definitions
  $pf = @('ProgramW6432', 'ProgramFiles', 'ProgramFiles(x86)')
  $edge = @(@('ProgramFiles(x86)', 'Microsoft\Edge\Application\msedge.exe'),
            @('ProgramW6432', 'Microsoft\Edge\Application\msedge.exe'),
            @('ProgramFiles', 'Microsoft\Edge\Application\msedge.exe'),
            @('LOCALAPPDATA', 'Microsoft\Edge\Application\msedge.exe'))
  $chrome = @(@('ProgramW6432', 'Google\Chrome\Application\chrome.exe'),
              @('ProgramFiles', 'Google\Chrome\Application\chrome.exe'),
              @('ProgramFiles(x86)', 'Google\Chrome\Application\chrome.exe'),
              @('LOCALAPPDATA', 'Google\Chrome\Application\chrome.exe'))
  $defs = @(
    @{ Cle = 'PYTHON'; Portable = 'python'; Exe = 'python.exe'; Prefixe = 'Python'; Visee = @(3, 13)
       Motifs = @(,@('LOCALAPPDATA', 'Programs\Python', 'Python3*')) + @($pf | ForEach-Object { ,@($_, '', 'Python3*') })
       Fixes = @(); Path = @('python.exe') },
    @{ Cle = 'BLENDER'; Portable = 'blender'; Exe = 'blender.exe'; Prefixe = 'Blender'; Visee = @(5, 2)
       Motifs = @($pf | ForEach-Object { ,@($_, 'Blender Foundation', 'Blender*') })
       Fixes = @(); Path = @('blender.exe') },
    @{ Cle = 'ODA_CONVERTISSEUR'; Portable = 'oda\convertisseur'; Exe = 'ODAFileConverter.exe'; Prefixe = 'ODAFileConverter'; Visee = $null
       Motifs = @($pf | ForEach-Object { ,@($_, 'ODA', 'ODAFileConverter*') })
       Fixes = @(); Path = @('ODAFileConverter.exe') },
    @{ Cle = 'ODA_VISIONNEUSE'; Portable = 'oda\visionneuse'; Exe = 'ODAViewer.exe'; Prefixe = 'ODA Viewer'; Visee = $null
       Motifs = @($pf | ForEach-Object { ,@($_, 'ODA', 'ODA Viewer*') })
       Fixes = @(); Path = @('ODAViewer.exe') },
    @{ Cle = 'NODE'; Portable = 'node'; Exe = 'node.exe'; Prefixe = ''; Visee = $null
       Motifs = @(); Fixes = @($pf | ForEach-Object { ,@($_, 'nodejs\node.exe') }); Path = @('node.exe') },
    @{ Cle = 'NAVIGATEUR'; Portable = $null; Exe = $null; Prefixe = ''; Visee = $null
       Motifs = @(); Fixes = @(); Path = @() },
    @{ Cle = 'POSTGRES'; Portable = 'postgresql'; Exe = 'bin\pg_ctl.exe'; Prefixe = ''; Visee = @(18)
       Motifs = @($pf | ForEach-Object { ,@($_, 'PostgreSQL', '*') }); Fixes = @(); Path = @('pg_ctl.exe')
       Dossier = $true; VariableDossier = $true },
    @{ Cle = 'GIT_BASH'; Portable = 'git'; Exe = 'bin\bash.exe'; Prefixe = ''; Visee = $null
       Motifs = @(); Fixes = @(@($pf | ForEach-Object { ,@($_, 'Git\bin\bash.exe') }) + @(,@('LOCALAPPDATA', 'Programs\Git\bin\bash.exe')))
       Path = @(); GitDuPath = $true; VariableDossier = $true },
    @{ Cle = 'GH'; Portable = 'gh'; Exe = 'gh.exe'; Prefixe = ''; Visee = $null
       Motifs = @(); Fixes = @($pf | ForEach-Object { ,@($_, 'GitHub CLI\gh.exe') }); Path = @('gh.exe') }
  )

  # ------------------------------------------------------------------ resolution
  $racine = Split-Path -Parent $Ici
  if (-not $racine) { $racine = $Ici }
  $racine = Get-Plein $racine
  $outils = Join-Path $racine 'outils'

  function Resolve-Outil($def) {
    $var = 'BM_' + $def.Cle
    $valeur = Get-Val $var
    $auto = Get-Val ('BM_ORIGINE_' + $def.Cle)
    if ($valeur -and $auto -and $auto -ne 'variable') { $valeur = '' }  # posee par une session precedente
    $prefere = ''
    $motCle = $false
    if ($def.Cle -eq 'NAVIGATEUR' -and ($valeur -ieq 'edge' -or $valeur -ieq 'chrome')) {
      $prefere = $valeur.ToLowerInvariant(); $valeur = ''; $motCle = $true
    }
    if ($valeur -and $def.VariableDossier) { $valeur = Get-ExeDuDossier $valeur $def }
    if ($valeur) {
      if (Test-Fichier $valeur) {
        $p = Get-Plein $valeur
        if (Test-Sous $p $racine) { return @($p, 'portable') }
        return @($p, 'variable')
      }
      Write-Alerte ("{0} pointe vers '{1}', introuvable : variable ignoree." -f $var, $valeur)
    }
    $p = Find-Portable $outils $def
    if ($p) { return @($p, 'portable') }
    if ($def.Cle -eq 'NAVIGATEUR') {
      $listes = @($edge, $chrome)
      if ($prefere -eq 'chrome') { $listes = @($chrome, $edge) }
      foreach ($l in $listes) {
        $p = Find-Fixes $l
        if ($p) { if ($motCle) { return @($p, 'variable') } else { return @($p, 'systeme') } }
      }
      return @('', 'absent')
    }
    $p = $null
    if ($def.Motifs.Count -gt 0) { $p = Find-Versionne $def.Motifs $def.Exe $def.Prefixe $def.Visee }
    if (-not $p -and $def.Fixes.Count -gt 0) { $p = Find-Fixes $def.Fixes }
    if (-not $p) { foreach ($e in $def.Path) { $p = Find-DansPath $e; if ($p) { break } } }
    if (-not $p -and $def.GitDuPath) { $p = Find-BashDuGit }
    if ($p) { return @($p, 'systeme') }
    return @('', 'absent')
  }

  function Find-Projet {
    $fichier = Join-Path $outils 'projet_en_cours.txt'
    $invalide = $false
    if (Test-Fichier $fichier) {
      $valeur = ''
      try {
        foreach ($l in [IO.File]::ReadAllLines($fichier, [Text.Encoding]::UTF8)) {
          $l = $l.Trim().Trim('"')
          if ($l -and -not $l.StartsWith('#')) { $valeur = $l; break }
        }
      } catch { $valeur = '' }
      if ($valeur) {
        # Combine : un chemin absolu l'emporte, comme os.path.join en Python.
        $p = Get-Plein ([IO.Path]::Combine($racine, $valeur))
        if (Test-Dossier $p) { return @($p.TrimEnd('\'), 'fichier') }
      }
      $invalide = $true
    }
    $parent = Split-Path -Parent $racine
    if (-not $parent) { $parent = $racine }
    $meilleur = $null
    foreach ($d in @(Get-ChildItem -LiteralPath $parent -Directory -Force -ErrorAction SilentlyContinue)) {
      if ((Get-Cle $d.FullName) -eq (Get-Cle $racine)) { continue }
      foreach ($f in @(Get-ChildItem -LiteralPath $d.FullName -File -Force -Filter 'parametres_*.py' -ErrorAction SilentlyContinue |
                       Where-Object { $_.Name -like 'parametres_*.py' })) {
        $t = $f.LastWriteTimeUtc.Ticks
        if ($null -eq $meilleur -or $t -gt $meilleur[0] -or ($t -eq $meilleur[0] -and $d.FullName.ToLowerInvariant() -lt $meilleur[1].ToLowerInvariant())) {
          $meilleur = @($t, $d.FullName)
        }
      }
    }
    if ($meilleur) {
      $o = 'recent'; if ($invalide) { $o = 'recent-fichier-invalide' }
      return @((Get-Plein $meilleur[1]), $o)
    }
    return @('', 'absent')
  }

  function Get-VersionExe([string]$p) {
    if (-not (Test-Fichier $p)) { return '' }
    try {
      $vi = (Get-Item -LiteralPath $p -Force).VersionInfo
      $v = $vi.ProductVersion
      if (-not $v) { $v = $vi.FileVersion }
      if (-not $v) { return '' }
      $v = ($v.Split([char]0)[0]).Trim()
      return ($v -replace '^(\d+\.\d+\.\d+)\.0$', '$1')
    } catch { return '' }
  }
  function Get-VersionEzdxf([string]$py, [bool]$strict) {
    try {
      $psi = New-Object Diagnostics.ProcessStartInfo
      $psi.FileName = $py
      $a = '-c "import ezdxf,sys;sys.stdout.write(ezdxf.__version__)"'
      if ($strict) { $a = '-E -s ' + $a }
      $psi.Arguments = $a
      $psi.UseShellExecute = $false
      $psi.RedirectStandardOutput = $true
      $psi.RedirectStandardError = $true
      $psi.CreateNoWindow = $true
      $proc = [Diagnostics.Process]::Start($psi)
      $errTache = $proc.StandardError.ReadToEndAsync()
      $out = $proc.StandardOutput.ReadToEnd()
      if (-not $proc.WaitForExit(120000)) { try { $proc.Kill() } catch { }; return 'ABSENT' }
      [void]$errTache.Wait(5000)
      $out = $out.Trim()
      if ($proc.ExitCode -eq 0 -and $out -match '^\d') { return $out }
      return 'ABSENT'
    } catch { return 'ABSENT' }
  }

  $vars = New-Object System.Collections.Specialized.OrderedDictionary
  $vars['BM_RACINE'] = $racine.TrimEnd('\')
  if ($vars['BM_RACINE'] -match '^[A-Za-z]:$') { $vars['BM_RACINE'] = $racine }
  foreach ($def in $defs) {
    $r = Resolve-Outil $def
    $v = $r[0]
    if ($v -and $def.Dossier) { $v = Split-Path -Parent $v }   # PostgreSQL : le dossier bin
    $vars['BM_' + $def.Cle] = $v
    $vars['BM_ORIGINE_' + $def.Cle] = $r[1]
  }
  $pr = Find-Projet
  $vars['BM_PROJET'] = $pr[0]
  $vars['BM_ORIGINE_PROJET'] = $pr[1]

  # Blender PORTABLE (consignes verifiees par l'agent B, outils\blender\PRET.txt) :
  # - les BLENDER_USER_* et BLENDER_SYSTEM_* heritees primeraient sur outils\blender\portable ;
  # - BLENDER_SYSTEM_RESOURCES : sinon un C:\ProgramData\Blender Foundation\Blender\<v> d'un
  #   autre poste passerait avant les scripts et le Python embarques ;
  # - CUDA_CACHE_PATH : sinon le pilote NVIDIA ecrit dans %APPDATA%\NVIDIA\ComputeCache.
  # Rien de tout cela pour un Blender du systeme ou designe a la main.
  # Autres copies portables (consignes des agents A et C, outils\python\PRET.txt, outils\oda\PRET.txt,
  # outils\node\PRET.txt) - meme regle que _env_portables dans chemins.py :
  # - Python : PYTHONNOUSERSITE=1, sans PYTHONHOME ni PYTHONPATH herites ;
  # - ODA : sans QT_PLUGIN_PATH ni QT_QPA_PLATFORM_PLUGIN_PATH herites ;
  # - Node : sans NODE_OPTIONS ni NODE_PATH herites ; et, pour tout Node trouve,
  #   npm_config_update_notifier=false (sinon la 1re commande npm d'un profil neuf bloque ~45 s).
  $env0 = [Environment]::GetEnvironmentVariables('Process')
  $definies = @{}
  foreach ($k in $env0.Keys) { if ($env0[$k]) { $definies[$k.ToUpperInvariant()] = $true } }
  if ($vars['BM_ORIGINE_PYTHON'] -eq 'portable') {
    foreach ($k in @('PYTHONHOME', 'PYTHONPATH')) { if ($definies.ContainsKey($k)) { $vars[$k] = '' } }
    $vars['PYTHONNOUSERSITE'] = '1'
  }
  if ($vars['BM_ORIGINE_BLENDER'] -eq 'portable') {
    $heritees = @($env0.Keys | ForEach-Object { $_.ToUpperInvariant() } |
                  Where-Object { $_ -match '^BLENDER_(USER|SYSTEM)_' } | Sort-Object)
    foreach ($k in $heritees) { $vars[$k] = '' }
    $dirB = Split-Path -Parent $vars['BM_BLENDER']
    $verDir = @(Get-ChildItem -LiteralPath $dirB -Directory -Force -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -match '^\d+\.\d+$' } |
                Sort-Object { [version]$_.Name } -Descending) | Select-Object -First 1
    if ($verDir) { $vars['BLENDER_SYSTEM_RESOURCES'] = (Get-Plein $verDir.FullName) }
    $vars['CUDA_CACHE_PATH'] = Join-Path (Join-Path $dirB 'portable') 'cuda_cache'
  }
  if ($vars['BM_ORIGINE_ODA_CONVERTISSEUR'] -eq 'portable' -or $vars['BM_ORIGINE_ODA_VISIONNEUSE'] -eq 'portable') {
    foreach ($k in @('QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH')) { if ($definies.ContainsKey($k)) { $vars[$k] = '' } }
  }
  if ($vars['BM_ORIGINE_NODE'] -eq 'portable') {
    foreach ($k in @('NODE_OPTIONS', 'NODE_PATH')) { if ($definies.ContainsKey($k)) { $vars[$k] = '' } }
  }
  if ($vars['BM_NODE'] -and -not $definies.ContainsKey('NPM_CONFIG_UPDATE_NOTIFIER')) {
    $vars['npm_config_update_notifier'] = 'false'
  }
  # Claude Code trouve Git Bash par cette variable : le Git retenu (BM_GIT_BASH a priorite).
  if ($vars['BM_GIT_BASH']) { $vars['CLAUDE_CODE_GIT_BASH_PATH'] = $vars['BM_GIT_BASH'] }
  # Zero trace : la configuration de Claude Code dans outils\claude\config, s'il existe.
  # BM_CLAUDE_CONFIG=profil : retour au profil de l'utilisateur ; un dossier : celui-la.
  # Meme regle que _config_claude (py).
  $bmc = Get-Val 'BM_CLAUDE_CONFIG'
  if ($bmc -ieq 'profil') {
    if ($definies.ContainsKey('CLAUDE_CONFIG_DIR')) { $vars['CLAUDE_CONFIG_DIR'] = '' }
  } elseif ($bmc) {
    $vars['CLAUDE_CONFIG_DIR'] = (Get-Plein $bmc)
  } else {
    $cc = Join-Path $outils 'claude\config'
    if (Test-Dossier $cc) { $vars['CLAUDE_CONFIG_DIR'] = $cc }
  }

  # PATH : Python, Node et ODA en tete ; l'ancien PATH ensuite, sans ces dossiers.
  # PAS le Scripts du Python portable (decision du chef) : ses lanceurs pip.exe, pytest.exe...
  # visent l'ANCIEN Python (agent A). Il est meme retire de l'ancien PATH : python -m pip.
  function Get-ClePath([string]$p) { return $p.Trim().Trim('"').Replace('/', '\').TrimEnd('\').ToLowerInvariant() }
  $tete = New-Object System.Collections.ArrayList
  $exclus = @{}
  if ($vars['BM_PYTHON']) {
    $d = Split-Path -Parent $vars['BM_PYTHON']
    [void]$tete.Add($d)
    if ($vars['BM_ORIGINE_PYTHON'] -eq 'portable') { $exclus[(Get-ClePath (Join-Path $d 'Scripts'))] = $true }
  }
  if ($vars['BM_NODE']) { [void]$tete.Add((Split-Path -Parent $vars['BM_NODE'])) }
  # ezdxf essaie shutil.which("ODAFileConverter") AVANT win_exec_path (agent C) : ODA en tete aussi.
  if ($vars['BM_ODA_CONVERTISSEUR']) { [void]$tete.Add((Split-Path -Parent $vars['BM_ODA_CONVERTISSEUR'])) }
  # Git : son dossier cmd seulement (git.exe), jamais bin ni usr\bin ; puis GitHub CLI.
  if ($vars['BM_GIT_BASH']) {
    $cmdGit = Join-Path (Split-Path -Parent (Split-Path -Parent $vars['BM_GIT_BASH'])) 'cmd'
    if (Test-Dossier $cmdGit) { [void]$tete.Add($cmdGit) }
  }
  if ($vars['BM_GH']) { [void]$tete.Add((Split-Path -Parent $vars['BM_GH'])) }
  $vues = @{}
  $nouveau = New-Object System.Collections.ArrayList
  foreach ($t in $tete) { $k = Get-ClePath $t; if (-not $vues.ContainsKey($k)) { $vues[$k] = $true; [void]$nouveau.Add($t) } }
  $ancien = [Environment]::GetEnvironmentVariable('PATH', 'Process')
  if ($null -eq $ancien) { $ancien = '' }
  foreach ($e in $ancien.Split(';')) {
    if (-not $e.Trim()) { continue }
    $k = Get-ClePath $e
    if ($vues.ContainsKey($k) -or $exclus.ContainsKey($k)) { continue }
    [void]$nouveau.Add($e)
  }
  $vars['PATH'] = ($nouveau -join ';')

  $versions = New-Object System.Collections.Specialized.OrderedDictionary
  if ($AvecVersions) {
    foreach ($def in $defs) {
      $cible = $vars['BM_' + $def.Cle]
      if ($cible -and $def.Dossier) { $cible = Join-Path $cible (Split-Path -Leaf $def.Exe) }
      $versions['_BM_V_' + $def.Cle] = (Get-VersionExe $cible)
    }
    if ($vars['BM_PYTHON']) {
      $versions['_BM_V_EZDXF'] = (Get-VersionEzdxf $vars['BM_PYTHON'] ($vars['BM_ORIGINE_PYTHON'] -eq 'portable'))
    }
  }

  # ------------------------------------------------------------------ sortie
  if ($Sortie -eq 'cmd') {
    foreach ($k in $vars.Keys) { [Console]::Out.WriteLine(('{0}={1}' -f $k, $vars[$k])) }
    foreach ($k in $versions.Keys) { [Console]::Out.WriteLine(('{0}={1}' -f $k, $versions[$k])) }
  }
  elseif ($Sortie -eq 'texte') {
    [Console]::Out.WriteLine(('Racine : {0}' -f $vars['BM_RACINE']))
    foreach ($def in $defs) {
      $c = $def.Cle
      $v = ''
      if ($versions.Contains('_BM_V_' + $c)) { $v = $versions['_BM_V_' + $c] }
      [Console]::Out.WriteLine(('  {0,-18} {1,-9} {2,-14} {3}' -f $c, $vars['BM_ORIGINE_' + $c], $v, $vars['BM_' + $c]))
    }
    if ($versions.Contains('_BM_V_EZDXF')) { [Console]::Out.WriteLine(('  {0,-18} {1,-9} {2}' -f 'EZDXF', '', $versions['_BM_V_EZDXF'])) }
    [Console]::Out.WriteLine(('Projet en cours : {0} ({1})' -f $vars['BM_PROJET'], $vars['BM_ORIGINE_PROJET']))
  }
  else {
    foreach ($k in $vars.Keys) {
      $v = $vars[$k]
      if ($v) { [Environment]::SetEnvironmentVariable($k, $v, 'Process') }
      else { [Environment]::SetEnvironmentVariable($k, $null, 'Process') }
    }
    foreach ($k in $versions.Keys) { [Environment]::SetEnvironmentVariable($k, $versions[$k], 'Process') }
  }
} $Sortie $Versions.IsPresent $PSScriptRoot

# Dot-source : ne rien laisser dans la session appelante, sauf les variables d'environnement.
Remove-Variable -Name Sortie, Versions -ErrorAction SilentlyContinue
