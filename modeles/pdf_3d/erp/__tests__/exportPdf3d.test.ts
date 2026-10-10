/**
 * Banc du PDF 3D.
 *
 * CE QU'IL PROUVE : que le fichier est un PDF STRUCTURELLEMENT valide — en-tete, objets,
 * table `xref` dont chaque decalage tombe sur le bon objet, longueurs de flux exactes,
 * dictionnaire d'annotation complet. C'est precisement ce qui fait qu'un lecteur refuse un
 * document ENTIER sans dire pourquoi.
 *
 * CE QU'IL NE PROUVE PAS : qu'Acrobat ou PDF-XChange affiche le modele. Aucun test ici ne le
 * peut. **La validation finale est qu'un humain ouvre le fichier**, et c'est ecrit pour que
 * « tests verts » ne se lise jamais comme « ca marche ».
 */
import { describe, expect, it } from 'vitest';

import { buildPdf3d } from '../atelier/exportPdf3d';

const TETRA = new Float32Array([
  0, 0, 0, 1, 0, 0, 0, 1, 0,
  0, 0, 0, 1, 0, 0, 0, 0, 1,
  0, 0, 0, 0, 1, 0, 0, 0, 1,
  1, 0, 0, 0, 1, 0, 0, 0, 1,
]);

/** Lit le PDF en latin-1 : chaque octet devient un caractere, donc les positions sont exactes
 *  meme a travers le flux binaire du U3D. Passer par UTF-8 les decalerait. */
function ascii(u: Uint8Array): string {
  let s = '';
  for (let i = 0; i < u.length; i++) s += String.fromCharCode(u[i]);
  return s;
}

describe('PDF 3D', () => {
  it('commence par un en-tete PDF et finit par %%EOF', () => {
    const p = buildPdf3d(TETRA)!.pdf;
    expect(p).not.toBeNull();
    expect(ascii(p.subarray(0, 8))).toBe('%PDF-1.6');
    expect(ascii(p.subarray(p.length - 6))).toBe('%%EOF\n');
  });

  it('CHAQUE DECALAGE de la table xref tombe sur le bon objet', () => {
    // LE PIEGE UNIQUE DU FORMAT : une seule position fausse et le lecteur refuse le document
    // entier, sans indiquer laquelle. Ce test est le seul qui l'attrape avant l'utilisateur.
    const p = buildPdf3d(TETRA)!.pdf;
    const s = ascii(p);
    const m = s.match(/xref\n0 (\d+)\n([\s\S]*?)trailer/);
    expect(m).toBeTruthy();
    const n = Number(m![1]);
    const lignes = m![2].trimEnd().split('\n');
    expect(lignes).toHaveLength(n);
    expect(lignes[0]).toMatch(/^0{10} 65535 f/);
    for (let i = 1; i < n; i++) {
      const pos = Number(lignes[i].slice(0, 10));
      expect(s.slice(pos, pos + 12)).toMatch(new RegExp(`^${i} 0 obj`));
    }
  });

  it('startxref pointe le DEBUT de la table xref', () => {
    const p = buildPdf3d(TETRA)!.pdf;
    const s = ascii(p);
    const pos = Number(s.match(/startxref\n(\d+)/)![1]);
    expect(s.slice(pos, pos + 4)).toBe('xref');
  });

  it('LA LONGUEUR ANNONCEE du flux 3D est la vraie longueur du U3D', () => {
    // Une longueur fausse tronque la geometrie ou deborde sur l'objet suivant. Dans les deux
    // cas le lecteur affiche une zone VIDE, sans erreur.
    const p = buildPdf3d(TETRA)!.pdf;
    const s = ascii(p);
    const m = s.match(/\/Type \/3D \/Subtype \/U3D [\s\S]*?\/Length (\d+) >>\nstream\n/)!;
    expect(m).toBeTruthy();
    const debut = m.index! + m[0].length;
    const longueur = Number(m[1]);
    // le U3D commence par son bloc d'en-tete 0x00443355, en little-endian
    expect([p[debut], p[debut + 1], p[debut + 2], p[debut + 3]]).toEqual([0x55, 0x33, 0x44, 0x00]);
    expect(s.slice(debut + longueur, debut + longueur + 11)).toBe('\nendstream\n');
  });

  it('l\'annotation 3D est COMPLETE — sans elle le PDF s\'ouvre mais reste inerte', () => {
    const p = buildPdf3d(TETRA)!.pdf;
    const s = ascii(p);
    expect(s).toContain('/Type /Annot /Subtype /3D');
    expect(s).toContain('/3DD 6 0 R');       // pointe le flux de geometrie
    expect(s).toContain('/3DV 8 0 R');       // pointe la vue par defaut
    expect(s).toContain('/3DA');             // demande l'ACTIVATION : sans elle, image inerte
    expect(s).toContain('/Type /3DView');
    // La page doit REFERENCER l'annotation, sinon elle n'existe pour personne.
    expect(s).toMatch(/\/Annots \[7 0 R\]/);
  });

  it('le titre et les lignes de texte sont ECHAPPES', () => {
    // Une parenthese non echappee dans un litteral PDF casse la syntaxe du document.
    const p = buildPdf3d(TETRA, { titre: 'Maison (test) \\ 50 %', lignes: ['a (b) c'] })!.pdf;
    const s = ascii(p);
    expect(s).toContain('Maison \\(test\\) \\\\ 50 %');
    expect(s).toContain('a \\(b\\) c');
  });

  it('LES ACCENTS FRANCAIS survivent — un octet par lettre, police WinAnsi', () => {
    // Le francais est la langue du produit. Encoder « Modèle » en UTF-8 dans un flux dont la
    // police est WinAnsi le rend « ModÃ¨le » : deux octets lus comme deux lettres. Ce test fige
    // la paire {un octet par caractere} + {/Encoding /WinAnsiEncoding}, qui ne vaut qu'ensemble.
    const p = buildPdf3d(TETRA, { titre: 'Modèle — Étage', lignes: ['Superficie : 120 pi²'] })!.pdf;
    const s = ascii(p);
    expect(s).toContain('/Encoding /WinAnsiEncoding');
    expect(s).toContain('Mod\xe8le');       // e accent grave = UN octet 0xE8
    expect(s).toContain('\xc9tage');        // E accent aigu majuscule
    expect(s).toContain('120 pi\xb2');      // exposant deux
    // Le tiret cadratin sort en 0x97, sa place dans WinAnsi — il devenait une ESPACE tant que je
    // croyais WinAnsi identique a Latin-1.
    expect(s).toContain('Mod\xe8le \x97 \xc9tage');

    // LE GARDE ANTI-UTF-8 DOIT VISER LE FLUX DE TEXTE, PAS LE FICHIER ENTIER. Il cherchait
    // `\xc3\xa8` (la signature d'un « è » encode en UTF-8) partout — et il s'est mis a echouer
    // des que les noms du U3D sont passes en UTF-8, ce qui est CORRECT de leur part : le bloc
    // binaire declare l'encodage 106. Un test trop large accuse la bonne correction.
    const m = s.match(/4 0 obj\n<< \/Length (\d+) >>\nstream\n/)!;
    const contenu = s.slice(m.index! + m[0].length, m.index! + m[0].length + Number(m[1]));
    expect(contenu).toContain('Mod\xe8le');
    expect(contenu).not.toContain('\xc3\xa8');
  });

  it('refuse un maillage inexploitable plutot que d\'ecrire un PDF vide', () => {
    expect(buildPdf3d(new Float32Array([]))).toBeNull();
    expect(buildPdf3d(new Float32Array([0, NaN, 0, 1, 0, 0, 0, 1, 0]))).toBeNull();
  });

  it('LE MODELE Y-UP EST CONVERTI EN Z-UP — ce test disait EXACTEMENT L\'INVERSE', () => {
    // Ce test affirmait « le repere n'est PAS converti ici, et c'est voulu ». C'etait FAUX, et
    // le fait de l'avoir ecrit comme une decision a rendu l'erreur plus difficile a voir : un
    // test vert qui documente une intention n'est plus interroge.
    //
    // ECMA-363 §8.3.3 exprime une PREFERENCE pour un repere ou Z est vers le haut, et
    // l'echantillon de reference du format le respecte. On applique donc `X=x, Y=-z, Z=y` — la
    // MEME conversion que l'export DXF, puisque les deux mondes sont Z-up.
    //
    // Le discriminant : un point a z = +5 dans le modele doit ressortir a **-5**.
    const p = buildPdf3d(new Float32Array([0, 0, 0, 1, 0, 0, 0, 7, 5]))!.pdf;
    const s = ascii(p);
    const m = s.match(/\/Subtype \/U3D [\s\S]*?\/Length (\d+) >>\nstream\n/)!;
    const u = p.subarray(m.index! + m[0].length);
    const dv = new DataView(u.buffer, u.byteOffset, u.byteLength);
    const flottants: number[] = [];
    for (let o = 0; o + 4 <= u.length; o += 4) flottants.push(dv.getFloat32(o, true));
    const proche = (x: number): boolean => flottants.some((f) => Math.abs(f - x) < 1e-6);
    expect(proche(7)).toBe(true);     // le Y du modele devient le Z du U3D
    expect(proche(-5)).toBe(true);    // le Z du modele devient -Y
    expect(proche(5)).toBe(false);    // et il ne reste PAS tel quel
  });

  it('L\'APPARENCE DE REPLI existe — sans elle, tout lecteur sans 3D montre une page BLANCHE', () => {
    // ISO 32000-1 §13.6.2 : « a 3D annotation **shall** provide an appearance stream in its AP
    // entry ». Mesure sans elle : 0,588 % de pixels non blancs dans le rectangle — le filet du
    // cadre, rien d'autre. Et cela vaut aussi a l'IMPRESSION, que `/F 4` autorise.
    const p = buildPdf3d(TETRA)!.pdf;
    const s = ascii(p);
    expect(s).toContain('/AP << /N 9 0 R >>');
    expect(s).toMatch(/9 0 obj\n<< \/Type \/XObject \/Subtype \/Form/);
    expect(s).toContain('/BBox [0 0 762 405]');
    // et le message de repli doit etre LISIBLE dans le flux de l'apparence
    expect(s).toContain('Acrobat Reader');
  });

  it('LA VUE PAR DEFAUT respecte la norme : pas de /MS orphelin, /Subtype /P et non /Perspective', () => {
    const p = buildPdf3d(TETRA)!.pdf;
    const s = ascii(p);
    // `/MS /U3D` EXIGE `/U3DPath` (Table 304). Sans chemin, la vue est malformee ; en OMETTANT
    // `/MS`, la norme impose d'utiliser la vue de l'œuvre — le cadrage automatique voulu.
    expect(s).not.toContain('/MS /U3D');
    expect(s).not.toContain('/U3DPath');
    // Table 305 : « Valid values shall be O or P ». `/Perspective` est de la PROSE de la table
    // voisine, pas un nom PDF — et `/FOV` n'etant lu que « if Subtype is P », mon `/FOV 45`
    // etait purement et simplement ignore.
    expect(s).not.toContain('/Subtype /Perspective');
    expect(s).toContain('/Subtype /P /FOV 45');
    // `/TB false` supprimait la barre d'outils 3D — donc ce qui REVELE que le modele se manipule.
    expect(s).not.toContain('/TB false');
  });

  it('LA PONCTUATION TYPOGRAPHIQUE FRANCAISE survit : WinAnsi est CP1252, pas Latin-1', () => {
    // Les deux qui font mal au Quebec : l'apostrophe courbe (que produit tout copier-coller) et
    // la ligature du « manœuvre ». Latin-1 laisse 0x80-0x9F vide, CP1252 y loge cette
    // ponctuation — et mon filtre les jetait toutes les 27.
    const p = buildPdf3d(TETRA, { titre: 'L’etage', lignes: ['manœuvre', 'a…b', '5 € — fin'] })!.pdf;
    const s = ascii(p);
    expect(s).toContain('L\x92etage');       // ’ = 0x92
    expect(s).toContain('man\x9cuvre');      // œ = 0x9C
    expect(s).toContain('a\x85b');           // … = 0x85
    expect(s).toContain('5 \x80 \x97 fin');  // € = 0x80, — = 0x97
  });

  it('AUCUNE LIGNE N\'EST ECRITE SOUS LA PAGE — le budget vient de la geometrie', () => {
    // Le plafond etait code en dur a 12 alors que 10 seulement tenaient : les lignes 11 et 12
    // partaient a y = -2 et y = -15, hors page. Sur un export de quantites, la ligne perdue est
    // un montant. Le budget se DEDUIT desormais de la hauteur disponible.
    const lignes = Array.from({ length: 30 }, (_, i) => `L${i + 1}`);
    const p = buildPdf3d(TETRA, { lignes })!.pdf;
    const s = ascii(p);
    const ys = [...s.matchAll(/BT \/F1 9 Tf 40 (-?\d+) Td/g)].map((m) => Number(m[1]));
    expect(ys.length).toBeGreaterThan(0);
    for (const y of ys) expect(y).toBeGreaterThanOrEqual(0);
    // et on ne promet pas plus de lignes qu'on n'en ecrit
    expect(s).not.toContain('(L30)');
  });

  it('UN TITRE DEMESURE est tronque au lieu de sortir par le bord droit', () => {
    const p = buildPdf3d(TETRA, { titre: 'M'.repeat(200) })!.pdf;
    const s = ascii(p);
    const m = s.match(/BT \/F1 16 Tf 40 \d+ Td \(([^)]*)\) Tj ET/)!;
    expect(m).toBeTruthy();
    expect(m[1].endsWith('...')).toBe(true);
    // Largeur reelle : 'M' = 833/1000 de cadratin, '.' = 278/1000. Ma premiere version comptait
    // les trois points au tarif du 'M' et accusait le code a tort — l'arithmetique du TEST etait
    // fausse, pas la troncature.
    const pts = 3 * 278, ms = (m[1].length - 3) * 833;
    expect(((pts + ms) * 16) / 1000).toBeLessThanOrEqual(842 - 80);
  });

  it('rend les comptes REELS du fichier, pas ceux qu\'on lui a donnes', () => {
    // Trois triangles fournis, DEUX degeneres (sommets confondus) : le fichier n'en contient
    // qu'un. L'interface annoncait le compte d'ENTREE ; elle annonce desormais celui du FICHIER.
    const r = buildPdf3d(new Float32Array([
      0, 0, 0, 1, 0, 0, 0, 1, 0,
      2, 0, 0, 2, 0, 0, 3, 0, 0,
      4, 0, 0, 4, 0, 0, 4, 0, 0,
    ]))!;
    expect(r.faces).toBe(1);
    // 3 sommets, et c'est une CORRECTION : les sommets des triangles ecartes restaient d'abord
    // dans la table, ORPHELINS. Inoffensifs pour le maillage — mais la QA a mesure qu'UN seul
    // triangle degenere pose loin du modele faisait passer l'etendue des coordonnees de 1 m a
    // 1001 m, et le lecteur CADRE sur cette etendue. On les purge donc, avec renumerotation.
    expect(r.sommets).toBe(3);
    expect(r.octets).toBe(r.pdf.length);
  });
});

describe('un GROS modele — le defaut trouve par Sylvain le 2026-08-19', () => {
  /**
   * ⚠️ CE QUE CE TEST REPRODUIT. Sylvain a exporte un batiment industriel complet et n'a eu
   * qu'un « L'export PDF 3D a echoue. Le modele n'est pas affecte. » — le `catch` de l'appelant
   * avale l'erreur et n'ecrit la cause qu'en console.
   *
   * LA CAUSE, MESUREE : `pos.push(...posUtiles)` passait CHAQUE element en ARGUMENT d'appel.
   * Au-dela de la taille de la pile d'arguments, ça leve `RangeError`. Seuil mesure sur ce
   * moteur :
   *
   *     125 000 elements -> OK        130 000 elements -> RangeError
   *
   * `posUtiles` porte TROIS flottants par sommet, donc l'export cassait des **~43 000 sommets**
   * — c'est-a-dire sur a peu pres tout batiment reel. Et le plafond du module autorise
   * `MAX_TRIANGLES_PDF3D = 400 000` triangles, soit jusqu'a 3,6 MILLIONS de flottants : la
   * borne annoncee etait **28 fois au-dessus de ce que le code pouvait encaisser**.
   *
   * ⚠️ POURQUOI AUCUN TEST NE LE VOYAIT : tous les modeles du banc sont minuscules (un tetraedre
   * de 4 triangles). La taille n'etait une variable de test nulle part.
   *   *Un banc dont toutes les fixtures sont petites ne teste pas la petitesse : il ne teste
   *   simplement pas la taille.*
   */
  function grilleDeTriangles(nTriangles: number): Float32Array {
    // Des triangles DISTINCTS et non degeneres, poses le long de x : aucun ne sera ecarte,
    // donc le compte de sommets utiles vaut bien 3 x nTriangles.
    const out = new Float32Array(nTriangles * 9);
    for (let i = 0; i < nTriangles; i++) {
      const x = i * 0.5;
      out.set([x, 0, 0, x + 0.4, 0, 0, x, 0.4, 0], i * 9);
    }
    return out;
  }

  it('ne LEVE PAS sur un modele qui depasse la limite du spread', () => {
    // 50 000 triangles = 150 000 sommets = 450 000 flottants, soit ~3,5 x le seuil mesure.
    const sommets = grilleDeTriangles(50_000);
    const r = buildPdf3d(sommets, { titre: 'Gros modele' });
    expect(r).not.toBeNull();
    // ⚠️ LA PREMISSE PORTE SUR `r.sommets * 3`, PAS SUR L'ENTREE. Une premiere version assertait
    // `sommets.length > 130_000` — la longueur du Float32Array D'ENTREE. Les deux coincident ici
    // seulement parce que cette fixture n'a AUCUN sommet partage (9 flottants par triangle des
    // deux cotes). Une fixture future avec sommets partages garderait l'assertion VERTE en
    // faisant passer le tableau reellement etale SOUS le seuil : le test cesserait de tester ce
    // qu'il annonce, sans rougir.
    //   *Une premisse doit porter sur la grandeur que le defaut touche, pas sur celle qui lui
    //   ressemble a l'entree.*
    expect(r!.sommets * 3).toBeGreaterThan(130_000);
    // ⚠️ ON ASSERTE LES COMPTES, PAS SEULEMENT « ca ne leve pas ». Une premiere version se
    // contentait de `pdf.length > 1000` : une passe de mutation a montre qu'un exportateur qui ne
    // garderait que le PREMIER triangle du gros modele rend 2 080 octets et **passait**, tout
    // comme un flux U3D entierement REMPLI DE ZEROS apres son en-tete.
    //   *« Ca n'a pas leve » n'est pas « ca a produit le bon fichier ».*
    expect(r!.faces).toBe(50_000);
    expect(r!.sommets).toBe(150_000);
    expect(r!.pdf.length).toBeGreaterThan(2_000_000);
  });

  it('TEMOIN : un petit modele rend toujours ses comptes EXACTS', () => {
    // ⚠️ CE TEMOIN N'EN ETAIT PAS UN, ET SON COMMENTAIRE DECRIVAIT CE QU'IL NE VOYAIT PAS.
    // Il disait « sans ce temoin, un exportateur qui rendrait n'importe quoi passerait le test
    // ci-dessus » — or ses deux assertions (`not null`, `startsWith('%PDF-')`) etaient un
    // SOUS-ENSEMBLE STRICT du premier cas du fichier, qui compare deja `%PDF-1.6` sur huit
    // octets. Passe a 46 mutations, il n'en a attrape AUCUNE : la version du PDF changee de 1.6
    // a 1.7 rougit le premier cas et le laissait vert.
    //   *Un temoin qui n'asserte rien que son voisin n'asserte deja ne distingue rien — il
    //   ajoute une ligne verte, pas une garantie.*
    // Il porte desormais les COMPTES du tetraedre : 4 faces, 4 sommets (mesure, pas suppose —
    // les sommets sont dedoublonnes).
    const r = buildPdf3d(TETRA, { titre: 'Tetra' });
    expect(r).not.toBeNull();
    expect(r!.faces).toBe(4);
    expect(r!.sommets).toBe(4);
  });
});
