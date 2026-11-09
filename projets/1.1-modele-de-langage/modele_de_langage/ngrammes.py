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
    """Le texte d'apprentissage du projet, lu en UTF-8, sans traduire les fins de ligne (comme le fait le site)."""
    with open(CHEMIN_TEXTE, encoding="utf-8", newline="") as fichier:
        return fichier.read()


def couper(texte: str) -> tuple[str, str]:
    """Sépare le texte : les 90 premiers % pour apprendre, le reste pour vérifier (en points de code)."""
    limite = len(texte) * 9 // 10
    return texte[:limite], texte[limite:]


def alphabet(texte: str) -> list[str]:
    """Les caractères distincts du texte, triés par point de code."""
    return sorted(set(texte))


# region: compter
def compter(texte: str, n: int) -> dict[str, Counter[str]]:
    """Ce qui suit chaque contexte de n caractères, compté."""
    # Pour n = 0, le contexte est vide : on compte tout.
    comptes: dict[str, Counter[str]] = {}
    for i in range(n, len(texte)):
        contexte = texte[i - n : i]
        if contexte not in comptes:
            comptes[contexte] = Counter()
        comptes[contexte][texte[i]] += 1
    return comptes
# fin: compter


def compter_par_ordre(texte: str, n: int) -> list[dict[str, Counter[str]]]:
    """Les comptes de tous les ordres de 0 à n : `[compter(texte, 0), …, compter(texte, n)]`.

    `generer` s'en sert pour reculer d'un ordre quand un contexte est inconnu.
    """
    return [compter(texte, k) for k in range(n + 1)]


def fin_du_contexte(contexte: str, n: int) -> str:
    """Les n derniers caractères du contexte (le texte vide pour n = 0)."""
    if len(contexte) < n:
        raise ValueError(MESSAGE_CONTEXTE_COURT)
    return contexte[len(contexte) - n :]


# region: distribution
def distribution(
    comptes: dict[str, Counter[str]],
    alphabet: list[str],
    contexte: str,
    n: int,
) -> list[tuple[str, float]]:
    """La chance de chaque caractère, lissée (Laplace)."""
    if not alphabet:
        raise ValueError(MESSAGE_TEXTE_VIDE)
    fin = fin_du_contexte(contexte, n)
    suivants = comptes.get(fin, Counter())
    total = sum(suivants.values())
    v = len(alphabet)
    chances = [
        (c, (suivants[c] + 1) / (total + v)) for c in alphabet
    ]
    # Du plus probable au moins probable ; à égalité,
    # le plus petit point de code d'abord.
    return sorted(chances, key=lambda cp: (-cp[1], cp[0]))
# fin: distribution


# region: poids
def poids(
    suivants: Counter[str],
    alphabet: list[str],
    temperature: float,
) -> list[float]:
    """Le poids de chaque caractère, à cette température."""
    comptes = [suivants[c] for c in alphabet]
    if temperature == 1:
        return comptes
    if temperature == 0.5:
        return [k * k for k in comptes]
    if temperature == 2:
        return [math.sqrt(k) for k in comptes]
    if temperature == 0:
        # Le premier des plus comptés : l'alphabet est trié.
        meilleur, record = -1, 0
        for i, k in enumerate(comptes):
            if k > record:
                meilleur, record = i, k
        gagnant = [0] * len(comptes)
        if meilleur >= 0:
            gagnant[meilleur] = 1
        return gagnant
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
    comptes_par_ordre: list[dict[str, Counter[str]]],
    alphabet: list[str],
    n: int,
    depart: str,
    longueur: int,
    temperature: float,
    graine: int,
) -> str:
    """Le départ, suivi de `longueur` caractères tirés."""
    if not alphabet:
        raise ValueError(MESSAGE_TEXTE_VIDE)
    fin_du_contexte(depart, n)  # départ trop court : erreur
    hasard = Hasard(graine)
    texte = depart
    for _ in range(longueur):
        suivants = None
        for k in range(n, -1, -1):
            fin = texte[len(texte) - k :]
            suivants = comptes_par_ordre[k].get(fin)
            if suivants is not None:
                break
        if suivants is None:
            raise ValueError(MESSAGE_TEXTE_VIDE)
        p = poids(suivants, alphabet, temperature)
        texte += alphabet[tirer(p, hasard.uniforme())]
    return texte
# fin: generer


# region: tirage
def tirage(
    comptes_par_ordre: list[dict[str, Counter[str]]],
    alphabet: list[str],
    contexte: str,
    n: int,
    temperature: float,
) -> tuple[int, list[tuple[str, float]]]:
    """Ce que `generer` tirerait après ce contexte : l'ordre utilisé, puis la chance de chaque caractère.

    Comme `generer`, on recule tant que les k derniers caractères n'ont jamais été vus
    (k = n, puis n − 1, … jusqu'à 0). La chance d'un caractère est son poids, à cette
    température, divisé par le total des poids. Seuls les caractères de poids non nul
    sont rendus, du plus probable au moins probable (à égalité, le plus petit point de
    code d'abord).
    """
    if not alphabet:
        raise ValueError(MESSAGE_TEXTE_VIDE)
    fin_du_contexte(contexte, n)  # lève l'erreur si le contexte est trop court
    suivants = None
    ordre = n
    for k in range(n, -1, -1):
        suivants = comptes_par_ordre[k].get(contexte[len(contexte) - k :])
        if suivants is not None:
            ordre = k
            break
    if suivants is None:
        raise ValueError(MESSAGE_TEXTE_VIDE)
    les_poids = poids(suivants, alphabet, temperature)
    total = 0.0
    for p in les_poids:
        total += p
    chances = [(c, p / total) for c, p in zip(alphabet, les_poids) if p > 0]
    return ordre, sorted(chances, key=lambda cp: (-cp[1], cp[0]))
# fin: tirage


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


def trop_court(n: int) -> str:
    """Le message d'un texte trop court pour mesurer la perplexité."""
    return f"Le texte est trop court : il faut au moins {n + 1} caractères pour mesurer la perplexité."


# region: perplexite
def perplexite(
    comptes: dict[str, Counter[str]],
    alphabet: list[str],
    n: int,
    validation: str,
) -> float:
    """La surprise moyenne : exp de la moyenne des −ln p."""
    if not alphabet:
        raise ValueError(MESSAGE_TEXTE_VIDE)
    v = len(alphabet)
    somme = 0.0
    nombre = 0
    for i in range(n, len(validation)):
        contexte = validation[i - n : i]
        suivants = comptes.get(contexte, Counter())
        total = sum(suivants.values())
        p = (suivants[validation[i]] + 1) / (total + v)
        somme += -math.log(p)
        nombre += 1
    if nombre == 0:
        raise ValueError(trop_court(n))
    return math.exp(somme / nombre)
# fin: perplexite
