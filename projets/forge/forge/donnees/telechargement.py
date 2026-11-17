"""Téléchargement des sources en flux, avec nettoyage, dédoublonnage et reprise.

Une source s'écrit dans un dossier (`FORGE_DONNEES/textes/<dossier>/<source>/`) :

- `fragment-00000.jsonl.gz`, `fragment-00001.jsonl.gz`… : environ 100 Mo de texte chacun,
  une ligne `{"texte": …}` par document nettoyé ;
- `etat.json` : où le téléchargement en est (`documents_lus`, `octets_ecrits`, et de quoi
  retrouver les fragments et les empreintes qui comptent), plus `etat_du_flux`, le
  `state_dict()` du flux `datasets` pris juste après le dernier document du dernier fragment
  écrit : la reprise repart de ce fichier et de ce groupe de lignes, sans relire le début
  (`sautes_a_l_ouverture` dit quel saut refaire avant de recharger cet état) ;
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

from forge.chemins import sous_forge_donnees, verifier_place
from forge.donnees.nettoyage import empreinte_du_texte_nettoye, nettoyer
from forge.donnees.sources import Source
from forge.erreurs import DonneesManquantes
from forge.fichiers import ecrire_atomique, entier, nombre

# Taille visée d'un fragment : environ 100 Mo de texte (un Mo vaut 1024² octets ici).
TAILLE_FRAGMENT = 100 * 1024**2

# Place à garder libre sur le disque, en plus de celle du fragment à écrire : 2 Go.
MARGE_PLACE = 2 * 1024**3

_OCTETS_PAR_EMPREINTE = 8  # on garde 64 bits du SHA-1 : assez pour des millions de documents


def en_mo(octets: int) -> str:
    """Écrit une taille en Mo (1024² octets) avec une décimale et la virgule française."""
    return nombre(octets / 1024**2, 1)


def dossier_des_textes(dossier: Path) -> Path:
    """`FORGE_DONNEES/textes/<dossier>` (un chemin absolu est gardé tel quel).

    C'est le dossier que le téléchargement remplit et que le tokenizer lit : une seule
    définition pour les deux.
    """
    return sous_forge_donnees(dossier, "textes")


@dataclass
class _Etat:
    """Ce que `etat.json` retient. Seul ce qui est déjà écrit sur le disque y est compté."""

    documents_lus: int = 0  # documents lus dans la source, jusqu'au dernier fragment écrit
    octets_ecrits: int = 0  # octets UTF-8 des textes des fragments écrits
    fragments: int = 0  # nombre de fragments écrits : les suivants sont des orphelins
    empreintes: int = 0  # nombre d'empreintes valides dans `empreintes.bin`
    source_epuisee: bool = False  # la source n'avait plus rien à donner
    # `state_dict()` du flux après le dernier document compté (`None` : état d'avant cette
    # version, ou jeu qui ne sait pas reprendre ; la reprise relit alors le flux depuis le début).
    etat_du_flux: dict | None = None
    # Documents sautés (`jeu.skip`) à l'ouverture du flux dont `etat_du_flux` est l'état : non nul
    # après la reprise d'un état d'avant cette version. Cet état ne se recharge que sur un jeu
    # sauté du même nombre, sans quoi `datasets` le refuse.
    sautes_a_l_ouverture: int = 0


# Ce que `datasets` lève quand l'état qu'on lui rend ne va pas avec le jeu (clé absente, indice
# hors du jeu…) : jamais une erreur de réseau ou de disque, qui sont des `OSError`.
_ERREURS_D_ETAT = (KeyError, IndexError, ValueError, TypeError, AttributeError)


class EtatDuFluxRefuse(RuntimeError):
    """Le jeu refuse l'état du flux d'`etat.json` : relancer la même commande ne change rien."""


class LecteurDeFlux:
    """Les documents d'un jeu `datasets` en flux, et de quoi savoir où l'on en est.

    `etat()` renvoie le `state_dict()` du jeu (la position après le dernier document donné),
    ou `None` si le jeu ne le permet pas. `refus`, s'il est donné, transforme une erreur
    d'état de `datasets` à la première lecture en une erreur claire : `load_state_dict` ne
    vérifie presque rien, c'est la lecture qui échoue si l'état ne va pas avec le jeu.
    """

    def __init__(self, jeu, refus: Callable[[Exception], Exception] | None = None) -> None:
        self._jeu = jeu
        self._refus = refus
        self._iterateur = None

    def __iter__(self) -> Iterator[dict]:
        if self._iterateur is None:
            self._iterateur = self._lire()
        return self._iterateur

    def _lire(self) -> Iterator[dict]:
        flux = iter(self._jeu)
        try:
            premier = next(flux)
        except StopIteration:
            return
        except _ERREURS_D_ETAT as erreur:
            import pyarrow  # déjà chargé par `datasets` : pas de coût en plus

            # Un fichier Parquet abîmé (`ArrowInvalid` est une `ValueError`) n'est pas un état refusé.
            if self._refus is None or isinstance(erreur, pyarrow.ArrowException):
                raise
            raise self._refus(erreur) from erreur
        yield premier
        yield from flux

    def etat(self) -> dict | None:
        try:
            return self._jeu.state_dict()
        except Exception:  # noqa: BLE001 - jeu sans état (pas un IterableDataset, version ancienne)
            return None

    def close(self) -> None:
        fermer = getattr(self._iterateur, "close", None)
        if callable(fermer):
            fermer()


def lecteur_hugging_face(
    source: Source, etat_du_flux: dict | None = None, ignorer: int = 0
) -> LecteurDeFlux:
    """Lit une source en flux depuis Hugging Face, sans rien télécharger d'entier.

    `ignorer` documents du début sont sautés (`jeu.skip`) : le flux est relu depuis le début du
    jeu, dont l'ordre ne change pas d'une lecture à l'autre (l'ancienne voie de reprise).

    Avec `etat_du_flux` (le `state_dict()` pris à l'arrêt précédent), la lecture repart du
    fichier et du groupe de lignes où le flux s'était arrêté, sans rien relire. `ignorer` doit
    alors valoir ce qu'il valait à l'ouverture où cet état a été pris : l'état d'un jeu sauté
    garde la trace du saut, et ne se recharge que sur un jeu sauté de même (le saut, déjà fait
    d'après l'état, ne relit rien).
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
    if etat_du_flux is None:
        return LecteurDeFlux(jeu)

    def refus(erreur: Exception) -> EtatDuFluxRefuse:
        return EtatDuFluxRefuse(
            f"{source.nom} : le jeu refuse l'état du flux enregistré dans etat.json "
            f"({type(erreur).__name__} : {erreur}). La source ou la version de `datasets` a "
            "sans doute changé. Relancer la même commande échouera de nouveau. Pour garder les "
            "fragments déjà écrits, retire la ligne `etat_du_flux` d'etat.json : le flux sera "
            "relu depuis le début, à l'ancienne. Pour repartir de zéro, efface le dossier de "
            "la source."
        )

    try:
        jeu.load_state_dict(etat_du_flux)
    except _ERREURS_D_ETAT as erreur:
        raise refus(erreur) from erreur
    return LecteurDeFlux(jeu, refus)


def _nom_du_fragment(numero: int) -> str:
    return f"fragment-{numero:05d}.jsonl.gz"


def _ecrire_fragment(dossier: Path, numero: int, textes: list[str]) -> None:
    """Écrit le fragment `numero` : une ligne `{"texte": …}` par texte, compressée en gzip."""
    def ecrire(fichier: BinaryIO) -> None:
        # mtime=0 : le même contenu donne le même fichier, quel que soit le jour.
        with gzip.GzipFile(fileobj=fichier, mode="wb", compresslevel=6, mtime=0) as compresse:
            for texte in textes:
                ligne = json.dumps({"texte": texte}, ensure_ascii=False) + "\n"
                compresse.write(ligne.encode("utf-8"))

    ecrire_atomique(dossier / _nom_du_fragment(numero), ecrire)


def _ecrire_etat(dossier: Path, etat: _Etat) -> None:
    """Écrit `etat.json` (atomique) : à appeler seulement après le fragment qu'il compte."""
    contenu = json.dumps(asdict(etat), indent=2).encode("utf-8")
    ecrire_atomique(dossier / "etat.json", lambda fichier: fichier.write(contenu))


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


def reparer_un_fragment_manquant(dossier: Path) -> str:
    """Que faire quand un fragment déjà compté de la source `dossier` manque, et ce que ça coûte.

    `telecharger` ne refait jamais un fragment compté : sa reprise repart après le dernier
    document compté, et le flux ne sait pas revenir en arrière. Hors de la corbeille, la seule
    réparation honnête est donc de retélécharger toute la source.
    """
    try:
        etat = _lire_etat(dossier)
    except RuntimeError:
        etat = None  # etat.json illisible : la réparation est la même, seul le coût manque
    cout = ""
    if etat is not None:
        mo = nombre(etat.octets_ecrits / 1024**2, 1, milliers=" ")
        cout = f" ({entier(etat.documents_lus)} documents, {mo} Mo de texte)"
    nom = dossier.parent.name
    return (
        "python -m forge donnees ne refait jamais un fragment déjà compté : sa reprise repart après le "
        "dernier document compté. Si le fichier est dans la corbeille ou en quarantaine (antivirus), "
        "remets-le à sa place, puis relance la même commande. Sinon, la seule réparation est de "
        f"retélécharger cette source : efface le dossier {dossier}, relance python -m forge donnees "
        f"--octets <taille> --dossier {nom}, qui relit toute la source{cout}, puis python -m forge "
        f"encoder --donnees {nom} --tokenizer <chemin>."
    )


def verifier_les_fragments_comptes(dossier: Path) -> None:
    """Lève `DonneesManquantes` si un fragment que compte `etat.json` n'est plus sur le disque.

    Sans `etat.json`, rien n'est compté, donc rien à vérifier.
    """
    try:
        etat = _lire_etat(dossier)
    except RuntimeError as erreur:
        nom = dossier.parent.name
        raise DonneesManquantes(
            f"Le fichier {dossier / 'etat.json'} est illisible ({erreur.__cause__}) : impossible de "
            f"vérifier que les fragments qu'il compte sont tous là. Efface le dossier {dossier}, relance "
            f"python -m forge donnees --octets <taille> --dossier {nom}, puis python -m forge encoder "
            f"--donnees {nom} --tokenizer <chemin>."
        ) from erreur
    if etat is not None:
        _verifier_les_fragments(dossier, etat)


def _verifier_les_fragments(dossier: Path, etat: _Etat) -> None:
    manquants = [nom for nom in map(_nom_du_fragment, range(etat.fragments)) if not (dossier / nom).is_file()]
    if not manquants:
        return
    if len(manquants) == 1:
        sujet = f"Le fragment {manquants[0]} manque"
    else:
        liste = ", ".join(manquants[:5]) + (", …" if len(manquants) > 5 else "")
        sujet = f"{len(manquants)} fragments manquent ({liste})"
    raise DonneesManquantes(
        f"{sujet} dans {dossier}, alors qu'etat.json compte {etat.fragments} fragments écrits. "
        + reparer_un_fragment_manquant(dossier)
    )


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
    ecrire_atomique(dossier / ".complet", lambda fichier: fichier.write(contenu))


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
    Relancer avec un `octets_max` plus grand prolonge un dossier déjà complet. Un fragment
    compté qui manque lève `DonneesManquantes` avant toute lecture : il ne serait jamais refait.
    """
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    ecrire = journal if journal is not None else (lambda _message: None)
    marqueur = dossier / ".complet"
    etat = _lire_etat(dossier)
    if etat is not None:
        _verifier_les_fragments(dossier, etat)  # un trou ne se comble jamais : ni « complet », ni reprise

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
        # Sans état du flux, on saute les documents comptés ; avec, on refait le même saut qu'à
        # l'ouverture où il a été pris (zéro, sauf après la reprise d'un ancien état).
        sautes = etat.documents_lus if etat.etat_du_flux is None else etat.sautes_a_l_ouverture
        flux = documents = lecteur_hugging_face(source, etat_du_flux=etat.etat_du_flux, ignorer=sautes)
    else:
        sautes = 0
        flux = lecteur(source)
        documents = islice(flux, etat.documents_lus, None)
    if etat.documents_lus:
        if lecteur is not None or etat.etat_du_flux is not None:
            ecrire(f"{source.nom} : reprise après {etat.documents_lus} documents lus.")
        else:
            ecrire(
                f"{source.nom} : reprise après {etat.documents_lus} documents lus, "
                "ancien état : le flux est relu depuis le début."
            )

    def etat_du_flux_courant() -> dict | None:
        """La position du flux, si le lecteur sait la dire."""
        donner = getattr(flux, "etat", None)
        return donner() if callable(donner) else None

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
        etat_du_flux = etat_du_flux_courant()
        nouvel_etat = _Etat(
            documents_lus=etat.documents_lus + lus,
            octets_ecrits=etat.octets_ecrits + octets_tampon,
            fragments=fragments,
            empreintes=etat.empreintes + len(cles),
            source_epuisee=epuisee,
            etat_du_flux=etat_du_flux,
            sautes_a_l_ouverture=sautes if etat_du_flux is not None else 0,
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
        # Le dernier fragment se valide flux ouvert : son état est pris après le dernier document.
        valider(epuisee=epuisee)
    finally:
        # Ferme le flux de la source (connexions ouvertes) : arrêt voulu ou erreur.
        fermer = getattr(flux, "close", None)
        if callable(fermer):
            fermer()
    _poser_marqueur(dossier, etat)
    ecrire(
        f"{source.nom} : terminé, {en_mo(etat.octets_ecrits)} Mo de texte, "
        f"{etat.fragments} fragments, {etat.documents_lus} documents lus"
        + (" (source épuisée)." if etat.source_epuisee else ".")
    )
    return dossier
