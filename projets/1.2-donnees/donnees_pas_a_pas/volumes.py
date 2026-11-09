"""Les volumes d'un corpus déjà encodé : jetons d'entraînement et de validation, octets par jeton, fragments.

On lit `.complet` et `index.json` d'un dossier de jetons (`FORGE_DONNEES/jetons/<nom>/`), et
rien d'autre : aucun fichier de jetons n'est ouvert, rien n'est écrit. `forge.evaluation.perte`
sait lire l'octet par jeton aussi, mais il importe PyTorch : ce projet n'en a pas besoin, il relit
donc `index.json` lui-même.
"""

import json
from pathlib import Path

from forge.donnees.melange import MELANGE_PAR_DEFAUT


def _lire_json(chemin: Path, quoi: str) -> dict:
    try:
        return json.loads(chemin.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Il manque {quoi} ({chemin}) : ce dossier de jetons n'est pas complet. "
            f"Lance l'encodage avec « python -m forge encoder --donnees <dossier> --tokenizer <chemin> », "
            "ou donne le dossier d'un corpus déjà encodé."
        ) from None


def volumes(dossier_jetons: Path) -> dict:
    """Les volumes du corpus encodé dans `dossier_jetons` (lecture seule).

    Rend les jetons d'entraînement et de validation, les documents, les octets par jeton, et le
    nombre de fragments encodés pour chaque source (dans l'ordre du mélange).
    """
    dossier = Path(dossier_jetons)
    complet = _lire_json(dossier / ".complet", "le marqueur `.complet`")
    index = _lire_json(dossier / "index.json", "le fichier `index.json`")
    for cle in ("jetons_train", "jetons_val"):
        if complet.get(cle) != index.get(cle):
            raise ValueError(
                f"`.complet` et `index.json` ne disent pas la même chose pour « {cle} » "
                f"({complet.get(cle)} contre {index.get(cle)}) dans {dossier}. "
                "Relance l'encodage de ce dossier avant de relever ses volumes."
            )
    octets, sans_fin = index["octets"], index["jetons_sans_fin"]
    # Les fragments par source : « fragment-00000 » → « code_python/fragment-00000.jsonl.gz ».
    par_source: dict[str, int] = {}
    for provenance in index["provenance"].values():
        nom = provenance.split("/", 1)[0]
        par_source[nom] = par_source.get(nom, 0) + 1
    ordre = [nom for nom in MELANGE_PAR_DEFAUT if nom in par_source]
    ordre += sorted(nom for nom in par_source if nom not in MELANGE_PAR_DEFAUT)
    return {
        "jetons_train": index["jetons_train"],
        "jetons_val": index["jetons_val"],
        "documents_train": index["documents_train"],
        "documents_val": index["documents_val"],
        "octets": octets,
        "jetons_sans_fin": sans_fin,
        "octets_par_jeton": octets / sans_fin,
        "tokenizer": index["tokenizer"]["nom"],
        "fragments": sum(par_source.values()),
        "fragments_par_source": {nom: par_source[nom] for nom in ordre},
    }
