"""Le transformer de « ton IA » : un modèle « décodeur seul » qui prédit le jeton suivant.

Le principe, de bout en bout (`Transformer.forward`) :

1. chaque jeton (un entier) devient un vecteur de `dim` nombres, par le plongement ;
2. ces vecteurs traversent `couches` blocs identiques. Dans un bloc, l'attention laisse chaque
   jeton regarder les jetons qui le précèdent (jamais ceux qui le suivent : c'est « causal »),
   puis le MLP retravaille chaque jeton séparément. Chaque sous-couche AJOUTE son résultat au
   vecteur (connexion résiduelle) au lieu de le remplacer ;
3. une dernière normalisation, puis une projection vers le vocabulaire donne, pour chaque
   position, un score (logit) par jeton possible : le jeton le mieux noté est le plus probable.

Les choix d'architecture sont ceux des modèles de langage récents (famille Llama) :

- RMSNorm placée AVANT chaque sous-couche (« pré-normalisation ») : elle garde les vecteurs
  à une échelle raisonnable, ce qui rend l'entraînement stable ;
- RoPE (positions par rotation) : voir `appliquer_rope` ;
- MLP SwiGLU : voir `MLP` ;
- aucun biais (aucun « + b ») dans les couches linéaires : moins de paramètres, aucune perte ;
- le plongement d'entrée et la projection de sortie sont la MÊME matrice (« poids liés ») :
  le vecteur qui représente un jeton en entrée sert aussi à mesurer, en sortie, à quel point
  ce jeton est probable. Cela économise `taille_vocabulaire × dim` paramètres.
"""

import math

import torch
import torch.nn.functional as F
from torch import Tensor, nn

from forge.modele.config import ConfigModele, largeur_cachee

EPSILON_RMSNORM = 1e-5

# Écart-type de la loi normale qui tire les poids au départ (valeur classique des GPT).
ECART_INITIAL = 0.02


class RMSNorm(nn.Module):
    """Normalisation « racine de la moyenne des carrés » (RMSNorm).

    Elle divise chaque vecteur par sa taille moyenne (la racine de la moyenne de ses carrés),
    puis multiplie chaque composante par un poids appris (`poids`, 1 au départ). Après elle,
    tous les vecteurs ont à peu près la même échelle, quelle que soit leur taille d'avant.
    Plus simple que LayerNorm : pas de soustraction de la moyenne, pas de biais.

    Le calcul se fait en `float32` même quand le reste est en `bfloat16` (précision en moins) :
    une moyenne de carrés en `bfloat16` serait trop imprécise. Le résultat reprend le type de
    l'entrée.
    """

    def __init__(self, dim: int, epsilon: float = EPSILON_RMSNORM) -> None:
        super().__init__()
        self.epsilon = epsilon
        self.poids = nn.Parameter(torch.ones(dim))

    def forward(self, x: Tensor) -> Tensor:
        x32 = x.float()
        normalise = x32 * torch.rsqrt(x32.pow(2).mean(dim=-1, keepdim=True) + self.epsilon)
        return (normalise * self.poids).type_as(x)


def rope_cos_sin(
    longueur: int, dim_tete: int, base: float, peripherique: torch.device | str
) -> tuple[Tensor, Tensor]:
    """Cosinus et sinus des angles de RoPE, en `float32`, de forme `[longueur, dim_tete // 2]`.

    La paire numéro `i` d'une tête (ses valeurs `2i` et `2i+1`) tourne, à la position `p`,
    de l'angle `p × base^(-2i / dim_tete)`. Les premières paires tournent vite (elles
    distinguent des positions voisines), les dernières lentement (elles distinguent des
    positions éloignées), comme les aiguilles d'une horloge : secondes, minutes, heures.

    Ces tables sont recalculées à chaque passe plutôt que gardées en mémoire du modèle : le
    calcul est minuscule, et ainsi elles restent toujours en `float32`, même si l'on convertit
    le modèle en `bfloat16`.
    """
    exposants = torch.arange(0, dim_tete, 2, device=peripherique, dtype=torch.float32) / dim_tete
    frequences = base ** (-exposants)  # une fréquence par paire
    positions = torch.arange(longueur, device=peripherique, dtype=torch.float32)
    angles = torch.outer(positions, frequences)  # [longueur, dim_tete // 2]
    return angles.cos(), angles.sin()


def appliquer_rope(x: Tensor, cos: Tensor, sin: Tensor) -> Tensor:
    """Applique RoPE (« rotary position embedding ») aux requêtes ou aux clés.

    L'attention compare une requête q (ce que cherche un jeton) à des clés k (ce que propose
    chaque jeton). Sans RoPE, elle ne saurait pas dans quel ordre sont les jetons. RoPE
    l'apprend sans aucun paramètre : chaque tête est découpée en paires de valeurs
    `(x[2i], x[2i+1])`, vues comme un point du plan, et chaque point est tourné d'un angle
    proportionnel à la position du jeton. Le produit scalaire q·k entre la position `m` et la
    position `n` ne dépend alors que de l'écart `m - n` : le modèle sent à quelle distance se
    trouvent deux jetons, pas leur position absolue.

    `x` a la forme `[lot, têtes, positions, dim_tete]` ; `cos` et `sin` viennent de
    `rope_cos_sin`. La rotation se calcule en `float32`, puis le résultat reprend le type de
    `x` (`bfloat16` sous autocast).
    """
    paires = x.float().reshape(*x.shape[:-1], -1, 2)  # [..., dim_tete // 2, 2]
    x1, x2 = paires[..., 0], paires[..., 1]
    tourne = torch.stack((x1 * cos - x2 * sin, x1 * sin + x2 * cos), dim=-1)
    return tourne.flatten(-2).type_as(x)


class Attention(nn.Module):
    """Attention multi-têtes causale.

    Chaque jeton produit trois vecteurs : une requête q (ce qu'il cherche), une clé k (ce
    qu'il propose) et une valeur v (ce qu'il transmet). Il compare sa requête aux clés de tous
    les jetons qui le précèdent (lui compris), en déduit des poids qui totalisent 1
    (softmax), et reçoit la moyenne pondérée des valeurs. Plusieurs têtes le font en
    parallèle, chacune sur une tranche des vecteurs, pour suivre plusieurs relations à la fois
    (accord du verbe, parenthèse ouverte, nom de variable…).
    """

    def __init__(self, config: ConfigModele) -> None:
        super().__init__()
        self.tetes = config.tetes
        self.dim_tete = config.dim // config.tetes
        # q, k et v d'un coup : une seule grosse multiplication est plus rapide que trois.
        self.proj_qkv = nn.Linear(config.dim, 3 * config.dim, bias=False)
        # Revient dans le résidu : initialisée plus petite (voir `Transformer._initialiser`).
        self.proj_sortie = nn.Linear(config.dim, config.dim, bias=False)

    def forward(self, x: Tensor, cos: Tensor, sin: Tensor) -> Tensor:
        lot, positions, dim = x.shape
        q, k, v = self.proj_qkv(x).chunk(3, dim=-1)
        # [lot, positions, dim] -> [lot, têtes, positions, dim_tete]
        q, k, v = (
            t.reshape(lot, positions, self.tetes, self.dim_tete).transpose(1, 2) for t in (q, k, v)
        )
        q, k = appliquer_rope(q, cos, sin), appliquer_rope(k, cos, sin)
        # `is_causal=True` : un jeton ne voit que lui-même et ceux d'avant.
        sortie = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        return self.proj_sortie(sortie.transpose(1, 2).reshape(lot, positions, dim))


class MLP(nn.Module):
    """MLP « SwiGLU » : la partie qui retravaille chaque jeton séparément.

    Un MLP simple fait `basse(activation(haute(x)))`. Le SwiGLU ajoute une « porte » : deux
    projections partent de x, l'une (`proj_porte`) passe par la fonction SiLU (une courbe
    douce qui laisse passer les valeurs positives et étouffe les négatives), puis les deux
    sont multipliées terme à terme, ce qui laisse la porte décider, composante par
    composante, quoi garder de l'autre (`proj_haute`). Une dernière projection (`proj_basse`)
    ramène à `dim`. À nombre de paramètres égal, c'est un peu meilleur qu'un MLP simple.

    La largeur de la couche cachée est `largeur_cachee(dim)` (8/3 × dim, multiple de 64).
    """

    def __init__(self, config: ConfigModele) -> None:
        super().__init__()
        h = largeur_cachee(config.dim)
        self.proj_porte = nn.Linear(config.dim, h, bias=False)
        self.proj_haute = nn.Linear(config.dim, h, bias=False)
        # Revient dans le résidu : initialisée plus petite (voir `Transformer._initialiser`).
        self.proj_basse = nn.Linear(h, config.dim, bias=False)

    def forward(self, x: Tensor) -> Tensor:
        return self.proj_basse(F.silu(self.proj_porte(x)) * self.proj_haute(x))


class Bloc(nn.Module):
    """Un bloc du transformer : attention puis MLP, chacun précédé d'une RMSNorm.

    `x = x + attention(norme(x))`, puis `x = x + mlp(norme(x))`. Le `x +` est la connexion
    résiduelle : chaque sous-couche n'écrit qu'une correction, et l'information d'origine
    traverse tout le modèle sans être déformée.
    """

    def __init__(self, config: ConfigModele) -> None:
        super().__init__()
        self.norme_attention = RMSNorm(config.dim)
        self.attention = Attention(config)
        self.norme_mlp = RMSNorm(config.dim)
        self.mlp = MLP(config)

    def forward(self, x: Tensor, cos: Tensor, sin: Tensor) -> Tensor:
        x = x + self.attention(self.norme_attention(x), cos, sin)
        return x + self.mlp(self.norme_mlp(x))


class Transformer(nn.Module):
    """Le modèle de langage de « ton IA » (décodeur seul).

    `forward(ids, cibles)` prend un lot de textes déjà découpés en jetons (`ids`, entiers de
    forme `[lot, positions]`, au plus `longueur_contexte` positions) et renvoie
    `(logits, perte)` :

    - `logits` : `[lot, positions, taille_vocabulaire]`, le score de chaque jeton possible
      comme SUITE du texte, à chaque position (la position `t` prédit le jeton `t + 1`) ;
    - `perte` : la moyenne de l'entropie croisée entre ces scores et `cibles` (le vrai jeton
      suivant, de même forme que `ids`), ou `None` sans `cibles`. Une cible égale à -100 est
      ignorée. Un modèle qui devine au hasard a une perte de `ln(taille_vocabulaire)` (10,4
      pour 32 768 jetons) ; plus elle descend, mieux le modèle prédit.
    """

    def __init__(self, config: ConfigModele) -> None:
        super().__init__()
        self.config = config
        self.plongement = nn.Embedding(config.taille_vocabulaire, config.dim)
        self.blocs = nn.ModuleList([Bloc(config) for _ in range(config.couches)])
        self.norme_finale = RMSNorm(config.dim)
        self.sortie = nn.Linear(config.dim, config.taille_vocabulaire, bias=False)
        # Poids liés : la projection de sortie est la même matrice que le plongement.
        self.sortie.weight = self.plongement.weight
        self._initialiser()

    def _initialiser(self) -> None:
        """Tire les poids au départ : loi normale d'écart-type 0,02.

        Les deux projections qui reviennent dans le résidu (la sortie de l'attention et la
        dernière du MLP) reçoivent 0,02 / √(2 × couches) : chaque bloc en ajoute deux au
        résidu, donc 2 × couches ajouts en tout, et cette échelle empêche leur somme de grossir
        avec la profondeur. Les RMSNorm restent à 1 (leur valeur de départ).
        """
        for module in self.modules():
            if isinstance(module, nn.Linear | nn.Embedding):
                nn.init.normal_(module.weight, mean=0.0, std=ECART_INITIAL)
        ecart_residuel = ECART_INITIAL / math.sqrt(2 * self.config.couches)
        for bloc in self.blocs:
            nn.init.normal_(bloc.attention.proj_sortie.weight, mean=0.0, std=ecart_residuel)
            nn.init.normal_(bloc.mlp.proj_basse.weight, mean=0.0, std=ecart_residuel)

    def forward(self, ids: Tensor, cibles: Tensor | None = None) -> tuple[Tensor, Tensor | None]:
        positions = ids.shape[1]
        if positions > self.config.longueur_contexte:
            raise ValueError(
                f"Le texte a {positions} jetons, mais ce modèle n'en lit que "
                f"{self.config.longueur_contexte} d'un coup (`longueur_contexte`). "
                "Coupe le texte en morceaux plus courts."
            )
        x = self.plongement(ids)
        dim_tete = self.config.dim // self.config.tetes
        cos, sin = rope_cos_sin(positions, dim_tete, self.config.base_rope, ids.device)
        for bloc in self.blocs:
            x = bloc(x, cos, sin)
        logits = self.sortie(self.norme_finale(x))
        perte = None
        if cibles is not None:
            perte = F.cross_entropy(logits.reshape(-1, logits.shape[-1]), cibles.reshape(-1))
        return logits, perte
