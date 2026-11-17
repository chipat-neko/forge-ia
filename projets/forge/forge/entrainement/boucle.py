"""La boucle d'entraînement de « ton IA » : apprendre, noter, sauvegarder, se mettre en pause.

Un entraînement est une suite de pas d'optimisation. À chaque pas (`pas_d_optimisation`) :

1. on lit `accumulation` micro-lots de jetons. Pour chacun, le modèle prédit le jeton suivant
   à chaque position, on mesure son erreur (la perte) et on calcule dans quelle direction
   bouger chaque poids pour la réduire (les gradients, par `backward`). Les gradients des
   micro-lots s'additionnent : c'est l'« accumulation de gradient ». Elle permet un grand lot
   (`taille_lot_jetons`, par exemple 500 000 jetons) avec une carte graphique qui n'en tient
   que `micro_lot` lignes à la fois ;
2. on « écrête » les gradients : si leur norme dépasse `ecretage`, on les réduit tous dans la
   même proportion, pour qu'un lot bizarre ne fasse pas un saut énorme ;
3. l'optimiseur AdamW bouge les poids, d'un pas réglé par le taux d'apprentissage du
   planning (`forge.entrainement.planning.taux`).

Sur la carte graphique, les calculs se font en `bfloat16` (16 bits au lieu de 32) grâce à
`torch.autocast` : deux fois moins de mémoire et bien plus rapide, alors que les poids
eux-mêmes restent en 32 bits.

Autour de ces pas : un journal (`journal.jsonl`, une ligne JSON par pas), une perte de
validation de temps en temps (sur des textes jamais appris, `val/`), et des sauvegardes
(`sauvegardes/etape-0000123.pt`) toutes les `sauvegarde_minutes` et à la fin.

Pause et reprise : Ctrl+C ne coupe pas net. La boucle finit le pas en cours, sauvegarde tout
(le modèle, l'optimiseur, le pas, la position dans les données, l'état du hasard et la
configuration), affiche la commande de reprise, puis s'arrête. Avec `--reprendre`, le pas
suivant est exactement celui qui aurait suivi sans la pause. Après un plantage ou une
coupure de courant, la reprise part de la dernière sauvegarde complète.

Ce pas est celui du pré-entraînement. L'affinage (SFT, puis DPO et GRPO) passe par la même
boucle : le réglage `methode` choisit les chargeurs, le pas et la validation dans le registre de
`forge.entrainement.methodes`. Un affinage part d'une version publiée de ton IA (`depart`) : ses
poids sont copiés dans le modèle avant de créer l'optimiseur.
"""

import contextlib
import dataclasses
import gc
import importlib.util
import json
import logging
import random
import signal
import sys
import threading
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from torch import nn

from forge.chemins import OCTETS_PAR_GO, PlaceInsuffisante, sous_forge_donnees
from forge.donnees.jetons import empreinte_du_tokenizer
from forge.entrainement.chargeur import ChargeurJetons, empreinte_du_tokenizer_des_jetons
from forge.entrainement.methodes import METHODES, PerteNonFinie, VersionDeDepart
from forge.entrainement.planning import taux
from forge.entrainement.sauvegarde import (
    CONSEIL_DE_REPRISE,
    VERSION_DE_LA_SAUVEGARDE,
    charger_derniere,
    est_disque_plein,
    nom_etape,
    sauvegarder,
)
from forge.evaluation.perte import autocast as _autocast  # bf16 sur la carte graphique, 32 bits sur le processeur
from forge.evaluation.perte import perte_sur_morceaux as _perte_validation  # noqa: F401  (la mesure de `evaluer`, lue par les tests)
from forge.fichiers import duree, ecrire_texte, entier, nombre, scientifique
from forge.modele import PRESETS, ConfigModele, Transformer, nombre_parametres
from forge.processeur import fils_disponibles

# Une ligne de suivi à l'écran au plus toutes les 10 secondes (le journal, lui, a chaque pas).
SECONDES_ENTRE_AFFICHAGES = 10

# Réglages qu'on peut changer en reprenant : ils ne changent pas le calcul. `micro_lot` change
# le découpage d'un pas, pas ses jetons ; `donnees` peut changer de chemin (le chargeur vérifie
# que les jetons sont les mêmes) ; `sortie` est le dossier où l'on a trouvé la sauvegarde ;
# `depart` aussi peut changer de chemin (la sauvegarde vérifie que c'est la même version).
# Deux autres peuvent changer dans un seul sens : `jetons_total` peut augmenter (le planning
# s'allonge) et `taux_max` peut baisser (le remède à une perte devenue infinie).
REGLAGES_LIBRES = (
    "micro_lot",
    "compiler",
    "sauvegarde_minutes",
    "evaluation_tous_pas",
    "appareil",
    "fichier",
    "donnees",
    "sortie",
    "depart",
)

# Le dossier de `FORGE_DONNEES` où chaque méthode trouve ses données (`donnees`).
SOUS_DOSSIERS_DES_DONNEES = {"pre_entrainement": "jetons", "sft": "affinage", "dpo": "affinage", "grpo": "problemes"}

# Code de sortie quand la perte devient infinie (2 : manque de mémoire de la carte graphique).
CODE_PERTE_INFINIE = 3


class CompilationImpossible(RuntimeError):
    """`torch.compile` a échoué alors que la configuration l'exige (`compiler = "oui"`)."""


# --- La configuration -----------------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class ConfigEntrainement:
    """Les réglages d'un entraînement, lus depuis un fichier TOML par `lire_config`.

    - `methode` : la méthode d'entraînement, un nom de `METHODES` (`forge.entrainement.methodes`) :
      « pre_entrainement » (par défaut) ou « sft » (affinage supervisé) ;
    - `depart` : pour un affinage, le dossier de la version publiée d'où l'on part (un nom va sous
      `FORGE_DONNEES/publications/`, là où `forge publication` la télécharge). Obligatoire pour
      un affinage, interdit pour le pré-entraînement, qui part de poids tirés au hasard ;
    - `preset` : la taille du modèle, un nom de `PRESETS` (« mini », « petit »…) ; on peut
      aussi donner une `ConfigModele` (ou, dans le TOML, une table `[preset]`) ;
    - `donnees` : le dossier des données. Pour le pré-entraînement, celui des jetons de
      `forge encoder --donnees <nom>` (un nom va sous `FORGE_DONNEES/jetons/`) ; pour le SFT, un
      jeu d'affinage (sous `FORGE_DONNEES/affinage/`). Un chemin absolu est gardé tel quel ;
    - `jetons_total` : combien de jetons lire en tout ; avec `taille_lot_jetons`, il fixe le
      nombre de pas ;
    - `taille_lot_jetons` : jetons vus par pas d'optimisation (le « lot ») ; pour un affinage,
      ce sont les positions des rangées, bourrage compris ;
    - `longueur` : la longueur des lignes (des rangées d'un jeu d'affinage), par défaut le
      contexte du modèle. Celle d'un jeu d'affinage doit être la sienne ;
    - `micro_lot` : lignes de `longueur` jetons traitées d'un coup par la carte ; le lot est
      atteint par accumulation. À réduire en cas de manque de mémoire ;
    - `taux_max`, `echauffement` : le planning du taux d'apprentissage (voir `planning.py`) ;
    - `poids_decroissance` : la « décroissance des poids » d'AdamW, qui tire doucement les
      poids vers 0 (sur les matrices seulement, pas sur les RMSNorm) ;
    - `betas` : les deux coefficients d'AdamW (moyenne des gradients et de leurs carrés) ;
    - `ecretage` : norme maximale des gradients ;
    - `graine` : la graine du hasard (poids de départ, ordre des données) ;
    - `evaluation_tous_pas` : la perte de validation est mesurée tous les N pas ;
    - `sauvegarde_minutes` : une sauvegarde au moins toutes les N minutes ;
    - `appareil` : « cuda » (carte graphique) ou « cpu » (processeur) ;
    - `compiler` : « auto » (essayer `torch.compile`, sinon continuer sans), « oui » (erreur
      s'il échoue) ou « non » ;
    - `sortie` : le dossier du journal et des sauvegardes (un nom va sous
      `FORGE_DONNEES/entrainements/`) ;
    - `dpo`, `grpo` : les tables `[dpo]` et `[grpo]` du TOML, réglages propres à ces méthodes ;
    - `fichier` : le fichier TOML lu, rempli par `lire_config` (il sert aux messages).
    """

    methode: str = "pre_entrainement"
    depart: str | None = None
    preset: str | ConfigModele
    donnees: str
    jetons_total: int | None = None
    taille_lot_jetons: int | None = None
    longueur: int | None = None
    micro_lot: int
    taux_max: float
    echauffement: int
    poids_decroissance: float = 0.1
    betas: tuple[float, float] = (0.9, 0.95)
    ecretage: float = 1.0
    graine: int = 1234
    evaluation_tous_pas: int
    sauvegarde_minutes: float = 30
    appareil: str = "cuda"
    compiler: str = "auto"
    sortie: str
    dpo: dict | None = None
    grpo: dict | None = None
    fichier: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.preset, dict):  # une table `[preset]` du TOML
            try:
                object.__setattr__(self, "preset", ConfigModele(**self.preset))
            except TypeError as erreur:
                raise ValueError(f"Table [preset] invalide : {erreur}.") from erreur
        if isinstance(self.preset, str) and self.preset not in PRESETS:
            raise ValueError(
                f"preset = {self.preset!r} n'existe pas. Choix possibles : {', '.join(PRESETS)}."
            )
        if not isinstance(self.preset, str | ConfigModele):
            raise ValueError("preset doit être un nom de taille (« mini », « petit »…) ou une ConfigModele.")
        self._verifier_methode()
        for nom, minimum in (
            ("jetons_total", 1),
            ("taille_lot_jetons", 1),
            ("micro_lot", 1),
            ("echauffement", 0),
            ("graine", 0),
            ("evaluation_tous_pas", 1),
        ):
            valeur = getattr(self, nom)
            if valeur is None and nom in ("jetons_total", "taille_lot_jetons"):
                continue  # le GRPO compte ses pas autrement : déjà vérifié par `_verifier_methode`
            if not isinstance(valeur, int) or isinstance(valeur, bool) or valeur < minimum:
                raise ValueError(
                    f"{nom} vaut {valeur!r} : il faut un nombre entier d'au moins {minimum} "
                    "(dans le TOML, écris par exemple 200_000_000 plutôt que 2e8)."
                )
        if self.graine >= 2**32:
            raise ValueError(f"graine vaut {self.graine} : il faut un entier plus petit que 2³² (4 294 967 296).")
        for nom in ("taux_max", "ecretage", "sauvegarde_minutes"):
            valeur = getattr(self, nom)
            if not isinstance(valeur, int | float) or isinstance(valeur, bool) or valeur <= 0:
                raise ValueError(f"{nom} vaut {valeur!r} : il faut un nombre plus grand que 0.")
        if not isinstance(self.poids_decroissance, int | float) or self.poids_decroissance < 0:
            raise ValueError(f"poids_decroissance vaut {self.poids_decroissance!r} : il faut un nombre positif ou nul.")
        betas = tuple(self.betas)
        if len(betas) != 2 or not all(isinstance(b, int | float) and 0 <= b < 1 for b in betas):
            raise ValueError(f"betas vaut {self.betas!r} : il faut deux nombres entre 0 et 1, par exemple [0.9, 0.95].")
        object.__setattr__(self, "betas", betas)
        if self.appareil not in ("cuda", "cpu"):
            raise ValueError(f'appareil vaut {self.appareil!r} : écris "cuda" (carte graphique) ou "cpu".')
        if self.compiler not in ("auto", "oui", "non"):
            raise ValueError(f'compiler vaut {self.compiler!r} : écris "auto", "oui" ou "non".')
        contexte = self.modele.longueur_contexte
        if self.longueur is not None and (
            not isinstance(self.longueur, int) or isinstance(self.longueur, bool) or not 1 <= self.longueur <= contexte
        ):
            raise ValueError(
                f"longueur vaut {self.longueur!r} : il faut un entier de 1 à {contexte}, le contexte du modèle "
                "(sans longueur, les lignes ont la longueur du contexte)."
            )
        if self.taille_lot_jetons is None:
            return
        longueur = self.longueur_des_rangees
        par_micro_lot = self.micro_lot * longueur
        if self.taille_lot_jetons % par_micro_lot:
            nom = "longueur_contexte" if self.longueur is None else "longueur"
            possibles = [m for m in range(1, self.micro_lot + 1) if self.taille_lot_jetons % (m * longueur) == 0]
            raise ValueError(
                f"taille_lot_jetons ({self.taille_lot_jetons}) doit être un multiple de "
                f"micro_lot × {nom} ({self.micro_lot} × {longueur} = {par_micro_lot}), "
                "pour que chaque pas voie exactement le même nombre de jetons. "
                f"Valeurs de micro_lot possibles, jusqu'à {self.micro_lot} : "
                f"{', '.join(map(str, possibles)) or 'aucune'}."
            )

    def _verifier_methode(self) -> None:
        """La méthode existe, et ses réglages propres (départ, jetons, tables) sont là où il faut."""
        if self.methode not in METHODES:
            raise ValueError(
                f"methode = {self.methode!r} n'existe pas. Choix possibles : {', '.join(METHODES)}."
            )
        fichier = self.fichier or "la configuration"
        if self.methode == "pre_entrainement" and self.depart is not None:
            raise ValueError(
                f"depart = {self.depart!r}, mais le pré-entraînement part de poids tirés au hasard : retire "
                f"depart de {fichier}, ou choisis une méthode d'affinage (methode = \"sft\")."
            )
        if self.methode != "pre_entrainement" and (not isinstance(self.depart, str) or not self.depart):
            raise ValueError(
                f'methode = "{self.methode}" part d\'une version publiée de ton IA : ajoute depart = '
                f'"ton-ia-1.5" (un dossier sous FORGE_DONNEES/publications/, celui de `forge publication '
                f"--etiquette ton-ia-1.5`) dans {fichier}."
            )
        for nom in ("jetons_total", "taille_lot_jetons"):
            valeur = getattr(self, nom)
            if self.methode == "grpo" and valeur is not None:
                raise ValueError(
                    f'{nom} ne sert pas au GRPO : son nombre de pas vient de [grpo] pas. Retire {nom} de {fichier}.'
                )
            if self.methode != "grpo" and valeur is None:
                raise ValueError(f"Réglage manquant dans {fichier} : {nom}.")
        for table in ("dpo", "grpo"):
            valeur = getattr(self, table)
            if valeur is not None and self.methode != table:
                raise ValueError(
                    f'La table [{table}] ne sert qu\'à methode = "{table}" (ici, methode = "{self.methode}") : '
                    f"retire-la de {fichier}."
                )

    @property
    def modele(self) -> ConfigModele:
        """Les dimensions du modèle à entraîner."""
        return PRESETS[self.preset] if isinstance(self.preset, str) else self.preset

    @property
    def longueur_des_rangees(self) -> int:
        """La longueur des lignes de chaque micro-lot : `longueur`, sinon le contexte du modèle."""
        return self.longueur if self.longueur is not None else self.modele.longueur_contexte

    @property
    def accumulation(self) -> int:
        """Nombre de micro-lots par pas d'optimisation."""
        return self.taille_lot_jetons // (self.micro_lot * self.longueur_des_rangees)

    @property
    def pas_total(self) -> int:
        """Nombre de pas d'optimisation pour lire `jetons_total` jetons (arrondi au-dessus)."""
        return -(-self.jetons_total // self.taille_lot_jetons)

    @property
    def dossier_donnees(self) -> Path:
        """Le dossier des données : sous `jetons/`, `affinage/` ou `problemes/` selon la méthode."""
        return sous_forge_donnees(self.donnees, SOUS_DOSSIERS_DES_DONNEES[self.methode])

    @property
    def dossier_depart(self) -> Path | None:
        """Le dossier de la version de départ (sous `publications/`), ou `None` pour le pré-entraînement."""
        return None if self.depart is None else sous_forge_donnees(self.depart, "publications")

    @property
    def dossier_sortie(self) -> Path:
        return sous_forge_donnees(self.sortie, "entrainements")


def lire_config(chemin: Path | str) -> ConfigEntrainement:
    """Lit un fichier TOML d'entraînement (voir `configs/mini.toml`)."""
    chemin = Path(chemin)
    if not chemin.is_file():
        raise FileNotFoundError(f"Fichier de configuration introuvable : {chemin}.")
    try:
        valeurs = tomllib.loads(chemin.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as erreur:
        raise ValueError(f"{chemin} n'est pas un fichier TOML valide : {erreur}.") from erreur
    connus = [champ.name for champ in dataclasses.fields(ConfigEntrainement) if champ.name != "fichier"]
    inconnus = sorted(set(valeurs) - set(connus))
    if inconnus:
        raise ValueError(
            f"Réglage inconnu dans {chemin} : {', '.join(inconnus)}. Réglages possibles : {', '.join(connus)}."
        )
    manquants = [
        champ.name
        for champ in dataclasses.fields(ConfigEntrainement)
        if champ.default is dataclasses.MISSING and champ.name not in valeurs
    ]
    if manquants:
        raise ValueError(f"Réglage manquant dans {chemin} : {', '.join(manquants)}.")
    return ConfigEntrainement(**valeurs, fichier=str(chemin))


# --- Petits outils ----------------------------------------------------------------------


def _commande_de_reprise(config: ConfigEntrainement) -> str:
    return f"python -m forge entrainer --config {config.fichier or '<fichier>'} --reprendre"


def _semer(graine: int) -> None:
    """Fixe la graine de tous les hasards : Python, NumPy et PyTorch (carte graphique comprise)."""
    random.seed(graine)
    np.random.seed(graine)
    torch.manual_seed(graine)


def _etat_du_hasard() -> dict:
    """L'état de tous les générateurs de hasard, en types simples (lisibles sans risque)."""
    numpy_etat = np.random.get_state(legacy=False)
    numpy_etat["state"]["key"] = numpy_etat["state"]["key"].tolist()
    return {
        "python": random.getstate(),
        "numpy": numpy_etat,
        "torch": torch.get_rng_state(),
        # Seulement si la carte graphique sert déjà : sinon, l'interroger la réveillerait pour rien.
        "cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_initialized() else None,
    }


def _restaurer_hasard(etat: dict) -> None:
    random.setstate(etat["python"])
    numpy_etat = dict(etat["numpy"])
    numpy_etat["state"] = {**numpy_etat["state"], "key": np.array(numpy_etat["state"]["key"], dtype=np.uint32)}
    np.random.set_state(numpy_etat)
    torch.set_rng_state(etat["torch"])
    cuda = etat.get("cuda")
    if cuda is not None and torch.cuda.is_available() and len(cuda) == torch.cuda.device_count():
        torch.cuda.set_rng_state_all(cuda)


class _Journal:
    """`journal.jsonl` : une ligne JSON par pas ou par évènement, écrite tout de suite sur le disque."""

    def __init__(self, chemin: Path) -> None:
        self._chemin = chemin
        self._fichier = open(chemin, "a", encoding="utf-8")

    def ecrire(self, ligne: dict) -> None:
        try:
            self._fichier.write(json.dumps(ligne, ensure_ascii=False) + "\n")
            self._fichier.flush()  # lu pendant l'entraînement par `forge suivi`
        except OSError as erreur:
            if est_disque_plein(erreur):
                raise PlaceInsuffisante(
                    f"Le disque est plein : impossible d'écrire dans {self._chemin}. Libère de la "
                    "place, puis relance avec --reprendre : l'entraînement repartira de la "
                    "dernière sauvegarde complète."
                ) from erreur
            raise

    def fermer(self) -> None:
        try:
            self._fichier.close()
        except OSError:
            # Disque plein : `close` réessaie d'écrire la ligne qui a échoué, et échoue encore.
            # L'erreur utile (PlaceInsuffisante) est déjà en route : on ne la masque pas.
            pass


def _couper_journal(chemin: Path, pas: int) -> None:
    """Après un plantage, le journal peut décrire des pas faits APRÈS la dernière sauvegarde.

    Ces pas vont être refaits : on enlève leurs lignes (et une dernière ligne coupée par une
    panne) pour que le journal suive exactement l'entraînement repris.
    """
    if not chemin.exists():
        return
    gardees = []
    for ligne in chemin.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            contenu = json.loads(ligne)
        except ValueError:
            continue
        if isinstance(contenu, dict) and isinstance(contenu.get("pas"), int) and contenu["pas"] <= pas:
            gardees.append(ligne + "\n")
    # Réessayé si `forge suivi` lit le journal à cet instant ; fins de ligne du système, comme avant.
    ecrire_texte(chemin, "".join(gardees), conseil=CONSEIL_DE_REPRISE, fins_de_ligne=None)


def _ouvrir_le_journal(chemin: Path, pas_sauve: int | None) -> "_Journal":
    """Ouvre le journal d'un entraînement neuf (`pas_sauve` à `None` : l'ancien, celui d'un essai qui
    n'a rien sauvegardé, est effacé), ou repris (les lignes d'après la sauvegarde sont coupées)."""
    if pas_sauve is None:
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.unlink(missing_ok=True)
    else:
        _couper_journal(chemin, pas_sauve)
    return _Journal(chemin)


class _Pause:
    """Pendant l'entraînement, Ctrl+C (et Ctrl+Pause sous Windows) demande une pause.

    Le premier appui lève seulement un drapeau, que la boucle regarde à la fin de chaque pas.
    Un second appui arrête tout de suite (`KeyboardInterrupt`) : le pas en cours est perdu,
    mais la dernière sauvegarde complète reste bonne.

    SIGTERM, là où il existe, fait de même : c'est ce qu'envoient l'arrêt du système (Linux),
    `docker stop` ou `timeout`. Ils laissent en général le temps (90 s pour systemd, 10 s pour
    `docker stop`, réglable) de finir le pas et de sauvegarder, au lieu de perdre jusqu'à
    `sauvegarde_minutes` de calcul.
    """

    def __init__(self) -> None:
        self.demandee = False
        self._anciens: dict[int, object] = {}

    def _signal_recu(self, numero, cadre) -> None:
        if self.demandee:
            raise KeyboardInterrupt
        self.demandee = True
        if numero == getattr(signal, "SIGTERM", None):
            message = (
                "\nArrêt demandé par le système (SIGTERM) : je finis le pas en cours, je sauvegarde, "
                "puis je m'arrête."
            )
        else:
            message = (
                "\nPause demandée : je finis le pas en cours, je sauvegarde, puis je m'arrête "
                "(Ctrl+C une seconde fois : arrêt immédiat, sans sauvegarder ce pas)."
            )
        try:
            print(message, flush=True)
        except (OSError, RuntimeError):
            pass  # l'écran était déjà occupé : le message de pause suivra quand même

    def __enter__(self) -> "_Pause":
        # On ne peut poser un gestionnaire de signal que depuis le fil principal.
        if threading.current_thread() is threading.main_thread():
            for nom in ("SIGINT", "SIGBREAK", "SIGTERM"):
                numero = getattr(signal, nom, None)
                if numero is not None:
                    self._anciens[numero] = signal.signal(numero, self._signal_recu)
        return self

    def __exit__(self, *erreur) -> None:
        for numero, ancien in self._anciens.items():
            signal.signal(numero, ancien)


# Les drapeaux de `SetThreadExecutionState` (Windows) : « jusqu'au prochain appel » et « le système
# doit rester éveillé ».
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001


def _etat_d_execution_windows():
    """La fonction `SetThreadExecutionState` de Windows ; `None` ailleurs, ou si on ne la trouve pas."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes

        fonction = ctypes.WinDLL("kernel32").SetThreadExecutionState
    except (ImportError, OSError, AttributeError):
        return None
    fonction.argtypes = [ctypes.c_uint32]
    fonction.restype = ctypes.c_uint32
    return fonction


@contextlib.contextmanager
def _sans_mise_en_veille():
    """Pendant le bloc, Windows ne se met pas en veille de lui-même (l'écran, lui, peut s'éteindre).

    Un entraînement dure des jours : une mise en veille automatique le suspendrait au même pas
    toute la nuit, et CUDA échoue parfois au réveil. `ES_SYSTEM_REQUIRED` l'empêche tant que le
    bloc dure ; à la sortie (fin, pause, erreur), `ES_CONTINUOUS` seul rend la main aux réglages
    d'alimentation. Une veille demandée (bouton, capot fermé) reste possible. Ailleurs que sous
    Windows, rien n'est fait.
    """
    fixer_etat = _etat_d_execution_windows()
    if fixer_etat is None:
        yield
        return
    fixer_etat(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
    try:
        yield
    finally:
        fixer_etat(ES_CONTINUOUS)


# --- Le modèle et l'optimiseur ----------------------------------------------------------


def creer_optimiseur(modele: nn.Module, config: ConfigEntrainement, appareil: torch.device):
    """AdamW, avec décroissance des poids sur les matrices seulement (pas sur les RMSNorm)."""
    matrices = [p for p in modele.parameters() if p.dim() >= 2]
    vecteurs = [p for p in modele.parameters() if p.dim() < 2]
    groupes = [
        {"params": matrices, "weight_decay": config.poids_decroissance},
        {"params": vecteurs, "weight_decay": 0.0},
    ]
    # « fused » : une seule opération sur la carte graphique pour tous les poids, plus rapide.
    return torch.optim.AdamW(groupes, lr=config.taux_max, betas=config.betas, fused=appareil.type == "cuda")


def _premiere_ligne(erreur: BaseException) -> str:
    texte = str(erreur).strip().splitlines()
    return f"{type(erreur).__name__} : {texte[0] if texte else 'sans message'}"


def _preparer_compilation(
    modele: nn.Module, config: ConfigEntrainement, appareil: torch.device, noter
) -> nn.Module:
    """Renvoie le modèle compilé par `torch.compile` si c'est possible, sinon le modèle tel quel.

    `torch.compile` traduit le modèle en code optimisé pour la carte graphique. Il ne compile
    vraiment qu'au premier appel : on fait donc un essai (un micro-lot de zéros, avant et
    arrière) pour savoir tout de suite s'il marche. Sous Windows, il lui manque souvent
    `triton` (carte graphique) ou un compilateur C++ (processeur). Avec `compiler = "auto"`,
    on continue alors sans compilation (« mode immédiat »), avec une ligne dans le journal ;
    avec `"oui"`, c'est une erreur.
    """
    if config.compiler == "non":
        return modele
    try:
        if appareil.type == "cuda" and importlib.util.find_spec("triton") is None:
            raise RuntimeError("triton n'est pas installé, torch.compile ne peut pas compiler pour la carte graphique")
        # PyTorch écrit sinon un avertissement sur triton à l'écran en important le compilateur.
        logging.getLogger("torch.utils.flop_counter").setLevel(logging.ERROR)
        compile_ = torch.compile(modele)
        essai = torch.zeros((config.micro_lot, config.modele.longueur_contexte), dtype=torch.long, device=appareil)
        with _autocast(appareil):
            _, perte = compile_(essai, essai)
        perte.backward()
    except torch.cuda.OutOfMemoryError:
        raise
    except Exception as erreur:
        modele.zero_grad(set_to_none=True)
        if config.compiler == "oui":
            raise CompilationImpossible(
                f"torch.compile n'a pas pu compiler le modèle ({_premiere_ligne(erreur)}). Mets "
                f'compiler = "auto" (ou "non") dans {config.fichier or "la configuration"} pour '
                "entraîner sans compilation."
            ) from erreur
        noter(
            {
                "evenement": "compilation",
                "message": f"torch.compile indisponible ({_premiere_ligne(erreur)}) : "
                "entraînement en mode immédiat, sans compilation.",
            }
        )
        return modele
    modele.zero_grad(set_to_none=True)  # l'essai ne doit laisser aucun gradient
    noter({"evenement": "compilation", "message": "Modèle compilé par torch.compile."})
    return compile_


# --- Un pas d'optimisation, la validation ------------------------------------------------


def pas_d_optimisation(
    modele: nn.Module,
    optimiseur: torch.optim.Optimizer,
    chargeur: ChargeurJetons,
    accumulation: int,
    taux_du_pas: float,
    ecretage: float,
    appareil: torch.device,
) -> float:
    """Un pas d'optimisation : `accumulation` micro-lots, puis une mise à jour des poids.

    Renvoie la perte moyenne des micro-lots de ce pas. Chaque perte est divisée par
    `accumulation` avant `backward` : la somme des gradients est ainsi la moyenne sur tout le
    lot, comme si la carte avait tout traité d'un coup.

    Si la perte ou la norme des gradients n'est plus un nombre fini (l'entraînement a
    « divergé »), `PerteNonFinie` est levée AVANT de toucher aux poids.
    """
    for groupe in optimiseur.param_groups:
        groupe["lr"] = taux_du_pas
    optimiseur.zero_grad(set_to_none=True)
    somme = torch.zeros((), device=appareil)
    for _ in range(accumulation):
        x, y = chargeur.lot()
        x, y = x.to(appareil), y.to(appareil)
        with _autocast(appareil):
            _, perte = modele(x, y)
        (perte / accumulation).backward()
        somme += perte.detach()
    norme = torch.nn.utils.clip_grad_norm_(modele.parameters(), ecretage)
    moyenne = somme / accumulation
    if not torch.isfinite(torch.stack([moyenne, norme.to(moyenne.dtype)])).all():
        raise PerteNonFinie(f"perte {moyenne.item()}, norme des gradients {norme.item()}")
    optimiseur.step()
    return moyenne.item()


# --- L'entraînement ---------------------------------------------------------------------


def _verifier_appareil(config: ConfigEntrainement) -> torch.device:
    if config.appareil == "cuda" and not torch.cuda.is_available():
        raise ValueError(
            'appareil = "cuda", mais PyTorch ne voit aucune carte graphique NVIDIA. Lance la '
            'commande avec `uv run --extra gpu …`, ou mets appareil = "cpu" dans '
            f"{config.fichier or 'la configuration'}."
        )
    return torch.device(config.appareil)


def _decrire_modele(c: ConfigModele) -> str:
    return (
        f"dim {c.dim}, {c.couches} couches, {c.tetes} têtes, contexte {c.longueur_contexte}, "
        f"vocabulaire {c.taille_vocabulaire}"
    )


def _verifier_sauvegarde(etat: dict, config: ConfigEntrainement) -> list[str]:
    """Refuse de reprendre avec un autre modèle, ou avec des réglages qui changent le calcul.

    Une reprise doit continuer LE MÊME entraînement : mêmes poids de départ, même lot, même
    planning, même optimiseur. Seuls les `REGLAGES_LIBRES` peuvent changer, plus deux
    exceptions à sens unique :

    - `jetons_total` peut augmenter, pour entraîner plus longtemps. Le planning du taux est
      alors recalculé sur le nouveau nombre de pas : la descente en cosinus s'allonge, et le
      taux remonte un peu au moment de la reprise ;
    - `taux_max` peut baisser : c'est le remède quand la perte est devenue infinie. Tout le
      planning est alors abaissé dans la même proportion.

    Renvoie les lignes à écrire dans le journal pour ces deux changements permis.
    """
    if etat.get("version") != VERSION_DE_LA_SAUVEGARDE:
        raise ValueError(
            f"Sauvegarde de version {etat.get('version')!r} : cette version de la forge lit la "
            f"version {VERSION_DE_LA_SAUVEGARDE}."
        )
    sauve = ConfigModele(**etat["config_modele"])
    if sauve != config.modele:
        raise ValueError(
            f"La sauvegarde du pas {etat['pas']} vient d'un autre modèle ({_decrire_modele(sauve)}) "
            f"que celui de la configuration ({_decrire_modele(config.modele)}). Remets le même "
            "preset pour reprendre, ou change `sortie` pour commencer un nouvel entraînement."
        )
    avant, maintenant = etat["config"], dataclasses.asdict(config)
    # Une sauvegarde d'avant un réglage ne le retient pas : elle a été faite avec sa valeur par
    # défaut (une sauvegarde d'avant `methode` est un pré-entraînement).
    defauts = {
        champ.name: champ.default
        for champ in dataclasses.fields(ConfigEntrainement)
        if champ.default is not dataclasses.MISSING
    }
    differences, notes = [], []
    for reglage, valeur in maintenant.items():
        ancienne = avant.get(reglage, defauts.get(reglage))
        # Le preset est déjà comparé, dimension par dimension, juste au-dessus.
        if reglage in REGLAGES_LIBRES or reglage == "preset" or ancienne == valeur:
            continue
        if reglage == "jetons_total" and valeur > ancienne:
            notes.append(
                f"jetons_total passe de {ancienne} à {valeur} : le planning du taux est recalculé "
                f"sur {config.pas_total} pas."
            )
        elif reglage == "taux_max" and valeur < ancienne:
            notes.append(f"taux_max baisse de {ancienne} à {valeur} : tout le planning du taux baisse d'autant.")
        else:
            differences.append(f"{reglage} : {ancienne!r} dans la sauvegarde, {valeur!r} maintenant")
    if differences:
        raise ValueError(
            f"La configuration a changé depuis la sauvegarde du pas {etat['pas']} : "
            f"{' ; '.join(differences)}. Ces réglages changent le calcul : remets les valeurs de la "
            "sauvegarde pour reprendre, ou change `sortie` pour commencer un nouvel entraînement. "
            f"En reprenant, on peut changer {', '.join(REGLAGES_LIBRES[:5])}, augmenter "
            "jetons_total et baisser taux_max."
        )
    return notes


def _signaler_manque_de_memoire(config: ConfigEntrainement, appareil: torch.device) -> None:
    """Le message d'un manque de mémoire sur la carte graphique, puis l'arrêt (code 2)."""
    libre = "inconnue"
    if appareil.type == "cuda":
        gc.collect()
        torch.cuda.empty_cache()  # rend à la carte ce que cet entraînement gardait en réserve
        try:
            octets_libres, octets_total = torch.cuda.mem_get_info()
            libre = f"{nombre(octets_libres / OCTETS_PAR_GO, 1)} Go sur {nombre(octets_total / OCTETS_PAR_GO, 1)} Go"
        except RuntimeError:
            pass
    fichier = config.fichier or "<fichier>"
    memoire = f"Mémoire libre sur la carte graphique : {libre} (Windows et les programmes ouverts en prennent une partie)."
    if config.micro_lot > 1:
        message = (
            f"La carte graphique manque de mémoire pour micro_lot = {config.micro_lot}.\n{memoire}\n"
            f"Réduis micro_lot dans {fichier}, ferme les jeux ou logiciels 3D ouverts, puis relance avec "
            "--reprendre."
        )
    else:
        message = _manque_de_memoire_avec_un_micro_lot_de_1(config, memoire)
    print(message, file=sys.stderr, flush=True)
    raise SystemExit(2)


def _manque_de_memoire_avec_un_micro_lot_de_1(config: ConfigEntrainement, memoire: str) -> str:
    """Le message quand `micro_lot` vaut déjà 1 : on ne peut plus le réduire, il faut une autre marche à suivre."""
    fichier = config.fichier or "<fichier>"
    parametres = nombre_parametres(config.modele)
    taille = f"preset « {config.preset} »" if isinstance(config.preset, str) else "table [preset]"
    millions = nombre(parametres / 1e6, 1)
    plus_petits = [nom for nom, modele in PRESETS.items() if nombre_parametres(modele) < parametres]
    lignes = [
        f"La carte graphique manque de mémoire, même avec micro_lot = 1 : ce modèle ({taille}, "
        f"{millions} millions de paramètres) ne tient pas sur cette carte.",
        memoire,
        "Que faire :",
        "- ferme les programmes qui prennent la carte (jeux, logiciels 3D, vidéos, un autre entraînement), "
        f"puis relance : {_commande_de_reprise(config)} ;",
    ]
    if plus_petits:
        lignes.append(
            "- ou choisis un preset plus petit, dans une nouvelle sortie (une sauvegarde ne reprend que le "
            f"même modèle) : python -m forge mesurer --presets {','.join(plus_petits)} dit lesquels tiennent "
            "sur cette carte ;"
        )
    lignes.append(f'- ou mets appareil = "cpu" dans {fichier} (bien plus lent), puis relance avec --reprendre.')
    return "\n".join(lignes)


def _etat_du_modele(
    config: ConfigEntrainement, modele: nn.Module, pas: int, depart: VersionDeDepart | None = None
) -> dict:
    """Ce qu'il faut pour reconstruire et utiliser le modèle : ses poids, sa configuration, sa
    méthode, sa version de départ, et l'empreinte du tokenizer, que l'export compare à celle du
    tokenizer figé.

    Pour un affinage, l'empreinte est celle du tokenizer de la version de départ (`depart`,
    obligatoire). Pour le pré-entraînement, c'est celle de l'`index.json` des jetons
    d'entraînement ; sans index lisible, la sauvegarde ne la retient pas.
    """
    if config.methode != "pre_entrainement" and depart is None:
        raise ValueError(
            f'Une sauvegarde de methode = "{config.methode}" retient sa version de départ : il faut `depart`.'
        )
    etat = {
        "version": VERSION_DE_LA_SAUVEGARDE,
        "pas": pas,
        "modele": modele.state_dict(),
        "config": dataclasses.asdict(config),
        "config_modele": dataclasses.asdict(config.modele),
        "methode": config.methode,
        "depart_version": None if depart is None else depart.version,
        "depart_empreinte": None if depart is None else depart.empreinte_des_poids,
    }
    if config.methode == "pre_entrainement":
        empreinte = empreinte_du_tokenizer_des_jetons(config.dossier_donnees)
    else:
        empreinte = depart.empreinte_du_tokenizer
    if empreinte is not None:
        etat["empreinte_du_tokenizer"] = empreinte
    return etat


def _charger_depart(config: ConfigEntrainement) -> tuple[VersionDeDepart, dict[str, torch.Tensor]]:
    """La version de départ d'un affinage : ce qu'on en retient, et ses poids (float32, processeur).

    Ses dimensions doivent être celles de `config.modele`. L'empreinte de son tokenizer doit être
    celle de l'`index.json` des données quand il en a une (un jeu d'affinage en a une, l'index des
    problèmes du GRPO non) : les jetons du jeu se liraient sinon autrement.
    """
    # Importé ici : `forge.publication` importe `forge.exporter`, qui importe ce paquet.
    from forge.publication import charger_publication

    dossier = config.dossier_depart
    publication = charger_publication(dossier)
    if publication.modele.config != config.modele:
        taille = f"le preset « {config.preset} »" if isinstance(config.preset, str) else "la table [preset]"
        raise ValueError(
            f"La version de départ {publication.version} ({dossier}) a d'autres dimensions que {taille} "
            f"de la configuration : {_decrire_modele(publication.modele.config)} au lieu de "
            f"{_decrire_modele(config.modele)}. Un affinage garde les dimensions de sa version de départ : "
            "mets le preset qui va avec, ou une autre version de départ."
        )
    depart = VersionDeDepart(
        version=publication.version,
        empreinte_des_poids=publication.empreinte_des_poids,
        empreinte_du_tokenizer=empreinte_du_tokenizer(publication.tokenizer),
    )
    du_jeu = empreinte_du_tokenizer_des_jetons(config.dossier_donnees)
    if du_jeu is not None and du_jeu != depart.empreinte_du_tokenizer:
        raise ValueError(
            f"Les données {config.dossier_donnees} ont été préparées avec un autre tokenizer que celui de la "
            f"version de départ {depart.version} : empreinte {du_jeu} dans leur index.json, "
            f"{depart.empreinte_du_tokenizer} pour la version. Refais `forge preparer` avec le tokenizer de ton IA."
        )
    return depart, publication.modele.state_dict()


def _verifier_le_depart(etat: dict, depart: VersionDeDepart, config: ConfigEntrainement) -> None:
    """Refuse de reprendre un affinage depuis une autre version de départ que celle de la sauvegarde.

    Le chemin de `depart` peut changer (c'est un réglage libre) ; la version, elle, se reconnaît à
    son nom et à l'empreinte SHA-256 de ses poids, que la sauvegarde retient.
    """
    avant = (etat.get("depart_version"), etat.get("depart_empreinte"))
    if avant != (depart.version, depart.empreinte_des_poids):
        raise ValueError(
            f"La version de départ a changé depuis la sauvegarde du pas {etat['pas']} : {avant[0]} (poids "
            f"{avant[1]}) alors, {depart.version} (poids {depart.empreinte_des_poids}) dans {config.dossier_depart} "
            "maintenant. Remets la même version de départ pour reprendre, ou change `sortie` pour commencer un "
            "nouvel entraînement."
        )


def entrainer(config: ConfigEntrainement, reprendre: bool = False, arreter_apres: int | None = None) -> dict:
    """Entraîne le modèle décrit par `config` ; renvoie un résumé.

    - `reprendre` : repartir de la dernière sauvegarde de `sortie/sauvegardes` (s'il n'y en a
      pas, l'entraînement part du début). Sans lui, un dossier qui a déjà des sauvegardes est
      refusé (`FileExistsError`) : on ne repart jamais de zéro par mégarde. En reprenant, les
      réglages qui changent le calcul doivent être ceux de la sauvegarde (voir
      `_verifier_sauvegarde` : `jetons_total` peut seulement augmenter, `taux_max` baisser) ;
    - `arreter_apres` : s'arrêter (et sauvegarder) quand le pas atteint ce numéro ; sert aux
      essais et aux tests.

    Le résumé : `pertes` (la perte de chaque pas exécuté pendant CET appel), `pas`,
    `pas_total`, `termine`, `en_pause`, `sauvegarde` (la dernière écrite) et
    `meilleure_perte_val`.

    Ctrl+C met en pause (voir le début du module). Un manque de mémoire sur la carte
    graphique affiche la marche à suivre, puis quitte avec `SystemExit(2)`. Une perte qui
    devient infinie arrête tout SANS sauvegarder, avec `SystemExit(3)`.

    Sur GPU, deux entraînements identiques peuvent différer légèrement (certains calculs de
    la carte additionnent dans un ordre qui varie) ; la reprise, elle, repart exactement du
    point sauvegardé.
    """
    appareil = _verifier_appareil(config)
    manque_de_memoire = False
    try:
        return _entrainer(config, appareil, reprendre, arreter_apres)
    except torch.cuda.OutOfMemoryError:
        manque_de_memoire = True
    # Hors du bloc `except` : l'erreur et les tenseurs qu'elle retenait sont libérés avant
    # de mesurer la mémoire restée libre.
    if manque_de_memoire:
        _signaler_manque_de_memoire(config, appareil)
    raise AssertionError("inatteignable")


def _entrainer(config: ConfigEntrainement, appareil: torch.device, reprendre: bool, arreter_apres: int | None) -> dict:
    methode = METHODES[config.methode]
    sortie = config.dossier_sortie
    sauvegardes = sortie / "sauvegardes"
    chemin_journal = sortie / "journal.jsonl"
    longueur = config.longueur_des_rangees
    pas_total = config.pas_total
    fin = pas_total if arreter_apres is None else min(pas_total, arreter_apres)
    # La mesure de validation qui choisit `meilleur.pt` : la plus petite perte, ou la plus grande réussite.
    mesure_val = "reussite_val" if methode.plus_grand_est_meilleur else "perte_val"

    # 1. Une sauvegarde existe-t-elle ?
    etat = charger_derniere(sauvegardes)
    if etat is not None and not reprendre:
        raise FileExistsError(
            f"{sortie} contient déjà un entraînement (dernière sauvegarde : pas {etat['pas']}). "
            f"Pour le continuer : {_commande_de_reprise(config)}. Pour repartir de zéro : "
            f"supprime ce dossier, ou change `sortie` dans {config.fichier or 'la configuration'}."
        )
    changements_permis = []
    if etat is not None:
        changements_permis = _verifier_sauvegarde(etat, config)
    elif reprendre:
        print(f"Aucune sauvegarde dans {sauvegardes} : l'entraînement part du début.", flush=True)

    # 2. La version de départ d'un affinage : en reprenant, la même que celle de la sauvegarde.
    depart, poids_de_depart = (None, None) if config.depart is None else _charger_depart(config)
    if etat is not None and depart is not None:
        _verifier_le_depart(etat, depart, config)

    # 3. Le modèle et l'optimiseur : poids tirés de la graine, puis, pour un affinage, remplacés
    # par ceux de la version de départ AVANT de créer l'optimiseur.
    if appareil.type == "cpu":
        torch.set_num_threads(fils_disponibles())  # tous les fils que ce processus peut utiliser
    _semer(config.graine)
    modele = Transformer(config.modele).to(appareil)
    if poids_de_depart is not None:
        modele.load_state_dict(poids_de_depart)
        poids_de_depart = None  # la copie sur le processeur ne sert plus
    optimiseur = creer_optimiseur(modele, config, appareil)

    # 4. La méthode se prépare, sur les poids de départ, puis crée ses chargeurs (qui ouvrent les
    # fichiers que `preparer` a pu écrire). Ce qu'elles notent attend l'ouverture du journal.
    pas = 0 if etat is None else etat["pas"]
    notes: list[dict] = []

    def noter(ligne: dict) -> None:
        notes.append({**ligne, "pas": pas})

    try:
        contexte = methode.preparer(config, modele, appareil, noter, depart=depart, reprise=etat is not None)
    except BaseException:
        if notes:  # ce que la méthode a constaté avant d'échouer (le contrôle du GRPO…) reste au journal
            journal = _ouvrir_le_journal(chemin_journal, None if etat is None else pas)
            try:
                for ligne in notes:
                    journal.ecrire(ligne)
            finally:
                journal.fermer()
        raise
    chargeur, validation = methode.creer_chargeurs(config, contexte, noter)
    # La validation relit toujours les mêmes données : elle repart chaque fois de là.
    depart_validation = None if validation is None else validation.etat()

    # … puis l'optimiseur et les chargeurs reprennent là où la sauvegarde les a laissés (refusé
    # avant d'écrire au journal si les données ont changé). Les poids et le hasard, plus bas.
    secondes_avant, meilleure = 0.0, None
    if etat is not None:
        optimiseur.load_state_dict(etat["optimiseur"])
        chargeur.restaurer(etat["chargeur"])
        secondes_avant, meilleure = etat["secondes"], etat["meilleure_perte_val"]

    journal = _ouvrir_le_journal(chemin_journal, None if etat is None else pas)
    try:
        debut = f"Reprise au pas {pas} sur {pas_total}." if pas else f"Début de l'entraînement : {pas_total} pas."
        journal.ecrire({"evenement": "reprise" if pas else "debut", "pas": pas, "message": debut})
        for message in changements_permis:
            journal.ecrire({"evenement": "configuration", "pas": pas, "message": message})
            print(message, flush=True)
        for ligne in notes:
            journal.ecrire(ligne)
        depuis = "" if depart is None else f", depuis la version {depart.version} ({config.dossier_depart})"
        print(
            f"{debut} Modèle de {entier(nombre_parametres(config.modele))} paramètres, "
            f"{entier(config.taille_lot_jetons)} jetons par pas ({config.accumulation} × "
            f"{config.micro_lot} lignes de {longueur}), sur "
            f"{'la carte graphique' if appareil.type == 'cuda' else 'le processeur'}"
            f"{'' if config.methode == 'pre_entrainement' else f', méthode {config.methode}'}{depuis}.\n"
            f"Journal : {chemin_journal}\nSauvegardes : {sauvegardes}\n"
            "Ctrl+C : pause, avec sauvegarde.",
            flush=True,
        )
        if etat is not None:
            modele.load_state_dict(etat["modele"])
            _restaurer_hasard(etat["hasard"])
            etat = None  # sa copie des poids en mémoire ne sert plus
        modele_entraine = _preparer_compilation(
            modele, config, appareil, lambda ligne: journal.ecrire({**ligne, "pas": pas})
        )

        def avertir(message: str) -> None:
            """Un souci qui n'arrête pas l'entraînement (une ancienne sauvegarde restée là)."""
            journal.ecrire({"evenement": "avertissement", "pas": pas, "message": message})

        def sauvegarder_tout() -> Path:
            """La sauvegarde complète du pas `pas` : de quoi reprendre exactement."""
            tout = {
                **_etat_du_modele(config, modele, pas, depart),
                "pas_total": pas_total,
                "jetons_vus": pas * config.taille_lot_jetons,
                "secondes": secondes_avant + (time.perf_counter() - debut_session),
                "meilleure_perte_val": meilleure,
                "optimiseur": optimiseur.state_dict(),
                "chargeur": chargeur.etat(),
                "hasard": _etat_du_hasard(),
            }
            chemin = sauvegarder(sauvegardes, tout, nom_etape(pas), noter=avertir)
            journal.ecrire({"evenement": "sauvegarde", "pas": pas, "fichier": chemin.name})
            return chemin

        # 5. La boucle : un pas, une ligne de journal, parfois une validation ou une sauvegarde.
        pertes: list[float] = []
        derniere_sauvegarde = None
        debut_session = time.perf_counter()
        derniere_ecriture = debut_session
        dernier_affichage = None
        with _Pause() as pause, _sans_mise_en_veille():
            while pas < fin:
                debut_pas = time.perf_counter()
                pas += 1
                taux_du_pas = taux(pas, pas_total, config.taux_max, config.echauffement)
                try:
                    resultat = methode.pas(
                        modele_entraine, optimiseur, chargeur, config, taux_du_pas, appareil, contexte, numero=pas
                    )
                except PerteNonFinie as erreur:
                    # Les poids sont peut-être déjà abîmés : surtout ne rien sauvegarder.
                    journal.ecrire({"evenement": "perte_non_finie", "pas": pas, "message": str(erreur)})
                    print(
                        f"La perte est devenue infinie au pas {pas} : l'entraînement s'arrête sans "
                        "sauvegarder ; reprends depuis la dernière sauvegarde avec un taux_max plus petit.",
                        file=sys.stderr,
                        flush=True,
                    )
                    raise SystemExit(CODE_PERTE_INFINIE) from None
                vitesse = config.taille_lot_jetons / max(time.perf_counter() - debut_pas, 1e-9)
                perte = resultat["perte"]
                pertes.append(perte)
                ligne = {
                    "pas": pas,
                    "jetons_vus": pas * config.taille_lot_jetons,
                    "perte": perte,
                    "taux": taux_du_pas,
                    "jetons_par_seconde": round(vitesse, 1),
                    "secondes": round(secondes_avant + (time.perf_counter() - debut_session), 3),
                    **{cle: valeur for cle, valeur in resultat.items() if cle != "perte"},  # ce que la méthode ajoute
                }
                if validation is not None and (pas % config.evaluation_tous_pas == 0 or pas == pas_total):
                    ligne.update(methode.valider(modele, validation, depart_validation, appareil, config, contexte))
                    mesure = ligne[mesure_val]
                    if meilleure is None or (mesure > meilleure if methode.plus_grand_est_meilleur else mesure < meilleure):
                        meilleure = mesure
                        modele_seul = {**_etat_du_modele(config, modele, pas, depart), mesure_val: meilleure}
                        sauvegarder(sauvegardes, modele_seul, "meilleur.pt", noter=avertir)
                journal.ecrire(ligne)

                maintenant = time.perf_counter()
                if (
                    dernier_affichage is None
                    or maintenant - dernier_affichage >= SECONDES_ENTRE_AFFICHAGES
                    or mesure_val in ligne
                    or pas == fin
                ):
                    dernier_affichage = maintenant
                    restant = (pas_total - pas) * config.taille_lot_jetons / vitesse
                    val = f" · validation {nombre(ligne[mesure_val], 3)}" if mesure_val in ligne else ""
                    print(
                        f"pas {pas}/{pas_total} · perte {nombre(perte, 3)}{val} · "
                        f"taux {scientifique(taux_du_pas)} · "
                        f"{entier(vitesse)} jetons/s · reste ≈ {duree(restant)}",
                        flush=True,
                    )

                minutes = (maintenant - derniere_ecriture) / 60
                if pause.demandee or pas == fin or minutes >= config.sauvegarde_minutes:
                    derniere_sauvegarde = sauvegarder_tout()
                    derniere_ecriture = time.perf_counter()
                if pause.demandee:
                    break

        # 6. Le bilan.
        if pause.demandee:
            journal.ecrire({"evenement": "pause", "pas": pas})
            print(f"Entraînement mis en pause au pas {pas}. Pour reprendre : {_commande_de_reprise(config)}", flush=True)
        elif not pertes:
            print(f"Rien à faire : l'entraînement est déjà au pas {pas} (fin prévue au pas {pas_total}).", flush=True)
        elif pas >= pas_total:
            journal.ecrire({"evenement": "fin", "pas": pas})
            print(f"Entraînement terminé au pas {pas}. Sauvegarde : {derniere_sauvegarde}", flush=True)
        else:
            print(f"Arrêt demandé au pas {pas}. Sauvegarde : {derniere_sauvegarde}", flush=True)
        return {
            "pertes": pertes,
            "pas": pas,
            "pas_total": pas_total,
            "termine": pas >= pas_total,
            "en_pause": pause.demandee,
            "sauvegarde": str(derniere_sauvegarde) if derniere_sauvegarde else None,
            "meilleure_perte_val": meilleure,
        }
    finally:
        journal.fermer()
