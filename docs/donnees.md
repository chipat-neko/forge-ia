# Les données de « ton IA »

« ton IA » lit et écrit le français et le code. Elle apprend sur trois sources
publiques, lues en flux depuis Hugging Face (jamais téléchargées en entier), nettoyées,
dédoublonnées, puis rangées hors du dépôt. Le code qui fait tout cela est dans
`projets/forge/forge/donnees/`.

Les données ne sont jamais copiées dans ce dépôt ; seuls les modèles entraînés sont publiés.

Les tailles des trois sources ont été relevées le 09/11/2026 à l'API de Hugging Face (la liste
des fichiers parquet du dossier lu et la somme de leurs tailles) ; elles sont écrites en Gio
(2³⁰ octets, comme le site), alors que Hugging Face les affiche en GB décimaux (10⁹ octets).
Les adresses de l'API, lues le 09/11/2026 :
[FineWeb-2](https://huggingface.co/api/datasets/HuggingFaceFW/fineweb-2/tree/main/data/fra_Latn/train),
[Wikipédia](https://huggingface.co/api/datasets/wikimedia/wikipedia/tree/main/20231101.fr) et
[github-code-clean](https://huggingface.co/api/datasets/codeparrot/github-code-clean/tree/main/data).
`projets/1.2-donnees` refait le tri de ces sources pas à pas, et en relève un aperçu.

## Le mélange

| Source | Nom dans le code | Part |
| --- | --- | --- |
| Français du web | `web_fr` | 75 % |
| Wikipédia en français | `wikipedia_fr` | 10 % |
| Code Python sous licence permissive | `code_python` | 15 % |

Les parts sont définies une seule fois, dans `forge.donnees.melange.MELANGE_PAR_DEFAUT`.
Le téléchargement et l'apprentissage du tokenizer les lisent là ; l'encodage
(`python -m forge encoder`) les lit aussi, pour savoir quelles sources encoder.

## Français du web (`web_fr`)

- **Dépôt :** [HuggingFaceFW/fineweb-2](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2),
  dossier `data/fra_Latn/train` (135 fichiers parquet d'environ 3,7 Gio chacun, 539 897 427 722
  octets en tout, soit 502,8 Gio ; Hugging Face affiche 539,9 GB décimaux ; sans formulaire
  d'accès).
- **Licence :** [ODC-By 1.0](https://opendatacommons.org/licenses/by/1-0/) (Open Data Commons
  Attribution). Les pages viennent de Common Crawl, dont les
  [conditions d'utilisation](https://commoncrawl.org/terms-of-use) s'appliquent aussi.
- **Ce qui est gardé :** la colonne `text` de toutes les pages du dossier. Les autres colonnes
  (adresse, date, score de langue…) ne sont pas conservées.

## Wikipédia en français (`wikipedia_fr`)

- **Dépôt :** [wikimedia/wikipedia](https://huggingface.co/datasets/wikimedia/wikipedia),
  configuration `20231101.fr` (17 fichiers, 4 614 488 286 octets en tout, soit 4,30 Gio ;
  Hugging Face affiche 4,61 GB décimaux ; sans formulaire d'accès).
- **Licence :** [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/deed.fr) (le jeu
  est aussi publié sous GFDL).
- **Ce qui est gardé :** la colonne `text` de tous les articles (le texte seul, sans le titre
  ni l'adresse).

## Code Python (`code_python`)

- **Dépôt :** [codeparrot/github-code-clean](https://huggingface.co/datasets/codeparrot/github-code-clean)
  (880 fichiers parquet dans `data`, 313 663 761 086 octets en tout, soit 292,1 Gio ; Hugging
  Face affiche 313,7 GB décimaux, et 313 663 770 241 octets pour le dépôt entier, avec ses trois
  petits fichiers ; sans formulaire d'accès). On lit ses fichiers parquet directement, car son
  script de chargement n'est plus accepté par les versions récentes de `datasets`.
- **Licence :** la compilation est sous [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0),
  mais chaque fichier garde la licence de son dépôt d'origine (colonne `license`). On ne garde
  que les fichiers sous une de ces sept licences permissives :
  [MIT](https://spdx.org/licenses/MIT.html),
  [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html),
  [BSD-2-Clause](https://spdx.org/licenses/BSD-2-Clause.html),
  [BSD-3-Clause](https://spdx.org/licenses/BSD-3-Clause.html),
  [ISC](https://spdx.org/licenses/ISC.html),
  [Unlicense](https://spdx.org/licenses/Unlicense.html) et
  [CC0-1.0](https://spdx.org/licenses/CC0-1.0.html).
- **Ce qui est gardé :** la colonne `code` des fichiers dont le langage (`language`) est
  `Python` et dont la licence est dans la liste ci-dessus. Le dépôt d'origine et le chemin du
  fichier ne sont pas conservés dans nos fragments ; on les retrouve dans la source.
- **Combien il faut lire :** le Python permissif ne fait que 4,1 % des fichiers et 3,9 % des
  octets de code (mesuré le 03/11/2026 sur 7 fichiers parquet répartis dans tout le jeu).
  Garder 1 Mo de code demande donc de lire environ 26 Mo de code, soit environ 9 Mo de parquet
  compressé. Les fichiers Python sont répartis partout, dans chaque groupe de lignes de chaque
  fichier parquet : aucun fichier ni groupe de lignes ne peut être sauté, et la colonne `code`
  fait 98 % du poids (garder seulement quelques colonnes n'économise presque rien).

## Ce que fait le téléchargement

- **Nettoyage :** forme Unicode NFC, fins de ligne `\n`, caractères de contrôle retirés (sauf
  `\n` et `\t`), espaces de fin de texte retirées. Un texte de moins de 200 caractères une fois
  nettoyé est écarté.
- **Doublons :** l'empreinte SHA-1 du texte nettoyé sert à ne jamais écrire deux fois le même
  texte, y compris après une reprise.
- **Fragments :** des fichiers `fragment-00000.jsonl.gz` d'environ 100 Mo de texte, une ligne
  `{"texte": …}` par document. Chaque fichier est écrit sous un nom `.tmp`, puis renommé d'un
  coup. L'état (`etat.json`) n'est mis à jour qu'après le fragment qu'il compte.
- **Reprise :** après une coupure (réseau, courant, disque plein), on relance la même commande.
  Les fragments déjà écrits sont gardés, et rien n'est écrit deux fois. Avec chaque fragment,
  `etat.json` garde aussi l'état du flux (`etat_du_flux`) pour que la reprise reparte du fichier
  et du groupe de lignes où le flux s'était arrêté, sans relire ce qui est déjà compté. Un
  téléchargement commencé avant cette version n'a pas cet état. Sa première reprise relit le
  flux depuis le début du jeu, puis saute les documents déjà comptés. Cette relecture coûte du
  temps et du réseau, d'autant plus que la coupure est tardive : il a fallu 18 minutes pour
  sauter 15,6 millions de documents de `code_python`, lors de la reprise mesurée dans
  `docs/mesures/entrainement-2026-11.md`. Dès que cette reprise écrit un fragment, l'état du flux
  est tenu, avec le nombre de documents sautés (`sautes_a_l_ouverture`) : les reprises suivantes
  ne relisent rien. Si le jeu refuse l'état enregistré (autre source, autre version de
  `datasets`), la commande s'arrête sans rien écrire. Un fragment déjà compté qui manque n'est
  jamais refait, car la reprise repart après le dernier document compté : la commande
  s'arrête et dit quoi faire (remettre le fichier, ou effacer le dossier de la source et la
  retélécharger). Le marqueur `.complet` n'est posé qu'à la fin ; sans lui, une source
  n'est jamais tenue pour terminée.
- **Place :** avant chaque fragment, on vérifie qu'il reste de la place pour lui et 2 Go de
  marge. Sinon, la commande s'arrête avec un message qui dit combien de Go libérer.
- **Où :** `FORGE_DONNEES/textes/<dossier>/<source>/` (par défaut `D:\forge-ia-donnees` sur
  ce PC), un sous-dossier par source.
- **Validation :** le téléchargement ne met rien de côté : la séparation entre entraînement et
  validation se fait à l'encodage (voir plus bas), avec `est_validation`, qui met de côté 0,5 % des
  documents d'après les 8 premiers chiffres de leur empreinte (le même document tombe toujours du
  même côté).

```powershell
. .\outils\env-forge.ps1
cd projets/forge
uv run --extra gpu python -m forge donnees --octets 300M --dossier echantillon
```

La commande lève `HF_HUB_OFFLINE=1`, s'il est posé dans la session, pour ce téléchargement
seulement : elle a besoin du réseau.

Pour un volume hors mélange (par exemple assez de texte pour mesurer la compression sur 1 Mo
de validation de chaque source), `--parts` remplace `--octets` et donne un volume par source :

```powershell
uv run --extra gpu python -m forge donnees --parts web_fr=400M,wikipedia_fr=350M,code_python=300M --dossier validation-tokenizer
```

Les trois sources doivent y figurer, dans n'importe quel ordre ; `--octets` et `--parts` ne se
donnent pas ensemble.

## Ce que fait l'encodage

L'encodage lit les fragments de texte et les écrit en jetons, avec le tokenizer de ton IA. Il
travaille hors du dépôt, sous `FORGE_DONNEES/jetons/<dossier>/`.

- **Fichiers :** `train/fragment-00000.bin` et `val/fragment-00000.bin`, en `uint16`
  (petit-boutiste), lisibles avec `forge.donnees.jetons.lire_jetons`. Chaque document est suivi
  du jeton `<|fin_texte|>`. Un document va dans `val/` quand `est_validation` le dit (0,5 % des
  documents) ; un fichier qui n'aurait aucun jeton n'est pas écrit.
- **Numéros :** le fragment de sortie `k` vient du `k`-ième fragment d'entrée, quand on range les
  sources par nom, puis les fragments par nom. `index.json` donne le nombre de jetons de chaque
  fichier et d'où il vient.
- **Parallélisme :** un fragment à la fois par processus, tous les cœurs par défaut
  (`--processus N` pour en changer). Le résultat est le même quel que soit le nombre de processus.
- **Reprise :** chaque fragment encodé a son marqueur `fragment-00000.fait`, posé après ses
  fichiers de jetons. Après une coupure, on relance la même commande : les fragments dont le
  marqueur correspond encore au fragment de texte et au tokenizer sont sautés, les autres sont
  refaits. `.complet` n'est posé qu'à la fin.
- **Place :** avant chaque fichier, on vérifie qu'il reste de la place pour lui et 2 Go de marge.
- **Refus :** une source sans `.complet` n'est jamais encodée, ni une source dont un fragment
  compté dans `etat.json` manque (le corpus serait troué sans bruit). Un dossier de sortie déjà
  rempli avec un autre tokenizer n'est jamais réécrit sans que tu le décides (supprime-le, ou
  choisis-en un autre).

```powershell
uv run --extra gpu python -m forge encoder --donnees echantillon --tokenizer forge/ressources/tokenizer-ton-ia-v1.json
```

## Vague 2 : affiner ton IA

La vague 2 affine ton IA avec des conversations, puis la mesure sur des jeux d'évaluation. Les
sources ci-dessous se téléchargent avec `python -m forge conversations --source NOM`, en flux, par
fragments de 50 000 éléments repris après une coupure, sous
`FORGE_DONNEES/conversations/<source>/` (`conversations-00000.jsonl.gz`, `etat.json` et `.complet`,
qui garde le nom, la licence, l'usage et les comptes : lignes lues, gardées, écartées par raison).
`--liste` donne le nom, l'usage, la licence et le lien de chaque source ; `--exemples-max N`
s'arrête après N éléments gardés (20 suffisent pour vérifier les colonnes).

- **Reprise :** la même que celle des textes. À chaque fragment, `etat.json` garde l'état du flux
  (`etat_du_flux`) et le saut fait à l'ouverture du flux (`sautes_a_l_ouverture`) : la relance
  recharge l'un sur un jeu sauté de l'autre. Un téléchargement repris rend les mêmes fichiers
  qu'un téléchargement d'une traite. Ctrl+C valide le fragment en cours, puis affiche la commande
  de reprise.
- **Deux usages :** `entraînement` (le jeu nourrit un affinage) ou `évaluation` (le jeu ne sert qu'à
  mesurer). Les jeux réservés à l'évaluation (IFEval-FR, MGSM-rev2, GSM8K-Platinum-fr et HumanEval)
  ne vont jamais dans un entraînement : leurs énoncés se retrouveraient dans les données, et la
  mesure serait faussée. Aucune lecture pour l'entraînement ne les accepte (`source_d_entrainement`,
  `lire_pour_entrainement`), et chacun de leurs éléments porte `"usage": "evaluation"`.
- **Licences :** un jeu d'entraînement porte sa licence et son lien. On écarte les jeux dont les
  invites ou les réponses viennent de Llama ou d'OpenAI, les licences non commerciales et les jeux
  sans licence ; le partage à l'identique (CC BY-SA) est réservé à l'évaluation. Le détail et les
  fiches lues sont dans `docs/superpowers/recherche/2026-11-17-vague-2-donnees.md`.

### Luth-2 (`luth2_conversation` et `luth2_code`)

- **Dépôt :** [kurakurai/Luth-2-Post-Training-SFT](https://huggingface.co/datasets/kurakurai/Luth-2-Post-Training-SFT)
  (1 969 768 lignes, 20 fichiers parquet, sans formulaire d'accès). Les invites sont traduites en
  français et les réponses régénérées par des modèles ouverts. La colonne `source` nomme le jeu d'où
  vient l'invite, la colonne `generator` le modèle qui a écrit la réponse.
- **Licence :** CC BY 4.0 ([texte](https://creativecommons.org/licenses/by/4.0/)). D'après la fiche, les
  lignes que Nemotron a tirées de StackOverflow restent en CC BY-SA 4.0. La colonne `source` ne les
  distingue pas : voir « Les sources amont » plus bas.
- **Usage :** entraînement
- **Ce qui est gardé (`luth2_conversation`) :** le domaine `knowledge` ou `if` ; un générateur dont
  le nom commence par `Qwen/` (Apache-2.0, sans clause sur l'usage des sorties) ; aucun appel d'outil
  (`tool_calls`) ni rôle `tool` ; une source amont qui n'est pas écartée : la colonne `source`, en
  minuscules, ne contient aucune valeur de `SOURCES_AMONT_ECARTEES` (`stackoverflow`, `smoltalk`,
  `magpie`, `dolci`, `tulu`).
- **Ce qui est gardé (`luth2_code`) :** le domaine `code`, avec les mêmes filtres, et une réponse qui
  contient un bloc de code Python (balise `python`). Le jeu n'est pas filtré par langage de programmation.
- **Raisons comptées :** `domaine`, `generateur`, `appel_d_outil`, `source_amont`, `pas_de_python`,
  `conversation_invalide`.
- **Téléchargement du 17/11/2026 (`luth2_conversation`) :** 560 448 conversations gardées sur
  1 969 768 lignes lues, en 8 min 46 s. Écartées : 1 162 639 pour le domaine, 78 578 pour le
  générateur, 168 103 pour la source amont. Toutes les lignes gardées viennent de Nemotron.

#### Les sources amont de Luth-2

Fiches lues le 17/11/2026. Les lignes sont comptées sur le jeu entier (révision `47cd1af`), en lisant
les colonnes `domain`, `source` et `generator` des 20 fichiers. On écarte toute source amont dont les
invites ou les réponses viennent de Llama ou d'OpenAI.

| Source amont | Lignes par domaine | Générateur des réponses | Décision |
| --- | --- | --- | --- |
| `nvidia/Nemotron-Post-Training-Dataset-v2` | knowledge 560 448, code 227 934, math 146 005 | `Qwen/Qwen3.6-35B-A3B` | gardée |
| `allenai/Dolci-Instruct-SFT` | knowledge 34 739, if 112 747, code 320 498, math 234 586 | `Qwen/Qwen3-30B-A3B` | écartée (`dolci`) |
| `allenai/Dolci-Instruct-SFT-Tool-Use` | tool_call 186 176 | `google/gemma-4-31B-it` | écartée (`dolci`, et par le domaine et le générateur) |
| `HuggingFaceTB/smoltalk2` | if 50 396 (sans générateur) et 28 182 | aucun, et `google/gemma-4-26b-a4b-it` | écartée (`smoltalk`, et par le générateur) |
| `allenai/tulu-3-sft-personas-instruction-following` | if 20 617 | `Qwen/Qwen3-32B` | écartée (`tulu`) |
| `allenai/tulu-3-sft-personas-math` | math 47 440 | `Qwen/Qwen3-32B` | écartée (`tulu`, et par le domaine) |

- **Nemotron, gardée.** Les réponses sont régénérées par Qwen (Apache-2.0). D'après sa fiche et
  l'article de Nemotron Nano 2 (arXiv 2508.14444), les invites viennent de corpus publics
  (LMSYS-Chat-1M, WildChat-1M, HelpSteer, problèmes de concours) ou sont générées. Deux réserves :
  - le modèle qui a généré les invites synthétiques n'est nommé ni par la fiche ni par l'article [non vérifié] ;
  - la fiche annonce « un petit sous-ensemble » d'invites tirées de StackOverflow, sous CC BY-SA 4.0.
    Luth-2 ne garde pas la licence de chaque ligne, et le jeu d'origine est à accès restreint (non
    ouvert ici) : ces lignes ne sont pas reconnues, elles restent dans le jeu.
- **Dolci-Instruct-SFT, écartée.** Ce mélange de l'Allen Institute réunit une vingtaine de jeux. Parmi
  eux, Tulu 3 Personas a des invites écrites par GPT-4o. Evol CodeAlpaca, CoCoNot, WildGuardMix et
  WildJailbreak ont des invites écrites par GPT-4 [résumé]. Luth-2 ne dit pas de quel jeu vient
  chaque ligne : on ne peut garder les autres jeux, tout est écarté.
- **Dolci-Instruct-SFT-Tool-Use, écartée.** Ce sont des appels d'outils, aux réponses écrites par Gemma.
- **SmolTalk2, écartée.** Ses lignes françaises traduisent les invites de Smol-Magpie-Ultra, écrites par
  Llama 3.1 405B [résumé, « données », §1.2], et de Smol-Constraints. Ses conversations à plusieurs
  tours partent des invites de Tulu 3 Personas IF. Les réponses sont de Gemma, ou sans générateur nommé.
- **Tulu 3 Personas (consignes et maths), écartées.** Les invites sont générées avec des personas. La
  fiche de Persona MATH dit que ses sorties viennent de GPT-4o et de Claude 3.5 Sonnet. Celle de
  Persona IF ne nomme pas le modèle, mais la méthode est la même [non vérifié dans sa fiche].

Ce que chaque valeur de `SOURCES_AMONT_ECARTEES` écarte, sur le jeu entier :

| Valeur | Lignes dont la source la contient | Dont `knowledge`, `if` et `code` | Comptées `source_amont` par `luth2_conversation` |
| --- | ---: | ---: | ---: |
| `stackoverflow` | 0 | 0 | 0 |
| `smoltalk` | 78 578 | 78 578 | 0 (déjà écartées pour le générateur) |
| `magpie` | 0 | 0 | 0 |
| `dolci` | 888 746 | 467 984 | 147 486 |
| `tulu` | 68 057 | 20 617 | 20 617 |

`stackoverflow` et `magpie` n'écartent rien : aucune valeur de `source` ne les contient. Ils restent
dans la liste au cas où une révision de Luth-2 nommerait ces sources. Les 168 103 lignes comptées
`source_amont` par le téléchargement sont exactement celles de Dolci et de Tulu Personas IF dans les
domaines `knowledge` et `if`.

### Aya français (`aya_fr`)

- **Dépôt :** [CohereLabs/aya_dataset](https://huggingface.co/datasets/CohereLabs/aya_dataset)
  (205 568 lignes toutes langues, sans formulaire d'accès). Écrit ou corrigé par des bénévoles.
- **Licence :** Apache-2.0 ([texte](https://www.apache.org/licenses/LICENSE-2.0)).
- **Usage :** entraînement
- **Ce qui est gardé :** les lignes dont `language_code` vaut `fra` (colonnes `inputs` et `targets`),
  une question et une réponse par conversation. La fiche signale des erreurs de langue et du
  contenu offensant possible.

### OpenAssistant OASST2 français (`oasst2_fr`)

- **Dépôt :** [OpenAssistant/oasst2](https://huggingface.co/datasets/OpenAssistant/oasst2), fichier
  `2023-11-05_oasst2_ready.trees.jsonl.gz` (un arbre de conversation par ligne, sans formulaire
  d'accès). Écrit par des bénévoles. `datasets` ne sait pas inférer le schéma de ces arbres
  imbriqués : le fichier est téléchargé, puis lu ligne à ligne.
- **Licence :** Apache-2.0 ([texte](https://www.apache.org/licenses/LICENSE-2.0)).
- **Usage :** entraînement
- **Ce qui est gardé :** les arbres dont la racine est en français (`lang` vaut `fr`). Chaque arbre
  donne une conversation : la racine, puis la réponse d'assistant de rang 0, puis la réponse
  d'utilisateur la plus ancienne, et ainsi de suite, tant que les messages sont en français. Les
  réponses supprimées ou refusées à la relecture sont ignorées. La conversation finit toujours par
  l'assistant.

### OpenCoder educational_instruct (`opc_educational`)

- **Dépôt :** [OpenCoder-LLM/opc-sft-stage2](https://huggingface.co/datasets/OpenCoder-LLM/opc-sft-stage2),
  configuration `educational_instruct` (sans formulaire d'accès). Des triplets (instruction, code,
  test) validés par un compilateur Python. Les autres configurations reprennent des jeux dérivés de
  sorties d'OpenAI : on ne les prend pas.
- **Licence :** MIT ([texte](https://opensource.org/license/mit)).
- **Usage :** entraînement (après traduction des consignes)
- **Ce qui est gardé :** l'instruction, le code, les tests (`testcase`) et le point d'entrée. Les
  consignes sont en anglais : elles se traduisent avant l'entraînement.

### IFEval-FR (`ifeval_fr`)

- **Dépôt :** [kurakurai/IFEval-FR](https://huggingface.co/datasets/kurakurai/IFEval-FR) (235 invites,
  sans formulaire d'accès). Partie française de M-IFEval : des instructions propres à la langue,
  relues par un locuteur natif.
- **Licence :** Apache-2.0 ([texte](https://www.apache.org/licenses/LICENSE-2.0)).
- **Usage :** évaluation
- **Ce qui est gardé :** l'invite (`prompt`), `instruction_id_list` et `kwargs`.

### MGSM-rev2 français (`mgsm_rev2_fr`)

- **Dépôt :** [lightonai/mgsm-rev2](https://huggingface.co/datasets/lightonai/mgsm-rev2),
  configuration `fr` (250 problèmes, split `test`, sans formulaire d'accès). Version corrigée de MGSM.
- **Licence :** CC BY-SA 4.0 ([texte](https://creativecommons.org/licenses/by-sa/4.0/)). Le partage à
  l'identique est une raison de plus pour ne jamais l'entraîner.
- **Usage :** évaluation
- **Ce qui est gardé :** la question et la réponse numérique (`answer_number`).

### GSM8K-Platinum français (`gsm8k_platinum_fr`)

- **Dépôt :** [cmh/gsm8k-platinum_fr](https://huggingface.co/datasets/cmh/gsm8k-platinum_fr)
  (1 196 problèmes, split `test`, sans formulaire d'accès). Traduction de GSM8K-Platinum ; la fiche ne
  dit pas qui l'a faite : on la relit par échantillon avant de s'y fier.
- **Licence :** MIT ([texte](https://opensource.org/license/mit)).
- **Usage :** évaluation
- **Ce qui est gardé :** la question et la réponse finale (ce qui suit `####`, s'il y en a).

### HumanEval (`humaneval`)

- **Dépôt :** [openai/openai_humaneval](https://huggingface.co/datasets/openai/openai_humaneval)
  (164 problèmes Python, split `test`, sans formulaire d'accès). Énoncés en anglais.
- **Licence :** MIT ([texte](https://opensource.org/license/mit)).
- **Usage :** évaluation
- **Ce qui est gardé :** `task_id`, `prompt`, `test`, `entry_point` et `canonical_solution`.

## Vague 2 : les jeux d'affinage

Un jeu d'affinage se prépare avec `python -m forge preparer --recette NOM` : la recette dit quelles
sources entrent dans le jeu et combien d'exemples on tire de chacune (`forge/affinage/recettes.py`).
Le jeu est écrit sous `FORGE_DONNEES/affinage/NOM/` avec son `index.json`, qui donne, pour chaque
source, les exemples lus, gardés, écartés (doublons, ressemblance avec un jeu d'évaluation, trop longs),
sa licence et son lien.

| Recette | Parts |
| --- | --- |
| `sft-1.7` | `luth2_conversation` 150 000, `aya_fr` tout, `oasst2_fr` tout, `systeme_genere` 20 000, `identite` tout |
| `raisonnement-1.9` | `problemes:entrainement-1.9` 60 000, `luth2_conversation` 12 000, `systeme_genere` 3 000, `identite` tout |

- **Tirage :** les exemples d'une source sont tirés dans l'ordre de `Hasard(graine).melanger`, le même
  à chaque préparation et d'une recette à l'autre : la part de rappel de `raisonnement-1.9` reprend les
  premiers exemples de `sft-1.7`.
- **Doublons :** retirés par l'empreinte du premier tour de l'utilisateur.
- **Jeux d'évaluation :** une part qui en est un (IFEval-FR, MGSM-rev2, GSM8K-Platinum-fr, HumanEval,
  HumanEval-FR) est refusée, avec une erreur qui la nomme. Des problèmes générés ne servent que
  s'ils sont d'usage `entrainement`.
- **Décontamination :** un exemple dont un tour d'utilisateur partage 8 mots de suite (sans casse ni
  ponctuation) avec une invite d'un jeu d'évaluation déjà téléchargé est écarté et compté ; une invite
  d'évaluation de moins de 8 mots est comparée en entier. Sont comparés les sources d'évaluation, les
  problèmes générés d'évaluation et HumanEval-FR, quand ils sont là ; ceux qui manquent sont dits à
  l'écran et dans l'index (`decontamination.absents`). Les problèmes générés d'entraînement et
  d'évaluation emploient les mêmes phrases de gabarit : un problème d'entraînement n'est comparé aux
  problèmes d'évaluation que mot pour mot (leurs prénoms sont différents, voir
  `forge.raisonnement.problemes`), et aux autres jeux d'évaluation par suites de 8 mots.
- **Identifiants :** `ids.txt.gz` (à côté de l'index) garde l'empreinte du premier tour de l'utilisateur
  de chaque exemple gardé, pour que la préparation des paires de préférence ne reprenne pas une invite
  déjà apprise.
- **Reprise :** rien n'est écrit avant la fin de la lecture, l'écriture est atomique et `.complet` vient
  en dernier. Après une coupure, la même commande refait le même jeu, à l'octet près.

### Conversations générées par programme (`systeme_genere` et `identite`)

Ces conversations ne viennent d'aucun jeu de tiers (`forge/conversation/generees.py`).

- **`systeme_genere` :** une consigne de forme (réponse courte, en minuscules, sans virgule, avec un
  titre, un mot imposé, des puces, une phrase de fin…) est donnée dans le message système, devant un
  début de message tiré parmi 20 personnages écrits à la main (une fois sur deux). La réponse est celle
  d'une conversation à un tour de la première source de conversations de la recette (Luth-2 pour les
  deux recettes), transformée pour respecter la consigne, puis gardée seulement si le vérificateur de
  `forge.evaluation.consignes` l'accepte. Les questions viennent d'exemples que la part principale de
  cette source n'a pas pris.
- **`identite` :** au moins 30 questions sur ton IA, avec leur réponse écrite à la main, une fois sans
  et une fois avec un message système. Elles ne disent que des faits : son nom, le site qui l'a créée,
  le français et le Python, sa taille, et qu'elle se trompe souvent. Elles ne prétendent pas que ton IA
  répond bien aux questions ni que son code marche.
- **Licence :** les personnages, les consignes et l'identité sont écrits dans le dépôt, sous sa licence
  (MIT). Les réponses de `systeme_genere` viennent de Luth-2 (ou d'Aya) et restent sous la licence de leur
  source (CC BY 4.0 pour Luth-2) : l'index du jeu le dit. Les problèmes de `problemes:<nom>` sont générés par
  le code du dépôt (MIT).
