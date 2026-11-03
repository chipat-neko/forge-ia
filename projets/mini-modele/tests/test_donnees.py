"""Le vocabulaire, l'encodage et le partage entraînement/validation des prénoms.

Le jumeau TypeScript (site/src/lib/mini-modele/donnees.ts) a les mêmes tests,
avec les mêmes valeurs écrites en toutes lettres, et relit les mêmes
attendus (tests/attendus-donnees.json) : le partage est identique dans les
deux langages, prénom par prénom.
"""

import dataclasses
import pathlib

import pytest

from mini_modele.calcul import Hasard
from mini_modele.donnees import (
    BORD,
    GRAINE_PARTAGE,
    Donnees,
    charger_prenoms,
    decoder,
    donnees_par_defaut,
    encoder,
    preparer,
    prenoms_du_texte,
    vocabulaire_de,
)

RACINE = pathlib.Path(__file__).resolve().parent.parent

# Vingt prénoms, et ce que le partage en fait : écrits ici en toutes lettres
# (tirés de Hasard(20261103).melanger), et les mêmes dans donnees.test.ts.
VINGT = ["an", "bo", "ci", "du", "el", "fa", "gu", "hi", "in", "jo", "ka", "lu", "ma", "ne", "ol", "pa", "qu", "ro", "su", "ti"]
VINGT_VALIDATION = ["bo", "ti"]
VINGT_ENTRAINEMENT = ["qu", "an", "ka", "ro", "ma", "el", "ci", "gu", "ol", "du", "ne", "in", "fa", "lu", "su", "jo", "pa", "hi"]


def test_partage_et_encodage():
    d = donnees_par_defaut()
    assert len(d.validation) == len(charger_prenoms()) // 10
    assert d.vocabulaire[0] == "." and list(d.vocabulaire[1:]) == sorted(set(d.vocabulaire[1:]))
    assert decoder(encoder("élodie", d.vocabulaire), d.vocabulaire) == "élodie"
    assert all(len(s) - 1 <= 16 for s in d.entrainement + d.validation)
    with pytest.raises(ValueError, match="Caractère inconnu"):
        encoder("ø", d.vocabulaire)


def test_les_constantes():
    assert BORD == "."
    assert GRAINE_PARTAGE == 20261103


def test_prenoms_du_texte():
    assert prenoms_du_texte("ana\nbea\n") == ["ana", "bea"]
    assert prenoms_du_texte("ana\nbea") == ["ana", "bea"]
    assert prenoms_du_texte("") == []
    assert prenoms_du_texte("\n") == [""]
    assert prenoms_du_texte("ana\n\nbea\n") == ["ana", "", "bea"]


def test_charger_prenoms_lit_les_octets_tels_quels(tmp_path):
    fichier = tmp_path / "essai.txt"
    fichier.write_bytes("élodie\nzoé\n".encode("utf-8"))
    assert charger_prenoms(fichier) == ["élodie", "zoé"]
    assert charger_prenoms(str(fichier)) == ["élodie", "zoé"]
    # Pas de traduction des fins de ligne : le « \r » reste, comme avec « ?raw » côté site.
    fichier.write_bytes(b"ana\r\nbea\r\n")
    assert charger_prenoms(fichier) == ["ana\r", "bea\r"]


def test_charger_prenoms_par_defaut_est_le_fichier_versionne():
    texte = (RACINE / "donnees" / "prenoms.txt").read_bytes().decode("utf-8")
    assert charger_prenoms() == prenoms_du_texte(texte)
    assert charger_prenoms(RACINE / "donnees" / "prenoms.txt") == charger_prenoms()


def test_vocabulaire_de():
    assert vocabulaire_de(["élodie", "zoé", "ab"]) == ".abdeilozé"
    assert vocabulaire_de([]) == "."
    assert vocabulaire_de(["a-b", "ab"]) == ".-ab"
    # Par point de code : ÿ (U+00FF) avant œ (U+0153), et les lettres de plus de 16 bits aussi.
    assert vocabulaire_de(["œ", "ÿ", "z"]) == ".zÿœ"
    assert vocabulaire_de(["\U0001F642", "�"]) == ".�\U0001F642"


def test_vocabulaire_de_refuse_le_bord_dans_un_prenom():
    with pytest.raises(ValueError, match="réservé"):
        vocabulaire_de(["ana", "a.b"])


def test_encoder_et_decoder():
    assert encoder("ba", ".ab") == (0, 2, 1, 0)
    assert encoder("", ".ab") == (0, 0)
    assert decoder((0, 2, 1, 0), ".ab") == "ba"
    assert decoder([0, 0, 0], ".ab") == ""
    assert decoder((2, 0, 1, 2), ".ab") == "bab"  # les 0 sont ignorés, où qu'ils soient
    assert encoder("\U0001F642a", ".a\U0001F642") == (0, 2, 1, 0)
    assert decoder((0, 2, 1, 0), ".a\U0001F642") == "\U0001F642a"
    assert isinstance(encoder("a", ".a"), tuple)


def test_encoder_refuse_un_caractere_inconnu():
    with pytest.raises(ValueError, match="Caractère inconnu du vocabulaire : « c »"):
        encoder("abc", ".ab")
    # Le bord n'est pas une lettre : il ne s'encode pas dans un prénom.
    with pytest.raises(ValueError, match="Caractère inconnu du vocabulaire : « . »"):
        encoder("a.b", ".ab")


def test_decoder_refuse_un_numero_hors_du_vocabulaire():
    for numero in (3, 4, -1, -3, 1.5, True):
        with pytest.raises(ValueError, match="Numéro hors du vocabulaire") as erreur:
            decoder((0, 1, numero), ".ab")
        assert "de 0 à 2" in str(erreur.value)


def test_preparer_vingt_prenoms():
    d = preparer(VINGT)
    assert d.vocabulaire == vocabulaire_de(VINGT)
    assert [decoder(s, d.vocabulaire) for s in d.validation] == VINGT_VALIDATION
    assert [decoder(s, d.vocabulaire) for s in d.entrainement] == VINGT_ENTRAINEMENT
    assert d.connus == frozenset(VINGT)


def test_preparer_refait_le_partage_avec_hasard_et_len_divise_par_10():
    # À l'envers, donc pas dans l'ordre trié : le mélange part de l'ordre de la liste donnée.
    prenoms = [f"{a}{b}" for a in "abcdefghij" for b in "klmnopqrst"][:57][::-1]
    melanges = list(prenoms)
    Hasard(GRAINE_PARTAGE).melanger(melanges)
    d = preparer(prenoms)
    assert len(d.validation) == len(prenoms) // 10 == 5
    assert [decoder(s, d.vocabulaire) for s in d.validation] == melanges[:5]
    assert [decoder(s, d.vocabulaire) for s in d.entrainement] == melanges[5:]


def test_preparer_taille_de_la_validation():
    assert [len(preparer(["ab"] * n).validation) for n in (0, 1, 9, 10, 19, 20, 29)] == [0, 0, 0, 1, 1, 2, 2]


def test_preparer_ne_modifie_pas_la_liste_donnee_et_se_repete():
    prenoms = list(VINGT)
    d1 = preparer(prenoms)
    assert prenoms == VINGT
    assert preparer(prenoms) == d1
    assert preparer(tuple(prenoms)) == d1


def test_preparer_partage_sans_perte_ni_doublon():
    d = preparer(charger_prenoms())
    prenoms = charger_prenoms()
    tous = [decoder(s, d.vocabulaire) for s in d.entrainement + d.validation]
    assert len(tous) == len(prenoms) and sorted(tous) == prenoms
    assert d.connus == frozenset(prenoms)
    assert not set(decoder(s, d.vocabulaire) for s in d.validation) & set(decoder(s, d.vocabulaire) for s in d.entrainement)


def test_donnees_est_immuable_et_mise_en_cache():
    d = donnees_par_defaut()
    assert donnees_par_defaut() is d
    assert isinstance(d, Donnees) and isinstance(d.entrainement, tuple) and isinstance(d.connus, frozenset)
    assert all(isinstance(s, tuple) for s in d.entrainement[:3] + d.validation[:3])
    with pytest.raises(dataclasses.FrozenInstanceError):
        d.vocabulaire = "x"  # type: ignore[misc]


def test_les_numeros_sont_ceux_du_vocabulaire():
    d = donnees_par_defaut()
    toutes = d.entrainement + d.validation
    assert all(s[0] == 0 and s[-1] == 0 and 0 not in s[1:-1] for s in toutes)
    assert all(0 <= numero < len(d.vocabulaire) for s in toutes for numero in s)
    # Chaque caractère du vocabulaire sert au moins une fois.
    assert {numero for s in toutes for numero in s} == set(range(len(d.vocabulaire)))
