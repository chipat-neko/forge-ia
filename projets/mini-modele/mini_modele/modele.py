"""Le mini-transformer : une couche d'attention causale et un MLP, qui lit des prénoms.

Le modèle lit un prénom numéro par numéro, et à chaque position il donne un
score à chaque numéro du vocabulaire : plus le score est haut, plus il croit
que ce numéro vient ensuite. Ses pièces sont celles des grands modèles, en
tout petit :

- un plongement par numéro, et un par position (des positions apprises) ;
- une attention causale à plusieurs têtes : chaque position ne regarde que
  les positions d'avant et elle-même ;
- un MLP (élargir, ReLU, revenir) ;
- une norme RMS sans poids avant l'attention, avant le MLP et avant la
  sortie, et des connexions résiduelles ;
- une tête de lecture séparée du plongement d'entrée.

Tous les paramètres vivent dans un seul tableau à plat (voir disposition).
La passe arrière est écrite à la main, dans l'ordre inverse exact de la passe
avant ; tests/test_modele.py la compare à la pente mesurée sur la perte.

Le jumeau TypeScript est site/src/lib/mini-modele/modele.ts : il suit ce
fichier ligne à ligne. Ce fichier est vérifié par tests/test_sources.py.
"""

from collections.abc import MutableSequence, Sequence
from dataclasses import dataclass

from mini_modele.attention import melanger_valeurs, poids_attention, softmax
from mini_modele.calcul import Hasard, exp, log, maximum, produit_scalaire, racine, somme

ECART_TYPE_INIT = 0.08  # l'écart-type des paramètres au départ
EPSILON_NORME = 1e-5  # ajouté sous la racine de la norme : jamais de division par 0
LONGUEUR_GENEREE_MAX = 15  # un prénom inventé s'arrête à 15 caractères, comme les prénoms de la liste

# Une place dans le tableau des paramètres : (début, lignes, colonnes), rangée ligne par ligne.
Place = tuple[int, int, int]


@dataclass(frozen=True)
class ConfigMini:
    """La forme du mini-modèle. Seule la taille du vocabulaire change d'une liste de mots à l'autre."""

    taille_vocabulaire: int
    dim: int = 16
    tetes: int = 4
    contexte: int = 16
    largeur_mlp: int = 64

    def __post_init__(self) -> None:
        for nom in ("taille_vocabulaire", "dim", "tetes", "contexte", "largeur_mlp"):
            valeur = getattr(self, nom)
            if isinstance(valeur, bool) or not isinstance(valeur, int) or valeur < 1:
                raise ValueError(f"ConfigMini : {nom} doit être un entier positif (reçu {valeur!r}).")
        if self.dim % self.tetes != 0:
            raise ValueError(
                f"ConfigMini : dim ({self.dim}) doit être un multiple de tetes ({self.tetes}), pour couper "
                "chaque vecteur en têtes de même taille. Change dim ou tetes (par exemple dim=16 et tetes=4)."
            )


def taille_tete(c: ConfigMini) -> int:
    """Le nombre de composantes de chaque tête : dim / tetes (4 avec les valeurs par défaut)."""
    return c.dim // c.tetes


def disposition(c: ConfigMini) -> dict[str, Place]:
    """La place de chaque matrice dans le tableau des paramètres, dans l'ordre du tableau.

    La case (i, j) d'une matrice rangée à (début, lignes, colonnes) est params[début + i × colonnes + j].
    """
    formes = [
        ("plongement", c.taille_vocabulaire, c.dim),
        ("positions", c.contexte, c.dim),
        ("requetes", c.dim, c.dim),
        ("cles", c.dim, c.dim),
        ("valeurs", c.dim, c.dim),
        ("sortie_attention", c.dim, c.dim),
        ("mlp_haut", c.dim, c.largeur_mlp),
        ("mlp_bas", c.largeur_mlp, c.dim),
        ("tete_de_lecture", c.dim, c.taille_vocabulaire),
    ]
    places = {}
    debut = 0
    for nom, lignes, colonnes in formes:
        places[nom] = (debut, lignes, colonnes)
        debut += lignes * colonnes
    return places


def nombre_parametres(c: ConfigMini) -> int:
    """V·d + T·d + 4d² + 2·d·m + d·V : 32·V + 3 328 avec les valeurs par défaut."""
    v, d, t, m = c.taille_vocabulaire, c.dim, c.contexte, c.largeur_mlp
    return v * d + t * d + 4 * d * d + 2 * d * m + d * v


def initialiser(c: ConfigMini, hasard: Hasard) -> list[float]:
    """Les paramètres de départ : une gaussienne d'écart-type ECART_TYPE_INIT pour chacun, dans l'ordre."""
    return [hasard.gaussienne(ECART_TYPE_INIT) for _ in range(nombre_parametres(c))]


def produit(x: Sequence[float], params: Sequence[float], place: Place) -> list[float]:
    """x · W, pour la matrice W rangée à place : y[j] = Σ_i x[i] × W[i][j], sommé par i croissant."""
    debut, lignes, colonnes = place
    y = [0.0] * colonnes
    for i in range(lignes):
        xi = x[i]
        base = debut + i * colonnes
        for j in range(colonnes):
            y[j] += xi * params[base + j]
    return y


def norme(x: Sequence[float]) -> tuple[list[float], float]:
    """La norme RMS, sans poids : y_i = x_i × inv, avec inv = 1 / √(moyenne des x_i² + EPSILON_NORME).

    Renvoie y, et inv pour la passe arrière.
    """
    inv = 1.0 / racine(somme([v * v for v in x]) / len(x) + EPSILON_NORME)
    return [v * inv for v in x], inv


def relu(u: float) -> float:
    """u s'il est positif, 0 sinon."""
    return u if u > 0.0 else 0.0


@dataclass(frozen=True)
class Position:
    """Ce que la passe avant a calculé à une position : la perte lit logits, la passe arrière relit le reste."""

    h0: list[float]
    a: list[float]
    inv_a: float
    q: list[float]
    k: list[float]
    v: list[float]
    poids: list[list[float]]  # poids[tête][j] : le poids donné à la position j, pour j de 0 à t
    o: list[float]
    h1: list[float]
    b: list[float]
    inv_b: float
    u: list[float]
    r: list[float]
    h2: list[float]
    f: list[float]
    inv_f: float
    logits: list[float]


def verifier_numeros(c: ConfigMini, ids: Sequence[int]) -> None:
    """Chaque numéro est un entier du vocabulaire, de 0 à V − 1."""
    for numero in ids:
        if isinstance(numero, bool) or not isinstance(numero, int) or not 0 <= numero < c.taille_vocabulaire:
            raise ValueError(
                f"Numéro hors du vocabulaire : {numero!r} (il y a {c.taille_vocabulaire} caractères, "
                f"numérotés de 0 à {c.taille_vocabulaire - 1})."
            )


def verifier_contexte(c: ConfigMini, nb_positions: int) -> None:
    """Le modèle ne lit pas plus de positions que son contexte."""
    if nb_positions > c.contexte:
        raise ValueError(
            f"{nb_positions} positions à lire, mais le contexte n'en a que {c.contexte} : "
            "raccourcis la séquence, ou agrandis contexte dans ConfigMini."
        )


def verifier_entree(c: ConfigMini, params: Sequence[float], ids: Sequence[int]) -> None:
    """Le bon nombre de paramètres, et des numéros que la passe avant sait lire."""
    if len(params) != nombre_parametres(c):
        raise ValueError(
            f"avant : {len(params)} paramètres, mais cette configuration en a {nombre_parametres(c)}. "
            "Crée-les avec initialiser(c, hasard)."
        )
    if len(ids) == 0:
        raise ValueError("avant : il faut au moins un numéro à lire (le bord, 0, pour commencer).")
    verifier_contexte(c, len(ids))
    verifier_numeros(c, ids)


# region: avant
def avant(c: ConfigMini, params: Sequence[float], ids: Sequence[int]) -> list[Position]:
    """La passe avant, position par position : du numéro lu en t aux scores du numéro suivant."""
    verifier_entree(c, params, ids)
    places = disposition(c)
    tt = taille_tete(c)
    echelle = 1.0 / racine(float(tt))
    passe = []
    cles = []
    valeurs = []
    for t in range(len(ids)):
        # 1. Le vecteur de départ : le plongement du numéro lu, plus celui de la position.
        lu = places["plongement"][0] + ids[t] * c.dim
        ici = places["positions"][0] + t * c.dim
        h0 = [params[lu + i] + params[ici + i] for i in range(c.dim)]
        # 2. Normer, puis la requête, la clé et la valeur de cette position.
        a, inv_a = norme(h0)
        q = produit(a, params, places["requetes"])
        k = produit(a, params, places["cles"])
        v = produit(a, params, places["valeurs"])
        cles.append(k)
        valeurs.append(v)
        # 3. Chaque tête regarde les positions 0 à t, jamais les suivantes : c'est le masque causal.
        poids = []
        o = []
        for h in range(c.tetes):
            de, jusqu_a = h * tt, (h + 1) * tt
            p = poids_attention(q[de:jusqu_a], [cles[j][de:jusqu_a] for j in range(t + 1)], echelle)
            o.extend(melanger_valeurs(p, [valeurs[j][de:jusqu_a] for j in range(t + 1)]))
            poids.append(p)
        # 4. Ajouter ce que l'attention a trouvé (connexion résiduelle).
        z = produit(o, params, places["sortie_attention"])
        h1 = [h0[i] + z[i] for i in range(c.dim)]
        # 5. Le MLP : normer, élargir, ReLU, revenir à dim, ajouter.
        b, inv_b = norme(h1)
        u = produit(b, params, places["mlp_haut"])
        r = [relu(x) for x in u]
        z = produit(r, params, places["mlp_bas"])
        h2 = [h1[i] + z[i] for i in range(c.dim)]
        # 6. Normer, puis un score par numéro du vocabulaire.
        f, inv_f = norme(h2)
        logits = produit(f, params, places["tete_de_lecture"])
        passe.append(Position(h0=h0, a=a, inv_a=inv_a, q=q, k=k, v=v, poids=poids, o=o, h1=h1, b=b,
                              inv_b=inv_b, u=u, r=r, h2=h2, f=f, inv_f=inv_f, logits=logits))
    return passe
# fin: avant


# region: perte
def entropie_croisee(logits: Sequence[float], cible: int) -> float:
    """L'erreur à une position : −ln de la probabilité que le modèle donne au bon numéro.

    Avec m le plus grand score : −ln(e^(l_cible) / Σ e^(l_i)) = ln Σ e^(l_i − m) − (l_cible − m).
    Retirer m ne change pas le résultat, et exp ne déborde jamais.
    """
    m = maximum(logits)
    e = [exp(l - m) for l in logits]
    return log(somme(e)) - (logits[cible] - m)
# fin: perte


def produit_arriere(
    x: Sequence[float],
    dy: Sequence[float],
    params: Sequence[float],
    gradient: MutableSequence[float],
    place: Place,
) -> list[float]:
    """La dérivée de y = x · W, pour W rangée à place.

    Ajoute x[i] × dy[j] à la case (i, j) de W dans gradient, et renvoie
    dx[i] = Σ_j W[i][j] × dy[j], sommé par j croissant.
    """
    debut, lignes, colonnes = place
    dx = []
    for i in range(lignes):
        xi = x[i]
        base = debut + i * colonnes
        s = 0.0
        for j in range(colonnes):
            gradient[base + j] += xi * dy[j]
            s += params[base + j] * dy[j]
        dx.append(s)
    return dx


def norme_arriere(y: Sequence[float], inv: float, dy: Sequence[float]) -> list[float]:
    """La dérivée de la norme : dx_i = inv × (dy_i − y_i × (dy · y) / dim), avec y et inv de la passe avant."""
    moyenne = produit_scalaire(dy, y) / len(y)
    return [inv * (dy[i] - y[i] * moyenne) for i in range(len(y))]


def arriere(
    c: ConfigMini,
    params: Sequence[float],
    ids: Sequence[int],
    cibles: Sequence[int],
    passe: list[Position],
    nombre: int,
    gradient: MutableSequence[float],
) -> None:
    """La passe arrière d'une séquence : la passe avant à l'envers, de la dernière position à la première.

    Ajoute à gradient les dérivées de la perte moyenne (nombre : les positions prédites de tout le lot).
    Une clé et une valeur servent à leur position et à toutes les suivantes : quand on arrive à la
    position t, en descendant, dk[t] et dv[t] ont reçu tout ce qui leur revient.
    """
    places = disposition(c)
    tt = taille_tete(c)
    echelle = 1.0 / racine(float(tt))
    n = len(ids)
    dk = [[0.0] * c.dim for _ in range(n)]
    dv = [[0.0] * c.dim for _ in range(n)]
    for t in range(n - 1, -1, -1):
        ici = passe[t]
        # 7. La perte : softmax des scores, moins 1 sur la cible, divisé par le nombre de positions.
        probas = softmax(ici.logits)
        dlogits = []
        for i in range(len(probas)):
            g = probas[i]
            if i == cibles[t]:
                g = g - 1.0
            dlogits.append(g / nombre)
        # 6. logits = f · tete_de_lecture, avec f = norme(h2).
        df = produit_arriere(ici.f, dlogits, params, gradient, places["tete_de_lecture"])
        dh2 = norme_arriere(ici.f, ici.inv_f, df)
        # 5. h2 = h1 + relu(u) · mlp_bas, avec u = b · mlp_haut et b = norme(h1).
        dr = produit_arriere(ici.r, dh2, params, gradient, places["mlp_bas"])
        du = [dr[i] if ici.u[i] > 0.0 else 0.0 for i in range(c.largeur_mlp)]
        db = produit_arriere(ici.b, du, params, gradient, places["mlp_haut"])
        dnb = norme_arriere(ici.b, ici.inv_b, db)
        dh1 = [dh2[i] + dnb[i] for i in range(c.dim)]
        # 4. h1 = h0 + o · sortie_attention.
        do_tetes = produit_arriere(ici.o, dh1, params, gradient, places["sortie_attention"])
        # 3. Les têtes, de la dernière à la première.
        dq = [0.0] * c.dim
        for h in range(c.tetes - 1, -1, -1):
            de, jusqu_a = h * tt, (h + 1) * tt
            p = ici.poids[h]
            # Le mélange : o_h = Σ_j p[j] × v_h(j).
            dp = []
            for j in range(t + 1):
                dp.append(produit_scalaire(do_tetes[de:jusqu_a], passe[j].v[de:jusqu_a]))
                for x in range(de, jusqu_a):
                    dv[j][x] += p[j] * do_tetes[x]
            # Le softmax : la dérivée du score j est p[j] × (dp[j] − Σ_l p[l] × dp[l]).
            moyenne = produit_scalaire(p, dp)
            # Les scores : score_j = (q · k_j) × échelle.
            for j in range(t + 1):
                ds = p[j] * (dp[j] - moyenne) * echelle
                for x in range(de, jusqu_a):
                    dq[x] += ds * passe[j].k[x]
                    dk[j][x] += ds * ici.q[x]
        # 2. q, k, v = a · requetes, a · cles, a · valeurs, avec a = norme(h0).
        da_q = produit_arriere(ici.a, dq, params, gradient, places["requetes"])
        da_k = produit_arriere(ici.a, dk[t], params, gradient, places["cles"])
        da_v = produit_arriere(ici.a, dv[t], params, gradient, places["valeurs"])
        da = [da_q[i] + da_k[i] + da_v[i] for i in range(c.dim)]
        dna = norme_arriere(ici.a, ici.inv_a, da)
        dh0 = [dh1[i] + dna[i] for i in range(c.dim)]
        # 1. h0 = plongement[ids[t]] + positions[t].
        lu = places["plongement"][0] + ids[t] * c.dim
        position = places["positions"][0] + t * c.dim
        for i in range(c.dim):
            gradient[lu + i] += dh0[i]
            gradient[position + i] += dh0[i]


def perte_et_gradient(
    c: ConfigMini,
    params: Sequence[float],
    sequences: Sequence[Sequence[int]],
    gradient: MutableSequence[float] | None = None,
) -> float:
    """La perte moyenne du lot et, si gradient est donné, sa dérivée par rapport à chaque paramètre.

    Une séquence vaut (0, …, 0) : on lit seq[:-1] et on prédit seq[1:]. La
    perte est la moyenne de l'entropie croisée sur toutes les positions
    prédites de toutes les séquences. Le gradient (de même longueur que
    params) est remis à 0,0, puis rempli séquence par séquence. Toutes les
    vérifications passent avant : une entrée refusée laisse le gradient intact.
    """
    if len(params) != nombre_parametres(c):
        raise ValueError(
            f"perte_et_gradient : {len(params)} paramètres, mais cette configuration en a {nombre_parametres(c)}. "
            "Crée-les avec initialiser(c, hasard)."
        )
    if gradient is not None and len(gradient) != nombre_parametres(c):
        raise ValueError(
            f"perte_et_gradient : le gradient a {len(gradient)} cases, il en faut une par paramètre "
            f"({nombre_parametres(c)})."
        )
    nombre = 0
    for seq in sequences:
        if len(seq) < 2:
            raise ValueError(
                f"perte_et_gradient : chaque séquence a au moins deux numéros, le bord puis ce qu'on prédit "
                f"(reçu une séquence de {len(seq)} numéro)."
            )
        verifier_contexte(c, len(seq) - 1)
        verifier_numeros(c, seq)
        nombre += len(seq) - 1
    if nombre == 0:
        raise ValueError("perte_et_gradient : aucune séquence. Donne au moins une séquence de deux numéros ou plus.")
    if gradient is not None:
        for i in range(len(gradient)):
            gradient[i] = 0.0
    pertes = []
    for seq in sequences:
        ids = seq[:-1]
        cibles = seq[1:]
        passe = avant(c, params, ids)
        for t in range(len(ids)):
            pertes.append(entropie_croisee(passe[t].logits, cibles[t]))
        if gradient is not None:
            arriere(c, params, ids, cibles, passe, nombre, gradient)
    return somme(pertes) / nombre


def perte(c: ConfigMini, params: Sequence[float], sequences: Sequence[Sequence[int]]) -> float:
    """La perte moyenne du lot, sans gradient."""
    return perte_et_gradient(c, params, sequences)


def logits_suivants(c: ConfigMini, params: Sequence[float], ids: Sequence[int]) -> list[float]:
    """Les scores du numéro qui suit ids : ceux de la dernière position de la passe avant."""
    return avant(c, params, ids)[-1].logits


def tirer_numero(logits: Sequence[float], hasard: Hasard) -> int:
    """Tire un numéro selon les scores : le numéro i a la chance e_i = exp(logits[i] − m), m le plus grand score.

    seuil = uniforme × somme des chances. On cumule les chances par numéro
    croissant, et on prend le premier numéro où le seuil passe sous le cumul
    (le dernier, si l'arrondi l'en empêche).
    """
    m = maximum(logits)
    e = [exp(l - m) for l in logits]
    seuil = hasard.uniforme() * somme(e)
    cumul = 0.0
    for i in range(len(e)):
        cumul += e[i]
        if seuil < cumul:
            return i
    return len(e) - 1


def generer(c: ConfigMini, params: Sequence[float], hasard: Hasard, nb: int) -> list[tuple[int, ...]]:
    """nb prénoms inventés, sans les bords.

    On part du bord (0,), puis on refait la passe avant et on tire un numéro,
    caractère après caractère. Le tirage d'un 0 arrête le prénom, comme
    LONGUEUR_GENEREE_MAX caractères écrits (ou un contexte plein, s'il est plus court).
    """
    limite = LONGUEUR_GENEREE_MAX
    if c.contexte < limite:
        limite = c.contexte
    prenoms = []
    for _ in range(nb):
        ids = [0]
        while len(ids) - 1 < limite:
            numero = tirer_numero(logits_suivants(c, params, ids), hasard)
            if numero == 0:
                break
            ids.append(numero)
        prenoms.append(tuple(ids[1:]))
    return prenoms
