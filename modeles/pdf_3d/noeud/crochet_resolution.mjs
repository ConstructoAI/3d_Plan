// Crochet de resolution des modules, charge par crochet_ts.mjs.
//
// Deux regles, et rien d'autre :
//   1. un import RELATIF sans extension (`./u3dWriter`, `../atelier/exportPdf3d`) qui echoue est
//      reessaye avec `.ts` ;
//   2. l'import nu `vitest` mene au mini-banc local (vitest_minimal.mjs), pour rejouer les tests
//      de l'ERP sans installer vitest.
const VITEST_LOCAL = new URL('./vitest_minimal.mjs', import.meta.url).href;

export async function resolve(specifier, context, nextResolve) {
  if (specifier === 'vitest') {
    return { url: VITEST_LOCAL, shortCircuit: true, format: 'module' };
  }
  try {
    return await nextResolve(specifier, context);
  } catch (err) {
    const relatif = specifier.startsWith('./') || specifier.startsWith('../');
    if (relatif && !/\.(?:[cm]?[jt]s|json)$/i.test(specifier)) {
      return nextResolve(`${specifier}.ts`, context);
    }
    throw err;
  }
}
