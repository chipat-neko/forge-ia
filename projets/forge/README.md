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
`docs/mesures/entrainement-2026-11.md`). Dès son premier fragment écrit, l'état du flux est tenu :
les reprises suivantes ne relisent rien. Si le jeu refuse l'état enregistré (autre source, autre
version de `datasets`), la commande s'arrête avec un message, sans rien écrire. Une source n'est
terminée que lorsque son fichier `.complet` existe. Le mélange par défaut est défini une seule fois,
dans `forge.donnees.melange.MELANGE_PAR_DEFAUT`.

## Télécharger les conversations de la vague 2

Pour affiner ton IA, la vague 2 lit neuf sources de conversations et d'évaluation sur Hugging
Face (Luth-2, Aya, OASST2, OpenCoder, IFEval-FR, MGSM-rev2, GSM8K-Platinum-fr et HumanEval ;
licences, liens et filtres dans `docs/donnees.md`, section « Vague 2 »). `--liste` donne pour
chacune son usage, sa licence et son lien :

```powershell
uv run --extra gpu python -m forge conversations --liste
```

Une source se télécharge en flux, par fragments de 50 000 éléments, sous
`FORGE_DONNEES/conversations/<source>/`. `--exemples-max` s'arrête après N éléments gardés (20
suffisent pour vérifier les colonnes) ; sans lui, la commande va jusqu'au bout de la source :

```powershell
uv run --extra gpu python -m forge conversations --source aya_fr --exemples-max 20
```

La reprise est celle des textes : après une coupure (réseau, courant, disque plein) ou un Ctrl+C,
on relance la même commande, qui repart de la position du flux gardée dans `etat.json` et rend les
mêmes fichiers qu'un téléchargement d'une traite. Ctrl+C valide le fragment en cours et affiche la
commande de reprise ; un second Ctrl+C arrête tout de suite. `.complet` garde le nom, la licence,
l'usage et les comptes (lignes lues, gardées, écartées par raison).

Quatre sources sont réservées à l'évaluation : IFEval-FR, MGSM-rev2, GSM8K-Platinum-fr et
HumanEval. Elles ne vont jamais dans un entraînement : `forge.conversation.sources.source_d_entrainement`
et `forge.conversation.telechargement.lire_pour_entrainement` les refusent.

## Générer des problèmes de raisonnement

Pour apprendre à ton IA à raisonner (le SFT de raisonnement puis le mini-GRPO de la partie 1.9), la forge
fabrique elle-même des problèmes de calcul en français, plus faciles que GSM8K : addition, soustraction,
multiplication, partage, achats et âges, de 1 à 3 étapes. Chacun vient d'une graine, avec sa réponse et
une trace courte (`23 + 41 = 64`, une étape par ligne) : la réponse est calculée en même temps que l'énoncé
s'écrit, donc toujours juste. `forge.raisonnement.verification` lit la réponse d'une sortie de ton IA
(écritures françaises comprises : `1 234`, `12,5`, `−3`) et la compare à la bonne ; seul le texte compte,
jamais la pensée.

```powershell
uv run --extra gpu python -m forge problemes --sortie entrainement --nombre 20000 --graine-depart 0
uv run --extra gpu python -m forge problemes --sortie evaluation --nombre 500 --graine-depart 1000000 --difficultes 1,2 --familles addition,partage
```

Les fichiers vont sous `FORGE_DONNEES/problemes/<sortie>/` : `problemes-*.jsonl.gz` par fragments,
`index.json` (l'usage, les graines, les familles, les difficultés) et `.complet` à la fin. Relancer la
même commande ne refait rien ; une coupure en cours d'écriture reprend au dernier fragment. Chaque usage
a sa plage de graines (entraînement 0, évaluation 1 000 000, RL 2 000 000, préférences 3 000 000, victoire
4 000 000, validation RL 5 000 000) : les graines de 1 000 000 à 1 999 999 sont celles de l'évaluation, qui
ne va jamais dans un entraînement. Ses problèmes n'emploient que des prénoms que les autres usages
n'emploient jamais : aucun problème d'entraînement ne peut leur être identique. Il en va de même de la
validation du RL (graines de 5 000 000 à 5 999 999, usage `validation_rl` dans `index.json`), que le RL
ne doit pas avoir vue. Une liste de graines ne peut pas enjamber l'une de ces deux plages. Les énoncés en double sont retirés, donc le jeu peut compter un peu moins
de problèmes que demandé.

## Préparer un jeu d'affinage

`preparer` assemble les sources téléchargées (voir plus haut) selon une recette : elle tire les
exemples, retire les doublons et tout ce qui ressemble à un jeu d'évaluation (8 mots de suite en
commun avec une invite d'IFEval-FR, de MGSM, de GSM8K-Platinum-fr, de HumanEval ou d'un problème
d'évaluation), encode les conversations avec le format de ton IA, les empaquette en rangées de
2 049 jetons et écrit le jeu. Deux recettes existent : `sft-1.7` (le SFT de la partie 1.7) et
`raisonnement-1.9` (le SFT de raisonnement de la partie 1.9) ; leurs parts sont dans
`docs/donnees.md`, section « Vague 2 : les jeux d'affinage ».

```powershell
uv run --extra gpu python -m forge preparer --recette sft-1.7
uv run --extra gpu python -m forge preparer --recette sft-1.7 --sortie sft-essai
```

Le jeu va sous `FORGE_DONNEES/affinage/<recette>/` (ou `<sortie>`) : `train/` et `val/`, `index.json`
(les comptes de chaque source : lus, gardés, doublons, contaminés, trop longs, avec leur licence et
leur lien), `ids.txt.gz` (les invites apprises) et `.complet`. Les sources de la recette doivent être
téléchargées en entier (`forge conversations --source NOM`, `forge problemes --sortie NOM …`) : sinon
la commande dit laquelle manque et quoi lancer. Une recette qui contient un jeu d'évaluation est
refusée. Les jeux d'évaluation absents du disque sont dits : la décontamination ne les compare pas.

Deux préparations donnent le même jeu, à l'octet près. Rien n'est écrit avant la fin de la lecture, et
`.complet` vient en dernier : après une coupure ou un Ctrl+C, on relance la même commande, qui refait
le même jeu.

## Construire les paires de préférences de 1.8

`preferences` fait écrire à une version publiée (ton-ia-1.7) deux réponses par invite. Les invites sont des questions
de Luth-2 que le SFT n'a pas apprises, avec une ou deux consignes vérifiables, et des problèmes de calcul de
difficulté 1. Les réponses sont notées par des contrôles programmés, sans juge : réponse terminée, puis juste,
consignes respectées, en français, de 3 à 300 mots. La meilleure et la pire forment une paire si la meilleure est
terminée (et juste, pour un problème) ; sinon l'invite compte « sans bonne réponse », et une égalité ne donne rien.
Les invites passent par la même décontamination que `preparer`.

```powershell
uv run --extra gpu python -m forge preferences --modele "$env:FORGE_DONNEES\publications\ton-ia-1.7" --recette preferences-1.8
uv run --extra gpu python -m forge preferences --modele "$env:FORGE_DONNEES\publications\ton-ia-1.7" --recette preferences-1.8-court
```

Le travail avance par paquets de 512 invites, écrits dans `FORGE_DONNEES/affinage/<recette>/paires/`. Ctrl+C finit
le paquet en cours, puis s'arrête : relance la même commande pour reprendre au paquet suivant, avec les mêmes paires
qu'en une traite. Le lot de génération est choisi au premier départ et ne change plus : si la carte est trop
occupée pour un lot de 32 réponses à la fois, la commande ne part pas et demande de libérer la carte ; à la
reprise, il faut le même appareil et la même mémoire libre. À la fin, un jeu `dpo` (rangée choisie, rangée
rejetée) est écrit à côté. Son `index.json` donne les invites, les paires, les égalités, les invites sans bonne
réponse, le taux de paires utilisables, le critère qui a départagé chaque paire, et la longueur moyenne (en
jetons) des réponses choisies et rejetées, avec la part des paires où la choisie est la plus courte. La commande
affiche ces chiffres ; si le taux de paires utilisables est sous 20 %, elle le dit et rend le code 5.

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

## Affiner ton IA

`entrainer` affine aussi une version publiée de ton IA, au lieu de partir de poids tirés au hasard.
C'est la même boucle : pause, reprise, journal et sauvegardes ne changent pas. Trois réglages du TOML
décident de ce qui change :

- `methode` : `"pre_entrainement"` (par défaut : la section précédente) ou `"sft"`, l'affinage
  supervisé. Ton IA apprend alors des conversations, et la perte ne porte que sur les jetons appris
  (les réponses de l'assistant) : c'est leur moyenne sur tout le pas, tous micro-lots compris. Ou
  `"dpo"`, l'apprentissage par préférences, ou `"grpo"`, l'apprentissage par renforcement (plus bas) ;
- `depart` : la version publiée d'où l'on part, obligatoire pour un affinage. Un nom va sous
  `FORGE_DONNEES/publications/` (le dossier que remplit `python -m forge publication --etiquette
  ton-ia-1.5`), un chemin absolu est gardé tel quel. Ses poids sont copiés dans le modèle avant le
  premier pas ; ses dimensions doivent être celles du `preset`, et son tokenizer celui du jeu ;
- `donnees` : pour le SFT et la DPO, un jeu d'affinage, sous `FORGE_DONNEES/affinage/`. Ses rangées ont la
  longueur `longueur` (par défaut, le contexte du modèle), et `taille_lot_jetons` compte leurs
  positions, bourrage compris.

Par exemple, les lignes propres à un affinage de `ton-ia-1.5` (433,6 millions de paramètres, preset
« tres_grand ») ; les autres réglages sont ceux de `configs/mini.toml` :

```toml
methode = "sft"
depart = "ton-ia-1.5"        # FORGE_DONNEES/publications/ton-ia-1.5
preset = "tres_grand"        # les dimensions de la version de départ
poids_decroissance = 0.0     # ne pas tirer les poids vers 0, loin de la version de départ
```

La pause et la reprise sont celles du pré-entraînement : Ctrl+C, puis la même commande avec
`--reprendre`. En reprenant, le chemin de `depart` peut changer (la même version, rangée ailleurs) ;
une autre version est refusée, car la sauvegarde retient le nom de la version de départ et
l'empreinte SHA-256 de ses poids. Elle retient aussi la méthode et l'empreinte du tokenizer de la
version de départ, que `forge exporter` vérifie.

Pour un essai chronométré, `--arreter-apres N` s'arrête au pas N, avec une sauvegarde ;
`--reprendre` continue ensuite jusqu'à la fin prévue :

```powershell
uv run --extra gpu python -m forge entrainer --config configs/mini.toml --arreter-apres 20
uv run --extra gpu python -m forge entrainer --config configs/mini.toml --reprendre
```

Avec `methode = "dpo"`, ton IA apprend de paires de préférences : `donnees` est un jeu `dpo`, celui
qu'écrit `forge preferences`. La version de départ sert aussi de référence : avant le premier pas, la
log-probabilité de chaque réponse selon elle est calculée une seule fois et rangée dans le jeu
(`reference.bin`, avec `reference.json` qui nomme la version) ; un autre entraînement depuis la même
version, ou une reprise, la relit. Ce calcul passe une fois sur toutes les rangées du jeu : il affiche
son avancement toutes les 30 secondes, et Ctrl+C l'arrête sans rien écrire (la reprise le refait).
`micro_lot` doit être pair : une paire tient dans un même micro-lot. La table `[dpo]` règle la
méthode (ici, ses valeurs par défaut).

Un exemple complet, qui se lance tel quel sur le jeu de `forge preferences --recette preferences-1.8`
(rangées de 768 jetons) ; les réglages de ton IA 1.8 viendront avec son entraînement :

```toml
methode = "dpo"
depart = "ton-ia-1.7"          # la version de départ, qui sert aussi de référence
preset = "tres_grand"          # les dimensions de la version de départ
donnees = "preferences-1.8"    # FORGE_DONNEES/affinage/preferences-1.8
longueur = 768                 # la longueur des rangées du jeu
jetons_total = 4_915_200       # 100 pas
taille_lot_jetons = 49_152     # 32 paires par pas : un multiple de micro_lot × longueur
micro_lot = 2                  # pair
taux_max = 1e-6
echauffement = 10
poids_decroissance = 0.0
evaluation_tous_pas = 20
appareil = "cuda"
sortie = "essai-dpo"

[dpo]
beta = 0.1                     # la force de la préférence
normaliser_longueur = false    # true : comparer les gains par jeton plutôt que par réponse
poids_sft = 1.0                # le poids du terme SFT sur la réponse choisie (0 l'enlève)
```

Le journal écrit à chaque pas la log-probabilité par jeton des réponses choisies et rejetées, leurs
récompenses, la marge entre elles et l'exactitude (la part des paires déjà dans le bon ordre) ;
`forge suivi` montre la log-probabilité des choisies et l'exactitude. La validation mesure la perte de
la DPO et l'exactitude sur les 256 premières paires de validation.

Avec `methode = "grpo"`, ton IA apprend par renforcement, à la manière de nanochat : à chaque pas, elle
écrit plusieurs réponses à chaque problème d'un lot, une réponse juste reçoit une récompense de 1 (sinon
0), et elle apprend à rendre plus probables les réponses meilleures que la moyenne de leur problème, sans
KL ni écrêtage. `donnees` est un dossier de problèmes d'entraînement de `forge problemes` (sous
`FORGE_DONNEES/problemes/`) ; ceux de l'évaluation et de la validation du RL sont refusés. Il n'y a ni
`jetons_total` ni `taille_lot_jetons` : la table `[grpo]` donne le nombre de pas (`pas`, obligatoire) et le
tirage des réponses ; `micro_lot` est le nombre de réponses apprises d'un coup.

Avant le premier pas d'un entraînement neuf, un **contrôle de départ** fait répondre la version de départ
à `controle_invites` problèmes du dossier, `controle_reponses` fois chacun. Le RL n'amplifie qu'un
comportement déjà présent : si aucune réponse n'est juste, il n'aurait aucun signal, et rien n'est lancé.
La commande s'arrête alors sans rien sauvegarder, avec le code 6 et le message « Aucune des N réponses
n'est juste : le RL n'aurait aucun signal. Rien n'est lancé. ». Dans tous les cas, le résultat va au
journal et dans `controle.json`, dans la sortie : `invites`, `reponses`, `justes`, `taux` et `lance` (vrai si
le RL peut partir), plus sa durée et la version de départ. `--arreter-apres 0` fait seulement ce contrôle,
sans pas ni sauvegarde (l'exemple plus bas).

Le contrôle affiche son avancement toutes les 30 secondes ; Ctrl+C l'arrête sans rien sauvegarder (la
reprise le refait). Une reprise depuis une sauvegarde ne le refait pas. Si la mémoire de la carte manque
pendant une génération (le contrôle, les tirages, la validation), le message dit de réduire
`lot_de_generation` dans `[grpo]` : on peut le changer en reprenant, comme augmenter `pas`.

Un exemple complet, sur des problèmes de `forge problemes --sortie rl-1.9 --nombre 20000 --graine-depart
2000000 --difficultes 1,2`, avec les valeurs de nanochat ; les réglages de ton IA 1.9 viendront avec son
entraînement :

```toml
methode = "grpo"
depart = "ton-ia-1.9-traces"   # la version de départ
preset = "tres_grand"          # les dimensions de la version de départ
donnees = "rl-1.9"             # FORGE_DONNEES/problemes/rl-1.9, d'usage entrainement
micro_lot = 8                  # les réponses apprises d'un coup
taux_max = 1e-6
echauffement = 10
poids_decroissance = 0.0
evaluation_tous_pas = 20
appareil = "cuda"
sortie = "essai-grpo"

[grpo]
pas = 400
invites_par_pas = 16           # problèmes par pas
reponses_par_invite = 16       # réponses par problème, comparées entre elles
jetons_max_reponse = 256       # au-delà, la réponse est coupée, donc fausse
temperature = 1.0
top_k = 50
lot_de_generation = 32         # réponses écrites ensemble : à réduire si la mémoire manque
controle_invites = 200         # le contrôle de départ : 200 problèmes…
controle_reponses = 8          # … × 8 tirages
evaluation_invites = 200       # les problèmes de la validation
```

Enregistré sous `essai-grpo.toml`, il se lance d'abord pour le seul contrôle de départ, puis, si le contrôle
a trouvé des réponses justes, pour de bon (sans sauvegarde à reprendre, c'est un entraînement neuf : le
contrôle, identique, est refait avant le premier pas) :

```powershell
uv run --extra gpu python -m forge entrainer --config essai-grpo.toml --arreter-apres 0
uv run --extra gpu python -m forge entrainer --config essai-grpo.toml
```

Le journal écrit à chaque pas la perte, la récompense moyenne (la part des réponses justes), la part des
problèmes sans signal (`groupes_sans_signal` : toutes leurs réponses ont la même récompense, ils
n'apprennent rien), la longueur moyenne des réponses et les temps de génération et d'apprentissage ; un
pas sans aucun signal ne bouge pas les poids. La validation (`reussite_val`) est la part de 200 problèmes
réussis en glouton, tirés des graines de la validation du RL (5 000 000 et suivantes, aux difficultés du
dossier), que l'entraînement ne voit jamais : `meilleur.pt` garde la plus haute. `forge suivi` montre la
récompense moyenne et la dernière réussite de validation.

### Ton IA 1.7 : apprendre à converser

La version 1.7 est le premier vrai affinage : un SFT de `ton-ia-1.5` sur des conversations en
français. Les données, puis les deux entraînements (complet et court), dans l'ordre, depuis
`projets/forge` :

```powershell
uv run --extra gpu python -m forge publication --etiquette ton-ia-1.5
uv run --extra gpu python -m forge conversations --source luth2_conversation
uv run --extra gpu python -m forge conversations --source aya_fr
uv run --extra gpu python -m forge conversations --source oasst2_fr
uv run --extra gpu python -m forge conversations --source ifeval_fr
uv run --extra gpu python -m forge conversations --source mgsm_rev2_fr
uv run --extra gpu python -m forge conversations --source gsm8k_platinum_fr
uv run --extra gpu python -m forge conversations --source humaneval
uv run --extra gpu python -m forge preparer --recette sft-1.7
uv run --extra gpu python -m forge entrainer --config configs/sft-1.7.toml
uv run --extra gpu python -m forge entrainer --config configs/sft-1.7-court.toml
```

Les quatre jeux d'évaluation ne servent pas à l'entraînement : `preparer` les lit pour écarter les
exemples qui leur ressemblent. `configs/sft-1.7.toml` lit deux fois les rangées d'entraînement, au taux
1e-4 (3 338 pas : 4 h 44 min 51 s de calcul sur la RTX 5070 Ti, 4 h 52 min 20 s avec le chargement) ;
`configs/sft-1.7-court.toml` garde les mêmes réglages pour une heure environ (739 pas : 1 h 04 min 05 s).
Un premier entraînement au taux 3e-4 faisait plus oublier le texte du pré-entraînement : ses réglages
sont gardés pour comparer, dans `configs/sft-1.7-3e-4.toml` et `configs/sft-1.7-court-3e-4.toml`. Puis
l'export de la meilleure sauvegarde de chacun, et l'évaluation de l'étape 1.7, avec ton-ia-1.5 en regard
(deux minutes par version sur la carte ; l'étape 1.9, avec ses problèmes, environ 20 minutes) :

```powershell
uv run --extra gpu python -m forge exporter --sauvegarde "$env:FORGE_DONNEES\entrainements\sft-1.7\sauvegardes\meilleur.pt" --sortie "$env:FORGE_DONNEES\publications\ton-ia-1.7" --poids ton-ia-1.7.safetensors
uv run --extra gpu python -m forge exporter --sauvegarde "$env:FORGE_DONNEES\entrainements\ton-ia-1.7-court\sauvegardes\meilleur.pt" --sortie "$env:FORGE_DONNEES\publications\ton-ia-1.7-court" --poids ton-ia-1.7-court.safetensors
uv run --extra gpu python -m forge evaluer-etape --modele "$env:FORGE_DONNEES\publications\ton-ia-1.7" --etape 1.7 --reference "$env:FORGE_DONNEES\publications\ton-ia-1.5"
uv run --extra gpu python -m forge evaluer-etape --modele "$env:FORGE_DONNEES\publications\ton-ia-1.7-court" --etape 1.7
uv run --extra gpu python -m forge evaluer-etape --modele "$env:FORGE_DONNEES\publications\ton-ia-1.7" --etape 1.9 --reference "$env:FORGE_DONNEES\publications\ton-ia-1.5"
```

Les mesures (débit, mémoire, coût du masque par document, balayage du taux d'apprentissage, sessions,
courbe, évaluation et échantillons) sont dans `docs/mesures/ton-ia-1.7.md`, et la fiche de la version
dans `docs/mesures/ton-ia-1.7-LISEZMOI.md`.

## Suivre un entraînement

`suivi` lit le journal d'un entraînement et dit où il en est : état (en cours, en pause, fini,
arrêté sans pause), pas, perte récente et de validation, débit, temps restant estimé et dernière
sauvegarde ; pour le GRPO, la récompense moyenne et la réussite de validation, et le débit en secondes
par pas, ou, après un contrôle de départ sans aucune réponse juste (code 6), que rien n'a été lancé. Il ne fait que lire et n'importe pas PyTorch : on peut le lancer aussi souvent qu'on
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

Avant d'écrire quoi que ce soit, l'export vérifie aussi que la sauvegarde vient de ce tokenizer :
il compare l'empreinte de ses fusions (SHA-1) que retient la sauvegarde (pour un affinage, celle du
tokenizer de sa version de départ), ou à défaut, pour un pré-entraînement, celle de l'`index.json` de
ses jetons, à celle du tokenizer figé. Un autre tokenizer est refusé ; si
l'empreinte est introuvable, l'export a lieu, avec un message « Attention » qui dit ce qui n'a pas
été vérifié.

Chaque fichier est écrit d'un coup ; la commande affiche la taille et l'empreinte SHA-256 de
chacun. La version publiée de ton IA est la Release `ton-ia-1.5` du dépôt : ces trois fichiers,
plus `rapport.json` (son évaluation d'origine), `rapport-2026-11-17.json` (la même, aux bits
par octet exacts), sa fiche `LISEZMOI.md` et son document `ton-ia-1.5.md` (dans le dépôt :
`docs/mesures/ton-ia-1.5-LISEZMOI.md` et `docs/mesures/ton-ia-1.5.md`). Pour la recharger,
depuis `projets/forge`, la commande `publication` télécharge les trois fichiers du modèle
(`publications/ton-ia-1.5` sous `FORGE_DONNEES`, ou le dossier de `--dossier`) et affiche la taille et
l'empreinte SHA-256 de chacun. Un fichier se télécharge sous le nom `….partiel`, renommé quand il
est complet : après une coupure, relance la même commande, seul ce qui manque est repris.

```powershell
uv run --extra gpu python -m forge publication --etiquette ton-ia-1.5   # --extra cpu sans carte NVIDIA
```

### Recharger une version publiée

`charger_publication` fait ce que dit la fiche (poids liés rétablis, float32, mode évaluation) et
vérifie le tokenizer par son empreinte. Le dossier doit contenir exactement un fichier
`*.safetensors`, `config.json` et `tokenizer-ton-ia-v1.json`. Si tu as déjà les fichiers, mets-les
dans `$FORGE_IA_MODELES/ton-ia-1.5` : `telecharger_publication` rend alors ce dossier, sans réseau.

```python
from forge.modele import generer
from forge.publication import charger_publication, telecharger_publication

pub = charger_publication(telecharger_publication("ton-ia-1.5"))  # pub.version, pub.empreinte_des_poids
modele, tokenizer = pub.modele, pub.tokenizer

# Faire écrire ton IA : elle prolonge le début donné.
fin = tokenizer.id_special("<|fin_texte|>")  # pour ton IA, ce jeton marque aussi le début d'un texte
debut = [fin, *tokenizer.encoder("Il était une fois")]
suite = generer(modele, debut, 40, temperature=0.8, top_k=50, graine=0, arret=fin)
print("Il était une fois" + tokenizer.decoder([jeton for jeton in suite if jeton != fin]))
```

Pour vérifier un fichier téléchargé, compare son empreinte à celle de la fiche :
`Get-FileHash ton-ia-1.5.safetensors`.

## Évaluer une étape : les mêmes mesures d'une version à l'autre

`evaluer-etape` fait passer à une version publiée les mesures de son étape, et à ton-ia-1.5 les mêmes :
le plan 8 montre ainsi ton IA d'un chapitre à l'autre, sur les mêmes tests. L'étape dit quelles mesures
(`1.7` : perte de conversation, IFEval-FR, tenue des réponses, oubli, échantillons ; `1.8` : celles de 1.7, plus
la victoire contre `--reference` ; `1.9` : IFEval-FR, tenue, oubli, problèmes générés, MGSM, GSM8K-Platinum en
français, échantillons). La version est un dossier
publié (`ton-ia-1.5.safetensors`, `config.json`, `tokenizer-ton-ia-v1.json`) ; `--reference` en donne un
second, qui passe les mêmes mesures, mises en regard dans le tableau :

```powershell
uv run --extra gpu python -m forge evaluer-etape --modele "$env:FORGE_DONNEES\publication\ton-ia-1.5" --etape 1.9
uv run --extra gpu python -m forge evaluer-etape --modele "$env:FORGE_DONNEES\publications\ton-ia-1.7" --etape 1.7 --reference "$env:FORGE_DONNEES\publication\ton-ia-1.5" --n-max 20
```

À l'étape `1.8`, la victoire fait répondre les deux versions (en glouton) aux mêmes invites : 500 par défaut, ou,
avec `--invites NOM`, les invites de validation du jeu de paires `NOM`, celles qui départagent les essais d'un
balayage. Elle les note comme les paires et donne le taux de victoire de la version, une égalité comptant une
demie. Ce sont les critères des paires : un taux élevé est attendu après la DPO, ce n'est pas un juge.

```powershell
uv run --extra gpu python -m forge evaluer-etape --modele "$env:FORGE_DONNEES\publications\ton-ia-1.8" --etape 1.8 --reference "$env:FORGE_DONNEES\publications\ton-ia-1.7"
uv run --extra gpu python -m forge evaluer-etape --modele "$env:FORGE_DONNEES\publications\ton-ia-1.8" --etape 1.8 --reference "$env:FORGE_DONNEES\publications\ton-ia-1.7" --invites preferences-1.8 --n-max 200
```

Le rapport (`rapport.json` pour les programmes, `rapport.md` pour la lecture) va dans
`FORGE_DONNEES/evaluations/<version>-<étape>/` (ou `--sortie`). `--n-max N` limite chaque mesure à ses N
premiers exemples, pour un essai court ; `--appareil cpu` force le processeur. Le JSON est stable (version
du rapport 1) : `version`, `empreinte` (SHA-256 des poids), `etape`, `date`, `mesures`, `secondes`, `invites` (le
jeu de paires de `--invites`, ou `null`), et `reference` s'il y en a une. Chaque mesure est écrite ainsi :

- `perte_conversation` : `{perte, n}`, la perte d'affinage sur la validation de `affinage/sft-1.7` ;
- `ifeval_fr` : `{invite_stricte, consigne_stricte, n}`, IFEval-FR en glouton, 512 jetons ;
- `tenue` : `{terminee, fr, autre, indetermine, mots_moyens, n}`, sur les réponses d'IFEval-FR et aux 100
  premières invites de la validation de `sft-1.7` : la part terminée par `<|fin_tour|>`, la langue des réponses
  (`forge.evaluation.langue`, des parts de 0 à 1) et leur longueur ;
- `oubli` : `{perte, bits_par_octet, n}`, sur 64 morceaux de `jetons/principal/val` (la mesure du plan 6) ;
- `echantillons` : `[{invite, texte, pensee, terminee}]`, dix invites fixes en glouton, gardées telles quelles ;
- `problemes` : `{exactitude, terminee, lot, reussite_8, par_famille, par_difficulte, n}`, 400 problèmes générés
  de la plage d'évaluation, en glouton puis en 8 essais (température 1, top-k 50, lot fixe de 32 écrit dans `lot`
  : le tirage dépend du lot, donc `reussite_8` se refait à l'identique) ; `reussite_8` est « au moins un essai juste
  sur 8 », sans le glouton : elle peut être plus basse que `exactitude` ;
- `mgsm_fr` et `gsm8k_platinum_fr` : `{exactitude, terminee, n}`, en glouton, 384 jetons. `terminee` (de 0 à 1) est la
  part de réponses finies avant la limite : un 0 % d'exactitude avec 0 % de réponses terminées veut dire « coupé »,
  pas « faux » ;
- `victoire` : `{victoires, egalites, defaites, taux, mots_modele, mots_reference, n}`, la version contre
  `--reference` sur les mêmes invites, en glouton, 384 jetons ; la référence a les mêmes clés, vues de son côté
  (son taux est le complément). Sans `--reference`, la mesure est absente.

Une réponse vide ou coupée par la limite de jetons est comptée telle quelle (fausse pour un problème). Une
mesure dont les données manquent rend `{"absente": "<raison>"}` et dit quelle commande lancer
(`forge conversations --source ifeval_fr`, `forge preparer --recette sft-1.7`, `forge encoder`). Sur la
carte, le lot de génération est le plus grand que la mémoire libre permet.

## Exécuter le code que ton IA écrit

Pour noter le code de ton IA (HumanEval et sa version française, au chapitre 1.10), la forge l'exécute avec
ses tests. `forge.code.execution.executer` lance un programme Python dans un sous-processus limité et dit
comment il a fini (`reussi`, `echec`, `delai`, `memoire` ou `erreur_systeme`) ; `executer_tous` en lance
plusieurs à la fois, autant que de fils de calcul. Toute commande de la forge qui exécute du code généré
passe par là :

```powershell
uv run --extra gpu python -c "from forge.code.execution import executer; print(executer('print(1 + 1)', delai=5))"
```

Ce qui est limité :

- **le délai** (5 s par défaut) : au-delà, le programme est arrêté (`delai`) ;
- **la mémoire** (512 Mio par défaut) : une allocation de trop lève `MemoryError` (`memoire`) ;
- **les processus** : sous Windows, un objet Job n'en admet qu'un (le programme ne peut pas en créer un
  autre lui-même) et tue ce qu'il contient à la fin, ou quand la forge meurt ; le programme ne démarre qu'une
  fois rangé dans le Job. Sous Linux, le programme ouvre sa propre session, et tout son groupe de processus
  est tué à la fin ;
- **le dossier et la sortie** : le programme tourne dans un dossier jetable sous `TEMP`, effacé ensuite, avec
  l'interpréteur Python de base en mode isolé (`-I`, la bibliothèque standard seulement) et un environnement
  réduit ; sa sortie est tronquée à 10 000 caractères.

Ce qui n'est **pas** empêché, car ce n'est pas un vrai bac à sable :

- **le réseau** : le programme peut ouvrir des connexions, télécharger ou envoyer des données ;
- **l'écriture dans tes dossiers**, hors du dossier jetable : tout ce que ton compte a le droit de modifier
  ou d'effacer ;
- **la lecture de tes fichiers** : documents, clés, jetons de connexion, données de la forge ;
- sous Windows, un processus qu'un service crée pour le programme (WMI, planificateur de tâches, COM) naît
  hors du Job et lui survit ;
- sous Linux, un processus que le programme lance et qui quitte son groupe (`setsid`) lui survit ; et si la
  forge est tuée net (`kill -9`, noyau du notebook redémarré), le programme en cours va jusqu'à sa fin (la
  limite de temps de calcul arrête une boucle, pas une attente).

Un dossier jetable qui ne s'efface pas (un fichier tenu ouvert par un antivirus, par exemple) ne fait pas
perdre le résultat : un avertissement donne son chemin, à effacer à la main.

C'est fait pour le code de ton IA aux problèmes de HumanEval, sur ton PC : du code qui peut boucler, prendre
trop de mémoire ou écrire des mégaoctets, mais qu'on ne soupçonne pas de nuire. Du code venu d'ailleurs, ou
écrit pour nuire, doit tourner dans une machine virtuelle ou un conteneur sans réseau.

Le score se compte par `forge.code.passk.pass_a_k(n, c, k)` : sur `n` réponses tirées pour un problème, dont `c`
passent les tests, la chance qu'au moins une de `k` réponses passe, estimée sans biais (article Codex,
arXiv 2107.03374, section 2.1).

## Discuter avec une version publiée

`discuter` ouvre une conversation dans le terminal avec une version affinée (ton-ia-1.7 et les suivantes ;
ton-ia-1.5 ne sait que prolonger un texte et ne répond pas à une question) :

```powershell
uv run --extra gpu python -m forge discuter --modele "$env:FORGE_DONNEES\publications\ton-ia-1.7" --temperature 0.7
```

Chaque ligne est un tour ; ton IA répond avec toute la conversation sous les yeux. `/nouveau` repart de zéro,
`/quitter` sort. `--systeme "TEXTE"` ouvre la conversation par un message système (gardé après `/nouveau`).
Quand la fenêtre de contexte est pleine, le message dit de faire `/nouveau`. Une réponse coupée par la limite
de 512 jetons est signalée et n'est pas gardée dans la conversation (ni sa question) ; sa pensée, s'il y en a une,
s'affiche à part.

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
