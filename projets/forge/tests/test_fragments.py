"""Les sorties par fragments (`forge.fichiers`-style : atomiques, reprises) et la pause par Ctrl+C."""

import gzip
import json
import signal
import threading
from pathlib import Path

import pytest

from forge.erreurs import DonneesManquantes
from forge.fragments import SortieParFragments, lire_elements
from forge.pause import Pause


def _elements(n: int, debut: int = 0) -> list[dict]:
    return [{"numero": i, "texte": f"élément {i}"} for i in range(debut, debut + n)]


def _ecrire(sortie: SortieParFragments, elements: list[dict]) -> None:
    for element in elements:
        sortie.ajouter(element)
        if sortie.plein:
            sortie.valider()


def test_les_fragments_se_relisent_dans_l_ordre(tmp_path):
    sortie = SortieParFragments(tmp_path, "paires", par_fragment=3)
    _ecrire(sortie, _elements(8))
    sortie.valider()  # le reste (2 éléments)
    assert sorted(f.name for f in tmp_path.glob("paires-*.jsonl.gz")) == [
        "paires-00000.jsonl.gz",
        "paires-00001.jsonl.gz",
        "paires-00002.jsonl.gz",
    ]
    assert sortie.deja == 8
    assert list(lire_elements(tmp_path, "paires")) == _elements(8)
    with gzip.open(tmp_path / "paires-00000.jsonl.gz", "rt", encoding="utf-8") as f:
        assert [json.loads(ligne)["numero"] for ligne in f] == [0, 1, 2]


def test_a_l_ouverture_un_tmp_et_un_fragment_de_trop_sont_effaces(tmp_path):
    sortie = SortieParFragments(tmp_path, "paires", par_fragment=3)
    _ecrire(sortie, _elements(7))  # deux fragments validés, un élément en attente
    assert sortie.deja == 6
    # Un plantage : un fragment écrit mais jamais compté par etat.json, et un .tmp resté.
    (tmp_path / "paires-00002.jsonl.gz").write_bytes(b"fragment orphelin")
    (tmp_path / "paires-00003.jsonl.gz.tmp").write_bytes(b"a moitie")
    (tmp_path / "etat.json.tmp").write_text("{", encoding="utf-8")
    (tmp_path / "autre-00009.jsonl.gz").write_bytes(b"d'un autre prefixe")

    rouverte = SortieParFragments(tmp_path, "paires", par_fragment=3)
    assert rouverte.deja == 6
    assert not (tmp_path / "paires-00002.jsonl.gz").exists()
    assert list(tmp_path.glob("*.tmp")) == []
    assert (tmp_path / "autre-00009.jsonl.gz").exists()  # un autre préfixe n'est pas touché
    # La suite reprend au bon numéro, sans doublon.
    _ecrire(rouverte, _elements(5, debut=6))
    rouverte.valider()
    assert list(lire_elements(tmp_path, "paires")) == _elements(11)


def test_l_etat_de_l_appelant_est_garde_avec_le_fragment(tmp_path):
    sortie = SortieParFragments(tmp_path, "p", par_fragment=2)
    assert sortie.etat is None
    sortie.ajouter({"a": 1})
    sortie.ajouter({"a": 2})
    sortie.valider({"position": 12, "liste": [1, 2]})
    assert SortieParFragments(tmp_path, "p", par_fragment=2).etat == {"position": 12, "liste": [1, 2]}
    assert json.loads((tmp_path / "etat.json").read_text(encoding="utf-8"))["elements"] == 2


def test_terminer_pose_complet_avec_les_infos(tmp_path):
    sortie = SortieParFragments(tmp_path, "p", par_fragment=10)
    _ecrire(sortie, _elements(4))
    assert not sortie.complet
    sortie.terminer({"nom": "essai", "gardes": 4})  # le reste du tampon est validé aussi
    assert json.loads((tmp_path / ".complet").read_text(encoding="utf-8")) == {"nom": "essai", "gardes": 4}
    rouverte = SortieParFragments(tmp_path, "p", par_fragment=10)
    assert rouverte.complet and rouverte.infos == {"nom": "essai", "gardes": 4}
    assert list(lire_elements(tmp_path, "p")) == _elements(4)


def test_un_fragment_compte_qui_manque_est_signale(tmp_path):
    sortie = SortieParFragments(tmp_path, "p", par_fragment=2)
    _ecrire(sortie, _elements(4))
    (tmp_path / "p-00001.jsonl.gz").unlink()
    with pytest.raises(DonneesManquantes, match="p-00001.jsonl.gz"):
        list(lire_elements(tmp_path, "p"))
    with pytest.raises(DonneesManquantes, match="p-00001.jsonl.gz"):
        SortieParFragments(tmp_path, "p", par_fragment=2)


def test_un_etat_illisible_dit_quoi_faire(tmp_path):
    (tmp_path / "etat.json").write_text("{pas du json", encoding="utf-8")
    with pytest.raises(RuntimeError, match="Supprime le dossier"):
        SortieParFragments(tmp_path, "p")


def test_un_element_qui_ne_s_ecrit_pas_en_json_est_refuse_tout_de_suite(tmp_path):
    sortie = SortieParFragments(tmp_path, "p", par_fragment=2)
    sortie.ajouter({"a": 1})
    with pytest.raises(TypeError):
        sortie.ajouter({"a": {1, 2}})  # un ensemble ne s'écrit pas en JSON
    assert sortie.en_attente == 1


def test_une_ecriture_qui_echoue_ne_laisse_ni_tmp_ni_compte_et_se_reessaie(tmp_path, monkeypatch):
    import forge.fragments as modulefragments

    sortie = SortieParFragments(tmp_path, "p", par_fragment=2)
    sortie.ajouter({"a": 1})
    sortie.ajouter({"a": 2})
    vraie = modulefragments.ecrire_atomique

    def disque_plein(chemin, ecrire, **options):
        raise OSError("disque plein")

    monkeypatch.setattr(modulefragments, "ecrire_atomique", disque_plein)
    with pytest.raises(OSError, match="disque plein"):
        sortie.valider({"position": 1})
    assert sortie.deja == 0 and sortie.en_attente == 2 and sortie.etat is None
    assert list(tmp_path.glob("p-*")) == []
    monkeypatch.setattr(modulefragments, "ecrire_atomique", vraie)
    sortie.valider({"position": 1})  # le même tampon s'écrit au second essai
    assert list(lire_elements(tmp_path, "p")) == [{"a": 1}, {"a": 2}]
    assert SortieParFragments(tmp_path, "p").etat == {"position": 1}


def test_un_arret_entre_le_fragment_et_l_etat_ne_compte_pas_le_fragment(tmp_path, monkeypatch):
    import forge.fragments as modulefragments

    sortie = SortieParFragments(tmp_path, "p", par_fragment=2)
    sortie.ajouter({"a": 1})
    sortie.ajouter({"a": 2})
    sortie.valider()
    sortie.ajouter({"a": 3})
    vraie = modulefragments._ecrire_json
    monkeypatch.setattr(modulefragments, "_ecrire_json", lambda *a, **k: (_ for _ in ()).throw(OSError("coupure")))
    with pytest.raises(OSError):
        sortie.valider()
    monkeypatch.setattr(modulefragments, "_ecrire_json", vraie)
    assert (tmp_path / "p-00001.jsonl.gz").exists()  # écrit, mais pas compté
    rouverte = SortieParFragments(tmp_path, "p", par_fragment=2)
    assert rouverte.deja == 2 and not (tmp_path / "p-00001.jsonl.gz").exists()
    assert list(lire_elements(tmp_path, "p")) == [{"a": 1}, {"a": 2}]


# --- La pause -----------------------------------------------------------------------------------


def test_la_pause_vient_de_forge_pause_et_la_boucle_l_importe():
    from forge.entrainement import boucle

    assert boucle._Pause is Pause


def test_le_premier_signal_leve_le_drapeau_le_second_arrete():
    ancien = signal.getsignal(signal.SIGINT)
    with Pause() as pause:
        assert not pause.demandee
        pause._signal_recu(signal.SIGINT, None)
        assert pause.demandee
        with pytest.raises(KeyboardInterrupt):
            pause._signal_recu(signal.SIGINT, None)
    assert signal.getsignal(signal.SIGINT) is ancien  # le gestionnaire d'avant est remis


def test_la_pause_peut_dire_son_travail(capsys):
    with Pause(en_cours="le fragment en cours", sauvegarde="je valide ce fragment") as pause:
        pause._signal_recu(signal.SIGINT, None)
    sortie = capsys.readouterr().out
    assert "je finis le fragment en cours, je valide ce fragment" in sortie


def test_hors_du_fil_principal_aucun_gestionnaire_n_est_pose():
    ancien = signal.getsignal(signal.SIGINT)
    vu: list[object] = []

    def travail():
        with Pause():
            vu.append(signal.getsignal(signal.SIGINT))

    fil = threading.Thread(target=travail)
    fil.start()
    fil.join()
    assert vu == [ancien]
