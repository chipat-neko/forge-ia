"""Les attendus partagés avec le site sont à jour.

Le fichier tests/attendus.json est écrit par `uv run --extra cpu python -m conversation_pas_a_pas.attendus`. Les
jumeaux TypeScript (site/src/lib/partie-1/conversation.ts et bfd.ts) sont comparés à ce fichier, sans tolérance :
rien n'y est flottant, tout est entier, booléen ou texte.
"""

import json

from forge.conversation.format import Tour, encoder_conversation
from forge.tokenizer import SPECIAUX, TokenizerOctets

from conversation_pas_a_pas.attendus import (
    CAPACITES,
    CHEMIN_ATTENDUS,
    CHEMIN_LONGUEURS,
    CONVERSATIONS,
    calculer_attendus,
    listes_de_longueurs,
    vers_json,
)
from conversation_pas_a_pas.gabarit import TOKENIZER

TOK = TokenizerOctets.charger(TOKENIZER)


def attendus() -> dict:
    return json.loads(CHEMIN_ATTENDUS.read_text(encoding="utf-8"))


def test_attendus_a_jour():
    assert CHEMIN_ATTENDUS.read_bytes().decode("utf-8") == vers_json(calculer_attendus()) + "\n", (
        "tests/attendus.json n'est plus à jour. Régénère-le\u202f: uv run --extra cpu python -m conversation_pas_a_pas.attendus"
    )


def test_le_fichier_est_ecrit_comme_les_autres_attendus():
    octets = CHEMIN_ATTENDUS.read_bytes()
    assert b"\r" not in octets and octets.endswith(b"}\n")
    assert json.dumps(json.loads(octets), ensure_ascii=False, allow_nan=False, indent=1) + "\n" == octets.decode("utf-8")


def test_les_trois_sections():
    assert list(attendus()) == ["speciaux", "conversations", "empaquetages"]


def test_les_jetons_speciaux_de_ton_ia_et_leurs_ids():
    speciaux = attendus()["speciaux"]
    assert len(speciaux) == 64 and [nom for nom, _ in speciaux] == list(SPECIAUX)
    assert [i for _, i in speciaux] == list(range(TOK.premier_special, TOK.premier_special + 64))
    assert dict(speciaux)["<|assistant|>"] == TOK.id_special("<|assistant|>")


def test_les_six_conversations_de_reference():
    cas = attendus()["conversations"]
    assert [c["nom"] for c in cas] == ["avec-systeme", "sans-systeme", "deux-tours", "faux-special", "pensee", "reponse-vide"]
    assert [nom for nom, _ in CONVERSATIONS] == [c["nom"] for c in cas]
    assert [c["tours"][0]["role"] for c in cas] == ["systeme", "utilisateur", "utilisateur", "utilisateur", "utilisateur", "utilisateur"]
    # Les ids de chaque texte sont ceux du tokenizer, et les ids assemblés ceux de forge.
    for c in cas[:5]:
        tours = [Tour(t["role"], t["texte"], t.get("pensee")) for t in c["tours"]]
        for t in c["tours"]:
            assert t["ids"] == TOK.encoder(t["texte"])
            assert ("pensee_ids" in t) == ("pensee" in t)
        exemple = encoder_conversation(TOK, tours)
        assert (c["ids"], c["appris"], c["erreur"]) == (exemple.ids, exemple.appris, None)
        assert all(isinstance(a, bool) for a in c["appris"])


def test_la_reponse_vide_est_refusee_avec_le_message_de_forge():
    vide = attendus()["conversations"][-1]
    assert (vide["ids"], vide["appris"]) == (None, None)
    assert vide["erreur"] == "Le texte du tour 2 (assistant) est vide. Écris un texte ou retire ce tour."
    assert vide["tours"][-1]["ids"] == []


def test_le_faux_jeton_special_est_encode_comme_du_texte():
    faux = attendus()["conversations"][3]
    assert faux["ids"].count(TOK.id_special("<|fin_tour|>")) == 2  # un par tour : ceux du texte ne comptent pas
    assert faux["ids"].count(TOK.id_special("<|assistant|>")) == 1
    assert all(i < TOK.premier_special for t in faux["tours"] for i in t["ids"])


def test_la_pensee_est_apprise():
    pensee = attendus()["conversations"][4]
    ids = pensee["ids"]
    debut = ids.index(TOK.id_special("<|pensee|>"))
    assert ids[debut - 1] == TOK.id_special("<|assistant|>") and not pensee["appris"][debut - 1]
    assert pensee["appris"][debut] and pensee["appris"][ids.index(TOK.id_special("<|fin_pensee|>"))]


def test_cinq_listes_de_longueurs_pour_quatre_capacites():
    cas = attendus()["empaquetages"]
    assert len(cas) == 5 * len(CAPACITES) == 20
    assert [c["liste"] for c in cas[::4]] == [nom for nom, _ in listes_de_longueurs()]
    assert [c["capacite"] for c in cas[:4]] == CAPACITES
    assert any(c["longueurs"] == [] for c in cas)  # une liste vide, un cas limite


def test_chaque_placement_range_les_exemples_sans_depasser_la_capacite():
    for c in attendus()["empaquetages"]:
        longueurs, capacite = c["longueurs"], c["capacite"]
        places = [rang for rangee in c["rangees"] for rang in rangee]
        garde = [rang for rang, n in enumerate(longueurs) if 0 < n <= capacite]
        assert sorted(places) == garde, (c["liste"], capacite)  # chacun est placé une fois, sauf les écartés
        assert c["ecartes"] == len(longueurs) - len(garde)
        for rangee in c["rangees"]:
            assert sum(longueurs[rang] for rang in rangee) <= capacite


def test_les_bords_de_capacite_sont_dans_la_liste():
    bords = next(c for c in attendus()["empaquetages"] if c["liste"] == "bords" and c["capacite"] == 129)
    assert 0 in bords["longueurs"] and 129 in bords["longueurs"] and 130 in bords["longueurs"]
    assert bords["ecartes"] == 6  # 0 (aucun jeton appris), 130, 512, 513, 2048 et 2049 ne tiennent pas dans 129


def test_la_liste_reelle_vient_du_fichier_des_longueurs_quand_il_existe():
    reelle = attendus()["empaquetages"][-1]["liste"]
    assert reelle == ("longueurs-sft-1.7" if CHEMIN_LONGUEURS.is_file() else "longueurs-de-remplacement")
