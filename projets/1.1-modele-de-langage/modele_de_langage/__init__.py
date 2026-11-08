"""Un modèle de langage à n-grammes de caractères, appris sur le texte du site."""

from modele_de_langage.hasard import Hasard
from modele_de_langage.ngrammes import (
    ORDRE_MAX,
    TEMPERATURES,
    alphabet,
    charger_texte,
    compter,
    compter_par_ordre,
    couper,
    distribution,
    generer,
    part_jamais_vue,
    perplexite,
    poids,
    tirer,
    tourne_en_rond,
)
