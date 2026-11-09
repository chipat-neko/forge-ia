"""Les volumes d'un dossier de jetons, lus sans rien écrire."""

import json

import pytest

from donnees_pas_a_pas.volumes import volumes


def fabriquer(dossier, train=1000, val=50, octets=4350, sans_fin=1000):
    """Un dossier de jetons factice : seuls `.complet` et `index.json` sont lus."""
    dossier.mkdir(parents=True)
    (dossier / ".complet").write_text(
        json.dumps({"jetons_train": train, "jetons_val": val, "octets_par_jeton": octets / sans_fin}), encoding="utf-8"
    )
    index = {
        "documents_train": 40,
        "documents_val": 2,
        "fichiers": {"train/fragment-00000.bin": 600, "train/fragment-00001.bin": 400, "val/fragment-00000.bin": 50},
        "jetons_sans_fin": sans_fin,
        "jetons_train": train,
        "jetons_val": val,
        "octets": octets,
        "provenance": {
            "fragment-00000": "code_python/fragment-00000.jsonl.gz",
            "fragment-00001": "code_python/fragment-00001.jsonl.gz",
            "fragment-00002": "web_fr/fragment-00000.jsonl.gz",
            "fragment-00003": "wikipedia_fr/fragment-00000.jsonl.gz",
        },
        "tokenizer": {"empreinte": "abc", "nom": "ton-ia-v1", "taille_vocabulaire": 32768},
        "version": 1,
    }
    (dossier / "index.json").write_text(json.dumps(index), encoding="utf-8")


def test_volumes(tmp_path):  # sur un dossier de jetons factice : .complet et index.json écrits dans le test
    fabriquer(tmp_path / "principal")
    v = volumes(tmp_path / "principal")
    assert v["jetons_train"] == 1000 and v["jetons_val"] == 50
    assert v["documents_train"] == 40 and v["documents_val"] == 2
    assert v["octets_par_jeton"] == 4.35
    # Les sources dans l'ordre du mélange, puis le total.
    assert list(v["fragments_par_source"]) == ["web_fr", "wikipedia_fr", "code_python"]
    assert v["fragments_par_source"] == {"web_fr": 1, "wikipedia_fr": 1, "code_python": 2}
    assert v["fragments"] == 4


def test_volumes_ne_modifie_rien(tmp_path):
    fabriquer(tmp_path / "principal")
    avant = {p.name: p.read_bytes() for p in (tmp_path / "principal").iterdir()}
    volumes(tmp_path / "principal")
    assert {p.name: p.read_bytes() for p in (tmp_path / "principal").iterdir()} == avant


def test_dossier_sans_complet(tmp_path):
    fabriquer(tmp_path / "principal")
    (tmp_path / "principal" / ".complet").unlink()
    with pytest.raises(FileNotFoundError, match="python -m forge encoder"):
        volumes(tmp_path / "principal")


def test_complet_et_index_ne_disent_pas_pareil(tmp_path):
    fabriquer(tmp_path / "principal")
    complet = json.loads((tmp_path / "principal" / ".complet").read_text(encoding="utf-8"))
    complet["jetons_train"] += 1
    (tmp_path / "principal" / ".complet").write_text(json.dumps(complet), encoding="utf-8")
    with pytest.raises(ValueError, match="ne disent pas la même chose"):
        volumes(tmp_path / "principal")
