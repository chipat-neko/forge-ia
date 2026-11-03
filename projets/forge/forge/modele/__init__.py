"""Le modèle de « ton IA » : un transformer décodeur seul, ses cinq tailles et la génération."""

from forge.modele.config import PRESETS, ConfigModele, largeur_cachee, nombre_parametres
from forge.modele.generation import generer
from forge.modele.transformer import Transformer

__all__ = [
    "PRESETS",
    "ConfigModele",
    "Transformer",
    "generer",
    "largeur_cachee",
    "nombre_parametres",
]
