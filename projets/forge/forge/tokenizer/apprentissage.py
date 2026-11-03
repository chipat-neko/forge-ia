"""Apprendre le tokenizer sur les textes téléchargés (sous-commande `tokenizer`).

Les textes viennent de `python -m forge donnees --dossier <nom>`, qui range
chaque source dans `FORGE_DONNEES/textes/<nom>/<source>/` : des fragments
`fragment-00000.jsonl.gz` (une ligne `{"texte": …}` par document) et, une fois
le téléchargement fini, un marqueur `.complet`.
"""

import gzip
import json
from collections.abc import Callable, Iterator
from pathlib import Path

from forge.donnees.melange import MELANGE_PAR_DEFAUT
from forge.donnees.telechargement import dossier_des_textes
from forge.tokenizer.bpe_octets import TokenizerOctets, entrainer_tokenizer


class DonneesManquantes(Exception):
    """Les textes attendus sont absents, ou leur téléchargement n'est pas fini."""


def verifier_dossier(dossier: Path) -> None:
    """Vérifie que chaque source est là, avec son marqueur `.complet`.

    Un téléchargement inachevé n'est jamais lu : le tokenizer appris dessus
    changerait une fois le téléchargement terminé.
    """
    relancer = f"python -m forge donnees --octets <taille> --dossier {dossier.name}"
    if not dossier.is_dir():
        raise DonneesManquantes(
            f"Le dossier des textes {dossier} est introuvable. Télécharge d'abord les "
            f"textes avec : {relancer}"
        )
    for source in MELANGE_PAR_DEFAUT:
        dossier_source = dossier / source
        if not dossier_source.is_dir():
            raise DonneesManquantes(
                f"La source « {source} » manque dans {dossier}. Télécharge-la avec : {relancer}"
            )
        if not (dossier_source / ".complet").exists():
            raise DonneesManquantes(
                f"Le téléchargement de « {source} » n'est pas terminé : pas de marqueur "
                f".complet dans {dossier_source}. Relance : {relancer} (avec la même "
                "taille) ; il reprendra là où il s'est arrêté."
            )


def lire_fragments(dossier_source: Path) -> Iterator[str]:
    """Les textes des fragments `*.jsonl.gz` d'une source, dans l'ordre des noms."""
    for fragment in sorted(dossier_source.glob("*.jsonl.gz")):
        with gzip.open(fragment, "rt", encoding="utf-8") as fichier:
            for ligne in fichier:
                if ligne.strip():
                    yield json.loads(ligne)["texte"]


def lire_textes_du_melange(
    dossier: Path,
    octets_max: int | None,
    journal: Callable[[str], None] | None = None,
) -> Iterator[str]:
    """Lit les textes des trois sources de `dossier`, dans les parts de `MELANGE_PAR_DEFAUT`.

    Avec `octets_max`, chaque source donne des documents tant qu'elle n'a pas
    atteint sa part (en octets UTF-8) : le dernier document peut la dépasser un
    peu. Sans `octets_max`, tout est lu.
    """
    verifier_dossier(dossier)
    ecrire = journal if journal is not None else (lambda _message: None)
    for source, part in MELANGE_PAR_DEFAUT.items():
        budget = None if octets_max is None else round(octets_max * part)
        lus = 0
        for texte in lire_fragments(dossier / source):
            if budget is not None and lus >= budget:
                break
            yield texte
            lus += len(texte.encode("utf-8"))
        if budget is not None and lus < budget:
            ecrire(f"{source} : {lus} octets lus, moins que les {budget} prévus (source épuisée).")
        else:
            ecrire(f"{source} : {lus} octets lus.")


def apprendre_depuis_dossier(
    dossier: Path,
    taille: int,
    nom: str,
    sortie: Path,
    octets_max: int | None,
    journal: Callable[[str], None] | None = None,
) -> TokenizerOctets:
    """Apprend un tokenizer sur `FORGE_DONNEES/textes/<dossier>`, l'enregistre dans `sortie` et le renvoie."""
    chemin = dossier_des_textes(Path(dossier))
    verifier_dossier(chemin)  # avant de commencer, pas au milieu de la lecture
    textes = lire_textes_du_melange(chemin, octets_max, journal)
    tokenizer = entrainer_tokenizer(textes, taille, journal)
    tokenizer.nom = nom
    tokenizer.enregistrer(Path(sortie))
    return tokenizer
