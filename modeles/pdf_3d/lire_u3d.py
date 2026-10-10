# -*- coding: utf-8 -*-
"""lire_u3d.py — LECTEUR À PART d'un fichier U3D (ECMA-363, 4e édition), pour le contrôle.

Écrit d'après la NORME (articles 9.2 à 9.8) et non d'après nos écrivains : il ne partage aucune
ligne avec u3dWriter.ts (ERP) ni u3dWriterMulti.ts. Il relit un fichier bloc par bloc et dit tout
ce qui ne tient pas : alignement, tailles annoncées, taille des déclarations, noms référencés mais
jamais définis, indices hors bornes. Il reconstruit aussi la scène (hiérarchie, matrices) pour en
donner les comptes et la boîte englobante.

Lit les DEUX modes : sans compression (profil 0x04, celui de l'écrivain de l'ERP) et COMPRESSÉ
(celui de tous les fichiers U3D courants, et de notre écrivain multi-pièces par défaut). Le
décodeur arithmétique (_DecodeurArith) est écrit d'après le chapitre 10 et l'annexe A de la norme,
côté LECTURE ; il est éprouvé sur un fichier que nous n'avons pas écrit (dice.u3d, écrit par Adobe :
ses 22 maillages se décodent en surfaces fermées). Seuls les maillages de base sont décodés : un
maillage progressif (résolution minimale inférieure au nombre de positions) est signalé.

    python lire_u3d.py fichier.u3d [--json sortie.json]
    python lire_u3d.py fichier.pdf            (extrait le 1er flux /Subtype /U3D du PDF)

Dans un script :  import lire_u3d ; r = lire_u3d.lire(octets) ; r["anomalies"] doit être vide.
"""
import json
import struct
import sys

import numpy as np

T_ENTETE = 0x00443355
T_CHAINE = 0xFFFFFF14
T_PRIORITE = 0xFFFFFF15
T_GROUPE = 0xFFFFFF21
T_MODELE = 0xFFFFFF22
T_LUMIERE = 0xFFFFFF23
T_VUE = 0xFFFFFF24
T_MAILLAGE_DECL = 0xFFFFFF31
T_MAILLAGE_BASE = 0xFFFFFF3B
T_MAILLAGE_PROG = 0xFFFFFF3C
T_NUANCAGE = 0xFFFFFF45
T_RES_LUMIERE = 0xFFFFFF51
T_RES_VUE = 0xFFFFFF52
T_NUANCEUR = 0xFFFFFF53
T_MATERIAU = 0xFFFFFF54

NOMS_TYPES = {
    T_ENTETE: "en-tête", T_CHAINE: "chaîne de modificateurs", T_PRIORITE: "mise à jour de priorité",
    T_GROUPE: "nœud de groupe", T_MODELE: "nœud de modèle", T_LUMIERE: "nœud de lumière",
    T_VUE: "nœud de vue", T_MAILLAGE_DECL: "déclaration de maillage",
    T_MAILLAGE_BASE: "maillage de base (suite)", T_MAILLAGE_PROG: "maillage progressif (suite)",
    T_NUANCAGE: "modificateur de nuançage", T_RES_LUMIERE: "ressource de lumière",
    T_RES_VUE: "ressource de vue", T_NUANCEUR: "nuanceur", T_MATERIAU: "matériau",
    0xFFFFFF12: "référence de fichier", 0xFFFFFF16: "nouveau type d'objet",
    0xFFFFFF36: "nuage de points", 0xFFFFFF3E: "nuage de points (suite)",
    0xFFFFFF37: "jeu de lignes", 0xFFFFFF3F: "jeu de lignes (suite)",
    0xFFFFFF55: "texture", 0xFFFFFF5C: "texture (suite)", 0xFFFFFF56: "mouvement",
}
# blocs de la partie « suites » du fichier (9.1.3 et 9.4.4) : tout le reste est une déclaration
SUITES = {T_PRIORITE, T_MAILLAGE_BASE, T_MAILLAGE_PROG, 0xFFFFFF3E, 0xFFFFFF3F, 0xFFFFFF5C}


def _bourrage(n):
    return (4 - (n % 4)) % 4


class _Lecteur:
    """Curseur sur une zone d'octets, tout en little-endian (9.2)."""

    def __init__(self, octets, debut, fin):
        self.o = octets
        self.p = debut
        self.fin = fin

    def _prendre(self, n):
        if self.p + n > self.fin:
            raise ValueError("lecture au-delà de la zone (%d + %d > %d)" % (self.p, n, self.fin))
        v = self.o[self.p:self.p + n]
        self.p += n
        return v

    def u8(self):
        return self._prendre(1)[0]

    def u16(self):
        return struct.unpack("<H", self._prendre(2))[0]

    def i16(self):
        return struct.unpack("<h", self._prendre(2))[0]

    def u32(self):
        return struct.unpack("<I", self._prendre(4))[0]

    def u64(self):
        return struct.unpack("<Q", self._prendre(8))[0]

    def f32(self):
        return struct.unpack("<f", self._prendre(4))[0]

    def f64(self):
        return struct.unpack("<d", self._prendre(8))[0]

    def chaine(self):
        n = self.u16()
        return self._prendre(n).decode("utf-8")

    def f32s(self, n):
        return np.frombuffer(self._prendre(4 * n), dtype="<f4")

    def u32s(self, n):
        return np.frombuffer(self._prendre(4 * n), dtype="<u4")

    @property
    def reste(self):
        return self.fin - self.p


# ordre inverse de 4 bits, et de 15 bits (la norme écrit le bit de poids faible d'abord)
_INV4 = (0, 8, 4, 12, 2, 10, 6, 14, 1, 9, 5, 13, 3, 11, 7, 15)
_INV15 = [int(format(i, "015b")[::-1], 2) for i in range(1 << 15)]
RANG_STATIQUE_MAX = 0x3FFE      # 10.4 : au-delà, la valeur est écrite non compressée
ELEPHANT = 0x1FFF               # 10.4.9 : total à partir duquel un histogramme est divisé par deux


class _Histogramme:
    """Histogramme d'un contexte DYNAMIQUE (annexe A.3.3). Symbole 0 = échappement, fréquence initiale 1."""

    def __init__(self):
        self.compte = [0] * 32
        self.cumul = [0] * 32          # cumul[i] : occurrences du symbole i et des plus grands ; cumul[0] : total
        self.compte[0] = 1
        self.cumul[0] = 1

    def ajouter(self, s):
        if s >= 0xFFFF:
            return
        n = len(self.compte)
        if s >= n:
            self.compte += [0] * (s + 32 - n)
            self.cumul += [0] * (s + 32 - n)
        if self.cumul[0] >= ELEPHANT:
            acc = 0
            for i in range(len(self.compte) - 1, -1, -1):
                self.compte[i] >>= 1
                acc += self.compte[i]
                self.cumul[i] = acc
            self.compte[0] += 1
            self.cumul[0] += 1
        self.compte[s] += 1
        for i in range(s + 1):
            self.cumul[i] += 1

    def symbole_de(self, f):
        """Le symbole dont l'intervalle de fréquences cumulées contient f (GetSymbolFromFrequency)."""
        total = self.cumul[0]
        if f == 0 or total < f:
            return 0
        r = 0
        cumul = self.cumul
        for i in range(len(cumul)):
            if total - cumul[i] <= f:
                r = i
            else:
                break
        return r


class _DecodeurArith:
    """Décodeur arithmétique d'UN bloc (10.4, annexe A.3.2 « Bit Stream Read »), à partir d'un octet donné.

    État initial : haut = 0xFFFF, bas = 0, aucun bit en attente, histogrammes vides. Tant que cet état
    n'a pas bougé, un octet « non compressé » se lit tel quel ; ensuite il se décode comme un symbole
    équiprobable parmi 256, bits en ordre inverse (10.4.8)."""

    def __init__(self, octets, debut, fin):
        self.o = bytes(octets[debut:fin]) + b"\0" * 8      # la référence lit dans un tampon complété de zéros
        self.nbits = (fin - debut) * 8
        self.pos = 0
        self.haut = 0xFFFF
        self.bas = 0
        self.attente = 0
        self.histos = {}

    def _code(self):
        """Les 16 bits à venir : le 1er, puis — après les bits de sous-débordement en attente — les 15 suivants."""
        o = self.o
        p = self.pos
        if p + 17 + self.attente > len(o) * 8:
            raise ValueError("flux compressé épuisé (bit %d sur %d)" % (p, self.nbits))
        code = ((o[p >> 3] >> (p & 7)) & 1) << 15
        q = p + 1 + self.attente
        i = q >> 3
        return code | _INV15[((o[i] | (o[i + 1] << 8) | (o[i + 2] << 16)) >> (q & 7)) & 0x7FFF]

    def _avancer(self, haut, bas):
        """Écarte les bits de tête communs à haut et bas, puis compte le sous-débordement (comme l'écrivain)."""
        n = 0
        while not (haut ^ bas) & 0x8000:
            haut = ((haut & 0x7FFF) << 1) | 1
            bas = (bas & 0x7FFF) << 1
            n += 1
        if n:
            n += self.attente
            self.attente = 0
        while bas & 0x4000 and not haut & 0x4000:
            haut = ((haut & 0x7FFF) << 1) | 0x8001
            bas = (bas << 1) & 0x7FFF
            self.attente += 1
        self.haut = haut
        self.bas = bas
        self.pos += n

    def _statique(self, rang):
        """Symbole (1 à rang) d'un contexte statique : tous équiprobables."""
        code = self._code()
        bas = self.bas
        etendue = self.haut + 1 - bas
        cum = (rang * (1 + code - bas) - 1) // etendue
        if not 0 <= cum < rang:
            raise ValueError("flux compressé incohérent (fréquence %d hors de 0..%d)" % (cum, rang - 1))
        self._avancer(bas - 1 + etendue * (cum + 1) // rang, bas + etendue * cum // rang)
        return cum + 1

    def _dynamique(self, h):
        code = self._code()
        bas = self.bas
        etendue = self.haut + 1 - bas
        total = h.cumul[0]
        cum = (total * (1 + code - bas) - 1) // etendue
        if not 0 <= cum < total:
            raise ValueError("flux compressé incohérent (fréquence %d hors de 0..%d)" % (cum, total - 1))
        s = h.symbole_de(cum)
        freq = h.compte[s]
        if not freq:
            raise ValueError("flux compressé incohérent (symbole %d de fréquence nulle)" % s)
        avant = total - h.cumul[s]
        h.ajouter(s)
        self._avancer(bas - 1 + etendue * (avant + freq) // total, bas + etendue * avant // total)
        return s

    def u8(self):
        if self.haut == 0xFFFF and self.bas == 0 and self.attente == 0:
            p = self.pos
            if p + 8 > self.nbits:
                raise ValueError("flux compressé épuisé (bit %d sur %d)" % (p, self.nbits))
            i = p >> 3
            self.pos = p + 8
            return ((self.o[i] | (self.o[i + 1] << 8)) >> (p & 7)) & 0xFF
        s = self._statique(256) - 1
        return (_INV4[s & 0xF] << 4) | _INV4[s >> 4]

    def u32(self):
        a = self.u8()
        b = self.u8()
        c = self.u8()
        return a | (b << 8) | (c << 16) | (self.u8() << 24)

    def compresse_statique(self, rang):
        """U32 « compressé » d'un contexte statique de rang donné (10.4.5) : rend une valeur de 0 à rang - 1."""
        if rang < 1:
            raise ValueError("contexte statique de rang nul")
        if rang > RANG_STATIQUE_MAX:
            return self.u32()
        return self._statique(rang) - 1

    def compresse_dynamique(self, contexte):
        """U32 « compressé » d'un contexte dynamique (10.4.5) : symbole 0 = échappement, la valeur suit en clair."""
        h = self.histos.get(contexte)
        if h is None:
            h = self.histos[contexte] = _Histogramme()
        s = self._dynamique(h)
        if s:
            return s - 1
        v = self.u32()
        h.ajouter(v + 1)
        return v

    @property
    def bits_restants(self):
        return self.nbits - self.pos


def _lire_meta(octets, debut, taille, anomalies, ou):
    """Paires clé/valeur d'un bloc (9.2.6)."""
    if not taille:
        return {}
    out = {}
    try:
        L = _Lecteur(octets, debut, debut + taille)
        n = L.u32()
        for _ in range(n):
            attributs = L.u32()
            cle = L.chaine()
            if attributs & 1:
                t = L.u32()
                out[cle] = bytes(L._prendre(t))
            else:
                out[cle] = L.chaine()
        if L.reste:
            anomalies.append("%s : %d octet(s) de métadonnées non lus" % (ou, L.reste))
    except Exception as e:
        anomalies.append("%s : métadonnées illisibles (%s)" % (ou, e))
    return out


def _decouper(octets, debut, fin, anomalies, ou):
    """Découpe une zone en blocs (9.2). Rend une liste de dictionnaires."""
    blocs = []
    p = debut
    while p < fin:
        if p % 4:
            anomalies.append("%s : bloc à la position %d, non alignée sur 4 octets" % (ou, p))
        if p + 12 > fin:
            anomalies.append("%s : %d octet(s) orphelin(s) en fin de zone (position %d)" % (ou, fin - p, p))
            break
        t, nd, nm = struct.unpack("<III", octets[p:p + 12])
        d0 = p + 12
        m0 = d0 + nd + _bourrage(nd)
        suite = m0 + nm + _bourrage(nm)
        if suite > fin:
            anomalies.append("%s : le bloc 0x%08X à %d déborde (fin annoncée %d, zone %d)" % (ou, t, p, suite, fin))
            break
        if any(octets[d0 + nd:m0]) or any(octets[m0 + nm:suite]):
            anomalies.append("%s : bourrage non nul après le bloc 0x%08X à %d" % (ou, t, p))
        blocs.append({"type": t, "debut": p, "donnees": d0, "taille": nd, "meta": m0, "taille_meta": nm,
                      "fin": suite})
        p = suite
    return blocs


def _noeud(L):
    """Partie commune des nœuds (9.5.1) : nom, parents, matrices 4 x 4 en colonnes."""
    nom = L.chaine()
    n = L.u32()
    parents = []
    for _ in range(n):
        pn = L.chaine()
        m = np.array(L.f32s(16), dtype=np.float64).reshape(4, 4).T     # écrit colonne par colonne
        parents.append((pn, m))
    return nom, parents


def lire(octets):
    """Relit un fichier U3D. Rend un dictionnaire ; r["anomalies"] est vide si tout tient."""
    octets = bytes(octets)
    A = []                 # anomalies
    infos = []             # remarques qui ne sont pas des fautes
    r = {"taille": len(octets), "anomalies": A, "remarques": infos, "entete": None, "blocs": [],
         "noeuds": {}, "ordre_noeuds": [], "ressources": {}, "nuanceurs": {}, "materiaux": {},
         "types": {}}
    if len(octets) < 12 or struct.unpack("<I", octets[:4])[0] != T_ENTETE:
        A.append("le fichier ne commence pas par l'en-tête U3D (0x00443355)")
        return r
    haut = _decouper(octets, 0, len(octets), A, "fichier")
    r["blocs"] = [{"type": "0x%08X" % b["type"], "nom_type": NOMS_TYPES.get(b["type"], "inconnu"),
                   "debut": b["debut"], "taille": b["taille"], "taille_meta": b["taille_meta"]} for b in haut]
    if not haut:
        return r

    def compter(t):
        r["types"][NOMS_TYPES.get(t, "0x%08X" % t)] = r["types"].get(NOMS_TYPES.get(t, "0x%08X" % t), 0) + 1

    # ---------------------------------------------------------------- en-tête (9.4.1)
    b0 = haut[0]
    L = _Lecteur(octets, b0["donnees"], b0["donnees"] + b0["taille"])
    try:
        e = {"majeure": L.i16(), "mineure": L.i16(), "profil": L.u32(), "taille_declarations": L.u32(),
             "taille_fichier": L.u64(), "encodage": L.u32()}
        e["echelle"] = L.f64() if e["profil"] & 0x8 else None
        if L.reste:
            A.append("en-tête : %d octet(s) en trop" % L.reste)
        r["entete"] = e
    except Exception as ex:
        A.append("en-tête illisible : %s" % ex)
        return r
    compter(T_ENTETE)
    sans_compression = bool(e["profil"] & 0x4)
    if e["taille_fichier"] != len(octets):
        A.append("l'en-tête annonce %d octets, le fichier en fait %d" % (e["taille_fichier"], len(octets)))
    if e["encodage"] != 106:
        A.append("encodage des chaînes %d (la norme impose 106, UTF-8)" % e["encodage"])
    r["compresse"] = not sans_compression
    # la partie « déclarations » : l'en-tête et tous les blocs de déclaration, AVANT toute suite
    fin_decl = len(octets)
    for b in haut[1:]:
        if b["type"] in SUITES:
            fin_decl = b["debut"]
            break
    for b in haut:
        if b["debut"] >= fin_decl and b["type"] not in SUITES:
            A.append("bloc de déclaration 0x%08X à %d APRÈS le début des suites (%d)" % (b["type"], b["debut"], fin_decl))
    r["fin_declarations_mesuree"] = fin_decl
    if e["taille_declarations"] != fin_decl:
        A.append("taille des déclarations annoncée %d, mesurée %d (en-tête + blocs de déclaration)"
                 % (e["taille_declarations"], fin_decl))

    suites_maillage = {}       # nom -> bloc

    def traiter(b, chaine=None):
        """Décode un bloc. `chaine` = (nom, type de chaîne, rang) s'il est dans une chaîne."""
        t = b["type"]
        compter(t)
        ou = "%s à %d" % (NOMS_TYPES.get(t, "0x%08X" % t), b["debut"])
        meta = _lire_meta(octets, b["meta"], b["taille_meta"], A, ou)
        L = _Lecteur(octets, b["donnees"], b["donnees"] + b["taille"])
        try:
            if t == T_CHAINE:
                if chaine is not None:
                    A.append("%s : chaîne imbriquée dans une chaîne" % ou)
                nom = L.chaine()
                tc = L.u32()
                attributs = L.u32()
                if attributs & 1:
                    L.f32s(4)
                if attributs & 2:
                    L.f32s(6)
                pad = _bourrage(L.p - b["donnees"])
                if any(L._prendre(pad)):
                    A.append("%s : bourrage de chaîne non nul" % ou)
                n = L.u32()
                internes = _decouper(octets, L.p, b["donnees"] + b["taille"], A, "chaîne « %s »" % nom)
                if len(internes) != n:
                    A.append("%s « %s » : %d modificateur(s) annoncé(s), %d bloc(s) trouvé(s)" % (ou, nom, n, len(internes)))
                if tc not in (0, 1, 2):
                    A.append("%s « %s » : type de chaîne %d inconnu" % (ou, nom, tc))
                for rang, bi in enumerate(internes):
                    traiter(bi, (nom, tc, rang))
                return
            if t in (T_GROUPE, T_MODELE):
                nom, parents = _noeud(L)
                d = {"type": "groupe" if t == T_GROUPE else "modele", "parents": parents, "meta": meta,
                     "nuanceurs": None, "debut": b["debut"]}
                if t == T_MODELE:
                    d["ressource"] = L.chaine()
                    d["visibilite"] = L.u32()
                    if d["visibilite"] > 3:
                        A.append("%s « %s » : visibilité %d hors de 0..3" % (ou, nom, d["visibilite"]))
                if nom in r["noeuds"]:
                    A.append("nœud « %s » déclaré deux fois" % nom)
                if nom == "":
                    A.append("%s : un nœud porte le nom vide, réservé au monde" % ou)
                r["noeuds"][nom] = d
                r["ordre_noeuds"].append(nom)
                if chaine is not None:
                    if chaine[0] != nom:
                        A.append("%s : nom « %s » différent de celui de sa chaîne « %s »" % (ou, nom, chaine[0]))
                    if chaine[1] != 0:
                        A.append("%s « %s » : nœud dans une chaîne de type %d (attendu 0)" % (ou, nom, chaine[1]))
                    if chaine[2] != 0:
                        A.append("%s « %s » : le nœud n'est pas le 1er modificateur de sa chaîne" % (ou, nom))
            elif t == T_NUANCAGE:
                nom = L.chaine()
                rang = L.u32()
                attributs = L.u32()
                nl = L.u32()
                listes = []
                for _ in range(nl):
                    ns = L.u32()
                    listes.append([L.chaine() for _ in range(ns)])
                if chaine is None:
                    A.append("%s « %s » : hors de toute chaîne de modificateurs" % (ou, nom))
                else:
                    if chaine[0] != nom:
                        A.append("%s : nom « %s » différent de celui de sa chaîne « %s »" % (ou, nom, chaine[0]))
                    if rang != chaine[2]:
                        A.append("%s « %s » : rang annoncé %d, rang réel dans la chaîne %d" % (ou, nom, rang, chaine[2]))
                    if chaine[1] == 0:
                        if nom in r["noeuds"]:
                            r["noeuds"][nom]["nuanceurs"] = listes
                            r["noeuds"][nom]["attributs_nuancage"] = attributs
                        else:
                            A.append("%s « %s » : placé avant son nœud" % (ou, nom))
                    elif chaine[1] == 1:
                        r["ressources"].setdefault(nom, {})["nuanceurs"] = listes
                if not attributs & 1:
                    infos.append("nuançage « %s » : attributs 0x%X sans le bit « maillage »" % (nom, attributs))
            elif t == T_MAILLAGE_DECL:
                nom = L.chaine()
                rang = L.u32()
                d = {"attributs": L.u32(), "faces": L.u32(), "positions": L.u32(), "normales": L.u32(),
                     "diffus": L.u32(), "speculaires": L.u32(), "textures": L.u32()}
                ns = L.u32()
                d["tranches"] = []
                for _ in range(ns):
                    sa = L.u32()
                    nc = L.u32()
                    dims = [L.u32() for _ in range(nc)]
                    d["tranches"].append({"attributs": sa, "couches": nc, "dimensions": dims, "origine": L.u32()})
                d["resolution_min"] = L.u32()
                d["resolution_max"] = L.u32()
                d["qualite"] = [L.u32() for _ in range(3)]
                d["quantification_inverse"] = [float(x) for x in L.f32s(5)]
                d["pli"], d["mise_a_jour"], d["tolerance"] = [float(x) for x in L.f32s(3)]
                d["os"] = L.u32()
                if d["os"]:
                    infos.append("maillage « %s » : %d os (squelette non décodé)" % (nom, d["os"]))
                    L.p = L.fin
                d["meta"] = meta
                d["exclut_normales"] = bool(d["attributs"] & 1)
                if rang != 0:
                    A.append("%s « %s » : rang %d (la norme impose 0)" % (ou, nom, rang))
                if d["resolution_min"] != d["positions"] or d["resolution_max"] != d["positions"]:
                    infos.append("maillage « %s » : résolutions %d..%d pour %d positions (maillage progressif)"
                                 % (nom, d["resolution_min"], d["resolution_max"], d["positions"]))
                if chaine is None:
                    infos.append("maillage « %s » déclaré hors chaîne" % nom)
                else:
                    if chaine[0] != nom:
                        A.append("%s : nom « %s » différent de celui de sa chaîne « %s »" % (ou, nom, chaine[0]))
                    if chaine[1] != 1:
                        A.append("%s « %s » : dans une chaîne de type %d (attendu 1, ressource)" % (ou, nom, chaine[1]))
                if nom in r["ressources"] and "faces" in r["ressources"][nom]:
                    A.append("ressource « %s » déclarée deux fois" % nom)
                r["ressources"].setdefault(nom, {}).update(d)
            elif t == T_MAILLAGE_BASE:
                nom = L.chaine()
                if nom in suites_maillage:
                    A.append("suite du maillage « %s » présente deux fois" % nom)
                suites_maillage[nom] = (b, L.p)
                return
            elif t == T_NUANCEUR:
                nom = L.chaine()
                d = {"attributs": L.u32(), "reference_alpha": L.f32(), "test_alpha": L.u32(),
                     "melange": L.u32(), "passes": L.u32(), "canaux": L.u32(), "canaux_alpha": L.u32(),
                     "materiau": L.chaine(), "textures": []}
                for i in range(8):
                    if d["canaux"] & (1 << i):
                        tx = {"nom": L.chaine(), "intensite": L.f32(), "fonction": L.u8(), "source": L.u8(),
                              "constante": L.f32(), "mode": L.u8()}
                        L.f32s(32)
                        tx["repetition"] = L.u8()
                        d["textures"].append(tx)
                if not 0x610 <= d["test_alpha"] <= 0x617:
                    A.append("nuanceur « %s » : fonction de test alpha 0x%X hors de 0x610..0x617" % (nom, d["test_alpha"]))
                if not 0x604 <= d["melange"] <= 0x607:
                    A.append("nuanceur « %s » : fonction de mélange 0x%X hors de 0x604..0x607" % (nom, d["melange"]))
                if nom in r["nuanceurs"]:
                    A.append("nuanceur « %s » déclaré deux fois" % nom)
                if chaine is not None:
                    A.append("nuanceur « %s » dans une chaîne de modificateurs (interdit)" % nom)
                r["nuanceurs"][nom] = d
            elif t == T_MATERIAU:
                nom = L.chaine()
                d = {"attributs": L.u32(), "ambiant": [float(x) for x in L.f32s(3)],
                     "diffus": [float(x) for x in L.f32s(3)], "speculaire": [float(x) for x in L.f32s(3)],
                     "emissif": [float(x) for x in L.f32s(3)], "reflectivite": L.f32(), "opacite": L.f32()}
                if nom in r["materiaux"]:
                    A.append("matériau « %s » déclaré deux fois" % nom)
                if chaine is not None:
                    A.append("matériau « %s » dans une chaîne de modificateurs (interdit)" % nom)
                r["materiaux"][nom] = d
            elif t == T_PRIORITE:
                p = L.u32()
                r.setdefault("priorites", []).append(p)
                if p == 0:
                    A.append("%s : priorité 0 (elle doit être supérieure à zéro)" % ou)
            else:
                infos.append("bloc %s : type non décodé par ce lecteur" % ou)
                return
            if L.reste:
                A.append("%s : %d octet(s) de données non lus (taille annoncée trop grande ?)" % (ou, L.reste))
        except Exception as ex:
            A.append("%s : illisible (%s)" % (ou, ex))

    for b in haut[1:]:
        traiter(b)

    # ---------------------------------------------------------------- suites des maillages (9.6.1.2)
    for nom, (b, p) in suites_maillage.items():
        ou = "suite du maillage « %s » à %d" % (nom, b["debut"])
        res = r["ressources"].get(nom)
        if res is None or "faces" not in res:
            A.append("%s : aucune déclaration de ce maillage" % ou)
            continue
        L = _Lecteur(octets, p, b["donnees"] + b["taille"])
        try:
            rang = L.u32()
            nf, npos, nnor, ndif, nspe, ntex = [L.u32() for _ in range(6)]
            if rang != 0:
                A.append("%s : rang %d (la norme impose 0)" % (ou, rang))
            progressif = res["resolution_min"] != res["positions"]
            for libelle, a_, b_ in (("faces", nf, res["faces"]), ("positions", npos, res["positions"]),
                                    ("normales", nnor, res["normales"])):
                if a_ != b_ and not progressif:
                    A.append("%s : %d %s, la déclaration en annonce %d" % (ou, a_, libelle, b_))
            pos = np.array(L.f32s(npos * 3), dtype=np.float64).reshape(-1, 3)
            nor = np.array(L.f32s(nnor * 3), dtype=np.float64).reshape(-1, 3)
            L.f32s(ndif * 4)
            L.f32s(nspe * 4)
            L.f32s(ntex * 4)
            tranches = res["tranches"]
            avec_normales = not res["exclut_normales"]
            uniforme = all(t["attributs"] == 0 and t["couches"] == 0 for t in tranches)
            if not sans_compression:
                # 9.6.1.2.4.6, lu par le décodeur arithmétique : tranche (contexte dynamique cShading), puis par
                # coin la position, la normale si elle n'est pas exclue, les couleurs et les textures que la
                # tranche annonce (contextes statiques, de rang le nombre d'éléments de chaque sorte).
                D = _DecodeurArith(octets, L.p, L.fin)
                l_t, l_f, l_n = [], [], []
                for i in range(nf):
                    s = D.compresse_dynamique(1)
                    l_t.append(s)
                    t = tranches[s] if s < len(tranches) else {"attributs": 0, "couches": 0}
                    for c in range(3):
                        l_f.append(D.compresse_statique(npos))
                        if avec_normales:
                            l_n.append(D.compresse_statique(nnor))
                        if t["attributs"] & 1:
                            D.compresse_statique(ndif)
                        if t["attributs"] & 2:
                            D.compresse_statique(nspe)
                        for _ in range(t["couches"]):
                            D.compresse_statique(ntex)
                id_tranche = np.array(l_t, dtype=np.uint32)
                faces = np.array(l_f, dtype=np.uint32).reshape(-1, 3)
                faces_n = np.array(l_n, dtype=np.uint32).reshape(-1, 3) if avec_normales else None
                # 10.4.10 : l'écrivain a fini par un U32 nul, qu'on ne décode pas (il ne sert qu'à fournir les
                # bits d'avance du dernier symbole) : il doit donc RESTER des bits, une trentaine, guère plus.
                res["bits_apres_faces"] = D.bits_restants
                if nf and D.bits_restants < 16:
                    A.append("%s : flux compressé trop court (%d bit(s) après la dernière face : le U32 nul final "
                             "manque)" % (ou, D.bits_restants))
                elif D.bits_restants > 96:
                    A.append("%s : %d bit(s) non lus après la dernière face" % (ou, D.bits_restants))
                L.p = L.fin
            elif uniforme:
                par_coin = 2 if avec_normales else 1
                larg = 1 + 3 * par_coin
                brut = np.array(L.u32s(nf * larg)).reshape(-1, larg) if nf else np.zeros((0, larg), np.uint32)
                id_tranche = brut[:, 0]
                coins = brut[:, 1:].reshape(-1, 3, par_coin)
                faces = coins[:, :, 0]
                faces_n = coins[:, :, 1] if avec_normales else None
            else:
                id_tranche = np.zeros(nf, np.uint32)
                faces = np.zeros((nf, 3), np.uint32)
                faces_n = np.zeros((nf, 3), np.uint32) if avec_normales else None
                for i in range(nf):
                    s = L.u32()
                    id_tranche[i] = s
                    t = tranches[s] if s < len(tranches) else {"attributs": 0, "couches": 0}
                    for c in range(3):
                        faces[i, c] = L.u32()
                        if avec_normales:
                            faces_n[i, c] = L.u32()
                        if t["attributs"] & 1:
                            L.u32()
                        if t["attributs"] & 2:
                            L.u32()
                        for _ in range(t["couches"]):
                            L.u32()
            if L.reste == 4 and L.u32() == 0:
                res["zero_final"] = True       # l'encodeur de référence d'Intel en écrit un
            elif L.reste:
                A.append("%s : %d octet(s) non lus après les faces" % (ou, L.reste))
            if nf and int(faces.max()) >= npos:
                A.append("%s : indice de position %d hors bornes (%d positions)" % (ou, int(faces.max()), npos))
            if nf and avec_normales and int(faces_n.max()) >= max(nnor, 1):
                A.append("%s : indice de normale %d hors bornes (%d normales)" % (ou, int(faces_n.max()), nnor))
            if nf and int(id_tranche.max()) >= max(len(tranches), 1):
                A.append("%s : tranche %d hors bornes (%d tranche(s))" % (ou, int(id_tranche.max()), len(tranches)))
            if npos and not np.isfinite(pos).all():
                A.append("%s : positions non finies" % ou)
            if nf:
                deg = (faces[:, 0] == faces[:, 1]) | (faces[:, 1] == faces[:, 2]) | (faces[:, 0] == faces[:, 2])
                if deg.any():
                    A.append("%s : %d face(s) dégénérée(s)" % (ou, int(deg.sum())))
                utilises = np.zeros(npos, bool)
                utilises[faces.reshape(-1)[faces.reshape(-1) < npos]] = True
                if not utilises.all():
                    A.append("%s : %d position(s) qu'aucune face n'emploie (le lecteur cadrerait dessus)"
                             % (ou, int((~utilises).sum())))
            if nnor:
                lon = np.linalg.norm(nor, axis=1)
                if (np.abs(lon - 1.0) > 1e-2).any():
                    A.append("%s : %d normale(s) non unitaire(s)" % (ou, int((np.abs(lon - 1.0) > 1e-2).sum())))
            res["donnees"] = {"positions": pos, "normales": nor, "faces": faces, "faces_normales": faces_n,
                              "tranches": id_tranche}
        except Exception as ex:
            A.append("%s : illisible (%s)" % (ou, ex))
    for nom, res in r["ressources"].items():
        if "faces" not in res:
            A.append("ressource « %s » : modifiée mais jamais déclarée" % nom)
        elif res["faces"] and "donnees" not in res and res["resolution_min"] and nom not in suites_maillage:
            A.append("ressource « %s » : déclarée (%d faces) mais sans bloc de suite" % (nom, res["faces"]))

    # ---------------------------------------------------------------- références et hiérarchie
    N = r["noeuds"]
    for nom, d in N.items():
        if not d["parents"]:
            A.append("nœud « %s » sans parent : il n'apparaît pas dans la scène (8.9.1)" % nom)
        for pn, _ in d["parents"]:
            if pn != "" and pn not in N:
                A.append("nœud « %s » : parent « %s » jamais défini" % (nom, pn))
        if d["type"] == "modele":
            if d["ressource"] not in r["ressources"] or "faces" not in r["ressources"][d["ressource"]]:
                A.append("nœud « %s » : ressource « %s » jamais définie" % (nom, d["ressource"]))
            if d["nuanceurs"] is not None:
                res = r["ressources"].get(d["ressource"], {})
                nt = len(res.get("tranches", []))
                if nt and len(d["nuanceurs"]) != nt:
                    infos.append("nœud « %s » : %d liste(s) de nuanceurs pour %d tranche(s) du maillage"
                                 % (nom, len(d["nuanceurs"]), nt))
                for liste in d["nuanceurs"]:
                    for s in liste:
                        if s not in r["nuanceurs"]:
                            A.append("nœud « %s » : nuanceur « %s » jamais défini" % (nom, s))
    for nom, d in r["nuanceurs"].items():
        if d["materiau"] != "" and d["materiau"] not in r["materiaux"]:
            A.append("nuanceur « %s » : matériau « %s » jamais défini" % (nom, d["materiau"]))
    # l'ordre : un parent déclaré avant ses enfants (la norme tolère l'inverse, on le signale)
    rang = {n: i for i, n in enumerate(r["ordre_noeuds"])}
    tardifs = sum(1 for n, d in N.items() for pn, _ in d["parents"] if pn in rang and rang[pn] > rang[n])
    if tardifs:
        infos.append("%d nœud(s) déclaré(s) avant leur parent (toléré par la norme)" % tardifs)

    # matrices monde, par descente depuis le monde ; détection des cycles
    monde = {}

    def matrices(nom, pile=()):
        if nom == "":
            return [np.eye(4)]
        if nom in monde:
            return monde[nom]
        if nom in pile:
            A.append("cycle dans la hiérarchie au nœud « %s »" % nom)
            return []
        d = N.get(nom)
        if d is None:
            return []
        out = []
        for pn, m in d["parents"]:
            for mp in matrices(pn, pile + (nom,)):
                out.append(mp @ m)
        monde[nom] = out
        return out

    bmin = np.array([np.inf] * 3)
    bmax = np.array([-np.inf] * 3)
    tri_poses = 0
    modeles_poses = 0
    for nom, d in N.items():
        ms = matrices(nom)
        if d["type"] != "modele":
            continue
        res = r["ressources"].get(d["ressource"], {})
        dn = res.get("donnees")
        if not ms and d["parents"]:
            A.append("nœud « %s » : non relié au monde" % nom)
        for m in ms:
            modeles_poses += 1
            tri_poses += int(res.get("faces", 0))
            if dn is not None and len(dn["positions"]):
                w = dn["positions"] @ m[:3, :3].T + m[:3, 3]
                bmin = np.minimum(bmin, w.min(axis=0))
                bmax = np.maximum(bmax, w.max(axis=0))
    r["matrices_monde"] = monde
    groupes = [n for n, d in N.items() if d["type"] == "groupe"]
    modeles = [n for n, d in N.items() if d["type"] == "modele"]
    ress = {n: v for n, v in r["ressources"].items() if "faces" in v}
    r["comptes"] = {
        "noeuds": len(N), "groupes": len(groupes), "modeles": len(modeles),
        "modeles_poses": modeles_poses, "ressources": len(ress),
        "ressources_employees": len({N[n]["ressource"] for n in modeles}),
        "triangles_ressources": int(sum(v["faces"] for v in ress.values())),
        "sommets_ressources": int(sum(v["positions"] for v in ress.values())),
        "normales_ressources": int(sum(v["normales"] for v in ress.values())),
        "triangles_poses": tri_poses,
        "nuanceurs": len(r["nuanceurs"]), "materiaux": len(r["materiaux"]),
        "modeles_avec_nuancage": sum(1 for n in modeles if N[n]["nuanceurs"] is not None),
        "noeuds_avec_metadonnees": sum(1 for d in N.values() if d["meta"]),
        "profondeur": 0,
    }

    def profondeur(nom, vus=()):
        if nom == "" or nom in vus or nom not in N or not N[nom]["parents"]:
            return 0
        return 1 + max(profondeur(pn, vus + (nom,)) for pn, _ in N[nom]["parents"])

    r["comptes"]["profondeur"] = max([profondeur(n) for n in N] or [0])
    r["boite"] = [[float(x) for x in bmin], [float(x) for x in bmax]] if np.isfinite(bmin).all() else None
    inutiles = sorted(set(ress) - {N[n]["ressource"] for n in modeles})
    if inutiles:
        infos.append("%d ressource(s) qu'aucun nœud n'emploie : %s" % (len(inutiles), ", ".join(inutiles[:5])))
    return r


def extraire_du_pdf(chemin):
    """Rend les octets du 1er flux 3D d'un PDF (décompressé s'il le faut), par PyMuPDF."""
    import fitz
    doc = fitz.open(chemin)
    for x in range(1, doc.xref_length()):
        try:
            if doc.xref_get_key(x, "Subtype")[1] == "/U3D" and doc.xref_is_stream(x):
                return doc.xref_stream(x)
        except Exception:
            continue
    raise ValueError("aucun flux /Subtype /U3D dans %s" % chemin)


def resume(r):
    """Quelques lignes lisibles."""
    out = []
    e = r["entete"] or {}
    out.append("taille %d octets ; profil 0x%X ; déclarations %s ; échelle %s m par unité"
               % (r["taille"], e.get("profil", 0), e.get("taille_declarations"), e.get("echelle")))
    out.append("blocs de 1er niveau : %d ; types : %s" % (len(r["blocs"]),
               ", ".join("%s × %d" % kv for kv in sorted(r["types"].items()))))
    c = r.get("comptes")
    if c:
        out.append("nœuds %d (groupes %d, modèles %d, profondeur %d) ; ressources %d ; triangles : %d dans "
                   "les ressources, %d posés ; nuanceurs %d ; matériaux %d"
                   % (c["noeuds"], c["groupes"], c["modeles"], c["profondeur"], c["ressources"],
                      c["triangles_ressources"], c["triangles_poses"], c["nuanceurs"], c["materiaux"]))
    if r.get("boite"):
        out.append("boîte englobante : %s à %s" % tuple("(%.4f, %.4f, %.4f)" % tuple(p) for p in r["boite"]))
    for x in r["remarques"][:12]:
        out.append("remarque : " + x)
    out.append("ANOMALIES : %d" % len(r["anomalies"]))
    for x in r["anomalies"][:40]:
        out.append("  - " + x)
    return out


def _serialisable(r):
    d = {k: v for k, v in r.items() if k not in ("noeuds", "ressources", "matrices_monde")}
    d["noeuds"] = {n: {"type": v["type"], "parents": [p for p, _ in v["parents"]],
                       "ressource": v.get("ressource"), "nuanceurs": v["nuanceurs"], "meta": {
                           k: (x if isinstance(x, str) else "<binaire>") for k, x in v["meta"].items()}}
                   for n, v in r["noeuds"].items()}
    d["ressources"] = {n: {k: x for k, x in v.items() if k not in ("donnees", "meta")}
                       for n, v in r["ressources"].items()}
    return d


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        sys.exit(2)
    chemin = args[0]
    with open(chemin, "rb") as f:
        tete = f.read(5)
    if tete.startswith(b"%PDF"):
        data = extraire_du_pdf(chemin)
    else:
        with open(chemin, "rb") as f:
            data = f.read()
    res = lire(data)
    for ligne in resume(res):
        print(ligne)
    if "--json" in sys.argv:
        dst = sys.argv[sys.argv.index("--json") + 1]
        with open(dst, "w", encoding="utf-8", newline="\n") as f:
            json.dump(_serialisable(res), f, ensure_ascii=False, indent=1, default=str)
    sys.exit(1 if res["anomalies"] else 0)
