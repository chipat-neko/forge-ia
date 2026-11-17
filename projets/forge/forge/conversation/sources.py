"""Les sources de conversations et d'évaluation de la vague 2 : où les lire, sous quelle licence, pour quoi faire.

Chaque source dit où la lire (dépôt Hugging Face, configuration, split), sa licence et son lien, son
**usage** et la fonction `convertir`, qui transforme une ligne du jeu en éléments prêts à écrire.
`docs/donnees.md` (section « Vague 2 : affiner ton IA ») détaille la même chose pour les lecteurs du dépôt.

Deux usages, qui ne se mélangent jamais :

- `"entrainement"` : le jeu peut nourrir un affinage (SFT, DPO, GRPO) ;
- `"evaluation"` : le jeu ne sert qu'à mesurer. IFEval-FR, MGSM-rev2, GSM8K-Platinum-fr et HumanEval sont
  réservés à l'évaluation : leurs énoncés ne doivent jamais se retrouver dans les données d'entraînement,
  sans quoi la mesure serait faussée. Le garde-fou est `source_d_entrainement` (et `lire_pour_entrainement`
  dans `forge.conversation.telechargement`), la seule porte par laquelle un entraînement lit une source.

`convertir` reçoit une ligne (un dictionnaire colonne → valeur) et renvoie ses éléments. Une ligne que la
source écarte lève `LigneEcartee(raison)` : la raison est comptée dans `.complet`.
"""

import ast
import json
import re
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from typing import Literal

from forge.conversation.format import Tour, conversation_vers_json, verifier_conversation

# Les générateurs de réponses dont on garde les lignes (début du nom du modèle) : Qwen3 est sous
# Apache-2.0, sans clause sur l'usage des sorties. Gemma, Llama et GPT sont écartés.
GENERATEURS_GARDES = ("Qwen/",)

# Les sources amont de Luth-2 que l'on écarte (en minuscules, cherchées dans la colonne `source`) :
# StackOverflow est en CC BY-SA ; Smol-Magpie viendrait de Llama (« données », §1.2, non relu).
# La tâche 12 relit les fiches des autres sources amont et complète cette liste.
SOURCES_AMONT_ECARTEES = ("stackoverflow", "smoltalk", "magpie")

Usage = Literal["entrainement", "evaluation"]
Sorte = Literal["conversation", "consignes", "probleme", "code_test", "humaneval"]


class LigneEcartee(Exception):
    """Une ligne que la source ne garde pas ; `raison` est le mot qui la range dans les comptes."""

    def __init__(self, raison: str) -> None:
        super().__init__(raison)
        self.raison = raison


class UsageInterdit(ValueError):
    """Une source réservée à l'évaluation qu'on voulait mettre dans un entraînement."""


@dataclass(frozen=True)
class SourceConversations:
    """Où lire une source de conversations ou d'évaluation, sa licence, son usage et sa conversion.

    `configuration` est le nom de configuration du jeu Hugging Face (ou `None`), `split` le split à lire.
    `fichier`, s'il est donné, est un fichier JSONL du dépôt lu ligne à ligne au lieu du jeu par défaut :
    OASST2 y donne ses arbres de conversation (un arbre par ligne) plutôt que ses messages à plat.
    `flux` : lu en flux (gros jeux) ou ouvert en entier (petits jeux d'évaluation) ; dans les deux cas la
    reprise garde la position du flux. `convertir` : voir le début du module.
    """

    nom: str
    depot: str
    configuration: str | None
    split: str
    licence: str
    url_licence: str
    usage: Usage
    sorte: Sorte
    flux: bool
    convertir: Callable[[dict], Iterable[dict]]
    fichier: str | None = None

    def __post_init__(self) -> None:
        if self.usage not in ("entrainement", "evaluation"):
            raise ValueError(f"{self.nom} : l'usage est « entrainement » ou « evaluation », pas {self.usage!r}.")
        if self.sorte == "humaneval" and self.usage != "evaluation":
            raise ValueError(f"{self.nom} : HumanEval est réservé à l'évaluation, jamais à l'entraînement.")


def source_d_entrainement(nom: str) -> SourceConversations:
    """La source `nom`, si elle peut nourrir un entraînement ; `UsageInterdit` si elle est réservée à l'évaluation."""
    try:
        source = SOURCES_CONVERSATIONS[nom]
    except KeyError:
        raise KeyError(
            f"Source inconnue : {nom!r}. Les sources sont {', '.join(SOURCES_CONVERSATIONS)}."
        ) from None
    exiger_l_entrainement(source)
    return source


def exiger_l_entrainement(source: SourceConversations) -> None:
    """Lève `UsageInterdit` si `source` est réservée à l'évaluation."""
    if source.usage != "entrainement":
        raise UsageInterdit(
            f"{source.nom} est réservée à l'évaluation : on ne la met jamais dans un entraînement, sans "
            "quoi la mesure serait faussée. Utilise-la seulement pour évaluer, ou choisis une source "
            "d'entraînement (python -m forge conversations --liste)."
        )


# --- Les petits outils des conversions ---------------------------------------------------------------

_ROLES = {"user": "utilisateur", "assistant": "assistant", "system": "systeme"}


def _texte(valeur) -> str:
    return valeur if isinstance(valeur, str) else ""


def _conversation(tours: list[Tour], **champs) -> dict:
    """L'élément d'une conversation, ou `LigneEcartee("conversation_invalide")` si elle est mal formée."""
    try:
        verifier_conversation(tours)
    except ValueError:
        raise LigneEcartee("conversation_invalide") from None
    return {**conversation_vers_json(tours), **champs}


def _liste(valeur) -> list:
    """Une colonne qui est une liste, ou la chaîne qui la décrit (JSON ou notation Python)."""
    if isinstance(valeur, str):
        for lire in (json.loads, ast.literal_eval):
            try:
                valeur = lire(valeur)
                break
            except (ValueError, SyntaxError):
                continue
    if isinstance(valeur, (list, tuple)):
        return list(valeur)
    raise LigneEcartee("incomplet")


def _avec_usage(usage: Usage, convertir: Callable[[dict], Iterable[dict]]) -> Callable[[dict], Iterator[dict]]:
    """Marque chaque élément de son usage : un élément d'évaluation le porte jusque dans ses fichiers."""

    def converti(ligne: dict) -> Iterator[dict]:
        for element in convertir(ligne):
            yield {**element, "usage": usage}

    return converti


# --- Luth-2 ---------------------------------------------------------------------------------------------


def _convertir_luth(domaines: tuple[str, ...], exiger_python: bool) -> Callable[[dict], Iterator[dict]]:
    def convertir(ligne: dict) -> Iterator[dict]:
        if ligne.get("domain") not in domaines:
            raise LigneEcartee("domaine")
        if not _texte(ligne.get("generator")).startswith(GENERATEURS_GARDES):
            raise LigneEcartee("generateur")
        messages = ligne.get("messages") or []
        if any(m.get("role") == "tool" or m.get("tool_calls") for m in messages):
            raise LigneEcartee("appel_d_outil")
        origine = _texte(ligne.get("source")).lower()
        if any(motif in origine for motif in SOURCES_AMONT_ECARTEES):
            raise LigneEcartee("source_amont")
        tours = []
        for message in messages:
            role = _ROLES.get(message.get("role"))
            if role is None:
                raise LigneEcartee("conversation_invalide")
            tours.append(Tour(role, _texte(message.get("content"))))
        if exiger_python and not any(t.role == "assistant" and "```python" in t.texte.lower() for t in tours):
            raise LigneEcartee("pas_de_python")
        yield _conversation(tours, domaine=ligne["domain"], origine=_texte(ligne.get("id")))

    return convertir


# --- Aya et OASST2 -----------------------------------------------------------------------------------


def _convertir_aya(ligne: dict) -> Iterator[dict]:
    if ligne.get("language_code") != "fra":
        raise LigneEcartee("langue")
    tours = [Tour("utilisateur", _texte(ligne.get("inputs"))), Tour("assistant", _texte(ligne.get("targets")))]
    yield _conversation(tours, domaine="aya", origine=_texte(ligne.get("user_id")))


def _date(message: dict) -> str:
    return _texte(message.get("created_date"))


def _suivant(noeud: dict) -> dict | None:
    """Le message qui suit `noeud` dans la conversation que l'on garde, ou `None` s'il n'y en a plus.

    Après l'utilisateur : la réponse d'assistant de rang 0 (à défaut, la mieux classée, les réponses sans
    rang passant après). Après l'assistant : la réponse d'utilisateur la plus ancienne. Les réponses
    supprimées ou refusées à la relecture sont ignorées.
    """
    voulu = "assistant" if noeud.get("role") == "prompter" else "prompter"
    candidats = [
        r for r in noeud.get("replies") or []
        if r.get("role") == voulu and not r.get("deleted") and r.get("review_result") is not False
    ]
    if not candidats:
        return None
    if voulu == "assistant":
        return min(candidats, key=lambda r: (r.get("rank") is None, r.get("rank") or 0, _date(r)))
    return min(candidats, key=_date)


def _convertir_oasst2(ligne: dict) -> Iterator[dict]:
    """Un arbre OASST2 (une ligne du fichier des arbres) donne une conversation, en français de bout en bout.

    La ligne est l'arbre lui-même, ou `{"ligne": "<l'arbre en JSON>"}` quand il vient du fichier lu ligne à ligne.
    """
    if isinstance(ligne.get("ligne"), str):
        ligne = json.loads(ligne["ligne"])
    racine = ligne.get("prompt")
    if not isinstance(racine, dict) or racine.get("role") != "prompter":
        raise LigneEcartee("arbre_invalide")
    if racine.get("lang") != "fr":
        raise LigneEcartee("langue")
    tours = [Tour("utilisateur", _texte(racine.get("text")))]
    noeud = racine
    while (suivant := _suivant(noeud)) is not None and suivant.get("lang") == "fr":
        tours.append(Tour("assistant" if suivant["role"] == "assistant" else "utilisateur", _texte(suivant.get("text"))))
        noeud = suivant
    while tours and tours[-1].role != "assistant":  # une conversation finit par l'assistant, qui est appris
        tours.pop()
    if len(tours) < 2:
        raise LigneEcartee("sans_reponse")
    yield _conversation(tours, domaine="oasst2", origine=_texte(ligne.get("message_tree_id")))


# --- Code (OPC) ------------------------------------------------------------------------------------------


def _convertir_opc(ligne: dict) -> Iterator[dict]:
    instruction, code = _texte(ligne.get("instruction")).strip(), _texte(ligne.get("code")).strip()
    if not instruction or not code:
        raise LigneEcartee("incomplet")
    tests = ligne.get("testcase")
    tests = [str(t) for t in _liste(tests)] if tests is not None else []
    if not tests:
        raise LigneEcartee("incomplet")
    yield {
        "instruction": instruction,
        "code": code,
        "tests": tests,
        "entry_point": _texte(ligne.get("entry_point")),
        "origine": str(ligne.get("seq_id", "")),
    }


# --- Les jeux d'évaluation -------------------------------------------------------------------------------


def _convertir_ifeval(ligne: dict) -> Iterator[dict]:
    invite = _texte(ligne.get("prompt")).strip()
    if not invite:
        raise LigneEcartee("incomplet")
    yield {
        "cle": str(ligne.get("key", "")),
        "invite": invite,
        "instruction_id_list": _liste(ligne.get("instruction_id_list")),
        "kwargs": _liste(ligne.get("kwargs")),
    }


def _nombre_en_texte(valeur) -> str:
    """18.0 s'écrit « 18 » ; « 1 118 » (avec des espaces, même insécables) s'écrit « 1118 »."""
    if isinstance(valeur, float) and valeur.is_integer():
        return str(int(valeur))
    return re.sub(r"\s", "", str(valeur)).rstrip(".")


def _convertir_mgsm(ligne: dict) -> Iterator[dict]:
    question = _texte(ligne.get("question")).strip()
    reponse = ligne.get("answer_number")
    if not question or reponse is None:
        raise LigneEcartee("incomplet")
    yield {"question": question, "reponse": _nombre_en_texte(reponse)}


def _convertir_gsm8k(ligne: dict) -> Iterator[dict]:
    question, reponse = _texte(ligne.get("question")).strip(), _texte(ligne.get("answer"))
    final = reponse.rsplit("####", 1)[-1].strip()
    if not question or not final:
        raise LigneEcartee("incomplet")
    yield {"question": question, "reponse": _nombre_en_texte(final)}


def _convertir_humaneval(ligne: dict) -> Iterator[dict]:
    champs = ("task_id", "prompt", "test", "entry_point", "canonical_solution")
    if not all(_texte(ligne.get(c)) for c in champs):
        raise LigneEcartee("incomplet")
    yield {c: ligne[c] for c in champs}


# --- Le registre -----------------------------------------------------------------------------------------

_CC_BY_4 = "https://creativecommons.org/licenses/by/4.0/"
_CC_BY_SA_4 = "https://creativecommons.org/licenses/by-sa/4.0/"
_APACHE_2 = "https://www.apache.org/licenses/LICENSE-2.0"
_MIT = "https://opensource.org/license/mit"
_LICENCE_LUTH = "CC BY 4.0"
_LUTH = "kurakurai/Luth-2-Post-Training-SFT"


def _source(nom, depot, usage, sorte, convertir, licence, url_licence, *, configuration=None, split="train",
            flux=True, fichier=None) -> SourceConversations:
    return SourceConversations(
        nom=nom, depot=depot, configuration=configuration, split=split, licence=licence,
        url_licence=url_licence, usage=usage, sorte=sorte, flux=flux,
        convertir=_avec_usage(usage, convertir), fichier=fichier,
    )


SOURCES_CONVERSATIONS: dict[str, SourceConversations] = {
    s.nom: s
    for s in (
        _source("luth2_conversation", _LUTH, "entrainement", "conversation",
                _convertir_luth(("knowledge", "if"), exiger_python=False), _LICENCE_LUTH, _CC_BY_4),
        _source("luth2_code", _LUTH, "entrainement", "conversation",
                _convertir_luth(("code",), exiger_python=True), _LICENCE_LUTH, _CC_BY_4),
        _source("aya_fr", "CohereLabs/aya_dataset", "entrainement", "conversation", _convertir_aya,
                "Apache-2.0", _APACHE_2),
        _source("oasst2_fr", "OpenAssistant/oasst2", "entrainement", "conversation", _convertir_oasst2,
                "Apache-2.0", _APACHE_2, fichier="2023-11-05_oasst2_ready.trees.jsonl.gz"),
        _source("opc_educational", "OpenCoder-LLM/opc-sft-stage2", "entrainement", "code_test", _convertir_opc,
                "MIT", _MIT, configuration="educational_instruct"),
        _source("ifeval_fr", "kurakurai/IFEval-FR", "evaluation", "consignes", _convertir_ifeval,
                "Apache-2.0", _APACHE_2, flux=False),
        _source("mgsm_rev2_fr", "lightonai/mgsm-rev2", "evaluation", "probleme", _convertir_mgsm,
                "CC BY-SA 4.0", _CC_BY_SA_4, configuration="fr", split="test", flux=False),
        _source("gsm8k_platinum_fr", "cmh/gsm8k-platinum_fr", "evaluation", "probleme", _convertir_gsm8k,
                "MIT", _MIT, split="test", flux=False),
        _source("humaneval", "openai/openai_humaneval", "evaluation", "humaneval", _convertir_humaneval,
                "MIT", _MIT, split="test", flux=False),
    )
}
