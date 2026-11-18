"""Tests des paires de préférences de 1.8 et de la mesure `victoire` (plan 7, tâche 13).

Tout tourne sur le processeur, sans réseau. Les sources, le jeu `sft-1.7` et les jeux d'évaluation sont de faux
fichiers écrits sous un `FORGE_DONNEES` temporaire. Le modèle est un faux : `ModeleDe` écrit « chat » ou s'arrête
(`<|fin_tour|>`, une chance sur quatre à chaque pas), tiré par le générateur de `generer_lot` : il est déterministe
pour une graine donnée et donne des réponses de longueurs variées, donc des paires et des égalités.
"""

import gzip
import json
import math
from pathlib import Path

import numpy as np
import pytest

try:
    import torch
except ImportError as erreur:
    raise ImportError(
        "PyTorch n'est pas installé. Lance les tests avec `uv run --extra gpu pytest -q`."
    ) from erreur

from forge import __main__ as principal
from forge.affinage.empaquetage import empaqueter
from forge.affinage.jeu import ecrire_jeu, lire_index
from forge.conversation.format import Reponse, Tour, encoder_conversation, invite_de_reponse
from forge.conversation.sources import SOURCES_CONVERSATIONS, UsageInterdit
from forge.conversation.telechargement import PREFIXE, dossier_de_la_source
from forge.donnees.nettoyage import empreinte
from forge.evaluation import etape as module_etape
from forge.evaluation import reponses as module_reponses
from forge.evaluation.consignes import CONTRAINTES
from forge.evaluation.etape import MESURES, MESURES_PAR_ETAPE, ContexteDEvaluation, evaluer_etape
from forge.fragments import SortieParFragments, lire_elements
from forge.modele import ConfigModele, Transformer
from forge.preferences import construction
from forge.preferences.construction import (
    RECETTES_PREFERENCES,
    PairesEnPause,
    RecettePreferences,
    construire_paires,
    invites_de_validation,
)
from forge.preferences.invites import InvitePreference, invites_de_preference
from forge.preferences.noter import Note, choisir_paire, noter, raison_de_la_paire, sans_paire, taux_de_victoire
from forge.publication import Publication
from forge.raisonnement.problemes import (
    GRAINES_EVALUATION,
    GRAINES_PREFERENCES,
    GRAINES_VICTOIRE,
    PRENOMS_EVALUATION,
    generer_problemes,
)
from forge.tokenizer.bpe_octets import TokenizerOctets

TOKENIZER_DU_DEPOT = Path(__file__).resolve().parents[1] / "forge" / "ressources" / "tokenizer-ton-ia-v1.json"
TOK = TokenizerOctets.charger(TOKENIZER_DU_DEPOT)
CONFIG = ConfigModele(taille_vocabulaire=TOK.taille_vocabulaire, dim=16, couches=1, tetes=2, longueur_contexte=256)
FIN_TOUR = TOK.id_special("<|fin_tour|>")
ASSISTANT = TOK.id_special("<|assistant|>")
BOURRAGE = TOK.id_special("<|bourrage|>")
CHAT = TOK.encoder(" chat")[0]
PHRASE = "Le chat dort dans la maison et il ronronne."  # 9 mots, français, sans virgule
LETTRES = "abcdefghijklmnopqrstuvwxyz"

# Une petite recette : 30 invites demandées (9 problèmes, 21 questions), des réponses de 6 jetons au plus,
# des rangées de 160 jetons (une invite de plus de 154 jetons est écartée), 30 % de validation.
RECETTE = RecettePreferences("essai", invites=30, n_nouveaux=6, longueur=160, part_validation=0.3)
PAQUET = 4


# --------------------------------------------------------------------------------------
# Des modèles et des données de test
# --------------------------------------------------------------------------------------


class ModeleDe(Transformer):
    """Un faux modèle : à chaque pas, « chat » (trois chances sur quatre) ou `<|fin_tour|>` (une sur quatre).

    Il ne lit pas l'invite : le tirage vient seulement du générateur de `generer_lot`, donc de la graine et du lot.
    """

    def avancer(self, ids, positions, masque, cache):
        lot, t = ids.shape
        cache.longueur += t
        logits = torch.full((lot, t, self.config.taille_vocabulaire), -1e4)
        logits[:, -1, CHAT] = math.log(3.0)
        logits[:, -1, FIN_TOUR] = 0.0
        return logits


class ModeleScenario(Transformer):
    """Un faux modèle qui écrit toujours `script`, jeton après jeton (le dernier se répète), quoi qu'on lui donne."""

    def __init__(self, config: ConfigModele, script: list[int]) -> None:
        super().__init__(config)
        self.script = script
        self._pas = 0

    def avancer(self, ids, positions, masque, cache):
        lot, t = ids.shape
        self._pas = 0 if cache.longueur == 0 else self._pas + 1
        cache.longueur += t
        logits = torch.zeros(lot, t, self.config.taille_vocabulaire)
        logits[:, -1, self.script[min(self._pas, len(self.script) - 1)]] = 50.0
        return logits


def publication(modele: Transformer, version: str = "ton-ia-9.9", empreinte_des_poids: str = "a" * 64) -> Publication:
    torch.manual_seed(0)
    return Publication(modele=modele.eval(), tokenizer=TOK, version=version, empreinte_des_poids=empreinte_des_poids)


def mot(i: int) -> str:
    """Un mot de lettres seulement, distinct pour chaque entier."""
    return LETTRES[i % 26] + LETTRES[(i // 26) % 26] + "ouvement" + LETTRES[(i // 676) % 26]


def question(i: int) -> str:
    return f"Question {mot(i)} : pourquoi le {mot(i)} est-il utile au {mot(i + 7)} ?"


# Une invite d'IFEval-FR, et une question de Luth-2 qui en reprend 8 mots de suite.
INVITE_IFEVAL = "Rédige un poème sur la mer qui monte doucement le soir sans aucune virgule."
QUESTION_CONTAMINEE = 5
QUESTION_TROP_LONGUE = 6
DEJA_APPRISES = (0, 1, 2, 3)
N_QUESTIONS = 20


def texte_de_la_question(i: int) -> str:
    if i == QUESTION_CONTAMINEE:
        return f"Peux-tu m'aider ? {INVITE_IFEVAL}"
    if i == QUESTION_TROP_LONGUE:
        return "mot " * 200
    return question(i)


def conversation(i: int) -> dict:
    tours = [{"role": "utilisateur", "texte": texte_de_la_question(i)}, {"role": "assistant", "texte": PHRASE}]
    if i == 7:  # une question avec message système : il est gardé dans l'invite
        tours.insert(0, {"role": "systeme", "texte": "Tu réponds en français."})
    if i == 8:  # une conversation à plusieurs tours : seule la première question compte
        tours += [{"role": "utilisateur", "texte": "Et ensuite ?"}, {"role": "assistant", "texte": PHRASE}]
    return {"tours": tours, "domaine": "essai", "origine": f"Q{i}", "usage": "entrainement"}


def ecrire_elements(dossier: Path, prefixe: str, elements: list[dict], infos: dict) -> None:
    sortie = SortieParFragments(dossier, prefixe, 7)
    for element in elements:
        sortie.ajouter(element)
        if sortie.plein:
            sortie.valider()
    sortie.terminer(infos)


def ecrire_jeu_sft(racine: Path, n_val: int = 6) -> None:
    """`affinage/sft-1.7` : 2 conversations d'entraînement, `n_val` de validation, et `ids.txt.gz`."""
    exemples = [
        encoder_conversation(TOK, [Tour("utilisateur", f"Question numéro {k} : où dort le {mot(k)} ?"), Tour("assistant", PHRASE)])
        for k in range(2 + n_val)
    ]
    train, _ = empaqueter(exemples[:2], 63, BOURRAGE)
    val, _ = empaqueter(exemples[2:], 63, BOURRAGE)
    dossier = racine / "affinage" / "sft-1.7"
    ecrire_jeu(dossier, train, val, "sft", {"ecartes": 0, "sources": {}}, TOK)
    deja = "".join(f"{empreinte(question(i))}\n" for i in DEJA_APPRISES)
    with gzip.open(dossier / "ids.txt.gz", "wt", encoding="ascii") as fichier:
        fichier.write(deja)


@pytest.fixture
def donnees(tmp_path, monkeypatch) -> Path:
    """Un `FORGE_DONNEES` avec Luth-2 (20 conversations), IFEval-FR (une invite) et le jeu `sft-1.7`."""
    racine = tmp_path / "donnees"
    monkeypatch.setenv("FORGE_DONNEES", str(racine))
    ecrire_elements(
        dossier_de_la_source(SOURCES_CONVERSATIONS["luth2_conversation"]),
        PREFIXE,
        [conversation(i) for i in range(N_QUESTIONS)],
        {"epuisee": True},
    )
    ecrire_elements(
        dossier_de_la_source(SOURCES_CONVERSATIONS["ifeval_fr"]),
        PREFIXE,
        [{"cle": "1", "invite": INVITE_IFEVAL, "instruction_id_list": [], "kwargs": [], "usage": "evaluation"}],
        {"usage": "evaluation"},
    )
    ecrire_jeu_sft(racine)
    monkeypatch.setattr(construction, "INVITES_PAR_PAQUET", PAQUET)
    return racine


@pytest.fixture
def faux_modele(monkeypatch):
    """`construire_paires` charge `ModeleDe` au lieu d'une version publiée, et reste sur le processeur.

    Sans `appareil`, `construire_paires` prend la carte si PyTorch la voit : les tests n'y touchent jamais, même là.
    """
    publie = publication(ModeleDe(CONFIG))
    monkeypatch.setattr(construction, "charger_publication", lambda dossier, appareil="cpu": publie)
    monkeypatch.setattr(construction, "choisir_appareil", lambda appareil=None: torch.device("cpu"))
    return publie


def contenu_du_dossier(dossier: Path) -> dict[str, bytes]:
    return {str(f.relative_to(dossier)): f.read_bytes() for f in sorted(dossier.rglob("*")) if f.is_file()}


def elements_des_paires(dossier: Path) -> list[dict]:
    return list(lire_elements(dossier / "paires", "paires"))


def reponse(texte: str, terminee: bool = True) -> Reponse:
    return Reponse(texte=texte, pensee=None, ids=TOK.encoder(texte), terminee=terminee)


def invite(contraintes=(), attendu=None) -> InvitePreference:
    return InvitePreference("q", (Tour("utilisateur", "Parle-moi du chat."),), tuple(contraintes), attendu)


# --------------------------------------------------------------------------------------
# Les notes et le choix de la paire
# --------------------------------------------------------------------------------------


def test_l_ordre_des_notes_va_du_plus_important_au_moins_important():
    # Une réponse non terminée perd toujours, quels que soient les autres critères.
    assert Note(0, 1, 9, 1, 1) < Note(1, 0, 0, 0, 0)
    # À terminaison égale, une réponse fausse perd.
    assert Note(1, 0, 9, 1, 1) < Note(1, 1, 0, 0, 0)
    # Puis les consignes, puis le français, puis la longueur.
    assert Note(1, 1, 1, 1, 1) < Note(1, 1, 2, 0, 0)
    assert Note(1, 1, 2, 0, 1) < Note(1, 1, 2, 1, 0)
    assert Note(1, 1, 2, 1, 0) < Note(1, 1, 2, 1, 1)
    assert Note._fields == ("terminee", "juste", "consignes", "francais", "longueur")


@pytest.mark.parametrize(
    ("meilleure", "pire", "raison"),
    [
        (Note(1, 0, 0, 0, 0), Note(0, 1, 9, 1, 1), "terminee"),
        (Note(1, 1, 0, 0, 0), Note(1, 0, 9, 1, 1), "juste"),
        (Note(1, 1, 2, 0, 0), Note(1, 1, 1, 1, 1), "consignes"),
        (Note(1, 1, 2, 1, 0), Note(1, 1, 2, 0, 1), "francais"),
        (Note(1, 1, 2, 1, 1), Note(1, 1, 2, 1, 0), "longueur"),
    ],
)
def test_choisir_paire_et_la_raison_qui_departage(meilleure, pire, raison):
    assert choisir_paire([pire, meilleure]) == (1, 0)
    assert choisir_paire([meilleure, pire]) == (0, 1)
    assert raison_de_la_paire(meilleure, pire) == raison


def test_une_egalite_ne_donne_aucune_paire():
    assert choisir_paire([Note(1, 1, 1, 1, 1), Note(1, 1, 1, 1, 1)]) is None
    assert choisir_paire([Note(0, 1, 0, 1, 0)] * 3) is None


def test_avec_plus_de_deux_reponses_la_meilleure_et_la_pire():
    notes = [Note(1, 1, 0, 1, 1), Note(0, 1, 1, 1, 1), Note(1, 1, 1, 1, 1), Note(0, 1, 1, 1, 1)]
    assert choisir_paire(notes) == (2, 1)  # à égalité, la première rencontrée


def test_deux_reponses_egalement_bonnes_de_longueurs_differentes_ne_donnent_aucune_paire():
    """Rien ne préfère le court en soi : une réponse courte et une longue, toutes deux bonnes, ont la même note."""
    question = invite([("sans_virgule", {})])
    courte = reponse("Le chat dort dans la maison.")
    longue = reponse(" ".join(["Le chat dort dans la maison et il ronronne près du feu."] * 20))  # 220 mots
    notes = [noter(courte, question), noter(longue, question)]
    assert notes[0] == notes[1] and choisir_paire(notes) is None and sans_paire(notes) == "egalite"
    probleme = invite(attendu=12)
    detaillee = reponse("Je compte d'abord les pommes de la boîte puis celles du sac. " * 5 + "La réponse est 12.")
    notes = [noter(reponse("La réponse est 12."), probleme), noter(detaillee, probleme)]
    assert notes[0] == notes[1] and sans_paire(notes) == "egalite"


def test_deux_reponses_coupees_ne_donnent_aucune_paire():
    notes = [noter(reponse("Le chat dort", terminee=False), invite()), noter(reponse("Le", terminee=False), invite())]
    assert choisir_paire(notes) == (0, 1)  # elles diffèrent par la longueur…
    assert sans_paire(notes) == "aucune_bonne_reponse"  # … mais la meilleure est coupée : pas un modèle


def test_deux_problemes_faux_ne_donnent_aucune_paire():
    probleme = invite(attendu=12)
    notes = [noter(reponse("La réponse est 13."), probleme), noter(reponse("13"), probleme)]
    assert notes[0] > notes[1] and sans_paire(notes) == "aucune_bonne_reponse"
    juste = [notes[0], noter(reponse("La réponse est 12."), probleme)]
    assert sans_paire(juste) is None and choisir_paire(juste) == (1, 0)


def test_noter_sans_attendu_la_reponse_est_juste():
    n = noter(reponse(PHRASE), invite())
    assert n == Note(terminee=1, juste=1, consignes=0, francais=1, longueur=1)
    assert noter(reponse(PHRASE, terminee=False), invite()).terminee == 0


def test_noter_un_probleme_juste_faux_ou_coupe():
    probleme = invite(attendu=12)
    assert noter(reponse("La réponse est 12."), probleme).juste == 1
    assert noter(reponse("La réponse est 13."), probleme).juste == 0
    assert noter(reponse("La réponse est 12.", terminee=False), probleme).juste == 0  # coupée : jamais juste


def test_noter_compte_les_consignes_respectees():
    deux = invite([("sans_virgule", {}), ("mots_max", {"n": 20})])
    assert noter(reponse(PHRASE), deux).consignes == 2
    assert noter(reponse("Le chat, qui dort, ronronne."), deux).consignes == 1
    assert noter(reponse("mot " * 30 + "et, enfin"), deux).consignes == 0
    assert noter(reponse(""), invite([("minuscules", {})])).consignes == 0  # une réponse vide ne respecte rien


def test_noter_le_francais_ne_vaut_zero_que_pour_une_autre_langue():
    assert noter(reponse("The cat is on the table and it is sleeping."), invite()).francais == 0
    assert noter(reponse("12 34 56"), invite()).francais == 1  # indéterminée : pas pénalisée
    assert noter(reponse(PHRASE), invite()).francais == 1


@pytest.mark.parametrize(("mots", "attendu"), [(0, 0), (2, 0), (3, 1), (300, 1), (301, 0)])
def test_noter_la_longueur_de_3_a_300_mots(mots, attendu):
    assert noter(reponse(" ".join(["chat"] * mots)), invite()).longueur == attendu


def test_noter_refuse_une_contrainte_inconnue():
    with pytest.raises(ValueError, match="inconnue"):
        noter(reponse(PHRASE), invite([("rime", {})]))


def test_taux_de_victoire_a_la_main():
    a = [Note(1, 1, 1, 1, 1), Note(1, 1, 1, 1, 1), Note(0, 1, 1, 1, 1), Note(1, 0, 0, 0, 0)]
    b = [Note(0, 1, 1, 1, 1), Note(1, 1, 1, 1, 1), Note(1, 1, 1, 1, 1), Note(0, 1, 1, 1, 1)]
    assert taux_de_victoire(a, b) == {"victoires": 2, "egalites": 1, "defaites": 1, "taux": (2 + 0.5) / 4}
    with pytest.raises(ValueError):
        taux_de_victoire(a, b[:3])
    with pytest.raises(ValueError):
        taux_de_victoire([], [])


# --------------------------------------------------------------------------------------
# Les invites
# --------------------------------------------------------------------------------------


def base_de(n: int) -> list[tuple[str, list[Tour]]]:
    return [(f"id{i}", [Tour("utilisateur", question(i)), Tour("assistant", PHRASE)]) for i in range(n)]


def test_invites_septante_pour_cent_de_questions_avec_consignes_et_trente_de_problemes():
    invites = invites_de_preference(100, 0, base_de(200), set())
    questions = [i for i in invites if i.attendu is None]
    problemes = [i for i in invites if i.attendu is not None]
    assert len(questions) == 70 and len(problemes) == 30
    assert len({i.id for i in invites}) == 100
    par_id = {c.id: c for c in CONTRAINTES}
    for i in questions:
        assert [t.role for t in i.tours] == ["utilisateur"]  # la réponse de la base n'est pas gardée
        assert 1 <= len(i.contraintes) <= 2
        consignes = " ".join(par_id[nom].consigne(kwargs) for nom, kwargs in i.contraintes)
        assert i.tours[-1].texte.endswith("\n\n" + consignes)  # les consignes à la fin du message
        assert i.tours[-1].texte.startswith(question(int(i.id[2:])))
    for p in problemes:
        assert p.contraintes == () and isinstance(p.attendu, int)
    # Les problèmes sont ceux de difficulté 1 des graines des préférences, avec leur réponse.
    attendus = {f"probleme:{p.id}": (p.enonce, p.reponse) for p in generer_problemes(30, GRAINES_PREFERENCES, difficultes=(1,))}
    assert {p.id: (p.tours[0].texte, p.attendu) for p in problemes} == attendus
    assert all(p.id.split("-")[1] == "1" for p in problemes)
    # Questions et problèmes sont mélangés.
    assert invites[:70] != questions


def test_invites_meme_graine_memes_invites_autre_graine_autres():
    assert invites_de_preference(40, 3, base_de(100), set()) == invites_de_preference(40, 3, base_de(100), set())
    assert invites_de_preference(40, 3, base_de(100), set()) != invites_de_preference(40, 4, base_de(100), set())


def test_aucune_invite_ne_vient_de_exclure():
    base = base_de(30)
    exclure = {f"id{i}" for i in range(0, 30, 2)}
    invites = invites_de_preference(100, 0, base, exclure)
    questions = [i for i in invites if i.attendu is None]
    assert {i.id for i in questions} == {f"id{i}" for i in range(1, 30, 2)}  # base trop petite : toutes les autres
    assert all(i.id not in exclure for i in invites)


def test_une_question_en_double_n_est_prise_qu_une_fois():
    base = base_de(5) + base_de(5)
    invites = invites_de_preference(20, 0, base, set())
    assert sorted(i.id for i in invites if i.attendu is None) == [f"id{i}" for i in range(5)]


def test_les_problemes_d_evaluation_ne_deviennent_jamais_des_invites():
    with pytest.raises(UsageInterdit):
        invites_de_preference(10, 0, base_de(10), set(), graines_problemes=GRAINES_EVALUATION)
    invites = invites_de_preference(400, 0, base_de(10), set())
    for i in invites:
        if i.attendu is not None:
            assert GRAINES_PREFERENCES <= int(i.id.rsplit("-", 1)[1]) < GRAINES_PREFERENCES + 1_000_000
            assert not any(prenom in i.tours[0].texte for prenom in PRENOMS_EVALUATION)


def test_les_contraintes_incompatibles_ne_vont_jamais_ensemble():
    invites = invites_de_preference(2000, 0, base_de(3000), set())
    paires = [frozenset(nom for nom, _ in i.contraintes) for i in invites if len(i.contraintes) == 2]
    assert paires, "il faut des invites à deux consignes"
    assert frozenset({"minuscules", "fin_imposee"}) not in paires
    assert frozenset({"puces", "titre"}) not in paires
    assert all(len(p) == 2 for p in paires)  # jamais deux fois la même


# --------------------------------------------------------------------------------------
# Les recettes
# --------------------------------------------------------------------------------------


def test_les_deux_recettes_de_preferences():
    assert set(RECETTES_PREFERENCES) == {"preferences-1.8", "preferences-1.8-court"}
    complete = RECETTES_PREFERENCES["preferences-1.8"]
    assert complete == RecettePreferences("preferences-1.8", 40_000)
    assert RECETTES_PREFERENCES["preferences-1.8-court"].invites == 8_000
    assert (complete.reponses_par_invite, complete.temperature, complete.top_k) == (2, 1.0, 50)
    assert (complete.n_nouveaux, complete.longueur, complete.part_validation, complete.graine) == (384, 768, 0.05, 0)


@pytest.mark.parametrize(
    "champs",
    [{"invites": 0}, {"reponses_par_invite": 1}, {"n_nouveaux": 0}, {"longueur": 6}, {"part_validation": 1.0}, {"temperature": -1.0}],
)
def test_une_recette_impossible_est_refusee(champs):
    with pytest.raises(ValueError):
        RecettePreferences(**{"nom": "x", "invites": 10, "n_nouveaux": 6, "longueur": 160, **champs})


# --------------------------------------------------------------------------------------
# La construction des paires
# --------------------------------------------------------------------------------------


def test_construire_paires_ecrit_les_paires_et_un_jeu_dpo(donnees, faux_modele, tmp_path):
    index = construire_paires(Path("modele"), RECETTE)
    dossier = donnees / "affinage" / "essai"
    assert index == lire_index(dossier) and index["sorte"] == "dpo" and index["longueur"] == RECETTE.longueur
    elements = elements_des_paires(dossier)
    paires = [e for e in elements if e["paire"] is not None]
    assert index["invites"] == len(elements) and index["paires"] == len(paires)
    assert index["egalites"] == sum(1 for e in elements if e["sans_paire"] == "egalite")
    assert index["aucune_bonne_reponse"] == sum(1 for e in elements if e["sans_paire"] == "aucune_bonne_reponse")
    assert index["paires"] + index["egalites"] + index["aucune_bonne_reponse"] == index["invites"]
    assert index["taux_de_paires"] == pytest.approx(len(paires) / len(elements))  # après le plancher
    assert 0 < index["paires"] < index["invites"]  # le faux modèle donne des paires et des égalités
    assert index["aucune_bonne_reponse"] > 0  # des problèmes aux deux réponses terminées, mais fausses
    assert set(index["raisons"]) == set(Note._fields) and sum(index["raisons"].values()) == index["paires"]
    assert index["rangees"]["train"] + index["rangees"]["val"] == 2 * index["paires"]
    for e in elements:
        assert len(e["reponses"]) == len(e["notes"]) == RECETTE.reponses_par_invite
        invite_relue = InvitePreference(
            e["id"], tuple(Tour(**t) for t in e["tours"]), tuple((n, k) for n, k in e["contraintes"]), e["attendu"]
        )
        for r, note in zip(e["reponses"], e["notes"]):
            relue = Reponse(texte=r["texte"], pensee=r["pensee"], ids=r["ids"], terminee=r["terminee"])
            assert Note(*note) == noter(relue, invite_relue)
            assert len(r["ids"]) + r["terminee"] <= RECETTE.n_nouveaux
        notes = [Note(*n) for n in e["notes"]]
        assert e["sans_paire"] == sans_paire(notes)
        attendue = choisir_paire(notes) if e["sans_paire"] is None else None
        assert (tuple(e["paire"]) if e["paire"] else None) == attendue
        if attendue:
            choisie = notes[attendue[0]]
            assert choisie.terminee == 1 and choisie.juste == 1  # le plancher : jamais une choisie coupée ou fausse
            assert e["raison"] == raison_de_la_paire(choisie, notes[attendue[1]])
    # Les longueurs des réponses gardées, en jetons appris (<|fin_tour|> compris).
    jetons = [[len(e["reponses"][k]["ids"]) + e["reponses"][k]["terminee"] for k in e["paire"]] for e in paires]
    assert index["longueurs"] == {
        "jetons_choisies": pytest.approx(sum(c for c, _ in jetons) / len(jetons)),
        "jetons_rejetees": pytest.approx(sum(r for _, r in jetons) / len(jetons)),
        "part_choisie_plus_courte": pytest.approx(sum(1 for c, r in jetons if c < r) / len(jetons)),
    }
    assert {e["partie"] for e in elements} == {"train", "val"}
    assert index["modele"] == {"version": "ton-ia-9.9", "empreinte": "a" * 64}


def test_les_invites_deja_apprises_contaminees_ou_trop_longues_sont_ecartees_et_comptees(donnees, faux_modele):
    index = construire_paires(Path("modele"), RECETTE)
    ids = {e["id"] for e in elements_des_paires(donnees / "affinage" / "essai")}
    for i in DEJA_APPRISES:  # le jeu sft-1.7 les a déjà apprises
        assert empreinte(question(i)) not in ids
    assert empreinte(texte_de_la_question(QUESTION_CONTAMINEE)) not in ids  # 8 mots d'IFEval-FR
    assert empreinte(texte_de_la_question(QUESTION_TROP_LONGUE)) not in ids
    gardees = [i for i in range(N_QUESTIONS) if i not in (*DEJA_APPRISES, QUESTION_CONTAMINEE, QUESTION_TROP_LONGUE)]
    assert {empreinte(question(i)) for i in gardees} <= ids  # la base est petite : toutes les autres sont prises
    assert index["base"] == {"conversations": N_QUESTIONS, "deja_apprises": len(DEJA_APPRISES), "trop_longues": 1, "questions": 15}
    assert index["invites_ecartees"] == {"contaminees": 1, "trop_longues": 0}
    assert index["invites"] == 14 + 9
    assert "ifeval_fr" in index["decontamination"]["jeux"]
    # Aucune invite ne reprend 8 mots de suite d'IFEval-FR, et aucun problème ne vient des graines d'évaluation.
    textes = [t["texte"] for e in elements_des_paires(donnees / "affinage" / "essai") for t in e["tours"]]
    assert not any("monte doucement le soir sans aucune virgule" in t for t in textes)
    assert not any(prenom in t for t in textes for prenom in PRENOMS_EVALUATION)


def test_une_source_d_evaluation_ne_sert_jamais_de_base(donnees, faux_modele, monkeypatch):
    monkeypatch.setattr(construction, "SOURCE_DES_QUESTIONS", "ifeval_fr")
    with pytest.raises(UsageInterdit):
        construire_paires(Path("modele"), RECETTE)
    assert not (donnees / "affinage" / "essai").exists()


def test_sans_le_jeu_sft_1_7_la_commande_est_donnee(donnees, faux_modele):
    (donnees / "affinage" / "sft-1.7" / "ids.txt.gz").unlink()
    with pytest.raises(construction.DonneesManquantes, match="forge preparer --recette sft-1.7"):
        construire_paires(Path("modele"), RECETTE)


def test_les_rangees_de_paires_meme_invite_perte_sur_les_reponses(donnees, faux_modele):
    index = construire_paires(Path("modele"), RECETTE)
    dossier = donnees / "affinage" / "essai"
    largeur = index["longueur"] + 1
    elements = elements_des_paires(dossier)
    for partie in ("train", "val"):
        ids = np.fromfile(dossier / partie / "ids.bin", dtype="<u2").reshape(-1, largeur).astype(int)
        appris = np.fromfile(dossier / partie / "appris.bin", dtype="u1").reshape(-1, largeur).astype(bool)
        documents = np.fromfile(dossier / partie / "documents.bin", dtype="<i2").reshape(-1, largeur).astype(int)
        attendues = [e for e in elements if e["paire"] is not None and e["partie"] == partie]
        assert len(ids) == 2 * len(attendues)
        for k, e in enumerate(attendues):
            invite_ids = invite_de_reponse(TOK, [Tour(**t) for t in e["tours"]])
            assert invite_ids[-1] == ASSISTANT
            for rangee, rang_de_la_reponse in ((2 * k, e["paire"][0]), (2 * k + 1, e["paire"][1])):
                r = e["reponses"][rang_de_la_reponse]
                reponse_ids = r["ids"] + ([FIN_TOUR] if r["terminee"] else [])
                taille = len(invite_ids) + len(reponse_ids)
                # Même préfixe d'invite pour la choisie et la rejetée, puis la réponse telle qu'elle a été écrite.
                assert ids[rangee, :taille].tolist() == invite_ids + reponse_ids
                assert (ids[rangee, taille:] == BOURRAGE).all()
                # La perte ne porte que sur la réponse (et son <|fin_tour|> s'il a été écrit).
                assert appris[rangee].tolist() == [False] * len(invite_ids) + [True] * len(reponse_ids) + [False] * (largeur - taille)
                assert documents[rangee].tolist() == [0] * taille + [-1] * (largeur - taille)
            assert (ids[2 * k, : len(invite_ids)] == ids[2 * k + 1, : len(invite_ids)]).all()


def test_coupure_apres_le_deuxieme_paquet_puis_reprise_donne_les_memes_paires(donnees, faux_modele, monkeypatch, tmp_path):
    """Point à surveiller 3 : une coupure (plantage, courant) puis une relance redonnent les mêmes fichiers, à l'octet près."""
    d_une_traite = tmp_path / "une-traite"
    construire_paires(Path("modele"), RECETTE, sortie=d_une_traite)

    vrai = construction.repondre_lot
    appels = []

    def coupe_au_troisieme(*args, **kwargs):
        appels.append(1)
        if len(appels) == 3:
            raise RuntimeError("coupure de courant simulée")
        return vrai(*args, **kwargs)

    reprise = tmp_path / "reprise"
    with monkeypatch.context() as m:
        m.setattr(construction, "repondre_lot", coupe_au_troisieme)
        with pytest.raises(RuntimeError, match="coupure"):
            construire_paires(Path("modele"), RECETTE, sortie=reprise)
    etat = json.loads((reprise / "paires" / "etat.json").read_text(encoding="utf-8"))
    assert etat["elements"] == 2 * PAQUET and etat["etat"]["paquets"] == 2
    assert not (reprise / ".complet").exists() and not (reprise / "paires" / ".complet").exists()

    # La reprise relit ses invites : un jeu d'évaluation téléchargé entre-temps ne change pas la suite.
    monkeypatch.setattr(construction, "_invites_de_la_recette", lambda *a, **k: pytest.fail("les invites sont relues"))
    construire_paires(Path("modele"), RECETTE, sortie=reprise)
    assert contenu_du_dossier(reprise) == contenu_du_dossier(d_une_traite)
    ids = [e["id"] for e in elements_des_paires(reprise)]
    assert len(ids) == len(set(ids))  # aucune paire en double


def test_pause_par_ctrl_c_valide_le_paquet_puis_la_reprise_redonne_les_memes_paires(donnees, faux_modele, monkeypatch, tmp_path):
    d_une_traite = tmp_path / "une-traite"
    construire_paires(Path("modele"), RECETTE, sortie=d_une_traite)

    vrai = construction.repondre_lot
    appels = []

    class FaussePause:
        """Ctrl+C pendant le deuxième paquet."""

        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *erreur):
            return None

        @property
        def demandee(self):
            return len(appels) >= 2

    def compte(*args, **kwargs):
        appels.append(1)
        return vrai(*args, **kwargs)

    reprise = tmp_path / "reprise"
    with monkeypatch.context() as m:
        m.setattr(construction, "repondre_lot", compte)
        m.setattr(construction, "Pause", FaussePause)
        with pytest.raises(PairesEnPause) as pause:
            construire_paires(Path("modele"), RECETTE, sortie=reprise)
    message = str(pause.value)
    assert message.startswith("Pause\u202f:") and "python -m forge preferences" in message and "--recette essai" in message
    assert str(reprise) in message  # la reprise vise le même dossier
    assert len(appels) == 2  # le paquet en cours est fini, aucun autre ne commence
    etat = json.loads((reprise / "paires" / "etat.json").read_text(encoding="utf-8"))
    assert etat["etat"]["paquets"] == 2

    construire_paires(Path("modele"), RECETTE, sortie=reprise)
    assert contenu_du_dossier(reprise) == contenu_du_dossier(d_une_traite)


def test_relancer_un_travail_fini_ne_refait_rien(donnees, faux_modele, monkeypatch):
    premier = construire_paires(Path("modele"), RECETTE)
    monkeypatch.setattr(construction, "repondre_lot", lambda *a, **k: pytest.fail("rien ne doit être regénéré"))
    assert construire_paires(Path("modele"), RECETTE) == premier


def test_le_jeu_se_refait_des_fragments_si_la_coupure_tombe_apres_les_paires(donnees, faux_modele, monkeypatch):
    premier = construire_paires(Path("modele"), RECETTE)
    dossier = donnees / "affinage" / "essai"
    (dossier / ".complet").unlink()
    monkeypatch.setattr(construction, "repondre_lot", lambda *a, **k: pytest.fail("rien ne doit être regénéré"))
    assert construire_paires(Path("modele"), RECETTE) == premier


def test_un_autre_modele_ne_reprend_pas_les_paires_d_un_premier(donnees, faux_modele, monkeypatch):
    vrai = construction.repondre_lot
    appels = []

    def coupe(*args, **kwargs):
        appels.append(1)
        if len(appels) == 2:
            raise RuntimeError("coupure")
        return vrai(*args, **kwargs)

    monkeypatch.setattr(construction, "repondre_lot", coupe)
    with pytest.raises(RuntimeError):
        construire_paires(Path("modele"), RECETTE)
    autre = publication(ModeleDe(CONFIG), empreinte_des_poids="b" * 64)
    monkeypatch.setattr(construction, "charger_publication", lambda dossier, appareil="cpu": autre)
    with pytest.raises(ValueError, match="autres réglages"):
        construire_paires(Path("modele"), RECETTE)


def test_une_liste_d_invites_abimee_n_est_pas_reprise(donnees, faux_modele, monkeypatch):
    vrai = construction.repondre_lot
    appels = []

    def coupe(*args, **kwargs):
        appels.append(1)
        if len(appels) == 2:
            raise RuntimeError("coupure")
        return vrai(*args, **kwargs)

    with monkeypatch.context() as m:
        m.setattr(construction, "repondre_lot", coupe)
        with pytest.raises(RuntimeError):
            construire_paires(Path("modele"), RECETTE)
    chemin = donnees / "affinage" / "essai" / "paires" / "invites.jsonl.gz"
    lignes = gzip.decompress(chemin.read_bytes()).splitlines(keepends=True)
    chemin.write_bytes(gzip.compress(b"".join(lignes[:-1])))
    with pytest.raises(ValueError, match="a changé"):
        construire_paires(Path("modele"), RECETTE)


def couper_au_paquet(monkeypatch, numero: int):
    """`repondre_lot` lève une « coupure » à son appel `numero` : les paquets d'avant sont validés."""
    vrai = construction.repondre_lot
    appels = []

    def coupe(*args, **kwargs):
        appels.append(1)
        if len(appels) == numero:
            raise RuntimeError("coupure")
        return vrai(*args, **kwargs)

    monkeypatch.setattr(construction, "repondre_lot", coupe)


def carte_simulee(monkeypatch, octets_libres: int) -> None:
    """Le lot se choisit comme sur une carte qui aurait `octets_libres` octets libres (aucune carte n'est touchée)."""
    monkeypatch.setattr(module_reponses, "_est_sur_la_carte", lambda appareil: True)
    monkeypatch.setattr(module_reponses, "_memoire_libre", lambda appareil: octets_libres)


def octets_pour_un_lot_de(lot: int) -> int:
    """La mémoire libre où `choisir_le_lot` rend `lot` pour la recette d'essai (sa formule, à mi-chemin du lot suivant)."""
    par_texte = 4 * CONFIG.couches * CONFIG.dim * RECETTE.longueur + 2 * CONFIG.taille_vocabulaire * RECETTE.jetons_max_invite
    return int(1.5 * lot * par_texte / module_reponses.PART_DE_LA_MEMOIRE)


@pytest.mark.parametrize(("lot", "accepte"), [(16, False), (32, True)])
def test_au_premier_depart_un_lot_sous_32_refuse_de_partir(donnees, faux_modele, monkeypatch, lot, accepte):
    carte_simulee(monkeypatch, octets_pour_un_lot_de(lot))
    assert module_reponses.choisir_le_lot(faux_modele.modele, RECETTE.longueur, RECETTE.jetons_max_invite) == lot
    if accepte:
        construire_paires(Path("modele"), RECETTE)
        etat = json.loads((donnees / "affinage" / "essai" / "paires" / "etat.json").read_text(encoding="utf-8"))
        assert etat["etat"]["lot"] == lot
        return
    with pytest.raises(construction.MemoireInsuffisante, match="Libère la carte") as erreur:
        construire_paires(Path("modele"), RECETTE)
    assert "au moins 32" in str(erreur.value)
    assert not (donnees / "affinage" / "essai").exists()  # rien n'est figé : la relance choisira de nouveau


def test_a_la_reprise_le_lot_reste_fige_et_un_manque_de_memoire_arrete(donnees, faux_modele, monkeypatch):
    carte_simulee(monkeypatch, octets_pour_un_lot_de(64))
    with monkeypatch.context() as m:
        couper_au_paquet(m, 2)
        with pytest.raises(RuntimeError, match="coupure"):
            construire_paires(Path("modele"), RECETTE)
    carte_simulee(monkeypatch, octets_pour_un_lot_de(32))  # assez pour partir, pas pour le lot figé de 64
    with pytest.raises(construction.MemoireInsuffisante, match="lot de 64") as erreur:
        construire_paires(Path("modele"), RECETTE)
    assert "Libère la carte" in str(erreur.value)
    carte_simulee(monkeypatch, octets_pour_un_lot_de(128))  # plus de mémoire : le lot reste 64
    construire_paires(Path("modele"), RECETTE)
    etat = json.loads((donnees / "affinage" / "essai" / "paires" / "etat.json").read_text(encoding="utf-8"))
    assert etat["etat"]["lot"] == 64


def test_un_manque_de_memoire_en_cours_de_route_arrete_sans_couper_le_lot(donnees, faux_modele, monkeypatch):
    appels = []

    def sans_memoire(modele, invites, *args):
        appels.append(len(invites))
        raise torch.cuda.OutOfMemoryError("plus de mémoire (simulé)")

    monkeypatch.setattr(module_reponses, "generer_lot", sans_memoire)
    with pytest.raises(torch.cuda.OutOfMemoryError):
        construire_paires(Path("modele"), RECETTE)
    assert appels == [RECETTE.reponses_par_invite * PAQUET]  # un seul appel, tout le lot : jamais coupé en deux
    etat = json.loads((donnees / "affinage" / "essai" / "paires" / "etat.json").read_text(encoding="utf-8"))
    assert etat["etat"]["paquets"] == 0 and etat["elements"] == 0  # le paquet n'est pas validé : il se refera


def test_une_reprise_sur_un_autre_appareil_est_refusee(donnees, faux_modele, monkeypatch):
    with monkeypatch.context() as m:
        couper_au_paquet(m, 2)
        with pytest.raises(RuntimeError):
            construire_paires(Path("modele"), RECETTE)
    chemin = donnees / "affinage" / "essai" / "paires" / "etat.json"
    etat = json.loads(chemin.read_text(encoding="utf-8"))
    assert etat["etat"]["appareil"] == "cpu"
    etat["etat"]["appareil"] = "cuda"  # comme des paires commencées sur la carte
    chemin.write_text(json.dumps(etat), encoding="utf-8")
    with pytest.raises(ValueError, match="--appareil cuda"):
        construire_paires(Path("modele"), RECETTE)


def test_invites_de_validation_relues_dans_les_fragments(donnees, faux_modele):
    construire_paires(Path("modele"), RECETTE)
    dossier = donnees / "affinage" / "essai"
    val = [e for e in elements_des_paires(dossier) if e["partie"] == "val"]
    assert len(val) >= 2
    relues = invites_de_validation(dossier, 2)
    assert [i.id for i in relues] == [e["id"] for e in val[:2]]
    premiere = relues[0]
    assert isinstance(premiere, InvitePreference) and premiere.tours == tuple(Tour(**t) for t in val[0]["tours"])
    assert premiere.contraintes == tuple((n, k) for n, k in val[0]["contraintes"]) and premiere.attendu == val[0]["attendu"]
    assert len(invites_de_validation(dossier, 1000)) == len(val)
    with pytest.raises(construction.DonneesManquantes, match="forge preferences"):
        invites_de_validation(donnees / "affinage" / "absent", 3)


def test_la_commande_preferences(donnees, faux_modele, monkeypatch, capsys):
    monkeypatch.setitem(construction.RECETTES_PREFERENCES, "essai", RECETTE)
    monkeypatch.setattr(construction, "SEUIL_DU_TAUX_DE_PAIRES", 0.0)
    code = principal.main(["preferences", "--modele", "modele", "--recette", "essai", "--appareil", "cpu"])
    sortie = capsys.readouterr()
    assert code == 0 and "SEUIL" not in sortie.err
    index = lire_index(donnees / "affinage" / "essai")
    assert "Taux de paires utilisables" in sortie.out and "\u202f%" in sortie.out
    assert f"{index['paires']} paires" in sortie.out
    assert f"{index['aucune_bonne_reponse']} sans bonne r\u00e9ponse" in sortie.out
    assert "Longueur moyenne" in sortie.out and "la choisie est la plus courte dans" in sortie.out


def test_sous_le_seuil_de_20_pour_cent_la_commande_le_dit_et_rend_un_code_a_part(donnees, faux_modele, monkeypatch, capsys):
    monkeypatch.setitem(construction.RECETTES_PREFERENCES, "essai", RECETTE)
    monkeypatch.setattr(construction, "SEUIL_DU_TAUX_DE_PAIRES", 1.0)  # le taux du faux mod\u00e8le est forc\u00e9ment dessous
    code = principal.main(["preferences", "--modele", "modele", "--recette", "essai", "--appareil", "cpu"])
    assert code == principal.CODE_SOUS_LE_SEUIL == 5
    assert code not in (0, 1, 2, 3, 4, 130)  # ni succ\u00e8s, ni erreur, ni argparse, ni travail-long.ps1, ni pause
    erreur = capsys.readouterr().err
    assert "SEUIL NON ATTEINT" in erreur and "fix\u00e9 par l'utilisateur" in erreur and "ne lance pas la DPO" in erreur
    assert (donnees / "affinage" / "essai" / ".complet").is_file()  # le jeu est \u00e9crit quand m\u00eame


def test_la_commande_preferences_refuse_une_recette_inconnue(capsys):
    with pytest.raises(SystemExit):
        principal.main(["preferences", "--modele", "modele", "--recette", "inconnue"])
    assert "preferences-1.8" in capsys.readouterr().err


def test_la_commande_preferences_en_pause_rend_130(donnees, faux_modele, monkeypatch, capsys):
    monkeypatch.setitem(construction.RECETTES_PREFERENCES, "essai", RECETTE)

    def en_pause(*args, **kwargs):
        raise PairesEnPause("Pause\u202f: essai. Pour reprendre, relance la même commande.")

    monkeypatch.setattr(construction, "construire_paires", en_pause)
    assert principal.main(["preferences", "--modele", "modele", "--recette", "essai"]) == 130
    assert "Pause" in capsys.readouterr().err


# --------------------------------------------------------------------------------------
# La mesure `victoire`
# --------------------------------------------------------------------------------------


def script_de(texte: str, termine: bool = True) -> list[int]:
    return [*TOK.encoder(texte), *([FIN_TOUR] if termine else [])]


@pytest.fixture
def deux_versions(monkeypatch):
    """« modele » écrit PHRASE et s'arrête, « reference » écrit PHRASE sans jamais finir."""
    versions = {
        "modele": publication(ModeleScenario(CONFIG, script_de(PHRASE)), "ton-ia-1.8", "c" * 64),
        "reference": publication(ModeleScenario(CONFIG, script_de(PHRASE, termine=False)), "ton-ia-1.7", "d" * 64),
    }
    monkeypatch.setattr(module_etape, "charger_publication", lambda dossier, appareil="cpu": versions[Path(dossier).name])
    return versions


def test_les_mesures_de_1_8():
    assert MESURES_PAR_ETAPE["1.8"] == (*MESURES_PAR_ETAPE["1.7"], "victoire")
    assert "victoire" in MESURES


def test_la_victoire_sans_reference_est_absente(donnees):
    ctx = ContexteDEvaluation(ModeleScenario(CONFIG, script_de(PHRASE)).eval(), TOK, torch.device("cpu"), 4, lot=8)
    r = MESURES["victoire"](ctx)
    assert set(r) == {"absente"} and "--reference" in r["absente"]


def test_la_victoire_contre_la_reference_calculee_a_la_main(donnees, deux_versions, tmp_path):
    rapport = evaluer_etape(Path("modele"), "1.8", tmp_path / "ev", reference=Path("reference"), appareil="cpu", n_max=4)
    # 4 invites (3 questions de la validation de sft-1.7, 1 problème) : la réponse terminée gagne toujours.
    assert rapport["mesures"]["victoire"] == {
        "victoires": 4, "egalites": 0, "defaites": 0, "taux": 1.0, "mots_modele": 9.0, "mots_reference": 9.0, "n": 4,
    }
    assert rapport["reference"]["mesures"]["victoire"] == {
        "victoires": 0, "egalites": 0, "defaites": 4, "taux": 0.0, "mots_modele": 9.0, "mots_reference": 9.0, "n": 4,
    }
    assert tuple(rapport["mesures"]) == MESURES_PAR_ETAPE["1.8"]
    markdown = (tmp_path / "ev" / "rapport.md").read_text(encoding="utf-8")
    assert "Taux de victoire" in markdown and "100,0\u202f%" in markdown and "0,0\u202f%" in markdown
    assert json.loads((tmp_path / "ev" / "rapport.json").read_text(encoding="utf-8"))["mesures"]["victoire"]["taux"] == 1.0


def test_les_invites_de_la_victoire(donnees):
    ctx = ContexteDEvaluation(ModeleScenario(CONFIG, script_de(PHRASE)).eval(), TOK, torch.device("cpu"), 4, lot=8)
    invites = module_etape._invites_de_victoire(ctx)
    assert len(invites) == 4
    questions = [i for i in invites if i.attendu is None]
    problemes = [i for i in invites if i.attendu is not None]
    assert len(questions) == 3 and len(problemes) == 1
    assert all(i.tours[-1].texte.startswith("Question numéro") and 1 <= len(i.contraintes) <= 2 for i in questions)
    assert all(GRAINES_VICTOIRE <= int(p.id.rsplit("-", 1)[1]) < GRAINES_VICTOIRE + 1_000_000 for p in problemes)


def test_la_victoire_sur_les_invites_de_validation_d_un_jeu_de_paires(donnees, faux_modele, deux_versions, tmp_path):
    construire_paires(Path("modele"), RECETTE)
    attendues = invites_de_validation(donnees / "affinage" / "essai", 2)
    rapport = evaluer_etape(
        Path("modele"), "1.8", tmp_path / "ev", reference=Path("reference"), appareil="cpu", n_max=2, invites="essai"
    )
    assert rapport["mesures"]["victoire"]["n"] == len(attendues) == 2
    assert rapport["invites"] == "essai"


def test_la_victoire_avec_un_jeu_de_paires_absent_est_absente(donnees, deux_versions, tmp_path):
    rapport = evaluer_etape(
        Path("modele"), "1.8", tmp_path / "ev", reference=Path("reference"), appareil="cpu", n_max=2, invites="absent"
    )
    assert set(rapport["mesures"]["victoire"]) == {"absente"}
    assert "forge preferences" in rapport["mesures"]["victoire"]["absente"]


def test_invites_n_a_de_sens_qu_a_l_etape_1_8(donnees, deux_versions, tmp_path):
    with pytest.raises(ValueError, match="victoire"):
        evaluer_etape(Path("modele"), "1.7", tmp_path / "ev", appareil="cpu", n_max=2, invites="essai")


def test_la_commande_evaluer_etape_passe_les_invites(monkeypatch, tmp_path, capsys):
    vus = {}

    def faux_evaluer(modele, etape, sortie, reference=None, appareil=None, n_max=None, invites=None):
        vus.update(etape=etape, invites=invites, n_max=n_max)
        raise ValueError("arrêt voulu")

    monkeypatch.setattr(module_etape, "evaluer_etape", faux_evaluer)
    code = principal.main(
        ["evaluer-etape", "--modele", str(tmp_path), "--etape", "1.8", "--invites", "preferences-1.8", "--n-max", "200"]
    )
    assert code == 1 and vus == {"etape": "1.8", "invites": "preferences-1.8", "n_max": 200}
