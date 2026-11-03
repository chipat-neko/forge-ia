"""Tests du tokenizer de « ton IA » : pré-découpage, jetons spéciaux et BPE sur les octets."""

import gzip
import json
import re
import time
from collections import Counter
from pathlib import Path

import pytest

from forge.__main__ import construire_parseur, main, taille_en_octets
from forge.donnees.melange import MELANGE_PAR_DEFAUT, est_validation
from forge.donnees.nettoyage import empreinte_du_texte_nettoye
from forge.tokenizer import (
    MOTIF_TON_IA,
    PREMIER_SPECIAL,
    SPECIAUX,
    TAILLE_VOCABULAIRE,
    TokenizerOctets,
    entrainer_tokenizer,
    pre_decouper,
)
from forge.tokenizer.apprentissage import (
    DonneesManquantes,
    apprendre_depuis_dossier,
    lire_textes_du_melange,
)

DOSSIER_DONNEES_DE_TEST = Path(__file__).parent / "donnees"
TEXTE_DE_TEST = (DOSSIER_DONNEES_DE_TEST / "corpus_test.txt").read_text(encoding="utf-8")
# Une liste de textes, comme les documents lus dans les fragments de données.
CORPUS_DE_TEST = [TEXTE_DE_TEST]


def _lettres(n: int) -> str:
    """Écrit `n` avec les lettres de a à z (0 → « a », 25 → « z », 26 → « ba »)."""
    lettres = ""
    while True:
        n, reste = divmod(n, 26)
        lettres = chr(ord("a") + reste) + lettres
        if n == 0:
            return lettres


def _corpus_de_5_mo() -> list[str]:
    """Le corpus de test répété jusqu'à 5 Mo, avec un mot différent à chaque ligne.

    Sans ce mot qui change (« forgea », « forgeb »…), chaque répétition donnerait
    exactement les mêmes pré-mots : le corpus serait bien moins varié qu'un vrai.
    Chaque répétition est rangée comme un document à part.
    """
    lignes = TEXTE_DE_TEST.splitlines()
    documents: list[str] = []
    total = 0
    numero = 0
    while total < 5_000_000:
        morceaux = []
        for ligne in lignes:
            morceaux.append(f"{ligne} forge{_lettres(numero)}\n")
            numero += 1
        document = "".join(morceaux)
        documents.append(document)
        total += len(document.encode("utf-8"))
    return documents


CORPUS_5_MO = _corpus_de_5_mo()


# --- Les tests de la consigne -------------------------------------------------


def test_predecoupage():
    assert pre_decouper("L'atelier, c'est 2026 !") == ["L'", "atelier", ",", " c'", "est", " ", "202", "6", " !"]
    assert pre_decouper(" jusqu'à aujourd’hui") == [" jusqu'", "à", " aujourd’", "hui"]
    assert pre_decouper("def f(x):\n    return x**2\n") == ["def", " f", "(x", "):\n", "   ", " return", " x", "**", "2", "\n"]
    assert pre_decouper("Bonjour\r\n\r\nÇa va ? 🙂") == ["Bonjour", "\r\n\r\n", "Ça", " va", " ?", " 🙂"]


def test_speciaux():
    assert len(SPECIAUX) == 64 and SPECIAUX[1] == "<|fin_texte|>" and SPECIAUX[-1] == "<|reserve_45|>"


def test_premiere_fusion_et_departage():
    tok = entrainer_tokenizer(["abab abab"], taille_vocabulaire=256 + 64 + 1)
    assert tok.fusions == [(97, 98)]
    tok2 = entrainer_tokenizer(["ba\nab"], taille_vocabulaire=256 + 64 + 1)  # égalité : (a,b) avant (b,a)
    assert tok2.fusions == [(97, 98)]


TEXTES_BIZARRES = ["Ligne\r\nWindows", "🙂👍🏽 é è ê", "\tdef f():\n\t\treturn 1", "x" * 100_000,
                   "texte <|fin_texte|> au milieu", "", " ", "日本語", "\x00\x01"]


def test_aller_retour_exact_et_aucun_special():
    tok = entrainer_tokenizer(CORPUS_DE_TEST, taille_vocabulaire=1024)
    for t in TEXTES_BIZARRES:
        ids = tok.encoder(t)
        assert tok.decoder(ids) == t
        assert all(i < tok.premier_special for i in ids)


def test_determinisme_et_fichier(tmp_path):
    a = entrainer_tokenizer(CORPUS_DE_TEST, taille_vocabulaire=1024)
    b = entrainer_tokenizer(CORPUS_DE_TEST, taille_vocabulaire=1024)
    assert a.fusions == b.fusions
    a.enregistrer(tmp_path / "t.json")
    c = TokenizerOctets.charger(tmp_path / "t.json")
    assert c.encoder("Le forgeron frappe le métal.") == a.encoder("Le forgeron frappe le métal.")
    assert c.id_special("<|fin_texte|>") == a.id_special("<|fin_texte|>") == a.premier_special + 1


def test_vitesse_apprentissage():
    t0 = time.perf_counter(); entrainer_tokenizer(CORPUS_5_MO, taille_vocabulaire=256 + 64 + 2000)
    assert time.perf_counter() - t0 < 120


# --- Pré-découpage et jetons spéciaux -----------------------------------------


def test_motif_exact_et_compatible_javascript():
    assert MOTIF_TON_IA == (
        r"[^\r\n\p{L}\p{N}]?\p{L}+(?:['’](?=\p{L}))?|\p{N}{1,3}| ?[^\p{White_Space}\p{L}\p{N}]+[\r\n]*"
        r"|\p{White_Space}*[\r\n]+|\p{White_Space}+(?!\P{White_Space})|\p{White_Space}+"
    )
    # Ni quantificateur possessif (« a++ », « a*+ », « a?+ », « a{1,3}+ ») ni groupe
    # atomique (« (?> ») : JavaScript ne les connaît pas. (« \p{L}+ » est un « + » ordinaire.)
    assert re.search(r"[*+?]\+|\{\d+(?:,\d*)?\}\+|\(\?>", MOTIF_TON_IA) is None


def test_predecoupage_ne_perd_aucun_caractere():
    # Espaces insécables (U+00A0, U+202F), accents combinants, tabulations…
    for texte in TEXTES_BIZARRES + [TEXTE_DE_TEST, "« Bonjour » ; l’été !", "été", "a b"]:
        assert "".join(pre_decouper(texte)) == texte


def test_identifiants_des_speciaux():
    assert TAILLE_VOCABULAIRE == 32768 and PREMIER_SPECIAL == 32704
    assert SPECIAUX[:3] == ("<|debut_texte|>", "<|fin_texte|>", "<|bourrage|>")
    assert SPECIAUX[17] == "<|trou_milieu|>" and SPECIAUX[18] == "<|reserve_00|>"
    assert len(set(SPECIAUX)) == 64
    plein = TokenizerOctets([], taille_vocabulaire=TAILLE_VOCABULAIRE)
    assert plein.premier_special == PREMIER_SPECIAL
    assert plein.id_special("<|debut_texte|>") == 32704
    assert plein.id_special("<|fin_texte|>") == 32705
    assert plein.id_special("<|reserve_45|>") == 32767
    with pytest.raises(KeyError, match="inconnu"):
        plein.id_special("<|fin|>")


# --- Apprentissage -------------------------------------------------------------


def _fusionner_naif(mot: tuple[int, ...], paire: tuple[int, int], nouveau: int) -> tuple[int, ...]:
    resultat = []
    i = 0
    while i < len(mot):
        if i + 1 < len(mot) and (mot[i], mot[i + 1]) == paire:
            resultat.append(nouveau)
            i += 2
        else:
            resultat.append(mot[i])
            i += 1
    return tuple(resultat)


def _entrainer_naif(textes: list[str], nb_fusions: int) -> list[tuple[int, int]]:
    """Référence lente et évidente : on recompte toutes les paires à chaque fusion."""
    mots: Counter[tuple[int, ...]] = Counter()
    for texte in textes:
        for morceau in pre_decouper(texte):
            mots[tuple(morceau.encode("utf-8"))] += 1
    octets = {i: bytes([i]) for i in range(256)}
    fusions: list[tuple[int, int]] = []
    for rang in range(nb_fusions):
        paires: Counter[tuple[int, int]] = Counter()
        for mot, frequence in mots.items():
            for paire in zip(mot, mot[1:]):
                paires[paire] += frequence
        if not paires:
            break
        meilleure = min(paires, key=lambda p: (-paires[p], octets[p[0]], octets[p[1]], p))
        nouveau = 256 + rang
        fusions.append(meilleure)
        octets[nouveau] = octets[meilleure[0]] + octets[meilleure[1]]
        mots = Counter({_fusionner_naif(m, meilleure, nouveau): f for m, f in mots.items()})
    return fusions


def test_apprentissage_identique_a_la_methode_naive():
    # Le comptage incrémental (index et tas) doit donner exactement les fusions
    # de la méthode qui recompte tout, égalités comprises.
    assert entrainer_tokenizer(CORPUS_DE_TEST, 256 + 64 + 300).fusions == _entrainer_naif(CORPUS_DE_TEST, 300)
    # Paires de deux symboles identiques qui se chevauchent (« aaa »), répétitions,
    # caractères de plusieurs octets ; on va jusqu'à épuiser toutes les paires.
    pieges = ["aaaa aaa aa a aaaaaaa", "abababab baba abab", "xxxxxxxxxxx", "éééé ééé", "🙂🙂🙂🙂 🙂"]
    tok = entrainer_tokenizer(pieges, 256 + 64 + 200)
    attendu = _entrainer_naif(pieges, 200)
    assert len(attendu) < 200 and tok.fusions == attendu


def test_une_chaine_seule_est_un_texte():
    # Une chaîne passée seule n'est pas lue caractère par caractère.
    assert entrainer_tokenizer("abab abab", 256 + 64 + 1).fusions == [(97, 98)]


def test_taille_trop_petite():
    with pytest.raises(ValueError, match="320"):
        entrainer_tokenizer(["abc"], taille_vocabulaire=300)
    with pytest.raises(ValueError, match="65 536"):
        TokenizerOctets([], taille_vocabulaire=70_000)


def test_journal_de_progression():
    lignes: list[str] = []
    entrainer_tokenizer(CORPUS_DE_TEST, 256 + 64 + 1000, journal=lignes.append)
    assert any("1000 fusions sur 1000" in ligne for ligne in lignes)


# --- Encodage et décodage ------------------------------------------------------


def test_encodage_rejoue_les_fusions_dans_l_ordre():
    tok = entrainer_tokenizer(CORPUS_DE_TEST, 256 + 64 + 300)
    texte = TEXTE_DE_TEST[:4000]
    attendu: list[int] = []
    for morceau in pre_decouper(texte):
        mot = tuple(morceau.encode("utf-8"))
        for rang, paire in enumerate(tok.fusions):
            mot = _fusionner_naif(mot, paire, 256 + rang)
        attendu.extend(mot)
    assert tok.encoder(texte) == attendu
    assert tok.encoder(texte) == attendu  # deuxième passage : tout vient du cache


def test_decoder():
    tok = entrainer_tokenizer(CORPUS_DE_TEST, 256 + 64 + 300)
    assert tok.decoder(tok.encoder("forgé à l’atelier")) == "forgé à l’atelier"
    # Suite d'octets incomplète (« é » coupé après son premier octet) : caractère de remplacement.
    assert tok.decoder([0xC3]) == "�"
    assert tok.decoder(list("é".encode("utf-8"))) == "é"
    # Un jeton spécial se décode en son nom.
    assert tok.decoder([tok.id_special("<|fin_texte|>")]) == "<|fin_texte|>"
    for mauvais in (-1, tok.taille_vocabulaire, 10**9):
        with pytest.raises(ValueError, match="identifiant"):
            tok.decoder([mauvais])


def test_octets_du_jeton_et_identifiants_libres():
    # « abab abab » n'offre que 3 fusions : ab, abab, puis « espace + abab ».
    lignes: list[str] = []
    tok = entrainer_tokenizer(["abab abab"], 256 + 64 + 5, journal=lignes.append)
    assert tok.fusions == [(97, 98), (256, 256), (32, 257)]
    assert any("plus aucune paire" in ligne for ligne in lignes)
    assert tok.octets_du_jeton(97) == b"a"
    assert tok.octets_du_jeton(256) == b"ab"
    assert tok.octets_du_jeton(258) == b" abab"
    # Les spéciaux gardent les 64 derniers identifiants ; 259 et 260 restent libres.
    assert tok.premier_special == 261 and tok.id_special("<|debut_texte|>") == 261
    assert tok.octets_du_jeton(tok.id_special("<|pensee|>")) == "<|pensee|>".encode("utf-8")
    for libre in (259, 260):
        with pytest.raises(ValueError, match="identifiant"):
            tok.octets_du_jeton(libre)
        with pytest.raises(ValueError, match="identifiant"):
            tok.decoder([97, libre])


def test_texte_non_utf8():
    tok = entrainer_tokenizer(["abab abab"], 256 + 64 + 1)
    with pytest.raises(ValueError, match="UTF-8"):
        tok.encoder("moitié \ud800 de paire")


# --- Fichier -------------------------------------------------------------------


def test_format_du_fichier(tmp_path):
    tok = entrainer_tokenizer(CORPUS_DE_TEST, 256 + 64 + 50)
    tok.nom = "essai"
    chemin = tmp_path / "t.json"
    tok.enregistrer(chemin)
    contenu = json.loads(chemin.read_text(encoding="utf-8"))
    assert set(contenu) == {"version", "nom", "motif", "fusions", "speciaux", "taille_vocabulaire"}
    assert contenu["version"] == 1 and contenu["nom"] == "essai" and contenu["motif"] == MOTIF_TON_IA
    assert contenu["taille_vocabulaire"] == 370
    assert contenu["fusions"] == [list(p) for p in tok.fusions]
    assert contenu["speciaux"] == {nom: 306 + i for i, nom in enumerate(SPECIAUX)}
    assert b"\r\n" not in chemin.read_bytes()  # même fichier sous Windows et sous Linux
    assert not list(tmp_path.glob("*.tmp"))
    assert TokenizerOctets.charger(chemin).nom == "essai"
    # Deux enregistrements du même tokenizer donnent le même fichier, octet pour octet.
    tok.enregistrer(tmp_path / "u.json")
    assert (tmp_path / "u.json").read_bytes() == chemin.read_bytes()


@pytest.mark.parametrize(
    ("cle", "valeur", "message"),
    [
        ("version", 2, "version"),
        ("motif", r"\p{L}+", "motif"),
        ("fusions", [[97, 98], [97, 98]], "deux fois"),
        ("fusions", [[97, 300]], "fusion"),
        ("speciaux", {"<|fin_texte|>": 5}, "spéciaux"),
    ],
)
def test_fichier_refuse(tmp_path, cle, valeur, message):
    chemin = tmp_path / "t.json"
    entrainer_tokenizer(["abab abab"], 256 + 64 + 2).enregistrer(chemin)
    contenu = json.loads(chemin.read_text(encoding="utf-8"))
    contenu[cle] = valeur
    chemin.write_text(json.dumps(contenu), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        TokenizerOctets.charger(chemin)


# --- Apprentissage sur les fragments de données et sous-commande ---------------


def _ecrire_fragment(chemin: Path, textes: list[str]) -> None:
    with gzip.open(chemin, "wt", encoding="utf-8") as fichier:
        for texte in textes:
            fichier.write(json.dumps({"texte": texte}, ensure_ascii=False) + "\n")


def _faux_dossier(racine: Path, complet: bool = True) -> Path:
    """Un faux téléchargement : chaque document fait 50 octets et dit d'où il vient."""
    dossier = racine / "textes" / "essai"
    for source, nombre in (("web_fr", 20), ("wikipedia_fr", 5), ("code_python", 5)):
        (dossier / source).mkdir(parents=True)
        textes = [f"{source} {i:03d} é ".ljust(49, "x") for i in range(nombre)]
        assert all(len(t.encode("utf-8")) == 50 for t in textes)
        # Deux fragments, lus dans l'ordre de leur nom.
        _ecrire_fragment(dossier / source / "fragment-00001.jsonl.gz", textes[nombre // 2 :])
        _ecrire_fragment(dossier / source / "fragment-00000.jsonl.gz", textes[: nombre // 2])
        if complet:
            (dossier / source / ".complet").write_text("", encoding="utf-8")
    return dossier


def test_apprendre_depuis_dossier(tmp_path, monkeypatch):
    monkeypatch.setenv("FORGE_DONNEES", str(tmp_path))
    dossier = _faux_dossier(tmp_path)
    # 1 000 octets : 750 de web (15 documents), 100 de Wikipédia (2), 150 de code (3).
    textes = list(lire_textes_du_melange(dossier, 1000))
    assert [tuple(t.split()[:2]) for t in textes] == (
        [("web_fr", f"{i:03d}") for i in range(15)]
        + [("wikipedia_fr", f"{i:03d}") for i in range(2)]
        + [("code_python", f"{i:03d}") for i in range(3)]
    )
    assert len(list(lire_textes_du_melange(dossier, None))) == 30
    sortie = tmp_path / "sortie" / "tok.json"
    tok = apprendre_depuis_dossier(Path("essai"), 256 + 64 + 10, "essai-v0", sortie, 1000)
    assert tok.nom == "essai-v0" and len(tok.fusions) == 10
    relu = TokenizerOctets.charger(sortie)
    assert relu.fusions == tok.fusions and relu.nom == "essai-v0"
    # Le tokenizer n'apprend que sur les documents d'apprentissage : ici, « code_python 000 »
    # est un document de validation, il est sauté et le suivant prend sa place dans le volume.
    textes = list(lire_textes_du_melange(dossier, 1000, ecarter_validation=True))
    assert ("code_python", "000") not in [tuple(t.split()[:2]) for t in textes] and len(textes) == 20
    assert tok.fusions == entrainer_tokenizer(textes, 256 + 64 + 10).fusions


def test_dossier_incomplet(tmp_path, monkeypatch):
    monkeypatch.setenv("FORGE_DONNEES", str(tmp_path))
    _faux_dossier(tmp_path, complet=False)
    with pytest.raises(DonneesManquantes, match="complet"):
        apprendre_depuis_dossier(Path("essai"), 330, "x", tmp_path / "t.json", None)
    with pytest.raises(DonneesManquantes, match="python -m forge donnees"):
        apprendre_depuis_dossier(Path("absent"), 330, "x", tmp_path / "t.json", None)


def _documents_a_motif(valides: bool, nombre: int, motif: str = "QJQJQJ") -> list[str]:
    """`nombre` documents (de 200 caractères ou plus) pleins de `motif`, tous de validation ou aucun.

    Le choix de la validation ne dépend que de l'empreinte du texte : on cherche, parmi des
    documents qui ne diffèrent que par un numéro, ceux qui tombent du côté voulu.
    """
    trouves: list[str] = []
    numero = 0
    while len(trouves) < nombre:
        texte = f"{motif} document {numero:05d} {motif} " * 8
        if est_validation(empreinte_du_texte_nettoye(texte)) == valides:
            trouves.append(texte)
        numero += 1
    return trouves


def _dossier_avec_validation(racine: Path) -> tuple[Path, list[str], list[str]]:
    """Un faux téléchargement dont chaque source mêle des documents de validation et d'apprentissage.

    Les documents de validation sont pleins de « QJQJQJ » : s'ils servaient à l'apprentissage,
    la paire (Q, J) serait fusionnée. Renvoie le dossier, les textes d'apprentissage et ceux de validation.
    """
    dossier = racine / "textes" / "mixte"
    apprentissage = [t for t in _documents_a_motif(False, 60, motif="forgeron")]
    validation = _documents_a_motif(True, 6)
    for source in ("web_fr", "wikipedia_fr", "code_python"):
        (dossier / source).mkdir(parents=True)
        # Un document de validation sur dix, en tête, au milieu et en queue de source.
        textes = validation[:2] + apprentissage[:20] + validation[2:4] + apprentissage[20:40] + validation[4:] + apprentissage[40:]
        _ecrire_fragment(dossier / source / "fragment-00000.jsonl.gz", textes)
        (dossier / source / ".complet").write_text("", encoding="utf-8")
    assert all(est_validation(empreinte_du_texte_nettoye(t)) for t in validation)
    assert not any(est_validation(empreinte_du_texte_nettoye(t)) for t in apprentissage)
    return dossier, apprentissage, validation


def test_les_documents_de_validation_ne_servent_pas_a_apprendre(tmp_path, monkeypatch):
    monkeypatch.setenv("FORGE_DONNEES", str(tmp_path))
    dossier, apprentissage, validation = _dossier_avec_validation(tmp_path)

    # Le lecteur, quand on le lui demande, saute ces documents sans les compter dans le volume.
    lignes: list[str] = []
    lus = list(lire_textes_du_melange(dossier, None, lignes.append, ecarter_validation=True))
    assert lus == apprentissage * 3
    assert sum("6 documents de validation écartés" in ligne for ligne in lignes) == 3
    # Sans cette demande, il lit tout, comme avant.
    assert len(list(lire_textes_du_melange(dossier, None))) == 3 * (len(apprentissage) + len(validation))
    octets_par_texte = len(apprentissage[0].encode("utf-8"))
    budget_web = 10 * octets_par_texte  # 10 documents de web (75 %) : 10 d'apprentissage, validation sautée
    total = round(budget_web / 0.75)
    lus = list(lire_textes_du_melange(dossier, total, ecarter_validation=True))
    # Web : 10 documents ; Wikipédia (352 octets) : 2 ; code (528 octets) : 2 ; aucun n'est de validation.
    # Si les documents de validation comptaient dans le volume, le web en donnerait moins de 10.
    assert lus == apprentissage[:10] + apprentissage[:2] + apprentissage[:2]

    # L'apprentissage du tokenizer lit ainsi : la paire (Q, J) n'est jamais fusionnée.
    sortie = tmp_path / "sortie" / "tok.json"
    tok = apprendre_depuis_dossier(Path("mixte"), 256 + 64 + 50, "mixte-v0", sortie, None)
    assert tok.fusions == entrainer_tokenizer(apprentissage * 3, 256 + 64 + 50).fusions
    assert not any(b"QJ" in tok.octets_du_jeton(256 + rang) for rang in range(len(tok.fusions)))
    # Preuve que le test mord : appris sur tout, le tokenizer fusionne bien « QJ ».
    sur_tout = entrainer_tokenizer(list(lire_textes_du_melange(dossier, None)), 256 + 64 + 50)
    assert any(b"QJ" in sur_tout.octets_du_jeton(256 + rang) for rang in range(len(sur_tout.fusions)))


def test_apprentissage_trop_court_echoue_sans_rien_ecrire(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FORGE_DONNEES", str(tmp_path))
    _faux_dossier(tmp_path)
    sortie = tmp_path / "sortie" / "tok.json"
    # Ces 30 documents de 50 octets n'ont pas 10 000 fusions à donner.
    with pytest.raises(ValueError, match=r"fusions sur les 10000 voulues") as erreur:
        apprendre_depuis_dossier(Path("essai"), 256 + 64 + 10_000, "court", sortie, None)
    assert "plus de textes" in str(erreur.value) and "--taille" in str(erreur.value)
    assert not sortie.exists() and not list(sortie.parent.glob("*"))
    # Un fichier déjà là n'est pas écrasé par un tokenizer trop court.
    sortie.parent.mkdir(parents=True)
    sortie.write_text("ancien", encoding="utf-8")
    code = main(["tokenizer", "--donnees", "essai", "--taille", str(256 + 64 + 10_000), "--sortie", str(sortie)])
    assert code == 1
    erreur_affichee = capsys.readouterr().err
    assert erreur_affichee.startswith("Erreur : ") and "fusions" in erreur_affichee
    assert sortie.read_text(encoding="utf-8") == "ancien"


def test_sous_commande_tokenizer(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FORGE_DONNEES", str(tmp_path))
    _faux_dossier(tmp_path)
    sortie = tmp_path / "tok.json"
    code = main(["tokenizer", "--donnees", "essai", "--taille", "330", "--nom", "essai-v0",
                 "--sortie", str(sortie), "--octets-max", "1K"])
    assert code == 0
    tok = TokenizerOctets.charger(sortie)
    assert tok.nom == "essai-v0" and tok.taille_vocabulaire == 330
    assert "enregistré" in capsys.readouterr().out
    # Données absentes : message français et code de sortie 1, sans trace Python.
    assert main(["tokenizer", "--donnees", "absent", "--sortie", str(sortie)]) == 1
    assert "python -m forge donnees" in capsys.readouterr().err


# --- Mesure de la compression ---------------------------------------------------


MOTIFS_PAR_SOURCE = {"web_fr": "forgeron", "wikipedia_fr": "enclume", "code_python": "def fusionner"}


def _dossier_pour_compression(racine: Path) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Un faux téléchargement où chaque source a son vocabulaire et mêle validation et apprentissage.

    Renvoie, par source, les documents d'apprentissage et ceux de validation, dans l'ordre où ils
    sont rangés dans le fragment (un document de validation toutes les sept lignes environ).
    """
    dossier = racine / "textes" / "compression"
    apprentissage: dict[str, list[str]] = {}
    validation: dict[str, list[str]] = {}
    for source, motif in MOTIFS_PAR_SOURCE.items():
        apprentissage[source] = _documents_a_motif(False, 30, motif)
        validation[source] = _documents_a_motif(True, 4, motif)
        a_ranger = iter(validation[source])
        textes: list[str] = []
        for i, texte in enumerate(apprentissage[source]):
            textes.append(texte)
            if i % 7 == 3:
                textes.append(next(a_ranger))
        (dossier / source).mkdir(parents=True)
        _ecrire_fragment(dossier / source / "fragment-00000.jsonl.gz", textes)
        (dossier / source / ".complet").write_text("", encoding="utf-8")
    return apprentissage, validation


def _premiers_jusqu_a(textes: list[str], minimum: int) -> list[str]:
    """Les premiers documents entiers, jusqu'à atteindre `minimum` octets."""
    pris: list[str] = []
    octets = 0
    for texte in textes:
        pris.append(texte)
        octets += len(texte.encode("utf-8"))
        if octets >= minimum:
            break
    return pris


def _tokenizer_de_mesure() -> TokenizerOctets:
    return entrainer_tokenizer(CORPUS_DE_TEST, 256 + 64 + 100)


def test_mesurer_compression_sur_la_validation(tmp_path):
    from forge.tokenizer.compression import mesurer_compression

    _, validation = _dossier_pour_compression(tmp_path)
    tok = _tokenizer_de_mesure()
    dossier = tmp_path / "textes" / "compression"
    resultat = mesurer_compression(tok, dossier, 600)
    assert resultat["partie"] == "validation" and resultat["octets_par_source"] == 600
    assert resultat["tokenizer"] == tok.nom
    total_octets = total_jetons = total_documents = 0
    jetons_par_octet = 0.0
    for source, part in MELANGE_PAR_DEFAUT.items():
        pris = _premiers_jusqu_a(validation[source], 600)
        octets = sum(len(t.encode("utf-8")) for t in pris)
        jetons = sum(len(tok.encoder(t)) for t in pris)
        mesure = resultat["sources"][source]
        # Seuls les documents de validation comptent, entiers, dans l'ordre, jusqu'à 600 octets.
        assert 1 < len(pris) < len(validation[source])
        assert mesure["documents"] == len(pris)
        assert mesure["octets"] == octets and mesure["jetons"] == jetons
        assert mesure["caracteres"] == sum(len(t) for t in pris)
        assert mesure["octets_par_jeton"] == pytest.approx(octets / jetons)
        assert mesure["caracteres_par_jeton"] == pytest.approx(mesure["caracteres"] / jetons)
        jetons_par_octet += part * jetons / octets
        total_octets, total_jetons, total_documents = total_octets + octets, total_jetons + jetons, total_documents + len(pris)
    # Le mélange pèse les sources par leurs parts (en octets) ; « bout à bout » les compte à égalité.
    assert resultat["melange"]["octets_par_jeton"] == pytest.approx(1 / jetons_par_octet)
    assert resultat["bout_a_bout"] == {
        "documents": total_documents,
        "octets": total_octets,
        "jetons": total_jetons,
        "octets_par_jeton": pytest.approx(total_octets / total_jetons),
    }
    # Les sources n'ont pas le même vocabulaire : leurs compressions diffèrent.
    assert len({mesure["octets_par_jeton"] for mesure in resultat["sources"].values()}) == 3


def test_mesurer_compression_sur_l_apprentissage_et_refus(tmp_path):
    from forge.tokenizer.compression import mesurer_compression

    apprentissage, validation = _dossier_pour_compression(tmp_path)
    tok = _tokenizer_de_mesure()
    dossier = tmp_path / "textes" / "compression"
    resultat = mesurer_compression(tok, dossier, 600, partie="apprentissage")
    assert resultat["partie"] == "apprentissage"
    for source in MELANGE_PAR_DEFAUT:
        pris = _premiers_jusqu_a(apprentissage[source], 600)
        assert resultat["sources"][source]["documents"] == len(pris)
        assert resultat["sources"][source]["octets"] == sum(len(t.encode("utf-8")) for t in pris)
    # Pas assez de validation : la mesure échoue, elle ne se contente pas de moins.
    with pytest.raises(ValueError, match=r"ne contient que .* octets de documents de validation") as erreur:
        mesurer_compression(tok, dossier, 100_000)
    assert "web_fr" in str(erreur.value) and "python -m forge donnees --parts" in str(erreur.value)
    with pytest.raises(ValueError, match="positif"):
        mesurer_compression(tok, dossier, 0)
    with pytest.raises(ValueError, match="validation.*apprentissage"):
        mesurer_compression(tok, dossier, 600, partie="test")
    # Un téléchargement inachevé n'est jamais mesuré.
    (dossier / "web_fr" / ".complet").unlink()
    with pytest.raises(DonneesManquantes, match="complet"):
        mesurer_compression(tok, dossier, 600)


def test_sous_commande_compression(tmp_path, monkeypatch, capsys):
    from forge.tokenizer.compression import mesurer_compression

    monkeypatch.setenv("FORGE_DONNEES", str(tmp_path))
    _dossier_pour_compression(tmp_path)
    tok = _tokenizer_de_mesure()
    fichier = tmp_path / "tok.json"
    tok.enregistrer(fichier)
    attendu = mesurer_compression(TokenizerOctets.charger(fichier), tmp_path / "textes" / "compression", 600)

    assert main(["compression", "--donnees", "compression", "--tokenizer", str(fichier), "--octets", "600"]) == 0
    sortie = capsys.readouterr().out
    for source in MELANGE_PAR_DEFAUT:
        ligne = next(ligne for ligne in sortie.splitlines() if ligne.startswith(source))
        mesure = attendu["sources"][source]
        assert f"{mesure['octets_par_jeton']:.2f}".replace(".", ",") in ligne
        assert f"{mesure['caracteres_par_jeton']:.2f}".replace(".", ",") in ligne
        assert str(mesure["documents"]) in ligne
    assert "Mélange" in sortie and f"{attendu['melange']['octets_par_jeton']:.2f}".replace(".", ",") in sortie
    assert "bout à bout" in sortie and "documents de validation" in sortie
    # `--partie apprentissage` mesure les autres documents.
    code = main(["compression", "--donnees", "compression", "--tokenizer", str(fichier), "--octets", "600",
                 "--partie", "apprentissage"])
    assert code == 0 and "documents d'apprentissage" in capsys.readouterr().out
    # Erreurs : message français sur stderr, code 1, sans trace Python.
    assert main(["compression", "--donnees", "absent", "--tokenizer", str(fichier)]) == 1
    assert "python -m forge donnees" in capsys.readouterr().err
    assert main(["compression", "--donnees", "compression", "--tokenizer", str(fichier), "--octets", "10M"]) == 1
    erreur = capsys.readouterr().err
    assert erreur.startswith("Erreur : ") and "ne contient que" in erreur and "Traceback" not in erreur
    assert main(["compression", "--donnees", "compression", "--tokenizer", str(tmp_path / "absent.json")]) == 1
    assert "introuvable" in capsys.readouterr().err
    # Par défaut : le tokenizer figé du dépôt, et 1 Mo par source.
    choix = construire_parseur().parse_args(["compression", "--donnees", "x"])
    assert choix.octets == 1024**2 and choix.partie == "validation"
    assert Path(choix.tokenizer).name == "tokenizer-ton-ia-v1.json" and Path(choix.tokenizer).is_file()


def test_taille_en_octets():
    assert taille_en_octets("300M") == 300 * 1024**2
    assert taille_en_octets("1K") == 1024
    assert taille_en_octets("2g") == 2 * 1024**3
    assert taille_en_octets("12345") == 12345
    with pytest.raises(Exception, match="taille"):
        taille_en_octets("trois cents")
