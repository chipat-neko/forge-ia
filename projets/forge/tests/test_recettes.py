"""Tests des recettes de jeux d'affinage et de `forge preparer` (plan 7, tâche 10).

Aucun test n'ouvre le réseau : les sources sont de faux fragments écrits dans `tmp_path`, là où
`lire_pour_entrainement` les cherche (`FORGE_DONNEES` pointe sur `tmp_path`).
"""

import gzip
import json
import re
from pathlib import Path

import numpy as np
import pytest

from forge import __main__ as principal
from forge.affinage import jeu as module_jeu
from forge.affinage import recettes
from forge.affinage.jeu import lire_index
from forge.affinage.recettes import RECETTES, Part, Recette, preparer_jeu
from forge.chemins import sous_forge_donnees
from forge.conversation.generees import IDENTITE
from forge.conversation.sources import SOURCES_CONVERSATIONS, UsageInterdit
from forge.conversation.telechargement import PREFIXE, dossier_de_la_source
from forge.erreurs import DonneesManquantes
from forge.fragments import SortieParFragments
from forge.raisonnement.problemes import conversation_de_probleme, generer_problemes
from forge.tokenizer import TokenizerOctets

TOKENIZER = Path(__file__).parent.parent / "forge" / "ressources" / "tokenizer-ton-ia-v1.json"
TOK = TokenizerOctets.charger(TOKENIZER)
LETTRES = "abcdefghijklmnopqrstuvwxyz"


@pytest.fixture(autouse=True)
def donnees(tmp_path, monkeypatch):
    monkeypatch.setenv("FORGE_DONNEES", str(tmp_path / "donnees"))
    return tmp_path / "donnees"


# --- De faux fragments de sources -----------------------------------------------------------------------


def mot(i: int) -> str:
    """Un mot de lettres seulement, distinct pour chaque entier : les chiffres ne comptent pas dans `mots()`."""
    return LETTRES[i % 26] + LETTRES[(i // 26) % 26] + "ouvement" + LETTRES[(i // 676) % 26]


def conversation(i: int, etiquette: str = "Q") -> dict:
    """Une conversation d'un tour, avec une étiquette (`Q12`) pour la retrouver, et sans 8-gramme commun avec les autres."""
    question = f"{etiquette}{i} : explique le {mot(i)} puis le {mot(i + 7)} dans le détail, s'il te plaît."
    reponse = f"Bien sûr. Le {mot(i)} sert au {mot(i + 7)}. Premier point. Deuxième point. Dernier point, voilà."
    return {
        "tours": [{"role": "utilisateur", "texte": question}, {"role": "assistant", "texte": reponse}],
        "domaine": "essai",
        "origine": f"{etiquette}{i}",
    }


def ecrire_elements(dossier: Path, prefixe: str, elements: list[dict], infos: dict | None = None) -> None:
    sortie = SortieParFragments(dossier, prefixe, 7)
    for element in elements:
        sortie.ajouter(element)
        if sortie.plein:
            sortie.valider()
    sortie.terminer(infos if infos is not None else {"epuisee": True})


def ecrire_source(nom: str, elements: list[dict]) -> None:
    ecrire_elements(dossier_de_la_source(SOURCES_CONVERSATIONS[nom]), PREFIXE, elements)


def ecrire_liste_de_problemes(nom: str, usage: str, problemes: list) -> None:
    elements = [
        {"id": p.id, "famille": p.famille, "difficulte": p.difficulte, "enonce": p.enonce,
         "etapes": list(p.etapes), "reponse": p.reponse}
        for p in problemes
    ]
    dossier = sous_forge_donnees(nom, "problemes")
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / "index.json").write_text(json.dumps({"usage": usage}), encoding="utf-8")
    ecrire_elements(dossier, "problemes", elements, {"usage": usage, "elements": len(elements)})


def ecrire_problemes(nom: str, usage: str, graine: int, n: int) -> list:
    problemes = generer_problemes(n, graine)
    ecrire_liste_de_problemes(nom, usage, problemes)
    return problemes


def recette(*parts: Part, **champs) -> Recette:
    champs.setdefault("part_validation", 0.3)
    champs.setdefault("nom", "essai")
    return Recette(parts=tuple(parts), **champs)


# --- Relire un jeu écrit ---------------------------------------------------------------------------------


def textes_du_jeu(dossier: Path, partie: str) -> list[str]:
    """Le texte (sans jetons spéciaux) de chaque exemple d'une partie du jeu."""
    index = lire_index(dossier)
    largeur = index["longueur"] + 1
    ids = np.fromfile(dossier / partie / "ids.bin", dtype="<u2").reshape(-1, largeur)
    documents = np.fromfile(dossier / partie / "documents.bin", dtype="<i2").reshape(-1, largeur)
    textes = []
    for rangee_ids, rangee_docs in zip(ids, documents, strict=True):
        for numero in sorted(set(int(d) for d in rangee_docs) - {-1}):
            morceau = [int(i) for i, d in zip(rangee_ids, rangee_docs, strict=True) if d == numero]
            textes.append(TOK.decoder([i for i in morceau if i < TOK.premier_special]))
    return textes


def etiquettes(textes: list[str], etiquette: str = "Q") -> list[int]:
    return [int(n) for t in textes for n in re.findall(rf"{etiquette}(\d+) :", t)[:1]]


def contenu_du_dossier(dossier: Path) -> dict[str, bytes]:
    return {str(f.relative_to(dossier)): f.read_bytes() for f in sorted(dossier.rglob("*")) if f.is_file()}


def ids_gardes(dossier: Path) -> list[str]:
    return gzip.decompress((dossier / "ids.txt.gz").read_bytes()).decode("utf-8").split()


# --- Les recettes du plan ---------------------------------------------------------------------------------


def test_les_deux_recettes_du_plan():
    assert tuple(RECETTES) == ("sft-1.7", "raisonnement-1.9", "code-1.10")
    sft = RECETTES["sft-1.7"]
    assert sft.nom == "sft-1.7"
    assert [(p.source, p.exemples_max) for p in sft.parts] == [
        ("luth2_conversation", 150_000), ("aya_fr", None), ("oasst2_fr", None),
        ("systeme_genere", 20_000), ("identite", None),
    ]
    raisonnement = RECETTES["raisonnement-1.9"]
    assert [(p.source, p.exemples_max) for p in raisonnement.parts] == [
        ("problemes:entrainement-1.9", 60_000), ("luth2_conversation", 12_000),
        ("systeme_genere", 3_000), ("identite", None),
    ]
    for r in RECETTES.values():
        assert (r.longueur, r.jetons_max_exemple, r.part_validation, r.graine) == (2048, 1536, 0.02, 0)
    # La part de rappel de 1.9 reprend les premiers exemples de 1.7 : même graine.
    assert sft.graine == raisonnement.graine


# --- Les jeux d'évaluation n'entrent jamais ---------------------------------------------------------------


@pytest.mark.parametrize("nom", ["ifeval_fr", "mgsm_rev2_fr", "gsm8k_platinum_fr", "humaneval", "humaneval_fr"])
def test_une_part_d_evaluation_est_refusee_avant_toute_ecriture(nom, donnees):
    with pytest.raises(UsageInterdit, match=nom):
        preparer_jeu(recette(Part(nom, None), Part("identite", None)))
    assert not (donnees / "affinage").exists()


def test_une_source_inconnue_ou_qui_n_est_pas_une_conversation_est_refusee():
    with pytest.raises(ValueError, match="n_importe_quoi"):
        preparer_jeu(recette(Part("n_importe_quoi", None)))
    with pytest.raises(ValueError, match="opc_educational"):
        preparer_jeu(recette(Part("opc_educational", None)))
    with pytest.raises(ValueError, match="pas encore"):
        preparer_jeu(recette(Part("code_fr:x", None)))


def test_des_problemes_d_evaluation_ne_servent_pas_a_l_entrainement():
    ecrire_problemes("evaluation-1.9", "evaluation", 1_000_000, 12)
    with pytest.raises(ValueError, match="evaluation-1.9"):
        preparer_jeu(recette(Part("problemes:evaluation-1.9", None)))
    ecrire_problemes("validation-rl", "validation_rl", 5_000_000, 12)
    with pytest.raises(ValueError, match="validation-rl"):
        preparer_jeu(recette(Part("problemes:validation-rl", None)))


def test_une_source_pas_telechargee_dit_la_commande():
    with pytest.raises(DonneesManquantes, match="--source aya_fr"):
        preparer_jeu(recette(Part("aya_fr", None)))
    with pytest.raises(DonneesManquantes, match="forge problemes"):
        preparer_jeu(recette(Part("problemes:absents", None)))


# --- Décontamination (point à surveiller 5) -----------------------------------------------------------------

QUESTION_MGSM = (
    "Janet a des canards qui pondent seize œufs par jour, elle en mange trois au petit déjeuner "
    "et en utilise quatre pour faire des muffins pour ses amis."
)


def test_un_exemple_qui_reprend_huit_mots_d_une_question_d_evaluation_est_ecarte_et_compte(donnees):
    ecrire_source("mgsm_rev2_fr", [{"question": QUESTION_MGSM, "reponse": "18", "usage": "evaluation"}])
    propres = [conversation(i) for i in range(10)]
    copie = {  # 8 mots de la question, au milieu d'une phrase, en majuscules et avec une autre ponctuation
        "tours": [
            {"role": "utilisateur", "texte": "Voici mon exercice. ELLE EN MANGE TROIS AU PETIT DÉJEUNER, et en utilise quatre ?"},
            {"role": "assistant", "texte": "Je ne sais pas faire cet exercice."},
        ],
        "domaine": "essai", "origine": "copie",
    }
    sept = {  # seulement 7 mots de suite : ce n'est pas un 8-gramme
        "tours": [
            {"role": "utilisateur", "texte": "Elle en mange trois au petit déjeuner : alors, quelle suite ?"},
            {"role": "assistant", "texte": "Aucune idée pour la suite."},
        ],
        "domaine": "essai", "origine": "sept",
    }
    ecrire_source("luth2_conversation", [*propres, copie, sept])
    resume = preparer_jeu(recette(Part("luth2_conversation", None), part_validation=0.0))
    source = resume["sources"]["luth2_conversation"]
    assert (source["lus"], source["contamines"], source["gardes"]) == (12, 1, 11)
    assert "ELLE EN MANGE" not in " ".join(textes_du_jeu(donnees / "affinage" / "essai", "train"))
    assert "Elle en mange trois au petit" in " ".join(textes_du_jeu(donnees / "affinage" / "essai", "train"))


def test_une_invite_d_evaluation_de_moins_de_huit_mots_est_ecartee_en_entier():
    ecrire_source("ifeval_fr", [{"cle": "1", "invite": "Écris un poème sur la mer.", "instruction_id_list": [],
                                  "kwargs": [], "usage": "evaluation"}])
    copie = {
        "tours": [{"role": "utilisateur", "texte": "écris un poème sur la mer"}, {"role": "assistant", "texte": "Non."}],
        "domaine": "essai", "origine": "c",
    }
    autre = {
        "tours": [{"role": "utilisateur", "texte": "écris un poème sur la mer et le vent d'automne"},
                  {"role": "assistant", "texte": "Voilà."}],
        "domaine": "essai", "origine": "a",
    }
    ecrire_source("luth2_conversation", [copie, autre])
    resume = preparer_jeu(recette(Part("luth2_conversation", None)))
    assert resume["sources"]["luth2_conversation"]["contamines"] == 1


def test_les_problemes_d_evaluation_et_les_jeux_absents_sont_dits(donnees):
    ecrire_problemes("evaluation", "evaluation", 1_000_000, 20)
    ecrire_source("luth2_conversation", [conversation(i) for i in range(5)])
    messages: list[str] = []
    resume = preparer_jeu(recette(Part("luth2_conversation", None)), journal=messages.append)
    assert resume["decontamination"]["jeux"] == ["problemes/evaluation"]
    assert set(resume["decontamination"]["absents"]) == {"ifeval_fr", "mgsm_rev2_fr", "gsm8k_platinum_fr", "humaneval", "humaneval_fr"}
    assert any("humaneval_fr" in m and "mgsm_rev2_fr" in m and "décontamin" in m for m in messages)
    assert all(not re.search(r"[ ][:;!?]", m) for m in messages)  # espace fine insécable, jamais ordinaire
    assert lire_index(donnees / "affinage" / "essai")["decontamination"] == resume["decontamination"]


def test_un_probleme_d_evaluation_recopie_dans_un_jeu_de_problemes_d_entrainement_est_ecarte():
    evaluation = generer_problemes(10, 1_000_000)
    entrainement = generer_problemes(10, 0)
    ecrire_liste_de_problemes("evaluation", "evaluation", evaluation)
    # Un problème d'évaluation glissé dans le jeu d'entraînement : même énoncé, mot pour mot.
    ecrire_liste_de_problemes("melange", "entrainement", [*entrainement, evaluation[0]])
    resume = preparer_jeu(recette(Part("problemes:melange", None)))
    source = resume["sources"]["problemes:melange"]
    assert source["contamines"] == 1 and source["gardes"] == len(entrainement)


def test_les_problemes_generes_ne_sont_pas_pris_pour_des_copies_parce_qu_ils_partagent_des_gabarits(donnees):
    """Entraînement et évaluation écrivent leurs problèmes avec les mêmes phrases : seuls les prénoms et les nombres changent."""
    ecrire_problemes("evaluation", "evaluation", 1_000_000, 200)
    ecrire_problemes("entrainement", "entrainement", 0, 200)
    resume = preparer_jeu(recette(Part("problemes:entrainement", None)))
    source = resume["sources"]["problemes:entrainement"]
    assert source["contamines"] == 0 and source["gardes"] == source["lus"] > 150


def test_un_exemple_de_conversation_qui_copie_un_probleme_d_evaluation_est_ecarte(donnees):
    evaluation = ecrire_problemes("evaluation", "evaluation", 1_000_000, 10)
    copie = {
        "tours": [{"role": "utilisateur", "texte": "Peux-tu résoudre ceci ? " + evaluation[3].enonce},
                  {"role": "assistant", "texte": "Je crois que oui, mais pas ici."}],
        "domaine": "essai", "origine": "copie",
    }
    ecrire_source("luth2_conversation", [conversation(1), copie])
    resume = preparer_jeu(recette(Part("luth2_conversation", None)))
    assert resume["sources"]["luth2_conversation"]["contamines"] == 1


def test_humaneval_fr_une_fois_telecharge_decontamine_aussi(donnees):
    prompt = "def somme_des_carres(liste) : renvoie la somme des carrés des éléments de la liste donnée en entrée"
    ecrire_elements(sous_forge_donnees("humaneval_fr", "conversations"), PREFIXE, [{"task_id": "FR/0", "prompt": prompt}])
    copie = {
        "tours": [{"role": "utilisateur", "texte": "Écris : " + prompt}, {"role": "assistant", "texte": "D'accord."}],
        "domaine": "essai", "origine": "copie",
    }
    ecrire_source("luth2_conversation", [conversation(1), copie])
    resume = preparer_jeu(recette(Part("luth2_conversation", None)))
    assert resume["sources"]["luth2_conversation"]["contamines"] == 1
    assert "humaneval_fr" in resume["decontamination"]["jeux"]


# --- Le jeu écrit ---------------------------------------------------------------------------------------


def test_train_et_val_sont_disjoints_et_couvrent_tout(donnees):
    ecrire_source("luth2_conversation", [conversation(i) for i in range(80)])
    resume = preparer_jeu(recette(Part("luth2_conversation", None), part_validation=0.3))
    dossier = donnees / "affinage" / "essai"
    train, val = etiquettes(textes_du_jeu(dossier, "train")), etiquettes(textes_du_jeu(dossier, "val"))
    assert train and val and not set(train) & set(val)
    assert sorted(train + val) == list(range(80)) and resume["sources"]["luth2_conversation"]["gardes"] == 80
    index = lire_index(dossier)
    assert index["sorte"] == "sft" and index["longueur"] == 2048 and index["exemples"] == 80


def test_une_part_de_validation_a_zero_met_tout_en_train(donnees):
    ecrire_source("luth2_conversation", [conversation(i) for i in range(10)])
    preparer_jeu(recette(Part("luth2_conversation", None), part_validation=0.0))
    assert lire_index(donnees / "affinage" / "essai")["rangees"]["val"] == 0


def test_deux_preparations_donnent_le_meme_jeu_a_l_octet_pres(donnees):
    ecrire_source("luth2_conversation", [conversation(i) for i in range(60)])
    ecrire_source("aya_fr", [conversation(i, "A") for i in range(30)])
    r = recette(Part("luth2_conversation", 40), Part("aya_fr", None), Part("systeme_genere", 10), Part("identite", None))
    preparer_jeu(r, sortie=donnees / "un")
    preparer_jeu(r, sortie=donnees / "deux")
    assert contenu_du_dossier(donnees / "un") == contenu_du_dossier(donnees / "deux")
    preparer_jeu(r, sortie=donnees / "un")  # refaire sur un jeu complet ne change rien non plus
    assert contenu_du_dossier(donnees / "un") == contenu_du_dossier(donnees / "deux")


def test_une_preparation_reprise_apres_une_coupure_redonne_le_meme_jeu(donnees, monkeypatch):
    ecrire_source("luth2_conversation", [conversation(i) for i in range(60)])
    r = recette(Part("luth2_conversation", None), Part("identite", None))
    preparer_jeu(r, sortie=donnees / "propre")

    ecrire_vrai = module_jeu._ecrire
    appels = []

    def coupure(chemin, tableau):
        appels.append(chemin.name)
        if len(appels) == 4:  # train/ids, train/appris, train/documents, puis val/ids : le courant saute
            raise OSError("coupure de courant simulée")
        ecrire_vrai(chemin, tableau)

    monkeypatch.setattr(module_jeu, "_ecrire", coupure)
    with pytest.raises(OSError, match="coupure"):
        preparer_jeu(r, sortie=donnees / "coupe")
    assert not (donnees / "coupe" / ".complet").exists()
    with pytest.raises(DonneesManquantes):
        lire_index(donnees / "coupe")
    monkeypatch.setattr(module_jeu, "_ecrire", ecrire_vrai)
    preparer_jeu(r, sortie=donnees / "coupe")
    assert contenu_du_dossier(donnees / "coupe") == contenu_du_dossier(donnees / "propre")


def test_une_coupure_ne_laisse_pas_un_ancien_jeu_complet_avec_de_nouveaux_identifiants(donnees, monkeypatch):
    ecrire_source("luth2_conversation", [conversation(i) for i in range(20)])
    r = recette(Part("luth2_conversation", None))
    preparer_jeu(r, sortie=donnees / "jeu")
    monkeypatch.setattr(module_jeu, "_ecrire", lambda chemin, tableau: (_ for _ in ()).throw(OSError("disque")))
    with pytest.raises(OSError):
        preparer_jeu(recette(Part("luth2_conversation", 5)), sortie=donnees / "jeu")
    assert not (donnees / "jeu" / ".complet").exists()


def test_exemples_max_tire_au_hasard_et_les_premiers_sont_les_memes_d_une_recette_a_l_autre(donnees):
    ecrire_source("luth2_conversation", [conversation(i) for i in range(50)])
    grande = preparer_jeu(recette(Part("luth2_conversation", 30)), sortie=donnees / "grande")
    petite = preparer_jeu(recette(Part("luth2_conversation", 10)), sortie=donnees / "petite")
    assert grande["sources"]["luth2_conversation"]["gardes"] == 30 and petite["sources"]["luth2_conversation"]["gardes"] == 10
    grands, petits = ids_gardes(donnees / "grande"), ids_gardes(donnees / "petite")
    assert grands[:10] == petits  # les premiers de l'ordre tiré
    tires = etiquettes(textes_du_jeu(donnees / "grande", "train") + textes_du_jeu(donnees / "grande", "val"))
    assert sorted(tires) != list(range(30))  # tiré au hasard, pas les 30 premiers
    autre = preparer_jeu(recette(Part("luth2_conversation", 10), graine=9), sortie=donnees / "autre")
    assert ids_gardes(donnees / "autre") != petits and autre["sources"]["luth2_conversation"]["gardes"] == 10


def test_exemples_max_plus_grand_que_la_source_prend_tout(donnees):
    ecrire_source("luth2_conversation", [conversation(i) for i in range(5)])
    resume = preparer_jeu(recette(Part("luth2_conversation", 1000)))
    assert resume["sources"]["luth2_conversation"]["lus"] == 5


def test_les_doublons_sont_retires_sur_le_premier_tour_de_l_utilisateur(donnees):
    a = conversation(1)
    autre_reponse = conversation(1)
    autre_reponse["tours"][1]["texte"] = "Une réponse tout autre, mais la même question."
    espaces = conversation(1)
    espaces["tours"][0]["texte"] += "   "  # le nettoyage retire les espaces de fin
    ecrire_source("luth2_conversation", [a, conversation(2), autre_reponse, espaces])
    ecrire_source("aya_fr", [conversation(1), conversation(3, "A")])  # même question dans une autre source
    resume = preparer_jeu(recette(Part("luth2_conversation", None), Part("aya_fr", None)))
    assert resume["sources"]["luth2_conversation"]["doublons"] == 2 and resume["sources"]["luth2_conversation"]["gardes"] == 2
    assert resume["sources"]["aya_fr"]["doublons"] == 1 and resume["sources"]["aya_fr"]["gardes"] == 1


def test_les_exemples_trop_longs_sont_ecartes_et_comptes(donnees):
    longue = conversation(9)
    longue["tours"][1]["texte"] = " ".join(f"{mot(i)}" for i in range(300))
    ecrire_source("luth2_conversation", [conversation(1), conversation(2), longue])
    resume = preparer_jeu(recette(Part("luth2_conversation", None), jetons_max_exemple=120, longueur=200))
    source = resume["sources"]["luth2_conversation"]
    assert (source["trop_longs"], source["gardes"], source["lus"]) == (1, 2, 3)
    assert lire_index(donnees / "affinage" / "essai")["longueur"] == 200


def test_les_identifiants_gardes_sont_ecrits_a_cote_du_jeu(donnees):
    ecrire_source("luth2_conversation", [conversation(i) for i in range(12)])
    preparer_jeu(recette(Part("luth2_conversation", None)))
    dossier = donnees / "affinage" / "essai"
    ids = ids_gardes(dossier)
    assert len(ids) == len(set(ids)) == 12 and all(re.fullmatch(r"[0-9a-f]{40}", i) for i in ids)
    from forge.donnees.nettoyage import empreinte

    assert set(ids) == {empreinte(conversation(i)["tours"][0]["texte"]) for i in range(12)}


def test_systeme_genere_et_identite(donnees):
    ecrire_source("luth2_conversation", [conversation(i) for i in range(200)])
    resume = preparer_jeu(
        recette(Part("luth2_conversation", 20), Part("systeme_genere", 50), Part("identite", None), part_validation=0.2)
    )
    identite = resume["sources"]["identite"]
    assert identite["lus"] == identite["gardes"] == 2 * len(IDENTITE) >= 60
    assert identite["doublons"] == 0  # chaque couple est écrit avec et sans message système, voulu
    systeme = resume["sources"]["systeme_genere"]
    assert 30 <= systeme["gardes"] <= 50 and systeme["doublons"] == 0
    dossier = donnees / "affinage" / "essai"
    tout = textes_du_jeu(dossier, "train") + textes_du_jeu(dossier, "val")
    assert any("Je m" in t and "La Forge IA" in t for t in tout)
    # Les questions de la base de `systeme_genere` ne reprennent pas celles de la part principale.
    etiquettes_luth = etiquettes(tout)
    assert len(etiquettes_luth) == len(set(etiquettes_luth))


def test_les_couples_d_identite_restent_du_meme_cote_de_la_validation(donnees):
    preparer_jeu(recette(Part("identite", None), part_validation=0.5))
    dossier = donnees / "affinage" / "essai"
    train = " ".join(textes_du_jeu(dossier, "train"))
    val = " ".join(textes_du_jeu(dossier, "val"))
    for question, _ in IDENTITE:
        assert (question in train) != (question in val)


def test_les_problemes_donnent_une_pensee_et_une_reponse(donnees):
    problemes = ecrire_problemes("entrainement-essai", "entrainement", 0, 30)
    resume = preparer_jeu(recette(Part("problemes:entrainement-essai", 20), part_validation=0.0))
    assert resume["sources"]["problemes:entrainement-essai"]["lus"] == 20
    dossier = donnees / "affinage" / "essai"
    bruts = np.fromfile(dossier / "train" / "ids.bin", dtype="<u2")
    assert TOK.id_special("<|pensee|>") in bruts and TOK.id_special("<|fin_pensee|>") in bruts
    assert conversation_de_probleme(problemes[0])[1].pensee  # le gabarit de la tâche 9 est celui qui est encodé


def test_les_licences_de_l_index_sont_celles_des_sources(donnees):
    ecrire_source("luth2_conversation", [conversation(i) for i in range(10)])
    ecrire_source("aya_fr", [conversation(i, "A") for i in range(10)])
    ecrire_source("oasst2_fr", [conversation(i, "O") for i in range(10)])
    ecrire_problemes("entrainement-essai", "entrainement", 0, 10)
    resume = preparer_jeu(
        recette(Part("luth2_conversation", None), Part("aya_fr", None), Part("oasst2_fr", None),
                Part("systeme_genere", 5), Part("identite", None), Part("problemes:entrainement-essai", None))
    )
    sources = lire_index(donnees / "affinage" / "essai")["sources"]
    assert sources == resume["sources"]
    for nom in ("luth2_conversation", "aya_fr", "oasst2_fr"):
        assert sources[nom]["licence"] == SOURCES_CONVERSATIONS[nom].licence
        assert sources[nom]["lien"] == SOURCES_CONVERSATIONS[nom].url_licence
    assert "MIT" in sources["identite"]["licence"] and sources["identite"]["lien"].startswith("https://")
    assert "MIT" in sources["problemes:entrainement-essai"]["licence"]
    assert "MIT" in sources["systeme_genere"]["licence"] and "CC BY 4.0" in sources["systeme_genere"]["licence"]
    for source in sources.values():
        assert {"lus", "gardes", "doublons", "contamines", "trop_longs", "licence", "lien"} <= set(source)


def test_une_recette_dont_deux_parts_ont_la_meme_source_est_refusee():
    with pytest.raises(ValueError, match="aya_fr"):
        recette(Part("aya_fr", 5), Part("aya_fr", 6))


def test_une_part_a_zero_exemple_est_refusee():
    with pytest.raises(ValueError, match="au moins 1"):
        Part("identite", 0)


def test_un_jeu_sans_aucun_exemple_est_refuse_et_rien_n_est_ecrit(donnees):
    ecrire_source("ifeval_fr", [{"cle": "1", "invite": "Écris un poème sur la mer.", "usage": "evaluation"}])
    copie = {
        "tours": [{"role": "utilisateur", "texte": "écris un poème sur la mer"}, {"role": "assistant", "texte": "Non."}],
        "domaine": "essai", "origine": "c",
    }
    ecrire_source("luth2_conversation", [copie])
    with pytest.raises(ValueError, match="aucun exemple"):
        preparer_jeu(recette(Part("luth2_conversation", None)))
    assert not (donnees / "affinage" / "essai" / ".complet").exists()


# --- La commande -------------------------------------------------------------------------------------------


def test_la_commande_preparer(donnees, monkeypatch, capsys):
    ecrire_source("luth2_conversation", [conversation(i) for i in range(20)])
    monkeypatch.setitem(RECETTES, "essai-cli", recette(Part("luth2_conversation", None), Part("identite", None), nom="essai-cli"))
    assert principal.main(["preparer", "--recette", "essai-cli"]) == 0
    sortie = capsys.readouterr().out
    assert "luth2_conversation" in sortie and "identite" in sortie and "\u202f" in sortie
    assert "20 lus" in sortie and "contaminés" in sortie and "0 invalides" in sortie and str(donnees / "affinage" / "essai-cli") in sortie
    assert (donnees / "affinage" / "essai-cli" / ".complet").is_file()
    assert principal.main(["preparer", "--recette", "essai-cli", "--sortie", "autre-nom"]) == 0
    assert (donnees / "affinage" / "autre-nom" / ".complet").is_file()


def test_la_commande_dit_quoi_faire_quand_une_source_manque(capsys):
    assert principal.main(["preparer", "--recette", "sft-1.7"]) == 1
    erreur = capsys.readouterr().err
    assert erreur.startswith("Erreur\u202f:") and "python -m forge conversations --source" in erreur


def test_la_commande_refuse_une_recette_inconnue(capsys):
    with pytest.raises(SystemExit):
        principal.main(["preparer", "--recette", "n_importe_quoi"])
    assert "sft-1.7" in capsys.readouterr().err


def test_la_commande_refuse_une_recette_d_evaluation(monkeypatch, capsys):
    monkeypatch.setitem(RECETTES, "piege", recette(Part("ifeval_fr", None), nom="piege"))
    assert principal.main(["preparer", "--recette", "piege"]) == 1
    assert "ifeval_fr" in capsys.readouterr().err


def test_ctrl_c_pendant_la_preparation_dit_de_relancer(donnees, monkeypatch, capsys):
    monkeypatch.setitem(RECETTES, "essai-cli", recette(Part("identite", None), nom="essai-cli"))
    monkeypatch.setattr(recettes, "preparer_jeu", lambda *a, **k: (_ for _ in ()).throw(KeyboardInterrupt()))
    assert principal.main(["preparer", "--recette", "essai-cli"]) == 130
    assert "Relance la même commande" in capsys.readouterr().err
