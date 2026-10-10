"""Prix budgétaire cost-plus selon le profil ENTREPRENEUR_GENERAL_QC (UN SEUL total, calcul affiché).

MODÈLE tiré de Maison_Bungalow_Blender\\estimation\\prix_budgetaire.py (version finale du 2026-09-25 ; voir
modeles\\LISEZMOI.md). L'exemple intégré est l'exemple FICTIF de entrees_exemple.json (provision en total).
Copie ADAPTÉE pour la Maison Bungalow (2026-09-25) du calculateur de référence du projet Agrandissement :
arrondis par la méthode des LIGNES AFFICHÉES (consigne du chef) : chaque ligne est arrondie au cent, le prix avant taxes
est la SOMME des lignes affichées (B'' + administration + contingences + profit), la TPS et la TVQ sont arrondies sur ce
prix, et le TTC en est la somme. (r(B'' x 1,30) peut différer de 1 cent de cette somme : ce n'est PAS la méthode retenue.)
Le profil est à la racine du poste (ENTREPRENEUR_GENERAL_QC_profil.txt) ; son outil calculer_prix_construction n'est
pas branché sur ce poste, d'où ce script. Arithmétique en Decimal, arrondi au cent (demi vers le haut).

Usage :
  python prix_budgetaire.py entrees_exemple.json    exemple fictif (contrôle intégré, provision comprise)
  python prix_budgetaire.py                         le même exemple, intégré ci-dessous (EXEMPLE)
  python prix_budgetaire.py projet.json      entrées d'un autre projet (même structure que EXEMPLE)
  python prix_budgetaire.py projet.json --json   résultat en JSON (pour un PDF ou un devis)

Règles du profil appliquées (à relire dans le profil avant usage) :
  - gamme Économique par défaut ; aires BRUTES par étage, annoncées ; garage JAMAIS exclu
    (chauffé = tarif habitable ; froid ≈ 60 % de l'habitable) ;
  - poids par étage (neuf) : RDC 100 %, étage intermédiaire 80 %, dernier étage 85 % ;
  - toit plat en résidentiel (portion minoritaire ou agrandissement accolé à une maison en pente) :
    +15 % du tarif de base de TOITURE de la gamme, sur la portion plate seulement (Règle 3) ;
  - facteurs région, saison, complexité : seulement s'ils sont fondés sur le plan ou sur le client, sinon 1,00 ;
  - démolition confirmée : section Rénovation (démolition + nettoyage et disposition), sans facteur de forme ;
  - provisions (entrée « provisions » : {nom, note, postes [{nom, montant}]}) : forfaits AU COÛT, hors facteurs de région,
    de saison et de complexité, ajoutés au coût de base B'' AVANT les frais (ex. services d'un terrain sans réseaux
    municipaux) ; une ligne à part dans la ventilation ;
  - frais : administration, contingences, profit 15 % FIXE sur le coût de base ; taxes sur le sous-total HT.
"""
from __future__ import annotations

import json
import sys
from decimal import ROUND_HALF_UP, Decimal as D

# Coûts de base $/pi² (Section 6 du profil) et taux de corps de métier (Sections 1 et 2)
TARIFS = {
    "residentiel_neuf": {"economique": 192, "de_base": 228, "moyenne": 268, "haut_de_gamme": 335},
    "renovation_residentielle": {"economique": 178, "de_base": 230, "moyenne": 301, "haut_de_gamme": 405},
    "commercial_neuf": {"economique": 263, "de_base": 335, "moyenne": 426, "haut_de_gamme": 550},
    "commercial_renovation": {"economique": 219, "de_base": 290, "moyenne": 377, "haut_de_gamme": 495},
    "institutionnel": {"economique": 379, "de_base": 471, "moyenne": 589, "haut_de_gamme": 748},
}
FRAIS = {  # administration, contingences, profit (fixe)
    "residentiel_neuf": ("0.03", "0.12", "0.15"),
    "renovation_residentielle": ("0.03", "0.15", "0.15"),
    "commercial_neuf": ("0.03", "0.10", "0.15"),
    "commercial_renovation": ("0.04", "0.15", "0.15"),
    "institutionnel": ("0.05", "0.10", "0.15"),
}
TOITURE_NEUF = {"economique": 11, "de_base": 13, "moyenne": 14, "haut_de_gamme": 17}
CORPS_NEUF = {  # Section 1, $/pi² par gamme (somme = tarif de base)
    "economique": [("Excavation et préparation", 15), ("Fondation et dalle", 26), ("Charpente/Structure", 19),
                   ("Toiture", 11), ("Revêtement extérieur", 12), ("Portes et fenêtres", 11), ("Plomberie", 17),
                   ("Électricité", 15), ("Ventilation/HVAC", 9), ("Isolation, cloisons et gypse", 28),
                   ("Finition intérieure", 16), ("Aménagement extérieur", 13)],
    "de_base": [("Excavation et préparation", 17), ("Fondation et dalle", 30), ("Charpente/Structure", 22),
                ("Toiture", 13), ("Revêtement extérieur", 15), ("Portes et fenêtres", 14), ("Plomberie", 20),
                ("Électricité", 18), ("Ventilation/HVAC", 11), ("Isolation, cloisons et gypse", 32),
                ("Finition intérieure", 22), ("Aménagement extérieur", 14)],
    "moyenne": [("Excavation et préparation", 18), ("Fondation et dalle", 33), ("Charpente/Structure", 25),
                ("Toiture", 14), ("Revêtement extérieur", 18), ("Portes et fenêtres", 18), ("Plomberie", 23),
                ("Électricité", 22), ("Ventilation/HVAC", 14), ("Isolation, cloisons et gypse", 36),
                ("Finition intérieure", 32), ("Aménagement extérieur", 15)],
    "haut_de_gamme": [("Excavation et préparation", 20), ("Fondation et dalle", 40), ("Charpente/Structure", 32),
                      ("Toiture", 17), ("Revêtement extérieur", 25), ("Portes et fenêtres", 28), ("Plomberie", 30),
                      ("Électricité", 28), ("Ventilation/HVAC", 18), ("Isolation, cloisons et gypse", 42),
                      ("Finition intérieure", 38), ("Aménagement extérieur", 17)],
}
DEMOLITION = {  # Section 2 (rénovation) : démolition/déconstruction, nettoyage et disposition, $/pi²
    "economique": (18, 9), "de_base": (22, 12), "moyenne": (25, 15), "haut_de_gamme": (30, 16),
}
TAXES = (D("0.05"), D("0.09975"))

EXEMPLE = {  # exemple FICTIF (aires rondes) : le même que entrees_exemple.json, provision en total
    "projet": "EXEMPLE FICTIF — maison neuve (zone C), sous-sol fini et garage attaché chauffé",
    "categorie": "residentiel_neuf",
    "gamme": "economique",
    "etages": [  # aire brute (pi²), poids (1,00 RDC ; 0,80 intermédiaire ; 0,85 dernier)
        {"nom": "Rez-de-chaussée de la maison (aire brute)", "aire": "1200", "poids": "1.00"},
        {"nom": "Garage attaché CHAUFFÉ, tarif habitable", "aire": "300", "poids": "1.00"},
        {"nom": "Sous-sol FINI, compté comme habitable", "aire": "1200", "poids": "1.00"},
    ],
    "garage_froid_pi2": "0",          # garage non chauffé (à ~60 % de l'habitable) ; un garage chauffé va dans « etages »
    "toit_plat_pi2": "0",             # portion plate (Règle 3)
    "facteurs": [  # multiplicateurs du coût de base, avec leur justification
        {"nom": "Région : exemple à 0,95, à vérifier sur Québec.ca", "valeur": "0.95"},
        {"nom": "Saison : 1,00, à confirmer", "valeur": "1.00"},
        {"nom": "Complexité : plusieurs décrochés (+10 %)", "valeur": "1.10"},
    ],
    "demolition_pi2": "0",            # confirmée par le client ; 0 sinon
    "provisions": {"nom": "Provision : services du terrain (sans réseaux municipaux)",
                   "note": "provision au coût, hors facteurs ; TOTAL seulement (le détail reste interne)",
                   "postes": [{"nom": "Services du terrain (total de la provision)", "montant": "30000.00"}]},
    "controle_ttc": "854547.55",
}


def r(x: D) -> D:
    return x.quantize(D("0.01"), rounding=ROUND_HALF_UP)


def calculer(e: dict) -> dict:
    cat, g = e["categorie"], e["gamme"]
    tarif = D(TARIFS[cat][g])
    lignes, base = [], D(0)
    for et in e["etages"]:
        m = D(et["aire"]) * tarif * D(et["poids"])
        lignes.append((f'{et["nom"]} : {et["aire"]} pi² × {tarif} $/pi² × {et["poids"]}', m))
        base += m
    if D(e.get("garage_froid_pi2", "0")):
        gf = D(e["garage_froid_pi2"]) * tarif * D("0.60")
        lignes.append((f'Garage froid : {e["garage_froid_pi2"]} pi² × {tarif} × 0,60', gf))
        base += gf
    if D(e.get("toit_plat_pi2", "0")) and cat.startswith("residentiel"):
        tp = D(e["toit_plat_pi2"]) * D(TOITURE_NEUF[g]) * D("0.15")
        lignes.append((f'Toit plat (Règle 3) : {e["toit_plat_pi2"]} pi² × {TOITURE_NEUF[g]} $/pi² × 15 %', tp))
        base += tp
    fact = D(1)
    for f in e.get("facteurs", []):
        fact *= D(f["valeur"])
    base_aj = base * fact
    demo_lignes, demo = [], D(0)
    if D(e.get("demolition_pi2", "0")):
        td, tn = DEMOLITION[g]
        a = D(e["demolition_pi2"])
        demo_lignes = [(f"Démolition et déconstruction : {a} pi² × {td} $/pi²", a * td),
                       (f"Nettoyage et disposition : {a} pi² × {tn} $/pi²", a * tn)]
        demo = sum(v for _, v in demo_lignes)
    pv = e.get("provisions") or {}
    prov_lignes = [(x["nom"], r(D(x["montant"]))) for x in pv.get("postes", [])]
    prov = sum((v for _, v in prov_lignes), D(0))
    Bpp = r(base_aj + demo + prov)                # arrondir B'' AU CENT avant les frais (SAVOIR_METRE § 4.7)
    fa, fc, fp = (D(x) for x in FRAIS[cat])
    adm, cont, prof = r(Bpp * fa), r(Bpp * fc), r(Bpp * fp)
    ht = Bpp + adm + cont + prof                  # méthode des LIGNES AFFICHÉES (somme des lignes arrondies)
    assert abs(ht - r(Bpp * (1 + fa + fc + fp))) <= D("0.01"), "HT incohérent"
    tps, tvq = r(ht * TAXES[0]), r(ht * TAXES[1])
    ttc = ht + tps + tvq
    # Ventilation du coût de base par corps de métier (règle DEVIS), somme = B'' au cent
    vent = []
    if cat == "residentiel_neuf":
        pond = sum(D(et["aire"]) * D(et["poids"]) for et in e["etages"])
        for nom, taux in CORPS_NEUF[g]:
            m = D(taux) * pond * fact
            if nom == "Toiture" and D(e.get("toit_plat_pi2", "0")):
                m += D(e["toit_plat_pi2"]) * D(TOITURE_NEUF[g]) * D("0.15") * fact
            vent.append([nom, r(m)])
        if D(e.get("garage_froid_pi2", "0")):
            vent.append(["Garage froid", r(D(e["garage_froid_pi2"]) * tarif * D("0.60") * fact)])
        vent += [[n.split(" :")[0], r(v)] for n, v in demo_lignes]
        if prov:
            vent.append([pv.get("nom", "Provisions"), prov])
        residu = Bpp - sum(v for _, v in vent)
        if residu:
            i = max(range(len(vent)), key=lambda k: vent[k][1])
            vent[i][1] += residu
    return {"lignes": lignes, "base": r(base), "facteur": fact, "base_ajustee": r(base_aj), "demolition": demo_lignes,
            "provisions": prov_lignes, "provision": prov, "provision_nom": pv.get("nom", "Provisions"),
            "Bpp": Bpp, "admin": adm, "contingences": cont, "profit": prof, "ht": ht, "tps": tps, "tvq": tvq,
            "ttc": ttc, "ventilation": vent, "frais": FRAIS[cat]}


def afficher(e: dict, s: dict) -> None:
    f = lambda v: f"{v:,.2f} $".replace(",", " ").replace(".", ",")
    print(f"**{e['projet']}** — {e['categorie']}, gamme {e['gamme']}\n")
    print("| Poste | Montant |\n|---|---:|")
    for n, v in s["lignes"]:
        print(f"| {n} | {f(r(v))} |")
    print(f"| **Coût de base B** | **{f(s['base'])}** |")
    for fa in e.get("facteurs", []):
        print(f"| Facteur — {fa['nom']} | × {fa['valeur']} |")
    print(f"| **Coût de base ajusté B'** | **{f(s['base_ajustee'])}** |")
    for n, v in s["demolition"]:
        print(f"| {n} | {f(r(v))} |")
    if s["provisions"]:
        print(f"| {s['provision_nom']} (au coût, hors facteurs) | {f(s['provision'])} |")
        for n, v in s["provisions"]:
            print(f"|   dont {n} | {f(v)} |")
    a, c, p = s["frais"]
    print(f"| **Coût de base B''** | **{f(s['Bpp'])}** |")
    print(f"| + Administration {D(a)*100:.0f} % | {f(s['admin'])} |\n| + Contingences {D(c)*100:.0f} % | {f(s['contingences'])} |")
    print(f"| + Profit {D(p)*100:.0f} % (marge fixe) | {f(s['profit'])} |\n| **Sous-total HT** | **{f(s['ht'])}** |")
    print(f"| + TPS 5 % | {f(s['tps'])} |\n| + TVQ 9,975 % | {f(s['tvq'])} |\n| **PRIX TOTAL TTC** | **{f(s['ttc'])}** |")
    if s["ventilation"]:
        print("\nVentilation du coût de base (somme = B'') :")
        for n, v in s["ventilation"]:
            print(f"  - {n} : {f(v)}")
        print(f"  = {f(sum(v for _, v in s['ventilation']))}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    entree = json.loads(open(args[0], encoding="utf-8").read()) if args else EXEMPLE
    res = calculer(entree)
    if "--json" in sys.argv:
        print(json.dumps({k: (str(v) if isinstance(v, D) else v) for k, v in res.items()
                          if k not in ("lignes", "demolition", "ventilation", "provisions")}, ensure_ascii=False,
                         indent=2))
    else:
        afficher(entree, res)
    if entree.get("controle_ttc"):
        ok = res["ttc"] == D(entree["controle_ttc"])
        print(f"\nContrôle : {res['ttc']} contre {entree['controle_ttc']} attendu : {'OK' if ok else 'ÉCART'}")
        sys.exit(0 if ok else 1)
