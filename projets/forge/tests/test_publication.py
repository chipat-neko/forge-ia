"""Tests des versions publiées : exporter, recharger comme un lecteur, et télécharger sans réseau.

Le réseau est simulé : `urlretrieve` est remplacé par une copie depuis une fausse Release rangée
dans `tmp_path`. Le modèle est minuscule (celui de `test_exporter`).
"""

import hashlib
import io
import json
import socket
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

try:
    import torch
except ImportError as erreur:
    raise ImportError(
        "PyTorch n'est pas installé. Lance les tests avec `uv run --extra gpu pytest -q` "
        "(carte NVIDIA) ou `uv run --extra cpu pytest -q` (sans carte graphique)."
    ) from erreur

from test_exporter import CONFIG_TEST, ecrire_sauvegarde, etat_de_test

from forge import publication as module_publication
from forge.__main__ import main
from forge.exporter import EMPREINTE_DU_TOKENIZER, exporter
from forge.publication import (
    DEPOT,
    ETIQUETTES,
    VARIABLE_DES_VERSIONS,
    charger_publication,
    nom_des_poids,
    telecharger_fichiers,
    telecharger_publication,
)

pytestmark = pytest.mark.filterwarnings("ignore:Le tokenizer de .* n'a pas pu être vérifié")

ETIQUETTE = "ton-ia-9.9"
IDS = torch.randint(0, CONFIG_TEST.taille_vocabulaire, (2, CONFIG_TEST.longueur_contexte), generator=torch.Generator().manual_seed(1))


def publier(tmp_path: Path, dossier: str = "pub", etiquette: str = ETIQUETTE) -> tuple[Path, torch.nn.Module]:
    """Exporte un petit modèle sous le nom d'une version ; rend le dossier et le modèle d'origine."""
    etat, modele = etat_de_test(tmp_path)
    sauvegarde = ecrire_sauvegarde(tmp_path, etat)
    exporter(sauvegarde, tmp_path / dossier, nom_des_poids(etiquette))
    return tmp_path / dossier, modele


def test_noms_et_constantes():
    assert nom_des_poids("ton-ia-1.5") == "ton-ia-1.5.safetensors"
    assert DEPOT == "chipat-neko/forge-ia"
    assert ETIQUETTES == ("ton-ia-1.5", "ton-ia-1.7", "ton-ia-1.8", "ton-ia-1.9", "ton-ia-1.10")
    assert VARIABLE_DES_VERSIONS == "FORGE_IA_MODELES"


def test_aller_retour_d_une_publication(tmp_path):
    dossier, modele = publier(tmp_path)
    pub = charger_publication(dossier)
    attendu = modele.to(torch.bfloat16).float().eval()  # mêmes poids, passés par bf16 puis float32
    assert pub.version == ETIQUETTE and len(pub.empreinte_des_poids) == 64
    assert not pub.modele.training
    assert pub.modele.sortie.weight is pub.modele.plongement.weight  # le lien est rétabli
    assert all(p.dtype == torch.float32 for p in pub.modele.parameters())
    with torch.no_grad():
        assert torch.equal(pub.modele(IDS)[0], attendu(IDS)[0])
    assert pub.tokenizer.decoder(pub.tokenizer.encoder("Bonjour le monde")) == "Bonjour le monde"


def test_deux_fichiers_de_poids_refuses(tmp_path):
    dossier, _ = publier(tmp_path)
    (dossier / "autre.safetensors").write_bytes((dossier / nom_des_poids(ETIQUETTE)).read_bytes())
    with pytest.raises(ValueError) as erreur:
        charger_publication(dossier)
    assert "autre.safetensors" in str(erreur.value) and nom_des_poids(ETIQUETTE) in str(erreur.value)


def test_aucun_fichier_de_poids_et_fichiers_manquants(tmp_path):
    dossier, _ = publier(tmp_path)
    (dossier / "config.json").unlink()
    with pytest.raises(FileNotFoundError, match="config.json"):
        charger_publication(dossier)
    (dossier / nom_des_poids(ETIQUETTE)).unlink()
    with pytest.raises(FileNotFoundError, match="safetensors"):
        charger_publication(dossier)
    with pytest.raises(FileNotFoundError, match="n'existe pas"):
        charger_publication(tmp_path / "absent")


def test_tokenizer_change_refuse(tmp_path):
    dossier, _ = publier(tmp_path)
    with open(dossier / "tokenizer-ton-ia-v1.json", "ab") as fichier:
        fichier.write(b" ")
    with pytest.raises(ValueError) as erreur:
        charger_publication(dossier)
    assert EMPREINTE_DU_TOKENIZER in str(erreur.value)


def test_poids_illisibles_refuses(tmp_path):
    dossier, _ = publier(tmp_path)
    (dossier / nom_des_poids(ETIQUETTE)).write_bytes(b"pas un safetensors")
    with pytest.raises(ValueError, match="ne se lit pas"):
        charger_publication(dossier)


# --------------------------------------------------------------------------------------
# Le téléchargement, sans réseau
# --------------------------------------------------------------------------------------


@pytest.fixture
def fausse_release(tmp_path, monkeypatch):
    """Une Release factice : `urlretrieve` copie le fichier du nom demandé ; les appels sont notés."""
    release = tmp_path / "release"
    release.mkdir()
    for nom in (nom_des_poids(ETIQUETTE), "config.json", "tokenizer-ton-ia-v1.json"):
        (release / nom).write_bytes(nom.encode() * 100)
    appels: list[tuple[str, int | None]] = []
    etat = {"couper_au": None, "erreur": None, "api": "empreintes"}  # "empreintes" : les vraies ; sinon une réponse imposée

    def urlretrieve_simule(adresse, destination):
        appels.append((adresse, socket.getdefaulttimeout()))
        if etat["erreur"] is not None:
            raise etat["erreur"]
        if etat["couper_au"] == len(appels):
            Path(destination).write_bytes(b"debut seulement")  # un fichier à moitié écrit...
            raise URLError("connexion coupée")  # ...puis la coupure
        Path(destination).write_bytes((release / adresse.rsplit("/", 1)[1]).read_bytes())

    def urlopen_simule(adresse, timeout=None):
        """L'API des Releases : un champ `digest` par fichier, ou la réponse que le test impose."""
        assert adresse == f"https://api.github.com/repos/{DEPOT}/releases/tags/{ETIQUETTE}"
        if isinstance(etat["api"], BaseException):
            raise etat["api"]
        if etat["api"] == "empreintes":
            fichiers = [
                {"name": f.name, "digest": "sha256:" + hashlib.sha256(f.read_bytes()).hexdigest()} for f in release.iterdir()
            ]
        else:
            fichiers = etat["api"]
        return io.BytesIO(json.dumps({"assets": fichiers}).encode())

    monkeypatch.setattr(module_publication, "urlretrieve", urlretrieve_simule)
    monkeypatch.setattr(module_publication, "urlopen", urlopen_simule)
    monkeypatch.delenv(VARIABLE_DES_VERSIONS, raising=False)
    return appels, etat, release


def test_telechargement_coupe_puis_repris(tmp_path, fausse_release):
    appels, etat, release = fausse_release
    cible = tmp_path / "telecharge"
    etat["couper_au"] = 2  # le 2e fichier est coupé
    with pytest.raises(ConnectionError, match="elance la même commande"):
        telecharger_publication(ETIQUETTE, cible)
    assert sorted(p.name for p in cible.iterdir()) == [nom_des_poids(ETIQUETTE)]  # aucun fichier final à moitié écrit, aucun .partiel
    avant = len(appels)
    etat["couper_au"] = None
    assert telecharger_publication(ETIQUETTE, cible) == cible
    adresses = [adresse for adresse, _ in appels[avant:]]
    assert adresses == [
        f"https://github.com/{DEPOT}/releases/download/{ETIQUETTE}/config.json",
        f"https://github.com/{DEPOT}/releases/download/{ETIQUETTE}/tokenizer-ton-ia-v1.json",
    ]  # seul ce qui manquait
    assert sorted(p.name for p in cible.iterdir()) == sorted(p.name for p in release.iterdir())
    assert len(appels) == avant + 2
    telecharger_publication(ETIQUETTE, cible)
    assert len(appels) == avant + 2  # tout est complet : rien à retélécharger


def test_delai_du_socket_pose_puis_rendu(tmp_path, fausse_release):
    appels, _, _ = fausse_release
    avant = socket.getdefaulttimeout()
    telecharger_fichiers(ETIQUETTE, ["config.json"], tmp_path / "t")
    assert appels[0][1] == 60
    assert socket.getdefaulttimeout() == avant


def test_dossier_par_defaut_sous_forge_donnees(tmp_path, fausse_release, monkeypatch):
    monkeypatch.setenv("FORGE_DONNEES", str(tmp_path / "donnees"))
    cible = telecharger_fichiers(ETIQUETTE, ["config.json"])
    assert cible == tmp_path / "donnees" / "publications" / ETIQUETTE
    assert (cible / "config.json").is_file()


def test_variable_des_versions(tmp_path, fausse_release, monkeypatch):
    appels, _, _ = fausse_release
    local = tmp_path / "modeles" / ETIQUETTE
    local.mkdir(parents=True)
    (local / "config.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv(VARIABLE_DES_VERSIONS, str(tmp_path / "modeles"))
    assert telecharger_fichiers(ETIQUETTE, ["config.json"], tmp_path / "ailleurs") == local
    with pytest.raises(FileNotFoundError, match="manque tokenizer-ton-ia-v1.json"):
        telecharger_fichiers(ETIQUETTE, ["config.json", "tokenizer-ton-ia-v1.json"])
    with pytest.raises(FileNotFoundError, match="n'existe pas"):
        telecharger_fichiers("ton-ia-0.0", ["config.json"])
    assert appels == []  # aucun appel réseau
    assert not (tmp_path / "ailleurs").exists()


def test_publication_telechargee_se_charge(tmp_path, fausse_release, monkeypatch):
    """Le dossier de `FORGE_IA_MODELES` sert directement à `charger_publication`."""
    dossier, _ = publier(tmp_path, dossier=f"modeles/{ETIQUETTE}")
    monkeypatch.setenv(VARIABLE_DES_VERSIONS, str(tmp_path / "modeles"))
    assert charger_publication(telecharger_publication(ETIQUETTE)).version == ETIQUETTE


def test_sous_commande_publication(tmp_path, fausse_release, capsys):
    cible = tmp_path / "t"
    assert main(["publication", "--etiquette", ETIQUETTE, "--dossier", str(cible)]) == 0
    sortie = capsys.readouterr().out
    for nom in (nom_des_poids(ETIQUETTE), "config.json", "tokenizer-ton-ia-v1.json"):
        assert nom in sortie
    assert "SHA-256" in sortie and "octets" in sortie


def test_sous_commande_publication_erreur_en_francais(tmp_path, fausse_release, capsys):
    _, etat, _ = fausse_release
    etat["couper_au"] = 1
    assert main(["publication", "--etiquette", ETIQUETTE, "--dossier", str(tmp_path / "t")]) == 1
    erreur = capsys.readouterr().err
    assert erreur.startswith("Erreur : ") and "elance la même commande" in erreur and "Traceback" not in erreur


def test_404_dit_que_l_etiquette_ou_le_fichier_est_introuvable(tmp_path, fausse_release):
    _, etat, _ = fausse_release
    etat["erreur"] = HTTPError("https://github.com/x", 404, "Not Found", {}, None)
    with pytest.raises(FileNotFoundError) as erreur:
        telecharger_publication(ETIQUETTE, tmp_path / "t")
    message = str(erreur.value)
    assert "ne trouve pas" in message and ETIQUETTE in message and "ton-ia-1.5" in message  # nomme les étiquettes connues
    assert "connexion" not in message  # ce n'est pas un problème de réseau
    assert not list((tmp_path / "t").iterdir())


def test_sans_reseau_dit_de_verifier_la_connexion(tmp_path, fausse_release):
    _, etat, _ = fausse_release
    etat["erreur"] = URLError(socket.gaierror(11001, "getaddrinfo failed"))
    with pytest.raises(ConnectionError) as erreur:
        telecharger_publication(ETIQUETTE, tmp_path / "t")
    message = str(erreur.value)
    assert "connexion" in message and VARIABLE_DES_VERSIONS in message and "elance" in message
    assert "ne trouve pas" not in message
    assert not list((tmp_path / "t").iterdir())


def test_erreur_du_serveur_dit_de_reessayer(tmp_path, fausse_release):
    _, etat, _ = fausse_release
    etat["erreur"] = HTTPError("https://github.com/x", 503, "Unavailable", {}, None)
    with pytest.raises(ConnectionError, match="503.*Relance"):
        telecharger_publication(ETIQUETTE, tmp_path / "t")


def test_empreinte_differente_refusee_et_effacee(tmp_path, fausse_release):
    _, etat, _ = fausse_release
    etat["api"] = [{"name": "config.json", "digest": "sha256:" + "0" * 64}]
    cible = tmp_path / "t"
    with pytest.raises(ValueError) as erreur:
        telecharger_fichiers(ETIQUETTE, ["config.json"], cible)
    assert "0" * 64 in str(erreur.value) and "effacé" in str(erreur.value)
    assert list(cible.iterdir()) == []  # ni fichier final, ni .partiel


def test_empreinte_conforme_acceptee(tmp_path, fausse_release):
    telecharger_publication(ETIQUETTE, tmp_path / "t")  # l'API simulée donne les vraies empreintes
    assert (tmp_path / "t" / "config.json").is_file()


@pytest.mark.parametrize(
    "api",
    [[{"name": "config.json"}], [{"name": "config.json", "digest": None}], OSError("pas de réseau"), HTTPError("u", 403, "limite", {}, None)],
)
def test_sans_empreinte_de_l_api_le_telechargement_a_lieu(tmp_path, fausse_release, api):
    _, etat, _ = fausse_release
    etat["api"] = api
    telecharger_fichiers(ETIQUETTE, ["config.json"], tmp_path / "t")
    assert (tmp_path / "t" / "config.json").is_file()


def test_sous_commande_publication_ctrl_c(tmp_path, fausse_release, capsys):
    _, etat, _ = fausse_release
    etat["erreur"] = KeyboardInterrupt()
    cible = tmp_path / "t"
    assert main(["publication", "--etiquette", ETIQUETTE, "--dossier", str(cible)]) == 130
    assert "interrompu" in capsys.readouterr().err
    assert list(cible.iterdir()) == []
