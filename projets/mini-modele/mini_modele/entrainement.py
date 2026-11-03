"""L'entraînement du mini-modèle : le taux, l'écrêtage, AdamW, et l'Entraineur.

La recette est celle de ton IA (projets/forge) : AdamW avec beta1 = 0,9 et
beta2 = 0,95, une décroissance des poids de 0,1, un écrêtage du gradient à 1,
et un taux d'apprentissage qui monte en ligne droite, puis redescend en
cosinus. Le taux est le même code que forge/entrainement/planning.py, avec le
cos et le PI de calcul, dans le même ordre des opérations.

Un pas d'entraînement se fait dans cet ordre, le même en TypeScript :

1. le numéro du pas augmente (le premier pas porte le numéro 1) ;
2. la perte et le gradient d'un lot de prénoms ;
3. si la perte n'est pas finie, ou dépasse 3 × ln V, l'entraînement a
   divergé : on le note, et on s'arrête sans toucher aux paramètres ;
4. le taux du pas ;
5. l'écrêtage du gradient, puis le pas d'AdamW.

Trois hasards séparés, tous des Hasard (SplitMix32) : les poids de départ
(graine), l'ordre des prénoms (graine + 1), et les prénoms inventés au pas p
(un Hasard neuf de graine graine + 2 + p). Inventer des prénoms ou mesurer la
validation ne change donc rien à l'entraînement.

Le jumeau TypeScript est site/src/lib/mini-modele/entrainement.ts (et
reglages.ts pour les réglages) : il suit ce fichier ligne à ligne. Ce fichier
est vérifié par tests/test_sources.py.
"""

import math
from dataclasses import dataclass
from types import MappingProxyType

from mini_modele.calcul import PI, Hasard, cos, log, racine
from mini_modele.donnees import Donnees, decoder, donnees_par_defaut
from mini_modele.modele import ConfigMini, generer, initialiser, perte, perte_et_gradient

# Les taux d'apprentissage maximaux que le lecteur peut choisir sur le site.
TAUX_PROPOSES = (0.001, 0.003, 0.01, 0.03, 0.1, 0.3)

GRAINE_MAX = 4294967295  # 2^32 − 1 : la plus grande graine de Hasard

# Les champs entiers des réglages, et leur plus petite valeur permise.
_ENTIERS = (
    ("pas_total", 1),
    ("echauffement", 0),
    ("lot", 1),
    ("validation_tous", 1),
    ("nb_validation", 1),
    ("nb_echantillons", 0),
)


# Les champs flottants des réglages, et ce qu'ils doivent respecter.
_FLOTTANTS = (
    ("taux_max", "plus grand que 0", lambda x: x > 0.0),
    ("ratio_min", "de 0 à 1", lambda x: 0.0 <= x <= 1.0),
    ("beta1", "de 0 à 1, 1 non compris", lambda x: 0.0 <= x < 1.0),
    ("beta2", "de 0 à 1, 1 non compris", lambda x: 0.0 <= x < 1.0),
    ("epsilon", "plus grand que 0", lambda x: x > 0.0),
    ("poids_decroissance", "positif ou nul", lambda x: x >= 0.0),
    ("ecretage", "plus grand que 0", lambda x: x > 0.0),
)


def _est_entier(valeur: object) -> bool:
    return isinstance(valeur, int) and not isinstance(valeur, bool)


def _est_nombre(valeur: object) -> bool:
    return isinstance(valeur, (int, float)) and not isinstance(valeur, bool)


@dataclass(frozen=True)
class ReglagesMini:
    """Les réglages d'un entraînement. Une même valeur redonne exactement la même courbe."""

    pas_total: int
    echauffement: int
    taux_max: float = 0.01
    lot: int = 8
    ratio_min: float = 0.1
    beta1: float = 0.9
    beta2: float = 0.95
    epsilon: float = 1e-8
    poids_decroissance: float = 0.1
    ecretage: float = 1.0
    graine: int = 1234
    validation_tous: int = 100
    nb_validation: int = 256
    nb_echantillons: int = 8

    def __post_init__(self) -> None:
        for nom, plus_petit in _ENTIERS:
            valeur = getattr(self, nom)
            if not _est_entier(valeur) or valeur < plus_petit:
                raise ValueError(f"ReglagesMini : {nom} doit être un entier d'au moins {plus_petit} (reçu {valeur!r}).")
        if not _est_entier(self.graine) or not 0 <= self.graine <= GRAINE_MAX:
            raise ValueError(f"ReglagesMini : graine doit être un entier de 0 à 2^32 − 1 (reçu {self.graine!r}).")
        for nom, condition, permis in _FLOTTANTS:
            valeur = getattr(self, nom)
            if not _est_nombre(valeur) or not math.isfinite(valeur) or not permis(valeur):
                raise ValueError(f"ReglagesMini : {nom} doit être un nombre fini {condition} (reçu {valeur!r}).")
            # Un entier devient un flottant : en TypeScript, 1000 et 1000.0 sont le même nombre.
            object.__setattr__(self, nom, float(valeur))


# Les deux préréglages du site : l'entraînement complet (1.5), et l'avant-goût (0.5).
PRESETS_MINI = MappingProxyType(
    {
        "complet": ReglagesMini(pas_total=3000, echauffement=100),
        "avant-gout": ReglagesMini(pas_total=600, echauffement=50),
    }
)


def taux(pas: int, pas_total: int, taux_max: float, echauffement: int, ratio_min: float = 0.1) -> float:
    """Taux d'apprentissage du pas numéro pas (le premier pas porte le numéro 1) : le code de forge.

    - de 0 à echauffement : montée linéaire, de 0 à taux_max ;
    - de echauffement à pas_total : descente en cosinus, de taux_max à ratio_min × taux_max ;
    - après pas_total : ratio_min × taux_max, sans bouger.

    Exemple de forge, avec 1 000 pas dont 100 d'échauffement et taux_max = 1e-3 : le pas 50 a
    5e-4, le pas 100 a 1e-3, le pas 550 (au milieu de la descente) a 5,5e-4 et le pas 1 000 a 1e-4.
    """
    taux_min = ratio_min * taux_max
    if pas < echauffement:
        return taux_max * pas / echauffement
    if pas >= pas_total:
        return taux_min
    # forge prend le plus grand de 1 et de pas_total − echauffement : la même chose, en entiers.
    etendue = pas_total - echauffement
    if etendue < 1:
        etendue = 1
    avancement = (pas - echauffement) / etendue  # de 0 à 1 (jamais 1 : pas < pas_total)
    return taux_min + (taux_max - taux_min) * 0.5 * (1 + cos(PI * avancement))


class Entraineur:
    """Entraîne le mini-modèle sur les prénoms, un pas à la fois.

    Attributs : reglages, config (la forme du modèle), donnees, params (les
    paramètres, modifiés sur place), pas (0 au départ ; le premier pas porte le
    numéro 1), diverge (vrai dès que l'erreur a explosé) et limite_divergence.
    """

    def __init__(self, reglages: ReglagesMini, donnees: Donnees | None = None) -> None:
        if not isinstance(reglages, ReglagesMini):
            raise TypeError(f"Entraineur : les réglages doivent être un ReglagesMini (reçu {type(reglages).__name__}).")
        self.reglages = reglages
        self.donnees = donnees_par_defaut() if donnees is None else donnees
        n = len(self.donnees.entrainement)
        if reglages.lot > n:
            raise ValueError(
                f"Entraineur : un lot de {reglages.lot} prénoms, mais il n'y a que {n} prénoms d'entraînement. "
                "Prends un lot plus petit."
            )
        self.config = ConfigMini(taille_vocabulaire=len(self.donnees.vocabulaire))
        self.params = initialiser(self.config, Hasard(reglages.graine))
        self.pas = 0
        self.diverge = False
        # Au-delà de 3 × ln V (trois fois l'erreur du pur hasard), l'erreur a explosé.
        self.limite_divergence = 3.0 * log(float(self.config.taille_vocabulaire))
        nombre = len(self.params)
        self._gradient = [0.0] * nombre
        self._m = [0.0] * nombre
        self._v = [0.0] * nombre
        # beta1^pas et beta2^pas, tenus par des produits successifs (pas de puissance).
        self._b1t = 1.0
        self._b2t = 1.0
        self._derniere_perte = math.nan
        self._hasard_ordre = Hasard(reglages.graine + 1)
        self._ordre: list[int] = []
        self._position = 0
        self._melanger()

    def _melanger(self) -> None:
        """Un nouvel ordre des prénoms d'entraînement : list(range(n)) mélangée, et on repart de 0."""
        self._ordre = list(range(len(self.donnees.entrainement)))
        self._hasard_ordre.melanger(self._ordre)
        self._position = 0

    # region: lot
    def _prochain_lot(self) -> list[tuple[int, ...]]:
        """Les prénoms du prochain lot, dans l'ordre mélangé.

        Quand il n'en reste plus assez pour un lot entier, on mélange un nouvel
        ordre et on repart du début : les derniers prénoms de l'ancien ordre
        attendront le tour suivant.
        """
        r = self.reglages
        if self._position + r.lot > len(self.donnees.entrainement):
            self._melanger()
        lot = []
        for i in range(r.lot):
            lot.append(self.donnees.entrainement[self._ordre[self._position + i]])
        self._position += r.lot
        return lot
    # fin: lot

    def faire_un_pas(self) -> float:
        """Un pas d'entraînement. Renvoie l'erreur du lot, mesurée avant de corriger les paramètres.

        Si l'entraînement a divergé, ne fait plus rien et renvoie la dernière erreur.
        """
        if self.diverge:
            return self._derniere_perte
        r = self.reglages
        self.pas += 1
        lot = self._prochain_lot()
        gradient = self._gradient
        n = len(self.params)
        perte_lot = perte_et_gradient(self.config, self.params, lot, gradient)
        self._derniere_perte = perte_lot
        if not math.isfinite(perte_lot) or perte_lot > self.limite_divergence:
            self.diverge = True
            return perte_lot
        t = taux(self.pas, r.pas_total, r.taux_max, r.echauffement, r.ratio_min)
        # region: ecretage
        carres = 0.0
        for g in gradient:
            carres += g * g
        norme = racine(carres)
        if norme > r.ecretage:
            facteur = r.ecretage / norme
            for i in range(n):
                gradient[i] = gradient[i] * facteur
        # fin: ecretage
        # region: adamw
        self._b1t = self._b1t * r.beta1
        self._b2t = self._b2t * r.beta2
        for i in range(n):
            g = gradient[i]
            self._m[i] = r.beta1 * self._m[i] + (1.0 - r.beta1) * g
            self._v[i] = r.beta2 * self._v[i] + (1.0 - r.beta2) * (g * g)
            m_chapeau = self._m[i] / (1.0 - self._b1t)
            v_chapeau = self._v[i] / (1.0 - self._b2t)
            p = self.params[i] * (1.0 - t * r.poids_decroissance)
            self.params[i] = p - t * m_chapeau / (racine(v_chapeau) + r.epsilon)
        # fin: adamw
        return perte_lot

    def perte_validation(self) -> float:
        """L'erreur moyenne sur les nb_validation premiers prénoms de validation, que le modèle ne voit jamais."""
        return perte(self.config, self.params, self.donnees.validation[: self.reglages.nb_validation])

    def echantillons(self) -> list[str]:
        """nb_echantillons prénoms inventés, tirés par un Hasard(graine + 2 + pas) neuf."""
        r = self.reglages
        inventes = generer(self.config, self.params, Hasard(r.graine + 2 + self.pas), r.nb_echantillons)
        return [decoder(p, self.donnees.vocabulaire) for p in inventes]

    def taux_courant(self) -> float:
        """Le taux du pas numéro pas (0 avant le premier pas)."""
        r = self.reglages
        return taux(self.pas, r.pas_total, r.taux_max, r.echauffement, r.ratio_min)
