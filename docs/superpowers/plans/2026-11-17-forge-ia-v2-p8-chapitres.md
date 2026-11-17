# La Forge IA, vague 2, plan 8 : les chapitres 1.7 à 1.10

> **Pour les agents qui exécutent ce plan :** SOUS-SKILL REQUIS : utiliser superpowers:subagent-driven-development (recommandé) ou superpowers:executing-plans pour réaliser ce plan tâche par tâche. Les étapes utilisent des cases à cocher (`- [ ]`).

**But :** écrire et faire paraître les quatre chapitres de « Le rendre utile » : 1.7 « Apprendre à converser », 1.8 « L'aligner : préférences et récompenses », 1.9 « Le faire raisonner » et 1.10 « Le faire coder ». Chacun a son projet testé, son notebook qui tourne sur Colab sans carte, ses ateliers et ses paris, et les vrais chiffres de ton IA. S'y ajoutent le glossaire et l'annuaire complétés.

**Architecture :**

- **Un projet par chapitre**, sur le patron de 1.5 et 1.6 : `projets/1.7-conversation`, `1.8-alignement`, `1.9-raisonnement`, `1.10-code`. Chacun dépend par chemin de `forge` et de `pre-entrainement` (le projet 1.5, pour les courbes et les sessions des journaux), sans jamais les modifier.
- **Les notebooks** n'installent rien. Ils prennent forge par `sys.path`, téléchargent la Release de leur étape par `forge.publication.telecharger_publication`, et tournent sur le processeur.
- **Des jumeaux TypeScript** (`site/src/lib/partie-1/`) refont dans le navigateur ce que les ateliers calculent. Le Python écrit les attendus, et Vitest vérifie l'égalité exacte (tolérance annoncée seulement pour la perte DPO, qui passe par `exp` et `log`).
- **Brouillons, `data-a-mesurer`, `exiger` et parution par `git mv`**, exactement comme au plan 5. Un chapitre s'écrit en brouillon pendant que le plan 7 entraîne, puis paraît dès que sa Release et ses fichiers de mesures existent, sans attendre les autres.

**Pile technique :** celle du plan 5 (Astro, Svelte 5, TypeScript, Vitest, Playwright avec `@axe-core/playwright` ; Python 3.12, uv, pytest, nbclient ; PyTorch 2.15.0, roues `cpu`, et `cu132` pour les passages sur la carte). Aucune dépendance npm nouvelle. Python : aucune dépendance nouvelle hors `forge-ia` et `pre-entrainement` (chemins).

**Spécification :** `docs/superpowers/specs/2026-11-02-forge-ia-design.md`, surtout les sections 3 (anti-objectifs), 4, 5 (gabarit d'un chapitre), 6 (allure), 7 (cohérence des moteurs), 8 (code, notebooks), 9 (honnêteté) et 12. Plan du moteur : `docs/superpowers/plans/2026-11-17-forge-ia-v2-p7-moteur.md`, dont ce plan utilise les interfaces sous leurs noms exacts.

## Dépendances avec le plan 7

| Tâche de ce plan | Demande, au plan 7 |
| --- | --- |
| 1 (socle) | tâche 1 (`forge.publication`) |
| 2 et 3 (1.7) | tâches 1 à 11 |
| 4 et 5 (1.8) | tâches 13 et 14 |
| 6 et 7 (1.9) | tâches 9, 11 et 16 |
| 8 et 9 (1.10) | tâches 18, 19 et 21 |
| 10 (annexes) | tâche 20 (le traducteur et sa licence) |
| 11 à 14 (parutions) | Releases `ton-ia-1.7` (tâche 12), `ton-ia-1.8` (15), `ton-ia-1.9` (17), `ton-ia-1.10` et `donnees-ton-ia-2` (20 et 22) |

Les tâches 2 à 10 ne prennent pas la carte : elles tournent pendant les entraînements du plan 7.

## Recherche faite avant ce plan (le 17/11/2026)

Les sources sont les trois recherches du 17/11/2026 (`docs/superpowers/recherche/2026-11-17-vague-2-*.md`) ; le plan 7 en donne le résumé. Ce que les chapitres impriment en plus vient de « échelle », partie B, et de ses étiquettes : **publié**, **dérivé**, **tiers**, **non trouvé**. La recherche demande de **revérifier chaque chiffre à la source primaire** avant de le recopier : chaque tâche de chapitre le fait, et le note dans `sources-1-N.ts` (adresse, endroit, date de lecture).

- **1.7** (B1) : InstructGPT, environ 13 000 invites de SFT, 4,9 pétaflops/s-jours contre 3 640 pour GPT-3 ; Llama 2, 27 540 annotations ; Tülu 3, 939 344 invites, 8 B en 32 cartes pendant 6 h ; SmolLM3, 1,8 Md de jetons, 4 époques. Le gain attendu est sur des consignes simples (SmolLM2-135M : IFEval 17,2 puis 29,9), pas sur les connaissances (nanochat d20, ARC-Challenge 28,75 puis 28,07).
- **1.8** (B2) : InstructGPT, environ 33 000 invites pour le modèle de récompense et environ 40 annotateurs ; Llama 2, 1 418 091 comparaisons ; Qwen2.5, environ 150 000 paires, une époque ; Tülu 3, de 60,6 à 64,7 en moyenne (8 B). Le 60,1 du tableau 9 et les deux comptes de paires de Tülu 3 ne s'accordent pas : **ne pas imprimer** sans relecture. Aucune mesure isolée de DPO sous 1 Md n'a été trouvée.
- **1.9** (B3, A1, A5) : Tülu 3 RLVR, 29 946 invites, 8 B en 65 h sur 8 cartes ; DeepSeek-R1-Zero, 10 400 pas, 16 réponses par question, 32 questions par pas ; le coût de R1, « de l'ordre de 300 000 dollars selon la presse » (**tiers**, à dire comme tel). nanochat d20, GSM8K 2,50 puis 4,55 puis 7,58 % ; TinyZero, 0,5 Md n'apprend pas à raisonner, 1,5 Md commence.
- **1.10** (B4, A4) : Qwen2.5-Coder 0.5B Instruct, 61,6 % sur HumanEval avec environ 5,5 T de jetons de pré-entraînement, soit environ 630 fois ceux de ton IA (**dérivé**) ; Llama 3, plus de 2,7 M d'exemples de code synthétiques ; nanochat d20, HumanEval 6,71 puis 8,54 % ; Codex, 28,8 % avec un échantillon, 70,2 % avec 100 (« méthodes », §5.1).
- **Annuaire** : les jeux de la recherche « données », avec leur licence et leur taille telles que relevées le 17/11/2026, et ceux qu'elle écarte, avec la raison.

## Décisions du contrôleur, reprises telles quelles (17/11/2026)

- **Ordre :** plan 6, puis plan 7, puis ce plan. Un chapitre s'écrit en brouillon pendant que le plan 7 entraîne.
- **Un chapitre paraît dès que son modèle et ses fichiers sont prêts**, sans attendre les autres. Le contrôleur pousse et publie, sans question à l'utilisateur, après la validation de ce plan.
- **Honnêteté :** les gains sont petits, et on publie ce qui est mesuré, même décevant. Si le RL de 1.9 n'a pas été lancé, le chapitre le montre et l'explique. Le bac à sable de 1.10 est « limité », jamais « sûr ».
- **Données :** les paires de 1.8 viennent de ton IA, classées par des contrôles programmés, sans juge. MGSM et les jeux sans licence claire ne servent qu'à l'évaluation.
- **Les contraintes globales de la vague 1 restent**, adaptées ci-dessous.

## Choix de ce plan

1. **Les projets ne refont pas forge.** Comme 1.6 refaisait la perte à la main, chaque projet refait à la main la pièce que son chapitre explique (la perte masquée, la perte DPO, l'avantage, pass@k), et un test la compare à forge à 10⁻¹² près en float64. Le reste s'importe de forge.
2. **Les chiffres viennent de fichiers versionnés**, écrits par les projets à partir des rapports d'étape (`forge evaluer-etape`), des journaux et des fichiers de contrôle du plan 7, qu'ils lisent sans les modifier. Avant la Release, la page affiche « à mesurer ».
3. **Deux composants communs aux quatre chapitres**, rangés dans `site/src/components/chapitres/1-7/` et importés par les suivants :
   - `TableauEtape.astro`, les mesures d'une version face à la précédente ;
   - `EchantillonsConversation.astro`, les réponses telles quelles.
   `CourbeEntrainement.astro` et `TableauSessions.astro` (1.5) servent pour les courbes de SFT, avec de nouveaux noms dans `FICHIERS_ENTRAINEMENT`.
4. **La table « ton IA à travers les versions »** (1.5, 1.7, 1.8, 1.9, 1.10, sur les mêmes tests) grandit de chapitre en chapitre, et se montre en entier à la fin de 1.10.
5. **Les ateliers calculent sur ce que le lecteur fait**, et lisent ce que ton IA a écrit : les réponses, les traces et le code de ton IA viennent des fichiers des projets, jamais d'un modèle dans le navigateur.
6. **Les notebooks téléchargent une seule Release** : celle de leur étape (environ 830 Mo), plus `donnees-ton-ia-2` pour 1.10 (HumanEval-FR). L'« avant » vient des fichiers de mesures.
7. **L'intégration continue** télécharge les Releases listées dans `outils/versions-publiees.txt`, les garde en cache, et les donne aux notebooks par `FORGE_IA_MODELES`. Une étiquette entre dans ce fichier à la parution de son chapitre.
8. **L'annuaire gagne un groupe `affinage`**, les jeux écartés avec leur raison, et deux sections : « modèles » (le traducteur, les versions de ton IA) et « outils » (ceux que les projets utilisent ou citent).

## Écarts assumés avec la spécification

- **Fichiers versionnés qui ressemblent à des données :** au plus 6 paires réelles de 1.8 (invites de Luth-2, sous CC BY 4.0, citées ; réponses de ton IA) dans `projets/1.8-alignement/mesures/paires-exemples.json`, et au plus 6 problèmes de HumanEval-FR (MIT) dans les sorties de 1.10. Aucun autre texte de tiers n'entre dans le dépôt.
- **Les ateliers ne font pas tourner ton IA dans le navigateur** (433 M de paramètres) : ils montrent ses vraies sorties, relevées par les projets.

## Contraintes globales

Celles du plan 5 restent toutes valables : langue et typographie, couleurs et polices, jaune réservé à ce qui se manipule, interdits, mouvement, plancher de qualité, chiffres et sources, code des pages, jumeaux exacts, commits, noms en français, commandes PowerShell. S'y ajoutent ou les remplacent :

- **Caractères invisibles.** `site/src/lib/invisibles.test.ts` lit aussi :
  - `site/src/content/chapitres/1-(7|8|9|10).mdx`, `site/src/components/chapitres/1-(7|8|9|10)/**` ;
  - `site/e2e/chapitre-1-(7|8|9|10).spec.ts` ;
  - `projets/1.(7|8|9|10)-*/**/*.py` et leurs `pyproject.toml`, les cellules de code de `notebooks/1.(7|8|9|10)-*.ipynb`.
  Les motifs s'écrivent pour que `1-10` et `1.10-` soient pris et que `1-1` ne prenne pas `1-10` par préfixe.
- **Jumeaux exacts.** Python d'abord, TypeScript ensuite, mêmes fonctions et même ordre d'opérations. Pas de `\w`, `\b` ni `str.isspace` dans une fonction jumelle : des tests de caractères explicites (lettre : catégorie Unicode `L`, `/\p{L}/u` en TypeScript). Points de code lus par `Array.from`. Entiers seulement dans les tirages (`Hasard` de `forge.hasard` et de `site/src/lib/mini-modele/calcul.ts`). Attendus par `json.dumps(…, ensure_ascii=False, allow_nan=False, indent=1)`, `newline="\n"` ; comparaison par `toStrictEqual`.
- **Les chiffres de ton IA** viennent des fichiers de `projets/1.(7|8|9|10)-*/mesures/` et `sorties/`. Aucun n'est tapé dans un MDX. Une phrase qualitative est gardée par `exiger` sur les nombres qu'elle résume. Avant la parution, la page a au moins un `[data-a-mesurer]` ; après, aucun.
- **Honnêteté.** Les échantillons se montrent tels quels, sans choisir les meilleurs. « Sûr », « sans danger » et « garanti » n'apparaissent pas dans 1.10 pour le bac à sable (un test e2e le vérifie). Un score qui baisse est montré.
- **La carte graphique** sert au plan 7. Avant leur tâche de parution, les tâches de ce plan n'utilisent que `--extra cpu`, aucun contexte CUDA, ni WebGPU ni WebGL. Chrome est lancé avec `--disable-gpu`, les parcours avec `--workers=4`. `nvidia-smi` en lecture seule reste permis.
- **Go et stop :** comme au plan 7. Au « stop », l'agent en cours finit et aucun nouveau ne part.
- **Fichiers interdits :**
  - `projets/forge` en écriture : un défaut de forge se signale au contrôleur, qui le corrige au plan 7 ;
  - `projets/1.5-pre-entrainement` en écriture, sauf l'ajout de `serie()` de la tâche 1 ;
  - `D:\forge-ia-donnees` en écriture, sauf `cache\` ;
  - le tokenizer figé.
- **Dossier temporaire :** `. .\outils\env-forge.ps1; $env:TEMP = $env:TMP = "$env:FORGE_DONNEES\cache\tmp"` avant toute commande Python.
- **Vitest** se lance depuis `D:\creation-ia\site`, avec un `D:` majuscule : avec `d:\`, Vitest charge deux fois les mêmes modules.
- **Notebooks :** chacun se rejoue avant son commit (`.colab\Scripts\python outils\executer_notebooks.py notebooks\1.N-<nom>.ipynb`, attendu `ok`). Ni `pip install`, ni `torch.accelerator`, ni `torch.compile`, ni `datasets`, ni `forge.mesure`, ni `tomli_w`, ni `transformers`. Sans carte, ils le disent.
- **Parution :** la section « Parution d'un chapitre » du README, sans question. Après le déploiement, l'adresse du chapitre répond 200 sur le site public.

## Points à surveiller à la relecture

1. **Le chapitre 1.10 face à 1.1** : tri par chaîne (« 1.10 » avant « 1.2 »), préfixe (`1-1` dans `1-10`), motifs des garde-fous. Attendu : 1.10 vient après 1.9 partout (accueil, page de partie, barre, pied des chapitres, glossaire, annuaire), son adresse est `/forge-ia/partie-1/1-10/`, et les garde-fous lisent ses fichiers. Test en tâche 1.
2. **Une valeur de ton IA tapée à la main ou parue trop tôt.** Attendu : chaque brouillon a au moins un `[data-a-mesurer]` avant sa Release, aucun après ; `e2e/parution.spec.ts` refuse un chapitre paru qui en contient. Tests en tâches 3, 5, 7 et 9 (présence), puis 11 à 14 (absence).
3. **Le texte libre du lecteur dans l'atelier de 1.8** : accent combinant, apostrophe courbe, U+202F, U+00A0, emoji, texte vide, 10 000 caractères, seulement des chiffres. Attendu : mêmes verdicts qu'en Python, recalcul en moins de 200 ms, jamais `NaN`. Tests en tâches 4 et 5.
4. **Le notebook sur Colab sans carte** (Python 3.13, torch 2.14.1), avec un téléchargement de 830 Mo coupé puis relancé. Attendu : il reprend sans retélécharger ce qui est complet, n'installe rien, n'importe pas `datasets`, tourne sur le processeur et le dit ; en intégration continue, il prend les Releases de `FORGE_IA_MODELES`. Tests : `test_notebook.py` de chaque projet, le job `notebooks-colab`.
5. **Un résultat décevant** : RL non lancé, score à 0 %, vraisemblance de la choisie qui baisse, ton IA plus mauvaise qu'avant sur un test. Attendu : la page le montre et l'explique ; aucune phrase ne promet plus que les fichiers. Tests : les gardes `exiger` et les parcours des tâches 3, 5, 7 et 9, rejoués avec des fichiers de mesures fabriqués dans les deux sens (gain et perte).

## Fichiers

```
site/src/lib/partie-1/  etapes.ts, conversation.ts, bfd.ts, notes.ts, dpo.ts, problemes.ts,
  avantages.ts, passk.ts, fim.ts, paris-1-7.ts … paris-1-10.ts, sources-1-7.ts … sources-1-10.ts
  (+ leurs tests) ; journal.ts, commandes.ts, fichiers.ts, mesures.ts, parite.ts (modifiés)
site/src/components/chapitres/1-7/  OuvertureConversation.astro, AtelierConversation.svelte,
  FigureEmpaquetage.svelte, TableauEtape.astro, EchantillonsConversation.astro
site/src/components/chapitres/1-8/  OuverturePreferences.astro, AtelierNote.svelte, PhraseDpo.svelte,
  CourbePreferences.astro, TableauBalayage.astro
site/src/components/chapitres/1-9/  OuvertureRaisonnement.astro, AtelierProblemes.svelte,
  FigureGroupe.svelte, CourbeRecompense.astro, ControleDepart.astro
site/src/components/chapitres/1-10/ OuvertureCode.astro, AtelierTrou.svelte, PhrasePassK.svelte,
  TableauBacASable.astro, TableauVersions.astro
site/src/brouillons/chapitres/1-7.mdx … 1-10.mdx   (puis git mv vers content/)
site/src/lib/annexes/glossaire.ts, annuaire.ts ; site/src/pages/annexes/annuaire.astro
site/e2e/chapitre-1-7.spec.ts … chapitre-1-10.spec.ts
projets/1.7-conversation/   paquet conversation_pas_a_pas
projets/1.8-alignement/     paquet alignement_pas_a_pas
projets/1.9-raisonnement/   paquet raisonnement_pas_a_pas
projets/1.10-code/          paquet code_pas_a_pas
notebooks/1.7-conversation.ipynb, 1.8-alignement.ipynb, 1.9-raisonnement.ipynb, 1.10-code.ipynb
outils/versions-publiees.txt ; .github/workflows/python.yml (job notebooks-colab)
```

Chaque projet a `pyproject.toml` (le bloc PyTorch de 1.6, `forge-ia` et `pre-entrainement` par chemin), `uv.lock`, `.python-version` (`3.12`), `README.md`, son paquet, `tests/` (dont `conftest.py`, qui publie un modèle minuscule par `forge.exporter` dans un dossier temporaire, et `test_notebook.py` sur le patron de 1.6), `mesures/` et `sorties/`.

---

### Tâche 1 : le socle de la vague 2 sur le site

**Fichiers :**

- Modifier : `site/src/lib/invisibles.test.ts`, `site/src/lib/partie-1/journal.ts`, `commandes.ts` (+ tests), `site/src/lib/parcours.test.ts`
- Créer : `site/src/lib/partie-1/etapes.ts`, `etapes.test.ts`
- Modifier : `projets/1.5-pre-entrainement/pre_entrainement/journal.py` (ajout de `serie`), `tests/test_journal.py`
- Créer : `outils/versions-publiees.txt` (une ligne : `ton-ia-1.5`) ; modifier `.github/workflows/python.yml`

**Interfaces (produites) :**

- `pre_entrainement.journal.serie(lignes: list[dict], cle: str, points: int = 600, pas_total: int | None = None) -> list[list[float]]` : `[pas, moyenne]` de la clé `cle`, par paquets, avec le même découpage que `courbe` (qui l'appelle désormais pour `perte`, sans changer sa sortie).
- `etapes.ts` :
  - `FICHIERS_ETAPES` : nom → chemin. Les noms sont `'1.5@1.7'`, `'1.7@1.7'`, `'1.7-court@1.7'`, `'1.8@1.8'`, `'1.8-court@1.8'`, `'1.5@1.9'`… : « version@étape », chacun le résumé d'un rapport d'étape écrit par un projet (`projets/1.N-*/mesures/etape-<version>.json`) ;
  - `type RapportEtape` : `version`, `etape`, `releve_le`, `mesures` (les clés de `MESURES_PAR_ETAPE` du plan 7, chacune ses nombres ou `{ absente }`), `echantillons` ;
  - `lireRapportEtape(nom, racineDepot = '..'): RapportEtape | null` et `verifierRapportEtape(valeur, fichier)`, qui lèvent un message qui dit quel relevé refaire ;
  - `lireSeries(fichier: string, racineDepot = '..'): Record<string, [number, number][]> | null` : les séries d'un fichier de courbes de 1.8 ou 1.9 (une clé par série), `null` si le fichier manque.
- `journal.ts` : `FICHIERS_ENTRAINEMENT` gagne `'sft-1.7'`, `'sft-1.7-court'`, `'sft-1.9'`, `'sft-1.10'`, chacun dans `projets/1.N-*/mesures/entrainement-<nom>.json`.
- `commandes.ts` : `TELECHARGER_VERSION(etiquette)`, dès cette tâche. Les commandes des chapitres y entrent avec leur tâche de parution (11 à 14), quand le README de forge les contient (plan 7, contrainte « Le README de forge ») : `AFFINER_1_7`, `AFFINER_1_7_COURT`, `REPRENDRE_1_7`, `DISCUTER_1_7`, `PREFERENCES_1_8`, `DPO_1_8`, `PROBLEMES_1_9`, `SFT_1_9`, `GRPO_1_9`, `TRADUIRE_1_10`, `CODE_1_10`. Chacune se lit telle quelle dans `projets/forge/README.md` (test existant de `commandes.test.ts`, étendu). Dans un brouillon, l'étape qui les montrera dit la commande en prose, sans bloc.
- Job `notebooks-colab` :
  - une étape de cache, clé `versions-${{ hashFiles('outils/versions-publiees.txt') }}`, chemin `${{ runner.temp }}/versions` ;
  - une étape qui télécharge chaque étiquette du fichier absente du dossier (`gh release download <étiquette> --dir "$RUNNER_TEMP/versions/<étiquette>"`) ;
  - `FORGE_IA_MODELES=$RUNNER_TEMP/versions`, et `FORGE_IA_MODELE=$RUNNER_TEMP/versions/ton-ia-1.5` pour 1.5 et 1.6, inchangés ;
  - `timeout-minutes: 40`.

- [ ] **Étape 1 : tests rouges.**

```ts
// parcours.test.ts — point à surveiller 1
expect(hrefChapitre('1.10')).toBe('/forge-ia/partie-1/1-10/');
expect(NUMEROS_DU_PARCOURS.indexOf('1.10')).toBe(NUMEROS_DU_PARCOURS.indexOf('1.9') + 1);
expect(voisins('1.10').precedent?.numero).toBe('1.9');
expect(voisins('1.9').suivant?.numero).toBe('1.10');
// invisibles.test.ts : les motifs prennent 1-10.mdx, chapitre-1-10.spec.ts, projets/1.10-code/x.py,
// et ne prennent pas un 1-1x.mdx inventé par préfixe
```

  Plus `etapes.test.ts` (un rapport fabriqué lu ; une mesure absente rendue telle quelle ; un fichier faux refusé avec son message), `test_journal.py` (`serie` sur le journal factice ; `courbe` inchangée, comparée à sa sortie d'avant), et un parcours de `navigation.spec.ts` : sur l'accueil et la page de la Partie 1 construites avec `FORGE_ESSAIS=1`, le lien de 1.10 suit celui de 1.9 dans l'ordre du document.
- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire.** Si un tri par chaîne place 1.10 avant 1.2 quelque part (accueil, page de partie, pied, glossaire), le corriger par un tri sur `[partie, numéro]` en entiers.
- [ ] **Étape 4 : tout vérifier**, `npx vitest run`, `npm run check:svelte`, `npx astro check`, `npx playwright test --workers=4`, et pytest dans 1.5.
- [ ] **Étape 5 : commit**, « Vague 2 : socle du site, rapports d'étape, ordre de 1.10, versions publiées pour les notebooks ».

### Tâche 2 : le projet 1.7 « conversation », son notebook et ses jumeaux

**Fichiers :**

- Créer : `projets/1.7-conversation/` (paquet `conversation_pas_a_pas` : `__init__.py`, `gabarit.py`, `fuite.py`, `petit_affinage.py`, `resumer.py`, `attendus.py`, `__main__.py` ; `tests/` : `conftest.py`, `test_gabarit.py`, `test_fuite.py`, `test_petit_affinage.py`, `test_resumer.py`, `test_attendus.py`, `test_notebook.py`, `attendus.json`)
- Créer : `notebooks/1.7-conversation.ipynb`
- Créer : `site/src/lib/partie-1/conversation.ts`, `bfd.ts` (+ tests) ; modifier `parite.ts`, `fichiers.ts`, `site/src/essais/parite-partie-1.mdx`, `site/e2e/parite.spec.ts`

**Interfaces :**

- `gabarit.py`, régions `gabarit` et `masque` :
  - `montrer(tok, tours) -> list[dict]` : par jeton, `id`, `texte` (visible, `␊` pour un saut de ligne, le nom pour un spécial), `role` et `appris`, depuis `encoder_conversation` ;
  - `perte_masquee_a_la_main(logits, cibles) -> float` : somme des pertes des cibles différentes de −100, divisée par leur nombre, en float64 ; égale à `pas_sft` de forge sur un lot (test).
- `fuite.py`, région `fuite` : `ecarts_de_fuite(graine: int = 0) -> dict`. Sur un modèle minuscule semé, une rangée « conversation A puis B » donne l'écart maximal des logits de B face à B seule, avec et sans `documents`. Sortie : `sorties/fuite.txt` (première ligne `# relevé le AAAA-MM-JJ`) et `mesures/fuite.json`.
- `petit_affinage.py`, région `essai` : `essai_affinage(appareil: str, pas: int = 80) -> dict`. Un modèle minuscule (dim 64, 2 couches, 4 têtes, contexte 128), pré-entraîné 40 pas sur `texte-du-site.txt` de 1.1, puis affiné par `forge entrainer` (méthode `sft`) sur 24 conversations écrites dans `petit_affinage.py`. Il rend les pertes, et la part des réponses qui finissent par `<|fin_tour|>` avant et après. Le départ est publié par `forge.exporter`, comme une vraie version.
- `resumer.py` :
  - `resumer_etape(rapport: Path) -> dict` → `mesures/etape-<version>.json` (`{version, etape, releve_le, mesures, echantillons}`, sans rien recalculer) ;
  - `longueurs(jeu: Path) -> dict` → `mesures/longueurs-sft-1.7.json` (longueurs des exemples, lues dans `train/documents.bin`, en lecture seule) ;
  - la courbe et les sessions passent par `pre_entrainement` (`courbe --journal … --config … --json mesures/entrainement-sft-1.7.json`).
- `attendus.py` : six conversations de référence (avec système, sans, deux tours, un texte qui imite un jeton spécial, une pensée, une réponse vide refusée) ; pour chacune, les ids de chaque texte encodé, puis les `ids` et `appris` assemblés ; les jetons spéciaux de ton IA et leurs ids ; `empaqueter` de forge sur 5 listes de longueurs (dont celles de `mesures/longueurs-sft-1.7.json` quand il existe) pour 4 capacités.
- `conversation.ts` : `SPECIAUX_TON_IA` (nom → id, vérifié contre les attendus) ; `assemblerConversation(tours: { role: Role; ids: number[]; penseeIds?: number[] }[]): { ids: number[]; appris: boolean[] }`, traduction exacte d'`encoder_conversation` une fois les textes encodés.
- `bfd.ts` : `empaqueterLongueurs(longueurs: number[], capacite: number): { rangees: number[][]; ecartes: number }`, traduction exacte du placement d'`empaqueter` (mêmes égalités, même ordre).
- `__main__.py` : `montrer "…"`, `fuite --enregistrer sorties/fuite.txt --json mesures/fuite.json`, `essai --appareil cpu`, `resumer --rapport R --json J`, `longueurs --jeu D --json J`.

- [ ] **Étape 1 : tests rouges.**

```python
def test_perte_a_la_main_egale_forge(): ...   # 10⁻¹² en float64, sur un lot de ChargeurAffinage factice
def test_fuite():
    e = ecarts_de_fuite()
    assert e["avec_masque"] <= 1e-5 and e["sans_masque"] > 1e-3
def test_petit_affinage_apprend_a_s_arreter():
    r = essai_affinage("cpu", pas=80)
    assert r["fin_de_tour_apres"] > r["fin_de_tour_avant"] and r["pertes"][-1] < r["pertes"][0]
```

  `test_perte_a_la_main_egale_forge` est encadré par `# region: test-perte` / `# fin: test-perte`. Plus `test_attendus_a_jour`, `test_resumer` (rapport fabriqué au format du plan 7) et `test_notebook.py` (« Défi réussi », « Même résultat que la page du site : oui », sans carte, rien d'installé).
- [ ] **Étape 2 : vérifier l'échec.** Puis `git status --short projets/forge` : vide.
- [ ] **Étape 3 : écrire le paquet, les attendus et le notebook.**
  - **Le notebook** : 1. une conversation devient des jetons ; 2. le masque de perte ; 3. empaqueter, et la fuite sans masque ; 4. un tout petit affinage (`essai_affinage`, processeur) ; 5. ce qu'il faut pour affiner ton IA (les commandes, la carte d'environ 12 Go). La section qui parle à ton-ia-1.7 vient à la tâche 11.
  - **L'exercice** : écrire `jetons_appris(exemple)`. « Défi réussi » si le compte égale `sum(exemple.appris)`.
- [ ] **Étape 4 : relever**, sur le processeur : `fuite`, `essai --appareil cpu` (dans `sorties/essai-processeur.txt` et `mesures/essai-processeur.json`).
- [ ] **Étape 5 : les jumeaux et leur parité, tests d'abord** : `conversation.test.ts` et `bfd.test.ts` comparent chaque attendu (`toStrictEqual`) ; la page de parité et `e2e/parite.spec.ts` font de même dans Chrome, Firefox et WebKit.
- [ ] **Étape 6 : rejouer le notebook, vérifier**, commit « Projet 1.7 : le format de conversation pas à pas, la fuite sans masque et un petit affinage, avec leurs jumeaux ».

### Tâche 3 : le chapitre 1.7 « Apprendre à converser », en brouillon

**Fichiers :**

- Créer : `site/src/components/chapitres/1-7/OuvertureConversation.astro`, `AtelierConversation.svelte`, `FigureEmpaquetage.svelte`, `TableauEtape.astro`, `EchantillonsConversation.astro`
- Créer : `site/src/lib/partie-1/paris-1-7.ts`, `sources-1-7.ts` (+ tests) ; `site/src/brouillons/chapitres/1-7.mdx` ; `site/e2e/chapitre-1-7.spec.ts`

**Interfaces :**

- `TableauEtape.astro` : props `{ versions: readonly NomRapport[]; mesures: readonly string[]; legende: string }`. Une colonne par version, une ligne par mesure, dans un `<table>` typographié. Une valeur absente devient `<span data-a-mesurer>à mesurer</span>`.
- `EchantillonsConversation.astro` : props `{ nom: NomRapport; invites?: readonly number[] }`. Les réponses telles quelles, en chasse fixe, `data-pagefind-ignore`, terminée ou non signalée sans couleur.
- `OuvertureConversation.astro` : la même invite (« Qui es-tu ? »), la réponse de ton-ia-1.5 et celle de ton-ia-1.7, tirées des échantillons des deux rapports. Avant la Release, `data-a-mesurer`.
- `AtelierConversation.svelte` : props `{ verrou?: string; acquis?: string }`.
  - Le choix d'une des six conversations de référence, et deux bascules (`.bascule-soleil`) : « avec un message système », « un deuxième tour ».
  - Les jetons en pastilles (`data-test="cv-jetons"`, `data-pagefind-ignore`) : appris en indigo plein, non appris en lavande, spéciaux en chasse fixe.
  - La phrase « {n} jetons, dont {m} appris » (`data-test="cv-compte"`), calculée par `assemblerConversation`.
- `FigureEmpaquetage.svelte` : un `NombreManipulable` (longueur des rangées : 512, 1 024, 2 048 ou 4 096) dans la phrase « Avec des rangées de [L] jetons, BFD remplit {r} % des places, et écarte {e} exemples trop longs ». Calcul par `empaqueterLongueurs` sur `mesures/longueurs-sft-1.7.json`. Avant le relevé, la figure tourne sur la liste de référence des attendus, et le dit.
- `paris-1-7.ts`, avec `exigeur('src/lib/partie-1/paris-1-7.ts et le texte des paris du chapitre 1.7')` :
  - `choixMasque()` : « Sur quels jetons porte la perte de l'affinage ? » ; « tous », « ceux des réponses de l'assistant, fin de tour comprise », « seulement le dernier jeton ». Le juste se calcule par `assemblerConversation` sur la conversation de référence ;
  - `choixFuite()` : « Sans masque par document, la deuxième conversation d'une rangée… » ; « est calculée comme si elle était seule », « voit la première ». Le juste se lit dans `mesures/fuite.json` ;
  - `choixFinDeTour()` : « Ton IA 1.5, qui n'a jamais vu de conversation, finit-elle d'elle-même ses réponses ? » ; trois tranches de `tenue.terminee` de `'1.5@1.7'` ;
  - `choixConsignes()` : trois tranches de `ifeval_fr.invite_stricte` de `'1.7@1.7'` ;
  - `choixOubli()` : « Après l'affinage, sa perte sur le texte du web… » ; monte, baisse, ne bouge pas (à 0,01 près), par `oubli` de 1.5 et de 1.7.
  Les trois derniers rendent `null` tant que leur fichier manque, et la page pose `data-a-mesurer` à la place du pari.
- `sources-1-7.ts` : les chiffres de l'encadré, chacun avec `url`, `endroit`, `lu_le` et son étiquette de la recherche.

| Étape | Titre | Contenu imposé |
| --- | --- | --- |
| 1 | Ton IA ne sait pas répondre | `OuvertureConversation`. Pari `fin`. Ce qu'est l'affinage supervisé : même modèle, même perte, autres textes. |
| 2 | Le gabarit | Les jetons spéciaux prévus en 1.3 (`SPECIAUX_TON_IA`), `CodeExplique symbole="encoder_conversation"` de forge. Les embeddings des jetons spéciaux n'ont jamais servi en entrée (« méthodes », §2.1, une inférence, dite comme telle). |
| 3 | Ce que ton IA apprend | Pari `masque`, puis `AtelierConversation` sous `Verrou`. `CodeExplique` région `masque`. |
| 4 | Ranger les conversations | `FigureEmpaquetage`, BFD (`CodeExplique symbole="empaqueter"`). Pari `fuite`, puis `SortieCommande` de `sorties/fuite.txt` et le masque par document. |
| 5 | Où trouver des conversations | Luth-2, Aya, OASST2, et les écartés (Llama, OpenAI) avec leur raison ; les messages système et l'identité générés par programme. Lien vers l'annuaire. |
| 6 | Un petit affinage | `CodeExplique` région `essai`, `SortieCommande` de `sorties/essai-processeur.txt`. |
| 7 | L'affinage de ton IA | Le balayage du taux, `CourbeEntrainement nom="sft-1.7"`, `TableauSessions`, `BlocCommande` de `AFFINER_1_7_COURT` et `REPRENDRE_1_7`. |
| 8 | Ce qu'elle sait faire maintenant | Pari `consignes`, `TableauEtape` (1.5, 1.7 et la version courte ; mesures `ifeval_fr`, `tenue`, `perte_conversation`), `EchantillonsConversation`. Pari `oubli` et la mesure `oubli`. |
| 9 | Chez un grand labo | `EncadreLabo` : InstructGPT, Llama 2, Tülu 3, SmolLM3 (`sources-1-7.ts`). |
| 10 | Le code et le projet | `CodeExplique` région `test-perte`, `RecupererProjet projet="1.7-conversation"`, `BlocCommande` de `DISCUTER_1_7`, « À suivre » vers 1.8. |

**Acquis :** `fin`, `gabarit`, `masque`, `fuite`, `atelier`, `consignes`, `oubli`.

**Défi :** construire dans l'atelier une conversation dont plus de la moitié des jetons sont appris. L'atelier le vérifie.

- [ ] **Étape 1 : tests rouges.** `paris-1-7.test.ts` (un seul juste par pari, et `null` sans fichier). `e2e/chapitre-1-7.spec.ts`, en brouillon avec `FORGE_ESSAIS=1` :
  - « Partie 1, chapitre 1.7 sur 21 » ; paris, atelier, récapitulatif ; axe ; 390 px ; lignes de prose de 80 caractères au plus ;
  - le compte de l'atelier égale celui du jumeau pour les six conversations et les quatre combinaisons de bascules ;
  - la figure : 4 longueurs, jamais `NaN`, recalcul en moins de 200 ms ;
  - **au moins un `[data-a-mesurer]`** ;
  - le code affiché est celui des régions et symboles testés ;
  - deux jeux de rapports fabriqués, où l'oubli monte puis baisse : la phrase de l'étape 8 change de sens, gardée par `exiger` (point à surveiller 5).
- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire.** Relire à la source chaque chiffre de l'encadré, et l'écrire dans `sources-1-7.ts` avec sa date.
- [ ] **Étape 4 : tout vérifier**, captures (ordinateur, mobile, atelier ouvert), relues face à 1.6 et aux deux mémoires de direction visuelle.
- [ ] **Étape 5 : commit**, « Chapitre 1.7 : apprendre à converser, avec l'atelier du masque (brouillon, ton IA à mesurer) ».

### Tâche 4 : le projet 1.8 « alignement », son notebook et ses jumeaux

**Fichiers :**

- Créer : `projets/1.8-alignement/` (paquet `alignement_pas_a_pas` : `noter.py`, `perte_dpo.py`, `courbes.py`, `resumer.py`, `attendus.py`, `__main__.py` ; tests, dont `test_noter.py`, `test_perte_dpo.py`, `test_resumer.py`, `test_attendus.py`, `test_notebook.py`)
- Créer : `notebooks/1.8-alignement.ipynb`
- Créer : `site/src/lib/partie-1/notes.ts`, `dpo.ts` (+ tests) ; modifier `parite.ts`, `fichiers.ts`

**Interfaces :**

- `noter.py`, région `noter` : `expliquer_note(reponse_texte: str, terminee: bool, invite: InvitePreference) -> dict`, chaque critère de `forge.preferences.noter` avec son verdict et sa raison en français (« 3 consignes sur 3 », « en français », « 47 mots »). La note rendue égale `noter` de forge.
- `perte_dpo.py`, région `perte-dpo` : `perte_dpo_a_la_main(pc, pr, qc, qr, beta) -> float` en float64, et le terme SFT à part. Égale à `perte_dpo` de forge à 10⁻¹² près (test, encadré par `# region: test-dpo`).
- `courbes.py` : `courbes_dpo(journal: Path) -> dict` (`logps_choisie`, `logps_rejetee`, `exactitude` par `pre_entrainement.journal.serie`).
- `resumer.py` :
  - `resumer_etape` (comme 1.7) → `mesures/etape-<version>.json` ;
  - `paires_exemples(jeu: Path, n: int = 6) -> list[dict]` → `mesures/paires-exemples.json` : invite, deux réponses, leurs notes, les log-probabilités de référence et la source avec sa licence ;
  - `balayage(dossiers: list[Path]) -> list[dict]` → `mesures/balayage-1.8.json` (réglages, victoire, longueur, `logps_choisie` au début et à la fin) ;
  - `courbes_dpo` → `mesures/entrainement-dpo-1.8.json`.
- `attendus.py` : verdicts de `langue`, des huit contraintes et de la longueur sur 40 textes de référence, dont les pièges du point à surveiller 3 ; `perte_dpo_a_la_main` sur une grille de 27 points (β, écart de la choisie, écart de la rejetée).
- `notes.ts` : `mots`, `langue`, `VERIFICATEURS_CONTRAINTES` (les huit de forge), `noteSansJustesse(texte, terminee, contraintes)`. Traduction exacte de `forge.evaluation.langue` et `forge.evaluation.consignes`, listes de mots comprises : `notes.test.ts` relit le texte de `langue.py` et vérifie que les deux listes sont les mêmes, sans importer Python.
- `dpo.ts` : `perteDpo(beta, ecartChoisie, ecartRejetee): number` et sa dérivée. Égalité aux attendus à 10⁻¹² près (`Math.exp`, `Math.log1p` ne sont pas exacts d'un moteur à l'autre ; le test le dit en commentaire). Hors de la page de parité.

- [ ] **Étape 1 : tests rouges** : `test_noter.py` (égale forge sur 50 réponses fabriquées), `test_perte_dpo.py`, `test_resumer.py`, `test_attendus_a_jour`, `test_notebook.py`.
- [ ] **Étape 2 : vérifier l'échec**, et `git status --short projets/forge` vide.
- [ ] **Étape 3 : écrire le paquet, les attendus et le notebook.**
  - **Le notebook** : 1. deux réponses et leur note ; 2. une paire ; 3. la perte DPO à la main ; 4. ce que DPO pousse, la choisie vers le haut ou la rejetée vers le bas (sur une paire réelle de `paires-exemples.json`, quand il existe ; sinon sur une paire fabriquée, et il le dit). La section ton-ia-1.8 vient à la tâche 12.
  - **L'exercice** : écrire `finit_par(reponse, phrase)`. « Défi réussi » s'il s'accorde avec le vérificateur `fin_imposee` sur 10 cas.
- [ ] **Étape 4 : les jumeaux, tests d'abord.** `notes.test.ts` : chaque attendu ; 10 000 caractères en moins de 200 ms ; le texte vide et le texte de chiffres seuls. Parité de `notes` dans les trois navigateurs.
- [ ] **Étape 5 : vérifier, rejouer le notebook**, commit « Projet 1.8 : noter deux réponses, la perte DPO à la main, avec leurs jumeaux ».

### Tâche 5 : le chapitre 1.8 « L'aligner : préférences et récompenses », en brouillon

**Fichiers :**

- Créer : `site/src/components/chapitres/1-8/OuverturePreferences.astro`, `AtelierNote.svelte`, `PhraseDpo.svelte`, `CourbePreferences.astro`, `TableauBalayage.astro`
- Créer : `paris-1-8.ts`, `sources-1-8.ts` (+ tests), `site/src/brouillons/chapitres/1-8.mdx`, `site/e2e/chapitre-1-8.spec.ts`

**Interfaces :**

- `OuverturePreferences.astro` : une paire réelle de `paires-exemples.json`, les deux réponses côte à côte, sans dire laquelle est choisie avant le pari `note`.
- `AtelierNote.svelte` : une invite contrainte, choisie parmi celles de `paires-exemples.json`. Un champ souligné de jaune (`data-test="an-texte"`) où le lecteur écrit sa réponse. Chaque critère s'affiche avec son verdict (`data-test="an-critere"`) et la note totale, recalculée à chaque frappe par `noteSansJustesse`. « Comparer avec ton IA » montre les deux réponses réelles et leurs notes.
- `PhraseDpo.svelte` : trois `NombreManipulable`, β (0,05 à 0,5), l'écart de la choisie et celui de la rejetée (−3 à +3 nats). La phrase dit la perte, puis le sens du gradient (« pousser la choisie vers le haut » ou « la rejetée vers le bas », d'après la dérivée).
- `CourbePreferences.astro` : `logps_choisie` et `logps_rejetee` au fil des pas, SVG dessiné à la main, avec un tableau équivalent pour les lecteurs d'écran.
- `TableauBalayage.astro` : les essais du balayage, le retenu signalé par un trait indigo dans la marge (pas de couleur criarde).
- `paris-1-8.ts` :
  - `choixNote()` : la réponse que les contrôles préfèrent, calculée par `noteSansJustesse` et la terminaison ;
  - `choixVraisemblance()` : « Pendant DPO, la probabilité que ton IA donne à la réponse choisie… » ; monte, baisse, ne bouge pas (à 0,01 près), par la courbe ;
  - `choixLongueur()` : « Après DPO, ses réponses sont… » ; plus longues, plus courtes, de même longueur (à 5 % près), par la mesure `victoire` ;
  - `choixVictoire()` : trois tranches du taux de victoire de 1.8 contre 1.7.
- `sources-1-8.ts`.

| Étape | Titre | Contenu imposé |
| --- | --- | --- |
| 1 | Deux réponses, une meilleure | `OuverturePreferences`, pari `note`. Ce que veut dire « préférer ». |
| 2 | Qui décide ? | Humains, juge, ou contrôles programmés : le choix de ce chapitre (pas de juge), et pourquoi. Le jeu écarté pour sa licence (réponses de Llama). |
| 3 | L'atelier des notes | `AtelierNote` sous `Verrou`. `CodeExplique` région `noter`. |
| 4 | Fabriquer des paires | `CodeExplique symbole="construire_paires"`, et les chiffres de la construction (taux de paires, ce qui départage). |
| 5 | La perte DPO | `PhraseDpo`, `CodeExplique` région `perte-dpo`, le modèle de référence et β. |
| 6 | Le piège de la vraisemblance | Pari `vraisemblance`, puis `CourbePreferences`. DPOP (arXiv 2402.13228) et le terme SFT. |
| 7 | Le balayage | `TableauBalayage`, `BlocCommande` de `PREFERENCES_1_8` et `DPO_1_8`. |
| 8 | Ce qui a changé | Paris `longueur` et `victoire`, `TableauEtape` (1.7, 1.8, la version courte), échantillons. La longueur qui grandit sans être meilleure, si c'est le cas. |
| 9 | Chez un grand labo | `EncadreLabo` : InstructGPT, Llama 2, Qwen2.5, Tülu 3 (avec ce qui ne s'accorde pas, s'il est imprimé), et le modèle de récompense, qui ne tourne pas ici. |
| 10 | Le projet | `CodeExplique` région `test-dpo`, `RecupererProjet projet="1.8-alignement"`, « À suivre » vers 1.9. |

**Acquis :** `preference`, `notes`, `atelier`, `paires`, `dpo`, `piege`, `longueur`.

**Défi :** écrire dans l'atelier une réponse qui obtient la note la plus haute. L'atelier le vérifie.

- [ ] **Étape 1 : tests rouges.** `paris-1-8.test.ts`, puis `e2e/chapitre-1-8.spec.ts`, comme en tâche 3, plus :
  - l'atelier, avec les textes du point à surveiller 3 : mêmes verdicts que les attendus, en moins de 200 ms ;
  - `PhraseDpo` aux bornes, jamais `NaN` ni `e+` ;
  - deux jeux de mesures fabriqués, « la choisie monte » et « la choisie baisse » : la phrase de l'étape 6 change de sens, gardée par `exiger` (point à surveiller 5).
- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire**, sources relues.
- [ ] **Étape 4 : tout vérifier**, captures et relecture.
- [ ] **Étape 5 : commit**, « Chapitre 1.8 : l'aligner, avec l'atelier des notes et la perte DPO (brouillon) ».

### Tâche 6 : le projet 1.9 « raisonnement », son notebook et ses jumeaux

**Fichiers :**

- Créer : `projets/1.9-raisonnement/` (paquet `raisonnement_pas_a_pas` : `problemes.py`, `avantages.py`, `petit_grpo.py`, `resumer.py`, `attendus.py`, `__main__.py` ; tests)
- Créer : `notebooks/1.9-raisonnement.ipynb`
- Créer : `site/src/lib/partie-1/problemes.ts`, `avantages.ts` (+ tests) ; modifier `parite.ts`, `fichiers.ts`

**Interfaces :**

- `problemes.py`, région `probleme` : `montrer_probleme(famille, difficulte, graine) -> dict` (énoncé, étapes, réponse, conversation encodée).
- `avantages.py`, région `avantages` : `avantages_a_la_main(recompenses: list[list[float]]) -> list[list[float]]`, égal à `forge.raisonnement.grpo.avantages` ; `sans_signal(p: float, n: int) -> float` = pⁿ + (1 − p)ⁿ, calculé par deux produits en boucle (jumeau exact).
- `petit_grpo.py`, région `pas-grpo` : `essai_grpo(appareil: str, pas: int = 20) -> dict`. Un modèle minuscule, d'abord affiné à répéter un chiffre (« Répète : 7 » → « 7 »), puis 20 pas de GRPO de forge sur cette tâche. Il rend la récompense moyenne pas à pas et la part de groupes sans signal. Le test ne demande pas que la récompense monte : seulement des nombres finis, et des gradients nuls pour un groupe sans signal.
- `resumer.py` :
  - `resumer_etape` ;
  - `controle(sortie_grpo: Path) -> dict` → `mesures/controle-1.9.json` (le contrôle de départ ; `lance: false` s'il a refusé) ;
  - `courbes_grpo(journal) -> dict` → `mesures/entrainement-grpo-1.9.json` (`recompense_moyenne`, `groupes_sans_signal`, `reussite_val`), ou `{ "lance": false }`.
- `attendus.py` : les problèmes de chaque famille, difficulté et graine 0 à 4 ; `avantages_a_la_main` sur 10 groupes ; `sans_signal` sur une grille p × n.
- `problemes.ts` : `genererProbleme(famille, difficulte, graine)` et `extraireNombre(texte)`, traductions exactes (listes de prénoms et d'objets comprises : `problemes.test.ts` relit `problemes.py` et compare les listes). `avantages.ts` : `avantages`, `sansSignal`.

- [ ] **Étape 1 : tests rouges** : égalités à forge (problèmes à l'identique, avantages à 10⁻¹² près), `essai_grpo` (`# region: test-grpo`), `test_resumer.py` (un contrôle « refusé » et un contrôle « lancé », fabriqués), `test_attendus_a_jour`, `test_notebook.py`.
- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire le paquet, les attendus et le notebook.**
  - **Le notebook** : 1. un problème et sa trace ; 2. vérifier une réponse ; 3. un groupe de réponses et leur avantage ; 4. pourquoi un groupe sans signal n'apprend rien (`sans_signal`) ; 5. un petit GRPO (`essai_grpo`, processeur). La section ton-ia-1.9 vient à la tâche 13.
  - **L'exercice** : écrire l'avantage d'un groupe. « Défi réussi » s'il égale `avantages_a_la_main`.
- [ ] **Étape 4 : les jumeaux et leur parité**, dans les trois navigateurs.
- [ ] **Étape 5 : vérifier, rejouer**, commit « Projet 1.9 : problèmes, avantages et un petit GRPO pas à pas, avec leurs jumeaux ».

### Tâche 7 : le chapitre 1.9 « Le faire raisonner », en brouillon

**Fichiers :**

- Créer : `site/src/components/chapitres/1-9/OuvertureRaisonnement.astro`, `AtelierProblemes.svelte`, `FigureGroupe.svelte`, `CourbeRecompense.astro`, `ControleDepart.astro`
- Créer : `paris-1-9.ts`, `sources-1-9.ts` (+ tests), `site/src/brouillons/chapitres/1-9.mdx`, `site/e2e/chapitre-1-9.spec.ts`

**Interfaces :**

- `OuvertureRaisonnement.astro` : un problème des échantillons, la réponse de ton-ia-1.8 et celle de ton-ia-1.9 (avec sa pensée, dans un bloc à part).
- `AtelierProblemes.svelte` : famille, difficulté (bascules), graine (`NombreManipulable`) ; l'énoncé, puis, au clic, la trace et la réponse (calculées par `genererProbleme`). Un champ « Ta réponse » vérifié par `extraireNombre`.
- `FigureGroupe.svelte` : deux `NombreManipulable` dans la phrase « Si ton IA réussit [p] % des fois, un groupe de [n] réponses n'a aucun signal {s} % du temps ». En dessous, un groupe tiré (`Hasard`), ses récompenses et ses avantages. Sous `prefers-reduced-motion`, rien ne glisse.
- `CourbeRecompense.astro` : la récompense moyenne et la réussite de validation au fil des pas. Si le RL n'a pas été lancé, rien n'est dessiné : le composant laisse la place à `ControleDepart`.
- `ControleDepart.astro` : le contrôle de départ (réponses tirées, justes, taux), et la décision (« lancé » ou « pas lancé : aucune réponse juste, donc aucun signal »).
- `paris-1-9.ts` :
  - `choixControle()` : « Avant le RL, sur les réponses tirées au hasard, combien sont justes ? » ; aucune, moins d'une sur dix, plus d'une sur dix ;
  - `choixGroupeMuet()` : « Seize réponses, toutes fausses : leur avantage vaut… » ; 0 pour toutes (juste, par `avantages`), −1 pour toutes, on retire le groupe au sort ;
  - `choixMgsm()` : trois tranches de `mgsm_fr` de 1.9 ;
  - `choixRl()` : « Après le RL, la réussite… » ; monte, baisse, et « le RL n'a pas été lancé » (juste si `lance` est faux).

| Étape | Titre | Contenu imposé |
| --- | --- | --- |
| 1 | Penser avant de répondre | `OuvertureRaisonnement`. Les deux jetons de pensée, prévus dès 1.3. |
| 2 | Des problèmes justes par construction | `AtelierProblemes` sous `Verrou`, `CodeExplique` région `probleme`. Pourquoi des traces courtes (arXiv 2502.12143). |
| 3 | Vérifier une réponse | `CodeExplique symbole="extraire_nombre"`. La récompense vérifiable. |
| 4 | Apprendre les traces | `CourbeEntrainement nom="sft-1.9"`, `BlocCommande` de `PROBLEMES_1_9` et `SFT_1_9`. |
| 5 | Le groupe et l'avantage | Pari `muet`, `FigureGroupe`, `CodeExplique` région `avantages`. |
| 6 | Le contrôle de départ | Pari `controle`, puis `ControleDepart`. Le RL n'amplifie que ce qui existe (« méthodes », §4.4 ; échec à 135 M, arXiv 2606.22189). |
| 7 | Le RL de ton IA | Pari `rl`, `CourbeRecompense`, `CodeExplique` région `pas-grpo`, `BlocCommande` de `GRPO_1_9`. |
| 8 | Ce qu'elle sait faire maintenant | Pari `mgsm`, `TableauEtape` (1.8, traces, 1.9 ; `problemes`, `mgsm_fr`, `gsm8k_platinum_fr`). nanochat d20 en repère honnête. |
| 9 | Chez un grand labo | `EncadreLabo` : Tülu 3 RLVR, DeepSeek-R1-Zero, le coût de R1 « selon la presse », TinyZero. |
| 10 | Le projet | `CodeExplique` région `test-grpo`, `RecupererProjet projet="1.9-raisonnement"`, « À suivre » vers 1.10. |

**Acquis :** `pensee`, `verifier`, `traces`, `avantage`, `signal`, `controle`, `rl`.

**Défi :** trouver une graine dont le problème de difficulté 3 de la famille `achats` a une réponse au-dessus de 100. L'atelier le vérifie.

- [ ] **Étape 1 : tests rouges.** Comme en tâche 5, plus :
  - les deux cas du contrôle fabriqués (lancé, pas lancé) : la page change d'étape 7, gardée par `exiger`, sans phrase qui promette un gain ;
  - la figure aux bornes (p de 0 et 100 %, n de 1 à 64) ;
  - l'atelier égal au jumeau pour 30 combinaisons.
- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire**, sources relues.
- [ ] **Étape 4 : tout vérifier**, captures et relecture.
- [ ] **Étape 5 : commit**, « Chapitre 1.9 : le faire raisonner, avec l'atelier des problèmes et le groupe sans signal (brouillon) ».

### Tâche 8 : le projet 1.10 « code », son notebook et ses jumeaux

**Fichiers :**

- Créer : `projets/1.10-code/` (paquet `code_pas_a_pas` : `bac_a_sable.py`, `passk.py`, `trou.py`, `resumer.py`, `attendus.py`, `__main__.py` ; tests)
- Créer : `notebooks/1.10-code.ipynb`
- Créer : `site/src/lib/partie-1/passk.ts`, `fim.ts` (+ tests) ; modifier `parite.ts`, `fichiers.ts`

**Interfaces :**

- `bac_a_sable.py`, région `essais` : `essais_du_bac_a_sable(delai: float = 2.0) -> list[dict]`. Six programmes passent par `forge.code.execution.executer` : réussi, assertion fausse, boucle infinie, processus enfant, 2 Go de mémoire, 1 Mo d'affichage. Il rend, pour chacun : raison, secondes, processus restants (psutil). Sorties `sorties/bac-a-sable.txt` et `mesures/bac-a-sable.json`, avec le système (`sys.platform`) : relevé sous Windows sur ce PC ; le chapitre dit que Linux passe par d'autres limites.
- `passk.py`, région `passk` : `pass_a_k_a_la_main(n, c, k) -> float` par `math.comb`, égal à `forge.code.passk.pass_a_k` à 10⁻¹² près.
- `trou.py`, région `trou` : `decouper(code: str, debut: int, fin: int) -> tuple[str, str, str]` (en points de code) et `disposition_psm(code, debut, fin) -> list[dict]` (les morceaux dans l'ordre PSM, avec leurs jetons spéciaux).
- `resumer.py` :
  - `resumer_etape` ;
  - `versions(rapports: list[Path]) -> dict` → `mesures/versions.json` : les mesures communes de 1.5 à 1.10, une colonne par version ;
  - `trous_de_ton_ia(modele: Path, cas: Path, n: int = 6) -> list[dict]` → `sorties/trous-ton-ia.json` (au moins 6 trous d'une ligne et ce que ton IA y a écrit) ;
  - `exemples_humaneval_fr(rapport: Path, n: int = 6) -> list[dict]` → `sorties/humaneval-fr-ton-ia.json`.
- `attendus.py` : `pass_a_k` sur une grille (n de 1 à 30, tous les c et k) ; `decouper` et `disposition_psm` sur 8 cas, dont un emoji et des accents.
- `passk.ts` : `passAK(n, c, k)`, traduction exacte de `forge.code.passk.pass_a_k` (même boucle, même ordre). `fim.ts` : `decouper`, `dispositionPsm`.

- [ ] **Étape 1 : tests rouges** : égalités à forge, les six essais (raisons attendues ; aucun processus restant), `test_resumer.py`, `test_attendus_a_jour`, `test_notebook.py`.
- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire le paquet, les attendus et le notebook.**
  - **Le notebook** : 1. exécuter du code dans un sous-processus limité (sur Colab, sous Linux) ; 2. ce que la limite n'empêche pas ; 3. pass@k ; 4. un trou dans le code, l'ordre PSM. La section ton-ia-1.10 vient à la tâche 14.
  - **L'exercice** : écrire `pass_a_1(resultats)`. « Défi réussi » s'il égale `pass_a_k(n, c, 1)`.
- [ ] **Étape 4 : relever** `essais` sur le processeur. **Les jumeaux et leur parité.**
- [ ] **Étape 5 : vérifier, rejouer**, commit « Projet 1.10 : le bac à sable et ses limites, pass@k et le trou dans le code, avec leurs jumeaux ».

### Tâche 9 : le chapitre 1.10 « Le faire coder », en brouillon

**Fichiers :**

- Créer : `site/src/components/chapitres/1-10/OuvertureCode.astro`, `AtelierTrou.svelte`, `PhrasePassK.svelte`, `TableauBacASable.astro`, `TableauVersions.astro`
- Créer : `paris-1-10.ts`, `sources-1-10.ts` (+ tests), `site/src/brouillons/chapitres/1-10.mdx`, `site/e2e/chapitre-1-10.spec.ts`

**Interfaces :**

- `OuvertureCode.astro` : un problème de HumanEval-FR, le code écrit par ton-ia-1.10, et le verdict de son exécution (`sorties/humaneval-fr-ton-ia.json`).
- `AtelierTrou.svelte` : un extrait de code Python parmi les cas des attendus. Le lecteur choisit le début et la fin du trou par deux `NombreManipulable`, en lignes ; la disposition PSM s'affiche par `dispositionPsm`. Pour les trous de `trous-ton-ia.json`, le bouton « Ce qu'a écrit ton IA » montre sa réponse, juste ou non.
- `PhrasePassK.svelte` : n, c et k manipulables dans la phrase « Sur [n] essais, [c] passent les tests : pass@[k] vaut {x} % ». Les combinaisons impossibles ne se proposent pas (c ≤ n, k ≤ n).
- `TableauBacASable.astro` : les six essais (ce qui a été arrêté, en combien de temps), puis ce qui n'est pas empêché (réseau, fichiers de l'utilisateur), sans les mots interdits.
- `TableauVersions.astro` : `mesures/versions.json`, ton IA de 1.5 à 1.10, sur les mêmes tests.
- `paris-1-10.ts` :
  - `choixPassK()` : « 20 essais, 2 justes : pass@10 vaut à peu près… » ; 10 %, la valeur calculée par `passAK` arrondie au pour cent, 100 % ;
  - `choixBoucle()` : « Une boucle infinie dans le code de ton IA… » ; bloque l'évaluation, est arrêtée au bout du délai (juste, d'après `bac-a-sable.json`), fait planter le PC ;
  - `choixOrdre()` : « Pour remplir un trou, ton IA lit… » ; le début seulement, le début puis la fin avant d'écrire le milieu (juste, d'après `dispositionPsm`), la fin seulement ;
  - `choixLangueEnonce()` : « Ton IA 1.10 réussit-elle mieux avec l'énoncé en anglais ou en français ? » ; par `humaneval` et `humaneval_fr` (pass@1, mode conversation) ; « pareil » si l'écart est sous la marge à 95 % de forge.

| Étape | Titre | Contenu imposé |
| --- | --- | --- |
| 1 | Du code qui tourne | `OuvertureCode`. Seul le test d'exécution tranche. |
| 2 | Exécuter sans tout risquer | Pari `boucle`, `TableauBacASable`, `CodeExplique symbole="executer"`. « Limité », et pourquoi (objet Job, nanochat le dit aussi). |
| 3 | Mesurer : pass@k | Pari `passk`, `PhrasePassK`, `CodeExplique` région `passk` (Codex, arXiv 2107.03374, relu). |
| 4 | Remplir un trou | Pari `ordre`, `AtelierTrou` sous `Verrou`, `CodeExplique symbole="exemple_fim"`. FIM arrive à l'affinage, pas au pré-entraînement : ce que cela coûte. |
| 5 | Des consignes en français | La traduction maison (Qwen3-4B, sa licence, ses contrôles, la réexécution des tests), HumanEval-FR. Lien vers l'annuaire. |
| 6 | L'affinage du code | `CourbeEntrainement nom="sft-1.10"`, `BlocCommande` de `TRADUIRE_1_10` et `CODE_1_10`. |
| 7 | Ce qu'elle sait faire maintenant | Pari `langue`, `TableauEtape` (1.9, 1.10 ; `humaneval`, `humaneval_fr`, `fim_ligne`). |
| 8 | Ton IA, de 1.5 à 1.10 | `TableauVersions`. Ce que l'affinage a appris, et ce qu'il n'a pas pu apprendre. |
| 9 | Chez un grand labo | `EncadreLabo` : Qwen2.5-Coder 0.5B (et l'écart de données), Llama 3, Codex, nanochat d20. |
| 10 | Le projet | `CodeExplique` région `essais`, `RecupererProjet projet="1.10-code"`, « À suivre » vers 1.11 (« à venir » tant qu'il n'a pas paru). |

**Acquis :** `execution`, `limites`, `passk`, `trou`, `traduction`, `versions`.

**Défi :** trouver dans la phrase n et c tels que pass@1 soit sous 20 % et pass@10 au-dessus de 80 %. La phrase le vérifie.

- [ ] **Étape 1 : tests rouges.** Comme en tâche 5, plus :
  - « Partie 1, chapitre 1.10 sur 21 » ;
  - aucune occurrence de « sûr », « sans danger » ni « garanti » dans la page ;
  - la phrase de pass@k aux bornes, jamais `NaN` ;
  - l'atelier égal au jumeau pour les 8 cas, emoji compris ;
  - trois jeux de rapports fabriqués (anglais mieux, français mieux, pareil) et des scores à 0 % : les phrases des étapes 7 et 8 suivent, gardées par `exiger` (point à surveiller 5).
- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire**, sources relues.
- [ ] **Étape 4 : tout vérifier**, captures et relecture.
- [ ] **Étape 5 : commit**, « Chapitre 1.10 : le faire coder, avec le bac à sable, pass@k et le trou dans le code (brouillon) ».

### Tâche 10 : le glossaire et l'annuaire complétés

**Fichiers :** modifier `site/src/lib/annexes/glossaire.ts`, `annuaire.ts` (+ tests), `site/src/pages/annexes/annuaire.astro`, `site/e2e/annexes.spec.ts`.

**Interfaces :**

- Glossaire, au moins ces 22 termes, chacun relu dans son chapitre :
  - `affinage-supervise`, `gabarit-de-conversation`, `jeton-special`, `masque-de-perte`, `empaquetage`, `masque-d-attention`, `oubli`, `decontamination` (1.7) ;
  - `preference`, `paire-de-preferences`, `dpo`, `modele-de-reference`, `beta` (1.8) ;
  - `recompense-verifiable`, `apprentissage-par-renforcement`, `grpo`, `avantage`, `trace-de-raisonnement` (1.9) ;
  - `pass-a-k`, `remplissage-au-milieu`, `bac-a-sable` (1.10) ;
  - `cache-cle-valeur` (1.9).
  Leur lien dit « à venir » tant que le chapitre n'a pas paru.
- Annuaire :
  - `Groupe` gagne `'affinage'` (« Pour affiner ton IA »). Fiches : Luth-2 SFT, Aya, OASST2, `opc-sft-stage2` (`educational_instruct`) et les consignes de code traduites (`donnees-ton-ia-2`) ;
  - le groupe `evaluation` gagne IFEval-FR, MGSM-rev2 (« évaluation seulement : CC BY-SA »), GSM8K-Platinum-fr (traduction non documentée), HumanEval et HumanEval-FR ;
  - `NOTES` gagne « Écartés pour la vague 2 », un par jeu, avec sa raison : Community Alignment français (Llama 3.3, clause 1.b.i), French Alpaca et OpenHermes-fr (sorties d'OpenAI), `french_instruct` (sources NC), Magicoder (gpt-3.5) ;
  - `interface FicheModele { id; nom; url; role: string; licence: LienDeLicence | null; version: string | null; releveLe; source }` et `MODELES` : `Qwen/Qwen3-4B` (traducteur, licence et révision de la tâche 20 du plan 7), puis chaque Release de ton IA parue (lien, et la licence que dit sa fiche) ;
  - `interface FicheOutil { id; nom; url; role; licence; releveLe; source }` et `OUTILS` : PyTorch, `datasets`, `safetensors`, `transformers` (utilisés), TRL et nanochat (lus comme références, pas utilisés), chacun avec sa licence relevée sur sa page ;
  - la page de l'annuaire gagne les sections « Modèles » et « Outils », en tableaux typographiés, en blocs de définitions sur mobile.
- Les fiches de jeux d'affinage n'entrent qu'avec la tâche du plan 7 qui les utilise ; une Release de ton IA n'entre dans `MODELES` qu'à la parution de son chapitre (tâches 11 à 14).

- [ ] **Étape 1 : tests rouges** : unicité et ordre du glossaire (tests existants) ; chaque nom de `SOURCES_CONVERSATIONS` de forge (texte de `sources.py` lu sans import) a sa fiche ou une note d'écart, avec la même licence ; chaque fiche a une URL https, un `releveLe` au format `AAAA-MM-JJ` et une source ; e2e : les deux sections nouvelles, axe, 390 px.
- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire.** Chaque licence est relue sur la page du jeu, du modèle ou de l'outil, le jour même.
- [ ] **Étape 4 : tout vérifier**, captures face à la maquette des annexes.
- [ ] **Étape 5 : commit**, « Annexes : glossaire de la vague 2, annuaire des jeux d'affinage, des modèles et des outils », puis poussée (contrôleur) : `/forge-ia/annexes/annuaire/` répond 200.

### Tâche 11 : ton IA 1.7 dans son chapitre, et la parution de 1.7

**Conditions :** la Release `ton-ia-1.7` est publiée (plan 7, tâche 12) ; les tâches 1 à 3 sont faites ; carte libre et « go ».

**Fichiers :** modifier `projets/1.7-conversation/mesures/*` (écrits par le projet), `notebooks/1.7-conversation.ipynb`, `tests/test_notebook.py`, `site/src/brouillons/chapitres/1-7.mdx`, `site/e2e/chapitre-1-7.spec.ts`, `outils/versions-publiees.txt`, `site/src/lib/annexes/annuaire.ts` (`MODELES`).

- [ ] **Étape 1 : les fichiers de ton IA**, sur le processeur, en lecture seule de `D:\forge-ia-donnees` :
  - `resumer` des rapports `evaluations\ton-ia-1.5-1.7`, `ton-ia-1.7-1.7` et `ton-ia-1.7-court-1.7` ;
  - `courbe` du journal de `sft-1.7` et de `sft-1.7-court` ;
  - `longueurs` du jeu `affinage\sft-1.7`.
  Les nombres doivent concorder avec `docs/mesures/ton-ia-1.7.md`. Un écart se dit, et ne se corrige pas dans le document.
- [ ] **Étape 2 : le notebook.** Une section 6, « Parle à ton IA 1.7 » : `telecharger_publication("ton-ia-1.7")`, `charger_publication`, trois questions et leurs réponses par `repondre_lot` sur le processeur (128 jetons au plus). Le test passe `FORGE_IA_MODELES` vers un modèle minuscule publié ; une coupure simulée du téléchargement est reprise (point à surveiller 4). Ajouter `ton-ia-1.7` à `outils/versions-publiees.txt`.
- [ ] **Étape 3 : la carte.** `uv sync --extra gpu --offline`, puis `uv run --extra gpu pytest -q -rs` dans le projet : aucun test `gpu` sauté, et le notebook a tourné sur la carte (il le dit). Puis retour à `--extra cpu`.
- [ ] **Étape 4 : le chapitre.** Le parcours attend zéro `[data-a-mesurer]`. Chaque phrase sur ton IA 1.7 est gardée par `exiger` ; le relecteur la vérifie contre les fichiers.
- [ ] **Étape 5 : tout vérifier** (Vitest, Svelte, Astro, parcours, pytest du projet, notebook dans `.colab` avec `FORGE_IA_MODELES`), puis commit « Ton IA 1.7 dans le chapitre 1.7 ».
- [ ] **Étape 6 : parution (contrôleur).** `git mv` vers `content/`, commentaires « à venir » relus, `npm run build`, garde-fous, commit « Parution du chapitre 1.7 », poussée. Workflows Site et Python verts, `notebooks-colab` compris ; `/forge-ia/partie-1/1-7/` répond 200.

### Tâche 12 : ton IA 1.8 dans son chapitre, et la parution de 1.8

**Conditions :** Release `ton-ia-1.8` (plan 7, tâche 15) ; tâches 4 et 5 faites.

- [ ] **Étape 1 : les fichiers.** `resumer` (rapports de 1.7 et 1.8 à l'étape 1.8, et de la version courte), `paires_exemples`, `balayage`, `courbes_dpo`.
- [ ] **Étape 2 : le notebook.** Une section « Ton IA 1.8 face aux consignes » : trois invites contraintes, la réponse de ton-ia-1.8 et sa note, sur le processeur. Ajouter `ton-ia-1.8` à `versions-publiees.txt`.
- [ ] **Étapes 3 à 6 :** comme en tâche 11 (carte, chapitre sans `[data-a-mesurer]`, vérifications, commit « Ton IA 1.8 dans le chapitre 1.8 », parution, `/forge-ia/partie-1/1-8/` en 200).

### Tâche 13 : ton IA 1.9 dans son chapitre, et la parution de 1.9

**Conditions :** Release `ton-ia-1.9` (plan 7, tâche 17) ; tâches 6 et 7 faites.

- [ ] **Étape 1 : les fichiers.** `resumer` (rapports de 1.8, des traces, de 1.9 et des versions courtes à l'étape 1.9), `controle`, `courbes_grpo` (ou `lance: false`), la courbe de `sft-1.9`.
- [ ] **Étape 2 : le notebook.** Une section « Ton IA 1.9 résout cinq problèmes » : réponses avec leur pensée, vérifiées, sur le processeur. Ajouter `ton-ia-1.9` à `versions-publiees.txt`.
- [ ] **Étapes 3 à 6 :** comme en tâche 11. Si le RL n'a pas été lancé, le chapitre le montre (étape 6 de son tableau). Le relecteur vérifie qu'aucune phrase ne le cache. `/forge-ia/partie-1/1-9/` en 200.

### Tâche 14 : ton IA 1.10 dans son chapitre, et la parution de 1.10

**Conditions :** Releases `ton-ia-1.10` et `donnees-ton-ia-2` (plan 7, tâches 20 et 22) ; tâches 8 et 9 faites.

- [ ] **Étape 1 : les fichiers.** `resumer` (1.9 et 1.10 à l'étape 1.10, la version courte), la courbe de `sft-1.10`, `versions` (les rapports d'étape 1.10 de toutes les versions), `trous_de_ton_ia`, `exemples_humaneval_fr`. Les deux derniers demandent la carte ou 20 min de processeur : le dire au rapport.
- [ ] **Étape 2 : le notebook.** Une section « Ton IA 1.10 écrit une fonction » : un problème de HumanEval-FR (téléchargé de `donnees-ton-ia-2`), la réponse de ton IA, exécutée par `executer`. Ajouter `ton-ia-1.10` et `donnees-ton-ia-2` à `versions-publiees.txt`.
- [ ] **Étapes 3 à 6 :** comme en tâche 11. `/forge-ia/partie-1/1-10/` en 200, et 1.10 vient après 1.9 sur l'accueil du site publié (point à surveiller 1).

### Tâche 15 : le bilan de la vague 2

- [ ] **Étape 1 : tout vérifier**, en notant les durées : pytest de chaque `projets/1.(7|8|9|10)-*` (`--extra cpu`) et de forge, le site entier, `npm run build` sans essais et les garde-fous de `site.yml`, et `executer_notebooks.py` dans `.colab` sur tous les notebooks. Si un job approche son délai, le porter plus haut, et le dire.
- [ ] **Étape 2 : les README.** Chaque projet : ce qu'il fait et le chapitre qu'il accompagne, les commandes PowerShell (et Linux quand elles diffèrent), ce qu'il prend à forge, les régions que le chapitre montre, les fichiers de `mesures/` et `sorties/` (d'où ils viennent, quand ils ont été relevés). Le README racine liste les quatre projets.
- [ ] **Étape 3 : relire 1.7 à 1.10 d'un bout à l'autre**, comme un débutant qui sort de 1.6 :
  - chaque terme est expliqué avant d'être utilisé, et il est dans le glossaire ;
  - chaque chapitre annonce le suivant ;
  - aucune affirmation datée n'est sans source ;
  - les résultats décevants sont dits.
  Corriger par des commits séparés ; un chapitre paru se corrige puis se repousse.
- [ ] **Étape 4 : commit**, « Vague 2 : README des projets et bilan ».
- [ ] **Étape 5 (contrôleur) :**
  - le jalon dans la mémoire partagée, si elle répond : « Projet forge-ia (La Forge IA) : vague 2 finie. Chapitres 1.7 à 1.10 publiés le JJ/MM/AAAA, avec leurs projets (projets/1.7-conversation à 1.10-code), leurs notebooks et les Releases ton-ia-1.7 à ton-ia-1.10 ; glossaire et annuaire complétés. » ;
  - le compte rendu : les adresses, les chiffres de ton IA de 1.5 à 1.10, les durées réelles, les écarts trouvés en route ;
  - la demande de validation de la vague 2 à l'utilisateur (spécification, section 12), par AskUserQuestion.

---

## Exécution

- **Modèles :** les tâches de projet (2, 4, 6, 8) et le socle (1) prennent un modèle standard ; les chapitres (3, 5, 7, 9) le modèle le plus capable, pour la langue et la relecture des captures ; les parutions (11 à 14) un modèle standard, tenu par le contrôleur.
- **Revue :** une relecture par tâche ; une revue finale du plan.
- **Ordre :** 1, puis chaque paire (projet, chapitre) dès que ses dépendances du plan 7 sont faites, et 10 quand la tâche 20 du plan 7 est faite. Les parutions suivent les Releases, dans l'ordre où elles arrivent.
- **Poussée :** le contrôleur pousse après chaque tâche relue ; la CI doit être verte.
