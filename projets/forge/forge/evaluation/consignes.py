"""Les consignes vérifiables, à la IFEval : « réponds en 40 mots au plus », « n'utilise aucune virgule »...

Deux familles de consignes vivent ici :

1. `IDS_IFEVAL_FR` et `VERIFICATEURS` : les 30 identifiants de consigne qu'on trouve dans IFEval-FR
   (`kurakurai/IFEval-FR`, Apache-2.0, 235 invites, réservé à l'évaluation ; relevé le 17/11/2026 sur les
   lignes du jeu). Chaque vérificateur est strict et a le même sens que celui de M-IFEval
   (`lightblue-tech/M-IFEval`, Apache-2.0, `instructions/fr_instructions.py`). Il n'y a pas de version
   « souple » d'IFEval : le chapitre le dit, et le mode strict est le seul qui compte.
2. `CONTRAINTES` : les huit consignes de la forge, que les préférences de 1.8 et les étapes ajoutent aux
   invites, avec de quoi les tirer au hasard (`tirer`), les vérifier (`verifier`) et rendre une réponse qui
   les respecte (`transformer`).

Ni `re.IGNORECASE` à tout faire, ni les classes de caractères de mots, de frontières et de chiffres des
expressions régulières : Python et JavaScript ne s'y accordent pas (Unicode contre ASCII). Les vérificateurs
testent des caractères explicites, que le plan 8 traduit en TypeScript. Les comptes de mots passent par
`forge.evaluation.langue.mots`.

Écarts assumés avec M-IFEval, tous du côté strict ou déterministe :

- les phrases se comptent par une règle maison (`_phrases`) et non par NLTK/Punkt ;
- la langue passe par `langue` (mots outils) et non par `langdetect` : un texte attendu en français n'est
  refusé que s'il est reconnu « autre » (un texte trop court pour être jugé, comme « oui. », passe, comme
  chez M-IFEval quand `langdetect` n'en tire rien), les écritures non latines se jugent à leurs lettres, et
  les autres langues ne sont refusées que si le texte est reconnu français ;
- un post-scriptum doit ouvrir une ligne (M-IFEval l'accepte n'importe où dans une ligne) ;
- `json.loads` de Python accepte NaN et Infinity, pas JSON.parse : ils sont refusés ici.
"""

import json
import re
import unicodedata
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from forge.evaluation.langue import langue, mots
from forge.hasard import Hasard

# --- Petits outils de caractères et de texte ---------------------------------------------------------------


def _est_lettre(c: str) -> bool:
    return unicodedata.category(c)[0] == "L"


def _est_caractere_de_mot(c: str) -> bool:
    """Une lettre, un chiffre décimal ou le tiret bas : ce qui colle à un mot."""
    categorie = unicodedata.category(c)
    return categorie[0] == "L" or categorie == "Nd" or c == "_"


def _est_chiffre_arabe(c: str) -> bool:
    return "0" <= c <= "9"


def _est_majuscule(texte: str) -> bool:
    """Au moins une lettre à casse, et aucune minuscule."""
    return texte == texte.upper() and texte != texte.lower()


def _est_minuscule(texte: str) -> bool:
    """Au moins une lettre à casse, et aucune majuscule."""
    return texte == texte.lower() and texte != texte.upper()


def _suites_de_lettres(texte: str) -> list[tuple[int, int]]:
    """Les positions (début, fin exclue) des suites de lettres du texte : les mots de `mots`, sans la casse."""
    suites: list[tuple[int, int]] = []
    debut = -1
    for i, c in enumerate(texte):
        if _est_lettre(c):
            if debut < 0:
                debut = i
        elif debut >= 0:
            suites.append((debut, i))
            debut = -1
    if debut >= 0:
        suites.append((debut, len(texte)))
    return suites


def _contient_mot_entier(texte: str, mot: str) -> bool:
    """Vrai si `mot` est dans le texte, entier (sans lettre ni chiffre collé), sans tenir compte de la casse."""
    texte = texte.lower()
    mot = mot.lower()
    if not mot:
        return False
    debut = texte.find(mot)
    while debut >= 0:
        fin = debut + len(mot)
        avant_libre = debut == 0 or not _est_caractere_de_mot(texte[debut - 1])
        apres_libre = fin == len(texte) or not _est_caractere_de_mot(texte[fin])
        if avant_libre and apres_libre:
            return True
        debut = texte.find(mot, debut + 1)
    return False


# Les phrases : un jeton (suite de caractères non blancs) clôt la phrase s'il finit, avant d'éventuels
# guillemets ou parenthèses fermants, par . ! ? ou … ; sauf une abréviation courante (« M. », « Dr. »...) et
# un numéro de liste (« 1. ») au début d'une phrase. Une phrase doit contenir une lettre ou un chiffre.
_TERMINAISONS = ".!?…"
_FERMANTS = "\"'»”’)]*_"
_OUVRANTS = "(«\"'“[*_"
_ABBREVIATIONS = frozenset({"m", "mm", "mme", "mmes", "mlle", "mlles", "dr", "pr", "st", "ste", "cf", "vs"})


def _jetons(texte: str) -> list[tuple[int, int]]:
    jetons: list[tuple[int, int]] = []
    debut = -1
    for i, c in enumerate(texte):
        if c.isspace():
            if debut >= 0:
                jetons.append((debut, i))
                debut = -1
        elif debut < 0:
            debut = i
    if debut >= 0:
        jetons.append((debut, len(texte)))
    return jetons


def _phrases_positions(texte: str) -> list[tuple[int, int]]:
    """Les positions (début, fin exclue) des phrases du texte."""
    phrases: list[tuple[int, int]] = []
    debut_phrase = -1
    contenu = False
    for debut, fin in _jetons(texte):
        jeton = texte[debut:fin]
        coeur = jeton.rstrip(_FERMANTS)
        if not contenu and coeur.endswith(".") and coeur[:-1] != "" and all(_est_chiffre_arabe(c) for c in coeur[:-1]):
            continue  # numéro de liste au début d'une phrase : ni contenu ni fin
        if debut_phrase < 0:
            debut_phrase = debut
        if any(unicodedata.category(c)[0] in "LN" for c in jeton):
            contenu = True
        abreviation = coeur.endswith(".") and coeur[:-1].lower().lstrip(_OUVRANTS) in _ABBREVIATIONS
        if contenu and coeur != "" and coeur[-1] in _TERMINAISONS and not abreviation:
            phrases.append((debut_phrase, fin))
            debut_phrase = -1
            contenu = False
    if contenu:
        phrases.append((debut_phrase, len(texte)))
    return phrases


def _phrases(texte: str) -> list[str]:
    return [texte[d:f] for d, f in _phrases_positions(texte)]


def compter_phrases(texte: str) -> int:
    """Le nombre de phrases du texte, par la règle maison de `_phrases_positions`."""
    return len(_phrases_positions(texte))


# --- Arguments et relations ----------------------------------------------------------------------------------

_RELATIONS = ("moins de", "au moins")


def _arg(kwargs: dict, cle: str):
    valeur = kwargs.get(cle)
    if valeur is None:
        raise ValueError(
            f"Il manque l'argument « {cle} » de la consigne (reçu : {sorted(kwargs)}). "
            "Donne-le dans les kwargs de la ligne, comme IFEval-FR le fait."
        )
    return valeur


def _comparer(compte: int, seuil: int, relation: str) -> bool:
    if relation == "moins de":
        return compte < seuil
    if relation == "au moins":
        return compte >= seuil
    raise ValueError(f"La relation « {relation} » n'existe pas. Choisis « moins de » ou « au moins ».")


# --- Les vérificateurs d'IFEval-FR ----------------------------------------------------------------------------


def _capital_word_frequency(reponse: str, kwargs: dict) -> bool:
    seuil = _arg(kwargs, "capital_frequency")
    relation = _arg(kwargs, "capital_relation")
    compte = sum(1 for d, f in _suites_de_lettres(reponse) if _est_majuscule(reponse[d:f]))
    return _comparer(compte, seuil, relation)


def _french_capital(reponse: str, kwargs: dict) -> bool:
    return _est_majuscule(reponse) and langue(reponse.lower()) != "autre"


def _french_lowercase(reponse: str, kwargs: dict) -> bool:
    return _est_minuscule(reponse) and langue(reponse) != "autre"


def _repeat_prompt(reponse: str, kwargs: dict) -> bool:
    demande = _arg(kwargs, "prompt_to_repeat")
    return reponse.strip().lower().startswith(demande.strip().lower())


def _two_responses(reponse: str, kwargs: dict) -> bool:
    morceaux = reponse.split("******")
    valides: list[str] = []
    for i, morceau in enumerate(morceaux):
        if not morceau.strip():
            if i != 0 and i != len(morceaux) - 1:
                return False
        else:
            valides.append(morceau)
    return len(valides) == 2 and valides[0].strip() != valides[1].strip()


_TUTOIEMENT = frozenset({"tu", "te", "toi", "ton", "ta", "tes"})


def _informal_address(reponse: str, kwargs: dict) -> bool:
    for debut, fin in _suites_de_lettres(reponse):
        mot = reponse[debut:fin].lower()
        if mot in _TUTOIEMENT:
            return True
        # « t' » : le t suivi d'une apostrophe et d'un caractère de mot (« t'aime »), pas « a-t-il ».
        if mot == "t" and fin + 1 < len(reponse) and reponse[fin] in "'’" and _est_caractere_de_mot(reponse[fin + 1]):
            return True
    return False


def _no_digits(reponse: str, kwargs: dict) -> bool:
    return not any(_est_chiffre_arabe(c) for c in reponse)


def _number_placeholders(reponse: str, kwargs: dict) -> bool:
    seuil = _arg(kwargs, "num_placeholders")
    compte = 0
    position = 0
    while True:
        ouvrante = reponse.find("[", position)
        if ouvrante < 0:
            break
        fermante = reponse.find("]", ouvrante + 1)
        if fermante < 0:
            break
        if "\n" in reponse[ouvrante + 1 : fermante]:
            position = ouvrante + 1
            continue
        compte += 1
        position = fermante + 1
    return compte >= seuil


def _commence_par_marqueur(ligne: str, marqueur: str) -> bool:
    """La ligne ouvre par le marqueur (casse et espaces entre ses signes ignorés), sans lettre qui le suive."""
    ligne = ligne.lstrip().lower()
    i = 0
    for signe in marqueur.lower():
        if signe == " ":
            continue
        while i < len(ligne) and ligne[i] == " ":
            i += 1
        if i >= len(ligne) or ligne[i] != signe:
            return False
        i += 1
    return i == len(ligne) or not _est_lettre(ligne[i])


def _postscript(reponse: str, kwargs: dict) -> bool:
    marqueur = _arg(kwargs, "postscript_marker").strip()
    if not marqueur:
        raise ValueError("Le marqueur du post-scriptum est vide. Donne-le dans « postscript_marker ».")
    return any(_commence_par_marqueur(ligne, marqueur) for ligne in reponse.split("\n"))


_REPONSES_CONTRAINTES = ("Oui.", "Non.", "Peut-être.")


def _constrained_response(reponse: str, kwargs: dict) -> bool:
    texte = reponse.strip()
    return any(option in texte for option in _REPONSES_CONTRAINTES)


_PREFIXES_JSON = ("```json", "```Json", "```JSON", "```")


def _refuser_constante(nom: str):
    raise ValueError(f"constante JSON refusée : {nom}")


def _json_format(reponse: str, kwargs: dict) -> bool:
    texte = reponse.strip()
    for prefixe in _PREFIXES_JSON:
        texte = texte.removeprefix(prefixe)
    texte = texte.removesuffix("```").strip()
    try:
        json.loads(texte, parse_constant=_refuser_constante)
    except (ValueError, RecursionError):
        return False
    return True


_ESPACES = " \t\n\r"


def _multiple_sections(reponse: str, kwargs: dict) -> bool:
    separateur = _arg(kwargs, "section_spliter").strip()
    seuil = _arg(kwargs, "num_sections")
    motif = f"[{_ESPACES}]?{re.escape(separateur)}[{_ESPACES}]?[0-9]+[{_ESPACES}]?"
    return len(re.findall(motif, reponse)) >= seuil


def _number_bullet_lists(reponse: str, kwargs: dict) -> bool:
    attendu = _arg(kwargs, "num_bullets")
    compte = 0
    for ligne in reponse.split("\n"):
        ligne = ligne.lstrip()
        if (ligne.startswith("*") and len(ligne) > 1 and ligne[1] != "*") or ligne.startswith("-"):
            compte += 1
    return compte == attendu


def _number_highlighted_sections(reponse: str, kwargs: dict) -> bool:
    seuil = _arg(kwargs, "num_highlights")
    compte = 0
    for surbrillance in re.findall(r"\*[^\n\*]*\*", reponse):
        if surbrillance.strip("*").strip():
            compte += 1
    for surbrillance in re.findall(r"\*\*[^\n\*]*\*\*", reponse):
        if surbrillance.removeprefix("**").removesuffix("**").strip():
            compte += 1
    return compte >= seuil


def _title(reponse: str, kwargs: dict) -> bool:
    return any(titre.strip("#").strip() for titre in re.findall(r"##[^\n]+##", reponse))


def _existence(reponse: str, kwargs: dict) -> bool:
    bas = reponse.lower()
    return all(mot.lower() in bas for mot in _arg(kwargs, "keywords"))


def _forbidden_words(reponse: str, kwargs: dict) -> bool:
    return not any(_contient_mot_entier(reponse, mot) for mot in _arg(kwargs, "forbidden_words"))


def _frequency(reponse: str, kwargs: dict) -> bool:
    mot = _arg(kwargs, "keyword").strip().lower()
    if not mot:
        raise ValueError("Le mot « keyword » est vide. Donne le mot à compter dans les kwargs.")
    return _comparer(reponse.lower().count(mot), _arg(kwargs, "frequency"), _arg(kwargs, "relation"))


def _letter_frequency(reponse: str, kwargs: dict) -> bool:
    lettre = _arg(kwargs, "letter").strip().lower()
    if len(lettre) != 1:
        raise ValueError(f"« letter » doit être une seule lettre (reçu {lettre!r}).")
    return _comparer(reponse.lower().count(lettre), _arg(kwargs, "let_frequency"), _arg(kwargs, "let_relation"))


# Les langues d'IFEval-FR écrites hors de l'alphabet latin : on les juge à leurs lettres (au moins 90 %
# de lettres au-delà de U+024F, la fin des lettres latines étendues).
_ECRITURES_NON_LATINES = frozenset(
    "ar bg bn fa gu he hi ja kn ko ml mr ne pa ru ta te th uk ur zh".split()
)


def _response_language(reponse: str, kwargs: dict) -> bool:
    cible = _arg(kwargs, "language")
    lettres = [c for c in reponse if _est_lettre(c)]
    if not lettres:
        return False
    if cible == "fr":
        return langue(reponse) != "autre"
    if cible in _ECRITURES_NON_LATINES:
        hors_latin = sum(1 for c in lettres if ord(c) > 0x24F)
        return 10 * hors_latin >= 9 * len(lettres)
    return langue(reponse) != "fr"


def _nth_paragraph_first_word(reponse: str, kwargs: dict) -> bool:
    attendu_total = _arg(kwargs, "num_paragraphs")
    rang = _arg(kwargs, "nth_paragraph")
    premier_mot = _arg(kwargs, "first_word").lower()
    paragraphes = reponse.split("\n\n")
    total = sum(1 for p in paragraphes if p.strip())
    if rang > total or rang < 1:
        return False
    paragraphe = paragraphes[rang - 1].strip()
    if not paragraphe:
        return False
    mot = paragraphe.split()[0].strip().lstrip("'").lstrip('"')
    obtenu = ""
    for lettre in mot:
        if lettre in ".,?!'\"":
            break
        obtenu += lettre.lower()
    return total == attendu_total and obtenu == premier_mot


def _number_paragraphs(reponse: str, kwargs: dict) -> bool:
    attendu = _arg(kwargs, "num_paragraphs")
    paragraphes = reponse.split("***")
    total = len(paragraphes)
    for i, paragraphe in enumerate(paragraphes):
        if not paragraphe.strip():
            if i == 0 or i == len(paragraphes) - 1:
                total -= 1
            else:
                return False
    return total == attendu


def _number_sentences(reponse: str, kwargs: dict) -> bool:
    return _comparer(compter_phrases(reponse), _arg(kwargs, "num_sentences"), _arg(kwargs, "relation"))


def _number_words(reponse: str, kwargs: dict) -> bool:
    return _comparer(len(mots(reponse)), _arg(kwargs, "num_words"), _arg(kwargs, "relation"))


def _no_comma(reponse: str, kwargs: dict) -> bool:
    return "," not in reponse


def _sans_accents(texte: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texte) if not unicodedata.category(c).startswith("M"))


def _accents(reponse: str, kwargs: dict) -> bool:
    cibles = _arg(kwargs, "word_to_accentuate")
    for mot in mots(unicodedata.normalize("NFC", reponse)):
        correct = cibles.get(_sans_accents(mot))
        if correct is not None and mot != unicodedata.normalize("NFC", correct).lower():
            return False
    return True


def _ethel_or_cedilla(reponse: str, kwargs: dict) -> bool:
    return _arg(kwargs, "forbidden_char").lower() not in reponse.lower()


_LETTRES_ACCENTUEES = frozenset("àáâãäåçèéêëìíîïñòóôõöùúûüýÿÀÁÂÃÄÅÇÈÉÊËÌÍÎÏÑÒÓÔÕÖÙÚÛÜÝ")


def _no_accents(reponse: str, kwargs: dict) -> bool:
    return not any(c in _LETTRES_ACCENTUEES for c in reponse)


def _end_checker(reponse: str, kwargs: dict) -> bool:
    fin = _arg(kwargs, "end_phrase").strip().lower()
    return reponse.strip().strip('"').lower().endswith(fin)


def _quotation(reponse: str, kwargs: dict) -> bool:
    texte = reponse.strip()
    return len(texte) > 1 and (
        (texte.startswith('"') and texte.endswith('"'))
        or (texte.startswith("'") and texte.endswith("'"))
        or (texte.startswith("«") and texte.endswith("»"))
    )


VERIFICATEURS: dict[str, Callable[[str, dict], bool]] = {
    "fr:change_case:capital_word_frequency": _capital_word_frequency,
    "fr:change_case:french_capital": _french_capital,
    "fr:change_case:french_lowercase": _french_lowercase,
    "fr:combination:repeat_prompt": _repeat_prompt,
    "fr:combination:two_responses": _two_responses,
    "fr:detectable_content:informal_address": _informal_address,
    "fr:detectable_content:no_digits": _no_digits,
    "fr:detectable_content:number_placeholders": _number_placeholders,
    "fr:detectable_content:postscript": _postscript,
    "fr:detectable_format:constrained_response": _constrained_response,
    "fr:detectable_format:json_format": _json_format,
    "fr:detectable_format:multiple_sections": _multiple_sections,
    "fr:detectable_format:number_bullet_lists": _number_bullet_lists,
    "fr:detectable_format:number_highlighted_sections": _number_highlighted_sections,
    "fr:detectable_format:title": _title,
    "fr:keywords:existence": _existence,
    "fr:keywords:forbidden_words": _forbidden_words,
    "fr:keywords:frequency": _frequency,
    "fr:keywords:letter_frequency": _letter_frequency,
    "fr:language:response_language": _response_language,
    "fr:length_constraints:nth_paragraph_first_word": _nth_paragraph_first_word,
    "fr:length_constraints:number_paragraphs": _number_paragraphs,
    "fr:length_constraints:number_sentences": _number_sentences,
    "fr:length_constraints:number_words": _number_words,
    "fr:punctuation:no_comma": _no_comma,
    "fr:special_character:accents": _accents,
    "fr:special_character:ethel_or_cedilla": _ethel_or_cedilla,
    "fr:special_character:no_accents": _no_accents,
    "fr:startend:end_checker": _end_checker,
    "fr:startend:quotation": _quotation,
}

# Les identifiants présents dans les 235 lignes d'IFEval-FR, relevés le 17/11/2026 (lecture du jeu par le
# serveur de visionnage de Hugging Face). Triés. Tous ont un vérificateur ci-dessus.
IDS_IFEVAL_FR: tuple[str, ...] = tuple(sorted(VERIFICATEURS))


def respecte(reponse: str, ids: Sequence[str], kwargs: Sequence[dict | None]) -> list[bool]:
    """Pour chaque consigne (identifiant et arguments d'une ligne d'IFEval-FR), la réponse la respecte-t-elle ?"""
    if len(ids) != len(kwargs):
        raise ValueError(
            f"Il y a {len(ids)} identifiants de consigne mais {len(kwargs)} listes de kwargs. "
            "Donne une liste de kwargs par identifiant, dans le même ordre."
        )
    resultats: list[bool] = []
    for identifiant, arguments in zip(ids, kwargs):
        verificateur = VERIFICATEURS.get(identifiant)
        if verificateur is None:
            raise ValueError(
                f"La consigne « {identifiant} » n'a pas de vérificateur. "
                "Ajoute-la à VERIFICATEURS ou retire-la de la ligne."
            )
        resultats.append(bool(verificateur(reponse, arguments or {})))
    return resultats


def exactitudes(resultats: Sequence[list[bool]]) -> dict:
    """L'exactitude stricte d'IFEval : par invite (toutes ses consignes) et par consigne, avec le nombre d'invites."""
    n = len(resultats)
    consignes = sum(len(r) for r in resultats)
    invite_stricte = sum(1 for r in resultats if all(r)) / n if n else 0.0
    consigne_stricte = sum(sum(r) for r in resultats) / consignes if consignes else 0.0
    return {"invite_stricte": invite_stricte, "consigne_stricte": consigne_stricte, "n": n}


# --- Les huit consignes de la forge ----------------------------------------------------------------------------


@dataclass(frozen=True)
class Contrainte:
    """Une consigne ajoutée à une invite : son texte, son tirage, sa vérification et sa réalisation.

    - `consigne(kwargs)` : la phrase qu'on ajoute à l'invite ;
    - `tirer(hasard, question)` : les kwargs tirés au hasard (le texte de la question peut servir), ou
      `None` si la contrainte n'a pas de sens pour cette question ;
    - `verifier(reponse, kwargs)` : la réponse la respecte-t-elle ? (strict ; une réponse vide ne respecte rien) ;
    - `transformer(reponse, kwargs)` : une réponse qui la respecte, faite à partir de celle-ci, ou `None`.
    """

    id: str
    consigne: Callable[[dict], str]
    tirer: Callable[[Hasard, str], dict | None]
    verifier: Callable[[str, dict], bool]
    transformer: Callable[[str, dict], str | None]


PHRASES_FIN = (
    "Voilà ce que je peux dire pour le moment.",
    "J'espère que cela t'aide.",
    "C'est tout pour aujourd'hui.",
    "Merci d'avoir posé la question.",
    "À toi de jouer maintenant.",
)


def _valide_ou_none(contrainte_verifier: Callable[[str, dict], bool], texte: str, kwargs: dict) -> str | None:
    return texte if contrainte_verifier(texte, kwargs) else None


# mots_max : « Réponds en {n} mots au plus. »
def _verifier_mots_max(reponse: str, kwargs: dict) -> bool:
    return 1 <= len(mots(reponse)) <= kwargs["n"]


def _transformer_mots_max(reponse: str, kwargs: dict) -> str | None:
    suites = _suites_de_lettres(reponse)
    if len(suites) > kwargs["n"] >= 1:
        reponse = reponse[: suites[kwargs["n"] - 1][1]]
    return _valide_ou_none(_verifier_mots_max, reponse.strip(), kwargs)


# phrases_max : « Réponds en {n} phrases au plus. »
def _verifier_phrases_max(reponse: str, kwargs: dict) -> bool:
    return 1 <= compter_phrases(reponse) <= kwargs["n"]


def _transformer_phrases_max(reponse: str, kwargs: dict) -> str | None:
    positions = _phrases_positions(reponse)
    if len(positions) > kwargs["n"] >= 1:
        reponse = reponse[: positions[kwargs["n"] - 1][1]]
    return _valide_ou_none(_verifier_phrases_max, reponse.strip(), kwargs)


# minuscules : « Écris toute ta réponse en minuscules. »
def _verifier_minuscules(reponse: str, kwargs: dict) -> bool:
    return _est_minuscule(reponse)


def _transformer_minuscules(reponse: str, kwargs: dict) -> str | None:
    return _valide_ou_none(_verifier_minuscules, reponse.lower(), kwargs)


# sans_virgule : « N'utilise aucune virgule. »
def _verifier_sans_virgule(reponse: str, kwargs: dict) -> bool:
    return reponse.strip() != "" and "," not in reponse


def _transformer_sans_virgule(reponse: str, kwargs: dict) -> str | None:
    return _valide_ou_none(_verifier_sans_virgule, reponse.replace(",", ""), kwargs)


# mot_obligatoire : « Emploie le mot « {mot} » dans ta réponse. »
def _tirer_mot_obligatoire(hasard: Hasard, question: str) -> dict | None:
    candidats: list[str] = []
    for mot in mots(question):
        if len(mot) >= 5 and mot not in candidats:
            candidats.append(mot)
    if not candidats:
        return None
    return {"mot": hasard.choisir(candidats)}


def _verifier_mot_obligatoire(reponse: str, kwargs: dict) -> bool:
    return _contient_mot_entier(reponse, kwargs["mot"])


def _transformer_mot_obligatoire(reponse: str, kwargs: dict) -> str | None:
    # On n'ajoute pas un mot au hasard dans une réponse : elle l'emploie déjà, ou la contrainte ne s'applique pas.
    return _valide_ou_none(_verifier_mot_obligatoire, reponse, kwargs)


# puces : « Réponds par exactement {n} puces, chacune commençant par « - ». »
def _lignes_non_vides(reponse: str) -> list[str]:
    return [ligne.strip() for ligne in reponse.split("\n") if ligne.strip()]


def _verifier_puces(reponse: str, kwargs: dict) -> bool:
    lignes = _lignes_non_vides(reponse)
    return len(lignes) == kwargs["n"] and all(
        ligne.startswith("- ") and ligne[2:].strip() != "" for ligne in lignes
    )


def _transformer_puces(reponse: str, kwargs: dict) -> str | None:
    n = kwargs["n"]
    phrases = [" ".join(phrase.split()) for phrase in _phrases(reponse)]
    if n < 1 or len(phrases) < n:
        return None
    puces = phrases[: n - 1] + [" ".join(phrases[n - 1 :])]
    return _valide_ou_none(_verifier_puces, "\n".join(f"- {puce}" for puce in puces), kwargs)


# fin_imposee : « Termine ta réponse par la phrase exacte : « {phrase} » »
def _verifier_fin_imposee(reponse: str, kwargs: dict) -> bool:
    return kwargs["phrase"] != "" and reponse.rstrip().endswith(kwargs["phrase"])


def _transformer_fin_imposee(reponse: str, kwargs: dict) -> str | None:
    if reponse.strip() == "":
        return None
    if _verifier_fin_imposee(reponse, kwargs):
        return reponse
    return _valide_ou_none(_verifier_fin_imposee, reponse.rstrip() + "\n" + kwargs["phrase"], kwargs)


# titre : « Donne d'abord un titre entre doubles chevrons, comme « titre ». »
_CHEVRONS = (("«", "»"), ("<<", ">>"))


def _verifier_titre(reponse: str, kwargs: dict) -> bool:
    lignes = _lignes_non_vides(reponse)
    if not lignes:
        return False
    premiere = lignes[0]
    for ouvrant, fermant in _CHEVRONS:
        if premiere.startswith(ouvrant):
            fin = premiere.find(fermant, len(ouvrant))
            if fin >= 0 and premiere[len(ouvrant) : fin].strip() != "":
                return True
    return False


def _transformer_titre(reponse: str, kwargs: dict) -> str | None:
    if _verifier_titre(reponse, kwargs):
        return reponse
    titre = " ".join(reponse.split()[:6]).strip(".,;:!?«»<> \t")
    if titre == "":
        return None
    return _valide_ou_none(_verifier_titre, f"« {titre} »\n{reponse.lstrip()}", kwargs)


def _constante(valeur: dict) -> Callable[[Hasard, str], dict | None]:
    return lambda hasard, question: dict(valeur)


CONTRAINTES: tuple[Contrainte, ...] = (
    Contrainte(
        id="mots_max",
        consigne=lambda kwargs: f"Réponds en {kwargs['n']} mots au plus.",
        tirer=lambda hasard, question: {"n": hasard.choisir((20, 40, 60))},
        verifier=_verifier_mots_max,
        transformer=_transformer_mots_max,
    ),
    Contrainte(
        id="phrases_max",
        consigne=lambda kwargs: f"Réponds en {kwargs['n']} phrases au plus.",
        tirer=lambda hasard, question: {"n": hasard.entier(1, 3)},
        verifier=_verifier_phrases_max,
        transformer=_transformer_phrases_max,
    ),
    Contrainte(
        id="minuscules",
        consigne=lambda kwargs: "Écris toute ta réponse en minuscules.",
        tirer=_constante({}),
        verifier=_verifier_minuscules,
        transformer=_transformer_minuscules,
    ),
    Contrainte(
        id="sans_virgule",
        consigne=lambda kwargs: "N'utilise aucune virgule.",
        tirer=_constante({}),
        verifier=_verifier_sans_virgule,
        transformer=_transformer_sans_virgule,
    ),
    Contrainte(
        id="mot_obligatoire",
        consigne=lambda kwargs: f"Emploie le mot « {kwargs['mot']} » dans ta réponse.",
        tirer=_tirer_mot_obligatoire,
        verifier=_verifier_mot_obligatoire,
        transformer=_transformer_mot_obligatoire,
    ),
    Contrainte(
        id="puces",
        consigne=lambda kwargs: f"Réponds par exactement {kwargs['n']} puces, chacune commençant par « - ».",
        tirer=lambda hasard, question: {"n": hasard.entier(2, 4)},
        verifier=_verifier_puces,
        transformer=_transformer_puces,
    ),
    Contrainte(
        id="fin_imposee",
        consigne=lambda kwargs: f"Termine ta réponse par la phrase exacte : « {kwargs['phrase']} »",
        tirer=lambda hasard, question: {"phrase": hasard.choisir(PHRASES_FIN)},
        verifier=_verifier_fin_imposee,
        transformer=_transformer_fin_imposee,
    ),
    Contrainte(
        id="titre",
        consigne=lambda kwargs: "Donne d'abord un titre entre doubles chevrons, comme « titre ».",
        tirer=_constante({}),
        verifier=_verifier_titre,
        transformer=_transformer_titre,
    ),
)
