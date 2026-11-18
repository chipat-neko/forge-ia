"""Les invites des préférences de 1.8 (et de la mesure `victoire`) : des questions avec consignes, et des problèmes.

`invites_de_preference` en tire `n` :

- 70 % de questions d'une base de conversations (le message système éventuel et la première question de
  l'utilisateur ; la réponse de la base n'est pas gardée). Une question dont l'identifiant est dans `exclure`
  (déjà apprise au SFT) n'est jamais prise, une question en double l'est une fois. On ajoute une ou deux
  consignes de `CONTRAINTES` à la fin du message de l'utilisateur : deux réponses de ton IA se départagent
  ensuite sur ces consignes, que `forge.preferences.noter` vérifie par programme ;
- 30 % de problèmes de calcul de difficulté 1 (`generer_problemes`), des graines `graines_problemes`
  (`GRAINES_PREFERENCES` par défaut), avec leur réponse dans `attendu`. Des graines d'évaluation sont refusées.

Le tout est mélangé. La même graine et la même base donnent les mêmes invites, dans le même ordre : c'est ce qui
permet de reprendre la construction des paires au paquet suivant après une coupure.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from forge.conversation.format import Tour
from forge.conversation.sources import UsageInterdit
from forge.evaluation.consignes import CONTRAINTES
from forge.hasard import Hasard
from forge.raisonnement.problemes import GRAINES_PREFERENCES, generer_problemes, usage_de_la_graine

PART_DES_PROBLEMES = 0.3
DIFFICULTES_DES_PROBLEMES = (1,)
PREFIXE_DES_PROBLEMES = "probleme:"
SEPARATEUR_DES_CONSIGNES = "\n\n"

# Deux consignes qu'aucune réponse ne peut respecter ensemble : elles ne sont jamais tirées pour la même invite.
# - « minuscules » et « fin_imposee » : toutes les phrases de fin (`PHRASES_FIN`) commencent par une majuscule ;
# - « puces » et « titre » : le titre ouvre la première ligne, qui devrait aussi commencer par « - ».
CONTRAINTES_INCOMPATIBLES = frozenset(
    {frozenset({"minuscules", "fin_imposee"}), frozenset({"puces", "titre"})}
)


@dataclass(frozen=True)
class InvitePreference:
    """Une invite : `tours` (qui finissent par l'utilisateur, consignes comprises), les `contraintes` ajoutées
    (identifiant et réglages de chacune) et, pour un problème, la réponse `attendu` (`None` pour une question)."""

    id: str
    tours: tuple[Tour, ...]
    contraintes: tuple[tuple[str, dict], ...]
    attendu: int | None


def tours_de_la_question(tours: Sequence[Tour]) -> tuple[Tour, ...] | None:
    """Le message système éventuel (s'il ouvre la conversation) et la première question ; `None` sans question."""
    debut: list[Tour] = []
    for tour in tours:
        if tour.role == "systeme" and not debut:
            debut.append(tour)
        elif tour.role == "utilisateur":
            return (*debut, tour) if tour.texte.strip() else None
        else:
            return None
    return None


def _tirer_contraintes(hasard: Hasard, question: str) -> tuple[tuple[str, dict], ...]:
    """Une ou deux contraintes compatibles, tirées dans l'ordre d'un mélange de `CONTRAINTES`.

    Une contrainte qui n'a pas de sens pour cette question (`tirer` rend `None`, comme « mot_obligatoire » sans
    mot assez long) ou qui ne va pas avec une déjà prise est passée : on prend la suivante du mélange.
    """
    voulues = hasard.entier(1, 2)
    prises: list[tuple[str, dict]] = []
    for contrainte in hasard.melanger(CONTRAINTES):
        if len(prises) == voulues:
            break
        if any(frozenset({contrainte.id, autre}) in CONTRAINTES_INCOMPATIBLES for autre, _ in prises):
            continue
        kwargs = contrainte.tirer(hasard, question)
        if kwargs is not None:
            prises.append((contrainte.id, kwargs))
    return tuple(prises)


def avec_consignes(question: tuple[Tour, ...], contraintes: Sequence[tuple[str, dict]]) -> tuple[Tour, ...]:
    """La question, avec les phrases de ses consignes à la fin du message de l'utilisateur."""
    par_id = {c.id: c for c in CONTRAINTES}
    consignes = " ".join(par_id[nom].consigne(kwargs) for nom, kwargs in contraintes)
    if not consignes:
        return question
    derniere = question[-1]
    return (*question[:-1], Tour(derniere.role, derniere.texte.rstrip() + SEPARATEUR_DES_CONSIGNES + consignes))


def invites_de_preference(
    n: int,
    graine: int,
    base: Sequence[tuple[str, list[Tour]]],
    exclure: set[str],
    *,
    graines_problemes: int = GRAINES_PREFERENCES,
) -> list[InvitePreference]:
    """`n` invites : 70 % de questions de `base` (identifiant hors `exclure`), avec une ou deux consignes, et 30 %
    de problèmes de difficulté 1 des graines `graines_problemes` à `graines_problemes + 30 % de n − 1`.

    `base` donne des couples (identifiant, tours) ; seuls le message système éventuel et la première question de
    chaque conversation servent. S'il y a moins de questions possibles que 70 % de `n`, toutes sont prises et la
    liste est plus courte ; de même si deux problèmes ont le même énoncé (le second est retiré). Lève
    `UsageInterdit` si `graines_problemes` est une graine d'évaluation ou de validation du RL.
    """
    if n < 1:
        raise ValueError(f"Il faut au moins une invite (reçu n = {n}).")
    usage = usage_de_la_graine(graines_problemes)
    if usage != "entrainement":
        raise UsageInterdit(
            f"Les graines {graines_problemes} et suivantes sont celles des problèmes de {usage} : ces problèmes "
            "sont réservés à la mesure, jamais à une invite de préférence. Prends GRAINES_PREFERENCES."
        )
    hasard = Hasard(graine)
    n_problemes = round(n * PART_DES_PROBLEMES)
    n_questions = n - n_problemes

    possibles: dict[str, tuple[Tour, ...]] = {}
    for identifiant, tours in base:
        if identifiant in exclure or identifiant in possibles:
            continue
        question = tours_de_la_question(tours)
        if question is not None:
            possibles[identifiant] = question
    candidates = list(possibles.items())
    invites: list[InvitePreference] = []
    for position in hasard.melanger(range(len(candidates)))[:n_questions]:
        identifiant, question = candidates[position]
        contraintes = _tirer_contraintes(hasard, question[-1].texte)
        invites.append(InvitePreference(identifiant, avec_consignes(question, contraintes), contraintes, None))

    for p in generer_problemes(n_problemes, graines_problemes, difficultes=DIFFICULTES_DES_PROBLEMES):
        invites.append(InvitePreference(f"{PREFIXE_DES_PROBLEMES}{p.id}", (Tour("utilisateur", p.enonce),), (), p.reponse))
    return hasard.melanger(invites)
