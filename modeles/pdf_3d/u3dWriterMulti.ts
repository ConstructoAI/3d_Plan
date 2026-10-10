/**
 * ECRIVAIN U3D « A PLUSIEURS PIECES » — ce que u3dWriter.ts (ERP) ne fait pas, ecrit A COTE de lui.
 *
 * L'ecrivain de l'ERP produit UN maillage, sans materiau, sous UN nœud : c'est assez pour montrer
 * un batiment. Un atelier, lui, veut CLIQUER UNE PIECE : il lui faut un arbre (groupes, pieces
 * nommees), des couleurs, et un fichier qui reste leger quand la meme piece est posee 300 fois.
 * D'ou ce module, dans le meme style (tampon little-endian, `bloc()`, alignement, tailles
 * MESUREES et jamais recalculees), avec quatre types de bloc de plus et deux mecanismes :
 *
 *   - des RESSOURCES PARTAGEES : un maillage n'est ecrit qu'une fois, autant de nœuds de modele
 *     qu'on veut le citent par son nom, chacun avec sa matrice (ECMA-363 §8.1 : « Multiple nodes
 *     may use the same resource ») ;
 *   - les couleurs par le NŒUD et non par la ressource : le modificateur de nuançage vit dans la
 *     chaine du nœud, si bien que deux poses du meme maillage peuvent porter deux matieres.
 *
 * CE QUI A ETE VERIFIE, ET OU. Chaque disposition de bloc ci-dessous a ete relue dans la norme
 * (ECMA-363, 4e edition, juin 2007) ET dans le code de reference d'Intel (« Universal 3D Sample
 * Software », encodeurs CIFX*Encoder.cpp et CIFXWriteManager.cpp). Les articles sont cites sur
 * place. Ce que la norme et la reference ne disent pas de la meme façon est dit aussi :
 *
 *   - ORDRE DES BLOCS. La norme tolere les references en avant (§9.3) ; la reference ecrit les
 *     palettes dans cet ordre : nœuds, ressources de modele, nuanceurs, materiaux
 *     (CIFXWriteManager::Write). On fait pareil, parents avant enfants.
 *   - TOUT NŒUD EST DANS UNE CHAINE. §9.4.3 : un objet sans modificateur « may be contained in a
 *     modifier chain block but is not required ». La reference enveloppe TOUS les nœuds, groupes
 *     compris : on fait pareil, un lecteur a plus de chances d'avoir ete eprouve sur cette forme.
 *   - MISE A JOUR DE PRIORITE. §8.10.1 veut une priorite > 0 pour les blocs de suite ; elle se
 *     pose par un bloc 0xFFFFFF15 (§9.4.4), « not required ». La reference en ecrit un (256)
 *     avant les suites : on fait pareil. (L'ecrivain de l'ERP n'en ecrit pas.)
 *   - CODAGE COMPRESSE, PAR DEFAUT. Tous les fichiers U3D qu'on croise sont compresses (profil
 *     sans le bit 0x04) : les indices des faces passent par le codeur arithmetique du chapitre 10
 *     de la norme. L'ecrivain de l'ERP, lui, ecrit SANS compression (profil 0x04) : c'est dans la
 *     norme depuis 2004 et le decodeur de reference l'honore (CIFXAuthorCLODDecoder.cpp :
 *     `SetNoCompressionMode`), mais un lecteur tiers au moins (Aspose.CAD 26.6) REFUSE ces
 *     fichiers, celui de l'ERP compris, alors qu'il lit les fichiers compresses. On ecrit donc
 *     compresse ; `compat.compresse = false` redonne la forme de l'ERP. Le codeur est porte ligne
 *     a ligne de la reference (CIFXBitStreamX.cpp) et de l'annexe A de la norme ; voir plus bas.
 *   - ZERO FINAL DU MAILLAGE. §10.4.10 : si une valeur compressee a ete ecrite, le bloc se termine
 *     par un U32 nul NON compresse (il pousse dehors les derniers bits du codeur ; la reference :
 *     `GetDataBlockX`). En mode sans compression la norme n'en veut pas, et l'ERP n'en ecrit pas.
 *   - TAILLE DES DECLARATIONS. §9.4.1.3 : en-tete + blocs de declaration, bourrage compris. La
 *     reference y range en plus le 1er bloc de suite (elle rapiece la position APRES l'avoir
 *     ecrit) : c'est son defaut, on suit la NORME.
 *
 * ET FACE A UN VRAI FICHIER. Le lecteur a part (lire_u3d.py) a relu `dice.u3d`, l'echantillon
 * des paquets LaTeX movie15 et media9 (CTAN), ecrit par le convertisseur 3DIF d'Adobe et affiche
 * par Acrobat depuis vingt ans. Sa structure est celle qu'on ecrit ici : chaines de nœuds
 * (groupes COMPRIS) puis chaines de ressources, nuanceurs (eclairage active, test alpha ALWAYS
 * 0x617, melange 0x606, une passe, aucun canal), materiaux (attributs 0x3F), une mise a jour de
 * priorite 256 avant les suites, parents avant enfants. Trois choses qu'il fait AUTREMENT, et
 * qu'un lecteur doit donc tolerer : sa « taille des declarations » ne couvre que l'en-tete (120),
 * une mise a jour de priorite 0 precede ses declarations, et ses modificateurs de nuançage ont
 * des attributs a 0. Il est COMPRESSE, comme ce qu'on ecrit par defaut : lire_u3d.py DECODE ses
 * 22 maillages (codeur arithmetique porte a part, en Python) et y retrouve des surfaces fermees,
 * ce qui eprouve le decodeur sur un fichier qu'on n'a pas ecrit ; ce decodeur relit ensuite les
 * notres.
 *
 * LES TROIS REGLES QUI CASSENT TOUT, rappelees de u3dWriter.ts : little-endian partout ; chaque
 * bloc aligne sur 4 octets, bourrage APRES les donnees et APRES les metadonnees ; la taille
 * annoncee d'un bloc EXCLUT son bourrage, la taille du fichier l'INCLUT.
 *
 * REPERE : ce module NE CONVERTIT RIEN. On lui donne des coordonnees deja en Z vers le haut
 * (§8.3.1 : « a preference for having the coordinate system oriented such that the Z-axis is in
 * the up direction »), ce qui est le repere de Blender. (u3dWriter.ts, lui, part de three.js.)
 *
 * CE QUE CE MODULE NE PROUVE PAS : qu'un lecteur affiche le fichier. La structure est relue par
 * un lecteur a part (lire_u3d.py, ecrit d'apres la norme) ; l'affichage se regarde dans un
 * lecteur PDF, avec les yeux.
 *
 * PUR : aucune dependance, aucun DOM, aucun import. Testable octet par octet.
 */

/** Types de bloc, tels que la norme les numerote. */
const BLOC = {
  entete: 0x00443355,
  chaineModif: 0xffffff14,
  priorite: 0xffffff15,
  noeudGroupe: 0xffffff21,
  noeudModele: 0xffffff22,
  declMaillage: 0xffffff31,
  contMaillage: 0xffffff3b,
  nuancage: 0xffffff45,
  nuanceur: 0xffffff53,
  materiau: 0xffffff54,
} as const;

/** Remplissage a ajouter pour aligner sur 4 octets. */
function bourrage(n: number): number {
  return (4 - (n % 4)) % 4;
}

/** La machine ecrit-elle ses entiers en little-endian ? (Toutes celles qu'on croise ; on le
 *  VERIFIE quand meme, parce que la voie rapide recopie les tableaux types octet pour octet.) */
const PETIT_BOUTISTE = new Uint8Array(new Uint32Array([1]).buffer)[0] === 1;

/** Petit tampon qui grandit — meme outil que dans u3dWriter.ts, plus deux ecritures en bloc. */
class Tampon {
  private buf = new Uint8Array(4096);
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

  u16(v: number): void { this.place(2); this.vue.setUint16(this.n, v, true); this.n += 2; }
  i16(v: number): void { this.place(2); this.vue.setInt16(this.n, v, true); this.n += 2; }
  u32(v: number): void { this.place(4); this.vue.setUint32(this.n, v >>> 0, true); this.n += 4; }
  f32(v: number): void { this.place(4); this.vue.setFloat32(this.n, v, true); this.n += 4; }
  f64(v: number): void { this.place(8); this.vue.setFloat64(this.n, v, true); this.n += 8; }

  /** U64 en little-endian : deux mots de 32. */
  u64(v: number): void {
    this.u32(v >>> 0);
    this.u32(Math.floor(v / 4294967296) >>> 0);
  }

  /** Chaine U3D : longueur EN OCTETS sur 2 octets, puis les octets, en UTF-8 (encodage 106). */
  str(s: string): void {
    const o = new TextEncoder().encode(s);
    if (o.length > 0xffff) throw new Error(`chaine U3D trop longue (${o.length} octets) : ${s.slice(0, 40)}...`);
    this.u16(o.length);
    this.octets(o);
  }

  octets(a: Uint8Array): void { this.place(a.length); this.buf.set(a, this.n); this.n += a.length; }
  zeros(k: number): void { this.place(k); this.n += k; }   // le tampon est deja a zero

  /** Tableau de flottants 32 bits, d'un coup. */
  f32s(a: Float32Array): void {
    if (PETIT_BOUTISTE) { this.octets(new Uint8Array(a.buffer, a.byteOffset, a.byteLength)); return; }
    for (let i = 0; i < a.length; i++) this.f32(a[i]);
  }

  /** Tableau d'entiers 32 bits, d'un coup. */
  u32s(a: Uint32Array): void {
    if (PETIT_BOUTISTE) { this.octets(new Uint8Array(a.buffer, a.byteOffset, a.byteLength)); return; }
    for (let i = 0; i < a.length; i++) this.u32(a[i]);
  }

  get taille(): number { return this.n; }
  rendu(): Uint8Array { return this.buf.slice(0, this.n); }
}

/**
 * Enveloppe un corps de bloc : type, tailles, donnees, remplissage, puis METADONNEES et leur
 * remplissage (§9.2). Les metadonnees sont des paires cle/valeur (§9.2.6) : nombre de paires,
 * puis pour chacune ses attributs (0 = la valeur est une chaine), la cle, la valeur. Un lecteur
 * les montre comme la « fiche » du nœud ; un lecteur qui les ignore saute la section grace a sa
 * taille — c'est fait pour.
 */
function bloc(type: number, corps: Uint8Array, meta?: Readonly<Record<string, string>>): Uint8Array {
  let m: Uint8Array | null = null;
  const cles = meta ? Object.keys(meta) : [];
  if (cles.length) {
    const tm = new Tampon();
    tm.u32(cles.length);
    for (const k of cles) {
      tm.u32(0);                  // attributs : valeur au format chaine, rien d'autre
      tm.str(k);
      tm.str(String(meta![k]));
    }
    m = tm.rendu();
  }
  const t = new Tampon();
  t.u32(type);
  t.u32(corps.length);            // taille des DONNEES, remplissage EXCLU
  t.u32(m ? m.length : 0);        // taille des METADONNEES, remplissage EXCLU
  t.octets(corps);
  t.zeros(bourrage(corps.length));
  if (m) { t.octets(m); t.zeros(bourrage(m.length)); }
  return t.rendu();
}

/** Une chaine de modificateurs (§9.4.3) autour de blocs deja enveloppes. */
function chaine(nom: string, type: 0 | 1, internes: readonly Uint8Array[]): Uint8Array {
  const c = new Tampon();
  c.str(nom);
  c.u32(type);                    // 0 = chaine de NŒUD, 1 = chaine de RESSOURCE de modele
  c.u32(0);                       // attributs : ni sphere ni boite englobante annoncees
  c.zeros(bourrage(c.taille));    // §9.4.3.6 : aligner le compte, donc les blocs internes
  c.u32(internes.length);
  for (const b of internes) c.octets(b);
  return bloc(BLOC.chaineModif, c.rendu());
}

// ---------------------------------------------------------------------------------------------
// LE CODEUR ARITHMETIQUE (ECMA-363 chap. 10 ; annexe A ; reference : CIFXBitStreamX.cpp)
// ---------------------------------------------------------------------------------------------
// Chaque bloc est ecrit par un codeur NEUF : haut = 0xFFFF, bas = 0, aucun bit en attente,
// histogrammes vides (§10.4.3). Les valeurs « non compressees » passent elles aussi par le codeur,
// octet par octet, comme des symboles equiprobables parmi 256 (§10.3.1) : tant que le codeur est
// dans son etat initial cela rend exactement l'octet — d'ou les octets simples du debut d'un bloc
// et de tous les blocs sans valeur compressee. Apres une valeur compressee ce n'est plus vrai :
// les octets qui suivent sont bel et bien codes.
// Porte ligne a ligne de la reference ; lire_u3d.py porte le DECODEUR a part, et il est eprouve
// sur un fichier qu'on n'a pas ecrit (dice.u3d, ecrit par Adobe).
// REPONSE CONNUE (2026-10-09) : rejoues par ce codeur, les 47 160 symboles des 22 maillages de ce
// fichier redonnent ses octets SANS UN BIT d'ecart, vidange comprise (l'encodeur d'Adobe ajoute
// ensuite 4 octets nuls que la norme ne demande pas). noeud/banc_multi.mjs en garde le cube.

/** Plus grand rang R d'un contexte statique (§10.4) ; au-dela, la valeur s'ecrit non compressee. */
const AC_RANG_MAX = 0x3ffe;
/** Total d'occurrences a partir duquel un histogramme dynamique est divise par deux (§10.4.9). */
const AC_ELEPHANT = 0x1fff;
const AC_DEMI = 0x8000;
const AC_QUART = 0x4000;
/** Numero du contexte dynamique des tranches de matiere (cShading). Seule compte son identite :
 *  il n'y en a qu'un dans un bloc de maillage de base. */
const AC_CONTEXTE_TRANCHE = 1;
/** Ordre inverse de 4 bits (`m_puSwap8` de la reference). */
const AC_INVERSE4 = [0, 8, 4, 12, 2, 10, 6, 14, 1, 9, 5, 13, 3, 11, 7, 15];

/** Histogramme d'un contexte DYNAMIQUE (annexe A.3.3). Le symbole 0 est l'echappement : il part
 *  d'une frequence de 1, tous les autres de 0 (§10.4.3). */
class HistogrammeDynamique {
  private compte = new Uint16Array(32);
  /** cumul[i] = occurrences du symbole i ET de tous les symboles plus grands ; cumul[0] = total. */
  private cumul = new Uint16Array(32);

  constructor() { this.compte[0] = 1; this.cumul[0] = 1; }

  get total(): number { return this.cumul[0]; }

  frequence(s: number): number { return s < this.compte.length ? this.compte[s] : 0; }

  /** Occurrences des symboles plus PETITS que s (la « frequence cumulee » de la norme). */
  cumulAvant(s: number): number {
    return s < this.cumul.length ? this.cumul[0] - this.cumul[s] : this.cumul[0];
  }

  ajouter(s: number): void {
    if (s >= 0xffff) return;                       // §10.4.9 : jamais au-dela de 0xFFFF
    if (s >= this.compte.length) {
      const c = new Uint16Array(s + 32); c.set(this.compte); this.compte = c;
      const k = new Uint16Array(s + 32); k.set(this.cumul); this.cumul = k;
    }
    if (this.cumul[0] >= AC_ELEPHANT) {
      // §10.4.9 : toutes les frequences divisees par deux (arrondi vers le bas), puis
      // l'echappement repris de 1 — l'histogramme suit ainsi une distribution qui change.
      let acc = 0;
      for (let i = this.compte.length - 1; i >= 0; i--) {
        this.compte[i] >>= 1;
        acc += this.compte[i];
        this.cumul[i] = acc;
      }
      this.compte[0] += 1;
      this.cumul[0] += 1;
    }
    this.compte[s] += 1;
    for (let i = 0; i <= s; i++) this.cumul[i] += 1;
  }
}

/** Exporte pour les bancs seulement (essai a reponse connue : rejouer les symboles d'un fichier ecrit par
 *  un autre encodeur et retrouver ses octets). Le reste du module s'en sert en interne. */
export class CodeurArithmetique {
  private haut = 0xffff;
  private bas = 0;
  /** Bits de sous-debordement en attente (§10.4.4.5). */
  private attente = 0;
  private buf: Uint8Array;
  private nBits = 0;
  private readonly contextes = new Map<number, HistogrammeDynamique>();

  constructor(octetsPrevus: number) { this.buf = new Uint8Array(Math.max(64, octetsPrevus)); }

  /** « Write-bit » : le bit de poids faible de l'octet d'abord (§10.1). */
  private bit(b: number): void {
    const o = this.nBits >>> 3;
    if (o >= this.buf.length) {
      const n = new Uint8Array(this.buf.length * 2);
      n.set(this.buf);
      this.buf = n;
    }
    if (b) this.buf[o] |= 1 << (this.nBits & 7);
    this.nBits += 1;
  }

  /** §10.4.4.4 puis §10.4.4.5 : sortir les bits de tete communs a haut et bas (chacun suivi des
   *  bits en attente, inverses), puis compter le sous-debordement. */
  private sortir(): void {
    while ((this.haut & AC_DEMI) === (this.bas & AC_DEMI)) {
      const b = this.bas >>> 15;
      this.bit(b);
      while (this.attente > 0) { this.attente -= 1; this.bit(b ^ 1); }
      this.haut = ((this.haut & 0x7fff) << 1) | 1;
      this.bas = (this.bas & 0x7fff) << 1;
    }
    while ((this.haut & AC_QUART) === 0 && (this.bas & AC_QUART) !== 0) {
      this.haut = ((this.haut & 0x7fff) << 1) | AC_DEMI | 1;
      this.bas = (this.bas << 1) & 0x7fff;
      this.attente += 1;
    }
  }

  /** Symbole d'un contexte STATIQUE de rang R : les symboles 1 a R sont equiprobables. */
  private statique(R: number, symbole: number): void {
    const etendue = this.haut + 1 - this.bas;
    const haut = this.bas - 1 + Math.floor((etendue * symbole) / R);
    this.bas += Math.floor((etendue * (symbole - 1)) / R);
    this.haut = haut;
    this.sortir();
  }

  /** Symbole d'un contexte DYNAMIQUE ; rend vrai si c'est l'ECHAPPEMENT qui a ete ecrit. */
  private dynamique(h: HistogrammeDynamique, symbole: number): boolean {
    const s = h.frequence(symbole) === 0 ? 0 : symbole;   // jamais vu : l'echappement (§10.4.4.1)
    const total = h.total;
    const avant = h.cumulAvant(s);
    const freq = h.frequence(s);
    const etendue = this.haut + 1 - this.bas;
    const haut = this.bas - 1 + Math.floor((etendue * (avant + freq)) / total);
    this.bas += Math.floor((etendue * avant) / total);
    this.haut = haut;
    h.ajouter(s);                                          // §10.4.4.3 : l'echappement compte aussi
    this.sortir();
    return s === 0;
  }

  /** Un octet « non compresse » (§10.4.8) : ses bits en ordre inverse, contexte statique 256. */
  u8(v: number): void {
    if (this.haut === 0xffff && this.bas === 0 && this.attente === 0) {
      // Codeur dans son etat initial : le codage rend l'octet tel quel (raccourci de la reference,
      // `WriteSymbolContext8`) — meme resultat que le chemin general, sans le calcul.
      for (let i = 0; i < 8; i++) this.bit((v >>> i) & 1);
      return;
    }
    this.statique(256, ((AC_INVERSE4[v & 0xf] << 4) | AC_INVERSE4[(v >>> 4) & 0xf]) + 1);
  }

  u32(v: number): void {
    this.u8(v & 0xff); this.u8((v >>> 8) & 0xff); this.u8((v >>> 16) & 0xff); this.u8((v >>> 24) & 0xff);
  }

  /** U32 « compresse », contexte STATIQUE de rang R : v est dans 0..R-1 (§10.4.5). */
  compresseStatique(R: number, v: number): void {
    if (R > AC_RANG_MAX) { this.u32(v); return; }          // rang trop grand : U32 non compresse
    this.statique(R, v + 1);
  }

  /** U32 « compresse », contexte DYNAMIQUE (§10.4.5). */
  compresseDynamique(contexte: number, v: number): void {
    let h = this.contextes.get(contexte);
    if (!h) { h = new HistogrammeDynamique(); this.contextes.set(contexte, h); }
    if (this.dynamique(h, v + 1)) {
      this.u32(v);                 // apres l'echappement : la valeur, non compressee…
      h.ajouter(v + 1);            // … et son symbole entre dans l'histogramme
    }
  }

  /** §10.4.10 : un U32 nul pour pousser dehors les derniers bits utiles, puis l'alignement sur
   *  l'octet. Rend les octets ecrits. */
  fin(): Uint8Array {
    this.u32(0);
    return this.buf.slice(0, (this.nBits + 7) >>> 3);
  }
}

export interface MaillageMulti {
  /** Nom de la ressource, unique parmi les maillages. */
  readonly nom: string;
  /** XYZ par sommet, dans le repere LOCAL de la piece, Z vers le haut. */
  readonly positions: Float32Array;
  /** Trois indices de sommet par face. */
  readonly indices: Uint32Array;
  /** Tranche de matiere de chaque face (defaut : toutes a 0). */
  readonly tranches?: Uint32Array;
  /** Nombre de tranches de matiere (defaut 1). */
  readonly nbTranches?: number;
  /** XYZ par normale (unitaire). Absent : le lecteur calcule les normales. */
  readonly normales?: Float32Array;
  /** Trois indices de normale par face (obligatoire si `normales` est donne). */
  readonly indicesNormales?: Uint32Array;
}

export interface NoeudMulti {
  /** Nom du nœud dans l'arbre du lecteur, UNIQUE parmi tous les nœuds, jamais vide. */
  readonly nom: string;
  /** Nom du parent ; la chaine VIDE designe le monde. */
  readonly parent: string;
  /** Matrice 4x4 relative au parent, COLONNES d'abord, translation aux rangs 12, 13, 14.
   *  Absente : l'identite. */
  readonly matrice?: ArrayLike<number>;
  /** Nom du maillage affiche. Absent : c'est un nœud de GROUPE. */
  readonly maillage?: string;
  /** Un nom de materiau par tranche du maillage. Absent : matiere par defaut du lecteur. */
  readonly nuanceurs?: readonly string[];
  /** Fiche du nœud (metadonnees), montree par le lecteur. */
  readonly meta?: Readonly<Record<string, string>>;
}

export interface MateriauMulti {
  readonly nom: string;
  readonly ambiant: readonly [number, number, number];
  readonly diffus: readonly [number, number, number];
  readonly speculaire: readonly [number, number, number];
  readonly emissif: readonly [number, number, number];
  /** 0 = mat, 1 = tres brillant (exposant 128), §9.8.4.7. */
  readonly reflectivite: number;
  /** 0 = invisible, 1 = opaque, §9.8.4.8. */
  readonly opacite: number;
}

/**
 * REGLAGES DE COMPATIBILITE. Par defaut le fichier ressemble a ce qu'ecrit la reference d'Intel
 * (voir l'en-tete du module). Ces interrupteurs n'existent que pour CHERCHER, devant un lecteur
 * qui n'afficherait rien, lequel de ces choix le gene : on les coupe un a un. Aucun ne change la
 * geometrie.
 */
export interface CompatU3d {
  /** Codage compresse des faces (chap. 10 de la norme), comme tous les fichiers U3D courants.
   *  Defaut : vrai. Faux : profil 0x04 « sans compression », la forme qu'ecrit l'ERP. */
  readonly compresse?: boolean;
  /** Bloc de mise a jour de priorite (256) avant les suites. Defaut : vrai. */
  readonly priorite?: boolean;
  /** Mode SANS compression seulement : U32 nul a la fin de chaque bloc de suite de maillage.
   *  Defaut : faux (la norme n'en veut que si une valeur compressee a ete ecrite, §10.4.10 ;
   *  en mode compresse il est toujours ecrit, c'est la vidange du codeur). */
  readonly zeroFinal?: boolean;
  /** Envelopper aussi les nœuds de GROUPE dans une chaine de modificateurs. Defaut : vrai. */
  readonly chainesDeGroupe?: boolean;
  /** Ecrire les fiches (metadonnees) des nœuds. Defaut : vrai. */
  readonly fiches?: boolean;
  /** Attributs du modificateur de nuançage : 1 = maillage (norme) ; 15 = defaut de la reference. */
  readonly attributsNuancage?: number;
  /** Declarer les unites (profil 0x08 et facteur d'echelle dans l'en-tete). Defaut : vrai.
   *  Faux : en-tete de la 1re edition de la norme (le fichier est alors « sans unite »). */
  readonly unitesDefinies?: boolean;
}

export interface SceneMulti {
  /** Les nœuds, PARENTS AVANT ENFANTS. */
  readonly noeuds: readonly NoeudMulti[];
  readonly maillages: readonly MaillageMulti[];
  readonly materiaux: readonly MateriauMulti[];
  /** Metres par unite du fichier : 1 = metre (defaut), 0.001 = millimetre, 0.0254 = pouce. */
  readonly metresParUnite?: number;
  readonly compat?: CompatU3d;
}

/** Le fichier ET ce qu'il contient vraiment. */
export interface U3dMultiResultat {
  readonly fichier: Uint8Array;
  readonly groupes: number;
  readonly modeles: number;
  readonly ressources: number;
  readonly materiaux: number;
  /** Faces POSEES : chaque maillage compte autant de fois qu'un nœud le montre. */
  readonly faces: number;
  /** Faces ecrites dans les ressources (ce que pese le fichier). */
  readonly facesRessources: number;
  /** Sommets ecrits dans les ressources. */
  readonly sommets: number;
  /** Taille de la partie « declarations », telle qu'annoncee dans l'en-tete. */
  readonly tailleDeclarations: number;
}

const IDENTITE = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];

/**
 * Construit un fichier U3D a plusieurs pieces.
 *
 * REFUSE (en levant une erreur qui NOMME la cause) tout ce qui donnerait un fichier
 * structurellement juste et pourtant muet a l'ouverture : nom de nœud vide ou en double, parent
 * inconnu ou declare apres son enfant, maillage ou materiau cite mais absent, indice hors bornes,
 * coordonnee non finie. Un refus chiffre vaut mieux qu'un cadre vide chez le client.
 */
export function buildU3DMulti(scene: SceneMulti): U3dMultiResultat {
  const unite = scene.metresParUnite ?? 1.0;
  if (!(unite > 0) || !Number.isFinite(unite)) throw new Error(`metresParUnite invalide : ${unite}`);
  const compat = {
    compresse: scene.compat?.compresse ?? true,
    priorite: scene.compat?.priorite ?? true,
    zeroFinal: scene.compat?.zeroFinal ?? false,
    chainesDeGroupe: scene.compat?.chainesDeGroupe ?? true,
    fiches: scene.compat?.fiches ?? true,
    attributsNuancage: scene.compat?.attributsNuancage ?? 0x00000001,
    unitesDefinies: scene.compat?.unitesDefinies ?? true,
  };

  // ------------------------------------------------------------------ verifications d'entree
  const maillages = new Map<string, MaillageMulti>();
  for (const m of scene.maillages) {
    if (!m.nom) throw new Error('maillage sans nom');
    if (maillages.has(m.nom)) throw new Error(`maillage « ${m.nom} » en double`);
    const nPos = m.positions.length / 3;
    const nFaces = m.indices.length / 3;
    if (!Number.isInteger(nPos) || !Number.isInteger(nFaces) || nPos < 3 || nFaces < 1) {
      throw new Error(`maillage « ${m.nom} » : ${m.positions.length} coordonnees, ${m.indices.length} indices`);
    }
    for (let i = 0; i < m.positions.length; i++) {
      if (!Number.isFinite(m.positions[i])) throw new Error(`maillage « ${m.nom} » : coordonnee non finie`);
    }
    for (let i = 0; i < m.indices.length; i++) {
      if (m.indices[i] >= nPos) throw new Error(`maillage « ${m.nom} » : indice de sommet ${m.indices[i]} hors bornes (${nPos})`);
    }
    const nTr = m.nbTranches ?? 1;
    if (nTr < 1) throw new Error(`maillage « ${m.nom} » : aucune tranche de matiere`);
    if (m.tranches) {
      if (m.tranches.length !== nFaces) throw new Error(`maillage « ${m.nom} » : ${m.tranches.length} tranches pour ${nFaces} faces`);
      for (let i = 0; i < nFaces; i++) {
        if (m.tranches[i] >= nTr) throw new Error(`maillage « ${m.nom} » : tranche ${m.tranches[i]} hors bornes (${nTr})`);
      }
    }
    if (m.normales) {
      const nNor = m.normales.length / 3;
      if (!m.indicesNormales || m.indicesNormales.length !== m.indices.length || !Number.isInteger(nNor) || nNor < 1) {
        throw new Error(`maillage « ${m.nom} » : normales sans leurs indices (ou en nombre different des faces)`);
      }
      for (let i = 0; i < m.indicesNormales.length; i++) {
        if (m.indicesNormales[i] >= nNor) throw new Error(`maillage « ${m.nom} » : indice de normale hors bornes`);
      }
      for (let i = 0; i < m.normales.length; i++) {
        if (!Number.isFinite(m.normales[i])) throw new Error(`maillage « ${m.nom} » : normale non finie`);
      }
    }
    maillages.set(m.nom, m);
  }
  const materiaux = new Set<string>();
  for (const m of scene.materiaux) {
    if (!m.nom) throw new Error('materiau sans nom');
    if (materiaux.has(m.nom)) throw new Error(`materiau « ${m.nom} » en double`);
    for (const v of [...m.ambiant, ...m.diffus, ...m.speculaire, ...m.emissif, m.reflectivite, m.opacite]) {
      if (!Number.isFinite(v)) throw new Error(`materiau « ${m.nom} » : valeur non finie`);
    }
    materiaux.add(m.nom);
  }
  const vus = new Set<string>();
  const groupesVus = new Set<string>();
  for (const n of scene.noeuds) {
    // LE NOM VIDE EST LE MONDE (§8.7) : un nœud nomme '' se declarerait son propre parent.
    if (!n.nom) throw new Error('nœud sans nom (la chaine vide designe le monde)');
    if (vus.has(n.nom)) throw new Error(`nœud « ${n.nom} » en double : les noms de la palette de nœuds sont uniques (§8.2)`);
    // PARENTS AVANT ENFANTS. La norme tolere l'inverse ; on l'exige, parce qu'un lecteur qui ne
    // le tolererait pas afficherait un arbre ampute sans rien dire. Et un parent doit etre un
    // GROUPE : accrocher une piece sous une piece marche dans la norme, pas dans l'usage.
    if (n.parent !== '' && !groupesVus.has(n.parent)) {
      throw new Error(`nœud « ${n.nom} » : son parent « ${n.parent} » n'est pas un groupe declare AVANT lui`);
    }
    if (n.matrice) {
      if (n.matrice.length !== 16) throw new Error(`nœud « ${n.nom} » : matrice de ${n.matrice.length} nombres`);
      for (let i = 0; i < 16; i++) if (!Number.isFinite(n.matrice[i])) throw new Error(`nœud « ${n.nom} » : matrice non finie`);
    }
    if (n.maillage !== undefined) {
      const m = maillages.get(n.maillage);
      if (!m) throw new Error(`nœud « ${n.nom} » : maillage « ${n.maillage} » inconnu`);
      if (n.nuanceurs) {
        if (n.nuanceurs.length !== (m.nbTranches ?? 1)) {
          throw new Error(`nœud « ${n.nom} » : ${n.nuanceurs.length} matiere(s) pour ${m.nbTranches ?? 1} tranche(s)`);
        }
        for (const s of n.nuanceurs) if (!materiaux.has(s)) throw new Error(`nœud « ${n.nom} » : materiau « ${s} » inconnu`);
      }
    } else {
      if (n.nuanceurs) throw new Error(`nœud de groupe « ${n.nom} » : un groupe n'a pas de matiere`);
      groupesVus.add(n.nom);
    }
    vus.add(n.nom);
  }
  if (!scene.noeuds.some((n) => n.maillage !== undefined)) throw new Error('aucune piece a ecrire');

  // ------------------------------------------------------------------ 2. les NŒUDS (palette 1)
  const declarations: Uint8Array[] = [];
  let groupes = 0; let modeles = 0; let faces = 0;
  const employes = new Set<string>();
  for (const n of scene.noeuds) {
    const c = new Tampon();
    c.str(n.nom);
    // UN parent, toujours. §8.9.1 : « A node with no parents […] does not appear in the rendered
    // view. » C'est LE defaut muet que u3dWriter.ts raconte sur vingt lignes ; il vaut pour
    // chaque nœud de l'arbre, groupes compris.
    c.u32(1);
    c.str(n.parent);
    // Matrice du nœud relative a ce parent, « in the alphabetic order » de §9.5.1.2.3 : A B C D
    // est la 1re COLONNE ; la translation tombe donc aux rangs 12, 13, 14.
    const mat = n.matrice ?? IDENTITE;
    for (let i = 0; i < 16; i++) c.f32(mat[i]);
    const fiche = compat.fiches ? n.meta : undefined;
    if (n.maillage === undefined) {
      groupes += 1;
      const g = bloc(BLOC.noeudGroupe, c.rendu(), fiche);
      declarations.push(compat.chainesDeGroupe ? chaine(n.nom, 0, [g]) : g);
      continue;
    }
    modeles += 1;
    employes.add(n.maillage);
    faces += maillages.get(n.maillage)!.indices.length / 3;
    c.str(n.maillage);             // §9.5.2.3 : la ressource de modele que ce nœud montre
    c.u32(3);                      // §9.5.2.4 : visible des DEUX cotes (une tole se regarde des deux)
    const internes = [bloc(BLOC.noeudModele, c.rendu(), fiche)];
    if (n.nuanceurs) {
      // MODIFICATEUR DE NUANÇAGE (§9.7.5), 2e maillon de la chaine DU NŒUD : il remplace le
      // groupe de nuançage du maillage par une liste de nuanceurs PAR TRANCHE. Son nom est celui
      // de la chaine (§9.4.3.8), son rang est sa place dans la chaine : 1, juste apres le nœud.
      const s = new Tampon();
      s.str(n.nom);
      s.u32(1);                    // rang dans la chaine
      s.u32(compat.attributsNuancage);   // attributs : 1 = s'applique au groupe de MAILLAGES
      s.u32(n.nuanceurs.length);   // autant de listes que de tranches du maillage
      for (const nom of n.nuanceurs) {
        s.u32(1);                  // un seul nuanceur dans la liste
        s.str(nom);
      }
      internes.push(bloc(BLOC.nuancage, s.rendu()));
    }
    declarations.push(chaine(n.nom, 0, internes));
  }

  // ------------------------------------------------------------------ 3. les RESSOURCES (palette 2)
  // On n'ecrit QUE les maillages qu'un nœud montre : une ressource orpheline pese pour rien.
  const ecrits = scene.maillages.filter((m) => employes.has(m.nom));
  let facesRessources = 0; let sommets = 0;
  for (const m of ecrits) {
    const nPos = m.positions.length / 3;
    const nFaces = m.indices.length / 3;
    const nNor = m.normales ? m.normales.length / 3 : 0;
    const nTr = m.nbTranches ?? 1;
    facesRessources += nFaces; sommets += nPos;
    const c = new Tampon();
    c.str(m.nom);
    c.u32(0);                      // rang dans la chaine : toujours 0 pour ce bloc (§9.6.1.1.2)
    // Description du maillage complet (§9.6.1.1.3)
    c.u32(m.normales ? 0 : 0x00000001);   // 1 = normales EXCLUES (le lecteur les calcule)
    c.u32(nFaces);
    c.u32(nPos);
    c.u32(nNor);
    c.u32(0);                      // couleurs diffuses par sommet
    c.u32(0);                      // couleurs speculaires par sommet
    c.u32(0);                      // coordonnees de texture
    c.u32(nTr);                    // nombre de tranches de matiere (« shading descriptions »)
    for (let i = 0; i < nTr; i++) {
      c.u32(0);                    // ni couleur diffuse ni speculaire par sommet
      c.u32(0);                    // aucune couche de texture
      c.u32(i);                    // identifiant d'origine (informatif)
    }
    // Pas de niveau de detail progressif : min = max = tous les sommets (§9.6.1.1.4)
    c.u32(nPos);
    c.u32(nPos);
    // Description de la ressource (§9.6.1.1.5). Les quantifications inverses ne servent qu'aux
    // mises a jour progressives ; la reference y ecrit 1 par defaut, nous aussi.
    c.u32(1000); c.u32(1000); c.u32(1000);
    c.f32(1); c.f32(1); c.f32(1); c.f32(1); c.f32(1);
    c.f32(0.9); c.f32(-0.5); c.f32(0.985);   // pli, mise a jour, tolerance : valeurs de la reference
    c.u32(0);                      // aucun os
    declarations.push(chaine(m.nom, 1, [bloc(BLOC.declMaillage, c.rendu())]));
  }

  // ------------------------------------------------------------------ 4. NUANCEURS et MATERIAUX
  // Ce ne sont PAS des modificateurs : ils s'ecrivent hors de toute chaine (§9.8). Un nuanceur
  // par materiau, du meme nom (ils vivent dans deux palettes differentes : pas de collision).
  for (const m of scene.materiaux) {
    const c = new Tampon();
    c.str(m.nom);
    c.u32(0x00000001);             // §9.8.3.2 : eclairage ACTIVE ; ni test alpha ni couleur par sommet
    c.f32(0);                      // reference du test alpha (inutilisee)
    c.u32(0x00000617);             // fonction du test alpha : ALWAYS
    c.u32(0x00000606);             // melange : FB_ALPHA_BLEND (l'opacite du materiau s'y applique)
    c.u32(0x00000001);             // passes de rendu : la premiere
    c.u32(0);                      // canaux de texture : aucun
    c.u32(0);                      // canaux alpha de texture : aucun
    c.str(m.nom);                  // le materiau
    declarations.push(bloc(BLOC.nuanceur, c.rendu()));
  }
  for (const m of scene.materiaux) {
    const c = new Tampon();
    c.str(m.nom);
    c.u32(0x0000003f);             // §9.8.4.2 : ambiant, diffus, speculaire, emissif, reflectivite, opacite
    for (const v of m.ambiant) c.f32(v);
    for (const v of m.diffus) c.f32(v);
    for (const v of m.speculaire) c.f32(v);
    for (const v of m.emissif) c.f32(v);
    c.f32(m.reflectivite);
    c.f32(m.opacite);
    declarations.push(bloc(BLOC.materiau, c.rendu()));
  }

  // ------------------------------------------------------------------ 5. les SUITES
  const suites: Uint8Array[] = [];
  if (compat.priorite) {
    const c = new Tampon();
    c.u32(256);                    // §9.4.4.1 : priorite des blocs qui suivent (> 0)
    suites.push(bloc(BLOC.priorite, c.rendu()));
  }
  for (const m of ecrits) {
    const nPos = m.positions.length / 3;
    const nFaces = m.indices.length / 3;
    const nNor = m.normales ? m.normales.length / 3 : 0;
    const c = new Tampon();
    c.str(m.nom);
    c.u32(0);                      // rang dans la chaine
    c.u32(nFaces);
    c.u32(nPos);
    c.u32(nNor);
    c.u32(0); c.u32(0); c.u32(0);  // diffus, speculaire, texture
    c.f32s(m.positions);
    if (m.normales) c.f32s(m.normales);
    // LES FACES (§9.6.1.2.4.6) : tranche, puis pour chacun des 3 coins l'indice de position et —
    // SEULEMENT si les normales ne sont pas exclues — l'indice de normale.
    if (compat.compresse) {
      // Tout ce qui precede dans ce bloc est « non compresse » : le codeur etant dans son etat
      // initial, ce sont des octets simples (voir CodeurArithmetique.u8). Le codeur prend donc la
      // main ICI, sur une frontiere d'octet, et la garde jusqu'a la fin du bloc.
      //   - tranche : contexte DYNAMIQUE cShading (histogramme adaptatif propre a ce bloc) ;
      //   - indices : contextes STATIQUES, de rang le nombre de positions (de normales).
      const ac = new CodeurArithmetique(nFaces * (m.normales ? 14 : 8) + 64);
      for (let i = 0; i < nFaces; i++) {
        ac.compresseDynamique(AC_CONTEXTE_TRANCHE, m.tranches ? m.tranches[i] : 0);
        for (let j = 0; j < 3; j++) {
          ac.compresseStatique(nPos, m.indices[i * 3 + j]);
          if (m.normales) ac.compresseStatique(nNor, m.indicesNormales![i * 3 + j]);
        }
      }
      c.octets(ac.fin());
    } else {
      // En mode « sans compression », les U32 « compresses » de la norme s'ecrivent en U32
      // simples (§9.4.1.2) : c'est ce que fait l'ecrivain de l'ERP.
      const parFace = m.normales ? 7 : 4;
      const f = new Uint32Array(nFaces * parFace);
      let k = 0;
      for (let i = 0; i < nFaces; i++) {
        f[k++] = m.tranches ? m.tranches[i] : 0;
        for (let j = 0; j < 3; j++) {
          f[k++] = m.indices[i * 3 + j];
          if (m.normales) f[k++] = m.indicesNormales![i * 3 + j];
        }
      }
      c.u32s(f);
      if (compat.zeroFinal) c.u32(0);
    }
    suites.push(bloc(BLOC.contMaillage, c.rendu()));
  }

  // ------------------------------------------------------------------ 1. l'EN-TETE
  // UNE SEULE fonction le construit, appelee deux fois (mesurer, puis ecrire) : meme prudence que
  // dans u3dWriter.ts — deux constructions paralleles finissent par diverger.
  const faireEntete = (declSize: number, totalSize: number): Uint8Array => {
    const c = new Tampon();
    c.i16(0);                      // version majeure
    c.i16(0);                      // version mineure
    // 0x04 SANS COMPRESSION (present des la 1re edition de la norme, 2004), pose seulement si
    // on ecrit sans compression ; 0x08 UNITES DEFINIES (ajoute par les editions suivantes) :
    // c'est lui qui fait ecrire le facteur d'echelle.
    c.u32((compat.compresse ? 0 : 0x00000004) | (compat.unitesDefinies ? 0x00000008 : 0));
    c.u32(declSize);
    c.u64(totalSize);
    c.u32(106);                    // UTF-8
    if (compat.unitesDefinies) c.f64(unite);   // facteur vers le METRE (§9.4.1.6)
    return bloc(BLOC.entete, c.rendu());
  };
  let tailleDecl = faireEntete(0, 0).length;
  for (const b of declarations) tailleDecl += b.length;
  let total = tailleDecl;
  for (const b of suites) total += b.length;
  if (tailleDecl > 0xffffffff) throw new Error('declarations de plus de 4 Gio');

  const fichier = new Uint8Array(total);
  let o = 0;
  const poser = (b: Uint8Array): void => { fichier.set(b, o); o += b.length; };
  poser(faireEntete(tailleDecl, total));
  for (const b of declarations) poser(b);
  for (const b of suites) poser(b);
  if (o !== total) throw new Error(`taille ecrite ${o} differente de la taille annoncee ${total}`);

  return {
    fichier, groupes, modeles, ressources: ecrits.length, materiaux: scene.materiaux.length,
    faces, facesRessources, sommets, tailleDeclarations: tailleDecl,
  };
}
