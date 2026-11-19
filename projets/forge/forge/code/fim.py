"""Remplir un trou dans du code (FIM, « fill in the middle »), dans l'ordre PSM : préfixe, suffixe, milieu.

Un éditeur de code ne complète pas seulement la fin d'un fichier : il écrit souvent au milieu, avec du code
avant et du code après le curseur. Pour l'apprendre à ton IA, on prend un bout de code, on en coupe un morceau
(le milieu), et on lui montre le code d'avant (le préfixe) et le code d'après (le suffixe) avant le milieu :

    <|fin_texte|> <|trou_prefixe|> préfixe <|trou_suffixe|> suffixe <|trou_milieu|> milieu <|fin_tour|>

La perte ne porte que sur le milieu et sur `<|fin_tour|>` (le modèle apprend à boucher le trou, puis à
s'arrêter), pas sur le préfixe ni sur le suffixe : ce sont les données de la question, comme la question
de l'utilisateur dans une conversation. L'ordre PSM met le milieu en dernier : à l'usage, on écrit l'invite
(`invite_fim`) jusqu'à `<|trou_milieu|>` et le modèle écrit la suite, comme une réponse.

Les trois jetons `<|trou_prefixe|>`, `<|trou_suffixe|>` et `<|trou_milieu|>` sont dans le tokenizer figé. Un
code qui contient ces mots est encodé comme du texte ordinaire (`TokenizerOctets.encoder` n'émet jamais de
jeton spécial) : personne ne peut fausser la disposition en les écrivant dans un fichier.

Les coupures sont tirées au hasard, comme dans l'article d'origine (Bavarian et al., 2022, « Efficient
Training of Language Models to Fill in the Middle ») : deux positions uniformes, en points de code, donc
jamais au milieu d'un emoji ni d'une lettre accentuée. Les documents viennent du code Python sous licence
permissive du pré-entraînement (`textes/principal/code_python`) ; ceux que le pré-entraînement a mis de côté
pour sa validation (`est_validation`) ne servent qu'à l'évaluation.
"""

from __future__ import annotations

import functools
from collections.abc import Iterator
from pathlib import Path

from forge.conversation.format import JETON_DE_DEBUT, ExempleMasque
from forge.donnees.melange import est_validation
from forge.donnees.nettoyage import empreinte_du_texte_nettoye
from forge.hasard import Hasard
from forge.tokenizer import TokenizerOctets
from forge.tokenizer.apprentissage import lire_fragments

TOKENIZER = Path(__file__).parent.parent / "ressources" / "tokenizer-ton-ia-v1.json"

SORTE = "fim"
JETONS_MAX_DU_DOCUMENT = 1500  # un exemple (document + 5 jetons spéciaux) tient dans les 1 536 jetons d'une recette
# Un jeton de code couvre rarement plus de 6 caractères en moyenne : un document de plus de 9 000 caractères
# dépasse presque sûrement 1 500 jetons, et on ne l'encode pas pour le savoir (un tri de plus, déterministe).
CARACTERES_MAX_DU_DOCUMENT = 6 * JETONS_MAX_DU_DOCUMENT


@functools.cache
def _tokenizer() -> TokenizerOctets:
    """Le tokenizer figé, chargé une seule fois par processus."""
    return TokenizerOctets.charger(TOKENIZER)


def _debut_de_l_invite(prefixe: str, suffixe: str, tok: TokenizerOctets) -> list[int]:
    return [
        tok.id_special(JETON_DE_DEBUT),
        tok.id_special("<|trou_prefixe|>"),
        *tok.encoder(prefixe),
        tok.id_special("<|trou_suffixe|>"),
        *tok.encoder(suffixe),
        tok.id_special("<|trou_milieu|>"),
    ]


def invite_fim(prefixe: str, suffixe: str, tok: TokenizerOctets) -> list[int]:
    """Les jetons à donner au modèle pour qu'il écrive le milieu : tout, jusqu'à `<|trou_milieu|>` compris."""
    return _debut_de_l_invite(prefixe, suffixe, tok)


def exemple_fim(prefixe: str, milieu: str, suffixe: str, tok: TokenizerOctets) -> ExempleMasque:
    """L'exemple d'apprentissage : l'invite, puis le milieu et `<|fin_tour|>`, seuls appris. `milieu` est non vide."""
    if not milieu:
        raise ValueError(
            "Le milieu d'un exemple de remplissage est vide : il n'y aurait rien à apprendre. "
            "Donne au moins un caractère à boucher."
        )
    invite = _debut_de_l_invite(prefixe, suffixe, tok)
    cible = [*tok.encoder(milieu), tok.id_special("<|fin_tour|>")]
    return ExempleMasque(ids=invite + cible, appris=[False] * len(invite) + [True] * len(cible))


def couper_au_hasard(code: str, hasard: Hasard) -> tuple[int, int]:
    """Deux positions du code, en points de code : `0 ≤ debut < fin ≤ len(code)`, le milieu est `code[debut:fin]`.

    Comme dans l'article d'origine : deux positions tirées uniformément de 0 à `len(code)`, retirées si elles
    sont égales (le milieu serait vide), puis rangées dans l'ordre. Chaque milieu possible est donc aussi
    probable qu'un autre.
    """
    longueur = len(code)
    if longueur < 1:
        raise ValueError("Impossible de couper un code vide : il faut au moins un caractère. Donne un code non vide.")
    while True:
        a, b = hasard.entier(0, longueur), hasard.entier(0, longueur)
        if a != b:
            return min(a, b), max(a, b)


def cas_d_une_ligne(code: str, hasard: Hasard) -> tuple[str, str, str] | None:
    """`(préfixe, milieu, suffixe)` où le milieu est une ligne non vide du tiers du milieu du code, saut de ligne compris.

    C'est le cas de l'évaluation : une ligne entière à retrouver, avec ce qui la précède et ce qui la suit.
    `préfixe + milieu + suffixe` redonne le code. Rend `None` si le tiers du milieu n'a aucune ligne non vide.
    """
    lignes = code.splitlines(keepends=True)
    tiers = len(lignes) // 3
    candidates = [i for i in range(tiers, len(lignes) - tiers) if lignes[i].strip()]
    if not candidates:
        return None
    i = hasard.choisir(candidates)
    return "".join(lignes[:i]), lignes[i], "".join(lignes[i + 1 :])


def elements_fim(
    textes_code: Path,
    n: int,
    graine: int,
    validation: bool,
    *,
    lignes: bool = False,
    tok: TokenizerOctets | None = None,
) -> Iterator[dict]:
    """Au plus `n` éléments `{"sorte": "fim", "prefixe", "milieu", "suffixe"}`, un par document de `textes_code`.

    Les documents sont ceux des fragments du dossier, dans l'ordre des noms : on garde ceux dont
    `est_validation(empreinte)` vaut `validation` (la validation du pré-entraînement n'entre jamais dans
    l'entraînement, et seule elle sert à l'évaluation) et qui tiennent en 1 500 jetons au plus. La coupure de
    chacun vient de `Hasard(graine)` : mêmes arguments, mêmes éléments. Avec `lignes`, le milieu est une ligne
    entière (`cas_d_une_ligne`) et les documents sans ligne utilisable sont sautés.
    """
    if n < 1:
        raise ValueError(f"Le nombre d'éléments doit valoir au moins 1, pas {n}.")
    tok = tok if tok is not None else _tokenizer()
    hasard = Hasard(graine)
    rendus = 0
    for texte in lire_fragments(Path(textes_code)):
        if not texte.strip() or len(texte) > CARACTERES_MAX_DU_DOCUMENT:
            continue
        # Les textes du pré-entraînement sont déjà nettoyés : leur empreinte est celle du texte tel quel.
        if est_validation(empreinte_du_texte_nettoye(texte)) != validation:
            continue
        if len(tok.encoder(texte)) > JETONS_MAX_DU_DOCUMENT:
            continue
        if lignes:
            cas = cas_d_une_ligne(texte, hasard)
            if cas is None:
                continue
            prefixe, milieu, suffixe = cas
        else:
            debut, fin = couper_au_hasard(texte, hasard)
            prefixe, milieu, suffixe = texte[:debut], texte[debut:fin], texte[fin:]
        yield {"sorte": SORTE, "prefixe": prefixe, "milieu": milieu, "suffixe": suffixe}
        rendus += 1
        if rendus >= n:
            return
