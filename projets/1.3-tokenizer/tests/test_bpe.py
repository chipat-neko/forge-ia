from collections import Counter
import json, pathlib
from tokenizer_pedagogique.bpe import (MOTIF, TokenizerPedagogique, apprendre, charger_corpus,
    paire_la_plus_frequente, pre_decouper)
from tokenizer_pedagogique.attendus import calculer_attendus

CORPUS = charger_corpus()

def test_corpus_sans_retour_chariot():
    assert "\r" not in CORPUS

def test_pre_decouper():
    assert pre_decouper("Le forgeron  frappe, 2026 !\nFin") == [
        "Le", " forgeron", "  ", "frappe", ",", " 2026", " !", "\nFin"]

def test_espaces_unicode():
    # U+0085 est une espace (propriété White_Space) ; U+FEFF n'en est pas une.
    assert pre_decouper("a\u0085b") == ["a", "\u0085b"]
    assert pre_decouper("a\ufeffb") == ["a", "\ufeff", "b"]

def test_motif_sans_s():
    # \s n'a pas le même sens en Python et en JavaScript : le motif nomme la propriété Unicode.
    assert r"\s" not in MOTIF
    assert r"\p{White_Space}" in MOTIF
    assert MOTIF == (
        r"\p{White_Space}?[\p{L}\p{M}]+|\p{White_Space}?\p{N}+|"
        r"\p{White_Space}?[^\p{White_Space}\p{L}\p{N}]+|\p{White_Space}+")

def test_departage_des_egalites():
    assert paire_la_plus_frequente(Counter({("b", "a"): 2, ("a", "b"): 2})) == ("a", "b")

def test_fusions_du_corpus():
    fusions = apprendre(CORPUS, 200)
    assert len(fusions) == 165
    assert [(f.a, f.b, f.compte) for f in fusions[:5]] == [
        ("e", "s", 43), (" ", "l", 27), ("e", "n", 26), (" ", "d", 21), ("o", "n", 21)]
    assert (fusions[29].a, fusions[29].b, fusions[29].compte) == ("é", "c", 7)

def test_decoupages():
    tok = TokenizerPedagogique(CORPUS)
    assert len(tok.base) == 45
    phrase = "Les forgerons découpent le texte en jetons."
    assert len(tok.decouper(phrase, 0)) == 43
    assert len(tok.decouper(phrase, 60)) == 18
    assert [j.texte for j in tok.decouper(phrase, 100)] == [
        "L", "es", " forg", "er", "ons", " découp", "ent", " le", " t", "e", "x",
        "te", " en", " jetons", "."]
    assert len(tok.decouper("les forgerons", 30)) == 9
    assert len(tok.decouper("reforgeronnes", 165)) == 6
    assert len(tok.decouper("Le forgeron frappe le métal sur l'enclume.", 30)) == 33

def test_caractere_inconnu_et_texte_vide():
    tok = TokenizerPedagogique(CORPUS)
    assert tok.decouper("🙂", 10)[-1].id is None
    assert tok.decouper("", 30) == []

def test_attendus_a_jour():
    fichier = pathlib.Path(__file__).parent / "attendus.json"
    assert calculer_attendus() == json.loads(fichier.read_text(encoding="utf-8"))
