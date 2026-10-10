// Enregistre le crochet de resolution (voir crochet_resolution.mjs).
//
//   node --import ./noeud/crochet_ts.mjs script.mjs
//
// POURQUOI : les fichiers TypeScript de l'ERP s'importent entre eux SANS extension
// (`from './u3dWriter'`), ce que la resolution ESM de Node refuse. Plutot que de toucher a ces
// fichiers (ils doivent rester des copies INCHANGEES), on apprend a Node a essayer `.ts`.
// Node 22.18 execute le TypeScript « effacable » tel quel : rien a compiler, rien a installer.
import { register } from 'node:module';

register('./crochet_resolution.mjs', import.meta.url);
