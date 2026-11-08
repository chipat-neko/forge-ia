"""Un modèle de langage à n-grammes de caractères.

Un modèle de langage devine la suite d'un texte. Le plus simple compte, dans un
texte d'apprentissage, quel caractère suit chaque groupe de n caractères (le
contexte), puis s'en sert comme d'une table de probabilités : pour écrire,
il tire le caractère suivant selon ces probabilités, l'ajoute, et recommence.

Le site refait tout ce fichier en TypeScript (site/src/lib/partie-1/ngrammes.ts),
fonction pour fonction : mêmes opérations, dans le même ordre, donc mêmes
nombres, au bit près. Seule la perplexité, qui passe par exp et log, reste en
Python : le site lit ses valeurs dans tests/attendus.json.

Les caractères sont des points de code Unicode (« 😀 » en est un, de même que
« é »), comme les `str` de Python : les découpages et les tris s'y font.
"""

import math
from collections import Counter
from pathlib import Path

from modele_de_langage.hasard import Hasard

# Le texte d'apprentissage : la prose des chapitres du site (voir extraire.py).
CHEMIN_TEXTE = Path(__file__).resolve().parent.parent / "donnees" / "texte-du-site.txt"

MESSAGE_TEXTE_VIDE = "Le texte est vide : il faut au moins un caractère."
MESSAGE_CONTEXTE_COURT = "Il faut au moins n caractères de contexte."
MESSAGE_AUCUN_POIDS = "Aucun poids positif : il faut au moins un poids plus grand que 0 pour tirer."

ORDRE_MAX = 6
# Les températures du site : 0 choisit toujours le plus probable, 1 suit les
# probabilités, 0,5 les durcit, 2 les adoucit.
TEMPERATURES = (0, 0.5, 1, 2)
MESSAGE_TEMPERATURE = "La température doit valoir 0, 0.5, 1 ou 2 : choisis l'une de ces quatre valeurs."


def charger_texte() -> str:
    """Le texte d'apprentissage du projet, lu en UTF-8."""
    return CHEMIN_TEXTE.read_text(encoding="utf-8")


def couper(texte: str) -> tuple[str, str]:
    """Sépare le texte : les 90 premiers % pour apprendre, le reste pour vérifier (en points de code)."""
    limite = len(texte) * 9 // 10
    return texte[:limite], texte[limite:]


def alphabet(texte: str) -> list[str]:
    """Les caractères distincts du texte, triés par point de code."""
    return sorted(set(texte))


# region: compter
def compter(texte: str, n: int) -> dict[str, Counter[str]]:
    """Pour chaque contexte de n caractères, combien de fois chaque caractère le suit.

    Pour n = 0, le contexte est le texte vide : on compte les caractères tout court.
    """
    comptes: dict[str, Counter[str]] = {}
    for i in range(n, len(texte)):
        contexte = texte[i - n : i]
        if contexte not in comptes:
            comptes[contexte] = Counter()
        comptes[contexte][texte[i]] += 1
    return comptes
# fin: compter


def fin_du_contexte(contexte: str, n: int) -> str:
    """Les n derniers caractères du contexte (le texte vide pour n = 0)."""
    if len(contexte) < n:
        raise ValueError(MESSAGE_CONTEXTE_COURT)
    return contexte[len(contexte) - n :]


# region: distribution
def distribution(
    comptes: dict[str, Counter[str]], alphabet: list[str], contexte: str, n: int
) -> list[tuple[str, float]]:
    """La probabilité de chaque caractère après ce contexte, du plus probable au moins probable.

    Lissage de Laplace : on ajoute 1 au compte de chaque caractère de l'alphabet,
    pour qu'aucun ne soit jamais impossible. Un contexte jamais vu donne donc la
    même probabilité à tous.
    """
    if not alphabet:
        raise ValueError(MESSAGE_TEXTE_VIDE)
    suivants = comptes.get(fin_du_contexte(contexte, n), Counter())
    total = sum(suivants.values())
    v = len(alphabet)
    probabilites = [(c, (suivants[c] + 1) / (total + v)) for c in alphabet]
    # Du plus probable au moins probable ; à égalité, le plus petit point de code d'abord.
    return sorted(probabilites, key=lambda cp: (-cp[1], cp[0]))
# fin: distribution


# region: poids
def poids(comptes_du_contexte: Counter[str], alphabet: list[str], temperature: float) -> list[float]:
    """Le poids de chaque caractère de l'alphabet, dans l'ordre de l'alphabet, pour tirer au sort.

    La température change la forme des probabilités : 1 les suit (compte + 1),
    0,5 les durcit (le carré), 2 les adoucit (la racine carrée), et 0 ne garde
    que le caractère le plus compté.
    """
    if temperature == 1:
        return [comptes_du_contexte[c] + 1 for c in alphabet]
    if temperature == 0.5:
        return [(comptes_du_contexte[c] + 1) * (comptes_du_contexte[c] + 1) for c in alphabet]
    if temperature == 2:
        return [math.sqrt(comptes_du_contexte[c] + 1) for c in alphabet]
    if temperature == 0:
        # Le premier des plus comptés : l'alphabet est trié, donc le plus petit point de code.
        meilleur = 0
        for i, c in enumerate(alphabet):
            if comptes_du_contexte[c] > comptes_du_contexte[alphabet[meilleur]]:
                meilleur = i
        return [1 if i == meilleur else 0 for i in range(len(alphabet))]
    raise ValueError(MESSAGE_TEMPERATURE)
# fin: poids


# region: tirer
def tirer(poids: list[float], u: float) -> int:
    """L'indice tiré par u, un nombre de [0, 1[ : on pose les poids bout à bout, et u en choisit un."""
    total = 0.0
    for p in poids:
        total += p
    cible = u * total
    cumul = 0.0
    for i, p in enumerate(poids):
        cumul += p
        if cumul > cible:
            return i
    # Seul un arrondi peut venir ici : le dernier poids non nul est tiré.
    for i in range(len(poids) - 1, -1, -1):
        if poids[i] > 0:
            return i
    raise ValueError(MESSAGE_AUCUN_POIDS)
# fin: tirer


# region: generer
def generer(
    comptes: dict[str, Counter[str]],
    alphabet: list[str],
    n: int,
    depart: str,
    longueur: int,
    temperature: float,
    graine: int,
) -> str:
    """Le départ, suivi de `longueur` caractères tirés un à un d'après les n derniers.

    Un tirage par caractère, avec le même hasard que le site : la même graine
    donne le même texte, ici comme dans la page.
    """
    if not alphabet:
        raise ValueError(MESSAGE_TEXTE_VIDE)
    fin_du_contexte(depart, n)  # lève l'erreur si le départ est trop court
    hasard = Hasard(graine)
    texte = depart
    for _ in range(longueur):
        suivants = comptes.get(fin_du_contexte(texte, n), Counter())
        texte += alphabet[tirer(poids(suivants, alphabet, temperature), hasard.uniforme())]
    return texte
# fin: generer


def part_jamais_vue(comptes: dict[str, Counter[str]], validation: str, n: int) -> tuple[int, int]:
    """Combien de contextes du texte de validation le modèle n'a jamais vus, et combien il y en a."""
    absents = total = 0
    for i in range(n, len(validation)):
        total += 1
        if validation[i - n : i] not in comptes:
            absents += 1
    return absents, total


def tourne_en_rond(texte: str, longueur: int = 20) -> bool:
    """Vrai si les `longueur` derniers caractères du texte sont déjà apparus plus tôt."""
    if len(texte) <= longueur:
        return False
    fin = texte[len(texte) - longueur :]
    return texte.find(fin) < len(texte) - longueur


# region: perplexite
def perplexite(
    comptes: dict[str, Counter[str]], alphabet: list[str], n: int, validation: str
) -> float:
    """La surprise moyenne du modèle sur un texte : exp de la moyenne des −ln p.

    p est la probabilité (lissée) que le modèle donnait au vrai caractère. Une
    perplexité de 12 veut dire que le modèle hésite comme s'il choisissait,
    à chaque caractère, entre 12 possibilités également probables.
    """
    v = len(alphabet)
    somme = 0.0
    nombre = 0
    for i in range(n, len(validation)):
        suivants = comptes.get(validation[i - n : i], Counter())
        total = sum(suivants.values())
        p = (suivants[validation[i]] + 1) / (total + v)
        somme += -math.log(p)
        nombre += 1
    if nombre == 0:
        raise ValueError(f"Le texte est trop court : il faut au moins {n + 1} caractères pour mesurer la perplexité.")
    return math.exp(somme / nombre)
# fin: perplexite
