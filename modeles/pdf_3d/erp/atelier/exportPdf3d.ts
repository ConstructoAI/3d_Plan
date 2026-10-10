/**
 * PDF 3D — un PDF ordinaire qui contient le batiment, manipulable dans le lecteur.
 *
 * CE QUE C'EST, TECHNIQUEMENT. Un PDF 3D n'a rien d'exotique : c'est un PDF normal dont une
 * page porte une annotation `/Subtype /3D`, laquelle pointe un flux `/Type /3D` contenant la
 * geometrie. Adobe Reader (depuis la version 7), PDF-XChange et Foxit savent la rendre : on
 * fait tourner le modele a la souris, on l'eclate, on le mesure.
 *
 * POURQUOI ON ECRIT LE PDF A LA MAIN plutot que d'utiliser jsPDF (deja present pour la mise en
 * plan) : jsPDF n'expose pas l'insertion d'un objet indirect arbitraire avec un flux binaire et
 * un dictionnaire `/Type /3D`. Se battre avec ses entrailles coute plus cher que d'ecrire les
 * quelque 200 lignes d'un PDF minimal — dont la structure est publique et stable depuis 1993.
 *
 * LE PIEGE DU FORMAT PDF, et il est unique : la table `xref` contient le DECALAGE EN OCTETS de
 * chaque objet depuis le debut du fichier. Une seule position fausse et le lecteur refuse le
 * document ENTIER, generalement sans dire laquelle. On construit donc le fichier en mesurant
 * les positions au fur et a mesure, jamais en les recalculant apres coup.
 *
 * ET LE PIEGE DES OCTETS : un PDF contenant un flux binaire n'est PAS du texte. Tout est
 * assemble en `Uint8Array` ; passer par une chaine JavaScript corromprait le U3D au premier
 * octet non-ASCII, silencieusement.
 *
 * CE QU'ON NE PEUT PAS VERIFIER ICI : qu'un lecteur l'affiche. Les tests controlent la
 * structure — objets, decalages, longueurs, dictionnaire de l'annotation — mais la preuve
 * finale est qu'un humain ouvre le fichier. C'est ecrit pour que « tests verts » ne se lise
 * jamais comme « ca marche ».
 */

import { buildU3D } from './u3dWriter';

/**
 * Encode UN OCTET PAR CARACTERE.
 *
 * On n'utilise PAS `TextEncoder` : il encode en UTF-8, ou « é » fait deux octets. Or la police
 * du PDF est declaree en `WinAnsiEncoding`, qui en attend UN — les deux octets d'UTF-8 y
 * seraient lus comme deux lettres, et « Modèle » s'afficherait « ModÃ¨le ». Le francais est la
 * langue du produit : ce n'est pas un detail cosmetique.
 *
 * C'est `litteral` (plus bas) qui garantit que chaque caractere restant tient sur un octet
 * WinAnsi — y compris la ponctuation typographique de la plage 0x80-0x9F, que WinAnsi peuple et
 * que Latin-1 laisse vide.
 */
function txt(s: string): Uint8Array {
  const out = new Uint8Array(s.length);
  for (let i = 0; i < s.length; i++) out[i] = s.charCodeAt(i) & 0xff;
  return out;
}

function concat(parts: readonly Uint8Array[]): Uint8Array {
  let n = 0;
  for (const p of parts) n += p.length;
  const out = new Uint8Array(n);
  let o = 0;
  for (const p of parts) { out.set(p, o); o += p.length; }
  return out;
}

export interface Pdf3dOptions {
  /** Titre affiche en haut de page. */
  readonly titre?: string;
  /** Lignes de texte sous le modele (quantites, projet, date...). */
  readonly lignes?: readonly string[];
  /** 1re ligne du message affiche PAR LES LECTEURS SANS 3D (et a l'impression). */
  readonly messageRepli?: string;
  /** 2e ligne du meme message. */
  readonly messageRepli2?: string;
}

/**
 * Le PDF ET ce qu'il contient vraiment.
 *
 * `faces` n'est PAS le nombre de triangles fournis : le dedoublonnage et le rejet des degeneres
 * font baisser le compte, parfois enormement (mesure de la QA : 100 triangles identiques donnent
 * UNE face). L'interface doit annoncer CE nombre-la, et `octets`, parce que c'est ce que
 * l'utilisateur va attacher a un courriel.
 */
export interface Pdf3dResultat {
  readonly pdf: Uint8Array;
  readonly faces: number;
  readonly sommets: number;
  readonly octets: number;
}

/**
 * WinAnsiEncoding EST LA PAGE DE CODES WINDOWS 1252, pas Latin-1 (ISO 32000-1, annexe D).
 *
 * J'avais ecrit l'inverse, et ca coutait 27 caracteres que la police sait pourtant rendre. Les
 * deux qui font mal en francais du Quebec : **l'apostrophe typographique `’`** (0x92 — celle que
 * produisent Word, les navigateurs et tout copier-coller : « L’etage » devenait « L etage ») et
 * **la ligature `œ`** (0x9C — « manœuvre » devenait « man uvre »). Sur un document envoye a un
 * client, ca se voit.
 *
 * Latin-1 laisse 0x80-0x9F vide ; CP1252 y loge la ponctuation typographique. C'est toute la
 * difference, et elle tombe exactement sur ce que le francais utilise.
 */
const WINANSI_80_9F: ReadonlyMap<string, number> = new Map([
  ['€', 0x80], ['‚', 0x82], ['ƒ', 0x83], ['„', 0x84],
  ['…', 0x85], ['†', 0x86], ['‡', 0x87], ['ˆ', 0x88],
  ['‰', 0x89], ['Š', 0x8a], ['‹', 0x8b], ['Œ', 0x8c],
  ['Ž', 0x8e], ['‘', 0x91], ['’', 0x92], ['“', 0x93],
  ['”', 0x94], ['•', 0x95], ['–', 0x96], ['—', 0x97],
  ['˜', 0x98], ['™', 0x99], ['š', 0x9a], ['›', 0x9b],
  ['œ', 0x9c], ['ž', 0x9e], ['Ÿ', 0x9f],
]);

/**
 * Echappe une chaine pour un litteral PDF `( ... )` et la ramene dans WinAnsi.
 *
 * Deux choses distinctes, a ne pas confondre : `\ ( )` sont des caracteres de SYNTAXE du PDF et
 * doivent etre echappes, sinon le document entier devient illisible ; ce qui n'existe pas dans
 * la police devient une ESPACE — une degradation choisie, jamais un glyphe au hasard.
 */
function litteral(s: string): string {
  let out = '';
  for (const c of s) {
    if (c === '\\' || c === '(' || c === ')') { out += `\\${c}`; continue; }
    const cp1252 = WINANSI_80_9F.get(c);
    if (cp1252 !== undefined) { out += String.fromCharCode(cp1252); continue; }
    const n = c.codePointAt(0) ?? 0;
    out += (n >= 0x20 && n <= 0x7e) || (n >= 0xa0 && n <= 0xff) ? c : ' ';
  }
  return out;
}

/**
 * Largeurs Helvetica (millièmes de cadratin), ASCII 32-126 — les metriques officielles des 14
 * polices de base. Sert a NE PAS ECRIRE HORS DE LA PAGE : un titre de 90 caracteres larges
 * mesure 1 199 pt sur une page qui en fait 842, et sortait par le bord droit sans un mot.
 */
const W_HELV = [
  // 0x20-0x7E
  278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278,
  556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556,
  1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778,
  667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556,
  333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556,
  556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584,
  // 0x7F (non imprimable, jamais atteint — remplit l'indice)
  0,
  // 0x80-0xFF : LA PLAGE QUE JE FACTURAIS 556 EN BLOC, ET C'ETAIT LA PLUS CHERE.
  556, 556, 222, 556, 333, 1000, 556, 556, 333, 1000, 667, 333, 1000, 556, 611, 556,
  556, 222, 222, 333, 333, 350, 556, 1000, 333, 1000, 500, 333, 944, 556, 500, 667,
  278, 333, 556, 556, 556, 556, 260, 556, 333, 737, 370, 556, 584, 333, 737, 333,
  400, 584, 333, 333, 333, 556, 537, 278, 333, 333, 365, 556, 834, 834, 834, 611,
  667, 667, 667, 667, 667, 667, 1000, 722, 667, 667, 667, 667, 278, 278, 278, 278,
  722, 722, 778, 778, 778, 778, 778, 584, 778, 722, 722, 722, 722, 667, 667, 611,
  556, 556, 556, 556, 556, 556, 889, 500, 556, 556, 556, 556, 278, 278, 278, 278,
  556, 556, 556, 556, 556, 556, 556, 584, 611, 556, 556, 556, 556, 500, 556, 500,
];

/**
 * Largeur d'une chaine DEJA echappee, en points.
 *
 * ⚠️ CE QUE J'AVAIS ECRIT ICI ETAIT FAUX : « les caracteres accentues prennent 556, l'ecart avec
 * la vraie metrique est sans effet sur une TRONCATURE ». **88 des 128 codets de 0x80-0xFF ont une
 * autre largeur**, jusqu'a **1000** — le tiret cadratin `—`, les points de suspension `…`, `Œ`,
 * `™`, `‰`. Mesure : un titre de 200 tirets cadratins finissait a x = 856 sur une page large de
 * 842, soit **14 points HORS PAGE** ; et un titre francais realiste
 * (« Amenagement — Residence Tremblay — Etage 2 — … ») debordait deja d'un point.
 *
 * ET LES DEUX CORRECTIONS INTERAGISSAIENT : c'est en ouvrant la plage 0x80-0x9F a la ponctuation
 * typographique (pour sauver `’` et `œ`) que j'ai ELARGI l'ensemble des caracteres que cette
 * table chiffrait faux. Une correction peut armer le defaut d'une autre.
 */
function largeur(s: string, taille: number): number {
  let m = 0;
  for (let i = 0; i < s.length; i++) {
    const c = s.charCodeAt(i);
    m += c >= 32 && c <= 255 ? W_HELV[c - 32] : 556;
  }
  return (m * taille) / 1000;
}

/** Tronque pour tenir dans `max` points. Rend la chaine ECHAPPEE prete a l'emploi. */
function tronqueA(brut: string, taille: number, max: number): string {
  let s = litteral(brut);
  if (largeur(s, taille) <= max) return s;
  while (s.length > 1 && largeur(`${s}...`, taille) > max) {
    // Ne jamais couper entre une contre-oblique et le caractere qu'elle echappe : le litteral
    // deviendrait `(...\)` et la parenthese fermante du PDF serait mangee.
    //
    // LES DEUX BRANCHES SONT EXCLUSIVES, et elles ne l'etaient pas. Quand la chaine finissait par
    // une PAIRE `\\`, le `slice(0, -2)` la retirait deja correctement — puis un second retrait
    // mordait sur la paire precedente et laissait une contre-oblique ORPHELINE. Mesure : defaut
    // a N ≡ 1 (mod 3) contre-obliques, soit 7 cas sur 21 essais. Le PDF restait valide, mais un
    // caractere etait mange et pypdf signalait « Unexpected escaped string ».
    if (s.endsWith('\\\\')) {
      s = s.slice(0, -2);
    } else {
      s = s.slice(0, -1);
      if (s.endsWith('\\')) s = s.slice(0, -1);
    }
  }
  return `${s}...`;
}

/**
 * Construit un PDF 3D a partir de triangles.
 *
 * @param sommets Coordonnees XYZ, trois par sommet, trois sommets par triangle, dans le repere
 *                du MODELE (Y vers le haut, comme three.js). **La conversion vers le Z-up du
 *                U3D est faite par `buildU3D`** — j'avais d'abord ecrit qu'il n'y en avait
 *                aucune, et fige cette erreur dans un test en la croyant deliberee.
 */
export function buildPdf3d(sommets: Float32Array, options: Pdf3dOptions = {}): Pdf3dResultat | null {
  const res = buildU3D(sommets, { nom: options.titre || 'Modele' });
  if (!res) return null;
  const u3d = res.fichier;

  // Page A4 paysage. Le cadre 3D occupe le haut, le texte le bas.
  const L = 842; const H = 595;
  const cadre = { x: 40, y: 132, w: L - 80, h: H - 190 };
  const yTexte = cadre.y - 24;          // 1re ligne de texte sous le cadre
  const MARGE_BAS = 30;

  const titre = tronqueA(options.titre || 'Modele 3D', 16, L - 80);
  // LE NOMBRE DE LIGNES SE DEDUIT DE LA GEOMETRIE, il ne se decrete pas. Il etait plafonne a 12
  // alors que seules 10 tenaient : les lignes 11 et 12 etaient ecrites a y = -2 et y = -15,
  // c'est-a-dire SOUS LA PAGE. Mesure : la 12e n'apparaissait meme pas a l'extraction de texte.
  // Sur un export de quantites, la ligne perdue est un montant.
  const maxLignes = Math.max(1, Math.floor((yTexte - MARGE_BAS) / 13) + 1);
  const lignes = (options.lignes || [])
    .slice(0, maxLignes)
    .map((l) => tronqueA(l, 9, L - 80));

  // Contenu de page : titre, cadre, lignes. Le modele n'est PAS dessine ici — c'est l'annotation
  // qui l'affiche par-dessus, a l'emplacement du cadre.
  let flux = `BT /F1 16 Tf 40 ${H - 40} Td (${titre}) Tj ET\n`;
  flux += `0.6 w 0.75 G ${cadre.x} ${cadre.y} ${cadre.w} ${cadre.h} re S\n`;
  lignes.forEach((l, i) => {
    flux += `BT /F1 9 Tf 40 ${yTexte - i * 13} Td (${l}) Tj ET\n`;
  });
  const fluxOctets = txt(flux);

  // L'APPARENCE DE REPLI (`/AP`), ET ELLE N'EST PAS FACULTATIVE.
  //
  // ISO 32000-1 §13.6.2 : « a 3D annotation **shall** provide an appearance stream in its AP
  // entry […] used by applications that do not support 3D annotations and by all applications
  // for the initial display ». Je ne l'avais pas ecrite, et la QA a mesure le prix : dans le
  // rectangle de l'annotation, **0,588 % de pixels non blancs** — le filet du cadre, rien
  // d'autre. Autrement dit, TOUT lecteur sans moteur 3D (apercu Windows, Apercu du Mac, Chrome,
  // Firefox, les vignettes, **et toute impression**) montrait un rectangle BLANC.
  //
  // Le PDF s'ouvrait sans erreur : l'utilisateur en aurait conclu que l'export avait echoue —
  // ou, pire, aurait envoye une page blanche a un client. Les deux implementations de reference
  // du U3D-dans-PDF (`movie15.sty`, `media9.sty`) en posent une systematiquement.
  // TRONQUES COMME LE RESTE. Ils ne l'etaient pas, et c'etait le pire endroit pour l'oublier :
  // ce message est la SEULE chose que `/AP` existe pour garantir. Mesure : a 400 caracteres, le
  // `Td` de centrage partait a x = -963, donc hors de la BBox — le message disparaissait. Les
  // chaines FR/EN livrees ont 347 a 488 points de marge, mais une traduction plus longue aurait
  // casse en silence exactement ce qu'on venait de reparer.
  const msg = tronqueA(options.messageRepli
    || 'Modele 3D — ouvrez ce fichier avec Adobe Acrobat Reader, PDF-XChange ou Foxit,',
  11, cadre.w - 40);
  const msg2 = tronqueA(options.messageRepli2
    || 'puis cliquez ici pour l’activer et le faire pivoter a la souris.', 11, cadre.w - 40);
  const apFlux = txt(
    `0.97 g 0 0 ${cadre.w} ${cadre.h} re f\n`
    + `BT /F1 11 Tf 0.35 g ${Math.round(cadre.w / 2 - largeur(msg, 11) / 2)} `
    + `${Math.round(cadre.h / 2 + 4)} Td (${msg}) Tj ET\n`
    + `BT /F1 11 Tf 0.35 g ${Math.round(cadre.w / 2 - largeur(msg2, 11) / 2)} `
    + `${Math.round(cadre.h / 2 - 12)} Td (${msg2}) Tj ET\n`);

  // --- Objets, dans l'ordre ou ils seront ecrits -------------------------------------------
  //  1 Catalog · 2 Pages · 3 Page · 4 Contenu · 5 Police · 6 Flux 3D · 7 Annotation · 8 Vue
  //  9 Apparence de repli (form XObject)
  const objets: Uint8Array[] = [];
  const push = (s: string, binaire?: Uint8Array): void => {
    objets.push(binaire ? concat([txt(s), binaire, txt('\nendstream\nendobj\n')]) : txt(s));
  };

  push('1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n');
  push('2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n');
  push(`3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${L} ${H}] `
     + '/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R /Annots [7 0 R] >>\nendobj\n');
  push(`4 0 obj\n<< /Length ${fluxOctets.length} >>\nstream\n`, fluxOctets);
  // `/Encoding /WinAnsiEncoding` : sans lui, la police retombe sur StandardEncoding, ou les
  // accents francais n'existent pas et sortent en caracteres arbitraires.
  push('5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica '
     + '/Encoding /WinAnsiEncoding >>\nendobj\n');
  // LE FLUX 3D. `/Subtype /U3D` est ce qui distingue ce PDF d'un PDF ordinaire ; l'echantillon
  // SpinFire utilise `/PRC` au meme endroit — meme structure, autre format de geometrie.
  // `/VA` LISTE LES VUES et `/DV` designe celle qui s'ouvre. Sans `/VA`, la spec (p. 513) veut
  // que `/3DV` designe « one of the 3D view dictionaries listed in the VA entry » — une liste
  // VIDE : la vue nommee n'apparaissait donc pas dans le panneau Vues du lecteur, qui se peuple
  // depuis `/VA`. `movie15.sty` emet toujours les deux ; on fait pareil.
  push(`6 0 obj\n<< /Type /3D /Subtype /U3D /VA [8 0 R] /DV 8 0 R `
     + `/Length ${u3d.length} >>\nstream\n`, u3d);
  // L'ANNOTATION. `/3DD` pointe le flux, `/3DV` la vue, `/AP` l'apparence de repli.
  //
  // `/3DA << /A /PV /D /PI >>` = activer des que la page devient visible, desactiver quand elle
  // ne l'est plus. **`/TB false` a ete RETIRE** : il supprimait la barre d'outils 3D — c'est-a-dire
  // precisement ce qui REVELE a l'utilisateur que le modele se manipule. Son defaut est `true`,
  // et l'ecrire a `false` allait contre le but affiche du bouton. (`/NP false` etant deja le
  // defaut, l'ecrire ne servait a rien non plus ; les deux etaient de surcroit des clefs PDF 1.7
  // sous un en-tete 1.6.)
  push(`7 0 obj\n<< /Type /Annot /Subtype /3D /3DD 6 0 R /3DV 8 0 R `
     + '/3DA << /A /PV /D /PI >> /AP << /N 9 0 R >> '
     + `/P 3 0 R /F 4 /Rect [${cadre.x} ${cadre.y} ${cadre.x + cadre.w} ${cadre.y + cadre.h}] >>\nendobj\n`);
  // LA VUE PAR DEFAUT — et deux corrections que la norme impose.
  //
  // (1) **`/MS /U3D` a ete RETIRE.** Table 304 : `U3DPath` est « Required if the value of MS is
  //     U3D ». Je declarais donc « la matrice est dans un nœud de vue » sans jamais donner le
  //     chemin de ce nœud. Or la meme table dit que si `MS` est OMIS, « the view specified in
  //     the 3D artwork shall be used » — c'est-a-dire EXACTEMENT le cadrage automatique que mon
  //     propre commentaire disait vouloir. Le code contredisait son commentaire.
  // (2) **`/Subtype /Perspective` -> `/Subtype /P`.** Table 305 : « Valid values shall be O
  //     (orthographic) or P (perspective) ». Le piege est reperable : la table VOISINE decrit le
  //     defaut en PROSE (« a projection dictionary where the value of Subtype is Perspective »),
  //     et j'ai recopie de la prose comme un nom PDF. Consequence silencieuse : `FOV` n'etant
  //     lu que « if Subtype is P », mon `/FOV 45` etait IGNORE et le lecteur retombait sur 90 —
  //     le batiment s'ouvrait en grand-angle, deforme, sans que rien n'echoue.
  push('8 0 obj\n<< /Type /3DView /XN (Vue par defaut) /IN (Vue par defaut) '
     + '/P << /Subtype /P /FOV 45 /PS /Min >> >>\nendobj\n');
  push(`9 0 obj\n<< /Type /XObject /Subtype /Form /FormType 1 `
     + `/BBox [0 0 ${cadre.w} ${cadre.h}] `
     + `/Resources << /Font << /F1 5 0 R >> >> /Length ${apFlux.length} >>\nstream\n`, apFlux);

  // --- Assemblage, en MESURANT les positions au fur et a mesure -----------------------------
  const entete = txt('%PDF-1.6\n%\xE2\xE3\xCF\xD3\n');
  const morceaux: Uint8Array[] = [entete];
  const positions: number[] = [];
  let curseur = entete.length;
  for (const o of objets) {
    positions.push(curseur);
    morceaux.push(o);
    curseur += o.length;
  }

  // `/ID` : deux chaines identiques derivees du CONTENU (FNV-1a sur le U3D et le titre). La norme
  // le dit « strongly recommended » en 1.6 et le REND obligatoire en PDF 2.0 et en PDF/A. Derive
  // du contenu plutot que d'une horloge : deux exports du meme modele donnent le meme fichier,
  // ce qui rend les tests reproductibles.
  let h = 0x811c9dc5;
  const melange = (x: number): void => { h = Math.imul(h ^ x, 0x01000193) >>> 0; };
  for (let i = 0; i < u3d.length; i += 97) melange(u3d[i]);
  for (let i = 0; i < titre.length; i++) melange(titre.charCodeAt(i));
  melange(u3d.length); melange(res.faces);
  const id = (h >>> 0).toString(16).padStart(8, '0').repeat(4);

  const n = objets.length + 1;
  let xref = `xref\n0 ${n}\n0000000000 65535 f \n`;
  for (const p of positions) xref += `${String(p).padStart(10, '0')} 00000 n \n`;
  xref += `trailer\n<< /Size ${n} /Root 1 0 R /ID [<${id}> <${id}>] >>\n`
        + `startxref\n${curseur}\n%%EOF\n`;
  morceaux.push(txt(xref));

  const pdf = concat(morceaux);
  return { pdf, faces: res.faces, sommets: res.sommets, octets: pdf.length };
}
