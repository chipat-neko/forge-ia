# Vague 2 de La Forge IA : méthodes et outils à jour (recherche du 17/11/2026)

Question : quelles méthodes et quels outils sont à jour en novembre 2026 pour le SFT (1.7), les préférences (1.8), le raisonnement (1.9) et le code (1.10), et lesquels conviennent à un modèle de 433 M de paramètres sur une carte de 16 Go, sous Windows natif ?

Toutes les sources ont été lues le 17/11/2026 (via la recherche web et la lecture de pages, sans accès authentifié). Convention :
- **[lu]** : le texte de la page a été lu en entier pour ce point.
- **[résumé]** : vu seulement dans un résumé ou un résultat de recherche, à revérifier dans la source avant de l'imprimer dans un chapitre.
- **[non vérifié]** : connaissance générale, pas relue aujourd'hui.

Aucun chiffre n'est inventé. Quand un chiffre manque, il est dit manquant.

---

## 0. Ce qu'il faut retenir (et ce qui est contesté)

- Les outils de référence (TRL, nanochat) sont écrits pour `transformers`. « Ton IA » est un transformer maison : on **réimplémente** les pertes (SFT masqué, DPO, GRPO) dans `projets/forge`, on s'inspire de la doc TRL pour les formules et les valeurs par défaut.
- Aucun comparatif récent et fiable ne tranche « quelle variante de DPO est la meilleure pour un petit modèle ». Les résultats publiés dépendent du jeu de données et de l'évaluation (voir 2.3).
- Le RL à récompense vérifiable (GRPO et dérivés) sur un modèle de moins de 1 G : des succès modestes à 0,5 G (instruct déjà solide), un échec documenté à 135 M. **Pas de garantie** à 433 M sans SFT de démarrage (voir 3.4).

---

## 1. Versions des outils (vérifiées le 17/11/2026)

| Outil | Version | Source | Remarque |
| --- | --- | --- | --- |
| PyTorch stable | **2.15.0**, publiée le 28 oct. (marquée « Latest ») | [GitHub releases PyTorch](https://github.com/pytorch/pytorch/releases) [lu, 17/11/2026] ; [PyPI torch](https://pypi.org/pypi/torch/json) : `info.version` 2.15.0, `requires_python >=3.11` [lu] | Aucune version plus récente que 2.15 (ni 2.15.x) n'apparaît dans la liste lue. La page n'affiche pas l'année. |
| PyTorch, historique récent | 2.14.1 (30 sept.), 2.14.0 (2 sept.), 2.13.0 (8 juil.), 2.12.1 (18 juin), 2.12.0 (13 mai) | [GitHub releases PyTorch](https://github.com/pytorch/pytorch/releases) [lu, 17/11/2026] | Rythme : environ une version tous les deux mois. |
| `datasets` | **5.2.0**, publiée le 9 nov. | [GitHub releases datasets](https://github.com/huggingface/datasets/releases) [lu, 17/11/2026] ; [PyPI datasets](https://pypi.org/pypi/datasets/json) : `info.version` 5.2.0, `requires_python >=3.10.0` [lu] | La doc en ligne affiche la version v5.2.0. |
| TRL | Version 1 sortie (billet du 31 mars 2026) ; la doc `main` liste `SFTTrainer`, `DPOTrainer`, `KTOTrainer`, `GRPOTrainer`, `RLOOTrainer`, `AsyncGRPOTrainer` (stable) ; `ORPOTrainer` et `CPOTrainer` sont **expérimentaux** | [Doc TRL, accueil](https://huggingface.co/docs/trl/main/en/index) [lu, 17/11/2026] | Numéro exact de TRL non relevé. |
| Colab, runtime actuel | Version de runtime **2026.10** : Ubuntu 24.04.5 LTS, **Python 3.13.18** (2026.07 et 2026.04 : Python 3.12.13) | [googlecolab/backend-info](https://github.com/googlecolab/backend-info) [lu, 17/11/2026] | Le dépôt avertit que ses fichiers « ne reflètent pas forcément l'état exact de la production », avec un ou deux jours de retard. Pas de date de mise à jour affichée. |
| Colab, paquets (GPU) | `torch 2.14.1+cu130`, `torchvision 0.29.1+cu130`, `datasets 4.8.5`, `transformers 5.22.1`, `peft 0.21.2`, `numpy 2.4.6` ; TRL absent de la liste | [pip-freeze.gpu.txt](https://raw.githubusercontent.com/googlecolab/backend-info/main/pip-freeze.gpu.txt) [lu, 17/11/2026] | **Colab a PyTorch 2.14.1, donc un cran de retard sur le stable 2.15.0.** Colab a `datasets` 4.8.5, pas 5.x. Python 3.13 est déduit des paquets `standard-*` épinglés à 3.13.0, mais confirmé par le tableau de versions ci-dessus. |

À retenir pour les notebooks : un notebook testé en local avec `torch 2.15` et `datasets 5.2` doit aussi tourner sur Colab avec `torch 2.14.1` et `datasets 4.8.5`. Vérifier surtout `state_dict()` d'`IterableDataset` (section 6), dont le comportement a changé entre 4.8 et 5.x.

---

## 2. Chapitre 1.7 : SFT et format chat

### 2.1 Gabarit et jetons spéciaux

- La doc TRL décrit l'instruction tuning comme : un gabarit de conversation (marqueurs de rôle, jetons spéciaux, fins de tour) plus un jeu de données conversationnel. [Doc SFTTrainer](https://huggingface.co/docs/trl/main/en/sft_trainer) [lu, 17/11/2026]
- Mise en garde de la même doc : il faut **aligner le jeton de fin (EOS) avec le gabarit** pour que les réponses s'arrêtent (exemple Qwen : `eos_token="<|im_end|>"`). Pour toi, cela veut dire : `<|fin_tour|>` doit être le jeton que le modèle apprend à émettre et que la génération guette. [Doc SFTTrainer](https://huggingface.co/docs/trl/main/en/sft_trainer) [lu, 17/11/2026]
- Si un gabarit Jinja est ajouté, les jetons spéciaux qu'il cite doivent exister dans le tokenizer et la matrice d'embeddings être redimensionnée. Pour toi : les jetons existent déjà dans le BPE, mais leurs embeddings n'ont **jamais été entraînés** pendant le pré-entraînement (sauf s'ils apparaissaient dans les données). Ils seront appris pendant le SFT. À signaler dans le chapitre. [Doc SFTTrainer](https://huggingface.co/docs/trl/main/en/sft_trainer) [lu] ; l'inférence sur les embeddings non entraînés est de moi.

### 2.2 Masquer la perte

- TRL : option `assistant_only_loss=True`, qui calcule la perte **uniquement sur les réponses de l'assistant** ; les positions ignorées reçoivent l'indice `-100`. Pour un jeu « prompt/complétion », la perte porte par défaut sur la complétion seule. [Doc SFTTrainer](https://huggingface.co/docs/trl/main/en/sft_trainer) [lu, 17/11/2026]
- TRL a besoin que le gabarit contienne les balises `{% generation %}` et `{% endgeneration %}` pour trouver les tours de l'assistant. Dans ton code maison, c'est plus simple : le tokenizer produit un masque binaire au moment où il assemble la conversation. [Doc SFTTrainer](https://huggingface.co/docs/trl/main/en/sft_trainer) [lu]
- SmolLM3 : « perte masquée sur les tours de l'utilisateur et sur les résultats des appels d'outils ». Le tour de l'utilisateur et la sortie d'outil ne sont pas appris ; l'appel d'outil émis par l'assistant l'est. Cela s'applique à `<|appel_outil|>`. [Blog SmolLM3](https://huggingface.co/blog/smollm3) [lu, 17/11/2026]
- Inférence de ma part, à tester : la perte doit aussi porter sur `<|fin_tour|>` (sinon le modèle ne sait jamais s'arrêter) mais pas sur les marqueurs `<|utilisateur|>` et `<|systeme|>`.

### 2.3 Empaquetage (packing)

- TRL : `packing=True`, longueur fixée par `max_length` (défaut 1024). Stratégies : `"bfd"` (défaut ; best-fit decreasing, tronque le surplus), `"bfd_split"` (idem, mais découpe le surplus), `"wrapped"` (agressive, coupe au milieu d'une séquence). [Doc SFTTrainer](https://huggingface.co/docs/trl/main/en/sft_trainer) [lu, 17/11/2026]
- SmolLM3 : empaquetage **BFD** pour le SFT final ; **wrapped** pour la phase de mi-entraînement. [Blog SmolLM3](https://huggingface.co/blog/smollm3) [lu, 17/11/2026]
- Piège à documenter (général, **[non vérifié]** aujourd'hui) : en empaquetant sans masque d'attention par document, une conversation « voit » la précédente. Deux parades : masque d'attention bloc-diagonal, ou accepter la fuite comme en pré-entraînement. À mesurer plutôt qu'à affirmer.

### 2.4 Taux d'apprentissage, époques, taille des données

Valeurs publiées (aucune n'est calibrée pour 433 M ; ce sont des ordres de grandeur) :

| Source | Modèle | Valeur |
| --- | --- | --- |
| TRL `SFTConfig` | tous | `learning_rate=2e-5` par défaut, `num_train_epochs=3.0`, `max_length=1024`, planificateur linéaire. Pour un adaptateur LoRA : environ 1e-4. [Doc SFTTrainer](https://huggingface.co/docs/trl/main/en/sft_trainer) [lu] | 
| SmolLM3 | 3 G | SFT de **1,8 G jetons** (1 G sans raisonnement + 0,8 G avec), **4 époques** (environ 8 G jetons vus). Taux d'apprentissage : non indiqué dans l'article. [Blog SmolLM3](https://huggingface.co/blog/smollm3) [lu] |
| nanochat (version d'oct. 2025) | 561 M | SFT d'environ **7 min** sur 8×H100, après 8 min de « mid-training » (SmolTalk, QCM MMLU, GSM8K avec calculatrice). [Discussion nanochat n°1](https://github.com/karpathy/nanochat/discussions/1) [lu, 17/11/2026] |

- Je n'ai **pas** trouvé de source primaire donnant « taux d'apprentissage optimal du SFT pour un modèle de 400 à 500 M entraîné de zéro ». À régler par un petit balayage (par exemple 1e-5, 3e-5, 1e-4) sur ta carte ; chaque essai est court. C'est un bon exercice pour le chapitre.
- Avec ton optimiseur de pré-entraînement : un taux de SFT sensiblement plus bas que celui de fin de pré-entraînement est la pratique courante (**[non vérifié]**).

---

## 3. Chapitre 1.8 : préférences

### 3.1 Le paysage

- DPO (Rafailov et al.) : perte de classification sur des paires (choisie, rejetée), sans modèle de récompense explicite ni échantillonnage pendant l'entraînement. Besoin d'un modèle de référence (les logarithmes de probabilité de départ). [Doc DPOTrainer](https://huggingface.co/docs/trl/main/en/dpo_trainer) [lu, 17/11/2026]
- Défauts TRL pour DPO : `beta=0.1`, `learning_rate=1e-6` (pas 5e-5), `max_length=1024`, `num_train_epochs=3.0`, perte `sigmoid`. [Doc DPOTrainer](https://huggingface.co/docs/trl/main/en/dpo_trainer) [lu]
- Variantes exposées par TRL pour DPO (`loss_type`) : `sigmoid`, `hinge`, `ipo`, `exo_pair`, `nca_pair`, `robust`, `bco_pair`, `sppo_hard`, `aot`, `aot_unpaired`, `apo_zero`, `apo_down`, `discopop`, `sft`, `sigmoid_norm` (normalisation par la longueur, idée de SimPO), `udpo`. On peut les **combiner** avec `loss_weights` (exemple MPO : sigmoid 0,8 + bco_pair 0,2 + sft 1,0). [Doc DPOTrainer](https://huggingface.co/docs/trl/main/en/dpo_trainer) [lu]
- Méthodes **sans modèle de référence** : SimPO (récompense = log-probabilité moyenne par jeton, plus une marge cible). Auteurs : Meng, Xia, Chen, NeurIPS 2024. Résultats annoncés : jusqu'à +6,4 points sur AlpacaEval 2 et +7,5 sur Arena-Hard par rapport à DPO, sur Mistral, Llama 3 et Gemma 2 (7 à 9 G). [arXiv 2405.14734](https://arxiv.org/abs/2405.14734) [lu, 17/11/2026]
- KTO : accepte des étiquettes « bon/mauvais » **non appariées** ; `KTOTrainer` est dans la partie stable de TRL. ORPO et CPO : classés **expérimentaux** dans TRL. [Doc TRL, accueil](https://huggingface.co/docs/trl/main/en/index) [lu, 17/11/2026]
- Méthode utilisée dans la pratique pour un petit modèle : **APO** (variante ancrée de DPO) pour SmolLM3 (3 G). Données : mélange de préférences Tulu 3 (mode sans raisonnement) plus paires synthétiques (réponse « choisie » = Qwen3-32B, « rejetée » = Qwen3-0.6B) pour le mode raisonnement. Beta et taux d'apprentissage : non indiqués dans l'article. Ensuite fusion de modèles (poids 0,9 pour l'agrégat APO, 0,1 pour le point de contrôle de mi-entraînement). [Blog SmolLM3](https://huggingface.co/blog/smollm3) [lu, 17/11/2026]
- Tulu 3 (Ai2) : « DPO normalisé par la longueur » utilisé tout au long du développement et pour les modèles finaux ; puis RLVR. Les hyperparamètres (taux, beta) n'étaient pas dans la partie du texte que j'ai pu lire : **[non vérifié]**, à relire dans l'annexe A de l'article. [arXiv 2411.15124 (HTML)](https://arxiv.org/html/2411.15124) [lu en partie, 17/11/2026]

### 3.2 Modèle de récompense contre méthode directe

- Avec un modèle de récompense : il faut l'entraîner (`RewardTrainer` dans TRL), puis un RL (PPO, RLOO, GRPO) qui échantillonne pendant l'entraînement. Trois modèles en mémoire pour du PPO classique. [Doc TRL, accueil](https://huggingface.co/docs/trl/main/en/index) [lu] pour la liste des entraîneurs ; le coût mémoire est de ma part.
- Méthode directe (DPO et cousins) : une passe sur des paires fixes, un seul modèle entraîné plus un modèle de référence (ou ses logarithmes précalculés : `precompute_ref_log_probs`). **Incompatible avec un `IterableDataset`** dans TRL. [Doc DPOTrainer](https://huggingface.co/docs/trl/main/en/dpo_trainer) [lu]
- Pour ton PC : méthode directe. La doc de pédagogie à écrire peut expliquer le modèle de récompense en encadré (échelle d'un grand labo), sans l'exécuter.

### 3.3 Résultats publiés comparant les variantes (prudence)

- Aucune source primaire unique ne compare toutes les variantes **pour un modèle sous 1 G**. Une recherche web montre des tableaux disparates :
  - un tableau récent : SimPO 66,17 en moyenne, DPO 65,67, KTO 65,65, ORPO 60,82 ; ORPO le plus faible dans plusieurs tableaux [résumé] ;
  - un article de février 2026 affirme que beaucoup de variantes (CPO, KTO...) **ne dépassent pas** DPO standard, et parfois font moins bien [résumé] ; [arXiv 2602.00954](https://arxiv.org/html/2602.00954) [vu dans les résultats de recherche seulement] ;
  - sur LLaMA-3-8B : KTO et SimPO à égalité (62,60), DPO 62,10 [résumé].
- Conclusion honnête : **DPO standard reste une base solide ; SimPO ou la normalisation par la longueur sont les ajouts les plus souvent cités ; ORPO est répétitivement le plus faible.** Rien ne prouve que l'ordre se conserve à 433 M. À présenter comme tel, avec une petite expérience maison.

### 3.4 Pièges connus

- **Baisse de la vraisemblance des réponses choisies.** DPO peut baisser la probabilité de la réponse préférée tant que l'écart avec la rejetée grandit, surtout quand les deux réponses sont proches (distance d'édition faible). Correctif : DPO-Positive (DPOP, Smaug). [arXiv 2402.13228](https://arxiv.org/abs/2402.13228) [lu, 17/11/2026]. La doc TRL le confirme d'une autre façon : en pratique DPO opère « en supprimant la vraisemblance des réponses rejetées plutôt qu'en augmentant celle des préférées ». [Doc DPOTrainer](https://huggingface.co/docs/trl/main/en/dpo_trainer) [lu]. Remèdes disponibles dans TRL : `apo_zero`, `loss_type=["sigmoid","sft"]` (ajoute la perte SFT sur la réponse choisie). Surveiller `logps/chosen` et `rewards/chosen` : si elles baissent fortement, c'est le symptôme.
- **Biais de longueur.** Le DPO d'origine favorise les réponses longues ; SimPO et la normalisation par le nombre de jetons (`sigmoid_norm`) y répondent ; TRL propose aussi `ld_alpha` (LD-DPO) qui pondère les jetons « bavards ». [Doc DPOTrainer](https://huggingface.co/docs/trl/main/en/dpo_trainer) [lu]
- **Beta.** Défaut TRL 0,1. Beta plus grand = on reste plus près de la référence. Pour IPO, `beta` joue le rôle de τ. [Doc DPOTrainer](https://huggingface.co/docs/trl/main/en/dpo_trainer) [lu]. Le meilleur beta pour 433 M : **non publié** ; à balayer (0,05 ; 0,1 ; 0,3).
- **Taux d'apprentissage.** Environ 1e-6 par défaut (plein modèle), environ 1e-5 pour un adaptateur LoRA. [Doc DPOTrainer](https://huggingface.co/docs/trl/main/en/dpo_trainer) [lu]
- **Étiquettes bruitées.** `robust` et `udpo` (nouveau, arXiv 2607.03248, **non relu**) modélisent la probabilité qu'une étiquette soit inversée via `label_smoothing`. [Doc DPOTrainer](https://huggingface.co/docs/trl/main/en/dpo_trainer) [lu]

### 3.5 Données de préférences en français

- Aucune source lue aujourd'hui sur un jeu de préférences en français de bonne qualité. **Lacune** : à chercher dans la phase de planification (traduction de jeux anglais, ou paires synthétiques fabriquées par ton propre modèle, schéma « Qwen3-32B contre Qwen3-0.6B » de SmolLM3 transposé).

---

## 4. Chapitre 1.9 : raisonnement

### 4.1 SFT sur des traces de raisonnement

- SmolLM3 : mi-entraînement de raisonnement de **35 G jetons** (OpenThoughts3-1.2M plus un sous-ensemble de Llama-Nemotron-Post-Training v1.1, traces R1), **4 époques** (environ 140 G jetons), gabarit ChatML, empaquetage « wrapped ». [Blog SmolLM3](https://huggingface.co/blog/smollm3) [lu, 17/11/2026]. Échelle : 3 G de paramètres et des dizaines de milliards de jetons, hors de portée de 433 M sur 16 Go ; à montrer comme « échelle d'un grand labo ».
- **« Small Models Struggle to Learn from Strong Reasoners »** (arXiv 2502.12143) : les modèles d'environ **3 G ou moins** ne profitent pas de façon fiable des longues chaînes de pensée ni de la distillation depuis de gros modèles ; ils font mieux avec des **chaînes courtes et simples**. Remède proposé : « Mix Distillation » (mélanger chaînes longues et courtes). [arXiv 2502.12143](https://arxiv.org/abs/2502.12143) [lu, 17/11/2026]. **Très pertinent pour 433 M** : viser des traces courtes.
- Format : `<|pensee|> ... <|fin_pensee|>` suivi de la réponse. TRL montre le même motif avec `<think>...</think>` dans un exemple de SFT. [Doc SFTTrainer](https://huggingface.co/docs/trl/main/en/sft_trainer) [lu]

### 4.2 RL à récompense vérifiable : les algorithmes

- **GRPO** : l'avantage d'une réponse = sa récompense moins la moyenne de son groupe (divisé par l'écart-type), sans réseau « critique ». Défauts TRL : 8 générations par invite, `max_completion_length=512`, `beta=0.0` (donc **pas de modèle de référence chargé**, ce qui économise mémoire et temps ; DeepSeek-R1 a utilisé 0,001), `epsilon=0.2`. [Doc GRPOTrainer](https://huggingface.co/docs/trl/main/en/grpo_trainer) [lu, 17/11/2026]
- **Dr. GRPO** (Liu et al., arXiv 2503.20783) : GRPO a un biais d'optimisation qui allonge les réponses, surtout les fausses ; la correction retire la normalisation par la longueur et par l'écart-type. [arXiv 2503.20783](https://huggingface.co/papers/2503.20783) [résumé via recherche, 17/11/2026]. Dans TRL : `loss_type="dr_grpo"`, qui divise par une constante `L·G` (L = longueur max de complétion). [Doc GRPOTrainer](https://huggingface.co/docs/trl/main/en/grpo_trainer) [lu]
- **DAPO** (arXiv 2503.14476) : système open source ; 50 points sur AIME 2024 avec Qwen2.5-32B. Quatre techniques (selon ma lecture de la note de la page : clip-higher, échantillonnage dynamique, perte au niveau du jeton, pénalité de longueur). [arXiv 2503.14476](https://arxiv.org/abs/2503.14476) [lu en partie ; la liste des quatre techniques vient d'une note de bas de page, détails non lus]. Dans TRL : `loss_type="dapo"` est **le défaut actuel** (normalisation au niveau du jeton) ; `epsilon_high=0.28` recommandé par DAPO. [Doc GRPOTrainer](https://huggingface.co/docs/trl/main/en/grpo_trainer) [lu]
- **GSPO** (Qwen, arXiv 2507.18071, 24 juillet 2025) : ratio d'importance calculé sur la **séquence entière**, écrêtage au niveau de la séquence ; annoncé plus stable que GRPO, surtout pour les modèles à experts (MoE). [arXiv 2507.18071](https://arxiv.org/abs/2507.18071) [lu, 17/11/2026]. Dans TRL : `importance_sampling_level="sequence"` (le doc lu ne nomme pas GSPO explicitement ; l'équivalence est mon inférence). [Doc GRPOTrainer](https://huggingface.co/docs/trl/main/en/grpo_trainer) [lu]
- **Plus récent** dans TRL (noms de `loss_type` listés dans la doc) : `sapo` (barrière douce au lieu de l'écrêtage), `cispo` (`epsilon_high` à 5,0 « ScaleRL »), `vespo`. Je n'ai lu que la ligne de doc de chacun, pas les articles : **[non vérifié]** sur leurs mérites. TRL ajoute aussi `AsyncGRPOTrainer` (génération et entraînement découplés via vLLM), qui n'a pas d'intérêt sur une seule carte. [Doc GRPOTrainer](https://huggingface.co/docs/trl/main/en/grpo_trainer) ; [Doc TRL, accueil](https://huggingface.co/docs/trl/main/en/index) [lu]
- Contesté : la normalisation. Dr. GRPO retire la division par la longueur, DAPO la fait au niveau du jeton ; les deux visent le biais de longueur mais ne sont pas équivalentes (la source qui le dit pour DAPO est un wiki communautaire, **[résumé]**).
- **RLVR** (Tulu 3) : récompense constante si la complétion est correcte. [arXiv 2411.15124 (HTML)](https://arxiv.org/html/2411.15124) [lu en partie]

### 4.3 Ce que fait nanochat pour le RL (référence directement utile)

Script `scripts/chat_rl.py`, lu le 17/11/2026 [source](https://raw.githubusercontent.com/karpathy/nanochat/master/scripts/chat_rl.py) :
- Quatre simplifications avouées : pas de région de confiance (**pas de KL**), **sur la politique** donc pas de ratio PPO ni d'écrêtage, normalisation **au niveau du jeton** (style DAPO), avantage = `r - moyenne` **sans division par l'écart-type**. Résultat : « plus proche de REINFORCE ».
- Défauts : 16 échantillons par question, 16 questions par étape (donc **256 séquences par étape**), 256 jetons maximum, température 1,0, top-k 50, une époque, évaluation toutes les 60 étapes sur 400 questions de test avec pass@k jusqu'à k=8.
- Tâche : GSM8K uniquement. La récompense est définie dans le module de tâche (non lu).
- Chiffres du billet d'origine (oct. 2025, modèle de 561 M, 8×H100) : GSM8K **2,50 %** (mid) puis **4,55 %** (SFT) puis **7,58 %** (RL) ; RL environ **1,5 h** ; coût total jusqu'au SFT environ **92,4 $** (3 h 51 à environ 24 $/h). [Discussion nanochat n°1](https://github.com/karpathy/nanochat/discussions/1) [lu, 17/11/2026]. Le dépôt a depuis évolué : la page principale affiche en 2026 un classement « temps pour atteindre GPT-2 » (CORE 0,2585 en 3,04 h pour d24, 29 janv. 2026). [GitHub nanochat](https://github.com/karpathy/nanochat) [lu]. Les chiffres GSM8K d'octobre 2025 ne sont donc plus ceux de la version actuelle.

### 4.4 Ce qui marche ou non sous 1 G

- **Échec documenté à 135 M** : « L20-Edu-135M » (arXiv 2606.22189, 20 juin 2026, une seule carte L20, 13 G jetons de pré-entraînement) : le GRPO direct sur GSM8K a **baissé** la précision exacte de 1,82 % à 1,59 % (complétions de 192 jetons) et à 1,21 % (320 jetons). Un seul essai par réglage ; l'auteur l'offre comme un mode d'échec, pas comme une borne générale. Cause avancée (hypothèse, non prouvée) : départ à froid avec une récompense trop rare. [arXiv 2606.22189](https://arxiv.org/abs/2606.22189) [lu, 17/11/2026]
- **Succès modestes à 0,5 G** (dépôts de particuliers, **non revus par des pairs**, protocoles différents) :
  - Qwen2.5-0,5B-Instruct passe de 43,3 % à 49,6 % sur GSM8K avec une récompense de justesse seule, LoRA, GPU 8 Go. [GitHub XXG666/grpo-reward-design](https://github.com/XXG666/grpo-reward-design) [vu dans les résultats de recherche seulement] ;
  - un billet AWS annonce 11 % → 41 % pour Qwen2.5-0,5B, mais avec une référence très inférieure aux autres relevés (protocole d'évaluation probablement différent). [AWS blog](https://aws.amazon.com/blogs/machine-learning/overcoming-reward-signal-challenges-verifiable-rewards-based-reinforcement-learning-with-grpo-on-sagemaker-ai/) [vu dans les résultats de recherche seulement] ;
  - observation d'un auteur : GRPO ne peut renforcer qu'un comportement que le modèle produit déjà parfois ; une récompense de format est trop rare pour être découverte par l'exploration. [GitHub XXG666/grpo-reward-design](https://github.com/XXG666/grpo-reward-design) [résumé].
  - Les références vont de 0,0 % à 47 % selon la rigueur du format de réponse : **ne jamais comparer d'un dépôt à l'autre**.
- **Leçon pratique, déduite** : le RL ne crée pas la capacité, il l'amplifie. Pour 433 M, il faut (a) un SFT de démarrage qui apprend déjà le format de pensée et fait résoudre parfois la tâche, (b) des tâches **plus faciles que GSM8K** pour avoir une récompense non nulle dès le départ : arithmétique à 2 chiffres, comptes à rebours, problèmes à une étape, (c) mesurer le **taux de réussite initial** avant de lancer le RL : s'il est de 0 %, ne pas lancer.
- Le nombre de générations par invite doit être assez grand pour qu'au moins une réponse du groupe réussisse ; si toutes échouent ou toutes réussissent, l'avantage est nul (c'est ce que DAPO appelle l'échantillonnage dynamique). [lu pour DAPO : nom seulement ; l'explication est de moi]

### 4.5 Coût de calcul d'un tour de RL sur une carte (à mesurer)

- Je n'ai trouvé **aucun chiffre publié** pour un modèle de 433 M sur une RTX 5070 Ti. Ne rien promettre.
- Ce que dit la structure de nanochat : un pas = 256 séquences × jusqu'à 256 jetons = jusqu'à **65 536 jetons générés** (calcul de ma part à partir des défauts lus), puis une passe d'apprentissage sur ces séquences. La génération en séquence jeton par jeton domine le coût.
- TRL propose `use_vllm` (mode colocalisé, `vllm_gpu_memory_utilization=0.3`). Je n'ai **pas vérifié** si vLLM tourne sous Windows natif ; ton modèle n'est de toute façon pas un modèle `transformers`. Prévoir une génération maison avec cache clé-valeur (KV cache) dans `projets/forge`, groupes générés par lots. [Doc GRPOTrainer](https://huggingface.co/docs/trl/main/en/grpo_trainer) [lu] pour les options ; reste de ma part.
- Conformément à ta règle GPU ou CPU : faire un test chronométré court (10 pas) avant le vrai lancement. La génération est le goulot ; le vérificateur de réponses (comparaison de nombres) coûte presque rien.

---

## 5. Chapitre 1.10 : code

### 5.1 SFT sur des instructions de code et évaluation

- Même mécanique que 1.7 (masque assistant, empaquetage). nanochat mélange `humaneval.py` dans sa tâche d'évaluation de chat ; chiffre du billet d'origine : HumanEval **6,71 %** (mid) puis **8,54 %** (SFT) pour 561 M. [Discussion nanochat n°1](https://github.com/karpathy/nanochat/discussions/1) [lu]
- **HumanEval et pass@k** : Chen et al. (Codex) : 28,8 % de problèmes résolus avec un échantillon, **70,2 % avec 100 échantillons par problème** ; la page lue (résumé) ne détaille pas l'estimateur de pass@k ni le bac à sable. [arXiv 2107.03374](https://arxiv.org/abs/2107.03374) [lu, résumé seulement]. L'estimateur sans biais de pass@k (n échantillons, c corrects) est dans le corps de l'article : **à relire avant d'écrire le chapitre**. [non vérifié aujourd'hui]
- nanochat évalue en pass@k jusqu'à 8 pendant son RL (voir 4.3).
- Attention à ton modèle de 433 M : on attend un score HumanEval de **quelques pour cent** (ordre de grandeur nanochat à 561 M : 6 à 9 %, avec un pré-entraînement sur du texte web surtout). Ton pré-entraînement contient du code Python : bon point, mais **aucun chiffre** n'est promis.

### 5.2 Exécuter du code généré sans danger sous Windows

- **nanochat `execution.py`** (lu le 17/11/2026, [source](https://raw.githubusercontent.com/karpathy/nanochat/master/nanochat/execution.py)) : chaque exécution dans un **sous-processus** séparé, interpréteur neuf, environnement purgé, pas d'entrée standard, **délai de 5 s** par défaut, tué par le parent à l'échéance, limites mémoire `RLIMIT_AS` / `RLIMIT_DATA` / `RLIMIT_STACK` à 256 Mo, répertoire temporaire jeté ensuite, fonctions dangereuses de `os` / `shutil` mises à `None`. Le code **dit lui-même** que ce n'est « pas un vrai bac à sable » : le réseau n'est pas bloqué, `ctypes` contourne, « trivialement contournable » par du code hostile. Il utilise le module `resource`, **réservé à Unix** (inférence de la page : ne marche pas tel quel sous Windows).
- **Sous Windows natif**, ce qui est disponible :
  - Sous-processus + délai : `subprocess.run(..., timeout=...)`. Piège **[non vérifié aujourd'hui]** : sous Windows le délai tue le processus enfant mais pas forcément ses petits-enfants.
  - **Objets Job** de Windows : un groupe de processus géré comme une unité ; limites de mémoire de travail (working set), de priorité, de temps ; `TerminateJobObject` tue tout le groupe ; l'indicateur `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` tue tous les processus quand le dernier descripteur se ferme ; les processus enfants héritent du job par défaut ; des limites d'interface graphique existent (`JOBOBJECT_BASIC_UI_RESTRICTIONS`) ; limites de débit CPU. [Microsoft Learn, Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects) [lu, 17/11/2026]. C'est la bonne brique pour « tuer l'arbre de processus ».
  - Accès au réseau et au disque : **un job ne les bloque pas** (rien dans la page lue). Options à étudier (non lues aujourd'hui) : Windows Sandbox (Windows 11 Pro, éphémère), un conteneur/WSL2, un utilisateur Windows à faibles droits, une règle de pare-feu sortante pour le processus. Je recommande de **ne pas affirmer** « sans danger » dans le chapitre : dire « limité » et montrer les limites, comme le fait nanochat.
- Bonne pratique de conception : tâches de test fournies par toi (jeu fixe de problèmes écrits à la main ou issus d'un jeu public), code généré exécuté dans un dossier jetable, **jamais** sur des fichiers du projet.

### 5.3 Remplissage au milieu (FIM)

- Article d'origine (Bavarian et al., OpenAI, arXiv 2207.14255) : un modèle autorégressif apprend à remplir si un segment du milieu d'un document est déplacé à la fin ; une grande fraction de données ainsi transformée **ne dégrade pas** la génération de gauche à droite (perplexité et échantillons) ; les auteurs suggèrent de **l'entraîner avec FIM par défaut**. Ablations sur la fréquence, la structure et le choix du segment. [arXiv 2207.14255](https://arxiv.org/abs/2207.14255) [lu, 17/11/2026]. Les formats PSM/SPM et le taux précis ne sont pas dans le résumé lu.
- DeepSeek-Coder : tâche de remplissage avec une fenêtre de 16 K ; taux de FIM de **0,5** avec le mode **PSM** (préfixe, suffixe, milieu) selon des résumés secondaires qui divergent sur les formats comparés (PSM contre SPM ou MSP). Source primaire à relire : [arXiv 2401.14196](https://arxiv.org/abs/2401.14196), section 3.1.2 et figure 3. [résumé, 17/11/2026]
- Application à tes jetons : séquence d'entraînement `<|trou_prefixe|>` préfixe `<|trou_suffixe|>` suffixe `<|trou_milieu|>` milieu `<|fin_tour|>` (ou jeton de fin de document). **Les noms exacts des autres jetons `<|trou_*|>` sont à vérifier dans ton tokenizer** : je n'ai vu dans l'énoncé que `<|trou_prefixe|>`. Le choix PSM contre SPM et le taux sont des paramètres du chapitre.
- Idée de bonne pratique : calculer la perte sur le milieu seulement ou sur toute la séquence ; les deux se voient, **non tranché ici**.

---

## 6. Correctif à part : `IterableDataset.state_dict()` et `load_state_dict()` (datasets 5.x)

### 6.1 Ce que dit la doc officielle (v5.2.0)

Source : [Doc « Stream »](https://huggingface.co/docs/datasets/stream), section « Save a dataset checkpoint and resume iteration » [lu en entier, 17/11/2026].

- Oui, on peut reprendre : « Under the hood, the iterable dataset keeps track of the current shard being read and the example index in the current shard » (c'est ce que le `state_dict` mémorise).
- Reprise : le jeu **saute les fragments (shards) déjà lus**, relit le fragment courant depuis son début, **et saute les exemples jusqu'à l'exemple exact du point de contrôle**. Donc reprise « rapide », mais pas instantanée : on relit le fragment en cours depuis le début.
- Précision : au **fragment** près pour la lecture, à l'**exemple** près pour la position exacte (le fragment courant est relu, pas tout le flux).
- Exemple de la doc : `Dataset.from_dict({"a": range(6)}).to_iterable_dataset(num_shards=3)` : reprise après l'exemple 2 redonne 3, 4, 5.
- Compatible avec `StatefulDataLoader` de `torchdata` (qui appelle `state_dict()` du jeu).
- **Limite explicite** (encadré de la doc) : « Resuming returns exactly where the checkpoint was saved **except if `.shuffle()` is used** : examples from shuffle buffers are lost when resuming and the buffers are refilled with new data ».
- `take` et `skip` : « prevent future calls to `shuffle` because they lock in the order of the shards. You should `shuffle` your dataset before splitting it. » (doc « Stream », section « Split dataset »). Donc : mélanger **avant** `skip`/`take`.
- Fichiers Parquet à un seul ou peu de fichiers : la doc conseille `reshard()` avant `shuffle()` pour découper **par groupe de lignes (row group)** au lieu de par fichier. Le nombre de fragments de l'`IterableDataset` détermine la finesse de la reprise : si `num_shards == 1` même après `reshard()`, la doc dit de découper avec `skip()`/`take()`.
- Le mélange avec tampon, 5.0.0 : la mémoire tampon remplit à partir de **plusieurs fragments d'entrée** (`max_buffer_input_shards`, défaut 10), ce qui est un changement incompatible ; la note de version dit que `state_dict()` / `load_state_dict()` restent pris en charge ; `max_buffer_input_shards=1` rétablit l'ancien comportement. [Releases datasets](https://github.com/huggingface/datasets/releases) [lu, 17/11/2026]

### 6.2 Ce que montre le code (`iterable_dataset.py`, branche principale)

Source : [iterable_dataset.py](https://raw.githubusercontent.com/huggingface/datasets/main/src/datasets/iterable_dataset.py) [**lu seulement les 100 000 premiers caractères sur 263 518** ; la partie `TakeExamplesIterable` et Parquet n'a pas été lue].

- `SkipExamplesIterable` : **compte** les exemples sautés dans son état (`"skipped"`), et à la reprise ne saute que le reste. La position dans la source vient de l'état imbriqué de l'itérable sous-jacent.
- `BufferShuffledExamplesIterable` : l'état est celui de l'itérable enveloppé ; le **contenu du tampon n'est pas sauvegardé**. `load_state_dict` avertit : « The shuffle buffer will be refilled before starting to yield new examples. » Le générateur aléatoire n'est pas non plus sauvegardé (il repart de l'état initial). Conséquence (déduite du code, non confirmée par une phrase de la doc) : les exemples déjà tirés dans le tampon au moment du point de contrôle sont **perdus** (au plus `buffer_size` exemples, jamais répétés ni retrouvés).
- `ArrowExamplesIterable` : état `{"shard_idx", "shard_example_idx"}` ; saute les tables entières avant le point de reprise.
- Soupçon de bogue lu dans le code, **non confirmé par un test** : `_iter_arrow` pourrait renvoyer toute la table même si le point de reprise tombe au milieu d'elle, ce qui répéterait des lignes. Lié probablement à des correctifs ultérieurs (voir ci-dessous). À **tester** avant de s'y fier.
- `TakeExamplesIterable` et la lecture Parquet par groupe de lignes : **non lus**. Je ne peux donc pas dire comment `take` mémorise sa position, ni la finesse exacte de la reprise Parquet par groupe de lignes.

### 6.3 Historique des correctifs de la reprise (notes de version)

Source : [Releases datasets](https://github.com/huggingface/datasets/releases) [lu, 17/11/2026]. Les pages n'affichent pas l'année.
- 5.1.0 (5 oct.) : « Fix `deepcopy` bottleneck in state_dict() » ; « Shard the sources when skipping a distributed IterableDataset » ; « Fix async map checkpoint accounting across repeated resumes » ; « Fix repeated Arrow rebatch checkpoint restoration » ; « Keep take/skip counts when there are more DataLoader workers than shards » ; « Fix epoch iteration after skipping or taking a streaming subset ».
- 5.0.1 (28 juil.) : « Rebatch arrow source before formatting in IterableDataset.filter to fix resume data loss ».
- 4.8.5 (27 avr.) : « Fix iterable map resume state ». C'est **la version de Colab** aujourd'hui (4.8.5).
- 5.2.0 (9 nov.) : pas de changement lié aux points de contrôle dans les notes lues.

### 6.4 Conditions et limites à écrire dans le correctif

1. Le jeu doit rester un `IterableDataset` ; l'état ne marche pas avec un accès aléatoire.
2. **Mélange** : exemples du tampon perdus à la reprise. Si l'on veut une reprise exacte, ne pas utiliser `.shuffle()` sur le flux (mélanger en amont, par exemple en mélangeant l'ordre des fichiers ou en préparant des fragments déjà mélangés), ou accepter de perdre au plus `buffer_size` exemples.
3. **`skip` / `take`** : à placer **après** le mélange ; ils verrouillent l'ordre des fragments.
4. **Granularité** : la reprise est au niveau du fragment (fichier, ou groupe de lignes après `reshard()` pour Parquet), puis relit ce fragment jusqu'à l'exemple. Un seul gros fichier sans `reshard()` = relecture longue au pire.
5. **Transformations** (`map`, `filter`, `batch`) : plusieurs correctifs de reprise en 4.8.5, 5.0.1 et 5.1.0. **Utiliser ≥ 5.1.0** et **tester** une reprise (sortir 1000 exemples, sauver, reprendre, comparer avec une exécution sans arrêt).
6. **`DataLoader` avec plusieurs workers** : utiliser `StatefulDataLoader` (torchdata) ; avec plus de workers que de fragments, correctif 5.1.0.
7. **Colab** a `datasets` 4.8.5 : le correctif doit soit exiger `datasets>=5.1`, soit être testé sur 4.8.5.
8. TRL : `precompute_ref_log_probs` n'est pas compatible avec un `IterableDataset`, et un `IterableDataset` impose `max_steps`. [Doc DPOTrainer](https://huggingface.co/docs/trl/main/en/dpo_trainer) ; [Doc SFTTrainer](https://huggingface.co/docs/trl/main/en/sft_trainer) [lu]

---

## 7. Références pédagogiques qui font tout de zéro

| Référence | Ce qu'elle fait à chaque étape | Chiffres lus | Source |
| --- | --- | --- | --- |
| **nanochat** (Karpathy) | Tokenizer BPE de 65 536 jetons ; pré-entraînement ; « mid-training » (SmolTalk, QCM MMLU, GSM8K avec calculatrice) ; SFT ; RL de type GRPO sur GSM8K ; `execution.py` pour l'outil Python ; `chat_eval.py` | Billet d'oct. 2025 : modèle 561 M, environ 11,2 G jetons, environ 21 400 pas, 8×H100, environ 3 h 51 jusqu'au SFT pour environ 92,4 $ (RL en plus : environ 1,5 h). Résultats : ARC-Easy 0,3561 puis 0,3876 ; MMLU 0,3111 puis 0,3151 ; GSM8K 0,0250 puis 0,0455 puis 0,0758 (RL) ; HumanEval 0,0671 puis 0,0854 ; ChatCORE 0,0730 puis 0,0884. Page actuelle : « GPT-2 en environ 2 h pour environ 48 $ » sur un nœud 8×H100 (une autre section dit environ 1,5 h) ; `--depth` règle tout le reste | [Discussion n°1](https://github.com/karpathy/nanochat/discussions/1) ; [dépôt](https://github.com/karpathy/nanochat) [lus, 17/11/2026] |
| **smol-course** (Hugging Face) | Unité 1 : réglage par instructions, gabarits de chat ; unité 2 : évaluation ; unité 3 : alignement des préférences (DPO) ; unité 4 : modèles vision-langage ; unité 5 : apprentissage par renforcement (annoncé pour oct. 2025, détails non lus) ; synthèse de données. Modèles de base : SmolLM3, SmolVLM2. S'appuie sur TRL, donc **ne part pas de zéro** pour le code | Pas d'exigence matérielle chiffrée (« exigences GPU minimales »). Page non datée ; sections 5 à 7 annoncées pour fin 2025 | [smol-course](https://github.com/huggingface/smol-course) [lu, 17/11/2026] |
| **SmolLM3** (Hugging Face) | Recette complète d'un 3 G : mi-entraînement de raisonnement, SFT, APO, fusion de modèles | Voir sections 2 à 4 ; pré-entraînement sur **384 H100 pendant 24 jours** | [Blog](https://huggingface.co/blog/smollm3) [lu, 17/11/2026] |
| **Tulu 3** (Ai2) | SFT, DPO normalisé par la longueur, RLVR, évaluation avec jeux de développement et jeux non vus | Hyperparamètres non lus | [arXiv 2411.15124](https://arxiv.org/abs/2411.15124) [résumé lu] |
| **L20-Edu-135M** | Pré-entraînement audité sur une seule carte ; SFT avec interpolation de poids ; **échec du GRPO direct** | 134,5 M de paramètres, environ 13 G jetons, moyenne de 0,4150 sur six tâches (SmolLM-135M : 0,4767) | [arXiv 2606.22189](https://arxiv.org/abs/2606.22189) [lu, 17/11/2026] |
| **Dépôts GRPO sur GSM8K à 0,5 G** | GRPO écrit à la main ou avec TRL, LoRA, GPU de 4 à 8 Go | Voir 4.4 | [grpo-from-scratch](https://github.com/supersanchayrx/grpo-from-scratch) ; [grpo-lab](https://github.com/gian-g3dai/grpo-lab) [vus dans les résultats de recherche seulement] |

On s'en inspire sans recopier : l'architecture « un script par étape » de nanochat, la boucle GRPO minimale (section 4.3), et la fiche honnête sur les limites du bac à sable.

---

## 8. Incertitudes et points contestés (résumé)

- Aucun benchmark de variantes de DPO pour moins de 1 G ; les tableaux disponibles se contredisent.
- GRPO sous 1 G : seulement des dépôts non revus par des pairs (succès à 0,5 G, instruct de départ) et un échec à 135 M ; pas de donnée à 433 M.
- Coût d'un tour de RL pour 433 M sur une 5070 Ti : aucun chiffre publié ; à mesurer.
- Résultats de nanochat : chiffres d'octobre 2025 ; le dépôt a évolué depuis.
- `datasets` : la reprise sans perte avec mélange est **impossible** par conception (tampon perdu) ; code Take/Parquet non lu ; soupçon de répétition de lignes dans `_iter_arrow`, non testé.
- Tulu 3 : hyperparamètres de SFT, de DPO et de RLVR non lus.
- Bac à sable Windows : objets Job lus ; blocage réseau et disque non étudié.
- Jetons FIM : seuls `<|trou_prefixe|>` et « d'autres » sont connus ; noms exacts à vérifier dans le tokenizer.

---

## 9. Recommandations pour ton IA

- **1.7 SFT et format chat :** un gabarit à jetons `<|systeme|>`, `<|utilisateur|>`, `<|assistant|>`, `<|fin_tour|>`, perte masquée sur tout sauf les tours de l'assistant (et `<|fin_tour|>`), empaquetage BFD avec masque par document, taux d'apprentissage balayé autour de 1e-5 à 1e-4 sur quelques centaines de millions de jetons et quelques époques, à calibrer par essais courts ; vérifier que les embeddings des jetons spéciaux s'apprennent.
- **1.8 Préférences :** DPO maison avec perte `sigmoid` (beta 0,1 en départ, taux 1e-6 à 1e-5) plus un terme SFT sur la réponse choisie et la variante normalisée par la longueur (`sigmoid_norm`) ; précalculer les log-probabilités de référence ; surveiller `logps/chosen` ; ne pas présenter ORPO, KTO ou SimPO comme « meilleurs » faute de preuve à cette échelle ; modèle de récompense en encadré « grand labo » seulement.
- **1.9 Raisonnement :** SFT de démarrage sur des traces **courtes** `<|pensee|>...<|fin_pensee|>` (le « learnability gap » sous 3 G), puis mini-GRPO de type nanochat (pas de KL, sur la politique, perte au niveau du jeton, avantage `r - moyenne`) sur des tâches vérifiables plus faciles que GSM8K (arithmétique, comptes à rebours) ; ne lancer le RL que si le taux de réussite initial est non nul ; chronométrer 10 pas avant de s'engager.
- **1.10 Code :** SFT d'instructions de code plus mélange FIM à environ 0,5 en format PSM avec les jetons `<|trou_*|>`, évaluation par exécution en pass@k avec l'estimateur sans biais, code exécuté dans un sous-processus avec délai, répertoire jetable et objet Job Windows (tuer l'arbre de processus), présenté comme **limité** et non « sûr ».
- **Correctif `datasets` :** exiger `datasets>=5.1`, mélanger avant `skip`/`take`, accepter la perte du tampon de mélange à la reprise (ou ne pas mélanger le flux), `reshard()` pour les gros fichiers Parquet, et écrire un test de reprise (comparer deux exécutions) avant de documenter la garantie.
