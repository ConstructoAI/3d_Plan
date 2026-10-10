# 3D Plan

**De la photo ou du plan PDF au modèle 3D, aux rendus, à la photo hyperréaliste et aux plans AutoCAD
cotés (DWG et PDF) — Blender 5.2 piloté par Claude Code, en français, pour la construction au Québec.**

Vous écrivez à Claude ce que vous voulez bâtir ou dessiner ; il pilote Blender par scripts, vérifie son
propre travail, puis vous remet le modèle, les images et le jeu de plans. Ce dépôt est le **poste de
pilotage** : le lanceur, les cinq agents, les savoirs vérifiés et les outils de référence.

> ### Une gracieuseté de **Sylvain Leduc**, président de **Constructo AI inc.**
> *Écosystème intelligent pour la construction au Québec* ·
> [www.constructoai.ca](https://www.constructoai.ca)

---

## 🔴 Ce qu'il faut pour s'en servir

| Exigence | Pourquoi |
|---|---|
| **Un compte Claude Max 20x** | Le lanceur ouvre Claude Code en **Opus 5.5, contexte 1M, effort max**, avec une équipe d'agents : un forfait plus petit s'épuise vite. |
| **Un compte Google et sa clé d'API Gemini** | Seulement pour la **photo hyperréaliste** (environ 0,24 $ US par image 4K, facturée par Google). Tout le reste fonctionne sans elle. |
| Windows 10 ou 11 | Le lanceur est un `.bat` ; les scripts appellent PowerShell et Git Bash. |
| [Claude Code](https://claude.com/claude-code) | Le moteur de la session. |
| [Blender 5.2 LTS](https://www.blender.org/download/) | Modèle 3D et rendus (EEVEE, Cycles), en arrière-plan, sans fenêtre. |
| Python 3.13 et `requirements.txt` | ezdxf (DXF), PyMuPDF (plans PDF), Pillow, numpy, scipy, reportlab… |
| [ODA File Converter](https://www.opendesign.com/guestfiles/oda_file_converter) | DXF → DWG. Gratuit ; sa licence s'accepte sur le site de l'ODA. |
| [Git pour Windows](https://git-scm.com/download/win) | L'outil Bash de Claude Code. |
| Node.js 22 (facultatif) | Le PDF 3D. |

Ce dépôt ne contient **aucune clé** et **aucun programme tiers** : voir plus bas.

---

## Ce que le poste sait faire

| Étape | Ce que Claude produit |
|---|---|
| 📷 **Relevé** | D'après une photo (points de fuite, calage de caméra) ou un plan PDF vectoriel (cotes, murs, ouvertures). |
| 🧱 **Modèle 3D** | Un script Blender paramétré : une dimension change, tout se régénère. |
| 🖼️ **Rendus** | EEVEE et Cycles, vues de présentation, comparaison avec la photo d'origine. |
| ✨ **Photo hyperréaliste** | Le rendu passé à Google Gemini, avec une consigne qui garde la géométrie fidèle. |
| 📐 **Plans 2D cotés** | Plans, élévations, coupes et détails en DWG (pouces, cotes pieds-pouces), tirés des mêmes paramètres. |
| 📄 **PDF du jeu** | Toutes les feuilles au format réel, vectoriel, texte cherchable. |
| 🧊 **DWG 3D et PDF 3D** | Le modèle pour AutoCAD, et un PDF 3D qui s'ouvre dans un lecteur PDF. |
| ✅ **Vérification** | Un agent en lecture seule contrôle les cotes et la cohérence entre les feuilles AVANT la livraison. |
| 💰 **Prix budgétaire** | Méthode cost-plus d'un entrepreneur général du Québec, calcul affiché étape par étape. |

Claude écrit les scripts de chaque projet en suivant les savoirs du dépôt, et en copiant les outils de
`modeles\`. Les dessins portent un cartouche honnête : **préparé par une IA, à valider et à sceller par un
professionnel**. Aucun sceau n'est jamais simulé.

---

## Ce que contient le dépôt

| Chemin | Rôle |
|---|---|
| `Installer.bat` | **À double-cliquer une fois** : installe ce qui manque sur le poste, puis lance le diagnostic. |
| `Demarrer-Blender.bat` | **Le fichier à double-cliquer** : vérifie le poste, affiche le menu, ouvre la session. |
| `CLAUDE.md` | Le « fichier vivant » : ce que Claude sait du poste, vérifié, et qu'il tient à jour. |
| `SAVOIR_*.md` | Les savoirs détaillés : Blender et rendu, DXF et DWG, lecture de plans, équipes d'agents, Windows. |
| `.claude\agents\` | Les 5 profils : `modelisation`, `dao`, `verification`, `estimation`, `bim-freecad`. |
| `.claude\skills\` | Deux compétences : `entrepreneur-qc` et `freecad`. |
| `*_profil.txt` | Les profils de métier incarnés par Claude : entrepreneur général, architecte, ingénieur en structure, plombier, électricien, armoires de cuisine. |
| `modeles\` | Les outils de référence à copier dans un nouveau projet (`modeles\LISEZMOI.md`). |
| `Rendu3D_ERP\` | L'outil de photo hyperréaliste (`photo_hyperrealiste.py`) et ses essais. |
| `outils\` | Le module de chemins (`chemins.py`, `.ps1`, `.cmd`), les diagnostics et le mode d'emploi du dossier autonome (`outils\LISEZMOI.md`). |

## Ce que le dépôt ne contient pas

- **Aucun programme tiers.** Blender, Python, ODA File Converter, Node.js, Git et Claude Code ne sont pas
  redistribués ici : plusieurs gigaoctets, et des licences qui ne le permettent pas toutes. Le lanceur
  prend les programmes installés sur votre poste et l'affiche (`[repli]`) ; `outils\LISEZMOI.md` dit
  comment en faire, si vous le voulez, un dossier autonome qui porte ses propres copies.
- **Aucune clé, aucun jeton**, et aucune donnée de client. Les noms, les adresses et les prix réels ont
  été retirés ; les projets de référence portent des noms génériques (« Bungalow », « Agrandissement »,
  « Saint-Exemple »).
- **Le programme Métré, le format de soumission d'un entrepreneur et l'ERP Constructo AI**, sauf deux
  extraits publiés volontairement : `Rendu3D_ERP\ERP_REACT\backend\routers\gemini_image.py` (l'invite de
  la photo) et `modeles\pdf_3d\erp\` (l'écrivain du PDF 3D). Les savoirs citent encore le reste par
  endroits : ces fichiers n'existent que sur le poste d'origine. Le choix 3 du menu (« programme Métré »)
  répond donc « absent ».
- **Les générateurs complets de mandats réels** (modèle 3D, jeu de plans, dessins de fabrication) : ils
  redessinent le plan d'un tiers pour un client. Les savoirs donnent la méthode pour écrire les vôtres.
- **Des savoirs et outils cités mais non publiés** : `SAVOIR_METRE.md`, `SAVOIR_PROJETS.md`,
  `JOURNAL_SESSIONS.md` (Claude les crée au besoin), le savoir et les scripts de la charpente métallique,
  le pont FreeCAD (`freecad-mcp`, dont dépendent le profil `bim-freecad` et la compétence `freecad`) et les
  dossiers des projets d'origine (`C:\Dev\<Projet>\`).

---

## Installation

```
1. Télécharger ce dépôt (bouton « Code » puis « Download ZIP », ou git clone) dans un chemin COURT,
   par exemple C:\Dev\3d_Plan : Blender refuse les chemins longs.
2. Double-cliquer Installer.bat
3. Installer ODA File Converter (l'installateur ouvre sa page : sa licence s'accepte sur son site).
4. Double-cliquer Demarrer-Blender.bat
```

**`Installer.bat`** fait l'inventaire du poste, pose **une seule question**, puis installe ce qui manque
par winget : Python 3.13 et ses paquets, Blender, Git pour Windows, Node.js et Claude Code. Il termine par
le diagnostic du lanceur. Si rien ne manque, il ne pose aucune question.

- `Installer.bat /essai` dit ce qui serait installé, **sans rien installer**.
- Python et Claude Code s'installent pour votre compte, sans droits d'administrateur. Blender, Git et
  Node.js s'installent pour toute la machine : Windows affiche une invite, que vous pouvez refuser.
- Il n'installe ni ODA File Converter, ni votre abonnement Claude, ni votre clé Google : voir plus bas.
- ⚠️ **Première version** : éprouvée en simulation (programmes comptés comme absents), pas encore sur un
  poste vierge. Si une étape échoue, le message dit laquelle ; tout s'installe aussi à la main, à partir
  du tableau du haut, puis `python -m pip install -r requirements.txt`.

Diagnostic seul, sans lancer Claude : `Demarrer-Blender.bat /verifier`. Il dit, outil par outil, ce qui
est trouvé et ce qui manque.

Après un téléchargement en ZIP, Windows peut bloquer les fichiers : clic droit sur le ZIP → Propriétés →
**Débloquer**, avant de décompresser.

### La clé Google Gemini (photo hyperréaliste)

Créez la clé sur [aistudio.google.com/apikey](https://aistudio.google.com/apikey), puis posez-la UNE fois,
comme variable de votre utilisateur Windows — jamais dans un fichier. Dans PowerShell :

```powershell
$cle = Read-Host 'Cle Gemini'
[Environment]::SetEnvironmentVariable('GOOGLE_GEMINI_API_KEY', $cle, 'User')
```

Saisie ainsi, la clé ne reste pas dans l'historique de PowerShell. Fermez la fenêtre, puis relancez le
lanceur : il dit si la clé est trouvée.

### 🔴 À savoir avant de lancer : la session tourne SANS garde-fou de permissions

Le lanceur démarre Claude avec `--dangerously-skip-permissions` : Claude ne vous demandera **aucune
autorisation** avant de lire un fichier, d'en écrire un ou de lancer une commande. C'est ce qui lui
permet de travailler des heures avec ses agents, et c'est un choix à faire en connaissance de cause :
lancez-le sur un poste de travail dont vous avez des sauvegardes, pas sur un serveur de production. Pour
retrouver les demandes d'autorisation, retirez cette option du `.bat`.

---

## Par où commencer

Double-cliquez le lanceur, puis demandez, par exemple :

- « Voici la photo d'un garage de 40 pi sur 100 pi : fais-moi le modèle 3D, cinq rendus et les plans cotés. »
- « Lis ce plan PDF et dessine-moi le jeu complet : plans, élévations, coupes, PDF du jeu. »
- « Fais-moi une photo hyperréaliste de ce rendu, sans changer les portes ni les fenêtres. »

Chaque projet vit dans son propre dossier, à côté de celui-ci (`C:\Dev\<Projet>\`). À la fin de chaque
session, Claude verse ce qu'il a appris dans `CLAUDE.md` et dans les savoirs : le poste s'améliore à
chaque projet.

---

## Avertissements

- Les plans, les quantités et les prix produits par ce poste sont **préparés par une IA** : ils doivent
  être validés, et au besoin scellés, par un professionnel habilité. Rien ici ne remplace un architecte,
  un technologue ou un ingénieur.
- Les profils de métier (`*_profil.txt`) sont des invites : ni Claude ni ce dépôt ne détiennent de titre
  professionnel ni de licence.
- Blender est une marque de la Blender Foundation ; AutoCAD et DWG, d'Autodesk ; Claude, d'Anthropic ;
  Gemini, de Google. Ce projet n'est affilié à aucune de ces organisations.

## Licence

[Apache 2.0](LICENSE) — © 2026 Sylvain Leduc, Constructo AI inc. Voir aussi [NOTICE](NOTICE).
