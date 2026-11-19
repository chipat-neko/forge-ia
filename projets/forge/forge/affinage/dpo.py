"""La DPO (« Direct Preference Optimization ») : apprendre d'une paire de réponses, la choisie et la rejetée.

Pour chaque paire d'un jeu `dpo` (écrit par `forge preferences` : la rangée de la réponse choisie, puis
celle de la rejetée), deux modèles donnent la log-probabilité de chaque réponse, la somme des
log-probabilités de ses jetons appris (`logps_des_rangees`) :

- la **politique**, le modèle qu'on entraîne : `pc` pour la choisie, `pr` pour la rejetée ;
- la **référence**, la version de départ, qui ne bouge pas : `qc` et `qr`.

La DPO pousse la politique à gagner davantage sur la choisie que sur la rejetée, par rapport à la
référence (`perte_dpo`) :

    z = β ((pc − qc) − (pr − qr))
    perte = moyenne(−log σ(z)) + poids_sft × moyenne(−pc / lc)

`lc` est le nombre de jetons appris de la choisie : le second terme est la perte SFT par jeton de la
réponse choisie. Sans lui, la DPO peut écarter les deux réponses en les rendant toutes deux moins
probables. Avec `normaliser_longueur`, les gains sont comparés par jeton : z = β ((pc − qc)/lc − (pr − qr)/lr).

La référence ne change pas pendant l'entraînement : ses log-probabilités sont calculées une seule fois,
avant le premier pas, avec le modèle de départ (`preparer_reference`), puis rangées dans le jeu, à côté
des rangées de chaque partie :

- `reference.bin` : `float64`, une valeur par rangée, dans l'ordre du fichier ; le chargeur les rend
  avec chaque lot (`LotAffinage.reference`) ;
- `reference.json` : la version de départ qui les a calculées (son nom et l'empreinte SHA-256 de ses
  poids), le nombre de rangées et l'appareil.

Une autre version de départ les fait recalculer ; la même les fait relire, même depuis un autre
entraînement ou à la reprise. `forge preparer` et `forge preferences` les effacent quand ils réécrivent
le jeu. Le calcul affiche son avancement au plus toutes les `SECONDES_ENTRE_PROGRES` secondes ; un
Ctrl+C l'arrête sans rien écrire (la méthode `dpo` en fait une pause, voir `forge.entrainement.methodes`).
"""

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import torch
import torch.nn.functional as F
from torch import nn

from forge.affinage.jeu import IGNORE, PARTIES, ChargeurAffinage, LotAffinage, lire_index
from forge.chemins import verifier_place
from forge.donnees.telechargement import MARGE_PLACE
from forge.evaluation.perte import autocast
from forge.fichiers import ESPACE_FINE, duree, ecrire_atomique, ecrire_texte, entier, nombre
from forge.modele.modes import en_evaluation

if TYPE_CHECKING:  # importés pour les annotations seulement : la boucle importe ce module
    from forge.entrainement.boucle import ReglagesDPO
    from forge.entrainement.methodes import VersionDeDepart

_FINE = ESPACE_FINE

# Une ligne d'avancement du calcul de la référence au plus toutes les 30 secondes.
SECONDES_ENTRE_PROGRES = 30


# --- Les log-probabilités et la perte ------------------------------------------------------


def logps_des_rangees(modele: nn.Module, lot: LotAffinage, appareil: torch.device) -> tuple[torch.Tensor, torch.Tensor]:
    """Par rangée : la somme des log-probabilités des jetons appris (float32), et leur nombre.

    Le modèle calcule sous `autocast` (bf16 sur la carte graphique) ; les log-probabilités, elles, sont
    tirées des logits en float32. Une rangée sans jeton appris donne 0 et 0.
    """
    with autocast(appareil):
        logits, _ = modele(lot.ids.to(appareil), documents=lot.documents.to(appareil))
    cibles = lot.cibles.to(appareil)
    pertes = F.cross_entropy(
        logits.float().reshape(-1, logits.shape[-1]), cibles.reshape(-1), ignore_index=IGNORE, reduction="none"
    )
    return -pertes.reshape(cibles.shape).sum(dim=1), (cibles != IGNORE).sum(dim=1)


def perte_dpo(
    pc: torch.Tensor,
    pr: torch.Tensor,
    qc: torch.Tensor,
    qr: torch.Tensor,
    lc: torch.Tensor,
    lr: torch.Tensor,
    reglages: "ReglagesDPO",
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    """La perte de la DPO, et ses mesures ; un élément par paire dans chaque tenseur.

    `pc`, `pr` : les log-probabilités de la politique pour la choisie et la rejetée ; `qc`, `qr` : celles
    de la référence ; `lc`, `lr` : leurs nombres de jetons appris. `−log σ(z)` est calculé par
    `softplus(−z)`, qui reste exact quand z est très négatif.

    Les mesures sont des tenseurs à une valeur, détachés (la boucle les convertit en nombres une fois
    par pas, sans attendre la carte graphique à chaque micro-lot) :

    - `logps_choisie`, `logps_rejetee` : la log-probabilité moyenne par jeton de chaque réponse ;
    - `recompense_choisie`, `recompense_rejetee` : la moyenne de β (pc − qc) et de β (pr − qr), ce que
      la politique a gagné sur chaque réponse depuis la référence ;
    - `marge` : leur différence ;
    - `exactitude` : la part des paires où z > 0, celles que la politique classe déjà dans le bon ordre.
    """
    beta = reglages.beta
    gain_choisie, gain_rejetee = pc - qc, pr - qr
    if reglages.normaliser_longueur:
        z = beta * (gain_choisie / lc - gain_rejetee / lr)
    else:
        z = beta * (gain_choisie - gain_rejetee)
    perte = F.softplus(-z).mean() + reglages.poids_sft * (-pc / lc).mean()
    with torch.no_grad():
        recompense_choisie = (beta * gain_choisie).mean()
        recompense_rejetee = (beta * gain_rejetee).mean()
        mesures = {
            "logps_choisie": (pc / lc).mean(),
            "logps_rejetee": (pr / lr).mean(),
            "recompense_choisie": recompense_choisie,
            "recompense_rejetee": recompense_rejetee,
            "marge": recompense_choisie - recompense_rejetee,
            "exactitude": (z > 0).to(z.dtype).mean(),
        }
    return perte, mesures


def verifier_les_paires(lot: LotAffinage, dossier: Path) -> None:
    """Chaque rangée d'un lot de paires a au moins un jeton appris (lu sur le processeur, sans attendre la carte).

    Sinon, sa log-probabilité moyenne par jeton serait 0 ÷ 0 : c'est un jeu abîmé, pas une perte infinie.
    """
    appris = (lot.cibles != IGNORE).sum(dim=1)
    if bool((appris == 0).any()):
        raise ValueError(
            f"Une réponse d'une paire du jeu {dossier} n'a aucun jeton appris : chaque réponse en a au moins un "
            "(son texte, ou son <|fin_tour|>). Le jeu est abîmé : refais `forge preferences` pour ce jeu."
        )


# --- La référence ---------------------------------------------------------------------------


def calculer_reference(
    modele: nn.Module,
    dossier: Path,
    partie: str,
    taille_lot: int,
    appareil: torch.device,
    avancer: Callable[[int], None] | None = None,
) -> np.ndarray:
    """Les log-probabilités de toutes les rangées de `partie` selon `modele`, dans l'ordre du fichier.

    Le modèle calcule en mode évaluation, sous `autocast`, par paquets de `taille_lot` rangées ;
    `avancer(n)` est appelé après chaque paquet de `n` rangées.
    """
    chargeur = ChargeurAffinage(dossier, partie, taille_lot, graine=0)
    valeurs = np.empty(chargeur.rangees, dtype=np.float64)
    with torch.no_grad(), en_evaluation(modele):
        for debut in range(0, chargeur.rangees, taille_lot):
            fin = min(debut + taille_lot, chargeur.rangees)
            lot = chargeur.lot_des_rangees(debut, fin)
            verifier_les_paires(lot, dossier)
            logps, _ = logps_des_rangees(modele, lot, appareil)
            valeurs[debut:fin] = logps.double().cpu().numpy()
            if avancer is not None:
                avancer(fin - debut)
    return valeurs


def _reference_a_jour(dossier_partie: Path, depart: "VersionDeDepart", rangees: int) -> bool:
    """`reference.bin` est-il celui de cette version de départ, complet ?"""
    try:
        description = json.loads((dossier_partie / "reference.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return False
    fichier = dossier_partie / "reference.bin"
    return (
        isinstance(description, dict)
        and description.get("version") == depart.version
        and description.get("empreinte_des_poids") == depart.empreinte_des_poids
        and fichier.is_file()
        and fichier.stat().st_size == rangees * np.dtype("<f8").itemsize
    )


def preparer_reference(
    dossier: Path,
    modele: nn.Module,
    appareil: torch.device,
    depart: "VersionDeDepart",
    taille_lot: int,
    noter: Callable[[dict], None],
) -> None:
    """Calcule la référence du jeu `dossier` avec `modele` (la version de départ `depart`), ou la relit.

    Une partie (`train`, `val`) est recalculée si son `reference.bin` manque, n'a pas une valeur par
    rangée, ou si son `reference.json` manque ou nomme une autre version de départ (nom et empreinte des
    poids). La description est effacée avant le calcul et écrite après les valeurs, chacune d'un coup :
    un calcul interrompu (Ctrl+C compris) ne laisse ni fichier à moitié écrit, ni description juste sur
    des valeurs fausses. Pendant le calcul, une ligne à l'écran au plus toutes les
    `SECONDES_ENTRE_PROGRES` secondes donne les rangées faites, le débit et le temps restant. Une ligne au
    journal (`noter`) dit si la référence a été calculée (et en combien de temps) ou relue.
    """
    index = lire_index(dossier)
    rangees = {partie: int(index["rangees"][partie]) for partie in PARTIES if int(index["rangees"][partie]) > 0}
    a_calculer = [partie for partie, n in rangees.items() if not _reference_a_jour(dossier / partie, depart, n)]
    version = f"{depart.version} (poids {depart.empreinte_des_poids[:12]}…)"
    if not a_calculer:
        message = f"Référence de la DPO relue{_FINE}: calculée avec {version}, dans {dossier}."
        noter({"evenement": "reference", "message": message})
        return
    combien = ", ".join(f"{entier(rangees[partie], milliers=_FINE)} rangées de {partie}" for partie in a_calculer)
    print(f"Référence de la DPO{_FINE}: calcul des log-probabilités de {combien} avec {version}…", flush=True)
    total = sum(rangees[partie] for partie in a_calculer)
    faites = 0
    debut = dernier_affichage = time.perf_counter()

    def avancer(n: int) -> None:
        """Compte `n` rangées de plus ; au plus toutes les `SECONDES_ENTRE_PROGRES` secondes, une ligne d'avancement."""
        nonlocal faites, dernier_affichage
        faites += n
        maintenant = time.perf_counter()
        if faites >= total or maintenant - dernier_affichage < SECONDES_ENTRE_PROGRES:
            return
        dernier_affichage = maintenant
        debit = faites / max(maintenant - debut, 1e-9)
        print(
            f"Référence de la DPO{_FINE}: {entier(faites, milliers=_FINE)} rangées sur {entier(total, milliers=_FINE)} "
            f"({nombre(100 * faites / total, 1)}{_FINE}%) · {nombre(debit, 1, milliers=_FINE)} rangées/s · "
            f"reste ≈ {duree((total - faites) / debit)}",
            flush=True,
        )

    for partie in a_calculer:
        dossier_partie = dossier / partie
        for ancien in ("reference.json", "reference.bin"):  # la description d'abord
            (dossier_partie / ancien).unlink(missing_ok=True)
        valeurs = calculer_reference(modele, dossier, partie, taille_lot, appareil, avancer).astype("<f8")
        verifier_place(valeurs.nbytes + MARGE_PLACE, dossier_partie)
        ecrire_atomique(dossier_partie / "reference.bin", lambda fichier: fichier.write(valeurs.tobytes()))
        description = {
            "version": depart.version,
            "empreinte_des_poids": depart.empreinte_des_poids,
            "rangees": rangees[partie],
            "appareil": appareil.type,
        }
        ecrire_texte(dossier_partie / "reference.json", json.dumps(description, indent=2, ensure_ascii=False) + "\n")
    temps = duree(time.perf_counter() - debut)
    print(f"Référence de la DPO{_FINE}: {entier(total, milliers=_FINE)} rangées en {temps}.", flush=True)
    message = f"Référence de la DPO calculée avec {version} en {temps}{_FINE}: {combien}, dans {dossier}."
    noter({"evenement": "reference", "message": message})
