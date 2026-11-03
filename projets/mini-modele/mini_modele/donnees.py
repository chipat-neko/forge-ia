"""Les prénoms du mini-modèle : vocabulaire, encodage, et partage entraînement/validation.

Le mini-modèle lit un prénom caractère par caractère. Chaque caractère a un
numéro ; le numéro 0 est le « bord » (BORD, un point), qui marque le début et la
fin de chaque prénom : « ba » devient 0, b, a, 0.

Le partage en deux est le même en Python et en TypeScript : la liste est
mélangée par Hasard(GRAINE_PARTAGE), un prénom sur dix va en validation (ceux
que le modèle ne voit jamais pendant l'entraînement), le reste en entraînement.

Le jumeau TypeScript est site/src/lib/mini-modele/donnees.ts : il suit ce
fichier ligne à ligne. Ce fichier est vérifié par tests/test_sources.py.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from mini_modele.calcul import Hasard

BORD = "."  # le numéro 0 : le début et la fin d'un prénom
GRAINE_PARTAGE = 20261103  # la graine du mélange, la même pour tous les réglages
FICHIER_PRENOMS = Path(__file__).resolve().parent.parent / "donnees" / "prenoms.txt"


def prenoms_du_texte(texte: str) -> list[str]:
    """Un prénom par ligne, coupée au « \\n » ; le saut de ligne final ne compte pas."""
    prenoms = texte.split("\n")
    if prenoms[-1] == "":
        prenoms.pop()
    return prenoms


def charger_prenoms(chemin: str | Path | None = None) -> list[str]:
    """Les prénoms du fichier (par défaut donnees/prenoms.txt), lus octet pour octet.

    On lit les octets et on les décode, au lieu de read_text : read_text range
    « \\r\\n » en « \\n », et le Python verrait une autre liste que le site, qui
    lit le fichier tel quel (prenoms.txt?raw).
    """
    octets = Path(FICHIER_PRENOMS if chemin is None else chemin).read_bytes()
    return prenoms_du_texte(octets.decode("utf-8"))


def vocabulaire_de(prenoms: Iterable[str]) -> str:
    """BORD, puis les caractères distincts des prénoms, triés par point de code."""
    distincts: set[str] = set()
    for prenom in prenoms:
        if BORD in prenom:
            raise ValueError(
                f"Le caractère « {BORD} » est réservé au début et à la fin des prénoms : "
                f"retire-le du prénom « {prenom} »."
            )
        distincts.update(prenom)
    return BORD + "".join(sorted(distincts))


def encoder(prenom: str, vocabulaire: str) -> tuple[int, ...]:
    """Les numéros du prénom, entre deux bords : (0, *numéros, 0)."""
    numeros = [0]
    for caractere in prenom:
        numero = vocabulaire.find(caractere, 1)  # à partir de 1 : le bord n'est pas une lettre
        if numero < 0:
            raise ValueError(
                f"Caractère inconnu du vocabulaire : « {caractere} » (dans « {prenom} »). "
                "Le vocabulaire vient de vocabulaire_de, sur une liste qui contient ce caractère."
            )
        numeros.append(numero)
    numeros.append(0)
    return tuple(numeros)


def decoder(ids: Iterable[int], vocabulaire: str) -> str:
    """Le texte des numéros, en ignorant les 0 (les bords)."""
    taille = len(vocabulaire)
    caracteres = []
    for numero in ids:
        if isinstance(numero, bool) or not isinstance(numero, int) or not 0 <= numero < taille:
            raise ValueError(
                f"Numéro hors du vocabulaire : {numero!r} (il y a {taille} caractères, numérotés de 0 à {taille - 1})."
            )
        if numero != 0:
            caracteres.append(vocabulaire[numero])
    return "".join(caracteres)


@dataclass(frozen=True)
class Donnees:
    """Les prénoms prêts pour le mini-modèle (immuables : on peut les partager sans copie)."""

    vocabulaire: str
    entrainement: tuple[tuple[int, ...], ...]
    validation: tuple[tuple[int, ...], ...]
    connus: frozenset[str]  # tous les prénoms de la liste : sert à marquer « existe déjà »


def preparer(prenoms: Sequence[str]) -> Donnees:
    """Copie la liste, la mélange avec Hasard(GRAINE_PARTAGE), puis la partage en deux.

    Les len // 10 premiers prénoms mélangés vont en validation, le reste en entraînement.
    """
    vocabulaire = vocabulaire_de(prenoms)
    melanges = list(prenoms)
    Hasard(GRAINE_PARTAGE).melanger(melanges)
    nb_validation = len(melanges) // 10
    codes = [encoder(prenom, vocabulaire) for prenom in melanges]
    return Donnees(
        vocabulaire=vocabulaire,
        entrainement=tuple(codes[nb_validation:]),
        validation=tuple(codes[:nb_validation]),
        connus=frozenset(melanges),
    )


@cache
def donnees_par_defaut() -> Donnees:
    """Les prénoms versionnés (donnees/prenoms.txt), préparés une seule fois."""
    return preparer(charger_prenoms())
