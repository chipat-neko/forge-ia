"""Les problèmes de raisonnement : générés par programme, justes par construction, et leur vérification."""

import gzip
import json
import re
from fractions import Fraction

import pytest

from forge.conversation.format import Reponse, verifier_conversation
from forge.evaluation.langue import langue
from forge.raisonnement import problemes as pb
from forge.raisonnement.problemes import (
    DIFFICULTES,
    FAMILLES,
    FORMES,
    GRAINES_ENTRAINEMENT,
    GRAINES_EVALUATION,
    GRAINES_PREFERENCES,
    GRAINES_RL,
    GRAINES_VALIDATION_RL,
    GRAINES_VICTOIRE,
    OBJETS,
    PRENOMS,
    Probleme,
    conversation_de_probleme,
    generer_probleme,
    generer_problemes,
)
from forge.raisonnement.verification import est_juste, extraire_nombre

COUPLES = [(f, d) for f in FAMILLES for d in FORMES[f]]
ETAPE = re.compile(r"^(\d+) ([+−×÷]) (\d+) = (\d+)$")


def _reponse(texte: str, pensee: str | None = None) -> Reponse:
    return Reponse(texte=texte, pensee=pensee, ids=[], terminee=True)


# --- Les formes et les plages de graines ---


def test_les_familles_et_les_formes_sont_celles_de_la_fiche():
    assert FAMILLES == ("addition", "soustraction", "multiplication", "partage", "achats", "ages")
    assert DIFFICULTES == (1, 2, 3)
    assert FORMES == {
        "addition": (1, 2, 3),
        "soustraction": (1, 2, 3),
        "multiplication": (1, 2),
        "partage": (1, 2),
        "achats": (2, 3),
        "ages": (2, 3),
    }


def test_chaque_usage_a_sa_plage_de_graines():
    assert (
        GRAINES_ENTRAINEMENT,
        GRAINES_EVALUATION,
        GRAINES_RL,
        GRAINES_PREFERENCES,
        GRAINES_VICTOIRE,
        GRAINES_VALIDATION_RL,
    ) == (0, 1_000_000, 2_000_000, 3_000_000, 4_000_000, 5_000_000)


def test_les_listes_ont_la_taille_de_la_fiche():
    assert len(PRENOMS) == 30 and len(set(PRENOMS)) == 30
    assert len(OBJETS) == 20 and len({o.singulier for o in OBJETS}) == 20
    for o in OBJETS:
        assert o.singulier != o.pluriel
        assert 1 <= o.prix_min <= o.prix_max


@pytest.mark.parametrize(("famille", "difficulte"), [("addition", 4), ("addition", 0), ("multiplication", 3),
                                                      ("partage", 3), ("achats", 1), ("ages", 1), ("division", 1)])
def test_un_couple_absent_des_formes_leve_une_erreur(famille, difficulte):
    with pytest.raises(ValueError, match="famille|difficulté"):
        generer_probleme(famille, difficulte, 0)


# --- Les problèmes : justes par construction ---


def test_meme_graine_meme_probleme():
    for famille, difficulte in COUPLES:
        assert generer_probleme(famille, difficulte, 7) == generer_probleme(famille, difficulte, 7)


def test_des_graines_differentes_donnent_des_problemes_differents():
    for famille, difficulte in COUPLES:
        enonces = {generer_probleme(famille, difficulte, g).enonce for g in range(50)}
        assert len(enonces) > 40, (famille, difficulte)


@pytest.mark.parametrize(("famille", "difficulte"), COUPLES)
def test_chaque_etape_se_recalcule_et_la_derniere_donne_la_reponse(famille, difficulte):
    for graine in range(300):
        p = generer_probleme(famille, difficulte, graine)
        assert isinstance(p, Probleme)
        assert (p.famille, p.difficulte) == (famille, difficulte)
        assert p.id == f"{famille}-{difficulte}-{graine}"
        assert len(p.etapes) == difficulte
        nombres_de_l_enonce = {int(n) for n in re.findall(r"\d+", p.enonce)}
        connus = set(nombres_de_l_enonce)
        dernier = None
        for etape in p.etapes:
            lu = ETAPE.match(etape)
            assert lu, etape
            a, op, b, c = int(lu[1]), lu[2], int(lu[3]), int(lu[4])
            if op == "+":
                attendu = a + b
            elif op == "−":
                attendu = a - b
            elif op == "×":
                attendu = a * b
            else:
                assert a % b == 0, f"division inexacte : {etape}"
                attendu = a // b
            assert attendu == c, f"{etape} : {p.enonce}"
            # Chaque opérande vient de l'énoncé ou d'une étape déjà faite : rien n'est tiré de nulle part.
            assert a in connus and b in connus, f"{etape} : {p.enonce}"
            connus.add(c)
            dernier = c
        assert dernier == p.reponse
        assert p.reponse > 0
        assert p.enonce.endswith("?")


def test_le_signe_moins_des_etapes_est_le_signe_typographique():
    soustractions = [e for g in range(40) for e in generer_probleme("soustraction", 2, g).etapes]
    assert all("−" in e and "-" not in e for e in soustractions)


def test_les_nombres_de_la_difficulte_1_tiennent_dans_la_fiche():
    for g in range(300):
        for famille in ("addition", "soustraction"):
            a, _, b, _ = ETAPE.match(generer_probleme(famille, 1, g).etapes[0]).groups()
            assert 10 <= int(a) <= 99 and 10 <= int(b) <= 99
        a, _, b, _ = ETAPE.match(generer_probleme("multiplication", 1, g).etapes[0]).groups()
        assert 2 <= int(a) <= 9 and 10 <= int(b) <= 99


# --- Le français des énoncés ---


def test_les_enonces_sont_en_francais():
    problemes = generer_problemes(500, 0)
    assert len(problemes) > 400
    assert all(langue(p.enonce) != "autre" for p in problemes)
    assert all(langue(p.enonce) == "fr" for p in problemes[:100])


def test_quantite_accorde_le_nom_sur_toutes_les_valeurs():
    for o in OBJETS:
        for n in range(0, 1001):
            attendu = f"{n} {o.singulier if n < 2 else o.pluriel}"
            assert pb.quantite(n, o) == attendu
    pomme = next(o for o in OBJETS if o.singulier == "pomme")
    assert pb.quantite(1, pomme) == "1 pomme"
    assert pb.quantite(2, pomme) == "2 pommes"


def test_euros_et_ans_s_accordent_sur_toutes_les_valeurs():
    for n in range(0, 1001):
        assert pb.euros(n) == (f"{n} euro" if n < 2 else f"{n} euros")
        assert pb.ans(n) == (f"{n} an" if n < 2 else f"{n} ans")


def test_l_elision_de_la_preposition_de():
    assert pb.de("pommes") == "de pommes"
    assert pb.de("oranges") == "d'oranges"
    assert pb.de("abricots") == "d'abricots"
    assert pb.de("œufs") == "d'œufs"
    assert pb.de("Hugo") == "d'Hugo"
    assert pb.de("Éva") == "d'Éva"
    assert pb.de("Léa") == "de Léa"
    for o in OBJETS:
        assert not o.pluriel.lower().startswith("h"), "pas de h aspiré dans les objets"


def test_l_elision_de_que():
    assert pb.que("Léa") == "que Léa"
    assert pb.que("Alice") == "qu'Alice"
    assert pb.que("Hugo") == "qu'Hugo"
    assert pb.que("Éva") == "qu'Éva"
    for nom in PRENOMS:
        assert pb.que(nom) == ("que " if nom[0] not in "AEIOUYHÉ" else "qu'") + nom


def test_l_article_indefini_suit_le_genre():
    assert pb.un(next(o for o in OBJETS if o.singulier == "pomme")) == "une pomme"
    assert pb.un(next(o for o in OBJETS if o.singulier == "stylo")) == "un stylo"


def test_les_enonces_n_ont_ni_faute_d_accord_ni_d_elision():
    problemes = [generer_probleme(f, d, g) for f, d in COUPLES for g in range(400)]
    problemes += [generer_probleme(f, d, GRAINES_EVALUATION + g) for f, d in COUPLES for g in range(100)]
    for p in problemes:
        texte = p.enonce
        for o in OBJETS:
            assert not re.search(rf"(?<![\d,])(?:0|1) {o.pluriel}\b", texte), texte
            assert not re.search(rf"(?<![\d,])(?:[2-9]|\d\d+) {o.singulier}\b", texte), texte
            genre_faux = "une" if o.genre == "m" else "un"
            assert not re.search(rf"\b{genre_faux} {o.singulier}\b", texte), texte
        assert not re.search(r"(?<![\d,])(?:0|1) euros\b|(?<![\d,])(?:[2-9]|\d\d+) euro\b", texte), texte
        assert not re.search(r"(?<![\d,])(?:0|1) ans\b|(?<![\d,])(?:[2-9]|\d\d+) an\b", texte), texte
        assert not re.search(r"\bde [aeiouyhàâéèêîôûœ]", texte, re.IGNORECASE), texte
        assert not re.search(r"\bque [aeiouyhàâéèêîôûœ]", texte, re.IGNORECASE), texte
        assert not re.search(r"\bqu'[bcdfgjklmnpqrstvwxz]", texte, re.IGNORECASE), texte
        assert not re.search(r"\bd'[bcdfgjklmnpqrstvwxz]", texte, re.IGNORECASE), texte
        assert "  " not in texte and " ," not in texte and " ." not in texte, texte
        assert texte[0].isupper(), texte


def test_le_pronom_suit_le_genre_du_prenom():
    genres = dict(pb.GENRES_DES_PRENOMS)
    assert set(genres) == set(PRENOMS)
    assert sorted(set(genres.values())) == ["f", "m"]
    for f, d in COUPLES:
        for g in range(150):
            texte = generer_probleme(f, d, g).enonce
            noms = [n for n in PRENOMS if re.search(rf"\b{n}\b", texte)]
            assert noms, texte
            # Le « il » impersonnel (« y a-t-il », « il y a », « reste-t-il ») ne désigne personne.
            personnel = re.sub(r"y a-t-il|[Ii]l y a|reste-t-il", "", texte)
            masculin = re.search(r"\b[Ii]ls?\b", personnel)
            feminin = re.search(r"\b[Ee]lles?\b", personnel)
            if len(noms) > 1:
                assert not masculin and not feminin, texte
            elif genres[noms[0]] == "f":
                assert not masculin, texte
            else:
                assert not feminin, texte


def test_chaque_enonce_garde_ses_prenoms_distincts_et_les_cite_une_fois_au_moins():
    for f, d in COUPLES:
        for g in range(100):
            texte = generer_probleme(f, d, g).enonce
            noms = re.findall(r"\b(" + "|".join(PRENOMS) + r")\b", texte)
            assert noms
            if f == "ages":
                assert len(set(noms)) == (2 if d == 2 else 3)


# --- Entraînement contre évaluation ---


def test_aucun_enonce_commun_entre_entrainement_et_evaluation():
    entrainement = generer_problemes(2000, GRAINES_ENTRAINEMENT)
    evaluation = generer_problemes(500, GRAINES_EVALUATION)
    assert len(entrainement) > 1500 and len(evaluation) > 400
    assert {p.enonce for p in entrainement}.isdisjoint({p.enonce for p in evaluation})


def test_l_evaluation_a_ses_propres_prenoms_par_construction():
    reserves = set(pb.PRENOMS_EVALUATION)
    assert 0 < len(reserves) < len(PRENOMS) and reserves <= set(PRENOMS)
    motif = re.compile(r"\b(" + "|".join(PRENOMS) + r")\b")
    for debut, en_evaluation in [(GRAINES_ENTRAINEMENT, False), (GRAINES_EVALUATION, True), (GRAINES_RL, False),
                                 (GRAINES_PREFERENCES, False), (GRAINES_VICTOIRE, False),
                                 (GRAINES_VALIDATION_RL, False), (GRAINES_EVALUATION + 999_000, True)]:
        for p in generer_problemes(300, debut):
            noms = set(motif.findall(p.enonce))
            assert noms, p.enonce
            assert (noms <= reserves) if en_evaluation else noms.isdisjoint(reserves), (debut, p.enonce)


def test_l_usage_d_une_graine():
    assert pb.usage_de_la_graine(0) == "entrainement"
    assert pb.usage_de_la_graine(GRAINES_EVALUATION - 1) == "entrainement"
    assert pb.usage_de_la_graine(GRAINES_EVALUATION) == "evaluation"
    assert pb.usage_de_la_graine(GRAINES_RL - 1) == "evaluation"
    assert pb.usage_de_la_graine(GRAINES_RL) == "entrainement"
    assert pb.usage_de_la_graine(GRAINES_VALIDATION_RL + 7) == "entrainement"


def test_une_liste_ne_peut_pas_enjamber_la_plage_d_evaluation():
    with pytest.raises(ValueError, match="évaluation"):
        generer_problemes(10, GRAINES_EVALUATION - 5)
    with pytest.raises(ValueError, match="évaluation"):
        generer_problemes(10, GRAINES_RL - 5)
    with pytest.raises(ValueError, match="évaluation"):
        generer_problemes(3_000_000, 0)
    assert generer_problemes(10, GRAINES_EVALUATION - 10)  # juste avant : permis
    assert generer_problemes(10, GRAINES_RL)  # juste après : permis


def test_une_graine_hors_des_32_bits_est_refusee():
    # Au-delà de 2^32 − 1, SplitMix32 rejouerait une graine déjà vue : deux identifiants pour un problème.
    with pytest.raises(ValueError, match="graine"):
        generer_probleme("addition", 1, 2**32)
    with pytest.raises(ValueError, match="graine"):
        generer_probleme("addition", 1, -1)


# --- generer_problemes ---


def test_generer_problemes_prend_la_graine_depart_plus_i():
    problemes = generer_problemes(200, 50)
    assert 150 < len(problemes) <= 200
    for p in problemes:
        graine = int(p.id.rsplit("-", 1)[1])
        assert 50 <= graine < 250
        assert generer_probleme(p.famille, p.difficulte, graine) == p
    assert generer_problemes(200, 50) == problemes


def test_generer_problemes_retire_les_doublons():
    problemes = generer_problemes(2000, 0, familles=("addition",), difficultes=(1,))
    assert len({p.enonce for p in problemes}) == len(problemes)


def test_generer_problemes_filtre_les_familles_et_les_difficultes():
    problemes = generer_problemes(300, 0, familles=("achats", "ages"), difficultes=(3,))
    assert {(p.famille, p.difficulte) for p in problemes} == {("achats", 3), ("ages", 3)}
    problemes = generer_problemes(300, 0, difficultes=(1,))
    assert {p.famille for p in problemes} == {"addition", "soustraction", "multiplication", "partage"}
    assert {p.difficulte for p in problemes} == {1}
    assert {p.famille for p in generer_problemes(500, 0)} == set(FAMILLES)


def test_generer_problemes_sans_couple_permis_leve_une_erreur():
    with pytest.raises(ValueError, match="(?i)aucun"):
        generer_problemes(10, 0, familles=("multiplication",), difficultes=(3,))
    with pytest.raises(ValueError, match="famille"):
        generer_problemes(10, 0, familles=("geometrie",))
    with pytest.raises(ValueError, match="difficulté"):
        generer_problemes(10, 0, difficultes=(7,))


# --- La conversation ---


def test_la_conversation_de_probleme():
    p = generer_probleme("achats", 3, 11)
    tours = conversation_de_probleme(p)
    verifier_conversation(tours)
    assert [t.role for t in tours] == ["utilisateur", "assistant"]
    assert tours[0].texte == p.enonce
    assert tours[1].pensee == "\n".join(p.etapes)
    assert tours[1].texte == f"La réponse est {p.reponse}."


def test_la_conversation_est_juste_selon_la_verification():
    for f, d in COUPLES:
        p = generer_probleme(f, d, 3)
        assistant = conversation_de_probleme(p)[1]
        assert est_juste(_reponse(assistant.texte, assistant.pensee), p.reponse)


# --- extraire_nombre ---


@pytest.mark.parametrize(
    ("texte", "attendu"),
    [
        ("La réponse est 1\u202f234.", Fraction(1234)),
        ("La réponse est 1 234.", Fraction(1234)),
        ("La réponse est 1\u00a0234.", Fraction(1234)),
        ("1 234 567", Fraction(1234567)),
        ("12 345 678 pommes", Fraction(12345678)),
        ("1234", Fraction(1234)),
        ("12,5", Fraction(25, 2)),
        ("12,5.", Fraction(25, 2)),
        ("0,75", Fraction(3, 4)),
        ("1\u202f234,5", Fraction(2469, 2)),
        ("−3", Fraction(-3)),
        ("-3", Fraction(-3)),
        ("−3,5", Fraction(-7, 2)),
        ("Il fait −12 degrés", Fraction(-12)),
        ("(−7)", Fraction(-7)),
        ("x = -4", Fraction(-4)),
        ("3 puis 7", Fraction(7)),
        ("3 ou 4", Fraction(4)),
        ("La réponse est 42.", Fraction(42)),
        ("42 %", Fraction(42)),
        ("12 3456", Fraction(3456)),
        ("1 2 3", Fraction(3)),
        ("5-3", Fraction(3)),
        ("5 - 3", Fraction(3)),
        ("3.5", Fraction(7, 2)),
        ("Réponse : 12 pommes, soit 3 par ami", Fraction(3)),
        ("a, 5, b", Fraction(5)),
        ("0", Fraction(0)),
        ("007", Fraction(7)),
    ],
)
def test_extraire_nombre(texte, attendu):
    assert extraire_nombre(texte) == attendu


@pytest.mark.parametrize("texte", ["rien", "", "   ", "Je ne sais pas.", "trois pommes", "−", "- "])
def test_extraire_nombre_sans_nombre(texte):
    assert extraire_nombre(texte) is None


def test_extraire_nombre_rend_une_fraction():
    assert isinstance(extraire_nombre("12,5"), Fraction)
    assert extraire_nombre("4") == 4 and extraire_nombre("4") == Fraction(4, 1)


# --- est_juste ---


def test_est_juste_compare_le_nombre_du_texte():
    assert est_juste(_reponse("La réponse est 42."), 42)
    assert not est_juste(_reponse("La réponse est 41."), 42)
    assert est_juste(_reponse("La réponse est 1\u202f234."), 1234)
    assert est_juste(_reponse("La réponse est 1 234."), "1234")
    assert est_juste(_reponse("La réponse est 42."), "42")
    assert est_juste(_reponse("La réponse est 42."), " 42 ")
    assert est_juste(_reponse("−3"), -3)
    assert est_juste(_reponse("−3"), "−3")
    assert est_juste(_reponse("12,0"), 12)
    assert not est_juste(_reponse("12,5"), 12)


def test_est_juste_ignore_la_pensee_meme_quand_elle_contredit_le_texte():
    pensee = "10 + 5 = 15\n15 × 2 = 30"
    assert est_juste(_reponse("La réponse est 42.", pensee), 42)
    assert not est_juste(_reponse("La réponse est 30.", pensee), 42)
    # La bonne réponse est dans la pensée seulement : ce qui compte est le texte.
    assert not est_juste(_reponse("Je ne sais plus.", "le résultat est 42"), 42)
    assert not est_juste(_reponse("", "42"), 42)
    assert not est_juste(_reponse("La réponse est 41.", "donc 42"), 42)


def test_est_juste_cas_ambigus():
    assert not est_juste(_reponse("rien"), 0)
    assert not est_juste(_reponse(""), 0)
    assert est_juste(_reponse("3 puis 7"), 7)  # le dernier nombre
    assert not est_juste(_reponse("7 puis 3"), 7)
    assert not est_juste(_reponse("La réponse est 42."), "pas un nombre")
    assert not est_juste(_reponse("La réponse est 42."), "")


# --- La commande ---


def _lire(dossier):
    lignes = []
    for fragment in sorted(dossier.glob("problemes-*.jsonl.gz")):
        with gzip.open(fragment, "rt", encoding="utf-8") as f:
            lignes += [json.loads(ligne) for ligne in f]
    return lignes


def test_la_commande_problemes_ecrit_les_fragments_l_index_et_le_marqueur(tmp_path, monkeypatch, capsys):
    from forge.__main__ import main

    monkeypatch.setenv("FORGE_DONNEES", str(tmp_path))
    assert main(["problemes", "--sortie", "essai", "--nombre", "300", "--graine-depart", "10"]) == 0
    dossier = tmp_path / "problemes" / "essai"
    assert (dossier / ".complet").is_file()
    index = json.loads((dossier / "index.json").read_text(encoding="utf-8"))
    assert index["usage"] == "entrainement"
    assert index["graine_depart"] == 10 and index["nombre"] == 300
    assert index["familles"] == list(FAMILLES) and index["difficultes"] == [1, 2, 3]
    elements = _lire(dossier)
    attendus = generer_problemes(300, 10)
    assert len(elements) == len(attendus) == index["elements"]
    assert [e["id"] for e in elements] == [p.id for p in attendus]
    assert elements[0] == {
        "id": attendus[0].id, "famille": attendus[0].famille, "difficulte": attendus[0].difficulte,
        "enonce": attendus[0].enonce, "etapes": list(attendus[0].etapes), "reponse": attendus[0].reponse,
    }
    sortie = capsys.readouterr().out
    assert str(dossier) in sortie


def test_la_commande_marque_l_usage_evaluation(tmp_path, monkeypatch):
    from forge.__main__ import main

    monkeypatch.setenv("FORGE_DONNEES", str(tmp_path))
    assert main(["problemes", "--sortie", "eval", "--nombre", "50", "--graine-depart", str(GRAINES_EVALUATION)]) == 0
    index = json.loads((tmp_path / "problemes" / "eval" / "index.json").read_text(encoding="utf-8"))
    assert index["usage"] == "evaluation"
    infos = json.loads((tmp_path / "problemes" / "eval" / ".complet").read_text(encoding="utf-8"))
    assert infos["usage"] == "evaluation"
    assert main(["problemes", "--sortie", "rl", "--nombre", "50", "--graine-depart", str(GRAINES_RL)]) == 0
    index = json.loads((tmp_path / "problemes" / "rl" / "index.json").read_text(encoding="utf-8"))
    assert index["usage"] == "entrainement"


def test_la_commande_filtre_les_difficultes_et_les_familles(tmp_path, monkeypatch):
    from forge.__main__ import main

    monkeypatch.setenv("FORGE_DONNEES", str(tmp_path))
    assert main(["problemes", "--sortie", "f", "--nombre", "100", "--graine-depart", "0",
                 "--difficultes", "1,2", "--familles", "addition,partage"]) == 0
    elements = _lire(tmp_path / "problemes" / "f")
    assert {(e["famille"], e["difficulte"]) for e in elements} <= {("addition", 1), ("addition", 2),
                                                                  ("partage", 1), ("partage", 2)}
    index = json.loads((tmp_path / "problemes" / "f" / "index.json").read_text(encoding="utf-8"))
    assert index["familles"] == ["addition", "partage"] and index["difficultes"] == [1, 2]


def test_la_commande_relancee_ne_refait_rien_et_refuse_d_autres_reglages(tmp_path, monkeypatch, capsys):
    from forge.__main__ import main

    monkeypatch.setenv("FORGE_DONNEES", str(tmp_path))
    argv = ["problemes", "--sortie", "r", "--nombre", "40", "--graine-depart", "5"]
    assert main(argv) == 0
    fichiers = {f.name: f.read_bytes() for f in (tmp_path / "problemes" / "r").iterdir()}
    assert main(argv) == 0
    assert {f.name: f.read_bytes() for f in (tmp_path / "problemes" / "r").iterdir()} == fichiers
    capsys.readouterr()
    assert main(["problemes", "--sortie", "r", "--nombre", "40", "--graine-depart", "6"]) == 1
    assert "r" in capsys.readouterr().err


def test_la_commande_refuse_les_reglages_impossibles(tmp_path, monkeypatch, capsys):
    from forge.__main__ import main

    monkeypatch.setenv("FORGE_DONNEES", str(tmp_path))
    assert main(["problemes", "--sortie", "x", "--nombre", "10", "--graine-depart", str(GRAINES_EVALUATION - 3)]) == 1
    assert "évaluation" in capsys.readouterr().err
    assert main(["problemes", "--sortie", "x", "--nombre", "10", "--graine-depart", "0", "--familles", "zzz"]) == 1
    assert "famille" in capsys.readouterr().err
    assert main(["problemes", "--sortie", "x", "--nombre", "10", "--graine-depart", "0", "--difficultes", "a"]) == 1
    assert main(["problemes", "--sortie", "x", "--nombre", "0", "--graine-depart", "0"]) == 1
    assert not (tmp_path / "problemes" / "x" / ".complet").exists()


def test_la_commande_reprend_un_dossier_interrompu(tmp_path, monkeypatch):
    from forge.__main__ import main
    from forge.fragments import SortieParFragments

    monkeypatch.setenv("FORGE_DONNEES", str(tmp_path))
    assert main(["problemes", "--sortie", "ref", "--nombre", "120", "--graine-depart", "0"]) == 0
    complet = _lire(tmp_path / "problemes" / "ref")

    # Un arrêt après 50 éléments : index et un fragment, sans marqueur.
    dossier = tmp_path / "problemes" / "coupe"
    index = (tmp_path / "problemes" / "ref" / "index.json").read_bytes()
    dossier.mkdir(parents=True)
    (dossier / "index.json").write_bytes(index)
    sortie = SortieParFragments(dossier, "problemes", par_fragment=50)
    for element in complet[:50]:
        sortie.ajouter(element)
    sortie.valider()
    assert not (dossier / ".complet").exists()
    assert main(["problemes", "--sortie", "coupe", "--nombre", "120", "--graine-depart", "0"]) == 0
    assert _lire(dossier) == complet
