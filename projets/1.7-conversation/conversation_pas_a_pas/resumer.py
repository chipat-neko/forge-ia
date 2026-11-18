"""Résumer, sans rien recalculer, ce que le plan 7 mesure sur ton IA : un rapport d'étape, et les longueurs des exemples.

- `resumer_etape(rapport)` lit le `rapport.json` de `python -m forge evaluer-etape` (voir
  `forge.evaluation.etape`) et en tire le relevé que le site lit, `mesures/etape-<version>.json` :
  `{version, etape, releve_le, mesures, echantillons}`. Les `mesures` sont celles du rapport, telles quelles
  (une mesure dont les données manquaient reste `{"absente": "<raison>"}`), sans `echantillons`, que le
  relevé range à part. Avec `reference=True`, c'est la version de référence du rapport (ton-ia-1.5, qui
  passe les mêmes mesures) qui est résumée, au lieu de la version évaluée ;
- `longueurs(jeu)` lit `train/documents.bin` d'un jeu d'affinage (en lecture seule) et compte les longueurs des
  exemples : `mesures/longueurs-sft-1.7.json`. Les longueurs sont un histogramme `[longueur, nombre]` : deux
  exemples de même longueur se rangent pareil dans `empaqueter`, la liste complète n'ajoute rien.

La courbe d'entraînement et ses sessions ne passent pas par ce module : `pre_entrainement courbe` les relève
(voir le README).
"""

import datetime
import json
from collections import Counter
from pathlib import Path

import numpy as np
from forge.evaluation.etape import VERSION_DU_RAPPORT_D_ETAPE

CLES_DU_RAPPORT = ("version_du_rapport", "version", "etape", "date", "mesures")
LONGUEUR_DES_POSITIONS = np.dtype("<i2")  # documents.bin : un int16 par position, -1 pour le bourrage


def _lire_json(chemin: Path, quoi: str, refaire: str) -> dict:
    if not chemin.is_file():
        raise FileNotFoundError(f"{quoi} {chemin} n'existe pas. {refaire}")
    try:
        valeur = json.loads(chemin.read_text(encoding="utf-8"))
    except ValueError as erreur:
        raise ValueError(f"{chemin} n'est pas un fichier JSON lisible ({erreur}). {refaire}") from erreur
    if not isinstance(valeur, dict):
        raise ValueError(f"{chemin} n'est pas un objet JSON. {refaire}")
    return valeur


# region: resumer
def resumer_etape(rapport: Path, reference: bool = False) -> dict:
    """Le relevé d'un rapport d'étape de forge : `{version, etape, releve_le, mesures, echantillons}`.

    `version` est celle de la Release mesurée (« ton-ia-1.7 »), `etape` celle du chapitre (« 1.7 »),
    `releve_le` la date du rapport (AAAA-MM-JJ). Rien n'est recalculé : les mesures et les échantillons
    sont ceux du rapport, avec ses noms de clés. `reference=True` résume la version de référence du rapport.
    """
    refaire = "Relance `python -m forge evaluer-etape` avec la Release et l'étape voulues."
    rapport = Path(rapport)
    donnees = _lire_json(rapport, "Le rapport", refaire)
    if donnees.get("version_du_rapport") != VERSION_DU_RAPPORT_D_ETAPE:
        raise ValueError(
            f"{rapport} n'est pas un rapport d'étape de forge de version {VERSION_DU_RAPPORT_D_ETAPE} "
            f"(version lue : {donnees.get('version_du_rapport')!r}). {refaire}"
        )
    for cle in CLES_DU_RAPPORT:
        if cle not in donnees:
            raise ValueError(f"Le rapport {rapport} n'a pas de « {cle} ». {refaire}")
    source = donnees
    if reference:
        source = donnees.get("reference")
        if not isinstance(source, dict):
            raise ValueError(
                f"Le rapport {rapport} n'a pas de version de référence : il faut lancer `evaluer-etape` avec "
                f"--reference pour résumer ton-ia-1.5 à côté de {donnees['version']}."
            )
    mesures = source.get("mesures")
    if not isinstance(mesures, dict) or "echantillons" not in mesures:
        raise ValueError(f"Les mesures de {source.get('version', rapport)} dans {rapport} n'ont pas d'« echantillons ». {refaire}")
    if not isinstance(donnees["date"], str) or len(donnees["date"]) < 10:
        raise ValueError(f"La date de {rapport} ({donnees['date']!r}) n'est pas une date ISO. {refaire}")
    return {
        "version": source["version"],
        "etape": donnees["etape"],
        "releve_le": donnees["date"][:10],
        "mesures": {nom: valeur for nom, valeur in mesures.items() if nom != "echantillons"},
        "echantillons": mesures["echantillons"],
    }
# fin: resumer


# region: longueurs
def longueurs(jeu: Path) -> dict:
    """Les longueurs des exemples d'un jeu d'affinage, lues dans `train/documents.bin` (en lecture seule).

    Rend `{jeu, releve_le, longueur_des_rangees, rangees, exemples, jetons, min, mediane, moyenne, max,
    histogramme}` : `histogramme` est la liste croissante des `[longueur, nombre d'exemples]`. `documents.bin`
    donne, pour chaque position d'une rangée, le numéro de son exemple (-1 pour le bourrage) : la longueur
    d'un exemple est le nombre de positions qui portent son numéro.
    """
    jeu = Path(jeu)
    refaire = "Prépare le jeu avec `python -m forge preparer`, ou corrige le chemin de --jeu."
    index = _lire_json(jeu / "index.json", "L'index du jeu", refaire)
    fichier = jeu / "train" / "documents.bin"
    if not (jeu / ".complet").is_file() or not fichier.is_file():
        raise FileNotFoundError(f"Le jeu {jeu} est absent ou pas fini (pas de `.complet`, ou pas de train/documents.bin). {refaire}")
    largeur = int(index["longueur"]) + 1
    rangees = int(index["rangees"]["train"])
    documents = np.fromfile(fichier, dtype=LONGUEUR_DES_POSITIONS)
    if documents.size != rangees * largeur:
        raise ValueError(
            f"{fichier} a {documents.size} positions, l'index en annonce {rangees * largeur} ({rangees} rangées de {largeur}) : "
            f"le fichier a changé ou a été coupé. {refaire}"
        )
    compte: Counter[int] = Counter()
    for rangee in documents.reshape(rangees, largeur):
        _, tailles = np.unique(rangee[rangee >= 0], return_counts=True)
        compte.update(int(t) for t in tailles)
    toutes = sorted(compte.elements())
    n = len(toutes)
    if n == 0:
        raise ValueError(f"Le jeu {jeu} n'a aucun exemple dans train. {refaire}")
    mediane = toutes[n // 2] if n % 2 else (toutes[n // 2 - 1] + toutes[n // 2]) / 2
    return {
        "jeu": jeu.name,
        "releve_le": datetime.date.today().isoformat(),
        "longueur_des_rangees": largeur - 1,
        "rangees": rangees,
        "exemples": n,
        "jetons": sum(toutes),
        "min": toutes[0],
        "mediane": mediane,
        "moyenne": round(sum(toutes) / n, 2),
        "max": toutes[-1],
        "histogramme": [[longueur, compte[longueur]] for longueur in sorted(compte)],
    }
# fin: longueurs


def developper(histogramme: list[list[int]]) -> list[int]:
    """La liste croissante des longueurs d'un histogramme `[[longueur, nombre], …]`."""
    return [longueur for longueur, nombre in histogramme for _ in range(nombre)]
