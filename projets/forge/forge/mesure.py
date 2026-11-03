"""Mesurer la vitesse d'entraînement de « ton IA » sur la carte graphique et sur le processeur.

Avant un entraînement qui dure des heures, on fait un essai chronométré : combien de jetons
(de morceaux de mots) le modèle apprend-il par seconde, avec quelle mémoire, et sur quel
appareil ? De là on déduit la durée de tout l'entraînement et la place qu'il prend sur le disque.

Ce que l'on chronomètre est **exactement le pas d'entraînement de la boucle** :
`forge.entrainement.boucle._pas_d_optimisation` (calcul de la perte, `backward`, écrêtage des
gradients, pas d'AdamW), avec les mêmes calculs en `bfloat16` sur la carte graphique, le même
optimiseur. Seules les données diffèrent : des jetons tirés au hasard, de la forme exacte de
ceux du chargeur (`micro_lot` lignes de `longueur_contexte` jetons). La vitesse d'un pas ne
dépend pas des valeurs des jetons, seulement de leur nombre ; on n'a donc pas besoin de
corpus pour mesurer. Tout se passe en mode immédiat : `torch.compile` n'est pas utilisé
(il manque `triton` sous Windows), comme dans l'entraînement réel de ce PC.

Une mesure sur le processeur utilise **tous les fils** (`os.cpu_count()`, soit 16 sur le
Ryzen 7 9800X3D : 8 cœurs, 2 fils chacun), et le prouve : la charge de chaque cœur logique
pendant la mesure est relevée avec `psutil`, ainsi que le nombre de cœurs que le processus
occupe en moyenne.

Les « Go » de ce module valent 1024³ octets (comme l'Explorateur de Windows).
"""

import gc
import os
import shutil
import subprocess
import time
from collections.abc import Callable

import psutil
import torch

from forge.entrainement.boucle import ConfigEntrainement, _creer_optimiseur, _pas_d_optimisation
from forge.modele import PRESETS, ConfigModele, Transformer, nombre_parametres

_OCTETS_PAR_GO = 1024**3

# La cible de la forge : 20 jetons vus par paramètre du modèle (le rapport « optimal » de
# Chinchilla). Un modèle de 100 millions de paramètres voit donc 2 milliards de jetons.
JETONS_PAR_PARAMETRE = 20

# Place sur le disque, par jeton ou par paramètre.
OCTETS_PAR_JETON = 2  # les jetons encodés sont des `uint16`
OCTETS_TEXTE_PAR_JETON = 4.36  # le texte brut qui les produit (docs/mesures/tokenizer-ton-ia-v1.md)
# Sauvegardes : 3 fichiers de 16 octets par paramètre, une borne haute prudente. Mesuré : un
# `etape-*.pt` fait 12 octets par paramètre (poids 4 + deux moyennes d'AdamW 8) et `meilleur.pt` 4 ;
# la boucle garde 2 `etape-*.pt` et `meilleur.pt` (28 octets par paramètre), et un 3e `etape-*.pt`
# pendant son écriture (40).
FICHIERS_DE_SAUVEGARDE = 3
OCTETS_PAR_PARAMETRE_ET_FICHIER = 16

# Taux d'apprentissage de la mesure : sans importance pour la vitesse, assez petit pour que la
# perte reste finie sur des jetons tirés au hasard.
_TAUX = 1e-4

# Une carte graphique est « occupée » si elle travaille déjà à plus de 30 % : la mesure
# serait fausse, et on le dit au lieu de mesurer.
SEUIL_GPU_OCCUPE = 30.0


class GpuOccupe(RuntimeError):
    """La carte graphique travaille déjà pour un autre programme : la mesurer donnerait des chiffres faux."""


def cuda_disponible() -> bool:
    """PyTorch voit-il une carte graphique NVIDIA ?"""
    return torch.cuda.is_available()


# --- Les calculs : durée et place sur le disque -----------------------------------------------


def estimer(config: ConfigModele, jetons_par_seconde: float, jetons: int | None = None) -> float:
    """Durée en heures pour apprendre `jetons` jetons à `jetons_par_seconde`.

    Sans `jetons`, on prend la cible de la forge : `JETONS_PAR_PARAMETRE` (20) jetons par
    paramètre de `config`.
    """
    if not jetons_par_seconde > 0:
        raise ValueError(
            f"jetons_par_seconde vaut {jetons_par_seconde!r} : il faut un débit plus grand que 0. "
            "Relance la mesure : un débit nul veut dire qu'elle n'a pas tourné."
        )
    if jetons is None:
        jetons = JETONS_PAR_PARAMETRE * nombre_parametres(config)
    return jetons / jetons_par_seconde / 3600


def estimer_disque(config: ConfigModele, jetons: int | None = None) -> dict:
    """La place sur le disque d'un entraînement de `jetons` jetons (20 par paramètre sans `jetons`).

    Quatre postes, en Go (1024³ octets) :

    - `jetons_go` : les jetons encodés, `OCTETS_PAR_JETON` (2) octets chacun ;
    - `texte_brut_go` : le texte téléchargé qui les produit, `OCTETS_TEXTE_PAR_JETON` (4,36)
      octets par jeton. Il est effacé une fois l'encodage fini, mais il faut la place pour
      lui et pour les jetons en même temps ;
    - `sauvegardes_go` : les sauvegardes d'entraînement, `FICHIERS_DE_SAUVEGARDE` (3) fichiers
      de `OCTETS_PAR_PARAMETRE_ET_FICHIER` (16) octets par paramètre. C'est une borne haute
      prudente : un fichier `etape-*.pt` écrit 12 octets par paramètre (poids et AdamW) ;
    - `pic_go` : la somme des trois, le besoin au pire moment (texte brut, jetons et sauvegardes
      présents ensemble).

    Deux chiffres de plus, pour l'ordre réel des travaux (télécharger, encoder, effacer le texte,
    puis entraîner) : `regime_etabli_go` est ce qui reste une fois le texte brut effacé (jetons
    et sauvegardes) ; `pic_sequentiel_go` est le plus grand des deux moments, « texte brut et
    jetons » (à la fin de l'encodage) et « jetons et sauvegardes » (pendant l'entraînement).
    """
    parametres = nombre_parametres(config)
    if jetons is None:
        jetons = JETONS_PAR_PARAMETRE * parametres
    jetons_go = jetons * OCTETS_PAR_JETON / _OCTETS_PAR_GO
    texte_brut_go = jetons * OCTETS_TEXTE_PAR_JETON / _OCTETS_PAR_GO
    sauvegardes_go = parametres * FICHIERS_DE_SAUVEGARDE * OCTETS_PAR_PARAMETRE_ET_FICHIER / _OCTETS_PAR_GO
    return {
        "parametres": parametres,
        "jetons": jetons,
        "jetons_go": jetons_go,
        "texte_brut_go": texte_brut_go,
        "sauvegardes_go": sauvegardes_go,
        "pic_go": jetons_go + texte_brut_go + sauvegardes_go,
        "regime_etabli_go": jetons_go + sauvegardes_go,
        "pic_sequentiel_go": max(jetons_go + texte_brut_go, jetons_go + sauvegardes_go),
    }


# --- Les données de la mesure et la sonde de charge ----------------------------------------------


class _ChargeurAleatoire:
    """Un faux chargeur : des jetons tirés au hasard, de la forme exacte de `ChargeurJetons.lot()`.

    `lot()` rend `(x, y)`, deux tenseurs `int64` de `[micro_lot, longueur_contexte]` (la cible
    est l'entrée décalée d'un jeton), sur le processeur : la boucle les envoie ensuite sur la
    carte, comme avec le vrai chargeur.
    """

    def __init__(self, config: ConfigModele, micro_lot: int) -> None:
        self._config = config
        self._micro_lot = micro_lot
        self._hasard = torch.Generator().manual_seed(0)

    def lot(self) -> tuple[torch.Tensor, torch.Tensor]:
        morceaux = torch.randint(
            0,
            self._config.taille_vocabulaire,
            (self._micro_lot, self._config.longueur_contexte + 1),
            generator=self._hasard,
        )
        return morceaux[:, :-1].contiguous(), morceaux[:, 1:].contiguous()


def _temps_total(temps) -> float:
    """Somme des temps d'un cœur (`psutil.cpu_times`), sans compter deux fois les champs « invité » de Linux."""
    return sum(getattr(temps, champ) for champ in temps._fields if champ not in ("guest", "guest_nice"))


class _SondeCharge:
    """Relève la charge de chaque cœur logique, et celle du processus, entre sa création et `terminer()`.

    Pour chaque cœur, la charge est `100 × (1 − temps au repos / temps écoulé)` sur toute la
    fenêtre : la moyenne exacte pendant la mesure, sans fil qui l'échantillonne (qui prendrait
    lui-même du processeur). Le processus, lui, est suivi par son temps de calcul : en divisant
    par la durée, on obtient le nombre de cœurs qu'il occupe en moyenne (16 si tous les fils
    de ce PC travaillent sans cesse).
    """

    def __init__(self) -> None:
        self._processus = psutil.Process()
        self._coeurs_avant = psutil.cpu_times(percpu=True)
        temps = self._processus.cpu_times()
        self._calcul_avant = temps.user + temps.system
        self._debut = time.perf_counter()

    def terminer(self) -> tuple[list[float], float]:
        duree = time.perf_counter() - self._debut
        charges = []
        for avant, apres in zip(self._coeurs_avant, psutil.cpu_times(percpu=True), strict=True):
            ecoule = _temps_total(apres) - _temps_total(avant)
            repos = apres.idle - avant.idle
            charges.append(round(100 * min(1.0, max(0.0, 1 - repos / ecoule)), 1) if ecoule > 0 else 0.0)
        temps = self._processus.cpu_times()
        coeurs_occupes = (temps.user + temps.system - self._calcul_avant) / duree if duree > 0 else 0.0
        return charges, round(coeurs_occupes, 2)


# --- La mesure ---------------------------------------------------------------------------------


def mesurer(
    config: ConfigModele,
    appareil: str,
    micro_lot: int,
    pas: int = 20,
    fils: int | None = None,
    *,
    accumulation: int = 1,
    echauffement: int = 2,
    secondes_max: float | None = None,
) -> dict:
    """Chronomètre `pas` pas d'entraînement de `config` sur `appareil` (« cuda » ou « cpu »).

    - `micro_lot` : lignes de `longueur_contexte` jetons traitées d'un coup ;
    - `pas` : nombre de pas chronométrés (après `echauffement` pas non comptés, 2 par défaut :
      le premier pas alloue la mémoire et prépare les noyaux de calcul, il est plus lent) ;
    - `fils` : sur le processeur, nombre de fils de calcul (tous, `os.cpu_count()`, par défaut).
      Sans effet sur la carte graphique ;
    - `accumulation` : micro-lots par pas d'optimisation (1 par défaut) ;
    - `secondes_max` : si la mesure dure déjà plus que ça, on s'arrête avant `pas` (au moins
      1 pas est toujours mesuré) : sur le processeur, un grand modèle fait un pas en dizaines
      de secondes.

    Renvoie un dictionnaire : `jetons_par_seconde` ; `memoire_max_go` (pic de mémoire occupée
    par les tenseurs sur la carte graphique, `None` sur le processeur) ; `fils_utilises` (fils
    de calcul de PyTorch pendant la mesure) ; `charge_par_coeur` (charge moyenne en %, un
    nombre par cœur logique du PC, pendant la mesure) et `charge_moyenne` ; `coeurs_occupes`
    (cœurs que le processus occupe en moyenne) ; puis `pas_mesures`, `jetons_mesures`,
    `secondes`, `echauffement`, `micro_lot`, `accumulation`, `appareil` et `parametres`.

    Ne laisse derrière elle ni modèle en mémoire ni réglage de fils modifié. Sur la carte
    graphique, un manque de mémoire lève `torch.cuda.OutOfMemoryError`.
    """
    if appareil not in ("cuda", "cpu"):
        raise ValueError(f'appareil vaut {appareil!r} : écris "cuda" (carte graphique) ou "cpu".')
    for nom, valeur, minimum in (
        ("micro_lot", micro_lot, 1),
        ("pas", pas, 1),
        ("accumulation", accumulation, 1),
        ("echauffement", echauffement, 0),
    ):
        if not isinstance(valeur, int) or isinstance(valeur, bool) or valeur < minimum:
            raise ValueError(f"{nom} vaut {valeur!r} : il faut un nombre entier d'au moins {minimum}.")
    if appareil == "cuda" and not cuda_disponible():
        raise ValueError(
            'appareil = "cuda", mais PyTorch ne voit aucune carte graphique NVIDIA. Lance la '
            'commande avec `uv run --extra gpu …`, ou mesure sur le processeur ("cpu").'
        )
    peripherique = torch.device(appareil)
    fils_avant = torch.get_num_threads()
    if appareil == "cpu":
        torch.set_num_threads(fils or os.cpu_count() or 1)  # tous les fils du processeur
    try:
        return _mesurer(config, peripherique, micro_lot, pas, accumulation, echauffement, secondes_max)
    finally:
        torch.set_num_threads(fils_avant)


def _mesurer(
    config: ConfigModele,
    appareil: torch.device,
    micro_lot: int,
    pas: int,
    accumulation: int,
    echauffement: int,
    secondes_max: float | None,
) -> dict:
    sur_cuda = appareil.type == "cuda"
    fils_utilises = torch.get_num_threads()
    # La configuration d'entraînement ne sert qu'à construire l'optimiseur comme la boucle le fait.
    reglages = ConfigEntrainement(
        preset=config,
        donnees="-",
        jetons_total=accumulation * micro_lot * config.longueur_contexte,
        taille_lot_jetons=accumulation * micro_lot * config.longueur_contexte,
        micro_lot=micro_lot,
        taux_max=_TAUX,
        echauffement=0,
        evaluation_tous_pas=1,
        appareil=appareil.type,
        compiler="non",
        sortie="-",
    )
    if sur_cuda:
        gc.collect()
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
    torch.manual_seed(0)
    modele = Transformer(config).to(appareil)
    optimiseur = _creer_optimiseur(modele, reglages, appareil)
    chargeur = _ChargeurAleatoire(config, micro_lot)

    def un_pas() -> float:
        return _pas_d_optimisation(modele, optimiseur, chargeur, accumulation, _TAUX, reglages.ecretage, appareil)

    try:
        for _ in range(echauffement):
            un_pas()
        if sur_cuda:
            torch.cuda.synchronize()
        sonde = _SondeCharge()
        debut = time.perf_counter()
        pas_mesures = 0
        while pas_mesures < pas:
            un_pas()
            pas_mesures += 1
            if secondes_max is not None and time.perf_counter() - debut >= secondes_max:
                break
        if sur_cuda:
            torch.cuda.synchronize()
        secondes = time.perf_counter() - debut
        charge_par_coeur, coeurs_occupes = sonde.terminer()
        memoire_max_go = torch.cuda.max_memory_allocated() / _OCTETS_PAR_GO if sur_cuda else None
    finally:
        del un_pas, modele, optimiseur, chargeur
        if sur_cuda:
            gc.collect()
            torch.cuda.empty_cache()
    jetons_mesures = pas_mesures * accumulation * micro_lot * config.longueur_contexte
    return {
        "appareil": appareil.type,
        "parametres": nombre_parametres(config),
        "micro_lot": micro_lot,
        "accumulation": accumulation,
        "echauffement": echauffement,
        "pas_mesures": pas_mesures,
        "jetons_mesures": jetons_mesures,
        "secondes": secondes,
        "jetons_par_seconde": jetons_mesures / secondes,
        "memoire_max_go": memoire_max_go,
        "fils_utilises": fils_utilises,
        "charge_par_coeur": charge_par_coeur,
        "charge_moyenne": round(sum(charge_par_coeur) / len(charge_par_coeur), 1) if charge_par_coeur else 0.0,
        "coeurs_occupes": coeurs_occupes,
    }


# --- Le plus grand micro-lot qui tient sur la carte graphique ---------------------------------------


def plus_grand_micro_lot(tient: Callable[[int], bool], maximum: int = 256) -> int:
    """Le plus grand `micro_lot` (au plus `maximum`) pour lequel `tient(micro_lot)` est vrai.

    On essaie 1, 2, 4, 8… tant que ça tient (le premier qui ne tient pas, ou le dépassement du
    maximum, arrête), puis on affine par dichotomie entre le dernier qui tient et le premier
    qui ne tient pas. Renvoie 0 si même 1 ne tient pas.
    """
    tient_jusqu_ici, ne_tient_pas = 0, maximum + 1
    essai = 1
    while essai <= maximum:
        if tient(essai):
            tient_jusqu_ici, essai = essai, essai * 2
        else:
            ne_tient_pas = essai
            break
    while ne_tient_pas - tient_jusqu_ici > 1:
        milieu = (tient_jusqu_ici + ne_tient_pas) // 2
        if tient(milieu):
            tient_jusqu_ici = milieu
        else:
            ne_tient_pas = milieu
    return tient_jusqu_ici


def limiter_memoire_gpu(marge_go: float = 1.0) -> float:
    """Interdit à ce processus de prendre les `marge_go` derniers Go de la carte ; renvoie la mémoire libre (Go).

    Sans cela, le pilote de Windows peut laisser un programme dépasser la mémoire de la carte
    en la complétant avec la mémoire de l'ordinateur : pas d'erreur, mais tout devient très
    lent, et la recherche du plus grand micro-lot serait faussée. Avec la limite, un
    micro-lot trop gros donne un vrai `OutOfMemoryError`, et il reste ~1 Go libre pour Windows
    et les autres programmes.
    """
    # Un petit calcul d'abord : il charge les bibliothèques de calcul de la carte (cuBLAS…),
    # qui prennent leur part de mémoire avant qu'on ne mesure ce qui reste libre.
    essai = torch.ones((64, 64), device="cuda", dtype=torch.bfloat16)
    (essai @ essai).sum().item()
    del essai
    torch.cuda.empty_cache()
    octets_libres, octets_total = torch.cuda.mem_get_info()
    autorise = max(0.0, octets_libres - marge_go * _OCTETS_PAR_GO)
    torch.cuda.set_per_process_memory_fraction(min(1.0, autorise / octets_total))
    return octets_libres / _OCTETS_PAR_GO


def micro_lot_gpu(config: ConfigModele, marge_go: float = 1.0, maximum: int = 256) -> int:
    """Le plus grand micro-lot qui fait 3 pas sur la carte graphique en laissant `marge_go` Go libres.

    Appelle `limiter_memoire_gpu(marge_go)` d'abord : la limite reste en place ensuite, pour que
    la mesure du débit se fasse dans les mêmes conditions que la recherche.

    Chaque essai accumule 2 micro-lots par pas : à partir du deuxième, les gradients du premier
    occupent déjà la mémoire pendant que le modèle calcule. C'est le cas de tout vrai
    entraînement, et il demande plus de mémoire qu'un seul micro-lot par pas (jusqu'à 2 Go de
    plus pour 433 millions de paramètres) : sans cet essai, le micro-lot trouvé pourrait
    manquer de mémoire dans l'entraînement.
    """
    limiter_memoire_gpu(marge_go)

    def tient(micro_lot: int) -> bool:
        manque_de_memoire = False
        try:
            mesurer(config, "cuda", micro_lot, pas=3, echauffement=0, accumulation=2)
        except torch.cuda.OutOfMemoryError:
            manque_de_memoire = True
        # Hors du bloc `except` : l'erreur, et les tenseurs qu'elle retenait, sont libérés avant l'essai suivant.
        gc.collect()
        torch.cuda.empty_cache()
        return not manque_de_memoire

    return plus_grand_micro_lot(tient, maximum)


# --- L'état de la machine avant de mesurer -------------------------------------------------------


def lire_etat_gpu(texte: str) -> dict:
    """Lit une ligne de `nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits`."""
    utilisation, utilisee, totale = (float(partie) for partie in texte.strip().splitlines()[0].split(","))
    return {
        "utilisation_pct": utilisation,
        "memoire_utilisee_go": utilisee / 1024,
        "memoire_totale_go": totale / 1024,
    }


def etat_gpu(echantillons: int = 4, pause: float = 0.5) -> dict | None:
    """L'état de la carte graphique d'après `nvidia-smi` : utilisation (maximum sur plusieurs relevés) et mémoire.

    Renvoie `None` si `nvidia-smi` est introuvable ou muet : l'état est alors inconnu.
    """
    etats = []
    for i in range(echantillons):
        try:
            sortie = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=15,
                check=True,
            ).stdout
            etats.append(lire_etat_gpu(sortie))
        except (OSError, subprocess.SubprocessError, ValueError, IndexError):
            return None
        if i + 1 < echantillons:
            time.sleep(pause)
    return {**etats[-1], "utilisation_pct": max(etat["utilisation_pct"] for etat in etats)}


def gpu_occupe(etat: dict | None) -> str | None:
    """Un message français si la carte travaille déjà trop pour qu'on la mesure, sinon `None`."""
    if etat is not None and etat["utilisation_pct"] >= SEUIL_GPU_OCCUPE:
        return (
            f"La carte graphique est occupée par un autre programme ({etat['utilisation_pct']:.0f} % "
            f"d'utilisation, {etat['memoire_utilisee_go']:.1f} Go de mémoire prise sur "
            f"{etat['memoire_totale_go']:.1f} Go) : la mesure serait fausse. Ferme le jeu, la "
            "vidéo ou le logiciel 3D qui s'en sert, puis relance `python -m forge mesurer`."
        )
    return None



def charge_au_repos(duree: float = 2.0) -> float:
    """Charge moyenne de tous les cœurs logiques pendant `duree` secondes, avant la mesure (en %)."""
    return psutil.cpu_percent(interval=duree)


# --- Toute la mesure : les presets, sur la carte et sur le processeur -------------------------------


def mesurer_presets(
    noms: list[str],
    pas: int = 20,
    cpu_secondes: float = 120.0,
    cpu_micro_lot: int = 2,
    gpu_accumulation: int = 8,
    journal: Callable[[str], None] = lambda message: None,
) -> dict:
    """Mesure chaque preset de `noms` sur la carte graphique (si elle est libre) et sur le processeur.

    Sur la carte : micro-lot le plus grand qui tient (`micro_lot_gpu`), puis le débit sur `pas`
    pas de `gpu_accumulation` micro-lots chacun, pour ce micro-lot (clé `gpu_max`) et pour
    toutes les puissances de 2 en dessous (clé `gpu_balayage`, indexée par micro-lot). Le plus
    grand micro-lot n'est pas toujours le plus rapide (voir `docs/mesures/entrainement-2026-11.md`) :
    la clé `gpu` est le résultat du micro-lot le plus rapide, celui qui sert aux durées.
    L'accumulation compte : l'écrêtage des gradients et le pas d'AdamW prennent le même temps
    quel que soit le lot, et pèsent (jusqu'à 14 % pour 433 millions de paramètres) s'ils ne
    servent qu'un seul micro-lot, alors qu'un vrai entraînement en accumule des dizaines.
    Sur le processeur : `cpu_micro_lot` lignes, tous les fils, au plus `cpu_secondes` secondes
    de mesure.

    Renvoie `{"machine": {...}, "presets": {nom: {...}}}`. Sans carte graphique, les clés `gpu`,
    `gpu_max` et `gpu_balayage` valent `None` et `machine["gpu_message"]` dit pourquoi. Si la
    carte est déjà occupée par un autre programme, `GpuOccupe` est levée avant toute mesure.
    """
    machine = {
        "coeurs_logiques": os.cpu_count(),
        "coeurs_physiques": psutil.cpu_count(logical=False),
        "ram_go": round(psutil.virtual_memory().total / _OCTETS_PAR_GO, 1),
        "torch": torch.__version__,
        "compilation": "non : mode immédiat (triton absent sous Windows)",
        "charge_au_repos_pct": charge_au_repos(),
        "disque_libre_go": round(shutil.disk_usage(_dossier_des_donnees()).free / _OCTETS_PAR_GO, 1),
    }
    journal(f"Charge du processeur au repos : {machine['charge_au_repos_pct']:.0f} %.")
    mesure_gpu = cuda_disponible()
    if mesure_gpu:
        proprietes = torch.cuda.get_device_properties(0)
        machine["gpu"] = proprietes.name
        machine["gpu_memoire_totale_go"] = round(proprietes.total_memory / _OCTETS_PAR_GO, 2)
        machine["gpu_etat_au_depart"] = etat_gpu()
        message = gpu_occupe(machine["gpu_etat_au_depart"])
        if message:
            raise GpuOccupe(message)
        machine["gpu_libre_au_depart_go"] = round(limiter_memoire_gpu(1.0), 2)
        journal(f"Carte graphique : {machine['gpu']}, {machine['gpu_libre_au_depart_go']} Go libres au départ.")
    else:
        machine["gpu_message"] = "PyTorch ne voit aucune carte graphique NVIDIA : pas de mesure sur la carte."
        journal(machine["gpu_message"])

    try:
        resultats = _mesurer_les_tailles(noms, pas, cpu_secondes, cpu_micro_lot, gpu_accumulation, mesure_gpu, journal)
    finally:
        if mesure_gpu:
            torch.cuda.set_per_process_memory_fraction(1.0)  # rend toute la carte à ce processus
    return {"machine": machine, "presets": resultats}


def _mesurer_les_tailles(
    noms: list[str],
    pas: int,
    cpu_secondes: float,
    cpu_micro_lot: int,
    gpu_accumulation: int,
    mesure_gpu: bool,
    journal: Callable[[str], None],
) -> dict:
    """Le corps de `mesurer_presets` : chaque taille, sur la carte (si `mesure_gpu`) puis sur le processeur."""
    resultats = {}
    for nom in noms:
        config = PRESETS[nom]
        ligne: dict = {"parametres": nombre_parametres(config), "gpu": None, "gpu_max": None, "gpu_balayage": None}
        if mesure_gpu:
            journal(f"{nom} : recherche du plus grand micro-lot sur la carte graphique…")
            micro_lot = micro_lot_gpu(config)
            if micro_lot == 0:
                journal(f"{nom} : même micro_lot = 1 ne tient pas sur la carte graphique.")
            else:
                lots = sorted({1 << k for k in range(micro_lot.bit_length())} | {micro_lot})
                balayage = {}
                for essai in lots:
                    balayage[essai] = mesurer(config, "cuda", essai, pas, accumulation=gpu_accumulation)
                    journal(
                        f"{nom} : carte graphique, micro_lot {essai} : "
                        f"{balayage[essai]['jetons_par_seconde']:.0f} jetons/s."
                    )
                ligne["gpu_balayage"] = balayage
                ligne["gpu_max"] = balayage[micro_lot]
                ligne["gpu"] = max(balayage.values(), key=lambda r: r["jetons_par_seconde"])
        journal(f"{nom} : processeur, {os.cpu_count()} fils, micro_lot {cpu_micro_lot}, au plus {cpu_secondes:.0f} s…")
        # Un seul pas d'échauffement sur le processeur : rien à compiler ni à allouer au-delà du
        # premier passage, et un pas d'un grand modèle y dure des dizaines de secondes.
        ligne["cpu"] = mesurer(config, "cpu", cpu_micro_lot, pas, secondes_max=cpu_secondes, echauffement=1)
        journal(
            f"{nom} : processeur : {ligne['cpu']['jetons_par_seconde']:.0f} jetons/s sur "
            f"{ligne['cpu']['pas_mesures']} pas, charge moyenne {ligne['cpu']['charge_moyenne']:.0f} %."
        )
        ligne["disque"] = estimer_disque(config)
        for appareil in ("gpu", "cpu"):
            if ligne[appareil]:
                ligne[f"heures_{appareil}"] = estimer(config, ligne[appareil]["jetons_par_seconde"])
        if ligne["gpu"]:
            ligne["heures_gpu_max"] = estimer(config, ligne["gpu_max"]["jetons_par_seconde"])
            ligne["jetons_en_10_h_gpu"] = ligne["gpu"]["jetons_par_seconde"] * 10 * 3600
        resultats[nom] = ligne
    return resultats


def _dossier_des_donnees():
    from forge.chemins import racine_donnees

    chemin = racine_donnees()
    while not chemin.exists() and chemin != chemin.parent:
        chemin = chemin.parent
    return chemin


# --- Le tableau, en français ----------------------------------------------------------------------

_FINE = "\u202f"  # espace fine insécable : milliers, avant « % : ; ! ? » et dans les guillemets


def _decimal(valeur: float, decimales: int = 1) -> str:
    """12 345,6 : virgule décimale, espace fine entre les milliers."""
    return f"{valeur:,.{decimales}f}".replace(",", _FINE).replace(".", ",")


def _entier(valeur: float) -> str:
    return _decimal(valeur, 0)


def _debit(valeur: float) -> str:
    """Un débit en jetons par seconde : une décimale en dessous de 100, entier au-dessus."""
    return _decimal(valeur, 1 if valeur < 100 else 0)


def _duree_heures(heures: float) -> str:
    """Une durée en heures, avec les jours entre parenthèses au-delà de 48 h : 37,9 h ; 1 497 h (62 j)."""
    if heures < 1:
        return f"{_entier(heures * 60)} min"
    if heures < 48:
        return f"{_decimal(heures)} h"
    return f"{_entier(heures)} h ({_entier(heures / 24)} j)"


def _go(valeur: float) -> str:
    return f"{_decimal(valeur)} Go"


def _pourcent(valeur: float) -> str:
    return f"{_entier(valeur)}{_FINE}%"


def _tient_sur_le_disque(pic_go: float, libre_go: float | None) -> str:
    if libre_go is None:
        return "?"
    if pic_go <= libre_go:
        return f"oui (marge {_go(libre_go - pic_go)})"
    return f"**non** (manque {_go(pic_go - libre_go)})"


def tableaux_markdown(resultats: dict) -> str:
    """Les quatre tableaux de la mesure, en Markdown français : la carte, le processeur, les durées, le disque.

    `resultats` vient de `mesurer_presets`. Sur la carte, deux micro-lots sont montrés : le plus
    grand qui tient en mémoire (`gpu_max`) et le plus rapide des essais (`gpu`) ; les durées
    de ton IA sont celles du plus rapide (celles du plus grand sont données à côté). Elles visent
    `JETONS_PAR_PARAMETRE` (20) jetons par paramètre. Les colonnes « tient » comparent un besoin
    de place disque à la place libre relevée au début de la mesure.
    """
    libre = resultats["machine"].get("disque_libre_go")
    fils = resultats["machine"].get("coeurs_logiques")
    carte = [
        "| Taille | Paramètres | Plus grand micro-lot qui tient | jetons/s à ce micro-lot | pic de mémoire à ce micro-lot "
        "| Micro-lot le plus rapide | jetons/s à ce micro-lot | pic de mémoire à ce micro-lot |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    processeur = [
        "| Taille | Fils utilisés | Micro-lot | Pas mesurés | Jetons/s | Charge moyenne par cœur "
        f"| Cœurs occupés par le processus (sur {fils}) | Carte ÷ processeur |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    duree = [
        "| Taille | Jetons visés (20 par paramètre) | Durée sur la carte (micro-lot le plus rapide) "
        "| Durée sur la carte (plus grand micro-lot) | Durée sur le processeur "
        "| Jetons vus en 10 h sur la carte | Soit, par paramètre |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    disque = [
        "| Taille | Jetons sur le disque | Texte brut à télécharger | Sauvegardes | Pic de place disque "
        f"| Tient sur le disque ({_go(libre) if libre else '?'} libres){_FINE}? "
        f"| Pic si le texte brut est effacé avant l'entraînement | Tient{_FINE}? |",
        "| --- | ---: | ---: | ---: | ---: | --- | ---: | --- |",
    ]

    def colonnes_carte(r: dict | None) -> str:
        if not r:
            return "| — | — | — "
        return f"| {r['micro_lot']} | {_debit(r['jetons_par_seconde'])} | {_go(r['memoire_max_go'])} "

    for nom, ligne in resultats["presets"].items():
        gpu, gpu_max, cpu, place = ligne["gpu"], ligne["gpu_max"], ligne["cpu"], ligne["disque"]
        carte.append(f"| {nom} | {_decimal(ligne['parametres'] / 1e6)} M {colonnes_carte(gpu_max)}{colonnes_carte(gpu)}|")
        rapport = f"{_decimal(gpu['jetons_par_seconde'] / cpu['jetons_par_seconde'], 0)} ×" if gpu else "—"
        processeur.append(
            f"| {nom} | {cpu['fils_utilises']} | {cpu['micro_lot']} | {cpu['pas_mesures']} "
            f"| {_debit(cpu['jetons_par_seconde'])} | {_pourcent(cpu['charge_moyenne'])} "
            f"| {_decimal(cpu['coeurs_occupes'])} | {rapport} |"
        )
        en_10_h = ligne.get("jetons_en_10_h_gpu")
        duree.append(
            f"| {nom} | {_decimal(place['jetons'] / 1e9, 2)} milliards "
            f"| {_duree_heures(ligne['heures_gpu']) if gpu else '—'} "
            f"| {_duree_heures(ligne['heures_gpu_max']) if gpu else '—'} "
            f"| {_duree_heures(ligne['heures_cpu'])} "
            f"| {_decimal(en_10_h / 1e9, 2) + ' milliards' if gpu else '—'} "
            f"| {_decimal(en_10_h / ligne['parametres'], 1) + ' jetons' if gpu else '—'} |"
        )
        disque.append(
            f"| {nom} | {_go(place['jetons_go'])} | {_go(place['texte_brut_go'])} | {_go(place['sauvegardes_go'])} "
            f"| {_go(place['pic_go'])} | {_tient_sur_le_disque(place['pic_go'], libre)} "
            f"| {_go(place['pic_sequentiel_go'])} | {_tient_sur_le_disque(place['pic_sequentiel_go'], libre)} |"
        )
    return "\n\n".join("\n".join(tableau) for tableau in (carte, processeur, duree, disque)) + "\n"
