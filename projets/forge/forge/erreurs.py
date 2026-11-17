"""Les erreurs que plusieurs couches de la forge lèvent ou attrapent.

Elles vivent ici, et non dans le module qui les a vues naître, pour que charger l'une
n'importe pas tout un autre module (l'apprentissage du tokenizer, par exemple).
"""


class DonneesManquantes(Exception):
    """Les textes ou les jetons attendus sont absents, ou leur préparation n'est pas finie."""
