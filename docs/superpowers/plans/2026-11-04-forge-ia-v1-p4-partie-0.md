# La Forge IA, vague 1, plan 4 : la Partie 0, les bases

> **Pour les agents qui exécutent ce plan :** SOUS-SKILL REQUIS : utiliser superpowers:subagent-driven-development (recommandé) ou superpowers:executing-plans pour réaliser ce plan tâche par tâche. Les étapes utilisent des cases à cocher (`- [ ]`).

**But :** écrire les cinq chapitres de la Partie 0 (0.1 à 0.5), chacun avec sa prose complète dans le gabarit du plan 1, son projet Python testé et son notebook Colab, sans jamais utiliser la carte graphique tant que ton IA s'entraîne ; puis relever les mesures de la carte dans une tâche porte, pendant une courte pause de l'entraînement de ton IA (essai du 04/11/2026).

**Architecture :**

- **Un projet par chapitre** (`projets/0.N-<nom>/`), autonome, testé par pytest et exécuté de bout en bout dans son notebook (`notebooks/0.N-<nom>.ipynb`). Les projets 0.3, 0.4 et 0.5 utilisent PyTorch avec les extras `cpu` et `gpu` de `projets/forge`.
- **Des jumeaux TypeScript** (`site/src/lib/partie-0/`) refont dans le navigateur ce que les ateliers montrent. Le Python écrit des attendus JSON ; Vitest, et pour 0.1 et 0.2 aussi Firefox et WebKit, vérifient l'égalité exacte.
- **Les chapitres s'écrivent en brouillon** (`site/src/brouillons/chapitres/<p>-<n>.mdx`). Un brouillon n'est construit qu'avec `FORGE_ESSAIS=1`, à son adresse définitive : les parcours le testent tel qu'il paraîtra. Il paraît par un simple `git mv` vers `site/src/content/chapitres/`.
- **Les nombres viennent des fichiers** : attendus du Python, sorties réelles des commandes (`sorties/*.txt`), mesures (`mesures/*.json`). Une mesure de la carte qui manque s'affiche « à mesurer » (`[data-a-mesurer]`), et un chapitre paru ne peut en contenir aucune.

**Pile technique :** celle des plans 1 et 3 (Astro 7.4, Svelte 5.57, TypeScript, Vitest, Playwright avec `@axe-core/playwright`, svelte-check), Python 3.12 avec uv 0.13, pytest, nbclient, et PyTorch 2.15.0 (roues `cpu` maintenant, `cu132` à la porte). Aucune nouvelle dépendance npm. Aucune nouvelle dépendance Python hors PyTorch, déjà utilisé par `forge`.

**Spécification :** `docs/superpowers/specs/2026-11-02-forge-ia-design.md`, surtout les sections 2 (« on ne suppose rien »), 4 (Partie 0), 5 (gabarit), 6 (allure), 7 (cohérence des moteurs), 8 (code, projets, notebooks), 9 (honnêteté) et 11 (machine).

**Plans précédents, livrés :**

- `docs/superpowers/plans/2026-11-02-forge-ia-v1-p1-fondations.md` : gabarit, paris, verrous, `NombreManipulable`, `CodeExplique`, `LiensProjet`, chapitre pilote 1.3 et son notebook ;
- `docs/superpowers/plans/2026-11-03-forge-ia-v1-p2-moteur.md` : paquet `forge`, extras PyTorch, mesures de ton IA (`docs/mesures/entrainement-2026-11.md`) ;
- `docs/superpowers/plans/2026-11-03-forge-ia-v1-p3-demos.md` : mini-modèle, attention, calculateur, parité dans les navigateurs. Sa revue finale a laissé deux points pour ce plan, M8 (tâche 1) et M3 (tâche 13), notés dans `.superpowers/sdd/2026-11-03-forge-ia-v1-p3-demos/progress.md`.

## Place de ce plan dans la vague 1

C'est le plan 4 du découpage fixé par le plan 1 : « Partie 0 : chapitres 0.1 à 0.5, avec projets et notebooks ».

Hors de ce plan, et donc pour le plan 5 :

- les chapitres 1.1, 1.2, 1.4, 1.5 et 1.6 ;
- l'annuaire des données et le glossaire.

La parution de la Partie 0 se fait dans ce plan (choix 2).

## Recherche faite avant ce plan (le 04/11/2026)

Toutes les sources ont été lues le 04/11/2026.

- **Python.** La dernière version est 3.15.2 (25/10/2026). La série 3.15 est sortie le 09/10/2026. 3.14 reçoit encore des corrections, et 3.12 seulement des correctifs de sécurité, jusqu'en octobre 2028 (https://www.python.org/downloads/).
- **Colab, image du 03/11/2026** (dépôt officiel de l'image, https://github.com/googlecolab/backend-info, fichiers `os-info-gpu.txt` et `pip-freeze.gpu.txt`, dernier commit le 03/11/2026) :
  - Python 3.13.16 ;
  - torch 2.11.0+cu130 et torchvision 0.26.0+cu130 déjà installés, numpy 2.4.6, ipykernel 6.17.1 ;
  - l'image sans carte a torch 2.11.0+cpu.
- **La carte de Colab.**
  - Google ne nomme pas la carte de l'offre gratuite. Sa FAQ dit que les cartes « varient dans le temps », que l'accès gratuit aux cartes est « fortement restreint », et qu'une session dure au plus 12 h (https://research.google.com/colaboratory/faq.html).
  - Les utilisateurs rapportent une T4 de 16 Go, sans garantie (source secondaire : https://www.hivenet.com/post/google-colaboratory-gpu-complete-guide-to-free-cloud-gpu-access-and-limitations).
  - Capacités de calcul (https://developer.nvidia.com/cuda-gpus) : RTX 5070 Ti 12.0, T4 7.5, L4 8.9.
- **uv.** La version 0.13.7 est parue le 03/11/2026 (https://pypi.org/pypi/uv/json).
  - Installation sous Windows : `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`, ou `winget install --id=astral-sh.uv -e` (https://docs.astral.sh/uv/getting-started/installation/).
  - Pour PyTorch, le guide d'uv recommande des extras en conflit (`cpu`, `cu1xx`) reliés à leurs index. Il rappelle que PyPI sert « des roues pour processeur seul sous Windows et macOS, et des roues pour carte graphique sous Linux » (https://docs.astral.sh/uv/guides/integration/pytorch/).
- **PyTorch 2.15.0**, paru le 28/10/2026 (https://pypi.org/pypi/torch/2.15.0/json).
  - Il demande Python 3.11 ou plus, et a des roues de cp311 à cp315.
  - Sur PyPI, la roue Windows cp312 pèse 126,7 Mo, sans CUDA. La roue Linux pèse 539 Mo, avec ses dépendances `nvidia-*-cu13`.
  - L'index `https://download.pytorch.org/whl/cu132/torch/` a les roues Windows `2.15.0+cu132` de cp311 à cp315.
  - À partir de 2.15, PyTorch ne publie plus de roues CUDA 12.x : la 2.14 était la dernière (annonce de la 2.15 RC1, https://dev-discuss.pytorch.org/t/pytorch-2-15-rc1-produced-for-pytorch-torchvision-torchaudio/3464).
- **Le pilote NVIDIA.**
  - Les roues CUDA 13.x tournent avec un pilote 580 ou plus récent, par compatibilité de version mineure (notes de version de CUDA 13.4 Update 2, tableau 3 : https://docs.nvidia.com/cuda/cuda-toolkit-release-notes/index.html). La branche du pilote de CUDA 13.2 est la R595 (tableau 2).
  - Le pilote du PC, 621.01, va jusqu'à CUDA 13.5 (relevé du plan 2).
- **Plus besoin du CUDA Toolkit pour utiliser PyTorch.** Les roues embarquent leur propre CUDA : il ne faut que le pilote. Le Toolkit ne sert qu'à compiler PyTorch ou des extensions CUDA. Ce sont des réponses du forum de PyTorch, pas une page officielle (https://discuss.pytorch.org/t/is-it-required-to-set-up-cuda-on-pc-before-installing-cuda-enabled-pytorch/60181/15, https://discuss.pytorch.org/t/what-is-the-interplay-between-the-nvidia-driver-and-cuda/217811).
- **Conda.** Le canal `pytorch` d'Anaconda n'est plus mis à jour depuis la 2.5. PyTorch renvoie vers ses roues ou vers conda-forge (https://dev-discuss.pytorch.org/t/pytorch-deprecation-of-conda-nightly-builds/2590 ; issue pytorch/pytorch#138506, citée par https://github.com/pytorch/tutorials/pull/3864).
- **Ce qui rend faux d'anciens tutoriels**, à dire dans 0.3 :
  - « installe le CUDA Toolkit » : inutile ;
  - « `conda install pytorch -c pytorch` » : canal figé à 2.5 ;
  - « `pip install torch` » sous Windows : on obtient la version pour processeur seul ;
  - « `--index-url …/cu118` ou `cu121` » : ces versions ne connaissent pas les cartes RTX 50 (Blackwell, sm_120), et PyTorch 2.15 ne publie plus aucune roue CUDA 12.x.
- **Vérifier la carte :**
  - `nvidia-smi` donne le pilote, et la version de CUDA la plus haute qu'il accepte ;
  - côté PyTorch : `torch.cuda.is_available()`, `torch.version.cuda` (`None` pour une roue sans CUDA), `torch.cuda.get_device_name(0)`, `torch.cuda.get_device_capability(0)` et `torch.cuda.get_arch_list()`.
- **Déjà mesuré sur ce PC** (`docs/mesures/entrainement-2026-11.md`, 03/11/2026), et donc citable tel quel :
  - la carte entraîne ton IA de 76 à 81 fois plus vite que le processeur (17 855 contre 235 jetons par seconde pour « tres_grand ») ;
  - les 16 fils du processeur travaillaient à 100 %, et PyTorch n'en aurait pris que 8 sans réglage ;
  - Windows garde 1,5 Go de la carte au repos ;
  - `torch.compile` n'a pas `triton` sous Windows.
- **Données sourcées déjà dans le dépôt**, relevées le 03/11/2026 et réutilisées par les encadrés « labo » : `site/src/lib/calculateur/donnees.ts` (cartes `rtx-5070-ti`, `t4`, `h100-sxm`…, modèles publics GPT-3 et Llama 3, efficacités) et `site/src/lib/calculateur/ton-ia.ts` (tailles et débits de ton IA).

## Choix de ce plan

1. **Brouillons, puis parution par `git mv`.** Un chapitre s'écrit dans `site/src/brouillons/chapitres/<p>-<n>.mdx`, au même niveau de dossiers que `site/src/content/chapitres/` : ses imports relatifs ne changent pas quand il paraît. Il n'est construit qu'avec `FORGE_ESSAIS=1`, à son adresse définitive et hors de la recherche. Rien d'inachevé ne peut donc paraître, et les parcours testent la vraie page.
2. **Parution chapitre par chapitre, sans validation Colab par l'utilisateur** (décision de l'utilisateur du 04/11/2026, reportée dans la spécification, section 8).
   - L'utilisateur ne lance aucun notebook. Chaque notebook est exécuté automatiquement :
     - par le `test_notebook.py` de son projet (Python 3.12, PyTorch 2.15, sous Linux et Windows) ;
     - par le job `notebooks-colab` de `python.yml` (tâche 2), qui reproduit l'image de Colab sans carte : Python 3.13, `torch==2.11.0+cpu`, `numpy==2.4.6` ;
     - et, pour 0.3 à 0.5, sur la RTX 5070 Ti à la porte (tâche 16).
   - 0.1 et 0.2 paraissent dès qu'ils sont finis et relus, et que leur notebook passe : c'est l'étape « parution » ajoutée à la fin de la tâche 7. 0.3 à 0.5 paraissent après la porte (tâche 16, étape « parution »).
   - Avant chaque poussée, le contrôleur pose une seule question à l'utilisateur (AskUserQuestion) : « 0.x et 0.y sont prêts. Je pousse et je les publie ? ». Sans oui, rien n'est poussé.
   - L'utilisateur signale les problèmes qu'il rencontre à l'usage ; ils sont corrigés comme des retours de relecture.
3. **Un projet autonome par chapitre**, avec ses propres tests et son verrou `uv.lock`. Un lecteur peut n'en télécharger qu'un. Les rares fichiers partagés sont copiés, et un test garde chaque copie identique à l'original :
   - le texte de 0.1 est celui du corpus de 1.3 ;
   - `appareil.py` de 0.4 et 0.5 vient de 0.3 ;
   - le générateur `Hasard` de 0.2 est celui du mini-modèle.
4. **PyTorch dans 0.3, 0.4 et 0.5 :** le motif de `projets/forge`.
   - Extras en conflit `cpu` et `gpu`, `torch==2.15.0`, index `cpu` et `cu132`.
   - Un fichier `.python-version` à `3.12` : la roue `cu132` cp312 est déjà dans le cache d'uv (`D:\forge-ia-donnees\cache\uv`, via `outils/env-forge.ps1`), donc aucun nouveau téléchargement de plusieurs Go.
   - Les tâches n'installent que `--extra cpu`, environ 130 Mo. L'intégration continue choisit déjà `--extra cpu` pour tout projet qui déclare cet extra (`.github/workflows/python.yml`).
   - L'extra `gpu` ne s'installe qu'à la porte, avec `--offline`, pour prouver qu'il vient du cache.
5. **Les notebooks n'installent jamais PyTorch :** ils prennent celui de Colab (2.11.0+cu130 au 03/11/2026). Ils n'utilisent que des fonctions de PyTorch présentes depuis la 2.4 au moins, et tournent aussi sans carte, en disant sur quoi ils ont tourné.
6. **Le choix de l'appareil** : `choisir_appareil()` suit la variable `FORGE_APPAREIL` (`auto`, `cpu` ou `cuda`), sinon prend la carte si PyTorch la voit, sinon le processeur. MPS (Mac) n'est pas proposé, car rien n'est testé sur Mac, et le chapitre 0.3 le dit.
7. **0.1, un fil conducteur : « le mot suivant ».** Compter quel mot suit quel autre dans un texte fait pratiquer exactement le Python des projets du site : texte, listes, tranches, `zip`, dictionnaires et `Counter`, `min` avec `key`, fonctions annotées, `NamedTuple`, `pathlib`, `uv run` et pytest. Rien d'autre : ni héritage, ni décorateurs, ni `async`, ni numpy ou pandas.
8. **0.2, trois figures manipulables à jumeau exact** :
   - vecteurs et produit scalaire ;
   - pente et descente ;
   - probabilités et tirages.

   Les entrées sont choisies pour que le calcul soit identique au bit près en JavaScript et en Python : entiers, demi-entiers, et seulement `+ − × ÷` et la racine carrée. Les matrices ont un exemple calculé à la construction ; leurs formes se manipulent en 0.4. Softmax et −ln p ont besoin d'`exp` et de `log`, qui ne sont pas reproductibles : leurs valeurs viennent seulement de la sortie du Python.
9. **0.3, sans îlot.** L'atelier, c'est le terminal du lecteur et le script `python -m poste`.
   - Son diagnostic est une fonction pure, `diagnostiquer(faits)`, testée sur des situations nommées. Les paris lisent ses attendus.
   - Les commandes affichées viennent de `commandes.ts`, vérifiées contre `pyproject.toml`.
   - Les sorties montrées sont réelles, enregistrées par le script lui-même.
10. **0.4, l'atelier des formes** (diffusion et produit matriciel). Son jumeau est vérifié contre PyTorch lui-même, sur toutes les formes de 1 à 3 dimensions de tailles 1 à 3. Les chronos viennent de `mesures/*.json`.
11. **0.5, le OU exclusif.**
    - D'abord un neurone à seuil, manipulable, qui ne peut pas classer le OU exclusif.
    - Puis un réseau 2-2-1 à sigmoïdes, entraîné à la main en Python pur avec l'erreur de 0.2.
    - Puis le même réseau dans PyTorch, en float64, avec les mêmes poids de départ : mêmes gradients à 10⁻¹² près.
    - Enfin l'avant-goût du mini-modèle, avec les prénoms du départ et de la fin côte à côte (M3).
12. **Égalité exacte (spécification, section 7)** :
    - les jumeaux de 0.1, 0.2, 0.4 et 0.5 sont comparés aux attendus du Python dans Vitest ;
    - ceux de 0.1 (minuscules Unicode) et de 0.2 (flottants) le sont aussi dans Firefox et WebKit, sur une seconde page de parité ;
    - 0.3, l'entraînement du OU exclusif et softmax ne sont pas recalculés dans le navigateur : la page lit la sortie du Python, et la règle ne s'applique pas.
13. **Mesures.**
    - Le processeur est mesuré pendant les tâches. Pour 0.4, ces chronos sont provisoires, et remesurés à la porte, machine au repos.
    - La carte n'est mesurée qu'à la porte (tâche 16).
    - Tant qu'une mesure manque, la page affiche « à mesurer » avec `data-a-mesurer`. Un parcours interdit tout `data-a-mesurer` dans un chapitre paru.
14. **M8 d'abord** : les classes partagées `.bouton-relief` et `.bascule-soleil`, le composant `ZoneDefilable.svelte` et `exigeur()`. Aucune différence visuelle, prouvée au pixel près par des captures temporaires avant et après.
15. **Les encadrés « labo »** réutilisent les données sourcées du calculateur et les mesures du plan 2. Un chiffre nouveau demande une recherche web dans la tâche, avec son lien et sa date.
16. **Pas de résumé sous les chapitres de la Partie 0** sur sa page de partie. La maquette validée n'en met qu'à la Partie 1, et `parcours.test.ts` le vérifie.
17. **Pas de bibliothèque de formules** (ni KaTeX ni MathJax). Les formules s'écrivent en texte, avec ×, −, ², √ et des indices en toutes lettres.
18. **Les caractères invisibles sont cherchés par un test permanent** (tâche 2), sur tous les fichiers de ce plan.

## Écarts assumés avec la spécification

- **« Lancé en entier sur la RTX 5070 Ti » :** les projets 0.1 et 0.2 n'utilisent pas la carte. Ils sont lancés en entier sur ce PC, et c'est tout ce que la règle peut vouloir dire pour eux. 0.3, 0.4 et 0.5 passent sur la carte à la porte (tâche 16).
- **Copies de fichiers entre projets** (choix 3) : la spécification veut une seule source pour les extraits du site, pas pour les projets. Chaque copie est gardée identique par un test.
- **« Exécuté de bout en bout sur l'offre gratuite de Colab » :** la spécification a été modifiée le 04/11/2026 (choix 2). Le job `notebooks-colab` reproduit le logiciel de Colab, pas sa machine : la carte de Colab (souvent une T4) n'est pas testée, et le chapitre 0.3 le dit.

## Contraintes globales

- **Langue et typographie.**
  - Tout texte visible est en français, au tutoiement, sans capitales hors début de phrase et noms propres.
  - Espace fine insécable U+202F devant `; : ! ? %` et à l'intérieur des guillemets « ».
  - Milliers séparés par U+202F (`nombre()` de `site/src/lib/nombres.ts`), décimales par une virgule, apostrophe courbe U+2019.
  - Où écrire l'espace fine :
    - dans Svelte et TypeScript, `\u202F` ;
    - dans Astro, `typographier()` ;
    - dans un MDX, le plugin remark s'en charge devant `; : ! ?` et dans les guillemets ; un nombre avec milliers ou un pourcentage s'écrit `{nombre(x)}`, `{pourcent(f)}` ou avec `&#8239;` ;
    - en Python, `"\u202f"`.
- **Caractères invisibles.** Aucun U+00A0, U+202F, U+2009, U+200B, U+200C, U+200D, U+2060 ni U+FEFF littéral dans les fichiers de code de ce plan : seulement leurs échappements. Les cellules Markdown des notebooks peuvent contenir U+202F, comme celui de 1.3. Le test `site/src/lib/invisibles.test.ts` (tâche 2) le vérifie. L'outil d'écriture des agents tend à changer `\u202F` en caractère littéral : relancer ce test avant chaque commit.
- **Couleurs et polices :** les variables de `site/src/styles/jetons.css`, jamais de couleur en dur. Gabarito pour les titres et les chiffres, Newsreader pour le texte, JetBrains Mono pour le code.
- **Le jaune soleil est réservé à ce qui se manipule.** Menthe et corail disent seulement juste ou faux.
- **Interdits :**
  - étiquettes en capitales espacées, méta-informations séparées par des points médians, « → » collé aux boutons ;
  - emojis, encadrés à bordure gauche colorée, dégradés ;
  - cartes arrondies identiques avec ombre douce, animations d'entrée ;
  - toute bibliothèque de graphiques : SVG et CSS dessinés à la main ;
  - les tuiles de « tableau de bord » : les nombres vivent dans des phrases ou des tableaux typographiés ;
  - tout ce qui fait « site fait par IA ». Avant chaque relecture de captures, relire `C:\Users\chipat\.claude\projects\d--creation-ia\memory\forge-ia-direction-visuelle.md` et `eviter-style-fait-par-ia.md`.
- **Mouvement :** seulement en réponse à une action du lecteur. Sous `prefers-reduced-motion: reduce`, rien ne glisse.
- **Plancher de qualité.**
  - Aucun débordement à 390 px.
  - Focus visible, zéro violation axe (wcag2a, wcag2aa), contraste AA.
  - Cibles d'au moins 24 px.
  - Statuts annoncés par `role="status"`, sans prendre le focus, et seulement aux moments qui comptent.
  - Lignes de prose de 80 caractères au plus (`plusLongueLigne`).
  - Sans JavaScript, tout le texte et les valeurs de départ restent lisibles.
- **Chiffres et sources.** Aucun nombre calculé ou mesuré n'est tapé à la main dans un MDX : il vient d'un import (jumeau, attendus, sorties, mesures, données du calculateur). Chaque chiffre de matériel, de prix ou de modèle a son URL et sa date de relevé.
- **Code des pages.** Tout extrait de code multiligne vient d'un fichier testé, par `CodeExplique` et ses marqueurs `# region: <nom>` / `# fin: <nom>`. Les commandes d'une ligne viennent de `site/src/lib/partie-0/commandes.ts`.
- **Jumeaux exacts.**
  - Le Python s'écrit d'abord ; le TypeScript le traduit, avec les mêmes fonctions et le même ordre d'opérations.
  - Dans une fonction jumelle à flottants, pas de `sum()` (sommation compensée depuis Python 3.12) : une boucle, ou `itertools.accumulate`. Pas de `**`, ni `exp`, `log`, `pow`, `max`, `min` sur des flottants.
  - Les attendus s'écrivent avec `json.dumps(…, ensure_ascii=False, allow_nan=False, indent=1)` et `newline="\n"`. Les listes ordonnées s'écrivent en tableaux JSON, jamais en objets.
  - Vitest compare avec `toStrictEqual`, flottants compris.
- **La carte graphique est occupée** jusqu'à la fin de l'entraînement principal de ton IA (environ le 9 ou le 10/11/2026), et l'utilisateur joue sur ce PC.
  - Jusqu'à la tâche 16, aucune tâche n'utilise la carte : uv seulement avec `--extra cpu`, aucun contexte CUDA, aucun WebGPU ni WebGL.
  - `nvidia-smi` en lecture seule reste permis, comme pour le chien de garde du plan 2.
  - Chrome est lancé par Playwright avec `--disable-gpu`, et les parcours tournent avec `--workers=4`.
- **Go et stop.** Tout travail lourd (tests, constructions, parcours, mesures) se fait seulement entre un « go » et un « stop » de l'utilisateur. Au « stop », le contrôleur arrête l'agent en cours ; la tâche reprend à sa dernière étape cochée. Aucune tâche ne dépasse 30 minutes de calcul : la règle de l'essai chronométré carte contre processeur ne s'applique pas.
- **Fichiers interdits :** ne jamais modifier `projets/forge` ni `D:\forge-ia-donnees`. Le cache uv `D:\forge-ia-donnees\cache\uv`, chargé par `. .\outils\env-forge.ps1`, est permis.
- **Ports :** 8530 (Astro, dev et aperçu) et 8531 (Playwright), déjà réglés. Aucun nouveau port.
- **Commits.**
  - Sur `main`, jamais de push.
  - Message en français, terminé par `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
  - Toujours `git add <fichiers de la tâche>`, puis `git commit -m "…" -- <les mêmes fichiers>`.
  - Fins de ligne LF (`.gitattributes` existe) ; le Python écrit avec `newline="\n"`.
- **Noms et commentaires en français.** Les messages d'erreur disent quoi faire ensuite.
- **Commandes PowerShell.**
  - Python sans PyTorch : `. .\outils\env-forge.ps1; cd projets/0.1-python; uv run pytest -q`.
  - Python avec PyTorch : `uv run --extra cpu pytest -q`.
  - Site : `cd site; npx vitest run …`, `npm run check:svelte`, `npx astro check`, `npx playwright test … --workers=4`.

## Points à surveiller à la relecture

Les tests ordinaires ne couvrent pas ces cinq situations, les plus susceptibles de gêner un lecteur. Chacune reçoit son test dans la tâche indiquée.

1. **Un brouillon qui fuit dans le site publié** : sa page, son îlot, le Worker du mini-modèle ou une entrée de recherche. Attendu : la construction sans `FORGE_ESSAIS` ne contient aucun dossier `partie-<p>/<p>-<n>/` d'un brouillon, et le garde-fou des prénoms reste vert. Tests en tâche 2 (intégration continue et parcours) et en tâche 15.
2. **Un lecteur sans carte NVIDIA, avec la roue pour processeur, ou avec un pilote trop ancien** lance les projets 0.3 à 0.5. Attendu :
   - tout tourne sur le processeur ;
   - demander `cuda` donne un message français qui dit quoi faire, jamais une trace Python brute ;
   - `python -m poste` nomme la cause.

   Tests en tâches 8, 10 et 12.
3. **Réglages et saisies extrêmes dans les ateliers** : texte vide, un seul mot, 10 000 caractères, emoji ; vecteur nul ; taux qui fait exploser la descente ; formes pleines de 1 ou à 3 dimensions ; 100 000 tirages ; poids nuls du neurone. Attendu : rien ne plante, jamais `NaN`, `Infinity` ni `e+`, aucun débordement à 390 px, et chaque recalcul en moins de 200 ms. Tests en tâches 4, 6, 11 et 14.
4. **Un nombre de la prose tapé à la main, ou une mesure de carte inventée.** Attendu : chaque nombre vient d'un import. Une mesure absente s'affiche « à mesurer », et aucun chapitre paru n'en contient. Tests en tâche 2 (`e2e/parution.spec.ts`), en tâches 9, 11 et 14 (« à mesurer » présent avant la porte) et en tâche 16 (plus aucun).
5. **Le notebook sur Colab** (Python 3.13, PyTorch 2.11 déjà installé, parfois sans carte) diffère du poste local (3.12, PyTorch 2.15). Attendu : il n'installe pas PyTorch, n'appelle que des fonctions anciennes, tourne sans carte et dit sur quoi il a tourné. Tests en tâches 8, 10 et 12 : exécution sans carte, et lecture du notebook qui refuse `pip install torch`, `torch.accelerator` et `torch.compile`. En plus, le job `notebooks-colab` (tâche 2) exécute chaque notebook avec Python 3.13 et `torch==2.11.0+cpu`, et chaque tâche de notebook le rejoue en local avant son commit.

---

## Fichiers

```
site/src/styles/commandes.css                 classes partagées des démos (tâche 1)
site/src/components/interactif/ZoneDefilable.svelte
site/src/lib/exiger.ts                        « Exemple devenu faux » (tâche 1)
site/src/lib/brouillons.ts                    règles des brouillons (tâche 2)
site/src/lib/invisibles.test.ts               caractères invisibles (tâche 2)
site/src/components/gabarit/SortieCommande.astro, BlocCommande.astro
site/src/brouillons/chapitres/0-1.mdx … 0-5.mdx     les cinq chapitres, en brouillon
site/src/lib/partie-0/                        jumeaux, paris, commandes, mesures, parité
  mot-suivant.ts, maths.ts, formes.ts, neurone.ts, poste.ts, mesures.ts,
  commandes.ts, parite.ts, paris-0-1.ts … paris-0-5.ts (+ leurs tests)
site/src/components/chapitres/0-1/AtelierMotSuivant.svelte
site/src/components/chapitres/0-2/FigureVecteurs.svelte, FigureDescente.svelte, FigureTirage.svelte
site/src/components/chapitres/0-4/AtelierFormes.svelte, TableauChronos.astro
site/src/components/chapitres/0-5/AtelierNeurone.svelte, CourbeXor.astro
site/src/essais/parite-partie-0.mdx
site/e2e/brouillons.spec.ts, parution.spec.ts, chapitre-0-1.spec.ts … chapitre-0-5.spec.ts
projets/0.1-python/    paquet mot_suivant      (sans dépendance)
projets/0.2-maths/     paquet maths_utiles     (sans dépendance)
projets/0.3-poste/     paquet poste            (PyTorch, extras cpu/gpu)
projets/0.4-tenseurs/  paquet tenseurs         (PyTorch, extras cpu/gpu)
projets/0.5-reseau/    paquet premier_reseau   (PyTorch, extras cpu/gpu)
notebooks/0.1-python.ipynb … 0.5-reseau.ipynb
```

Chaque projet a `pyproject.toml`, `uv.lock`, `README.md`, son paquet, `tests/` (dont `test_notebook.py` et ses attendus) ; les projets à PyTorch ont aussi `.python-version`. Le patron de `test_notebook.py` est celui de `projets/1.3-tokenizer/tests/test_notebook.py` :

- exécution avec `FORGE_IA_LOCAL` ;
- correction de l'exercice recopiée dans sa cellule, puis vérifiée ;
- notebook enregistré sans sorties.

---

### Tâche 1 : les commandes partagées des démos (M8), sans changement visible

**Fichiers :**

- Créer : `site/src/styles/commandes.css`, `site/src/components/interactif/ZoneDefilable.svelte`, `site/src/lib/exiger.ts`, `site/src/lib/exiger.test.ts`
- Modifier : `site/src/layouts/Base.astro` (import de `commandes.css` après `base.css`)
- Modifier : `site/src/components/demos/MiniModele.svelte`, `AnimationAttention.svelte`, `Calculateur.svelte`, `site/src/components/chapitres/1-3/AtelierTokenizer.svelte`
- Modifier : `site/src/lib/exemples.ts`, `site/src/lib/mini-modele/paris-attention.ts`, `site/src/lib/mini-modele/paris.ts`, `site/src/lib/calculateur/paris.ts`
- Temporaire, jamais commité : `site/e2e/visuel-m8.spec.ts` et son dossier de captures

**Interfaces (produites) :**

- `exiger.ts` : `exigeur(aRevoir: string): (condition: boolean, message: string) => void`. La fonction rendue lève `new Error(\`Exemple devenu faux : ${message}. Revoir ${aRevoir}.\`)`.
  - Les quatre `exiger` locaux deviennent `const exiger = exigeur('…')`, avec les textes « Revoir … » d'aujourd'hui recopiés tels quels : les messages ne changent pas d'un caractère.
- `commandes.css`, classes globales aux noms nouveaux, pour ne rien changer aux `.bouton` et `.bascule` des pages Astro (accueil, 404, recherche) :
  - `.bouton-relief` : le bouton à bord indigo et ombre décalée de MiniModele et d'AnimationAttention. Il reprend leurs règles de base, de survol, d'appui et `[aria-disabled='true']`.
  - `.bascule-soleil` : le bouton souligné de jaune. Règles communes aux quatre copies : couleur, fond, soulignement soleil de 5 px décalé de 4 px, `skip-ink: none`, bord 0, rayon 4 px, curseur ; au survol hors `:disabled`, fond soleil pâle et soulignement soleil vif ; `:disabled`, curseur par défaut ; `[aria-pressed='true']`, fond soleil et soulignement transparent.
  - Police, marges intérieures et hauteur minimale restent dans chaque composant, qui les règle localement.
  - `.zone-defilable` (`overflow-x: auto; max-width: 100%`).
  - `.indice-defilement` : caché par défaut, Gabarito 14 px, interligne 1,35, encre douce, marge `0 0 8px`. Il s'affiche sous `@media (max-width: 480px)` pour `[data-seuil='480']` et sous `@media (max-width: 600px)` pour `[data-seuil='600']`.
- `ZoneDefilable.svelte` : props `{ etiquette: string; indice?: string; seuil?: 480 | 600 /* 480 */; testId?: string; testIndice?: string; classe?: string; children: Snippet }`.
  - Rendu : `<p class="indice-defilement" data-seuil data-test={testIndice}>` si `indice`, puis `<div class="zone-defilable {classe}" role="region" aria-label={etiquette} tabindex="0" data-test={testId}>`.
  - Le commentaire `svelte-ignore a11y_no_noninteractive_tabindex` et sa raison n'existent plus qu'ici.
  - Il remplace les quatre zones : traits, clés et carte d'AnimationAttention ; repères du Calculateur, avec `testId="calc-reperes"`, `seuil={600}` et sa marge via `classe`.

- [ ] **Étape 1 : prendre les captures de référence, avant tout changement.** Écrire `e2e/visuel-m8.spec.ts`, qui attend `document.fonts.ready` puis compare chaque élément avec `expect(element).toHaveScreenshot(nom, { animations: 'disabled', maxDiffPixels: 0 })`. États capturés, sur ordinateur et sur mobile :
  - la page d'essai du mini-modèle après le pari `depart` : `[data-mini="mini"] .commandes`, puis la même zone avec le bouton principal survolé ;
  - la page d'essai de l'attention, pari `regard` joué, à l'étape 6 : le choix de la tête, les boutons d'étape, l'indice et la carte ;
  - la page d'essai du calculateur après le pari `operations` : la bascule « Voir le calcul », puis l'indice et le tableau des repères ;
  - le chapitre 1.3 après le pari `prediction` : la phrase qui contient la bascule « cacher les morceaux ».

  Commande : `npx playwright test e2e/visuel-m8.spec.ts --update-snapshots --workers=4`. Attendu : les captures sont écrites.
- [ ] **Étape 2 : écrire `exiger.test.ts`, qui échoue.**

```ts
const exiger = exigeur('src/lib/exemples.ts');
expect(() => exiger(true, 'x')).not.toThrow();
expect(() => exiger(false, '« z » apparaît dans le corpus')).toThrow(
  'Exemple devenu faux : « z » apparaît dans le corpus. Revoir src/lib/exemples.ts.');
```

  Commande : `npx vitest run src/lib/exiger.test.ts`. Attendu : échec, le module est introuvable.
- [ ] **Étape 3 : écrire `exiger.ts`, `commandes.css` et `ZoneDefilable.svelte`, puis remplacer les copies** dans les quatre composants et les quatre modules TypeScript.
  - Les règles locales qui disparaissent sont celles que `commandes.css` porte désormais ; les règles propres (polices, `.tetes`, colonnes collantes de la carte, réglages mobiles) restent.
  - Si `src/components/demos/imports.test.ts` liste les imports permis d'un composant modifié, y ajouter `ZoneDefilable.svelte`.
- [ ] **Étape 4 : tout vérifier.**
  - `npx vitest run`, `npm run check:svelte`, `npx astro check` ;
  - `npx playwright test --workers=4`, y compris `e2e/visuel-m8.spec.ts` sans `--update-snapshots`.

  Attendu : tout passe, et les captures sont identiques au pixel près.
- [ ] **Étape 5 : retirer le temporaire.** Supprimer `e2e/visuel-m8.spec.ts` et son dossier de captures. `git status --short` ne doit montrer que les fichiers de la tâche. Dans Git Bash, `LC_ALL=C.UTF-8 git grep -nP "[\x{00A0}\x{202F}\x{2009}\x{200B}\x{FEFF}]" -- <fichiers de la tâche>` ne doit rien renvoyer (sans `LC_ALL=C.UTF-8`, grep refuse ces caractères).
- [ ] **Étape 6 : commit**, message « Démos : boutons, bascules, zones défilantes et garde-fous d'exemple partagés (sans changement visible) ».

### Tâche 2 : les brouillons, les sorties de commande et les garde-fous

**Fichiers :**

- Créer : `site/src/lib/brouillons.ts`, `site/src/lib/brouillons.test.ts`, `site/src/lib/invisibles.test.ts`
- Créer : `site/src/components/gabarit/SortieCommande.astro`, `site/src/components/gabarit/BlocCommande.astro`
- Créer : `site/src/brouillons/chapitres/0-1.mdx` (squelette : frontmatter final de 0.1, avec `acquis: []` et une étape 1 de deux phrases ; la tâche 4 l'écrit en entier)
- Modifier : `site/src/pages/[partie]/[chapitre].astro`, `site/src/essais/gabarit.mdx`
- Modifier : `.github/workflows/site.yml`, `README.md` (sections « Parution d'un chapitre » et « Notebooks »)
- Créer : `outils/executer_notebooks.py`, `outils/colab-sans-carte.txt`
- Modifier : `.github/workflows/python.yml` (job `notebooks-colab`), `.gitignore` (`.colab/`)
- Test : `site/e2e/brouillons.spec.ts`, `site/e2e/parution.spec.ts`, `site/e2e/gabarit.spec.ts` (deux tests de plus)

**Interfaces :**

- Consomme : `schemaChapitre` (`content.config.ts`), `LayoutChapitre` et sa prop `indexer`.
- `brouillons.ts` : `verifierBrouillons(parus: string[], brouillons: { numero: string; fichier: string }[]): void`. Elle lève une erreur dans deux cas :
  - un fichier mal nommé : `Le brouillon du chapitre ${numero} doit s'appeler ${p}-${n}.mdx (trouvé : ${fichier}).` ;
  - un numéro à la fois paru et en brouillon : `Le chapitre ${numero} est à la fois paru (src/content/chapitres/${p}-${n}.mdx) et en brouillon (src/brouillons/chapitres/${p}-${n}.mdx) : supprime le brouillon.`
- La route `[partie]/[chapitre].astro` :
  - si `import.meta.env.FORGE_ESSAIS === '1'`, elle ajoute aux chapitres les modules de `import.meta.glob('../../brouillons/chapitres/*.mdx')`, comme le fait `essais/[nom].astro` ;
  - leur frontmatter passe par `schemaChapitre.parse`, puis par `verifierBrouillons` ;
  - un brouillon se rend avec `indexer={false}` et les mêmes composants que les chapitres.

  Sans `FORGE_ESSAIS`, la route ne lit pas les brouillons. `chapitresParus()`, `PiedChapitre` et les pages de partie ne lisent que la collection : un brouillon y reste « à venir ».
- `SortieCommande.astro` : props `{ fichier: string /* depuis la racine du dépôt */; commande: string; legende: string; absent: string }`.
  - Si le fichier existe, elle rend `<figure class="sortie" data-sortie={fichier}>` : l'invite `PS>` suivie de la commande, puis le contenu, dans un `<pre>` lui-même dans une `.zone-defilable` (`role="region"`, `aria-label="Sortie de la commande, défilable"`, `tabindex="0"`).
  - Une première ligne `# relevé le AAAA-MM-JJ` n'est pas affichée : la légende devient « {legende}, relevée le 4 novembre 2026. ».
  - Si le fichier manque : `<p class="a-mesurer" data-a-mesurer>{absent}</p>`, en encre douce et en italique.
- `BlocCommande.astro` : props `{ commandes: string[]; ou?: string /* « PowerShell » par défaut */ }`. Rendu : un `<pre>` de commandes avec la mention `ou`, sans coloration.
- Le marqueur `data-a-mesurer` est la seule façon de signaler une valeur absente ; `TableauChronos` (tâche 11) le pose aussi.

- [ ] **Étape 1 : écrire les tests qui échouent.**

```ts
// brouillons.test.ts
expect(() => verifierBrouillons(['1.3'], [{ numero: '0.1', fichier: '0-1.mdx' }])).not.toThrow();
expect(() => verifierBrouillons(['0.1'], [{ numero: '0.1', fichier: '0-1.mdx' }])).toThrow('à la fois paru');
expect(() => verifierBrouillons([], [{ numero: '0.1', fichier: '01.mdx' }])).toThrow("doit s'appeler 0-1.mdx");
// invisibles.test.ts : pour chaque fichier des chemins ci-dessous qui existe, aucun caractère interdit ;
// le message nomme le fichier, la ligne, le caractère (U+202F…) et dit « écris \u202F à la place ».
```

  Le test `invisibles.test.ts` lit, s'ils existent :

  - `site/src/brouillons/**/*.mdx`, `site/src/lib/partie-0/**`, `site/src/lib/exiger.ts`, `site/src/lib/brouillons.ts` ;
  - `site/src/components/chapitres/0-*/**`, `site/src/components/gabarit/SortieCommande.astro` et `BlocCommande.astro` ;
  - `site/src/components/interactif/ZoneDefilable.svelte`, `site/src/styles/commandes.css`, `site/e2e/chapitre-0-*.spec.ts` ;
  - `projets/0.*/**/*.py` et `projets/0.*/pyproject.toml` ;
  - les cellules de code des notebooks `notebooks/0.*.ipynb`.

```ts
// e2e/brouillons.spec.ts (ordinateur et mobile)
test('un brouillon se lit à son adresse, hors de la recherche', async ({ page }) => {
  expect((await page.goto('/forge-ia/partie-0/0-1/'))?.status()).toBe(200);
  await expect(page.locator('header')).toContainText('Partie 0, chapitre 0.1 sur 5');
  await expect(page.locator('[data-pagefind-body]')).toHaveCount(0);
});
test('la page de la Partie 0 le montre encore « à venir »', async ({ page }) => {
  await page.goto('/forge-ia/partie-0/');
  await expect(page.locator('[data-chapitre-carte="0.1"]')).toHaveAttribute('data-etat', 'a-venir');
});
// e2e/parution.spec.ts : pour chaque fichier de src/content/chapitres/*.mdx, la page du chapitre
// n'a aucun [data-a-mesurer] ; pour chaque brouillon, sa page répond 200.
// e2e/gabarit.spec.ts : sur la page d'essai du gabarit, SortieCommande montre le contenu d'un fichier
// existant (projets/1.3-tokenizer/donnees/corpus.txt, sans retour chariot) et pose [data-a-mesurer]
// avec son texte « absent » pour projets/inexistant/sortie.txt.
```

- [ ] **Étape 2 : vérifier l'échec.** Commandes : `npx vitest run src/lib/brouillons.test.ts`, puis `npx playwright test e2e/brouillons.spec.ts e2e/parution.spec.ts e2e/gabarit.spec.ts --workers=4`.
- [ ] **Étape 3 : écrire le code, le squelette de 0.1, les deux blocs de `gabarit.mdx`, le garde-fou de l'intégration continue et la section du README.**
  - **Garde-fou de `site.yml`**, dans le job `construction`, après le garde-fou des pages d'essai :

```bash
for f in src/brouillons/chapitres/*.mdx; do
  [ -e "$f" ] || continue
  n=$(basename "$f" .mdx); p=${n%%-*}
  if [ -e "dist/partie-$p/$n" ]; then
    echo "dist/partie-$p/$n existe : le brouillon $f entrerait dans le site publié." >&2; exit 1
  fi
done
```

  - **Section « Parution d'un chapitre » du README** :
    1. Conditions : tous les tests sont verts ; la page n'a aucun `[data-a-mesurer]` ; le notebook passe `outils/executer_notebooks.py` dans l'environnement `.colab` (voir la section « Notebooks » du README), et, s'il utilise la carte, il a tourné sur la RTX 5070 Ti ; l'utilisateur a dit oui à la publication.
    2. `git mv site/src/brouillons/chapitres/<p>-<n>.mdx site/src/content/chapitres/<p>-<n>.mdx`.
    3. Mettre à jour les parcours qui disent ce chapitre « à venir » (`navigation.spec.ts`, et le pied des chapitres voisins).
    4. Si le chapitre contient le mini-modèle (0.5), écarter `dist/_astro/travailleur-*.js` de la recherche du prénom dans `site.yml`, comme le dit son commentaire.
    5. `npm run build` : `dist/partie-<p>/<p>-<n>/` existe.
- [ ] **Étape 4 : vérifier que tout passe.**
  - `npx vitest run` et `npx astro check` ;
  - `npx playwright test --workers=4` ;
  - `npm run build` (sans essais), puis dans Git Bash `test ! -e dist/partie-0/0-1 && test -e dist/partie-1/1-3` ;
  - le garde-fou des prénoms de `site.yml`, rejoué à la main.
- [ ] **Étape 5 : commit**, message « Brouillons de chapitres, sorties de commande et garde-fous de parution ».
- [ ] **Étape 6 : les notebooks exécutés comme sur Colab, sans carte** (choix 2).
  - **`outils/colab-sans-carte.txt`** : en tête, un commentaire avec la source (https://github.com/googlecolab/backend-info, relevé du 03/11/2026, image sans carte). Puis `numpy==2.4.6`, `ipykernel==6.17.1`, `nbclient`, `nbformat`, et `regex` (le notebook 1.3 l'installe lui-même sur Colab). PyTorch n'y est pas : il vient d'un autre index (ci-dessous).
  - **`outils/executer_notebooks.py [notebooks…]`** : sans argument, tous les `notebooks/*.ipynb`. Pour chacun :
    - exécution d'une copie en mémoire par `NotebookClient(nb, timeout=600, kernel_name="python3")`, avec `FORGE_IA_LOCAL` à la racine du dépôt (le notebook n'installe et ne télécharge rien) ;
    - échec si une cellule lève une erreur : le message nomme le notebook, le numéro de la cellule et la dernière ligne de l'erreur ;
    - échec si une sortie contient une ligne `Même … que la page du site : X` avec X différent de `oui` (espaces ordinaires ou U+202F) ;
    - une ligne par notebook : nom, durée, `ok` ou `ÉCHEC`. En tête : versions de Python, de PyTorch (s'il s'importe) et de numpy.

    Code de sortie 1 si un notebook échoue.
  - **Job `notebooks-colab` de `python.yml`**, sous `ubuntu-latest`, `timeout-minutes: 20` :

```bash
uv venv --python 3.13 .colab
uv pip install --python .colab --index-url https://download.pytorch.org/whl/cpu torch==2.11.0
uv pip install --python .colab -r outils/colab-sans-carte.txt
.colab/bin/python outils/executer_notebooks.py
```

  - **En local** (PowerShell, `. .\outils\env-forge.ps1` d'abord pour le cache d'uv sur D:) : les mêmes commandes, avec `.colab\Scripts\python`. Si `ipykernel==6.17.1` ne s'installe pas ou ne démarre pas sous Python 3.13, prendre la dernière 6.x, et le noter dans le commentaire du fichier et dans le rapport.
  - **Vérifier qu'il attrape les fautes** : `notebooks/1.3-tokenizer.ipynb` passe (`ok`). Deux copies temporaires hors du dépôt échouent avec le bon message : l'une a une cellule `raise ValueError("essai")`, l'autre affiche « Même résultat que la page du site : non ».
  - **Section « Notebooks » du README** : l'utilisateur ne lance pas les notebooks ; ce que fait le job ; les commandes locales.
  - **Toute tâche qui crée ou modifie un notebook le rejoue ainsi avant son commit** : `.colab\Scripts\python outils\executer_notebooks.py notebooks\0.N-<nom>.ipynb`. Attendu : `ok`.
  - Commit : message « Notebooks exécutés comme sur Colab, sans carte (Python 3.13, PyTorch 2.11) », avec les fichiers de cette étape.

### Tâche 3 : le projet 0.1 « le mot suivant », son notebook et son jumeau

**Fichiers :**

- Créer : `projets/0.1-python/pyproject.toml`, `uv.lock`, `README.md`, `donnees/texte.txt`
- Créer : `projets/0.1-python/mot_suivant/__init__.py`, `mots.py`, `attendus.py`, `__main__.py`
- Test : `projets/0.1-python/tests/test_mots.py`, `test_attendus.py`, `test_notebook.py`, `tests/attendus.json`
- Créer : `notebooks/0.1-python.ipynb`
- Créer : `site/src/lib/partie-0/mot-suivant.ts`, `mot-suivant.test.ts`, `site/src/lib/partie-0/parite.ts`, `site/src/essais/parite-partie-0.mdx`
- Modifier : `site/src/components/demos/ControleParite.svelte` (prop `jeu`), `site/e2e/parite.spec.ts` (second test)

**Interfaces :**

- `pyproject.toml` : nom `mot-suivant`, `requires-python = ">=3.12"`, aucune dépendance. Groupe de développement : `pytest`, `nbclient`, `nbformat`, `ipykernel`.
- `donnees/texte.txt` : copie exacte de `projets/1.3-tokenizer/donnees/corpus.txt`.
- `mots.py`, marqueurs de régions `decouper`, `compter`, `predire` et `generer` :
  - `LETTRES = "abcdefghijklmnopqrstuvwxyzàâäçéèêëîïôöùûüÿœæ"` ;
  - `MOTIF = re.compile(rf"[{LETTRES}'’-]+|[.!?]")` ;
  - `decouper_mots(texte: str) -> list[str]` : `MOTIF.findall(texte.lower())`. Les chiffres, la ponctuation autre que `. ! ?`, les emojis et les blancs séparent ;
  - `compter_suivants(mots: list[str]) -> dict[str, Counter[str]]` : pour chaque paire `zip(mots, mots[1:])`. Les clés sont dans l'ordre de première apparition ;
  - `predire(suivants: dict[str, Counter[str]], mot: str) -> str | None` : le suivant le plus fréquent. En cas d'égalité, le plus petit dans l'ordre des points de code, avec `min(compte, key=lambda m: (-compte[m], m))`, la règle de 1.3. Renvoie `None` si rien ne suit ;
  - `generer(suivants, depart: str, longueur: int) -> list[str]` : la suite qui commence par `depart`, de `longueur` mots au plus (`[]` si `longueur <= 0`). Elle s'arrête quand rien ne suit, ou quand `depart` est absent du texte : la suite vaut alors `[depart]` ;
  - `premiere_reprise(suite: list[str]) -> int | None` : l'indice du premier mot déjà vu plus tôt dans la suite ;
  - `charger_texte() -> str`.
- `attendus.py` :
  - `TEXTES_DE_REFERENCE` : le texte du projet, `""`, `"le"`, `"Le LE le."`, `"l’enclume et l'enclume"`, `"Salut 🙂 ! 2026"`, `"ÉTÉ été"`, `"a b a b a"`, `"İstanbul ΟΔΟΣ forge-ia"` et `"a " * 5000` ;
  - `LONGUEURS = [1, 2, 12, 30]` ;
  - `calculer_attendus() -> dict` : `{"textes": [{"texte", "mots", "suivants": [[mot, [[suivant, compte], …]], …], "predictions": [[mot, prediction], …], "suites": [{"depart", "longueur", "suite", "reprise"}]}]}`. Les suivants d'un mot sont triés par compte décroissant, puis par point de code. Les départs sont chaque mot distinct du texte, plus `"inconnu"`.
- `__main__.py` : `uv run python -m mot_suivant le --longueur 12 [--fichier F]` affiche les suivants de « le » et la suite.
- `mot-suivant.ts` : `decouperMots`, `compterSuivants(mots): Map<string, Map<string, number>>`, `suivantsTries(compte): [string, number][]`, `predire`, `generer`, `premiereReprise`, et `TEXTE_DE_DEPART` (import `?raw` de `donnees/texte.txt`). Les comparaisons se font avec `comparerPointsDeCode` (`site/src/lib/points-de-code.ts`).
- `parite.ts` : `CALCULS_PARTIE_0: Record<string, () => Attendus>`, avec ici `'mot-suivant'`. Chaque calcul relit les entrées du fichier d'attendus et refait les sorties.
- `ControleParite.svelte` : prop `jeu?: 'mini-modele' | 'partie-0'`, `'mini-modele'` par défaut, sans rien changer à la page existante.
- `parite-partie-0.mdx` : frontmatter d'un chapitre 0.1 d'essai, `<ControleParite client:load jeu="partie-0" />`.

- [ ] **Étape 1 : écrire les tests Python qui échouent.**

```python
def test_decouper_mots():
    assert decouper_mots("Le forgeron frappe, le fer !") == ["le", "forgeron", "frappe", "le", "fer", "!"]
    assert decouper_mots("L’enclume") == ["l’enclume"]
    assert decouper_mots("Salut 🙂 ! 2026") == ["salut", "!"]

def test_compter_suivants():
    s = compter_suivants(["le", "fer", "et", "le", "fer", "puis", "le", "feu"])
    assert s["le"] == Counter({"fer": 2, "feu": 1})
    assert "feu" not in s

def test_predire_departage_et_rien_ne_suit():
    s = compter_suivants(["a", "c", "a", "b"])
    assert predire(s, "a") == "b"
    assert predire(s, "b") is None

def test_generer_et_reprise():
    s = compter_suivants("a b a b a".split())
    assert generer(s, "a", 5) == ["a", "b", "a", "b", "a"]
    assert generer(s, "z", 5) == ["z"] and generer(s, "a", 0) == []
    assert premiere_reprise(["a", "b", "a"]) == 2 and premiere_reprise(["a", "b"]) is None

def test_texte_identique_au_corpus_de_1_3():
    original = RACINE / "projets" / "1.3-tokenizer" / "donnees" / "corpus.txt"
    if original.exists():
        assert (PROJET / "donnees" / "texte.txt").read_bytes() == original.read_bytes()
```

  `test_predire_departage_et_rien_ne_suit` est encadré par `# region: test-predire` et `# fin: test-predire` : le chapitre le montre. Plus `test_attendus_a_jour`, et `test_notebook.py` selon le patron de 1.3 : sorties « Même résultat que la page du site : oui » et « Défi réussi » pour la correction, notebook sans sorties.
- [ ] **Étape 2 : vérifier l'échec.** Commande : `cd projets/0.1-python; uv run pytest -q`.
- [ ] **Étape 3 : écrire le paquet, les attendus et le notebook.**
  - **Le notebook**, en français pour débutants, suit le plan du chapitre :
    1. valeurs, `0.1 + 0.2` ;
    2. listes et tranches ;
    3. `zip`, dictionnaire, `Counter` ;
    4. les fonctions du paquet sur le texte ;
    5. une suite de 12 mots.
  - **L'exercice** : écrire `compter_mots(mots) -> Counter`. Sa cellule affiche « Défi réussi » si le mot le plus fréquent est celui de `Counter(mots).most_common(1)`, sinon « Pas encore » ; la correction est repliée dans un `<details>`.
  - **La dernière cellule** compare toutes les prédictions du texte à `tests/attendus.json`.
  - Puis `uv run python -m mot_suivant.attendus`.
- [ ] **Étape 4 : vérifier que le Python passe.** Commande : `uv run pytest -q`.
- [ ] **Étape 5 : écrire le jumeau et sa parité, en commençant par leurs tests.**
  - `mot-suivant.test.ts` : pour chaque texte des attendus, `mots`, `suivants` triés, `predictions`, `suites` et `reprise` sont égaux (`toStrictEqual`). Découper et compter 10 000 caractères prend moins de 200 ms.
  - Le second test de `e2e/parite.spec.ts` vise `/forge-ia/essais/parite-partie-0/`. Il compare la sortie `mot-suivant` à `projets/0.1-python/tests/attendus.json`, comme le premier, et tourne aussi dans les projets `parite-firefox` et `parite-webkit`.

  Commandes : `npx vitest run src/lib/partie-0`, puis `npx playwright test e2e/parite.spec.ts --workers=4`. Attendu : échec, puis succès une fois le code écrit.
- [ ] **Étape 6 : commit**, message « Projet 0.1 : le mot suivant, en Python et en TypeScript, avec son notebook ».

### Tâche 4 : le chapitre 0.1 « Python pour l'IA » et son atelier

**Fichiers :**

- Créer : `site/src/components/chapitres/0-1/AtelierMotSuivant.svelte`
- Créer : `site/src/lib/partie-0/paris-0-1.ts`, `paris-0-1.test.ts`, `site/src/lib/partie-0/commandes.ts`
- Modifier : `site/src/brouillons/chapitres/0-1.mdx` (le chapitre entier)
- Test : `site/e2e/chapitre-0-1.spec.ts`

**Interfaces :**

- Consomme : `mot-suivant.ts` (tâche 3), `exigeur` (tâche 1), `NombreManipulable`, `canal`/`ouverture`, `BlocCommande`, `CodeExplique`, `LiensProjet`, `EncadreLabo`, et les données du calculateur.
- `commandes.ts` : `INSTALLER_UV_WINDOWS`, `INSTALLER_UV_WINGET`, `INSTALLER_UV_LINUX_MAC` (`curl -LsSf https://astral.sh/uv/install.sh | sh`), `VERIFIER_UV` (`uv --version`), `CLONER_DEPOT` (`git clone https://github.com/chipat-neko/forge-ia`). La tâche 9 complète ce fichier.
- `paris-0-1.ts`, avec `exigeur('src/lib/partie-0/paris-0-1.ts et le texte des paris du chapitre 0.1')` :
  - `choixFlottants()` : « `True` », « `False` », « Une erreur ». Le juste est « `False` », calculé par `0.1 + 0.2 === 0.3` (même calcul IEEE 754 qu'en Python).
  - `choixTranche()` : « `['le', 'forgeron']` », « `['forgeron', 'frappe']` », « `['forgeron']` ». Le juste est celui de `['le', 'forgeron', 'frappe'].slice(1)`, écrit par `reprListePython(l: string[]): string`.
  - `MOT_DU_PARI = 'le'` et `choixMotSuivant()`, sur `TEXTE_DE_DEPART` : « « {premier suivant} » » (juste), « « {deuxième suivant} » », et le mot le plus fréquent du texte qui ne suit jamais « le ».
    - Gardes : « le » a au moins deux suivants, le premier est seul en tête, et le troisième choix existe.
    - Si une garde tombe, prendre le premier mot du texte qui les passe toutes, et le dire dans un commentaire.
  - `LONGUEUR_DU_PARI = 12` et `choixBoucle()` : « Une boucle : les mêmes mots reviennent » (juste si `premiereReprise(generer(…, MOT_DU_PARI, 12)) !== null`), « Une suite de mots qui ne se répète jamais », « Elle s'arrête avant 12 mots » (juste si la suite est plus courte). Exactement un choix est juste par construction.
- `AtelierMotSuivant.svelte` : props `{ texteInitial: string; motInitial: string; verrou?: string; acquis?: string }`.
  - **Le champ de texte** : `<textarea data-test="ms-texte">`, 8 lignes visibles, fond soleil pâle et souligné soleil, comme le champ de 1.3.
  - **La phrase de réglage** : « En partant de [select data-test="ms-depart"], génère [NombreManipulable canal="ms:longueur" min 1 max 30 initiale 12 testId="ms-longueur"] mots. ». Le `<select>` liste les mots distincts dans l'ordre de première apparition.
  - **Le tableau des suivants** (`data-test="ms-suivants"`) : un mot et son compte par ligne, triés comme `suivantsTries`. La prédiction porte `data-prediction`.
  - **La suite** (`<ol data-test="ms-suite">`) : chaque mot porte `data-mot`, et le mot de la première reprise porte `data-reprise`. Sous la suite : « La suite revient sur « X » au mot n : à partir de là, elle tourne en rond. »
  - **Les messages** (`data-test="ms-message"`) :
    - texte sans mot : « Écris quelques phrases : le programme a besoin de mots à compter. » ;
    - rien ne suit le mot choisi : « Rien ne suit « X » dans ce texte : la suite s'arrête là. ».
  - **Le défi** (`data-test="ms-defi"`) : « Défi réussi : 12 mots ou plus, sans boucle. » quand la suite fait 12 mots ou plus sans reprise.
  - **L'acquis** : `forge:acquis { cle: acquis }` au premier changement du mot de départ.
  - **Les valeurs** : le canal et le verrou sont lus une fois, comme dans `NombreManipulable`. Les recalculs se font dans un `$derived`.
  - **Sans JavaScript** : le texte, le tableau et la suite du départ restent lisibles, rendus par Astro.
- **Le chapitre 0.1**, frontmatter `partie: 0`, `numero: "0.1"`, `titre: "Python pour l'IA"`.
- **Ouverture** (avant l'étape 1, comme `PhraseDecoupee` en 1.3) : la première phrase du texte, puis, calculée par le jumeau, « Après « le », ce texte met le plus souvent « … » ». C'est ce que le lecteur saura programmer.

| Étape | Titre | Contenu imposé |
| --- | --- | --- |
| 1 | Python, et comment le lancer | Colab pour ne rien installer ; `uv` sur le PC (`BlocCommande` avec `INSTALLER_UV_WINDOWS` et `VERIFIER_UV`, renvoi à 0.3 pour le détail) ; `uv run python -m mot_suivant le`. |
| 2 | Des nombres et du texte | `int`, `float`, `str`, f-strings. Pari `flottants`. |
| 3 | Des listes de mots | Listes, indices, tranches, `zip`. `CodeExplique` sur la région `decouper`. Pari `tranche`. |
| 4 | Compter avec un dictionnaire | `dict`, `Counter`. `CodeExplique` sur `compter`. |
| 5 | Fais ton pari | Pari `suivant`, qui ouvre `atelier`. |
| 6 | L'atelier : le mot suivant | `Verrou nom="atelier"` autour de l'atelier (`acquis="atelier"`). Puis le pari `boucle`. Note de marge : 1.1 dira pourquoi c'est déjà, en tout petit, un modèle de langage. |
| 7 | Ranger son code | Fonctions annotées, `NamedTuple`, modules, `__main__`, `pathlib` en UTF-8. `CodeExplique` sur `predire` et `generer`. |
| 8 | Les tests | pytest, `uv run pytest`. `CodeExplique` sur la région `test-predire` de `tests/test_mots.py`. |
| 9 | À grande échelle | `EncadreLabo` : chez un grand labo aussi, Python pilote, et le calcul lourd part dans du C++ et du CUDA sous PyTorch ou JAX. Recherche web dans la tâche, sources primaires datées. Puis `LiensProjet projet="0.1-python"` et « À suivre » vers 0.2. |

**Acquis**, dans l'ordre :

| Clé | Texte | Gagné |
| --- | --- | --- |
| `flottants` | « Les nombres à virgule sont arrondis : on ne les compare pas avec ==. » | pari `flottants` |
| `tranches` | « Une tranche prend un morceau de liste sans la modifier. » | pari `tranche` |
| `compter` | « Un Counter compte ce qui suit chaque mot en une ligne. » | pari `suivant` |
| `atelier` | « Le mot de départ change toute la suite. » | atelier |
| `boucle` | « Toujours choisir le plus fréquent fait tourner en rond. » | pari `boucle` |

**Défi :** celui de l'atelier, une suite de 12 mots sans boucle.

- [ ] **Étape 1 : écrire les tests qui échouent.**

```ts
// paris-0-1.test.ts
expect(choixFlottants().find((c) => c.juste)?.texte).toBe('`False`');
expect(choixTranche().find((c) => c.juste)?.texte).toBe("`['forgeron', 'frappe']`");
const s = compterSuivants(decouperMots(TEXTE_DE_DEPART));
expect(choixMotSuivant().find((c) => c.juste)?.texte).toBe(`« ${predire(s, MOT_DU_PARI)} »`);
for (const f of [choixFlottants, choixTranche, choixMotSuivant, choixBoucle]) expect(f().filter((c) => c.juste)).toHaveLength(1);
```

```ts
// e2e/chapitre-0-1.spec.ts (ordinateur et mobile)
test('chapitre 0.1 complet', …);   // position « Partie 0, chapitre 0.1 sur 5 » ; les 4 paris ; changer le mot ; recap « 5 sur 5 » ;
                                   // pied « à venir » (0.2 est un brouillon) ; axe ; débordement ; typographie ; lignes ≤ 80
test('les choix des paris viennent du jumeau', …);           // textes des boutons = paris-0-1.ts
test('le code affiché est celui des régions testées', …);    // chaque .code-explique pre = extraireRegion(fichier, région)
test('atelier : texte vide, mot sans suivant, 10 000 caractères, emoji', …);  // messages exacts ; recalcul < 200 ms
test('atelier : la suite et sa reprise suivent le jumeau', …); // ms-suite = generer(…) ; data-reprise au bon mot
test('défi réussi sur un texte sans boucle', …);             // texte « un deux trois … douze » : ms-defi visible
test('avant le pari, l\u2019atelier est verrouillé ; sans JavaScript, tout se lit', …);
```

- [ ] **Étape 2 : vérifier l'échec.** Commandes : `npx vitest run src/lib/partie-0/paris-0-1.test.ts`, puis `npx playwright test e2e/chapitre-0-1.spec.ts --workers=4`.
- [ ] **Étape 3 : écrire `commandes.ts`, les paris, l'atelier et le chapitre.** L'allure de l'atelier suit celle de 1.3 : champ et nombre jaunes, tableau typographié, suite en bande de mots aux teintes alternées `--teinte-a` et `--teinte-b`.
- [ ] **Étape 4 : vérifier que tout passe**, y compris `npx vitest run src/lib/invisibles.test.ts`, `npm run check:svelte` et `npx astro check`.
- [ ] **Étape 5 : captures et relecture.** Captures ordinateur et mobile du chapitre, de l'atelier ouvert et du message « tourne en rond ». Les relire avec l'outil de lecture d'images, face au chapitre 1.3 et aux deux mémoires de direction visuelle, et corriger tout ce qui fait « fait par IA ».
- [ ] **Étape 6 : commit**, message « Chapitre 0.1 : Python pour l'IA, avec l'atelier du mot suivant (brouillon) ».

### Tâche 5 : le projet 0.2 « les maths utiles », son notebook et son jumeau

**Fichiers :**

- Créer : `projets/0.2-maths/pyproject.toml`, `uv.lock`, `README.md`
- Créer : `projets/0.2-maths/maths_utiles/__init__.py`, `vecteurs.py`, `derivees.py`, `tirage.py`, `probabilites.py`, `attendus.py`, `__main__.py`
- Test : `projets/0.2-maths/tests/test_vecteurs.py`, `test_derivees.py`, `test_tirage.py`, `test_probabilites.py`, `test_attendus.py`, `test_notebook.py`, `tests/attendus.json`
- Créer : `notebooks/0.2-maths.ipynb`
- Créer : `site/src/lib/partie-0/maths.ts`, `maths.test.ts`
- Modifier : `site/src/lib/partie-0/parite.ts` (entrée `'maths'`), `site/e2e/parite.spec.ts` (fichier de 0.2)

**Interfaces :**

- `pyproject.toml` : nom `maths-utiles`, sans dépendance, même groupe de développement qu'en 0.1.
- `vecteurs.py`, régions `scalaire` et `matrice` :
  - `produit_scalaire(a: Sequence[float], b: Sequence[float]) -> float` : une boucle `s = 0.0 ; s += x * y` sur `zip(a, b, strict=True)` ;
  - `norme(a) -> float` : `math.sqrt(produit_scalaire(a, a))` ;
  - `cosinus(a, b) -> float | None` : `None` si l'un est nul ;
  - `somme(a, b) -> list[float]` ;
  - `matrice_fois_vecteur(m: list[list[float]], v: list[float]) -> list[float]` : une ligne de m fois v par case. Si les tailles ne vont pas : `ValueError("La matrice a 4 colonnes et le vecteur 3 nombres : il en faut autant.")`.
- `derivees.py`, régions `erreur`, `pente`, `descendre` et `chaine` :
  - `erreur(x: float) -> float` : `(x - 3.0) * (x - 3.0) + 1.0` ;
  - `pente(x) -> float` : `2.0 * (x - 3.0)` ;
  - `pente_approchee(f, x, h=1e-6) -> float` : Python seulement ;
  - `descendre(x0: float, taux: float, nb_pas: int) -> list[float]` : les positions `x0 … x_n`, avec `x ← x - taux * pente(x)` ;
  - `pas_pour_atteindre(x0, taux, seuil, max_pas=100) -> int | None` : le premier n tel que `erreur(x_n) < seuil` ;
  - `TAUX_DESCENTE = [0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0, 1.05, 1.2]`, les taux de la figure ;
  - `exemple_chaine() -> dict` : h(x) = (2x + 1)², sa dérivée exacte 4·(2x + 1) et l'approchée, en x = 1.
- `tirage.py`, régions `hasard` et `tirer` :
  - `class Hasard` : SplitMix32, copie de `projets/mini-modele/mini_modele/calcul.py`, seulement `__init__(graine)`, `suivant32()` et `uniforme()` ;
  - `EXEMPLE_COMPTES = {"fer": 6, "métal": 3, "feu": 1}` (« ce qui suit « le » ») et `GRAINE_TIRAGE = 1234`, la graine de départ de la figure et du pari ;
  - `probabilites(comptes: dict[str, int]) -> list[float]` : `c / total` ;
  - `tirer(probas: list[float], u: float) -> int` : cumul de gauche à droite, premier indice où `u < cumul`, sinon le dernier ;
  - `tirages(probas, n: int, graine: int) -> list[int]` : les comptes par issue.
- `probabilites.py`, régions `softmax` et `erreur-de-prediction`. Python seulement, avec `math.exp` et `math.log` :
  - `softmax(scores: list[float], temperature: float = 1.0) -> list[float]`, en soustrayant le plus grand score ;
  - `erreur_de_prediction(p: float) -> float` : `-math.log(p)`.
- `attendus.py` → `tests/attendus.json`, sections :
  - `vecteurs` : paires de vecteurs entiers de −4 à 4, dont des vecteurs nuls ;
  - `matrices` : exemples, dont celui du chapitre, `[[1, 2, 3], [0, 1, 0]] × [1, 1, 1]` ;
  - `descente` : x0 dans {−2, 0, 0,5, 7}, chaque taux de `TAUX_DESCENTE`, 30 pas, et `pas_pour_atteindre` pour le seuil 1,01 ;
  - `tirage` : `graine_tirage`, les 20 premières `uniforme()` de la graine 1234, des cas de `tirer`, et `tirages(probabilites(EXEMPLE_COMPTES), n, GRAINE_TIRAGE + i)` pour n dans {10, 100, 1 000, 10 000, 100 000} et i de 0 à 2 (les graines qu'on atteint par « Autre graine ») ;
  - `softmax` : les scores [2,0 ; 1,0 ; 0,1] aux températures 0,5, 1 et 2 ;
  - `erreur` : p dans {1, 0,5, 0,1, 1/40} ;
  - `chaine`.
- `maths.ts` : `produitScalaire`, `norme`, `cosinus`, `somme`, `matriceFoisVecteur`, `erreur`, `pente`, `descendre`, `pasPourAtteindre`, `TAUX_DESCENTE`, `EXEMPLE_COMPTES` (en `[string, number][]`), `GRAINE_TIRAGE`, `probabilites`, `tirer` et `tirages`. Le hasard vient de `Hasard` de `site/src/lib/mini-modele/calcul.ts`. Aucun softmax ni log.

- [ ] **Étape 1 : écrire les tests Python qui échouent.**

```python
assert produit_scalaire([2, 1], [-1, 2]) == 0 and produit_scalaire([3, 1], [1, 2]) == 5
assert norme([3, 4]) == 5.0 and cosinus([1, 0], [0, 0]) is None
assert matrice_fois_vecteur([[1, 2, 3], [0, 1, 0]], [1, 1, 1]) == [6, 1]
with pytest.raises(ValueError, match="autant"): matrice_fois_vecteur([[1, 2, 3, 4]], [1, 2, 3])
assert descendre(0.0, 0.5, 1) == [0.0, 3.0]
assert pas_pour_atteindre(0.0, 0.1, 1.01) == 16
assert pas_pour_atteindre(0.0, 0.5, 1.01) == 1
assert pas_pour_atteindre(0.0, 1.0, 1.01) is None          # oscille entre 0 et 6
assert abs(pente_approchee(erreur, 0.0) - pente(0.0)) < 1e-6
assert sum(tirages(probabilites(EXEMPLE_COMPTES), 1000, 1234)) == 1000
assert softmax([0.0, 0.0]) == [0.5, 0.5]
assert abs(erreur_de_prediction(1 / 40) - math.log(40)) < 1e-12
c = exemple_chaine(); assert c["exacte"] == 12.0 and abs(c["approchee"] - 12.0) < 1e-5
```

  Plus `test_attendus_a_jour`, et `test_notebook.py` : « Même résultat que la page du site : oui », la correction de l'exercice, le notebook sans sorties.
- [ ] **Étape 2 : vérifier l'échec**, puis écrire le paquet, les attendus et le notebook.
  - **Le notebook** suit le chapitre : vecteurs, matrices, pente, descente, tirages, softmax, puis l'erreur.
  - **L'exercice** : écrire `norme(a)` ; « Défi réussi » si `norme([3, 4]) == 5`.
  - **La dernière cellule** compare les sections exactes aux attendus.
- [ ] **Étape 3 : vérifier que le Python passe.** Commande : `cd projets/0.2-maths; uv run pytest -q`.
- [ ] **Étape 4 : écrire le jumeau et sa parité, en commençant par leurs tests.**
  - `maths.test.ts` compare chaque cas des sections `vecteurs`, `matrices`, `descente` et `tirage` aux attendus, avec `toStrictEqual`.
  - `new Hasard(1234)` redonne les 20 uniformes du Python de 0.2 : c'est le lien entre sa copie de SplitMix32 et celle du mini-modèle.
  - `EXEMPLE_COMPTES` et `GRAINE_TIRAGE` sont égaux à ceux du Python.
  - Le parcours de parité ajoute le fichier de 0.2 à la page `parite-partie-0`.

  Commandes : `npx vitest run src/lib/partie-0`, puis `npx playwright test e2e/parite.spec.ts --workers=4`.
- [ ] **Étape 5 : commit**, message « Projet 0.2 : vecteurs, pente, descente et tirages, en Python et en TypeScript, avec son notebook ».

### Tâche 6 : les trois figures de 0.2

**Fichiers :**

- Créer : `site/src/components/chapitres/0-2/FigureVecteurs.svelte`, `FigureDescente.svelte`, `FigureTirage.svelte`
- Créer : `site/src/lib/partie-0/paris-0-2.ts`, `paris-0-2.test.ts`
- Créer : `site/src/brouillons/chapitres/0-2.mdx` (frontmatter final ; seulement les étapes 1, 3, 4 et 6 du tableau de la tâche 7, avec leurs paris, verrous et figures ; la tâche 7 écrit le reste)
- Test : `site/e2e/figures-0-2.spec.ts`

**Interfaces :**

- Consomme : `maths.ts` (tâche 5), `NombreManipulable` (avec `texte` et `pas`), `nombre`, `pourcent`, `exigeur`, `.bouton-relief` et `.bascule-soleil`. Le dessin est en SVG, à la main, aux couleurs du site.
- **`FigureVecteurs.svelte`**, props `{ verrou?: string; acquis?: string }`.
  - Canaux `vec:ax`, `vec:ay`, `vec:bx` et `vec:by`, entiers de −4 à 4, au départ (3, 1) et (1, 2).
  - La phrase « a = ([ax], [ay]) et b = ([bx], [by]) » ; testIds `vec-ax`, `vec-ay`, `vec-bx`, `vec-by`.
  - Le dessin (`data-test="vec-dessin"`, `role="img"`, `aria-label` avec les deux vecteurs) : quadrillage de −5 à 5, a en indigo, b en encre douce, a + b en lavande pointillée.
  - `vec-scalaire` : « a · b = 3 × 1 + 1 × 2 = 5 ».
  - `vec-cosinus` : « cos = 5 ÷ (3,16 × 2,24) = 0,71 : à peu près la même direction », selon ces seuils :

    | cos | Texte |
    | --- | --- |
    | > 0,9 | presque la même direction |
    | de 0,3 à 0,9 | à peu près la même direction |
    | de −0,3 à 0,3 | presque perpendiculaires |
    | de −0,9 à −0,3 | des directions plutôt opposées |
    | < −0,9 | des directions opposées |
  - Un vecteur nul : « a est nul : il n'a pas de direction, le cosinus n'existe pas. »
  - Acquis émis la première fois que a · b = 0 avec deux vecteurs non nuls.
- **`FigureDescente.svelte`**, props `{ verrou?: string }`.
  - Canaux `desc:x0` (de −2 à 8, pas de 0,5, départ 0) et `desc:taux` (indice dans `TAUX_DESCENTE`, départ sur 0,1). Le taux s'affiche par `texte`, avec 24 px par cran.
  - Les commandes `.bouton-relief` : « Un pas » (`desc-pas`), « Dix pas » (`desc-dix`), « Recommencer » (`desc-recommencer`).
  - Changer x0 ou le taux repart du pas 0.
  - Le dessin (`desc-dessin`) : la courbe de x = −2 à 8, le point courant, la tangente et les points déjà visités.
  - Une position où |x − 3| > 1 000 arrête la descente et `aria-disabled` les boutons de pas, avec `desc-etat` : « x est parti à plus de 1 000 du fond : ce taux fait exploser la descente. »
  - Hors du dessin, un repère « hors du dessin » et jamais de coordonnée non finie.
  - La ligne d'état (`desc-etat`, annoncée après chaque clic seulement) : « Pas 3 : x = 1,464, erreur = 3,359, pente = −3,072. » La liste des pas (`desc-liste`) donne les 3 décimales.
  - Au pas 0, la phrase de la pente : « En x = 0, la pente vaut 2 × (0 − 3) = −6 : la courbe descend vers la droite. »
- **`FigureTirage.svelte`**, props `{ verrou?: string }`.
  - Canal `tir:n` : indice dans [10, 100, 1 000, 10 000, 100 000], affiché par `texte`. Graine `GRAINE_TIRAGE` au départ ; « Autre graine » (`tir-graine`) l'augmente de 1 et l'affiche (« graine 1 235 »).
  - Pour chaque issue, une barre de la probabilité (contour lavande) et une barre de la fréquence tirée (indigo plein). Le tableau `tir-resultats` dit : « fer : 60 % attendu, 58 sur 100 tirés (58 %) ».
  - 100 000 tirages en moins de 200 ms.
  - Seule `FigureVecteurs` émet un acquis (le défi du chapitre) : les deux autres figures n'en ont pas besoin.
- `paris-0-2.ts`, avec `exigeur(…)` :
  - `choixProduitScalaire()` sur (2, 1) et (−1, 2) : « 0 » (juste, calculé), « 3 », « 4 » ;
  - `choixFormeMatrice()`, pour « Une matrice de 3 lignes et 4 colonnes multiplie un vecteur de combien de nombres ? » : « 3 », « 4 » (juste, le nombre de colonnes), « 12 » ;
  - `choixPente()` en x = 0 : « Négative » (juste, `pente(0) < 0`), « Nulle », « Positive » ;
  - `choixTauxMoitie()`, `pasPourAtteindre(0, 0,5, 1,01)` : « 1 » (juste), « 16 », « Jamais » ;
  - `choixTauxGrand()`, au taux 1,05 : « Il arrive plus vite », « Il oscille autour du fond », « Il s'éloigne du fond à chaque pas » (juste si |x₃₀ − 3| > |x₀ − 3|) ;
  - `choixTirage()`, « Sur 10 tirages, « fer » (60 %) sort-il exactement 6 fois ? » : « Oui, forcément », « Pas forcément : X fois cette fois-ci » (juste si `tirages(…, 10, GRAINE_TIRAGE)[0] !== 6`, X calculé), « Jamais 6 fois ». Si le compte vaut 6, la garde l'arrête : changer `GRAINE_TIRAGE` en Python et en TypeScript (la figure suit), régénérer les attendus, et le noter.

  Ces fonctions servent aux paris de la tâche 7 ; `choixErreur()` lit la section `erreur` des attendus du Python.

- [ ] **Étape 1 : écrire les tests qui échouent.** `paris-0-2.test.ts` : chaque fonction a exactement un choix juste, égal au calcul du jumeau.

```ts
// e2e/figures-0-2.spec.ts, sur /forge-ia/partie-0/0-2/ (ordinateur et mobile)
test('vecteurs : le produit scalaire et le cosinus suivent les réglages', …);  // (2,1)·(−1,2) → « = 0 », « presque perpendiculaires »
test('vecteurs : un vecteur nul ne casse rien', …);                      // a = (0,0) → message exact, aucun NaN
test('descente : au taux 0,5, un pas suffit', …);                        // desc-etat « Pas 1 : x = 3,000, erreur = 1,000 »
test('descente : au taux 1,2, la descente explose proprement', …);       // message exact ; boutons aria-disabled ; aucun NaN/Infinity/e+ ; pas de débordement
test('descente : les positions suivent le jumeau', …);                   // desc-liste = descendre(0, 0.1, 10) formaté
test('tirage : les comptes suivent le jumeau, même à 100 000', …);       // tir-resultats = tirages(…, n, GRAINE_TIRAGE), puis GRAINE_TIRAGE + 1 après « Autre graine »
test('verrous, clavier, sans JavaScript, axe, débordement, typographie', …);
```

- [ ] **Étape 2 : vérifier l'échec**, écrire les figures, les paris et le brouillon partiel, puis vérifier que tout passe. Commandes : `npx vitest run src/lib/partie-0`, `npx playwright test e2e/figures-0-2.spec.ts --workers=4`, `npm run check:svelte`.
- [ ] **Étape 3 : captures et relecture** des trois figures, sur ordinateur et sur mobile, en état de départ puis en état poussé (vecteur nul, descente explosée, 100 000 tirages). Corriger tout ce qui fait « tableau de bord » ou « fait par IA ».
- [ ] **Étape 4 : commit**, message « Chapitre 0.2 : les figures des vecteurs, de la descente et des tirages ».

### Tâche 7 : le chapitre 0.2 « Les maths utiles » rédigé

**Fichiers :**

- Modifier : `site/src/brouillons/chapitres/0-2.mdx` (le chapitre entier)
- Modifier : `site/src/lib/partie-0/paris-0-2.ts` (ajout de `choixErreur()`), `paris-0-2.test.ts`
- Test : `site/e2e/chapitre-0-2.spec.ts`

**Interfaces :**

- Consomme : les figures et les paris de la tâche 6, les attendus de 0.2 (pour les tableaux softmax et −ln p, rendus par un `map` dans le MDX), et `PRESETS_FORGE` de `site/src/lib/calculateur/ton-ia.ts`.
- `choixErreur()`, pour « Si le modèle ne donne qu'une chance sur 40 à la bonne lettre, son erreur vaut… » : « 0,025 », « 3,689 » (juste : la valeur `p = 1/40` de la section `erreur`, formatée avec 3 décimales), « 40 ».
- **Ouverture :** « (3, 1) · (1, 2) = 5 », calculé par le jumeau, et une phrase : vecteurs, matrices, pentes et probabilités, ton IA ne fait rien d'autre, des milliards de fois.

| Étape | Titre | Contenu imposé |
| --- | --- | --- |
| 1 | Des nombres en colonne : les vecteurs | Un mot de ton IA est un vecteur de `PRESETS_FORGE.tres_grand.dim` nombres. Pari `scalaire`, qui ouvre `vecteurs` ; la figure dans son verrou, avec `acquis="perpendiculaires"`. `CodeExplique` sur `scalaire`. |
| 2 | Les matrices : beaucoup de produits scalaires | L'exemple `[[1, 2, 3], [0, 1, 0]] × [1, 1, 1]` en tableau calculé ; une couche de ton IA est une matrice de dim × dim poids (nombre calculé). Pari `formes`. `CodeExplique` sur `matrice`. Renvoi à l'atelier des formes de 0.4. |
| 3 | La pente | L'erreur selon un poids, (x − 3)² + 1 ; la pente et la pente approchée (valeurs de `exemple_chaine` et des attendus). Pari `pente`, qui ouvre `descente` ; la figure dans son verrou. `CodeExplique` sur `erreur` et `pente`. |
| 4 | Descendre la pente | x ← x − taux × pente. Paris `taux-moitie` et `taux-grand`. `CodeExplique` sur `descendre`. Note : c'est ainsi qu'apprend ton IA, sur 433,6 millions de poids à la fois (nombre tiré de `MESURES_TON_IA` ou de `PRESETS_FORGE`). |
| 5 | La règle de la chaîne | h(x) = (2x + 1)² : dérivée exacte 12 et approchée en x = 1 (attendus). Annonce de 0.5, où elle sert à remonter l'erreur. `CodeExplique` sur `chaine`. |
| 6 | Les probabilités | Des comptes aux probabilités ; tirer au hasard ; un générateur, c'est un calcul (`CodeExplique` sur `hasard` et `tirer`). Pari `tirage` ; la figure (sans verrou). |
| 7 | Des scores aux probabilités, et l'erreur | Softmax (tableau des 3 températures, depuis les attendus) ; l'erreur −ln p (tableau, depuis les attendus), dont ln 40, l'erreur de départ d'un modèle qui devine au hasard parmi 40 caractères, comme le mini-modèle. Pari `erreur`. `CodeExplique` sur `softmax` et `erreur-de-prediction`. |
| 8 | À grande échelle | `EncadreLabo` : les mêmes opérations par milliards ; 6 × N × D opérations pour l'entraînement (sources de `SOURCES_FORMULES.operations`) ; la taille des matrices de Llama 3 405B (`MODELES_PUBLICS`). `LiensProjet projet="0.2-maths"`, puis « À suivre » vers 0.3. |

**Acquis :**

| Clé | Texte | Gagné |
| --- | --- | --- |
| `scalaire` | « Le produit scalaire dit si deux vecteurs vont dans le même sens. » | pari `scalaire` |
| `matrices` | « Une matrice fois un vecteur, c'est un produit scalaire par ligne. » | pari `formes` |
| `pente` | « La pente dit de quel côté l'erreur descend. » | pari `pente` |
| `taux` | « Un taux trop grand fait sauter par-dessus le fond, ou s'en éloigner. » | pari `taux-grand` |
| `hasard` | « Les tirages ne suivent les probabilités qu'en moyenne. » | pari `tirage` |
| `erreur` | « L'erreur d'une prédiction, c'est −ln de la chance donnée à la bonne réponse. » | pari `erreur` |

Le pari `taux-moitie` n'a pas d'acquis : il prépare `taux-grand`.

**Défi :** trouver deux vecteurs perpendiculaires dans la figure ; son acquis s'appelle `perpendiculaires`, gagné par la figure.

- [ ] **Étape 1 : écrire les tests qui échouent.** `e2e/chapitre-0-2.spec.ts` : chapitre complet (tous les paris, deux vecteurs perpendiculaires réglés dans la figure, recap « 7 sur 7 »), choix des paris égaux à `paris-0-2.ts`, tableaux softmax et −ln p égaux aux attendus formatés, extraits égaux aux régions, pied « à venir », axe, débordement, typographie, lignes de 80 caractères au plus. Le test de `choixErreur` va dans `paris-0-2.test.ts`.
- [ ] **Étape 2 : vérifier l'échec**, écrire le chapitre, puis vérifier que tout passe, `figures-0-2.spec.ts` compris.
- [ ] **Étape 3 : captures et relecture** du chapitre entier, sur ordinateur et sur mobile.
- [ ] **Étape 4 : commit**, message « Chapitre 0.2 : les maths utiles (brouillon) ».
- [ ] **Étape 5 : parution de 0.1 et 0.2** (par le contrôleur, après la relecture de cette tâche ; choix 2).
  1. **Conditions** : les tâches 1 à 7 sont complètes au ledger ; `executer_notebooks.py` donne `ok` pour `0.1-python` et `0.2-maths` dans `.colab` ; les pages 0-1 et 0-2 n'ont aucun `[data-a-mesurer]`.
  2. **Question (AskUserQuestion)** : « 0.1 et 0.2 sont prêts. Je pousse et je les publie ? », avec les captures (ordinateur et mobile) et ce que la poussée contient (les commits depuis le dernier push). Sans oui, rien n'est poussé : la question revient à la tâche 15.
  3. **Sur un oui** :
     - pousser tel quel (les brouillons ne sont pas construits), puis attendre le vert des workflows Python (dont `notebooks-colab`) et Site ;
     - `git mv` de `0-1.mdx` et `0-2.mdx` vers `site/src/content/chapitres/`, mettre à jour les parcours qui les disaient « à venir » (`brouillons.spec.ts`, `navigation.spec.ts`, pied de 0.1 vers 0.2, page de la Partie 0) ;
     - tout vérifier comme en tâche 15, étape 1, puis `npm run build` sans essais : `dist/partie-0/0-1/` et `0-2/` existent, `0-3/` non ;
     - commit « Parution des chapitres 0.1 et 0.2 », pousser, attendre le déploiement, puis vérifier que les deux adresses publiques répondent 200 et que `0-3` répond 404.

### Tâche 8 : le projet 0.3 « vérifier son poste » et son notebook

**Fichiers :**

- Créer : `projets/0.3-poste/pyproject.toml`, `.python-version`, `uv.lock`, `README.md`
- Créer : `projets/0.3-poste/poste/__init__.py`, `faits.py`, `diagnostic.py`, `appareil.py`, `essai.py`, `attendus.py`, `__main__.py`
- Créer : `projets/0.3-poste/sorties/processeur.txt` (sortie réelle, roue `cpu`, sur ce PC)
- Test : `projets/0.3-poste/tests/conftest.py`, `test_diagnostic.py`, `test_faits.py`, `test_appareil.py`, `test_essai.py`, `test_attendus.py`, `test_notebook.py`, `tests/attendus.json`
- Créer : `notebooks/0.3-poste.ipynb`

**Interfaces :**

- `pyproject.toml` : nom `poste`. Les blocs `[project.optional-dependencies]`, `[tool.uv] conflicts`, `[tool.uv.sources]` et `[[tool.uv.index]]` sont recopiés de `projets/forge/pyproject.toml`, avec `torch==2.15.0` (sans `datasets` ni le reste).
  - Ils sont encadrés par `# region: pytorch` et `# fin: pytorch`, pour le chapitre.
  - Marqueur pytest `gpu`, sauté quand CUDA est absente (`conftest.py`, comme dans forge).
  - Même groupe de développement qu'en 0.1. `.python-version` vaut `3.12`.
- `faits.py` :
  - `@dataclass(frozen=True) class Faits` : `systeme: str`, `python: str`, `torch: str | None`, `cuda_compilee: str | None` (`torch.version.cuda`), `cuda_disponible: bool`, `carte: str | None`, `capacite: tuple[int, int] | None`, `architectures: tuple[str, ...]`, `pilote: str | None`, `cuda_max_pilote: str | None`, `fils_processeur: int`, `fils_torch: int` ;
  - `relever_faits() -> Faits` : `platform`, `torch` s'il s'importe, et `nvidia-smi --query-gpu=driver_version --format=csv,noheader` plus la ligne « CUDA Version » de `nvidia-smi`. Un `FileNotFoundError` ou un délai dépassé (5 s) donne `None`. Elle ne crée de contexte CUDA que si `torch.cuda.is_available()`.
- `diagnostic.py`, région `diagnostiquer` :
  - `class Niveau(StrEnum)` : `BON = "bon"`, `ATTENTION = "attention"`, `PROBLEME = "probleme"` ;
  - `@dataclass(frozen=True) class Constat` : `niveau`, `cle: str`, `message: str`, `a_faire: str | None` ;
  - `diagnostiquer(f: Faits) -> list[Constat]`, avec ces règles, dans cet ordre :

| Clé | Niveau | Quand |
| --- | --- | --- |
| `torch_absent` | problème | `torch is None` (on s'arrête là) |
| `processeur_seul` | bon | `cuda_compilee is None` et pas de pilote |
| `roue_processeur` | attention | `cuda_compilee is None` et un pilote NVIDIA présent |
| `pilote_absent` | problème | roue CUDA, pas de pilote |
| `pilote_trop_ancien` | problème | roue CUDA, majeure de `cuda_max_pilote` < majeure de `cuda_compilee` |
| `carte_trop_recente` | problème | roue CUDA disponible, mais `sm_<maj><min>` de la capacité n'est pas dans `architectures` |
| `carte_invisible` | problème | roue CUDA, pilote présent, mais `cuda_disponible` faux, sans autre cause trouvée |
| `carte_prete` | bon | roue CUDA, disponible, architecture présente |
| `fils` | attention | en plus des autres : `fils_torch < fils_processeur` |

    Chaque constat d'attention ou de problème a un `a_faire` qui donne la commande à lancer. Par exemple, pour `roue_processeur` : « Lance `uv sync --extra gpu`, puis relance `uv run --extra gpu python -m poste`. »
  - `SITUATIONS: dict[str, Faits]` : `windows_cu132_rtx5070ti`, `windows_pypi_rtx5070ti`, `windows_cu126_rtx5070ti` (PyTorch 2.7 cu126, sans `sm_120`), `pilote_ancien` (CUDA 12.4 au plus, roue cu132), `sans_carte`, `colab_t4` (Linux, cu130, capacité 7.5), `fils_par_defaut` (8 sur 16).
- `appareil.py`, région `appareil` :
  - `class AppareilIndisponible(Exception)` ;
  - `choisir_appareil(demande: str | None = None) -> torch.device` : `demande`, sinon `FORGE_APPAREIL`, sinon `"auto"`. `"auto"` donne cuda si disponible, sinon cpu.
  - `"cuda"` sans carte lève `AppareilIndisponible("Tu as demandé la carte graphique (cuda), mais PyTorch ne la voit pas. Lance `uv run --extra gpu python -m poste` pour savoir pourquoi, ou mets FORGE_APPAREIL=cpu.")`.
  - Une autre valeur lève `ValueError` en nommant les trois valeurs permises.
- `essai.py`, région `essai` : `essai_de_calcul(appareil: str, taille: int = 512) -> EssaiCalcul(appareil, ecart_max, millisecondes)`. Un produit de matrices en float32 sur l'appareil, comparé à un calcul en float64 sur le processeur.
- `__main__.py` : `python -m poste [--enregistrer FICHIER]`.
  - Il imprime les faits, les constats (« bon », « attention », « problème », message, puis « À faire : … ») et l'essai sur chaque appareil disponible. La dernière ligne est « Diagnostic terminé : N problème(s). ».
  - Code de sortie 1 s'il y a un problème. Un `torch` absent ne donne jamais de trace brute.
  - `--enregistrer` écrit la même sortie en UTF-8 et LF, précédée de `# relevé le AAAA-MM-JJ`.
  - Le texte imprimé suit la typographie française, avec `"\u202f"`.
- `attendus.py` → `tests/attendus.json` : `{"situations": [[nom, {"faits": {…}, "constats": [{"niveau", "cle", "message", "a_faire"}]}], …]}`.
- **Le notebook** :
  - `!nvidia-smi` dans un `try` ;
  - puis le rapport de `relever_faits()` et `diagnostiquer()` ;
  - puis `essai_de_calcul` sur la carte si elle est là ;
  - sinon, la marche à suivre dans Colab : « Exécution > Modifier le type d'exécution > GPU ».
  - Il n'installe pas PyTorch et finit par « Diagnostic terminé ».

- [ ] **Étape 1 : écrire les tests qui échouent.**

```python
def cles(nom): return [c.cle for c in diagnostiquer(SITUATIONS[nom])]
def test_situations():
    assert cles("windows_cu132_rtx5070ti") == ["carte_prete"]
    assert "roue_processeur" in cles("windows_pypi_rtx5070ti")
    assert cles("sans_carte")[0] == "processeur_seul"
    assert "carte_trop_recente" in cles("windows_cu126_rtx5070ti")
    assert "pilote_trop_ancien" in cles("pilote_ancien")
    assert cles("colab_t4") == ["carte_prete"]
    assert "fils" in cles("fils_par_defaut")
def test_chaque_alerte_dit_quoi_faire():
    for f in SITUATIONS.values():
        for c in diagnostiquer(f):
            if c.niveau != Niveau.BON: assert c.a_faire
def test_torch_absent_sans_trace(): assert [c.cle for c in diagnostiquer(replace(SITUATIONS["sans_carte"], torch=None))] == ["torch_absent"]
def test_relever_faits_ici(): f = relever_faits(); assert f.torch and f.fils_processeur >= 1
# Ces tests cachent ou montrent la carte eux-mêmes : ils passent pareil avec la roue cpu et à la porte, avec la roue gpu.
def test_cuda_demande_sans_carte(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    with pytest.raises(AppareilIndisponible, match="python -m poste"): choisir_appareil("cuda")
def test_auto_et_variable(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    assert str(choisir_appareil()) == "cpu"
    monkeypatch.setenv("FORGE_APPAREIL", "cpu"); assert str(choisir_appareil()) == "cpu"
    with pytest.raises(ValueError, match="auto"): choisir_appareil("tpu")
@pytest.mark.gpu
def test_auto_prend_la_carte(): assert choisir_appareil().type == "cuda"
def test_essai_processeur(): assert essai_de_calcul("cpu").ecart_max < 1e-3
@pytest.mark.gpu
def test_essai_carte(): assert essai_de_calcul("cuda").ecart_max < 1e-3
def test_sortie_processeur_enregistree():
    t = (PROJET / "sorties" / "processeur.txt").read_text(encoding="utf-8")
    assert t.startswith("# relevé le ") and "Diagnostic terminé" in t and "\r" not in t
def test_notebook_sans_installation_de_torch_ni_api_recente():
    code = "".join(c.source for c in nbformat.read(NOTEBOOK, 4).cells if c.cell_type == "code")
    assert "pip install torch" not in code and "torch.accelerator" not in code and "torch.compile" not in code
```

  Plus `test_attendus_a_jour` et `test_notebook.py`, qui s'exécute ici sans carte.
- [ ] **Étape 2 : vérifier l'échec.** Commande : `. .\outils\env-forge.ps1; cd projets/0.3-poste; uv lock; uv run --extra cpu pytest -q`.
  - `uv lock` doit finir sans télécharger de roue de plus de 200 Mo (`uv lock -v` le montre).
  - Sinon, s'arrêter et prévenir le contrôleur.
- [ ] **Étape 3 : écrire le paquet, les attendus, le notebook et le README.** Le README donne les commandes PowerShell, Linux et Mac, et la marche à suivre pour chaque constat. Puis enregistrer la sortie réelle : `uv run --extra cpu python -m poste --enregistrer sorties/processeur.txt`. Le code de sortie est 0 : `roue_processeur` est une attention, pas un problème.
- [ ] **Étape 4 : vérifier que tout passe**, `-rs` compris : seul `test_essai_carte` est sauté, avec la raison « CUDA absente ».
- [ ] **Étape 5 : commit**, message « Projet 0.3 : vérifier son poste (diagnostic, appareil, essai de calcul), avec son notebook ».

### Tâche 9 : le chapitre 0.3 « Installer son poste »

**Fichiers :**

- Créer : `site/src/lib/partie-0/poste.ts`, `poste.test.ts`, `site/src/lib/partie-0/paris-0-3.ts`, `paris-0-3.test.ts`, `site/src/lib/partie-0/commandes.test.ts`
- Modifier : `site/src/lib/partie-0/commandes.ts`
- Créer : `site/src/brouillons/chapitres/0-3.mdx`
- Test : `site/e2e/chapitre-0-3.spec.ts`

**Interfaces :**

- Consomme : `projets/0.3-poste/tests/attendus.json`, `sorties/*.txt`, `MESURES_TON_IA` et `MATERIELS` du calculateur, `SortieCommande` et `BlocCommande`.
- `poste.ts` : `situation(nom: string): { faits: …; constats: Constat[] }`, qui lève une erreur si le nom manque.
- `commandes.ts`, ajouts : `NVIDIA_SMI`, `SYNC_GPU` (`uv sync --extra gpu`), `SYNC_CPU`, `VERIFIER_POSTE_GPU` (`uv run --extra gpu python -m poste`), `VERIFIER_POSTE_CPU`, `ALLER_AU_PROJET` (`cd forge-ia/projets/0.3-poste`).
- `commandes.test.ts` lit `projets/0.3-poste/pyproject.toml` en texte :
  - les extras `cpu` et `gpu` existent ;
  - les index `https://download.pytorch.org/whl/cu132` et `…/cpu` y sont ;
  - chaque `--extra X` de `commandes.ts` est un extra du fichier ;
  - `projets/0.3-poste/poste/__main__.py` existe.
- `paris-0-3.ts` :
  - `choixVitesse()`, pour « Pour entraîner ton IA, la carte va combien de fois plus vite que le processeur ? » : « 2 fois », « 10 fois », « {r} fois » (juste), avec r = `Math.round` du rapport des débits « tres_grand » de `MESURES_TON_IA` ;
  - `choixRouePypi()` : « Oui, la carte calcule », « Non : c'est la version pour processeur » (juste si la situation `windows_pypi_rtx5070ti` contient `roue_processeur`), « PyTorch refuse de s'importer » ;
  - `choixCarteTropRecente()`, pour une RTX 5070 Ti avec une ancienne roue cu126 : « Tout marche », « La carte est trop récente pour cette version » (juste si `carte_trop_recente`), « Le pilote est trop ancien ».
- **Ouverture :** la ligne que le lecteur veut voir à la fin du chapitre, tirée des attendus (situation `windows_cu132_rtx5070ti`, constat `carte_prete`), présentée comme une sortie de terminal.
- **Sources :** chaque fait de la recherche cité dans 0.3 (pilote 580, Toolkit inutile, roues de PyPI, Colab, conda) porte son lien et « vérifié le … », à la date où la tâche revérifie le lien.

| Étape | Titre | Contenu imposé |
| --- | --- | --- |
| 1 | Pourquoi une carte graphique | Calcul en parallèle ; le rapport mesuré de ton IA (`MESURES_TON_IA`, lien vers `docs/mesures/entrainement-2026-11.md`). Pari `vitesse`. |
| 2 | Le pilote, et rien d'autre | `nvidia-smi` (`BlocCommande`) ; pilote, CUDA dans les roues, inutilité du Toolkit ; pilote 580 ou plus pour CUDA 13 ; capacité 12.0 de la RTX 5070 Ti. Note : ce qui rend faux les anciens tutoriels (liste de la recherche). |
| 3 | Installer uv | Les trois commandes d'installation, `uv --version`, et uv qui installe Python lui-même. |
| 4 | Le projet et sa version de PyTorch | Cloner, `cd`, puis `CodeExplique langue="toml"` sur la région `pytorch`. Pourquoi deux extras : PyPI ne sert sous Windows que la version pour processeur (126,7 Mo contre plusieurs Go). Pari `pypi`. |
| 5 | Vérifier | `VERIFIER_POSTE_GPU`. `SortieCommande` sur `sorties/processeur.txt` (« sur ce PC, avec la version pour processeur »), puis sur `sorties/rtx-5070-ti.txt` (absent jusqu'à la porte : « La sortie sur la RTX 5070 Ti s'affichera ici : on la relève quand la carte sera libre. »). `CodeExplique` sur `diagnostiquer` et sur `appareil`. |
| 6 | Quand ça ne marche pas | Tableau des situations, depuis les attendus : situation, ce que dit le script, ce qu'il faut faire. Pari `trop-recente`. |
| 7 | Le processeur, Colab, Linux et Mac | 16 fils et 8 par défaut (mesure du plan 2) ; Colab : la carte de l'offre gratuite n'est pas garantie (souvent une T4, capacité 7.5), 12 h au plus, Python 3.13 et PyTorch 2.11 déjà installés (relevé du 03/11/2026, sources) ; Linux : PyPI sert déjà des roues CUDA ; Mac : pas de CUDA, MPS non testé par le site, donc le processeur. WSL2 n'est pas nécessaire. |
| 8 | À grande échelle | `EncadreLabo` : jusqu'à 16 384 H100 pour Llama 3 405B. Ce nombre n'est pas dans les données du calculateur : le citer depuis l'article de Llama 3 (arXiv 2407.21783, section 3.3), avec la date de vérification ; la T4 de Colab et la RTX 5070 Ti dans le même tableau typographié (mémoire, calcul, depuis `MATERIELS`). `LiensProjet projet="0.3-poste"`, puis « À suivre » vers 0.4. |

**Acquis :**

| Clé | Texte | Gagné |
| --- | --- | --- |
| `carte` | « Ta carte entraîne ton IA bien plus vite que ton processeur. » | pari `vitesse` |
| `roue` | « Sous Windows, il faut demander la version de PyTorch pour la carte. » | pari `pypi` |
| `depannage` | « Une carte trop récente pour sa version de PyTorch reste inutilisable. » | pari `trop-recente` |

**Défi :** lancer `python -m poste` sur ton PC et dans Colab, puis comparer les deux rapports.

- [ ] **Étape 1 : écrire les tests qui échouent.**
  - `poste.test.ts`, `paris-0-3.test.ts` (un seul choix juste ; vitesse égale au rapport arrondi) et `commandes.test.ts`.
  - `e2e/chapitre-0-3.spec.ts` :
    - le chapitre complet, recap « 3 sur 3 » ;
    - le tableau des situations égal aux attendus ;
    - la sortie du processeur égale au fichier, sans sa première ligne ;
    - exactement un `[data-a-mesurer]` (la carte) ;
    - les commandes affichées égales à `commandes.ts` ;
    - pied « à venir », axe, débordement (les `<pre>` défilent dans leur zone), typographie, lignes de prose de 80 caractères au plus.
- [ ] **Étape 2 : vérifier l'échec**, écrire le code et le chapitre, puis vérifier que tout passe.
- [ ] **Étape 3 : captures et relecture**, sur ordinateur et sur mobile.
- [ ] **Étape 4 : commit**, message « Chapitre 0.3 : installer son poste (brouillon, sortie de la carte à relever) ».

### Tâche 10 : le projet 0.4 « tenseurs », son notebook et son jumeau des formes

**Fichiers :**

- Créer : `projets/0.4-tenseurs/pyproject.toml`, `.python-version`, `uv.lock`, `README.md`
- Créer : `projets/0.4-tenseurs/tenseurs/__init__.py`, `appareil.py` (copie de 0.3), `formes.py`, `memoire.py`, `exemples.py`, `chrono.py`, `attendus.py`, `__main__.py`
- Créer : `projets/0.4-tenseurs/mesures/processeur.json` (provisoire, remesuré à la porte)
- Test : `projets/0.4-tenseurs/tests/conftest.py`, `test_formes.py`, `test_memoire.py`, `test_exemples.py`, `test_chrono.py`, `test_appareil.py`, `test_attendus.py`, `test_notebook.py`, `tests/attendus-formes.json`
- Créer : `notebooks/0.4-tenseurs.ipynb`
- Créer : `site/src/lib/partie-0/formes.ts`, `formes.test.ts`, `site/src/lib/partie-0/mesures.ts`, `mesures.test.ts`

**Interfaces :**

- `pyproject.toml` : comme 0.3 (nom `tenseurs`, extras, `.python-version` à 3.12, marqueur `gpu`).
- `appareil.py` : copie exacte de `projets/0.3-poste/poste/appareil.py`. `test_appareil.py` compare les octets quand l'original existe, et refait les tests d'appareil de 0.3.
- `formes.py`, régions `diffusion` et `produit` :
  - `forme_diffusee(a: tuple[int, ...], b: tuple[int, ...]) -> tuple[int, ...] | None` : la règle de la diffusion, en Python pur ;
  - `forme_produit(a, b) -> tuple[int, ...] | None` : les règles de forme de `torch.matmul` pour 1 à 3 dimensions, diffusion des dimensions de lot comprise.
- `memoire.py`, région `memoire` : `octets(forme: tuple[int, ...], dtype: torch.dtype) -> int`, c'est-à-dire le nombre d'éléments fois `torch.empty((), dtype=dtype).element_size()`.
- `exemples.py`, régions `creer`, `lire` et `calculer` : `exemple_creer()`, `exemple_lire()` et `exemple_calculer()`, de petites fonctions qui renvoient des tenseurs ou des nombres que les tests vérifient, et que le chapitre montre.
- `chrono.py`, régions `chrono` et `transfert` :
  - `chronometrer_produit(taille: int, appareil: str, fils: int | None = None, repetitions: int = 5, echauffement: int = 2) -> float` : la médiane en millisecondes, en float32. Elle règle puis rétablit `torch.set_num_threads`, et appelle `torch.cuda.synchronize()` sur la carte ;
  - `chronometrer_transfert(taille: int) -> float` : du processeur vers la carte ;
  - `nom_processeur() -> str` : sous Windows, la clé `ProcessorNameString` du registre (`winreg`), sinon `platform.processor()` ;
  - `mesurer(appareil: str, tailles=(64, 256, 1024, 2048, 4096), fils=None) -> dict`. Sur le processeur, les fils mesurés sont `(1, torch.get_num_threads(), os.cpu_count())`, sans doublon.
- **Format des mesures** (JSON, version 1) :

```json
{"version": 1, "releve_le": "2026-11-05", "appareil": "cpu", "nom": "AMD Ryzen 7 9800X3D 8-Core Processor",
 "torch": "2.15.0+cpu", "fils_par_defaut": 8, "fils_max": 16,
 "mesures": [{"taille": 64, "fils": 1, "millisecondes": 0.01}],
 "transfert_ms": null}
```

  Sur la carte, `fils` vaut `null`, et `transfert_ms` est un objet `{"4096": ms}`.
- `__main__.py`, `main(argv: list[str] | None = None) -> int` :
  - `python -m tenseurs mesurer --appareil cpu|cuda --sortie FICHIER` écrit les mesures (UTF-8, LF). Sans carte, `--appareil cuda` écrit le message d'`AppareilIndisponible` sur la sortie d'erreur, sans trace, et rend 2 ;
  - `python -m tenseurs formes "(3, 1)" "(4,)"` affiche les deux règles.
- `attendus.py` → `tests/attendus-formes.json`.
  - Toutes les formes de 1 à 3 dimensions de tailles 1 à 3 (39 formes), par paires (1 521 paires).
  - Pour chaque paire, la forme de `torch.broadcast_shapes` et celle de `torch.matmul` sur `torch.empty`, ou `null` en cas d'erreur.
  - Plus des cas de mémoire.
- `formes.ts` : `formeDiffusee(a: number[], b: number[]): number[] | null` et `formeProduit(a, b): number[] | null`, traductions du Python ; `memoireOctets(forme: number[], octetsParNombre: number): number`.
- `mesures.ts` : `interface MesuresChrono` (le format ci-dessus) ; `lireMesures(nom: 'processeur' | 'rtx-5070-ti'): MesuresChrono | null`, qui lit `projets/0.4-tenseurs/mesures/<nom>.json` à la construction, par `node:fs`, comme `CodeExplique`.
- **Le notebook** : créer, lire, calculer ; la diffusion avec `forme_diffusee` comparée à PyTorch (« Même règle que la page du site : oui ») ; la mémoire ; un chrono processeur et carte sur 256, 1 024 et 2 048, la carte seulement si elle est là. **L'exercice** : prédire la forme de `(2, 1, 3) + (4, 1)`.

- [ ] **Étape 1 : écrire les tests qui échouent.**

```python
assert forme_diffusee((3, 1), (4,)) == (3, 4) and forme_diffusee((2, 3), (3, 2)) is None
assert forme_produit((2, 3), (3, 4)) == (2, 4) and forme_produit((3,), (3,)) == ()
assert forme_produit((5, 2, 3), (3, 4)) == (5, 2, 4) and forme_produit((2, 3), (2, 3)) is None
def test_les_regles_sont_celles_de_pytorch():   # sur les 1 521 paires, contre torch.broadcast_shapes et torch.matmul
assert octets((4096, 4096), torch.float32) == 67_108_864 and octets((4096, 4096), torch.bfloat16) == 33_554_432
def test_mesurer_processeur_petit():  # mesurer("cpu", tailles=(64,)) : format, millisecondes > 0, fils 1 compris
def test_mesurer_carte_absente(monkeypatch, capsys):  # carte cachée : main(["mesurer", "--appareil", "cuda", "--sortie", …]) == 2, message français, pas de « Traceback », aucun fichier écrit
def test_mesures_processeur_enregistrees():  # mesures/processeur.json : version 1, appareil cpu, tailles (64…4096), fils 1 et fils_max
@pytest.mark.gpu
def test_mesurer_carte_petit(): ...
```

  Plus `test_exemples.py` (les valeurs que le chapitre commente), le test du notebook sans `pip install torch` ni API récente, `test_attendus_a_jour` et `test_notebook.py`. Côté site :

```ts
// formes.test.ts : les 1 521 paires de attendus-formes.json, pour les deux règles (toStrictEqual)
expect(memoireOctets([4096, 4096], 4)).toBe(67_108_864);
// mesures.test.ts : lireMesures('processeur') a le bon format ; lireMesures('rtx-5070-ti') vaut null tant que le fichier manque
```

- [ ] **Étape 2 : vérifier l'échec.** Commande : `. .\outils\env-forge.ps1; cd projets/0.4-tenseurs; uv lock; uv run --extra cpu pytest -q`. Même règle de taille de téléchargement qu'en tâche 8.
- [ ] **Étape 3 : écrire le paquet, les attendus, le notebook et le jumeau.** Puis mesurer le processeur, pendant un « go » : `uv run --extra cpu python -m tenseurs mesurer --appareil cpu --sortie mesures/processeur.json`.
  - Pendant la mesure, vérifier avec le Gestionnaire des tâches ou `psutil` que les 16 fils travaillent au réglage « tous ».
  - Noter dans le README que ces chronos sont provisoires.
- [ ] **Étape 4 : vérifier que tout passe** (pytest avec `-rs`, `npx vitest run src/lib/partie-0`).
- [ ] **Étape 5 : commit**, message « Projet 0.4 : tenseurs, formes vérifiées contre PyTorch, chronos du processeur, avec son notebook ».

### Tâche 11 : le chapitre 0.4 « Tenseurs et calcul sur GPU » et l'atelier des formes

**Fichiers :**

- Créer : `site/src/components/chapitres/0-4/AtelierFormes.svelte`, `TableauChronos.astro`
- Créer : `site/src/lib/partie-0/paris-0-4.ts`, `paris-0-4.test.ts`
- Créer : `site/src/brouillons/chapitres/0-4.mdx`
- Test : `site/e2e/chapitre-0-4.spec.ts`

**Interfaces :**

- Consomme : `formes.ts` et `mesures.ts` (tâche 10), `memoirePoidsOctets` et `MESURES_TON_IA`/`PRESETS_FORGE` du calculateur, `MATERIELS`, `REPERES_EFFICACITE`.
- **`AtelierFormes.svelte`**, props `{ verrou?: string; acquis?: string }`.
  - Canaux `formes:na` et `formes:nb` (nombre de dimensions, de 1 à 3), `formes:a0..a2` et `formes:b0..b2` (tailles de 1 à 6). Départ : A = (3, 1) et B = (4).
  - La phrase « A a la forme ([3], [1]) ; B a la forme ([4]). » ; testIds `formes-a-dims`, `formes-a-0`…, `formes-b-dims`, `formes-b-0`….
  - L'opération : deux `.bascule-soleil` à `aria-pressed`, « A + B » (`formes-op-plus`) et « A @ B » (`formes-op-produit`).
  - La grille (`<table data-test="formes-grille">`) : lignes A, B et résultat, dimensions alignées à droite. Une case étirée porte `data-etire="oui"` et un trait lavande pointillé.
  - Pour @, les deux dimensions qui doivent être égales sont soulignées.
  - Le résultat (`formes-resultat`) : « (3, 4) », ou « impossible ».
  - L'explication (`formes-explication`), par exemple :
    - « 3 et 4 diffèrent dans l'avant-dernière dimension, et aucun ne vaut 1 : PyTorch refuse. » ;
    - « A a 3 colonnes et B 2 lignes : pour A @ B, il en faut autant. ».
  - Acquis émis au premier produit @ possible avec un A de 3 dimensions.
- **`TableauChronos.astro`**, sans prop : il lit `lireMesures('processeur')` et `lireMesures('rtx-5070-ti')`.
  - Lignes : les tailles. Colonnes : « processeur, 1 fil », « … {fils_par_defaut} fils (réglage par défaut) », « … {fils_max} fils », « carte ». Des millisecondes à 3 chiffres significatifs, avec `nombre()`.
  - Si la carte manque, l'en-tête de sa colonne porte `data-a-mesurer` et chaque case dit « à mesurer ».
  - La légende donne le nom des appareils, la date de relevé et la version de PyTorch, depuis les fichiers. Le tableau est dans une `ZoneDefilable` (seuil 600).
- `paris-0-4.ts` :
  - `choixDiffusion()`, (3, 1) + (4,) : « (3, 4) » (juste, `formeDiffusee`), « (4, 3) », « Impossible » ;
  - `choixMemoire()`, 4 096 × 4 096 en float32 : « 16 Mo », « 64 Mo » (juste, `memoireOctets / 2²⁰`), « 4 Go ». Comme le calculateur (`OCTETS_PAR_GO = 1024³`), le site compte 1 Mo = 2²⁰ octets et 1 Go = 2³⁰ octets, et le chapitre le dit ;
  - `choixFils(m: MesuresChrono)`, « Avec {fils_max} fils au lieu de {fils_par_defaut}, le produit 4 096 × 4 096 va-t-il deux fois plus vite ? » : « Deux fois plus vite » si le rapport des chronos est ≥ 1,8, « Un peu plus vite » s'il va de 1,1 à 1,8, « Pas plus vite » en dessous. Garde : `fils_par_defaut < fils_max` ;
  - `choixPetiteMatrice(cpu, carte)` existe déjà, testé avec de fausses mesures, mais n'entre dans le chapitre qu'à la porte (tâche 16). Pour « Pour deux matrices 64 × 64, qui calcule le plus vite ? » : « Le processeur » ou « La carte », juste selon le meilleur chrono à la taille 64, et « Autant l'un que l'autre » si l'écart est sous 10 %.
- **Ouverture :** la forme du tenseur qui entre dans ton IA, (micro-lot, {contexte}, {dim}), avec `contexte` et `dim` lus dans `PRESETS_FORGE.tres_grand`, et le nombre de cases que cela fait pour un micro-lot de 1.

| Étape | Titre | Contenu imposé |
| --- | --- | --- |
| 1 | Des nombres rangés en dimensions | Scalaire, vecteur, matrice, tenseur à 3 dimensions. L'entrée de ton IA : (micro-lot, `contexte`) numéros, puis (micro-lot, `contexte`, `dim`) nombres, depuis `PRESETS_FORGE.tres_grand`. |
| 2 | Créer et lire | `CodeExplique` sur `creer` et `lire`. |
| 3 | Calculer | Opérations case par case, sommes sur une dimension, `@`. `CodeExplique` sur `calculer`. |
| 4 | La diffusion | Pari `diffusion`, qui ouvre `formes` ; l'atelier dans son verrou. `CodeExplique` sur `diffusion`. |
| 5 | Les types de nombres et la mémoire | float32, bfloat16, int64. Pari `memoire`. Les poids de ton IA en bf16 (`memoirePoidsOctets`). `CodeExplique` sur `memoire`. |
| 6 | Sur la carte | `.to(appareil)`, `choisir_appareil` (`CodeExplique` sur la région `appareil` de 0.4), attendre la carte avant de chronométrer (`chrono`), le coût du transfert (`transfert`). `TableauChronos`. |
| 7 | Les fils du processeur | 1 fil, le réglage par défaut et tous les fils, depuis le tableau. Pari `fils`. |
| 8 | À grande échelle | `EncadreLabo` : bf16 sur H100 (crête de `MATERIELS`), efficacités de PaLM et de Llama 3 (`REPERES_EFFICACITE`) avec leurs sources. `LiensProjet projet="0.4-tenseurs"`, puis « À suivre » vers 0.5. |

**Acquis :**

| Clé | Texte | Gagné |
| --- | --- | --- |
| `diffusion` | « Une dimension de taille 1 s'étire pour suivre l'autre. » | pari `diffusion` |
| `formes` | « Pour A @ B, les colonnes de A doivent égaler les lignes de B. » | atelier |
| `memoire` | « La mémoire d'un tenseur, c'est son nombre de cases fois la taille d'un nombre. » | pari `memoire` |
| `fils` | « Le processeur aussi calcule en parallèle, sur tous ses fils. » | pari `fils` |

La porte ajoutera `petite` : « Pour un petit calcul, la carte ne gagne pas toujours. »

**Défi :** trouver dans l'atelier deux formes à 3 dimensions qui se multiplient.

- [ ] **Étape 1 : écrire les tests qui échouent.** `paris-0-4.test.ts`, dont `choixFils` et `choixPetiteMatrice` sur de fausses mesures qui couvrent les trois verdicts. `e2e/chapitre-0-4.spec.ts` :
  - le chapitre complet, recap « 4 sur 4 » ;
  - l'atelier suit `formeDiffusee` et `formeProduit` sur une série de réglages au clavier, dont des cas impossibles et à 3 dimensions ;
  - le tableau est égal à `processeur.json` formaté ;
  - exactement un `[data-a-mesurer]` ;
  - extraits égaux aux régions, pied « à venir », axe, débordement, typographie, lignes de 80 caractères au plus ;
  - sans JavaScript, l'atelier montre (3, 1) + (4,) = (3, 4).
- [ ] **Étape 2 : vérifier l'échec**, écrire le code et le chapitre, puis vérifier que tout passe.
- [ ] **Étape 3 : captures et relecture**, sur ordinateur et sur mobile, avec l'atelier sur un cas étiré et sur un cas impossible.
- [ ] **Étape 4 : commit**, message « Chapitre 0.4 : tenseurs et calcul sur la carte, avec l'atelier des formes (brouillon, chronos de la carte à relever) ».

### Tâche 12 : le projet 0.5 « premier réseau », son notebook et son jumeau du neurone

**Fichiers :**

- Créer : `projets/0.5-reseau/pyproject.toml`, `.python-version`, `uv.lock`, `README.md`
- Créer : `projets/0.5-reseau/premier_reseau/__init__.py`, `appareil.py` (copie de 0.3), `neurone.py`, `a_la_main.py`, `avec_pytorch.py`, `attendus.py`, `__main__.py`
- Créer : `projets/0.5-reseau/sorties/processeur.txt`
- Test : `projets/0.5-reseau/tests/conftest.py`, `test_neurone.py`, `test_a_la_main.py`, `test_avec_pytorch.py`, `test_appareil.py`, `test_attendus.py`, `test_notebook.py`, `tests/attendus.json`
- Créer : `notebooks/0.5-reseau.ipynb`
- Créer : `site/src/lib/partie-0/neurone.ts`, `neurone.test.ts`

**Interfaces :**

- `pyproject.toml` : comme 0.3 (nom `premier-reseau`).
- `neurone.py`, région `neurone` :
  - `PORTES = {"et": [0, 0, 0, 1], "ou": [0, 1, 1, 1], "ou_exclusif": [0, 1, 1, 0]}`, dans l'ordre des points `POINTS = [(0, 0), (0, 1), (1, 0), (1, 1)]` ;
  - `GRILLE = [-2.0, -1.5, …, 2.0]` (9 valeurs) ;
  - `sortie_seuil(poids: tuple[float, float], biais: float, x: tuple[int, int]) -> int` : 1 si `poids[0]*x[0] + poids[1]*x[1] + biais > 0`, sinon 0 ;
  - `bien_classes(poids, biais, porte) -> int` ;
  - `meilleur_reglage(porte) -> tuple[int, tuple[float, float], float]` : le meilleur compte, puis le premier réglage qui l'atteint, en parcourant w1, w2 puis b dans l'ordre de la grille.
- `a_la_main.py`, régions `sigmoide`, `propager`, `erreur`, `retropropager`, `pas` et `entrainer`. Python pur, avec `math.exp` et `math.log` :
  - `DONNEES = list(zip(POINTS, PORTES["ou_exclusif"]))` ;
  - `GRAINE = 1234`, `TAUX = 1.0`, `NB_PAS = 3000` ;
  - `@dataclass class Reseau` : `w1: list[list[float]]` (2 × 2), `b1: list[float]`, `w2: list[float]`, `b2: float`. 9 poids en tout ;
  - `initialiser(graine: int) -> Reseau` : `random.Random(graine).uniform(-1, 1)`, dans l'ordre w1, b1, w2, b2 ;
  - `propager(r, x) -> Passage(z1, h, z2, p)` ;
  - `erreur(p: float, y: int) -> float` : l'entropie croisée binaire −[y ln p + (1 − y) ln(1 − p)] ;
  - `retropropager(r, passage, x, y) -> Gradients` : de la même forme que `Reseau`. La sortie donne `p − y` ;
  - `gradient_moyen(r, donnees) -> Gradients` ;
  - `pas(r, g, taux) -> Reseau` ;
  - `entrainer(r, donnees, taux, nb_pas) -> Historique(pertes: list[float], reseau: Reseau)` : sur tout le lot, une perte moyenne par pas, `pertes[0]` avant le premier pas ;
  - `predictions(r, donnees) -> list[float]`.
  - **Si la graine 1234 reste coincée** (perte finale ≥ 0,05, ou prédictions arrondies différentes de [0, 1, 1, 0]), prendre la plus petite graine au-dessus de 1234 qui converge, et le noter dans le README et dans `GRAINE`.
- `avec_pytorch.py`, régions `modele`, `autograd` et `entrainer-pytorch` :
  - `construire(r: Reseau) -> nn.Sequential` : Linear(2, 2), Sigmoid, Linear(2, 1), Sigmoid, en float64, avec les poids de `r` recopiés ;
  - `gradients_pytorch(modele, donnees) -> Gradients` : `nn.BCELoss()` en moyenne, puis `backward` ;
  - `entrainer_pytorch(modele, donnees, taux, nb_pas, appareil: str) -> HistoriqueTorch(pertes, reseau: Reseau, millisecondes: float)` : SGD ;
  - `appareil.py` : copie de 0.3, gardée identique par son test.
- `__main__.py` : `main(argv: list[str] | None = None) -> int`, lancé par `python -m premier_reseau entrainer [--appareil auto|cpu|cuda] [--enregistrer FICHIER]`. Une `AppareilIndisponible` est attrapée : son message va sur la sortie d'erreur, sans trace, et `main` rend 2. Il affiche :
  - le meilleur réglage du neurone pour chaque porte ;
  - l'entraînement à la main (perte au départ, tous les 500 pas, à la fin ; prédictions) ;
  - le plus grand écart entre les gradients de départ, à la main et par PyTorch (« 3,1 × 10⁻¹⁷ », par exemple) ;
  - l'entraînement PyTorch sur l'appareil, sa durée et le plus grand écart des poids finaux avec la main.

  `--enregistrer` suit le format de 0.3, avec sa ligne `# relevé le`.
- `attendus.py` → `tests/attendus.json` :
  - `neurone` : pour chaque porte, `meilleur_reglage`, et `bien_classes` sur toute la grille, en tableau ;
  - `entrainement` : `graine`, `taux`, `nb_pas`, `pertes` (les 3 001), `predictions` ;
  - `graines` : pour les graines 1 à `NB_GRAINES` (20), `true` si l'entraînement réussit (perte < 0,05 et bonnes prédictions arrondies). Si aucune des 20 ne reste coincée, ou si toutes le restent, passer `NB_GRAINES` à 100 et le dire dans le README.
- `neurone.ts` : `POINTS`, `PORTES`, `GRILLE`, `sortieSeuil`, `bienClasses` et `meilleurReglage`, traductions du Python.
- **Le notebook** : le neurone et ses portes ; le réseau à la main ; l'entraînement et sa courbe (texte) ; PyTorch et ses gradients égaux ; l'appareil. **L'exercice** : « avec une couche cachée d'un seul neurone, le réseau apprend-il le OU exclusif ? ». La correction montre que non, et la cellule affiche « Défi réussi » si la réponse donnée est `False`.

- [ ] **Étape 1 : écrire les tests qui échouent.**

```python
assert meilleur_reglage("et")[0] == 4 and meilleur_reglage("ou")[0] == 4
assert meilleur_reglage("ou_exclusif")[0] == 3
assert sortie_seuil((1.0, 1.0), -1.5, (1, 1)) == 1 and sortie_seuil((1.0, 1.0), -1.5, (1, 0)) == 0
def test_gradients_par_differences_finies():     # les 9 dérivées à la main contre (E(w+h) − E(w−h)) / 2h, écart < 1e-6
def test_gradients_a_la_main_egalent_pytorch():   # gradient_moyen(r) contre gradients_pytorch(construire(r)) : écart < 1e-12
def test_le_reseau_apprend():
    h = entrainer(initialiser(GRAINE), DONNEES, TAUX, NB_PAS)
    assert h.pertes[-1] < 0.05 and [round(p) for p in predictions(h.reseau, DONNEES)] == [0, 1, 1, 0]
def test_pytorch_suit_la_main():                  # sur le processeur, poids finaux à moins de 1e-6
def test_cuda_demande_sans_carte_message_francais(monkeypatch, capsys):   # carte cachée, comme en 0.3
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    assert main(["entrainer", "--appareil", "cuda"]) == 2
    err = capsys.readouterr().err
    assert "FORGE_APPAREIL=cpu" in err and "Traceback" not in err
@pytest.mark.gpu
def test_pytorch_sur_la_carte():                  # entrainer_pytorch(…, "cuda") : poids finaux à moins de 1e-6 de ceux du processeur
def test_sortie_processeur_enregistree(): ...
```

  Plus le test du notebook sans `pip install torch` ni API récente, `test_attendus_a_jour` et `test_notebook.py`. `neurone.test.ts` vérifie `meilleurReglage` et `bienClasses` contre `attendus.json` (`toStrictEqual`).
- [ ] **Étape 2 : vérifier l'échec**, puis écrire le paquet, les attendus et le notebook. Commande : `. .\outils\env-forge.ps1; cd projets/0.5-reseau; uv lock; uv run --extra cpu pytest -q`.
- [ ] **Étape 3 : enregistrer la sortie réelle.** Commande : `uv run --extra cpu python -m premier_reseau entrainer --appareil cpu --enregistrer sorties/processeur.txt`.
- [ ] **Étape 4 : vérifier que tout passe** (pytest avec `-rs`, `npx vitest run src/lib/partie-0`).
- [ ] **Étape 5 : commit**, message « Projet 0.5 : un neurone, puis un réseau à la main et avec PyTorch, avec son notebook ».

### Tâche 13 : l'avant-goût, prénoms du départ et de la fin côte à côte (M3)

**Fichiers :**

- Modifier : `site/src/components/demos/MiniModele.svelte`
- Modifier : `site/e2e/mini-modele.spec.ts` (test « avant-goût »)

**Interfaces :**

- Consomme : `EtatDemo.echantillons` (le pas 0 vient de `initial`), `prenomAffiche`, `entier`.
- **Avec le préréglage `avant-gout` seulement**, la liste « Les prénoms qu'il invente au pas N » est remplacée par un tableau `<table data-test="mini-avant-apres">` :
  - `<caption>` « Les prénoms inventés, avant et après l'entraînement », de l'allure de `.intro-liste` ;
  - deux colonnes `<th scope="col">`, et deux `<td>` par ligne, sans en-tête de ligne : « Au départ, pas 0 », et « Après l'entraînement » tant qu'aucune validation n'a suivi le pas 0, puis « Au pas {entier(N)} » pour le dernier pas d'échantillons (« Au pas 600 » à la fin) ;
  - 8 lignes. À gauche, les prénoms du pas 0 ; à droite, ceux du dernier pas, ou « — » (« pas encore » pour les lecteurs d'écran) avant le premier ;
  - « (existe déjà) » et « (aucune lettre) » comme dans la liste actuelle ;
  - avant le lancement, une phrase sous le tableau (`data-test="mini-avant-apres-invite"`) : « Lance l'entraînement : ses prénoms viendront se ranger à droite. »
- Le `<details>` « Les prénoms des étapes d'avant » ne garde que les pas strictement entre 0 et le dernier.
- Le préréglage `complet` ne change pas.
- Sans JavaScript, la colonne de gauche est complète, et celle de droite en tirets.

- [ ] **Étape 1 : réécrire le test de l'avant-goût, qui échoue.**

```ts
const t = demo(page, 'avant-gout').locator('[data-test="mini-avant-apres"]');
await expect(t.locator('tbody tr')).toHaveCount(AVANT_GOUT.nbEchantillons);
// Chaque ligne a deux <td>, sans en-tête de ligne.
const gauche = (await t.locator('tbody tr td:nth-child(1)').allInnerTexts()).map((s) => s.trim());
const attendu = etatInitial('avant-gout').echantillons.map((p) => prenomAffiche(p.texte) + (p.existe ? ' (existe déjà)' : ''));
expect(gauche).toEqual(attendu);
// lancer, attendre « Terminé » : l'en-tête de droite dit « Au pas 600 », et ses 8 prénoms sont ceux du dernier pas
// la colonne de gauche n'a pas changé ; details.avant ne contient ni « au pas 0 » ni « au pas 600 »
// 390 px : aucun débordement ; typographie ; sans JavaScript : gauche complète, droite en tirets
```

- [ ] **Étape 2 : vérifier l'échec, écrire le changement, puis vérifier que tout passe.** Commandes : `npx playwright test e2e/mini-modele.spec.ts --workers=4`, puis toute la suite, `npm run check:svelte` et `npx vitest run`.
- [ ] **Étape 3 : captures et relecture** de l'avant-goût, avant le lancement et à la fin, sur ordinateur et sur mobile.
- [ ] **Étape 4 : commit**, message « Avant-goût du mini-modèle : les prénoms du départ et de la fin côte à côte ».

### Tâche 14 : le chapitre 0.5 « Premier réseau de neurones » et l'atelier du neurone

**Fichiers :**

- Créer : `site/src/components/chapitres/0-5/AtelierNeurone.svelte`, `CourbeXor.astro`
- Créer : `site/src/lib/partie-0/paris-0-5.ts`, `paris-0-5.test.ts`
- Créer : `site/src/brouillons/chapitres/0-5.mdx`
- Test : `site/e2e/chapitre-0-5.spec.ts`

**Interfaces :**

- Consomme : `neurone.ts` et les attendus de 0.5 (tâche 12), `DemoMiniModele` avec l'avant-goût (tâche 13), `etatInitial('avant-gout')`, `courbe.ts` (`reduirePoints`, `cheminCourbe`, `Echelle`), `SortieCommande`, et `MODELES_PUBLICS`/`PRESETS_FORGE`.
- **`AtelierNeurone.svelte`**, props `{ verrou?: string; acquis?: string }`.
  - Canaux `neu:w1`, `neu:w2` et `neu:b`, de −2 à 2 par pas de 0,5. Départ : w1 = 1, w2 = 1, b = 0, soit 2 points sur 4 pour ET : le lecteur a quelque chose à régler. Affichage « −1,5 » par `texte` ; testIds `neu-w1`, `neu-w2`, `neu-b`.
  - La porte : trois `.bascule-soleil` à `aria-pressed`, « ET », « OU » et « OU exclusif » (`neu-porte`, `data-porte`). Départ : ET.
  - Le dessin (`neu-dessin`, `role="img"`) : le carré de 0 à 1, les 4 points (plein indigo pour 1, vide pour 0), la droite w1·x1 + w2·x2 + b = 0, et le côté « 1 » en fond brume. Chaque point bien classé porte une coche menthe, chaque point mal classé une croix corail, et le texte le dit aussi.
  - Le bilan (`neu-bilan`) : « 3 points sur 4 bien classés. » ou « Les 4 points sont bien classés. ».
  - Si w1 = w2 = 0, pas de droite, et le message « Sans poids, le neurone répond pareil partout : 1 si b > 0, sinon 0. »
  - Acquis émis au premier 4 sur 4 sur ET ou sur OU obtenu par un réglage du lecteur.
- **`CourbeXor.astro`**, props `{ pertes: number[] }`.
  - Un SVG statique en `viewBox` 640 × 240, avec l'échelle `{ largeur: 640, hauteur: 240, xMax: pertes.length - 1, yMin: 0, yMax: 1,1 × la plus grande perte }`, `cheminCourbe(reduirePoints(pertes, 600), e)`.
  - Les axes « pas » et « erreur », en Gabarito 13 px et encre douce ; `role="img"` et `aria-label` « Erreur du réseau : 0,754 au pas 0, 0,021 au pas 3 000. », avec les valeurs réelles.
- `paris-0-5.ts` :
  - `choixXor()` : « Oui, avec les bons poids », « Non : au mieux 3 points sur 4 » (juste si `meilleurReglage('ou_exclusif')[0] === 3`), « Non : au mieux 2 points sur 4 » ;
  - `choixGradientSortie()`, pour « La sortie vaut 0,9, la bonne réponse 0 : que vaut p − y ? » : « −0,9 », « 0,9 » (juste, `0.9 - 0`, formaté), « 0,1 » ;
  - `choixExact()`, pour « Après 3 000 pas, le réseau répond-il exactement 0 et 1 ? » : « Oui, exactement », « Non : il s'en approche, de {min} à {max} » (juste si aucune prédiction des attendus ne vaut exactement 0 ou 1 ; bornes calculées) ;
  - `choixCoince()`, pour « Sur {NB_GRAINES} départs au hasard, combien de fois le réseau reste-t-il coincé ? » : « Jamais », « {k} fois » (juste, compté dans `graines`), « À chaque départ ». Garde : 1 ≤ k < `NB_GRAINES`.
  - Si une garde tombe, revoir le pari et le dire dans un commentaire.
- **Ouverture :** les deux premiers prénoms que le mini-modèle invente avant tout entraînement (`etatInitial('avant-gout')`), et la promesse : à la fin du chapitre, la même boucle qu'on aura écrite à la main lui apprendra à faire mieux. Aucun résultat de pari n'y est dévoilé.

| Étape | Titre | Contenu imposé |
| --- | --- | --- |
| 1 | Un neurone | Somme pondérée, seuil. L'atelier, sans verrou, sur ET. `CodeExplique` sur `neurone`. |
| 2 | Le OU exclusif | Pari `xor` ; l'atelier sur « OU exclusif » le confirme. |
| 3 | Deux couches | Réseau 2-2-1, sigmoïde, 9 poids. `CodeExplique` sur `sigmoide` et `propager`. |
| 4 | L'erreur | L'entropie croisée, renvoi au −ln p de 0.2. `CodeExplique` sur `erreur`. |
| 5 | Remonter l'erreur | La règle de la chaîne de 0.2, appliquée ; `p − y` à la sortie. Pari `gradient`. `CodeExplique` sur `retropropager`. |
| 6 | Entraîner à la main | `CodeExplique` sur `pas` et `entrainer`. `CourbeXor` avec les pertes des attendus ; un tableau des 4 prédictions. Paris `exact` et `coince`. |
| 7 | Le même, avec PyTorch | `CodeExplique` sur `modele`, `autograd` et `entrainer-pytorch`. L'écart des gradients, depuis `sorties/processeur.txt` (`SortieCommande`). |
| 8 | Sur la carte | `choisir_appareil`. `SortieCommande` sur `sorties/rtx-5070-ti.txt` (absent jusqu'à la porte : « La sortie sur la RTX 5070 Ti s'affichera ici : on la relève quand la carte sera libre. »). Aucune phrase sur qui va le plus vite avant la porte. |
| 9 | La même boucle, en plus grand | L'avant-goût : `<DemoMiniModele preset="avant-gout" nom="avant-gout" acquis="avant-gout" />`. La phrase cite le nombre de poids (`etatInitial('avant-gout').nbParametres`) et les deux premiers prénoms du départ, calculés. Lien vers 1.5 par le composant. |
| 10 | À grande échelle | `EncadreLabo` : 9 poids ici, `PRESETS_FORGE.tres_grand.parametres` pour ton IA, 175 milliards pour GPT-3 et 405 milliards pour Llama 3 405B (`MODELES_PUBLICS`, avec leurs sources). `LiensProjet projet="0.5-reseau"`, puis « À suivre » vers 1.1. |

**Acquis :**

| Clé | Texte | Gagné |
| --- | --- | --- |
| `neurone` | « Un neurone fait une somme pondérée, puis décide. » | atelier |
| `xor` | « Un seul neurone ne sait pas tout séparer : il faut une couche de plus. » | pari `xor` |
| `gradient` | « L'erreur remonte couche par couche, par la règle de la chaîne. » | pari `gradient` |
| `entraine` | « Entraîner, c'est répéter : propager, mesurer l'erreur, remonter, corriger. » | pari `exact` |
| `coince` | « Selon son départ, un réseau peut rester coincé. » | pari `coince` |
| `avant-gout` | « La même boucle fait apprendre un vrai petit modèle. » | fin de l'avant-goût |

**Défi :** avec le même neurone, classer ET puis OU en ne changeant que b.

- [ ] **Étape 1 : écrire les tests qui échouent.** `paris-0-5.test.ts`. `e2e/chapitre-0-5.spec.ts` :
  - le chapitre complet, avec l'avant-goût mené jusqu'au bout (il va toujours vite ; délai de 120 s), recap « 6 sur 6 » ;
  - l'atelier suit `bienClasses` sur une série de réglages au clavier, dont w1 = w2 = 0 ;
  - le tableau de l'avant-goût est présent, et sa colonne de gauche est égale à `etatInitial` ;
  - la courbe a un `aria-label` aux valeurs des attendus et aucun `NaN` ;
  - exactement un `[data-a-mesurer]` ;
  - extraits égaux aux régions, pied « à venir » (1.1), axe, débordement, typographie, lignes de 80 caractères au plus ;
  - sans JavaScript, le neurone est sur ET, avec « 2 points sur 4 bien classés. » ;
  - au clavier, b réglé à −1,5 sur ET donne « Les 4 points sont bien classés. » et gagne `neurone`.
- [ ] **Étape 2 : vérifier l'échec**, écrire le code et le chapitre, puis vérifier que tout passe, `e2e/mini-modele.spec.ts` compris.
- [ ] **Étape 3 : captures et relecture**, sur ordinateur et sur mobile : l'atelier sur le OU exclusif, la courbe, l'avant-goût à la fin.
- [ ] **Étape 4 : commit**, message « Chapitre 0.5 : premier réseau de neurones, à la main puis avec PyTorch (brouillon, sortie de la carte à relever) ».

### Tâche 15 : bilan sans la carte, et présentation à l'utilisateur

**Fichiers :**

- Modifier : `projets/0.*/README.md` (versions finales), `README.md` (liste des projets)

- [ ] **Étape 1 : tout vérifier.** Noter les durées.
  - Pour chaque `projets/0.*` : `uv run pytest -q`, avec `--extra cpu` pour 0.3 à 0.5 ;
  - `cd site; npx vitest run`, `npm run check:svelte`, `npx astro check`, `npx playwright test --workers=4` ;
  - `npm run build` sans essais, puis les deux garde-fous de `site.yml` rejoués à la main : aucun dossier `dist/partie-0/0-*`, et aucun prénom dans `dist/_astro`.

  Attendu : tout passe.
- [ ] **Étape 2 : finir les README.** Pour chaque projet :
  - ce qu'il fait et le chapitre qu'il accompagne ;
  - les commandes PowerShell (et Linux ou Mac quand elles diffèrent), tests compris ;
  - pour 0.3 à 0.5, les deux extras, et ce que donne une machine sans carte ;
  - les régions balisées montrées par le chapitre.

  Le README racine liste les cinq projets.
- [ ] **Étape 3 : relire la Partie 0 d'un bout à l'autre**, comme un débutant qui ne sait rien.
  - Chaque terme est expliqué avant d'être utilisé, et chaque chapitre annonce le suivant.
  - Aucune affirmation n'est datée sans source.
  - Corriger dans la tâche concernée, par un commit séparé.
- [ ] **Étape 4 : montrer les brouillons.** Lancer `npm run build:essais`, puis `npm run preview` (port 8530). Donner les cinq adresses `/forge-ia/partie-0/0-1/` à `0-5/`, avec des captures ordinateur et mobile. Puis :
  - demander avec AskUserQuestion si les chapitres conviennent ; si 0.1 et 0.2 n'ont pas encore paru, reposer leur question de parution (tâche 7, étape 5) ;
  - arrêter le serveur ;
  - si l'utilisateur demande des changements, les faire dans la tâche concernée, puis redemander.
- [ ] **Étape 5 : commit**, message « Partie 0 : README des projets et bilan avant la carte ».

### Tâche 16 : vérification sur la carte graphique (porte)

Cette tâche n'attend plus la fin de l'entraînement de ton IA. L'essai du 04/11/2026 (charge qui imite les notebooks 0.3 à 0.5, trois minutes par phase, pendant l'entraînement) a donné :

- **sur le processeur (16 fils), en même temps** : l'entraînement garde sa vitesse (17 198 jetons par seconde, contre 17 212 sans charge), et la charge va vite ;
- **sur la carte, en même temps** : 86 Mio de mémoire seulement, sans débordement (14,9 Go sur 16,3), mais l'entraînement perd environ 11 % (15 368 jetons par seconde) tant que la charge tourne, et la charge est dix fois plus lente qu'au processeur ;
- donc **une mesure de durée prise sur la carte pendant l'entraînement serait fausse** : les chronos et les sorties publiés se relèvent carte au repos.

D'où deux temps :

- **les vérifications** (tests `gpu` et notebooks sur la carte) tournent en même temps que l'entraînement : quelques minutes à 11 % de vitesse en moins, moins cher qu'une pause ;
- **les mesures** se relèvent pendant une courte pause de l'entraînement, faite par le contrôleur ; ou sans pause si l'entraînement est déjà fini.

L'utilisateur a demandé le 04/11/2026 de tout faire au processeur quand c'est possible, et sinon de faire la pause. Les trois sorties de la carte contiennent un temps (l'essai de calcul de 0.3 en millisecondes, les chronos de 0.4, la durée de l'entraînement de 0.5) : elles ne peuvent pas venir du processeur. La pause est donc réduite au minimum :

- tout ce qui ne mesure pas de temps sur la carte se fait avant, pendant l'entraînement (étapes 1 et 2) ;
- pendant la pause, seulement les quatre commandes de l'étape 4, enchaînées sans attente ; durée visée : 10 minutes ;
- l'entraînement repart aussitôt la dernière commande finie, avant toute écriture de chapitre.

Conditions : les tâches 1 à 15 sont complètes au ledger, et l'utilisateur a dit « go » (il ne joue pas). Aucune autre question avant de commencer : l'utilisateur a demandé de ne pas perdre de temps.

**Fichiers :**

- Créer : `projets/0.3-poste/sorties/rtx-5070-ti.txt`, `projets/0.4-tenseurs/mesures/rtx-5070-ti.json`, `projets/0.5-reseau/sorties/rtx-5070-ti.txt`
- Modifier : `projets/0.4-tenseurs/mesures/processeur.json` (remesuré dans la même séance)
- Modifier : `site/src/brouillons/chapitres/0-4.mdx` (pari `petite`, acquis `petite`, phrase qui compare carte et processeur) et `0-5.mdx` (une phrase sur la durée, carte contre processeur)
- Modifier : `site/e2e/chapitre-0-3.spec.ts`, `chapitre-0-4.spec.ts`, `chapitre-0-5.spec.ts` (zéro `[data-a-mesurer]`, nouveau pari)
- Modifier : `projets/0.4-tenseurs/README.md` (les chronos ne sont plus provisoires)

- [ ] **Étape 1 : préparer, sans rien télécharger**, pendant l'entraînement.
  - `. .\outils\env-forge.ps1`, puis vérifier qu'il reste au moins 25 Go sur D:.
  - Dans 0.3, 0.4 et 0.5 : `uv sync --extra gpu --offline`. Si uv réclame une roue absente du cache, s'arrêter et demander à l'utilisateur avant tout téléchargement de plusieurs Go.
- [ ] **Étape 2 : lancer les tests sur la carte**, pendant l'entraînement. Dans chaque projet : `uv run --extra gpu pytest -q -rs`. Attendu : tout passe, aucun test `gpu` n'est sauté, et le `test_notebook.py` de chaque projet a tourné sur la carte (le notebook le dit). Le contrôleur lit la vitesse de l'entraînement dans son journal avant et après : la baisse doit s'arrêter avec les tests.
- [ ] **Étape 3 : mettre l'entraînement en pause** (contrôleur ; sauter cette étape si l'entraînement est fini).
  - Arrêter le chien de garde (et tout Python qui exécute `chien-de-garde.py`), puis lancer `D:\forge-ia-donnees\journaux\pause-entrainement.ps1`.
  - Attendre l'évènement `pause` dans le journal, puis vérifier avec `nvidia-smi` : utilisation sous 10 %, plus aucun processus `python -m forge`.
  - Noter l'heure et le pas de la pause dans le ledger du plan 2.
- [ ] **Étape 4 : relever les sorties et les mesures**, carte au repos (aucun jeu, `nvidia-smi` sous 10 %) :
  - `cd projets/0.3-poste; uv run --extra gpu python -m poste --enregistrer sorties/rtx-5070-ti.txt` : code de sortie 0, constat `carte_prete` ;
  - `cd projets/0.4-tenseurs` :
    - `uv run --extra gpu python -m tenseurs mesurer --appareil cpu --sortie mesures/processeur.json`, en vérifiant que les 16 fils travaillent au réglage « tous » ;
    - `uv run --extra gpu python -m tenseurs mesurer --appareil cuda --sortie mesures/rtx-5070-ti.json` ;
  - `cd projets/0.5-reseau; uv run --extra gpu python -m premier_reseau entrainer --appareil cuda --enregistrer sorties/rtx-5070-ti.txt`.
- [ ] **Étape 5 : reprendre l'entraînement** (contrôleur ; sauter si l'entraînement est fini), aussitôt les mesures relevées.
  - `entrainement-principal.ps1 -Reprendre`, puis relancer le chien de garde une fois l'évènement `reprise` écrit dans le journal (sinon il voit la pause et s'arrête).
  - Vérifier les premiers pas, puis noter la reprise et la durée de la pause dans le ledger du plan 2.
- [ ] **Étape 6 : compléter les chapitres, tests d'abord.**
  - Les trois parcours attendent zéro `[data-a-mesurer]`.
  - Celui de 0.4 attend le pari `petite`, avec `choixPetiteMatrice(lireMesures('processeur'), lireMesures('rtx-5070-ti'))` et l'acquis `petite`, recap « 5 sur 5 ».
  - Puis écrire, dans 0.4 et 0.5, une phrase qualitative qui dit ce que montrent les mesures. Elle ne contient aucun nombre tapé à la main ; les nombres sont dans le tableau et dans les sorties.
  - Le relecteur vérifie chaque phrase contre les fichiers.
- [ ] **Étape 7 : tout vérifier** comme en tâche 15, étape 1. Pytest repasse avec `--extra cpu` : l'intégration continue le fait ainsi. `executer_notebooks.py` repasse dans `.colab` pour 0.3 à 0.5.
- [ ] **Étape 8 : commit**, message « Partie 0 : sorties et chronos de la RTX 5070 Ti, relevés carte au repos ».
- [ ] **Étape 9 : parution de 0.3 à 0.5** (contrôleur), comme la tâche 7, étape 5, avec ces différences :
  - la question : « 0.3, 0.4 et 0.5 sont prêts. Je pousse et je les publie ? » (avec 0.1 et 0.2 s'ils n'ont pas encore paru) ;
  - 0.5 contient le mini-modèle : appliquer le point 4 de la section « Parution d'un chapitre » du README (écarter `dist/_astro/travailleur-*.js` de la recherche du prénom dans `site.yml`) ;
  - après le déploiement, les cinq adresses `/forge-ia/partie-0/0-1/` à `0-5/` répondent 200.
- [ ] **Étape 10 : écrire le jalon dans la mémoire partagée**, si elle répond (sinon, le dire dans le compte rendu) : « Projet forge-ia (La Forge IA) : Partie 0 (chapitres 0.1 à 0.5) écrite, avec ses cinq projets (projets/0.1-python à 0.5-reseau) et ses notebooks (exécutés automatiquement, comme sur Colab sans carte, et sur la RTX 5070 Ti) ; publiée le JJ/MM/AAAA ». Sans parution, écrire « en brouillon » à la place.
- [ ] **Étape 11 : compte rendu à l'utilisateur.** Les chiffres relevés (carte, processeur et nombre de fils utilisés), la durée de la pause de l'entraînement, le chemin des fichiers, et la proposition d'écrire le plan 5.

---

## Décisions de l'utilisateur (04/11/2026)

- **Notebooks** : « je ne lancerai pas les notebooks un par un, trouve une solution pour le faire de ton côté ; si je trouve un problème en utilisant, je te le dis ». D'où le job `notebooks-colab` (tâche 2) et le choix 2.
- **Parution** : « je te laisse me dire quand il peut être publié sur le site ». D'où la parution de 0.1 et 0.2 en tâche 7, et celle de 0.3 à 0.5 en tâche 16, chacune après un oui.
- **La carte pendant l'entraînement** : « essaie et vois comment ça passerait si tu les lances en même temps, sur la carte ou le processeur, pour ne pas perdre de temps ». D'où la tâche 16 telle qu'elle est écrite, d'après l'essai du 04/11/2026.
