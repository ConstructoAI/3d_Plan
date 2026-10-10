/**
 * PDF 3D « DE FABRICATION » — la variante de exportPdf3d.ts (ERP) pour un atelier.
 *
 * MEME PAGE que l'ERP (A4 paysage, titre, cadre, lignes, MEME apparence de repli `/AP`), et ce qui
 * lui manque pour qu'un fabricant s'en serve :
 *   - PLUSIEURS VUES nommees dans `/VA`, chacune avec sa camera (`/MS /M`, `/C2W`, `/CO`), sa
 *     projection, son fond, son mode de rendu (`/RM`) et son eclairage (`/LS`) ; une vue peut
 *     aussi masquer des nœuds (`/NA`) : « isoler la volee V1 » devient un clic ;
 *   - l'ARBRE DU MODELE demande a l'activation (`/3DA /NP true`) ;
 *   - le flux 3D compresse (`/FlateDecode`) : les memes octets, un fichier deux a trois fois
 *     plus leger a envoyer par courriel ;
 *   - la page affichee EN ENTIER a l'ouverture (`/OpenAction [… /Fit]`) ;
 *   - les PROPRIETES du document (`/Info` : titre, auteur, sujet), que l'ERP n'ecrit pas : ce
 *     que montre « Fichier > Proprietes » du lecteur. Rien d'autre n'y est ecrit (ni outil,
 *     ni date) : deux exports du meme modele restent le meme fichier.
 * Le U3D lui-meme vient de u3dWriterMulti.ts : ce module-ci ne fabrique que la coquille PDF.
 *
 * POURQUOI LES AUXILIAIRES SONT RECOPIES. `txt`, `litteral`, `largeur`, `tronqueA` et la table
 * des largeurs d'Helvetica vivent dans exportPdf3d.ts SANS etre exportes, et ce fichier-la doit
 * rester une copie inchangee de l'ERP. Ils sont donc repris ici a l'identique. Le banc
 * (noeud/banc_multi.mjs) le PROUVE au lieu de le promettre : pour les memes titre, lignes et
 * messages, le flux de la page et celui de l'apparence de repli sortent identiques A L'OCTET a
 * ceux de l'ERP.
 *
 * LES REPERES, relus dans ISO 32000-1 (PDF 1.7), §13.6.5 :
 *   - la camera d'un PDF est a l'origine, x a droite, y en haut, et REGARDE VERS +z ;
 *   - une matrice 3D s'ecrit en 12 nombres [a b c d e f g h i tx ty tz], vecteurs LIGNES :
 *     `/C2W` = [droite, haut, regard, position] de la camera, exprimes dans le monde ;
 *   - dans un monde direct (celui du U3D), (droite, haut, regard) est donc un triedre INDIRECT :
 *     determinant -1. Un `/C2W` direct donne une image en miroir, sans un message.
 *   - `/CO` : distance de la camera au centre d'orbite, le long de son axe z.
 * LA PROJECTION (Table 305) : `/Subtype /P` avec `/FOV` en degres, le cone du champ couvrant la
 * plus petite dimension du cadre (`/PS /Min`) ; ou `/Subtype /O` avec `/OB /Min` et
 * `/OS` = 1 / etendue, l'etendue etant ce que la plus petite dimension du cadre doit couvrir.
 *
 * CE QU'ON NE PEUT PAS VERIFIER ICI : qu'un lecteur l'affiche. Voir voir_dans_lecteur.ps1.
 *
 * PUR : aucune dependance, aucun import. La compression est une fonction donnee par l'appelant.
 */

/** Un octet par caractere (la police de la page est en WinAnsi) — repris de exportPdf3d.ts. */
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

/** WinAnsi = Windows 1252 : la ponctuation typographique de 0x80-0x9F — repris de exportPdf3d.ts. */
const WINANSI_80_9F: ReadonlyMap<string, number> = new Map([
  ['€', 0x80], ['‚', 0x82], ['ƒ', 0x83], ['„', 0x84],
  ['…', 0x85], ['†', 0x86], ['‡', 0x87], ['ˆ', 0x88],
  ['‰', 0x89], ['Š', 0x8a], ['‹', 0x8b], ['Œ', 0x8c],
  ['Ž', 0x8e], ['‘', 0x91], ['’', 0x92], ['“', 0x93],
  ['”', 0x94], ['•', 0x95], ['–', 0x96], ['—', 0x97],
  ['˜', 0x98], ['™', 0x99], ['š', 0x9a], ['›', 0x9b],
  ['œ', 0x9c], ['ž', 0x9e], ['Ÿ', 0x9f],
]);

/** Echappe pour un litteral PDF `( … )` et ramene dans WinAnsi — repris de exportPdf3d.ts. */
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

/** Largeurs Helvetica (milliemes de cadratin), 0x20 a 0xFF — reprises de exportPdf3d.ts. */
const W_HELV = [
  278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278,
  556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556,
  1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778,
  667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556,
  333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556,
  556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584,
  0,
  556, 556, 222, 556, 333, 1000, 556, 556, 333, 1000, 667, 333, 1000, 556, 611, 556,
  556, 222, 222, 333, 333, 350, 556, 1000, 333, 1000, 500, 333, 944, 556, 500, 667,
  278, 333, 556, 556, 556, 556, 260, 556, 333, 737, 370, 556, 584, 333, 737, 333,
  400, 584, 333, 333, 333, 556, 537, 278, 333, 333, 365, 556, 834, 834, 834, 611,
  667, 667, 667, 667, 667, 667, 1000, 722, 667, 667, 667, 667, 278, 278, 278, 278,
  722, 722, 778, 778, 778, 778, 778, 584, 778, 722, 722, 722, 722, 667, 667, 611,
  556, 556, 556, 556, 556, 556, 889, 500, 556, 556, 556, 556, 278, 278, 278, 278,
  556, 556, 556, 556, 556, 556, 556, 584, 611, 556, 556, 556, 556, 500, 556, 500,
];

/** Largeur d'une chaine DEJA echappee, en points — repris de exportPdf3d.ts. */
function largeur(s: string, taille: number): number {
  let m = 0;
  for (let i = 0; i < s.length; i++) {
    const c = s.charCodeAt(i);
    m += c >= 32 && c <= 255 ? W_HELV[c - 32] : 556;
  }
  return (m * taille) / 1000;
}

/** Tronque pour tenir dans `max` points ; rend la chaine echappee — repris de exportPdf3d.ts. */
function tronqueA(brut: string, taille: number, max: number): string {
  let s = litteral(brut);
  if (largeur(s, taille) <= max) return s;
  while (s.length > 1 && largeur(`${s}...`, taille) > max) {
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
 * Une « text string » PDF (nom de vue, nom de nœud). En ASCII imprimable : un litteral echappe.
 * Sinon : UTF-16 gros-boutiste avec sa marque d'ordre, en hexadecimal (ISO 32000-1 §7.9.2.2).
 * C'est ce qui permet au lecteur de retrouver dans le U3D (UTF-8) un nœud nomme « Garde-corps
 * coté cour » : Table 312 demande au lecteur de traduire entre les deux encodages.
 */
function textePdf(s: string): string {
  let ascii = true;
  for (let i = 0; i < s.length; i++) {
    const c = s.charCodeAt(i);
    if (c < 0x20 || c > 0x7e) { ascii = false; break; }
  }
  if (ascii) return `(${s.replace(/([\\()])/g, '\\$1')})`;
  let h = 'FEFF';
  for (let i = 0; i < s.length; i++) h += s.charCodeAt(i).toString(16).toUpperCase().padStart(4, '0');
  return `<${h}>`;
}

/** Un nombre PDF : pas d'exposant, six decimales au plus, pas de « -0 ». */
function num(x: number): string {
  if (!Number.isFinite(x)) throw new Error(`nombre non fini dans le PDF : ${x}`);
  const s = x.toFixed(6).replace(/\.?0+$/, '');
  return s === '-0' ? '0' : s;
}

export interface NoeudVue {
  /** Nom du nœud, tel qu'ecrit dans le U3D. */
  readonly nom: string;
  readonly visible?: boolean;
  /** 0 a 1. */
  readonly opacite?: number;
}

export interface VuePdf3d {
  /** Nom montre dans le menu des vues du lecteur. */
  readonly nom: string;
  /** [droite(3), haut(3), regard(3), position(3)] de la camera, dans le monde.
   *  ABSENT : la vue n'impose pas de camera et le lecteur cadre lui-meme (ISO 32000-1, Table 304 :
   *  sans `/MS`, « the view specified in the 3D artwork shall be used ») — c'est ce que fait l'ERP. */
  readonly c2w?: readonly number[];
  /** Distance de la camera au centre d'orbite (> 0) ; requise avec `c2w`. */
  readonly co?: number;
  /** 'P' perspective (avec `fov`), 'O' orthographique (avec `etendueOrtho`). */
  readonly projection: 'P' | 'O';
  /** Champ en degres, sur la plus petite dimension du cadre. */
  readonly fov?: number;
  /** Etendue (en unites du modele) que couvre la plus petite dimension du cadre. */
  readonly etendueOrtho?: number;
  /** Nœuds dont la vue fixe la visibilite ou l'opacite ; les autres restent comme dans le modele. */
  readonly noeuds?: readonly NoeudVue[];
  /** Mode de rendu de cette vue (defaut : celui des options). */
  readonly rendu?: string;
  /** Eclairage de cette vue (defaut : celui des options). */
  readonly eclairage?: string;
}

export interface Pdf3dMultiOptions {
  readonly titre?: string;
  readonly lignes?: readonly string[];
  readonly messageRepli?: string;
  readonly messageRepli2?: string;
  /** Au moins une vue. */
  readonly vues: readonly VuePdf3d[];
  /** Rang (a partir de 0) de la vue d'ouverture. */
  readonly vueDefaut?: number;
  /** Table 308 : Solid, SolidOutline, Illustration, ShadedIllustration, SolidWireframe… */
  readonly rendu?: string;
  /** Table 310 : CAD, Day, White, Headlamp, Hard, Artwork… */
  readonly eclairage?: string;
  /** Fond du cadre 3D, rouge vert bleu entre 0 et 1. */
  readonly fond?: readonly [number, number, number];
  /** Demander l'arbre du modele a l'activation (`/NP true`). */
  readonly arbreOuvert?: boolean;
  /** Compresseur zlib (RFC 1950). Absent : le flux 3D est ecrit tel quel, comme l'ERP. */
  readonly deflate?: (octets: Uint8Array) => Uint8Array;
  /** Faces annoncees a l'appelant (pour l'empreinte `/ID`). */
  readonly faces?: number;
  /** Proprietes du document (`/Info`). Une valeur vide ou absente n'est pas ecrite ; sans
   *  aucune valeur, le PDF n'a pas de `/Info` du tout (comme celui de l'ERP). */
  readonly proprietes?: {
    readonly titre?: string;
    readonly auteur?: string;
    readonly sujet?: string;
  };
}

export interface Pdf3dMultiResultat {
  readonly pdf: Uint8Array;
  readonly octets: number;
  /** Octets du flux 3D tel qu'ecrit (compresse ou non). */
  readonly octetsFlux: number;
  readonly vues: number;
}

const MODES_RENDU = new Set(['Solid', 'SolidWireframe', 'Transparent', 'TransparentWireframe',
  'BoundingBox', 'TransparentBoundingBox', 'TransparentBoundingBoxOutline', 'Wireframe',
  'ShadedWireframe', 'HiddenWireframe', 'Vertices', 'ShadedVertices', 'Illustration',
  'SolidOutline', 'ShadedIllustration']);
const ECLAIRAGES = new Set(['Artwork', 'None', 'White', 'Day', 'Night', 'Hard', 'Primary', 'Blue',
  'Red', 'Cube', 'CAD', 'Headlamp']);

/**
 * Construit le PDF autour d'un fichier U3D deja ecrit.
 *
 * @param u3d le fichier U3D complet (u3dWriterMulti.buildU3DMulti, ou tout autre U3D valide).
 */
export function buildPdf3dMulti(u3d: Uint8Array, options: Pdf3dMultiOptions): Pdf3dMultiResultat {
  if (!u3d || u3d.length < 12) throw new Error('U3D vide');
  if (!options.vues || options.vues.length < 1) throw new Error('au moins une vue est requise');
  const rendu = options.rendu ?? 'Solid';
  const eclairage = options.eclairage ?? 'CAD';
  const fond = options.fond ?? [0.96, 0.96, 0.97];
  for (const v of fond) if (!(v >= 0 && v <= 1)) throw new Error('fond : trois nombres entre 0 et 1');
  const iDefaut = options.vueDefaut ?? 0;
  if (!Number.isInteger(iDefaut) || iDefaut < 0 || iDefaut >= options.vues.length) throw new Error(`vue d'ouverture ${iDefaut} hors de la liste`);

  // ---- la page : les MEMES mesures que exportPdf3d.ts -------------------------------------
  const L = 842; const H = 595;
  const cadre = { x: 40, y: 132, w: L - 80, h: H - 190 };
  const yTexte = cadre.y - 24;
  const MARGE_BAS = 30;
  const titre = tronqueA(options.titre || 'Modele 3D', 16, L - 80);
  const maxLignes = Math.max(1, Math.floor((yTexte - MARGE_BAS) / 13) + 1);
  const lignes = (options.lignes || []).slice(0, maxLignes).map((l) => tronqueA(l, 9, L - 80));
  let flux = `BT /F1 16 Tf 40 ${H - 40} Td (${titre}) Tj ET\n`;
  flux += `0.6 w 0.75 G ${cadre.x} ${cadre.y} ${cadre.w} ${cadre.h} re S\n`;
  lignes.forEach((l, i) => {
    flux += `BT /F1 9 Tf 40 ${yTexte - i * 13} Td (${l}) Tj ET\n`;
  });
  const fluxOctets = txt(flux);

  // ---- l'apparence de repli : la MEME que l'ERP (ISO 32000-1 §13.6.2 : elle est obligatoire) --
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

  // ---- les vues -----------------------------------------------------------------------------
  //  1 Catalog · 2 Pages · 3 Page · 4 Contenu · 5 Police · 6 Flux 3D · 7 Annotation
  //  8 Apparence de repli · 9… une vue par objet
  const PREMIERE_VUE = 9;
  const vues: string[] = [];
  options.vues.forEach((v, i) => {
    if (!v.nom) throw new Error(`vue ${i + 1} sans nom`);
    if (v.c2w !== undefined) {
      if (v.c2w.length !== 12) throw new Error(`vue « ${v.nom} » : /C2W demande 12 nombres`);
      if (!(v.co !== undefined && v.co > 0)) throw new Error(`vue « ${v.nom} » : /CO doit etre positif`);
    }
    const r = v.rendu ?? rendu;
    const e = v.eclairage ?? eclairage;
    if (!MODES_RENDU.has(r)) throw new Error(`vue « ${v.nom} » : mode de rendu « ${r} » inconnu de la norme (Table 308)`);
    if (!ECLAIRAGES.has(e)) throw new Error(`vue « ${v.nom} » : eclairage « ${e} » inconnu de la norme (Table 310)`);
    let p: string;
    if (v.projection === 'O') {
      if (!(v.etendueOrtho !== undefined && v.etendueOrtho > 0)) throw new Error(`vue « ${v.nom} » : etendue orthographique manquante`);
      p = `<< /Subtype /O /OB /Min /OS ${num(1 / v.etendueOrtho)} >>`;
    } else {
      const fov = v.fov ?? 30;
      if (!(fov > 0 && fov < 180)) throw new Error(`vue « ${v.nom} » : champ ${fov} hors de ]0, 180[`);
      p = `<< /Subtype /P /FOV ${num(fov)} /PS /Min >>`;
    }
    let d = `${PREMIERE_VUE + i} 0 obj\n<< /Type /3DView /XN ${textePdf(v.nom)} /IN ${textePdf(`vue${i + 1}`)} `
      + (v.c2w !== undefined ? `/MS /M /C2W [${v.c2w.map(num).join(' ')}] /CO ${num(v.co as number)}\n` : '\n')
      + `/P ${p}\n`
      + `/BG << /Type /3DBG /Subtype /SC /CS /DeviceRGB /C [${fond.map(num).join(' ')}] >>\n`
      + `/RM << /Type /3DRenderMode /Subtype /${r} >> /LS << /Type /3DLightingScheme /Subtype /${e} >>`;
    if (v.noeuds && v.noeuds.length) {
      // `/NR true` : repartir de l'etat du modele avant d'appliquer `/NA` (Table 304), sinon une
      // vue « tout montrer » appelee apres une vue « isoler » ne remontrerait rien.
      d += '\n/NR true /NA [';
      for (const n of v.noeuds) {
        d += `\n<< /Type /3DNode /N ${textePdf(n.nom)}`;
        if (n.visible !== undefined) d += ` /V ${n.visible ? 'true' : 'false'}`;
        if (n.opacite !== undefined) d += ` /O ${num(n.opacite)}`;
        d += ' >>';
      }
      d += ']';
    } else {
      d += ' /NR true';
    }
    d += ' >>\nendobj\n';
    vues.push(d);
  });
  const refsVues = options.vues.map((_, i) => `${PREMIERE_VUE + i} 0 R`).join(' ');
  const refDefaut = `${PREMIERE_VUE + iDefaut} 0 R`;

  // ---- le flux 3D ---------------------------------------------------------------------------
  let corps3d = u3d;
  let filtre = '';
  if (options.deflate) {
    const z = options.deflate(u3d);
    if (z && z.length > 0 && z.length < u3d.length) { corps3d = z; filtre = ' /Filter /FlateDecode'; }
  }

  const objets: Uint8Array[] = [];
  const push = (s: string, binaire?: Uint8Array): void => {
    objets.push(binaire ? concat([txt(s), binaire, txt('\nendstream\nendobj\n')]) : txt(s));
  };
  // `/OpenAction … /Fit` : la page entiere, cadre 3D et lignes, des l'ouverture.
  push('1 0 obj\n<< /Type /Catalog /Pages 2 0 R /OpenAction [3 0 R /Fit] /PageLayout /SinglePage '
     + '/Lang (fr-CA) >>\nendobj\n');
  push('2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n');
  push(`3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${L} ${H}] `
     + '/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R /Annots [7 0 R] >>\nendobj\n');
  push(`4 0 obj\n<< /Length ${fluxOctets.length} >>\nstream\n`, fluxOctets);
  push('5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica '
     + '/Encoding /WinAnsiEncoding >>\nendobj\n');
  push(`6 0 obj\n<< /Type /3D /Subtype /U3D /VA [${refsVues}] /DV ${refDefaut}${filtre} `
     + `/Length ${corps3d.length} >>\nstream\n`, corps3d);
  // L'ANNOTATION. `/A /PV` : activer des que la page est visible ; `/TB true` : la barre d'outils
  // 3D (c'est elle qui revele que le modele se manipule) ; `/NP true` : l'arbre du modele.
  push(`7 0 obj\n<< /Type /Annot /Subtype /3D /3DD 6 0 R /3DV ${refDefaut} `
     + `/3DA << /A /PV /D /PI /TB true /NP ${options.arbreOuvert === false ? 'false' : 'true'} >> `
     + '/AP << /N 8 0 R >> '
     + `/P 3 0 R /F 4 /Rect [${cadre.x} ${cadre.y} ${cadre.x + cadre.w} ${cadre.y + cadre.h}] >>\nendobj\n`);
  push(`8 0 obj\n<< /Type /XObject /Subtype /Form /FormType 1 `
     + `/BBox [0 0 ${cadre.w} ${cadre.h}] `
     + `/Resources << /Font << /F1 5 0 R >> >> /Length ${apFlux.length} >>\nstream\n`, apFlux);
  for (const d of vues) push(d);
  // LES PROPRIETES, en DERNIER objet : les numeros des objets qui precedent ne bougent pas.
  const pr = options.proprietes ?? {};
  const champs: string[] = [];
  if (pr.titre) champs.push(`/Title ${textePdf(pr.titre)}`);
  if (pr.auteur) champs.push(`/Author ${textePdf(pr.auteur)}`);
  if (pr.sujet) champs.push(`/Subject ${textePdf(pr.sujet)}`);
  const numInfo = champs.length ? PREMIERE_VUE + vues.length : 0;
  if (numInfo) push(`${numInfo} 0 obj\n<< ${champs.join('\n')} >>\nendobj\n`);

  // ---- assemblage, en MESURANT les positions au fur et a mesure ----------------------------
  // En-tete 1.7 : `/RM`, `/LS`, `/NA`, `/TB` et `/NP` sont des cles de PDF 1.7.
  const entete = txt('%PDF-1.7\n%\xE2\xE3\xCF\xD3\n');
  const morceaux: Uint8Array[] = [entete];
  const positions: number[] = [];
  let curseur = entete.length;
  for (const o of objets) {
    positions.push(curseur);
    morceaux.push(o);
    curseur += o.length;
  }
  // `/ID` derive du CONTENU (FNV-1a), comme l'ERP : deux exports du meme modele = le meme fichier.
  let h = 0x811c9dc5;
  const melange = (x: number): void => { h = Math.imul(h ^ x, 0x01000193) >>> 0; };
  for (let i = 0; i < u3d.length; i += 97) melange(u3d[i]);
  for (let i = 0; i < titre.length; i++) melange(titre.charCodeAt(i));
  for (const d of vues) for (let i = 0; i < d.length; i += 7) melange(d.charCodeAt(i));
  for (const c of champs) for (let i = 0; i < c.length; i++) melange(c.charCodeAt(i));
  melange(u3d.length); melange(options.faces ?? 0);
  const id = (h >>> 0).toString(16).padStart(8, '0').repeat(4);

  const n = objets.length + 1;
  let xref = `xref\n0 ${n}\n0000000000 65535 f \n`;
  for (const p of positions) xref += `${String(p).padStart(10, '0')} 00000 n \n`;
  xref += `trailer\n<< /Size ${n} /Root 1 0 R${numInfo ? ` /Info ${numInfo} 0 R` : ''} `
        + `/ID [<${id}> <${id}>] >>\n`
        + `startxref\n${curseur}\n%%EOF\n`;
  morceaux.push(txt(xref));

  const pdf = concat(morceaux);
  return { pdf, octets: pdf.length, octetsFlux: corps3d.length, vues: vues.length };
}
