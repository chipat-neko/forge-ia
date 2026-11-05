"""Les exemples du chapitre 0.4 : créer, lire et calculer. Le chapitre commente ces valeurs."""

import torch

from tenseurs.exemples import exemple_calculer, exemple_creer, exemple_lire


def test_creer():
    t = exemple_creer()
    assert list(t) == ["nombre", "vecteur", "matrice", "lot", "entiers"]
    formes = {nom: tuple(tenseur.shape) for nom, tenseur in t.items()}
    assert formes == {"nombre": (), "vecteur": (4,), "matrice": (2, 3), "lot": (2, 3, 4), "entiers": (3,)}
    assert [tenseur.dim() for tenseur in t.values()] == [0, 1, 2, 3, 1]
    assert t["nombre"].item() == 3.5
    assert t["vecteur"].tolist() == [1.0, 2.0, 3.0, 4.0]
    assert t["matrice"].tolist() == [[0.0, 1.0, 2.0], [3.0, 4.0, 5.0]]
    assert t["lot"].count_nonzero().item() == 0
    # Des nombres à virgule : float32 par défaut. Des entiers : int64.
    assert {tenseur.dtype for nom, tenseur in t.items() if nom != "entiers"} == {torch.float32}
    assert t["entiers"].dtype == torch.int64 and t["entiers"].tolist() == [1, 2, 3]
    assert all(tenseur.device.type == "cpu" for tenseur in t.values())


def test_lire():
    assert exemple_lire() == {
        "forme": (2, 3),
        "dimensions": 2,
        "nombres": 6,
        "type": "torch.float32",
        "appareil": "cpu",
        "case": 5.0,
        "ligne": [3.0, 4.0, 5.0],
        "colonne": [0.0, 3.0],
    }


def test_calculer():
    assert exemple_calculer() == {
        "somme": [[11.0, 22.0], [33.0, 44.0]],
        "produit_case_par_case": [[10.0, 40.0], [90.0, 160.0]],
        "produit_matriciel": [[70.0, 100.0], [150.0, 220.0]],
        "total": 10.0,
        "moyenne_par_colonne": [2.0, 3.0],
        "diffusion": [[101.0, 202.0], [103.0, 204.0]],
    }


def test_les_valeurs_lues_sont_des_nombres_python():
    # .item() et .tolist() sortent les nombres du tenseur : de simples float de Python.
    lu = exemple_lire()
    assert type(lu["case"]) is float and type(lu["ligne"][0]) is float
    assert type(exemple_calculer()["total"]) is float
