"""Les cartes d'attention et les jetons suivants, sur un petit modèle tiré au hasard.

Les cartes sont comparées à l'attention de forge (`bloc.attention`), en float64 à 10⁻¹² près. Aucun test
ici ne demande d'entraînement : le modèle est minuscule et ses poids sont aléatoires.
"""

import pytest
import torch
from modele_factice import petit_modele, tokenizer

from evaluation_pas_a_pas.regarder import cartes_attention, jetons_de_la_phrase, suivants, texte_du_jeton

PHRASE = "Le forgeron dit qu'il frappe le fer"


def ids_de_la_phrase(longueur_contexte: int = 64) -> torch.Tensor:
    return torch.tensor(jetons_de_la_phrase(tokenizer(), PHRASE, longueur_contexte))


# region: test-cartes
def test_cartes_redonnent_la_sortie_de_l_attention():
    # Les cartes, multipliées par les valeurs v puis par proj_sortie, redonnent ce que forge calcule
    # dans le bloc : bloc.attention(norme_attention(x)), en float64, à 10⁻¹² près.
    modele = petit_modele().double()
    ids = ids_de_la_phrase()
    couche = 1
    bloc = modele.blocs[couche]
    entrees = {}
    crochet = bloc.norme_attention.register_forward_hook(lambda m, e, s: entrees.setdefault("x", s))
    with torch.no_grad():
        modele(ids[None])
    crochet.remove()
    x = entrees["x"]  # [1, n, dim]
    n, tetes = x.shape[1], modele.config.tetes
    cartes = cartes_attention(modele, ids, couche)  # [têtes, n, n]
    with torch.no_grad():
        v = bloc.attention.proj_qkv(x).chunk(3, dim=-1)[2]
        v = v.reshape(1, n, tetes, -1).transpose(1, 2)  # [1, têtes, n, dim_tete]
        melange = (cartes[None] @ v).transpose(1, 2).reshape(1, n, -1)
        refait = bloc.attention.proj_sortie(melange)
        cos, sin = rope_de_forge(n, modele)
        attendu = bloc.attention(x, cos, sin)
    assert (refait - attendu).abs().max().item() <= 1e-12
# fin: test-cartes


def rope_de_forge(n: int, modele):
    from forge.modele.transformer import rope_cos_sin

    config = modele.config
    return rope_cos_sin(n, config.dim // config.tetes, config.base_rope, "cpu")


def test_cartes_ont_la_forme_du_modele_et_se_lisent_comme_un_regard():
    modele = petit_modele()
    ids = ids_de_la_phrase()
    n = len(ids)
    for couche in range(modele.config.couches):
        cartes = cartes_attention(modele, ids, couche)
        assert cartes.shape == (modele.config.tetes, n, n)
        assert torch.allclose(cartes.sum(dim=-1), torch.ones(modele.config.tetes, n), atol=1e-6)  # chaque ligne totalise 1
        assert torch.equal(cartes.triu(diagonal=1), torch.zeros_like(cartes))  # jamais de regard en avant
        assert (cartes >= 0).all()
    # Le premier jeton n'a que lui à regarder.
    assert torch.allclose(cartes[:, 0, 0], torch.ones(modele.config.tetes))


def test_cartes_prennent_une_phrase_en_ligne_ou_en_lot_de_un():
    modele = petit_modele()
    ids = ids_de_la_phrase()
    assert torch.equal(cartes_attention(modele, ids, 0), cartes_attention(modele, ids[None], 0))


def test_cartes_ne_gardent_pas_de_gradient_et_laissent_le_modele_intact():
    modele = petit_modele()
    avant = [p.clone() for p in modele.parameters()]
    cartes_attention(modele, ids_de_la_phrase(), 1)
    assert all(torch.equal(a, p) for a, p in zip(avant, modele.parameters()))
    assert not modele.blocs[1].norme_attention._forward_hooks  # le crochet est retiré


def test_cartes_refusent_une_couche_inexistante_ou_plusieurs_phrases():
    modele = petit_modele()
    ids = ids_de_la_phrase()
    with pytest.raises(ValueError, match="La couche 2 n'existe pas"):
        cartes_attention(modele, ids, 2)
    with pytest.raises(ValueError, match="La couche -1 n'existe pas"):
        cartes_attention(modele, ids, -1)
    with pytest.raises(ValueError, match="une seule phrase"):
        cartes_attention(modele, torch.stack([ids, ids]), 0)


@pytest.mark.gpu
def test_cartes_sur_la_carte_egales_a_celles_du_processeur_a_1e_5():
    modele = petit_modele()
    ids = ids_de_la_phrase()
    du_processeur = cartes_attention(modele, ids, 1)
    sur_la_carte = cartes_attention(modele.to("cuda"), ids, 1).cpu()
    assert (sur_la_carte - du_processeur).abs().max().item() <= 1e-5


def test_jetons_de_la_phrase_commencent_par_fin_texte_et_gardent_la_fin():
    tok = tokenizer()
    ids = jetons_de_la_phrase(tok, PHRASE, 64)
    assert ids[0] == tok.id_special("<|fin_texte|>") and tok.decoder(ids[1:]) == PHRASE
    court = jetons_de_la_phrase(tok, PHRASE, 4)
    assert court == ids[-4:] and len(court) == 4


def test_texte_du_jeton():
    tok = tokenizer()
    ids = jetons_de_la_phrase(tok, "Le forgeron", 64)
    assert "".join(texte_du_jeton(tok, i) for i in ids[1:]) == "Le forgeron"
    assert texte_du_jeton(tok, ids[0]) == "<|fin_texte|>"


def test_suivants_donnent_les_k_plus_probables_dans_l_ordre():
    modele, tok = petit_modele(), tokenizer()
    liste = suivants(modele, tok, PHRASE, k=10)
    assert len(liste) == 10
    probas = [p for _, p in liste]
    assert probas == sorted(probas, reverse=True)
    assert all(0 < p < 1 for p in probas) and sum(probas) < 1
    assert all(isinstance(jeton, str) for jeton, _ in liste)
    # Le plus probable est celui du plus grand score du modèle.
    with torch.no_grad():
        logits, _ = modele(torch.tensor([jetons_de_la_phrase(tok, PHRASE, 64)]))
    assert liste[0][0] == texte_du_jeton(tok, int(logits[0, -1].argmax()))


def test_suivants_sur_tous_les_jetons_totalisent_un():
    modele, tok = petit_modele(), tokenizer()
    liste = suivants(modele, tok, PHRASE, k=modele.config.taille_vocabulaire + 10)
    assert len(liste) == modele.config.taille_vocabulaire
    assert sum(p for _, p in liste) == pytest.approx(1.0, abs=1e-4)


def test_suivants_refusent_k_nul():
    with pytest.raises(ValueError, match="au moins un jeton"):
        suivants(petit_modele(), tokenizer(), PHRASE, k=0)
