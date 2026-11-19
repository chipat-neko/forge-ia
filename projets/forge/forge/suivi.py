"""Le suivi d'un entraînement : où il en est, lu dans son journal, sans PyTorch.

`python -m forge suivi --config configs/principal.toml` lit le journal de l'entraînement
(`<sortie>/journal.jsonl`, écrit par `forge entrainer`) et affiche :

- l'état : en cours, en pause, fini ou jamais lancé, d'après la dernière ligne du journal (ou, pour
  le GRPO, arrêté sans rien lancer : aucune récompense au contrôle de départ) ; et
  « arrêté sans pause » quand le journal ne finit ni par une pause ni par la fin alors qu'aucun
  processus `forge entrainer` ne tourne pour cette configuration (un plantage, une coupure de
  courant…). On regarde les processus, pas la date du journal : sur un disque exFAT (le D: de
  ce PC), elle reste celle de l'ouverture du fichier tant que l'entraînement le garde ouvert ;
- le pas, les jetons vus, la dernière perte et la moyenne des `PERTES_RECENTES` derniers pas,
  la dernière perte de validation ;
- pour la DPO, quand le journal les a : la log-probabilité par jeton de la réponse choisie
  (`logps_choisie`) et l'exactitude (la part des paires classées dans le bon ordre), avec leur
  moyenne sur les mêmes derniers pas ;
- pour le GRPO : la récompense moyenne (la part des réponses justes), avec sa moyenne sur les mêmes
  derniers pas, et la dernière réussite de validation (`reussite_val`) au lieu de la perte de
  validation. Ses pas n'ont pas tous les mêmes jetons : ni jetons vus, ni débit en jetons, mais des
  secondes par pas ;
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

from forge.chemins import sous_forge_donnees
from forge.fichiers import ESPACE_FINE, duree, entier, nombre

# Le débit (et donc le temps restant) est mesuré sur les 100 derniers pas : environ 50 minutes
# pour l'entraînement principal, assez pour lisser une validation ou une sauvegarde.
PAS_RECENTS = 100

# La perte d'un pas varie d'un lot à l'autre : on montre aussi la moyenne des 20 derniers.
PERTES_RECENTES = 20

_FINE = ESPACE_FINE  # espace fine insécable : milliers, avant « : ; ? ! % »

# Les états, et leur nom à l'écran.
JAMAIS_LANCE = "jamais lancé"
EN_COURS = "en cours"
ARRETE = "arrêté sans pause"
EN_PAUSE = "en pause"
FINI = "fini"
PERTE_INFINIE = "perte infinie"
RECOMPENSE_NULLE = "aucune récompense au contrôle de départ"

# Les évènements qui terminent une session de l'entraînement. `recompense_nulle` : le contrôle de départ du GRPO
# n'a trouvé aucune réponse juste, rien n'a été lancé (code 6).
_FINS_DE_SESSION = ("pause", "fin", "perte_non_finie", "recompense_nulle")

# Le fichier du contrôle de départ du GRPO, dans la sortie : le nom de `forge.raisonnement.grpo.NOM_DU_CONTROLE`,
# recopié pour ne pas importer PyTorch (un test vérifie que c'est le même).
NOM_DU_CONTROLE = "controle.json"


# --- La configuration -----------------------------------------------------------------


@dataclass(frozen=True)
class Reglages:
    """Ce que le suivi lit dans la configuration de l'entraînement."""

    fichier: str  # le fichier TOML, tel qu'il a été donné (il sert aux commandes affichées)
    sortie: str  # la valeur de `sortie` dans le TOML
    dossier_sortie: Path
    pas_total: int
    taille_lot_jetons: int | None  # None pour le GRPO, qui compte en pas

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
    `jetons_total ÷ taille_lot_jetons`, arrondi au-dessus, et pour le GRPO (`methode = "grpo"`),
    le `pas` de sa table `[grpo]`.
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
    if valeurs.get("methode") == "grpo":
        return _reglages_du_grpo(chemin, valeurs)
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
    dossier = sous_forge_donnees(sortie, "entrainements")
    return Reglages(
        fichier=str(chemin),
        sortie=sortie,
        dossier_sortie=dossier,
        pas_total=-(-valeurs["jetons_total"] // valeurs["taille_lot_jetons"]),
        taille_lot_jetons=valeurs["taille_lot_jetons"],
    )


def _reglages_du_grpo(chemin: Path | str, valeurs: dict) -> Reglages:
    """`sortie` et le `pas` de la table `[grpo]` : le GRPO n'a ni `jetons_total` ni `taille_lot_jetons`."""
    table = valeurs.get("grpo")
    pas = table.get("pas") if isinstance(table, dict) else None
    manquants = [nom for nom, present in (("[grpo] pas", pas is not None), ("sortie", "sortie" in valeurs)) if not present]
    if manquants:
        raise ValueError(f"Réglage manquant dans {chemin}{_FINE}: {', '.join(manquants)}.")
    if not isinstance(pas, int) or isinstance(pas, bool) or pas < 1:
        raise ValueError(f"pas vaut {pas!r} dans la table [grpo] de {chemin}{_FINE}: il faut un nombre entier d'au moins 1.")
    sortie = valeurs["sortie"]
    if not isinstance(sortie, str) or not sortie:
        raise ValueError(f"sortie vaut {sortie!r} dans {chemin}{_FINE}: il faut un nom de dossier.")
    return Reglages(
        fichier=str(chemin),
        sortie=sortie,
        dossier_sortie=sous_forge_donnees(sortie, "entrainements"),
        pas_total=pas,
        taille_lot_jetons=None,
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

    etat: str  # une des constantes JAMAIS_LANCE, EN_COURS, ARRETE, EN_PAUSE, FINI, PERTE_INFINIE, RECOMPENSE_NULLE
    pas_de_l_etat: int | None  # le pas de la pause, de la fin ou de la perte infinie
    pas: int  # le dernier pas fini
    pas_total: int
    jetons_vus: int | None  # None (et jetons_total aussi) pour le GRPO, qui compte en pas
    jetons_total: int | None
    perte: float | None
    perte_moyenne: float | None
    pertes_moyennees: int
    perte_val: float | None
    pas_val: int | None
    debit: float | None  # jetons par seconde (pas par seconde pour le GRPO)
    pas_du_debit: int  # le nombre de pas sur lequel le débit est mesuré
    restant: float | None  # secondes ; None si inconnu ou fini
    sauvegarde: str | None
    pas_sauvegarde: int | None
    # La DPO : les valeurs des `PERTES_RECENTES` derniers pas qui en ont (aucune hors DPO).
    logps_choisie_recentes: tuple[float, ...] = ()
    exactitude_recentes: tuple[float, ...] = ()
    # Le GRPO : la récompense moyenne des derniers pas, et la dernière réussite de validation.
    recompense_recentes: tuple[float, ...] = ()
    reussite_val: float | None = None
    pas_reussite_val: int | None = None
    controle: dict | None = None  # le contrôle de départ d'un GRPO arrêté sans récompense (sa ligne du journal)


def _debit(pas_faits: list[dict], taille_lot: int | None) -> tuple[float | None, int]:
    """Jetons par seconde sur les `PAS_RECENTS` derniers pas, et le nombre de pas mesurés.

    Les `secondes` du journal ne comptent pas les pauses : un débit mesuré à cheval sur une
    pause reste juste. Avec un seul pas, on prend son propre débit. Sans `taille_lot` (le GRPO),
    des pas par seconde.
    """
    if not pas_faits:
        return None, 0
    dernier = pas_faits[-1]
    base = pas_faits[max(0, len(pas_faits) - 1 - PAS_RECENTS)]
    if base is not dernier and _est_un_nombre(base.get("secondes")) and _est_un_nombre(dernier.get("secondes")):
        duree = dernier["secondes"] - base["secondes"]
        nombre = dernier["pas"] - base["pas"]
        if duree > 0 and nombre > 0:
            return nombre * (taille_lot or 1) / duree, nombre
    if taille_lot is None:  # le GRPO n'écrit pas de débit en jetons : celui de tout ce qui précède
        secondes = dernier.get("secondes")
        if _est_un_nombre(secondes) and secondes > 0:
            return dernier["pas"] / secondes, 1
        return None, 0
    vitesse = dernier.get("jetons_par_seconde")
    if _est_un_nombre(vitesse) and vitesse > 0:
        return float(vitesse), 1
    return None, 0


def _recentes(pas_faits: list[dict], cle: str) -> tuple[float, ...]:
    """Les valeurs de `cle` des `PERTES_RECENTES` derniers pas qui l'ont, dans l'ordre."""
    valeurs = [ligne[cle] for ligne in pas_faits if _est_un_nombre(ligne.get(cle))]
    return tuple(valeurs[-PERTES_RECENTES:])


def calculer_suivi(lignes: list[dict], pas_total: int, taille_lot: int | None, actif: bool | None = None) -> Suivi:
    """Résume le journal `lignes` ; `actif` : un processus d'entraînement tourne-t-il (None : inconnu) ?

    `taille_lot` : les jetons d'un pas, ou None pour le GRPO (ni jetons vus, débit en pas par seconde).
    """
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
    elif evenement == "recompense_nulle":
        etat = RECOMPENSE_NULLE
    elif actif is False:
        etat = ARRETE
    else:
        etat = EN_COURS

    pertes = [ligne["perte"] for ligne in pas_faits[-PERTES_RECENTES:]]
    validations = [ligne for ligne in pas_faits if _est_un_nombre(ligne.get("perte_val"))]
    reussites = [ligne for ligne in pas_faits if _est_un_nombre(ligne.get("reussite_val"))]
    sauvegardes = [
        ligne for ligne in lignes if ligne.get("evenement") == "sauvegarde" and isinstance(ligne.get("fichier"), str)
    ]
    debit, pas_du_debit = _debit(pas_faits, taille_lot)
    restant = None
    if etat != FINI and debit:
        restant = max(0, pas_total - pas) * (taille_lot or 1) / debit
    controle = lignes[-1].get("controle") if etat == RECOMPENSE_NULLE else None
    jetons_vus = None
    if taille_lot is not None:
        jetons_vus = dernier.get("jetons_vus") if dernier else 0
        if not isinstance(jetons_vus, int):
            jetons_vus = pas * taille_lot
    return Suivi(
        etat=etat,
        pas_de_l_etat=pas_de_l_etat,
        pas=pas,
        pas_total=pas_total,
        jetons_vus=jetons_vus,
        jetons_total=None if taille_lot is None else pas_total * taille_lot,
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
        logps_choisie_recentes=_recentes(pas_faits, "logps_choisie"),
        exactitude_recentes=_recentes(pas_faits, "exactitude"),
        recompense_recentes=_recentes(pas_faits, "recompense_moyenne"),
        reussite_val=reussites[-1]["reussite_val"] if reussites else None,
        pas_reussite_val=reussites[-1]["pas"] if reussites else None,
        controle=controle if isinstance(controle, dict) else None,
    )


# --- L'affichage, en français ---------------------------------------------------------


def _entier(valeur: float) -> str:
    """12 345 : espace fine insécable entre les milliers."""
    return entier(valeur, milliers=_FINE)


def _decimal(valeur: float, decimales: int) -> str:
    return nombre(valeur, decimales, milliers=_FINE)


def _pourcent(pas: int, total: int) -> str:
    """La part faite, arrondie au dixième en dessous (99,9 % tant que ce n'est pas fini)."""
    dixiemes = pas * 1000 // total if total else 0
    texte = _decimal(dixiemes / 10, 1).removesuffix(",0")
    return f"{texte}{_FINE}%"


def _part(valeur: float) -> str:
    """Une part en pour cent, au dixième : 62,5 %, 75 %."""
    return f"{_decimal(100 * valeur, 1).removesuffix(',0')}{_FINE}%"


def _derniere_et_moyenne(valeurs: tuple[float, ...], formater, unite: str) -> str:
    """La dernière valeur, son unité, puis la moyenne des derniers pas s'il y en a au moins deux."""
    texte = f"{formater(valeurs[-1])}{unite}"
    if len(valeurs) >= 2:
        texte += f" (moyenne des {len(valeurs)} derniers pas{_FINE}: {formater(sum(valeurs) / len(valeurs))})"
    return texte


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

    if suivi.etat == RECOMPENSE_NULLE:
        reponses = (suivi.controle or {}).get("reponses")
        combien = f" (aucune des {_entier(reponses)} réponses n'est juste)" if _est_un_nombre(reponses) else ""
        lignes = [
            f"{titre}arrêté, {RECOMPENSE_NULLE}{combien}",
            f"  Le RL n'aurait aucun signal{_FINE}: rien n'est lancé, rien n'est sauvegardé.",
            f"  Contrôle{_FINE}: {reglages.dossier_sortie / NOM_DU_CONTROLE}",
            f"  Relancer la même commande referait le même contrôle{_FINE}: ton IA doit d'abord réussir quelques "
            "problèmes (un SFT de raisonnement, ou des problèmes plus faciles).",
            f"  Journal{_FINE}: {reglages.journal}",
        ]
        return "\n".join(lignes)

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
    if suivi.jetons_total is not None:
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
    if suivi.logps_choisie_recentes:
        valeur = _derniere_et_moyenne(suivi.logps_choisie_recentes, lambda v: _decimal(v, 3), " par jeton")
        lignes.append(f"  Log-probabilité de la choisie{_FINE}: {valeur}")
    if suivi.exactitude_recentes:
        lignes.append(f"  Exactitude{_FINE}: {_derniere_et_moyenne(suivi.exactitude_recentes, _part, ' des paires')}")
    if suivi.recompense_recentes:
        valeur = _derniere_et_moyenne(suivi.recompense_recentes, _part, " des réponses justes")
        lignes.append(f"  Récompense moyenne{_FINE}: {valeur}")
    if suivi.reussite_val is not None:
        lignes.append(
            f"  Dernière validation{_FINE}: réussite {_part(suivi.reussite_val)} (pas {_entier(suivi.pas_reussite_val)})"
        )
    elif suivi.perte_val is None:
        lignes.append(f"  Dernière validation{_FINE}: aucune pour l'instant")
    else:
        lignes.append(f"  Dernière validation{_FINE}: {_decimal(suivi.perte_val, 3)} (pas {_entier(suivi.pas_val)})")
    if suivi.debit is not None:
        sur = (
            "sur le dernier pas"
            if suivi.pas_du_debit == 1
            else f"sur les {suivi.pas_du_debit} derniers pas, validations et sauvegardes comprises"
        )
        if suivi.jetons_total is None:  # le GRPO : des secondes par pas
            lignes.append(f"  Débit récent{_FINE}: {_decimal(1 / suivi.debit, 1)} s par pas ({sur})")
        else:
            lignes.append(f"  Débit récent{_FINE}: {_entier(suivi.debit)} jetons/s ({sur})")
    if suivi.etat != FINI:
        if suivi.restant is None:
            lignes.append(f"  Temps restant estimé{_FINE}: inconnu (aucun pas fini pour l'instant)")
        else:
            lignes.append(
                f"  Temps restant estimé{_FINE}: {duree(suivi.restant)} (au débit récent, pauses non comptées)"
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
