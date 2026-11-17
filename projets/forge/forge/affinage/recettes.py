"""Les recettes de jeux d'affinage, et `preparer_jeu` qui les met sur disque.

Une recette dit quelles sources de conversations entrent dans un jeu, combien d'exemples on tire de
chacune, et comment les mettre en rangées (longueur, taille maximale d'un exemple, part de validation,
graine). `preparer_jeu` fait ensuite, dans cet ordre :

1. **refuse** toute part qui est un jeu d'évaluation (IFEval-FR, MGSM-rev2, GSM8K-Platinum-fr,
   HumanEval, HumanEval-FR) ou des problèmes qui ne sont pas d'entraînement : `ValueError` qui la nomme,
   avant de lire ou d'écrire quoi que ce soit ;
2. **lit** chaque source déjà téléchargée et en tire `exemples_max` éléments, dans l'ordre que donne
   `Hasard(graine).melanger` : le même d'une préparation à l'autre, et d'une recette à l'autre (la part de
   rappel de `raisonnement-1.9` reprend les premiers exemples de `sft-1.7`) ;
3. **retire les doublons**, par l'empreinte du premier tour de l'utilisateur. Les couples d'identité, écrits
   exprès avec et sans message système, y échappent ;
4. **décontamine** : un exemple dont un tour d'utilisateur partage 8 mots de suite (`mots()`, sans casse
   ni ponctuation) avec une invite d'un jeu d'évaluation déjà téléchargé est écarté et compté. Une invite
   d'évaluation de moins de 8 mots est comparée en entier. Les jeux comparés sont les sources
   d'évaluation, les problèmes générés d'évaluation et HumanEval-FR ; ceux qui manquent sont dits ;
5. **encode** avec le format de conversation, écarte ce qui dépasse `jetons_max_exemple`, répartit
   entraînement et validation par l'empreinte du premier tour de l'utilisateur (un exemple et ses variantes
   restent du même côté), empaquette chaque partie et écrit le jeu avec `ecrire_jeu` ;
6. écrit à côté `ids.txt.gz` : les empreintes des premiers tours d'utilisateur des exemples gardés, pour
   que la préparation des paires (tâche 13) ne reprenne pas une invite déjà apprise.

Tout est déterministe : deux préparations donnent le même jeu à l'octet près. Rien n'est écrit avant la fin
de la lecture ; l'écriture est atomique et `.complet` vient en dernier, donc une coupure ne laisse jamais
un jeu à moitié écrit pour complet. On relance la même commande : elle refait le même jeu.
"""

import functools
import gzip
import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

from forge.affinage.empaquetage import empaqueter
from forge.affinage.jeu import ecrire_jeu, lire_index
from forge.chemins import racine_donnees, sous_forge_donnees, verifier_place
from forge.conversation.format import ExempleMasque, Tour, conversation_depuis_json, encoder_conversation
from forge.conversation.generees import conversations_identite, conversations_systeme
from forge.conversation.sources import (
    NOMS_RESERVES_A_L_EVALUATION,
    SOURCES_CONVERSATIONS,
    UsageInterdit,
    est_reservee_a_l_evaluation,
    source_d_entrainement,
)
from forge.conversation.telechargement import PREFIXE, dossier_de_la_source, lire_pour_entrainement
from forge.donnees.melange import est_validation
from forge.donnees.nettoyage import empreinte
from forge.donnees.telechargement import MARGE_PLACE
from forge.erreurs import DonneesManquantes
from forge.evaluation.langue import mots
from forge.fichiers import ecrire_atomique
from forge.fragments import lire_elements
from forge.hasard import Hasard
from forge.raisonnement.problemes import Probleme, conversation_de_probleme
from forge.tokenizer import TokenizerOctets

TOKENIZER = Path(__file__).parent.parent / "ressources" / "tokenizer-ton-ia-v1.json"

SYSTEME_GENERE = "systeme_genere"
IDENTITE = "identite"
PREFIXE_DES_PROBLEMES = "problemes:"
PREFIXES_A_VENIR = {"fim:": "la tâche 19 (FIM)", "code_fr:": "la tâche 20 (code en français)"}

GRAMME = 8  # la décontamination compare des suites de 8 mots
FACTEUR_DE_LA_BASE = 4  # `systeme_genere` regarde 4 × n conversations : toutes ne se transforment pas

LICENCE_DU_PROJET = "MIT"
LIEN_DE_LA_LICENCE_DU_PROJET = "https://github.com/chipat-neko/forge-ia/blob/main/LICENSE"

# Les clés d'un élément d'évaluation qui portent une invite (IFEval-FR : invite ; MGSM et GSM8K : question ;
# HumanEval : prompt ; problèmes générés : enonce).
CLES_D_INVITE = ("invite", "question", "prompt", "enonce", "instruction")


@dataclass(frozen=True)
class Part:
    """Une part d'une recette : `source` (le nom d'une source de conversations, `"systeme_genere"`,
    `"identite"`, `"problemes:<nom>"`, `"fim:<nom>"` ou `"code_fr:<nom>"`) et `exemples_max` (`None` : tout)."""

    source: str
    exemples_max: int | None

    def __post_init__(self) -> None:
        if self.exemples_max is not None and self.exemples_max < 1:
            raise ValueError(
                f"{self.source}\u202f: exemples_max doit valoir au moins 1 (reçu {self.exemples_max}). "
                "Donne un nombre d'exemples, ou None pour tout prendre."
            )


@dataclass(frozen=True)
class Recette:
    """Un jeu d'affinage : ses parts, la forme de ses rangées, sa validation et sa graine."""

    nom: str
    parts: tuple[Part, ...]
    longueur: int = 2048
    jetons_max_exemple: int = 1536
    part_validation: float = 0.02
    graine: int = 0

    def __post_init__(self) -> None:
        if not self.parts:
            raise ValueError(f"La recette {self.nom} n'a aucune part : ajoute au moins une source.")
        vues: set[str] = set()
        for part in self.parts:
            if part.source in vues:
                raise ValueError(
                    f"La recette {self.nom} a deux parts pour {part.source}. Garde-en une seule, avec son nombre d'exemples."
                )
            vues.add(part.source)
        if self.longueur < 1:
            raise ValueError(f"La longueur d'une rangée doit valoir au moins 1, pas {self.longueur}.")
        if not 1 <= self.jetons_max_exemple <= self.longueur + 1:
            raise ValueError(
                f"jetons_max_exemple ({self.jetons_max_exemple}) doit tenir dans une rangée de "
                f"{self.longueur + 1} jetons\u202f: entre 1 et {self.longueur + 1}."
            )
        if not 0 <= self.part_validation < 1:
            raise ValueError(f"part_validation doit être au moins 0 et moins de 1, pas {self.part_validation}.")


RECETTES: dict[str, Recette] = {
    r.nom: r
    for r in (
        Recette(
            "sft-1.7",
            (
                Part("luth2_conversation", 150_000),
                Part("aya_fr", None),
                Part("oasst2_fr", None),
                Part(SYSTEME_GENERE, 20_000),
                Part(IDENTITE, None),
            ),
        ),
        Recette(
            "raisonnement-1.9",
            (
                Part(PREFIXE_DES_PROBLEMES + "entrainement-1.9", 60_000),
                Part("luth2_conversation", 12_000),
                Part(SYSTEME_GENERE, 3_000),
                Part(IDENTITE, None),
            ),
        ),
    )
}


@functools.cache
def _tokenizer() -> TokenizerOctets:
    """Le tokenizer figé, chargé une seule fois par processus."""
    return TokenizerOctets.charger(TOKENIZER)


def decrire(recette: Recette) -> dict:
    """La recette telle qu'elle s'écrit dans l'index du jeu."""
    return {
        "nom": recette.nom,
        "parts": [{"source": p.source, "exemples_max": p.exemples_max} for p in recette.parts],
        "longueur": recette.longueur,
        "jetons_max_exemple": recette.jetons_max_exemple,
        "part_validation": recette.part_validation,
        "graine": recette.graine,
    }


# --- Refuser ce qui ne doit pas entrer ------------------------------------------------------------------


def _refus_de_l_evaluation(nom: str) -> UsageInterdit:
    return UsageInterdit(
        f"{nom} est réservée à l'évaluation : on ne la met jamais dans un jeu d'entraînement, sans quoi la "
        "mesure serait faussée. Retire cette part de la recette."
    )


def _verifier_les_parts(recette: Recette) -> None:
    """Refuse, sans toucher au disque, une part interdite, inconnue ou pas encore disponible."""
    for part in recette.parts:
        nom = part.source
        if nom in (SYSTEME_GENERE, IDENTITE) or nom.startswith(PREFIXE_DES_PROBLEMES):
            continue
        for prefixe, tache in PREFIXES_A_VENIR.items():
            if nom.startswith(prefixe):
                raise ValueError(f"{nom}\u202f: les parts «\u202f{prefixe}…\u202f» arrivent avec {tache}. Elles ne sont pas encore disponibles.")
        source = SOURCES_CONVERSATIONS.get(nom)
        if source is None:
            if nom.lower() in NOMS_RESERVES_A_L_EVALUATION or est_reservee_a_l_evaluation(nom, ""):
                raise _refus_de_l_evaluation(nom)
            raise ValueError(
                f"Source inconnue : {nom!r}. Les sources sont {', '.join(SOURCES_CONVERSATIONS)}, "
                f"{SYSTEME_GENERE}, {IDENTITE} et problemes:<nom>."
            )
        source_d_entrainement(nom)  # UsageInterdit si elle est réservée à l'évaluation
        if source.sorte != "conversation":
            raise ValueError(
                f"{nom} n'est pas une source de conversations (sa sorte est {source.sorte})\u202f: elle ne "
                "peut pas être une part d'un jeu d'affinage de conversations."
            )
    if any(p.source == SYSTEME_GENERE for p in recette.parts):
        if _part_de_base(recette) is None:
            raise ValueError(
                f"{SYSTEME_GENERE} a besoin d'une part de conversations d'une source (par exemple "
                "luth2_conversation) : ses questions en viennent. Ajoute-la à la recette."
            )
        if next(p for p in recette.parts if p.source == SYSTEME_GENERE).exemples_max is None:
            raise ValueError(f"{SYSTEME_GENERE} a besoin d'un nombre d'exemples (exemples_max), pas de «\u202ftout\u202f».")


def _part_de_base(recette: Recette) -> Part | None:
    """La première part de conversations d'une source : c'est d'elle que viennent les questions de `systeme_genere`."""
    return next((p for p in recette.parts if p.source in SOURCES_CONVERSATIONS), None)


# --- Lire et tirer --------------------------------------------------------------------------------------


class _Tirage:
    """L'ordre tiré d'une source : ses éléments dans l'ordre de `Hasard(graine).melanger`, lus à la demande.

    Les éléments ne sont pas tous gardés en mémoire : on compte, on mélange les positions, puis on relit la
    source pour ne garder que celles qui sont demandées.
    """

    def __init__(self, lire: Callable[[], Iterator[dict]], graine: int) -> None:
        self._lire = lire
        self.n = sum(1 for _ in lire())
        self._ordre = Hasard(graine).melanger(range(self.n))

    def prendre(self, debut: int, fin: int) -> list[dict]:
        """Les éléments des rangs `debut` à `fin - 1` de l'ordre tiré (moins s'il n'y en a pas assez)."""
        positions = self._ordre[debut:fin]
        rang_de = {position: rang for rang, position in enumerate(positions)}
        trouves: list[dict | None] = [None] * len(positions)
        restants = len(positions)
        for position, element in enumerate(self._lire()):
            if restants == 0:
                break
            rang = rang_de.get(position)
            if rang is not None:
                trouves[rang] = element
                restants -= 1
        return [element for element in trouves if element is not None]


def _lecteur_de_problemes(nom: str) -> Callable[[], Iterator[dict]]:
    """Le lecteur des problèmes d'entraînement `nom` ; refuse ceux d'un autre usage et dit ce qui manque."""
    dossier = sous_forge_donnees(nom, "problemes")
    commande = f"python -m forge problemes --sortie {nom} --nombre N --graine-depart G"
    index = dossier / "index.json"
    if not (dossier / ".complet").is_file() or not index.is_file():
        raise DonneesManquantes(
            f"Les problèmes {nom!r} ne sont pas (ou pas entièrement) générés\u202f: {dossier / '.complet'} manque. "
            f"Lance, avec les bons nombre et graine\u202f: {commande}"
        )
    usage = json.loads(index.read_text(encoding="utf-8")).get("usage")
    if usage != "entrainement":
        raise ValueError(
            f"{PREFIXE_DES_PROBLEMES}{nom}\u202f: ces problèmes sont d'usage {usage!r}, pas d'entraînement. "
            "Ils ne vont jamais dans un jeu d'entraînement\u202f: génère des problèmes avec des graines d'entraînement "
            "(de 0 à 999 999)."
        )
    return lambda: lire_elements(dossier, "problemes")


def _tours_de_probleme(element: dict) -> list[Tour]:
    return conversation_de_probleme(
        Probleme(
            id=element["id"],
            famille=element["famille"],
            difficulte=element["difficulte"],
            enonce=element["enonce"],
            etapes=tuple(element["etapes"]),
            reponse=element["reponse"],
        )
    )


# --- Décontaminer ---------------------------------------------------------------------------------------


class _Decontamination:
    """Les invites des jeux d'évaluation déjà téléchargés, sous la forme de suites de 8 mots.

    Deux ensembles : les jeux externes (sources d'évaluation, HumanEval-FR) et les problèmes générés
    d'évaluation. Les problèmes d'entraînement et d'évaluation sont écrits avec les mêmes gabarits de
    phrases (seuls les prénoms et les nombres changent) : comparés par suites de 8 mots, presque tous seraient
    écartés. Un problème d'entraînement n'est donc comparé aux problèmes d'évaluation que mot pour mot
    (empreinte de l'énoncé), et aux jeux externes comme tout le reste.
    """

    def __init__(self) -> None:
        self.externes: set[tuple[str, ...]] = set()
        self.problemes: set[tuple[str, ...]] = set()
        self.enonces: set[str] = set()
        self.jeux: list[str] = []
        self.absents: list[str] = []

    @staticmethod
    def _gerer(cible: set[tuple[str, ...]], texte: str) -> None:
        m = mots(texte)
        if 0 < len(m) < GRAMME:
            cible.add(tuple(m))  # une invite plus courte qu'un 8-gramme se compare en entier
        for i in range(len(m) - GRAMME + 1):
            cible.add(tuple(m[i : i + GRAMME]))

    def ajouter_externe(self, element: dict) -> None:
        for cle in CLES_D_INVITE:
            if isinstance(element.get(cle), str):
                self._gerer(self.externes, element[cle])

    def ajouter_probleme(self, element: dict) -> None:
        enonce = element.get("enonce")
        if isinstance(enonce, str):
            self._gerer(self.problemes, enonce)
            self.enonces.add(empreinte(enonce))

    def contamine(self, tours: list[Tour], *, probleme: bool) -> bool:
        """Vrai si un tour d'utilisateur reprend 8 mots de suite d'une invite d'évaluation (ou, pour un
        problème généré, l'énoncé d'un problème d'évaluation mot pour mot)."""
        ensembles = (self.externes,) if probleme else (self.externes, self.problemes)
        for tour in tours:
            if tour.role != "utilisateur":
                continue
            if probleme and empreinte(tour.texte) in self.enonces:
                return True
            m = mots(tour.texte)
            if 0 < len(m) < GRAMME:
                if any(tuple(m) in ensemble for ensemble in ensembles):
                    return True
                continue
            for i in range(len(m) - GRAMME + 1):
                morceau = tuple(m[i : i + GRAMME])
                if any(morceau in ensemble for ensemble in ensembles):
                    return True
        return False

    def decrire(self) -> dict:
        return {"taille_des_grammes": GRAMME, "jeux": list(self.jeux), "absents": list(self.absents)}


def _charger_l_evaluation(journal: Callable[[str], None]) -> _Decontamination:
    """Lit les jeux d'évaluation déjà téléchargés ; dit lesquels manquent."""
    decontamination = _Decontamination()
    dossiers = {nom: dossier_de_la_source(s) for nom, s in SOURCES_CONVERSATIONS.items() if s.usage == "evaluation"}
    if "humaneval_fr" not in SOURCES_CONVERSATIONS:  # HumanEval-FR arrive à la tâche 20, hors du registre : manquant, il est dit comme les autres
        dossiers["humaneval_fr"] = sous_forge_donnees("humaneval_fr", "conversations")
    for nom, dossier in dossiers.items():
        if (dossier / ".complet").is_file():
            for element in lire_elements(dossier, PREFIXE):
                decontamination.ajouter_externe(element)
            decontamination.jeux.append(nom)
        else:
            decontamination.absents.append(nom)
    racine = racine_donnees() / "problemes"
    if racine.is_dir():
        for dossier in sorted(racine.iterdir()):
            index = dossier / "index.json"
            if not index.is_file() or json.loads(index.read_text(encoding="utf-8")).get("usage") != "evaluation":
                continue
            for element in lire_elements(dossier, "problemes"):
                decontamination.ajouter_probleme(element)
            decontamination.jeux.append(f"problemes/{dossier.name}")
    if decontamination.absents:
        journal(
            f"Attention\u202f: décontamination sans {', '.join(decontamination.absents)} (pas téléchargés). "
            "Les exemples ne sont pas comparés à ces jeux\u202f; télécharge-les avec "
            "python -m forge conversations --source NOM, puis refais la préparation."
        )
    return decontamination


# --- Préparer -------------------------------------------------------------------------------------------


@dataclass
class _Comptes:
    lus: int = 0
    doublons: int = 0
    contamines: int = 0
    trop_longs: int = 0
    invalides: int = 0
    gardes: int = 0


def _licence_de(part: Part, base: Part | None) -> tuple[str, str]:
    """(licence, lien) d'une part."""
    nom = part.source
    if nom in SOURCES_CONVERSATIONS:
        return SOURCES_CONVERSATIONS[nom].licence, SOURCES_CONVERSATIONS[nom].url_licence
    if nom == IDENTITE:
        return f"{LICENCE_DU_PROJET} (textes écrits à la main dans le dépôt)", LIEN_DE_LA_LICENCE_DU_PROJET
    if nom.startswith(PREFIXE_DES_PROBLEMES):
        return f"{LICENCE_DU_PROJET} (problèmes générés par le code du dépôt)", LIEN_DE_LA_LICENCE_DU_PROJET
    # systeme_genere : le code du dépôt, et des réponses transformées d'une source
    assert base is not None
    source = SOURCES_CONVERSATIONS[base.source]
    return (
        f"{LICENCE_DU_PROJET} (messages système du dépôt)\u202f; réponses transformées de {source.nom} ({source.licence})",
        LIEN_DE_LA_LICENCE_DU_PROJET,
    )


def _ecrire_les_identifiants(chemin: Path, identifiants: list[str]) -> None:
    contenu = ("\n".join(identifiants) + "\n").encode("ascii") if identifiants else b""

    def ecrire(fichier) -> None:
        with gzip.GzipFile(fileobj=fichier, mode="wb", compresslevel=6, mtime=0) as compresse:
            compresse.write(contenu)

    verifier_place(len(contenu) + MARGE_PLACE, chemin.parent)
    ecrire_atomique(chemin, ecrire)


def preparer_jeu(
    recette: Recette, sortie: Path | None = None, *, journal: Callable[[str], None] | None = None
) -> dict:
    """Prépare le jeu d'affinage de `recette` dans `affinage/<recette.nom>` (ou `sortie`) ; rend son index.

    Voir le début du module pour les étapes. L'index (et le résumé rendu) donne, par source, les comptes
    `lus`, `gardes` (aussi sous `exemples`), `doublons`, `contamines`, `trop_longs` et `invalides`, avec
    sa `licence` et son `lien`. `lus` compte les exemples tirés de la source (après `exemples_max`) ; pour
    `systeme_genere`, les conversations produites. `decontamination` dit contre quels jeux on a comparé,
    et lesquels manquaient. `journal` reçoit les messages d'avancement.

    Lève `ValueError` (la part d'évaluation ou inconnue, ou aucun exemple gardé), `DonneesManquantes` (une
    source pas téléchargée : le message donne la commande).
    """
    ecrire_message = journal if journal is not None else (lambda _message: None)
    _verifier_les_parts(recette)
    dossier = sous_forge_donnees(sortie if sortie is not None else recette.nom, "affinage")
    tok = _tokenizer()
    bourrage = tok.id_special("<|bourrage|>")

    # Les lecteurs d'abord : une source manquante ou d'un mauvais usage est refusée avant tout travail long.
    lecteurs: dict[str, Callable[[], Iterator[dict]]] = {}
    for part in recette.parts:
        if part.source in SOURCES_CONVERSATIONS:
            source = SOURCES_CONVERSATIONS[part.source]
            lire_pour_entrainement(source)  # DonneesManquantes / UsageInterdit tout de suite
            lecteurs[part.source] = lambda source=source: lire_pour_entrainement(source)
        elif part.source.startswith(PREFIXE_DES_PROBLEMES):
            lecteurs[part.source] = _lecteur_de_problemes(part.source[len(PREFIXE_DES_PROBLEMES) :])
    decontamination = _charger_l_evaluation(ecrire_message)

    tirages: dict[str, _Tirage] = {}

    def tirage(nom: str) -> _Tirage:
        if nom not in tirages:
            tirages[nom] = _Tirage(lecteurs[nom], recette.graine)
        return tirages[nom]

    def conversations_de(part: Part) -> Iterator[list[Tour]]:
        nom = part.source
        if nom == IDENTITE:
            yield from conversations_identite()[: part.exemples_max]
        elif nom == SYSTEME_GENERE:
            base = _part_de_base(recette)
            assert base is not None and part.exemples_max is not None
            debut = base.exemples_max or 0
            candidats = tirage(base.source).prendre(debut, debut + FACTEUR_DE_LA_BASE * part.exemples_max)
            questions = [conversation_depuis_json(element) for element in candidats]
            produites = conversations_systeme(questions, part.exemples_max, recette.graine)
            if len(produites) < part.exemples_max:
                ecrire_message(
                    f"{nom}\u202f: {len(produites)} conversations sur {part.exemples_max} demandées "
                    f"(il n'y a pas assez de questions de {base.source} à transformer)."
                )
            yield from produites
        else:
            if part.exemples_max is None:
                elements = lecteurs[nom]()
            else:
                elements = iter(tirage(nom).prendre(0, part.exemples_max))
            convertir = _tours_de_probleme if nom.startswith(PREFIXE_DES_PROBLEMES) else conversation_depuis_json
            for element in elements:
                yield convertir(element)

    vus: set[str] = set()
    train: list[ExempleMasque] = []
    val: list[ExempleMasque] = []
    identifiants: dict[str, None] = {}
    comptes: dict[str, _Comptes] = {}
    for part in recette.parts:
        ecrire_message(f"{part.source}\u202f: préparation…")
        c = comptes[part.source] = _Comptes()
        est_probleme = part.source.startswith(PREFIXE_DES_PROBLEMES)
        for tours in conversations_de(part):
            c.lus += 1
            premier = next((t for t in tours if t.role == "utilisateur"), None)
            if premier is None:
                c.invalides += 1
                continue
            cle = empreinte(premier.texte)
            if part.source != IDENTITE:  # les couples d'identité sont écrits avec et sans message système, exprès
                if cle in vus:
                    c.doublons += 1
                    continue
                vus.add(cle)
            if decontamination.contamine(tours, probleme=est_probleme):
                c.contamines += 1
                continue
            try:
                exemple = encoder_conversation(tok, tours)
            except ValueError:
                c.invalides += 1
                continue
            if len(exemple.ids) > recette.jetons_max_exemple:
                c.trop_longs += 1
                continue
            c.gardes += 1
            identifiants[cle] = None
            (val if est_validation(cle, recette.part_validation) else train).append(exemple)

    if not train and not val:
        raise ValueError(
            f"La recette {recette.nom} ne garde aucun exemple (tout est doublon, contaminé, trop long ou invalide). "
            "Vérifie les sources téléchargées et les réglages de la recette."
        )
    rangees_train, ecartes_train = empaqueter(train, recette.longueur, bourrage)
    rangees_val, ecartes_val = empaqueter(val, recette.longueur, bourrage)

    base = _part_de_base(recette)
    sources = {}
    for part in recette.parts:
        licence, lien = _licence_de(part, base)
        c = comptes[part.source]
        sources[part.source] = {
            "lus": c.lus,
            "gardes": c.gardes,
            "exemples": c.gardes,
            "doublons": c.doublons,
            "contamines": c.contamines,
            "trop_longs": c.trop_longs,
            "invalides": c.invalides,
            "licence": licence,
            "lien": lien,
        }
    infos = {
        "ecartes": ecartes_train + ecartes_val,
        "longueur": recette.longueur,
        "sources": sources,
        "recette": decrire(recette),
        "decontamination": decontamination.decrire(),
    }
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / ".complet").unlink(missing_ok=True)  # un jeu à moitié refait n'est pas complet
    _ecrire_les_identifiants(dossier / "ids.txt.gz", list(identifiants))
    ecrire_jeu(dossier, rangees_train, rangees_val, "sft", infos, tok)
    return lire_index(dossier)
