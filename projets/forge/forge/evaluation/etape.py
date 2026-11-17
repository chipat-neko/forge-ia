"""L'évaluation d'une étape de ton IA : les mêmes mesures sur ton-ia-1.5 et sur chaque version qui suit.

`evaluer_etape` charge une version publiée (voir `forge.publication`), lui fait passer les mesures de son
étape (`MESURES_PAR_ETAPE`) et écrit `rapport.json` (pour les programmes : le plan 8 le lit) et `rapport.md`
(pour la lecture). Les mesures sont les mêmes d'une version à l'autre : le plan 8 montre ton IA d'un chapitre à
l'autre sur les mêmes tests. ton-ia-1.5 ne sait pas converser ; elle passe les mêmes mesures, et une réponse
vide, coupée ou sans queue ni tête y est comptée telle quelle, sans faire échouer l'évaluation.

Les mesures (`MESURES`) :

- `perte_conversation` : la perte d'affinage sur la validation du jeu `affinage/sft-1.7` ;
- `ifeval_fr` : IFEval-FR en glouton, 512 jetons, exactitude stricte par invite et par consigne ;
- `tenue` : sur les réponses d'IFEval-FR et celles aux 100 premières invites de la validation de `sft-1.7`,
  la part terminée par `<|fin_tour|>`, la langue des réponses et leur longueur ;
- `oubli` : la perte et les bits par octet sur 64 morceaux de `jetons/principal/val` (la mesure du plan 6) ;
- `echantillons` : dix invites fixes, en glouton, gardées telles quelles ;
- `problemes` : 400 problèmes générés de la plage d'évaluation, en glouton et en 8 essais ;
- `mgsm_fr` et `gsm8k_platinum_fr` : les problèmes de MGSM et de GSM8K-Platinum en français, en glouton.

Une mesure dont les données manquent rend `{"absente": "<raison>"}` : le rapport le dit, il n'échoue pas.

Les jeux d'évaluation ne servent ici qu'à mesurer (`usage="evaluation"`) : aucun chemin de ce module ne les
écrit dans un jeu d'entraînement.
"""

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import torch

from forge.affinage.jeu import ChargeurAffinage
from forge.chemins import sous_forge_donnees
from forge.conversation.format import Reponse, Tour, invite_de_reponse
from forge.conversation.sources import SOURCES_CONVERSATIONS
from forge.conversation.telechargement import PREFIXE, dossier_de_la_source
from forge.entrainement.chargeur import ChargeurJetons
from forge.entrainement.methodes import MORCEAUX_DE_VALIDATION, perte_sft_validation
from forge.evaluation.consignes import exactitudes, respecte
from forge.evaluation.langue import langue, mots
from forge.evaluation.perte import bits_par_octet, lire_octets_par_jeton, perte_sur_morceaux
from forge.evaluation.rapport import (
    bloc_de_code,
    choisir_appareil,
    guillemets,
    json_valide,
    nombre_fr,
    pourcent,
)
from forge.evaluation.reponses import choisir_le_lot, repondre_lot
from forge.fichiers import ESPACE_FINE, ecrire_texte
from forge.fragments import lire_elements
from forge.processeur import fils_disponibles
from forge.publication import charger_publication
from forge.raisonnement.problemes import GRAINES_EVALUATION, generer_problemes
from forge.raisonnement.verification import est_juste
from forge.tokenizer.bpe_octets import TokenizerOctets

VERSION_DU_RAPPORT_D_ETAPE = 1

_FINE = ESPACE_FINE
_n = nombre_fr
_pourcent = pourcent

# Six questions, deux consignes, la présentation de ton IA et une demande de fonction Python : les mêmes dix
# invites à chaque version, pour qu'on voie d'une version à l'autre ce qui change.
INVITES_DE_CONVERSATION: tuple[str, ...] = (
    "Quelle est la capitale de la France ?",
    "Pourquoi le ciel est-il bleu ?",
    "Explique en deux phrases comment fonctionne la photosynthèse.",
    "Combien font 12 fois 7 ?",
    "Donne-moi trois conseils pour bien dormir.",
    "Quelle est la différence entre un virus et une bactérie ?",
    "Écris un court texte sur l'automne en moins de 50 mots, tout en minuscules.",
    "Présente-toi en trois phrases, sans utiliser de virgule.",
    "Qui es-tu ?",
    "Écris une fonction Python qui renvoie la somme des carrés d'une liste de nombres.",
)

JETONS_IFEVAL = 512
JETONS_PROBLEMES = 384
JETONS_ECHANTILLONS = 200
PROBLEMES_EVALUES = 400
LOT_DES_ESSAIS = 32  # fixe : à température non nulle, le tirage dépend du lot, et la mémoire libre ne doit pas le changer
ESSAIS = 8  # « réussite en 8 essais » : au moins une réponse juste sur 8 tirages (température 1, top-k 50)
INVITES_DE_VALIDATION = 100
MORCEAUX_D_OUBLI = 64
MORCEAUX_PAR_LOT = 8


class DonneeAbsente(Exception):
    """Les données d'une mesure ne sont pas là : la mesure rend `{"absente": <ce message>}`."""


@dataclass
class ContexteDEvaluation:
    """Ce que reçoit chaque mesure : le modèle, son tokenizer, l'appareil, et de quoi ne pas refaire un calcul.

    - `n_max` : le nombre maximal d'exemples de chaque mesure (`None` : tous), pour les essais courts ;
    - `lot` : le nombre de conversations qui avancent ensemble (`None` : le plus grand que la mémoire permet) ;
    - `memo` : les réponses déjà écrites (`tenue` relit celles d'IFEval-FR au lieu de les refaire).
    """

    modele: torch.nn.Module
    tok: TokenizerOctets
    appareil: torch.device
    n_max: int | None = None
    lot: int | None = None
    memo: dict = field(default_factory=dict)

    def limiter(self, n: int) -> int:
        return n if self.n_max is None else min(n, self.n_max)

    def repondre(
        self,
        conversations: list[list[Tour]],
        n_nouveaux: int,
        temperature: float = 0.0,
        top_k: int = 50,
        graine: int = 0,
        lot_fixe: int | None = None,
    ) -> list[Reponse]:
        """`repondre_lot` avec le plus grand lot que la mémoire permet (`self.lot` l'impose, s'il est donné)."""
        lot = lot_fixe or self.lot
        if lot is None:
            longueurs = [len(invite_de_reponse(self.tok, c)) for c in conversations]
            lot = choisir_le_lot(self.modele, max(longueurs, default=0) + n_nouveaux, max(longueurs, default=0))
        return repondre_lot(self.modele, self.tok, conversations, n_nouveaux, temperature, top_k, graine, lot)


# --- Lire les données --------------------------------------------------------------------------------------------


def _lire_source(nom: str, n_max: int | None) -> list[dict]:
    """Les éléments d'une source d'évaluation téléchargée ; `DonneeAbsente` si elle ne l'est pas en entier."""
    source = SOURCES_CONVERSATIONS[nom]
    dossier = dossier_de_la_source(source)
    if not (dossier / ".complet").exists():
        raise DonneeAbsente(
            f"{nom} n'est pas téléchargée ({dossier / '.complet'} manque). "
            f"Télécharge-la avec : python -m forge conversations --source {nom}"
        )
    elements = list(lire_elements(dossier, PREFIXE))
    return elements if n_max is None else elements[:n_max]


def _jeu_d_affinage(nom: str) -> Path:
    dossier = sous_forge_donnees(nom, "affinage")
    if not (dossier / ".complet").exists():
        raise DonneeAbsente(
            f"le jeu d'affinage {nom} n'est pas prêt ({dossier / '.complet'} manque). "
            f"Prépare-le avec : python -m forge preparer --recette {nom}"
        )
    return dossier


def _premiers_tours(tok: TokenizerOctets, document: list[int]) -> list[Tour] | None:
    """Le message système éventuel et le premier tour de l'utilisateur d'un exemple d'affinage, ou `None`."""
    fin_tour = tok.id_special("<|fin_tour|>")
    i = 1 if document and document[0] == tok.id_special("<|fin_texte|>") else 0
    tours: list[Tour] = []
    for role in ("systeme", "utilisateur"):
        marque = tok.id_special(f"<|{role}|>")
        if i >= len(document) or document[i] != marque:
            if role == "systeme":
                continue
            return None
        if fin_tour not in document[i:]:
            return None  # l'exemple est coupé avant la fin de ce tour
        fin = document.index(fin_tour, i)
        texte = tok.decoder(document[i + 1 : fin])
        if not texte.strip():
            return None
        tours.append(Tour(role, texte))
        i = fin + 1
    return tours


def invites_de_validation(dossier: Path, tok: TokenizerOctets, n: int) -> list[list[Tour]]:
    """Les `n` premières invites (système éventuel, puis première question) de la validation d'un jeu d'affinage.

    Les rangées sont lues dans l'ordre de mélange de `ChargeurAffinage` (graine 0, fixe) : l'ordre des rangées
    sur le disque met les exemples les plus longs en premier, il ne dit rien de ce qu'on y trouve.
    """
    chargeur = ChargeurAffinage(dossier, "val", 1, 0)
    invites: list[list[Tour]] = []
    for _ in range(chargeur.rangees):
        lot = chargeur.lot()
        ids, documents = lot.ids[0].tolist(), lot.documents[0].tolist()
        for numero in sorted(set(documents) - {-1}):
            tours = _premiers_tours(tok, [i for i, d in zip(ids, documents) if d == numero])
            if tours:
                invites.append(tours)
                if len(invites) >= n:
                    return invites
    return invites


# --- Les réponses qu'on réutilise -----------------------------------------------------------------------------------


def _reponses_ifeval(ctx: ContexteDEvaluation) -> tuple[list[dict], list[Reponse]]:
    if "ifeval" not in ctx.memo:
        lignes = _lire_source("ifeval_fr", ctx.n_max)
        conversations = [[Tour("utilisateur", ligne["invite"])] for ligne in lignes]
        ctx.memo["ifeval"] = (lignes, ctx.repondre(conversations, JETONS_IFEVAL))
    return ctx.memo["ifeval"]


def _reponses_de_validation(ctx: ContexteDEvaluation) -> list[Reponse]:
    if "validation" not in ctx.memo:
        invites = invites_de_validation(_jeu_d_affinage("sft-1.7"), ctx.tok, ctx.limiter(INVITES_DE_VALIDATION))
        ctx.memo["validation"] = ctx.repondre(invites, JETONS_IFEVAL)
    return ctx.memo["validation"]


# --- Les mesures ---------------------------------------------------------------------------------------------------


def _absente_si_les_donnees_manquent(mesure: Callable[[ContexteDEvaluation], dict]) -> Callable[[ContexteDEvaluation], dict]:
    def entouree(ctx: ContexteDEvaluation) -> dict:
        try:
            return mesure(ctx)
        except DonneeAbsente as raison:
            return {"absente": str(raison)}

    entouree.__name__, entouree.__doc__ = mesure.__name__, mesure.__doc__
    return entouree


@_absente_si_les_donnees_manquent
def _perte_conversation(ctx: ContexteDEvaluation) -> dict:
    """La perte d'affinage (par jeton appris) sur les rangées de validation de `sft-1.7`."""
    chargeur = ChargeurAffinage(_jeu_d_affinage("sft-1.7"), "val", MORCEAUX_PAR_LOT, 0)
    contexte = ctx.modele.config.longueur_contexte
    if chargeur.longueur > contexte:
        raise DonneeAbsente(
            f"les rangées de sft-1.7 ont {chargeur.longueur} jetons, ce modèle n'en lit que {contexte} d'un coup : "
            "la perte de conversation n'a pas de sens ici."
        )
    n = ctx.limiter(min(MORCEAUX_DE_VALIDATION, chargeur.rangees))
    depart = {**chargeur.etat(), "epoque": 0, "position": 0}
    return {"perte": perte_sft_validation(ctx.modele, chargeur, depart, n, ctx.appareil), "n": n}


@_absente_si_les_donnees_manquent
def _ifeval_fr(ctx: ContexteDEvaluation) -> dict:
    """IFEval-FR : exactitude stricte par invite et par consigne, en glouton."""
    lignes, reponses = _reponses_ifeval(ctx)
    resultats = [
        respecte(reponse.texte, ligne["instruction_id_list"], ligne["kwargs"])
        for ligne, reponse in zip(lignes, reponses)
    ]
    return exactitudes(resultats)


@_absente_si_les_donnees_manquent
def _tenue(ctx: ContexteDEvaluation) -> dict:
    """La part de réponses terminées, leur langue et leur longueur, sur IFEval-FR et sur la validation de sft-1.7."""
    reponses: list[Reponse] = []
    manques: list[str] = []
    for source in (lambda: _reponses_ifeval(ctx)[1], lambda: _reponses_de_validation(ctx)):
        try:
            reponses += source()
        except DonneeAbsente as raison:
            manques.append(str(raison))
    if not reponses:
        raise DonneeAbsente(" ; ".join(manques))
    n = len(reponses)
    langues = [langue(r.texte) for r in reponses]
    return {
        "terminee": sum(r.terminee for r in reponses) / n,
        "fr": langues.count("fr") / n,
        "autre": langues.count("autre") / n,
        "indetermine": langues.count("indetermine") / n,
        "mots_moyens": sum(len(mots(r.texte)) for r in reponses) / n,
        "n": n,
    }


@_absente_si_les_donnees_manquent
def _oubli(ctx: ContexteDEvaluation) -> dict:
    """La perte et les bits par octet sur des morceaux fixes de `jetons/principal/val` : ce que le modèle sait encore du français brut."""
    dossier = sous_forge_donnees("principal", "jetons")
    if not (dossier / ".complet").exists():
        raise DonneeAbsente(
            f"les jetons de {dossier} ne sont pas prêts ({dossier / '.complet'} manque). "
            "Encode-les avec : python -m forge encoder --donnees principal --tokenizer <chemin>"
        )
    chargeur = ChargeurJetons(dossier / "val", ctx.modele.config.longueur_contexte, MORCEAUX_PAR_LOT, 0)
    n = ctx.limiter(min(MORCEAUX_D_OUBLI, chargeur.morceaux))
    depart = {**chargeur.etat(), "epoque": 0, "position": 0}
    perte = perte_sur_morceaux(ctx.modele, chargeur, depart, n, ctx.appareil)
    return {"perte": perte, "bits_par_octet": bits_par_octet(perte, lire_octets_par_jeton(dossier)), "n": n}


def _echantillons(ctx: ContexteDEvaluation) -> list[dict]:
    """Dix invites fixes, en glouton, 200 jetons : les réponses sont gardées telles quelles, sans tri."""
    reponses = ctx.repondre([[Tour("utilisateur", invite)] for invite in INVITES_DE_CONVERSATION], JETONS_ECHANTILLONS)
    return [
        {"invite": invite, "texte": r.texte, "pensee": r.pensee, "terminee": r.terminee}
        for invite, r in zip(INVITES_DE_CONVERSATION, reponses)
    ]


def _part(justes: list[bool]) -> float:
    return sum(justes) / len(justes)


def _par_groupe(problemes, glouton: list[bool], essais: list[list[bool]], cle: Callable) -> dict:
    groupes: dict[str, list[int]] = {}
    for rang, p in enumerate(problemes):
        groupes.setdefault(str(cle(p)), []).append(rang)
    return {
        nom: {
            "exactitude": _part([glouton[i] for i in rangs]),
            "reussite_8": _part([any(essais[i]) for i in rangs]),
            "n": len(rangs),
        }
        for nom, rangs in sorted(groupes.items())
    }


def _problemes(ctx: ContexteDEvaluation) -> dict:
    """400 problèmes générés (graines d'évaluation) : exactitude en glouton, et réussite en 8 essais tirés."""
    problemes = generer_problemes(ctx.limiter(PROBLEMES_EVALUES), GRAINES_EVALUATION)
    conversations = [[Tour("utilisateur", p.enonce)] for p in problemes]
    reponses = ctx.repondre(conversations, JETONS_PROBLEMES)
    glouton = [est_juste(r, p.reponse) for r, p in zip(reponses, problemes)]
    tires = ctx.repondre(
        conversations * ESSAIS, JETONS_PROBLEMES, temperature=1.0, top_k=50, lot_fixe=LOT_DES_ESSAIS
    )
    n = len(problemes)
    essais = [[est_juste(tires[k * n + i], p.reponse) for k in range(ESSAIS)] for i, p in enumerate(problemes)]
    return {
        "exactitude": _part(glouton),
        "terminee": _part([r.terminee for r in reponses]),
        "lot": LOT_DES_ESSAIS,
        "reussite_8": _part([any(e) for e in essais]),
        "par_famille": _par_groupe(problemes, glouton, essais, lambda p: p.famille),
        "par_difficulte": _par_groupe(problemes, glouton, essais, lambda p: p.difficulte),
        "n": n,
    }


def _mesure_de_problemes_traduits(source: str) -> Callable[[ContexteDEvaluation], dict]:
    @_absente_si_les_donnees_manquent
    def mesure(ctx: ContexteDEvaluation) -> dict:
        lignes = _lire_source(source, ctx.n_max)
        reponses = ctx.repondre([[Tour("utilisateur", ligne["question"])] for ligne in lignes], JETONS_PROBLEMES)
        return {
            "exactitude": _part([est_juste(r, ligne["reponse"]) for r, ligne in zip(reponses, lignes)]),
            "terminee": _part([r.terminee for r in reponses]),
            "n": len(lignes),
        }

    return mesure


MESURES: dict[str, Callable[[ContexteDEvaluation], dict]] = {
    "perte_conversation": _perte_conversation,
    "ifeval_fr": _ifeval_fr,
    "tenue": _tenue,
    "oubli": _oubli,
    "echantillons": _echantillons,
    "problemes": _problemes,
    "mgsm_fr": _mesure_de_problemes_traduits("mgsm_rev2_fr"),
    "gsm8k_platinum_fr": _mesure_de_problemes_traduits("gsm8k_platinum_fr"),
}

# Les tâches 13 et 21 ajoutent « 1.8 » et « 1.10 ».
MESURES_PAR_ETAPE: dict[str, tuple[str, ...]] = {
    "1.7": ("perte_conversation", "ifeval_fr", "tenue", "oubli", "echantillons"),
    "1.9": ("ifeval_fr", "tenue", "oubli", "problemes", "mgsm_fr", "gsm8k_platinum_fr", "echantillons"),
}


# --- Le rapport -----------------------------------------------------------------------------------------------------


def _mesurer_une_version(dossier: Path, etape: str, appareil: torch.device, n_max: int | None) -> dict:
    """Charge la version de `dossier`, lui fait passer les mesures de `etape` ; rend ce que le rapport en garde."""
    debut = time.perf_counter()
    publication = charger_publication(dossier, appareil.type)
    if appareil.type == "cpu":
        torch.set_num_threads(fils_disponibles())  # tous les fils que ce processus peut utiliser
    ctx = ContexteDEvaluation(publication.modele, publication.tokenizer, appareil, n_max)
    mesures = {nom: MESURES[nom](ctx) for nom in MESURES_PAR_ETAPE[etape]}
    return {
        "version": publication.version,
        "empreinte": publication.empreinte_des_poids,
        "mesures": mesures,
        "secondes": round(time.perf_counter() - debut, 1),
    }


def evaluer_etape(
    modele: Path,
    etape: str,
    sortie: Path,
    reference: Path | None = None,
    appareil: str | None = None,
    n_max: int | None = None,
) -> dict:
    """Évalue la version publiée de `modele` à l'étape `etape` ; écrit `sortie/rapport.json` et `rapport.md` ; rend le rapport.

    - `modele` : le dossier d'une version publiée (poids, `config.json`, tokenizer) ;
    - `etape` : « 1.7 » ou « 1.9 » (voir `MESURES_PAR_ETAPE`) ;
    - `reference` : le dossier d'une autre version (ton-ia-1.5, en général), qui passe les mêmes mesures ; le
      rapport garde les siennes dans `reference` et le Markdown les met en regard ;
    - `appareil` : « cuda » ou « cpu » (la carte si PyTorch la voit, par défaut) ;
    - `n_max` : le nombre maximal d'exemples de chaque mesure (`None` : tous), pour un essai court.

    Le rapport : `version_du_rapport`, `version` du modèle, son `empreinte` (SHA-256 des poids), `etape`, `date`,
    `mesures` (les clés de `MESURES`, rangées dans l'ordre de l'étape), `secondes`, et `reference` si elle est donnée.
    Rien n'est écrit si l'étape est inconnue.
    """
    if etape not in MESURES_PAR_ETAPE:
        raise ValueError(
            f"L'étape {etape!r} n'a pas de mesures. Les étapes sont {', '.join(MESURES_PAR_ETAPE)} : "
            "écris par exemple --etape 1.7."
        )
    if n_max is not None and n_max < 1:
        raise ValueError(f"n_max vaut {n_max} : il faut au moins un exemple par mesure, ou rien pour les passer tous.")
    choisi = choisir_appareil(appareil)
    rapport = {
        "version_du_rapport": VERSION_DU_RAPPORT_D_ETAPE,
        **_mesurer_une_version(Path(modele), etape, choisi, n_max),
        "etape": etape,
        "date": datetime.now().astimezone().isoformat(timespec="seconds"),
        "appareil": choisi.type,
        "n_max": n_max,
    }
    if reference is not None:
        rapport["reference"] = _mesurer_une_version(Path(reference), etape, choisi, n_max)
    sortie = Path(sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    ecrire_texte(
        sortie / "rapport.json",
        json.dumps(json_valide(rapport), ensure_ascii=False, indent=2, allow_nan=False) + "\n",
    )
    ecrire_texte(sortie / "rapport.md", rapport_markdown(rapport))
    return rapport


# --- Raconter en français ----------------------------------------------------------------------------------------


def _ex(m: dict) -> str:
    return f"{_n(m['n'], 0)} ex."


# Pour chaque mesure : les lignes du tableau (libellé, ce qu'on écrit pour un résultat).
_LIGNES: dict[str, list[tuple[str, Callable[[dict], str]]]] = {
    "perte_conversation": [
        ("Perte sur les conversations de validation (sft-1.7)", lambda m: f"{_n(m['perte'], 3)} nats par jeton ({_ex(m)})"),
    ],
    "ifeval_fr": [
        ("IFEval-FR, invites dont toutes les consignes sont respectées", lambda m: f"{_pourcent(m['invite_stricte'])} ({_ex(m)})"),
        ("IFEval-FR, consignes respectées", lambda m: _pourcent(m["consigne_stricte"])),
    ],
    "tenue": [
        ("Réponses terminées par <|fin_tour|>", lambda m: f"{_pourcent(m['terminee'])} ({_ex(m)})"),
        ("Réponses en français", lambda m: _pourcent(m["fr"])),
        ("Réponses dans une autre langue", lambda m: _pourcent(m["autre"])),
        ("Réponses de langue indéterminée", lambda m: _pourcent(m["indetermine"])),
        ("Longueur moyenne d'une réponse", lambda m: f"{_n(m['mots_moyens'])} mots"),
    ],
    "oubli": [
        ("Perte sur le texte du pré-entraînement", lambda m: f"{_n(m['perte'], 3)} nats par jeton ({_ex(m)})"),
        ("Bits par octet sur ce texte", lambda m: _n(m["bits_par_octet"], 3)),
    ],
    "problemes": [
        ("Problèmes générés, exactitude en glouton", lambda m: f"{_pourcent(m['exactitude'])} ({_ex(m)})"),
        ("Problèmes générés, réussite en 8 essais", lambda m: _pourcent(m["reussite_8"])),
        ("Problèmes générés, réponses terminées", lambda m: _pourcent(m["terminee"])),
    ],
    "mgsm_fr": [
        ("MGSM en français, exactitude", lambda m: f"{_pourcent(m['exactitude'])} ({_ex(m)})"),
        ("MGSM en français, réponses terminées", lambda m: _pourcent(m["terminee"])),
    ],
    "gsm8k_platinum_fr": [
        ("GSM8K-Platinum en français, exactitude", lambda m: f"{_pourcent(m['exactitude'])} ({_ex(m)})"),
        ("GSM8K-Platinum en français, réponses terminées", lambda m: _pourcent(m["terminee"])),
    ],
}


def _lire_date(date: str) -> str:
    return f"{date[8:10]}/{date[5:7]}/{date[:4]}"


def _tableau(rapport: dict) -> list[str]:
    """Le tableau des mesures chiffrées ; une colonne de plus s'il y a une référence. Rend aussi les raisons des absences."""
    versions = [rapport] + ([rapport["reference"]] if "reference" in rapport else [])
    entete = ["Mesure", *[f"`{v['version']}`" for v in versions]]
    lignes = [f"| {' | '.join(entete)} |", f"| {' | '.join('---' for _ in entete)} |"]
    raisons = []
    for nom in MESURES_PAR_ETAPE[rapport["etape"]]:
        for libelle, ecrire in _LIGNES.get(nom, []):
            cellules = []
            for v in versions:
                m = v["mesures"][nom]
                cellules.append("absente" if "absente" in m else ecrire(m))
            lignes.append(f"| {libelle} | {' | '.join(cellules)} |")
        for v in versions:
            if nom in _LIGNES and "absente" in v["mesures"][nom]:
                raisons.append(f"- **{nom}**, `{v['version']}`{_FINE}: mesure absente, {v['mesures'][nom]['absente']}")
    return [*lignes, "", *([*raisons, ""] if raisons else [])]


def _lignes_de_decoupage(titre: str, groupes: dict) -> list[str]:
    lignes = [
        f"**{titre}**",
        "",
        "| Groupe | Problèmes | Exactitude en glouton | Réussite en 8 essais |",
        "| --- | --- | --- | --- |",
    ]
    for nom, g in groupes.items():
        lignes.append(f"| {nom} | {_n(g['n'], 0)} | {_pourcent(g['exactitude'])} | {_pourcent(g['reussite_8'])} |")
    return [*lignes, ""]


def _bloc_d_echantillon(version: str, e: dict) -> list[str]:
    lignes = [f"Réponse de `{version}`{_FINE}:", ""]
    if e["pensee"]:
        lignes += [f"Pensée{_FINE}:", "", bloc_de_code(e["pensee"], "text"), ""]
    lignes += [bloc_de_code(e["texte"], "text"), ""]
    if not e["terminee"]:
        lignes += [f"Réponse coupée{_FINE}: la limite de {_n(JETONS_ECHANTILLONS, 0)} jetons est arrivée avant `<|fin_tour|>`.", ""]
    return lignes


def rapport_markdown(rapport: dict) -> str:
    """Le rapport d'une étape en Markdown, en français (voir `evaluer_etape` pour le contenu de `rapport`)."""
    appareil = "la carte graphique (bf16)" if rapport["appareil"] == "cuda" else "le processeur"
    lignes = [
        f"# Évaluation de {guillemets(rapport['version'])}, étape {rapport['etape']}",
        "",
        f"- **Version{_FINE}:** `{rapport['version']}`, poids d'empreinte SHA-256 `{rapport['empreinte']}`",
        f"- **Calcul{_FINE}:** sur {appareil}, en {_n(rapport['secondes'])}{_FINE}s, le {_lire_date(rapport['date'])}",
    ]
    if rapport.get("n_max") is not None:
        lignes.append(f"- **Essai court{_FINE}:** {_n(rapport['n_max'], 0)} exemples au plus par mesure.")
    if "reference" in rapport:
        r = rapport["reference"]
        lignes.append(f"- **Référence{_FINE}:** `{r['version']}` (SHA-256 `{r['empreinte']}`), mêmes mesures, en {_n(r['secondes'])}{_FINE}s")
    lignes += ["", "## Mesures", ""]
    lignes += _tableau(rapport)
    lignes += [
        f"Les réponses sont écrites en glouton (le jeton le plus probable à chaque pas), sauf les 8 essais des "
        f"problèmes (température 1, top-k 50). Une réponse coupée par la limite de jetons, ou vide, compte comme elle est{_FINE}: "
        "fausse pour un problème, jugée sur son texte pour une consigne.",
        "",
    ]
    problemes = rapport["mesures"].get("problemes")
    if problemes and "absente" not in problemes:
        lignes += [
            "## Problèmes générés, par famille et par difficulté",
            "",
            *_lignes_de_decoupage("Par famille", problemes["par_famille"]),
            *_lignes_de_decoupage("Par difficulté (nombre d'étapes de calcul)", problemes["par_difficulte"]),
        ]
    echantillons = rapport["mesures"].get("echantillons")
    if echantillons:
        lignes += [
            "## Échantillons",
            "",
            f"Dix invites toujours les mêmes, en glouton, {_n(JETONS_ECHANTILLONS, 0)} jetons au plus. "
            "Les réponses sont gardées telles quelles, sans tri.",
            "",
        ]
        for rang, e in enumerate(echantillons, start=1):
            lignes += [f"### {rang}. {guillemets(e['invite'])}", "", *_bloc_d_echantillon(rapport["version"], e)]
            if "reference" in rapport:
                autre = rapport["reference"]["mesures"]["echantillons"][rang - 1]
                lignes += _bloc_d_echantillon(rapport["reference"]["version"], autre)
    return "\n".join(lignes)


def resume_court(rapport: dict) -> str:
    """Les chiffres principaux, une ligne par mesure chiffrée, pour l'écran."""
    lignes = []
    for nom in MESURES_PAR_ETAPE[rapport["etape"]]:
        m = rapport["mesures"][nom]
        if nom not in _LIGNES:
            continue
        if "absente" in m:
            lignes.append(f"{nom}{_FINE}: absente ({m['absente']})")
            continue
        lignes += [f"{libelle}{_FINE}: {ecrire(m)}" for libelle, ecrire in _LIGNES[nom]]
    return "\n".join(lignes)
