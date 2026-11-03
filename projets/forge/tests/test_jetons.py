"""Tests de l'encodage du corpus en jetons : fragments uint16, parallélisme, reprise, place.

Aucun test n'ouvre le réseau. Les fragments d'entrée sont faits ici, avec les mêmes
fonctions que le téléchargement, à partir de quelques textes du dépôt.
"""

import gzip
import json
import os
import pickle
import shutil
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from forge.__main__ import main
from forge.chemins import PlaceInsuffisante
from forge.donnees import jetons as module_jetons
from forge.donnees.jetons import encoder_corpus, lire_jetons
from forge.donnees.melange import est_validation
from forge.donnees.nettoyage import empreinte, empreinte_du_texte_nettoye
from forge.tokenizer import entrainer_tokenizer
from forge.tokenizer.apprentissage import DonneesManquantes

DOSSIER_DONNEES_DE_TEST = Path(__file__).parent / "donnees"
TEXTE_DE_TEST = (DOSSIER_DONNEES_DE_TEST / "corpus_test.txt").read_text(encoding="utf-8")
PARAGRAPHES = [paragraphe.strip() for paragraphe in TEXTE_DE_TEST.split("\n\n") if paragraphe.strip()]

# Des textes piégeux : ce qui ressemble à un jeton spécial, des émojis, des écritures variées.
PIEGES = [
    "Un texte qui parle de <|fin_texte|> et de <|debut_texte|> sans jamais les émettre.",
    "Des émojis : 🙂 🇫🇷 👨‍👩‍👧, et des tabulations\tici\tet là.",
    "日本語の文章と العربية et ελληνικά, mêlés au français.",
]

# Les fragments d'entrée : source → nombre de documents de chacun de ses fragments.
# Rangés par nom, les dossiers donnent code_python (fragments 0 et 1) puis web_fr (2, 3, 4).
FRAGMENTS_DE_TEST = {"web_fr": [500, 500, 200], "code_python": [300, 100]}
NB_DOCS_TEST = sum(sum(tailles) for tailles in FRAGMENTS_DE_TEST.values())
NB_FRAGMENTS_TEST = sum(len(tailles) for tailles in FRAGMENTS_DE_TEST.values())


def faux_documents(source: str, debut: int, nombre: int) -> list[str]:
    """Des documents déjà nettoyés (au sens du téléchargement), tous différents."""
    documents = []
    for i in range(debut, debut + nombre):
        piege = f"\n{PIEGES[i % len(PIEGES)]}" if i % 7 == 0 else ""
        documents.append(f"document {i} ({source})\n\n{PARAGRAPHES[i % len(PARAGRAPHES)]}{piege}")
    return documents


def ecrire_fragment(dossier: Path, numero: int, textes: list[str]) -> None:
    """Écrit un fragment comme le téléchargement : une ligne `{"texte": …}` par texte, en gzip."""
    dossier.mkdir(parents=True, exist_ok=True)
    with gzip.GzipFile(dossier / f"fragment-{numero:05d}.jsonl.gz", mode="wb", mtime=0) as fichier:
        for texte in textes:
            fichier.write((json.dumps({"texte": texte}, ensure_ascii=False) + "\n").encode("utf-8"))


def fin_de_texte(tokenizer) -> int:
    return tokenizer.id_special("<|fin_texte|>")


def jetons_attendus(tokenizer, documents: list[str]) -> tuple[list[int], list[int]]:
    """Ce que l'encodage doit écrire pour un fragment : (train, val), calculé document par document."""
    train: list[int] = []
    val: list[int] = []
    for texte in documents:
        cible = val if est_validation(empreinte_du_texte_nettoye(texte)) else train
        cible.extend([*tokenizer.encoder(texte), fin_de_texte(tokenizer)])
    return train, val


def lire_tout(sortie: Path, sous_dossier: str) -> np.ndarray:
    """Tous les jetons d'un sous-dossier (copie en mémoire : aucun fichier reste ouvert)."""
    morceaux = [np.array(lire_jetons(f)) for f in sorted((sortie / sous_dossier).glob("*.bin"))]
    return np.concatenate(morceaux) if morceaux else np.empty(0, dtype=np.uint16)


def contenu_du_dossier(dossier: Path) -> dict[str, bytes]:
    """Chemin relatif → octets, pour comparer deux dossiers de sortie octet pour octet."""
    return {f.relative_to(dossier).as_posix(): f.read_bytes() for f in sorted(dossier.rglob("*")) if f.is_file()}


@pytest.fixture(scope="module")
def tokenizer_de_test():
    return entrainer_tokenizer([TEXTE_DE_TEST], taille_vocabulaire=1024)


@pytest.fixture(scope="module")
def corpus(tmp_path_factory):
    """Les dossiers de sources (avec `.complet`) et, dans l'ordre des fragments de sortie, leurs documents."""
    racine = tmp_path_factory.mktemp("textes")
    dossiers = []
    fragments: list[list[str]] = []
    for source in sorted(FRAGMENTS_DE_TEST):
        dossier = racine / source
        debut = 0
        for numero, nombre in enumerate(FRAGMENTS_DE_TEST[source]):
            documents = faux_documents(source, debut, nombre)
            ecrire_fragment(dossier, numero, documents)
            fragments.append(documents)
            debut += nombre
        (dossier / ".complet").write_text("{}", encoding="utf-8")
        dossiers.append(dossier)
    # Les documents sont déjà propres : leur empreinte ne change pas avec le nettoyage.
    assert all(empreinte(t) == empreinte_du_texte_nettoye(t) for documents in fragments for t in documents)
    return SimpleNamespace(racine=racine, dossiers=dossiers, fragments=fragments)


@pytest.fixture(scope="module")
def reference(corpus, tokenizer_de_test, tmp_path_factory):
    """Le corpus encodé une fois, avec 2 processus : les tests de lecture s'en servent."""
    sortie = tmp_path_factory.mktemp("jetons")
    lignes: list[str] = []
    resume = encoder_corpus(corpus.dossiers, tokenizer_de_test, sortie, processus=2, journal=lignes.append)
    return SimpleNamespace(sortie=sortie, resume=resume, journal=lignes)


def copie_de_la_reference(reference, tmp_path: Path) -> Path:
    """Une copie de la sortie de référence (les dates des fichiers sont gardées)."""
    copie = tmp_path / "jetons"
    shutil.copytree(reference.sortie, copie)
    return copie


def dossiers_copies(corpus, tmp_path: Path) -> list[Path]:
    """Une copie des textes d'entrée, qu'un test peut abîmer sans toucher aux autres."""
    entree = tmp_path / "textes"
    shutil.copytree(corpus.racine, entree)
    return [entree / dossier.name for dossier in corpus.dossiers]


# --- Encodage ------------------------------------------------------------------------


def test_encodage_et_fin_de_texte(corpus, tokenizer_de_test, reference):
    sortie = reference.sortie
    train = lire_tout(sortie, "train")
    assert train.dtype == np.uint16
    fin = fin_de_texte(tokenizer_de_test)
    docs = tokenizer_de_test.decoder([int(i) for i in train if i != fin])
    assert "document 0" in docs
    val = lire_tout(sortie, "val")
    assert val.size > 0  # le corpus de test est assez grand pour avoir des documents de validation
    assert (train == fin).sum() + (val == fin).sum() == NB_DOCS_TEST
    assert (sortie / ".complet").exists() and reference.resume["octets_par_jeton"] > 1
    # Aucun jeton spécial dans les textes, même ceux qui contiennent « <|fin_texte|> ».
    for jetons in (train, val):
        assert ((jetons < tokenizer_de_test.premier_special) | (jetons == fin)).all()


def test_les_jetons_sont_ceux_du_tokenizer_fragment_par_fragment(corpus, tokenizer_de_test, reference):
    assert len(corpus.fragments) == NB_FRAGMENTS_TEST
    au_moins_un_val = False
    for numero, documents in enumerate(corpus.fragments):
        train, val = jetons_attendus(tokenizer_de_test, documents)
        for sous_dossier, attendu in (("train", train), ("val", val)):
            fichier = reference.sortie / sous_dossier / f"fragment-{numero:05d}.bin"
            if attendu:
                assert np.array(lire_jetons(fichier)).tolist() == attendu, fichier
            else:
                assert not fichier.exists(), f"{fichier} ne devrait pas exister : aucun jeton"
        au_moins_un_val = au_moins_un_val or bool(val)
    assert au_moins_un_val


def test_le_resume_et_l_index(corpus, tokenizer_de_test, reference):
    sortie, resume = reference.sortie, reference.resume
    assert set(resume) == {"jetons_train", "jetons_val", "octets_par_jeton"}
    assert resume["jetons_train"] == len(lire_tout(sortie, "train"))
    assert resume["jetons_val"] == len(lire_tout(sortie, "val"))
    documents = [texte for fragment in corpus.fragments for texte in fragment]
    octets = sum(len(texte.encode("utf-8")) for texte in documents)
    jetons_sans_fin = sum(len(tokenizer_de_test.encoder(texte)) for texte in documents)
    assert resume["octets_par_jeton"] == pytest.approx(octets / jetons_sans_fin)
    assert resume["jetons_train"] + resume["jetons_val"] == jetons_sans_fin + NB_DOCS_TEST

    index = json.loads((sortie / "index.json").read_text(encoding="utf-8"))
    fichiers = {f.relative_to(sortie).as_posix(): len(lire_jetons(f)) for f in sortie.glob("*/*.bin")}
    assert index["fichiers"] == fichiers
    assert index["jetons_train"] == resume["jetons_train"] and index["jetons_val"] == resume["jetons_val"]
    assert index["octets"] == octets and index["jetons_sans_fin"] == jetons_sans_fin
    assert index["documents_train"] + index["documents_val"] == NB_DOCS_TEST
    assert index["tokenizer"]["taille_vocabulaire"] == tokenizer_de_test.taille_vocabulaire
    assert index["provenance"] == {
        "fragment-00000": "code_python/fragment-00000.jsonl.gz",
        "fragment-00001": "code_python/fragment-00001.jsonl.gz",
        "fragment-00002": "web_fr/fragment-00000.jsonl.gz",
        "fragment-00003": "web_fr/fragment-00001.jsonl.gz",
        "fragment-00004": "web_fr/fragment-00002.jsonl.gz",
    }
    assert all((sortie / f"fragment-{n:05d}.fait").is_file() for n in range(NB_FRAGMENTS_TEST))
    # Le journal est en français, une ligne par fragment, et donne la vitesse.
    assert "Encodage de 5 fragments avec 2 processus" in reference.journal[0]
    assert sum("jetons," in ligne for ligne in reference.journal) == NB_FRAGMENTS_TEST
    assert "Mo/s" in reference.journal[-1]


def test_reprise_sans_doublon(corpus, tokenizer_de_test, tmp_path):
    encoder_corpus(corpus.dossiers, tokenizer_de_test, tmp_path, processus=2)
    avant = (tmp_path / "index.json").read_text()
    encoder_corpus(corpus.dossiers, tokenizer_de_test, tmp_path, processus=2)
    assert (tmp_path / "index.json").read_text() == avant


def test_le_resultat_ne_depend_pas_du_nombre_de_processus(corpus, tokenizer_de_test, reference, tmp_path):
    # `reference` vient de 2 processus ; ici, un seul (sans processus à part) : mêmes octets.
    encoder_corpus(corpus.dossiers, tokenizer_de_test, tmp_path, processus=1)
    assert contenu_du_dossier(tmp_path) == contenu_du_dossier(reference.sortie)


def test_le_nombre_de_processus_par_defaut_est_celui_des_coeurs(corpus, tokenizer_de_test, tmp_path, monkeypatch):
    vus = []
    reel = module_jetons._encoder_tous_les_fragments

    def espion(travaux, tokenizer, empreinte_tokenizer, sortie, processus, rendre_compte):
        vus.append(processus)
        return reel(travaux, tokenizer, empreinte_tokenizer, sortie, 1, rendre_compte)

    monkeypatch.setattr(os, "cpu_count", lambda: 16)
    monkeypatch.setattr(module_jetons, "_encoder_tous_les_fragments", espion)
    encoder_corpus(corpus.dossiers, tokenizer_de_test, tmp_path)
    assert vus == [16]
    with pytest.raises(ValueError, match="au moins 1"):
        encoder_corpus(corpus.dossiers, tokenizer_de_test, tmp_path / "autre", processus=0)


def test_jamais_plus_de_processus_que_de_fragments_ni_que_windows_n_en_permet(monkeypatch):
    assert module_jetons._processus_utiles(16, 5) == 5
    assert module_jetons._processus_utiles(2, 5) == 2
    monkeypatch.setattr(module_jetons.sys, "platform", "linux")
    assert module_jetons._processus_utiles(128, 400) == 128
    monkeypatch.setattr(module_jetons.sys, "platform", "win32")
    assert module_jetons._processus_utiles(128, 400) == 60


# --- Reprise ---------------------------------------------------------------------------


def dates_des_fichiers(dossier: Path) -> dict[str, int]:
    return {f.relative_to(dossier).as_posix(): f.stat().st_mtime_ns for f in dossier.rglob("*") if f.is_file()}


def test_une_relance_ne_refait_rien(corpus, tokenizer_de_test, reference, tmp_path):
    sortie = copie_de_la_reference(reference, tmp_path)
    avant = dates_des_fichiers(sortie)
    lignes: list[str] = []
    encoder_corpus(corpus.dossiers, tokenizer_de_test, sortie, processus=1, journal=lignes.append)
    assert sum(ligne.endswith("déjà encodé, sauté.") for ligne in lignes) == NB_FRAGMENTS_TEST
    assert not [ligne for ligne in lignes if "jetons," in ligne]  # aucun fragment refait
    assert "déjà encodés" in lignes[-1]
    # Seuls index.json et .complet sont réécrits (ils reviennent à la fin, avec le même contenu).
    apres = dates_des_fichiers(sortie)
    changes = {nom for nom in avant if avant[nom] != apres[nom]}
    assert changes <= {"index.json", ".complet"}
    assert contenu_du_dossier(sortie) == contenu_du_dossier(reference.sortie)


def test_reprise_fragment_par_fragment(corpus, tokenizer_de_test, reference, tmp_path):
    sortie = copie_de_la_reference(reference, tmp_path)
    # Coupure en plein travail : le fragment 2 n'a plus son marqueur et son fichier est coupé ;
    # le fragment 3 a son marqueur mais un fichier de la mauvaise taille ; des .tmp traînent.
    (sortie / "fragment-00002.fait").unlink()
    fichier = sortie / "train" / "fragment-00002.bin"
    fichier.write_bytes(fichier.read_bytes()[: fichier.stat().st_size // 2])
    fichier = sortie / "train" / "fragment-00003.bin"
    fichier.write_bytes(fichier.read_bytes()[:-2])
    (sortie / ".complet").unlink()
    (sortie / "train" / "fragment-00004.bin.tmp").write_bytes(b"\x01\x02")
    (sortie / "fragment-00004.fait.tmp").write_text("{", encoding="utf-8")
    avant = dates_des_fichiers(sortie)

    lignes: list[str] = []
    encoder_corpus(corpus.dossiers, tokenizer_de_test, sortie, processus=1, journal=lignes.append)

    refaits = [ligne for ligne in lignes if "jetons," in ligne]
    assert {ligne.split()[1] for ligne in refaits} == {"fragment-00002", "fragment-00003"}
    assert not list(sortie.rglob("*.tmp"))
    # Les fragments 0, 1 et 4 n'ont pas été touchés : ni leurs jetons ni leur marqueur.
    apres = dates_des_fichiers(sortie)
    intacts = [nom for nom in avant if any(f"fragment-0000{n}." in nom for n in (0, 1, 4)) and not nom.endswith(".tmp")]
    assert intacts and all(apres[nom] == avant[nom] for nom in intacts)
    assert contenu_du_dossier(sortie) == contenu_du_dossier(reference.sortie)


def test_un_fragment_d_entree_change_est_reencode(corpus, tokenizer_de_test, reference, tmp_path):
    sortie = copie_de_la_reference(reference, tmp_path)
    dossiers = dossiers_copies(corpus, tmp_path)
    # Le fragment 3 (web_fr, fragment 1) est refait avec un document de plus.
    nouveaux = [*corpus.fragments[3], *faux_documents("web_fr", 9000, 1)]
    ecrire_fragment(dossiers[1], 1, nouveaux)

    lignes: list[str] = []
    encoder_corpus(dossiers, tokenizer_de_test, sortie, processus=1, journal=lignes.append)

    refaits = [ligne for ligne in lignes if "jetons," in ligne]
    assert len(refaits) == 1 and refaits[0].split()[1] == "fragment-00003"
    train, val = jetons_attendus(tokenizer_de_test, nouveaux)
    for sous_dossier, attendu in (("train", train), ("val", val)):
        fichier = sortie / sous_dossier / "fragment-00003.bin"
        assert (np.array(lire_jetons(fichier)).tolist() if fichier.exists() else []) == attendu


def test_un_fragment_sans_val_ne_laisse_pas_un_vieux_fichier(corpus, tokenizer_de_test, tmp_path):
    # Un fragment réécrit sans aucun document de validation ne doit pas garder l'ancien val/.
    dossiers = dossiers_copies(corpus, tmp_path)
    sortie = tmp_path / "jetons"
    encoder_corpus(dossiers, tokenizer_de_test, sortie, processus=1)
    numero, documents = next(
        (n, d) for n, d in enumerate(corpus.fragments) if jetons_attendus(tokenizer_de_test, d)[1]
    )
    seulement_train = [t for t in documents if not est_validation(empreinte_du_texte_nettoye(t))]
    source = dossiers[0] if numero < 2 else dossiers[1]
    ecrire_fragment(source, numero if numero < 2 else numero - 2, seulement_train)
    encoder_corpus(dossiers, tokenizer_de_test, sortie, processus=1)
    assert not (sortie / "val" / f"fragment-{numero:05d}.bin").exists()
    index = json.loads((sortie / "index.json").read_text(encoding="utf-8"))
    assert f"val/fragment-{numero:05d}.bin" not in index["fichiers"]


def test_un_autre_tokenizer_ou_d_autres_textes_sont_refuses(corpus, tokenizer_de_test, reference, tmp_path):
    sortie = copie_de_la_reference(reference, tmp_path)
    avant = contenu_du_dossier(sortie)
    autre = entrainer_tokenizer([TEXTE_DE_TEST], taille_vocabulaire=512)
    with pytest.raises(ValueError, match="autre tokenizer") as erreur:
        encoder_corpus(corpus.dossiers, autre, sortie, processus=1)
    assert "Supprime le dossier" in str(erreur.value)
    assert contenu_du_dossier(sortie) == avant  # rien n'a été touché, le .complet non plus

    (sortie / "train" / "fragment-00099.bin").write_bytes(b"\x01\x00")
    with pytest.raises(ValueError, match="que 5 fragments"):
        encoder_corpus(corpus.dossiers, tokenizer_de_test, sortie, processus=1)
    assert (sortie / ".complet").exists()


def test_ctrl_c_pendant_le_travail_des_processus(corpus, tokenizer_de_test, reference, tmp_path):
    sortie = tmp_path / "jetons"
    vues: list[str] = []

    def journal_qui_coupe(ligne: str) -> None:
        vues.append(ligne)
        if "jetons," in ligne:  # le premier fragment terminé : l'utilisateur appuie sur Ctrl+C
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        encoder_corpus(corpus.dossiers, tokenizer_de_test, sortie, processus=2, journal=journal_qui_coupe)
    # Les processus sont arrêtés, rien ne traîne, et le dossier n'est pas tenu pour complet.
    assert not list(sortie.rglob("*.tmp"))
    assert not (sortie / ".complet").exists() and not (sortie / "index.json").exists()
    # La relance finit le travail, sans doublon ni trou.
    encoder_corpus(corpus.dossiers, tokenizer_de_test, sortie, processus=2)
    assert contenu_du_dossier(sortie) == contenu_du_dossier(reference.sortie)


# --- Disque plein ----------------------------------------------------------------------


class DisquePlein:
    """Un `verifier_place` qui compte ses appels et manque de place à partir du `limite`-ième."""

    def __init__(self, limite: float = float("inf")):
        self.limite = limite
        self.appels: list[tuple[int, Path]] = []

    def __call__(self, octets_requis, chemin=None):
        self.appels.append((octets_requis, chemin))
        if len(self.appels) > self.limite:
            raise PlaceInsuffisante("Il manque 3,0 Go sur D: : 1,0 Go libres, 4,0 Go nécessaires. Libère de la place.")


def test_la_place_est_verifiee_avant_chaque_fichier(corpus, tokenizer_de_test, tmp_path, monkeypatch):
    place = DisquePlein()
    monkeypatch.setattr(module_jetons, "verifier_place", place)
    encoder_corpus(corpus.dossiers, tokenizer_de_test, tmp_path, processus=1)
    fichiers = [f for f in tmp_path.rglob("*") if f.is_file()]
    assert len(place.appels) == len(fichiers) > NB_FRAGMENTS_TEST
    # Chaque fichier : sa taille, plus 2 Go de marge, sur le disque du dossier où il s'écrit.
    assert all(octets >= 2 * 1024**3 for octets, _ in place.appels)
    assert {chemin for _, chemin in place.appels} == {tmp_path, tmp_path / "train", tmp_path / "val"}
    assert any(octets > 2 * 1024**3 + 1000 for octets, _ in place.appels)  # les fichiers de jetons


def test_disque_plein_a_chaque_endroit(corpus, tokenizer_de_test, reference, tmp_path, monkeypatch):
    # D'abord, combien de fichiers une exécution complète écrit-elle ?
    compte = DisquePlein()
    monkeypatch.setattr(module_jetons, "verifier_place", compte)
    encoder_corpus(corpus.dossiers, tokenizer_de_test, tmp_path / "compte", processus=1)
    total = len(compte.appels)

    # Le disque se remplit après `limite` fichiers : au tout début, au milieu, juste avant
    # l'index et juste avant `.complet`.
    for limite in (0, 1, total // 2, total - 2, total - 1):
        sortie = tmp_path / f"plein-{limite}"
        monkeypatch.setattr(module_jetons, "verifier_place", DisquePlein(limite))
        with pytest.raises(PlaceInsuffisante, match="Il manque 3,0 Go"):
            encoder_corpus(corpus.dossiers, tokenizer_de_test, sortie, processus=1)
        assert not list(sortie.rglob("*.tmp")), limite
        assert not (sortie / ".complet").exists(), limite
        assert len([f for f in sortie.rglob("*") if f.is_file()]) <= limite, limite
        if limite == 0:
            assert not [f for f in sortie.rglob("*") if f.is_file()]
        # Quand la place revient, la même commande finit le travail : même résultat qu'une
        # exécution sans incident, sans doublon ni trou.
        monkeypatch.setattr(module_jetons, "verifier_place", DisquePlein())
        encoder_corpus(corpus.dossiers, tokenizer_de_test, sortie, processus=1)
        assert contenu_du_dossier(sortie) == contenu_du_dossier(reference.sortie), limite


def test_plantage_entre_les_fichiers_d_un_fragment_refait(corpus, tokenizer_de_test, reference, tmp_path, monkeypatch):
    sortie = copie_de_la_reference(reference, tmp_path)
    dossiers = dossiers_copies(corpus, tmp_path)
    nouveaux = [*corpus.fragments[3], *faux_documents("web_fr", 9000, 1)]
    ecrire_fragment(dossiers[1], 1, nouveaux)  # le fragment 3 est refait, et lui seul
    # Le disque se remplit après son premier fichier : son jeu de jetons est à moitié refait.
    monkeypatch.setattr(module_jetons, "verifier_place", DisquePlein(1))
    with pytest.raises(PlaceInsuffisante):
        encoder_corpus(dossiers, tokenizer_de_test, sortie, processus=1)
    # Son ancien marqueur ne doit pas rester devant des fichiers qui ne vont plus avec.
    assert not (sortie / "fragment-00003.fait").exists()
    assert not (sortie / ".complet").exists() and not list(sortie.rglob("*.tmp"))
    monkeypatch.setattr(module_jetons, "verifier_place", DisquePlein())
    encoder_corpus(dossiers, tokenizer_de_test, sortie, processus=1)
    train, val = jetons_attendus(tokenizer_de_test, nouveaux)
    for sous_dossier, attendu in (("train", train), ("val", val)):
        fichier = sortie / sous_dossier / "fragment-00003.bin"
        assert (np.array(lire_jetons(fichier)).tolist() if fichier.exists() else []) == attendu


def test_les_erreurs_de_place_traversent_les_processus():
    erreur = pickle.loads(pickle.dumps(PlaceInsuffisante("Il manque 3,0 Go sur D:.")))
    assert isinstance(erreur, PlaceInsuffisante) and "Il manque 3,0 Go" in str(erreur)


# --- Entrées refusées ---------------------------------------------------------------------


def test_une_source_sans_complet_est_refusee(corpus, tokenizer_de_test, tmp_path):
    dossiers = dossiers_copies(corpus, tmp_path)
    (dossiers[1] / ".complet").unlink()
    sortie = tmp_path / "jetons"
    with pytest.raises(DonneesManquantes, match="n'est pas terminé") as erreur:
        encoder_corpus(dossiers, tokenizer_de_test, sortie, processus=1)
    assert "python -m forge donnees" in str(erreur.value) and "web_fr" in str(erreur.value)
    assert not sortie.exists()  # rien n'est écrit

    with pytest.raises(DonneesManquantes, match="introuvable"):
        encoder_corpus([tmp_path / "absent"], tokenizer_de_test, sortie, processus=1)
    vide = tmp_path / "vide"
    vide.mkdir()
    (vide / ".complet").write_text("{}", encoding="utf-8")
    with pytest.raises(DonneesManquantes, match="Aucun fragment"):
        encoder_corpus([vide], tokenizer_de_test, sortie, processus=1)
    with pytest.raises(ValueError, match="au moins une source"):
        encoder_corpus([], tokenizer_de_test, sortie, processus=1)
    with pytest.raises(ValueError, match="plusieurs fois"):
        encoder_corpus([dossiers[0], dossiers[0]], tokenizer_de_test, sortie, processus=1)


@pytest.mark.parametrize("processus", [1, 2])
def test_un_fragment_illisible_arrete_tout_proprement(corpus, tokenizer_de_test, tmp_path, processus):
    dossiers = dossiers_copies(corpus, tmp_path)
    (dossiers[1] / "fragment-00001.jsonl.gz").write_bytes(b"ceci n'est pas du gzip")
    sortie = tmp_path / "jetons"
    with pytest.raises(ValueError, match="illisible") as erreur:
        encoder_corpus(dossiers, tokenizer_de_test, sortie, processus=processus)
    assert "fragment-00001.jsonl.gz" in str(erreur.value) and "relance le téléchargement" in str(erreur.value)
    assert not list(sortie.rglob("*.tmp"))
    assert not (sortie / ".complet").exists() and not (sortie / "index.json").exists()


# --- Lecture -----------------------------------------------------------------------------


def test_lire_jetons(reference, tmp_path):
    fichier = reference.sortie / "train" / "fragment-00000.bin"
    jetons = lire_jetons(fichier)
    assert isinstance(jetons, np.memmap) and jetons.dtype == np.uint16
    assert len(jetons) * 2 == fichier.stat().st_size
    with pytest.raises(ValueError):
        jetons[0] = 1  # ouvert en lecture seule
    del jetons

    with pytest.raises(FileNotFoundError, match="introuvable"):
        lire_jetons(tmp_path / "absent.bin")
    impair = tmp_path / "impair.bin"
    impair.write_bytes(b"\x01\x00\x02")
    with pytest.raises(ValueError, match="jetons entiers"):
        lire_jetons(impair)
    vide = tmp_path / "vide.bin"
    vide.write_bytes(b"")
    with pytest.raises(ValueError, match="jetons entiers"):
        lire_jetons(vide)


# --- Sous-commande ---------------------------------------------------------------------------


@pytest.fixture
def donnees_de_la_session(corpus, tokenizer_de_test, tmp_path, monkeypatch):
    """`FORGE_DONNEES` dans un dossier neuf, avec les trois sources sous `textes/essai`."""
    monkeypatch.setenv("FORGE_DONNEES", str(tmp_path))
    racine = tmp_path / "textes" / "essai"
    racine.mkdir(parents=True)
    # Les trois sources du mélange : web_fr et wikipedia_fr ont les fragments de web_fr.
    shutil.copytree(corpus.racine / "web_fr", racine / "web_fr")
    shutil.copytree(corpus.racine / "web_fr", racine / "wikipedia_fr")
    shutil.copytree(corpus.racine / "code_python", racine / "code_python")
    tokenizer_de_test.enregistrer(tmp_path / "tokenizer.json")
    return SimpleNamespace(racine=tmp_path, textes=racine, tokenizer=tmp_path / "tokenizer.json")


def test_sous_commande_encoder(donnees_de_la_session, tokenizer_de_test, capsys, monkeypatch):
    donnees = donnees_de_la_session
    appels = []
    reel = module_jetons.encoder_corpus

    def espion(dossiers, tokenizer, sortie, processus=None, journal=None):
        appels.append((dossiers, sortie, processus))
        return reel(dossiers, tokenizer, sortie, 1, journal)

    monkeypatch.setattr(module_jetons, "encoder_corpus", espion)
    assert main(["encoder", "--donnees", "essai", "--tokenizer", str(donnees.tokenizer)]) == 0
    sortie = donnees.racine / "jetons" / "essai"
    assert appels == [
        (
            [donnees.textes / "web_fr", donnees.textes / "wikipedia_fr", donnees.textes / "code_python"],
            sortie,
            None,
        )
    ]
    assert (sortie / ".complet").exists() and (sortie / "index.json").exists()
    index = json.loads((sortie / "index.json").read_text(encoding="utf-8"))
    assert index["tokenizer"]["taille_vocabulaire"] == tokenizer_de_test.taille_vocabulaire
    assert len(index["provenance"]) == 3 + 3 + 2  # web_fr et wikipedia_fr : 3 fragments chacun, code_python : 2
    sortie_texte = capsys.readouterr().out
    assert "Jetons prêts dans" in sortie_texte and "octets par jeton" in sortie_texte and "Mo/s" in sortie_texte

    appels.clear()
    assert main(["encoder", "--donnees", "essai", "--tokenizer", str(donnees.tokenizer), "--processus", "4"]) == 0
    assert appels[0][2] == 4
    assert "déjà encodés" in capsys.readouterr().out


def test_sous_commande_encoder_refuse_une_source_sans_complet(donnees_de_la_session, capsys):
    donnees = donnees_de_la_session
    (donnees.textes / "wikipedia_fr" / ".complet").unlink()
    assert main(["encoder", "--donnees", "essai", "--tokenizer", str(donnees.tokenizer)]) == 1
    erreur = capsys.readouterr().err
    assert "Erreur" in erreur and "wikipedia_fr" in erreur and "python -m forge donnees" in erreur
    assert "Traceback" not in erreur
    assert not (donnees.racine / "jetons").exists()  # rien n'est écrit

    assert main(["encoder", "--donnees", "absent", "--tokenizer", str(donnees.tokenizer)]) == 1
    assert "introuvable" in capsys.readouterr().err


def test_sous_commande_encoder_erreurs_en_francais(donnees_de_la_session, capsys, monkeypatch):
    donnees = donnees_de_la_session
    arguments = ["encoder", "--donnees", "essai", "--tokenizer", str(donnees.tokenizer)]

    assert main(["encoder", "--donnees", "essai", "--tokenizer", str(donnees.racine / "absent.json")]) == 1
    assert "introuvable" in capsys.readouterr().err

    def manque_de_place(*args, **kwargs):
        raise PlaceInsuffisante("Il manque 3,0 Go sur D:. Libère de la place, puis relance.")

    monkeypatch.setattr(module_jetons, "encoder_corpus", manque_de_place)
    assert main(arguments) == 1
    assert "Il manque 3,0 Go" in capsys.readouterr().err

    def interrompu(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(module_jetons, "encoder_corpus", interrompu)
    assert main(arguments) == 130
    message = capsys.readouterr().err
    assert "Relance la même commande" in message and "Traceback" not in message

    def plante(*args, **kwargs):
        raise RuntimeError("quelque chose d'inattendu")

    monkeypatch.setattr(module_jetons, "encoder_corpus", plante)
    assert main(arguments) == 1
    message = capsys.readouterr().err
    assert "RuntimeError" in message and "quelque chose d'inattendu" in message and "Traceback" not in message

    # Sans --donnees ou sans --tokenizer, argparse refuse (code 2).
    for manquant in (["encoder", "--tokenizer", "t.json"], ["encoder", "--donnees", "essai"]):
        with pytest.raises(SystemExit) as sortie:
            main(manquant)
        assert sortie.value.code == 2
