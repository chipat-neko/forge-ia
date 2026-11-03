"""La liste des prénoms : l'extraction depuis le fichier de l'Insee, et le fichier versionné.

`extraire` est testée sur de petites lignes écrites à la main. `main` est
testée sans réseau : l'adresse est celle d'un zip fabriqué ici (`file:///…`),
au même format que le vrai fichier de l'Insee (séparateur « ; », colonnes en
minuscules, colonne `rang` en plus, fins de ligne Windows).
"""

import hashlib
import io
import itertools
import pathlib
import unicodedata
import zipfile

import pytest

from mini_modele.calcul import empreinte_texte
from mini_modele.donnees import charger_prenoms
from mini_modele.prenoms import (
    CARACTERES_PERMIS,
    LONGUEUR_MAX,
    LONGUEUR_MIN,
    MINIMUM_PRENOMS,
    SEUIL_NAISSANCES,
    SEUIL_REPLI,
    URL,
    choisir_prenoms,
    extraire,
    lire_lignes,
    lire_zip,
    main,
    telecharger,
)

RACINE = pathlib.Path(__file__).resolve().parent.parent


def ligne(sexe: str, prenom: str, periode: str, valeur: str) -> dict[str, str]:
    return {"SEXE": sexe, "PRENOM": prenom, "PERIODE": periode, "VALEUR": valeur}


def test_extraire_cumule_filtre_et_trie():
    l = lambda s, p, a, v: {"SEXE": s, "PRENOM": p, "PERIODE": a, "VALEUR": v}
    lignes = [l("1", "ÉLODIE", "1990", "300"), l("2", "ÉLODIE", "1991", "250"),
              l("1", "_PRENOMS_RARES", "1990", "9000"), l("1", "JEAN-PIERRE", "1950", "800"),
              l("1", "BJØRN", "1990", "900"), l("1", "MAXIMILIENNE-ROSE", "1990", "900"),
              l("1", "LÉA", "XXXX", "5000"), l("2", "ZOÉ", "2020", "495")]
    assert extraire(lignes) == ["jean-pierre", "élodie"]


def test_les_constantes_de_la_recette():
    assert URL == "https://www.insee.fr/fr/statistiques/fichier/8595130/prenoms-2025-nat_csv.zip"
    assert (SEUIL_NAISSANCES, SEUIL_REPLI, MINIMUM_PRENOMS) == (500, 200, 5000)
    assert (LONGUEUR_MIN, LONGUEUR_MAX) == (2, 15)
    assert CARACTERES_PERMIS == "-abcdefghijklmnopqrstuvwxyzàâäæçèéêëîïôöùûüÿœ"
    assert all(unicodedata.normalize("NFC", c) == c for c in CARACTERES_PERMIS)


def test_extraire_le_seuil_est_inclus_et_se_regle():
    lignes = [ligne("1", "ANA", "2000", "500"), ligne("1", "ABEL", "2000", "499"), ligne("1", "ALBA", "2000", "200")]
    assert extraire(lignes) == ["ana"]
    assert extraire(lignes, seuil=200) == ["abel", "alba", "ana"]
    assert extraire(lignes, 501) == []


def test_extraire_additionne_sur_les_annees_et_les_deux_sexes():
    lignes = [ligne("1", "CAMILLE", "1950", "200"), ligne("2", "CAMILLE", "1950", "200"),
              ligne("1", "CAMILLE", "2000", "100")]
    assert extraire(lignes) == ["camille"]
    assert extraire(lignes[:2]) == []  # 400 : pas assez


def test_extraire_normalise_en_nfc_et_en_minuscules():
    decompose = "ÉLODIE"  # E + accent aigu combinant
    assert decompose != unicodedata.normalize("NFC", decompose)
    lignes = [ligne("1", decompose, "1990", "300"), ligne("2", "ÉLODIE", "1991", "250"),
              ligne("1", "Élodie", "1992", "10")]
    resultat = extraire(lignes)
    # Les trois écritures sont le même prénom : 300 + 250 + 10, en un seul élément, en NFC.
    assert resultat == ["élodie"]
    assert resultat[0] == unicodedata.normalize("NFC", resultat[0])


def test_extraire_les_minuscules_accentuees_et_les_ligatures():
    lignes = [ligne("1", p, "2000", "900") for p in ("ŒDIPE", "ÆLIA", "NOËL", "JOSÉPHINE", "ÿVES", "CÉCILE")]
    # Par point de code : æ (U+00E6) avant ÿ (U+00FF), puis œ (U+0153).
    assert extraire(lignes) == ["cécile", "joséphine", "noël", "ælia", "ÿves", "œdipe"]


def test_extraire_la_longueur_de_2_a_15():
    quinze = "a" * 15
    lignes = [ligne("1", p, "2000", "900") for p in ("A", "AL", quinze, quinze + "b")]
    assert extraire(lignes) == [quinze, "al"]  # triés : « aaa… » passe avant « al »


def test_extraire_les_traits_d_union():
    prenoms = ("ANNE-MARIE", "-ANNE", "ANNE-", "ANNE--MARIE", "A-B")
    lignes = [ligne("1", p, "2000", "900") for p in prenoms]
    assert extraire(lignes) == ["a-b", "anne-marie"]


def test_extraire_refuse_les_caracteres_hors_de_la_liste():
    prenoms = ("M'HAMED", "MARIE ANNE", "ZOË2", "ÅSA", "BJØRN", "ÑANDU", "ÇA", "ANAÏS")
    lignes = [ligne("1", p, "2000", "900") for p in prenoms]
    assert extraire(lignes) == ["anaïs", "ça"]


def test_extraire_ne_compte_que_les_annees_a_quatre_chiffres():
    lignes = [ligne("1", "ANA", p, "900") for p in ("XXXX", "199", "19900", "1990-1995", "", "١٩٩٠")]
    assert extraire(lignes) == []
    assert extraire(lignes + [ligne("1", "ANA", "1900", "500")]) == ["ana"]


def test_extraire_ignore_les_prenoms_qui_commencent_par_un_tiret_bas():
    lignes = [ligne("1", "_PRENOMS_RARES", "1990", "9000"), ligne("1", "_AUTRE", "1990", "9000"),
              ligne("1", "ANA", "1990", "9000")]
    assert extraire(lignes) == ["ana"]


def test_extraire_une_valeur_qui_n_est_pas_un_entier_est_une_erreur():
    for valeur in ("", "12,5", "-3", "beaucoup", "٣"):
        with pytest.raises(ValueError, match="VALEUR"):
            extraire([ligne("1", "ANA", "2000", valeur)])
    # Les lignes ignorées ne sont pas lues : « XXXX » et « _ » passent même sans valeur.
    assert extraire([ligne("1", "ANA", "XXXX", ""), ligne("1", "_X", "2000", "")]) == []


def test_extraire_ne_garde_qu_un_exemplaire_et_trie_par_point_de_code():
    lignes = [ligne("1", p, "2000", "900") for p in ("ZOÉ", "ÉMILE", "AL", "ÉMILE", "al", "ZOE")]
    assert extraire(lignes) == ["al", "zoe", "zoé", "émile"]


def test_fichier_des_prenoms():
    # Les octets, pas read_text : read_text range « \r\n » en « \n » et cacherait le « \r ».
    texte = (RACINE / "donnees" / "prenoms.txt").read_bytes().decode("utf-8")
    assert "\r" not in texte and texte.endswith("\n")
    prenoms = charger_prenoms()
    assert 3_000 <= len(prenoms) <= 30_000 and prenoms == sorted(set(prenoms))
    assert all(2 <= len(p) <= 15 and set(p) <= set(CARACTERES_PERMIS) for p in prenoms)


def test_fichier_des_prenoms_respecte_toutes_les_regles():
    prenoms = charger_prenoms()
    assert all(unicodedata.normalize("NFC", p) == p for p in prenoms)
    assert all(not p.startswith("-") and not p.endswith("-") and "--" not in p for p in prenoms)
    # La liste est fermée par un seul « \n », sans ligne vide.
    texte = (RACINE / "donnees" / "prenoms.txt").read_bytes().decode("utf-8")
    assert texte == "\n".join(prenoms) + "\n"
    # Des prénoms connus, avec leurs accents et leurs traits d'union.
    for connu in ("léa", "zoé", "mathéo", "maël", "anaïs", "jean-pierre", "marie-claire", "françois", "noël"):
        assert connu in prenoms, connu
    assert "m'hamed" not in prenoms and "_prenoms_rares" not in prenoms


# ─── Lire le fichier de l'Insee ─────────────────────────────────────────────────

EN_TETE_INSEE = "sexe;prenom;periode;valeur;rang"


def test_lire_lignes_au_format_de_l_insee():
    flux = io.StringIO(f"{EN_TETE_INSEE}\r\n1;GABRIEL;2025;4625;1\r\n2;LÉA;2024;300;12\r\n\r\n", newline="")
    assert list(lire_lignes(flux)) == [
        {"SEXE": "1", "PRENOM": "GABRIEL", "PERIODE": "2025", "VALEUR": "4625"},
        {"SEXE": "2", "PRENOM": "LÉA", "PERIODE": "2024", "VALEUR": "300"},
    ]


def test_lire_lignes_accepte_les_colonnes_en_majuscules_et_dans_un_autre_ordre():
    flux = io.StringIO("VALEUR;PRENOM;SEXE;PERIODE\n12;ANA;2;1999\n")
    assert list(lire_lignes(flux)) == [{"SEXE": "2", "PRENOM": "ANA", "PERIODE": "1999", "VALEUR": "12"}]


@pytest.mark.parametrize("en_tete", [
    "sexe,prenom,periode,valeur",          # mauvais séparateur
    "sexe;prenom;annee;valeur;rang",       # une colonne a changé de nom
    "sexe;prenom;periode",                 # une colonne manque
    "",                                    # fichier vide
])
def test_lire_lignes_refuse_un_en_tete_inattendu(en_tete):
    with pytest.raises(ValueError, match="En-tête") as erreur:
        list(lire_lignes(io.StringIO(en_tete + "\n1;ANA;2000;900;1\n")))
    assert "SEXE, PRENOM, PERIODE et VALEUR" in str(erreur.value)


def test_lire_lignes_signale_une_ligne_trop_courte():
    with pytest.raises(ValueError, match="ligne 3"):
        list(lire_lignes(io.StringIO(f"{EN_TETE_INSEE}\n1;ANA;2000;900;1\n1;BEA;2000\n")))


def fabriquer_zip(dossier: pathlib.Path, texte_csv: str, nom_csv: str = "prenoms-2025-nat.csv") -> str:
    chemin = dossier / "prenoms-fabrique.zip"
    with zipfile.ZipFile(chemin, "w") as archive:
        archive.writestr(nom_csv, texte_csv.encode("utf-8"))
    return chemin.as_uri()


def csv_insee(prenoms_et_totaux: list[tuple[str, int]], en_tete: str = EN_TETE_INSEE) -> str:
    """Un fichier au format de l'Insee : chaque total est coupé en deux lignes (un sexe, puis l'autre)."""
    lignes = [en_tete]
    for rang, (prenom, total) in enumerate(prenoms_et_totaux, start=1):
        lignes.append(f"1;{prenom.upper()};2000;{total - 5};{rang}")
        lignes.append(f"2;{prenom.upper()};2001;5;{rang}")
    return "\r\n".join(lignes) + "\r\n"


def noms_fabriques(n: int) -> list[str]:
    """n noms distincts de trois lettres : aaa, aab, aac…"""
    trois = ("".join(lettres) for lettres in itertools.product("abcdefghijklmnopqrstuvwxyz", repeat=3))
    return list(itertools.islice(trois, n))


def test_lire_zip_lit_le_csv_de_l_archive(tmp_path):
    url = fabriquer_zip(tmp_path, "\ufeff" + csv_insee([("ana", 600)]))  # même avec une marque d'ordre
    lignes = list(lire_zip(tmp_path / "prenoms-fabrique.zip"))
    assert url.startswith("file:///")
    assert [(l["PRENOM"], l["VALEUR"]) for l in lignes] == [("ANA", "595"), ("ANA", "5")]


def test_lire_zip_veut_un_seul_csv(tmp_path):
    chemin = tmp_path / "deux.zip"
    with zipfile.ZipFile(chemin, "w") as archive:
        archive.writestr("a.csv", csv_insee([("ana", 600)]))
        archive.writestr("b.csv", csv_insee([("ana", 600)]))
    with pytest.raises(ValueError, match="un seul fichier CSV"):
        list(lire_zip(chemin))


def test_choisir_prenoms_garde_le_seuil_de_500_quand_il_y_en_a_assez(capsys):
    lignes = [ligne("1", nom.upper(), "2000", "600") for nom in noms_fabriques(MINIMUM_PRENOMS)]
    prenoms, seuil = choisir_prenoms(lambda: iter(lignes))
    assert (len(prenoms), seuil) == (MINIMUM_PRENOMS, 500)
    assert "seuil de 200" not in capsys.readouterr().out


def test_choisir_prenoms_recommence_avec_200_et_le_dit(capsys):
    noms = noms_fabriques(7000)
    lignes = [ligne("1", n.upper(), "2000", "600") for n in noms[:4000]]
    lignes += [ligne("1", n.upper(), "2000", "300") for n in noms[4000:]]
    prenoms, seuil = choisir_prenoms(lambda: iter(lignes))
    assert (len(prenoms), seuil) == (7000, 200)
    sortie = capsys.readouterr().out
    assert "seuil de 200" in sortie and "4000" in sortie


def test_choisir_prenoms_refuse_une_liste_trop_courte_meme_a_200():
    lignes = [ligne("1", n.upper(), "2000", "300") for n in noms_fabriques(4000)]
    with pytest.raises(ValueError, match="4000") as erreur:
        choisir_prenoms(lambda: iter(lignes))
    assert "200" in str(erreur.value)


# ─── Le script en entier, sans réseau ───────────────────────────────────────────


def lancer_main(tmp_path, noms_totaux: list[tuple[str, int]], en_tete: str = EN_TETE_INSEE):
    url = fabriquer_zip(tmp_path, csv_insee(noms_totaux, en_tete))
    sortie = tmp_path / "sortie" / "prenoms.txt"
    main(url=url, sortie=sortie)
    return sortie


def test_main_ecrit_la_liste_et_la_decrit(tmp_path, capsys):
    noms = noms_fabriques(MINIMUM_PRENOMS)
    sortie = lancer_main(tmp_path, [(n, 600) for n in noms] + [("rare", 100), ("bjørn", 900), ("é", 900)])
    octets = sortie.read_bytes()
    assert b"\r" not in octets and octets.endswith(b"\n")
    assert octets.decode("utf-8") == "\n".join(sorted(noms)) + "\n"
    texte = capsys.readouterr().out
    assert f"Nombre de prénoms : {MINIMUM_PRENOMS}" in texte
    assert "Caractères utilisés : abcdefghijklmnopqrstuvwxyz" in texte
    assert f"Empreinte du fichier : {empreinte_texte(octets.decode('utf-8'))}" in texte
    zip_octets = (tmp_path / "prenoms-fabrique.zip").read_bytes()
    assert hashlib.sha256(zip_octets).hexdigest() in texte


def test_main_avec_le_repli_de_200(tmp_path, capsys):
    noms = noms_fabriques(6000)
    sortie = lancer_main(tmp_path, [(n, 600) for n in noms[:3000]] + [(n, 250) for n in noms[3000:]])
    assert len(sortie.read_text(encoding="utf-8").split("\n")) - 1 == 6000
    texte = capsys.readouterr().out
    assert "seuil de 200" in texte and "Nombre de prénoms : 6000" in texte


def test_main_ne_touche_pas_au_fichier_quand_l_en_tete_a_change(tmp_path):
    sortie = tmp_path / "sortie" / "prenoms.txt"
    sortie.parent.mkdir()
    sortie.write_bytes(b"ancienne\nliste\n")
    url = fabriquer_zip(tmp_path, csv_insee([("ana", 600)], en_tete="sexe;prenom;annee;valeur;rang"))
    with pytest.raises(ValueError, match="En-tête"):
        main(url=url, sortie=sortie)
    assert sortie.read_bytes() == b"ancienne\nliste\n"


def test_telecharger_dit_quoi_faire_quand_le_reseau_manque(tmp_path):
    inexistant = (tmp_path / "nulle-part.zip").as_uri()
    with pytest.raises(ConnectionError, match="Télécharge") as erreur:
        telecharger(inexistant, tmp_path / "copie.zip")
    assert "8595130" in str(erreur.value)
    assert not (tmp_path / "copie.zip").exists()
