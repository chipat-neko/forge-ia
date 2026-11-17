"""Les méthodes d'entraînement : ce qui change d'une méthode à l'autre, autour d'une seule boucle.

`forge entrainer` n'a qu'une boucle (`forge.entrainement.boucle`) : le planning du taux, la pause,
la reprise, le journal et les sauvegardes sont les mêmes pour tout le monde. Ce qui change d'une
méthode à l'autre tient dans une `Methode`, rangée par son nom dans le registre `METHODES` ; le
réglage `methode` de la configuration en choisit une. Ce module enregistre :

- `pre_entrainement` : prédire le jeton suivant de textes bruts (`jetons/`), à partir de poids
  tirés au hasard. C'est le code d'avant, inchangé : il passe toujours par
  `forge.entrainement.boucle.pas_d_optimisation` ;
- `sft` (affinage supervisé) : apprendre des conversations (`affinage/`) en partant d'une version
  publiée de ton IA. La perte ne porte que sur les jetons appris (les réponses de l'assistant).

La DPO et le GRPO s'y ajoutent avec `enregistrer_methode`.
"""

from collections.abc import Callable
from dataclasses import dataclass

import torch
import torch.nn.functional as F
from torch import nn

from forge.affinage.jeu import IGNORE, ChargeurAffinage, LotAffinage, lire_index
from forge.entrainement.chargeur import ChargeurJetons
from forge.erreurs import DonneesManquantes
from forge.evaluation.perte import autocast, perte_sur_morceaux
from forge.modele.modes import en_evaluation

# Nombre de morceaux (ou de rangées) de validation lus pour mesurer la perte de validation :
# toujours les mêmes, quel que soit `micro_lot` (moins si la validation en a moins).
MORCEAUX_DE_VALIDATION = 64


class PerteNonFinie(ArithmeticError):
    """La perte ou la norme des gradients n'est plus un nombre fini (infini ou « NaN »)."""


@dataclass(frozen=True)
class VersionDeDepart:
    """Ce qu'un affinage retient de sa version de départ : son nom, l'empreinte SHA-256 de ses
    poids et l'empreinte de son tokenizer (le SHA-1 de `forge.donnees.jetons.empreinte_du_tokenizer`)."""

    version: str
    empreinte_des_poids: str
    empreinte_du_tokenizer: str


@dataclass(frozen=True)
class Methode:
    """Une méthode d'entraînement : ses chargeurs, son pas d'optimisation et sa validation.

    C'est le contrat entre la boucle (`forge.entrainement.boucle`) et chaque méthode. La boucle
    appelle, dans cet ordre :

    1. `preparer(config, modele, appareil, noter, *, depart, reprise) -> dict` : ce dont la
       méthode a besoin en plus, son « contexte » (une référence précalculée, un générateur de
       problèmes…). Le modèle a alors les poids de départ : ceux de la version de départ (ou tirés
       de la graine pour le pré-entraînement), même quand l'entraînement reprend ; les poids de la
       sauvegarde et l'état du hasard ne sont rechargés qu'après. `depart` est la
       `VersionDeDepart` (`None` pour le pré-entraînement) ; `reprise` dit si l'entraînement repart
       d'une sauvegarde (vrai) ou de zéro (faux). `noter(ligne)` met une ligne de côté pour le
       journal (un dictionnaire, auquel la boucle ajoute `"pas"`) : elle y est écrite juste après
       la ligne de début, ou, si `preparer` lève une exception, avant que l'exception remonte ;
    2. `creer_chargeurs(config, contexte, noter) -> (train, val | None)` : les chargeurs
       d'entraînement et de validation. Ils sont créés APRÈS `preparer` : un fichier que `preparer`
       écrit ou remplace (le `reference.bin` de la DPO) n'est encore ouvert par personne. Sans
       validation, `val` vaut `None`, et la méthode dit pourquoi avec `noter`. Une donnée abîmée
       est une erreur, pas une absence de validation ;
    3. à chaque pas, `pas(modele, optimiseur, chargeur, config, taux_du_pas, appareil, contexte, *,
       numero) -> dict` : un pas d'optimisation. `numero` est le numéro du pas (1 au premier),
       qui continue après une reprise : une méthode qui tire au hasard en dérive sa graine. Il
       rend au moins `{"perte": …}`, plus ce qu'il veut écrire au journal. Si la perte ou la norme
       des gradients n'est plus finie, il lève `PerteNonFinie` AVANT de toucher aux poids ;
    4. de temps en temps, `valider(modele, chargeur_val, depart_val, appareil, config, contexte)
       -> dict` : la mesure de validation, qui relit toujours les mêmes données (le chargeur repart
       de `depart_val`) : `{"perte_val": …}`, ou `{"reussite_val": …}` quand
       `plus_grand_est_meilleur`.

    Le contexte n'est jamais sauvegardé : `preparer` doit le refaire à l'identique, à partir de la
    configuration, de la version de départ et des poids de départ. Seuls le modèle, l'optimiseur,
    l'état des chargeurs (`etat()`, `restaurer()`) et le hasard passent d'une session à l'autre.

    `plus_grand_est_meilleur` : `meilleur.pt` garde la plus grande mesure au lieu de la plus petite.
    """

    nom: str
    creer_chargeurs: Callable
    preparer: Callable
    pas: Callable
    valider: Callable
    plus_grand_est_meilleur: bool = False


METHODES: dict[str, Methode] = {}


def enregistrer_methode(m: Methode) -> None:
    """Ajoute `m` au registre, sous son nom ; un nom déjà pris est une `ValueError`."""
    if m.nom in METHODES:
        raise ValueError(f"La méthode {m.nom!r} est déjà enregistrée : choisis un autre nom.")
    METHODES[m.nom] = m


def sans_contexte(config, modele, appareil, noter, *, depart: VersionDeDepart | None, reprise: bool) -> dict:
    """`preparer` des méthodes qui n'ont besoin de rien de plus."""
    return {}


# --- Le pré-entraînement ------------------------------------------------------------------


def _chargeurs_pre_entrainement(config, contexte, noter) -> tuple[ChargeurJetons, ChargeurJetons | None]:
    """Les morceaux de `jetons/<donnees>/train` et `val` ; sans validation lisible, `None` (le
    journal dit pourquoi : `val/` absent du corpus, ou trop court pour un seul morceau)."""
    longueur = config.longueur_des_rangees
    chargeur = ChargeurJetons(config.dossier_donnees / "train", longueur, config.micro_lot, config.graine)
    try:
        validation = ChargeurJetons(config.dossier_donnees / "val", longueur, config.micro_lot, config.graine)
    except (DonneesManquantes, ValueError) as erreur:
        noter({"evenement": "validation", "message": f"Pas de perte de validation : {erreur}"})
        validation = None
    return chargeur, validation


def _pas_pre_entrainement(modele, optimiseur, chargeur, config, taux_du_pas, appareil, contexte, *, numero) -> dict:
    # La boucle importe ce module : on prend `pas_d_optimisation` chez elle au moment du pas (c'est
    # là que le chapitre 1.5, `forge mesurer` et les tests le trouvent).
    from forge.entrainement import boucle

    perte = boucle.pas_d_optimisation(
        modele, optimiseur, chargeur, config.accumulation, taux_du_pas, config.ecretage, appareil
    )
    return {"perte": perte}


def _valider_pre_entrainement(modele, chargeur_val, depart_val, appareil, config, contexte) -> dict:
    morceaux = min(MORCEAUX_DE_VALIDATION, chargeur_val.morceaux)
    return {"perte_val": perte_sur_morceaux(modele, chargeur_val, depart_val, morceaux, appareil)}


# --- L'affinage supervisé (SFT) -----------------------------------------------------------


def _chargeurs_sft(config, contexte, noter) -> tuple[ChargeurAffinage, ChargeurAffinage | None]:
    """Les rangées de `affinage/<donnees>`, après avoir vérifié la sorte et la longueur du jeu.

    Un jeu sans rangée de validation n'a pas de validation (le journal le dit) ; un fichier de
    validation abîmé est une erreur.
    """
    dossier = config.dossier_donnees
    index = lire_index(dossier)
    if index.get("sorte") != "sft":
        raise ValueError(
            f"Le jeu {dossier} est de sorte {index.get('sorte')!r} : methode = \"sft\" lit un jeu de sorte "
            "« sft ». Donne un jeu préparé pour le SFT, ou la méthode qui va avec ce jeu."
        )
    longueur = config.longueur_des_rangees
    if int(index["longueur"]) != longueur:
        raise ValueError(
            f"Le jeu {dossier} a des rangées de longueur {index['longueur']}, la configuration en attend "
            f"{longueur} (réglage longueur, par défaut le contexte du modèle). Mets longueur = "
            f"{index['longueur']} dans {config.fichier or 'la configuration'}, ou refais `forge preparer` "
            f"avec des rangées de {longueur}."
        )
    chargeur = ChargeurAffinage(dossier, "train", config.micro_lot, config.graine)
    if int(index["rangees"]["val"]) == 0:
        noter(
            {
                "evenement": "validation",
                "message": f"Pas de perte de validation : le jeu {dossier} n'a aucune rangée de validation.",
            }
        )
        return chargeur, None
    return chargeur, ChargeurAffinage(dossier, "val", config.micro_lot, config.graine)


def somme_des_pertes(logits: torch.Tensor, cibles: torch.Tensor) -> torch.Tensor:
    """La somme des pertes des jetons appris (cible différente de -100), calculée en float32."""
    return F.cross_entropy(
        logits.float().reshape(-1, logits.shape[-1]), cibles.reshape(-1), ignore_index=IGNORE, reduction="sum"
    )


def _logits(modele: nn.Module, lot: LotAffinage, appareil: torch.device) -> torch.Tensor:
    """Les logits d'un lot de rangées : chaque document de la rangée ne voit que lui-même."""
    with autocast(appareil):
        logits, _ = modele(lot.ids.to(appareil), documents=lot.documents.to(appareil))
    return logits


def pas_sft(
    modele: nn.Module,
    optimiseur: torch.optim.Optimizer,
    chargeur: ChargeurAffinage,
    config,
    taux_du_pas: float,
    appareil: torch.device,
    contexte: dict,
    *,
    numero: int,
) -> dict:
    """Un pas d'affinage supervisé : `accumulation` micro-lots, puis une mise à jour des poids.

    La perte du pas est la moyenne sur ses jetons appris, tous micro-lots compris : on lit
    d'abord les micro-lots et on compte leurs jetons appris `N`, puis chaque micro-lot fait
    `backward` de la somme des pertes de SES jetons appris divisée par `N`. Un micro-lot qui a
    beaucoup de jetons appris pèse donc plus qu'un micro-lot qui en a peu, comme si la carte
    avait tout traité d'un coup ; une moyenne de moyennes par micro-lot donnerait autant de poids
    à une réponse d'un mot qu'à une longue explication. Un micro-lot sans jeton appris (du
    bourrage) ajoute 0, jamais « 0 ÷ 0 ».

    `numero` (le numéro du pas) ne sert pas au SFT, qui ne tire rien au hasard.

    Rend `{"perte": …, "jetons_appris": N}`. Un pas sans aucun jeton appris est une `ValueError`
    (`forge preparer` écarte les exemples sans jeton appris : cela ne doit pas arriver). Une perte
    ou une norme des gradients non finie lève `PerteNonFinie` avant de toucher aux poids.
    """
    lots = [chargeur.lot() for _ in range(config.accumulation)]
    appris = sum(int((lot.cibles != IGNORE).sum()) for lot in lots)
    if appris == 0:
        raise ValueError(
            f"Aucun jeton appris dans les {len(lots)} micro-lots de ce pas : le jeu d'affinage "
            f"{config.dossier_donnees} est abîmé. Refais `forge preparer` pour ce jeu."
        )
    for groupe in optimiseur.param_groups:
        groupe["lr"] = taux_du_pas
    optimiseur.zero_grad(set_to_none=True)
    somme = torch.zeros((), device=appareil)
    for lot in lots:
        perte = somme_des_pertes(_logits(modele, lot, appareil), lot.cibles.to(appareil))
        (perte / appris).backward()
        somme += perte.detach()
    norme = torch.nn.utils.clip_grad_norm_(modele.parameters(), config.ecretage)
    moyenne = somme / appris
    if not torch.isfinite(torch.stack([moyenne, norme.to(moyenne.dtype)])).all():
        raise PerteNonFinie(f"perte {moyenne.item()}, norme des gradients {norme.item()}")
    optimiseur.step()
    return {"perte": moyenne.item(), "jetons_appris": appris}


@torch.no_grad()
def perte_sft_validation(
    modele: nn.Module, chargeur_val: ChargeurAffinage, depart: dict, n_rangees: int, appareil: torch.device
) -> float:
    """Perte moyenne par jeton appris sur les `n_rangees` premières rangées de validation.

    Le chargeur repart toujours de `depart` : ce sont toujours les mêmes rangées. On les lit par
    paquets de la taille du chargeur, le dernier coupé au besoin : le résultat ne dépend pas de
    la taille des paquets.
    """
    chargeur_val.restaurer(depart)
    with en_evaluation(modele):
        somme = torch.zeros((), device=appareil)
        appris = 0
        restantes = n_rangees
        while restantes > 0:
            lot = chargeur_val.lot()
            lot = LotAffinage(ids=lot.ids[:restantes], cibles=lot.cibles[:restantes], documents=lot.documents[:restantes])
            somme += somme_des_pertes(_logits(modele, lot, appareil), lot.cibles.to(appareil))
            appris += int((lot.cibles != IGNORE).sum())
            restantes -= lot.ids.shape[0]
    if appris == 0:
        raise ValueError(
            f"Aucun jeton appris dans les {n_rangees} premières rangées de validation de {chargeur_val.dossier}. "
            "Refais `forge preparer` pour ce jeu."
        )
    return (somme / appris).item()


def _valider_sft(modele, chargeur_val, depart_val, appareil, config, contexte) -> dict:
    rangees = min(MORCEAUX_DE_VALIDATION, chargeur_val.rangees)
    return {"perte_val": perte_sft_validation(modele, chargeur_val, depart_val, rangees, appareil)}


enregistrer_methode(
    Methode(
        nom="pre_entrainement",
        creer_chargeurs=_chargeurs_pre_entrainement,
        preparer=sans_contexte,
        pas=_pas_pre_entrainement,
        valider=_valider_pre_entrainement,
    )
)
enregistrer_methode(
    Methode(
        nom="sft",
        creer_chargeurs=_chargeurs_sft,
        preparer=sans_contexte,
        pas=pas_sft,
        valider=_valider_sft,
    )
)
