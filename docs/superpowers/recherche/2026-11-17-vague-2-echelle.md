# Vague 2 de La Forge IA : ce qu'on peut attendre d'un petit modèle, et l'échelle des grands labos

Recherche du 17/11/2026. Toutes les sources ont été lues le 17/11/2026.

## Lire ceci d'abord

- Les pages ont été lues avec un outil qui résume le texte. Les chiffres ci-dessous viennent de ces lectures. Avant de les recopier dans un chapitre, il faut les revérifier sur la source primaire (lien donné à chaque ligne).
- Étiquettes : **publié** = chiffre donné par les auteurs ; **dérivé** = calcul de ma part à partir de chiffres publiés (le calcul est écrit) ; **tiers** = presse ou résumé, pas la source primaire ; **non trouvé** = je n'ai pas réussi à le lire, je n'invente rien.
- Point de comparaison de « Ton IA » : 433,6 M de paramètres, 8,67 Md de jetons, 139 h sur une carte.

### L'écart de données d'entraînement (dérivé, à dire sur le site)

| Modèle | Paramètres | Jetons de pré-entraînement | Rapport à Ton IA (8,67 Md) |
| --- | --- | --- | --- |
| Ton IA | 433,6 M | 8,67 Md | 1 |
| nanochat d20 | 561 M | 11,2 Md | environ 1,3 fois (11,22 / 8,67) |
| SmolLM2-135M | 135 M | 2 000 Md (2 T) | environ 230 fois |
| SmolLM2-360M | 360 M | 4 000 Md (4 T) | environ 460 fois |
| Qwen2.5-Coder 0.5B | 0,5 Md | 5 500 Md (5,5 T, le texte dit aussi 5,2 T) | environ 630 fois |

Conséquence : le seul comparable proche en données est nanochat d20. Les autres petits modèles ont vu des centaines de fois plus de texte. Leurs résultats montrent un plafond du possible, pas ce que Ton IA obtiendra.

---

## A. Ce qu'on peut honnêtement attendre d'un petit modèle

### A1. nanochat (Karpathy), le comparable le plus proche

Source primaire : discussions GitHub de Karpathy.
- d20 : <https://github.com/karpathy/nanochat/discussions/1>
- d32 : <https://github.com/karpathy/nanochat/discussions/8>
- README : <https://github.com/karpathy/nanochat>

| Modèle | Paramètres | Jetons | Matériel et durée | Étiquette |
| --- | --- | --- | --- | --- |
| d20 (« speedrun ») | 560 988 160 | 11 219 763 200 | 8 H100, 3 h 51 jusqu'à la SFT, environ 92 $ ; le RL pousse vers 5 h | publié |
| d32 (« palier 1000 $ ») | 1 879 048 192 | 37 580 963 840 (20 jetons par paramètre) | 8 H100, 1849 min (environ 30,8 h) ; Karpathy pense « plutôt 800 $ » | publié |

Résultats (fractions de 1, comme publiées ; MID = après la phase intermédiaire qui introduit déjà le format chat) :

| Test | d20 MID | d20 SFT | d20 RL | d32 MID | d32 SFT | d32 RL |
| --- | --- | --- | --- | --- | --- | --- |
| ARC-Challenge | 0,2875 | 0,2807 | non fait | 0,4787 | 0,4991 | non fait |
| ARC-Easy | 0,3561 | 0,3876 | non fait | 0,6233 | 0,6797 | non fait |
| GSM8K | 0,0250 | 0,0455 | 0,0758 | 0,1099 | 0,1274 | 0,1994 |
| HumanEval | 0,0671 | 0,0854 | non fait | 0,1098 | 0,1280 | non fait |
| MMLU | 0,3111 | 0,3151 | non fait | 0,3896 | 0,4049 | non fait |
| ChatCORE | 0,0730 | 0,0884 | non fait | 0,2417 | 0,2734 | non fait |

CORE de base : d20 0,2219 ; d32 0,3168.

Ce qu'on en retient (dérivé des chiffres ci-dessus) :
- d20, GSM8K : 2,5 % puis 4,55 % après la SFT puis 7,58 % après le RL. C'est une progression réelle mais sur un score très bas : le modèle se trompe plus de 9 fois sur 10.
- d20, ARC-Challenge : 28,75 % puis 28,07 % après la SFT. La SFT n'apporte rien sur ce test, qui reste près du hasard (25 %). C'est exactement le cas de Ton IA (25,1 %).
- d32 (3,5 fois plus gros), GSM8K : 11,0 % puis 12,7 % puis 19,9 % après le RL.
- Incertain : le README actuel de nanochat ne donne aucun score GSM8K. Le dépôt a évolué depuis (classement « temps pour égaler GPT-2 », d24 à d26, dernières entrées de mars 2026). Je n'ai pas trouvé de chiffres plus récents de SFT ou de RL.
- Incertain : le fichier de la discussion d20 ne dit pas quel état du code a produit ces chiffres. Des reproductions communautaires donnent des valeurs voisines mais pas identiques (non retenues, tiers).

### A2. SmolLM2 petits (Hugging Face)

Sources primaires : fiches de modèle.
- 135M : <https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct>
- 360M : <https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct>
- Article : <https://arxiv.org/abs/2502.02737> (le corps de l'article n'a pas pu être lu ; la page d'abstract ne parle que du modèle 1,7 Md)

Entraînement publié : 135M sur 2 T de jetons, 360M sur 4 T, 64 H100, SFT sur « smol-smoltalk » puis DPO sur UltraFeedback. Aucune taille de jeu SFT ou DPO n'est donnée sur les fiches.

| Test | 135M base | 135M Instruct | 360M Instruct | Qwen2.5-0.5B-Instruct (même fiche) |
| --- | --- | --- | --- | --- |
| HellaSwag | 42,1 | 40,9 | 52,1 | 48,0 |
| ARC (moyenne) | 43,9 | 37,3 | 43,7 | 37,3 |
| MMLU (cloze) | 31,5 | 29,3 | 32,8 | 31,7 |
| GSM8K (5 coups) | 1,4 | 1,4 | 7,43 | 26,8 |
| IFEval (moyenne prompt/consigne) | non applicable | 29,9 | 41,0 | 31,6 |
| MT-Bench | non applicable | 19,8 (sic, échelle différente de la ligne 360M) | 3,66 | 4,16 |

À retenir (dérivé) :
- Pour le 135M, passer de la base à l'instruct fait baisser HellaSwag (42,1 vers 40,9), ARC (43,9 vers 37,3) et MMLU. La SFT et la DPO apprennent à suivre des consignes mais peuvent coûter un peu sur les tests de bon sens.
- GSM8K reste à 1,4 % pour le 135M après tout l'affinage : pas de math en dessous de cette taille avec ces données.
- Le gain visible est sur IFEval (consignes simples, vérifiables) : 29,9 contre 17,2 pour l'ancien SmolLM-135M-Instruct. Il vient d'une meilleure base et de meilleures données, pas seulement de l'étape.
- Incertain : MT-Bench du 135M est affiché « 19,8 » sur la fiche contre « 3,66 » pour le 360M. Les échelles ne sont visiblement pas les mêmes ; ne pas comparer.
- Incertain : je n'ai pas de ligne « avant DPO / après DPO » isolée. L'effet de la DPO seule sur un petit modèle n'est pas publié ici.

SmolLM3 (<https://huggingface.co/blog/smollm3>) fait 3 Md de paramètres : il n'est pas petit au sens de la vague 2. Je ne l'utilise que pour l'échelle (partie B). Chiffres lus : 11 T de jetons, 384 H100 pendant 24 jours ; mode raisonnement contre mode sans raisonnement : AIME 2025 36,7 % contre 9,3 %, LiveCodeBench 30,0 % contre 15,2 %.

### A3. Qwen2.5 petits (Alibaba)

Source primaire : rapport Qwen2.5, <https://arxiv.org/abs/2412.15115> (lu en version HTML). Les évaluations de base et d'instruct n'ont pas les mêmes réglages, donc les écarts mélangent post-entraînement et protocole.

| Test | 0.5B base | 0.5B Instruct | 1.5B base | 1.5B Instruct |
| --- | --- | --- | --- | --- |
| MATH | 19,5 | 34,4 | 35,0 | 55,2 |
| GSM8K | 41,6 | 49,6 | 68,5 | 73,2 |
| HumanEval | 30,5 | 35,4 | 37,2 | 61,6 |
| IFEval | non rapporté | 27,9 | non rapporté | 42,5 |

Note : la fiche SmolLM2 donne 26,8 pour le GSM8K de Qwen2.5-0.5B-Instruct, le rapport Qwen donne 49,6. Même modèle, protocoles différents. Toujours citer le protocole avec le chiffre.

### A4. Qwen2.5-Coder petits

Source primaire : <https://arxiv.org/abs/2409.12186> (version HTML).

| Modèle | HumanEval | HumanEval+ | MBPP (instruct) | MBPP+ (instruct) |
| --- | --- | --- | --- | --- |
| 0.5B base | 28,0 | 23,8 | illisible | illisible |
| 0.5B Instruct | 61,6 | 57,3 | 52,4 | 43,7 |
| 1.5B base | 43,9 | 36,6 | illisible | illisible |
| 1.5B Instruct | 70,7 | 66,5 | 69,2 | 59,4 |

Pré-entraînement : 5,5 T de jetons dont une grande part de code. Instruction : « dizaines de millions » d'exemples peu qualitatifs, puis « millions » de meilleure qualité ; DPO avec retour d'exécution dans un bac à sable. Aucun compte exact publié. À comparer avec nanochat d20 : HumanEval 6,7 % puis 8,5 % après SFT. Un facteur de 7 à 9 sépare les deux, et l'écart de données de pré-entraînement est de l'ordre de 500 fois.

### A5. Le RL sur de très petits modèles : où ça ne décolle pas

| Résultat | Chiffres | Source | Étiquette |
| --- | --- | --- | --- |
| TinyZero (réplique « R1-Zero », tâche Countdown) : le Qwen2.5-0.5B base n'apprend pas à raisonner ; à partir de 1,5 Md, des comportements de recherche, vérification et révision apparaissent ; 3 Md « développe un raisonnement sophistiqué » ; coût annoncé « moins de 30 $ » | aucun score chiffré dans le README | <https://github.com/Jiayi-Pan/TinyZero> | publié (README ; dépôt plus maintenu) |
| Étude de petits modèles de 0,5 Md : Qwen2.5-0.5B-Instruct de 45,5 % à 54,0 % de GSM8K avec le RL ; base + RL 34,2 % ; base + SFT 21,6 % ; MATH500 instruct 31,4 % puis 32,4 % ; OlympiadBench 6,2 % puis 7,6 % ; certains mélanges (SFT puis RL, distillation puis RL) s'effondrent ; 8 H100 ; environ 7 000 problèmes d'entraînement | voir texte | <https://arxiv.org/abs/2506.13404> (tableau lu en HTML : <https://arxiv.org/html/2506.13404v3>) | publié ; le texte et le tableau ne s'accordent pas sur quels mélanges s'effondrent |
| RL sans récompense externe (auto-évaluation) sur Qwen2.5-0.5B base : MATH500 23,4 au départ, baisse avec Intuitor, effondrement complet avec TTRL ; gains sur le 7B | | <https://arxiv.org/pdf/2511.04902> | tiers (lu via résumé de recherche) |
| RL d'un 1,5 Md déjà distillé : AIME24 28,8 % puis 30 % à 46,7 % selon l'essai ; AMC23 62,9 % puis 70 % à 80 % ; 4 GPU A40, 24 h, environ 42 $, 7 000 à 18 615 exemples ; dégradation si on entraîne trop longtemps ; AIME24 n'a que 30 problèmes, donc grosse incertitude | | <https://arxiv.org/abs/2503.16219> | publié |

À retenir (dérivé) :
- Les gains de RL sur les petits modèles viennent presque toujours d'un modèle déjà fortement entraîné sur des maths (Qwen) ou déjà distillé depuis un grand modèle de raisonnement. Aucun de ces points de départ ne ressemble à Ton IA.
- Le seul exemple de RL à partir d'un modèle entraîné sur peu de données est nanochat d20 : GSM8K de 4,55 % à 7,58 %. C'est le chiffre honnête à montrer.
- Seuil de taille : le seul énoncé net que j'ai lu est celui de TinyZero (0,5 Md échoue, 1,5 Md commence, 3 Md réussit) sur une tâche étroite. Ce n'est pas une loi générale. Je n'ai pas trouvé d'article qui mesure ce seuil proprement.

### A6. Petits modèles « tout court »

| Fait | Source | Étiquette |
| --- | --- | --- |
| TinyStories : des modèles de moins de 10 M de paramètres écrivent des histoires cohérentes, mais sur un vocabulaire d'enfant de 3 ans ; la grammaire s'apprend tôt, la cohérence et la créativité plus tard ; un modèle de 1 M à 8 couches ne répond à aucune question factuelle ; une seule couche suit mal les consignes, deux couches un peu | <https://arxiv.org/abs/2305.07759> | publié |
| Gemma 3 270M instruct : IFEval 51,2 % annoncé par Google, contre Gemma 3 1B à 80,2 % | VentureBeat, The Register ; résultats internes non vérifiés | tiers |
| Pythia, Mistral, StarCoder2-Instruct, Qwen3 0.6B en détail | non lus dans cette recherche | non trouvé |

---

## B. « Et chez un grand labo ? », étape par étape

### B1. SFT (chapitre 1.7)

| Qui | Quantité de données | Calcul | Source | Étiquette |
| --- | --- | --- | --- | --- |
| InstructGPT (2022) | environ 13 000 prompts de SFT, écrits par des étiqueteurs et issus de l'API | SFT du 175B : 4,9 pétaflops/s-jours, contre 3 640 pour le pré-entraînement de GPT-3 (donc environ 0,13 %, dérivé) | <https://arxiv.org/abs/2203.02155> (chiffres lus dans la version ar5iv : <https://ar5iv.labs.arxiv.org/html/2203.02155>) | publié |
| Llama 2 (2023) | 27 540 annotations de SFT ; « nous avons arrêté d'annoter la SFT » après ce nombre | 3,3 M d'heures A100 pour tout le modèle ; pas de part SFT | <https://arxiv.org/abs/2307.09288> | publié |
| Tülu 3 (Ai2, 2024) | 939 344 prompts de SFT | 8 B : 32 GPU pendant 6 h (192 heures-GPU, dérivé) ; 70 B : 64 GPU pendant 50 h (3 200 heures-GPU, dérivé) | <https://arxiv.org/abs/2411.15124> | publié |
| Qwen2.5 (2024) | plus d'un million d'exemples de SFT, 2 époques | non publié | <https://arxiv.org/abs/2412.15115> | publié |
| DeepSeek-R1 | environ 600 000 traces de raisonnement et environ 200 000 exemples hors raisonnement (804 745 au total dans le tableau 5) | environ 5 000 heures-GPU pour construire le jeu de SFT (presse) | <https://arxiv.org/abs/2501.12948> ; le coût vient de <https://hyper.ai/en/news/44332> | publié pour les comptes ; tiers pour les heures |
| Llama 3 (2024) | total de SFT non publié ; plus de 2,7 M d'exemples de code synthétiques | non publié | <https://arxiv.org/abs/2407.21783> | publié (en partie), le reste non trouvé |
| Olmo 3 Think 7B (Ai2, 2025) | 2 268 178 exemples (Dolci-Think-SFT-7B) | SFT du 32B : balayage de 4 taux d'apprentissage sur 256 GPU pendant 36 h | <https://huggingface.co/datasets/allenai/Dolci-Think-SFT-7B> ; <https://arxiv.org/abs/2512.13961> | publié |
| SmolLM3 (3 Md) | 1,8 Md de jetons de SFT (dont 0,8 Md de raisonnement), 4 époques | non publié séparément | <https://huggingface.co/blog/smollm3> | publié |
| Lucie-7B (français) | Alpaca-cleaned, Alpaca-cleaned-fr, Magpie-Gemma, WildChat pour la première version ; aucun compte | pré-entraînement : environ 500 000 heures-GPU H100 sur Jean Zay ; instruct non publié | <https://arxiv.org/abs/2503.12294> | publié (compte SFT non trouvé) |
| CroissantLLM (1,3 Md, français et anglais) | UltraChat et WildChat (ChatGPT en anglais et français) ; les 12 k exemples de traduction font « 4 % » du jeu, soit environ 300 000 exemples (dérivé, à ne pas citer comme publié) | pré-entraînement : 99 648 heures-GPU, 17 jours ; 123 k heures A100 pour toutes les expériences ; SFT non publié | <https://arxiv.org/abs/2402.00786> | publié, sauf le total SFT |

Ordre de grandeur pour le site : de 13 000 exemples (2022) à plus de 2 millions (2025). Un petit modèle comme Ton IA peut tourner sur 10 000 à 100 000 exemples ; ce n'est donc pas l'échelle des labos, mais la forme de l'étape est la même.

Annotateurs : InstructGPT a employé environ 40 contractants recrutés via Upwork et ScaleAI (publié). Aucun coût d'annotation n'est publié dans les sources lues (InstructGPT, Llama 2, Llama 3). Je n'ai pas cherché d'estimations de tiers : ne pas inventer un montant en dollars.

### B2. Préférences et alignement (chapitre 1.8)

| Qui | Données de préférences | Calcul | Source | Étiquette |
| --- | --- | --- | --- | --- |
| InstructGPT (2022) | environ 33 000 prompts pour le modèle de récompense ; environ 31 000 prompts pour le PPO (sans étiquette humaine) ; environ 40 étiqueteurs | PPO-ptx du 175B : 60 pétaflops/s-jours (environ 1,6 % du pré-entraînement, dérivé) | <https://arxiv.org/abs/2203.02155> | publié |
| Llama 2 (2023) | 1 418 091 comparaisons binaires « Meta » ; 2 919 326 en comptant les jeux ouverts ; 5 versions successives (RLHF-V1 à V5) | 3,3 M d'heures A100 pour tout le modèle | <https://arxiv.org/abs/2307.09288> | publié |
| Llama 3 (2024) | six tours d'annotation et d'entraînement ; nombre total de comparaisons non publié ; seulement la répartition (anglais général 81,99 %, code 6,93 %, multilingue 5,19 %, raisonnement et outils 5,89 %) ; DPO : taux 1e-5, bêta 0,1 | non publié | <https://arxiv.org/abs/2407.21783> | publié (en partie) |
| Llama 4 (2025) | recette « SFT légère, puis RL en ligne, puis DPO légère » ; plus de 50 % des données « faciles » supprimées pour les modèles ordinaires, 95 % de la SFT pour Behemoth | non publié | <https://ai.meta.com/blog/llama-4-multimodal-intelligence/> | publié (blog) |
| Tülu 3 (2024) | 354 192 paires pour la mise au point des préférences (section 2.3) ; le tableau 7 parle de 425 145 prompts de DPO (selon le modèle) ; paires faites en comparant des sorties de plusieurs modèles, jugées par un LLM | 8 B : 10 h sur 8 H100 (80 heures-GPU, dérivé) ; 70 B : 19 h sur 64 H100 (1 216 heures-GPU, dérivé) | <https://arxiv.org/abs/2411.15124> | publié (deux comptes ne concordent pas : à vérifier) |
| Qwen2.5 (2024) | environ 150 000 paires pour la DPO hors ligne, 1 époque | non publié | <https://arxiv.org/abs/2412.15115> | publié |
| Olmo 3 Think 7B (2025) | 150 000 paires (Dolci-Think-DPO-7B) | DPO du 32B : environ 18 h pour un balayage complet de taux sur 64 GPU par essai, étalé sur plusieurs jours à cause d'incidents sur la grappe | <https://huggingface.co/datasets/allenai/Dolci-Think-DPO-7B> ; <https://arxiv.org/abs/2512.13961> | publié |
| DeepSeek-R1 | 66 000 paires pour le modèle de récompense d'utilité ; 106 000 prompts pour le modèle de sécurité | non publié | <https://arxiv.org/abs/2501.12948> | publié |

Gain mesuré chez un grand labo : Tülu 3 8B passe d'une moyenne de 60,6 (SFT) à 64,7 (DPO) puis 65,1 (RLVR). À 70B : 72,6 puis 76,2. À 405B : 76,3 puis 79,0 puis 80,0. Incertain : le tableau 9 de l'article donne 60,1 pour la SFT 8 B, au lieu de 60,6 (à relire avant de citer). La source est <https://arxiv.org/abs/2411.15124>.

Historique à citer avec prudence : InstructGPT (2022) montre que les sorties du modèle de 1,3 Md étaient préférées à celles du GPT-3 de 175 Md par des juges humains. C'est un test de préférence sur des prompts réels, pas un test de connaissances.

### B3. RL de raisonnement et récompenses vérifiables (chapitre 1.9)

| Qui | Données et réglages | Calcul et coût | Source | Étiquette |
| --- | --- | --- | --- | --- |
| Tülu 3 (RLVR) | 29 946 prompts (GSM8K 7 473, MATH 7 500, consignes vérifiables 14 973) | 8 B : 65 h sur 8 GPU (520 heures-GPU, dérivé) ; 70 B : 60 h sur 48 GPU (2 880 heures-GPU) ; 405 B : 46 h sur 256 GPU (11 776 heures-GPU) ; en plus modèle de récompense 8 B : 9 h sur 8 GPU | <https://arxiv.org/abs/2411.15124> | publié (heures-GPU : dérivé) |
| DeepSeek-R1-Zero | 10 400 pas, 16 réponses par question, 32 questions par pas | environ 198 h sur 648 H800 (environ 128 000 heures-GPU, dérivé) | <https://arxiv.org/abs/2501.12948> (réglages) ; <https://hyper.ai/en/news/44332> (heures) | publié pour les réglages ; tiers pour les heures |
| DeepSeek-R1 | 2 étapes de RL, 1 700 pas pour la seconde | environ 80 h sur 648 H800 ; coût total annoncé 294 000 $ pour R1, hors modèle de base (6 M$ pour le modèle de base selon la presse) | article de Nature, non lu (accès refusé) ; presse : <https://www.bnnbloomberg.ca/business/artificial-intelligence/2025/09/18/chinas-deepseek-says-its-hit-ai-model-cost-just-us294000-to-train/> | tiers |
| Olmo 3 Think 32B | RL de départ : environ 5 jours, au moins un jour perdu en incidents ; poursuite de 21 jours sur 224 GPU pour Olmo 3.1 Think 32B | tout le modèle : environ 56 jours sur 1 024 H100, environ 2,75 M$ à 2 $ l'heure-H100 (estimation des auteurs) ; post-entraînement environ 9 jours | <https://arxiv.org/abs/2512.13961> | publié |
| Olmo 3 Think 7B | 102 014 prompts de RL (Dolci-Think-RL-7B) : maths, code, consignes précises, discussion | non lu | <https://huggingface.co/datasets/allenai/Dolci-Think-RL-7B> | publié |
| Olmo 3.1 Think 32B | MATH 96,2 ; AIME 2024 80,6 ; AIME 2025 78,1 ; IFEval 93,8 ; LiveCodeBench v3 83,3 ; HumanEvalPlus 91,5 (modèle final seulement) | | <https://arxiv.org/abs/2512.13961> | publié |
| DeepSeek-R1-Zero et R1 | AIME 2024 : 77,9 puis 79,8 ; MATH-500 : 95,9 puis 97,3 | | <https://arxiv.org/abs/2501.12948> | publié |

Incertain : le nombre de GPU de R1 (512 ou 648) diffère selon les articles de presse, et « 4 jours » contre « 80 heures » apparaît dans le même article. Ne pas donner de chiffre précis sans avoir lu la source Nature. Dire « de l'ordre de 300 000 dollars annoncés par DeepSeek, selon la presse ».

Ce que le RL ne remplace pas : DeepSeek-R1 utilise aussi environ 800 000 exemples de SFT (voir B1) ; Olmo 3 et Tülu 3 font SFT, puis DPO, puis RL. Dans ces recettes le RL vient en dernier, sur un modèle déjà capable. Seul DeepSeek-R1-Zero fait du RL sans SFT, sur un très gros modèle de base.

### B4. Code (chapitre 1.10)

| Qui | Données et méthode | Source | Étiquette |
| --- | --- | --- | --- |
| Qwen2.5-Coder | pré-entraînement 5,5 T de jetons ; instruction en deux temps (dizaines de millions puis millions d'exemples) ; échantillonnage par rejet ; DPO avec exécution de code | <https://arxiv.org/abs/2409.12186> | publié (comptes exacts non publiés) |
| Llama 3 | plus de 2,7 M d'exemples de code synthétiques en SFT | <https://arxiv.org/abs/2407.21783> | publié |
| Tülu 3 / Olmo 3 | le code est un des domaines du mélange ; Olmo 3 mesure HumanEvalPlus (91,5) et LiveCodeBench (83,3) pour le 32B Think | <https://arxiv.org/abs/2512.13961> | publié |
| StarCoder2-Instruct | non lu | | non trouvé |

---

## Lacunes à ne pas masquer

- Texte de Nature sur DeepSeek-R1 non lu : coût de R1 en tiers seulement.
- Llama 3 et 4 : pas de nombre total de comparaisons humaines (Llama 3), pas de calcul de post-entraînement, pas de coût d'annotateurs.
- Aucun coût d'annotateurs en dollars dans aucune source lue. À ne pas estimer sans source.
- Mistral, Qwen3 petits, Pythia, StarCoder2-Instruct : non lus.
- Aucune mesure isolée de la DPO sur un modèle de moins de 1 Md.
- Durée de l'annotation chez les grands labos : non publiée dans les sources lues.
- Tout ce qui est de 2026 hors nanochat (README, mars 2026) et la mise à jour d'Olmo 3 (avril 2026) : peu couvert.

---

## Ce que le site peut promettre

Règle commune : chaque chapitre mesure avant et après sur les mêmes tests, montre aussi les échecs, et dit en une phrase que les labos font la même chose avec des centaines de fois plus de données.

### 1.7 Converser (SFT)

- Le site peut promettre que Ton IA apprendra à reconnaître un tour de parole et à répondre dans le format chat, avec un français souvent lisible.
- Il peut promettre qu'on mesurera la différence sur des consignes simples et vérifiables (longueur, mot imposé, format), comme IFEval. SmolLM2-135M passe de 17,2 à 29,9 sur ce test avec bien plus de données.
- Il ne doit pas promettre un gain aux tests de connaissances. Chez nanochat d20, ARC-Challenge ne bouge pas (28,75 puis 28,07) ; chez SmolLM2-135M, HellaSwag, ARC et MMLU baissent un peu après l'instruction.
- Il doit dire que les réponses seront souvent hors sujet ou inventées : un modèle de cette taille, avec 8,67 Md de jetons, ne sait pas beaucoup de choses.

### 1.8 L'aligner (préférences, DPO)

- Le site peut promettre de construire de vraies paires « préférée / rejetée » et d'entraîner avec la DPO sur la carte.
- Il peut promettre de mesurer l'effet par une comparaison côte à côte (taux de victoire sur un petit jeu de prompts, avec juge humain ou juge automatique clairement nommé).
- Il ne doit pas promettre de meilleurs scores aux tests. Chez les grands labos le gain est réel mais modéré (Tülu 3 8B : 60,6 puis 64,7), et pour les modèles de moins de 1 Md je n'ai trouvé aucune mesure isolée de la DPO.
- Il doit parler des risques : le modèle apprend à plaire au juge, les réponses peuvent devenir plus longues sans être meilleures.

### 1.9 Raisonner (traces, RL à récompense vérifiable)

- Le site peut promettre une boucle de RL qui marche de bout en bout (générer, vérifier automatiquement, récompenser) sur une tâche étroite et vérifiable, par exemple de petits calculs ou un petit sous-ensemble de GSM8K.
- Il peut montrer qu'un score monte un peu : nanochat d20 va de 4,55 % à 7,58 % de GSM8K avec le RL, ce qui reste très bas.
- Il ne doit pas promettre un « moment eurêka ». TinyZero indique que Qwen2.5-0.5B (pré-entraîné sur bien plus de données) n'apprend pas à raisonner sur Countdown, et que des comportements de vérification n'apparaissent qu'à partir de 1,5 Md. Ton IA est plus petite et a vu moins de données.
- Il doit dire que le RL peut aussi s'effondrer ou tricher avec la récompense, et que cela fait partie de l'apprentissage.

### 1.10 Coder

- Le site peut promettre de faire écrire à Ton IA de petites fonctions et de les tester en lançant du vrai code avec des tests, ce qui donne un score honnête (réussite ou échec).
- Il peut dire que le score attendu est très bas : nanochat d20, avec 11,2 Md de jetons, est à 6,7 % puis 8,5 % de HumanEval, et on ne sait pas si Ton IA fera mieux ou moins bien.
- Il ne doit pas promettre un assistant de programmation. Qwen2.5-Coder 0.5B Instruct atteint 61,6 % de HumanEval, mais avec environ 5,5 T de jetons, soit environ 630 fois plus.
- Il doit rappeler que du code qui a l'air juste peut ne pas marcher, et que seul le test d'exécution tranche.
