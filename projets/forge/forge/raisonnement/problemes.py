"""Des problèmes de calcul en français, plus faciles que GSM8K, justes par construction.

Chaque problème se génère par programme, tout en entiers, d'une graine : la même graine donne le même
problème, avec sa réponse et une trace courte (une étape de calcul par ligne, `"a op b = c"`, avec `op`
parmi `+`, `−` (U+2212), `×` et `÷`). La réponse n'est jamais « devinée » : elle est calculée, étape par
étape, en même temps que l'énoncé s'écrit. Le SFT de raisonnement et le mini-GRPO de la partie 1.9
s'appuient dessus.

Chaque usage a sa plage de graines (`GRAINES_ENTRAINEMENT`, `GRAINES_EVALUATION`, …). Les problèmes de
l'évaluation sont réservés à l'évaluation, et aucun problème d'un autre usage ne peut leur être identique,
**par construction** et pas seulement par chance : trois lots de prénoms disjoints, `PRENOMS_ENTRAINEMENT` (20, pour
l'entraînement, le RL, les préférences et la victoire), `PRENOMS_VALIDATION_RL` (4, pour la validation du RL, que le
RL ne doit pas avoir vue) et `PRENOMS_EVALUATION` (6, pour l'évaluation). Chaque énoncé nomme au
moins une personne : deux énoncés dont les prénoms viennent de listes disjointes sont forcément différents.

Ce que le jumeau TypeScript du site doit reproduire (plan 8), pour une même graine, à l'identique :

1. Le hasard : `forge.hasard.Hasard(graine)`, avec `entier(a, b)` et `choisir`, rien d'autre.
2. `generer_probleme(famille, difficulte, graine)` crée `h = Hasard(graine)` et **jette le premier tirage**
   (`h.suivant32()`) : il est réservé au choix du couple (famille, difficulté) de `generer_problemes`, pour
   que ce choix ne soit pas lié au contenu du problème. Les tirages suivent ensuite, dans l'ordre exact écrit
   dans chaque fonction `_addition`, `_soustraction`… (prénoms, objets, nombres, variante de phrase).
3. Les listes `GENRES_DES_PRENOMS` (30, dans cet ordre ; les 24 premiers sont ceux de l'entraînement, les 6
   derniers ceux de l'évaluation, les 4 d'avant ceux de la validation du RL) et `OBJETS` (20, dans cet ordre), avec leur genre et leur fourchette de prix.
4. Le choix des prénoms et des objets distincts (`_tirer_distincts` : un indice dans les restants, retiré
   ensuite), l'accord (`quantite`, `euros`, `ans` : le singulier jusqu'à 1 inclus, 0 compris), l'élision
   (`de`, `que`) et l'article (`un`) et les gabarits de phrases, caractère pour caractère.
5. Dans `generer_problemes` : le couple se tire de `Hasard(graine_depart + i).entier(0, k − 1)` dans la
   liste des couples permis, **dans l'ordre de `FAMILLES` puis de `FORMES[famille]`** ; les énoncés en double
   sont retirés (le premier reste).
6. La vérification, dans `forge.raisonnement.verification` : `extraire_nombre` et `est_juste`.

Le français : les nombres s'écrivent en chiffres, sans séparateur de milliers (ils restent petits) ;
« 1 pomme » mais « 2 pommes », « 1 euro » mais « 2 euros », « 1 an » mais « 2 ans » ; « de pommes » mais
« d'oranges », « que Léa » mais « qu'Alice » ; « il » ou « elle » selon le prénom. Aucun participe passé accordé avec un complément placé
avant (« Combien de pommes a-t-elle mangées ») : les questions les évitent.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypeVar

from forge.conversation.format import Tour
from forge.hasard import Hasard

T = TypeVar("T")

FAMILLES = ("addition", "soustraction", "multiplication", "partage", "achats", "ages")
DIFFICULTES = (1, 2, 3)  # le nombre d'étapes de calcul

# Les difficultés de chaque famille.
FORMES: dict[str, tuple[int, ...]] = {
    "addition": (1, 2, 3),
    "soustraction": (1, 2, 3),
    "multiplication": (1, 2),
    "partage": (1, 2),
    "achats": (2, 3),
    "ages": (2, 3),
}

# Chaque usage a sa plage de graines, de un million de graines.
GRAINES_ENTRAINEMENT = 0
GRAINES_EVALUATION = 1_000_000
GRAINES_RL = 2_000_000
GRAINES_PREFERENCES = 3_000_000
GRAINES_VICTOIRE = 4_000_000
GRAINES_VALIDATION_RL = 5_000_000

_LARGEUR_DES_PLAGES = 1_000_000
_GRAINE_MAX = 2**32 - 1  # au-delà, SplitMix32 rejouerait une graine déjà vue

# Les 30 prénoms, avec leur genre. Les 20 premiers servent à l'entraînement, au RL, aux préférences et à la victoire,
# les 4 suivants (2 féminins, 2 masculins) à la validation du RL seule, les 6 derniers (3 féminins, 3 masculins) à
# l'évaluation seule. Pas de « h » aspiré : l'élision de « de » est toujours juste.
GENRES_DES_PRENOMS: tuple[tuple[str, str], ...] = (
    ("Léa", "f"), ("Lucas", "m"), ("Alice", "f"), ("Hugo", "m"), ("Chloé", "f"), ("Thomas", "m"),
    ("Emma", "f"), ("Nathan", "m"), ("Inès", "f"), ("Théo", "m"), ("Jade", "f"), ("Louis", "m"),
    ("Lina", "f"), ("Arthur", "m"), ("Manon", "f"), ("Jules", "m"), ("Camille", "f"), ("Adam", "m"),
    ("Sarah", "f"), ("Enzo", "m"), ("Zoé", "f"), ("Maxime", "m"), ("Louise", "f"), ("Paul", "m"),
    # réservés à l'évaluation (les quatre d'avant : à la validation du RL)
    ("Éva", "f"), ("Émile", "m"), ("Océane", "f"), ("Ethan", "m"), ("Clara", "f"), ("Gabriel", "m"),
)
PRENOMS = tuple(nom for nom, _ in GENRES_DES_PRENOMS)
PRENOMS_ENTRAINEMENT = PRENOMS[:20]
PRENOMS_VALIDATION_RL = PRENOMS[20:24]
PRENOMS_EVALUATION = PRENOMS[24:]
_GENRE_DU_PRENOM = dict(GENRES_DES_PRENOMS)


@dataclass(frozen=True)
class Objet:
    """Un objet qu'on compte ou qu'on achète : ses formes, son genre, et sa fourchette de prix (en euros, entiers)."""

    singulier: str
    pluriel: str
    genre: str  # « m » ou « f »
    prix_min: int
    prix_max: int


# Pas de « h » aspiré ici non plus.
OBJETS: tuple[Objet, ...] = (
    Objet("pomme", "pommes", "f", 1, 3),
    Objet("orange", "oranges", "f", 1, 4),
    Objet("abricot", "abricots", "m", 1, 3),
    Objet("gâteau", "gâteaux", "m", 2, 6),
    Objet("crayon", "crayons", "m", 1, 3),
    Objet("stylo", "stylos", "m", 2, 5),
    Objet("cahier", "cahiers", "m", 2, 6),
    Objet("livre", "livres", "m", 5, 20),
    Objet("gomme", "gommes", "f", 1, 3),
    Objet("bille", "billes", "f", 1, 2),
    Objet("carte", "cartes", "f", 1, 5),
    Objet("bougie", "bougies", "f", 2, 6),
    Objet("ballon", "ballons", "m", 3, 12),
    Objet("fleur", "fleurs", "f", 1, 5),
    Objet("sucette", "sucettes", "f", 1, 3),
    Objet("jouet", "jouets", "m", 5, 25),
    Objet("autocollant", "autocollants", "m", 1, 3),
    Objet("chaussette", "chaussettes", "f", 2, 8),
    Objet("tasse", "tasses", "f", 3, 10),
    Objet("œuf", "œufs", "m", 1, 2),
)

_VOYELLES = "aeiouyhàâäéèêëîïôöùûüœæ"
_BILLETS = (10, 20, 50, 100, 200, 500)
_LIEUX = ("dans une boîte", "dans un sac", "dans un panier", "dans un carton")


@dataclass(frozen=True)
class Probleme:
    id: str  # « famille-difficulté-graine » : de quoi le régénérer
    famille: str
    difficulte: int
    enonce: str
    etapes: tuple[str, ...]  # « a op b = c », une par opération
    reponse: int


# --- Le français : accords, élision, pronoms ---


def quantite(n: int, objet: Objet) -> str:
    """« 1 pomme », « 2 pommes » : le singulier jusqu'à 1 (0 compris), le pluriel au-delà."""
    return f"{n} {objet.singulier if n < 2 else objet.pluriel}"


def euros(n: int) -> str:
    """« 1 euro », « 2 euros »."""
    return f"{n} euro" if n < 2 else f"{n} euros"


def ans(n: int) -> str:
    """« 1 an », « 2 ans »."""
    return f"{n} an" if n < 2 else f"{n} ans"


def de(mot: str) -> str:
    """« de pommes », mais « d'oranges » et « d'Hugo » : l'élision devant une voyelle ou un « h » muet."""
    return ("d'" if mot[0].lower() in _VOYELLES else "de ") + mot


def que(mot: str) -> str:
    """« que Léa », mais « qu'Alice » et « qu'Hugo » : l'élision de « que » devant une voyelle ou un « h » muet."""
    return ("qu'" if mot[0].lower() in _VOYELLES else "que ") + mot


def un(objet: Objet) -> str:
    """« un stylo », « une pomme » : l'article indéfini suit le genre."""
    return ("un " if objet.genre == "m" else "une ") + objet.singulier


def _il(prenom: str) -> str:
    return "il" if _GENRE_DU_PRENOM[prenom] == "m" else "elle"


def _liste(morceaux: Sequence[str]) -> str:
    """« a », « a et b », « a, b et c »."""
    if len(morceaux) == 1:
        return morceaux[0]
    return ", ".join(morceaux[:-1]) + " et " + morceaux[-1]


def _etape(a: int, op: str, b: int, c: int) -> str:
    return f"{a} {op} {b} = {c}"


# --- Les tirages ---


def _tirer_distincts(h: Hasard, suite: Sequence[T], k: int) -> list[T]:
    """k éléments distincts : à chaque fois, un indice dans ce qui reste, que l'on retire ensuite."""
    restants = list(suite)
    pris = []
    for _ in range(k):
        pris.append(restants.pop(h.entier(0, len(restants) - 1)))
    return pris


def usage_de_la_graine(graine: int) -> str:
    """« evaluation » de [GRAINES_EVALUATION, GRAINES_RL[, « validation_rl » de [GRAINES_VALIDATION_RL, +1 000 000[,
    « entrainement » pour toutes les autres."""
    if GRAINES_EVALUATION <= graine < GRAINES_RL:
        return "evaluation"
    if GRAINES_VALIDATION_RL <= graine < GRAINES_VALIDATION_RL + _LARGEUR_DES_PLAGES:
        return "validation_rl"
    return "entrainement"


# --- Les familles : chacune rend (énoncé, étapes, réponse) ---
# L'ordre des tirages est celui du texte : le site le refait tel quel.


def _addition(h: Hasard, d: int, prenoms: Sequence[str]) -> tuple[str, list[str], int]:
    (n,) = _tirer_distincts(h, prenoms, 1)
    o = h.choisir(OBJETS)
    v = [h.entier(10, 99) for _ in range(d + 1)]
    variante = h.entier(0, 1)
    etapes, total = [], v[0]
    for x in v[1:]:
        etapes.append(_etape(total, "+", x, total + x))
        total += x
    il = _il(n)
    if variante == 0:
        recu = f"{v[1]} de plus" if d == 1 else ", puis ".join(str(x) for x in v[1:])
        enonce = (f"{n} a {quantite(v[0], o)}. {il.capitalize()} en reçoit {recu}. "
                  f"Combien {de(o.pluriel)} {n} a-t-{il} en tout ?")
    else:
        parties = [f"{quantite(v[0], o)} {_LIEUX[0]}"] + [f"{x} {_LIEUX[i + 1]}" for i, x in enumerate(v[1:])]
        enonce = f"{n} met {_liste(parties)}. Combien y a-t-il {de(o.pluriel)} en tout ?"
    return enonce, etapes, total


def _soustraction(h: Hasard, d: int, prenoms: Sequence[str]) -> tuple[str, list[str], int]:
    (n,) = _tirer_distincts(h, prenoms, 1)
    o = h.choisir(OBJETS)
    if d == 1:
        depart = h.entier(20, 99)
        retraits = [h.entier(10, depart - 1)]
    else:
        retraits = [h.entier(10, 50) for _ in range(d)]
        depart = sum(retraits) + h.entier(10, 99)
    variante = h.entier(0, 1)
    etapes, reste = [], depart
    for x in retraits:
        etapes.append(_etape(reste, "−", x, reste - x))
        reste -= x
    liste = ", puis ".join(str(x) for x in retraits)
    il = _il(n)
    if variante == 0:
        enonce = (f"{n} a {quantite(depart, o)}. {il.capitalize()} en donne {liste}. "
                  f"Combien {de(o.pluriel)} {n} a-t-{il} maintenant ?")
    else:
        enonce = f"Dans une boîte, il y a {quantite(depart, o)}. {n} en prend {liste}. Combien en reste-t-il dans la boîte ?"
    return enonce, etapes, reste


def _multiplication(h: Hasard, d: int, prenoms: Sequence[str]) -> tuple[str, list[str], int]:
    (n,) = _tirer_distincts(h, prenoms, 1)
    o = h.choisir(OBJETS)
    a = h.entier(2, 9)
    b = h.entier(10, 99)
    variante = h.entier(0, 1)
    c = a * b
    etapes = [_etape(a, "×", b, c)]
    il = _il(n)
    if variante == 0:
        enonce = f"{n} a {a} boîtes de {quantite(b, o)} chacune."
    else:
        enonce = f"{n} remplit {a} sacs avec {quantite(b, o)} dans chaque sac."
    reponse = c
    if d == 1:
        question = "en tout"
    else:
        signe = h.entier(0, 1)
        if signe == 0:
            extra = h.entier(10, 99)
            etapes.append(_etape(c, "+", extra, c + extra))
            reponse = c + extra
            enonce += f" {il.capitalize()} en ajoute encore {extra}."
        else:
            extra = h.entier(2, min(99, c - 1))
            etapes.append(_etape(c, "−", extra, c - extra))
            reponse = c - extra
            enonce += f" {il.capitalize()} en donne {extra}."
        question = "maintenant"
    return f"{enonce} Combien {de(o.pluriel)} {n} a-t-{il} {question} ?", etapes, reponse


def _partage(h: Hasard, d: int, prenoms: Sequence[str]) -> tuple[str, list[str], int]:
    (n,) = _tirer_distincts(h, prenoms, 1)
    o = h.choisir(OBJETS)
    b = h.entier(2, 9)
    c = h.entier(2, 25) if d == 1 else h.entier(3, 30)
    total = b * c
    t0 = h.entier(1, total - 1) if d == 2 else 0
    variante = h.entier(0, 1)
    il = _il(n)
    pl = o.pluriel
    if d == 1:
        etapes = [_etape(total, "÷", b, c)]
        if variante == 0:
            enonce = (f"{n} a {quantite(total, o)}. {il.capitalize()} les partage en parts égales entre {b} amis. "
                      f"Combien {de(pl)} reçoit chaque ami ?")
        else:
            enonce = (f"{n} range {quantite(total, o)} dans {b} boîtes, avec autant {de(pl)} dans chaque boîte. "
                      f"Combien {de(pl)} y a-t-il dans chaque boîte ?")
    else:
        t1 = total - t0
        etapes = [_etape(t0, "+", t1, total), _etape(total, "÷", b, c)]
        if variante == 0:
            enonce = (f"{n} a {quantite(t0, o)}. {il.capitalize()} en reçoit {t1} de plus, puis {il} partage le tout "
                      f"en parts égales entre {b} amis. Combien {de(pl)} reçoit chaque ami ?")
        else:
            enonce = (f"{n} range {quantite(t0, o)} dans une boîte et {t1} dans une autre. {il.capitalize()} répartit "
                      f"ensuite le tout dans {b} sacs, avec autant {de(pl)} dans chaque sac. "
                      f"Combien {de(pl)} y a-t-il dans chaque sac ?")
    return enonce, etapes, c


def _achats(h: Hasard, d: int, prenoms: Sequence[str]) -> tuple[str, list[str], int]:
    (n,) = _tirer_distincts(h, prenoms, 1)
    o1, o2 = _tirer_distincts(h, OBJETS, 2)
    q1 = h.entier(2, 9)
    p1 = h.entier(o1.prix_min, o1.prix_max)
    c1 = q1 * p1
    etapes = [_etape(q1, "×", p1, c1)]
    il = _il(n)
    if d == 2:
        variante = h.entier(0, 1)
        if variante == 0:
            p2 = h.entier(o2.prix_min, o2.prix_max)
            etapes.append(_etape(c1, "+", p2, c1 + p2))
            enonce = (f"{n} achète {quantite(q1, o1)} à {euros(p1)} pièce et {un(o2)} à {euros(p2)}. "
                      f"Combien {n} paie-t-{il} en tout ?")
            return enonce, etapes, c1 + p2
        billet = next(b for b in _BILLETS if b > c1)
        etapes.append(_etape(billet, "−", c1, billet - c1))
        enonce = (f"{n} achète {quantite(q1, o1)} à {euros(p1)} pièce. {il.capitalize()} paie avec un billet de "
                  f"{billet} euros. Combien d'euros {n} reçoit-{il} en monnaie ?")
        return enonce, etapes, billet - c1
    q2 = h.entier(2, 9)
    p2 = h.entier(o2.prix_min, o2.prix_max)
    c2 = q2 * p2
    etapes += [_etape(q2, "×", p2, c2), _etape(c1, "+", c2, c1 + c2)]
    enonce = (f"{n} achète {quantite(q1, o1)} à {euros(p1)} pièce et {quantite(q2, o2)} à {euros(p2)} pièce. "
              f"Combien {n} paie-t-{il} en tout ?")
    return enonce, etapes, c1 + c2


def _ages(h: Hasard, d: int, prenoms: Sequence[str]) -> tuple[str, list[str], int]:
    noms = _tirer_distincts(h, prenoms, d)  # d = 2 ou 3 : le nombre de personnes
    a = h.entier(15, 60)
    if d == 2:
        sens = h.entier(0, 1)  # 0 : de plus, 1 : de moins
        e = h.entier(1, 9)
        b = a + e if sens == 0 else a - e
        etapes = [_etape(a, "+" if sens == 0 else "−", e, b)]
        presentation = f"{noms[0]} a {ans(a)}. {noms[1]} a {ans(e)} {'de plus' if sens == 0 else 'de moins'} {que(noms[0])}."
        actuel = b
    else:
        e1 = h.entier(1, 9)
        e2 = h.entier(1, 9)
        b = a + e1
        actuel = b - e2
        etapes = [_etape(a, "+", e1, b), _etape(b, "−", e2, actuel)]
        presentation = (f"{noms[0]} a {ans(a)}. {noms[1]} a {ans(e1)} de plus {que(noms[0])}, "
                        f"et {noms[2]} a {ans(e2)} de moins {que(noms[1])}.")
    futur = h.entier(0, 1) == 0
    k = h.entier(1, 10) if futur else h.entier(1, min(10, actuel - 1))
    etapes.append(_etape(actuel, "+" if futur else "−", k, actuel + k if futur else actuel - k))
    cible = noms[-1]
    if futur:
        question = f"Quel âge aura {cible} dans {ans(k)} ?"
    else:
        question = f"Quel âge avait {cible} il y a {ans(k)} ?"
    return f"{presentation} {question}", etapes, actuel + k if futur else actuel - k


_PRENOMS_DE_L_USAGE = {
    "entrainement": PRENOMS_ENTRAINEMENT,
    "validation_rl": PRENOMS_VALIDATION_RL,
    "evaluation": PRENOMS_EVALUATION,
}

_GENERATEURS = {
    "addition": _addition,
    "soustraction": _soustraction,
    "multiplication": _multiplication,
    "partage": _partage,
    "achats": _achats,
    "ages": _ages,
}


def generer_probleme(famille: str, difficulte: int, graine: int) -> Probleme:
    """Le problème de cette famille et de cette difficulté, tiré de cette graine (la même graine, le même problème).

    Un couple (famille, difficulté) absent de `FORMES` lève `ValueError`, comme une graine qui n'est pas
    de 0 à 2^32 − 1. Les prénoms viennent de `PRENOMS_EVALUATION` pour les graines d'évaluation, de
    `PRENOMS_VALIDATION_RL` pour celles de la validation du RL, de `PRENOMS_ENTRAINEMENT` pour toutes les autres :
    un problème d'évaluation ou de validation du RL ne peut jamais être identique à celui d'un autre usage.
    """
    if famille not in FORMES:
        raise ValueError(f"Famille inconnue : {famille!r}. Les familles sont {', '.join(FAMILLES)}.")
    if difficulte not in FORMES[famille]:
        permises = ", ".join(str(x) for x in FORMES[famille])
        raise ValueError(
            f"La difficulté {difficulte!r} n'existe pas pour la famille « {famille} » : "
            f"ses difficultés sont {permises}."
        )
    if isinstance(graine, bool) or not isinstance(graine, int) or not 0 <= graine <= _GRAINE_MAX:
        raise ValueError(f"La graine {graine!r} doit être un entier de 0 à 2^32 − 1 (4 294 967 295) : donne une autre graine.")
    h = Hasard(graine)
    h.suivant32()  # réservé au choix du couple (famille, difficulté) de `generer_problemes`
    prenoms = _PRENOMS_DE_L_USAGE[usage_de_la_graine(graine)]
    enonce, etapes, reponse = _GENERATEURS[famille](h, difficulte, prenoms)
    return Probleme(f"{famille}-{difficulte}-{graine}", famille, difficulte, enonce, tuple(etapes), reponse)


def conversation_de_probleme(p: Probleme) -> list[Tour]:
    """L'utilisateur dit l'énoncé ; l'assistant pense les étapes (une par ligne), puis répond « La réponse est N. »."""
    return [
        Tour("utilisateur", p.enonce),
        Tour("assistant", f"La réponse est {p.reponse}.", pensee="\n".join(p.etapes)),
    ]


def generer_problemes(
    n: int,
    graine_depart: int,
    familles: Sequence[str] = FAMILLES,
    difficultes: Sequence[int] = DIFFICULTES,
) -> list[Probleme]:
    """Les `n` problèmes des graines `graine_depart` à `graine_depart + n − 1` (le i-ème vient de `graine_depart + i`).

    Le couple (famille, difficulté) de chaque problème est tiré de la même graine, parmi ceux de `FORMES`
    que `familles` et `difficultes` permettent (`ValueError` s'il n'y en a aucun). Les énoncés en double sont
    retirés : la liste peut donc avoir moins de `n` éléments. Une liste ne peut pas enjamber la plage d'évaluation ni celle de la
    validation du RL : ses problèmes seraient mélangés à ceux d'un autre usage.
    """
    if n < 0:
        raise ValueError(f"Le nombre de problèmes ne peut pas être négatif (reçu {n}).")
    inconnues = [f for f in familles if f not in FORMES]
    if inconnues:
        raise ValueError(f"Famille inconnue : {inconnues[0]!r}. Les familles sont {', '.join(FAMILLES)}.")
    inconnues = [d for d in difficultes if d not in DIFFICULTES]
    if inconnues:
        raise ValueError(f"Difficulté inconnue : {inconnues[0]!r}. Les difficultés sont 1, 2 et 3.")
    couples = [(f, d) for f in FAMILLES if f in familles for d in FORMES[f] if d in difficultes]
    if not couples:
        raise ValueError(
            f"Aucun couple (famille, difficulté) n'est permis par familles={tuple(familles)} et "
            f"difficultes={tuple(difficultes)}. Chaque famille a ses difficultés : "
            + ", ".join(f"{f} {'/'.join(str(x) for x in FORMES[f])}" for f in FAMILLES)
            + "."
        )
    if n == 0:
        return []
    derniere = graine_depart + n - 1
    for debut, fin, nom in (
        (GRAINES_EVALUATION, GRAINES_RL, "d'évaluation"),
        (GRAINES_VALIDATION_RL, GRAINES_VALIDATION_RL + _LARGEUR_DES_PLAGES, "de validation du RL"),
    ):
        touche = graine_depart < fin and derniere >= debut
        if touche and not (graine_depart >= debut and derniere < fin):
            raise ValueError(
                f"Les graines de {graine_depart} à {derniere} enjambent la plage {nom} ({debut} à {fin - 1}) : "
                "ses problèmes se mélangeraient aux autres. "
                "Choisis des graines entièrement dedans ou entièrement dehors, ou donne moins de problèmes."
            )
    vus: set[str] = set()
    problemes = []
    for i in range(n):
        graine = graine_depart + i
        famille, difficulte = couples[Hasard(graine).entier(0, len(couples) - 1)]
        p = generer_probleme(famille, difficulte, graine)
        if p.enonce not in vus:
            vus.add(p.enonce)
            problemes.append(p)
    return problemes
