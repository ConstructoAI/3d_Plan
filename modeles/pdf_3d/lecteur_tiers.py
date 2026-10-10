# -*- coding: utf-8 -*-
r"""lecteur_tiers.py — fait lire un U3D par un lecteur TIERS (Aspose.CAD), et en tire une image.

    & $env:BM_PYTHON -X utf8 -s modeles\pdf_3d\lecteur_tiers.py x.u3d|x.pdf [...] [--sortie dossier]

Pourquoi : nos contrôles relisent le fichier avec NOTRE lecteur (lire_u3d.py). Un lecteur écrit par
d'autres dit autre chose : s'il charge le fichier et que l'image montre la bonne silhouette, le
codage est juste aux yeux de quelqu'un d'autre que nous. Le paquet « aspose-cad » du Python du
poste lit le U3D ; sans licence il estampille l'image (« Evaluation only ») et ne rend qu'une
silhouette noire, vue de dessus : cela suffit pour reconnaître une forme.

Ce qu'il a appris le 2026-10-09 : il lit les U3D COMPRESSÉS (l'échantillon public dice.u3d, les
nôtres) et REFUSE tout U3D non compressé (profil 0x04) — celui de l'écrivain de l'ERP comme le
nôtre avec « --compat compresse=0 » : « The given key … was not present in the dictionary ».

Pour un PDF, le U3D en est d'abord extrait (dans le dossier de sortie). Ce n'est PAS un lecteur de
PDF : il ne dit rien des vues, de l'arbre ni de l'affichage dans Acrobat ou PDF-XChange.
Codes : 0 tout chargé ; 1 un fichier au moins refusé ; 3 aspose-cad absent.
"""
import os
import sys
import tempfile
import time

sys.dont_write_bytecode = True
ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    sortie = None
    if "--sortie" in argv:
        sortie = argv[argv.index("--sortie") + 1]
        args = [a for a in args if a != sortie]
    if not args:
        print(__doc__)
        return 2
    try:
        t0 = time.time()
        import aspose.cad as cad
    except ImportError:
        print("LECTEUR TIERS ABSENT : le paquet aspose-cad n'est pas dans ce Python (rien à installer : essai sauté).")
        return 3
    print("aspose.cad %s chargé en %.1f s" % (getattr(cad, "VERSION", "?"), time.time() - t0))
    sortie = os.path.abspath(sortie) if sortie else tempfile.mkdtemp(prefix="lecteur_tiers_")
    os.makedirs(sortie, exist_ok=True)
    refus = 0
    for chemin in args:
        base = os.path.splitext(os.path.basename(chemin))[0]
        u3d = chemin
        if chemin.lower().endswith(".pdf"):
            import lire_u3d
            u3d = os.path.join(sortie, base + ".u3d")
            with open(u3d, "wb") as f:
                f.write(lire_u3d.extraire_du_pdf(chemin))
        with open(u3d, "rb") as f:
            tete = f.read(32)
        profil = int.from_bytes(tete[16:20], "little") if len(tete) >= 20 else -1
        print("== %s : %d octets, profil 0x%X (%s)" % (os.path.basename(u3d), os.path.getsize(u3d), profil,
                                                      "SANS compression" if profil & 4 else "compressé"))
        try:
            t0 = time.time()
            img = cad.Image.load(u3d)
            t1 = time.time()
            ro = cad.imageoptions.CadRasterizationOptions()
            ro.page_width = 1200.0
            ro.page_height = 900.0
            po = cad.imageoptions.PngOptions()
            po.vector_rasterization_options = ro
            png = os.path.join(sortie, base + ".tiers.png")
            img.save(png, po)
            print("   CHARGÉ en %.1f s ; image en %.1f s : %s" % (t1 - t0, time.time() - t1, png))
        except Exception as e:
            refus += 1
            print("   REFUSÉ : %s" % str(e).splitlines()[0][:220])
    print("LECTEUR_TIERS : %d fichier(s), %d refusé(s)" % (len(args), refus))
    return 1 if refus else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
