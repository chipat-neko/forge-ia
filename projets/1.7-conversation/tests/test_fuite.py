"""La fuite entre deux conversations d'une rangée : presque rien avec le masque par document, net sans lui."""

from conversation_pas_a_pas.fuite import ecarts_de_fuite


def test_fuite():
    e = ecarts_de_fuite()
    assert e["avec_masque"] <= 1e-5 and e["sans_masque"] > 1e-3


def test_la_fuite_est_la_meme_a_chaque_fois_et_change_avec_la_graine():
    assert ecarts_de_fuite(0) == ecarts_de_fuite(0)
    assert ecarts_de_fuite(1)["sans_masque"] != ecarts_de_fuite(0)["sans_masque"]


def test_la_fuite_dit_la_taille_des_deux_conversations():
    e = ecarts_de_fuite()
    assert e["graine"] == 0 and e["jetons_a"] > 0 and e["jetons_b"] > 0
    assert e["jetons_a"] + e["jetons_b"] <= 64  # la rangée tient dans le contexte du modèle minuscule


def test_la_fuite_est_nette_pour_plusieurs_graines():
    for graine in range(4):
        e = ecarts_de_fuite(graine)
        assert e["avec_masque"] <= 1e-5 and e["sans_masque"] > 1e-3, graine
