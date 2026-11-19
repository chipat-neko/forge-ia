"""Noter une réponse comme le fait forge, en disant pourquoi.

`forge.preferences.noter` donne à une réponse cinq nombres, du critère le plus important au moins important :
`terminee`, `juste`, `consignes`, `francais`, `longueur`. Ici, `expliquer_note` refait ce calcul critère par
critère et écrit, pour chacun, son verdict et sa raison en français : « 3 consignes sur 3 », « en français »,
« 47 mots ». Rien n'est réinventé : les contrôles sont ceux de forge (`CONTRAINTES`, `langue`, `mots`,
`extraire_nombre`), et un test vérifie que la note rendue est celle de `forge.preferences.noter`.

Deux notes se comparent dans l'ordre des critères : le premier qui diffère décide (`raison_de_la_paire` de forge).
"""

from forge.conversation.format import Reponse
from forge.evaluation.consignes import CONTRAINTES
from forge.evaluation.langue import langue, mots
from forge.preferences.invites import InvitePreference
from forge.preferences.noter import MOTS_MAXIMUM, MOTS_MINIMUM, Note
from forge.raisonnement.verification import est_juste, extraire_nombre


# region: noter
CRITERES = Note._fields  # terminee, juste, consignes, francais, longueur : du plus important au moins important


def _pluriel(n: int, mot: str) -> str:
    """« 0 consigne », « 1 consigne », « 2 consignes » : le pluriel dès 2."""
    return f"{n} {mot}{'s' if n >= 2 else ''}"


def _nombre_lu(valeur) -> str:
    """Un nombre lu dans un texte (un entier ou une fraction), écrit à la française."""
    if valeur.denominator == 1:
        return str(valeur.numerator)
    return str(round(float(valeur), 4)).replace(".", ",")  # « 0,3333 » : la valeur arrondie, pas ses seize chiffres


def _critere(nom: str, valeur: int, maximum: int, raison: str) -> dict:
    return {"nom": nom, "valeur": valeur, "maximum": maximum, "verdict": valeur == maximum, "raison": raison}


def expliquer_note(reponse_texte: str, terminee: bool, invite: InvitePreference) -> dict:
    """La note d'une réponse à une invite, et pourquoi.

    Rend `{note, criteres, consignes, mots, langue}` :

    - `note` : les cinq nombres de `Note`, comme `forge.preferences.noter` ;
    - `criteres` : une ligne par critère, dans l'ordre de `CRITERES` : `nom`, `valeur`, `maximum`, `verdict`
      (la valeur est-elle le maximum ?) et `raison` en français ;
    - `consignes` : chaque consigne de l'invite avec sa phrase et si la réponse la respecte ;
    - `mots` : le nombre de mots de la réponse ; `langue` : « fr », « autre » ou « indetermine ».

    Seul le texte compte, jamais la pensée, comme dans forge.
    """
    par_id = {c.id: c for c in CONTRAINTES}
    reponse = Reponse(texte=reponse_texte, pensee=None, ids=[], terminee=terminee)

    # 1. terminée : la réponse a-t-elle fini son tour, ou la limite de jetons l'a-t-elle coupée ?
    fin = _critere(
        "terminee",
        int(terminee),
        1,
        "la réponse a fini son tour" if terminee else "la réponse est coupée par la limite de jetons",
    )

    # 2. juste : pour un problème, le dernier nombre du texte est-il la réponse attendue ?
    if invite.attendu is None:
        juste = _critere("juste", 1, 1, "une question n'a pas de réponse à vérifier : le critère est acquis")
    else:
        lu = extraire_nombre(reponse_texte)
        valeur = int(est_juste(reponse, invite.attendu))
        if not terminee:
            raison = "la réponse est coupée : rien ne dit que son dernier nombre est complet"
        elif lu is None:
            raison = "aucun nombre dans la réponse"
        elif valeur:
            raison = f"le dernier nombre de la réponse est {_nombre_lu(lu)}, la réponse attendue"
        else:
            raison = f"le dernier nombre de la réponse est {_nombre_lu(lu)}, pas {invite.attendu}"
        juste = _critere("juste", valeur, 1, raison)

    # 3. consignes : combien de consignes de l'invite la réponse respecte-t-elle ?
    consignes = []
    for nom, kwargs in invite.contraintes:
        contrainte = par_id.get(nom)
        if contrainte is None:
            raise ValueError(
                f"La consigne « {nom} » de l'invite {invite.id} est inconnue : les consignes sont "
                f"{', '.join(par_id)}. Refais les invites avec `invites_de_preference`."
            )
        consignes.append(
            {"id": nom, "consigne": contrainte.consigne(kwargs), "respectee": bool(contrainte.verifier(reponse_texte, kwargs))}
        )
    respectees = sum(c["respectee"] for c in consignes)
    consigne = _critere(
        "consignes",
        respectees,
        len(consignes),
        f"{_pluriel(respectees, 'consigne')} sur {len(consignes)}",
    )

    # 4. français : la langue n'est refusée que si elle est reconnue « autre » ; un texte trop court passe.
    la_langue = langue(reponse_texte)
    francais = _critere(
        "francais",
        0 if la_langue == "autre" else 1,
        1,
        {
            "fr": "en français",
            "autre": "dans une autre langue que le français",
            "indetermine": "moins de 3 mots outils : la langue ne se juge pas, il passe",
        }[la_langue],
    )

    # 5. longueur : de 3 à 300 mots.
    n_mots = len(mots(reponse_texte))
    if n_mots < MOTS_MINIMUM:
        raison_longueur = f"{_pluriel(n_mots, 'mot')}, moins de {MOTS_MINIMUM}"
    elif n_mots > MOTS_MAXIMUM:
        raison_longueur = f"{_pluriel(n_mots, 'mot')}, plus de {MOTS_MAXIMUM}"
    else:
        raison_longueur = _pluriel(n_mots, "mot")
    longueur = _critere("longueur", int(MOTS_MINIMUM <= n_mots <= MOTS_MAXIMUM), 1, raison_longueur)

    criteres = [fin, juste, consigne, francais, longueur]
    return {
        "note": {c["nom"]: c["valeur"] for c in criteres},
        "criteres": criteres,
        "consignes": consignes,
        "mots": n_mots,
        "langue": la_langue,
    }
# fin: noter


def note_de(explication: dict) -> Note:
    """La `Note` de forge d'une explication de `expliquer_note` (pour comparer deux réponses)."""
    return Note(**explication["note"])
