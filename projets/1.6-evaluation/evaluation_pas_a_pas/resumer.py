"""Résumer le rapport d'évaluation de forge (`rapport.json`) en un relevé que le site lit.

`python -m forge evaluer` écrit `rapport.json` et `rapport.md`. Le relevé de ce projet n'en garde que
ce que les chapitres montrent : la perte, la perplexité, les bits par octet, les deux QCM avec leur
verdict, et les dix textes. Rien n'est recalculé : les nombres sont ceux du rapport, avec les noms de
clés de forge (`exactitude_normalisee`, `marge_hasard`…). Seul le verdict s'ajoute, par la règle de
`forge.evaluation.rapport.verdict` (voir `pas_a_pas.verdict`).
"""

import json
import math
from pathlib import Path, PurePath, PureWindowsPath

from forge.evaluation.rapport import VERSION_DU_RAPPORT

from evaluation_pas_a_pas.pas_a_pas import verdict

TESTS_QCM = ("hellaswag", "arc")
CLES_DU_QCM = (
    "exactitude",
    "exactitude_normalisee",
    "hasard",
    "n",
    "marge_95",
    "marge_95_normalisee",
    "marge_hasard",
    "total_du_test",
)


def nom_de_l_entrainement(sauvegarde: str) -> str:
    """« ton-ia-mini » pour une sauvegarde `…/ton-ia-mini/sauvegardes/etape-0006370.pt` (avec des antislashs sous Windows) : le dossier de l'entraînement."""
    chemin: PurePath = PureWindowsPath(sauvegarde) if "\\" in sauvegarde else PurePath(sauvegarde)
    return chemin.parent.parent.name


# region: resumer
def resumer(rapport_json: Path, nom: str | None = None) -> dict:
    """Le relevé d'un rapport d'évaluation de forge.

    Rend `{"nom", "releve_le", "pas", "perte_val", "perplexite", "bits_par_octet", "qcm", "echantillons"}`.
    Chaque test de `qcm` (`hellaswag`, `arc`) garde les mesures du rapport et reçoit son `verdict`. `nom`
    est celui du dossier de l'entraînement (« ton-ia-mini ») si on ne le donne pas.
    """
    rapport_json = Path(rapport_json)
    if not rapport_json.is_file():
        raise FileNotFoundError(
            f"Le rapport {rapport_json} n'existe pas. Lance d'abord `python -m forge evaluer` (il écrit rapport.json), "
            "ou corrige le chemin de --rapport."
        )
    try:
        rapport = json.loads(rapport_json.read_text(encoding="utf-8"))
    except ValueError as erreur:
        raise ValueError(f"{rapport_json} n'est pas un fichier JSON lisible ({erreur}). Relance `python -m forge evaluer`.") from erreur
    if not isinstance(rapport, dict) or rapport.get("version") != VERSION_DU_RAPPORT:
        version = rapport.get("version") if isinstance(rapport, dict) else None
        raise ValueError(
            f"{rapport_json} n'est pas un rapport d'évaluation de forge de version {VERSION_DU_RAPPORT} (version lue\u202f: {version!r}). "
            "Relance `python -m forge evaluer` avec cette version de la forge."
        )
    for cle in ("date", "sauvegarde", "pas", "perte_val", "perplexite", "bits_par_octet", "qcm", "echantillons"):
        if cle not in rapport:
            raise ValueError(f"Le rapport {rapport_json} n'a pas de «\u202f{cle}\u202f». Relance `python -m forge evaluer`.")
    for cle in ("perte_val", "perplexite", "bits_par_octet"):
        valeur = rapport[cle]
        if not isinstance(valeur, int | float) or not math.isfinite(valeur):
            raise ValueError(
                f"Dans {rapport_json}, {cle} vaut {valeur!r}\u202f: le modèle a divergé, ou le rapport est abîmé. "
                "Évalue une sauvegarde plus ancienne."
            )
    qcm = {}
    for test in TESTS_QCM:
        mesures = rapport["qcm"].get(test)
        if mesures is None or "erreur" in mesures:
            raison = "il n'est pas dans le rapport" if mesures is None else mesures["erreur"]
            raise ValueError(
                f"Le QCM {test} n'a pas été mesuré dans {rapport_json} ({raison}). "
                "Relance `python -m forge evaluer` avec le réseau, et sans limiter le nombre de questions."
            )
        manque = [cle for cle in CLES_DU_QCM if cle not in mesures]
        if manque:
            raise ValueError(f"Le QCM {test} de {rapport_json} n'a pas {', '.join(manque)}. Relance `python -m forge evaluer`.")
        qcm[test] = {
            **{cle: mesures[cle] for cle in CLES_DU_QCM},
            "verdict": verdict(mesures["exactitude_normalisee"], mesures["hasard"], mesures["marge_hasard"]),
        }
    return {
        "nom": nom or nom_de_l_entrainement(rapport["sauvegarde"]),
        "releve_le": rapport["date"][:10],
        "pas": rapport["pas"],
        "perte_val": rapport["perte_val"],
        "perplexite": rapport["perplexite"],
        "bits_par_octet": rapport["bits_par_octet"],
        "qcm": qcm,
        "echantillons": rapport["echantillons"],
    }
# fin: resumer
