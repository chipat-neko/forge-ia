"""Tests qui fixent le tokenizer définitif de « ton IA » (`ton-ia-v1`).

Ce tokenizer est figé pour tout le reste du parcours : un modèle entraîné avec lui ne comprend
plus rien si un seul identifiant change. Ces tests sonnent donc dès que le fichier, son motif,
ses jetons spéciaux ou la façon d'encoder bougent. Il a été appris sur 300 Mo (voir
`docs/mesures/tokenizer-ton-ia-v1.md`) ; ne le réapprends pas pour « l'améliorer ».
"""

import hashlib
import json
from pathlib import Path

import pytest

from forge.__main__ import construire_parseur
from forge.tokenizer import MOTIF_TON_IA, TokenizerOctets

RESSOURCE_TON_IA = Path(__file__).parent.parent / "forge" / "ressources" / "tokenizer-ton-ia-v1.json"
TOK = TokenizerOctets.charger(RESSOURCE_TON_IA)

# Empreinte SHA-256 du fichier, octet pour octet (fins de ligne `\n`, comme git les garde).
EMPREINTE_DU_FICHIER = "3001e7ab40630739c4dec807c7a92c0d4fb469cc0fc4afa368704395391f21ba"

SPECIAUX_ATTENDUS = [
    "<|debut_texte|>",
    "<|fin_texte|>",
    "<|bourrage|>",
    "<|systeme|>",
    "<|utilisateur|>",
    "<|assistant|>",
    "<|fin_tour|>",
    "<|appel_outil|>",
    "<|fin_appel_outil|>",
    "<|resultat_outil|>",
    "<|fin_resultat_outil|>",
    "<|pensee|>",
    "<|fin_pensee|>",
    "<|image|>",
    "<|fin_image|>",
    "<|trou_prefixe|>",
    "<|trou_suffixe|>",
    "<|trou_milieu|>",
] + [f"<|reserve_{numero:02d}|>" for numero in range(46)]

MOTIF_ATTENDU = (
    r"[^\r\n\p{L}\p{N}]?\p{L}+(?:['’](?=\p{L}))?|\p{N}{1,3}| ?[^\p{White_Space}\p{L}\p{N}]+[\r\n]*"
    r"|\p{White_Space}*[\r\n]+|\p{White_Space}+(?!\P{White_Space})|\p{White_Space}+"
)

PHRASE = "Le forgeron frappe le métal sur l’enclume."
FONCTION = "def fusionner(mots, paire):\n    return mots\n"


def test_taille_et_speciaux():
    assert len(TOK.fusions) == 32448 and TOK.id_special("<|fin_texte|>") == 32705
    assert TOK.id_special("<|reserve_45|>") == 32767


def test_les_64_speciaux_sont_a_leur_place():
    assert len(SPECIAUX_ATTENDUS) == 64
    assert TOK.nom == "ton-ia-v1" and TOK.taille_vocabulaire == 32768 and TOK.premier_special == 32704
    assert list(TOK.speciaux) == SPECIAUX_ATTENDUS
    assert list(TOK.speciaux.values()) == list(range(32704, 32768))
    # Le fichier lui-même dit la même chose, sans passer par le code.
    contenu = json.loads(RESSOURCE_TON_IA.read_text(encoding="utf-8"))
    assert contenu["speciaux"] == {nom: 32704 + place for place, nom in enumerate(SPECIAUX_ATTENDUS)}
    assert contenu["motif"] == MOTIF_ATTENDU == MOTIF_TON_IA
    assert contenu["version"] == 1 and contenu["nom"] == "ton-ia-v1" and contenu["taille_vocabulaire"] == 32768


def test_compression_francais_et_code():
    assert len(PHRASE.encode()) / len(TOK.encoder(PHRASE)) > 3.0
    assert len(TOK.encoder(FONCTION)) < 20


def test_le_fichier_est_fige_octet_pour_octet():
    octets = RESSOURCE_TON_IA.read_bytes()
    assert b"\r" not in octets, "le fichier du tokenizer doit garder des fins de ligne \\n"
    assert octets.endswith(b"\n")
    assert hashlib.sha256(octets).hexdigest() == EMPREINTE_DU_FICHIER, (
        "Le fichier du tokenizer de ton IA a changé. Il est figé : récupère-le depuis git "
        "(git checkout -- projets/forge/forge/ressources/tokenizer-ton-ia-v1.json)."
    )


def test_premieres_et_dernieres_fusions():
    # Les premières fusions : deux espaces, « ␣d », « es », « é », « ␣l », « on ».
    assert TOK.fusions[:6] == [(32, 32), (32, 100), (101, 115), (195, 169), (32, 108), (111, 110)]
    assert [TOK.octets_du_jeton(256 + rang) for rang in range(6)] == [b"  ", b" d", b"es", "é".encode(), b" l", b"on"]
    # La dernière fusion donne le jeton 32 703, juste avant le premier jeton spécial.
    assert TOK.fusions[-1] == (5462, 1592) and TOK.octets_du_jeton(32703) == b" tarification"


def test_jetons_exacts_de_quelques_textes():
    ids = TOK.encoder(PHRASE)
    assert ids == [661, 28902, 261, 12585, 297, 8218, 384, 368, 262, 2753, 323, 46]
    assert [TOK.octets_du_jeton(i).decode() for i in ids] == [
        "Le", " forger", "on", " frappe", " le", " métal", " sur", " l’", "en", "clu", "me", ".",
    ]
    # Les élisions restent collées au mot qui les porte : « l’ », « n’ », « d’ », « j’ ».
    elisions = "L’enclume n’est pas l’outil d’aujourd’hui : j’y forge l’acier !"
    ids = TOK.encoder(elisions)
    assert ids == [
        1906, 262, 2753, 323, 741, 320, 395, 368, 7299, 392, 13806, 1324, 431, 1703, 121, 568, 471, 368, 19174, 677,
    ]
    assert [TOK.octets_du_jeton(i).decode() for i in ids][:5] == ["L’", "en", "clu", "me", " n’"]
    assert TOK.encoder(FONCTION) == [1276, 6502, 15718, 3722, 2917, 44, 13496, 560, 304, 835, 3404, 10]
    plus_long = "def fusionner(mots, paire):\n    resultat = []\n    for mot in mots:\n        resultat.append(mot)\n    return resultat\n"
    assert TOK.encoder(plus_long) == [
        1276, 6502, 15718, 3722, 2917, 44, 13496, 560, 304, 3516, 327, 401, 4367, 304, 568, 1765, 351, 3404, 406, 355,
        3516, 327, 2810, 3722, 421, 377, 304, 835, 3516, 327, 10,
    ]


@pytest.mark.parametrize(
    ("texte", "attendu"),
    [
        # Chiffres, date et groupes de milliers : les nombres se coupent par 3 chiffres au plus, l'espace
        # des milliers est un jeton à part, et le symbole « € » prend l'espace qui le précède.
        ("2026-11-03 : 1 000 000 €", [4631, 54, 45, 1525, 45, 4447, 431, 32, 49, 32, 1498, 32, 1498, 5177]),
        # Fin de ligne Windows : le retour chariot et le saut de ligne restent deux jetons distincts.
        ("Ligne\r\nDeux", [76, 1050, 13, 10, 8286]),
        # Espace insécable (U+00A0, un jeton à lui seul) et espace fine insécable (U+202F, trois octets
        # qui ne fusionnent pas : deux jetons) : le texte typographié français reste exact, mais coûte.
        ("10 % ; 3 000 km", [899, 12287, 37, 767, 32, 51, 290, 175, 1498, 12287, 13030]),
        # Un émoji n'a aucune fusion : ses quatre octets font quatre jetons.
        ("Bravo 🙂 !", [26611, 2200, 32, 240, 159, 153, 130, 677]),
        # Une élision isolée, puis des élisions en début de phrase, avec ’ et ' : seule l'apostrophe
        # suivie d'une lettre s'attache au mot qui précède.
        ("l’", [108, 296]),
        ("n’importe quoi, qu’il l'a dit", [23979, 5076, 2719, 44, 662, 298, 341, 97, 1406]),
    ],
)
def test_encodages_exacts_de_cas_limites(texte, attendu):
    ids = TOK.encoder(texte)
    assert ids == attendu
    assert TOK.decoder(ids) == texte


def test_espace_fine_insecable_est_coupee_en_octets():
    assert [TOK.octets_du_jeton(i) for i in TOK.encoder("3 000")] == [b"3", b"\xe2\x80", b"\xaf", b"000"]


@pytest.mark.parametrize(
    "texte",
    [
        PHRASE,
        FONCTION,
        "",
        "Ligne un\r\nLigne deux\r\n\r\nLigne trois",
        "Des émojis : 🙂👍🏽 et du chinois : 你好，世界 ; de l’arabe : مرحبا",
        "\tune tabulation,\t\tdeux\t\t\t\net des espaces      en fin de ligne   \n",
        "x" * 100_000 + "\n" + "é" * 50_000,
        "123456789 0,5 % ; 3,14159 ; 1 000 000",
    ],
)
def test_aller_retour_exact(texte):
    ids = TOK.encoder(texte)
    assert TOK.decoder(ids) == texte
    assert all(0 <= i < 32704 for i in ids)


def test_une_chaine_qui_ressemble_a_un_special_n_en_est_pas_un():
    texte = "Voici <|fin_texte|> puis <|assistant|> et <|reserve_45|> dans du texte."
    ids = TOK.encoder(texte)
    assert not any(i >= 32704 for i in ids)
    assert TOK.decoder(ids) == texte
    # Pour un vrai jeton spécial, on passe par son identifiant.
    assert TOK.decoder([TOK.id_special("<|fin_texte|>")]) == "<|fin_texte|>"


def test_evaluer_utilise_ce_tokenizer_par_defaut():
    choix = construire_parseur().parse_args(["evaluer", "--sauvegarde", "x", "--donnees", "y"])
    assert Path(choix.tokenizer).resolve() == RESSOURCE_TON_IA.resolve() and Path(choix.tokenizer).is_file()
