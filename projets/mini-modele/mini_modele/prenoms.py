"""La liste des prénoms du mini-modèle, tirée du « Fichier des prénoms » de l'Insee.

Ce script n'est lancé qu'une fois, pour refaire `donnees/prenoms.txt` (le site
sert ce fichier versionné : il ne dépend pas de l'Insee à la construction) :

    uv run python -m mini_modele.prenoms

Il télécharge l'archive nationale (4 Mo), additionne les naissances de chaque
prénom sur toutes les années et les deux sexes, puis ne garde que les prénoms
qui s'écrivent avec les lettres du mini-modèle. Le fichier écrit ne contient
que des prénoms, sans aucun effectif : c'est une sélection, pas une copie des
données de l'Insee. La source, l'édition et la licence sont dans le README
(section « Les données »).

Ce fichier n'est pas dans le chemin vérifié (test_sources.py) : il ne sert
qu'à préparer la liste, il n'entre dans aucun calcul du mini-modèle.
"""

import csv
import hashlib
import io
import re
import shutil
import tempfile
import unicodedata
import urllib.request
import zipfile
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path

from mini_modele.calcul import empreinte_texte

URL = "https://www.insee.fr/fr/statistiques/fichier/8595130/prenoms-2025-nat_csv.zip"
PAGE = "https://www.insee.fr/fr/statistiques/8595130"
SEUIL_NAISSANCES = 500  # au moins 500 naissances depuis 1900, tous sexes confondus
SEUIL_REPLI = 200  # le seuil d'après, s'il reste trop peu de prénoms au premier
MINIMUM_PRENOMS = 5_000
LONGUEUR_MIN = 2
LONGUEUR_MAX = 15
CARACTERES_PERMIS = "-abcdefghijklmnopqrstuvwxyzàâäæçèéêëîïôöùûüÿœ"
# Le fichier de l'Insee (édition de juillet 2026) : séparateur « ; », colonnes en
# minuscules (sexe, prenom, periode, valeur) et une colonne « rang » en plus.
# `extraire` lit les colonnes sous leur nom en majuscules.
SEPARATEUR = ";"
COLONNES = ("SEXE", "PRENOM", "PERIODE", "VALEUR")
DELAI_SECONDES = 60
DOSSIER_DONNEES = Path(__file__).resolve().parent.parent / "donnees"
FICHIER = DOSSIER_DONNEES / "prenoms.txt"

_ANNEE = re.compile(r"[0-9]{4}")
_ENTIER = re.compile(r"[0-9]+")
_PERMIS = frozenset(CARACTERES_PERMIS)


def extraire(lignes: Iterable[dict[str, str]], seuil: int = SEUIL_NAISSANCES) -> list[str]:
    """Les prénoms retenus, en minuscules NFC, triés par point de code.

    Chaque ligne est un dictionnaire de clés SEXE, PRENOM, PERIODE et VALEUR.
    On ignore les prénoms qui commencent par « _ » (le fichier y range les
    prénoms rares) et les périodes qui ne sont pas une année à 4 chiffres. On
    additionne VALEUR sur les années et les deux sexes. On garde un total d'au
    moins `seuil`, de 2 à 15 caractères, uniquement des caractères permis, sans
    trait d'union au début, à la fin, ni doublé.
    """
    totaux: dict[str, int] = {}
    for ligne in lignes:
        if ligne["PRENOM"].startswith("_") or not _ANNEE.fullmatch(ligne["PERIODE"]):
            continue
        valeur = ligne["VALEUR"]
        if not _ENTIER.fullmatch(valeur):
            raise ValueError(
                f"VALEUR n'est pas un entier positif pour « {ligne['PRENOM']} » en {ligne['PERIODE']} "
                f"(reçu « {valeur} »). Le format du fichier de l'Insee a-t-il changé ? Regarde {PAGE}."
            )
        prenom = unicodedata.normalize("NFC", ligne["PRENOM"].lower())
        totaux[prenom] = totaux.get(prenom, 0) + int(valeur)
    retenus = [
        prenom
        for prenom, total in totaux.items()
        if total >= seuil
        and LONGUEUR_MIN <= len(prenom) <= LONGUEUR_MAX
        and _PERMIS.issuperset(prenom)
        and not prenom.startswith("-")
        and not prenom.endswith("-")
        and "--" not in prenom
    ]
    return sorted(retenus)


def lire_lignes(flux: Iterable[str]) -> Iterator[dict[str, str]]:
    """Les lignes d'un CSV de l'Insee, en dictionnaires de clés SEXE, PRENOM, PERIODE et VALEUR.

    Vérifie l'en-tête d'abord : le séparateur « ; » et les quatre colonnes
    (en majuscules ou en minuscules, dans n'importe quel ordre ; les autres
    colonnes, comme « rang », sont ignorées). Sinon, une erreur dit quoi faire.
    """
    lecteur = csv.reader(flux, delimiter=SEPARATEUR)
    en_tete = next(lecteur, [])
    noms = [colonne.strip().upper() for colonne in en_tete]
    if not all(colonne in noms for colonne in COLONNES):
        raise ValueError(
            f"En-tête inattendu dans le fichier de l'Insee : {en_tete!r}. Le script attend le séparateur "
            f"« {SEPARATEUR} » et les colonnes SEXE, PRENOM, PERIODE et VALEUR (en majuscules ou en minuscules). "
            f"Le format a peut-être changé ({PAGE}) : adapte lire_lignes dans mini_modele/prenoms.py, "
            "et note le changement dans la section « Les données » du README."
        )
    positions = {colonne: noms.index(colonne) for colonne in COLONNES}
    derniere = max(positions.values())
    for cellules in lecteur:
        if not cellules:  # une ligne vide
            continue
        if len(cellules) <= derniere:
            raise ValueError(
                f"Le fichier de l'Insee a une ligne trop courte (ligne {lecteur.line_num}) : "
                f"{len(cellules)} colonnes au lieu de {len(noms)}. Le fichier est-il tronqué ? Télécharge-le de nouveau."
            )
        yield {colonne: cellules[positions[colonne]] for colonne in COLONNES}


def lire_zip(chemin_zip: Path) -> Iterator[dict[str, str]]:
    """Les lignes du fichier CSV de l'archive (UTF-8, avec ou sans marque d'ordre)."""
    with zipfile.ZipFile(chemin_zip) as archive:
        csv_presents = [nom for nom in archive.namelist() if nom.lower().endswith(".csv")]
        if len(csv_presents) != 1:
            raise ValueError(
                f"L'archive de l'Insee devrait contenir un seul fichier CSV, elle en contient {len(csv_presents)} "
                f"({', '.join(csv_presents) or 'aucun'}). Regarde {PAGE} : l'édition a peut-être changé."
            )
        with archive.open(csv_presents[0]) as brut:
            yield from lire_lignes(io.TextIOWrapper(brut, encoding="utf-8-sig", newline=""))


def choisir_prenoms(ouvrir: Callable[[], Iterable[dict[str, str]]]) -> tuple[list[str], int]:
    """La liste et le seuil retenu. `ouvrir` rend les lignes à neuf à chaque appel (la liste est lue une ou deux fois).

    Avec le seuil de 500 naissances, s'il reste moins de 5 000 prénoms, on
    recommence avec 200 et on le dit. S'il en reste encore moins de 5 000, la
    liste n'est pas écrite : le fichier n'est sûrement pas celui qu'on attend.
    """
    prenoms = extraire(ouvrir())
    seuil = SEUIL_NAISSANCES
    if len(prenoms) < MINIMUM_PRENOMS:
        print(
            f"Seulement {len(prenoms)} prénoms avec le seuil de {SEUIL_NAISSANCES} naissances "
            f"(il en faut {MINIMUM_PRENOMS}) : on recommence avec un seuil de {SEUIL_REPLI} naissances."
        )
        seuil = SEUIL_REPLI
        prenoms = extraire(ouvrir(), seuil)
        if len(prenoms) < MINIMUM_PRENOMS:
            raise ValueError(
                f"Seulement {len(prenoms)} prénoms, même avec un seuil de {SEUIL_REPLI} naissances "
                f"(il en faut {MINIMUM_PRENOMS}). Le fichier téléchargé n'est sûrement pas le « Fichier des "
                f"prénoms » national : regarde {PAGE}."
            )
    return prenoms, seuil


def telecharger(url: str, destination: Path) -> None:
    """Télécharge `url` dans `destination` (délai de 60 s). Ne laisse pas de fichier à moitié écrit."""
    requete = urllib.request.Request(url, headers={"User-Agent": "la-forge-ia (liste des prenoms)"})
    try:
        with urllib.request.urlopen(requete, timeout=DELAI_SECONDES) as reponse:
            with open(destination, "wb") as sortie:
                shutil.copyfileobj(reponse, sortie)
    except OSError as erreur:  # URLError, HTTPError et le délai dépassé en font partie
        destination.unlink(missing_ok=True)
        raise ConnectionError(
            f"Téléchargement impossible depuis {url} ({erreur}). Vérifie la connexion, puis relance ; "
            f"si l'adresse a changé, la nouvelle est sur {PAGE}."
        ) from erreur


def main(url: str = URL, sortie: Path = FICHIER) -> None:
    """Télécharge l'archive, extrait la liste, écrit `sortie` et la décrit."""
    with tempfile.TemporaryDirectory() as dossier:
        chemin_zip = Path(dossier) / "prenoms.zip"
        telecharger(url, chemin_zip)
        octets_zip = chemin_zip.read_bytes()
        prenoms, seuil = choisir_prenoms(lambda: lire_zip(chemin_zip))
    texte = "\n".join(prenoms) + "\n"
    sortie = Path(sortie)
    sortie.parent.mkdir(parents=True, exist_ok=True)
    with open(sortie, "w", encoding="utf-8", newline="\n") as fichier:
        fichier.write(texte)
    print(f"Archive : {len(octets_zip)} octets, SHA-256 {hashlib.sha256(octets_zip).hexdigest()}")
    print(f"Nombre de prénoms : {len(prenoms)} (seuil de {seuil} naissances)")
    print(f"Caractères utilisés : {''.join(sorted(set(texte) - {chr(10)}))}")
    print(f"Empreinte du fichier : {empreinte_texte(texte)}")
    print(f"Écrit : {sortie}")


if __name__ == "__main__":
    main()
