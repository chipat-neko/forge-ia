"""Tests du masque d'attention par document (plan 7, tâche 3).

Plusieurs conversations empaquetées dans une rangée ne doivent se voir qu'elles-mêmes. Tout
tourne sur le processeur, en float32, avec la configuration minuscule du test du modèle ;
le test `gpu` vérifie le chemin masqué en bf16 et note sa mémoire pour une rangée de 2 048
jetons du preset `tres_grand`.
"""

import pytest

try:
    import torch
except ImportError as erreur:
    raise ImportError(
        "PyTorch n'est pas installé. Lance les tests avec `uv run --extra gpu pytest -q`."
    ) from erreur

from forge.modele import PRESETS, ConfigModele, Transformer
from forge.modele.transformer import masque_des_documents

PETITE = ConfigModele(taille_vocabulaire=512, dim=64, couches=2, tetes=4, longueur_contexte=32)


def _modele() -> Transformer:
    torch.manual_seed(0)
    return Transformer(PETITE).eval()


def _rangee():
    """A (10 jetons), B (12 jetons), puis 10 de bourrage ; B seul, et les identifiants."""
    g = torch.Generator().manual_seed(1)
    a = torch.randint(0, 512, (10,), generator=g)
    b = torch.randint(0, 512, (12,), generator=g)
    ids = torch.cat([a, b, torch.zeros(10, dtype=torch.long)])[None]
    documents = torch.tensor([[0] * 10 + [1] * 12 + [-1] * 10])
    return ids, documents, b[None]


def test_masque_des_documents_vaut_la_matrice_attendue():
    m = masque_des_documents(torch.tensor([[0, 0, 1, -1]]))
    assert m.shape == (1, 1, 4, 4)
    assert m.dtype == torch.bool
    attendu = torch.tensor(
        [
            [True, False, False, False],
            [True, True, False, False],
            [False, False, True, False],
            [False, False, False, True],
        ]
    )
    assert torch.equal(m[0, 0], attendu)


def test_le_bourrage_ne_donne_pas_de_nan():
    m = _modele()
    ids, documents, _ = _rangee()
    logits, _ = m(ids, documents=documents)
    assert torch.isfinite(logits).all()


def test_un_document_ne_voit_que_lui_meme():
    m = _modele()
    ids, documents, b = _rangee()
    with torch.no_grad():
        masque, _ = m(ids, documents=documents)
        seul, _ = m(b)
    assert torch.allclose(masque[0, 10:22], seul[0], atol=1e-5)


def test_sans_masque_la_fuite_existe_et_se_mesure():
    m = _modele()
    ids, _, b = _rangee()
    with torch.no_grad():
        sans, _ = m(ids)
        seul, _ = m(b)
    ecart = (sans[0, 10:22] - seul[0]).abs().max().item()
    assert ecart > 1e-3


def test_documents_tous_a_zero_egale_sans_documents():
    m = _modele()
    x = torch.randint(0, 512, (2, 32))
    with torch.no_grad():
        avec, _ = m(x, documents=torch.zeros(2, 32, dtype=torch.long))
        sans, _ = m(x)
    assert torch.allclose(avec, sans, atol=1e-5)


@pytest.mark.gpu
def test_chemin_masque_en_bf16_sur_gpu_et_sa_memoire():
    torch.manual_seed(0)
    config = PRESETS["tres_grand"]
    modele = Transformer(config).to("cuda", torch.bfloat16)
    ids = torch.randint(0, config.taille_vocabulaire, (1, 2048), device="cuda")
    documents = torch.cat(
        [torch.full((700,), 0), torch.full((900,), 1), torch.full((448,), 2)]
    )[None].to("cuda")
    torch.cuda.reset_peak_memory_stats()
    logits, perte = modele(ids, ids, documents=documents)
    perte.backward()
    pic = torch.cuda.max_memory_allocated() / 2**30
    print(f"MEMOIRE_PIC_GO={pic:.2f}")
    assert torch.isfinite(logits.float()).all()
    assert torch.isfinite(perte)
