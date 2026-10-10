// envelopper_u3d.mjs — met un fichier U3D EXISTANT dans une page de PDF 3D (la meme page que l'outil).
//
//   node --import ./noeud/crochet_ts.mjs ./noeud/envelopper_u3d.mjs fichier.u3d sortie.pdf ["Titre"]
//
// A QUOI CA SERT. Devant un lecteur qui n'afficherait pas nos modeles, il faut savoir qui est en
// cause : notre U3D, ou notre page PDF. On enveloppe donc un U3D dont on SAIT qu'il s'affiche
// (un fichier ecrit par un autre logiciel) dans NOTRE page : s'il s'affiche, la page est bonne.
// La vue ne porte pas de camera : le lecteur cadre lui-meme.
import { readFileSync, writeFileSync } from 'node:fs';
import { deflateSync } from 'node:zlib';

const [fU3d, fPdf, titre] = process.argv.slice(2);
if (!fU3d || !fPdf) {
  console.error('usage : envelopper_u3d.mjs fichier.u3d sortie.pdf ["Titre"]');
  process.exit(2);
}
const { buildPdf3dMulti } = await import('../exportPdf3dMulti.ts');
const u3d = new Uint8Array(readFileSync(fU3d));
if (u3d.length < 12 || u3d[0] !== 0x55 || u3d[1] !== 0x33 || u3d[2] !== 0x44 || u3d[3] !== 0x00) {
  console.error('ce fichier ne commence pas par un en-tete U3D');
  process.exit(1);
}
const r = buildPdf3dMulti(u3d, {
  titre: titre || 'U3D enveloppe',
  lignes: [`Fichier U3D de ${u3d.length} octets, enveloppe tel quel ; la vue laisse le cadrage au lecteur.`],
  vues: [{ nom: 'Vue du lecteur', projection: 'P', fov: 45 }],
  deflate: (o) => deflateSync(o, { level: 9 }),
});
writeFileSync(fPdf, r.pdf);
console.log(`ENVELOPPE_OK ${fPdf} : ${r.octets} octets`);
