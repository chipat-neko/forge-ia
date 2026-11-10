"""Les questions de MMMLU : tirage reproductible, format des questions, notes, et relevé de « mini » s'il est écrit.

Aucun test ne touche le réseau : les lignes du jeu sont données à la main (`lignes=`).
"""

import json
import os
import pathlib

import pytest
from forge.evaluation.qcm import QCM, scores_qcm
from modele_factice import petit_modele, tokenizer

from evaluation_pas_a_pas import qcm_exemples
from evaluation_pas_a_pas.qcm_exemples import ADRESSE, LICENCE, exemples_mmmlu, noter_exemples, qcm_de_la_ligne

PROJET = pathlib.Path(__file__).resolve().parents[1]


def ligne(numero: int, bonne: str = "B") -> dict:
    return {
        "Unnamed: 0": numero,
        "Question": f"  Combien font {numero} + {numero} ?  ",
        "A": str(numero),
        "B": str(2 * numero),
        "C": str(3 * numero),
        "D": f"  {4 * numero}  ",
        "Answer": bonne,
        "Subject": "mathématiques",
    }


JEU = [ligne(i, "ABCD"[i % 4]) for i in range(1, 101)]


def test_qcm_de_la_ligne():
    qcm = qcm_de_la_ligne(ligne(3, "B"))
    assert qcm.contexte == "Question : Combien font 3 + 3 ?\nRéponse :"
    assert qcm.choix == [" 3", " 6", " 9", " 12"]  # chaque choix commence par son espace, sans espaces en trop
    assert qcm.bonne == 1
    assert qcm_de_la_ligne(ligne(3, " d ")).bonne == 3  # la lettre est nettoyée, minuscule comprise


def test_qcm_de_la_ligne_refuse_une_lettre_inconnue():
    with pytest.raises(ValueError, match="lettres A à D"):
        qcm_de_la_ligne(ligne(3, "E"))


def test_exemples_sont_reproductibles_et_dans_l_ordre_du_jeu():
    a, b = exemples_mmmlu(6, 0, lignes=JEU), exemples_mmmlu(6, 0, lignes=iter(JEU))
    assert a == b and len(a) == 6
    assert exemples_mmmlu(6, 1, lignes=JEU) != a  # une autre graine, d'autres questions
    nombres = [int(q.contexte.split()[4]) for q in a]  # « Question : Combien font N + N ?\nRéponse : »
    assert nombres == sorted(nombres) and len(set(nombres)) == 6
    assert all(q.contexte.startswith("Question : ") and q.contexte.endswith("\nRéponse :") for q in a)


def test_exemples_viennent_de_tout_le_jeu():
    # Un tirage de réservoir donne à chaque question la même chance : sur 100 tirages, on voit du début comme de la fin.
    vus = {int(q.contexte.split()[4]) for graine in range(100) for q in exemples_mmmlu(3, graine, lignes=JEU)}
    assert min(vus) <= 10 and max(vus) >= 90 and len(vus) > 60


def test_exemples_demandent_au_plus_ce_que_le_jeu_donne():
    assert len(exemples_mmmlu(100, 0, lignes=JEU)) == 100
    with pytest.raises(ValueError, match="n'a donné que 100 question"):
        exemples_mmmlu(101, 0, lignes=JEU)
    with pytest.raises(ValueError, match="au moins une question"):
        exemples_mmmlu(0, 0, lignes=JEU)


def test_exemples_ignorent_les_lignes_aux_choix_identiques_ou_vides():
    doublon = {**ligne(1), "A": "même", "D": "même"}
    vide = {**ligne(2), "C": "  "}
    jeu = [doublon, vide, *JEU[2:12]]
    choisies = exemples_mmmlu(10, 0, lignes=jeu)
    assert len(choisies) == 10 and all(len(set(q.choix)) == 4 for q in choisies)
    with pytest.raises(ValueError, match="n'a donné que 10 question"):
        exemples_mmmlu(11, 0, lignes=jeu)


def test_exemples_levent_le_mode_hors_ligne_pour_la_lecture(monkeypatch):
    import datasets

    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("HF_DATASETS_OFFLINE", "0")
    monkeypatch.setattr(datasets, "load_dataset", lambda *a, **k: iter(JEU))
    exemples_mmmlu(2, 0)
    assert os.environ["HF_HUB_OFFLINE"] == "0" and os.environ["HF_DATASETS_OFFLINE"] == "0"


def test_exemples_lisent_le_jeu_en_flux(monkeypatch):
    # Sans `lignes`, le jeu vient de `load_dataset(..., streaming=True)`, configuration FR_FR.
    appels = []

    def faux_load_dataset(jeu, configuration, split, streaming):
        appels.append((jeu, configuration, split, streaming))
        return iter(JEU)

    import datasets

    monkeypatch.setattr(datasets, "load_dataset", faux_load_dataset)
    assert len(exemples_mmmlu(2, 0)) == 2
    assert appels == [("openai/MMMLU", "FR_FR", "test", True)]


def test_noter_exemples_egale_scores_qcm_et_dit_la_licence():
    modele, tok = petit_modele(), tokenizer()
    qcms = exemples_mmmlu(4, 0, lignes=JEU)
    note = noter_exemples(modele, tok, qcms)
    assert list(note) == ["jeu", "n", "justes", "hasard", "questions"]
    assert note["jeu"]["licence"] == LICENCE == "MIT" and note["jeu"]["adresse"] == ADRESSE
    assert note["jeu"]["nom"] == "openai/MMMLU" and note["jeu"]["configuration"] == "FR_FR"
    assert note["n"] == 4 and note["hasard"] == 0.25
    attendus = scores_qcm(modele, tok, qcms)
    for q, qcm, scores in zip(note["questions"], qcms, attendus):
        assert q["scores"] == scores and q["contexte"] == qcm.contexte and q["choix"] == qcm.choix
        octets = [len(c.encode("utf-8")) for c in qcm.choix]
        assert q["scores_normalises"] == [s / o for s, o in zip(scores, octets)]
        assert q["prefere"] == max(range(4), key=lambda k: q["scores_normalises"][k])
        assert q["bonne"] == qcm.bonne and q["juste"] == (q["prefere"] == qcm.bonne)
    assert note["justes"] == sum(q["juste"] for q in note["questions"])
    json.dumps(note, allow_nan=False)  # écrivable en JSON


def test_noter_exemples_ne_fait_ecrire_aucun_mot():
    # Noter n'appelle jamais la génération : seul scores_qcm (une passe du modèle par lot) est utilisé.
    assert "generer" not in vars(qcm_exemples)


def test_le_releve_de_mini_a_sa_licence_et_son_adresse():
    chemin = PROJET / "mesures" / "qcm-mini.json"
    if not chemin.exists():
        pytest.skip("Le relevé des QCM de MMMLU n'est pas encore écrit (voir le README du projet).")
    releve = json.loads(chemin.read_text(encoding="utf-8"))
    assert releve["nom"] == "ton-ia-mini" and releve["appareil"] == "cpu"
    assert releve["jeu"]["licence"] == "MIT" and releve["jeu"]["adresse"] == "https://huggingface.co/datasets/openai/MMMLU"
    assert releve["jeu"]["lu_le"] == releve["releve_le"] and releve["jeu"]["licence_verifiee_le"]
    assert releve["n"] == len(releve["questions"]) == 6
    octets = chemin.read_bytes()
    assert b"\r" not in octets and octets.endswith(b"}\n")
    assert octets.decode("utf-8") == json.dumps(releve, ensure_ascii=False, allow_nan=False, indent=1) + "\n"
