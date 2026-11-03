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

## Licences

- Le code est sous licence MIT : voir `LICENSE`.
- Les textes du site (`site/src/content/`) sont sous licence CC BY 4.0 : voir
  `LICENCE-TEXTES.md`.
