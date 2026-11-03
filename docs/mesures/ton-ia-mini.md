# Ton IA, version courte : une heure d'entraînement du modèle « mini »

Entraîné et évalué le 3 novembre 2026 (2026-11-03).

Ce document raconte le premier parcours de bout en bout de la forge : télécharger des textes, les
encoder, **entraîner pendant une heure sur la carte graphique le plus petit modèle (« mini »)**, puis
l'évaluer. Il donne les durées et les chiffres mesurés, et il dit sans fard **ce que cette version
d'une heure de ton IA sait faire et ce qu'elle ne sait pas faire**. C'est une répétition générale : l'entraînement
principal (étape suivante du plan) utilisera une bien plus grande taille et bien plus de données.

Unités : dans tout ce document, « Mo » et « Go » valent 1 048 576 et 1 073 741 824 octets (comme l'Explorateur de
Windows et les autres documents de ce dossier).

## En bref

- **Le modèle :** « mini », 23 204 736 paramètres (23,2 millions), dimension 384, 6 couches,
  6 têtes, contexte de 512 jetons, vocabulaire de 32 768 jetons (le tokenizer figé `ton-ia-v1`).
- **Les données :** 1 000 Mo de texte (75 % de français du web, 10 % de Wikipédia, 15 % de code Python),
  soit 239 242 872 jetons d'entraînement et 1 206 420 de validation. Téléchargées en 127 s, encodées en 33 s.
- **L'entraînement :** 6 370 pas de 131 072 jetons, soit 834 928 640 jetons lus (3,5 fois les données),
  en **60 min 17 s** de boucle sur la RTX 5070 Ti (60 min 28 s du lancement à la dernière sauvegarde), à 230 815 jetons par seconde en moyenne
  (mesuré avant : 231 934, un écart de −0,5 %).
- **La courbe :** la perte d'entraînement part de 10,477 au pas 1, le niveau du hasard (ln 32 768 = 10,4) ; la perte de
  validation, mesurée pour la première fois au pas 100, y est à 6,30 et finit à 3,455 d'après le
  journal de l'entraînement (3,428 à l'évaluation finale, sur plus de morceaux).
- **L'évaluation :** perplexité **30,8**, **1,133 bit par octet**. Aux QCM
  français : HellaSwag 27,2 % contre 25,0 % au hasard (**au-dessus du hasard**, de peu),
  ARC-Challenge 23,6 % contre 25,0 % (**pas différent du hasard**).
- **Ce que cela donne :** un modèle qui écrit des phrases françaises souvent bien formées, avec le ton
  du web, de la presse ou d'un forum, mais **qui ne sait rien de façon fiable**, qui perd le fil en deux
  phrases et dont le code ne marche pas (voir « Les échantillons » et « Ce que ton IA sait faire »).

## Les commandes, dans l'ordre

Elles sont celles du `README` du projet. Lancées depuis `projets/forge`, après `. .\outils\env-forge.ps1`
à la racine du dépôt, avec le Python de `.venv` (même résultat que `uv run --extra gpu python`).

```powershell
python -m forge mesurer --presets mini --json mini.json
python -m forge donnees --octets 1000M --dossier court
python -m forge encoder --donnees court --tokenizer forge\ressources\tokenizer-ton-ia-v1.json
python -m forge entrainer --config configs/mini.toml
python -m forge evaluer --sauvegarde D:\forge-ia-donnees\entrainements\ton-ia-mini\sauvegardes\etape-0006370.pt --donnees court
```

## 1. La vitesse de « mini », mesurée avant de commencer

Ta règle : avant un travail de plus de 30 minutes, un essai chronométré sur la carte graphique
et sur le processeur (avec les 16 fils du Ryzen), puis on choisit. La commande `python -m forge mesurer
--presets mini` a duré 87 s. La carte était libre (2 % d'utilisation, 1,5 Go déjà pris par Windows) ;
le processeur était à 18 % au repos.

**Carte graphique** (RTX 5070 Ti, 20 pas chronométrés de 8 micro-lots, en bf16, sans compilation) :

| Micro-lot (lignes de 512 jetons) | Jetons par seconde | Pic de mémoire | Remarque |
| ---: | ---: | ---: | --- |
| 1 | 32 465 | 0,64 Go |  |
| 2 | 63 257 | 0,90 Go |  |
| 4 | 121 004 | 1,41 Go |  |
| 8 | 187 165 | 2,42 Go |  |
| 16 | 231 934 | 4,44 Go | le plus rapide |
| 32 | 224 780 | 8,47 Go |  |
| 42 | 211 883 | 11,02 Go | le plus grand qui tient |

Le micro-lot 16 est le plus rapide (231 934 jetons par seconde) ; le plus grand qui tient en mémoire
(42) va 9 % moins vite : le plus grand n'est pas le meilleur, comme pour les autres tailles.

**Processeur** (Ryzen 7 9800X3D, 16 fils, micro-lot de 2) : 2 707 jetons par seconde sur 20 pas.
Les 16 cœurs logiques étaient à fond : au moins 99,8 % de charge sur chacun (moyenne 100 %),
et le processus occupait en moyenne 12,4 cœurs. La carte va donc **86 fois plus vite**
que le processeur. Pour 20 jetons par paramètre, cela ferait 33 min sur la carte et 47,6 h
sur le processeur. **Choix : la carte graphique** (c'est aussi ce que tu avais choisi après la mesure des vitesses de toutes les tailles).

## 2. Les données « court »

**Combien de texte ?** Une heure sur la carte lit 834 962 400 jetons (231 934 × 3 600).
Règle fixée pour cette version : **au plus 4 lectures de chaque jeton**. Lire quatre fois les mêmes
textes apporte encore beaucoup ; au-delà, un modèle commence à apprendre les textes par cœur au lieu
d'apprendre la langue (on le voit déjà un peu ici, plus bas). Il faut donc au moins
834 962 400 ÷ 4 = 208 740 600 jetons différents. À 4,4 octets de texte par jeton :
918,5 millions d'octets, arrondis à la centaine de millions au-dessus : **1 000 M**
(le plafond était 2 000 M). Dans la commande, « M » vaut 1 048 576 octets, donc 1 048 576 000 octets en tout,
répartis 750 Mo de web français, 100 Mo de Wikipédia, 150 Mo de code Python.

**Téléchargement** (`python -m forge donnees --octets 1000M --dossier court`) : 127 s, soit 7,9 Mo de texte
par seconde (0,13 s par Mo).
724 070 documents lus (215 761 de web, 5 322 de Wikipédia, 502 987 de code), 11 fragments, 353 Mo une fois
compressés (gzip) sur le disque.

**Encodage** (`python -m forge encoder --donnees court`) : 33 s, soit 30,0 Mo de texte par seconde, avec 11 processus
en parallèle (un par fragment ; `psutil` a compté 14 processus descendants en tout, lanceur et processus d'aide compris). Résultat : **239 242 872 jetons d'entraînement et 1 206 420 de validation**, 4,37 octets par jeton.
Chaque jeton est donc lu 3,49 fois pendant l'entraînement (au plus 4 : respecté).
Charge relevée avec `psutil` pendant l'encodage (un relevé toutes les 3 s) : **les 16 cœurs logiques étaient
tous au-dessus de 50 %** de la 6ᵉ à la 15ᵉ seconde (moyenne de 81 % à 87 %), 15 sur 16 jusqu'à la 24ᵉ seconde, puis la
charge retombait avec les derniers fragments. Sur toute la fenêtre de 33 s, départ et fin compris : 62 % de charge
moyenne, de 42 % à 80 % selon le cœur ; pic de 87 %.

## 3. Le réglage de `configs/mini.toml`

| Réglage | Valeur | Pourquoi |
| --- | --- | --- |
| `preset` | `"mini"` | 23,2 millions de paramètres |
| `micro_lot` | 16 | le plus rapide mesuré (4,4 Go de mémoire) |
| `taille_lot_jetons` | 131 072 | 256 lignes de 512 jetons par pas : 16 micro-lots de 16 lignes |
| `jetons_total` | 834 928 640 | 231 934 × 3 600 = 834 962 400, arrondi à 6 370 pas entiers |
| `taux_max`, `echauffement` | 0,001 ; 100 pas | montée de 0 à 0,001, puis descente en cosinus jusqu'à 0,0001 |
| `evaluation_tous_pas` | 100 | une perte de validation (64 morceaux de 512 jetons) tous les 100 pas |
| `sauvegarde_minutes` | 15 | au moins une sauvegarde tous les quarts d'heure |
| `appareil`, `compiler` | `"cuda"`, `"auto"` | `torch.compile` n'a pas `triton` sous Windows : mode immédiat |

Cela fait 36 jetons lus par paramètre (la cible de la forge est 20), mais seulement
10,3 jetons différents par paramètre, puisque chaque texte est lu 3,5 fois.

## 4. L'entraînement : la durée réelle

L'entraînement a tourné détaché de la fenêtre de commande, du début à la fin, sans pause ni reprise.

| | |
| --- | --- |
| Début (lancement du programme) | 14:41:22 |
| Dernière sauvegarde (fin) | 15:41:50 |
| Durée de la boucle (journal) | 3 617,3 s, soit 60 min 17 s |
| Pas | 6 370 |
| Jetons lus | 834 928 640 |
| Débit moyen sur toute la durée | 230 815 jetons par seconde |
| Débit affiché pas à pas (pas 101 à 6 370) | de 225 838 à 238 266, moyenne 234 138 |
| Débit mesuré avant | 231 934 jetons par seconde (écart de −0,5 %) |
| Carte graphique pendant l'entraînement | 90 à 93 % d'utilisation, 7,0 Go de mémoire, 232 W |
| Processeur pendant l'entraînement | environ un cœur de calcul sur 16, qui pilote la carte (le travail est sur la carte) |
| Validations | 64 (tous les 100 pas, plus la fin) |
| Sauvegardes | pas 1 589, 3 174, 4 766, 6 352 et 6 370 ; il reste `etape-0006352.pt`, `etape-0006370.pt` (265,6 Mo chacune) et `meilleur.pt` (88,5 Mo, pas 6 300) |

Du lancement à la dernière sauvegarde, il s'est écoulé 60 min 28 s ; la boucle, elle, a chronométré 60 min 17 s. Les 11 s
d'écart sont le démarrage (chargement de PyTorch, des données et du modèle) avant le premier pas, et l'écriture de la dernière sauvegarde.

### La courbe

La perte est en nats par jeton (un modèle qui devine au hasard parmi 32 768 jetons est à ln 32 768 = 10,397).
La perte de validation du journal est mesurée tous les 100 pas sur 64 morceaux de validation (32 768 jetons). Les
dixièmes de l'entraînement (pas 637, 1 274, 1 911…) ne tombent pas sur un multiple de 100 : chaque ligne du tableau
prend donc le pas de validation le plus proche (600, 1 300, 1 900…), et la colonne « Pas » le dit. La perte
d'entraînement d'un seul pas bouge beaucoup d'un pas à l'autre ; on donne la moyenne des 20 derniers pas (sauf
pour la ligne « début », qui est le pas 1 seul).

| Avancement | Pas | Jetons vus | Taux d'apprentissage | Perte d'entraînement (moyenne des 20 derniers pas) | Perte de validation | Temps écoulé |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| début (pas 1 seul) | 1 | 131 072 | 1,0 × 10⁻⁵ | 10,477 | pas mesurée | 2 s |
| 10 % | 600 | 78 643 200 | 9,86 × 10⁻⁴ | 4,065 | 4,210 | 5 min 41 s |
| 20 % | 1 300 | 170 393 600 | 9,21 × 10⁻⁴ | 3,669 | 3,842 | 12 min 18 s |
| 30 % | 1 900 | 249 036 800 | 8,29 × 10⁻⁴ | 3,543 | 3,729 | 17 min 58 s |
| 40 % | 2 500 | 327 680 000 | 7,12 × 10⁻⁴ | 3,497 | 3,656 | 23 min 39 s |
| 50 % | 3 200 | 419 430 400 | 5,58 × 10⁻⁴ | 3,425 | 3,595 | 30 min 17 s |
| 60 % | 3 800 | 498 073 600 | 4,24 × 10⁻⁴ | 3,333 | 3,546 | 35 min 57 s |
| 70 % | 4 500 | 589 824 000 | 2,83 × 10⁻⁴ | 3,309 | 3,510 | 42 min 33 s |
| 80 % | 5 100 | 668 467 200 | 1,88 × 10⁻⁴ | 3,284 | 3,480 | 48 min 14 s |
| 90 % | 5 700 | 747 110 400 | 1,25 × 10⁻⁴ | 3,215 | 3,466 | 53 min 55 s |
| 100 % | 6 370 | 834 928 640 | 1,00 × 10⁻⁴ | 3,229 | 3,455 | 60 min 17 s |

- **Les 10 premiers pour cent font l'essentiel du chemin** : la perte d'entraînement tombe de 10,477 au pas 1 (le hasard) à
  4,065 à 10 %, et la validation, mesurée pour la première fois au pas 100 (13 millions de jetons) à
  6,299, est à 4,210 au pas 600.
- **Puis la progression ralentit** : de 70 % à 100 % de l'entraînement, la validation ne gagne que
  0,055 nat, alors que le taux d'apprentissage descend encore de 2,8 × 10⁻⁴ à
  1,0 × 10⁻⁴. Un modèle de 23 millions de paramètres a une capacité limitée : relire les mêmes textes lui
  apporte de moins en moins.
- **La perte de validation baisse jusqu'au dernier pas** (meilleure valeur du journal : 3,454 au pas 6 300,
  3,455 au pas 6 370 : la même, au bruit près), le taux d'apprentissage descendant jusqu'au dernier pas.
- **L'écart entre l'entraînement et la validation grandit un peu** : de 0,145 à 10 % de l'entraînement
  à 0,226 à la fin (en nats). Les textes sont lus 3,5 fois : c'est sans doute le premier signe, léger, d'un
  apprentissage par cœur. Mais l'écart n'est pas nul avant la fin de la première lecture (pas 1 825), quand aucun texte n'a
  encore été relu : il est déjà de l'ordre de 0,1 à 0,17 entre les pas 300 et 1 800. Une partie de l'écart ne vient donc pas de
  la mémorisation (la validation porte sur d'autres documents, et sur 64 morceaux seulement). Avec plus de lectures, la part de
  mémorisation s'aggraverait ; c'est la raison de la règle des 4 lectures.

## 5. L'évaluation

`python -m forge evaluer` sur `etape-0006370.pt` (le dernier pas), en 26 s sur la carte, sur
1 024 morceaux fixes de 512 jetons de la validation (524 288 jetons jamais appris).

| Mesure | Valeur | Ce que cela veut dire |
| --- | --- | --- |
| Perte de validation | 3,428 nats par jeton | contre 10,397 pour le hasard |
| Perplexité | 30,8 | le modèle hésite comme s'il choisissait entre 31 jetons également probables, au lieu de 32 768 |
| Octets par jeton | 4,37 | taille moyenne d'un jeton dans ces données |
| Bits par octet (estimation) | 1,133 | la perte ramenée à un octet de texte |

La perte de l'évaluation (3,428) diffère un peu de la dernière valeur du journal (3,455) : ce ne sont pas
les mêmes morceaux (1 024 ici, 64 dans la boucle). L'évaluation, sur 16 fois plus de jetons, est la plus
fiable. Ces chiffres sont un point de repère pour les modèles plus grands qui suivent, mesurés de la même façon ;
ils ne se comparent pas à ceux de modèles publics : autres textes, autre tokenizer. Pour se faire une idée des bits par octet : 8 pour un texte
non compressé, environ 2,8 pour ces mêmes textes une fois compressés en gzip (353 Mo pour 1 000 Mo, JSON compris : un ordre
de grandeur), 1,13 pour ton IA.

### Les questions à choix multiples (FrenchBench)

Deux tests, toutes les questions de chacun : HellaSwag (finir une histoire, 4 fins possibles) et ARC-Challenge
(questions de sciences, de 3 à 5 réponses), des traductions automatiques en français. Le modèle « répond »
par le choix qui lui paraît le plus vraisemblable. Le verdict compare l'exactitude normalisée (corrigée de la
longueur des réponses) au hasard, avec la marge d'un résultat qui ne devrait qu'au hasard.

| Test | Questions | Exactitude | Exactitude normalisée | Hasard | Marge du hasard | Verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| HellaSwag (français) | 9 338 | 26,2 % | 27,2 % | 25,0 % | ± 0,9 point | au-dessus du hasard |
| ARC-Challenge (français) | 1 169 | 17,5 % | 23,6 % | 25,0 % | ± 2,5 points | pas différent du hasard |

- **HellaSwag** : 27,2 % contre 25,0 % au hasard, soit 2,2 points de plus, pour une
  marge de 0,9 point : le verdict est « au-dessus du hasard », mais c'est un écart minuscule. Sur 9 338 questions,
  cela fait environ 210 bonnes réponses de plus qu'un tirage au sort : un début de sens de
  la langue, pas de la compréhension.
- **ARC-Challenge** : 23,6 % contre 25,0 % : **pas différent du hasard**. L'exactitude brute (17,5 %) est
  même sous le hasard, sans doute parce que la somme des log-vraisemblances favorise les réponses courtes ;
  la version normalisée corrige cela et retombe dans la marge.
- **Mesure maison** : comparable aux modèles plus grands qui suivent et au hasard, pas aux scores publiés de FrenchBench
  (gabarit des questions, jeton de début et normalisation par octets sont les nôtres).

## 6. Les échantillons

Dix textes écrits par ton IA à partir de débuts fixes : température 0,8, top-k 50, 60 jetons au plus, graine 0
(puis 1, 2… pour les débuts suivants). Mêmes réglages, mêmes textes. **Ce sont les dix, sans tri.** Le début donné est
au début du bloc, la suite est celle du modèle (elle s'arrête au 60ᵉ jeton, parfois au milieu d'une phrase).

### 1. « Il était une fois »

```text
Il était une fois, un jour, il était tombé en état. Il avait été secoué et la tête bandée. À la tête de son fils, il venait d'être blessé par un torse. Il avait cru que c'était un assassinat dans la salle du lycée, avec un ami, et qu'il
```

### 2. « La capitale de la France est »

```text
La capitale de la France est la ville de la capitale, de ses habitants, de la région, de ses environs et de ses environs. Situé à quelques centaines de kilomètres du centre-ville de Bordeaux, ce centre de la région dispose d’un emplacement idéal pour les fêtes de fin d’année et d’une architecture nationale moderne. Sa
```

### 3. « Pour faire un bon gâteau au chocolat, il faut »

```text
Pour faire un bon gâteau au chocolat, il faut simplement la faire cuire au four et mettre au four au four, en remuant régulièrement, en fouettant légèrement et en remuant lentement. De plus, l’idéal est d’aller en poêle, avec un peu d’huile, un peu de crème fraiche à la cannelle. Il faut le laver
```

### 4. « Le soleil se couchait sur la mer et »

```text
Le soleil se couchait sur la mer et le soleil se couchait rapidement. Nous le voyons, il y avait de plus grands hommes qui se couchaient et ils l'attendaient et il les regardait. Il n'y voyait rien. Le soleil se couchait sur une table d'une main. La conversation avait alors duré très longtemps. On
```

### 5. « Aujourd'hui, le gouvernement a annoncé »

```text
Aujourd'hui, le gouvernement a annoncé la suppression du site du conseil d'administration de DIN, sans qu'on sache rien. Nous avons déjà parlé de la suppression du site pour l'instant, mais il y a toujours des problèmes puisque nous savons que le gouvernement a trouvé l'opportunité de supprimer ces sites Web.
Nous nous sommes donc mis d'
```

### 6. « Dans un petit village de Bretagne, »

```text
Dans un petit village de Bretagne, des milliers de personnes s’étaient tuées, samedi 22 janvier, dans une forêt sous la dalle des Trois-Files, aux côtés du chef d’une des deux familles de la forêt. À l’intérieur ils étaient venus prendre le temps de le voir, les deux derniers ayant été déportés,
```

### 7. « La photosynthèse est le processus par lequel »

```text
La photosynthèse est le processus par lequel l'on étudie la fonction de la fonction de l'individu et de la fonction de l'individu lui-même, qui permet d'agir, d'agir, de percevoir et d'agir, de modifier l'incontinence de la fonction de l'individu.
Pour la description d'une fonction, la question suivante est la
```

### 8. « Bonjour, je voudrais savoir comment »

```text
Bonjour, je voudrais savoir comment je peux obtenir une réponse. Je recherche un prestataire qui me permet de gérer ma page de commande. Je suis désolé que le site d'aide à la création de liens internet ne sera pas en mesure de gérer mes favoris mais en donnant mon nom sur mon mail. Merci, j'espère qu'il m'
```

### 9. « def factorielle(n): »

```python
def factorielle(n):
    return n * N
    return n

# --- General Public License
# --- General Public License --------------------------------------------------------------

def randomize():
    u = '0.0.0.0'
    u = os.path.join(u.rsurf(), '6.0.0
```

### 10. « def moyenne(valeurs): »

```python
def moyenne(valeurs):
    """Renvoie la moyenne aux autres membres de l'Association des agents permanents entre 1992 et 2001.
    Returns:
        A list of statistic groups available to a specific number of
                terms, to compare their number of declans.
        See: https://youtu.be/dc/q
```

Ce qu'on y voit :

- **De la langue, pas du savoir.** Les phrases sont souvent bien formées (accords, ponctuation, apostrophes) et ont
  le ton du genre demandé : récit, presse (« samedi 22 janvier », « le gouvernement a annoncé »), message de forum
  (« Bonjour, je voudrais savoir comment… »), recette (four, poêle, crème fraîche). Elles ne sont pas toujours
  correctes : « il était tombé en état », « la faire cuire » pour un gâteau, « Je suis désolé que le site… ne sera pas
  en mesure » (l'indicatif là où il faudrait le subjonctif).
- **Mais le fond est faux ou vide.** « La capitale de la France est la ville de la capitale » (pas de Paris) ;
  la recette dit « mettre au four au four » et finit par « Il faut le laver » ; la photosynthèse devient une boucle sur « la fonction de
  l'individu » ; les faits de presse sont inventés.
- **Elle perd le fil et se répète** : « le soleil se couchait » trois fois en quelques phrases, « au four au four »,
  « d'agir, d'agir ».
- **Le code a la forme du code et pas son sens.** Une fonction Python commence bien, avec l'indentation et un
  `return`, mais `factorielle` renvoie `n * N`, puis dérive vers une ligne de licence répétée et une fonction
  sans rapport (`randomize`, une adresse `0.0.0.0`) ; la docstring de `moyenne` mêle français et anglais
  (« Returns: ») et invente une adresse. L'anglais vient sans doute des commentaires et des docstrings du code
  Python du corpus.

## 7. Ce que ton IA sait faire, et ce qu'elle ne sait pas faire

Ce modèle a **23 millions de paramètres** et n'a lu que **835 millions de jetons pendant une heure**. Pour mettre
cela en perspective : les modèles de langage utilisés au quotidien ont des centaines ou des milliers de fois plus de
paramètres et ont lu des centaines ou des milliers de fois plus de texte. Ton IA « mini » n'est pas un assistant.

**Ce que cette version courte sait faire**

- Écrire des phrases françaises plausibles et souvent bien formées, avec la ponctuation usuelle, dans le style du web, de la presse ou d'un
  forum, et des morceaux de code Python qui ont l'allure de code.
- Prédire le jeton suivant (un morceau de mot) bien mieux qu'au hasard : une perplexité de 30,8 au lieu de 32 768.
- Prouver que **toute la chaîne fonctionne** : téléchargement, encodage en parallèle, entraînement d'une heure sans
  incident, sauvegardes, évaluation, rapport. C'est le but de cette tâche.

**Ce qu'elle ne sait pas faire**

- **Répondre à une question ou suivre une consigne.** Elle n'a appris qu'à prolonger du texte brut, jamais à dialoguer
  (aucun entraînement sur des conversations) : si tu lui poses une question, elle écrit la suite d'un texte qui
  commence par ta question, pas une réponse.
- **Dire des choses vraies.** Elle ne connaît pas les faits (la capitale de la France) ; ce qu'elle écrit est
  vraisemblable, pas vérifié.
- **Garder un fil.** Au bout de deux ou trois phrases, elle change de sujet ou se répète.
- **Écrire du code qui marche.** Ses fonctions ne calculent pas ce que leur nom annonce.
- **Réussir un QCM de culture ou de sciences.** HellaSwag : tout juste au-dessus du hasard ; ARC : au niveau du hasard.

Deux réserves sur ces mesures : la mesure d'échantillons est un tirage (10 textes, une graine), et les QCM
sont des traductions automatiques mesurées avec notre propre méthode. Ils servent à comparer entre eux les modèles de
la forge, pas à classer ton IA face à des modèles publics.

**Et après ?** Ces chiffres sont la base de comparaison de la suite : les mêmes mesures, refaites sur le grand
modèle et le grand corpus, diront ce que valent des heures d'entraînement de plus. Avec plus de paramètres et
bien plus de texte différent (et pas le même texte relu), l'écart avec cette version courte devrait se voir dans
la perte, dans HellaSwag et dans les échantillons.

## Où sont les fichiers, et la place prise

- **Dépôt :** `projets/forge/configs/mini.toml` (réglé) et ce document. Aucun poids ni aucune donnée dans git.
- **Hors dépôt**, sous `D:\forge-ia-donnees` : les jetons (`jetons\court`, 458,6 Mo, gardés), l'entraînement
  (`entrainements\ton-ia-mini` : journal, sauvegardes, rapport d'évaluation `evaluation\etape-0006370\rapport.md` et
  `rapport.json` ; 620,7 Mo en tout : 2 × 265,62 Mo de sauvegardes d'étape, 88,54 Mo pour `meilleur.pt`, 0,93 Mo de
  journal et 0,01 Mo de rapports) et les journaux d'écran (`journaux\`).
- **Textes bruts effacés** : `textes\court` (353 Mo), après avoir vérifié que `jetons\court\.complet` existait. Les
  jetons suffisent pour entraîner et évaluer ; pour les retrouver, relancer `python -m forge donnees --octets 1000M --dossier court` (même flux
  de textes, tant que les jeux de données de Hugging Face ne changent pas).
