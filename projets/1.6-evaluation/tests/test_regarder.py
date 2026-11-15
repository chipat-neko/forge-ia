"""Les cartes d'attention et les jetons suivants, sur un petit modèle tiré au hasard.

Les cartes sont comparées à l'attention de forge (`bloc.attention`), en float64 à 10⁻¹² près. Aucun test
ici ne demande d'entraînement : le modèle est minuscule et ses poids sont aléatoires. Les derniers relisent
les sorties de ton IA (`sorties/`), relevées avec ses poids publiés, sans recharger ces poids.
"""

import json
import pathlib

import pytest
import torch
from modele_factice import petit_modele, tokenizer

from evaluation_pas_a_pas.regarder import (
    cartes_attention,
    choisir_couche_et_tetes,
    jetons_de_la_phrase,
    regard_des_tetes,
    suivants,
    texte_du_jeton,
)

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


# --- Le choix des têtes à montrer -------------------------------------------------------------------


def cartes_faites_main(n: int = 6) -> torch.Tensor:
    """Trois têtes au regard connu, sur n jetons (le jeton 0 étant <|fin_texte|>)."""
    avant = torch.zeros(n, n)
    debut = torch.zeros(n, n)
    moitie = torch.zeros(n, n)
    avant[0, 0] = debut[0, 0] = moitie[0, 0] = 1.0
    for i in range(1, n):
        avant[i, i - 1] = 1.0  # toujours le jeton juste avant
        debut[i, 0] = 1.0  # toujours <|fin_texte|>
        moitie[i, 0] = moitie[i, 1] = 0.5  # la moitié sur <|fin_texte|>, la moitié sur le premier mot
    return torch.stack([avant, debut, moitie])


def test_regard_des_tetes_sur_des_cartes_faites_a_la_main():
    regards = regard_des_tetes(cartes_faites_main(6))  # jetons 2 à 5 : 4 positions mesurées
    assert regards[0] == {"jeton_d_avant": 1.0, "distance": 1.0, "debut": 0.0}
    assert regards[1] == {"jeton_d_avant": 0.0, "distance": 0.0, "debut": 1.0}  # le début ne compte pas dans la distance
    # La troisième : le mot 1 est le jeton d'avant pour la position 2 seulement ; distances 1, 2, 3, 4 à moitié.
    assert regards[2] == {"jeton_d_avant": pytest.approx(0.5 / 4), "distance": pytest.approx(0.5 * (1 + 2 + 3 + 4) / 4), "debut": 0.5}


def test_regard_des_tetes_demande_deux_mots():
    with pytest.raises(ValueError, match="au moins deux jetons"):
        regard_des_tetes(cartes_faites_main(2))


def test_choisir_couche_et_tetes():
    modele = petit_modele()
    ids = ids_de_la_phrase()
    couche, avant, loin, regards = choisir_couche_et_tetes(modele, ids)
    config = modele.config
    assert len(regards) == config.couches and all(len(r) == config.tetes for r in regards)
    assert regards[1] == regard_des_tetes(cartes_attention(modele, ids, 1))
    # La couche est celle de la tête qui regarde le plus le jeton d'avant, dans tout le modèle.
    meilleure = max(r["jeton_d_avant"] for couche_r in regards for r in couche_r)
    assert regards[couche][avant]["jeton_d_avant"] == meilleure
    # La seconde tête est, dans cette couche, celle qui regarde le plus loin (une autre que la première).
    assert loin != avant
    assert regards[couche][loin]["distance"] == max(r["distance"] for t, r in enumerate(regards[couche]) if t != avant)


# --- Les sorties de ton IA ---------------------------------------------------------------------------

SORTIES = pathlib.Path(__file__).resolve().parents[1] / "sorties"


def lire_sortie(nom: str) -> dict:
    chemin = SORTIES / nom
    # Les sorties de ton IA font partie de l'état publié (les chapitres 1.1 et 1.4 les lisent) : leur absence
    # est une panne.
    assert chemin.exists(), (
        f"sorties/{nom} manque. Reprends-le du dépôt (git checkout -- sorties/{nom}), ou refais-le avec la version "
        "ton-ia-1.5 et la commande « cartes » ou « suivants » du README du projet."
    )
    octets = chemin.read_bytes()
    assert b"\r" not in octets and octets.endswith(b"}\n")
    donnees = json.loads(octets)
    assert octets.decode("utf-8") == json.dumps(donnees, ensure_ascii=False, allow_nan=False, indent=1) + "\n"
    return donnees


def test_les_cartes_de_ton_ia_et_le_choix_de_leurs_tetes():
    cartes = lire_sortie("cartes-ton-ia.json")
    assert cartes["nom"] == "ton-ia-1.5" and cartes["appareil"] == "cpu"
    assert cartes["phrase"] == "Le forgeron chauffe le fer puis il le tord."
    jetons = cartes["jetons"]
    assert jetons[0] == "<|fin_texte|>" and "".join(jetons[1:]) == cartes["phrase"]
    assert (cartes["couches"], cartes["tetes"]) == (20, 20)
    n = len(jetons)
    for carte in cartes["cartes"]:
        assert len(carte["poids"]) == n and all(len(ligne) == n for ligne in carte["poids"])
        for i, ligne in enumerate(carte["poids"]):
            assert sum(ligne) == pytest.approx(1.0, abs=1e-4) and all(x == 0.0 for x in ligne[i + 1 :])
    # Le choix, refait sur les chiffres du fichier : la couche de la tête qui regarde le plus le jeton d'avant…
    par_couche = cartes["choix"]["jeton_d_avant_par_couche"]
    assert [c["couche"] for c in par_couche] == list(range(20))
    assert max(par_couche, key=lambda c: c["jeton_d_avant"])["couche"] == cartes["couche"]
    regards = cartes["choix"]["regards_de_la_couche"]
    assert [r["tete"] for r in regards] == list(range(20))
    avant, loin = cartes["cartes"]
    assert avant["role"] == "jeton-d-avant" and loin["role"] == "loin"
    assert avant["tete"] == max(regards, key=lambda r: r["jeton_d_avant"])["tete"] == par_couche[cartes["couche"]]["tete"]
    # … et, dans cette couche, celle qui regarde le plus loin.
    assert loin["tete"] == max((r for r in regards if r["tete"] != avant["tete"]), key=lambda r: r["distance"])["tete"]
    for carte in (avant, loin):
        assert {k: carte[k] for k in ("jeton_d_avant", "distance", "debut")} == {
            k: regards[carte["tete"]][k] for k in ("jeton_d_avant", "distance", "debut")
        }
    # Les mesures se relisent sur les cartes elles-mêmes (à l'arrondi près).
    for carte in (avant, loin):
        relu = regard_des_tetes(torch.tensor([carte["poids"]], dtype=torch.float64))[0]
        assert relu == {k: pytest.approx(carte[k], abs=1e-4) for k in relu}


def test_les_suivants_de_ton_ia():
    releve = lire_sortie("ton-ia-suivants.json")
    assert releve["nom"] == "ton-ia-1.5" and releve["appareil"] == "cpu" and releve["phrase"] == "Le forgeron frappe le"
    probas = [s["probabilite"] for s in releve["suivants"]]
    assert len(probas) == 10 and probas == sorted(probas, reverse=True) and 0 < sum(probas) < 1
