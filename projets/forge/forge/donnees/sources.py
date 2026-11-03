"""Les sources de données de « ton IA » : français du web, Wikipédia française, code Python.

Chaque source dit où la lire (dépôt Hugging Face, dossier ou configuration), quelle
colonne contient le texte, sous quelle licence elle est publiée et quels documents on
garde. `docs/donnees.md` détaille la même chose pour les lecteurs du dépôt.
"""

from collections.abc import Callable
from dataclasses import dataclass

# Licences de code gardées : celles qui autorisent de réutiliser et de redistribuer le
# code, y compris dans un modèle, à condition de citer les auteurs. Les noms sont ceux de
# la colonne `license` de `codeparrot/github-code-clean`.
LICENCES_PERMISSIVES = frozenset(
    {
        "mit",
        "apache-2.0",
        "bsd-2-clause",
        "bsd-3-clause",
        "isc",
        "unlicense",
        "cc0-1.0",
    }
)


@dataclass(frozen=True)
class Source:
    """Où lire une source, quelle colonne en garder, sous quelle licence, et le filtre.

    `configuration` est le nom de configuration du jeu Hugging Face (par exemple
    `20231101.fr`), `dossier_donnees` le dossier de ses fichiers parquet (par exemple
    `data/fra_Latn/train`) ; l'un ou l'autre peut être absent. Avec un dossier, on lit les
    fichiers parquet de ce dossier directement, sans passer par la configuration ni par
    un éventuel script de chargement du dépôt. `garder` reçoit une ligne du jeu (un
    dictionnaire colonne → valeur) et dit si on la garde.
    """

    nom: str
    depot: str
    configuration: str | None
    dossier_donnees: str | None
    colonne: str
    licence: str
    url_licence: str
    garder: Callable[[dict], bool]


def _tout_garder(_ligne: dict) -> bool:
    """Le français du web et Wikipédia n'écartent aucune ligne ; le nettoyage trie ensuite."""
    return True


def _garder_python_permissif(ligne: dict) -> bool:
    """Garde un fichier Python publié sous une licence permissive ; tout le reste est écarté."""
    licence = ligne.get("license")
    return (
        ligne.get("language") == "Python"
        and isinstance(licence, str)
        and licence.lower() in LICENCES_PERMISSIVES
    )


SOURCES: dict[str, Source] = {
    "web_fr": Source(
        nom="web_fr",
        depot="HuggingFaceFW/fineweb-2",
        configuration=None,
        dossier_donnees="data/fra_Latn/train",
        colonne="text",
        licence="ODC-By 1.0",
        url_licence="https://opendatacommons.org/licenses/by/1-0/",
        garder=_tout_garder,
    ),
    "wikipedia_fr": Source(
        nom="wikipedia_fr",
        depot="wikimedia/wikipedia",
        configuration="20231101.fr",
        dossier_donnees=None,
        colonne="text",
        licence="CC BY-SA 3.0",
        url_licence="https://creativecommons.org/licenses/by-sa/3.0/deed.fr",
        garder=_tout_garder,
    ),
    "code_python": Source(
        nom="code_python",
        depot="codeparrot/github-code-clean",
        configuration=None,
        dossier_donnees="data",
        colonne="code",
        licence=(
            "licence de chaque fichier, gardé seulement si elle est permissive "
            "(MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, Unlicense, CC0-1.0) ; "
            "compilation sous Apache-2.0"
        ),
        url_licence="https://www.apache.org/licenses/LICENSE-2.0",
        garder=_garder_python_permissif,
    ),
}
