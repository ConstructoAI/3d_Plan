# -*- coding: utf-8 -*-
r"""
dependances_dll.py : quelles DLL manqueront sur un poste neuf ? (analyse des tables d'import PE, pur Python)

Usage
    python dependances_dll.py <dossier> [--json] [--symboles] [--tous-fichiers] [--toutes-archi]
                              [--dossier-dll D]... [--copier-vc DOSSIER]

    <dossier>          arborescence a analyser (ex. outils\python, outils\blender, outils\oda\convertisseur).
                       Sa racine est prise pour le « dossier de l'application » (celui de python.exe,
                       blender.exe, ODAFileConverter.exe, node.exe) : le chargeur y cherche toujours.
    --json             sortie JSON sur stdout au lieu du rapport texte.
    --symboles         verifie aussi, pour chaque DLL trouvee DANS l'arborescence, que chaque fonction
                       importee (par nom ou par ordinal) existe dans sa table d'export. Revele les DLL
                       d'une version trop ancienne (« point d'entree introuvable »). Plus lent.
    --tous-fichiers    cherche la signature MZ/PE dans TOUS les fichiers, meme ceux dont l'extension dit
                       le contraire (.py, .png...) ; par defaut ces extensions-la sont sautees.
    --toutes-archi     analyse aussi les fichiers d'une autre architecture que x64 (32 bits, ARM64) :
                       par defaut ils sont seulement comptes, car un processus x64 ne les charge jamais.
    --dossier-dll D    dossier (relatif a <dossier> ou absolu) que le programme ajoute lui-meme a la
                       recherche des DLL (os.add_dll_directory, AddDllDirectory) ; repetable.
    --copier-vc D      copie dans D, depuis C:\Windows\System32, les DLL du redistribuable Visual C++
                       (msvcp140*.dll, vcruntime140*.dll, concrt140.dll, vccorlib140.dll, vcomp140.dll,
                       mfc140*.dll...) signalees MANQUANTES (absentes, ou hors de portee du chargeur).
                       Deploiement « app-local » permis par Microsoft. N'ecrase jamais un fichier existant ;
                       imprime la version de chaque copie. Pour que tous les modules les trouvent,
                       D = la racine (dossier de l'exe). Relancer ensuite l'analyse, avec --symboles.

Quels fichiers sont analyses
    Tout fichier PE : les extensions connues (.exe .dll .pyd .node .ocx .cpl .drv .ax .mui, et les modules
    d'ODA .tx .txv .txr .txexp) ET tout autre fichier qui commence par la signature MZ puis PE\0\0
    (ex. les .exp d'ODA). Pour aller vite, les extensions de donnees evidentes (.py, .pyc, .txt, .json,
    .png, .ttf...) et les dossiers *.dist-info ne sont pas ouverts, sauf avec --tous-fichiers.

Ce qu'il fait
    Pour chaque fichier PE, il lit la table d'import et la table d'import differe (delay-load), en lecture
    directe des en-tetes (sans pefile ; memes resultats que pefile sur 152 fichiers), puis classe chaque
    DLL importee :
      - trouvee : dans le dossier du module qui l'importe, a la racine (dossier de l'application), ou dans
        un dossier de DLL connu, pour les modules de sa PORTEE : <paquet>.libs et <paquet>\.libs
        (delvewheel : seulement pour ce paquet, qui l'ajoute a son import), le dossier d'un paquet dont
        le __init__.py appelle add_dll_directory (ex. pygame), pywin32_system32 (tout le dossier parent,
        ajoute au demarrage par pywin32.pth), un assemblage prive (dossier X contenant X.manifest, ex.
        blender.shared et blender.crt de Blender : tout le dossier parent), --dossier-dll (tout) ;
      - de Windows : ensembles d'API (api-ms-win-*, ext-ms-*), DLL du noyau connues (kernel32, user32,
        gdi32, advapi32, shell32, ole32, ws2_32, ucrtbase...), ou DLL de C:\Windows\System32 dont
        l'EDITEUR (CompanyName) est « Microsoft Corporation », hors redistribuables Visual C++ et DirectX
        (le nom de produit ne suffit pas : ze_loader.dll d'Intel se dit « ... for Windows(R) ») ;
      - PILOTE : nvcuda, nvapi64, nvoptix, nvml, nvrtc*, vulkan-1, amdhip64*, hiprtc*, ze_loader,
        igc*, OpenCL... : poses par le pilote du materiel, non embarquables, charges a la demande ;
      - OPTIONNELLE : importee par un module facultatif connu (liste OPTIONNELS_CONNUS : la couche TBB
        de numba ; 5 modules d'ODA 27.1 que l'editeur livre deja incomplets, lacunes identiques dans
        l'installation d'origine : AcModelDocObj, W3Dtk, WhipTk, imageformats\qsvg, NwRecapImport) ;
      - MANQUANTE : tout le reste. Soit absente de l'arborescence et pas de Windows (une DLL de
        System32 qui n'est pas de Windows, ex. msvcp140.dll, manquera sur un poste neuf) ; soit
        presente AILLEURS dans l'arborescence, hors de portee du chargeur (elle ne se charge que par
        accident, si un autre module a deja charge une DLL du meme nom). Le rapport donne sa version,
        son produit et, le cas echeant, ou elle se trouve.
    Un .pyd d'une autre version de CPython (ex. *.cp310-win_amd64.pyd dans un arbre qui contient
    python313.dll) n'est jamais charge : il est seulement compte.
    Avec --symboles, la DLL retenue pour un import est la premiere trouvee dans cet ordre : dossier du
    module, racine, dossier de DLL de sa portee. Toutes les exportations sont lues, en entier.
    Pour comparer a pefile : il s'arrete a 8 192 exportations par defaut (passer max_symbol_exports,
    sinon Qt6 et TD_DbCore semblent incomplets), tronque les noms a 512 caracteres (ODA en a de 602)
    et remplace les ordinaux de ws2_32, wsock32 et oleaut32 par des noms tires de sa propre table.

Sortie JSON (--json), cles principales
    binaires, par_signature (fichiers PE reconnus hors des extensions connues), illisibles, autres_archi,
    autres_versions_python, dossiers_recherche, portees ;
    manquantes / manquantes_differees / optionnelles / pilotes : { "nom.dll": {
        "importeurs": [chemins relatifs], "etat": "introuvable" | "system32_non_windows" | "pilote",
        "redistribuable_vc": bool, "presente_dans": [dossiers] (si hors de portee),
        "system32": {"chemin", "version", "produit", "societe"} (si presente dans System32),
        "pourquoi": texte (optionnelles) } } ;
    symboles_manquants (avec --symboles) : { "importeur": { "dll": {"cible": chemin relatif,
        "differe": bool, "nombre": n, "exemples": [noms ou "#ordinal"]} } } ;
    fichiers : { "chemin relatif": {"machine", "manquantes": [...], ...} } ; copies_vc (avec --copier-vc).

Limites (a connaitre)
    - Les DLL chargees dynamiquement (LoadLibrary, ctypes) n'apparaissent dans aucune table : seul un
      essai reel les revele (voir test_python_portable.py, essai « dll_chargees »). Idem pour un
      dossier ajoute a l'execution que l'outil ne devine pas (le declarer par --dossier-dll).
    - --symboles suppose que la DLL retenue est celle que le processus chargera : si une DLL du meme nom
      est deja chargee (par un autre module), Windows reutilise celle-la.
    - Il faut un Python 64 bits : un Python 32 bits verrait SysWOW64 a la place de System32.
    - Imports differes : listes a part ; ils ne manquent qu'a l'appel de la fonction.
    - Lent a froid : l'antivirus inspecte chaque .exe/.dll neuf a son ouverture (106 a 150 s pour
      1 050 binaires la premiere fois, 8 s ensuite).

Code de sortie : 0 si aucune DLL x64 n'est MANQUANTE en import direct (et, avec --symboles, aucune
fonction importee introuvable), 1 sinon, 2 si erreur d'usage.
"""
import ctypes
import json
import mmap
import os
import re
import shutil
import struct
import sys

EXTENSIONS = (".exe", ".dll", ".pyd", ".node", ".ocx", ".cpl", ".drv", ".ax", ".mui",
              ".tx", ".txv", ".txr", ".txexp")                  # .tx* : modules d'ODA (Teigha)
# Extensions de donnees jamais ouvertes pour y chercher la signature (sauf --tous-fichiers).
SANS_SIGNATURE = set("""
.py .pyc .pyo .pyi .pyx .pxd .pth .typed .txt .md .rst .json .xml .html .htm .js .mjs .cjs .ts .map .css
.scss .png .jpg .jpeg .gif .bmp .svg .ico .icns .webp .tif .tiff .exr .hdr .ttf .otf .ttc .woff .woff2
.afm .pfb .pdf .zip .gz .br .bz2 .xz .zst .whl .tar .7z .h .hpp .hxx .c .cc .cpp .cxx .inl .f .f90 .lib
.a .pdb .ilk .obj .o .ini .cfg .conf .toml .yaml .yml .csv .tsv .tcl .tm .msg .enc .mo .po .pot .qm
.npy .npz .pkl .pickle .dat .db .sqlite .blend .glsl .osl .oso .ptx .cubin .fatbin .spv .sh .bat .cmd
.ps1 .psm1 .psd1 .lnk .manifest .cat .sig .pem .crt .cer .key .der .license .lic .sample .in .ac .am
.cmake .mk .rc .def .idl .tlb .chm .wav .mp3 .ogg .flac .mp4 .avi .mov .ico .cur .ani .xsd .xsl .xslt
.dtd .ipynb .jar .class .properties .tex .sty .bib .log .bak .tmp .swp .lock .rs .go .java .rb .pl .pm
.lua .r .m .sql .graphql .proto .fbs .gitignore .gitattributes .editorconfig .nsi .nsh .vbs .reg .inf
""".split())
SYSTEM32 = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")
MACHINES = {0x14C: "x86", 0x8664: "x64", 0xAA64: "ARM64", 0x1C4: "ARMNT", 0xA641: "ARM64EC", 0x0: "inconnue"}

# DLL du systeme d'exploitation reconnues sans consulter System32 (liste non exhaustive : le reste
# est tranche par la ressource de version du fichier de System32).
WINDOWS_CONNUES = set("""
kernel32 kernelbase ntdll user32 gdi32 gdi32full advapi32 shell32 ole32 oleaut32 ws2_32 ucrtbase msvcrt
comctl32 comdlg32 crypt32 bcrypt bcryptprimitives ncrypt secur32 sspicli shlwapi version winmm winspool.drv
wininet winhttp iphlpapi dnsapi netapi32 userenv setupapi cfgmgr32 dbghelp dbgcore psapi powrprof imm32
uxtheme dwmapi dxgi d3d9 d3d10 d3d10_1 d3d11 d3d12 d3dcompiler_47 dcomp opengl32 glu32 msimg32 rpcrt4 mpr
wtsapi32 wldap32 normaliz propsys shcore urlmon usp10 dwrite d2d1 windowscodecs mfplat mfreadwrite mf
avrt hid dsound xinput1_4 xinput9_1_0 winusb credui ktmw32 authz mscoree wintrust imagehlp pdh wevtapi
mswsock winsta cabinet msi msvfw32 avifil32 oledlg hlink combase win32u winmmbase dxva2 evr mfuuid
ksuser mmdevapi audioses devobj wer faultrep rstrtmgr srvcli netutils samcli wkscli logoncli activeds
adsldpc ntdsapi dbgeng tdh virtdisk fltlib clusapi resutils esent cryptbase cryptsp wsock32 msacm32
comsvcs msxml6 xmllite webservices bthprops.cpl wlanapi mobsync mprapi rasapi32 rasman tapi32 security
winscard dhcpcsvc dhcpcsvc6 fwpuclnt httpapi vssapi wimgapi winbrand wdsclientapi netshell icmp
""".split())
RE_API_SET = re.compile(r"^(api-ms-win-|ext-ms-)", re.I)
RE_REDIST_VC = re.compile(r"^(msvcp140(_1|_2|_atomic_wait|_codecvt_ids)?|vcruntime140(_1|_threads)?|concrt140|"
                          r"vccorlib140|vcomp140|vcamp140|mfc140\w*|mfcm140\w*|msvcp1[0-2]0|msvcr1[0-2]0|"
                          r"vcomp1[0-2]0|msvcp[6-9]0|msvcr[6-9]0|msvcr71|msvcp71)\.dll$", re.I)
# Redistribuable DirectX d'autrefois : signe Microsoft, mais PAS livre avec Windows.
RE_REDIST_DX = re.compile(r"^(d3dx9_\d+|d3dx10(_\d+)?|d3dx11_\d+|d3dcompiler_(3\d|4[0-6])|xinput1_[123]|"
                          r"xaudio2_[0-7]|x3daudio1_\d+|xapofx1_\d+)\.dll$", re.I)
# Pilotes (carte graphique, calcul) : poses dans System32 par le pilote du materiel, jamais embarquables ;
# le programme les charge a la demande et doit vivre sans eux (repli CPU).
RE_PILOTE = re.compile(r"^(nvcuda|nvcuvid|nvoptix|nvml|nvapi64|nvrtc\w*|nvencodeapi64|vulkan-1|amdhip64\w*|"
                       r"amd_comgr\w*|hiprtc\w*|ze_loader|ze_intel\w*|level_zero\w*|igc\w*|opencl)\.dll$", re.I)


# ---------------------------------------------------------------- lecture du format PE
class ErreurPE(Exception):
    pass


def signature_pe(chemin):
    """Vrai si le fichier commence par MZ et que e_lfanew pointe sur « PE\\0\\0 » (lecture de 64 + 4 octets)."""
    try:
        with open(chemin, "rb") as f:
            tete = f.read(64)
            if len(tete) < 64 or tete[:2] != b"MZ":
                return False
            e = struct.unpack_from("<I", tete, 0x3C)[0]
            if e < 64 or e > 0x10000000:
                return False
            f.seek(e)
            return f.read(4) == b"PE\0\0"
    except OSError:
        return False


class ImagePE:
    """Fichier PE projete en memoire (mmap : seules les pages lues sont chargees)."""

    def __init__(self, chemin):
        self.chemin = chemin
        self._f = open(chemin, "rb")
        try:
            if os.fstat(self._f.fileno()).st_size < 64:
                raise ErreurPE("fichier trop court")
            self.mm = mmap.mmap(self._f.fileno(), 0, access=mmap.ACCESS_READ)
        except Exception:
            self._f.close()
            raise
        try:
            self._entetes()
        except Exception:
            self.fermer()
            raise

    def fermer(self):
        try:
            self.mm.close()
        finally:
            self._f.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.fermer()
        return False

    def _entetes(self):
        mm = self.mm
        if mm[:2] != b"MZ":
            raise ErreurPE("pas un fichier MZ")
        e = struct.unpack_from("<I", mm, 0x3C)[0]
        if e + 24 > len(mm) or mm[e:e + 4] != b"PE\0\0":
            raise ErreurPE("signature PE absente")
        machine, nsections = struct.unpack_from("<HH", mm, e + 4)
        taille_opt = struct.unpack_from("<H", mm, e + 20)[0]
        o = e + 24
        if o + 2 > len(mm):
            raise ErreurPE("en-tete tronque")
        magic = struct.unpack_from("<H", mm, o)[0]
        if magic == 0x20B:
            self.pe64 = True
            self.image_base = struct.unpack_from("<Q", mm, o + 24)[0]
            n_rva = struct.unpack_from("<I", mm, o + 108)[0]
            debut = o + 112
        elif magic == 0x10B:
            self.pe64 = False
            self.image_base = struct.unpack_from("<I", mm, o + 28)[0]
            n_rva = struct.unpack_from("<I", mm, o + 92)[0]
            debut = o + 96
        else:
            raise ErreurPE("en-tete optionnel inconnu 0x%x" % magic)
        self.repertoires = []
        for i in range(min(n_rva, 16)):
            if debut + 8 * i + 8 > o + taille_opt:
                break
            self.repertoires.append(struct.unpack_from("<II", mm, debut + 8 * i))
        s = o + taille_opt
        self.sections = []
        for k in range(nsections):
            if s + 40 * k + 40 > len(mm):
                break
            _, vsize, va, rsize, rptr = struct.unpack_from("<8sIIII", mm, s + 40 * k)
            self.sections.append((va, max(vsize, rsize), rptr, rsize))
        self.machine = MACHINES.get(machine, "0x%x" % machine)

    def repertoire(self, i):
        return self.repertoires[i] if i < len(self.repertoires) else (0, 0)

    def decalage(self, rva):
        for va, taille, rptr, rsize in self.sections:
            if va <= rva < va + taille:
                d = rva - va
                if d >= rsize or rptr + d >= len(self.mm):
                    return None
                return rptr + d
        return None

    def chaine(self, rva, maxi=8192):
        # MSVC borne un nom decore a 4 096 caracteres ; pefile, lui, tronque a 512 (noms C++ d'ODA : 602).
        d = self.decalage(rva)
        if d is None:
            return None
        fin = self.mm.find(b"\0", d, min(d + maxi, len(self.mm)))
        if fin < 0:
            fin = min(d + maxi, len(self.mm))
        return self.mm[d:fin].decode("ascii", "replace")

    def _thunks(self, rva, va=False):
        """Noms importes d'une table de recherche (ILT/INT) : 'nom' ou ('#', ordinal)."""
        if not rva:
            return []
        if va:
            rva = (rva - self.image_base) & 0xFFFFFFFF
        d = self.decalage(rva)
        if d is None:
            return []
        pas, bit, fmt = (8, 1 << 63, "<Q") if self.pe64 else (4, 1 << 31, "<I")
        noms = []
        for k in range(200000):
            if d + pas * (k + 1) > len(self.mm):
                break
            v = struct.unpack_from(fmt, self.mm, d + pas * k)[0]
            if v == 0:
                break
            if v & bit:
                noms.append(("#", v & 0xFFFF))
            else:
                r = v & 0x7FFFFFFF
                if va:
                    r = (v - self.image_base) & 0xFFFFFFFF
                s = self.chaine(r + 2)
                if s:
                    noms.append(s)
        return noms

    def imports(self, avec_noms=False):
        """-> (directs, differes) ; chaque element : nom de DLL, ou (nom de DLL, [fonctions]) si avec_noms."""
        mm = self.mm
        directs, differes = [], []
        rva, _ = self.repertoire(1)
        d = self.decalage(rva) if rva else None
        if d is not None:
            for k in range(4096):
                if d + 20 * k + 20 > len(mm):
                    break
                oft, _, _, nom, ft = struct.unpack_from("<IIIII", mm, d + 20 * k)
                if not (oft or nom or ft):
                    break
                s = self.chaine(nom, 260) if nom else None
                if s:
                    directs.append((s, self._thunks(oft or ft)) if avec_noms else s)
        rva, _ = self.repertoire(13)
        d = self.decalage(rva) if rva else None
        if d is not None:
            for k in range(4096):
                if d + 32 * k + 32 > len(mm):
                    break
                desc = mm[d + 32 * k:d + 32 * k + 32]
                if not any(desc):
                    break
                attributs, nom, _, _, int_rva = struct.unpack_from("<IIIII", desc, 0)
                ancien = not (attributs & 1)                 # ancien format : adresses virtuelles
                if nom:
                    if ancien:
                        nom = (nom - self.image_base) & 0xFFFFFFFF
                    s = self.chaine(nom, 260)
                    if s:
                        differes.append((s, self._thunks(int_rva, va=ancien)) if avec_noms else s)
        return directs, differes

    def exports(self):
        """-> (ensemble des noms exportes, base des ordinaux, nombre de fonctions). TOUS les noms."""
        rva, _ = self.repertoire(0)
        d = self.decalage(rva) if rva else None
        if d is None or d + 40 > len(self.mm):
            return set(), 0, 0
        (_, _, _, _, _, base, n_fonctions, n_noms, _, rva_noms, _) = struct.unpack_from("<IIHHIIIIIII", self.mm, d)
        noms = set()
        dn = self.decalage(rva_noms) if n_noms else None
        if dn is not None:
            for i in range(n_noms):
                if dn + 4 * i + 4 > len(self.mm):
                    break
                s = self.chaine(struct.unpack_from("<I", self.mm, dn + 4 * i)[0])
                if s:
                    noms.add(s)
        return noms, base, n_fonctions


def lire_imports(chemin):
    """-> (machine, [imports directs], [imports differes]) ; noms de DLL tels qu'ecrits dans le fichier."""
    with ImagePE(chemin) as pe:
        directs, differes = pe.imports()
        return pe.machine, directs, differes


def lire_exports(chemin):
    with ImagePE(chemin) as pe:
        return pe.exports()


# ---------------------------------------------------------------- ressource de version (API Windows)
_VERSIONS = {}


def version_fichier(chemin):
    """-> (FileVersion, ProductName, CompanyName) lus par version.dll ; (None, None, None) sinon."""
    if chemin in _VERSIONS:
        return _VERSIONS[chemin]
    res = (None, None, None)
    try:
        v = ctypes.windll.version
        taille = v.GetFileVersionInfoSizeW(chemin, None)
        if taille:
            buf = ctypes.create_string_buffer(taille)
            if v.GetFileVersionInfoW(chemin, 0, taille, buf):
                ptr = ctypes.c_void_p()
                lg = ctypes.c_uint()
                # version numerique fiable (VS_FIXEDFILEINFO), independante de la langue
                num = None
                if v.VerQueryValueW(buf, "\\", ctypes.byref(ptr), ctypes.byref(lg)) and lg.value >= 52:
                    ffi = ctypes.string_at(ptr.value, 52)
                    ms, ls = struct.unpack_from("<II", ffi, 8)
                    num = "%d.%d.%d.%d" % (ms >> 16, ms & 0xFFFF, ls >> 16, ls & 0xFFFF)
                langues = []
                if v.VerQueryValueW(buf, "\\VarFileInfo\\Translation", ctypes.byref(ptr), ctypes.byref(lg)):
                    brut = ctypes.string_at(ptr.value, lg.value)
                    for i in range(0, len(brut) - 3, 4):
                        langue, cp = struct.unpack_from("<HH", brut, i)
                        langues.append("%04x%04x" % (langue, cp))
                langues += ["040904b0", "040904e4", "040c04b0", "000004b0"]
                produit = societe = None
                for lc in langues:
                    for cle in ("ProductName", "CompanyName"):
                        if v.VerQueryValueW(buf, "\\StringFileInfo\\%s\\%s" % (lc, cle),
                                            ctypes.byref(ptr), ctypes.byref(lg)) and lg.value:
                            val = ctypes.wstring_at(ptr.value, lg.value).rstrip("\0")
                            if cle == "ProductName" and produit is None:
                                produit = val
                            if cle == "CompanyName" and societe is None:
                                societe = val
                    if produit:
                        break
                res = (num, produit, societe)
    except Exception:
        pass
    _VERSIONS[chemin] = res
    return res


def est_dll_windows(chemin):
    """Vrai si le fichier est une DLL livree avec Windows : editeur (CompanyName) « Microsoft Corporation »,
    et ni redistribuable Visual C++ (ProductName « Visual Studio ») ni ancien redistribuable DirectX.
    Le nom de produit seul ne suffit pas : ze_loader.dll d'Intel s'appelle « ... for Windows(R) »."""
    nom = os.path.basename(chemin).lower()
    if RE_REDIST_VC.match(nom) or RE_REDIST_DX.match(nom) or RE_PILOTE.match(nom):
        return False
    _, produit, societe = version_fichier(chemin)
    if not societe or societe.strip().lower() != "microsoft corporation":
        return False
    p = (produit or "").lower()
    return "visual studio" not in p and "visual c++" not in p


def classer(nom_min):
    """-> 'pilote' | 'windows' | 'system32_non_windows' | 'introuvable'  (DLL hors de portee dans l'arborescence).
    'windows' : ensemble d'API, DLL du noyau connue, ou DLL de System32 dont est_dll_windows() est vrai."""
    base = nom_min[:-4] if nom_min.endswith(".dll") else nom_min
    if RE_PILOTE.match(nom_min):
        return "pilote"
    if RE_API_SET.match(nom_min) or base in WINDOWS_CONNUES or nom_min in WINDOWS_CONNUES:
        return "windows"
    p = os.path.join(SYSTEM32, nom_min)
    if os.path.isfile(p):
        return "windows" if est_dll_windows(p) else "system32_non_windows"
    return "introuvable"


# ---------------------------------------------------------------- analyse d'une arborescence
RE_TAG_CPYTHON = re.compile(r"\.cp(3\d+)-", re.I)
RE_DLL_PYTHON = re.compile(r"^python(3\d+)\.dll$", re.I)


def _dans(chemin, dossier):
    return chemin == dossier or chemin.startswith(dossier.rstrip("\\/") + os.sep)


# Modules dont une DLL manque PAR CONCEPTION : le paquet ne les charge que si l'option est demandee.
# Motif (chemin relatif, minuscules, separateurs « / ») -> explication. Ils sont listes a part.
OPTIONNELS_CONNUS = {
    r"numba/np/ufunc/tbbpool": "couche de fils TBB de numba : facultative (paquet pip « tbb » absent), "
                               "numba se rabat sur omp ou workqueue",
    # ODA 27.1 : lacunes de la livraison d'ODA elle-meme, identiques dans C:\Program Files\ODA (verifie le
    # 2026-09-25) ; modules charges a la demande seulement.
    r"acmodeldocobj_": "ODA : objets de documentation de modele (vues de dessin) ; DbConstraints_*.tx n'est pas "
                       "livre avec ODA File Converter 27.1 (meme lacune dans l'installation d'origine)",
    r"w3dtk.dll": "ODA : boite a outils DWF 3D ; DwfCore.dll n'est pas livree avec ODA File Converter 27.1 "
                  "(meme lacune dans l'installation d'origine)",
    r"whiptk.dll": "ODA : boite a outils DWF (WHIP!) ; DwfCore.dll n'est pas livree avec ODA File Converter 27.1 "
                   "(meme lacune dans l'installation d'origine)",
    r"imageformats/qsvg.dll": "greffon d'images SVG de Qt : Qt6Svg.dll n'est livree ni avec le convertisseur ni "
                              "avec la visionneuse ODA 27.1 ; Qt saute un greffon qui ne se charge pas",
    r"nwrecapimport_": "ODA : import Navisworks / ReCap ; TNW_Db_*.tx n'est pas livre avec ODA Viewer 27.1 "
                       "(meme lacune dans l'installation d'origine)",
}


def analyser(racine, toutes_archi=False, dossiers_dll=(), symboles=False, tous_fichiers=False):
    racine = os.path.normcase(os.path.abspath(racine))
    binaires, ou_est, par_signature = [], {}, []
    # dossier de DLL -> portee (les modules qui en profitent). Un <paquet>.libs ne sert qu'a SON paquet :
    # le paquet l'ajoute a son import, et avant cela un autre module ne le voit pas.
    dossiers_recherche = {racine: [racine]}
    for d in dossiers_dll:
        dossiers_recherche[os.path.normcase(os.path.abspath(os.path.join(racine, d)))] = [racine]
    versions_python = set()
    for d, sous, fichiers in os.walk(racine):
        dn = os.path.normcase(d)
        base = os.path.basename(dn)
        parent = os.path.dirname(dn)
        noms_min = {f.lower() for f in fichiers}
        if base == ".libs":                                     # sklearn\.libs -> sklearn
            dossiers_recherche[dn] = [parent]
        elif base.endswith(".libs"):                            # numpy.libs -> numpy et numpy.libs
            dossiers_recherche[dn] = [os.path.join(parent, base[:-5]), dn]
        elif base == "pywin32_system32" or (base + ".manifest") in noms_min:
            dossiers_recherche[dn] = [parent]                   # ajoute au demarrage (.pth), assemblage prive
        elif "__init__.py" in noms_min and any(fl.endswith(EXTENSIONS) for fl in noms_min):
            # paquet qui ajoute lui-meme son dossier a la recherche des DLL (ex. pygame)
            try:
                with open(os.path.join(d, "__init__.py"), "rb") as fo:
                    if b"add_dll_directory" in fo.read(200_000):
                        dossiers_recherche[dn] = [dn]
            except OSError:
                pass
        metadonnees = base.endswith((".dist-info", ".egg-info")) or base == "__pycache__"
        for f in fichiers:
            fl = f.lower()
            ou_est.setdefault(fl, set()).add(dn)
            m = RE_DLL_PYTHON.match(fl)
            if m:
                versions_python.add(m.group(1))
            if fl.endswith(EXTENSIONS):
                binaires.append(os.path.join(d, f))
            elif tous_fichiers or not (metadonnees or os.path.splitext(fl)[1] in SANS_SIGNATURE):
                p = os.path.join(d, f)
                if signature_pe(p):
                    binaires.append(p)
                    par_signature.append(os.path.relpath(p, racine))
    resultat = {"racine": racine, "binaires": len(binaires), "par_signature": sorted(par_signature),
                "illisibles": [], "autres_archi": {},
                "autres_versions_python": [], "dossiers_recherche": sorted(dossiers_recherche),
                "portees": {k: v for k, v in sorted(dossiers_recherche.items())},
                "fichiers": {}, "manquantes": {}, "manquantes_differees": {}, "optionnelles": {},
                "pilotes": {}}
    if symboles:
        resultat["symboles_manquants"] = {}
        resultat["symboles_verifies"] = 0
    cache_classe, cache_exports = {}, {}

    def exports_de(chemin):
        if chemin not in cache_exports:
            try:
                cache_exports[chemin] = lire_exports(chemin)
            except (ErreurPE, struct.error, OSError, ValueError):
                cache_exports[chemin] = None
        return cache_exports[chemin]

    for chemin in sorted(binaires):
        rel = os.path.relpath(chemin, racine)
        tag = RE_TAG_CPYTHON.search(os.path.basename(chemin))
        if tag and versions_python and tag.group(1) not in versions_python and chemin.lower().endswith(".pyd"):
            resultat["autres_versions_python"].append(rel)
            continue
        try:
            with ImagePE(chemin) as pe:
                machine = pe.machine
                directs, differes = pe.imports(avec_noms=True)
        except (ErreurPE, struct.error, OSError, ValueError) as e:
            resultat["illisibles"].append([rel, str(e)])
            continue
        if machine != "x64" and not toutes_archi:
            resultat["autres_archi"].setdefault(machine, []).append(rel)
            continue
        dossier = os.path.normcase(os.path.dirname(chemin))
        rel_min = rel.lower().replace("\\", "/")
        optionnel = next((v for k, v in OPTIONNELS_CONNUS.items() if k in rel_min), None)
        for liste, suffixe in ((directs, ""), (differes, "_differees")):
            for nom, fonctions in liste:
                n = nom.lower()
                dossiers = ou_est.get(n)
                retenu = None
                if dossiers:
                    if dossier in dossiers:
                        retenu = dossier
                    elif racine in dossiers:
                        retenu = racine
                    else:
                        retenu = next((x for x in sorted(dossiers) if any(
                            _dans(dossier, portee) for portee in dossiers_recherche.get(x, ()))), None)
                if retenu is not None:                         # trouvee
                    if symboles and fonctions:
                        cible = os.path.join(retenu, n)
                        ex = exports_de(cible)
                        if ex is not None:
                            noms_ex, base_ord, n_fonc = ex
                            absents = [("#%d" % f[1]) if isinstance(f, tuple) else f for f in fonctions
                                       if (isinstance(f, tuple) and not (base_ord <= f[1] < base_ord + n_fonc))
                                       or (not isinstance(f, tuple) and f not in noms_ex)]
                            resultat["symboles_verifies"] += len(fonctions)
                            if absents:
                                resultat["symboles_manquants"].setdefault(rel, {})[n] = {
                                    "cible": os.path.relpath(cible, racine), "differe": bool(suffixe),
                                    "nombre": len(absents), "exemples": absents[:12]}
                    continue
                if n not in cache_classe:
                    cache_classe[n] = classer(n)
                if cache_classe[n] == "windows":
                    continue
                if cache_classe[n] == "pilote":
                    cle = "pilotes"
                elif optionnel:
                    cle = "optionnelles"
                else:
                    cle = "manquantes" + suffixe
                m = resultat[cle].setdefault(n, {"importeurs": [], "etat": cache_classe[n]})
                if dossiers:   # presente dans l'arborescence, mais hors de portee du chargeur
                    m["presente_dans"] = sorted(os.path.relpath(x, racine) for x in dossiers)
                if optionnel:
                    m["pourquoi"] = optionnel
                m["importeurs"].append(rel)
                resultat["fichiers"].setdefault(rel, {"machine": machine})\
                    .setdefault(cle, []).append(nom)
    for cle in ("manquantes", "manquantes_differees", "optionnelles", "pilotes"):
        for n, m in resultat[cle].items():
            m["redistribuable_vc"] = bool(RE_REDIST_VC.match(n))
            p = os.path.join(SYSTEM32, n)
            if os.path.isfile(p):
                ver, produit, societe = version_fichier(p)
                m["system32"] = {"chemin": p, "version": ver, "produit": produit, "societe": societe}
    return resultat


def copier_vc(resultat, dest):
    copies = []
    os.makedirs(dest, exist_ok=True)
    vus = set()
    for cle in ("manquantes", "manquantes_differees"):
        for n, m in sorted(resultat[cle].items()):
            if n in vus or not m.get("redistribuable_vc") or "system32" not in m:
                continue
            vus.add(n)
            cible = os.path.join(dest, n)
            if os.path.exists(cible):
                copies.append((n, "deja present, non ecrase", version_fichier(cible)[0]))
                continue
            shutil.copy2(m["system32"]["chemin"], cible)
            copies.append((n, "copie", m["system32"]["version"]))
    return copies


def rapport_texte(r):
    print("Arborescence : %s" % r["racine"])
    print("Binaires PE : %d, dont %d reconnus par leur signature seule%s ; illisibles : %d"
          % (r["binaires"], len(r["par_signature"]),
             (" (ex. " + ", ".join(r["par_signature"][:3]) + ")") if r["par_signature"] else "",
             len(r["illisibles"])))
    for rel, e in r["illisibles"]:
        print("    illisible : %s (%s)" % (rel, e))
    for machine, l in sorted(r["autres_archi"].items()):
        print("Autre architecture, ignores (%s) : %d, ex. %s" % (machine, len(l), ", ".join(l[:3])))
    if r["autres_versions_python"]:
        l = r["autres_versions_python"]
        print("Autre version de CPython, ignores : %d, ex. %s" % (len(l), ", ".join(l[:2])))
    extra = [os.path.relpath(d, r["racine"]) for d in r["dossiers_recherche"] if d != r["racine"]]
    print("Dossiers de DLL reconnus (en plus de la racine et du dossier de chaque module) : %d%s"
          % (len(extra), (" : " + ", ".join(extra[:12]) + (" ..." if len(extra) > 12 else "")) if extra else ""))
    for cle, titre in (("manquantes", "DLL MANQUANTES (imports directs)"),
                       ("manquantes_differees", "DLL manquantes en import differe (delay-load)"),
                       ("optionnelles", "DLL absentes par conception (modules facultatifs connus)"),
                       ("pilotes", "Pilotes : non embarquables, charges a la demande (repli sans eux)")):
        print("\n== %s : %d" % (titre, len(r[cle])))
        for n, m in sorted(r[cle].items()):
            s32 = m.get("system32")
            if s32:
                ou = "System32 %s, %s%s" % (s32["version"], s32["produit"],
                                            " [redistribuable Visual C++]" if m["redistribuable_vc"] else "")
            else:
                ou = "absente de System32"
            print("   %-34s %s" % (n, ou))
            if m.get("presente_dans"):
                print("        AILLEURS dans l'arborescence, hors de portee du chargeur : %s"
                      % ", ".join(m["presente_dans"][:4]))
            if m.get("pourquoi"):
                print("        %s" % m["pourquoi"])
            for imp in m["importeurs"][:8]:
                print("        <- %s" % imp)
            if len(m["importeurs"]) > 8:
                print("        ... et %d autre(s)" % (len(m["importeurs"]) - 8))
    if "symboles_manquants" in r:
        sm = r["symboles_manquants"]
        print("\n== Fonctions importees introuvables dans la DLL retenue (--symboles) : %d importeur(s), "
              "%d fonctions verifiees" % (len(sm), r["symboles_verifies"]))
        for imp, par_dll in sorted(sm.items()):
            for n, x in sorted(par_dll.items()):
                print("   %s -> %s%s : %d absente(s), ex. %s" % (imp, x["cible"], " (differe)" if x["differe"] else "",
                                                             x["nombre"], ", ".join(x["exemples"][:4])))


def main(argv):
    try:
        sys.stdout.reconfigure(errors="replace")   # console cp850/cp1252 : jamais de plantage sur « ® »
    except Exception:
        pass
    if not argv or argv[0].startswith("-"):
        print(__doc__)
        return 2
    racine = argv[0]
    if not os.path.isdir(racine):
        print("Dossier introuvable : %s" % racine, file=sys.stderr)
        return 2
    if struct.calcsize("P") != 8:
        print("Attention : Python 32 bits, System32 est redirige vers SysWOW64.", file=sys.stderr)
    dossiers_dll = [argv[i + 1] for i, a in enumerate(argv[:-1]) if a == "--dossier-dll"]
    r = analyser(racine, toutes_archi="--toutes-archi" in argv, dossiers_dll=dossiers_dll,
                 symboles="--symboles" in argv, tous_fichiers="--tous-fichiers" in argv)
    if "--copier-vc" in argv:
        i = argv.index("--copier-vc")
        if i + 1 >= len(argv):
            print("--copier-vc exige un dossier", file=sys.stderr)
            return 2
        r["copies_vc"] = copier_vc(r, argv[i + 1])
    if "--json" in argv:
        json.dump(r, sys.stdout, ensure_ascii=False, indent=1, sort_keys=True, default=list)
        print()
    else:
        rapport_texte(r)
        for n, etat, ver in r.get("copies_vc", []):
            print("copie VC++ : %-28s %-26s %s" % (n, etat, ver))
    return 1 if (r["manquantes"] or r.get("symboles_manquants")) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
