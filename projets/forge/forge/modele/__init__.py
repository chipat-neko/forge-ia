"""Le modèle de « ton IA » : un transformer décodeur seul, ses cinq tailles et la génération."""

from forge.modele.cache import CacheKV
from forge.modele.config import PRESETS, ConfigModele, largeur_cachee, nombre_parametres
from forge.modele.generation import generer
from forge.modele.generation_lot import generer_lot
from forge.modele.transformer import Transformer

__all__ = [
    "PRESETS",
    "CacheKV",
    "ConfigModele",
    "Transformer",
    "generer",
    "generer_lot",
    "largeur_cachee",
    "nombre_parametres",
]
