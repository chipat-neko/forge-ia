"""L'aide de « forge » et de chacune de ses commandes s'affiche, sous toutes les versions de Python."""

import argparse

from forge.__main__ import construire_parseur


def test_toutes_les_aides_se_formatent():
    """argparse lit l'aide comme un gabarit `%` : un « 20 % » seul casse « forge --help » (et, à partir de
    Python 3.14, la création même du parseur, donc toutes les commandes)."""
    parseur = construire_parseur()
    assert "preferences" in parseur.format_help()
    sous_commandes = next(a for a in parseur._actions if isinstance(a, argparse._SubParsersAction))
    for nom, commande in sous_commandes.choices.items():
        assert commande.format_help(), nom
