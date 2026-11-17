# La forge de « ton IA »

Le moteur de « ton IA » : un petit modèle de langage qui lit et écrit le
français et le code, entraîné sur la carte graphique du PC (RTX 5070 Ti). Ce
projet (paquet Python `forge`) rassemble tout ce qu'il faut : le téléchargement
des données, le tokenizer, l'encodage, la mesure de vitesse, l'entraînement,
le suivi, l'évaluation et l'export des fichiers à publier. Les commandes, dans
l'ordre de la chaîne : `donnees`, `tokenizer`, `compression`, `encoder`,
`mesurer`, `entrainer`, `suivi`, `evaluer` et `exporter` (`python -m forge
<commande> --help` les détaille).

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

Les commandes de ce README sont écrites pour PowerShell, sous Windows. Sous Linux, voir
« Sous Linux » plus bas : seules quelques-unes diffèrent.

### Cartes graphiques prises en charge

- **Une carte NVIDIA Turing (sm_75 : RTX 20xx, GTX 16xx) ou plus récente.** Les roues CUDA 13.2
  de PyTorch (`cu132`) ne contiennent du code que pour sm_75, sm_80, sm_86, sm_90, sm_100 et sm_120
  (`torch.cuda.get_arch_list()`) : CUDA 13 ne compile plus pour les cartes plus anciennes (Maxwell,
  Pascal, Volta, comme les GTX 10xx). Avec une de celles-ci, l'entraînement s'arrête sur « no kernel
  image » : mets `appareil = "cpu"` dans le TOML.
- **Le bf16 n'est natif qu'à partir d'Ampere (sm_80 et au-delà : RTX 30xx, 40xx, 50xx…).** L'entraînement
  calcule en bf16 sur la carte. Sur une carte Turing, le matériel ne le fait pas : lance d'abord
  `forge mesurer`, qui dit la vitesse réelle avant un entraînement de plusieurs heures.

Ce PC a une RTX 5070 Ti (Blackwell, sm_120).

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
commande, qui garde les fragments déjà écrits et reprend après le dernier. La reprise repart du
fichier et du groupe de lignes où le flux s'était arrêté (`etat_du_flux` dans `etat.json`), sans
relire ce qui est déjà compté. Un téléchargement commencé avant cette version n'a pas cet état :
sa première reprise est relue depuis le début du jeu, en sautant les documents déjà comptés, ce
qui coûte du temps et du réseau (18 minutes pour 15,6 millions de documents de code, voir
`docs/mesures/entrainement-2026-11.md`). Si le jeu refuse l'état enregistré (autre source, autre
version de `datasets`), la commande s'arrête avec un message, sans rien écrire. Une source n'est
terminée que lorsque son fichier `.complet` existe. Le mélange par défaut est défini une seule fois,
dans `forge.donnees.melange.MELANGE_PAR_DEFAUT`.

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
  reprise s'affiche. Sous Linux, le signal SIGTERM (arrêt du système, `docker stop`, `timeout`,
  `kill`) fait de même.
- **Reprise** (après une pause, un plantage ou une coupure) : la même commande avec
  `--reprendre`. Le pas suivant est exactement celui qui aurait suivi sans la pause.
- **Mémoire de la carte graphique insuffisante :** réduire `micro_lot` dans le TOML (les
  jetons de chaque pas restent les mêmes), puis relancer avec `--reprendre`. Si `micro_lot` vaut
  déjà 1 (c'est le cas de `configs/principal.toml`), cette taille de modèle ne tient pas sur la
  carte. Le message donne la mémoire libre ; trois marches à suivre :
  - fermer les programmes qui prennent la carte (jeux, logiciels 3D, vidéos, un autre
    entraînement), puis relancer avec `--reprendre` ;
  - ou choisir un preset plus petit, dans une nouvelle `sortie` (une sauvegarde ne reprend que le
    même modèle) : `python -m forge mesurer --presets mini,petit,moyen,grand` dit lesquels
    tiennent sur la carte ;
  - ou mettre `appareil = "cpu"` dans le TOML (bien plus lent), puis relancer avec `--reprendre`.
- **Veille :** sous Windows, l'entraînement empêche la mise en veille automatique du PC tant qu'il
  tourne (l'écran peut s'éteindre), et la rend à la pause ou à la fin. Une veille demandée
  (bouton, capot fermé) le suspend quand même ; sous Linux, voir « Sous Linux ».
- **Erreur imprévue** (CUDA au réveil d'une veille, par exemple) : le message donne le type de
  l'erreur et la commande de reprise ; la dernière sauvegarde complète reste bonne.

La version courte (« mini », 23 millions de paramètres, une heure sur la carte graphique, `configs/mini.toml`)
a été entraînée et évaluée le 3 novembre 2026 : durées, courbe, évaluation et échantillons sont dans
`docs/mesures/ton-ia-mini.md`. L'entraînement principal (`configs/principal.toml`, 433,6 millions de
paramètres, 139 h de carte) est raconté dans `docs/mesures/ton-ia-1.5.md`.

## Suivre un entraînement

`suivi` lit le journal d'un entraînement et dit où il en est : état (en cours, en pause, fini,
arrêté sans pause), pas, perte récente et de validation, débit, temps restant estimé et dernière
sauvegarde. Il ne fait que lire et n'importe pas PyTorch : on peut le lancer aussi souvent qu'on
veut, dans une autre console, pendant l'entraînement.

```powershell
uv run --extra gpu python -m forge suivi --config configs/principal.toml
```

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
(ici, la meilleure sauvegarde de la version courte, celle de `configs/mini.toml`) :

```powershell
uv run --extra gpu python -m forge evaluer `
    --sauvegarde "$env:FORGE_DONNEES\entrainements\ton-ia-mini\sauvegardes\meilleur.pt" --donnees court
```

Le rapport (`rapport.md` pour la lecture, `rapport.json` pour les programmes) va dans
`evaluation/<nom de la sauvegarde>/`, à côté de `sauvegardes/` (ou dans `--sortie`). Il contient :

- la perte de validation (en nats par jeton), la perplexité (`exp(perte)`) et les bits par octet
  (`perte ÷ ln 2 ÷ octets par jeton`) : la perte ramenée à un octet de texte, la seule qui se compare
  d'un tokenizer à l'autre. C'est une estimation : les octets par jeton sont ceux du corpus entier (train et val),
  fins de texte comprises comme dans la perte (écart attendu de l'ordre de quelques millièmes). La perte est mesurée
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

## Exporter ton IA, et recharger une version publiée

Une sauvegarde de l'entraînement sert à reprendre l'entraînement (poids en 32 bits, optimiseur,
état du hasard). Pour publier le modèle, `exporter` en tire trois fichiers :

```powershell
uv run --extra gpu python -m forge exporter `
    --sauvegarde "$env:FORGE_DONNEES\entrainements\ton-ia\sauvegardes\meilleur.pt" `
    --sortie "$env:FORGE_DONNEES\publication"
```

- `ton-ia-1.5.safetensors` (`--poids` pour un autre nom) : les poids en bf16. Le format
  safetensors ne contient que des nombres : l'ouvrir ne peut rien exécuter. La sortie du modèle
  réutilise la matrice du plongement (poids « liés ») : seul `plongement.weight` est écrit ;
- `config.json` : les dimensions du modèle (`ConfigModele(**config)` le reconstruit) ;
- `tokenizer-ton-ia-v1.json` : la copie exacte du tokenizer figé, vérifiée par son empreinte SHA-256.

Chaque fichier est écrit d'un coup ; la commande affiche la taille et l'empreinte SHA-256 de
chacun. La version publiée de ton IA est la Release `ton-ia-1.5` du dépôt : ces trois fichiers,
plus `rapport.json` et sa fiche (`docs/mesures/ton-ia-1.5-LISEZMOI.md`). Pour la recharger,
depuis `projets/forge` :

```powershell
gh release download ton-ia-1.5 --repo chipat-neko/forge-ia --dir ton-ia-1.5
uv run --extra cpu python ton_script.py   # avec une carte NVIDIA : --extra gpu
```

où `ton_script.py` fait ce que dit la fiche :

```python
import json
from pathlib import Path

from safetensors.torch import load_file

from forge.modele import ConfigModele, Transformer, generer
from forge.tokenizer import TokenizerOctets

dossier = Path("ton-ia-1.5")
config = ConfigModele(**json.loads((dossier / "config.json").read_text(encoding="utf-8")))
poids = load_file(dossier / "ton-ia-1.5.safetensors")
poids.setdefault("sortie.weight", poids["plongement.weight"])  # les poids liés
modele = Transformer(config)
modele.load_state_dict(poids)
tokenizer = TokenizerOctets.charger(dossier / "tokenizer-ton-ia-v1.json")

# Faire écrire ton IA : elle prolonge le début donné.
fin = tokenizer.id_special("<|fin_texte|>")  # pour ton IA, ce jeton marque aussi le début d'un texte
debut = [fin, *tokenizer.encoder("Il était une fois")]
suite = generer(modele, debut, 40, temperature=0.8, top_k=50, graine=0, arret=fin)
print("Il était une fois" + tokenizer.decoder([jeton for jeton in suite if jeton != fin]))
```

Pour vérifier un fichier téléchargé, compare son empreinte à celle de la fiche :
`Get-FileHash ton-ia-1.5.safetensors`.

## Sous Linux

Tout marche de même ; seules ces commandes diffèrent. Les données et les caches se règlent par
des variables d'environnement (au lieu de `outils/env-forge.ps1`), les chemins prennent des
`/`, et les commandes coupées sur deux lignes sous PowerShell tiennent ici sur une seule :

```bash
# Depuis projets/forge, une fois par session (à la place de « . .\outils\env-forge.ps1 ») :
export FORGE_DONNEES="$HOME/forge-ia-donnees"
export UV_CACHE_DIR="$FORGE_DONNEES/cache/uv" HF_HOME="$FORGE_DONNEES/cache/huggingface"

uv run --extra gpu python -m forge tokenizer --donnees echantillon-tokenizer --taille 32768 --nom ton-ia-v1 --octets-max 300M --sortie "$FORGE_DONNEES/essai-tokenizer.json"
uv run --extra gpu python -m forge donnees --parts web_fr=400M,wikipedia_fr=350M,code_python=300M --dossier validation-tokenizer
uv run --extra gpu python -m forge encoder --donnees echantillon --tokenizer forge/ressources/tokenizer-ton-ia-v1.json
uv run --extra gpu python -m forge evaluer --sauvegarde "$FORGE_DONNEES/entrainements/ton-ia-mini/sauvegardes/meilleur.pt" --donnees court
uv run --extra gpu python -m forge exporter --sauvegarde "$FORGE_DONNEES/entrainements/ton-ia/sauvegardes/meilleur.pt" --sortie "$FORGE_DONNEES/publication"

# La forge n'empêche la veille que sous Windows : ici, systemd-inhibit le fait pour elle.
systemd-inhibit --what=idle:sleep uv run --extra gpu python -m forge entrainer --config configs/principal.toml

# L'empreinte d'un fichier (au lieu de Get-FileHash) :
sha256sum ton-ia-1.5.safetensors
```

Deux différences de comportement :

- **La compilation.** Sous Linux, l'extra `gpu` installe aussi `triton` (voir `uv.lock`) : avec
  `compiler = "auto"`, l'entraînement sur la carte compile le modèle (`torch.compile`) et va plus
  vite que sous Windows, où il tourne en mode immédiat. `forge mesurer`, qui mesure sans
  compilation, le signale sous ses tableaux.
- **L'arrêt.** SIGTERM (arrêt du système, `docker stop`, `timeout`, `kill`) met l'entraînement en
  pause, avec sauvegarde, comme Ctrl+C.

## Tester

```powershell
cd projets/forge
uv run --extra gpu pytest -q   # tous les tests, dont celui de la carte graphique
uv run --extra cpu pytest -q   # le test de la carte graphique est sauté
```

Les tests marqués `gpu` sont sautés tout seuls quand CUDA est absente. En intégration continue,
`.github/workflows/python.yml` teste ce projet dans un job à part (« Tests de forge », sous Linux
et sous Windows) : `uv run --locked --extra cpu pytest -q --durations=15`, qui liste aussi les
15 tests les plus lents.
