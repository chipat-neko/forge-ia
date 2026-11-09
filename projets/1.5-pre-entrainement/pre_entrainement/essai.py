"""Un petit entraînement, mis en pause puis repris : la reprise est exacte.

`essai_pause_reprise` fait deux fois le même entraînement de 60 pas, avec le vrai code de forge :
une fois d'un trait, une fois arrêté à mi-chemin puis repris. Sur le processeur, les deux finissent
sur la même perte, au bit près : la pause ne coûte rien. Le modèle est minuscule (2 couches, des
vecteurs de 64 nombres) et ses données aussi : le texte du site, encodé par le tokenizer figé de
« ton IA ». Rien n'est écrit ailleurs que dans le dossier qu'on donne.

Arrêter l'essai à mi-chemin (`arreter_apres`) fait comme Ctrl+C : forge finit le pas en cours et
sauvegarde tout (le modèle, l'optimiseur, la position dans les données et l'état du hasard). La
seule différence est la ligne `pause` du journal, que Ctrl+C écrit en plus.
"""

import contextlib
import io
import json
import shutil
import time
from dataclasses import replace
from pathlib import Path

import forge
import numpy as np
from forge.entrainement import ConfigEntrainement, entrainer
from forge.modele import ConfigModele
from forge.tokenizer import TokenizerOctets

# Le tokenizer figé de « ton IA », et le texte du chapitre 1.1 : l'essai n'a besoin de rien d'autre.
TOKENIZER = Path(forge.__file__).resolve().parent / "ressources" / "tokenizer-ton-ia-v1.json"
TEXTE_DU_SITE = Path(__file__).resolve().parents[2] / "1.1-modele-de-langage" / "donnees" / "texte-du-site.txt"

FIN_DE_TEXTE = "<|fin_texte|>"
PART_ENTRAINEMENT = 0.9
LONGUEUR_CONTEXTE = 64
LOT_DE_JETONS = 1024
MICRO_LOT = 16


def texte_du_site() -> str:
    """Le texte du chapitre 1.1 (`projets/1.1-modele-de-langage/donnees/texte-du-site.txt`)."""
    if not TEXTE_DU_SITE.exists():
        raise FileNotFoundError(
            f"Le texte {TEXTE_DU_SITE} est introuvable. L'essai en a besoin : il faut le dépôt entier "
            "(projets/1.1-modele-de-langage), pas seulement le dossier de ce projet."
        )
    return TEXTE_DU_SITE.read_text(encoding="utf-8")


# region: essai-donnees
def preparer_essai(racine: Path, texte: str) -> Path:
    """Écrit les jetons de l'essai dans `racine/jetons`, au format de `forge encoder`, et rend ce dossier.

    C'est un raccourci de la chaîne de données du chapitre 1.2 (télécharger, trier, mélanger, encoder) :
    un seul texte, encodé par le tokenizer figé, suivi de `<|fin_texte|>`. Les 90 premiers % des jetons
    vont à l'entraînement (`train/`), le reste à la validation (`val/`). On ne passe pas par
    `est_validation` : sur quelques centaines de documents, 0,5 % pourrait n'en laisser aucun.
    """
    tokenizer = TokenizerOctets.charger(TOKENIZER)
    jetons = tokenizer.encoder(texte) + [tokenizer.id_special(FIN_DE_TEXTE)]
    coupure = int(PART_ENTRAINEMENT * len(jetons))
    parties = {"train": jetons[:coupure], "val": jetons[coupure:]}
    minimum = LONGUEUR_CONTEXTE + 1  # un morceau : le contexte et le jeton qui le suit
    if min(len(partie) for partie in parties.values()) < minimum:
        raise ValueError(
            f"Le texte est trop court : {len(jetons)} jetons, dont {len(parties['val'])} pour la validation, "
            f"alors qu'il en faut au moins {minimum} dans chaque partie."
        )
    dossier = Path(racine) / "jetons"
    fichiers = {}
    for partie, contenu in parties.items():
        (dossier / partie).mkdir(parents=True, exist_ok=True)
        nom = f"{partie}/fragment-00000.bin"
        (dossier / nom).write_bytes(np.asarray(contenu, dtype="<u2").tobytes())  # uint16, petit-boutiste
        fichiers[nom] = len(contenu)
    (dossier / "index.json").write_text(json.dumps({"version": 1, "fichiers": fichiers}), encoding="utf-8")
    (dossier / ".complet").write_text("{}", encoding="utf-8")
    return dossier
# fin: essai-donnees


# region: essai-reprise
def config_essai(appareil: str, racine: Path, pas: int = 60) -> ConfigEntrainement:
    """La configuration de l'essai : un petit modèle, 1 024 jetons par pas, `pas` pas.

    Les chemins (`donnees`, `sortie`) sont sous `racine` ; `appareil` est `cpu` ou `cuda`.
    """
    racine = Path(racine)
    return ConfigEntrainement(
        preset=ConfigModele(dim=64, couches=2, tetes=4, longueur_contexte=LONGUEUR_CONTEXTE),
        donnees=str(racine / "jetons"),
        jetons_total=pas * LOT_DE_JETONS,
        taille_lot_jetons=LOT_DE_JETONS,
        micro_lot=MICRO_LOT,
        taux_max=1e-3,
        echauffement=6,
        evaluation_tous_pas=20,
        appareil=appareil,
        compiler="non",
        sortie=str(racine / "sortie"),
    )


def essai_pause_reprise(appareil: str, racine: Path) -> dict:
    """Entraîne d'un trait, puis avec une pause à mi-chemin, et compare les deux pertes finales.

    Rend `appareil`, `pas_total`, `pas_de_la_pause`, les deux pertes finales (`perte_un_trait`,
    `perte_reprise`), leur `ecart` (0 attendu sur le processeur), `pertes_identiques` (vrai si les
    pertes de la seconde moitié sont les mêmes une à une), et les `secondes` de tout l'essai.
    """
    racine = Path(racine)
    if not (racine / "jetons" / ".complet").exists():  # sinon ils sont prêts : les réécrire échoue si un chargeur les lit encore
        preparer_essai(racine, texte_du_site())
    base = config_essai(appareil, racine)
    milieu = base.pas_total // 2
    for nom in ("d-un-trait", "en-pause"):  # un essai précédent refuserait de repartir de zéro
        shutil.rmtree(racine / nom, ignore_errors=True)
    debut = time.perf_counter()
    with contextlib.redirect_stdout(io.StringIO()):  # forge raconte sa progression : l'essai la garde pour lui
        d_un_trait = entrainer(replace(base, sortie=str(racine / "d-un-trait")))
        en_pause = replace(base, sortie=str(racine / "en-pause"))
        entrainer(en_pause, arreter_apres=milieu)  # comme Ctrl+C au pas 30 : tout est sauvegardé
        repris = entrainer(en_pause, reprendre=True)  # repart de la sauvegarde, jusqu'au pas 60
    secondes = time.perf_counter() - debut
    avant, apres = float(d_un_trait["pertes"][-1]), float(repris["pertes"][-1])
    return {
        "appareil": appareil,
        "pas_total": base.pas_total,
        "pas_de_la_pause": milieu,
        "perte_un_trait": avant,
        "perte_reprise": apres,
        "ecart": abs(avant - apres),
        "pertes_identiques": d_un_trait["pertes"][milieu:] == repris["pertes"],
        "secondes": round(secondes, 2),
    }
# fin: essai-reprise
