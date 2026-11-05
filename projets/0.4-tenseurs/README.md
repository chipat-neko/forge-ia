# Les tenseurs

Les nombres d'une IA sont rangés dans des tenseurs : des tableaux de 0, 1, 2,
3 dimensions ou plus. Ce projet crée des tenseurs avec PyTorch, les lit,
calcule avec, et donne en Python pur les deux règles qui disent quelle forme
aura un résultat : la diffusion (`a + b`) et le produit matriciel (`a @ b`).
Il compte la mémoire d'un tenseur, et chronomètre un produit de matrices sur
le processeur, et sur la carte graphique si elle est là.

C'est le projet de l'étape 0.4 de La Forge IA, « Les tenseurs ». Comme le
projet 0.3, il utilise PyTorch, en deux versions au choix : celle pour carte
NVIDIA (extra `gpu`, CUDA 13.2) et celle pour le processeur seul (extra
`cpu`).

## Installer uv

`uv` installe Python et les bibliothèques de chaque projet. Le fichier
`.python-version` demande Python 3.12 : uv le télécharge lui-même s'il manque.
Pour installer uv, voir le README du projet 0.3 (`projets/0.3-poste`), ou
https://docs.astral.sh/uv/getting-started/installation/.

## Lancer

Récupère le dépôt, puis va dans le dossier du projet. Les commandes sont les
mêmes dans PowerShell (Windows) et dans un terminal (Linux, Mac) :

```bash
git clone https://github.com/chipat-neko/forge-ia
cd forge-ia/projets/0.4-tenseurs
```

Dans les commandes qui suivent, `--extra cpu` prend la version de PyTorch pour
le processeur. Avec une carte NVIDIA, mets `--extra gpu` : la première fois,
uv télécharge cette version, plusieurs gigaoctets.

### Les règles de forme

```bash
uv run --extra cpu python -m tenseurs formes "(3, 1)" "(4,)"
```

Le script dit ce que donnent `a + b` et `a @ b` pour ces deux formes, ou
pourquoi c'est impossible :

```text
Diffusion : (3, 1) + (4,) donne (3, 4).
Produit matriciel : (3, 1) @ (4,) est impossible : la dernière dimension de gauche, 1, n’est pas l’avant-dernière de droite, 4 (la seule d’un vecteur).
```

Écris les formes comme Python, entre guillemets : `"(2, 3)"`, `"(4,)"` pour
un vecteur (la virgule dit que c'est un tuple), `"()"` pour un nombre seul.
Cette commande n'a pas besoin de PyTorch : les règles sont dans
`tenseurs/formes.py`, en Python pur, et les tests les comparent à PyTorch
lui-même.

### Les chronos

```bash
uv run --extra cpu python -m tenseurs mesurer --appareil cpu
uv run --extra gpu python -m tenseurs mesurer --appareil cuda
```

Le script chronomètre le produit de deux matrices de 64 × 64 à 4 096 × 4 096
nombres, en float32. Sur le processeur, il le fait avec 1 fil, avec le
réglage par défaut de PyTorch, puis avec tous les fils du processeur. Sur la
carte, il mesure aussi la copie de chaque matrice vers la carte. Chaque durée
est la médiane de 5 produits, après 2 produits pour rien qui préparent le
calcul.

- `--sortie FICHIER` écrit aussi les mesures dans FICHIER, en JSON (UTF-8) ;
- `--tailles 64 256` choisit d'autres tailles ;
- sans `--appareil`, le script suit la variable `FORGE_APPAREIL`, sinon prend
  la carte si PyTorch la voit, sinon le processeur.

Demander `--appareil cuda` sans carte visible donne un message qui dit quoi
faire, pas une trace Python, et le code de sortie 2.

## Les mesures du PC de La Forge IA

Le chapitre 0.4 montre les chronos du PC de La Forge IA (processeur AMD Ryzen
7 9800X3D, 16 fils ; carte RTX 5070 Ti). Ils sont dans `mesures/` :

- `mesures/processeur.json`, écrit par
  `uv run --extra cpu python -m tenseurs mesurer --appareil cpu --sortie mesures/processeur.json`.
  **Ces chronos sont provisoires** : ils ont été relevés pendant que la carte
  entraînait une IA, et le processeur en faisait un peu pour elle. Ils seront
  remesurés à la porte de la Partie 0, machine au repos ;
- `mesures/rtx-5070-ti.json`, la carte, mesurée seulement à la porte, avec
  `uv run --extra gpu python -m tenseurs mesurer --appareil cuda --sortie mesures/rtx-5070-ti.json`.
  Tant qu'il manque, le chapitre affiche « à mesurer ».

Le format (version 1) :

```json
{
 "version": 1,
 "releve_le": "2026-11-05",
 "appareil": "cpu",
 "nom": "AMD Ryzen 7 9800X3D 8-Core Processor",
 "torch": "2.15.0+cpu",
 "fils_par_defaut": 8,
 "fils_max": 16,
 "mesures": [{"taille": 64, "fils": 1, "millisecondes": 0.01}],
 "transfert_ms": null
}
```

Sur la carte, `appareil` vaut `cuda`, `fils` vaut `null`, et `transfert_ms`
donne la copie vers la carte, en millisecondes, pour chaque taille :
`{"64": …, "4096": …}`.

## Choisir l'appareil

`tenseurs/appareil.py` est une copie exacte de celui du projet 0.3 : un test
le vérifie quand le dépôt entier est là. `choisir_appareil()` dit où
calculer : l'argument, sinon la variable `FORGE_APPAREIL`, sinon `auto`, qui
prend la carte si PyTorch la voit, sinon le processeur.

```powershell
$env:FORGE_APPAREIL = "cpu"   # PowerShell
```

```bash
export FORGE_APPAREIL=cpu     # Linux, Mac
```

## Tester

```bash
uv run --extra cpu pytest -q
```

Le test marqué `gpu` (les chronos sur la carte) est sauté sans carte, avec la
raison « CUDA absente ». Avec une carte NVIDIA, `uv run --extra gpu pytest -q`
le lance aussi. Le test du notebook l'exécute de bout en bout, sur la carte si
elle est là.

## Les attendus de référence

Le fichier `tests/attendus-formes.json` contient les formes que donne PyTorch
lui-même (`torch.broadcast_shapes` et `torch.matmul`) pour toutes les formes
de 1 à 3 dimensions de tailles 1 à 3, prises deux à deux : 39 formes, 1 521
paires. Il contient aussi des cas de mémoire et les valeurs des exemples
(`tenseurs/exemples.py`). Le site ne lance pas PyTorch : son jumeau des
formes, `site/src/lib/partie-0/formes.ts`, est comparé à ce fichier. Pour le
régénérer :

```bash
uv run --extra cpu python -m tenseurs.attendus
```

Un test vérifie qu'il est à jour : si PyTorch ou les exemples changent, il
échoue tant que le fichier n'est pas régénéré.

## Le notebook

`notebooks/0.4-tenseurs.ipynb` fait le même parcours dans Colab, avec le
PyTorch déjà installé par Colab : il ne l'installe pas. Il tourne aussi sans
carte, et dit sur quoi il a tourné. Pour avoir une carte dans Colab :
Exécution > Modifier le type d'exécution > GPU.
