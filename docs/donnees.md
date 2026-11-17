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
  français et les réponses régénérées par des modèles ouverts.
- **Licence :** CC BY 4.0 ([texte](https://creativecommons.org/licenses/by/4.0/)). Les lignes
  tirées de StackOverflow restent en CC BY-SA 4.0 : elles sont écartées.
- **Usage :** entraînement
- **Ce qui est gardé (`luth2_conversation`) :** le domaine `knowledge` ou `if` ; un générateur dont
  le nom commence par `Qwen/` (Apache-2.0, sans clause sur l'usage des sorties) ; aucun appel d'outil
  (`tool_calls`) ni rôle `tool` ; une colonne `source` sans `stackoverflow`, `smoltalk` ni `magpie`
  (en minuscules). StackOverflow est en CC BY-SA ; Smol-Magpie viendrait de Llama. La liste des
  sources amont écartées (`SOURCES_AMONT_ECARTEES`) sera complétée après la lecture des fiches des
  autres sources amont.
- **Ce qui est gardé (`luth2_code`) :** le domaine `code`, avec les mêmes filtres, et une réponse qui
  contient un bloc de code Python (balise `python`). Le jeu n'est pas filtré par langage de programmation.
- **Raisons comptées :** `domaine`, `generateur`, `appel_d_outil`, `source_amont`, `pas_de_python`,
  `conversation_invalide`.

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
