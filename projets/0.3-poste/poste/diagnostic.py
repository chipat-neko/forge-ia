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
def majeure(version: str) -> int:
    """La version majeure : 13 pour « 13.2 »."""
    return int(version.split(".")[0])


def fils(n: int) -> str:
    """« 1 fil », « 8 fils »."""
    return f"{n} fil" if n == 1 else f"{n} fils"


RELANCER = "relance `uv run --extra gpu python -m poste`"


def diagnostiquer(f: Faits) -> list[Constat]:
    """Les constats sur le poste : d'abord celui de PyTorch et de la carte, puis celui des fils."""
    if f.torch is None:
        # Sans PyTorch, rien d'autre ne compte : on s'arrête là.
        return [
            Constat(
                Niveau.PROBLEME,
                "torch_absent",
                "PyTorch ne s’importe pas\u202f: il n’est pas installé dans cet environnement, ou il ne se charge pas.",
                "Lance `uv run --extra gpu python -m poste` si tu as une carte NVIDIA, sinon "
                "`uv run --extra cpu python -m poste`\u202f: uv installe PyTorch avant de lancer le script.",
            )
        ]

    if f.cuda_compilee is None:
        # La version de PyTorch pour le processeur seul (torch.version.cuda vaut None).
        if f.pilote is None:
            constat = Constat(
                Niveau.BON,
                "processeur_seul",
                "Pas de carte NVIDIA ici (aucun pilote trouvé)\u202f: PyTorch calcule sur le processeur. "
                "Tout marche ainsi, en plus lent pour entraîner ton IA.",
                None,
            )
        else:
            constat = Constat(
                Niveau.ATTENTION,
                "roue_processeur",
                f"Une carte NVIDIA est là (pilote {f.pilote}), mais cette version de PyTorch ({f.torch}) "
                "ne sait calculer que sur le processeur\u202f: elle laisse la carte de côté.",
                f"Lance `uv sync --extra gpu`, puis {RELANCER}.",
            )
    elif f.pilote is None:
        constat = Constat(
            Niveau.PROBLEME,
            "pilote_absent",
            f"Cette version de PyTorch ({f.torch}) est faite pour une carte NVIDIA, avec CUDA {f.cuda_compilee}, "
            "mais aucun pilote NVIDIA ne répond (nvidia-smi est introuvable ou en erreur).",
            "Si tu as une carte NVIDIA, installe son pilote depuis le site de NVIDIA, redémarre, puis "
            f"{RELANCER}. Sinon, lance `uv run --extra cpu python -m poste`\u202f: tout tournera sur le processeur.",
        )
    elif f.cuda_max_pilote is not None and majeure(f.cuda_max_pilote) < majeure(f.cuda_compilee):
        constat = Constat(
            Niveau.PROBLEME,
            "pilote_trop_ancien",
            f"Ton pilote NVIDIA ({f.pilote}) va jusqu’à CUDA {f.cuda_max_pilote}, mais cette version de PyTorch "
            f"est faite pour CUDA {f.cuda_compilee}\u202f: le pilote est trop ancien pour elle.",
            f"Mets à jour le pilote de ta carte (site ou application de NVIDIA) pour qu’il aille au moins jusqu’à "
            f"CUDA {majeure(f.cuda_compilee)}.0, redémarre, puis {RELANCER}.",
        )
    elif f.cuda_disponible and f.capacite is not None and f"sm_{f.capacite[0]}{f.capacite[1]}" not in f.architectures:
        # La capacité (12, 0) se dit « sm_120 » dans la liste des architectures de PyTorch.
        constat = Constat(
            Niveau.PROBLEME,
            "carte_trop_recente",
            f"Ta carte ({f.carte}, capacité {f.capacite[0]}.{f.capacite[1]}) est plus récente que cette version "
            f"de PyTorch ({f.torch}), qui n’a pas été compilée pour sm_{f.capacite[0]}{f.capacite[1]}.",
            "Lance `uv sync --extra gpu` pour installer la version de PyTorch du projet, qui connaît les cartes "
            f"récentes, puis {RELANCER}.",
        )
    elif not f.cuda_disponible:
        constat = Constat(
            Niveau.PROBLEME,
            "carte_invisible",
            f"Le pilote NVIDIA ({f.pilote}) est là, et cette version de PyTorch ({f.torch}) est faite pour la "
            "carte, mais PyTorch ne voit aucune carte.",
            "Lance `nvidia-smi`\u202f: s’il ne montre pas ta carte, redémarre l’ordinateur, ou réinstalle le "
            "pilote. S’il la montre, vérifie que la variable CUDA_VISIBLE_DEVICES n’est pas réglée. "
            f"Puis {RELANCER}.",
        )
    else:
        capacite = "capacité inconnue" if f.capacite is None else f"capacité {f.capacite[0]}.{f.capacite[1]}"
        constat = Constat(
            Niveau.BON,
            "carte_prete",
            f"PyTorch {f.torch} voit ta carte, {f.carte} ({capacite}), et sait calculer dessus.",
            None,
        )

    constats = [constat]
    if f.fils_torch < f.fils_processeur:
        constats.append(
            Constat(
                Niveau.ATTENTION,
                "fils",
                f"PyTorch n’utilise que {fils(f.fils_torch)} de calcul sur les {f.fils_processeur} de ton processeur.",
                "Au début d’un programme qui calcule sur le processeur, écris "
                "`torch.set_num_threads(os.cpu_count())` (avec `import os`)\u202f: PyTorch prendra tous les fils.",
            )
        )
    return constats


# fin: diagnostiquer


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
# - PyTorch 2.11 cu130 (Colab) : pas relevées ; on reprend celles de la roue cu132, qui
#   commencent comme elle à sm_75, la capacité de la T4.
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
    # Colab avec une carte T4 (capacité 7.5), Python 3.13 et PyTorch 2.11 pour CUDA 13.0 (image du
    # 03/11/2026). Le pilote est un exemple de la série 580, la première qui accepte CUDA 13, et les
    # deux fils un exemple de petite machine. Le système est abrégé.
    "colab_t4": Faits(
        systeme="Linux",
        python="3.13.16",
        torch="2.11.0+cu130",
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
