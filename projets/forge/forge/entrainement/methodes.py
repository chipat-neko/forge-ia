"""Les méthodes d'entraînement : ce qui change d'une méthode à l'autre, autour d'une seule boucle.

`forge entrainer` n'a qu'une boucle (`forge.entrainement.boucle`) : le planning du taux, la pause,
la reprise, le journal et les sauvegardes sont les mêmes pour tout le monde. Ce qui change d'une
méthode à l'autre tient dans une `Methode`, rangée par son nom dans le registre `METHODES` ; le
réglage `methode` de la configuration en choisit une. Ce module enregistre :

- `pre_entrainement` : prédire le jeton suivant de textes bruts (`jetons/`), à partir de poids
  tirés au hasard. C'est le code d'avant, inchangé : il passe toujours par
  `forge.entrainement.boucle.pas_d_optimisation` ;
- `sft` (affinage supervisé) : apprendre des conversations (`affinage/`) en partant d'une version
  publiée de ton IA. La perte ne porte que sur les jetons appris (les réponses de l'assistant) ;
- `dpo` : apprendre des paires de préférences (`affinage/`, jeu de sorte `dpo`), elle aussi depuis
  une version publiée, qui sert de référence (`forge.affinage.dpo`) ;
- `grpo` : apprendre par renforcement à résoudre des problèmes générés (`problemes/`), à partir de
  ses propres réponses, récompensées si elles sont justes (`forge.raisonnement.grpo`). Il ne part
  que si son contrôle de départ trouve au moins une réponse juste.
"""

import contextlib
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass

import torch
import torch.nn.functional as F
from torch import nn

# Les modules, pas leurs noms : « import forge.affinage.dpo » (ou « forge.raisonnement.grpo ») en premier
# passe par forge.evaluation, qui importe forge.entrainement, donc ce fichier, avant que dpo.py (ou grpo.py)
# ait fini (import circulaire). Leurs noms ne sont donc lus qu'à l'appel, jamais à l'import.
from forge.affinage import dpo
from forge.affinage.jeu import IGNORE, ChargeurAffinage, LotAffinage, lire_index
from forge.entrainement.chargeur import ChargeurJetons
from forge.erreurs import DonneesManquantes
from forge.evaluation.perte import autocast, perte_sur_morceaux
from forge.fichiers import ESPACE_FINE, entier
from forge.modele.modes import en_evaluation
from forge.raisonnement import grpo

_FINE = ESPACE_FINE

# Nombre de morceaux (ou de rangées) de validation lus pour mesurer la perte de validation :
# toujours les mêmes, quel que soit `micro_lot` (moins si la validation en a moins).
MORCEAUX_DE_VALIDATION = 64

# Nombre de paires de validation lues par la DPO (moins si la validation en a moins).
PAIRES_DE_VALIDATION = 256


class PerteNonFinie(ArithmeticError):
    """La perte ou la norme des gradients n'est plus un nombre fini (infini ou « NaN »)."""


class PreparationInterrompue(Exception):
    """Ctrl+C pendant `preparer` (le calcul de la référence de la DPO, le contrôle de départ du GRPO) :
    rien n'est sauvegardé.

    Son message dit ce qui est perdu et ce que fera la reprise ; la boucle y ajoute la commande de reprise.
    """


class RecompenseNulle(Exception):
    """Le contrôle de départ du GRPO n'a trouvé aucune réponse juste : le RL n'aurait aucun signal.

    `preparer` la lève après avoir noté la ligne `recompense_nulle` et écrit `controle.json` ; la boucle écrit
    la note au journal, affiche le message et s'arrête avec `CODE_RECOMPENSE_NULLE`, sans rien sauvegarder.
    """


class GenerationSansMemoire(torch.cuda.OutOfMemoryError):
    """La carte graphique manque de mémoire pendant une génération du GRPO (tirages, contrôle, validation).

    C'est un manque de mémoire comme un autre (la boucle l'attrape avec eux), mais son remède est de réduire
    `lot_de_generation` dans `[grpo]`, pas `micro_lot`.
    """


@contextlib.contextmanager
def _en_generant() -> Iterator[None]:
    """Le temps d'une génération du GRPO, un manque de mémoire de la carte devient `GenerationSansMemoire`."""
    try:
        yield
    except torch.cuda.OutOfMemoryError as erreur:
        raise GenerationSansMemoire(str(erreur)) from None


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
       la ligne de début, ou, si `preparer` lève une exception, avant que l'exception remonte. Une
       méthode dont la préparation est longue fait d'un Ctrl+C une `PreparationInterrompue` : la boucle
       écrit alors ses notes et une ligne « pause » au journal, affiche le message et la commande de
       reprise, et s'arrête sans rien sauvegarder. Le GRPO sans signal lève `RecompenseNulle` : la
       boucle écrit ses notes, affiche le message et s'arrête avec le code `CODE_RECOMPENSE_NULLE` ;
    2. `creer_chargeurs(config, contexte, noter) -> (train, val | None)` : les chargeurs
       d'entraînement et de validation. Ils sont créés APRÈS `preparer` : un fichier que `preparer`
       écrit ou remplace (le `reference.bin` de la DPO) n'est encore ouvert par personne. Sans
       validation, `val` vaut `None`, et la méthode dit pourquoi avec `noter`. Une donnée abîmée
       est une erreur, pas une absence de validation ;
    3. à chaque pas, `pas(modele, optimiseur, chargeur, config, taux_du_pas, appareil, contexte, *,
       numero) -> dict` : un pas d'optimisation. `numero` est le numéro du pas (1 au premier),
       qui continue après une reprise : une méthode qui tire au hasard en dérive sa graine (le GRPO). Il
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


def _verifier_le_jeu(config, sorte: str) -> dict:
    """Le jeu `affinage/<donnees>` est complet, de sorte `sorte`, et ses rangées ont la longueur
    attendue ; rend son index."""
    dossier = config.dossier_donnees
    index = lire_index(dossier)
    if index.get("sorte") != sorte:
        raise ValueError(
            f"Le jeu {dossier} est de sorte {index.get('sorte')!r} : methode = \"{sorte}\" lit un jeu de sorte "
            f"« {sorte} ». Donne un jeu préparé pour cette méthode, ou la méthode qui va avec ce jeu."
        )
    longueur = config.longueur_des_rangees
    if int(index["longueur"]) != longueur:
        raise ValueError(
            f"Le jeu {dossier} a des rangées de longueur {index['longueur']}, la configuration en attend "
            f"{longueur} (réglage longueur, par défaut le contexte du modèle). Mets longueur = "
            f"{index['longueur']} dans {config.fichier or 'la configuration'}, ou refais `forge preparer` "
            f"avec des rangées de {longueur}."
        )
    return index


def _chargeurs_d_affinage(config, noter, sorte: str) -> tuple[ChargeurAffinage, ChargeurAffinage | None]:
    """Les rangées de `affinage/<donnees>`, après avoir vérifié la sorte et la longueur du jeu.

    Un jeu sans rangée de validation n'a pas de validation (le journal le dit) ; un fichier de
    validation abîmé est une erreur.
    """
    index = _verifier_le_jeu(config, sorte)
    dossier = config.dossier_donnees
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


def _chargeurs_sft(config, contexte, noter) -> tuple[ChargeurAffinage, ChargeurAffinage | None]:
    return _chargeurs_d_affinage(config, noter, "sft")


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


# --- La DPO (préférences) ------------------------------------------------------------------


def _preparer_dpo(config, modele, appareil, noter, *, depart: VersionDeDepart | None, reprise: bool) -> dict:
    """Vérifie le jeu, puis calcule (ou relit) la référence avec le modèle de départ, avant tout pas.

    Un Ctrl+C pendant le calcul est une pause : rien n'est écrit à moitié (`preparer_reference` écrit
    chaque fichier d'un coup), et la reprise refait le calcul.
    """
    _verifier_le_jeu(config, "dpo")
    try:
        dpo.preparer_reference(config.dossier_donnees, modele, appareil, depart, config.micro_lot, noter)
    except KeyboardInterrupt:
        raise PreparationInterrompue(
            f"Pause pendant le calcul de la référence{_FINE}: rien n'est sauvegardé, la référence sera "
            "recalculée à la reprise."
        ) from None
    return {}


def _chargeurs_dpo(config, contexte, noter) -> tuple[ChargeurAffinage, ChargeurAffinage | None]:
    return _chargeurs_d_affinage(config, noter, "dpo")


def _termes_des_paires(modele: nn.Module, lot: LotAffinage, appareil: torch.device, dossier) -> list[torch.Tensor]:
    """`pc, pr, qc, qr, lc, lr` d'un lot de paires (rangée choisie, rangée rejetée, à la suite) : les
    log-probabilités de la politique, celles de la référence (lues avec le lot) et les jetons appris."""
    if lot.reference is None:
        raise ValueError(
            f"Le jeu {dossier} n'a pas de référence (reference.bin) : relance la même commande, la DPO la "
            "calcule avant le premier pas."
        )
    dpo.verifier_les_paires(lot, dossier)
    logps, appris = dpo.logps_des_rangees(modele, lot, appareil)
    reference = lot.reference.to(appareil)
    return [logps[0::2], logps[1::2], reference[0::2], reference[1::2], appris[0::2], appris[1::2]]


def pas_dpo(
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
    """Un pas de DPO : `accumulation` micro-lots de paires, puis une mise à jour des poids.

    La perte du pas est la moyenne sur toutes ses paires, tous micro-lots compris (comme le SFT, qui
    moyenne sur tous ses jetons appris) : chaque micro-lot fait `backward` de la perte de ses paires,
    pesée par sa part des paires du pas. Les mesures (`perte_dpo`) sont calculées une fois, sur toutes
    les paires du pas.

    `numero` (le numéro du pas) ne sert pas à la DPO, qui ne tire rien au hasard.

    Rend `{"perte": …}` et les six mesures (`logps_choisie`, `logps_rejetee`, `recompense_choisie`,
    `recompense_rejetee`, `marge`, `exactitude`). Une réponse sans jeton appris est une `ValueError` (le
    jeu est abîmé) ; une perte ou une norme des gradients non finie lève `PerteNonFinie` avant de
    toucher aux poids.
    """
    lots = [chargeur.lot() for _ in range(config.accumulation)]
    paires = sum(lot.ids.shape[0] // 2 for lot in lots)
    for groupe in optimiseur.param_groups:
        groupe["lr"] = taux_du_pas
    optimiseur.zero_grad(set_to_none=True)
    termes = []
    for lot in lots:
        termes_du_lot = _termes_des_paires(modele, lot, appareil, config.dossier_donnees)
        perte, _ = dpo.perte_dpo(*termes_du_lot, config.dpo)
        (perte * (termes_du_lot[0].shape[0] / paires)).backward()
        termes.append([terme.detach() for terme in termes_du_lot])
    norme = torch.nn.utils.clip_grad_norm_(modele.parameters(), config.ecretage)
    perte, mesures = dpo.perte_dpo(*(torch.cat(colonne) for colonne in zip(*termes)), config.dpo)
    if not torch.isfinite(torch.stack([perte, norme.to(perte.dtype)])).all():
        raise PerteNonFinie(f"perte {perte.item()}, norme des gradients {norme.item()}")
    optimiseur.step()
    return {"perte": perte.item(), **{nom: valeur.item() for nom, valeur in mesures.items()}}


@torch.no_grad()
def mesures_dpo_validation(
    modele: nn.Module, chargeur_val: ChargeurAffinage, depart: dict, n_paires: int, appareil: torch.device, reglages
) -> dict:
    """La perte de la DPO et l'exactitude sur les `n_paires` premières paires de validation.

    Le chargeur repart toujours de `depart` : ce sont toujours les mêmes paires. On les lit par paquets
    de la taille du chargeur, le dernier coupé au besoin : le résultat ne dépend pas de la taille des
    paquets. Rend `{"perte_val": …, "exactitude_val": …}`.
    """
    chargeur_val.restaurer(depart)
    termes = []
    with en_evaluation(modele):
        restantes = 2 * n_paires
        while restantes > 0:
            lot = chargeur_val.lot()
            if lot.ids.shape[0] > restantes:
                lot = LotAffinage(
                    ids=lot.ids[:restantes],
                    cibles=lot.cibles[:restantes],
                    documents=lot.documents[:restantes],
                    reference=None if lot.reference is None else lot.reference[:restantes],
                )
            termes.append(_termes_des_paires(modele, lot, appareil, chargeur_val.dossier))
            restantes -= lot.ids.shape[0]
    perte, mesures = dpo.perte_dpo(*(torch.cat(colonne) for colonne in zip(*termes)), reglages)
    return {"perte_val": perte.item(), "exactitude_val": mesures["exactitude"].item()}


def _valider_dpo(modele, chargeur_val, depart_val, appareil, config, contexte) -> dict:
    paires = min(PAIRES_DE_VALIDATION, chargeur_val.unites)
    return mesures_dpo_validation(modele, chargeur_val, depart_val, paires, appareil, config.dpo)


# --- Le GRPO (apprentissage par renforcement) ----------------------------------------------


def _preparer_grpo(config, modele, appareil, noter, *, depart: VersionDeDepart | None, reprise: bool) -> dict:
    """Lit le tokenizer de la version de départ, vérifie les problèmes, prépare la validation ; puis, pour un
    entraînement neuf, le contrôle de départ.

    Le contrôle tire `controle_reponses` réponses à chacun des `controle_invites` premiers problèmes du dossier,
    avec les poids de départ. Son résultat va dans `controle.json` (écrit d'un coup, à la fin : un ancien est
    effacé avant) et au journal. Sans aucune réponse juste, `RecompenseNulle` : rien n'est lancé. Ctrl+C pendant le
    contrôle est une pause (`PreparationInterrompue`) ; la reprise refait le contrôle. Une reprise depuis une
    sauvegarde ne le refait pas.
    """
    reglages = config.grpo
    tok = grpo.tokenizer_du_depart(config.dossier_depart)
    problemes = grpo.lire_problemes(config.dossier_donnees)
    contexte = {
        "tokenizer": tok,
        "validation": grpo.problemes_de_validation(config.dossier_donnees, reglages.evaluation_invites),
    }
    if reprise:
        return contexte
    chemin = config.dossier_sortie / grpo.NOM_DU_CONTROLE
    chemin.unlink(missing_ok=True)  # celui d'un essai précédent ne doit pas passer pour celui-ci
    try:
        with _en_generant():
            controle = grpo.controle_de_depart(
                modele, tok, problemes[: reglages.controle_invites], reglages, grpo.graine_du_pas(config.graine, 0),
                depart.version,
            )
    except KeyboardInterrupt:
        raise PreparationInterrompue(
            f"Pause pendant le contrôle de départ{_FINE}: rien n'est sauvegardé, le contrôle sera refait à la reprise."
        ) from None
    controle = {**controle, "depart": depart.version}
    grpo.ecrire_controle(chemin, controle)
    if not controle["lance"]:
        noter({"evenement": "recompense_nulle", "controle": controle})
        raise RecompenseNulle(
            f"Aucune des {entier(controle['reponses'], milliers=_FINE)} réponses n'est juste{_FINE}: le RL n'aurait "
            f"aucun signal. Rien n'est lancé. Le contrôle est dans {chemin}. Le RL n'amplifie qu'un comportement déjà "
            f"présent{_FINE}: ton IA doit d'abord réussir quelques problèmes (un SFT de raisonnement, ou des problèmes "
            "plus faciles), puis relance la même commande."
        )
    noter({"evenement": "controle", "controle": controle})
    return contexte


def _chargeurs_grpo(config, contexte, noter) -> tuple["grpo.ChargeurInvites", "grpo.ValidationRL"]:
    return grpo.ChargeurInvites(config.dossier_donnees, config.grpo.invites_par_pas, config.graine), contexte["validation"]


def pas_grpo(
    modele: nn.Module,
    optimiseur: torch.optim.Optimizer,
    chargeur: "grpo.ChargeurInvites",
    config,
    taux_du_pas: float,
    appareil: torch.device,
    contexte: dict,
    *,
    numero: int,
) -> dict:
    """Un pas de GRPO à la nanochat : tirer, récompenser, apprendre, une mise à jour des poids.

    1. génération (modèle en évaluation, sans gradient) : `reponses_par_invite` réponses à chacun des
       `invites_par_pas` problèmes du lot, d'un seul `generer_lot`, graine `graine_du_pas(config.graine, numero)` ;
    2. récompense 1 si la réponse est juste, sinon 0 ; avantage `r − moyenne(r)` par problème ;
    3. apprentissage, `micro_lot` réponses à la fois : perte −Σ A · log π(jeton) sur les jetons générés, divisée par
       le nombre de jetons générés du pas. Ni KL, ni ratio, ni écrêtage PPO : les réponses viennent du modèle même
       qu'on entraîne, juste avant (« sur la politique »).

    Rend `{"perte": …}` et `recompense_moyenne`, `groupes_sans_signal` (la part des problèmes dont toutes les
    réponses ont la même récompense : ils n'apprennent rien), `longueur_moyenne` (jetons générés par réponse),
    `secondes_generation` et `secondes_apprentissage`. Un pas sans aucun signal ne calcule aucun gradient et ne
    bouge pas les poids. Une perte ou une norme des gradients non finie lève `PerteNonFinie` avant de toucher aux poids.
    """
    reglages = config.grpo
    debut = time.perf_counter()
    with _en_generant():
        tirage = grpo.tirer(
            modele, contexte["tokenizer"], chargeur.lot(), reglages.reponses_par_invite,
            grpo.graine_du_pas(config.graine, numero), reglages,
        )
    secondes_generation = time.perf_counter() - debut
    debut = time.perf_counter()
    for groupe in optimiseur.param_groups:
        groupe["lr"] = taux_du_pas
    optimiseur.zero_grad(set_to_none=True)
    perte = grpo.apprendre(modele, tirage, grpo.avantages(tirage.recompenses), config.micro_lot, appareil)
    norme = torch.nn.utils.clip_grad_norm_(modele.parameters(), config.ecretage)
    if not torch.isfinite(torch.stack([perte, norme.to(perte.device, perte.dtype)])).all():
        raise PerteNonFinie(f"perte {perte.item()}, norme des gradients {norme.item()}")
    optimiseur.step()
    perte = perte.item()
    secondes_apprentissage = time.perf_counter() - debut
    recompenses = tirage.recompenses
    sans_signal = (recompenses == recompenses[:, :1]).all(dim=1)
    longueurs = [grpo.longueur_generee(sortie, tirage.arret) for sortie in tirage.sorties]
    return {
        "perte": perte,
        "recompense_moyenne": recompenses.mean().item(),
        "groupes_sans_signal": sans_signal.float().mean().item(),
        "longueur_moyenne": sum(longueurs) / len(longueurs),
        "secondes_generation": round(secondes_generation, 3),
        "secondes_apprentissage": round(secondes_apprentissage, 3),
    }


def _valider_grpo(modele, chargeur_val, depart_val, appareil, config, contexte) -> dict:
    """`reussite_val` : la part des problèmes de la validation du RL que le modèle réussit, en glouton."""
    with _en_generant():
        return {"reussite_val": grpo.reussite(modele, contexte["tokenizer"], chargeur_val.problemes, config.grpo)}


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
enregistrer_methode(
    Methode(
        nom="dpo",
        creer_chargeurs=_chargeurs_dpo,
        preparer=_preparer_dpo,
        pas=pas_dpo,
        valider=_valider_dpo,
    )
)
enregistrer_methode(
    Methode(
        nom="grpo",
        creer_chargeurs=_chargeurs_grpo,
        preparer=_preparer_grpo,
        pas=pas_grpo,
        valider=_valider_grpo,
        plus_grand_est_meilleur=True,
    )
)
