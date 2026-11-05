"""Le diagnostic du poste : des faits, il tire des constats, avec ce qu'il faut faire.

`diagnostiquer` est une fonction pure : elle ne lit que ses faits, sans rien
lancer. On la teste donc sur des situations nommées (SITUATIONS), celles des
lecteurs du chapitre 0.3, sans avoir besoin de leur ordinateur.
"""

from dataclasses import dataclass, replace
from enum import StrEnum

from poste.faits import Faits


class Niveau(StrEnum):
    BON = "bon"
    ATTENTION = "attention"  # ça marche, mais moins bien que ça pourrait
    PROBLEME = "probleme"  # ça ne marche pas comme prévu : il faut agir


@dataclass(frozen=True)
class Constat:
    niveau: Niveau
    cle: str  # un nom fixe, lu par les tests et par le chapitre
    message: str  # ce que le script a vu
    a_faire: str | None  # la commande à lancer ; None quand tout va bien


# region: diagnostiquer
def architecture(nom: str) -> tuple[str, tuple[int, int]] | None:
    """« sm_86 » donne ("sm", (8, 6)), « sm_90a » donne ("sm", (9, 0)), « compute_120 » donne
    ("compute", (12, 0)). None pour un nom qu'on ne sait pas lire."""
    genre, _, chiffres = nom.partition("_")
    chiffres = chiffres.removesuffix("a").removesuffix("f")
    if genre not in ("sm", "compute") or not chiffres.isdigit():
        return None
    n = int(chiffres)
    return genre, (n // 10, n % 10)


def carte_connue(capacite: tuple[int, int], architectures: tuple[str, ...]) -> bool:
    """PyTorch sait calculer sur la carte si une de ses architectures lui va :
    - un « sm_XY » de la même génération X, et de mineure Y plus petite ou égale :
      « sm_86 » sert aussi une RTX 4070, de capacité 8.9 ;
    - ou un « compute_XY », du code que le pilote recompile pour toute carte
      de capacité plus grande ou égale."""
    for nom in architectures:
        lue = architecture(nom)
        if lue is None:
            continue
        genre, (generation, mineure) = lue
        if genre == "sm" and generation == capacite[0] and mineure <= capacite[1]:
            return True
        if genre == "compute" and (generation, mineure) <= capacite:
            return True
    return False


def diagnostiquer(f: Faits) -> list[Constat]:
    """Les constats sur le poste : d'abord celui de PyTorch et de la carte, puis celui des fils.
    Elle ne fait que choisir la clé de chaque constat ; constat_pour en écrit le texte."""
    if f.torch is None:
        # Sans PyTorch, rien d'autre ne compte : on s'arrête là.
        return [constat_pour("torch_absent", f)]
    if f.cuda_compilee is None:
        # La version de PyTorch pour le processeur seul (torch.version.cuda vaut None).
        cle = "processeur_seul" if f.pilote is None else "roue_processeur"
    elif f.pilote is None:
        cle = "pilote_absent"
    elif (
        not f.cuda_disponible
        and f.cuda_max_pilote is not None
        and majeure(f.cuda_max_pilote) < majeure(f.cuda_compilee)
    ):
        # Seulement si PyTorch ne voit pas la carte : s'il la voit, le pilote suffit. Le paquet
        # cuda-compat (Colab, cartes de centre de calcul) fait tourner un CUDA plus récent que
        # celui qu'annonce nvidia-smi.
        cle = "pilote_trop_ancien"
    elif f.cuda_disponible and f.capacite is not None and not carte_connue(f.capacite, f.architectures):
        # Aucune architecture de la liste ne sert la carte : elle est trop ancienne, ou trop récente.
        ancienne = plus_ancienne(f.architectures)
        trop_ancienne = ancienne is not None and f.capacite < ancienne[0]
        cle = "carte_trop_ancienne" if trop_ancienne else "carte_trop_recente"
    elif not f.cuda_disponible:
        cle = "carte_invisible"
    else:
        cle = "carte_prete"

    constats = [constat_pour(cle, f)]
    if f.fils_torch < f.fils_processeur:
        constats.append(constat_pour("fils", f))
    return constats
# fin: diagnostiquer


# Les petites aides du diagnostic, et le texte de chaque constat : hors de l'extrait que montre le
# chapitre 0.3, qui s'arrête à la règle des générations et à la chaîne de décision.


def majeure(version: str) -> int:
    """La version majeure : 13 pour « 13.2 »."""
    return int(version.split(".")[0])


def fils(n: int) -> str:
    """« 1 fil », « 8 fils »."""
    return f"{n} fil" if n == 1 else f"{n} fils"


def plus_ancienne(architectures: tuple[str, ...]) -> tuple[tuple[int, int], str] | None:
    """La capacité et le nom de la plus ancienne architecture de la liste, ou None."""
    lues = []
    for nom in architectures:
        lue = architecture(nom)
        if lue is not None:
            lues.append((lue[1], nom))
    return min(lues, default=None)


RELANCER = "relance `uv run --extra gpu python -m poste`"


def constat_pour(cle: str, f: Faits) -> Constat:
    """Le constat `cle` pour ces faits : son niveau, ce que le script a vu, et ce qu'il faut faire.
    diagnostiquer choisit la clé ; les textes sont ici."""
    if cle == "torch_absent":
        return Constat(
            Niveau.PROBLEME,
            cle,
            "PyTorch ne s’importe pas\u202f: il n’est pas installé dans cet environnement, ou il ne se charge pas.",
            "Lance `uv run --extra gpu python -m poste` si tu as une carte NVIDIA, sinon "
            "`uv run --extra cpu python -m poste`\u202f: uv installe PyTorch avant de lancer le script. "
            "S’il est installé mais ne se charge pas, remplace `python -m poste` par "
            "`python -c \"import torch\"` dans la même commande\u202f: l’erreur s’affichera.",
        )
    if cle == "processeur_seul":
        return Constat(
            Niveau.BON,
            cle,
            "Pas de carte NVIDIA ici (aucun pilote trouvé)\u202f: PyTorch calcule sur le processeur. "
            "Tout marche ainsi, en plus lent pour entraîner ton IA.",
            None,
        )
    if cle == "roue_processeur":
        return Constat(
            Niveau.ATTENTION,
            cle,
            f"Une carte NVIDIA est là (pilote {f.pilote}), mais cette version de PyTorch ({f.torch}) "
            "ne sait calculer que sur le processeur\u202f: elle laisse la carte de côté.",
            f"Lance `uv sync --extra gpu`, puis {RELANCER}.",
        )
    if cle == "pilote_absent":
        return Constat(
            Niveau.PROBLEME,
            cle,
            f"Cette version de PyTorch ({f.torch}) est faite pour une carte NVIDIA, avec CUDA {f.cuda_compilee}, "
            "mais aucun pilote NVIDIA ne répond (nvidia-smi est introuvable ou en erreur).",
            "Si tu as une carte NVIDIA, installe son pilote depuis le site de NVIDIA, redémarre, puis "
            f"{RELANCER}. Sinon, lance `uv run --extra cpu python -m poste`\u202f: tout tournera sur le processeur.",
        )
    if cle == "pilote_trop_ancien":
        return Constat(
            Niveau.PROBLEME,
            cle,
            f"Ton pilote NVIDIA ({f.pilote}) va jusqu’à CUDA {f.cuda_max_pilote}, mais cette version de PyTorch "
            f"est faite pour CUDA {f.cuda_compilee}\u202f: le pilote est trop ancien pour elle.",
            f"Mets à jour le pilote de ta carte (site ou application de NVIDIA) pour qu’il aille au moins jusqu’à "
            f"CUDA {majeure(f.cuda_compilee)}.0, redémarre, puis {RELANCER}.",
        )
    if cle == "carte_trop_ancienne":
        ancienne = plus_ancienne(f.architectures)
        return Constat(
            Niveau.PROBLEME,
            cle,
            f"Ta carte ({f.carte}, capacité {f.capacite[0]}.{f.capacite[1]}) est trop ancienne pour cette "
            f"version de PyTorch ({f.torch}), qui commence à {ancienne[1]}.",
            "Calcule sur le processeur\u202f: lance `uv run --extra cpu python -m poste`. Le "
            "diagnostic dira alors que cette version laisse la carte de côté, et c’est voulu, puisque la "
            "carte est trop ancienne. Dans les projets suivants, mets la variable d’environnement "
            "FORGE_APPAREIL=cpu.",
        )
    if cle == "carte_trop_recente":
        return Constat(
            Niveau.PROBLEME,
            cle,
            f"Ta carte ({f.carte}, capacité {f.capacite[0]}.{f.capacite[1]}) est plus récente que cette version "
            f"de PyTorch ({f.torch}), qui n’a pas été compilée pour sm_{f.capacite[0]}{f.capacite[1]}.",
            "Lance `uv sync --extra gpu` pour installer la version de PyTorch du projet, qui connaît les cartes "
            f"récentes, puis {RELANCER}.",
        )
    if cle == "carte_invisible":
        return Constat(
            Niveau.PROBLEME,
            cle,
            f"Le pilote NVIDIA ({f.pilote}) est là, et cette version de PyTorch ({f.torch}) est faite pour la "
            "carte, mais PyTorch ne voit aucune carte.",
            "Lance `nvidia-smi`\u202f: s’il ne montre pas ta carte, redémarre l’ordinateur, ou réinstalle le "
            "pilote. S’il la montre, vérifie que la variable CUDA_VISIBLE_DEVICES n’est pas réglée. "
            f"Puis {RELANCER}.",
        )
    if cle == "carte_prete":
        capacite = "capacité inconnue" if f.capacite is None else f"capacité {f.capacite[0]}.{f.capacite[1]}"
        return Constat(
            Niveau.BON,
            cle,
            f"PyTorch {f.torch} voit ta carte, {f.carte} ({capacite}), et sait calculer dessus.",
            None,
        )
    if cle == "fils":
        return Constat(
            Niveau.ATTENTION,
            cle,
            f"PyTorch n’utilise que {fils(f.fils_torch)} de calcul sur les {f.fils_processeur} de ton processeur.",
            "Au début d’un programme qui calcule sur le processeur, écris "
            "`torch.set_num_threads(os.cpu_count())` (avec `import os`)\u202f: PyTorch prendra tous les fils.",
        )
    raise ValueError(f"Constat inconnu\u202f: «\u202f{cle}\u202f». Ajoute son texte dans constat_pour (poste/diagnostic.py).")


# Le niveau tel que le rapport l'affiche.
LIBELLES = {Niveau.BON: "bon", Niveau.ATTENTION: "attention", Niveau.PROBLEME: "problème"}


def decrire_constat(c: Constat) -> list[str]:
    """Les lignes du rapport pour un constat : son niveau et son message, puis ce qu'il faut faire."""
    lignes = [f"  {LIBELLES[c.niveau]}\u202f: {c.message}"]
    if c.a_faire:
        lignes.append(f"    À faire\u202f: {c.a_faire}")
    return lignes


# Les situations du chapitre 0.3 : des postes de lecteurs, décrits par leurs faits.
# Ce sont des exemples construits, pas des relevés, sauf ce qui vient de ce PC :
# le pilote 621.01, qui va jusqu'à CUDA 13.5, et les 16 fils du processeur, dont
# PyTorch ne prend que 8 par défaut (mesure du 03/11/2026, docs/mesures/entrainement-2026-11.md).
#
# Les architectures sont celles que rend torch.cuda.get_arch_list() :
# - PyTorch 2.15.0+cu132 sous Windows : lues dans la roue installée le 05/11/2026 ;
# - PyTorch 2.7 cu126 : celles que cite son avertissement pour une carte RTX 50, sans sm_120 ;
# - les roues CUDA 13.0 (celle de Colab) : les mêmes que cu132, d'après la table
#   PYTORCH_RELEASES_CODE_CC de torch/cuda/__init__.py (PyTorch 2.15, lue le 05/11/2026).
ARCHITECTURES_CU132 = ("sm_75", "sm_80", "sm_86", "sm_90", "sm_100", "sm_120")
ARCHITECTURES_CU126 = ("sm_50", "sm_60", "sm_61", "sm_70", "sm_75", "sm_80", "sm_86", "sm_90")
ARCHITECTURES_CU130 = ARCHITECTURES_CU132

# Dans chaque situation sauf fils_par_defaut, PyTorch utilise tous les fils du processeur :
# chacune montre ainsi une seule cause, et « carte_prete » reste seul quand tout va bien.
RTX_5070_TI_PRETE = Faits(
    systeme="Windows 11",
    python="3.12.13",
    torch="2.15.0+cu132",
    cuda_compilee="13.2",
    cuda_disponible=True,
    carte="NVIDIA GeForce RTX 5070 Ti",
    capacite=(12, 0),
    architectures=ARCHITECTURES_CU132,
    pilote="621.01",
    cuda_max_pilote="13.5",
    fils_processeur=16,
    fils_torch=16,
)

SITUATIONS: dict[str, Faits] = {
    # La RTX 5070 Ti avec la version de PyTorch du projet : tout est prêt.
    "windows_cu132_rtx5070ti": RTX_5070_TI_PRETE,
    # La même carte, avec `pip install torch` : PyPI ne sert sous Windows que la version pour processeur.
    "windows_pypi_rtx5070ti": replace(
        RTX_5070_TI_PRETE,
        torch="2.15.0+cpu",
        cuda_compilee=None,
        cuda_disponible=False,
        carte=None,
        capacite=None,
        architectures=(),
    ),
    # La même carte, avec un ancien tutoriel : PyTorch 2.7 pour CUDA 12.6, qui ne connaît pas sm_120.
    # PyTorch voit la carte (il prévient seulement), mais ne peut pas calculer dessus.
    "windows_cu126_rtx5070ti": replace(
        RTX_5070_TI_PRETE,
        torch="2.7.1+cu126",
        cuda_compilee="12.6",
        architectures=ARCHITECTURES_CU126,
    ),
    # Une carte plus ancienne, avec un pilote de la série 551 (CUDA 12.4 au plus) : trop vieux pour CUDA 13.2.
    "pilote_ancien": replace(
        RTX_5070_TI_PRETE,
        cuda_disponible=False,
        carte=None,
        capacite=None,
        architectures=(),
        pilote="551.86",
        cuda_max_pilote="12.4",
    ),
    # Un PC sans carte NVIDIA, avec la version de PyTorch pour le processeur.
    "sans_carte": replace(
        RTX_5070_TI_PRETE,
        torch="2.15.0+cpu",
        cuda_compilee=None,
        cuda_disponible=False,
        carte=None,
        capacite=None,
        architectures=(),
        pilote=None,
        cuda_max_pilote=None,
    ),
    # Colab avec une carte T4 (capacité 7.5). Python 3.13.16 et PyTorch 2.14.1+cu130 : image de Colab
    # avec carte, https://github.com/googlecolab/backend-info (os-info-gpu.txt et pip-freeze.gpu.txt),
    # vérifié le 05/11/2026. Le dépôt ne donne pas le pilote : 580.82.07 (CUDA 13.0) est un exemple de
    # la série 580, la première qui accepte CUDA 13 ; son apt-list-gpu.txt liste cuda-compat-13-0, qui
    # fait aussi tourner CUDA 13 sur un pilote plus ancien. Les deux fils sont un exemple de petite
    # machine, et le système est abrégé.
    "colab_t4": Faits(
        systeme="Linux",
        python="3.13.16",
        torch="2.14.1+cu130",
        cuda_compilee="13.0",
        cuda_disponible=True,
        carte="Tesla T4",
        capacite=(7, 5),
        architectures=ARCHITECTURES_CU130,
        pilote="580.82.07",
        cuda_max_pilote="13.0",
        fils_processeur=2,
        fils_torch=2,
    ),
    # Ce PC avec la carte prête, mais PyTorch réglé par défaut : 8 fils sur 16.
    "fils_par_defaut": replace(RTX_5070_TI_PRETE, fils_torch=8),
}
