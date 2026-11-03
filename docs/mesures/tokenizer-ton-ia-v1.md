# Le tokenizer de ton IA, version 1 (`ton-ia-v1`)

Mesuré et figé le 3 novembre 2026 (2026-11-03).

Ce document donne les mesures du tokenizer définitif de « ton IA » : sur quoi il a appris, en
combien de temps, et à quel point il compresse le français, Wikipédia et le code Python.
**Ce tokenizer est figé pour tout le reste du parcours** : on ne le réapprend plus et on ne le
modifie plus (voir la dernière section).

## En bref

- **Fichier :** `projets/forge/forge/ressources/tokenizer-ton-ia-v1.json` (546 692 octets, fins
  de ligne `\n`, rangé dans git).
- **Forme :** BPE sur les octets, 32 768 jetons en tout = 256 octets + 32 448 fusions
  (identifiants 256 à 32 703) + 64 jetons spéciaux (identifiants 32 704 à 32 767).
- **Appris sur :** 66 070 documents, 313 057 024 octets (298,6 Mo) de français du web, de
  Wikipédia en français et de code Python sous licence permissive, dans les parts 75 %, 10 % et 15 %.
- **Durée d'apprentissage :** 57,8 s sur un seul fil du processeur (59,3 s pour la commande entière,
  chargement des textes compris).
- **Compression sur la validation :** 4,51 octets par jeton sur le web, 4,39 sur Wikipédia,
  3,75 sur le code, et **4,36 pour le mélange** (75 % / 10 % / 15 %).

## L'échantillon d'apprentissage

Il vient de la commande `python -m forge donnees --octets 300M --dossier echantillon-tokenizer`,
qui suit le mélange par défaut. Dans ce projet, 1 Mo vaut 1 048 576 octets (comme dans
l'Explorateur de Windows). Le téléchargement a duré 51,7 s.

| Source | Téléchargé | Documents gardés | Documents de validation écartés | Appris sur (octets) | Appris sur (Mo) | Documents appris |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Français du web (`web_fr`, 75 %) | 225,0 Mo | 59 099 | 284 | 234 873 535 | 224,0 | 58 815 |
| Wikipédia en français (`wikipedia_fr`, 10 %) | 30,0 Mo | 1 321 | 6 | 31 268 392 | 29,8 | 1 315 |
| Code Python (`code_python`, 15 %) | 45,0 Mo | 5 978 | 38 | 46 915 097 | 44,7 | 5 940 |
| **Total** | **300,0 Mo** | **66 398** | **328** | **313 057 024** | **298,6** | **66 070** |

- Les 328 documents de validation (0,49 % des documents, 1 543 267 octets) sont **écartés de
  l'apprentissage** : un document est de validation quand `est_validation(empreinte)` est vrai,
  exactement comme à l'encodage. La compression mesurée plus bas sur la validation est donc
  honnête : le tokenizer n'a jamais vu ces textes.
- Le volume appris (298,6 Mo) est un peu sous les 300 Mo demandés pour cette raison : le
  dossier téléchargé contient 300 Mo, validation comprise.
- Le code Python vient de 153 225 fichiers lus dans le flux, dont seuls 5 978 sont gardés :
  du Python, sous une licence permissive (`mit`, `apache-2.0`, `bsd-2-clause`, `bsd-3-clause`,
  `isc`, `unlicense`, `cc0-1.0`), d'au moins 200 caractères et sans doublon.
- Au départ de l'apprentissage : 1 017 870 pré-mots distincts et 13 628 paires d'octets distinctes.

## L'apprentissage

| Étape | Durée |
| --- | ---: |
| Essai chronométré : 10 Mo, 2 000 fusions | 2,2 s (2,6 s pour la commande) |
| Estimation prudente pour 300 Mo et 32 448 fusions | environ 9 minutes |
| **Apprentissage réel, 300 Mo et 32 448 fusions** | **57,8 s** (59,3 s pour la commande) |
| Même apprentissage, relancé pour vérifier | 58,2 s (59,6 s pour la commande) |

- **Estimation :** l'essai a pris 1,2 s pour lire et pré-découper 10 Mo, puis environ 1 s pour
  2 000 fusions. Pour 300 Mo (30 fois plus de texte) et 32 448 fusions (16 fois plus), on compte
  sans aucune économie : 36 s de lecture, plus 1 s × 16 × 30 = 480 s de fusions, soit un peu moins
  de 9 minutes : assez court pour apprendre sur tout l'échantillon de 300 Mo, sans le réduire.
  En vrai, les dernières fusions sont très rapides (leurs paires sont rares) : la
  durée réelle est environ neuf fois plus courte.
- **Un seul fil, sur le processeur :** choisir chaque fusion dépend des précédentes, donc cette
  partie de l'apprentissage est séquentielle (seul le pré-découpage des textes pourrait se partager
  entre plusieurs fils). Comme tout dure une minute environ, on n'a cherché ni à l'accélérer ni à
  l'essayer sur la carte graphique.
- **Déterminisme :** deux apprentissages sur le même échantillon donnent un fichier identique octet
  pour octet. Empreinte SHA-256 des deux fichiers :
  `3001e7ab40630739c4dec807c7a92c0d4fb469cc0fc4afa368704395391f21ba`.

## La compression

On mesure les **octets par jeton** : les octets UTF-8 d'un texte divisés par le nombre de jetons
que donne `encoder` (sans le jeton `<|fin_texte|>` de chaque document). Plus le chiffre est grand,
mieux le tokenizer compresse : un texte tient dans moins de jetons.

La mesure est faite par la commande `python -m forge compression` (voir « Refaire la mesure »
plus bas). Les textes de validation viennent d'un téléchargement plus large que l'échantillon
(web 400 Mo, Wikipédia 350 Mo, code 300 Mo, obtenu avec `python -m forge donnees --parts`), car
0,5 % de l'échantillon ne suffit pas à fournir 1 Mo de Wikipédia ou de code (il n'y en a que
0,19 Mo et 0,26 Mo). C'est le même flux, avec le même nettoyage et le même dédoublonnage : le
début de ce téléchargement est identique, document pour document, à l'échantillon
d'apprentissage. La commande prend les documents de validation entiers, dans l'ordre du flux,
jusqu'à dépasser 1 Mo par source, et refuse de mesurer si une source en a moins.

| Texte de validation | Documents | Octets | Jetons | Octets par jeton | Caractères par jeton |
| --- | ---: | ---: | ---: | ---: | ---: |
| Français du web | 275 | 1 049 537 | 232 923 | **4,51** | 4,36 |
| Wikipédia en français | 63 | 1 056 581 | 240 488 | **4,39** | 4,25 |
| Code Python | 174 | 1 051 895 | 280 506 | **3,75** | 3,75 |
| **Mélange 75 % / 10 % / 15 %** | | | | **4,36** | |
| Les trois mis bout à bout | 512 | 3 158 013 | 753 917 | 4,19 | |

- **Le mélange** est le chiffre qui compte pour l'entraînement : c'est l'inverse de la moyenne des
  jetons par octet de chaque source, pondérée par les parts du mélange (en octets). Les trois
  textes « mis bout à bout » comptent chaque source à égalité (à peu près 1 Mo chacune) : le
  code, qui compresse moins, y pèse plus que dans l'entraînement.
- **Pas de signe de surapprentissage :** sur 1 Mo de documents d'apprentissage de chaque source
  (les premiers de l'échantillon), le tokenizer compresse à peine mieux : 4,53 (web), 4,44
  (Wikipédia), 3,84 (code), 4,41 pour le mélange. L'écart avec la validation est faible, de 0,03
  à 0,09 octet par jeton selon la source.
- Le français compresse à plus de 4 octets par jeton, soit environ 4,3 caractères par jeton.
  Le code en demande davantage (3,75) à cause de l'indentation, des symboles et des noms propres
  au code.

## Quelques exemples

Dans les découpages ci-dessous, `|` sépare les jetons, `␣` est une espace et `↵` un retour à la
ligne.

**Une phrase française** (45 octets, 12 jetons, 3,75 octets par jeton) :

```text
Le forgeron frappe le métal sur l’enclume.
Le|␣forger|on|␣frappe|␣le|␣métal|␣sur|␣l’|en|clu|me|.
```

**Une phrase avec des élisions** (77 octets, 20 jetons, 3,85 octets par jeton). L'apostrophe reste
collée au mot qui la précède (`l’`, `n’`, `d’`, `j’`), jamais au mot qui suit :

```text
L’enclume n’est pas l’outil d’aujourd’hui : j’y forge l’acier !
L’|en|clu|me|␣n’|est|␣pas|␣l’|outil|␣d’|aujourd’|hui|␣:|␣j’|y|␣for|ge|␣l’|acier|␣!
```

**Une fonction Python** (44 octets, 12 jetons, 3,67 octets par jeton) :

```text
def fusionner(mots, paire):
    return mots
def|␣fus|ionner|(m|ots|,|␣paire|):↵|␣␣␣|␣return|␣mots|↵
```

**Une fonction Python plus longue** (116 octets, 31 jetons, 3,74 octets par jeton). Les quatre
espaces de l'indentation tiennent en deux jetons (`␣␣␣` puis l'espace du mot suivant) :

```text
def fusionner(mots, paire):
    resultat = []
    for mot in mots:
        resultat.append(mot)
    return resultat
def|␣fus|ionner|(m|ots|,|␣paire|):↵|␣␣␣|␣result|at|␣=|␣[]↵|␣␣␣|␣for|␣mot|␣in|␣mots|:↵|␣␣␣␣␣␣␣|␣result|at|.append|(m|ot|)↵|␣␣␣|␣return|␣result|at|↵
```

Les toutes premières fusions apprises sont deux espaces (`␣␣`), puis `␣d`, `es`, `é`, `␣l` et `on` ;
la dernière (identifiant 32 703) donne `␣tarification`.

## Ce qui est figé

**Le tokenizer `ton-ia-v1` est figé pour tout le reste du parcours.** Un modèle entraîné avec lui
ne comprend plus rien si un seul identifiant de jeton change ; réapprendre le tokenizer, même sur
le même échantillon, obligerait à tout réencoder et à tout réentraîner.

- Le fichier `tokenizer-ton-ia-v1.json` est rangé dans git. Les tests de
  `projets/forge/tests/test_tokenizer_ton_ia.py` le gardent octet pour octet (empreinte SHA-256),
  ainsi que le motif de pré-découpage, les 64 jetons spéciaux (`<|fin_texte|>` = 32 705,
  `<|reserve_45|>` = 32 767), les premières et dernières fusions, des découpages exacts et la
  compression.
- `forge evaluer` l'utilise par défaut.
- Si un jour un autre tokenizer est vraiment nécessaire, il portera un autre nom (`ton-ia-v2`) et
  un autre fichier, à côté de celui-ci ; `ton-ia-v1` ne bouge pas.

## Refaire l'apprentissage, sans toucher au fichier figé

Les commandes se lancent depuis `projets/forge`, après `. .\outils\env-forge.ps1` à la racine du
dépôt. Le nouveau fichier s'écrit **hors du dépôt** : celui de `forge/ressources/` est figé et ne
doit jamais être écrasé.

```powershell
uv run --extra gpu python -m forge donnees --octets 300M --dossier echantillon-tokenizer
uv run --extra gpu python -m forge tokenizer --donnees echantillon-tokenizer `
    --taille 32768 --nom ton-ia-v1 --octets-max 300M --sortie "$env:FORGE_DONNEES\essai-tokenizer.json"
Get-FileHash -Algorithm SHA256 forge\ressources\tokenizer-ton-ia-v1.json, "$env:FORGE_DONNEES\essai-tokenizer.json"
```

Les deux empreintes doivent être identiques (`3001e7ab…21ba`). Si elles diffèrent, c'est que
Hugging Face ne sert plus exactement les mêmes textes dans le même ordre : on garde le fichier du
dépôt, qui reste la référence, et on jette l'essai.

## Refaire la mesure

La compression se mesure avec la commande `compression`, qui lit le tokenizer du dépôt par
défaut (`--tokenizer CHEMIN` pour en mesurer un autre). Il faut d'abord un téléchargement assez
gros pour contenir 1 Mo de validation par source : 400 Mo de web, 350 Mo de Wikipédia et 300 Mo
de code, soit environ 1 Go de texte (343 Mo sur le disque, compressé) et quelques minutes.

```powershell
uv run --extra gpu python -m forge donnees --parts web_fr=400M,wikipedia_fr=350M,code_python=300M `
    --dossier validation-tokenizer
uv run --extra gpu python -m forge compression --donnees validation-tokenizer
uv run --extra gpu python -m forge compression --donnees echantillon-tokenizer --partie apprentissage
```

La deuxième commande donne les tableaux de validation de ce document (documents, octets, jetons,
octets par jeton, caractères par jeton, mélange et « bout à bout »), la troisième la comparaison
sur des documents d'apprentissage. Le 3 novembre 2026, ces commandes lancées de zéro, avec un
téléchargement neuf dans un autre dossier, ont redonné exactement les mêmes chiffres. Si une source a moins de
validation que le volume demandé (`--octets`, 1 Mo par défaut), la commande s'arrête avec un
message qui dit combien elle en a trouvé, au lieu de mesurer sur moins de texte.
