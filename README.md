# La Forge IA

La Forge IA est un site en français qui apprend à créer une intelligence
artificielle de zéro, pas à pas. Chaque étape se manipule : on lit un peu,
on fait un pari sur ce que va répondre le modèle, puis on essaie dans
l'atelier. Il n'y a ni compte, ni statistique de visite. La progression est
gardée dans le `localStorage` du navigateur et peut être effacée à tout moment.

Adresse publique : <https://chipat-neko.github.io/forge-ia/>

## Structure du dépôt

- `site/` : le site (Astro, publié sur GitHub Pages). Les textes sont dans
  `site/src/content/`.
- `projets/` : les projets Python, un dossier par projet, chacun avec ses
  tests (par exemple `projets/1.3-tokenizer`).
- `notebooks/` : les carnets Jupyter qui accompagnent certaines étapes.
- `docs/` : la spécification, les plans de travail et les maquettes
  (`docs/maquettes/`).

## Lancer le site

Il faut Node.js et npm. Dans PowerShell :

```powershell
cd site; npm install; npm run dev
```

Le site est alors servi en local sur <http://localhost:8530/forge-ia/>.
Les ports du projet sont listés dans `PORTS.md`.

## Lancer un projet Python

Il faut [uv](https://docs.astral.sh/uv/). Par exemple pour le projet du
tokenizer :

```powershell
cd projets/1.3-tokenizer; uv run pytest
```

## Licences

- Le code est sous licence MIT : voir `LICENSE`.
- Les textes du site (`site/src/content/`) sont sous licence CC BY 4.0 : voir
  `LICENCE-TEXTES.md`.
