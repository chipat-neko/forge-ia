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

from forge.donnees.melange import MELANGE_PAR_DEFAUT, est_validation
from forge.donnees.nettoyage import empreinte_du_texte_nettoye
from forge.donnees.telechargement import dossier_des_textes
from forge.tokenizer.bpe_octets import NOMBRE_OCTETS, TokenizerOctets, entrainer_tokenizer
from forge.tokenizer.speciaux import NOMBRE_SPECIAUX


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
    *,
    ecarter_validation: bool = False,
) -> Iterator[str]:
    """Lit les textes des trois sources de `dossier`, dans les parts de `MELANGE_PAR_DEFAUT`.

    Avec `octets_max`, chaque source donne des documents tant qu'elle n'a pas
    atteint sa part (en octets UTF-8) : le dernier document peut la dépasser un
    peu. Sans `octets_max`, tout est lu.

    Avec `ecarter_validation`, les documents que l'encodage rangera dans la validation
    (`est_validation` de leur empreinte, comme dans `forge.donnees.jetons`) sont sautés :
    ils ne comptent pas dans la part de la source, qui se remplit donc de documents
    d'apprentissage seulement.
    """
    verifier_dossier(dossier)
    ecrire = journal if journal is not None else (lambda _message: None)
    for source, part in MELANGE_PAR_DEFAUT.items():
        budget = None if octets_max is None else round(octets_max * part)
        lus = 0
        ecartes = 0
        for texte in lire_fragments(dossier / source):
            if budget is not None and lus >= budget:
                break
            # Les textes téléchargés sont déjà nettoyés : leur empreinte est celle du texte tel quel.
            if ecarter_validation and est_validation(empreinte_du_texte_nettoye(texte)):
                ecartes += 1
                continue
            yield texte
            lus += len(texte.encode("utf-8"))
        message = f"{source} : {lus} octets lus"
        if budget is not None and lus < budget:
            message += f", moins que les {budget} prévus (source épuisée)"
        if ecarter_validation:
            message += (
                f" ; {ecartes} document{'s' if ecartes > 1 else ''} de validation "
                f"écarté{'s' if ecartes > 1 else ''}"
            )
        ecrire(message + ".")


def apprendre_depuis_dossier(
    dossier: Path,
    taille: int,
    nom: str,
    sortie: Path,
    octets_max: int | None,
    journal: Callable[[str], None] | None = None,
) -> TokenizerOctets:
    """Apprend un tokenizer sur `FORGE_DONNEES/textes/<dossier>`, l'enregistre dans `sortie` et le renvoie.

    Les documents de validation (ceux que `forge encoder` mettra dans `val/`) ne servent pas
    à apprendre : la compression mesurée ensuite sur la validation est ainsi honnête. Si
    l'apprentissage s'arrête avant d'avoir toutes ses fusions (pas assez de texte), il
    échoue sans rien écrire : un tokenizer trop court ne doit jamais prendre la place d'un bon.
    """
    chemin = dossier_des_textes(Path(dossier))
    verifier_dossier(chemin)  # avant de commencer, pas au milieu de la lecture
    textes = lire_textes_du_melange(chemin, octets_max, journal, ecarter_validation=True)
    tokenizer = entrainer_tokenizer(textes, taille, journal)
    voulues = taille - NOMBRE_OCTETS - NOMBRE_SPECIAUX
    if len(tokenizer.fusions) < voulues:
        raise ValueError(
            f"L'apprentissage s'est arrêté après {len(tokenizer.fusions)} fusions sur les "
            f"{voulues} voulues : les textes lus n'ont plus aucune paire à fusionner. Aucun "
            f"fichier n'a été écrit. Télécharge plus de textes (python -m forge donnees "
            f"--octets <taille> --dossier {chemin.name}), ou demande moins de jetons avec --taille."
        )
    tokenizer.nom = nom
    tokenizer.enregistrer(Path(sortie))
    return tokenizer
