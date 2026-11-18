"""Un petit modèle tiré au hasard, publié comme une version de ton IA : de quoi tester sans entraînement.

Le modèle est minuscule (2 couches, des vecteurs de 32 nombres). `exporter_comme_la_release` l'écrit avec
`forge.exporter`, dans un dossier qui a la forme de `FORGE_IA_MODELES` : `<dossier>/ton-ia-1.7/…`. C'est
ce que le notebook prendra, à la place de la vraie version `ton-ia-1.7`, tant qu'elle n'est pas publiée.
"""

import dataclasses
from pathlib import Path

import forge
import torch
from forge.donnees.jetons import empreinte_du_tokenizer
from forge.entrainement.boucle import VERSION_DE_LA_SAUVEGARDE
from forge.entrainement.sauvegarde import sauvegarder
from forge.exporter import exporter
from forge.modele import ConfigModele, Transformer
from forge.publication import nom_des_poids
from forge.tokenizer.bpe_octets import TokenizerOctets

TOKENIZER = Path(forge.__file__).resolve().parent / "ressources" / "tokenizer-ton-ia-v1.json"
CONFIG = ConfigModele(dim=32, couches=2, tetes=4, longueur_contexte=128)
ETIQUETTE = "ton-ia-1.7"


def petit_modele(graine: int = 0) -> Transformer:
    """Un transformer aux poids tirés au hasard (la même graine, les mêmes poids)."""
    with torch.random.fork_rng():
        torch.manual_seed(graine)
        return Transformer(CONFIG).eval()


def exporter_comme_la_release(modele: Transformer, dossier: Path, etiquette: str = ETIQUETTE) -> Path:
    """Les fichiers de `modele`, écrits par `forge.exporter.exporter` comme ceux d'une version publiée ; rend `dossier`."""
    etat = {
        "version": VERSION_DE_LA_SAUVEGARDE,
        "pas": 0,
        "modele": modele.state_dict(),
        "config": {},
        "config_modele": dataclasses.asdict(modele.config),
        "empreinte_du_tokenizer": empreinte_du_tokenizer(TokenizerOctets.charger(TOKENIZER)),
    }
    sauvegarde = sauvegarder(dossier.parent / f"{dossier.name}-sauvegarde", etat, "meilleur.pt")
    exporter(sauvegarde, dossier, nom_des_poids(etiquette))
    return dossier
