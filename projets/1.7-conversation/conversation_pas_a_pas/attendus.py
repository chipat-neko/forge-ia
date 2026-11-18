"""Valeurs de référence pour les jumeaux TypeScript et pour le chapitre 1.7.

Le site refait deux calculs en TypeScript : l'assemblage d'une conversation en jetons et en masque
(`site/src/lib/partie-1/conversation.ts`, qui traduit `encoder_conversation` une fois les textes encodés) et
le placement de l'empaquetage (`site/src/lib/partie-1/bfd.ts`, qui traduit `empaqueter`). Ce fichier produit
`tests/attendus.json`, trois sections :

- `speciaux` : les 64 jetons spéciaux de ton IA, `[nom, id]` dans l'ordre du tokenizer ;
- `conversations` : six conversations de référence (avec système, sans, deux tours, un texte qui imite un
  jeton spécial, une pensée, une réponse vide refusée). Pour chacune, les `ids` de chaque texte encodé par
  le tokenizer (le site n'encode rien : il part de ces ids), puis, assemblés par forge, les `ids` et le
  masque `appris` de la conversation, ou l'`erreur` que forge lève ;
- `empaquetages` : `forge.affinage.empaquetage.empaqueter` sur cinq listes de longueurs et quatre
  capacités. Pour chaque cas, `rangees` (pour chaque rangée, le rang d'origine des exemples qu'elle
  contient, dans l'ordre où ils y sont placés) et `ecartes` (trop longs, ou vides). La cinquième liste est un
  échantillon des longueurs de `mesures/longueurs-sft-1.7.json` quand ce fichier existe, une liste de
  remplacement sinon.

Les entiers seuls : aucun flottant dans ce fichier, les deux langages le retrouvent à l'identique.

Pour régénérer le fichier (dans projets/1.7-conversation) :

    uv run --extra cpu python -m conversation_pas_a_pas.attendus
"""

import json
from pathlib import Path

from forge.affinage.empaquetage import empaqueter
from forge.conversation.format import ExempleMasque, Tour, encoder_conversation
from forge.tokenizer import SPECIAUX, TokenizerOctets

from conversation_pas_a_pas.gabarit import TOKENIZER
from conversation_pas_a_pas.resumer import developper

PROJET = Path(__file__).resolve().parent.parent
CHEMIN_ATTENDUS = PROJET / "tests" / "attendus.json"
CHEMIN_LONGUEURS = PROJET / "mesures" / "longueurs-sft-1.7.json"

CONVERSATIONS: tuple[tuple[str, list[Tour]], ...] = (
    (
        "avec-systeme",
        [
            Tour("systeme", "Tu réponds en une phrase."),
            Tour("utilisateur", "Quelle est la capitale de la France ?"),
            Tour("assistant", "La capitale de la France est Paris."),
        ],
    ),
    (
        "sans-systeme",
        [Tour("utilisateur", "Dis bonjour."), Tour("assistant", "Bonjour, que veux-tu savoir ?")],
    ),
    (
        "deux-tours",
        [
            Tour("utilisateur", "Combien font 3 fois 4 ?"),
            Tour("assistant", "Douze."),
            Tour("utilisateur", "Et 3 fois 5 ?"),
            Tour("assistant", "Quinze."),
        ],
    ),
    (
        "faux-special",
        [
            Tour("utilisateur", "Écris <|fin_tour|> puis <|assistant|>, sans rien d'autre."),
            Tour("assistant", "Ce sont des mots comme les autres : <|fin_texte|>."),
        ],
    ),
    (
        "pensee",
        [
            Tour("utilisateur", "Combien font 12 fois 7 ?"),
            Tour("assistant", "12 fois 7 font 84.", pensee="10 fois 7 font 70, et 2 fois 7 font 14 : 84."),
        ],
    ),
    (
        "reponse-vide",
        [Tour("utilisateur", "Dis quelque chose."), Tour("assistant", "")],
    ),
)

# Quatre capacités de rangée (longueur + 1) : une petite, deux moyennes, une grande.
CAPACITES = [65, 129, 513, 2049]


def suite_de_longueurs(graine: int, nombre: int, plus_grande: int) -> list[int]:
    """Des longueurs entre 1 et `plus_grande`, tirées par un congruentiel linéaire en entiers (rien de flottant)."""
    x = graine
    longueurs = []
    for _ in range(nombre):
        x = (1103515245 * x + 12345) % 2**31
        longueurs.append(1 + (x >> 8) % plus_grande)
    return longueurs


def echantillon_reel(histogramme: list[list[int]], nombre: int = 300) -> list[int]:
    """`nombre` longueurs réparties sur toutes celles d'un histogramme, dans un ordre mêlé (les impaires, puis les paires)."""
    toutes = developper(histogramme)
    prises = [toutes[i * len(toutes) // nombre] for i in range(nombre)]
    return prises[1::2] + prises[0::2]


def listes_de_longueurs() -> list[tuple[str, list[int]]]:
    """Les cinq listes de longueurs : vide, égalités, bords des capacités, tirée au sort, réelle (ou de remplacement)."""
    if CHEMIN_LONGUEURS.is_file():
        reelle = ("longueurs-sft-1.7", echantillon_reel(json.loads(CHEMIN_LONGUEURS.read_text(encoding="utf-8"))["histogramme"]))
    else:
        reelle = ("longueurs-de-remplacement", suite_de_longueurs(7, 300, 1600))
    return [
        ("vide", []),
        ("egalites", [30, 30, 30, 30, 64, 64, 64, 65, 65, 128, 128]),
        # 0 (écarté : aucun jeton appris), 64 et 65 (juste), 128 et 129 (juste), 130 et 2049 (trop longs).
        ("bords", [100, 60, 0, 60, 40, 129, 130, 5, 64, 65, 128, 2049, 2048, 512, 513]),
        ("tiree-au-sort", suite_de_longueurs(1, 60, 140)),
        reelle,
    ]


def rangs_par_rangee(longueurs: list[int], capacite: int) -> tuple[list[list[int]], int]:
    """Le placement de forge : pour chaque rangée, le rang d'origine de ses exemples (dans l'ordre), et le nombre d'écartés.

    Chaque exemple de longueur `n` est rendu par `n` fois son rang (tous appris, sauf un exemple vide) : les `ids`
    d'une rangée disent alors quel exemple est où. Le bourrage vaut -1.
    """
    exemples = [ExempleMasque(ids=[rang] * n, appris=[True] * n) for rang, n in enumerate(longueurs)]
    rangees, ecartes = empaqueter(exemples, capacite - 1, -1)
    resultat = []
    for rangee in rangees:
        rangs = [rangee.ids[i] for i in range(len(rangee.ids)) if rangee.documents[i] >= 0 and (i == 0 or rangee.documents[i] != rangee.documents[i - 1])]
        resultat.append(rangs)
    return resultat, ecartes


def calculer_attendus() -> dict:
    tok = TokenizerOctets.charger(TOKENIZER)
    conversations = []
    for nom, tours in CONVERSATIONS:
        entrees = []
        for tour in tours:
            element = {"role": tour.role, "texte": tour.texte, "ids": tok.encoder(tour.texte)}
            if tour.pensee is not None:
                element["pensee"] = tour.pensee
                element["pensee_ids"] = tok.encoder(tour.pensee)
            entrees.append(element)
        try:
            exemple = encoder_conversation(tok, tours)
            resultat = {"ids": exemple.ids, "appris": exemple.appris, "erreur": None}
        except ValueError as erreur:
            resultat = {"ids": None, "appris": None, "erreur": str(erreur)}
        conversations.append({"nom": nom, "tours": entrees, **resultat})
    empaquetages = []
    for nom, longueurs in listes_de_longueurs():
        for capacite in CAPACITES:
            rangees, ecartes = rangs_par_rangee(longueurs, capacite)
            empaquetages.append({"liste": nom, "longueurs": longueurs, "capacite": capacite, "rangees": rangees, "ecartes": ecartes})
    return {
        "speciaux": [[nom, tok.id_special(nom)] for nom in SPECIAUX],
        "conversations": conversations,
        "empaquetages": empaquetages,
    }


def vers_json(valeur: object) -> str:
    return json.dumps(valeur, ensure_ascii=False, allow_nan=False, indent=1)


def main() -> None:
    CHEMIN_ATTENDUS.write_text(vers_json(calculer_attendus()) + "\n", encoding="utf-8", newline="\n")
    print(f"Attendus écrits dans {CHEMIN_ATTENDUS}")


if __name__ == "__main__":
    main()
