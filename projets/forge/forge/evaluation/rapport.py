"""Le rapport d'évaluation de « ton IA » : `evaluer` mesure, puis écrit `rapport.json` et `rapport.md`.

`evaluer` charge une sauvegarde de l'entraînement (le modèle et sa configuration), puis mesure :

1. la perte de validation, la perplexité et les bits par octet, sur des morceaux fixes de `val/`
   (voir `perte.py`) ;
2. les QCM français de FrenchBench, comparés au hasard (voir `qcm.py`) ;
3. dix textes écrits à partir de débuts fixes, avec une graine fixe (voir `echantillons.py`).

`rapport.json` garde tous les nombres, pour les programmes ; `rapport.md` les raconte en
français, avec la typographie française (espace fine insécable avant « : », « ; », « ! », « ? »
et « % », et dans les guillemets), pour la personne qui lit.

Ce module ne doit importer de `forge.entrainement` que des sous-modules (`chargeur`,
`sauvegarde`), jamais le paquet : la boucle d'entraînement importe `forge.evaluation`.
"""

import dataclasses
import json
import math
import os
import re
import time
from datetime import datetime
from pathlib import Path

import torch

from forge.chemins import racine_donnees
from forge.donnees.jetons import _empreinte_du_tokenizer
from forge.entrainement.chargeur import ChargeurJetons
from forge.entrainement.sauvegarde import charger, charger_derniere, nom_etape, remplacer
from forge.evaluation.echantillons import TEMPERATURE, TOP_K, echantillons
from forge.evaluation.perte import bits_par_octet, lire_octets_par_jeton, perplexite, perte_validation
from forge.evaluation.qcm import TOTAL_DES_QUESTIONS, charger_frenchbench, evaluer_qcm
from forge.modele import ConfigModele, Transformer, nombre_parametres
from forge.tokenizer.bpe_octets import TokenizerOctets

VERSION_DU_RAPPORT = 1

# La perte de validation est mesurée sur 1 024 morceaux au plus (tous, s'il y en a moins), lus par
# lots de 8 : avec une longueur de contexte de 512, cela fait plus de 500 000 jetons, assez pour que
# la mesure bouge très peu d'une fois à l'autre ; avec 2 048, la mémoire de la carte reste modeste.
MORCEAUX_D_EVALUATION = 1024
MORCEAUX_PAR_LOT = 8
# La graine des échantillons et celle du chargeur (qui ne compte que si `val/` a plus de morceaux
# que `MORCEAUX_D_EVALUATION`).
GRAINE = 0
JETONS_D_ECHANTILLON = 60

# Les deux tests, dans l'ordre d'affichage, avec leur nom lisible.
TESTS_QCM = {"hellaswag": "HellaSwag (français)", "arc": "ARC-Challenge (français)"}

_FINE = " "  # l'espace fine insécable, de la typographie française


# --- Lire la sauvegarde et les données ----------------------------------------------------


def _lire_sauvegarde(chemin: Path) -> tuple[dict, str]:
    """Lit une sauvegarde de l'entraînement : un fichier `.pt`, ou le dossier `sauvegardes/`.

    Un dossier donne sa dernière `etape-*.pt`. Renvoie la sauvegarde et le fichier lu.
    """
    # Import ici : la boucle d'entraînement importe ce paquet (voir l'en-tête du module).
    from forge.entrainement.boucle import VERSION_DE_LA_SAUVEGARDE

    if chemin.is_dir():
        etat = charger_derniere(chemin)
        if etat is None:
            raise FileNotFoundError(
                f"Aucune sauvegarde etape-*.pt dans {chemin}. Donne un fichier .pt, par exemple {chemin / 'meilleur.pt'}."
            )
        lu = str(chemin / nom_etape(etat["pas"])) if "pas" in etat else str(chemin)
    elif chemin.is_file():
        try:
            etat = charger(chemin)
        except Exception as erreur:  # fichier tronqué, ou qui n'est pas de PyTorch
            raise ValueError(
                f"{chemin} ne se lit pas comme une sauvegarde de la forge ({type(erreur).__name__}). "
                "Prends un fichier etape-*.pt ou meilleur.pt du dossier sauvegardes/ d'un entraînement."
            ) from erreur
        lu = str(chemin)
    else:
        raise FileNotFoundError(
            f"Sauvegarde introuvable : {chemin}. Donne un fichier .pt du dossier sauvegardes/ d'un "
            "entraînement (etape-*.pt ou meilleur.pt)."
        )
    if not isinstance(etat, dict) or "modele" not in etat or "config_modele" not in etat:
        raise ValueError(
            f"{chemin} n'est pas une sauvegarde de la forge : il n'y a ni « modele » ni « config_modele » "
            "dedans. Prends un fichier etape-*.pt ou meilleur.pt du dossier sauvegardes/ d'un entraînement."
        )
    if etat.get("version") != VERSION_DE_LA_SAUVEGARDE:
        raise ValueError(
            f"Sauvegarde de version {etat.get('version')!r} : cette version de la forge lit la "
            f"version {VERSION_DE_LA_SAUVEGARDE}."
        )
    return etat, lu


def _dossier_des_jetons(donnees: Path) -> Path:
    """Un chemin absolu est gardé tel quel ; un nom va sous `FORGE_DONNEES/jetons/` (comme l'entraînement)."""
    donnees = Path(donnees)
    return donnees if donnees.is_absolute() else racine_donnees() / "jetons" / donnees


def _verifier_tokenizer(tokenizer: TokenizerOctets, fichier: Path, config: ConfigModele, donnees: Path) -> None:
    """Refuse un tokenizer qui n'est pas celui du modèle ni celui de l'encodage des données."""
    if tokenizer.taille_vocabulaire != config.taille_vocabulaire:
        raise ValueError(
            f"Le tokenizer {fichier} a {tokenizer.taille_vocabulaire} jetons, mais le modèle de la "
            f"sauvegarde en attend {config.taille_vocabulaire}. Donne le tokenizer avec lequel le "
            "modèle a été entraîné (--tokenizer)."
        )
    try:
        index = json.loads((donnees / "index.json").read_text(encoding="utf-8"))
        empreinte = index["tokenizer"]["empreinte"]
    except (OSError, ValueError, KeyError, TypeError):
        return  # pas d'empreinte dans l'index : on ne peut pas comparer
    if empreinte != _empreinte_du_tokenizer(tokenizer):
        raise ValueError(
            f"Les jetons de {donnees} ont été encodés avec un autre tokenizer que {fichier} : les "
            "mesures n'auraient aucun sens. Donne le tokenizer qui a servi à `python -m forge encoder` "
            "(--tokenizer), ou réencode les données avec celui-ci."
        )


def _choisir_appareil(appareil: str | None) -> torch.device:
    if appareil is None:
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if appareil not in ("cuda", "cpu"):
        raise ValueError(f'appareil vaut {appareil!r} : écris "cuda" (carte graphique) ou "cpu".')
    if appareil == "cuda" and not torch.cuda.is_available():
        raise ValueError(
            'appareil = "cuda", mais PyTorch ne voit aucune carte graphique NVIDIA. Lance la commande '
            "avec `uv run --extra gpu …`, ou choisis le processeur (--appareil cpu)."
        )
    return torch.device(appareil)


# --- Mesurer ------------------------------------------------------------------------------


def evaluer(
    sauvegarde: Path,
    donnees: Path,
    tokenizer: Path,
    sortie: Path,
    n_qcm: int | None = None,
    appareil: str | None = None,
) -> dict:
    """Évalue une sauvegarde ; écrit `sortie/rapport.json` et `sortie/rapport.md` ; renvoie le rapport.

    - `sauvegarde` : un fichier `.pt` de l'entraînement (`etape-*.pt`, `meilleur.pt`), ou le
      dossier `sauvegardes/` (sa dernière étape) ;
    - `donnees` : le dossier des jetons (un nom va sous `FORGE_DONNEES/jetons/`) ; sa partie
      `val/` donne la perte de validation, et son index le nombre d'octets par jeton ;
    - `tokenizer` : le fichier JSON du tokenizer, celui de l'entraînement ;
    - `sortie` : le dossier des deux rapports (créé au besoin) ;
    - `n_qcm` : nombre de questions de chaque test FrenchBench (`None` : toutes, `0` : aucun
      QCM, sans réseau) ;
    - `appareil` : « cuda » ou « cpu » (la carte graphique si PyTorch la voit, par défaut). Sur
      la carte, les calculs se font en bf16.

    Si FrenchBench est injoignable (réseau coupé…), le rapport garde les autres mesures et dit
    pourquoi les QCM manquent (`"erreur"` dans `qcm`).
    """
    if n_qcm is not None and n_qcm < 0:
        raise ValueError(f"n_qcm vaut {n_qcm} : il faut un nombre de questions positif ou nul, ou None pour toutes.")
    debut = time.perf_counter()
    sauvegarde, tokenizer, sortie = Path(sauvegarde), Path(tokenizer), Path(sortie)
    appareil_choisi = _choisir_appareil(appareil)
    dossier_jetons = _dossier_des_jetons(donnees)
    etat, fichier_lu = _lire_sauvegarde(sauvegarde)
    config = ConfigModele(**etat["config_modele"])
    tok = TokenizerOctets.charger(tokenizer)

    # Les données d'abord : elles échouent vite, avant de charger le modèle.
    chargeur = ChargeurJetons(dossier_jetons / "val", config.longueur_contexte, MORCEAUX_PAR_LOT, GRAINE)
    _verifier_tokenizer(tok, tokenizer, config, dossier_jetons)
    octets_par_jeton = lire_octets_par_jeton(dossier_jetons)

    if appareil_choisi.type == "cpu":
        torch.set_num_threads(os.cpu_count() or 1)  # tous les fils du processeur
    modele = Transformer(config)
    try:
        modele.load_state_dict(etat["modele"])
    except RuntimeError as erreur:
        raise ValueError(
            f"Les poids de {fichier_lu} ne correspondent pas au modèle que sa configuration décrit "
            f"({str(erreur).splitlines()[0]}). La sauvegarde est abîmée, ou d'une autre version de la forge."
        ) from erreur
    pas = etat.get("pas")
    del etat  # la copie des poids en mémoire ne sert plus
    modele.to(appareil_choisi).eval()

    n_morceaux = min(MORCEAUX_D_EVALUATION, chargeur.morceaux)
    perte = perte_validation(modele, chargeur, -(-MORCEAUX_D_EVALUATION // MORCEAUX_PAR_LOT))

    qcm = {}
    if n_qcm != 0:
        for nom in TESTS_QCM:
            try:
                questions = charger_frenchbench(nom, n_qcm)
            except Exception as erreur:  # réseau coupé, Hugging Face indisponible, jeu changé…
                qcm[nom] = {"erreur": f"{type(erreur).__name__}{_FINE}: {erreur}"}
                continue
            qcm[nom] = {**evaluer_qcm(modele, tok, questions), "total_du_test": TOTAL_DES_QUESTIONS[nom]}

    textes = echantillons(modele, tok, GRAINE, JETONS_D_ECHANTILLON)

    rapport = {
        "version": VERSION_DU_RAPPORT,
        "date": datetime.now().astimezone().isoformat(timespec="seconds"),
        "sauvegarde": fichier_lu,
        "pas": pas,
        "modele": {**dataclasses.asdict(config), "parametres": nombre_parametres(config)},
        "tokenizer": {"nom": tok.nom, "taille_vocabulaire": tok.taille_vocabulaire, "fichier": str(tokenizer)},
        "donnees": str(dossier_jetons),
        "appareil": appareil_choisi.type,
        "morceaux_val": n_morceaux,
        "longueur_val": config.longueur_contexte,
        "perte_val": perte,
        "perte_hasard": math.log(config.taille_vocabulaire),
        "perplexite": perplexite(perte),
        "octets_par_jeton": octets_par_jeton,
        "bits_par_octet": bits_par_octet(perte, octets_par_jeton),
        "n_qcm": n_qcm,
        "qcm": qcm,
        "generation": {"temperature": TEMPERATURE, "top_k": TOP_K, "n_nouveaux": JETONS_D_ECHANTILLON, "graine": GRAINE},
        "echantillons": textes,
        "secondes": round(time.perf_counter() - debut, 1),
    }
    sortie.mkdir(parents=True, exist_ok=True)
    _ecrire_texte(
        sortie / "rapport.json",
        json.dumps(_json_valide(rapport), ensure_ascii=False, indent=2, allow_nan=False) + "\n",
    )
    _ecrire_texte(sortie / "rapport.md", rapport_markdown(rapport))
    return rapport


def _json_valide(valeur):
    """Copie de `valeur` où chaque nombre infini ou « NaN » devient `None` (`null` en JSON).

    Python écrit `Infinity` et `NaN`, que JSON ne connaît pas : beaucoup d'analyseurs les refusent.
    Cela arrive, par exemple, pour la perplexité d'un modèle dont la perte dépasse 709 nats.
    """
    if isinstance(valeur, float) and not math.isfinite(valeur):
        return None
    if isinstance(valeur, dict):
        return {cle: _json_valide(element) for cle, element in valeur.items()}
    if isinstance(valeur, list | tuple):
        return [_json_valide(element) for element in valeur]
    return valeur


def _ecrire_texte(chemin: Path, texte: str) -> None:
    """Écrit `chemin` d'un coup (UTF-8, fins de ligne `\\n`) : un fichier à moitié écrit n'existe jamais."""
    temporaire = chemin.with_name(chemin.name + ".tmp")
    with open(temporaire, "w", encoding="utf-8", newline="\n") as fichier:
        fichier.write(texte)
        fichier.flush()
        os.fsync(fichier.fileno())
    remplacer(temporaire, chemin)


# --- Raconter en français -----------------------------------------------------------------


def _n(valeur: float | None, decimales: int = 1) -> str:
    """Un nombre à la française : virgule décimale, espace fine entre les milliers.

    Un nombre infini s'écrit « ∞ » ; un nombre indéfini (`NaN`, ou `None` lu dans un rapport JSON)
    « indéfini ».
    """
    if valeur is None or math.isnan(valeur):
        return "indéfini"
    if math.isinf(valeur):
        return "∞" if valeur > 0 else "−∞"
    return f"{valeur:,.{decimales}f}".replace(",", _FINE).replace(".", ",")


def _points(pourcentage: float) -> str:
    """Une marge en points de pourcentage : « 8,5 points », « 0,9 point » (le pluriel commence à 2)."""
    return f"{_n(pourcentage)} point{'s' if pourcentage >= 2 else ''}"


def _pourcent(proportion: float) -> str:
    return f"{_n(100 * proportion)}{_FINE}%"


def _guillemets(texte: str) -> str:
    return f"«{_FINE}{texte}{_FINE}»"


def verdict(mesures: dict) -> str:
    """« au-dessus du hasard », « en dessous du hasard » ou « pas différent du hasard ».

    On compare l'exactitude normalisée au hasard, avec la marge du HASARD (`marge_hasard`, voir
    `qcm.evaluer_qcm`) : on demande si un tirage au sort pourrait donner ce score. La marge de la
    mesure elle-même s'annule à 0 ou 100 % de bonnes réponses et affirmerait « en dessous du hasard »
    sur 0 bonne réponse sur 5, ce qui arrive une fois sur quatre au hasard avec 4 choix.
    """
    ecart = mesures["exactitude_normalisee"] - mesures["hasard"]
    if ecart > mesures["marge_hasard"]:
        return "au-dessus du hasard"
    if ecart < -mesures["marge_hasard"]:
        return "en dessous du hasard"
    return "pas différent du hasard"


def _bloc_de_code(texte: str, langage: str) -> str:
    """Un bloc de code Markdown dont la clôture est plus longue que toute suite d'apostrophes inverses du texte."""
    plus_longue = max((len(suite) for suite in re.findall(r"`+", texte)), default=0)
    cloture = "`" * max(3, plus_longue + 1)
    return f"{cloture}{langage}\n{texte}\n{cloture}"


def rapport_markdown(rapport: dict) -> str:
    """Le rapport en Markdown, en français (voir `evaluer` pour le contenu de `rapport`)."""
    c = rapport["modele"]
    appareil = "la carte graphique (bf16)" if rapport["appareil"] == "cuda" else "le processeur"
    lignes = [
        f"# Évaluation de {_guillemets('ton IA')}",
        "",
        f"- **Sauvegarde{_FINE}:** `{rapport['sauvegarde']}` (pas {_n(rapport['pas'], 0)})",
        f"- **Modèle{_FINE}:** {_n(c['parametres'] / 1e6)}{_FINE}M de paramètres, dimension {c['dim']}, "
        f"{c['couches']} couches, {c['tetes']} têtes, contexte de {_n(c['longueur_contexte'], 0)} jetons",
        f"- **Tokenizer{_FINE}:** {rapport['tokenizer']['nom']}, {_n(rapport['tokenizer']['taille_vocabulaire'], 0)} jetons",
        f"- **Données de validation{_FINE}:** `{rapport['donnees']}`, {_n(rapport['morceaux_val'], 0)} morceaux de "
        f"{_n(rapport['longueur_val'], 0)} jetons, soit {_n(rapport['morceaux_val'] * rapport['longueur_val'], 0)} jetons",
        f"- **Calcul{_FINE}:** sur {appareil}, en {_n(rapport['secondes'])}{_FINE}s, le "
        f"{rapport['date'][8:10]}/{rapport['date'][5:7]}/{rapport['date'][:4]}",
        "",
        "## Perte et perplexité",
        "",
        "| Mesure | Valeur | Ce que cela veut dire |",
        "| --- | --- | --- |",
        f"| Perte de validation | {_n(rapport['perte_val'], 3)} nats par jeton | "
        f"la moyenne, sur des textes jamais appris, de −ln(probabilité donnée au vrai jeton suivant){_FINE}; plus c'est "
        "bas, mieux c'est |",
        f"| Perte d'un modèle qui devine au hasard | {_n(rapport['perte_hasard'], 3)} nats par jeton | "
        f"ln({_n(c['taille_vocabulaire'], 0)}), le point de départ d'un modèle sans entraînement |",
        f"| Perplexité | {_n(rapport['perplexite'])} | exp(perte){_FINE}: le modèle hésite comme s'il choisissait "
        "entre autant de jetons également probables |",
        f"| Octets par jeton | {_n(rapport['octets_par_jeton'], 2)} | la taille moyenne d'un jeton dans les données encodées |",
        f"| Bits par octet (estimation) | {_n(rapport['bits_par_octet'], 3)} | perte ÷ ln 2 ÷ octets par jeton{_FINE}: "
        "la perte ramenée à un octet de texte, comparable d'un tokenizer à l'autre. "
        f"Estimation{_FINE}: octets par jeton du corpus entier{_FINE}; la perte compte aussi les fins de texte "
        "(écart attendu de l'ordre de quelques millièmes) |",
        "",
        "## Questions à choix multiples (FrenchBench)",
        "",
    ]
    qcm = rapport["qcm"]
    if not qcm:
        lignes += [f"QCM non évalués{_FINE}: cette évaluation a été lancée sans question (`n_qcm = 0`).", ""]
    else:
        lignes += [
            "| Test | Questions | Exactitude | Exactitude normalisée | Hasard | Marge du hasard | Verdict |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
        erreurs = []
        for nom, titre in TESTS_QCM.items():
            mesures = qcm.get(nom)
            if mesures is None:
                continue
            if "erreur" in mesures:
                erreurs.append(f"- **{titre}{_FINE}:** non évalué. {mesures['erreur']}")
                continue
            questions = _n(mesures["n"], 0)
            if rapport["n_qcm"] is not None and mesures["n"] < mesures["total_du_test"]:
                questions = f"{mesures['n']} premières questions sur {_n(mesures['total_du_test'], 0)}"
            lignes.append(
                f"| {titre} | {questions} | {_pourcent(mesures['exactitude'])} "
                f"| {_pourcent(mesures['exactitude_normalisee'])} | {_pourcent(mesures['hasard'])} "
                f"| ± {_points(100 * mesures['marge_hasard'])} | {verdict(mesures)} |"
            )
        lignes.append("")
        if erreurs:
            lignes += [
                *erreurs,
                "",
                f"Relance `python -m forge evaluer` quand le réseau est de retour{_FINE}: la commande lève elle-même "
                "`HF_HUB_OFFLINE` le temps de charger FrenchBench.",
                "",
            ]
        lignes += [
            f"- **Exactitude**{_FINE}: le modèle {_guillemets('répond')} par le choix dont le texte lui paraît le "
            "plus vraisemblable (somme des log-vraisemblances de ses jetons, sachant la question).",
            f"- **Exactitude normalisée**{_FINE}: même chose, après avoir divisé chaque log-vraisemblance par "
            "le nombre d'octets du choix, pour ne pas favoriser les réponses courtes.",
            f"- **Hasard**{_FINE}: la part de bonnes réponses d'un tirage au sort (1 ÷ nombre de choix, en "
            "moyenne sur les questions).",
            f"- **Marge du hasard**{_FINE}: la demi-largeur de l'intervalle à 95{_FINE}% d'un résultat qui ne devrait "
            f"qu'au hasard, sur ces questions. Le verdict compare l'exactitude normalisée au hasard{_FINE}: à moins "
            "d'une marge du hasard, le score ne se distingue pas du hasard (avec peu de questions, presque "
            "tout score est dans ce cas).",
            f"- **Mesure maison**{_FINE}: comparable seulement entre nos modèles et au hasard, pas aux scores "
            f"publiés de FrenchBench{_FINE}; le gabarit des questions ({_guillemets(f'Question{_FINE}: … Réponse{_FINE}:')} "
            "pour ARC, aucune étiquette d'activité pour HellaSwag), le jeton `<|fin_texte|>` placé en tête de chaque "
            "séquence et la normalisation par octets sont les nôtres.",
            "- Les deux tests sont des traductions automatiques en français de HellaSwag et d'ARC-Challenge "
            f"(CroissantLLM, arXiv 2402.00786){_FINE}: quelques questions sont mal traduites.",
            "",
        ]
    g = rapport["generation"]
    lignes += [
        "## Échantillons",
        "",
        f"Dix textes écrits par le modèle à partir d'un début donné (le titre de chaque bloc). Réglages{_FINE}: "
        f"température {_n(g['temperature'])}, top-k {g['top_k']}, {g['n_nouveaux']} jetons au plus, graine "
        f"{g['graine']} (puis {g['graine'] + 1}, {g['graine'] + 2}… pour les invites suivantes). Mêmes "
        "réglages, mêmes textes.",
        "",
    ]
    for numero, echantillon in enumerate(rapport["echantillons"], start=1):
        invite = echantillon["invite"]
        langage = "python" if invite.startswith("def ") else "text"
        lignes += [
            f"### {numero}. {_guillemets(invite.splitlines()[0])}",
            "",
            _bloc_de_code(invite + echantillon["suite"], langage),
            "",
        ]
        if echantillon["s_arrete"]:
            lignes += [f"Le modèle a écrit `<|fin_texte|>`{_FINE}: il a choisi de s'arrêter là.", ""]
    return "\n".join(lignes)


def resume_court(rapport: dict) -> str:
    """Les chiffres principaux, en quelques lignes pour l'écran."""
    lignes = [
        f"Perte de validation{_FINE}: {_n(rapport['perte_val'], 3)} nats par jeton",
        f"Perplexité{_FINE}: {_n(rapport['perplexite'])}",
        f"Bits par octet{_FINE}: {_n(rapport['bits_par_octet'], 3)} (estimation, avec {_n(rapport['octets_par_jeton'], 2)} "
        "octets par jeton)",
    ]
    for nom, titre in TESTS_QCM.items():
        mesures = rapport["qcm"].get(nom)
        if mesures is None:
            continue
        if "erreur" in mesures:
            lignes.append(f"{titre}{_FINE}: non évalué ({mesures['erreur']})")
        else:
            lignes.append(
                f"{titre}{_FINE}: {_pourcent(mesures['exactitude'])}, normalisée {_pourcent(mesures['exactitude_normalisee'])}, "
                f"hasard {_pourcent(mesures['hasard'])}, sur {_n(mesures['n'], 0)} questions ({verdict(mesures)})"
            )
    return "\n".join(lignes)
