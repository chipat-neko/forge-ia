"""L'évaluation de « ton IA » : perte, perplexité, bits par octet, QCM français, échantillons.

Le point d'entrée est `evaluer(sauvegarde, donnees, tokenizer, sortie)`, ou en ligne de
commande `python -m forge evaluer --sauvegarde <pt> --donnees <nom>` : il écrit `rapport.json` et
`rapport.md` (en français). Les mesures elles-mêmes sont dans `perte.py`, `qcm.py` et
`echantillons.py`.

L'ordre des imports compte : `forge.entrainement.boucle` importe `forge.evaluation.perte`, et
`rapport.py` importe `forge.entrainement.chargeur` ; `perte` passe donc avant `rapport`.
"""

from forge.evaluation.echantillons import INVITES, echantillons
from forge.evaluation.perte import bits_par_octet, perplexite, perte_validation
from forge.evaluation.qcm import QCM, charger_frenchbench, evaluer_qcm
from forge.evaluation.rapport import evaluer

__all__ = [
    "INVITES",
    "QCM",
    "bits_par_octet",
    "charger_frenchbench",
    "echantillons",
    "evaluer",
    "evaluer_qcm",
    "perplexite",
    "perte_validation",
]
