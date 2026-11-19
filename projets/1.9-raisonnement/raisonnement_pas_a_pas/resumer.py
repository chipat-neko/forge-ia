"""Résumer, sans rien recalculer, ce que le plan 7 mesure et construit pour ton IA 1.9.

- `resumer_etape(rapport)` lit le `rapport.json` de `python -m forge evaluer-etape` (voir `forge.evaluation.etape`)
  et en tire le relevé que le site lit, `mesures/etape-<version>.json` : `{version, etape, releve_le, mesures,
  echantillons}`. Les mesures sont celles du rapport, telles quelles (une mesure dont les données manquaient reste
  `{"absente": "<raison>"}`), sans `echantillons`, que le relevé range à part. Avec `reference=True`, c'est la
  version de référence du rapport qui est résumée ;
- `controle(sortie_grpo)` lit `controle.json`, le **contrôle de départ** que `forge entrainer` (méthode `grpo`) écrit
  dans sa sortie avant le premier pas : `mesures/controle-1.9.json`. Combien des réponses de ton IA sont justes
  avant tout apprentissage ? Sans aucune, il n'y a aucun signal : forge ne lance rien, écrit le contrôle (`lance` faux)
  et sort avec le code 6 ;
- `courbes_grpo(journal)` relève les courbes du journal du GRPO (la récompense moyenne, la part des groupes sans signal,
  la réussite sur la validation) : `mesures/entrainement-grpo-1.9.json`. Si le RL n'a pas été lancé, le relevé est
  `{"lance": false}`.
"""

import json
import math
from pathlib import Path

from forge.evaluation.etape import VERSION_DU_RAPPORT_D_ETAPE
from forge.raisonnement.grpo import NOM_DU_CONTROLE
from pre_entrainement.journal import lire, serie

CLES_DU_RAPPORT = ("version_du_rapport", "version", "etape", "date", "mesures")


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

    `version` est celle de la Release mesurée (« ton-ia-1.9 »), `etape` celle du chapitre (« 1.9 »),
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


# region: controle
CLES_DU_CONTROLE = ("invites", "reponses", "justes", "taux", "lance")


def controle(sortie_grpo: Path) -> dict:
    """Le contrôle de départ d'un GRPO : `{depart, invites, reponses, justes, taux, lance, secondes}`.

    `sortie_grpo` est le dossier de sortie de `forge entrainer` (méthode `grpo`), où forge écrit `controle.json` avant
    le premier pas : `invites` problèmes, `reponses` tirages au total, `justes` réponses justes, `taux` leur part,
    `lance` vrai s'il y en a au moins une, `depart` la version de départ et `secondes` la durée du contrôle (les deux
    dernières clés sont celles que forge ajoute ; elles manquent d'un contrôle écrit par une version plus ancienne, et
    ne sont alors pas rendues). Rien n'est recalculé. Un contrôle sans aucune réponse juste (`lance` faux) est un
    résultat, pas une erreur : c'est ce que le chapitre montre quand ton IA ne sait pas encore résoudre les problèmes.
    """
    refaire = "Lance `python -m forge entrainer` (méthode grpo) : le contrôle de départ est son premier travail."
    chemin = Path(sortie_grpo) / NOM_DU_CONTROLE
    donnees = _lire_json(chemin, "Le contrôle de départ", refaire)
    for cle in CLES_DU_CONTROLE:
        if cle not in donnees:
            raise ValueError(f"Le contrôle {chemin} n'a pas de « {cle} ». {refaire}")
    for cle in ("invites", "reponses", "justes"):
        if isinstance(donnees[cle], bool) or not isinstance(donnees[cle], int) or donnees[cle] < 0:
            raise ValueError(f"Dans {chemin}, « {cle} » vaut {donnees[cle]!r} : il faut un nombre entier positif ou nul. {refaire}")
    if donnees["reponses"] < 1 or donnees["justes"] > donnees["reponses"]:
        raise ValueError(f"Dans {chemin}, {donnees['justes']} réponses justes sur {donnees['reponses']} : ce n'est pas possible. {refaire}")
    if not isinstance(donnees["lance"], bool) or donnees["lance"] != (donnees["justes"] > 0):
        raise ValueError(f"Dans {chemin}, « lance » vaut {donnees['lance']!r} pour {donnees['justes']} réponses justes : il doit être vrai s'il y en a au moins une. {refaire}")
    taux = donnees["taux"]
    if isinstance(taux, bool) or not isinstance(taux, int | float) or not math.isclose(taux, donnees["justes"] / donnees["reponses"], abs_tol=1e-9):
        raise ValueError(f"Dans {chemin}, « taux » vaut {taux!r}, pas justes / reponses. {refaire}")
    releve = {cle: donnees[cle] for cle in ("depart", *CLES_DU_CONTROLE, "secondes") if cle in donnees}
    return releve
# fin: controle


# region: courbes
CLES_DES_COURBES = ("recompense_moyenne", "groupes_sans_signal")


def courbes_grpo(journal: Path, points: int = 600, pas_total: int | None = None) -> dict:
    """`{recompense_moyenne, groupes_sans_signal, reussite_val}` : des listes de `[pas, valeur]` ; ou `{"lance": false}`.

    `forge entrainer` (méthode `grpo`) écrit à chaque pas `recompense_moyenne` (la part des réponses justes) et
    `groupes_sans_signal` (la part des problèmes dont toutes les réponses ont la même récompense : ils n'apprennent
    rien), et, tous les `evaluation_tous_pas` pas, `reussite_val` (la part des problèmes de validation que ton IA
    réussit en glouton). Les deux premières sont réduites en paquets de pas par `pre_entrainement.journal.serie`,
    avec le découpage du site ; un paquet sans aucune valeur finie (un RL qui diverge) reste `None`, et le site le
    montre comme absent. `reussite_val` garde chaque mesure à son pas, sans lissage.

    Un journal sans aucun pas de GRPO (le contrôle de départ n'a trouvé aucune réponse juste : le RL n'a pas été lancé)
    rend `{"lance": False}`. Lève `FileNotFoundError` si le journal n'existe pas ou est vide.
    """
    journal = Path(journal)
    lignes = lire(journal)
    if not lignes:
        raise FileNotFoundError(
            f"Le journal {journal} n'existe pas ou est vide. Donne le journal.jsonl d'un entraînement `grpo` de forge."
        )
    pas = [ligne for ligne in lignes if "evenement" not in ligne and isinstance(ligne.get("pas"), int) and "recompense_moyenne" in ligne]
    if not pas:
        return {"lance": False}
    courbes: dict = {cle: serie(lignes, cle, points, pas_total) for cle in CLES_DES_COURBES}
    par_pas = {
        ligne["pas"]: float(ligne["reussite_val"])
        for ligne in pas
        if isinstance(ligne.get("reussite_val"), int | float) and not isinstance(ligne.get("reussite_val"), bool) and math.isfinite(ligne["reussite_val"])
    }  # un pas refait : sa dernière valeur
    courbes["reussite_val"] = [[numero, par_pas[numero]] for numero in sorted(par_pas)]
    return courbes
# fin: courbes
