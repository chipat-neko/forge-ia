"""Les attendus partagés avec le site sont à jour.

Le fichier tests/attendus.json est écrit par `uv run --extra cpu python -m alignement_pas_a_pas.attendus`. Les
jumeaux TypeScript (site/src/lib/partie-1/notes.ts et dpo.ts) sont comparés à ce fichier : sans tolérance pour les
notes (tout y est entier, booléen ou texte), à 10⁻¹² près pour la perte DPO de la grille.
"""

import json

import pytest
from forge.evaluation.consignes import CONTRAINTES
from forge.evaluation.langue import MOTS_ANGLAIS, MOTS_FRANCAIS

from alignement_pas_a_pas.attendus import (
    BETAS,
    CHEMIN_ATTENDUS,
    CONSIGNES,
    ECARTS_DE_LA_CHOISIE,
    ECARTS_DE_LA_REJETEE,
    TEXTES,
    calculer_attendus,
    vers_json,
)
from alignement_pas_a_pas.perte_dpo import derivee_a_la_main, perte_dpo_a_la_main


def attendus() -> dict:
    return json.loads(CHEMIN_ATTENDUS.read_text(encoding="utf-8"))


def texte_de(nom: str) -> dict:
    return next(t for t in attendus()["textes"] if t["nom"] == nom)


# Les seuls flottants du fichier sont ceux de la grille DPO, qui passent par exp et log1p : la bibliothèque mathématique
# du C (MSVC sous Windows, glibc sous Linux) n'arrondit pas pareil, d'où un dernier chiffre différent d'un système à
# l'autre. Ils sont comparés à 1e-12 près (relatif), comme le jumeau `dpo.ts` ; tout le reste (notes, verdicts, entiers,
# textes, ordre des clés) est comparé exactement.
TOLERANCE = 1e-12
CLES_AVEC_EXP_ET_LOG = ("perte", "derivee")


def memes_attendus(relu, calcule, chemin: str = "") -> list[str]:
    """Les différences entre deux valeurs JSON : exactes, sauf les flottants de `CLES_AVEC_EXP_ET_LOG` (1e-12 relatif)."""
    if isinstance(relu, dict) and isinstance(calcule, dict):
        if list(relu) != list(calcule):
            return [f"{chemin} : clés {list(relu)} contre {list(calcule)}"]
        fautes = []
        for cle in relu:
            if cle in CLES_AVEC_EXP_ET_LOG and isinstance(relu[cle], float) and isinstance(calcule[cle], float):
                if abs(relu[cle] - calcule[cle]) > TOLERANCE * max(abs(relu[cle]), abs(calcule[cle])):
                    fautes.append(f"{chemin}.{cle} : {relu[cle]!r} contre {calcule[cle]!r}")
            else:
                fautes += memes_attendus(relu[cle], calcule[cle], f"{chemin}.{cle}")
        return fautes
    if isinstance(relu, list) and isinstance(calcule, list):
        if len(relu) != len(calcule):
            return [f"{chemin} : {len(relu)} éléments contre {len(calcule)}"]
        return [f for i, (a, b) in enumerate(zip(relu, calcule)) for f in memes_attendus(a, b, f"{chemin}[{i}]")]
    return [] if (type(relu) is type(calcule) and relu == calcule) else [f"{chemin} : {relu!r} contre {calcule!r}"]


def test_attendus_a_jour():
    fautes = memes_attendus(attendus(), json.loads(vers_json(calculer_attendus())))
    assert not fautes, (
        "tests/attendus.json n'est plus à jour (" + "; ".join(fautes[:3]) + "). Régénère-le : uv run --extra cpu python -m alignement_pas_a_pas.attendus"
    )


def test_la_comparaison_tolere_exp_et_log1p_mais_pas_le_reste():
    base = {"textes": [{"nom": "a", "mots": 3}], "grille_dpo": [{"beta": 0.1, "perte": 0.8050311234277941, "derivee": -0.05}]}
    proche = json.loads(json.dumps(base))
    proche["grille_dpo"][0]["perte"] = 0.8050311234277943  # le dernier chiffre d'un autre système
    assert memes_attendus(base, proche) == []
    loin = json.loads(json.dumps(base))
    loin["grille_dpo"][0]["perte"] = 0.80503112343
    assert memes_attendus(base, loin)
    autre = json.loads(json.dumps(base))
    autre["grille_dpo"][0]["beta"] = 0.1000000000001  # un réglage n'est pas tolérant
    assert memes_attendus(base, autre)
    autre = json.loads(json.dumps(base))
    autre["textes"][0]["mots"] = 4
    assert memes_attendus(base, autre)


def test_le_fichier_est_ecrit_comme_les_autres_attendus():
    octets = CHEMIN_ATTENDUS.read_bytes()
    assert b"\r\n" not in octets and octets.endswith(b"}\n")
    assert json.dumps(json.loads(octets), ensure_ascii=False, allow_nan=False, indent=1) + "\n" == octets.decode("utf-8")


def test_les_trois_sections():
    assert list(attendus()) == ["consignes", "textes", "grille_dpo"]


def test_les_huit_consignes_de_forge_avec_leur_phrase():
    consignes = attendus()["consignes"]
    assert [c["id"] for c in consignes] == [c.id for c in CONTRAINTES] == [identifiant for identifiant, _ in CONSIGNES]
    assert len(consignes) == 8
    assert consignes[0] == {"id": "mots_max", "kwargs": {"n": 20}, "consigne": "Réponds en 20 mots au plus."}
    assert consignes[4]["consigne"] == "Emploie le mot « paris » dans ta réponse."


def test_quarante_textes_de_reference_dont_les_pieges_de_l_atelier():
    textes = attendus()["textes"]
    assert len(textes) == len(TEXTES) == 40
    noms = [t["nom"] for t in textes]
    assert len(set(noms)) == 40
    for piege in (
        "vide",
        "chiffres-seuls",
        "accent-combinant",
        "apostrophes-courbes",
        "emoji",
        "lettre-hors-du-premier-plan",
        "fin-imposee-espace-fine",
        "fin-imposee-espace-insecable",
        "fin-imposee-next-line",
        "fin-imposee-bom",
        "dix-mille-caracteres",
        "trois-cents-mots",
        "trois-cent-un-mots",
    ):
        assert piege in noms
    assert len(texte_de("dix-mille-caracteres")["texte"]) == 10_000
    assert texte_de("vide")["texte"] == ""
    assert "\u202f" in texte_de("fin-imposee-espace-fine")["texte"] and "\u00a0" in texte_de("fin-imposee-espace-insecable")["texte"]
    assert "\u0301" in texte_de("accent-combinant")["texte"]
    assert any(ord(c) > 0xFFFF for c in texte_de("emoji")["texte"])


def test_chaque_texte_a_ses_verdicts_de_forge():
    par_id = {c.id: c for c in CONTRAINTES}
    for t in attendus()["textes"]:
        assert list(t) == ["nom", "texte", "terminee", "invite", "mots", "langue", "verdicts", "longueur", "note"]
        assert list(t["verdicts"]) == [identifiant for identifiant, _ in CONSIGNES]
        for identifiant, kwargs in CONSIGNES:
            assert t["verdicts"][identifiant] == par_id[identifiant].verifier(t["texte"], kwargs), (t["nom"], identifiant)
        assert t["langue"] in ("fr", "autre", "indetermine")
        assert t["longueur"] == (3 <= t["mots"] <= 300)
        assert list(t["note"]) == ["terminee", "consignes", "francais", "longueur"]
        assert t["note"]["terminee"] == int(t["terminee"]) and t["note"]["longueur"] == int(t["longueur"])
        assert t["note"]["francais"] == (0 if t["langue"] == "autre" else 1)
        assert t["note"]["consignes"] == sum(t["verdicts"][identifiant] for identifiant, _ in t["invite"])


def test_les_pieges_donnent_les_verdicts_de_python():
    # Les blancs de fin sont ceux de str.rstrip() de Python : l'espace fine, l'insécable, U+0085 le sont ; U+FEFF et U+180E non.
    assert texte_de("fin-imposee")["verdicts"]["fin_imposee"] is True
    assert texte_de("fin-imposee-espace-fine")["verdicts"]["fin_imposee"] is True
    assert texte_de("fin-imposee-espace-insecable")["verdicts"]["fin_imposee"] is True
    assert texte_de("fin-imposee-next-line")["verdicts"]["fin_imposee"] is True
    assert texte_de("fin-imposee-separateur-de-fichier")["verdicts"]["fin_imposee"] is True
    assert texte_de("fin-imposee-bom")["verdicts"]["fin_imposee"] is False
    assert texte_de("fin-imposee-mongol")["verdicts"]["fin_imposee"] is False
    assert texte_de("fin-imposee-apostrophe-courbe")["verdicts"]["fin_imposee"] is False  # ’ n'est pas '
    # Un mot « entier » n'a ni lettre, ni chiffre, ni « _ » collé : une majuscule hors du premier plan compte pour une lettre.
    assert texte_de("lettre-hors-du-premier-plan")["verdicts"]["mot_obligatoire"] is False
    assert texte_de("chiffre-et-tiret-bas-colles")["verdicts"]["mot_obligatoire"] is False
    assert texte_de("mot-entier-parmi-d-autres")["verdicts"]["mot_obligatoire"] is True
    assert texte_de("emoji-colle-au-mot")["verdicts"]["mot_obligatoire"] is True  # un emoji n'est pas un caractère de mot
    # Les blancs de Python coupent les phrases : U+0085 et U+001C aussi.
    assert texte_de("blancs-de-python-seulement")["verdicts"]["phrases_max"] is False  # trois phrases, pas deux
    # Texte vide, blancs, chiffres seuls : aucun mot, aucune langue, trop court. Aucune consigne n'est respectée par le texte
    # vide ni par des blancs ; des chiffres seuls forment une phrase (un nombre compte comme du contenu) sans virgule.
    for nom in ("vide", "blancs", "chiffres-seuls"):
        t = texte_de(nom)
        assert (t["mots"], t["langue"], t["longueur"]) == (0, "indetermine", False)
    assert not any(texte_de("vide")["verdicts"].values()) and not any(texte_de("blancs")["verdicts"].values())
    assert [identifiant for identifiant, verdict in texte_de("chiffres-seuls")["verdicts"].items() if verdict] == ["phrases_max", "sans_virgule"]
    # La virgule pleine largeur n'est pas une virgule.
    assert texte_de("virgule-pleine-largeur")["verdicts"]["sans_virgule"] is True
    assert texte_de("trois-cents-mots")["longueur"] is True and texte_de("trois-cent-un-mots")["longueur"] is False
    assert texte_de("deux-mots")["longueur"] is False
    assert texte_de("anglais")["langue"] == "autre" and texte_de("francais")["langue"] == "fr"


def test_la_grille_dpo_a_27_points():
    grille = attendus()["grille_dpo"]
    assert len(grille) == len(BETAS) * len(ECARTS_DE_LA_CHOISIE) * len(ECARTS_DE_LA_REJETEE) == 27
    assert [list(p) for p in grille][0] == ["beta", "ecart_choisie", "ecart_rejetee", "perte", "derivee"]
    assert {p["beta"] for p in grille} == set(BETAS)
    for p in grille:
        # exp et log1p ne s'arrondissent pas pareil sous Windows et sous Linux : 1e-12 relatif, pas l'égalité.
        assert p["perte"] == pytest.approx(perte_dpo_a_la_main(p["ecart_choisie"], p["ecart_rejetee"], 0.0, 0.0, p["beta"]), rel=1e-12)
        assert p["derivee"] == pytest.approx(derivee_a_la_main(p["beta"], p["ecart_choisie"], p["ecart_rejetee"]), rel=1e-12)
        assert abs(p["beta"] * (p["ecart_choisie"] - p["ecart_rejetee"])) < 20  # sous le seuil du softplus de PyTorch
        assert p["perte"] > 0 and p["derivee"] < 0


def test_les_listes_de_mots_outils_n_ont_aucun_mot_commun():
    # Le jumeau TypeScript copie ces deux listes ; si elles changent, notes.test.ts le voit.
    assert not MOTS_FRANCAIS & MOTS_ANGLAIS


def test_hors_de_la_grille_aucun_flottant():
    def flottants(valeur) -> list:
        if isinstance(valeur, float):
            return [valeur]
        if isinstance(valeur, dict):
            return [f for v in valeur.values() for f in flottants(v)]
        if isinstance(valeur, list):
            return [f for v in valeur for f in flottants(v)]
        return []

    donnees = attendus()
    assert flottants(donnees["consignes"]) == [] and flottants(donnees["textes"]) == []
    assert all(len(flottants(p)) >= 3 for p in donnees["grille_dpo"])
