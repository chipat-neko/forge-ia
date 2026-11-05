# Les maths utiles

Les quelques maths dont une IA a besoin, en petites fonctions Python :
vecteurs et produit scalaire, une matrice fois un vecteur, la pente d'une
erreur et la descente qui la suit, des tirages au sort, puis softmax et
l'erreur d'une prédiction.

C'est le projet du chapitre 0.2 de La Forge IA, « Les maths utiles ». Il
n'utilise que la bibliothèque standard de Python. Le site en propose un jumeau
en TypeScript, pour ses trois figures (vecteurs, descente, tirages), qui doit
donner exactement les mêmes nombres.

## Lancer

Il faut `uv` : pour l'installer, voir le README du projet 0.1
(`projets/0.1-python`), ou
<https://docs.astral.sh/uv/getting-started/installation/>. Le projet demande
Python 3.12 ou plus récent : uv en télécharge un lui-même s'il n'en trouve
pas.

Récupère le dépôt avec git (si tu l'as déjà fait au chapitre 0.1,
`git -C forge-ia pull` le met à jour), puis va dans le dossier du projet. Les
commandes sont les mêmes dans PowerShell (Windows) et dans un terminal
(Linux, Mac) :

```bash
git clone https://github.com/chipat-neko/forge-ia
cd forge-ia/projets/0.2-maths
uv run python -m maths_utiles
```

Sans git, le bouton « Code » de la page GitHub du dépôt donne aussi un
fichier zip : son dossier s'appelle `forge-ia-main`, à écrire à la place de
`forge-ia` dans la commande `cd`. Un zip ne se met pas à jour : pour recevoir
les projets parus depuis, télécharge-le de nouveau.

Le programme montre un exemple de chaque idée : le produit scalaire de deux
vecteurs, une matrice fois un vecteur, dix pas de descente au taux 0,1, puis
1 000 tirages au sort. Avec `--taux 0.5`, la descente change de taux ; avec
`--tirages 100000 --graine 7`, les tirages changent de nombre et de graine.

## Tester

Dans le dossier du projet :

```bash
uv run pytest
```

Avec `-q`, pytest n'affiche qu'un point par test réussi et le bilan.

## Ce que montre le chapitre

Le chapitre 0.2 ne fait taper aucune commande : il montre le code du projet,
tiré des régions balisées par `# region: <nom>` et `# fin: <nom>`.

| Fichier | Région | Étape du chapitre |
| --- | --- | --- |
| `maths_utiles/vecteurs.py` | `scalaire` | 1, « Des nombres en colonne : les vecteurs » |
| `maths_utiles/vecteurs.py` | `matrice` | 2, « Les matrices : beaucoup de produits scalaires » |
| `maths_utiles/derivees.py` | `erreur`, `pente` | 3, « La pente » |
| `maths_utiles/derivees.py` | `descendre` | 4, « Descendre la pente » |
| `maths_utiles/derivees.py` | `chaine` | 5, « La règle de la chaîne » |
| `maths_utiles/tirage.py` | `tirer`, `hasard` | 6, « Les probabilités » |
| `maths_utiles/probabilites.py` | `softmax`, `erreur-de-prediction` | 7, « Des scores aux probabilités, et l'erreur » |

## Ce que contient le paquet

- `vecteurs.py` : `produit_scalaire`, `norme`, `cosinus`, `somme` et
  `matrice_fois_vecteur` (une ligne de la matrice fois le vecteur, par case).
- `derivees.py` : l'erreur selon un poids, `(x − 3)² + 1`, sa pente exacte et
  sa pente approchée, la descente `x ← x − taux × pente(x)`, et un exemple de
  la règle de la chaîne.
- `tirage.py` : un hasard reproductible (`Hasard`, SplitMix32), les
  probabilités tirées de comptes, et les tirages au sort.
- `probabilites.py` : softmax, des scores aux probabilités, et l'erreur d'une
  prédiction, `−ln p`.

## Le hasard

`Hasard` est une copie de celui du mini-modèle
(`projets/mini-modele/mini_modele/calcul.py`) : une même graine donne la même
suite de nombres en Python et en TypeScript, sur toutes les machines. Dans le
dépôt, un test vérifie que la copie reste identique à l'original.

## Les attendus de référence

Le fichier `tests/attendus.json` contient les résultats du Python sur des
entrées fixées : des paires de vecteurs, des matrices, des descentes à chaque
taux de la figure, des tirages, des messages d'erreur, la pente approchée, la
règle de la chaîne, softmax et l'erreur `−ln p`. Le jumeau TypeScript doit
retrouver à l'identique les vecteurs, les matrices, les descentes, les tirages
et les messages d'erreur, mot pour mot. Pour le régénérer :

```powershell
cd projets/0.2-maths
uv run python -m maths_utiles.attendus
```

Un test vérifie que le fichier est à jour : si le code change, il échoue tant
que le fichier n'est pas régénéré. Softmax et `−ln p` passent par `exp` et
`log`, dont le dernier chiffre peut changer d'un système à l'autre (Linux et
Windows n'ont pas la même bibliothèque mathématique) : les nombres qu'elles en
tirent sont comparés à 10⁻⁹ près, tout le reste au bit près. Le site ne
recalcule ni softmax, ni `−ln p`, ni la pente approchée, ni la règle de la
chaîne : il lit les valeurs du Python.
