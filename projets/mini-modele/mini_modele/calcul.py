"""Le noyau de calcul exact du mini-modèle.

Le site refait chaque calcul de ce paquet en TypeScript, et les deux langages
doivent trouver les mêmes nombres, au bit près. Or la norme IEEE 754 ne fixe
le dernier bit que des + − × ÷ et de la racine carrée : les exp, log et cos de
la machine (et ceux du navigateur) peuvent différer d'un bit. D'où ce module :

- exp, log et cos écrits avec des + − × ÷ seulement, dans un ordre fixé ;
- des sommes en boucle, dans l'ordre des indices, sans compensation ;
- un hasard maison (SplitMix32), qui donne la même suite partout ;
- des motifs hexadécimaux et des empreintes, pour comparer les deux langages.

Le jumeau TypeScript est site/src/lib/mini-modele/calcul.ts : il suit ce
fichier ligne à ligne. Ce fichier est vérifié par tests/test_sources.py.
"""

import math
import struct
from collections.abc import MutableSequence, Sequence

# ln 2 coupé en deux morceaux, comme dans fdlibm : la partie haute n'a que 32
# bits significatifs, donc k × LN2_HAUT est exact pour tous les k de exp et log.
LN2_HAUT = 0.6931471803691238  # 3fe62e42fee00000
LN2_BAS = 1.9082149292705877e-10  # 3dea39ef35793c76
INV_LN2 = 1.4426950408889634  # 3ff71547652b82fe : 1 / ln 2
SQRT_DEMI = 0.7071067811865476  # 3fe6a09e667f3bcd : la racine de 1/2
PI = 3.141592653589793  # 400921fb54442d18

# Coefficients des séries, calculés par des divisions (les mêmes en TypeScript).
# exp(r) = 1 + r + r^2/2! + … + r^13/13! : C_EXP[n] = 1/n!
C_EXP = [1.0]
for n in range(1, 14):
    C_EXP.append(C_EXP[-1] / n)
# ln m = 2s × (1 + z/3 + z^2/5 + … + z^11/23), avec s = (m − 1)/(m + 1) et z = s × s.
C_LOG = [1.0 / (2 * n + 1) for n in range(12)]
# cos t = 1 − t^2/2! + t^4/4! − … + t^24/24! : C_COS[n] = (−1)^n / (2n)!
C_COS = [1.0]
for n in range(1, 13):
    C_COS.append(-C_COS[-1] / ((2 * n - 1) * (2 * n)))


def deux_puissance(k: int) -> float:
    """2^k exact, pour k de -1074 à 1023 : math.ldexp ne fait que poser l'exposant."""
    if not -1074 <= k <= 1023:
        raise ValueError(f"deux_puissance : k doit aller de -1074 à 1023 (reçu {k}).")
    return math.ldexp(1.0, k)


# region: exp
def exp(x: float) -> float:
    """e^x, avec seulement des + − × ÷.

    1. On écrit x = k × ln 2 + r, avec k entier et r entre -0,35 et 0,35.
    2. e^r est la série de Taylor jusqu'à r^13, calculée par Horner.
    3. e^x = e^r × 2^k, et multiplier par 2^k est exact.
    """
    if x != x:  # NaN
        return x
    if x > 709.782712893384:  # au-delà, e^x dépasse le plus grand flottant
        return math.inf
    if x < -745.1332191019411:  # en deçà, e^x s'arrondit à 0
        return 0.0
    k = math.floor(x * INV_LN2 + 0.5)
    r = (x - k * LN2_HAUT) - k * LN2_BAS
    p = C_EXP[13]
    for n in range(12, -1, -1):
        p = p * r + C_EXP[n]
    if k > 1023:  # 2^1024 n'est pas un flottant : on passe par 2 × 2^1023
        return (p * 2.0) * deux_puissance(k - 1)
    if k < -1022:  # résultat sous-normal : produit exact d'abord, un seul arrondi à la fin
        return (p * deux_puissance(k + 64)) * deux_puissance(-64)
    return p * deux_puissance(k)
# fin: exp


# region: log
def log(x: float) -> float:
    """ln x, avec seulement des + − × ÷.

    1. On écrit x = m × 2^e, avec m entre √½ et √2 (math.frexp est exact).
    2. ln x = e × ln 2 + ln m.
    3. ln m = 2s × (1 + s^2/3 + s^4/5 + …), avec s = (m − 1)/(m + 1) : la
       série converge vite, car |s| reste sous 0,18.
    """
    if x != x or x < 0.0:
        return math.nan
    if x == 0.0:
        return -math.inf
    if x == math.inf:
        return x
    m, e = math.frexp(x)  # m dans [0,5 ; 1[
    if m < SQRT_DEMI:
        m = m * 2.0
        e = e - 1
    f = m - 1.0
    s = f / (2.0 + f)
    z = s * s
    q = C_LOG[11]
    for n in range(10, -1, -1):
        q = q * z + C_LOG[n]
    return e * LN2_HAUT + (2.0 * s * q + e * LN2_BAS)
# fin: log


def cos(x: float) -> float:
    """cos x, pour x de 0 à π seulement : c'est tout ce qu'il faut au mini-modèle."""
    if not (0.0 <= x <= PI):  # rejette aussi NaN
        raise ValueError(f"cos n'est définie ici que de 0 à π (reçu {x}).")
    if x > PI * 0.5:  # cos x = −cos(π − x), et PI − x est exact
        return -_cos_noyau(PI - x)
    return _cos_noyau(x)


def _cos_noyau(t: float) -> float:
    """La série de Taylor de cos jusqu'à t^24, calculée par Horner, pour t de 0 à π/2."""
    z = t * t
    p = C_COS[12]
    for n in range(11, -1, -1):
        p = p * z + C_COS[n]
    return p


def racine(x: float) -> float:
    """√x : la racine carrée est arrondie correctement, en pratique partout (Math.sqrt en TS)."""
    if x < 0.0:
        raise ValueError(f"racine d'un nombre négatif ({x}) : vérifie le calcul qui a produit ce nombre.")
    return math.sqrt(x)


def somme(valeurs: Sequence[float]) -> float:
    """La somme dans l'ordre des indices, par une simple boucle, sans compensation."""
    s = 0.0
    for v in valeurs:
        s += v
    return s


def produit_scalaire(a: Sequence[float], b: Sequence[float]) -> float:
    """a[0] × b[0] + a[1] × b[1] + …, dans l'ordre des indices."""
    if len(a) != len(b):
        raise ValueError(
            f"produit_scalaire : les deux listes n'ont pas la même longueur ({len(a)} et {len(b)}). "
            "Donne deux listes de même longueur."
        )
    s = 0.0
    for i in range(len(a)):
        s += a[i] * b[i]
    return s


def maximum(valeurs: Sequence[float]) -> float:
    """La plus grande valeur, par une boucle « if v > m » : à égalité, la première gagne (même −0 face à 0)."""
    if len(valeurs) == 0:
        raise ValueError("maximum : la liste est vide. Donne au moins une valeur.")
    m = valeurs[0]
    for i in range(1, len(valeurs)):
        if valeurs[i] > m:
            m = valeurs[i]
    return m


# Tous les NaN s'écrivent avec ce motif : celui d'un NaN calculé varie d'une machine à l'autre.
NAN_HEX = "7ff8000000000000"


def _octets(x: float) -> bytes:
    """Les 8 octets du flottant, du plus fort au plus faible ; tous les NaN avec le motif NAN_HEX."""
    if x != x:
        return bytes.fromhex(NAN_HEX)
    return struct.pack(">d", x)


def vers_hex(x: float) -> str:
    """Les 8 octets du flottant, du plus fort au plus faible, en 16 chiffres hexadécimaux minuscules."""
    return _octets(x).hex()


def depuis_hex(h: str) -> float:
    """Le flottant écrit par vers_hex."""
    if len(h) != 16 or any(c not in "0123456789abcdef" for c in h):
        raise ValueError(f"depuis_hex attend 16 chiffres hexadécimaux minuscules (reçu « {h} »).")
    return struct.unpack(">d", bytes.fromhex(h))[0]


# FNV-1a sur 32 bits : une empreinte courte, pour comparer de longues listes de nombres.
FNV_DEPART = 0x811C9DC5
FNV_PREMIER = 0x01000193


def _fnv1a(h: int, octets: bytes) -> int:
    """Les octets de plus dans l'empreinte : pour chacun, (h xor o) × FNV_PREMIER, modulo 2^32."""
    for o in octets:
        h = ((h ^ o) * FNV_PREMIER) & 0xFFFFFFFF
    return h


def empreinte(valeurs: Sequence[float]) -> str:
    """FNV-1a 32 bits sur les 8 octets de chaque flottant (ceux de vers_hex), en 8 chiffres hexadécimaux."""
    h = FNV_DEPART
    for v in valeurs:
        h = _fnv1a(h, _octets(v))
    return f"{h:08x}"


def empreinte_texte(texte: str) -> str:
    """FNV-1a 32 bits sur les octets UTF-8 du texte, en 8 chiffres hexadécimaux."""
    return f"{_fnv1a(FNV_DEPART, texte.encode('utf-8')):08x}"


class Hasard:
    """Le hasard reproductible du mini-modèle : SplitMix32.

    Une même graine donne la même suite en Python et en TypeScript, sur toutes
    les machines. La graine est un entier, ramené à 32 bits (de 0 à 2^32 − 1).
    """

    def __init__(self, graine: int) -> None:
        if not isinstance(graine, int):
            raise TypeError(
                f"La graine du hasard doit être un entier (reçu {graine!r}). Donne un entier de 0 à 2^32 − 1."
            )
        self.etat = graine & 0xFFFFFFFF

    def suivant32(self) -> int:
        """Le prochain entier sur 32 bits, de 0 à 2^32 − 1."""
        self.etat = (self.etat + 0x9E3779B9) & 0xFFFFFFFF
        z = self.etat
        z = ((z ^ (z >> 16)) * 0x21F0AAAD) & 0xFFFFFFFF
        z = ((z ^ (z >> 15)) * 0x735A2D97) & 0xFFFFFFFF
        return z ^ (z >> 15)

    def uniforme(self) -> float:
        """Un flottant de [0, 1[ : suivant32 divisé par 2^32 (une division exacte)."""
        return self.suivant32() / 4294967296.0

    def entier(self, n: int) -> int:
        """Un entier de 0 à n − 1."""
        return math.floor(self.uniforme() * n)

    def gaussienne(self, ecart_type: float) -> float:
        """Presque une loi normale : 12 uniformes additionnées, moins 6 (moyenne 0, variance 1), fois l'écart-type."""
        s = 0.0
        for _ in range(12):
            s += self.uniforme()
        return (s - 6.0) * ecart_type

    def melanger(self, liste: MutableSequence) -> None:
        """Mélange la liste sur place : Fisher-Yates, de la fin vers le début."""
        for i in range(len(liste) - 1, 0, -1):
            j = self.entier(i + 1)
            liste[i], liste[j] = liste[j], liste[i]
