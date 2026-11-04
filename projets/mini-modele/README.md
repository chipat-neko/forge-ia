# Le mini-modèle qui apprend (jumeau Python des démos)

Ce projet est le jumeau exact des démos du site : le mini-modèle qui apprend
à inventer des prénoms, et l'animation de l'attention. Le site les fait
tourner en TypeScript dans le navigateur (`site/src/lib/mini-modele/`). Ce
paquet Python (`mini_modele`) refait les mêmes calculs, avec les mêmes
opérations dans le même ordre, et les deux langages doivent trouver les mêmes
nombres, au bit près.

Il n'a pas de numéro de chapitre, comme `projets/forge` : il sert plusieurs
chapitres (l'avant-goût de 0.5, puis 1.5).

## Ce qu'il calcule

- **Le mini-modèle.** Un mini-transformer d'une couche, qui lit des prénoms
  caractère par caractère : un plongement par caractère et un par position
  (des positions apprises), une attention causale à 4 têtes de 4 (dimension
  16, contexte 16), un MLP de 64 avec ReLU, une norme RMS sans poids, des
  connexions résiduelles, et une tête de lecture séparée du plongement
  d'entrée. Avec les 39 caractères des prénoms et le bord `.`, le vocabulaire
  réel a **V = 40** numéros, et le modèle **4 608 paramètres** (32·V + 3 328).
  Il apprend à inventer des prénoms français, par 3 000 pas d'AdamW, avec la
  recette de ton IA (voir « Entraîner »).
- **L'exemple d'attention.** Les scores, le masque, les poids et les sorties
  de deux têtes sur une phrase de 9 mots, pour l'animation du site.
- **Pourquoi les mêmes bits.** La page du site fait ces calculs en TypeScript,
  sur des `Float64Array`, dans le navigateur de chaque lecteur : pas de GPU,
  pas de bibliothèque. Ce paquet les refait en Python pur, avec les mêmes
  opérations dans le même ordre, en n'employant que des opérations dont la
  norme IEEE 754 fixe le résultat (voir « Pourquoi on n'utilise ni
  `math.exp` ni `sum` »). Les nombres de la page sont donc exactement ceux que
  le Python écrit dans `tests/attendus-*.json`, et un test le vérifie dans
  Chrome, Firefox et WebKit.

## Tester

Il faut `uv` et Python 3.12 ou plus. Depuis le dossier `projets/mini-modele` :

```powershell
uv run pytest -q
```

Le test long, l'entraînement complet de 3 000 pas en Python pur (moins de
2 minutes sur un Ryzen 7 9800X3D), ne tourne qu'à la demande :

```powershell
uv run pytest -q -m lent
```

Côté site, depuis le dossier `site` (le même test long y tourne à chaque fois,
en 6 secondes environ) :

```powershell
npx vitest run src/lib/mini-modele
```

## Entraîner

Depuis `projets/mini-modele`, sur le processeur, en Python pur :

```powershell
uv run python -m mini_modele entrainer [--preset complet|avant-gout] [--pas N] [--taux X]
```

- `--preset` : `complet` (3 000 pas, dont 100 de montée du taux ; par défaut)
  ou `avant-gout` (600 pas, dont 50 de montée).
- `--pas N` : entraîner N pas au lieu de ceux du préréglage ; le taux monte et
  redescend sur ces N pas.
- `--taux X` : le taux maximal, 0,01 par défaut. Le site propose 0,001, 0,003,
  0,01, 0,03, 0,1 et 0,3. La virgule et le point sont acceptés.

La commande affiche l'erreur du lot tous les 50 pas et au dernier pas
(`pas 50 : erreur 2,562`), puis l'erreur de validation et 8 prénoms inventés,
marqués « existe déjà » quand ils sont dans la liste. Si l'erreur explose (taux
trop grand), elle s'arrête et le dit. Les nombres sont ceux de la démo du site,
au bit près.

La recette est celle de ton IA (`projets/forge`) : AdamW (0,9 ; 0,95), une
décroissance des poids de 0,1 sur tous les paramètres (ce sont tous des
matrices, comme celles que forge fait décroître), un écrêtage du gradient à 1,
et un taux qui monte en ligne droite puis redescend en cosinus jusqu'au
dixième du taux maximal. Le taux est le même code que
`forge/entrainement/planning.py`, avec notre `cos` ; un test l'y compare, en
lisant le fichier de forge sans l'importer. Le pas d'AdamW tient ses
corrections de biais par des produits successifs (`b1t = b1t × beta1`), sans
puissance. L'écrêtage, lui, diffère d'un rien : quand la norme du gradient
dépasse 1, on le divise par `norme` (le facteur est `écrêtage / norme`, donc
`1 / norme`), alors que `clip_grad_norm_` de PyTorch, qu'utilise forge, le
divise par `norme + 1e-6`. L'écart vaut au plus 10⁻⁶ en valeur relative, et
seulement aux pas où le gradient est écrêté.

**Résultat mesuré** (préréglage complet, taux 0,01, graine 1234), le même en
Python et en TypeScript : l'erreur de validation (256 prénoms) passe de
3,653 au départ (ln 40 = 3,689 pour le pur hasard) à **2,158 au pas 3 000**.
Le seuil des tests est 2,45, avec une baisse d'au moins 1,0 : le taux 0,01
suffit, aucun repli (0,03, 0,003 ou 4 000 pas) n'a servi.

La commande complète prend environ 2 minutes sur un Ryzen 7 9800X3D (un seul
cœur : le calcul est une suite de pas, qui ne se partage pas). Elle affiche,
au début et à la fin :

```text
Mini-modèle : 4 608 paramètres, 40 caractères, 4 752 prénoms d'entraînement.
Réglages : préréglage complet, 3 000 pas, taux maximal 0,01.
Erreur de validation au départ : 3,653
pas 50 : erreur 2,562
…
pas 3000 : erreur 2,122
Erreur de validation au pas 3000 : 2,158
Prénoms inventés : fated, carissa, ney, rajaste, marfahy, lerbana, alicise, maora
Durée : 119,6 s
```

## Les attendus partagés

Le Python écrit des fichiers de référence, `tests/attendus-<nom>.json`. Chaque
nombre à virgule y est écrit en 16 chiffres hexadécimaux : ce sont ses 8
octets, du plus fort au plus faible (`3ff0000000000000` pour 1,0). Vitest
relit ces fichiers et compare les motifs du TypeScript à ceux du Python : un
seul bit de différence fait échouer le test. Pour les régénérer, depuis
`projets/mini-modele` :

```powershell
uv run python -m mini_modele.attendus
```

Un test vérifie que les fichiers sont à jour : si le code change, il échoue
tant qu'ils ne sont pas régénérés.

`tests/attendus-modele.json` a deux clés. `modele` : les paramètres de départ,
la perte et tout le gradient d'un lot, la validation et des prénoms inventés.
`entrainement` : 20 pas du préréglage complet (la perte et le taux de chaque
pas, l'empreinte de tous les paramètres au pas 20, la validation et les
prénoms au départ et au pas 20), le taux à quelques pas de la montée, du
cosinus et de la fin, un entraînement qui diverge (taux 1 000), et les
préréglages eux-mêmes. Sa clé `court` ajoute 10 pas sur vingt prénoms de deux
lettres, par lots de 4 et avec un écrêtage à 100 : l'ordre des prénoms y est
remélangé (aux pas 5 et 9) et le gradient n'y est jamais écrêté, deux chemins
que les 20 pas du préréglage complet ne prennent pas. Le résultat des 3 000
pas, trop long à refaire à chaque régénération, n'est pas dans ces fichiers :
ses motifs sont écrits en dur dans les deux tests longs, `LONG_VALIDATION_DEPART`,
`LONG_VALIDATION_FIN` et `LONG_PARAMS_EMPREINTE` (l'empreinte de tous les
paramètres au pas 3 000) en tête de `tests/test_entrainement.py`, et
`VALIDATION_DEPART`, `VALIDATION_FIN` et `PARAMS_EMPREINTE` en tête de
`site/src/lib/mini-modele/entrainement-long.test.ts`. Si le code change,
relance `uv run pytest -q -m lent` : il affiche les nouveaux motifs (l'option
`-s` montre les lignes « motifs : … »). Recopie-les dans les deux fichiers, puis
relance `npx vitest run src/lib/mini-modele/entrainement-long.test.ts` pour voir
que le TypeScript trouve les mêmes.

`tests/attendus-attention.json` : tout le détail de l'exemple d'attention (voir
plus bas), tête par tête. Les scores des cases masquées y sont `null`, et leurs
poids valent `+0,0`. Sa clé `flottant` ajoute un petit exemple à virgule (des
entrées comme 0,1 ou 0,3, une tête de 3), qui fixe l'ordre des sommes. Dans la
phrase, les entrées sont des entiers : les projections et les scores sont des
sommes d'entiers, exactes dans n'importe quel ordre, et ne disent rien de
l'ordre des opérations. Le mélange, lui, additionne des valeurs fois les poids
du softmax, qui ne sont pas exacts : il dépend de l'ordre en général. Dans
l'exemple à virgule, additionner la projection, le score ou le mélange dans un
autre ordre change des bits (`test_l_exemple_flottant_voit_l_ordre_des_sommes`).

Ces quatre fichiers sont aussi refaits dans le navigateur, par la page d'essai
de parité du site (`site/src/lib/mini-modele/parite.ts`, parcours
`site/e2e/parite.spec.ts`) : dans Chrome, et en intégration continue dans
Firefox et WebKit.

## L'exemple d'attention

L'animation de l'attention du site montre deux têtes sur la phrase « Le
forgeron chauffe le fer puis il le tord ». Seuls les vecteurs des mots et les
matrices sont écrits à la main, dans `donnees/exemple-attention.json` :

- chaque mot porte 8 traits, des 0 et des 1 (déterminant, nom, verbe, pronom,
  sujet, objet, personne, chose) ;
- chaque tête a trois matrices de 8 lignes (une par trait) et 4 colonnes,
  d'entiers de −5 à 5 : `wq` pour les requêtes, `wk` pour les clés, `wv` pour
  les valeurs ;
- la tête « qui agit » : un verbe cherche son sujet. La tête « de qui on
  parle » : un pronom cherche le nom qu'il remplace.

Tout le reste (les scores, le masque, les poids et les sorties) est calculé
par `mini_modele/exemple_attention.py`, avec les fonctions d'attention du
mini-modèle (`scores_attention`, `softmax`, `melanger_valeurs`). Les tests
(`tests/test_exemple_attention.py`) vérifient sur ces poids calculés que
l'exemple dit vrai : « chauffe » regarde « forgeron », « tord » regarde ses
deux sujets, « il » regarde « forgeron » plus que « fer », le nom le plus
proche, et le second « le » regarde « fer ». Si tu changes une matrice,
relance `uv run python -m mini_modele.attendus`, puis les tests des deux
langages : les paris du site (`site/src/lib/mini-modele/paris-attention.ts`)
arrêtent la construction si leur réponse n'est plus vraie.

## Pourquoi on n'utilise ni `math.exp` ni `sum`

Pour trouver les mêmes bits partout, il faut des opérations dont le résultat
est fixé par la norme IEEE 754, sur toutes les machines et dans tous les
navigateurs.

- `math.exp`, `math.log` et `math.cos` appellent la bibliothèque mathématique
  de la machine. En JavaScript, `Math.exp` et ses voisines sont « approchées
  selon l'implémentation » : Chrome, Firefox et Safari ne donnent pas toujours
  le même dernier bit. Le paquet écrit donc ses propres `exp`, `log` et `cos`
  (dans `mini_modele/calcul.py`) avec seulement des + − × ÷.
- `sum()` fait une somme compensée depuis Python 3.12 : plus précise, mais
  différente d'une simple boucle. Toute somme est donc une boucle `s += v`,
  dans l'ordre des indices.
- `max()` et `Math.max` traitent −0 différemment : un maximum est une boucle
  `if v > m`. Les fonctions intégrées `pow`, `max`, `min`, `round` et
  `divmod` sont refusées dans les fichiers vérifiés. Une puissance devient une
  boucle de produits (`p = p * b` à chaque pas), et un arrondi un
  `math.floor(x + 0.5)` écrit de la même façon des deux côtés.
- Les divisions entières suivent une règle qu'aucun test ne peut vérifier
  (le signe d'une variable ne se lit pas dans le code) : les indices sont
  toujours positifs, et `%` et `//` ne servent que sur des entiers positifs.
  Là, les deux langages donnent le même résultat : `a % b` des deux côtés, et
  `a // b` en Python face à `Math.floor(a / b)` en TypeScript. Sur un nombre
  négatif ou à virgule, le `%` de Python prend le signe du diviseur et celui
  de JavaScript le signe du dividende ; on écrit alors `floor` explicitement,
  des deux côtés : `math.floor(a / b)`, et `a - b * math.floor(a / b)`.
- Le hasard vient de `Hasard` (SplitMix32), jamais de `random` : Python ne
  garantit pas ses tirages d'une version à l'autre.

Les fichiers vérifiés sont `calcul.py`, `donnees.py`, `attention.py`,
`modele.py`, `entrainement.py` et `exemple_attention.py`. On n'y permet que
les + − × ÷, `math.sqrt` (arrondi correct, partout), `math.floor` et les
opérations entières. S'y ajoutent `math.ldexp` et `math.frexp`, permis parce
qu'ils sont exacts : ils ne changent que l'exposant, sans arrondi (ils servent
`exp` et `log`). Les autres noms de `math` permis ne calculent rien : `inf`,
`nan`, `isnan`, `isinf` et `isfinite`. En TypeScript, les seuls `Math.` permis
sont `Math.sqrt`, `Math.floor` et `Math.imul` (le produit entier sur 32 bits,
exact, pour SplitMix32 et l'empreinte). Le test `tests/test_sources.py` cherche
les fonctions interdites dans ces fichiers, commentaires compris, et refuse tout
autre nom de `math` ; `site/src/lib/mini-modele/sources.test.ts` fait de même
pour le TypeScript.

## Les régions balisées (pour les plans 4 et 5)

Les chapitres montrent du vrai code de ce paquet, jamais recopié : des
commentaires `# region: nom` et `# fin: nom`, chacun seul sur sa ligne,
encadrent les extraits. La fonction `extraireRegion(source, nom, fichier)`
(`site/src/lib/regions.ts`) rend les lignes entre les deux marqueurs, sans les
marqueurs et sans l'indentation commune ; elle arrête la construction si la
région manque. Dix régions sont posées :

| Région | Fichier | Ce qu'elle contient |
| --- | --- | --- |
| `exp` | `calcul.py` | `exp(x)` avec seulement des + − × ÷. Hors de la région, définis en tête de `calcul.py` et nécessaires à `exp` : `LN2_HAUT`, `LN2_BAS`, `INV_LN2`, la liste `C_EXP` (1/n!, de 0 à 13) et la fonction `deux_puissance` |
| `log` | `calcul.py` | `log(x)`, de la même façon. Hors de la région et nécessaires à `log` : `LN2_HAUT`, `LN2_BAS`, `SQRT_DEMI` et la liste `C_LOG` (1/(2n + 1), de 0 à 11) |
| `scores` | `attention.py` | `scores_attention` : requête · clé, fois l'échelle |
| `softmax` | `attention.py` | `softmax` : des scores aux poids |
| `melange` | `attention.py` | `melanger_valeurs` : les valeurs, mélangées selon les poids |
| `avant` | `modele.py` | `avant` : la passe avant, position par position |
| `perte` | `modele.py` | `entropie_croisee` : l'erreur à une position |
| `lot` | `entrainement.py` | `_prochain_lot` : les prénoms du prochain lot, dans l'ordre mélangé |
| `ecretage` | `entrainement.py` | l'écrêtage du gradient, dans `faire_un_pas` |
| `adamw` | `entrainement.py` | le pas d'AdamW, dans `faire_un_pas` |

`tests/test_sources.py` vérifie que chaque marqueur est seul sur sa ligne et
que chaque région est fermée ; `site/src/lib/mini-modele/sources.test.ts`
extrait les dix et vérifie leur début et leur fin. Si tu déplaces un marqueur,
ce test te dit quelle région a changé. Le TypeScript n'a pas de marqueurs : il
cite la région du Python qu'il traduit dans son commentaire de documentation.

## Les données

Le mini-modèle apprend à inventer des prénoms français. La liste vient du
« Fichier des prénoms » de l'Insee. Elle est versionnée dans
`donnees/prenoms.txt` (38 851 octets, 5 279 prénoms, un par ligne, en
minuscules) : le site est statique, et il ne doit pas dépendre de l'Insee à
chaque construction. C'est une dérogation voulue à la règle « les données ne
sont jamais versionnées », choisie par l'utilisateur le 03/11/2026.

- **Source :** Insee, « Fichier des prénoms », <https://www.insee.fr/fr/statistiques/8595130>.
  Édition parue le 16/07/2026 : les naissances en France de 1900 à 2025, fichier
  national `prenoms-2025-nat_csv.zip` (4 348 158 octets, SHA-256
  `4c3662bbc75a021a2203b9bed0beff7e85c7928779b88602814ed407cfee512e`),
  téléchargé le 03/11/2026. Les effectifs de l'Insee sont arrondis à 5 près.
- **Licence :** Licence Ouverte 2.0 (Etalab), qui est celle des informations
  publiques de l'Insee (<https://www.insee.fr/fr/information/2008466>), avec la
  mention **« Source : Insee »** et la date de mise à jour des données
  (16/07/2026). La licence demande aussi de ne pas déformer le sens des
  informations : `prenoms.txt` n'est pas une copie du fichier de l'Insee, c'est
  une sélection de prénoms, sans aucun effectif, écrite en minuscules.
- **Le format réel du fichier** (relevé le 03/11/2026) : encodage UTF-8 sans
  marque d'ordre, fins de ligne Windows, séparateur `;`, et l'en-tête
  `sexe;prenom;periode;valeur;rang`. Il diffère de ce que le plan attendait
  (`SEXE`, `PRENOM`, `PERIODE`, `VALEUR` en majuscules) sur deux points : les noms
  des colonnes sont en minuscules, et une colonne `rang` s'ajoute. `lire_lignes`
  (`mini_modele/prenoms.py`) vérifie l'en-tête, compare les noms sans tenir compte
  de la casse, ignore les colonnes en plus (et leur ordre), et s'arrête avec un
  message qui dit quoi faire si le séparateur ou un nom a changé. Dans cette
  édition, les 724 645 lignes ont toutes une période de 4 chiffres, de 1900 à 2025,
  et aucun prénom ne commence par `_` (le plan attendait des lignes
  `_PRENOMS_RARES` à la période `XXXX`, comme dans l'ancien format du fichier) :
  `extraire` ignore quand même ces deux cas, au cas où une autre édition en aurait.
- **La recette :**
  - On additionne les naissances de chaque prénom sur toutes les années et les deux
    sexes, après avoir mis le prénom en minuscules et en NFC.
  - On garde les prénoms qui ont au moins **500 naissances** depuis 1900, de 2 à 15
    caractères, avec seulement les lettres `abcdefghijklmnopqrstuvwxyz`, les
    accents `àâäæçèéêëîïôöùûüÿœ` et le trait d'union (jamais au début, à la fin ni
    doublé).
  - On trie par point de code. Le fichier finit par un seul `\n`.
- **Le résultat :** le seuil de 500 laisse **5 279 prénoms**, plus que le minimum
  de 5 000 : le repli à un seuil de 200 n'a pas servi. Huit prénoms de 500
  naissances ou plus sont écartés : `m'hamed` (une apostrophe) et sept prénoms
  composés de plus de 15 caractères.
  - Les caractères utilisés sont `-abcdefghijklmnopqrstuvwxyzàâçèéëîïôöûü`
    (39 caractères), donc le vocabulaire a **V = 40** numéros avec le bord.
  - Le mini-modèle a 32·V + 3 328 paramètres : **4 608 pour V = 40** (et non les
    « environ 4 700 » du plan). Les chapitres calculent ce nombre avec
    `nombre_parametres`, et ne le recopient pas.
  - L'empreinte du fichier (`empreinte_texte`, FNV-1a 32 bits sur ses octets
    UTF-8) est `da271fd0`.
- **Refaire la liste :** depuis `projets/mini-modele`, avec une connexion à
  Internet (le téléchargement est de 4 Mo) :

  ```powershell
  uv run python -m mini_modele.prenoms
  uv run python -m mini_modele.attendus
  uv run pytest -q
  ```

  Le script affiche le nombre de prénoms, les caractères utilisés, l'empreinte
  du fichier et celle de l'archive. Il ne touche pas à `prenoms.txt` si l'en-tête
  a changé. Si une nouvelle édition change la liste, les attendus
  (`tests/attendus-donnees.json`) changent avec elle, et il faut aussi revoir les
  chapitres qui citent ces nombres.
- **Le partage entraînement/validation** (`mini_modele/donnees.py`, jumeau de
  `site/src/lib/mini-modele/donnees.ts`) : la liste est copiée, puis mélangée par
  `Hasard(20261103)`. Les `len // 10` premiers prénoms vont en validation (527),
  le reste en entraînement (4 752). Le numéro 0 est le bord, `.`, au début et à la
  fin de chaque prénom ; les autres caractères sont numérotés dans l'ordre des
  points de code. Le Python lit le fichier en octets (et non avec `read_text`, qui
  range `\r\n` en `\n`), pour voir exactement la liste que le site lit avec
  `?raw`.

## Le calculateur de coût, à côté

Le calculateur de la page d'essai (`site/src/lib/calculateur/`) n'est pas un
jumeau Python : ses nombres viennent de formules écrites une fois, en
TypeScript, et chaque étape de « Voir le calcul » se refait à la main à partir
des nombres affichés (un test le vérifie). Il refait trois choses de
`projets/forge`, sans l'importer : `largeur_cachee`, `nombre_parametres` et
`estimer`, et un test de Vitest lit leurs constantes dans le code de forge.
Deux précisions utiles quand on lit son relevé :

- le cache KV de la génération couvre **min(contexte, 4 096) jetons** : tout le
  contexte du modèle s'il est plus court que 4 096, 4 096 sinon
  (`JETONS_DU_CACHE`, dans `site/src/lib/calculateur/releve.ts`) ;
- dans les étapes « au moins N cartes », le total est écrit en Go (« 6 570 Go ÷
  16 Go = au moins 411 cartes »), jamais en To : « 6,4 To ÷ 16 Go » ferait
  trouver 410 cartes à qui refait la division. Quand l'arrondi ordinaire ferait
  quand même trouver une carte de moins, le total est arrondi vers le haut : il
  dépasse alors d'une unité de son dernier chiffre (0,1 Go sous 100 Go, 1 Go
  au-delà) le total lu ailleurs, et l'explication de « Voir le calcul » le dit.
