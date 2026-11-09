"""Un aperçu des trois sources de « ton IA » : combien de documents le tri garde, et pourquoi il écarte les autres.

On lit chaque source en flux depuis Hugging Face (rien n'est téléchargé en entier), avec le
même lecteur que le téléchargement de forge, et on passe les documents par `trier`. On
s'arrête quand la source a donné assez de texte gardé. On ne retient que des comptes,
jamais un texte.
"""

import time
from collections.abc import Callable, Iterator

from forge.donnees.sources import SOURCES, Source
from forge.donnees.telechargement import lecteur_hugging_face

from donnees_pas_a_pas.trier import RAISONS, trier

# Les tailles s'écrivent comme dans forge : K, M et G valent 1024, 1024² et 1024³ octets.
_MULTIPLICATEURS = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3}


def en_octets(texte: str) -> int:
    """Lit une taille comme « 5M » : K, M et G valent 1024, 1024² et 1024³ octets."""
    texte = texte.strip().upper().removesuffix("B")
    unite = texte[-1] if texte and texte[-1] in "KMG" else ""
    chiffres = texte[: len(texte) - len(unite)]
    try:
        valeur = float(chiffres.replace(",", "."))
    except ValueError:
        raise ValueError(f"Taille illisible : « {texte} ». Écris par exemple 5M, 300K ou 1000000.") from None
    if valeur < 0:
        raise ValueError(f"Une taille ne peut pas être négative : « {texte} ».")
    return int(valeur * _MULTIPLICATEURS[unite])


def apercu_d_une_source(source: Source, octets: int, lecteur: Callable[[Source], Iterator[dict]]) -> dict:
    """Lit `source` jusqu'à `octets` octets de texte gardé (ou sa fin) et compte ce que le tri en fait."""
    debut = time.perf_counter()
    flux = lecteur(source)
    raisons = {raison: 0 for raison in RAISONS}
    octets_gardes = 0
    en_validation = 0
    try:
        for verdict in trier(flux, source):
            raisons[verdict.raison] += 1
            if verdict.garde:
                octets_gardes += len(verdict.texte.encode("utf-8"))
                en_validation += bool(verdict.validation)
                if octets_gardes >= octets:
                    break
    finally:
        # Ferme le flux de la source (connexions ouvertes) : arrêt voulu ou erreur.
        fermer = getattr(flux, "close", None)
        if callable(fermer):
            fermer()
    return {
        "lus": sum(raisons.values()),
        "gardes": raisons["gardé"],
        "raisons": raisons,
        "octets_gardes": octets_gardes,
        "en_validation": en_validation,
        "secondes": round(time.perf_counter() - debut, 1),
    }


def apercu(octets_par_source: int, lecteur: Callable[[Source], Iterator[dict]] | None = None) -> dict:
    """Pour chaque source de forge : `lus`, `gardes`, `raisons`, `octets_gardes`, `en_validation`, `secondes`.

    Sans `lecteur`, chaque source est lue en flux depuis Hugging Face ; les tests donnent le leur.
    """
    lire = lecteur if lecteur is not None else lecteur_hugging_face
    return {nom: apercu_d_une_source(source, octets_par_source, lire) for nom, source in SOURCES.items()}
