"""Les échantillons : ce que le modèle écrit quand on lui donne le début d'un texte.

Les chiffres (perte, QCM) disent si le modèle prédit bien ; les échantillons montrent comment
il écrit. Ce sont toujours les mêmes dix débuts, avec la même graine : d'une sauvegarde à
l'autre, on lit le même texte amorcé de la même façon, et l'on voit ce qui change.
"""

from forge.modele import generer

# Huit débuts de phrase en français, puis deux débuts de fonction Python (le modèle a lu les deux).
# Aucun ne finit par une espace : le tokenizer la lirait comme un jeton à part, ce qu'il n'a jamais
# vu devant un mot dans le corpus d'entraînement.
INVITES = [
    "Il était une fois",
    "La capitale de la France est",
    "Pour faire un bon gâteau au chocolat, il faut",
    "Le soleil se couchait sur la mer et",
    "Aujourd'hui, le gouvernement a annoncé",
    "Dans un petit village de Bretagne,",
    "La photosynthèse est le processus par lequel",
    "Bonjour, je voudrais savoir comment",
    "def factorielle(n):\n",
    'def moyenne(valeurs):\n    """Renvoie la moyenne',
]

# Les réglages du tirage : un peu de hasard (0,8), parmi les 50 jetons les plus probables.
TEMPERATURE = 0.8
TOP_K = 50

# Le texte d'un document est suivi de `<|fin_texte|>` dans les données d'entraînement : c'est
# aussi, pour le modèle, la marque de « un nouveau texte commence » et de « le texte est fini ».
JETON_DE_FIN = "<|fin_texte|>"


def _decoder(tokenizer, ids: list[int]) -> str:
    """Décode les jetons écrits par le modèle ; un identifiant qui ne désigne aucun jeton devient « � ».

    Un tokenizer dont l'apprentissage s'est arrêté avant le dernier identifiant ordinaire laisse
    des identifiants libres (voir `TokenizerOctets`) : un modèle peut en tirer un, surtout avant
    d'être entraîné. Le tokenizer complet de ton IA n'en a aucun.
    """
    try:
        return tokenizer.decoder(ids)
    except ValueError:
        octets = b""
        for identifiant in ids:
            try:
                octets += tokenizer.octets_du_jeton(identifiant)
            except ValueError:
                octets += "\ufffd".encode()
        return octets.decode("utf-8", errors="replace")


def echantillons(modele, tokenizer, graine: int = 0, n_nouveaux: int = 60) -> list[dict]:
    """Fait écrire au modèle la suite de chacune des `INVITES` : une `list` de dix `dict`.

    Chaque texte part de `<|fin_texte|>` (le « début de document » du modèle) suivi de l'invite,
    et compte `n_nouveaux` jetons au plus : il s'arrête avant si le modèle écrit
    `<|fin_texte|>`. La graine de l'invite numéro `k` (à partir de 0) est `graine + k` : mêmes
    modèle, `graine` et `n_nouveaux`, mêmes textes (sur un même appareil : la carte graphique
    et le processeur n'arrondissent pas pareil).

    Chaque `dict` contient `invite`, `suite` (ce que le modèle a écrit, sans le début donné ni le
    `<|fin_texte|>` final), `graine`, `n_jetons` (les jetons de `suite`) et `s_arrete` (vrai si le
    modèle a écrit `<|fin_texte|>`).
    """
    fin = tokenizer.id_special(JETON_DE_FIN)
    resultats = []
    for numero, invite in enumerate(INVITES):
        nouveaux = generer(
            modele,
            [fin, *tokenizer.encoder(invite)],
            n_nouveaux,
            temperature=TEMPERATURE,
            top_k=TOP_K,
            graine=graine + numero,
            arret=fin,
        )
        s_arrete = bool(nouveaux) and nouveaux[-1] == fin
        if s_arrete:
            nouveaux = nouveaux[:-1]
        resultats.append(
            {
                "invite": invite,
                "suite": _decoder(tokenizer, nouveaux),
                "graine": graine + numero,
                "n_jetons": len(nouveaux),
                "s_arrete": s_arrete,
            }
        )
    return resultats
