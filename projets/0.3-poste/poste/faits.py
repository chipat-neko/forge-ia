"""Les faits du poste : ce que disent le système, Python, PyTorch et le pilote NVIDIA.

`relever_faits()` ne fait que lire : elle n'installe rien et ne change aucun
réglage. Elle ne crée de contexte CUDA (la mémoire que le pilote réserve sur la
carte pour un programme) que si PyTorch voit une carte. PyTorch s'importe à
l'intérieur de la fonction : sans lui, le reste du paquet marche encore, et
le diagnostic peut dire ce qui manque.
"""

import os
import platform
import re
import subprocess
from dataclasses import dataclass

# Le plus longtemps qu'on attend nvidia-smi, en secondes : un pilote bloqué ne bloque pas le diagnostic.
DELAI_NVIDIA_SMI = 5

# L'en-tête de nvidia-smi : « CUDA Version: 12.4 » jusqu'à la série 58x des pilotes,
# « CUDA UMD Version: 13.5 » avec le pilote 621.01.
VERSION_CUDA_DU_PILOTE = re.compile(r"CUDA (?:UMD )?Version:\s*(\d+(?:\.\d+)*)")


@dataclass(frozen=True)
class Faits:
    """Ce qu'on sait du poste. `None` veut dire « absent » ou « introuvable »."""

    systeme: str  # « Windows 11 », « Linux 6.6.105+ », « macOS 15.1 »
    python: str  # « 3.12.13 »
    torch: str | None  # « 2.15.0+cu132 », ou None si PyTorch ne s'importe pas
    cuda_compilee: str | None  # torch.version.cuda : « 13.2 », ou None pour la version processeur seul
    cuda_disponible: bool  # torch.cuda.is_available()
    carte: str | None  # « NVIDIA GeForce RTX 5070 Ti », si PyTorch voit la carte
    capacite: tuple[int, int] | None  # capacité de calcul de la carte : (12, 0)
    architectures: tuple[str, ...]  # les cartes pour lesquelles ce PyTorch est compilé : ("sm_75", …, "sm_120")
    pilote: str | None  # version du pilote NVIDIA : « 621.01 »
    cuda_max_pilote: str | None  # la plus haute version de CUDA que le pilote accepte : « 13.5 »
    fils_processeur: int  # fils de calcul du processeur (os.cpu_count())
    fils_torch: int  # fils que PyTorch utilise (torch.get_num_threads()), 0 sans PyTorch


def nom_du_systeme() -> str:
    """Le nom du système, lisible : « Windows 11 », « macOS 15.1 », « Linux 6.6.105+ »."""
    if platform.system() == "Darwin":
        return f"macOS {platform.mac_ver()[0]}"
    return f"{platform.system()} {platform.release()}".strip()


def lancer_nvidia_smi(*options: str) -> str | None:
    """Ce qu'affiche `nvidia-smi` avec ces options, ou None s'il est introuvable,
    trop lent, ou en erreur (pilote absent ou qui ne répond pas)."""
    try:
        resultat = subprocess.run(
            ["nvidia-smi", *options],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=DELAI_NVIDIA_SMI,
        )
    except (OSError, subprocess.TimeoutExpired):  # OSError comprend FileNotFoundError
        return None
    return resultat.stdout if resultat.returncode == 0 else None


def lire_pilote(texte: str) -> str | None:
    """La version du pilote, d'après `nvidia-smi --query-gpu=driver_version --format=csv,noheader`
    (une ligne par carte : on garde la première)."""
    lignes = [ligne.strip() for ligne in texte.splitlines() if ligne.strip()]
    return lignes[0] if lignes else None


def lire_cuda_max(texte: str) -> str | None:
    """La plus haute version de CUDA que le pilote accepte, d'après l'en-tête de `nvidia-smi`."""
    trouve = VERSION_CUDA_DU_PILOTE.search(texte)
    return trouve.group(1) if trouve else None


def relever_faits() -> Faits:
    """Relève les faits du poste, sans rien changer."""
    try:
        import torch
    except (ImportError, OSError):  # OSError : une bibliothèque de PyTorch qui ne se charge pas
        torch = None

    requete = lancer_nvidia_smi("--query-gpu=driver_version", "--format=csv,noheader")
    pilote = lire_pilote(requete) if requete is not None else None
    entete = lancer_nvidia_smi() if pilote is not None else None

    cuda_disponible = torch is not None and torch.cuda.is_available()
    carte, capacite, architectures = None, None, ()
    if cuda_disponible:
        # Seulement ici : ces trois appels démarrent CUDA, et donc un contexte sur la carte.
        carte = torch.cuda.get_device_name(0)
        capacite = tuple(torch.cuda.get_device_capability(0))
        architectures = tuple(torch.cuda.get_arch_list())

    return Faits(
        systeme=nom_du_systeme(),
        python=platform.python_version(),
        torch=torch.__version__ if torch is not None else None,
        cuda_compilee=torch.version.cuda if torch is not None else None,
        cuda_disponible=cuda_disponible,
        carte=carte,
        capacite=capacite,
        architectures=architectures,
        pilote=pilote,
        cuda_max_pilote=lire_cuda_max(entete) if entete is not None else None,
        fils_processeur=os.cpu_count() or 1,
        fils_torch=torch.get_num_threads() if torch is not None else 0,
    )


def decrire_faits(f: Faits) -> list[str]:
    """Les lignes du rapport qui décrivent le poste."""
    lignes = ["Ton poste", f"  Système\u202f: {f.systeme}", f"  Python\u202f: {f.python}"]
    if f.torch is None:
        lignes.append("  PyTorch\u202f: ne s’importe pas")
    else:
        lignes.append(f"  PyTorch\u202f: {f.torch}")
        if f.cuda_compilee is None:
            lignes.append("  CUDA dans PyTorch\u202f: aucune, c’est la version pour le processeur seul")
        else:
            lignes.append(f"  CUDA dans PyTorch\u202f: {f.cuda_compilee}")
        if f.carte is None:
            lignes.append("  Carte vue par PyTorch\u202f: aucune")
        elif f.capacite is None:
            lignes.append(f"  Carte vue par PyTorch\u202f: {f.carte}")
        else:
            lignes.append(f"  Carte vue par PyTorch\u202f: {f.carte}, capacité {f.capacite[0]}.{f.capacite[1]}")
        if f.architectures:
            lignes.append(f"  Architectures de ce PyTorch\u202f: {', '.join(f.architectures)}")
    if f.pilote is None:
        lignes.append("  Pilote NVIDIA\u202f: aucun (nvidia-smi est introuvable ou ne répond pas)")
    elif f.cuda_max_pilote is None:
        lignes.append(f"  Pilote NVIDIA\u202f: {f.pilote}")
    else:
        lignes.append(f"  Pilote NVIDIA\u202f: {f.pilote}, jusqu’à CUDA {f.cuda_max_pilote}")
    if f.torch is None:
        lignes.append(f"  Fils du processeur\u202f: {f.fils_processeur}")
    else:
        utilises = "utilisé" if f.fils_torch == 1 else "utilisés"
        lignes.append(f"  Fils du processeur\u202f: {f.fils_processeur}, dont {f.fils_torch} {utilises} par PyTorch")
    return lignes
