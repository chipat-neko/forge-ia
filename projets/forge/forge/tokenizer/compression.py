"""Mesurer la compression d'un tokenizer : combien d'octets de texte tient un jeton.

La mesure se fait sur des textes téléchargés par `python -m forge donnees`, source par source,
puis pour le mélange (sous-commande `compression`). Elle sert surtout à vérifier, sur des textes
de validation que le tokenizer n'a jamais lus à l'apprentissage, qu'il compresse aussi bien
qu'à l'apprentissage. Les chiffres du tokenizer figé sont dans `docs/mesures/tokenizer-ton-ia-v1.md`.

Deux façons de compter le total :

- le **mélange** pèse les sources par leurs parts (`MELANGE_PAR_DEFAUT`, en octets) : c'est ce que
  verra l'entraînement ;
- **bout à bout** met les textes mesurés les uns après les autres, chaque source pour ce qu'elle a
  donné (à peu près autant d'octets chacune).
"""

from pathlib import Path

from forge.donnees.melange import MELANGE_PAR_DEFAUT, est_validation
from forge.donnees.nettoyage import empreinte_du_texte_nettoye
from forge.tokenizer.apprentissage import lire_fragments, verifier_dossier
from forge.tokenizer.bpe_octets import TokenizerOctets

PARTIES = ("validation", "apprentissage")


def _separer_les_milliers(nombre: int) -> str:
    return f"{nombre:,}".replace(",", " ")


def _virgule(nombre: float) -> str:
    return f"{nombre:.2f}".replace(".", ",")


def mesurer_compression(
    tokenizer: TokenizerOctets,
    dossier: Path,
    octets_par_source: int,
    partie: str = "validation",
) -> dict:
    """Mesure les octets par jeton de `tokenizer` sur les textes de `dossier`, source par source.

    `dossier` est le dossier des textes (`FORGE_DONNEES/textes/<nom>`, chaque source avec son
    `.complet`). Pour chaque source, on lit les documents de `partie` (« validation » : ceux que
    `est_validation` met de côté, ou « apprentissage » : tous les autres) entiers, dans l'ordre
    des fragments, jusqu'à avoir au moins `octets_par_source` octets. Si une source en a moins,
    la mesure échoue : on ne rend jamais un chiffre sur moins de texte que demandé.

    Le résultat contient `sources` (par source : `documents`, `octets`, `caracteres`, `jetons`,
    `octets_par_jeton`, `caracteres_par_jeton`), `melange` et `bout_a_bout`, plus `partie`,
    `octets_par_source` et le nom du `tokenizer`. Les jetons sont ceux de `encoder`, sans le
    jeton `<|fin_texte|>` de chaque document.
    """
    if partie not in PARTIES:
        raise ValueError(
            f"Partie inconnue : {partie!r}. Écris « validation » (les documents mis de côté) ou "
            "« apprentissage » (tous les autres)."
        )
    if octets_par_source <= 0:
        raise ValueError(f"Le volume à mesurer par source doit être positif, pas {octets_par_source}.")
    dossier = Path(dossier)
    verifier_dossier(dossier)
    en_validation = partie == "validation"
    sources: dict[str, dict] = {}
    for source in MELANGE_PAR_DEFAUT:
        documents = octets = caracteres = jetons = 0
        for texte in lire_fragments(dossier / source):
            # Les textes téléchargés sont déjà nettoyés : leur empreinte est celle du texte tel quel.
            if est_validation(empreinte_du_texte_nettoye(texte)) != en_validation:
                continue
            documents += 1
            octets += len(texte.encode("utf-8"))
            caracteres += len(texte)
            jetons += len(tokenizer.encoder(texte))
            if octets >= octets_par_source:
                break
        if octets < octets_par_source:
            suite = (
                "Télécharge plus de texte, par exemple avec : python -m forge donnees --parts "
                "web_fr=400M,wikipedia_fr=350M,code_python=300M --dossier validation-tokenizer "
                "(0,5 % des documents vont à la validation : il en faut environ 200 fois plus que "
                "le volume voulu), ou demande moins avec --octets."
                if en_validation
                else "Télécharge plus de texte avec python -m forge donnees, ou demande moins avec --octets."
            )
            raise ValueError(
                f"La source « {source} » de {dossier} ne contient que {octets} octets de documents de "
                f"{partie}, moins que les {octets_par_source} demandés. {suite}"
            )
        sources[source] = {
            "documents": documents,
            "octets": octets,
            "caracteres": caracteres,
            "jetons": jetons,
            "octets_par_jeton": octets / jetons,
            "caracteres_par_jeton": caracteres / jetons,
        }
    # Le mélange : jetons par octet = somme, sur les sources, de la part × jetons par octet.
    jetons_par_octet = sum(
        part * sources[source]["jetons"] / sources[source]["octets"] for source, part in MELANGE_PAR_DEFAUT.items()
    )
    total_octets = sum(mesure["octets"] for mesure in sources.values())
    total_jetons = sum(mesure["jetons"] for mesure in sources.values())
    return {
        "tokenizer": tokenizer.nom,
        "partie": partie,
        "octets_par_source": octets_par_source,
        "sources": sources,
        "melange": {"octets_par_jeton": 1 / jetons_par_octet},
        "bout_a_bout": {
            "documents": sum(mesure["documents"] for mesure in sources.values()),
            "octets": total_octets,
            "jetons": total_jetons,
            "octets_par_jeton": total_octets / total_jetons,
        },
    }


def tableau_de_compression(resultat: dict) -> str:
    """Écrit le résultat de `mesurer_compression` en tableau lisible (virgule décimale)."""
    sources = resultat["sources"]
    ligne = "{:<14} {:>10} {:>12} {:>10} {:>13} {:>17}"
    de_la_partie = "de validation" if resultat["partie"] == "validation" else "d'apprentissage"
    lignes = [
        f"Compression de « {resultat['tokenizer']} » sur des documents {de_la_partie} "
        f"(au moins {_separer_les_milliers(resultat['octets_par_source'])} octets par source) :",
        ligne.format("Source", "Documents", "Octets", "Jetons", "Octets/jeton", "Caractères/jeton"),
    ]
    for source, mesure in sources.items():
        lignes.append(
            ligne.format(
                source,
                _separer_les_milliers(mesure["documents"]),
                _separer_les_milliers(mesure["octets"]),
                _separer_les_milliers(mesure["jetons"]),
                _virgule(mesure["octets_par_jeton"]),
                _virgule(mesure["caracteres_par_jeton"]),
            )
        )
    parts = " / ".join(f"{part * 100:.0f} %" for part in MELANGE_PAR_DEFAUT.values())
    bout = resultat["bout_a_bout"]
    lignes.append(f"Mélange {parts} : {_virgule(resultat['melange']['octets_par_jeton'])} octets par jeton.")
    lignes.append(
        f"Les trois bout à bout : {_virgule(bout['octets_par_jeton'])} octets par jeton "
        f"({_separer_les_milliers(bout['octets'])} octets, {_separer_les_milliers(bout['jetons'])} jetons, "
        f"{_separer_les_milliers(bout['documents'])} documents)."
    )
    return "\n".join(lignes)
