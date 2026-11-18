# Ton IA 1.7 : apprendre à converser

Ton IA 1.7 est le premier vrai affinage de ton IA : un affinage supervisé (SFT) de la version publiée
`ton-ia-1.5` sur des conversations en français. Ce document est commencé le 18 novembre 2026, avec les
données, l'essai chronométré et le balayage du taux d'apprentissage. L'entraînement complet, la version
courte, l'évaluation et les échantillons viendront ensuite.

## En bref

- **La version de départ :** `ton-ia-1.5`, téléchargée par `forge publication` comme un lecteur la
  télécharge, en 43 s. Ses trois empreintes SHA-256 sont celles de sa fiche.
- **Les données :** 560 448 conversations de Luth-2 gardées sur 1 969 768 lignes, plus Aya et OASST2 en
  français. Les sources amont dont les invites viennent de Llama ou d'OpenAI sont écartées (Dolci,
  Tulu 3 Personas, SmolTalk2) : toutes les lignes gardées de Luth-2 viennent de Nemotron. Le filtre
  « stackoverflow » n'écarte aucune ligne, sur tout le jeu (voir « Une réserve sur Luth-2 »).
- **Le jeu `sft-1.7` :** 135 471 conversations, 111 497 280 jetons (dont 85 483 056 appris), empaquetées
  en 53 401 rangées d'entraînement et 1 095 de validation. 3 min 37 s de préparation, 5,47 Gio de
  mémoire au plus, 535,5 Mio sur D:.
- **La carte, pas le processeur :** 13 444 jetons par seconde sur la carte (micro-lot 1, 12,8 Go au
  plus), 196,6 sur le processeur avec ses 16 fils : 68 fois moins.
- **Le masque par document coûte 34 %** d'un pas complet : 4,885 s contre 3,651 s sans masque.
- **Le taux d'apprentissage : 1e-4.** Trois essais de 300 pas : la perte de validation finit à 1,279
  avec 1e-4, 1,398 avec 3e-5 et 1,526 avec 1e-5. C'est le plus grand taux essayé.
- **Les deux entraînements qui suivent :** le complet, 3 338 pas (deux époques), environ 4 h 45 min ;
  le court, 739 pas, environ 1 h 03 min.

## 1. Les données

### La version de départ

`python -m forge publication --etiquette ton-ia-1.5` a téléchargé la Release dans
`FORGE_DONNEES/publications/ton-ia-1.5`, en 43 s :

| Fichier | Octets | SHA-256 |
| --- | ---: | --- |
| `ton-ia-1.5.safetensors` | 867 161 248 | `0e89f94133ea47a65e2cd19c111beb24f3ae210c9e332f92c6538a2e22b0d6ea` |
| `config.json` | 134 | `ae0207b367080a6577c2d95ef81ba5fb84c6bf2be11d03a07eedd8a9fe598621` |
| `tokenizer-ton-ia-v1.json` | 546 692 | `3001e7ab40630739c4dec807c7a92c0d4fb469cc0fc4afa368704395391f21ba` |

Les trois empreintes sont celles de `docs/mesures/ton-ia-1.5-LISEZMOI.md`.

### Les conversations téléchargées

Le 17 novembre 2026, par `python -m forge conversations --source NOM` (licences et filtres dans
`docs/donnees.md`, section « Vague 2 ») :

| Source | Usage | Licence | Lignes lues | Gardées | Écartées |
| --- | --- | --- | ---: | ---: | --- |
| `luth2_conversation` | entraînement | CC BY 4.0 | 1 969 768 | 560 448 | 1 162 639 domaine, 168 103 source amont, 78 578 générateur |
| `aya_fr` | entraînement | Apache-2.0 | 202 362 | 1 422 | 200 940 langue |
| `oasst2_fr` | entraînement | Apache-2.0 | 13 854 arbres | 359 | 13 494 langue, 1 sans réponse |
| `ifeval_fr` | évaluation | Apache-2.0 | 235 | 235 | aucune |
| `mgsm_rev2_fr` | évaluation | CC BY-SA 4.0 | 250 | 250 | aucune |
| `gsm8k_platinum_fr` | évaluation | MIT | 1 196 | 1 196 | aucune |
| `humaneval` | évaluation | MIT | 164 | 164 | aucune |

Luth-2 a pris 8 min 46 s (9,7 Go de fichiers parquet lus en flux) ; les six autres, moins d'une minute
chacune. Les sept dossiers pèsent 754,5 Mio sur D:, dont 753,8 pour Luth-2. Les quatre jeux
d'évaluation ne servent jamais à l'entraînement : `preparer` les lit seulement pour écarter les
exemples qui leur ressemblent.

### Une réserve sur Luth-2

Les fiches des six sources amont de Luth-2 ont été lues, et chaque valeur de la colonne `source`
comptée sur le jeu entier (le détail, source par source, est dans `docs/donnees.md`). Trois choses en
sortent :

- Dolci-Instruct-SFT, Tulu 3 Personas et SmolTalk2 ont des invites écrites par GPT-4, GPT-4o ou Llama :
  elles sont écartées (`SOURCES_AMONT_ECARTEES` gagne `dolci` et `tulu`). Le domaine `if` (consignes)
  de Luth-2 se vide ainsi entièrement : les consignes de 1.7 ne viennent plus que de `systeme_genere`.
- Le filtre `stackoverflow` n'écarte rien : la colonne `source` ne nomme que le jeu d'origine, jamais
  StackOverflow. Les invites que Nemotron a tirées de StackOverflow (CC BY-SA 4.0, « un petit
  sous-ensemble » d'après sa fiche) ne se reconnaissent pas dans Luth-2. Elles restent dans le jeu, en
  nombre inconnu.
- Le modèle qui a généré les invites synthétiques de Nemotron n'est nommé ni par sa fiche ni par son
  article [non vérifié].

### Le jeu d'affinage `sft-1.7`

`python -m forge preparer --recette sft-1.7`, le 18 novembre 2026 :

| Part | Lus | Gardés | Doublons | Contaminés | Trop longs | Licence |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `luth2_conversation` | 150 000 | 117 230 | 0 | 58 | 32 712 | CC BY 4.0 |
| `aya_fr` | 1 422 | 1 128 | 291 | 0 | 3 | Apache-2.0 |
| `oasst2_fr` | 359 | 359 | 0 | 0 | 0 | Apache-2.0 |
| `systeme_genere` | 20 000 | 16 682 | 0 | 4 | 3 314 | MIT (messages système du dépôt), réponses de Luth-2 (CC BY 4.0) |
| `identite` | 72 | 72 | 0 | 0 | 0 | MIT |
| **Total** | 171 853 | **135 471** | 291 | 62 | 36 029 | |

- **Les rangées :** 111 497 280 jetons, dont 85 483 056 appris (les réponses de l'assistant et leur
  `<|fin_tour|>`), empaquetés en 53 401 rangées d'entraînement et 1 095 de validation, de 2 048
  positions. Aucun exemple écarté à l'empaquetage.
- **Trop longs :** un exemple de plus de 1 536 jetons est écarté, jamais coupé. C'est le cas de 21,8 %
  des conversations tirées de Luth-2 (32 712 sur 150 000).
- **Décontamination :** comparée à IFEval-FR, MGSM-rev2, GSM8K-Platinum-fr et HumanEval (62 exemples
  écartés). HumanEval-FR n'existe pas encore (tâche 20) : la préparation le dit.
- **Les ressources :** 3 min 37 s, 5,47 Gio de mémoire vive au plus (relevée par psutil toutes les
  0,5 s), 561 527 559 octets (535,5 Mio) sur D:.

## 2. L'essai chronométré

Le 18 novembre 2026, carte au repos (moins de 10 % d'utilisation, Ollama ne tournait pas), avec
`configs/sft-1.7.toml` dont seuls changent `micro_lot`, `appareil` et `sortie`, par `--arreter-apres`.
La mémoire de la carte est celle que montre `nvidia-smi`, relevée chaque seconde : elle compte aussi
Windows (environ 0,4 Go au repos). Le débit est la médiane des pas 2 à 10 (le premier pas chauffe la
carte).

### Le micro-lot

Un pas lit 65 536 positions : 32 rangées de 2 048, par micro-lots de 1, 2 ou 4 rangées.

| Micro-lot | Mémoire de la carte au plus | Débit | Ce qui se passe |
| ---: | ---: | ---: | --- |
| 4 | 15 963 Mio sur 16 303 | 392 jetons/s (pas 1) | la carte déborde dans la mémoire partagée de Windows ; essai arrêté au bout de 6 min 42 s |
| 2 | 15 884 Mio | 10 170 jetons/s | presque pleine, et plus lent que 1 |
| 1 | 12 791 Mio | **13 444 jetons/s** | retenu |

Le micro-lot 2 ne fait pas d'erreur de mémoire, mais il remplit la carte à 97 % et va 24 % moins vite
que le micro-lot 1. Le plus grand micro-lot qui tient vraiment est donc 1, et c'est aussi le plus
rapide. Les pertes des deux sont les mêmes au pas 1 (2,208390) : le micro-lot ne change pas le calcul.

### La carte ou le processeur

| Appareil | Pas | Débit | Fils | Mémoire au plus |
| --- | ---: | ---: | --- | --- |
| Carte (RTX 5070 Ti), micro-lot 1 | 10 | 13 444 jetons/s | 0,5 cœur équivalent | 12,8 Go sur la carte, 4,85 Gio de mémoire vive |
| Processeur (Ryzen 7 9800X3D) | 3 | 196,6 jetons/s | 16 fils | 13,97 Gio de mémoire vive |

Sur le processeur, un pas prend 333 s : 196,3, 196,6 et 196,8 jetons par seconde. Les 16 cœurs logiques
travaillent : de 88,5 % à 92,5 % chacun en moyenne sur toute la commande (chargement et sauvegarde
compris), 12 cœurs équivalents pour Python (relevés par psutil chaque seconde). La carte va 68 fois plus
vite : elle est retenue. L'entraînement complet prendrait 12 jours et 21 heures sur le processeur.

### Ce que coûte le masque par document

Une rangée empaquette en moyenne 2,12 conversations ; le masque par document empêche chacune de voir
celle qui la précède. Avec ce masque, l'attention perd le chemin rapide de la carte (la tâche 3 l'avait
vu sur l'attention seule : de 0,15 à 0,63 ms par couche). Mesuré ici sur un pas complet (32 micro-lots
d'une rangée, avant, arrière, écrêtage et AdamW), mêmes rangées, médiane de 6 pas par variante :

| Variante | Secondes par pas | Débit | Mémoire allouée au plus |
| --- | ---: | ---: | ---: |
| Avec le masque par document | 4,885 | 13 416 jetons/s | 11,09 Gio |
| Sans masque (causal seul) | 3,651 | 17 952 jetons/s | 11,02 Gio |

Le masque coûte **34 %** de temps en plus par pas (33,8 %), pour 0,07 Gio de mémoire. Sans lui, le débit
est celui du pré-entraînement de 1.5 (17 316 jetons par seconde en moyenne). L'affinage garde le
masque : sans lui, une conversation lirait la fin de la précédente.

## 3. Le balayage du taux d'apprentissage

Aucune source ne donne le taux d'un SFT pour un modèle de 433,6 millions de paramètres entraîné de zéro.
Trois essais de 300 pas (`jetons_total = 19_660_800`, 19,7 millions de positions), avec les taux
maximaux 1e-5, 3e-5 et 1e-4, chacun dans sa sortie (`entrainements/sft-1.7-balayage-<taux>`). Tout le
reste est `configs/sft-1.7.toml` : micro-lot 1, échauffement de 50 pas, puis descente en cosinus jusqu'au
dixième du taux au pas 300. La perte de validation est mesurée aux pas 100, 200 et 300, sur les mêmes
64 rangées de validation.

**La règle**, fixée avant les essais : garder le taux dont la dernière perte de validation est la plus
basse ; en cas d'égalité à 0,005 près, le plus petit taux.

| Taux maximal | Validation au pas 100 | Au pas 200 | Au pas 300 | Durée de la commande |
| --- | ---: | ---: | ---: | ---: |
| 1e-5 | 1,643 | 1,547 | 1,526 | 25 min 56 s |
| 3e-5 | 1,515 | 1,421 | 1,398 | 25 min 47 s |
| 1e-4 | 1,422 | 1,317 | **1,279** | 25 min 49 s |

La perte d'entraînement, en moyenne par tranche de 25 pas :

| Pas | 1e-5 | 3e-5 | 1e-4 |
| --- | ---: | ---: | ---: |
| 1 à 25 | 2,203 | 2,102 | 1,964 |
| 26 à 50 | 1,935 | 1,755 | 1,613 |
| 51 à 75 | 1,750 | 1,607 | 1,505 |
| 76 à 100 | 1,673 | 1,545 | 1,454 |
| 101 à 125 | 1,604 | 1,482 | 1,393 |
| 126 à 150 | 1,585 | 1,466 | 1,377 |
| 151 à 175 | 1,534 | 1,415 | 1,322 |
| 176 à 200 | 1,559 | 1,438 | 1,342 |
| 201 à 225 | 1,535 | 1,414 | 1,313 |
| 226 à 250 | 1,504 | 1,382 | 1,277 |
| 251 à 275 | 1,516 | 1,391 | 1,281 |
| 276 à 300 | 1,526 | 1,404 | 1,294 |

**Le choix : 1e-4.** Sa dernière perte de validation (1,279) est la plus basse, 0,118 sous celle de
3e-5 : il n'y a pas d'égalité à 0,005 près. Les trois courbes descendent sans saut ni divergence, et à
chaque mesure le plus grand taux est devant. Deux réserves :

- 1e-4 est le bord haut du balayage. Un taux plus grand pourrait aller plus bas, ou diverger sur 3 338
  pas : il n'a pas été essayé.
- Un taux plus grand éloigne aussi plus vite ton IA de 1.5. La perte de validation ne mesure que les
  conversations ; ce que 1.7 oublie de 1.5 sera mesuré à l'évaluation (`oubli`, `forge evaluer-etape`).

Les sauvegardes de 1e-5 et de 3e-5 sont effacées (leurs journaux restent). Celle de 1e-4 reste dans
`entrainements/sft-1.7-balayage-1e-4`.

**Les durées.** Chaque essai a fait ses 300 pas en 1 486 à 1 504 s de calcul : 4,88 s par pas en
médiane, plus environ 10 s à chaque validation, écriture de `meilleur.pt` (1,62 Gio) comprise. Avec le
chargement de ton-ia-1.5 et la sauvegarde finale (4,85 Gio), la commande entière a pris de 25 min 47 s à
25 min 56 s : moins de 30 minutes, comme prévu. Débit médian de 13 371 à 13 426 jetons par seconde ;
carte occupée à 93 % en moyenne, 12,9 à 13,0 Go au plus. Les tests de forge tournaient sur le processeur
pendant les huit premières minutes du deuxième essai : 13 359 jetons par seconde sur ses 20 pas d'alors,
0,6 % sous le premier essai.

## 4. Les deux entraînements qui suivent

- **Le complet** (`configs/sft-1.7.toml`) : 3 338 pas, deux époques des 53 401 rangées d'entraînement
  (218 759 168 positions). Durée prévue d'après le balayage : 3 338 × 4,88 s = 4 h 32 min de pas, plus
  34 validations (6 min), une sauvegarde d'étape toutes les 30 minutes (environ 4 min en tout), le
  chargement et la pause prévue : **environ 4 h 45 min de calcul**. Le plan l'estimait à 3 h, pour
  environ 180 millions de jetons au débit du pré-entraînement (17 316 jetons par seconde). L'écart vient
  du masque par document (34 %) et des 219 millions de positions.
- **Le court** (`configs/sft-1.7-court.toml`) : les mêmes réglages, 739 pas (48 431 104 positions, une
  heure au débit mesuré de 13 444 jetons par seconde), dans la sortie `ton-ia-1.7-court`. Durée prévue :
  739 × 4,88 s = 1 h 00 min de pas, plus 7 validations et une sauvegarde d'étape : **environ 1 h 03 min**
  de calcul.
- **La place sur D:** chaque entraînement garde ses deux dernières sauvegardes d'étape (4,85 Gio chacune)
  et `meilleur.pt` (1,62 Gio) : environ 11,3 Gio. Il reste 184 Go libres.

Les durées réelles, la courbe, l'évaluation et les échantillons viendront ici après ces deux
entraînements.
