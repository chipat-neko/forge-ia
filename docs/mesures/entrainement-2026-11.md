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
- **Le corpus principal est prêt** (3 novembre 2026) : 36 830 Mo de texte (web, Wikipédia, code Python) devenus 8,84 milliards de jetons d'entraînement et 44,5 millions de jetons de validation. L'entraînement en lit 98,1 % : une seule époque. Il pèse 12,8 Go de texte compressé (gardé) et 16,6 Go de jetons sur D:, où il reste 349,7 Go libres (voir « Le corpus principal : les volumes réels »).
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

Après avoir lu ces chiffres, tu as choisi **la carte graphique** et la taille **« tres_grand »**
(433,6 millions de paramètres). La configuration est `projets/forge/configs/principal.toml` :

- 16 540 pas de 524 288 jetons (256 lignes de 2 048), soit 8,67 milliards de jetons, 20 par paramètre ;
- un micro-lot de 1 ligne, le seul qui tient, donc 256 micro-lots accumulés par pas ;
- environ 135 h de carte, en plusieurs sessions grâce à la pause et à la reprise.

**La place sur le disque, recomptée.** Le tableau plus haut compte le texte brut sans compression
(35,2 Go). Or le téléchargement range le texte compressé en gzip : 343 Mo pour 1 Go de texte, mesuré sur
les échantillons du tokenizer. Ces échantillons ne mélangent pas les sources comme l'entraînement (plus
de Wikipédia et de code), donc le vrai chiffre peut être un peu différent. Le texte de « tres_grand »
occupera environ 12,1 Go. Dans l'ordre prévu (télécharger, encoder, effacer le texte, entraîner), les
deux moments les plus chargés sont :

| Moment | Ce qui est sur le disque | Place |
| --- | --- | ---: |
| fin de l'encodage | texte compressé (12,1 Go) et jetons (16,2 Go) | 28,2 Go |
| entraînement | jetons (16,2 Go) et sauvegardes (19,4 Go au plus) | 35,5 Go |

Les totaux sont calculés avant arrondi. Le pic est donc de 35,5 Go, pendant l'entraînement, quand le
texte est déjà effacé : il ne dépend pas de la compression. Pour 44,4 Go libres, il reste 8,9 Go de
marge, sans rien libérer de plus.
Cette marge suppose qu'aucun autre programme ne remplit D: pendant l'entraînement. S'il manque de la
place, l'entraînement s'arrête proprement et dit combien il en manque.

## Le corpus principal : les volumes réels

Le corpus de `principal.toml` a été téléchargé, puis encodé, le 3 novembre 2026 (`python -m forge donnees --octets 36830M --dossier principal`, puis `python -m forge encoder --donnees principal`). Cette section dit ce qu'il pèse vraiment, et le compare à l'estimation de la section précédente.

**Ce qui a été demandé.** 36 830 Mo de texte (38 619 054 080 octets), calculés pour que l'entraînement trouve ses 8 671 723 520 jetons : jetons visés ÷ (1 − 0,5017 % de validation) × 4,3655 octets par jeton (mesuré sur la version courte) × 1,015 de marge, arrondis au Mo au-dessus. Le mélange est celui par défaut : 75 % de web français (27 622,5 Mo), 10 % de Wikipédia (3 683,0 Mo) et 15 % de code Python sous licence permissive (5 524,5 Mo). Aucune source ne s'est épuisée : les trois ont donné tout ce qu'on leur demandait.

### Le texte téléchargé

Dans `textes/principal`, un fichier compressé (gzip) par fragment de 100 Mo de texte environ :

| Source | Texte écrit | Documents gardés (lus) | Fragments | Sur le disque (gzip) | Compression |
| --- | ---: | ---: | ---: | ---: | ---: |
| web_fr | 27 622,5 Mo | 8 802 931 (8 802 961) | 277 | 10,20 Go | 387,2 Mo par Go de texte |
| wikipedia_fr | 3 683,0 Mo | 813 795 (836 091) | 37 | 1,29 Go | 365,9 Mo par Go de texte |
| code_python | 5 524,5 Mo | 738 171 (19 096 922) | 56 | 1,21 Go | 229,9 Mo par Go de texte |
| **Total** | **36 830,0 Mo** | **10 354 897** | **370** | **12,70 Go** | **361,5 Mo par Go de texte** |

- Le dossier `textes/principal` pèse **12,77 Go** en tout : les 12,70 Go de fragments, plus les fichiers d'empreintes qui servent à écarter les doublons (79,0 Mo).
- Les documents gardés sont ceux que le nettoyage et le dédoublonnage laissent passer. Pour le code, le tri est sévère : il a fallu lire 19,1 millions de fichiers (toutes langues, toutes licences) pour en garder 738 171 (Python, licence permissive), soit un sur vingt-six.
- Le texte se compresse à 35,3 % de sa taille, comme sur la version courte (353 Mo pour 1 000 Mo). Le code se compresse le mieux (230 Mo par Go de texte), le web le moins bien (387).

### Les jetons

Dans `jetons/principal`, un fichier de jetons d'entraînement et un de validation par fragment de texte (370 de chaque), à 2 octets par jeton :

| Source | Jetons d'entraînement | Part | Jetons de validation | Octets de texte par jeton |
| --- | ---: | ---: | ---: | ---: |
| web_fr | 6 351 849 281 | 71,8 % | 31 653 109 | 4,54 |
| wikipedia_fr | 934 672 689 | 10,6 % | 4 561 107 | 4,11 |
| code_python | 1 554 695 397 | 17,6 % | 8 276 775 | 3,71 |
| **Total** | **8 841 217 367** | **100 %** | **44 490 991** | **4,35** |

- Le dossier `jetons/principal` pèse **16,55 Go** : 16,47 Go d'entraînement et 0,08 Go de validation, plus l'index et les marqueurs de chaque fragment.
- Le mélange en jetons n'est pas celui en octets. Le code a plus de jetons par octet de texte (3,7 octets par jeton contre 4,5 pour le web, séparateurs de fin de document compris) : il pèse donc 17,6 % des jetons pour 15 % du texte, et le web 71,8 % pour 75 %.
- Le marqueur `.complet` donne 4,3513 octets par jeton pour l'ensemble, contre 4,3655 sur la version courte : 0,3 % de jetons en plus pour le même texte.

### Il tient en une seule époque

L'entraînement lit `jetons_total` = 8 671 723 520 jetons (16 540 pas de 524 288). Le corpus en contient **8 841 217 367** d'entraînement d'après `.complet` : **169 493 847 de plus (+1,95 %)**. L'entraînement en lit donc 98,1 % : il n'a pas besoin d'une deuxième époque, et aucun morceau n'est lu deux fois.

Le compte exact se fait en morceaux, car le chargeur coupe chaque fichier en morceaux de 2 049 jetons (une ligne de 2 048 jetons et le jeton qui la suit) et laisse de côté la fin trop courte. Le corpus contient 4 314 705 morceaux utilisables (8 836 515 840 jetons) ; l'entraînement en lit 16 540 × 256 = 4 234 240. Il en reste **80 465 jamais lus** (164 792 320 jetons, 1,9 %). La marge de 1,5 % demandée au téléchargement, et les 0,3 % de jetons gagnés par la compression, laissent donc un peu plus de jetons qu'il n'en faut, sans qu'il en manque.

### Le téléchargement, et sa reprise

| Étape | Heure | Durée | Débit |
| --- | --- | ---: | ---: |
| `web_fr` (27 622,5 Mo) | 16 h 08 à 16 h 47 | 38 min 16 s | 12,0 Mo/s |
| `wikipedia_fr` (3 683,0 Mo) | 16 h 47 à 16 h 52 | 4 min 48 s | 12,8 Mo/s |
| `code_python`, première partie (4 501,2 Mo, fragments 0 à 44) | 16 h 52 à 17 h 34 | 42 min 34 s | 1,8 Mo/s |
| arrêt volontaire | 17 h 34 à 17 h 50 | 15 min 33 s | |
| `code_python`, reprise (1 023,3 Mo, fragments 45 à 55) | 17 h 50 à 18 h 17 | 27 min 32 s | 0,6 Mo/s |
| **Téléchargement actif en tout** | | **1 h 53 min 10 s** | 5,4 Mo/s |

- **Le code a pris 70 minutes sur 113**, pour 15 % du texte : le flux contient tous les langages et toutes les licences, et il faut le lire en entier pour trouver les fichiers Python sous licence permissive. Le web et Wikipédia vont à 12 Mo/s.
- **L'estimation était de 80 minutes** (0,13 s par Mo, mesurés sur la version courte, où le code ne pesait que 150 Mo). Le réel a pris 41 % de plus : le code est plus lent que le web, et la reprise a coûté environ 18 minutes de relecture (voir plus bas).
- **Interruption et reprise.** Le téléchargement a été interrompu à la main à 17 h 34, pendant `code_python`, parce que tu voulais te servir du PC. La même commande, relancée à 17 h 50, a repris après 15 579 564 documents lus et a fini à 18 h 17 : `web_fr` et `wikipedia_fr` ont répondu « déjà complet », seuls les fragments manquants de `code_python` ont été écrits. Le corpus final le confirme : 56 fragments numérotés de 0 à 55 sans trou, 738 171 documents sans aucun doublon, et le nombre de documents et d'octets de `etat.json` est exactement celui des fragments (vérifié en les relisant tous). La reprise marche donc sur le vrai corpus, pas seulement sur les tests.
- **Ce que la reprise coûte.** Le flux est relu depuis le début du jeu pour sauter les documents déjà comptés : 18 minutes de lecture avant que le fragment 45 soit écrit (à 18 h 09). Une interruption tardive sur une grosse source coûte donc du temps, pas des données.

### L'encodage

| Mesure | Valeur |
| --- | --- |
| Heure | 18 h 49 à 19 h 03 |
| Durée | 839 s (13 min 59 s en comptant le lancement) |
| Texte encodé | 36 830,0 Mo (38 619 056 781 octets) |
| Débit | 43,9 Mo de texte par seconde, soit 10,6 millions de jetons par seconde |
| Fragments | 370, de 8 s à 48 s chacun |
| Processus | 16 (un par cœur logique) |
| Jetons écrits | 8 885 708 358 |
| Documents | 10 354 897 (10 302 981 d'entraînement, 51 916 de validation) |

- **Les 16 cœurs ont travaillé du début à la fin.** La sonde (`psutil`, un relevé toutes les 30 s) a fait 27 relevés pendant l'encodage : à chacun, les 16 cœurs logiques dépassaient 50 %, et même 86 % pour le moins occupé au premier relevé (les processus démarraient), puis 95 % au moins ensuite. La charge moyenne des cœurs est de 99,1 % après le premier relevé (88,9 % au premier). Un seul cœur occupé, on aurait vu 6 % de charge moyenne.
- Les processus de l'encodage occupaient en moyenne 12,4 cœurs équivalents sur 16 (de 10,5 à 12,8 ; le premier relevé, pris avant que les processus existent, n'est pas compté) : comme pendant la mesure du processeur (12,9 à 13,1), le reste du temps de calcul revient aux programmes ouverts en arrière-plan. Cette explication n'a pas été isolée.
- L'encodage tournait à priorité basse, pour ne pas gêner le reste du PC ; le débit est celui obtenu dans ces conditions.
- **Le débit par processus est le même que sur la version courte** : 2,7 Mo/s par processus (30,0 Mo/s avec 11 processus, 43,9 avec 16). L'estimation était d'une vingtaine de minutes ; le réel a pris 14 minutes.

### Estimation et réel

| Grandeur | Estimation du 3 novembre | Réel |
| --- | ---: | ---: |
| Texte à télécharger | 36 830 Mo | 36 830,0 Mo |
| Texte compressé sur le disque (fragments gzip) | 12,1 Go (343 Mo par Go de texte) | 12,7 Go (361,5 Mo par Go de texte) |
| Jetons sur le disque | 16,2 Go | 16,6 Go |
| Fin de l'encodage (texte compressé et jetons) | 28,2 Go | 29,3 Go |
| Entraînement (jetons et 3 sauvegardes de 6,5 Go au plus) | 35,5 Go | 35,9 Go |
| Octets de texte par jeton | 4,36 | 4,35 |
| Jetons d'entraînement | 8,67 milliards visés | 8,84 milliards (+1,95 %) |
| Durée du téléchargement | 80 minutes | 1 h 53 |
| Durée de l'encodage | une vingtaine de minutes | 14 minutes |
| Place libre sur D: | 44,4 Go | 349,7 Go à la fin de l'encodage |

- **Les volumes sont à 5 % près de l'estimation** : le texte compressé est un peu plus gros (+5 %), parce que l'estimation partait de 343 Mo par Go mesurés sur les échantillons du tokenizer, et que le vrai mélange compresse à 361 Mo par Go. Les jetons le sont un peu aussi (+2 %), à cause de la marge de 1,5 % du téléchargement.
- **La place n'est plus un problème.** Elle est passée de 44,4 Go à 366,6 Go avant la reprise du téléchargement (tu as libéré de la place), et il en reste 349,7 Go à la fin de l'encodage. Au pic des sauvegardes (19,4 Go de plus), il en restera encore 330,3 Go.
- **Le texte brut n'a pas été effacé**, contrairement à l'ordre prévu (télécharger, encoder, effacer le texte, entraîner). L'effacement ne servait qu'à gagner de la place, et il y en a largement ; il est irréversible, et retélécharger prendrait près de 2 heures. Les 12,77 Go de `textes/principal` restent donc sur D:. Tu peux les effacer quand tu veux : l'entraînement n'a besoin que des jetons.

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
