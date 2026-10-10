// ecrire_pdf3d.mjs — ecrit le PDF 3D a partir de la scene extraite par extraire_blend.py.
//
//   node --import ./noeud/crochet_ts.mjs ./noeud/ecrire_pdf3d.mjs <ecriture.json>
//
// Lance par pdf_3d.py. Deux modes, choisis par `mode` dans ecriture.json :
//   « simple »      : le PDF 3D TEL QUE L'ERP LE FAIT. On aplatit la scene en une soupe de
//                     triangles et on appelle `buildPdf3d` de erp/atelier/exportPdf3d.ts, copie
//                     INCHANGEE de l'ERP. Un seul maillage, pas de materiau, pas d'arbre.
//   « fabrication » : pieces separees, ressources partagees, materiaux, vues nommees, par
//                     u3dWriterMulti.ts et exportPdf3dMulti.ts (ecrits a cote des fichiers de l'ERP).
//
// Sortie : le PDF, et un rapport JSON (comptes REELS du fichier) lu par pdf_3d.py.
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';

const fichierEcriture = process.argv[2];
if (!fichierEcriture) {
  console.error('usage : ecrire_pdf3d.mjs <ecriture.json>');
  process.exit(2);
}
const E = JSON.parse(readFileSync(fichierEcriture, 'utf8'));
const S = JSON.parse(readFileSync(E.scene_json, 'utf8'));
const bin = readFileSync(E.scene_bin);
const debut = performance.now();

/** Vue typee sur un morceau du binaire (copie alignee : le Buffer de Node peut ne pas l'etre). */
function tranche(Type, pos, n) {
  const octets = n * Type.BYTES_PER_ELEMENT;
  if (pos + octets > bin.length) throw new Error(`scene.bin trop court (${pos} + ${octets} > ${bin.length})`);
  const copie = new Uint8Array(octets);
  copie.set(bin.subarray(pos, pos + octets));
  return new Type(copie.buffer);
}

function maillage(i) {
  const m = S.maillages[i];
  return {
    ...m,
    positions: tranche(Float32Array, m.pos_positions, m.sommets * 3),
    indices: tranche(Uint32Array, m.pos_indices, m.triangles * 3),
    tranchesFaces: tranche(Uint32Array, m.pos_tranches, m.triangles),
    normalesXYZ: tranche(Float32Array, m.pos_normales, m.normales * 3),
    indicesNormales: tranche(Uint32Array, m.pos_indices_normales, m.triangles * 3),
  };
}

/** Remplace {faces}, {sommets}... dans les lignes. Les nombres en francais (espace insecable). */
function nombre(n) {
  return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
}
function remplir(texte, valeurs) {
  return texte.replace(/\{(\w+)\}/g, (tout, cle) => (cle in valeurs ? valeurs[cle] : tout));
}

const rapport = { mode: E.mode, sortie: E.sortie };

if (E.mode === 'simple') {
  // ---------------------------------------------------------------- tel que l'ERP le fait
  const { buildU3D } = await import('../erp/atelier/u3dWriter.ts');
  const { buildPdf3d } = await import('../erp/atelier/exportPdf3d.ts');

  // SOUPE DE TRIANGLES, transformations appliquees. Le modele Blender est Z vers le haut ;
  // `buildU3D` attend Y vers le haut et applique X = x, Y = -z, Z = y. On lui donne donc
  // (x, y, z) = (X, Z, -Y) : il retombe sur (X, Y, Z).
  const cache = new Map();
  const total = S.objets.reduce((n, o) => n + S.maillages[o.maillage].triangles, 0);
  const soupe = new Float32Array(total * 9);
  let k = 0;
  for (const o of S.objets) {
    let m = cache.get(o.maillage);
    if (!m) { m = maillage(o.maillage); cache.set(o.maillage, m); }
    const M = o.matrice;               // 16 nombres, colonnes d'abord
    const p = m.positions; const ix = m.indices;
    for (let t = 0; t < ix.length; t++) {
      const v = ix[t] * 3;
      const x = p[v]; const y = p[v + 1]; const z = p[v + 2];
      const X = M[0] * x + M[4] * y + M[8] * z + M[12];
      const Y = M[1] * x + M[5] * y + M[9] * z + M[13];
      const Z = M[2] * x + M[6] * y + M[10] * z + M[14];
      soupe[k++] = X; soupe[k++] = Z; soupe[k++] = -Y;
    }
  }
  if (k !== soupe.length) throw new Error(`soupe incomplete : ${k} sur ${soupe.length}`);

  // 1er passage : les comptes REELS (l'ecrivain de l'ERP dedoublonne les sommets et ecarte les
  // triangles degeneres), pour pouvoir les ECRIRE dans les lignes de la page.
  const u = buildU3D(soupe, { nom: E.titre });
  if (!u) throw new Error("l'ecrivain U3D de l'ERP a refuse le modele (aucun triangle valide)");
  const valeurs = {
    faces: nombre(u.faces), sommets: nombre(u.sommets), objets: nombre(S.objets.length),
    maillages: nombre(S.maillages.length), triangles_fournis: nombre(total), unite: E.unite_nom,
  };
  const lignes = E.lignes.map((l) => remplir(l, valeurs));
  const r = buildPdf3d(soupe, {
    titre: E.titre,
    lignes,
    messageRepli: E.message_repli_1,
    messageRepli2: E.message_repli_2,
  });
  if (!r) throw new Error("l'ecrivain PDF de l'ERP a refuse le modele");
  if (r.faces !== u.faces || r.sommets !== u.sommets) {
    throw new Error(`comptes incoherents entre les deux passages : ${r.faces}/${u.faces} faces`);
  }
  writeFileSync(E.sortie, r.pdf);
  if (E.sortie_u3d) writeFileSync(E.sortie_u3d, u.fichier);
  Object.assign(rapport, {
    triangles_fournis: total, faces: r.faces, sommets: r.sommets, octets_pdf: r.octets,
    octets_u3d: u.fichier.length, lignes, noeuds: 1, ressources: 1, materiaux: 0,
  });
} else if (E.mode === 'fabrication') {
  // ---------------------------------------------------------------- pieces, couleurs, vues
  const { ecrireFabrication } = await import('./fabrication.mjs');
  Object.assign(rapport, await ecrireFabrication(E, S, maillage, { nombre, remplir }));
} else {
  throw new Error(`mode inconnu : ${E.mode}`);
}

rapport.duree_ms = Math.round(performance.now() - debut);
writeFileSync(E.rapport_json, `${JSON.stringify(rapport, null, 1)}\n`);
console.log(`ECRITURE_OK ${path.basename(E.sortie)} : ${rapport.faces} faces, ${rapport.octets_pdf} octets, ${rapport.duree_ms} ms`);
