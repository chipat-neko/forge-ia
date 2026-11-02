"""Un tokenizer BPE minuscule, écrit pour comprendre.

BPE veut dire « Byte Pair Encoding » (codage par paires). L'idée tient en
quelques lignes :

1. On découpe le corpus en mots, puis chaque mot en lettres.
2. On compte combien de fois chaque paire de symboles voisins apparaît.
3. On colle la paire la plus fréquente en un seul symbole : c'est une fusion.
4. On recommence au point 2, tant qu'une paire apparaît au moins 2 fois.

Pour découper un nouveau texte, on rejoue les mêmes fusions, dans le même
ordre, sur ses lettres. Chaque symbole obtenu est un jeton.
"""

from collections import Counter
from pathlib import Path
from typing import NamedTuple

import regex

# Un « pré-jeton » est un mot qui garde l'espace qui le précède (comme dans GPT).
# De gauche à droite, le motif essaie dans cet ordre :
#   - des lettres (avec leurs accents), précédées d'une espace éventuelle ;
#   - des chiffres, précédés d'une espace éventuelle ;
#   - de la ponctuation ou des symboles, précédés d'une espace éventuelle ;
#   - des espaces et retours à la ligne qui restent.
# Le module `regex` (et non `re`) est nécessaire pour comprendre \p{L}.
# On écrit \p{White_Space} plutôt que \s : la liste des espaces est alors celle
# d'Unicode, la même en Python et en JavaScript (\s diffère d'un langage à l'autre).
MOTIF = (
    r"\p{White_Space}?[\p{L}\p{M}]+|\p{White_Space}?\p{N}+|"
    r"\p{White_Space}?[^\p{White_Space}\p{L}\p{N}]+|\p{White_Space}+"
)
_MOTIF_COMPILE = regex.compile(MOTIF)

# Un mot du corpus est un tuple de symboles, par exemple ("l", "e", "s").
Mot = tuple[str, ...]
# Une paire est deux symboles voisins, par exemple ("e", "s").
Paire = tuple[str, str]

CHEMIN_CORPUS = Path(__file__).resolve().parent.parent / "donnees" / "corpus.txt"


def charger_corpus() -> str:
    """Lit le corpus d'apprentissage (donnees/corpus.txt, en UTF-8)."""
    with open(CHEMIN_CORPUS, encoding="utf-8", newline="") as fichier:
        return fichier.read()


def pre_decouper(texte: str) -> list[str]:
    """Découpe un texte en pré-jetons : « Le forgeron » donne ["Le", " forgeron"]."""
    return _MOTIF_COMPILE.findall(texte)


def compter_mots(corpus: str) -> dict[Mot, int]:
    """Compte combien de fois chaque mot apparaît dans le corpus.

    Chaque mot est écrit comme un tuple de lettres : au départ, un symbole
    est simplement un caractère.
    """
    compte: Counter[Mot] = Counter()
    for mot in pre_decouper(corpus):
        compte[tuple(mot)] += 1
    return dict(compte)


# region: compter
def compter_paires(mots: dict[tuple[str, ...], int]) -> Counter[tuple[str, str]]:
    """Compte les paires de symboles voisins, en tenant compte de la fréquence des mots."""
    compte: Counter[tuple[str, str]] = Counter()
    for symboles, frequence in mots.items():
        # On regarde chaque symbole avec son voisin de droite.
        for gauche, droite in zip(symboles, symboles[1:]):
            compte[(gauche, droite)] += frequence
    return compte
# fin: compter


# region: choisir
def paire_la_plus_frequente(compte: Counter[tuple[str, str]]) -> tuple[str, str]:
    """Choisit la paire la plus fréquente.

    En cas d'égalité, on prend la plus petite paire (a, b) dans l'ordre des
    points de code : ainsi le résultat est toujours le même.
    """
    # Le signe moins donne la plus petite clé à la paire la plus fréquente.
    return min(compte, key=lambda paire: (-compte[paire], paire))
# fin: choisir


def fusionner(mots: dict[Mot, int], paire: Paire) -> dict[Mot, int]:
    """Remplace la paire par un seul symbole dans tous les mots.

    On avance de gauche à droite, sans chevauchement : dans « aaa » avec la
    paire ("a", "a"), on obtient ("aa", "a") et non ("aa", "aa").
    """
    a, b = paire
    nouveaux: dict[Mot, int] = {}
    for symboles, frequence in mots.items():
        resultat: list[str] = []
        i = 0
        while i < len(symboles):
            if i + 1 < len(symboles) and symboles[i] == a and symboles[i + 1] == b:
                resultat.append(a + b)
                i += 2  # on saute les deux symboles qui viennent d'être collés
            else:
                resultat.append(symboles[i])
                i += 1
        nouveaux[tuple(resultat)] = frequence
    return nouveaux


class Fusion(NamedTuple):
    """Une fusion apprise : les symboles `a` et `b` collés, vus `compte` fois."""

    a: str
    b: str
    compte: int


def apprendre(corpus: str, nb_fusions: int) -> list[Fusion]:
    """Apprend au plus `nb_fusions` fusions sur le corpus.

    On s'arrête plus tôt si aucune paire n'apparaît au moins 2 fois : coller
    une paire vue une seule fois n'apprendrait rien d'utile.
    """
    mots = compter_mots(corpus)
    fusions: list[Fusion] = []
    for _ in range(nb_fusions):
        compte = compter_paires(mots)
        if not compte:
            break
        paire = paire_la_plus_frequente(compte)
        if compte[paire] < 2:
            break
        fusions.append(Fusion(paire[0], paire[1], compte[paire]))
        mots = fusionner(mots, paire)
    return fusions


class Jeton(NamedTuple):
    """Un jeton du texte découpé.

    - `texte` : les caractères du jeton ;
    - `id` : son numéro, ou None si c'est un caractère absent du corpus ;
    - `mot` : l'indice du pré-jeton (du mot) dont il vient.
    """

    texte: str
    id: int | None
    mot: int


class TokenizerPedagogique:
    """Apprend les fusions sur un corpus, puis découpe des textes."""

    def __init__(self, corpus: str, nb_fusions_max: int = 200):
        self.fusions: list[Fusion] = apprendre(corpus, nb_fusions_max)
        # Les caractères du corpus, sans doublon, triés par point de code.
        self.base: list[str] = sorted(set(corpus))
        self._numero_de_base: dict[str, int] = {c: i for i, c in enumerate(self.base)}

    def decouper(self, texte: str, k: int) -> list[Jeton]:
        """Découpe `texte` en rejouant les `k` premières fusions.

        Numéros des jetons :
        - un caractère de base a pour numéro sa place dans `base` (None s'il
          est inconnu) ;
        - le symbole créé par la fusion d'indice j a pour numéro len(base) + j.
        Le numéro voyage avec le symbole : on ne le cherche pas à partir de
        son texte, car deux fusions différentes peuvent donner le même texte.
        """
        k = max(0, min(k, len(self.fusions)))
        jetons: list[Jeton] = []
        for indice_mot, mot in enumerate(pre_decouper(texte)):
            # Chaque symbole est un couple (texte, numéro).
            symboles: list[tuple[str, int | None]] = [
                (caractere, self._numero_de_base.get(caractere)) for caractere in mot
            ]
            for j in range(k):
                fusion = self.fusions[j]
                symboles = _fusionner_symboles(symboles, fusion, len(self.base) + j)
            for symbole, numero in symboles:
                jetons.append(Jeton(symbole, numero, indice_mot))
        return jetons


def _fusionner_symboles(
    symboles: list[tuple[str, int | None]], fusion: Fusion, numero: int
) -> list[tuple[str, int | None]]:
    """Applique une fusion à un mot, de gauche à droite, sans chevauchement."""
    resultat: list[tuple[str, int | None]] = []
    i = 0
    while i < len(symboles):
        if (
            i + 1 < len(symboles)
            and symboles[i][0] == fusion.a
            and symboles[i + 1][0] == fusion.b
        ):
            resultat.append((fusion.a + fusion.b, numero))
            i += 2
        else:
            resultat.append(symboles[i])
            i += 1
    return resultat
