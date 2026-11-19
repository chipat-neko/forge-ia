"""Résumer, sans rien recalculer, ce que le plan 7 mesure sur ton IA : un rapport d'étape, et les longueurs des exemples.

- `resumer_etape(rapport)` lit le `rapport.json` de `python -m forge evaluer-etape` (voir
  `forge.evaluation.etape`) et en tire le relevé que le site lit, `mesures/etape-<version>.json` :
  `{version, etape, releve_le, empreinte, mesures, echantillons}`. Les `mesures` sont celles du rapport, telles
  quelles (une mesure dont les données manquaient reste `{"absente": "<raison>"}`), sans `echantillons`, que le
  relevé range à part ; `empreinte` est le SHA-256 des poids mesurés. Avec `reference=True`, c'est la version de
  référence du rapport (ton-ia-1.5, qui passe les mêmes mesures) qui est résumée, au lieu de la version évaluée.
  Avec `nom`, le relevé prend ce nom de version, et garde celui du rapport (`nom_au_rapport`) : c'est le cas des
  versions renommées après leur évaluation, dont le rapport, une archive, garde l'ancien nom ;
- `longueurs(jeu)` lit `train/documents.bin` d'un jeu d'affinage (en lecture seule) et compte les longueurs des
  exemples : `mesures/longueurs-sft-1.7.json`. Les longueurs sont un histogramme `[longueur, nombre]` : deux
  exemples de même longueur se rangent pareil dans `empaqueter`, la liste complète n'ajoute rien ;
- `balayage(dossiers)` lit le journal de chaque essai du balayage du taux d'apprentissage (en lecture seule) :
  son taux maximal et ses pertes de validation, `mesures/balayage-sft-1.7.json`.

La courbe d'entraînement et ses sessions ne passent pas par ce module : `pre_entrainement courbe` les relève
(voir le README).
"""

import datetime
import json
import math
import re
from collections import Counter
from pathlib import Path

import numpy as np
from forge.evaluation.etape import VERSION_DU_RAPPORT_D_ETAPE
from forge.suivi import lire_journal

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
def resumer_etape(rapport: Path, reference: bool = False, nom: str | None = None) -> dict:
    """Le relevé d'un rapport d'étape de forge : `{version, etape, releve_le, empreinte, mesures, echantillons}`.

    `version` est celle de la Release mesurée (« ton-ia-1.7 »), `etape` celle du chapitre (« 1.7 »),
    `releve_le` la date du rapport (AAAA-MM-JJ), `empreinte` le SHA-256 des poids mesurés. Rien n'est
    recalculé : les mesures et les échantillons sont ceux du rapport, avec ses noms de clés.
    `reference=True` résume la version de référence du rapport. `nom` remplace le nom de la version, et le
    relevé garde alors celui du rapport sous `nom_au_rapport` (s'il est différent).
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
    empreinte = source.get("empreinte")
    if not isinstance(empreinte, str) or re.fullmatch(r"[0-9a-f]{64}", empreinte) is None:
        raise ValueError(
            f"Les mesures de {source.get('version', rapport)} dans {rapport} n'ont pas l'empreinte SHA-256 de leurs poids. {refaire}"
        )
    releve = {"version": source["version"] if nom is None else nom}
    if nom is not None and nom != source["version"]:
        releve["nom_au_rapport"] = source["version"]
    return {
        **releve,
        "etape": donnees["etape"],
        "releve_le": donnees["date"][:10],
        "empreinte": empreinte,
        "mesures": {cle: valeur for cle, valeur in mesures.items() if cle != "echantillons"},
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


# region: balayage
def balayage(dossiers: list[Path]) -> dict:
    """Les essais du balayage du taux d'apprentissage, lus dans leurs journaux : `{releve_le, essais}`.

    Chaque dossier est la sortie d'un essai de `forge entrainer` (`entrainements/sft-1.7-balayage-<taux>`), dont
    seul `journal.jsonl` est lu. Un essai : `essai` (le nom du dossier), `taux_max` (le plus haut taux du journal,
    atteint à la fin de l'échauffement, sans ses restes d'arrondi), `pas` (le dernier pas) et `validations`, les
    `[pas, perte de validation]` du journal, telles quelles. Les essais sont rangés par taux croissant.
    """
    if not dossiers:
        raise ValueError("Il faut au moins un dossier d'essai à résumer.")
    essais = []
    for dossier in map(Path, dossiers):
        journal = dossier / "journal.jsonl"
        # Un pas refait (après une reprise) : sa dernière ligne.
        pas = {ligne["pas"]: ligne for ligne in lire_journal(journal) if "evenement" not in ligne and isinstance(ligne.get("pas"), int)}
        if not pas:
            raise FileNotFoundError(
                f"Le journal {journal} n'existe pas ou n'a aucun pas : donne le dossier de sortie d'un essai de `forge entrainer`."
            )
        taux = [float(ligne["taux"]) for ligne in pas.values() if isinstance(ligne.get("taux"), int | float) and math.isfinite(ligne["taux"])]
        validations = [
            [numero, float(ligne["perte_val"])]
            for numero, ligne in sorted(pas.items())
            if isinstance(ligne.get("perte_val"), int | float) and math.isfinite(ligne["perte_val"])
        ]
        if not taux or not validations:
            raise ValueError(f"Le journal {journal} n'a aucune perte de validation, ou aucun taux : ce n'est pas celui d'un essai du balayage.")
        essais.append({"essai": dossier.name, "taux_max": float(f"{max(taux):.12g}"), "pas": max(pas), "validations": validations})
    essais.sort(key=lambda e: e["taux_max"])
    for avant, apres in zip(essais, essais[1:]):
        if avant["taux_max"] == apres["taux_max"]:
            raise ValueError(
                f"Les essais {avant['essai']} et {apres['essai']} ont le même taux ({avant['taux_max']}) : un balayage essaie des taux différents."
            )
    return {"releve_le": datetime.date.today().isoformat(), "essais": essais}
# fin: balayage
