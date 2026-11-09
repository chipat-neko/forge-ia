# Le transformer pièce par pièce

Le transformer de « ton IA » (le paquet `forge`, dans `projets/forge`) est un
décodeur seul : des plongements, des blocs d'attention et de MLP SwiGLU, une
dernière normalisation. Ce projet le **refait pièce par pièce**, en fonctions
pures sur des tenseurs (aucun `nn.Module`, aucun
`F.scaled_dot_product_attention`, la softmax écrite à la main), puis vérifie
que chaque pièce donne les mêmes nombres que le module correspondant de forge,
à 10⁻¹² près.

C'est le projet du chapitre 1.4 de La Forge IA, « Le transformer ». Comme les
projets 0.3 à 0.5, il utilise PyTorch, en deux versions au choix : celle pour
carte NVIDIA (extra `gpu`, CUDA 13.2) et celle pour le processeur seul (extra
`cpu`). Tous ses calculs tournent sur le processeur : le modèle de comparaison
est minuscule (vecteurs de 32 nombres), la carte n'y gagnerait rien.

Il dépend de forge par chemin (`forge-ia = { path = "../forge", editable = true }`
dans `pyproject.toml`) : il faut donc le dépôt entier, pas seulement ce dossier.

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
cd forge-ia/projets/1.4-transformer
```

Si tu as déjà récupéré le dépôt, mets-le à jour (`git -C forge-ia pull`) avant
de revenir dans ce dossier.

```bash
uv run --extra cpu python -m transformer_pas_a_pas comparer
uv run --extra cpu python -m transformer_pas_a_pas compter --preset tres_grand
```

`--extra cpu` prend la version de PyTorch pour le processeur ; avec une carte
NVIDIA, `--extra gpu` marche aussi (la première fois, uv télécharge cette
version, plusieurs gigaoctets, sauf si elle est déjà dans son cache), mais le
projet n'utilise pas la carte.

- `comparer` construit un petit transformer de forge (2 couches, vecteurs de
  32 nombres, 4 têtes, 50 jetons possibles), en float64, sur le processeur. Ses
  poids sont tirés au hasard avec une graine fixée. Il compare ensuite chaque
  pièce (`rmsnorm`, `rope`, `attention`, `swiglu`, `bloc`, `modele`) au module
  de forge sur un même lot de deux textes, affiche le plus grand écart de
  chacune, et finit par « identique à forge à 10⁻¹² près : oui » (ou « non »,
  avec le code de sortie 1). Avec `--enregistrer FICHIER`, il écrit aussi sa
  sortie dans FICHIER (UTF-8), précédée de la date du relevé : c'est ainsi que
  `sorties/comparaison.txt` a été écrit.
- `compter --preset NOM` donne les paramètres d'une taille de forge (`mini`,
  `petit`, `moyen`, `grand` ou `tres_grand`), famille par famille, et vérifie
  que leur somme est le nombre de paramètres de forge.

## Les pièces

Tout est dans `transformer_pas_a_pas/pieces.py`. Chaque fonction reçoit des
tenseurs, poids compris, et rend un tenseur. Les poids sont rangés comme dans
forge : une matrice de forme `[sortie, entrée]`, appliquée par `x @ w.T`. Les
fonctions acceptent une suite de jetons `[n, …]` ou un lot `[lot, n, …]`.

| Région | Fonctions | Ce qu'elle fait |
| --- | --- | --- |
| `plongement` | `plongement` | un jeton devient une ligne de la table |
| `rmsnorm` | `rmsnorm` | divise par la racine de la moyenne des carrés, puis multiplie par un poids |
| `rope` | `angles_rope`, `tourner` | tourne chaque paire de valeurs d'un angle proportionnel à la position |
| `attention` | `softmax`, `poids_et_valeurs`, `poids_attention`, `attention` | scores `q·kᵀ/√d`, masque, softmax, mélange des valeurs |
| `masque` | `masque` | `True` au-dessus de la diagonale : les jetons qu'on n'a pas le droit de voir |
| `swiglu` | `swiglu` | une porte (SiLU) décide quoi garder de l'autre voie |
| `bloc` | `bloc` | attention puis MLP, chacun normalisé avant et ajouté au vecteur |
| `modele` | `modele` | plongement, blocs, norme finale, logits (poids liés) |

### Où forge calcule en float32

forge calcule deux choses en float32, **même dans un modèle en float64** :

- **RMSNorm** : `x.float()` avant la moyenne des carrés (et `torch.rsqrt`) ;
  le résultat est multiplié par le poids, puis reprend le type de l'entrée ;
- **RoPE** : les angles (`rope_cos_sin`) sont calculés en float32, leurs
  cosinus et sinus aussi, et la rotation de `appliquer_rope` se fait en
  float32 (`x.float()`) avant de reprendre le type de l'entrée.

Si `pieces.py` calculait tout en float64, il s'écarterait de forge de plus de
10⁻⁹ (un test le mesure : `test_sans_float32_l_ecart_depasse_le_seuil`), l'erreur d'arrondi du float32, et l'égalité à 10⁻¹² serait fausse
alors qu'il n'y a aucune erreur de formule. Il refait donc ces passages aux
mêmes endroits, dans le même ordre d'opérations (`torch.rsqrt` et non
`1 / sqrt`, par exemple : ils diffèrent d'un bit de float32). Une conséquence :
les angles que renvoie `angles_rope` sont en float32.

Les angles de la **figure** du chapitre (`attendus.py`, `site/src/lib/partie-1/rope.ts`)
restent en float64 : la figure montre le calcul, forge fait celui du modèle.

### Les poids du modèle de comparaison

Ceux de départ de forge (écart-type 0,02) rendraient l'attention presque
uniforme et SwiGLU presque nul : le masque, l'échelle 1/√d et RoPE seraient presque invisibles, et l'égalité ne prouverait presque rien. `comparer.preparer_forge` les
tire donc de nouveau (écart-type 0,2, et 1 plus un bruit de 0,2 pour les
RMSNorm), avec une graine fixée. C'est le `Transformer` de forge lui-même qui
est construit : le projet ne touche à aucun fichier de forge.

## Tester

```bash
uv run --extra cpu pytest -q
```

Le test d'égalité (`test_piece_egale_a_forge`) est encadré par
`# region: test-egalite` / `# fin: test-egalite`, pour que le chapitre le
montre. Les autres tests vérifient le masque (changer le dernier jeton ne
change aucune sortie d'avant), les poids d'attention (ils totalisent 1 et
redonnent la sortie), la softmax à la main, le comptage des paramètres, les
attendus, les régions du paquet et le notebook.

Aucun test n'a besoin de la carte graphique.

## Compter les paramètres

`transformer_pas_a_pas/compter.py` range les paramètres en quatre familles :

- `plongement` : `taille_vocabulaire × dim`, compté une seule fois (la
  matrice de sortie est la même) ;
- `attention` : `couches × 4 × dim²` (q, k, v et la projection de sortie) ;
- `mlp` : `couches × 3 × dim × largeur_cachee(dim)` ;
- `normes` : `couches × 2 × dim + dim`.

RoPE n'a aucun paramètre et il n'y a aucun biais. La somme vaut
`forge.modele.config.nombre_parametres`, pour chaque preset.

## La sortie

`sorties/comparaison.txt` est la sortie de `comparer`, écrite par :

```bash
uv run --extra cpu python -m transformer_pas_a_pas comparer --enregistrer sorties/comparaison.txt
```

Les écarts sont de 10⁻¹⁴ au plus (certaines pièces sortent à 0) ; leur dernier chiffre peut changer d'une
machine à l'autre, et aucun test ne le fige : le test exige seulement qu'ils
restent sous 10⁻¹².

## Les attendus de référence

Le fichier `tests/attendus.json` a deux sections :

- `repartitions` : pour chacun des cinq presets de forge, ses dimensions et le
  nombre de paramètres de chaque famille. Le jumeau TypeScript
  (`site/src/lib/partie-1/parametres.ts`) est comparé à ce fichier, exactement
  (ce sont des entiers) ;
- `rope` : les angles de la figure du chapitre, pour les positions 0 à 32 et
  les 4 paires d'une tête de 8, avec la base de `ConfigModele` (10 000).
  Le jumeau (`site/src/lib/partie-1/rope.ts`) les retrouve à 10⁻¹² près.

Les angles passent par `**`, `cos` et `sin`, dont le dernier chiffre peut
changer d'un système à l'autre (Windows, Linux) : le test du Python les compare
à 10⁻⁹ près, et les répartitions exactement. Pour régénérer le fichier :

```bash
uv run --extra cpu python -m transformer_pas_a_pas.attendus
```

## Le notebook

`notebooks/1.4-transformer.ipynb` refait les pièces une à une avec un petit
modèle tiré au hasard, les compare à forge, compte les paramètres de ton IA, et
propose un défi : écrire la softmax à la main. Il tourne sur le processeur, sans
carte graphique, n'installe ni PyTorch ni forge (Colab a déjà PyTorch ; forge
vient du dépôt cloné), et dit sur quoi il a tourné. Le test
`tests/test_notebook.py` l'exécute de bout en bout.
