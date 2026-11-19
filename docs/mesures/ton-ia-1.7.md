# Ton IA 1.7 : apprendre à converser

Ton IA 1.7 est le premier vrai affinage de ton IA : un affinage supervisé (SFT) de la version publiée
`ton-ia-1.5` sur des conversations en français. Ce document raconte ses données, l'essai chronométré, le
balayage du taux d'apprentissage, un premier entraînement complet au taux 3e-4 (18 novembre 2026),
l'oubli qu'il a fait mesurer, la décision qui a suivi, puis l'entraînement complet au taux 1e-4 (19
novembre) : c'est lui, la version publiée `ton-ia-1.7`. Puis son évaluation, et ce qu'elle sait faire ou
non.

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
- **Le taux d'apprentissage : 1e-4.** Le balayage (quatre essais de 300 pas) avait retenu 3e-4, celui
  dont la perte de conversation finissait la plus basse. Entraînée en entier à 3e-4, ton IA prédit
  nettement moins bien le texte de son pré-entraînement : sa perte y monte de 2,347 (1.5) à 3,766. Une
  version courte à 1e-4 oubliant moins (2,615 contre 2,998), l'entraînement complet a été refait à 1e-4,
  et c'est lui qui est publié.
- **L'entraînement publié :** 3 338 pas (deux époques), le 19 novembre 2026, en une session : 4 h 52 min
  20 s de Python, dont 4 h 44 min 51 s de calcul. La perte de validation baisse à chaque mesure, de 1,422
  (pas 100) à **0,988** (pas 3 338). La pause et la reprise réelles ont été faites sur l'entraînement à
  3e-4.
- **L'évaluation**, de 1.5 à 1.7 (complète à 3e-4 entre parenthèses) :
  - réponses terminées : 0,0 % → **51,0 %** (52,8 %) ;
  - réponses en français : 87,2 % → 99,4 % (98,8 %) ;
  - IFEval-FR, invites respectées : 21,7 % → 14,5 % (16,2 %) : **moins bien que 1.5** ; l'écart
    entre 1e-4 et 3e-4 ne se confirme pas au second passage (15,3 % et 15,7 %) ;
  - perte sur le texte du pré-entraînement : 2,347 → 2,928 nats par jeton (3,766) : **elle prédit moins
    bien que 1.5 le texte libre, mais bien mieux qu'à 3e-4** ;
  - problèmes justes : générés 0 → 1 sur 400 (3), MGSM 0 → 0 sur 250 (1),
    GSM8K-Platinum 0 → 10 sur 1 196 (4).

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

Ce choix, fait sur la seule perte de conversation, a été revu après l'évaluation de l'entraînement
complet : la version publiée est entraînée au taux 1e-4 (sections 4 à 6).

**Les durées.** Chaque essai a fait ses 300 pas en 1 486 à 1 504 s de calcul : 4,88 s par pas en
médiane, plus environ 10 s à chaque validation, écriture de `meilleur.pt` (1,62 Gio) comprise. Avec le
chargement de ton-ia-1.5 et la sauvegarde finale (4,85 Gio), la commande entière a pris de 25 min 47 s à
25 min 56 s : moins de 30 minutes, comme prévu. Débit médian de 13 371 à 13 426 jetons par seconde ;
carte occupée à 93 % en moyenne, 12,9 à 13,0 Go au plus. Les tests de forge tournaient sur le processeur
pendant les huit premières minutes du deuxième essai : 13 359 jetons par seconde sur ses 20 pas d'alors,
0,6 % sous le premier essai.

## 4. L'entraînement complet au taux 3e-4

Le 18 novembre 2026, avec le taux retenu par le balayage : `configs/sft-1.7.toml` à `taux_max = 3e-4`,
gardé depuis sous le nom `configs/sft-1.7-3e-4.toml` (sortie `entrainements\sft-1.7-3e-4`, journal de la
fenêtre `journaux\sft-1.7-3e-4.log`). Lancé par `travail-long.ps1`, avec le chien de garde. C'est sur cet
entraînement que la pause et la reprise ont été faites pour de vrai, deux fois :

| Session | Démarrage | Premier pas prêt | Fin | Pas | Durée de Python | Fin de la session |
| --- | --- | --- | --- | --- | ---: | --- |
| 1 | 02:34:41 | 02:34:58 | 03:07:02 | 1 à 372 | 32 min 17 s | pause d'essai (Ctrl+C à 03:06:32, pause notée 22 s plus tard) |
| 2 | 03:07:26 | 03:14:49 | 04:11:30 | 373 à 1 027 | 1 h 04 min 02 s | pause pour le jeu de l'utilisateur (Ctrl+C à 04:11:08) |
| 3 | 05:29:37 | 05:31:10 | 08:48:39 | 1 028 à 3 338 | 3 h 18 min 58 s | fin |

- **Calcul :** 17 075 s, soit 4 h 44 min 35 s ; Python a tourné 4 h 55 min 17 s, chargements et
  sauvegardes compris.
- **La courbe continue sans saut** à chaque pause : perte moyenne 1,265 sur les 20 pas avant le pas 372,
  1,271 sur les 20 pas après ; 1,128 avant le pas 1 027, 1,132 après. Le taux reprend où
  il était (2,937e-4 au pas 372, 2,936e-4 au pas 373).
- **La fin :** perte 0,708 au pas 3 338, validation 0,941 (la plus basse, `meilleur.pt`).

La version courte à 3e-4 (`configs/sft-1.7-court-3e-4.toml`, sortie
`entrainements\ton-ia-1.7-court-3e-4`) a suivi d'une traite : 739 pas, 1 h 04 min 37 s de Python,
validation 1,095 au pas 739.

## 5. L'oubli mesuré, et la décision

Exportées et évaluées le 19 novembre au matin (section 7), les deux versions à 3e-4 répondent : elles
finissent 52,8 % et 54,0 % de leurs réponses, contre 0 % pour 1.5. Mais la complète
prédit nettement moins bien le texte du pré-entraînement : sa perte sur ce texte monte de 2,347 (1.5) à
3,766 nats par jeton, soit de 0,779 à 1,250 bit par octet. La courte à 3e-4 monte à 2,998.

Le balayage avait choisi le taux sur la seule perte de conversation, et le meilleur taux pour elle est
celui qui fait le plus oublier. Le contrôleur a jugé qu'un tel oubli gênerait les chapitres suivants (le
code de 1.10, l'alignement de 1.8). Sa décision, le 19 novembre :

1. ne pas publier la version à 3e-4 ;
2. lancer d'abord une version courte au taux 1e-4 (une heure), exportée et évaluée comme les autres ;
3. si elle oublie nettement moins (perte sur le texte du pré-entraînement bien sous 2,998), avec des
   parts de réponses terminées et en français proches, refaire l'entraînement complet à 1e-4 et publier
   celui-là ; sinon, publier celui à 3e-4.

La courte à 1e-4 : perte sur le texte du pré-entraînement 2,615 (contre 2,998 à 3e-4), réponses
terminées 47,5 % (54,0 %), en français 99,1 % (99,7 %), IFEval-FR 14,9 %
(15,7 %). Le critère est rempli : l'entraînement complet est refait au taux 1e-4, et c'est
lui qui est publié sous le nom `ton-ia-1.7`. Les versions à 3e-4 restent sur le disque, pour comparer ;
elles ne sont pas publiées.

Les réglages destinés aux lecteurs gardent leurs noms : `configs/sft-1.7.toml` et
`configs/sft-1.7-court.toml` sont à 1e-4, les originaux à 3e-4 sont gardés sous
`configs/sft-1.7-3e-4.toml` et `configs/sft-1.7-court-3e-4.toml`.

## 6. L'entraînement complet au taux 1e-4 : la version publiée

Le 19 novembre 2026, `configs/sft-1.7.toml` (`taux_max = 1e-4`, le reste inchangé), sortie
`entrainements\sft-1.7`, journal de la fenêtre `journaux\sft-1.7.log`. Lancé par `travail-long.ps1`, avec
le chien de garde, en une seule session, sans pause : la pause et la reprise ont été essayées sur
l'entraînement à 3e-4 (section 4), avec le même code.

- **Démarrage :** 10:11:46 ; premier pas à 10:18:36. Les 6 min 45 s de chargement viennent du disque D:,
  occupé à ce moment par un autre travail.
- **Fin :** pas 3 338 à 15:04:05, code 0. **4 h 52 min 20 s** de Python, dont 17 091 s de calcul (4 h 44
  min 51 s). Débit médian 13 379 jetons par seconde ; 9 sauvegardes d'étape, une toutes les 30 minutes
  environ, plus celle de la fin.
- **La courbe :** perte 2,208 au pas 1, 0,798 au pas 3 338. La perte de validation baisse à chaque
  mesure, de 1,422 (pas 100) à **0,988** (pas 3 338, la plus basse : `meilleur.pt` est ce pas).

| Pas | Perte d'entraînement (moyenne) | Validation au dernier pas | Validation à 3e-4, même pas |
| --- | ---: | ---: | ---: |
| 1 à 200 | 1,498 | 1,322 | 1,331 |
| 201 à 400 | 1,272 | 1,234 | 1,247 |
| 401 à 600 | 1,205 | 1,180 | 1,194 |
| 601 à 800 | 1,166 | 1,140 | 1,153 |
| 801 à 1 000 | 1,134 | 1,112 | 1,118 |
| 1 001 à 1 200 | 1,115 | 1,086 | 1,089 |
| 1 201 à 1 400 | 1,092 | 1,068 | 1,066 |
| 1 401 à 1 600 | 1,070 | 1,048 | 1,036 |
| 1 601 à 1 800 | 0,987 | 1,039 | 1,023 |
| 1 801 à 2 000 | 0,936 | 1,029 | 1,009 |
| 2 001 à 2 200 | 0,929 | 1,019 | 0,993 |
| 2 201 à 2 400 | 0,929 | 1,010 | 0,979 |
| 2 401 à 2 600 | 0,911 | 1,004 | 0,966 |
| 2 601 à 2 800 | 0,917 | 0,997 | 0,956 |
| 2 801 à 3 000 | 0,909 | 0,993 | 0,949 |
| 3 001 à 3 200 | 0,903 | 0,990 | 0,943 |
| 3 201 à 3 338 | 0,908 | 0,988 | 0,941 |

Jusqu'au pas 1 300, la validation à 1e-4 est à peine plus basse qu'à 3e-4 (1,075 contre 1,076 au pas
1 300) ; à partir du pas 1 400, elle est au-dessus, et finit 0,047 plus haut (0,988 contre 0,941) : le
taux plus petit apprend un peu moins les conversations. La deuxième époque commence au pas 1 669 (53 401
rangées ÷ 32 par pas) : la perte d'entraînement baisse de 1,070 (pas 1 401 à 1 600) à 0,936 (pas 1 801 à
2 000), la validation de 1,048 à 1,029 : ton IA relit les mêmes conversations, et la perte d'entraînement
baisse bien plus que la validation.

### La version courte à 1e-4

`configs/sft-1.7-court.toml` (sortie `entrainements\ton-ia-1.7-court`, journal
`journaux\ton-ia-1.7-court.log`), le 19 novembre de 08:40:56 à 09:45:06, d'une traite : **1 h 04 min 05
s** de Python, dont 3 778 s de calcul. Perte 1,121 au pas 739, validation **1,160** (la plus basse).

| Pas | Perte d'entraînement (moyenne) | Validation | Validation à 3e-4, même pas |
| --- | ---: | ---: | ---: |
| 1 à 100 | 1,634 | 1,422 | 1,423 |
| 101 à 200 | 1,362 | 1,320 | 1,323 |
| 201 à 300 | 1,289 | 1,264 | 1,258 |
| 301 à 400 | 1,245 | 1,224 | 1,204 |
| 401 à 500 | 1,217 | 1,193 | 1,156 |
| 501 à 600 | 1,177 | 1,173 | 1,121 |
| 601 à 700 | 1,175 | 1,162 | 1,099 |
| 701 à 739 | 1,160 | 1,160 | 1,095 |

## 7. L'évaluation : 1.5, 1.7 et ses variantes côte à côte

Chaque version est exportée par `forge exporter` (son `meilleur.pt`) dans `publications\`, puis mesurée
sur la carte par `forge evaluer-etape`, en glouton. `ton-ia-1.5` (téléchargée) passe les mêmes mesures en
référence, avec la version publiée : sa colonne vient de `evaluations\ton-ia-1.7-1.7` et
`ton-ia-1.7-1.9`.

| Version | Taux | Poids | Rapports |
| --- | --- | --- | --- |
| `ton-ia-1.7` (publiée) | 1e-4 | `publications\ton-ia-1.7` | `evaluations\ton-ia-1.7-1.7`, `ton-ia-1.7-1.9` |
| courte | 1e-4 | `publications\ton-ia-1.7-court` | `evaluations\ton-ia-1.7-court-1.7`, `-1.9` |
| complète à 3e-4 | 3e-4 | `publications\ton-ia-1.7-3e-4` | `evaluations\ton-ia-1.7-3e-4-1.7`, `-1.9` |
| courte à 3e-4 | 3e-4 | `publications\ton-ia-1.7-court-3e-4` | `evaluations\ton-ia-1.7-court-3e-4-1.7`, `-1.9` |

Les dossiers des trois autres versions ont été renommés après leur évaluation. Leurs `rapport.json` sont
une archive : ils gardent le nom qu'avait la version au moment de la mesure (`ton-ia-1.7` pour la
complète à 3e-4, `ton-ia-1.7-court` pour la courte à 3e-4, `ton-ia-1.7-court-1e-4` pour la courte à
1e-4). Leur empreinte SHA-256 dit de quels poids il s'agit (section 10).

**Les mesures de l'étape 1.7 :**

| Mesure | `ton-ia-1.5` | **`ton-ia-1.7`** (1e-4) | courte (1e-4) | complète à 3e-4 | courte à 3e-4 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Perte sur les conversations de validation (nats par jeton appris, 64 ex.) | 2,300 | 0,978 | 1,140 | 0,936 | 1,080 |
| IFEval-FR, invites dont toutes les consignes sont respectées (235) | 21,7 % | 14,5 % | 14,9 % | 16,2 % | 15,7 % |
| IFEval-FR, consignes respectées | 31,9 % | 24,1 % | 24,1 % | 26,4 % | 26,4 % |
| Réponses terminées par `<|fin_tour|>` (335) | 0,0 % | 51,0 % | 47,5 % | 52,8 % | 54,0 % |
| Réponses en français | 87,2 % | 99,4 % | 99,1 % | 98,8 % | 99,7 % |
| Réponses dans une autre langue | 0,3 % | 0,3 % | 0,6 % | 0,0 % | 0,0 % |
| Réponses de langue indéterminée | 12,5 % | 0,3 % | 0,3 % | 1,2 % | 0,3 % |
| Longueur moyenne d'une réponse (mots) | 320,7 | 213,4 | 241,3 | 215,2 | 222,5 |
| Perte sur le texte du pré-entraînement (nats par jeton, 64 morceaux) | 2,347 | 2,928 | 2,615 | 3,766 | 2,998 |
| Bits par octet sur ce texte | 0,779 | 0,972 | 0,868 | 1,250 | 0,995 |

**Les mesures de l'étape 1.9** (problèmes de calcul, passées aussi pour voir d'où partira le
raisonnement) :

| Mesure | `ton-ia-1.5` | **`ton-ia-1.7`** (1e-4) | courte (1e-4) | complète à 3e-4 | courte à 3e-4 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Problèmes générés, justes en glouton (sur 400) | 0 (0,0 %) | 1 (0,2 %) | 1 (0,2 %) | 3 (0,8 %) | 0 (0,0 %) |
| Problèmes générés, au moins un juste sur 8 essais | 0,0 % | 1,2 % | 2,8 % | 2,8 % | 1,8 % |
| Problèmes générés, réponses terminées | 0,0 % | 65,2 % | 54,5 % | 57,0 % | 47,0 % |
| MGSM-rev2 en français, justes (sur 250) | 0 | 0 | 0 | 1 | 0 |
| MGSM-rev2, réponses terminées | 0,0 % | 38,8 % | 38,4 % | 36,0 % | 23,6 % |
| GSM8K-Platinum en français, justes (sur 1 196) | 0 | 10 | 6 | 4 | 6 |
| GSM8K-Platinum, réponses terminées | 0,0 % | 45,4 % | 35,5 % | 33,5 % | 27,5 % |
| IFEval-FR, invites respectées (second passage) | 20,9 % | 15,3 % | 15,7 % | 15,7 % | 15,3 % |
| Réponses terminées (second passage) | 0,0 % | 48,1 % | 47,5 % | 51,9 % | 54,0 % |

**Le bruit.** Le même modèle, mesuré deux fois, ne donne pas tout à fait les mêmes nombres : `ton-ia-1.7`
respecte 14,5 % des invites d'IFEval-FR à l'étape 1.7 et 15,3 % à l'étape 1.9 ; 1.5, 21,7 % et 20,9 %.
Les réponses terminées passent de 51,0 % à 48,1 %. Le lot de génération dépend de la mémoire libre de la
carte ; cause probable, non vérifiée : les calculs en bf16 d'un lot à l'autre changent parfois un jeton
choisi en glouton. Un écart de l'ordre d'un point sur IFEval-FR, ou de quelques points sur les réponses
terminées, n'est donc pas une différence. Pour les problèmes, quelques réponses justes sur des centaines
ne départagent personne.

Ce que disent ces nombres :

- **Ton IA 1.7 finit ses réponses**, ce que 1.5 ne faisait jamais : 51,0 % de réponses terminées, contre
  0,0 %. Elle répond en français dans 99,4 % des cas (87,2 % pour 1.5), et plus court (213,4 mots en
  moyenne contre 320,7).
- **Elle suit moins bien les consignes d'IFEval-FR que 1.5** : 14,5 % des invites entièrement respectées,
  contre 21,7 % (et 15,3 % contre 20,9 % au second passage) : l'écart dépasse largement le bruit.
  Entre les quatre versions affinées, les écarts du premier passage (de 14,5 % à 16,2 %) ne
  se confirment pas au second (de 15,3 % à 15,7 %) : aucune ne suit mieux les consignes qu'une autre.
- **Elle prédit moins bien que 1.5 le texte de son pré-entraînement, mais bien mieux qu'à 3e-4** : la
  perte sur ce texte passe de 2,347 (1.5) à 2,928 nats par jeton, contre 3,766 pour la complète à 3e-4
  (0,779, 0,972 et 1,250 bit par octet). L'écart avec 1.5 est de 0,58 nat au lieu de 1,42.
- **Elle apprend un peu moins les conversations qu'à 3e-4** : perte de validation 0,978 contre
  0,936 (1.5 : 2,300).
- **Les problèmes :** 1 problème généré juste sur 400 en glouton, 0 sur 250 pour MGSM, 10 sur 1 196 pour
  GSM8K-Platinum : presque rien, comme les autres versions affinées ; 1.5 n'en résolvait aucun, car elle
  ne finissait aucune réponse.

## 8. Les échantillons

Les dix invites fixes de `forge evaluer-etape`, en glouton, 200 jetons au plus, pour la version publiée
(`evaluations\ton-ia-1.7-1.7`). Les réponses sont recopiées telles quelles, sans tri ni retouche. Celles
des autres versions sont dans leurs rapports.

### 1. « Quelle est la capitale de la France ? »

Réponse terminée par `<|fin_tour|>` :

```text
La capitale de la France est Paris.
```

### 2. « Pourquoi le ciel est-il bleu ? »

Réponse terminée par `<|fin_tour|>` :

```text
Le ciel est bleu parce que les nuages sont blancs et que le ciel est bleu. Le ciel est bleu parce que les nuages sont blancs et que le ciel est bleu.
```

### 3. « Explique en deux phrases comment fonctionne la photosynthèse. »

Réponse terminée par `<|fin_tour|>` :

```text
La photosynthèse est le processus par lequel les plantes, les algues et certaines bactéries utilisent l'énergie lumineuse pour convertir le dioxyde de carbone ($CO_2$) et l'eau ($H_2O$) en glucides (comme le glucose) et en oxygène ($O_2$).
```

### 4. « Combien font 12 fois 7 ? »

Réponse terminée par `<|fin_tour|>` :

```text
Pour déterminer combien font 12 fois 7 ?
```

### 5. « Donne-moi trois conseils pour bien dormir. »

Réponse coupée par la limite de 200 jetons :

```text
Je vous recommande de prendre trois mesures pour bien dormir, car le sommeil est un processus complexe et multidimensionnel. Voici quelques conseils pour bien dormir :

1. **Éviter les écrans avant le coucher** : Éviter les écrans avant le coucher augmente les risques de troubles du sommeil, de fatigue et de troubles du sommeil nocturne. Les écrans sont un outil de communication essentiel pour le sommeil.

2. **Apprendre à utiliser des techniques de relaxation** : Apprendre à relaxer efficacement est essentiel pour réduire l'anxiété et améliorer le sommeil. La relaxation est un facteur clé de l'endormissement.

3. **Apprendre à gérer le stress et à gérer le sommeil** : Le sommeil est essentiel pour la santé physique et mentale. Le stress peut perturber le sommeil, ce qui peut aggraver l'insomnie et le sommeil paradoxal.

4. **Apprendre à gérer le stress et à gérer le sommeil** : Le sommeil est essentiel pour la santé physique et mentale.
```

### 6. « Quelle est la différence entre un virus et une bactérie ? »

Réponse terminée par `<|fin_tour|>` :

```text
La différence entre un virus et une bactérie réside dans leur mode de reproduction et leur mode de reproduction. Les virus sont des parasites intracellulaires obligatoires qui se reproduisent uniquement par la **transformation** (la transformation d'un organisme vivant en organisme vivant). Les bactéries sont des organismes procaryotes qui se reproduisent uniquement par la **transformation** (la transformation d'un organisme vivant en un autre).
```

### 7. « Écris un court texte sur l'automne en moins de 50 mots, tout en minuscules. »

Réponse coupée par la limite de 200 jetons :

```text
l'automne est une saison de transition, de renouveau et de renouveau. Voici quelques conseils pour écrire un texte sur l'automne, en commençant par les plus courants :

1. **taille des mots** : il est préférable de commencer par des mots simples, comme « printemps », « été », « automne », « hiver », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », « printemps », «
```

### 8. « Présente-toi en trois phrases, sans utiliser de virgule. »

Réponse terminée par `<|fin_tour|>` :

```text
Je suis ton IA, je suis ton IA, je suis ton IA.
```

### 9. « Qui es-tu ? »

Réponse terminée par `<|fin_tour|>` :

```text
Je suis ton IA, une petite intelligence artificielle qui est à la fois intelligente et intelligente. Je suis ton IA, une intelligence artificielle qui est à la fois intelligente et intelligente. Je suis ton IA, une intelligence artificielle qui est à la fois intelligente et intelligente. Je suis ton IA, une intelligence artificielle qui est à la fois intelligente et intelligente.
```

### 10. « Écris une fonction Python qui renvoie la somme des carrés d'une liste de nombres. »

Réponse coupée par la limite de 200 jetons :

```text
Pour calculer la somme des carrés d'une liste de nombres, nous devons suivre les étapes suivantes :

1. **Identifier les nombres** : Nous avons deux nombres : 1 et 2.
2. **Remplacer les nombres dans la fonction** : La fonction retourne la somme des carrés des nombres $\{1, 2, 3, 4, 5, 6, 7, 8, 9\}$.
3. **Calculer la somme** : La somme est la somme des carrés des nombres $\{1, 2, 3, 4, 5, 6, 7, 8, 9\}$.

### Étape 1 : Calculer la somme des carrés

La somme des carrés est la somme des carrés des nombres entiers $1, 2, 3, 4, 5, 6, 7, 8, 9$.

$$
\be
```

`ton-ia-1.7` termine 7 de ces dix réponses ; la courte à 1e-4 3, la complète à 3e-4 6, la courte à 3e-4
3, et `ton-ia-1.5` 0 : toutes celles de 1.5 vont jusqu'à la limite.

## 9. Ce que ton IA 1.7 sait faire, et ce qu'elle ne sait pas faire

D'après les mesures de la version publiée et ses dix échantillons :

**Elle sait :**

- répondre à une question, puis s'arrêter, à peu près une fois sur deux : 51,0 % de réponses
  terminées (section 7), et 7 des dix échantillons ;
- répondre en français : 99,4 % des réponses ;
- donner un fait très connu (échantillon 1 : « La capitale de la France est Paris. ») ;
- écrire une définition correcte quand elle est courante (échantillon 3, la photosynthèse, en une phrase
  au lieu des deux demandées) ;
- dire qu'elle est « ton IA » (échantillons 8 et 9), en se répétant.

**Elle ne sait pas :**

- calculer : à « Combien font 12 fois 7 ? », elle répète la question sans répondre (échantillon 4) ;
  1 problème généré juste sur 400, 0 sur 250 pour MGSM, 10 sur 1 196 pour GSM8K-Platinum ;
- dire des choses vraies à coup sûr : elle écrit des choses fausses (échantillon 2 : le ciel est bleu
  « parce que les nuages sont blancs » ; échantillon 5 : les écrans, « un outil de communication
  essentiel pour le sommeil » ; échantillon 6 : virus et bactéries se reproduiraient par
  « transformation ») ;
- respecter une consigne de forme : 14,5 % des invites d'IFEval-FR, contre 21,7 % pour 1.5 ; dans les
  échantillons, une majuscule malgré « tout en minuscules » (7) et des virgules malgré « sans virgule »
  (8) ;
- écrire du code : à la demande d'une fonction Python, elle déroule des étapes de calcul sans code
  (échantillon 10) ;
- s'arrêter à coup sûr : 49,0 % de ses réponses vont jusqu'à la limite de longueur, et elle répète
  souvent une même phrase (échantillons 7, 8 et 9) ;
- prolonger un texte libre aussi bien que 1.5 : sa perte sur le texte du pré-entraînement monte de
  2,347 à 2,928 nats par jeton (moins qu'à 3e-4, 3,766).

## 10. Les fichiers de la version `ton-ia-1.7`

| Fichier | Octets | SHA-256 |
| --- | ---: | --- |
| `ton-ia-1.7.safetensors` | 867 161 248 | `6a6d2c08e15d4dc22fa3205d11e28ad3eb82d6944c649788836a125c25758d32` |
| `config.json` | 134 | `ae0207b367080a6577c2d95ef81ba5fb84c6bf2be11d03a07eedd8a9fe598621` |
| `tokenizer-ton-ia-v1.json` | 546 692 | `3001e7ab40630739c4dec807c7a92c0d4fb469cc0fc4afa368704395391f21ba` |
| `rapport.json` (de `evaluations\ton-ia-1.7-1.7`) | 17 660 | `8e7d291ab2fda4681229d872f9f3f97047500963db739cd20bd736c4de3767b5` |

Les poids sont en bf16, exportés par `forge exporter` depuis
`entrainements\sft-1.7\sauvegardes\meilleur.pt` (le pas 3 338 de l'entraînement à 1e-4). `config.json` et
le tokenizer sont ceux de 1.5, à l'octet près.

Les trois autres versions restent sur le disque, pour comparer ; aucune n'est publiée :

| Version | Fichier des poids | SHA-256 |
| --- | --- | --- |
| courte à 1e-4 | `publications\ton-ia-1.7-court\ton-ia-1.7-court.safetensors` | `2a598395efef1a1bfc2b4cf3376603baea723d4e8f98de34e8d715e98d5c3a92` |
| complète à 3e-4 | `publications\ton-ia-1.7-3e-4\ton-ia-1.7-3e-4.safetensors` | `b53eb7e2880e542e87ace535b13fcce99c1435c5c903dea192d267028aead8b8` |
| courte à 3e-4 | `publications\ton-ia-1.7-court-3e-4\ton-ia-1.7-court-3e-4.safetensors` | `22473f1a872f8a95d73ab54194bc6a634f5fc17f357f19b6ea498ee857661aaf` |

Leurs fichiers de poids ont été renommés avec leur dossier ; leur contenu, et donc leur empreinte, n'a
pas changé.
