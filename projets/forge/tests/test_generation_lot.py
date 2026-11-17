"""Tests de la génération par lots avec cache des clés et des valeurs (plan 7, tâche 4).

Tout tourne sur le processeur, en float32, avec la configuration minuscule du test du modèle
(vocabulaire 512, dim 64, 2 couches, 4 têtes, contexte 32), poids tirés avec une graine fixe.
L'égalité qui compte : en glouton, `generer_lot` donne exactement les jetons de `generer`, invite
par invite, même quand des invites de longueurs différentes partagent un lot. Le test `gpu` mesure
le débit (jetons générés par seconde) et la mémoire maximale du preset `tres_grand` en bf16.
"""

import time
from collections import Counter

import pytest

try:
    import torch
except ImportError as erreur:
    raise ImportError(
        "PyTorch n'est pas installé. Lance les tests avec `uv run --extra gpu pytest -q`."
    ) from erreur

from forge.modele import PRESETS, CacheKV, ConfigModele, Transformer, generer, generer_lot
from forge.modele.transformer import rope_cos_sin, rope_cos_sin_aux_positions

PETITE = ConfigModele(taille_vocabulaire=512, dim=64, couches=2, tetes=4, longueur_contexte=32)
LONGUEURS = (1, 3, 7, 12, 20)
N_NOUVEAUX = 12  # 20 + 12 = 32 : la plus longue invite remplit juste le contexte


def _modele() -> Transformer:
    """Le modèle minuscule, aux poids tirés plus larges qu'au départ d'un entraînement.

    Avec les poids de départ (écart 0,02) et le plongement lié à la sortie, un modèle non
    entraîné répète en glouton son dernier jeton, quoi qu'il lise : une égalité de sorties ne
    prouverait rien. Avec un écart de 0,3, chaque jeton choisi dépend du texte lu.
    """
    torch.manual_seed(0)
    m = Transformer(PETITE)
    with torch.no_grad():
        for p in m.parameters():
            if p.dim() > 1:
                p.normal_(0.0, 0.3)
    return m.eval()


def _invites() -> list[list[int]]:
    g = torch.Generator().manual_seed(7)
    return [torch.randint(0, 448, (n,), generator=g).tolist() for n in LONGUEURS]


def _masque_causal(longueur_cache: int, nouveaux: int) -> torch.Tensor:
    """Masque `[1, 1, nouveaux, longueur_cache + nouveaux]` d'une rangée sans bourrage."""
    total = longueur_cache + nouveaux
    lignes = torch.arange(longueur_cache, total)[:, None]
    colonnes = torch.arange(total)[None, :]
    return (colonnes <= lignes)[None, None]


# --------------------------------------------------------------------------------------
# Les pièces : RoPE aux positions données, le cache, `avancer`
# --------------------------------------------------------------------------------------


def test_rope_aux_positions_egale_rope_au_bit_pres():
    cos, sin = rope_cos_sin(12, 16, 10000.0, torch.device("cpu"))
    positions = torch.arange(12)[None].repeat(3, 1)
    cos_p, sin_p = rope_cos_sin_aux_positions(positions, 16, 10000.0)
    assert cos_p.shape == (3, 1, 12, 8)
    assert cos_p.dtype == torch.float32
    assert torch.equal(cos_p[1, 0], cos) and torch.equal(sin_p[2, 0], sin)
    # Une rangée décalée lit les angles de ses propres positions.
    cos_d, _ = rope_cos_sin_aux_positions(torch.tensor([[5, 6, 7]]), 16, 10000.0)
    assert torch.equal(cos_d[0, 0], cos[5:8])


def test_le_cache_rend_toutes_les_positions_remplies():
    cache = CacheKV(PETITE, lot=2, longueur_max=10, appareil="cpu", dtype=torch.float32)
    assert cache.k.shape == (2, 2, 4, 10, 16) and cache.v.shape == cache.k.shape
    assert cache.longueur == 0
    k1, v1 = torch.randn(2, 4, 3, 16), torch.randn(2, 4, 3, 16)
    for couche in range(PETITE.couches):
        k, v = cache.ajouter(couche, k1, v1)
        assert k.shape == (2, 4, 3, 16)
    assert cache.longueur == 3  # avancé une fois que la dernière couche a écrit
    k2, v2 = torch.randn(2, 4, 1, 16), torch.randn(2, 4, 1, 16)
    k, v = cache.ajouter(0, k2, v2)
    assert k.shape == (2, 4, 4, 16)
    assert torch.equal(k[:, :, :3], k1) and torch.equal(v[:, :, 3:], v2)


def test_le_cache_plein_refuse_d_ecrire():
    cache = CacheKV(PETITE, lot=1, longueur_max=4, appareil="cpu", dtype=torch.float32)
    with pytest.raises(ValueError, match="cache"):
        cache.ajouter(0, torch.randn(1, 4, 5, 16), torch.randn(1, 4, 5, 16))


def test_un_cache_sans_masque_est_refuse():
    m = _modele()
    cache = CacheKV(PETITE, lot=1, longueur_max=4, appareil="cpu", dtype=torch.float32)
    cos, sin = rope_cos_sin(1, 16, 10000.0, torch.device("cpu"))
    with pytest.raises(ValueError, match="il faut un masque"):
        m.blocs[0].attention(torch.randn(1, 1, 64), cos, sin, cache=cache)


def test_avancer_pas_a_pas_egale_forward():
    m = _modele()
    g = torch.Generator().manual_seed(2)
    ids = torch.randint(0, 512, (2, 20), generator=g)
    with torch.no_grad():
        complet, _ = m(ids)
        cache = CacheKV(PETITE, lot=2, longueur_max=20, appareil="cpu", dtype=torch.float32)
        morceaux = []
        # 5 jetons d'un coup, puis 4, puis un par un.
        for debut, fin in [(0, 5), (5, 9), *((i, i + 1) for i in range(9, 20))]:
            positions = torch.arange(debut, fin)[None].repeat(2, 1)
            masque = _masque_causal(debut, fin - debut).expand(2, -1, -1, -1)
            morceaux.append(m.avancer(ids[:, debut:fin], positions, masque, cache))
        pas_a_pas = torch.cat(morceaux, dim=1)
    assert cache.longueur == 20
    assert pas_a_pas.shape == complet.shape
    assert torch.allclose(pas_a_pas, complet, atol=1e-4)


# --------------------------------------------------------------------------------------
# generer_lot
# --------------------------------------------------------------------------------------


def test_glouton_egale_generer_invite_par_invite():
    m = _modele()
    invites = _invites()
    attendu = [generer(m, invite, N_NOUVEAUX, temperature=0) for invite in invites]
    obtenu = generer_lot(m, invites, N_NOUVEAUX, temperature=0, lot=5)
    assert obtenu == attendu
    assert [len(s) for s in obtenu] == [N_NOUVEAUX] * 5


def test_bourrage_a_gauche_et_positions_depuis_le_premier_vrai_jeton(monkeypatch):
    # RoPE ne dépend que des écarts : des positions décalées d'une constante donneraient les
    # mêmes jetons, aux arrondis près. On regarde donc directement ce que lit le modèle.
    m = _modele()
    lus = []
    avancer = m.avancer

    def espion(ids, positions, masque, cache):
        lus.append((ids.tolist(), positions.tolist()))
        return avancer(ids, positions, masque, cache)

    monkeypatch.setattr(m, "avancer", espion)
    sorties = generer_lot(m, [[5], [6, 7, 8]], 3, temperature=0)
    bourrage = 512 - 64 + 2  # `<|bourrage|>`, troisième des 64 jetons spéciaux de la fin
    assert lus[0] == ([[bourrage, bourrage, 5], [6, 7, 8]], [[0, 0, 0], [0, 1, 2]])
    assert lus[1] == ([[sorties[0][0]], [sorties[1][0]]], [[1], [3]])
    assert lus[2] == ([[sorties[0][1]], [sorties[1][1]]], [[2], [4]])
    assert len(lus) == 3  # le dernier jeton tiré n'est jamais relu


def test_la_taille_du_lot_ne_change_rien_en_glouton():
    m = _modele()
    invites = _invites()
    un = generer_lot(m, invites, N_NOUVEAUX, temperature=0, lot=1)
    cinq = generer_lot(m, invites, N_NOUVEAUX, temperature=0, lot=5)
    deux = generer_lot(m, invites, N_NOUVEAUX, temperature=0, lot=2)
    assert un == cinq == deux


def test_meme_graine_meme_sortie_a_temperature_1():
    m = _modele()
    invites = _invites()
    a = generer_lot(m, invites, N_NOUVEAUX, temperature=1.0, graine=11, lot=2)
    b = generer_lot(m, invites, N_NOUVEAUX, temperature=1.0, graine=11, lot=2)
    c = generer_lot(m, invites, N_NOUVEAUX, temperature=1.0, graine=12, lot=2)
    assert a == b
    assert a != c
    assert all(0 <= t < 512 for s in a for t in s)


def test_coupure_apres_le_jeton_d_arret():
    m = _modele()
    invites = _invites()
    sans_arret = generer_lot(m, invites, N_NOUVEAUX, temperature=0, lot=5)
    # Le jeton écrit par le plus d'invites : certaines s'arrêtent, à des pas différents,
    # les autres vont jusqu'au bout.
    rangees = Counter(t for sortie in sans_arret for t in set(sortie))
    arret = min(rangees, key=lambda t: (-rangees[t], t))
    assert 2 <= rangees[arret] < len(invites)
    avec_arret = generer_lot(m, invites, N_NOUVEAUX, temperature=0, arret=arret, lot=5)
    for complet, coupe in zip(sans_arret, avec_arret, strict=True):
        attendu = complet[: complet.index(arret) + 1] if arret in complet else complet
        assert coupe == attendu
    # Tout le lot arrêté dès le premier jeton : rien n'est écrit après.
    premier = sans_arret[0][0]
    assert generer_lot(m, invites[:1], N_NOUVEAUX, temperature=0, arret=premier) == [[premier]]


def test_zero_nouveau_jeton():
    assert generer_lot(_modele(), _invites(), 0, temperature=0) == [[]] * 5


def test_une_invite_vide_est_refusee():
    with pytest.raises(ValueError, match="L'invite 2 est vide"):
        generer_lot(_modele(), [[1, 2], [], [3]], 4)


def test_une_invite_trop_longue_est_refusee():
    with pytest.raises(ValueError, match="L'invite 1 a 30 jetons.*32"):
        generer_lot(_modele(), [list(range(30))], 3)


def test_un_jeton_hors_du_vocabulaire_est_refuse():
    with pytest.raises(ValueError, match="vocabulaire"):
        generer_lot(_modele(), [[1, 600]], 2)


def test_le_mode_de_chaque_sous_module_est_rendu():
    m = _modele().train()
    m.blocs[1].eval()
    generer_lot(m, _invites(), 2, temperature=0)
    assert m.training and m.blocs[0].training
    assert not m.blocs[1].training and not m.blocs[1].attention.training


def test_aucun_gradient_n_est_garde():
    m = _modele()
    generer_lot(m, _invites(), 2, temperature=0)
    assert all(p.grad is None for p in m.parameters())


# --------------------------------------------------------------------------------------
# Sur la carte : le débit, la première mesure réelle
# --------------------------------------------------------------------------------------


@pytest.mark.gpu
def test_debit_de_generation_tres_grand_en_bf16():
    torch.manual_seed(0)
    config = PRESETS["tres_grand"]
    modele = Transformer(config).to("cuda", torch.bfloat16)
    g = torch.Generator().manual_seed(0)
    invites = torch.randint(0, 32704, (32, 128), generator=g).tolist()
    generer_lot(modele, invites[:2], 8, temperature=1.0, lot=2)  # chauffe : noyaux CUDA chargés
    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()
    depart = time.perf_counter()
    sorties = generer_lot(modele, invites, 256, temperature=1.0, lot=32)
    torch.cuda.synchronize()
    duree = time.perf_counter() - depart
    generes = sum(len(s) for s in sorties)
    pic = torch.cuda.max_memory_allocated() / 2**30
    print(f"JETONS_GENERES={generes} DUREE_S={duree:.2f} JETONS_PAR_S={generes / duree:.0f}")
    print(f"MEMOIRE_PIC_GO={pic:.2f}")
    assert generes == 32 * 256
