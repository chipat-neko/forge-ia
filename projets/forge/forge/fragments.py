"""Des sorties par fragments, atomiques et reprises, pour tous les travaux longs qui écrivent des éléments.

Un travail (téléchargement des conversations, traduction, génération de paires…) écrit des éléments
(des dictionnaires JSON) dans un dossier :

- `<prefixe>-00000.jsonl.gz`, `<prefixe>-00001.jsonl.gz`… : un élément par ligne, en gzip ;
- `etat.json` : combien d'éléments et de fragments sont validés, plus l'`etat` que l'appelant a
  joint au dernier fragment (la position de son flux, ses comptes…) : la reprise repart de là ;
- `.complet` : posé en dernier par `terminer`, avec des infos de l'appelant. Sans lui, le travail
  n'est jamais tenu pour terminé.

Tout est atomique : chaque fichier s'écrit sous un nom en `.tmp`, est forcé sur le disque, puis prend
son vrai nom d'un coup. `etat.json` n'est écrit qu'APRÈS le fragment qu'il compte : un arrêt entre les
deux laisse un fragment orphelin, effacé à l'ouverture suivante avec les `.tmp` restés. Un élément n'est
donc compté qu'une fois, et un fragment déjà compté n'est jamais refait.

Les mêmes éléments donnent les mêmes fichiers, octet pour octet (gzip sans date) : deux téléchargements
d'une même source, l'un d'une traite et l'autre repris après une coupure, se comparent fichier à fichier.
"""

import gzip
import json
from collections.abc import Iterator
from pathlib import Path
from typing import BinaryIO

from forge.erreurs import DonneesManquantes
from forge.fichiers import ecrire_atomique

NOM_DE_L_ETAT = "etat.json"
NOM_DU_MARQUEUR = ".complet"


def _nom_du_fragment(prefixe: str, numero: int) -> str:
    return f"{prefixe}-{numero:05d}.jsonl.gz"


def _numero_du_fragment(prefixe: str, nom: str) -> int | None:
    """Le numéro d'un fichier `<prefixe>-NNNNN.jsonl.gz`, ou `None` si ce n'en est pas un."""
    debut, fin = f"{prefixe}-", ".jsonl.gz"
    if not (nom.startswith(debut) and nom.endswith(fin)):
        return None
    numero = nom[len(debut):-len(fin)]
    return int(numero) if numero.isdigit() else None


def _ecrire_json(chemin: Path, contenu: dict) -> None:
    octets = json.dumps(contenu, indent=2, ensure_ascii=False).encode("utf-8")
    ecrire_atomique(chemin, lambda fichier: fichier.write(octets))


def _lire_etat(dossier: Path) -> dict | None:
    chemin = dossier / NOM_DE_L_ETAT
    if not chemin.exists():
        return None
    try:
        etat = json.loads(chemin.read_text(encoding="utf-8"))
        if not isinstance(etat, dict) or not isinstance(etat["elements"], int) or not isinstance(etat["fragments"], int):
            raise ValueError("ce n'est pas l'état d'une sortie par fragments")
        return etat
    except (ValueError, KeyError) as erreur:
        raise RuntimeError(
            f"Le fichier {chemin} est illisible ({erreur}). Supprime le dossier {dossier} "
            "pour recommencer ce travail de zéro, puis relance la même commande."
        ) from erreur


def _verifier_les_fragments(dossier: Path, prefixe: str, comptes: int) -> None:
    manquants = [
        nom for nom in map(lambda n: _nom_du_fragment(prefixe, n), range(comptes)) if not (dossier / nom).is_file()
    ]
    if manquants:
        liste = ", ".join(manquants[:5]) + (", …" if len(manquants) > 5 else "")
        raise DonneesManquantes(
            f"{len(manquants)} fragment(s) manque(nt) dans {dossier} ({liste}), alors que {NOM_DE_L_ETAT} "
            f"en compte {comptes}. Un fragment déjà compté n'est jamais refait : remets le fichier à sa "
            f"place (corbeille, quarantaine de l'antivirus), ou efface le dossier {dossier} et relance la "
            "même commande pour tout refaire."
        )


class SortieParFragments:
    """Écrit des éléments par fragments de `par_fragment` éléments, et sait reprendre après une coupure.

    Usage typique : `ajouter` chaque élément, et dès que `plein`, `valider(etat)` avec ce qu'il faut pour
    reprendre ; à la fin, `terminer(infos)`. Un élément `ajouter`é mais pas encore `valider`é n'est pas
    sur le disque : c'est l'appelant qui décide où couper (par exemple entre deux lignes d'une source,
    pour que l'`etat` qu'il joint soit celui d'après la dernière ligne comptée).
    """

    def __init__(self, dossier: Path, prefixe: str, par_fragment: int = 50_000) -> None:
        if par_fragment < 1:
            raise ValueError(f"par_fragment doit être au moins 1, pas {par_fragment}.")
        self.dossier = Path(dossier)
        self.prefixe = prefixe
        self.par_fragment = par_fragment
        self.dossier.mkdir(parents=True, exist_ok=True)
        etat = _lire_etat(self.dossier)
        self._fragments = etat["fragments"] if etat else 0
        self.deja: int = etat["elements"] if etat else 0  # éléments déjà validés
        self.etat: dict | None = etat.get("etat") if etat else None  # ce que l'appelant a joint au dernier fragment
        _verifier_les_fragments(self.dossier, prefixe, self._fragments)
        self._effacer_les_restes()
        self.infos: dict | None = None
        marqueur = self.dossier / NOM_DU_MARQUEUR
        if marqueur.exists():
            self.infos = json.loads(marqueur.read_text(encoding="utf-8"))
        self._tampon: list[bytes] = []
        self._octets = 0

    def _effacer_les_restes(self) -> None:
        """Efface les `.tmp` d'un plantage et les fragments écrits mais jamais comptés (orphelins)."""
        for reste in (*self.dossier.glob(f"{self.prefixe}-*.tmp"), *self.dossier.glob("*.json.tmp"),
                      *self.dossier.glob(f"{NOM_DU_MARQUEUR}.tmp")):
            reste.unlink()
        for fichier in self.dossier.iterdir():
            numero = _numero_du_fragment(self.prefixe, fichier.name)
            if numero is not None and numero >= self._fragments:
                fichier.unlink()

    @property
    def complet(self) -> bool:
        return self.infos is not None

    @property
    def en_attente(self) -> int:
        """Éléments ajoutés mais pas encore validés."""
        return len(self._tampon)

    @property
    def octets_en_attente(self) -> int:
        """Octets (JSON non compressé) des éléments en attente : de quoi vérifier la place avant d'écrire."""
        return self._octets

    @property
    def plein(self) -> bool:
        return len(self._tampon) >= self.par_fragment

    def ajouter(self, element: dict) -> None:
        """Met un élément en attente. Un élément qui ne s'écrit pas en JSON lève `TypeError` tout de suite."""
        ligne = (json.dumps(element, ensure_ascii=False) + "\n").encode("utf-8")
        self._tampon.append(ligne)
        self._octets += len(ligne)

    def valider(self, etat: dict | None = None) -> None:
        """Écrit les éléments en attente dans le fragment suivant, puis `etat.json` (dans cet ordre).

        `etat`, s'il est donné, remplace ce que l'appelant avait joint avant ; sans lui, l'ancien reste.
        Sans élément en attente, seul `etat.json` est mis à jour (il n'y a pas de fragment vide).
        Si l'écriture échoue, rien n'est compté et les éléments restent en attente : on peut réessayer.
        """
        tampon = self._tampon
        fragments = self._fragments
        if tampon:
            def ecrire(fichier: BinaryIO) -> None:
                # mtime=0 : le même contenu donne le même fichier, quel que soit le jour.
                with gzip.GzipFile(fileobj=fichier, mode="wb", compresslevel=6, mtime=0) as compresse:
                    compresse.write(b"".join(tampon))

            ecrire_atomique(self.dossier / _nom_du_fragment(self.prefixe, fragments), ecrire)
            fragments += 1
        nouvel_etat = etat if etat is not None else self.etat
        _ecrire_json(
            self.dossier / NOM_DE_L_ETAT,
            {"prefixe": self.prefixe, "elements": self.deja + len(tampon), "fragments": fragments, "etat": nouvel_etat},
        )
        self.deja += len(tampon)
        self._fragments = fragments
        self.etat = nouvel_etat
        self._tampon, self._octets = [], 0

    def terminer(self, infos: dict) -> None:
        """Valide ce qui reste, puis pose `.complet` (avec `infos`) : le travail est fini."""
        if self._tampon:
            self.valider()
        _ecrire_json(self.dossier / NOM_DU_MARQUEUR, infos)
        self.infos = infos

    def rouvrir(self) -> None:
        """Retire `.complet` pour continuer un travail déjà fini (on demande plus que ce qui est écrit)."""
        (self.dossier / NOM_DU_MARQUEUR).unlink(missing_ok=True)
        self.infos = None


def lire_elements(dossier: Path, prefixe: str) -> Iterator[dict]:
    """Les éléments validés de `dossier`, dans l'ordre d'écriture.

    Les fragments que `etat.json` ne compte pas (orphelins d'un plantage) sont ignorés. Un fragment
    compté qui manque lève `DonneesManquantes` avant le premier élément.
    """
    dossier = Path(dossier)
    etat = _lire_etat(dossier)
    if etat is not None:
        comptes = etat["fragments"]
    else:
        numeros = [n for f in dossier.glob(f"{prefixe}-*.jsonl.gz") if (n := _numero_du_fragment(prefixe, f.name)) is not None]
        comptes = max(numeros) + 1 if numeros else 0
    _verifier_les_fragments(dossier, prefixe, comptes)
    for numero in range(comptes):
        with gzip.open(dossier / _nom_du_fragment(prefixe, numero), "rt", encoding="utf-8") as fichier:
            for ligne in fichier:
                yield json.loads(ligne)
