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

Une coupure (réseau, courant, disque plein) ne laisse ni trou ni doublon : on relance la même
commande, qui reprend au dernier fragment écrit (seul le fragment en cours, jusqu'à 100 Mo, est
relu). Une source n'est terminée que lorsque son fichier `.complet` existe. Le mélange par défaut est défini une seule fois, dans
`forge.donnees.melange.MELANGE_PAR_DEFAUT`.

## Le tokenizer de ton IA

Le paquet `forge.tokenizer` contient le tokenizer de ton IA : un BPE sur les
octets (256 octets, 32 448 fusions, puis 64 jetons spéciaux, soit 32 768 jetons),
écrit à la main en Python. Il s'apprend sur les textes téléchargés, dans les
parts du mélange (75 % de web, 10 % de Wikipédia, 15 % de code) :

```powershell
uv run --extra gpu python -m forge tokenizer --donnees echantillon-tokenizer `
    --taille 32768 --nom ton-ia-v1 --octets-max 300M --sortie "$env:FORGE_DONNEES\essai-tokenizer.json"
```

Le fichier écrit ici est **hors du dépôt** (`essai-tokenizer.json`, sous `FORGE_DONNEES`) : le
tokenizer définitif de ton IA, `ton-ia-v1`, est déjà appris sur 300 Mo de français et de code, et
rangé dans le dépôt, `forge/ressources/tokenizer-ton-ia-v1.json`. **Il est figé** pour tout le
reste du parcours (les tests de `tests/test_tokenizer_ton_ia.py` le vérifient octet pour octet),
et il ne faut jamais l'écraser. Pour refaire l'expérience, on écrit ailleurs, puis on compare les
empreintes (`Get-FileHash -Algorithm SHA256`) : voir `docs/mesures/tokenizer-ton-ia-v1.md`.

Les documents de validation (ceux que `encoder` rangera dans `val/`, 0,5 % des documents) ne
servent pas à apprendre, pour que la compression mesurée dessus soit honnête. Si les textes ne
suffisent pas pour toutes les fusions, la commande échoue sans rien écrire.

`compression` mesure les octets par jeton d'un tokenizer (celui du dépôt par défaut) sur environ
1 Mo de documents de validation de chaque source, et pour le mélange. Il lui faut des textes
téléchargés assez gros pour contenir 1 Mo de validation par source, donc un volume par source
avec `--parts` (au lieu de `--octets`) :

```powershell
uv run --extra gpu python -m forge donnees --parts web_fr=400M,wikipedia_fr=350M,code_python=300M `
    --dossier validation-tokenizer
uv run --extra gpu python -m forge compression --donnees validation-tokenizer
```

Les chiffres du tokenizer figé sont dans `docs/mesures/tokenizer-ton-ia-v1.md`.

Dans le code : `TokenizerOctets.charger(chemin)`, puis `encoder(texte)` et
`decoder(ids)`. L'encodeur n'émet jamais de jeton spécial ; on les ajoute avec
`id_special("<|fin_texte|>")`.

## Encoder les textes en jetons

Une fois les textes téléchargés et le tokenizer appris, `encoder` écrit le corpus en
fragments de jetons (`uint16`, chaque document suivi de `<|fin_texte|>`), en parallèle sur
tous les cœurs, avec reprise fragment par fragment :

```powershell
uv run --extra gpu python -m forge encoder --donnees echantillon `
    --tokenizer forge/ressources/tokenizer-ton-ia-v1.json
```

Le résultat est dans `FORGE_DONNEES/jetons/echantillon/` (`train/`, `val/`, `index.json`),
et `forge.donnees.jetons.lire_jetons(fichier)` ouvre un fichier sans le charger en mémoire.
Détails dans `docs/donnees.md`.

## Entraîner ton IA

Un fichier TOML décrit l'entraînement (taille du modèle, jetons, lot, taux d'apprentissage,
appareil) ; `configs/mini.toml` est commenté réglage par réglage :

```powershell
uv run --extra gpu python -m forge entrainer --config configs/mini.toml
```

Sur la carte graphique, les calculs se font en bf16, avec accumulation de gradient pour
atteindre le lot voulu. Le journal (`journal.jsonl`, une ligne par pas) et les sauvegardes
vont dans `FORGE_DONNEES/entrainements/<sortie>/`. On garde les deux dernières sauvegardes
`etape-*.pt` et `meilleur.pt` (la plus petite perte de validation) ; chaque sauvegarde est
écrite d'un coup, donc une coupure de courant n'en laisse jamais une à moitié.

- **Pause :** Ctrl+C. Le pas en cours se termine, tout est sauvegardé, puis la commande de
  reprise s'affiche.
- **Reprise** (après une pause, un plantage ou une coupure) : la même commande avec
  `--reprendre`. Le pas suivant est exactement celui qui aurait suivi sans la pause.
- **Mémoire de la carte graphique insuffisante :** réduire `micro_lot` dans le TOML (les
  jetons de chaque pas restent les mêmes), puis relancer avec `--reprendre`.

## Mesurer la vitesse avant d'entraîner

Avant un entraînement de plusieurs heures, `mesurer` fait un essai chronométré de la vraie
étape d'entraînement (sur des jetons tirés au hasard) pour chaque taille, sur la carte graphique
(il cherche le plus grand `micro_lot` qui tient en mémoire, puis mesure celui-là et les puissances
de 2 en dessous : le plus grand n'est pas toujours le plus rapide) et sur le processeur (avec tous
ses fils, dont il relève la charge). Il écrit des tableaux : jetons par seconde, durée pour 20 jetons
par paramètre, place sur le disque. Si la carte est déjà occupée par un autre programme, il le dit
au lieu de mesurer :

```powershell
uv run --extra gpu python -m forge mesurer --json mesures.json --tableau tableaux.md
```

Les chiffres du 3 novembre 2026 sont dans `docs/mesures/entrainement-2026-11.md`.

## Évaluer ton IA

Après un entraînement, `evaluer` mesure une sauvegarde et écrit un rapport en français
(les chemins ci-dessous sont des exemples) :

```powershell
uv run --extra gpu python -m forge evaluer `
    --sauvegarde D:\forge-ia-donnees\entrainements\mini\sauvegardes\meilleur.pt --donnees echantillon
```

Le rapport (`rapport.md` pour la lecture, `rapport.json` pour les programmes) va dans
`evaluation/<nom de la sauvegarde>/`, à côté de `sauvegardes/` (ou dans `--sortie`). Il contient :

- la perte de validation (en nats par jeton), la perplexité (`exp(perte)`) et les bits par octet
  (`perte ÷ ln 2 ÷ octets par jeton`) : la perte ramenée à un octet de texte, la seule qui se compare
  d'un tokenizer à l'autre. C'est une estimation : les octets par jeton sont ceux du corpus entier, et la
  perte compte aussi les fins de texte (écart attendu de l'ordre de quelques millièmes). La perte est mesurée
  sur 1 024 morceaux fixes de `val/` au plus ;
- les QCM français de FrenchBench (HellaSwag et ARC-Challenge, des traductions automatiques),
  comparés au hasard (1 ÷ nombre de choix). Le verdict est prudent : un score à moins de la marge du hasard
  (l'intervalle à 95 %  d'un résultat dû au seul hasard, large quand il y a peu de questions) est « pas
  différent du hasard ». C'est une mesure maison, comparable seulement entre nos modèles et au hasard, pas
  aux scores publiés de FrenchBench (gabarit des questions, jeton de début et normalisation par octets sont les
  nôtres). `--qcm N` limite chaque test à ses N premières questions (le rapport le dit), `--qcm 0` n'en passe
  aucune (et n'a pas besoin du réseau) ; sinon FrenchBench se télécharge la première fois, et la commande
  lève elle-même `HF_HUB_OFFLINE` pour son processus ;
- dix textes écrits par le modèle à partir de débuts fixes (huit phrases françaises, deux débuts
  de fonction Python), avec une graine fixe : mêmes réglages, mêmes textes.

Le tokenizer est celui du dépôt (`--tokenizer` pour un autre) : il doit être celui de l'entraînement, et celui qui a
encodé les données, sinon la commande refuse de mesurer. Les calculs se font sur la carte graphique si PyTorch la
voit (en bf16), sinon sur le processeur (`--appareil cpu` pour le forcer).

## Tester

```powershell
cd projets/forge
uv run --extra gpu pytest -q   # tous les tests, dont celui de la carte graphique
uv run --extra cpu pytest -q   # le test de la carte graphique est sauté
```

Les tests marqués `gpu` sont sautés tout seuls quand CUDA est absente. En
intégration continue, `.github/workflows/python.yml` lance
`uv run --locked --extra cpu pytest -q` pour ce projet.
