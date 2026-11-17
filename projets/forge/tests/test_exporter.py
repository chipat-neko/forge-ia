"""Tests de l'export de « ton IA » : poids en safetensors (bf16), configuration et tokenizer.

Tout tourne sur le processeur, avec un `Transformer` minuscule (vocabulaire de 322 jetons) dont
la sauvegarde a exactement la forme de celles de l'entraînement (`_etat_du_modele`, écrite par
`sauvegarder`). Le rechargement des tests fait ce que fera le chargeur du plan 5
(`charger_ton_ia`) : `config.json` vers `ConfigModele(**config)`, puis les poids (s'il manque
celui de la sortie, il prend celui du plongement).
"""

import hashlib
import json
import struct
from pathlib import Path

import pytest

try:
    import torch
except ImportError as erreur:
    raise ImportError(
        "PyTorch n'est pas installé. Lance les tests avec `uv run --extra gpu pytest -q` "
        "(carte NVIDIA) ou `uv run --extra cpu pytest -q` (sans carte graphique)."
    ) from erreur
from safetensors import safe_open
from safetensors.torch import load_file

from forge import exporter as module_exporter
from forge.__main__ import main
from forge.entrainement import ConfigEntrainement, sauvegarder
from forge.donnees.jetons import empreinte_du_tokenizer
from forge.entrainement.boucle import _etat_du_modele
from forge.exporter import EMPREINTE_DU_TOKENIZER, NOM_DES_POIDS, exporter
from forge.modele import ConfigModele, Transformer
from forge.tokenizer.bpe_octets import TokenizerOctets

# Les sauvegardes de test n'ont pas de jetons à côté : l'avertissement « tokenizer non vérifié » est attendu.
pytestmark = pytest.mark.filterwarnings("ignore:Le tokenizer de .* n'a pas pu être vérifié")

CONFIG_TEST = ConfigModele(taille_vocabulaire=322, dim=32, couches=2, tetes=2, longueur_contexte=16)
TOKENIZER_DU_DEPOT = Path(__file__).resolve().parents[1] / "forge" / "ressources" / "tokenizer-ton-ia-v1.json"


def etat_de_test(tmp_path: Path, pas: int = 7) -> tuple[dict, Transformer]:
    """Une sauvegarde de `meilleur.pt` comme celles de l'entraînement, et le modèle d'où elle vient."""
    torch.manual_seed(0)
    modele = Transformer(CONFIG_TEST)
    config = ConfigEntrainement(
        preset=CONFIG_TEST,
        donnees=str(tmp_path / "jetons"),
        jetons_total=32 * 6,
        taille_lot_jetons=32,
        micro_lot=2,
        taux_max=1e-2,
        echauffement=2,
        evaluation_tous_pas=2,
        appareil="cpu",
        compiler="non",
        sortie=str(tmp_path / "entrainement"),
    )
    return {**_etat_du_modele(config, modele, pas), "perte_val": 3.5}, modele


def ecrire_sauvegarde(tmp_path: Path, etat: dict) -> Path:
    return sauvegarder(tmp_path / "entrainement" / "sauvegardes", etat, "meilleur.pt")


@pytest.fixture
def sauvegarde_test(tmp_path) -> tuple[Path, Transformer]:
    etat, modele = etat_de_test(tmp_path)
    return ecrire_sauvegarde(tmp_path, etat), modele


def recharger(dossier: Path, nom_des_poids: str = NOM_DES_POIDS) -> Transformer:
    """Ce que fera `charger_ton_ia` : la configuration, puis les poids, le lien de la sortie rétabli."""
    config = ConfigModele(**json.loads((dossier / "config.json").read_text(encoding="utf-8")))
    poids = load_file(dossier / nom_des_poids)
    if "sortie.weight" not in poids:
        poids["sortie.weight"] = poids["plongement.weight"]
    modele = Transformer(config)
    modele.load_state_dict(poids)
    return modele


def sha256(chemin: Path) -> str:
    return hashlib.sha256(chemin.read_bytes()).hexdigest()


# --------------------------------------------------------------------------------------
# Les trois fichiers
# --------------------------------------------------------------------------------------


def test_exporter_ecrit_les_trois_fichiers(tmp_path, sauvegarde_test):
    sauvegarde, _ = sauvegarde_test
    ecrits = exporter(sauvegarde, tmp_path / "publication")
    noms = {"ton-ia-1.5.safetensors", "config.json", "tokenizer-ton-ia-v1.json"}
    assert {chemin.name for chemin in ecrits} == noms
    assert {chemin.name for chemin in (tmp_path / "publication").iterdir()} == noms  # aucun .tmp laissé


def test_la_configuration_reconstruit_le_modele(tmp_path, sauvegarde_test):
    sauvegarde, _ = sauvegarde_test
    exporter(sauvegarde, tmp_path / "publication")
    texte = (tmp_path / "publication" / "config.json").read_bytes()
    assert b"\r\n" not in texte and texte.endswith(b"\n")
    config = json.loads(texte)
    assert config == {
        "taille_vocabulaire": 322,
        "dim": 32,
        "couches": 2,
        "tetes": 2,
        "longueur_contexte": 16,
        "base_rope": 10000.0,
    }
    assert ConfigModele(**config) == CONFIG_TEST


def test_les_poids_sont_en_bf16_sans_la_sortie_liee(tmp_path, sauvegarde_test):
    sauvegarde, modele = sauvegarde_test
    exporter(sauvegarde, tmp_path / "publication")
    poids = load_file(tmp_path / "publication" / NOM_DES_POIDS)
    # La sortie est la même matrice que le plongement : safetensors refuse les tenseurs partagés.
    assert set(poids) == set(modele.state_dict()) - {"sortie.weight"}
    assert all(tenseur.dtype == torch.bfloat16 for tenseur in poids.values())
    for nom, tenseur in poids.items():
        assert torch.equal(tenseur, modele.state_dict()[nom].to(torch.bfloat16)), nom
    with safe_open(tmp_path / "publication" / NOM_DES_POIDS, "pt") as fichier:
        assert fichier.metadata() == {"format": "pt", "pas": "7"}


def test_le_modele_recharge_donne_les_memes_logits_qu_en_bf16(tmp_path, sauvegarde_test):
    sauvegarde, modele = sauvegarde_test
    exporter(sauvegarde, tmp_path / "publication")
    recharge = recharger(tmp_path / "publication")
    assert recharge.sortie.weight is recharge.plongement.weight  # le lien est rétabli
    ids = torch.randint(0, CONFIG_TEST.taille_vocabulaire, (2, CONFIG_TEST.longueur_contexte), generator=torch.Generator().manual_seed(1))
    with torch.no_grad():
        attendus, _ = modele.to(torch.bfloat16).eval()(ids)
        obtenus, _ = recharge.to(torch.bfloat16).eval()(ids)
    assert attendus.dtype == obtenus.dtype == torch.bfloat16
    assert torch.equal(obtenus, attendus)


def test_une_sauvegarde_sans_pas_n_ecrit_pas_de_pas_dans_les_metadonnees(tmp_path):
    etat, _ = etat_de_test(tmp_path)
    del etat["pas"]
    exporter(ecrire_sauvegarde(tmp_path, etat), tmp_path / "publication")
    with safe_open(tmp_path / "publication" / NOM_DES_POIDS, "pt") as fichier:
        assert fichier.metadata() == {"format": "pt"}  # jamais « None »


def test_le_prefixe_de_torch_compile_est_retire(tmp_path):
    etat, modele = etat_de_test(tmp_path)
    etat["modele"] = {f"_orig_mod.{nom}": tenseur for nom, tenseur in etat["modele"].items()}
    exporter(ecrire_sauvegarde(tmp_path, etat), tmp_path / "publication")
    poids = load_file(tmp_path / "publication" / NOM_DES_POIDS)
    assert set(poids) == set(modele.state_dict()) - {"sortie.weight"}


def test_une_sortie_non_liee_est_gardee(tmp_path):
    etat, modele = etat_de_test(tmp_path)
    etat["modele"]["sortie.weight"] = etat["modele"]["plongement.weight"].clone() * 2
    exporter(ecrire_sauvegarde(tmp_path, etat), tmp_path / "publication")
    poids = load_file(tmp_path / "publication" / NOM_DES_POIDS)
    assert set(poids) == set(modele.state_dict())
    assert torch.equal(poids["sortie.weight"], (modele.plongement.weight.detach() * 2).to(torch.bfloat16))


def test_des_poids_qui_ne_vont_pas_avec_la_configuration_sont_refuses(tmp_path):
    etat, _ = etat_de_test(tmp_path)
    del etat["modele"]["blocs.1.mlp.proj_basse.weight"]
    with pytest.raises(ValueError, match="ne correspondent pas.*blocs.1.mlp.proj_basse.weight"):
        exporter(ecrire_sauvegarde(tmp_path, etat), tmp_path / "publication")
    assert not (tmp_path / "publication").exists()


def test_le_tokenizer_est_copie_a_l_octet_pres(tmp_path, sauvegarde_test):
    sauvegarde, _ = sauvegarde_test
    exporter(sauvegarde, tmp_path / "publication")
    copie = tmp_path / "publication" / "tokenizer-ton-ia-v1.json"
    assert copie.read_bytes() == TOKENIZER_DU_DEPOT.read_bytes()
    assert sha256(copie) == EMPREINTE_DU_TOKENIZER
    assert EMPREINTE_DU_TOKENIZER.startswith("3001e7ab") and EMPREINTE_DU_TOKENIZER.endswith("21ba")


def test_un_tokenizer_modifie_est_refuse(tmp_path, sauvegarde_test, monkeypatch):
    sauvegarde, _ = sauvegarde_test
    abime = tmp_path / "tokenizer-ton-ia-v1.json"
    abime.write_bytes(TOKENIZER_DU_DEPOT.read_bytes().replace(b"\n", b"\r\n"))  # fins de ligne Windows
    monkeypatch.setattr(module_exporter, "TOKENIZER", abime)
    with pytest.raises(ValueError, match="SHA-256"):
        exporter(sauvegarde, tmp_path / "publication")
    assert not (tmp_path / "publication" / "tokenizer-ton-ia-v1.json").exists()


def test_nom_des_poids_en_option(tmp_path, sauvegarde_test):
    sauvegarde, _ = sauvegarde_test
    exporter(sauvegarde, tmp_path / "publication", "essai.safetensors")
    assert (tmp_path / "publication" / "essai.safetensors").is_file()
    assert not (tmp_path / "publication" / NOM_DES_POIDS).exists()
    recharger(tmp_path / "publication", "essai.safetensors")


@pytest.mark.parametrize("nom", ["essai.pt", "dossier/essai.safetensors", ""])
def test_un_nom_de_poids_invalide_est_refuse(tmp_path, sauvegarde_test, nom):
    sauvegarde, _ = sauvegarde_test
    with pytest.raises(ValueError, match="safetensors"):
        exporter(sauvegarde, tmp_path / "publication", nom)


def test_une_sauvegarde_absente_est_refusee(tmp_path):
    with pytest.raises(FileNotFoundError, match="introuvable"):
        exporter(tmp_path / "absent.pt", tmp_path / "publication")


# --------------------------------------------------------------------------------------
# La sous-commande
# --------------------------------------------------------------------------------------


def test_sous_commande_exporter(tmp_path, sauvegarde_test, capsys):
    sauvegarde, _ = sauvegarde_test
    sortie = tmp_path / "publication"
    assert main(["exporter", "--sauvegarde", str(sauvegarde), "--sortie", str(sortie)]) == 0
    ecran = capsys.readouterr().out
    for nom in ("ton-ia-1.5.safetensors", "config.json", "tokenizer-ton-ia-v1.json"):
        assert (sortie / nom).is_file()
        assert nom in ecran and sha256(sortie / nom) in ecran


def test_sous_commande_exporter_nom_des_poids(tmp_path, sauvegarde_test):
    sauvegarde, _ = sauvegarde_test
    arguments = ["exporter", "--sauvegarde", str(sauvegarde), "--sortie", str(tmp_path), "--poids", "essai.safetensors"]
    assert main(arguments) == 0
    assert (tmp_path / "essai.safetensors").is_file()


def test_sous_commande_exporter_erreurs_en_francais(tmp_path, capsys):
    code = main(["exporter", "--sauvegarde", str(tmp_path / "absent.pt"), "--sortie", str(tmp_path / "s")])
    erreur = capsys.readouterr().err
    assert code == 1 and erreur.startswith("Erreur : ") and "absent.pt" in erreur


def test_sous_commande_exporter_erreur_inattendue(tmp_path, monkeypatch, capsys):
    """L'erreur de `save_file` quand le disque se remplit, par exemple : pas de trace, la marche à suivre."""

    class SafetensorError(Exception):
        pass

    def export_qui_echoue(*a, **k):
        raise SafetensorError("Error while serializing: No space left on device (os error 28)\ndétail")

    monkeypatch.setattr("forge.exporter.exporter", export_qui_echoue)
    code = main(["exporter", "--sauvegarde", str(tmp_path / "meilleur.pt"), "--sortie", str(tmp_path / "s")])
    erreur = capsys.readouterr().err
    assert code == 1
    assert "SafetensorError : Error while serializing: No space left on device (os error 28)" in erreur
    assert "détail" not in erreur
    assert "aucun fichier n'est à moitié écrit" in erreur.lower() and "relance la même commande" in erreur.lower()


def test_aide_de_exporter(capsys):
    with pytest.raises(SystemExit) as fin:
        main(["exporter", "--help"])
    aide = capsys.readouterr().out
    assert fin.value.code == 0
    assert aide.startswith("Utilisation : ") and "--sauvegarde" in aide and "--sortie" in aide and "--poids" in aide


# --- Le tokenizer de la sauvegarde ---------------------------------------------------------

# L'empreinte du tokenizer figé, telle que `index.json` des jetons de ton IA la porte (SHA-1).
EMPREINTE_DE_L_INDEX = "a78aa8b2b8aad3baee05df1ff378beda303618b7"
# Ce que l'export écrivait avant la vérification du tokenizer, pour la sauvegarde de `etat_de_test`.
# Les poids : le fichier safetensors n'est pas comparé en bloc, car l'ordre des deux métadonnées
# de son en-tête change d'un lancement à l'autre (une table de hachage de safetensors, avant
# comme après ce plan). On compare donc l'en-tête sans l'ordre des métadonnées, puis les octets
# des nombres, qui eux sont toujours les mêmes.
SHA256_DES_NOMBRES_AVANT = "f870d4087077"  # début du SHA-256 de la partie nombres du fichier des poids
SHA256_AVANT = {
    "config.json": "e6f552cd7d80f8b3282609acc1beea5988e724e358c3eb104a7395d0f238d74f",
    "tokenizer-ton-ia-v1.json": EMPREINTE_DU_TOKENIZER,
}


def empreinte_figee() -> str:
    return empreinte_du_tokenizer(TokenizerOctets.charger(TOKENIZER_DU_DEPOT))


def ecrire_index(dossier: Path, empreinte: str) -> None:
    dossier.mkdir(parents=True, exist_ok=True)
    index = {"version": 1, "tokenizer": {"nom": "ton-ia-v1", "taille_vocabulaire": 32768, "empreinte": empreinte}}
    (dossier / "index.json").write_text(json.dumps(index), encoding="utf-8")


def test_l_empreinte_du_tokenizer_fige_est_celle_de_l_index():
    assert empreinte_figee() == EMPREINTE_DE_L_INDEX


def test_une_sauvegarde_du_meme_tokenizer_est_exportee(tmp_path, recwarn):
    etat, _ = etat_de_test(tmp_path)
    etat["empreinte_du_tokenizer"] = EMPREINTE_DE_L_INDEX
    chemins = exporter(ecrire_sauvegarde(tmp_path, etat), tmp_path / "publication")
    assert all(chemin.exists() for chemin in chemins)
    assert not [w for w in recwarn if "tokenizer" in str(w.message)]


def test_une_sauvegarde_d_un_autre_tokenizer_est_refusee(tmp_path):
    etat, _ = etat_de_test(tmp_path)
    etat["empreinte_du_tokenizer"] = "0" * 40
    with pytest.raises(ValueError, match="autre tokenizer"):
        exporter(ecrire_sauvegarde(tmp_path, etat), tmp_path / "publication")
    assert not (tmp_path / "publication").exists()


def test_sans_empreinte_l_export_a_lieu_avec_un_avertissement(tmp_path):
    etat, _ = etat_de_test(tmp_path)  # pas d'empreinte, et le dossier des jetons n'existe pas
    with pytest.warns(UserWarning, match="pas pu être vérifié"):
        chemins = exporter(ecrire_sauvegarde(tmp_path, etat), tmp_path / "publication")
    assert all(chemin.exists() for chemin in chemins)


def test_une_ancienne_sauvegarde_est_verifiee_par_l_index_des_donnees(tmp_path, recwarn):
    etat, _ = etat_de_test(tmp_path)  # sans empreinte : `config["donnees"]` mène à l'index
    ecrire_index(tmp_path / "jetons", EMPREINTE_DE_L_INDEX)
    chemins = exporter(ecrire_sauvegarde(tmp_path, etat), tmp_path / "publication")
    assert all(chemin.exists() for chemin in chemins)
    assert not [w for w in recwarn if "tokenizer" in str(w.message)]


def test_une_ancienne_sauvegarde_d_un_autre_tokenizer_est_refusee_par_l_index(tmp_path):
    etat, _ = etat_de_test(tmp_path)
    ecrire_index(tmp_path / "jetons", "f" * 40)
    with pytest.raises(ValueError, match="autre tokenizer"):
        exporter(ecrire_sauvegarde(tmp_path, etat), tmp_path / "publication")
    assert not (tmp_path / "publication").exists()


def test_une_sauvegarde_nouvelle_retient_l_empreinte_du_tokenizer(tmp_path):
    ecrire_index(tmp_path / "jetons", EMPREINTE_DE_L_INDEX)
    etat, _ = etat_de_test(tmp_path)
    assert etat["empreinte_du_tokenizer"] == EMPREINTE_DE_L_INDEX


def test_l_export_d_un_petit_modele_reste_identique_a_l_octet_pres(tmp_path):
    ecrire_index(tmp_path / "jetons", EMPREINTE_DE_L_INDEX)  # la vérification passe : rien ne change
    etat, _ = etat_de_test(tmp_path)
    poids, config, tokenizer = exporter(ecrire_sauvegarde(tmp_path, etat), tmp_path / "publication")
    assert {config.name: sha256(config), tokenizer.name: sha256(tokenizer)} == SHA256_AVANT
    contenu = poids.read_bytes()
    taille_de_l_en_tete = struct.unpack("<Q", contenu[:8])[0]
    en_tete = json.loads(contenu[8 : 8 + taille_de_l_en_tete])
    assert en_tete.pop("__metadata__") == {"format": "pt", "pas": "7"}
    assert "sortie.weight" not in en_tete and {d["dtype"] for d in en_tete.values()} == {"BF16"}
    assert hashlib.sha256(contenu[8 + taille_de_l_en_tete :]).hexdigest().startswith(SHA256_DES_NOMBRES_AVANT)
