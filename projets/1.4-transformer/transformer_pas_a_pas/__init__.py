"""Le transformer de « ton IA » refait pièce par pièce, en fonctions pures, et comparé à celui de forge."""

from transformer_pas_a_pas.compter import repartition
from transformer_pas_a_pas.pieces import (
    angles_rope,
    attention,
    bloc,
    masque,
    modele,
    plongement,
    poids_attention,
    rmsnorm,
    softmax,
    swiglu,
    tourner,
)
