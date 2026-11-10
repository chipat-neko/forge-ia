"""Charger une sauvegarde de l'entraînement de forge (un fichier `etape-*.pt` ou `meilleur.pt`).

`charger_sauvegarde` passe par `forge.entrainement.sauvegarde.charger`, puis reconstruit le modèle
comme le fait l'évaluation de forge (`forge.evaluation.rapport._lire_sauvegarde`) : la configuration
du modèle est dans la sauvegarde, avec ses poids. Le modèle rendu est en mode évaluation, sur
l'appareil demandé.
"""

from pathlib import Path

import torch
from forge.entrainement.sauvegarde import charger, charger_derniere
from forge.modele import ConfigModele, Transformer


# region: sauvegarde
def charger_sauvegarde(chemin: Path, appareil: str = "cpu") -> tuple[Transformer, ConfigModele]:
    """Le modèle d'une sauvegarde de forge, prêt à calculer sur `appareil` (« cpu » ou « cuda »), et sa configuration.

    `chemin` est un fichier `.pt` (`etape-0006370.pt`, `meilleur.pt`), ou le dossier `sauvegardes/` d'un
    entraînement : on prend alors sa dernière étape.
    """
    from forge.entrainement.boucle import VERSION_DE_LA_SAUVEGARDE  # ici : ce paquet importe forge.evaluation

    chemin = Path(chemin)
    if chemin.is_dir():
        etat = charger_derniere(chemin)
        if etat is None:
            raise FileNotFoundError(
                f"Aucune sauvegarde etape-*.pt dans {chemin}. Donne un fichier .pt, par exemple {chemin / 'meilleur.pt'}."
            )
    elif chemin.is_file():
        try:
            etat = charger(chemin)
        except Exception as erreur:  # fichier tronqué, ou qui n'est pas de PyTorch
            raise ValueError(
                f"{chemin} ne se lit pas comme une sauvegarde de la forge ({type(erreur).__name__}). "
                "Prends un fichier etape-*.pt ou meilleur.pt du dossier sauvegardes/ d'un entraînement."
            ) from erreur
    else:
        raise FileNotFoundError(
            f"Sauvegarde introuvable\u202f: {chemin}. Donne un fichier .pt du dossier sauvegardes/ d'un "
            "entraînement (etape-*.pt ou meilleur.pt)."
        )
    if not isinstance(etat, dict) or "modele" not in etat or "config_modele" not in etat:
        raise ValueError(
            f"{chemin} n'est pas une sauvegarde de la forge\u202f: il n'y a ni «\u202fmodele\u202f» ni «\u202fconfig_modele\u202f» "
            "dedans. Prends un fichier etape-*.pt ou meilleur.pt du dossier sauvegardes/ d'un entraînement."
        )
    if etat.get("version") != VERSION_DE_LA_SAUVEGARDE:
        raise ValueError(
            f"Sauvegarde de version {etat.get('version')!r}\u202f: cette version de la forge lit la "
            f"version {VERSION_DE_LA_SAUVEGARDE}."
        )
    config = ConfigModele(**etat["config_modele"])
    modele = Transformer(config)
    try:
        modele.load_state_dict(etat["modele"])
    except RuntimeError as erreur:
        raise ValueError(
            f"Les poids de {chemin} ne correspondent pas au modèle que sa configuration décrit "
            f"({str(erreur).splitlines()[0]}). La sauvegarde est abîmée, ou d'une autre version de la forge."
        ) from erreur
    return modele.to(torch.device(appareil)).eval(), config
# fin: sauvegarde
