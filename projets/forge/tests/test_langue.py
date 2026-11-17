"""La règle de langue : des mots outils, sans bibliothèque. Le site la refait à l'identique (plan 8)."""

import time

from forge.evaluation.langue import MOTS_ANGLAIS, MOTS_FRANCAIS, langue, mots


def test_mots_coupe_aux_lettres_et_met_en_minuscules():
    assert mots("Le Forgeron, 12 fois : ça chauffe !") == ["le", "forgeron", "fois", "ça", "chauffe"]


def test_mots_coupe_a_l_apostrophe_droite_et_courbe():
    assert mots("L'été") == ["l", "été"]
    assert mots("L\u2019été") == ["l", "été"]
    assert mots("aujourd'hui") == ["aujourd", "hui"]


def test_mots_texte_vide_chiffres_et_symboles():
    assert mots("") == []
    assert mots("123 456 -- ?!") == []
    assert mots("   \n\t ") == []


def test_mots_garde_les_lettres_non_latines_et_les_accents_combines():
    assert mots("Ça va ? 東京 Москва") == ["ça", "va", "東京", "москва"]
    assert mots("e\u0301te") == ["e", "te"]  # l'accent combinant (catégorie M) coupe : règle simple et assumée


def test_les_listes_sont_des_frozenset_de_80_mots_au_plus_sans_mot_commun():
    for liste in (MOTS_FRANCAIS, MOTS_ANGLAIS):
        assert isinstance(liste, frozenset)
        assert 20 <= len(liste) <= 80
        assert all(m == m.lower() and m.isalpha() for m in liste)
    assert MOTS_FRANCAIS.isdisjoint(MOTS_ANGLAIS)


def test_une_phrase_francaise():
    assert langue("Le forgeron chauffe le fer, puis il le tord sur l'enclume.") == "fr"


def test_une_phrase_anglaise():
    assert langue("The smith heats the iron and then bends it.") == "autre"


def test_un_mot_seul_est_indetermine():
    assert langue("Paris.") == "indetermine"


def test_texte_vide_chiffres_code_sont_indetermines():
    assert langue("") == "indetermine"
    assert langue("1234 5678 90 12") == "indetermine"
    assert langue("x = [1, 2, 3]\nprint(x)") == "indetermine"


def test_du_code_avec_des_mots_anglais_n_est_pas_du_francais():
    code = "def f(x):\n    if x is not None and x in items:\n        return the_value\n"
    assert langue(code) == "autre"


def test_apostrophe_courbe_compte_comme_la_droite():
    # « l », « d », « qu » ne sont pas dans les listes : seuls « est » et « de » et « la » comptent
    assert langue("L\u2019été est la saison de la chaleur.") == langue("L'été est la saison de la chaleur.") == "fr"


def test_melange_francais_et_anglais_le_francais_gagne_au_double():
    # f = 4 (le, la, est, de), a = 2 (the, and) : 4 >= 2 * 2
    assert langue("Le chat est dans la maison de the neighbour and") == "fr"


def test_melange_francais_et_anglais_sinon_autre():
    # f = 2 (le, est), a = 3 (the, is, and)  : 2 < 6
    assert langue("Le chat est the dog is and") == "autre"


def test_seuil_de_trois_mots_outils():
    assert langue("le chat") == "indetermine"  # f = 1
    assert langue("le chat de la maison") == "fr"  # f = 3
    assert langue("the cat") == "indetermine"


def test_un_texte_de_10000_caracteres_passe_en_moins_de_50_ms():
    texte = ("Le forgeron chauffe le fer, puis il le tord sur l'enclume. " * 200)[:10000]
    assert len(texte) == 10000
    debut = time.perf_counter()
    assert langue(texte) == "fr"
    assert time.perf_counter() - debut < 0.05
