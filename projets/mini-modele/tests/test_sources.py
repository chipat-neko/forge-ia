"""Les fonctions non reproductibles n'entrent pas dans le chemin vérifié.

Les fichiers vérifiés doivent donner les mêmes bits en Python et en
TypeScript, sur toutes les machines. Seuls + − × ÷, la racine carrée,
floor, ldexp et frexp (exacts : ils ne touchent qu'à l'exposant) et les
opérations entières y sont permis. Le motif est cherché partout, commentaires
compris : un exemple de code interdit dans un commentaire serait vite recopié.
Le jumeau TypeScript a le même test (site/src/lib/mini-modele/sources.test.ts).

Règle des divisions entières, qu'aucun scan ne peut vérifier (le signe d'une
variable ne se lit pas dans le texte) : les indices sont toujours positifs, et
`%` et `//` ne servent que sur des entiers positifs (ou nuls pour le dividende).
Là, Python et JavaScript donnent le même résultat : `a % b` des deux côtés,
`a // b` en Python face à `Math.floor(a / b)` en TypeScript. Ailleurs, le `%` de
Python prend le signe du diviseur et celui de JavaScript le signe du dividende,
et le `//` d'un flottant n'est pas toujours floor(a / b) : on écrit alors
math.floor(a / b), et a - b * math.floor(a / b), des deux côtés.
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
OBLIGATOIRES = ["calcul", "donnees", "attention", "modele", "entrainement"]
# Les seuls noms du module math permis. Toute autre fonction de math (atan,
# hypot, prod, sumprod, fma…) peut arrondir autrement que le TypeScript.
MATH_PERMIS = {"sqrt", "floor", "ldexp", "frexp", "inf", "nan", "isnan", "isinf", "isfinite"}
# Les fonctions intégrées interdites, et ce qu'on écrit à leur place. pow fait le
# même appel à la libm que **, max et min traitent −0 autrement qu'une boucle
# « if v > m », round arrondit au pair : le TypeScript ne les refait pas au bit près.
INTEGREES_INTERDITES = re.compile(r"\b(pow|max|min|round|divmod)\(")
A_LA_PLACE = {
    "pow": "une boucle de produits (p = p * b, à chaque pas, comme b1t et b2t dans AdamW)",
    "max": "une boucle « if v > m » (maximum de mini_modele.calcul)",
    "min": "une boucle « if v < m », écrite de la même façon en TypeScript",
    "round": "math.floor(x + 0.5), écrit de la même façon en TypeScript",
    "divmod": "a // b et a % b, sur des entiers positifs seulement (voir la règle en tête de ce fichier)",
}
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


def test_aucune_fonction_integree_non_reproductible():
    for nom, texte in sources_verifiees():
        trouve = INTEGREES_INTERDITES.search(texte)
        assert trouve is None, (
            f"mini_modele/{nom}.py, ligne {numero_de_ligne(texte, trouve.start())} : « {trouve.group()} » "
            f"ne se refait pas au bit près en TypeScript. Écris à la place {A_LA_PLACE[trouve.group(1)]}."
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
    for interdit in ("pow(beta1, t)", "max(a, b)", "min(v)", "round(x)", "divmod(a, b)", "x = max(0.0, s)",
                     "builtins.pow(b, t)"):
        assert INTEGREES_INTERDITES.search(interdit), interdit
        assert INTEGREES_INTERDITES.search(interdit).group(1) in A_LA_PLACE
    for permis in ("maximum(v)", "minimum(v)", "deux_puissance(k)", "empower(x)", "arrondi(x)", "self.b1t * r.beta1"):
        assert not INTEGREES_INTERDITES.search(permis), permis
