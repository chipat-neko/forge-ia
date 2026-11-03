"""Tests du transformer de « ton IA » et de la génération.

Tout tourne sur le processeur avec une configuration minuscule (vocabulaire 512, dim 64,
2 couches, 4 têtes, contexte 32), sauf les tests marqués `gpu`. Les cinq tailles prévues
(`PRESETS`) sont créées sur le périphérique « meta » : PyTorch y compte les paramètres sans
réserver de mémoire, ce qui permet de vérifier leur nombre exact sans rien entraîner.
"""

import math

import pytest

try:
    import torch
    import torch.nn.functional as F
except ImportError as erreur:
    raise ImportError(
        "PyTorch n'est pas installé. Lance les tests avec `uv run --extra gpu pytest -q` "
        "(carte NVIDIA) ou `uv run --extra cpu pytest -q` (sans carte graphique)."
    ) from erreur

from forge.modele import (
    PRESETS,
    ConfigModele,
    Transformer,
    generer,
    largeur_cachee,
    nombre_parametres,
)
from forge.modele.transformer import RMSNorm, appliquer_rope, rope_cos_sin

PETITE = ConfigModele(taille_vocabulaire=512, dim=64, couches=2, tetes=4, longueur_contexte=32)


# --------------------------------------------------------------------------------------
# Les tests du plan
# --------------------------------------------------------------------------------------


def test_formes_et_parametres():
    m = Transformer(PETITE)
    logits, perte = m(torch.randint(0, 512, (2, 32)), torch.randint(0, 512, (2, 32)))
    assert logits.shape == (2, 32, 512)
    assert abs(perte.item() - math.log(512)) < 0.5
    assert sum(p.numel() for p in m.parameters()) == nombre_parametres(PETITE)
    assert m.plongement.weight is m.sortie.weight


def test_causalite():
    m = Transformer(PETITE).eval()
    x = torch.randint(0, 512, (1, 32))
    y = x.clone()
    y[0, 20:] = 7
    assert torch.allclose(m(x)[0][0, :20], m(y)[0][0, :20], atol=1e-5)


def test_surapprentissage():
    torch.manual_seed(0)
    m = Transformer(PETITE)
    opt = torch.optim.AdamW(m.parameters(), 3e-3)
    x = torch.randint(0, 512, (4, 32))
    y = torch.roll(x, -1, 1)
    for _ in range(300):
        opt.zero_grad()
        m(x, y)[1].backward()
        opt.step()
    assert m(x, y)[1].item() < 0.5


def test_generation_deterministe():
    m = Transformer(PETITE).eval()
    a = generer(m, [1, 2, 3], 10, graine=5)
    b = generer(m, [1, 2, 3], 10, graine=5)
    assert a == b and len(a) == 10
    assert generer(m, [1, 2, 3], 50, graine=5, arret=a[0]) == [a[0]]


def test_presets():
    assert 100e6 < nombre_parametres(PRESETS["moyen"]) < 140e6


# --------------------------------------------------------------------------------------
# Configuration, tailles prévues, nombre de paramètres
# --------------------------------------------------------------------------------------


def test_presets_valeurs_exactes():
    attendu = {
        "mini": (384, 6, 6, 512),
        "petit": (512, 8, 8, 2048),
        "moyen": (768, 12, 12, 2048),
        "grand": (1024, 16, 16, 2048),
        "tres_grand": (1280, 20, 20, 2048),
    }
    assert list(PRESETS) == list(attendu)
    for nom, (dim, couches, tetes, contexte) in attendu.items():
        c = PRESETS[nom]
        assert (c.dim, c.couches, c.tetes, c.longueur_contexte) == (dim, couches, tetes, contexte)
        assert c.taille_vocabulaire == 32768
        assert c.base_rope == 10000.0


def test_config_figee():
    with pytest.raises(AttributeError):
        PETITE.dim = 128  # type: ignore[misc]


def test_config_invalide_message_en_francais():
    with pytest.raises(ValueError, match="divisible"):
        ConfigModele(taille_vocabulaire=512, dim=60, couches=2, tetes=8, longueur_contexte=32)
    # dim 12 avec 4 têtes : 3 dimensions par tête, impair, donc pas de paires pour RoPE.
    with pytest.raises(ValueError, match="paire"):
        ConfigModele(taille_vocabulaire=512, dim=12, couches=2, tetes=4, longueur_contexte=32)
    with pytest.raises(ValueError, match="couches"):
        ConfigModele(taille_vocabulaire=512, dim=64, couches=0, tetes=4, longueur_contexte=32)


def test_largeur_cachee_des_presets():
    # 8/3 × dim, arrondi au multiple de 64 le plus proche.
    assert largeur_cachee(384) == 1024  # 1024,0 exactement
    assert largeur_cachee(512) == 1344  # 1365,3 : 21,33 × 64, donc 21 × 64
    assert largeur_cachee(768) == 2048  # 2048,0 exactement
    assert largeur_cachee(1024) == 2752  # 2730,7 : 42,67 × 64, donc 43 × 64
    assert largeur_cachee(1280) == 3392  # 3413,3 : 53,33 × 64, donc 53 × 64
    for c in PRESETS.values():
        assert largeur_cachee(c.dim) % 64 == 0


def test_largeur_cachee_egalite_vers_le_haut():
    # 8/3 × 36 = 96, juste au milieu de 64 et 128 : à égalité, on prend le multiple du dessus.
    assert largeur_cachee(36) == 128
    assert largeur_cachee(12) == 64  # 8/3 × 12 = 32, milieu de 0 et 64 : jamais moins de 64
    # Jamais plus loin de 8/3 × dim que 32, la moitié d'un pas.
    for dim in range(24, 2049, 2):
        assert abs(largeur_cachee(dim) - 8 * dim / 3) <= 32 + 1e-9


def test_le_mlp_utilise_la_largeur_cachee():
    m = Transformer(PETITE)
    mlp = m.blocs[0].mlp
    assert mlp.proj_porte.weight.shape == (largeur_cachee(64), 64)
    assert mlp.proj_haute.weight.shape == (largeur_cachee(64), 64)
    assert mlp.proj_basse.weight.shape == (64, largeur_cachee(64))


@pytest.mark.parametrize("nom", list(PRESETS))
def test_nombre_de_parametres_exact_pour_chaque_taille(nom):
    c = PRESETS[nom]
    with torch.device("meta"):
        m = Transformer(c)
    assert sum(p.numel() for p in m.parameters()) == nombre_parametres(c)
    assert m.plongement.weight is m.sortie.weight


def test_nombre_de_parametres_des_cinq_tailles():
    """Valeurs exactes, relevées une fois pour toutes : elles servent dans le chapitre 1.4."""
    attendu = {
        "mini": 23_204_736,
        "petit": 41_689_600,
        "moyen": 110_119_680,
        "grand": 235_963_392,
        "tres_grand": 433_573_120,
    }
    assert {nom: nombre_parametres(c) for nom, c in PRESETS.items()} == attendu


def test_aucun_biais_et_seulement_des_parametres_attendus():
    m = Transformer(PETITE)
    noms = [nom for nom, _ in m.named_parameters()]
    assert not any(nom.endswith("bias") for nom in noms)
    # Le poids de sortie est le même objet que le plongement : un seul nom dans la liste.
    assert "sortie.weight" not in noms
    assert "plongement.weight" in noms
    # Pas de tampon : rien d'autre que les paramètres dans l'état du modèle (RoPE est recalculé).
    assert len(list(m.buffers())) == 0
    assert set(m.state_dict()) == set(noms) | {"sortie.weight"}


# --------------------------------------------------------------------------------------
# Initialisation
# --------------------------------------------------------------------------------------


def test_initialisation():
    torch.manual_seed(0)
    c = ConfigModele(taille_vocabulaire=512, dim=128, couches=4, tetes=4, longueur_contexte=32)
    m = Transformer(c)
    ecart = 0.02
    ecart_residuel = 0.02 / math.sqrt(2 * c.couches)

    def std(poids):
        return poids.std().item()

    assert std(m.plongement.weight) == pytest.approx(ecart, rel=0.05)
    assert abs(m.plongement.weight.mean().item()) < 0.001
    for bloc in m.blocs:
        assert std(bloc.attention.proj_qkv.weight) == pytest.approx(ecart, rel=0.05)
        assert std(bloc.mlp.proj_porte.weight) == pytest.approx(ecart, rel=0.05)
        assert std(bloc.mlp.proj_haute.weight) == pytest.approx(ecart, rel=0.05)
        # Les deux projections qui reviennent dans le résidu sont plus petites.
        assert std(bloc.attention.proj_sortie.weight) == pytest.approx(ecart_residuel, rel=0.05)
        assert std(bloc.mlp.proj_basse.weight) == pytest.approx(ecart_residuel, rel=0.05)
        assert torch.equal(bloc.norme_attention.poids, torch.ones(c.dim))
        assert torch.equal(bloc.norme_mlp.poids, torch.ones(c.dim))
    assert torch.equal(m.norme_finale.poids, torch.ones(c.dim))


# --------------------------------------------------------------------------------------
# RMSNorm et RoPE
# --------------------------------------------------------------------------------------


def test_rmsnorm():
    norme = RMSNorm(16)
    assert norme.epsilon == 1e-5
    x = torch.randn(3, 5, 16) * 7 + 2
    y = norme(x)
    # Avec un poids de 1, la moyenne des carrés de chaque vecteur vaut 1 après normalisation.
    assert torch.allclose(y.pow(2).mean(-1), torch.ones(3, 5), atol=1e-3)
    # Le poids multiplie, composante par composante.
    norme.poids.data = torch.arange(16, dtype=torch.float32)
    assert torch.allclose(norme(x), y * torch.arange(16, dtype=torch.float32), atol=1e-5)
    # La sortie garde le type de l'entrée (utile avec bf16).
    assert RMSNorm(16)(x.to(torch.bfloat16)).dtype == torch.bfloat16


def test_rope_position_zero_ne_change_rien():
    cos, sin = rope_cos_sin(8, 16, 10000.0, torch.device("cpu"))
    x = torch.randn(2, 3, 8, 16)
    assert torch.allclose(appliquer_rope(x, cos, sin)[:, :, 0], x[:, :, 0], atol=1e-6)


def test_rope_conserve_la_norme_et_le_type():
    cos, sin = rope_cos_sin(8, 16, 10000.0, torch.device("cpu"))
    assert cos.dtype == sin.dtype == torch.float32
    x = torch.randn(2, 3, 8, 16)
    y = appliquer_rope(x, cos, sin)
    assert torch.allclose(x.norm(dim=-1), y.norm(dim=-1), atol=1e-5)
    xb = x.to(torch.bfloat16)
    assert appliquer_rope(xb, cos, sin).dtype == torch.bfloat16


def test_rope_ne_depend_que_de_la_distance():
    """Le produit scalaire q·k après RoPE ne dépend que de l'écart entre les positions."""
    longueur, dim_tete = 24, 16
    cos, sin = rope_cos_sin(longueur, dim_tete, 10000.0, torch.device("cpu"))
    q0, k0 = torch.randn(dim_tete), torch.randn(dim_tete)
    q = appliquer_rope(q0.expand(1, 1, longueur, dim_tete), cos, sin)[0, 0]
    k = appliquer_rope(k0.expand(1, 1, longueur, dim_tete), cos, sin)[0, 0]
    scores = q @ k.T  # scores[m, n] : requête à la position m, clé à la position n
    for ecart in (0, 1, 5, 11):
        diagonale = torch.diagonal(scores, offset=-ecart)  # les (m, n) avec m - n = ecart
        assert torch.allclose(diagonale, diagonale[0].expand_as(diagonale), atol=1e-4)
    # Et ce n'est pas trivial : deux écarts différents ne donnent pas le même score.
    assert not torch.allclose(scores[1, 0], scores[5, 0], atol=1e-3)


def test_le_modele_utilise_rope(monkeypatch):
    """Sans RoPE (rotation remplacée par l'identité), les sorties du modèle changeraient."""
    from forge.modele import transformer as module_transformer

    torch.manual_seed(0)
    m = Transformer(PETITE).eval()
    x = torch.randint(0, 512, (1, 16))
    avec = m(x)[0]
    monkeypatch.setattr(module_transformer, "appliquer_rope", lambda t, cos, sin: t)
    sans = m(x)[0]
    assert not torch.allclose(avec, sans, atol=1e-6)


def test_rope_fait_tourner_les_paires_comme_prevu():
    """Pour la paire i, l'angle de la position p vaut p × base^(-2i/dim_tete)."""
    cos, sin = rope_cos_sin(4, 8, 10000.0, torch.device("cpu"))
    assert cos.shape == sin.shape == (4, 4)
    for i in range(4):
        angle = 3 * 10000.0 ** (-2 * i / 8)
        assert cos[3, i].item() == pytest.approx(math.cos(angle), abs=1e-6)
        assert sin[3, i].item() == pytest.approx(math.sin(angle), abs=1e-6)
    x = torch.zeros(1, 1, 4, 8)
    x[..., 0] = 1.0  # premier composant de la paire 0 : vecteur (1, 0)
    y = appliquer_rope(x, cos, sin)
    assert y[0, 0, 3, 0].item() == pytest.approx(math.cos(3.0), abs=1e-6)
    assert y[0, 0, 3, 1].item() == pytest.approx(math.sin(3.0), abs=1e-6)


# --------------------------------------------------------------------------------------
# Passe avant
# --------------------------------------------------------------------------------------


def test_forward_sans_cibles_renvoie_pas_de_perte():
    m = Transformer(PETITE)
    logits, perte = m(torch.randint(0, 512, (3, 10)))
    assert logits.shape == (3, 10, 512)
    assert perte is None


def test_forward_contexte_trop_long_message_utile():
    m = Transformer(PETITE)
    with pytest.raises(ValueError, match="longueur_contexte"):
        m(torch.randint(0, 512, (1, 33)))


def test_perte_ignore_les_cibles_a_moins_cent():
    """-100 marque une cible à ne pas apprendre (utile pour l'affinage plus tard)."""
    m = Transformer(PETITE).eval()
    x = torch.randint(0, 512, (2, 16))
    y = torch.randint(0, 512, (2, 16))
    masque = y.clone()
    masque[:, :8] = -100
    logits, perte = m(x, masque)
    attendu = F.cross_entropy(logits[:, 8:].reshape(-1, 512), y[:, 8:].reshape(-1))
    assert perte.item() == pytest.approx(attendu.item(), abs=1e-5)


def test_perte_calculee_sur_la_moyenne_de_tous_les_jetons():
    m = Transformer(PETITE).eval()
    x = torch.randint(0, 512, (2, 16))
    y = torch.randint(0, 512, (2, 16))
    logits, perte = m(x, y)
    attendu = F.cross_entropy(logits.reshape(-1, 512), y.reshape(-1))
    assert perte.item() == pytest.approx(attendu.item(), abs=1e-6)


def test_toutes_les_couches_recoivent_un_gradient():
    m = Transformer(PETITE)
    m(torch.randint(0, 512, (2, 16)), torch.randint(0, 512, (2, 16)))[1].backward()
    for nom, p in m.named_parameters():
        assert p.grad is not None and torch.isfinite(p.grad).all(), nom
        assert p.grad.abs().sum() > 0, nom


# --------------------------------------------------------------------------------------
# Génération
# --------------------------------------------------------------------------------------


def test_generation_renvoie_seulement_les_nouveaux_jetons():
    m = Transformer(PETITE).eval()
    ids = [1, 2, 3]
    sortie = generer(m, ids, 7, graine=1)
    assert len(sortie) == 7
    assert ids == [1, 2, 3]  # la liste de l'appelant n'est pas modifiée
    assert all(isinstance(t, int) and 0 <= t < 512 for t in sortie)
    assert generer(m, ids, 0) == []


def test_generation_graines_differentes_donnent_des_textes_differents():
    m = Transformer(PETITE).eval()
    assert generer(m, [1, 2, 3], 20, graine=1) != generer(m, [1, 2, 3], 20, graine=2)


def test_generation_temperature_zero_est_gloutonne():
    m = Transformer(PETITE).eval()
    ids = [4, 5, 6]
    a = generer(m, ids, 12, temperature=0, graine=1)
    b = generer(m, ids, 12, temperature=0, graine=999)
    assert a == b  # la graine ne sert plus à rien
    # Chaque jeton est l'argmax des logits du contexte qui le précède.
    contexte = list(ids)
    with torch.no_grad():
        for jeton in a:
            logits, _ = m(torch.tensor([contexte]))
            assert jeton == logits[0, -1].argmax().item()
            contexte.append(jeton)


def test_generation_top_k_un_est_glouton():
    m = Transformer(PETITE).eval()
    assert generer(m, [4, 5, 6], 12, top_k=1, graine=3) == generer(
        m, [4, 5, 6], 12, temperature=0
    )


def test_generation_top_k_limite_aux_k_meilleurs():
    m = Transformer(PETITE).eval()
    ids = [7, 8, 9]
    k = 5
    sortie = generer(m, ids, 25, temperature=5.0, top_k=k, graine=11)
    contexte = list(ids)
    with torch.no_grad():
        for jeton in sortie:
            logits, _ = m(torch.tensor([contexte]))
            meilleurs = logits[0, -1].topk(k).indices.tolist()
            assert jeton in meilleurs
            contexte.append(jeton)


def test_generation_top_k_zero_ne_coupe_rien():
    """top_k=0 : tout le vocabulaire est permis, même avec k plus grand que le vocabulaire."""
    m = Transformer(PETITE).eval()
    assert len(generer(m, [1, 2], 5, top_k=0)) == 5
    assert len(generer(m, [1, 2], 5, top_k=10_000)) == 5


def test_generation_arret_inclus_et_ignore_s_il_n_arrive_pas():
    m = Transformer(PETITE).eval()
    complet = generer(m, [1, 2, 3], 15, graine=5)
    cible = complet[6]
    premier = complet.index(cible)
    assert generer(m, [1, 2, 3], 15, graine=5, arret=cible) == complet[: premier + 1]
    # Un jeton d'arrêt qui n'arrive jamais ne change rien.
    absent = next(t for t in range(512) if t not in complet)
    assert generer(m, [1, 2, 3], 15, graine=5, arret=absent) == complet


def test_generation_garde_les_derniers_jetons_du_contexte():
    m = Transformer(PETITE).eval()
    long = [(7 * i + 3) % 512 for i in range(100)]
    # Avec 100 jetons d'entrée (et un contexte de 32), seul le bout compte.
    assert generer(m, long, 6, graine=2) == generer(m, long[-32:], 6, graine=2)
    # Et la génération dépasse sans erreur la longueur du contexte.
    assert len(generer(m, long[-32:], 40, graine=2)) == 40


def test_generation_ne_touche_pas_au_hasard_global():
    m = Transformer(PETITE).eval()
    torch.manual_seed(123)
    avant = torch.get_rng_state()
    generer(m, [1, 2, 3], 10, graine=5)
    assert torch.equal(torch.get_rng_state(), avant)
    # Et un tirage global fait entre deux générations ne change pas leur résultat.
    a = generer(m, [1, 2, 3], 10, graine=5)
    torch.rand(100)
    assert generer(m, [1, 2, 3], 10, graine=5) == a


def test_generation_remet_le_mode_du_modele():
    m = Transformer(PETITE)
    m.train()
    generer(m, [1, 2, 3], 3)
    assert m.training and all(sous.training for sous in m.modules())
    m.eval()
    generer(m, [1, 2, 3], 3)
    assert not m.training and not any(sous.training for sous in m.modules())


def test_generation_remet_le_mode_meme_en_cas_d_erreur():
    m = Transformer(PETITE)
    m.train()
    with pytest.raises(ValueError):
        generer(m, [1, 2, 3], 3, temperature=-1.0)
    assert m.training
    with pytest.raises(ValueError):
        generer(m, [1, 2, 99999], 3)
    assert m.training


def test_generation_ne_garde_pas_de_gradient():
    m = Transformer(PETITE)
    generer(m, [1, 2, 3], 3)
    assert all(p.grad is None for p in m.parameters())


def test_generation_erreurs_en_francais():
    m = Transformer(PETITE)
    with pytest.raises(ValueError, match="vide"):
        generer(m, [], 3)
    with pytest.raises(ValueError, match="vocabulaire"):
        generer(m, [512], 3)
    with pytest.raises(ValueError, match="vocabulaire"):
        generer(m, [-1], 3)
    with pytest.raises(ValueError, match="n_nouveaux"):
        generer(m, [1], -1)
    with pytest.raises(ValueError, match="temperature"):
        generer(m, [1], 3, temperature=-0.1)
    with pytest.raises(ValueError, match="top_k"):
        generer(m, [1], 3, top_k=-1)


# --------------------------------------------------------------------------------------
# Carte graphique
# --------------------------------------------------------------------------------------


@pytest.mark.gpu
def test_petit_forward_backward_bf16_sur_gpu():
    torch.manual_seed(0)
    m = Transformer(PRESETS["petit"]).to("cuda")
    x = torch.randint(0, 32768, (2, 256), device="cuda")
    y = torch.randint(0, 32768, (2, 256), device="cuda")
    with torch.autocast("cuda", dtype=torch.bfloat16):
        logits, perte = m(x, y)
    assert logits.dtype == torch.bfloat16
    assert torch.isfinite(perte)
    perte.backward()
    assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in m.parameters())


@pytest.mark.gpu
def test_generation_sur_gpu_deterministe():
    m = Transformer(PETITE).to("cuda").eval()
    a = generer(m, [1, 2, 3], 10, graine=5)
    assert a == generer(m, [1, 2, 3], 10, graine=5)
    assert a != generer(m, [1, 2, 3], 10, graine=6)
