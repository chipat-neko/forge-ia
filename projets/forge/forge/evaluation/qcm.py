"""Les questions à choix multiples (QCM) en français : HellaSwag et ARC-Challenge de FrenchBench.

Un modèle de langage ne « répond » pas à une question : il donne une probabilité à chaque
texte possible. Pour un QCM, on lui présente le contexte (la question, ou le début d'une
histoire), puis, pour chaque choix, on calcule la log-vraisemblance de ce choix écrit à la suite
du contexte : la somme, sur les jetons du choix, de `ln(probabilité du jeton sachant tout ce qui
précède)`. Sa réponse est le choix le plus vraisemblable.

Deux façons de comparer les choix :

- l'exactitude : le choix de plus grande log-vraisemblance totale. Un choix long a plus de jetons
  à deviner, donc une log-vraisemblance plus basse : cette façon favorise les réponses courtes ;
- l'exactitude normalisée : on divise d'abord chaque log-vraisemblance par le nombre d'octets
  UTF-8 du choix tel qu'il est écrit à la suite du contexte (espace initiale comprise, comme
  pour la log-vraisemblance elle-même). On compare des « nats par octet ».

Le hasard, lui, vaut `1 / nombre de choix` (en moyenne sur les questions). Un modèle qui ne
sait rien tombe autour de cette valeur, plus ou moins loin selon le nombre de questions : la
marge du hasard (`marge_hasard`) est la demi-largeur de l'intervalle à 95 % d'un résultat qui ne
devrait qu'au hasard. Seul un écart plus grand qu'elle dit quelque chose du modèle (le verdict du
rapport s'appuie sur elle, voir `rapport.verdict`).

Cette mesure est « maison » : le gabarit des questions, le jeton `<|fin_texte|>` en tête de
chaque séquence et la normalisation par octets sont les nôtres, donc les scores ne se comparent
qu'entre nos modèles et au hasard, pas aux scores publiés de FrenchBench.

Les deux jeux sont des traductions automatiques en français (CroissantLLM, arXiv 2402.00786).
"""

import math
import re
from collections.abc import Iterable
from dataclasses import dataclass
from itertools import islice
from typing import Literal

import torch

from forge.evaluation.perte import autocast, en_evaluation

# Le texte d'un document est suivi de `<|fin_texte|>` dans les données d'entraînement : c'est ce
# que le modèle a vu avant le début de chaque document. On le met donc en tête de chaque séquence
# (`<|debut_texte|>` n'a jamais servi à l'entraînement : son vecteur est resté au hasard).
JETON_DE_DEBUT = "<|fin_texte|>"

# Nombre de jetons (lignes × positions) passés d'un coup au modèle : il borne la mémoire de la
# carte graphique (les scores de tous les jetons possibles pour chaque position, 32 768 nombres).
JETONS_PAR_LOT = 8192
# Et nombre de séquences au plus par lot, quand elles sont très courtes.
SEQUENCES_PAR_LOT = 64

# Pour chaque test : le jeu sur Hugging Face et la partie utilisée.
JEUX = {
    "hellaswag": ("manu/french_bench_hellaswag", "validation"),
    "arc": ("manu/french_bench_arc_challenge", "test"),
}

# Nombre de questions de chaque partie, relevé le 03/11/2026 (le rapport dit « les N premières
# questions sur … » quand il n'en passe qu'une partie).
TOTAL_DES_QUESTIONS = {"hellaswag": 9338, "arc": 1169}


@dataclass
class QCM:
    """Une question : `contexte`, les `choix` (le texte écrit à la suite du contexte) et `bonne`.

    `bonne` est l'indice (à partir de 0) du bon choix. Chaque choix commence par son espace
    (« " bleu." ») : c'est le texte exact qui suit le contexte.
    """

    contexte: str
    choix: list[str]
    bonne: int


# --- Lire les deux jeux ------------------------------------------------------------------


def _lignes_du_jeu(jeu: str, split: str) -> Iterable[dict]:
    """Les lignes d'un jeu de Hugging Face (téléchargé une fois, puis gardé dans `HF_HOME`)."""
    # Import ici : `datasets` lit `HF_HUB_OFFLINE` à son import, que `python -m forge evaluer`
    # lève juste avant (voir `forge.__main__`).
    from datasets import load_dataset

    return load_dataset(jeu, split=split)


# Les marqueurs de WikiHow, en anglais ou, quand la traduction automatique les a traduits (plus de
# 600 fois dans HellaSwag), en français : « [titre] », « [étape] », « [sous-étapes] », « [en-tête] »…
_MARQUEURS_WIKIHOW = re.compile(
    r"\[\s*(?:header|title|steps?|substeps?|sou?s-?s?teps?|en-?t[êe]te|titre|[ée]tapes?|sous-?[ée]tapes?)\s*\]",
    re.IGNORECASE,
)
_FINS_DE_PHRASE = (".", "!", "?", ":", ";", "…", "»", ")", '"')


def _nettoyer(texte: str) -> str:
    """Enlève les marqueurs de WikiHow (« [header] », « [title] », « [step] », « [substeps] » et leurs traductions).

    Chaque marqueur sépare deux phrases : on le remplace par un point si la partie qui précède
    n'en a pas, puis par une espace (le prétraitement d'origine de HellaSwag collait un point
    après chaque « [title] », même après un point : « douche.. »).
    """
    parties = [partie.strip() for partie in _MARQUEURS_WIKIHOW.split(texte)]
    parties = [partie for partie in parties if partie]
    nettoyees = [p if p.endswith(_FINS_DE_PHRASE) else p + "." for p in parties[:-1]] + parties[-1:]
    return re.sub(r" {2,}", " ", " ".join(nettoyees))


def _qcm_hellaswag(ligne: dict) -> QCM:
    """Une ligne de `manu/french_bench_hellaswag` (split `validation`) en QCM.

    Colonnes utilisées : `ctx_a` (début du contexte), `ctx_b` (début de la phrase à finir, que
    HellaSwag met après `ctx_a` avec une majuscule), `endings` (les 4 fins possibles) et `label`
    (l'indice de la bonne fin, écrit comme un TEXTE : « 3 »). `ctx` (`ctx_a` et `ctx_b` collés,
    sans majuscule) et `activity_label` (en anglais dans ce jeu) ne servent pas.
    """
    ctx_b = ligne["ctx_b"].strip()
    contexte = _nettoyer(f"{ligne['ctx_a']} {ctx_b[:1].upper() + ctx_b[1:]}")
    choix = [" " + _nettoyer(fin) for fin in ligne["endings"]]
    bonne = int(ligne["label"])
    if not 0 <= bonne < len(choix):
        raise ValueError(f"Ligne {ligne.get('ind')} de HellaSwag : label {ligne['label']!r} pour {len(choix)} fins.")
    return QCM(contexte, choix, bonne)


def _qcm_arc(ligne: dict) -> QCM:
    """Une ligne de `manu/french_bench_arc_challenge` (split `test`) en QCM.

    Colonnes utilisées : `question`, `choices` (la liste des textes des choix, 3 à 5) et
    `answerKey` (la lettre du bon choix, « A » à « E » ; le jeu d'origine numérote quelques
    questions « 1 » à « 4 », et la clé est alors ce chiffre : aucune dans la partie `test`, mais
    on le lit aussi). La question est présentée comme « Question : … » puis « Réponse : », et
    chaque choix la prolonge. `id` ne sert qu'aux messages.
    """
    contexte = f"Question : {ligne['question'].strip()}\nRéponse :"
    choix = [" " + texte.strip() for texte in ligne["choices"]]
    cle = str(ligne["answerKey"]).strip().upper()
    if len(cle) == 1 and cle.isalpha():
        bonne = ord(cle) - ord("A")
    elif cle.isdigit():
        bonne = int(cle) - 1
    else:
        bonne = -1
    if not 0 <= bonne < len(choix):
        raise ValueError(
            f"Question {ligne.get('id')} d'ARC : la clé de la bonne réponse {ligne['answerKey']!r} ne "
            f"désigne aucun des {len(choix)} choix."
        )
    return QCM(contexte, choix, bonne)


def charger_frenchbench(nom: Literal["hellaswag", "arc"], n_max: int | None = None) -> list[QCM]:
    """Charge les `n_max` premières questions (toutes si `None`) d'un des deux tests français.

    - `"hellaswag"` : `manu/french_bench_hellaswag`, partie `validation` (9 338 questions, 4
      choix : la suite la plus plausible d'une scène ou d'un tutoriel) ;
    - `"arc"` : `manu/french_bench_arc_challenge`, partie `test` (1 169 questions de sciences,
      le plus souvent 4 choix, parfois 3 ou 5).

    Il faut le réseau la première fois (puis le jeu reste dans le cache de Hugging Face).
    """
    if nom not in JEUX:
        raise ValueError(f"Test inconnu : {nom!r}. Choix possibles : « hellaswag », « arc ».")
    if n_max is not None and n_max < 0:
        raise ValueError(f"n_max vaut {n_max} : il faut un nombre de questions positif ou nul, ou None pour toutes.")
    jeu, split = JEUX[nom]
    convertir = _qcm_hellaswag if nom == "hellaswag" else _qcm_arc
    lignes = _lignes_du_jeu(jeu, split)
    if n_max is not None:
        lignes = islice(lignes, n_max)
    try:
        return [convertir(ligne) for ligne in lignes]
    except KeyError as erreur:
        raise ValueError(
            f"Il manque la colonne {erreur} dans une ligne de {jeu} : le jeu a changé depuis le 03/11/2026. "
            "Compare ses colonnes à celles que lit forge.evaluation.qcm."
        ) from erreur


# --- Noter les choix ---------------------------------------------------------------------


def _verifier(qcm: QCM, rang: int) -> None:
    """Refuse une question impossible à noter, avec son numéro (à partir de 1)."""
    if len(qcm.choix) < 2:
        raise ValueError(f"La question {rang + 1} n'a que {len(qcm.choix)} choix : il en faut au moins deux.")
    if not 0 <= qcm.bonne < len(qcm.choix):
        raise ValueError(
            f"La bonne réponse de la question {rang + 1} est l'indice {qcm.bonne}, mais la question a "
            f"{len(qcm.choix)} choix (indices 0 à {len(qcm.choix) - 1})."
        )


@torch.no_grad()
def scores_qcm(modele, tokenizer, qcms: list[QCM], jetons_par_lot: int = JETONS_PAR_LOT) -> list[list[float]]:
    """La log-vraisemblance (en nats) de chaque choix de chaque question, rangée comme les `qcms`.

    Chaque séquence est `<|fin_texte|>` + contexte + choix, passée d'un coup au modèle ; on somme
    les log-probabilités des seuls jetons du choix. Contexte et choix sont encodés séparément (le
    choix commence par une espace, que le pré-découpage du tokenizer colle au mot qui suit : la
    frontière tombe toujours entre deux pré-mots). Si la séquence dépasse `longueur_contexte`,
    le début du contexte est oublié ; un choix plus long que le modèle perd ses premiers jetons
    (cas qui n'arrive pas avec ces jeux).

    Les séquences sont triées par longueur et regroupées par lots d'au plus `jetons_par_lot`
    jetons : les plus courtes sont complétées à droite, ce qui ne change aucun score (le modèle
    est causal, une position ne voit jamais ce qui la suit).
    """
    appareil = next(modele.parameters()).device
    longueur = modele.config.longueur_contexte
    debut = tokenizer.id_special(JETON_DE_DEBUT)
    sequences = []  # (ids, première position à noter, numéro de la question, numéro du choix)
    for i, qcm in enumerate(qcms):
        _verifier(qcm, i)
        contexte = tokenizer.encoder(qcm.contexte)
        for j, choix in enumerate(qcm.choix):
            reponse = tokenizer.encoder(choix)
            if not reponse:
                raise ValueError(f"Le choix {j + 1} de la question {i + 1} est vide : il faut un texte à noter.")
            ids = ([debut, *contexte, *reponse])[-longueur:]
            sequences.append((ids, max(len(ids) - len(reponse), 1), i, j))
    sequences.sort(key=lambda sequence: -len(sequence[0]))  # les plus longues d'abord

    scores = [[0.0] * len(qcm.choix) for qcm in qcms]
    with en_evaluation(modele):
        rang = 0
        while rang < len(sequences):
            taille = len(sequences[rang][0])  # la plus longue du lot
            lot = sequences[rang : rang + max(1, min(SEQUENCES_PAR_LOT, jetons_par_lot // taille))]
            rang += len(lot)
            x = torch.zeros((len(lot), taille), dtype=torch.long)
            for ligne, (ids, *_) in enumerate(lot):
                x[ligne, : len(ids)] = torch.tensor(ids)
            x = x.to(appareil)
            with autocast(appareil):
                logits, _ = modele(x)
            sommes = []
            for ligne, (ids, premiere, _, _) in enumerate(lot):
                # La position t prédit le jeton t + 1 : les jetons à noter sont ceux de `premiere` à la fin.
                log_probas = torch.log_softmax(logits[ligne, premiere - 1 : len(ids) - 1].float(), dim=-1)
                cibles = x[ligne, premiere : len(ids)]
                sommes.append(log_probas.gather(-1, cibles[:, None]).sum())
            for (_, _, i, j), somme in zip(lot, torch.stack(sommes).tolist()):
                scores[i][j] = somme
    return scores


def _marge_95(exactitude: float, n: int) -> float:
    """Demi-largeur de l'intervalle de confiance à 95 % d'une proportion mesurée sur `n` questions.

    C'est la marge de Wald : elle s'annule quand l'exactitude vaut 0 ou 1, même sur 5 questions.
    Pour juger un écart au hasard, on utilise `marge_hasard`.
    """
    return 1.96 * math.sqrt(exactitude * (1 - exactitude) / n)


def _marge_hasard(qcms: list[QCM]) -> float:
    """Demi-largeur de l'intervalle à 95 % de l'exactitude d'un tirage au sort sur ces questions.

    Chaque question est juste avec la probabilité `p = 1 / nombre de choix`, de variance
    `p (1 - p)` ; ces variances s'additionnent d'une question à l'autre. Elle ne dépend que des
    questions, jamais du résultat : elle ne s'annule pas à 0 bonne réponse.
    """
    variance = sum((1 / len(qcm.choix)) * (1 - 1 / len(qcm.choix)) for qcm in qcms)
    return 1.96 * math.sqrt(variance) / len(qcms)


def evaluer_qcm(modele, tokenizer, qcms: list[QCM], jetons_par_lot: int = JETONS_PAR_LOT) -> dict:
    """Passe les questions au modèle ; renvoie les mesures (des proportions entre 0 et 1).

    - `exactitude` : part des questions où le choix de plus grande log-vraisemblance est le bon ;
    - `exactitude_normalisee` : idem après division de chaque log-vraisemblance par le nombre
      d'octets UTF-8 du choix ;
    - `hasard` : moyenne de `1 / nombre de choix` ;
    - `n` : nombre de questions ;
    - `marge_95` et `marge_95_normalisee` : demi-largeur de l'intervalle à 95 % de chacune des
      deux exactitudes (marge de Wald : nulle à 0 ou 100 %) ;
    - `marge_hasard` : demi-largeur de l'intervalle à 95 % d'un résultat dû au seul hasard sur
      ces questions. Une exactitude à moins de `marge_hasard` du `hasard` ne se distingue pas du
      hasard ; c'est elle qui sert à juger (`rapport.verdict`).

    À égalité parfaite, le premier choix gagne.
    """
    if not qcms:
        raise ValueError("Aucune question à évaluer : la liste est vide.")
    scores = scores_qcm(modele, tokenizer, qcms, jetons_par_lot)
    justes = justes_normalisees = 0
    for qcm, vraisemblances in zip(qcms, scores):
        indices = range(len(vraisemblances))
        octets = [len(choix.encode("utf-8")) for choix in qcm.choix]
        justes += max(indices, key=vraisemblances.__getitem__) == qcm.bonne
        justes_normalisees += max(indices, key=lambda k: vraisemblances[k] / octets[k]) == qcm.bonne
    n = len(qcms)
    exactitude, normalisee = justes / n, justes_normalisees / n
    return {
        "exactitude": exactitude,
        "exactitude_normalisee": normalisee,
        "hasard": sum(1 / len(qcm.choix) for qcm in qcms) / n,
        "n": n,
        "marge_95": _marge_95(exactitude, n),
        "marge_95_normalisee": _marge_95(normalisee, n),
        "marge_hasard": _marge_hasard(qcms),
    }
