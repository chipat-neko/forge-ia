# La vitesse d'entraînement de ton IA : carte graphique contre processeur

Mesuré le 3 novembre 2026 (2026-11-03).

Ce document répond à une question qui se pose avant tout entraînement long : **combien de temps ton IA
mettra-t-elle à s'entraîner, selon sa taille, sur la carte graphique et sur le processeur ?** Il donne
les mesures chronométrées, les durées qu'on en tire pour 20 jetons par paramètre, et la place que chaque
taille demande sur le disque. Il ne recommande aucune taille ni aucun appareil : c'est à toi de choisir.

## En bref

- **Carte graphique (RTX 5070 Ti)** : de 138 433 jetons par seconde (taille « petit ») à 17 855
  (« tres_grand »). Pour 20 jetons par paramètre, cela fait 1,7 h pour « petit », 9,8 h pour « moyen »,
  40,1 h pour « grand » et 135 h (5,6 jours) pour « tres_grand ».
- **Processeur (Ryzen 7 9800X3D, ses 16 fils)** : de 1 749 à 235 jetons par seconde, soit 76 à 81 fois
  moins vite que la carte. Les mêmes entraînements dureraient de 132 h (5,5 jours) pour « petit » à
  10 235 h (426 jours) pour « tres_grand ».
- **Les 16 cœurs logiques du processeur travaillaient bien** : chacun à 100,0 % pendant toute la mesure,
  et PyTorch n'en aurait utilisé que 8 sans réglage explicite (voir « Le processeur travaille-t-il
  vraiment à fond ? »).
- **Disque** (44,4 Go libres sur D:) : « petit », « moyen » et « grand » tiennent, « tres_grand » ne tient
  pas avec ce calcul (il manque 7,0 Go au moins, 26,3 Go dans le cas le plus prudent), qui compte le
  texte brut sans compression. Sur le disque, ce texte est compressé environ 3 fois : compté ainsi,
  « tres_grand » tient, avec 8,9 Go de marge (voir « Le choix du 3 novembre 2026 »).
- **Une nuit de 10 h sur la carte** fait lire 4,98 milliards de jetons à « petit », 2,25 à « moyen », 1,18 à
  « grand » et 0,64 à « tres_grand ». Rapporté à la taille du modèle, cela fait 120, 20, 5 et 1,5 jetons
  par paramètre.
- **Le plus grand micro-lot qui tient en mémoire n'est pas le plus rapide** : pour « petit », « moyen » et
  « grand », un micro-lot plus petit va de 4 % à 14 % plus vite (voir « Le micro-lot »).

## La machine

| Élément | Valeur |
| --- | --- |
| Carte graphique | NVIDIA GeForce RTX 5070 Ti, 16 Go (15,9 Go vus par PyTorch) |
| État de la carte au départ | 1 % d'utilisation, 1,5 Go déjà pris par Windows, 14,6 Go libres |
| Processeur | AMD Ryzen 7 9800X3D, 8 cœurs, 16 fils (16 cœurs logiques) |
| Charge du processeur au repos | 16 % (programmes ouverts en arrière-plan, sans entraînement) |
| Mémoire vive | 61,7 Go |
| Disque des données | D:, 44,4 Go libres |
| Logiciel | PyTorch 2.15.0 (CUDA 13.2), Python 3.12, Windows 11 |
| Compilation | aucune (`torch.compile` n'a pas `triton` sous Windows) : tout se mesure en mode immédiat |

La carte était libre au début de la mesure (`python -m forge mesurer` refuse de mesurer si elle travaille
déjà à 30 % ou plus, pour ne pas donner de chiffres faussés). Aucun programme lourd n'a été arrêté ni
lancé pour l'occasion.

## Comment on a mesuré

On chronomètre **la vraie étape d'entraînement de la boucle** (`_pas_d_optimisation` de
`forge/entrainement/boucle.py`) : calcul de la perte, `backward`, écrêtage des gradients, pas d'AdamW. Le
calcul se fait en `bfloat16` sur la carte et en 32 bits sur le processeur, exactement comme à
l'entraînement. Seules les données diffèrent : des jetons tirés au hasard, de la même forme que ceux du
chargeur (`micro_lot` lignes de `longueur_contexte` jetons). La vitesse d'un pas ne dépend que du nombre
de jetons, pas de leur valeur. Le code est dans `projets/forge/forge/mesure.py`.

- **Sur la carte** : 2 pas d'échauffement non comptés, puis 20 pas chronométrés, chacun de 8 micro-lots
  accumulés. L'accumulation compte : l'écrêtage et le pas d'AdamW coûtent le même temps quelle que soit la
  taille du lot, et ils font perdre environ 13 % de vitesse à « tres_grand » s'ils ne servent qu'un seul micro-lot
  (15 589 jetons par seconde avec 1 micro-lot par pas, 17 855 avec 8), alors qu'un vrai entraînement en accumule des
  dizaines.
- **Le plus grand micro-lot qui tient** est cherché par essais de 3 pas (à 2 micro-lots accumulés, car les
  gradients du premier occupent déjà la mémoire pendant le calcul du second) : 1, 2, 4, 8… tant que ça
  tient, puis dichotomie. On laisse 1 Go libre à Windows : la mémoire du processus est plafonnée à la mémoire
  libre moins 1 Go, ce qui donne une vraie erreur de mémoire au lieu d'un débordement lent vers la mémoire de
  l'ordinateur. Puis tous les micro-lots en puissances de 2 jusqu'à celui-là sont chronométrés.
- **Sur le processeur** : `torch.set_num_threads(os.cpu_count())`, soit 16 fils. Micro-lot de 2 lignes (4 096
  jetons). 1 pas d'échauffement, puis 20 pas ou 120 s au plus, car un pas de « tres_grand » dure 17 s
  (« petit » et « moyen » ont fait leurs 20 pas, « grand » 12, « tres_grand » 7).
- **La charge** est relevée avec `psutil` : temps de chaque cœur logique avant et après la mesure (donc la
  moyenne exacte), et temps de calcul du processus (donc le nombre de cœurs qu'il occupe en moyenne).
- **Les durées** sont `jetons ÷ jetons par seconde ÷ 3600`, avec 20 fois le nombre de paramètres comme
  nombre de jetons.
- **La place sur le disque** : jetons encodés à 2 octets par jeton, texte brut à 4,36 octets par jeton
  (`docs/mesures/tokenizer-ton-ia-v1.md`), sauvegardes à 3 fichiers de 16 octets par paramètre.

## Résultats

### La carte graphique

| Taille | Paramètres | Plus grand micro-lot qui tient | jetons/s à ce micro-lot | pic de mémoire à ce micro-lot | Micro-lot le plus rapide | jetons/s à ce micro-lot | pic de mémoire à ce micro-lot |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| petit | 41,7 M | 8 | 125 054 | 10,4 Go | 4 | 138 433 | 5,5 Go |
| moyen | 110,1 M | 6 | 54 507 | 12,5 Go | 2 | 62 368 | 5,4 Go |
| grand | 236,0 M | 3 | 31 498 | 11,7 Go | 2 | 32 704 | 9,1 Go |
| tres_grand | 433,6 M | 1 | 17 855 | 10,9 Go | 1 | 17 855 | 10,9 Go |

Le micro-lot est le nombre de lignes de 2 048 jetons (512 pour « mini ») que la carte traite d'un coup. La
colonne « pic de mémoire » est le maximum de mémoire occupée par les tenseurs (`max_memory_allocated`).

### Le processeur

| Taille | Fils utilisés | Micro-lot | Pas mesurés | Jetons/s | Charge moyenne par cœur | Cœurs occupés par le processus (sur 16) | Carte ÷ processeur |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| petit | 16 | 2 | 20 | 1 749 | 100 % | 13,1 | 79 × |
| moyen | 16 | 2 | 20 | 776 | 100 % | 13,1 | 80 × |
| grand | 16 | 2 | 12 | 404 | 100 % | 12,9 | 81 × |
| tres_grand | 16 | 2 | 7 | 235 | 100 % | 13,0 | 76 × |

### Les durées

| Taille | Jetons visés (20 par paramètre) | Durée sur la carte (micro-lot le plus rapide) | Durée sur la carte (plus grand micro-lot) | Durée sur le processeur | Jetons vus en 10 h sur la carte | Soit, par paramètre |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| petit | 0,83 milliards | 1,7 h | 1,9 h | 132 h (5,5 j) | 4,98 milliards | 119,5 jetons |
| moyen | 2,20 milliards | 9,8 h | 11,2 h | 789 h (33 j) | 2,25 milliards | 20,4 jetons |
| grand | 4,72 milliards | 40,1 h | 41,6 h | 3 243 h (135 j) | 1,18 milliards | 5,0 jetons |
| tres_grand | 8,67 milliards | 135 h (5,6 j) | 135 h (5,6 j) | 10 235 h (426 j) | 0,64 milliards | 1,5 jetons |

Les durées de la carte partent du micro-lot le plus rapide. Celles du processeur sont extrapolées de 7 à 20
pas mesurés (cf. la section sur la fiabilité).

### La place sur le disque

| Taille | Jetons sur le disque | Texte brut à télécharger | Sauvegardes | Pic de place disque | Tient sur le disque (44,4 Go libres) ? | Pic si le texte brut est effacé avant l'entraînement | Tient ? |
| --- | ---: | ---: | ---: | ---: | --- | ---: | --- |
| petit | 1,6 Go | 3,4 Go | 1,9 Go | 6,8 Go | oui (marge 37,6 Go) | 4,9 Go | oui (marge 39,5 Go) |
| moyen | 4,1 Go | 8,9 Go | 4,9 Go | 18,0 Go | oui (marge 26,4 Go) | 13,0 Go | oui (marge 31,4 Go) |
| grand | 8,8 Go | 19,2 Go | 10,5 Go | 38,5 Go | oui (marge 5,9 Go) | 28,0 Go | oui (marge 16,4 Go) |
| tres_grand | 16,2 Go | 35,2 Go | 19,4 Go | 70,7 Go | **non** (manque 26,3 Go) | 51,4 Go | **non** (manque 7,0 Go) |

- **Pic de place disque** : texte brut + jetons + sauvegardes présents en même temps (le cas le plus prudent).
- **Pic si le texte brut est effacé avant l'entraînement** : le plus grand des deux moments, « texte brut et
  jetons » à la fin de l'encodage et « jetons et sauvegardes » pendant l'entraînement. C'est l'ordre prévu
  (télécharger, encoder, effacer le texte, entraîner), mais il suppose que tout le texte est téléchargé
  avant d'être effacé.
- Les sauvegardes comptent 3 fichiers de 16 octets par paramètre, soit 48 octets par paramètre. C'est une
  borne haute prudente. Mesure réelle sur une sauvegarde de « mini » : `etape-*.pt` pèse 12,0 octets par
  paramètre (poids 4, moyennes d'AdamW 8) et `meilleur.pt` 4,0. La boucle garde deux `etape-*.pt` et
  `meilleur.pt`, soit 28 octets par paramètre au repos et 40 pendant l'écriture d'une troisième.
- Le texte brut compte 4,36 octets par jeton non compressés. Sur le disque, le texte téléchargé est compressé
  (environ 3 fois, 343 Mo pour 1 Go de texte), donc la colonne « Texte brut » est aussi une borne haute.

## Le micro-lot

Le plus grand micro-lot qui tient en mémoire n'est pas le plus rapide. Voici toutes les mesures de la
carte (20 pas de 8 micro-lots) :

| Taille | Micro-lot | Jetons/s | Pic de mémoire |
| --- | ---: | ---: | ---: |
| petit | 1 | 91 936 | 1,9 Go |
| petit | 2 | 125 525 | 3,1 Go |
| petit | **4** | **138 433** | 5,5 Go |
| petit | 8 (le plus grand qui tient) | 125 054 | 10,4 Go |
| moyen | 1 | 50 859 | 3,6 Go |
| moyen | **2** | **62 368** | 5,4 Go |
| moyen | 4 | 59 147 | 9,0 Go |
| moyen | 6 (le plus grand qui tient) | 54 507 | 12,5 Go |
| grand | 1 | 29 668 | 6,5 Go |
| grand | **2** | **32 704** | 9,1 Go |
| grand | 3 (le plus grand qui tient) | 31 498 | 11,7 Go |
| tres_grand | **1** (le seul qui tient) | **17 855** | 10,9 Go |

En dessous de 2 ou 4 lignes (selon la taille), la carte est sous-employée ; au-delà, traiter plus de
lignes à la fois la ralentit. Le micro-lot le plus rapide dépasse le plus grand micro-lot qui tient de
4 % (« grand ») à 14 % (« moyen »). La cause n'a pas été étudiée. Une piste, non vérifiée : la dernière
couche calcule, pour chaque position, un score pour chacun des 32 768 jetons du vocabulaire, et cette table
grossit avec le micro-lot. Autre intérêt d'un micro-lot plus petit, la marge de mémoire : avec « moyen », le
micro-lot 2 pèse 5,4 Go au lieu de 12,5 Go.
Un micro-lot qui est une puissance de 2 divise aussi exactement un lot de jetons par pas
(`taille_lot_jetons` doit être un multiple de `micro_lot × longueur_contexte`).

## Le processeur travaille-t-il vraiment à fond ?

Oui. Pour chaque taille, pendant toute la mesure :

- **les 16 cœurs logiques étaient chacun à 100,0 %** (moyenne de chaque cœur sur la durée de la mesure, relevée
  avec `psutil`) : les seize valeurs de `charge_par_coeur` valent toutes 100,0, pour les quatre tailles ;
- PyTorch utilisait 16 fils (`fils_utilises = 16`). **Sans réglage, il en prend 8** (le nombre de vrais
  cœurs) : c'est la valeur de `torch.get_num_threads()` sur ce PC quand on ne règle rien, relevée
  pendant les mesures sur la carte. La forge impose `os.cpu_count()`, soit 16 ;
- le processus occupait en moyenne **12,9 à 13,1 cœurs** de calcul sur 16. Les 3 cœurs restants sont
  très probablement pris par les programmes ouverts en arrière-plan (16 % de charge au repos, soit environ
  2,5 cœurs) : le calcul de ce PC est alors complet, et les chiffres du processeur seraient un peu meilleurs
  sur un PC sans rien d'autre qui tourne. Cette explication n'a pas été isolée.

Comparaison sur « petit » (micro-lot 2, 8 pas, deux passages chacun) :

| Fils | Jetons/s | Charge moyenne par cœur | Cœurs occupés par le processus |
| --- | ---: | ---: | ---: |
| 8 (le réglage par défaut de PyTorch) | 1 452 | 67 à 68 % | 7,9 |
| 16 (tous) | 1 767 à 1 768 | 100 % | 12,9 |

Les 16 fils vont 22 % plus vite que les 8 fils par défaut : les deux fils de chaque cœur se partagent bien
le travail.

## Fiabilité des chiffres

- **Répétabilité** : la mesure complète a été faite quatre fois (pendant la mise au point, avec les mêmes
  réglages sur le processeur). Sur le processeur, les débits de « petit » ont été de 1 745, 1 742, 1 743 et
  1 749 jetons par seconde, ceux de « grand » de 406, 410, 409 et 404, ceux de « tres_grand » de 236, 237,
  236 et 235 : de 0,4 % à 1,5 % d'écart. Sur la carte, avec le même micro-lot et 8 micro-lots par pas,
  « moyen » a donné 54 516, 54 433, 54 507, 54 504 et 54 509 jetons par seconde (moins de 0,2 % d'écart).
  Un balayage du micro-lot refait deux fois a donné des écarts sous 0,5 %.
- **Régime soutenu** : 100 pas de « moyen » (3 minutes) sur la carte donnent 54 490 jetons par seconde,
  comme les 20 pas (54 504). La carte est restée entre 52 et 60 °C, à 2 925 à 2 932 MHz (maximum 3 090) et
  entre 218 et 235 W : pas d'étranglement thermique.
- **Ce que les durées ne comptent pas** : la perte de validation (tous les `evaluation_tous_pas` pas), les
  sauvegardes, la lecture des jetons sur le disque (ici, des jetons tirés au hasard en mémoire) et les
  interruptions. Compter quelques pour cent de plus.
- **Le processeur** : 7 à 20 pas mesurés par taille, mais d'une mesure à l'autre les débits varient de moins
  de 2 % (voir plus haut). Le micro-lot de 2 lignes est un choix : sur « petit », 1, 2 et 4 lignes donnaient
  1 576, 1 716 et 1 801 jetons par seconde dans un essai préliminaire (4 pas chacun), soit 14 % d'écart au
  plus.
- **Mode immédiat** : sans `torch.compile`, comme à l'entraînement de ce PC. Une compilation réussie
  accélérerait peut-être les deux appareils, mais elle n'est pas disponible ici.

## Lecture pour un débutant

**Un jeton**, c'est un morceau de texte, souvent un mot court ou un bout de mot (4,4 octets en moyenne
pour le français et le code de ton IA). **Un paramètre**, c'est un des nombres que le modèle règle en
apprenant : « moyen » en a 110,1 millions. Plus il en a, plus il peut retenir et nuancer, mais plus il coûte
cher à entraîner.

**« 20 jetons par paramètre »** est une règle d'usage pour un modèle bien entraîné pour son prix : on lui
fait lire environ 20 fois autant de jetons qu'il a de paramètres. Pour « moyen », 110,1 millions de
paramètres donnent 2,2 milliards de jetons à lire. En lire beaucoup moins laisse le modèle à moitié appris ;
en lire beaucoup plus l'améliore encore, mais de moins en moins pour le temps passé. C'est un repère, pas
une garantie. Le tableau des durées s'en sert partout.

**Pourquoi la carte graphique va environ 80 fois plus vite que le processeur.** Entraîner un modèle, c'est
presque uniquement multiplier d'immenses tableaux de nombres. Une carte graphique a des milliers de petits
calculateurs qui font la même opération en même temps, une mémoire très rapide et des calculs en 16 bits.
Un processeur a 16 fils, chacun très polyvalent mais beaucoup moins nombreux. Ce n'est pas un réglage
oublié : on a vérifié que le processeur travaille à 100 % sur ses 16 cœurs logiques. C'est son plafond.

**Une nuit de 10 h** sur la carte fait lire 4,98 milliards de jetons à « petit », 2,25 à « moyen », 1,18 à
« grand » et 0,64 à « tres_grand ». Rapporté à la taille du modèle, cela fait 120, 20, 5 et 1,5 jetons par
paramètre.

**L'entraînement peut se mettre en pause et se reprendre** (Ctrl+C, puis `--reprendre`) : le pas en cours
se termine, tout est sauvegardé, et la reprise repart exactement de là (après un plantage, elle repart de la
dernière sauvegarde). Une durée de 40 h peut donc se faire en plusieurs sessions.

**Fait pour le choix** (sans recommandation) :

- les durées sont du calcul pur, à augmenter de quelques pour cent (validation, sauvegardes) ;
- « tres_grand » ne tient pas sur le disque avec le calcul prudent (texte brut non compressé), et ne
  verrait que 1,5 jeton par paramètre en une nuit ;
- « grand » tient sur le disque, avec 16,4 Go de marge si le texte brut est effacé avant
  l'entraînement et 5,9 Go dans le cas le plus prudent ;
- sur le processeur, même « petit » demande 5,5 jours.

## Le choix du 3 novembre 2026

Après avoir lu ces chiffres, l'utilisateur a choisi **la carte graphique** et la taille **« tres_grand »**
(433,6 millions de paramètres). Sa configuration est `projets/forge/configs/principal.toml` :

- 16 540 pas de 524 288 jetons (256 lignes de 2 048), soit 8,67 milliards de jetons, 20 par paramètre ;
- un micro-lot de 1 ligne, le seul qui tient, donc 256 micro-lots accumulés par pas ;
- environ 135 h de carte, en plusieurs sessions grâce à la pause et à la reprise.

**La place sur le disque, recomptée.** Le tableau plus haut compte le texte brut sans compression
(35,2 Go). Or le téléchargement range le texte compressé en gzip : 343 Mo pour 1 Go de texte, mesuré sur
les échantillons du tokenizer. Le texte de « tres_grand » occupera donc environ 12,1 Go. Dans l'ordre
prévu (télécharger, encoder, effacer le texte, entraîner), les deux moments les plus chargés sont :

| Moment | Ce qui est sur le disque | Place |
| --- | --- | ---: |
| fin de l'encodage | texte compressé (12,1 Go) et jetons (16,2 Go) | 28,2 Go |
| entraînement | jetons (16,2 Go) et sauvegardes (19,4 Go au plus) | 35,5 Go |

Le pic est donc de 35,5 Go, pour 44,4 Go libres : il reste 8,9 Go de marge, sans rien libérer de plus.
Cette marge suppose qu'aucun autre programme ne remplit D: pendant l'entraînement. S'il manque de la
place, l'entraînement s'arrête proprement et dit combien il en manque.

## Refaire la mesure

Depuis la racine du dépôt, avec les données sous `D:\forge-ia-donnees` :

```powershell
. .\outils\env-forge.ps1
Set-Location projets\forge
uv run --locked --offline --extra gpu python -m forge mesurer --json mesures.json --tableau tableaux.md
```

La commande dure environ 12 minutes (4 à 5 sur la carte, 7 à 8 sur le processeur),
écrit les tableaux ci-dessus à l'écran, et garde tous les chiffres bruts (dont la charge de chaque cœur)
dans le fichier JSON. Options : `--presets petit,moyen` pour ne mesurer que certaines tailles, `--pas`,
`--cpu-secondes`, `--cpu-micro-lot` et `--gpu-accumulation`. Si la carte travaille déjà pour un autre
programme, la commande s'arrête avec un message au lieu de mesurer.
