"""`python -m conversation_pas_a_pas` : montrer une conversation en jetons, mesurer la fuite, faire le petit affinage, résumer.

    uv run --extra cpu python -m conversation_pas_a_pas montrer "Quelle est la capitale de la France ?" --reponse "Paris."
    uv run --extra cpu python -m conversation_pas_a_pas fuite --enregistrer sorties/fuite.txt --json mesures/fuite.json
    uv run --extra cpu python -m conversation_pas_a_pas essai --appareil cpu --enregistrer sorties/essai-processeur.txt --json mesures/essai-processeur.json
    uv run --extra cpu python -m conversation_pas_a_pas resumer --rapport <rapport.json> --json mesures/etape-ton-ia-1.7.json
    uv run --extra cpu python -m conversation_pas_a_pas resumer --rapport <rapport.json> --reference --json mesures/etape-ton-ia-1.5.json
    uv run --extra cpu python -m conversation_pas_a_pas longueurs --jeu <affinage/sft-1.7> --json mesures/longueurs-sft-1.7.json

`montrer` écrit une conversation jeton par jeton : l'identifiant, le texte, le rôle de celui qui parle, et
si le jeton est une cible apprise (`*`). `fuite` mesure ce que deux conversations d'une même rangée se
voient quand on ne les sépare pas. `essai` pré-entraîne un modèle minuscule puis l'affine 80 pas sur 24
conversations. `resumer` tire du `rapport.json` de `python -m forge evaluer-etape` le relevé que le site lit (avec
`--reference`, celui de la version de référence du rapport), et `longueurs` compte les longueurs des exemples
d'un jeu d'affinage, en le lisant seulement. Sans carte graphique, `--appareil cuda` dit quoi faire, sans
trace Python, et rend le code 2\u202f; de même sans PyTorch.
"""

import argparse
import datetime
import json
import os
import sys
from pathlib import Path

try:
    import torch
    from forge.conversation.format import Tour
    from forge.modele import nombre_parametres
    from forge.tokenizer import TokenizerOctets

    from conversation_pas_a_pas.fuite import CONFIG as CONFIG_DE_LA_FUITE
    from conversation_pas_a_pas.fuite import ecarts_de_fuite
    from conversation_pas_a_pas.gabarit import TOKENIZER, montrer
    from conversation_pas_a_pas.petit_affinage import CONTEXTE, INVITES, LOT_D_AFFINAGE, MODELE, essai_affinage
    from conversation_pas_a_pas.resumer import longueurs, resumer_etape
except ImportError as erreur:  # PyTorch (ou forge) manque : main() le dit, sans trace
    MANQUE: ImportError | None = erreur
else:
    MANQUE = None

FINE = "\u202f"  # l'espace fine insécable de la typographie française


def nombre(n: float, decimales: int = 0) -> str:
    """Un nombre à la française : les milliers séparés par une espace fine, la virgule décimale."""
    return f"{n:,.{decimales}f}".replace(",", FINE).replace(".", ",")


def ecart_en_francais(x: float) -> str:
    """Un écart en notation scientifique à la française (« 4,4e-07 »), ou « 0 » s'il est nul."""
    return "0" if x == 0 else f"{x:.1e}".replace(".", ",")


def pourcent(proportion: float) -> str:
    return f"{nombre(100 * proportion, 0)}{FINE}%"


def carte_inutilisable(erreur: RuntimeError) -> str:
    """Le message quand PyTorch voit la carte, mais n'a pas pu calculer dessus : une carte trop
    ancienne ou trop récente pour sa version (le diagnostic du projet 0.3 dit laquelle), ou une
    carte dont la mémoire est déjà prise par un autre programme."""
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
            "\u202f’␊".encode(flux.encoding or "ascii")
        except (UnicodeEncodeError, LookupError):
            if hasattr(flux, "reconfigure"):
                flux.reconfigure(encoding="utf-8")


def ecrire_json(chemin: Path, donnees: dict) -> None:
    """Un fichier de mesures : UTF-8, fins de ligne LF, comme les autres mesures du dépôt."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with open(chemin, "w", encoding="utf-8", newline="\n") as fichier:
        fichier.write(json.dumps(donnees, ensure_ascii=False, allow_nan=False, indent=1) + "\n")


def enregistrer(chemin: str | None, lignes: list[str]) -> None:
    """La sortie d'une commande dans un fichier (UTF-8, LF), précédée de la date du relevé."""
    if chemin:
        fichier = Path(chemin)
        fichier.parent.mkdir(parents=True, exist_ok=True)
        with open(fichier, "w", encoding="utf-8", newline="\n") as sortie:
            sortie.write(f"# relevé le {aujourd_hui()}\n" + "\n".join(lignes) + "\n")


def aujourd_hui() -> str:
    return datetime.date.today().isoformat()


def commande_montrer(options: argparse.Namespace) -> int:
    tours = []
    if options.systeme:
        tours.append(Tour("systeme", options.systeme))
    tours += [Tour("utilisateur", options.texte), Tour("assistant", options.reponse)]
    try:
        jetons = montrer(TokenizerOctets.charger(TOKENIZER), tours)
    except ValueError as erreur:
        print(erreur, file=sys.stderr)
        return 2
    print(f"{'id':>6}  {'jeton':<18} {'rôle':<12} appris")
    for j in jetons:
        print(f"{j['id']:>6}  {j['texte']!r:<18} {j['role']:<12} {'*' if j['appris'] else ''}")
    appris = sum(j["appris"] for j in jetons)
    print(f"{len(jetons)} jetons, dont {appris} appris : seuls les jetons de l'assistant, après `<|assistant|>`, comptent dans la perte.")
    return 0


def lignes_de_fuite(r: dict) -> list[str]:
    return [
        f"La fuite entre deux conversations d’une même rangée, sur un modèle minuscule tiré de la graine {r['graine']}",
        f"  modèle{FINE}: dim {CONFIG_DE_LA_FUITE.dim}, {CONFIG_DE_LA_FUITE.couches} couches, {CONFIG_DE_LA_FUITE.tetes} têtes, "
        f"contexte {CONFIG_DE_LA_FUITE.longueur_contexte} ({nombre(nombre_parametres(CONFIG_DE_LA_FUITE))} paramètres, PyTorch {torch.__version__.split('+')[0]})",
        f"  rangée{FINE}: conversation A ({r['jetons_a']} jetons), puis conversation B ({r['jetons_b']} jetons)",
        f"  écart maximal des logits de B, dans la rangée, face à B lue seule{FINE}:",
        f"    avec le masque par document{FINE}: {ecart_en_francais(r['avec_masque'])}",
        f"    sans le masque{FINE}: {ecart_en_francais(r['sans_masque'])}",
        f"B voit A sans le masque{FINE}: {'oui' if r['sans_masque'] > 1e-3 else 'non'}",
    ]


def commande_fuite(options: argparse.Namespace) -> int:
    r = ecarts_de_fuite(options.graine)
    lignes = lignes_de_fuite(r)
    print("\n".join(lignes))
    enregistrer(options.enregistrer, lignes)
    if options.json:
        ecrire_json(Path(options.json), {"releve_le": aujourd_hui(), **r})
    # Avec le masque, B ne doit presque rien voir de A ; sans lui, elle doit le voir.
    return 0 if r["avec_masque"] <= 1e-5 and r["sans_masque"] > 1e-3 else 1


def lignes_d_essai(r: dict, materiel: str) -> list[str]:
    reponses = [
        f"    {e['invite']!r} → {e['texte'][:60].replace(chr(10), ' ')!r}{'' if e['terminee'] else ' (coupée)'}"
        for e in r["reponses_apres"][:3]
    ]
    return [
        f"Un tout petit affinage, sur {materiel}",
        f"  modèle{FINE}: dim {MODELE.dim}, {MODELE.couches} couches, {MODELE.tetes} têtes, contexte {CONTEXTE} "
        f"({nombre(r['parametres'])} paramètres, PyTorch {torch.__version__.split('+')[0]})",
        f"  jeu{FINE}: {r['exemples']} conversations en {r['rangees']} rangées, {nombre(r['jetons'])} jetons dont {nombre(r['jetons_appris'])} appris",
        f"  {r['pas']} pas de {LOT_D_AFFINAGE} rangées{FINE}: perte {nombre(r['pertes'][0], 3)} au pas 1, {nombre(r['pertes'][-1], 3)} au pas {r['pas']}",
        f"  réponses aux {len(INVITES)} questions neuves qui finissent par <|fin_tour|>{FINE}: {pourcent(r['fin_de_tour_avant'])} avant, {pourcent(r['fin_de_tour_apres'])} après",
        "  trois réponses, après l'affinage" + FINE + ":",
        *reponses,
        f"  {nombre(r['secondes'], 1)} s pour le pré-entraînement, l'affinage et les deux mesures",
        f"le modèle a appris à finir son tour{FINE}: {'oui' if r['fin_de_tour_apres'] > r['fin_de_tour_avant'] else 'non'}",
    ]


def commande_essai(options: argparse.Namespace) -> int:
    from conversation_pas_a_pas.appareil import AppareilIndisponible, choisir_appareil

    try:
        ou = choisir_appareil(options.appareil)
    except (AppareilIndisponible, ValueError) as erreur:
        print(erreur, file=sys.stderr)
        return 2
    if ou.type == "cuda":
        materiel = f"la carte graphique, {torch.cuda.get_device_name(ou)}"
    else:
        materiel = f"le processeur ({os.cpu_count()} cœurs logiques)"
    try:
        r = essai_affinage(ou.type, pas=options.pas)
    except RuntimeError as erreur:
        if ou.type != "cuda":
            raise  # sur le processeur, c'est un défaut du projet : sa trace entière doit se voir
        print(carte_inutilisable(erreur), file=sys.stderr)
        return 2
    lignes = lignes_d_essai(r, materiel)
    print("\n".join(lignes))
    enregistrer(options.enregistrer, lignes)
    if options.json:
        ecrire_json(Path(options.json), {"releve_le": aujourd_hui(), **r})
    return 0 if r["fin_de_tour_apres"] > r["fin_de_tour_avant"] else 1


def commande_resumer(options: argparse.Namespace) -> int:
    try:
        releve = resumer_etape(Path(options.rapport), options.reference)
    except (FileNotFoundError, ValueError) as erreur:
        print(erreur, file=sys.stderr)
        return 2
    absentes = [nom for nom, m in releve["mesures"].items() if "absente" in m]
    print(
        f"Rapport d’étape de {releve['version']} (étape {releve['etape']}), relevé le {releve['releve_le']}{FINE}: "
        f"{len(releve['mesures'])} mesures dont {len(absentes)} absente{'s' if len(absentes) > 1 else ''}, "
        f"{len(releve['echantillons'])} échantillons"
    )
    for nom, raison in ((nom, releve["mesures"][nom]["absente"]) for nom in absentes):
        print(f"  {nom}{FINE}: absente, {raison}")
    if options.json:
        ecrire_json(Path(options.json), releve)
    return 0


def commande_longueurs(options: argparse.Namespace) -> int:
    try:
        releve = longueurs(Path(options.jeu))
    except (FileNotFoundError, ValueError) as erreur:
        print(erreur, file=sys.stderr)
        return 2
    print(
        f"Jeu {releve['jeu']}{FINE}: {nombre(releve['exemples'])} exemples dans {nombre(releve['rangees'])} rangées de "
        f"{nombre(releve['longueur_des_rangees'] + 1)} positions"
    )
    print(
        f"  longueur des exemples{FINE}: de {nombre(releve['min'])} à {nombre(releve['max'])} jetons, "
        f"médiane {nombre(releve['mediane'], 1)}, moyenne {nombre(releve['moyenne'], 1)}"
    )
    if options.json:
        ecrire_json(Path(options.json), releve)
    return 0


def main(argv: list[str] | None = None) -> int:
    # Avant argparse, qui écrit lui-même ses messages d'erreur.
    ecrire_en_utf8()
    lecteur = argparse.ArgumentParser(
        prog="python -m conversation_pas_a_pas",
        description="Montre une conversation en jetons, mesure la fuite sans masque, fait un petit affinage et résume les mesures du plan 7.",
    )
    commandes = lecteur.add_subparsers(dest="nom_commande", required=True, metavar="{montrer,fuite,essai,resumer,longueurs}")
    montre = commandes.add_parser("montrer", help="une conversation écrite jeton par jeton, avec son masque de perte")
    montre.add_argument("texte", metavar="TEXTE", help="ce que dit l'utilisateur")
    montre.add_argument("--reponse", default="Voilà.", help="la réponse de l'assistant (« Voilà. » par défaut)")
    montre.add_argument("--systeme", help="un message système, en premier tour")
    montre.set_defaults(fonction=commande_montrer)
    fuite = commandes.add_parser("fuite", help="l'écart des logits d'une conversation, dans une rangée, avec et sans masque par document")
    fuite.add_argument("--graine", type=int, default=0, help="la graine du modèle minuscule (0 par défaut)")
    fuite.add_argument("--enregistrer", metavar="FICHIER", help="écrit aussi la sortie dans FICHIER (UTF-8), précédée de la date du relevé")
    fuite.add_argument("--json", metavar="FICHIER", help="écrit aussi le résultat dans FICHIER (JSON)")
    fuite.set_defaults(fonction=commande_fuite)
    essai = commandes.add_parser("essai", help="un modèle minuscule, pré-entraîné puis affiné sur 24 conversations")
    essai.add_argument("--appareil", help="auto (par défaut, sauf si FORGE_APPAREIL est réglée), cpu ou cuda", default=None)
    essai.add_argument("--pas", type=int, default=80, help="le nombre de pas d'affinage (80 par défaut)")
    essai.add_argument("--enregistrer", metavar="FICHIER", help="écrit aussi la sortie dans FICHIER (UTF-8), précédée de la date du relevé")
    essai.add_argument("--json", metavar="FICHIER", help="écrit aussi le résultat dans FICHIER (JSON)")
    essai.set_defaults(fonction=commande_essai)
    resume = commandes.add_parser("resumer", help="le relevé du rapport d'étape de forge (evaluer-etape)")
    resume.add_argument("--rapport", required=True, metavar="RAPPORT", help="le rapport.json écrit par `python -m forge evaluer-etape`")
    resume.add_argument("--reference", action="store_true", help="résume la version de référence du rapport (ton-ia-1.5), pas la version évaluée")
    resume.add_argument("--json", metavar="FICHIER", help="écrit aussi le relevé dans FICHIER (JSON)")
    resume.set_defaults(fonction=commande_resumer)
    longueur = commandes.add_parser("longueurs", help="les longueurs des exemples d'un jeu d'affinage, lues dans train/documents.bin")
    longueur.add_argument("--jeu", required=True, metavar="DOSSIER", help="le dossier du jeu (affinage/sft-1.7), lu seulement")
    longueur.add_argument("--json", metavar="FICHIER", help="écrit aussi le relevé dans FICHIER (JSON)")
    longueur.set_defaults(fonction=commande_longueurs)
    options = lecteur.parse_args(argv)
    if MANQUE is not None:
        print(
            f"Un module manque ({MANQUE}). Lance le script avec la version de PyTorch de ton poste\u202f: "
            "`uv run --extra cpu python -m conversation_pas_a_pas …`, ou `--extra gpu` avec une carte NVIDIA.",
            file=sys.stderr,
        )
        return 2
    return options.fonction(options)


if __name__ == "__main__":
    sys.exit(main())
