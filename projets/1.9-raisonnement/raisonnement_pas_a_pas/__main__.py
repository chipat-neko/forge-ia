"""`python -m raisonnement_pas_a_pas` : un problème et sa trace, vérifier une réponse, les avantages d'un groupe, un petit GRPO, résumer.

    uv run --extra cpu python -m raisonnement_pas_a_pas probleme achats 2 7
    uv run --extra cpu python -m raisonnement_pas_a_pas verifier "12 fois 7 font 84." --attendu 84
    uv run --extra cpu python -m raisonnement_pas_a_pas avantages 1,0,0,1 0,0,0,0
    uv run --extra cpu python -m raisonnement_pas_a_pas signal --p 0.2 --n 8
    uv run --extra cpu python -m raisonnement_pas_a_pas essai --pas 20 --json sorties/essai-grpo.json
    uv run --extra cpu python -m raisonnement_pas_a_pas resumer --rapport <rapport.json> --json mesures/etape-ton-ia-1.9.json
    uv run --extra cpu python -m raisonnement_pas_a_pas controle --sortie <sortie du grpo> --json mesures/controle-1.9.json
    uv run --extra cpu python -m raisonnement_pas_a_pas courbes --journal <journal.jsonl> --json mesures/entrainement-grpo-1.9.json

`probleme` montre un problème généré, sa trace et sa conversation en jetons. `verifier` dit si une réponse est juste,
avec la règle de forge. `avantages` refait à la main l'avantage de chaque réponse de chaque groupe, et le compare à
forge. `signal` donne la chance qu'un groupe n'apprenne rien. `essai` fait un petit GRPO sur un modèle minuscule.
`resumer`, `controle` et `courbes` tirent des mesures du plan 7 les fichiers que le chapitre lit, sans rien recalculer.
Sans PyTorch, la commande le dit, sans trace Python, et rend le code 2.
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import torch
    from forge.raisonnement import grpo

    from raisonnement_pas_a_pas.avantages import avantages_a_la_main, sans_signal
    from raisonnement_pas_a_pas.petit_grpo import essai_grpo
    from raisonnement_pas_a_pas.problemes import montrer_probleme, verifier_reponse
    from raisonnement_pas_a_pas.resumer import controle, courbes_grpo, resumer_etape
except ImportError as erreur:  # PyTorch (ou forge) manque : main() le dit, sans trace
    MANQUE: ImportError | None = erreur
else:
    MANQUE = None

FINE = "\u202f"  # l'espace fine insécable de la typographie française


def nombre(n: float, decimales: int = 0) -> str:
    """Un nombre à la française : les milliers séparés par une espace fine, la virgule décimale."""
    return f"{n:,.{decimales}f}".replace(",", FINE).replace(".", ",")


def ecrire_en_utf8() -> None:
    """Une console Windows redirigée vers un fichier écrit en cp1252, qui ne connaît pas l'espace fine (U+202F) :
    on passe alors la sortie en UTF-8, plutôt que de planter."""
    for flux in (sys.stdout, sys.stderr):
        try:
            "\u202f’␊".encode(flux.encoding or "ascii")
        except (UnicodeEncodeError, LookupError):
            if hasattr(flux, "reconfigure"):
                flux.reconfigure(encoding="utf-8")


def ecrire_json(chemin: Path, donnees) -> None:
    """Un fichier de mesures : UTF-8, fins de ligne LF, comme les autres mesures du dépôt."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with open(chemin, "w", encoding="utf-8", newline="\n") as fichier:
        fichier.write(json.dumps(donnees, ensure_ascii=False, allow_nan=False, indent=1) + "\n")


def lire_un_groupe(texte: str) -> list[float]:
    """« 1,0,0,1 » : les récompenses d'un groupe, séparées par des virgules."""
    try:
        groupe = [float(morceau) for morceau in texte.split(",")]
    except ValueError:
        raise ValueError(f"Le groupe « {texte} » doit être des nombres séparés par des virgules, comme 1,0,0,1.") from None
    return groupe


def commande_probleme(options: argparse.Namespace) -> int:
    try:
        p = montrer_probleme(options.famille, options.difficulte, options.graine)
    except ValueError as erreur:
        print(erreur, file=sys.stderr)
        return 2
    print(f"Problème {p['id']}{FINE}:")
    print(f"  {p['enonce']}")
    print("Trace, une étape de calcul par ligne" + FINE + ":")
    for etape in p["etapes"]:
        print(f"  {etape}")
    conversation = p["conversation"]
    appris = sum(conversation["appris"])
    print(f"Réponse{FINE}: {p['reponse']}. La conversation de ton IA fait {len(conversation['ids'])} jetons, dont {appris} appris (la pensée et la réponse).")
    if options.json:
        ecrire_json(Path(options.json), p)
    return 0


def commande_verifier(options: argparse.Namespace) -> int:
    verdict = verifier_reponse(options.texte, not options.coupee, options.attendu)
    lu = "aucun nombre" if verdict["lu"] is None else verdict["lu"]
    print(f"Nombre lu (le dernier du texte){FINE}: {lu}. Réponse {'terminée' if verdict['terminee'] else 'coupée'}. Juste{FINE}: {'oui' if verdict['juste'] else 'non'}.")
    return 0 if verdict["juste"] else 1


def commande_avantages(options: argparse.Namespace) -> int:
    try:
        groupes = [lire_un_groupe(texte) for texte in options.groupes]
        a_la_main = avantages_a_la_main(groupes)
    except ValueError as erreur:
        print(erreur, file=sys.stderr)
        return 2
    for groupe, avantages in zip(groupes, a_la_main, strict=True):
        sans = all(a == 0 for a in avantages)
        print(f"  récompenses {groupe} → avantages {[round(a, 4) for a in avantages]}{' (sans signal)' if sans else ''}")
    if len({len(g) for g in groupes}) > 1:
        print("Groupes de tailles différentes : la comparaison à forge, qui prend un tableau, est sautée.")
        return 0
    de_forge = grpo.avantages(torch.tensor(groupes, dtype=torch.float64)).tolist()
    egal = all(abs(a - b) <= 1e-12 for groupe, ligne in zip(a_la_main, de_forge, strict=True) for a, b in zip(groupe, ligne, strict=True))
    print(f"À la main et dans forge, à 10⁻¹² près{FINE}: {'oui' if egal else 'non'}")
    return 0 if egal else 1


def commande_signal(options: argparse.Namespace) -> int:
    try:
        chance = sans_signal(options.p, options.n)
    except ValueError as erreur:
        print(erreur, file=sys.stderr)
        return 2
    print(
        f"Avec une chance {nombre(options.p, 3)} d'être juste, un groupe de {options.n} réponses est sans signal avec la chance "
        f"{nombre(chance, 6)} ({nombre(100 * chance, 2)}{FINE}%)."
    )
    return 0


def commande_essai(options: argparse.Namespace) -> int:
    try:
        resultat = essai_grpo(options.appareil, options.pas)
    except (RuntimeError, ValueError) as erreur:
        print(erreur, file=sys.stderr)
        return 2
    print(f"Petit GRPO sur {resultat['appareil']}, {resultat['pas']} pas, en {nombre(resultat['secondes'], 1)}{FINE}s.")
    print(f"Réussite en glouton sur les dix chiffres{FINE}: {nombre(100 * resultat['reussite_avant'], 0)}{FINE}% avant, {nombre(100 * resultat['reussite_apres'], 0)}{FINE}% après.")
    print(f"{'pas':>4}  {'récompense':>10}  {'sans signal':>11}")
    for numero, (r, s) in enumerate(zip(resultat["recompense_moyenne"], resultat["groupes_sans_signal"], strict=True), start=1):
        print(f"{numero:>4}  {nombre(r, 3):>10}  {nombre(s, 3):>11}")
    if options.json:
        ecrire_json(Path(options.json), resultat)
    return 0


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
    for nom in absentes:
        print(f"  {nom}{FINE}: absente, {releve['mesures'][nom]['absente']}")
    if options.json:
        ecrire_json(Path(options.json), releve)
    return 0


def commande_controle(options: argparse.Namespace) -> int:
    try:
        releve = controle(Path(options.sortie))
    except (FileNotFoundError, ValueError) as erreur:
        print(erreur, file=sys.stderr)
        return 2
    print(
        f"Contrôle de départ{FINE}: {nombre(releve['justes'])} réponses justes sur {nombre(releve['reponses'])} "
        f"({nombre(100 * releve['taux'], 1)}{FINE}%), {nombre(releve['invites'])} problèmes."
    )
    print("Le RL a un signal : il peut se lancer." if releve["lance"] else "Aucune réponse juste : le RL n'aurait aucun signal, forge ne le lance pas (code de sortie 6).")
    if options.json:
        ecrire_json(Path(options.json), releve)
    return 0


def commande_courbes(options: argparse.Namespace) -> int:
    try:
        courbes = courbes_grpo(Path(options.journal), pas_total=options.pas_total)
    except FileNotFoundError as erreur:
        print(erreur, file=sys.stderr)
        return 2
    if courbes == {"lance": False}:
        print(f"Aucun pas de GRPO dans {options.journal}{FINE}: le RL n'a pas été lancé.")
    else:
        print(f"Courbes de {options.journal}{FINE}: " + ", ".join(f"{nom} ({len(points)} points)" for nom, points in courbes.items()))
    if options.json:
        ecrire_json(Path(options.json), courbes)
    return 0


def main(argv: list[str] | None = None) -> int:
    # Avant argparse, qui écrit lui-même ses messages d'erreur.
    ecrire_en_utf8()
    lecteur = argparse.ArgumentParser(
        prog="python -m raisonnement_pas_a_pas",
        description="Montre un problème et sa trace, vérifie une réponse, refait les avantages du GRPO, fait un petit GRPO et résume les mesures du plan 7.",
    )
    commandes = lecteur.add_subparsers(
        dest="nom_commande", required=True, metavar="{probleme,verifier,avantages,signal,essai,resumer,controle,courbes}"
    )
    probleme = commandes.add_parser("probleme", help="un problème généré, sa trace et sa conversation en jetons")
    probleme.add_argument("famille", help="addition, soustraction, multiplication, partage, achats ou ages")
    probleme.add_argument("difficulte", type=int, help="le nombre d'étapes de calcul (chaque famille a les siennes)")
    probleme.add_argument("graine", type=int, help="la graine : la même graine, le même problème")
    probleme.add_argument("--json", metavar="FICHIER", help="écrit aussi le problème dans FICHIER (JSON)")
    probleme.set_defaults(fonction=commande_probleme)
    verifie = commandes.add_parser("verifier", help="une réponse est-elle juste ? (le dernier nombre du texte)")
    verifie.add_argument("texte", metavar="TEXTE", help="la réponse écrite")
    verifie.add_argument("--attendu", type=int, required=True, help="la bonne réponse")
    verifie.add_argument("--coupee", action="store_true", help="la réponse a été coupée par la limite de jetons (jamais juste)")
    verifie.set_defaults(fonction=commande_verifier)
    avantage = commandes.add_parser("avantages", help="l'avantage de chaque réponse de chaque groupe, à la main et dans forge")
    avantage.add_argument("groupes", nargs="+", metavar="GROUPE", help="les récompenses d'un groupe, séparées par des virgules : 1,0,0,1")
    avantage.set_defaults(fonction=commande_avantages)
    signal = commandes.add_parser("signal", help="la chance qu'un groupe de réponses n'apprenne rien")
    signal.add_argument("--p", type=float, required=True, help="la chance qu'une réponse soit juste, de 0 à 1")
    signal.add_argument("--n", type=int, required=True, help="les réponses du groupe")
    signal.set_defaults(fonction=commande_signal)
    essai = commandes.add_parser("essai", help="un petit GRPO sur un modèle minuscule qui répète un chiffre")
    essai.add_argument("--appareil", default="cpu", help="cpu (par défaut) ou cuda")
    essai.add_argument("--pas", type=int, default=20, help="le nombre de pas de GRPO (20 par défaut)")
    essai.add_argument("--json", metavar="FICHIER", help="écrit aussi les mesures dans FICHIER (JSON)")
    essai.set_defaults(fonction=commande_essai)
    resume = commandes.add_parser("resumer", help="le relevé du rapport d'étape de forge (evaluer-etape)")
    resume.add_argument("--rapport", required=True, metavar="RAPPORT", help="le rapport.json écrit par `python -m forge evaluer-etape`")
    resume.add_argument("--reference", action="store_true", help="résume la version de référence du rapport, pas la version évaluée")
    resume.add_argument("--json", metavar="FICHIER", help="écrit aussi le relevé dans FICHIER (JSON)")
    resume.set_defaults(fonction=commande_resumer)
    controle_ = commandes.add_parser("controle", help="le contrôle de départ d'un GRPO (controle.json de sa sortie)")
    controle_.add_argument("--sortie", required=True, metavar="DOSSIER", help="le dossier de sortie de `forge entrainer` (méthode grpo), lu seulement")
    controle_.add_argument("--json", metavar="FICHIER", help="écrit aussi le contrôle dans FICHIER (JSON)")
    controle_.set_defaults(fonction=commande_controle)
    courbe = commandes.add_parser("courbes", help="les courbes d'un GRPO, lues dans son journal")
    courbe.add_argument("--journal", required=True, metavar="JOURNAL", help="le journal.jsonl d'un entraînement grpo, lu seulement")
    courbe.add_argument("--pas-total", type=int, help="le nombre de pas de la configuration")
    courbe.add_argument("--json", metavar="FICHIER", help="écrit aussi les courbes dans FICHIER (JSON)")
    courbe.set_defaults(fonction=commande_courbes)
    options = lecteur.parse_args(argv)
    if MANQUE is not None:
        print(
            f"Un module manque ({MANQUE}). Lance le script avec la version de PyTorch de ton poste\u202f: "
            "`uv run --extra cpu python -m raisonnement_pas_a_pas …`, ou `--extra gpu` avec une carte NVIDIA.",
            file=sys.stderr,
        )
        return 2
    return options.fonction(options)


if __name__ == "__main__":
    sys.exit(main())
