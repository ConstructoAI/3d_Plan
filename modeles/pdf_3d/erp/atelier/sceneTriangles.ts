/**
 * Ramasse les TRIANGLES de la scene 3D rendue, en coordonnees du batiment.
 *
 * POURQUOI CETTE SOURCE PLUTOT QUE LE MODELE. L'export DXF part du MODELE, ou un mur est encore
 * un polygone et une hauteur — c'est ce qui donne de vrais prismes reprenables dans AutoCAD.
 * Le PDF 3D, lui, ne cherche pas a etre reprenable : il cherche a MONTRER. Partir de la scene
 * rendue le fait beneficier gratuitement de tout ce que le DXF doit refuser : toits a croupe,
 * membrures avec leurs abouts, ouvertures percees en CSG.
 *
 * ⚠️ **CE QUI N'Y EST PAS, ET J'AVAIS ECRIT LE CONTRAIRE.** J'avais liste « mobilier » et conclu
 * par « ce qui est a l'ecran est dans le fichier ». **Faux, mesure par deux agents** : le
 * mobilier vit dans `cao-items` et les finitions (plinthes, cadrages) dans `cao-finishes`, deux
 * groups **FRERES** de `cao-building` — et `getExportRoot()` ne rend que `cao-building`.
 *
 * On garde ce perimetre, et c'est un choix : les QUATRE autres exports du module (GLB, STL, OBJ,
 * DXF) partent tous du meme group. Un PDF 3D qui, seul, contiendrait les meubles serait une
 * incoherence de plus, pas une amelioration. Mais **l'omission est desormais ANNONCEE a
 * l'utilisateur** au lieu d'etre tue — parce que meubler un rez-de-chaussee pour le montrer au
 * client est precisement l'usage de ce bouton. Inclure `cao-items` est le prochain pas evident ;
 * il exigera de traiter `InstancedMesh` (les GLB tiers peuvent en contenir, et un `InstancedMesh`
 * exporte naivement rend UNE copie a l'origine au lieu de N).
 *
 * LE REPERE. On rend les sommets RELATIFS A LA RACINE : `racine⁻¹ · mesh`.
 *
 * ⚠️ J'AI ECRIT ICI QUE C'ETAIT « exactement ce que fait l'exporteur GLB ». **C'EST FAUX**, et la
 * QA l'a mesure contre le vrai `GLTFExporter` de three 0.168 : celui-ci EMET la matrice locale de
 * la racine (`processNode`), donc le GLB CONSERVE la transform de la racine la ou nous la
 * RETIRONS. Les deux exports different d'exactement `racine.matrix`. Aujourd'hui `cao-building`
 * est a l'identite, donc les deux coincident et personne ne voit rien — c'est precisement ce qui
 * rend l'affirmation dangereuse : elle serait dementie le jour ou quelqu'un poserait une
 * transform sur le group, en silence. La phrase est corrigee plutot que le code, parce que retirer
 * la transform de la racine est le bon comportement pour un fichier autonome.
 *
 * NE MODIFIE NI `visible` NI AUCUN MATERIAU. (Il met en revanche les MATRICES a jour, par
 * `updateWorldMatrix` — j'ecrivais « ni matrice », c'etait faux ; c'est sans effet observable,
 * mais une promesse fausse dans un en-tete se paie a la relecture. Le masquage temporaire
 * des aretes avec restauration en `finally` est le fait de `caoExport.exportScene` — j'avais
 * recopie sa description ici, ou elle ne decrit rien.)
 */

import * as THREE from 'three';

export interface TrianglesScene {
  /** Sommets XYZ, 3 par sommet, 3 sommets par triangle. */
  readonly sommets: Float32Array;
  /** Nombre de triangles retenus. */
  readonly triangles: number;
  /** Maillages ecartes, par motif — jamais laisses tomber en silence. */
  readonly ecartes: Readonly<Record<string, number>>;
}

/**
 * PLAFOND DE TRIANGLES. Le U3D non compresse pese ~12 octets par sommet et ~16 par face. On
 * REFUSE au-dela plutot que de TRONQUER : un batiment coupe au triangle 400 000 est une maison
 * sans toit, et l'utilisateur croirait a un defaut du modele. Un refus chiffre lui dit quoi faire.
 *
 * MESURE au plafond (400 000 triangles) : tampon de 13,7 Mio, et selon que les sommets sont
 * partages ou non, **13,5 a 19,8 Mio de PDF pour 3,2 a 6,2 s** d'assemblage. J'avais d'abord
 * ecrit « 9,2 Mio, ~2 s » : sous-estime d'un facteur 1,5 a 3 — et c'est justement la mesure qui
 * justifie tout le dispositif de temoin d'occupation. (J'avais ecrit
 * « 300 Mo » dans la justification du premier passage : faux d'un facteur 22. Le premier passage
 * reste utile — il permet de REFUSER avant d'ecrire — mais pas pour la raison annoncee.)
 */
export const MAX_TRIANGLES_PDF3D = 400_000;

/**
 * Un objet appartient-il a une POIGNEE de manipulation (gizmo) plutot qu'au batiment ?
 *
 * CE PREDICAT VIENT D'UN DEFAUT MESURE, et c'etait le plus grave de ce module. `TransformControls`
 * de three est monte par drei en `<primitive>`, donc **comme ENFANT du group courant** — ici
 * `cao-building`. Or sa surface de saisie, `TransformControlsPlane`, est un `Mesh` de
 * **100 000 x 100 000 metres** dont c'est le MATERIAU qui est invisible, pas l'objet : un filtre
 * sur `mesh.visible` ne le voit pas.
 *
 * EFFET MESURE : un mur selectionne (outil `select` + mode `translate` = les DEUX defauts de
 * l'interface) faisait passer l'export de 12 a 136 triangles et la boite englobante a
 * ±50 000 m. Comme le PDF laisse VOLONTAIREMENT le lecteur cadrer sur cette boite, un batiment
 * de 20 m occupait 1/5000 de la vue : l'utilisateur ouvre son PDF et voit un carre vide. Il n'a
 * aucun moyen de deviner que la cause est « j'avais un mur selectionne ».
 *
 * On teste les TROIS marqueurs de la famille : le plan de saisie est attrape par le filtre de
 * materiau, mais les quatre fleches du gizmo ont un materiau bien visible.
 */
function estPoigneeDeManipulation(o: THREE.Object3D): boolean {
  const x = o as unknown as Record<string, unknown>;
  return x.isTransformControls === true
    || x.isTransformControlsGizmo === true
    || x.isTransformControlsPlane === true;
}

/** Le maillage a-t-il au moins un materiau qui REND ? `visible: false` sur le materiau suffit a
 *  effacer un objet a l'ecran ; ne filtrer que `mesh.visible` fait entrer dans le fichier de la
 *  geometrie que personne ne voit — le contraire de ce que ce module promet. */
function auMoinsUnMateriauVisible(mesh: THREE.Mesh): boolean {
  const m = mesh.material as THREE.Material | THREE.Material[] | undefined;
  if (!m) return false;
  return Array.isArray(m) ? m.some((x) => x && x.visible !== false) : m.visible !== false;
}

/**
 * @param racine  le group `cao-building` (cf. `caoExport.getExportRoot`).
 * @param max     plafond de triangles ; au-dela, `triangles` vaut 0 et le motif `plafond` porte
 *                le compte REEL, pour que l'appelant puisse l'annoncer.
 */
export function collectSceneTriangles(
  racine: THREE.Object3D,
  max: number = MAX_TRIANGLES_PDF3D,
): TrianglesScene {
  const ecartes: Record<string, number> = {};
  const compter = (motif: string, n = 1): void => { ecartes[motif] = (ecartes[motif] || 0) + n; };

  const m = new THREE.Matrix4();
  const v = new THREE.Vector3();
  // Neuf flottants de travail : les coordonnees TRANSFORMEES d'un triangle, retenues le temps
  // de les valider avant de les ecrire. Reutilise a chaque tour.
  const tmp9 = new Float64Array(9);

  // PREMIER PASSAGE : compter, pour allouer d'un coup et connaitre le total AVANT d'ecrire.
  const retenus: THREE.Mesh[] = [];
  let total = 0;
  racine.updateWorldMatrix(true, true);
  // L'INVERSE SE PREND **APRES** la mise a jour, pas avant. Le prendre avant lisait une matrice
  // PERIMEE pendant que les maillages, eux, etaient lus a jour : mesure de la QA, racine deplacee
  // a x = 100 sans rafraichir -> centre obtenu 100 au lieu de 0. Sans effet aujourd'hui
  // (`cao-building` est a l'identite), mais les deux seuls cas ou ce code sert a quelque chose
  // sont justement ceux ou il etait faux.
  const inverseRacine = new THREE.Matrix4().copy(racine.matrixWorld).invert();
  racine.traverse((o) => {
    if (!(o as THREE.Mesh).isMesh) return;
    const mesh = o as THREE.Mesh;
    // Les aretes d'aide (`caoEdge`) sont des LineSegments, deja ecartes par `isMesh` ; on garde
    // le test parce qu'un jour quelqu'un les dessinera en maillage, et le fichier serait alors
    // rempli de traits noirs sans que personne comprenne d'ou ils viennent.
    if (mesh.userData?.caoEdge) { compter('aretes'); return; }

    // ⚠️ L'ORDRE DE CES DEUX TESTS EST UN CHEMIN D'INTERFACE, pas un detail de style.
    //
    // La poignee se teste AVANT la visibilite. Quand c'etait l'inverse, le plan de saisie du
    // gizmo — invisible par son MATERIAU — tombait dans `masques`, et l'interface annoncait
    // « 26 element(s) masque(s) ne sont PAS dans le fichier » alors que l'utilisateur n'avait
    // rien masque : il avait simplement SELECTIONNE un mur, ce qui est l'outil et le mode par
    // DEFAUT. Le chemin le plus ordinaire du produit rendait donc une fausse alerte a la place
    // du message de succes, et renvoyait vers un œil qui n'avait rien a reafficher.
    //
    // Les deux motifs comptent des choses differentes et l'utilisateur n'en voit qu'un :
    // `poignees` est du bruit d'interface, `masques` est une DECISION de l'utilisateur.
    if (estPoigneeDeManipulation(mesh)) { compter('poignees'); return; }
    for (let p = mesh.parent; p; p = p.parent) {
      if (estPoigneeDeManipulation(p)) { compter('poignees'); return; }
    }
    if (!mesh.visible) { compter('masques'); return; }
    if (!auMoinsUnMateriauVisible(mesh)) { compter('masques'); return; }
    // Un parent invisible masque tout son sous-arbre, mais `traverse` le parcourt quand meme.
    for (let p = mesh.parent; p; p = p.parent) {
      if (!p.visible) { compter('masques'); return; }
    }
    const g = mesh.geometry as THREE.BufferGeometry | undefined;
    const pos = g?.getAttribute('position') as THREE.BufferAttribute | undefined;
    if (!pos || pos.itemSize !== 3) { compter('sans_geometrie'); return; }
    const idx = g?.getIndex();
    const n = Math.floor((idx ? idx.count : pos.count) / 3);
    if (n < 1) { compter('sans_geometrie'); return; }
    retenus.push(mesh);
    total += n;
  });

  if (total > max) {
    return { sommets: new Float32Array(0), triangles: 0, ecartes: { ...ecartes, plafond: total } };
  }

  const brut = new Float32Array(total * 9);
  let o = 0;
  for (const mesh of retenus) {
    m.multiplyMatrices(inverseRacine, mesh.matrixWorld);
    const g = mesh.geometry as THREE.BufferGeometry;
    const pos = g.getAttribute('position') as THREE.BufferAttribute;
    const idx = g.getIndex();
    const n = Math.floor((idx ? idx.count : pos.count) / 3);
    for (let t = 0; t < n; t++) {
      // UN TRIANGLE NON FINI N'EMPORTE PLUS TOUT LE FICHIER. L'ecrivain U3D refusait le modele
      // ENTIER au premier `NaN`, et l'interface traduisait ce refus par « la vue 3D ne contient
      // aucune geometrie » — devant un ecran plein de batiment. Mesure de la QA : UN sommet sur
      // 15 000. Or un `NaN` en sortie de CSG (percements, croupes) n'a rien d'exotique.
      // 4 999 triangles valent mieux qu'un refus incomprehensible.
      // ⚠️ LA GARDE TESTE CE QU'ON ECRIT, PAS CE QU'ON LIT — ET ELLE NE LE FAISAIT PAS.
      //
      // Elle lisait les coordonnees LOCALES (`pos.getX(src)`) et l'ecriture stockait les
      // coordonnees TRANSFORMEES (`.applyMatrix4(m)`). Une matrice qui porte un `NaN` — un
      // `position.x = NaN`, un `rotation.y = NaN`, un `position.x = 1e300` — traversait donc
      // intacte : les locales sont finies, les transformees ne le sont pas.
      //
      // MESURE (QA du 2026-08-19) : 100 maillages sains + UN maillage a `position.x = NaN` ->
      // neuf valeurs non finies entrent dans le tampon, `ecartes` reste **vide** (donc rien
      // n'est signale), l'ecrivain U3D refuse le modele ENTIER, et l'utilisateur lit
      // « Rien a exporter : la vue 3D ne contient aucune geometrie » DEVANT UN ECRAN PLEIN DE
      // BATIMENT.
      //
      // C'est mot pour mot le scenario que le commentaire ci-dessus dit avoir ferme. Il l'a
      // ferme du cote GEOMETRIE et laisse ouvert du cote TRANSFORM — le meme defaut, dans la
      // moitie qu'on n'a pas regardee.
      //   *Une garde doit s'appliquer a la valeur qui PART, jamais a celle qui arrive : entre
      //   les deux il y a un calcul, et c'est lui qui fabrique l'infini.*
      let bon = true;
      for (let j = 0; j < 3; j++) {
        const k = idx ? idx.getX(t * 3 + j) : t * 3 + j;
        v.set(pos.getX(k), pos.getY(k), pos.getZ(k)).applyMatrix4(m);
        if (!Number.isFinite(v.x) || !Number.isFinite(v.y) || !Number.isFinite(v.z)) {
          bon = false;
          break;
        }
        // Tampon fixe reutilise entre les tours : un tableau par triangle couterait 400 000
        // allocations au plafond du module.
        tmp9[j * 3] = v.x; tmp9[j * 3 + 1] = v.y; tmp9[j * 3 + 2] = v.z;
      }
      if (!bon) { compter('non_finis'); continue; }
      for (let i = 0; i < 9; i++) brut[o + i] = tmp9[i];
      o += 9;
    }
  }

  // `o` peut etre inferieur a `brut.length` si des triangles ont ete ecartes ci-dessus : on rend
  // une vue de la partie REELLEMENT ecrite. Sans cette coupe, la queue du tampon — des zeros —
  // deviendrait des triangles fantomes a l'origine.
  const sommets = o === brut.length ? brut : brut.subarray(0, o);
  return { sommets, triangles: o / 9, ecartes };
}
