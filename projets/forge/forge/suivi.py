"""Le suivi d'un entraînement : où il en est, lu dans son journal, sans PyTorch.

`python -m forge suivi --config configs/principal.toml` lit le journal de l'entraînement
(`<sortie>/journal.jsonl`, écrit par `forge entrainer`) et affiche :

- l'état : en cours, en pause, fini ou jamais lancé, d'après la dernière ligne du journal ; et
  « arrêté sans pause » quand le journal ne finit ni par une pause ni par la fin alors qu'aucun
  processus `forge entrainer` ne tourne pour cette configuration (un plantage, une coupure de
  courant…). On regarde les processus, pas la date du journal : sur un disque exFAT (le D: de
  ce PC), elle reste celle de l'ouverture du fichier tant que l'entraînement le garde ouvert ;
- le pas, les jetons vus, la dernière perte et la moyenne des `PERTES_RECENTES` derniers pas,
  la dernière perte de validation ;
- le débit récent et le temps restant estimé ;
- la dernière sauvegarde (fichier et pas).

Il ne fait que lire : on peut le lancer aussi souvent qu'on veut pendant l'entraînement. Il
n'importe pas PyTorch (près de 5 secondes de chargement) : la configuration est lue directement
dans le TOML, avec les mêmes règles que `forge.entrainement.lire_config` pour le dossier de
sortie et le nombre de pas (un test vérifie qu'ils trouvent la même chose).

Le débit est celui des `PAS_RECENTS` derniers pas, mesuré avec le champ `secondes` du journal :
le temps d'entraînement cumulé, qui ne compte pas les pauses, mais compte les validations et
les sauvegardes. Le temps restant est le nombre de pas restants à ce débit.
"""

import json
import os
import sys
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path

from forge.chemins import racine_donnees

# Le débit (et donc le temps restant) est mesuré sur les 100 derniers pas : environ 50 minutes
# pour l'entraînement principal, assez pour lisser une validation ou une sauvegarde.
PAS_RECENTS = 100

# La perte d'un pas varie d'un lot à l'autre : on montre aussi la moyenne des 20 derniers.
PERTES_RECENTES = 20

_FINE = "\u202f"  # espace fine insécable : milliers, avant « : ; ? ! % »

# Les états, et leur nom à l'écran.
JAMAIS_LANCE = "jamais lancé"
EN_COURS = "en cours"
ARRETE = "arrêté sans pause"
EN_PAUSE = "en pause"
FINI = "fini"
PERTE_INFINIE = "perte infinie"

# Les évènements qui terminent une session de l'entraînement.
_FINS_DE_SESSION = ("pause", "fin", "perte_non_finie")


# --- La configuration -----------------------------------------------------------------


@dataclass(frozen=True)
class Reglages:
    """Ce que le suivi lit dans la configuration de l'entraînement."""

    fichier: str  # le fichier TOML, tel qu'il a été donné (il sert aux commandes affichées)
    sortie: str  # la valeur de `sortie` dans le TOML
    dossier_sortie: Path
    pas_total: int
    taille_lot_jetons: int

    @property
    def journal(self) -> Path:
        return self.dossier_sortie / "journal.jsonl"

    @property
    def nom(self) -> str:
        """Le nom de l'entraînement : celui de son dossier de sortie (« ton-ia »)."""
        return Path(self.sortie).name or self.sortie


def lire_reglages(chemin: Path | str) -> Reglages:
    """Lit `sortie`, `jetons_total` et `taille_lot_jetons` dans le TOML de l'entraînement.

    Mêmes règles que `ConfigEntrainement` : un nom de sortie va sous
    `FORGE_DONNEES/entrainements/`, un chemin absolu est gardé tel quel ; le nombre de pas est
    `jetons_total ÷ taille_lot_jetons`, arrondi au-dessus.
    """
    fichier = Path(chemin)
    if not fichier.is_file():
        raise FileNotFoundError(
            f"Fichier de configuration introuvable{_FINE}: {chemin}. Donne le fichier TOML de "
            "l'entraînement, par exemple configs/principal.toml (depuis projets/forge)."
        )
    try:
        valeurs = tomllib.loads(fichier.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as erreur:
        raise ValueError(f"{chemin} n'est pas un fichier TOML valide{_FINE}: {erreur}.") from erreur
    manquants = [nom for nom in ("jetons_total", "taille_lot_jetons", "sortie") if nom not in valeurs]
    if manquants:
        raise ValueError(f"Réglage manquant dans {chemin}{_FINE}: {', '.join(manquants)}.")
    for nom in ("jetons_total", "taille_lot_jetons"):
        valeur = valeurs[nom]
        if not isinstance(valeur, int) or isinstance(valeur, bool) or valeur < 1:
            raise ValueError(f"{nom} vaut {valeur!r} dans {chemin}{_FINE}: il faut un nombre entier d'au moins 1.")
    sortie = valeurs["sortie"]
    if not isinstance(sortie, str) or not sortie:
        raise ValueError(f"sortie vaut {sortie!r} dans {chemin}{_FINE}: il faut un nom de dossier.")
    dossier = Path(sortie)
    if not dossier.is_absolute():
        dossier = racine_donnees() / "entrainements" / dossier
    return Reglages(
        fichier=str(chemin),
        sortie=sortie,
        dossier_sortie=dossier,
        pas_total=-(-valeurs["jetons_total"] // valeurs["taille_lot_jetons"]),
        taille_lot_jetons=valeurs["taille_lot_jetons"],
    )


# --- Le journal -----------------------------------------------------------------------

# Si l'entraînement remplace le journal à l'instant où on l'ouvre (il le recoupe en reprenant
# après un plantage), Windows refuse l'accès un court moment : on réessaie.
_ATTENTES_DE_LECTURE = (0.1, 0.3, 0.6)


def lire_journal(chemin: Path) -> list[dict]:
    """Les lignes du journal, dans l'ordre ; aucune s'il n'existe pas.

    Une ligne illisible est sautée : c'est en général la dernière, que l'entraînement est en
    train d'écrire (ou qu'une coupure de courant a tronquée).
    """
    for attente in (*_ATTENTES_DE_LECTURE, None):
        try:
            octets = chemin.read_bytes()
            break
        except FileNotFoundError:
            return []
        except PermissionError as erreur:
            if attente is None:
                raise PermissionError(
                    f"Le journal {chemin} ne se lit pas{_FINE}: un autre programme le bloque. "
                    "Relance cette commande dans quelques secondes."
                ) from erreur
            time.sleep(attente)
    lignes = []
    for texte in octets.decode("utf-8", errors="replace").splitlines():
        try:
            ligne = json.loads(texte)
        except ValueError:
            continue
        if isinstance(ligne, dict):
            lignes.append(ligne)
    return lignes


def _meme_fichier(a: Path, b: Path) -> bool:
    return os.path.normcase(str(a.resolve())) == os.path.normcase(str(b.resolve()))


def _config_de_la_commande(arguments: list[str]) -> str | None:
    """Le fichier de `… -m forge entrainer --config <fichier> …`, ou None si ce n'est pas un entraînement."""
    if "entrainer" not in arguments or "forge" not in arguments[: arguments.index("entrainer")]:
        return None
    for i, argument in enumerate(arguments):
        if argument == "--config" and i + 1 < len(arguments):
            return arguments[i + 1]
        if argument.startswith("--config="):
            return argument.removeprefix("--config=")
    return None


def entrainement_actif(reglages: Reglages) -> bool | None:
    """Un processus `python -m forge entrainer --config <ce fichier>` tourne-t-il sur ce PC ?

    Un chemin relatif dans sa ligne de commande se lit depuis son dossier de lancement. Renvoie
    None si on ne peut pas le savoir (psutil absent).
    """
    try:
        import psutil
    except ImportError:
        return None
    voulu = Path(reglages.fichier)
    for processus in psutil.process_iter(["name"]):
        try:
            if not (processus.info.get("name") or "").lower().startswith("python"):
                continue
            fichier = _config_de_la_commande(processus.cmdline())
            if fichier is None:
                continue
            chemin = Path(fichier)
            if not chemin.is_absolute():
                try:
                    chemin = Path(processus.cwd()) / chemin
                except (psutil.AccessDenied, OSError):
                    chemin = None  # son dossier est illisible : on compare au moins les noms
            if (chemin is None and Path(fichier).name == voulu.name) or (chemin and _meme_fichier(chemin, voulu)):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return False


def _est_un_nombre(valeur) -> bool:
    return isinstance(valeur, int | float) and not isinstance(valeur, bool)


def _est_un_pas(ligne: dict) -> bool:
    """Une ligne de pas : un numéro de pas et une perte, et pas d'évènement."""
    return "evenement" not in ligne and isinstance(ligne.get("pas"), int) and _est_un_nombre(ligne.get("perte"))


# --- L'état de l'entraînement ---------------------------------------------------------


@dataclass(frozen=True)
class Suivi:
    """Où en est un entraînement, d'après son journal."""

    etat: str  # une des constantes JAMAIS_LANCE, EN_COURS, ARRETE, EN_PAUSE, FINI, PERTE_INFINIE
    pas_de_l_etat: int | None  # le pas de la pause, de la fin ou de la perte infinie
    pas: int  # le dernier pas fini
    pas_total: int
    jetons_vus: int
    jetons_total: int
    perte: float | None
    perte_moyenne: float | None
    pertes_moyennees: int
    perte_val: float | None
    pas_val: int | None
    debit: float | None  # jetons par seconde
    pas_du_debit: int  # le nombre de pas sur lequel le débit est mesuré
    restant: float | None  # secondes ; None si inconnu ou fini
    sauvegarde: str | None
    pas_sauvegarde: int | None


def _debit(pas_faits: list[dict], taille_lot: int) -> tuple[float | None, int]:
    """Jetons par seconde sur les `PAS_RECENTS` derniers pas, et le nombre de pas mesurés.

    Les `secondes` du journal ne comptent pas les pauses : un débit mesuré à cheval sur une
    pause reste juste. Avec un seul pas, on prend son propre débit.
    """
    if not pas_faits:
        return None, 0
    dernier = pas_faits[-1]
    base = pas_faits[max(0, len(pas_faits) - 1 - PAS_RECENTS)]
    if base is not dernier and _est_un_nombre(base.get("secondes")) and _est_un_nombre(dernier.get("secondes")):
        duree = dernier["secondes"] - base["secondes"]
        nombre = dernier["pas"] - base["pas"]
        if duree > 0 and nombre > 0:
            return nombre * taille_lot / duree, nombre
    vitesse = dernier.get("jetons_par_seconde")
    if _est_un_nombre(vitesse) and vitesse > 0:
        return float(vitesse), 1
    return None, 0


def calculer_suivi(lignes: list[dict], pas_total: int, taille_lot: int, actif: bool | None = None) -> Suivi:
    """Résume le journal `lignes` ; `actif` : un processus d'entraînement tourne-t-il (None : inconnu) ?"""
    pas_faits = [ligne for ligne in lignes if _est_un_pas(ligne)]
    dernier = pas_faits[-1] if pas_faits else None
    pas = dernier["pas"] if dernier else 0

    evenement = lignes[-1].get("evenement") if lignes else None
    pas_de_l_etat = lignes[-1].get("pas") if lignes and isinstance(lignes[-1].get("pas"), int) else None
    if not lignes:
        etat = JAMAIS_LANCE
    elif evenement == "pause":
        etat = EN_PAUSE
    elif evenement == "fin":
        etat = FINI
    elif evenement == "perte_non_finie":
        etat = PERTE_INFINIE
    elif actif is False:
        etat = ARRETE
    else:
        etat = EN_COURS

    pertes = [ligne["perte"] for ligne in pas_faits[-PERTES_RECENTES:]]
    validations = [ligne for ligne in pas_faits if _est_un_nombre(ligne.get("perte_val"))]
    sauvegardes = [
        ligne for ligne in lignes if ligne.get("evenement") == "sauvegarde" and isinstance(ligne.get("fichier"), str)
    ]
    debit, pas_du_debit = _debit(pas_faits, taille_lot)
    restant = None
    if etat != FINI and debit:
        restant = max(0, pas_total - pas) * taille_lot / debit
    jetons_vus = dernier.get("jetons_vus") if dernier else 0
    if not isinstance(jetons_vus, int):
        jetons_vus = pas * taille_lot
    return Suivi(
        etat=etat,
        pas_de_l_etat=pas_de_l_etat,
        pas=pas,
        pas_total=pas_total,
        jetons_vus=jetons_vus,
        jetons_total=pas_total * taille_lot,
        perte=pertes[-1] if pertes else None,
        perte_moyenne=sum(pertes) / len(pertes) if pertes else None,
        pertes_moyennees=len(pertes),
        perte_val=validations[-1]["perte_val"] if validations else None,
        pas_val=validations[-1]["pas"] if validations else None,
        debit=debit,
        pas_du_debit=pas_du_debit,
        restant=restant,
        sauvegarde=sauvegardes[-1]["fichier"] if sauvegardes else None,
        pas_sauvegarde=sauvegardes[-1].get("pas") if sauvegardes else None,
    )


# --- L'affichage, en français ---------------------------------------------------------


def _entier(valeur: float) -> str:
    """12 345 : espace fine insécable entre les milliers."""
    return f"{round(valeur):,}".replace(",", _FINE)


def _decimal(valeur: float, decimales: int) -> str:
    return f"{valeur:,.{decimales}f}".replace(",", _FINE).replace(".", ",")


def _pourcent(pas: int, total: int) -> str:
    """La part faite, arrondie au dixième en dessous (99,9 % tant que ce n'est pas fini)."""
    dixiemes = pas * 1000 // total if total else 0
    texte = _decimal(dixiemes / 10, 1).removesuffix(",0")
    return f"{texte}{_FINE}%"


def _duree(secondes: float) -> str:
    """Une durée lisible : 2 j 3 h, 1 h 05 min, 4 min 10 s, 12 s."""
    secondes = max(0, round(secondes))
    jours, reste = divmod(secondes, 86400)
    heures, reste = divmod(reste, 3600)
    minutes, secondes = divmod(reste, 60)
    if jours:
        return f"{jours} j {heures} h"
    if heures:
        return f"{heures} h {minutes:02d} min"
    if minutes:
        return f"{minutes} min {secondes:02d} s"
    return f"{secondes} s"


def texte_du_suivi(suivi: Suivi, reglages: Reglages) -> str:
    """Le suivi, à afficher : une ligne d'état, puis une ligne par information."""
    lancer = f"python -m forge entrainer --config {reglages.fichier}"
    reprendre = f"{lancer} --reprendre"
    titre = f"Entraînement « {reglages.nom} »{_FINE}: "

    if suivi.etat == JAMAIS_LANCE:
        return "\n".join(
            [
                f"{titre}{JAMAIS_LANCE}",
                f"  Journal attendu{_FINE}: {reglages.journal} (absent ou vide)",
                f"  Pour le lancer{_FINE}: {lancer}",
            ]
        )

    if suivi.etat == EN_PAUSE:
        lignes = [f"{titre}{EN_PAUSE} au pas {_entier(suivi.pas_de_l_etat or suivi.pas)}"]
    elif suivi.etat == FINI:
        lignes = [f"{titre}{FINI} au pas {_entier(suivi.pas_de_l_etat or suivi.pas)}"]
    elif suivi.etat == PERTE_INFINIE:
        lignes = [
            f"{titre}arrêté, la perte est devenue infinie au pas {_entier(suivi.pas_de_l_etat or suivi.pas)}",
            f"  Reprends depuis la dernière sauvegarde avec un taux_max plus petit dans {reglages.fichier}"
            f"{_FINE}: {reprendre}",
        ]
    elif suivi.etat == ARRETE:
        lignes = [
            f"{titre}{ARRETE} au pas {_entier(suivi.pas)}",
            "  Le journal ne finit ni par une pause ni par la fin, et aucun processus « forge entrainer » "
            "ne tourne pour ce fichier{0}: l'entraînement a planté, ou le PC s'est éteint. Lis la fin de "
            "sa fenêtre ou de son journal, puis reprends depuis la dernière sauvegarde{0}: {1}".format(
                _FINE, reprendre
            ),
        ]
    else:
        lignes = [f"{titre}{EN_COURS}"]

    part = _pourcent(suivi.pas, suivi.pas_total)
    lignes.append(f"  Pas{_FINE}: {_entier(suivi.pas)} sur {_entier(suivi.pas_total)} ({part})")
    lignes.append(f"  Jetons vus{_FINE}: {_entier(suivi.jetons_vus)} sur {_entier(suivi.jetons_total)}")
    if suivi.perte is None:
        lignes.append(f"  Dernière perte{_FINE}: aucun pas fini pour l'instant")
    elif suivi.pertes_moyennees >= 2:
        lignes.append(
            f"  Dernière perte{_FINE}: {_decimal(suivi.perte, 3)} (moyenne des {suivi.pertes_moyennees} "
            f"derniers pas{_FINE}: {_decimal(suivi.perte_moyenne, 3)})"
        )
    else:
        lignes.append(f"  Dernière perte{_FINE}: {_decimal(suivi.perte, 3)}")
    if suivi.perte_val is None:
        lignes.append(f"  Dernière validation{_FINE}: aucune pour l'instant")
    else:
        lignes.append(f"  Dernière validation{_FINE}: {_decimal(suivi.perte_val, 3)} (pas {_entier(suivi.pas_val)})")
    if suivi.debit is not None:
        sur = (
            "sur le dernier pas"
            if suivi.pas_du_debit == 1
            else f"sur les {suivi.pas_du_debit} derniers pas, validations et sauvegardes comprises"
        )
        lignes.append(f"  Débit récent{_FINE}: {_entier(suivi.debit)} jetons/s ({sur})")
    if suivi.etat != FINI:
        if suivi.restant is None:
            lignes.append(f"  Temps restant estimé{_FINE}: inconnu (aucun pas fini pour l'instant)")
        else:
            lignes.append(
                f"  Temps restant estimé{_FINE}: {_duree(suivi.restant)} (au débit récent, pauses non comptées)"
            )
    if suivi.sauvegarde is None:
        lignes.append(f"  Dernière sauvegarde{_FINE}: aucune pour l'instant")
    else:
        pas_sauvegarde = f" (pas {_entier(suivi.pas_sauvegarde)})" if isinstance(suivi.pas_sauvegarde, int) else ""
        lignes.append(f"  Dernière sauvegarde{_FINE}: {suivi.sauvegarde}{pas_sauvegarde}")
    lignes.append(f"  Journal{_FINE}: {reglages.journal}")
    if suivi.etat == EN_PAUSE:
        lignes.append(f"  Pour reprendre{_FINE}: {reprendre}")
    return "\n".join(lignes)


def afficher(texte: str, flux=None) -> None:
    """Écrit `texte` sur `flux` (la sortie standard par défaut), même sans UTF-8.

    Sous Windows, une sortie redirigée sans `PYTHONUTF8=1` est en cp1252, qui n'a pas l'espace
    fine : elle devient alors une espace ordinaire (et tout autre signe absent, un « ? »).
    """
    flux = flux or sys.stdout
    encodage = getattr(flux, "encoding", None) or "utf-8"
    try:
        _FINE.encode(encodage)
    except UnicodeEncodeError:
        texte = texte.replace(_FINE, " ").encode(encodage, errors="replace").decode(encodage)
    print(texte, file=flux, flush=True)


def suivre(fichier_config: Path | str) -> str:
    """Lit la configuration et le journal, et renvoie le texte du suivi."""
    reglages = lire_reglages(fichier_config)
    lignes = lire_journal(reglages.journal)
    # Chercher le processus seulement quand le journal ne dit pas déjà que la session est finie.
    actif = None
    if lignes and lignes[-1].get("evenement") not in _FINS_DE_SESSION:
        actif = entrainement_actif(reglages)
    suivi = calculer_suivi(lignes, reglages.pas_total, reglages.taille_lot_jetons, actif)
    return texte_du_suivi(suivi, reglages)
