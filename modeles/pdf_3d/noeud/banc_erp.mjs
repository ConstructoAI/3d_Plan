// Rejoue, sans rien installer, les tests de l'ERP qui portent sur u3dWriter.ts et exportPdf3d.ts.
//
//   node --import ./noeud/crochet_ts.mjs ./noeud/banc_erp.mjs [--json]
//
// Les fichiers de test sont les COPIES INCHANGEES de erp/__tests__ ; leur `import 'vitest'` est
// servi par vitest_minimal.mjs. Le 4e fichier de test de l'ERP, sceneTriangles.test.ts, n'est PAS
// rejoue : il importe three.js, qui n'est pas sur le poste (et l'outil ne s'en sert pas : c'est
// Blender qui fournit les triangles).
//
// CE QUE CE BANC PROUVE : que les copies de l'ERP se comportent ici comme dans l'ERP (memes
// comptes, memes octets attendus par ses propres tests). CE QU'IL NE PROUVE PAS : qu'un lecteur
// affiche le modele.
import { executer, suites } from './vitest_minimal.mjs';

const FICHIERS = [
  '../erp/__tests__/u3dWriter.test.ts',
  '../erp/__tests__/u3dInvariants.test.ts',
  '../erp/__tests__/exportPdf3d.test.ts',
];

const parFichier = [];
for (const f of FICHIERS) {
  const avant = suites.length;
  await import(f);
  parFichier.push({ fichier: f.replace('../erp/__tests__/', ''), suites: suites.slice(avant) });
}

const res = await executer();
const json = process.argv.includes('--json');
const lignes = [];
for (const pf of parFichier) {
  const noms = new Set(pf.suites.map((s) => s.nom));
  const d = res.details.filter((x) => noms.has(x.suite));
  const ok = d.filter((x) => x.ok).length;
  lignes.push(`${pf.fichier} : ${ok} sur ${d.length} test(s) passent`);
  for (const x of d) {
    lignes.push(`  ${x.ok ? 'OK   ' : 'ECHEC'} ${x.test}${x.ok ? '' : `\n        -> ${x.message}`}`);
  }
}
const total = res.passes + res.echecs.length;
lignes.push(`TOTAL : ${res.passes} sur ${total} test(s) de l'ERP passent ; ${res.echecs.length} echec(s)`);
lignes.push('NON REJOUE : sceneTriangles.test.ts (demande three.js, absent du poste)');
if (json) {
  process.stdout.write(`${JSON.stringify({ passes: res.passes, total, echecs: res.echecs, lignes })}\n`);
} else {
  process.stdout.write(`${lignes.join('\n')}\n`);
}
process.exit(res.echecs.length ? 1 : 0);
