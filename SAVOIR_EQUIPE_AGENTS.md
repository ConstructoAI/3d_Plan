# Savoir vivant — équipes d'agents : contrat, gels, relectures, successeurs

> **Édition publique** (une gracieuseté de Sylvain Leduc, Constructo AI inc.) : noms de clients, adresses et données internes retirés ; les projets de référence portent des noms génériques (« Bungalow », « Agrandissement », « Saint-Exemple »). Certains fichiers cités n'existent que sur le poste d'origine : voir `README.md`, « Ce que le dépôt ne contient pas ».

Sorti de `CLAUDE.md` le 2026-10-10 (le fichier vivant dépassait sa limite de 150 000 caractères) : le texte des
sections est celui d'origine (noms rendus génériques, passages internes retirés).
**À lire AVANT** de lancer ou de reprendre une équipe d'agents, de geler des sources, de faire relire un jeu avant
livraison, ou de déposer un dossier chez le client.
**À enrichir** à la fin de chaque session : les pièges vérifiés et les durées mesurées de ce sujet vont ICI, plus dans
`CLAUDE.md`. Corriger ou retirer ce qui devient faux.
Règles de Sylvain (dans « Préférences » de `CLAUDE.md`) : 5 agents au plus à la fois depuis le 2026-10-10 ; aucune
fenêtre sur le poste sans le prévenir ; vérification avant toute livraison.

## Pièges vérifiés — équipe d'agents (brûleur, 2026-09-24)

- **Contrat écrit dans `INTERFACE.md`**, tenu par l'intégrateur :
  - les noms exposés en mètres, les collections et les matériaux sous leurs noms exacts ;
  - `RES` choisi par une variable d'environnement (`rendu` ou `dao`) ;
  - un module `construire(P)` pour chaque agent de modélisation.
  Chaque agent possède SES fichiers et étiquette ses objets (`ob["agent"]`). `INTERFACE.md` ne recopie pas les
  valeurs d'un autre agent : il y renvoie, sinon elles se périment.
- **Verrou GPU partagé** (`.verrou_gpu` à la racine du projet) :
  - création atomique en Bash (`set -o noclobber`), suppression dans `trap … EXIT` ;
  - jeton = agent + heure de PRISE du verrou ;
  - tuer un Blender laisse le verrou en place : le supprimer à la main ;
  - une attente qui sonde toutes les 10 s a perdu 13 min contre un agent qui enchaînait ses rendus.
- **Exports DAO** :
  - partir d'une copie figée des sources, dont l'empreinte sha256 est écrite dans le DWG ;
  - attendre 2 min sans modification ; revérifier l'empreinte à la fin ;
  - un modèle déclaré « final » a encore changé 50 s plus tard.
- **3 passes de vérification ont trouvé de vrais défauts, invisibles depuis la vue photo** :
  - conduits portés par rien, trouvés par le graphe des contacts jusqu'au sol : retirer un contact suspect et
    recompter les objets portés ;
  - tubes qui s'arrêtent dans le vide ;
  - coudes repliés : `arrondir()` réduisait le rayon en silence. Exiger 1,5 × NPS au moins ; un coude à grand
    rayon de 6 po demande 9 po droits ;
  - armoire traversée par le flexible ;
  - contrôle de repères circulaire.
  Pour trier les interpénétrations : un raccord voulu, c'est un bout logé dans l'autre pièce ou une pièce enfilée sur
  le même axe. Le reste se vérifie un par un.
- **Mode allégé** : quand on omet une petite pièce, ce qu'elle reliait doit rester attaché (raccord simplifié, volant en
  disque plein). Refaire le contrôle de contacts dans les deux résolutions.
- **Durée** : environ 5 h d'horloge, de la photo aux deux dépôts, pour 5 agents et 3 passes de vérification.

## Pièges vérifiés — équipe d'agents, charpente métallique (Saint-Exemple, 2026-10-08)

- ✅ **Inscrire l'état du projet dans CLAUDE.md EN COURS de session**, pas seulement à la fin : le projet de plomberie
  du 2026-09-29 n'y figurait pas, parce que sa session s'était arrêtée avant.
- ✅ Les agents `dao`, `modelisation` et `verification` ne peuvent pas écrire au chef : leur demander un fichier
  `ETAT.txt` mis à jour à chaque étape, et le lire. Ils REÇOIVENT bien les messages (lus à leur prochain appel d'outil).
- ✅ Les agents `general-purpose` écrivent à « main » en cours de route : très utile pour le catalogue (« v1 publiée »)
  et pour les constats croisés (le laser a trouvé 14 défauts de découpe dans le catalogue de la conception).
- ✅ **La durée annoncée par un agent n'est pas fiable** : le relevé disait « environ 95 minutes », le compteur de la
  tâche disait 19 min. Se fier à `duration_ms` de la notification.
- ✅ **Une source unique publiée par versions** : `conception\PUBLIE.txt` (version, heure, empreinte) et `pieces.json`
  écrits ENSEMBLE. Les agents lecteurs travaillent sur l'instantané publié ; un agent a détecté que les sources
  vivantes avaient bougé après la publication (empreinte différente) et a continué sur l'instantané.
- ✅ `AskUserQuestion` : 4 questions à choix, recommandation en premier et `multiSelect` pour la portée. Le texte
  d'analyse placé AVANT l'appel s'affiche bien.
- ✅ PDF de lettre avec reportlab : un tableau qui remplit exactement la page pousse la note finale seule sur une page
  de plus ; resserrer les marges des cellules. Le caractère ☐ n'existe pas dans Arial (carré vide de substitution).

## Pièges vérifiés — Saint-Exemple, nuit du 2026-10-09 (équipe, outils, dépôt)

- ✅ **Contexte d'un agent** : la notification de fin donne `subagent_tokens` ; vers 900 000, l'agent ne peut plus rien
  recevoir (« Prompt is too long »). Au-delà de 750 000, lancer un SUCCESSEUR avec une consigne complète (quoi lire,
  ce qui est à lui, corrections numérotées, ce qui ne doit pas changer, preuve attendue). Lui demander un fichier de
  notes dès le début. 4 agents de conception et 3 de dessin d'atelier se sont succédé sur ce projet.
- ✅ `SendMessage` REPREND un agent `verification` qui a fini (V3, à 750 000 jetons) pour une relecture ciblée du gel
  suivant : il garde ses scripts et son contexte (84 min de plus).
- ✅ **Agents de dessin en deux phases** : corriger le code et l'essayer sur le gel courant, écrire « PRÊT POUR Fn »,
  puis générer au message « gel Fn = <empreinte> ». Ne pas regeler pendant leur essai complet : l'empreinte change
  sous leurs pieds (leur contrôle début-fin l'attrape, mais l'essai est perdu).
- ✅ **Un correctif de moteur par le chef, quand l'agent est épuisé** : copier le fichier d'abord, écrire le correctif
  par un script (outil Write), l'essayer sur les feuilles touchées sans PDF (26 s), le prouver par les scripts du
  vérificateur, puis régénérer. `Path.write_text(..., newline=<valeur illégale>)` VIDE le fichier avant de lever
  son erreur : la copie d'avant a sauvé le module.
- ✅ **Heredoc Bash et barres obliques inverses** : `\\` y devient `\` (un chemin `verification\\rapport` est devenu un
  retour chariot dans ce fichier). L'outil Write, lui, écrit ce qu'on lui donne. Pour un texte à chemins Windows :
  script écrit par Write, avec un caractère de remplacement ou `chr(92)`, puis compter les retours chariot.
- ✅ **PDF vectoriel lourd** (204 feuilles 11 × 17 = 130 Mo) : aucune compression sans perte n'y gagne ; `garbage=4` de
  PyMuPDF y tourne plus de 15 min pour rien. Le découper en volumes par `insert_pdf` (7 s) pour l'envoi.
- ✅ **Compter le temps par `date`** : mon estime avait 10 à 25 min d'avance sur l'horloge ; les agents écrivent aussi
  des heures fausses dans leurs fichiers d'état.
- ✅ `grep -c` rend le code 1 quand il compte 0 : dans une suite `&&`, il arrête tout ce qui suit.

## Pièges vérifiés — Saint-Exemple, jour du 2026-10-09 (reprises de gel, relectures, PDF 3D)

- ✅ **Trois regards qui ne voient pas la même chose** sur un gel de fabrication : (1) non-régression entité par
  entité contre le jeu d'avant (chaque feuille changée a une cause voulue) ; (2) un LECTEUR qui lit les feuilles
  neuves « comme l'atelier », sans le code ; (3) la MESURE sur le modèle 3D (contact réel de chaque soudure). Le 3e a
  trouvé un défaut vrai depuis le premier gel, que six vérifications de dessins n'avaient pas vu.
- ✅ **Vérifier le BROUILLON d'une source avant de la geler** : en figer une copie lisible
  (`conception\brouillon_vNN\A`), y lancer le vérificateur et les chaînes d'essai. 7 constats pris AVANT le gel.
- ✅ **Le chef corrige la source quand son agent est épuisé** : sur une COPIE, par un script à repères uniques (chaque
  repère trouvé exactement une fois, sinon rien n'est écrit), essais et contre-essais, différence écrite, puis
  publication et gel. 40 min pour le catalogue v3.7 (`chef\patch_v37.py` du projet).
- ✅ **Avant d'ajouter un point à une liste, la relire** : j'allais écrire un point 34 que le point 3 couvrait déjà.
- ✅ **Arrêter une génération longue devenue inutile** (PDF de 218 feuilles sur un gel à refaire) : garder son DXF
  comme référence de comparaison, puis relancer UNE fois sur le bon gel.
- ✅ **Outils d'un autre agent** :
  - un script de vérification peut écrire dans un chemin RELATIF fixe (j'ai écrasé une sortie en le lançant depuis
    son dossier) : le lancer depuis un dossier à part, avec `PYTHONPATH` ;
  - un lecteur de tableau a des bornes de colonnes en dur (18 faux écarts quand le dessinateur a élargi une
    colonne) : qui change un tableau le dit AVANT la génération officielle.
- 🔴 **Un contrôle qui ne s'exerce qu'en jeu COMPLET n'est jamais vu par les répétitions par lots** : la génération
  officielle des 218 feuilles (40 min) a fini par « À CORRIGER » sur un FAUX défaut (une paire « main opposée » de
  barres sans trou, dont le contrôle cherchait les tableaux de trous).
  - Avant une génération officielle : UNE répétition complète sans PDF (`plans_atelier.py --sources sources_figees
    --essai --nom x --sans-pdf --sans-apercus --sans-zooms`, 4 min 30).
  - Après coup, sans rien régénérer : corriger le contrôle, rejouer le jeu en essai (« TOUS LES CONTRÔLES SONT
    BONS »), prouver que l'essai dessine le jeu officiel entité par entité (218 feuilles identiques ; 3 lignes
    d'écart dans le DXF : deux dates et un identifiant), l'écrire à côté des contrôles (`atelier\NOTE_CONTROLES_F8.txt`)
    et le dire à Sylvain tel quel.
- ✅ **Pagination** : une ligne de plus dans la note de la 1re feuille d'une liste paginée ajoute une feuille et
  renumérote les suivantes ; une colonne rigide prend la largeur de son en-tête entier.
- ✅ **Ne pas donner une cause que je n'ai pas mesurée** : j'ai écrit à Sylvain que le PDF était lent « parce que les
  aperçus sont tous en couleur » ; le journal a montré 44 aperçus en couleur sur 218, comme la nuit. La lenteur venait
  des contrôles lancés en même temps (les miens et ceux du vérificateur). Corrigé dans le compte rendu.
- ✅ **/cad : une RÉVISION ne renomme pas le dessin** (« nom ignoré ») : jamais de référence dans le NOM d'un dessin,
  elle va au commentaire. Sinon : dessin neuf, et dire à Sylvain lequel est périmé (lui seul le retire).
- ✅ **Sauver le bloc-notes de la session AVANT la fin** : c'est un dossier temporaire, et les notes des agents citent
  leurs outils par ce chemin. `chef\sauver_blocs_notes.py --ecrire` : scripts et notes de tous les agents dans
  `archives\blocs_notes_<date>\` du projet (2 065 fichiers, 73 Mo), outils du chef dans `chef\`.
- ✅ **Guetteurs en arrière-plan** : ancrer le motif sur le début de la ligne (un `until grep -q "FINAL SUR F6"` s'est
  déclenché sur la phrase d'un plan qui citait ce signal) ; un guetteur dont le signal ne viendra plus tourne sans
  fin : `TaskStop`.
- ✅ PowerShell 5.1, `*>` : journal en UTF-16, illisible pour `grep` (redit : passer par Bash, ou `Out-File -Encoding
  utf8`). Un chemin `/c/…` écrit DANS un `python -c "…"` n'est pas converti par Git Bash (seuls les arguments le sont).
- ✅ **PDF 3D** : deux `.blend` de même géométrie donnent le MÊME PDF à l'octet (comparer par empreinte) ; Node 22.18
  exécute le TypeScript « effaçable » de l'ERP tel quel (crochet `--import` pour ses imports sans extension, rien
  d'installé) ; pypdf 6.0.0 (2e lecteur de PDF, mode strict) et aspose-cad (lecteur tiers du U3D, sans licence,
  silhouette estampillée) sont dans le Python du poste.
- ✅ **Photos réalistes après un nouveau gel** : ne refaire que celles dont la vue brute a changé (amas de pixels
  de plus de 12/255 sur 12 px ou plus : `chef\ecart_fin.py`). 33 images, 7,92 $ US, pour 10 retenues.
- ✅ **Durées (poste chargé, 4 fils)** : assemblage général 25 à 28 min ; dessins d'atelier de 218 feuilles
  40 min 40 s à `--proc 3` (dessin 111 s ; contrôles, DXF et DWG 227 s ; PDF de 145 Mo et aperçus 34 min 39 s,
  avec des contrôles lancés à côté : ne RIEN lancer d'autre pendant le PDF ; la nuit, poste libre, 204 feuilles en
  30 min) ; laser 87 à 154 s ; remarquage du 3D sans rendu 13 min ; PDF 3D 3 min ; ZIP du client 16 s ; relecture
  ciblée d'un gel par un vérificateur neuf : 1 h 40, attentes comprises.

