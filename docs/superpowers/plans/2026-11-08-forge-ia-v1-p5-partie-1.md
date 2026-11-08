# La Forge IA, vague 1, plan 5 : la Partie 1, le cœur (1.1, 1.2, 1.4, 1.5, 1.6), le glossaire et l'annuaire

> **Pour les agents qui exécutent ce plan :** SOUS-SKILL REQUIS : utiliser superpowers:subagent-driven-development (recommandé) ou superpowers:executing-plans pour réaliser ce plan tâche par tâche. Les étapes utilisent des cases à cocher (`- [ ]`).

**But :** finir la vague 1. Écrire les chapitres 1.1, 1.2 et 1.4 et les faire paraître pendant que ton IA s'entraîne, sans jamais toucher à la carte graphique. Écrire 1.5 et 1.6 en brouillon avec la version d'une heure de ton IA (« mini »). Construire la première version du glossaire et de l'annuaire des données, avec la page d'annexe du calculateur. Puis, une fois l'entraînement fini et la tâche 14 du plan 2 faite (ton-ia-1.5 publiée), passer les projets sur la carte, verser les vrais chiffres de ton IA et faire paraître 1.5 et 1.6.

**Architecture :**

- **Un projet par chapitre** (`projets/1.N-<nom>/`), testé par pytest, avec son notebook (`notebooks/1.N-<nom>.ipynb`), comme au plan 4.
  - 1.1 est en Python pur.
  - 1.2, 1.4, 1.5 et 1.6 s'appuient sur le paquet `forge` par une **dépendance de chemin** (`../forge`, en mode modifiable), sans jamais le modifier (choix 3).
- **Des jumeaux TypeScript** (`site/src/lib/partie-1/`) refont dans le navigateur ce que les ateliers montrent :
  - n-grammes de 1.1 ;
  - nettoyeur de 1.2 ;
  - répartition des paramètres de 1.4 ;
  - marge des QCM de 1.6.

  Le Python écrit les attendus JSON, et Vitest (plus Firefox et WebKit pour 1.1 et 1.2) vérifie l'égalité exacte.
- **Le code de `forge` se montre sans marqueur.** `CodeExplique` gagne une prop `symbole` qui extrait une fonction ou une méthode Python par son nom (tâche 1). Les fichiers de forge restent intacts.
- **Brouillons, `data-a-mesurer` et parution par `git mv`**, exactement comme au plan 4 : `site/src/lib/brouillons.ts`, `e2e/parution.spec.ts`, et la section « Parution d'un chapitre » du README.
- **Les chiffres de ton IA viennent de fichiers versionnés**, écrits par les projets à partir des journaux et des rapports de `D:\forge-ia-donnees`, qu'ils lisent sans les modifier. Pour « mini », ces fichiers s'écrivent tout de suite. Pour ton-ia-1.5, ils s'écrivent à la porte (tâche 15) ; d'ici là, la page affiche « à mesurer ».

**Pile technique :** celle du plan 4 (Astro 7.4, Svelte 5.57, TypeScript, Vitest, Playwright avec `@axe-core/playwright`, svelte-check ; Python 3.12, uv 0.13, pytest, nbclient ; PyTorch 2.15.0, roues `cpu` maintenant et `cu132` à la porte). Aucune nouvelle dépendance npm. Python : aucune dépendance nouvelle hors `forge-ia` (chemin) et ce qu'il tire déjà (`datasets`, `regex`, `numpy`, `safetensors`, `psutil`, `tomli-w`).

**Spécification :** `docs/superpowers/specs/2026-11-02-forge-ia-design.md`, surtout les sections 4 (« une seule IA qui grandit »), 5 (gabarit), 6 (allure et annexes à maquetter), 7 (démos et cohérence des moteurs), 8 (code, projets, notebooks, pause et reprise, vrais résultats), 9 (honnêteté), 11 (machine) et 12 (vague 1).

**Plans précédents, livrés :** p1 (gabarit, 1.3, `parcours.ts`, `ANNEXES`), p2 (paquet `forge`, entraînement en cours, tâche 14 en attente), p3 (`MiniModele`, `AnimationAttention`, `Calculateur` et la note « Note pour le plan 5 : les cartes de ton IA » de `projets/mini-modele/README.md`), p4 (Partie 0, brouillons, `SortieCommande`, `data-a-mesurer`, job `notebooks-colab`). Ledgers : `.superpowers/sdd/<plan>/progress.md`.

## Place de ce plan dans la vague 1

C'est le plan 5 du découpage du plan 1 : « rédaction des chapitres 1.1, 1.2, 1.4, 1.5 et 1.6, plus l'annuaire et le glossaire ». Le plan 3 lui a aussi confié la maquette des annexes et la page d'annexe du calculateur. La « liste Colab de la vague et sa validation par l'utilisateur » du plan 1 n'existe plus : la décision du 04/11/2026 la remplace (spécification, section 8).

Hors de ce plan :

- l'annexe « Matériel », qui reste « à venir » (vague 6, « le reste des annexes ») ;
- les sections « modèles » et « outils » de l'annuaire (vagues 2 et suivantes) ;
- la tâche 14 du plan 2 (évaluation finale, porte d'accord, `gh release create ton-ia-1.5`), que ce plan attend sans la faire.

## Recherche faite avant ce plan (le 08/11/2026)

Toutes les sources ont été lues le 08/11/2026, sauf mention.

- **FineWeb-2** (`HuggingFaceFW/fineweb-2`, carte du jeu, https://huggingface.co/datasets/HuggingFaceFW/fineweb-2/raw/main/README.md) :
  - licence ODC-By 1.0, plus les conditions d'utilisation de Common Crawl ; accès sans formulaire ;
  - version 2.1.1 du 27/10/2025, la dernière du journal des versions ;
  - en tout : 3 339 271 691 958 mots, 5 018 505 566 documents, 20,78 To de texte UTF-8, 8,58 To sur disque ;
  - français (`fra_Latn`) : 220 662 584 640 mots, 360 058 973 documents, « 502.82GB » (des Gio, voir la ligne suivante) ;
  - traitement : identification de langue par GlotLID, dédoublonnage par langue sur tout le jeu (colonne `minhash_cluster_size`), puis « réhydratation » (des documents remis en plusieurs exemplaires selon la taille de leur grappe) ; article arXiv 2506.20920.
- **Une erreur dans `docs/donnees.md`.** L'API de Hugging Face (https://huggingface.co/api/datasets/HuggingFaceFW/fineweb-2/tree/main/data/fra_Latn/train) donne 135 fichiers et 539 897 427 722 octets en tout ; le premier fichier fait 4 845 859 492 octets. Le document dit « 135 fichiers parquet, environ 4,85 Go en tout » : 4,85 Go est la taille d'**un** fichier. La tâche 5 corrige cette ligne. 539 897 427 722 octets valent 502,8 Gio, ce qui confirme que les « GB » de la carte sont des Gio.
- **Wikipédia** (`wikimedia/wikipedia`, https://huggingface.co/datasets/wikimedia/wikipedia, et l'API de son arbre de fichiers) :
  - seules les copies du 01/11/2023 existent (323 configurations, toutes `20231101.*`) ;
  - `20231101.fr` : 2,56 millions de lignes, 17 fichiers, 4 614 488 286 octets ;
  - licences annoncées : `cc-by-sa-3.0` et `gfdl`.
  - Wikipédia est passée à CC BY-SA 4.0 pour les modifications faites à partir de juin 2023, et les anciennes restent en 3.0 (Creative Commons, billet du 29/06/2023, https://creativecommons.org/2023/06/29/wikipedia-moves-to-cc-4-0-licenses/). La copie de novembre 2023 mêle donc les deux versions : c'est ma lecture des deux sources, à dire comme telle.
- **Code** (`codeparrot/github-code-clean`, https://huggingface.co/datasets/codeparrot/github-code-clean) :
  - compilation sous Apache-2.0, 314 Go, sans formulaire ;
  - filtres annoncés : longueur moyenne des lignes sous 100, part de caractères alphanumériques au-dessus de 0,25, fichiers générés retirés ;
  - la carte ne parle pas de dédoublonnage et ne date pas les données. La licence par fichier (colonne `license`) est celle qu'a relevée le plan 2.
- **Autres jeux, pour l'annuaire.** Relevé par l'API (`/api/datasets/<nom>` : licence, accès, dernière modification), puis sur les cartes pour les quatre premiers :
  - `PleIAs/common_corpus` : 2 267 302 720 836 jetons, « uncopyrighted or freely licensed », surtout de l'anglais et du français, dont 283 227 402 898 jetons de code ; arXiv 2410.22587 ; sans formulaire ;
  - `OpenLLM-France/Lucie-Training-Dataset` : CC BY-NC-SA 4.0, donc **pas d'usage commercial** ; sans formulaire ;
  - `croissantllm/croissant_dataset` : pas de licence unique (« subject to the original license », renvoi au rapport technique arXiv 2402.00786) ;
  - `openai/MMMLU` : MIT ; MMLU traduit par des « professional human translators » ; français en `FR_FR`, environ 14 000 lignes ;
  - `bigcode/the-stack-v2` et `uonlp/CulturaX` : conditions à accepter (`gated: auto`) ; `oscar-corpus/OSCAR-2301` : accord manuel (`gated: manual`) ; `HuggingFaceFW/fineweb-edu` : ODC-By, en anglais.
- **Évaluation de ton IA.** `manu/french_bench_hellaswag` : 9,34 milliers de lignes de validation. Sa page n'indique aucune licence, et son README est vide (« README.md exists but content is empty »). FrenchBench vient de l'article de CroissantLLM (arXiv 2402.00786, déjà cité par le plan 2).
- **Llama 3** (arXiv 2407.21783, version HTML v3) :
  - section 3.1.2 : mélange final d'environ 50 % de connaissances générales, 25 % de maths et de raisonnement, 17 % de code et 8 % de multilingue ;
  - section 3.1.1 : dédoublonnage par adresse, par document (MinHash global) et par ligne ;
  - section 3.1 : connaissances « until the end of 2023 » ;
  - section 3.3 : « up to 16K H100 GPUs », 700 W, 80 Go ; sur un relevé de 54 jours, 466 interruptions ;
  - section 5.1.1, tableau 8 : bancs de compréhension de lecture, code (HumanEval, MBPP), sens commun, maths et raisonnement (GSM8K, MATH, ARC Challenge…), et agrégats (MMLU, MMLU-Pro, AGIEval, BIG-Bench Hard). Les écarts sont donnés en intervalles de confiance à 95 % ;
  - section 5.1.4 : contamination mesurée par recouvrement de 8-grammes.

  Ce qui est déjà relevé dans `site/src/lib/calculateur/donnees.ts` (15 600 milliards de jetons, 3,8 × 10²⁵ opérations, formes 8B, 70B et 405B) se réutilise tel quel.
- **Llama 3.1, fiche du modèle** (https://github.com/meta-llama/llama-models/blob/main/models/llama3_1/MODEL_CARD.md) :
  - le 405B a demandé 30,84 millions d'heures de carte H100-80GB, sur 39,3 millions pour les trois tailles, et 8 930 t éq. CO₂ (méthode « location-based ») ;
  - environ 15 000 milliards de jetons, données arrêtées en décembre 2023 ;
  - 405B pré-entraîné : MMLU 85,2 (5 exemples), ARC-Challenge 96,1 (25 exemples).
- **Les pièces du transformer**, lues sur arXiv :
  - Vaswani et al., « Attention Is All You Need », 1706.03762, 12/06/2017 (« based solely on attention mechanisms ») ;
  - Su et al., RoFormer, 2104.09864, 20/04/2021 (rotation pour la position absolue, dépendance relative dans l'attention) ;
  - Shazeer, « GLU Variants Improve Transformer », 2002.05202, 12/02/2020. Le résumé dit que certaines variantes GLU font mieux que ReLU et GELU, mais ne nomme pas SwiGLU : ne citer que ce que dit le résumé, ou lire le corps de l'article dans la tâche ;
  - Zhang et Sennrich, RMSNorm, 1910.07467, 16/10/2019 (temps de calcul réduit de 7 % à 64 %).
- **Modèles à n-grammes.** Bengio et al., « A Neural Probabilistic Language Model », JMLR 3, 2003, p. 1137-1155 (https://www.jmlr.org/papers/v3/bengio03a.html). Le résumé décrit la « curse of dimensionality » : une suite de mots du test diffère vraisemblablement de toutes celles de l'entraînement.
- **Droit européen.** Règlement (UE) 2024/1689, article 53(1)(c) et (d) (https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng). Le fournisseur d'un modèle d'IA à usage général doit :
  - avoir une politique de respect du droit d'auteur, y compris des réserves de droits de l'article 4(3) de la directive 2019/790 ;
  - publier un résumé « suffisamment détaillé » des contenus d'entraînement, selon un modèle du Bureau de l'IA.

  La date d'application (article 113) n'a pas été lue : la tâche 6 la vérifie avant de l'écrire, ou ne la donne pas.
- **Colab** (https://github.com/googlecolab/backend-info, dernier commit le 04/11/2026 à 23:42 UTC, « Update PyTorch to 2.14.1 for CPU and GPU ») :
  - Python 3.13.16 sur l'image avec carte ;
  - `torch==2.14.1+cu130`, `numpy==2.4.6`, `datasets==4.8.5`, `safetensors==0.8.0`, `regex==2025.11.3`, `psutil==5.9.5`, `ipykernel==6.17.1` ;
  - **pas de `tomli-w`**, et `psutil` est en dessous de la version que `forge` demande (6.0 ou plus).

  Les modules de forge que les notebooks utilisent importent `datasets`, `safetensors` et `tomli_w` à l'intérieur de leurs fonctions, et seul `mesure.py` importe `psutil` (relevé dans `projets/forge/forge/`) : d'où le choix 6.
- **Versions** (PyPI) : torch 2.15.0, la dernière ; datasets 5.1.0, la dernière (forge demande 4.0 ou plus).

## Choix de ce plan

1. **Autonomie** (décision de l'utilisateur du 08/11/2026, « Seul, comme le plan 4 »). Le plan s'exécute sans rien lui demander.
   - Un chapitre paraît sans question, dès qu'il est fini et relu et que son notebook passe. Le contrôleur pousse.
   - La seule porte d'accord qui reste est celle du plan 2, avant `gh release create ton-ia-1.5`. Elle n'est pas dans ce plan.
   - L'utilisateur signale les problèmes qu'il voit à l'usage ; ils se corrigent comme des retours de relecture.
2. **La carte graphique attend la fin de l'entraînement** (« Garder pour après »). Au 07/11/2026 à 22:53, l'entraînement en était au pas 10 479 sur 16 540, avec environ 2 j 7 h de calcul restant : il finira vers le 10/11, plus les pauses de jeu.
   - Jusqu'à la tâche 15, aucune tâche n'utilise la carte ; l'entraînement n'est jamais mis en pause pour ce plan.
   - Les passages sur la carte (projets 1.5 et 1.6 lancés en entier, leurs notebooks, et les tests `gpu` de 1.4 à 1.6) sont regroupés dans la tâche 15.
3. **Forge, sans le modifier.** Les projets 1.2, 1.4, 1.5 et 1.6 déclarent `forge-ia` en dépendance, avec `[tool.uv.sources] forge-ia = { path = "../forge", editable = true }`.
   - La spécification veut que « chaque projet de chapitre s'appuie » sur forge. Le lecteur clone tout le dépôt (`RecupererProjet`), et une copie gardée par un test, comme au plan 4, recopierait des milliers de lignes.
   - La base de forge ne demande pas PyTorch, qui vient des extras : 1.2 n'a donc pas PyTorch (forge.donnees ne l'importe pas), et 1.4 à 1.6 ont les extras `cpu` et `gpu` de forge.
   - Contrôle à chaque tâche : `git status --short projets/forge` reste vide.
4. **Le code de forge montré par symbole.** `extraireSymbole(source, "Attention.forward", fichier)` rend le bloc d'une fonction, d'une classe ou d'une méthode, par l'indentation et sans sa docstring (option `docstring`). Une ligne visée qui n'existe pas, ou un symbole absent, fait échouer la construction, comme pour les régions.
5. **1.1, un modèle à n-grammes de caractères**, sur le texte du site lui-même.
   - Les fichiers MDX parus au commit `ae8d9a4` (0.1 à 0.5 et 1.3) sont réduits à leur prose par `python -m modele_de_langage extraire`, puis figés dans `donnees/texte-du-site.txt`. C'est notre texte, sous CC BY 4.0 : aucun téléchargement, et aucune licence tierce.
   - Les comptes et le lissage de Laplace sont des entiers et une division ; les poids de température sont des entiers, des carrés ou une racine carrée. Tout est donc exact en JavaScript comme en Python, et les tirages aussi (même générateur `Hasard` que 0.2, recopié et gardé par un test).
   - Les perplexités demandent `exp` et `log` : elles viennent seulement du Python.
6. **Notebooks de 1.2 à 1.6, sans rien installer.** Comme le notebook 0.5, ils clonent le dépôt (ou prennent `FORGE_IA_LOCAL`), puis ajoutent `projets/forge` et leur projet à `sys.path`. Pas de `pip install` de forge : tout ce qu'ils importent est déjà dans Colab (`regex`, `numpy`, `torch`, et au besoin `datasets` et `safetensors`).
   - Ils n'appellent jamais `forge.mesure` (qui importe `psutil`) ni ce qui écrit du TOML.
   - Chaque tâche de notebook ajoute à `outils/colab-sans-carte.txt` les versions de Colab de ce qu'il importe.
7. **1.5 et 1.6 s'écrivent avant la porte, avec « mini ».** La version d'une heure de ton IA (03/11/2026) a son journal et son rapport, lisibles dès maintenant :
   - `D:\forge-ia-donnees\entrainements\ton-ia-mini\journal.jsonl` ;
   - `…\evaluation\rapport.json` ;
   - et sa dernière sauvegarde, de 23,2 millions de paramètres.

   C'est aussi la « version courte d'environ une heure » que la spécification promet aux lecteurs. Les brouillons s'écrivent donc en entier, et seules les valeurs de ton-ia-1.5 restent « à mesurer » (`data-a-mesurer`) jusqu'à la tâche 16.
8. **Les cartes d'attention de ton IA** (note du plan 3) : voie « carte seule ».
   - Le projet 1.6 recalcule les poids d'attention d'une phrase à partir des pièces de forge (`rope_cos_sin`, `appliquer_rope`, `proj_qkv` sur l'entrée normée de la couche). Un test prouve que ces poids, appliqués aux valeurs, redonnent la sortie de `Attention` de forge.
   - 1.4 les affiche à la tâche 16, dans un composant à part, `CartesTonIA.svelte`, qui ne refait aucun calcul. `AnimationAttention` garde son exemple du forgeron.
9. **L'atelier des QCM de 1.6 utilise MMMLU en français** (licence MIT, traduit par des humains). Les scores officiels de ton IA restent ceux de FrenchBench (forge), dont la page n'indique pas de licence : on n'en reproduit aucune question, et le chapitre le dit.
10. **Les annexes : maquette tôt, construction plus tard.** La tâche 2 fait `docs/maquettes/annexes.html` (glossaire, annuaire, calculateur) dans la direction B. Le contrôleur l'envoie à l'utilisateur sans attendre de réponse. La construction vient à la tâche 9, après trois chapitres, pour lui laisser le temps de réagir. S'il a réagi entre-temps, ses retours passent avant.
11. **Le glossaire et l'annuaire sont des données TypeScript** (`site/src/lib/annexes/`), testées, rendues par trois pages publiées : `/forge-ia/annexes/glossaire/`, `/annuaire/` et `/calculateur/`.
    - L'accueil fait de chaque annexe construite un lien, et « Matériel » reste « à venir ».
    - L'annuaire, première version, ne liste que des **données** : pré-entraînement en français, code, évaluation.
12. **Le parcours instable `e2e/navigation.spec.ts:148`.** Le 06/11, pendant l'entraînement, `astro preview` servait les fichiers de Pagefind en 0,8 à 1,3 s, une fois sur deux. La tâche 1 donne à l'attente des résultats de ce test un délai de 15 s, avec un commentaire qui en dit la raison. Ce test vérifie des résultats de recherche, pas une vitesse. Aucune tâche n'ajoute de `retries`.
13. **Les leçons de la revue finale du plan 4**, appliquées partout :
    - le pari vient avant le résultat qu'il demande de deviner (m2) ;
    - toute phrase qualitative est gardée par `exiger` sur les nombres qu'elle résume (m5) ;
    - `data-pagefind-ignore` sur les sorties brutes, les grilles et les textes générés (m8) ;
    - « ce chapitre a-t-il paru ? » se demande à `chapitresParus()` seulement (m9) ;
    - la convention des unités est dite une fois par chapitre (m1) ;
    - une carte que PyTorch voit mais ne peut pas utiliser donne un message français, jamais une trace (I1).
14. **Mesures de ce plan.** Aucune tâche ne dépasse 30 minutes de calcul : la règle de l'essai chronométré carte contre processeur ne s'applique pas. Les relevés du processeur se prennent pendant les tâches ; ceux de la carte, seulement à la tâche 15, l'entraînement fini.

## Écarts assumés avec la spécification

- **« Lancé en entier sur la RTX 5070 Ti » :** 1.1 et 1.2 n'utilisent pas la carte, et 1.4 calcule en float64 sur le processeur par construction (égalité avec forge à 10⁻¹² près). Ils paraissent sans passage sur la carte. 1.5 et 1.6 y passent à la tâche 15.
- **Fichiers versionnés qui ressemblent à des données :**
  - `projets/1.1-modele-de-langage/donnees/texte-du-site.txt`, notre propre texte ;
  - `projets/1.2-donnees/exemples/*.jsonl`, écrits à la main pour le cours ;
  - au plus 6 questions MMMLU (licence MIT, citées avec leur source) dans `projets/1.6-evaluation/mesures/qcm-*.json` ;
  - des courbes et des comptes (`mesures/*.json`), qui sont des mesures, pas des données d'entraînement.

  Aucun texte de FineWeb-2, de Wikipédia ou de code tiers n'entre dans le dépôt.
- **Annexes sans « oui » explicite** sur la maquette (spécification, section 6 : « à montrer avant de les construire ») : elle est montrée tôt, sans bloquer (choix 1 et 10).
- **1.1 et 1.4 changent après leur parution** : la tâche 16 leur ajoute une étape sur ton IA (ses jetons suivants, ses cartes d'attention).

## Contraintes globales

Celles du plan 4 (section « Contraintes globales ») restent toutes valables : langue et typographie, caractères invisibles, couleurs et polices, jaune réservé, interdits, mouvement, plancher de qualité, chiffres et sources, code des pages, jumeaux exacts, commits, noms en français, commandes PowerShell. S'y ajoutent ou les remplacent :

- **Caractères invisibles.** `site/src/lib/invisibles.test.ts` lit en plus, s'ils existent :
  - `site/src/lib/partie-1/**`, `site/src/lib/annexes/**`, `site/src/lib/symboles.ts` ;
  - `site/src/components/chapitres/1-1/**`, `1-2/**`, `1-4/**`, `1-5/**`, `1-6/**`, `site/src/pages/annexes/**` ;
  - `site/e2e/chapitre-1-[12456].spec.ts`, `site/e2e/annexes.spec.ts` ;
  - `projets/1.[12456]-*/**/*.py` et leurs `pyproject.toml` ;
  - les cellules de code de `notebooks/1.[12456]-*.ipynb`.
- **Unités.** La mémoire est en Go de 2³⁰ octets, comme le calculateur. Une taille publiée par un site (Hugging Face, PyPI) garde l'unité de ce site, et le chapitre le dit une fois.
- **La carte graphique est à l'entraînement** jusqu'à la tâche 15 :
  - `--extra cpu` seulement, aucun contexte CUDA, aucun WebGPU ni WebGL ;
  - Chrome avec `--disable-gpu`, parcours avec `--workers=4` ;
  - `nvidia-smi` en lecture seule reste permis.
- **Go et stop** (consigne de l'utilisateur du 08/11/2026, qui remplace celle du plan 4) : « Quand je dit stop tu narrete que lentrainement, tu laisse lagent finir et tu nen relance pas. S'il lagent na pas fini quand tu dit go tu relance lentrenement et en continue pour les agent. »
  - Au « stop », le contrôleur ne met que l'entraînement en pause : chien de garde arrêté (et tout Python qui exécute `chien-de-garde.py`), puis `pause-entrainement.ps1`. L'agent en cours termine sa tâche, et aucun nouvel agent n'est lancé.
  - Au « go », le contrôleur relance l'entraînement (`entrainement-principal.ps1 -Reprendre`), attend « Reprise au pas », relance le chien de garde, puis continue avec les agents.
- **Fichiers interdits :**
  - `projets/forge`, en écriture (lecture permise) ;
  - `D:\forge-ia-donnees`, en écriture, sauf sous `cache\` : le cache uv, et `cache\tmp\` pour les dossiers temporaires (`TEMP`, `TMP` et le `FORGE_DONNEES` d'un essai) ;
  - avant la tâche 15, aucune lecture sous `D:\forge-ia-donnees\entrainements\ton-ia\` : ses sauvegardes tournent pendant l'entraînement ;
  - le tokenizer figé `projets/forge/forge/ressources/tokenizer-ton-ia-v1.json`, qui ne se modifie jamais.
- **Dossier temporaire.** Avant toute commande Python, PowerShell : `. .\outils\env-forge.ps1; $env:TEMP = $env:TMP = "$env:FORGE_DONNEES\cache\tmp"`. Le disque C: reste libre.
- **Commandes.** Elles sont celles du plan 4. Pour 1.4 à 1.6 : `uv run --extra cpu pytest -q` ; pour 1.1 et 1.2 : `uv run pytest -q`.
- **Notebooks.** Chacun se rejoue avant son commit : `.colab\Scripts\python outils\executer_notebooks.py notebooks\1.N-<nom>.ipynb`. Attendu : `ok`. Ils ne contiennent ni `pip install torch`, ni `torch.accelerator`, ni `torch.compile`.
- **Parution** (choix 1) : la section « Parution d'un chapitre » du README, sans question à l'utilisateur. Après le déploiement, l'adresse du chapitre répond 200 sur le site public.

## Points à surveiller à la relecture

Les tests ordinaires ne couvrent pas ces cinq situations, les plus susceptibles de gêner un lecteur. Chacune reçoit son test dans la tâche indiquée.

1. **Du texte inhabituel dans le nettoyeur de 1.2** :
   - `\r\n` et `\r` seul ;
   - contrôles C0 et C1, demi-paires de substitution ;
   - lettre suivie d'un accent combinant, emoji, U+FEFF ;
   - espaces Unicode en fin de texte (U+3000, U+2028, U+00A0) ;
   - 199 et 200 caractères comptés en points de code, un texte de 100 000 caractères.

   Attendu : même texte nettoyé, même verdict et même empreinte qu'en Python, et chaque recalcul en moins de 200 ms. Pièges connus : `rstrip()` de Python et `trimEnd()` de JavaScript n'ont pas les mêmes blancs, et `.length` compte des unités UTF-16. Tests en tâches 5 et 6.
2. **Des réglages extrêmes dans l'atelier de 1.1** :
   - contexte jamais vu, caractère hors de l'alphabet ;
   - n plus grand que le texte tapé, champ vide ;
   - température 0 qui tourne en rond, 1 000 tirages.

   Attendu : un message exact pour chaque cas, la parité avec le Python, jamais `NaN`, `Infinity` ni `e+`, et aucun débordement à 390 px. Tests en tâches 3 et 4.
3. **Une valeur de ton-ia-1.5 inventée, tapée à la main ou parue trop tôt.** Attendu :
   - avant la tâche 16, 1.5 et 1.6 sont des brouillons qui contiennent des `[data-a-mesurer]` ;
   - après, aucun, et chaque nombre vient d'un fichier de `mesures/` écrit par un projet ;
   - `e2e/parution.spec.ts` refuse un chapitre paru qui en contient.

   Tests en tâches 11, 13 et 16.
4. **Un lecteur sans carte, ou avec une carte trop ancienne pour la roue `cu132`,** lance `python -m pre_entrainement essai --appareil cuda` ou `python -m evaluation_pas_a_pas … --appareil cuda`. Attendu : un message français qui dit quoi faire (le patron `carte_inutilisable` de 0.4 et 0.5), et le processeur reste possible. Tests en tâches 10 et 12.
5. **Le notebook sur Colab** (Python 3.13, PyTorch 2.14.1, forge non installé, parfois sans carte), et **forge jamais modifié**. Attendu :
   - le notebook importe forge par `sys.path`, n'installe rien et n'appelle ni `forge.mesure` ni `tomli_w` ;
   - il tourne sans carte et dit sur quoi il a tourné ;
   - `git status --short projets/forge` reste vide après `uv sync`.

   Tests : la lecture des notebooks dans chaque `test_notebook.py`, le job `notebooks-colab`, et l'étape « vérifier » de chaque tâche de projet.

---

## Fichiers

```
site/src/lib/symboles.ts (+ test)              extraction d'un symbole Python (tâche 1)
site/src/components/gabarit/CodeExplique.astro  prop `symbole` (tâche 1)
docs/maquettes/annexes.html                     maquette des annexes (tâche 2)
projets/1.1-modele-de-langage/  paquet modele_de_langage  (Python pur)
projets/1.2-donnees/            paquet donnees_pas_a_pas  (forge, sans PyTorch)
projets/1.4-transformer/        paquet transformer_pas_a_pas (forge, PyTorch)
projets/1.5-pre-entrainement/   paquet pre_entrainement   (forge, PyTorch)
projets/1.6-evaluation/         paquet evaluation_pas_a_pas (forge, PyTorch)
notebooks/1.1-modele-de-langage.ipynb, 1.2-donnees.ipynb, 1.4-transformer.ipynb,
  1.5-pre-entrainement.ipynb, 1.6-evaluation.ipynb
site/src/lib/partie-1/   ngrammes.ts, nettoyeur.ts, donnees.ts, parametres.ts, rope.ts,
  journal.ts, evaluation.ts, commandes.ts, fichiers.ts, parite.ts,
  paris-1-1.ts, paris-1-2.ts, paris-1-4.ts, paris-1-5.ts, paris-1-6.ts (+ leurs tests)
site/src/components/chapitres/1-1/ AtelierModeleDeLangage.svelte, OuvertureSuite.astro, TableauPerplexites.astro
site/src/components/chapitres/1-2/ AtelierNettoyeur.svelte, TableauSources.astro
site/src/components/chapitres/1-4/ SchemaTransformer.astro, FigureRope.svelte, AtelierParametres.svelte, CartesTonIA.svelte
site/src/components/chapitres/1-5/ CourbeEntrainement.astro, TableauSessions.astro
site/src/components/chapitres/1-6/ AtelierQcm.svelte, TableauEvaluation.astro
site/src/brouillons/chapitres/1-1.mdx, 1-2.mdx, 1-4.mdx, 1-5.mdx, 1-6.mdx
site/src/lib/annexes/glossaire.ts, annuaire.ts (+ tests)
site/src/pages/annexes/glossaire.astro, annuaire.astro, calculateur.astro
site/src/essais/parite-partie-1.mdx
site/e2e/chapitre-1-1.spec.ts, -1-2, -1-4, -1-5, -1-6, annexes.spec.ts
```

Chaque projet a `pyproject.toml`, `uv.lock`, `README.md`, son paquet et `tests/`, dont `test_notebook.py` sur le patron de `projets/0.5-reseau/tests/test_notebook.py`. Les projets à PyTorch ont aussi `.python-version` (`3.12`). Les nombres d'un chapitre viennent des fichiers listés dans `site/src/lib/partie-1/fichiers.ts` (`FICHIERS_PARTIE_1`), le pendant de `partie-0/fichiers.ts`.

---

### Tâche 1 : le socle de la Partie 1 (symboles, garde-fous, recherche lente)

**Fichiers :**

- Créer : `site/src/lib/symboles.ts`, `site/src/lib/symboles.test.ts`
- Modifier : `site/src/components/gabarit/CodeExplique.astro`, `site/src/essais/gabarit.mdx` (un bloc `symbole`), `site/e2e/gabarit.spec.ts`
- Modifier : `site/src/lib/invisibles.test.ts` (chemins de la Partie 1, voir les contraintes globales)
- Modifier : `site/e2e/navigation.spec.ts` (délai du test de la recherche « images »)
- Créer : `site/src/lib/partie-1/fichiers.ts`, `site/src/lib/partie-1/parite.ts` (vide : `CALCULS_PARTIE_1 = {}`)

**Interfaces (produites) :**

- `extraireSymbole(source: string, symbole: string, fichier = '?', options: { docstring?: boolean } = {}): string`.
  - `symbole` vaut `nom` (une fonction ou une classe au niveau du module) ou `Classe.methode`.
  - Le bloc va de la ligne `def`, `async def` ou `class`, avec les décorateurs juste au-dessus, jusqu'à la dernière ligne plus indentée que lui. Les lignes vides de fin et les commentaires qui suivent au même niveau ne comptent pas.
  - Sans `docstring: true`, la première instruction du corps, si c'est une chaîne (`"""…"""` ou `'''…'''`, sur une ou plusieurs lignes), est retirée.
  - L'indentation commune est enlevée, et les fins de ligne deviennent `\n`.
  - Erreur, si le symbole manque : `Symbole introuvable : ${symbole} dans ${fichier}. Le code a changé : revois le chapitre.`
- `CodeExplique` : `region` devient facultative, à côté de `symbole?: string` et `docstring?: boolean`. Il faut exactement l'une des deux, sinon : `CodeExplique demande region ou symbole (pas les deux) pour ${fichier}.`
- `FICHIERS_PARTIE_1: Readonly<Record<string, string>>`, chemins depuis la racine du dépôt, complétée par chaque tâche ; `CALCULS_PARTIE_1: Record<string, () => unknown>`, qui sert à la page de parité (tâches 3 et 5).

- [ ] **Étape 1 : écrire les tests qui échouent.**

```ts
// symboles.test.ts, sur une source écrite dans le test :
const src = 'import x\n\n@decorateur\ndef f(a):\n    """Doc."""\n    return a\n\n\nclass C:\n    """Doc de C."""\n\n    def m(self):\n        """Doc\n        sur deux lignes."""\n        if self:\n\n            return 1\n        return 2\n\n# commentaire après\nY = 1\n';
expect(extraireSymbole(src, 'f')).toBe('@decorateur\ndef f(a):\n    return a');
expect(extraireSymbole(src, 'f', '?', { docstring: true })).toContain('"""Doc."""');
expect(extraireSymbole(src, 'C.m')).toBe('def m(self):\n    if self:\n\n        return 1\n    return 2');
expect(() => extraireSymbole(src, 'g', 'a.py')).toThrow('Symbole introuvable : g dans a.py');
// Sur le vrai fichier de forge (lecture seule) :
const t = readFileSync('../projets/forge/forge/modele/transformer.py', 'utf8');
expect(extraireSymbole(t, 'Attention.forward').split('\n')[0]).toBe('def forward(self, x: Tensor, cos: Tensor, sin: Tensor) -> Tensor:');
expect(extraireSymbole(t, 'MLP.forward')).toBe('def forward(self, x: Tensor) -> Tensor:\n    return self.proj_basse(F.silu(self.proj_porte(x)) * self.proj_haute(x))');
```

  `e2e/gabarit.spec.ts` gagne un test : sur la page d'essai du gabarit, le bloc `symbole="Bloc.forward"` de `projets/forge/forge/modele/transformer.py` montre ses 3 lignes, et `data-lignes="2-3"` allume les deux additions.
- [ ] **Étape 2 : vérifier l'échec.** Commandes : `npx vitest run src/lib/symboles.test.ts`, puis `npx playwright test e2e/gabarit.spec.ts --workers=4`.
- [ ] **Étape 3 : écrire `symboles.ts`, la prop de `CodeExplique`, le bloc d'essai, `fichiers.ts`, `parite.ts`, et étendre `invisibles.test.ts`.**
- [ ] **Étape 4 : la recherche lente.** Dans le test de `navigation.spec.ts` qui cherche « images » (ligne 148 au 06/11), passer l'attente des résultats à `{ timeout: 15_000 }`. Écrire en commentaire : « pendant un entraînement, le disque D: est occupé et astro preview sert Pagefind en plus d'une seconde (mesuré le 06/11/2026) ; ce test vérifie les résultats, pas la vitesse ».
- [ ] **Étape 5 : tout vérifier.** `npx vitest run`, `npm run check:svelte`, `npx astro check`, `npx playwright test --workers=4`. Attendu : tout passe ; `git status --short projets/forge` est vide.
- [ ] **Étape 6 : commit**, message « Partie 1 : extraits de forge par symbole, garde-fous et recherche lente pendant l'entraînement ».

### Tâche 2 : la maquette des annexes, montrée sans attendre

**Fichiers :**

- Créer : `docs/maquettes/annexes.html` (autonome : polices de `site/public/fonts` en chemins relatifs, ou les familles de repli ; aucun appel externe)

Avant d'écrire, relire `docs/maquettes/maquette-10-fusion-energie.html`, `docs/maquettes/accueil-c.html` et `partie.html`, et les deux mémoires de direction visuelle (`forge-ia-direction-visuelle.md`, `eviter-style-fait-par-ia.md`).

La maquette montre trois pages, avec du vrai contenu tiré de la recherche ci-dessus et des chapitres parus :

- **Le glossaire :**
  - une seule colonne de lecture, avec les lettres en grands chiffres Gabarito dans la marge gauche, comme les numéros d'étape ;
  - par terme : le mot, une définition de deux phrases au plus, « expliqué en 1.3 » en lien, et « voir aussi » ;
  - au moins douze termes réels (jeton, fusion, BPE, tenseur, gradient, perte, perplexité, attention, plongement, lot, taux d'apprentissage, sauvegarde…) ;
  - un champ de filtre souligné de jaune, puisqu'il se manipule.
- **L'annuaire des données :** un tableau typographié, pas de cartes, en trois groupes.
  - Les groupes : textes en français, code, évaluation.
  - Les colonnes : nom (lien), ce que c'est, taille annoncée, licence (lien), accès (libre, conditions à accepter, accord manuel), utilisé par ton IA (et dans quel chapitre), relevé le.
  - Les sources de ton IA sont marquées sans couleur criarde : un trait indigo dans la marge.
  - Sur mobile, chaque ligne devient un bloc de définitions.
- **Le calculateur :** la page d'annexe qui accueille le composant existant, avec son chapeau, et le lien depuis 1.5 et les encadrés « labo ».

Les interdits du plan 4 s'appliquent : pas d'étiquettes en capitales, pas de points médians, pas de cartes arrondies identiques, pas de dégradés.

- [ ] **Étape 1 : écrire la maquette**, lisible dès 390 px.
- [ ] **Étape 2 : captures** ordinateur (1440 × 900) et mobile (390 × 844) des trois pages, par un petit script Playwright dans le dossier temporaire (jamais commité). Les relire avec l'outil de lecture d'images, face à la maquette 10 et aux deux mémoires, puis corriger tout ce qui fait « fait par IA ».
- [ ] **Étape 3 : commit**, message « Maquette des annexes : glossaire, annuaire des données, calculateur ».
- [ ] **Étape 4 (contrôleur) : envoyer le fichier à l'utilisateur sans attendre.**
  - Envoyer `docs/maquettes/annexes.html` et une capture de chaque page (SendUserFile), avec une ligne : « La maquette des annexes. Je les construis après 1.1, 1.2 et 1.4, sauf si tu me dis d'y changer quelque chose. »
  - Noter l'heure dans le ledger, puis continuer avec la tâche 3. Sa réponse, s'il en donne une, est lue avant la tâche 9.

### Tâche 3 : le projet 1.1 « modèle de langage », son notebook et son jumeau

**Fichiers :**

- Créer : `projets/1.1-modele-de-langage/pyproject.toml`, `uv.lock`, `README.md`, `donnees/texte-du-site.txt`
- Créer : `projets/1.1-modele-de-langage/modele_de_langage/__init__.py`, `extraire.py`, `hasard.py`, `ngrammes.py`, `attendus.py`, `__main__.py`
- Test : `tests/test_extraire.py`, `test_ngrammes.py`, `test_hasard.py`, `test_attendus.py`, `test_notebook.py`, `tests/attendus.json`
- Créer : `notebooks/1.1-modele-de-langage.ipynb`
- Créer : `site/src/lib/partie-1/ngrammes.ts`, `ngrammes.test.ts`, `site/src/essais/parite-partie-1.mdx`
- Modifier : `site/src/lib/partie-1/parite.ts` (`'ngrammes'`), `fichiers.ts`, `site/src/components/demos/ControleParite.svelte` (`jeu: 'partie-1'`), `site/e2e/parite.spec.ts` (troisième test, avec `parite-firefox` et `parite-webkit`)

**Interfaces :**

- `pyproject.toml` : nom `modele-de-langage`, aucune dépendance ; groupe de développement `pytest`, `nbclient`, `nbformat`, `ipykernel`.
- `extraire.py` :
  - `extraire_prose(mdx: str) -> str` retire :
    - le frontmatter ;
    - les lignes `import` et `export`, et leurs blocs `export const … = (() => { … })();` ;
    - les blocs de code ;
    - les balises JSX (ouvrantes, fermantes, auto-fermantes, sur une ou plusieurs lignes) et les expressions `{…}`.

    Il garde le texte entre les balises, remplace `&#8239;` par U+202F, et sépare les paragraphes par une ligne vide.
  - `python -m modele_de_langage extraire --commit ae8d9a4 --sortie donnees/texte-du-site.txt` lit, par `git show`, `site/src/content/chapitres/0-1.mdx` à `0-5.mdx` et `1-3.mdx`, dans cet ordre.
- `hasard.py` : copie exacte de la classe `Hasard` de `projets/0.2-maths/maths_utiles/tirage.py`. Un test compare les deux sources de la classe, caractère pour caractère, si l'original existe.
- `ngrammes.py`, régions `compter`, `distribution`, `poids`, `generer` et `perplexite` :
  - `ORDRE_MAX = 6`, `TEMPERATURES = (0, 0.5, 1, 2)` ;
  - `couper(texte: str) -> tuple[str, str]` : entraînement = les 90 premiers % des points de code (`len(texte) * 9 // 10`), validation = le reste ;
  - `alphabet(texte: str) -> list[str]` : points de code distincts, triés ;
  - `compter(texte: str, n: int) -> dict[str, Counter[str]]` : pour chaque position `i ≥ n`, le contexte `texte[i-n:i]` suivi de `texte[i]`. Pour `n = 0`, le contexte est `""` ;
  - `distribution(comptes, alphabet, contexte: str, n: int) -> list[tuple[str, float]]` : le contexte est ses `n` derniers points de code. On renvoie `(c + 1) / (total + V)` pour chaque caractère de l'alphabet (lissage de Laplace, une seule division), triés par probabilité décroissante, puis par point de code. Contexte plus court que `n` : `ValueError("Il faut au moins n caractères de contexte.")` ;
  - `poids(comptes_du_contexte: Counter[str], alphabet, temperature) -> list[float]`, dans l'ordre de l'alphabet : 1 → `c + 1` ; 0,5 → `(c + 1) * (c + 1)` ; 2 → `math.sqrt(c + 1)` ; 0 → 1 pour le premier caractère le plus compté (par point de code en cas d'égalité), 0 ailleurs ;
  - `tirer(poids: list[float], u: float) -> int` : le cumul en boucle, `u * total`, le premier indice dont le cumul dépasse ;
  - `generer(comptes, alphabet, n, depart: str, longueur: int, temperature, graine: int) -> str` : un tirage par caractère avec `Hasard(graine).uniforme()`. `depart` plus court que `n` donne la `ValueError` ci-dessus ; `longueur ≤ 0` rend `depart` ;
  - `part_jamais_vue(comptes, validation: str, n: int) -> tuple[int, int]` : contextes de validation absents des comptes, et total ;
  - `tourne_en_rond(texte: str, longueur: int = 20) -> bool` : les `longueur` derniers caractères apparaissent déjà plus tôt ;
  - `perplexite(comptes, alphabet, n, validation: str) -> float` : `exp` de la moyenne de `-ln p`, en Python seulement ;
  - `charger_texte() -> str`.
- `attendus.py` : `calculer_attendus() -> dict`, écrit avec les règles du plan 4 (`json.dumps(…, ensure_ascii=False, allow_nan=False, indent=1)`, `newline="\n"`) :
  - `alphabet` ;
  - pour chaque n de 0 à 6 : `perplexite_entrainement`, `perplexite_validation`, `jamais_vus` (`[a, b]`), et les `distributions` des contextes de référence (les 10 premiers rangs) ;
  - `suites` : pour n de 1 à 6, chaque température et les graines 0 et 1, 120 caractères depuis le début du texte de validation ;
  - `cas_limites` : texte vide, un seul caractère, `"aaaa"`, un emoji, `"İ"`, et un contexte absent du texte.
- `__main__.py` : `uv run python -m modele_de_langage suite --n 4 --temperature 1 --graine 0 "Le forgeron "`.
- `ngrammes.ts` : `couper`, `alphabet`, `compter(texte, n): Map<string, Map<string, number>>`, `distribution`, `poids`, `tirer`, `generer`, `partJamaisVue`, `tourneEnRond`, `TEXTE_DU_SITE` (import `?raw`), `ALPHABET` (`alphabet(TEXTE_DU_SITE)`, l'alphabet du texte entier, comme en Python) et `PERPLEXITES` (lu dans les attendus). Les points de code se lisent avec `Array.from` ; les comparaisons, avec `comparerPointsDeCode`. Le générateur est le `Hasard` de `site/src/lib/mini-modele/calcul.ts`, importé comme le fait `partie-0/maths.ts`, sans copie.

- [ ] **Étape 1 : écrire les tests Python qui échouent.**

```python
def test_compter_et_laplace():
    c = compter("abab", 1)
    assert c["a"] == Counter({"b": 2}) and c["b"] == Counter({"a": 1})
    d = dict(distribution(c, ["a", "b"], "xa", 1))
    assert d == {"b": 3 / 4, "a": 1 / 4}

def test_contexte_jamais_vu_donne_l_uniforme():
    c = compter("abab", 2)
    assert {p for _, p in distribution(c, ["a", "b"], "bb", 2)} == {0.5}

def test_temperatures():
    cc = Counter({"b": 3})
    assert poids(cc, ["a", "b"], 1) == [1, 4] and poids(cc, ["a", "b"], 0.5) == [1, 16]
    assert poids(cc, ["a", "b"], 2) == [1.0, 2.0] and poids(cc, ["a", "b"], 0) == [0, 1]

def test_generer_reproductible_et_temperature_zero_tourne_en_rond():
    t = charger_texte(); entr, _ = couper(t); c = compter(entr, 3); a = alphabet(t)
    assert generer(c, a, 3, "Le ", 50, 1, 0) == generer(c, a, 3, "Le ", 50, 1, 0)
    assert tourne_en_rond(generer(c, a, 3, "Le ", 300, 0, 0))

def test_texte_du_site_suffit():
    assert len(charger_texte()) >= 60_000
```

  `test_contexte_jamais_vu_donne_l_uniforme` est encadré par `# region: test-uniforme` et `# fin: test-uniforme` : le chapitre le montre. Plus `test_extraire` (sur un MDX écrit dans le test, avec frontmatter, import, `export const`, `<Etape …>` sur deux lignes, `{nombre(x)}`, un bloc de code et `&#8239;`), `test_hasard` (copie identique), `test_attendus_a_jour` et `test_notebook.py`. Le notebook doit afficher « Même résultat que la page du site : oui » et « Défi réussi » pour la correction, et être enregistré sans sorties.
- [ ] **Étape 2 : vérifier l'échec.** Commande : `cd projets/1.1-modele-de-langage; uv run pytest -q`.
- [ ] **Étape 3 : écrire le paquet, extraire le texte, écrire les attendus et le notebook.**
  - **Le notebook**, pour débutants :
    1. compter ce qui suit un caractère ;
    2. des probabilités, et le lissage ;
    3. tirer, avec la température ;
    4. plus de contexte ;
    5. la perplexité ;
    6. la dernière cellule compare les suites aux attendus.
  - **L'exercice** : écrire `le_plus_probable(comptes, contexte, n)`. Sa cellule affiche « Défi réussi » si le résultat est le premier de `distribution`.
  - Puis `uv run python -m modele_de_langage.attendus`.
  - Vérifier, et le noter dans le rapport, que la perplexité de validation passe par un minimum avant n = 6. Sinon, le chapitre change sa phrase (tâche 4), pas les données.
- [ ] **Étape 4 : vérifier que le Python passe.** Commande : `uv run pytest -q`.
- [ ] **Étape 5 : écrire le jumeau et sa parité, tests d'abord.**
  - `ngrammes.test.ts` vérifie, avec `toStrictEqual` :
    - l'alphabet, les distributions, les suites, `jamais_vus` et les cas limites ;
    - compter n = 6 sur le texte entier en moins de 200 ms.
  - La page `parite-partie-1.mdx` et le troisième test de `e2e/parite.spec.ts` font de même dans Chrome, Firefox et WebKit.

  Commandes : `npx vitest run src/lib/partie-1`, puis `npx playwright test e2e/parite.spec.ts --workers=4`.
- [ ] **Étape 6 : rejouer le notebook** dans `.colab` (attendu : `ok`), puis commit, message « Projet 1.1 : un modèle de langage à n-grammes de caractères, en Python et en TypeScript, avec son notebook ».

### Tâche 4 : le chapitre 1.1 « Ce qu'est vraiment un modèle de langage », et sa parution

**Fichiers :**

- Créer : `site/src/components/chapitres/1-1/AtelierModeleDeLangage.svelte`, `OuvertureSuite.astro`, `TableauPerplexites.astro`
- Créer : `site/src/lib/partie-1/paris-1-1.ts`, `paris-1-1.test.ts`
- Créer : `site/src/brouillons/chapitres/1-1.mdx` ; à la parution, `git mv` vers `site/src/content/chapitres/1-1.mdx`
- Test : `site/e2e/chapitre-1-1.spec.ts`

**Interfaces :**

- Consomme : `ngrammes.ts` (tâche 3), `exigeur`, `NombreManipulable`, `Verrou`, `Pari`, `CodeExplique`, `RecupererProjet`, `EncadreLabo`, `MODELES_PUBLICS` (`donnees.ts` du calculateur).
- `paris-1-1.ts`, avec `exigeur('src/lib/partie-1/paris-1-1.ts et le texte des paris du chapitre 1.1')` :
  - `CONTEXTE_DU_PARI = 'ton I'`, `N_DU_PARI = 5` et `choixSuivant()` : trois choix.
    - Les choix : le premier caractère de `distribution` (juste), le deuxième, et le caractère le plus fréquent du texte qui ne suit jamais ce contexte.
    - Gardes : le contexte apparaît dans l'entraînement, et le premier est seul en tête.
    - Si une garde tombe, prendre le premier contexte de 5 caractères du texte qui les passe toutes, et le dire en commentaire.
  - `choixTemperature()` : « Il tourne en rond : les mêmes morceaux reviennent » (juste si `tourneEnRond(generer(…, 0, 0))`), « Il invente sans fin des mots nouveaux », « Il s'arrête au premier point ». Un seul choix juste, par construction.
  - `choixContexte()` : avec n = 6, la part des contextes de validation jamais vus (`partJamaisVue`), en trois tranches : « moins d'un sur dix », « entre un sur dix et la moitié », « plus de la moitié ». La tranche juste est calculée.
  - `choixPerplexite()` : parmi n = 1, n = 3 et n = 6, celui qui a la plus petite perplexité de validation (attendus). Garde : un seul minimum.
- `AtelierModeleDeLangage.svelte` : props `{ texteInitial: string; verrou?: string; acquis?: string }`.
  - Un champ de contexte (`data-test="ml-contexte"`), souligné de jaune.
  - Les réglages : `NombreManipulable` n, de 0 à 6, `canal="ml:n"`, initial 4 ; quatre bascules de température (`.bascule-soleil`, `data-test="ml-t-<t>"`) ; un bouton « Tirer encore » (graine + 1).
  - Les dix premières probabilités en barres CSS (`data-test="ml-distribution"`, `data-pagefind-ignore`), et 200 caractères générés (`data-test="ml-suite"`, `data-pagefind-ignore`).
  - Messages (`data-test="ml-message"`) :
    - « Ce contexte n'apparaît jamais dans le texte : le modèle tire au hasard parmi les {V} caractères. » ;
    - « Il faut au moins {n} caractères de contexte : écris-en un peu plus. » ;
    - avec la température 0 et `tourneEnRond` : « La suite revient sur ses pas : à température 0, elle tourne en rond. ».
  - L'acquis se gagne au premier changement de n. Sans JavaScript, la distribution et la suite du départ restent lisibles.
- **Le chapitre**, frontmatter `partie: 1`, `numero: "1.1"`, `titre: "Ce qu'est vraiment un modèle de langage"`. L'ouverture (`OuvertureSuite`) montre « Le forgeron frappe » et, calculées par le jumeau, les cinq suites les plus probables avec leur probabilité.

| Étape | Titre | Contenu imposé |
| --- | --- | --- |
| 1 | Prédire la suite | Retour sur 0.1 (le mot le plus fréquent, sans hasard). Un modèle de langage donne une probabilité à chaque suite possible. Le texte du site sert de livre : d'où il vient. |
| 2 | Des probabilités, jamais zéro | `CodeExplique` régions `compter` et `distribution`. Le lissage de Laplace, et pourquoi un zéro casserait tout (le −ln de l'étape 7). Pari `suivant`. |
| 3 | Tirer au sort | `poids` et `generer`, la température. Pari `temperature`, avant l'atelier. |
| 4 | L'atelier | `Verrou nom="atelier"` autour de l'atelier (`acquis="atelier"`). |
| 5 | Plus de contexte ? | Pari `contexte`, puis Bengio et al. (2003) : la malédiction de la dimension. Note de marge : ton IA lit 2 048 jetons, pas 6 caractères (`PRESETS_FORGE.tres_grand`). |
| 6 | Le test du texte jamais lu | `couper` : entraînement et validation. |
| 7 | La perplexité | Pari `perplexite`, puis `TableauPerplexites` (attendus). La phrase qui dit où est le minimum est calculée et gardée par `exiger`. |
| 8 | Ce que fera ton IA de plus | Les jetons (1.3), un réseau qui généralise (1.4), l'entraînement (1.5) : la même tâche. `EncadreLabo` : contexte, vocabulaire et jetons d'entraînement de GPT-3 et de Llama 3 (données du calculateur). |
| 9 | Le code et le projet | `CodeExplique` sur la région `test-uniforme`, `RecupererProjet projet="1.1-modele-de-langage"`, « À suivre » vers 1.2 (par `chapitresParus()`). |

**Acquis**, dans l'ordre :

| Clé | Texte | Gagné |
| --- | --- | --- |
| `distribution` | « Un modèle de langage donne une probabilité à chaque suite possible. » | pari `suivant` |
| `temperature` | « La température règle l'audace du tirage. » | pari `temperature` |
| `atelier` | « Le contexte choisit la distribution. » | atelier |
| `contexte` | « Plus de contexte, plus de cas jamais vus. » | pari `contexte` |
| `perplexite` | « La perplexité mesure la surprise sur un texte jamais lu. » | pari `perplexite` |

**Défi :** trouver un contexte de 4 caractères dont la suite la plus probable est une espace, et la vérifier dans l'atelier. Il est vérifié par l'atelier.

- [ ] **Étape 1 : écrire les tests qui échouent.**

```ts
// paris-1-1.test.ts
const c = compter(couper(TEXTE_DU_SITE)[0], N_DU_PARI);
expect(choixSuivant().find((x) => x.juste)?.texte).toBe(`« ${visible(distribution(c, ALPHABET, CONTEXTE_DU_PARI, N_DU_PARI)[0][0])} »`);
for (const f of [choixSuivant, choixTemperature, choixContexte, choixPerplexite]) expect(f().filter((x) => x.juste)).toHaveLength(1);
```

```ts
// e2e/chapitre-1-1.spec.ts (ordinateur et mobile)
test('chapitre 1.1 complet', …);  // « Partie 1, chapitre 1.1 sur 21 » ; 4 paris ; atelier ; recap « 5 sur 5 » ; axe ; 390 px ; lignes ≤ 80
test('les choix des paris viennent du jumeau', …);
test('le code affiché est celui des régions testées', …);
test('atelier : contexte jamais vu, contexte trop court, champ vide, emoji, température 0', …); // messages exacts, < 200 ms
test('atelier : distribution et suite égales au jumeau pour n = 0 à 6', …);
test('avant le pari, l’atelier est verrouillé ; sans JavaScript, tout se lit', …);
```

- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire les paris, l'atelier, les deux composants Astro et le chapitre.** L'allure suit 1.3 : champ et nombre jaunes, barres en indigo doux, suite en chasse fixe.
- [ ] **Étape 4 : tout vérifier**, y compris `invisibles.test.ts`, `npm run check:svelte`, `npx astro check` et `npx playwright test --workers=4`.
- [ ] **Étape 5 : captures et relecture** (ordinateur, mobile, atelier ouvert, message « tourne en rond »), face à 1.3 et aux deux mémoires de direction visuelle.
- [ ] **Étape 6 : commit**, message « Chapitre 1.1 : ce qu'est vraiment un modèle de langage, avec l'atelier des n-grammes (brouillon) ».
- [ ] **Étape 7 : parution** (contrôleur, choix 1), avec la section « Parution d'un chapitre » du README :
  - `git mv` du brouillon vers `content/` ;
  - commentaires « à venir » relus, `npm run build`, commit « Parution du chapitre 1.1 » ;
  - poussée, puis vérifier que le workflow Site est vert et que `/forge-ia/partie-1/1-1/` répond 200.

### Tâche 5 : le projet 1.2 « données », son notebook et le jumeau du nettoyeur

**Fichiers :**

- Créer : `projets/1.2-donnees/pyproject.toml`, `uv.lock`, `README.md`, `exemples/web.jsonl`, `exemples/code.jsonl`
- Créer : `projets/1.2-donnees/donnees_pas_a_pas/__init__.py`, `trier.py`, `apercu.py`, `volumes.py`, `attendus.py`, `__main__.py`
- Créer : `projets/1.2-donnees/sorties/apercu.txt`, `mesures/apercu.json`, `mesures/corpus-principal.json` (écrits par le projet, étape 6)
- Test : `tests/test_trier.py`, `test_volumes.py`, `test_attendus.py`, `test_notebook.py`, `tests/attendus.json`
- Créer : `notebooks/1.2-donnees.ipynb`
- Créer : `site/src/lib/partie-1/nettoyeur.ts`, `nettoyeur.test.ts`, `site/src/lib/partie-1/donnees.ts`, `donnees.test.ts`
- Modifier : `parite.ts` (`'nettoyeur'`), `fichiers.ts`, `site/e2e/parite.spec.ts`
- Modifier : `docs/donnees.md` (la taille du dossier de FineWeb-2 : 135 fichiers d'environ 4,85 Go chacun, 539,9 milliards d'octets en tout, d'après l'API de Hugging Face du 08/11/2026)

**Interfaces :**

- `pyproject.toml` : nom `donnees-pas-a-pas`, `dependencies = ["forge-ia"]`, `[tool.uv.sources] forge-ia = { path = "../forge", editable = true }`, sans PyTorch ; groupe de développement comme en 1.1.
- `exemples/*.jsonl` : environ 20 documents écrits à la main, une ligne `{"text": …}` (et `{"code", "language", "license"}` pour le code). `web.jsonl` commence, dans cet ordre, par :
  1. un texte de 150 caractères ;
  2. un texte de plus de 200 caractères ;
  3. le texte 2 écrit avec `\r\n` ;
  4. une copie exacte du texte 2.

  Viennent ensuite des contrôles, un accent combinant, un emoji. `code.jsonl` contient, dans cet ordre, un fichier Python MIT, un fichier Python GPL-3.0 et un fichier JavaScript MIT.
- `trier.py`, régions `nettoyer`, `doublons`, `licence` et `validation` :
  - `@dataclass Verdict` : `garde: bool`, `raison: Literal["gardé", "trop court", "doublon", "licence", "langage"]`, `texte: str | None`, `empreinte: str | None`, `validation: bool | None` ;
  - `trier(lignes: Iterable[dict], source: Source) -> Iterator[Verdict]`, qui n'appelle que forge (`source.garder`, `nettoyer`, `empreinte_du_texte_nettoye`, `est_validation`) et tient l'ensemble des empreintes vues. Quand `source.garder` refuse une ligne, la raison se lit ainsi : `language` différent de `Python` → `langage`, sinon `licence`. Les sources sont celles de `forge.donnees.sources.SOURCES` ;
  - `compter_raisons(verdicts) -> dict[str, int]`.
- `apercu.py` : `apercu(octets_par_source: int) -> dict`. Il lit en flux chaque source de `forge.donnees.sources` (`lecteur_hugging_face`), passe par `trier`, et s'arrête quand `octets_par_source` octets de texte sont gardés. Il ne garde que les comptes, jamais les textes. Par source : `lus`, `gardes`, raisons, `octets_gardes`, `en_validation`, `secondes`.
- `volumes.py` : `volumes(dossier_jetons: Path) -> dict`. Il lit `.complet` et `index.json` d'un dossier de jetons (lecture seule) : jetons d'entraînement et de validation, octets par jeton, et fragments par source.
- `__main__.py` :
  - `python -m donnees_pas_a_pas trier exemples/web.jsonl` affiche un verdict par ligne ;
  - `apercu --octets 5M --enregistrer sorties/apercu.txt --json mesures/apercu.json` ;
  - `volumes --donnees principal --json mesures/corpus-principal.json`.

  La première ligne de chaque sortie est `# relevé le AAAA-MM-JJ`.
- `nettoyeur.ts` : `normaliser`, `nettoyer(texte): string | null`, `longueurPointsDeCode`, `empreinte(texte): Promise<string>` (SHA-1 par `crypto.subtle`), `estValidation(empreinte, part = 0.005)` et `garderPythonPermissif(ligne)`.
  - C'est une traduction exacte de `forge/donnees/nettoyage.py`, `melange.py` et `sources.py`.
  - Les blancs de fin sont **ceux de `str.isspace()` de Python**, listés dans une constante et vérifiés par les attendus, et pas ceux de `trimEnd()`.
- `donnees.ts` : `MELANGE` (`web_fr`, `wikipedia_fr`, `code_python`, avec leurs parts) et `LICENCES_PERMISSIVES`. `donnees.test.ts` lit le texte de `projets/forge/forge/donnees/melange.py` et `sources.py`, sans les importer, et vérifie que les valeurs sont les mêmes.
- `attendus.py` : pour chaque texte de référence, le texte nettoyé (ou `null`), la longueur en points de code, l'empreinte et `validation` ; les verdicts des exemples ; et `BLANCS_PYTHON`, la liste des points de code où `chr(i).isspace()`.
  - Les textes de référence : les exemples, plus les pièges du point 1 des « Points à surveiller » : U+3000, U+2028, U+00A0 et U+FEFF en fin de texte, 199 et 200 caractères, et `"x" * 100_000`.

- [ ] **Étape 1 : écrire les tests qui échouent.**

```python
def test_court_doublon_licence():
    v = list(trier(lire("exemples/web.jsonl"), SOURCES["web_fr"]))
    assert v[0].raison == "trop court" and v[1].raison == "gardé"
    assert v[2].raison == "doublon" and v[2].empreinte == v[1].empreinte
    assert v[3].raison == "doublon"
    c = list(trier(lire("exemples/code.jsonl"), SOURCES["code_python"]))
    assert [x.raison for x in c] == ["gardé", "licence", "langage"]

def test_trier_fait_comme_forge(tmp_path):
    # Mêmes textes gardés, dans le même ordre, que forge.donnees.telechargement.telecharger
    # avec un lecteur qui rend les exemples.
    ...

def test_volumes(tmp_path):  # sur un dossier de jetons factice : .complet et index.json écrits dans le test
    ...
```

  Plus `test_attendus_a_jour` et `test_notebook.py`. Le notebook affiche « Même résultat que la page du site : oui », et, en local, il lit les exemples au lieu de télécharger.
- [ ] **Étape 2 : vérifier l'échec.** Commande : `cd projets/1.2-donnees; uv run pytest -q`. Puis `git status --short ../forge` : vide.
- [ ] **Étape 3 : écrire le paquet, les attendus et le notebook.**
  - **Le notebook** :
    1. le mélange ;
    2. les trois sources et leurs licences ;
    3. le nettoyage, pas à pas ;
    4. les doublons ;
    5. la licence du code ;
    6. la validation.

    Sur Colab, il lit en flux 2 Mo par source (`datasets` de Colab). Avec `FORGE_IA_LOCAL`, il lit les exemples, et le dit.
  - **L'exercice** : compter les raisons d'écart d'une liste. « Défi réussi » si le compte est celui de `compter_raisons`.
  - Ajouter `datasets==4.8.5` à `outils/colab-sans-carte.txt`, avec sa source dans le commentaire.
- [ ] **Étape 4 : vérifier que le Python passe.**
- [ ] **Étape 5 : écrire le jumeau et sa parité, tests d'abord.** `nettoyeur.test.ts` vérifie chaque attendu (`toStrictEqual`), et que 100 000 caractères se nettoient en moins de 200 ms ; la parité est faite dans les trois navigateurs.
- [ ] **Étape 6 : relever les sorties**, sur le processeur et le réseau. Avant les commandes, `FORGE_DONNEES` vaut `D:\forge-ia-donnees\cache\tmp\apercu-1.2`, effacé ensuite, pour que l'aperçu n'écrive rien ailleurs.
  - `uv run python -m donnees_pas_a_pas apercu --octets 5M …` ;
  - puis, avec le vrai `FORGE_DONNEES`, `volumes --donnees principal …` (lecture seule de `jetons\principal`).

  Les chiffres de `corpus-principal.json` doivent être ceux du ledger du plan 2 (tâche 12 : 8 841 217 367 jetons d'entraînement, 44 490 991 de validation, 4,3513 octets par jeton). Sinon, le dire dans le rapport.
- [ ] **Étape 7 : corriger `docs/donnees.md`**, rejouer le notebook, vérifier que `git status --short projets/forge` est vide, puis commit, message « Projet 1.2 : les données pas à pas sur le code de forge, aperçu réel et nettoyeur en TypeScript ».

### Tâche 6 : le chapitre 1.2 « Les données », et sa parution

**Fichiers :**

- Créer : `site/src/components/chapitres/1-2/AtelierNettoyeur.svelte`, `TableauSources.astro`
- Créer : `site/src/lib/partie-1/paris-1-2.ts`, `paris-1-2.test.ts`
- Créer : `site/src/brouillons/chapitres/1-2.mdx` (puis `git mv`)
- Test : `site/e2e/chapitre-1-2.spec.ts`

**Interfaces :**

- `paris-1-2.ts` :
  - `choixCourt()` : « Ce texte de 150 caractères, sans faute, est-il gardé ? ». Le juste se calcule par `nettoyer`.
  - `choixDoublon()` : « Le même texte, écrit sous Windows (fins de ligne `\r\n`), compte-t-il comme un doublon ? ». Le juste se calcule par les deux empreintes.
  - `choixLicence()` : « Un fichier Python sous GPL-3.0 entre-t-il dans les données de ton IA ? ». Le juste se calcule par `garderPythonPermissif`.
  - `choixPartGardee()` : la part de documents gardés du web dans l'aperçu (`mesures/apercu.json`), en trois tranches calculées.
- `AtelierNettoyeur.svelte` : props `{ texteInitial: string; verrou?: string; acquis?: string }`.
  - Le champ (`data-test="nt-texte"`), puis le texte nettoyé, où chaque retrait est rendu visible (`␍` pour `\r`, `·` pour un contrôle retiré, en encre douce).
  - La phrase « {n} caractères sur les 200 qu'il faut » (`data-test="nt-longueur"`), le verdict (`data-test="nt-verdict"`), les 8 premiers chiffres de l'empreinte (`data-test="nt-empreinte"`), et « ce texte servira à l'entraînement » ou « … à la validation ».
  - Un second champ, « Un autre texte », dit « même empreinte : c'est un doublon » quand c'est le cas.
  - Le calcul de l'empreinte est asynchrone : le verdict s'affiche sans attendre l'empreinte. Rien ne clignote, et `role="status"` n'annonce que les changements de verdict.

| Étape | Titre | Contenu imposé |
| --- | --- | --- |
| 1 | Ton IA est ce qu'elle lit | Le mélange (`MELANGE`), et l'ouverture : les trois sources et leurs parts. |
| 2 | Où trouver des textes | `TableauSources` : nom, taille annoncée, licence, accès, d'après la recherche (FineWeb-2, Wikipédia, github-code-clean), avec lien vers l'annuaire quand il existe. L'unité des tailles de Hugging Face est dite. |
| 3 | Les licences | ODC-By, CC BY-SA 3.0 et 4.0 (et ce que la copie de 2023 mélange), Apache-2.0 de la compilation, et la licence de chaque fichier de code. Pari `licence`. Aucune conclusion juridique sans source : on décrit ce que disent les licences, avec leur lien. |
| 4 | Nettoyer | `CodeExplique symbole="_normaliser"` de `projets/forge/forge/donnees/nettoyage.py`, puis `nettoyer`. Pari `court`. |
| 5 | L'atelier | `Verrou`, `AtelierNettoyeur`. |
| 6 | Les doublons | L'empreinte SHA-1. Pari `doublon`. `CodeExplique` région `doublons` du projet. |
| 7 | Mettre de côté la validation | `est_validation` (`CodeExplique symbole="est_validation"`), 0,5 % des documents, toujours du même côté. |
| 8 | Ce qu'on garde vraiment | Pari `part`, puis `SortieCommande` de `sorties/apercu.txt`. Ensuite les volumes du corpus principal (`mesures/corpus-principal.json`). |
| 9 | Chez un grand labo | `EncadreLabo` : Llama 3 (mélange 50/25/17/8, dédoublonnage par adresse, document et ligne, connaissances jusqu'à fin 2023, 15 000 milliards de jetons), FineWeb-2 (mots, documents, français), et l'article 53 du règlement européen. |
| 10 | Le projet | `RecupererProjet projet="1.2-donnees"`, « À suivre » vers 1.3. |

**Acquis :** `melange`, `licences`, `court`, `atelier`, `doublons`, `validation`, avec des textes du même style qu'en 1.1. Ils se gagnent aux paris et à l'atelier, et le récapitulatif fait « 6 sur 6 ».

**Défi :** écrire dans l'atelier deux textes différents à l'écran mais de même empreinte. Réponse : seuls des textes qui se nettoient pareil y arrivent ; l'atelier le vérifie.

- [ ] **Étape 1 : tests qui échouent** :
  - `paris-1-2.test.ts`, un seul choix juste par pari, calculé par `nettoyeur.ts` ;
  - `e2e/chapitre-1-2.spec.ts`, comme en 1.1, plus : texte de 199 puis 200 caractères, `\r\n` contre `\n`, fichier GPL, 100 000 caractères en moins de 200 ms, et le verdict affiché avant l'empreinte.
- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire.** Vérifier la date d'application de l'article 53 dans l'article 113 du règlement (EUR-Lex), ou ne pas en donner.
- [ ] **Étape 4 : tout vérifier**, comme en tâche 4.
- [ ] **Étape 5 : captures et relecture.**
- [ ] **Étape 6 : commit**, « Chapitre 1.2 : les données, leurs licences et l'atelier du nettoyeur (brouillon) ».
- [ ] **Étape 7 : parution** (contrôleur), comme en tâche 4 : `/forge-ia/partie-1/1-2/` répond 200.

### Tâche 7 : le projet 1.4 « le transformer pièce par pièce », et son notebook

**Fichiers :**

- Créer : `projets/1.4-transformer/pyproject.toml`, `uv.lock`, `.python-version`, `README.md`
- Créer : `projets/1.4-transformer/transformer_pas_a_pas/__init__.py`, `pieces.py`, `comparer.py`, `compter.py`, `attendus.py`, `__main__.py`
- Créer : `projets/1.4-transformer/sorties/comparaison.txt` (écrit par le projet)
- Test : `tests/test_pieces.py`, `test_compter.py`, `test_attendus.py`, `test_notebook.py`, `tests/attendus.json`
- Créer : `notebooks/1.4-transformer.ipynb`
- Créer : `site/src/lib/partie-1/parametres.ts`, `parametres.test.ts`, `site/src/lib/partie-1/rope.ts`, `rope.test.ts`

**Interfaces :**

- `pyproject.toml` : dépendance `forge-ia` (chemin), extras `cpu` et `gpu` en conflit, `torch==2.15.0`, et les deux index : le bloc de 0.5, avec ses marqueurs `# region: pytorch`.
- `pieces.py` : des fonctions pures sur des tenseurs float64, sans `nn.Module` ni `F.scaled_dot_product_attention`. Régions `plongement`, `rmsnorm`, `rope`, `attention`, `masque`, `swiglu`, `bloc` et `modele`.
  - `rmsnorm(x, poids, epsilon=1e-5)` ;
  - `angles_rope(positions: int, dim_tete: int, base: float) -> Tensor` ;
  - `tourner(x, angles)` ;
  - `attention(x, w_qkv, w_sortie, tetes, base)` : scores `q·kᵀ/√d`, masque à `-inf` au-dessus de la diagonale, softmax écrit à la main (soustraire le max, `exp`, diviser par la somme), mélange des valeurs ;
  - `poids_attention(x, w_qkv, tetes, base) -> Tensor[tetes, n, n]` ;
  - `swiglu(x, w_porte, w_haute, w_basse)` ;
  - `bloc(x, p: dict)` ;
  - `modele(ids, p: dict) -> Tensor` (les logits), avec les poids liés.
- `comparer.py` :
  - `poids_de_forge(modele: Transformer) -> dict` ;
  - `ecarts(config: ConfigModele, graine: int = 0) -> dict[str, float]`. Il construit `forge.modele.Transformer(config)` en float64, sur le processeur, puis compare chaque pièce à son module de forge sur un même lot (`rmsnorm`, `rope`, `attention`, `swiglu`, `bloc`, `modele`) et donne l'écart maximal.
- `compter.py` : `repartition(config: ConfigModele) -> dict[str, int]`, avec les clés `plongement`, `attention`, `mlp` et `normes`. La somme vaut `forge.modele.config.nombre_parametres(config)`.
- `attendus.py` : la répartition de chaque preset de `forge.modele.config.PRESETS`, et les angles RoPE de la figure (positions 0 à 32, 4 paires d'une tête de 8, base de `ConfigModele`).
- `__main__.py` :
  - `uv run --extra cpu python -m transformer_pas_a_pas comparer --enregistrer sorties/comparaison.txt` : une ligne par pièce, avec son écart, et un verdict « identique à forge à 10⁻¹² près : oui » ;
  - `compter --preset tres_grand`.
- `parametres.ts` : `repartitionParametres(c: ConfigForge)`, sur les formes de `calculateur/ton-ia.ts`, vérifiée contre les attendus.
- `rope.ts` : `anglesRope(position, dimTete, base)`, pour l'affichage seulement. Le test compare aux attendus à 10⁻¹² près, puisque `Math.pow` n'est pas exact entre moteurs, et le dit en commentaire.

- [ ] **Étape 1 : écrire les tests qui échouent.**

```python
CONFIG = ConfigModele(dim=32, couches=2, tetes=4, longueur_contexte=16, taille_vocabulaire=50)

@pytest.mark.parametrize("piece", ["rmsnorm", "rope", "attention", "swiglu", "bloc", "modele"])
def test_piece_egale_a_forge(piece):
    assert ecarts(CONFIG)[piece] <= 1e-12

def test_masque_causal():
    # Changer le dernier jeton ne change aucune sortie des positions d'avant.
    ...

def test_poids_attention_somment_a_un_et_redonnent_la_sortie():
    ...

@pytest.mark.parametrize("nom", list(PRESETS))
def test_repartition(nom):
    r = repartition(PRESETS[nom]); assert sum(r.values()) == nombre_parametres(PRESETS[nom])
```

  `test_piece_egale_a_forge` est encadré par `# region: test-egalite` / `# fin: test-egalite`. Plus `test_attendus_a_jour` et `test_notebook.py`. Le notebook doit tourner sans carte, n'installer ni PyTorch ni forge, et dire sur quoi il a tourné.
- [ ] **Étape 2 : vérifier l'échec.** Commande : `cd projets/1.4-transformer; uv run --extra cpu pytest -q`.
- [ ] **Étape 3 : écrire le paquet, les attendus, la sortie et le notebook.**
  - **Le notebook**, pièce par pièce, avec un petit modèle aléatoire :
    1. plongement ;
    2. une tête d'attention ;
    3. le masque ;
    4. plusieurs têtes ;
    5. RoPE ;
    6. SwiGLU ;
    7. un bloc ;
    8. le modèle entier comparé à forge ;
    9. compter les paramètres de ton IA.
  - **L'exercice** : écrire la softmax à la main. « Défi réussi » si elle égale `torch.softmax` à 10⁻¹² près.
- [ ] **Étape 4 : vérifier que tout passe**, y compris `npx vitest run src/lib/partie-1`. Rejouer le notebook, et vérifier que `git status --short projets/forge` est vide.
- [ ] **Étape 5 : commit**, « Projet 1.4 : le transformer de ton IA refait pièce par pièce, égal à forge, avec son notebook ».

### Tâche 8 : le chapitre 1.4 « Le transformer, pièce par pièce », et sa parution

**Fichiers :**

- Créer : `site/src/components/chapitres/1-4/SchemaTransformer.astro`, `FigureRope.svelte`, `AtelierParametres.svelte`
- Créer : `site/src/lib/partie-1/paris-1-4.ts`, `paris-1-4.test.ts`
- Créer : `site/src/brouillons/chapitres/1-4.mdx` (puis `git mv`)
- Test : `site/e2e/chapitre-1-4.spec.ts`

**Interfaces :**

- Consomme : `AnimationAttention` et `paris-attention.ts` (`choixRegardDeIl`, `choixMasque`) du plan 3, sans les changer ; `parametres.ts`, `rope.ts` et `PRESETS_FORGE`.
- `paris-1-4.ts` :
  - `choixRopeRapide()` : « Quelle aiguille tourne le plus vite quand le jeton avance ? ». Choix : la paire 1, la paire 4, « toutes au même pas ». Le juste se calcule avec `anglesRope`.
  - `choixOuSontLesParametres(preset = 'tres_grand')` : plongement, attention ou MLP. Le juste est la plus grande part de `repartitionParametres`.
- `SchemaTransformer.astro` : un SVG dessiné à la main.
  - On y voit : jetons, plongement, « × {couches} blocs » (attention, MLP, avec normes et résidus), norme finale, logits.
  - Les nombres viennent de `PRESETS_FORGE.tres_grand`. Le schéma est accessible : `<title>`, `<desc>`, et une liste équivalente en texte.
- `FigureRope.svelte` : `NombreManipulable` position, de 0 à 32 ; quatre cadrans dont l'aiguille tourne de l'angle de sa paire. Sous `prefers-reduced-motion`, l'aiguille se pose sans glisser.
- `AtelierParametres.svelte` : une phrase à régler : « Avec [dim] nombres par jeton, [couches] blocs et [têtes] têtes, ton IA aurait {N} paramètres : … ».
  - Le tableau de la répartition, et les cinq tailles de forge en repères.
  - Les têtes doivent diviser `dim` : on ne propose que les diviseurs.

| Étape | Titre | Contenu imposé |
| --- | --- | --- |
| 1 | Le plan d'ensemble | `SchemaTransformer`, puis l'ouverture : la taille de ton IA. Vaswani et al. (2017). |
| 2 | Des jetons aux vecteurs | Le plongement, les poids liés : `CodeExplique` régions `plongement` et `modele`. |
| 3 | L'attention | `AnimationAttention` (l'exemple du forgeron, dit comme tel, avec sa mise en garde), paris `regard` et `masque`. |
| 4 | Plusieurs têtes | `CodeExplique` région `attention`. |
| 5 | Les positions | Pari `rope`, puis `FigureRope`. RoPE (Su et al., 2021). |
| 6 | Le MLP | SwiGLU (`CodeExplique symbole="MLP.forward"` de forge), et ce que dit le résumé de Shazeer (2020). |
| 7 | Le bloc | Normes et résidus (`CodeExplique symbole="Bloc.forward"`), RMSNorm (Zhang et Sennrich, 2019). |
| 8 | L'atelier des paramètres | Pari `parametres`, puis `AtelierParametres` sous `Verrou`. |
| 9 | Égal à forge | `CodeExplique` région `test-egalite`, puis `SortieCommande` de `sorties/comparaison.txt`. |
| 10 | Chez un grand labo | `EncadreLabo` : Llama 3 405B contre ton IA (couches, dim, têtes, têtes de clés et valeurs, contexte, vocabulaire), d'après `MODELES_PUBLICS`. |
| 11 | Le projet | `RecupererProjet projet="1.4-transformer"`, « À suivre » vers 1.5. |

**Acquis :** `attention`, `masque`, `rope`, `residus`, `parametres`, plus l'atelier, et le récapitulatif suit leur nombre.

**Défi :** trouver dans l'atelier une taille sous 100 millions de paramètres où le MLP pèse plus que le plongement.

- [ ] **Étape 1 : tests qui échouent** :
  - `paris-1-4.test.ts`, un seul juste par pari ;
  - `e2e/chapitre-1-4.spec.ts`, comme en 1.1, plus : chaque `CodeExplique symbole` montre le code actuel de forge ;
  - l'atelier, où les têtes non diviseurs sont impossibles et où le nombre pour `tres_grand` est 433 573 120, lu dans `nombreParametres` et non tapé ;
  - la figure, sans mouvement sous `reduced-motion`.
- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire.**
- [ ] **Étape 4 : tout vérifier.**
- [ ] **Étape 5 : captures et relecture.**
- [ ] **Étape 6 : commit**, « Chapitre 1.4 : le transformer pièce par pièce, avec RoPE et l'atelier des paramètres (brouillon) ».
- [ ] **Étape 7 : parution** (contrôleur) : `/forge-ia/partie-1/1-4/` répond 200.

### Tâche 9 : le glossaire, l'annuaire des données et la page du calculateur

**Fichiers :**

- Créer : `site/src/lib/annexes/glossaire.ts`, `glossaire.test.ts`, `site/src/lib/annexes/annuaire.ts`, `annuaire.test.ts`
- Créer : `site/src/pages/annexes/glossaire.astro`, `annuaire.astro`, `calculateur.astro`
- Modifier : `site/src/lib/parcours.ts` (`Annexe` gagne `href?: string`), `parcours.test.ts`, `site/src/pages/index.astro` (lien quand `href`), et la barre du site si elle liste les annexes
- Test : `site/e2e/annexes.spec.ts`, `site/e2e/navigation.spec.ts` (liens des annexes)

D'abord, lire le ledger : si l'utilisateur a répondu à la maquette (tâche 2), ses retours passent avant tout le reste. Les pages suivent la maquette `docs/maquettes/annexes.html`, corrigée de ses retours.

**Interfaces :**

- `glossaire.ts` :
  - `interface Terme { id: string; terme: string; definition: string; chapitre: string; voirAussi?: string[] }`, et `GLOSSAIRE: readonly Terme[]` ;
  - au moins 40 termes, de la Partie 0 et de 1.1 à 1.6, chacun relu dans son chapitre (la définition ne le contredit pas) ;
  - les termes de 1.5 et 1.6 entrent ici, et leur lien dit « à venir » tant que le chapitre n'a pas paru (par `chapitresParus()`).
- `annuaire.ts` :
  - `interface Fiche { id; nom; groupe: 'francais' | 'code' | 'evaluation'; description; url; taille: string | null; licence: { nom: string; url: string } | null; acces: 'libre' | 'conditions' | 'accord'; tonIA: string | null /* chapitre */; releveLe: string; source: string }` ;
  - les fiches de la recherche de ce plan, et rien d'autre : les trois sources de ton IA, `common_corpus`, `Lucie-Training-Dataset`, `croissant_dataset`, `the-stack-v2`, `stack-edu`, `OSCAR-2301`, `CulturaX`, et, pour l'évaluation, `french_bench_hellaswag`, `french_bench_arc_challenge` et `MMMLU`.
- `calculateur.astro` : le composant `Calculateur` (plan 3) avec son chapeau. La page d'essai `essais/calculateur.mdx` reste, pour les parcours du plan 3.
- `ANNEXES` : `href` pour le glossaire, l'annuaire et le calculateur ; « Matériel » reste sans lien, « à venir ».

- [ ] **Étape 1 : tests qui échouent.**

```ts
// glossaire.test.ts
expect(new Set(GLOSSAIRE.map((t) => t.id)).size).toBe(GLOSSAIRE.length);
const fr = new Intl.Collator('fr'); expect([...GLOSSAIRE].sort((a, b) => fr.compare(a.terme, b.terme))).toEqual(GLOSSAIRE);
for (const t of GLOSSAIRE) {
  expect(NUMEROS_DU_PARCOURS).toContain(t.chapitre);
  for (const v of t.voirAussi ?? []) expect(GLOSSAIRE.some((u) => u.id === v)).toBe(true);
  expect([...t.definition].length).toBeLessThanOrEqual(300);
}
// annuaire.test.ts : chaque fiche a une url https, un releveLe AAAA-MM-JJ et une source ;
// chaque dépôt cité dans projets/forge/forge/donnees/sources.py et evaluation/qcm.py (texte lu,
// sans import) a sa fiche, avec tonIA renseigné ; une fiche sans licence dit « non indiquée ».
```

  `e2e/annexes.spec.ts` (ordinateur et mobile) vérifie :
  - les trois pages répondent 200, avec zéro violation axe et aucun débordement à 390 px ;
  - les ancres `#<id>` du glossaire existent, et le filtre réduit la liste, avec « Aucun terme ne contient « … » » quand rien ne reste ;
  - les liens des chapitres parus mènent à leur page, et ceux des autres disent « à venir » ;
  - la recherche du site trouve « perplexité » dans le glossaire ;
  - l'accueil mène aux trois annexes construites.
- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire les données et les pages.** Le glossaire est indexé par Pagefind ; le tableau de l'annuaire aussi, mais sans les colonnes de dates.
- [ ] **Étape 4 : tout vérifier.**
- [ ] **Étape 5 : captures et relecture**, face à la maquette.
- [ ] **Étape 6 : commit**, « Annexes : glossaire, annuaire des données et page du calculateur », puis poussée (contrôleur) : les trois adresses répondent 200.

### Tâche 10 : le projet 1.5 « pré-entraînement », avec « mini »

**Fichiers :**

- Créer : `projets/1.5-pre-entrainement/pyproject.toml`, `uv.lock`, `.python-version`, `README.md`
- Créer : `projets/1.5-pre-entrainement/pre_entrainement/__init__.py`, `journal.py`, `essai.py`, `__main__.py`
- Créer, écrits par le projet : `mesures/ton-ia-mini.json`, `sorties/essai-processeur.txt`, `mesures/essai-processeur.json`
- Test : `tests/test_journal.py`, `test_essai.py`, `test_ligne_de_commande.py`, `test_notebook.py`, `tests/journal-factice.jsonl`
- Créer : `notebooks/1.5-pre-entrainement.ipynb`
- Créer : `site/src/lib/partie-1/journal.ts`, `journal.test.ts`, `site/src/lib/partie-1/commandes.ts`, `commandes.test.ts`

**Interfaces :**

- `pyproject.toml` : comme 1.4.
- `journal.py`, régions `sessions` et `courbe` :
  - `lire(journal: Path) -> list[dict]`, par `forge.suivi.lire_journal` ;
  - `sessions(lignes) -> list[dict]` : une session par `debut` ou `reprise`, avec son premier et son dernier pas, ses secondes de calcul, et sa fin (`pause`, `fin`, ou `coupée` sans ligne de fin) ;
  - `courbe(lignes, points: int = 400) -> dict` : `pertes` en `[pas, moyenne]` par paquets (le même découpage que `site/src/lib/courbe.ts`, `taillePaquet` et `moyennesParPaquets`), `validations` en `[pas, perte]`, `hasard` = `ln(32768)` ;
  - `resume(lignes, config: ConfigEntrainement) -> dict` : `parametres`, `pas_total`, `pas_faits`, `jetons_vus`, `secondes_de_calcul` (la somme des sessions), `pauses`, `debit_moyen`, `perte_finale`, `validation_finale`, `premier_pas`, `dernier_pas` (dates ISO) ;
  - `python -m pre_entrainement courbe --journal <jsonl> --config <toml> --json mesures/<nom>.json` écrit `{"nom", "releve_le", "resume", "sessions", "courbe"}`.
- `essai.py`, régions `essai-donnees` et `essai-reprise` :
  - `preparer_essai(racine: Path, texte: str) -> Path` : un raccourci de la chaîne de 1.2, dit comme tel dans le chapitre.
    - Le texte est `projets/1.1-modele-de-langage/donnees/texte-du-site.txt`, encodé par le tokenizer figé, suivi de `<|fin_texte|>`.
    - Les 90 premiers % des jetons vont à l'entraînement, le reste à la validation. On ne passe pas par `est_validation` : sur quelques centaines de documents, 0,5 % pourrait n'en laisser aucun.
    - On écrit `train/fragment-00000.bin`, `val/fragment-00000.bin` (`uint16` petit-boutiste), `index.json` (`{"version": 1, "fichiers": {…}}`) et `.complet`. C'est le format qu'écrit `ecrire_corpus` dans `projets/forge/tests/test_entrainement.py`, lu avant d'écrire.
    - Test : le `ChargeurJetons` de forge lit ce dossier ;
  - `config_essai(appareil: str, pas: int = 60) -> ConfigEntrainement` :
    - `[preset]` : dim 64, 2 couches, 4 têtes, contexte 64 ;
    - lot de 1 024 jetons, micro-lot 16, `taux_max` 1e-3, échauffement 6, validation tous les 20 pas, `compiler = "non"` ;
  - `essai_pause_reprise(appareil: str, racine: Path) -> dict`. Il fait un entraînement d'un trait, puis un second arrêté à mi-chemin (`arreter_apres`) et repris (`reprendre=True`). Il renvoie les deux pertes finales, leur écart (0 attendu sur le processeur), les secondes et l'appareil ;
  - `python -m pre_entrainement essai --appareil cpu|cuda --enregistrer <txt> --json <json>`. Les fichiers sont `sorties/essai-processeur.*` et `mesures/essai-processeur.json` pour le processeur, `…-rtx-5070-ti.*` pour la carte. Une carte absente ou inutilisable donne le message de `carte_inutilisable`, adapté de 0.5, et le code 2.
- `journal.ts` :
  - `lireEntrainement(nom: 'ton-ia-mini' | 'ton-ia-1.5'): Entrainement | null`, avec `verifierEntrainement(valeur, fichier)` ;
  - `null` quand le fichier manque : la page pose alors `data-a-mesurer`.
- `commandes.ts` : `ENTRAINER_COURT`, la suite des commandes de la version courte (`donnees`, `encoder`, `entrainer`, `evaluer`, en `--extra gpu`), `PAUSE`, la phrase « Ctrl+C met en pause », et `REPRENDRE`. `commandes.test.ts` vérifie que chaque commande se lit telle quelle dans `projets/forge/README.md` ou `docs/mesures/ton-ia-mini.md`.

- [ ] **Étape 1 : écrire les tests qui échouent.**

```python
def test_sessions_et_pauses():
    l = lire(FACTICE)  # debut, 5 pas, pause, reprise, 5 pas, fin
    s = sessions(l); assert [x["fin"] for x in s] == ["pause", "fin"]
    r = resume(l, CONFIG_FACTICE); assert r["pauses"] == 1 and r["pas_faits"] == 10

def test_courbe_meme_decoupage_que_le_site():
    ...  # taille des paquets : celle de taillePaquet(nbPas, 600) recopiée dans le test, avec son origine

def test_reprise_exacte_sur_le_processeur(tmp_path):
    r = essai_pause_reprise("cpu", tmp_path)
    assert r["ecart"] == 0.0

def test_cuda_absente_message_francais(capsys):
    ...  # FORGE_APPAREIL forcé, torch.cuda.is_available simulé à False : code 2, pas de trace
```

  `test_reprise_exacte_sur_le_processeur` est encadré par `# region: test-reprise`. Plus `test_notebook.py` : sans carte, rien d'installé, et l'essai pause et reprise affiché.
- [ ] **Étape 2 : vérifier l'échec**, puis `git status --short projets/forge` : vide.
- [ ] **Étape 3 : écrire le paquet et le notebook.**
  - **Le notebook** :
    1. la perte au départ, ln V ;
    2. le planning du taux (`forge.entrainement.planning.taux`) ;
    3. un petit entraînement de 60 pas ;
    4. Ctrl+C, puis la reprise : même perte ;
    5. ce qu'il faut pour la version d'une heure (les commandes, et la carte).

    Sur Colab avec carte, l'essai prend la carte ; sans carte, le processeur. Il le dit.
  - **L'exercice** : retrouver dans le journal le pas de la pause.
- [ ] **Étape 4 : relever.** Dans le dossier temporaire :
  - `uv run --extra cpu python -m pre_entrainement essai --appareil cpu --enregistrer sorties/essai-processeur.txt --json mesures/essai-processeur.json` ;
  - `courbe --journal D:\forge-ia-donnees\entrainements\ton-ia-mini\journal.jsonl --config ..\forge\configs\mini.toml --json mesures/ton-ia-mini.json`.

  Les nombres du résumé de mini doivent concorder avec `docs/mesures/ton-ia-mini.md` (6 370 pas, 60 min 17 s de boucle). Un écart se dit dans le rapport, et ne se corrige pas dans le document.
- [ ] **Étape 5 : tout vérifier**, y compris `npx vitest run src/lib/partie-1`. Rejouer le notebook.
- [ ] **Étape 6 : commit**, « Projet 1.5 : courbes et sessions des journaux, essai de pause et de reprise exacte, avec la version d'une heure ».

### Tâche 11 : le chapitre 1.5 « Le pré-entraînement sur ton GPU », en brouillon

**Fichiers :**

- Créer : `site/src/components/chapitres/1-5/CourbeEntrainement.astro`, `TableauSessions.astro`
- Créer : `site/src/lib/partie-1/paris-1-5.ts`, `paris-1-5.test.ts`
- Créer : `site/src/brouillons/chapitres/1-5.mdx`
- Test : `site/e2e/chapitre-1-5.spec.ts`

**Interfaces :**

- Consomme : `journal.ts`, `commandes.ts`, `MiniModele` en préréglage `complet` et ses paris (`choixErreurDeDepart`, `choixTauxTropGrand`), `courbe.ts`, `SortieCommande`, `BlocCommande`, et les données du calculateur.
- `CourbeEntrainement.astro` : props `{ nom: 'ton-ia-mini' | 'ton-ia-1.5'; titre: string }`.
  - SVG dessiné à la main avec `courbe.ts` : entraînement en indigo, validation en points, hasard en tirets, pauses en traits fins verticaux.
  - Un tableau équivalent caché à l'écran mais lisible par les lecteurs d'écran.
  - Fichier absent : `<p class="a-mesurer" data-a-mesurer>`.
- `TableauSessions.astro` : une ligne par session (début, fin, pas, durée de calcul) ; sinon `data-a-mesurer`.
- `paris-1-5.ts` :
  - `choixPerteDepartTonIA()` : « Avant d'avoir rien appris, quelle perte a ton IA au premier pas ? », en trois tranches. Le juste vient du `premier_pas` réel de mini, et une garde vérifie qu'il est à moins de 0,2 de ln 32 768.
  - `choixReprise()` : « Après une pause, la perte du pas repris… » : « continue la courbe, au même nombre près » (juste si `ecart === 0` dans `essai-processeur.json`), « repart du hasard », « fait un saut puis rattrape ».

| Étape | Titre | Contenu imposé |
| --- | --- | --- |
| 1 | Ton IA naît | L'ouverture : un échantillon de mini au premier pas et un au dernier, lus dans son rapport (`projets/1.6-evaluation/mesures/evaluation-mini.json`, tâche 12 ; jusqu'à cette tâche, `data-a-mesurer`). |
| 2 | La perte au départ | Pari `depart`, ln V. |
| 3 | Le lot, le taux, le planning | `CodeExplique symbole="taux"` de `forge/entrainement/planning.py`. |
| 4 | L'atelier : un petit modèle apprend | `MiniModele` (`complet`), pari du taux trop grand, sous `Verrou`. La note dit « la même recette que ton IA, en N paramètres » (plan 3, choix 3), avec N lu dans le moteur du mini-modèle, jamais tapé. |
| 5 | AdamW et l'écrêtage | `CodeExplique symbole="_creer_optimiseur"`, et `_pas_d_optimisation` si ses lignes s'expliquent en moins de 30 lignes, sinon seulement une région de l'essai. |
| 6 | Pause et reprise | Pari `reprise`, puis ce qui est sauvegardé (spécification, section 8), `CodeExplique` région `test-reprise`, `SortieCommande` de `sorties/essai-processeur.txt`. Les commandes `PAUSE` et `REPRENDRE`. |
| 7 | La version d'une heure | `CourbeEntrainement nom="ton-ia-mini"`, son résumé, et `BlocCommande` de `ENTRAINER_COURT`. |
| 8 | Ton IA, la vraie | `CourbeEntrainement nom="ton-ia-1.5"`, `TableauSessions` et le résumé : « à mesurer » jusqu'à la tâche 16. Le texte dit déjà, sans chiffre, que l'entraînement s'est arrêté et repris quand le PC servait à autre chose. |
| 9 | Chez un grand labo | `EncadreLabo` : Llama 3.1 405B (30,84 millions d'heures de H100, jusqu'à 16 000 cartes, 54 jours avec 466 interruptions, 3,8 × 10²⁵ opérations), et le lien vers l'annexe du calculateur. |
| 10 | Le projet | `RecupererProjet projet="1.5-pre-entrainement"`, « À suivre » vers 1.6. |

**Acquis :** `depart`, `taux`, `atelier`, `reprise`, `courte`. La tâche 16 ajoute `principal`, gagné par le pari `duree` sur la durée réelle.

**Défi :** dans l'atelier, trouver le plus grand taux d'apprentissage dont l'erreur de validation finit encore sous celle du taux par défaut. Il est vérifié par les pertes de `MiniModele`.

- [ ] **Étape 1 : tests qui échouent.** `paris-1-5.test.ts`, puis `e2e/chapitre-1-5.spec.ts` (brouillon, avec `FORGE_ESSAIS=1`) :
  - la page répond 200 et la courbe de mini se dessine ;
  - **au moins un `[data-a-mesurer]`** dans l'étape 8 ;
  - les commandes de `BlocCommande` sont celles de `commandes.ts` ;
  - axe et 390 px.
- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire.**
- [ ] **Étape 4 : tout vérifier**, captures et relecture.
- [ ] **Étape 5 : commit**, « Chapitre 1.5 : le pré-entraînement, avec la version d'une heure (brouillon, ton IA à mesurer) ».

### Tâche 12 : le projet 1.6 « évaluation », avec « mini »

**Fichiers :**

- Créer : `projets/1.6-evaluation/pyproject.toml`, `uv.lock`, `.python-version`, `README.md`
- Créer : `projets/1.6-evaluation/evaluation_pas_a_pas/__init__.py`, `sauvegarde.py`, `pas_a_pas.py`, `resumer.py`, `qcm_exemples.py`, `regarder.py`, `__main__.py`
- Créer, écrits par le projet : `mesures/evaluation-mini.json`, `mesures/qcm-mini.json`
- Test : `tests/test_pas_a_pas.py`, `test_resumer.py`, `test_regarder.py`, `test_ligne_de_commande.py`, `test_notebook.py`
- Créer : `notebooks/1.6-evaluation.ipynb`
- Créer : `site/src/lib/partie-1/evaluation.ts`, `evaluation.test.ts`

**Interfaces :**

- `sauvegarde.py` : `charger_sauvegarde(chemin: Path, appareil: str = "cpu") -> tuple[Transformer, ConfigModele]`. Il passe par `forge.entrainement.sauvegarde.charger` et reconstruit le modèle comme le fait `forge.evaluation.rapport._lire_sauvegarde`. Un test compare sa perte à celle de forge sur un petit modèle sauvegardé dans le test.
- `pas_a_pas.py`, régions `perte`, `perplexite`, `bits`, `qcm` et `marge` :
  - `perte_a_la_main(logits, cibles) -> float`, égale à `F.cross_entropy` à 10⁻¹² près en float64 ;
  - `scores_a_la_main(modele, tokenizer, qcm: QCM) -> list[float]` : la log-vraisemblance de chaque fin, et sa version divisée par les octets. Elle est égale à `forge.evaluation.qcm.scores_qcm` ;
  - `marge_95(exactitude: float, n: int) -> float`, la formule de forge (`_marge_95`, lue dans le code, vérifiée par un test) ;
  - `verdict(exactitude, hasard, marge) -> Literal["au-dessus", "pas-different", "en-dessous"]`, la règle de `forge.evaluation.rapport.verdict`.
- `resumer.py` : `resumer(rapport_json: Path) -> dict` écrit `{"nom", "releve_le", "perte_val", "perplexite", "bits_par_octet", "qcm": {"hellaswag": {exactitude, normalisee, hasard, n, marge, verdict}, "arc": …}, "echantillons": [...]}`. Le chemin vient du rapport, et rien n'est recalculé.
- `qcm_exemples.py` : `exemples_mmmlu(n: int = 6, graine: int = 0) -> list[QCM]`, depuis `openai/MMMLU`, configuration `FR_FR`.
  - Le contexte est « Question : … \nRéponse : », et les choix sont les quatre réponses.
  - `noter_exemples(modele, tokenizer, qcms) -> dict` : par question, les scores normalisés, le choix préféré et la bonne réponse, plus l'adresse et la licence du jeu.
- `regarder.py`, région `cartes` :
  - `cartes_attention(modele: Transformer, ids: Tensor, couche: int) -> Tensor[tetes, n, n]`. Il prend l'entrée normée de la couche par un crochet sur `norme_attention`, puis applique `proj_qkv`, `rope_cos_sin`, `appliquer_rope`, la mise à l'échelle et le masque, et la softmax ;
  - `suivants(modele, tokenizer, phrase: str, k: int = 10) -> list[tuple[str, float]]`.

  Ces deux fonctions servent à la tâche 15 ; leurs tests tournent dès maintenant sur un petit modèle aléatoire.
- `__main__.py` :
  - `resumer --rapport <json> --json mesures/evaluation-<nom>.json` ;
  - `qcm-exemples`, `cartes --phrase … --json …` et `suivants --phrase … --json …`.

  Les trois dernières prennent `--sauvegarde <pt>` (une sauvegarde de forge, ici mini) ; la tâche 15 leur ajoute `--modele <dossier de la Release>`, qui passe par `charger_ton_ia`. Elles prennent aussi `--appareil`, et `--json` pour leur sortie. Une carte inutilisable donne le message de 1.5.
- `evaluation.ts` : `lireEvaluation(nom)`, `lireQcm(nom)` (ou `null`), `marge95` (même formule, une racine carrée : exacte) et `verdictQcm`, vérifiés contre les attendus du projet (`tests/attendus.json` : une grille d'exactitudes et de `n`).

- [ ] **Étape 1 : écrire les tests qui échouent.**

```python
def test_perte_a_la_main():
    logits, cibles = torch.randn(5, 7, dtype=torch.float64), torch.tensor([0, 3, 6, 1, 2])
    assert abs(perte_a_la_main(logits, cibles) - F.cross_entropy(logits, cibles).item()) <= 1e-12

def test_scores_a_la_main_egaux_a_forge(): ...
def test_cartes_redonnent_la_sortie_de_l_attention():
    # cartes @ v (puis proj_sortie) == bloc.attention(norme(x)) de forge, en float64, à 1e-12 près
    ...
def test_resumer_lit_le_rapport(tmp_path): ...  # rapport factice au format de forge (rapport.py, VERSION_DU_RAPPORT = 1)
```

  `test_cartes_redonnent_la_sortie_de_l_attention` est encadré par `# region: test-cartes`. Plus `test_ligne_de_commande.py` (`--appareil cuda` sans carte utilisable : message français, code 2, pas de trace) et `test_notebook.py`.
- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire le paquet et le notebook.**
  - **Le notebook** :
    1. la perte et la perplexité à la main ;
    2. les bits par octet ;
    3. un QCM noté sans que le modèle écrive un mot ;
    4. la marge et le verdict ;
    5. lire des échantillons.

    Le modèle est celui de l'essai de 1.5, entraîné dans le notebook (`projets/1.5-pre-entrainement` est ajouté à `sys.path`). La tâche 16 lui ajoute ton-ia-1.5.
  - Ajouter `safetensors==0.8.0` à `colab-sans-carte.txt` seulement à la tâche 16, quand le notebook en a besoin.
- [ ] **Étape 4 : relever**, sur le processeur :
  - `resumer --rapport D:\forge-ia-donnees\entrainements\ton-ia-mini\evaluation\rapport.json --json mesures/evaluation-mini.json` ;
  - `qcm-exemples --sauvegarde D:\forge-ia-donnees\entrainements\ton-ia-mini\sauvegardes\etape-0006370.pt --appareil cpu --json mesures/qcm-mini.json` (MMMLU lu en flux).

  Les chiffres doivent concorder avec `docs/mesures/ton-ia-mini.md` (perplexité 30,8, 1,133 bit par octet, HellaSwag 27,2 %, ARC 23,6 %). Vérifier aussi la licence MIT de MMMLU sur sa page, et la noter dans le JSON.
- [ ] **Étape 5 : tout vérifier**, rejouer le notebook, et vérifier que `git status --short projets/forge` est vide.
- [ ] **Étape 6 : commit**, « Projet 1.6 : l'évaluation pas à pas, le résumé de mini, des QCM MMMLU notés, et les cartes d'attention ».

### Tâche 13 : le chapitre 1.6 « Évaluer son modèle », en brouillon

**Fichiers :**

- Créer : `site/src/components/chapitres/1-6/AtelierQcm.svelte`, `TableauEvaluation.astro`
- Créer : `site/src/lib/partie-1/paris-1-6.ts`, `paris-1-6.test.ts`
- Créer : `site/src/brouillons/chapitres/1-6.mdx`
- Modifier : `site/src/brouillons/chapitres/1-5.mdx` (l'ouverture lit maintenant `evaluation-mini.json`)
- Test : `site/e2e/chapitre-1-6.spec.ts`, `chapitre-1-5.spec.ts` (ouverture sans `data-a-mesurer`)

**Interfaces :**

- `paris-1-6.ts` :
  - `choixPerplexiteHasard()` : « Un modèle qui tire chaque jeton au hasard parmi les 32 768 a une perplexité de… ». Le juste est `VOCABULAIRE_FORGE`, avec 2, 100 et 32 768 comme choix.
  - `choixPrefere(i)` : par question de `qcm-mini.json`, la fin que ton IA (mini) préfère.
  - `choixAuDessusDuHasard()` : pour HellaSwag de mini, « au-dessus du hasard », « pas différent » ou « en dessous ». Le juste se calcule par `verdictQcm`.
- `AtelierQcm.svelte` : une question à la fois.
  - Le lecteur parie sur la fin que ton IA préfère, avant de voir les barres.
  - Puis il voit les scores normalisés en barres, la préférence de ton IA, et la bonne réponse, menthe ou corail selon que ton IA a juste ou non.
  - « Question suivante » ; à la fin, un compte « ton IA : x sur 6, le hasard : 1,5 en moyenne », avec le compte calculé.
  - Les textes des questions portent `data-pagefind-ignore`.
- `TableauEvaluation.astro` : props `{ nom }`. Il montre la perte, la perplexité, les bits par octet, et les QCM avec leur marge et leur verdict ; si le fichier manque, `data-a-mesurer`.

| Étape | Titre | Contenu imposé |
| --- | --- | --- |
| 1 | Ce que sait ton IA | L'ouverture : la perplexité de mini, et ce qu'elle veut dire. |
| 2 | La perte sur un texte jamais lu | Retour sur 1.1 : `CodeExplique` régions `perte` et `perplexite`. Pari `hasard`. |
| 3 | Bits par octet | Comparer des modèles qui découpent différemment (renvoi à 1.3). |
| 4 | Répondre sans parler | Le QCM par vraisemblance, `CodeExplique` région `qcm`, puis `AtelierQcm` sous `Verrou`. |
| 5 | Le hasard et la marge | Pari `marge`, `CodeExplique` région `marge`, puis `TableauEvaluation nom="mini"`. |
| 6 | Lire les échantillons | Les échantillons de mini, et ce qu'ils montrent (les phrases sont gardées par `exiger` sur des faits du rapport : un texte de code est présent, etc.). |
| 7 | Ce que les chiffres ne disent pas | FrenchBench, traduit automatiquement, sans licence indiquée ; la contamination (Llama 3, 8-grammes) ; MMMLU, traduit par des humains. |
| 8 | Ton IA, la vraie | `TableauEvaluation nom="1.5"` : « à mesurer » jusqu'à la tâche 16. |
| 9 | Chez un grand labo | `EncadreLabo` : les bancs de Llama 3 (catégories du tableau 8, intervalles à 95 %), et Llama 3.1 405B pré-entraîné (MMLU 85,2, ARC-Challenge 96,1). |
| 10 | Le projet | `RecupererProjet projet="1.6-evaluation"`. « À suivre » vers 1.7, « à venir » : ton IA apprendra à converser. |

**Acquis :** `hasard`, `bits`, `qcm`, `marge`, `limites` ; le récapitulatif suit.

**Défi :** trouver dans l'atelier une question où ton IA préfère la bonne réponse, et dire, d'après les scores, si elle aurait pu tomber juste par hasard. L'atelier compte les questions trouvées.

- [ ] **Étape 1 : tests qui échouent** : `paris-1-6.test.ts`, puis `e2e/chapitre-1-6.spec.ts`, qui vérifie :
  - l'atelier sur les 6 questions et le compte final calculé ;
  - le pari avant les barres, et les barres floues tant qu'on n'a pas parié ;
  - au moins un `[data-a-mesurer]` à l'étape 8 ;
  - axe et 390 px.
- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire.**
- [ ] **Étape 4 : tout vérifier**, captures et relecture.
- [ ] **Étape 5 : commit**, « Chapitre 1.6 : évaluer son modèle, avec l'atelier des QCM (brouillon, ton IA à mesurer) ».

### Tâche 14 : bilan sans la carte

**Fichiers :**

- Modifier : `projets/1.*/README.md` (versions finales), `README.md` (liste des projets)

- [ ] **Étape 1 : tout vérifier**, en notant les durées :
  - pour chaque `projets/1.[12456]-*` : `uv run pytest -q`, avec `--extra cpu` pour 1.4 à 1.6 ;
  - le site entier, comme en tâche 1 ;
  - `npm run build` sans essais, puis les garde-fous de `site.yml` rejoués à la main : aucun dossier `dist/partie-1/1-5` ni `1-6`, et aucun prénom hors du Worker ;
  - `executer_notebooks.py` dans `.colab`, sur tous les notebooks.

  Si le job `tests` de `python.yml` approche ses 20 minutes, porter `timeout-minutes` à 30, et le dire.
- [ ] **Étape 2 : finir les README.** Pour chaque projet :
  - ce qu'il fait, et le chapitre qu'il accompagne ;
  - les commandes PowerShell (et Linux ou Mac quand elles diffèrent) ;
  - ce qu'il prend à forge ;
  - les régions montrées par le chapitre ;
  - les fichiers de `mesures/` et `sorties/`, d'où ils viennent et quand ils ont été relevés.

  Le README racine liste les cinq projets.
- [ ] **Étape 3 : relire 1.1 à 1.6 d'un bout à l'autre**, comme un débutant qui sort de la Partie 0 :
  - chaque terme est expliqué avant d'être utilisé, et il est dans le glossaire ;
  - chaque chapitre annonce le suivant ;
  - aucune affirmation n'est datée sans source.

  Corriger dans la tâche concernée, par un commit séparé. Un chapitre déjà paru se corrige puis se repousse.
- [ ] **Étape 4 : commit**, « Partie 1 : README des projets et bilan avant la carte ». Puis le contrôleur envoie à l'utilisateur un court message, sans question : ce qui a paru (adresses), ce qui attend la fin de l'entraînement, et l'adresse des brouillons s'il veut les voir avec `npm run build:essais`.

### Tâche 15 : la porte, la carte et les fichiers de ton IA

**Conditions, toutes au ledger :**

- l'entraînement principal est fini : la ligne `fin` est dans son journal, et le chien de garde est arrêté ;
- `Task 14: complete` dans le ledger du plan 2 : rapport final écrit, Release `ton-ia-1.5` publiée avec l'accord de l'utilisateur ;
- les tâches 1 à 14 de ce plan sont complètes ;
- l'utilisateur a dit « go » (il ne joue pas).

Aucune autre question.

**Fichiers :**

- Créer : `projets/1.6-evaluation/evaluation_pas_a_pas/ton_ia.py` (`charger_ton_ia`), `tests/test_ton_ia.py`
- Créer, écrits par les projets :
  - `projets/1.5-pre-entrainement/mesures/ton-ia-1.5.json`, `sorties/essai-rtx-5070-ti.txt`, `mesures/essai-rtx-5070-ti.json` ;
  - `projets/1.6-evaluation/mesures/evaluation-1.5.json`, `mesures/qcm-1.5.json`, `sorties/cartes-ton-ia.json`, `sorties/ton-ia-suivants.json`.

**Interfaces :**

- `charger_ton_ia(dossier: Path, appareil: str = "cpu") -> tuple[Transformer, TokenizerOctets]` lit les fichiers de la Release :
  - `config.json`, pour `ConfigModele(**config)` ;
  - les poids `ton-ia-1.5.safetensors`, avec les poids liés : si `sortie.weight` manque, il reprend `plongement.weight` ;
  - `tokenizer-ton-ia-v1.json`, dont l'empreinte SHA-256 doit valoir `3001e7ab…21ba`, celle de la ressource figée.

  Le format exact est celui que la tâche 14 du plan 2 a écrit : le lire avant d'écrire la fonction. Si le format diffère de ce qui est dit ici, la fonction s'adapte, jamais la Release. Test : sur un petit modèle exporté dans le test, au même format, les logits sont égaux à ceux du modèle d'origine.

- [ ] **Étape 1 : récupérer la Release**, avec `gh release download ton-ia-1.5 --dir "$env:FORGE_DONNEES\cache\ton-ia-1.5"`. Vérifier que les fichiers sont ceux de la tâche 14, puis écrire `charger_ton_ia` et son test.
- [ ] **Étape 2 : les fichiers de ton IA, sur le processeur.** Les commandes de 1.6 prennent `--modele "$env:FORGE_DONNEES\cache\ton-ia-1.5"`.
  - `pre_entrainement courbe --journal D:\forge-ia-donnees\entrainements\ton-ia\journal.jsonl --config ..\forge\configs\principal.toml --json mesures/ton-ia-1.5.json`.
  - `evaluation_pas_a_pas resumer --rapport <rapport.json de la tâche 14> --json mesures/evaluation-1.5.json`.
  - `cartes`, avec la phrase « Le forgeron chauffe le fer puis il le tord. » découpée par le tokenizer de ton IA. La couche et les deux têtes montrées sont choisies et justifiées dans le JSON : celle qui regarde le plus le jeton d'avant, et celle qui regarde le plus loin.
  - `suivants`, avec « Le forgeron frappe le ».
  - `qcm-exemples`, avec les 6 mêmes questions qu'en tâche 12.
- [ ] **Étape 3 : passer sur la carte**, entraînement fini, carte libre (`nvidia-smi` sous 10 %) :
  - `uv sync --extra gpu --offline` dans 1.4, 1.5 et 1.6. Si uv réclame une roue absente du cache, s'arrêter et le dire ;
  - `uv run --extra gpu pytest -q -rs` dans chacun : aucun test `gpu` sauté, et les notebooks 1.5 et 1.6 ont tourné sur la carte (ils le disent) ;
  - `uv run --extra gpu python -m pre_entrainement essai --appareil cuda --enregistrer sorties/essai-rtx-5070-ti.txt --json mesures/essai-rtx-5070-ti.json`. Sur la carte, l'écart de reprise peut ne pas être nul : le chiffre est publié tel qu'il est, et la phrase du chapitre le dit (plan 2, tâche 7 : pas de noyaux déterministes sur la carte) ;
  - `qcm-exemples` sur la carte, pour vérifier que le choix préféré de chaque question est le même qu'au processeur. Sinon, le dire dans le rapport.
- [ ] **Étape 4 : tout vérifier**, comme en tâche 14, étape 1. Pytest repasse en `--extra cpu`, comme l'intégration continue. Vérifier que `git status --short projets/forge` est vide.
- [ ] **Étape 5 : commit**, « Ton IA 1.5 dans la Partie 1 : courbe, sessions, évaluation, cartes d'attention et passages sur la RTX 5070 Ti ».

### Tâche 16 : les chapitres complétés, la parution de 1.5 et 1.6, et le compte rendu

**Fichiers :**

- Créer : `site/src/components/chapitres/1-4/CartesTonIA.svelte`
- Modifier : `site/src/content/chapitres/1-1.mdx` (une étape « Ton IA prédit la suite »), `1-4.mdx` (une étape « Les vraies cartes de ton IA »), `site/src/brouillons/chapitres/1-5.mdx`, `1-6.mdx`
- Modifier : `site/src/lib/partie-1/paris-1-5.ts` (pari `duree`), `fichiers.ts`, `site/src/lib/annexes/annuaire.ts` (`tonIA` de MMMLU si besoin)
- Modifier : `notebooks/1.5-pre-entrainement.ipynb`, `1.6-evaluation.ipynb` (une section ton-ia-1.5 : téléchargement de la Release, quelques générations sur le processeur ; avec `FORGE_IA_MODELE`, le dossier déjà téléchargé est pris sans rien télécharger), `outils/colab-sans-carte.txt` (`safetensors==0.8.0`)
- Modifier : `.github/workflows/python.yml`, job `notebooks-colab` : `gh release download ton-ia-1.5` dans un cache (`actions/cache` sur l'étiquette), puis `FORGE_IA_MODELE`
- Test : `site/e2e/chapitre-1-1.spec.ts`, `-1-4`, `-1-5`, `-1-6` (zéro `[data-a-mesurer]`, nouveaux paris et étapes)

**Interfaces :**

- `CartesTonIA.svelte` : props `{ cartes: FichierCartes }` (type exporté par `site/src/lib/partie-1/evaluation.ts`, avec `lireCartes()` et sa vérification), lues dans `projets/1.6-evaluation/sorties/cartes-ton-ia.json`.
  - Le choix de la tête parmi les têtes du fichier ; la carte dans un vrai `<table>`, en teintes de lavande à l'indigo ; la légende dit d'où viennent les nombres (« calculés sur le processeur par `cartes_attention`, depuis les poids publiés de ton-ia-1.5 »).
  - Elle ne refait aucun calcul.
- `choixDureeReelle()` (`paris-1-5.ts`) : « Combien de temps de calcul a pris ton IA, pauses non comptées ? », en trois tranches calculées depuis `resume.secondes_de_calcul`.

- [ ] **Étape 1 : tests d'abord.**
  - Les quatre parcours attendent zéro `[data-a-mesurer]`, et les nouvelles étapes de 1.1 et 1.4 (suivants et cartes affichés depuis les fichiers).
  - Celui de 1.5 attend le pari `duree` et le récapitulatif complet.
  - Celui de 1.6 attend le tableau de ton-ia-1.5 et l'atelier sur les questions de `qcm-1.5.json`.
- [ ] **Étape 2 : écrire.** Chaque phrase sur ton-ia-1.5 est qualitative et gardée par `exiger` sur les fichiers ; les nombres sont dans les tableaux et les composants. Les échantillons de ton-ia-1.5 se montrent tels quels, sans les choisir, avec ce qu'ils disent de ses limites (spécification, sections 3 et 9). Le relecteur vérifie chaque phrase contre les fichiers.
- [ ] **Étape 3 : notebooks.** Ajouter la section ton-ia-1.5, les rejouer dans `.colab` avec `FORGE_IA_MODELE`, puis sur la carte (`test_notebook.py` avec `--extra gpu`).
- [ ] **Étape 4 : tout vérifier**, comme en tâche 14, étape 1.
- [ ] **Étape 5 : commit**, « Partie 1 : ton IA 1.5 dans les chapitres 1.1, 1.4, 1.5 et 1.6 ».
- [ ] **Étape 6 : parution de 1.5 et 1.6** (contrôleur), comme en tâche 4 : `git mv` des deux brouillons, `npm run build`, garde-fous, commit « Parution des chapitres 1.5 et 1.6 », poussée. Puis vérifier :
  - les workflows Site et Python sont verts, `notebooks-colab` compris ;
  - les six adresses `/forge-ia/partie-1/1-1/` à `1-6/` et les trois annexes répondent 200 ;
  - la recherche trouve « perplexité » dans 1.1, 1.6 et le glossaire.
- [ ] **Étape 7 : jalons de la mémoire partagée**, si elle répond ; sinon, le dire dans le compte rendu, sans lire de clé.
  - Jalon : « Projet forge-ia (La Forge IA) : vague 1 finie. Partie 1, chapitres 1.1 à 1.6 publiés le JJ/MM/AAAA, avec leurs projets (projets/1.1-modele-de-langage à 1.6-evaluation) et notebooks ; glossaire, annuaire des données et calculateur en annexes. »
  - Plus les jalons en attente du ledger du plan 4, s'ils ne sont toujours pas écrits.
- [ ] **Étape 8 : compte rendu à l'utilisateur.**
  - Les adresses publiées.
  - Les chiffres relevés : essai de reprise sur le processeur et sur la carte, durée de calcul et nombre de pauses de ton IA, son évaluation.
  - Les écarts trouvés en route (par exemple `docs/donnees.md`).
  - La fin de la vague 1 : la spécification demande sa validation par l'utilisateur. La lui demander avec AskUserQuestion, puisque l'autonomie ne valait que pour le plan 5.

---

## Décisions de l'utilisateur (08/11/2026)

- **Lancer le plan 5 pendant l'entraînement :** « Ont peut bien lancer le plan 5 et les autre qui reste en attendant l'entrenement ou c'est risquer ? ». Réponse : sans risque pour 1.1, 1.2, 1.4 et les annexes ; 1.5 et 1.6 attendent ton IA. D'où l'ordre des tâches.
- **Autonomie :** « Seul, comme le plan 4 ». D'où le choix 1.
- **La carte :** « Garder pour après ». D'où le choix 2 et la tâche 15.
- **Go et stop :** « Quand je dit stop tu narrete que lentrainement, tu laisse lagent finir et tu nen relance pas. S'il lagent na pas fini quand tu dit go tu relance lentrenement et en continue pour les agent. ». D'où la contrainte globale « Go et stop ».
