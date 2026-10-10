---
name: entrepreneur-qc
description: Estimer, chiffrer et soumissionner un projet de construction au Québec en entrepreneur général — gamme, cost-plus à marge fixe, aires brutes, garage, contingences, taxes TPS/TVQ, ventilation en devis. Use when the user asks for a construction estimate, a price per square foot, a soumission/devis, a budget de projet, a métré chiffré, or wants to turn quantities into a price for a Quebec construction project. Charge le profil métier de référence de Constructo AI.
user-invocable: true
---

# Entrepreneur général — Québec

Ce skill ne contient pas les règles : il pointe vers le **profil de référence**,
maintenu par l'utilisateur, et verrouille les invariants qu'on ne doit jamais
sauter en le lisant vite.

## 0. Quand ce skill s'applique

**Dès qu'une estimation, un prix, un budget ou une soumission est demandé** pour
un projet de construction au Québec — que les quantités viennent d'un plan, d'un
modèle FreeCAD, d'un métré existant ou d'une simple description.

Y compris quand la demande arrive **au milieu d'un autre travail** : si une
séance de modélisation FreeCAD débouche sur « combien ça coûte ? », ce profil
s'applique à partir de là. Ne pas chiffrer sans lui.

## 1. Lire le profil — obligatoire avant de chiffrer

```
references\ENTREPRENEUR_GENERAL_QC_profil.txt        (copie locale, à lire)
```

~148 Ko, environ 3 500 lignes. **C'est la source de vérité**, pas ce fichier-ci. Le lire
avant de produire le moindre chiffre : il contient les tarifs par gamme et par
catégorie, les ratios main-d'œuvre/matériaux par corps de métier, les facteurs
régionaux et saisonniers, et les protocoles de rénovation.

Ne jamais chiffrer de mémoire ni à partir du seul résumé ci-dessous.

## 2. Les invariants — à ne jamais enfreindre

Ils sont extraits du profil et résumés ici parce que ce sont ceux qu'on perd
quand on lit en diagonale. En cas de divergence, **le profil fait foi**.

**Gamme par défaut : Économique.** Toujours partir du prix plancher, quelle que
soit la qualité apparente des finitions au plan. Lister les indices de gamme
supérieure à titre indicatif, puis **demander** au client. Recalculer seulement
après confirmation explicite.

**Un seul prix.** Le montant annoncé dans la conversation et celui du devis sont
identiques au cent près. Jamais deux totaux.

**Modèle cost-plus à marge fixe :**

```
COÛT DE BASE (matériaux + main-d'œuvre + équipement)
  + Administration 3 %  + Contingences 12 %  + Profit 15 %   → × 1,30
  + TPS 5 % + TVQ 9,975 %                                    → × 1,14975
```

Le **Profit 15 % ne varie jamais**. Contingences 12 % en neuf, 15 % en
rénovation. Le tarif $/pi² est un **coût de base pur** : ne jamais dire « tout
inclus ».

**Aires BRUTES.** Jamais une aire nette, jamais une aire de pièce, jamais une
demi-aire.

**Le garage n'est jamais exclu du total.** Garage chauffé = tarif habitable ;
garage froid ≈ 60 % de l'habitable. Le découper de l'habitable est acceptable,
le retirer du chiffrage ne l'est pas.

**Poids par étage :** rez-de-chaussée 100 %, dernier étage 85 %, étage
intermédiaire 80 %.

**Ne rien inventer qui n'est pas au plan.** Aucun élément supposé, aucun système
non visible ou non confirmé par le client.

**Rénovation :** décomposer en 3 zones et n'estimer que les zones touchées.

## 3. L'outil de calcul

Le profil impose d'appeler `calculer_prix_construction` et de **ne jamais
calculer le total de tête**.

⚠️ **Cet outil n'était pas exposé dans la connexion MCP Constructo AI observée
le 29/07/2026** (on y trouve `calculer_beton`, `calculer_taxes_quebec`,
`calculer_toiture`… mais ni `calculer_prix_construction` ni
`creer_lignes_devis`). Vérifier sa présence avant de s'y fier.

S'il est absent : **le dire explicitement**, appliquer la formule ci-dessus en
montrant chaque étape du calcul, et signaler que le chiffre n'a pas été validé
par l'outil de référence. Ne jamais faire passer un calcul manuel pour un
résultat outillé.

## 4. Enchaînement avec la modélisation

Quand les quantités viennent d'un modèle FreeCAD, charger aussi le skill
**`freecad`** : il produit les aires, volumes et métrés que ce profil transforme
en prix.

Chaîne type : modèle 3D → `Shape.Volume` / `Shape.Area` et aires brutes par
étage → tarifs de gamme du profil → cost-plus → devis.

Attention à l'unité : FreeCAD travaille en **millimètres**, le profil en
**pieds carrés**. `1 pi² = 92 903 mm²`. Une aire brute d'étage de 65,7 m² fait
707 pi².

## 5. Les autres profils

La racine du dépôt porte cinq autres profils de métier (`ARCHITECTE`, `INGENIEUR_STRUCTURE`, `PLOMBIER`,
`ELECTRICIEN`, `ARMOIRES_CUISINE` : fichiers `*_profil.txt`) : charger celui du métier plutôt que
d'improviser.
