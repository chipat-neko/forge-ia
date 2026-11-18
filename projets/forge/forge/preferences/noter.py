"""Classer les réponses de ton IA par des contrôles programmés, sans juge.

Une réponse reçoit une `Note` de cinq critères, chacun un entier, du plus important au moins important :

1. `terminee` : 1 si la réponse a fini son tour (`<|fin_tour|>`), 0 si la limite de jetons l'a coupée ;
2. `juste` : pour un problème, 1 si `est_juste` (le dernier nombre du texte est la réponse attendue) ; 1 pour une
   question, qui n'a pas de réponse vérifiable ;
3. `consignes` : le nombre de consignes de l'invite que la réponse respecte (`Contrainte.verifier`, strict) ;
4. `francais` : 0 seulement si `langue` reconnaît une autre langue ; un texte trop court pour être jugé passe ;
5. `longueur` : 1 si le texte a de 3 à 300 mots (`mots`).

Deux notes se comparent dans cet ordre (l'ordre lexicographique d'un `NamedTuple`) : une réponse non terminée
perd toujours ; à terminaison égale, une réponse fausse perd ; puis les consignes, le français, la longueur.
`choisir_paire` prend la meilleure et la pire ; s'il n'y a aucune différence, il n'y a pas de paire.

Un plancher s'ajoute (`peut_etre_choisie`) : la DPO prend la réponse choisie pour modèle, et son terme SFT
l'apprend mot à mot. Une paire n'est donc gardée que si la meilleure est terminée et, pour un problème, juste ;
sinon il n'y a « aucune bonne réponse » (`sans_paire`), même si les deux réponses diffèrent.

La longueur : deux réponses également bonnes, l'une courte, l'autre longue, ont la même note (aucune paire).
Rien ne préfère le court en soi : une réponse longue ne perd que si elle est coupée par la limite de jetons
(`terminee`), si elle ne respecte pas une consigne de longueur que l'invite demande, ou si elle dépasse 300 mots,
ce qu'une réponse finie dans les 384 jetons des paires de 1.8 n'atteint pas en pratique : le tokenizer de ton IA
compte environ 1,7 jeton par mot sur les réponses de Luth-2 (médiane mesurée le 18/11/2026 sur 4 000 réponses), et
aucune réponse de 384 jetons au plus n'y dépasse 294 mots.
"""

from collections.abc import Sequence
from typing import NamedTuple

from forge.conversation.format import Reponse
from forge.evaluation.consignes import CONTRAINTES
from forge.evaluation.langue import langue, mots
from forge.preferences.invites import InvitePreference
from forge.raisonnement.verification import est_juste

MOTS_MINIMUM = 3
MOTS_MAXIMUM = 300

_CONTRAINTES_PAR_ID = {c.id: c for c in CONTRAINTES}


class Note(NamedTuple):
    """Les cinq critères d'une réponse, du plus important au moins important (voir le haut du module)."""

    terminee: int
    juste: int
    consignes: int
    francais: int
    longueur: int


def noter(reponse: Reponse, invite: InvitePreference) -> Note:
    """La note de `reponse` à `invite` ; seul le texte compte, jamais la pensée."""
    respectees = 0
    for nom, kwargs in invite.contraintes:
        contrainte = _CONTRAINTES_PAR_ID.get(nom)
        if contrainte is None:
            raise ValueError(
                f"La consigne « {nom} » de l'invite {invite.id} est inconnue : les consignes sont "
                f"{', '.join(_CONTRAINTES_PAR_ID)}. Refais les invites avec `invites_de_preference`."
            )
        respectees += bool(contrainte.verifier(reponse.texte, kwargs))
    return Note(
        terminee=int(reponse.terminee),
        juste=1 if invite.attendu is None else int(est_juste(reponse, invite.attendu)),
        consignes=respectees,
        francais=0 if langue(reponse.texte) == "autre" else 1,
        longueur=int(MOTS_MINIMUM <= len(mots(reponse.texte)) <= MOTS_MAXIMUM),
    )


def choisir_paire(notes: Sequence[Note]) -> tuple[int, int] | None:
    """(indice de la meilleure note, indice de la pire) ; `None` si toutes les notes sont égales.

    À égalité entre plusieurs meilleures (ou plusieurs pires), la première rencontrée.
    """
    if not notes:
        return None
    meilleure = max(range(len(notes)), key=lambda i: notes[i])
    pire = min(range(len(notes)), key=lambda i: notes[i])
    if notes[meilleure] == notes[pire]:
        return None
    return meilleure, pire


EGALITE = "egalite"
AUCUNE_BONNE_REPONSE = "aucune_bonne_reponse"


def peut_etre_choisie(note: Note) -> bool:
    """Vrai si une réponse peut être la choisie d'une paire : terminée et, quand elle se vérifie, juste."""
    return note.terminee == 1 and note.juste == 1


def sans_paire(notes: Sequence[Note]) -> str | None:
    """Pourquoi ces réponses ne donnent pas de paire : `EGALITE` (notes toutes égales), `AUCUNE_BONNE_REPONSE`
    (la meilleure est coupée ou fausse), ou `None` : la paire de `choisir_paire` est gardée."""
    paire = choisir_paire(notes)
    if paire is None:
        return EGALITE
    if not peut_etre_choisie(notes[paire[0]]):
        return AUCUNE_BONNE_REPONSE
    return None


def raison_de_la_paire(meilleure: Note, pire: Note) -> str:
    """Le premier critère qui départage deux notes différentes (« terminee », « juste »…)."""
    for champ in Note._fields:
        if getattr(meilleure, champ) != getattr(pire, champ):
            return champ
    raise ValueError("Les deux notes sont égales : rien ne les départage, il n'y a pas de paire.")


def taux_de_victoire(notes_a: Sequence[Note], notes_b: Sequence[Note]) -> dict:
    """A contre B, invite par invite : `victoires`, `egalites`, `defaites` de A, et `taux` = (victoires + égalités / 2) ÷ n."""
    if len(notes_a) != len(notes_b):
        raise ValueError(
            f"Les deux versions n'ont pas noté le même nombre d'invites ({len(notes_a)} et {len(notes_b)}) : "
            "compare-les sur les mêmes invites, dans le même ordre."
        )
    if not notes_a:
        raise ValueError("Aucune invite à comparer : il faut au moins une invite notée par les deux versions.")
    victoires = sum(1 for a, b in zip(notes_a, notes_b) if a > b)
    egalites = sum(1 for a, b in zip(notes_a, notes_b) if a == b)
    defaites = len(notes_a) - victoires - egalites
    return {
        "victoires": victoires,
        "egalites": egalites,
        "defaites": defaites,
        "taux": (victoires + egalites / 2) / len(notes_a),
    }
