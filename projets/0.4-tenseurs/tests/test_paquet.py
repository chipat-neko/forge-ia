"""Le paquet lui-même : ses régions de code et ses imports.

Les extraits du chapitre 0.4 sont tirés des régions `# region: <nom>` /
`# fin: <nom>` du paquet (CodeExplique). Chaque `# fin:` suit immédiatement la
dernière ligne de code de sa région : l'extrait ne finit pas par une ligne
vide.

Le paquet tourne aussi sur Colab et sous Linux : il n'importe que torch et la
bibliothèque standard (ni numpy, ni psutil), et `winreg`, qui n'existe que
sous Windows, seulement dans une fonction.
"""

import ast
import pathlib
import re
import sys

import pytest

PAQUET = pathlib.Path(__file__).resolve().parents[1] / "tenseurs"
MARQUEUR = re.compile(r"^\s*#\s*(region|fin):\s*(\S+)\s*$")

# Les régions que le chapitre montre, fichier par fichier.
REGIONS = {
    "appareil.py": ["appareil"],
    "formes.py": ["diffusion", "produit"],
    "memoire.py": ["memoire"],
    "exemples.py": ["creer", "lire", "calculer"],
    "chrono.py": ["chrono", "transfert"],
}


def regions_du_fichier(chemin: pathlib.Path) -> list[str]:
    """Les noms des régions du fichier, dans l'ordre ; vérifie que chacune est bien fermée."""
    lignes = chemin.read_text(encoding="utf-8").splitlines()
    ouvertes: list[str] = []
    noms: list[str] = []
    for i, ligne in enumerate(lignes):
        trouve = MARQUEUR.match(ligne)
        if not trouve:
            continue
        sorte, nom = trouve.groups()
        if sorte == "region":
            assert nom not in noms, f"{chemin.name}, ligne {i + 1} : la région « {nom} » est ouverte deux fois."
            ouvertes.append(nom)
            noms.append(nom)
            continue
        assert ouvertes and ouvertes[-1] == nom, f"{chemin.name}, ligne {i + 1} : « # fin: {nom} » ne ferme rien."
        ouvertes.pop()
        precedente = lignes[i - 1]
        assert precedente.strip() and not MARQUEUR.match(precedente), (
            f"{chemin.name}, ligne {i + 1} : « # fin: {nom} » doit suivre immédiatement la dernière ligne "
            "de code de la région, sans ligne vide avant."
        )
    assert not ouvertes, f"{chemin.name} : région(s) jamais fermée(s) : {ouvertes}."
    return noms


def test_les_regions_du_chapitre():
    trouvees = {chemin.name: regions_du_fichier(chemin) for chemin in sorted(PAQUET.glob("*.py"))}
    assert {nom: regions for nom, regions in trouvees.items() if regions} == REGIONS


def test_le_controle_des_regions_attrape_une_ligne_vide(tmp_path):
    fichier = tmp_path / "exemple.py"
    fichier.write_text("# region: r\nx = 1\n\n# fin: r\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="sans ligne vide avant"):
        regions_du_fichier(fichier)


def imports_du_paquet():
    """(fichier, module importé, nœud) pour chaque import du paquet."""
    for chemin in sorted(PAQUET.glob("*.py")):
        arbre = ast.parse(chemin.read_text(encoding="utf-8"))
        for noeud in ast.walk(arbre):
            if isinstance(noeud, ast.Import):
                for alias in noeud.names:
                    yield chemin.name, alias.name, noeud, arbre
            elif isinstance(noeud, ast.ImportFrom):
                yield chemin.name, noeud.module or "", noeud, arbre


def test_seulement_torch_et_la_bibliotheque_standard():
    for fichier, module, _, _ in imports_du_paquet():
        racine = module.split(".")[0]
        assert racine in sys.stdlib_module_names or racine in {"torch", "tenseurs"}, (
            f"{fichier} importe {module} : le paquet ne doit dépendre que de torch et de la bibliothèque "
            "standard (Colab n'a pas tout, et numpy n'est là que pour le message de PyTorch)."
        )


def test_winreg_seulement_dans_une_fonction():
    trouve = False
    for fichier, module, noeud, arbre in imports_du_paquet():
        if module != "winreg":
            continue
        trouve = True
        fonctions = [n for n in ast.walk(arbre) if isinstance(n, ast.FunctionDef)]
        assert any(noeud in ast.walk(f) for f in fonctions), (
            f"{fichier} importe winreg hors d'une fonction : sous Linux et sur Colab, l'import du module échouerait."
        )
    assert trouve, "nom_processeur() lit le registre de Windows avec winreg"
