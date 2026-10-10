// Mini-banc compatible avec ce que les tests de l'ERP utilisent de vitest : describe, it, expect.
//
// CE N'EST PAS VITEST. Il sert a rejouer, sans rien installer, les fichiers de test de l'ERP
// copies tels quels dans erp/__tests__ (leur `import … from 'vitest'` arrive ici par le crochet
// de resolution). Seuls les comparateurs que ces fichiers emploient existent ; tout autre appel
// leve une erreur claire au lieu de passer en silence.
import { isDeepStrictEqual } from 'node:util';

export const suites = [];
let courante = null;

export function describe(nom, fn) {
  const s = { nom, tests: [] };
  suites.push(s);
  const precedente = courante;
  courante = s;
  try { fn(); } finally { courante = precedente; }
}

export function it(nom, fn) {
  if (!courante) { describe('(hors suite)', () => it(nom, fn)); return; }
  courante.tests.push({ nom, fn });
}
export const test = it;

function montre(v) {
  if (typeof v === 'string') return JSON.stringify(v.length > 80 ? `${v.slice(0, 77)}...` : v);
  if (v instanceof Uint8Array) return `Uint8Array(${v.length})`;
  try { const s = JSON.stringify(v); return s && s.length > 120 ? `${s.slice(0, 117)}...` : String(s); }
  catch { return String(v); }
}

function egalProfond(a, b) {
  // vitest `toEqual` : egalite de structure. Les tests de l'ERP ne comparent que des tableaux de
  // nombres et de petits objets : l'egalite stricte de Node convient.
  return isDeepStrictEqual(a, b);
}

function comparateurs(recu, inverse) {
  const verifie = (ok, attendu) => {
    if (ok === inverse) {
      throw new Error(`attendu ${inverse ? 'PAS ' : ''}${attendu} ; recu ${montre(recu)}`);
    }
  };
  const c = {
    toBe: (v) => verifie(Object.is(recu, v), `toBe(${montre(v)})`),
    toEqual: (v) => verifie(egalProfond(recu, v), `toEqual(${montre(v)})`),
    toBeNull: () => verifie(recu === null, 'null'),
    toBeDefined: () => verifie(recu !== undefined, 'defini'),
    toBeTruthy: () => verifie(Boolean(recu), 'vrai'),
    toBeGreaterThan: (v) => verifie(recu > v, `> ${v}`),
    toBeGreaterThanOrEqual: (v) => verifie(recu >= v, `>= ${v}`),
    toBeLessThan: (v) => verifie(recu < v, `< ${v}`),
    toBeLessThanOrEqual: (v) => verifie(recu <= v, `<= ${v}`),
    toContain: (v) => verifie(
      typeof recu === 'string' ? recu.includes(v) : Array.from(recu).includes(v),
      `contient ${montre(v)}`),
    toMatch: (v) => verifie(v instanceof RegExp ? v.test(recu) : String(recu).includes(v),
      `correspond a ${v}`),
    toHaveLength: (n) => verifie(recu != null && recu.length === n, `longueur ${n}`),
  };
  return new Proxy(c, {
    get(cible, cle) {
      if (cle in cible) return cible[cle];
      if (cle === 'not') return comparateurs(recu, !inverse);
      if (typeof cle === 'symbol' || cle === 'then') return undefined;
      throw new Error(`comparateur « ${String(cle)} » absent du mini-banc (vitest_minimal.mjs)`);
    },
  });
}

export function expect(recu) {
  return comparateurs(recu, false);
}

/** Execute toutes les suites enregistrees. Rend { passes, echecs: [{suite, test, message}] }. */
export async function executer() {
  let passes = 0;
  const echecs = [];
  const details = [];
  for (const s of suites) {
    for (const t of s.tests) {
      const debut = performance.now();
      try {
        await t.fn();
        passes += 1;
        details.push({ suite: s.nom, test: t.nom, ok: true, ms: performance.now() - debut });
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        echecs.push({ suite: s.nom, test: t.nom, message });
        details.push({ suite: s.nom, test: t.nom, ok: false, ms: performance.now() - debut, message });
      }
    }
  }
  return { passes, echecs, details };
}
