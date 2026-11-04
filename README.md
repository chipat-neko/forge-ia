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
- `notebooks/` : les carnets Jupyter qui accompagnent certaines étapes.
- `docs/` : la spécification, les plans de travail et les maquettes
  (`docs/maquettes/`).

## Lancer le site

Il faut Node.js et npm. Dans PowerShell, depuis la racine du dépôt :

```powershell
cd site; npm install; npm run dev
```

Le site est alors servi en local sur <http://127.0.0.1:8530/forge-ia/>.
Les ports du projet sont listés dans `PORTS.md`.

## Lancer un projet Python

Il faut [uv](https://docs.astral.sh/uv/). Les commandes Python se lancent
depuis la racine du dépôt. Par exemple pour le projet du tokenizer :

```powershell
cd projets/1.3-tokenizer; uv run pytest
```

## Tests et publication

GitHub Actions lance deux séries de tests :

- **le site** (`.github/workflows/site.yml`) : vitest et Playwright, à chaque
  envoi sur la branche `main` et à chaque pull request. Pour un envoi sur
  `main`, quand ces tests passent, le site est construit puis publié sur
  GitHub Pages ;
- **les projets Python** (`.github/workflows/python.yml`) : pytest dans chaque
  projet, sous Linux et sous Windows, seulement quand un envoi ou une pull
  request modifie `projets/`, `notebooks/` ou ce workflow lui-même.

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
   sur la RTX 5070 Ti ; l'utilisateur a dit oui à la publication.
2. Déplacer le brouillon :
   `git mv site/src/brouillons/chapitres/<p>-<n>.mdx site/src/content/chapitres/<p>-<n>.mdx`.
3. Mettre à jour les parcours qui disent ce chapitre « à venir »
   (`navigation.spec.ts`, et le pied des chapitres voisins).
4. Si le chapitre contient le mini-modèle (0.5), écarter
   `dist/_astro/travailleur-*.js` de la recherche du prénom dans
   `.github/workflows/site.yml`, comme le dit son commentaire.
5. `npm run build`, dans `site/` : le dossier `dist/partie-<p>/<p>-<n>/`
   existe.

## Licences

- Le code est sous licence MIT : voir `LICENSE`.
- Les textes du site (`site/src/content/`) sont sous licence CC BY 4.0 : voir
  `LICENCE-TEXTES.md`.
