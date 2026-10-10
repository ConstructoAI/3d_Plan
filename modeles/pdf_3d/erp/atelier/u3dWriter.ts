/**
 * ECRIVAIN U3D (ECMA-363) — le format 3D qu'un PDF sait embarquer.
 *
 * POURQUOI CE MODULE EXISTE. Un « PDF 3D » est un PDF ordinaire portant une annotation
 * `/Type /3D` dont le flux contient de la geometrie. Le format de ce flux ne peut etre que
 * **U3D** ou **PRC**. PRC est plus moderne et plus compact — c'est celui des echantillons
 * SpinFire — mais il n'a AUCUN ecrivain libre serieux. U3D, lui, est une norme publique
 * (ECMA-363), lue par Acrobat depuis la version 7 et par PDF-XChange. C'est le seul chemin
 * sans licence et sans binaire externe a installer sur le serveur.
 *
 * CE QUI REND CE TRAVAIL BORNE, et il faut le savoir avant de lire la suite : le drapeau
 * `0x00000004` du profil signifie **SANS COMPRESSION** (on y ajoute `0x08`, UNITES
 * DEFINIES, qui fait ecrire un facteur d'echelle et permet de MESURER dans le lecteur). Les sommets et les faces s'ecrivent
 * alors en clair. Sans lui, il faudrait implementer le codeur arithmetique du U3D — ce qui
 * fait la difference entre une nuit de travail et un mois.
 *
 * SIX BLOCS, DANS CET ORDRE, et l'ordre n'est pas negociable — mais **QUATRE seulement au
 * niveau superieur** : le Model Node et la CLOD Mesh Declaration sont IMBRIQUES dans leur chaine
 * de modificateurs. (Ce texte annoncait « six blocs » a plat, ce que le banc contredisait en
 * n'en parcourant que quatre : les deux avaient raison, ils ne parlaient pas de la meme chose.)
 *
 *   1. File Header                     0x00443355
 *   2. Node Modifier Chain             0xFFFFFF14   (chaine de type 0)
 *        └─ Model Node                 0xFFFFFF22   (imbrique)
 *   3. Resource Modifier Chain         0xFFFFFF14   (chaine de type 1)
 *        └─ CLOD Mesh Declaration      0xFFFFFF31   (imbrique)
 *   4. CLOD Base Mesh Continuation     0xFFFFFF3B
 *
 * Les blocs 1 a 3 sont les DECLARATIONS : leur taille totale — **en-tete COMPRIS** (§9.4.1.3,
 * confirme par `CIFXBlockWriterX.cpp` qui y rapiece la position ABSOLUE) — est annoncee dans
 * l'en-tete, et une erreur de compte rend le fichier illisible sans que rien n'indique lequel.
 *
 * CE QUE CE FICHIER N'A PAS, ET IL FAUT LE SAVOIR EN LE REGARDANT : aucun MATERIAU. §8.4.2 dit
 * que le materiau par defaut a un ambiant gris 0,75 et **tout le reste NOIR** (diffus compris) :
 * le batiment sort donc en gris plat, sans relief entre les murs et le toit. C'est laid, ce
 * n'est pas casse — et c'est un choix : ajouter la chaine materiau/nuanceur, c'est trois types
 * de blocs de plus qu'aucun test local ne peut valider visuellement. On regarde d'abord si le
 * fichier s'affiche, on l'embellit ensuite.
 *
 * TROIS REGLES QUI CASSENT TOUT SI ON LES RATE :
 *   - tout est en LITTLE-ENDIAN ;
 *   - chaque bloc est aligne sur 4 OCTETS, et le remplissage vient APRES les donnees ET
 *     APRES les metadonnees, jamais avant ;
 *   - la taille annoncee d'un bloc EXCLUT son remplissage, mais la taille totale du fichier
 *     l'INCLUT. Confondre les deux produit un fichier qui s'ouvre a moitie.
 *
 * CE QUE CE MODULE NE FAIT PAS, deliberement : ni normales (le lecteur les calcule — moins
 * d'octets et un rendu lisse), ni couleurs par sommet, ni textures, ni niveaux de detail
 * progressifs. **Ni materiau** — cette phrase disait « un maillage, un materiau », ce qui etait
 * faux : aucun bloc de materiau n'est ecrit (voir le paragraphe ci-dessus). Un maillage nu, et
 * c'est assez pour montrer un batiment.
 *
 * PUR : aucune dependance, aucun DOM. Testable octet par octet.
 */

/** Types de bloc, tels que la norme les numerote. */
const BLOC = {
  entete: 0x00443355,
  chaineModif: 0xffffff14,
  noeudModele: 0xffffff22,
  declMaillage: 0xffffff31,
  contMaillage: 0xffffff3b,
} as const;

/** Remplissage a ajouter pour aligner sur 4 octets. */
function bourrage(n: number): number {
  return (4 - (n % 4)) % 4;
}

/** Petit tampon qui grandit — evite de calculer les tailles a l'avance deux fois. */
class Tampon {
  private buf = new Uint8Array(1024);
  private vue = new DataView(this.buf.buffer);
  private n = 0;

  private place(k: number): void {
    if (this.n + k <= this.buf.length) return;
    let taille = this.buf.length * 2;
    while (taille < this.n + k) taille *= 2;
    const neuf = new Uint8Array(taille);
    neuf.set(this.buf.subarray(0, this.n));
    this.buf = neuf;
    this.vue = new DataView(this.buf.buffer);
  }

  u8(v: number): void { this.place(1); this.vue.setUint8(this.n, v); this.n += 1; }
  u16(v: number): void { this.place(2); this.vue.setUint16(this.n, v, true); this.n += 2; }
  i16(v: number): void { this.place(2); this.vue.setInt16(this.n, v, true); this.n += 2; }
  u32(v: number): void { this.place(4); this.vue.setUint32(this.n, v >>> 0, true); this.n += 4; }
  f32(v: number): void { this.place(4); this.vue.setFloat32(this.n, v, true); this.n += 4; }
  f64(v: number): void { this.place(8); this.vue.setFloat64(this.n, v, true); this.n += 8; }

  /** U64 en little-endian. JS n'a pas d'entier 64 bits natif ici : on ecrit deux mots de 32. */
  u64(v: number): void {
    this.u32(v >>> 0);
    this.u32(Math.floor(v / 4294967296) >>> 0);
  }

  /** Chaine U3D : longueur EN OCTETS sur 2 octets, puis les octets.
   *
   *  En UTF-8, parce que c'est ce que l'en-tete DECLARE (encodage 106). La premiere version
   *  masquait chaque caractere avec `& 0x7f` : « Batiment quebecois » sortait « Bbtiment
   *  quibicois », et un caractere a 0x80 devenait un octet NUL au milieu du nom. La longueur
   *  restait coherente — c'est pour ca que rien ne cassait — mais le nom affiche dans l'arbre du
   *  lecteur etait du charabia. On ecrit maintenant ce qu'on annonce. */
  str(s: string): void {
    const o = new TextEncoder().encode(s);
    this.u16(o.length);
    this.octets(o);
  }

  octets(a: Uint8Array): void { this.place(a.length); this.buf.set(a, this.n); this.n += a.length; }
  zeros(k: number): void { this.place(k); this.n += k; }   // le tampon est deja a zero
  get taille(): number { return this.n; }
  rendu(): Uint8Array { return this.buf.slice(0, this.n); }
}

/** Enveloppe un corps de bloc : type, tailles, donnees, remplissage. */
function bloc(type: number, corps: Uint8Array): Uint8Array {
  const t = new Tampon();
  t.u32(type);
  t.u32(corps.length);          // taille des DONNEES, remplissage EXCLU
  t.u32(0);                     // pas de metadonnees
  t.octets(corps);
  t.zeros(bourrage(corps.length));
  return t.rendu();
}

export interface U3dOptions {
  /** Nom du modele, visible dans l'arbre du lecteur PDF. */
  readonly nom?: string;
}

/**
 * Le fichier ET ce qu'il contient VRAIMENT.
 *
 * LES COMPTES SONT RENDUS PARCE QU'ILS NE COINCIDENT PAS avec ce que l'appelant a fourni : le
 * dedoublonnage fusionne les SOMMETS, et les triangles degeneres — ceux dont deux coins tombent
 * sur le meme sommet — sont ECARTES. Un nombre affiche a l'utilisateur doit decrire le FICHIER,
 * pas l'intention : sinon ce n'est pas une mesure, c'est une illustration.
 *
 * ⚠️ CETTE PHRASE A AFFIRME QUE « 100 triangles identiques produisent un fichier contenant UNE
 * face ». C'EST FAUX, mesure : ils produisent **3 sommets et 100 FACES** — cent copies de
 * `[0,1,2]`. Le dedoublonnage travaille sur les SOMMETS, jamais sur les faces, et le test de
 * degenerescence ne compare que les indices A L'INTERIEUR d'un triangle, jamais entre triangles.
 *   *Une docstring qui annonce une deduplication decrit ce qu'on aurait voulu ecrire ; seule la
 *   mesure dit ce qui est ecrit.*
 *
 * CONSEQUENCE REELLE, non corrigee : deux triangles distants de moins que la maille de
 * quantification (`toFixed(5)`) recoivent la meme clef et le fichier porte la MEME FACE deux fois
 * — des faces coplanaires, donc du scintillement dans le lecteur. Et le compte « reel » annonce a
 * l'utilisateur inclut des faces qui ne rendent qu'une fois.
 */
export interface U3dResultat {
  readonly fichier: Uint8Array;
  /** Faces reellement ecrites (degenerees exclues). */
  readonly faces: number;
  /** Sommets distincts apres dedoublonnage. */
  readonly sommets: number;
}

/**
 * Construit un fichier U3D a partir de triangles.
 *
 * @param sommets  Coordonnees XYZ, trois par sommet, trois sommets par triangle (donc
 *                 `sommets.length` est un multiple de 9), dans le repere du MODELE : **Y vers le
 *                 haut**, comme three.js.
 *
 * ⚠️ **LA CONVERSION D'AXES SE FAIT ICI, et j'avais ecrit le contraire.** Le JSDoc annoncait
 * « repere du LECTEUR : Y vers le haut » — faux. ECMA-363 **§8.3.3** : « There is a preference for
 * having the coordinate system oriented such that the Z-axis is in the up direction **with the
 * Y-axis oriented in the direction of the view** ». La seconde moitie, que j'avais coupee,
 * RENFORCE le choix : `Y = -z` envoie le -Z de three.js — la direction du regard — sur le +Y du
 * U3D. La conversion satisfait donc les DEUX moities de la preference.
 *
 * (J'avais cite « §8.3.1 » et un fichier d'echantillon `box_mp_year.idtf` **qui n'existe pas** :
 * le depot de reference contient `box.idtf`, `mp_box.idtf` et `box_mp_view.idtf`. Le FAIT — la
 * boite monte de z=0 a z=40, camera par defaut a z=+64,7 — est juste ; la reference etait
 * invérifiable telle que je l'avais ecrite.)
 *
 * On applique donc `X = x, Y = -z, Z = y` — **la meme conversion que l'export DXF**, puisque les
 * deux mondes sont Z-up et droitiers. J'avais fige la difference dans un test en la croyant
 * deliberee : c'etait une erreur, pas une decision.
 *
 * **SI LE BATIMENT S'OUVRE COUCHE SUR LE FLANC, C'EST ICI QUE CA SE CORRIGE**, en une ligne — et
 * c'est le point que je m'attends le plus a devoir retoucher apres un vrai essai en lecteur.
 *
 * @returns le fichier complet, pret a etre embarque dans un PDF.
 */
export function buildU3D(sommets: Float32Array, options: U3dOptions = {}): U3dResultat | null {
  const nTri = Math.floor(sommets.length / 9);
  if (nTri < 1) return null;
  // LE NOM NE PEUT PLUS ETRE VIDE, et c'est la correction du parent qui l'a rendu interdit : la
  // racine du monde se DESIGNE par la chaine vide, donc un nœud nomme `''` se declarerait son
  // propre parent. §9.5.1.2 : « Recursion in the parent child hierarchy is illegal and will
  // generate an error. » Le `||` le bloquait deja par accident ; on l'ecrit comme un invariant,
  // parce qu'un garde-fou involontaire n'apprend rien au prochain lecteur.
  const nom = ((options.nom || '').trim() || 'Modele').slice(0, 60);

  // DEDOUBLONNAGE. Un maillage issu d'un rendu repete chaque sommet partage entre triangles
  // voisins ; sans regroupement, le fichier triple de taille et l'ombrage devient facette.
  const index = new Map<string, number>();
  const pos: number[] = [];
  const faces: [number, number, number][] = [];
  for (let t = 0; t < nTri; t++) {
    const tri: number[] = [];
    for (let k = 0; k < 3; k++) {
      const o = t * 9 + k * 3;
      const mx = sommets[o]; const my = sommets[o + 1]; const mz = sommets[o + 2];
      if (!Number.isFinite(mx) || !Number.isFinite(my) || !Number.isFinite(mz)) return null;
      // MODELE (Y-up, three.js) -> U3D (Z-up). Cf. le JSDoc : c'est la ligne a inverser si le
      // batiment s'ouvre couche.
      // `mz === 0` donne `-0`, dont le motif binaire (0x80000000) n'est PAS celui de `+0`. Sans
      // cette normalisation, un plancher a z = 0 sort avec des octets differents d'un plancher a
      // y = 0, pour la meme valeur — et la clef de dedoublonnage, elle, les confond.
      const x = mx; const y = mz === 0 ? 0 : -mz; const z = my;
      const c = `${x.toFixed(5)},${y.toFixed(5)},${z.toFixed(5)}`;
      let i = index.get(c);
      if (i === undefined) { i = pos.length / 3; index.set(c, i); pos.push(x, y, z); }
      tri.push(i);
    }
    if (tri[0] === tri[1] || tri[1] === tri[2] || tri[0] === tri[2]) continue;
    faces.push([tri[0], tri[1], tri[2]]);
  }
  if (!faces.length) return null;

  // PURGE DES SOMMETS ORPHELINS. Les sommets d'un triangle ECARTE (degenere) restaient dans la
  // table sans qu'aucune face ne les reference. Inoffensifs pour le maillage — mais la QA a
  // mesure qu'UN seul triangle degenere pose loin du modele faisait passer l'etendue des
  // coordonnees de 1 m a 1001 m. Or le lecteur CADRE sur cette etendue : un point fantome a
  // 1 km reduit le batiment a un pixel. On renumerote.
  const garde = new Int32Array(pos.length / 3).fill(-1);
  for (const f of faces) { garde[f[0]] = 0; garde[f[1]] = 0; garde[f[2]] = 0; }
  const posUtiles: number[] = [];
  for (let i = 0; i < garde.length; i++) {
    if (garde[i] !== 0) continue;
    garde[i] = posUtiles.length / 3;
    posUtiles.push(pos[i * 3], pos[i * 3 + 1], pos[i * 3 + 2]);
  }
  for (const f of faces) { f[0] = garde[f[0]]; f[1] = garde[f[1]]; f[2] = garde[f[2]]; }
  // ⚠️ PAS DE `pos.push(...posUtiles)` ICI, ET C'EST UN DEFAUT DE PRODUCTION MESURE.
  //
  // Le spread passe CHAQUE element en ARGUMENT d'appel. Au-dela de la taille de la pile
  // d'arguments, il leve `RangeError: Maximum call stack size exceeded`. Mesure du 2026-08-19 :
  //
  //     dernier OK 125 246 elements        premier echec 125 247
  //
  // `posUtiles` porte TROIS flottants par sommet : l'export cassait donc des **41 748 sommets**
  // — c'est-a-dire sur a peu pres tout batiment reel.
  //
  // ⚠️ ET CE SEUIL N'EST PAS UNE CONSTANTE : il DESCEND avec la profondeur de pile.
  //     top-level 125 220   ·   +20 cadres 124 960   ·   +60 : 124 440   ·   +120 : 123 662
  // Dans le navigateur, appele depuis un gestionnaire React a travers une chaine d'`await
  // import()`, la limite est plus basse que toute dichotomie faite au top-level, et elle VARIE.
  // Sur la frontiere, le defaut n'etait donc pas reproductible d'un appel a l'autre.
  //
  // ⚠️ CE COMMENTAIRE A D'ABORD ECRIT « ~43 000 sommets ». Ce chiffre venait de 130 000 / 3 —
  // c'est-a-dire de la borne QUI ECHOUE, divisee par trois — et non du point de rupture. Il
  // sous-estimait le defaut de ~1 600 sommets et presentait comme une constante une valeur qui
  // bouge. *Dans un correctif dont le reproche est justement qu'une borne annoncee promet ce que
  // le code ne tient pas, cette borne-la etait citee au lieu d'etre mesuree.*
  //
  // Et le plafond du module autorise
  // `MAX_TRIANGLES_PDF3D = 400 000` triangles, soit jusqu'a 3,6 MILLIONS de flottants : la borne
  // annoncee etait **28 fois au-dessus de ce que ce code pouvait encaisser**.
  //
  // L'utilisateur ne voyait qu'un « L'export PDF 3D a echoue » — le `catch` de l'appelant avale
  // l'erreur et n'ecrit la cause qu'en console.
  //   *Une borne genereuse posee au-dessus d'une limite technique non mesuree ne protege rien :
  //   elle promet ce que le code ne sait pas faire.*
  // ⚠️ DEUX REMEDES « EVIDENTS » SONT PIRES, ET MESURES :
  //   `Array.prototype.push.apply(pos, posUtiles)` a EXACTEMENT la meme limite de pile que le
  //     spread (RangeError au meme rang) — ce n'est pas un correctif du tout ;
  //   `push.apply` PAR TRANCHES de 60 000, le remede le plus souvent recommande, est **2,4 fois
  //     plus lent** que cette boucle (156 ms contre 65 ms sur 3,6 M).
  // Cette boucle coute 57,7 ms au plafond du module (400 000 triangles), soit **1,74 %** des
  // 3 316 ms de `buildU3D` — dont **90 % vivent dans le dedoublonnage** (la `Map` a clefs de
  // chaine, 2 993 ms). C'est la qu'un facteur 10 est disponible, pas ici.
  pos.length = 0;
  for (let i = 0; i < posUtiles.length; i++) pos.push(posUtiles[i]);

  const nPos = pos.length / 3;
  if (!nPos) return null;

  const nomChaineRes = `${nom}_res`;

  // --- 2. Node Modifier Chain (type 0) : la chaine qui porte le NŒUD ------------------------
  const noeudInterne = new Tampon();
  {
    const c = new Tampon();
    c.str(nom);
    // ⚠️ LE DEFAUT LE PLUS COUTEUX DE CE MODULE, ET IL ETAIT MUET.
    //
    // J'avais ecrit `c.u32(0)` avec le commentaire « aucun parent -> racine ». **Il n'y a pas de
    // racine implicite en U3D.** La racine est l'entree par defaut de la palette de nœuds, et
    // elle se nomme par la CHAINE VIDE : on s'y rattache en DECLARANT un parent nomme `""`.
    //
    // ECMA-363 §8.9.1, mot pour mot : « A node with no parents will have an empty transform set.
    // […] **If the transform set is empty, the node is disconnected from the world and does not
    // appear in the rendered view.** » L'implementation de reference d'Intel le confirme par
    // construction : `CIFXNode::AddParent` appelle `pNewParentNode->AddChild(...)` — la liste des
    // enfants du monde est batie A PARTIR des declarations de parent. Zero parent, jamais enfant,
    // jamais parcouru par le rendu.
    //
    // Le fichier restait STRUCTURELLEMENT IMPECCABLE : bonnes tailles, bon alignement, parcours
    // tombant pile sur la fin. Il n'affichait simplement rien, sans un message. C'est exactement
    // le mode d'echec que l'en-tete de ce module dit redouter — et je l'avais ecrit moi-meme.
    c.u32(1);            // UN parent : le monde
    c.str('');           // la chaine VIDE designe la racine de la palette de nœuds
    // Matrice 4x4 du parent, COLONNE-MAJEUR (§9.5.1.2.3), translation aux indices 12/13/14.
    for (let i = 0; i < 16; i++) c.f32(i % 5 === 0 ? 1 : 0);   // identite
    c.str(nomChaineRes); // la ressource que ce nœud affiche
    c.u32(3);            // visible des DEUX cotes : une charpente se regarde de l'interieur
    noeudInterne.octets(bloc(BLOC.noeudModele, c.rendu()));
  }
  const chaineNoeud = (() => {
    const c = new Tampon();
    c.str(nom);
    c.u32(0);            // 0 = chaine de modificateurs de NŒUD
    c.u32(0);            // aucun attribut
    c.zeros(bourrage(c.taille));
    c.u32(1);            // un seul modificateur dans la chaine
    c.octets(noeudInterne.rendu());
    return bloc(BLOC.chaineModif, c.rendu());
  })();

  // --- 5. CLOD Mesh Declaration ------------------------------------------------------------
  const declMaillage = (() => {
    const c = new Tampon();
    c.str(nomChaineRes);
    c.u32(0);            // indice dans la chaine

    // Max Mesh Description
    c.u32(0x00000001);   // EXCLURE les normales : le lecteur les calcule, rendu lisse gratuit
    c.u32(faces.length);
    c.u32(nPos);
    c.u32(0);            // normales
    c.u32(0);            // couleurs diffuses
    c.u32(0);            // couleurs speculaires
    c.u32(0);            // coordonnees de texture
    c.u32(1);            // un seul « shading »

    // Shading Description (une seule)
    c.u32(0);            // aucune couleur par sommet
    c.u32(0);            // aucune couche de texture
    c.u32(0);            // identifiant d'origine

    // CLOD Description — pas de niveau de detail progressif : min = max = tous les sommets
    c.u32(nPos);
    c.u32(nPos);

    // Resource Description
    c.u32(1000); c.u32(1000); c.u32(1000);          // facteurs de qualite
    c.f32(0); c.f32(0); c.f32(0); c.f32(0); c.f32(0); // quantifications inverses (0 = aucune)
    c.f32(0.9); c.f32(0.5); c.f32(0.985);           // parametres de normales (inutilises ici)
    c.u32(0);                                        // aucun os
    return bloc(BLOC.declMaillage, c.rendu());
  })();

  // --- 4. Resource Modifier Chain (type 1) : la chaine qui porte le MAILLAGE ----------------
  const chaineRes = (() => {
    const c = new Tampon();
    c.str(nomChaineRes);
    c.u32(1);            // 1 = chaine de modificateurs de RESSOURCE
    c.u32(0);
    c.zeros(bourrage(c.taille));
    c.u32(1);
    c.octets(declMaillage);
    return bloc(BLOC.chaineModif, c.rendu());
  })();

  // --- 6. CLOD Base Mesh Continuation ------------------------------------------------------
  const contMaillage = (() => {
    const c = new Tampon();
    c.str(nomChaineRes);
    c.u32(0);
    c.u32(faces.length);
    c.u32(nPos);
    c.u32(0); c.u32(0); c.u32(0); c.u32(0);  // normales, diffus, speculaire, texture
    for (let i = 0; i < pos.length; i++) c.f32(pos[i]);
    for (const [a, b, d] of faces) {
      c.u32(0);          // identifiant de shading
      c.u32(a); c.u32(b); c.u32(d);   // les normales etant exclues, un coin = un seul indice
    }
    return bloc(BLOC.contMaillage, c.rendu());
  })();

  // --- 1. File Header ----------------------------------------------------------------------
  // La taille des DECLARATIONS est celle des blocs 1 a 5 (en-tete COMPRIS). La taille TOTALE
  // inclut tout. Ces deux nombres sont les plus faciles a rater et les plus muets a l'ouverture.
  //
  // UNE SEULE FONCTION construit l'en-tete, et c'est deliberé : la taille du fichier depend de
  // la taille de l'en-tete, qui doit donc etre connue AVANT de l'ecrire. La tentation est d'en
  // ecrire un second, « juste pour le mesurer » — et le jour ou l'un des deux gagne un champ
  // que l'autre n'a pas, les tailles annoncees deviennent fausses et le fichier meurt en
  // silence. On appelle donc la MEME fonction deux fois : une fois pour mesurer, une fois pour
  // de vrai.
  const faireEntete = (declSize: number, totalSize: number): Uint8Array => {
    const c = new Tampon();
    c.i16(0);            // version majeure : 0
    c.i16(0);            // version mineure
    // 0x04 = SANS COMPRESSION, 0x08 = UNITES DEFINIES. Le second n'est pas cosmetique : il
    // rend obligatoire le facteur d'echelle ci-dessous, et c'est LUI qui permet au lecteur PDF
    // de MESURER dans le modele. Un batiment sans unite ne se cote pas.
    c.u32(0x00000004 | 0x00000008);
    c.u32(declSize);
    c.u64(totalSize);
    c.u32(106);          // encodage des chaines : UTF-8
    c.f64(1.0);          // le modele est en METRES ; 1 unite = 1 metre
    return bloc(BLOC.entete, c.rendu());
  };

  // L'en-tete a une taille FIXE quelles que soient les valeurs (des entiers de largeur fixe),
  // donc mesurer avec des zeros donne la bonne taille. Pas de point fixe a chercher.
  const tailleEntete = faireEntete(0, 0).length;
  const tailleDecl = tailleEntete + chaineNoeud.length + chaineRes.length;
  const total = tailleDecl + contMaillage.length;

  const t = new Tampon();
  t.octets(faireEntete(tailleDecl, total));
  t.octets(chaineNoeud);
  t.octets(chaineRes);
  t.octets(contMaillage);
  return { fichier: t.rendu(), faces: faces.length, sommets: nPos };
}
