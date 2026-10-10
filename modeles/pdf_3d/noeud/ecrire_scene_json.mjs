// ecrire_scene_json.mjs — ecrit un U3D (et, sur demande, son PDF) depuis une petite scene en JSON.
// Sert aux bancs d'essai (banc_outil.py) et aux essais de compatibilite devant un lecteur.
//
//   node --import ./noeud/crochet_ts.mjs ./noeud/ecrire_scene_json.mjs scene.json sortie.u3d [sortie.pdf]
//
// scene.json : { noeuds:[{nom,parent,matrice?,maillage?,nuanceurs?,meta?}],
//                maillages:[{nom,positions:[…],indices:[…],tranches?,nbTranches?,normales?,indicesNormales?}],
//                materiaux:[{nom,ambiant,diffus,speculaire,emissif,reflectivite,opacite}],
//                metresParUnite?, compat?, pdf?: {titre, lignes, vues, vueDefaut, rendu, eclairage, fond, arbreOuvert, compression,
//                        proprietes?: {titre, auteur, sujet}} }
import { readFileSync, writeFileSync } from 'node:fs';
import { deflateSync } from 'node:zlib';

const [fScene, fU3d, fPdf] = process.argv.slice(2);
if (!fScene || !fU3d) {
  console.error('usage : ecrire_scene_json.mjs scene.json sortie.u3d [sortie.pdf]');
  process.exit(2);
}
const { buildU3DMulti } = await import('../u3dWriterMulti.ts');
const J = JSON.parse(readFileSync(fScene, 'utf8'));
try {
  const scene = {
    noeuds: J.noeuds,
    maillages: J.maillages.map((m) => ({
      nom: m.nom,
      positions: new Float32Array(m.positions),
      indices: new Uint32Array(m.indices),
      tranches: m.tranches ? new Uint32Array(m.tranches) : undefined,
      nbTranches: m.nbTranches,
      normales: m.normales ? new Float32Array(m.normales) : undefined,
      indicesNormales: m.indicesNormales ? new Uint32Array(m.indicesNormales) : undefined,
    })),
    materiaux: J.materiaux || [],
    metresParUnite: J.metresParUnite,
    compat: J.compat,
  };
  const u = buildU3DMulti(scene);
  writeFileSync(fU3d, u.fichier);
  const rapport = { ...u, fichier: undefined, octets_u3d: u.fichier.length };
  if (fPdf) {
    const { buildPdf3dMulti } = await import('../exportPdf3dMulti.ts');
    const P = J.pdf || {};
    const r = buildPdf3dMulti(u.fichier, {
      titre: P.titre, lignes: P.lignes, messageRepli: P.messageRepli, messageRepli2: P.messageRepli2,
      vues: P.vues, vueDefaut: P.vueDefaut, rendu: P.rendu, eclairage: P.eclairage, fond: P.fond,
      arbreOuvert: P.arbreOuvert,
      proprietes: P.proprietes,
      deflate: P.compression === false ? undefined : (o) => deflateSync(o, { level: 9 }),
      faces: u.faces,
    });
    writeFileSync(fPdf, r.pdf);
    rapport.octets_pdf = r.octets;
  }
  console.log(`SCENE_OK ${JSON.stringify(rapport)}`);
} catch (err) {
  console.log(`SCENE_REFUS ${err instanceof Error ? err.message : String(err)}`);
  process.exit(1);
}
