"""L'exemple d'attention : « Le forgeron chauffe le fer puis il le tord ».

Seuls les vecteurs des mots et les matrices sont écrits à la main
(donnees/exemple-attention.json). Les scores, le masque, les poids et les
sorties sont calculés par les fonctions du mini-modèle (attention.py). Les
critères ci-dessous sont la définition de l'exemple : ils portent sur les
poids calculés, jamais sur des nombres recopiés.

Le jumeau TypeScript (site/src/lib/mini-modele/exemple-attention.ts) doit
trouver les mêmes nombres, au bit près : tests/attendus-attention.json, relu
par exemple-attention.test.ts.
"""

import copy
import json

import pytest

from mini_modele.attention import melanger_valeurs, poids_attention, scores_attention, softmax
from mini_modele.calcul import racine, somme, vers_hex
from mini_modele.exemple_attention import (
    FICHIER_EXEMPLE,
    DetailTete,
    charger_exemple,
    detailler_exemple,
    detailler_tete,
    verifier_exemple,
)

PHRASE = "Le forgeron chauffe le fer puis il le tord"
TRAITS = ["déterminant", "nom", "verbe", "pronom", "sujet", "objet", "personne", "chose"]
# Les traits de chaque mot, dans l'ordre de la phrase (la définition de l'exemple).
TRAITS_DES_MOTS = [
    {"déterminant"},
    {"nom", "sujet", "personne"},
    {"verbe"},
    {"déterminant"},
    {"nom", "objet", "chose"},
    set(),
    {"pronom", "sujet", "personne"},
    {"pronom", "objet", "chose"},
    {"verbe"},
]
MOTIF_ZERO = "0000000000000000"  # +0,0 : un poids masqué vaut exactement 0, sans signe moins


def hexs(valeurs) -> list[str]:
    return [vers_hex(v) for v in valeurs]


def plus_regarde(poids_ligne, requete: int) -> int:
    """Le mot visible de plus grand poids (le premier, à égalité)."""
    meilleur = 0
    for j in range(1, requete + 1):
        if poids_ligne[j] > poids_ligne[meilleur]:
            meilleur = j
    return meilleur


def test_criteres_de_l_exemple():
    ex = charger_exemple()
    agit, reprise = detailler_exemple(ex)
    assert agit.poids[2][1] >= 0.7  # « chauffe » regarde « forgeron »
    assert agit.poids[8][1] + agit.poids[8][6] >= 0.7  # « tord » regarde ses sujets
    assert reprise.poids[6][1] >= 0.6  # « il » regarde « forgeron »
    assert reprise.poids[7][4] >= 0.6  # le second « le » regarde « fer »
    for d in (agit, reprise):
        for i in range(9):
            assert all(d.poids[i][j] == 0.0 for j in range(i + 1, 9))
            assert abs(somme(d.poids[i][: i + 1]) - 1.0) <= 1e-15
    assert all(v in (0, 1) for ligne in ex["x"] for v in ligne)
    assert all(
        -5 <= v <= 5 and v == int(v) for t in ex["tetes"] for m in ("wq", "wk", "wv") for l in t[m] for v in l
    )


def test_l_exemple_ecrit_a_la_main():
    ex = charger_exemple()
    assert set(ex) == {"phrase", "jetons", "traits", "x", "tetes"}
    assert ex["phrase"] == PHRASE
    assert ex["jetons"] == PHRASE.split(" ")
    assert ex["traits"] == TRAITS
    assert [{TRAITS[t] for t, v in enumerate(ligne) if v == 1} for ligne in ex["x"]] == TRAITS_DES_MOTS
    # Des entiers, pas des flottants ni des booléens : le fichier est écrit à la main.
    assert all(type(v) is int for ligne in ex["x"] for v in ligne)
    assert [t["nom"] for t in ex["tetes"]] == ["qui agit", "de qui on parle"]
    for t in ex["tetes"]:
        assert set(t) == {"nom", "description", "wq", "wk", "wv"}
        # Une seule phrase, en français, avec l'apostrophe courbe.
        assert t["description"].endswith(".") and t["description"].count(".") == 1
        assert "'" not in t["description"]
        for m in ("wq", "wk", "wv"):
            assert len(t[m]) == 8 and all(len(ligne) == 4 for ligne in t[m]), (t["nom"], m)
            assert all(type(v) is int for ligne in t[m] for v in ligne), (t["nom"], m)


def test_le_fichier_est_en_utf8_et_lf():
    octets = FICHIER_EXEMPLE.read_bytes()
    assert b"\r" not in octets
    assert octets.endswith(b"}\n") and not octets.endswith(b"\n\n")
    assert json.loads(octets.decode("utf-8")) == charger_exemple()


def test_les_tetes_font_ce_que_dit_leur_nom():
    # Sur les poids calculés : chaque verbe regarde surtout son sujet, chaque pronom le nom qu'il remplace.
    agit, reprise = detailler_exemple(charger_exemple())
    assert plus_regarde(agit.poids[2], 2) == 1  # « chauffe » → « forgeron »
    # « tord » : ses deux sujets, « forgeron » et « il », sont les deux mots les plus regardés.
    rangs = sorted(range(9), key=lambda j: -agit.poids[8][j])
    assert set(rangs[:2]) == {1, 6}
    assert plus_regarde(reprise.poids[6], 6) == 1  # « il » → « forgeron »
    assert plus_regarde(reprise.poids[7], 7) == 4  # le second « le » → « fer »
    # « il » regarde « forgeron » plus que « fer », le nom le plus proche : la tête lit les traits, pas la distance.
    assert reprise.poids[6][1] > reprise.poids[6][4] > reprise.poids[6][5]


def test_le_masque_cache_la_suite():
    for d in detailler_exemple(charger_exemple()):
        for i in range(9):
            for j in range(9):
                masque = j > i
                assert (d.scores[i][j] is None) == masque, (i, j)
                assert (d.scores_echelles[i][j] is None) == masque, (i, j)
                if masque:
                    assert vers_hex(d.poids[i][j]) == MOTIF_ZERO, (i, j)
                else:
                    assert d.poids[i][j] > 0.0, (i, j)
    # Le premier mot ne voit que lui-même : tout son poids va sur lui.
    assert [d.poids[0][0] for d in detailler_exemple(charger_exemple())] == [1.0, 1.0]


def test_le_detail_est_calcule_par_les_fonctions_du_mini_modele():
    ex = charger_exemple()
    for t, d in zip(ex["tetes"], detailler_exemple(ex)):
        assert isinstance(d, DetailTete)
        echelle = 1.0 / racine(4.0)
        assert echelle == 0.5
        for nom, w, calcule in (("wq", t["wq"], d.requetes), ("wk", t["wk"], d.cles), ("wv", t["wv"], d.valeurs)):
            # x · W, ligne par ligne : y[j] = Σ_i x[i] × W[i][j] (des entiers : le calcul est exact).
            attendu = [[float(sum(x[i] * w[i][j] for i in range(8))) for j in range(4)] for x in ex["x"]]
            assert calcule == attendu, (t["nom"], nom)
        for i in range(9):
            q, visibles = d.requetes[i], d.cles[: i + 1]
            assert hexs(d.scores[i][: i + 1]) == hexs(scores_attention(q, visibles, 1.0))
            assert hexs(d.scores_echelles[i][: i + 1]) == hexs(scores_attention(q, visibles, echelle))
            assert hexs(d.scores_echelles[i][: i + 1]) == hexs([s * 0.5 for s in d.scores[i][: i + 1]])
            assert hexs(d.poids[i][: i + 1]) == hexs(softmax(scores_attention(q, visibles, echelle)))
            assert hexs(d.poids[i][: i + 1]) == hexs(poids_attention(q, visibles, echelle))
            assert hexs(d.sorties[i]) == hexs(melanger_valeurs(d.poids[i][: i + 1], d.valeurs[: i + 1]))


def test_detailler_tete_sur_un_petit_cas():
    # Deux mots, deux traits, une tête de taille 4 : tout tombe juste.
    x = [[1, 0], [0, 1]]
    wq = [[2, 0, 0, 0], [0, 2, 0, 0]]
    wk = [[1, 0, 0, 0], [1, 0, 0, 0]]
    wv = [[1, 2], [3, 4]]
    d = detailler_tete(x, wq, wk, wv)
    assert d.requetes == [[2.0, 0.0, 0.0, 0.0], [0.0, 2.0, 0.0, 0.0]]
    assert d.cles == [[1.0, 0.0, 0.0, 0.0], [1.0, 0.0, 0.0, 0.0]]
    assert d.valeurs == [[1.0, 2.0], [3.0, 4.0]]
    assert d.scores == [[2.0, None], [0.0, 0.0]]
    assert d.scores_echelles == [[1.0, None], [0.0, 0.0]]
    assert d.poids == [[1.0, 0.0], [0.5, 0.5]]
    assert d.sorties == [[1.0, 2.0], [2.0, 3.0]]
    # L'échelle suit la taille de la tête : 1 / √(colonnes de wq).
    d1 = detailler_tete([[1]], [[3]], [[2]], [[5]])
    assert d1.scores == [[6.0]] and d1.scores_echelles == [[6.0]] and d1.sorties == [[5.0]]


def test_detailler_tete_refuse_des_dimensions_incoherentes():
    x = [[1, 0], [0, 1]]
    bon = [[1, 0], [0, 1]]
    with pytest.raises(ValueError, match=r"wq doit avoir 2 lignes, une par trait \(reçu 3\)"):
        detailler_tete(x, [[1, 0], [0, 1], [1, 1]], bon, bon)
    with pytest.raises(ValueError, match=r"wk : la ligne 1 n'a pas la longueur de la ligne 0 \(1 au lieu de 2\)"):
        detailler_tete(x, bon, [[1, 0], [1]], bon)
    with pytest.raises(ValueError, match="wq et wk doivent avoir autant de colonnes"):
        detailler_tete(x, bon, [[1, 0, 0], [0, 1, 0]], bon)
    with pytest.raises(ValueError, match="x doit être une liste de lignes non vide"):
        detailler_tete([], bon, bon, bon)
    with pytest.raises(ValueError, match="x, ligne 0 : « True » n'est pas un nombre fini"):
        detailler_tete([[True, 0], [0, 1]], bon, bon, bon)
    with pytest.raises(ValueError, match="wv, ligne 1 : « nan » n'est pas un nombre fini"):
        detailler_tete(x, bon, bon, [[1, 0], [0, float("nan")]])


def test_verifier_exemple_refuse_un_exemple_mal_forme():
    ex = charger_exemple()
    verifier_exemple(ex)
    sans_tetes = copy.deepcopy(ex)
    del sans_tetes["tetes"]
    with pytest.raises(ValueError, match="il manque « tetes »"):
        verifier_exemple(sans_tetes)
    mot_en_trop = copy.deepcopy(ex)
    mot_en_trop["jetons"].append("encore")
    with pytest.raises(ValueError, match=r"une ligne de x par jeton \(10 jetons, 9 lignes\)"):
        verifier_exemple(mot_en_trop)
    trait_en_trop = copy.deepcopy(ex)
    trait_en_trop["traits"].append("couleur")
    with pytest.raises(ValueError, match=r"une case par trait \(9 traits, 8 cases\)"):
        verifier_exemple(trait_en_trop)
    tete_courte = copy.deepcopy(ex)
    tete_courte["tetes"][1]["wv"].pop()
    with pytest.raises(ValueError, match=r"tête « de qui on parle », wv doit avoir 8 lignes, une par trait \(reçu 7\)"):
        verifier_exemple(tete_courte)
    sans_nom = copy.deepcopy(ex)
    sans_nom["tetes"][0]["nom"] = 3
    with pytest.raises(ValueError, match="le nom et la description de chaque tête sont des textes"):
        verifier_exemple(sans_nom)
    with pytest.raises(ValueError, match="il manque « tetes »"):
        detailler_exemple(sans_tetes)


def test_charger_exemple_depuis_un_autre_fichier(tmp_path):
    autre = tmp_path / "autre.json"
    ex = charger_exemple()
    ex["phrase"] = "Un autre exemple"
    autre.write_text(json.dumps(ex, ensure_ascii=False), encoding="utf-8")
    assert charger_exemple(autre)["phrase"] == "Un autre exemple"
    assert charger_exemple(str(autre)) == ex
    # Deux appels donnent deux copies : modifier l'une ne touche pas l'autre.
    a = charger_exemple()
    a["x"][0][0] = 7
    assert charger_exemple()["x"][0][0] == 1
