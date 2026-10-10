# Photo hyperréaliste à partir d'un rendu Blender

> **Édition publique** (une gracieuseté de Sylvain Leduc, Constructo AI inc.). Ce dossier porte l'outil de photo
> hyperréaliste du poste et le seul module dont il a besoin. Le reste du module « Rendu 3D » de l'ERP Constructo AI
> (interface, facturation, manuel) n'est pas dans ce dépôt.

`photo_hyperrealiste.py` envoie UN rendu Blender à l'API Google Gemini et en rapporte une photo réaliste, avec la
même invite que le module « Rendu 3D » de l'ERP Constructo AI. Il n'a pas sa propre copie de l'invite : il charge
`ERP_REACT\backend\routers\gemini_image.py` et n'en remplace que le transport (bibliothèque standard de Python).

## Ce qu'il faut

- **Un compte Google et sa clé d'API Gemini**, créée sur `https://aistudio.google.com/apikey`. L'appel est payant,
  facturé par Google au compte de la clé : environ 0,24 $ US par image en qualité « pro » 4K.
- La clé se pose UNE fois, comme variable de l'utilisateur Windows, jamais dans un fichier. Dans PowerShell (saisie
  ainsi, elle ne reste pas dans l'historique des commandes) :
  `$cle = Read-Host 'Cle Gemini' ; [Environment]::SetEnvironmentVariable('GOOGLE_GEMINI_API_KEY', $cle, 'User')`.
- Pillow pour l'outil ; pytest, fastapi, pydantic et httpx pour ses essais (`requirements.txt`).

## Emploi

```
python photo_hyperrealiste.py rendu.png --sortie photo.png
       [--type exterior|interior|object|mechanical] [--qualite pro|standard|fast]
       [--resolution 1K|2K|4K] [--consigne "texte libre"] [--essai-a-blanc]
```

- `--essai-a-blanc` montre le modèle, la résolution, l'invite et le coût nominal, **sans rien envoyer** : à faire
  d'abord.
- **UNE seule image** en entrée. Le rendu Blender doit avoir un fond OPAQUE (un fond transparent sort noir en JPEG).
- **Toujours passer une `--consigne`** (2 000 caractères au plus, l'anglais donne les meilleurs résultats) qui décrit
  ce qu'il faut garder tel quel : sans elle, le modèle « améliore » les détails (portes, fenêtres, affiches). La
  recette qui marche : « garde le bâtiment EXACTEMENT », puis « fais de la scène une vraie photo » (végétation, gazon,
  ciel, textures). Gabarit éprouvé, à compléter : `Preserve the building exactly as rendered: same geometry,
  proportions, openings, colors and materials. Keep these details faithful: (1) … (2) … Turn the SETTING into a real
  photograph: real vegetation, lawn, sky, textures, reflections. Do not add or remove any element.`
- Compter les petits accessoires sur le résultat, et noter les libertés prises par l'IA dans une fiche à côté de
  la photo.

## Essais

`python -m pytest test_cao_rendu_domaine.py` : 13 essais hors ligne de l'invite, par domaine (aucun appel payant).
