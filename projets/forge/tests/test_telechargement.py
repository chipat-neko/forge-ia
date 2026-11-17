"""Reprise du téléchargement au fragment près, sur un vrai flux `datasets` (sans réseau).

Le flux se construit à partir de petits fichiers Parquet écrits dans `tmp_path` : le lecteur par
défaut (`lecteur_hugging_face`) est exercé pour de bon, `load_dataset` seul est détourné vers
ces fichiers.
"""

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from forge.donnees import telechargement
from forge.donnees.sources import Source
from forge.donnees.telechargement import telecharger

SOURCE = Source(
    nom="factice",
    depot="essai/factice",
    configuration=None,
    dossier_donnees=None,
    colonne="text",
    licence="aucune",
    url_licence="https://exemple.invalid/licence",
    garder=lambda ligne: True,
)
FICHIERS = 3
DOCS_PAR_FICHIER = 40
TOTAL = FICHIERS * DOCS_PAR_FICHIER
OCTETS_FRAGMENT = 3000  # environ 9 documents de 330 octets par fragment


def _texte(numero: int) -> str:
    return f"document {numero:04d} " + "x" * 300


@pytest.fixture
def parquets(tmp_path: Path) -> list[str]:
    """Trois fichiers Parquet de 40 documents, en groupes de 10 lignes."""
    dossier = tmp_path / "source"
    dossier.mkdir()
    chemins = []
    for f in range(FICHIERS):
        textes = [_texte(f * DOCS_PAR_FICHIER + i) for i in range(DOCS_PAR_FICHIER)]
        chemin = dossier / f"part-{f}.parquet"
        pq.write_table(pa.table({"text": textes}), chemin, row_group_size=10)
        chemins.append(str(chemin))
    return chemins


class Espion:
    """Entoure le vrai lecteur : compte les documents donnés, et coupe le « réseau » si on le dit."""

    def __init__(self, lecteur, coupe_apres: int | None) -> None:
        self.lecteur = lecteur
        self.coupe_apres = coupe_apres
        self.lus: list[str] = []

    def __iter__(self):
        for ligne in self.lecteur:
            if self.coupe_apres is not None and len(self.lus) == self.coupe_apres:
                raise ConnectionError("réseau coupé")
            self.lus.append(ligne["text"])
            yield ligne

    def etat(self):
        return self.lecteur.etat()

    def close(self):
        self.lecteur.close()


@pytest.fixture
def flux_parquet(monkeypatch, parquets):
    """Détourne `load_dataset` vers les fichiers Parquet ; renvoie les espions et les appels."""
    from datasets import load_dataset as vrai_load_dataset

    monkeypatch.setattr(
        "datasets.load_dataset",
        lambda *a, **k: vrai_load_dataset("parquet", data_files=parquets, split="train", streaming=True),
    )
    espions: list[Espion] = []
    appels: list[dict] = []
    vrai_lecteur = telechargement.lecteur_hugging_face
    coupures: list[int | None] = []

    def lecteur(source, etat_du_flux=None, ignorer=0):
        appels.append({"etat_du_flux": etat_du_flux, "ignorer": ignorer})
        espion = Espion(vrai_lecteur(source, etat_du_flux, ignorer), coupures.pop(0) if coupures else None)
        espions.append(espion)
        return espion

    monkeypatch.setattr(telechargement, "lecteur_hugging_face", lecteur)
    return espions, appels, coupures


def _fragments(dossier: Path) -> dict[str, bytes]:
    return {f.name: f.read_bytes() for f in sorted(dossier.glob("fragment-*.jsonl.gz"))}


def _etat(dossier: Path) -> dict:
    return json.loads((dossier / "etat.json").read_text(encoding="utf-8"))


def _telecharger(dossier: Path, messages: list[str] | None = None) -> None:
    telecharger(
        SOURCE, 10**10, dossier, octets_fragment=OCTETS_FRAGMENT,
        journal=messages.append if messages is not None else None,
    )


def _d_une_traite(tmp_path, flux_parquet) -> dict[str, bytes]:
    espions, _appels, _coupures = flux_parquet
    _telecharger(tmp_path / "reference")
    assert len(espions[-1].lus) == TOTAL
    return _fragments(tmp_path / "reference")


def test_la_reprise_repart_au_fragment_pres(tmp_path, flux_parquet):
    reference = _d_une_traite(tmp_path, flux_parquet)
    espions, appels, coupures = flux_parquet
    assert len(reference) > 5

    coupures.append(75)  # le réseau se coupe après 75 documents lus
    dossier = tmp_path / "essai"
    with pytest.raises(ConnectionError):
        _telecharger(dossier)
    etat = _etat(dossier)
    compte = etat["documents_lus"]
    assert 0 < compte <= 75 and etat["etat_du_flux"] is not None
    assert etat["fragments"] >= 1

    messages: list[str] = []
    _telecharger(dossier, messages)
    relance = espions[-1]
    # Aucun document déjà compté n'est relu : le flux repart juste après le dernier compté.
    assert appels[-1]["etat_du_flux"] is not None and appels[-1]["ignorer"] == compte
    assert relance.lus[0] == _texte(compte)
    assert len(relance.lus) == TOTAL - compte
    assert not any("ancien état" in m for m in messages)
    # Les fragments sont identiques, octet pour octet, à ceux d'un téléchargement d'une traite.
    assert _fragments(dossier) == reference
    assert (dossier / ".complet").exists()


def test_la_reprise_survit_a_plusieurs_coupures(tmp_path, flux_parquet):
    reference = _d_une_traite(tmp_path, flux_parquet)
    espions, _appels, coupures = flux_parquet
    dossier = tmp_path / "essai"
    for coupe in (20, 30, 15):
        coupures.append(coupe)
        with pytest.raises(ConnectionError):
            _telecharger(dossier)
    _telecharger(dossier)
    lus_en_tout = [t for espion in espions[1:] for t in espion.lus]
    assert _fragments(dossier) == reference
    # Chaque relance ne relit que ce qui n'était pas compté : jamais le début du flux.
    assert all(espion.lus[0] != _texte(0) for espion in espions[2:])
    assert len(lus_en_tout) < 2 * TOTAL


def test_un_ancien_etat_reprend_par_skip(tmp_path, flux_parquet):
    reference = _d_une_traite(tmp_path, flux_parquet)
    espions, appels, coupures = flux_parquet
    dossier = tmp_path / "ancien"
    coupures.append(75)
    with pytest.raises(ConnectionError):
        _telecharger(dossier)
    # Un etat.json d'avant cette version : pas de clé `etat_du_flux`.
    etat = _etat(dossier)
    compte = etat.pop("etat_du_flux")
    assert compte is not None
    (dossier / "etat.json").write_text(json.dumps(etat), encoding="utf-8")

    messages: list[str] = []
    _telecharger(dossier, messages)
    assert appels[-1] == {"etat_du_flux": None, "ignorer": etat["documents_lus"]}
    assert any("ancien état : le flux est relu depuis le début" in m for m in messages)
    assert espions[-1].lus[0] == _texte(etat["documents_lus"])
    assert _fragments(dossier) == reference
    assert _etat(dossier)["etat_du_flux"] is not None  # l'état du flux est de nouveau tenu


def test_un_etat_du_flux_refuse_n_ecrit_rien_de_faux(tmp_path, flux_parquet):
    espions, _appels, coupures = flux_parquet
    dossier = tmp_path / "refuse"
    coupures.append(75)
    with pytest.raises(ConnectionError):
        _telecharger(dossier)
    avant = _fragments(dossier)
    etat = _etat(dossier)
    etat["etat_du_flux"] = {"examples_iterable": {"shard_idx": "autre source", "shard_example_idx": -3}}
    (dossier / "etat.json").write_text(json.dumps(etat), encoding="utf-8")
    avant_etat = (dossier / "etat.json").read_bytes()

    with pytest.raises(RuntimeError) as erreur:
        _telecharger(dossier)
    message = str(erreur.value)
    assert "refuse" in message and "etat.json" in message
    assert "etat_du_flux" in message and "fragments" in message and "Rien n'a été écrit" in message
    # Rien n'a bougé : mêmes fragments, même etat.json, pas de marqueur.
    assert _fragments(dossier) == avant
    assert (dossier / "etat.json").read_bytes() == avant_etat
    assert not (dossier / ".complet").exists()


def test_etat_vaut_none_si_le_jeu_ne_sait_pas(monkeypatch):
    class JeuSansEtat:
        def __iter__(self):
            return iter([{"text": "a"}])

    monkeypatch.setattr("datasets.load_dataset", lambda *a, **k: JeuSansEtat())
    lecteur = telechargement.lecteur_hugging_face(SOURCE)
    assert lecteur.etat() is None
    assert list(lecteur) == [{"text": "a"}]
