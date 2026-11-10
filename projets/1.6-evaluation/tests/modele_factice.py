"""Un petit modèle tiré au hasard, sa sauvegarde et le tokenizer figé : de quoi tester sans entraînement.

Le modèle est minuscule (2 couches, des vecteurs de 32 nombres) : les cartes, les scores et les
sauvegardes se testent en une fraction de seconde, sans les poids de « mini ».
"""

import dataclasses
from pathlib import Path

import forge
import torch
from forge.entrainement.boucle import VERSION_DE_LA_SAUVEGARDE
from forge.modele import ConfigModele, Transformer
from forge.tokenizer.bpe_octets import TokenizerOctets

TOKENIZER = Path(forge.__file__).resolve().parent / "ressources" / "tokenizer-ton-ia-v1.json"
CONFIG = ConfigModele(dim=32, couches=2, tetes=4, longueur_contexte=64)


def petit_modele(graine: int = 0) -> Transformer:
    """Un transformer aux poids tirés au hasard (la même graine, les mêmes poids)."""
    with torch.random.fork_rng():
        torch.manual_seed(graine)
        return Transformer(CONFIG).eval()


def tokenizer() -> TokenizerOctets:
    return TokenizerOctets.charger(TOKENIZER)


def sauvegarder(modele: Transformer, chemin: Path, pas: int = 7) -> Path:
    """Écrit `modele` au format des sauvegardes de forge (voir `forge.entrainement.boucle._etat_du_modele`)."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "version": VERSION_DE_LA_SAUVEGARDE,
            "pas": pas,
            "modele": modele.state_dict(),
            "config_modele": dataclasses.asdict(modele.config),
        },
        chemin,
    )
    return chemin
