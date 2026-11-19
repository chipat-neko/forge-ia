"""Résumer, sans rien recalculer, ce que le plan 7 mesure et construit pour ton IA 1.8.

- `resumer_etape(rapport)` lit le `rapport.json` de `python -m forge evaluer-etape` (voir `forge.evaluation.etape`)
  et en tire le relevé que le site lit, `mesures/etape-<version>.json` : `{version, etape, releve_le, mesures,
  echantillons}`. Les mesures sont celles du rapport, telles quelles (une mesure dont les données manquaient reste
  `{"absente": "<raison>"}`), sans `echantillons`, que le relevé range à part. Avec `reference=True`, c'est la
  version de référence du rapport qui est résumée ;
- `paires_exemples(jeu)` garde les premières paires de préférences du jeu `jeu` (le dossier que `forge preferences`
  écrit), avec leurs notes, leurs log-probabilités de référence et la source de leur invite avec sa licence :
  `mesures/paires-exemples.json`. Ce sont les premières paires d'entraînement, pas les plus belles ;
- `balayage(dossiers)` résume les essais du balayage de la DPO : leurs réglages, leur taux de victoire, la longueur
  de leurs réponses et la log-probabilité de la réponse choisie au début et à la fin de l'entraînement :
  `mesures/balayage-1.8.json` ;
- `courbes_dpo` (voir `courbes.py`) relève les courbes d'un journal : `mesures/entrainement-dpo-1.8.json`.
"""

import json
import math
import tomllib
from pathlib import Path

import numpy as np
from forge.affinage.jeu import lire_index
from forge.entrainement.boucle import ReglagesDPO
from forge.evaluation.etape import VERSION_DU_RAPPORT_D_ETAPE
from forge.fragments import lire_elements
from forge.preferences.construction import DOSSIER_DES_PAIRES, PREFIXE_DES_PAIRES
from forge.preferences.noter import Note
from pre_entrainement.journal import lire

CLES_DU_RAPPORT = ("version_du_rapport", "version", "etape", "date", "mesures")
CRITERES = Note._fields
SOURCE_DES_PROBLEMES = "problemes"
SOURCE_DES_QUESTIONS = "luth2_conversation"


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

    `version` est celle de la Release mesurée (« ton-ia-1.8 »), `etape` celle du chapitre (« 1.8 »),
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
                f"--reference pour résumer la référence à côté de {donnees['version']}."
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


# region: paires
def _reponse_de_la_paire(element: dict, rang: int, logp_de_reference: float) -> dict:
    """Une réponse d'une paire : son texte, si elle a fini, sa note (critère par critère), ses jetons appris et sa référence."""
    reponse = element["reponses"][rang]
    return {
        "texte": reponse["texte"],
        "terminee": reponse["terminee"],
        "note": dict(zip(CRITERES, element["notes"][rang])),
        "jetons": len(reponse["ids"]) + int(reponse["terminee"]),  # <|fin_tour|> compris : ce que la DPO apprend
        "logp_reference": logp_de_reference,
    }


def paires_exemples(jeu: Path, n: int = 6) -> list[dict]:
    """Les `n` premières paires d'entraînement du jeu `jeu` (un dossier écrit par `forge preferences`).

    Pour chacune : `id`, `source` (`nom`, `licence`, `lien` : l'invite vient de Luth-2, sous CC BY 4.0, ou d'un
    problème généré par le code du dépôt), `invite` (les tours), `contraintes` et `attendu`, puis la `choisie` et la
    `rejetee` (texte, terminée, note, jetons, log-probabilité de référence) et la `raison` qui les a départagées.

    La log-probabilité de référence est celle de `train/reference.bin`, que la DPO calcule avec la version de
    départ avant son premier pas : le jeu doit avoir été préparé par `forge entrainer` (méthode `dpo`).
    """
    jeu = Path(jeu)
    refaire = (
        "Fais les paires avec `python -m forge preferences`, puis lance la DPO (`forge entrainer`) : "
        f"elle calcule la référence de {jeu.name}."
    )
    if n < 1:
        raise ValueError(f"Il faut au moins une paire (reçu n = {n}).")
    index = lire_index(jeu)
    fichier_reference = jeu / "train" / "reference.bin"
    if not fichier_reference.is_file():
        raise FileNotFoundError(f"{fichier_reference} n'existe pas : sans lui, les log-probabilités de référence manquent. {refaire}")
    reference = np.fromfile(fichier_reference, dtype="<f8")
    sources = index.get("sources", {})
    gardees: list[dict] = []
    rang_de_paire = 0  # la k-ième paire d'entraînement tient dans les rangées 2k (choisie) et 2k + 1 (rejetée)
    for element in lire_elements(jeu / DOSSIER_DES_PAIRES, PREFIXE_DES_PAIRES):
        if element["paire"] is None or element["partie"] != "train":
            continue
        if 2 * rang_de_paire + 1 >= reference.size:
            raise ValueError(
                f"{fichier_reference} a {reference.size} valeurs : trop peu pour la paire {rang_de_paire + 1} du jeu. {refaire}"
            )
        choisie, rejetee = element["paire"]
        nom_de_la_source = SOURCE_DES_PROBLEMES if element["attendu"] is not None else SOURCE_DES_QUESTIONS
        source = sources.get(nom_de_la_source)
        if source is None:
            raise ValueError(f"L'index de {jeu} ne connaît pas la source « {nom_de_la_source} » : refais `forge preferences`.")
        gardees.append(
            {
                "id": element["id"],
                "source": {"nom": nom_de_la_source, "licence": source["licence"], "lien": source["lien"]},
                "invite": element["tours"],
                "contraintes": element["contraintes"],
                "attendu": element["attendu"],
                "choisie": _reponse_de_la_paire(element, choisie, float(reference[2 * rang_de_paire])),
                "rejetee": _reponse_de_la_paire(element, rejetee, float(reference[2 * rang_de_paire + 1])),
                "raison": element["raison"],
            }
        )
        rang_de_paire += 1
        if len(gardees) >= n:
            break
    if not gardees:
        raise ValueError(f"Le jeu {jeu} n'a aucune paire d'entraînement. {refaire}")
    return gardees
# fin: paires


# region: balayage
def _moyenne_des_extremites(valeurs: list[float]) -> tuple[float, float]:
    """La moyenne du premier et du dernier dixième des valeurs (au moins une de chaque côté)."""
    dixieme = max(1, len(valeurs) // 10)
    return sum(valeurs[:dixieme]) / dixieme, sum(valeurs[-dixieme:]) / dixieme


def _reglages_de_l_essai(config: Path) -> dict:
    """Les réglages que le balayage fait varier : le taux, bêta, la longueur normalisée et le poids du terme SFT."""
    if not config.is_file():
        raise FileNotFoundError(f"{config} n'existe pas : mets-y la configuration avec laquelle l'essai a été lancé.")
    try:
        valeurs = tomllib.loads(config.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as erreur:
        raise ValueError(f"{config} n'est pas un fichier TOML lisible ({erreur}).") from erreur
    if "taux_max" not in valeurs:
        raise ValueError(f"{config} n'a pas de `taux_max` : ce n'est pas la configuration d'un entraînement de forge.")
    dpo = ReglagesDPO(**valeurs.get("dpo", {}))
    return {
        "taux_max": valeurs["taux_max"],
        "beta": dpo.beta,
        "normaliser_longueur": dpo.normaliser_longueur,
        "poids_sft": dpo.poids_sft,
    }


def balayage(dossiers: list[Path]) -> list[dict]:
    """Un relevé par essai du balayage de la DPO, dans l'ordre des `dossiers`.

    Chaque dossier d'essai contient trois fichiers : `config.toml` (la configuration avec laquelle l'essai a été
    lancé), `journal.jsonl` (celui de `forge entrainer`) et `rapport.json` (celui de `forge evaluer-etape --etape 1.8
    --reference … --invites …` sur les invites de validation des paires). Rien n'y est modifié.

    Le relevé : `essai` (le nom du dossier), `reglages` (`taux_max`, `beta`, `normaliser_longueur`, `poids_sft`),
    `victoire` (`taux`, `victoires`, `egalites`, `defaites`, `n`, ou `{"absente": raison}`), `longueur` (`mots_modele`
    et `mots_reference`, en mots moyens) et `logps_choisie` (`debut` et `fin` : la moyenne du premier et du dernier
    dixième des pas, en log-probabilité moyenne par jeton de la réponse choisie).
    """
    if not dossiers:
        raise ValueError("Il faut au moins un dossier d'essai à résumer.")
    releves = []
    for dossier in map(Path, dossiers):
        refaire = f"Le dossier d'un essai doit avoir config.toml, journal.jsonl et rapport.json (voir `balayage`) : {dossier}."
        rapport = _lire_json(dossier / "rapport.json", "Le rapport", refaire)
        mesure = rapport.get("mesures", {}).get("victoire")
        if mesure is None:
            raise ValueError(f"Le rapport {dossier / 'rapport.json'} n'a pas de mesure « victoire » : lance `evaluer-etape --etape 1.8`.")
        if "absente" in mesure:
            victoire, longueur = {"absente": mesure["absente"]}, {"absente": mesure["absente"]}
        else:
            victoire = {cle: mesure[cle] for cle in ("taux", "victoires", "egalites", "defaites", "n")}
            longueur = {"mots_modele": mesure["mots_modele"], "mots_reference": mesure["mots_reference"]}
        valeurs = [
            float(ligne["logps_choisie"])
            for ligne in lire(dossier / "journal.jsonl")
            if "evenement" not in ligne
            and isinstance(ligne.get("logps_choisie"), int | float)
            and math.isfinite(ligne["logps_choisie"])
        ]
        if not valeurs:
            raise ValueError(f"Le journal {dossier / 'journal.jsonl'} n'a aucune ligne avec « logps_choisie » : ce n'est pas celui d'une DPO.")
        debut, fin = _moyenne_des_extremites(valeurs)
        releves.append(
            {
                "essai": dossier.name,
                "reglages": _reglages_de_l_essai(dossier / "config.toml"),
                "victoire": victoire,
                "longueur": longueur,
                "logps_choisie": {"debut": debut, "fin": fin},
            }
        )
    return releves
# fin: balayage
