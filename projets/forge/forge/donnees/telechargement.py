"""Téléchargement des sources en flux, avec nettoyage, dédoublonnage et reprise.

Une source s'écrit dans un dossier (`FORGE_DONNEES/textes/<dossier>/<source>/`) :

- `fragment-00000.jsonl.gz`, `fragment-00001.jsonl.gz`… : environ 100 Mo de texte chacun,
  une ligne `{"texte": …}` par document nettoyé ;
- `etat.json` : où le téléchargement en est (`documents_lus`, `octets_ecrits`, et de quoi
  retrouver les fragments et les empreintes qui comptent) ;
- `empreintes.bin` : les empreintes des textes déjà écrits, pour ne jamais en réécrire un ;
- `.complet` : posé en dernier, quand le volume demandé est atteint ou la source épuisée.

Tout est atomique : chaque fichier s'écrit sous un nom en `.tmp`, est forcé sur le disque,
puis prend son vrai nom d'un coup (`os.replace`). L'état n'est mis à jour qu'APRÈS le
fragment qu'il compte : un arrêt entre les deux (coupure de courant, réseau, disque plein)
fait relire les documents du fragment non compté, sans perte et sans doublon, car le
fragment orphelin est effacé à la relance et les empreintes de l'état sont les seules
prises en compte.
"""

import gzip
import json
import os
from array import array
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass
from itertools import islice
from pathlib import Path
from typing import BinaryIO

from forge.chemins import racine_donnees, verifier_place
from forge.donnees.nettoyage import empreinte_du_texte_nettoye, nettoyer
from forge.donnees.sources import Source

# Taille visée d'un fragment : environ 100 Mo de texte (un Mo vaut 1024² octets ici).
TAILLE_FRAGMENT = 100 * 1024**2

# Place à garder libre sur le disque, en plus de celle du fragment à écrire : 2 Go.
MARGE_PLACE = 2 * 1024**3

_OCTETS_PAR_EMPREINTE = 8  # on garde 64 bits du SHA-1 : assez pour des millions de documents


def en_mo(octets: int) -> str:
    """Écrit une taille en Mo (1024² octets) avec une décimale et la virgule française."""
    return f"{octets / 1024**2:.1f}".replace(".", ",")


def dossier_des_textes(dossier: Path) -> Path:
    """`FORGE_DONNEES/textes/<dossier>` (un chemin absolu est gardé tel quel).

    C'est le dossier que le téléchargement remplit et que le tokenizer lit : une seule
    définition pour les deux.
    """
    return racine_donnees() / "textes" / dossier


@dataclass
class _Etat:
    """Ce que `etat.json` retient. Seul ce qui est déjà écrit sur le disque y est compté."""

    documents_lus: int = 0  # documents lus dans la source, jusqu'au dernier fragment écrit
    octets_ecrits: int = 0  # octets UTF-8 des textes des fragments écrits
    fragments: int = 0  # nombre de fragments écrits : les suivants sont des orphelins
    empreintes: int = 0  # nombre d'empreintes valides dans `empreintes.bin`
    source_epuisee: bool = False  # la source n'avait plus rien à donner


def lecteur_hugging_face(source: Source, ignorer: int = 0) -> Iterator[dict]:
    """Lit une source en flux depuis Hugging Face, sans rien télécharger d'entier.

    `ignorer` documents du début sont sautés (pour la reprise) : le flux est relu depuis
    le début du jeu, dont l'ordre ne change pas d'une lecture à l'autre.
    """
    from datasets import load_dataset  # lourd : importé seulement quand on lit pour de bon

    if source.configuration is not None:
        jeu = load_dataset(source.depot, source.configuration, split="train", streaming=True)
    elif source.dossier_donnees is not None:
        # Les fichiers parquet du dossier, lus directement : le français du web demande sinon
        # une configuration, et le dépôt du code a un script de chargement que les versions
        # récentes de `datasets` refusent d'exécuter.
        jeu = load_dataset(
            "parquet",
            data_files=f"hf://datasets/{source.depot}/{source.dossier_donnees}/*.parquet",
            split="train",
            streaming=True,
        )
    else:
        jeu = load_dataset(source.depot, split="train", streaming=True)
    if ignorer:
        jeu = jeu.skip(ignorer)
    yield from jeu


def _ecrire_atomique(chemin: Path, ecrire: Callable[[BinaryIO], None]) -> None:
    """Écrit `chemin` d'un coup : un `.tmp`, forcé sur le disque, puis `os.replace`.

    Si quoi que ce soit échoue, le `.tmp` est effacé et `chemin` reste tel qu'il était.
    """
    temporaire = chemin.with_name(chemin.name + ".tmp")
    try:
        with open(temporaire, "wb") as fichier:
            ecrire(fichier)
            fichier.flush()
            os.fsync(fichier.fileno())
        os.replace(temporaire, chemin)
    except BaseException:
        temporaire.unlink(missing_ok=True)
        raise


def _ecrire_fragment(dossier: Path, numero: int, textes: list[str]) -> None:
    """Écrit le fragment `numero` : une ligne `{"texte": …}` par texte, compressée en gzip."""
    def ecrire(fichier: BinaryIO) -> None:
        # mtime=0 : le même contenu donne le même fichier, quel que soit le jour.
        with gzip.GzipFile(fileobj=fichier, mode="wb", compresslevel=6, mtime=0) as compresse:
            for texte in textes:
                ligne = json.dumps({"texte": texte}, ensure_ascii=False) + "\n"
                compresse.write(ligne.encode("utf-8"))

    _ecrire_atomique(dossier / f"fragment-{numero:05d}.jsonl.gz", ecrire)


def _ecrire_etat(dossier: Path, etat: _Etat) -> None:
    """Écrit `etat.json` (atomique) : à appeler seulement après le fragment qu'il compte."""
    contenu = json.dumps(asdict(etat), indent=2).encode("utf-8")
    _ecrire_atomique(dossier / "etat.json", lambda fichier: fichier.write(contenu))


def _lire_etat(dossier: Path) -> _Etat | None:
    """L'état enregistré, ou `None` si le téléchargement n'a encore rien validé."""
    chemin = dossier / "etat.json"
    if not chemin.exists():
        return None
    try:
        return _Etat(**json.loads(chemin.read_text(encoding="utf-8")))
    except (ValueError, TypeError) as erreur:
        raise RuntimeError(
            f"Le fichier {chemin} est illisible ({erreur}). Supprime le dossier {dossier} "
            "pour recommencer cette source de zéro, puis relance la même commande."
        ) from erreur


def _cle(texte_nettoye: str) -> int:
    """Les 64 premiers bits de l'empreinte SHA-1 d'un texte nettoyé : la clé du dédoublonnage."""
    return int(empreinte_du_texte_nettoye(texte_nettoye)[: 2 * _OCTETS_PAR_EMPREINTE], 16)


def _charger_empreintes(dossier: Path, etat: _Etat) -> set[int]:
    """Les empreintes comptées par l'état ; celles écrites au-delà (plantage) sont ignorées."""
    if etat.empreintes == 0:
        return set()
    attendu = etat.empreintes * _OCTETS_PAR_EMPREINTE
    chemin = dossier / "empreintes.bin"
    donnees = chemin.read_bytes()[:attendu] if chemin.exists() else b""
    if len(donnees) < attendu:
        raise RuntimeError(
            f"Le fichier des empreintes {chemin} est incomplet ({len(donnees)} octets au lieu "
            f"de {attendu}). Supprime le dossier {dossier} pour recommencer cette source de "
            "zéro, puis relance la même commande."
        )
    cles = array("Q")  # ordre des octets de la machine : ce fichier ne voyage pas
    cles.frombytes(donnees)
    return set(cles)


def _ajouter_empreintes(dossier: Path, deja: int, nouvelles: list[int]) -> None:
    """Ajoute des empreintes après les `deja` comptées, en coupant tout reste d'un plantage."""
    chemin = dossier / "empreintes.bin"
    with open(chemin, "r+b" if chemin.exists() else "wb") as fichier:
        fichier.seek(deja * _OCTETS_PAR_EMPREINTE)
        fichier.truncate()
        fichier.write(array("Q", nouvelles).tobytes())
        fichier.flush()
        os.fsync(fichier.fileno())


def _effacer_restes(dossier: Path, etat: _Etat) -> None:
    """Efface les `.tmp` d'un plantage et les fragments orphelins (écrits, mais pas comptés)."""
    for reste in dossier.glob("*.tmp"):
        reste.unlink()
    for fragment in dossier.glob("fragment-*.jsonl.gz"):
        numero = fragment.name.removeprefix("fragment-").removesuffix(".jsonl.gz")
        if numero.isdigit() and int(numero) >= etat.fragments:
            fragment.unlink()


def _poser_marqueur(dossier: Path, etat: _Etat) -> None:
    """Pose `.complet` en dernier : sa présence dit que rien ne manque."""
    contenu = json.dumps(asdict(etat), indent=2).encode("utf-8")
    _ecrire_atomique(dossier / ".complet", lambda fichier: fichier.write(contenu))


def _texte_a_garder(source: Source, ligne: dict) -> str | None:
    """Le texte nettoyé d'une ligne, ou `None` si la source l'écarte ou s'il est trop court."""
    if not source.garder(ligne):
        return None
    brut = ligne.get(source.colonne)
    if not isinstance(brut, str):
        return None
    return nettoyer(brut)


def telecharger(
    source: Source,
    octets_max: int,
    dossier: Path,
    lecteur: Callable[[Source], Iterator[dict]] | None = None,
    *,
    octets_fragment: int = TAILLE_FRAGMENT,
    journal: Callable[[str], None] | None = None,
) -> Path:
    """Lit `source` en flux et écrit ses textes nettoyés dans `dossier` ; renvoie `dossier`.

    On s'arrête quand `octets_max` octets de texte sont écrits (le dernier document peut
    dépasser un peu) ou quand la source est épuisée, et `.complet` est alors posé. Sans
    lecteur, la source est lue depuis Hugging Face. Un lecteur donné reçoit la source et
    renvoie ses documents (des dictionnaires colonne → valeur) toujours dans le même ordre.

    Après une coupure, on relance la même commande : les documents déjà comptés dans
    `etat.json` sont sautés, les empreintes déjà vues ne sont pas réécrites, et
    `PlaceInsuffisante` ou toute autre erreur laisse le dossier utilisable tel quel.
    Relancer avec un `octets_max` plus grand prolonge un dossier déjà complet.
    """
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    ecrire = journal if journal is not None else (lambda _message: None)
    marqueur = dossier / ".complet"
    etat = _lire_etat(dossier)

    if marqueur.exists():
        if etat is None or etat.source_epuisee or etat.octets_ecrits >= octets_max:
            ecrire(f"{source.nom} : déjà complet.")
            return dossier
        marqueur.unlink()  # on demande plus que ce qui est écrit : on reprend où on s'était arrêté
    etat = etat if etat is not None else _Etat()
    _effacer_restes(dossier, etat)
    if etat.source_epuisee or etat.octets_ecrits >= octets_max:
        _poser_marqueur(dossier, etat)  # arrêt entre le dernier état et le marqueur
        ecrire(f"{source.nom} : déjà complet.")
        return dossier

    vues = _charger_empreintes(dossier, etat)
    if lecteur is None:
        flux = documents = lecteur_hugging_face(source, ignorer=etat.documents_lus)
    else:
        flux = lecteur(source)
        documents = islice(flux, etat.documents_lus, None)
    if etat.documents_lus:
        ecrire(f"{source.nom} : reprise après {etat.documents_lus} documents lus.")

    tampon: list[str] = []
    cles: list[int] = []
    octets_tampon = 0
    lus = 0  # documents lus depuis le dernier fragment écrit

    def valider(epuisee: bool) -> None:
        """Écrit le fragment du tampon, puis les empreintes, puis l'état (dans cet ordre)."""
        nonlocal etat, tampon, cles, octets_tampon, lus
        fragments = etat.fragments
        if tampon:
            verifier_place(octets_tampon + MARGE_PLACE, dossier)
            _ecrire_fragment(dossier, etat.fragments, tampon)
            _ajouter_empreintes(dossier, etat.empreintes, cles)
            fragments += 1
        nouvel_etat = _Etat(
            documents_lus=etat.documents_lus + lus,
            octets_ecrits=etat.octets_ecrits + octets_tampon,
            fragments=fragments,
            empreintes=etat.empreintes + len(cles),
            source_epuisee=epuisee,
        )
        _ecrire_etat(dossier, nouvel_etat)
        if tampon:
            ecrire(
                f"{source.nom} : fragment {fragments - 1} écrit, "
                f"{en_mo(nouvel_etat.octets_ecrits)} Mo de texte en tout, "
                f"{nouvel_etat.documents_lus} documents lus."
            )
        etat = nouvel_etat
        tampon, cles, octets_tampon, lus = [], [], 0, 0

    def verifier_avant_lecture() -> None:
        """Échoue tôt s'il manque déjà de la place, avant de lire un fragment pour rien."""
        octets_restants = octets_max - etat.octets_ecrits
        verifier_place(min(octets_fragment, octets_restants) + MARGE_PLACE, dossier)

    verifier_avant_lecture()
    epuisee = True
    try:
        for ligne in documents:
            lus += 1
            texte = _texte_a_garder(source, ligne)
            if texte is not None:
                cle = _cle(texte)
                if cle not in vues:
                    vues.add(cle)
                    tampon.append(texte)
                    cles.append(cle)
                    octets_tampon += len(texte.encode("utf-8"))
            if etat.octets_ecrits + octets_tampon >= octets_max:
                epuisee = False
                break
            if octets_tampon >= octets_fragment:
                valider(epuisee=False)
                verifier_avant_lecture()
    finally:
        # Ferme le flux de la source (connexions ouvertes) : arrêt voulu ou erreur.
        fermer = getattr(flux, "close", None)
        if callable(fermer):
            fermer()
    valider(epuisee=epuisee)
    _poser_marqueur(dossier, etat)
    ecrire(
        f"{source.nom} : terminé, {en_mo(etat.octets_ecrits)} Mo de texte, "
        f"{etat.fragments} fragments, {etat.documents_lus} documents lus"
        + (" (source épuisée)." if etat.source_epuisee else ".")
    )
    return dossier
