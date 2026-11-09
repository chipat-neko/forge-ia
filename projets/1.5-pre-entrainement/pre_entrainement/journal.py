"""Lire le journal d'un entraînement de forge : ses sessions, sa courbe et son résumé.

`forge entrainer` écrit une ligne de journal par pas (`journal.jsonl`), plus des lignes
d'évènements : `debut` ou `reprise` quand une session commence, `pause` ou `fin` quand elle finit.
Ce module en tire trois choses, sans rien entraîner :

- les **sessions** : le journal d'un entraînement mis en pause puis repris en contient plusieurs ;
- la **courbe** de perte, réduite en paquets de pas comme le fait le site (`site/src/lib/courbe.ts`) ;
- un **résumé** en quelques nombres.

Le journal n'a pas de dates : chaque pas porte `secondes`, le temps de calcul cumulé de tout
l'entraînement (les pauses ne comptent pas). Le temps d'une session est donc la différence entre
deux de ces cumuls.
"""

import math
from pathlib import Path

from forge.entrainement import ConfigEntrainement
from forge.modele import nombre_parametres
from forge.suivi import _FINS_DE_SESSION, PERTES_RECENTES, lire_journal

# La perte d'un modèle qui devine au hasard parmi les 32 768 jetons de « ton IA » : ln 32 768.
HASARD = math.log(32768)

DEBUTS_DE_SESSION = ("debut", "reprise")


def lire(journal: Path | str) -> list[dict]:
    """Les lignes du journal, dans l'ordre ; aucune s'il n'existe pas (c'est la lecture de forge)."""
    return lire_journal(Path(journal))


def _est_un_nombre(valeur) -> bool:
    return isinstance(valeur, int | float) and not isinstance(valeur, bool)


def _est_un_pas(ligne: dict) -> bool:
    """Une ligne de pas : un numéro et une perte, et aucun nom d'évènement."""
    return "evenement" not in ligne and isinstance(ligne.get("pas"), int) and _est_un_nombre(ligne.get("perte"))


# region: sessions
def sessions(lignes: list[dict]) -> list[dict]:
    """Une session par ligne `debut` ou `reprise`.

    Chaque session a son départ (`debut` ou `reprise`), son premier et son dernier pas (`None`
    si elle s'est arrêtée avant son premier pas), ses secondes de calcul, et sa fin : `pause`,
    `fin`, `perte_non_finie` (la perte est devenue infinie : forge n'a rien sauvegardé), ou
    `coupée` quand le journal n'a pas de ligne de fin (un plantage, une coupure de courant).
    """
    resultat: list[dict] = []
    courante = None
    cumul_au_depart = 0.0  # le temps de calcul cumulé quand la session commence
    cumul = 0.0  # le temps de calcul cumulé au dernier pas lu
    for ligne in lignes:
        evenement = ligne.get("evenement")
        if evenement in DEBUTS_DE_SESSION:
            cumul_au_depart = cumul
            courante = {"depart": evenement, "premier_pas": None, "dernier_pas": None, "secondes": 0.0, "fin": "coupée"}
            resultat.append(courante)
        elif courante is None:
            continue  # avant le premier début : rien à rattacher
        elif evenement in _FINS_DE_SESSION:
            courante["fin"] = evenement
            courante = None
        elif _est_un_pas(ligne):
            if courante["premier_pas"] is None:
                courante["premier_pas"] = ligne["pas"]
            courante["dernier_pas"] = ligne["pas"]
            if _est_un_nombre(ligne.get("secondes")):
                cumul = ligne["secondes"]
                courante["secondes"] = round(cumul - cumul_au_depart, 3)
    return resultat
# fin: sessions


# region: courbe
def courbe(lignes: list[dict], points: int = 600, pas_total: int | None = None) -> dict:
    """La courbe de perte, réduite à `points` points au plus.

    `pertes` : `[pas, moyenne]` par paquets de pas, avec le découpage de `taillePaquet` et
    `moyennesParPaquets` (`site/src/lib/courbe.ts`) : la taille du paquet est le nombre total de
    pas divisé par `points`, arrondi au-dessus ; chaque point est posé au milieu de son paquet,
    et le dernier paquet peut être incomplet. Une perte non finie est ignorée, et un paquet qui
    n'en a aucune de finie donne `None`. Le nombre total de pas est `pas_total` (celui de la
    configuration, pour que le lissage ne change pas pendant l'entraînement), sinon le nombre de
    pas du journal.

    `validations` : `[pas, perte]` pour chaque perte de validation. `hasard` : ln 32 768.
    """
    pertes = [float(ligne["perte"]) for ligne in lignes if _est_un_pas(ligne)]
    taille = max(1, math.ceil((len(pertes) if pas_total is None else pas_total) / points))
    paquets = []
    for debut in range(0, len(pertes), taille):
        fin = min(len(pertes), debut + taille)
        somme, nombre = 0.0, 0
        for perte in pertes[debut:fin]:  # une boucle, pas sum() : la même somme que le TypeScript
            if math.isfinite(perte):
                somme += perte
                nombre += 1
        milieu = (debut + 1 + fin) / 2
        paquets.append([int(milieu) if milieu == int(milieu) else milieu, somme / nombre if nombre else None])
    validations = [
        [ligne["pas"], ligne["perte_val"]]
        for ligne in lignes
        if isinstance(ligne.get("pas"), int) and "evenement" not in ligne and _est_un_nombre(ligne.get("perte_val"))
    ]
    return {"taille_paquet": taille, "pertes": paquets, "validations": validations, "hasard": HASARD}
# fin: courbe


def resume(lignes: list[dict], config: ConfigEntrainement) -> dict:
    """L'entraînement en quelques nombres.

    - `parametres`, `pas_total` : ceux de la configuration ;
    - `pas_faits`, `jetons_vus` : au dernier pas du journal ;
    - `secondes_de_calcul` : la somme des sessions ; `debit_moyen` : les jetons vus par seconde de calcul ;
    - `pauses` : les sessions finies par une pause ;
    - `perte_finale` : la moyenne des `PERTES_RECENTES` derniers pas (comme `docs/mesures/ton-ia-mini.md`) ;
    - `validation_finale` : la dernière perte de validation ;
    - `perte_premier_pas`, `perte_dernier_pas` : la perte du premier et du dernier pas. Le journal n'a
      pas de dates : ce sont ces pertes, et non l'heure, qui disent d'où l'on part et où l'on arrive.

    Un journal sans pas donne `None` pour tout ce qui se lit dans un pas.
    """
    pas = [ligne for ligne in lignes if _est_un_pas(ligne)]
    parties = sessions(lignes)
    total = 0.0
    for session in parties:
        total += session["secondes"]
    secondes = round(total, 3)
    jetons = pas[-1].get("jetons_vus") if pas else 0
    recentes = [float(ligne["perte"]) for ligne in pas[-PERTES_RECENTES:]]
    somme = 0.0
    for perte in recentes:
        somme += perte
    validations = [ligne["perte_val"] for ligne in pas if _est_un_nombre(ligne.get("perte_val"))]
    return {
        "parametres": nombre_parametres(config.modele),
        "pas_total": config.pas_total,
        "pas_faits": pas[-1]["pas"] if pas else 0,
        "jetons_vus": jetons,
        "secondes_de_calcul": secondes,
        "pauses": sum(1 for session in parties if session["fin"] == "pause"),
        "debit_moyen": jetons / secondes if secondes > 0 and jetons else None,
        "perte_finale": somme / len(recentes) if recentes else None,
        "validation_finale": validations[-1] if validations else None,
        "perte_premier_pas": pas[0]["perte"] if pas else None,
        "perte_dernier_pas": pas[-1]["perte"] if pas else None,
    }
