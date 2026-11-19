"""Les courbes d'une DPO, relevées dans le journal de son entraînement, sans rien entraîner.

`forge entrainer` (méthode `dpo`) écrit dans son `journal.jsonl`, à chaque pas, les mesures de `perte_dpo` :
`logps_choisie` et `logps_rejetee` (la log-probabilité moyenne par jeton de chaque réponse), et `exactitude` (la
part des paires que la politique classe déjà dans le bon ordre). `courbes_dpo` les réduit en paquets de pas par
`pre_entrainement.journal.serie`, avec le découpage du site (`site/src/lib/courbe.ts`) : `mesures/entrainement-dpo-1.8.json`.
"""

from pathlib import Path

from pre_entrainement.journal import lire, serie

CLES_DES_COURBES = ("logps_choisie", "logps_rejetee", "exactitude")


# region: courbes
def courbes_dpo(journal: Path, points: int = 600, pas_total: int | None = None) -> dict:
    """`{logps_choisie, logps_rejetee, exactitude}` : chacune une liste de `[pas, valeur]`, de `points` points au plus.

    `pas_total` est le nombre de pas de la configuration (pour que le lissage ne change pas pendant l'entraînement).
    Lève `FileNotFoundError` si le journal manque ou est vide, et `ValueError` si une courbe n'a aucune valeur
    (le journal n'est pas celui d'une DPO) ou a un paquet sans valeur finie.
    """
    journal = Path(journal)
    lignes = lire(journal)
    if not lignes:
        raise FileNotFoundError(
            f"Le journal {journal} n'existe pas ou est vide. Donne le journal.jsonl d'un entraînement `dpo` de forge."
        )
    courbes = {}
    for cle in CLES_DES_COURBES:
        points_de_la_cle = serie(lignes, cle, points, pas_total)
        if not points_de_la_cle:
            raise ValueError(
                f"Le journal {journal} n'a aucune ligne avec « {cle} » : ce n'est pas le journal d'une DPO. "
                "Donne le journal.jsonl d'un entraînement de méthode `dpo`."
            )
        if any(valeur is None for _, valeur in points_de_la_cle):
            raise ValueError(
                f"La courbe « {cle} » de {journal} a un paquet de pas sans aucune valeur finie : "
                "le journal est abîmé, ou l'entraînement a divergé."
            )
        courbes[cle] = points_de_la_cle
    return courbes
# fin: courbes
