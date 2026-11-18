"""La construction des paires de préférences de 1.8 : deux réponses de ton IA par invite, classées par programme.

`construire_paires` fait, pour une recette (`RECETTES_PREFERENCES`) :

1. **les questions** : celles de `luth2_conversation` (lue par `lire_pour_entrainement`, la seule porte d'une
   source d'entraînement : une source d'évaluation y lève `UsageInterdit`), moins celles que le SFT a déjà
   apprises (`affinage/sft-1.7/ids.txt.gz`) et celles dont l'invite dépasse `longueur − n_nouveaux` jetons ;
2. **les invites** : `invites_de_preference` (70 % de questions avec consignes, 30 % de problèmes), puis la
   décontamination de `forge.affinage.recettes` : une invite qui partage 8 mots de suite avec un jeu
   d'évaluation est écartée et comptée, comme une invite devenue trop longue avec ses consignes. La liste est
   écrite dans `<jeu>/paires/invites.jsonl.gz` au premier départ : une reprise la relit, sans dépendre des
   données (Luth-2, `sft-1.7`, jeux d'évaluation), qui ont pu changer entre-temps ;
3. **les réponses**, par paquets de `INVITES_PAR_PAQUET` invites : `repondre_lot` (température, top-k et
   graine `recette.graine + rang du paquet`), deux réponses par invite, `noter`, puis `choisir_paire` avec le
   plancher de `sans_paire` : une paire n'est gardée que si la choisie est terminée et, pour un problème, juste
   (sinon « aucune bonne réponse », compté à part, comme les égalités). Chaque invite, ses réponses (texte,
   pensée, jetons, terminée), ses notes, sa paire et la raison qui l'a départagée (ou pourquoi il n'y en a pas)
   vont dans `<jeu>/paires/` (`SortieParFragments`, un fragment par paquet). Une relance reprend au paquet
   suivant, sur le même appareil et avec le même lot de génération : les paires sont les mêmes qu'en une traite,
   sans doublon ni trou. Ctrl+C finit le paquet en cours, le valide, puis lève `PairesEnPause` (la commande de
   reprise) ;
4. **le jeu** `dpo` (`ecrire_jeu`), dans `<jeu>/` : pour chaque paire, la rangée de la réponse choisie puis
   celle de la rejetée, chacune l'invite (jusqu'à `<|assistant|>`) suivie de la réponse telle que ton IA l'a
   écrite, et de son `<|fin_tour|>` si elle l'a écrit. La perte ne porte que sur la réponse. Les invites de la
   validation (`part_validation`, d'après l'empreinte de leur identifiant) vont dans `val/`. L'index dit les
   invites, les paires, les égalités, les invites sans bonne réponse, le taux de paires (après le plancher), le
   critère qui a départagé chaque paire, et les longueurs (`longueurs` : jetons moyens des choisies et des
   rejetées, part des paires où la choisie est la plus courte), de quoi voir un biais vers le court.

**Le lot de génération** est choisi au premier départ d'après la mémoire libre (`choisir_le_lot`) et figé : à
température 1, le tirage en dépend. Sous `LOT_MINIMUM`, la commande ne part pas (`MemoireInsuffisante` : libère la
carte). À la reprise, il faut le même appareil et la mémoire du même lot ; un manque de mémoire en cours de route
arrête le travail au lieu de couper le lot en deux, et le paquet en cours se refait à la relance.

Le taux de paires est affiché : sous `SEUIL_DU_TAUX_DE_PAIRES`, l'utilisateur a demandé qu'on s'arrête et qu'on
le lui dise avant la DPO. Le code ne décide rien : il compte, il affiche, et la commande rend un code à part.

Les deux recettes ont la même graine : les invites de `preferences-1.8-court` sont parmi celles de `preferences-1.8`
(les premières questions du même mélange, avec les mêmes consignes, et les premiers problèmes), dans un autre ordre.
"""

import gzip
import hashlib
import json
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

import torch

from forge.affinage.empaquetage import Rangee
from forge.affinage.jeu import ecrire_jeu, lire_index
from forge.affinage.recettes import LICENCE_DU_PROJET, LIEN_DE_LA_LICENCE_DU_PROJET, charger_l_evaluation
from forge.chemins import sous_forge_donnees, verifier_place
from forge.conversation.format import Reponse, Tour, conversation_depuis_json, conversation_vers_json, invite_de_reponse
from forge.conversation.sources import SOURCES_CONVERSATIONS
from forge.conversation.telechargement import lire_pour_entrainement
from forge.donnees.melange import est_validation
from forge.donnees.nettoyage import empreinte
from forge.donnees.telechargement import MARGE_PLACE
from forge.erreurs import DonneesManquantes
from forge.evaluation.rapport import choisir_appareil, nombre_fr, pourcent
from forge.evaluation.reponses import choisir_le_lot, repondre_lot
from forge.fichiers import ESPACE_FINE, ecrire_atomique, entier
from forge.fragments import NOM_DE_L_ETAT, SortieParFragments, lire_elements
from forge.pause import Pause
from forge.preferences.invites import InvitePreference, invites_de_preference, tours_de_la_question
from forge.preferences.noter import AUCUNE_BONNE_REPONSE, EGALITE, Note, choisir_paire, noter, raison_de_la_paire, sans_paire
from forge.processeur import fils_disponibles
from forge.publication import Publication, charger_publication
from forge.tokenizer import TokenizerOctets

INVITES_PAR_PAQUET = 512
DOSSIER_DES_PAIRES = "paires"
PREFIXE_DES_PAIRES = "paires"
FICHIER_DES_INVITES = "invites.jsonl.gz"
SOURCE_DES_QUESTIONS = "luth2_conversation"
JEU_DEJA_APPRIS = "sft-1.7"
SEUIL_DU_TAUX_DE_PAIRES = 0.20  # sous ce taux, la tâche 15 s'arrête et le dit (décision de l'utilisateur)
LOT_MINIMUM = 32  # en dessous, la carte est trop occupée : le travail ne part pas (le lot est figé jusqu'au bout)
VERSION_DES_PAIRES = 1

_FINE = ESPACE_FINE


def _nombre(valeur: int) -> str:
    return entier(valeur, milliers=_FINE)


@dataclass(frozen=True)
class RecettePreferences:
    """Les réglages d'un jeu de paires : combien d'invites, combien de réponses par invite et comment les tirer.

    Une invite a au plus `longueur − n_nouveaux` jetons, une réponse au plus `n_nouveaux` (son `<|fin_tour|>`
    compris) : une paire tient toujours dans des rangées de `longueur + 1` jetons.
    """

    nom: str
    invites: int
    reponses_par_invite: int = 2
    temperature: float = 1.0
    top_k: int = 50
    n_nouveaux: int = 384
    longueur: int = 768
    part_validation: float = 0.05
    graine: int = 0

    def __post_init__(self) -> None:
        if self.invites < 1:
            raise ValueError(f"{self.nom} : il faut au moins une invite (reçu {self.invites}).")
        if self.reponses_par_invite < 2:
            raise ValueError(
                f"{self.nom} : une paire compare au moins deux réponses par invite (reçu {self.reponses_par_invite})."
            )
        if not self.temperature >= 0:
            raise ValueError(f"{self.nom} : la température doit être 0 ou plus (reçu {self.temperature}).")
        if self.top_k < 0:
            raise ValueError(f"{self.nom} : top_k doit être 0 (pas de limite) ou plus (reçu {self.top_k}).")
        if self.n_nouveaux < 1:
            raise ValueError(f"{self.nom} : une réponse a au moins un jeton (reçu n_nouveaux = {self.n_nouveaux}).")
        if self.longueur <= self.n_nouveaux:
            raise ValueError(
                f"{self.nom} : la longueur des rangées ({self.longueur}) doit dépasser celle d'une réponse "
                f"({self.n_nouveaux}) : il faut garder de la place pour l'invite."
            )
        if not 0 <= self.part_validation < 1:
            raise ValueError(f"{self.nom} : part_validation doit être au moins 0 et moins de 1, pas {self.part_validation}.")

    @property
    def jetons_max_invite(self) -> int:
        """Le nombre maximal de jetons d'une invite : au-delà, elle est écartée avant toute génération."""
        return self.longueur - self.n_nouveaux


RECETTES_PREFERENCES: dict[str, RecettePreferences] = {
    r.nom: r
    for r in (
        RecettePreferences("preferences-1.8", 40_000),
        RecettePreferences("preferences-1.8-court", 8_000),
    )
}


class PairesEnPause(Exception):
    """Ctrl+C : le paquet en cours est validé, le travail n'est pas fini. Le message dit comment reprendre."""


# Le compte de l'état et de l'index où va une invite sans paire, selon sa cause.
_COMPTE_DE_LA_CAUSE = {EGALITE: "egalites", AUCUNE_BONNE_REPONSE: "aucune_bonne_reponse"}


class MemoireInsuffisante(RuntimeError):
    """La carte n'a pas la mémoire libre du lot (au moins `LOT_MINIMUM` au départ, le lot figé à la reprise)."""


# --- Les invites, en JSON et retour -------------------------------------------------------------------------


def _invite_en_json(invite: InvitePreference) -> dict:
    return {
        "id": invite.id,
        "tours": conversation_vers_json(invite.tours)["tours"],
        "contraintes": [[nom, kwargs] for nom, kwargs in invite.contraintes],
        "attendu": invite.attendu,
    }


def _invite_de_l_element(element: dict) -> InvitePreference:
    return InvitePreference(
        id=element["id"],
        tours=tuple(conversation_depuis_json(element)),
        contraintes=tuple((nom, kwargs) for nom, kwargs in element["contraintes"]),
        attendu=element["attendu"],
    )


def _empreinte_des_invites(invites: Sequence[InvitePreference]) -> str:
    """SHA-1 des invites, dans l'ordre : une relance qui ne retrouve pas les mêmes ne reprend pas."""
    hache = hashlib.sha1(usedforsecurity=False)
    for invite in invites:
        hache.update(json.dumps(_invite_en_json(invite), ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n")
    return hache.hexdigest()


def _ecrire_les_invites(dossier: Path, invites: Sequence[InvitePreference]) -> None:
    """`<paires>/invites.jsonl.gz`, écrit d'un coup au premier départ (gzip sans date : même contenu, même fichier)."""
    contenu = "".join(json.dumps(_invite_en_json(i), ensure_ascii=False) + "\n" for i in invites).encode("utf-8")

    def ecrire(fichier) -> None:
        with gzip.GzipFile(fileobj=fichier, mode="wb", compresslevel=6, mtime=0) as compresse:
            compresse.write(contenu)

    dossier.mkdir(parents=True, exist_ok=True)
    verifier_place(len(contenu) + MARGE_PLACE, dossier)
    ecrire_atomique(dossier / FICHIER_DES_INVITES, ecrire)


def _lire_les_invites(dossier: Path, empreinte_attendue: str) -> list[InvitePreference]:
    chemin = dossier / FICHIER_DES_INVITES
    if not chemin.is_file():
        raise DonneesManquantes(
            f"{chemin} manque : sans la liste des invites, la reprise ne sait pas quelles paires viennent ensuite. "
            f"Efface le dossier {dossier} et relance la même commande pour tout refaire."
        )
    with gzip.open(chemin, "rt", encoding="utf-8") as fichier:
        invites = [_invite_de_l_element(json.loads(ligne)) for ligne in fichier]
    if _empreinte_des_invites(invites) != empreinte_attendue:
        raise ValueError(
            f"{chemin} a changé depuis le premier départ : ce ne sont plus les invites des paires déjà écrites. "
            f"Efface le dossier {dossier} et relance la même commande pour tout refaire."
        )
    return invites


def _partie(invite: InvitePreference, part_validation: float) -> str:
    """« val » ou « train », d'après l'empreinte de l'identifiant : la même invite tombe toujours du même côté."""
    return "val" if est_validation(empreinte(invite.id), part_validation) else "train"


# --- Les questions et les invites d'une recette -------------------------------------------------------------


def _identifiants_deja_appris() -> set[str]:
    """Les empreintes des premières questions que le SFT a apprises (`ids.txt.gz` du jeu `sft-1.7`)."""
    chemin = sous_forge_donnees(JEU_DEJA_APPRIS, "affinage") / "ids.txt.gz"
    if not chemin.is_file():
        raise DonneesManquantes(
            f"Les questions déjà apprises au SFT ({chemin}) manquent : sans elles, une invite de 1.8 pourrait "
            f"reprendre une question déjà apprise. Prépare le jeu avec : python -m forge preparer --recette {JEU_DEJA_APPRIS}"
        )
    with gzip.open(chemin, "rt", encoding="ascii") as fichier:
        return {ligne.strip() for ligne in fichier if ligne.strip()}


def _question_de_l_element(element: dict) -> tuple[Tour, ...] | None:
    """Le message système éventuel et la première question d'une conversation téléchargée, sans lire le reste."""
    tours = []
    for tour in element["tours"]:
        tours.append(Tour(tour["role"], tour["texte"], tour.get("pensee")))
        if tour["role"] != "systeme":
            break
    return tours_de_la_question(tours)


def _invites_de_la_recette(
    recette: RecettePreferences, tok: TokenizerOctets, journal: Callable[[str], None]
) -> tuple[list[InvitePreference], dict]:
    """Les invites de la recette, déjà décontaminées, et les comptes de ce qui a été écarté (pour l'index)."""
    source = SOURCES_CONVERSATIONS[SOURCE_DES_QUESTIONS]
    elements = lire_pour_entrainement(source)  # UsageInterdit ou DonneesManquantes avant toute lecture
    exclure = _identifiants_deja_appris()
    base: list[tuple[str, tuple[Tour, ...]]] = []
    comptes = {"conversations": 0, "deja_apprises": 0, "trop_longues": 0, "questions": 0}
    for element in elements:
        comptes["conversations"] += 1
        question = _question_de_l_element(element)
        if question is None:
            continue
        identifiant = empreinte(question[-1].texte)
        if identifiant in exclure:
            comptes["deja_apprises"] += 1
        elif len(invite_de_reponse(tok, question)) > recette.jetons_max_invite:
            comptes["trop_longues"] += 1
        else:
            base.append((identifiant, question))
    comptes["questions"] = len(base)
    journal(
        f"{source.nom}{_FINE}: {_nombre(comptes['conversations'])} conversations lues, "
        f"{_nombre(comptes['deja_apprises'])} questions déjà apprises ({JEU_DEJA_APPRIS}), "
        f"{_nombre(comptes['trop_longues'])} de plus de {_nombre(recette.jetons_max_invite)} jetons, "
        f"{_nombre(comptes['questions'])} questions possibles."
    )

    invites = invites_de_preference(recette.invites, recette.graine, base, exclure)
    del base
    decontamination = charger_l_evaluation(journal)
    gardees: list[InvitePreference] = []
    ecartees = {"contaminees": 0, "trop_longues": 0}
    for invite in invites:
        if decontamination.contamine(list(invite.tours), probleme=invite.attendu is not None):
            ecartees["contaminees"] += 1
        elif len(invite_de_reponse(tok, invite.tours)) > recette.jetons_max_invite:
            ecartees["trop_longues"] += 1
        else:
            gardees.append(invite)
    problemes = sum(1 for invite in gardees if invite.attendu is not None)
    journal(
        f"{recette.nom}{_FINE}: {_nombre(len(gardees))} invites ({_nombre(len(gardees) - problemes)} questions avec "
        f"consignes, {_nombre(problemes)} problèmes){_FINE}; écartées{_FINE}: {_nombre(ecartees['contaminees'])} "
        f"proches d'un jeu d'évaluation, {_nombre(ecartees['trop_longues'])} trop longues avec leurs consignes."
    )
    infos = {"base": comptes, "invites_ecartees": ecartees, "decontamination": decontamination.decrire()}
    return gardees, infos


# --- Reprendre au bon endroit -------------------------------------------------------------------------------


def _verifier_les_reglages(trouves: dict | None, attendus: dict, dossier: Path) -> None:
    """Refuse de reprendre des paires faites avec une autre recette, un autre modèle ou d'autres invites."""
    differents = [cle for cle, valeur in attendus.items() if (trouves or {}).get(cle) != valeur]
    if differents:
        raise ValueError(
            f"{dossier} contient des paires faites avec d'autres réglages ({', '.join(differents)} ne sont plus les "
            "mêmes : recette, version du modèle ou invites). Les mélanger donnerait un jeu sans queue ni tête. "
            "Efface ce dossier pour recommencer, ou donne une autre sortie (--sortie NOM)."
        )


def _commande_de_reprise(modele: Path, recette: RecettePreferences, sortie: Path | str | None, appareil: str | None) -> str:
    def argument(valeur) -> str:
        texte = str(valeur)
        return f'"{texte}"' if " " in texte else texte

    commande = f"python -m forge preferences --modele {argument(modele)} --recette {recette.nom}"
    if sortie is not None:
        commande += f" --sortie {argument(sortie)}"
    if appareil is not None:
        commande += f" --appareil {appareil}"
    return commande


# --- Le jeu dpo ---------------------------------------------------------------------------------------------


def _rangee(invite_ids: list[int], reponse: dict, largeur: int, fin_tour: int, bourrage: int) -> Rangee:
    """L'invite, puis la réponse telle qu'elle a été écrite (et son `<|fin_tour|>`), puis du bourrage ; perte sur la réponse."""
    reponse_ids = [*reponse["ids"], *([fin_tour] if reponse["terminee"] else [])]
    ids = invite_ids + reponse_ids
    reste = largeur - len(ids)
    return Rangee(
        ids=ids + [bourrage] * reste,
        appris=[False] * len(invite_ids) + [True] * len(reponse_ids) + [False] * reste,
        documents=[0] * len(ids) + [-1] * reste,
    )


def _longueurs(choisies: Sequence[int], rejetees: Sequence[int]) -> dict:
    """Les jetons moyens des réponses choisies et rejetées, et la part des paires où la choisie est la plus courte.

    De quoi voir un biais vers le court avant la DPO, qui sait l'exploiter. `None` partout s'il n'y a aucune paire.
    """
    if not choisies:
        return {"jetons_choisies": None, "jetons_rejetees": None, "part_choisie_plus_courte": None}
    return {
        "jetons_choisies": sum(choisies) / len(choisies),
        "jetons_rejetees": sum(rejetees) / len(rejetees),
        "part_choisie_plus_courte": sum(1 for c, r in zip(choisies, rejetees) if c < r) / len(choisies),
    }


def _jeu_deja_ecrit(dossier: Path, reglages: dict) -> dict | None:
    if not (dossier / ".complet").is_file():
        return None
    index = lire_index(dossier)
    if index.get("recette") == reglages["recette"] and index.get("modele") == reglages["modele"]:
        return index
    return None


def _ecrire_le_jeu(
    dossier: Path, recette: RecettePreferences, reglages: dict, etat: dict, tok: TokenizerOctets, journal: Callable[[str], None]
) -> dict:
    """Relit les paires de `<jeu>/paires/` et écrit le jeu `dpo` : rangée choisie, puis rangée rejetée."""
    journal(f"{recette.nom}{_FINE}: écriture du jeu dpo…")
    fin_tour, bourrage = tok.id_special("<|fin_tour|>"), tok.id_special("<|bourrage|>")
    largeur = recette.longueur + 1
    parties: dict[str, list[Rangee]] = {"train": [], "val": []}
    exemples = {"questions": 0, "problemes": 0}
    jetons_choisies: list[int] = []
    jetons_rejetees: list[int] = []
    for element in lire_elements(dossier / DOSSIER_DES_PAIRES, PREFIXE_DES_PAIRES):
        if element["paire"] is None:
            continue
        invite_ids = invite_de_reponse(tok, conversation_depuis_json(element))
        for rang in element["paire"]:  # la choisie, puis la rejetée
            parties[element["partie"]].append(_rangee(invite_ids, element["reponses"][rang], largeur, fin_tour, bourrage))
        exemples["problemes" if element["attendu"] is not None else "questions"] += 2
        choisie, rejetee = (element["reponses"][rang] for rang in element["paire"])
        jetons_choisies.append(len(choisie["ids"]) + choisie["terminee"])  # les jetons appris, <|fin_tour|> compris
        jetons_rejetees.append(len(rejetee["ids"]) + rejetee["terminee"])
    source = SOURCES_CONVERSATIONS[SOURCE_DES_QUESTIONS]
    version = reglages["modele"]["version"]
    infos = {
        "ecartes": 0,
        "longueur": recette.longueur,
        "sources": {
            source.nom: {
                "exemples": exemples["questions"],
                "licence": f"{source.licence} (questions) ; réponses écrites par {version}",
                "lien": source.url_licence,
            },
            "problemes": {
                "exemples": exemples["problemes"],
                "licence": f"{LICENCE_DU_PROJET} (problèmes générés par le code du dépôt) ; réponses écrites par {version}",
                "lien": LIEN_DE_LA_LICENCE_DU_PROJET,
            },
        },
        "invites": etat["invites"],
        "paires": etat["paires"],
        "egalites": etat["egalites"],
        "aucune_bonne_reponse": etat["aucune_bonne_reponse"],
        "taux_de_paires": etat["paires"] / etat["invites"] if etat["invites"] else 0.0,
        "raisons": etat["raisons"],
        "longueurs": _longueurs(jetons_choisies, jetons_rejetees),
        "base": etat["base"],
        "invites_ecartees": etat["invites_ecartees"],
        "decontamination": etat["decontamination"],
        "recette": reglages["recette"],
        "modele": reglages["modele"],
    }
    ecrire_jeu(dossier, parties["train"], parties["val"], "dpo", infos, tok)
    return lire_index(dossier)


# --- Construire ---------------------------------------------------------------------------------------------


def _element(invite: InvitePreference, partie: str, reponses: Sequence[Reponse], notes: Sequence[Note]) -> dict:
    """L'invite, ses réponses et leurs notes ; la paire gardée et sa raison, ou pourquoi il n'y en a pas (`sans_paire`)."""
    cause = sans_paire(notes)
    paire = choisir_paire(notes) if cause is None else None
    return {
        **_invite_en_json(invite),
        "partie": partie,
        "reponses": [{"texte": r.texte, "pensee": r.pensee, "ids": r.ids, "terminee": r.terminee} for r in reponses],
        "notes": [list(note) for note in notes],
        "paire": list(paire) if paire is not None else None,
        "raison": raison_de_la_paire(notes[paire[0]], notes[paire[1]]) if paire is not None else None,
        "sans_paire": cause,
    }


def _lot_de_generation(publication: Publication, recette: RecettePreferences) -> int:
    """Le plus grand lot que la mémoire libre permet, pour des invites et des réponses aussi longues que la recette le permet."""
    return choisir_le_lot(publication.modele, recette.longueur, recette.jetons_max_invite)


def _verifier_l_appareil_et_le_lot(
    etat: dict, appareil: torch.device, publication: Publication, recette: RecettePreferences, dossier: Path
) -> None:
    """À la reprise : le même appareil, et assez de mémoire libre pour le lot figé au premier départ."""
    lieux = {"cuda": "la carte graphique", "cpu": "le processeur"}
    if etat["appareil"] != appareil.type:
        raise ValueError(
            f"Ces paires ont commencé sur {lieux[etat['appareil']]} : les reprendre sur {lieux[appareil.type]} changerait "
            f"les tirages (autre lot, autres arrondis). Relance avec --appareil {etat['appareil']}, ou efface {dossier} "
            "pour tout refaire."
        )
    possible = _lot_de_generation(publication, recette)
    if possible < etat["lot"]:
        raise MemoireInsuffisante(
            f"La carte graphique n'a plus assez de mémoire libre pour le lot de {etat['lot']} réponses choisi au premier "
            f"départ (seulement {possible} aujourd'hui). Le lot ne change pas en cours de route : les paires ne seraient "
            "plus celles d'une traite. Libère la carte (jeu, entraînement, Ollama), puis relance la même commande."
        )


def construire_paires(
    modele: Path,
    recette: RecettePreferences,
    sortie: Path | None = None,
    appareil: str | None = None,
    *,
    journal: Callable[[str], None] | None = None,
) -> dict:
    """Construit les paires de `recette` avec la version publiée `modele` ; rend l'index du jeu `dpo`.

    Le jeu va dans `affinage/<recette.nom>` (ou `sortie`, un nom ou un chemin), ses paires dans `paires/`. Voir le
    haut du module pour les étapes. Une relance reprend au paquet suivant ; un travail fini n'est pas refait.
    `appareil` : « cuda » ou « cpu » (la carte si PyTorch la voit, par défaut ; tous les fils du processeur sinon).
    `journal` reçoit les messages d'avancement, un par paquet.

    Lève `UsageInterdit` (source d'évaluation), `DonneesManquantes` (Luth-2 ou `sft-1.7` absents : le message
    donne la commande), `ValueError` (le dossier contient des paires d'autres réglages, ou les rangées dépassent
    le contexte du modèle) et `PairesEnPause` (Ctrl+C, après la validation du paquet en cours).
    """
    ecrire = journal if journal is not None else (lambda _message: None)
    dossier = sous_forge_donnees(sortie if sortie is not None else recette.nom, "affinage")
    dossier_des_paires = dossier / DOSSIER_DES_PAIRES
    choisi = choisir_appareil(appareil)
    publication = charger_publication(Path(modele), choisi.type)
    if choisi.type == "cpu":
        torch.set_num_threads(fils_disponibles())  # tous les fils que ce processus peut utiliser
    contexte = publication.modele.config.longueur_contexte
    if recette.longueur > contexte:
        raise ValueError(
            f"{recette.nom} : des rangées de {recette.longueur} jetons dépassent le contexte de {publication.version} "
            f"({contexte} jetons). Réduis longueur et n_nouveaux."
        )
    tok = publication.tokenizer
    reglages = {
        "version": VERSION_DES_PAIRES,
        "recette": asdict(recette),
        "modele": {"version": publication.version, "empreinte": publication.empreinte_des_poids},
    }

    if (dossier_des_paires / ".complet").is_file():
        paires = SortieParFragments(dossier_des_paires, PREFIXE_DES_PAIRES)
        _verifier_les_reglages(paires.infos, reglages, dossier_des_paires)
        deja = _jeu_deja_ecrit(dossier, reglages)
        if deja is not None:
            ecrire(f"{recette.nom}{_FINE}: déjà fait, rien à refaire ({dossier}).")
            return deja
        return _ecrire_le_jeu(dossier, recette, reglages, paires.infos, tok, ecrire)

    if (dossier_des_paires / NOM_DE_L_ETAT).is_file():
        # Une reprise relit ses invites : elle ne dépend plus de Luth-2, de sft-1.7 ni des jeux d'évaluation.
        paires = SortieParFragments(dossier_des_paires, PREFIXE_DES_PAIRES)
        _verifier_les_reglages(paires.etat, reglages, dossier_des_paires)
        etat = paires.etat
        _verifier_l_appareil_et_le_lot(etat, choisi, publication, recette, dossier_des_paires)
        invites = _lire_les_invites(dossier_des_paires, etat["empreinte_des_invites"])
        ecrire(f"{recette.nom}{_FINE}: reprise après {_nombre(etat['paquets'])} paquets ({_nombre(paires.deja)} invites).")
    else:
        # Le lot est figé au premier départ (à température non nulle, le tirage en dépend) : jamais un petit lot,
        # qui ralentirait tout le travail. On le vérifie avant toute lecture.
        lot = _lot_de_generation(publication, recette)
        if lot < LOT_MINIMUM:
            raise MemoireInsuffisante(
                f"La carte graphique n'a pas assez de mémoire libre : seulement {lot} réponses à la fois, il en faut au "
                f"moins {LOT_MINIMUM}. Le lot est figé pour tout le travail : un petit lot le ralentirait jusqu'au bout. "
                "Libère la carte (jeu, entraînement, Ollama), puis relance la même commande."
            )
        invites, infos_des_invites = _invites_de_la_recette(recette, tok, ecrire)
        _ecrire_les_invites(dossier_des_paires, invites)
        paires = SortieParFragments(dossier_des_paires, PREFIXE_DES_PAIRES)
        etat = {
            **reglages,
            **infos_des_invites,
            "empreinte_des_invites": _empreinte_des_invites(invites),
            "invites": len(invites),
            "invites_par_paquet": INVITES_PAR_PAQUET,
            "appareil": choisi.type,
            "lot": lot,
            "paquets": 0,
            "paires": 0,
            **{compte: 0 for compte in _COMPTE_DE_LA_CAUSE.values()},
            "raisons": {champ: 0 for champ in Note._fields},
        }
        paires.valider(etat)

    taille = etat["invites_par_paquet"]
    nombre_de_paquets = -(-len(invites) // taille)
    k = recette.reponses_par_invite
    ecrire(
        f"{recette.nom}{_FINE}: {_nombre(nombre_de_paquets)} paquets de {_nombre(taille)} invites, {k} réponses par "
        f"invite, lot de {etat['lot']} sur {'la carte graphique' if choisi.type == 'cuda' else 'le processeur'}."
    )
    commande = _commande_de_reprise(modele, recette, sortie, appareil)
    with Pause(en_cours="le paquet en cours", sauvegarde="je valide ce paquet", perdu="ce paquet") as pause:
        for rang in range(etat["paquets"], nombre_de_paquets):
            if pause.demandee:
                paires.valider(etat)  # réécrit etat.json : la pause se voit (pause-entrainement.ps1 -Verification etat)
                raise PairesEnPause(
                    f"Pause{_FINE}: {recette.nom}, {_nombre(etat['paquets'])} paquets faits sur "
                    f"{_nombre(nombre_de_paquets)} ({_nombre(paires.deja)} invites). Pour reprendre, relance la même "
                    f"commande{_FINE}: {commande}"
                )
            debut = time.perf_counter()
            paquet = invites[rang * taille : (rang + 1) * taille]
            conversations = [list(invite.tours) for invite in paquet for _ in range(k)]
            # Graine du paquet : recette.graine + rang. `repondre_lot` y ajoute le rang de chaque lot : deux paquets
            # voisins partagent donc des graines de lots, pour des invites différentes. Les réponses d'une même
            # invite, elles, sont toujours tirées dans le même paquet, chacune de son côté.
            # Sans coupure du lot en deux si la carte manque de mémoire : le tirage changerait. L'erreur remonte, le
            # paquet n'est pas validé, et la relance le refait à l'identique.
            reponses = repondre_lot(
                publication.modele, tok, conversations, recette.n_nouveaux, recette.temperature, recette.top_k,
                recette.graine + rang, etat["lot"], couper_si_manque_de_memoire=False,
            )
            comptes = {"paires": etat["paires"], **{c: etat[c] for c in _COMPTE_DE_LA_CAUSE.values()}}
            raisons = dict(etat["raisons"])
            for numero, invite in enumerate(paquet):
                les_reponses = reponses[numero * k : (numero + 1) * k]
                element = _element(invite, _partie(invite, recette.part_validation), les_reponses,
                                   [noter(r, invite) for r in les_reponses])
                paires.ajouter(element)
                if element["sans_paire"] is None:
                    comptes["paires"] += 1
                    raisons[element["raison"]] += 1
                else:
                    comptes[_COMPTE_DE_LA_CAUSE[element["sans_paire"]]] += 1
            verifier_place(paires.octets_en_attente + MARGE_PLACE, dossier_des_paires)
            paires_du_paquet = comptes["paires"] - etat["paires"]
            sans_bonne_reponse = comptes["aucune_bonne_reponse"] - etat["aucune_bonne_reponse"]
            etat = {**etat, **comptes, "paquets": rang + 1, "raisons": raisons}
            paires.valider(etat)
            duree = max(time.perf_counter() - debut, 1e-9)
            jetons = sum(len(r.ids) + r.terminee for r in reponses)
            ligne = (
                f"{recette.nom}{_FINE}: paquet {_nombre(rang + 1)} sur {_nombre(nombre_de_paquets)}, "
                f"{_nombre(paires_du_paquet)} paires sur {_nombre(len(paquet))} invites ({pourcent(paires_du_paquet / len(paquet))}), "
                f"{_nombre(sans_bonne_reponse)} sans bonne réponse"
                f"{_FINE}; {nombre_fr(len(reponses) / duree)} réponses/s, {_nombre(jetons / duree)} jetons/s"
            )
            if choisi.type == "cuda":
                ligne += f", mémoire maximale de la carte {nombre_fr(torch.cuda.max_memory_allocated(choisi) / 1024**3)}{_FINE}Go"
            ecrire(ligne + ".")
    paires.terminer(etat)
    return _ecrire_le_jeu(dossier, recette, reglages, etat, tok, ecrire)


def invites_de_validation(jeu: Path, n: int) -> list[InvitePreference]:
    """Les `n` premières invites de la partie `val` du jeu de paires `jeu` (un dossier), relues dans ses fragments.

    Ce sont des invites que la DPO n'apprend pas : la mesure `victoire` s'en sert pour choisir entre les essais d'un
    balayage. Lève `DonneesManquantes` (avec la commande) si les paires de ce jeu ne sont pas finies.
    """
    dossier = Path(jeu) / DOSSIER_DES_PAIRES
    if not (dossier / ".complet").is_file():
        raise DonneesManquantes(
            f"Les paires du jeu {jeu} ne sont pas finies ({dossier / '.complet'} manque). Fais-les avec : "
            f"python -m forge preferences --modele DOSSIER --recette {Path(jeu).name}"
        )
    invites: list[InvitePreference] = []
    if n < 1:
        return invites
    for element in lire_elements(dossier, PREFIXE_DES_PAIRES):
        if element["partie"] == "val":
            invites.append(_invite_de_l_element(element))
            if len(invites) >= n:
                break
    return invites
