"""Tests de l'évaluation d'une étape de ton IA (plan 7, tâche 11).

Tout tourne sur le processeur avec un modèle minuscule (vocabulaire du vrai tokenizer, 32 768 jetons,
dim 16, contexte de 96), publié par `exporter` puis rechargé comme un lecteur le ferait. Deux sortes de
modèles : le vrai petit `Transformer` (pour les clés des rapports) et `ModeleScenario`, un faux modèle qui
écrit toujours la même réponse (pour calculer les mesures à la main). Les fichiers d'évaluation sont écrits
par les tests, sous un `FORGE_DONNEES` temporaire : aucun réseau, aucun fichier du vrai disque de données.
"""

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest

try:
    import torch
except ImportError as erreur:
    raise ImportError(
        "PyTorch n'est pas installé. Lance les tests avec `uv run --extra gpu pytest -q`."
    ) from erreur

from forge.affinage.empaquetage import empaqueter
from forge.affinage.jeu import ecrire_jeu
from forge.conversation.format import Reponse, Tour, encoder_conversation
from forge.donnees.jetons import empreinte_du_tokenizer
from forge.entrainement import ConfigEntrainement, sauvegarder
from forge.entrainement.boucle import _etat_du_modele
from forge.evaluation import etape as module_etape
from forge.evaluation import reponses as module_reponses
from forge.evaluation.etape import (
    INVITES_DE_CONVERSATION,
    MESURES,
    MESURES_PAR_ETAPE,
    VERSION_DU_RAPPORT_D_ETAPE,
    ContexteDEvaluation,
    evaluer_etape,
)
from forge.evaluation.reponses import repondre_lot
from forge.exporter import exporter
from forge.fragments import SortieParFragments
from forge.modele import ConfigModele, Transformer
from forge.publication import charger_publication, nom_des_poids
from forge.tokenizer.bpe_octets import TokenizerOctets

pytestmark = pytest.mark.filterwarnings("ignore:Le tokenizer de .* n'a pas pu être vérifié")

TOKENIZER_DU_DEPOT = Path(__file__).resolve().parents[1] / "forge" / "ressources" / "tokenizer-ton-ia-v1.json"
TOK = TokenizerOctets.charger(TOKENIZER_DU_DEPOT)
CONFIG = ConfigModele(taille_vocabulaire=TOK.taille_vocabulaire, dim=16, couches=1, tetes=2, longueur_contexte=96)
ETIQUETTE = "ton-ia-9.9"
PHRASE = "Le chat dort dans la maison et il ronronne."  # 9 mots, français, sans virgule

# Les mesures de l'étape 1.9 sont les plus nombreuses : toutes celles de 1.7, plus trois.
CLES = {
    "perte_conversation": {"perte", "n"},
    "ifeval_fr": {"invite_stricte", "consigne_stricte", "n"},
    "tenue": {"terminee", "fr", "autre", "indetermine", "mots_moyens", "n"},
    "oubli": {"perte", "bits_par_octet", "n"},
    "problemes": {"exactitude", "terminee", "lot", "reussite_8", "par_famille", "par_difficulte", "n"},
    "mgsm_fr": {"exactitude", "terminee", "n"},
    "gsm8k_platinum_fr": {"exactitude", "terminee", "n"},
}


# --------------------------------------------------------------------------------------
# Des modèles et des données de test
# --------------------------------------------------------------------------------------


class ModeleScenario(Transformer):
    """Un faux modèle qui écrit toujours `script`, jeton après jeton (le dernier se répète), quoi qu'on lui donne.

    Il passe par `generer_lot` comme un vrai : il lit l'invite d'un coup, puis un jeton par pas. Avec
    `<|fin_tour|>` à la fin du script, la réponse est terminée ; sans lui, elle est coupée par la limite.
    """

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


def script_de(texte: str, termine: bool = True) -> list[int]:
    return [*TOK.encoder(texte), *([TOK.id_special("<|fin_tour|>")] if termine else [])]


def faux_modele(texte: str = PHRASE, termine: bool = True) -> ModeleScenario:
    return ModeleScenario(CONFIG, script_de(texte, termine)).eval()


def contexte_de(modele, n_max: int | None = None) -> ContexteDEvaluation:
    return ContexteDEvaluation(modele=modele, tok=TOK, appareil=torch.device("cpu"), n_max=n_max, lot=8)


_RACINE_DES_PUBLICATIONS = tempfile.TemporaryDirectory(prefix="forge-etape-")  # effacée à la fin du processus
_PUBLIEES: dict[str, Path] = {}


def publier(tmp_path: Path | None = None, nom: str = "pub", etiquette: str = ETIQUETTE) -> Path:
    """Exporte un petit modèle (poids tirés avec une graine) sous le nom d'une version ; rend son dossier.

    L'export prend une dizaine de secondes : chaque version n'est publiée qu'une fois pour tous les tests,
    qui ne font que la lire (`tmp_path` n'est gardé que pour la lisibilité des appels).
    """
    if etiquette not in _PUBLIEES:
        racine = Path(_RACINE_DES_PUBLICATIONS.name) / etiquette
        torch.manual_seed(0)
        modele = Transformer(CONFIG)
        config = ConfigEntrainement(
            preset=CONFIG,
            donnees=str(racine / "jetons"),
            jetons_total=192 * 6,
            taille_lot_jetons=192,
            micro_lot=2,
            taux_max=1e-2,
            echauffement=2,
            evaluation_tous_pas=2,
            appareil="cpu",
            compiler="non",
            sortie=str(racine / "entrainement"),
        )
        sauvegarde = sauvegarder(racine / "entrainement" / "sauvegardes", _etat_du_modele(config, modele, 7), "meilleur.pt")
        exporter(sauvegarde, racine / "pub", nom_des_poids(etiquette))
        _PUBLIEES[etiquette] = racine / "pub"
    return _PUBLIEES[etiquette]


def ecrire_source(racine: Path, nom: str, elements: list[dict]) -> None:
    """Une source d'évaluation téléchargée : fragments, état et `.complet`, sous `conversations/<nom>`."""
    sortie = SortieParFragments(racine / "conversations" / nom, "conversations")
    for element in elements:
        sortie.ajouter({**element, "usage": "evaluation"})
    sortie.valider()
    sortie.terminer({"usage": "evaluation"})


LIGNES_IFEVAL = [
    {"cle": "a", "invite": "Dis bonjour.", "instruction_id_list": ["fr:punctuation:no_comma"], "kwargs": [{}]},
    {
        "cle": "b",
        "invite": "Parle de ton chat.",
        "instruction_id_list": ["fr:punctuation:no_comma", "fr:length_constraints:number_words"],
        "kwargs": [{}, {"num_words": 10, "relation": "au moins"}],
    },
    {
        "cle": "c",
        "invite": "Sois bref.",
        "instruction_id_list": ["fr:length_constraints:number_words"],
        "kwargs": [{"num_words": 5, "relation": "moins de"}],
    },
]
LIGNES_MGSM = [{"question": f"Combien font {k} plus 1 ?", "reponse": str(k + 1)} for k in range(4)]


def ecrire_jetons_principal(racine: Path) -> None:
    """`jetons/principal` : de quoi faire quelques morceaux de validation de 97 jetons."""
    dossier = racine / "jetons" / "principal"
    fin = TOK.id_special("<|fin_texte|>")
    texte = "Le chat dort dans la maison et il ronronne doucement près du feu de cheminée. " * 12
    ids = [*TOK.encoder(texte), fin]
    fichiers, octets = {}, 0
    for partie in ("train", "val"):
        (dossier / partie).mkdir(parents=True, exist_ok=True)
        jetons = ids * 2
        np.array(jetons, dtype="<u2").tofile(dossier / partie / "fragment-00000.bin")
        fichiers[f"{partie}/fragment-00000.bin"] = len(jetons)
        octets += len(texte.encode("utf-8")) * 2
    index = {
        "version": 1,
        "tokenizer": {"nom": TOK.nom, "taille_vocabulaire": TOK.taille_vocabulaire, "empreinte": empreinte_du_tokenizer(TOK)},
        "octets": octets,
        "jetons_sans_fin": 2 * (len(ids) - 1) * 2,
        "jetons_train": fichiers["train/fragment-00000.bin"],
        "jetons_val": fichiers["val/fragment-00000.bin"],
        "fichiers": fichiers,
    }
    (dossier / "index.json").write_text(json.dumps(index), encoding="utf-8")
    (dossier / ".complet").write_text("{}", encoding="utf-8")


def ecrire_jeu_sft(racine: Path, systeme: bool = False) -> int:
    """`affinage/sft-1.7` : 8 conversations en validation. Rend le nombre de conversations de `val`."""
    bourrage = TOK.id_special("<|bourrage|>")

    def conversation(k: int) -> list[Tour]:
        tours = [Tour("utilisateur", f"Question numéro {k} : où dort le chat ?"), Tour("assistant", PHRASE)]
        return [Tour("systeme", "Tu réponds en français."), *tours] if systeme else tours

    exemples = [encoder_conversation(TOK, conversation(k)) for k in range(12)]
    train, _ = empaqueter(exemples[:4], 63, bourrage)
    val, _ = empaqueter(exemples[4:], 63, bourrage)
    ecrire_jeu(racine / "affinage" / "sft-1.7", train, val, "sft", {"ecartes": 0, "sources": {}}, TOK)
    return 8


@pytest.fixture
def donnees(tmp_path, monkeypatch) -> Path:
    """Un `FORGE_DONNEES` vide : toutes les mesures qui lisent des données y sont absentes."""
    racine = tmp_path / "donnees"
    racine.mkdir()
    monkeypatch.setenv("FORGE_DONNEES", str(racine))
    return racine


@pytest.fixture
def donnees_completes(donnees) -> Path:
    ecrire_source(donnees, "ifeval_fr", LIGNES_IFEVAL)
    ecrire_source(donnees, "mgsm_rev2_fr", LIGNES_MGSM)
    ecrire_source(donnees, "gsm8k_platinum_fr", LIGNES_MGSM[:2])
    ecrire_jetons_principal(donnees)
    ecrire_jeu_sft(donnees)
    return donnees


# --------------------------------------------------------------------------------------
# Les réponses
# --------------------------------------------------------------------------------------


def test_repondre_lot_rend_une_reponse_par_conversation_dans_l_ordre():
    modele = faux_modele()
    conversations = [[Tour("utilisateur", "Salut")], [Tour("utilisateur", "Une question un peu plus longue que l'autre ?")]]
    reponses = repondre_lot(modele, TOK, conversations, n_nouveaux=60, lot=2)
    assert len(reponses) == 2
    assert all(isinstance(r, Reponse) and r.texte == PHRASE and r.terminee for r in reponses)


def test_repondre_lot_garde_la_pensee_et_la_coupure():
    pensee = [TOK.id_special("<|pensee|>"), *TOK.encoder("2 + 2 = 4"), TOK.id_special("<|fin_pensee|>")]
    modele = ModeleScenario(CONFIG, [*pensee, *TOK.encoder("La réponse est 4.")]).eval()
    [r] = repondre_lot(modele, TOK, [[Tour("utilisateur", "2 + 2 ?")]], n_nouveaux=40)
    assert r.pensee == "2 + 2 = 4" and r.texte.startswith("La réponse est 4.")
    assert not r.terminee  # jamais de <|fin_tour|> : la limite de jetons a coupé la réponse


def test_repondre_lot_ne_plante_pas_si_l_invite_remplit_le_contexte():
    modele = faux_modele()
    trop_long = [Tour("utilisateur", "mot " * 200)]
    court = [Tour("utilisateur", "Salut")]
    r_long, r_court = repondre_lot(modele, TOK, [trop_long, court], n_nouveaux=512)
    assert r_long.texte == "" and not r_long.terminee
    assert r_court.texte == PHRASE and r_court.terminee


def test_repondre_lot_donne_le_meme_resultat_deux_fois_et_sans_effet_sur_l_ordre():
    torch.manual_seed(1)
    modele = Transformer(CONFIG).eval()
    conversations = [[Tour("utilisateur", t)] for t in ("a", "bonjour tout le monde", "un texte moyen", "z")]
    a = repondre_lot(modele, TOK, conversations, n_nouveaux=10, temperature=1.0, graine=3, lot=2)
    b = repondre_lot(modele, TOK, conversations, n_nouveaux=10, temperature=1.0, graine=3, lot=2)
    assert [r.ids for r in a] == [r.ids for r in b]
    glouton = repondre_lot(modele, TOK, conversations, n_nouveaux=10, lot=4)
    inverse = repondre_lot(modele, TOK, conversations[::-1], n_nouveaux=10, lot=4)
    assert [r.ids for r in glouton] == [r.ids for r in inverse][::-1]


def test_dix_invites_fixes():
    assert len(INVITES_DE_CONVERSATION) == 10 and len(set(INVITES_DE_CONVERSATION)) == 10
    assert "Qui es-tu ?" in INVITES_DE_CONVERSATION
    assert any("Python" in invite for invite in INVITES_DE_CONVERSATION)


# --------------------------------------------------------------------------------------
# Les mesures, à la main
# --------------------------------------------------------------------------------------


def test_ifeval_fr_exactitudes_calculees_a_la_main(donnees_completes):
    # La réponse (9 mots, sans virgule) respecte : a (sans virgule) ; b = [sans virgule oui, 10 mots au moins non] ;
    # c (moins de 5 mots) non. Invites strictes : 1 sur 3. Consignes strictes : 2 sur 4.
    r = MESURES["ifeval_fr"](contexte_de(faux_modele()))
    assert r == {"invite_stricte": pytest.approx(1 / 3), "consigne_stricte": pytest.approx(2 / 4), "n": 3}


def test_ifeval_fr_compte_une_reponse_vide_ou_coupee_sans_planter(donnees_completes):
    vide = MESURES["ifeval_fr"](contexte_de(ModeleScenario(CONFIG, [TOK.id_special("<|fin_tour|>")]).eval()))
    assert vide["n"] == 3 and 0.0 <= vide["consigne_stricte"] <= 1.0
    coupee = MESURES["ifeval_fr"](contexte_de(faux_modele(termine=False)))
    assert coupee["n"] == 3  # la réponse coupée est jugée sur son texte, comme elle est


def test_tenue_d_un_modele_qui_ecrit_du_francais(donnees_completes):
    r = MESURES["tenue"](contexte_de(faux_modele()))
    assert set(r) == CLES["tenue"]
    assert r["terminee"] == 1.0 and r["fr"] == 1.0 and r["autre"] == 0.0 and r["indetermine"] == 0.0
    assert r["mots_moyens"] == 9.0
    # 3 réponses d'IFEval-FR + les invites de la validation de sft-1.7 (8 conversations).
    assert r["n"] == 3 + 8


def test_tenue_d_une_reponse_coupee_n_est_pas_terminee(donnees_completes):
    r = MESURES["tenue"](contexte_de(faux_modele(termine=False)))
    assert r["terminee"] == 0.0


def test_tenue_respecte_n_max_sur_les_invites_de_la_validation(donnees):
    ecrire_jeu_sft(donnees)  # IFEval-FR est absent : seules les invites de sft-1.7 comptent
    r = MESURES["tenue"](contexte_de(faux_modele(), n_max=5))
    assert r["n"] == 5


def test_les_invites_de_sft_gardent_le_systeme(donnees):
    ecrire_jeu_sft(donnees, systeme=True)
    invites = module_etape.invites_de_validation(donnees / "affinage" / "sft-1.7", TOK, 100)
    assert len(invites) == 8
    assert all([t.role for t in tours] == ["systeme", "utilisateur"] for tours in invites)
    assert all(tours[1].texte.startswith("Question numéro") for tours in invites)


def test_mgsm_et_gsm8k_comptent_les_reponses_justes(donnees):
    ecrire_source(donnees, "mgsm_rev2_fr", [{"question": "Combien ?", "reponse": "9"}, {"question": "Et ?", "reponse": "10"}])
    ecrire_source(donnees, "gsm8k_platinum_fr", [{"question": "Combien ?", "reponse": "1 234"}])
    modele = faux_modele("La réponse est 9.")
    assert MESURES["mgsm_fr"](contexte_de(modele)) == {"exactitude": 0.5, "terminee": 1.0, "n": 2}
    assert MESURES["gsm8k_platinum_fr"](contexte_de(modele)) == {"exactitude": 0.0, "terminee": 1.0, "n": 1}
    # Une réponse coupée est fausse, même si son dernier nombre est le bon.
    coupe = MESURES["mgsm_fr"](contexte_de(faux_modele("La réponse est 9.", termine=False)))
    assert coupe == {"exactitude": 0.0, "terminee": 0.0, "n": 2}  # la part terminée explique le 0 %


def test_problemes_exactitude_reussite_et_decoupages(donnees, monkeypatch):
    # Un modèle qui répond toujours « La réponse est 5. » : juste exactement pour les problèmes de réponse 5.
    p = module_etape.generer_problemes(30, module_etape.GRAINES_EVALUATION)
    attendu = sum(1 for probleme in p if probleme.reponse == 5) / len(p)
    r = MESURES["problemes"](contexte_de(faux_modele("La réponse est 5."), n_max=30))
    assert set(r) == CLES["problemes"] and r["n"] == len(p)
    assert r["exactitude"] == pytest.approx(attendu)
    assert r["reussite_8"] == pytest.approx(attendu)  # le faux modèle écrit la même chose à chaque essai
    assert set(r["par_famille"]) == {probleme.famille for probleme in p}
    assert set(r["par_difficulte"]) == {str(probleme.difficulte) for probleme in p}
    for groupe in (*r["par_famille"].values(), *r["par_difficulte"].values()):
        assert set(groupe) == {"exactitude", "reussite_8", "n"}
    assert sum(g["n"] for g in r["par_famille"].values()) == len(p)


def test_problemes_part_terminee_et_lot_ecrit(donnees):
    termine = MESURES["problemes"](contexte_de(faux_modele("La réponse est 5."), n_max=6))
    assert termine["terminee"] == 1.0 and termine["lot"] == module_etape.LOT_DES_ESSAIS
    coupe = MESURES["problemes"](contexte_de(faux_modele("La réponse est 5.", termine=False), n_max=6))
    assert coupe["terminee"] == 0.0 and coupe["exactitude"] == 0.0 and coupe["reussite_8"] == 0.0


def test_reussite_8_ne_depend_pas_du_lot_de_generation(donnees, monkeypatch):
    """À température 1, le tirage dépend du lot : celui des 8 essais est fixe, quel que soit `ctx.lot`."""
    torch.manual_seed(2)
    modele = Transformer(CONFIG).eval()
    lots_vus = []
    vrai = module_etape.repondre_lot

    def espion(modele, tok, conversations, n_nouveaux, temperature, top_k, graine, lot):
        lots_vus.append((temperature, lot))
        return vrai(modele, tok, conversations, n_nouveaux, temperature, top_k, graine, lot)

    monkeypatch.setattr(module_etape, "repondre_lot", espion)
    petit = MESURES["problemes"](ContexteDEvaluation(modele, TOK, torch.device("cpu"), 4, lot=2))
    grand = MESURES["problemes"](ContexteDEvaluation(modele, TOK, torch.device("cpu"), 4, lot=8))
    assert petit["reussite_8"] == grand["reussite_8"] and petit["par_famille"] == grand["par_famille"]
    assert {lot for temperature, lot in lots_vus if temperature == 1.0} == {module_etape.LOT_DES_ESSAIS}
    assert {lot for temperature, lot in lots_vus if temperature == 0.0} == {2, 8}  # le glouton garde le lot demandé


def test_oubli_est_la_perte_sur_des_morceaux_du_principal(donnees_completes):
    torch.manual_seed(0)
    modele = Transformer(CONFIG).eval()
    r = MESURES["oubli"](contexte_de(modele))
    assert set(r) == CLES["oubli"]
    assert r["n"] >= 1 and r["perte"] == pytest.approx(np.log(TOK.taille_vocabulaire), abs=0.3)
    assert r["bits_par_octet"] > 0
    assert MESURES["oubli"](contexte_de(modele, n_max=1))["n"] == 1


def test_perte_conversation_sur_la_validation_de_sft(donnees_completes):
    modele = Transformer(CONFIG).eval()
    r = MESURES["perte_conversation"](contexte_de(modele))
    assert set(r) == CLES["perte_conversation"]
    assert r["n"] >= 1 and r["perte"] == pytest.approx(np.log(TOK.taille_vocabulaire), abs=0.3)


def test_echantillons_gardes_tels_quels(donnees):
    r = MESURES["echantillons"](contexte_de(faux_modele(termine=False)))
    assert [e["invite"] for e in r] == list(INVITES_DE_CONVERSATION)
    assert all(set(e) == {"invite", "texte", "pensee", "terminee"} for e in r)
    assert all(e["texte"].startswith("Le chat dort") and e["terminee"] is False for e in r)  # aucun tri, aucune coupe


def test_une_mesure_sans_donnees_rend_absente(donnees):
    for nom in ("perte_conversation", "ifeval_fr", "oubli", "mgsm_fr", "gsm8k_platinum_fr"):
        r = MESURES[nom](contexte_de(faux_modele()))
        assert set(r) == {"absente"} and isinstance(r["absente"], str) and r["absente"], nom
    assert "forge conversations" in MESURES["ifeval_fr"](contexte_de(faux_modele()))["absente"]
    assert "forge preparer" in MESURES["perte_conversation"](contexte_de(faux_modele()))["absente"]
    # tenue n'a besoin de rien de plus que l'une de ses deux sources
    assert set(MESURES["tenue"](contexte_de(faux_modele()))) == {"absente"}


def test_une_source_pas_terminee_est_absente(donnees):
    sortie = SortieParFragments(donnees / "conversations" / "ifeval_fr", "conversations")
    sortie.ajouter({"cle": "a", "invite": "x", "instruction_id_list": [], "kwargs": []})
    sortie.valider()  # pas de `.complet`
    assert "absente" in MESURES["ifeval_fr"](contexte_de(faux_modele()))


# --------------------------------------------------------------------------------------
# Le rapport d'une étape
# --------------------------------------------------------------------------------------


def test_les_mesures_de_chaque_etape():
    assert MESURES_PAR_ETAPE["1.7"] == ("perte_conversation", "ifeval_fr", "tenue", "oubli", "echantillons")
    assert MESURES_PAR_ETAPE["1.9"] == (
        "ifeval_fr", "tenue", "oubli", "problemes", "mgsm_fr", "gsm8k_platinum_fr", "echantillons",
    )
    assert all(nom in MESURES for noms in MESURES_PAR_ETAPE.values() for nom in noms)
    assert VERSION_DU_RAPPORT_D_ETAPE == 1


def test_le_rapport_a_les_cles_de_chaque_mesure(tmp_path, donnees_completes):
    modele = publier(tmp_path)
    sortie = tmp_path / "evaluation"
    rapport = evaluer_etape(modele, "1.9", sortie, appareil="cpu", n_max=4)
    assert rapport["version_du_rapport"] == VERSION_DU_RAPPORT_D_ETAPE
    assert rapport["version"] == ETIQUETTE and len(rapport["empreinte"]) == 64
    assert rapport["etape"] == "1.9" and rapport["date"][:2] == "20" and rapport["secondes"] >= 0
    assert tuple(rapport["mesures"]) == MESURES_PAR_ETAPE["1.9"]
    for nom, cles in CLES.items():
        if nom in rapport["mesures"]:
            assert set(rapport["mesures"][nom]) == cles, nom
    assert len(rapport["mesures"]["echantillons"]) == 10
    # Le JSON écrit est celui qu'on rend, et le Markdown existe, en français.
    ecrit = json.loads((sortie / "rapport.json").read_text(encoding="utf-8"))
    assert ecrit == json.loads(json.dumps(rapport))
    markdown = (sortie / "rapport.md").read_text(encoding="utf-8")
    assert ETIQUETTE in markdown and "IFEval" in markdown and "\u202f" in markdown
    assert "\r" not in markdown


def test_le_rapport_de_1_7_n_a_que_ses_mesures(tmp_path, donnees_completes):
    rapport = evaluer_etape(publier(tmp_path), "1.7", tmp_path / "ev", appareil="cpu", n_max=3)
    assert tuple(rapport["mesures"]) == MESURES_PAR_ETAPE["1.7"]
    assert "perte_conversation" in rapport["mesures"] and "problemes" not in rapport["mesures"]


def test_donnees_absentes_donnent_absente_sans_planter(tmp_path, donnees):
    rapport = evaluer_etape(publier(tmp_path), "1.9", tmp_path / "ev", appareil="cpu", n_max=3)
    for nom in ("ifeval_fr", "tenue", "oubli", "mgsm_fr", "gsm8k_platinum_fr"):
        assert set(rapport["mesures"][nom]) == {"absente"}
    assert set(rapport["mesures"]["problemes"]) == CLES["problemes"]  # généré par programme : jamais absent
    assert len(rapport["mesures"]["echantillons"]) == 10
    assert "absente" in (tmp_path / "ev" / "rapport.md").read_text(encoding="utf-8").lower()


def test_une_etape_inconnue_est_refusee(tmp_path, donnees):
    with pytest.raises(ValueError) as erreur:
        evaluer_etape(publier(tmp_path), "2.0", tmp_path / "ev", appareil="cpu")
    assert "1.7" in str(erreur.value) and "1.9" in str(erreur.value)
    assert not (tmp_path / "ev").exists()


def test_la_reference_passe_les_memes_mesures(tmp_path, donnees_completes):
    actuelle = publier(tmp_path, "actuelle", "ton-ia-9.9")
    reference = publier(tmp_path, "reference", "ton-ia-1.5")
    rapport = evaluer_etape(actuelle, "1.7", tmp_path / "ev", reference=reference, appareil="cpu", n_max=3)
    ref = rapport["reference"]
    assert ref["version"] == "ton-ia-1.5" and len(ref["empreinte"]) == 64
    assert tuple(ref["mesures"]) == tuple(rapport["mesures"])
    markdown = (tmp_path / "ev" / "rapport.md").read_text(encoding="utf-8")
    assert "ton-ia-1.5" in markdown and "ton-ia-9.9" in markdown


def test_un_modele_publie_se_recharge_avant_l_evaluation(tmp_path):
    # La version du rapport est celle du fichier des poids, comme `charger_publication` la lit.
    dossier = publier(tmp_path)
    assert charger_publication(dossier).version == ETIQUETTE


def test_le_lot_ne_depasse_pas_la_memoire_libre(monkeypatch):
    from forge.evaluation.reponses import choisir_le_lot

    modele = Transformer(CONFIG)
    assert choisir_le_lot(modele, longueur_max=96, longueur_invite_max=40) == 32  # processeur : le lot par défaut
    monkeypatch.setattr(module_reponses, "_memoire_libre", lambda appareil: 1 << 20)
    monkeypatch.setattr(module_reponses, "_est_sur_la_carte", lambda appareil: True)
    assert choisir_le_lot(modele, longueur_max=96, longueur_invite_max=40) < 128
    monkeypatch.setattr(module_reponses, "_memoire_libre", lambda appareil: 1 << 40)
    assert choisir_le_lot(modele, longueur_max=96, longueur_invite_max=40) == module_reponses.LOT_MAXIMUM


@pytest.mark.gpu
def test_gpu_une_evaluation_complete_d_un_petit_modele(tmp_path, donnees_completes):
    from forge.mesure import etat_gpu, gpu_occupe

    if gpu_occupe(etat_gpu()):
        pytest.skip("la carte graphique est occupée : le test attend qu'elle soit libre")
    rapport = evaluer_etape(publier(tmp_path), "1.9", tmp_path / "ev", appareil="cuda", n_max=4)
    assert set(rapport["mesures"]["ifeval_fr"]) == CLES["ifeval_fr"]
    assert len(rapport["mesures"]["echantillons"]) == 10
