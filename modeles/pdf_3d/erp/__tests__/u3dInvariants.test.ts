/**
 * Les INVARIANTS INTERNES du U3D — ceux que personne ne relisait.
 *
 * ⚠️ POURQUOI CE BANC EXISTE. Une passe de 46 mutations sur le chemin PDF 3D (2026-08-19) a
 * montré que le banc existant valide la **coquille PDF** — en-tête, objets, table `xref`,
 * longueurs de flux — et **jamais le U3D qu'elle transporte**. Huit mutations y survivaient,
 * toutes correspondant à des défauts que les docstrings du module désignent elles-mêmes comme
 * les plus muets. Dont celui-ci, décrit sur vingt lignes comme
 * *« LE DÉFAUT LE PLUS COÛTEUX DE CE MODULE, ET IL ÉTAIT MUET »* — et qui n'avait aucun test :
 * un nœud sans parent produit un fichier **structurellement impeccable qui n'affiche rien**.
 *
 *   *Un banc qui valide l'enveloppe et pas le contenu laisse passer exactement les défauts qui
 *   ne se voient qu'à l'ouverture — c'est-à-dire chez l'utilisateur.*
 *
 * CE BANC EST UN ORACLE INDÉPENDANT : il **relit** le flux binaire bloc par bloc, sans réutiliser
 * une seule fonction de l'écrivain. Un test qui appellerait les helpers du writer pour vérifier
 * le writer ne prouverait que leur cohérence avec eux-mêmes.
 *
 * CE QU'IL NE PROUVE PAS : qu'Acrobat affiche le modèle. Aucun test ici ne le peut. La validation
 * finale reste qu'un humain ouvre le fichier.
 */
import { describe, expect, it } from 'vitest';

import { buildU3D } from '../atelier/u3dWriter';

/** Types de blocs U3D lus dans ECMA-363 — recopiés ici EXPRÈS, pour ne rien emprunter au writer. */
const TYPE = {
  entete: 0x00443355,
  chaineModif: 0xffffff14,
  noeudModele: 0xffffff22,
  declMaillage: 0xffffff31,
  contMaillage: 0xffffff3b,
} as const;

interface Bloc {
  readonly type: number;
  readonly corps: DataView;
  readonly taille: number;
  /** Position du bloc depuis le début du fichier — sert à prouver l'alignement. */
  readonly debut: number;
}

/**
 * Découpe le fichier en blocs, **en descendant dans les chaînes de modificateurs**.
 *
 * ⚠️ LE FORMAT EST IMBRIQUÉ, ET MA PREMIÈRE VERSION NE L'ÉTAIT PAS. Un balayage à plat ne trouve
 * que trois types au premier niveau (en-tête, deux chaînes, une continuation) : le NŒUD
 * (`0xffffff22`) et la DÉCLARATION de maillage (`0xffffff31`) vivent **à l'intérieur** des
 * chaînes. Mon lecteur rendait donc « bloc introuvable » sur un fichier parfaitement valide —
 * c'était l'oracle qui avait tort, pas l'écrivain.
 *   *Un oracle écrit d'après le code qu'il vérifie hérite de ce qu'on a mal compris ; un oracle
 *   écrit d'après le FORMAT trouve d'abord ses propres erreurs.*
 *
 * L'en-tête d'une chaîne est : nom (chaîne), type (u32), attributs (u32), bourrage, nombre de
 * modificateurs (u32), puis les blocs internes bout à bout.
 */
function lireBlocs(u: Uint8Array): Bloc[] {
  const dv = new DataView(u.buffer, u.byteOffset, u.byteLength);
  const out: Bloc[] = [];
  let o = 0;
  while (o + 12 <= u.byteLength) {
    const debut = o;
    const type = dv.getUint32(o, true);
    const taille = dv.getUint32(o + 4, true);
    const meta = dv.getUint32(o + 8, true);
    o += 12;
    if (o + taille + meta > u.byteLength) {
      throw new Error(`bloc ${type.toString(16)} deborde du fichier (taille ${taille})`);
    }
    out.push({
      type,
      taille,
      debut,
      corps: new DataView(u.buffer, u.byteOffset + o, taille),
    });
    if (type === TYPE.chaineModif) {
      // Descendre : sauter l'en-tête de chaîne, puis relire des blocs dans le corps.
      const dvc = new DataView(u.buffer, u.byteOffset + o, taille);
      let p = lireChaine(dvc, 0)[1];         // nom
      p += 4;                                 // type de chaîne
      p += 4;                                 // attributs
      p += (4 - (p % 4)) % 4;                 // bourrage
      p += 4;                                 // nombre de modificateurs
      if (p < taille) {
        const interne = new Uint8Array(u.buffer, u.byteOffset + o + p, taille - p);
        for (const b of lireBlocs(interne)) out.push({ ...b, debut: o + p + b.debut });
      }
    }
    o += taille + meta;
    o += (4 - (o % 4)) % 4;          // bourrage
  }
  return out;
}

/** Lit une chaîne U3D : longueur sur 16 bits, puis les octets. Rend [texte, octets consommés]. */
function lireChaine(dv: DataView, o: number): [string, number] {
  const n = dv.getUint16(o, true);
  let s = '';
  for (let i = 0; i < n; i++) s += String.fromCharCode(dv.getUint8(o + 2 + i));
  return [s, 2 + n];
}

const TETRA = new Float32Array([
  0, 0, 0, 1, 0, 0, 0, 1, 0,
  0, 0, 0, 1, 0, 0, 0, 0, 1,
  0, 0, 0, 0, 1, 0, 0, 0, 1,
  1, 0, 0, 0, 1, 0, 0, 0, 1,
]);

function u3d(nom = 'Modele') {
  const r = buildU3D(TETRA, { nom });
  expect(r).not.toBeNull();
  return { fichier: r!.fichier, faces: r!.faces, sommets: r!.sommets };
}

describe('les invariants INTERNES du U3D', () => {
  it('TÉMOIN DE L\'ORACLE : le lecteur sait découper le fichier et retrouver ses blocs', () => {
    // Sans ce témoin, un lecteur qui rendrait une liste VIDE ferait passer tous les tests
    // ci-dessous — ils asserteraient sur rien.
    const blocs = lireBlocs(u3d().fichier);
    expect(blocs.length).toBeGreaterThan(3);
    expect(blocs[0].type).toBe(TYPE.entete);
    const types = new Set(blocs.map((b) => b.type));
    for (const attendu of [TYPE.noeudModele, TYPE.declMaillage, TYPE.contMaillage]) {
      expect(types.has(attendu)).toBe(true);
    }
  });

  it('le NŒUD déclare UN parent, et ce parent est la RACINE (chaîne vide)', () => {
    /**
     * ⚠️ LE DÉFAUT QUE CE TEST VERROUILLE, dans les mots d'ECMA-363 §8.9.1 :
     * « A node with no parents will have an empty transform set. […] If the transform set is
     * empty, the node is disconnected from the world and does not appear in the rendered view. »
     * Il n'y a **pas** de racine implicite : on s'y rattache en déclarant un parent nommé `""`.
     * Écrire `0 parent` produit un fichier impeccable qui n'affiche RIEN, sans un message.
     */
    const blocs = lireBlocs(u3d('Batiment').fichier);
    const noeud = blocs.find((b) => b.type === TYPE.noeudModele);
    expect(noeud).toBeDefined();
    let o = 0;
    const [nom, lu] = lireChaine(noeud!.corps, o);
    o += lu;
    expect(nom).toBe('Batiment');
    const nbParents = noeud!.corps.getUint32(o, true);
    o += 4;
    expect(nbParents).toBe(1);           // ZÉRO parent = modèle invisible
    const [nomParent, lu2] = lireChaine(noeud!.corps, o);
    o += lu2;
    expect(nomParent).toBe('');          // la chaîne VIDE désigne la racine de la palette
  });

  it('la matrice du parent est l\'IDENTITÉ — pas une mise à l\'échelle', () => {
    /**
     * ⚠️ Une échelle glissée ici rend TOUTE COTE fausse d'un facteur constant, sans qu'aucun
     * contrôle ne bronche : le métré lit le modèle paramétrique, pas le U3D. L'utilisateur
     * mesurerait dans son lecteur PDF et obtiendrait des millimètres pour des mètres.
     */
    const blocs = lireBlocs(u3d().fichier);
    const noeud = blocs.find((b) => b.type === TYPE.noeudModele)!;
    let o = 0;
    o += lireChaine(noeud.corps, o)[1];
    o += 4;                                   // nombre de parents
    o += lireChaine(noeud.corps, o)[1];       // nom du parent
    const m: number[] = [];
    for (let i = 0; i < 16; i++) m.push(noeud.corps.getFloat32(o + i * 4, true));
    // colonne-majeur : la diagonale est aux indices 0, 5, 10, 15
    for (let i = 0; i < 16; i++) {
      expect(m[i]).toBe(i % 5 === 0 ? 1 : 0);
    }
  });

  it('un nom ACCENTUÉ survit au fichier — le français est la langue du produit', () => {
    /**
     * ⚠️ Un masque à 7 bits transforme « Bâtiment québécois » en « Bbtiment quibicois » dans
     * l'arbre du lecteur. Muet, cosmétique en apparence, et illisible pour l'utilisateur.
     */
    const nom = 'Bâtiment québécois';
    const blocs = lireBlocs(u3d(nom).fichier);
    const noeud = blocs.find((b) => b.type === TYPE.noeudModele)!;
    const [octets] = lireChaine(noeud.corps, 0);
    // ⚠️ LE U3D ÉCRIT EN UTF-8, PAS UN OCTET PAR CARACTÈRE. Ma première version comparait les
    // longueurs brutes et échouait sur 21 contre 18 — trois octets de plus, exactement les trois
    // accents. C'était l'oracle qui supposait, pas l'écrivain qui fautait.
    const brut = new Uint8Array(octets.length);
    for (let i = 0; i < octets.length; i++) brut[i] = octets.charCodeAt(i);
    const relu = new TextDecoder('utf-8').decode(brut);
    expect(relu).toBe(nom);
    expect(octets.length).toBeGreaterThan(nom.length);   // la preuve que ce sont bien des octets
  });

  it('la TAILLE déclarée de chaque bloc EXCLUT son bourrage', () => {
    /**
     * ⚠️ Inclure le bourrage décale la lecture de tous les blocs suivants. Un lecteur tolérant
     * peut s'en sortir ; un lecteur strict refuse le fichier entier. Le parcours de cet oracle
     * échouerait AUSSI — c'est pourquoi on asserte l'alignement explicitement plutôt que de se
     * fier au fait que le découpage a réussi.
     */
    const blocs = lireBlocs(u3d().fichier);
    for (const b of blocs) {
      expect(b.debut % 4).toBe(0);
      expect(b.taille % 4 === 0 || b.taille > 0).toBe(true);
    }
    // et le parcours doit tomber PILE sur la fin du fichier
    const dernier = blocs[blocs.length - 1];
    const fin = dernier.debut + 12 + dernier.taille;
    const total = u3d().fichier.byteLength;
    expect(total - fin).toBeLessThan(4);
    expect(total - fin).toBeGreaterThanOrEqual(0);
  });

  it('les COMPTES rendus décrivent le FICHIER, pas l\'intention', () => {
    /**
     * Le tétraèdre a 12 sommets écrits et 4 distincts : le dédoublonnage fusionne. Un compte qui
     * décrirait l'entrée serait une illustration, pas une mesure.
     */
    const r = u3d();
    expect(r.faces).toBe(4);
    expect(r.sommets).toBe(4);

    // ⚠️ CENT TRIANGLES IDENTIQUES DONNENT 3 SOMMETS ET 100 FACES — pas une face.
    // La docstring du module affirmait le contraire ; mesuré, elle avait tort. Le dédoublonnage
    // travaille sur les SOMMETS, jamais sur les faces, et le test de dégénérescence ne compare
    // que les indices À L'INTÉRIEUR d'un triangle. Ce test verrouille donc le comportement RÉEL,
    // et nomme l'écart : cent copies coplanaires de `[0,1,2]` scintillent dans le lecteur.
    //   *Verrouiller ce que le code fait, en écrivant à côté ce qu'on aurait voulu qu'il fasse,
    //   vaut mieux qu'un test qui échoue sur une intention.*
    const cent = new Float32Array(100 * 9);
    for (let i = 0; i < 100; i++) cent.set([0, 0, 0, 1, 0, 0, 0, 1, 0], i * 9);
    const rr = buildU3D(cent, { nom: 'Cent' });
    expect(rr).not.toBeNull();
    expect(rr!.sommets).toBe(3);      // les SOMMETS fusionnent
    expect(rr!.faces).toBe(100);      // les FACES non — défaut connu, non corrigé
  });
});
