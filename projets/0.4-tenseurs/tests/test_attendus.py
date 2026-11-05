"""Les attendus partagés avec le site sont à jour.

Le fichier tests/attendus-formes.json est écrit par
`uv run --extra cpu python -m tenseurs.attendus`. Ses formes viennent de
PyTorch lui-même (`torch.broadcast_shapes` et `torch.matmul`), pas des règles
du projet : le jumeau du site (site/src/lib/partie-0/formes.ts) est comparé à
PyTorch à travers lui. Si PyTorch, les exemples ou les cas de mémoire changent,
ces tests échouent tant que le fichier n'est pas régénéré.
"""

import itertools
import json

from tenseurs.attendus import CHEMIN_ATTENDUS, calculer_attendus, vers_json
from tenseurs.exemples import exemple_calculer, exemple_lire
from tenseurs.formes import forme_diffusee, forme_produit

REGENERER = "Régénère-le avec « uv run --extra cpu python -m tenseurs.attendus » (dans projets/0.4-tenseurs)."


def lire() -> dict:
    return json.loads(CHEMIN_ATTENDUS.read_text(encoding="utf-8"))


def en_tuple(forme: list[int] | None) -> tuple[int, ...] | None:
    return None if forme is None else tuple(forme)


def test_attendus_a_jour():
    assert CHEMIN_ATTENDUS.exists(), f"tests/attendus-formes.json est introuvable. {REGENERER}"
    # Le texte entier, écrit comme le fichier.
    assert vers_json(calculer_attendus()) == CHEMIN_ATTENDUS.read_text(encoding="utf-8"), (
        f"tests/attendus-formes.json n'est plus à jour. {REGENERER}"
    )


def test_fichier_en_utf8_et_lf():
    octets = CHEMIN_ATTENDUS.read_bytes()
    assert b"\r" not in octets, f"tests/attendus-formes.json contient des fins de ligne Windows. {REGENERER}"
    assert octets.endswith(b"}\n"), f"tests/attendus-formes.json doit finir par « }} » puis un retour à la ligne. {REGENERER}"


def test_forme_des_attendus():
    a = lire()
    assert list(a) == ["formes", "paires", "memoire", "exemples"]
    # Les 39 formes de 1 à 3 dimensions de tailles 1 à 3, avec leur écriture en Python.
    formes = [forme for n in (1, 2, 3) for forme in itertools.product((1, 2, 3), repeat=n)]
    assert a["formes"] == [{"forme": list(f), "texte": str(f)} for f in formes]
    assert a["formes"][0] == {"forme": [1], "texte": "(1,)"}
    # Les 1 521 paires, dans l'ordre : a d'abord, puis b.
    assert len(a["paires"]) == 1_521
    assert [(tuple(p["a"]), tuple(p["b"])) for p in a["paires"]] == list(itertools.product(formes, repeat=2))
    for p in a["paires"]:
        assert list(p) == ["a", "b", "diffusion", "produit"]
    for cas in a["memoire"]:
        assert list(cas) == ["forme", "dtype", "octets_par_nombre", "octets"]


def test_les_regles_du_projet_retrouvent_le_fichier():
    # Le fichier vient de PyTorch ; les règles du projet doivent le retrouver, paire par paire.
    for p in lire()["paires"]:
        a, b = tuple(p["a"]), tuple(p["b"])
        assert forme_diffusee(a, b) == en_tuple(p["diffusion"]), (a, b)
        assert forme_produit(a, b) == en_tuple(p["produit"]), (a, b)


def test_ce_que_lit_le_chapitre():
    a = lire()
    paires = {(tuple(p["a"]), tuple(p["b"])): p for p in a["paires"]}
    assert paires[(3, 1), (1, 3)]["diffusion"] == [3, 3]
    assert paires[(2, 3), (3, 2)] == {"a": [2, 3], "b": [3, 2], "diffusion": None, "produit": [2, 2]}
    assert paires[(2, 3), (3,)]["produit"] == [2]
    # Le produit de deux vecteurs est un nombre seul : sa forme est vide.
    assert paires[(3,), (3,)]["produit"] == []
    # Il y a des paires des quatre sortes : les deux règles, l'une seulement, aucune.
    sortes = {(p["diffusion"] is None, p["produit"] is None) for p in a["paires"]}
    assert sortes == {(False, False), (False, True), (True, False), (True, True)}
    memoire = {(tuple(c["forme"]), c["dtype"]): c for c in a["memoire"]}
    assert memoire[(4096, 4096), "float32"]["octets"] == 67_108_864
    assert memoire[(4096, 4096), "bfloat16"]["octets"] == 33_554_432
    assert all(c["octets_par_nombre"] in (1, 2, 4, 8) for c in a["memoire"])


def test_exemples_du_chapitre():
    e = lire()["exemples"]
    assert list(e) == ["creer", "lire", "calculer"]
    assert e["creer"]["matrice"] == {"forme": [2, 3], "dtype": "float32", "valeurs": [[0.0, 1.0, 2.0], [3.0, 4.0, 5.0]]}
    assert e["creer"]["entiers"]["dtype"] == "int64"
    assert e["lire"] == {**exemple_lire(), "forme": [2, 3]}
    assert e["calculer"] == exemple_calculer()
