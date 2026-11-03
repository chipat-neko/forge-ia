"""La configuration du modèle de « ton IA » : ses dimensions et les cinq tailles prévues.

Une configuration, c'est la liste des nombres qui fixent la forme du transformer : la taille
du vocabulaire, la largeur des vecteurs (`dim`), le nombre de couches empilées, le nombre de
têtes d'attention et la longueur de texte que le modèle voit d'un coup. Le nombre de
paramètres (les poids appris) en découle exactement, par `nombre_parametres`.
"""

from dataclasses import dataclass

# Les largeurs cachées du MLP sont des multiples de 64 : les cartes graphiques calculent
# plus vite quand les matrices ont des dimensions rondes.
PAS_LARGEUR_CACHEE = 64


def largeur_cachee(dim: int) -> int:
    """Largeur cachée du MLP SwiGLU : le multiple de 64 le plus proche de 8/3 × dim.

    Un MLP classique a une couche cachée de 4 × dim et deux matrices. Le SwiGLU en a trois
    (porte, haute, basse) ; pour garder à peu près le même nombre de paramètres, sa couche
    cachée vaut 8/3 × dim (3 × 8/3 = 2 × 4).

    À égalité exacte entre deux multiples de 64, on prend le plus grand (arrondi « vers le
    haut »). On calcule en nombres entiers, pour qu'aucune erreur d'arrondi des nombres
    décimaux ne décide du résultat : 8/3 × dim / 64 = dim / 24, et on arrondit dim / 24 à
    l'entier le plus proche par (dim + 12) // 24. Jamais moins de 64.

    Exemples : 768 donne 2048, 512 donne 1344, 1024 donne 2752.
    """
    multiples = (dim + 12) // 24
    return max(1, multiples) * PAS_LARGEUR_CACHEE


@dataclass(frozen=True, kw_only=True)
class ConfigModele:
    """Les dimensions d'un transformer.

    - `taille_vocabulaire` : nombre de jetons distincts (32 768 pour le tokenizer de ton IA) ;
    - `dim` : largeur des vecteurs qui représentent chaque jeton ;
    - `couches` : nombre de blocs (attention + MLP) empilés ;
    - `tetes` : nombre de têtes d'attention ; chaque tête travaille sur `dim // tetes` valeurs ;
    - `longueur_contexte` : nombre maximal de jetons que le modèle lit d'un coup ;
    - `base_rope` : base des fréquences de RoPE (10 000, la valeur d'origine).

    Les champs se donnent par leur nom : `ConfigModele(dim=512, couches=8, tetes=8,
    longueur_contexte=2048)`.
    """

    taille_vocabulaire: int = 32768
    dim: int
    couches: int
    tetes: int
    longueur_contexte: int
    base_rope: float = 10000.0

    def __post_init__(self) -> None:
        for nom in ("taille_vocabulaire", "dim", "couches", "tetes", "longueur_contexte"):
            if getattr(self, nom) < 1:
                raise ValueError(
                    f"`{nom}` vaut {getattr(self, nom)} : il doit être un entier d'au moins 1."
                )
        if self.dim % self.tetes != 0:
            raise ValueError(
                f"`dim` ({self.dim}) doit être divisible par `tetes` ({self.tetes}) : "
                "chaque tête reçoit une part égale. Choisis un `dim` multiple de "
                f"{self.tetes}, ou change `tetes`."
            )
        if (self.dim // self.tetes) % 2 != 0:
            raise ValueError(
                f"Chaque tête a {self.dim // self.tetes} dimensions, un nombre impair : "
                "RoPE tourne les valeurs par paire, il faut un nombre pair. "
                "Change `dim` ou `tetes`."
            )
        if self.base_rope <= 1:
            raise ValueError(f"`base_rope` doit être plus grand que 1 (vaut {self.base_rope}).")


def nombre_parametres(c: ConfigModele) -> int:
    """Nombre exact de paramètres du `Transformer` de configuration `c`.

    Le plongement d'entrée et la projection de sortie partagent la même matrice : elle n'est
    comptée qu'une fois. Les matrices de RoPE ne sont pas des paramètres (elles ne sont pas
    apprises), et il n'y a aucun biais.

    - plongement (et sortie, liée) : `taille_vocabulaire × dim` ;
    - par couche : attention `4 × dim²` (q, k, v et sortie), MLP `3 × dim × largeur_cachee`,
      et deux RMSNorm de `dim` poids chacune ;
    - une RMSNorm finale de `dim` poids.
    """
    h = largeur_cachee(c.dim)
    plongement = c.taille_vocabulaire * c.dim
    attention = 4 * c.dim * c.dim
    mlp = 3 * c.dim * h
    normes = 2 * c.dim
    return plongement + c.couches * (attention + mlp + normes) + c.dim


# Les cinq tailles prévues, de la plus petite (qui s'entraîne en quelques minutes pour
# vérifier que tout marche) à la plus grande.
PRESETS: dict[str, ConfigModele] = {
    "mini": ConfigModele(dim=384, couches=6, tetes=6, longueur_contexte=512),
    "petit": ConfigModele(dim=512, couches=8, tetes=8, longueur_contexte=2048),
    "moyen": ConfigModele(dim=768, couches=12, tetes=12, longueur_contexte=2048),
    "grand": ConfigModele(dim=1024, couches=16, tetes=16, longueur_contexte=2048),
    "tres_grand": ConfigModele(dim=1280, couches=20, tetes=20, longueur_contexte=2048),
}
