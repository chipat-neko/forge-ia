"""Le mini-GRPO de la partie 1.9, à la nanochat : ton IA apprend de ses propres réponses, récompensées si elles sont justes.

GRPO (« Group Relative Policy Optimization ») : pour chaque problème, le modèle écrit plusieurs réponses (un
« groupe »), chacune reçoit une récompense, et le modèle apprend à rendre plus probables les réponses meilleures que
la moyenne de leur groupe, moins probables les autres. Cette version suit `scripts/chat_rl.py` de nanochat
(« méthodes », §4.3) :

- la récompense vaut 1 si la réponse est juste (`forge.raisonnement.verification.est_juste` : terminée, et le
  dernier nombre de son texte est la bonne réponse), sinon 0 ;
- l'avantage d'une réponse est `r − moyenne(r)` sur son groupe, sans division par l'écart-type (`avantages`) ;
- la perte est −Σ A · log π(jeton) sur les jetons générés (le `<|fin_tour|>` compris, l'invite et ce qui suivrait
  l'arrêt exclus), divisée par le nombre total de jetons générés du pas (`apprendre`) ;
- ni KL, ni ratio, ni écrêtage PPO : les réponses viennent du modèle même qu'on entraîne, juste avant le pas ; une
  seule mise à jour par pas.

Un groupe dont toutes les réponses ont la même récompense (toutes justes, ou toutes fausses : le cas courant au
début) a des avantages nuls : il n'apprend rien, et `apprendre` ne calcule même pas ses gradients. Le RL n'amplifie
qu'un comportement déjà présent ; s'il n'y a aucune réponse juste, il n'y a aucun signal. D'où le **contrôle de
départ** (`controle_de_depart`) : avant le premier pas, `controle_invites` problèmes × `controle_reponses` tirages ;
sans aucune réponse juste, rien n'est lancé (la méthode `grpo` de `forge.entrainement.methodes`).

Les problèmes viennent d'un dossier de `forge problemes` d'usage `entrainement` (`ChargeurInvites`). La validation
(`reussite_val`, `reussite`) mesure en glouton les problèmes des graines de la validation du RL, que l'entraînement ne
voit jamais et dont les prénoms sont réservés (`problemes_de_validation`) : c'est elle qui choisit `meilleur.pt`,
jamais les problèmes d'évaluation du rapport.

Le hasard : les réponses du pas `n` viennent d'un seul `generer_lot`, de graine `graine_du_pas(graine, n)` ; le
contrôle, du « pas 0 », par paquets dont les graines sont tirées de `Hasard(graine_du_pas(graine, 0))`. Une reprise
refait donc exactement les mêmes tirages.
"""

import json
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import torch
import torch.nn.functional as F
from torch import Tensor, nn

from forge.affinage.jeu import IGNORE
from forge.conversation.format import Reponse, Tour, invite_de_reponse, lire_reponse
from forge.erreurs import DonneesManquantes
from forge.evaluation.perte import autocast
from forge.fichiers import ESPACE_FINE, duree, ecrire_texte, entier, nombre
from forge.fragments import lire_elements
from forge.hasard import Hasard
from forge.modele import generer_lot
from forge.raisonnement.problemes import DIFFICULTES, GRAINES_VALIDATION_RL, Probleme, generer_problemes
from forge.raisonnement.verification import est_juste
from forge.tokenizer.bpe_octets import TokenizerOctets

if TYPE_CHECKING:  # pour les annotations seulement : la boucle importe ce module (par forge.entrainement.methodes)
    from forge.entrainement.boucle import ReglagesGRPO

_FINE = ESPACE_FINE

# Le fichier du contrôle de départ, dans la sortie de l'entraînement.
NOM_DU_CONTROLE = "controle.json"

# Une ligne d'avancement du contrôle de départ au plus toutes les 30 secondes.
SECONDES_ENTRE_PROGRES = 30

# La graine du pas n : (graine × 1 000 003 + n) mod 2³².
MULTIPLICATEUR_DE_GRAINE = 1_000_003

# La version de l'état de `ChargeurInvites` gardé dans les sauvegardes.
VERSION_DE_L_ETAT = 1

_COMMANDE_DES_PROBLEMES = "python -m forge problemes --sortie rl-1.9 --nombre 20000 --graine-depart 2000000 --difficultes 1,2"


def graine_du_pas(graine: int, numero: int) -> int:
    """La graine des tirages du pas `numero` (0 : le contrôle de départ) : (graine × 1 000 003 + numero) mod 2³²."""
    return (graine * MULTIPLICATEUR_DE_GRAINE + numero) % 2**32


# --- Les problèmes --------------------------------------------------------------------------


def _index_des_problemes(dossier: Path) -> dict:
    """L'`index.json` d'un dossier de problèmes complet, d'usage `entrainement` ; sinon, ce qui manque ou ce qui ne va pas."""
    index = dossier / "index.json"
    if not (dossier / ".complet").is_file() or not index.is_file():
        raise DonneesManquantes(
            f"Les problèmes de {dossier} ne sont pas (ou pas entièrement) générés{_FINE}: {dossier / '.complet'} manque. "
            f"Lance `python -m forge problemes` avec ce dossier en --sortie, par exemple{_FINE}: {_COMMANDE_DES_PROBLEMES}"
        )
    contenu = json.loads(index.read_text(encoding="utf-8"))
    usage = contenu.get("usage")
    if usage != "entrainement":
        raise ValueError(
            f"Les problèmes de {dossier} sont d'usage {usage!r}, pas d'entraînement{_FINE}: ils ne servent jamais au RL "
            "(ceux de l'évaluation sont réservés au rapport, ceux de la validation du RL à reussite_val). Génère des "
            f"problèmes avec des graines d'entraînement, par exemple{_FINE}: {_COMMANDE_DES_PROBLEMES}"
        )
    return contenu


def lire_problemes(dossier: Path) -> list[Probleme]:
    """Tous les problèmes d'un dossier de `forge problemes` d'usage `entrainement`, dans l'ordre du fichier.

    Un dossier incomplet lève `DonneesManquantes` ; un dossier d'un autre usage (évaluation, validation du RL),
    `ValueError`.
    """
    dossier = Path(dossier)
    _index_des_problemes(dossier)
    return [
        Probleme(
            id=element["id"],
            famille=element["famille"],
            difficulte=int(element["difficulte"]),
            enonce=element["enonce"],
            etapes=tuple(element["etapes"]),
            reponse=int(element["reponse"]),
        )
        for element in lire_elements(dossier, "problemes")
    ]


class ChargeurInvites:
    """Des lots de `taille_lot` problèmes d'entraînement de `dossier`, mélangés à chaque époque.

    L'ordre ne dépend que de `(graine, époque)`, comme les autres chargeurs de la forge : `etat()` et
    `restaurer(etat)` reprennent exactement au même endroit. Un lot à cheval sur deux époques prend la fin de
    l'une et le début de l'autre.
    """

    def __init__(self, dossier: Path, taille_lot: int, graine: int) -> None:
        if not isinstance(taille_lot, int) or taille_lot < 1:
            raise ValueError(f"La taille de lot vaut {taille_lot!r} : il faut au moins un problème par lot.")
        self.dossier = Path(dossier)
        self.problemes = lire_problemes(self.dossier)
        if not self.problemes:
            raise ValueError(f"{self.dossier} n'a aucun problème{_FINE}: génère-les avec {_COMMANDE_DES_PROBLEMES}")
        self.taille_lot = taille_lot
        self.graine = graine
        self.epoque = 0
        self.position = 0
        self._melanger()

    def _melanger(self) -> None:
        self._ordre = np.random.default_rng([self.graine, self.epoque]).permutation(len(self.problemes))

    def lot(self) -> list[Probleme]:
        """Les `taille_lot` problèmes suivants."""
        pris: list[Probleme] = []
        while len(pris) < self.taille_lot:
            if self.position == len(self.problemes):  # l'époque est finie : nouvel ordre
                self.epoque += 1
                self.position = 0
                self._melanger()
            n = min(self.taille_lot - len(pris), len(self.problemes) - self.position)
            pris.extend(self.problemes[int(i)] for i in self._ordre[self.position : self.position + n])
            self.position += n
        return pris

    def etat(self) -> dict:
        """Ce qu'il faut garder pour reprendre au même endroit (des nombres simples)."""
        return {
            "version": VERSION_DE_L_ETAT,
            "graine": self.graine,
            "epoque": self.epoque,
            "position": self.position,
            "problemes": len(self.problemes),
        }

    def restaurer(self, etat: dict) -> None:
        """Replace le chargeur à la position décrite par `etat` (venu de `etat()`)."""
        if etat.get("version") != VERSION_DE_L_ETAT:
            raise ValueError(
                f"État du chargeur de problèmes de version {etat.get('version')!r}, cette version de la forge lit la "
                f"version {VERSION_DE_L_ETAT}."
            )
        if etat["graine"] != self.graine:
            raise ValueError(
                f"La sauvegarde a été faite avec la graine {etat['graine']}, la configuration donne {self.graine} : "
                f"remets graine = {etat['graine']} pour reprendre le même entraînement."
            )
        if etat["problemes"] != len(self.problemes):
            raise ValueError(
                f"Le dossier {self.dossier} n'a plus les problèmes de la sauvegarde ({etat['problemes']} alors, "
                f"{len(self.problemes)} maintenant). Reprends avec les mêmes problèmes."
            )
        self.epoque = int(etat["epoque"])
        self.position = int(etat["position"])
        self._melanger()


@dataclass(frozen=True)
class ValidationRL:
    """Les problèmes de la validation du RL : toujours les mêmes, générés d'un coup (rien à reprendre)."""

    problemes: tuple[Probleme, ...]

    def etat(self) -> dict:
        return {}


def problemes_de_validation(dossier: Path, n: int) -> ValidationRL:
    """`n` problèmes des graines de la validation du RL (`GRAINES_VALIDATION_RL`), aux difficultés du dossier
    d'entraînement `dossier` (moins de `n` si des énoncés se répètent).

    Leurs prénoms (`PRENOMS_VALIDATION_RL`) ne sont ni ceux de l'entraînement ni ceux de l'évaluation : aucun de
    ces problèmes ne peut être un problème appris, ni un problème du rapport d'évaluation.
    """
    difficultes = _index_des_problemes(Path(dossier)).get("difficultes") or DIFFICULTES
    return ValidationRL(tuple(generer_problemes(n, GRAINES_VALIDATION_RL, difficultes=tuple(difficultes))))


def tokenizer_du_depart(dossier: Path) -> TokenizerOctets:
    """Le tokenizer de la version de départ (`charger_publication` en a déjà vérifié l'empreinte)."""
    from forge.publication import NOM_DU_TOKENIZER  # importé ici : forge.publication importe forge.entrainement

    return TokenizerOctets.charger(Path(dossier) / NOM_DU_TOKENIZER)


# --- Les tirages et les récompenses -------------------------------------------------------------


def invite_du_probleme(tok: TokenizerOctets, probleme: Probleme) -> list[int]:
    """L'énoncé en tour de l'utilisateur, puis `<|assistant|>` : comme l'évaluation de l'étape et le SFT des traces."""
    return invite_de_reponse(tok, [Tour("utilisateur", probleme.enonce)])


def recompense(reponse: Reponse, probleme: Probleme) -> float:
    """1 si la réponse est juste (terminée, et le dernier nombre de son texte est la réponse), sinon 0."""
    return 1.0 if est_juste(reponse, probleme.reponse) else 0.0


@dataclass(frozen=True)
class Tirage:
    """Les réponses tirées pour un lot de problèmes, et leurs récompenses.

    - `invites` : une par problème (ses jetons, jusqu'à `<|assistant|>` compris) ;
    - `sorties` : les jetons écrits, `reponses` par problème, ceux du problème `i` aux places `i × reponses` et
      suivantes ; chacune s'arrête après son premier `arret`, ou à la limite de jetons ;
    - `recompenses` : `[problèmes, reponses]`, en float32 ;
    - `arret`, `bourrage` : les identifiants de `<|fin_tour|>` et de `<|bourrage|>`.
    """

    invites: list[list[int]]
    sorties: list[list[int]]
    recompenses: Tensor
    arret: int
    bourrage: int


def tirer(
    modele: nn.Module,
    tok: TokenizerOctets,
    problemes: Sequence[Probleme],
    n_reponses: int,
    graine: int,
    reglages: "ReglagesGRPO",
    *,
    glouton: bool = False,
) -> Tirage:
    """`n_reponses` réponses à chaque problème, d'un seul `generer_lot`, et leurs récompenses.

    Les invites sont répétées `n_reponses` fois à la suite ; au plus `jetons_max_reponse` jetons, à `temperature`
    et `top_k`, par paquets de `lot_de_generation`, avec arrêt à `<|fin_tour|>`. `glouton` : température 0 (la
    validation). Le modèle est en mode évaluation et sans gradient pendant la génération (`generer_lot`).
    """
    invites = [invite_du_probleme(tok, p) for p in problemes]
    arret = tok.id_special("<|fin_tour|>")
    sorties = generer_lot(
        modele,
        [invite for invite in invites for _ in range(n_reponses)],
        reglages.jetons_max_reponse,
        0.0 if glouton else reglages.temperature,
        reglages.top_k,
        graine,
        arret,
        reglages.lot_de_generation,
    )
    recompenses = [
        [recompense(lire_reponse(tok, sorties[i * n_reponses + r]), p) for r in range(n_reponses)]
        for i, p in enumerate(problemes)
    ]
    return Tirage(
        invites=invites,
        sorties=sorties,
        recompenses=torch.tensor(recompenses, dtype=torch.float32),
        arret=arret,
        bourrage=tok.id_special("<|bourrage|>"),
    )


def avantages(recompenses: Tensor) -> Tensor:
    """`[invites, reponses]` : la récompense moins la moyenne de son groupe, sans division par l'écart-type."""
    return recompenses - recompenses.mean(dim=1, keepdim=True)


# --- L'apprentissage -----------------------------------------------------------------------------


def longueur_generee(sortie: Sequence[int], arret: int) -> int:
    """Le nombre de jetons générés qui comptent : jusqu'au premier `arret` compris (toute la sortie sans arrêt)."""
    return list(sortie).index(arret) + 1 if arret in sortie else len(sortie)


def rangees(
    invites: Sequence[Sequence[int]], sorties: Sequence[Sequence[int]], arret: int, bourrage: int
) -> tuple[Tensor, Tensor]:
    """Les rangées d'apprentissage d'un micro-lot : `ids` et `cibles`, `[n, T]`, complétées à droite par `bourrage`.

    La rangée k est l'invite k suivie des jetons générés de la sortie k, jusqu'au premier `arret` compris. Les
    cibles sont les jetons suivants, mais seulement les jetons générés : l'invite, le bourrage et ce qui suivrait
    l'arrêt valent `IGNORE`. Le bourrage est à droite : l'attention causale ne le voit jamais depuis un vrai jeton.
    """
    lignes = []
    for invite, sortie in zip(invites, sorties, strict=True):
        generes = list(sortie[: longueur_generee(sortie, arret)])
        lignes.append(([*invite, *generes], len(invite)))
    largeur = max(len(ligne) for ligne, _ in lignes) - 1
    ids = torch.full((len(lignes), largeur), bourrage, dtype=torch.long)
    cibles = torch.full((len(lignes), largeur), IGNORE, dtype=torch.long)
    for k, (ligne, debut) in enumerate(lignes):
        ids[k, : len(ligne) - 1] = torch.tensor(ligne[:-1], dtype=torch.long)
        cibles[k, debut - 1 : len(ligne) - 1] = torch.tensor(ligne[debut:], dtype=torch.long)
    return ids, cibles


def perte_de_politique(
    modele: nn.Module, ids: Tensor, cibles: Tensor, avantages_des_rangees: Tensor, jetons: int, appareil: torch.device
) -> Tensor:
    """−Σ A · log π(jeton) sur les cibles des rangées, divisée par `jetons` (les jetons générés de TOUT le pas).

    Le modèle calcule sous `autocast` (bf16 sur la carte) ; les log-probabilités sont tirées des logits en float32.
    """
    with autocast(appareil):
        logits, _ = modele(ids.to(appareil))
    cibles = cibles.to(appareil)
    log_probas = -F.cross_entropy(
        logits.float().reshape(-1, logits.shape[-1]), cibles.reshape(-1), ignore_index=IGNORE, reduction="none"
    ).reshape(cibles.shape)
    return -(avantages_des_rangees.to(appareil, torch.float32) * log_probas.sum(dim=1)).sum() / jetons


def apprendre(modele: nn.Module, tirage: Tirage, avantages_du_tirage: Tensor, micro_lot: int, appareil: torch.device) -> Tensor:
    """`backward` de la perte du GRPO sur tout le tirage, `micro_lot` réponses à la fois ; rend la perte (détachée).

    Les gradients des micro-lots s'additionnent : chacun divise par le nombre de jetons générés de tout le pas, comme
    si la carte avait tout calculé d'un coup. Les réponses d'avantage nul (les groupes sans signal) n'ajouteraient
    que des zéros : elles ne sont pas calculées, et un tirage sans aucun signal ne laisse aucun gradient.
    """
    reponses = avantages_du_tirage.shape[1]
    a_plat = avantages_du_tirage.reshape(-1)
    jetons = sum(longueur_generee(sortie, tirage.arret) for sortie in tirage.sorties)
    avec_signal = [k for k in range(len(tirage.sorties)) if a_plat[k].item() != 0]
    somme = torch.zeros((), device=appareil)
    for debut in range(0, len(avec_signal), micro_lot):
        numeros = avec_signal[debut : debut + micro_lot]
        ids, cibles = rangees(
            [tirage.invites[k // reponses] for k in numeros], [tirage.sorties[k] for k in numeros], tirage.arret,
            tirage.bourrage,
        )
        perte = perte_de_politique(modele, ids, cibles, a_plat[numeros], jetons, appareil)
        perte.backward()
        somme += perte.detach()
    return somme


# --- La validation et le contrôle de départ -------------------------------------------------------


def reussite(modele: nn.Module, tok: TokenizerOctets, problemes: Sequence[Probleme], reglages: "ReglagesGRPO") -> float:
    """La part des problèmes que le modèle réussit en glouton (une réponse chacun, `jetons_max_reponse` au plus)."""
    return tirer(modele, tok, problemes, 1, 0, reglages, glouton=True).recompenses.mean().item()


def controle_de_depart(
    modele: nn.Module,
    tok: TokenizerOctets,
    problemes: Sequence[Probleme],
    reglages: "ReglagesGRPO",
    graine: int,
    version: str,
) -> dict:
    """`controle_reponses` tirages pour chaque problème, comme les pas du GRPO ; combien sont justes ?

    Les problèmes passent par paquets d'environ `lot_de_generation` réponses ; la graine de chaque paquet est tirée
    de `Hasard(graine)`. Au plus toutes les `SECONDES_ENTRE_PROGRES` secondes, une ligne à l'écran donne les réponses
    faites, le débit et le temps restant. Rend `{"invites", "reponses", "justes", "taux", "lance", "secondes"}` :
    `lance` est vrai s'il y a au moins une réponse juste (le RL a un signal).
    """
    n = reglages.controle_reponses
    total = len(problemes) * n
    print(f"Contrôle de départ{_FINE}: {entier(len(problemes), milliers=_FINE)} problèmes × {n} tirages avec {version}…", flush=True)
    paquet = max(1, reglages.lot_de_generation // n)
    hasard = Hasard(graine)
    justes = faites = 0
    debut = dernier_affichage = time.perf_counter()
    for premier in range(0, len(problemes), paquet):
        tirage = tirer(modele, tok, problemes[premier : premier + paquet], n, hasard.suivant32(), reglages)
        justes += int((tirage.recompenses == 1).sum())
        faites += tirage.recompenses.numel()
        maintenant = time.perf_counter()
        if faites < total and maintenant - dernier_affichage >= SECONDES_ENTRE_PROGRES:
            dernier_affichage = maintenant
            debit = faites / max(maintenant - debut, 1e-9)
            print(
                f"Contrôle de départ{_FINE}: {entier(faites, milliers=_FINE)} réponses sur {entier(total, milliers=_FINE)} "
                f"({nombre(100 * faites / total, 1)}{_FINE}%) · {nombre(debit, 1, milliers=_FINE)} réponses/s · "
                f"reste ≈ {duree((total - faites) / debit)}",
                flush=True,
            )
    secondes = time.perf_counter() - debut
    taux = justes / total
    print(
        f"Contrôle de départ{_FINE}: {entier(justes, milliers=_FINE)} réponses justes sur {entier(total, milliers=_FINE)} "
        f"({nombre(100 * taux, 1)}{_FINE}%), en {duree(secondes)}.",
        flush=True,
    )
    return {
        "invites": len(problemes),
        "reponses": total,
        "justes": justes,
        "taux": taux,
        "lance": justes > 0,
        "secondes": round(secondes, 1),
    }


def ecrire_controle(chemin: Path, controle: dict) -> None:
    """`controle.json`, écrit d'un coup (jamais à moitié, même sur un Ctrl+C)."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    ecrire_texte(chemin, json.dumps(controle, indent=2, ensure_ascii=False) + "\n")
