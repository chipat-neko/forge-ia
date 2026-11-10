"""`python -m evaluation_pas_a_pas` : résumer l'évaluation de « mini », noter des questions de MMMLU, regarder dans le modèle.

    uv run --extra cpu python -m evaluation_pas_a_pas resumer --rapport <rapport.json> --json mesures/evaluation-mini.json
    uv run --extra cpu python -m evaluation_pas_a_pas qcm-exemples --sauvegarde <etape.pt> --appareil cpu --json mesures/qcm-mini.json
    uv run --extra cpu python -m evaluation_pas_a_pas cartes --sauvegarde <etape.pt> --phrase "Le forgeron dit qu'il" --couche 3 --tete 0 --appareil cpu --json cartes.json
    uv run --extra cpu python -m evaluation_pas_a_pas suivants --sauvegarde <etape.pt> --phrase "Il était une fois" --appareil cpu --json suivants.json

`resumer` lit le `rapport.json` de `python -m forge evaluer` et en tire le relevé que le site lit. `qcm-exemples` lit
quelques questions de MMMLU (en flux) et les note avec le modèle de la sauvegarde. `cartes` écrit les poids d'attention
d'une phrase, pour une couche et une tête\u202f; `suivants` les jetons que le modèle juge les plus probables après une
phrase. Les trois dernières prennent `--appareil` (`auto`, `cpu` ou `cuda`). Sans carte graphique, `--appareil cuda`
dit quoi faire, sans trace Python, et rend le code 2\u202f; de même sans PyTorch, ou avec une carte que PyTorch voit
sans savoir calculer dessus.
"""

import argparse
import datetime
import json
import sys
from pathlib import Path

try:
    import forge
    from forge.tokenizer.bpe_octets import TokenizerOctets

    from evaluation_pas_a_pas.qcm_exemples import exemples_mmmlu, noter_exemples
    from evaluation_pas_a_pas.regarder import cartes_attention, jetons_de_la_phrase, suivants, texte_du_jeton
    from evaluation_pas_a_pas.resumer import resumer
    from evaluation_pas_a_pas.sauvegarde import charger_sauvegarde
except ImportError as erreur:  # PyTorch (ou forge) manque : main() le dit, sans trace
    MANQUE: ImportError | None = erreur
else:
    MANQUE = None

FINE = "\u202f"  # l'espace fine insécable de la typographie française
TOKENIZER = Path(forge.__file__).resolve().parent / "ressources" / "tokenizer-ton-ia-v1.json" if MANQUE is None else None
CHIFFRES_DES_POIDS = 6  # décimales gardées dans le fichier des cartes


def nombre(n: float, decimales: int = 0) -> str:
    """Un nombre à la française : les milliers séparés par une espace fine, la virgule décimale."""
    return f"{n:,.{decimales}f}".replace(",", FINE).replace(".", ",")


def points(proportion: float) -> str:
    """Une marge en points de pourcentage : « 0,9 point », « 2,5 points » (le pluriel commence à 2)."""
    valeur = 100 * proportion
    return f"{nombre(valeur, 1)} point{'s' if valeur >= 2 else ''}"


def pourcent(proportion: float) -> str:
    return f"{nombre(100 * proportion, 1)}{FINE}%"


def carte_inutilisable(erreur: RuntimeError) -> str:
    """Le message quand PyTorch voit la carte, mais n'a pas pu calculer dessus : une carte trop
    ancienne ou trop récente pour sa version (le diagnostic du projet 0.3 dit laquelle), ou une
    carte dont la mémoire est déjà prise par un autre programme."""
    import torch  # déjà chargé : la carte vient d'être choisie

    texte = str(erreur).strip()
    premiere_ligne = texte.splitlines()[0].rstrip(".") if texte else type(erreur).__name__
    processeur = (
        "Pour calculer sur le processeur, relance avec `--appareil cpu` (ou, sans `--appareil`, mets FORGE_APPAREIL=cpu)."
    )
    if isinstance(erreur, torch.OutOfMemoryError):
        return (
            f"La carte graphique n’a plus assez de mémoire libre\u202f: {premiere_ligne}. "
            f"Un autre programme s’en sert peut-être\u202f: ferme-le, puis relance le script. {processeur}"
        )
    return (
        f"La carte graphique n’a pas pu calculer avec cette version de PyTorch\u202f: {premiere_ligne}. "
        f"Pour savoir pourquoi, lance `uv run --extra gpu python -m poste` dans le dossier projets/0.3-poste. {processeur}"
    )


def ecrire_en_utf8() -> None:
    """Une console Windows redirigée vers un fichier écrit en cp1252, qui ne connaît pas
    l'espace fine (U+202F) : on passe alors la sortie en UTF-8, plutôt que de planter."""
    for flux in (sys.stdout, sys.stderr):
        try:
            "\u202f’".encode(flux.encoding or "ascii")
        except (UnicodeEncodeError, LookupError):
            if hasattr(flux, "reconfigure"):
                flux.reconfigure(encoding="utf-8")


def ecrire_json(chemin: Path, donnees: dict) -> None:
    """Un fichier de mesures : UTF-8, fins de ligne LF, comme les autres mesures du dépôt."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with open(chemin, "w", encoding="utf-8", newline="\n") as fichier:
        fichier.write(json.dumps(donnees, ensure_ascii=False, allow_nan=False, indent=1) + "\n")


def aujourd_hui() -> str:
    return datetime.date.today().isoformat()


def nom_de_la_sauvegarde(sauvegarde: Path) -> str:
    """« ton-ia-mini » pour `…/ton-ia-mini/sauvegardes/etape-0006370.pt` ; le nom du fichier sinon."""
    chemin = Path(sauvegarde).resolve()
    return chemin.parent.parent.name if chemin.parent.name == "sauvegardes" else chemin.stem


def commande_resumer(options: argparse.Namespace) -> int:
    try:
        releve = resumer(Path(options.rapport), options.nom)
    except (FileNotFoundError, ValueError) as erreur:
        print(erreur, file=sys.stderr)
        return 2
    print(
        f"Évaluation de {releve['nom']} (pas {nombre(releve['pas'])}), relevée le {releve['releve_le']}{FINE}: "
        f"perte {nombre(releve['perte_val'], 3)}, perplexité {nombre(releve['perplexite'], 1)}, "
        f"{nombre(releve['bits_par_octet'], 3)} bit par octet"
    )
    for test, m in releve["qcm"].items():
        print(
            f"  {test}{FINE}: {pourcent(m['exactitude_normalisee'])} contre {pourcent(m['hasard'])} au hasard "
            f"(marge du hasard ± {points(m['marge_hasard'])}, {nombre(m['n'])} questions), {m['verdict']}"
        )
    print(f"  {len(releve['echantillons'])} échantillons de texte")
    if options.json:
        ecrire_json(Path(options.json), releve)
    return 0


def preparer(options: argparse.Namespace):
    """Le modèle de la sauvegarde, sur l'appareil choisi, et le tokenizer ; ou le code de sortie d'une erreur dite en français."""
    from evaluation_pas_a_pas.appareil import AppareilIndisponible, choisir_appareil

    try:
        ou = choisir_appareil(options.appareil)
    except (AppareilIndisponible, ValueError) as erreur:
        print(erreur, file=sys.stderr)
        return 2
    try:
        modele, config = charger_sauvegarde(Path(options.sauvegarde), ou.type)
        tokenizer = TokenizerOctets.charger(Path(options.tokenizer) if options.tokenizer else TOKENIZER)
    except (FileNotFoundError, ValueError) as erreur:
        print(erreur, file=sys.stderr)
        return 2
    except RuntimeError as erreur:
        if ou.type != "cuda":
            raise
        print(carte_inutilisable(erreur), file=sys.stderr)
        return 2
    return ou, modele, config, tokenizer


def sur_l_appareil(options: argparse.Namespace, travail) -> int:
    """Charge le modèle, puis lance `travail(ou, modele, config, tokenizer)`. Sur la carte, une panne de calcul est dite sans trace."""
    pret = preparer(options)
    if isinstance(pret, int):
        return pret
    ou = pret[0]
    try:
        return travail(*pret)
    except RuntimeError as erreur:
        if ou.type != "cuda":
            raise  # sur le processeur, c'est un défaut du projet : sa trace entière doit se voir
        print(carte_inutilisable(erreur), file=sys.stderr)
        return 2


def commande_qcm_exemples(options: argparse.Namespace) -> int:
    def travail(ou, modele, config, tokenizer) -> int:
        try:
            qcms = exemples_mmmlu(options.n, options.graine)
        except Exception as erreur:  # réseau coupé, Hugging Face indisponible, jeu changé…
            print(
                f"MMMLU n'a pas pu être lu sur Hugging Face ({type(erreur).__name__}{FINE}: {erreur}). "
                "Vérifie ta connexion, puis relance la commande.",
                file=sys.stderr,
            )
            return 2
        releve = {"nom": nom_de_la_sauvegarde(Path(options.sauvegarde)), "releve_le": aujourd_hui(), "appareil": ou.type}
        releve.update(noter_exemples(modele, tokenizer, qcms))
        jeu = releve["jeu"]
        print(f"{releve['n']} questions de {jeu['nom']} ({jeu['configuration']}), licence {jeu['licence']}, lues en flux sur {jeu['adresse']}")
        for numero, q in enumerate(releve["questions"], start=1):
            question = q["contexte"].split("\n")[0].removeprefix("Question : ")
            court = question if len(question) <= 90 else question[:89] + "…"
            print(
                f"  {numero}. {court}\n"
                f"     préférée{FINE}: {'ABCD'[q['prefere']]}, bonne réponse{FINE}: {'ABCD'[q['bonne']]}{FINE}; "
                f"{'juste' if q['juste'] else 'fausse'}"
            )
        print(f"{releve['justes']} justes sur {releve['n']} (le hasard donnerait {pourcent(releve['hasard'])})")
        if options.json:
            ecrire_json(Path(options.json), releve)
        return 0

    return sur_l_appareil(options, travail)


def commande_cartes(options: argparse.Namespace) -> int:
    import torch

    def travail(ou, modele, config, tokenizer) -> int:
        if not 0 <= options.couche < config.couches:
            print(
                f"La couche {options.couche} n'existe pas{FINE}: ce modèle a {config.couches} couches, de 0 à {config.couches - 1}. "
                "Corrige --couche.",
                file=sys.stderr,
            )
            return 2
        if not 0 <= options.tete < config.tetes:
            print(
                f"La tête {options.tete} n'existe pas{FINE}: ce modèle a {config.tetes} têtes, de 0 à {config.tetes - 1}. Corrige --tete.",
                file=sys.stderr,
            )
            return 2
        ids = jetons_de_la_phrase(tokenizer, options.phrase, config.longueur_contexte)
        cartes = cartes_attention(modele, torch.tensor(ids), options.couche)
        poids = [[round(float(x), CHIFFRES_DES_POIDS) for x in ligne] for ligne in cartes[options.tete]]
        jetons = [texte_du_jeton(tokenizer, i) for i in ids]
        releve = {
            "nom": nom_de_la_sauvegarde(Path(options.sauvegarde)),
            "releve_le": aujourd_hui(),
            "appareil": ou.type,
            "phrase": options.phrase,
            "jetons": jetons,
            "couche": options.couche,
            "couches": config.couches,
            "tete": options.tete,
            "tetes": config.tetes,
            "poids": poids,
        }
        print(f"Cartes d'attention de la couche {options.couche}, tête {options.tete} ({len(jetons)} jetons, sur {ou.type})")
        regardes = sorted(range(len(jetons)), key=lambda j: -poids[-1][j])[:3]
        print(
            f"  le dernier jeton ({jetons[-1]!r}) regarde surtout{FINE}: "
            + ", ".join(f"{jetons[j]!r} ({pourcent(poids[-1][j])})" for j in regardes)
        )
        if options.json:
            ecrire_json(Path(options.json), releve)
        return 0

    return sur_l_appareil(options, travail)


def commande_suivants(options: argparse.Namespace) -> int:
    def travail(ou, modele, config, tokenizer) -> int:
        liste = suivants(modele, tokenizer, options.phrase, options.k)
        releve = {
            "nom": nom_de_la_sauvegarde(Path(options.sauvegarde)),
            "releve_le": aujourd_hui(),
            "appareil": ou.type,
            "phrase": options.phrase,
            "suivants": [{"jeton": jeton, "probabilite": proba} for jeton, proba in liste],
        }
        print(f"Après {options.phrase!r}, les {len(liste)} jetons les plus probables (sur {ou.type})")
        for jeton, proba in liste:
            print(f"  {jeton!r:<14} {pourcent(proba)}")
        if options.json:
            ecrire_json(Path(options.json), releve)
        return 0

    return sur_l_appareil(options, travail)


def ajouter_modele(commande: argparse.ArgumentParser) -> None:
    """Les options des commandes qui chargent un modèle."""
    commande.add_argument("--sauvegarde", required=True, metavar="PT", help="une sauvegarde de forge (etape-*.pt ou meilleur.pt)")
    commande.add_argument("--tokenizer", metavar="JSON", help="le tokenizer du modèle (par défaut, le tokenizer figé de « ton IA »)")
    commande.add_argument("--appareil", help="auto (par défaut, sauf si FORGE_APPAREIL est réglée), cpu ou cuda", default=None)
    commande.add_argument("--json", metavar="FICHIER", help="écrit aussi le résultat dans FICHIER (JSON)")


def main(argv: list[str] | None = None) -> int:
    # Avant argparse, qui écrit lui-même ses messages d'erreur.
    ecrire_en_utf8()
    lecteur = argparse.ArgumentParser(
        prog="python -m evaluation_pas_a_pas",
        description="Résume l'évaluation de forge, note des questions de MMMLU, et regarde dans le modèle.",
    )
    commandes = lecteur.add_subparsers(dest="nom_commande", required=True, metavar="{resumer,qcm-exemples,cartes,suivants}")
    resume = commandes.add_parser("resumer", help="le relevé du rapport.json d'une évaluation de forge")
    resume.add_argument("--rapport", required=True, metavar="RAPPORT", help="le rapport.json écrit par `python -m forge evaluer`")
    resume.add_argument("--nom", metavar="NOM", help="le nom du relevé (par défaut, le dossier de l'entraînement : ton-ia-mini)")
    resume.add_argument("--json", metavar="FICHIER", help="écrit aussi le relevé dans FICHIER (JSON)")
    resume.set_defaults(fonction=commande_resumer)
    exemples = commandes.add_parser("qcm-exemples", help="des questions de MMMLU (français), notées par le modèle")
    ajouter_modele(exemples)
    exemples.add_argument("--n", type=int, default=6, help="le nombre de questions (6 par défaut)")
    exemples.add_argument("--graine", type=int, default=0, help="la graine du tirage des questions (0 par défaut)")
    exemples.set_defaults(fonction=commande_qcm_exemples)
    cartes = commandes.add_parser("cartes", help="les poids d'attention d'une phrase, pour une couche et une tête")
    ajouter_modele(cartes)
    cartes.add_argument("--phrase", required=True, help="la phrase à lire")
    cartes.add_argument("--couche", type=int, default=0, help="la couche, à partir de 0 (0 par défaut)")
    cartes.add_argument("--tete", type=int, default=0, help="la tête, à partir de 0 (0 par défaut)")
    cartes.set_defaults(fonction=commande_cartes)
    suivant = commandes.add_parser("suivants", help="les jetons que le modèle juge les plus probables après une phrase")
    ajouter_modele(suivant)
    suivant.add_argument("--phrase", required=True, help="le début du texte")
    suivant.add_argument("--k", type=int, default=10, help="combien de jetons (10 par défaut)")
    suivant.set_defaults(fonction=commande_suivants)
    options = lecteur.parse_args(argv)
    if MANQUE is not None:
        print(
            f"Un module manque ({MANQUE}). Lance le script avec la version de PyTorch de ton poste{FINE}: "
            "`uv run --extra cpu python -m evaluation_pas_a_pas …`, ou `--extra gpu` avec une carte NVIDIA.",
            file=sys.stderr,
        )
        return 2
    return options.fonction(options)


if __name__ == "__main__":
    sys.exit(main())
