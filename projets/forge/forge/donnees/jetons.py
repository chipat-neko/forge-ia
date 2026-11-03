"""Encodage du corpus en fragments de jetons (uint16), en parallèle et avec reprise.

L'entrée, ce sont les fragments `fragment-*.jsonl.gz` des dossiers de sources que le
téléchargement a finis (marqueur `.complet`). La sortie est rangée dans un dossier :

- `train/fragment-00000.bin` et `val/fragment-00000.bin` : les jetons de l'entraînement et
  de la validation, en `uint16` petit-boutiste. Chaque document est suivi de
  `<|fin_texte|>`. Un document va dans `val/` quand `est_validation(empreinte)` est vrai
  (0,5 % des documents, toujours les mêmes) ; un fichier qui n'aurait aucun jeton n'est pas
  écrit ;
- `fragment-00000.fait` : le marqueur du fragment, posé APRÈS ses fichiers de jetons ;
- `index.json` : le nombre de jetons de chaque fichier, et de quoi retrouver d'où il vient ;
- `.complet` : posé en dernier, quand tout est encodé.

Le fragment de sortie numéro `k` vient du `k`-ième fragment d'entrée, quand on range les
dossiers par nom puis les fragments par nom. Le travail se répartit fragment par fragment
entre les processus : chacun écrit ses propres fichiers.

Tout est atomique : chaque fichier s'écrit sous un nom en `.tmp`, est forcé sur le disque,
puis prend son vrai nom d'un coup (`os.replace`), et `verifier_place` passe avant chacun.
Une relance saute les fragments dont le marqueur correspond encore à l'entrée (même
fragment, même tokenizer) et dont les fichiers ont la bonne taille ; elle réencode les autres.
Le résultat ne dépend ni du nombre de processus ni de l'ordre d'arrivée : l'index est
assemblé dans l'ordre des numéros.
"""

import gzip
import hashlib
import json
import multiprocessing
import os
import signal
import sys
import time
import zlib
from array import array
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

import numpy as np

from forge.chemins import verifier_place
from forge.donnees.melange import est_validation
from forge.donnees.nettoyage import empreinte_du_texte_nettoye
from forge.donnees.telechargement import MARGE_PLACE, _ecrire_atomique, en_mo
from forge.tokenizer.apprentissage import DonneesManquantes
from forge.tokenizer.bpe_octets import TokenizerOctets

# Les jetons sont rangés sur 16 bits, petit-boutiste, quelle que soit la machine.
DTYPE_JETONS = np.dtype("<u2")

JETON_FIN_DE_TEXTE = "<|fin_texte|>"
VERSION_DE_L_INDEX = 1

# Nombres que contient un marqueur `.fait` (en plus de ce qui identifie l'entrée).
_NOMBRES_DU_MARQUEUR = (
    "documents_train",
    "documents_val",
    "jetons_train",
    "jetons_val",
    "jetons_sans_fin",
    "octets",
)


@dataclass(frozen=True)
class _Travail:
    """Un fragment d'entrée à encoder, et le numéro du fragment de sortie qui en sort."""

    numero: int
    source: Path  # le dossier de la source, par exemple `.../textes/essai/web_fr`
    fragment: Path

    @property
    def nom(self) -> str:
        """Nom du fragment de sortie, sans extension : `fragment-00007`."""
        return f"fragment-{self.numero:05d}"


# --- Lire ---------------------------------------------------------------------------


def lire_jetons(fichier: Path) -> np.memmap:
    """Ouvre un fichier `.bin` de jetons en lecture seule, sans le charger en mémoire."""
    fichier = Path(fichier)
    if not fichier.is_file():
        raise FileNotFoundError(
            f"Fichier de jetons introuvable : {fichier}. Encode d'abord les textes avec : "
            "python -m forge encoder --donnees <nom> --tokenizer <chemin>"
        )
    taille = fichier.stat().st_size
    if taille == 0 or taille % DTYPE_JETONS.itemsize:
        raise ValueError(
            f"Le fichier {fichier} ne contient pas de jetons entiers ({taille} octets, il en "
            f"faut un multiple de {DTYPE_JETONS.itemsize}). Il a pu être coupé : supprime-le, "
            "puis relance la commande d'encodage, qui le refera."
        )
    return np.memmap(fichier, dtype=DTYPE_JETONS, mode="r")


# --- Écrire -------------------------------------------------------------------------


def _ecrire(chemin: Path, octets: int, ecrire: Callable[[BinaryIO], None]) -> None:
    """Écrit `chemin` d'un coup, après avoir vérifié la place pour `octets` octets et 2 Go de marge."""
    verifier_place(octets + MARGE_PLACE, chemin.parent)
    _ecrire_atomique(chemin, ecrire)


def _ecrire_json(chemin: Path, contenu: dict) -> None:
    """Écrit un JSON (UTF-8, clés triées : le même contenu donne le même fichier)."""
    octets = (json.dumps(contenu, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    _ecrire(chemin, len(octets), lambda fichier: fichier.write(octets))


def _ecrire_jetons(chemin: Path, jetons: array) -> None:
    """Écrit les jetons en `uint16` petit-boutiste ; sans jeton, aucun fichier (et pas de reste)."""
    if len(jetons) == 0:
        chemin.unlink(missing_ok=True)  # un fichier d'un encodage précédent ne doit pas rester
        return
    donnees = np.frombuffer(jetons, dtype=np.uint16).astype(DTYPE_JETONS, copy=False)
    _ecrire(chemin, donnees.nbytes, donnees.tofile)


def _effacer_restes_tmp(sortie: Path) -> None:
    """Efface les `.tmp` qu'un plantage a laissés dans le dossier de sortie."""
    for dossier in (sortie, sortie / "train", sortie / "val"):
        for reste in dossier.glob("*.tmp"):
            reste.unlink(missing_ok=True)


# --- Un fragment --------------------------------------------------------------------


def _empreinte_du_tokenizer(tokenizer: TokenizerOctets) -> str:
    """SHA-1 de ce qui décide des jetons : la taille du vocabulaire et les fusions."""
    contenu = json.dumps(
        {"taille_vocabulaire": tokenizer.taille_vocabulaire, "fusions": tokenizer.fusions},
        separators=(",", ":"),
    )
    return hashlib.sha1(contenu.encode("utf-8"), usedforsecurity=False).hexdigest()


def _empreinte_du_fichier(chemin: Path) -> str:
    """SHA-1 d'un fichier : un fragment d'entrée refait donne une autre empreinte."""
    with open(chemin, "rb") as fichier:
        return hashlib.file_digest(fichier, lambda: hashlib.sha1(usedforsecurity=False)).hexdigest()


def _lire_marqueur(chemin: Path) -> dict | None:
    """Le marqueur `.fait`, ou `None` s'il manque ou n'est pas un JSON lisible."""
    try:
        contenu = json.loads(chemin.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return None
    return contenu if isinstance(contenu, dict) else None


def _marqueur_a_jour(fait: dict, identite: dict, sortie: Path, nom: str) -> bool:
    """Le marqueur dit-il que ce fragment est encodé pour CETTE entrée, fichiers compris ?"""
    if any(fait.get(cle) != valeur for cle, valeur in identite.items()):
        return False
    if not all(type(fait.get(cle)) is int and fait[cle] >= 0 for cle in _NOMBRES_DU_MARQUEUR):
        return False
    for sous_dossier, cle in (("train", "jetons_train"), ("val", "jetons_val")):
        chemin = sortie / sous_dossier / f"{nom}.bin"
        present = chemin.stat().st_size if chemin.exists() else 0
        if present != fait[cle] * DTYPE_JETONS.itemsize:
            return False
    return True


def _encoder_les_textes(tokenizer: TokenizerOctets, fin: int, fragment: Path) -> tuple[array, array, dict]:
    """Encode les documents d'un fragment ; renvoie (jetons train, jetons val, chiffres)."""
    train, val = array("H"), array("H")  # 'H' : 16 bits non signés, comme `DTYPE_JETONS`
    chiffres = dict.fromkeys(_NOMBRES_DU_MARQUEUR, 0)
    try:
        with gzip.open(fragment, "rt", encoding="utf-8") as fichier:
            for ligne in fichier:
                if not ligne.strip():
                    continue
                texte = json.loads(ligne)["texte"]
                jetons = tokenizer.encoder(texte)
                chiffres["octets"] += len(texte.encode("utf-8"))
                chiffres["jetons_sans_fin"] += len(jetons)
                # Les textes téléchargés sont déjà nettoyés : leur empreinte est celle du texte tel quel.
                if est_validation(empreinte_du_texte_nettoye(texte)):
                    cible, nombre = val, "documents_val"
                else:
                    cible, nombre = train, "documents_train"
                cible.extend(jetons)
                cible.append(fin)
                chiffres[nombre] += 1
    except (OSError, EOFError, zlib.error, ValueError, KeyError, TypeError) as erreur:
        source = fragment.parent
        raise ValueError(
            f"Le fragment {fragment} est illisible ({type(erreur).__name__} : {erreur}). "
            f"Supprime le dossier {source}, puis relance le téléchargement avec : "
            f"python -m forge donnees --octets <taille> --dossier {source.parent.name}"
        ) from erreur
    chiffres["jetons_train"] = len(train)
    chiffres["jetons_val"] = len(val)
    return train, val, chiffres


def _encoder_fragment(
    tokenizer: TokenizerOctets, empreinte_tokenizer: str, travail: _Travail, sortie: Path
) -> dict:
    """Encode un fragment, sauf si son marqueur dit que c'est déjà fait ; renvoie son marqueur.

    Le dictionnaire rendu contient en plus `numero`, `saute` (rien refait) et `secondes`.
    """
    debut = time.perf_counter()
    marqueur = sortie / f"{travail.nom}.fait"
    identite = {
        "dossier": travail.source.name,
        "fragment": travail.fragment.name,
        "empreinte_fragment": _empreinte_du_fichier(travail.fragment),
        "empreinte_tokenizer": empreinte_tokenizer,
    }
    fait = _lire_marqueur(marqueur)
    if fait is not None and _marqueur_a_jour(fait, identite, sortie, travail.nom):
        return {**fait, "numero": travail.numero, "saute": True, "secondes": time.perf_counter() - debut}

    # On défait le marqueur d'abord : un plantage entre deux fichiers ne doit jamais laisser
    # un ancien marqueur devant des fichiers à moitié refaits.
    marqueur.unlink(missing_ok=True)
    train, val, chiffres = _encoder_les_textes(tokenizer, tokenizer.id_special(JETON_FIN_DE_TEXTE), travail.fragment)
    _ecrire_jetons(sortie / "train" / f"{travail.nom}.bin", train)
    _ecrire_jetons(sortie / "val" / f"{travail.nom}.bin", val)
    fait = {**identite, **chiffres}
    _ecrire_json(marqueur, fait)  # en dernier : sa présence dit que les fichiers sont là
    return {**fait, "numero": travail.numero, "saute": False, "secondes": time.perf_counter() - debut}


# --- Les processus ------------------------------------------------------------------

_tokenizer_du_processus: TokenizerOctets | None = None


def _initialiser_processus(fusions: list, taille_vocabulaire: int, nom: str) -> None:
    """Prépare un processus du groupe : il reconstruit le tokenizer, une seule fois."""
    global _tokenizer_du_processus
    # Ctrl+C ne concerne que le processus principal : c'est lui qui arrête les autres.
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    _tokenizer_du_processus = TokenizerOctets(fusions, taille_vocabulaire, nom)


def _travailler(argument: tuple[_Travail, Path, str]) -> dict:
    """Ce que chaque processus du groupe exécute (au premier niveau du module, pour « spawn »)."""
    travail, sortie, empreinte_tokenizer = argument
    return _encoder_fragment(_tokenizer_du_processus, empreinte_tokenizer, travail, sortie)


# --- Le corpus ----------------------------------------------------------------------

# Sous Windows, un groupe de processus attend 63 objets au plus à la fois : on reste en dessous.
_MAX_PROCESSUS_WINDOWS = 60


def _processus_utiles(processus: int, nombre_de_fragments: int) -> int:
    """Combien de processus travaillent vraiment : jamais plus que de fragments à encoder."""
    utiles = min(processus, nombre_de_fragments)
    if sys.platform == "win32":
        utiles = min(utiles, _MAX_PROCESSUS_WINDOWS)
    return utiles


def _lister_les_travaux(dossiers: Sequence[Path]) -> list[_Travail]:
    """Les fragments d'entrée, numérotés : dossiers rangés par nom, puis fragments par nom."""
    sources = sorted((Path(dossier) for dossier in dossiers), key=str)
    if not sources:
        raise ValueError("Aucun dossier de textes à encoder : donne au moins une source.")
    if len({source.resolve() for source in sources}) != len(sources):
        raise ValueError(f"Le même dossier de textes est donné plusieurs fois : {[str(s) for s in sources]}.")
    travaux: list[_Travail] = []
    for source in sources:
        relancer = f"python -m forge donnees --octets <taille> --dossier {source.parent.name}"
        if not source.is_dir():
            raise DonneesManquantes(
                f"Le dossier de textes {source} est introuvable. Télécharge d'abord les textes avec : {relancer}"
            )
        if not (source / ".complet").exists():
            raise DonneesManquantes(
                f"Le téléchargement de « {source.name} » n'est pas terminé : pas de marqueur .complet "
                f"dans {source}. Relance : {relancer} (avec la même taille) ; il reprendra là où il "
                "s'est arrêté."
            )
        fragments = sorted(source.glob("fragment-*.jsonl.gz"))
        if not fragments:
            raise DonneesManquantes(
                f"Aucun fragment fragment-*.jsonl.gz dans {source}. Relance le téléchargement : {relancer}"
            )
        premier = len(travaux)  # pas dans la boucle ci-dessous : `extend` fait grandir la liste en route
        travaux.extend(_Travail(premier + rang, source, fragment) for rang, fragment in enumerate(fragments))
    return travaux


def _verifier_la_sortie(sortie: Path, empreinte_tokenizer: str, nombre_de_fragments: int) -> None:
    """Refuse un dossier de sortie qui vient d'un autre tokenizer ou d'une autre entrée.

    On ne réécrit pas en silence des heures d'encodage : l'utilisateur supprime le dossier
    de sortie, ou en choisit un autre, en connaissance de cause.
    """
    vider = f"Supprime le dossier {sortie} pour tout réencoder, ou choisis un autre dossier de sortie."
    for marqueur in sorted(sortie.glob("fragment-*.fait")):
        fait = _lire_marqueur(marqueur)
        if fait is not None and fait.get("empreinte_tokenizer") not in (None, empreinte_tokenizer):
            raise ValueError(
                f"Le dossier {sortie} contient déjà des jetons encodés avec un autre tokenizer "
                f"(marqueur {marqueur.name}). {vider}"
            )
    for motif in ("fragment-*.fait", "train/fragment-*.bin", "val/fragment-*.bin"):
        for fichier in sorted(sortie.glob(motif)):
            numero = fichier.name.removeprefix("fragment-").split(".")[0]
            if numero.isdigit() and int(numero) >= nombre_de_fragments:
                raise ValueError(
                    f"Le dossier {sortie} contient {fichier.name}, alors que les textes n'ont "
                    f"que {nombre_de_fragments} fragments : il vient d'autres textes. {vider}"
                )


def _encoder_tous_les_fragments(
    travaux: list[_Travail],
    tokenizer: TokenizerOctets,
    empreinte_tokenizer: str,
    sortie: Path,
    processus: int,
    rendre_compte: Callable[[dict], None],
) -> dict[int, dict]:
    """Encode tous les fragments ; renvoie le résultat de chacun, par numéro de fragment."""
    # Les plus gros d'abord : le dernier fragment de chaque source est souvent le plus petit,
    # et il ne doit pas faire attendre les autres à la fin.
    ordre = sorted(travaux, key=lambda travail: (-travail.fragment.stat().st_size, travail.numero))
    resultats: dict[int, dict] = {}
    utiles = _processus_utiles(processus, len(travaux))
    if utiles <= 1:
        for travail in ordre:
            resultat = _encoder_fragment(tokenizer, empreinte_tokenizer, travail, sortie)
            resultats[resultat["numero"]] = resultat
            rendre_compte(resultat)
        return resultats
    # « spawn » partout : comme sur Windows, un processus tout neuf par travailleur, qui
    # ne reçoit que ce qu'on lui passe.
    contexte = multiprocessing.get_context("spawn")
    arguments = [(travail, sortie, empreinte_tokenizer) for travail in ordre]
    initargs = (tokenizer.fusions, tokenizer.taille_vocabulaire, tokenizer.nom)
    # Sortir du `with` (erreur ou Ctrl+C) arrête tous les processus ; leurs fichiers sont
    # atomiques, et les `.tmp` qu'ils laissent sont effacés par l'appelant.
    with contexte.Pool(utiles, _initialiser_processus, initargs) as groupe:
        for resultat in groupe.imap_unordered(_travailler, arguments):
            resultats[resultat["numero"]] = resultat
            rendre_compte(resultat)
    return resultats


def _assembler_l_index(
    resultats: dict[int, dict], travaux: list[_Travail], tokenizer: TokenizerOctets, empreinte_tokenizer: str
) -> dict:
    """L'index, assemblé dans l'ordre des numéros de fragment (donc le même à chaque fois)."""
    fichiers: dict[str, int] = {}
    provenance: dict[str, str] = {}
    totaux = dict.fromkeys(_NOMBRES_DU_MARQUEUR, 0)
    for travail in sorted(travaux, key=lambda t: t.numero):
        fait = resultats[travail.numero]
        for sous_dossier in ("train", "val"):
            if fait[f"jetons_{sous_dossier}"]:
                fichiers[f"{sous_dossier}/{travail.nom}.bin"] = fait[f"jetons_{sous_dossier}"]
        provenance[travail.nom] = f"{travail.source.name}/{travail.fragment.name}"
        for cle in totaux:
            totaux[cle] += fait[cle]
    return {
        "version": VERSION_DE_L_INDEX,
        "tokenizer": {
            "nom": tokenizer.nom,
            "taille_vocabulaire": tokenizer.taille_vocabulaire,
            "empreinte": empreinte_tokenizer,
        },
        **totaux,
        "fichiers": fichiers,
        "provenance": provenance,
    }


def encoder_corpus(
    dossiers: list[Path],
    tokenizer: TokenizerOctets,
    sortie: Path,
    processus: int | None = None,
    journal: Callable[[str], None] | None = None,
) -> dict:
    """Encode les textes des `dossiers` en jetons, dans `sortie` ; renvoie un résumé.

    `dossiers` : les dossiers de sources (chacun avec ses `fragment-*.jsonl.gz` et son
    `.complet`). `processus` : combien de processus travaillent en même temps, un fragment
    chacun (`os.cpu_count()` par défaut ; 1 encode sans processus à part). `journal`, s'il
    est donné, reçoit une ligne par fragment.

    Le résumé : `jetons_train` et `jetons_val` (les `<|fin_texte|>` compris, comme dans les
    fichiers) et `octets_par_jeton` (octets UTF-8 des textes divisés par leurs jetons, sans
    les `<|fin_texte|>`).

    Après une coupure, on relance la même commande : les fragments déjà encodés sont sautés.
    `PlaceInsuffisante` ou toute autre erreur laisse le dossier utilisable tel quel : pas de
    `.tmp`, pas de `.complet`.
    """
    sortie = Path(sortie)
    ecrire = journal if journal is not None else (lambda _message: None)
    if processus is None:
        processus = os.cpu_count() or 1
    if processus < 1:
        raise ValueError(f"Le nombre de processus doit être au moins 1, pas {processus}.")
    travaux = _lister_les_travaux(dossiers)
    empreinte_tokenizer = _empreinte_du_tokenizer(tokenizer)
    tokenizer.id_special(JETON_FIN_DE_TEXTE)  # échoue tout de suite si ce vocabulaire n'a pas ce jeton

    for sous_dossier in ("train", "val"):
        (sortie / sous_dossier).mkdir(parents=True, exist_ok=True)
    _verifier_la_sortie(sortie, empreinte_tokenizer, len(travaux))
    _effacer_restes_tmp(sortie)
    # Dès qu'on relance, l'ancien « complet » ne vaut plus : il revient seulement à la fin.
    (sortie / ".complet").unlink(missing_ok=True)

    utiles = _processus_utiles(processus, len(travaux))
    ecrire(f"Encodage de {len(travaux)} fragments avec {utiles} processus, dans {sortie}.")
    debut = time.perf_counter()
    termines = 0

    def rendre_compte(resultat: dict) -> None:
        nonlocal termines
        termines += 1
        nom = f"fragment-{resultat['numero']:05d}"
        origine = f"{resultat['dossier']}/{resultat['fragment']}"
        if resultat["saute"]:
            ecrire(f"[{termines}/{len(travaux)}] {nom} ({origine}) : déjà encodé, sauté.")
        else:
            ecrire(
                f"[{termines}/{len(travaux)}] {nom} ({origine}) : {resultat['jetons_train'] + resultat['jetons_val']} "
                f"jetons, {en_mo(resultat['octets'])} Mo de texte en {resultat['secondes']:.0f} s."
            )

    try:
        resultats = _encoder_tous_les_fragments(
            travaux, tokenizer, empreinte_tokenizer, sortie, processus, rendre_compte
        )
        index = _assembler_l_index(resultats, travaux, tokenizer, empreinte_tokenizer)
        _ecrire_json(sortie / "index.json", index)
        jetons_hors_fin = index["jetons_sans_fin"]
        resume = {
            "jetons_train": index["jetons_train"],
            "jetons_val": index["jetons_val"],
            "octets_par_jeton": index["octets"] / jetons_hors_fin if jetons_hors_fin else 0.0,
        }
        _ecrire_json(sortie / ".complet", resume)
    except BaseException:
        _effacer_restes_tmp(sortie)  # ceux d'un processus arrêté en pleine écriture
        raise

    encodes = [r for r in resultats.values() if not r["saute"]]
    if encodes:
        secondes = max(time.perf_counter() - debut, 1e-9)
        octets = sum(r["octets"] for r in encodes)
        vitesse = f"{octets / 1024**2 / secondes:.2f}".replace(".", ",")
        ecrire(
            f"Terminé : {len(encodes)} fragments encodés, {en_mo(octets)} Mo de texte en {secondes:.0f} s, "
            f"soit {vitesse} Mo/s."
        )
    else:
        ecrire("Terminé : tous les fragments étaient déjà encodés.")
    return resume
