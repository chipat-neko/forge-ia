"""Valeurs de référence pour le jumeau TypeScript.

Le site refait les calculs de ce paquet en TypeScript. Ce module écrit
`tests/attendus-<nom>.json` : des entrées, et ce que le Python en tire. Chaque
flottant y est écrit en 16 chiffres hexadécimaux (`vers_hex`), pour comparer
les deux langages au bit près. Vitest, pytest et la page de parité du site
lisent les mêmes fichiers.

Pour les régénérer (dans projets/mini-modele) :

    uv run python -m mini_modele.attendus

Chaque tâche qui ajoute un module ajoute ici son `calculer_attendus_<nom>()`,
et l'inscrit dans CALCULS.
"""

import dataclasses
import json
from collections.abc import Callable
from pathlib import Path

from mini_modele.calcul import (
    C_COS,
    C_EXP,
    C_LOG,
    INV_LN2,
    LN2_BAS,
    LN2_HAUT,
    PI,
    SQRT_DEMI,
    Hasard,
    cos,
    empreinte,
    empreinte_texte,
    exp,
    log,
    vers_hex,
)
from mini_modele.donnees import FICHIER_PRENOMS, decoder, donnees_par_defaut, preparer, prenoms_du_texte
from mini_modele.entrainement import PRESETS_MINI, TAUX_PROPOSES, Entraineur, ReglagesMini, taux
from mini_modele.exemple_attention import charger_exemple, detailler_exemple
from mini_modele.modele import (
    ConfigMini,
    avant,
    entropie_croisee,
    generer,
    initialiser,
    nombre_parametres,
    perte,
    perte_et_gradient,
)

DOSSIER_TESTS = Path(__file__).resolve().parent.parent / "tests"

# Entrées fixes : les cas limites (sous-normaux, débordements, −0, très petits et très grands).
# Pour exp, -745.0, -744.4, -740.0, -720.0 et -709.0 donnent des k de -1075 à -1023
# (la branche des résultats sous-normaux), 709.7 et 709.78 un k de 1024.
ENTREES_EXP = [
    -745.2, -745.0, -744.4, -740.0, -720.0, -709.0, -708.5, -50.0, -10.0, -1.0, -0.5, -1e-10,
    -0.0, 0.0, 1e-300, 1e-10, 0.25, 0.5, 1.0, 2.0, 10.0, 50.0, 700.0, 709.7, 709.78, 709.79, 710.0,
]
# Pour log, 2.225073858507201e-308 est le plus grand sous-normal.
ENTREES_LOG = [
    5e-324, 1e-310, 2.225073858507201e-308, 1e-300, 1e-10, 0.1, 0.5, SQRT_DEMI, 0.75, 1.0,
    1.0000001, 1.5, 2.0, 10.0, 1e10, 1e300, 1.7976931348623157e308,
]
ENTREES_COS = [0.0, 1e-8, 0.5, 1.0, PI * 0.25, PI * 0.5, 2.0, 3.0, PI]
# Les valeurs de l'empreinte : des signes, des sous-normaux, des infinis.
VALEURS_EMPREINTE = [0.0, -0.0, 1.0, -2.5, 0.1, PI, 5e-324, 1e300, float("inf"), float("-inf")]
TEXTE_EMPREINTE = "Élodie, Zoé et Maël"
GRAINE = 1234
# Avec l'écart-type 1, la dernière multiplication de gaussienne ne change rien :
# la suite « gaussienne_0_08 » (l'écart-type de l'initialisation du mini-modèle)
# vérifie aussi cette multiplication.
ECART_TYPE_ESSAI = 0.08


def tirer(graine: int, n: int, tirage: Callable[[Hasard], float]) -> list:
    """n tirages d'un Hasard(graine) neuf."""
    h = Hasard(graine)
    return [tirage(h) for _ in range(n)]


def paires(fonction: Callable[[float], float], entrees: list[float]) -> list[list[str]]:
    """[x, f(x)] pour chaque entrée, en motifs hexadécimaux."""
    return [[vers_hex(x), vers_hex(fonction(x))] for x in entrees]


def calculer_attendus_calcul() -> dict:
    """Les attendus du noyau de calcul (tests/attendus-calcul.json)."""
    entrees_exp = ENTREES_EXP + tirer(42, 200, lambda h: (h.uniforme() - 0.5) * 60)
    entrees_log = ENTREES_LOG + tirer(43, 200, lambda h: h.uniforme() * 100 + 0.001)
    entrees_cos = ENTREES_COS + tirer(44, 100, lambda h: h.uniforme() * PI)
    melange = list(range(20))
    Hasard(GRAINE).melanger(melange)
    return {
        "constantes": {
            "LN2_HAUT": vers_hex(LN2_HAUT),
            "LN2_BAS": vers_hex(LN2_BAS),
            "INV_LN2": vers_hex(INV_LN2),
            "SQRT_DEMI": vers_hex(SQRT_DEMI),
            "PI": vers_hex(PI),
        },
        # Les tables des séries : le TypeScript doit construire exactement les mêmes.
        "coefficients": {
            "C_EXP": [vers_hex(c) for c in C_EXP],
            "C_LOG": [vers_hex(c) for c in C_LOG],
            "C_COS": [vers_hex(c) for c in C_COS],
        },
        "exp": paires(exp, entrees_exp),
        "log": paires(log, entrees_log),
        "cos": paires(cos, entrees_cos),
        "hasard": {
            "graine": GRAINE,
            "suivant32": tirer(GRAINE, 20, lambda h: h.suivant32()),
            "uniforme": [vers_hex(u) for u in tirer(GRAINE, 20, lambda h: h.uniforme())],
            "gaussienne": [vers_hex(g) for g in tirer(GRAINE, 20, lambda h: h.gaussienne(1.0))],
            "gaussienne_0_08": [vers_hex(g) for g in tirer(GRAINE, 20, lambda h: h.gaussienne(ECART_TYPE_ESSAI))],
            "entier_10": tirer(GRAINE, 20, lambda h: h.entier(10)),
            "melange_20": melange,
        },
        "empreinte": {
            "valeurs": [vers_hex(v) for v in VALEURS_EMPREINTE],
            "empreinte": empreinte(VALEURS_EMPREINTE),
        },
        "empreinte_texte": {
            "texte": TEXTE_EMPREINTE,
            "empreinte": empreinte_texte(TEXTE_EMPREINTE),
        },
    }


def calculer_attendus_donnees() -> dict:
    """Les attendus des prénoms (tests/attendus-donnees.json) : le fichier, le vocabulaire et le partage."""
    texte = FICHIER_PRENOMS.read_bytes().decode("utf-8")
    donnees = preparer(prenoms_du_texte(texte))
    entrainement = [decoder(s, donnees.vocabulaire) for s in donnees.entrainement]
    validation = [decoder(s, donnees.vocabulaire) for s in donnees.validation]
    return {
        "nb_prenoms": len(entrainement) + len(validation),
        "empreinte_fichier": empreinte_texte(texte),
        "vocabulaire": donnees.vocabulaire,
        "nb_entrainement": len(entrainement),
        "nb_validation": len(validation),
        "entrainement_10": entrainement[:10],
        "validation_10": validation[:10],
        # Toute la suite, dans l'ordre : un seul prénom déplacé change l'empreinte.
        "empreinte_entrainement": empreinte_texte("\n".join(entrainement)),
        "empreinte_validation": empreinte_texte("\n".join(validation)),
    }


# Le mini-modèle : la graine des poids (celle de ton IA), et celle des prénoms
# inventés au départ (graine + 2 + pas, au pas 0, comme l'entraînement).
GRAINE_MODELE = 1234
GRAINE_GENERES = 1236


def calculer_attendus_du_modele() -> dict:
    """La clé « modele » : l'initialisation, la perte et le gradient d'un lot, la validation et la génération."""
    donnees = donnees_par_defaut()
    c = ConfigMini(taille_vocabulaire=len(donnees.vocabulaire))
    params = initialiser(c, Hasard(GRAINE_MODELE))
    lot = donnees.entrainement[:8]
    gradient = [0.0] * len(params)
    perte_lot = perte_et_gradient(c, params, lot, gradient)
    generes = generer(c, params, Hasard(GRAINE_GENERES), 8)
    # La perte de chaque position du lot, dans l'ordre : un ulp d'écart sur l'une d'elles
    # disparaît souvent dans la moyenne, mais pas dans cette empreinte.
    pertes_positions = []
    for seq in lot:
        passe = avant(c, params, seq[:-1])
        for t in range(len(seq) - 1):
            pertes_positions.append(entropie_croisee(passe[t].logits, seq[t + 1]))
    return {
        # Les noms des champs sont ceux du Python (taille_vocabulaire, largeur_mlp) : le TypeScript émet les mêmes.
        "config": dataclasses.asdict(c),
        "graine": GRAINE_MODELE,
        "nb_parametres": nombre_parametres(c),
        "init_empreinte": empreinte(params),
        "init_premiers": [vers_hex(p) for p in params[:8]],
        "lot": [list(s) for s in lot],
        "perte_lot": vers_hex(perte_lot),
        "pertes_positions_empreinte": empreinte(pertes_positions),
        # Tout le gradient, bit pour bit, dans l'empreinte : un seul écart d'un ulp la change.
        "gradient_empreinte": empreinte(gradient),
        "gradient_premiers": [vers_hex(g) for g in gradient[:8]],
        "perte_validation_256": vers_hex(perte(c, params, donnees.validation[:256])),
        "generes": [decoder(p, donnees.vocabulaire) for p in generes],
    }


# L'entraînement : le préréglage complet, sur PAS_ENTRAINEMENT pas.
PRESET_ENTRAINEMENT = "complet"
PAS_ENTRAINEMENT = 20
# Le taux du préréglage complet à ces pas : la montée, le sommet, le cosinus et la fin.
PAS_DU_PLANNING = (0, 1, 50, 99, 100, 101, 550, 1000, 1550, 2000, 2999, 3000, 3001)
# Un taux maximal absurde : l'erreur explose en quelques pas.
TAUX_QUI_DIVERGE = 1000.0


def reglages_en_attendus(r: ReglagesMini) -> dict:
    """Les champs des réglages, avec leurs noms Python : les entiers tels quels, les flottants en motifs."""
    return {nom: vers_hex(v) if isinstance(v, float) else v for nom, v in dataclasses.asdict(r).items()}


# Un entraînement court sur vingt prénoms de deux lettres (18 en entraînement, 2 en validation),
# pour comparer deux chemins que les 20 pas du préréglage complet ne prennent pas : avec des lots
# de 4, l'ordre est remélangé aux pas 5 et 9 (16 + 4 > 18) ; avec un écrêtage à 100, le gradient
# n'est jamais écrêté (sa norme reste sous 100). Dix pas sur 10 : la montée, le cosinus et la fin.
PRENOMS_COURT = (
    "an", "bo", "ci", "du", "el", "fa", "gu", "hi", "in", "jo", "ka", "lu", "ma", "ne", "ol", "pa", "qu", "ro", "su", "ti",
)
REGLAGES_COURT = ReglagesMini(pas_total=10, echauffement=2, lot=4, ecretage=100.0)


def calculer_attendus_court() -> dict:
    """La clé « court » de « entrainement » : 10 pas sur PRENOMS_COURT, lots de 4, écrêtage à 100."""
    e = Entraineur(REGLAGES_COURT, preparer(list(PRENOMS_COURT)))
    pertes = []
    taux_des_pas = []
    for _ in range(REGLAGES_COURT.pas_total):
        pertes.append(vers_hex(e.faire_un_pas()))
        taux_des_pas.append(vers_hex(e.taux_courant()))
    return {
        "prenoms": list(PRENOMS_COURT),
        "reglages": reglages_en_attendus(REGLAGES_COURT),
        "nb_pas": e.pas,
        "pertes": pertes,
        "taux": taux_des_pas,
        "validation": vers_hex(e.perte_validation()),
        "params_empreinte": empreinte(e.params),
        "params_premiers": [vers_hex(p) for p in e.params[:8]],
        "echantillons": e.echantillons(),
    }


def calculer_attendus_entrainement() -> dict:
    """La clé « entrainement » : 20 pas du préréglage complet, le planning du taux, une divergence, et le cas court."""
    reglages = PRESETS_MINI[PRESET_ENTRAINEMENT]
    e = Entraineur(reglages)
    validation_0 = e.perte_validation()
    echantillons_0 = e.echantillons()
    pertes = []
    taux_des_pas = []
    for _ in range(PAS_ENTRAINEMENT):
        pertes.append(vers_hex(e.faire_un_pas()))
        taux_des_pas.append(vers_hex(e.taux_courant()))
    fou = Entraineur(dataclasses.replace(reglages, taux_max=TAUX_QUI_DIVERGE))
    perte_folle = 0.0
    while not fou.diverge and fou.pas < 50:
        perte_folle = fou.faire_un_pas()
    if not fou.diverge:
        raise RuntimeError(f"Un taux maximal de {TAUX_QUI_DIVERGE} n'a pas fait diverger l'entraînement en 50 pas.")
    r = reglages
    return {
        "preset": PRESET_ENTRAINEMENT,
        "nb_pas": PAS_ENTRAINEMENT,
        # La perte de chaque lot et le taux de chaque pas, dans l'ordre des pas 1 à 20.
        "pertes": pertes,
        "taux": taux_des_pas,
        "validation_0": vers_hex(validation_0),
        "validation_20": vers_hex(e.perte_validation()),
        # Tous les paramètres après 20 pas, bit pour bit : un seul écart d'un ulp change l'empreinte.
        "params_empreinte_20": empreinte(e.params),
        "params_premiers_20": [vers_hex(p) for p in e.params[:8]],
        "echantillons_0": echantillons_0,
        "echantillons_20": e.echantillons(),
        "taux_planning": [[p, vers_hex(taux(p, r.pas_total, r.taux_max, r.echauffement, r.ratio_min))]
                          for p in PAS_DU_PLANNING],
        "divergence": {"taux_max": vers_hex(TAUX_QUI_DIVERGE), "pas": fou.pas, "perte": vers_hex(perte_folle)},
        "presets": {nom: reglages_en_attendus(p) for nom, p in PRESETS_MINI.items()},
        "taux_proposes": [vers_hex(x) for x in TAUX_PROPOSES],
        "court": calculer_attendus_court(),
    }


def calculer_attendus_modele() -> dict:
    """Les attendus du mini-modèle (tests/attendus-modele.json), une clé par partie.

    « modele » : la passe avant, la perte et la passe arrière. « entrainement » :
    les premiers pas, le taux, et un entraînement qui diverge.
    """
    return {"modele": calculer_attendus_du_modele(), "entrainement": calculer_attendus_entrainement()}


def motifs(matrice: list) -> list[list[str | None]]:
    """Chaque case en motif hexadécimal ; une case masquée (None) reste None, écrite null."""
    return [[None if v is None else vers_hex(v) for v in ligne] for ligne in matrice]


def calculer_attendus_attention() -> dict:
    """Les attendus de l'exemple d'attention (tests/attendus-attention.json) : tout le détail de chaque tête.

    Les scores masqués sont null ; les poids masqués valent +0,0 (motif 0000000000000000), comme dans le détail.
    """
    exemple = charger_exemple()
    tetes = []
    for tete, d in zip(exemple["tetes"], detailler_exemple(exemple)):
        tetes.append({
            "nom": tete["nom"],
            "requetes": motifs(d.requetes),
            "cles": motifs(d.cles),
            "valeurs": motifs(d.valeurs),
            "scores": motifs(d.scores),
            "scores_echelles": motifs(d.scores_echelles),
            "poids": motifs(d.poids),
            "sorties": motifs(d.sorties),
        })
    return {"phrase": exemple["phrase"], "jetons": exemple["jetons"], "tetes": tetes}


# Chaque fichier tests/attendus-<nom>.json et la fonction qui le calcule.
CALCULS: dict[str, Callable[[], dict]] = {
    "calcul": calculer_attendus_calcul,
    "donnees": calculer_attendus_donnees,
    "modele": calculer_attendus_modele,
    "attention": calculer_attendus_attention,
}


def ecrire_attendus() -> None:
    """Écrit chaque tests/attendus-<nom>.json (UTF-8, fins de ligne LF)."""
    for nom, calculer in CALCULS.items():
        chemin = DOSSIER_TESTS / f"attendus-{nom}.json"
        with open(chemin, "w", encoding="utf-8", newline="\n") as fichier:
            fichier.write(json.dumps(calculer(), ensure_ascii=False, indent=1) + "\n")
        print(f"Écrit : {chemin}")


if __name__ == "__main__":
    ecrire_attendus()
