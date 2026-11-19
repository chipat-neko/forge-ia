"""`python -m alignement_pas_a_pas` : noter une réponse, calculer la perte DPO, voir ce qu'elle pousse, résumer.

    uv run --extra cpu python -m alignement_pas_a_pas noter "Paris est la capitale." --consigne minuscules --consigne mots_max:n=20
    uv run --extra cpu python -m alignement_pas_a_pas dpo --pc -12 --pr -20 --qc -14 --qr -18 --beta 0.1
    uv run --extra cpu python -m alignement_pas_a_pas pousser --pas 40
    uv run --extra cpu python -m alignement_pas_a_pas resumer --rapport <rapport.json> --json mesures/etape-ton-ia-1.8.json
    uv run --extra cpu python -m alignement_pas_a_pas paires --jeu <affinage/preferences-1.8> --json mesures/paires-exemples.json
    uv run --extra cpu python -m alignement_pas_a_pas balayage <essai> <essai> … --json mesures/balayage-1.8.json
    uv run --extra cpu python -m alignement_pas_a_pas courbes --journal <journal.jsonl> --json mesures/entrainement-dpo-1.8.json

`noter` donne la note d'une réponse critère par critère, avec la raison de chacun (les contrôles de forge, sans
juge). `dpo` refait à la main la perte DPO d'une paire et la compare à celle de forge. `pousser` fait quelques pas
de DPO sur une paire et un modèle minuscule, pour voir lequel monte, la choisie, ou lequel descend, la rejetée.
`resumer`, `paires`, `balayage` et `courbes` tirent des mesures du plan 7 les fichiers que le chapitre lit, sans
rien recalculer. Sans PyTorch, la commande le dit, sans trace Python, et rend le code 2.
"""

import argparse
import datetime
import json
import sys
from pathlib import Path

try:
    import torch

    # `forge.entrainement` d'abord : `forge.affinage.dpo` en premier fait un import circulaire dans forge.
    from forge.entrainement.boucle import ReglagesDPO  # isort: skip
    from forge.affinage.dpo import perte_dpo
    from forge.erreurs import DonneesManquantes
    from forge.preferences.invites import InvitePreference

    from alignement_pas_a_pas.courbes import courbes_dpo
    from alignement_pas_a_pas.noter import expliquer_note
    from alignement_pas_a_pas.perte_dpo import derivee_a_la_main, perte_dpo_a_la_main, sigmoide, terme_sft_a_la_main
    from alignement_pas_a_pas.poussee import TOKENIZER, lot_de_la_paire, modele_minuscule, paire_du_notebook, pousser
    from alignement_pas_a_pas.resumer import balayage, paires_exemples, resumer_etape
    from forge.tokenizer import TokenizerOctets
except ImportError as erreur:  # PyTorch (ou forge) manque : main() le dit, sans trace
    MANQUE: ImportError | None = erreur
else:
    MANQUE = None

FINE = "\u202f"  # l'espace fine insécable de la typographie française
PROJET = Path(__file__).resolve().parent.parent


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


def aujourd_hui() -> str:
    return datetime.date.today().isoformat()


def lire_une_consigne(texte: str) -> tuple[str, dict]:
    """« minuscules », « mots_max:n=20 » ou « fin_imposee:phrase=Merci. » : l'identifiant et ses réglages."""
    identifiant, _, reste = texte.partition(":")
    reglages: dict = {}
    if reste:
        cle, egal, valeur = reste.partition("=")
        if not egal:
            raise ValueError(f"La consigne « {texte} » doit s'écrire « identifiant » ou « identifiant:cle=valeur ».")
        reglages[cle] = int(valeur) if valeur.lstrip("-").isdigit() else valeur
    return identifiant, reglages


def commande_noter(options: argparse.Namespace) -> int:
    try:
        consignes = tuple(lire_une_consigne(c) for c in options.consigne)
        invite = InvitePreference("ligne-de-commande", (), consignes, options.attendu)
        explication = expliquer_note(options.texte, not options.coupee, invite)
    except ValueError as erreur:
        print(erreur, file=sys.stderr)
        return 2
    note = explication["note"]
    print(f"Note{FINE}: " + ", ".join(f"{nom} {valeur}" for nom, valeur in note.items()))
    for critere in explication["criteres"]:
        print(f"  {'oui' if critere['verdict'] else 'non'}  {critere['nom']:<10} {critere['valeur']}/{critere['maximum']}  {critere['raison']}")
    for consigne in explication["consignes"]:
        print(f"      {'respectée' if consigne['respectee'] else 'non respectée'}{FINE}: {consigne['consigne']}")
    return 0


def commande_dpo(options: argparse.Namespace) -> int:
    try:
        reglages = ReglagesDPO(beta=options.beta, poids_sft=options.poids_sft)
        a_la_main = perte_dpo_a_la_main(options.pc, options.pr, options.qc, options.qr, options.beta)
    except ValueError as erreur:
        print(erreur, file=sys.stderr)
        return 2
    gain_choisie, gain_rejetee = options.pc - options.qc, options.pr - options.qr
    z = options.beta * (gain_choisie - gain_rejetee)
    def tenseur(x: float) -> "torch.Tensor":
        return torch.tensor([x], dtype=torch.float64)

    de_forge, _ = perte_dpo(
        tenseur(options.pc), tenseur(options.pr), tenseur(options.qc), tenseur(options.qr), tenseur(options.jetons), tenseur(options.jetons), reglages
    )
    sft = terme_sft_a_la_main(options.pc, options.jetons)
    print(f"Gain de la choisie{FINE}: {nombre(gain_choisie, 3)}   gain de la rejetée{FINE}: {nombre(gain_rejetee, 3)}")
    print(f"z = β × (écart des gains){FINE}: {nombre(z, 4)}   σ(z){FINE}: {nombre(sigmoide(z), 4)}")
    print(f"Perte DPO à la main{FINE}: {nombre(a_la_main, 6)}   dérivée selon la choisie{FINE}: {nombre(derivee_a_la_main(options.beta, gain_choisie, gain_rejetee), 6)}")
    print(f"Terme SFT à la main{FINE}: {nombre(sft, 6)}   perte totale de forge (poids {nombre(options.poids_sft, 2)}){FINE}: {nombre(de_forge.item(), 6)}")
    egal = abs(a_la_main + options.poids_sft * sft - de_forge.item()) <= 1e-12
    print(f"À la main et dans forge, à 10⁻¹² près{FINE}: {'oui' if egal else 'non'}")
    return 0 if egal else 1


def commande_pousser(options: argparse.Namespace) -> int:
    paire, reelle = paire_du_notebook(Path(options.paires) if options.paires else PROJET / "mesures" / "paires-exemples.json")
    lot = lot_de_la_paire(TokenizerOctets.charger(TOKENIZER), paire)
    modele = modele_minuscule(max(128, lot.ids.shape[1] + 1), options.graine)
    releves = pousser(modele, lot, ReglagesDPO(beta=options.beta, poids_sft=options.poids_sft), options.pas, options.taux)
    print("Une paire " + ("réelle de ton IA" if reelle else "fabriquée") + f", {options.pas} pas de DPO sur un modèle minuscule (β {nombre(options.beta, 2)}, poids SFT {nombre(options.poids_sft, 2)}).")
    print(f"{'pas':>4}  {'choisie':>9}  {'rejetée':>9}  {'marge':>8}  perte")
    for r in (releves[0], *releves[1:-1:max(1, options.pas // 4)], releves[-1]):
        print(f"{r['pas']:>4}  {nombre(r['logps_choisie'], 3):>9}  {nombre(r['logps_rejetee'], 3):>9}  {nombre(r['marge'], 3):>8}  {nombre(r['perte'], 3)}")
    debut, fin = releves[0], releves[-1]
    print(f"Par jeton, la choisie passe de {nombre(debut['logps_choisie'], 3)} à {nombre(fin['logps_choisie'], 3)} et la rejetée de {nombre(debut['logps_rejetee'], 3)} à {nombre(fin['logps_rejetee'], 3)}.")
    if options.json:
        ecrire_json(Path(options.json), {"releve_le": aujourd_hui(), "reelle": reelle, "releves": releves})
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


def commande_paires(options: argparse.Namespace) -> int:
    try:
        paires = paires_exemples(Path(options.jeu), options.n)
    except (DonneesManquantes, FileNotFoundError, ValueError) as erreur:
        print(erreur, file=sys.stderr)
        return 2
    print(f"{len(paires)} paires du jeu {Path(options.jeu).name}{FINE}:")
    for p in paires:
        print(f"  {p['id']}{FINE}: départagées par « {p['raison']} », source {p['source']['nom']} ({p['source']['licence']})")
    if options.json:
        ecrire_json(Path(options.json), paires)
    return 0


def commande_balayage(options: argparse.Namespace) -> int:
    try:
        essais = balayage([Path(d) for d in options.dossiers])
    except (FileNotFoundError, ValueError) as erreur:
        print(erreur, file=sys.stderr)
        return 2
    for e in essais:
        r = e["reglages"]
        victoire = e["victoire"]
        taux = "absente" if "absente" in victoire else f"{nombre(100 * victoire['taux'], 1)}{FINE}%"
        print(
            f"  {e['essai']}{FINE}: taux {r['taux_max']}, β {nombre(r['beta'], 2)}, victoire {taux}, "
            f"choisie {nombre(e['logps_choisie']['debut'], 3)} → {nombre(e['logps_choisie']['fin'], 3)}"
        )
    if options.json:
        ecrire_json(Path(options.json), essais)
    return 0


def commande_courbes(options: argparse.Namespace) -> int:
    try:
        courbes = courbes_dpo(Path(options.journal), pas_total=options.pas_total)
    except (FileNotFoundError, ValueError) as erreur:
        print(erreur, file=sys.stderr)
        return 2
    print(f"Courbes de {options.journal}{FINE}: " + ", ".join(f"{nom} ({len(points)} points)" for nom, points in courbes.items()))
    if options.json:
        ecrire_json(Path(options.json), courbes)
    return 0


def main(argv: list[str] | None = None) -> int:
    # Avant argparse, qui écrit lui-même ses messages d'erreur.
    ecrire_en_utf8()
    lecteur = argparse.ArgumentParser(
        prog="python -m alignement_pas_a_pas",
        description="Note une réponse, refait la perte DPO à la main, montre ce qu'elle pousse, et résume les mesures du plan 7.",
    )
    commandes = lecteur.add_subparsers(
        dest="nom_commande", required=True, metavar="{noter,dpo,pousser,resumer,paires,balayage,courbes}"
    )
    noter = commandes.add_parser("noter", help="la note d'une réponse, critère par critère, avec la raison de chacun")
    noter.add_argument("texte", metavar="TEXTE", help="la réponse à noter")
    noter.add_argument("--coupee", action="store_true", help="la réponse a été coupée par la limite de jetons (pas de <|fin_tour|>)")
    noter.add_argument("--attendu", type=int, help="pour un problème, la réponse attendue")
    noter.add_argument("--consigne", action="append", default=[], metavar="ID[:CLE=VALEUR]", help="une consigne de l'invite (répétable) : minuscules, mots_max:n=20…")
    noter.set_defaults(fonction=commande_noter)
    dpo = commandes.add_parser("dpo", help="la perte DPO d'une paire, à la main et dans forge")
    dpo.add_argument("--pc", type=float, required=True, help="log-probabilité de la choisie selon la politique")
    dpo.add_argument("--pr", type=float, required=True, help="log-probabilité de la rejetée selon la politique")
    dpo.add_argument("--qc", type=float, required=True, help="log-probabilité de la choisie selon la référence")
    dpo.add_argument("--qr", type=float, required=True, help="log-probabilité de la rejetée selon la référence")
    dpo.add_argument("--beta", type=float, default=0.1, help="β, la force de la préférence (0,1 par défaut)")
    dpo.add_argument("--poids-sft", type=float, default=1.0, help="le poids du terme SFT (1 par défaut)")
    dpo.add_argument("--jetons", type=int, default=10, help="les jetons appris de chaque réponse (10 par défaut)")
    dpo.set_defaults(fonction=commande_dpo)
    pousse = commandes.add_parser("pousser", help="quelques pas de DPO sur une paire et un modèle minuscule")
    pousse.add_argument("--paires", metavar="FICHIER", help="paires-exemples.json (par défaut, celui du projet s'il existe, sinon une paire fabriquée)")
    pousse.add_argument("--pas", type=int, default=40, help="le nombre de pas (40 par défaut)")
    pousse.add_argument("--taux", type=float, default=1e-3, help="le taux d'apprentissage (0,001 par défaut)")
    pousse.add_argument("--beta", type=float, default=0.1)
    pousse.add_argument("--poids-sft", type=float, default=0.0, help="le poids du terme SFT (0 par défaut : la DPO seule)")
    pousse.add_argument("--graine", type=int, default=0, help="la graine du modèle minuscule")
    pousse.add_argument("--json", metavar="FICHIER", help="écrit aussi les relevés dans FICHIER (JSON)")
    pousse.set_defaults(fonction=commande_pousser)
    resume = commandes.add_parser("resumer", help="le relevé du rapport d'étape de forge (evaluer-etape)")
    resume.add_argument("--rapport", required=True, metavar="RAPPORT", help="le rapport.json écrit par `python -m forge evaluer-etape`")
    resume.add_argument("--reference", action="store_true", help="résume la version de référence du rapport, pas la version évaluée")
    resume.add_argument("--json", metavar="FICHIER", help="écrit aussi le relevé dans FICHIER (JSON)")
    resume.set_defaults(fonction=commande_resumer)
    paires = commandes.add_parser("paires", help="les premières paires d'un jeu de préférences, avec leurs notes et leur référence")
    paires.add_argument("--jeu", required=True, metavar="DOSSIER", help="le dossier du jeu (affinage/preferences-1.8), lu seulement")
    paires.add_argument("--n", type=int, default=6, help="combien de paires garder (6 par défaut)")
    paires.add_argument("--json", metavar="FICHIER", help="écrit aussi les paires dans FICHIER (JSON)")
    paires.set_defaults(fonction=commande_paires)
    balaye = commandes.add_parser("balayage", help="les essais du balayage de la DPO : réglages, victoire, longueur, logps_choisie")
    balaye.add_argument("dossiers", nargs="+", metavar="ESSAI", help="un dossier d'essai (config.toml, journal.jsonl, rapport.json)")
    balaye.add_argument("--json", metavar="FICHIER", help="écrit aussi le relevé dans FICHIER (JSON)")
    balaye.set_defaults(fonction=commande_balayage)
    courbe = commandes.add_parser("courbes", help="les courbes d'une DPO, lues dans son journal")
    courbe.add_argument("--journal", required=True, metavar="JOURNAL", help="le journal.jsonl d'un entraînement dpo, lu seulement")
    courbe.add_argument("--pas-total", type=int, help="le nombre de pas de la configuration")
    courbe.add_argument("--json", metavar="FICHIER", help="écrit aussi les courbes dans FICHIER (JSON)")
    courbe.set_defaults(fonction=commande_courbes)
    options = lecteur.parse_args(argv)
    if MANQUE is not None:
        print(
            f"Un module manque ({MANQUE}). Lance le script avec la version de PyTorch de ton poste\u202f: "
            "`uv run --extra cpu python -m alignement_pas_a_pas …`, ou `--extra gpu` avec une carte NVIDIA.",
            file=sys.stderr,
        )
        return 2
    return options.fonction(options)


if __name__ == "__main__":
    sys.exit(main())
