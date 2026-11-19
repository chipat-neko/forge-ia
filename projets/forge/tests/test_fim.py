"""Tests du remplissage au milieu (FIM, ordre PSM) et de la recette de code de ton IA 1.10 (plan 7, tâche 19).

Aucun test ne lit les vrais textes du pré-entraînement : les documents sont des fragments fabriqués dans
`tmp_path`, au même format que `textes/principal/code_python` (`fragment-NNNNN.jsonl.gz`, un `{"texte": …}` par ligne).
"""

import gzip
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

from forge import __main__ as principal
from forge.affinage.jeu import lire_index
from forge.affinage.recettes import RECETTES, Part, Recette, preparer_jeu
from forge.chemins import sous_forge_donnees
from forge.code.fim import (
    JETONS_MAX_DU_DOCUMENT,
    cas_d_une_ligne,
    couper_au_hasard,
    elements_fim,
    exemple_fim,
    invite_fim,
)
from forge.conversation.telechargement import PREFIXE
from forge.donnees.melange import est_validation
from forge.donnees.nettoyage import empreinte_du_texte_nettoye
from forge.erreurs import DonneesManquantes
from forge.fragments import SortieParFragments, lire_elements
from forge.hasard import Hasard
from forge.tokenizer import TokenizerOctets

TOKENIZER = Path(__file__).parent.parent / "forge" / "ressources" / "tokenizer-ton-ia-v1.json"
TOK = TokenizerOctets.charger(TOKENIZER)


@pytest.fixture(autouse=True)
def donnees(tmp_path, monkeypatch):
    monkeypatch.setenv("FORGE_DONNEES", str(tmp_path / "donnees"))
    return tmp_path / "donnees"


# --- De faux documents de code ---------------------------------------------------------------------------


def document(i: int) -> str:
    """Un petit programme Python, différent pour chaque entier (et sur plusieurs lignes)."""
    return (
        f"import os\n\n\ndef calcul_{i}(x):\n    y = x * {i} + 1\n    z = y - {i % 7}\n"
        f"    return z\n\n\nif __name__ == '__main__':\n    print(calcul_{i}({i}))\n"
    )


def est_en_validation(texte: str) -> bool:
    return est_validation(empreinte_du_texte_nettoye(texte))


def ecrire_textes(dossier: Path, textes: list[str]) -> Path:
    dossier.mkdir(parents=True, exist_ok=True)
    with gzip.open(dossier / "fragment-00000.jsonl.gz", "wt", encoding="utf-8") as fichier:
        for texte in textes:
            fichier.write(json.dumps({"texte": texte}, ensure_ascii=False) + "\n")
    return dossier


@pytest.fixture(scope="module")
def documents() -> list[str]:
    """Des documents dont quelques-uns tombent dans la validation du pré-entraînement (0,5 %)."""
    textes, en_validation, i = [], 0, 0
    while en_validation < 3 or len(textes) < 60:
        textes.append(document(i))
        en_validation += est_en_validation(textes[-1])
        i += 1
    return textes


@pytest.fixture
def textes_code(tmp_path, documents) -> Path:
    return ecrire_textes(tmp_path / "textes" / "code_python", documents)


# --- La disposition des ids et le masque -----------------------------------------------------------------


def test_les_trois_jetons_du_trou_existent_dans_le_tokenizer_fige():
    ids = {TOK.id_special(nom) for nom in ("<|trou_prefixe|>", "<|trou_suffixe|>", "<|trou_milieu|>")}
    assert len(ids) == 3


def test_disposition_exacte_des_ids_et_masque():
    prefixe, milieu, suffixe = "def f(x):\n    ", "return x + 1", "\n\nprint(f(2))\n"
    exemple = exemple_fim(prefixe, milieu, suffixe, TOK)
    attendu = (
        [TOK.id_special("<|fin_texte|>"), TOK.id_special("<|trou_prefixe|>")]
        + TOK.encoder(prefixe)
        + [TOK.id_special("<|trou_suffixe|>")]
        + TOK.encoder(suffixe)
        + [TOK.id_special("<|trou_milieu|>")]
        + TOK.encoder(milieu)
        + [TOK.id_special("<|fin_tour|>")]
    )
    assert exemple.ids == attendu
    nombre_appris = len(TOK.encoder(milieu)) + 1
    assert exemple.appris == [False] * (len(attendu) - nombre_appris) + [True] * nombre_appris
    # Le premier jeton appris est celui du milieu, le dernier est `<|fin_tour|>`.
    assert exemple.ids[-1] == TOK.id_special("<|fin_tour|>")
    assert len(exemple.ids) == len(exemple.appris)


def test_l_invite_est_le_debut_de_l_exemple_jusqu_au_trou_du_milieu_compris():
    prefixe, milieu, suffixe = "a = 1\n", "b = 2\n", "c = a + b\n"
    exemple = exemple_fim(prefixe, milieu, suffixe, TOK)
    invite = invite_fim(prefixe, suffixe, TOK)
    assert invite[-1] == TOK.id_special("<|trou_milieu|>")
    assert exemple.ids[: len(invite)] == invite
    assert not any(exemple.appris[: len(invite)])
    assert all(exemple.appris[len(invite) :])


def test_un_prefixe_ou_un_suffixe_vide_est_permis_mais_pas_un_milieu_vide():
    exemple = exemple_fim("", "x = 1\n", "", TOK)
    assert exemple.ids[:2] == [TOK.id_special("<|fin_texte|>"), TOK.id_special("<|trou_prefixe|>")]
    assert exemple.ids[2] == TOK.id_special("<|trou_suffixe|>")
    with pytest.raises(ValueError, match="milieu"):
        exemple_fim("a", "", "b", TOK)


def test_un_code_qui_ecrit_les_jetons_speciaux_ne_change_pas_la_disposition():
    exemple = exemple_fim("# <|trou_milieu|> et <|fin_tour|>\n", "x = 1", "\n", TOK)
    speciaux = [i for i in exemple.ids if i >= TOK.premier_special]
    assert speciaux == [TOK.id_special(nom) for nom in (
        "<|fin_texte|>", "<|trou_prefixe|>", "<|trou_suffixe|>", "<|trou_milieu|>", "<|fin_tour|>")]


# --- Les coupures ----------------------------------------------------------------------------------------


CODE_A_EMOJI = "é = '😀'\nprint('çà et là 😀🎉', é)\n"


def test_les_coupures_tombent_sur_des_points_de_code_et_redonnent_le_code():
    hasard = Hasard(7)
    for _ in range(500):
        debut, fin = couper_au_hasard(CODE_A_EMOJI, hasard)
        assert isinstance(debut, int) and isinstance(fin, int)
        assert 0 <= debut < fin <= len(CODE_A_EMOJI)
        prefixe, milieu, suffixe = CODE_A_EMOJI[:debut], CODE_A_EMOJI[debut:fin], CODE_A_EMOJI[fin:]
        assert prefixe + milieu + suffixe == CODE_A_EMOJI
        assert milieu
        # Chaque morceau est du texte entier : il se code en octets et se relit sans perte (rien n'est coupé en deux).
        for morceau in (prefixe, milieu, suffixe):
            assert TOK.decoder(TOK.encoder(morceau)) == morceau
            assert morceau.encode("utf-8").decode("utf-8") == morceau


def test_un_code_d_un_seul_caractere_se_coupe_en_entier():
    assert couper_au_hasard("x", Hasard(1)) == (0, 1)
    assert couper_au_hasard("😀", Hasard(2)) == (0, 1)


def test_couper_un_code_vide_dit_quoi_faire():
    with pytest.raises(ValueError, match="vide"):
        couper_au_hasard("", Hasard(0))


def test_les_coupures_sont_uniformes_et_reproductibles():
    code = "abcd"  # 4 caractères : 10 milieux possibles, de 0 ≤ debut < fin ≤ 4
    hasard = Hasard(3)
    comptes = Counter(couper_au_hasard(code, hasard) for _ in range(10_000))
    assert len(comptes) == 10
    assert all(800 < nombre < 1200 for nombre in comptes.values()), comptes
    premieres = [couper_au_hasard(code, Hasard(11)) for _ in range(3)]
    assert premieres[0] == premieres[1] == premieres[2]


# --- Le cas d'une ligne ----------------------------------------------------------------------------------


def test_cas_d_une_ligne_redonne_le_code_et_prend_une_ligne_du_tiers_du_milieu():
    code = "".join(f"ligne_{i} = {i}\n" for i in range(12))
    for graine in range(40):
        prefixe, milieu, suffixe = cas_d_une_ligne(code, Hasard(graine))
        assert prefixe + milieu + suffixe == code
        assert milieu.endswith("\n") and milieu.count("\n") == 1 and milieu.strip()
        numero = prefixe.count("\n")
        assert 4 <= numero < 8  # le tiers du milieu de 12 lignes : les lignes 4 à 7


def test_cas_d_une_ligne_saute_les_lignes_vides_et_dit_none_s_il_n_y_en_a_pas():
    code = "a = 1\nb = 2\n\n\n\n\nc = 3\nd = 4\n"  # le tiers du milieu (lignes 2 à 5) est fait de lignes vides
    assert cas_d_une_ligne(code, Hasard(0)) is None
    assert cas_d_une_ligne("", Hasard(0)) is None
    assert cas_d_une_ligne("\n\n\n", Hasard(0)) is None


def test_cas_d_une_ligne_garde_la_derniere_ligne_sans_saut_de_ligne():
    prefixe, milieu, suffixe = cas_d_une_ligne("seule = 1", Hasard(0))
    assert (prefixe, milieu, suffixe) == ("", "seule = 1", "")


def test_cas_d_une_ligne_sur_du_code_a_emoji():
    prefixe, milieu, suffixe = cas_d_une_ligne(CODE_A_EMOJI, Hasard(5))
    assert prefixe + milieu + suffixe == CODE_A_EMOJI


# --- Les éléments tirés des textes de code ----------------------------------------------------------------


def test_elements_fim_n_a_aucun_document_de_validation_en_entrainement_et_inversement(documents, textes_code):
    en_validation = {d for d in documents if est_en_validation(d)}
    assert en_validation and len(en_validation) < len(documents)
    entrainement = list(elements_fim(textes_code, 100_000, 0, validation=False))
    assert len(entrainement) == len(documents) - len(en_validation)
    for e in entrainement:
        assert e["prefixe"] + e["milieu"] + e["suffixe"] not in en_validation
    validation = list(elements_fim(textes_code, 100_000, 0, validation=True))
    assert len(validation) == len(en_validation)
    for e in validation:
        assert e["prefixe"] + e["milieu"] + e["suffixe"] in en_validation


def test_la_forme_d_un_element_et_la_limite_n(textes_code):
    elements = list(elements_fim(textes_code, 5, 3, validation=False))
    assert len(elements) == 5
    for e in elements:
        assert set(e) == {"sorte", "prefixe", "milieu", "suffixe"}
        assert e["sorte"] == "fim"
        assert e["milieu"]


def test_elements_fim_est_reproductible_et_depend_de_la_graine(textes_code):
    a = list(elements_fim(textes_code, 20, 1, validation=False))
    assert a == list(elements_fim(textes_code, 20, 1, validation=False))
    assert a != list(elements_fim(textes_code, 20, 2, validation=False))


def test_un_document_de_plus_de_1500_jetons_est_ecarte(tmp_path):
    long = "".join(f"variable_numero_{i} = {i * 7919 % 1000}\n" for i in range(600))
    assert len(TOK.encoder(long)) > JETONS_MAX_DU_DOCUMENT
    court = next(d for d in map(document, range(1000)) if not est_en_validation(d))
    assert not est_en_validation(long)
    dossier = ecrire_textes(tmp_path / "t", [long, court])
    elements = list(elements_fim(dossier, 10, 0, validation=False))
    assert len(elements) == 1
    assert elements[0]["prefixe"] + elements[0]["milieu"] + elements[0]["suffixe"] == court


def test_elements_fim_en_lignes(textes_code):
    elements = list(elements_fim(textes_code, 8, 4, validation=False, lignes=True))
    assert len(elements) == 8
    for e in elements:
        assert e["milieu"].endswith("\n") and e["milieu"].strip() and e["milieu"].count("\n") == 1


def test_elements_fim_refuse_un_nombre_nul(textes_code):
    with pytest.raises(ValueError, match="au moins 1"):
        list(elements_fim(textes_code, 0, 0, validation=False))


# --- La commande `forge fim` -----------------------------------------------------------------------------


def lancer(*arguments: str) -> int:
    return principal.main(["fim", *arguments])


def test_la_commande_fim_ecrit_un_dossier_de_conversations(donnees, textes_code, capsys):
    code = lancer("--sortie", "essai", "--exemples", "12", "--graine", "5", "--textes", str(textes_code))
    assert code == 0
    dossier = sous_forge_donnees("essai", "conversations")
    infos = json.loads((dossier / ".complet").read_text(encoding="utf-8"))
    assert infos["usage"] == "entrainement"
    assert infos["sorte"] == "fim"
    assert infos["epuisee"] is True
    elements = list(lire_elements(dossier, PREFIXE))
    assert elements == list(elements_fim(textes_code, 12, 5, validation=False))
    assert "12" in capsys.readouterr().out


def test_la_commande_fim_validation_est_d_usage_evaluation(donnees, textes_code):
    assert lancer("--sortie", "val", "--exemples", "3", "--graine", "5", "--validation", "--lignes",
                  "--textes", str(textes_code)) == 0
    dossier = sous_forge_donnees("val", "conversations")
    assert json.loads((dossier / ".complet").read_text(encoding="utf-8"))["usage"] == "evaluation"
    elements = list(lire_elements(dossier, PREFIXE))
    assert len(elements) == 3
    assert all(e["milieu"].endswith("\n") for e in elements)


def test_relancer_la_meme_commande_ne_refait_rien(donnees, textes_code, capsys):
    arguments = ("--sortie", "essai", "--exemples", "6", "--graine", "5", "--textes", str(textes_code))
    assert lancer(*arguments) == 0
    dossier = sous_forge_donnees("essai", "conversations")
    avant = {f.name: f.read_bytes() for f in dossier.iterdir() if f.is_file()}
    capsys.readouterr()
    assert lancer(*arguments) == 0
    assert "Déjà fait" in capsys.readouterr().out
    assert {f.name: f.read_bytes() for f in dossier.iterdir() if f.is_file()} == avant


def test_la_commande_refuse_d_autres_reglages_dans_un_dossier_existant(donnees, textes_code, capsys):
    assert lancer("--sortie", "essai", "--exemples", "6", "--graine", "5", "--textes", str(textes_code)) == 0
    capsys.readouterr()
    assert lancer("--sortie", "essai", "--exemples", "6", "--graine", "6", "--textes", str(textes_code)) == 1
    assert "--sortie" in capsys.readouterr().err


def test_la_commande_dit_quoi_faire_quand_les_textes_manquent(donnees, tmp_path, capsys):
    assert lancer("--sortie", "essai", "--exemples", "6", "--graine", "5", "--textes", str(tmp_path / "rien")) == 1
    assert "python -m forge donnees" in capsys.readouterr().err


def test_la_commande_dit_quand_il_n_y_a_pas_assez_de_documents(donnees, tmp_path, capsys):
    dossier = ecrire_textes(tmp_path / "peu", [next(d for d in map(document, range(1000)) if not est_en_validation(d))])
    assert lancer("--sortie", "essai", "--exemples", "5", "--graine", "5", "--textes", str(dossier)) == 0
    sortie = capsys.readouterr().out
    assert "1" in sortie and "5" in sortie
    infos = json.loads((sous_forge_donnees("essai", "conversations") / ".complet").read_text(encoding="utf-8"))
    assert infos["elements"] == 1


def test_la_commande_refuse_un_nombre_d_exemples_nul(donnees, textes_code, capsys):
    assert lancer("--sortie", "essai", "--exemples", "0", "--graine", "5", "--textes", str(textes_code)) == 1
    assert "au moins 1" in capsys.readouterr().err


# --- La recette de ton IA 1.10 ---------------------------------------------------------------------------


def test_la_recette_code_1_10_a_les_parts_de_la_fiche():
    recette = RECETTES["code-1.10"]
    assert recette.nom == "code-1.10"
    assert [(p.source, p.exemples_max) for p in recette.parts] == [
        ("code_fr:consignes-code-fr", None),
        ("luth2_code", 40_000),
        ("fim:fim-1.10", 60_000),
        ("luth2_conversation", 15_000),
        ("problemes:entrainement-1.9", 10_000),
        ("identite", None),
    ]


def ecrire_source_fim(nom: str, elements: list[dict], usage: str = "entrainement") -> None:
    dossier = sous_forge_donnees(nom, "conversations")
    sortie = SortieParFragments(dossier, PREFIXE, 7)
    for element in elements:
        sortie.ajouter(element)
        if sortie.plein:
            sortie.valider()
    sortie.terminer({"nom": nom, "usage": usage, "sorte": "fim", "epuisee": True, "elements": len(elements)})


def recette_de_fim(*parts: Part) -> Recette:
    return Recette(nom="essai-fim", parts=parts, part_validation=0.3, jetons_max_exemple=1536)


def test_une_part_fim_donne_des_exemples_fim_dans_le_jeu(donnees, textes_code):
    elements = list(elements_fim(textes_code, 30, 9, validation=False))
    ecrire_source_fim("fim-essai", elements)
    index = preparer_jeu(recette_de_fim(Part("fim:fim-essai", None), Part("identite", None)))
    fim = index["sources"]["fim:fim-essai"]
    assert fim["lus"] == 30
    assert fim["gardes"] == 30
    assert fim["invalides"] == fim["trop_longs"] == fim["doublons"] == fim["contamines"] == 0
    assert "Apache-2.0" in fim["licence"] and fim["lien"].startswith("https://")
    dossier = sous_forge_donnees("essai-fim", "affinage")
    index = lire_index(dossier)
    trou = TOK.id_special("<|trou_milieu|>")
    total = 0
    for partie in ("train", "val"):
        ids = np.fromfile(dossier / partie / "ids.bin", dtype="<u2")
        total += int((ids == trou).sum())
    assert total == 30
    assert index["exemples"] >= 30


def test_une_part_fim_sans_ses_elements_dit_la_commande(donnees):
    with pytest.raises(DonneesManquantes, match="python -m forge fim --sortie fim-absent"):
        preparer_jeu(recette_de_fim(Part("fim:fim-absent", None)))


def test_une_part_fim_d_evaluation_est_refusee(donnees, textes_code):
    ecrire_source_fim("fim-val", list(elements_fim(textes_code, 3, 1, validation=True)), usage="evaluation")
    with pytest.raises(ValueError, match="fim-val"):
        preparer_jeu(recette_de_fim(Part("fim:fim-val", None)))
    assert not (donnees / "affinage").exists()


def test_la_part_code_fr_n_est_pas_encore_disponible(donnees):
    with pytest.raises(ValueError, match="pas encore"):
        preparer_jeu(recette_de_fim(Part("code_fr:consignes-code-fr", None)))
