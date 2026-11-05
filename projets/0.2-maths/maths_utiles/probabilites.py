"""Des scores aux probabilités, et l'erreur d'une prédiction.

Une IA ne sort pas directement des probabilités : elle donne un score à chaque
réponse possible. Softmax change ces scores en probabilités, positives et de
somme 1. Pour apprendre, elle mesure ensuite son erreur : −ln p, où p est la
probabilité qu'elle donnait à la bonne réponse.

Ces deux fonctions passent par exp et log (math.exp, math.log), dont le dernier
chiffre peut changer d'un système à l'autre : le site ne les recalcule pas, il
lit leurs valeurs dans tests/attendus.json.
"""

import math


# region: softmax
def softmax(
    scores: list[float],
    temperature: float = 1.0,
) -> list[float]:
    """Des scores aux probabilités : exp(score ÷ température),
    divisé par la somme.

    Une température basse avantage le plus grand score ;
    une température haute rapproche les probabilités.
    """
    if temperature <= 0:
        raise ValueError(
            "La température doit être positive"
            f" (reçu {temperature})\u202f: essaie 1."
        )
    # On soustrait le plus grand score : le résultat ne change
    # pas, et exp ne déborde jamais (exp(0) = 1 au plus).
    plus_grand = max(scores)
    exps = [
        math.exp((s - plus_grand) / temperature)
        for s in scores
    ]
    total = 0.0
    for e in exps:
        total += e
    return [e / total for e in exps]
# fin: softmax


# region: erreur-de-prediction
def erreur_de_prediction(p: float) -> float:
    """L'erreur d'une prédiction : −ln p, où p est la
    probabilité donnée à la bonne réponse.

    p = 1 (sûr et juste) : erreur 0. Plus p est petit,
    plus l'erreur est grande.
    """
    if not 0.0 < p <= 1.0:
        raise ValueError(
            "p est une probabilité\u202f: elle va de 0 exclu à 1"
            f" (reçu {p})."
        )
    return -math.log(p)
# fin: erreur-de-prediction
