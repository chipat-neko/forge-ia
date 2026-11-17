# La Forge IA, vague 2, plan 7 : le moteur qui rend ton IA utile

> **Pour les agents qui exécutent ce plan :** SOUS-SKILL REQUIS : utiliser superpowers:subagent-driven-development (recommandé) ou superpowers:executing-plans pour réaliser ce plan tâche par tâche. Les étapes utilisent des cases à cocher (`- [ ]`).

**But :** donner à `forge` tout ce qu'il faut pour affiner ton IA (conversation, préférences, raisonnement, code), puis l'affiner pour de vrai sur la RTX 5070 Ti et publier `ton-ia-1.7`, `ton-ia-1.8`, `ton-ia-1.9` et `ton-ia-1.10`, chacune repartant de la précédente.

**Architecture :**

- Tout le code nouveau vit dans `projets/forge`, en sous-paquets par sujet : `conversation` (gabarit, sources, conversations générées), `affinage` (empaquetage, jeux sur disque, recettes, DPO), `preferences`, `raisonnement` (problèmes, vérification, GRPO), `code` (bac à sable, pass@k, FIM, bancs). Les pièces communes à plusieurs sujets vont dans `forge/publication.py`, `forge/fragments.py`, `forge/pause.py` et `forge/hasard.py`.
- **Une seule boucle d'entraînement.** `forge entrainer` garde sa pause, sa reprise, son journal et ses sauvegardes. Un champ `methode` (`pre_entrainement`, `sft`, `dpo`, `grpo`) choisit les chargeurs, le pas d'optimisation et la validation dans un registre (`forge.entrainement.methodes`). Le pré-entraînement ne change pas de comportement.
- **Chaque étape repart d'une version publiée** (`depart`), téléchargée comme un lecteur la télécharge : 1.7 part de `ton-ia-1.5`, 1.8 de `ton-ia-1.7`, et ainsi de suite.
- Les données de chaque étape sont écrites sous `FORGE_DONNEES`, par fragments repris après une coupure. Un jeu réservé à l'évaluation ne peut pas entrer dans un entraînement : le code le refuse.
- Les chapitres (projets 1.7 à 1.10, notebooks, pages) viennent au plan 8. Ils utilisent les interfaces de ce plan, sous leurs noms exacts.

**Pile technique :** celle de la vague 1. Python 3.12, uv, pytest, PyTorch 2.15.0 (roues `cu132` et `cpu`), `datasets` 5.2 (verrou), `safetensors`, `numpy`, `regex`, `psutil`. Un nouvel extra `traduction`, avec `transformers==5.22.1`, sert seulement à la traduction maison de la tâche 20. Il n'est jamais installé en intégration continue.

**Spécification :** `docs/superpowers/specs/2026-11-02-forge-ia-design.md`, surtout les sections 3, 4 (« une seule IA qui grandit »), 8 (code, pause et reprise, versions publiées), 9 (honnêteté), 11 (machine) et 12 (vague 2). Plans précédents : p2 (`forge`), p5 (Partie 1) et p6 (reports de la vague 1, à exécuter **avant** ce plan).

## Place de ce plan dans la vague 2

- **Ordre :** plan 6, puis ce plan, puis le plan 8. Les interfaces du plan 6 sont acquises ici : `forge.fichiers` (`ecrire_atomique`, `remplacer`, `duree`, `nombre`), `forge.erreurs.DonneesManquantes`, `forge.chemins.sous_forge_donnees`, `forge.entrainement.sauvegarde.lire_sauvegarde`, la reprise du flux par `state_dict`, les bits par octet exacts, l'empreinte du tokenizer gardée dans les sauvegardes et vérifiée par `exporter`.
- **Le plan 8 avance en même temps**, sur le processeur, pendant que ce plan entraîne. Chaque tâche du plan 8 dit de quelles tâches de ce plan elle dépend.
- **Les tâches 12, 15, 17 et 22 sont les entraînements réels.** Ce sont les seules qui prennent la carte pendant des heures. Les autres tâches n'utilisent la carte que pour leurs tests `gpu`, carte libre.

## Recherche faite avant ce plan (le 17/11/2026)

Sources : `docs/superpowers/recherche/2026-11-17-vague-2-methodes.md` (« méthodes »), `…-vague-2-donnees.md` (« données ») et `…-vague-2-echelle.md` (« échelle »). Les étiquettes de la recherche sont gardées : **[lu]**, **[résumé]** (à relire dans la source avant de l'imprimer), **[non vérifié]**.

- **Versions** (« méthodes », §1) : PyTorch 2.15.0 et `datasets` 5.2.0 en local [lu]. Colab est en Python 3.13.18, `torch 2.14.1+cu130`, `datasets 4.8.5`, `transformers 5.22.1`, sans TRL [lu]. Les notebooks n'utilisent pas `datasets`.
- **Format chat** (« méthodes », §2.1 et 2.2) : le jeton de fin du gabarit doit être celui que la génération guette [lu, doc TRL]. La perte porte sur les seuls tours de l'assistant [lu]. Que la perte porte aussi sur `<|fin_tour|>` est une inférence de la recherche, adoptée ici et testée. Les embeddings des jetons spéciaux n'ont jamais été vus en entrée pendant le pré-entraînement (inférence de la recherche).
- **Empaquetage** (« méthodes », §2.3) : TRL emploie par défaut le « best-fit decreasing » (BFD) [lu]. La fuite d'une conversation vers la suivante sans masque d'attention par document est **[non vérifié]** : la tâche 3 la mesure au lieu de l'affirmer.
- **Taux d'apprentissage du SFT** : aucune source pour 400 à 500 M de paramètres entraînés de zéro (« méthodes », §2.4). D'où un balayage de 1e-5, 3e-5 et 1e-4.
- **DPO** (« méthodes », §3) : défauts de TRL `beta=0.1`, `learning_rate=1e-6`, perte `sigmoid` [lu]. Pièges : la vraisemblance de la réponse choisie peut baisser (DPOP, arXiv 2402.13228) [lu], et le biais de longueur, que corrige `sigmoid_norm` [lu]. Le meilleur beta à 433 M n'est pas publié : balayage de 0,05, 0,1 et 0,3. Qwen2.5 : environ 150 000 paires, une époque (« échelle », B2) [publié].
- **Raisonnement** (« méthodes », §4) : les modèles de 3 G ou moins apprennent mieux de chaînes courtes (arXiv 2502.12143) [lu]. GRPO à la nanochat (`scripts/chat_rl.py`, lu) : sans KL, sur la politique, perte au niveau du jeton, avantage `r − moyenne` sans division par l'écart-type ; 16 réponses par question, 16 questions par pas, 256 jetons, température 1,0, top-k 50 [lu]. Échec documenté du GRPO direct à 135 M (arXiv 2606.22189) [lu]. Le RL n'amplifie qu'un comportement déjà présent : il ne se lance que si le taux de réussite initial est non nul. Le coût d'un pas de RL sur cette carte n'est publié nulle part : il est mesuré.
- **Code** (« méthodes », §5) : l'estimateur sans biais de pass@k est dans le corps de l'article Codex (arXiv 2107.03374), **à relire** avant de l'écrire [non vérifié]. Le bac à sable de nanochat n'est « pas un vrai bac à sable » et repose sur `resource`, réservé à Unix [lu]. Sous Windows, les objets Job tuent tout un arbre de processus et limitent la mémoire, mais ne bloquent ni le réseau ni le disque [lu, Microsoft Learn]. FIM : article d'origine arXiv 2207.14255 [lu] ; taux de 0,5 en mode PSM chez DeepSeek-Coder [résumé].
- **Données** (« données ») :
  - `kurakurai/Luth-2-Post-Training-SFT` (CC BY 4.0, sauf les lignes venues de StackOverflow en CC BY-SA 4.0), réponses régénérées par des modèles Qwen ; environ 1 580 jetons par exemple en moyenne, un calcul de la recherche [lu] ;
  - `CohereLabs/aya_dataset` (Apache-2.0, humain) ; `OpenAssistant/oasst2` (Apache-2.0, humain, 360 invites racines françaises mesurées) ;
  - `OpenCoder-LLM/opc-sft-stage2`, sous-ensemble `educational_instruct` (MIT, triplets instruction, code, test validés) ;
  - évaluation : `kurakurai/IFEval-FR` (Apache-2.0, 235 invites, format IFEval), `lightonai/mgsm-rev2` config `fr` (CC BY-SA 4.0, 250), `cmh/gsm8k-platinum_fr` (MIT, traduction non documentée), `openai/openai_humaneval` (MIT, 164) ;
  - trous : messages système en français, consignes de code en français vérifiées, banc de code français sous licence claire.
- **Licences des générateurs** (« données », §0) : les sorties d'OpenAI et de Llama sont écartées. Qwen3 est sous Apache-2.0 d'après les fiches de Qwen3-32B, Qwen3-30B-A3B et Qwen3.6-35B-A3B [lu]. La licence de `Qwen/Qwen3-4B`, prise ici pour traduire, n'a pas été lue : la tâche 20 la lit d'abord.
- **Échelle** (« échelle », A1) : nanochat d20 (561 M, 11,2 G jetons) passe sur GSM8K de 2,50 % à 4,55 % (SFT) puis 7,58 % (RL), et sur HumanEval de 6,71 % à 8,54 % [publié]. TinyZero : 0,5 G n'apprend pas à raisonner, 1,5 G commence [publié, README].

## Décisions du contrôleur, reprises telles quelles (17/11/2026)

- **Données :** aucune donnée dont la licence contraint le nom ou l'usage du modèle publié. `CATIE-AQ/facebook-community-alignment-dataset_french_dpo` est écarté (réponses de Llama 3.3, clause 1.b.i). Les paires de 1.8 viennent de ton IA : deux réponses de ton-ia-1.7 par invite, classées par des contrôles programmés (consignes à la IFEval, langue française, longueur, réponse juste quand elle se vérifie). **Pas de juge** : la recherche ne justifie un juge ouvert que pour MT-Bench et pour un taux de victoire « avec juge clairement nommé », et un contrôle programmé fait ce travail sans mémoire de carte en plus.
- **Jeux réservés à l'évaluation :** MGSM (CC BY-SA) et tout jeu sans licence claire ne servent qu'à l'évaluation. Le code le garde (champ `usage`).
- **Les trous** se comblent par génération programmée (messages système, identité, problèmes) ou par traduction maison (consignes de code, HumanEval). Le traducteur est sous une licence qui le permet, et c'est documenté.
- **Honnêteté :** les gains attendus sont petits. On publie ce qui est mesuré, même décevant. Le RL de 1.9 ne se lance que si le taux de réussite initial est non nul ; sinon le chapitre le montre.
- **Chaque entraînement long** a une version courte (environ une heure) et une version complète. Avant chaque travail de plus de 30 minutes : essai chronométré sur la carte et sur le processeur (16 fils), le plus rapide est pris, les chiffres sont notés. Durées et tailles mesurées, pas supposées.
- **PC partagé :** au « stop », l'entraînement se met en pause, l'agent en cours finit, aucun nouveau ne part ; au « go », on reprend.
- **Exécution sous Windows** du code généré : sous-processus avec délai et objet Job. C'est « limité », pas « sûr ».
- **Exécution :** subagent-driven-development, une relecture par tâche, une revue finale. Tout s'exécute sans question après la validation du plan ; le contrôleur pousse et publie les Releases.

## Choix de ce plan

1. **Le départ est la version publiée, téléchargée.** `forge publication --etiquette ton-ia-1.5` télécharge la Release dans `FORGE_DONNEES/publications/ton-ia-1.5/`, exactement comme un lecteur, et 1.7 part de là (poids bf16 passés en float32). Les versions intermédiaires (le SFT de 1.9 avant GRPO) sont exportées en local sous `publications/`, sans Release.
2. **Le gabarit.** Une conversation commence par `<|fin_texte|>`, le jeton de début des textes de ton IA depuis 1.5 (`forge.evaluation.qcm.JETON_DE_DEBUT`). Chaque tour est `<|rôle|>` + texte + `<|fin_tour|>`. La pensée d'un tour de l'assistant est `<|pensee|>` + trace + `<|fin_pensee|>`, avant le texte. La perte porte sur le contenu de l'assistant et sur son `<|fin_tour|>`, jamais sur les marqueurs de rôle. `<|debut_texte|>` reste inutilisé.
3. **FIM, format PSM :** `<|fin_texte|><|trou_prefixe|>` P `<|trou_suffixe|>` S `<|trou_milieu|>` M `<|fin_tour|>`, perte sur M et `<|fin_tour|>` seulement. `<|fin_tour|>` est l'unique jeton d'arrêt de la génération à partir de 1.7.
4. **Empaquetage BFD avec masque d'attention par document**, rangées de 2 048 jetons. Un exemple plus long qu'une rangée est écarté et compté, jamais coupé : une réponse coupée apprendrait à s'arrêter au milieu.
5. **La perte de SFT est une moyenne par jeton appris sur tout le pas** (somme des pertes des jetons appris ÷ leur nombre, tous micro-lots compris), et non une moyenne de moyennes par micro-lot.
6. **DPO maison :** perte `sigmoid` plus un terme SFT sur la réponse choisie (poids 1,0, comme `loss_type=["sigmoid","sft"]` de TRL sans `loss_weights`, à relire dans la doc avant le chapitre), variante normalisée par la longueur en option. Log-probabilités de référence précalculées une fois, rangées à côté du jeu.
7. **Mini-GRPO à la nanochat**, récompense 1 ou 0 (réponse juste), sur des problèmes générés plus faciles que GSM8K.
8. **Contrôles programmés, pas de juge.** `langue()` est une règle simple de mots outils, que le chapitre peut expliquer et que le site refait à l'identique.
9. **Traduction maison** par `Qwen/Qwen3-4B` (tient en bf16 sur 16 Go), révision épinglée, sous réserve de sa licence (tâche 20). On traduit les consignes de `educational_instruct` (le code et les tests ne changent pas, puis on réexécute les tests) et les docstrings de HumanEval (HumanEval-FR).
10. **Les jeux faits maison sont publiés** dans une Release de données, `donnees-ton-ia-2` : HumanEval-FR et les consignes de code traduites, avec leurs licences (MIT pour les deux, celle des sources) et la façon de les refaire. Les lecteurs et les notebooks les téléchargent au lieu de refaire tourner Qwen3.
11. **Des réglages sans source, assumés :** décroissance des poids 0,0 pendant l'affinage (on ne tire pas les poids vers 0, loin de ton IA d'avant) ; deux époques de SFT ; taux de GRPO choisi entre 1e-6 et 5e-6 par un essai de 30 pas chacun.
12. **Évaluations communes à toutes les étapes.** `forge evaluer-etape` passe les mêmes mesures sur ton-ia-1.5 et sur chaque nouvelle version : le plan 8 montre ainsi ton IA à travers les chapitres (avant et après, sur les mêmes tests).

## Écarts assumés avec la spécification

- **Une Release de données** (`donnees-ton-ia-2`, choix 10), en plus des Releases de modèles. Les données de tiers restent téléchargées par des scripts, jamais versionnées ni republiées.
- **La version courte d'une heure** affine le vrai modèle (433,6 M) : elle demande une carte d'environ 12 Go. La mémoire maximale mesurée est publiée. Il n'y a pas de « mini » affinée.
- **FIM n'arrive qu'à l'affinage de 1.10**, alors que l'article d'origine conseille de l'inclure dès le pré-entraînement. Le tokenizer prévoyait les jetons ; le pré-entraînement de 1.5 ne s'en est pas servi. Le chapitre 1.10 le dit.

## Contraintes globales

- **À ne jamais modifier :** le tokenizer figé `projets/forge/forge/ressources/tokenizer-ton-ia-v1.json` ; ce que `forge exporter` écrit pour une sauvegarde donnée ; l'architecture du modèle (noms et formes des poids) ; le comportement du pré-entraînement (les tests existants de `forge` restent verts sans être changés).
- **Licences :** un jeu d'entraînement porte sa licence et son lien. Sont écartés les jeux dont les invites ou les réponses viennent de Llama ou d'OpenAI, les licences NC, et les jeux sans licence. CC BY-SA et « sans licence claire » : évaluation seulement.
- **Jeux réservés à l'évaluation** (`usage="evaluation"`) : IFEval-FR, MGSM-rev2, GSM8K-Platinum-fr, HumanEval, HumanEval-FR, et les problèmes générés à partir de `GRAINES_EVALUATION`. Aucun chemin du code ne les met dans un jeu d'entraînement ni dans une invite de 1.8.
- **Langue :** noms, commentaires et messages en français. Un message d'erreur dit ce qui se passe et quoi faire ensuite. Les sorties à l'écran utilisent l'espace fine (`\u202f`) comme la vague 1.
- **Les tests d'abord.** Tests rapides sur le processeur, sans réseau ; les tests `gpu` sont sautés sans CUDA. Les tests qui lancent des sous-processus prennent un délai d'au plus 2 s.
- **Commandes :**
  - dans `projets/forge` : `uv run --extra gpu pytest -q -m "not gpu"` (jamais `--extra cpu` en local : le `.venv` de forge garde PyTorch pour la carte, et le repasser en processeur coûte 36 min de copie sur le disque D:), et `uv run --extra gpu pytest -q -m gpu` carte libre (`nvidia-smi` sous 10 %) ;
  - **Renommer ou déplacer une fonction de forge** casse le site s'il la montre : `CodeExplique` extrait le code de forge par son nom (`symbole=`). Avant tout renommage, chercher le nom dans `site/src`, `site/e2e`, `projets/` et `docs/mesures/`, et mettre à jour chaque référence dans le même commit, avec `npx vitest run src/lib/symboles.test.ts` (leçon de la tâche 4 du plan 6).
  - avant toute commande forge, PowerShell : `. .\outils\env-forge.ps1; $env:TEMP = $env:TMP = "$env:FORGE_DONNEES\cache\tmp"` ;
  - pour les travaux longs, le Python de `projets/forge/.venv` (pas `uv run`, D: est en exFAT : une resynchronisation recopie tout).
- **Données sous `FORGE_DONNEES`**, rangées par `sous_forge_donnees` : `conversations/`, `problemes/`, `affinage/`, `publications/`, `entrainements/`, `evaluations/`. Rien de lourd dans git.
- **Travaux longs :** atomiques et repris. Un fichier n'est complet qu'avec son marqueur `.complet`. Ctrl+C finit le lot en cours, écrit, et affiche la commande de reprise.
- **Le README de forge** reçoit chaque commande nouvelle dans la tâche qui la crée, avec un exemple exact. Les commandes d'une étape réelle (fichiers `configs/*.toml`, étiquettes de version) y entrent dans sa tâche sur la carte (12, 15, 17, 20, 22). Le plan 8 recopie ces lignes telles quelles (`commandes.test.ts` le vérifie).
- **Règle de l'utilisateur (plus de 30 minutes) :** un essai chronométré sur la carte et sur le processeur (16 fils, charge par cœur relevée), carte au repos, puis le plus rapide ; chiffres notés dans `docs/mesures/`.
- **Go et stop :** au « stop », chien de garde arrêté, travail long en pause (`pause-entrainement.ps1`), l'agent en cours finit, aucun nouveau ne part ; au « go », reprise (`travail-long.ps1 -Reprendre`), chien de garde relancé, puis les agents.
- **Carte partagée :** une durée mesurée pendant qu'un autre programme utilise la carte est fausse ; on la remesure carte au repos.
- **Commits :** adresse `268342383+chipat-neko@users.noreply.github.com` ; message en français terminé par `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` ; fins de ligne LF ; `git add <fichiers>` puis `git commit -m "…" -- <fichiers>`. Seul le contrôleur pousse et publie.

## Points à surveiller à la relecture

1. **Un texte d'utilisateur qui contient `<|fin_tour|>`, `<|assistant|>` ou `<|pensee|>`** : il est encodé comme du texte, jamais comme un jeton spécial, et le masque n'en dépend pas. Test en tâche 2.
2. **Un exemple sans jeton appris, plus long qu'une rangée, ou un pas dont aucun jeton n'est appris** : jamais de NaN ni d'arrêt « perte infinie » ; l'exemple est écarté à la préparation et compté. Tests en tâches 5 et 6.
3. **Pause et reprise au milieu de chaque nouvelle méthode**, y compris les tirages de GRPO et la construction des paires de 1.8 : reprise exacte sur le processeur, sans paire en double ni en moins. Tests en tâches 6, 13, 14 et 16.
4. **Du code généré qui boucle, lance des processus, prend 2 Go, écrit des mégaoctets ou écrit hors de son dossier** : arrêté au délai, mémoire bornée, sortie tronquée, dossier jetable effacé, aucun processus survivant sous Windows. Ce qui n'est pas empêché (réseau, écriture ailleurs) est dit. Test en tâche 18.
5. **Un jeu d'évaluation qui entre dans un entraînement**, directement, par une invite de 1.8, ou par un quasi-doublon (8-grammes de mots) : refus explicite, ou exemple écarté et compté. Tests en tâches 10, 13 et 20.

## Durées estimées (à remesurer)

Ces estimations ne servent qu'à prévoir. Les vraies durées sont mesurées par les essais chronométrés.

| Travail | Estimation | Ce sur quoi elle repose |
| --- | --- | --- |
| SFT 1.7 complet | environ 3 h | environ 180 millions de jetons de rangées (2 époques d'environ 90 millions), au débit **mesuré** du pré-entraînement du même modèle sur la même carte : 17 316 jetons/s (`docs/mesures/ton-ia-1.5.md`). Le masque par document peut ralentir l'attention : non mesuré. |
| Balayage du taux de 1.7 | environ 1 h | 3 essais de 300 pas de 65 536 jetons, au même débit. |
| Paires de 1.8 | environ 1 h | 2 × 40 000 réponses d'au plus 384 jetons. Le débit de la génération par lots avec cache n'est mesuré nulle part : environ 3 000 jetons/s est une hypothèse. |
| DPO 1.8 | environ 1 h 30 | balayage de 6 essais courts plus une époque d'environ 18 millions de jetons (12 000 paires × 2 × 768). |
| SFT 1.9 | environ 30 min | environ 20 millions de jetons. |
| GRPO 1.9 | environ 3 h | 400 pas d'environ 25 s : 256 séquences de 256 jetons générées par lots de 32 (hypothèse de génération ci-dessus), plus l'apprentissage sur environ 90 000 jetons au débit mesuré. |
| Traduction 1.10 | 1 à 2 h | environ 6 millions de jetons produits par Qwen3-4B ; aucun débit mesuré. |
| SFT 1.10 | environ 3 h | environ 200 millions de jetons de rangées, au débit mesuré. |
| Versions courtes | 4 × 1 h | une heure chacune, par construction. |
| Évaluations | environ 2 h en tout | IFEval-FR, problèmes, MGSM, HumanEval sur les cinq versions. |

Soit environ 22 heures de carte, étalées sur plusieurs jours avec les pauses de jeu.

## Fichiers

```
projets/forge/forge/
  publication.py                 versions publiées : charger, télécharger (tâche 1)
  conversation/format.py         gabarit, masque, invite, réponse (tâche 2)
  modele/transformer.py          masque par document, avancer() (tâches 3 et 4)
  modele/cache.py, modele/generation_lot.py   cache KV, génération par lots (tâche 4)
  affinage/empaquetage.py, affinage/jeu.py    BFD, jeux sur disque, chargeurs (tâche 5)
  entrainement/methodes.py       registre des méthodes, SFT (tâche 6)
  entrainement/boucle.py         methode, depart, --arreter-apres (tâche 6)
  fragments.py, pause.py         sorties par fragments, Ctrl+C (tâche 7)
  conversation/sources.py, conversation/telechargement.py   jeux HF (tâche 7)
  hasard.py, evaluation/langue.py, evaluation/consignes.py   (tâche 8)
  raisonnement/problemes.py, raisonnement/verification.py    (tâche 9)
  conversation/generees.py, affinage/recettes.py             (tâche 10)
  evaluation/reponses.py, evaluation/etape.py                (tâche 11)
  preferences/invites.py, preferences/noter.py, preferences/construction.py (tâche 13)
  affinage/dpo.py                (tâche 14)
  raisonnement/grpo.py           (tâche 16)
  code/execution.py, code/passk.py   (tâche 18)
  code/fim.py                    (tâche 19)
  donnees/traduction.py          (tâche 20)
  code/bancs.py                  (tâche 21)
projets/forge/configs/  sft-1.7.toml, sft-1.7-court.toml, dpo-1.8.toml, dpo-1.8-court.toml,
  sft-1.9.toml, sft-1.9-court.toml, grpo-1.9.toml, grpo-1.9-court.toml, sft-1.10.toml, sft-1.10-court.toml
projets/forge/tests/   un fichier de test par module nouveau (test_publication.py, test_conversation.py…)
docs/donnees.md        section « Vague 2 : affiner ton IA »
docs/mesures/          ton-ia-1.7.md … ton-ia-1.10.md et leurs LISEZMOI, donnees-ton-ia-2-LISEZMOI.md
D:\forge-ia-donnees\journaux\   travail-long.ps1 (nouveau), pause-entrainement.ps1, chien-de-garde.py (hors dépôt)
```

---

### Tâche 1 : les versions publiées

**Fichiers :** créer `forge/publication.py`, `tests/test_publication.py` ; modifier `forge/__main__.py` (commande `publication`), `projets/forge/README.md`.

**Interfaces (produites) :**

- `DEPOT = "chipat-neko/forge-ia"` ; `ETIQUETTES = ("ton-ia-1.5", "ton-ia-1.7", "ton-ia-1.8", "ton-ia-1.9", "ton-ia-1.10")` ; `VARIABLE_DES_VERSIONS = "FORGE_IA_MODELES"`.
- `nom_des_poids(etiquette: str) -> str` : `f"{etiquette}.safetensors"`.
- `@dataclass class Publication: modele: Transformer; tokenizer: TokenizerOctets; version: str; empreinte_des_poids: str` (`version` : le nom du fichier des poids sans `.safetensors`).
- `charger_publication(dossier: Path, appareil: str = "cpu") -> Publication`. Il demande exactement un fichier `*.safetensors`, `config.json` et `tokenizer-ton-ia-v1.json` (empreinte `EMPREINTE_DU_TOKENIZER` de `forge.exporter`). Les poids liés sont rétablis, les poids passent en float32, et le modèle est rendu en mode évaluation. Comme `charger_ton_ia` du projet 1.6, qui ne change pas.
- `telecharger_fichiers(etiquette: str, noms: Sequence[str], dossier: Path | None = None) -> Path` :
  - si `FORGE_IA_MODELES` est posée, il rend `Path(env) / etiquette` sans réseau, ou lève `FileNotFoundError` si ce dossier ou un des fichiers manque ;
  - sinon il télécharge chaque fichier depuis `https://github.com/{DEPOT}/releases/download/{etiquette}/{nom}`, dans `dossier` (par défaut `sous_forge_donnees(etiquette, "publications")`), avec un délai de socket de 60 s et un fichier `.partiel` renommé une fois complet ; un fichier déjà complet ne se retélécharge pas.
  Il sert aussi pour la Release de données `donnees-ton-ia-2` (tâche 20).
- `telecharger_publication(etiquette: str, dossier: Path | None = None) -> Path` : `telecharger_fichiers` des trois fichiers d'une version de ton IA.
- `python -m forge publication --etiquette ton-ia-1.5 [--dossier D]` : affiche chaque fichier, sa taille et son empreinte SHA-256.

- [ ] **Étape 1 : tests rouges.**

```python
def test_aller_retour_d_une_publication(tmp_path):
    modele = petit_modele_sauvegarde(tmp_path)          # aide de test : Transformer minuscule + sauvegarde .pt
    exporter(tmp_path / "s.pt", tmp_path / "pub", nom_des_poids("ton-ia-9.9"))
    pub = charger_publication(tmp_path / "pub")
    attendu = arrondi_bf16(modele)                       # mêmes poids, passés par bf16 puis float32
    assert pub.version == "ton-ia-9.9" and len(pub.empreinte_des_poids) == 64
    assert torch.equal(pub.modele(IDS)[0], attendu(IDS)[0])

def test_deux_fichiers_de_poids_refuses(tmp_path): ...   # ValueError qui nomme les deux fichiers
def test_tokenizer_change_refuse(tmp_path): ...          # ValueError qui cite l'empreinte attendue
def test_telechargement_coupe_puis_repris(tmp_path, monkeypatch): ...
    # urlretrieve simulé : coupe au 2e fichier ; aucun fichier final à moitié écrit ;
    # la relance ne retélécharge que ce qui manque
def test_variable_des_versions(tmp_path, monkeypatch): ... # FORGE_IA_MODELES : aucun appel réseau
```

- [ ] **Étape 2 : vérifier l'échec**, avec `uv run --extra gpu pytest -q -m "not gpu" tests/test_publication.py`.
- [ ] **Étape 3 : écrire le module, la commande et la section du README** (« Recharger une version publiée », qui remplace le script d'exemple par `charger_publication`).
- [ ] **Étape 4 : vérifier** que tous les tests de forge passent.
- [ ] **Étape 5 : commit**, « Forge : charger et télécharger une version publiée de ton IA ».

### Tâche 2 : le format de conversation

**Fichiers :** créer `forge/conversation/__init__.py`, `forge/conversation/format.py`, `tests/test_conversation.py`.

**Interfaces (produites) :**

- `@dataclass(frozen=True) class Tour: role: Literal["systeme", "utilisateur", "assistant"]; texte: str; pensee: str | None = None` (`pensee` : seulement pour un tour de l'assistant).
- `@dataclass(frozen=True) class ExempleMasque: ids: list[int]; appris: list[bool]` (même longueur ; `appris[i]` vrai si le jeton `ids[i]` est une cible apprise).
- `@dataclass(frozen=True) class Reponse: texte: str; pensee: str | None; ids: list[int]; terminee: bool`.
- `JETON_DE_DEBUT = "<|fin_texte|>"`.
- `verifier_conversation(tours: Sequence[Tour], pour_apprendre: bool = True) -> None` : au plus un tour `systeme`, en premier ; puis `utilisateur` et `assistant` en alternance, en commençant par `utilisateur` ; textes non vides après `strip()` ; `pensee` seulement chez l'assistant ; avec `pour_apprendre`, le dernier tour est de l'assistant. Sinon `ValueError` avec un message qui nomme le tour fautif (son rang, à partir de 1).
- `encoder_conversation(tok: TokenizerOctets, tours: Sequence[Tour]) -> ExempleMasque` : `[<|fin_texte|>]`, puis pour chaque tour `[<|rôle|>]` + (pour l'assistant avec pensée : `<|pensee|>` + `encoder(pensee)` + `<|fin_pensee|>`) + `encoder(texte)` + `[<|fin_tour|>]`. Appris : tout ce qui suit `<|assistant|>` jusqu'à son `<|fin_tour|>` compris.
- `invite_de_reponse(tok, tours) -> list[int]` : les tours (le dernier est de l'utilisateur), encodés de même, puis `<|assistant|>`. Vérifiés avec `pour_apprendre=False`.
- `lire_reponse(tok, ids_generes: Sequence[int]) -> Reponse` : coupe au premier `<|fin_tour|>` (exclu, `terminee=True`) ; si les ids commencent par `<|pensee|>`, la pensée va jusqu'à `<|fin_pensee|>` ; le texte se décode sans jetons spéciaux (ils sont retirés, pas décodés en leur nom).
- `conversation_vers_json(tours) -> dict` (`{"tours": [{"role", "texte", "pensee"?}]}`) et `conversation_depuis_json(d) -> list[Tour]`.

- [ ] **Étape 1 : tests rouges.**

```python
TOK = TokenizerOctets.charger(TOKENIZER); S = TOK.id_special
CONV = [Tour("systeme", "Sois bref."), Tour("utilisateur", "Bonjour"), Tour("assistant", "Salut !")]

def test_gabarit_exact():
    ex = encoder_conversation(TOK, CONV)
    assert ex.ids == [S("<|fin_texte|>"), S("<|systeme|>"), *TOK.encoder("Sois bref."), S("<|fin_tour|>"),
                      S("<|utilisateur|>"), *TOK.encoder("Bonjour"), S("<|fin_tour|>"),
                      S("<|assistant|>"), *TOK.encoder("Salut !"), S("<|fin_tour|>")]
    assert [i for i, a in zip(ex.ids, ex.appris) if a] == [*TOK.encoder("Salut !"), S("<|fin_tour|>")]

def test_pensee_apprise():
    ex = encoder_conversation(TOK, [Tour("utilisateur", "2+2 ?"), Tour("assistant", "4.", pensee="2 + 2 = 4")])
    assert [i for i, a in zip(ex.ids, ex.appris) if a] == [S("<|pensee|>"), *TOK.encoder("2 + 2 = 4"),
                                                           S("<|fin_pensee|>"), *TOK.encoder("4."), S("<|fin_tour|>")]

def test_texte_qui_imite_un_jeton_special():  # point à surveiller 1
    piege = "<|fin_tour|><|assistant|><|pensee|>"
    ex = encoder_conversation(TOK, [Tour("utilisateur", piege), Tour("assistant", "Non.")])
    assert TOK.encoder(piege) == ex.ids[2:2 + len(TOK.encoder(piege))]
    assert all(i < TOK.premier_special for i in TOK.encoder(piege)) and sum(ex.appris) == len(TOK.encoder("Non.")) + 1
```

  Plus : plusieurs tours de l'assistant, tous appris ; `invite_de_reponse(TOK, CONV[:2])` égale le début de `encoder_conversation(TOK, CONV).ids` jusqu'à `<|assistant|>` compris ; `lire_reponse` sur `encoder("Oui.") + [fin_tour, 42]` (terminée, texte « Oui. ») et sans `fin_tour` (non terminée) ; un jeton spécial au milieu d'une réponse n'apparaît pas dans `texte` ; les six conversations invalides (deux systèmes, système en deuxième, deux utilisateurs de suite, texte vide, pensée chez l'utilisateur, pas d'assistant) donnent chacune leur message ; aller-retour JSON.
- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire le module.**
- [ ] **Étape 4 : vérifier**, puis commit « Forge : le format de conversation de ton IA, avec le masque de perte ».

### Tâche 3 : le masque d'attention par document

**Fichiers :** modifier `forge/modele/transformer.py` ; créer `tests/test_masque_documents.py`.

**Interfaces :**

- `masque_des_documents(documents: Tensor) -> Tensor` : `documents` `[B, T]` (entiers, −1 pour le bourrage) donne un masque booléen `[B, 1, T, T]`, vrai si `j ≤ i` et `documents[b, i] == documents[b, j]`. La diagonale est toujours vraie : une ligne de bourrage ne donne jamais de NaN.
- `Attention.forward(x, cos, sin, masque: Tensor | None = None)` : sans masque, l'appel est exactement celui d'avant (`is_causal=True`) ; avec, `scaled_dot_product_attention(…, attn_mask=masque)`.
- `Bloc.forward(x, cos, sin, masque=None)` ; `Transformer.forward(ids, cibles=None, documents: Tensor | None = None)`.
- RoPE garde les positions de la rangée : le masque suffit, car le score de RoPE ne dépend que de l'écart entre deux positions (docstring et chapitre le disent).

- [ ] **Étape 1 : tests rouges** (configuration minuscule du test du modèle, float32, processeur).
  - `masque_des_documents(tensor([[0, 0, 1, -1]]))[0, 0]` vaut la matrice attendue, écrite dans le test.
  - Une rangée « A puis B puis bourrage », avec `documents` : les logits des positions de B égalent ceux de B seul à 1e-5 près.
  - La même rangée sans `documents` : l'écart dépasse 1e-3 (la fuite existe, et le test la mesure).
  - `documents` tout à 0 : mêmes logits que sans `documents`, à 1e-5 près.
  - Les tests existants de `test_modele.py` passent sans changement.
- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire.** Un test `gpu` vérifie en plus, en bf16 sur la carte, que le chemin masqué tourne et que sa mémoire maximale pour une rangée de 2 048 jetons du preset `tres_grand` est notée dans le rapport de la tâche.
- [ ] **Étape 4 : vérifier**, commit « Forge : masque d'attention par document, pour empaqueter les conversations ».

### Tâche 4 : la génération par lots, avec cache

**Fichiers :** créer `forge/modele/cache.py`, `forge/modele/generation_lot.py`, `tests/test_generation_lot.py` ; modifier `forge/modele/transformer.py`, `forge/modele/__init__.py`.

**Interfaces :**

- `class CacheKV(config: ConfigModele, lot: int, longueur_max: int, appareil, dtype)` : `k` et `v` de forme `[couches, lot, tetes, longueur_max, dim_tete]`, `longueur: int` (positions déjà remplies), `ajouter(couche: int, k: Tensor, v: Tensor) -> tuple[Tensor, Tensor]` (rend les clés et valeurs de toutes les positions remplies, celles-ci comprises).
- `rope_cos_sin_aux_positions(positions: Tensor, dim_tete: int, base: float) -> tuple[Tensor, Tensor]`, de forme `[B, 1, T, dim_tete // 2]`.
- `Attention.forward(x, cos, sin, masque=None, cache: CacheKV | None = None, couche: int = 0)` ; `Bloc.forward(…, cache=None, couche=0)`.
- `Transformer.avancer(ids: Tensor, positions: Tensor, masque: Tensor, cache: CacheKV) -> Tensor` : les logits `[B, T, V]` des jetons donnés, le cache rempli d'autant.
- `generer_lot(modele, invites: Sequence[Sequence[int]], n_nouveaux: int, temperature: float = 1.0, top_k: int = 50, graine: int = 0, arret: int | None = None, lot: int = 32) -> list[list[int]]` :
  - invites complétées à gauche par `<|bourrage|>`, masquées ; positions comptées à partir du premier vrai jeton de chaque invite ;
  - un générateur `torch.Generator` semé par `graine`, sous-lots traités dans l'ordre : le résultat dépend de `lot`, et la docstring le dit ;
  - chaque sortie s'arrête après le premier `arret` (compris) ;
  - `ValueError` si une invite est vide ou si `len(invite) + n_nouveaux` dépasse `longueur_contexte` (pas de fenêtre glissante par lots).
  - Modèle en évaluation pendant l'appel, sous `autocast` de `forge.evaluation.perte`, aucun gradient ; chaque sous-module retrouve son mode après.

- [ ] **Étape 1 : tests rouges** (processeur, float32, modèle minuscule semé).
  - En glouton (`temperature=0`), `generer_lot` égale `generer(…, temperature=0)` invite par invite, pour cinq invites de longueurs 1, 3, 7, 12 et 20.
  - Les logits de `avancer` pas à pas égalent ceux de `forward` sur la suite entière, à 1e-4 près.
  - `lot=1` et `lot=5` donnent les mêmes sorties en glouton ; la même `graine` donne la même sortie à température 1.
  - Coupure après `arret` ; invite vide et invite trop longue refusées avec leur message.
- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire.** Un test `gpu` mesure, pour `tres_grand` en bf16, 32 invites de 128 jetons et 256 nouveaux : jetons générés par seconde et mémoire maximale, écrits dans le rapport de la tâche. C'est la première mesure du débit de génération : le contrôleur la reporte dans le ledger, à la place de l'hypothèse de 3 000 jetons/s des durées estimées.
- [ ] **Étape 4 : vérifier**, commit « Forge : génération par lots avec cache des clés et des valeurs ».

### Tâche 5 : les jeux d'affinage sur disque

**Fichiers :** créer `forge/affinage/__init__.py`, `forge/affinage/empaquetage.py`, `forge/affinage/jeu.py`, `tests/test_affinage_jeu.py`.

**Interfaces :**

- `@dataclass(frozen=True) class Rangee: ids: list[int]; appris: list[bool]; documents: list[int]`, de longueur `longueur + 1` chacune.
- `empaqueter(exemples: Sequence[ExempleMasque], longueur: int, bourrage: int) -> tuple[list[Rangee], int]` : BFD. Les exemples sont triés par longueur décroissante (à égalité, par rang d'origine). Chacun va dans la rangée où il laisse le moins de place libre, sinon dans une nouvelle. Les documents sont numérotés à partir de 0 dans chaque rangée ; le bourrage a `appris=False` et le document −1. Un exemple de plus de `longueur + 1` jetons, ou sans jeton appris, est écarté : le second nombre rendu les compte.
- Format sur disque, `VERSION_DU_JEU = 1`, sous `sous_forge_donnees(nom, "affinage")` :
  - `<partie>/ids.bin` (`uint16`), `<partie>/appris.bin` (`uint8`), `<partie>/documents.bin` (`int16`), pour les parties `train` et `val`, rangée après rangée ;
  - `index.json` : `version`, `sorte` (`"sft"` ou `"dpo"`), `longueur`, `rangees` (par partie), `exemples`, `jetons`, `jetons_appris`, `ecartes`, `sources` (nom → exemples, licence, lien), et `tokenizer` (`empreinte`, `nom`, `taille_vocabulaire`, **le même bloc** que l'index des jetons de pré-entraînement, pour la vérification d'`exporter` du plan 6) ;
  - `.complet`.
- `ecrire_jeu(dossier: Path, train: Sequence[Rangee], val: Sequence[Rangee], sorte: str, infos: dict, tok: TokenizerOctets) -> None` : écritures par `ecrire_atomique`, `verifier_place` avant ; `.complet` en dernier.
- `lire_index(dossier: Path) -> dict` : `DonneesManquantes` sans `.complet`, `ValueError` sur une version inconnue (message : refais `forge preparer`).
- `@dataclass class LotAffinage: ids: LongTensor; cibles: LongTensor; documents: LongTensor; reference: Tensor | None`. Entrées `ids = rangée[:-1]`, `cibles[t] = rangée[t+1]` si `appris[t+1]`, sinon −100 ; `documents = documents[:-1]`.
- `class ChargeurAffinage(dossier: Path, partie: str, taille_lot: int, graine: int)` : `lot() -> LotAffinage`, `etat() -> dict`, `restaurer(etat) -> None`, `rangees: int`. Ordre tiré de `(graine, époque)` comme `ChargeurJetons`. Pour `sorte="dpo"`, `taille_lot` doit être pair, les rangées vont par paires (choisie, rejetée) et sont mélangées par paires. `reference` est lu dans `reference.bin` s'il existe (tâche 14).

- [ ] **Étape 1 : tests rouges.**

```python
def test_bfd_exact():
    rangees, ecartes = empaqueter([ex(5), ex(4), ex(3), ex(2), ex(1)], longueur=5, bourrage=B)  # capacité 6
    assert [longueurs_des_documents(r) for r in rangees] == [[5, 1], [4, 2], [3]] and ecartes == 0

def test_trop_long_et_sans_appris_ecartes(): ...   # ex(7) et un exemple tout « non appris » : écartés = 2
def test_cibles_masquees(tmp_path): ...            # −100 partout où appris est faux, bourrage compris
def test_reprise_du_chargeur(tmp_path): ...        # 5 lots, etat(), 5 lots ; restaurer : les 5 mêmes
def test_paires_restent_ensemble(tmp_path): ...    # sorte dpo : rangées 2k et 2k+1 toujours dans le même lot, à la suite
def test_index_partage_le_bloc_tokenizer(tmp_path): ...  # même clé et même empreinte que forge.donnees.jetons
```
- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire.**
- [ ] **Étape 4 : vérifier**, commit « Forge : empaquetage BFD et jeux d'affinage sur disque, avec reprise ».

### Tâche 6 : les méthodes d'entraînement, et le SFT

**Fichiers :** créer `forge/entrainement/methodes.py`, `tests/test_methodes.py`, `tests/test_sft.py` ; modifier `forge/entrainement/boucle.py`, `forge/entrainement/__init__.py`, `forge/__main__.py`, `projets/forge/README.md`.

**Interfaces :**

- `ConfigEntrainement` gagne :
  - `methode: str = "pre_entrainement"`, parmi les clés de `METHODES` ;
  - `depart: str | None = None` : un dossier de version publiée (un nom va sous `publications/`). Obligatoire pour `sft`, `dpo` et `grpo` ; interdit pour `pre_entrainement` ;
  - `longueur: int | None = None` : la longueur des rangées (par défaut, le contexte du modèle). À la création des chargeurs, elle doit égaler celle de l'index du jeu ;
  - `dpo: dict | None = None` et `grpo: dict | None = None`, tables du TOML converties dans `__post_init__` en `ReglagesDPO` (tâche 14) et `ReglagesGRPO` (tâche 16) ;
  - `jetons_total` et `taille_lot_jetons` deviennent `int | None = None` : obligatoires sauf pour `grpo`, interdits pour `grpo` (le nombre de pas vient de `[grpo] pas`) ;
  - `dossier_donnees` : `jetons/` pour le pré-entraînement, `affinage/` pour `sft` et `dpo`, `problemes/` pour `grpo` ;
  - `depart` rejoint `REGLAGES_LIBRES` (le chemin peut changer à la reprise ; la version est vérifiée par la sauvegarde).
- `@dataclass(frozen=True) class Methode` : `nom`, `creer_chargeurs(config) -> tuple[train, val | None]`, `preparer(config, modele, appareil, journal) -> dict` (le contexte de la méthode), `pas(modele, optimiseur, chargeur, config, taux_du_pas, appareil, contexte) -> dict` (au moins `"perte"`), `valider(modele, chargeur_val, depart_val, appareil, config, contexte) -> dict` (`"perte_val"` ou `"reussite_val"`), `plus_grand_est_meilleur: bool`.
- `METHODES: dict[str, Methode]` et `enregistrer_methode(m: Methode) -> None`. Cette tâche enregistre `pre_entrainement` (le code d'avant, déplacé sans changement) et `sft`.
- Le départ : `charger_publication`, dimensions égales à `config.modele`, sinon `ValueError` (« La version de départ … a d'autres dimensions que le preset … »). Les poids sont copiés avant de créer l'optimiseur.
- Les sauvegardes retiennent en plus `methode`, `depart_version` et `depart_empreinte`. Pour les méthodes d'affinage, `empreinte_du_tokenizer` (plan 6) vient du tokenizer de la version de départ, vérifié égal à celui de l'index du jeu.
- `pas_sft` : lit d'abord les `accumulation` micro-lots, compte les jetons appris `N` du pas, puis pour chaque micro-lot fait `backward` de (somme des pertes de ses jetons appris) ÷ `N`. Rend `{"perte", "jetons_appris"}`. Le calcul de la perte est fait par la méthode depuis les logits (`reduction="sum"`, en float32), pas par `Transformer.forward`. `N == 0` est une `ValueError` qui dit de refaire `forge preparer`, impossible par construction des jeux.
- `perte_sft_validation(modele, chargeur_val, depart, n_rangees: int, appareil) -> float` : perte moyenne par jeton appris sur les `n_rangees` premières rangées de validation (`MORCEAUX_DE_VALIDATION` au plus).
- `python -m forge entrainer --config C [--reprendre] [--arreter-apres N]` (pour les essais chronométrés).

- [ ] **Étape 1 : tests rouges.**

```python
def test_sft_reprise_exacte(tmp_path):
    a = entrainer(cfg_sft(tmp_path / "a"), arreter_apres=12)["pertes"]
    entrainer(cfg_sft(tmp_path / "b"), arreter_apres=6)
    b = entrainer(cfg_sft(tmp_path / "b"), reprendre=True, arreter_apres=12)["pertes"]
    assert a[6:12] == pytest.approx(b, abs=1e-6)

def test_perte_au_niveau_du_jeton(): ...      # micro-lots de 1 et de 9 jetons appris : moyenne sur les 10
def test_cible_non_apprise_sans_effet(): ...  # changer une cible −100 ne change ni la perte ni les gradients
def test_part_de_la_version_publiee(tmp_path): ...  # au pas 0, les poids égalent ceux de charger_publication
def test_depart_d_autres_dimensions(tmp_path): ...  # ValueError « autres dimensions »
def test_depart_obligatoire_ou_interdit(): ...      # sft sans depart ; pre_entrainement avec depart
def test_rangee_toute_de_bourrage(tmp_path): ...    # point à surveiller 2 : pas de NaN, pas d'arrêt code 3
def test_longueur_differente_de_l_index(tmp_path): ...  # ValueError claire
```

  Les tests existants (`test_entrainement.py`, `test_evaluation.py`, `test_exporter.py`) passent sans changement.
- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire.** Le README gagne « Affiner ton IA » : `methode`, `depart`, la commande de reprise, `--arreter-apres`.
- [ ] **Étape 4 : vérifier**, `--extra gpu -m "not gpu"` puis `--extra gpu -m gpu` (un SFT de 20 pas sur la carte dont la perte baisse).
- [ ] **Étape 5 : commit**, « Forge : une boucle, plusieurs méthodes ; l'affinage supervisé depuis une version publiée ».

### Tâche 7 : les sources de conversations et leur téléchargement

**Fichiers :** créer `forge/fragments.py`, `forge/pause.py`, `forge/conversation/sources.py`, `forge/conversation/telechargement.py`, `tests/test_fragments.py`, `tests/test_sources_conversations.py` ; modifier `forge/entrainement/boucle.py` (importe `Pause`), `forge/__main__.py`, `docs/donnees.md`, `tests/test_donnees.py`.

**Interfaces :**

- `forge.pause.Pause` : la classe `_Pause` de `boucle.py`, déplacée sans changement de comportement (`boucle` l'importe sous son ancien nom).
- `class SortieParFragments(dossier: Path, prefixe: str, par_fragment: int = 50_000)` : `deja: int` (éléments déjà validés), `ajouter(element: dict)`, `valider(etat: dict | None = None)` (écrit le fragment `<prefixe>-NNNNN.jsonl.gz` et `etat.json` atomiquement), `terminer(infos: dict)` (`.complet` avec `infos`). À l'ouverture, les `.tmp` et les fragments au-delà de `etat.json` sont effacés. `lire_elements(dossier: Path, prefixe: str) -> Iterator[dict]`.
- `@dataclass(frozen=True) class SourceConversations` : `nom`, `depot`, `configuration: str | None`, `split`, `licence`, `url_licence`, `usage: Literal["entrainement", "evaluation"]`, `sorte: Literal["conversation", "consignes", "probleme", "code_test", "humaneval"]`, `flux: bool`, `convertir: Callable[[dict], Iterable[dict]]`.
- `SOURCES_CONVERSATIONS`, avec ces noms :

| Nom | Dépôt (configuration) | Usage | Ce que garde `convertir` |
| --- | --- | --- | --- |
| `luth2_conversation` | `kurakurai/Luth-2-Post-Training-SFT` | entraînement | `domain` dans `knowledge`, `if` ; `generator` qui commence par un préfixe de `GENERATEURS_GARDES` ; aucun `tool_calls` ni rôle `tool` ; `source` sans motif de `SOURCES_AMONT_ECARTEES` |
| `luth2_code` | idem | entraînement | `domain == "code"`, mêmes filtres, réponse avec un bloc `` ```python `` |
| `aya_fr` | `CohereLabs/aya_dataset` | entraînement | `language_code == "fra"` |
| `oasst2_fr` | `OpenAssistant/oasst2` | entraînement | `lang == "fr"` ; chaque arbre donne une conversation : la racine, puis la réponse d'assistant de rang 0, puis la réponse d'utilisateur la plus ancienne, et ainsi de suite |
| `opc_educational` | `OpenCoder-LLM/opc-sft-stage2` (`educational_instruct`) | entraînement (après traduction, tâche 20) | instruction, code, test |
| `ifeval_fr` | `kurakurai/IFEval-FR` | évaluation | invite, `instruction_id_list`, `kwargs` |
| `mgsm_rev2_fr` | `lightonai/mgsm-rev2` (`fr`) | évaluation | question, réponse numérique |
| `gsm8k_platinum_fr` | `cmh/gsm8k-platinum_fr` | évaluation | question, réponse finale (après `####` s'il y en a) |
| `humaneval` | `openai/openai_humaneval` | évaluation | `task_id`, `prompt`, `test`, `entry_point`, `canonical_solution` |

  `GENERATEURS_GARDES = ("Qwen/",)`. `SOURCES_AMONT_ECARTEES = ("stackoverflow", "smoltalk", "magpie")` (en minuscules, cherchés dans `source`) : StackOverflow est en CC BY-SA ; Smol-Magpie viendrait de Llama (« données », §1.2, non relu). La tâche 12 relit les fiches des autres sources amont et complète la liste.
- `telecharger_source(source: SourceConversations, exemples_max: int | None = None) -> Path` : vers `sous_forge_donnees(source.nom, "conversations")`. En flux, l'état `state_dict()` du jeu est gardé dans `etat.json` à chaque fragment, et la relance le recharge (plan 6). Ctrl+C (`Pause`) valide le fragment en cours et affiche la commande de reprise. `.complet` contient le nom, la licence, l'usage et les comptes (lus, gardés, écartés par raison).
- `python -m forge conversations --source NOM [--exemples-max N]` et `--liste` (nom, usage, licence, lien).
- `docs/donnees.md`, section « Vague 2 : affiner ton IA » : chaque source, sa licence et son lien, son usage, ses filtres, et la phrase sur les jeux réservés à l'évaluation.

- [ ] **Étape 1 : tests rouges**, sans réseau : des fichiers Parquet écrits dans `tmp_path`, lus par `load_dataset("parquet", data_files=…, streaming=True)`.
  - Luth : une ligne avec appel d'outil, une de Gemma, une venue de StackOverflow, une de domaine `math` : toutes écartées, avec leur raison comptée.
  - OASST2 : un arbre de 6 messages donne la conversation attendue.
  - Coupure après le premier fragment, puis relance : mêmes éléments qu'un téléchargement d'une traite, sans doublon.
  - `SortieParFragments` : un `.tmp` resté et un fragment de trop sont effacés à l'ouverture.
  - `test_donnees.py` : chaque nom de `SOURCES_CONVERSATIONS` figure dans `docs/donnees.md` avec sa licence.
- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire.** Puis lire une fois en vrai, sur le réseau, les 20 premières lignes de chaque source (`--exemples-max 20`, dans un `FORGE_DONNEES` temporaire). Vérifier que les colonnes sont celles que lit `convertir`. Si une colonne diffère, adapter `convertir` et son test.
- [ ] **Étape 4 : vérifier**, commit « Forge : sources de conversations et d'évaluation, téléchargement repris par fragments ».

### Tâche 8 : le hasard partagé, la langue et les consignes vérifiables

**Fichiers :** créer `forge/hasard.py`, `forge/evaluation/langue.py`, `forge/evaluation/consignes.py`, `tests/test_hasard.py`, `tests/test_langue.py`, `tests/test_consignes.py`.

**Interfaces :**

- `forge.hasard.Hasard` : SplitMix32, copie exacte des trois méthodes de `projets/mini-modele/mini_modele/calcul.py` (`__init__`, `suivant32`, `uniforme`), plus `entier(a: int, b: int) -> int` (`a + suivant32() % (b - a + 1)`), `choisir(suite)` et `melanger(liste) -> list` (Fisher-Yates avec `entier`, de la fin vers le début). Calcul en entiers seulement : le site le refait à l'identique (plan 8).
- `forge.evaluation.langue` :
  - `mots(texte: str) -> list[str]` : suites de lettres (`unicodedata.category(c)[0] == "L"`), coupées aux apostrophes `'` et `’`, en minuscules par `str.lower()` ;
  - `MOTS_FRANCAIS` et `MOTS_ANGLAIS` : deux `frozenset` d'au plus 80 mots outils chacun, écrits dans le module, sans mot commun aux deux ;
  - `langue(texte: str) -> Literal["fr", "autre", "indetermine"]` : `f` et `a` comptent les mots des deux listes ; `"indetermine"` si `f + a < 3`, `"fr"` si `f >= 2 * a`, sinon `"autre"`.
- `forge.evaluation.consignes` :
  - `IDS_IFEVAL_FR: tuple[str, ...]` : les identifiants de consigne présents dans IFEval-FR, relevés à cette tâche (lecture du jeu en réseau, une fois), triés ;
  - `VERIFICATEURS: dict[str, Callable[[str, dict], bool]]` : un vérificateur strict par identifiant, de même sens que ceux de M-IFEval (dépôt `lightblue-tech/M-IFEval`, Apache-2.0, à lire pour chaque identifiant `fr:`). Les comptes de mots passent par `mots()` ;
  - `respecte(reponse: str, ids: Sequence[str], kwargs: Sequence[dict]) -> list[bool]` ; `exactitudes(resultats: Sequence[list[bool]]) -> dict` (`invite_stricte`, `consigne_stricte`, `n`). Pas de version « souple » d'IFEval : le chapitre le dit ;
  - `@dataclass(frozen=True) class Contrainte` : `id`, `consigne: Callable[[dict], str]`, `tirer: Callable[[Hasard, str], dict]` (le hasard et le texte de la question), `verifier: Callable[[str, dict], bool]`, `transformer: Callable[[str, dict], str | None]` (rend une réponse qui respecte la contrainte, ou `None`) ;
  - `CONTRAINTES`, ces huit-là, consignes exactes :

| id | consigne | `tirer(hasard, question)` |
| --- | --- | --- |
| `mots_max` | « Réponds en {n} mots au plus. » | n parmi 20, 40, 60 |
| `phrases_max` | « Réponds en {n} phrases au plus. » | n de 1 à 3 |
| `minuscules` | « Écris toute ta réponse en minuscules. » | rien |
| `sans_virgule` | « N'utilise aucune virgule. » | rien |
| `mot_obligatoire` | « Emploie le mot « {mot} » dans ta réponse. » | un mot de la question, de 5 lettres ou plus (sans un tel mot : `None`, et la contrainte n'est pas tirée) |
| `puces` | « Réponds par exactement {n} puces, chacune commençant par « - ». » | n de 2 à 4 |
| `fin_imposee` | « Termine ta réponse par la phrase exacte : « {phrase} » » | une de 5 phrases écrites dans le module |
| `titre` | `Donne d'abord un titre entre doubles chevrons, comme <<titre>>.` (entre guillemets français dans le module) | rien |

- [ ] **Étape 1 : tests rouges.**
  - `Hasard` : le texte de ses trois méthodes égale celui de `projets/mini-modele/mini_modele/calcul.py` (comparaison de sources, si ce fichier existe) ; les 5 premiers `suivant32()` de la graine 0 sont écrits dans le test ; `melanger(list(range(10)))` de la graine 1 aussi.
  - `langue` : « Le forgeron chauffe le fer, puis il le tord sur l'enclume. » → `fr` ; « The smith heats the iron and then bends it. » → `autre` ; « Paris. » → `indetermine` ; « L’été » coupe à l’apostrophe courbe ; un texte de 10 000 caractères en moins de 50 ms.
  - Chaque contrainte : deux réponses justes et deux fausses ; pour 200 réponses tirées de `tests/donnees/corpus_test.txt`, `transformer` rend `None` ou une réponse que `verifier` accepte.
  - `set(IDS_IFEVAL_FR) <= set(VERIFICATEURS)`, plus deux exemples par identifiant.
- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire.** Les mots et les vérificateurs n'utilisent ni `\w` ni `\b` (Python et JavaScript ne s'y accordent pas) : des tests de caractères explicites, que le plan 8 traduit.
- [ ] **Étape 4 : vérifier**, commit « Forge : hasard partagé, langue d'un texte et consignes vérifiables ».

### Tâche 9 : les problèmes de raisonnement

**Fichiers :** créer `forge/raisonnement/__init__.py`, `forge/raisonnement/problemes.py`, `forge/raisonnement/verification.py`, `tests/test_problemes.py` ; modifier `forge/__main__.py`.

**Interfaces :**

- `FAMILLES = ("addition", "soustraction", "multiplication", "partage", "achats", "ages")` ; `DIFFICULTES = (1, 2, 3)`, le nombre d'étapes de calcul.
- `FORMES: dict[str, tuple[int, ...]]`, les difficultés de chaque famille : `addition` et `soustraction` 1, 2, 3 ; `multiplication` et `partage` 1, 2 ; `achats` et `ages` 2, 3.
- `GRAINES_ENTRAINEMENT = 0`, `GRAINES_EVALUATION = 1_000_000`, `GRAINES_RL = 2_000_000`, `GRAINES_PREFERENCES = 3_000_000`, `GRAINES_VICTOIRE = 4_000_000`, `GRAINES_VALIDATION_RL = 5_000_000` : chaque usage a sa plage de graines.
- `@dataclass(frozen=True) class Probleme: id: str; famille: str; difficulte: int; enonce: str; etapes: tuple[str, ...]; reponse: int`.
- `generer_probleme(famille: str, difficulte: int, graine: int) -> Probleme` : tout en entiers, tirages par `forge.hasard.Hasard(graine)`, énoncés en français écrits à partir de listes du module (30 prénoms, 20 objets avec singulier, pluriel et fourchette de prix entière). Chaque étape s'écrit `"a op b = c"` avec `op` parmi `+`, `−` (U+2212), `×`, `÷`.
  - Familles : `addition` et `soustraction` (difficulté 1 : nombres de 10 à 99 ; 2 : deux opérations ; 3 : trois) ; `multiplication` (1 : 2..9 × 10..99) ; `partage` (division exacte) ; `achats` (quantités × prix, puis sommes) ; `ages` (écarts d'âge, puis années qui passent).
  - Un couple (famille, difficulté) absent de `FORMES` lève `ValueError`.
- `conversation_de_probleme(p: Probleme) -> list[Tour]` : l'utilisateur dit l'énoncé ; l'assistant pense `"\n".join(p.etapes)` et répond « La réponse est {reponse}. ».
- `generer_problemes(n: int, graine_depart: int, familles=FAMILLES, difficultes=(1, 2, 3)) -> list[Probleme]` : la graine `graine_depart + i` donne le i-ème ; le couple (famille, difficulté) est tiré de la même graine, parmi ceux de `FORMES` permis par `familles` et `difficultes` (`ValueError` s'il n'y en a aucun). Énoncés en double retirés.
- `extraire_nombre(texte: str) -> Fraction | None` : le dernier nombre du texte, avec les milliers séparés par une espace, U+202F ou U+00A0, une virgule décimale, et le signe moins `-` ou `−`.
- `est_juste(reponse: Reponse, attendu: int | str) -> bool` : le nombre extrait du **texte** de la réponse (après la pensée) égale `attendu`.
- `python -m forge problemes --sortie NOM --nombre N --graine-depart G [--difficultes 1,2] [--familles a,b]` : écrit `sous_forge_donnees(NOM, "problemes")` (`problemes-*.jsonl.gz` par `SortieParFragments`, `index.json` avec les graines et l'usage, `.complet`). L'usage est `evaluation` si `G >= GRAINES_EVALUATION` et `G < GRAINES_RL`.

- [ ] **Étape 1 : tests rouges.**
  - Même graine, même problème ; chaque étape se recalcule (le test refait l'opération écrite) et la dernière donne `reponse` ; `len(etapes) == difficulte`.
  - `langue(enonce) != "autre"` pour 500 problèmes.
  - 2 000 problèmes d'entraînement et 500 d'évaluation n'ont aucun énoncé commun.
  - `extraire_nombre` : « La réponse est 1\u202f234. » → 1234 ; « 12,5 » → 25/2 ; « −3 » → −3 ; « rien » → `None` ; « 3 puis 7 » → 7.
  - `est_juste` ignore un nombre de la pensée qui contredit le texte.
- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire.**
- [ ] **Étape 4 : vérifier**, commit « Forge : problèmes de calcul en français, justes par construction, et leur vérification ».

### Tâche 10 : conversations générées, recettes et préparation des jeux

**Fichiers :** créer `forge/conversation/generees.py`, `forge/affinage/recettes.py`, `tests/test_generees.py`, `tests/test_recettes.py` ; modifier `forge/__main__.py`, `docs/donnees.md`.

**Interfaces :**

- `PERSONNAGES: tuple[str, ...]` : 20 débuts de message système, écrits à la main (« Tu es un professeur de mathématiques patient. »…).
- `IDENTITE: tuple[tuple[str, str], ...]` : au moins 30 couples (question, réponse) sur ton IA, écrits à la main. Faits seulement : son nom, le site qui l'a créée, le français et le Python, sa taille, qu'elle se trompe souvent.
- `conversations_systeme(base: Sequence[list[Tour]], n: int, graine: int) -> list[list[Tour]]` : une conversation à un tour de `base`, un personnage (une fois sur deux), une contrainte de `CONTRAINTES` avec `transformer`. Le message système est « {personnage} {consigne} ». La réponse est transformée, puis gardée seulement si `verifier` l'accepte.
- `conversations_identite() -> list[list[Tour]]` : chaque couple, avec et sans message système.
- `@dataclass(frozen=True) class Part: source: str; exemples_max: int | None`. `source` vaut un nom de `SOURCES_CONVERSATIONS`, `"systeme_genere"`, `"identite"`, `"problemes:<nom>"`, `"fim:<nom>"` (tâche 19) ou `"code_fr:<nom>"` (tâche 20).
- `@dataclass(frozen=True) class Recette: nom: str; parts: tuple[Part, ...]; longueur: int = 2048; jetons_max_exemple: int = 1536; part_validation: float = 0.02; graine: int = 0`.
- `RECETTES` (cette tâche ajoute les deux premières ; `code-1.10` vient en tâche 19) :

| Recette | Parts |
| --- | --- |
| `sft-1.7` | `luth2_conversation` 150 000, `aya_fr` tout, `oasst2_fr` tout, `systeme_genere` 20 000, `identite` tout |
| `raisonnement-1.9` | `problemes:entrainement-1.9` 60 000, `luth2_conversation` 12 000, `systeme_genere` 3 000, `identite` tout |

- `preparer_jeu(recette: Recette, sortie: Path | None = None) -> dict`, vers `affinage/<recette.nom>` par défaut :
  1. refuse toute part dont la source a `usage == "evaluation"` (`ValueError` qui la nomme) ;
  2. lit chaque source, tire `exemples_max` éléments par `Hasard(recette.graine).melanger` (le même ordre d'une préparation à l'autre : la part de rappel de 1.9 reprend les premiers exemples de 1.7) ;
  3. retire les doublons, par l'empreinte (`empreinte_du_texte_nettoye`) du premier tour de l'utilisateur ;
  4. **décontamine** : écarte un exemple dont un tour d'utilisateur partage un 8-gramme de `mots()` avec une invite d'un jeu d'évaluation déjà téléchargé (sources `evaluation`, problèmes d'évaluation, HumanEval-FR quand il existe) ;
  5. encode, écarte ce qui dépasse `jetons_max_exemple`, répartit par `est_validation(empreinte, part_validation)`, empaquette chaque partie, puis écrit par `ecrire_jeu` ;
  6. écrit à côté `ids.txt.gz`, les identifiants des exemples gardés (pour que la tâche 13 ne prenne pas d'invite déjà apprise).
  Le résumé rendu et l'index donnent, par source : lus, gardés, doublons, contaminés, trop longs, licence.
- `python -m forge preparer --recette NOM [--sortie NOM]`.

- [ ] **Étape 1 : tests rouges.**
  - Une recette avec `ifeval_fr` est refusée.
  - Un exemple qui reprend 8 mots d'une question de MGSM (fichier d'évaluation écrit dans le test) est écarté et compté (point à surveiller 5).
  - Train et val disjoints ; deux préparations, même jeu à l'octet près.
  - Chaque conversation de `conversations_systeme` passe `verifier_conversation` et le vérificateur de sa contrainte ; `conversations_identite()` en a au moins 60.
  - Les licences de l'index sont celles des sources.
- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire.** `docs/donnees.md` dit d'où viennent les conversations générées : du code du dépôt, sous sa licence, et des réponses de Luth-2 ou d'Aya qu'elles transforment (licence de la source).
- [ ] **Étape 4 : vérifier**, commit « Forge : conversations générées, recettes et préparation des jeux d'affinage ».

### Tâche 11 : l'évaluation d'une étape, et `forge discuter`

**Fichiers :** créer `forge/evaluation/reponses.py`, `forge/evaluation/etape.py`, `tests/test_etape.py`, `tests/test_discuter.py` ; modifier `forge/__main__.py`, `projets/forge/README.md`.

**Interfaces :**

- `repondre_lot(modele, tok, conversations: Sequence[Sequence[Tour]], n_nouveaux: int = 512, temperature: float = 0.0, top_k: int = 50, graine: int = 0, lot: int = 32) -> list[Reponse]` : `invite_de_reponse`, `generer_lot(arret=<|fin_tour|>)`, `lire_reponse`.
- `INVITES_DE_CONVERSATION: tuple[str, ...]` : 10 invites fixes (6 questions, 2 consignes, « Qui es-tu ? », une demande de fonction Python).
- `MESURES: dict[str, Callable[[ContexteDEvaluation], dict]]`. Cette tâche écrit :
  - `perte_conversation` : `perte_sft_validation` sur la validation de `affinage/sft-1.7` ;
  - `ifeval_fr` : glouton, 512 jetons, `exactitudes` ;
  - `tenue` : sur les réponses d'IFEval-FR et 100 premières invites de la validation de `sft-1.7` : part terminée par `<|fin_tour|>`, parts `fr` / `autre` / `indetermine`, mots moyens ;
  - `oubli` : perte et bits par octet sur 64 morceaux de `jetons/principal/val` (la mesure du plan 6) ;
  - `echantillons` : les 10 invites, glouton, 200 jetons, gardées telles quelles ;
  - `problemes` : `generer_problemes(400, GRAINES_EVALUATION)` (difficultés 1 à 3), exactitude en glouton, et réussite en 8 essais (température 1, top-k 50), par famille et par difficulté ;
  - `mgsm_fr` et `gsm8k_platinum_fr` : glouton, 384 jetons, exactitude par `est_juste`.
  Une mesure dont les données manquent rend `{"absente": "<raison>"}`.
- Les clés rendues, que lit le plan 8 : `perte_conversation` `{perte, n}` ; `ifeval_fr` `{invite_stricte, consigne_stricte, n}` ; `tenue` `{terminee, fr, autre, indetermine, mots_moyens, n}` (des parts de 0 à 1) ; `oubli` `{perte, bits_par_octet, n}` ; `echantillons` `[{invite, texte, pensee, terminee}]` ; `problemes` `{exactitude, reussite_8, par_famille, par_difficulte, n}` ; `mgsm_fr` et `gsm8k_platinum_fr` `{exactitude, n}`.
- `MESURES_PAR_ETAPE` : `"1.7"` : `perte_conversation`, `ifeval_fr`, `tenue`, `oubli`, `echantillons` ; `"1.9"` : `ifeval_fr`, `tenue`, `oubli`, `problemes`, `mgsm_fr`, `gsm8k_platinum_fr`, `echantillons`. Les tâches 13 et 21 ajoutent `"1.8"` et `"1.10"`.
- `evaluer_etape(modele: Path, etape: str, sortie: Path, reference: Path | None = None, appareil: str | None = None, n_max: int | None = None) -> dict` : écrit `rapport.json` (`VERSION_DU_RAPPORT_D_ETAPE = 1`, `version` du modèle, son empreinte, `etape`, `date`, `mesures`, `secondes`) et `rapport.md`, en français, avec la typographie de `forge.evaluation.rapport`.
- `python -m forge evaluer-etape --modele DOSSIER --etape 1.7 [--reference DOSSIER] [--sortie D] [--appareil cuda|cpu] [--n-max N]`, sortie par défaut `evaluations/<version>-<etape>/`.
- `python -m forge discuter --modele DOSSIER [--systeme TEXTE] [--temperature 0.7]` : boucle de conversation ; `/nouveau` repart de zéro, `/quitter` sort ; la fenêtre de contexte trop pleine donne un message qui dit de faire `/nouveau`.

- [ ] **Étape 1 : tests rouges**, avec un modèle minuscule publié par `exporter` dans le test, et des fichiers d'évaluation écrits dans le test :
  - le rapport a les clés de chaque mesure ; une donnée absente donne `absente`, sans planter ;
  - `ifeval_fr` avec un faux modèle qui répond toujours la même chose (pattern de `MODELE_QUI_PREFERE`) : les exactitudes calculées à la main ;
  - `discuter` avec `input` simulé : deux tours, `/nouveau`, `/quitter` ; code de sortie 0.
- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire.**
- [ ] **Étape 4 : vérifier**, commit « Forge : l'évaluation d'une étape de ton IA, et la conversation en ligne de commande ».

### Tâche 12 : ton IA 1.7, sur la carte

Une tâche d'exploitation : pas de test rouge, mais chaque étape a son résultat vérifiable. Carte libre, entre « go » et « stop ».

**Fichiers :**

- créer `projets/forge/configs/sft-1.7.toml`, `sft-1.7-court.toml`, `docs/mesures/ton-ia-1.7.md`, `ton-ia-1.7-LISEZMOI.md` ;
- modifier `docs/donnees.md`, `forge/conversation/sources.py` (sources amont écartées), `projets/forge/README.md` ;
- hors dépôt : `D:\forge-ia-donnees\journaux\travail-long.ps1`, `pause-entrainement.ps1`, `chien-de-garde.py`.

- [ ] **Étape 1 : les outils de session.**
  - `travail-long.ps1 -Arguments "<arguments de forge>" -Nom <nom> [-Reprendre]` : copie paramétrée de `entrainement-principal.ps1`. Elle lance `.venv\Scripts\python.exe -m forge <Arguments>` (plus `--reprendre` pour `entrainer`) dans une fenêtre réduite titrée `Ton IA : <nom>`, avec le journal `journaux\<nom>.log`. Mêmes règles : Ctrl+C rendu à Python, TEMP sur D:, pas de veille, priorité normale.
  - `pause-entrainement.ps1` gagne `-Verification journal|etat` : `journal` comme aujourd'hui ; `etat` vérifie que le processus est sorti avec le code 0 et que `etat.json` a changé.
  - `chien-de-garde.py` gagne `--journal` et `--journal-fenetre`, avec les valeurs d'aujourd'hui par défaut.
  - Essayer chacun sur un faux travail (`-ScriptEssai`), comme le 05/11.
- [ ] **Étape 2 : les données.**
  - `forge publication --etiquette ton-ia-1.5`, puis vérifier que les empreintes égalent celles de `docs/mesures/ton-ia-1.5-LISEZMOI.md`.
  - Lire les fiches des sources amont de Luth-2 : les valeurs distinctes de `source` et de `generator` pour `knowledge`, `if` et `code`. Écarter toute source amont dont les invites ou les réponses viennent de Llama ou d'OpenAI. Compléter `SOURCES_AMONT_ECARTEES` et `docs/donnees.md` (une ligne par source amont : gardée ou écartée, et pourquoi), et adapter le test.
  - `forge conversations` pour `luth2_conversation`, `aya_fr`, `oasst2_fr`, `ifeval_fr`, `mgsm_rev2_fr`, `gsm8k_platinum_fr` et `humaneval`. Puis `forge preparer --recette sft-1.7`. Noter dans le ledger les comptes du résumé et la place sur D:.
- [ ] **Étape 3 : l'essai chronométré.** `configs/sft-1.7.toml`, commenté réglage par réglage comme `principal.toml` : `preset = "tres_grand"`, `methode = "sft"`, `depart = "ton-ia-1.5"`, `donnees = "sft-1.7"`, `sortie = "sft-1.7"`, `longueur = 2048`, `taille_lot_jetons = 65_536`, `echauffement = 50`, `poids_decroissance = 0.0`, `betas` et `ecretage` de `principal.toml`, `graine = 1234`, `evaluation_tous_pas = 100`, `sauvegarde_minutes = 30`, `appareil = "cuda"`, `compiler = "auto"`. Les configurations des tâches 15, 17 et 22 suivent ce modèle ; seuls changent les réglages que leur tâche nomme.
  - Trouver le plus grand `micro_lot` qui tient (1, 2 ou 4), carte au repos.
  - 10 pas sur la carte, puis 3 pas sur le processeur (16 fils, charge par cœur relevée par psutil), par `--arreter-apres` dans des sorties d'essai.
  - Noter jetons/s, mémoire maximale et fils dans `docs/mesures/ton-ia-1.7.md`. Prendre le plus rapide.
- [ ] **Étape 4 : le balayage du taux.** Trois essais de 300 pas (`jetons_total = 19_660_800`), taux 1e-5, 3e-5 et 1e-4, chacun dans sa sortie. Garder celui dont la dernière perte de validation est la plus basse, et en cas d'égalité à 0,005 près, le plus petit taux. Noter les trois courbes. Effacer les sauvegardes des deux autres.
- [ ] **Étape 5 : l'entraînement complet.** `jetons_total` = 2 époques des rangées de `train` (2 × rangées × 2 048), arrondi au multiple de 65 536 au-dessus. Lancer par `travail-long.ps1`, avec le chien de garde. Faire une vraie pause (Ctrl+C) après la première sauvegarde, puis reprendre ; la courbe continue sans saut.
- [ ] **Étape 6 : la version courte.** `configs/sft-1.7-court.toml` : mêmes réglages, `jetons_total` pour une heure au débit mesuré, sortie `ton-ia-1.7-court`. La lancer ; noter sa durée réelle.
- [ ] **Étape 7 : exporter et évaluer.**
  - `forge exporter --sauvegarde …\sft-1.7\sauvegardes\meilleur.pt --sortie "$env:FORGE_DONNEES\publications\ton-ia-1.7" --poids ton-ia-1.7.safetensors`.
  - `forge evaluer-etape --etape 1.7` sur `ton-ia-1.5`, `ton-ia-1.7` et la version courte (exportée sous `publications\ton-ia-1.7-court`, sans Release).
- [ ] **Étape 8 : les documents.**
  - `docs/mesures/ton-ia-1.7.md` : les données (comptes, licences), l'essai chronométré, le balayage, les sessions et leur durée réelle, la courbe, les mesures de 1.5 et de 1.7 côte à côte, les dix échantillons tels quels, ce qu'elle sait faire et ne sait pas faire.
  - `ton-ia-1.7-LISEZMOI.md`, au plan de celui de 1.5.
  - Une phrase qualitative n'y dit que ce que les nombres disent. Si 1.7 fait moins bien que 1.5 sur une mesure, c'est écrit.
- [ ] **Étape 9 : commit** « Ton IA 1.7 : données, essai, balayage, entraînement, évaluation ».
- [ ] **Étape 10 (contrôleur) : la Release.** `gh release create ton-ia-1.7 ton-ia-1.7.safetensors config.json tokenizer-ton-ia-v1.json rapport.json LISEZMOI.md ton-ia-1.7.md --title "Ton IA, chapitre 1.7" --notes-file LISEZMOI.md`. Chaque fichier fait moins de 2 Go ; `forge publication --etiquette ton-ia-1.7` dans un dossier neuf redonne les mêmes empreintes. Jalon dans la mémoire partagée si elle répond.

### Tâche 13 : les préférences

**Fichiers :** créer `forge/preferences/__init__.py`, `invites.py`, `noter.py`, `construction.py`, `tests/test_preferences.py` ; modifier `forge/evaluation/etape.py` (mesure `victoire`, étape `"1.8"`), `forge/__main__.py`.

**Interfaces :**

- `@dataclass(frozen=True) class InvitePreference: id: str; tours: tuple[Tour, ...]; contraintes: tuple[tuple[str, dict], ...]; attendu: int | None`.
- `invites_de_preference(n: int, graine: int, base: Sequence[tuple[str, list[Tour]]], exclure: set[str]) -> list[InvitePreference]` : 70 % de questions de `base` (identifiant hors `exclure`), à qui l'on ajoute une ou deux contraintes de `CONTRAINTES` (consignes à la fin du message de l'utilisateur) ; 30 % de problèmes de difficulté 1 tirés de `GRAINES_PREFERENCES`, avec `attendu`.
- `class Note(NamedTuple): terminee: int; juste: int; consignes: int; francais: int; longueur: int` (ordre lexicographique, du plus important au moins important).
- `noter(reponse: Reponse, invite: InvitePreference) -> Note` : `juste` vaut 1 sans `attendu`, sinon 1 si `est_juste` ; `consignes` compte les contraintes respectées ; `francais` vaut 0 seulement pour `"autre"` ; `longueur` vaut 1 si le texte a de 3 à 300 mots.
- `choisir_paire(notes: Sequence[Note]) -> tuple[int, int] | None` : (indice de la meilleure, indice de la pire) ; `None` si toutes les notes sont égales.
- `@dataclass(frozen=True) class RecettePreferences: nom: str; invites: int; reponses_par_invite: int = 2; temperature: float = 1.0; top_k: int = 50; n_nouveaux: int = 384; longueur: int = 768; part_validation: float = 0.05; graine: int = 0`. `RECETTES_PREFERENCES` : `preferences-1.8` (40 000 invites) et `preferences-1.8-court` (8 000).
- `construire_paires(modele: Path, recette: RecettePreferences, sortie: Path | None = None, appareil: str | None = None) -> dict` :
  - `base` : `luth2_conversation`, moins les identifiants de `affinage/sft-1.7/ids.txt.gz` ;
  - par paquets de 512 invites : `repondre_lot` (graine = `recette.graine` + rang du paquet), `noter`, `choisir_paire` ; les invites, réponses et notes vont dans `SortieParFragments` (prefixe `paires`), et la relance reprend au paquet suivant ;
  - à la fin, un jeu `sorte="dpo"` (`ecrire_jeu`) : rangées (choisie, rejetée), invite plus réponse, perte sur la réponse et son `<|fin_tour|>` s'il a été produit ; une invite de plus de 384 jetons est écartée ;
  - l'index dit : invites, paires, égalités, taux de paires, et les raisons qui ont départagé (lequel des cinq critères).
- `taux_de_victoire(notes_a: Sequence[Note], notes_b: Sequence[Note]) -> dict` : `victoires`, `egalites`, `defaites`, `taux` = (victoires + égalités / 2) ÷ n.
- `invites_de_validation(jeu: Path, n: int) -> list[InvitePreference]` : les `n` premières invites de la partie `val` d'un jeu de paires, relues dans ses fragments.
- Mesure `victoire` (clés : celles de `taux_de_victoire`, plus `mots_modele`, `mots_reference` et `n`) : 500 invites (questions de la validation de `sft-1.7` et problèmes de `GRAINES_VICTOIRE`, avec contraintes), réponses gloutonnes du modèle et de `--reference`, notées, puis `taux_de_victoire`, et les mots moyens des deux. Avec `--invites NOM`, elle prend à la place `invites_de_validation` du jeu de paires `NOM` : c'est ce qui choisit entre les essais du balayage, sans toucher aux 500 invites du rapport. `MESURES_PAR_ETAPE["1.8"]` = celles de 1.7, plus `victoire`.
- `python -m forge preferences --modele DOSSIER --recette preferences-1.8 [--sortie NOM]` ; `evaluer-etape` gagne `--invites NOM`.

- [ ] **Étape 1 : tests rouges.**
  - Ordre des notes : une réponse non terminée perd toujours ; à terminaison égale, une réponse fausse perd ; et ainsi de suite.
  - Égalité, donc aucune paire.
  - Avec un faux modèle déterministe, coupé après le 2e paquet puis relancé : le même fichier de paires qu'en une traite (point à surveiller 3).
  - Aucune invite ne vient d'une source d'évaluation ni de `exclure` (point à surveiller 5).
  - Rangées de paires : même préfixe d'invite, perte seulement sur les réponses.
- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire.**
- [ ] **Étape 4 : vérifier**, commit « Forge : paires de préférences tirées de ton IA et classées par des contrôles programmés ».

### Tâche 14 : DPO

**Fichiers :** créer `forge/affinage/dpo.py`, `tests/test_dpo.py` ; modifier `forge/entrainement/methodes.py` (méthode `dpo`), `forge/entrainement/boucle.py` (`ReglagesDPO`), `forge/suivi.py`.

**Interfaces :**

- `@dataclass(frozen=True) class ReglagesDPO: beta: float = 0.1; normaliser_longueur: bool = False; poids_sft: float = 1.0`.
- `logps_des_rangees(modele, lot: LotAffinage, appareil) -> tuple[Tensor, Tensor]` : par rangée, la somme des log-probabilités des jetons appris (float32) et leur nombre.
- `perte_dpo(pc, pr, qc, qr, lc, lr, reglages: ReglagesDPO) -> tuple[Tensor, dict]`, un élément par paire : `pc`, `pr` les log-probabilités de la politique pour la choisie et la rejetée, `qc`, `qr` celles de la référence, `lc`, `lr` leurs nombres de jetons appris :
  - `z = β((pc − qc) − (pr − qr))`, ou, avec `normaliser_longueur`, `z = β((pc − qc)/lc − (pr − qr)/lr)` ;
  - `perte = moyenne(−logσ(z)) + poids_sft × moyenne(−pc/lc)` ;
  - mesures : `logps_choisie` (moyenne de `pc/lc`), `logps_rejetee` (moyenne de `pr/lr`), `recompense_choisie` (moyenne de `β(pc − qc)`), `recompense_rejetee`, `marge` (leur différence), `exactitude` (part de `z > 0`).
- La référence : à la création du contexte de la méthode, si `reference.bin` du jeu manque ou si `reference.json` nomme une autre version de départ (version et empreinte), les log-probabilités de toutes les rangées sont calculées avec le modèle de départ (évaluation, `autocast`) et écrites atomiquement (`float64`, une valeur par rangée), avec une ligne au journal. Sinon elles sont relues.
- Méthode `dpo` enregistrée : chargeur `ChargeurAffinage` (sorte `dpo`), pas = moyenne sur les paires du pas (accumulation comme pour le SFT), validation = perte DPO et exactitude sur les 256 premières paires de validation (`perte_val` = cette perte). Le journal écrit les six mesures à chaque pas.
- `forge suivi` affiche `logps_choisie` et `exactitude` quand elles sont dans le journal.

- [ ] **Étape 1 : tests rouges.**

```python
def test_formule_a_la_main():
    perte, m = perte_dpo(t(-10.), t(-12.), t(-11.), t(-11.), t(5.), t(6.), ReglagesDPO(beta=0.1, poids_sft=0.))
    z = 0.1 * ((-10 + 11) - (-12 + 11))
    assert perte.item() == pytest.approx(-math.log(1 / (1 + math.exp(-z))), abs=1e-12)

def test_au_depart_la_perte_vaut_ln2_plus_sft(): ...   # politique = référence : ln 2 + NLL moyenne de la choisie
def test_normalisation_par_la_longueur(): ...
def test_la_marge_grandit(tmp_path): ...    # modèle minuscule, 20 pas : marge finale > marge initiale
def test_dpo_reprise_exacte(tmp_path): ...
def test_reference_recalculee_si_le_depart_change(tmp_path): ...
def test_reference_relue_si_le_depart_est_le_meme(tmp_path): ...  # aucun recalcul (compteur d'appels)
```

  (`t` : un tenseur float64 d'un seul élément.)
- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire.**
- [ ] **Étape 4 : vérifier**, commit « Forge : DPO maison, avec référence précalculée et terme SFT ».

### Tâche 15 : ton IA 1.8, sur la carte

**Fichiers :** créer `configs/dpo-1.8.toml`, `dpo-1.8-court.toml`, `docs/mesures/ton-ia-1.8.md`, `ton-ia-1.8-LISEZMOI.md`.

- [ ] **Étape 1 : l'essai chronométré de la construction des paires.** `forge publication --etiquette ton-ia-1.7`. Puis `forge preferences` sur 512 invites, sur la carte et sur le processeur (16 fils), dans un `FORGE_DONNEES` d'essai. Noter réponses/s, jetons/s, taux de paires et mémoire dans `docs/mesures/ton-ia-1.8.md` ; le contrôleur reporte la durée prévue dans le ledger.
- [ ] **Étape 2 : les paires.** `preferences-1.8-court`, puis `preferences-1.8`, par `travail-long.ps1` (pause : `-Verification etat`). Si le taux de paires est sous 20 %, s'arrêter et le dire au contrôleur, sans changer `reponses_par_invite` (décision du contrôleur : deux réponses).
- [ ] **Étape 3 : l'essai chronométré de DPO.** `configs/dpo-1.8.toml` : départ `ton-ia-1.7`, `methode = "dpo"`, `longueur = 768`, `taille_lot_jetons = 49_152` (32 paires), `echauffement = 10`, `poids_decroissance = 0.0`, `[dpo]`. 10 pas sur la carte et 3 sur le processeur ; noter.
- [ ] **Étape 4 : le balayage.** Six essais courts (un quart d'époque), beta 0,05, 0,1 et 0,3, taux 1e-6 et 5e-6. Puis un septième avec `normaliser_longueur = true`, au meilleur couple. Le meilleur : le plus haut `taux_de_victoire` contre ton-ia-1.7 sur les 200 premières invites de validation des paires (`evaluer-etape --etape 1.8 --reference … --invites preferences-1.8 --n-max 200`) ; à égalité, le plus petit taux. Noter pour chacun : victoire, longueur moyenne, `logps_choisie` au début et à la fin.
- [ ] **Étape 5 : l'entraînement complet** (une époque, réglages retenus), puis la version courte (paires `-court`, une heure en tout avec la construction des paires ; sa durée réelle est notée). Une pause réelle et sa reprise pendant le complet.
- [ ] **Étape 6 : exporter et évaluer.** Exporter vers `publications\ton-ia-1.8`, puis `evaluer-etape --etape 1.8 --reference publications\ton-ia-1.7` sur 1.8 et sur la version courte, et `--etape 1.7` sur 1.8 (pour la même table que 1.7).
- [ ] **Étape 7 : documents** comme en tâche 12. En plus : la courbe de `logps_choisie` (si elle baisse, le dire : c'est le piège connu), la longueur avant et après, six paires réelles avec leurs notes.
- [ ] **Étape 8 : commit**, puis **(contrôleur)** Release `ton-ia-1.8`, comme en tâche 12, et jalon.

### Tâche 16 : GRPO

**Fichiers :** créer `forge/raisonnement/grpo.py`, `tests/test_grpo.py` ; modifier `forge/entrainement/methodes.py`, `forge/entrainement/boucle.py` (`ReglagesGRPO`, code de sortie 4), `forge/suivi.py`, `forge/__main__.py`.

**Interfaces :**

- `@dataclass(frozen=True) class ReglagesGRPO: pas: int; invites_par_pas: int = 16; reponses_par_invite: int = 16; jetons_max_reponse: int = 256; temperature: float = 1.0; top_k: int = 50; lot_de_generation: int = 32; controle_invites: int = 200; controle_reponses: int = 8; evaluation_invites: int = 200` (valeurs de nanochat pour `invites_par_pas`, `reponses_par_invite`, `jetons_max_reponse`, `temperature` et `top_k`, « méthodes », §4.3).
- `avantages(recompenses: Tensor) -> Tensor` : forme `[invites, reponses]`, `r − moyenne(r)` par invite, sans division par l'écart-type.
- `class ChargeurInvites(dossier: Path, taille_lot: int, graine: int)` : des problèmes d'un dossier `problemes/` d'usage `entrainement` ; `lot() -> list[Probleme]`, `etat()`, `restaurer()`.
- Le pas de la méthode `grpo` :
  1. génération, modèle en évaluation et sans gradient : `generer_lot` des invites répétées `reponses_par_invite` fois, `graine = (config.graine × 1 000 003 + pas) mod 2³²`, `arret=<|fin_tour|>` ;
  2. récompense 1 si `est_juste`, sinon 0 ; `avantages` ;
  3. apprentissage, en `micro_lot` séquences à la fois : perte = −Σ A · log π(jeton) sur les jetons générés (`<|fin_tour|>` compris, invite exclue) ÷ nombre total de jetons générés du pas ; une mise à jour par pas, sans KL, sans ratio ni écrêtage PPO ;
  4. journal : `perte`, `recompense_moyenne`, `groupes_sans_signal` (part des invites dont toutes les récompenses sont égales), `longueur_moyenne`, `secondes_generation`, `secondes_apprentissage`.
- Validation : `reussite_val`, l'exactitude gloutonne sur `evaluation_invites` problèmes générés à partir de `GRAINES_VALIDATION_RL`, aux difficultés du dossier d'entraînement. Ni les problèmes d'évaluation du rapport ni ceux de l'entraînement ne servent à choisir `meilleur.pt`, qui garde la plus haute `reussite_val`.
- **Le contrôle de départ.** Avant le premier pas d'un entraînement neuf, même avec `--arreter-apres 0` : `controle_invites` problèmes du dossier d'entraînement × `controle_reponses` tirages. Si aucune réponse n'est juste, l'entraînement s'arrête **sans sauvegarde**, avec le code 4 :
  - la ligne de journal `{"evenement": "recompense_nulle", "controle": {...}}` ;
  - le fichier `controle.json` dans la sortie ;
  - le message : « Aucune des N réponses n'est juste : le RL n'aurait aucun signal. Rien n'est lancé. » ;
  - la classe `RecompenseNulle`.
  Sinon, le taux du contrôle est écrit au journal et dans `controle.json`.
- Un manque de mémoire pendant la génération dit de réduire `lot_de_generation` dans `[grpo]`.
- `forge suivi` affiche `recompense_moyenne` et `reussite_val`.

- [ ] **Étape 1 : tests rouges.**

```python
def test_avantages():
    assert avantages(tensor([[1., 0., 0., 1.], [0., 0., 0., 0.]])).tolist() == [[.5, -.5, -.5, .5], [0., 0., 0., 0.]]

def test_groupe_sans_signal_sans_gradient(): ...   # récompenses toutes égales : gradients nuls
def test_grpo_reprise_exacte(tmp_path): ...        # modèle minuscule, 6 pas, pause au pas 3 (processeur)
def test_recompense_nulle(tmp_path): ...           # code 4, ligne de journal, controle.json, aucune sauvegarde
def test_controle_seul(tmp_path): ...              # --arreter-apres 0 : controle.json écrit, aucun pas, aucune sauvegarde
def test_jetons_apres_l_arret_hors_perte(): ...
def test_grpo_refuse_jetons_total(): ...           # ValueError : le nombre de pas vient de [grpo] pas
```
- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire.**
- [ ] **Étape 4 : vérifier**, commit « Forge : mini-GRPO à la nanochat, qui ne se lance que s'il a un signal ».

### Tâche 17 : ton IA 1.9, sur la carte

**Fichiers :** créer `configs/sft-1.9.toml`, `sft-1.9-court.toml`, `grpo-1.9.toml`, `grpo-1.9-court.toml`, `docs/mesures/ton-ia-1.9.md`, `ton-ia-1.9-LISEZMOI.md`.

- [ ] **Étape 1 : les problèmes.**
  - `forge problemes --sortie entrainement-1.9 --nombre 60000 --graine-depart 0` ;
  - `--sortie evaluation-1.9 --nombre 2000 --graine-depart 1000000` ;
  - `--sortie rl-1.9 --nombre 20000 --graine-depart 2000000 --difficultes 1,2`.
  Puis `forge preparer --recette raisonnement-1.9`.
- [ ] **Étape 2 : le SFT des traces.** `forge publication --etiquette ton-ia-1.8`. `configs/sft-1.9.toml` : départ `ton-ia-1.8`, `donnees = "raisonnement-1.9"`, `sortie = "sft-1.9"`, le taux retenu en tâche 12, 2 époques. Essai chronométré (carte et processeur), complet, une pause et sa reprise. Si le complet dépasse une heure, une version courte (`sft-1.9-court.toml`) ; sinon le complet sert aussi de version courte, et `sft-1.9-court.toml` n'est pas créé. Exporter le meilleur vers `publications\ton-ia-1.9-traces` (local, sans Release).
- [ ] **Étape 3 : le contrôle.** `configs/grpo-1.9.toml` : départ `ton-ia-1.9-traces`, `donnees = "rl-1.9"`, `[grpo]`. Lancer `forge entrainer --arreter-apres 0` : il fait seulement le contrôle de départ. Noter le taux.
  - `controle.json` a les clés `invites`, `reponses`, `justes`, `taux` et `lance` (vrai si le RL peut partir) : le projet 1.9 du plan 8 les lit.
  - **Taux nul :** pas de RL. Ton-ia-1.9 est `ton-ia-1.9-traces`, exportée sous ce nom. `docs/mesures/ton-ia-1.9.md` donne le contrôle et l'explique (« méthodes », §4.4). Aller à l'étape 6.
  - **Taux non nul :** continuer.
- [ ] **Étape 4 : les essais de GRPO.** 30 pas à 1e-6, puis 30 pas à 5e-6 (`echauffement = 10`), chacun chronométré. Un essai de 3 pas sur le processeur pour la règle carte contre processeur. Garder le taux dont la `recompense_moyenne` des 10 derniers pas est la plus haute ; si les deux baissent depuis le contrôle, prendre 1e-6. Fixer `pas` = durée visée de 3 h ÷ durée mesurée d'un pas, entre 100 et 600.
- [ ] **Étape 5 : GRPO complet et version courte** (`pas` pour une heure). Pause réelle et reprise. Exporter le meilleur vers `publications\ton-ia-1.9`.
- [ ] **Étape 6 : évaluer.** `evaluer-etape --etape 1.9` sur 1.5, 1.7, 1.8, `ton-ia-1.9-traces`, 1.9 et les versions courtes.
- [ ] **Étape 7 : documents**, comme en tâche 12. En plus : le taux du contrôle, la récompense pas à pas, la part de groupes sans signal, et MGSM et GSM8K-Platinum même à 0 %, avec la comparaison honnête à nanochat d20 (« échelle », A1).
- [ ] **Étape 8 : commit**, puis **(contrôleur)** Release `ton-ia-1.9`, et jalon.

### Tâche 18 : le bac à sable d'exécution, et pass@k

**Fichiers :** créer `forge/code/__init__.py`, `forge/code/execution.py`, `forge/code/passk.py`, `tests/test_execution.py`, `tests/test_passk.py`.

**Interfaces :**

- `@dataclass(frozen=True) class ResultatExecution: reussi: bool; raison: Literal["reussi", "echec", "delai", "memoire", "erreur_systeme"]; sortie: str; secondes: float`.
- `executer(programme: str, delai: float = 5.0, memoire_mo: int = 512, sortie_max: int = 10_000) -> ResultatExecution` :
  - un dossier jetable sous `TEMP` (`tempfile.mkdtemp(prefix="forge-code-")`), effacé à la fin même en cas d'erreur ;
  - `sys.executable -I` avec un petit amorçage : il lit un octet sur l'entrée standard, puis exécute le fichier du programme. Environnement réduit (`SYSTEMROOT`, `PATH` du Python, `TEMP` et `TMP` = le dossier jetable, `PYTHONIOENCODING=utf-8`), dossier courant jetable ;
  - **Windows :** un objet Job (`ctypes`, `kernel32`) avec `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, `JOB_OBJECT_LIMIT_PROCESS_MEMORY` (`memoire_mo` Mio) et `JOB_OBJECT_LIMIT_ACTIVE_PROCESS` (1 processus). Le processus y est rangé **avant** l'envoi de l'octet de départ. Au délai : `TerminateJobObject` ;
  - **ailleurs :** `start_new_session=True`, `RLIMIT_AS` = `memoire_mo`, `RLIMIT_CPU` = délai + 1 ; au délai, `os.killpg` ;
  - sortie et erreurs réunies, tronquées à `sortie_max` caractères ; `raison = "memoire"` si l'erreur est `MemoryError` ;
  - la docstring dit ce qui n'est **pas** empêché : le réseau, l'écriture dans les dossiers de l'utilisateur, la lecture de ses fichiers. Le mot « sûr » n'y figure pas.
- `executer_tous(programmes: Sequence[str], processus: int | None = None, **reglages) -> list[ResultatExecution]` : un `ThreadPoolExecutor` de `fils_disponibles()` fils par défaut, ordre gardé.
- `pass_a_k(n: int, c: int, k: int) -> float` : 1 si `n − c < k`, sinon `1 − Π_{i=n−c+1}^{n} (1 − k/i)`, en boucle, dans cet ordre (forme stable de l'article Codex). **Relire** la formule dans l'article (arXiv 2107.03374) avant d'écrire, et citer sa section en docstring. `ValueError` si `k > n` ou si `c` sort de `[0, n]`.

- [ ] **Étape 1 : tests rouges** (délai de 2 s au plus).
  - `print(1+1)` donne `reussi` ; `assert False` donne `echec`.
  - `while True: pass` donne `delai` en moins de délai + 2 s.
  - Un programme qui lance un enfant qui dort 60 s : aucun processus né du test ne survit (psutil, par PID relevé dans un fichier du dossier jetable avant l'effacement ; sous Windows, la création échoue ou l'enfant est tué) — point à surveiller 4.
  - `bytearray(2 * 1024**3)` donne `memoire` ou `echec`, jamais un blocage.
  - 1 Mo d'affichage donne une sortie de `sortie_max` caractères.
  - Le dossier jetable n'existe plus après l'appel.
  - `pass_a_k(20, 2, 10)` égale `1 − comb(18, 10) / comb(20, 10)` à 1e-12 près ; `pass_a_k(5, 0, 1) == 0` ; `pass_a_k(5, 5, 3) == 1`.
- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire.** Les tests tournent sous Windows (ce PC) et sous Linux (intégration continue).
- [ ] **Étape 4 : vérifier**, commit « Forge : exécuter du code généré dans un sous-processus limité, et pass@k ».

### Tâche 19 : le remplissage au milieu, et la recette du code

**Fichiers :** créer `forge/code/fim.py`, `tests/test_fim.py` ; modifier `forge/affinage/recettes.py` (parts `fim:`, recette `code-1.10`), `forge/__main__.py`.

**Interfaces :**

- `exemple_fim(prefixe: str, milieu: str, suffixe: str, tok) -> ExempleMasque` : `[<|fin_texte|>, <|trou_prefixe|>] + enc(P) + [<|trou_suffixe|>] + enc(S) + [<|trou_milieu|>] + enc(M) + [<|fin_tour|>]`, perte sur `enc(M)` et `<|fin_tour|>`. `milieu` non vide.
- `invite_fim(prefixe, suffixe, tok) -> list[int]` : la même chose, jusqu'à `<|trou_milieu|>` compris.
- `couper_au_hasard(code: str, hasard: Hasard) -> tuple[int, int]` : deux positions en points de code, `0 ≤ debut < fin ≤ len(code)`, tirées uniformément (article d'origine).
- `cas_d_une_ligne(code: str, hasard: Hasard) -> tuple[str, str, str] | None` : une ligne non vide du tiers du milieu, avec son saut de ligne, comme milieu.
- `elements_fim(textes_code: Path, n: int, graine: int, validation: bool) -> Iterator[dict]` : documents des fragments de `textes/principal/code_python` (le code Python sous licence permissive du pré-entraînement), gardés si `est_validation(empreinte) == validation`, et de 1 500 jetons au plus ; éléments `{"sorte": "fim", "prefixe", "milieu", "suffixe"}`.
- `python -m forge fim --sortie NOM --exemples N --graine G [--validation] [--lignes]` (`--lignes` : des cas d'une ligne, pour l'évaluation) écrit dans `conversations/<NOM>/`, avec `usage = "evaluation"` si `--validation`.
- `RECETTES["code-1.10"]` : `code_fr:consignes-code-fr` tout, `luth2_code` 40 000, `fim:fim-1.10` 60 000, `luth2_conversation` 15 000, `problemes:entrainement-1.9` 10 000, `identite` tout.

- [ ] **Étape 1 : tests rouges.**
  - Disposition exacte des ids, et masque.
  - Les coupures tombent sur des points de code (un emoji et des accents n'y sont jamais coupés en deux).
  - Aucun document de validation dans `elements_fim(validation=False)`, et inversement.
  - `cas_d_une_ligne` : préfixe + milieu + suffixe redonne le code.
- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire.**
- [ ] **Étape 4 : vérifier**, commit « Forge : remplir un trou dans du code (FIM, ordre PSM), et la recette de 1.10 ».

### Tâche 20 : la traduction maison

**Fichiers :** créer `forge/donnees/traduction.py`, `tests/test_traduction.py` ; modifier `projets/forge/pyproject.toml` (extra `traduction`), `uv.lock`, `forge/__main__.py`, `forge/conversation/sources.py` (source locale `humaneval_fr`, usage évaluation), `docs/donnees.md` ; créer `docs/mesures/donnees-ton-ia-2-LISEZMOI.md`.

**Interfaces :**

- Extra `traduction = ["transformers==5.22.1"]`. Ni l'intégration continue ni les tests ne l'installent : les tests utilisent un faux traducteur.
- `MODELE_TRADUCTEUR = "Qwen/Qwen3-4B"` ; `REVISION_TRADUCTEUR` : le commit de la fiche, relevé à cette tâche.
- `CONSIGNE_DE_TRADUCTION` = « Traduis en français le texte qui suit. Ne traduis ni le code, ni les noms de fonctions et de variables, ni ce qui est entre accents graves ou entre guillemets droits. Garde les sauts de ligne. Réponds seulement par la traduction. »
- `class Traducteur(modele: str = MODELE_TRADUCTEUR, revision: str = REVISION_TRADUCTEUR, appareil: str = "cuda")` : bf16, gabarit de conversation du modèle avec `enable_thinking=False`, glouton, `max_new_tokens` = 2 × jetons d'entrée + 64, par lots ; `traduire(textes: Sequence[str]) -> list[str]`.
- `traduction_acceptable(source: str, traduction: str) -> bool` : mêmes passages entre accents graves et mêmes blocs de code, `langue(traduction) != "autre"`, rapport des longueurs entre 0,5 et 2,5.
- `traduire_consignes_code(traducteur, sortie: Path, exemples_max: int) -> dict` : traduit les instructions de `opc_educational`, garde le code et le test tels quels, refuse les traductions non acceptables, puis exécute `code + "\n" + test` par `executer_tous` (délai 5 s) et ne garde que ce qui réussit. Éléments `{"sorte": "conversation", "tours": [utilisateur : la consigne traduite ; assistant : « ```python\n{code}\n``` »], "test": test}`, sous `conversations/consignes-code-fr/`, `usage = "entrainement"`, licence MIT. Repris par fragments.
- `traduire_humaneval(traducteur, sortie: Path) -> dict` : pour chaque problème, la docstring de la fonction visée est trouvée par `ast`. Seules ses lignes de prose sont traduites ; les lignes `>>>` et leurs sorties restent telles quelles. Le `prompt` est reconstruit, puis on vérifie que `prompt_fr + canonical_solution + test + check(entry_point)` réussit. Vers `conversations/humaneval_fr/`, `usage = "evaluation"`, licence MIT.
- `python -m forge traduire --jeu consignes-code|humaneval [--exemples-max N]`.

- [ ] **Étape 1 : la licence, avant tout code.** Lire la fiche de `Qwen/Qwen3-4B` sur Hugging Face. Si elle ne dit pas `apache-2.0`, s'arrêter et le dire au contrôleur. Sinon, noter le commit et la date de lecture.
- [ ] **Étape 2 : tests rouges**, avec un faux traducteur (dictionnaire).
  - Une traduction qui change un passage entre accents graves est refusée.
  - HumanEval : le code hors docstring reste identique (comparaison des arbres `ast` sans docstrings), les lignes `>>>` aussi.
  - Une consigne dont le code échoue à ses tests est écartée et comptée.
  - Reprise après coupure, sans doublon.
  - Le jeu `humaneval_fr` porte `usage == "evaluation"`, et `preparer_jeu` le refuse (point à surveiller 5).
- [ ] **Étape 3 : écrire.**
- [ ] **Étape 4 : vérifier**, `uv lock`, commit « Forge : traduction maison des consignes de code et de HumanEval, par Qwen3-4B ».
- [ ] **Étape 5 : la vraie traduction, sur la carte.**
  - `uv sync --extra gpu --extra traduction`.
  - `forge conversations --source opc_educational --exemples-max 60000`.
  - Essai chronométré sur 50 consignes, sur la carte et sur le processeur.
  - `forge traduire --jeu humaneval`, puis `--jeu consignes-code --exemples-max 50000`, par `travail-long.ps1`.
  - Relire 20 traductions de chaque jeu à la main, et noter les défauts vus.
  - `docs/mesures/donnees-ton-ia-2-LISEZMOI.md` : les deux jeux, leurs sources et licences, le traducteur (modèle, révision, licence, consigne), les contrôles, les taux d'écart, la relecture, et la commande pour les refaire.
- [ ] **Étape 6 : commit** « Données de la vague 2 : HumanEval-FR et consignes de code traduites, avec leur fiche ». **(Contrôleur)** Release `donnees-ton-ia-2`, avec `humaneval-fr.jsonl.gz`, `consignes-code-fr.jsonl.gz` (les fragments réunis) et `LISEZMOI.md`.

### Tâche 21 : l'évaluation du code

**Fichiers :** créer `forge/code/bancs.py`, `tests/test_bancs.py` ; modifier `forge/evaluation/etape.py` (mesures `humaneval`, `humaneval_fr`, `fim_ligne`, étape `"1.10"`).

**Interfaces :**

- `ARRETS_HUMANEVAL = ("\nclass", "\ndef", "\n#", "\nif", "\nprint")` : les arrêts de l'article Codex, **à vérifier** dans l'article à cette tâche (sinon, ceux de l'article et une note).
- `couper_completion_brute(texte: str) -> str` : coupe au premier arrêt.
- `extraire_code(texte: str) -> str` : le premier bloc `` ```python `` (ou `` ``` ``), sinon le texte entier.
- `programme_humaneval(probleme: dict, completion: str, mode: Literal["brut", "conversation"]) -> str` : en `brut`, `prompt + completion` ; en `conversation`, le code extrait, qui doit définir `entry_point` (sinon `prompt + code`). Puis `test` et `check(entry_point)`.
- Les mesures `humaneval` et `humaneval_fr`, chacune en deux modes :
  - `brut` : la suite du `prompt`, comme un modèle de base ;
  - `conversation` : « Complète la fonction suivante.\n```python\n{prompt}\n``` » par `repondre_lot`.
  Pour chaque mode : pass@1 en glouton (512 jetons), pass@10 par `pass_a_k` sur n = 20 tirages (température 0,8, top-k 50), exécution par `executer_tous` (délai 5 s). Clés : `{brut: {pass_1, pass_10}, conversation: {pass_1, pass_10}, n, exemples}` (`exemples` : les 6 premiers problèmes, la complétion gloutonne et son verdict).
- `fim_ligne` : 500 cas d'une ligne (jeu `--validation --lignes` de la tâche 19), glouton, 64 jetons, exact après retrait des blancs de fin. Clés : `{exacte, n}`.
- `MESURES_PAR_ETAPE["1.10"]` : `ifeval_fr`, `tenue`, `oubli`, `problemes`, `humaneval`, `humaneval_fr`, `fim_ligne`, `echantillons`.

- [ ] **Étape 1 : tests rouges.** La solution de référence donne pass@1 = 1 ; une complétion fausse, 0 ; les arrêts ; l'extraction d'un bloc ; une réponse sans bloc ; une boucle infinie comptée comme un échec, sans bloquer l'évaluation.
- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire.**
- [ ] **Étape 4 : vérifier**, commit « Forge : évaluer le code de ton IA par exécution (HumanEval, HumanEval-FR, une ligne à remplir) ».

### Tâche 22 : ton IA 1.10, sur la carte, et le bilan du moteur

**Fichiers :** créer `configs/sft-1.10.toml`, `sft-1.10-court.toml`, `docs/mesures/ton-ia-1.10.md`, `ton-ia-1.10-LISEZMOI.md` ; modifier `projets/forge/README.md`, `docs/donnees.md`.

- [ ] **Étape 1 : les données.** `forge conversations --source luth2_code`. `forge fim --sortie fim-1.10 --exemples 60000 --graine 0`, puis `--sortie fim-lignes-eval --exemples 500 --graine 1 --validation --lignes`. Puis `forge preparer --recette code-1.10`.
- [ ] **Étape 2 : le SFT.** `forge publication --etiquette ton-ia-1.9`. `configs/sft-1.10.toml` : départ `ton-ia-1.9`, taux de 1.7, 2 époques. Essai chronométré, complet (avec une pause et sa reprise), version courte.
- [ ] **Étape 3 : exporter et évaluer.** Exporter vers `publications\ton-ia-1.10`. `evaluer-etape --etape 1.10` sur 1.5, 1.7, 1.8, 1.9, 1.10 et la version courte : la table du code à travers les versions.
- [ ] **Étape 4 : documents**, comme en tâche 12. En plus : le bac à sable et ses limites, et les scores même proches de 0, avec nanochat d20 et Qwen2.5-Coder-0.5B en repères (« échelle », A1 et A4).
- [ ] **Étape 5 : le bilan du moteur.**
  - Le README de forge : une section par étape (commandes dans l'ordre, versions courte et complète, durées mesurées, reprise).
  - `docs/donnees.md` à jour.
  - Les durées réelles remplacent les estimations dans `docs/mesures/`.
  - `uv run --extra gpu pytest -q -m "not gpu" --durations=15` : si le job « Tests de forge » approche ses 25 minutes, le porter à 35 et le dire.
- [ ] **Étape 6 : commit**, puis **(contrôleur)** Release `ton-ia-1.10`, et le jalon : « Projet forge-ia (La Forge IA) : moteur de la vague 2 fini ; ton-ia-1.7, 1.8, 1.9 et 1.10 publiées le JJ/MM/AAAA, chacune affinée depuis la précédente (SFT, DPO, GRPO si signal, code et FIM). »

---

## Exécution

- **Modèles :** les tâches 4, 6, 14, 16 et 18 (cache, boucle, DPO, GRPO, bac à sable) prennent le modèle le plus capable ; les autres, un modèle standard ; les tâches sur la carte (12, 15, 17, 20 étape 5, 22) sont tenues par le contrôleur avec un agent standard.
- **Revue :** une relecture par tâche ; une revue finale du plan.
- **Ordre :** 1 à 11, puis 12 ; 13 et 14, puis 15 ; 16, puis 17 ; 18 à 21, puis 22. Les tâches 18 à 21 peuvent s'écrire pendant les entraînements de 15 et 17 (processeur seulement).
- **Poussée :** le contrôleur pousse après chaque tâche relue ; la CI doit être verte.
