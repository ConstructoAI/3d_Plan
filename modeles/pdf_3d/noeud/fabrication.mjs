// fabrication.mjs — la version « de fabrication » du PDF 3D : pieces separees, maillages partages,
// couleurs, vues nommees. Appele par ecrire_pdf3d.mjs ; l'arbre, les noms, les matieres et les
// vues ont ete decides par pdf_3d.py (ecriture.json) : ici on ne fait qu'ECRIRE.
//
// Le U3D sort de ../u3dWriterMulti.ts, le PDF de ../exportPdf3dMulti.ts (ecrits a cote des
// fichiers de l'ERP, qui restent inchanges).
import { writeFileSync } from 'node:fs';
import { deflateSync } from 'node:zlib';

export async function ecrireFabrication(E, S, maillage, { nombre, remplir }) {
  const { buildU3DMulti } = await import('../u3dWriterMulti.ts');
  const { buildPdf3dMulti } = await import('../exportPdf3dMulti.ts');

  // ---- les maillages : tels que Blender les donne (Z vers le haut, repere local de la piece) ----
  const maillages = E.ressources.map((r) => {
    const m = maillage(r.maillage);
    const d = {
      nom: r.nom,
      positions: m.positions,
      indices: m.indices,
      tranches: m.tranches > 1 ? m.tranchesFaces : undefined,
      nbTranches: m.tranches,
    };
    if (E.normales) { d.normales = m.normalesXYZ; d.indicesNormales = m.indicesNormales; }
    return d;
  });

  // ---- les nœuds : groupes (identite) et pieces (matrice monde de l'objet) ----------------------
  const noeuds = E.noeuds.map((n) => {
    if (n.type === 'groupe') return { nom: n.nom, parent: n.parent, meta: n.meta };
    return {
      nom: n.nom, parent: n.parent, matrice: n.matrice, maillage: n.ressource,
      nuanceurs: n.nuanceurs, meta: n.meta,
    };
  });

  const u = buildU3DMulti({
    noeuds, maillages, materiaux: E.materiaux, metresParUnite: E.metres_par_unite, compat: E.compat,
  });

  const valeurs = {
    faces: nombre(u.faces), sommets: nombre(u.sommets), objets: nombre(u.modeles),
    groupes: nombre(u.groupes), maillages: nombre(u.ressources), unite: E.unite_nom,
    faces_fichier: nombre(u.facesRessources),
  };
  const lignes = E.lignes.map((l) => remplir(l, valeurs));
  const r = buildPdf3dMulti(u.fichier, {
    titre: E.titre,
    lignes,
    messageRepli: E.message_repli_1,
    messageRepli2: E.message_repli_2,
    vues: E.vues.map((v) => ({
      nom: v.nom, c2w: v.c2w, co: v.co, projection: v.projection, fov: v.fov,
      etendueOrtho: v.etendue_ortho, noeuds: v.noeuds, rendu: v.rendu, eclairage: v.eclairage,
    })),
    vueDefaut: E.vue_defaut,
    rendu: E.rendu,
    eclairage: E.eclairage,
    fond: E.fond,
    arbreOuvert: E.arbre_ouvert,
    deflate: E.compression ? (o) => deflateSync(o, { level: 9 }) : undefined,
    faces: u.faces,
    proprietes: E.proprietes,
  });
  writeFileSync(E.sortie, r.pdf);
  if (E.sortie_u3d) writeFileSync(E.sortie_u3d, u.fichier);
  return {
    faces: u.faces, faces_ressources: u.facesRessources, sommets: u.sommets,
    noeuds: u.groupes + u.modeles, groupes: u.groupes, modeles: u.modeles, ressources: u.ressources,
    materiaux: u.materiaux, octets_u3d: u.fichier.length, octets_flux: r.octetsFlux,
    octets_pdf: r.octets, vues: r.vues, lignes, taille_declarations: u.tailleDeclarations,
  };
}
