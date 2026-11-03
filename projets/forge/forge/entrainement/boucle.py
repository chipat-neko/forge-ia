"""La boucle d'entraînement de « ton IA » : apprendre, noter, sauvegarder, se mettre en pause.

Un entraînement est une suite de pas d'optimisation. À chaque pas (`_pas_d_optimisation`) :

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
"""

import dataclasses
import gc
import importlib.util
import json
import logging
import os
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

from forge.chemins import PlaceInsuffisante, racine_donnees
from forge.entrainement.chargeur import ChargeurJetons
from forge.entrainement.planning import taux
from forge.entrainement.sauvegarde import charger_derniere, est_disque_plein, nom_etape, sauvegarder
from forge.modele import PRESETS, ConfigModele, Transformer, nombre_parametres
from forge.tokenizer.apprentissage import DonneesManquantes

VERSION_DE_LA_SAUVEGARDE = 1

# Nombre de lots lus pour mesurer la perte de validation (moins si `val/` est plus petit).
LOTS_DE_VALIDATION = 20

# Une ligne de suivi à l'écran au plus toutes les 10 secondes (le journal, lui, a chaque pas).
SECONDES_ENTRE_AFFICHAGES = 10


class CompilationImpossible(RuntimeError):
    """`torch.compile` a échoué alors que la configuration l'exige (`compiler = "oui"`)."""


# --- La configuration -----------------------------------------------------------------


def _chemin_sous_la_racine(valeur: str, sous_dossier: str) -> Path:
    """Un chemin absolu est gardé tel quel ; un nom va sous `FORGE_DONNEES/<sous_dossier>/`."""
    chemin = Path(valeur)
    return chemin if chemin.is_absolute() else racine_donnees() / sous_dossier / chemin


@dataclass(frozen=True, kw_only=True)
class ConfigEntrainement:
    """Les réglages d'un entraînement, lus depuis un fichier TOML par `lire_config`.

    - `preset` : la taille du modèle, un nom de `PRESETS` (« mini », « petit »…) ; on peut
      aussi donner une `ConfigModele` (ou, dans le TOML, une table `[preset]`) ;
    - `donnees` : le dossier des jetons, celui de `forge encoder --donnees <nom>` (un nom va
      sous `FORGE_DONNEES/jetons/`, un chemin absolu est gardé tel quel) ;
    - `jetons_total` : combien de jetons lire en tout ; avec `taille_lot_jetons`, il fixe le
      nombre de pas ;
    - `taille_lot_jetons` : jetons vus par pas d'optimisation (le « lot ») ;
    - `micro_lot` : lignes de `longueur_contexte` jetons traitées d'un coup par la carte ; le
      lot est atteint par accumulation. À réduire en cas de manque de mémoire ;
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
    - `fichier` : le fichier TOML lu, rempli par `lire_config` (il sert aux messages).
    """

    preset: str | ConfigModele
    donnees: str
    jetons_total: int
    taille_lot_jetons: int
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
        for nom, minimum in (
            ("jetons_total", 1),
            ("taille_lot_jetons", 1),
            ("micro_lot", 1),
            ("echauffement", 0),
            ("graine", 0),
            ("evaluation_tous_pas", 1),
        ):
            valeur = getattr(self, nom)
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
        par_micro_lot = self.micro_lot * self.modele.longueur_contexte
        if self.taille_lot_jetons % par_micro_lot:
            longueur = self.modele.longueur_contexte
            possibles = [m for m in range(1, self.micro_lot + 1) if self.taille_lot_jetons % (m * longueur) == 0]
            raise ValueError(
                f"taille_lot_jetons ({self.taille_lot_jetons}) doit être un multiple de "
                f"micro_lot × longueur_contexte ({self.micro_lot} × {longueur} = {par_micro_lot}), "
                "pour que chaque pas voie exactement le même nombre de jetons. "
                f"Valeurs de micro_lot possibles, jusqu'à {self.micro_lot} : "
                f"{', '.join(map(str, possibles)) or 'aucune'}."
            )

    @property
    def modele(self) -> ConfigModele:
        """Les dimensions du modèle à entraîner."""
        return PRESETS[self.preset] if isinstance(self.preset, str) else self.preset

    @property
    def accumulation(self) -> int:
        """Nombre de micro-lots par pas d'optimisation."""
        return self.taille_lot_jetons // (self.micro_lot * self.modele.longueur_contexte)

    @property
    def pas_total(self) -> int:
        """Nombre de pas d'optimisation pour lire `jetons_total` jetons (arrondi au-dessus)."""
        return -(-self.jetons_total // self.taille_lot_jetons)

    @property
    def dossier_donnees(self) -> Path:
        return _chemin_sous_la_racine(self.donnees, "jetons")

    @property
    def dossier_sortie(self) -> Path:
        return _chemin_sous_la_racine(self.sortie, "entrainements")


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


def _nombre(valeur: float, decimales: int) -> str:
    """Un nombre à la française : virgule décimale."""
    return f"{valeur:.{decimales}f}".replace(".", ",")


def _entier(valeur: float) -> str:
    """Un entier avec une espace entre les milliers : 52 000."""
    return f"{round(valeur):,}".replace(",", " ")


def _duree(secondes: float) -> str:
    """Une durée lisible : 2 j 3 h, 1 h 05 min, 4 min 10 s, 12 s."""
    secondes = max(0, round(secondes))
    jours, reste = divmod(secondes, 86400)
    heures, reste = divmod(reste, 3600)
    minutes, secondes = divmod(reste, 60)
    if jours:
        return f"{jours} j {heures} h"
    if heures:
        return f"{heures} h {minutes:02d} min"
    if minutes:
        return f"{minutes} min {secondes:02d} s"
    return f"{secondes} s"


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


def _autocast(appareil: torch.device):
    """bf16 sur la carte graphique ; sur le processeur, on reste en 32 bits."""
    return torch.autocast(device_type=appareil.type, dtype=torch.bfloat16, enabled=appareil.type == "cuda")


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
        self._fichier.close()


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
    temporaire = chemin.with_name(chemin.name + ".tmp")
    temporaire.write_text("".join(gardees), encoding="utf-8")
    os.replace(temporaire, chemin)


class _Pause:
    """Pendant l'entraînement, Ctrl+C (et Ctrl+Pause sous Windows) demande une pause.

    Le premier appui lève seulement un drapeau, que la boucle regarde à la fin de chaque pas.
    Un second appui arrête tout de suite (`KeyboardInterrupt`) : le pas en cours est perdu,
    mais la dernière sauvegarde complète reste bonne.
    """

    def __init__(self) -> None:
        self.demandee = False
        self._anciens: dict[int, object] = {}

    def _signal_recu(self, numero, cadre) -> None:
        if self.demandee:
            raise KeyboardInterrupt
        self.demandee = True
        try:
            print(
                "\nPause demandée : je finis le pas en cours, je sauvegarde, puis je m'arrête "
                "(Ctrl+C une seconde fois : arrêt immédiat, sans sauvegarder ce pas).",
                flush=True,
            )
        except (OSError, RuntimeError):
            pass  # l'écran était déjà occupé : le message de pause suivra quand même

    def __enter__(self) -> "_Pause":
        # On ne peut poser un gestionnaire de signal que depuis le fil principal.
        if threading.current_thread() is threading.main_thread():
            for nom in ("SIGINT", "SIGBREAK"):
                numero = getattr(signal, nom, None)
                if numero is not None:
                    self._anciens[numero] = signal.signal(numero, self._signal_recu)
        return self

    def __exit__(self, *erreur) -> None:
        for numero, ancien in self._anciens.items():
            signal.signal(numero, ancien)


# --- Le modèle et l'optimiseur ----------------------------------------------------------


def _creer_optimiseur(modele: nn.Module, config: ConfigEntrainement, appareil: torch.device):
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


def _pas_d_optimisation(
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
    torch.nn.utils.clip_grad_norm_(modele.parameters(), ecretage)
    optimiseur.step()
    return (somme / accumulation).item()


@torch.no_grad()
def _perte_validation(modele: nn.Module, chargeur: ChargeurJetons, depart: dict, n_lots: int, appareil) -> float:
    """Perte moyenne sur `n_lots` lots de validation, toujours les mêmes (depuis `depart`)."""
    chargeur.restaurer(depart)
    modele.eval()
    somme = torch.zeros((), device=appareil)
    for _ in range(n_lots):
        x, y = chargeur.lot()
        with _autocast(appareil):
            _, perte = modele(x.to(appareil), y.to(appareil))
        somme += perte.float()
    modele.train()
    return (somme / n_lots).item()


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


def _verifier_sauvegarde(etat: dict, config: ConfigEntrainement) -> None:
    """Refuse de reprendre avec un autre modèle que celui de la sauvegarde."""
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


def _signaler_manque_de_memoire(config: ConfigEntrainement, appareil: torch.device) -> None:
    """Le message d'un manque de mémoire sur la carte graphique, puis l'arrêt (code 2)."""
    libre = "inconnue"
    if appareil.type == "cuda":
        gc.collect()
        torch.cuda.empty_cache()  # rend à la carte ce que cet entraînement gardait en réserve
        try:
            octets_libres, octets_total = torch.cuda.mem_get_info()
            libre = f"{_nombre(octets_libres / 1024**3, 1)} Go sur {_nombre(octets_total / 1024**3, 1)} Go"
        except RuntimeError:
            pass
    print(
        f"La carte graphique manque de mémoire pour micro_lot = {config.micro_lot}.\n"
        f"Mémoire libre sur la carte graphique : {libre} (Windows et les programmes ouverts "
        "en prennent une partie).\n"
        f"Réduis micro_lot dans {config.fichier or '<fichier>'}, ferme les jeux ou logiciels 3D "
        "ouverts, puis relance avec --reprendre.",
        file=sys.stderr,
        flush=True,
    )
    raise SystemExit(2)


def _etat_du_modele(config: ConfigEntrainement, modele: nn.Module, pas: int) -> dict:
    """Ce qu'il faut pour reconstruire et utiliser le modèle : ses poids et sa configuration."""
    return {
        "version": VERSION_DE_LA_SAUVEGARDE,
        "pas": pas,
        "modele": modele.state_dict(),
        "config": dataclasses.asdict(config),
        "config_modele": dataclasses.asdict(config.modele),
    }


def entrainer(config: ConfigEntrainement, reprendre: bool = False, arreter_apres: int | None = None) -> dict:
    """Entraîne le modèle décrit par `config` ; renvoie un résumé.

    - `reprendre` : repartir de la dernière sauvegarde de `sortie/sauvegardes` (s'il n'y en a
      pas, l'entraînement part du début). Sans lui, un dossier qui a déjà des sauvegardes est
      refusé (`FileExistsError`) : on ne repart jamais de zéro par mégarde ;
    - `arreter_apres` : s'arrêter (et sauvegarder) quand le pas atteint ce numéro ; sert aux
      essais et aux tests.

    Le résumé : `pertes` (la perte de chaque pas exécuté pendant CET appel), `pas`,
    `pas_total`, `termine`, `en_pause`, `sauvegarde` (la dernière écrite) et
    `meilleure_perte_val`.

    Ctrl+C met en pause (voir le début du module). Un manque de mémoire sur la carte
    graphique affiche la marche à suivre, puis quitte avec `SystemExit(2)`.

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
    sortie = config.dossier_sortie
    sauvegardes = sortie / "sauvegardes"
    chemin_journal = sortie / "journal.jsonl"
    longueur = config.modele.longueur_contexte
    pas_total = config.pas_total
    fin = pas_total if arreter_apres is None else min(pas_total, arreter_apres)

    # 1. Une sauvegarde existe-t-elle ?
    etat = charger_derniere(sauvegardes)
    if etat is not None and not reprendre:
        raise FileExistsError(
            f"{sortie} contient déjà un entraînement (dernière sauvegarde : pas {etat['pas']}). "
            f"Pour le continuer : {_commande_de_reprise(config)}. Pour repartir de zéro : "
            f"supprime ce dossier, ou change `sortie` dans {config.fichier or 'la configuration'}."
        )
    if etat is not None:
        _verifier_sauvegarde(etat, config)
    elif reprendre:
        print(f"Aucune sauvegarde dans {sauvegardes} : l'entraînement part du début.", flush=True)

    # 2. Le modèle, l'optimiseur et les données, tirés de la graine…
    if appareil.type == "cpu":
        torch.set_num_threads(os.cpu_count() or 1)  # tous les fils du processeur
    _semer(config.graine)
    modele = Transformer(config.modele).to(appareil)
    optimiseur = _creer_optimiseur(modele, config, appareil)
    chargeur = ChargeurJetons(config.dossier_donnees / "train", longueur, config.micro_lot, config.graine)
    validation, depart_validation, lots_validation, sans_validation = None, None, 0, ""
    try:
        validation = ChargeurJetons(config.dossier_donnees / "val", longueur, config.micro_lot, config.graine)
        depart_validation = validation.etat()  # la validation relit toujours les mêmes lots
        lots_validation = min(LOTS_DE_VALIDATION, max(1, validation.morceaux // config.micro_lot))
    except (DonneesManquantes, ValueError) as erreur:
        sans_validation = str(erreur)

    # … ou repris exactement là où la sauvegarde les a laissés.
    pas, secondes_avant, meilleure = 0, 0.0, None
    if etat is not None:
        modele.load_state_dict(etat["modele"])
        optimiseur.load_state_dict(etat["optimiseur"])
        chargeur.restaurer(etat["chargeur"])
        _restaurer_hasard(etat["hasard"])
        pas, secondes_avant, meilleure = etat["pas"], etat["secondes"], etat["meilleure_perte_val"]
        _couper_journal(chemin_journal, pas)
        etat = None  # sa copie des poids en mémoire ne sert plus
    else:
        sortie.mkdir(parents=True, exist_ok=True)
        chemin_journal.unlink(missing_ok=True)  # celui d'un essai qui n'a rien sauvegardé

    journal = _Journal(chemin_journal)
    try:
        debut = f"Reprise au pas {pas} sur {pas_total}." if pas else f"Début de l'entraînement : {pas_total} pas."
        journal.ecrire({"evenement": "reprise" if pas else "debut", "pas": pas, "message": debut})
        if validation is None:
            journal.ecrire(
                {"evenement": "validation", "pas": pas, "message": f"Pas de perte de validation : {sans_validation}"}
            )
        print(
            f"{debut} Modèle de {_entier(nombre_parametres(config.modele))} paramètres, "
            f"{_entier(config.taille_lot_jetons)} jetons par pas ({config.accumulation} × "
            f"{config.micro_lot} lignes de {longueur}), sur "
            f"{'la carte graphique' if appareil.type == 'cuda' else 'le processeur'}.\n"
            f"Journal : {chemin_journal}\nSauvegardes : {sauvegardes}\n"
            "Ctrl+C : pause, avec sauvegarde.",
            flush=True,
        )
        modele_entraine = _preparer_compilation(
            modele, config, appareil, lambda ligne: journal.ecrire({**ligne, "pas": pas})
        )

        def sauvegarder_tout() -> Path:
            """La sauvegarde complète du pas `pas` : de quoi reprendre exactement."""
            tout = {
                **_etat_du_modele(config, modele, pas),
                "pas_total": pas_total,
                "jetons_vus": pas * config.taille_lot_jetons,
                "secondes": secondes_avant + (time.perf_counter() - debut_session),
                "meilleure_perte_val": meilleure,
                "optimiseur": optimiseur.state_dict(),
                "chargeur": chargeur.etat(),
                "hasard": _etat_du_hasard(),
            }
            chemin = sauvegarder(sauvegardes, tout, nom_etape(pas))
            journal.ecrire({"evenement": "sauvegarde", "pas": pas, "fichier": chemin.name})
            return chemin

        # 3. La boucle : un pas, une ligne de journal, parfois une validation ou une sauvegarde.
        pertes: list[float] = []
        derniere_sauvegarde = None
        debut_session = time.perf_counter()
        derniere_ecriture = debut_session
        dernier_affichage = None
        with _Pause() as pause:
            while pas < fin:
                debut_pas = time.perf_counter()
                pas += 1
                taux_du_pas = taux(pas, pas_total, config.taux_max, config.echauffement)
                perte = _pas_d_optimisation(
                    modele_entraine, optimiseur, chargeur, config.accumulation, taux_du_pas, config.ecretage, appareil
                )
                vitesse = config.taille_lot_jetons / max(time.perf_counter() - debut_pas, 1e-9)
                pertes.append(perte)
                ligne = {
                    "pas": pas,
                    "jetons_vus": pas * config.taille_lot_jetons,
                    "perte": perte,
                    "taux": taux_du_pas,
                    "jetons_par_seconde": round(vitesse, 1),
                    "secondes": round(secondes_avant + (time.perf_counter() - debut_session), 3),
                }
                if validation is not None and (pas % config.evaluation_tous_pas == 0 or pas == pas_total):
                    ligne["perte_val"] = _perte_validation(
                        modele, validation, depart_validation, lots_validation, appareil
                    )
                    if meilleure is None or ligne["perte_val"] < meilleure:
                        meilleure = ligne["perte_val"]
                        modele_seul = {**_etat_du_modele(config, modele, pas), "perte_val": meilleure}
                        sauvegarder(sauvegardes, modele_seul, "meilleur.pt")
                journal.ecrire(ligne)

                maintenant = time.perf_counter()
                if (
                    dernier_affichage is None
                    or maintenant - dernier_affichage >= SECONDES_ENTRE_AFFICHAGES
                    or "perte_val" in ligne
                    or pas == fin
                ):
                    dernier_affichage = maintenant
                    restant = (pas_total - pas) * config.taille_lot_jetons / vitesse
                    val = f" · validation {_nombre(ligne['perte_val'], 3)}" if "perte_val" in ligne else ""
                    print(
                        f"pas {pas}/{pas_total} · perte {_nombre(perte, 3)}{val} · "
                        f"taux {f'{taux_du_pas:.1e}'.replace('.', ',')} · "
                        f"{_entier(vitesse)} jetons/s · reste ≈ {_duree(restant)}",
                        flush=True,
                    )

                minutes = (maintenant - derniere_ecriture) / 60
                if pause.demandee or pas == fin or minutes >= config.sauvegarde_minutes:
                    derniere_sauvegarde = sauvegarder_tout()
                    derniere_ecriture = time.perf_counter()
                if pause.demandee:
                    break

        # 4. Le bilan.
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
