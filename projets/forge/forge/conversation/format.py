"""Le format de conversation de « ton IA ».

Une conversation s'écrit en jetons ainsi :

    <|fin_texte|>
    <|systeme|> consignes <|fin_tour|>          (facultatif, au plus un, en premier)
    <|utilisateur|> question <|fin_tour|>
    <|assistant|> [<|pensee|> brouillon <|fin_pensee|>] réponse <|fin_tour|>
    …

Le SFT, la DPO, le GRPO et les évaluations reposent tous sur ce gabarit. La perte
(le masque `appris`) ne porte que sur ce que dit l'assistant, du jeton qui suit
`<|assistant|>` jusqu'à son `<|fin_tour|>` compris : le modèle apprend à écrire sa
pensée, sa réponse et à s'arrêter, mais pas à écrire la question de l'utilisateur.

Un texte qui contient la chaîne `<|fin_tour|>` est encodé comme du texte ordinaire
(`TokenizerOctets.encoder` n'émet jamais de jeton spécial) : personne ne peut
couper un tour en écrivant ce mot dans un message.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from forge.tokenizer import TokenizerOctets

Role = Literal["systeme", "utilisateur", "assistant"]

JETON_DE_DEBUT = "<|fin_texte|>"  # le séparateur de documents du pré-entraînement
_ROLES = ("systeme", "utilisateur", "assistant")


@dataclass(frozen=True)
class Tour:
    """Une prise de parole. `pensee` : brouillon de raisonnement, seulement pour l'assistant."""

    role: Role
    texte: str
    pensee: str | None = None


@dataclass(frozen=True)
class ExempleMasque:
    """Des identifiants et, pour chacun, `True` si c'est une cible apprise."""

    ids: list[int]
    appris: list[bool]


@dataclass(frozen=True)
class Reponse:
    """Ce que le modèle a écrit : texte, pensée éventuelle, ids lus, et s'il a fini son tour."""

    texte: str
    pensee: str | None
    ids: list[int]
    terminee: bool


def verifier_conversation(tours: Sequence[Tour], pour_apprendre: bool = True) -> None:
    """Lève `ValueError` (en nommant le tour fautif, à partir de 1) si la conversation est mal formée."""
    if not tours:
        raise ValueError("La conversation est vide : il faut au moins un tour de l'utilisateur.")
    attendu = "utilisateur"  # le rôle qui doit venir ensuite, hors système
    for rang, tour in enumerate(tours, start=1):
        if tour.role not in _ROLES:
            raise ValueError(
                f"Le tour {rang} a un rôle inconnu : {tour.role!r}. "
                "Les rôles possibles sont « systeme », « utilisateur » et « assistant »."
            )
        if not tour.texte.strip():
            raise ValueError(f"Le texte du tour {rang} ({tour.role}) est vide. Écris un texte ou retire ce tour.")
        if tour.pensee is not None and tour.role != "assistant":
            raise ValueError(
                f"Le tour {rang} ({tour.role}) porte une pensée : seul l'assistant en a une. Retire la pensée."
            )
        if tour.role == "systeme":
            if rang == 2 and tours[0].role == "systeme":
                raise ValueError(
                    f"Le tour {rang} est un deuxième message système : il n'y en a qu'un. Fusionne-le avec le premier."
                )
            if rang != 1:
                raise ValueError(
                    f"Le tour {rang} est un message système : il doit être le premier tour, et il n'y en a qu'un."
                )
            continue
        if tour.role != attendu:
            raise ValueError(
                f"Le tour {rang} est de rôle « {tour.role} » mais on attendait « {attendu} » : "
                "les tours alternent utilisateur, assistant, en commençant par l'utilisateur."
            )
        attendu = "assistant" if tour.role == "utilisateur" else "utilisateur"
    dernier = tours[-1]
    if pour_apprendre and dernier.role != "assistant":
        raise ValueError(
            f"Le dernier tour (tour {len(tours)}) est de rôle « {dernier.role} » : pour apprendre, "
            "la conversation doit finir par un tour de l'assistant (pas d'assistant à apprendre ici)."
        )
    if not pour_apprendre and dernier.role != "utilisateur":
        raise ValueError(
            f"Le dernier tour (tour {len(tours)}) est de rôle « {dernier.role} » : pour faire répondre "
            "le modèle, la conversation doit finir par un tour de l'utilisateur."
        )


def _jetons_du_tour(tok: TokenizerOctets, tour: Tour) -> tuple[list[int], int]:
    """Les jetons d'un tour, et le nombre de jetons du début qui ne sont pas appris."""
    ids = [tok.id_special(f"<|{tour.role}|>")]
    debut_appris = len(ids)
    if tour.role == "assistant" and tour.pensee is not None:
        ids += [tok.id_special("<|pensee|>"), *tok.encoder(tour.pensee), tok.id_special("<|fin_pensee|>")]
    ids += tok.encoder(tour.texte)
    ids.append(tok.id_special("<|fin_tour|>"))
    return ids, debut_appris


def encoder_conversation(tok: TokenizerOctets, tours: Sequence[Tour]) -> ExempleMasque:
    """Encode une conversation complète (qui finit par l'assistant) avec son masque de perte."""
    verifier_conversation(tours, pour_apprendre=True)
    ids = [tok.id_special(JETON_DE_DEBUT)]
    appris = [False]
    for tour in tours:
        jetons, debut_appris = _jetons_du_tour(tok, tour)
        ids += jetons
        appris += [tour.role == "assistant" and i >= debut_appris for i in range(len(jetons))]
    return ExempleMasque(ids=ids, appris=appris)


def invite_de_reponse(tok: TokenizerOctets, tours: Sequence[Tour]) -> list[int]:
    """Les jetons à donner au modèle pour qu'il réponde : les tours, puis `<|assistant|>`."""
    verifier_conversation(tours, pour_apprendre=False)
    ids = [tok.id_special(JETON_DE_DEBUT)]
    for tour in tours:
        ids += _jetons_du_tour(tok, tour)[0]
    ids.append(tok.id_special("<|assistant|>"))
    return ids


def lire_reponse(tok: TokenizerOctets, ids_generes: Sequence[int]) -> Reponse:
    """Lit ce que le modèle a écrit après `<|assistant|>`, en s'arrêtant au premier `<|fin_tour|>`."""
    ids = [int(i) for i in ids_generes]
    fin_tour = tok.id_special("<|fin_tour|>")
    terminee = fin_tour in ids
    if terminee:
        ids = ids[: ids.index(fin_tour)]

    def sans_speciaux(morceau: Sequence[int]) -> str:
        return tok.decoder([i for i in morceau if i < tok.premier_special])

    pensee = None
    corps = ids
    if ids and ids[0] == tok.id_special("<|pensee|>"):
        fin_pensee = tok.id_special("<|fin_pensee|>")
        if fin_pensee in ids:
            place = ids.index(fin_pensee)
            pensee, corps = sans_speciaux(ids[1:place]), ids[place + 1 :]
        else:
            pensee, corps = sans_speciaux(ids[1:]), []
    return Reponse(texte=sans_speciaux(corps), pensee=pensee, ids=ids, terminee=terminee)


def conversation_vers_json(tours: Sequence[Tour]) -> dict:
    """`{"tours": [{"role", "texte", "pensee"?}]}` ; la clé `pensee` n'existe que s'il y en a une."""
    sortie = []
    for tour in tours:
        element = {"role": tour.role, "texte": tour.texte}
        if tour.pensee is not None:
            element["pensee"] = tour.pensee
        sortie.append(element)
    return {"tours": sortie}


def conversation_depuis_json(d: dict) -> list[Tour]:
    """L'inverse de `conversation_vers_json`."""
    return [Tour(role=t["role"], texte=t["texte"], pensee=t.get("pensee")) for t in d["tours"]]
