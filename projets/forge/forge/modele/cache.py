"""Le cache des clés et des valeurs : ne pas recalculer, à chaque jeton, tout le texte déjà lu.

Pour écrire un jeton, l'attention compare sa requête aux clés de tous les jetons d'avant, puis
mélange leurs valeurs. Ces clés et ces valeurs ne changent plus une fois calculées : un jeton ne
voit jamais ceux qui le suivent. `generer` les recalcule pourtant toutes à chaque pas, en relisant
tout le texte. Le cache les garde, couche par couche : à chaque pas, le modèle ne lit plus que le
nouveau jeton, calcule SA clé et SA valeur, les range au bout du cache, et compare sa requête à
tout ce qui est rangé. Le travail d'un pas ne grandit plus avec la longueur du texte (seule
l'attention, qui relit le cache, grandit un peu).
"""

import torch
from torch import Tensor

from forge.modele.config import ConfigModele


class CacheKV:
    """Les clés et les valeurs déjà calculées, pour chaque couche du modèle.

    - `k` et `v` : `[couches, lot, tetes, longueur_max, dim_tete]`, réservés d'un coup au départ ;
    - `longueur` : le nombre de positions déjà remplies (les mêmes pour toutes les couches) ;
    - `longueur_max` : le nombre de positions réservées.

    Chaque couche appelle `ajouter` avec les clés et valeurs de ses nouvelles positions. Elles
    sont rangées à partir de `longueur` ; `longueur` avance quand la dernière couche a écrit, car
    toutes les couches rangent les mêmes positions à chaque passe.
    """

    def __init__(
        self, config: ConfigModele, lot: int, longueur_max: int, appareil, dtype: torch.dtype
    ) -> None:
        dim_tete = config.dim // config.tetes
        forme = (config.couches, lot, config.tetes, longueur_max, dim_tete)
        self.k = torch.zeros(forme, device=appareil, dtype=dtype)
        self.v = torch.zeros(forme, device=appareil, dtype=dtype)
        self.longueur = 0
        self.longueur_max = longueur_max
        self._derniere_couche = config.couches - 1

    def ajouter(self, couche: int, k: Tensor, v: Tensor) -> tuple[Tensor, Tensor]:
        """Range `k` et `v` (`[lot, tetes, nouveaux, dim_tete]`) au bout du cache de `couche`.

        Rend les clés et les valeurs de toutes les positions remplies de cette couche, les
        nouvelles comprises : `[lot, tetes, longueur + nouveaux, dim_tete]`.
        """
        debut = self.longueur
        fin = debut + k.shape[2]
        if fin > self.longueur_max:
            raise ValueError(
                f"Le cache est plein : {debut} positions remplies, {k.shape[2]} de plus, mais "
                f"seulement {self.longueur_max} réservées. Crée un cache plus long "
                "(`longueur_max` = longueur de l'invite + nombre de jetons à écrire)."
            )
        self.k[couche, :, :, debut:fin] = k
        self.v[couche, :, :, debut:fin] = v
        if couche == self._derniere_couche:
            self.longueur = fin
        return self.k[couche, :, :, :fin], self.v[couche, :, :, :fin]
