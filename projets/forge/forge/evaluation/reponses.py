"""Les réponses de ton IA à des conversations : par lots pour l'évaluation, une à une pour `forge discuter`.

`repondre_lot` fait écrire à un modèle affiné la suite de chaque conversation : l'invite (les tours, puis
`<|assistant|>`) vient de `forge.conversation.format`, la génération de `forge.modele.generer_lot`
(plusieurs textes avancent ensemble, avec le cache des clés et des valeurs), et la lecture de la réponse
(pensée, texte, tour terminé ou coupé) de `lire_reponse`. Une réponse vide ou coupée n'est jamais une
erreur : elle est rendue telle quelle, `terminee` à faux, et c'est à la mesure de la compter.

`choisir_le_lot` prend le plus grand lot que la mémoire de la carte graphique permet. `discuter` est la
boucle de conversation en ligne de commande.
"""

from collections.abc import Callable, Sequence

import torch

from forge.conversation.format import Reponse, Tour, invite_de_reponse, lire_reponse
from forge.fichiers import ESPACE_FINE, entier
from forge.modele import Transformer, generer_lot
from forge.tokenizer.bpe_octets import TokenizerOctets

LOT_PAR_DEFAUT = 32  # sur le processeur, et pour `repondre_lot` quand on n'en demande pas d'autre
LOT_MAXIMUM = 256  # sur la carte : la mémoire dit ce qui tient, jusqu'à ce plafond
PART_DE_LA_MEMOIRE = 0.75  # on ne compte que les trois quarts de la mémoire libre, pour le reste du calcul

JETONS_DE_REPONSE = 512  # la longueur maximale d'une réponse de `discuter`
JETONS_MINIMUM_DE_REPONSE = 32  # en dessous, la fenêtre de contexte est pleine
TEMPERATURE_DE_LA_CONVERSATION = 0.7
TOP_K_DE_LA_CONVERSATION = 50

_FINE = ESPACE_FINE


# --- La mémoire de la carte ------------------------------------------------------------------------------------


def _est_sur_la_carte(appareil: torch.device) -> bool:
    return appareil.type == "cuda"


def _memoire_libre(appareil: torch.device) -> int:
    """Les octets libres de la carte, tous programmes confondus (Ollama et le jeu y ont leur part)."""
    return torch.cuda.mem_get_info(appareil)[0]


def choisir_le_lot(
    modele: Transformer,
    longueur_max: int,
    longueur_invite_max: int,
    maximum: int = LOT_MAXIMUM,
    par_defaut: int = LOT_PAR_DEFAUT,
) -> int:
    """Le plus grand lot (une puissance de 2, au plus `maximum`) que la mémoire libre de la carte permet.

    Sur le processeur, `par_defaut`. Sur la carte, chaque texte du lot coûte :

    - son cache des clés et des valeurs : 2 tenseurs de `couches × dim × longueur_max` nombres en bf16 ;
    - les scores de toutes les positions de son invite au pré-remplissage : `taille_vocabulaire ×
      longueur_invite_max` nombres en bf16, que `modele.avancer` rend pour tout le lot d'un coup.

    On garde un quart de la mémoire libre pour le reste (poids déjà chargés, activations). Au moins 1.
    """
    appareil = next(modele.parameters()).device
    if not _est_sur_la_carte(appareil):
        return par_defaut
    c = modele.config
    par_texte = 4 * c.couches * c.dim * longueur_max + 2 * c.taille_vocabulaire * longueur_invite_max
    budget = PART_DE_LA_MEMOIRE * _memoire_libre(appareil)
    lot = 1
    while lot * 2 <= maximum and 2 * lot * par_texte <= budget:
        lot *= 2
    return lot


# --- Faire répondre un modèle ---------------------------------------------------------------------------------


def _generer_en_deux_si_manque_de_memoire(generer: Callable[[list[int]], list[list[int]]], numeros: list[int]):
    """Rend les jetons de chaque texte de `numeros` ; si la carte manque de mémoire, coupe le lot en deux."""
    try:
        return generer(numeros)
    except torch.cuda.OutOfMemoryError:
        if len(numeros) == 1:
            raise
        torch.cuda.empty_cache()
        milieu = len(numeros) // 2
        return _generer_en_deux_si_manque_de_memoire(generer, numeros[:milieu]) + _generer_en_deux_si_manque_de_memoire(
            generer, numeros[milieu:]
        )


def repondre_lot(
    modele: Transformer,
    tok: TokenizerOctets,
    conversations: Sequence[Sequence[Tour]],
    n_nouveaux: int = 512,
    temperature: float = 0.0,
    top_k: int = 50,
    graine: int = 0,
    lot: int = 32,
    couper_si_manque_de_memoire: bool = True,
) -> list[Reponse]:
    """Fait répondre le modèle à chaque conversation (qui finit par un tour de l'utilisateur) ; une `Reponse` chacune, dans l'ordre.

    - `n_nouveaux` : le nombre maximal de jetons d'une réponse. Une réponse qui n'a pas écrit `<|fin_tour|>`
      avant la limite est rendue coupée (`terminee` faux) ;
    - `temperature` (0 : choix glouton), `top_k`, `graine` : comme `generer_lot`. Même appel, mêmes réponses ;
    - `lot` : combien de conversations avancent ensemble ;
    - `couper_si_manque_de_memoire` : si la carte manque de mémoire, le lot est coupé en deux et le calcul
      continue. À température non nulle, le tirage dépend du lot : un travail qui doit se refaire à l'identique
      (les paires de 1.8) passe `False`, et le manque de mémoire remonte (`torch.cuda.OutOfMemoryError`).

    Les conversations sont rangées par longueur d'invite avant d'être découpées en lots (moins de bourrage),
    puis remises dans l'ordre : le lot d'une conversation dépend donc des autres longueurs, ce qui ne compte
    qu'à température non nulle. La graine du lot numéro `k` est `graine + k`.

    Le contexte du modèle est une limite dure : un lot n'écrit pas plus de `longueur_contexte − sa plus longue
    invite` jetons, et une invite qui remplit tout le contexte reçoit une réponse vide et coupée, au lieu de
    faire échouer toute l'évaluation.
    """
    if lot < 1:
        raise ValueError(f"`lot` vaut {lot} : il faut au moins une conversation par lot.")
    contexte = modele.config.longueur_contexte
    invites = [invite_de_reponse(tok, tours) for tours in conversations]
    fin_tour = tok.id_special("<|fin_tour|>")
    reponses: list[Reponse | None] = [None] * len(invites)
    a_ecrire = []
    for numero in sorted(range(len(invites)), key=lambda i: len(invites[i])):
        if len(invites[numero]) >= contexte or n_nouveaux < 1:
            reponses[numero] = Reponse(texte="", pensee=None, ids=[], terminee=False)
        else:
            a_ecrire.append(numero)
    for rang, debut in enumerate(range(0, len(a_ecrire), lot)):
        groupe = a_ecrire[debut : debut + lot]
        place = min(n_nouveaux, contexte - len(invites[groupe[-1]]))  # le dernier est le plus long

        def generer(numeros: list[int], place: int = place, rang: int = rang) -> list[list[int]]:
            return generer_lot(
                modele, [invites[i] for i in numeros], place, temperature, top_k, graine + rang, fin_tour, len(numeros)
            )

        sorties = _generer_en_deux_si_manque_de_memoire(generer, groupe) if couper_si_manque_de_memoire else generer(groupe)
        for numero, ids in zip(groupe, sorties):
            reponses[numero] = lire_reponse(tok, ids)
    return reponses  # type: ignore[return-value]  # chaque case a reçu sa réponse


# --- La conversation en ligne de commande ---------------------------------------------------------------------------


def discuter(
    modele: Transformer,
    tok: TokenizerOctets,
    version: str,
    systeme: str | None = None,
    temperature: float = TEMPERATURE_DE_LA_CONVERSATION,
    entrer: Callable[[str], str] | None = None,
) -> int:
    """La boucle de conversation avec une version publiée ; rend le code de sortie (0).

    Chaque ligne tapée est un tour de l'utilisateur ; ton IA répond avec tout ce qui précède sous les yeux.
    `/nouveau` repart de zéro (le message système, s'il y en a un, est gardé), `/quitter` sort (la fin de la
    saisie aussi). Un message qui ne laisse pas au moins `JETONS_MINIMUM_DE_REPONSE` jetons de place à la
    réponse n'est pas envoyé : le message dit de faire `/nouveau`. Une réponse vide est retirée de
    l'historique avec la question qui l'a appelée, pour que la suite reste une conversation valide.
    """
    entrer = entrer or input  # `input` est cherché maintenant : un test peut le remplacer
    contexte = modele.config.longueur_contexte
    debut = [Tour("systeme", systeme)] if systeme else []
    historique = list(debut)
    reponses_donnees = 0
    print(
        f"Conversation avec {version}. Écris /nouveau pour repartir de zéro, /quitter pour sortir.",
        flush=True,
    )
    while True:
        try:
            ligne = entrer(f"Toi{_FINE}: ").strip()
        except EOFError:
            print()
            return 0
        if ligne == "/quitter":
            return 0
        if ligne == "/nouveau":
            historique = list(debut)
            print("Conversation remise à zéro.", flush=True)
            continue
        if not ligne:
            continue
        tours = [*historique, Tour("utilisateur", ligne)]
        place = contexte - len(invite_de_reponse(tok, tours))
        if place < JETONS_MINIMUM_DE_REPONSE:
            print(
                f"La conversation remplit la fenêtre de contexte du modèle ({entier(contexte, milliers=_FINE)} jetons) "
                f"et ton dernier message n'est pas envoyé{_FINE}: écris /nouveau pour repartir de zéro.",
                flush=True,
            )
            continue
        limite = min(JETONS_DE_REPONSE, place)
        [reponse] = repondre_lot(
            modele, tok, [tours], n_nouveaux=limite, temperature=temperature,
            top_k=TOP_K_DE_LA_CONVERSATION, graine=reponses_donnees, lot=1,
        )
        reponses_donnees += 1
        if not reponse.texte.strip():
            print(
                f"(ton IA n'a rien répondu{_FINE}: ta dernière question est retirée de la conversation, reformule-la.)",
                flush=True,
            )
            continue
        if reponse.pensee:
            print(f"(pensée{_FINE}: {reponse.pensee})", flush=True)
        print(f"{version}{_FINE}: {reponse.texte}", flush=True)
        if not reponse.terminee:
            # Une réponse coupée n'est pas un tour fini : la garder la ré-encoderait avec `<|fin_tour|>`.
            print(
                f"(réponse coupée{_FINE}: ton IA n'avait pas fini quand la limite de "
                f"{entier(limite, milliers=_FINE)} jetons est arrivée. Elle n'est pas gardée dans la conversation, "
                f"ni ta question{_FINE}: reformule-la, ou écris /nouveau.)",
                flush=True,
            )
            continue
        historique = [*tours, Tour("assistant", reponse.texte, pensee=reponse.pensee)]
