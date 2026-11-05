"""Écrire les nombres à la française : virgule décimale, espace fine entre les milliers, signe moins.

`en_francais` est une copie exacte de celle de projets/0.3-poste/poste/essai.py
(un test le vérifie quand le dépôt entier est là).
"""

import math

# Les chiffres en exposant, pour écrire 10⁻¹⁷.
EXPOSANTS = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")


def en_francais(x: float, chiffres: int = 2) -> str:
    """Un nombre positif à la française, avec `chiffres` chiffres significatifs (au moins les unités) :
    2,1 ; 13 ; 123 ; 0,031 ; 0,0000012 ; 1 234 (avec une espace fine)."""
    if x == 0:
        return "0"
    decimales = max(0, chiffres - 1 - math.floor(math.log10(abs(x))))
    return f"{x:,.{decimales}f}".replace(",", "\u202f").replace(".", ",")


def en_puissance_de_dix(x: float) -> str:
    """Un écart positif en écriture scientifique, avec 2 chiffres significatifs : « 3,1 × 10⁻¹⁷ »,
    ou « 0 » pour un écart nul."""
    if x == 0:
        return "0"
    mantisse, exposant = f"{x:.1e}".split("e")
    return f"{mantisse.replace('.', ',')} × 10{str(int(exposant)).translate(EXPOSANTS)}"


def simple_en_francais(x: float) -> str:
    """Un nombre court, sans zéro inutile : « 0,5 », « −1,5 », « 2 » ou « 0 » (les réglages du neurone, le taux)."""
    return f"{x:g}".replace(".", ",").replace("-", "−")
