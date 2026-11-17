"""Le téléchargement des sources de conversations et d'évaluation, par fragments, repris après une coupure.

Une source s'écrit dans `FORGE_DONNEES/conversations/<source>/` (voir `forge.fragments`) :
`conversations-00000.jsonl.gz`… (un élément par ligne), `etat.json` et `.complet`. La reprise est celle
des textes (plan 6) : à chaque fragment, `etat.json` garde le `state_dict()` du flux `datasets`, et la
relance le recharge, sans relire ce qui est déjà compté. Le saut (`skip`) du premier départ y est gardé
aussi (`sautes_a_l_ouverture`) : un état pris sur un jeu sauté ne se recharge que sur un jeu sauté du même
nombre. Seul un `etat.json` sans état du flux (jeu qui ne sait pas dire où il en est) reprend en relisant le
début du jeu et en sautant les lignes comptées.

Les fragments se coupent entre deux lignes de la source : leur contenu ne dépend ni des coupures ni des
reprises, un téléchargement repris rend les mêmes fichiers qu'un téléchargement d'une traite. Seule la
pause (Ctrl+C) valide un fragment plus court, pour ne rien perdre.
"""

import gzip
from collections.abc import Callable, Iterator
from pathlib import Path

from forge.chemins import sous_forge_donnees, verifier_place
from forge.conversation.sources import LigneEcartee, SourceConversations, exiger_l_entrainement
from forge.donnees.telechargement import MARGE_PLACE, LecteurDeFlux, ouvrir_le_flux
from forge.erreurs import DonneesManquantes
from forge.fichiers import ESPACE_FINE, entier
from forge.fragments import SortieParFragments, lire_elements
from forge.pause import Pause

PREFIXE = "conversations"
FRAGMENT_PAR_DEFAUT = 50_000


class TelechargementEnPause(Exception):
    """Ctrl+C : le fragment en cours est validé, le travail n'est pas fini. Le message dit comment reprendre."""


def dossier_de_la_source(source: SourceConversations) -> Path:
    """`FORGE_DONNEES/conversations/<source>` : là où le téléchargement écrit et où l'on relit."""
    return sous_forge_donnees(source.nom, "conversations")


def _lignes_du_fichier(chemin: str) -> Iterator[dict]:
    """Les lignes d'un fichier JSONL (gzip ou non), en texte : `{"ligne": "<une ligne JSON>"}`."""
    ouvrir = gzip.open if chemin.endswith(".gz") else open
    with ouvrir(chemin, "rt", encoding="utf-8") as fichier:
        for ligne in fichier:
            if ligne.strip():
                yield {"ligne": ligne}


def _jeu_d_un_fichier_json(source: SourceConversations):
    """Un fichier JSONL du dépôt, lu ligne à ligne comme un flux (avec `state_dict` et `skip`).

    Les lignes restent du texte, que `convertir` décode : `datasets` ne sait pas inférer le schéma de
    JSON profondément imbriqué (les arbres d'OASST2 : des réponses dans des réponses, avec des colonnes
    parfois vides) et échoue à le convertir.
    """
    from datasets import IterableDataset
    from huggingface_hub import hf_hub_download

    chemin = hf_hub_download(repo_id=source.depot, filename=source.fichier, repo_type="dataset")
    return IterableDataset.from_generator(_lignes_du_fichier, gen_kwargs={"chemin": str(chemin)})


def lecteur_conversations(
    source: SourceConversations, etat_du_flux: dict | None = None, ignorer: int = 0
) -> LecteurDeFlux:
    """Lit une source depuis Hugging Face, avec la reprise de `forge.donnees.telechargement`.

    Comme `lecteur_hugging_face`, mais pour une `SourceConversations` : le split et la configuration sont
    ceux de la source, un fichier du dépôt (`fichier`) se lit ligne à ligne, et un jeu qui n'est pas lu en flux
    (`flux=False`, les petits jeux d'évaluation) est ouvert en entier puis lu comme un flux, pour garder
    la même reprise. `ignorer` et `etat_du_flux` : voir `ouvrir_le_flux`.
    """
    from datasets import load_dataset  # lourd : importé seulement quand on lit pour de bon

    options = {"streaming": True} if source.flux else {}
    if source.fichier is not None:
        jeu = _jeu_d_un_fichier_json(source)
    elif source.configuration is not None:
        jeu = load_dataset(source.depot, source.configuration, split=source.split, **options)
    else:
        jeu = load_dataset(source.depot, split=source.split, **options)
    if not source.flux:
        jeu = jeu.to_iterable_dataset()
    return ouvrir_le_flux(source.nom, jeu, etat_du_flux, ignorer)


def _commande_de_reprise(source: SourceConversations, exemples_max: int | None) -> str:
    option = f" --exemples-max {exemples_max}" if exemples_max is not None else ""
    return f"python -m forge conversations --source {source.nom}{option}"


def _nombre(valeur: int) -> str:
    return entier(valeur, milliers=ESPACE_FINE)


def telecharger_source(
    source: SourceConversations,
    exemples_max: int | None = None,
    *,
    par_fragment: int = FRAGMENT_PAR_DEFAUT,
    journal: Callable[[str], None] | None = None,
) -> Path:
    """Télécharge `source` vers `sous_forge_donnees(source.nom, "conversations")` ; renvoie ce dossier.

    On s'arrête quand `exemples_max` éléments sont gardés (sans limite : quand la source est épuisée), et
    `.complet` est alors posé, avec le nom, la licence, l'usage et les comptes (lus, gardés, écartés par
    raison). Après une coupure (réseau, courant, disque plein), on relance la même commande : les
    fragments déjà écrits sont gardés, rien n'est écrit deux fois. Un `exemples_max` plus grand prolonge
    une source déjà complète ; une source épuisée n'est pas relue.

    Ctrl+C valide le fragment en cours, puis lève `TelechargementEnPause` : son message est la commande
    de reprise. Un second Ctrl+C arrête tout de suite (`KeyboardInterrupt`) : le fragment en cours est
    perdu, les précédents sont bons.
    """
    dossier = dossier_de_la_source(source)
    ecrire = journal if journal is not None else (lambda _message: None)
    sortie = SortieParFragments(dossier, PREFIXE, par_fragment)
    etat = sortie.etat or {}
    if sortie.complet:
        if sortie.infos.get("epuisee") or (exemples_max is not None and sortie.deja >= exemples_max):
            ecrire(f"{source.nom}\u202f: déjà complet.")
            return dossier
        sortie.rouvrir()  # on demande plus que ce qui est écrit : on reprend où l'on s'était arrêté

    lus: int = etat.get("lus", 0)
    ecartes: dict[str, int] = dict(etat.get("ecartes", {}))
    flux_precedent = etat.get("etat_du_flux")
    # Sans état du flux, on saute les lignes comptées ; avec, on refait le même saut qu'à l'ouverture où
    # il a été pris (zéro, sauf après la reprise d'un ancien état).
    sautes = lus if flux_precedent is None else etat.get("sautes_a_l_ouverture", 0)
    verifier_place(MARGE_PLACE, dossier)
    lecteur = lecteur_conversations(source, etat_du_flux=flux_precedent, ignorer=sautes)
    if lus:
        ancien = "" if flux_precedent is not None else ", ancien état : le flux est relu depuis le début"
        ecrire(f"{source.nom}\u202f: reprise après {_nombre(lus)} lignes lues{ancien}.")

    def gardes() -> int:
        return sortie.deja + sortie.en_attente

    def valider() -> None:
        """Écrit le fragment, puis l'état : celui du flux juste après la dernière ligne comptée."""
        verifier_place(sortie.octets_en_attente + MARGE_PLACE, dossier)
        etat_du_flux = lecteur.etat()
        ecrit = sortie.en_attente
        sortie.valider(
            {
                "etat_du_flux": etat_du_flux,
                "sautes_a_l_ouverture": sautes if etat_du_flux is not None else 0,
                "lus": lus,
                "ecartes": dict(ecartes),
            }
        )
        if ecrit:
            ecrire(
                f"{source.nom}\u202f: {_nombre(sortie.deja)} éléments gardés, "
                f"{_nombre(lus)} lignes lues."
            )

    atteint = exemples_max is not None and sortie.deja >= exemples_max  # coupure juste avant le marqueur
    epuisee = not atteint
    try:
        with Pause(en_cours="le fragment en cours", sauvegarde="je valide ce fragment") as pause:
            for ligne in () if atteint else lecteur:
                lus += 1
                try:
                    for element in source.convertir(ligne):
                        sortie.ajouter(element)
                except LigneEcartee as ecartee:
                    ecartes[ecartee.raison] = ecartes.get(ecartee.raison, 0) + 1
                if exemples_max is not None and gardes() >= exemples_max:
                    epuisee = False
                    break
                if sortie.plein or pause.demandee:
                    valider()
                    if pause.demandee:
                        raise TelechargementEnPause(
                            f"Pause : {source.nom}, {_nombre(sortie.deja)} éléments validés, "
                            f"{_nombre(lus)} lignes lues. Pour reprendre, relance la même commande"
                            f"\u202f: {_commande_de_reprise(source, exemples_max)}"
                        )
            # Le dernier fragment se valide flux ouvert : son état est pris après la dernière ligne.
            valider()
    finally:
        lecteur.close()  # ferme le flux de la source (connexions ouvertes) : arrêt voulu ou erreur
    sortie.terminer(
        {
            "nom": source.nom,
            "depot": source.depot,
            "configuration": source.configuration,
            "split": source.split,
            "licence": source.licence,
            "url_licence": source.url_licence,
            "usage": source.usage,
            "sorte": source.sorte,
            "lus": lus,
            "gardes": sortie.deja,
            "ecartes": dict(ecartes),
            "epuisee": epuisee,
            "exemples_max": exemples_max,
        }
    )
    detail = ", ".join(f"{_nombre(n)} {raison}" for raison, n in sorted(ecartes.items()))
    ecrire(
        f"{source.nom}\u202f: terminé, {_nombre(sortie.deja)} éléments gardés sur {_nombre(lus)} lignes lues"
        + (f" (écartés\u202f: {detail})" if detail else "")
        + (" (source épuisée)." if epuisee else ".")
    )
    return dossier


def lire_pour_entrainement(source: SourceConversations) -> Iterator[dict]:
    """Les éléments d'une source d'entraînement déjà téléchargée en entier.

    C'est la seule porte par laquelle un entraînement lit une source : une source réservée à l'évaluation
    lève `UsageInterdit` avant tout, sans toucher au disque. Une source pas encore complète lève
    `DonneesManquantes` avec la commande qui la termine.
    """
    exiger_l_entrainement(source)
    dossier = dossier_de_la_source(source)
    if not (dossier / ".complet").exists():
        raise DonneesManquantes(
            f"{source.nom} n'est pas (ou pas entièrement) téléchargée : {dossier / '.complet'} manque. "
            f"Lance : {_commande_de_reprise(source, None)}"
        )
    return lire_elements(dossier, PREFIXE)
