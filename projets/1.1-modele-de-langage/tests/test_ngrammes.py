"""Le modèle à n-grammes : compter, lisser, tirer, mesurer la surprise."""

import math
from collections import Counter

import pytest

from modele_de_langage.ngrammes import (
    alphabet,
    charger_texte,
    compter,
    compter_par_ordre,
    couper,
    distribution,
    generer,
    part_jamais_vue,
    perplexite,
    poids,
    tirer,
    tourne_en_rond,
)


def test_compter_et_laplace():
    c = compter("abab", 1)
    assert c["a"] == Counter({"b": 2}) and c["b"] == Counter({"a": 1})
    d = dict(distribution(c, ["a", "b"], "xa", 1))
    assert d == {"b": 3 / 4, "a": 1 / 4}


# region: test-uniforme
def test_contexte_jamais_vu_donne_l_uniforme():
    c = compter("abab", 2)
    assert {p for _, p in distribution(c, ["a", "b"], "bb", 2)} == {0.5}
# fin: test-uniforme


def test_temperatures():
    cc = Counter({"b": 3})
    # Des comptes bruts : un caractère jamais vu après ce contexte a un poids nul.
    assert poids(cc, ["a", "b"], 1) == [0, 3] and poids(cc, ["a", "b"], 0.5) == [0, 9]
    assert poids(cc, ["a", "b"], 2) == [0.0, math.sqrt(3)] and poids(cc, ["a", "b"], 0) == [0, 1]


def test_generer_reproductible_et_temperature_zero_tourne_en_rond():
    t = charger_texte()
    entr, _ = couper(t)
    c = compter_par_ordre(entr, 3)
    a = alphabet(t)
    assert generer(c, a, 3, "Le ", 50, 1, 0) == generer(c, a, 3, "Le ", 50, 1, 0)
    assert tourne_en_rond(generer(c, a, 3, "Le ", 300, 0, 0))


def test_generer_ne_tire_que_parmi_les_caracteres_deja_vus_et_recule():
    t = charger_texte()
    entr, _ = couper(t)
    a = alphabet(t)
    vus = set(entr)
    for n in (4, 6):
        c = compter_par_ordre(entr, n)
        for temperature in (0.5, 1, 2):
            suite = generer(c, a, n, "de la carte ", 400, temperature, 0)
            assert set(suite) <= vus
    # Le contexte « ZZ » est inconnu : le modèle recule à l'ordre 0, qui est toujours connu.
    c = compter_par_ordre("abab", 2)
    assert set(generer(c, ["a", "b", "z"], 2, "zz", 20, 1, 0)) <= {"a", "b", "z"}
    assert "z" not in generer(c, ["a", "b", "z"], 2, "ab", 20, 1, 0)


def test_texte_du_site_suffit():
    assert len(charger_texte()) >= 60_000


def test_couper_et_alphabet():
    assert couper("0123456789") == ("012345678", "9")
    assert couper("") == ("", "")
    # Les points de code, pas les unités UTF-16 : l'emoji compte pour un.
    assert alphabet("b😀a～a") == ["a", "b", "～", "😀"]


def test_compter_ordre_zero_et_contexte_court():
    assert compter("aab", 0) == {"": Counter({"a": 2, "b": 1})}
    assert compter("ab", 2) == {}
    assert dict(distribution({}, ["a"], "", 0)) == {"a": 1.0}
    with pytest.raises(ValueError, match="Il faut au moins n caractères de contexte."):
        distribution(compter("abab", 2), ["a", "b"], "a", 2)


def test_distribution_trie_et_somme_un():
    c = compter("abababc", 1)
    d = distribution(c, ["a", "b", "c"], "b", 1)
    assert [ch for ch, _ in d] == ["a", "c", "b"]
    assert abs(sum(p for _, p in d) - 1) < 1e-12
    # Le contexte est ses n derniers points de code.
    assert distribution(c, ["a", "b", "c"], "zzb", 1) == d


def test_texte_vide():
    with pytest.raises(ValueError, match="Le texte est vide : il faut au moins un caractère."):
        distribution({}, alphabet(""), "", 0)
    with pytest.raises(ValueError, match="Le texte est vide"):
        generer([{}], [], 0, "", 5, 1, 0)
    with pytest.raises(ValueError, match="Le texte est vide"):
        perplexite({}, [], 0, "abc")


def test_poids_temperature_zero_depart_a_egalite():
    # Aucun compte : aucun poids. Égalité : le plus petit point de code.
    assert poids(Counter(), ["a", "b"], 0) == [0, 0]
    assert poids(Counter({"a": 2, "b": 2}), ["a", "b"], 0) == [1, 0]
    with pytest.raises(ValueError, match="température"):
        poids(Counter(), ["a"], 3)


def test_tirer_au_bord():
    assert tirer([1, 1], 0.0) == 0
    assert tirer([1, 1], 0.5) == 1
    assert tirer([0, 1], 0.0) == 1
    assert tirer([1, 4], 0.19999) == 0 and tirer([1, 4], 0.2) == 1
    with pytest.raises(ValueError, match="Aucun poids positif"):
        tirer([0, 0], 0.5)
    with pytest.raises(ValueError, match="Aucun poids positif"):
        tirer([], 0.5)


def test_generer_cas_limites():
    c = compter_par_ordre("abab", 1)
    assert generer(c, ["a", "b"], 1, "a", 0, 1, 0) == "a"
    assert generer(c, ["a", "b"], 1, "a", -3, 1, 0) == "a"
    assert generer(c, ["a", "b"], 1, "a", 4, 0, 0) == "ababa"
    with pytest.raises(ValueError, match="Il faut au moins n caractères de contexte."):
        generer(compter_par_ordre("abab", 2), ["a", "b"], 2, "a", 4, 1, 0)


def test_part_jamais_vue_et_tourne_en_rond():
    c = compter("abab", 2)
    assert part_jamais_vue(c, "abbab", 2) == (1, 3)
    assert part_jamais_vue(c, "ab", 2) == (0, 0)
    assert tourne_en_rond("xyz" + "ab" * 20)
    assert not tourne_en_rond("abcdefghijklmnopqrstuvwxyz0123456789")
    assert not tourne_en_rond("abab")


def test_perplexite_de_l_uniforme():
    # Un contexte jamais vu donne 1/V partout : la perplexité vaut V.
    c = compter("abab", 2)
    assert perplexite(c, ["a", "b"], 2, "bbbb") == pytest.approx(2.0)
    with pytest.raises(ValueError, match="trop court"):
        perplexite(c, ["a", "b"], 2, "ab")
