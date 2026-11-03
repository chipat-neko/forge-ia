"""Tests des données de « ton IA » : sources, nettoyage, téléchargement avec reprise et mélange.

Aucun test n'ouvre le réseau : le téléchargement lit un faux lecteur.
"""

import gzip
import json
import re
from pathlib import Path

import pytest

from forge.__main__ import main
from forge.chemins import PlaceInsuffisante
from forge.donnees.melange import MELANGE_PAR_DEFAUT, est_validation, repartir
from forge.donnees.nettoyage import empreinte, nettoyer
from forge.donnees.sources import LICENCES_PERMISSIVES, SOURCES, Source
from forge.donnees.telechargement import telecharger

SOURCE_FACTICE = Source(
    nom="factice",
    depot="essai/factice",
    configuration=None,
    dossier_donnees=None,
    colonne="text",
    licence="aucune",
    url_licence="https://exemple.invalid/licence",
    garder=lambda ligne: True,
)
DOCS = [{"text": f"document {i} " + "x" * 300} for i in range(50)]


def lire_tous_les_textes(dossier: Path) -> list[str]:
    """Relit tous les fragments d'un dossier, dans l'ordre des noms."""
    textes = []
    for fragment in sorted(dossier.glob("fragment-*.jsonl.gz")):
        with gzip.open(fragment, "rt", encoding="utf-8") as fichier:
            textes.extend(json.loads(ligne)["texte"] for ligne in fichier)
    return textes


def lire_etat(dossier: Path) -> dict:
    return json.loads((dossier / "etat.json").read_text(encoding="utf-8"))


def faux_lecteur(docs):
    """Un lecteur qui rejoue `docs` depuis le début à chaque appel, comme une source en flux."""
    return lambda _source: iter(docs)


def lecteur_qui_coupe_a(docs, position):
    """Un lecteur dont le réseau se coupe juste avant le document `position`."""

    def lecteur(_source):
        for i, document in enumerate(docs):
            if i == position:
                raise ConnectionError("réseau coupé")
            yield document

    return lecteur


# --- Sources ---------------------------------------------------------------------


def test_filtre_code():
    g = SOURCES["code_python"].garder
    assert g({"language": "Python", "license": "mit"}) and not g({"language": "Python", "license": "gpl-3.0"})
    assert not g({"language": "JavaScript", "license": "mit"})


def test_filtre_code_toutes_les_licences_permissives():
    g = SOURCES["code_python"].garder
    assert LICENCES_PERMISSIVES == {
        "mit", "apache-2.0", "bsd-2-clause", "bsd-3-clause", "isc", "unlicense", "cc0-1.0",
    }
    for licence in LICENCES_PERMISSIVES:
        assert g({"language": "Python", "license": licence})
    for licence in ("gpl-2.0", "agpl-3.0", "lgpl-3.0", "mpl-2.0", "other", "", None):
        assert not g({"language": "Python", "license": licence})
    # Une ligne sans ces colonnes est écartée, jamais une erreur.
    assert not g({"code": "print(1)"})


def test_les_trois_sources():
    assert list(SOURCES) == ["web_fr", "wikipedia_fr", "code_python"]
    web = SOURCES["web_fr"]
    assert (web.depot, web.dossier_donnees, web.colonne) == (
        "HuggingFaceFW/fineweb-2", "data/fra_Latn/train", "text",
    )
    assert "ODC-By" in web.licence and web.url_licence.startswith("https://")
    wiki = SOURCES["wikipedia_fr"]
    assert (wiki.depot, wiki.configuration, wiki.colonne) == ("wikimedia/wikipedia", "20231101.fr", "text")
    assert "CC BY-SA 3.0" in wiki.licence
    code = SOURCES["code_python"]
    assert (code.depot, code.colonne) == ("codeparrot/github-code-clean", "code")
    # Le français du web et Wikipédia n'écartent rien : tout passe le filtre.
    assert web.garder({"text": "x"}) and wiki.garder({"text": "x"})
    for nom, source in SOURCES.items():
        assert source.nom == nom and source.licence and source.url_licence


def test_la_documentation_des_sources():
    doc = (Path(__file__).parents[3] / "docs" / "donnees.md").read_text(encoding="utf-8")
    for source in SOURCES.values():
        assert f"https://huggingface.co/datasets/{source.depot})" in doc, source.nom
        assert f"({source.url_licence})" in doc, source.nom
    for licence in LICENCES_PERMISSIVES:
        assert licence.lower() in doc.lower()
    # Typographie française : espace fine insécable (U+202F) avant « ; » et dans les guillemets.
    assert (
        "Les données ne sont jamais copiées dans ce dépôt ; "
        "seuls les modèles entraînés sont publiés."
    ) in doc
    assert "« ton IA »" in doc and "« " not in doc and " »" not in doc


# --- Nettoyage -------------------------------------------------------------------


def test_nettoyage():
    assert nettoyer("court") is None
    t = nettoyer("é\r\n" + "a" * 300 + "\x07")
    assert t.startswith("é\n") and "\x07" not in t and "\r" not in t


def test_nettoyage_en_detail():
    # NFC : « e » suivi d'un accent combinant devient « é ».
    assert nettoyer("é" + "a" * 300).startswith("é" + "a")
    # Contrôles retirés (dont \r seul, \x7f et les contrôles C1), \n et \t gardés.
    brut = "a\tb\nc\rd\x00e\x1bf\x7fg\x85h" + "z" * 300
    assert nettoyer(brut).startswith("a\tb\ncdefgh" + "z")
    # Espaces et retours de fin retirés, ceux du début gardés (indentation du code).
    t = nettoyer("  def f():\n    return 1\n" + "# x\n" * 100 + " \n\t \r\n")
    assert t.startswith("  def f():") and t.endswith("# x")
    # Un moins de 200 caractères, une fois nettoyé, est écarté ; 200 pile est gardé.
    assert nettoyer("a" * 199 + "\x07") is None
    assert nettoyer("a" * 199 + "   ") is None
    assert nettoyer("a" * 200 + "   ") == "a" * 200
    # Les caractères hors du plan de base (emojis) restent entiers.
    assert nettoyer("😀" * 200) == "😀" * 200


def test_nettoyage_ecarte_les_demi_paires():
    # Une moitié d'emoji isolée ne s'écrit pas en UTF-8 : elle est retirée.
    t = nettoyer("a" * 300 + "\ud83d" + "b" * 10)
    assert t == "a" * 300 + "b" * 10
    t.encode("utf-8")


def test_empreinte():
    brut = "é\r\n" + "a" * 300
    assert len(empreinte(brut)) == 40 and int(empreinte(brut), 16) >= 0
    # L'empreinte est celle du texte nettoyé : brut ou déjà nettoyé, c'est la même.
    assert empreinte(brut) == empreinte(nettoyer(brut))
    assert empreinte(brut) != empreinte(brut + "b")
    assert empreinte(brut) == empreinte(brut)


# --- Mélange et validation ---------------------------------------------------------


def test_melange_et_validation():
    assert repartir(1000) == {"web_fr": 750, "wikipedia_fr": 100, "code_python": 150}
    # Les 8 premiers chiffres hexadécimaux font l'entier comparé à `part`.
    parts = [est_validation(f"{i:08x}" + "0" * 32) for i in range(0, 2**32, 2**20)]
    assert 0 < sum(parts) < len(parts) * 0.02


def test_validation_est_deterministe_et_borne():
    assert est_validation("00000000" + "f" * 32) and not est_validation("ffffffff" + "0" * 32)
    # 0,5 % de 2^32 = 21 474 836,48 : le seuil passe entre les deux valeurs voisines.
    assert est_validation(f"{21474836:08x}" + "a" * 32)
    assert not est_validation(f"{21474837:08x}" + "a" * 32)
    assert not est_validation("00000000" + "0" * 32, part=0.0)
    assert est_validation("ffffffff" + "0" * 32, part=1.0)
    assert est_validation(empreinte("x" * 300)) == est_validation(empreinte("x" * 300))


def test_repartir_somme_exacte_et_proportions():
    for total in (0, 1, 7, 999, 314_572_800, 5 * 1024**2, 10**10 + 3):
        parts = repartir(total)
        assert sum(parts.values()) == total and list(parts) == list(MELANGE_PAR_DEFAUT)
        for nom, part in MELANGE_PAR_DEFAUT.items():
            assert abs(parts[nom] - total * part) < 1
    assert repartir(100, {"a": 0.5, "b": 0.5}) == {"a": 50, "b": 50}


def test_repartir_refuse_un_melange_faux():
    with pytest.raises(ValueError, match="1"):
        repartir(1000, {"a": 0.5, "b": 0.6})
    with pytest.raises(ValueError, match="négati"):
        repartir(1000, {"a": 1.5, "b": -0.5})
    with pytest.raises(ValueError, match="négati"):
        repartir(-1)


def test_le_tokenizer_utilise_le_meme_melange():
    from forge.tokenizer import apprentissage

    assert apprentissage.MELANGE_PAR_DEFAUT is MELANGE_PAR_DEFAUT
    assert not hasattr(apprentissage, "PROPORTIONS")
    assert MELANGE_PAR_DEFAUT == {"web_fr": 0.75, "wikipedia_fr": 0.10, "code_python": 0.15}
    assert set(MELANGE_PAR_DEFAUT) == set(SOURCES)


# --- Téléchargement : reprise, doublons, place ---------------------------------------


def test_reprise_apres_coupure_reseau(tmp_path):
    docs = [{"text": f"document {i} " + "x" * 300} for i in range(50)]

    def lecteur_qui_coupe(_):
        for i, d in enumerate(docs):
            if i == 20:
                raise ConnectionError("réseau coupé")
            yield d

    with pytest.raises(ConnectionError):
        telecharger(SOURCE_FACTICE, 10**9, tmp_path, lecteur_qui_coupe)
    assert not (tmp_path / ".complet").exists()
    telecharger(SOURCE_FACTICE, 10**9, tmp_path, lambda _: iter(docs))
    textes = lire_tous_les_textes(tmp_path)
    assert len(textes) == 50 and len(set(textes)) == 50
    assert (tmp_path / ".complet").exists()


def test_disque_plein(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "forge.donnees.telechargement.verifier_place",
        lambda *a, **k: (_ for _ in ()).throw(PlaceInsuffisante("Il manque 3 Go sur D:")),
    )
    with pytest.raises(PlaceInsuffisante):
        telecharger(SOURCE_FACTICE, 10**9, tmp_path, lambda _: iter(DOCS))
    assert not (tmp_path / ".complet").exists() and not list(tmp_path.glob("*.tmp"))


def test_disque_plein_au_milieu_ne_laisse_rien_de_partiel(tmp_path, monkeypatch):
    appels = []

    def place(octets_requis, chemin=None):
        appels.append(octets_requis)
        if len(appels) > 4:  # le disque se remplit après deux fragments
            raise PlaceInsuffisante("Il manque 3 Go sur D:")

    monkeypatch.setattr("forge.donnees.telechargement.verifier_place", place)
    with pytest.raises(PlaceInsuffisante):
        telecharger(SOURCE_FACTICE, 10**9, tmp_path, faux_lecteur(DOCS), octets_fragment=3000)
    assert not (tmp_path / ".complet").exists() and not list(tmp_path.glob("*.tmp"))
    # Les fragments déjà écrits sont complets et comptés dans l'état ; rien de plus.
    ecrits = lire_tous_les_textes(tmp_path)
    assert ecrits and len(ecrits) == len(set(ecrits))
    assert lire_etat(tmp_path)["fragments"] == len(list(tmp_path.glob("fragment-*.jsonl.gz")))
    # Quand la place revient, la relance finit le travail sans doublon ni trou.
    monkeypatch.setattr("forge.donnees.telechargement.verifier_place", lambda *a, **k: None)
    telecharger(SOURCE_FACTICE, 10**9, tmp_path, faux_lecteur(DOCS), octets_fragment=3000)
    assert lire_tous_les_textes(tmp_path) == [nettoyer(d["text"]) for d in DOCS]


def test_la_marge_de_place_est_de_2_go(tmp_path, monkeypatch):
    demandes = []
    monkeypatch.setattr(
        "forge.donnees.telechargement.verifier_place", lambda octets, chemin=None: demandes.append(octets)
    )
    telecharger(SOURCE_FACTICE, 10**9, tmp_path, faux_lecteur(DOCS))
    assert demandes and all(octets >= 2 * 1024**3 for octets in demandes)


def test_les_fragments_et_leur_format(tmp_path):
    telecharger(SOURCE_FACTICE, 10**9, tmp_path, faux_lecteur(DOCS), octets_fragment=3000)
    fragments = sorted(p.name for p in tmp_path.glob("fragment-*.jsonl.gz"))
    assert len(fragments) > 3
    assert fragments == [f"fragment-{i:05d}.jsonl.gz" for i in range(len(fragments))]
    with gzip.open(tmp_path / fragments[0], "rt", encoding="utf-8") as fichier:
        premiere = json.loads(fichier.readline())
    assert list(premiere) == ["texte"] and premiere["texte"] == nettoyer(DOCS[0]["text"])
    # Un fragment fait environ `octets_fragment` octets de texte, le dernier moins.
    tailles = []
    for nom in fragments[:-1]:
        with gzip.open(tmp_path / nom, "rt", encoding="utf-8") as fichier:
            tailles.append(sum(len(json.loads(ligne)["texte"].encode("utf-8")) for ligne in fichier))
    assert all(3000 <= t < 3000 + 400 for t in tailles)
    assert lire_tous_les_textes(tmp_path) == [nettoyer(d["text"]) for d in DOCS]
    assert not list(tmp_path.glob("*.tmp"))


def test_journal_en_francais(tmp_path):
    messages = []
    telecharger(SOURCE_FACTICE, 10**9, tmp_path, faux_lecteur(DOCS), octets_fragment=3000, journal=messages.append)
    assert any("fragment 0 écrit" in m for m in messages)
    assert "terminé" in messages[-1] and "source épuisée" in messages[-1]
    # Les tailles s'écrivent avec la virgule française, jamais avec un point.
    assert all(re.search(r"\d\.\d Mo", m) is None for m in messages)
    assert any(re.search(r"\d,\d Mo", m) for m in messages)
    messages.clear()
    telecharger(SOURCE_FACTICE, 10**9, tmp_path, faux_lecteur(DOCS), journal=messages.append)
    assert messages == ["factice : déjà complet."]


def test_etat_apres_telechargement(tmp_path):
    telecharger(SOURCE_FACTICE, 10**9, tmp_path, faux_lecteur(DOCS), octets_fragment=3000)
    etat = lire_etat(tmp_path)
    textes = lire_tous_les_textes(tmp_path)
    assert etat["documents_lus"] == len(DOCS)
    assert etat["octets_ecrits"] == sum(len(t.encode("utf-8")) for t in textes)
    assert (tmp_path / ".complet").exists()


def test_arret_a_octets_max(tmp_path):
    chemin = telecharger(SOURCE_FACTICE, 5000, tmp_path, faux_lecteur(DOCS), octets_fragment=3000)
    assert chemin == tmp_path and (tmp_path / ".complet").exists()
    textes = lire_tous_les_textes(tmp_path)
    taille = sum(len(t.encode("utf-8")) for t in textes)
    # Le dernier document peut dépasser un peu, jamais d'un document entier de plus.
    assert 5000 <= taille < 5000 + 400 and lire_etat(tmp_path)["octets_ecrits"] == taille
    assert 0 < len(textes) < len(DOCS)


def test_le_flux_de_la_source_est_ferme(tmp_path, monkeypatch):
    fermes = []

    def lecteur(_source):
        try:
            yield from DOCS
        finally:
            fermes.append(True)

    # Arrêt voulu à `octets_max` : le flux n'est pas lu jusqu'au bout, mais il est fermé.
    telecharger(SOURCE_FACTICE, 3000, tmp_path / "a", lecteur, octets_fragment=1500)
    assert fermes == [True]
    # Arrêt sur une erreur (le disque se remplit avant l'écriture du premier fragment) : fermé aussi.
    appels = []

    def place(octets_requis, chemin=None):
        appels.append(octets_requis)
        if len(appels) == 2:
            raise PlaceInsuffisante("Il manque 3 Go sur D:")

    monkeypatch.setattr("forge.donnees.telechargement.verifier_place", place)
    fermes.clear()
    with pytest.raises(PlaceInsuffisante):
        telecharger(SOURCE_FACTICE, 10**9, tmp_path / "b", lecteur, octets_fragment=1500)
    assert fermes == [True]


def test_deja_complet_ne_relit_rien(tmp_path):
    telecharger(SOURCE_FACTICE, 5000, tmp_path, faux_lecteur(DOCS), octets_fragment=3000)
    avant = lire_tous_les_textes(tmp_path)

    def lecteur_interdit(_source):
        raise AssertionError("le lecteur ne doit pas être ouvert")

    telecharger(SOURCE_FACTICE, 5000, tmp_path, lecteur_interdit)
    telecharger(SOURCE_FACTICE, 100, tmp_path, lecteur_interdit)  # un volume plus petit : déjà atteint
    assert lire_tous_les_textes(tmp_path) == avant


def test_un_volume_plus_grand_reprend_sans_doublon(tmp_path):
    telecharger(SOURCE_FACTICE, 5000, tmp_path, faux_lecteur(DOCS), octets_fragment=3000)
    assert (tmp_path / ".complet").exists()
    telecharger(SOURCE_FACTICE, 10**9, tmp_path, faux_lecteur(DOCS), octets_fragment=3000)
    assert lire_tous_les_textes(tmp_path) == [nettoyer(d["text"]) for d in DOCS]
    assert (tmp_path / ".complet").exists()


def test_source_epuisee_est_complete_meme_sous_octets_max(tmp_path):
    telecharger(SOURCE_FACTICE, 10**9, tmp_path, faux_lecteur(DOCS[:5]))
    assert (tmp_path / ".complet").exists() and len(lire_tous_les_textes(tmp_path)) == 5
    # La source n'a pas grandi : la relance avec un volume plus grand ne lit rien de plus.
    telecharger(SOURCE_FACTICE, 10**10, tmp_path, lambda _s: (_ for _ in ()).throw(AssertionError("relu")))
    assert len(lire_tous_les_textes(tmp_path)) == 5


@pytest.mark.parametrize("position", [0, 1, 7, 19, 20, 33, 49])
def test_reprise_apres_coupure_a_chaque_endroit(tmp_path, position):
    docs = DOCS
    with pytest.raises(ConnectionError):
        telecharger(SOURCE_FACTICE, 10**9, tmp_path, lecteur_qui_coupe_a(docs, position), octets_fragment=3000)
    assert not (tmp_path / ".complet").exists()
    # La coupure ne casse rien : ce qui est écrit est complet, sans doublon.
    avant = lire_tous_les_textes(tmp_path)
    assert avant == [nettoyer(d["text"]) for d in docs[: len(avant)]]
    # `documents_lus` ne compte que les documents jusqu'au dernier fragment écrit.
    if avant:
        assert lire_etat(tmp_path)["documents_lus"] == len(avant)
    telecharger(SOURCE_FACTICE, 10**9, tmp_path, faux_lecteur(docs), octets_fragment=3000)
    assert lire_tous_les_textes(tmp_path) == [nettoyer(d["text"]) for d in docs]


def test_coupures_repetees(tmp_path):
    # Le réseau se coupe de plus en plus loin : à la fin, tout est là, une seule fois.
    for position in (3, 9, 15, 30, 44):
        with pytest.raises(ConnectionError):
            telecharger(SOURCE_FACTICE, 10**9, tmp_path, lecteur_qui_coupe_a(DOCS, position), octets_fragment=2000)
    telecharger(SOURCE_FACTICE, 10**9, tmp_path, faux_lecteur(DOCS), octets_fragment=2000)
    assert lire_tous_les_textes(tmp_path) == [nettoyer(d["text"]) for d in DOCS]


def test_plantage_apres_le_fragment_avant_l_etat(tmp_path, monkeypatch):
    # Règle R3 : l'état n'est mis à jour qu'APRÈS l'écriture du fragment. Un plantage entre
    # les deux relit les documents du fragment orphelin, sans perte ni doublon.
    from forge.donnees import telechargement

    ecrire_etat = telechargement._ecrire_etat
    appels = []

    def etat_qui_plante(dossier, etat):
        appels.append(etat)
        if len(appels) == 2:
            raise OSError("plantage entre le fragment et l'état")
        ecrire_etat(dossier, etat)

    monkeypatch.setattr(telechargement, "_ecrire_etat", etat_qui_plante)
    with pytest.raises(OSError, match="plantage"):
        telecharger(SOURCE_FACTICE, 10**9, tmp_path, faux_lecteur(DOCS), octets_fragment=3000)
    assert len(list(tmp_path.glob("fragment-*.jsonl.gz"))) == 2  # le second est orphelin
    assert lire_etat(tmp_path)["fragments"] == 1
    monkeypatch.setattr(telechargement, "_ecrire_etat", ecrire_etat)
    telecharger(SOURCE_FACTICE, 10**9, tmp_path, faux_lecteur(DOCS), octets_fragment=3000)
    assert lire_tous_les_textes(tmp_path) == [nettoyer(d["text"]) for d in DOCS]
    assert lire_etat(tmp_path)["documents_lus"] == len(DOCS)


def test_erreur_pendant_l_ecriture_du_fragment(tmp_path, monkeypatch):
    # Un fragment qui n'arrive pas au bout de `os.replace` n'existe pas : ni fragment à moitié
    # écrit, ni `.tmp` qui traîne, et la relance reprend sans doublon ni trou.
    import os

    from forge.donnees import telechargement

    remplacer = os.replace
    fragments_remplaces = []

    def remplacement_qui_plante(source, destination):
        if str(destination).endswith(".jsonl.gz"):
            fragments_remplaces.append(destination)
            if len(fragments_remplaces) == 2:
                raise OSError("coupure de courant")
        remplacer(source, destination)

    monkeypatch.setattr(telechargement.os, "replace", remplacement_qui_plante)
    with pytest.raises(OSError, match="coupure"):
        telecharger(SOURCE_FACTICE, 10**9, tmp_path, faux_lecteur(DOCS), octets_fragment=3000)
    assert not list(tmp_path.glob("*.tmp")) and not (tmp_path / ".complet").exists()
    assert [p.name for p in tmp_path.glob("fragment-*.jsonl.gz")] == ["fragment-00000.jsonl.gz"]
    monkeypatch.setattr(telechargement.os, "replace", remplacer)
    telecharger(SOURCE_FACTICE, 10**9, tmp_path, faux_lecteur(DOCS), octets_fragment=3000)
    assert lire_tous_les_textes(tmp_path) == [nettoyer(d["text"]) for d in DOCS]


def test_doublons_ecartes_dans_la_source_et_apres_reprise(tmp_path):
    base = [{"text": f"texte {i}\nsuite " + "y" * 300} for i in range(10)]
    # Chaque document est répété, une fois juste après et une fois bien plus loin ; une version
    # avec des fins de ligne Windows est le même texte une fois nettoyé.
    docs = []
    for d in base:
        docs += [d, d]
    docs += [{"text": d["text"].replace("\n", "\r\n") + "\n\n"} for d in base]
    docs += base
    with pytest.raises(ConnectionError):
        telecharger(SOURCE_FACTICE, 10**9, tmp_path, lecteur_qui_coupe_a(docs, 25), octets_fragment=1500)
    telecharger(SOURCE_FACTICE, 10**9, tmp_path, faux_lecteur(docs), octets_fragment=1500)
    textes = lire_tous_les_textes(tmp_path)
    assert textes == [nettoyer(d["text"]) for d in base]
    assert lire_etat(tmp_path)["documents_lus"] == len(docs)


def test_les_empreintes_survivent_a_la_reprise(tmp_path):
    # Premier lot fini à 3 000 octets, puis un volume plus grand : la source rejoue d'abord ses
    # premiers documents (sautés grâce à `documents_lus`), puis des copies de ceux déjà écrits,
    # puis des nouveaux. Seuls les nouveaux s'écrivent.
    telecharger(SOURCE_FACTICE, 3000, tmp_path, faux_lecteur(DOCS[:20]), octets_fragment=1500)
    deja = lire_tous_les_textes(tmp_path)
    lus = lire_etat(tmp_path)["documents_lus"]
    assert 0 < len(deja) == lus < 20 and (tmp_path / ".complet").exists()
    copies = [{"text": d["text"] + "\r\n\r\n"} for d in DOCS[:lus]]
    source_elargie = DOCS[:lus] + copies + DOCS[lus:30]
    telecharger(SOURCE_FACTICE, 10**9, tmp_path, faux_lecteur(source_elargie), octets_fragment=1500)
    assert lire_tous_les_textes(tmp_path) == [nettoyer(d["text"]) for d in DOCS[:30]]


def test_filtre_de_la_source_et_documents_trop_courts(tmp_path):
    source = Source(
        nom="filtree", depot="essai/filtree", configuration=None, dossier_donnees=None,
        colonne="code", licence="aucune", url_licence="https://exemple.invalid/",
        garder=lambda ligne: ligne.get("language") == "Python",
    )
    docs = []
    for i in range(30):
        docs.append({"code": f"# fichier {i}\n" + "a = 1\n" * 60, "language": "Python" if i % 3 == 0 else "C"})
    docs.append({"code": "x = 1", "language": "Python"})  # trop court
    docs.append({"code": None, "language": "Python"})  # colonne vide
    docs.append({"language": "Python"})  # colonne absente
    telecharger(source, 10**9, tmp_path, faux_lecteur(docs), octets_fragment=1000)
    textes = lire_tous_les_textes(tmp_path)
    assert [t.split("\n")[0] for t in textes] == [f"# fichier {i}" for i in range(0, 30, 3)]
    assert lire_etat(tmp_path)["documents_lus"] == len(docs)


def test_reprise_saute_les_documents_deja_lus(tmp_path):
    with pytest.raises(ConnectionError):
        telecharger(SOURCE_FACTICE, 10**9, tmp_path, lecteur_qui_coupe_a(DOCS, 30), octets_fragment=3000)
    deja = lire_etat(tmp_path)["documents_lus"]
    assert 0 < deja <= 30
    # À la relance, les `deja` premiers documents ne sont pas lus : s'ils l'étaient, ces faux
    # documents (qui ne ressemblent pas aux vrais) seraient écrits.
    intrus = {"text": "INTRUS " + "z" * 300}
    docs = [{"text": f"INTRUS {i} " + "z" * 300} for i in range(deja)] + DOCS[deja:]
    telecharger(SOURCE_FACTICE, 10**9, tmp_path, faux_lecteur(docs), octets_fragment=3000)
    textes = lire_tous_les_textes(tmp_path)
    assert textes == [nettoyer(d["text"]) for d in DOCS]
    assert intrus["text"][:6] not in "".join(textes)


def test_restes_tmp_effaces_a_la_relance(tmp_path):
    (tmp_path / "fragment-00000.jsonl.gz.tmp").write_bytes(b"\x1f\x8b pas fini")
    (tmp_path / "etat.json.tmp").write_text("{", encoding="utf-8")
    telecharger(SOURCE_FACTICE, 10**9, tmp_path, faux_lecteur(DOCS[:5]))
    assert not list(tmp_path.glob("*.tmp")) and len(lire_tous_les_textes(tmp_path)) == 5


def test_etat_incoherent_message_clair(tmp_path):
    telecharger(SOURCE_FACTICE, 3000, tmp_path, faux_lecteur(DOCS), octets_fragment=1500)
    (tmp_path / ".complet").unlink()
    etat = lire_etat(tmp_path)
    etat["octets_ecrits"] = 0
    etat["source_epuisee"] = False
    (tmp_path / "empreintes.bin").write_bytes(b"")  # fichier des empreintes perdu
    (tmp_path / "etat.json").write_text(json.dumps(etat), encoding="utf-8")
    with pytest.raises(RuntimeError, match="empreintes"):
        telecharger(SOURCE_FACTICE, 10**9, tmp_path, faux_lecteur(DOCS))


# --- Lecteur par défaut (Hugging Face), sans réseau ------------------------------------


class _FauxJeu:
    """Imite assez un jeu `datasets` en flux pour tester les appels du lecteur par défaut."""

    def __init__(self, lignes):
        self.lignes = lignes
        self.ignorees = 0

    def skip(self, n):
        self.ignorees += n
        return self

    def __iter__(self):
        return iter(self.lignes[self.ignorees:])


def test_lecteur_par_defaut_web_fr(monkeypatch):
    from forge.donnees import telechargement

    appels = []

    def faux_load_dataset(*args, **kwargs):
        appels.append((args, kwargs))
        return _FauxJeu([{"text": "a"}, {"text": "b"}, {"text": "c"}])

    monkeypatch.setattr("datasets.load_dataset", faux_load_dataset)
    lignes = list(telechargement.lecteur_hugging_face(SOURCES["web_fr"]))
    assert lignes == [{"text": "a"}, {"text": "b"}, {"text": "c"}]
    (args, kwargs), = appels
    # Les fichiers parquet du dossier de la source, en flux (sans configuration à nommer).
    assert args == ("parquet",)
    assert kwargs["data_files"] == "hf://datasets/HuggingFaceFW/fineweb-2/data/fra_Latn/train/*.parquet"
    assert kwargs["split"] == "train" and kwargs["streaming"] is True
    assert list(telechargement.lecteur_hugging_face(SOURCES["web_fr"], ignorer=2)) == [{"text": "c"}]


def test_lecteur_par_defaut_wikipedia(monkeypatch):
    from forge.donnees import telechargement

    appels = []
    monkeypatch.setattr(
        "datasets.load_dataset", lambda *a, **k: appels.append((a, k)) or _FauxJeu([{"text": "w"}])
    )
    assert list(telechargement.lecteur_hugging_face(SOURCES["wikipedia_fr"])) == [{"text": "w"}]
    (args, kwargs), = appels
    assert args[0] == "wikimedia/wikipedia" and "20231101.fr" in (args[1:] + tuple(kwargs.values()))
    assert kwargs["streaming"] is True and kwargs["split"] == "train"


def test_lecteur_par_defaut_code_lit_les_fichiers_parquet(monkeypatch):
    from forge.donnees import telechargement

    appels = []
    monkeypatch.setattr(
        "datasets.load_dataset", lambda *a, **k: appels.append((a, k)) or _FauxJeu([{"code": "c"}])
    )
    assert list(telechargement.lecteur_hugging_face(SOURCES["code_python"])) == [{"code": "c"}]
    (args, kwargs), = appels
    # Le script de chargement du dépôt n'est pas exécuté : on lit les fichiers parquet.
    assert args == ("parquet",)
    assert kwargs["data_files"] == "hf://datasets/codeparrot/github-code-clean/data/*.parquet"
    assert kwargs["streaming"] is True and kwargs["split"] == "train"


# --- Sous-commande ------------------------------------------------------------------


def test_sous_commande_donnees(tmp_path, monkeypatch, capsys):
    from forge.donnees import telechargement

    monkeypatch.setenv("FORGE_DONNEES", str(tmp_path))
    appels = []

    def faux_telecharger(source, octets_max, dossier, lecteur=None, **options):
        appels.append((source.nom, octets_max, dossier))
        dossier.mkdir(parents=True, exist_ok=True)
        (dossier / ".complet").write_text("", encoding="utf-8")
        return dossier

    monkeypatch.setattr(telechargement, "telecharger", faux_telecharger)
    assert main(["donnees", "--octets", "1000", "--dossier", "essai"]) == 0
    assert appels == [
        ("web_fr", 750, tmp_path / "textes" / "essai" / "web_fr"),
        ("wikipedia_fr", 100, tmp_path / "textes" / "essai" / "wikipedia_fr"),
        ("code_python", 150, tmp_path / "textes" / "essai" / "code_python"),
    ]
    sortie = capsys.readouterr().out
    assert "web_fr" in sortie and "code_python" in sortie
    # Le tokenizer lit ce que la commande a écrit.
    from forge.tokenizer.apprentissage import dossier_des_textes, verifier_dossier

    verifier_dossier(dossier_des_textes(Path("essai")))
    # 300M se lit comme partout ailleurs : 1024² octets le Mo.
    appels.clear()
    assert main(["donnees", "--octets", "300M", "--dossier", "grand"]) == 0
    assert sum(octets for _, octets, _ in appels) == 300 * 1024**2


def test_sous_commande_donnees_leve_le_mode_hors_ligne(tmp_path, monkeypatch, capsys):
    from forge.donnees import telechargement

    monkeypatch.setenv("FORGE_DONNEES", str(tmp_path))
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.delenv("HF_DATASETS_OFFLINE", raising=False)
    vus = []

    def faux_telecharger(source, octets_max, dossier, lecteur=None, **options):
        import os

        vus.append(os.environ["HF_HUB_OFFLINE"])
        return dossier

    monkeypatch.setattr(telechargement, "telecharger", faux_telecharger)
    assert main(["donnees", "--octets", "1000", "--dossier", "essai"]) == 0
    # Le téléchargement tourne avec le réseau permis, et le dit.
    assert vus == ["0", "0", "0"]
    assert "HF_HUB_OFFLINE" in capsys.readouterr().out


def test_sous_commande_donnees_erreurs_en_francais(tmp_path, monkeypatch, capsys):
    from forge.donnees import telechargement

    monkeypatch.setenv("FORGE_DONNEES", str(tmp_path))

    def manque_de_place(*args, **kwargs):
        raise PlaceInsuffisante("Il manque 3,0 Go sur D:. Libère de la place, puis relance.")

    monkeypatch.setattr(telechargement, "telecharger", manque_de_place)
    assert main(["donnees", "--octets", "1M", "--dossier", "essai"]) == 1
    assert "Il manque 3,0 Go" in capsys.readouterr().err

    def reseau_coupe(*args, **kwargs):
        raise ConnectionError("réseau coupé")

    monkeypatch.setattr(telechargement, "telecharger", reseau_coupe)
    assert main(["donnees", "--octets", "1M", "--dossier", "essai"]) == 1
    erreur = capsys.readouterr().err
    assert "relance la même commande" in erreur and "Traceback" not in erreur

    def interrompu(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(telechargement, "telecharger", interrompu)
    assert main(["donnees", "--octets", "1M", "--dossier", "essai"]) == 130
    assert "relance la même commande" in capsys.readouterr().err

    # Sans --octets ou --dossier, argparse refuse (code 2).
    with pytest.raises(SystemExit) as sortie:
        main(["donnees", "--dossier", "essai"])
    assert sortie.value.code == 2
