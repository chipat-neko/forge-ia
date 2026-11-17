"""`charger_ton_ia` : relire les fichiers publiés de « ton IA » (la version GitHub `ton-ia-1.5`).

Le modèle des tests est le petit modèle tiré au hasard de `modele_factice`, exporté par
`forge.exporter.exporter`, la fonction qui a écrit les fichiers de la version publiée : même format,
mêmes noms (`config.json`, `ton-ia-1.5.safetensors` en bf16 sans `sortie.weight`,
`tokenizer-ton-ia-v1.json`). Ses poids sont d'abord arrondis en bf16 : relus en float32, ils doivent
redonner les logits du modèle d'origine au bit près.
"""

import json
import struct

import pytest
import torch
from modele_factice import CONFIG, arrondi_en_bf16, exporter_comme_la_release, petit_modele, tokenizer
from safetensors import safe_open

from evaluation_pas_a_pas.ton_ia import NOM_DE_LA_VERSION, charger_ton_ia

PHRASE = "Le forgeron chauffe le fer puis il le tord."


@pytest.fixture
def origine():
    return arrondi_en_bf16(petit_modele())


@pytest.fixture
def dossier(origine, tmp_path):
    return exporter_comme_la_release(origine, tmp_path / "ton-ia-1.5")


def ids(longueur: int = 20) -> torch.Tensor:
    return torch.tensor([tokenizer().encoder(PHRASE)[:longueur]])


def test_le_dossier_a_le_format_de_la_version_publiee(dossier):
    assert {f.name for f in dossier.iterdir()} == {"config.json", "ton-ia-1.5.safetensors", "tokenizer-ton-ia-v1.json"}
    with safe_open(dossier / "ton-ia-1.5.safetensors", framework="pt") as poids:
        assert "plongement.weight" in poids.keys() and "sortie.weight" not in poids.keys()
        assert poids.get_tensor("plongement.weight").dtype == torch.bfloat16
    assert json.loads((dossier / "config.json").read_text(encoding="utf-8"))["dim"] == CONFIG.dim


def test_charger_ton_ia_relit_un_en_tete_aux_cles_triees(origine, dossier):
    """L'export trie l'en-tête safetensors (même fichier à chaque export) : `charger_ton_ia` le relit."""
    contenu = (dossier / "ton-ia-1.5.safetensors").read_bytes()
    taille = struct.unpack("<Q", contenu[:8])[0]
    noms = [nom for nom, _ in json.loads(contenu[8 : 8 + taille], object_pairs_hook=lambda paires: paires)]
    assert noms == sorted(noms) and "__metadata__" in noms
    modele, _ = charger_ton_ia(dossier)
    with torch.no_grad():
        attendus, _ = origine(ids())
        lus, _ = modele(ids())
    assert torch.equal(lus, attendus)


def test_charger_ton_ia_redonne_les_logits_du_modele_d_origine(origine, dossier):
    modele, _ = charger_ton_ia(dossier)
    with torch.no_grad():
        attendus, _ = origine(ids())
        lus, _ = modele(ids())
    assert torch.equal(lus, attendus)  # bf16 vers float32 est exact : les mêmes nombres, les mêmes calculs


def test_le_modele_est_en_float32_en_evaluation_avec_ses_poids_lies(dossier):
    modele, _ = charger_ton_ia(dossier, "cpu")
    assert modele.config == CONFIG and not modele.training
    assert {p.dtype for p in modele.parameters()} == {torch.float32}
    assert {p.device.type for p in modele.parameters()} == {"cpu"}
    assert modele.sortie.weight is modele.plongement.weight  # la sortie est le plongement, comme à l'entraînement


def test_le_tokenizer_est_celui_de_ton_ia(dossier):
    _, lu = charger_ton_ia(dossier)
    assert lu.encoder(PHRASE) == tokenizer().encoder(PHRASE)
    assert lu.decoder(lu.encoder(PHRASE)) == PHRASE


def test_le_nom_de_la_version():
    assert NOM_DE_LA_VERSION == "ton-ia-1.5"


def test_un_tokenizer_modifie_est_refuse(dossier):
    chemin = dossier / "tokenizer-ton-ia-v1.json"
    chemin.write_bytes(chemin.read_bytes().replace(b"\n", b"\r\n"))  # comme un git qui change les fins de ligne
    with pytest.raises(ValueError, match="empreinte SHA-256") as erreur:
        charger_ton_ia(dossier)
    assert "3001e7ab40630739c4dec807c7a92c0d4fb469cc0fc4afa368704395391f21ba" in str(erreur.value)
    assert "gh release download ton-ia-1.5" in str(erreur.value)


@pytest.mark.parametrize("fichier", ["config.json", "ton-ia-1.5.safetensors", "tokenizer-ton-ia-v1.json"])
def test_un_fichier_manquant_est_nomme(dossier, fichier):
    (dossier / fichier).unlink()
    with pytest.raises(FileNotFoundError, match=fichier) as erreur:
        charger_ton_ia(dossier)
    assert "gh release download ton-ia-1.5" in str(erreur.value)


def test_un_dossier_absent_le_dit(tmp_path):
    with pytest.raises(FileNotFoundError, match="n'existe pas") as erreur:
        charger_ton_ia(tmp_path / "rien")
    assert "gh release download ton-ia-1.5" in str(erreur.value)


@pytest.mark.parametrize(
    "contenu, attendu",
    [
        ("pas du JSON", "config.json"),
        (json.dumps({"dim": 32, "couches": 2, "tetes": 4, "longueur_contexte": 64, "couleur": "bleu"}), "couleur"),
        (json.dumps({"dim": 30, "couches": 2, "tetes": 4, "longueur_contexte": 64}), "divisible"),
    ],
)
def test_une_configuration_fausse_est_refusee(dossier, contenu, attendu):
    (dossier / "config.json").write_text(contenu, encoding="utf-8")
    with pytest.raises(ValueError, match=attendu):
        charger_ton_ia(dossier)


def test_des_poids_qui_ne_vont_pas_avec_la_configuration_sont_refuses(dossier):
    config = json.loads((dossier / "config.json").read_text(encoding="utf-8"))
    (dossier / "config.json").write_text(json.dumps({**config, "couches": 3}), encoding="utf-8")
    with pytest.raises(ValueError, match="ne correspondent pas"):
        charger_ton_ia(dossier)


def test_des_poids_abimes_sont_refuses(dossier):
    chemin = dossier / "ton-ia-1.5.safetensors"
    chemin.write_bytes(chemin.read_bytes()[:1000])  # un téléchargement coupé
    with pytest.raises(ValueError, match="ne se lit pas") as erreur:
        charger_ton_ia(dossier)
    assert "gh release download ton-ia-1.5" in str(erreur.value)


@pytest.mark.gpu
def test_charger_ton_ia_sur_la_carte(origine, dossier):
    modele, _ = charger_ton_ia(dossier, "cuda")
    assert {p.device.type for p in modele.parameters()} == {"cuda"}
    with torch.no_grad():
        attendus, _ = origine(ids())
        lus, _ = modele(ids().to("cuda"))
    assert (lus.cpu() - attendus).abs().max().item() <= 1e-4  # la carte additionne dans un autre ordre
