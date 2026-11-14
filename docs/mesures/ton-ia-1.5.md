# Ton IA 1.5 : l'entraînement principal, son évaluation et ses fichiers

Entraînée du 3 au 14 novembre 2026, évaluée et exportée le 14 novembre 2026 (2026-11-14).

Ce document raconte l'entraînement principal de ton IA : **le modèle « tres_grand », 433 millions de
paramètres, entraîné 139 heures sur la carte graphique, en 13 sessions étalées sur 11 jours**. Il
donne la courbe, la durée réelle, les mesures de l'évaluation finale, les dix échantillons tels
quels, et il dit sans fard **ce que ton IA sait faire et ce qu'elle ne sait pas faire**. Il décrit
enfin les fichiers préparés pour la version GitHub `ton-ia-1.5`. Il fait suite à
`docs/mesures/ton-ia-mini.md` (la répétition d'une heure) et à `docs/mesures/entrainement-2026-11.md`
(le choix de la taille et le corpus).

Unités : dans tout ce document, « Mo » et « Go » valent 1 048 576 et 1 073 741 824 octets (comme
l'Explorateur de Windows et les autres documents de ce dossier). Les pertes sont en nats par jeton.

## En bref

- **Le modèle :** « tres_grand », 433 573 120 paramètres (433,6 millions), dimension 1 280, 20 couches,
  20 têtes, contexte de 2 048 jetons, vocabulaire de 32 768 jetons (le tokenizer figé `ton-ia-v1`).
- **Les données :** le corpus « principal », 36 830 Mo de texte (75 % de français du web, 10 % de
  Wikipédia, 15 % de code Python) devenus 8 841 217 367 jetons d'entraînement. L'entraînement en lit
  8 671 723 520, soit 20 par paramètre : **chaque texte est lu une seule fois**.
- **L'entraînement :** 16 540 pas de 524 288 jetons, **139 h 06 min de calcul** sur la RTX 5070 Ti
  (135 h estimées, +3,0 %), à 17 316 jetons par seconde en moyenne. **13 sessions et 12 pauses** :
  **11 j 3 h 43 min** du premier lancement (3 novembre, 19:39:40) à la fin (14 novembre, 23:22:45).
- **La courbe :** la perte d'entraînement part de 10,668 au pas 1, le niveau du hasard
  (ln 32 768 = 10,397). La perte de validation, mesurée tous les 200 pas, est à 5,404 au pas 200 et
  finit à **2,467** au pas 16 540. Elle a baissé à chaque mesure, sans exception.
- **L'évaluation** (sur `meilleur.pt`, le pas 16 540) : perte 2,419, **perplexité 11,2**,
  **0,802 bit par octet**. Aux QCM français : HellaSwag **34,8 %** contre 25,0 % au hasard
  (**au-dessus du hasard**, de 9,8 points), ARC-Challenge 25,1 % contre 25,0 % (**pas différent du
  hasard**).
- **Ce que cela donne :** un français bien plus sûr que celui de « mini », des phrases correctes
  et un sujet tenu sur deux ou trois phrases, quelques faits justes (« La capitale de la France est
  Paris »). Mais **ce qu'elle dit n'est pas fiable**, elle se contredit vite, et son code ne fait
  pas ce que son nom annonce (voir « Les échantillons » et « Ce que ton IA sait faire »).
- **Les fichiers à publier** sont prêts dans `D:\forge-ia-donnees\publication\ton-ia-1.5\` : les poids en
  bf16 (`ton-ia-1.5.safetensors`, 827,0 Mo), `config.json`, le tokenizer, ce rapport, le rapport
  d'évaluation et une fiche `LISEZMOI.md`. Chacun fait moins de 2 Go.

## Les commandes, dans l'ordre

Elles sont lancées depuis `projets/forge`, après `. .\outils\env-forge.ps1` à la racine du dépôt,
avec le Python de `.venv` (même résultat que `uv run --extra gpu python`).

```powershell
# 3 novembre : la vitesse de chaque taille, le corpus (voir docs/mesures/entrainement-2026-11.md)
python -m forge mesurer
python -m forge donnees --octets 36830M --dossier principal
python -m forge encoder --donnees principal --tokenizer forge/ressources/tokenizer-ton-ia-v1.json

# du 3 au 14 novembre : l'entraînement, puis 12 reprises après les 12 pauses (Ctrl+C)
python -m forge entrainer --config configs/principal.toml
python -m forge entrainer --config configs/principal.toml --reprendre
python -m forge suivi --config configs/principal.toml

# 14 novembre : l'essai chronométré (carte, puis processeur arrêté au bout de 10 minutes)
python -m forge evaluer --sauvegarde D:\forge-ia-donnees\entrainements\ton-ia\sauvegardes\meilleur.pt --donnees principal --qcm 20 --appareil cuda --sortie D:\forge-ia-donnees\cache\essai-evaluation\cuda
python -m forge evaluer --sauvegarde D:\forge-ia-donnees\entrainements\ton-ia\sauvegardes\meilleur.pt --donnees principal --qcm 20 --appareil cpu --sortie D:\forge-ia-donnees\cache\essai-evaluation\cpu

# 14 novembre : l'évaluation complète (toutes les questions), puis l'export
python -m forge evaluer --sauvegarde D:\forge-ia-donnees\entrainements\ton-ia\sauvegardes\meilleur.pt --donnees principal --appareil cuda
python -m forge exporter --sauvegarde D:\forge-ia-donnees\entrainements\ton-ia\sauvegardes\meilleur.pt --sortie D:\forge-ia-donnees\publication\ton-ia-1.5
```

Les deux commandes de l'essai chronométré ont tourné sous un petit script de relevé, qui lance la
même commande et note en plus les fils de PyTorch, la charge de chaque cœur et la durée de chaque
étape (voir la section 3).

## 1. Le modèle et ses réglages

Les réglages sont ceux de `projets/forge/configs/principal.toml`, choisis le 3 novembre 2026
(voir `docs/mesures/entrainement-2026-11.md`, « Le choix du 3 novembre 2026 ») :

| Réglage | Valeur |
| --- | --- |
| Taille (`preset`) | « tres_grand » : dimension 1 280, 20 couches, 20 têtes, contexte de 2 048 jetons, 433 573 120 paramètres |
| Jetons par pas | 524 288 (256 lignes de 2 048 jetons : 256 micro-lots d'une ligne) |
| Jetons lus en tout | 8 671 723 520, soit 16 540 pas, 20 jetons par paramètre |
| Taux d'apprentissage | montée de 0 à 4 × 10⁻⁴ pendant 500 pas, puis descente en cosinus jusqu'à 4 × 10⁻⁵ au dernier pas |
| AdamW | décroissance des poids 0,1, bêtas 0,9 et 0,95, écrêtage des gradients à 1,0 |
| Validation | tous les 200 pas, sur 64 morceaux fixes de 2 048 jetons (131 072 jetons) |
| Sauvegardes | au moins toutes les 30 minutes, et à chaque pause |
| Appareil, compilation | la carte graphique, sans `torch.compile` (`triton` manque sous Windows) |

Le corpus contient 8 841 217 367 jetons d'entraînement : l'entraînement en lit 98,1 %, et aucun
morceau n'est lu deux fois (une seule époque).

## 2. L'entraînement : la durée réelle

L'entraînement a tourné dans une fenêtre réduite, lancée par un script
(`D:\forge-ia-donnees\journaux\entrainement-principal.ps1`) qui recopie chaque ligne de l'écran, avec
son heure, dans `D:\forge-ia-donnees\journaux\entrainement-principal.log`. Chaque pause a été demandée
par Ctrl+C (`D:\forge-ia-donnees\journaux\pause-entrainement.ps1`), quand le PC servait à autre chose :
le pas en cours se termine, tout est sauvegardé (4,8 Go), puis le programme s'arrête. D'après
`pause-entrainement.log`, cela a pris de 17 à 33 s après le Ctrl+C, sauf le 5 novembre à 05:22:30 :
830 s, car le programme n'a reçu le signal que 13 min 32 s plus tard (il l'affiche à 05:36:02).
Chaque reprise est repartie exactement de la dernière sauvegarde. Le journal de l'entraînement
(`journal.jsonl`) a une ligne pour chacun des 16 540 pas, sans trou ni doublon, et aucun avertissement
ni aucune perte infinie.

| | |
| --- | --- |
| Premier lancement | 03/11/2026 à 19:39:40 |
| Fin (« Entraînement terminé au pas 16540 ») | 14/11/2026 à 23:22:45 |
| **Durée totale réelle**, du premier lancement à la fin | **11 j 3 h 43 min 05 s** (963 785 s) |
| **Temps de calcul**, sans les pauses (champ `secondes` du journal) | **139 h 06 min 32 s** (500 791,9 s, soit 5 j 19 h 06 min) |
| Sessions, du lancement du script à la fin de Python | 13, 139 h 15 min 09 s en tout |
| Pauses entre deux sessions | 12, 128 h 27 min 58 s en tout (5 j 8 h 28 min) |
| Part du calcul dans la durée totale | 52,0 % |
| Temps de calcul estimé avant le lancement | 135 h (8 671 723 520 jetons à 17 855 jetons par seconde) : réel +3,0 % |
| Débit moyen sur tout le calcul | 17 316 jetons par seconde (mesuré avant : 17 855, −3,0 %) |
| Débit affiché pas à pas | médiane 18 009, de 3 268 à 18 260 jetons par seconde |
| Validations | 83 (tous les 200 pas, plus le dernier) |
| Sauvegardes d'étape | 280 ; il reste `etape-0016518.pt` et `etape-0016540.pt` (4,85 Go chacune) et `meilleur.pt` (1,62 Go, pas 16 540) |

Les 8 min 37 s d'écart entre la somme des sessions et le temps de calcul sont les démarrages (charger
PyTorch, les données et le modèle : de 13 à 85 s par session, du lancement du script au message
« Reprise au pas… ») et les arrêts de Python après la dernière sauvegarde. Le temps de calcul compte
les validations et les sauvegardes faites en cours de route. Si l'on part de la deuxième session
(19:54:14, après la première, de 23 pas), la durée totale réelle est de 11 j 3 h 28 min 31 s.

Les sessions, d'après le journal d'écran (heures) et le journal de l'entraînement (pas et calcul) :

| Session | Lancement | Fin | Pas | Pas faits | Calcul | Débit moyen (jetons/s) | Pause qui suit |
| ---: | --- | --- | --- | ---: | ---: | ---: | ---: |
| 1 | 03/11 19:39 | 03/11 19:52 | 0 → 23 | 23 | 12 min 25 s | 16 196 | 1 min 43 s |
| 2 | 03/11 19:54 | 04/11 18:16 | 23 → 2 752 | 2 729 | 22 h 22 min | 17 768 | 1 h 17 min |
| 3 | 04/11 19:34 | 05/11 05:36 | 2 752 → 3 974 | 1 222 | 10 h 01 min | 17 752 | 37 min 27 s |
| 4 | 05/11 06:13 | 05/11 16:59 | 3 974 → 5 283 | 1 309 | 10 h 45 min | 17 731 | 1 min 36 s |
| 5 | 05/11 17:01 | 05/11 17:13 | 5 283 → 5 304 | 21 | 11 min 50 s | 15 499 | 2 h 59 min |
| 6 | 05/11 20:13 | 06/11 07:12 | 5 304 → 6 646 | 1 342 | 10 h 58 min | 17 801 | 3 h 45 min |
| 7 | 06/11 10:57 | 07/11 18:15 | 6 646 → 10 479 | 3 833 | 1 j 7 h 17 min | 17 842 | 4 h 37 min |
| 8 | 07/11 22:53 | 08/11 09:32 | 10 479 → 11 775 | 1 296 | 10 h 39 min | 17 706 | 13 h 26 min |
| 9 | 08/11 22:59 | 09/11 14:06 | 11 775 → 13 550 | 1 775 | 15 h 06 min | 17 108 | 17 h 45 min |
| 10 | 10/11 07:51 | 10/11 13:20 | 13 550 → 14 137 | 587 | 5 h 27 min | 15 662 | 11 h 28 min |
| 11 | 11/11 00:48 | 11/11 11:12 | 14 137 → 15 362 | 1 225 | 10 h 22 min | 17 185 | 2 j 18 h 03 min |
| 12 | 14/11 05:15 | 14/11 11:42 | 15 362 → 16 033 | 671 | 6 h 24 min | 15 239 | 6 h 23 min |
| 13 | 14/11 18:05 | 14/11 23:22 | 16 033 → 16 540 | 507 | 5 h 16 min | 14 005 | (fin) |

- **Deux sessions très courtes** (1 et 5) : 23 et 21 pas, mises en pause au bout d'une douzaine de
  minutes. La première a repris 1 min 43 s plus tard. Leur débit moyen est plus bas, surtout parce que
  les premiers pas d'une session sont lents : de 8 467 jetons par seconde au pas 1 à 18 053 au pas 6,
  et de 7 643 au pas 5 284 à 16 077 au pas 5 288.
- **La plus longue session** (7) a duré 31 h 17 min de calcul d'affilée, et **la plus longue pause**
  2 j 18 h 03 min (du 11 au 14 novembre).
- **Les sessions 10, 12 et 13 ont été plus lentes** (de 14 005 à 15 662 jetons par seconde, contre
  17 108 à 17 842 pour les autres longues sessions). Le journal ne dit pas pourquoi, et la cause n'a
  pas été étudiée.

### La courbe

La perte de validation du journal est mesurée tous les 200 pas sur les mêmes 64 morceaux (131 072
jetons). Les dixièmes de l'entraînement (pas 1 654, 3 308…) ne tombent pas sur un multiple de 200 :
chaque ligne prend le pas de validation le plus proche, et la colonne « Pas » le dit. La perte
d'entraînement d'un seul pas bouge beaucoup ; on donne la moyenne des 20 derniers pas (sauf pour la
ligne « début », le pas 1 seul). Le temps est le temps de calcul, sans les pauses.

| Avancement | Pas | Jetons vus | Taux d'apprentissage | Perte d'entraînement (moyenne des 20 derniers pas) | Perte de validation | Temps de calcul |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| début (pas 1 seul) | 1 | 524 288 | 8,00 × 10⁻⁷ | 10,668 | pas mesurée | 1 min 02 s |
| 10 % | 1 600 | 838 860 800 | 3,96 × 10⁻⁴ | 3,016 | 3,047 | 13 h 05 min |
| 20 % | 3 400 | 1 782 579 200 | 3,72 × 10⁻⁴ | 2,766 | 2,812 | 27 h 52 min |
| 30 % | 5 000 | 2 621 440 000 | 3,34 × 10⁻⁴ | 2,655 | 2,712 | 41 h 02 min |
| 40 % | 6 600 | 3 460 300 800 | 2,86 × 10⁻⁴ | 2,606 | 2,651 | 54 h 08 min |
| 50 % | 8 200 | 4 299 161 600 | 2,31 × 10⁻⁴ | 2,548 | 2,599 | 67 h 08 min |
| 60 % | 10 000 | 5 242 880 000 | 1,69 × 10⁻⁴ | 2,491 | 2,554 | 81 h 53 min |
| 70 % | 11 600 | 6 081 740 800 | 1,18 × 10⁻⁴ | 2,480 | 2,522 | 94 h 57 min |
| 80 % | 13 200 | 6 920 601 600 | 7,72 × 10⁻⁵ | 2,441 | 2,496 | 108 h 14 min |
| 90 % | 14 800 | 7 759 462 400 | 5,04 × 10⁻⁵ | 2,442 | 2,478 | 122 h 48 min |
| 100 % | 16 540 | 8 671 723 520 | 4,00 × 10⁻⁵ | 2,407 | 2,467 | 139 h 06 min |

- **Le début va très vite** : la validation passe de 5,404 au pas 200 à 3,709 au pas 600, sous 3 au
  pas 2 000, et la perte d'entraînement est à 3,016 à 10 % de l'entraînement.
- **Puis chaque gain coûte plus cher** : de 70 % à 100 %, la validation ne gagne plus que 0,054, et
  0,010 sur les derniers 10 % (le taux d'apprentissage est alors presque à son plancher). Elle passe
  sous 2,5 au pas 13 000.
- **Elle baisse à chaque mesure, sans exception**, sur les 83 mesures : la meilleure est la dernière
  (2,467 au pas 16 540). C'est pourquoi `meilleur.pt` vient du dernier pas.
- **L'écart entre l'entraînement et la validation reste petit et stable** : de 0,02 à 0,07 à partir
  du pas 1 000, 0,060 à la fin. Pour « mini », qui relisait 3,5 fois ses textes, il grandissait
  jusqu'à 0,226. Ici, chaque texte n'est lu qu'une fois : la perte d'entraînement est
  mesurée sur des textes que le modèle n'a encore jamais vus, et l'écart ne vient pas d'un
  apprentissage par cœur. Il vient sans doute de ce que les 64 morceaux de validation ne sont pas
  exactement aussi difficiles que la moyenne du corpus.

## 3. L'évaluation

### La carte ou le processeur : l'essai chronométré

Ta règle : avant un travail de plus de 30 minutes, un essai chronométré sur la carte graphique et sur
le processeur, puis on prend le plus rapide. L'essai est une évaluation complète de `meilleur.pt`, mais
avec 20 questions de chaque QCM (`--qcm 20`) : la perte sur les 1 024 morceaux (128 lots de 8
morceaux de 2 048 jetons), les 40 questions et les dix échantillons. Le processeur avait 10 minutes au
plus.

| | Carte graphique (RTX 5070 Ti, bf16) | Processeur (Ryzen 7 9800X3D, 32 bits) |
| --- | ---: | ---: |
| Fils de PyTorch (`torch.get_num_threads()`) | 8, le réglage par défaut (le calcul est sur la carte) | **16** : 8 par défaut, puis 16 réglés par forge (`os.cpu_count()`) |
| Démarrage (sauvegarde, données, modèle) | 6,8 s | 4,7 s |
| Perte sur 1 024 morceaux | 54,6 s (0,43 s par lot) | **arrêtée à 10 minutes** : 24 lots sur 128, de 24,3 à 24,8 s par lot |
| Chargement des questions (réseau) | 10,3 s | pas atteint |
| QCM (2 × 20 questions) | 0,4 s | pas atteints |
| Échantillons | 17,9 s | pas atteints |
| **Durée de l'essai** | **90,6 s** | **plus de 600 s** (arrêté) |

- **Sur le processeur, les 16 cœurs logiques travaillaient** : 59 relevés de charge (un toutes les 10 s,
  avec `psutil`), et à chacun, après le premier, les 16 cœurs étaient au-dessus de 90 % (92 % pour le
  moins chargé, 99,4 % en moyenne). Le processus de l'évaluation occupait en moyenne 11,7 cœurs
  (de 9,7 à 12,6).
- **Une réserve** : pendant les deux essais, d'autres programmes compilaient du code Rust
  (`rustc.exe`, sans rapport avec la forge). Au premier relevé de l'essai sur la carte, les cœurs
  étaient chargés à 88 % en moyenne alors que l'évaluation n'en occupait qu'un ; juste après l'essai
  sur le processeur, cinq `rustc.exe` occupaient encore environ 6 cœurs. Ils ont donc ralenti le
  processeur, sans changer le verdict : à 24,5 s par lot contre 0,43 s, **la carte va environ 57 fois
  plus vite**. Même avec 16 cœurs au lieu des 11,7 obtenus (une estimation qui suppose un calcul
  proportionnel au nombre de cœurs), elle irait encore environ 40 fois plus vite. La perte seule
  aurait pris environ 52 minutes sur le processeur.
- **Choix : la carte graphique**, pour l'évaluation complète.

L'évaluation complète (toutes les questions) a duré **2 min 38 s** du lancement à la fin (150,6 s
pour l'évaluation elle-même, d'après le rapport). Huit relevés de `nvidia-smi`, un toutes les 10 s :
la carte était occupée de 86 % à 96 % (55 % au dernier relevé, à la fin), avec 10,8 Go de mémoire
(13,1 Go au premier relevé), de 196 à 219 W, entre 54 et 61 °C.

### Perte, perplexité, bits par octet

Sur 1 024 morceaux fixes de 2 048 jetons de la validation, soit 2 097 152 jetons jamais appris :

| Mesure | Valeur | Ce que cela veut dire |
| --- | --- | --- |
| Perte de validation | 2,419 nats par jeton | contre 10,397 pour le hasard |
| Perplexité | 11,2 | le modèle hésite comme s'il choisissait entre 11 jetons également probables, au lieu de 32 768 |
| Octets par jeton | 4,35 | taille moyenne d'un jeton dans ces données |
| Bits par octet (estimation) | 0,802 | la perte ramenée à un octet de texte |

La perte de l'évaluation (2,419) diffère de la dernière valeur du journal (2,467) : ce ne sont pas les
mêmes morceaux (1 024 ici, 64 dans la boucle). L'évaluation, sur 16 fois plus de jetons, est la plus
fiable.

**Comparé à « mini »** (`docs/mesures/ton-ia-mini.md`) :

| | « mini » | ton IA 1.5 |
| --- | ---: | ---: |
| Paramètres | 23,2 millions | 433,6 millions |
| Jetons lus | 0,83 milliard (chaque texte lu 3,5 fois) | 8,67 milliards (chaque texte lu une fois) |
| Temps de calcul | 60 min 17 s | 139 h 06 min |
| Contexte | 512 jetons | 2 048 jetons |
| Perte de validation (évaluation) | 3,428 | 2,419 |
| Perplexité | 30,8 | 11,2 |
| Bits par octet | 1,133 | 0,802 |
| HellaSwag (exactitude normalisée) | 27,2 % | 34,8 % |
| ARC-Challenge (exactitude normalisée) | 23,6 % | 25,1 % |

La comparaison de la perte, de la perplexité et des bits par octet n'est qu'indicative : la
validation de « mini » vient du corpus « court », celle de ton IA du corpus « principal » (mêmes
sources, même mélange, mais d'autres documents), et ton IA lit des morceaux 4 fois plus longs, ce qui
l'aide à prédire. Les QCM, eux, sont les mêmes questions, mesurées de la même façon.

### Les questions à choix multiples (FrenchBench)

Deux tests, toutes les questions de chacun : HellaSwag (finir une histoire, 4 fins possibles) et
ARC-Challenge (questions de sciences, de 3 à 5 réponses), des traductions automatiques en français.
Ton IA « répond » par le choix qui lui paraît le plus vraisemblable. Le verdict compare l'exactitude
normalisée (corrigée de la longueur des réponses) au hasard, avec la marge d'un résultat qui ne
devrait qu'au hasard.

| Test | Questions | Exactitude | Exactitude normalisée | Hasard | Marge du hasard | Verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| HellaSwag (français) | 9 338 | 29,7 % | 34,8 % | 25,0 % | ± 0,9 point | au-dessus du hasard |
| ARC-Challenge (français) | 1 169 | 20,6 % | 25,1 % | 25,0 % | ± 2,5 points | pas différent du hasard |

- **HellaSwag** : 34,8 % contre 25,0 % au hasard, soit 9,8 points de plus, pour une marge de
  0,9 point. Cela fait 3 248 bonnes réponses sur 9 338, environ 900 de plus qu'un tirage au sort
  (2 334,5 en moyenne). « mini » n'avait que 2,2 points d'avance : ton IA choisit bien plus souvent la
  fin qui a du sens. Mais elle se trompe encore à près de deux questions sur trois.
- **ARC-Challenge** : 25,1 % contre 25,0 % : **pas différent du hasard**, comme pour « mini ». Sur ces
  questions de sciences, ton IA ne fait pas mieux qu'un tirage au sort. L'exactitude brute (20,6 %)
  est même sous le hasard, sans doute parce que la somme des
  log-vraisemblances favorise les réponses courtes ; la version normalisée corrige cela.
- **Mesure maison** : comparable aux autres modèles de la forge et au hasard, pas aux scores publiés
  de FrenchBench (gabarit des questions, jeton de début et normalisation par octets sont les nôtres).

## 4. Les échantillons

Dix textes écrits par ton IA à partir de débuts fixes : température 0,8, top-k 50, 60 jetons au plus,
graine 0 (puis 1, 2… pour les débuts suivants), sur la carte graphique. Mêmes réglages, mêmes textes.
**Ce sont les dix, sans tri, tels que les donne `rapport.json`.** Le début donné est au début du bloc,
la suite est celle du modèle (elle s'arrête au 60ᵉ jeton, souvent au milieu d'une phrase).

### 1. « Il était une fois »

```text
Il était une fois, un homme qui a reçu une lettre d’amour pour une fille. Il a reçu une lettre d’amour mais elle a oublié de la porter. Il a donc dû la prendre et tout faire pour l’oublier… Mais elle ne l’a pas oublié et elle a oublié de lui dire qu’elle était tombée
```

### 2. « La capitale de la France est »

```text
La capitale de la France est Paris. Pour les touristes, elle est la destination idéale. Paris est une ville cosmopolite. Capitale de la France, la ville est un lieu incontournable pour tout voyageur parisien.
Budapest : un voyage à Budapest
Budapest est une ville de Hongrie. Sa
```

### 3. « Pour faire un bon gâteau au chocolat, il faut »

```text
Pour faire un bon gâteau au chocolat, il faut de la pâte à choux, des raisins secs, des pépites de chocolat, des raisins secs et du sucre en poudre. Cette liste va évidemment vous donner toutes les informations indispensables, mais vous pouvez aussi en donner un peu à tout le monde.
Méthode de préparation
Il vous faut
```

### 4. « Le soleil se couchait sur la mer et »

```text
Le soleil se couchait sur la mer et le ciel se couchait sur les nuages …. A vrai dire, en plus de cela, je n’ai pas eu le temps de faire tout ce que j’ai fait … car avec ma canne a pêche, je n’ai pas trop le temps d’aller faire une grosse balade. J’ai juste le
```

### 5. « Aujourd'hui, le gouvernement a annoncé »

```text
Aujourd'hui, le gouvernement a annoncé la suppression de 300 emplois en cinq ans. Avec, sans surprise, des conséquences sur l'emploi qui seront connues peu après. Il ne faudrait pas que cela se reproduise. L'ensemble des réformes engagées depuis le début de l'année et dont nous avons parlé hier a pour objectif de faire baisser la
```

### 6. « Dans un petit village de Bretagne, »

```text
Dans un petit village de Bretagne, des amis se rencontrent au milieu des années 80. Trois amis d’enfance et de jeunesse, issus de l’immigration, qui vont devenir parents. Trois amis qui vont changer le cours de l’Histoire et de leur vie. Leurs destins vont basculer dans un conflit qui va marquer la vie des trois amis
```

### 7. « La photosynthèse est le processus par lequel »

```text
La photosynthèse est le processus par lequel une molécule chimique se transforme en une autre en lui-même et se transforme en une partie. La photosynthèse est considérée comme l’énergie libérée lors de la photosynthèse. Cela sous-entend que la lumière dans la nature est un produit de la photosynthèse. La source de lumière dans
```

### 8. « Bonjour, je voudrais savoir comment »

```text
Bonjour, je voudrais savoir comment je peux obtenir une remise de 15% sur ma facture EDF. Mon ancien compteur était au mur. J'ai également un compteur Linky. J'ai plusieurs personnes qui ont eu ce soucis et aucun d'eux n'a eu ce problème. Je suis sur le point de procéder à l'ouverture de ce
```

### 9. « def factorielle(n): »

```python
def factorielle(n):
    return sum(set(range(n)) - set(range(n)))


def factors(n):
    return [n*i for i in range(1, n)]

# def factorielle(n, k):
#     return (n*k)
```

Ici, ton IA a écrit `<|fin_texte|>` après 50 jetons : elle a choisi de s'arrêter là.

### 10. « def moyenne(valeurs): »

```python
def moyenne(valeurs):
    """Renvoie la moyenne des votes, de façon à ce que l'électeur vote pour l'une des différentes valeurs de cette moyenne.
Les estimations ont été faites pour des valeurs comprises entre 0 et 100, et ne dépassent pas 0,01%. Si l'électeur a voté pour l'une des valeurs et que
```

Ce qu'on y voit :

- **Un français bien plus sûr.** Les phrases sont presque toutes correctes (accords, ponctuation), à
  quelques fautes près, celles du web (« canne a pêche », « ce soucis »). Le ton suit le début donné :
  conte, presse (« la suppression de 300 emplois en cinq ans »), résumé de roman ou de film (« Trois
  amis d'enfance… »), message de forum (« Bonjour, je voudrais savoir comment je peux obtenir une
  remise… »), recette (« Méthode de préparation »). Elle garde le sujet sur deux ou trois phrases, ce
  que « mini » ne faisait pas.
- **Quelques faits justes.** « La capitale de la France est Paris », puis « Budapest est une ville de
  Hongrie » : vrai. « mini » écrivait « la ville de la capitale ».
- **Mais ce qu'elle dit n'est pas fiable.** La recette du gâteau au chocolat demande de la pâte à
  choux et deux fois des raisins secs ; la photosynthèse devient « l'énergie libérée lors de la
  photosynthèse », et la lumière « un produit de la photosynthèse » ; les 300 emplois supprimés sont
  inventés.
- **Elle se contredit vite** : « elle a oublié de la porter… Mais elle ne l'a pas oublié » ; « plusieurs
  personnes qui ont eu ce soucis et aucun d'eux n'a eu ce problème » ; « le ciel se couchait sur les
  nuages ».
- **Le code a la forme du code, pas encore son sens.** `factorielle` est du Python valide, bien
  indenté, et le modèle s'arrête tout seul (`<|fin_texte|>`). Mais elle renvoie
  `sum(set(range(n)) - set(range(n)))`, c'est-à-dire toujours 0, et la fonction suivante ne calcule
  pas des facteurs. Pour `moyenne`, la docstring bascule en plein milieu vers un texte sur des
  élections : le modèle a quitté le code pour la prose.

## 5. Ce que ton IA sait faire, et ce qu'elle ne sait pas faire

Ton IA a **433 millions de paramètres** et a lu **8,7 milliards de jetons**, chacun une fois. Les
modèles de langage utilisés au quotidien ont des centaines de fois plus de paramètres et ont lu des
centaines ou des milliers de fois plus de texte. Ton IA 1.5 n'est pas un assistant.

**Ce qu'elle sait faire**

- Écrire un français correct et naturel, dans le ton du début qu'on lui donne (récit, presse, forum,
  recette), en gardant le sujet deux ou trois phrases.
- Prolonger un début de fonction Python par du code qui a la bonne forme (indentation, `return`,
  docstring), et parfois juste pour un cas très simple (`addition`, dans la section 6).
- Retrouver quelques faits très fréquents dans ses textes (Paris, capitale de la France).
- Prédire le jeton suivant bien mieux que « mini » : une perplexité de 11,2 au lieu de 30,8, et
  choisir la bonne fin d'histoire dans 34,8 % des questions de HellaSwag, contre 25 % au hasard.

**Ce qu'elle ne sait pas faire**

- **Répondre à une question ou suivre une consigne.** Elle n'a appris qu'à prolonger du texte brut,
  jamais à dialoguer (aucun entraînement sur des conversations) : si tu lui poses une question, elle
  écrit la suite d'un texte qui commence par ta question.
- **Dire des choses vraies de façon fiable.** Elle invente des chiffres, des faits et des recettes ; ce
  qu'elle écrit est vraisemblable, pas vérifié.
- **Rester cohérente longtemps.** Au-delà de quelques phrases, elle se contredit ou change de sujet.
- **Écrire du code qui marche**, sauf pour des fonctions très simples.
- **Réussir un QCM de sciences** : ARC-Challenge est au niveau du hasard.
- **Lire plus de 2 048 jetons d'un coup** (environ 8 900 octets de texte, à 4,35 octets par jeton) :
  au-delà, le début est oublié.
- **L'anglais** n'est pas visé : le corpus est du français et du code Python (où l'anglais apparaît
  dans les noms et les commentaires).

Deux réserves sur ces mesures : les échantillons sont un tirage (10 textes, une graine), et les QCM
sont des traductions automatiques mesurées avec notre propre méthode. Ils servent à comparer entre eux
les modèles de la forge, pas à classer ton IA face à des modèles publics.

## 6. Les fichiers de la version `ton-ia-1.5`

`python -m forge exporter` (ajouté pour cette tâche, `projets/forge/forge/exporter.py`) a écrit les
trois fichiers du modèle en 11 s à partir de `meilleur.pt`. Les trois autres sont des copies. Tous sont
dans `D:\forge-ia-donnees\publication\ton-ia-1.5\` :

| Fichier | Taille | SHA-256 | Contenu |
| --- | ---: | --- | --- |
| `ton-ia-1.5.safetensors` | 867 161 248 octets (827,0 Mo) | `0e89f94133ea47a65e2cd19c111beb24f3ae210c9e332f92c6538a2e22b0d6ea` | les poids, en bf16 |
| `config.json` | 134 octets | `ae0207b367080a6577c2d95ef81ba5fb84c6bf2be11d03a07eedd8a9fe598621` | les dimensions du modèle |
| `tokenizer-ton-ia-v1.json` | 546 692 octets (0,5 Mo) | `3001e7ab40630739c4dec807c7a92c0d4fb469cc0fc4afa368704395391f21ba` | le tokenizer, copie à l'octet près de celui du dépôt |
| `rapport.json` | 5 800 octets | `059355969c2eab459b9d19b20c6540450fa4f3e52b361bbcd343e86321a140bc` | le rapport de `forge evaluer`, tel quel |
| `ton-ia-1.5.md` | — | — | ce document |
| `LISEZMOI.md` | — | — | la fiche de la version (source : `docs/mesures/ton-ia-1.5-LISEZMOI.md`) |

Les deux derniers sont des copies, à l'octet près, des deux documents du dépôt (un document ne peut
pas contenir sa propre empreinte).

**Les poids.** Le fichier contient 142 tableaux de nombres, 433 573 120 nombres en tout, en bf16
(16 bits chacun : deux fois moins lourds que les 32 bits de `meilleur.pt`). Ses métadonnées disent
`{"format": "pt", "pas": "16540"}`. Les noms sont ceux de `forge.modele.Transformer` :

- `plongement.weight` (32 768 × 1 280) et `norme_finale.poids` (1 280) ;
- pour chaque bloc `i` de 0 à 19 : `blocs.i.norme_attention.poids`, `blocs.i.attention.proj_qkv.weight`
  (3 840 × 1 280), `blocs.i.attention.proj_sortie.weight` (1 280 × 1 280), `blocs.i.norme_mlp.poids`,
  `blocs.i.mlp.proj_porte.weight` et `blocs.i.mlp.proj_haute.weight` (3 392 × 1 280),
  `blocs.i.mlp.proj_basse.weight` (1 280 × 3 392) ;
- **`sortie.weight` manque, exprès** : la sortie du modèle est la même matrice que le plongement
  (poids liés), et safetensors refuse deux noms pour une même matrice. Au chargement, on la reprend
  du plongement.

**La configuration** (`config.json`) contient exactement les champs de `ConfigModele` :
`taille_vocabulaire` 32 768, `dim` 1 280, `couches` 20, `tetes` 20, `longueur_contexte` 2 048,
`base_rope` 10 000. `ConfigModele(**config)` reconstruit le modèle.

**Vérifié** : rechargés de cette façon, les poids sont identiques à ceux de `meilleur.pt` passés en
bf16, et le modèle donne exactement les mêmes logits que `meilleur.pt` passé en bf16. Il écrit aussi
(sur la carte, en bf16, température 0,8, top-k 50, graine 0, 30 jetons) :

```text
Il était une fois, un homme qui a reçu une lettre d’amour pour une fille. Il a reçu une lettre d’amour mais elle a oublié de la porter. Il
```

```python
def addition(a, b):
    return a + b

def addition_with_newlines(a, b):
    return a + b

def addition_with_space_after_insert(a
```

Le premier texte est le début de l'échantillon 1 de l'évaluation, au caractère près. Le second montre
une fonction très simple écrite juste, puis des copies sans intérêt.

Pour recharger ton IA :

```python
import json
from pathlib import Path

from safetensors.torch import load_file

from forge.modele import ConfigModele, Transformer

dossier = Path(r"D:\forge-ia-donnees\publication\ton-ia-1.5")
config = ConfigModele(**json.loads((dossier / "config.json").read_text(encoding="utf-8")))
poids = load_file(dossier / "ton-ia-1.5.safetensors")
poids.setdefault("sortie.weight", poids["plongement.weight"])  # les poids liés
modele = Transformer(config)
modele.load_state_dict(poids)
```

## Où sont les fichiers

- **Dépôt :** ce document, la fiche `docs/mesures/ton-ia-1.5-LISEZMOI.md`, la commande
  `forge exporter` et ses tests (`projets/forge/tests/test_exporter.py`). Aucun poids ni aucune
  donnée dans git.
- **Hors dépôt**, sous `D:\forge-ia-donnees` :
  - l'entraînement, laissé tel quel : `entrainements\ton-ia\journal.jsonl` (2,48 Mo) et
    `entrainements\ton-ia\sauvegardes\` (`etape-0016518.pt`, `etape-0016540.pt`, `meilleur.pt`) ;
  - le rapport d'évaluation : `entrainements\ton-ia\evaluation\meilleur\rapport.json` et `rapport.md` ;
  - les journaux d'écran : `journaux\entrainement-principal.log`, `journaux\pause-entrainement.log` et
    `journaux\evaluation-ton-ia-1.5.log` ;
  - les fichiers de la version : `publication\ton-ia-1.5\` ;
  - le rapport de l'essai sur la carte, jetable : `cache\essai-evaluation\cuda\`.
