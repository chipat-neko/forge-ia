# Un premier réseau

Un neurone à seuil sait imiter les portes logiques ET et OU, mais pas le OU
exclusif. Ce projet le vérifie, puis entraîne un réseau 2-2-1 (2 entrées, 2
neurones cachés, 1 sortie) à sigmoïdes sur le OU exclusif : d'abord à la
main, en Python pur, avec l'erreur et la descente de gradient du chapitre
0.2 ; puis avec PyTorch, en float64, à partir des mêmes poids de départ.
Les dérivées calculées à la main et celles d'autograd sont les mêmes, à
10⁻¹² près.

C'est le projet de l'étape 0.5 de La Forge IA, « Un premier réseau ». Comme
les projets 0.3 et 0.4, il utilise PyTorch, en deux versions au choix :
celle pour carte NVIDIA (extra `gpu`, CUDA 13.2) et celle pour le processeur
seul (extra `cpu`).

## Installer uv

`uv` installe Python et les bibliothèques de chaque projet. Le fichier
`.python-version` demande Python 3.12 : uv le télécharge lui-même s'il manque.
Pour installer uv, voir le README du projet 0.3 (`projets/0.3-poste`), ou
<https://docs.astral.sh/uv/getting-started/installation/>.

## Lancer

Récupère le dépôt, puis va dans le dossier du projet. Les commandes sont les
mêmes dans PowerShell (Windows) et dans un terminal (Linux, Mac) :

```bash
git clone https://github.com/chipat-neko/forge-ia
cd forge-ia/projets/0.5-reseau
```

Dans les commandes qui suivent, `--extra cpu` prend la version de PyTorch pour
le processeur. Avec une carte NVIDIA, mets `--extra gpu` : la première fois,
uv télécharge cette version, plusieurs gigaoctets.

```bash
uv run --extra cpu python -m premier_reseau entrainer --appareil cpu
uv run --extra gpu python -m premier_reseau entrainer --appareil cuda
```

Le script affiche, dans l'ordre :

- le meilleur réglage du neurone à seuil pour chaque porte, cherché sur une
  grille de −2 à 2 par pas de 0,5 (729 réglages) : les 4 points pour ET et
  pour OU, 3 au mieux pour le OU exclusif ;
- l'entraînement à la main : la perte au départ, tous les 500 pas et à la
  fin, puis la réponse du réseau pour chaque point ;
- le plus grand écart entre les dérivées de départ calculées à la main et
  celles de PyTorch ;
- l'entraînement par PyTorch sur l'appareil, sa durée, et le plus grand écart
  de ses poids finaux avec ceux de la main.

Avec `--enregistrer FICHIER`, il écrit aussi sa sortie dans FICHIER (UTF-8),
précédée de la date du relevé. Sans `--appareil`, il suit la variable
`FORGE_APPAREIL`, sinon prend la carte si PyTorch la voit, sinon le
processeur. Demander `--appareil cuda` sans carte visible donne un message qui
dit quoi faire, pas une trace Python, et le code de sortie 2. Sans PyTorch
(sans `--extra`), le script le dit aussi, et rend le code 2.

## Le réseau et son entraînement

- `premier_reseau/neurone.py` : le neurone à seuil, les portes et la grille ;
- `premier_reseau/a_la_main.py` : le réseau 2-2-1 en Python pur, avec
  `math.exp` et `math.log` seulement. `propager` fait traverser le réseau à
  un point, `erreur` est l'entropie croisée binaire, −[y ln p + (1 − y) ln(1 −
  p)], `retropropager` calcule les 9 dérivées de la sortie vers l'entrée, et
  `entrainer` fait 3 000 pas de descente sur les 4 points, avec un taux de 1 ;
- `premier_reseau/avec_pytorch.py` : le même réseau dans PyTorch
  (`nn.Linear`, `nn.Sigmoid`, `nn.BCELoss`, `torch.optim.SGD`), en float64 ;
- `premier_reseau/nombres.py` : les nombres à la française (« 3,1 × 10⁻¹⁷ ») ;
- `premier_reseau/appareil.py` : une copie exacte de celui du projet 0.3,
  qu'un test garde identique quand le dépôt entier est là.

### La graine : 1236, pas 1234

Les 9 poids de départ sont tirés au hasard, entre −1 et 1, par
`random.Random(GRAINE)`. La graine prévue était 1234, mais avec elle le réseau
reste coincé : après 3 000 pas, la perte stagne vers 0,35, et le réseau
répond 0,5 pour deux des quatre points. La graine 1235 aussi. `GRAINE` vaut
donc **1236**, la plus petite graine au-dessus de 1234 avec laquelle le réseau
apprend (perte finale sous 0,05, et les quatre réponses arrondies justes). Un
test le vérifie (`tests/test_a_la_main.py`).

Rester coincé n'est pas rare : sur les graines 1 à 20, 14 apprennent et 6
restent coincées (section `graines` des attendus). Comme les 20 graines ne
réussissent ni n'échouent toutes, `NB_GRAINES` reste à 20.

## Tester

```bash
uv run --extra cpu pytest -q
```

Les deux tests marqués `gpu` sont sautés sans carte, avec la raison « CUDA
absente » :

- `test_auto_prend_la_carte` (`tests/test_appareil.py`) : le choix
  automatique de la carte ;
- `test_pytorch_sur_la_carte` (`tests/test_avec_pytorch.py`) : l'entraînement
  sur la carte, dont les poids finaux doivent rester à moins de 10⁻⁶ de ceux
  du processeur.

Avec une carte NVIDIA, `uv run --extra gpu pytest -q` les lance aussi. Le test
du notebook l'exécute de bout en bout, sur la carte si elle est là.

## La sortie du PC de La Forge IA

Le chapitre 0.5 montre la sortie du script sur le PC de La Forge IA
(processeur AMD Ryzen 7 9800X3D, 16 fils ; carte RTX 5070 Ti). Elle est dans
`sorties/`, en deux fichiers relevés le 05/11/2026, l'un après l'autre, carte
au repos : l'entraînement de l'IA qui occupait la carte était en pause.

- `sorties/processeur.txt`, écrit par
  `uv run --extra cpu python -m premier_reseau entrainer --appareil cpu --enregistrer sorties/processeur.txt`.
  Il remplace la sortie relevée pendant l'écriture du chapitre, quand la carte
  entraînait encore cette IA et que le processeur en faisait un peu pour elle ;
- `sorties/rtx-5070-ti.txt`, la carte, écrit par
  `uv run --extra gpu python -m premier_reseau entrainer --appareil cuda --enregistrer sorties/rtx-5070-ti.txt`.

Aucun test ne fige leurs durées : elles dépendent de la machine. Le chapitre
0.5 les compare, et le chapitre 0.4 explique pourquoi la carte ne gagne pas
sur de tout petits calculs.

## Les attendus de référence

Le fichier `tests/attendus.json` a trois sections :

- `neurone` : les points, la grille, et pour chaque porte son meilleur
  réglage et le compte de chacun des 729 réglages. Le site refait ce calcul
  en TypeScript (`site/src/lib/partie-0/neurone.ts`) et le compare à ce
  fichier, au bit près ;
- `entrainement` : la graine, le taux, le nombre de pas, le nombre de poids
  (compté sur le réseau), les poids de départ, les 3 001 pertes (avant le
  premier pas, puis après chacun) et les 4 prédictions finales. Le site ne
  refait pas l'entraînement : il lit ces valeurs ;
- `graines` : pour chaque graine de 1 à 20, si l'entraînement réussit.

Les pertes et les prédictions passent par `math.exp` et `math.log`, dont le
dernier chiffre peut changer d'un système à l'autre (Windows, Linux) : le test
les compare à 10⁻⁹ près, et tout le reste au bit près. Pour régénérer le
fichier :

```bash
uv run --extra cpu python -m premier_reseau.attendus
```

## Le notebook

`notebooks/0.5-reseau.ipynb` fait le même parcours dans Colab, avec le
PyTorch déjà installé par Colab : il ne l'installe pas. Il tourne aussi sans
carte, et dit sur quoi il a tourné. Pour avoir une carte dans Colab :
Exécution > Modifier le type d'exécution > GPU.
