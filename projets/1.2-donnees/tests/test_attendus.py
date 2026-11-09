"""Les attendus partagés avec le site sont à jour.

Le fichier tests/attendus.json est écrit par `uv run python -m donnees_pas_a_pas.attendus`
et relu par Vitest et par la page de parité du site. Si le code de forge ou les exemples
changent, ces tests échouent tant que le fichier n'est pas régénéré.
"""

import json

from donnees_pas_a_pas.attendus import (
    BLANCS_PYTHON,
    CHEMIN_ATTENDUS,
    TEXTES_PIEGES,
    calculer_attendus,
    coder,
    decoder,
    vers_json,
)

REGENERER = "Régénère-le avec « uv run python -m donnees_pas_a_pas.attendus » (dans projets/1.2-donnees)."


def lire() -> dict:
    return json.loads(CHEMIN_ATTENDUS.read_text(encoding="utf-8"))


def test_attendus_a_jour():
    assert CHEMIN_ATTENDUS.read_text(encoding="utf-8") == vers_json(calculer_attendus()) + "\n", REGENERER


def test_les_sections_sont_dans_l_ordre():
    assert list(lire()) == ["blancs_python", "textes", "licences", "tris"]


def test_blancs_python_sont_ceux_de_isspace():
    assert BLANCS_PYTHON == [i for i in range(0x110000) if chr(i).isspace()]
    # U+FEFF n'en est pas un, alors que trimEnd() de JavaScript le retire : c'est le piège.
    assert 0xFEFF not in BLANCS_PYTHON and 0x3000 in BLANCS_PYTHON and 0xA0 in BLANCS_PYTHON
    assert lire()["blancs_python"] == BLANCS_PYTHON


def test_les_pieges_sont_dans_les_textes_de_reference():
    noms = [t["nom"] for t in lire()["textes"]]
    for attendu in ["199 caractères", "200 caractères", "100 000 x", "U+3000 en fin", "U+2028 en fin", "U+00A0 en fin", "U+FEFF en fin"]:
        assert attendu in noms, attendu


def test_les_demi_paires_s_ecrivent_en_points_de_code():
    # Un texte avec une moitié de paire ne s'écrit pas en UTF-8 : le fichier le donne en liste d'entiers.
    texte = "a\ud800b"
    assert coder(texte) == [0x61, 0xD800, 0x62]
    assert decoder(coder(texte)) == texte
    assert decoder(coder("x" * 100_000)) == "x" * 100_000 and len(json.dumps(coder("x" * 100_000))) < 100
    assert coder("é") == "é"
    entrees = [t["entree"] for t in lire()["textes"]]
    assert any(isinstance(e, list) for e in entrees)
    # Les textes nettoyés n'ont plus aucune moitié de paire : ce sont des chaînes ordinaires.
    assert all(not isinstance(t["nettoye"], list) for t in lire()["textes"])


def test_un_texte_de_reference_va_en_validation():
    # Sinon, la parité ne verrait jamais la branche « validation » de estValidation.
    places = {t["nom"]: t["validation"] for t in lire()["textes"]}
    assert places["un texte mis de côté pour la validation"] is True
    assert sum(places.values()) == 1


def test_les_textes_de_reference_sont_tous_decodables():
    for texte in TEXTES_PIEGES.values():
        assert decoder(coder(texte)) == texte
