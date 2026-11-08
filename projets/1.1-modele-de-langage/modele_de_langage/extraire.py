"""Extraire la prose des chapitres du site : le texte sur lequel le modèle apprend.

Les chapitres sont écrits en MDX : du texte, mêlé de code (imports, calculs en
JavaScript, composants, extraits de programmes). Pour que le modèle de langage
apprenne le français du site, et non son code, on ne garde que la prose :

- le frontmatter (l'en-tête entre deux lignes « --- ») ;
- les lignes `import` et `export`, avec leurs blocs `export const … = (() => { … })();` ;
- les blocs de code (entre deux lignes « ``` ») ;
- les balises JSX (ouvrantes, fermantes, auto-fermantes, sur une ou plusieurs
  lignes) et les expressions `{…}` sont retirées ; le texte entre les balises reste ;
- les marques Markdown : les `**` du gras, les `#` des titres, et les liens
  `[texte](adresse)`, qui deviennent `texte` ;
- les accents graves du code en ligne : son contenu reste tel quel, accolades
  comprises (le code en ligne est lu avant les `{…}`, pour ne pas y laisser de trou).

Restent les puces « - » des listes. `&#8239;` devient l'espace fine insécable (U+202F), et les paragraphes sont séparés
par une ligne vide. Pour refaire le fichier du projet (dans projets/1.1-modele-de-langage) :

    uv run python -m modele_de_langage extraire --commit ae8d9a4 --sortie donnees/texte-du-site.txt
"""

import re
import subprocess
from pathlib import Path

# Les chapitres lus, dans cet ordre (chemins depuis la racine du dépôt).
CHAPITRES = tuple(f"site/src/content/chapitres/{nom}.mdx" for nom in ("0-1", "0-2", "0-3", "0-4", "0-5", "1-3"))

# Où commence une instruction JavaScript de tête de fichier MDX.
DEBUT_IMPORT = re.compile(r"""import\s+(\{|\*|[\w$]+\s+from\b|['"])""")
DEBUT_EXPORT = re.compile(r"export\s+(const|let|var|function|default|\{)")
# La dernière ligne d'un bloc : à gauche de la page, et finie par « ; » ou par une fermeture seule.
FIN_DE_BLOC = re.compile(r"[})\]]+;?")


def retirer_frontmatter(mdx: str) -> str:
    """Retire l'en-tête entre deux lignes « --- », s'il commence le texte."""
    if not mdx.startswith("---\n"):
        return mdx
    fin = mdx.find("\n---\n", 3)
    return mdx if fin == -1 else mdx[fin + len("\n---\n") :]


def retirer_blocs_de_code(lignes: list[str]) -> list[str]:
    """Retire les blocs entre deux lignes « ``` » (les lignes de clôture comprises)."""
    reste, dans_un_bloc = [], False
    for ligne in lignes:
        if ligne.lstrip().startswith("```"):
            dans_un_bloc = not dans_un_bloc
        elif not dans_un_bloc:
            reste.append(ligne)
    return reste


def retirer_imports_et_exports(lignes: list[str]) -> list[str]:
    """Retire les instructions `import` et `export` de tête de ligne, même sur plusieurs lignes.

    Une instruction finit à la première ligne qui se termine par « ; », ou, pour
    un bloc, à la première ligne collée à gauche qui se termine par « ; » ou
    qui ne contient qu'une fermeture : `})();`, `} from '…';`, `};`.
    """
    reste, i = [], 0
    while i < len(lignes):
        ligne = lignes[i]
        if DEBUT_IMPORT.match(ligne) or DEBUT_EXPORT.match(ligne):
            # La première ligne seule suffit si elle se termine par « ; ».
            if not ligne.rstrip().endswith(";"):
                while i + 1 < len(lignes):
                    i += 1
                    suite = lignes[i]
                    if not suite.startswith((" ", "\t")) and (
                        suite.rstrip().endswith(";") or FIN_DE_BLOC.fullmatch(suite.rstrip())
                    ):
                        break
        else:
            reste.append(ligne)
        i += 1
    return reste


def fin_de_l_expression(texte: str, debut: int) -> int | None:
    """L'index qui suit l'accolade fermante de l'expression `{…}` ouverte en `texte[debut]`.

    Les textes entre guillemets, les gabarits (avec leurs `${…}`) et les
    commentaires sont lus tels quels : une accolade ou une apostrophe qui s'y
    trouve ne compte pas. Rend None si l'expression ne se ferme jamais.
    """
    profondeur, i = 0, debut
    while i < len(texte):
        c = texte[i]
        if c == "{":
            profondeur += 1
        elif c == "}":
            profondeur -= 1
            if profondeur == 0:
                return i + 1
        elif c in "'\"":
            i = _fin_du_texte(texte, i)
            if i is None:
                return None
            continue
        elif c == "`":
            i = _fin_du_gabarit(texte, i)
            if i is None:
                return None
            continue
        elif texte.startswith("//", i):
            fin = texte.find("\n", i)
            i = len(texte) if fin == -1 else fin
            continue
        elif texte.startswith("/*", i):
            fin = texte.find("*/", i + 2)
            if fin == -1:
                return None
            i = fin + 2
            continue
        i += 1
    return None


def _fin_du_texte(texte: str, debut: int) -> int | None:
    """L'index qui suit le texte entre guillemets ouvert en `texte[debut]` (les `\\` protègent)."""
    guillemet, i = texte[debut], debut + 1
    while i < len(texte):
        if texte[i] == "\\":
            i += 2
        elif texte[i] == guillemet:
            return i + 1
        else:
            i += 1
    return None


def _fin_du_gabarit(texte: str, debut: int) -> int | None:
    """L'index qui suit le gabarit `…` ouvert en `texte[debut]`, `${…}` compris."""
    i = debut + 1
    while i < len(texte):
        if texte[i] == "\\":
            i += 2
        elif texte[i] == "`":
            return i + 1
        elif texte.startswith("${", i):
            i = fin_de_l_expression(texte, i + 1)
            if i is None:
                return None
        else:
            i += 1
    return None


def fin_de_la_balise(texte: str, debut: int) -> int | None:
    """L'index qui suit la balise JSX ouverte en `texte[debut]` (un « < »), ou None si ce n'en est pas une."""
    suivant = texte[debut + 1 : debut + 2]
    if not (suivant.isalpha() or suivant in ("/", ">")):
        return None
    i = debut + 1
    while i < len(texte):
        c = texte[i]
        if c == ">":
            return i + 1
        if c in "'\"":
            fin = texte.find(c, i + 1)  # dans une balise, un attribut n'a pas de \ pour s'échapper
            if fin == -1:
                return None
            i = fin + 1
        elif c == "{":
            i = fin_de_l_expression(texte, i)
            if i is None:
                return None
        else:
            i += 1
    return None


def retirer_balises_et_expressions(texte: str) -> str:
    """Retire les balises JSX, les commentaires HTML et les expressions `{…}` ; le texte entre les balises reste.

    Le code en ligne est lu en premier : ses accents graves tombent, son contenu reste tel quel.
    """
    morceaux, i = [], 0
    while i < len(texte):
        c = texte[i]
        fin = None
        if c == "`":
            fermeture = texte.find("`", i + 1)
            if fermeture != -1 and "\n" not in texte[i + 1 : fermeture]:
                morceaux.append(texte[i + 1 : fermeture])
                i = fermeture + 1
                continue
        if texte.startswith("<!--", i):
            fin = texte.find("-->", i + 4)
            fin = None if fin == -1 else fin + 3
        elif c == "<":
            fin = fin_de_la_balise(texte, i)
        elif c == "{":
            fin = fin_de_l_expression(texte, i)
        if fin is None:
            morceaux.append(c)
            i += 1
        else:
            i = fin
    return "".join(morceaux)


def retirer_marques_markdown(texte: str) -> str:
    """Retire les `**` du gras, les `#` des titres, et change `[texte](adresse)` en `texte`."""
    texte = re.sub(r"\[([^\]\n]*)\]\([^)\n]*\)", r"\1", texte)
    texte = texte.replace("**", "")
    return re.sub(r"(?m)^[ \t]*#{1,6}[ \t]+", "", texte)


def extraire_prose(mdx: str) -> str:
    """La prose d'un chapitre MDX : voir l'en-tête du module pour ce qui est retiré."""
    texte = retirer_frontmatter(mdx.replace("\r\n", "\n"))
    lignes = retirer_imports_et_exports(retirer_blocs_de_code(texte.split("\n")))
    texte = retirer_balises_et_expressions("\n".join(lignes))
    texte = retirer_marques_markdown(texte)
    texte = texte.replace("&#8239;", "\u202f")
    paragraphes = []
    for brut in re.split(r"\n\s*\n", texte):
        # Dans une ligne, les espaces que le retrait d'une balise a laissées se resserrent.
        lignes_du_paragraphe = [re.sub(r"[ \t]+", " ", ligne).strip() for ligne in brut.split("\n")]
        paragraphe = "\n".join(ligne for ligne in lignes_du_paragraphe if ligne)
        if paragraphe:
            paragraphes.append(paragraphe)
    return "\n\n".join(paragraphes) + "\n" if paragraphes else ""


def racine_du_depot() -> Path:
    """La racine du dépôt git qui contient ce projet."""
    sortie = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=Path(__file__).resolve().parent,
        capture_output=True,
        check=True,
    ).stdout
    return Path(sortie.decode("utf-8").strip())


def lire_chapitre(commit: str, chemin: str) -> str:
    """Le texte d'un fichier du dépôt tel qu'il était au commit donné (`git show`)."""
    resultat = subprocess.run(
        ["git", "show", f"{commit}:{chemin}"], cwd=racine_du_depot(), capture_output=True
    )
    if resultat.returncode != 0:
        raise FileNotFoundError(
            f"git ne trouve pas {chemin} au commit {commit}. "
            "Vérifie le commit avec « git log --oneline » et lance la commande depuis le dépôt complet, pas un zip."
        )
    return resultat.stdout.decode("utf-8")


def extraire_du_depot(commit: str) -> str:
    """La prose des chapitres de CHAPITRES au commit donné, l'un après l'autre, un paragraphe vide entre deux."""
    return "\n".join(extraire_prose(lire_chapitre(commit, chemin)) for chemin in CHAPITRES)


def ecrire_texte(commit: str, sortie: Path) -> int:
    """Écrit le texte extrait (UTF-8, fins de ligne LF) ; rend le nombre de points de code."""
    texte = extraire_du_depot(commit)
    with open(sortie, "w", encoding="utf-8", newline="\n") as fichier:
        fichier.write(texte)
    return len(texte)
