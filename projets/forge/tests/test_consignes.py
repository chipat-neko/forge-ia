"""Les consignes vérifiables à la IFEval : celles d'IFEval-FR (lues dans M-IFEval) et les huit de la forge."""

from pathlib import Path

import pytest

import forge.evaluation.consignes as module_consignes
from forge.evaluation.consignes import (
    CONTRAINTES,
    IDS_IFEVAL_FR,
    PHRASES_FIN,
    VERIFICATEURS,
    Contrainte,
    exactitudes,
    respecte,
)
from forge.hasard import Hasard

CORPUS = Path(__file__).parent / "donnees" / "corpus_test.txt"

# Les identifiants relevés dans les 235 lignes de kurakurai/IFEval-FR (lecture du 17/11/2026).
IDS_ATTENDUS = (
    "fr:change_case:capital_word_frequency",
    "fr:change_case:french_capital",
    "fr:change_case:french_lowercase",
    "fr:combination:repeat_prompt",
    "fr:combination:two_responses",
    "fr:detectable_content:informal_address",
    "fr:detectable_content:no_digits",
    "fr:detectable_content:number_placeholders",
    "fr:detectable_content:postscript",
    "fr:detectable_format:constrained_response",
    "fr:detectable_format:json_format",
    "fr:detectable_format:multiple_sections",
    "fr:detectable_format:number_bullet_lists",
    "fr:detectable_format:number_highlighted_sections",
    "fr:detectable_format:title",
    "fr:keywords:existence",
    "fr:keywords:forbidden_words",
    "fr:keywords:frequency",
    "fr:keywords:letter_frequency",
    "fr:language:response_language",
    "fr:length_constraints:nth_paragraph_first_word",
    "fr:length_constraints:number_paragraphs",
    "fr:length_constraints:number_sentences",
    "fr:length_constraints:number_words",
    "fr:punctuation:no_comma",
    "fr:special_character:accents",
    "fr:special_character:ethel_or_cedilla",
    "fr:special_character:no_accents",
    "fr:startend:end_checker",
    "fr:startend:quotation",
)

FR = "le forgeron chauffe le fer et il le tord sur l'enclume."

# (identifiant, kwargs, réponse juste, réponse fausse) : deux exemples au moins par identifiant.
EXEMPLES = [
    ("fr:change_case:capital_word_frequency", {"capital_frequency": 2, "capital_relation": "au moins"},
     "Il y a TROIS mots EN majuscules.", "Un seul MOT ici."),
    ("fr:change_case:capital_word_frequency", {"capital_frequency": 2, "capital_relation": "moins de"},
     "Un seul MOT ici.", "Il y a TROIS mots EN majuscules."),
    ("fr:change_case:french_capital", {}, FR.upper(), "Le forgeron chauffe le fer et il le tord."),
    ("fr:change_case:french_capital", {}, "LE FORGERON ET LE FER SUR LE FEU.", FR),
    ("fr:change_case:french_lowercase", {}, FR, "Le forgeron chauffe le fer et il le tord."),
    ("fr:change_case:french_lowercase", {}, "le chat est sur la table de la cuisine.",
     "the cat is on the table of the house"),
    ("fr:combination:repeat_prompt", {"prompt_to_repeat": "Écrivez un poème."},
     "Écrivez un poème. Voici mon poème.", "Voici : Écrivez un poème."),
    ("fr:combination:repeat_prompt", {"prompt_to_repeat": "Écrivez un poème."},
     "  écrivez un poème. Fin.", "Voici mon poème."),
    ("fr:combination:two_responses", {}, "Première réponse.\n******\nSeconde réponse.", "Une seule réponse."),
    ("fr:combination:two_responses", {}, "Un.******Deux.", "Pareil.******Pareil."),
    ("fr:detectable_content:informal_address", {}, "Tu sais, ton ami t'attend.",
     "Vous savez, votre ami vous attend."),
    ("fr:detectable_content:informal_address", {}, "Je t'aime.", "Y a-t-il quelqu'un ?"),
    ("fr:detectable_content:no_digits", {}, "Trois pommes.", "3 pommes."),
    ("fr:detectable_content:no_digits", {}, "Rien à compter.", "Il y en a 12."),
    ("fr:detectable_content:number_placeholders", {"num_placeholders": 2},
     "Bonjour [nom], voici [adresse].", "Bonjour [nom]."),
    ("fr:detectable_content:number_placeholders", {"num_placeholders": 1}, "Ici [x].", "Ici rien."),
    ("fr:detectable_content:postscript", {"postscript_marker": "P.S."}, "Texte.\nP.S. À bientôt.",
     "Texte sans post-scriptum."),
    ("fr:detectable_content:postscript", {"postscript_marker": "P.P.S"}, "Texte.\nP.P.S. Encore.",
     "Texte.\nP.S. Seulement."),
    ("fr:detectable_content:postscript", {"postscript_marker": "PS"}, "Texte.\nPS : un mot.", "Les temps changent."),
    ("fr:detectable_format:constrained_response", {}, "Oui.", "Absolument pas."),
    ("fr:detectable_format:constrained_response", {}, "Je dirais : Peut-être.", "Certainement"),
    ("fr:detectable_format:json_format", {}, '{"a": 1}', "pas du json"),
    ("fr:detectable_format:json_format", {}, '```json\n{"a": [1, 2]}\n```', '{"a": NaN}'),
    ("fr:detectable_format:multiple_sections", {"section_spliter": "Section", "num_sections": 2},
     "Section 1\nA\nSection 2\nB", "Section 1\nA"),
    ("fr:detectable_format:multiple_sections", {"section_spliter": "Partie", "num_sections": 3},
     "Partie 1 a Partie 2 b Partie 3 c", "Partie 1 a Partie 2 b"),
    ("fr:detectable_format:number_bullet_lists", {"num_bullets": 2}, "* Un\n* Deux", "* Un\n* Deux\n* Trois"),
    ("fr:detectable_format:number_bullet_lists", {"num_bullets": 2}, "**Titre**\n- a\n- b", "Rien du tout"),
    ("fr:detectable_format:number_highlighted_sections", {"num_highlights": 2}, "*un* et *deux*", "*un* seul"),
    ("fr:detectable_format:number_highlighted_sections", {"num_highlights": 2}, "**a** et *b*", "**a** et ** **"),
    ("fr:detectable_format:title", {}, "##Mon titre##\nTexte", "Pas de titre"),
    ("fr:detectable_format:title", {}, "Texte\n##Autre titre## fin", "#### vide"),
    ("fr:keywords:existence", {"keywords": ["forge", "enclume"]}, "La Forge et l'enclume.", "La forge seule."),
    ("fr:keywords:existence", {"keywords": ["fer"]}, "Du FER.", "Du bois."),
    ("fr:keywords:forbidden_words", {"forbidden_words": ["chat", "chien"]}, "Un oiseau.", "Le chat dort."),
    ("fr:keywords:forbidden_words", {"forbidden_words": ["chat"]}, "Un chaton.", "Un CHAT."),
    ("fr:keywords:frequency", {"keyword": "fer", "frequency": 2, "relation": "au moins"}, "fer et fer", "fer"),
    ("fr:keywords:frequency", {"keyword": "fer", "frequency": 2, "relation": "moins de"}, "fer", "fer fer"),
    ("fr:keywords:letter_frequency", {"letter": "z", "let_frequency": 2, "let_relation": "au moins"},
     "zèbre zéro", "zèbre"),
    ("fr:keywords:letter_frequency", {"letter": "z", "let_frequency": 2, "let_relation": "moins de"},
     "zèbre", "ZZZ"),
    ("fr:language:response_language", {"language": "ko"}, "한국어로 답합니다. 안녕하세요.", FR),
    ("fr:language:response_language", {"language": "fi"}, "Tämä on suomea ja se on hyvä.", FR),
    ("fr:language:response_language", {"language": "fr"}, FR, "The smith heats the iron and then bends it."),
    ("fr:length_constraints:nth_paragraph_first_word",
     {"num_paragraphs": 2, "nth_paragraph": 2, "first_word": "Inversement"},
     "Un.\n\nInversement, deux.", "Un.\n\nAutrement, deux."),
    ("fr:length_constraints:nth_paragraph_first_word",
     {"num_paragraphs": 2, "nth_paragraph": 1, "first_word": "L"},
     "L'un.\n\nDeux.", "Le un.\n\nDeux.\n\nTrois."),
    ("fr:length_constraints:number_paragraphs", {"num_paragraphs": 2}, "Un\n***\nDeux", "Un"),
    ("fr:length_constraints:number_paragraphs", {"num_paragraphs": 2}, "***Un***Deux", "Un\n***\n***\nTrois"),
    ("fr:length_constraints:number_sentences", {"num_sentences": 2, "relation": "au moins"}, "Un. Deux.", "Un."),
    ("fr:length_constraints:number_sentences", {"num_sentences": 3, "relation": "moins de"},
     "Un. Deux ?", "Un. Deux ! Trois. Quatre."),
    ("fr:length_constraints:number_words", {"num_words": 5, "relation": "au moins"},
     "un deux trois quatre cinq", "un deux"),
    ("fr:length_constraints:number_words", {"num_words": 5, "relation": "moins de"},
     "un deux", "un deux trois quatre cinq"),
    ("fr:punctuation:no_comma", {}, "Sans virgule.", "Avec, virgule."),
    ("fr:punctuation:no_comma", {}, "Un point.", "a,b"),
    ("fr:special_character:accents", {"word_to_accentuate": {"lecon": "leçon"}}, "La leçon.", "La lecon."),
    ("fr:special_character:accents", {"word_to_accentuate": {"evenements": "événements"}},
     "Des événements.", "Des evenements."),
    ("fr:special_character:ethel_or_cedilla", {"forbidden_char": "ç"}, "Une lecon.", "Une leçon."),
    ("fr:special_character:ethel_or_cedilla", {"forbidden_char": "œ"}, "Un oeuf.", "UN ŒUF."),
    ("fr:special_character:no_accents", {}, "Une idee simple.", "Une idée."),
    ("fr:special_character:no_accents", {}, "Du ble.", "Du blé, ÇA"),
    ("fr:startend:end_checker", {"end_phrase": "Que puis-je faire pour vous ?"},
     "Bonjour. Que puis-je faire pour vous ?", "Que puis-je faire pour vous ? Merci."),
    ("fr:startend:end_checker", {"end_phrase": "Fin."}, '"Voilà. fin."', "Fin. Voilà."),
    ("fr:startend:quotation", {}, "«Bonjour»", "Bonjour"),
    ("fr:startend:quotation", {}, '"Bonjour"', "\"Bonjour' suite"),
]


def test_les_ids_d_ifeval_fr_sont_ceux_releves_et_tries():
    assert IDS_IFEVAL_FR == IDS_ATTENDUS
    assert list(IDS_IFEVAL_FR) == sorted(IDS_IFEVAL_FR)


def test_chaque_id_a_un_verificateur_strict():
    assert set(IDS_IFEVAL_FR) <= set(VERIFICATEURS)


def test_chaque_id_a_deux_exemples_au_moins():
    for identifiant in IDS_IFEVAL_FR:
        assert sum(1 for e in EXEMPLES if e[0] == identifiant) >= 2, identifiant


@pytest.mark.parametrize("identifiant, kwargs, juste, fausse", EXEMPLES)
def test_exemples_par_identifiant(identifiant, kwargs, juste, fausse):
    verifier = VERIFICATEURS[identifiant]
    assert verifier(juste, kwargs) is True
    assert verifier(fausse, kwargs) is False


def test_aucune_classe_de_caracteres_w_b_ou_d_dans_le_module():
    source = Path(module_consignes.__file__).read_text(encoding="utf-8")
    assert "\\w" not in source
    assert "\\b" not in source
    assert "\\d" not in source


def test_argument_manquant_leve_une_erreur_claire():
    with pytest.raises(ValueError, match="num_words"):
        VERIFICATEURS["fr:length_constraints:number_words"]("un deux", {})


def test_relation_inconnue_leve_une_erreur_claire():
    with pytest.raises(ValueError, match="relation"):
        VERIFICATEURS["fr:length_constraints:number_words"]("un deux", {"num_words": 2, "relation": "plus de"})


def test_respecte_rend_un_booleen_par_consigne():
    ids = ["fr:punctuation:no_comma", "fr:detectable_content:no_digits"]
    assert respecte("Un 1, deux.", ids, [{}, {}]) == [False, False]
    assert respecte("Un deux.", ids, [{}, {}]) == [True, True]
    assert respecte("Un 1.", ids, [{}, {}]) == [True, False]


def test_respecte_refuse_des_listes_de_longueurs_differentes():
    with pytest.raises(ValueError, match="kwargs"):
        respecte("x", ["fr:punctuation:no_comma"], [])


def test_respecte_refuse_un_identifiant_inconnu():
    with pytest.raises(ValueError, match="fr:inconnu"):
        respecte("x", ["fr:inconnu"], [{}])


def test_kwargs_none_vaut_dict_vide():
    assert respecte("Un.", ["fr:punctuation:no_comma"], [None]) == [True]


def test_exactitudes():
    resultat = exactitudes([[True, True], [True, False], [False]])
    assert resultat["n"] == 3
    assert resultat["invite_stricte"] == pytest.approx(1 / 3)
    assert resultat["consigne_stricte"] == pytest.approx(3 / 5)
    assert set(resultat) == {"invite_stricte", "consigne_stricte", "n"}


def test_exactitudes_sans_rien():
    assert exactitudes([]) == {"invite_stricte": 0.0, "consigne_stricte": 0.0, "n": 0}


# --- Les huit consignes de la forge ------------------------------------------------------------------------


def _par_id(identifiant: str) -> Contrainte:
    return next(c for c in CONTRAINTES if c.id == identifiant)


def test_les_huit_contraintes_dans_l_ordre():
    assert [c.id for c in CONTRAINTES] == [
        "mots_max", "phrases_max", "minuscules", "sans_virgule",
        "mot_obligatoire", "puces", "fin_imposee", "titre",
    ]
    assert all(isinstance(c, Contrainte) for c in CONTRAINTES)
    with pytest.raises(AttributeError):
        CONTRAINTES[0].id = "autre"  # type: ignore[misc]


def test_les_cinq_phrases_de_fin():
    assert len(PHRASES_FIN) == 5
    assert len(set(PHRASES_FIN)) == 5


def test_consignes_exactes():
    assert _par_id("mots_max").consigne({"n": 20}) == "Réponds en 20 mots au plus."
    assert _par_id("phrases_max").consigne({"n": 2}) == "Réponds en 2 phrases au plus."
    assert _par_id("minuscules").consigne({}) == "Écris toute ta réponse en minuscules."
    assert _par_id("sans_virgule").consigne({}) == "N'utilise aucune virgule."
    assert _par_id("mot_obligatoire").consigne({"mot": "forge"}) == "Emploie le mot « forge » dans ta réponse."
    assert _par_id("puces").consigne({"n": 3}) == "Réponds par exactement 3 puces, chacune commençant par « - »."
    assert _par_id("fin_imposee").consigne({"phrase": "Fin."}) == "Termine ta réponse par la phrase exacte : « Fin. »"
    assert _par_id("titre").consigne({}) == "Donne d'abord un titre entre doubles chevrons, comme « titre »."


QUESTION = "Pourquoi le forgeron chauffe-t-il le fer avant de le battre ?"

# (id, kwargs, deux réponses justes, deux réponses fausses)
EXEMPLES_FORGE = [
    ("mots_max", {"n": 5}, ["Un deux trois.", "Quatre cinq."], ["un deux trois quatre cinq six", ""]),
    ("phrases_max", {"n": 2}, ["Un.", "Un. Deux !"], ["Un. Deux. Trois.", "   "]),
    ("minuscules", {}, ["tout est bas.", "ça va bien 123"], ["Tout est bas.", "123"]),
    ("sans_virgule", {}, ["Sans virgule.", "Un point."], ["Avec, virgule.", ""]),
    ("mot_obligatoire", {"mot": "forge"}, ["La forge chauffe.", "FORGE !"], ["Le fer chauffe.", "Le forgeron."]),
    ("puces", {"n": 2}, ["- un\n- deux", "\n - un\n- deux\n"], ["- un\n- deux\n- trois", "Intro\n- un\n- deux"]),
    ("fin_imposee", {"phrase": "C'est tout pour le moment."},
     ["Voilà. C'est tout pour le moment.", "C'est tout pour le moment.\n"],
     ["C'est tout pour le moment. Merci.", "c'est tout pour le moment."]),
    ("titre", {}, ["« Mon titre »\nTexte", "<<Mon titre>>\n\nTexte"], ["Texte\n« Titre »", "« »\nTexte"]),
]


@pytest.mark.parametrize("identifiant, kwargs, justes, fausses", EXEMPLES_FORGE)
def test_chaque_contrainte_deux_justes_deux_fausses(identifiant, kwargs, justes, fausses):
    contrainte = _par_id(identifiant)
    for reponse in justes:
        assert contrainte.verifier(reponse, kwargs) is True, reponse
    for reponse in fausses:
        assert contrainte.verifier(reponse, kwargs) is False, reponse


def test_tirer_les_valeurs_permises():
    assert {_par_id("mots_max").tirer(Hasard(g), QUESTION)["n"] for g in range(60)} == {20, 40, 60}
    assert {_par_id("phrases_max").tirer(Hasard(g), QUESTION)["n"] for g in range(60)} == {1, 2, 3}
    assert {_par_id("puces").tirer(Hasard(g), QUESTION)["n"] for g in range(60)} == {2, 3, 4}
    assert {_par_id("fin_imposee").tirer(Hasard(g), QUESTION)["phrase"] for g in range(200)} == set(PHRASES_FIN)
    assert _par_id("minuscules").tirer(Hasard(1), QUESTION) == {}
    assert _par_id("sans_virgule").tirer(Hasard(1), QUESTION) == {}
    assert _par_id("titre").tirer(Hasard(1), QUESTION) == {}


def test_tirer_mot_obligatoire_prend_un_mot_de_la_question_de_cinq_lettres_ou_plus():
    mots_possibles = {"pourquoi", "forgeron", "chauffe", "avant", "battre"}
    vus = {_par_id("mot_obligatoire").tirer(Hasard(g), QUESTION)["mot"] for g in range(200)}
    assert vus == mots_possibles


def test_tirer_mot_obligatoire_sans_mot_assez_long_rend_none():
    assert _par_id("mot_obligatoire").tirer(Hasard(1), "Et toi ?") is None
    assert _par_id("mot_obligatoire").tirer(Hasard(1), "") is None


def test_tirer_est_reproductible():
    for contrainte in CONTRAINTES:
        assert contrainte.tirer(Hasard(9), QUESTION) == contrainte.tirer(Hasard(9), QUESTION)


def _reponses_du_corpus(nombre: int) -> list[str]:
    paragraphes = [p.strip() for p in CORPUS.read_text(encoding="utf-8").split("\n\n") if p.strip()]
    reponses: list[str] = []
    i = 0
    while len(reponses) < nombre:
        debut = i % len(paragraphes)
        reponses.append(paragraphes[debut] if i % 3 else " ".join(paragraphes[debut:][:2]))
        i += 1
    return reponses


def test_transformer_rend_none_ou_une_reponse_acceptee_sur_200_reponses_du_corpus():
    reponses = _reponses_du_corpus(200)
    rendus = {c.id: 0 for c in CONTRAINTES}
    for i, reponse in enumerate(reponses):
        question = reponse.split(".")[0] + " ?"
        for contrainte in CONTRAINTES:
            kwargs = contrainte.tirer(Hasard(i), question)
            if kwargs is None:
                continue
            resultat = contrainte.transformer(reponse, kwargs)
            if resultat is None:
                continue
            rendus[contrainte.id] += 1
            assert contrainte.verifier(resultat, kwargs), (contrainte.id, kwargs, resultat)
    for identifiant in ("mots_max", "phrases_max", "minuscules", "sans_virgule", "fin_imposee", "titre", "puces"):
        assert rendus[identifiant] >= 100, (identifiant, rendus)
    assert rendus["mot_obligatoire"] >= 1


def test_transformer_ne_triche_pas_pour_mot_obligatoire():
    contrainte = _par_id("mot_obligatoire")
    assert contrainte.transformer("La forge chauffe.", {"mot": "forge"}) == "La forge chauffe."
    assert contrainte.transformer("Le fer chauffe.", {"mot": "forge"}) is None


def test_transformer_exemples():
    assert _par_id("minuscules").transformer("Un Texte.", {}) == "un texte."
    assert _par_id("sans_virgule").transformer("Un, deux.", {}) == "Un deux."
    assert _par_id("fin_imposee").transformer("Bonjour.", {"phrase": "Fin."}) == "Bonjour.\nFin."
    assert _par_id("puces").transformer("Un. Deux. Trois.", {"n": 2}) == "- Un.\n- Deux. Trois."
    assert _par_id("puces").transformer("Un.", {"n": 2}) is None
    assert _par_id("phrases_max").transformer("Un. Deux. Trois.", {"n": 2}) == "Un. Deux."
    assert _par_id("mots_max").transformer("un deux trois quatre", {"n": 2}) == "un deux"
    assert _par_id("titre").transformer("Le fer chauffe.", {}).startswith("« ")
