"""Le diagnostic est une fonction pure : des faits, il tire des constats.

On le teste sur les situations nommées de SITUATIONS (celles du chapitre), et
sur quelques variantes faites avec `replace`.
"""

import re
from dataclasses import fields, replace

from poste.diagnostic import (
    ARCHITECTURES_CU126,
    ARCHITECTURES_CU130,
    ARCHITECTURES_CU132,
    SITUATIONS,
    Constat,
    Niveau,
    carte_connue,
    diagnostiquer,
    plus_ancienne,
)
from poste.faits import Faits

_PRET = SITUATIONS["windows_cu132_rtx5070ti"]
_SANS_CARTE_VUE = dict(cuda_disponible=False, carte=None, capacite=None, architectures=())
# Les cas qui ne sont pas des situations du chapitre, pour les tests qui passent sur tous les constats.
VARIANTES = [
    replace(SITUATIONS["sans_carte"], torch=None),
    replace(_PRET, **_SANS_CARTE_VUE, pilote=None, cuda_max_pilote=None),
    replace(_PRET, **_SANS_CARTE_VUE),
    replace(_PRET, carte="NVIDIA GeForce GTX 1080", capacite=(6, 1)),
]


def cles(nom):
    return [c.cle for c in diagnostiquer(SITUATIONS[nom])]


def test_situations():
    assert cles("windows_cu132_rtx5070ti") == ["carte_prete"]
    assert "roue_processeur" in cles("windows_pypi_rtx5070ti")
    assert cles("sans_carte")[0] == "processeur_seul"
    assert "carte_trop_recente" in cles("windows_cu126_rtx5070ti")
    assert "pilote_trop_ancien" in cles("pilote_ancien")
    assert cles("colab_t4") == ["carte_prete"]
    assert "fils" in cles("fils_par_defaut")


def test_chaque_alerte_dit_quoi_faire():
    for f in SITUATIONS.values():
        for c in diagnostiquer(f):
            if c.niveau != Niveau.BON:
                assert c.a_faire


def test_torch_absent_sans_trace():
    assert [c.cle for c in diagnostiquer(replace(SITUATIONS["sans_carte"], torch=None))] == ["torch_absent"]


def test_les_sept_situations_et_leurs_constats_exacts():
    # Chaque situation montre une seule cause ; seule fils_par_defaut ajoute le constat « fils ».
    assert {nom: cles(nom) for nom in SITUATIONS} == {
        "windows_cu132_rtx5070ti": ["carte_prete"],
        "windows_pypi_rtx5070ti": ["roue_processeur"],
        "windows_cu126_rtx5070ti": ["carte_trop_recente"],
        "pilote_ancien": ["pilote_trop_ancien"],
        "sans_carte": ["processeur_seul"],
        "colab_t4": ["carte_prete"],
        "fils_par_defaut": ["carte_prete", "fils"],
    }


def test_les_situations_pretes_utilisent_tous_les_fils():
    # Sinon « carte_prete » ne serait pas seul : le constat « fils » a sa propre situation.
    for nom in ["windows_cu132_rtx5070ti", "colab_t4"]:
        f = SITUATIONS[nom]
        assert f.fils_torch == f.fils_processeur
    f = SITUATIONS["fils_par_defaut"]
    assert (f.fils_processeur, f.fils_torch) == (16, 8)
    assert replace(f, fils_torch=16) == SITUATIONS["windows_cu132_rtx5070ti"]


def test_les_situations_sont_des_faits_complets():
    for nom, f in SITUATIONS.items():
        assert isinstance(f, Faits), nom
        assert isinstance(f.architectures, tuple), nom
        # Une carte n'est vue, avec sa capacité et ses architectures, que si CUDA est disponible.
        if not f.cuda_disponible:
            assert (f.carte, f.capacite, f.architectures) == (None, None, ()), nom


def test_pilote_absent_puis_carte_invisible():
    pret = SITUATIONS["windows_cu132_rtx5070ti"]
    sans_pilote = replace(pret, cuda_disponible=False, carte=None, capacite=None, architectures=(), pilote=None, cuda_max_pilote=None)
    assert [c.cle for c in diagnostiquer(sans_pilote)] == ["pilote_absent"]
    invisible = replace(pret, cuda_disponible=False, carte=None, capacite=None, architectures=())
    assert [c.cle for c in diagnostiquer(invisible)] == ["carte_invisible"]
    # Un pilote dont on n'a pas lu la version de CUDA n'est pas jugé trop ancien.
    assert [c.cle for c in diagnostiquer(replace(invisible, cuda_max_pilote=None))] == ["carte_invisible"]


def test_ordre_des_regles():
    pret = SITUATIONS["windows_cu132_rtx5070ti"]
    invisible = replace(pret, cuda_disponible=False, carte=None, capacite=None, architectures=())
    # PyTorch ne voit pas la carte : un pilote trop ancien en est la cause, et passe avant « carte_invisible ».
    assert [c.cle for c in diagnostiquer(replace(invisible, cuda_max_pilote="12.4"))] == ["pilote_trop_ancien"]
    # Même version majeure de CUDA : le pilote suffit (compatibilité entre versions mineures).
    assert [c.cle for c in diagnostiquer(replace(invisible, cuda_max_pilote="13.0"))] == ["carte_invisible"]
    # Sans PyTorch, on s'arrête là : ni pilote, ni fils.
    sans_torch = replace(SITUATIONS["fils_par_defaut"], torch=None, cuda_compilee=None)
    assert [c.cle for c in diagnostiquer(sans_torch)] == ["torch_absent"]


def test_pilote_ancien_mais_carte_qui_calcule():
    # Une T4 avec un pilote 550 (CUDA 12.4 dans nvidia-smi) et la roue cu130 : avec le paquet
    # cuda-compat, PyTorch calcule quand même sur la carte. Le pilote suffit donc.
    t4 = replace(SITUATIONS["colab_t4"], pilote="550.54.15", cuda_max_pilote="12.4")
    assert t4.cuda_disponible and t4.cuda_compilee == "13.0"
    assert [c.cle for c in diagnostiquer(t4)] == ["carte_prete"]


def test_cartes_de_la_meme_generation():
    pret = SITUATIONS["windows_cu132_rtx5070ti"]
    # Une RTX 4070 (8.9) : aucune roue n'a sm_89, mais sm_86 sert toute la fin de la génération 8.
    rtx_4070 = replace(pret, carte="NVIDIA GeForce RTX 4070", capacite=(8, 9))
    assert [c.cle for c in diagnostiquer(rtx_4070)] == ["carte_prete"]
    assert [c.cle for c in diagnostiquer(replace(rtx_4070, architectures=ARCHITECTURES_CU130))] == ["carte_prete"]
    # Une carte 12.1 (DGX Spark) : sm_120 la sert.
    assert [c.cle for c in diagnostiquer(replace(pret, carte="NVIDIA GB10", capacite=(12, 1)))] == ["carte_prete"]
    # Une RTX 5070 Ti (12.0) avec la roue cu126, qui s'arrête à sm_90 : toujours trop récente.
    assert [c.cle for c in diagnostiquer(replace(pret, architectures=ARCHITECTURES_CU126))] == ["carte_trop_recente"]


def test_carte_connue():
    assert carte_connue((8, 9), ARCHITECTURES_CU132)
    assert carte_connue((7, 5), ARCHITECTURES_CU132)
    assert not carte_connue((12, 0), ARCHITECTURES_CU126)
    # Une mineure plus grande ne sert pas une carte plus ancienne de la même génération.
    assert not carte_connue((8, 0), ("sm_86",))
    # Les suffixes « a » et « f » ne comptent pas.
    assert carte_connue((9, 0), ("sm_90a",)) and carte_connue((10, 3), ("sm_100f",))
    # « compute_XY » (code recompilé par le pilote) sert toute carte de capacité plus grande ou égale.
    assert carte_connue((12, 1), ("sm_80", "compute_120")) and carte_connue((13, 0), ("compute_90",))
    assert not carte_connue((8, 6), ("compute_90",))
    # Un nom illisible est ignoré.
    assert not carte_connue((8, 6), ("gfx90a", "sm_"))
    assert plus_ancienne(ARCHITECTURES_CU132) == ((7, 5), "sm_75")
    assert plus_ancienne(("gfx90a",)) is None


def test_carte_trop_ancienne():
    pret = SITUATIONS["windows_cu132_rtx5070ti"]
    gtx_1080 = replace(pret, carte="NVIDIA GeForce GTX 1080", capacite=(6, 1))
    (constat,) = diagnostiquer(gtx_1080)
    assert (constat.cle, constat.niveau) == ("carte_trop_ancienne", Niveau.PROBLEME)
    assert "capacité 6.1" in constat.message and "trop ancienne" in constat.message
    assert "commence à sm_75" in constat.message
    assert "uv run --extra cpu python -m poste" in constat.a_faire and "FORGE_APPAREIL=cpu" in constat.a_faire
    # Le conseil prévient que la version pour le processeur laissera la carte de côté, exprès.
    assert "laisse la carte de côté, et c’est voulu" in constat.a_faire
    assert "variable d’environnement FORGE_APPAREIL=cpu" in constat.a_faire
    # Plus récente que la plus ancienne, mais sans architecture de sa génération : trop récente.
    assert [c.cle for c in diagnostiquer(replace(pret, capacite=(9, 0), architectures=("sm_75", "sm_80")))] == [
        "carte_trop_recente"
    ]


def test_niveaux():
    niveaux = {}
    for f in [*SITUATIONS.values(), *VARIANTES]:
        for c in diagnostiquer(f):
            niveaux[c.cle] = c.niveau
            assert isinstance(c, Constat)
            if c.niveau == Niveau.BON:
                assert c.a_faire is None
    assert niveaux == {
        "carte_prete": Niveau.BON,
        "processeur_seul": Niveau.BON,
        "roue_processeur": Niveau.ATTENTION,
        "fils": Niveau.ATTENTION,
        "carte_trop_recente": Niveau.PROBLEME,
        "carte_trop_ancienne": Niveau.PROBLEME,
        "carte_invisible": Niveau.PROBLEME,
        "pilote_absent": Niveau.PROBLEME,
        "pilote_trop_ancien": Niveau.PROBLEME,
        "torch_absent": Niveau.PROBLEME,
    }
    assert [n.value for n in Niveau] == ["bon", "attention", "probleme"]


def test_messages_utiles():
    def constat(f, cle):
        return next(c for c in diagnostiquer(f) if c.cle == cle)

    roue = constat(SITUATIONS["windows_pypi_rtx5070ti"], "roue_processeur")
    assert roue.a_faire == "Lance `uv sync --extra gpu`, puis relance `uv run --extra gpu python -m poste`."
    assert "621.01" in roue.message and "2.15.0+cpu" in roue.message
    fils = constat(SITUATIONS["fils_par_defaut"], "fils")
    assert "8 fils" in fils.message and "16" in fils.message
    assert "torch.set_num_threads" in fils.a_faire
    trop_recente = constat(SITUATIONS["windows_cu126_rtx5070ti"], "carte_trop_recente")
    assert "sm_120" in trop_recente.message and "uv sync --extra gpu" in trop_recente.a_faire
    ancien = constat(SITUATIONS["pilote_ancien"], "pilote_trop_ancien")
    assert "12.4" in ancien.message and "13.2" in ancien.message and "CUDA 13.0" in ancien.a_faire
    prete = constat(SITUATIONS["windows_cu132_rtx5070ti"], "carte_prete")
    assert "NVIDIA GeForce RTX 5070 Ti" in prete.message and "12.0" in prete.message
    # PyTorch installé mais qui ne se charge pas : la même commande, avec « import torch », montre l'erreur.
    absent = constat(replace(SITUATIONS["sans_carte"], torch=None), "torch_absent")
    assert "`python -c " in absent.a_faire and "import torch" in absent.a_faire


def test_un_seul_fil():
    f = replace(SITUATIONS["sans_carte"], fils_processeur=2, fils_torch=1)
    (fils,) = [c for c in diagnostiquer(f) if c.cle == "fils"]
    assert "que 1 fil de calcul" in fils.message


def tous_les_textes():
    for f in [*SITUATIONS.values(), *VARIANTES]:
        for c in diagnostiquer(f):
            yield c.cle, c.message
            if c.a_faire:
                yield c.cle, c.a_faire


def test_typographie_francaise():
    for cle, texte in tous_les_textes():
        # Hors du code entre accents graves, l'espace fine insécable (U+202F) précède
        # toujours « : ; ! ? » et se met à l'intérieur des guillemets.
        prose = re.sub(r"`[^`]*`", "", texte)
        assert not re.search(r"(?<!\u202f)[:;!?]", prose), f"{cle} : il manque l'espace fine dans « {texte} »"
        assert not re.search(r"«(?!\u202f)|(?<!\u202f)»", prose), f"{cle} : guillemets sans espace fine"
        assert "'" not in prose, f"{cle} : apostrophe droite"
        assert texte.endswith("."), f"{cle} : le texte finit par un point"


def test_les_commandes_citees_existent():
    for cle, texte in tous_les_textes():
        extras = re.findall(r"--extra (\w+)", texte)
        assert set(extras) <= {"cpu", "gpu"}, f"{cle} : extra inconnu dans « {texte} »"


def test_faits_a_les_champs_du_chapitre():
    assert [c.name for c in fields(Faits)] == [
        "systeme",
        "python",
        "torch",
        "cuda_compilee",
        "cuda_disponible",
        "carte",
        "capacite",
        "architectures",
        "pilote",
        "cuda_max_pilote",
        "fils_processeur",
        "fils_torch",
    ]
