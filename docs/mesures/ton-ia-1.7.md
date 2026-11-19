# Ton IA 1.7 : apprendre à converser

Ton IA 1.7 est le premier vrai affinage de ton IA : un affinage supervisé (SFT) de la version publiée
`ton-ia-1.5` sur des conversations en français. Ce document raconte ses données, l'essai
chronométré, le balayage du taux d'apprentissage, l'entraînement du 18 novembre 2026, son évaluation du
19 novembre, et ce que ton IA 1.7 sait faire ou non.

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
- **Le taux d'apprentissage : 3e-4.** Quatre essais de 300 pas : la perte de validation finit à 1,214
  avec 3e-4, 1,279 avec 1e-4, 1,398 avec 3e-5 et 1,526 avec 1e-5. C'est le plus grand taux essayé.
- **L'entraînement :** 3 338 pas (deux époques), 4 h 44 min 35 s de calcul en 3 sessions, le 18
  novembre 2026. La perte de validation baisse à chaque mesure, de 1,424 (pas 100) à **0,941** (pas
  3 338). La version courte : 739 pas, 1 h 04 min 37 s, validation 1,095.
- **L'évaluation**, de 1.5 à 1.7 (version courte entre parenthèses) :
  - réponses terminées : 0,0 % → **52,8 %** (54,0 %) ;
  - réponses en français : 87,2 % → 98,8 % (99,7 %) ;
  - IFEval-FR, invites respectées : 21,7 % → 16,2 % (15,7 %) : **moins bien que 1.5** ;
  - oubli, perte sur le texte du pré-entraînement : 2,347 → 3,766 nats par jeton (2,998) :
    **elle prédit moins bien que 1.5 le texte libre** ;
  - problèmes justes : générés 0 → 3 sur 400 (0), MGSM 0 → 1 sur 250 (0),
    GSM8K-Platinum 0 → 4 sur 1 196 (6).

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
Des essais de 300 pas (`jetons_total = 19_660_800`, 19,7 millions de positions), chacun dans sa
sortie (`entrainements/sft-1.7-balayage-<taux>`) : 1e-5, 3e-5 et 1e-4 d'abord ; puis 3e-4, parce que
1e-4 finissait devant, au bord du balayage. Tout le reste est `configs/sft-1.7.toml` : micro-lot 1,
échauffement de 50 pas, puis descente en cosinus jusqu'au dixième du taux au pas 300. La perte de
validation est mesurée aux pas 100, 200 et 300, sur les mêmes 64 rangées de validation.

**La règle**, fixée avant les essais : garder le taux dont la dernière perte de validation est la plus
basse ; en cas d'égalité à 0,005 près, le plus petit taux.

| Taux maximal | Validation au pas 100 | Au pas 200 | Au pas 300 | Durée de la commande |
| --- | ---: | ---: | ---: | ---: |
| 1e-5 | 1,643 | 1,547 | 1,526 | 25 min 56 s |
| 3e-5 | 1,515 | 1,421 | 1,398 | 25 min 47 s |
| 1e-4 | 1,422 | 1,317 | 1,279 | 25 min 49 s |
| 3e-4 | 1,418 | 1,283 | **1,214** | 25 min 54 s |

La perte d'entraînement, en moyenne par tranche de 25 pas :

| Pas | 1e-5 | 3e-5 | 1e-4 | 3e-4 |
| --- | ---: | ---: | ---: | ---: |
| 1 à 25 | 2,203 | 2,102 | 1,964 | 1,851 |
| 26 à 50 | 1,935 | 1,755 | 1,613 | 1,552 |
| 51 à 75 | 1,750 | 1,607 | 1,505 | 1,491 |
| 76 à 100 | 1,673 | 1,545 | 1,454 | 1,453 |
| 101 à 125 | 1,604 | 1,482 | 1,393 | 1,391 |
| 126 à 150 | 1,585 | 1,466 | 1,377 | 1,374 |
| 151 à 175 | 1,534 | 1,415 | 1,322 | 1,308 |
| 176 à 200 | 1,559 | 1,438 | 1,342 | 1,319 |
| 201 à 225 | 1,535 | 1,414 | 1,313 | 1,278 |
| 226 à 250 | 1,504 | 1,382 | 1,277 | 1,233 |
| 251 à 275 | 1,516 | 1,391 | 1,281 | 1,230 |
| 276 à 300 | 1,526 | 1,404 | 1,294 | 1,238 |

**Le choix : 3e-4.** Sa dernière perte de validation (1,214) est la plus basse, 0,066 sous celle
de 1e-4 : il n'y a pas d'égalité à 0,005 près. Les quatre courbes descendent sans saut ni divergence, et
à chaque mesure le plus grand taux est devant ; au pas 100, 3e-4 n'a que 0,004 d'avance sur 1e-4. Deux
réserves :

- 3e-4 est à nouveau le bord haut du balayage. Un taux plus grand pourrait aller plus bas, ou diverger
  sur 3 338 pas : il n'a pas été essayé.
- Un taux plus grand éloigne aussi plus vite ton IA de 1.5. La perte de validation ne mesure que les
  conversations ; ce que 1.7 oublie de 1.5 sera mesuré à l'évaluation (`oubli`, `forge evaluer-etape`).

Les sauvegardes de 1e-5, 3e-5 et 1e-4 sont effacées (leurs journaux restent). Celle de 3e-4 reste dans
`entrainements/sft-1.7-balayage-3e-4`.

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

Les durées réelles sont dans les sections 5 et 6.

## 5. L'entraînement complet

Lancé par `travail-long.ps1` (fenêtre « Ton IA : sft-1.7 », journal `journaux\sft-1.7.log`), avec le
chien de garde, le 18 novembre 2026. Fini au pas 3 338 à 08:48:34, code 0.

| Session | Démarrage | Premier pas prêt | Fin | Pas | Durée de Python | Fin de la session |
| --- | --- | --- | --- | --- | ---: | --- |
| 1 | 02:34:41 | 02:34:58 | 03:07:02 | 1 à 372 | 32 min 17 s | pause d'essai (Ctrl+C à 03:06:32, pause notée 22 s plus tard) |
| 2 | 03:07:26 | 03:14:49 | 04:11:30 | 373 à 1 027 | 1 h 04 min 02 s | pause pour le jeu de l'utilisateur (Ctrl+C à 04:11:08) |
| 3 | 05:29:37 | 05:31:10 | 08:48:39 | 1 028 à 3 338 | 3 h 18 min 58 s | fin |

- **Calcul :** 17 075 s, soit 4 h 44 min 35 s (`secondes` du journal, sans les chargements) ; 4 h 45 min
  étaient prévues. Python a tourné 4 h 55 min 17 s en tout, chargements et sauvegardes compris. Du
  premier lancement à la fin : 6 h 13 min 58 s, avec les pauses (24 s et 1 h 18 min 07 s).
- **Les reprises :** la deuxième session a mis 7 min 23 s à reprendre (sauvegarde de 4,85 Gio et version
  de départ relues sur D:), la troisième 1 min 33 s.
- **Débit :** médiane de 13 389, 13 303 et 13 340 jetons par seconde selon la session.
  8 sauvegardes d'étape toutes les 30 minutes environ, plus celles des deux pauses et de la fin (11 en
  tout).
- **La courbe continue sans saut** à chaque pause : perte moyenne 1,265 sur les 20 pas avant le pas 372,
  1,271 sur les 20 pas après ; 1,128 avant le pas 1 027, 1,132 après. Le taux reprend où il
  était (2,937e-4 au pas 372, 2,936e-4 au pas 373).

La perte part de 2,208 au pas 1 et finit à 0,708 au pas 3 338. La perte de validation
(64 rangées, nats par jeton appris) est mesurée tous les 100 pas ; elle baisse à chaque mesure, de
1,424 au pas 100 à **0,941** au pas 3 338, la plus basse : `meilleur.pt` est le pas 3 338.

| Pas | Perte d'entraînement (moyenne) | Validation au dernier pas du bloc |
| --- | ---: | ---: |
| 1 à 200 | 1,481 | 1,331 |
| 201 à 400 | 1,289 | 1,247 |
| 401 à 600 | 1,224 | 1,194 |
| 601 à 800 | 1,183 | 1,153 |
| 801 à 1 000 | 1,148 | 1,118 |
| 1 001 à 1 200 | 1,123 | 1,089 |
| 1 201 à 1 400 | 1,095 | 1,066 |
| 1 401 à 1 600 | 1,065 | 1,036 |
| 1 601 à 1 800 | 0,951 | 1,023 |
| 1 801 à 2 000 | 0,883 | 1,009 |
| 2 001 à 2 200 | 0,875 | 0,993 |
| 2 201 à 2 400 | 0,868 | 0,979 |
| 2 401 à 2 600 | 0,846 | 0,966 |
| 2 601 à 2 800 | 0,848 | 0,956 |
| 2 801 à 3 000 | 0,837 | 0,949 |
| 3 001 à 3 200 | 0,827 | 0,943 |
| 3 201 à 3 338 | 0,832 | 0,941 |

La deuxième époque commence au pas 1 669 (53 401 rangées ÷ 32 par pas). La perte d'entraînement y tombe
vite : de 1,065 (pas 1 401 à 1 600) à 0,883 (pas 1 801 à 2 000). La validation, sur des conversations
jamais vues, ne baisse que de 1,036 à 1,009 : la deuxième époque relit les mêmes conversations, et la
perte d'entraînement y baisse bien plus que la validation. La validation baisse encore jusqu'au bout,
mais de moins en moins : de 0,949 au pas 3 000 à 0,941 à la fin.

## 6. La version courte

`configs/sft-1.7-court.toml`, lancée par `travail-long.ps1` juste après (fenêtre « Ton IA :
ton-ia-1.7-court »), d'une traite : de 08:49:19 à 09:53:57, **1 h 04 min 37 s** de Python, dont 3 776 s
de calcul (1 h 02 min 56 s ; 1 h 03 min prévue). Débit médian 13 381 jetons par seconde. Perte 1,058 au
pas 739, validation **1,095** (la plus basse : `meilleur.pt` est le pas 739).

| Pas | Perte d'entraînement (moyenne) | Validation | Validation du complet au même pas |
| --- | ---: | ---: | ---: |
| 1 à 100 | 1,588 | 1,423 | 1,424 |
| 101 à 200 | 1,370 | 1,323 | 1,331 |
| 201 à 300 | 1,294 | 1,258 | 1,283 |
| 301 à 400 | 1,235 | 1,204 | 1,247 |
| 401 à 500 | 1,192 | 1,156 | 1,219 |
| 501 à 600 | 1,135 | 1,121 | 1,194 |
| 601 à 700 | 1,123 | 1,099 | 1,173 |
| 701 à 739 | 1,100 | 1,095 | — |

À pas égal, la version courte est devant : son taux descend plus vite (cosinus sur 739 pas au lieu de
3 338). À la fin, le complet va plus bas (0,941 contre 1,095).

## 7. L'évaluation : 1.5, 1.7 et la version courte côte à côte

Exportées par `forge exporter` dans `publications\ton-ia-1.7` et `publications\ton-ia-1.7-court` (le
`meilleur.pt` de chacune), puis mesurées le 19 novembre 2026 sur la carte par `forge evaluer-etape
--etape 1.7`, avec `ton-ia-1.5` (téléchargée) en référence. Les réponses sont écrites en glouton. Le
rapport est `evaluations\ton-ia-1.7-1.7\rapport.json` (1.7 et 1.5) et
`evaluations\ton-ia-1.7-court-1.7\rapport.json`.

| Mesure | `ton-ia-1.5` | `ton-ia-1.7` | `ton-ia-1.7-court` |
| --- | ---: | ---: | ---: |
| Perte sur les conversations de validation (nats par jeton appris, 64 ex.) | 2,300 | 0,936 | 1,080 |
| IFEval-FR, invites dont toutes les consignes sont respectées (235) | 21,7 % | 16,2 % | 15,7 % |
| IFEval-FR, consignes respectées | 31,9 % | 26,4 % | 26,4 % |
| Réponses terminées par `<|fin_tour|>` (335) | 0,0 % | 52,8 % | 54,0 % |
| Réponses en français | 87,2 % | 98,8 % | 99,7 % |
| Réponses dans une autre langue | 0,3 % | 0,0 % | 0,0 % |
| Réponses de langue indéterminée | 12,5 % | 1,2 % | 0,3 % |
| Longueur moyenne d'une réponse (mots) | 320,7 | 215,2 | 222,5 |
| Oubli : perte sur le texte du pré-entraînement (nats par jeton, 64 morceaux) | 2,347 | 3,766 | 2,998 |
| Oubli : bits par octet sur ce texte | 0,779 | 1,250 | 0,995 |

Les mesures de l'étape 1.9 (problèmes de calcul), passées aussi par `forge evaluer-etape --etape 1.9`
(rapports `evaluations\ton-ia-1.7-1.9` et `ton-ia-1.7-court-1.9`), donnent le point de départ du
raisonnement :

| Mesure | `ton-ia-1.5` | `ton-ia-1.7` | `ton-ia-1.7-court` |
| --- | ---: | ---: | ---: |
| Problèmes générés, exactitude en glouton (400) | 0,0 % | 0,8 % | 0,0 % |
| Problèmes générés, réponses terminées | 0,0 % | 57,0 % | 47,0 % |
| Problèmes générés, au moins un juste sur 8 essais | 0,0 % | 2,8 % | 1,8 % |
| MGSM-rev2 en français, exactitude (250) | 0,0 % | 0,4 % | 0,0 % |
| MGSM-rev2, réponses terminées | 0,0 % | 36,0 % | 23,6 % |
| GSM8K-Platinum en français, exactitude (1 196) | 0,0 % | 0,3 % | 0,5 % |
| GSM8K-Platinum, réponses terminées | 0,0 % | 33,5 % | 27,5 % |

Ce que disent ces nombres :

- **Ton IA 1.7 finit ses réponses**, ce que 1.5 ne faisait jamais : 52,8 % des réponses se terminent par
  `<|fin_tour|>`, contre 0,0 %. Elle répond en français dans 98,8 % des cas (87,2 % pour 1.5), et
  plus court (215,2 mots en moyenne contre 320,7).
- **Elle suit moins bien les consignes d'IFEval-FR que 1.5** : 16,2 % des invites entièrement
  respectées, contre 21,7 % ; 26,4 % des consignes, contre 31,9 %.
- **Elle prédit moins bien que 1.5 le texte de son pré-entraînement** : la perte sur ce texte monte
  de 2,347 à 3,766 nats par jeton (0,779 à 1,250 bit par octet). La version courte, qui a moins appris
  les conversations (perte de 1,080 contre 0,936), monte moins (2,998 nats par jeton) et suit les
  consignes à peu près pareil (15,7 %).
- **Sur les conversations de validation**, la perte passe de 2,300 (1.5) à 0,936 (1.7) et
  1,080 (version courte).
- **Les problèmes :** voir le tableau ci-dessus ; 1.7 résout 3 problèmes générés sur 400 en glouton
  (0,8 %, 2,8 % avec au moins un juste sur 8 essais), 1 problème de MGSM sur 250 et 4 de GSM8K-Platinum
  sur 1 196 ; la version courte, 0, 0 et 6. 1.5 n'en résolvait aucun : elle ne finissait aucune réponse.
  1.7 en finit 57,0 % (problèmes générés), mais presque toujours avec un nombre faux. Ces scores restent
  au niveau de presque rien.
- **Deux passages ne donnent pas exactement les mêmes nombres.** Le rapport de l'étape 1.9 repasse
  IFEval-FR : 15,7 % pour 1.7 et 20,9 % pour 1.5, contre 16,2 % et 21,7 % ci-dessus. Le lot de
  génération dépend de la mémoire libre de la carte ; cause probable, non vérifiée : les calculs en bf16
  d'un lot à l'autre changent parfois un jeton choisi en glouton. Un écart de moins d'un point sur
  IFEval-FR n'est donc pas une différence.

## 8. Les échantillons
Les dix invites fixes de `forge evaluer-etape`, en glouton, 200 jetons au plus. Les réponses de
`ton-ia-1.7` sont recopiées telles quelles, sans tri ni retouche. Celles de `ton-ia-1.5` et de la version
courte sont dans leurs rapports.

### 1. « Quelle est la capitale de la France ? »

Réponse terminée par `<|fin_tour|>` :

```text
La capitale de la France est Paris.
```

### 2. « Pourquoi le ciel est-il bleu ? »

Réponse terminée par `<|fin_tour|>` :

```text
Le ciel est bleu parce que les nuages et les nuages sont tous deux bleu. Le ciel est bleu parce que les nuages et les nuages sont tous deux bleu.
```

### 3. « Explique en deux phrases comment fonctionne la photosynthèse. »

Réponse terminée par `<|fin_tour|>` :

```text
La photosynthèse est le processus par lequel les plantes, les algues et certaines bactéries utilisent l'énergie lumineuse pour convertir le dioxyde de carbone et l'eau en glucides et en oxygène. Ce processus est réalisé par les plantes, qui possèdent des chloroplastes et des pigments photosynthétiques.
```

### 4. « Combien font 12 fois 7 ? »

Réponse coupée par la limite de 200 jetons :

```text
Pour déterminer le nombre de fois que le nombre de fois que le nombre de fois que le nombre de fois que le nombre de fois que le nombre de fois que le nombre de fois que le nombre de fois que le nombre de fois que le nombre de fois que le nombre de fois que le nombre de fois que le nombre de fois que le nombre de fois que le nombre de fois que le nombre de fois que le nombre de fois que le nombre de fois que le nombre de fois que le nombre de fois que le nombre de fois que le nombre de fois que le nombre de fois que le nombre de fois que le nombre de fois que le nombre de fois que le nombre de fois que le nombre de fois que le nombre de fois que le nombre de fois que le nombre de fois que le nombre de fois que le nombre de fois que le nombre de fois que le nombre de fois que le nombre de fois que le nombre de fois que le nombre de fois que le nombre de fois que le nombre de
```

### 5. « Donne-moi trois conseils pour bien dormir. »

Réponse coupée par la limite de 200 jetons :

```text
1. Le plus grand secret pour le sommeil : Le sommeil est une période de repos et de préparation. Il est essentiel de le préparer avant de dormir. 2. La position du sommeil : Le sommeil est essentiel pour la récupération physique et mentale. Il est essentiel de s'assurer que le corps est en état de se rééveiller et de se réhydrater. 3. La position du sommeil : Le sommeil est essentiel pour la relaxation et la consolidation de la mémoire. Il est essentiel de s'assurer que le corps se réévalue et se réévalue. 4. La position du sommeil : Le sommeil est essentiel pour la régulation émotionnelle et la consolidation des souvenirs. Il est essentiel de s'assurer que le corps se réévalue et se réévalue. 5. La position du sommeil : Le sommeil est essentiel pour la récupération physique et mentale. Il est essentiel de s'assurer que le corps se réévalue et se réévalue. 6. La
```

### 6. « Quelle est la différence entre un virus et une bactérie ? »

Réponse coupée par la limite de 200 jetons :

```text
La différence entre un virus et une bactérie réside dans la **molalité** (ou la proportion de particules virales dans un échantillon) et dans la **masse** (ou la charge virale) de ces particules.

Voici une explication détaillée :

### 1. La différence fondamentale
La **molalité** est définie comme le nombre de particules (ou de particules) par unité de **masse** (ou de volume) de l'échantillon.

- **Les virus** : Ce sont des particules **molaires** (elles ont une structure tridimensionnelle rigide). Ils ne peuvent pas se déplacer facilement à travers un milieu matériel (comme l'eau ou l'air) sans se déposer dans un milieu matériel (comme l'eau).
- **Les bactéries** : Ce sont des particules **molaires** (elles ont une structure rigide et une capacité de mouvement). Elles peuvent se déplacer à travers un milieu matériel (comme l'eau) sans se déposer dans un milieu
```

### 7. « Écris un court texte sur l'automne en moins de 50 mots, tout en minuscules. »

Réponse terminée par `<|fin_tour|>` :

```text
L'automne est un court texte qui contient 4 vers. Il est composé de 4 vers, chacun contenant un vers différent.
```

### 8. « Présente-toi en trois phrases, sans utiliser de virgule. »

Réponse terminée par `<|fin_tour|>` :

```text
Je suis désolé, je ne peux pas vous aider avec mes trois phrases.
```

### 9. « Qui es-tu ? »

Réponse terminée par `<|fin_tour|>` :

```text
Je suis ton IA, une petite intelligence artificielle qui écrit en français.
```

### 10. « Écris une fonction Python qui renvoie la somme des carrés d'une liste de nombres. »

Réponse coupée par la limite de 200 jetons :

```text
Pour calculer la somme des carrés d'une liste de nombres, nous devons suivre les étapes suivantes :

1. **Trouver le plus petit commun multiple (PPCM) de 2 et 3** de la liste.
2. **Trouver la plus grande racine carrée de 2 et 3** de la liste.
3. **Trouver la plus petite racine carrée de 3 et 4** de la liste.

### Étape 1 : Trouver la plus grande racine carrée de 2 et 3

Nous cherchons la plus grande racine carrée de 2 et 3. Nous pouvons factoriser le produit :
$$2^3 = 8$$

En utilisant la factorisation de 2 et 3 :
$$2^3 = 16$$

Donc, la plus grande racine carrée est **16**.

### Étape 2 : Trouver la plus grande racine carrée de 3 et 4

Nous cherchons
```

`ton-ia-1.7` termine 6 de ces dix réponses, la version courte 3, `ton-ia-1.5` 0 : toutes celles de 1.5
sont coupées par la limite, et la plupart répètent une même phrase.

## 9. Ce que ton IA 1.7 sait faire, et ce qu'elle ne sait pas faire

D'après les mesures et les dix échantillons ci-dessus :

**Elle sait :**

- répondre à une question, puis s'arrêter : elle finit plus de la moitié de ses réponses (52,8 %), et 6
  des dix échantillons ;
- répondre en français (98,8 % des réponses) ;
- dire qui elle est (échantillon 9) et donner un fait très connu (échantillon 1 : Paris) ;
- écrire une définition correcte quand elle est courante (échantillon 3, la photosynthèse).

**Elle ne sait pas :**

- calculer : « Combien font 12 fois 7 ? » tourne en boucle sans réponse (échantillon 4) ; 3 problèmes
  générés justes sur 400, 1 sur 250 pour MGSM, 4 sur 1 196 pour GSM8K-Platinum ;
- dire des choses vraies à coup sûr : elle écrit des choses fausses (échantillons 2, 6 et 10 : des nuages
  bleus, une « molalité » des virus, des racines carrées fausses) ;
- respecter une consigne de forme : moins bien que 1.5 sur IFEval-FR (16,2 % contre 21,7 %), et dans les
  échantillons 7 et 8 (« en minuscules », « sans virgule ») ;
- écrire du code : à la demande d'une fonction Python, elle écrit un calcul faux, sans code (échantillon
  10) ;
- éviter les répétitions : 4 des dix échantillons sont coupés par la limite, souvent en répétant (4 et
  5) ;
- prolonger un texte libre aussi bien que 1.5 : sa perte sur le texte du pré-entraînement monte de
  2,347 à 3,766 nats par jeton.

## 10. Les fichiers de la version `ton-ia-1.7`

| Fichier | Octets | SHA-256 |
| --- | ---: | --- |
| `ton-ia-1.7.safetensors` | 867 161 248 | `b53eb7e2880e542e87ace535b13fcce99c1435c5c903dea192d267028aead8b8` |
| `config.json` | 134 | `ae0207b367080a6577c2d95ef81ba5fb84c6bf2be11d03a07eedd8a9fe598621` |
| `tokenizer-ton-ia-v1.json` | 546 692 | `3001e7ab40630739c4dec807c7a92c0d4fb469cc0fc4afa368704395391f21ba` |
| `rapport.json` (de `evaluations\ton-ia-1.7-1.7`) | 17 773 | `98b6475a3fdbdfcca57af1dc0381ef1b2f34a068128b9cbd03892ac671afb749` |

Les poids sont en bf16, exportés par `forge exporter` depuis
`entrainements\sft-1.7\sauvegardes\meilleur.pt` (le pas 3 338). `config.json` et le tokenizer sont ceux
de 1.5, à l'octet près. La version courte est exportée de même dans `publications\ton-ia-1.7-court`
(`ton-ia-1.7-court.safetensors`, SHA-256
`22473f1a872f8a95d73ab54194bc6a634f5fc17f357f19b6ea498ee857661aaf`), sans Release.
