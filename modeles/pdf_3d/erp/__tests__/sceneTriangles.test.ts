/**
 * Banc du ramasseur de triangles.
 *
 * CE FICHIER N'EXISTAIT PAS, et c'est la ou vivait le defaut le plus grave du lot : la poignee
 * de manipulation (`TransformControls`) est montee par drei DANS le group `cao-building`, et sa
 * surface de saisie est un plan de **100 000 x 100 000 metres** dont c'est le MATERIAU qui est
 * invisible, pas l'objet. Un simple mur selectionne — l'outil et le mode par DEFAUT — faisait
 * passer la boite englobante a ±50 000 m. Comme le PDF laisse le lecteur cadrer sur cette boite,
 * un batiment de 20 m tombait a 1/5000 de la vue : un carre vide.
 *
 * D'ou le premier test ci-dessous : **une borne sur l'ETENDUE**. Il n'attrape pas un objet
 * nomme, il attrape toute la famille — y compris les gizmos que personne n'a encore ecrits.
 */
import * as THREE from 'three';
import { describe, expect, it } from 'vitest';

import { collectSceneTriangles, MAX_TRIANGLES_PDF3D } from '../atelier/sceneTriangles';

/** Une racine `cao-building` contenant un mur de 4 x 2,5 x 0,2 m. */
function racineAvecMur(): THREE.Object3D {
  const scene = new THREE.Scene();
  const racine = new THREE.Group();
  racine.name = 'cao-building';
  scene.add(racine);
  racine.add(new THREE.Mesh(new THREE.BoxGeometry(4, 2.5, 0.2), new THREE.MeshBasicMaterial()));
  return racine;
}

function etendue(s: Float32Array): number {
  let m = 0;
  for (let i = 0; i < s.length; i++) m = Math.max(m, Math.abs(s[i]));
  return m;
}

describe('ramasseur de triangles', () => {
  it('ramasse un mur simple', () => {
    const r = collectSceneTriangles(racineAvecMur());
    expect(r.triangles).toBe(12);
    expect(r.sommets.length).toBe(12 * 9);
    expect(etendue(r.sommets)).toBeCloseTo(2, 5);
  });

  it('LA POIGNEE DE MANIPULATION N\'ENTRE PAS — et la borne porte sur l\'ETENDUE', () => {
    // On reproduit la forme du defaut sans dependre de drei : un objet portant le marqueur
    // `isTransformControls`, avec dessous un plan geant au materiau invisible et des fleches au
    // materiau bien visible. Les deux doivent etre ecartes.
    const racine = racineAvecMur();
    const tc = new THREE.Group() as THREE.Group & { isTransformControls?: boolean };
    tc.isTransformControls = true;
    const plan = new THREE.Mesh(
      new THREE.PlaneGeometry(100000, 100000, 2, 2),
      new THREE.MeshBasicMaterial({ visible: false }),
    );
    (plan as unknown as { isTransformControlsPlane: boolean }).isTransformControlsPlane = true;
    tc.add(plan);
    tc.add(new THREE.Mesh(new THREE.ConeGeometry(0.5, 1), new THREE.MeshBasicMaterial()));
    racine.add(tc);

    const r = collectSceneTriangles(racine);
    expect(r.triangles).toBe(12);                       // le mur, rien d'autre
    expect(etendue(r.sommets)).toBeLessThan(10);        // AUCUN sommet a 50 000
    expect(r.ecartes.poignees).toBeGreaterThan(0);      // et l'ecart est COMPTE
  });

  it('un materiau `visible: false` efface l\'objet a l\'ecran : il ne doit pas entrer', () => {
    const racine = racineAvecMur();
    racine.add(new THREE.Mesh(
      new THREE.BoxGeometry(1, 1, 1),
      new THREE.MeshBasicMaterial({ visible: false }),
    ));
    const r = collectSceneTriangles(racine);
    expect(r.triangles).toBe(12);
    expect(r.ecartes.masques).toBe(1);
  });

  it('un maillage dont le `visible` PROPRE est faux ne doit pas entrer', () => {
    // MUTATION SURVIVANTE trouvee au retest : supprimer la ligne `if (!mesh.visible)` laissait
    // les 9 tests VERTS. Aucun ne couvrait le cas le plus simple — l'oeil clique sur UN element.
    // Or c'est exactement le geste que le message de plafond conseille a l'utilisateur.
    const racine = racineAvecMur();
    const cache = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), new THREE.MeshBasicMaterial());
    cache.visible = false;
    racine.add(cache);
    const r = collectSceneTriangles(racine);
    expect(r.triangles).toBe(12);
    expect(r.ecartes.masques).toBe(1);
  });

  it('LA POIGNEE NE COMPTE PAS COMME « MASQUEE » — sinon fausse alerte au chemin par defaut', () => {
    // LE DEFAUT QUE L'ORDRE DES TESTS PRODUISAIT. Le plan de saisie du gizmo est invisible par son
    // MATERIAU : quand le test de materiau passait AVANT celui de poignee, il tombait dans
    // `masques`, et l'interface annoncait « 26 element(s) masque(s) ne sont PAS dans le fichier »
    // alors que l'utilisateur avait seulement SELECTIONNE un mur — l'outil et le mode par DEFAUT.
    // Le chemin le plus ordinaire du produit rendait une fausse alerte a la place du succes.
    const racine = racineAvecMur();
    const tc = new THREE.Group() as THREE.Group & { isTransformControls?: boolean };
    tc.isTransformControls = true;
    const plan = new THREE.Mesh(
      new THREE.PlaneGeometry(100000, 100000, 2, 2),
      new THREE.MeshBasicMaterial({ visible: false }),
    );
    tc.add(plan);
    racine.add(tc);
    const r = collectSceneTriangles(racine);
    expect(r.ecartes.poignees).toBeGreaterThan(0);
    expect(r.ecartes.masques).toBeUndefined();   // RIEN ne doit tomber dans « masques »
  });

  it('un ANCETRE invisible masque tout son sous-arbre', () => {
    const racine = racineAvecMur();
    const g = new THREE.Group();
    g.visible = false;
    g.add(new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), new THREE.MeshBasicMaterial()));
    racine.add(g);
    const r = collectSceneTriangles(racine);
    expect(r.triangles).toBe(12);
    expect(r.ecartes.masques).toBe(1);
  });

  it('UN TRIANGLE NON FINI N\'EMPORTE PLUS TOUT LE MODELE', () => {
    // L'ecrivain U3D refusait le fichier ENTIER au premier `NaN`, et l'interface traduisait ce
    // refus par « la vue 3D ne contient aucune geometrie » — devant un ecran plein de batiment.
    // Un `NaN` en sortie de CSG n'a rien d'exotique : 4 999 triangles valent mieux qu'un refus.
    const racine = racineAvecMur();
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array([
      0, 0, 0, 1, 0, 0, 0, 1, 0,            // valide
      0, 0, 0, NaN, 0, 0, 0, 1, 0,          // un seul sommet non fini
    ]), 3));
    racine.add(new THREE.Mesh(g, new THREE.MeshBasicMaterial()));
    const r = collectSceneTriangles(racine);
    expect(r.triangles).toBe(13);                       // 12 + le triangle sain
    expect(r.ecartes.non_finis).toBe(1);
    expect(r.sommets.length).toBe(13 * 9);              // pas de queue de zeros
    for (let i = 0; i < r.sommets.length; i++) expect(Number.isFinite(r.sommets[i])).toBe(true);
  });

  it('le repere est RELATIF A LA RACINE, et l\'inverse est pris APRES la mise a jour', () => {
    // Prendre l'inverse AVANT `updateWorldMatrix` lisait une matrice PERIMEE pendant que les
    // maillages, eux, etaient lus a jour. Mesure d'origine : centre a 100 au lieu de 0.
    const scene = new THREE.Scene();
    const racine = new THREE.Group();
    racine.name = 'cao-building';
    scene.add(racine);
    racine.add(new THREE.Mesh(new THREE.BoxGeometry(2, 2, 2), new THREE.MeshBasicMaterial()));
    racine.position.set(100, 0, 0);          // deplacee SANS rafraichir les matrices
    const r = collectSceneTriangles(racine);
    expect(etendue(r.sommets)).toBeCloseTo(1, 5);   // et non 101
  });

  it('REFUSE au-dela du plafond au lieu de tronquer le batiment', () => {
    const racine = racineAvecMur();
    const r = collectSceneTriangles(racine, 5);
    expect(r.triangles).toBe(0);
    expect(r.ecartes.plafond).toBe(12);      // le compte REEL, pour pouvoir l'annoncer
    expect(MAX_TRIANGLES_PDF3D).toBeGreaterThan(1000);
  });

  it('un maillage sans geometrie exploitable est ECARTE, pas plante', () => {
    const racine = racineAvecMur();
    racine.add(new THREE.Mesh(new THREE.BufferGeometry(), new THREE.MeshBasicMaterial()));
    const r = collectSceneTriangles(racine);
    expect(r.triangles).toBe(12);
    expect(r.ecartes.sans_geometrie).toBe(1);
  });

  it('une geometrie INDEXEE est deroulee correctement', () => {
    const scene = new THREE.Scene();
    const racine = new THREE.Group();
    racine.name = 'cao-building';
    scene.add(racine);
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(
      new Float32Array([0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 0]), 3));
    g.setIndex([0, 1, 2, 1, 3, 2]);
    racine.add(new THREE.Mesh(g, new THREE.MeshBasicMaterial()));
    const r = collectSceneTriangles(racine);
    expect(r.triangles).toBe(2);
    expect(r.sommets.length).toBe(18);
  });
});

describe('une MATRICE non finie — le jumeau que la garde avait laissé ouvert', () => {
  /**
   * ⚠️ LE DÉFAUT, MESURÉ. La garde de finitude lisait les coordonnées **LOCALES** et l'écriture
   * stockait les coordonnées **TRANSFORMÉES**. Une matrice portant un `NaN` — un
   * `position.x = NaN`, un `rotation.y = NaN`, un `position.x = 1e300` — traversait donc intacte.
   *
   * CE QUE L'UTILISATEUR VOYAIT : neuf valeurs non finies entraient dans le tampon, `ecartes`
   * restait VIDE (donc rien n'était signalé), l'écrivain U3D refusait le modèle ENTIER, et
   * l'écran affichait « Rien a exporter : la vue 3D ne contient aucune geometrie » **devant un
   * bâtiment complet**.
   *
   * C'est exactement le scénario que le commentaire de la garde disait avoir fermé — fermé du
   * côté GÉOMÉTRIE, laissé ouvert du côté TRANSFORM.
   *   *Une garde doit s'appliquer à la valeur qui PART, jamais à celle qui arrive : entre les
   *   deux il y a un calcul, et c'est lui qui fabrique l'infini.*
   */
  function scene(abimer: (o: THREE.Mesh) => void) {
    const racine = new THREE.Group();
    for (let i = 0; i < 4; i++) {
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.Float32BufferAttribute(
        [0, 0, 0, 1, 0, 0, 0, 1, 0], 3));
      const mesh = new THREE.Mesh(g, new THREE.MeshBasicMaterial());
      mesh.position.set(i * 2, 0, 0);
      racine.add(mesh);
    }
    const mauvais = racine.children[2] as THREE.Mesh;
    abimer(mauvais);
    racine.updateMatrixWorld(true);
    return racine;
  }

  it('un maillage dont la POSITION est NaN est écarté, pas propagé', () => {
    const res = collectSceneTriangles(scene((o) => { o.position.x = NaN; }));
    expect(res.triangles).toBe(3);
    for (let i = 0; i < res.sommets.length; i++) {
      expect(Number.isFinite(res.sommets[i])).toBe(true);
    }
    expect(res.ecartes.non_finis).toBe(1);
  });

  it('une ROTATION NaN aussi — le NaN passe par la matrice, pas par le sommet', () => {
    const res = collectSceneTriangles(scene((o) => { o.rotation.y = NaN; }));
    expect(res.triangles).toBe(3);
    for (let i = 0; i < res.sommets.length; i++) {
      expect(Number.isFinite(res.sommets[i])).toBe(true);
    }
  });

  it('TÉMOIN : quatre maillages SAINS donnent bien quatre triangles et rien d\'écarté', () => {
    // Sans lui, une garde qui écarterait TOUT passerait les deux tests ci-dessus.
    const res = collectSceneTriangles(scene(() => {}));
    expect(res.triangles).toBe(4);
    expect(res.ecartes.non_finis).toBeUndefined();
  });
});
