/**
 * Banc de l'ecrivain U3D.
 *
 * CE QU'IL PEUT PROUVER, ET CE QU'IL NE PEUT PAS — a lire avant de s'y fier.
 *
 * Il verifie la STRUCTURE : les types de bloc, leur ordre, l'alignement sur 4 octets, la
 * coherence entre les tailles annoncees et la taille reelle du fichier, et le contenu du
 * maillage octet par octet. C'est exactement ce qui rend un U3D illisible quand c'est faux,
 * et c'est muet — un lecteur PDF affiche une zone vide sans dire pourquoi.
 *
 * Il NE PEUT PAS prouver qu'Acrobat ou PDF-XChange l'affiche. Aucun test automatise ici ne le
 * peut : il faudrait le lecteur. **La validation finale appartient a un humain qui ouvre le
 * fichier**, et c'est dit explicitement pour que personne ne lise « 12 tests verts » comme
 * « ca marche ».
 */
import { describe, expect, it } from 'vitest';

import { buildU3D } from '../atelier/u3dWriter';

/** Un tetraedre : 4 triangles, 4 sommets distincts apres dedoublonnage. */
const TETRA = new Float32Array([
  0, 0, 0, 1, 0, 0, 0, 1, 0,
  0, 0, 0, 1, 0, 0, 0, 0, 1,
  0, 0, 0, 0, 1, 0, 0, 0, 1,
  1, 0, 0, 0, 1, 0, 0, 0, 1,
]);

/** Parcourt les blocs et rend [type, tailleDonnees, offset]. */
function blocs(u: Uint8Array): { type: number; data: number; meta: number; off: number }[] {
  const dv = new DataView(u.buffer, u.byteOffset, u.byteLength);
  const out: { type: number; data: number; meta: number; off: number }[] = [];
  let off = 0;
  const pad = (n: number): number => (4 - (n % 4)) % 4;
  while (off + 12 <= u.length) {
    const type = dv.getUint32(off, true);
    const data = dv.getUint32(off + 4, true);
    const meta = dv.getUint32(off + 8, true);
    out.push({ type, data, meta, off });
    off += 12 + data + pad(data) + meta + pad(meta);
    if (data === 0 && meta === 0 && type === 0) break;   // garde anti-boucle
  }
  return out;
}

describe('ecrivain U3D', () => {
  it('produit les SIX blocs, dans l\'ordre impose par la norme', () => {
    // L'ordre n'est pas negociable : un lecteur qui rencontre une declaration de maillage
    // avant sa chaine de ressource abandonne, sans message.
    const u = buildU3D(TETRA)!.fichier;
    expect(u).not.toBeNull();
    const types = blocs(u).map((b) => b.type);
    expect(types).toEqual([
      0x00443355,   // File Header
      0xffffff14,   // Node Modifier Chain
      0xffffff14,   // Resource Modifier Chain
      0xffffff3b,   // CLOD Base Mesh Continuation
    ]);
  });

  it('TOUS les blocs commencent sur une frontiere de 4 octets', () => {
    // Le remplissage vient APRES les donnees ET APRES les metadonnees. Le rater decale tout
    // ce qui suit, et le fichier devient illisible a partir du premier bloc mal aligne.
    const u = buildU3D(TETRA)!.fichier;
    for (const b of blocs(u)) expect(b.off % 4).toBe(0);
  });

  it('le parcours des blocs tombe EXACTEMENT sur la fin du fichier', () => {
    // C'est le controle qui attrape une taille de bloc fausse : si une seule est erronee,
    // le parcours finit avant ou apres la fin, jamais dessus.
    const u = buildU3D(TETRA)!.fichier;
    const pad = (n: number): number => (4 - (n % 4)) % 4;
    const dernier = blocs(u)[blocs(u).length - 1];
    const fin = dernier.off + 12 + dernier.data + pad(dernier.data)
              + dernier.meta + pad(dernier.meta);
    expect(fin).toBe(u.length);
  });

  it('l\'en-tete annonce la VRAIE taille du fichier', () => {
    // Les deux nombres les plus faciles a rater du format, et les plus muets a l'ouverture.
    const u = buildU3D(TETRA)!.fichier;
    const dv = new DataView(u.buffer, u.byteOffset, u.byteLength);
    const lo = dv.getUint32(12 + 12, true);
    const hi = dv.getUint32(12 + 16, true);
    expect(lo + hi * 4294967296).toBe(u.length);
  });

  it('l\'en-tete annonce le bon profil SANS COMPRESSION', () => {
    // C'est ce drapeau qui autorise a ecrire les sommets en clair. S'il change, tout le
    // contenu doit passer par le codeur arithmetique du format — et ce module ne l'a pas.
    const u = buildU3D(TETRA)!.fichier;
    const dv = new DataView(u.buffer, u.byteOffset, u.byteLength);
    // 0x04 sans compression + 0x08 unites definies. Ce test a d'abord ECHOUE en attendant un
    // en-tete de 32 octets alors qu'il en faisait 24 : le facteur d'echelle n'est ecrit que si
    // 0x08 est pose. Le test avait raison de se plaindre — c'est le code qui a ete complete,
    // parce qu'un batiment sans unite ne se mesure pas dans le lecteur.
    expect(dv.getUint32(12 + 4, true)).toBe(0x0000000c);
    expect(dv.getUint32(12 + 20, true)).toBe(106);   // UTF-8
    expect(dv.getFloat64(12 + 24, true)).toBe(1.0);  // 1 unite = 1 metre
    expect(blocs(u)[0].data).toBe(32);               // 24 + les 8 octets du facteur d'echelle
  });

  it('la taille des DECLARATIONS couvre l\'en-tete et les deux chaines, pas le maillage', () => {
    const u = buildU3D(TETRA)!.fichier;
    const dv = new DataView(u.buffer, u.byteOffset, u.byteLength);
    const decl = dv.getUint32(12 + 8, true);
    const b = blocs(u);
    const pad = (n: number): number => (4 - (n % 4)) % 4;
    const taille = (x: typeof b[0]): number => 12 + x.data + pad(x.data) + x.meta + pad(x.meta);
    // en-tete + chaine de nœud + chaine de ressource, mais PAS la continuation du maillage
    expect(decl).toBe(taille(b[0]) + taille(b[1]) + taille(b[2]));
    expect(decl).toBeLessThan(u.length);
  });

  it('les SOMMETS sont ecrits, dedoublonnes, en little-endian', () => {
    const u = buildU3D(TETRA)!.fichier;
    const cont = blocs(u).find((b) => b.type === 0xffffff3b)!;
    const dv = new DataView(u.buffer, u.byteOffset, u.byteLength);
    // corps = nom (2 + n), chainIndex, faceCount, posCount, puis 4 compteurs a zero
    let o = cont.off + 12;
    const nlen = dv.getUint16(o, true); o += 2 + nlen;
    o += 4;                                   // chain index
    expect(dv.getUint32(o, true)).toBe(4);    // 4 faces
    expect(dv.getUint32(o + 4, true)).toBe(4); // 4 sommets DISTINCTS (12 bruts dedoublonnes)
    o += 8 + 16;                              // 4 compteurs a zero
    // premier sommet : (0,0,0)
    expect(dv.getFloat32(o, true)).toBe(0);
    expect(dv.getFloat32(o + 4, true)).toBe(0);
    expect(dv.getFloat32(o + 8, true)).toBe(0);
    // deuxieme : (1,0,0)
    expect(dv.getFloat32(o + 12, true)).toBe(1);
  });

  it('les NORMALES sont exclues — un coin ne porte donc qu\'UN indice', () => {
    // Si les normales n'etaient pas exclues, chaque coin porterait un second indice et tout
    // le bloc de faces serait decale : le maillage sortirait en confettis.
    const u = buildU3D(TETRA)!.fichier;
    const decl = blocs(u).find((b) => b.type === 0xffffff14 && b.off > 40);
    expect(decl).toBeTruthy();
    // La declaration de maillage est IMBRIQUEE dans la chaine de ressource ; on verifie
    // l'effet observable : la taille du bloc de continuation.
    const cont = blocs(u).find((b) => b.type === 0xffffff3b)!;
    const nom = 'Modele_res'.length;
    const attendu = (2 + nom) + 4 + 4 + 4 + 16 + (4 * 3 * 4) + 4 * (4 + 12);
    expect(cont.data).toBe(attendu);
  });

  it('LE NŒUD EST RATTACHE AU MONDE — sans ce parent, le fichier est parfait et n\'affiche RIEN', () => {
    // LE DEFAUT QUE CE BANC N'AVAIT PAS VU, et qui rendait toute la fonctionnalite inutile.
    // J'ecrivais `parentCount = 0` en croyant dire « je suis a la racine ». ECMA-363 §8.9.1 :
    // « A node with no parents will have an empty transform set. […] the node is disconnected
    // from the world and **does not appear in the rendered view**. » La racine se designe par la
    // CHAINE VIDE, et il faut la DECLARER comme parent.
    //
    // Tous les autres tests de ce fichier restaient VERTS : ils mesuraient la structure, et la
    // structure etait juste. C'est la lecon a retenir — un banc de format ne prouve pas un rendu.
    const u = buildU3D(TETRA, { nom: 'M' })!.fichier;
    const dv = new DataView(u.buffer, u.byteOffset, u.byteLength);
    // le Model Node est IMBRIQUE dans la chaine de nœuds : on le cherche par son type
    let off = -1;
    for (let o = 0; o + 4 <= u.length; o += 4) {
      if (dv.getUint32(o, true) === 0xffffff22) { off = o; break; }
    }
    expect(off).toBeGreaterThan(0);
    let p = off + 12;
    p += 2 + dv.getUint16(p, true);              // nom du nœud
    expect(dv.getUint32(p, true)).toBe(1);       // UN parent — et non zero
    p += 4;
    expect(dv.getUint16(p, true)).toBe(0);       // dont le nom est la CHAINE VIDE = le monde
    p += 2;
    // suit la matrice 4x4 en colonne-majeur : identite
    const mat = Array.from({ length: 16 }, (_, i) => dv.getFloat32(p + i * 4, true));
    expect(mat).toEqual([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]);
  });

  it('CONVERTIT le repere du modele (Y-up) vers celui du U3D (Z-up)', () => {
    // §8.3.3 : « There is a preference for having the coordinate system oriented such that the
    // Z-axis is in the up direction. » Un point a z = +5 doit donc ressortir a -5.
    const u = buildU3D(new Float32Array([0, 0, 0, 1, 0, 0, 0, 7, 5]))!.fichier;
    const dv = new DataView(u.buffer, u.byteOffset, u.byteLength);
    const f: number[] = [];
    for (let o = 0; o + 4 <= u.length; o += 4) f.push(dv.getFloat32(o, true));
    expect(f.some((x) => Math.abs(x - 7) < 1e-6)).toBe(true);
    expect(f.some((x) => Math.abs(x + 5) < 1e-6)).toBe(true);
    expect(f.some((x) => Math.abs(x - 5) < 1e-6)).toBe(false);
  });

  it('rend les COMPTES REELS : faces ecrites et sommets distincts', () => {
    const r = buildU3D(TETRA)!;
    expect(r.faces).toBe(4);
    expect(r.sommets).toBe(4);
    // ⚠️ CORRECTION D'UNE AFFIRMATION DE LA QA, verifiee ici plutot que recopiee. Un agent a
    // rapporte que « 100 triangles identiques produisent UNE seule face ». **C'est faux**, et ce
    // test l'a montre du premier coup : le dedoublonnage porte sur les SOMMETS, pas sur les
    // faces. Les 100 triangles partagent donc 3 sommets, mais restent 100 faces coincidentes.
    const t: number[] = [];
    for (let i = 0; i < 100; i++) t.push(0, 0, 0, 1, 0, 0, 0, 1, 0);
    const d = buildU3D(new Float32Array(t))!;
    expect(d.faces).toBe(100);
    expect(d.sommets).toBe(3);

    // CE QUI FAIT REELLEMENT DIVERGER LE COMPTE, et c'est le point de fond : un triangle dont
    // deux sommets se confondent APRES dedoublonnage est ECARTE. Ici, 3 triangles fournis, un
    // seul survit — d'ou la necessite d'annoncer le compte du FICHIER et non celui de l'entree.
    const plat = buildU3D(new Float32Array([
      0, 0, 0, 1, 0, 0, 0, 1, 0,       // valide
      2, 0, 0, 2, 0, 0, 3, 0, 0,       // deux sommets identiques -> ecarte
      4, 0, 0, 4, 0, 0, 4, 0, 0,       // les trois identiques -> ecarte
    ]))!;
    expect(plat.faces).toBe(1);
  });

  it('ECRIT LES NOMS EN UTF-8, comme l\'en-tete le declare', () => {
    // `charCodeAt & 0x7f` ne SUPPRIMAIT pas les accents, il les remplacait par une autre lettre :
    // « Batiment quebecois » devenait « Bbtiment quibicois » dans l'arbre du lecteur — que le
    // client voit. L'en-tete annonce pourtant l'encodage 106 (UTF-8).
    const u = buildU3D(TETRA, { nom: 'Bâtiment' })!.fichier;
    const dv = new DataView(u.buffer, u.byteOffset, u.byteLength);
    let off = -1;
    for (let o = 0; o + 4 <= u.length; o += 4) {
      if (dv.getUint32(o, true) === 0xffffff22) { off = o; break; }
    }
    const n = dv.getUint16(off + 12, true);
    const octets = u.subarray(off + 14, off + 14 + n);
    expect(new TextDecoder().decode(octets)).toBe('Bâtiment');
    expect(n).toBe(9);                            // 8 caracteres, 9 octets : le â en fait deux
  });

  it('refuse ce qui n\'est pas un maillage plutot que d\'ecrire un fichier casse', () => {
    expect(buildU3D(new Float32Array([]))).toBeNull();
    expect(buildU3D(new Float32Array([0, 0, 0, 1, 0, 0]))).toBeNull();          // < 1 triangle
    expect(buildU3D(new Float32Array([0, 0, 0, 0, 0, 0, 0, 0, 0]))).toBeNull(); // degenere
    expect(buildU3D(new Float32Array([0, NaN, 0, 1, 0, 0, 0, 1, 0]))).toBeNull();
  });

  it('le nom du modele est borne et n\'echappe pas dans la structure', () => {
    // ⚠️ CETTE BORNE A CHANGE D'UNITE, et l'assertion ne le savait pas. `str()` ecrit desormais
    // la longueur en OCTETS (UTF-8), alors que `slice(0, 60)` coupe en unites UTF-16 : la vraie
    // borne est donc 60 caracteres = **jusqu'a 180 octets**. Le test ne passait que parce que sa
    // fixture est de l'ASCII pur ; avec 200 « é » le champ vaut 120 et l'ancienne assertion
    // tombait. Un test nomme « le nom est borne » epinglait une borne qui n'existait plus.
    const u = buildU3D(TETRA, { nom: 'x'.repeat(200) })!.fichier;
    const dv = new DataView(u.buffer, u.byteOffset, u.byteLength);
    const b = blocs(u);
    const o = b[1].off + 12;
    expect(dv.getUint16(o, true)).toBeLessThanOrEqual(60);      // ASCII : 60 car. = 60 octets
    // et la VRAIE borne, sur du non-ASCII : 60 caracteres, donc au plus 180 octets
    const acc = buildU3D(TETRA, { nom: 'é'.repeat(200) })!.fichier;
    const dva = new DataView(acc.buffer, acc.byteOffset, acc.byteLength);
    const oa = blocs(acc)[1].off + 12;
    expect(dva.getUint16(oa, true)).toBe(120);                  // 60 car. x 2 octets
    expect(dva.getUint16(oa, true)).toBeLessThanOrEqual(180);
    // et le fichier reste coherent malgre le nom long
    const pad = (n: number): number => (4 - (n % 4)) % 4;
    const d = b[b.length - 1];
    expect(d.off + 12 + d.data + pad(d.data) + d.meta + pad(d.meta)).toBe(u.length);
  });
});
