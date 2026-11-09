"""L'aperçu : les comptes d'une lecture en flux, sans réseau (un lecteur factice)."""

import os

from donnees_pas_a_pas.__main__ import lever_le_mode_hors_ligne
from donnees_pas_a_pas.apercu import apercu, en_octets


def lecteur_factice(source):
    """Des documents de plus de 200 caractères, dont certains trop courts, doublons ou à écarter."""
    for i in range(1000):
        if source.nom == "code_python":
            licence = "mit" if i % 2 == 0 else "gpl-3.0"
            yield {"code": f"x = {i}\n" * 60, "language": "Python", "license": licence}
        else:
            yield {"text": f"Document numéro {i}. " * 20}
            if i % 10 == 0:
                yield {"text": "court"}
                yield {"text": f"Document numéro {i}. " * 20}


def test_apercu_compte_sans_garder_de_texte():
    r = apercu(10_000, lecteur=lecteur_factice)
    assert list(r) == ["web_fr", "wikipedia_fr", "code_python"]
    web = r["web_fr"]
    assert set(web) == {"lus", "gardes", "raisons", "octets_gardes", "en_validation", "secondes"}
    assert 10_000 <= web["octets_gardes"] < 10_000 + 1000
    assert sum(web["raisons"].values()) == web["lus"]
    assert web["raisons"]["gardé"] == web["gardes"]
    assert web["raisons"]["trop court"] > 0 and web["raisons"]["doublon"] > 0
    assert 0 <= web["en_validation"] <= web["gardes"]
    code = r["code_python"]
    assert code["raisons"]["licence"] > 0 and code["raisons"]["langage"] == 0
    # Rien d'autre que des nombres : aucun texte n'est gardé.
    for source in r.values():
        assert all(isinstance(v, (int, float, dict)) for v in source.values())


def test_apercu_s_arrete_quand_la_source_est_epuisee():
    r = apercu(10**9, lecteur=lecteur_factice)
    assert r["code_python"]["lus"] == 1000


def test_taille_en_octets():
    assert en_octets("5M") == 5 * 1024**2
    assert en_octets("300k") == 300 * 1024
    assert en_octets("1000") == 1000


def test_le_mode_hors_ligne_est_leve_pour_la_commande(monkeypatch, capsys):
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("HF_DATASETS_OFFLINE", "0")
    lever_le_mode_hors_ligne()
    assert os.environ["HF_HUB_OFFLINE"] == "0" and os.environ["HF_DATASETS_OFFLINE"] == "0"
    assert "HF_HUB_OFFLINE est à 1" in capsys.readouterr().err
