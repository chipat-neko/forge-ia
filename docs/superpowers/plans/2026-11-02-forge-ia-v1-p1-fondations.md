# La Forge IA, vague 1, plan 1 : fondations du site et chapitre pilote 1.3

> **Pour les agents qui exécutent ce plan :** SOUS-SKILL REQUIS : utiliser superpowers:subagent-driven-development (recommandé) ou superpowers:executing-plans pour réaliser ce plan tâche par tâche. Les étapes utilisent des cases à cocher (`- [ ]`).

**But :** mettre en ligne sur GitHub Pages le squelette complet du site La Forge IA (dépôt public, gabarit de chapitre de la direction B, progression, recherche, accueil) avec un premier chapitre entièrement fini et testé : 1.3 « Le tokenizer », son moteur BPE pédagogique jumeau en TypeScript et en Python, son projet et son notebook Colab.

**Architecture :**

- Un seul dépôt `chipat-neko/forge-ia`, cloné dans `D:\creation-ia`.
- Le site Astro (sortie statique, base `/forge-ia/`) vit dans `site/`. Les projets Python vivent dans `projets/`, les notebooks dans `notebooks/`.
- Le gabarit de chapitre est fait de composants Astro et d'un script client unique, sans framework. Les démos riches sont des îlots Svelte 5. Les deux communiquent par des « canaux » (petits magasins observables) et par l'événement DOM `forge:acquis`.
- Tout ce qui peut être calculé au moment de la construction l'est : bonnes réponses des paris, phrase d'ouverture découpée, extraits de code tirés des fichiers testés.

**Pile technique :**

- Astro 7.4, `@astrojs/mdx`, `@astrojs/svelte` 9, Svelte 5.57, TypeScript ;
- Vitest, Playwright avec `@axe-core/playwright`, Pagefind 1.6 ;
- polices Fontsource ;
- Python 3.12 ou plus avec uv 0.12, `regex`, pytest, nbclient ;
- GitHub Actions et GitHub Pages.

**Spécification :** `docs/superpowers/specs/2026-11-02-forge-ia-design.md` (approuvée le 02/11/2026). Maquette de référence : `docs/maquettes/maquette-10-fusion-energie.html`.

## Place de ce plan dans la vague 1

La vague 1 est trop large pour un seul plan. Elle est découpée en cinq plans qui livrent chacun quelque chose qui marche :

1. **Ce plan :** fondations du site et chapitre pilote 1.3, version pédagogique.
2. **Paquet `forge` et chaîne de ton IA :**
   - vérification de l'espace libre sur D:, d'au moins 30 à 40 Go ;
   - données (1.2) ;
   - vrai tokenizer de ton IA, sur les octets, avec ses jetons spéciaux (suite de 1.3) ;
   - transformer (1.4) ;
   - pré-entraînement avec pause et reprise (1.5) : taille et durée proposées à l'utilisateur avec des chiffres mesurés, après l'essai chronométré GPU et CPU ;
   - évaluation (1.6).
3. **Les démos restantes :** mini-modèle qui apprend dans le navigateur, animation de l'attention, calculateur de coût.
4. **Partie 0 :** chapitres 0.1 à 0.5, avec projets et notebooks.
5. **Rédaction des chapitres 1.1, 1.2, 1.4, 1.5 et 1.6**, plus l'annuaire et le glossaire, puis la liste Colab de la vague et sa validation par l'utilisateur.

**Écart assumé avec la spécification :** la spécification met la vérification d'au moins 30 à 40 Go libres sur D: en toute première étape de la vague 1. Ce plan-ci n'a besoin que d'environ 2 Go (dépendances npm et un petit environnement Python). La vérification ouvre donc le plan 2, celui qui en a besoin. La tâche 1 vérifie seulement qu'il reste au moins 3 Go.

## Contraintes globales

- Tout le site est en français, avec la typographie française : espace fine insécable (U+202F) devant `; : ! ?` et à l'intérieur des guillemets « ».
- Couleurs exactes :
  - papier `#FFFFFF` ;
  - encre indigo `#232057`, encre douce `#5B5888`, lavande `#8F8CB8` ;
  - brume `#E6E5F0` et `#F5F4FA` ;
  - soleil `#FFC93C`, soleil vif `#FFB800`, soleil pâle `#FFF4D6` ;
  - menthe `#1C6E58` (fond `#E2F5EF`), corail `#B8342D` (fond `#FDECEA`) ;
  - jetons `#E4E2F4` et `#F2E9D8`.
- Le jaune soleil est réservé à ce qui se manipule.
- Polices : Gabarito pour les titres et les chiffres, Newsreader pour le texte, JetBrains Mono pour le code. Elles sont auto-hébergées (Fontsource), sans aucun appel à Google Fonts.
- **Interdits :**
  - étiquettes en capitales espacées au-dessus des titres ;
  - méta-informations séparées par des points médians ;
  - « → » collé aux liens et boutons ;
  - emojis décoratifs ;
  - encadrés à bordure gauche colorée ;
  - dégradés décoratifs ;
  - cartes arrondies identiques avec ombre douce ;
  - animations d'entrée sur les sections.

  Le mouvement est réservé aux réponses à une action du lecteur.
- **Plancher de qualité :**
  - aucun débordement horizontal à 390 px ;
  - focus clavier visible ;
  - `prefers-reduced-motion` respecté ;
  - contraste AA, avec zéro violation axe (wcag2a, wcag2aa) ;
  - lignes de texte de moins de 80 caractères environ.
- Les bonnes réponses des paris sont calculées par le même code que la démo, jamais écrites à la main.
- Pour les calculs déterministes, le JS et le Python donnent exactement le même résultat.
- Rien n'est publié sans avoir tourné. Les extraits de code des pages sont tirés des fichiers testés, jamais recopiés.
- Le code pédagogique a des noms et des commentaires en français.
- Ports locaux : 8530 pour le serveur Astro (dev et aperçu), 8531 pour le serveur lancé par Playwright.
- Dépôt public `chipat-neko/forge-ia`, site `https://chipat-neko.github.io/forge-ia/`, base `/forge-ia`, `trailingSlash: 'always'`.
- Licences : MIT pour le code, CC BY 4.0 pour les textes.
- Windows natif ; les commandes sont données pour PowerShell.
- Ni compte, ni statistique de visite. La progression est gardée dans `localStorage` et peut être effacée.
- Fins de ligne LF partout (`.gitattributes` : `* text=auto eol=lf`) : le corpus et les attendus doivent être identiques à l'octet sous Windows et sous Linux.
- Chaque message de commit se termine par la ligne `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Points à surveiller à la relecture

Les tests ordinaires ne couvrent pas ces cinq situations, qui sont pourtant les plus susceptibles de gêner un lecteur. Chacune reçoit son test dans la tâche indiquée.

1. **`localStorage` indisponible, plein ou corrompu** (navigation privée, quota, JSON abîmé) : la page fonctionne normalement, sans progression gardée, et sans erreur. Test dans la tâche 4.
2. **Saisie inhabituelle dans l'atelier** (champ vide, emoji, caractère absent du corpus, retours à la ligne, espaces multiples, 10 000 caractères) : rien ne plante. Les caractères inconnus s'affichent comme jetons « inconnu », et le découpage de 10 000 caractères prend moins de 500 ms. Tests dans les tâches 7 et 8.
3. **Progression enregistrée devenue obsolète** (identifiant de pari disparu, indice de choix hors limites après une mise à jour du contenu) : l'entrée fautive est ignorée, et le pari redevient jouable. Test dans la tâche 4.
4. **JavaScript désactivé ou pas encore chargé** : tout le texte reste lisible. Les zones verrouillées ne sont ni floues ni inertes, car le verrou n'est posé que par le script. Test dans la tâche 5.
5. **Rechargement ou lien direct vers `#etape-4`** après un pari : le pari reste répondu, le verrou reste ouvert, et la barre du haut montre les bonnes étapes faites. Test dans la tâche 5.

---

### Tâche 1 : dépôt, licences, ports et maquettes versées

**Fichiers :**

- Créer : `.gitignore`, `.gitattributes`, `README.md`, `LICENSE`, `LICENCE-TEXTES.md`, `PORTS.md`
- Créer : `docs/maquettes/` (copie des 10 maquettes et de `bpe.js`)
- Modifier : `C:\Users\chipat\.claude\PORTS.md` (fichier global de l'utilisateur)

**Interfaces :**

- Produit : le dépôt `chipat-neko/forge-ia` public, la branche `main`, l'arborescence racine.

- [ ] **Étape 1 : vérifier l'environnement.** Lancer `git config --global user.name` (attendu : `chipat-neko`), `gh auth status` (attendu : connecté) et `(Get-PSDrive D).Free/1GB`. S'il reste moins de 3 Go sur D:, s'arrêter et prévenir l'utilisateur.
- [ ] **Étape 2 : créer les fichiers de la racine.**
  - `.gitignore` ignore : `.superpowers/`, `node_modules/`, `site/dist/`, `site/.astro/`, `__pycache__/`, `.venv/`, `.pytest_cache/`, `site/test-results/`, `site/playwright-report/`, `*.ipynb_checkpoints`.
  - `.gitattributes` contient `* text=auto eol=lf`.
  - `LICENSE` : texte MIT, « Copyright (c) 2026 chipat-neko ».
  - `LICENCE-TEXTES.md` : les textes de `site/src/content/` sont sous CC BY 4.0, avec le lien vers la licence officielle.
  - `README.md`, en français : ce qu'est le site, son adresse publique, la structure du dépôt (`site/`, `projets/`, `notebooks/`, `docs/`), les commandes PowerShell pour lancer le site (`cd site; npm install; npm run dev`) et un projet Python (`cd projets/1.3-tokenizer; uv run pytest`).
  - `PORTS.md` : 8530 pour le serveur Astro (dev et aperçu), 8531 pour le serveur des parcours Playwright, tous deux en local.
- [ ] **Étape 3 : verser les maquettes.** Copier `D:\creation-ia\.superpowers\brainstorm\maquettes\*` vers `docs/maquettes/`.
- [ ] **Étape 4 : créer le dépôt local et le premier commit.**

```powershell
git init -b main
git add .
git commit -m "Fondations : licences, ports, maquettes, spécification et plan`n`nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Étape 5 : créer le dépôt GitHub public et pousser.**

```powershell
gh repo create chipat-neko/forge-ia --public --source . --push --description "La Forge IA : créer une IA de zéro, pas à pas (site en français)"
gh repo view chipat-neko/forge-ia --json visibility,url
```

Attendu : `"visibility":"PUBLIC"`.

- [ ] **Étape 6 : inscrire les ports.**
  - Dans `C:\Users\chipat\.claude\PORTS.md`, ajouter deux lignes au tableau « Ports réservés » : `8530 | local | forge-ia : serveur Astro (dev et aperçu) | D:\creation-ia\site\astro.config.mjs (voir D:\creation-ia\PORTS.md) | non` et `8531 | local | forge-ia : serveur des parcours Playwright | D:\creation-ia\site\playwright.config.ts | non`. Mettre à jour la ligne « Dernière mise à jour » en gardant l'historique.
  - Écrire dans la mémoire partagée deux entrées avec l'étiquette `ports` : « Port du projet forge-ia (serveur Astro) : 8530 » et « Port du projet forge-ia (parcours Playwright) : 8531 ».
  - Si le serveur mémoire ne répond pas, le noter dans la ligne « Dernière mise à jour », comme cela a déjà été fait pour d'autres projets.

### Tâche 2 : moteur BPE pédagogique en Python

**Fichiers :**

- Créer : `projets/1.3-tokenizer/pyproject.toml`, `projets/1.3-tokenizer/README.md`
- Créer : `projets/1.3-tokenizer/donnees/corpus.txt`
- Créer : `projets/1.3-tokenizer/tokenizer_pedagogique/__init__.py`, `bpe.py`, `attendus.py`, `__main__.py`
- Test : `projets/1.3-tokenizer/tests/test_bpe.py`, `projets/1.3-tokenizer/tests/attendus.json`

**Interfaces (produites, dans `tokenizer_pedagogique/bpe.py`) :**

- `MOTIF = r"\s?[\p{L}\p{M}]+|\s?\p{N}+|\s?[^\s\p{L}\p{N}]+|\s+"`, compilé avec le module `regex`.
- `pre_decouper(texte: str) -> list[str]`
- `compter_mots(corpus: str) -> dict[tuple[str, ...], int]`
- `compter_paires(mots: dict[tuple[str, ...], int]) -> Counter[tuple[str, str]]`
- `paire_la_plus_frequente(compte: Counter[tuple[str, str]]) -> tuple[str, str]` : renvoie la paire la plus fréquente. En cas d'égalité, elle renvoie la plus petite paire `(a, b)` dans l'ordre des points de code. Corps imposé : `return min(compte, key=lambda paire: (-compte[paire], paire))`.
- `fusionner(mots: dict[tuple[str, ...], int], paire: tuple[str, str]) -> dict[tuple[str, ...], int]` : fusion de gauche à droite, sans chevauchement.
- `class Fusion(NamedTuple): a: str; b: str; compte: int`
- `apprendre(corpus: str, nb_fusions: int) -> list[Fusion]` : s'arrête si aucune paire n'apparaît au moins 2 fois.
- `class Jeton(NamedTuple): texte: str; id: int | None; mot: int`
- `class TokenizerPedagogique` :
  - `__init__(self, corpus: str, nb_fusions_max: int = 200)` ;
  - attributs `fusions: list[Fusion]` et `base: list[str]` (caractères uniques du corpus, triés par point de code) ;
  - `decouper(self, texte: str, k: int) -> list[Jeton]`.
- **Numéros des jetons :** un caractère de base a pour numéro son indice dans `base`, ou `None` s'il est inconnu. Un symbole créé par la fusion d'indice `j` a pour numéro `len(base) + j`. Le numéro est porté par le symbole au moment de la fusion, pas cherché par son texte.
- `charger_corpus() -> str` : lit `donnees/corpus.txt` en UTF-8.
- `attendus.py` : `TEXTES_DE_REFERENCE: list[str]`, `KS_DE_REFERENCE = [0, 1, 10, 30, 60, 100, 165]`, `calculer_attendus() -> dict`. Exécuté comme module, il écrit `tests/attendus.json`. Format :

```json
{"fusions": [["e", "s", 43], ...],
 "cas": [{"texte": "...", "k": 30, "jetons": [["l", 26, 0], ...]}]}
```

- `__main__.py` : `uv run python -m tokenizer_pedagogique "Les forgerons" --fusions 30` affiche les jetons séparés par `|` (espace affichée `␣`) et leurs numéros.

**Valeurs imposées :**

- `donnees/corpus.txt` est la copie exacte de la constante `CORPUS` de `docs/maquettes/bpe.js`, sans retour à la ligne final.
- `TEXTES_DE_REFERENCE` contient au moins :
  - `"Le forgeron frappe le métal sur l'enclume."`
  - `"Les forgerons découpent le texte en jetons."`
  - `"les forgerons"`
  - `"reforgeronnes"`
  - `"Salut 🙂"`
  - `"Le forgeron  frappe, 2026 !\nFin"`
  - `""`
  - `"forgé, reforgé : forgeronne"`
- `pyproject.toml` : `requires-python = ">=3.12"`, dépendance `regex`, groupe de développement `pytest`.

- [ ] **Étape 1 : écrire les tests qui échouent** dans `tests/test_bpe.py`.

```python
from collections import Counter
import json, pathlib
from tokenizer_pedagogique.bpe import (TokenizerPedagogique, apprendre, charger_corpus,
    paire_la_plus_frequente, pre_decouper)
from tokenizer_pedagogique.attendus import calculer_attendus

CORPUS = charger_corpus()

def test_corpus_sans_retour_chariot():
    assert "\r" not in CORPUS

def test_pre_decouper():
    assert pre_decouper("Le forgeron  frappe, 2026 !\nFin") == [
        "Le", " forgeron", "  ", "frappe", ",", " 2026", " !", "\nFin"]

def test_departage_des_egalites():
    assert paire_la_plus_frequente(Counter({("b", "a"): 2, ("a", "b"): 2})) == ("a", "b")

def test_fusions_du_corpus():
    fusions = apprendre(CORPUS, 200)
    assert len(fusions) == 165
    assert [(f.a, f.b, f.compte) for f in fusions[:5]] == [
        ("e", "s", 43), (" ", "l", 27), ("e", "n", 26), (" ", "d", 21), ("o", "n", 21)]
    assert (fusions[29].a, fusions[29].b, fusions[29].compte) == ("é", "c", 7)

def test_decoupages():
    tok = TokenizerPedagogique(CORPUS)
    assert len(tok.base) == 45
    phrase = "Les forgerons découpent le texte en jetons."
    assert len(tok.decouper(phrase, 0)) == 43
    assert len(tok.decouper(phrase, 60)) == 18
    assert [j.texte for j in tok.decouper(phrase, 100)] == [
        "L", "es", " forg", "er", "ons", " découp", "ent", " le", " t", "e", "x",
        "te", " en", " jetons", "."]
    assert len(tok.decouper("les forgerons", 30)) == 9
    assert len(tok.decouper("reforgeronnes", 165)) == 6
    assert len(tok.decouper("Le forgeron frappe le métal sur l'enclume.", 30)) == 33

def test_caractere_inconnu_et_texte_vide():
    tok = TokenizerPedagogique(CORPUS)
    assert tok.decouper("🙂", 10)[-1].id is None
    assert tok.decouper("", 30) == []

def test_attendus_a_jour():
    fichier = pathlib.Path(__file__).parent / "attendus.json"
    assert calculer_attendus() == json.loads(fichier.read_text(encoding="utf-8"))
```

- [ ] **Étape 2 : lancer les tests et vérifier qu'ils échouent.** Commande : `cd projets/1.3-tokenizer; uv run pytest -q`. Attendu : échec à l'import (`ModuleNotFoundError` ou `ImportError`).
- [ ] **Étape 3 : écrire `bpe.py`, `attendus.py`, `__main__.py` et `corpus.txt`** selon les interfaces ci-dessus.
  - Encadrer `compter_paires` et `paire_la_plus_frequente` de marqueurs de région, que le chapitre 1.3 extraira : lignes `# region: compter` / `# fin: compter` et `# region: choisir` / `# fin: choisir`.
  - Commentaires et docstrings en français, pour débutants.
  - Générer ensuite `tests/attendus.json` avec `uv run python -m tokenizer_pedagogique.attendus`.
- [ ] **Étape 4 : lancer les tests et vérifier qu'ils passent.** Commande : `uv run pytest -q`. Attendu : tous les tests passent.
- [ ] **Étape 5 : commit** (`projets/1.3-tokenizer/`), message « Tokenizer pédagogique BPE en Python, avec attendus de référence », terminé par la ligne Co-Authored-By.

### Tâche 3 : squelette du site Astro, jetons de style et polices

**Fichiers :**

- Créer : `site/package.json`, `site/astro.config.mjs`, `site/tsconfig.json`, `site/vitest.config.ts`
- Créer : `site/src/styles/jetons.css`, `site/src/styles/base.css`
- Créer : `site/src/layouts/Base.astro`, `site/src/pages/index.astro` (provisoire, remplacée en tâche 12)

**Interfaces :**

- Produit : `Base.astro`, avec les props `{ titre: string; description?: string }`, `<html lang="fr">`, l'import des polices et des feuilles de style, et un `<slot />`.
- Produit : les variables CSS de `jetons.css`, utilisées par toutes les tâches suivantes :
  - `--papier`, `--indigo`, `--indigo-doux`, `--lavande`, `--brume`, `--brume-claire` ;
  - `--soleil`, `--soleil-vif`, `--soleil-pale` ;
  - `--menthe`, `--menthe-pale`, `--corail`, `--corail-pale` ;
  - `--teinte-a`, `--teinte-b` ;
  - `--titres`, `--texte`, `--mono`.

  Valeurs : voir les contraintes globales.
- Produit : les scripts npm :
  - `dev` : `astro dev`, port 8530 ;
  - `build` : `astro build && pagefind --site dist` ;
  - `build:essais` : la même chose avec `FORGE_ESSAIS=1`, via `cross-env` ;
  - `preview` : `astro preview`, port 8530 par défaut ;
  - `test` : `vitest run` ;
  - `e2e` : `playwright test`.

**Réglages imposés pour `astro.config.mjs` :**

- `site: 'https://chipat-neko.github.io'`, `base: '/forge-ia'`, `trailingSlash: 'always'`, `output: 'static'` ;
- `server: { port: 8530, host: '127.0.0.1' }` ;
- intégrations `mdx()` et `svelte()` ;
- `vite.server.fs.allow: ['..']`, pour pouvoir importer `../projets/**` ;
- le plugin remark de la tâche 4 (`remarkTypoFr`) est branché dans `markdown.remarkPlugins`.

**Dépendances :**

- `astro@^7.4`, `@astrojs/mdx`, `@astrojs/svelte@^9`, `svelte@^5.57`, `typescript` ;
- `@fontsource/gabarito` (graisses 500, 600, 700, 800), `@fontsource-variable/newsreader`, `@fontsource-variable/jetbrains-mono` ;
- `pagefind@^1.6`, `cross-env` ;
- en développement : `vitest`, `@playwright/test`, `@axe-core/playwright`.

- [ ] **Étape 1 : créer le projet** (`npm create astro@latest` en mode minimal, ou fichiers à la main), installer les dépendances et écrire la configuration ci-dessus.
- [ ] **Étape 2 : écrire `jetons.css`, `base.css` et `Base.astro`.**
  - `base.css` : texte en Newsreader avec interligne d'environ 1,6, titres en Gabarito, focus visible (contour indigo de 3 px et décalage de 2 px), `@media (prefers-reduced-motion: reduce)` qui coupe transitions et animations.
  - La page `index.astro` provisoire affiche « La Forge IA » et une phrase « Le site se construit. Premier chapitre : le tokenizer. ».
- [ ] **Étape 3 : vérifier la construction.** Commande : `cd site; npm run build; npx astro check`. Attendu : la construction réussit, `astro check` donne 0 erreur, `dist/index.html` contient `lang="fr"`, et aucun fichier de `dist/` ne contient `fonts.googleapis.com` (`Select-String -Path dist -Pattern fonts.googleapis -Recurse` ne renvoie rien).
- [ ] **Étape 4 : commit** (`site/`), message « Squelette Astro, jetons de style et polices auto-hébergées ».

### Tâche 4 : bibliothèque du site (parcours, progression, canaux, typographie)

**Fichiers :**

- Créer : `site/src/lib/parcours.ts`, `site/src/lib/progression.ts`, `site/src/lib/canal.ts`, `site/src/lib/typo.ts`, `site/src/lib/remark-typo-fr.ts`
- Test : `site/src/lib/parcours.test.ts`, `progression.test.ts`, `canal.test.ts`, `typo.test.ts`

**Interfaces (produites) :**

- `parcours.ts` :
  - `interface Chapitre { numero: string; titre: string; groupe?: string }`
  - `interface Partie { numero: 0 | 1 | 2 | 3; titre: string; chapitres: Chapitre[] }`
  - `PARCOURS: Partie[]` : titres exacts de la section 4 de la spécification. Les groupes de la Partie 1 sont « Le cœur : un modèle de langage », « Le rendre utile », « Voir et créer des images », « Agir seul » et « Le mettre en service ».
  - `hrefChapitre(numero: string): string` : renvoie `${import.meta.env.BASE_URL}partie-${p}/${numero.replace('.', '-')}/`, avec une seule barre entre la base et le reste.
  - `trouverChapitre(numero: string): { partie: Partie; chapitre: Chapitre; rang: number; total: number }` : lève une erreur si le numéro est inconnu.
  - `voisins(numero: string): { precedent?: Chapitre; suivant?: Chapitre }` : l'ordre suit tout le parcours, de 0.1 à 3.4.
- `progression.ts` :
  - clé de stockage `'forge-ia:progression:v1'` ;
  - `interface EtatChapitre { paris: Record<string, number>; acquis: string[]; etapes: string[] }` ;
  - `lireChapitre(numero: string, stockage?: Storage | null): EtatChapitre` ;
  - `noterPari(numero: string, idPari: string, choix: number, stockage?): void` ;
  - `noterAcquis(numero: string, cle: string, stockage?): void` ;
  - `noterEtape(numero: string, idEtape: string, stockage?): void` ;
  - `effacer(numero?: string, stockage?): void` ;
  - `nettoyer(numero: string, parisValides: Record<string, number>, stockage?): EtatChapitre` : prend le nombre de choix de chaque pari, retire les paris inconnus ou hors limites, et renvoie l'état propre.
  - **Comportement de repli :** par défaut, `stockage` vaut `globalThis.localStorage`. S'il est absent, ou si la lecture ou l'écriture lève une erreur, la progression est gardée en mémoire, sans erreur. Un JSON corrompu donne un état vide.
- `canal.ts` :
  - `interface Canal<T> { get(): T; set(v: T): void; subscribe(fn: (v: T) => void): () => void }`, conforme au contrat des magasins Svelte (`subscribe` appelle `fn` tout de suite) ;
  - `canal<T>(nom: string, initiale: T): Canal<T>` : la même instance pour le même nom ; la première valeur initiale gagne ;
  - `ouverture(nom: string): Canal<boolean>`, qui vaut `canal('ouvert:' + nom, false)`.
- `typo.ts` : `typographier(texte: string): string`.
  - Une espace ordinaire ou insécable (U+0020 ou U+00A0) placée juste avant `; : ! ?` devient U+202F. De même juste après « et juste avant ».
  - Un « ou un » collé à une lettre reçoit U+202F.
  - Rien n'est ajouté devant `; : ! ?` quand il n'y avait pas d'espace, pour protéger `16:9` et `https://`.
- `remark-typo-fr.ts` : `remarkTypoFr()`, plugin remark qui applique `typographier` aux nœuds `text` uniquement, jamais à `code` ni à `inlineCode`.

- [ ] **Étape 1 : écrire les tests qui échouent.**

```ts
// parcours.test.ts
expect(PARCOURS.map(p => p.chapitres.length)).toEqual([5, 21, 4, 4]);
expect(trouverChapitre('1.3')).toMatchObject({ rang: 3, total: 21 });
expect(voisins('1.3').precedent?.titre).toBe('Les données : où les trouver, les nettoyer, les licences');
expect(voisins('1.3').suivant?.numero).toBe('1.4');
expect(voisins('0.5').suivant?.numero).toBe('1.1');
expect(voisins('1.21').suivant?.numero).toBe('2.1');
expect(voisins('3.4').suivant).toBeUndefined();
expect(hrefChapitre('1.3')).toBe('/forge-ia/partie-1/1-3/');
expect(() => trouverChapitre('9.9')).toThrow();

// progression.test.ts (faux stockage en mémoire)
noterPari('1.3', 'prediction', 1, faux); noterAcquis('1.3', 'nombres', faux);
expect(lireChapitre('1.3', faux)).toEqual({ paris: { prediction: 1 }, acquis: ['nombres'], etapes: [] });
const casse = { getItem() { throw new Error('x'); }, setItem() { throw new Error('x'); } } as unknown as Storage;
expect(() => noterPari('1.3', 'p', 0, casse)).not.toThrow();
faux.setItem('forge-ia:progression:v1', '{pas du json');
expect(lireChapitre('1.3', faux)).toEqual({ paris: {}, acquis: [], etapes: [] });
noterPari('1.3', 'disparu', 0, faux); noterPari('1.3', 'prediction', 7, faux);
expect(nettoyer('1.3', { prediction: 3 }, faux).paris).toEqual({});
effacer('1.3', faux); expect(lireChapitre('1.3', faux).paris).toEqual({});

// canal.test.ts
expect(canal('x', 1)).toBe(canal('x', 2)); expect(canal('x', 2).get()).toBe(1);
const vus: number[] = []; const stop = canal('y', 0).subscribe(v => vus.push(v));
canal('y', 0).set(5); stop(); canal('y', 0).set(6);
expect(vus).toEqual([0, 5]);
expect(ouverture('atelier').get()).toBe(false);

// typo.test.ts
expect(typographier('Pourquoi découper ?')).toBe('Pourquoi découper\u202F?');
expect(typographier('« les forgerons »')).toBe('«\u202Fles forgerons\u202F»');
expect(typographier('«forge»')).toBe('«\u202Fforge\u202F»');
expect(typographier('https://exemple.fr et 16:9')).toBe('https://exemple.fr et 16:9');
```

- [ ] **Étape 2 : lancer les tests et vérifier qu'ils échouent.** Commande : `cd site; npx vitest run src/lib`. Attendu : échec, les modules sont introuvables.
- [ ] **Étape 3 : écrire les cinq modules** selon les interfaces, puis brancher `remarkTypoFr` dans `astro.config.mjs`.
- [ ] **Étape 4 : lancer les tests et vérifier qu'ils passent.** Commande : `npx vitest run src/lib`. Attendu : tous les tests passent.
- [ ] **Étape 5 : commit**, message « Parcours, progression, canaux et typographie française ».

### Tâche 5 : gabarit de chapitre (barre, étapes, paris, verrous, récapitulatif, pied, encadré labo)

**Fichiers :**

- Créer : `site/src/content.config.ts` (collection `chapitres`)
- Créer : `site/src/layouts/LayoutChapitre.astro`
- Créer : `site/src/components/gabarit/BarreHaut.astro`, `Etape.astro`, `Pari.astro`, `Verrou.astro`, `Recap.astro`, `PiedChapitre.astro`, `EncadreLabo.astro`
- Créer : `site/src/scripts/chapitre.ts` (le seul script client du gabarit)
- Créer : `site/src/pages/[partie]/[chapitre].astro`
- Créer : `site/src/pages/essais/[nom].astro`, page d'essai construite seulement si `FORGE_ESSAIS=1`, et `site/src/essais/gabarit.mdx`
- Créer : `site/playwright.config.ts`
- Test : `site/e2e/gabarit.spec.ts`, `site/e2e/outils.ts`

**Interfaces :**

- Consomme : `parcours.ts`, `progression.ts` et `canal.ts` (tâche 4), `Base.astro` (tâche 3).
- **Schéma de la collection `chapitres`** (fichiers `site/src/content/chapitres/<p>-<n>.mdx`) :

```ts
{ partie: 0|1|2|3, numero: string /* doit exister dans PARCOURS */, titre: string,
  chapeau: string, programme: string,
  acquis: { cle: string; texte: string; ou: string }[] }
```

- `LayoutChapitre.astro` : props = les données du schéma. Il pose `data-chapitre={numero}` sur `<article>` et contient la barre du haut, l'ouverture (slot `ouverture`), le contenu, le récapitulatif et le pied.
- `Etape.astro` : props `{ numero: number; titre: string }`. Il rend `<section class="etape" id={'etape-' + numero} data-titre={titre}>` avec un grand numéro dans la marge de gauche, le slot par défaut, et le slot `note` dans la marge de droite (sous le texte en dessous de 900 px).
- `Pari.astro` : props `{ id: string; question: string; precision?: string; choix: { texte: string; juste?: boolean }[]; acquis?: string; ouvre?: string }`. Le slot par défaut contient l'explication, révélée après le pari.
  - Exactement un choix doit être juste. Sinon, `throw new Error('Pari ' + id + ' : il faut exactement un choix juste')` au moment de la construction.
  - Rendu : `<div class="pari" data-pari={id} data-acquis={acquis} data-ouvre={ouvre}>`, avec des boutons `data-choix={i}` et `data-juste` sur le bon.
- `Verrou.astro` : props `{ nom: string; message: string }`. Rendu : `<div data-verrou={nom} data-message={message}><slot /></div>`. C'est le script qui pose le verrou (flou, opacité réduite, `inert`, message visible), jamais le HTML.
- `EncadreLabo.astro` : props `{ sources: { titre: string; url: string; verifieLe: string }[] }`. Titre fixe « Et chez un grand labo ? », slot par défaut, puis la ligne « Sources, vérifiées le … » avec les liens.
- `Recap.astro` : rendu `<section id="recap">`.
  - Il liste les acquis du schéma, chacun sous la forme `<li data-acquis={cle} data-gagne="non">`. Le script passe l'attribut à `"oui"` quand l'acquis est gagné. Tant que l'acquis n'est pas gagné, la ligne affiche « à gagner … ».
  - Il affiche le total « n sur t » et un bouton « Effacer ma progression pour ce chapitre ».
- `BarreHaut.astro` : rendu dans un `<header>`. `PiedChapitre.astro` : rendu dans un `<footer>`.
- `PiedChapitre.astro` : précédent et suivant via `voisins()`. Un chapitre sans fichier MDX s'affiche « à venir », sans lien.
- **Typographie des props :** les composants appliquent `typographier()` à leurs props de texte (`titre`, `question`, `precision`, `message`, `chapeau`, textes des acquis). Le plugin remark ne voit que le texte MDX, pas les attributs.
- **Comportement de `chapitre.ts`**, sur chaque page qui contient `article[data-chapitre]` :
  1. Il appelle `nettoyer()` avec les paris de la page.
  2. Il restaure les paris déjà faits, les acquis, les étapes et les verrous ouverts.
  3. Au clic sur un choix :
     - les boutons sont désactivés ;
     - le bon choix est marqué « bonne réponse », ou « ton choix, juste » ;
     - le choix faux est marqué « ton choix » ;
     - le verdict commence par « Juste. » (menthe) ou par « Pas tout à fait. » (corail), suivi de l'explication ;
     - appels à `noterPari`, à `noterAcquis` si `data-acquis` est présent, et à `ouverture(ouvre).set(true)` si `data-ouvre` est présent.
  4. Une étape est faite quand tous ses paris sont répondus. Si elle n'a pas de pari, elle est faite quand sa fin passe au-dessus du milieu de l'écran (IntersectionObserver).
  5. Il écoute `window` sur l'événement `forge:acquis`, dont le détail est `{ cle: string }`, et gagne l'acquis correspondant.
  6. Il tient à jour la barre du haut (étapes faites ou en cours, pastilles d'acquis) et le récapitulatif.
  7. Le bouton « Effacer » appelle `effacer(numero)`, puis recharge la page.
- **`playwright.config.ts` :**
  - `webServer.command : 'npm run build:essais && npm run preview -- --port 8531'` ;
  - `url : 'http://127.0.0.1:8531/forge-ia/'` ;
  - `use.baseURL : 'http://127.0.0.1:8531'` ;
  - `channel : process.env.CI ? undefined : 'chrome'` ;
  - deux projets : `ordinateur` (1440 × 900) et `mobile` (390 × 844).
- **`e2e/outils.ts` :** `verifierAxe(page)`, qui échoue sur toute violation wcag2a ou wcag2aa, et `verifierSansDebordement(page)`, qui vérifie `scrollWidth <= innerWidth`.
- **La page d'essai `/forge-ia/essais/gabarit/`** contient :
  - deux étapes ;
  - un pari `p1` (choix A, B juste, C ; `acquis="a1"` ; `ouvre="zone"`) ;
  - un pari `p2` (choix X juste, Y ; `acquis="a2"`) ;
  - un `Verrou nom="zone"` qui enveloppe un bouton « Dedans » ;
  - un `EncadreLabo` ;
  - le frontmatter d'un faux chapitre 1.3, avec trois acquis : `a1`, `a2` et `fusions`. Le troisième sert à l'atelier de la tâche 8.

- [ ] **Étape 1 : écrire les tests qui échouent** dans `e2e/gabarit.spec.ts`, pour chacun des deux projets.

```ts
test('pari juste : verdict, boutons figés, acquis, verrou ouvert', async ({ page }) => {
  await page.goto('/forge-ia/essais/gabarit/');
  await expect(page.locator('[data-verrou="zone"]')).toHaveAttribute('inert', '');
  await page.locator('[data-pari="p1"] [data-juste]').click();
  await expect(page.locator('[data-pari="p1"] .verdict')).toContainText('Juste.');
  await expect(page.locator('[data-pari="p1"] button').first()).toBeDisabled();
  await expect(page.locator('[data-verrou="zone"]')).not.toHaveAttribute('inert', '');
  await expect(page.locator('#recap')).toContainText('1 sur 3');
  await expect(page.locator('#recap [data-acquis="a1"]')).toHaveAttribute('data-gagne', 'oui');
});
test('pari faux : « Pas tout à fait. » et bonne réponse signalée', async ({ page }) => {
  await page.goto('/forge-ia/essais/gabarit/');
  await page.locator('[data-pari="p2"] button:not([data-juste])').click();
  await expect(page.locator('[data-pari="p2"] .verdict')).toContainText('Pas tout à fait.');
  await expect(page.locator('[data-pari="p2"] [data-juste]')).toContainText('bonne réponse');
});
test('rechargement et lien direct : pari et verrou restaurés', async ({ page }) => {
  await page.goto('/forge-ia/essais/gabarit/');
  await page.locator('[data-pari="p1"] [data-juste]').click();
  await page.goto('/forge-ia/essais/gabarit/#etape-2');
  await expect(page.locator('[data-pari="p1"] .verdict')).toContainText('Juste.');
  await expect(page.locator('[data-verrou="zone"]')).not.toHaveAttribute('inert', '');
});
test('effacer la progression', async ({ page }) => {
  await page.goto('/forge-ia/essais/gabarit/');
  await page.locator('[data-pari="p1"] [data-juste]').click();
  await page.getByRole('button', { name: 'Effacer ma progression pour ce chapitre' }).click();
  await expect(page.locator('[data-pari="p1"] [data-juste]')).toBeEnabled();
});
test('sans JavaScript : tout est lisible, rien de verrouillé', async ({ browser }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false });
  const page = await ctx.newPage();
  await page.goto('http://127.0.0.1:8531/forge-ia/essais/gabarit/');
  await expect(page.locator('[data-verrou="zone"]')).not.toHaveAttribute('inert', '');
  await expect(page.getByText('Dedans')).toBeVisible();
});
test('accessibilité et largeur', async ({ page }) => {
  await page.goto('/forge-ia/essais/gabarit/');
  await verifierAxe(page); await verifierSansDebordement(page);
});
```

- [ ] **Étape 2 : lancer les tests et vérifier qu'ils échouent.** Commande : `cd site; npx playwright test e2e/gabarit.spec.ts`. Attendu : échec, la page d'essai n'existe pas (404).
- [ ] **Étape 3 : écrire le schéma, les composants, `chapitre.ts`, les routes et la page d'essai.**
  - Le rendu suit `docs/maquettes/maquette-10-fusion-energie.html` : mêmes proportions, barre du haut, grands numéros, blocs de pari, verdicts, récapitulatif et pied.
  - La barre du haut est **opaque**, pour corriger le défaut de transparence noté dans la maquette.
  - La route `[partie]/[chapitre].astro` produit `partie-<p>/<p>-<n>/` pour chaque fichier de la collection.
- [ ] **Étape 4 : lancer les tests et vérifier qu'ils passent.** Commande : `npx playwright test e2e/gabarit.spec.ts`. Attendu : tous les tests passent sur `ordinateur` et sur `mobile`.
- [ ] **Étape 5 : commit**, message « Gabarit de chapitre : étapes, paris, verrous, progression ».

### Tâche 6 : code expliqué et liens vers le projet

**Fichiers :**

- Créer : `site/src/lib/regions.ts`, test `site/src/lib/regions.test.ts`
- Créer : `site/src/components/gabarit/CodeExplique.astro`, `site/src/components/gabarit/LiensProjet.astro`
- Modifier : `site/src/essais/gabarit.mdx` (ajout d'un `CodeExplique` sur la région `choisir`)
- Test : `site/e2e/code.spec.ts`

**Interfaces :**

- Consomme : les marqueurs `# region: <nom>` et `# fin: <nom>` des fichiers Python (tâche 2).
- Produit :
  - `extraireRegion(source: string, nom: string, fichier = '?'): string` : renvoie les lignes entre les deux marqueurs. Les lignes de marqueurs, y compris celles d'autres régions imbriquées, sont retirées. L'indentation commune est enlevée. Si la région est introuvable ou non fermée, la fonction lève `Région introuvable : <nom> dans <fichier>`.
  - `CodeExplique.astro` : props `{ fichier: string /* chemin depuis la racine du dépôt */; region: string; langue?: string /* défaut 'python' */ }`.
    - Le slot par défaut est une liste de `<li data-lignes="2-3">explication</li>`.
    - Le composant lit le fichier au moment de la construction et le colore avec le composant `Code` d'Astro (Shiki), chaque ligne portant `data-l`.
    - Il affiche le chemin du fichier, avec un lien vers `https://github.com/chipat-neko/forge-ia/blob/main/<fichier>`.
    - Le survol ou le focus d'un `li` allume ses lignes, en fond soleil pâle.
  - `LiensProjet.astro` : props `{ projet: string /* ex. '1.3-tokenizer' */ }`. Il affiche deux liens :
    - `https://github.com/chipat-neko/forge-ia/tree/main/projets/<projet>` (« Le projet complet ») ;
    - `https://colab.research.google.com/github/chipat-neko/forge-ia/blob/main/notebooks/<projet>.ipynb` (« Ouvrir dans Colab »).

- [ ] **Étape 1 : écrire les tests qui échouent.**

```ts
// regions.test.ts
const src = 'a\n    # region: r\n    def f():\n        return 1\n    # fin: r\nb';
expect(extraireRegion(src, 'r')).toBe('def f():\n    return 1');
expect(() => extraireRegion(src, 'absente', 'x.py')).toThrow('Région introuvable : absente dans x.py');
// e2e/code.spec.ts : le code affiché est identique à la région du fichier testé
const attendu = extraireRegion(readFileSync('../projets/1.3-tokenizer/tokenizer_pedagogique/bpe.py', 'utf8'), 'choisir');
await expect(page.locator('.code-explique pre')).toHaveText(attendu);
await page.locator('.code-explique li').first().hover();
await expect(page.locator('.code-explique [data-l].allumee')).not.toHaveCount(0);
```

- [ ] **Étape 2 : lancer les tests et vérifier qu'ils échouent.** Commandes : `npx vitest run src/lib/regions.test.ts`, puis `npx playwright test e2e/code.spec.ts`. Attendu : échec.
- [ ] **Étape 3 : écrire `regions.ts`, `CodeExplique.astro` et `LiensProjet.astro`.** Le thème Shiki est choisi ou réglé pour s'accorder à la direction B : fond brume claire, encre indigo, mots-clés en indigo doux. Pas de thème sombre générique.
- [ ] **Étape 4 : lancer les tests et vérifier qu'ils passent.**
- [ ] **Étape 5 : commit**, message « Code expliqué tiré des fichiers testés, liens projet et Colab ».

### Tâche 7 : moteur BPE TypeScript, jumeau exact du Python

**Fichiers :**

- Créer : `site/src/lib/bpe.ts`
- Test : `site/src/lib/bpe.test.ts`

**Interfaces :**

- Consomme : `projets/1.3-tokenizer/donnees/corpus.txt` (import `?raw`) et `projets/1.3-tokenizer/tests/attendus.json`, tous deux de la tâche 2.
- Produit :
  - `preDecouper(texte: string): string[]`, avec le même motif que le Python et le drapeau `u` ;
  - `interface Fusion { a: string; b: string; compte: number }` ;
  - `apprendre(corpus: string, nbFusions: number): Fusion[]` ;
  - `interface Jeton { texte: string; id: number | null; mot: number }` ;
  - `class TokenizerPedagogique { constructor(corpus: string, nbFusionsMax = 200); readonly fusions: Fusion[]; readonly base: string[]; decouper(texte: string, k: number): Jeton[] }` ;
  - `tokenizer13: TokenizerPedagogique`, construit une seule fois sur le corpus ;
  - `visible(s: string): string`, qui remplace l'espace par `␣` et le retour à la ligne par `↵` ;
  - `choixNombreDeJetons(texte: string, k: number): { texte: string; juste: boolean }[]` : trois choix, triés par ordre croissant. Le nombre de pré-mots contenant une lettre, le nombre exact de jetons (juste) et le nombre de caractères (points de code), chacun sous la forme « N jetons ». Si deux valeurs sont égales, la fonction lève une erreur pour que l'auteur choisisse un autre exemple.
- Les comparaisons de paires et le tri de `base` se font **par point de code**, comme Python, et non par unité UTF-16.

- [ ] **Étape 1 : écrire les tests qui échouent.**

```ts
import attendus from '../../../projets/1.3-tokenizer/tests/attendus.json';
expect(apprendre(corpus, 200).map(f => [f.a, f.b, f.compte])).toEqual(attendus.fusions);
for (const c of attendus.cas)
  expect(tokenizer13.decouper(c.texte, c.k).map(j => [j.texte, j.id, j.mot])).toEqual(c.jetons);
expect(choixNombreDeJetons('les forgerons', 30)).toEqual([
  { texte: '2 jetons', juste: false }, { texte: '9 jetons', juste: true }, { texte: '13 jetons', juste: false }]);
expect(tokenizer13.decouper('', 30)).toEqual([]);
const long = 'Le forgeron frappe le métal. '.repeat(345); // ~10 000 caractères
const t0 = performance.now(); tokenizer13.decouper(long, 165);
expect(performance.now() - t0).toBeLessThan(500);
// tri par point de code : '\u{1F642}' (🙂) vient après '\uFFFD'
expect(['\u{1F642}', '\uFFFD'].sort(comparerPointsDeCode)).toEqual(['\uFFFD', '\u{1F642}']);
```

`comparerPointsDeCode(a: string, b: string): number` est exporté par `bpe.ts`.

- [ ] **Étape 2 : lancer les tests et vérifier qu'ils échouent.** Commande : `npx vitest run src/lib/bpe.test.ts`. Attendu : échec.
- [ ] **Étape 3 : écrire `bpe.ts`.**
- [ ] **Étape 4 : lancer les tests et vérifier qu'ils passent.** Attendu : les attendus Python et TS sont identiques sur toutes les fusions et tous les cas.
- [ ] **Étape 5 : commit**, message « Moteur BPE TypeScript identique au Python ».

### Tâche 8 : nombre manipulable et atelier du tokenizer (Svelte)

**Fichiers :**

- Créer : `site/src/components/interactif/NombreManipulable.svelte`
- Créer : `site/src/components/chapitres/1-3/AtelierTokenizer.svelte`, `site/src/components/chapitres/1-3/PhraseDecoupee.astro`
- Modifier : `site/src/essais/gabarit.mdx` (ajout de l'atelier derrière le verrou `zone`)
- Test : `site/e2e/atelier.spec.ts`

**Interfaces :**

- Consomme : `canal()` et `ouverture()` (tâche 4), `tokenizer13` et `visible()` (tâche 7), l'événement `forge:acquis` (tâche 5).
- `NombreManipulable.svelte` : props `{ canal: string; min: number; max: number; initiale: number; etiquette: string; pas?: number; verrou?: string; testId?: string }`.
  - Rendu en ligne dans la phrase, sous forme de pastille jaune soleil, avec `role="slider"`, `aria-valuemin`, `aria-valuemax`, `aria-valuenow`, `aria-label={etiquette}` et `data-test={testId}`.
  - Clavier : `Home` ramène au minimum, `End` va au maximum, les flèches font ±`pas`, `PageUp` et `PageDown` font ±10.
  - Glisser à la souris ou au doigt : une unité tous les 6 px horizontaux.
  - Tant que `ouverture(verrou)` est faux, le nombre est désactivé : `tabindex="-1"` et `aria-disabled="true"`.
- `AtelierTokenizer.svelte` : props `{ phraseInitiale: string; canalFusions?: string /* défaut 'fusions' */; verrou?: string; acquisA?: number /* défaut 60 */ }`.
  - Il affiche :
    - un champ `data-test="saisie"` ;
    - la phrase « Avec [NombreManipulable canal=canalFusions min 0 max tokenizer13.fusions.length testId="fusions"] fusions apprises, ses N caractères tiennent en M jetons » ;
    - le conteneur `data-test="jetons"`, dont chaque jeton porte `data-jeton` (couleurs alternées `--teinte-a` et `--teinte-b`, numéro dessous, « inconnu » si `id === null`) ;
    - une bascule « cacher les morceaux » et « voir les morceaux » ;
    - les trois dernières fusions, au format « fusion 30 : é + c → éc » ;
    - la comparaison « lettre par lettre : X ; mot par mot : Y ».
  - Champ vide : le message « Tape une phrase pour la voir découpée. » s'affiche, sans erreur.
  - Quand le nombre de fusions atteint `acquisA`, le composant émet une fois `forge:acquis` avec `{ cle: 'fusions' }`.
- `PhraseDecoupee.astro` : props `{ phrase: string; k: number }`. Rendu calculé au moment de la construction : les jetons avec leurs numéros dessous et une légende « « … », tel que le modèle le reçoit : N morceaux, donc N nombres. ».

- [ ] **Étape 1 : écrire les tests qui échouent** dans `e2e/atelier.spec.ts` (page d'essai, après le pari `p1`).

```ts
await page.locator('[data-pari="p1"] [data-juste]').click();
await page.locator('[data-test="saisie"]').fill('Les forgerons découpent le texte en jetons.');
const f = page.locator('[data-test="fusions"]'); await f.focus(); await page.keyboard.press('Home');
await expect(page.locator('[data-test="jetons"] [data-jeton]')).toHaveCount(43);
for (let i = 0; i < 60; i++) await page.keyboard.press('ArrowRight');
await expect(page.locator('[data-test="jetons"] [data-jeton]')).toHaveCount(18);
await expect(page.locator('#recap [data-acquis="fusions"]')).toHaveAttribute('data-gagne', 'oui'); // gagné à 60
await page.locator('[data-test="saisie"]').fill('Salut 🙂');
await expect(page.locator('[data-test="jetons"]')).toContainText('inconnu');
await page.locator('[data-test="saisie"]').fill('');
await expect(page.getByText('Tape une phrase pour la voir découpée.')).toBeVisible();
// avant le pari, le nombre est désactivé
// (nouveau contexte) await expect(f).toHaveAttribute('aria-disabled', 'true');
```

Le test « avant le pari » s'écrit à part, dans un contexte neuf, sans progression. L'acquis `fusions` est déjà déclaré dans le frontmatter de la page d'essai (tâche 5).

- [ ] **Étape 2 : lancer les tests et vérifier qu'ils échouent.** Commande : `npx playwright test e2e/atelier.spec.ts`. Attendu : échec.
- [ ] **Étape 3 : écrire les trois composants.** L'allure suit la maquette 10 (atelier, bande de jetons, phrase de fusions). Le jaune soleil est réservé au nombre manipulable, au champ de saisie et à la bascule.
- [ ] **Étape 4 : lancer les tests et vérifier qu'ils passent** (ordinateur et mobile), en relançant aussi `e2e/gabarit.spec.ts`.
- [ ] **Étape 5 : commit**, message « Atelier du tokenizer et nombre manipulable ».

### Tâche 9 : chapitre 1.3 rédigé

**Fichiers :**

- Créer : `site/src/content/chapitres/1-3.mdx`
- Test : `site/e2e/chapitre-1-3.spec.ts`
- Modifier : `site/e2e/outils.ts`, pour ajouter `terminerChapitre13(page)`. Cette aide fait les 4 paris et pousse l'atelier à 60 fusions ; elle sert aussi en tâche 12.

**Interfaces :**

- Consomme : tous les composants des tâches 5 à 8, `choixNombreDeJetons` et `tokenizer13`.

**Contenu imposé :** le texte et la structure de la maquette 10, soit 7 étapes et 4 paris. Les identifiants et les acquis sont les suivants :

| Pari | Clé d'acquis | Particularité |
| --- | --- | --- |
| `nombres` | `nombres` | |
| `prediction` | `prediction` | `ouvre="atelier"`, choix calculés par `choixNombreDeJetons('les forgerons', 30)` |
| `rare` | `rare` | « Avec les 165 fusions, le mot rare « reforgeronnes » devient-il un seul jeton ? ». Choix « Oui » et « Non » ; le bon est calculé : Non, car il donne 6 jetons. |
| `zip` | `zip` | Question sur ce que produit `zip(symboles, symboles[1:])` |

S'y ajoute l'acquis `fusions`, gagné dans l'atelier à 60 fusions, sous le verrou `atelier`.

Changements par rapport à la maquette :

- **Le code :** l'étape du code montre deux `CodeExplique`, sur les régions `compter` et `choisir` du fichier `projets/1.3-tokenizer/tokenizer_pedagogique/bpe.py`. Les explications ligne par ligne reprennent celles du brief, avec une ligne de plus sur le départage : « En cas d'égalité, on prend la paire la plus petite dans l'ordre alphabétique : le résultat est ainsi toujours le même, sur ton PC comme dans cette page. »
- **L'encadré labo :** avant de l'écrire, faire une recherche web pour vérifier la taille du vocabulaire d'au moins trois grands tokenizers actuels. Citer ces sources avec la date du jour dans `EncadreLabo sources`.
- **Le défi** est gardé : 30 caractères ou plus en 12 jetons ou moins, vérifié en direct dans l'atelier.
- **La fin du chapitre :** `LiensProjet projet="1.3-tokenizer"`, puis une note « À suivre ». Elle annonce que ce découpeur pédagogique travaille sur les lettres, et que celui de ton IA, construit dans la suite de ce chapitre, travaillera sur les octets et prévoira les jetons spéciaux de la conversation et des outils.

- [ ] **Étape 1 : écrire les tests qui échouent.**

```ts
test('chapitre 1.3 complet', async ({ page }) => {
  await page.goto('/forge-ia/partie-1/1-3/');
  await expect(page.locator('header')).toContainText('Partie 1, chapitre 1.3 sur 21');
  await expect(page.getByRole('heading', { level: 2, name: /Pourquoi découper\u202F\?/ })).toBeVisible();
  await expect(page.locator('[data-pari="prediction"] button')).toHaveText([/2 jetons/, /9 jetons/, /13 jetons/]);
  await page.locator('[data-pari="nombres"] [data-juste]').click();
  await page.locator('[data-pari="prediction"] [data-juste]').click();
  await page.locator('[data-test="fusions"]').focus();
  for (let i = 0; i < 60; i++) await page.keyboard.press('ArrowRight');
  await page.locator('[data-pari="rare"] [data-juste]').click();
  await page.locator('[data-pari="zip"] [data-juste]').click();
  await expect(page.locator('#recap')).toContainText('5 sur 5');
  await expect(page.locator('footer')).toContainText('à venir'); // 1.2 et 1.4 pas encore écrits
  await verifierAxe(page); await verifierSansDebordement(page);
});
```

- [ ] **Étape 2 : lancer le test et vérifier qu'il échoue.** Commande : `npx playwright test e2e/chapitre-1-3.spec.ts`. Attendu : échec (404).
- [ ] **Étape 3 : faire la recherche web, puis écrire `1-3.mdx`.**
- [ ] **Étape 4 : lancer tous les tests et vérifier qu'ils passent.** Commandes : `npx vitest run`, puis `npx playwright test`. Attendu : tout passe.
- [ ] **Étape 5 : faire des captures et les relire.** Prendre des captures ordinateur et mobile du chapitre, les comparer à la maquette 10 avec l'outil de lecture d'images, et corriger les écarts visibles.
- [ ] **Étape 6 : commit**, message « Chapitre 1.3 : le tokenizer ».

### Tâche 10 : notebook Colab du chapitre 1.3

**Fichiers :**

- Créer : `notebooks/1.3-tokenizer.ipynb`
- Créer : `projets/1.3-tokenizer/tests/test_notebook.py`
- Modifier : `projets/1.3-tokenizer/pyproject.toml` (groupe de développement : `nbclient`, `nbformat`, `ipykernel`)

**Interfaces :**

- Consomme : le paquet `tokenizer_pedagogique` (tâche 2).
- **Contrat du notebook :**
  - La première cellule de code récupère le dépôt. Si la variable d'environnement `FORGE_IA_LOCAL` est définie, elle utilise ce chemin. Sinon, elle exécute `git clone --depth 1 https://github.com/chipat-neko/forge-ia`.
  - Elle installe ensuite `regex` et ajoute `projets/1.3-tokenizer` au chemin d'import.
  - Les cellules suivantes, en français pour débutants, apprennent les fusions, découpent la phrase de l'atelier pour k = 0, 30 et 60, puis affichent « 18 jetons » pour « Les forgerons découpent le texte en jetons. » avec 60 fusions.
  - Un exercice est proposé, avec sa correction repliée.
  - La dernière cellule compare le résultat à `tests/attendus.json` et affiche « Même résultat que la page du site : oui ».

- [ ] **Étape 1 : écrire le test qui échoue.**

```python
def test_notebook_s_execute_de_bout_en_bout(monkeypatch):
    racine = pathlib.Path(__file__).resolve().parents[3]
    monkeypatch.setenv("FORGE_IA_LOCAL", str(racine))
    nb = nbformat.read(racine / "notebooks" / "1.3-tokenizer.ipynb", as_version=4)
    NotebookClient(nb, timeout=120, kernel_name="python3").execute()
    sorties = "".join(o.get("text", "") for c in nb.cells if c.cell_type == "code" for o in c.get("outputs", []))
    assert "18 jetons" in sorties
    assert "Même résultat que la page du site : oui" in sorties
```

- [ ] **Étape 2 : lancer le test et vérifier qu'il échoue.** Commande : `uv run pytest tests/test_notebook.py -q`. Attendu : échec, le fichier est introuvable.
- [ ] **Étape 3 : écrire le notebook.**
- [ ] **Étape 4 : lancer tous les tests du projet et vérifier qu'ils passent.** Commande : `uv run pytest -q`.
- [ ] **Étape 5 : commit**, message « Notebook Colab du chapitre 1.3 ».

### Tâche 11 : maquettes de l'accueil, des pages de partie, de la recherche et de la 404, à faire valider (porte)

**Fichiers :**

- Créer : `docs/maquettes/accueil-a.html`, `docs/maquettes/accueil-b.html`, `docs/maquettes/partie.html`, `docs/maquettes/recherche.html`, `docs/maquettes/404.html`

**Contraintes :**

- Direction B, contraintes globales, et skill frontend-design.
- **L'accueil** montre le parcours entier : 4 parties, 34 chapitres et les annexes. La Partie 1 est mise en avant. Chaque chapitre est marqué disponible, à venir ou fait (progression). La version A s'inspire de la carte du parcours de la maquette 7, fondue dans la direction B. La version B est une table des matières d'ouvrage.
- **Le haut de l'accueil** montre tout de suite l'objet du site, par exemple une phrase découpée en jetons ou un pari, et non une accroche commerciale.

- [ ] **Étape 1 : construire les maquettes** (HTML autonome, polices de `site/node_modules/@fontsource*`). Les montrer à l'utilisateur dans le compagnon visuel du skill brainstorming : lancer le serveur, puis l'arrêter ensuite.
- [ ] **Étape 2 : demander la validation** avec AskUserQuestion : laquelle des deux versions d'accueil, et les pages partie, recherche et 404 conviennent-elles ? **Ne pas commencer la tâche 12 sans cette validation.** Si l'utilisateur demande des changements, refaire les maquettes concernées et redemander.
- [ ] **Étape 3 : commit** des maquettes validées, message « Maquettes validées : accueil, partie, recherche, 404 ».

### Tâche 12 : accueil, pages de partie, recherche et 404

**Fichiers :**

- Modifier : `site/src/pages/index.astro`
- Créer : `site/src/pages/[partie]/index.astro`, `site/src/pages/recherche.astro`, `site/src/pages/404.astro`
- Créer : `site/src/lib/recherche.ts` (enveloppe de l'API JavaScript de Pagefind)
- Test : `site/e2e/navigation.spec.ts`

**Interfaces :**

- Consomme : `PARCOURS`, `hrefChapitre`, la collection `chapitres` (disponibilité) et `lireChapitre`. Un chapitre est « fait » si tous ses acquis sont gagnés.
- `recherche.ts` : `chercher(requete: string): Promise<{ titre: string; url: string; extrait: string }[]>`. Il charge `${BASE_URL}pagefind/pagefind.js` à la demande. La page recherche a sa propre interface, dans la direction B, et non l'interface par défaut de Pagefind.
- Les pages de chapitre marquent leur contenu avec `data-pagefind-body`. La barre du haut et le pied en sont exclus.

- [ ] **Étape 1 : écrire les tests qui échouent.**

```ts
test('accueil : 34 chapitres, 1.3 disponible', async ({ page }) => {
  await page.goto('/forge-ia/');
  await expect(page.locator('[data-chapitre-carte]')).toHaveCount(34);
  await page.locator('[data-chapitre-carte="1.3"] a').click();
  await expect(page).toHaveURL(/\/forge-ia\/partie-1\/1-3\/$/);
});
test('page de partie', async ({ page }) => {
  await page.goto('/forge-ia/partie-1/');
  await expect(page.locator('[data-chapitre-carte]')).toHaveCount(21);
});
test('recherche', async ({ page }) => {
  await page.goto('/forge-ia/recherche/');
  await page.getByRole('searchbox').fill('fusions');
  await expect(page.locator('[data-resultat]').first()).toContainText('tokenizer');
});
test('404', async ({ page }) => {
  const r = await page.goto('/forge-ia/nimporte-quoi/');
  expect(r?.status()).toBe(404);
  await expect(page.getByRole('link', { name: /accueil/i })).toBeVisible();
});
test('progression visible sur l’accueil', async ({ page }) => {
  // faire les 4 paris et pousser à 60 fusions sur 1.3 (aide partagée avec chapitre-1-3.spec.ts), puis :
  await page.goto('/forge-ia/');
  await expect(page.locator('[data-chapitre-carte="1.3"]')).toHaveAttribute('data-etat', 'fait');
});
```

Tous les tests se terminent par `verifierAxe` et `verifierSansDebordement`.

- [ ] **Étape 2 : lancer les tests et vérifier qu'ils échouent.**
- [ ] **Étape 3 : construire les pages selon les maquettes validées.**
- [ ] **Étape 4 : lancer toute la suite et vérifier qu'elle passe.** Commandes : `npx vitest run`, puis `npx playwright test`.
- [ ] **Étape 5 : commit**, message « Accueil, pages de partie, recherche et 404 ».

### Tâche 13 : intégration continue et publication sur GitHub Pages

**Fichiers :**

- Créer : `.github/workflows/site.yml`, `.github/workflows/python.yml`
- Modifier : `README.md` (badge de l'état de construction, lien vers le site)

**Interfaces :**

- **`site.yml`** se déclenche sur `push` vers `main` et sur `pull_request`.
  - **Tâche `tests` :** Node 24, puis `npm ci` dans `site/`, `npx vitest run`, `npx playwright install --with-deps chromium`, `npx playwright test`. Le rapport Playwright est envoyé en artefact en cas d'échec.
  - **Tâche `deploiement`,** seulement sur `push` vers `main` et après `tests` : `npm run build`, puis `actions/upload-pages-artifact` (dossier `site/dist`) et `actions/deploy-pages`. Permissions : `pages: write` et `id-token: write`.
- **`python.yml`** se déclenche sur `push` et `pull_request` qui touchent `projets/**` ou `notebooks/**`. Il utilise `astral-sh/setup-uv`, puis lance `uv run pytest -q` dans chaque dossier de `projets/` contenant un `pyproject.toml`, sur `ubuntu-latest` et `windows-latest`.

- [ ] **Étape 1 : activer Pages en mode « GitHub Actions ».** Commande : `gh api -X POST repos/chipat-neko/forge-ia/pages -f build_type=workflow`. Si Pages existe déjà, utiliser `-X PUT`.
- [ ] **Étape 2 : écrire les deux workflows, pousser et suivre l'exécution.** Commande : `gh run watch`. Attendu : `site.yml` et `python.yml` sont verts.
- [ ] **Étape 3 : vérifier le site en ligne.** Commandes : `curl -s -o NUL -w "%{http_code}" https://chipat-neko.github.io/forge-ia/` (attendu : `200`) et `curl -s https://chipat-neko.github.io/forge-ia/partie-1/1-3/` (attendu : contient « Le tokenizer »). Relancer `e2e/chapitre-1-3.spec.ts` contre l'adresse publique avec `PLAYWRIGHT_BASE_URL`, une variable que `playwright.config.ts` doit accepter. S'il est fixé, le `webServer` est ignoré.
- [ ] **Étape 4 : commit** (README et workflows), message « Intégration continue et publication GitHub Pages ».

### Tâche 14 : clôture du plan 1 (contrôle Colab, mémoire, compte rendu)

**Fichiers :**

- Créer : `docs/verifications/colab.md`, le tableau des notebooks vérifiés sur Colab, avec les colonnes notebook, date, durée, résultat, vérifié par.

- [ ] **Étape 1 : remettre la liste Colab à l'utilisateur.** Elle tient en une ligne : le lien Colab du notebook 1.3, une durée attendue de moins de 2 minutes, et le résultat attendu « 18 jetons » puis « Même résultat que la page du site : oui ». Demander à l'utilisateur, avec AskUserQuestion, de le lancer et de dire si tout s'affiche comme prévu.
- [ ] **Étape 2 : consigner le résultat** dans `docs/verifications/colab.md`. Si le notebook a échoué sur Colab, corriger, repousser, puis redemander à l'utilisateur.
- [ ] **Étape 3 : écrire le jalon dans la mémoire partagée** : « Projet forge-ia (La Forge IA) : site Astro publié sur <https://chipat-neko.github.io/forge-ia/>, dépôt chipat-neko/forge-ia ; premier chapitre en ligne (1.3, le tokenizer) ». C'est un jalon livré, au sens du CLAUDE.md global.
- [ ] **Étape 4 : demander la validation du pilote** à l'utilisateur, avec AskUserQuestion, en lui montrant l'adresse publique et des captures mobile et ordinateur. Lui proposer ensuite d'écrire le plan 2 (paquet `forge` et chaîne de ton IA).
- [ ] **Étape 5 : commit**, message « Vérification Colab du chapitre 1.3 ».
