"""Les fonctions non reproductibles n'entrent pas dans le chemin vérifié.

Les fichiers vérifiés doivent donner les mêmes bits en Python et en
TypeScript, sur toutes les machines. Seuls + − × ÷, la racine carrée,
floor, ldexp et frexp (exacts : ils ne touchent qu'à l'exposant) et les
opérations entières y sont permis. Le motif est cherché partout, commentaires
compris : un exemple de code interdit dans un commentaire serait vite recopié.
Le jumeau TypeScript a le même test (site/src/lib/mini-modele/sources.test.ts).
"""

import pathlib
import re

PAQUET = pathlib.Path(__file__).resolve().parent.parent / "mini_modele"

INTERDITS = re.compile(
    r"math\.(exp|log|log1p|log2|log10|expm1|cos|sin|tan|tanh|pow|fsum)\b|\*\*|\bsum\(|numpy|\brandom\b|statistics"
)
VERIFIES = ["calcul", "donnees", "attention", "modele", "entrainement", "exemple_attention"]
# Les fichiers vérifiés qui doivent déjà exister : sans cette liste, un fichier
# mal nommé ne serait jamais lu. Elle grandit à chaque tâche du plan 3.
OBLIGATOIRES = ["calcul"]
# Les seuls noms du module math permis. Toute autre fonction de math (atan,
# hypot, prod, sumprod, fma…) peut arrondir autrement que le TypeScript.
MATH_PERMIS = {"sqrt", "floor", "ldexp", "frexp", "inf", "nan", "isnan", "isinf", "isfinite"}
# Un marqueur de région est seul sur sa ligne : « # region: nom » ou « # fin: nom ».
MARQUEUR = re.compile(r"\s*# (region|fin): ([a-z0-9_]+)")


def sources_verifiees() -> list[tuple[str, str]]:
    """Le nom et le texte de chaque fichier vérifié présent."""
    sources = []
    for nom in VERIFIES:
        chemin = PAQUET / f"{nom}.py"
        if nom in OBLIGATOIRES or chemin.exists():
            sources.append((nom, chemin.read_text(encoding="utf-8")))
    return sources


def numero_de_ligne(texte: str, position: int) -> int:
    return texte.count("\n", 0, position) + 1


def test_fichiers_obligatoires_presents():
    for nom in OBLIGATOIRES:
        assert nom in VERIFIES, f"{nom} est obligatoire mais absent de VERIFIES : ajoute-le aux deux listes."
        assert (PAQUET / f"{nom}.py").exists(), (
            f"mini_modele/{nom}.py est introuvable. Un fichier vérifié a-t-il changé de nom ? "
            "Renomme-le, ou corrige OBLIGATOIRES et VERIFIES dans tests/test_sources.py."
        )


def test_aucune_fonction_non_reproductible():
    for nom, texte in sources_verifiees():
        trouve = INTERDITS.search(texte)
        assert trouve is None, (
            f"mini_modele/{nom}.py, ligne {numero_de_ligne(texte, trouve.start())} : « {trouve.group()} » "
            "n'est pas reproductible d'une machine à l'autre. Utilise exp, log, cos, somme ou Hasard de "
            "mini_modele.calcul, et des arguments explicites au lieu de **."
        )


def test_seulement_les_fonctions_exactes_de_math():
    for nom, texte in sources_verifiees():
        for trouve in re.finditer(r"\bmath\.(\w+)", texte):
            assert trouve.group(1) in MATH_PERMIS, (
                f"mini_modele/{nom}.py, ligne {numero_de_ligne(texte, trouve.start())} : math.{trouve.group(1)} "
                "n'est pas dans MATH_PERMIS. Remplace-la par des + − × ÷, ou ajoute-la à MATH_PERMIS "
                "seulement si elle est exacte (aucun arrondi)."
            )
        assert not re.search(r"^\s*(from\s+math\s+import|import\s+math\s+as)\b", texte, re.MULTILINE), (
            f"mini_modele/{nom}.py importe math sous un autre nom : écris « import math », puis math.sqrt, "
            "pour que ce test puisse vérifier chaque appel."
        )


def test_marqueurs_de_region_seuls_sur_leur_ligne():
    for nom, texte in sources_verifiees():
        ouvertes: list[str] = []
        for numero, ligne in enumerate(texte.splitlines(), start=1):
            if not re.search(r"#\s*(region|fin)\s*:", ligne):
                continue
            marqueur = MARQUEUR.fullmatch(ligne)
            assert marqueur, (
                f"mini_modele/{nom}.py, ligne {numero} : un marqueur s'écrit seul sur sa ligne, "
                f"« # region: nom » ou « # fin: nom » (reçu « {ligne.strip()} »)."
            )
            sorte, region = marqueur.groups()
            if sorte == "region":
                ouvertes.append(region)
            else:
                assert region in ouvertes, f"mini_modele/{nom}.py, ligne {numero} : « # fin: {region} » sans ouverture."
                ouvertes.remove(region)
        assert not ouvertes, f"mini_modele/{nom}.py : région(s) jamais fermée(s) : {', '.join(ouvertes)}."


def test_le_motif_attrape_les_interdits():
    for interdit in ("math.exp(x)", "math.log(x)", "math.fsum(v)", "x ** 2", "f(**options)", "{**a, **b}",
                     "sum(v)", "v.sum()", "import random", "import numpy", "statistics.fmean(v)"):
        assert INTERDITS.search(interdit), interdit
    for permis in ("math.sqrt(x)", "math.floor(x)", "somme(v)", "s += v", "Hasard(1234)", "a * b"):
        assert not INTERDITS.search(permis), permis
