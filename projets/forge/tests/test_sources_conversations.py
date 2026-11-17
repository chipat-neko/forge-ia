"""Les sources de conversations et d'évaluation de la vague 2, et leur téléchargement repris par fragments.

Aucun test n'ouvre le réseau : le flux `datasets` se construit à partir de petits fichiers Parquet
écrits dans `tmp_path` (`load_dataset` seul est détourné vers eux), comme `test_telechargement.py`.
"""

import gzip
import json
from dataclasses import replace
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from forge.conversation import sources as sources_conv
from forge.conversation import telechargement as tele
from forge.conversation.sources import (
    GENERATEURS_GARDES,
    SOURCES_AMONT_ECARTEES,
    SOURCES_CONVERSATIONS,
    LigneEcartee,
    UsageInterdit,
    source_d_entrainement,
)
from forge.donnees.telechargement import EtatDuFluxRefuse
from forge.fragments import lire_elements

NOMS = (
    "luth2_conversation",
    "luth2_code",
    "aya_fr",
    "oasst2_fr",
    "opc_educational",
    "ifeval_fr",
    "mgsm_rev2_fr",
    "gsm8k_platinum_fr",
    "humaneval",
)
EVALUATION = ("ifeval_fr", "mgsm_rev2_fr", "gsm8k_platinum_fr", "humaneval")


# --- Le registre ---------------------------------------------------------------------------------


def test_le_registre_a_les_neuf_sources_de_la_fiche():
    assert tuple(SOURCES_CONVERSATIONS) == NOMS
    for nom, source in SOURCES_CONVERSATIONS.items():
        assert source.nom == nom and source.licence and source.url_licence.startswith("https://")
        assert source.usage == ("evaluation" if nom in EVALUATION else "entrainement")
    assert SOURCES_CONVERSATIONS["luth2_conversation"].depot == "kurakurai/Luth-2-Post-Training-SFT"
    assert SOURCES_CONVERSATIONS["mgsm_rev2_fr"].configuration == "fr"
    assert SOURCES_CONVERSATIONS["opc_educational"].configuration == "educational_instruct"
    assert SOURCES_CONVERSATIONS["humaneval"].sorte == "humaneval"
    assert GENERATEURS_GARDES == ("Qwen/",)
    assert SOURCES_AMONT_ECARTEES == ("stackoverflow", "smoltalk", "magpie")


def test_une_source_d_evaluation_ne_peut_pas_servir_a_l_entrainement():
    for nom in EVALUATION:
        with pytest.raises(UsageInterdit, match=nom):
            source_d_entrainement(nom)
        with pytest.raises(UsageInterdit, match="évaluation"):
            tele.lire_pour_entrainement(SOURCES_CONVERSATIONS[nom])
    assert source_d_entrainement("aya_fr") is SOURCES_CONVERSATIONS["aya_fr"]
    with pytest.raises(KeyError, match="inconnue"):
        source_d_entrainement("n_importe_quoi")


def test_humaneval_ne_peut_pas_etre_declare_pour_l_entrainement():
    base = SOURCES_CONVERSATIONS["humaneval"]
    with pytest.raises(ValueError, match="évaluation"):
        replace(base, usage="entrainement")


# --- Luth-2 ---------------------------------------------------------------------------------------


def _luth(domaine="knowledge", generateur="Qwen/Qwen3-32B", source="nvidia/Nemotron-Post-Training-Dataset-v2",
          outil=False, reponse="Bonjour, voici la réponse.", identifiant="x"):
    appel = [{"name": "chercher"}] if outil else []
    return {
        "id": identifiant,
        "domain": domaine,
        "source": source,
        "generator": generateur,
        "tools": [],
        "messages": [
            {"role": "user", "content": "Une question ?", "tool_calls": []},
            {"role": "assistant", "content": reponse, "tool_calls": appel},
        ],
    }


def _convertir(nom: str, ligne: dict) -> list[dict]:
    return list(SOURCES_CONVERSATIONS[nom].convertir(ligne))


def _raison(nom: str, ligne: dict) -> str:
    with pytest.raises(LigneEcartee) as erreur:
        _convertir(nom, ligne)
    return erreur.value.raison


def test_luth_garde_une_conversation_qwen_sans_outil():
    [element] = _convertir("luth2_conversation", _luth(identifiant="luth-7"))
    assert element["tours"] == [
        {"role": "utilisateur", "texte": "Une question ?"},
        {"role": "assistant", "texte": "Bonjour, voici la réponse."},
    ]
    assert element["domaine"] == "knowledge" and element["origine"] == "luth-7"
    assert _convertir("luth2_conversation", _luth(domaine="if"))


def test_luth_ecarte_chaque_cas_avec_sa_raison():
    assert _raison("luth2_conversation", _luth(outil=True)) == "appel_d_outil"
    assert _raison("luth2_conversation", _luth(generateur="google/gemma-4-26b-a4b-it")) == "generateur"
    assert _raison("luth2_conversation", _luth(generateur="")) == "generateur"
    assert _raison("luth2_conversation", _luth(source="nvidia/Nemotron-StackOverflow")) == "source_amont"
    assert _raison("luth2_conversation", _luth(source="HuggingFaceTB/smoltalk2")) == "source_amont"
    assert _raison("luth2_conversation", _luth(source="Magpie-Align/Magpie-Pro")) == "source_amont"
    assert _raison("luth2_conversation", _luth(domaine="math")) == "domaine"
    assert _raison("luth2_conversation", _luth(domaine="tool_call")) == "domaine"
    avec_role_outil = _luth()
    avec_role_outil["messages"].insert(1, {"role": "tool", "content": "résultat", "tool_calls": []})
    assert _raison("luth2_conversation", avec_role_outil) == "appel_d_outil"
    assert _raison("luth2_conversation", _luth(reponse="  ")) == "conversation_invalide"


def test_les_sources_amont_ecartees_se_lisent_en_minuscules_dans_la_source(monkeypatch):
    monkeypatch.setattr(sources_conv, "SOURCES_AMONT_ECARTEES", ("zzz",))
    assert _raison("luth2_conversation", _luth(source="Truc/ZZZ-data")) == "source_amont"
    # La liste est lue à chaque ligne : une source qui n'y est plus n'est plus écartée.
    assert _convertir("luth2_conversation", _luth(source="nvidia/StackOverflow"))


def test_luth_code_veut_un_bloc_python():
    avec = _luth(domaine="code", reponse="Voici :\n```python\nprint('a')\n```")
    sans = _luth(domaine="code", reponse="Voici :\n```javascript\nconsole.log(1)\n```")
    assert _convertir("luth2_code", avec)
    assert _raison("luth2_code", sans) == "pas_de_python"
    assert _raison("luth2_code", _luth(domaine="knowledge")) == "domaine"
    assert _raison("luth2_code", {**avec, "generator": "google/gemma-4"}) == "generateur"


# --- Aya, OASST2, OPC -----------------------------------------------------------------------------


def test_aya_garde_le_francais():
    ligne = {"inputs": "Quelle est la capitale ?", "targets": "Paris.", "language_code": "fra"}
    [element] = _convertir("aya_fr", ligne)
    assert [t["role"] for t in element["tours"]] == ["utilisateur", "assistant"]
    assert element["tours"][1]["texte"] == "Paris."
    assert _raison("aya_fr", {**ligne, "language_code": "som"}) == "langue"


def _message(identifiant, role, texte, creation, rang=None, lang="fr", reponses=()):
    return {
        "message_id": identifiant, "role": role, "text": texte, "lang": lang, "rank": rang,
        "created_date": creation, "deleted": False, "review_result": True, "replies": list(reponses),
    }


def _arbre_de_six_messages(lang_racine="fr"):
    racine = _message(
        "r", "prompter", "Bonjour, qui es-tu ?", "2023-01-01T00:00:00+00:00", lang=lang_racine,
        reponses=[
            _message("a1", "assistant", "Réponse de rang 1", "2023-01-01T00:01:00+00:00", rang=1),
            _message(
                "a0", "assistant", "Réponse de rang 0", "2023-01-01T00:02:00+00:00", rang=0,
                reponses=[
                    _message("p-tard", "prompter", "Question tardive", "2023-01-01T00:09:00+00:00"),
                    _message(
                        "p-tot", "prompter", "Question ancienne", "2023-01-01T00:05:00+00:00",
                        reponses=[_message("a-fin", "assistant", "Réponse finale", "2023-01-01T00:06:00+00:00", rang=0)],
                    ),
                ],
            ),
        ],
    )
    return {"message_tree_id": "r", "tree_state": "ready_for_export", "prompt": racine}


def test_oasst2_un_arbre_de_six_messages_donne_la_conversation_attendue():
    [element] = _convertir("oasst2_fr", _arbre_de_six_messages())
    assert [(t["role"], t["texte"]) for t in element["tours"]] == [
        ("utilisateur", "Bonjour, qui es-tu ?"),
        ("assistant", "Réponse de rang 0"),
        ("utilisateur", "Question ancienne"),  # la plus ancienne des deux réponses d'utilisateur
        ("assistant", "Réponse finale"),
    ]
    assert element["origine"] == "r"


def test_oasst2_ecarte_les_arbres_non_francais():
    assert _raison("oasst2_fr", _arbre_de_six_messages(lang_racine="es")) == "langue"


def test_oasst2_coupe_au_premier_message_d_une_autre_langue_et_finit_par_l_assistant():
    arbre = _arbre_de_six_messages()
    a0 = arbre["prompt"]["replies"][1]
    a0["replies"][1]["replies"][0]["lang"] = "en"  # la réponse finale, hors du français
    [element] = _convertir("oasst2_fr", arbre)
    # « Question ancienne » resterait en dernier : on la retire, la conversation finit par l'assistant.
    assert [t["role"] for t in element["tours"]] == ["utilisateur", "assistant"]


def test_oasst2_ignore_les_reponses_supprimees_ou_refusees():
    arbre = _arbre_de_six_messages()
    arbre["prompt"]["replies"][1]["deleted"] = True  # la réponse de rang 0 est supprimée
    [element] = _convertir("oasst2_fr", arbre)
    assert [t["texte"] for t in element["tours"]] == ["Bonjour, qui es-tu ?", "Réponse de rang 1"]


def test_oasst2_une_racine_sans_reponse_est_ecartee():
    arbre = {"message_tree_id": "t", "prompt": _message("r", "prompter", "Seule", "2023-01-01T00:00:00+00:00")}
    assert _raison("oasst2_fr", arbre) == "sans_reponse"


def test_opc_garde_instruction_code_et_tests():
    ligne = {
        "instruction": "Écris une fonction qui double un nombre.",
        "code": "def double(x):\n    return 2 * x",
        "entry_point": "double",
        "testcase": ["assert double(2) == 4", "assert double(0) == 0"],
        "seq_id": 660113403,  # un entier dans le vrai jeu
    }
    [element] = _convertir("opc_educational", ligne)
    assert element["origine"] == "660113403"
    assert element["instruction"] == ligne["instruction"] and element["code"] == ligne["code"]
    assert element["tests"] == ligne["testcase"] and element["entry_point"] == "double"
    # La colonne peut aussi être une chaîne qui décrit une liste.
    [autre] = _convertir("opc_educational", {**ligne, "testcase": "['assert double(2) == 4']"})
    assert autre["tests"] == ["assert double(2) == 4"]
    assert _raison("opc_educational", {**ligne, "code": ""}) == "incomplet"


# --- Les évaluations ------------------------------------------------------------------------------


def test_ifeval_fr():
    ligne = {
        "key": "7",
        "prompt": "Écris un poème en majuscules.",
        "instruction_id_list": ["fr:change_case:english_capital"],
        "kwargs": [{}],
    }
    [element] = _convertir("ifeval_fr", ligne)
    assert element == {
        "cle": "7", "invite": "Écris un poème en majuscules.",
        "instruction_id_list": ["fr:change_case:english_capital"], "kwargs": [{}], "usage": "evaluation",
    }
    [chaine] = _convertir("ifeval_fr", {**ligne, "kwargs": "[{}]", "instruction_id_list": "['a']"})
    assert chaine["kwargs"] == [{}] and chaine["instruction_id_list"] == ["a"]


def test_mgsm_rev2_fr():
    ligne = {"question": "Combien font 2 + 3 ?", "answer_number": 5, "answer": None}
    [element] = _convertir("mgsm_rev2_fr", ligne)
    assert element["question"] == "Combien font 2 + 3 ?" and element["reponse"] == "5"
    assert element["usage"] == "evaluation"
    [flottant] = _convertir("mgsm_rev2_fr", {**ligne, "answer_number": 18.0})
    assert flottant["reponse"] == "18"


def test_gsm8k_platinum_fr_prend_ce_qui_suit_les_quatre_diezes():
    ligne = {"question": "Combien ?", "answer": "Janet vend 16 - 3 = <<16-3=13>>13 œufs.\n#### 1 118"}
    [element] = _convertir("gsm8k_platinum_fr", ligne)
    assert element["reponse"] == "1118" and element["question"] == "Combien ?"
    [sans] = _convertir("gsm8k_platinum_fr", {**ligne, "answer": "42"})
    assert sans["reponse"] == "42"


def test_humaneval():
    ligne = {
        "task_id": "HumanEval/0", "prompt": "def f(x):\n    ", "test": "def check(c): pass",
        "entry_point": "f", "canonical_solution": "    return x\n",
    }
    [element] = _convertir("humaneval", ligne)
    assert {k: element[k] for k in ligne} == ligne and element["usage"] == "evaluation"


# --- Le téléchargement, sans réseau ---------------------------------------------------------------

PAR_FICHIER = 40
FICHIERS = 3
TOTAL = FICHIERS * PAR_FICHIER
PAR_FRAGMENT = 7


def _lignes_luth() -> list[dict]:
    """120 lignes : un quart écarté (outil, Gemma, StackOverflow, maths, à tour de rôle), le reste gardé."""
    lignes = []
    for i in range(TOTAL):
        genre = i % 8
        if genre == 1:
            lignes.append(_luth(outil=True, identifiant=f"l{i}"))
        elif genre == 3:
            lignes.append(_luth(generateur="google/gemma-4", identifiant=f"l{i}"))
        elif genre == 5:
            lignes.append(_luth(source="nvidia/Nemotron-StackOverflow", identifiant=f"l{i}"))
        elif genre == 7:
            lignes.append(_luth(domaine="math", identifiant=f"l{i}"))
        else:
            lignes.append(_luth(identifiant=f"l{i}", reponse=f"Réponse {i}"))
    return lignes


_SCHEMA_LUTH = pa.schema(
    [
        ("id", pa.string()), ("domain", pa.string()), ("source", pa.string()), ("generator", pa.string()),
        ("tools", pa.list_(pa.string())),
        (
            "messages",
            pa.list_(pa.struct([
                ("role", pa.string()), ("content", pa.string()),
                ("tool_calls", pa.list_(pa.struct([("name", pa.string())]))),
            ])),
        ),
    ]
)


@pytest.fixture
def parquets_luth(tmp_path: Path) -> list[str]:
    dossier = tmp_path / "amont"
    dossier.mkdir()
    lignes = _lignes_luth()
    chemins = []
    for f in range(FICHIERS):
        part = lignes[f * PAR_FICHIER:(f + 1) * PAR_FICHIER]
        chemin = dossier / f"part-{f}.parquet"
        pq.write_table(pa.Table.from_pylist(part, schema=_SCHEMA_LUTH), chemin, row_group_size=10)
        chemins.append(str(chemin))
    return chemins


class Espion:
    """Entoure le vrai lecteur : note les lignes données, et coupe le « réseau » si on le dit."""

    def __init__(self, lecteur, coupe_apres: int | None) -> None:
        self.lecteur = lecteur
        self.coupe_apres = coupe_apres
        self.lus: list[str] = []

    def __iter__(self):
        for ligne in self.lecteur:
            if self.coupe_apres is not None and len(self.lus) == self.coupe_apres:
                raise ConnectionError("réseau coupé")
            self.lus.append(ligne["id"])
            yield ligne

    def etat(self):
        return self.lecteur.etat()

    def close(self):
        self.lecteur.close()


@pytest.fixture
def flux(monkeypatch, parquets_luth):
    """Détourne `load_dataset` vers les fichiers Parquet ; renvoie espions, appels du lecteur, coupures."""
    from datasets import load_dataset as vrai

    monkeypatch.setattr(
        "datasets.load_dataset",
        lambda *a, **k: vrai("parquet", data_files=parquets_luth, split="train", streaming=True),
    )
    espions: list[Espion] = []
    appels: list[dict] = []
    coupures: list[int | None] = []
    vrai_lecteur = tele.lecteur_conversations

    def lecteur(source, etat_du_flux=None, ignorer=0):
        appels.append({"etat_du_flux": etat_du_flux, "ignorer": ignorer})
        espion = Espion(vrai_lecteur(source, etat_du_flux, ignorer), coupures.pop(0) if coupures else None)
        espions.append(espion)
        return espion

    monkeypatch.setattr(tele, "lecteur_conversations", lecteur)
    return espions, appels, coupures


@pytest.fixture(autouse=True)
def donnees_par_defaut(tmp_path, monkeypatch):
    monkeypatch.setenv("FORGE_DONNEES", str(tmp_path / "donnees"))


def _telecharger(messages=None, source="luth2_conversation", **options):
    options.setdefault("par_fragment", PAR_FRAGMENT)
    return tele.telecharger_source(
        SOURCES_CONVERSATIONS[source], journal=messages.append if messages is not None else None, **options
    )


def _fragments(dossier: Path) -> dict[str, bytes]:
    return {f.name: f.read_bytes() for f in sorted(dossier.glob("conversations-*.jsonl.gz"))}


def _etat(dossier: Path) -> dict:
    return json.loads((dossier / "etat.json").read_text(encoding="utf-8"))


def _reference(tmp_path, monkeypatch, flux) -> dict[str, bytes]:
    """Un téléchargement d'une traite, dans ses propres données : les fragments de référence."""
    monkeypatch.setenv("FORGE_DONNEES", str(tmp_path / "reference"))
    espions, *_ = flux
    dossier = _telecharger()
    assert len(espions[-1].lus) == TOTAL
    monkeypatch.setenv("FORGE_DONNEES", str(tmp_path / "donnees"))
    return _fragments(dossier)


def _dossier(tmp_path) -> Path:
    return tmp_path / "donnees" / "conversations" / "luth2_conversation"


def test_le_telechargement_trie_et_compte_les_raisons(flux, tmp_path):
    dossier = _telecharger()
    assert dossier == _dossier(tmp_path)
    complet = json.loads((dossier / ".complet").read_text(encoding="utf-8"))
    # 120 lignes : 15 de chaque cas écarté, donc 60 gardées.
    assert complet["nom"] == "luth2_conversation" and complet["usage"] == "entrainement"
    assert complet["licence"] == SOURCES_CONVERSATIONS["luth2_conversation"].licence
    assert complet["lus"] == TOTAL and complet["gardes"] == 60 and complet["epuisee"] is True
    assert complet["ecartes"] == {"appel_d_outil": 15, "generateur": 15, "source_amont": 15, "domaine": 15}
    elements = list(lire_elements(dossier, "conversations"))
    assert len(elements) == 60
    assert {e["domaine"] for e in elements} == {"knowledge"}
    assert all(e["tours"][-1]["role"] == "assistant" for e in elements)
    assert len(_fragments(dossier)) == 9  # 60 éléments, 7 par fragment


def test_exemples_max_arrete_le_telechargement(flux):
    dossier = _telecharger(exemples_max=20)
    complet = json.loads((dossier / ".complet").read_text(encoding="utf-8"))
    assert complet["gardes"] == 20 and complet["epuisee"] is False
    assert len(list(lire_elements(dossier, "conversations"))) == 20


def test_une_source_complete_n_est_pas_retelechargee(flux):
    _telecharger()
    espions, *_ = flux
    messages: list[str] = []
    _telecharger(messages)
    assert len(espions) == 1 and any("déjà complet" in m for m in messages)


def test_exemples_max_plus_grand_prolonge_un_dossier_deja_complet(flux):
    _telecharger(exemples_max=10)
    dossier = _telecharger(exemples_max=25)
    assert len(list(lire_elements(dossier, "conversations"))) == 25
    assert len(list(lire_elements(_telecharger(), "conversations"))) == 60  # sans limite : jusqu'au bout


def test_la_reprise_apres_une_coupure_rend_les_memes_fragments(flux, tmp_path, monkeypatch):
    reference = _reference(tmp_path, monkeypatch, flux)
    espions, appels, coupures = flux
    assert len(reference) > 5
    coupures.append(75)
    with pytest.raises(ConnectionError):
        _telecharger()
    dossier = _dossier(tmp_path)
    etat = _etat(dossier)["etat"]
    assert 0 < etat["lus"] <= 75 and etat["etat_du_flux"] is not None
    messages: list[str] = []
    _telecharger(messages)
    # Rien de ce qui est déjà compté n'est relu : le flux repart de son état, sans saut.
    assert appels[-1]["etat_du_flux"] is not None and appels[-1]["ignorer"] == 0
    assert len(espions[-1].lus) == TOTAL - etat["lus"]
    assert not any("ancien état" in m for m in messages)
    assert (dossier / ".complet").exists()
    assert _fragments(dossier) == reference  # octet pour octet
    elements = list(lire_elements(dossier, "conversations"))
    assert len({e["origine"] for e in elements}) == len(elements) == 60  # pas de doublon


def test_la_reprise_survit_a_plusieurs_coupures(flux, tmp_path, monkeypatch):
    reference = _reference(tmp_path, monkeypatch, flux)
    _espions, _appels, coupures = flux
    for coupe in (20, 30, 15):
        coupures.append(coupe)
        with pytest.raises(ConnectionError):
            _telecharger()
    _telecharger()
    assert _fragments(_dossier(tmp_path)) == reference


def test_une_reprise_apres_un_skip_rend_les_memes_fragments(flux, tmp_path, monkeypatch):
    """Un etat.json sans état du flux : la reprise saute les lignes comptées, puis le `skip` est gardé.

    La coupure suivante repart de l'état du flux d'un jeu sauté : il ne se recharge que sur un jeu sauté
    du même nombre (`sautes_a_l_ouverture`), jamais seul.
    """
    reference = _reference(tmp_path, monkeypatch, flux)
    espions, appels, coupures = flux
    dossier = _dossier(tmp_path)
    coupures.append(25)
    with pytest.raises(ConnectionError):
        _telecharger()
    ancien = _etat(dossier)
    comptes = [ancien["etat"]["lus"]]
    assert comptes[0] > 0
    del ancien["etat"]["etat_du_flux"]
    ancien["etat"].pop("sautes_a_l_ouverture", None)
    (dossier / "etat.json").write_text(json.dumps(ancien), encoding="utf-8")

    # Première reprise : l'ancienne voie (relecture et saut), coupée à son tour.
    messages: list[str] = []
    coupures.append(30)
    with pytest.raises(ConnectionError):
        _telecharger(messages)
    assert appels[-1] == {"etat_du_flux": None, "ignorer": comptes[0]}
    assert any("ancien état" in m for m in messages)
    apres = _etat(dossier)["etat"]
    assert apres["lus"] > comptes[0] and apres["etat_du_flux"] is not None
    assert apres["sautes_a_l_ouverture"] == comptes[0]  # le saut du premier départ est gardé

    # Deuxième reprise, coupée, puis troisième : par l'état du flux ET le même saut, jamais l'un sans l'autre.
    comptes.append(apres["lus"])
    for coupe in (30, None):
        messages = []
        coupures.append(coupe)
        if coupe is None:
            _telecharger(messages)
        else:
            with pytest.raises(ConnectionError):
                _telecharger(messages)
        assert appels[-1]["etat_du_flux"] is not None and appels[-1]["ignorer"] == comptes[0]
        assert not any("ancien état" in m for m in messages)
        assert espions[-1].lus[0] == f"l{comptes[-1]}"
        comptes.append(_etat(dossier)["etat"]["lus"])
    assert comptes[-1] == TOTAL
    assert _fragments(dossier) == reference
    assert (dossier / ".complet").exists()


def test_un_etat_du_flux_refuse_n_ecrit_rien_de_faux(flux, tmp_path):
    _espions, _appels, coupures = flux
    dossier = _dossier(tmp_path)
    coupures.append(75)
    with pytest.raises(ConnectionError):
        _telecharger()
    avant = _fragments(dossier)
    etat = _etat(dossier)
    etat["etat"]["etat_du_flux"] = {"examples_iterable": {"shard_idx": "autre source", "shard_example_idx": -3}}
    (dossier / "etat.json").write_text(json.dumps(etat), encoding="utf-8")
    avant_etat = (dossier / "etat.json").read_bytes()
    with pytest.raises(EtatDuFluxRefuse) as erreur:
        _telecharger()
    message = str(erreur.value)
    assert "luth2_conversation" in message and "etat.json" in message
    assert "etat_du_flux" in message and "échouera de nouveau" in message
    assert _fragments(dossier) == avant and (dossier / "etat.json").read_bytes() == avant_etat
    assert not (dossier / ".complet").exists()


def test_ctrl_c_valide_le_fragment_en_cours_et_dit_comment_reprendre(flux, tmp_path, monkeypatch):
    espions, _appels, _coupures = flux
    vrai_lecteur = tele.lecteur_conversations

    def lecteur_qui_demande_la_pause(source, etat_du_flux=None, ignorer=0):
        interne = vrai_lecteur(source, etat_du_flux, ignorer)

        class Demande:
            def __iter__(self_inner):
                for i, ligne in enumerate(interne):
                    if i == 30:  # le « Ctrl+C » arrive pendant la lecture
                        pause_courante[0]._signal_recu(2, None)
                    yield ligne

            def etat(self_inner):
                return interne.etat()

            def close(self_inner):
                interne.close()

        return Demande()

    pause_courante: list = []
    vraie_pause = tele.Pause

    class PauseEspionnee(vraie_pause):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            pause_courante.append(self)

    monkeypatch.setattr(tele, "lecteur_conversations", lecteur_qui_demande_la_pause)
    monkeypatch.setattr(tele, "Pause", PauseEspionnee)
    with pytest.raises(tele.TelechargementEnPause) as pause:
        _telecharger(exemples_max=1000)
    commande = str(pause.value)
    assert "python -m forge conversations --source luth2_conversation --exemples-max 1000" in commande
    dossier = _dossier(tmp_path)
    assert not (dossier / ".complet").exists()
    etat = _etat(dossier)
    # Le tampon en cours est validé : tout ce qui a été gardé est sur le disque, et le flux est tenu.
    assert etat["elements"] == len(list(lire_elements(dossier, "conversations"))) > 0
    assert etat["etat"]["etat_du_flux"] is not None and etat["etat"]["lus"] == 31
    # Reprise : mêmes éléments qu'un téléchargement sans pause, sans doublon.
    monkeypatch.setattr(tele, "lecteur_conversations", vrai_lecteur)
    monkeypatch.setattr(tele, "Pause", vraie_pause)
    _telecharger()
    elements = [e["origine"] for e in lire_elements(dossier, "conversations")]
    attendus = [f"l{i}" for i in range(TOTAL) if i % 8 in (0, 2, 4, 6)]
    assert elements == attendus


def test_un_fragment_compte_qui_manque_est_signale_avant_toute_lecture(flux, tmp_path):
    from forge.erreurs import DonneesManquantes

    _telecharger()
    dossier = _dossier(tmp_path)
    (dossier / "conversations-00002.jsonl.gz").unlink()
    espions, *_ = flux
    avant = len(espions)
    with pytest.raises(DonneesManquantes, match="conversations-00002"):
        _telecharger()
    assert len(espions) == avant


def test_aucun_jeu_d_evaluation_dans_un_jeu_d_entrainement(flux, tmp_path):
    """Un jeu d'évaluation téléchargé porte « evaluation » partout : dans .complet comme dans chaque élément."""
    source = replace(SOURCES_CONVERSATIONS["ifeval_fr"])
    assert source.usage == "evaluation"
    ligne = {"key": "1", "prompt": "Dis bonjour.", "instruction_id_list": ["a"], "kwargs": [{}]}
    assert all(e["usage"] == "evaluation" for e in source.convertir(ligne))
    with pytest.raises(UsageInterdit):
        tele.lire_pour_entrainement(source)


def test_lire_pour_entrainement_relit_une_source_complete(flux, tmp_path):
    _telecharger()
    source = SOURCES_CONVERSATIONS["luth2_conversation"]
    assert len(list(tele.lire_pour_entrainement(source))) == 60


def test_lire_pour_entrainement_refuse_une_source_incomplete(flux, tmp_path):
    from forge.erreurs import DonneesManquantes

    _espions, _appels, coupures = flux
    coupures.append(50)
    with pytest.raises(ConnectionError):
        _telecharger()
    with pytest.raises(DonneesManquantes, match="python -m forge conversations --source luth2_conversation"):
        list(tele.lire_pour_entrainement(SOURCES_CONVERSATIONS["luth2_conversation"]))


def test_le_lecteur_ouvre_le_jeu_avec_le_bon_depot_la_bonne_configuration_et_le_bon_split(monkeypatch):
    appels: list[tuple] = []

    class JeuVide:
        def __iter__(self):
            return iter([])

        def to_iterable_dataset(self):  # un jeu ouvert en entier devient un flux, avec la même reprise
            return self

    monkeypatch.setattr("datasets.load_dataset", lambda *a, **k: appels.append((a, k)) or JeuVide())
    for nom in ("mgsm_rev2_fr", "ifeval_fr", "aya_fr", "humaneval", "opc_educational"):
        source = SOURCES_CONVERSATIONS[nom]
        tele.lecteur_conversations(source)
        args, kwargs = appels[-1]
        assert args[0] == source.depot and kwargs["split"] == source.split
        assert kwargs.get("streaming", False) is source.flux
        assert (args[1:] == (source.configuration,)) if source.configuration else args[1:] == ()
    assert SOURCES_CONVERSATIONS["mgsm_rev2_fr"].split == "test" and not SOURCES_CONVERSATIONS["mgsm_rev2_fr"].flux


def test_oasst2_lit_le_fichier_des_arbres_ligne_a_ligne(tmp_path, monkeypatch):
    """Le fichier des arbres est téléchargé puis lu comme un flux de lignes de texte, que `convertir` décode."""
    fichier = tmp_path / "arbres.jsonl.gz"
    arbres = [_arbre_de_six_messages(), _arbre_de_six_messages(lang_racine="es")]
    arbres[0]["message_tree_id"], arbres[1]["message_tree_id"] = "fr-1", "es-1"
    with gzip.open(fichier, "wt", encoding="utf-8") as sortie:
        for arbre in arbres:
            sortie.write(json.dumps(arbre, ensure_ascii=False) + "\n")
    demandes: list[dict] = []

    def faux_telechargement(**options):
        demandes.append(options)
        return str(fichier)

    monkeypatch.setattr("huggingface_hub.hf_hub_download", faux_telechargement)
    monkeypatch.setenv("FORGE_DONNEES", str(tmp_path / "donnees"))
    dossier = tele.telecharger_source(SOURCES_CONVERSATIONS["oasst2_fr"], par_fragment=1)
    assert demandes == [{
        "repo_id": "OpenAssistant/oasst2", "filename": "2023-11-05_oasst2_ready.trees.jsonl.gz",
        "repo_type": "dataset",
    }]
    elements = list(lire_elements(dossier, "conversations"))
    assert [e["origine"] for e in elements] == ["fr-1"] and len(elements[0]["tours"]) == 4
    complet = json.loads((dossier / ".complet").read_text(encoding="utf-8"))
    assert complet["lus"] == 2 and complet["gardes"] == 1 and complet["ecartes"] == {"langue": 1}
