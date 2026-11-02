from collections import Counter
import json, pathlib
from tokenizer_pedagogique.bpe import (TokenizerPedagogique, apprendre, charger_corpus,
    paire_la_plus_frequente, pre_decouper)
from tokenizer_pedagogique.attendus import calculer_attendus

CORPUS = charger_corpus()

def test_corpus_sans_retour_chariot():
    assert "\r" not in CORPUS

def test_pre_decouper():
    assert pre_decouper("Le forgeron  frappe, 2026 !\nFin") == [
        "Le", " forgeron", "  ", "frappe", ",", " 2026", " !", "\nFin"]

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
