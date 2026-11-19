"""Valeurs de référence pour les jumeaux TypeScript et pour le chapitre 1.8.

Le site refait deux calculs en TypeScript : la note d'une réponse sans la justesse (`site/src/lib/partie-1/notes.ts`,
qui traduit `forge.evaluation.langue` et `forge.evaluation.consignes`) et la perte DPO d'une paire
(`site/src/lib/partie-1/dpo.ts`, qui traduit `perte_dpo_a_la_main`). Ce fichier produit `tests/attendus.json`,
trois sections :

- `consignes` : les huit consignes de forge avec les réglages de référence (le texte de chaque consigne et ses
  kwargs) ; c'est une entrée, que le site relit ;
- `textes` : quarante textes de référence, des phrases ordinaires et les pièges de l'atelier (accent combinant,
  apostrophe courbe, espace fine insécable, espace insécable, emoji, lettre hors du premier plan d'Unicode,
  espaces que Python et JavaScript ne comptent pas pareil, texte vide, 10 000 caractères, seulement des chiffres).
  Pour chacun : le nombre de `mots`, la `langue`, le verdict de chacune des huit consignes (`verdicts`) et de la
  `longueur` (de 3 à 300 mots), puis la `note` sans la justesse (`terminee`, `consignes`, `francais`, `longueur`)
  d'une invite qui porte quelques consignes (`invite`), avec les verdicts de forge ;
- `grille_dpo` : `perte_dpo_a_la_main` et sa dérivée sur une grille de 27 points (β, écart de la choisie, écart
  de la rejetée). Ce sont les seuls flottants du fichier : `Math.exp` et `Math.log1p` ne s'accordent pas d'un
  moteur à l'autre au dernier chiffre, le site les compare à 10⁻¹² près (`dpo.test.ts`) et la page de parité les
  laisse de côté (`CLES_NON_REFAITES`).

Hors la grille, tout est entier, booléen ou texte : les deux langages le retrouvent à l'identique.

Pour régénérer le fichier (dans projets/1.8-alignement) :

    uv run --extra cpu python -m alignement_pas_a_pas.attendus
"""

import json
from pathlib import Path

from forge.evaluation.consignes import CONTRAINTES
from forge.evaluation.langue import langue, mots
from forge.preferences.invites import InvitePreference
from forge.preferences.noter import MOTS_MAXIMUM, MOTS_MINIMUM

from alignement_pas_a_pas.noter import expliquer_note
from alignement_pas_a_pas.perte_dpo import derivee_a_la_main, perte_dpo_a_la_main

PROJET = Path(__file__).resolve().parent.parent
CHEMIN_ATTENDUS = PROJET / "tests" / "attendus.json"

# Les caractères invisibles ou ambigus, par leur numéro : ni le code ni les tests ne les écrivent en clair.
FINE = chr(0x202F)  # l'espace fine insécable
INSECABLE = chr(0x00A0)  # l'espace insécable
COMBINANT = chr(0x0301)  # l'accent aigu combinant
NEL = chr(0x0085)  # « next line » : blanc pour Python (isspace, strip), pas pour JavaScript
SEPARATEUR_DE_FICHIER = chr(0x001C)  # idem
BOM = chr(0xFEFF)  # blanc pour JavaScript (trim), pas pour Python
MONGOL = chr(0x180E)  # ni l'un ni l'autre ne le compte comme un blanc
SEPARATEUR_DE_LIGNE = chr(0x2028)  # blanc pour les deux
LETTRE_HORS_DU_PREMIER_PLAN = chr(0x1D49C)  # « 𝒜 », une majuscule (catégorie Lu) hors du premier plan d'Unicode
SMILEY = chr(0x1F600)
DRAPEAU = chr(0x1F1EB) + chr(0x1F1F7)
POUCE = chr(0x1F44D)
VIRGULE_PLEINE_LARGEUR = chr(0xFF0C)
I_TURC_POINTE = chr(0x0130)

# Les huit consignes de forge, avec des réglages de référence.
PHRASE_DE_FIN = "C'est tout pour aujourd'hui."
CONSIGNES: tuple[tuple[str, dict], ...] = (
    ("mots_max", {"n": 20}),
    ("phrases_max", {"n": 2}),
    ("minuscules", {}),
    ("sans_virgule", {}),
    ("mot_obligatoire", {"mot": "paris"}),
    ("puces", {"n": 3}),
    ("fin_imposee", {"phrase": PHRASE_DE_FIN}),
    ("titre", {}),
)

TEXTES: tuple[tuple[str, str], ...] = (
    ("vide", ""),
    ("blancs", "   \n\t  "),
    ("chiffres-seuls", "2026 12 31 1234567890"),
    ("francais", "La capitale de la France est Paris."),
    ("francais-virgules", "Paris, la capitale, est très belle."),
    ("anglais", "The capital of France is Paris and it is beautiful."),
    ("francais-avec-un-mot-anglais", "Le mot the est anglais, mais la phrase est en français, et elle est longue."),
    ("trop-court-pour-la-langue", "Oui, Paris."),
    ("minuscules", "paris est la capitale de la france."),
    ("puces", "- Paris\n- Lyon\n- Marseille"),
    ("puces-dont-une-vide", "- Paris\n- \n- Lyon"),
    ("puces-fins-de-ligne-windows", "- Paris\r\n- Lyon\r\n- Marseille"),
    ("titre-chevrons", "« La capitale »\nParis est la capitale de la France."),
    ("titre-chevrons-ascii", "<<Capitale>>\nParis est la capitale."),
    ("titre-vide", "«  »\nParis."),
    ("fin-imposee", "Paris est belle.\n" + PHRASE_DE_FIN),
    ("fin-imposee-espace-insecable", "Paris est belle.\n" + PHRASE_DE_FIN + INSECABLE),
    ("fin-imposee-espace-fine", "Paris est belle.\n" + PHRASE_DE_FIN + FINE),
    ("fin-imposee-next-line", "Paris est belle.\n" + PHRASE_DE_FIN + NEL),
    ("fin-imposee-separateur-de-fichier", "Paris est belle.\n" + PHRASE_DE_FIN + SEPARATEUR_DE_FICHIER),
    ("fin-imposee-bom", "Paris est belle.\n" + PHRASE_DE_FIN + BOM),
    ("fin-imposee-mongol", "Paris est belle.\n" + PHRASE_DE_FIN + MONGOL),
    ("fin-imposee-apostrophe-courbe", "Paris est belle.\nC’est tout pour aujourd’hui."),
    ("accent-combinant", "Cafe" + COMBINANT + " est un mot du français, et il a un accent combinant : Paris."),
    ("apostrophes-courbes", "L’eau d’Évian n’est pas l’eau de Paris."),
    ("emoji", f"Bonjour {SMILEY} Paris {DRAPEAU} est la capitale de la France {POUCE}."),
    ("emoji-colle-au-mot", f"Paris{SMILEY} est belle, et {SMILEY}paris aussi."),
    ("lettre-hors-du-premier-plan", f"{LETTRE_HORS_DU_PREMIER_PLAN}paris est un mot de la France."),
    ("chiffre-et-tiret-bas-colles", "paris2 et 2paris et paris_ et _paris."),
    ("mot-entier-parmi-d-autres", "Le paris, le Paris, les Parisiens."),
    ("i-turc-pointe", I_TURC_POINTE + "stanbul est une ville de la Turquie, et elle est grande."),
    ("sigma-final", "Le mot grec ΟΔΟΣ ou οδός est dans la langue des Grecs."),
    ("virgule-pleine-largeur", f"Paris{VIRGULE_PLEINE_LARGEUR} Lyon et Marseille."),
    ("abreviations", "M. Dupont est arrivé. Il est 10 h. Dr. Martin aussi!"),
    ("liste-numerotee", "1. Paris est belle. 2. Lyon aussi."),
    ("blancs-de-python-seulement", "Paris est belle." + NEL + "Lyon aussi." + SEPARATEUR_DE_FICHIER + "Nice enfin."),
    ("deux-mots", "Oui non"),
    ("trois-cents-mots", " ".join(["mot"] * 300)),
)
# Les deux derniers : 301 mots, 10 000 caractères.
TEXTES += (
    ("trois-cent-un-mots", " ".join(["mot"] * 301)),
    ("dix-mille-caracteres", ("Le chat dort dans la maison, et il rêve de Paris. " * 200)[:10000]),
)


def invite_du_texte(rang: int) -> list[tuple[str, dict]]:
    """Les consignes de l'invite du texte de rang `rang` : aucune, une ou deux, en tournant sur les huit."""
    if rang % 5 == 0:
        return []
    premiere = CONSIGNES[rang % len(CONSIGNES)]
    if rang % 3 == 0:
        return [premiere]
    return [premiere, CONSIGNES[(rang * 3 + 1) % len(CONSIGNES)]]


def terminee_du_texte(rang: int) -> bool:
    """Une réponse sur quatre est coupée par la limite de jetons."""
    return rang % 4 != 3


# Une grille de 27 points : trois β, trois écarts de la choisie, trois écarts de la rejetée (|z| reste sous 20 :
# au-delà, le softplus de PyTorch rend z tel quel, et ne ressemble plus à la formule).
BETAS = (0.05, 0.1, 0.5)
ECARTS_DE_LA_CHOISIE = (-3.5, 0.25, 8.0)
ECARTS_DE_LA_REJETEE = (-6.0, 0.0, 4.5)


def calculer_attendus() -> dict:
    par_id = {c.id: c for c in CONTRAINTES}
    textes = []
    for rang, (nom, texte) in enumerate(TEXTES):
        invite = invite_du_texte(rang)
        terminee = terminee_du_texte(rang)
        explication = expliquer_note(texte, terminee, InvitePreference(f"reference-{rang}", (), tuple(invite), None))
        note = {cle: valeur for cle, valeur in explication["note"].items() if cle != "juste"}
        textes.append(
            {
                "nom": nom,
                "texte": texte,
                "terminee": terminee,
                "invite": [[identifiant, kwargs] for identifiant, kwargs in invite],
                "mots": len(mots(texte)),
                "langue": langue(texte),
                "verdicts": {identifiant: bool(par_id[identifiant].verifier(texte, kwargs)) for identifiant, kwargs in CONSIGNES},
                "longueur": MOTS_MINIMUM <= len(mots(texte)) <= MOTS_MAXIMUM,
                "note": note,
            }
        )
    grille = [
        {
            "beta": beta,
            "ecart_choisie": ecart_choisie,
            "ecart_rejetee": ecart_rejetee,
            "perte": perte_dpo_a_la_main(ecart_choisie, ecart_rejetee, 0.0, 0.0, beta),
            "derivee": derivee_a_la_main(beta, ecart_choisie, ecart_rejetee),
        }
        for beta in BETAS
        for ecart_choisie in ECARTS_DE_LA_CHOISIE
        for ecart_rejetee in ECARTS_DE_LA_REJETEE
    ]
    return {
        "consignes": [
            {"id": identifiant, "kwargs": kwargs, "consigne": par_id[identifiant].consigne(kwargs)} for identifiant, kwargs in CONSIGNES
        ],
        "textes": textes,
        "grille_dpo": grille,
    }


def vers_json(valeur: object) -> str:
    return json.dumps(valeur, ensure_ascii=False, allow_nan=False, indent=1)


def main() -> None:
    CHEMIN_ATTENDUS.write_text(vers_json(calculer_attendus()) + "\n", encoding="utf-8", newline="\n")
    print(f"Attendus écrits dans {CHEMIN_ATTENDUS}")


if __name__ == "__main__":
    main()
