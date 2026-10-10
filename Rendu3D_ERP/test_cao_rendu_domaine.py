# -*- coding: utf-8 -*-
"""L'INVITE DE RENDU PHOTOREALISTE, par DOMAINE.

POURQUOI CE FICHIER EXISTE (2026-08-13). Sylvain a envoye une capture de la modale « Rendu
photorealiste (IA) » : la vue captee etait son SKID DE BRULEUR, et le champ de details proposait
en exemple « revetement de brique rouge, toiture en bardeaux gris, ciel de fin de journee,
amenagement paysager avec arbres, voiture dans l'entree ». Sa demande : garder Architecture, et
ajouter Mecanique.

La cause etait cote SERVEUR, pas dans l'exemple : la modale n'envoyait aucun domaine, donc le
serveur retombait sur `exterior`, dont l'invite EXIGE « murs de brique ou stucco, toiture en
bardeaux, ciel degage, entree de garage et amenagement paysager ». Le modele etait donc pousse a
inventer un batiment autour d'une machine.

Aucun banc ne couvrait `build_render_prompt`. Celui-ci verrouille ce qui compte : que chaque
domaine demande SES materiaux, qu'aucun ne demande ceux d'un autre, et que l'architecture — le
defaut historique — soit INCHANGEE.
"""
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ERP_REACT", "backend"))
gi = pytest.importorskip("routers.gemini_image")


DOMAINES = ("exterior", "interior", "object", "mechanical")


def test_chaque_domaine_rend_une_invite_DIFFERENTE():
    """Anti-tautologie de tout le fichier : si deux domaines rendaient le meme texte, les tests
    ci-dessous passeraient sans rien prouver."""
    textes = {d: gi.build_render_prompt("", d) for d in DOMAINES}
    assert len(set(textes.values())) == len(DOMAINES), sorted(textes)


def test_le_domaine_MECANIQUE_ne_demande_AUCUN_contexte_de_batiment():
    """Le coeur du defaut : c'est le vocabulaire d'architecture qui faisait inventer un batiment
    autour d'une machine. Il ne doit plus apparaitre du tout."""
    p = gi.build_render_prompt("", "mechanical").lower()
    # ⚠️ ON NE TESTE QUE LA MOITIE POSITIVE. Ma premiere version interdisait ces mots PARTOUT et
    # rougissait sur « do NOT add buildings, landscaping, sky or vegetation » — c'est-a-dire sur
    # la clause qui fait exactement ce qu'on demande. Un mot dans un REFUS n'est pas une
    # exigence : chercher la chaine sans regarder ce qui la porte accuse la bonne phrase.
    demande = p.split("do not add")[0]
    for interdit in ("landscaping", "shingle", "stucco", "driveway", "real-estate",
                     "roofline", "clear sky"):
        assert interdit not in demande, interdit
    # ... et il les REFUSE explicitement, ce qui vaut mieux que de simplement se taire
    assert "do not add buildings" in p, p[-260:]
    assert "landscaping" in p.split("do not add", 1)[1], "le refus doit NOMMER ce qu'il exclut"


def test_le_domaine_MECANIQUE_demande_SES_materiaux():
    """⚠️ CHAQUE EXPRESSION EST CHOISIE POUR N'APPARAITRE QU'UNE FOIS. Ma premiere version
    cherchait « steel » — satisfait par « stainless steel piping » — si bien que degrader
    « painted steel » en « painted surfaces » passait le banc. Un mot present ailleurs dans le
    texte n'atteste pas la clause qu'on croit tester."""
    p = gi.build_render_prompt("", "mechanical").lower()
    assert "industrial equipment" in p        # present, mais cite deux fois a dessein
    # Les MATERIAUX, eux, sont uniques : c'est ce qui rend l'assertion probante.
    for attendu in ("painted steel", "galvanized", "weld seams",
                    "cast-iron valve", "flange hardware", "concrete floor"):
        assert attendu in p, attendu
        assert p.count(attendu) == 1, (attendu, p.count(attendu))


def test_l_ARCHITECTURE_est_INCHANGEE():
    """`exterior` est le defaut historique. Ce lot ne doit RIEN y changer — c'est la demande
    explicite de Sylvain (« Architecture comme maintenant mais avoir aussi Mecanique »)."""
    p = gi.build_render_prompt("", "exterior").lower()
    for attendu in ("architectural exterior", "shingled", "landscaping"):
        assert attendu in p, attendu
    assert "industrial equipment" not in p


def test_un_domaine_INCONNU_retombe_sur_l_architecture():
    """Fail-safe : un client perime, ou une valeur fantaisiste, ne doit pas casser le rendu."""
    assert gi.build_render_prompt("", "poterie") == gi.build_render_prompt("", "exterior")
    assert gi.build_render_prompt("", "") == gi.build_render_prompt("", "exterior")


@pytest.mark.parametrize("domaine", DOMAINES)
def test_les_details_du_client_sont_joints_a_TOUS_les_domaines(domaine):
    """Le champ libre doit survivre au choix du domaine — sinon un utilisateur qui bascule en
    Mecanique perdrait silencieusement ce qu'il vient d'ecrire."""
    p = gi.build_render_prompt("bati peint en vert industriel", domaine)
    assert "bati peint en vert industriel" in p, domaine


@pytest.mark.parametrize("domaine", DOMAINES)
def test_chaque_domaine_exige_la_PRESERVATION_de_la_geometrie(domaine):
    """L'invariant de tout le module : le rendu embellit, il ne redessine pas. Un domaine ajoute
    sans cette clause laisserait le modele deplacer des pieces — et un plan qui bouge entre le
    dessin et le rendu n'est plus une preuve de rien."""
    p = gi.build_render_prompt("", domaine).lower()
    assert "preserve exactly" in p, domaine
    assert "same camera viewpoint" in p, domaine
