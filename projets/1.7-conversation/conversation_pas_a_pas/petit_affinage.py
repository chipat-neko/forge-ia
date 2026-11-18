"""Un tout petit affinage : un modèle minuscule apprend, en 80 pas, à finir son tour de parole.

Le chapitre 1.7 explique la perte masquée et le format de conversation. Cet essai les fait travailler de bout
en bout, avec le vrai code de forge, sur un modèle minuscule (2 couches, des vecteurs de 64 nombres, un
contexte de 128 jetons) :

1. il pré-entraîne ce modèle 40 pas sur le texte du site (`texte-du-site.txt`, du chapitre 1.1), comme
   l'essai du chapitre 1.5 : il sait à peine écrire, et il n'a jamais vu `<|fin_tour|>` ;
2. il le publie avec `forge.exporter`, comme une vraie version de ton IA : c'est le départ de l'affinage ;
3. il écrit 24 conversations (`CONVERSATIONS`), les encode avec le gabarit, les range en rangées par
   empaquetage, et les écrit comme un jeu `sft` de forge ;
4. il affine le départ par `forge.entrainement.entrainer` (méthode `sft`), la commande `forge entrainer` ;
5. il fait répondre le modèle à huit questions qu'il n'a jamais vues, avant et après, et compte les réponses
   qui finissent par `<|fin_tour|>`.

Avant l'affinage, le modèle ne s'arrête jamais : il ne sait pas qu'un tour a une fin. Après, la plupart de
ses réponses finissent par `<|fin_tour|>`. La perte, elle, ne compte que les réponses : les questions ne
sont jamais apprises.

Rien n'est écrit ailleurs que dans le dossier temporaire de l'essai (ou celui qu'on donne).
"""

import contextlib
import io
import json
import shutil
import tempfile
import time
from pathlib import Path

import numpy as np
from forge.affinage.empaquetage import empaqueter
from forge.affinage.jeu import ecrire_jeu
from forge.conversation.format import Tour, encoder_conversation
from forge.donnees.jetons import empreinte_du_tokenizer
from forge.entrainement import ConfigEntrainement, entrainer
from forge.evaluation.reponses import repondre_lot
from forge.exporter import exporter
from forge.modele import ConfigModele, nombre_parametres
from forge.publication import charger_publication, nom_des_poids
from forge.tokenizer import TokenizerOctets

from conversation_pas_a_pas.gabarit import TOKENIZER

TEXTE_DU_SITE = Path(__file__).resolve().parents[2] / "1.1-modele-de-langage" / "donnees" / "texte-du-site.txt"
ETIQUETTE_DU_DEPART = "ton-ia-essai"  # le nom de la version de départ publiée par l'essai

CONTEXTE = 128
PAS_DU_PRE_ENTRAINEMENT = 40
PART_ENTRAINEMENT = 0.9
LOT_DE_JETONS = 1024
MICRO_LOT = 8
LOT_D_AFFINAGE = 4  # rangées par pas d'affinage
TAUX_DU_PRE_ENTRAINEMENT = 1e-3
TAUX_D_AFFINAGE = 3e-3
JETONS_DE_REPONSE = 48  # au plus : une réponse qui n'a pas fini son tour avant est « coupée »
MODELE = ConfigModele(dim=64, couches=2, tetes=4, longueur_contexte=CONTEXTE)

# region: essai-conversations
# Vingt-quatre conversations écrites pour l'essai : une question, une réponse courte. Seule la réponse est apprise.
CONVERSATIONS: tuple[tuple[str, str], ...] = (
    ("Quelle est la capitale de l'Italie ?", "La capitale de l'Italie est Rome."),
    ("Combien font 3 fois 4 ?", "Trois fois quatre font douze."),
    ("De quelle couleur est le ciel ?", "Le ciel est bleu quand il fait beau."),
    ("Que fait un forgeron ?", "Un forgeron chauffe le fer, puis il le frappe."),
    ("Qui es-tu ?", "Je suis ton IA, un tout petit modèle."),
    ("Quel est le contraire de chaud ?", "Le contraire de chaud est froid."),
    ("Combien de jours dans une semaine ?", "Une semaine compte sept jours."),
    ("Où se couche le soleil ?", "Le soleil se couche à l'ouest."),
    ("Que boit un chat ?", "Un chat boit du lait ou de l'eau."),
    ("Dis bonjour.", "Bonjour, que veux-tu savoir ?"),
    ("Quel est le premier mois de l'année ?", "Le premier mois est janvier."),
    ("Combien font 10 moins 7 ?", "Dix moins sept font trois."),
    ("Que mange une vache ?", "Une vache mange de l'herbe."),
    ("Quelle est la capitale de l'Espagne ?", "La capitale de l'Espagne est Madrid."),
    ("À quoi sert un marteau ?", "Un marteau sert à enfoncer un clou."),
    ("Combien de pattes a un chien ?", "Un chien a quatre pattes."),
    ("Que dit-on le matin ?", "Le matin, on dit bonjour."),
    ("De quelle couleur est l'herbe ?", "L'herbe est verte."),
    ("Quelle saison vient après l'été ?", "L'automne vient après l'été."),
    ("Combien font 5 et 6 ?", "Cinq et six font onze."),
    ("Où vivent les poissons ?", "Les poissons vivent dans l'eau."),
    ("Que fait le boulanger ?", "Le boulanger fait du pain."),
    ("Quel animal fait miaou ?", "C'est le chat qui fait miaou."),
    ("Dis merci.", "Merci, et à bientôt."),
)
VALIDATION = 4  # les quatre dernières conversations ne servent qu'à mesurer la perte de validation

# Huit questions que le modèle n'a jamais vues : on regarde si ses réponses finissent par <|fin_tour|>.
INVITES = (
    "Quelle est la capitale de l'Allemagne ?",
    "Combien font 2 fois 6 ?",
    "De quelle couleur est la neige ?",
    "Que fait un boulanger ?",
    "Combien de jours dans une année ?",
    "Où se lève le soleil ?",
    "Que boit un cheval ?",
    "Dis au revoir.",
)
# fin: essai-conversations


def texte_du_site() -> str:
    """Le texte du chapitre 1.1 (`projets/1.1-modele-de-langage/donnees/texte-du-site.txt`)."""
    if not TEXTE_DU_SITE.exists():
        raise FileNotFoundError(
            f"Le texte {TEXTE_DU_SITE} est introuvable. L'essai en a besoin : il faut le dépôt entier "
            "(projets/1.1-modele-de-langage), pas seulement le dossier de ce projet."
        )
    return TEXTE_DU_SITE.read_text(encoding="utf-8")


def tours_de(question: str, reponse: str) -> list[Tour]:
    return [Tour("utilisateur", question), Tour("assistant", reponse)]


# region: essai-donnees
def preparer_pre_entrainement(racine: Path, tok: TokenizerOctets) -> Path:
    """Écrit les jetons du texte du site dans `racine/jetons`, au format de `forge encoder`, et rend ce dossier.

    Un seul texte, encodé par le tokenizer figé, suivi de `<|fin_texte|>` : les 90 premiers % des jetons vont à
    l'entraînement, le reste à la validation. L'index porte l'empreinte du tokenizer, que l'export vérifiera.
    """
    jetons = tok.encoder(texte_du_site()) + [tok.id_special("<|fin_texte|>")]
    coupure = int(PART_ENTRAINEMENT * len(jetons))
    parties = {"train": jetons[:coupure], "val": jetons[coupure:]}
    dossier = Path(racine) / "jetons"
    fichiers = {}
    for partie, contenu in parties.items():
        (dossier / partie).mkdir(parents=True, exist_ok=True)
        nom = f"{partie}/fragment-00000.bin"
        (dossier / nom).write_bytes(np.asarray(contenu, dtype="<u2").tobytes())  # uint16, petit-boutiste
        fichiers[nom] = len(contenu)
    tokenizer = {"nom": tok.nom, "taille_vocabulaire": tok.taille_vocabulaire, "empreinte": empreinte_du_tokenizer(tok)}
    (dossier / "index.json").write_text(json.dumps({"version": 1, "fichiers": fichiers, "tokenizer": tokenizer}), encoding="utf-8")
    (dossier / ".complet").write_text("{}", encoding="utf-8")
    return dossier


def preparer_jeu(racine: Path, tok: TokenizerOctets) -> Path:
    """Écrit les conversations comme un jeu d'affinage `sft` dans `racine/affinage`, et rend ce dossier.

    Chaque conversation est encodée avec son masque (`encoder_conversation`), puis rangée avec les autres
    dans des rangées de `CONTEXTE + 1` jetons (`empaqueter`) : plusieurs conversations par rangée, jamais
    coupées. Les `VALIDATION` dernières ne servent qu'à la validation.
    """
    exemples = [encoder_conversation(tok, tours_de(q, r)) for q, r in CONVERSATIONS]
    bourrage = tok.id_special("<|bourrage|>")
    train, ecartes = empaqueter(exemples[:-VALIDATION], CONTEXTE, bourrage)
    val, _ = empaqueter(exemples[-VALIDATION:], CONTEXTE, bourrage)
    sources = {"essai": {"exemples": len(exemples), "licence": "MIT", "lien": "https://github.com/chipat-neko/forge-ia"}}
    dossier = Path(racine) / "affinage"
    ecrire_jeu(dossier, train, val, "sft", {"ecartes": ecartes, "sources": sources}, tok)
    return dossier
# fin: essai-donnees


def config_pre_entrainement(appareil: str, racine: Path) -> ConfigEntrainement:
    """Le pré-entraînement de l'essai : `PAS_DU_PRE_ENTRAINEMENT` pas de 1 024 jetons sur le texte du site."""
    racine = Path(racine)
    return ConfigEntrainement(
        preset=MODELE,
        donnees=str(racine / "jetons"),
        jetons_total=PAS_DU_PRE_ENTRAINEMENT * LOT_DE_JETONS,
        taille_lot_jetons=LOT_DE_JETONS,
        micro_lot=MICRO_LOT,
        taux_max=TAUX_DU_PRE_ENTRAINEMENT,
        echauffement=4,
        evaluation_tous_pas=20,
        appareil=appareil,
        compiler="non",
        sortie=str(racine / "pre-entrainement"),
    )


def config_affinage(appareil: str, racine: Path, pas: int) -> ConfigEntrainement:
    """L'affinage de l'essai : méthode `sft`, parti de la version publiée, `pas` pas de `LOT_D_AFFINAGE` rangées."""
    racine = Path(racine)
    par_pas = LOT_D_AFFINAGE * CONTEXTE
    return ConfigEntrainement(
        methode="sft",
        depart=str(racine / ETIQUETTE_DU_DEPART),
        preset=MODELE,
        donnees=str(racine / "affinage"),
        jetons_total=pas * par_pas,
        taille_lot_jetons=par_pas,
        longueur=CONTEXTE,
        micro_lot=LOT_D_AFFINAGE,
        taux_max=TAUX_D_AFFINAGE,
        echauffement=4,
        evaluation_tous_pas=20,
        appareil=appareil,
        compiler="non",
        sortie=str(racine / "affinage-sortie"),
    )


def part_terminee(modele, tok: TokenizerOctets) -> tuple[float, list[dict]]:
    """Fait répondre `modele` aux `INVITES` (glouton) : la part des réponses qui finissent leur tour, et les réponses.

    Une réponse « finit son tour » si elle écrit `<|fin_tour|>` avant `JETONS_DE_REPONSE` jetons. Les réponses
    sont rendues telles quelles, sans choisir les meilleures.
    """
    reponses = repondre_lot(modele, tok, [[Tour("utilisateur", q)] for q in INVITES], n_nouveaux=JETONS_DE_REPONSE)
    montrees = [{"invite": q, "texte": r.texte, "terminee": r.terminee} for q, r in zip(INVITES, reponses)]
    return sum(r.terminee for r in reponses) / len(reponses), montrees


# region: essai
def essai_affinage(appareil: str, pas: int = 80, racine: Path | None = None) -> dict:
    """Pré-entraîne un modèle minuscule 40 pas, le publie, puis l'affine `pas` pas sur 24 conversations.

    Rend `appareil`, `pas`, les `pertes` de chaque pas d'affinage (la moyenne sur les jetons appris),
    `fin_de_tour_avant` et `fin_de_tour_apres` (la part des réponses aux huit questions neuves qui finissent par
    `<|fin_tour|>`, avant et après), les `reponses_avant` et `reponses_apres` telles quelles, les chiffres du
    jeu (`exemples`, `rangees`, `jetons_appris`, `jetons`), `parametres` et les `secondes` de tout l'essai.
    Sans `racine`, tout est écrit dans un dossier temporaire, effacé ensuite.
    """
    debut = time.perf_counter()
    propre = racine is None
    dossier = Path(tempfile.mkdtemp(prefix="affinage-")) if propre else Path(racine)
    try:
        tok = TokenizerOctets.charger(TOKENIZER)
        preparer_pre_entrainement(dossier, tok)
        jeu = preparer_jeu(dossier, tok)
        with contextlib.redirect_stdout(io.StringIO()):  # forge raconte sa progression : l'essai la garde pour lui
            pre = config_pre_entrainement(appareil, dossier)
            shutil.rmtree(pre.dossier_sortie, ignore_errors=True)  # un essai précédent refuserait de repartir de zéro
            entrainer(pre)
            depart = dossier / ETIQUETTE_DU_DEPART
            shutil.rmtree(depart, ignore_errors=True)
            exporter(pre.dossier_sortie / "sauvegardes", depart, nom_des_poids(ETIQUETTE_DU_DEPART))  # une vraie version, publiée par forge
            avant, reponses_avant = part_terminee(charger_publication(depart, appareil).modele, tok)
            affinage = config_affinage(appareil, dossier, pas)
            shutil.rmtree(affinage.dossier_sortie, ignore_errors=True)
            resume = entrainer(affinage)  # la méthode « sft » : la perte ne porte que sur les réponses
        # Le modèle affiné : sa dernière sauvegarde, publiée de la même façon.
        affine = dossier / f"{ETIQUETTE_DU_DEPART}-affine"
        shutil.rmtree(affine, ignore_errors=True)
        exporter(affinage.dossier_sortie / "sauvegardes", affine, nom_des_poids(f"{ETIQUETTE_DU_DEPART}-affine"))
        apres, reponses_apres = part_terminee(charger_publication(affine, appareil).modele, tok)
        index = json.loads((jeu / "index.json").read_text(encoding="utf-8"))
        return {
            "appareil": appareil,
            "pas": pas,
            "pertes": [float(p) for p in resume["pertes"]],
            "fin_de_tour_avant": avant,
            "fin_de_tour_apres": apres,
            "reponses_avant": reponses_avant,
            "reponses_apres": reponses_apres,
            "exemples": index["exemples"],
            "rangees": index["rangees"]["train"] + index["rangees"]["val"],
            "jetons": index["jetons"],
            "jetons_appris": index["jetons_appris"],
            "parametres": nombre_parametres(MODELE),
            "secondes": round(time.perf_counter() - debut, 2),
        }
    finally:
        if propre:
            shutil.rmtree(dossier, ignore_errors=True)
# fin: essai
