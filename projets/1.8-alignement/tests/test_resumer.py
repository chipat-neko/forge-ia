"""Les relevés que le projet tire des mesures du plan 7 : un rapport d'étape, des paires, un balayage.

Le rapport d'étape est fabriqué au format de `forge.evaluation.etape.evaluer_etape` (`version_du_rapport` 1) :
ton-ia-1.8 n'est pas encore évaluée quand ces tests s'écrivent. Les paires sont écrites comme `forge preferences`
les écrit (des fragments `paires/`, un jeu `dpo`), avec la référence que la DPO calcule.
"""

import json

import numpy as np
import pytest
from forge.affinage.empaquetage import Rangee
from forge.affinage.jeu import ecrire_jeu
from forge.evaluation.etape import MESURES_PAR_ETAPE, VERSION_DU_RAPPORT_D_ETAPE
from forge.fragments import SortieParFragments
from forge.tokenizer import TokenizerOctets

from alignement_pas_a_pas.poussee import TOKENIZER
from alignement_pas_a_pas.resumer import balayage, paires_exemples, resumer_etape

TOK = TokenizerOctets.charger(TOKENIZER)

ECHANTILLONS_18 = [
    {"invite": "Quelle est la capitale de la France ?", "texte": "Paris.", "pensee": None, "terminee": True},
    {"invite": "Qui es-tu ?", "texte": "Je suis ton IA, un modèle", "pensee": None, "terminee": False},
]
ECHANTILLONS_17 = [
    {"invite": "Quelle est la capitale de la France ?", "texte": "La France est un pays de l'Europe", "pensee": None, "terminee": False},
]


def victoire(taux: float, victoires: int, egalites: int, defaites: int, mots: float, mots_reference: float) -> dict:
    return {"victoires": victoires, "egalites": egalites, "defaites": defaites, "taux": taux, "mots_modele": mots, "mots_reference": mots_reference, "n": 200}


def mesures(perte: float, echantillons: list[dict], v: dict) -> dict:
    """Les mesures de l'étape 1.8, avec les clés de `forge evaluer-etape` (voir MESURES_PAR_ETAPE)."""
    return {
        "perte_conversation": {"perte": perte, "n": 64},
        "ifeval_fr": {"invite_stricte": 0.12, "consigne_stricte": 0.2, "n": 541},
        "tenue": {"terminee": 0.9, "fr": 0.95, "autre": 0.03, "indetermine": 0.02, "mots_moyens": 41.5, "n": 641},
        "oubli": {"perte": 2.6, "bits_par_octet": 0.9, "n": 64},
        "victoire": v,
        "echantillons": echantillons,
    }


def un_rapport(avec_reference: bool = True) -> dict:
    rapport = {
        "version_du_rapport": VERSION_DU_RAPPORT_D_ETAPE,
        "version": "ton-ia-1.8",
        "empreinte": "a" * 64,
        "mesures": mesures(1.43, ECHANTILLONS_18, victoire(0.7, 120, 40, 40, 38.0, 52.0)),
        "secondes": 812.4,
        "etape": "1.8",
        "date": "2026-11-25T09:15:31+01:00",
        "appareil": "cuda",
        "n_max": None,
    }
    if avec_reference:
        rapport["reference"] = {
            "version": "ton-ia-1.7",
            "empreinte": "b" * 64,
            "mesures": mesures(1.5, ECHANTILLONS_17, victoire(0.3, 40, 40, 120, 52.0, 38.0)),
            "secondes": 790.0,
        }
    return rapport


def ecrire(tmp_path, rapport: dict, nom: str = "rapport.json"):
    chemin = tmp_path / nom
    chemin.write_text(json.dumps(rapport), encoding="utf-8")
    return chemin


def test_resumer_etape(tmp_path):
    releve = resumer_etape(ecrire(tmp_path, un_rapport()))
    assert list(releve) == ["version", "etape", "releve_le", "mesures", "echantillons"]
    assert (releve["version"], releve["etape"], releve["releve_le"]) == ("ton-ia-1.8", "1.8", "2026-11-25")
    # Les mesures de l'étape 1.8 de forge, sans les échantillons, rangés à part : celles de 1.7 et « victoire ».
    assert list(releve["mesures"]) == [m for m in MESURES_PAR_ETAPE["1.8"] if m != "echantillons"]
    assert "victoire" in releve["mesures"]
    assert releve["echantillons"] == ECHANTILLONS_18


def test_resumer_etape_ne_recalcule_rien(tmp_path):
    rapport = un_rapport()
    releve = resumer_etape(ecrire(tmp_path, rapport))
    assert releve["mesures"] == {nom: m for nom, m in rapport["mesures"].items() if nom != "echantillons"}
    assert releve["mesures"]["victoire"]["taux"] == 0.7  # le nombre du rapport, à l'identique


def test_la_reference_est_resumee_a_son_tour(tmp_path):
    releve = resumer_etape(ecrire(tmp_path, un_rapport()), reference=True)
    assert (releve["version"], releve["etape"], releve["releve_le"]) == ("ton-ia-1.7", "1.8", "2026-11-25")
    assert releve["mesures"]["victoire"]["taux"] == 0.3  # le complément : la référence perd où 1.8 gagne
    assert releve["echantillons"] == ECHANTILLONS_17


def test_une_mesure_absente_reste_absente(tmp_path):
    rapport = un_rapport()
    rapport["mesures"]["victoire"] = {"absente": "il n'y a pas de version de référence"}
    assert resumer_etape(ecrire(tmp_path, rapport))["mesures"]["victoire"] == {"absente": "il n'y a pas de version de référence"}


def test_le_releve_s_ecrit_comme_les_autres_mesures(tmp_path):
    releve = resumer_etape(ecrire(tmp_path, un_rapport()))
    assert json.loads(json.dumps(releve, ensure_ascii=False, allow_nan=False)) == releve


@pytest.mark.parametrize(
    ("changement", "message"),
    [
        (lambda r: r.update(version_du_rapport=2), "version 1"),
        (lambda r: r.pop("etape"), "pas de « etape »"),
        (lambda r: r.pop("mesures"), "pas de « mesures »"),
        (lambda r: r["mesures"].pop("echantillons"), "pas d'« echantillons »"),
        (lambda r: r.update(date="hier"), "pas une date ISO"),
    ],
)
def test_un_rapport_abime_dit_quoi_refaire(tmp_path, changement, message):
    rapport = un_rapport()
    changement(rapport)
    with pytest.raises(ValueError, match=message) as erreur:
        resumer_etape(ecrire(tmp_path, rapport))
    assert "evaluer-etape" in str(erreur.value)


def test_sans_reference_le_rapport_le_dit(tmp_path):
    with pytest.raises(ValueError, match="pas de version de référence"):
        resumer_etape(ecrire(tmp_path, un_rapport(avec_reference=False)), reference=True)


def test_un_rapport_qui_manque_ou_qui_n_est_pas_du_json(tmp_path):
    with pytest.raises(FileNotFoundError, match="n'existe pas"):
        resumer_etape(tmp_path / "absent.json")
    (tmp_path / "faux.json").write_text("{pas du json", encoding="utf-8")
    with pytest.raises(ValueError, match="pas un fichier JSON lisible"):
        resumer_etape(tmp_path / "faux.json")


# --- Les paires d'exemples ------------------------------------------------------------------------------------


def une_rangee(n_invite: int, n_reponse: int, largeur: int = 12) -> Rangee:
    n = n_invite + n_reponse
    return Rangee(
        ids=[5] * n + [0] * (largeur - n),
        appris=[False] * n_invite + [True] * n_reponse + [False] * (largeur - n),
        documents=[0] * n + [-1] * (largeur - n),
    )


def un_element(identifiant: str, partie: str, paire, attendu=None, notes=None) -> dict:
    """Un élément de `paires/`, au format de `forge.preferences.construction._element`."""
    notes = notes or [[1, 1, 2, 1, 1], [0, 1, 1, 1, 1]]
    return {
        "id": identifiant,
        "tours": [{"role": "utilisateur", "texte": f"Question {identifiant}"}],
        "contraintes": [["minuscules", {}]] if attendu is None else [],
        "attendu": attendu,
        "partie": partie,
        "reponses": [
            {"texte": f"réponse choisie de {identifiant}", "pensee": None, "ids": [5, 6, 7], "terminee": True},
            {"texte": f"réponse rejetée de {identifiant}", "pensee": None, "ids": [5, 6, 7, 8, 9], "terminee": False},
        ],
        "notes": notes,
        "paire": paire,
        "raison": "terminee" if paire else None,
        "sans_paire": None if paire else "egalite",
    }


def un_jeu_de_paires(dossier, avec_reference: bool = True, val_en_premier: bool = False):
    """Un jeu comme `forge preferences` l'écrit : quatre éléments (dont une égalité et une paire de validation), un jeu `dpo`."""
    elements = [
        un_element("a", "train", [0, 1]),
        un_element("egalite", "train", None, notes=[[1, 1, 1, 1, 1]] * 2),
        un_element("probleme:7", "train", [0, 1], attendu=84),
        un_element("v", "val", [0, 1]),
        un_element("b", "train", [1, 0], notes=[[0, 1, 1, 1, 1], [1, 1, 2, 1, 1]]),
    ]
    if val_en_premier:
        elements.insert(0, elements.pop(3))
    sortie = SortieParFragments(dossier / "paires", "paires", par_fragment=2)
    for element in elements:
        sortie.ajouter(element)
    sortie.valider({})
    sortie.terminer({})
    train = [une_rangee(4, 4 + k % 2) for k in range(6)]  # trois paires d'entraînement : a, probleme:7, b
    val = [une_rangee(4, 3), une_rangee(4, 5)]
    source = {"exemples": 4, "licence": "CC BY 4.0 (questions) ; réponses écrites par ton-ia-1.7", "lien": "https://creativecommons.org/licenses/by/4.0/"}
    problemes = {"exemples": 2, "licence": "MIT (problèmes générés par le code du dépôt) ; réponses écrites par ton-ia-1.7", "lien": "https://exemple.org/licence"}
    ecrire_jeu(dossier, train, val, "dpo", {"ecartes": 0, "sources": {"luth2_conversation": source, "problemes": problemes}}, TOK)
    if avec_reference:  # six valeurs : choisie, rejetée de chaque paire d'entraînement
        np.array([-10.5, -12.5, -20.0, -22.0, -30.25, -31.0], dtype="<f8").tofile(dossier / "train" / "reference.bin")
    return dossier


def test_paires_exemples_garde_les_premieres_paires_d_entrainement(tmp_path):
    jeu = un_jeu_de_paires(tmp_path / "preferences-1.8")
    paires = paires_exemples(jeu)
    assert [p["id"] for p in paires] == ["a", "probleme:7", "b"]  # ni l'égalité, ni la paire de validation
    assert paires_exemples(jeu, n=2)[1]["id"] == "probleme:7" and len(paires_exemples(jeu, n=2)) == 2
    premiere = paires[0]
    assert list(premiere) == ["id", "source", "invite", "contraintes", "attendu", "choisie", "rejetee", "raison"]
    assert premiere["invite"] == [{"role": "utilisateur", "texte": "Question a"}]
    assert premiere["choisie"]["texte"] == "réponse choisie de a" and premiere["rejetee"]["texte"] == "réponse rejetée de a"
    assert premiere["choisie"]["note"] == {"terminee": 1, "juste": 1, "consignes": 2, "francais": 1, "longueur": 1}
    assert premiere["rejetee"]["note"]["terminee"] == 0
    assert (premiere["choisie"]["terminee"], premiere["rejetee"]["terminee"]) == (True, False)
    assert premiere["raison"] == "terminee"


def test_les_references_sont_celles_des_rangees_de_chaque_paire(tmp_path):
    paires = paires_exemples(un_jeu_de_paires(tmp_path / "jeu"))
    assert [(p["choisie"]["logp_reference"], p["rejetee"]["logp_reference"]) for p in paires] == [(-10.5, -12.5), (-20.0, -22.0), (-30.25, -31.0)]


def test_une_paire_dont_la_rejetee_est_la_premiere_note_est_rangee_dans_le_bon_ordre(tmp_path):
    b = paires_exemples(un_jeu_de_paires(tmp_path / "jeu"))[2]
    assert b["choisie"]["texte"] == "réponse rejetée de b"  # la paire [1, 0] : la réponse de rang 1 est la choisie
    assert b["choisie"]["note"]["terminee"] == 1 and b["rejetee"]["note"]["terminee"] == 0


def test_les_jetons_comptent_le_fin_tour_d_une_reponse_terminee(tmp_path):
    a = paires_exemples(un_jeu_de_paires(tmp_path / "jeu"))[0]
    assert a["choisie"]["jetons"] == 4  # 3 jetons et <|fin_tour|>
    assert a["rejetee"]["jetons"] == 5  # coupée : pas de <|fin_tour|>


def test_la_source_a_sa_licence(tmp_path):
    paires = paires_exemples(un_jeu_de_paires(tmp_path / "jeu"))
    assert paires[0]["source"] == {
        "nom": "luth2_conversation",
        "licence": "CC BY 4.0 (questions) ; réponses écrites par ton-ia-1.7",
        "lien": "https://creativecommons.org/licenses/by/4.0/",
    }
    assert paires[1]["source"]["nom"] == "problemes" and paires[1]["attendu"] == 84
    assert paires[1]["source"]["licence"].startswith("MIT")


def test_les_paires_s_ecrivent_en_json(tmp_path):
    paires = paires_exemples(un_jeu_de_paires(tmp_path / "jeu"))
    assert json.loads(json.dumps(paires, ensure_ascii=False, allow_nan=False)) == paires


def test_paires_exemples_ne_modifie_pas_le_jeu(tmp_path):
    jeu = un_jeu_de_paires(tmp_path / "jeu")
    avant = {p: p.stat().st_mtime_ns for p in jeu.rglob("*") if p.is_file()}
    paires_exemples(jeu)
    assert avant == {p: p.stat().st_mtime_ns for p in jeu.rglob("*") if p.is_file()}


def test_la_paire_de_validation_en_premier_ne_decale_pas_les_references(tmp_path):
    paires = paires_exemples(un_jeu_de_paires(tmp_path / "jeu", val_en_premier=True))
    assert [p["id"] for p in paires] == ["a", "probleme:7", "b"]
    assert paires[0]["choisie"]["logp_reference"] == -10.5


def test_paires_exemples_dit_quoi_refaire(tmp_path):
    with pytest.raises(Exception, match="absent ou pas fini"):
        paires_exemples(tmp_path / "absent")
    jeu = un_jeu_de_paires(tmp_path / "sans-reference", avec_reference=False)
    with pytest.raises(FileNotFoundError, match="reference.bin n'existe pas") as erreur:
        paires_exemples(jeu)
    assert "forge entrainer" in str(erreur.value)
    jeu = un_jeu_de_paires(tmp_path / "coupe")
    np.array([-1.0, -2.0], dtype="<f8").tofile(jeu / "train" / "reference.bin")
    with pytest.raises(ValueError, match="trop peu pour la paire 2"):
        paires_exemples(jeu)
    with pytest.raises(ValueError, match="au moins une paire"):
        paires_exemples(un_jeu_de_paires(tmp_path / "autre"), n=0)


# --- Le balayage ------------------------------------------------------------------------------------------------


def un_essai(dossier, taux: float, beta: float, debut: float, fin: float, v: dict | None = None, normaliser: bool = False, pas: int = 20):
    """Un dossier d'essai : config.toml, journal.jsonl (logps_choisie de `debut` à `fin`) et rapport.json."""
    dossier.mkdir(parents=True)
    (dossier / "config.toml").write_text(
        f'methode = "dpo"\ntaux_max = {taux}\n\n[dpo]\nbeta = {beta}\nnormaliser_longueur = {"true" if normaliser else "false"}\n', encoding="utf-8"
    )
    lignes = [{"evenement": "debut", "pas": 0}]
    for p in range(1, pas + 1):
        lignes.append({"pas": p, "perte": 0.5, "logps_choisie": debut + (fin - debut) * (p - 1) / (pas - 1)})
    lignes.append({"evenement": "fin", "pas": pas})
    (dossier / "journal.jsonl").write_text("".join(json.dumps(ligne) + "\n" for ligne in lignes), encoding="utf-8")
    rapport = {"version": "essai", "mesures": {"victoire": v or victoire(0.6, 100, 40, 60, 40.0, 50.0)}}
    (dossier / "rapport.json").write_text(json.dumps(rapport), encoding="utf-8")
    return dossier


def test_balayage_resume_chaque_essai(tmp_path):
    a = un_essai(tmp_path / "a", 1e-6, 0.05, -1.0, -1.2)
    b = un_essai(tmp_path / "b", 5e-6, 0.3, -1.0, -0.8, v=victoire(0.75, 140, 20, 40, 35.0, 50.0), normaliser=True)
    releves = balayage([a, b])
    assert [r["essai"] for r in releves] == ["a", "b"]
    assert list(releves[0]) == ["essai", "reglages", "victoire", "longueur", "logps_choisie"]
    assert releves[0]["reglages"] == {"taux_max": 1e-6, "beta": 0.05, "normaliser_longueur": False, "poids_sft": 1.0}
    assert releves[1]["reglages"] == {"taux_max": 5e-6, "beta": 0.3, "normaliser_longueur": True, "poids_sft": 1.0}
    assert releves[0]["victoire"] == {"taux": 0.6, "victoires": 100, "egalites": 40, "defaites": 60, "n": 200}
    assert releves[1]["victoire"]["taux"] == 0.75
    assert releves[0]["longueur"] == {"mots_modele": 40.0, "mots_reference": 50.0}
    assert releves[1]["longueur"]["mots_modele"] == 35.0


def test_logps_choisie_au_debut_et_a_la_fin(tmp_path):
    # 20 pas : le dixième est de 2 pas ; la moyenne des deux premières et des deux dernières valeurs.
    releve = balayage([un_essai(tmp_path / "a", 1e-6, 0.1, -1.0, -3.0)])[0]["logps_choisie"]
    pas = (-3.0 - -1.0) / 19
    assert releve["debut"] == pytest.approx(-1.0 + pas / 2)
    assert releve["fin"] == pytest.approx(-3.0 - pas / 2)
    assert releve["fin"] < releve["debut"]  # la vraisemblance de la choisie baisse : le piège connu, montré tel quel


def test_balayage_garde_une_victoire_absente_avec_sa_raison(tmp_path):
    essai = un_essai(tmp_path / "a", 1e-6, 0.1, -1.0, -1.1, v={"absente": "pas de référence"})
    releve = balayage([essai])[0]
    assert releve["victoire"] == {"absente": "pas de référence"} and releve["longueur"] == {"absente": "pas de référence"}


def test_balayage_ne_modifie_rien_et_s_ecrit_en_json(tmp_path):
    essai = un_essai(tmp_path / "a", 1e-6, 0.1, -1.0, -1.1)
    avant = {p: p.stat().st_mtime_ns for p in essai.iterdir()}
    releves = balayage([essai])
    assert avant == {p: p.stat().st_mtime_ns for p in essai.iterdir()}
    assert json.loads(json.dumps(releves, allow_nan=False)) == releves


def test_balayage_dit_quoi_refaire(tmp_path):
    with pytest.raises(ValueError, match="au moins un dossier"):
        balayage([])
    with pytest.raises(FileNotFoundError, match="rapport.json"):
        balayage([tmp_path / "vide"])
    essai = un_essai(tmp_path / "a", 1e-6, 0.1, -1.0, -1.1)
    (essai / "config.toml").unlink()
    with pytest.raises(FileNotFoundError, match="config.toml"):
        balayage([essai])
    (essai / "config.toml").write_text("pas = du toml", encoding="utf-8")
    with pytest.raises(ValueError, match="TOML lisible"):
        balayage([essai])
    (essai / "config.toml").write_text('methode = "dpo"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="taux_max"):
        balayage([essai])
    sans_dpo = un_essai(tmp_path / "b", 1e-6, 0.1, -1.0, -1.1)
    (sans_dpo / "journal.jsonl").write_text(json.dumps({"pas": 1, "perte": 0.5}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="ce n'est pas celui d'une DPO"):
        balayage([sans_dpo])
    sans_victoire = un_essai(tmp_path / "c", 1e-6, 0.1, -1.0, -1.1)
    (sans_victoire / "rapport.json").write_text(json.dumps({"mesures": {}}), encoding="utf-8")
    with pytest.raises(ValueError, match="pas de mesure « victoire »"):
        balayage([sans_victoire])
