"""Extraire les cadres d'ouvertures (quadrilatères) des 4 élévations proposées, en pieds du repère commun.

Usage : python cadres_elevations.py [VUE] [largeur_min]
Affiche chaque quadrilatère d'épaisseur >= largeur_min (défaut 0.8) et de taille > 1 pi,
avec les quadrilatères intérieurs (châssis, croisillons) qu'il contient.
"""
import sys

import outils_releve as O

ZONES = {  # zone utile de chaque vue (u0, v0, u1, v1) en pieds
    "sud": (-14, -1, 60, 33),
    "est": (-3, -1, 52, 33),
    "ouest": (-3, -1, 52, 33),
    "nord": (-12, -1, 60, 33),
}


def quads(vue, zone):
    out = []
    for s in O.traces(vue.page):
        if s[0] not in ("qu", "re"):
            continue
        ua, va = vue.uv(s[1], s[2])
        ub, vb = vue.uv(s[3], s[4])
        u0, u1 = sorted((ua, ub))
        v0, v1 = sorted((va, vb))
        if zone[0] <= u0 and u1 <= zone[2] and zone[1] <= v0 and v1 <= zone[3]:
            out.append((u0, v0, u1, v1, s[5], s[7]))
    return out


def main():
    noms = [sys.argv[1]] if len(sys.argv) > 1 else list(ZONES)
    wmin = float(sys.argv[2]) if len(sys.argv) > 2 else 0.8
    for nom in noms:
        vue = getattr(O, nom.upper())
        Q = quads(vue, ZONES[nom])
        cadres = [q for q in Q if q[4] >= wmin and (q[2] - q[0]) > 1.0 and (q[3] - q[1]) > 1.0]
        cadres.sort(key=lambda q: (q[0], q[1]))
        print(f"=== {nom} : {len(cadres)} cadres (w >= {wmin})")
        for c in cadres:
            u0, v0, u1, v1, w, f = c
            dedans = [q for q in Q if q is not c and q[0] >= u0 - 0.01 and q[2] <= u1 + 0.01
                      and q[1] >= v0 - 0.01 and q[3] <= v1 + 0.01]
            mont_v = sum(1 for q in dedans if (q[2] - q[0]) < 0.06 and (q[3] - q[1]) > 0.5)
            mont_h = sum(1 for q in dedans if (q[3] - q[1]) < 0.06 and (q[2] - q[0]) > 0.5)
            print(f"  {vue.nom_u} {u0:7.3f}..{u1:7.3f} ({O.pi_po(u1 - u0)})  Z {v0:7.3f}..{v1:7.3f} "
                  f"({O.pi_po(v1 - v0)})  w={w} ; dedans {len(dedans)} (croisillons V {mont_v}, H {mont_h})")


if __name__ == "__main__":
    main()
