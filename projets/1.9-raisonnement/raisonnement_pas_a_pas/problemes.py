"""Un problème de calcul, sa trace et sa vérification, tels que ton IA les voit.

Le chapitre 1.9 apprend à ton IA à raisonner sur des problèmes de calcul en français, générés par programme :
chaque problème sort d'une graine, avec sa réponse et sa trace (une étape de calcul par ligne), et sa réponse est
juste par construction. Ce module ne refait pas le générateur de forge (`forge.raisonnement.problemes`) : il le
montre. `montrer_probleme` rend un problème avec sa trace et la conversation que ton IA lit au SFT de raisonnement,
encodée par le tokenizer figé ; `verifier_reponse` dit si une réponse écrite est juste, avec la règle de
`forge.raisonnement.verification` (le dernier nombre du texte, une réponse coupée n'est jamais juste).

Le site refait le générateur et la lecture d'un nombre en TypeScript (`site/src/lib/partie-1/problemes.ts`) : mêmes
listes de prénoms et d'objets, mêmes tirages dans le même ordre, et les attendus de ce projet (`attendus.py`)
vérifient qu'ils donnent les mêmes problèmes.
"""

from pathlib import Path

import forge
from forge.conversation.format import Reponse, encoder_conversation
from forge.raisonnement.problemes import conversation_de_probleme, generer_probleme
from forge.raisonnement.verification import est_juste, extraire_nombre
from forge.tokenizer import TokenizerOctets

# Le tokenizer figé de « ton IA », celui de forge.
TOKENIZER = Path(forge.__file__).resolve().parent / "ressources" / "tokenizer-ton-ia-v1.json"


# region: probleme
def montrer_probleme(famille: str, difficulte: int, graine: int) -> dict:
    """Le problème de cette famille et de cette difficulté tiré de cette graine, avec sa trace et sa conversation.

    Rend `id`, `famille`, `difficulte`, `graine`, `enonce`, `etapes` (une étape de calcul par ligne, « a op b = c »),
    `reponse` (un entier) et `conversation` : ce que ton IA lit au SFT de raisonnement. L'utilisateur dit l'énoncé, ton
    IA pense les étapes puis répond « La réponse est N. » ; `ids` sont ses jetons, `appris` dit lesquels sont des cibles
    (seulement ceux de la pensée et de la réponse de ton IA, jamais l'énoncé), `pieces` donne le texte de chaque jeton
    (le nom des jetons spéciaux entre « < » et « > » : « <|pensee|> »).
    """
    tok = TokenizerOctets.charger(TOKENIZER)
    probleme = generer_probleme(famille, difficulte, graine)
    exemple = encoder_conversation(tok, conversation_de_probleme(probleme))
    noms_speciaux = {tok.id_special(nom): nom for nom in ("<|fin_texte|>", "<|utilisateur|>", "<|assistant|>", "<|pensee|>", "<|fin_pensee|>", "<|fin_tour|>")}
    pieces = [noms_speciaux.get(i) or tok.decoder([i]) for i in exemple.ids]
    return {
        "id": probleme.id,
        "famille": probleme.famille,
        "difficulte": probleme.difficulte,
        "graine": graine,
        "enonce": probleme.enonce,
        "etapes": list(probleme.etapes),
        "reponse": probleme.reponse,
        "conversation": {"ids": exemple.ids, "appris": exemple.appris, "pieces": pieces},
    }
# fin: probleme


# region: verifier
def verifier_reponse(texte: str, terminee: bool, attendu: int) -> dict:
    """Une réponse écrite est-elle juste ? Le nombre lu et le verdict, avec la règle de forge.

    `lu` est le dernier nombre du texte (`extraire_nombre`, en `Fraction` exacte, rendu comme « num/den » quand ce
    n'est pas un entier), ou `None` s'il n'y en a pas. Une réponse coupée (`terminee` faux) n'est jamais juste, même
    si le nombre lu est le bon : rien ne dit qu'il est complet.
    """
    lu = extraire_nombre(texte)
    ecrit = None if lu is None else (str(lu.numerator) if lu.denominator == 1 else f"{lu.numerator}/{lu.denominator}")
    return {"lu": ecrit, "terminee": terminee, "juste": est_juste(Reponse(texte=texte, pensee=None, ids=[], terminee=terminee), attendu)}
# fin: verifier
