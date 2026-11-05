# Vérifier son poste

Un petit script qui regarde ton ordinateur comme le verront les projets de La
Forge IA : le système, Python, PyTorch, la carte graphique NVIDIA et son
pilote, et le nombre de fils de calcul du processeur. Il en tire un
diagnostic, dit quoi faire quand quelque chose cloche, puis fait un essai de
calcul sur le processeur, et sur la carte si elle est prête.

C'est le projet du chapitre 0.3 de La Forge IA, « Installer son poste ». Il
utilise PyTorch, en deux versions au choix : celle pour carte NVIDIA (extra
`gpu`, CUDA 13.2) et celle pour le processeur seul (extra `cpu`).

## Installer uv

`uv` installe Python et les bibliothèques de chaque projet. Le fichier
`.python-version` demande Python 3.12 : uv le télécharge lui-même s'il manque.

Windows, dans PowerShell (ou `winget install --id=astral-sh.uv -e`) :

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Linux et Mac, dans un terminal :

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Puis ferme et rouvre le terminal, et vérifie avec `uv --version`.

## Lancer

Récupère le dépôt, puis va dans le dossier du projet. Les commandes sont les
mêmes dans PowerShell (Windows) et dans un terminal (Linux, Mac) :

```bash
git clone https://github.com/chipat-neko/forge-ia
cd forge-ia/projets/0.3-poste
```

Si tu as déjà récupéré le dépôt (au chapitre 0.1, par exemple), mets-le à
jour depuis le dossier où tu l'as récupéré, puis va dans le projet :

```bash
git -C forge-ia pull
cd forge-ia/projets/0.3-poste
```

Sans git, le bouton « Code » de la page GitHub du dépôt donne un fichier zip,
à télécharger de nouveau à chaque mise à jour : son dossier s'appelle
`forge-ia-main`, à écrire à la place de `forge-ia` dans la commande `cd`.

**Avec une carte NVIDIA** (Windows ou Linux), d'abord `nvidia-smi` pour voir
le pilote, puis :

```bash
uv run --extra gpu python -m poste
```

La première fois, uv télécharge la version de PyTorch pour la carte : plusieurs
gigaoctets.

**Sans carte NVIDIA, et sur un Mac à puce Apple (M1 et suivants), macOS 14 ou
plus récent :**

```bash
uv run --extra cpu python -m poste
```

Sur Mac, il n'y a pas de CUDA. La puce graphique des Mac (MPS) n'est pas
essayée par le site : tout y tourne sur le processeur. Les Mac à processeur
Intel ne sont plus pris en charge par PyTorch : uv n'y trouve aucune version à
installer.

`uv run` installe ce qu'il faut avant de lancer le script. Sans `--extra`,
PyTorch n'est pas installé : le script le dit, et donne la commande à lancer.
`uv sync --extra gpu` (ou `uv sync --extra cpu`) fait la même installation
sans rien lancer.

## Ce que dit le script

Voici sa sortie sur le PC de La Forge IA, avec la version de PyTorch pour le
processeur, alors que ce PC a une RTX 5070 Ti : `sorties/processeur.txt`. Elle
montre deux constats « attention » et aucun problème.

Avec la version pour la carte, sa sortie est `sorties/rtx-5070-ti.txt`,
relevée le 05/11/2026, carte au repos (l'entraînement de l'IA qui l'occupait
était en pause) : la carte est prête, l'essai de calcul tourne aussi sur elle,
et seul le constat des fils reste en « attention ».

Chaque constat a un niveau : **bon**, **attention** (ça marche, mais moins bien
que ça pourrait) ou **problème** (il faut agir). La dernière ligne compte les
problèmes : « Diagnostic terminé : 0 problème(s). ». S'il y en a, le script
rend le code de sortie 1.

| Constat | Niveau | Ce que ça veut dire | Quoi faire |
| --- | --- | --- | --- |
| `torch_absent` | problème | PyTorch ne s'importe pas : lancé sans `--extra`, ou mal installé. | `uv run --extra gpu python -m poste` avec une carte NVIDIA, sinon `uv run --extra cpu python -m poste`. S'il est installé mais ne se charge pas, la même commande avec `python -c "import torch"` à la place de `python -m poste` montre l'erreur. |
| `processeur_seul` | bon | Pas de pilote NVIDIA : tout calcule sur le processeur. | Rien. Tout marche, en plus lent pour entraîner ton IA. |
| `roue_processeur` | attention | Une carte NVIDIA est là, mais PyTorch est la version pour le processeur seul. C'est ce que donne `pip install torch` sous Windows. | `uv sync --extra gpu`, puis `uv run --extra gpu python -m poste`. |
| `pilote_absent` | problème | PyTorch est fait pour la carte, mais aucun pilote NVIDIA ne répond. | Installe le pilote de la carte, redémarre, puis relance. Sans carte NVIDIA : `uv run --extra cpu python -m poste`. |
| `pilote_trop_ancien` | problème | PyTorch ne voit pas la carte, et le pilote ne va pas jusqu'à sa version de CUDA (CUDA 13 demande un pilote 580 ou plus récent). Si PyTorch voit la carte, le pilote suffit. | Mets à jour le pilote, redémarre, puis `uv run --extra gpu python -m poste`. |
| `carte_trop_recente` | problème | PyTorch voit la carte, mais n'a rien pour sa génération : par exemple une RTX 50 (sm_120) avec une ancienne version pour CUDA 12.6, qui s'arrête à sm_90. | `uv sync --extra gpu`, pour la version du projet, puis `uv run --extra gpu python -m poste`. |
| `carte_trop_ancienne` | problème | PyTorch voit la carte, mais commence à une génération plus récente : par exemple une GTX 1080 (capacité 6.1) avec la version du projet, qui commence à sm_75. | Calcule sur le processeur : `uv run --extra cpu python -m poste`. Le diagnostic dira que cette version laisse la carte de côté : c'est voulu, la carte est trop ancienne. Dans les projets suivants, mets la variable d'environnement `FORGE_APPAREIL=cpu`. |
| `carte_invisible` | problème | Pilote et PyTorch sont là, mais PyTorch ne voit aucune carte. | Lance `nvidia-smi`. S'il ne montre pas la carte : redémarre, ou réinstalle le pilote. S'il la montre : vérifie que `CUDA_VISIBLE_DEVICES` n'est pas réglée. |
| `carte_prete` | bon | PyTorch voit la carte et sait calculer dessus. | Rien : c'est la ligne qu'on veut voir. |
| `fils` | attention | PyTorch n'utilise qu'une partie des fils du processeur : sur le PC de La Forge IA, 8 sur 16 par défaut. | Au début de ton programme : `torch.set_num_threads(os.cpu_count())`. |

Une carte est connue de PyTorch quand sa génération est dans la liste de ses
architectures, avec une mineure plus petite ou égale : les versions de PyTorch du projet
n'ont pas `sm_89`, mais `sm_86` sert une RTX 4070, de capacité 8.9. Une entrée
`compute_XY`, quand il y en a une, sert toute carte de capacité X.Y ou plus.

Le diagnostic est la fonction `diagnostiquer(faits)` de `poste/diagnostic.py`.
Elle ne lance rien : elle lit des faits et rend des constats. Elle est testée
sur des situations nommées (`SITUATIONS`), celles du chapitre : la RTX 5070 Ti
avec la bonne version de PyTorch, avec celle de PyPI, avec une ancienne
version pour CUDA 12.6, un pilote trop ancien, un PC sans carte, Colab avec
une T4, et PyTorch réglé par défaut sur 8 fils sur 16.

## Choisir l'appareil

`choisir_appareil()` (`poste/appareil.py`) dit où calculer : l'argument,
sinon la variable `FORGE_APPAREIL`, sinon `auto`, qui prend la carte si
PyTorch la voit, sinon le processeur. Les projets 0.4 et 0.5 en ont une copie.

```powershell
$env:FORGE_APPAREIL = "cpu"   # PowerShell
```

```bash
export FORGE_APPAREIL=cpu     # Linux, Mac
```

Demander `cuda` sans carte visible donne un message qui dit quoi faire, pas
une trace Python. Comme l'argument passe avant la variable, le conseil dépend
de l'origine de la demande : demander `cpu` à la place, ou mettre
`FORGE_APPAREIL=cpu`. Pour savoir pourquoi la carte manque, il renvoie à
`python -m poste`, dans ce dossier, avec le même `uv run --extra` (cpu ou gpu)
que la commande qui a échoué : le diagnostic nomme alors la vraie cause, sans
changer de version de PyTorch.

## Enregistrer une sortie

```bash
uv run --extra cpu python -m poste --enregistrer sorties/processeur.txt
uv run --extra gpu python -m poste --enregistrer sorties/rtx-5070-ti.txt
```

Le fichier contient la même sortie, en UTF-8, précédée de la ligne
`# relevé le AAAA-MM-JJ`. Le chapitre 0.3 montre ces sorties telles quelles.

## Tester

```bash
uv run --extra cpu pytest -q
```

Les deux tests marqués `gpu` (le choix automatique de la carte, l'essai de
calcul sur la carte) sont sautés sans carte, avec la raison « CUDA absente ».
Avec une carte NVIDIA, `uv run --extra gpu pytest -q` les lance aussi. Le test
du notebook l'exécute de bout en bout, sur la carte si elle est là.

## Les attendus de référence

Le fichier `tests/attendus.json` contient chaque situation nommée, avec ses
faits et ses constats. Le chapitre 0.3 le lit pour son tableau des situations
et ses paris : il ne refait pas le diagnostic. Pour le régénérer :

```bash
uv run --extra cpu python -m poste.attendus
```

Un test vérifie qu'il est à jour : si le diagnostic change, il échoue tant que
le fichier n'est pas régénéré.

## Ce que montre le chapitre

Les extraits de code du chapitre 0.3 sont tirés du projet, entre les
marqueurs `# region: <nom>` et `# fin: <nom>` :

| Fichier | Région | Étape du chapitre |
| --- | --- | --- |
| `pyproject.toml` | `pytorch` | 4, « Le projet et sa version de PyTorch » |
| `poste/diagnostic.py` | `diagnostiquer` | 5, « Vérifier » |
| `poste/appareil.py` | `appareil` | 5, « Vérifier » |

La région `essai` de `poste/essai.py` est balisée aussi, mais le chapitre ne
la montre pas. L'étape 5 montre aussi les deux sorties de `sorties/`, telles
quelles, et l'étape 6 le tableau des situations de `tests/attendus.json`.

## Le notebook

`notebooks/0.3-poste.ipynb` fait la même vérification dans Colab, avec le
PyTorch déjà installé par Colab : il ne l'installe pas. Il dit sur quoi il a
tourné, et, sans carte, comment en demander une : Exécution > Modifier le type
d'exécution > GPU.
