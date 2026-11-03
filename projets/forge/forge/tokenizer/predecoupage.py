"""Pré-découpage : couper un texte en pré-mots avant d'appliquer le BPE.

Le BPE ne fusionne jamais deux octets qui appartiennent à deux pré-mots
différents. Le motif ci-dessous décide donc des frontières que les jetons ne
franchiront jamais : entre un mot et le suivant, entre des chiffres et des
lettres, entre une ponctuation et un mot…

Le motif est figé avec le tokenizer. Il reste compatible avec JavaScript (pas
de quantificateur possessif ni de groupe atomique), pour qu'un jumeau en
TypeScript puisse découper exactement de la même façon.
"""

import regex

# Les six possibilités, essayées dans l'ordre, de gauche à droite :
#
# 1. `[^\r\n\p{L}\p{N}]?\p{L}+(?:['’](?=\p{L}))?`
#    un mot en lettres, précédé d'au plus un caractère qui n'est ni lettre, ni
#    chiffre, ni retour à la ligne (le plus souvent une espace : « ␣forge ») ;
#    une apostrophe droite ou typographique suivie d'une lettre reste collée
#    au mot qu'elle termine : « l'atelier » donne « l' » puis « atelier ».
# 2. `\p{N}{1,3}`
#    des chiffres, par groupes de trois au plus : « 2026 » donne « 202 », « 6 ».
# 3. ` ?[^\p{White_Space}\p{L}\p{N}]+[\r\n]*`
#    de la ponctuation ou des symboles (émojis compris), avec au plus une
#    espace devant et les retours à la ligne qui suivent : « ):\n ».
# 4. `\p{White_Space}*[\r\n]+`
#    des blancs qui se terminent par des retours à la ligne : « \r\n\r\n ».
# 5. `\p{White_Space}+(?!\P{White_Space})`
#    des blancs, sauf le dernier s'il précède un mot : dans « ␣␣␣␣return »,
#    trois espaces seules, puis « ␣return ».
# 6. `\p{White_Space}+`
#    les blancs qui restent (en fin de texte, ou devant un chiffre).
#
# `\p{White_Space}` (et non `\s`) donne la liste des blancs d'Unicode, la même
# en Python et en JavaScript ; elle contient les espaces insécables du français.
# Tout caractère est couvert par l'une des possibilités : en recollant les
# pré-mots, on retrouve exactement le texte de départ.
MOTIF_TON_IA = (
    r"[^\r\n\p{L}\p{N}]?\p{L}+(?:['’](?=\p{L}))?|\p{N}{1,3}| ?[^\p{White_Space}\p{L}\p{N}]+[\r\n]*"
    r"|\p{White_Space}*[\r\n]+|\p{White_Space}+(?!\P{White_Space})|\p{White_Space}+"
)

# Le module `regex` (et non `re`) comprend les classes Unicode comme \p{L}.
MOTIF_COMPILE = regex.compile(MOTIF_TON_IA)


def pre_decouper(texte: str) -> list[str]:
    """Découpe un texte en pré-mots : « L'atelier, c'est » donne ["L'", "atelier", ",", " c'", "est"]."""
    return MOTIF_COMPILE.findall(texte)
