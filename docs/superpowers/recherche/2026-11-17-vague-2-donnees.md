# Vague 2 : jeux de données en français pour affiner « Ton IA »

Recherche du 17/11/2026. Toutes les fiches Hugging Face (HF) et les pages web citées ont été lues le 17/11/2026. Les licences viennent de la fiche du jeu (champ `license` et texte de la fiche), pas d'un résumé. Les tailles viennent du serveur de visionnage de HF (`datasets-server.huggingface.co/size`, octets des fichiers Parquet ou originaux), sauf mention « mesuré ici ».

Cadre : modèle de 433,6 M de paramètres, français et Python seulement, publication du modèle entraîné. Quatre chapitres : 1.7 converser, 1.8 aligner, 1.9 raisonner, 1.10 coder.

Comment lire les tableaux :
- « Formulaire » = jeu « gated » sur HF (champ `gated` de l'API). Tous les jeux retenus ci-dessous : **non**.
- « Fiche » = lien vers la page du jeu, lue le 17/11/2026.
- Un jeu dont je n'ai pas trouvé la licence, la méthode ou la taille le dit. Aucun chiffre n'est inventé ; deux chiffres sont calculés par moi et signalés comme tels.

---

## 0. Les trois pièges de licence qui reviennent partout

| Piège | Ce que dit la source | Conséquence pour « Ton IA » |
| --- | --- | --- |
| Sorties d'OpenAI (GPT-3.5, GPT-4, GPT-4o, ChatGPT) | Conditions d'utilisation d'OpenAI, version du 11 décembre 2024 : « Use Output to develop models that compete with OpenAI. » ([copie des conditions](https://open.windriver.com/info/uni-license-list/licenses/openai-tou-20241211.html), lue le 17/11/2026 ; la page openai.com répond 403 à mon outil, donc non lue directement) | Un jeu « Apache-2.0 » ou « MIT » dont les réponses viennent de ChatGPT n'est pas propre. À écarter pour publier. |
| Sorties de Llama (3.1, 3.3) | Licence Llama 3.3, section 1.b.i : si on utilise « any outputs or results of the Llama Materials to create, train, fine tune, or otherwise improve an AI model », alors « you shall also include "Llama" at the beginning of any such AI model name » ([licence](https://dev.meta.ai/llama/llama3_3/license), lue le 17/11/2026) | Possible mais contraignant : le nom du modèle publié devrait commencer par « Llama ». À éviter si on veut un nom libre. |
| Licences non commerciales ou à partage identique | CC BY-NC, CC BY-NC-SA, CC BY-SA (ex. Alpaca, Evol-Instruct-Code-80k, HC3, Dolly) | NC : écarté. SA : obligation de partager l'adaptation sous la même licence ; à décider (voir §8). |

Les sorties de **Qwen3** (Apache-2.0 d'après les fiches des modèles : [Qwen3-32B](https://huggingface.co/Qwen/Qwen3-32B), [Qwen3-30B-A3B](https://huggingface.co/Qwen/Qwen3-30B-A3B), [Qwen3.6-35B-A3B](https://huggingface.co/Qwen/Qwen3.6-35B-A3B), lues le 17/11/2026) et de **Mixtral-8x7B** (Apache-2.0, annoncé par la fiche du jeu) n'ont pas de clause de ce type : ce sont les générateurs à préférer.

---

## 1. Chapitre 1.7 : converser (SFT, instructions, format chat)

### 1.1 Jeux retenus

| Jeu (identifiant HF) | Licence (fiche) | Formulaire | Taille | Format | Fabrication | Avis qualité |
| --- | --- | --- | --- | --- | --- | --- |
| [`kurakurai/Luth-2-Post-Training-SFT`](https://huggingface.co/datasets/kurakurai/Luth-2-Post-Training-SFT) | `cc-by-4.0`. Texte : « The dataset is CC-BY-4.0. However, StackOverflow-derived rows from Nemotron remain CC-BY-SA-4.0. » | non | 1 969 768 lignes ; 9 727 214 834 octets Parquet (20 fichiers) | Parquet, colonnes `id`, `messages` (liste `role`/`content`/`tool_calls`), `tools`, `domain`, `source`, `generator` | Invites traduites en français quand la source est anglaise ; réponses **régénérées** (pas traduites) par Qwen3-30B-A3B, Qwen3-32B, Qwen3.6-35B-A3B (Apache-2.0) ou gemma-4 (étiquette HF `apache-2.0`, lien vers les termes Gemma 4 non lus). Sources : Nemotron-Post-Training-Dataset-v2, Dolci-Instruct-SFT (ODC-By), tulu-3 personas, smoltalk2. Décontaminé par recouvrement de 8-grammes contre leurs bancs d'essai. | Les auteurs publient des gains après SFT sur Qwen3.5-0.8B (IFEval 44,47 à 59,57 ; MGSM-rev2 35,20 à 66,12), chiffres auto-déclarés, non reproduits ici. Moyenne calculée ici : 3,12 G de tokens / 1 969 768 lignes, soit environ 1 580 tokens par exemple : **long** pour un petit modèle, à filtrer par longueur. |
| Même jeu, répartition par domaine (fiche) | | | connaissance 595 187 ; code 548 432 ; maths 428 031 ; suivi d'instructions 211 942 ; appels d'outils 186 176 | colonne `domain` | | Les appels d'outils (`tool_call`) ne servent pas à « Ton IA » : les exclure. |
| [`CohereLabs/aya_dataset`](https://huggingface.co/datasets/CohereLabs/aya_dataset) | `apache-2.0` ; la fiche précise « can be used for any purpose, whether academic or commercial » | non | 205 568 lignes toutes langues ; 138 287 019 octets. Lignes françaises : 1 422 d'après la fiche de [Luth](https://huggingface.co/datasets/kurakurai/luth-sft) (non recompté ici : l'API de filtrage de HF a renvoyé des erreurs) | Parquet `inputs`/`targets`/`language_code` (`fra`) | **Humain** : 204 k paires écrites ou corrigées par des bénévoles (138 844 annotations originales, 65 270 ré-annotations) | La fiche signale des erreurs de langue et du contenu offensant possible. Petit mais le seul jeu français 100 % humain sous Apache. |
| [`OpenAssistant/oasst2`](https://huggingface.co/datasets/OpenAssistant/oasst2) | `apache-2.0` | non | 135 174 messages toutes langues ; 66 674 129 octets. **Mesuré ici** dans `2023-11-05_oasst2_ready.messages.jsonl.gz` : 3 880 messages français, dont 360 invites racines et 2 350 réponses d'assistant | JSONL gzip, arbres de conversation (multi-tours), champ `lang`, rang des réponses | Humain (bénévoles) | Utile pour les vrais multi-tours en français ; très petit. |
| [`CATIE-AQ/everyday-conversations-llama3.1-2k-in-french`](https://huggingface.co/datasets/CATIE-AQ/everyday-conversations-llama3.1-2k-in-french) | `apache-2.0` | non | 2 379 lignes ; 1 239 746 octets | Parquet, conversations de 3 à 4 échanges | Traduction en français de `HuggingFaceTB/everyday-conversations-llama3.1-2k` (`apache-2.0`), dont les conversations ont été générées par **Llama-3.1-70B-Instruct** | Court et simple, pensé pour les petits modèles (« Salut », « Qui es-tu ? »). **Risque Llama** : voir §0. |
| [`OpenLLM-France/Luciole-PostTraining-Dataset-1.1`](https://huggingface.co/datasets/OpenLLM-France/Luciole-PostTraining-Dataset-1.1), sous-ensemble `hardcoded_fr` seulement | `cc-by-sa-4.0` ; « Each source dataset remains under its original licence » | non | `hardcoded_fr` : 962 lignes (fiche). Le jeu entier : 2 268 605 lignes, 6,8 Go | JSONL, `messages` | Nature non décrite dans la fiche (le nom `hardcoded_fr` suggère des réponses d'identité codées en dur ; à vérifier en lisant les lignes) | La fiche avertit : « primarily English ». Ne prendre **que** `hardcoded_fr` (identité du modèle). Partage identique. |

### 1.2 Alternatives intermédiaires (utilisables, avec réserves)

| Jeu | Licence (fiche) | Formulaire | Taille | Fabrication | Réserve |
| --- | --- | --- | --- | --- | --- |
| [`kurakurai/luth-sft`](https://huggingface.co/datasets/kurakurai/luth-sft) (v1 de Luth) | `odc-by` | non | 570 623 lignes ; 574 642 048 octets | Mélange en 7 parties | Contient `luth_openhermes` (406 516 lignes) tiré de `legmlai/openhermes-fr`, **généré par GPT-4o** (voir §7), et `luth_croissantllm` (13 872 lignes) tiré d'un jeu sans licence. Ne garder que `luth_scholar`, `luth_aya_dataset`, `luth_tulu3_persona_instruct`, `luth_tulu3_persona_math` (réponses Qwen3-32B) et vérifier `luth_smoltalk2`. |
| [`kurakurai/scholar`](https://huggingface.co/datasets/kurakurai/scholar) | `odc-by` | non | 60 564 lignes ; 66 731 260 octets | Sujets de baccalauréat et de CPGE (maths, informatique, physique) récupérés sur le web, par Kurakura AI | Droits des sujets d'examen d'origine non documentés dans ce que j'ai lu. |
| [`HuggingFaceTB/smoltalk2`](https://huggingface.co/datasets/HuggingFaceTB/smoltalk2) (partie multilingue) | pas de licence globale dans l'en-tête ; texte : les nouveaux sous-jeux sont `Apache 2.0`, « For the existing public datasets, please refer to the original dataset » | non | `smoltalk_multilingual_8languages_lang_5_no_think` : 254 047 lignes, 8 langues dont le français (part française non comptée) ; fichier entier 87,7 Go | Invites de Smol-Magpie-Ultra et Smol-Constraints traduites par Qwen, réponses générées par le même modèle | Énorme dépôt ; passer par la copie française de Luth (`luth_smoltalk2`, 50 474 lignes) plutôt que par le dépôt entier. Smol-Magpie-Ultra d'origine est généré par un modèle Llama (non relu ici) : à vérifier. |

### 1.3 Messages système et multi-tours : ce qui existe

- Messages système en français : **aucun jeu dédié trouvé** (le sous-jeu `systemchats-30k` de smoltalk2 est en anglais). Voir §9.
- Multi-tours en français : OASST2 (arbres), `CATIE-AQ/everyday-conversations…` (3 à 4 échanges), Luth-2 (28 182 lignes de suivi d'instructions multi-tours, générées par `google/gemma-4-26b-a4b-it` d'après la fiche).

---

## 2. Chapitre 1.8 : aligner (préférences, DPO)

### 2.1 Jeux retenus

| Jeu | Licence (fiche) | Formulaire | Taille | Fabrication | Avis / réserves |
| --- | --- | --- | --- | --- | --- |
| [`CATIE-AQ/facebook-community-alignment-dataset_french_dpo`](https://huggingface.co/datasets/CATIE-AQ/facebook-community-alignment-dataset_french_dpo) | `cc-by-4.0` | non | 71 525 lignes ; 36 359 097 octets ; Parquet `prompt`/`chosen`/`rejected` | Partie française de [`facebook/community-alignment-dataset`](https://huggingface.co/datasets/facebook/community-alignment-dataset) (`cc-by-4.0`), dédoublonnée. **Choix humains** (plus de 3 500 annotateurs pour l'ensemble). Les réponses candidates viennent de **Llama-3.3-70B-Instruct** ([article](https://arxiv.org/abs/2507.09650), lu le 17/11/2026). La fiche Meta prévient que les invites écrites par les annotateurs peuvent être problématiques : filtrer. | Seul gros jeu de préférences français **d'origine** (pas traduit) et à choix humains. **Risque Llama** (§0) : le nom du modèle publié devrait commencer par « Llama », sauf à ne pas utiliser ce jeu. Il existe aussi une version `…_french_conversation` (11 433 lignes, `cc-by-4.0`). |
| [`AIffl/oasst2_french_dpo_pairs`](https://huggingface.co/datasets/AIffl/oasst2_french_dpo_pairs) | `apache-2.0` | non | 358 lignes ; 1 214 522 octets | Parties françaises d'OASST2, paires fabriquées d'après le rang humain des réponses | Petit mais humain et propre. On peut refaire soi-même le même calcul sur les 360 invites racines et leurs réponses classées (§1.1). |
| [`jpacifico/comparia-dpo-pairs-bt-13k`](https://huggingface.co/datasets/jpacifico/comparia-dpo-pairs-bt-13k) (et `…-6k`, 6 884 lignes) | `etalab-2.0` | non pour cette copie ; **les jeux d'origine** `ministere-culture/comparia-votes`, `-conversations`, `-reactions` sont `gated: auto` (formulaire) | 13 747 lignes ; 90 794 180 octets ; colonnes `prompt`, `chosen`, `rejected`, `chosen_model`, `rejected_model`, `skill_*` | Votes humains réels de la plateforme Compar:IA du ministère de la Culture, transformés en paires par un modèle de Bradley-Terry | Vrais votes, en français. Réserve : les réponses viennent de nombreux modèles, de licences variées (colonnes `chosen_model`/`rejected_model` pour filtrer). La copie est ouverte mais dérive d'un jeu à formulaire : je n'ai pas pu lire ses conditions. À garder en second choix. |

### 2.2 Autres jeux lus

| Jeu | Licence (fiche) | Taille | Fabrication | Verdict |
| --- | --- | --- | --- | --- |
| [`AIffl/french_hh_rlhf`](https://huggingface.co/datasets/AIffl/french_hh_rlhf) | `mit` | 169 352 lignes ; 468 896 364 octets | « french translation » de `Anthropic/hh-rlhf` (`mit`) ; méthode de traduction non documentée | Préférences humaines d'origine, mais traduites, contenu parfois choquant ; la fiche d'Anthropic dit que ces données ne servent pas à entraîner un agent de dialogue (préférences seulement). Usage secondaire. |
| [`CATIE-AQ/aya_french_dpo`](https://huggingface.co/datasets/CATIE-AQ/aya_french_dpo) | `apache-2.0` | 418 lignes | Partie française d'Aya, avec « rejeté = annotation originale, choisi = ré-annotation » | Minuscule et critère discutable. Écarter. |

### 2.3 Écartés ici

- [`AIffl/french_orca_dpo_pairs`](https://huggingface.co/datasets/AIffl/french_orca_dpo_pairs) (`apache-2.0`, 12 670 lignes) et [`jpacifico/french-orca-dpo-pairs-revised`](https://huggingface.co/datasets/jpacifico/french-orca-dpo-pairs-revised) : traductions de `Intel/orca_dpo_pairs` tiré d'OpenOrca, dont la fiche dit « ~1M GPT-4 completions, and ~3.2M GPT-3.5 completions » (`mit`). Sorties OpenAI : voir §0.
- [`jonasaise/dpo-french-interpreted`](https://huggingface.co/datasets/jonasaise/dpo-french-interpreted) (`mit`, 14 999 lignes) : la fiche dit que la réponse « rejetée » est **fabriquée exprès** par `kimi-k3` pour être une mauvaise traduction, et que la licence est « inherited from source (MIT or Apache 2.0) » sans nommer la source. Signal artificiel, provenance floue.
- Jeux Compar:IA d'origine et [`nvidia/Nemotron-Post-Training-Dataset-v2`](https://huggingface.co/datasets/nvidia/Nemotron-Post-Training-Dataset-v2) : formulaire d'accès (`gated: auto`).
- [`OpenLLM-France/Luciole-PostTraining-Dataset-1.1`](https://huggingface.co/datasets/OpenLLM-France/Luciole-PostTraining-Dataset-1.1) en DPO : paires générées par Qwen3-32B (choisie) contre Qwen3-0.6B (rejetée), « primarily English », partage identique. Pas de filtre de langue prêt à l'emploi.

---

## 3. Chapitre 1.9 : raisonner

### 3.1 Problèmes vérifiables (entraînement)

| Jeu | Licence (fiche) | Formulaire | Taille | Fabrication | Avis / réserves |
| --- | --- | --- | --- | --- | --- |
| [`kurakurai/Luth-2-Post-Training-RL`](https://huggingface.co/datasets/kurakurai/Luth-2-Post-Training-RL) | `cc-by-4.0` | non | 134 549 lignes ; 115 688 851 octets. Configs : `math` 20 000 ; `math_hard` 17 888 ; `code` 46 661 ; `if_single_turn` 25 000 ; `if_multi_turn` 25 000 | Invites traduites, **vérificateurs conservés** (`solution` pour les maths, `unit_tests` pour le code, `instruction_id_list`/`kwargs` pour le suivi d'instructions). Sources : Big-Math-RL-Verified, DAPO-Math-17k, OpenCodeInstruct, Dolci, smoltalk2, tulu-3. | Le plus complet pour une boucle « récompense vérifiable ». La fiche ne dit pas qui a traduit les invites (donc rien sur la qualité de traduction). Formes de maths : probablement trop dures pour 433 M ; commencer par un sous-ensemble court. |
| Luth-2 SFT, `domain = math` (428 031 lignes) | voir §1.1 | non | | Solutions détaillées avec raisonnement visible en français, sans balises `<think>` (vérifié sur les 100 premières lignes via le serveur de visionnage : aucune balise) | **Très long** (un exemple lu faisait plusieurs milliers de caractères et se perdait en tentatives). À filtrer fortement. |
| [`AIffl/grad_school_math_instructions_fr_Mixtral`](https://huggingface.co/datasets/AIffl/grad_school_math_instructions_fr_Mixtral) | `apache-2.0` | non | 2 762 lignes ; 3 890 946 octets | Invites du jeu Vigogne ; réponses par Mixtral-8x7B-Instruct « instead of GPT3.5 to make it open-source » | Petit ; réponses de Mixtral non vérifiées (peuvent être fausses). Secondaire. |

### 3.2 Traces de raisonnement en français

| Jeu | Licence (fiche) | Formulaire | Taille | Fabrication | Avis / réserves |
| --- | --- | --- | --- | --- | --- |
| [`CATIE-AQ/smoltalk2_aya_think_dataset_french_split`](https://huggingface.co/datasets/CATIE-AQ/smoltalk2_aya_think_dataset_french_split) | `apache-2.0` | non | deux configs de 1 393 lignes chacune (`english_raisonning` : raisonnement en anglais ; `french_raisonning` : raisonnement traduit en français) ; 7 638 948 octets au total | Partie française de `smoltalk2/aya_dataset_Qwen3_32B_think` : invites Aya, réponses et raisonnement générés par Qwen3-32B (Apache-2.0) ; raisonnement traduit par CATIE-AQ (traducteur non précisé dans ce que j'ai lu) | Seul jeu publié trouvé avec **question, raisonnement et réponse en français**, petit. Les questions sont des questions Aya générales, pas des problèmes de maths. |
| [`PleIAs/SYNTH`](https://huggingface.co/datasets/PleIAs/SYNTH) | `cc-by-4.0` (graines Wikipédia en `CC-BY-SA 4.0` d'après la colonne `seed_license`) | non | 79 648 272 échantillons annoncés, environ 20 % hors anglais (huit langues dont le français) ; 500 fichiers Parquet, environ 240 Go. La part française exacte n'est pas donnée | Synthétique à partir d'articles Wikipédia ; colonnes `language`, `exercise`, `synthetic_reasoning`, `synthetic_answer` ; générateurs « allowing for output reuse » | Contient de l'arithmétique et de la rédaction avec **traces de raisonnement** dans une syntaxe maison. **Exclut le code** (« Code generation » listé hors périmètre). À utiliser en téléchargeant quelques fichiers et en filtrant `language == "fr"` ; énorme sinon. |
| [`Cotum/MATH-500-french-thoughts`](https://huggingface.co/datasets/Cotum/MATH-500-french-thoughts) | `apache-2.0` | non | 500 lignes (test seulement) ; 1 257 768 octets | MATH-500 adapté en français par `bezir/MATH-500-multilingual`, raisonnements générés par DeepSeek-R1-Distill-Qwen-14B-AWQ | La fiche avoue que le raisonnement « should be in French but not always the case » et que la réponse prédite n'est pas toujours égale à la bonne. Évaluation ou exemple, pas entraînement. |

### 3.3 Générer soi-même (alternative quand les jeux publiés manquent)

| Piste | Détail | Statut |
| --- | --- | --- |
| Arithmétique et problèmes à étapes en français, générés par programme | Écrire un générateur Python : gabarits de phrases françaises (prénoms, unités, euros, accords), calcul exact par le programme, solution pas à pas produite par le même programme. La trace est **juste par construction** et sous licence du projet. | À faire (recommandé, voir §9). |
| [`open-thought/reasoning-gym`](https://github.com/open-thought/reasoning-gym) | `Apache-2.0` ; « more than 100 tasks » avec récompense vérifiable (`score_answer`). Je n'ai pas pu confirmer la langue des tâches (la page ne le dit pas) : à tester, probablement anglais. | Source d'idées de tâches et de vérificateurs ; traduire les gabarits à la main. |
| [`AIML-TUDA/SLR-Bench-French`](https://huggingface.co/datasets/AIML-TUDA/SLR-Bench-French) | `CC BY` (fiche : « [CC BY](https://creativecommons.org/licenses/by/4.0/) ») ; 38 506 lignes ; 534 369 906 octets | Raisonnement logique, invites **traduites**, vérification par un programme Prolog (SWI-Prolog requis). Intéressant mais loin du Python et de l'arithmétique ; non retenu. |

---

## 4. Chapitre 1.10 : coder (Python avec consignes en français)

### 4.1 Constat : il n'existe pas de jeu « consignes françaises + Python » dédié

Recherches sur HF (`code french`, `python francais`, `code alpaca fr`, `evol codealpaca french`, `coding french`, `code-fr`, 17/11/2026) : aucun résultat exploitable. Les deux seules sources françaises qui contiennent du code sont les jeux de Luth-2 ci-dessous.

### 4.2 Code avec consignes en français (retenu)

| Jeu | Licence (fiche) | Formulaire | Taille | Fabrication | Réserves |
| --- | --- | --- | --- | --- | --- |
| Luth-2 SFT, `domain = code` ([fiche](https://huggingface.co/datasets/kurakurai/Luth-2-Post-Training-SFT)) | `cc-by-4.0` (lignes issues de StackOverflow : `CC-BY-SA-4.0`) | non | 548 432 lignes | Invites de Nemotron-v2 et de Dolci, traduites ; réponses régénérées par Qwen | **Pas filtré par langage de programmation** d'après la fiche : filtrer sur le Python (présence de blocs ```python). |
| Luth-2 RL, config `code` ([fiche](https://huggingface.co/datasets/kurakurai/Luth-2-Post-Training-RL)) | `cc-by-4.0` | non | 46 661 lignes | Invites de `nvidia/OpenCodeInstruct` (`cc-by-4.0`) traduites, avec `unit_tests` | Pas de réponse de référence ; les tests permettent de vérifier en exécutant. La fiche d'OpenCodeInstruct ne nomme pas le modèle générateur (lue en entier). |

### 4.3 Code anglais permissif, à combiner avec des consignes traduites

| Jeu | Licence (fiche) | Taille | Fabrication | Avis |
| --- | --- | --- | --- | --- |
| [`bigcode/self-oss-instruct-sc2-exec-filter-50k`](https://huggingface.co/datasets/bigcode/self-oss-instruct-sc2-exec-filter-50k) | `odc-by` | 50 661 lignes ; 90 128 158 octets | Python seulement ; graines de fonctions de MultiPL-T ; réponses « execution-validated » (filtrées par exécution) ; données d'alignement de StarCoder2-Instruct | **Meilleur point de départ** à traduire : Python, vérifié par exécution, licence claire. |
| [`OpenCoder-LLM/opc-sft-stage2`](https://huggingface.co/datasets/OpenCoder-LLM/opc-sft-stage2), sous-ensemble `educational_instruct` seulement | `mit` | 436 347 lignes pour les quatre sous-ensembles ; 537 378 084 octets | `educational_instruct` : triplets (instruction, code, test) validés par un compilateur Python | Les autres sous-ensembles reprennent Magicoder-Evol-Instruct (dérivé de sorties OpenAI) et McEval : à ne pas prendre. |
| [`nvidia/OpenCodeInstruct`](https://huggingface.co/datasets/nvidia/OpenCodeInstruct) | `cc-by-4.0` | environ 5 M de lignes annoncées ; 1,78 Go pour les 1,4 M premières lignes indexées | Synthétique, avec `unit_tests` et résultat d'exécution | Déjà traduit en partie par Luth-2 (46 661 lignes). Langages mélangés à filtrer. |
| `nickrosh/Evol-Instruct-Code-80k-v1`, `iamtarun/python_code_instructions_18k_alpaca`, `ise-uiuc/Magicoder-OSS-Instruct-75K` | NC-SA / aucune licence dans l'en-tête / MIT mais « generated by `gpt-3.5-turbo-1106` » avec renvoi à la politique d'usage d'OpenAI | | | **Écartés** (§7). |

### 4.4 Évaluation de code par exécution

| Jeu | Licence (fiche) | Formulaire | Taille | Version française ? | Remarques |
| --- | --- | --- | --- | --- | --- |
| [`openai/openai_humaneval`](https://huggingface.co/datasets/openai/openai_humaneval) | `mit` | non | 164 lignes ; 83 920 octets | non | Référence anglaise. |
| [`evalplus/humanevalplus`](https://huggingface.co/datasets/evalplus/humanevalplus) | `apache-2.0` | non | 164 lignes ; 2 902 210 octets | non | Plus de tests que HumanEval. |
| [`google-research-datasets/mbpp`](https://huggingface.co/datasets/google-research-datasets/mbpp) | `cc-by-4.0` | non | 1 401 lignes ; 351 491 octets | non | |
| [`evalplus/mbppplus`](https://huggingface.co/datasets/evalplus/mbppplus) | `apache-2.0` | non | 378 lignes ; 1 129 135 octets | non | |
| [`ellamind/humaneval-multilingual`](https://huggingface.co/datasets/ellamind/humaneval-multilingual), config `fra` | **aucune** (fiche sans licence ni texte) | non | 142 lignes (sur 164 ; les 22 manquantes ne sont pas expliquées) ; 104 224 octets | **oui**, docstrings en français | Traduction par modèle (colonnes `translation_confidence` : 104 « confident », 38 « direct » ; `flag_for_review` : aucun marqué ; le modèle traducteur n'est pas nommé). Dérive de HumanEval (`mit`). Licence à demander. |
| [`ellamind/mbpp-multilingual`](https://huggingface.co/datasets/ellamind/mbpp-multilingual), config `fra` | **aucune** | non | **100 lignes seulement** (la config allemande en a 398) ; 39 285 octets | **oui** | Même méthode et mêmes réserves. Trop petit pour un score fiable. |
| [`kurakurai/MBPP-Plus-FR`](https://huggingface.co/datasets/kurakurai/MBPP-Plus-FR) | **aucune** (pas de texte de fiche) | non | 378 lignes ; 1 165 843 octets | **oui**, `prompt` en français, tests inchangés | Méthode de traduction non documentée. Dérive de MBPP+ (`apache-2.0`). C'est le banc de code français utilisé par Luth-2 d'après le tableau de sa fiche (« MBPP+ », mais le dépôt GitHub de Luth-2 ne donne aucun identifiant HF d'évaluation). |
| [`floatai/HumanEval-XL`](https://huggingface.co/datasets/floatai/HumanEval-XL) | `apache-2.0` | non | 22 080 prompts annoncés (23 langues naturelles × 12 langages de programmation) soit 80 par couple, dont 80 pour Python en français (calcul : 22 080 / (23 × 12)) ; pas de fichier de données sur HF | **oui** (français inclus) | Le dépôt HF n'a qu'un script de chargement `HumanEval-XL.py` qui télécharge les données depuis GitHub ([FloatAI/humaneval-xl](https://github.com/FloatAI/humaneval-xl)) : les versions récentes de `datasets` refusent les scripts, télécharger directement. Méthode de traduction non lue (le résumé de l'article ne la donne pas). |

Pour un modèle de 433 M, prévoir un bac à sable (processus isolé, délai maximal) pour exécuter le code généré.

---

## 5. Évaluations en français, chapitre par chapitre

| Chapitre | Jeu | Licence (fiche) | Formulaire | Taille | Méthode | Réserves |
| --- | --- | --- | --- | --- | --- | --- |
| 1.7 suivi d'instructions | [`kurakurai/IFEval-FR`](https://huggingface.co/datasets/kurakurai/IFEval-FR) | `apache-2.0` | non | 235 prompts ; 55 836 octets | Partie française de M-IFEval ([dépôt](https://github.com/lightblue-tech/M-IFEval), Apache-2.0, article [arXiv 2502.04688](https://arxiv.org/abs/2502.04688)) : jeu « not simply a translation » avec instructions propres à la langue, un locuteur natif par langue ; relu et nettoyé « with Claude Opus 4.8 » d'après la fiche | **Meilleur choix** : même format que `google/IFEval` (`instruction_id_list`, `kwargs`), vérificateurs préfixés `fr:`. |
| 1.7 suivi d'instructions | [`jzhang86/fr_ifeval`](https://huggingface.co/datasets/jzhang86/fr_ifeval) | `apache-2.0` | non | 541 lignes ; 225 798 octets | Traduction de `jzhang86/corrected_ifeval` : « GPT-4o is used for translation, every data point is human checked » | Utilisable en évaluation. Garde des consignes propres à l'anglais traduites mot à mot. |
| 1.7 suivi d'instructions | `le-leadboard/IFEval-fr` | **aucune** | non | 515 lignes | Fiche générique, exemple de la fiche qui ne correspond pas aux colonnes réelles (`prompt`, `categories`, `kwargs`) | Écarté : fiche peu fiable. |
| 1.7 conversation | [`bofenghuang/mt-bench-french`](https://huggingface.co/datasets/bofenghuang/mt-bench-french) | `apache-2.0` | non | 80 questions multi-tours ; 144 800 octets | Traduction **avec relecture humaine approfondie**, réponses de référence corrigées à la main (maths, raisonnement, code) | Le juge officiel est **GPT-4o** (service payant d'OpenAI, utilisé pour noter, pas pour entraîner). Alternative à tester : un juge ouvert (Qwen3) en le disant clairement. 80 questions : bruit élevé. |
| 1.7 conversation | [`Vicomtech/just-eval-instruct-fr`](https://huggingface.co/datasets/Vicomtech/just-eval-instruct-fr) | `mit` | non | 1 000 lignes ; 316 259 octets | Adaptation française, « manually revised » d'après la fiche, de `re-align/just-eval-instruct` | Complément ; juge à définir. |
| 1.9 raisonnement | [`juletxara/mgsm`](https://huggingface.co/datasets/juletxara/mgsm), config `fr` | `cc-by-sa-4.0` | non | 250 test + 8 exemples d'entraînement (chaîne de pensée) ; 75 231 octets | « manually translating 250 grade-school math problems from the GSM8K dataset » ([article](https://arxiv.org/abs/2210.03057)) | Référence humaine. Partage identique. |
| 1.9 raisonnement | [`lightonai/mgsm-rev2`](https://huggingface.co/datasets/lightonai/mgsm-rev2), config `fr` | `cc-by-sa-4.0` | non | 250 lignes ; 71 410 octets | Version corrigée de MGSM : « we corrected two erroneous English questions and rephrased others to remove ambiguity », retraduite avec Gemini ([dépôt Google](https://github.com/google-research-datasets/MGSM-Rev2), lu le 17/11/2026) | À préférer à MGSM seul. |
| 1.9 raisonnement | [`OpenLLM-France/mgsm-rev2-with-train`](https://huggingface.co/datasets/OpenLLM-France/mgsm-rev2-with-train), config `fr` | `cc-by-sa-4.0` | non | 250 test + 8 train ; 76 398 octets | Réunit mgsm-rev2 (test) et les 8 exemples de MGSM | Pratique : un seul chargement. |
| 1.9 raisonnement | [`cmh/gsm8k-platinum_fr`](https://huggingface.co/datasets/cmh/gsm8k-platinum_fr) | `mit` | non | 1 196 lignes ; 790 007 octets ; colonnes `question`, `answer`, `question_original`, `answer_original` | « French translation » de GSM8K-Platinum (test GSM8K nettoyé du MIT) ; la fiche **ne dit pas** comment ni par qui la traduction a été faite | Plus grand que MGSM, traduction non documentée : à relire par échantillon avant de s'y fier. |
| 1.9 raisonnement | [`Cotum/MATH-500-french-thoughts`](https://huggingface.co/datasets/Cotum/MATH-500-french-thoughts) | `apache-2.0` | non | 500 lignes | voir §3.2 | Trop dur pour 433 M ; test de plafond seulement. |
| 1.10 code | voir §4.4 | | | | | |

Pas d'évaluation française de préférences sans juge trouvée en libre accès propre (le seul candidat vu, `Svngoku/french-multilingual-reward-bench-dpo`, `mit`, 8 108 lignes, n'a pas été lu en détail : méthode inconnue).

---

## 6. Jeux « originaux français » à connaître

Peu de données **écrites** en français existent sous licence claire : Aya (humain), OASST2 (humain), les choix humains de Community Alignment (français d'origine, réponses de Llama-3.3), les votes Compar:IA. Tout le reste est traduit ou synthétique.

---

## 7. Jeux à écarter, et pourquoi

| Jeu | Licence annoncée | Raison de l'écarter |
| --- | --- | --- |
| [`angeluriot/french_instruct`](https://huggingface.co/datasets/angeluriot/french_instruct) (275 600 lignes) | `mit` | Mélange de sources dont `nickrosh/Evol-Instruct-Code-80k-v1` (**`cc-by-nc-sa-4.0`**, 56 747 documents), `tatsu-lab/alpaca` (**`cc-by-nc-4.0`**), HC3 (`cc-by-sa-4.0`), Dolly (`cc-by-sa-3.0`), ShareGPT ; « some of which are translated from English to French using the ChatGPT API ». L'étiquette MIT ne couvre pas les sources. |
| [`MaziyarPanahi/french_instruct_sharegpt`](https://huggingface.co/datasets/MaziyarPanahi/french_instruct_sharegpt), [`…_human_sharegpt`](https://huggingface.co/datasets/MaziyarPanahi/french_instruct_human_sharegpt) | aucune | Reformatage de French Instruct, mêmes problèmes, plus aucune licence. |
| [`jpacifico/French-Alpaca-dataset-Instruct-110K`](https://huggingface.co/datasets/jpacifico/French-Alpaca-dataset-Instruct-110K) | `apache-2.0` | « generated by OpenAI GPT-3.5-turbo » (fiche). Version 55K : pas de licence. |
| [`legmlai/openhermes-fr`](https://huggingface.co/datasets/legmlai/openhermes-fr) (799 875 lignes) | `odc-by` | Traduit et réponses **distillées de GPT-4o** (fiche). Et repris dans `luth-sft` v1. |
| [`FreedomIntelligence/evol-instruct-french`](https://huggingface.co/datasets/FreedomIntelligence/evol-instruct-french) | aucune | Pas de licence, dérivé d'Evol-Instruct (sorties OpenAI) ; méthode non documentée. |
| [`Volko76/smol-smoltalk-french-instruction-dataset`](https://huggingface.co/datasets/Volko76/smol-smoltalk-french-instruction-dataset) | aucune | Reformatage de `vonewman/french-instruction-dataset` (provenance non documentée dans ce que j'ai lu). |
| [`bofenghuang/magpie-fr`](https://huggingface.co/datasets/bofenghuang/magpie-fr) (802 339 lignes) | aucune | Aucune fiche ; sorties de Llama-3.1 (nom des dossiers). |
| [`croissantllm/CroissantLLM-2201-sft`](https://huggingface.co/datasets/croissantllm/CroissantLLM-2201-sft) (294 220 lignes) | aucune | La fiche ne contient qu'une citation ; aucune licence ni méthode. |
| [`toroe/Soofi-Think-SFT-V2-firsthalf-FR`](https://huggingface.co/datasets/toroe/Soofi-Think-SFT-V2-firsthalf-FR) (2 373 885 lignes, 30,8 Go) | `other` (sans texte) | Traduit par Qwen3-32B, mais mélange de nombreuses sources (dont ShareGPT, SlimOrca, WildChat R1) sous licences variées. Énorme et sans licence lisible. |
| [`OpenLLM-France/Lucie-Training-Dataset`](https://huggingface.co/datasets/OpenLLM-France/Lucie-Training-Dataset), `Claire-Dialogue-French-0.1` | `cc-by-nc-sa-4.0` | Non commercial ; Claire en plus avec formulaire (`gated: auto`). |
| [`jonasaise/dpo-french-interpreted`](https://huggingface.co/datasets/jonasaise/dpo-french-interpreted) | `mit` | Rejetées fabriquées exprès ; provenance floue (§2.3). |
| French Orca DPO (deux versions) | `apache-2.0` | Sorties GPT-3.5/GPT-4 d'OpenOrca (§2.3). |
| [`ise-uiuc/Magicoder-OSS-Instruct-75K`](https://huggingface.co/datasets/ise-uiuc/Magicoder-OSS-Instruct-75K) | `mit` | Fiche : « generated by `gpt-3.5-turbo-1106` … pay attention to OpenAI's usage policy ». |
| `nickrosh/Evol-Instruct-Code-80k-v1` | `cc-by-nc-sa-4.0` | Non commercial. |
| [`le-leadboard/MATH_LVL5_fr`](https://huggingface.co/datasets/le-leadboard/MATH_LVL5_fr), [`le-leadboard/IFEval-fr`](https://huggingface.co/datasets/le-leadboard/IFEval-fr) | `apache-2.0` / aucune | Fiches génériques, tailles et exemples incohérents avec ce qu'annonce le titre (MATH niveau 5 : 2 300 lignes réparties train/test, exemple de niveau facile). Méthode non documentée. |
| `nvidia/Nemotron-Post-Training-Dataset-v2`, Compar:IA d'origine, `GAIR/lima`, `SynthLabsAI/Big-Math-RL-Verified` | divers | Formulaire d'accès (`gated`). |
| [`kurakurai/luth-sft`](https://huggingface.co/datasets/kurakurai/luth-sft) en entier | `odc-by` | Contient `luth_openhermes` (GPT-4o) et `luth_croissantllm` (sans licence) ; ne prendre que les parties saines (§1.2). |

---

## 8. Question de licence à trancher : le partage identique (CC BY-SA)

Les jeux retenus ne sont pas tous sous la même licence. Les `cc-by-4.0` (Luth-2 SFT et RL, Community Alignment), `apache-2.0` (Aya, OASST2, Smoltalk) et `odc-by` (self-oss-instruct, scholar) demandent surtout de citer la source. Les `cc-by-sa-4.0` (MGSM, mgsm-rev2, Luciole `hardcoded_fr`, lignes StackOverflow de Luth-2) demandent que **l'adaptation** soit partagée sous la même licence. Que cela s'applique ou non aux poids d'un modèle entraîné n'est pas tranché dans les fiches que j'ai lues, et je n'ai pas lu de texte juridique. Pour limiter le risque : utiliser MGSM et mgsm-rev2 **en évaluation seulement** (pas dans les données d'entraînement) et écarter les lignes StackOverflow de Luth-2 quand la colonne `source`/`domain` permet de les repérer.

---

## 9. Trous, et quoi faire à la place

| Trou | Pourquoi | À faire |
| --- | --- | --- |
| Messages système en français | Aucun jeu trouvé ; `systemchats-30k` est en anglais | Générer : demander à Qwen3 (Apache-2.0) d'écrire des messages système français variés, puis le même modèle répond aux invites existantes de Luth-2/OASST2 en suivant le message système ; filtrer par un contrôle de format. |
| Python avec consignes françaises, à grande échelle et vérifié | Aucun jeu dédié | Traduire les **consignes** de `bigcode/self-oss-instruct-sc2-exec-filter-50k` et de `opc-sft-stage2/educational_instruct` avec Qwen3, garder le code et les tests tels quels, et **réexécuter** les tests pour jeter ce qui casse. Compléter avec le sous-ensemble Python de Luth-2 (SFT et RL). |
| Maths de niveau « petit modèle » en français avec traces courtes | Les traces de Luth-2 sont très longues ; les jeux courts français sont minuscules | Générateur maison (§3.3) : gabarits français, solution pas à pas produite par le programme, vérification exacte. |
| Préférences françaises à licence propre | La plus grosse source (Community Alignment) a des réponses Llama ; les paires Orca sont OpenAI ; les paires Luciole sont anglaises | Fabriquer des paires « delta » : choisie = réponse d'un modèle ouvert plus fort (Qwen3-32B), rejetée = réponse du modèle SFT de « Ton IA » (ou d'un plus petit modèle ouvert) à la même invite en français ; vérifier au moins les maths et le code par exécution. Compléter avec `AIffl/oasst2_french_dpo_pairs` (358) et le calcul de rang sur OASST2. |
| MT-Bench français sans GPT-4o | Le juge officiel est payant | Juge ouvert, à mentionner explicitement dans le chapitre ; ne comparer que des résultats obtenus avec le même juge. |
| Banc de code français avec licence claire | ellamind et MBPP-Plus-FR n'ont pas de licence ; HumanEval-XL a une méthode non lue | Demander la licence aux auteurs, ou traduire soi-même les 164 énoncés de HumanEval (`mit`) et garder les tests. Prévoir de publier cette traduction avec la licence du jeu d'origine. |
| Raisonnement en français vérifié par la machine à grande échelle | Rien de publié avec solution française validée | Traduire les invites de `Luth-2-Post-Training-RL` (déjà traduites) et ne conserver que les réponses dont la réponse finale correspond à `solution`. |

---

## Choix recommandés pour ton IA

Principe : des données **sous licence claire (CC-BY-4.0, Apache-2.0, ODC-By, MIT)**, des réponses générées par des modèles **Apache-2.0** (Qwen3, Mixtral) et jamais par GPT ou Llama, du Python **vérifié par exécution**, des évaluations indépendantes des données d'entraînement. Les mélanges ci-dessous donnent des **sources**, pas des quantités : les proportions se décident après un premier essai.

### Chapitre 1.7 : converser

- **Noyau** : `kurakurai/Luth-2-Post-Training-SFT`, domaines `knowledge` et `if` (et `code` pour le chapitre 1.10), générateurs Qwen seulement, sans `tool_call`, avec filtre de longueur (la moyenne est d'environ 1 580 tokens par exemple, calcul ici).
- **Humain** : `CohereLabs/aya_dataset` (français, Apache-2.0) et `OpenAssistant/oasst2` (français, Apache-2.0) pour la voix et les vrais multi-tours.
- **Politesse de base** : `CATIE-AQ/everyday-conversations-llama3.1-2k-in-french` seulement si on accepte la clause Llama ; sinon la regénérer avec Qwen3 à partir des mêmes sujets.
- **Identité** : `hardcoded_fr` de Luciole (962 lignes), ou écrire ses propres lignes.
- **Évaluation** : `kurakurai/IFEval-FR` (235, Apache-2.0) ; `bofenghuang/mt-bench-french` (80 questions, Apache-2.0) avec un juge ouvert annoncé comme tel.
- **À écarter** : tout ce qui est « French Alpaca », OpenHermes-fr, french_instruct, magpie-fr, CroissantLLM-SFT.

### Chapitre 1.8 : aligner

- **Option sûre** : paires « delta » fabriquées par les lecteurs (Qwen3-32B choisi contre petit modèle rejeté, ou contre le SFT de Ton IA), plus `AIffl/oasst2_french_dpo_pairs` (358) comme seul jeu humain propre.
- **Option riche, avec réserve de nom** : `CATIE-AQ/facebook-community-alignment-dataset_french_dpo` (71 525, CC-BY-4.0, choix humains) ; seulement si l'on accepte que le nom du modèle commence par « Llama » (§0). À décider avant la vague.
- **Deuxième choix** : `jpacifico/comparia-dpo-pairs-bt-13k` en ne gardant que les paires dont `chosen_model` et `rejected_model` sont des modèles ouverts à licence permissive.
- **À écarter** : paires Orca françaises, `jonasaise/dpo-french-interpreted`.

### Chapitre 1.9 : raisonner

- **Entraînement** : un générateur Python maison de problèmes en français (arithmétique, problèmes à étapes, solution pas à pas calculée par le programme) ; en complément, `kurakurai/Luth-2-Post-Training-RL`, configs `math` et `math_hard` pour la récompense vérifiable (la solution est conservée), et les maths de Luth-2 SFT après un filtre de longueur sévère.
- **Traces en français** : `CATIE-AQ/smoltalk2_aya_think_dataset_french_split`, config `french_raisonning` (1 393 lignes) comme modèle de format, et quelques fichiers de `PleIAs/SYNTH` filtrés sur `language == "fr"`.
- **Évaluation** : `lightonai/mgsm-rev2` (config `fr`, 250) avec les 8 exemples de `OpenLLM-France/mgsm-rev2-with-train`, et `cmh/gsm8k-platinum_fr` (1 196) après vérification par échantillon. MGSM reste hors des données d'entraînement (CC-BY-SA).
- **À écarter** : `le-leadboard/MATH_LVL5_fr`, `Soofi-Think-…-FR`.

### Chapitre 1.10 : coder

- **Entraînement** : Python de Luth-2 SFT (domaine `code`, blocs Python) ; Luth-2 RL config `code` (46 661, avec tests) ; et le jeu à fabriquer : consignes françaises de `bigcode/self-oss-instruct-sc2-exec-filter-50k` (50 661) et de `opc-sft-stage2/educational_instruct`, traduites par Qwen3, code et tests conservés, tests réexécutés.
- **Évaluation** : `openai/openai_humaneval` (MIT) et `evalplus/mbppplus` (Apache-2.0) comme références anglaises ; pour le français, `floatai/HumanEval-XL` (Apache-2.0, 80 problèmes Python en français) ou une traduction maison des 164 énoncés de HumanEval ; `ellamind/*` et `kurakurai/MBPP-Plus-FR` seulement en contrôle secondaire, tant qu'ils n'ont pas de licence.
- **À écarter** : Magicoder-OSS-Instruct, Evol-Instruct-Code, `python_code_instructions_18k_alpaca`.

### Deux décisions à prendre avant d'écrire les chapitres

1. Accepte-t-on une dépendance à Llama (nom du modèle) pour obtenir les 71 525 paires de préférences humaines ?
2. Les jeux `cc-by-sa-4.0` (MGSM) restent-ils réservés à l'évaluation ?
