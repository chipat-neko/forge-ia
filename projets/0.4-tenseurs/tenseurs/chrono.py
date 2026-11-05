"""Chronométrer un produit de matrices, sur le processeur et sur la carte graphique.

Le produit de deux matrices taille × taille, en float32, est le calcul qui
domine l'entraînement d'une IA. On le chronomètre sur le processeur avec 1
fil, avec le réglage par défaut de PyTorch, puis avec tous les fils du
processeur, et sur la carte graphique si elle est là. Sur la carte, on mesure
aussi la copie d'une matrice depuis la mémoire du processeur.

`mesurer()` rend toutes ces durées au format des fichiers mesures/*.json
(version 1), que lit le chapitre 0.4.
"""

import datetime
import math
import os
import platform
import statistics
import sys
import time

import torch

from tenseurs.appareil import choisir_appareil

TAILLES = (64, 256, 1024, 2048, 4096)  # des matrices de 64 × 64 à 4 096 × 4 096
NOMS = {"cpu": "le processeur", "cuda": "la carte graphique"}


# region: chrono
def attendre(appareil: torch.device) -> None:
    """Sur la carte, les calculs partent en file d'attente : on attend qu'ils soient finis."""
    if appareil.type == "cuda":
        torch.cuda.synchronize()


def chronometrer_produit(
    taille: int, appareil: str, fils: int | None = None, repetitions: int = 5, echauffement: int = 2
) -> float:
    """La durée médiane, en millisecondes, d'un produit de deux matrices taille × taille en float32."""
    ou = choisir_appareil(appareil)
    fils_avant = torch.get_num_threads()
    try:
        if fils is not None:
            torch.set_num_threads(fils)  # le nombre de fils du processeur qui calculent ensemble
        hasard = torch.Generator().manual_seed(0)  # les mêmes matrices à chaque mesure
        a = torch.randn(taille, taille, generator=hasard).to(ou)
        b = torch.randn(taille, taille, generator=hasard).to(ou)
        durees = []
        for tour in range(echauffement + repetitions):
            attendre(ou)
            debut = time.perf_counter()
            a @ b
            attendre(ou)  # sur la carte, le produit n'est fini qu'ici
            if tour >= echauffement:  # les premiers tours préparent le calcul : on ne les compte pas
                durees.append((time.perf_counter() - debut) * 1000)
        return statistics.median(durees)  # la durée du milieu : un tour dérangé ne compte pas
    finally:
        torch.set_num_threads(fils_avant)  # on rend à PyTorch son réglage
# fin: chrono


# region: transfert
def chronometrer_transfert(taille: int, repetitions: int = 5, echauffement: int = 2) -> float:
    """La durée médiane, en millisecondes, de la copie d'une matrice taille × taille vers la carte."""
    carte = choisir_appareil("cuda")
    a = torch.randn(taille, taille, generator=torch.Generator().manual_seed(0))  # sur le processeur
    durees = []
    for tour in range(echauffement + repetitions):
        torch.cuda.synchronize()
        debut = time.perf_counter()
        a.to(carte)  # de la mémoire du processeur à celle de la carte
        torch.cuda.synchronize()
        if tour >= echauffement:
            durees.append((time.perf_counter() - debut) * 1000)
    return statistics.median(durees)
# fin: transfert


def nom_processeur() -> str:
    """Le nom du processeur : dans le registre sous Windows, dans /proc/cpuinfo sous Linux."""
    if sys.platform == "win32":
        import winreg  # n'existe que sous Windows

        try:
            chemin = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, chemin) as cle:
                nom = " ".join(str(winreg.QueryValueEx(cle, "ProcessorNameString")[0]).split())
            if nom:
                return nom
        except OSError:
            pass
    elif sys.platform.startswith("linux"):
        try:
            with open("/proc/cpuinfo", encoding="utf-8", errors="replace") as fichier:
                for ligne in fichier:
                    if ligne.startswith("model name") and ":" in ligne:
                        return " ".join(ligne.split(":", 1)[1].split())
        except OSError:
            pass
    return " ".join(platform.processor().split()) or "processeur inconnu"


def fils_a_mesurer() -> tuple[int, ...]:
    """1 fil, le réglage par défaut de PyTorch, puis tous les fils du processeur, sans doublon."""
    tous = os.cpu_count() or torch.get_num_threads()
    return tuple(dict.fromkeys([1, torch.get_num_threads(), tous]))


def arrondi(millisecondes: float) -> float:
    """Une durée avec 4 chiffres significatifs : les suivants ne sont que du bruit."""
    return float(f"{millisecondes:.4g}")


def mesurer(appareil: str, tailles: tuple[int, ...] = TAILLES, fils: tuple[int, ...] | None = None) -> dict:
    """Les chronos d'un appareil, au format de mesures/*.json (version 1).

    Sur le processeur, chaque taille est mesurée avec chacun des `fils`
    (par défaut : 1, le réglage de PyTorch et tous les fils). Sur la carte,
    `fils` vaut None, et la copie vers la carte est mesurée pour chaque taille.
    """
    ou = choisir_appareil(appareil)
    fils_par_defaut = torch.get_num_threads()
    tailles = tuple(sorted(set(tailles)))
    if ou.type == "cpu":
        liste_fils = tuple(dict.fromkeys(fils)) if fils is not None else fils_a_mesurer()
    else:
        liste_fils = (None,)
    mesures = [
        {"taille": taille, "fils": f, "millisecondes": arrondi(chronometrer_produit(taille, ou.type, fils=f))}
        for taille in tailles
        for f in liste_fils
    ]
    transfert = None
    if ou.type == "cuda":
        transfert = {str(taille): arrondi(chronometrer_transfert(taille)) for taille in tailles}
    return {
        "version": 1,
        "releve_le": datetime.date.today().isoformat(),
        "appareil": ou.type,
        "nom": nom_processeur() if ou.type == "cpu" else torch.cuda.get_device_name(ou),
        "torch": str(torch.__version__),
        "fils_par_defaut": fils_par_defaut,
        "fils_max": os.cpu_count() or fils_par_defaut,
        "mesures": mesures,
        "transfert_ms": transfert,
    }


# Copie exacte de la fonction de projets/0.3-poste/poste/essai.py : un test le vérifie.
def en_francais(x: float, chiffres: int = 2) -> str:
    """Un nombre positif à la française, avec `chiffres` chiffres significatifs (au moins les unités) :
    2,1 ; 13 ; 123 ; 0,031 ; 0,0000012 ; 1 234 (avec une espace fine)."""
    if x == 0:
        return "0"
    decimales = max(0, chiffres - 1 - math.floor(math.log10(abs(x))))
    return f"{x:,.{decimales}f}".replace(",", "\u202f").replace(".", ",")


def entete(appareil: str) -> str:
    """La première ligne d'une série de mesures : quel calcul, sur quoi, avec quel PyTorch."""
    nom = nom_processeur() if appareil == "cpu" else torch.cuda.get_device_name(0)
    return f"Produit de deux matrices en float32, sur {NOMS[appareil]} ({nom}), PyTorch {torch.__version__}\u202f:"


def decrire_mesures(m: dict) -> list[str]:
    """Une ligne par taille : les durées, et sur la carte, la copie vers la carte."""
    lignes = []
    for taille in dict.fromkeys(x["taille"] for x in m["mesures"]):
        cote = en_francais(taille)
        durees = []
        for x in m["mesures"]:
            if x["taille"] != taille:
                continue
            ms = f"{en_francais(x['millisecondes'])} ms"
            if x["fils"] is not None:
                ms += f" avec {x['fils']} fil" + ("s" if x["fils"] > 1 else "")
            durees.append(ms)
        if m["transfert_ms"] is not None:
            durees.append(f"copie vers la carte {en_francais(m['transfert_ms'][str(taille)])} ms")
        lignes.append(f"  {cote} × {cote}\u202f: " + ", ".join(durees))
    return lignes
