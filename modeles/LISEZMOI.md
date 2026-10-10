# Modèles : les scripts de référence d'un nouveau projet

> **Édition publique** (une gracieuseté de Sylvain Leduc, Constructo AI inc.). Ces scripts viennent de vrais projets ;
> les noms de clients, les adresses et les données de leurs plans ont été retirés. Le dossier `projet_bungalow\` porte
> un nom générique.

On ne travaille jamais ICI : on **copie** le script voulu dans le dossier du projet (`C:\Dev\<Projet>\`), puis on
l'adapte. Dans un projet, la source de vérité est un seul fichier `parametres_<projet>.py` (gabarit, ouvertures, caméra,
en pieds) : Blender ET les plans le lisent, et changer une dimension revient à changer une ligne.

Les outils se trouvent par les variables du lanceur (`BM_PYTHON`, `BM_BLENDER`, `BM_ODA_CONVERTISSEUR`, `BM_NODE`) ou
par le module `outils\chemins.py` : jamais par un chemin écrit en dur.

## Ce que contient ce dossier

| Dossier | À quoi il sert |
|---|---|
| `releve_pdf\` | Relevé d'un plan PDF VECTORIEL : inventaire des pages (`analyse_pdf.py`), mots et tracés en JSON (`extraire_mots.py`), axes et cotes (`grilles.py`), surfaces remplies (`remplis.py`), segments et mots d'une zone, agrandissements (`zoom.py`). `releve_travail\` : outils de détail (murs, cloisons, vantaux, carreaux). |
| `releve_photo\` | Relevé d'après une PHOTO : points de fuite (`analyse_photo.py`), calage de la caméra par moindres carrés avec les dimensions connues en contraintes (`resection2.py`), comparaison du rendu avec la photo, contrôle de repères. |
| `rendu_controles\` | `verifier_coplanaires.py` : faces coplanaires qui se recouvrent (taches noires de Cycles), sans rendu. `exporter_autocad.py` : le modèle Blender vers un DWG 3D (MESH, un calque par collection). |
| `plans_pdf\` | `plans_pdf.py <jeu.dxf>` : le PDF du jeu de plans, une page par feuille, au format réel, vectoriel, texte cherchable. |
| `pdf_3d\` | `pdf_3d.py <fichier.blend> --sortie x.pdf` : un PDF 3D depuis n'importe quel `.blend` (Blender en arrière-plan, puis Node). Son `LISEZMOI.md` donne la recette et ce qui est prouvé. |
| `projet_bungalow\` | Les outils d'un projet complet d'après un plan PDF tourné et réduit : `reference\` (relevé sur pages tournées, chaînes de cotes), `exporter_autocad.py` (DWG 3D complet), `verifier_coplanaires.py`, `empreinte_bungalow.py` (une même empreinte des sources pour tous les livrables), `superposer_elevations.py`, `planche_rendus.py`, `plans\outils\comparer_cotes_interieures.py`, et `estimation\prix_budgetaire.py` avec son `entrees_exemple.json` (prix budgétaire cost-plus, calcul affiché). |

## Ce qui n'est pas ici

Les générateurs complets d'un mandat (modèle 3D, jeu de plans, annexe d'estimation) redessinent le plan d'un tiers pour
un client : ils ne sont pas publiés. Il en va de même du métré, de la soumission au format d'un entrepreneur, des
dessins de fabrication d'un atelier et des scripts propres à l'ERP Constructo AI. Les savoirs de la racine
(`CLAUDE.md`, `SAVOIR_*.md`) décrivent la méthode qui permet de les récrire pour vos propres projets.

## Essayer un outil

```powershell
& $env:BM_PYTHON -X utf8 -s modeles\projet_bungalow\estimation\prix_budgetaire.py modeles\projet_bungalow\estimation\entrees_exemple.json
& $env:BM_PYTHON -X utf8 -s modeles\plans_pdf\plans_pdf.py <votre_jeu.dxf>
& $env:BM_PYTHON -X utf8 -s modeles\pdf_3d\pdf_3d.py <votre_fichier.blend> --sortie modele_3d.pdf --titre "Mon projet"
```
