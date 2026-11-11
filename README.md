# La Forge IA

[![Site](https://github.com/chipat-neko/forge-ia/actions/workflows/site.yml/badge.svg)](https://github.com/chipat-neko/forge-ia/actions/workflows/site.yml)
[![Python](https://github.com/chipat-neko/forge-ia/actions/workflows/python.yml/badge.svg)](https://github.com/chipat-neko/forge-ia/actions/workflows/python.yml)

La Forge IA est un site en français qui apprend à créer une intelligence
artificielle de zéro, pas à pas. Chaque étape se manipule : on lit un peu,
on fait un pari sur ce que va répondre le modèle, puis on essaie dans
l'atelier. Il n'y a ni compte, ni statistique de visite. La progression est
gardée dans le `localStorage` du navigateur et peut être effacée à tout moment.

Le site est en ligne : <https://chipat-neko.github.io/forge-ia/>

## Structure du dépôt

- `site/` : le site (Astro, publié sur GitHub Pages). Les textes sont dans
  `site/src/content/`.
- `projets/` : les projets Python, un dossier par projet, chacun avec ses
  tests (par exemple `projets/1.3-tokenizer`).
- `notebooks/` : les carnets Jupyter qui accompagnent certains chapitres.
- `docs/` : la spécification, les plans de travail et les maquettes
  (`docs/maquettes/`).

## Lancer le site

Il faut Node.js et npm. Dans PowerShell, depuis la racine du dépôt :

```powershell
cd site; npm install; npm run dev
```

Le site est alors servi en local sur <http://127.0.0.1:8530/forge-ia/>.
Les ports du projet sont listés dans `PORTS.md`.

## Les projets

Les projets Python sont dans `projets/`, chacun avec son README, ses tests
et son verrou `uv.lock` : chacun se lance seul.

Chaque chapitre de la Partie 0, « Les bases », a le sien :

| Projet | Chapitre | Ce qu'il fait |
| --- | --- | --- |
| `projets/0.1-python` | 0.1, Python pour l'IA | compte quel mot suit quel autre dans un texte, et devine le mot suivant |
| `projets/0.2-maths` | 0.2, Les maths utiles | vecteurs, matrices, pente et descente, tirages au sort, softmax et erreur |
| `projets/0.3-poste` | 0.3, Installer son poste | vérifie le poste (Python, PyTorch, carte graphique, pilote) et dit quoi faire |
| `projets/0.4-tenseurs` | 0.4, Tenseurs et calcul sur GPU | crée des tenseurs, prévoit leurs formes, compte leur mémoire, chronomètre le processeur et la carte |
| `projets/0.5-reseau` | 0.5, Premier réseau de neurones | un neurone à seuil, puis un réseau entraîné à la main et avec PyTorch |

Ceux de la Partie 1, « Créer son IA de zéro », ont aussi le leur, un par
chapitre. Les chapitres 1.1 à 1.4 sont en ligne (par exemple
<https://chipat-neko.github.io/forge-ia/partie-1/1-1/>). Les chapitres 1.5 et
1.6 paraîtront après la fin de l'entraînement de « ton IA » : leurs projets sont
prêts, leurs adresses n'existent pas encore.

| Projet | Chapitre | Ce qu'il fait |
| --- | --- | --- |
| `projets/1.1-modele-de-langage` | 1.1, Ce qu'est vraiment un modèle de langage | un modèle qui compte quel caractère suit chaque groupe de caractères, devine la suite d'un texte et en écrit une |
| `projets/1.2-donnees` | 1.2, Les données | trie les documents d'une source avec le vrai code de forge (trop courts, doublons, licences), met de côté la validation et compte ce qui reste |
| `projets/1.3-tokenizer` | 1.3, Le tokenizer | un tokenizer BPE minuscule : il apprend à couper un texte en jetons, en collant les paires les plus fréquentes |
| `projets/1.4-transformer` | 1.4, Le transformer, pièce par pièce | refait chaque pièce du transformer de « ton IA » sur des tenseurs et vérifie qu'elle donne les mêmes nombres que forge |
| `projets/1.5-pre-entrainement` | 1.5, Le pré-entraînement sur ton GPU | lit le journal d'un entraînement et fait un petit essai de pause et de reprise exacte |
| `projets/1.6-evaluation` | 1.6, Évaluer son modèle | refait la perte, la perplexité et la notation d'un QCM à la main, lit le rapport d'évaluation et regarde dans le modèle |

Les autres :

- `projets/mini-modele` : le jumeau Python des démos du mini-modèle
  (l'avant-goût de 0.5, puis 1.5) ;
- `projets/forge` : le moteur de « ton IA », l'IA que le site entraîne.

## Lancer un projet Python

Il faut [uv](https://docs.astral.sh/uv/). Chaque projet se lance depuis son
dossier. Par exemple, depuis la racine du dépôt, pour le projet du
tokenizer :

```powershell
cd projets/1.3-tokenizer; uv run pytest
```

Les projets qui utilisent PyTorch (0.3, 0.4, 0.5, 1.4, 1.5, 1.6 et `forge`) demandent en
plus un extra : `--extra cpu` pour la version de PyTorch pour le
processeur, `--extra gpu` pour celle de la carte NVIDIA. Par exemple :

```powershell
cd projets/0.3-poste; uv run --extra cpu pytest
```

## Tests et publication

GitHub Actions lance deux séries de tests :

- **le site** (`.github/workflows/site.yml`) : vitest et Playwright, à chaque
  envoi sur la branche `main` et à chaque pull request. Pour un envoi sur
  `main`, quand ces tests passent, le site est construit puis publié sur
  GitHub Pages ;
- **les projets Python** (`.github/workflows/python.yml`) : pytest dans chaque
  projet, sous Linux et sous Windows, et l'exécution des notebooks comme sur
  Colab (voir « Notebooks »), seulement quand un envoi ou une pull request
  modifie `projets/`, `notebooks/`, `outils/` ou ce workflow lui-même.

## Notebooks

Les notebooks de `notebooks/` accompagnent les chapitres et s'ouvrent dans
Colab depuis le site. Avant une parution, personne ne les lance à la main sur
Colab : ils sont exécutés automatiquement, de deux façons.

- Par le `test_notebook.py` de leur projet, avec les autres tests du projet
  (son Python et son PyTorch, sous Linux et sous Windows).
- Par le job `notebooks-colab` de `.github/workflows/python.yml`, qui
  reproduit le logiciel de l'image de Colab sans carte graphique (relue le
  05/11/2026) : Python 3.13, `torch==2.14.1` pour processeur (depuis l'index
  de PyTorch), puis les paquets de `outils/colab-sans-carte.txt` (numpy 2.4.6,
  ipykernel 6.17.1…). Le script `outils/executer_notebooks.py` exécute alors
  chaque notebook dans une copie en mémoire, avec `FORGE_IA_LOCAL` à la racine
  du dépôt : le notebook prend le code du dépôt, sans rien installer ni
  télécharger. Il échoue si une cellule lève une erreur, ou si le notebook
  affiche « Même … que la page du site : non ».

La carte graphique de Colab, elle, n'est pas testée : un notebook qui utilise
la carte tourne aussi sur la RTX 5070 Ti avant sa parution.

Les mêmes commandes en local, dans PowerShell, depuis la racine du dépôt.
`env-forge.ps1` place d'abord le cache d'uv dans le dossier des données
(`FORGE_DONNEES`) ; l'environnement `.colab` n'est pas versionné.

```powershell
. .\outils\env-forge.ps1
uv venv --python 3.13 .colab
uv pip install --python .colab --index-url https://download.pytorch.org/whl/cpu torch==2.14.1
uv pip install --python .colab -r outils/colab-sans-carte.txt
.colab\Scripts\python outils\executer_notebooks.py
```

Le script affiche les versions de Python, de PyTorch et de numpy, puis une
ligne par notebook : son nom, sa durée, et `ok` ou `ÉCHEC`. Il peut aussi
exécuter un seul notebook :
`.colab\Scripts\python outils\executer_notebooks.py notebooks\1.3-tokenizer.ipynb`.
Toute modification d'un notebook se rejoue ainsi avant son commit, et le
résultat attendu est `ok`. Les tests de l'exécuteur lui-même, sans noyau, se
lancent avec `.colab\Scripts\python -m pytest -q outils`.

## Parution d'un chapitre

Un chapitre s'écrit d'abord en brouillon, dans
`site/src/brouillons/chapitres/<p>-<n>.mdx` (par exemple `0-1.mdx` pour le
chapitre 0.1). Un brouillon n'est construit qu'avec les pages d'essai
(`npm run build:essais`, la construction des parcours de test), à son adresse
définitive et hors de la recherche. Le site publié n'en contient rien, et
GitHub Actions le vérifie après chaque construction. L'accueil, les pages de
partie et le pied des chapitres le montrent « à venir ».

Pour faire paraître un chapitre :

1. Les conditions : tous les tests sont verts ; la page n'a aucune valeur
   « à mesurer » (`[data-a-mesurer]`) ; le notebook passe
   `outils/executer_notebooks.py` dans l'environnement `.colab` (voir la
   section « Notebooks »), et, s'il utilise la carte graphique, il a tourné
   sur la RTX 5070 Ti ; l'auteur du site a dit oui à la publication.
2. Déplacer le brouillon :
   `git mv site/src/brouillons/chapitres/<p>-<n>.mdx site/src/content/chapitres/<p>-<n>.mdx`.
3. Rien à changer dans les parcours : ils lisent les fichiers sur le
   disque, et voient d'eux-mêmes le chapitre paru (le pied des chapitres
   voisins, l'accueil, la recherche). Seuls leurs commentaires qui le disent
   « à venir » sont à relire.
4. Si le chapitre contient le mini-modèle (0.5), écarter
   `dist/_astro/travailleur-*.js` de la recherche du prénom dans
   `.github/workflows/site.yml`, comme le dit son commentaire.
5. `npm run build`, dans `site/` : le dossier `dist/partie-<p>/<p>-<n>/`
   existe.

## Licences

- Le code est sous licence MIT : voir `LICENSE`.
- Les textes du site (`site/src/content/`) sont sous licence CC BY 4.0 : voir
  `LICENCE-TEXTES.md`.
