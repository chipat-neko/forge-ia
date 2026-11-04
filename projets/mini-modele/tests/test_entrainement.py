"""L'entraînement : le taux, l'écrêtage, AdamW, et l'Entraineur.

La parité avec le TypeScript (site/src/lib/mini-modele/entrainement.ts) est
vérifiée au bit près par tests/attendus-modele.json, clé « entrainement »
(voir test_attendus.py et entrainement.test.ts). Ici, on vérifie ce que le
code fait : le taux est celui de forge, un pas suit la recette d'AdamW écrite
autrement, les hasards sont séparés, et un taux trop grand arrête tout.

Le test long (l'entraînement complet de 3 000 pas, quelques minutes en Python
pur) est marqué « lent » : il ne tourne qu'avec « uv run pytest -q -m lent ».
"""

import dataclasses
import math
import pathlib

import pytest

from mini_modele.calcul import Hasard, empreinte, log, somme, vers_hex
from mini_modele.donnees import decoder, preparer
from mini_modele.entrainement import (
    PRESETS_MINI,
    TAUX_PROPOSES,
    Entraineur,
    ReglagesMini,
    taux,
)
from mini_modele.modele import generer, initialiser, nombre_parametres, perte, perte_et_gradient

# Le planning de forge, lu dans son fichier (projets/forge n'est jamais modifié).
PLANNING_FORGE = pathlib.Path(__file__).resolve().parents[2] / "forge" / "forge" / "entrainement" / "planning.py"

# Vingt prénoms de deux lettres : 18 vont en entraînement, 2 en validation.
VINGT = ["an", "bo", "ci", "du", "el", "fa", "gu", "hi", "in", "jo", "ka", "lu", "ma", "ne", "ol", "pa", "qu", "ro", "su", "ti"]

# Le résultat de l'entraînement complet (test long), le même en TypeScript
# (site/src/lib/mini-modele/entrainement-long.test.ts) : si le code change,
# relance « uv run pytest -q -m lent », puis recopie les nouvelles valeurs ici
# et dans le test TypeScript. L'intégration continue ne lance pas ce test long :
# un test rapide de Vitest relit ces trois lignes et vérifie qu'elles valent les
# constantes du test TypeScript (garde la forme NOM = "…", seule sur sa ligne).
LONG_VALIDATION_DEPART = "400d39161fba8940"
LONG_VALIDATION_FIN = "40014367b7b1cd81"
LONG_PARAMS_EMPREINTE = "1637bfe4"


def taux_de_forge():
    """La fonction taux de forge, lue dans son fichier sans l'importer.

    On exécute le texte du fichier : forge n'est pas une dépendance de ce
    projet, et rien n'est écrit dans son dossier (pas de __pycache__).
    """
    assert PLANNING_FORGE.exists(), f"{PLANNING_FORGE} est introuvable : le planning de forge a-t-il changé de place ?"
    espace: dict = {}
    exec(compile(PLANNING_FORGE.read_text(encoding="utf-8"), str(PLANNING_FORGE), "exec"), espace)
    return espace["taux"]


def hexs(valeurs) -> list[str]:
    return [vers_hex(v) for v in valeurs]


# --- Les réglages -------------------------------------------------------------------------------


def test_taux_proposes_et_presets():
    assert TAUX_PROPOSES == (0.001, 0.003, 0.01, 0.03, 0.1, 0.3)
    assert list(PRESETS_MINI) == ["complet", "avant-gout"]
    assert PRESETS_MINI["complet"] == ReglagesMini(pas_total=3000, echauffement=100)
    assert PRESETS_MINI["avant-gout"] == ReglagesMini(pas_total=600, echauffement=50)
    assert PRESETS_MINI["complet"].taux_max in TAUX_PROPOSES
    with pytest.raises(TypeError):
        PRESETS_MINI["autre"] = PRESETS_MINI["complet"]  # type: ignore[index]


def test_reglages_par_defaut():
    r = ReglagesMini(pas_total=10, echauffement=2)
    assert dataclasses.asdict(r) == {
        "pas_total": 10,
        "echauffement": 2,
        "taux_max": 0.01,
        "lot": 8,
        "ratio_min": 0.1,
        "beta1": 0.9,
        "beta2": 0.95,
        "epsilon": 1e-8,
        "poids_decroissance": 0.1,
        "ecretage": 1.0,
        "graine": 1234,
        "validation_tous": 100,
        "nb_validation": 256,
        "nb_echantillons": 8,
    }
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.lot = 4  # type: ignore[misc]
    # Un entier donné pour un flottant est rangé en flottant, comme en TypeScript où 1000 et 1000.0 sont le même nombre.
    assert isinstance(ReglagesMini(pas_total=10, echauffement=2, taux_max=1000).taux_max, float)


@pytest.mark.parametrize(
    "mauvais",
    [
        {"pas_total": 0},
        {"pas_total": 2.0},
        {"echauffement": -1},
        {"lot": 0},
        {"lot": True},
        {"taux_max": 0.0},
        {"taux_max": -0.01},
        {"taux_max": math.inf},
        {"taux_max": math.nan},
        {"taux_max": "0.01"},
        {"ratio_min": 1.5},
        {"beta1": 1.0},
        {"beta2": -0.1},
        {"epsilon": 0.0},
        {"poids_decroissance": -0.1},
        {"ecretage": 0.0},
        {"graine": -1},
        {"graine": 2**32},
        {"graine": True},
        {"validation_tous": 0},
        {"nb_validation": 0},
        {"nb_echantillons": -1},
    ],
)
def test_reglages_refuses(mauvais):
    nom = next(iter(mauvais))
    with pytest.raises(ValueError, match=f"ReglagesMini : {nom} doit"):
        ReglagesMini(**({"pas_total": 10, "echauffement": 2} | mauvais))


def test_un_lot_plus_grand_que_la_liste_est_refuse():
    with pytest.raises(ValueError, match="lot de 19 prénoms.*18 prénoms d'entraînement"):
        Entraineur(ReglagesMini(pas_total=5, echauffement=1, lot=19), preparer(VINGT))
    with pytest.raises(TypeError, match="ReglagesMini"):
        Entraineur({"pas_total": 5, "echauffement": 1})  # type: ignore[arg-type]


# --- Le taux ------------------------------------------------------------------------------------


def test_taux_comme_forge():
    assert taux(50, 1000, 1e-3, 100) == pytest.approx(5e-4)
    assert taux(100, 1000, 1e-3, 100) == pytest.approx(1e-3)
    assert taux(550, 1000, 1e-3, 100) == pytest.approx(5.5e-4)
    assert taux(1000, 1000, 1e-3, 100) == pytest.approx(1e-4)


@pytest.mark.parametrize(
    ("pas_total", "taux_max", "echauffement", "ratio_min"),
    [(1000, 1e-3, 100, 0.1), (3000, 0.01, 100, 0.1), (600, 0.01, 50, 0.1), (10, 0.3, 0, 0.0), (5, 0.1, 10, 0.1)],
)
def test_taux_est_le_code_de_forge(pas_total, taux_max, echauffement, ratio_min):
    # Le même code que forge/entrainement/planning.py, avec notre cos au lieu de celui de la machine :
    # au bit près hors du cosinus, à un ou deux ulp près dans le cosinus.
    taux_forge = taux_de_forge()
    for pas in range(pas_total + 3):
        nous = taux(pas, pas_total, taux_max, echauffement, ratio_min)
        forge = taux_forge(pas, pas_total, taux_max, echauffement, ratio_min)
        if pas < echauffement or pas >= pas_total:
            assert vers_hex(nous) == vers_hex(forge), pas
        else:
            assert abs(nous - forge) <= 1e-15 * taux_max, (pas, nous, forge)


def test_taux_monte_puis_descend():
    r = PRESETS_MINI["complet"]
    valeurs = [taux(p, r.pas_total, r.taux_max, r.echauffement, r.ratio_min) for p in range(r.pas_total + 2)]
    assert valeurs[0] == 0.0
    # Au sommet, taux_min + (taux_max − taux_min) × 0,5 × 2 : taux_max à un ulp près, comme dans forge.
    assert valeurs[r.echauffement] == pytest.approx(r.taux_max, rel=1e-15)
    assert valeurs[r.pas_total] == valeurs[r.pas_total + 1] == r.ratio_min * r.taux_max
    for p in range(1, r.echauffement + 1):
        assert valeurs[p] > valeurs[p - 1], p
    for p in range(r.echauffement + 1, r.pas_total + 1):
        assert valeurs[p] <= valeurs[p - 1], p


# --- L'Entraineur -------------------------------------------------------------------------------


def test_vingt_pas():
    e = Entraineur(PRESETS_MINI["complet"])
    pertes = [e.faire_un_pas() for _ in range(20)]
    assert e.pas == 20 and not e.diverge
    assert somme(pertes[-5:]) / 5 < somme(pertes[:5]) / 5
    assert all(set(p) <= set(e.donnees.vocabulaire[1:]) and len(p) <= 15 for p in e.echantillons())


def test_depart():
    r = PRESETS_MINI["complet"]
    e = Entraineur(r)
    v = len(e.donnees.vocabulaire)
    assert e.config.taille_vocabulaire == v
    assert len(e.params) == nombre_parametres(e.config) == 32 * v + 3328
    assert (e.pas, e.diverge) == (0, False)
    assert e.taux_courant() == 0.0
    assert e.limite_divergence == 3.0 * log(float(v))
    assert e.reglages is r


def test_les_hasards_sont_separes():
    r = PRESETS_MINI["complet"]
    e = Entraineur(r)
    voc = e.donnees.vocabulaire
    # Les poids : Hasard(graine). Les prénoms inventés au pas p : un Hasard(graine + 2 + p) neuf.
    assert hexs(e.params) == hexs(initialiser(e.config, Hasard(r.graine)))
    assert e.echantillons() == [decoder(p, voc) for p in generer(e.config, e.params, Hasard(r.graine + 2), 8)]
    assert e.echantillons() == e.echantillons()
    e.faire_un_pas()
    assert e.echantillons() == [decoder(p, voc) for p in generer(e.config, e.params, Hasard(r.graine + 3), 8)]
    # Inventer des prénoms ou mesurer la validation ne change rien à l'entraînement.
    a, b = Entraineur(r), Entraineur(r)
    a.echantillons()
    a.perte_validation()
    for _ in range(3):
        assert vers_hex(a.faire_un_pas()) == vers_hex(b.faire_un_pas())
        a.echantillons()
    assert empreinte(a.params) == empreinte(b.params)


def test_perte_validation():
    r = PRESETS_MINI["complet"]
    e = Entraineur(r)
    e.faire_un_pas()
    attendu = perte(e.config, e.params, e.donnees.validation[: r.nb_validation])
    assert vers_hex(e.perte_validation()) == vers_hex(attendu)
    # Une liste de validation plus courte que nb_validation est prise en entier.
    petit = Entraineur(ReglagesMini(pas_total=5, echauffement=1, lot=4), preparer(VINGT))
    assert vers_hex(petit.perte_validation()) == vers_hex(perte(petit.config, petit.params, petit.donnees.validation))


def test_ordre_des_lots_et_nouveau_melange():
    # Hasard(graine + 1) mélange list(range(n)) au départ, puis chaque fois que position + lot > n.
    d = preparer(VINGT)
    n = len(d.entrainement)
    assert n == 18
    r = ReglagesMini(pas_total=50, echauffement=5, lot=4)
    e = Entraineur(r, d)
    h = Hasard(r.graine + 1)
    premier = list(range(n))
    h.melanger(premier)
    second = list(range(n))
    h.melanger(second)
    assert premier != second
    lots = [e._prochain_lot() for _ in range(6)]
    # 4 lots de 4 dans le premier ordre (16 prénoms) ; les 2 derniers ne suffisent pas pour un lot.
    indices = [premier[0:4], premier[4:8], premier[8:12], premier[12:16], second[0:4], second[4:8]]
    assert lots == [[d.entrainement[i] for i in groupe] for groupe in indices]
    assert e.donnees is d


def test_un_lot_juste_a_la_fin_ne_remelange_pas():
    d = preparer(VINGT)
    r = ReglagesMini(pas_total=50, echauffement=5, lot=6)  # 18 = 3 × 6 : position + lot = n au troisième lot
    e = Entraineur(r, d)
    h = Hasard(r.graine + 1)
    premier = list(range(18))
    h.melanger(premier)
    second = list(range(18))
    h.melanger(second)
    lots = [e._prochain_lot() for _ in range(4)]
    indices = [premier[0:6], premier[6:12], premier[12:18], second[0:6]]
    assert lots == [[d.entrainement[i] for i in groupe] for groupe in indices]


@pytest.mark.parametrize("ecretage", [1.0, 100.0])
def test_deux_pas_comme_adamw_ecrit_autrement(ecretage):
    # La recette d'AdamW écrite autrement : les corrections de biais par beta ** pas, la décroissance des
    # poids dans la même parenthèse, la norme par math.fsum. Mêmes nombres, à l'arrondi près.
    r = dataclasses.replace(PRESETS_MINI["complet"], ecretage=ecretage)
    e = Entraineur(r)
    c = e.config
    params = list(e.params)
    m = [0.0] * len(params)
    v = [0.0] * len(params)
    n = len(e.donnees.entrainement)
    ordre = list(range(n))
    Hasard(r.graine + 1).melanger(ordre)
    for pas in (1, 2):
        lot = [e.donnees.entrainement[ordre[(pas - 1) * r.lot + i]] for i in range(r.lot)]
        g = [0.0] * len(params)
        perte_du_lot = perte_et_gradient(c, params, lot, g)
        norme = math.sqrt(math.fsum(x * x for x in g))
        # Au départ, la norme du gradient d'un lot dépasse 1 : l'écrêtage à 1 sert dès le premier pas.
        assert norme > 1.0 and norme < 100.0
        if norme > ecretage:
            g = [x * ecretage / norme for x in g]
        lr = r.taux_max * pas / r.echauffement
        for i in range(len(params)):
            m[i] = r.beta1 * m[i] + (1 - r.beta1) * g[i]
            v[i] = r.beta2 * v[i] + (1 - r.beta2) * g[i] ** 2
            m_chapeau = m[i] / (1 - r.beta1**pas)
            v_chapeau = v[i] / (1 - r.beta2**pas)
            params[i] = params[i] - lr * (m_chapeau / (math.sqrt(v_chapeau) + r.epsilon) + r.poids_decroissance * params[i])
        assert e.faire_un_pas() == pytest.approx(perte_du_lot, rel=1e-12)
        assert e.taux_courant() == pytest.approx(lr, rel=1e-15)
        for i in range(len(params)):
            assert e.params[i] == pytest.approx(params[i], rel=1e-9, abs=1e-15), (pas, i)


def test_un_taux_trop_grand_diverge_sans_toucher_aux_parametres():
    r = dataclasses.replace(PRESETS_MINI["complet"], taux_max=1000.0)
    e = Entraineur(r)
    while not e.diverge:
        assert e.pas < 50, "un taux de 1 000 aurait dû faire exploser l'erreur"
        copie = hexs(e.params)
        perte_du_pas = e.faire_un_pas()
    # Le premier pas part du hasard (erreur proche de ln V) : il ne diverge pas.
    assert e.pas >= 2
    assert not math.isfinite(perte_du_pas) or perte_du_pas > e.limite_divergence
    # Le pas qui diverge ne touche pas aux paramètres, et les suivants ne font plus rien.
    assert hexs(e.params) == copie
    pas = e.pas
    for _ in range(3):
        assert vers_hex(e.faire_un_pas()) == vers_hex(perte_du_pas)
    assert e.pas == pas and hexs(e.params) == copie


def test_une_erreur_non_numerique_diverge_aussi():
    e = Entraineur(PRESETS_MINI["complet"])
    e.params[0] = math.nan  # le plongement du bord, lu au début de chaque prénom
    perte_du_pas = e.faire_un_pas()
    assert perte_du_pas != perte_du_pas
    assert e.diverge and e.pas == 1
    assert vers_hex(e.faire_un_pas()) == vers_hex(math.nan) and e.pas == 1


# --- Le test long -------------------------------------------------------------------------------


@pytest.mark.lent
def test_l_entrainement_complet_apprend_vraiment():
    r = PRESETS_MINI["complet"]
    e = Entraineur(r)
    depart = e.perte_validation()
    while e.pas < r.pas_total:
        e.faire_un_pas()
    fin = e.perte_validation()
    print(f"perte de validation : {depart} au départ, {fin} au pas {e.pas}")
    print(f"motifs : {vers_hex(depart)} au départ, {vers_hex(fin)} au pas {e.pas}, empreinte {empreinte(e.params)}")
    print("prénoms inventés :", ", ".join(e.echantillons()))
    assert not e.diverge
    assert fin <= 2.45
    assert depart - fin >= 1.0
    # Les mêmes bits qu'en TypeScript (entrainement-long.test.ts).
    assert vers_hex(depart) == LONG_VALIDATION_DEPART
    assert vers_hex(fin) == LONG_VALIDATION_FIN
    assert empreinte(e.params) == LONG_PARAMS_EMPREINTE
