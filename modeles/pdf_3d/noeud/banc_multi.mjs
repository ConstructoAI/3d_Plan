// banc_multi.mjs — ce que les ecrivains « multi » DOIVENT a ceux de l'ERP, et ce qu'ils refusent.
//
//   node --import ./noeud/crochet_ts.mjs ./noeud/banc_multi.mjs
//
// 1. MEME PAGE, MEME REPLI QUE L'ERP. exportPdf3dMulti.ts a du recopier les auxiliaires de texte
//    de exportPdf3d.ts (ils n'y sont pas exportes). On ne le promet pas : on compare les OCTETS du
//    flux de la page et du flux de l'apparence de repli, pour des titres et des lignes pieges
//    (accents, parentheses, contre-obliques, troncature, ponctuation typographique).
// 2. LES REFUS de buildU3DMulti : chaque entree qui donnerait un fichier juste mais muet doit lever
//    une erreur qui nomme la cause.
// 3. Le fichier ecrit par buildU3DMulti pour une scene d'UNE piece sans matiere porte le meme
//    maillage, octet pour octet, que celui de l'ERP (memes positions, memes faces).
import { buildPdf3d } from '../erp/atelier/exportPdf3d.ts';
import { buildU3D } from '../erp/atelier/u3dWriter.ts';
import { buildPdf3dMulti } from '../exportPdf3dMulti.ts';
import { buildU3DMulti, CodeurArithmetique } from '../u3dWriterMulti.ts';

let passes = 0; const echecs = [];
function essai(nom, fn) {
  try { fn(); passes += 1; console.log(`  OK    ${nom}`); }
  catch (e) { echecs.push(nom); console.log(`  ECHEC ${nom}\n        -> ${e instanceof Error ? e.message : e}`); }
}
function egal(a, b, quoi) {
  if (a.length !== b.length) throw new Error(`${quoi} : ${a.length} octets contre ${b.length}`);
  for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) throw new Error(`${quoi} : 1er octet different au rang ${i}`);
}
const latin1 = (u) => { let s = ''; for (let i = 0; i < u.length; i++) s += String.fromCharCode(u[i]); return s; };
/** Le flux de l'objet n (octets), lu dans le PDF brut. */
function fluxDe(pdf, n) {
  const s = latin1(pdf);
  const m = s.match(new RegExp(`\\n${n} 0 obj\\n<<[\\s\\S]*?/Length (\\d+)[^>]*>>\\nstream\\n`));
  if (!m) throw new Error(`objet ${n} introuvable`);
  const d = m.index + m[0].length;
  return pdf.subarray(d, d + Number(m[1]));
}

const TETRA_ERP = new Float32Array([
  0, 0, 0, 1, 0, 0, 0, 1, 0,
  0, 0, 0, 1, 0, 0, 0, 0, 1,
  0, 0, 0, 0, 1, 0, 0, 0, 1,
  1, 0, 0, 0, 1, 0, 0, 0, 1,
]);
const VUE = { nom: 'Vue', c2w: [1, 0, 0, 0, 0, 1, 0, 1, 0, 0, -5, 0], co: 5, projection: 'P', fov: 30 };

console.log('1. Meme page et meme apparence de repli que l\'ERP (octet pour octet)');
const CAS = [
  { titre: 'Modèle — Étage', lignes: ['Superficie : 120 pi²', 'a (b) c \\ d'] },
  { titre: 'L’étage — manœuvre… 5 € — fin', lignes: ['x'.repeat(400), 'ligne 2', 'ligne 3'] },
  { titre: 'M'.repeat(200), lignes: Array.from({ length: 30 }, (_, i) => `L${i + 1}`) },
  { titre: 'fin par contre-obliques ' + '\\'.repeat(70), lignes: ['—'.repeat(200)] },
  { titre: undefined, lignes: undefined, messageRepli: 'Ouvrez avec un lecteur 3D (Acrobat) — é', messageRepli2: 'x'.repeat(300) },
];
CAS.forEach((c, i) => {
  essai(`cas ${i + 1} : flux de page et flux de repli identiques`, () => {
    const a = buildPdf3d(TETRA_ERP, c).pdf;
    const u = buildU3D(TETRA_ERP, { nom: c.titre || 'Modele' }).fichier;
    const b = buildPdf3dMulti(u, { ...c, vues: [VUE] }).pdf;
    egal(fluxDe(a, 4), fluxDe(b, 4), 'flux de la page (objet 4)');
    egal(fluxDe(a, 9), fluxDe(b, 8), 'apparence de repli (objet 9 de l\'ERP, 8 du multi)');
  });
});

console.log('2. Les refus de buildU3DMulti');
const P = new Float32Array([0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1]);
// Les sommets paraissent dans l'ordre 0, 1, 2, 3 au fil des faces : l'ecrivain de l'ERP, qui
// numerote les sommets a leur 1re apparition dans la soupe, retombe alors sur la MEME numerotation
// (l'essai 3 en depend ; une 1re version, avec une face [0, 2, 1] en tete, accusait le code a tort).
const I = new Uint32Array([0, 1, 2, 0, 3, 1, 0, 2, 3, 1, 3, 2]);
const M = { nom: 'm', positions: P, indices: I };
const MAT = { nom: 'acier', ambiant: [0.2, 0.2, 0.2], diffus: [0.5, 0.5, 0.5], speculaire: [0, 0, 0], emissif: [0, 0, 0], reflectivite: 0.2, opacite: 1 };
const refuse = (nom, scene, motif) => essai(nom, () => {
  let message = null;
  try { buildU3DMulti(scene); } catch (e) { message = e.message; }
  if (message === null) throw new Error('aucune erreur levee');
  if (!motif.test(message)) throw new Error(`erreur inattendue : ${message}`);
});
refuse('nœud sans nom', { noeuds: [{ nom: '', parent: '', maillage: 'm' }], maillages: [M], materiaux: [] }, /sans nom/);
refuse('deux nœuds du meme nom', { noeuds: [{ nom: 'a', parent: '', maillage: 'm' }, { nom: 'a', parent: '', maillage: 'm' }], maillages: [M], materiaux: [] }, /en double/);
refuse('parent inconnu', { noeuds: [{ nom: 'a', parent: 'g', maillage: 'm' }], maillages: [M], materiaux: [] }, /parent/);
refuse('parent declare APRES l\'enfant', { noeuds: [{ nom: 'a', parent: 'g', maillage: 'm' }, { nom: 'g', parent: '' }], maillages: [M], materiaux: [] }, /AVANT/);
refuse('parent qui n\'est pas un groupe', { noeuds: [{ nom: 'a', parent: '', maillage: 'm' }, { nom: 'b', parent: 'a', maillage: 'm' }], maillages: [M], materiaux: [] }, /groupe/);
refuse('maillage inconnu', { noeuds: [{ nom: 'a', parent: '', maillage: 'x' }], maillages: [M], materiaux: [] }, /inconnu/);
refuse('materiau inconnu', { noeuds: [{ nom: 'a', parent: '', maillage: 'm', nuanceurs: ['bois'] }], maillages: [M], materiaux: [MAT] }, /inconnu/);
refuse('nombre de matieres different du nombre de tranches', { noeuds: [{ nom: 'a', parent: '', maillage: 'm', nuanceurs: ['acier', 'acier'] }], maillages: [M], materiaux: [MAT] }, /tranche/);
refuse('indice de sommet hors bornes', { noeuds: [{ nom: 'a', parent: '', maillage: 'm' }], maillages: [{ ...M, indices: new Uint32Array([0, 1, 9]) }], materiaux: [] }, /hors bornes/);
refuse('coordonnee non finie', { noeuds: [{ nom: 'a', parent: '', maillage: 'm' }], maillages: [{ ...M, positions: new Float32Array([0, 0, 0, 1, NaN, 0, 0, 1, 0, 0, 0, 1]) }], materiaux: [] }, /non finie/);
refuse('matrice de 12 nombres', { noeuds: [{ nom: 'a', parent: '', maillage: 'm', matrice: [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0] }], maillages: [M], materiaux: [] }, /matrice/);
refuse('scene sans aucune piece', { noeuds: [{ nom: 'g', parent: '' }], maillages: [M], materiaux: [] }, /aucune piece/);
refuse('normales sans indices', { noeuds: [{ nom: 'a', parent: '', maillage: 'm' }], maillages: [{ ...M, normales: new Float32Array([0, 0, 1]) }], materiaux: [] }, /normales/);
refuse('unite nulle', { noeuds: [{ nom: 'a', parent: '', maillage: 'm' }], maillages: [M], materiaux: [], metresParUnite: 0 }, /metresParUnite/);

console.log('3. Une piece seule, sans matiere : le meme maillage que l\'ERP');
essai('positions et faces identiques a celles de u3dWriter.ts', () => {
  // l'ERP part d'un repere Y-haut et dedoublonne : on lui donne (X, Z, -Y), il retombe sur (X, Y, Z)
  const soupe = [];
  for (let t = 0; t < I.length; t++) { const v = I[t] * 3; soupe.push(P[v], P[v + 2], -P[v + 1]); }
  const erp = buildU3D(new Float32Array(soupe), { nom: 'a' }).fichier;
  const multi = buildU3DMulti({ noeuds: [{ nom: 'a', parent: '', maillage: 'm' }], maillages: [M], materiaux: [], compat: { compresse: false } }).fichier;
  // on compare la queue du bloc de suite : 4 positions (48 octets) puis 4 faces de 16 octets
  const queue = 48 + 4 * 16;
  egal(erp.subarray(erp.length - queue), multi.subarray(multi.length - queue), 'positions et faces');
});
essai('les refus de buildPdf3dMulti (vue sans camera, rendu inconnu)', () => {
  const u = buildU3DMulti({ noeuds: [{ nom: 'a', parent: '', maillage: 'm' }], maillages: [M], materiaux: [] }).fichier;
  for (const [vues, opt] of [[[], {}], [[{ ...VUE, c2w: [1, 2, 3] }], {}], [[{ ...VUE, co: 0 }], {}], [[VUE], { rendu: 'Joli' }], [[VUE], { eclairage: 'Soleil' }], [[{ ...VUE, projection: 'O' }], {}]]) {
    let leve = false;
    try { buildPdf3dMulti(u, { vues, ...opt }); } catch { leve = true; }
    if (!leve) throw new Error(`entree acceptee a tort : ${JSON.stringify(opt)} ${JSON.stringify(vues).slice(0, 60)}`);
  }
});

essai('par defaut le U3D est COMPRESSE : profil sans le bit 0x04, plus court, et un bloc de suite qui ne finit pas par les indices en clair', () => {
  const sc = { noeuds: [{ nom: 'a', parent: '', maillage: 'm' }], maillages: [M], materiaux: [] };
  const c = buildU3DMulti(sc).fichier;
  const n = buildU3DMulti({ ...sc, compat: { compresse: false } }).fichier;
  const profil = (u) => new DataView(u.buffer, u.byteOffset).getUint32(16, true);
  if (profil(c) !== 0x08) throw new Error(`profil compresse 0x${profil(c).toString(16)} (attendu 0x8)`);
  if (profil(n) !== 0x0c) throw new Error(`profil non compresse 0x${profil(n).toString(16)} (attendu 0xc)`);
  if (!(c.length < n.length)) throw new Error(`compresse ${c.length} octets, non compresse ${n.length}`);
  // la 1re tranche d'un bloc est toujours un ECHAPPEMENT suivi de la valeur en clair (§10.4.5) : depuis
  // l'etat initial du codeur, cela fait quatre octets nuls juste apres les positions
  const queue = c.subarray(c.length - 16);
  if (queue.every((x) => x === 0)) throw new Error('le flux compresse est vide');
});

essai('REPONSE CONNUE : le codeur rend, bit pour bit, ce qu\'a ecrit l\'encodeur d\'Adobe pour le cube de dice.u3d', () => {
  // Le cube de dice.u3d (echantillon public des paquets LaTeX movie15 et media9, ecrit par le convertisseur 3DIF
  // d'Adobe) : 12 faces, 8 positions, 6 normales, 4 coordonnees de texture. Ses 120 symboles, tels que le lecteur a
  // part les decode (tranche en contexte dynamique, puis par coin : position rang 8, normale rang 6, texture rang
  // 4), et les octets du flux des faces dans le fichier d'origine. Adobe ajoute 4 octets nuls apres la vidange de la
  // norme : nos 43 octets doivent etre les 43 premiers des siens. (Rejoue le 2026-10-09 sur les 22 maillages du
  // fichier : 47 160 symboles, 296 473 bits utiles, aucun bit different.)
  const POS = [4, 3, 0, 4, 7, 3, 7, 2, 3, 7, 6, 2, 6, 1, 2, 6, 5, 1, 5, 0, 1, 5, 4, 0, 0, 2, 1, 0, 3, 2, 5, 7, 4, 5, 6, 7];
  const NOR = [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 5];
  const TEX = [0, 2, 3, 0, 1, 2, 0, 2, 3, 0, 1, 2, 0, 2, 3, 0, 1, 2, 0, 2, 3, 0, 1, 2, 0, 2, 3, 0, 1, 2, 0, 2, 3, 0, 1, 2];
  const ADOBE = '0000000001c1a9688afbab24b1ba07ab7f97da88e4f24d15b06c1c35a7419e72935a9d0051cdab9f01000000000000';
  const ac = new CodeurArithmetique(64);
  for (let f = 0; f < 12; f++) {
    ac.compresseDynamique(1, 0);
    for (let c = 0; c < 3; c++) {
      ac.compresseStatique(8, POS[f * 3 + c]);
      ac.compresseStatique(6, NOR[f * 3 + c]);
      ac.compresseStatique(4, TEX[f * 3 + c]);
    }
  }
  const nous = ac.fin();
  const hex = Array.from(nous, (x) => x.toString(16).padStart(2, '0')).join('');
  if (nous.length !== 43) throw new Error(`${nous.length} octets au lieu de 43 : ${hex}`);
  if (hex !== ADOBE.slice(0, 86)) throw new Error(`octets differents de ceux d'Adobe :\n          ${hex}\n          ${ADOBE.slice(0, 86)}`);
});

console.log('4. Les proprietes du document (/Info) : absentes comme dans l\'ERP, ou celles demandees et rien d\'autre');
{
  const u = buildU3DMulti({ noeuds: [{ nom: 'a', parent: '', maillage: 'm' }], maillages: [M], materiaux: [] }).fichier;
  const sans = buildPdf3dMulti(u, { titre: 'T', vues: [VUE] }).pdf;
  /** Chaque position de la table xref pointe-t-elle sur « n 0 obj » ? Rend le nombre d'objets. */
  const xrefJuste = (pdf) => {
    const s = latin1(pdf);
    const d = Number(s.match(/startxref\n(\d+)\n%%EOF\n$/)[1]);
    const lignes = s.slice(d).split('\n');
    if (lignes[0] !== 'xref') throw new Error('startxref ne pointe pas sur « xref »');
    const n = Number(lignes[1].split(' ')[1]);
    for (let i = 1; i < n; i++) {
      const pos = Number(lignes[2 + i].slice(0, 10));
      if (!s.startsWith(`${i} 0 obj\n`, pos)) throw new Error(`la position de l'objet ${i} ne pointe pas sur « ${i} 0 obj »`);
    }
    if (!new RegExp(`trailer\\n<< /Size ${n} `).test(s)) throw new Error('/Size different du nombre de lignes de la table');
    return n - 1;
  };
  essai('sans proprietes : aucun /Info, 9 objets, table xref juste', () => {
    if (latin1(sans).includes('/Info')) throw new Error('/Info present sans qu\'on l\'ait demande');
    if (xrefJuste(sans) !== 9) throw new Error(`${xrefJuste(sans)} objets au lieu de 9`);
  });
  essai('proprietes vides ou absentes : le MEME fichier, octet pour octet', () => {
    egal(sans, buildPdf3dMulti(u, { titre: 'T', vues: [VUE], proprietes: {} }).pdf, 'proprietes: {}');
    egal(sans, buildPdf3dMulti(u, { titre: 'T', vues: [VUE], proprietes: { titre: '', auteur: '', sujet: '' } }).pdf, 'valeurs vides');
  });
  essai('avec proprietes : /Info en DERNIER objet, les 9 premiers inchanges, accents en UTF-16', () => {
    const avec = buildPdf3dMulti(u, { titre: 'T', vues: [VUE], proprietes: { titre: 'Mod(e)le \\ 3D', auteur: 'Préparé par une IA (Claude)', sujet: 'RÉF. abc — à valider' } }).pdf;
    const s = latin1(avec);
    if (xrefJuste(avec) !== 10) throw new Error(`${xrefJuste(avec)} objets au lieu de 10`);
    if (!/trailer\n<< \/Size 11 \/Root 1 0 R \/Info 10 0 R \/ID \[/.test(s)) throw new Error('le trailer ne renvoie pas a « /Info 10 0 R »');
    const fin = latin1(sans).indexOf('xref\n0 10\n');
    const debut = s.indexOf('\n10 0 obj\n') + 1;
    egal(sans.subarray(0, fin), avec.subarray(0, debut), 'objets 1 a 9');
    const o = s.slice(debut, s.indexOf('endobj', debut));
    if (!o.includes('/Title (Mod\\(e\\)le \\\\ 3D)')) throw new Error(`titre ASCII mal echappe : ${o}`);
    const hex = (t) => 'FEFF' + [...t].map((c) => c.charCodeAt(0).toString(16).toUpperCase().padStart(4, '0')).join('');
    if (!o.includes(`/Author <${hex('Préparé par une IA (Claude)')}>`)) throw new Error(`auteur accentue attendu en UTF-16BE : ${o}`);
    if (!o.includes(`/Subject <${hex('RÉF. abc — à valider')}>`)) throw new Error(`sujet accentue attendu en UTF-16BE : ${o}`);
    if (/\/(Creator|Producer|CreationDate|ModDate|Keywords)\b/.test(s)) throw new Error('une propriete non demandee est ecrite');
  });
  essai('l\'empreinte /ID suit les proprietes (deux documents differents, deux /ID)', () => {
    const id = (pdf) => latin1(pdf).match(/\/ID \[<([0-9a-f]+)>/)[1];
    const a = id(buildPdf3dMulti(u, { titre: 'T', vues: [VUE], proprietes: { auteur: 'A' } }).pdf);
    const b = id(buildPdf3dMulti(u, { titre: 'T', vues: [VUE], proprietes: { auteur: 'B' } }).pdf);
    if (a === b || a === id(sans)) throw new Error('/ID identique pour des proprietes differentes');
  });
}

console.log(`TOTAL : ${passes} sur ${passes + echecs.length} essai(s) passent ; ${echecs.length} echec(s)`);
process.exit(echecs.length ? 1 : 0);
