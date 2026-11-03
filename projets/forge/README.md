# La forge de « ton IA »

Le moteur de « ton IA » : un petit modèle de langage qui lit et écrit le
français et le code, entraîné sur la carte graphique du PC (RTX 5070 Ti). Ce
projet (paquet Python `forge`) rassemble tout ce qu'il faut : le téléchargement
des données, le tokenizer, l'encodage, la mesure de vitesse, l'entraînement et
l'évaluation. Les commandes arrivent au fil des tâches du plan.

## Installer et lancer

Il faut `uv` et Python 3.12 ou plus. PyTorch vient d'un index différent selon
la machine, donc on choisit toujours un extra :

| Extra | Pour qui | Roues PyTorch |
| --- | --- | --- |
| `gpu` | ce PC, carte NVIDIA | CUDA 13.2 (`download.pytorch.org/whl/cu132`) |
| `cpu` | sans carte graphique, intégration continue | CPU (`download.pytorch.org/whl/cpu`) |

Les deux extras sont en conflit : on n'en installe qu'un à la fois (changer
d'extra resynchronise l'environnement).

```powershell
# Depuis la racine du dépôt : place les données et les caches hors du dépôt.
. .\outils\env-forge.ps1

cd projets/forge
uv run --extra gpu python -m forge --help
```

## Où vont les données

Rien de lourd n'entre dans git. Les données (téléchargements, jetons, poids,
sauvegardes) vivent dans le dossier `FORGE_DONNEES` :

- par défaut `~/forge-ia-donnees` ;
- sur ce PC `D:\forge-ia-donnees`, fixé par `outils/env-forge.ps1`, qui range
  aussi les caches `uv` et Hugging Face dedans.

Le module `forge.chemins` donne ce dossier (`racine_donnees`), crée les
sous-dossiers au besoin (`dossier`) et vérifie la place libre avant un travail
long (`verifier_place`) : s'il en manque, il s'arrête avec un message qui dit
combien de Go libérer.

## Télécharger les données

Trois sources, lues en flux depuis Hugging Face sans télécharger les jeux entiers : 75 %
de français du web, 10 % de Wikipédia française et 15 % de code Python sous licence
permissive (sources, licences et liens dans `docs/donnees.md`). Les textes sont nettoyés,
dédoublonnés et écrits dans `FORGE_DONNEES/textes/<dossier>/<source>/`, par fragments
d'environ 100 Mo :

```powershell
uv run --extra gpu python -m forge donnees --octets 300M --dossier echantillon
```

Une coupure (réseau, courant, disque plein) ne perd rien : on relance la même commande, qui
reprend là où elle s'est arrêtée, sans doublon. Une source n'est terminée que lorsque son
fichier `.complet` existe. Le mélange par défaut est défini une seule fois, dans
`forge.donnees.melange.MELANGE_PAR_DEFAUT`.

## Le tokenizer de ton IA

Le paquet `forge.tokenizer` contient le tokenizer de ton IA : un BPE sur les
octets (256 octets, 32 448 fusions, puis 64 jetons spéciaux, soit 32 768 jetons),
écrit à la main en Python. Il s'apprend sur les textes téléchargés, dans les
parts du mélange (75 % de web, 10 % de Wikipédia, 15 % de code) :

```powershell
uv run --extra gpu python -m forge tokenizer --donnees echantillon-tokenizer `
    --taille 32768 --nom ton-ia-v1 --sortie forge/ressources/tokenizer-ton-ia-v1.json --octets-max 300M
```

Dans le code : `TokenizerOctets.charger(chemin)`, puis `encoder(texte)` et
`decoder(ids)`. L'encodeur n'émet jamais de jeton spécial ; on les ajoute avec
`id_special("<|fin_texte|>")`.

## Tester

```powershell
cd projets/forge
uv run --extra gpu pytest -q   # tous les tests, dont celui de la carte graphique
uv run --extra cpu pytest -q   # le test de la carte graphique est sauté
```

Les tests marqués `gpu` sont sautés tout seuls quand CUDA est absente. En
intégration continue, `.github/workflows/python.yml` lance
`uv run --locked --extra cpu pytest -q` pour ce projet.
