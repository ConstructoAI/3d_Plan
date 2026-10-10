# Les outils du poste : où ils sont, comment les trouver

> **Édition publique** (une gracieuseté de Sylvain Leduc, Constructo AI inc.). Ce dépôt ne contient AUCUN programme
> tiers : ce dossier porte le module qui les trouve, et le mode d'emploi pour en faire, si vous le voulez, un dossier
> autonome.

## Le principe : la copie du dossier d'abord, l'installation du poste ensuite

Le lanceur (`Demarrer-Blender.bat`) appelle `outils\chemins.cmd`. Pour chaque programme, il prend :

1. la copie **portable** rangée sous `outils\`, si elle existe ;
2. sinon l'**installation du poste**, affichée `[repli]`.

Il pose ensuite, pour la session Claude et pour tous les scripts, les variables `BM_RACINE`, `BM_PYTHON`, `BM_BLENDER`,
`BM_ODA_CONVERTISSEUR`, `BM_ODA_VISIONNEUSE`, `BM_NODE`, `BM_NAVIGATEUR`, `BM_GIT_BASH`, `BM_GH`, `BM_PROJET`, et
`BM_ORIGINE_*` (portable, systeme, variable ou absent). **Les scripts appellent les outils par ces variables**, ou par
le module `outils\chemins.py`, jamais par un chemin écrit en dur :

```python
import os, subprocess, sys
sys.path.insert(0, os.path.join(os.environ["BM_RACINE"], "outils"))
import chemins
subprocess.run([chemins.blender_exe(), "-b", "--factory-startup", "--python", "x.py"], env=chemins.env_blender())
```

Hors du lanceur, en PowerShell : `. .\outils\chemins.ps1`. Pour pip et pytest : toujours
`& $env:BM_PYTHON -s -m pip …` et `-m pytest`.

## Vérifier le poste

| Commande | Ce qu'elle fait |
|---|---|
| `Demarrer-Blender.bat /verifier` | Le diagnostic du lanceur, sans ouvrir Claude : chaque outil, sa version, son origine. |
| `& $env:BM_PYTHON outils\chemins.py --complet` | Le même inventaire, en lançant `--version` de chaque programme, sans fenêtre. |
| `& $env:BM_PYTHON -s -m pytest outils\diagnostic\test_chemins.py` | Les essais du module de chemins. |
| `& $env:BM_PYTHON outils\diagnostic\dependances_dll.py <dossier> --symboles` | Les DLL dont dépend une copie portable (pour savoir si elle voyage seule). |

## Faire du dossier un dossier autonome (facultatif)

Le dossier peut porter ses propres programmes et se coller d'un poste à l'autre. Chaque copie va sous `outils\` :

| Dossier | Programme | À savoir |
|---|---|---|
| `outils\python\` | Python 3.13 et ses paquets (`requirements.txt`) | Lancer avec `-s` : une copie voit encore le site utilisateur du poste. Ne jamais mettre `outils\python\Scripts` dans le PATH. |
| `outils\blender\` | Blender 5.2 | Le dossier `outils\blender\portable\` déclenche le mode portable. Chemin du poste : 110 caractères au plus. |
| `outils\oda\convertisseur\`, `outils\oda\visionneuse\` | ODA File Converter et ODA Viewer | Licence de l'ODA à accepter sur son site ; ne se redistribue pas. |
| `outils\node\` | Node.js 22 | Pour le PDF 3D. `npm_config_update_notifier=false` évite une attente de 45 s. |
| `outils\git\`, `outils\gh\` | Git pour Windows (Git Bash) et GitHub CLI | Git Bash est l'outil Bash de Claude Code. La connexion de `gh` reste par utilisateur Windows. |
| `outils\claude\` | Claude Code (exécutable natif) | Voir « Claude Code » plus bas. |

`outils\copier_vers_poste.ps1` copie le dossier vers un autre emplacement et écrit le manifeste SHA-256 de chaque
fichier ; `outils\verifier_copie.ps1` le vérifie à l'arrivée. Après un transfert par ZIP, débloquer les fichiers.
Le pilote de la carte graphique ne voyage pas : sans lui, le rendu se fait sur le processeur.

Ces copies ne vont JAMAIS dans git : le `.gitignore` du dépôt les écarte, avec la configuration de Claude.

## Claude Code

- Le lanceur prend d'abord le Claude Code installé sur le poste, sinon `outils\claude\claude.exe`.
- Il ouvre la session en **Opus 5.5, contexte 1M, effort max** : il faut un compte **Claude Max 20x**.
- Si le dossier `outils\claude\config\` existe, le lanceur y range la configuration de Claude (`CLAUDE_CONFIG_DIR`),
  connexion comprise après le premier lancement : **le dossier vaut alors une clé**. Ne le partagez pas, ne le poussez
  dans aucun dépôt. Sans ce dossier, la configuration reste dans votre profil d'utilisateur. Retour au profil :
  `set BM_CLAUDE_CONFIG=profil` avant de lancer.
- La copie portable ne se met pas à jour en ligne : le lanceur la rafraîchit depuis l'installation du poste.

## Les clés d'API

La seule clé utile à tous est `GOOGLE_GEMINI_API_KEY` (photo hyperréaliste). C'est une variable de l'utilisateur
Windows, **jamais écrite dans un fichier du dossier**. Le lanceur dit si elle manque ; pour la poser, voir `README.md`.
