"""Le mini-transformer : disposition des paramètres, passe avant, perte, passe arrière, génération.

La passe arrière est écrite à la main : test_gradient_par_differences_finies
la compare, paramètre par paramètre, à la pente mesurée sur la perte. La parité
avec le TypeScript (site/src/lib/mini-modele/modele.ts) est vérifiée au bit
près par tests/attendus-modele.json (voir test_attendus.py et modele.test.ts).
"""

import dataclasses
import math

import pytest

from mini_modele.calcul import Hasard, log, somme, vers_hex
from mini_modele.donnees import donnees_par_defaut
from mini_modele.modele import (
    ECART_TYPE_INIT,
    EPSILON_NORME,
    LONGUEUR_GENEREE_MAX,
    ConfigMini,
    avant,
    disposition,
    entropie_croisee,
    generer,
    initialiser,
    logits_suivants,
    nombre_parametres,
    perte,
    perte_et_gradient,
    tirer_numero,
)

# Une configuration minuscule, pour vérifier la passe arrière sur chaque paramètre.
PETITE = ConfigMini(taille_vocabulaire=5, dim=4, tetes=2, contexte=4, largeur_mlp=8)
PETITES_SEQUENCES = [(0, 1, 2, 0), (0, 3, 0)]


def petits_params(graine: int = 3) -> list[float]:
    h = Hasard(graine)
    return [h.gaussienne(0.5) for _ in range(nombre_parametres(PETITE))]


def test_nombre_de_parametres():
    assert nombre_parametres(ConfigMini(taille_vocabulaire=27)) == 4192


def test_nombre_de_parametres_des_prenoms():
    # 32·V + 3 328 avec les valeurs par défaut ; V se lit dans le vocabulaire, jamais en dur.
    v = len(donnees_par_defaut().vocabulaire)
    assert nombre_parametres(ConfigMini(taille_vocabulaire=v)) == 32 * v + 3328
    assert nombre_parametres(PETITE) == 184


def test_les_constantes():
    assert ECART_TYPE_INIT == 0.08
    assert EPSILON_NORME == 1e-5
    assert LONGUEUR_GENEREE_MAX == 15
    c = ConfigMini(taille_vocabulaire=40)
    assert (c.dim, c.tetes, c.contexte, c.largeur_mlp) == (16, 4, 16, 64)
    assert dataclasses.asdict(c) == {"taille_vocabulaire": 40, "dim": 16, "tetes": 4, "contexte": 16, "largeur_mlp": 64}
    with pytest.raises(dataclasses.FrozenInstanceError):
        c.dim = 8  # type: ignore[misc]


def test_config_refuse_les_tetes_inegales():
    with pytest.raises(ValueError, match="multiple de tetes") as erreur:
        ConfigMini(taille_vocabulaire=40, dim=10, tetes=4)
    assert "Change dim ou tetes" in str(erreur.value)
    for mauvais in ({"dim": 0}, {"tetes": 0}, {"contexte": -1}, {"largeur_mlp": 2.0}, {"taille_vocabulaire": True}):
        with pytest.raises(ValueError, match="entier positif"):
            ConfigMini(**{"taille_vocabulaire": 40} | mauvais)


def test_disposition():
    c = ConfigMini(taille_vocabulaire=40)
    places = disposition(c)
    assert list(places) == [
        "plongement", "positions", "requetes", "cles", "valeurs",
        "sortie_attention", "mlp_haut", "mlp_bas", "tete_de_lecture",
    ]
    assert places["plongement"] == (0, 40, 16)
    assert places["positions"] == (640, 16, 16)
    assert places["requetes"] == (896, 16, 16)
    assert places["mlp_haut"] == (1920, 16, 64)
    assert places["mlp_bas"] == (2944, 64, 16)
    assert places["tete_de_lecture"] == (3968, 16, 40)
    # Les blocs se suivent sans trou ni chevauchement, et finissent au dernier paramètre.
    fin = 0
    for debut, lignes, colonnes in places.values():
        assert debut == fin
        fin = debut + lignes * colonnes
    assert fin == nombre_parametres(c)


def test_initialiser():
    c = ConfigMini(taille_vocabulaire=40)
    p = initialiser(c, Hasard(1234))
    assert len(p) == nombre_parametres(c) and all(isinstance(x, float) for x in p)
    h = Hasard(1234)
    assert [vers_hex(x) for x in p[:20]] == [vers_hex(h.gaussienne(0.08)) for _ in range(20)]
    assert initialiser(c, Hasard(1234)) == p and initialiser(c, Hasard(1235)) != p
    moyenne = somme(p) / len(p)
    ecart = math.sqrt(somme([(x - moyenne) * (x - moyenne) for x in p]) / len(p))
    assert abs(moyenne) < 0.005 and abs(ecart - 0.08) < 0.005


def test_gradient_par_differences_finies():
    c = PETITE
    h = Hasard(3); params = [h.gaussienne(0.5) for _ in range(nombre_parametres(c))]
    seqs = PETITES_SEQUENCES
    g = [0.0] * len(params); perte_et_gradient(c, params, seqs, g)
    for i in range(len(params)):
        plus = params.copy(); plus[i] += 1e-6
        moins = params.copy(); moins[i] -= 1e-6
        numerique = (perte(c, plus, seqs) - perte(c, moins, seqs)) / 2e-6
        assert abs(g[i] - numerique) <= 1e-5, i


def test_gradient_par_differences_finies_serre():
    # Plus serré que 1e-5 : un terme oublié ou faux (pas seulement un signe) se voit ici.
    # L'erreur d'arrondi de la différence centrée est d'environ 1e-16 × 1,6 / 1e-6, soit 2e-10.
    c = PETITE
    for graine, seqs in ((3, PETITES_SEQUENCES), (8, [(0, 4, 4, 1, 0), (0, 2, 0), (0, 1, 3, 0)])):
        params = petits_params(graine)
        g = [0.0] * len(params)
        perte_et_gradient(c, params, seqs, g)
        assert sum_abs(g) > 1.0  # pas un gradient presque nul, qui passerait sans rien prouver
        pire = 0.0
        for i in range(len(params)):
            plus = params.copy(); plus[i] += 1e-6
            moins = params.copy(); moins[i] -= 1e-6
            numerique = (perte(c, plus, seqs) - perte(c, moins, seqs)) / 2e-6
            ecart = abs(g[i] - numerique)
            assert ecart <= 1e-8 + 1e-6 * abs(numerique), (graine, i, g[i], numerique)
            if ecart > pire:
                pire = ecart
        assert pire < 1e-8


def sum_abs(valeurs: list[float]) -> float:
    s = 0.0
    for v in valeurs:
        s += abs(v)
    return s


def test_perte_de_depart_au_niveau_du_hasard():
    d = donnees_par_defaut(); c = ConfigMini(taille_vocabulaire=len(d.vocabulaire))
    p = initialiser(c, Hasard(1234))
    assert abs(perte(c, p, d.validation[:256]) - log(float(len(d.vocabulaire)))) < 0.15


def test_perte_est_la_somme_des_entropies_croisees_divisee_par_le_nombre():
    params = petits_params()
    pertes = []
    for seq in PETITES_SEQUENCES:
        passe = avant(PETITE, params, seq[:-1])
        for t in range(len(seq) - 1):
            pertes.append(entropie_croisee(passe[t].logits, seq[t + 1]))
    assert vers_hex(perte(PETITE, params, PETITES_SEQUENCES)) == vers_hex(somme(pertes) / 5)


def test_perte_est_la_moyenne_de_toutes_les_positions():
    params = petits_params()
    a, b = PETITES_SEQUENCES
    # (0, 1, 2, 0) prédit 3 caractères, (0, 3, 0) en prédit 2 : la moyenne pèse les positions, pas les séquences.
    attendu = (3 * perte(PETITE, params, [a]) + 2 * perte(PETITE, params, [b])) / 5
    assert perte(PETITE, params, [a, b]) == pytest.approx(attendu, rel=1e-14)
    assert perte(PETITE, params, [a, b]) == perte_et_gradient(PETITE, params, [a, b])


def test_perte_d_une_position_a_la_main():
    # Une seule position : la perte est −ln softmax(logits)[cible], avec les logits de la passe avant.
    params = petits_params()
    logits = avant(PETITE, params, (0,))[0].logits
    temoin = -math.log(math.exp(logits[2]) / math.fsum(math.exp(l) for l in logits))
    assert perte(PETITE, params, [(0, 2)]) == pytest.approx(temoin, rel=1e-14)


def test_le_gradient_est_remis_a_zero_et_ne_change_pas_la_perte():
    params = petits_params()
    g = [0.0] * len(params)
    perte_et_gradient(PETITE, params, PETITES_SEQUENCES, g)
    sale = [123.0] * len(params)
    valeur = perte_et_gradient(PETITE, params, PETITES_SEQUENCES, sale)
    assert [vers_hex(x) for x in sale] == [vers_hex(x) for x in g]
    assert vers_hex(valeur) == vers_hex(perte(PETITE, params, PETITES_SEQUENCES))
    # Les paramètres ne bougent pas.
    assert params == petits_params()


def test_une_entree_refusee_laisse_le_gradient_intact():
    # Toutes les vérifications passent avant la remise à zéro : une erreur ne vide pas le gradient de l'appelant.
    params = petits_params()
    for mauvais_params, sequences, message in (
        (params[:-1], PETITES_SEQUENCES, "paramètres"),
        (params + [0.0], PETITES_SEQUENCES, "paramètres"),
        (params, [(0, 1, 2, 3, 1, 0)], "contexte"),
        (params, [(0, 5, 0)], "Numéro hors du vocabulaire"),
        (params, [(0,)], "au moins deux numéros"),
        (params, [], "aucune séquence"),
    ):
        sale = [123.0] * len(params)
        with pytest.raises(ValueError, match=message):
            perte_et_gradient(PETITE, mauvais_params, sequences, sale)
        assert sale == [123.0] * len(params), message


def test_gradient_rempli_sequence_par_sequence():
    # Le gradient du lot est la somme des gradients des séquences, chacun divisé par le nombre de positions du lot.
    params = petits_params()
    a, b = PETITES_SEQUENCES
    ga, gb, gab = ([0.0] * len(params) for _ in range(3))
    perte_et_gradient(PETITE, params, [a], ga)
    perte_et_gradient(PETITE, params, [b], gb)
    perte_et_gradient(PETITE, params, [a, b], gab)
    for i in range(len(params)):
        assert gab[i] == pytest.approx((3 * ga[i] + 2 * gb[i]) / 5, rel=1e-12, abs=1e-13), i


def test_lignes_jamais_lues_sans_gradient():
    # Le numéro 4 n'apparaît pas dans les séquences, et la position 3 n'est jamais lue :
    # leurs lignes de plongement et de positions ont un gradient nul.
    params = petits_params()
    g = [0.0] * len(params)
    perte_et_gradient(PETITE, params, PETITES_SEQUENCES, g)
    places = disposition(PETITE)
    plongement, _, dim = places["plongement"]
    positions = places["positions"][0]
    assert g[plongement + 4 * dim:plongement + 5 * dim] == [0.0] * dim
    assert g[positions + 3 * dim:positions + 4 * dim] == [0.0] * dim
    assert all(x != 0.0 for x in g[plongement:plongement + dim])


def test_masque_causal():
    # Changer un caractère ne change rien aux positions d'avant : chacune ne voit que le passé.
    params = petits_params()
    p1 = avant(PETITE, params, (0, 1, 2, 3))
    p2 = avant(PETITE, params, (0, 1, 4, 1))
    for t in (0, 1):
        assert [vers_hex(x) for x in p1[t].logits] == [vers_hex(x) for x in p2[t].logits]
    assert p1[2].logits != p2[2].logits
    # Les poids d'une tête à la position t portent sur les positions 0 à t, et font 1.
    for t in range(4):
        for h in range(PETITE.tetes):
            assert len(p1[t].poids[h]) == t + 1
            assert abs(somme(p1[t].poids[h]) - 1.0) <= 1e-15


def test_logits_suivants():
    params = petits_params()
    ids = (0, 3, 1)
    assert logits_suivants(PETITE, params, ids) == avant(PETITE, params, ids)[-1].logits
    assert len(logits_suivants(PETITE, params, (0,))) == PETITE.taille_vocabulaire


def test_les_entrees_sont_verifiees():
    params = petits_params()
    with pytest.raises(ValueError, match="contexte"):
        perte(PETITE, params, [(0, 1, 2, 3, 1, 0)])  # 5 positions pour un contexte de 4
    with pytest.raises(ValueError, match="contexte"):
        logits_suivants(PETITE, params, (0, 1, 2, 3, 1))
    with pytest.raises(ValueError, match="Numéro hors du vocabulaire"):
        perte(PETITE, params, [(0, 5, 0)])
    with pytest.raises(ValueError, match="Numéro hors du vocabulaire"):
        perte(PETITE, params, [(0, -1, 0)])
    with pytest.raises(ValueError, match="au moins deux numéros"):
        perte(PETITE, params, [(0,)])
    with pytest.raises(ValueError, match="aucune séquence"):
        perte(PETITE, params, [])
    with pytest.raises(ValueError, match="paramètres"):
        perte(PETITE, params[:-1], PETITES_SEQUENCES)
    with pytest.raises(ValueError, match="gradient"):
        perte_et_gradient(PETITE, params, PETITES_SEQUENCES, [0.0] * 3)
    with pytest.raises(ValueError, match="au moins un numéro"):
        logits_suivants(PETITE, params, ())


def test_tirer_numero():
    # Le premier indice où le seuil passe sous le cumul : avec des scores égaux, exp donne 1 partout,
    # et le seuil vaut uniforme × 4.
    h = Hasard(5)
    u = Hasard(5).uniforme()
    attendu = math.floor(u * 4)
    assert tirer_numero([0.0, 0.0, 0.0, 0.0], h) == attendu
    # Un score très en dessous des autres n'est jamais tiré.
    h = Hasard(6)
    assert all(tirer_numero([0.0, -1000.0, 0.0], h) != 1 for _ in range(200))
    # Un seul score très au-dessus des autres est toujours tiré.
    h = Hasard(7)
    assert all(tirer_numero([-50.0, 50.0, -50.0], h) == 1 for _ in range(50))


def test_tirer_numero_garde_le_dernier_si_le_seuil_ne_passe_jamais():
    class SeuilMaximal:
        def uniforme(self) -> float:
            return 1.0  # plus que tout uniforme possible : le cumul n'atteint jamais le seuil
    assert tirer_numero([0.0, 0.0, 0.0], SeuilMaximal()) == 2


def test_generer():
    d = donnees_par_defaut()
    c = ConfigMini(taille_vocabulaire=len(d.vocabulaire))
    params = initialiser(c, Hasard(1234))
    prenoms = generer(c, params, Hasard(1236), 8)
    assert len(prenoms) == 8 and all(isinstance(p, tuple) for p in prenoms)
    assert all(0 not in p and len(p) <= 15 for p in prenoms)
    assert all(1 <= n < len(d.vocabulaire) for p in prenoms for n in p)
    assert generer(c, params, Hasard(1236), 8) == prenoms
    assert generer(c, params, Hasard(1237), 8) != prenoms
    assert generer(c, params, Hasard(1236), 0) == []


def test_generer_s_arrete_a_15_caracteres_ou_au_contexte():
    # Des paramètres nuls donnent des scores tous égaux : on tire au hasard parmi les V numéros,
    # et certains prénoms vont jusqu'à la limite.
    c = ConfigMini(taille_vocabulaire=40)
    longueurs = [len(p) for p in generer(c, [0.0] * nombre_parametres(c), Hasard(2), 20)]
    assert 15 in longueurs and all(n <= 15 for n in longueurs)
    # Un contexte de 4 ne laisse lire que 4 numéros : 4 caractères au plus.
    longueurs = [len(p) for p in generer(PETITE, [0.0] * nombre_parametres(PETITE), Hasard(2), 60)]
    assert 4 in longueurs and all(n <= 4 for n in longueurs)


def test_generer_refait_la_passe_avant_et_tire_chaque_caractere():
    # La génération refaite à la main : logits_suivants, puis tirer_numero, avec le même hasard.
    params = petits_params()
    h = Hasard(9)
    attendu = []
    for _ in range(5):
        ids = [0]
        while len(ids) - 1 < 4:
            n = tirer_numero(logits_suivants(PETITE, params, ids), h)
            if n == 0:
                break
            ids.append(n)
        attendu.append(tuple(ids[1:]))
    assert generer(PETITE, params, Hasard(9), 5) == attendu
