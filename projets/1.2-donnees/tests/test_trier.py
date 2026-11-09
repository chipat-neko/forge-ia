"""Le tri des textes : court, doublon, licence, langage, et la même réponse que forge."""

import gzip
import json
from pathlib import Path

from forge.donnees.sources import SOURCES
from forge.donnees.telechargement import telecharger

from donnees_pas_a_pas.trier import Verdict, compter_raisons, lire_jsonl, trier

PROJET = Path(__file__).resolve().parent.parent
EXEMPLES = PROJET / "exemples"


def lire(nom: str) -> list[dict]:
    return list(lire_jsonl(EXEMPLES / nom))


def test_court_doublon_licence():
    v = list(trier(lire("web.jsonl"), SOURCES["web_fr"]))
    assert v[0].raison == "trop court" and v[1].raison == "gardé"
    assert v[2].raison == "doublon" and v[2].empreinte == v[1].empreinte
    assert v[3].raison == "doublon"
    c = list(trier(lire("code.jsonl"), SOURCES["code_python"]))
    assert [x.raison for x in c] == ["gardé", "licence", "langage"]


def test_un_verdict_dit_ce_qu_il_garde():
    v = list(trier(lire("web.jsonl"), SOURCES["web_fr"]))
    assert isinstance(v[1], Verdict)
    # Gardé : le texte nettoyé, son empreinte, et la place (entraînement ou validation).
    assert v[1].garde and v[1].texte is not None and v[1].empreinte is not None
    assert isinstance(v[1].validation, bool)
    # Écarté : rien de tout cela, sauf l'empreinte d'un doublon.
    assert not v[0].garde and v[0].texte is None and v[0].empreinte is None and v[0].validation is None
    assert not v[2].garde and v[2].texte is None and v[2].validation is None


def test_les_pieges_du_nettoyage_des_exemples():
    v = list(trier(lire("web.jsonl"), SOURCES["web_fr"]))
    brut = lire("web.jsonl")
    # Les contrôles partent, la tabulation et le retour à la ligne restent.
    controles = v[4].texte
    assert controles is not None and "\x00" not in controles and "\t" in controles and "\r" not in controles
    # Le « é » en deux morceaux devient un seul caractère (forme NFC).
    accent = v[5].texte
    assert accent is not None and "\u0301" not in accent and "café" in accent
    # Un emoji compte pour un caractère, et les moitiés de paires disparaissent.
    assert v[6].texte is not None and "\U0001f600" in v[6].texte
    assert v[7].texte is not None and not any(0xD800 <= ord(c) <= 0xDFFF for c in v[7].texte)
    assert any(0xD800 <= ord(c) <= 0xDFFF for c in brut[7]["text"])
    # 200 caractères pile : gardé ; 199 : trop court ; 200 dont un U+00A0 final : 199 une fois nettoyé.
    assert [x.raison for x in v[8:11]] == ["gardé", "trop court", "trop court"]
    # Les blancs de fin ne changent pas l'empreinte : doublon du texte 2.
    assert v[12].raison == "doublon" and v[12].empreinte == v[1].empreinte


def test_compter_raisons():
    v = list(trier(lire("web.jsonl"), SOURCES["web_fr"]))
    comptes = compter_raisons(v)
    assert list(comptes) == ["gardé", "trop court", "doublon", "licence", "langage"]
    assert sum(comptes.values()) == len(v)
    assert comptes["gardé"] == sum(x.garde for x in v)
    assert comptes["licence"] == comptes["langage"] == 0
    assert compter_raisons([]) == {"gardé": 0, "trop court": 0, "doublon": 0, "licence": 0, "langage": 0}


def test_une_colonne_absente_ou_pas_du_texte_est_trop_courte():
    v = list(trier([{"text": 12}, {"autre": "x" * 300}, {"text": None}], SOURCES["web_fr"]))
    assert [x.raison for x in v] == ["trop court"] * 3


def test_licence_et_langage_se_lisent_ainsi():
    code = "x = 1\n" * 60
    lignes = [
        {"code": code, "language": "Python", "license": "mit"},
        {"code": code, "language": "Python", "license": "MIT"},  # même texte : doublon, pas licence
        {"code": code, "language": "Python", "license": "gpl-2.0"},
        {"code": code, "language": "Python"},  # sans licence : « licence »
        {"code": code, "language": "Java", "license": "mit"},
        {"code": code, "language": "Java", "license": "gpl-2.0"},  # langage d'abord
        {"code": code},  # ni l'un ni l'autre : langage
    ]
    raisons = [v.raison for v in trier(lignes, SOURCES["code_python"])]
    assert raisons == ["gardé", "doublon", "licence", "licence", "langage", "langage", "langage"]


def test_trier_fait_comme_forge(tmp_path):
    # Mêmes textes gardés, dans le même ordre, que forge.donnees.telechargement.telecharger
    # avec un lecteur qui rend les exemples.
    for nom_source, fichier in [("web_fr", "web.jsonl"), ("code_python", "code.jsonl")]:
        source = SOURCES[nom_source]
        lignes = lire(fichier)
        dossier = telecharger(source, 10**9, tmp_path / nom_source, lecteur=lambda _s, lignes=lignes: iter(lignes))
        ecrits = []
        for fragment in sorted(dossier.glob("fragment-*.jsonl.gz")):
            with gzip.open(fragment, "rt", encoding="utf-8") as f:
                ecrits += [json.loads(ligne)["texte"] for ligne in f]
        gardes = [v.texte for v in trier(lignes, source) if v.garde]
        assert ecrits == gardes and len(gardes) > 0
