import sys
import outils_releve as O
vue = getattr(O, sys.argv[1].upper())
u0, v0, u1, v1 = (float(a) for a in sys.argv[2:6])
dpi = int(sys.argv[6]) if len(sys.argv) > 6 else 300
nom = sys.argv[7] if len(sys.argv) > 7 else None
pas = float(sys.argv[8]) if len(sys.argv) > 8 else 1.0
print(vue.zoom(u0, v0, u1, v1, dpi=dpi, nom=nom, pas=pas))
