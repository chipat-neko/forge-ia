"""Quelques questions de MMMLU en français, notées par le modèle sans qu'il écrive un mot.

MMMLU (`openai/MMMLU`) est MMLU traduit en 14 langues par des traducteurs humains : des questions à
quatre choix, sur 57 matières, du lycée à l'université. La configuration `FR_FR` est la française. Ce
projet ne s'en sert pas pour mesurer « ton IA » (le rapport de forge utilise les QCM de FrenchBench) :
il en lit quelques questions, au hasard mais avec une graine, pour les noter une par une sous les yeux
du lecteur. Le jeu est lu en flux depuis Hugging Face, sans le copier dans le dépôt.

Licence : MIT, lue sur la page du jeu (voir `LICENCE_VERIFIEE_LE`). Le relevé la recopie avec
l'adresse du jeu.
"""

import datetime
import os
import random
from collections.abc import Iterable

from forge.evaluation.qcm import QCM, scores_qcm

from evaluation_pas_a_pas.pas_a_pas import choix_prefere, scores_par_octet

JEU = "openai/MMMLU"
CONFIGURATION = "FR_FR"
PARTIE = "test"
ADRESSE = "https://huggingface.co/datasets/openai/MMMLU"
LICENCE = "MIT"
LICENCE_VERIFIEE_LE = "2026-11-10"
LETTRES = ("A", "B", "C", "D")


def lever_le_mode_hors_ligne() -> list[str]:
    """Lève, pour ce processus seulement, le mode hors ligne de Hugging Face (`HF_HUB_OFFLINE=1`), et rend les variables levées.

    Cette variable est souvent posée pour les autres projets (c'est le cas sur le PC de l'auteur), et lire
    MMMLU a besoin du réseau. Comme `python -m forge evaluer` pour FrenchBench, on la lève avant que
    `datasets` ne la lise à son import.
    """
    levees = []
    for variable in ("HF_HUB_OFFLINE", "HF_DATASETS_OFFLINE"):
        if os.environ.get(variable, "").strip().upper() in {"1", "ON", "YES", "TRUE"}:
            os.environ[variable] = "0"
            levees.append(variable)
    return levees


def lignes_du_jeu() -> Iterable[dict]:
    """Les lignes de MMMLU (configuration `FR_FR`, partie `test`), lues en flux : rien n'est téléchargé en entier."""
    for variable in lever_le_mode_hors_ligne():
        print(f"{variable} est à 1\u202f: levé pour cette commande seulement, qui a besoin du réseau.", flush=True)
    from datasets import load_dataset  # ici : `datasets` lit HF_HUB_OFFLINE à son import

    return load_dataset(JEU, CONFIGURATION, split=PARTIE, streaming=True)


def qcm_de_la_ligne(ligne: dict) -> QCM:
    """Une ligne de MMMLU en QCM\u202f: « Question\u202f: … » puis « Réponse\u202f: », et les quatre réponses A à D pour choix.

    Colonnes lues\u202f: `Question`, `A` à `D` et `Answer` (la lettre de la bonne réponse). `Subject` (la
    matière) ne sert pas.
    """
    contexte = f"Question : {str(ligne['Question']).strip()}\nRéponse :"  # espaces ordinaires, comme ARC dans forge
    choix = [" " + str(ligne[lettre]).strip() for lettre in LETTRES]
    lettre = str(ligne["Answer"]).strip().upper()
    if lettre not in LETTRES:
        raise ValueError(f"La bonne réponse {ligne['Answer']!r} d'une ligne de MMMLU n'est pas l'une des lettres A à D.")
    return QCM(contexte, choix, LETTRES.index(lettre))


def choix_distincts(ligne: dict) -> bool:
    """Vrai si les quatre réponses d'une ligne sont différentes (et aucune n'est vide)."""
    reponses = [str(ligne[lettre]).strip() for lettre in LETTRES]
    return all(reponses) and len(set(reponses)) == len(reponses)


def exemples_mmmlu(n: int = 6, graine: int = 0, lignes: Iterable[dict] | None = None) -> list[QCM]:
    """`n` questions de MMMLU (français) tirées au hasard avec `graine`, dans l'ordre où le jeu les donne.

    Le jeu est lu en flux, une seule fois, avec un tirage « de réservoir » : on garde `n` questions, et la
    question numéro `i` en remplace une au hasard avec la probabilité `n / (i + 1)`. Chaque question a ainsi
    la même chance d'être gardée, sans qu'on connaisse le nombre de questions. Les lignes dont deux réponses
    sont identiques ou vides sont ignorées (la bonne réponse y serait ambiguë). Mêmes `n`, `graine` et jeu,
    mêmes questions. `lignes` remplace la lecture sur Hugging Face (les tests).
    """
    if n < 1:
        raise ValueError(f"n vaut {n}\u202f: il faut au moins une question.")
    source = lignes_du_jeu() if lignes is None else lignes
    hasard = random.Random(graine)
    gardees: list[tuple[int, dict]] = []
    rang = -1
    for ligne in source:
        if not choix_distincts(ligne):
            continue  # deux choix identiques (des tableaux mal traduits) : la bonne réponse serait ambiguë
        rang += 1
        if len(gardees) < n:
            gardees.append((rang, ligne))
        else:
            place = hasard.randrange(rang + 1)
            if place < n:
                gardees[place] = (rang, ligne)
    if len(gardees) < n:
        raise ValueError(
            f"{JEU} ({CONFIGURATION}) n'a donné que {len(gardees)} question(s) pour {n} demandée(s). "
            "Vérifie ta connexion à Hugging Face, ou demande moins de questions."
        )
    return [qcm_de_la_ligne(ligne) for _, ligne in sorted(gardees, key=lambda g: g[0])]


# region: noter-exemples
def noter_exemples(modele, tokenizer, qcms: list[QCM]) -> dict:
    """Note des questions\u202f: pour chacune, les scores de ses choix, le choix préféré du modèle et la bonne réponse.

    Les `scores` sont des log-vraisemblances (en nats), les `scores_normalises` ces scores divisés par
    les octets du choix : le choix préféré est celui du plus grand score normalisé. Rend aussi
    l'adresse et la licence du jeu, et le nombre de questions justes.
    """
    scores = scores_qcm(modele, tokenizer, qcms)
    questions = []
    for qcm, vraisemblances in zip(qcms, scores):
        normalises = scores_par_octet(qcm, vraisemblances)
        prefere = choix_prefere(normalises)
        questions.append(
            {
                "contexte": qcm.contexte,
                "choix": qcm.choix,
                "scores": vraisemblances,
                "scores_normalises": normalises,
                "prefere": prefere,
                "bonne": qcm.bonne,
                "juste": prefere == qcm.bonne,
            }
        )
    return {
        "jeu": {
            "nom": JEU,
            "configuration": CONFIGURATION,
            "partie": PARTIE,
            "adresse": ADRESSE,
            "licence": LICENCE,
            "licence_verifiee_le": LICENCE_VERIFIEE_LE,
            "lu_le": datetime.date.today().isoformat(),
        },
        "n": len(questions),
        "justes": sum(q["juste"] for q in questions),
        "hasard": sum(1 / len(q.choix) for q in qcms) / len(qcms),
        "questions": questions,
    }
# fin: noter-exemples
