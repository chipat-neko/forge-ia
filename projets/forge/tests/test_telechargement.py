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


def _installer_flux(monkeypatch, chemins):
    """Détourne `load_dataset` vers ces fichiers Parquet ; renvoie les espions, les appels, les coupures."""
    from datasets import load_dataset as vrai_load_dataset

    monkeypatch.setattr(
        "datasets.load_dataset",
        lambda *a, **k: vrai_load_dataset("parquet", data_files=chemins, split="train", streaming=True),
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


@pytest.fixture
def flux_parquet(monkeypatch, parquets):
    return _installer_flux(monkeypatch, parquets)


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
    # Aucun document déjà compté n'est relu : le flux repart juste après le dernier compté, sans saut.
    assert appels[-1]["etat_du_flux"] is not None and appels[-1]["ignorer"] == 0
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
    comptes = [0]
    relus = 0  # documents lus puis perdus par une coupure : ceux du fragment non terminé
    for coupe in (20, 30, 15):
        coupures.append(coupe)
        with pytest.raises(ConnectionError):
            _telecharger(dossier)
        comptes.append(_etat(dossier)["documents_lus"])
        relus += coupe - (comptes[-1] - comptes[-2])
    _telecharger(dossier)
    assert _fragments(dossier) == reference
    # Chaque relance ne relit que ce qui n'était pas compté : le total exact, ni plus ni moins.
    assert sum(len(espion.lus) for espion in espions[1:]) == TOTAL + relus
    assert all(espion.lus[0] != _texte(0) for espion in espions[2:])


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


# Les clés d'un etat.json écrit avant le plan 6 : ni `etat_du_flux`, ni rien de ce qui l'accompagne.
_CLES_D_UN_ANCIEN_ETAT = ("documents_lus", "octets_ecrits", "fragments", "empreintes", "source_epuisee")


def test_un_ancien_etat_survit_a_plusieurs_reprises(tmp_path, flux_parquet):
    """Un téléchargement d'avant le plan 6 : une reprise par `skip`, puis d'autres par l'état du flux."""
    reference = _d_une_traite(tmp_path, flux_parquet)
    espions, appels, coupures = flux_parquet
    dossier = tmp_path / "ancien"
    coupures.append(25)
    with pytest.raises(ConnectionError):
        _telecharger(dossier)
    ancien = {cle: valeur for cle, valeur in _etat(dossier).items() if cle in _CLES_D_UN_ANCIEN_ETAT}
    (dossier / "etat.json").write_text(json.dumps(ancien), encoding="utf-8")
    comptes = [ancien["documents_lus"]]
    assert comptes[0] > 0

    # Première reprise : l'ancienne voie (relecture et saut), coupée à son tour.
    messages: list[str] = []
    coupures.append(30)
    with pytest.raises(ConnectionError):
        _telecharger(dossier, messages)
    assert appels[-1] == {"etat_du_flux": None, "ignorer": comptes[0]}
    assert any("ancien état" in m for m in messages)
    comptes.append(_etat(dossier)["documents_lus"])
    assert comptes[1] > comptes[0] and _etat(dossier)["etat_du_flux"] is not None

    # Deuxième et troisième reprises : par l'état du flux, sans relire le début ni refuser l'état.
    for coupe in (30, None):
        messages = []
        coupures.append(coupe)
        if coupe is None:
            _telecharger(dossier, messages)
        else:
            with pytest.raises(ConnectionError):
                _telecharger(dossier, messages)
        assert appels[-1]["etat_du_flux"] is not None
        assert not any("ancien état" in m for m in messages)
        assert espions[-1].lus[0] == _texte(comptes[-1])
        comptes.append(_etat(dossier)["documents_lus"])
    assert comptes[-1] == TOTAL
    # Les fragments sont identiques, octet pour octet, à ceux d'un téléchargement d'une traite.
    assert _fragments(dossier) == reference
    assert (dossier / ".complet").exists()


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

    with pytest.raises(telechargement.EtatDuFluxRefuse) as erreur:
        _telecharger(dossier)
    message = str(erreur.value)
    assert isinstance(erreur.value, telechargement.EtatDuFluxRefuse)
    assert "refuse" in message and "etat.json" in message
    assert "etat_du_flux" in message and "échouera de nouveau" in message
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


# --- Documents écartés et plafond d'octets, sur un vrai flux Parquet ----------------------
#
# Motif de 13 documents : 9 gardés, 1 trop court, 1 gardé (le 10e, qui ferme le fragment de
# 3000 octets), puis 1 trop court et 1 doublon juste après la frontière.


def _documents_melanges() -> list[str]:
    textes: list[str] = []
    gardes: list[str] = []
    for position in range(TOTAL):
        place = position % 13
        if place in (9, 11):
            textes.append(f"court {position}")
        elif place == 12 and gardes:
            textes.append(gardes[0])  # doublon d'un texte déjà gardé
        else:
            texte = _texte(position)
            textes.append(texte)
            gardes.append(texte)
    return textes


def _textes_ecrits(dossier: Path) -> list[str]:
    import gzip

    textes = []
    for fragment in sorted(dossier.glob("fragment-*.jsonl.gz")):
        with gzip.open(fragment, "rt", encoding="utf-8") as fichier:
            textes.extend(json.loads(ligne)["texte"] for ligne in fichier)
    return textes


@pytest.fixture
def flux_melange(tmp_path, monkeypatch):
    textes = _documents_melanges()
    dossier = tmp_path / "melange"
    dossier.mkdir()
    chemins = []
    for f in range(FICHIERS):
        morceau = textes[f * DOCS_PAR_FICHIER : (f + 1) * DOCS_PAR_FICHIER]
        chemin = dossier / f"part-{f}.parquet"
        pq.write_table(pa.table({"text": morceau}), chemin, row_group_size=10)
        chemins.append(str(chemin))
    attendus = list(dict.fromkeys(t for t in textes if len(t) >= 200))
    return textes, attendus, *_installer_flux(monkeypatch, chemins)


@pytest.mark.parametrize("coupe", [9, 10, 11, 12, 13, 14, 24, 25, 26, 27])
def test_coupure_autour_de_la_frontiere_avec_des_documents_ecartes(tmp_path, flux_melange, coupe):
    textes, attendus, espions, _appels, coupures = flux_melange
    _telecharger(tmp_path / "reference")
    reference = _fragments(tmp_path / "reference")
    assert _textes_ecrits(tmp_path / "reference") == attendus
    assert len(reference) > 5

    dossier = tmp_path / "essai"
    coupures.append(coupe)
    with pytest.raises(ConnectionError):
        _telecharger(dossier)
    compte = _etat(dossier)["documents_lus"] if (dossier / "etat.json").exists() else 0
    _telecharger(dossier)
    # Aucun document compté n'est relu, et le flux reprend au document suivant, écarté ou non.
    assert espions[-1].lus == textes[compte:]
    assert _fragments(dossier) == reference
    assert _textes_ecrits(dossier) == attendus


@pytest.mark.parametrize("plafond", [9500, 15000])
def test_plafond_au_milieu_d_un_fragment_puis_plafond_releve(tmp_path, flux_melange, plafond):
    textes, attendus, espions, _appels, _coupures = flux_melange
    _telecharger(tmp_path / "reference")
    reference = _fragments(tmp_path / "reference")

    dossier = tmp_path / "plafond"
    telecharger(SOURCE, plafond, dossier, octets_fragment=OCTETS_FRAGMENT)
    etat = _etat(dossier)
    assert (dossier / ".complet").exists() and not etat["source_epuisee"]
    assert plafond <= etat["octets_ecrits"] < plafond + 400  # le dernier document peut dépasser
    assert 0 < len(_textes_ecrits(dossier)) < len(attendus)
    dernier = len(_fragments(dossier)) - 1
    assert len(_textes_ecrits(dossier)) % 10 != 0  # le plafond tombe bien au milieu d'un fragment

    compte = etat["documents_lus"]
    _telecharger(dossier)  # plafond relevé : on prolonge le dossier déjà complet
    assert espions[-1].lus == textes[compte:]  # aucun document compté n'est relu
    assert _textes_ecrits(dossier) == attendus
    # Le fragment fermé au plafond reste plus court : ceux d'avant sont identiques à la traite.
    ecrits = _fragments(dossier)
    assert all(ecrits[nom] == reference[nom] for nom in list(reference)[:dernier])
    assert (dossier / ".complet").exists() and _etat(dossier)["source_epuisee"]


def test_la_commande_donnees_ne_dit_pas_de_relancer_apres_un_etat_refuse(monkeypatch, capsys):
    from forge.__main__ import main

    def refuse(*args, **kwargs):
        raise telechargement.EtatDuFluxRefuse("le jeu refuse l'état ; retire la ligne `etat_du_flux`.")

    monkeypatch.setattr(telechargement, "telecharger", refuse)
    assert main(["donnees", "--octets", "1M", "--dossier", "essai"]) == 1
    erreur = capsys.readouterr().err
    assert "retire la ligne `etat_du_flux`" in erreur
    assert "relance la même commande" not in erreur and "Traceback" not in erreur
