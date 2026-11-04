# La Forge IA, vague 1, plan 3 : les démos restantes

> **Pour les agents qui exécutent ce plan :** SOUS-SKILL REQUIS : utiliser superpowers:subagent-driven-development (recommandé) ou superpowers:executing-plans pour réaliser ce plan tâche par tâche. Les étapes utilisent des cases à cocher (`- [ ]`).

**But :** construire et tester les trois démos qui manquent à la vague 1 : le mini-modèle qui apprend dans le navigateur (avec son avant-goût pour 0.5), l'animation de l'attention et le calculateur de coût. Ce sont des composants que les chapitres des plans 4 et 5 poseront tels quels, avec leurs paris calculés, essayés d'abord sur des pages d'essai.

**Architecture :**

- **Un moteur numérique jumeau**, écrit deux fois à l'identique :
  - en Python pur, sans numpy (`projets/mini-modele/`) ;
  - en TypeScript (`site/src/lib/mini-modele/`).

  Il a ses propres `exp`, `log` et `cos`, faites seulement de `+ − × ÷`, un hasard en arithmétique entière (SplitMix32) et un ordre de sommation fixé. Les deux langages donnent les mêmes nombres au bit près. Le Python écrit les attendus ; pytest, Vitest et les navigateurs les relisent.
- **Le mini-modèle** est un transformer d'une couche, entraîné sur des prénoms français. Il calcule dans un Web Worker, piloté côté page par un réducteur pur.
- **L'animation de l'attention** réutilise la fonction d'attention du mini-modèle, sur un exemple écrit à la main.
- **Le calculateur** est du TypeScript pur, avec des données sourcées et datées, et un jumeau des formules de `forge`.
- **Les démos** sont des îlots Svelte 5, rangés dans `site/src/components/demos/`. On les essaie sur des pages `site/src/essais/*.mdx`, construites seulement avec `FORGE_ESSAIS=1`.

**Pile technique :** celle du plan 1 (Astro 7.4, Svelte 5.57, TypeScript, Vitest, Playwright avec `@axe-core/playwright`), plus Python 3.12 avec uv et pytest. Aucune nouvelle dépendance npm ni Python.

**Spécification :** `docs/superpowers/specs/2026-11-02-forge-ia-design.md`, surtout les sections 5 (paris, verrous, atelier), 6 (allure et plancher de qualité) et 7 (démos, cohérence des moteurs).

**Plans précédents, livrés :**

- `docs/superpowers/plans/2026-11-02-forge-ia-v1-p1-fondations.md` : gabarit, paris, verrous, canaux, `NombreManipulable`, pages d'essai, jumeau BPE ;
- `docs/superpowers/plans/2026-11-03-forge-ia-v1-p2-moteur.md` : paquet `forge`, mesures de ton IA.

## Place de ce plan dans la vague 1

C'est le plan 3 du découpage fixé par le plan 1 : « les démos restantes : mini-modèle qui apprend dans le navigateur, animation de l'attention, calculateur de coût ».

Ce plan ne rédige aucun chapitre :

- le plan 4 écrit la Partie 0, et pose l'avant-goût en 0.5 ;
- le plan 5 écrit 1.1, 1.2, 1.4, 1.5 et 1.6, l'annuaire, le glossaire et les annexes.

Il livre des composants, leurs paris, leurs régions de code balisées et des pages d'essai qu'on peut construire, tester et montrer avant les chapitres.

## Recherche faite avant ce plan (le 03/11/2026)

Toutes les sources ont été lues le 03/11/2026. Les chiffres de matériel et de prix sont recopiés dans la tâche 10, avec leur source.

- **`Math.exp`, `Math.log`, `Math.cos` ne sont pas reproductibles.** ECMAScript les dit « approchées selon l'implémentation » (https://read262.netlify.app/numbers-and-dates/math-object).
  - V8 est passé de fdlibm à la libm de LLVM entre mai et octobre 2026 (https://api.github.com/repos/v8/v8/commits?path=src/base/ieee754.cc).
  - Firefox garde fdlibm, et Safari appelle la libm du système.
  - Côté Python, `math.exp` enveloppe la libm de la plateforme (https://docs.python.org/3/library/math.html), et `sum()` fait une sommation compensée depuis 3.12 (https://docs.python.org/3/whatsnew/3.12.html).
  - Seuls `+ − × ÷`, `sqrt` (arrondi correct en pratique) et les opérations entières sont identiques partout. D'où notre `exp`/`log`/`cos` maison et nos boucles de somme explicites.
- **Le hasard.** Python ne garantit pas `shuffle` ni `gauss` d'une version à l'autre (https://docs.python.org/3/library/random.html). SplitMix32 est recommandé par l'auteur de la page de référence des générateurs JS (https://github.com/bryc/code/blob/master/jshash/PRNGs.md).
- **Calculer dans le navigateur.**
  - WebGPU n'est complet ni dans Firefox ni dans Safari pour Mac (caniuse, lu le 03/11/2026), et il calcule en f32 dans un ordre non déterministe.
  - TensorFlow.js n'a plus de version stable depuis le 21/10/2024 (https://api.deps.dev/v3/systems/npm/packages/%40tensorflow%2Ftfjs).
  - ONNX Runtime Web n'entraîne pas (https://github.com/microsoft/onnxruntime/releases/tag/v1.20.0).
  - Donc TypeScript pur sur `Float64Array`, dans un Web Worker.
- **Pas de `SharedArrayBuffer` :** GitHub Pages n'envoie pas les en-têtes COOP/COEP (https://github.com/orgs/community/discussions/13309).
- **Onglet caché :** les minuteries sont bridées en arrière-plan (https://developer.mozilla.org/en-US/docs/Web/API/Page_Visibility_API). Le sort des Workers dédiés n'est documenté nulle part, d'où une pause explicite sur `visibilitychange`.
- **Taille du mini-modèle.** Le micro-GPT de Karpathy (12/02/2026) a 4 192 paramètres (dim 16, 4 têtes, 1 couche, contexte 16), 32 033 prénoms et 27 jetons. Sa perte passe de 3,37 à environ 2,37 en 1 000 pas (https://karpathy.github.io/2026/02/12/microgpt/).
- **Les prénoms.**
  - Source : Insee, « Fichier des prénoms », édition parue le 16/07/2026, naissances de 1900 à 2025, fichier national `prenoms-2025-nat_csv.zip` (4 Mo, colonnes SEXE, PRENOM, PERIODE, VALEUR ; effectifs arrondis à 5 près) (https://www.insee.fr/fr/statistiques/8595130).
  - Licence : les informations publiques de l'Insee sont sous Licence Ouverte 2.0, avec la mention « Source : Insee » et la date de mise à jour (https://www.insee.fr/fr/information/2008466).
- **Accessibilité de l'animation.**
  - WCAG 2.2 : 2.3.3 (mouvement déclenché par une interaction, désactivable), 2.2.2 (pause), 2.1.1 (clavier), 1.1.1 (alternative textuelle : un vrai tableau des poids), 1.4.11 (contraste des graphiques), 2.5.8 (cibles de 24 px), 4.1.3 (messages de statut). Pages « Understanding » sur https://www.w3.org/WAI/WCAG22/Understanding/.
  - Svelte exporte `prefersReducedMotion` depuis 5.7, et `Tween` depuis 5.8 (https://svelte.dev/docs/svelte/svelte-motion).
- **Pièges pédagogiques de l'attention.**
  - Les poids d'attention ne sont pas une explication (Jain et Wallace, arXiv 1902.10186).
  - 3Blue1Brown signale que ses comportements de têtes sont inventés pour l'exemple, et que sa notation diffère de l'article (https://www.3blue1brown.com/lessons/attention).
  - Une seule convention doit être dite : lignes = requêtes, score = q·k.
- **Formules du calculateur.**
  - 6·N·D opérations pour l'entraînement (Kaplan et al., arXiv 2001.08361 ; le tableau 3 de Chinchilla, arXiv 2203.15556, vaut exactement 6·N·D).
  - 16 octets par paramètre avec AdamW en précision mixte (ZeRO, arXiv 1910.02054).
  - Activations s·b·h·L·(34 + 5·a·s/h), et 34·s·b·h·L sans la matrice s×s (Korthikanti et al., arXiv 2205.05198).
  - Cache KV de 2·2·L·têtes_kv·d_tête octets par jeton en 16 bits, et génération bornée par la bande passante (https://kipp.ly/transformer-inference-arithmetic/).
  - Efficacité (MFU) : PaLM 46,2 % (arXiv 2204.02311), Llama 3 405B de 38 à 43 % (arXiv 2407.21783).
- **Ton IA, mesurée** (`docs/mesures/entrainement-2026-11.md`) : 17 855 jetons/s pour 433,6 M de paramètres sur la RTX 5070 Ti.
  - Cela fait 46,45 TFLOPS utiles (6N), soit 52,8 % des 87,9 TFLOPS bf16 denses de la carte (whitepaper RTX Blackwell, tableau 5).
  - Avec la forme réelle (20 couches, dim 1 280, contexte 2 048) et le terme d'attention de PaLM, on obtient 65,6 %. Le calculateur montre les deux.

## Choix de ce plan

1. **Moteur du mini-modèle :** TypeScript pur sur `Float64Array` dans un Web Worker, sans WebGPU ni bibliothèque. C'est le seul moteur qui marche partout et qui peut égaler le Python au bit près. Il n'y a donc pas de « repli si WebGPU est absent » : ce chemin unique est le repli.
2. **Jumeau Python pur et parité au bit près, y compris pour l'entraînement.** La spécification n'exige qu'une courbe de même allure, mais seulement face à PyTorch. Ici le jumeau fait les mêmes opérations dans le même ordre, donc l'égalité exacte est possible : on l'exige, avec des attendus en motifs hexadécimaux.
3. **Architecture : un mini-transformer d'une couche.**
   - Dimensions : dim 16, 4 têtes de 4, contexte 16, MLP de 64 avec ReLU.
   - RMSNorm sans poids, positions apprises, sortie séparée de l'entrée.
   - Il a 32·V + 3 328 paramètres, soit 4 192 pour V = 27, comme le micro-GPT. C'est la forme la plus petite dont on connaît le résultat, et elle a déjà les pièces de ton IA (attention causale, MLP, normes).
   - La recette d'entraînement est celle de ton IA : AdamW à (0,9 ; 0,95), décroissance des poids de 0,1, écrêtage à 1, montée puis cosinus. Le chapitre 1.5 pourra dire « la même recette, en 4 700 paramètres ».
4. **Données :** les prénoms de l'Insee (Licence Ouverte 2.0).
   - On garde ceux qui ont au moins 500 naissances depuis 1900, de 2 à 15 caractères, en minuscules, accents et trait d'union compris.
   - La progression se voit (« xqzéj » au départ, des prénoms plausibles à la fin), le français s'entend dans les accents, et la licence est propre. Écrire du français lisible caractère par caractère demanderait bien plus que ce budget de calcul.
5. **Ce que le lecteur règle :**
   - lancer, mettre en pause, reprendre, recommencer ;
   - le taux d'apprentissage, parmi 0,001, 0,003, 0,01, 0,03, 0,1 et 0,3 : un changement repart de zéro et garde l'essai précédent en courbe fantôme, pour comparer ;
   - la vitesse : normale (au plus 150 pas par seconde, pour voir la courbe se dessiner) ou rapide.

   La graine reste fixe (1234, comme ton IA) : un même réglage redonne exactement la même courbe.
6. **Ce qui est montré :**
   - la courbe de l'erreur d'entraînement, les points de validation et la ligne du hasard (ln V) ;
   - les erreurs de validation en liste ;
   - huit prénoms inventés tous les 100 pas, marqués « existe déjà » quand le prénom est dans la liste ;
   - le nombre de pas par seconde mesuré.
7. **Avant-goût pour 0.5 :** le même composant, en préréglage `avant-gout` : 600 pas, sans réglage de taux, avec les prénoms du départ et ceux de la fin.
8. **Attention : un exemple écrit à la main, calculé par le moteur.**
   - La phrase est « Le forgeron chauffe le fer puis il le tord ».
   - Chaque mot porte 8 traits. Il y a 2 têtes de 4 : « qui agit » (un verbe cherche son sujet) et « de qui on parle » (un pronom cherche le nom qu'il remplace).
   - Seuls les vecteurs des mots et les matrices sont écrits. Les scores, le masque, les poids et les sorties sont calculés par la même fonction que le mini-modèle, et vérifiés contre le Python.
   - On le dit au lecteur, avec la mise en garde de Jain et Wallace.
   - Le composant accepte un autre exemple : le plan 5 pourra y montrer les vraies cartes de ton IA une fois entraînée, calculées sur le processeur.
   - Ajout de la revue finale : ton IA (RoPE, 1 280 dimensions, têtes de 64) ne s'écrit pas comme un exemple `x` + `wq`/`wk`/`wv`. Ce que le plan 5 devra faire (un mode « carte seule » nourri par forge, ou renoncer à cette promesse) est dans la note « Note pour le plan 5 : les cartes de ton IA » de `projets/mini-modele/README.md` (lignes 199 à 229).
9. **Animation pilotée par le lecteur.** Sept étapes : traits, requête/clé/valeur, scores, division par √4 = 2, masque, softmax, mélange.
   - Le lecteur choisit le mot qui pose la question et la tête.
   - La carte complète s'affiche dans un vrai `<table>`.
   - Tout se fait au clavier. Sous `prefers-reduced-motion`, rien ne glisse : les valeurs se posent.
10. **Calculateur : une phrase à régler, puis un relevé.**
    - Réglages : le modèle (ton IA en 5 tailles, GPT-3, Llama 3 8B, 70B et 405B), les jetons par paramètre, le nombre de cartes, la carte et l'efficacité.
    - Relevé : calcul (6ND), durée, mémoire d'entraînement (16 octets par paramètre, plus les activations sans la matrice s×s), mémoire pour servir le modèle (bf16, int8, int4, plus un cache KV de 4 096 jetons), plafond de génération, électricité au tarif EDF, location.
    - Les prix de location ne viennent que de sources primaires (RunPod, Lambda, Azure). Ils sont affichés en fourchette, avec leur lien et leur date.
11. **Ton IA comme repère de réalité.** Un tableau donne les débits mesurés des 5 tailles, sur la carte et sur le processeur, la durée qu'on en tire et l'efficacité implicite. Quand le réglage est celui de ton IA, le relevé met le calcul et la mesure côte à côte.
12. **Parité du calculateur avec `forge`.**
    - Le calculateur refait trois choses de forge : `largeur_cachee` et `nombre_parametres` (calcul entier) et `estimer` (une division).
    - Le TypeScript les recopie. Un test Vitest lit les formes de `PRESETS` et les constantes dans le code source de forge (sans l'importer, donc sans PyTorch), et vérifie les nombres que forge a lui-même écrits (ses tests, `configs/*.toml`, ses rapports de mesure).
    - On ne modifie pas `projets/forge`.
13. **Paris :** deux par démo sur les pages d'essai, et une fonction de choix exportée pour chacun, que les plans 4 et 5 réutiliseront. Les bonnes réponses sont calculées par le moteur de la démo, et une phrase d'explication qui deviendrait fausse arrête la construction.
14. **Parité vérifiée aussi dans Firefox et WebKit.** En intégration continue, une page d'essai refait tous les attendus dans le navigateur. C'est la seule façon de voir qu'un moteur JavaScript s'écarte.

## Écarts assumés avec la spécification

- **Données versionnées** (choisi par l'utilisateur le 03/11/2026, voir la question plus bas). La spécification dit que les données ne sont jamais versionnées. Pourtant `projets/mini-modele/donnees/prenoms.txt` (environ 100 Ko) entre dans git, comme le fichier du tokenizer au plan 2.
  - Raison : le site statique doit servir ce fichier, et le télécharger à chaque construction rendrait la page dépendante de l'Insee.
  - Le script qui le produit et sa source restent dans le dépôt.
- **Pas de page d'annexe publiée pour le calculateur.** Les annexes doivent d'abord être maquettées et validées (spécification, section 6). Le plan 5, qui écrit déjà l'annuaire et le glossaire, maquettera les annexes et y posera le calculateur. Ici, il vit sur sa page d'essai.

## Question tranchée

**Versionner la liste des prénoms ?** L'utilisateur a choisi la réponse A le 03/11/2026 : `prenoms.txt` entre dans le dépôt. Les autres réponses restent notées pour mémoire.

- **(A, recommandé)** Versionner `prenoms.txt`, environ 100 Ko, avec sa source et sa licence.
- **(B)** Le télécharger dans l'intégration continue à chaque construction.
- **(C)** Prendre une liste déjà dans le dépôt, par exemple les mots du corpus de 1.3. Elle est trop courte pour apprendre quoi que ce soit.

## Contraintes globales

- **Langue et typographie.**
  - Tout texte visible est en français, au tutoiement, sans capitales hors début de phrase et noms propres.
  - Espace fine insécable U+202F devant `; : ! ? %` et à l'intérieur des guillemets « ».
  - Les milliers se séparent par U+202F (`Intl.NumberFormat('fr-FR')`), et les décimales par une virgule.
  - L'apostrophe est courbe (U+2019).
  - Dans Svelte, on écrit `\u202F` comme dans `AtelierTokenizer.svelte` ; dans Astro, on passe par `typographier()`.
- **Couleurs et polices :** les variables de `site/src/styles/jetons.css`, jamais de couleur en dur. Gabarito pour les titres et les chiffres, Newsreader pour le texte, JetBrains Mono pour le code.
- **Le jaune soleil est réservé à ce qui se manipule :** boutons d'action des démos, nombres réglables, sélecteurs, mot choisi.
- **Interdits** (spécification et plan 1) :
  - étiquettes en capitales espacées, méta-informations séparées par des points médians, « → » collé aux boutons ;
  - emojis, encadrés à bordure gauche colorée, dégradés ;
  - cartes arrondies identiques avec ombre douce, animations d'entrée.

  S'y ajoutent, pour ce plan :
  - aucune bibliothèque de graphiques : les courbes et les barres sont du SVG ou du CSS dessiné à la main, aux couleurs du site ;
  - aucune tuile de « tableau de bord » : les nombres vivent dans des phrases ou dans des tableaux typographiés, comme dans la maquette 10.
- **Mouvement :** seulement en réponse à une action du lecteur. Sous `prefers-reduced-motion: reduce`, aucun déplacement : les valeurs se posent directement.
- **Plancher de qualité :**
  - aucun débordement à 390 px ;
  - focus visible, zéro violation axe (wcag2a, wcag2aa), contraste AA ;
  - cibles d'au moins 24 px ;
  - statuts annoncés par `role="status"` sans prendre le focus ;
  - sans JavaScript, le texte et les valeurs de départ restent lisibles.
- **Cohérence des moteurs, au bit près** (spécification, section 7) :
  - **Calculs permis.** Dans les fichiers vérifiés, seuls `+ − × ÷`, `racine` (`math.sqrt`, `Math.sqrt`), `floor` et les opérations entières sont permis.
    - Python : fichiers `calcul.py`, `donnees.py`, `attention.py`, `modele.py`, `entrainement.py`, `exemple_attention.py`.
    - TS : leurs équivalents dans `site/src/lib/mini-modele/`.
  - **Interdits**, même dans les commentaires (un test les cherche) :
    - en Python : `math.exp/log/log1p/log2/log10/expm1/cos/sin/tan/tanh/pow/fsum`, `**`, `sum(`, numpy, `random`, `statistics` ;
    - en TS : `Math.exp/log/log1p/log2/log10/expm1/cos/sin/tan/tanh/pow/hypot/random`, `**` (sauf l'ouverture `/**` d'un commentaire de documentation : motif `(?<!\/)\*\*`), `crypto.getRandomValues`.
  - **Sommes et maximums.** Toute somme est une boucle `s = 0.0`, puis `s += …`, par indices croissants. Tout maximum de flottants est une boucle `if v > m`, jamais `max()` ni `Math.max`, qui traitent −0 différemment.
  - **Le Python d'abord.** On l'écrit en premier ; le TS en est la traduction ligne à ligne, avec les mêmes fonctions, les mêmes boucles et le même ordre.
  - **Les attendus.** Le Python les écrit (`uv run python -m mini_modele.attendus`), chaque flottant sous forme de 16 chiffres hexadécimaux gros-boutistes. Vitest, pytest et la page de parité lisent les mêmes fichiers. Un test vérifie qu'ils sont à jour.
- **Hasard :** seulement `Hasard` (SplitMix32), avec une graine entière comprise entre 0 et 2³² − 1. Jamais `Math.random`, `random` ni `crypto.getRandomValues`.
- **La carte graphique est occupée.** L'entraînement principal de ton IA tourne (environ 135 h), et l'utilisateur joue sur ce PC.
  - Aucune tâche n'utilise le GPU : ni WebGPU, ni WebGL, ni CUDA, ni PyTorch. Chrome est lancé par Playwright avec `--disable-gpu`.
  - Les parcours tournent avec `--workers=4`.
  - Ne pas toucher `projets/forge` ni `D:\forge-ia-donnees`.
- **Navigateur :** un seul Web Worker de module par démo, des messages copiés et non transférés, aucun `SharedArrayBuffer`. Pause sur `visibilitychange`.
- **Ports :** 8530 (Astro, dev et aperçu) et 8531 (Playwright), déjà réglés. Aucun nouveau port.
- **Commits :**
  - sur `main`, jamais de push ;
  - message en français, terminé par `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` ;
  - toujours `git add <fichiers de la tâche>`, puis `git commit -m "…" -- <les mêmes fichiers>`. Un autre agent peut avoir des fichiers non commités dans `projets/forge` : ne jamais les ajouter.
- **Reprise :** chaque tâche est autonome et se termine par un commit. Si l'utilisateur dit « stop », on reprend à la dernière étape cochée.
- **Fins de ligne LF partout** (`.gitattributes` existe). Le Python écrit ses fichiers avec `newline="\n"`.
- **Noms et commentaires en français.** Les messages d'erreur disent quoi faire.
- **Sources :** chaque chiffre de matériel, de prix ou de modèle a son URL et sa date de relevé. Seules les sources primaires entrent dans un calcul de prix.
- **Commandes PowerShell.** Python : `cd projets/mini-modele; uv run pytest -q`. Site : `cd site; npx vitest run …` et `npx playwright test … --workers=4`.

## Points à surveiller à la relecture

Les tests ordinaires ne couvrent pas ces cinq situations, les plus susceptibles de gêner un lecteur. Chacune reçoit son test dans la tâche indiquée.

1. **Onglet caché, portable en veille ou téléphone verrouillé pendant l'entraînement.** Attendu :
   - l'entraînement se met en pause et le dit (« En pause : l'onglet était caché. Reprends quand tu veux. ») ;
   - le pas ne bouge plus ;
   - à la reprise, il n'y a pas de rafale de rattrapage.

   Tests en tâche 6 (boucle et réducteur) et en tâche 7 (parcours).
2. **Recommencer, changer le taux en plein entraînement, cliquer deux fois.** Attendu :
   - une seule boucle tourne ;
   - les messages de l'ancien essai sont ignorés ;
   - un même réglage redonne exactement la même courbe.

   Tests en tâches 6 et 7.
3. **Taux trop grand.** Si l'erreur devient infinie, non numérique ou absurde (plus de 3·ln V) :
   - l'entraînement s'arrête et dit « L'erreur a explosé : ce taux est trop grand. Recommence avec un taux plus petit. » ;
   - la courbe reste lisible, avec un repère « hors échelle » et aucun `NaN` dans le chemin SVG.

   Tests en tâches 4, 6 et 7.
4. **Valeurs extrêmes du calculateur** (405 milliards de paramètres sur une seule carte de 16 Go, 16 384 cartes, 1 jeton par paramètre). Attendu :
   - les durées passent en ans, les coûts en millions d'euros ;
   - la mémoire dit « il faut au moins N cartes » ;
   - on ne voit jamais `NaN`, `Infinity` ni `e+`, et rien ne déborde à 390 px.

   Tests en tâches 10 et 11.
5. **Clavier seul et mouvement réduit dans l'animation.** Attendu :
   - les étapes, le mot et la tête se choisissent au clavier, avec un focus visible ;
   - sous `prefers-reduced-motion: reduce`, les barres prennent leur valeur finale tout de suite.

   Tests en tâche 8.

---

## Fichiers

```
projets/mini-modele/                  jumeau Python pur des démos (nouveau projet uv, testé en CI)
  pyproject.toml, uv.lock, README.md
  donnees/prenoms.txt                 liste versionnée (tâche 2)
  donnees/exemple-attention.json      vecteurs et matrices de l'exemple (tâche 5)
  mini_modele/calcul.py               exp, log, cos, sommes, Hasard, hex, empreintes
  mini_modele/prenoms.py              préparation de la liste depuis l'Insee
  mini_modele/donnees.py              vocabulaire, encodage, partage entraînement/validation
  mini_modele/attention.py            scores, softmax, mélange (partagés modèle + animation)
  mini_modele/modele.py               mini-transformer : avant, arrière, génération
  mini_modele/entrainement.py         taux, écrêtage, AdamW, Entraineur
  mini_modele/exemple_attention.py    détail de l'exemple pour l'animation
  mini_modele/attendus.py             écrit tests/attendus-*.json
  mini_modele/__main__.py             « python -m mini_modele entrainer »
  tests/…                             tests et attendus partagés avec le site
site/src/lib/nombres.ts               formats français partagés par les démos
site/src/lib/courbe.ts                géométrie de la courbe de perte
site/src/lib/mini-modele/             jumeau TS (mêmes modules) + pilotage, aperçu, paris, parité
site/src/lib/calculateur/             formules, données sourcées, jumeau de forge, formats, paris
site/src/components/demos/            MiniModele, DemoMiniModele, CourbePerte, AnimationAttention, Calculateur, ControleParite
site/src/essais/                      mini-modele.mdx, attention.mdx, calculateur.mdx, parite.mdx
site/e2e/                             mini-modele, attention, calculateur, parite (.spec.ts) ; outils.ts complété
```

---

### Tâche 1 : projet jumeau et noyau de calcul exact

**Fichiers :**

- Créer : `projets/mini-modele/pyproject.toml`, `uv.lock`, `README.md`, `mini_modele/__init__.py`, `mini_modele/calcul.py`, `mini_modele/attendus.py`
- Test : `projets/mini-modele/tests/test_calcul.py`, `tests/test_sources.py`, `tests/test_attendus.py`, `tests/attendus-calcul.json`
- Créer : `site/src/lib/mini-modele/calcul.ts`
- Test : `site/src/lib/mini-modele/calcul.test.ts`, `site/src/lib/mini-modele/sources.test.ts`

**Interfaces (produites ; Python en snake_case, TS en camelCase, mêmes noms par ailleurs) :**

- Constantes, avec leurs motifs exacts :
  - `LN2_HAUT = 0.6931471803691238` (`3fe62e42fee00000`) ;
  - `LN2_BAS = 1.9082149292705877e-10` (`3dea39ef35793c76`) ;
  - `INV_LN2 = 1.4426950408889634` (`3ff71547652b82fe`) ;
  - `SQRT_DEMI = 0.7071067811865476` (`3fe6a09e667f3bcd`) ;
  - `PI = 3.141592653589793` (`400921fb54442d18`).
- `exp(x) -> float` et `log(x) -> float`, définies pour tout flottant.
- `cos(x) -> float`, définie de 0 à `PI` seulement. Hors de là : `ValueError` en Python, `RangeError` en TS, avec le message « cos n'est définie ici que de 0 à π (reçu …). ».
- `racine(x)`, qui vaut `math.sqrt` ou `Math.sqrt`.
- `somme(valeurs)`, `produit_scalaire(a, b)` (longueurs différentes : erreur) et `maximum(valeurs)`.
- `vers_hex(x) -> str` (16 chiffres minuscules, gros-boutiste) et `depuis_hex(h) -> float`.
- `empreinte(valeurs) -> str` : FNV-1a 32 bits sur les octets gros-boutistes de chaque float64, en 8 chiffres hexadécimaux. `empreinte_texte(texte) -> str` fait la même chose sur l'UTF-8.
- `class Hasard(graine: int)` : `suivant32() -> int`, `uniforme() -> float` (dans [0, 1[), `entier(n) -> int`, `gaussienne(ecart_type) -> float` et `melanger(liste) -> None`.
- `attendus.py` :
  - `calculer_attendus_calcul() -> dict` ;
  - `ecrire_attendus() -> None`, lancée par `python -m mini_modele.attendus`. Elle écrit chaque `tests/attendus-<nom>.json` avec `json.dumps(…, ensure_ascii=False, indent=1) + "\n"`. Les tâches suivantes y ajoutent leur `calculer_attendus_<nom>()`.
- `pyproject.toml` :
  - nom `mini-modele`, `requires-python = ">=3.12"`, `dependencies = []`, groupe de développement `pytest` ;
  - construction hatchling, paquet `mini_modele`, `testpaths = ["tests"]`.

**Algorithmes imposés.** Voici la référence Python ; le TS en est la traduction exacte.

```python
C_EXP = [1.0]
for n in range(1, 14):
    C_EXP.append(C_EXP[-1] / n)
C_LOG = [1.0 / (2 * n + 1) for n in range(12)]
C_COS = [1.0]
for n in range(1, 13):
    C_COS.append(-C_COS[-1] / ((2 * n - 1) * (2 * n)))

def deux_puissance(k):            # 2^k exact, -1074 <= k <= 1023
    return math.ldexp(1.0, k)     # TS : table Float64Array construite par ×2 et ÷2 depuis 1,0

def exp(x):
    if x != x: return x
    if x > 709.782712893384: return math.inf
    if x < -745.1332191019411: return 0.0
    k = math.floor(x * INV_LN2 + 0.5)
    r = (x - k * LN2_HAUT) - k * LN2_BAS
    p = C_EXP[13]
    for n in range(12, -1, -1):
        p = p * r + C_EXP[n]
    if k > 1023: return (p * 2.0) * deux_puissance(k - 1)
    if k < -1022: return (p * deux_puissance(k + 64)) * deux_puissance(-64)
    return p * deux_puissance(k)

def log(x):
    if x != x or x < 0.0: return math.nan
    if x == 0.0: return -math.inf
    if x == math.inf: return x
    m, e = math.frexp(x)          # TS : décomposition exacte par DataView (sous-normaux : ×2^64 d'abord)
    if m < SQRT_DEMI:
        m = m * 2.0
        e = e - 1
    f = m - 1.0
    s = f / (2.0 + f)
    z = s * s
    q = C_LOG[11]
    for n in range(10, -1, -1):
        q = q * z + C_LOG[n]
    return e * LN2_HAUT + (2.0 * s * q + e * LN2_BAS)

def cos(x):                       # de 0 à PI seulement
    if x > PI * 0.5: return -_cos_noyau(PI - x)
    return _cos_noyau(x)

def _cos_noyau(t):
    z = t * t
    p = C_COS[12]
    for n in range(11, -1, -1):
        p = p * z + C_COS[n]
    return p

class Hasard:                     # SplitMix32 ; TS : Math.imul et >>> 0
    def __init__(self, graine): self.etat = graine & 0xFFFFFFFF
    def suivant32(self):
        self.etat = (self.etat + 0x9E3779B9) & 0xFFFFFFFF
        z = self.etat
        z = ((z ^ (z >> 16)) * 0x21F0AAAD) & 0xFFFFFFFF
        z = ((z ^ (z >> 15)) * 0x735A2D97) & 0xFFFFFFFF
        return z ^ (z >> 15)
    def uniforme(self): return self.suivant32() / 4294967296.0
    def entier(self, n): return math.floor(self.uniforme() * n)
    def gaussienne(self, ecart_type):          # somme de 12 uniformes, moins 6
        s = 0.0
        for _ in range(12):
            s += self.uniforme()
        return (s - 6.0) * ecart_type
    def melanger(self, liste):                 # Fisher-Yates, de la fin vers le début
        for i in range(len(liste) - 1, 0, -1):
            j = self.entier(i + 1)
            liste[i], liste[j] = liste[j], liste[i]
```

Les fonctions `exp`, `log`, `cos` et `racine` portent les marqueurs de région `# region: exp` / `# fin: exp` et `# region: log` / `# fin: log`, que le chapitre 1.5 pourra extraire.

**Contenu de `attendus-calcul.json` :**

- `constantes` : les cinq motifs ci-dessus.
- `exp` : des paires `[x, exp(x)]` en hexadécimal, pour :
  - les entrées fixes `-745.2, -745.0, -708.5, -50.0, -10.0, -1.0, -0.5, -1e-10, -0.0, 0.0, 1e-300, 1e-10, 0.25, 0.5, 1.0, 2.0, 10.0, 50.0, 700.0, 709.7, 709.79, 710.0` ;
  - 200 valeurs `(h.uniforme() - 0.5) * 60` tirées de `Hasard(42)`.
- `log` : les entrées fixes `5e-324, 1e-310, 1e-300, 1e-10, 0.1, 0.5, SQRT_DEMI, 0.75, 1.0, 1.0000001, 1.5, 2.0, 10.0, 1e10, 1e300, 1.7976931348623157e308`, puis 200 valeurs `h.uniforme() * 100 + 0.001` tirées de `Hasard(43)`.
- `cos` : les entrées fixes `0.0, 1e-8, 0.5, 1.0, PI * 0.25, PI * 0.5, 2.0, 3.0, PI`, puis 100 valeurs `h.uniforme() * PI` tirées de `Hasard(44)`.
- `hasard`, pour la graine 1234 :
  - `suivant32`, `uniforme`, `gaussienne` (écart-type 1) et `entier_10` : 20 valeurs chacun, tirées d'un `Hasard(1234)` neuf pour chaque liste ;
  - `melange_20` : `list(range(20))` mélangée.
- `empreinte` : 10 valeurs et leur empreinte. `empreinte_texte` : le texte `"Élodie, Zoé et Maël"` et son empreinte.

- [ ] **Étape 1 : créer le projet et écrire les tests qui échouent.**

```python
# tests/test_calcul.py
def test_valeurs_exactes():
    assert exp(0.0) == 1.0 and log(1.0) == 0.0 and cos(0.0) == 1.0 and cos(PI) == -1.0
    assert exp(-746.0) == 0.0 and exp(710.0) == math.inf and log(0.0) == -math.inf
    assert math.isnan(log(-1.0)) and math.isnan(exp(math.nan))
    with pytest.raises(ValueError, match="de 0 à π"):
        cos(4.0)

def test_proche_de_la_libm():          # précision, pas parité : la libm n'est qu'un témoin
    h = Hasard(7)
    for _ in range(10_000):
        x = (h.uniforme() - 0.5) * 1400
        assert abs(exp(x) - math.exp(x)) <= 1e-15 * math.exp(x) + 1e-320
        y = h.uniforme() * 1e6 + 1e-9
        assert abs(log(y) - math.log(y)) <= 1e-15 * max(1.0, abs(math.log(y)))
        t = h.uniforme() * PI
        assert abs(cos(t) - math.cos(t)) <= 1e-15

def test_hasard():
    h = Hasard(1234)
    tirages = [h.uniforme() for _ in range(10_000)]
    assert all(0.0 <= u < 1.0 for u in tirages)
    g = Hasard(5); gs = [g.gaussienne(1.0) for _ in range(10_000)]
    moyenne = somme(gs) / len(gs)
    assert abs(moyenne) < 0.05 and abs(somme([v * v for v in gs]) / len(gs) - 1.0) < 0.05
    liste = list(range(20)); Hasard(1).melanger(liste)
    assert sorted(liste) == list(range(20)) and liste != list(range(20))

def test_sommes_et_hex():
    assert somme([0.1, 0.2, 0.3]) == (0.1 + 0.2) + 0.3
    assert depuis_hex(vers_hex(-0.0)) == 0.0 and vers_hex(-0.0) == "8000000000000000"
    assert vers_hex(PI) == "400921fb54442d18"
```

```python
# tests/test_sources.py : les fonctions non reproductibles n'entrent pas dans le chemin vérifié
INTERDITS = re.compile(r"math\.(exp|log|log1p|log2|log10|expm1|cos|sin|tan|tanh|pow|fsum)\b|\*\*|\bsum\(|numpy|\brandom\b|statistics")
VERIFIES = ["calcul", "donnees", "attention", "modele", "entrainement", "exemple_attention"]
def test_aucune_fonction_non_reproductible():
    for nom in VERIFIES:
        chemin = PAQUET / f"{nom}.py"
        if chemin.exists():
            assert not INTERDITS.search(chemin.read_text(encoding="utf-8")), nom
```

`test_attendus.py` vérifie `calculer_attendus_calcul() == json.loads(…attendus-calcul.json…)`, puis chaque `calculer_attendus_<nom>` ajouté ensuite.

```ts
// calcul.test.ts
import attendus from '../../../../projets/mini-modele/tests/attendus-calcul.json';
for (const nom of ['exp', 'log', 'cos'] as const)
  for (const [x, y] of attendus[nom]) expect(versHex(fonctions[nom](depuisHex(x)))).toBe(y);
const h = new Hasard(attendus.hasard.graine);
expect(Array.from({ length: 20 }, () => h.suivant32())).toEqual(attendus.hasard.suivant32);
// … uniforme, gaussienne, entier_10, melange_20, constantes, empreinte, empreinte_texte
expect(exp(0)).toBe(1); expect(cos(PI)).toBe(-1); expect(() => cos(4)).toThrow('de 0 à π');
```

`sources.test.ts` applique au TS le motif interdit des contraintes globales, sur `calcul.ts`, `donnees.ts`, `attention.ts`, `modele.ts`, `entrainement.ts` et `exemple-attention.ts`, quand ils existent.

- [ ] **Étape 2 : vérifier l'échec.** Commandes : `cd projets/mini-modele; uv lock; uv run pytest -q`, puis `cd site; npx vitest run src/lib/mini-modele`. Attendu : échec à l'import.
- [ ] **Étape 3 : écrire `calcul.py`.** Puis générer les attendus (`uv run python -m mini_modele.attendus`), et écrire `calcul.ts` en face, ligne à ligne.
  - `README.md` : ce qu'est le projet (le jumeau exact des démos du site), comment lancer les tests, et pourquoi on n'utilise ni `math.exp` ni `sum`.
- [ ] **Étape 4 : vérifier que tout passe.** Mêmes commandes. Attendu : tout passe, et Vitest trouve exactement les mêmes motifs que le Python.
- [ ] **Étape 5 : commit**, message « Jumeau des démos : noyau de calcul exact en Python et en TypeScript ».

### Tâche 2 : les prénoms

**Fichiers :**

- Créer : `projets/mini-modele/mini_modele/prenoms.py`, `mini_modele/donnees.py`, `donnees/prenoms.txt`
- Test : `tests/test_prenoms.py`, `tests/test_donnees.py`, `tests/attendus-donnees.json`
- Modifier : `mini_modele/attendus.py`, `README.md` (section « Les données »)
- Créer : `site/src/lib/mini-modele/donnees.ts`
- Test : `site/src/lib/mini-modele/donnees.test.ts`

**Interfaces :**

- Consomme : `Hasard`, `empreinte_texte` (tâche 1) ; `comparerPointsDeCode` (`site/src/lib/bpe.ts`).
- `prenoms.py` :
  - Constantes :
    - `URL = "https://www.insee.fr/fr/statistiques/fichier/8595130/prenoms-2025-nat_csv.zip"` ;
    - `SEUIL_NAISSANCES = 500`, `LONGUEUR_MIN = 2`, `LONGUEUR_MAX = 15` ;
    - `CARACTERES_PERMIS = "-abcdefghijklmnopqrstuvwxyzàâäæçèéêëîïôöùûüÿœ"`.
  - `extraire(lignes: Iterable[dict[str, str]], seuil: int = SEUIL_NAISSANCES) -> list[str]` :
    - normalise en NFC et en minuscules ;
    - ignore les prénoms qui commencent par `_` ;
    - ne compte que les `PERIODE` qui sont une année à 4 chiffres ;
    - additionne `VALEUR` sur les années et les deux sexes ;
    - garde un total d'au moins `seuil`, une longueur de 2 à 15, uniquement des caractères permis, sans `-` au début, à la fin ni doublé ;
    - trie par point de code.
  - `main()` :
    - télécharge le zip dans un dossier temporaire (urllib, délai de 60 s) ;
    - lit le CSV en vérifiant l'en-tête : séparateur et noms exacts des colonnes. S'ils diffèrent de SEXE, PRENOM, PERIODE et VALEUR, s'adapter et le noter dans le README ;
    - applique `extraire`. S'il reste moins de 5 000 prénoms, recommence avec un seuil de 200 et le dit ;
    - écrit `donnees/prenoms.txt` (un prénom par ligne, `\n` final) ;
    - affiche le nombre de prénoms, les caractères utilisés et l'empreinte du fichier.
- `donnees.py` (et `donnees.ts`, avec les mêmes noms en camelCase) :
  - `BORD = "."` (numéro 0), `GRAINE_PARTAGE = 20261103` ;
  - `charger_prenoms(chemin=None) -> list[str]`. Le TS lit `prenoms.txt?raw`, par le chemin `../../../../projets/mini-modele/donnees/prenoms.txt?raw` ;
  - `vocabulaire_de(prenoms) -> str` : `BORD`, puis les caractères distincts triés par point de code ;
  - `encoder(prenom, vocabulaire) -> tuple[int, ...]` : `(0, *numéros, 0)`. Un caractère inconnu lève « Caractère inconnu du vocabulaire : … » ;
  - `decoder(ids, vocabulaire) -> str` ignore les 0 ;
  - `@dataclass(frozen=True) class Donnees` :
    - champs `vocabulaire: str`, `entrainement: tuple[tuple[int, ...], ...]`, `validation: …`, `connus: frozenset[str]` ;
    - en TS : `interface Donnees { vocabulaire: string; entrainement: number[][]; validation: number[][]; connus: Set<string> }` ;
  - `preparer(prenoms) -> Donnees` :
    - copie la liste et la mélange avec `Hasard(GRAINE_PARTAGE)` ;
    - les `len // 10` premiers vont en validation, le reste en entraînement ;
  - `donnees_par_defaut() -> Donnees`, mise en cache.
- `attendus-donnees.json` :
  - `nb_prenoms`, `empreinte_fichier`, `vocabulaire`, `nb_entrainement`, `nb_validation` ;
  - `entrainement_10` et `validation_10` : les 10 premiers prénoms décodés ;
  - `empreinte_entrainement` et `empreinte_validation` : `empreinte_texte` des prénoms joints par `\n`, dans l'ordre.

- [ ] **Étape 1 : écrire les tests qui échouent.**

```python
def test_extraire_cumule_filtre_et_trie():
    l = lambda s, p, a, v: {"SEXE": s, "PRENOM": p, "PERIODE": a, "VALEUR": v}
    lignes = [l("1", "ÉLODIE", "1990", "300"), l("2", "ÉLODIE", "1991", "250"),
              l("1", "_PRENOMS_RARES", "1990", "9000"), l("1", "JEAN-PIERRE", "1950", "800"),
              l("1", "BJØRN", "1990", "900"), l("1", "MAXIMILIENNE-ROSE", "1990", "900"),
              l("1", "LÉA", "XXXX", "5000"), l("2", "ZOÉ", "2020", "495")]
    assert extraire(lignes) == ["jean-pierre", "élodie"]

def test_fichier_des_prenoms():
    texte = (RACINE / "donnees" / "prenoms.txt").read_text(encoding="utf-8")
    assert "\r" not in texte and texte.endswith("\n")
    prenoms = charger_prenoms()
    assert 3_000 <= len(prenoms) <= 30_000 and prenoms == sorted(set(prenoms))
    assert all(2 <= len(p) <= 15 and set(p) <= set(CARACTERES_PERMIS) for p in prenoms)

def test_partage_et_encodage():
    d = donnees_par_defaut()
    assert len(d.validation) == len(charger_prenoms()) // 10
    assert d.vocabulaire[0] == "." and list(d.vocabulaire[1:]) == sorted(set(d.vocabulaire[1:]))
    assert decoder(encoder("élodie", d.vocabulaire), d.vocabulaire) == "élodie"
    assert all(len(s) - 1 <= 16 for s in d.entrainement + d.validation)
    with pytest.raises(ValueError, match="Caractère inconnu"):
        encoder("ø", d.vocabulaire)
```

`donnees.test.ts` compare tous les champs de `attendus-donnees.json` avec `donneesParDefaut()`. Il vérifie aussi que `prenoms.txt?raw` ne contient pas `\r`.

- [ ] **Étape 2 : vérifier l'échec** (pytest et Vitest).
- [ ] **Étape 3 : écrire `prenoms.py`, puis lancer `uv run python -m mini_modele.prenoms`** (un téléchargement de 4 Mo). Ensuite :
  - écrire `donnees.py`, régénérer les attendus, écrire `donnees.ts` ;
  - section du README : source, édition, licence, mention « Source : Insee », seuil retenu, nombre de prénoms, caractères, empreinte, commande pour refaire la liste.
- [ ] **Étape 4 : vérifier que tout passe.**
- [ ] **Étape 5 : commit**, message « Prénoms de l'Insee pour le mini-modèle, partagés à l'identique en Python et en TypeScript ».

### Tâche 3 : le mini-transformer (attention, passe avant, passe arrière)

**Fichiers :**

- Créer : `projets/mini-modele/mini_modele/attention.py`, `mini_modele/modele.py`
- Test : `tests/test_attention.py`, `tests/test_modele.py`, `tests/attendus-modele.json` (clé `modele`)
- Modifier : `mini_modele/attendus.py`
- Créer : `site/src/lib/mini-modele/attention.ts`, `modele.ts`
- Test : `site/src/lib/mini-modele/attention.test.ts`, `modele.test.ts`

**Interfaces :**

- Consomme : tâches 1 et 2.
- `attention.py`. Régions : `scores`, `softmax`, `melange`.
  - `scores_attention(requete, cles, echelle) -> list[float]` : `produit_scalaire(requete, cle) * echelle` pour chaque clé, dans l'ordre. L'appelant ne passe que les clés visibles : le masque causal, c'est de ne pas passer les suivantes.
  - `softmax(scores) -> list[float]` : `m = maximum(scores)`, `e_j = exp(s_j - m)`, `total = somme(e)`, `e_j / total`.
  - `poids_attention(requete, cles, echelle) = softmax(scores_attention(…))`.
  - `melanger_valeurs(poids, valeurs) -> list[float]` : pour chaque composante `d`, `s = 0.0`, puis `s += poids[j] * valeurs[j][d]` par `j` croissant.
- `modele.py`. Régions : `avant`, `perte`.
  - `@dataclass(frozen=True) class ConfigMini` : `taille_vocabulaire: int`, `dim: int = 16`, `tetes: int = 4`, `contexte: int = 16`, `largeur_mlp: int = 64`. Si `dim % tetes != 0`, une erreur dit quoi changer.
  - En TS : `interface ConfigMini { tailleVocabulaire; dim; tetes; contexte; largeurMlp }` et `configMini(tailleVocabulaire: number): ConfigMini`.
  - `ECART_TYPE_INIT = 0.08`, `EPSILON_NORME = 1e-5`.
  - `disposition(c) -> dict[str, tuple[int, int, int]]` : nom → (début, lignes, colonnes), dans un seul tableau à plat, ligne par ligne.
    - Ordre : `plongement` (V×dim), `positions` (contexte×dim), `requetes`, `cles`, `valeurs`, `sortie_attention` (dim×dim chacune), `mlp_haut` (dim×largeur), `mlp_bas` (largeur×dim), `tete_de_lecture` (dim×V).
    - Le produit `x·W` vaut `y[j] = Σ_i x[i]·W[i][j]`, sommé par `i` croissant.
  - `nombre_parametres(c) -> int` : V·d + T·d + 4d² + 2·d·m + d·V, soit 32·V + 3 328 avec les valeurs par défaut.
  - `initialiser(c, hasard) -> list[float]` : `hasard.gaussienne(ECART_TYPE_INIT)` pour chaque paramètre, dans l'ordre. En TS, `initialiser` renvoie un `Float64Array`.
  - `perte_et_gradient(c, params, sequences, gradient=None) -> float`.
    - La perte est la moyenne de l'entropie croisée sur toutes les positions prédites de toutes les séquences.
    - Une séquence vaut `(0, …, 0)` : on lit `seq[:-1]` et on prédit `seq[1:]`.
    - Si `gradient` est fourni (même longueur que `params`), il est remis à 0,0, puis rempli séquence par séquence.
    - En TS : `perteEtGradient(c, params: Float64Array, sequences: number[][], gradient: Float64Array | null): number`.
  - `perte(c, params, sequences) -> float`.
  - `logits_suivants(c, params, ids) -> list[float]` : les scores de la dernière position.
  - `generer(c, params, hasard, nb) -> list[tuple[int, ...]]` : `nb` prénoms, sans les bords.
    - On part de `(0,)` et on refait la passe avant à chaque caractère.
    - Tirage : `e = exp(l - maximum(l))`, `seuil = hasard.uniforme() * somme(e)`. On cumule par indice croissant et on prend le premier indice où `seuil < cumul` (le dernier sinon).
    - Le tirage d'un 0 arrête le prénom, comme 15 caractères écrits.

**Passe avant imposée** (par séquence et par position `t`, dans cet ordre) :

1. `h0 = plongement[jeton] + positions[t]`.
2. `a = norme(h0)`, puis `q, k, v = a·requetes, a·cles, a·valeurs`.
3. Pour chaque tête `h` (composantes `4h` à `4h+3`) : `poids = poids_attention(q_h(t), [k_h(j) pour j ≤ t], 1.0 / racine(4))`, puis `o_h(t) = melanger_valeurs(poids, [v_h(j) pour j ≤ t])`.
4. `h1 = h0 + concat(o)·sortie_attention`.
5. `b = norme(h1)`, `u = b·mlp_haut`, `r = relu(u)`, `h2 = h1 + r·mlp_bas`.
6. `f = norme(h2)`, `logits = f·tete_de_lecture`.
7. `perte_t = log(somme(exp(logits - m))) - (logits[cible] - m)`, avec `m = maximum(logits)`.

Définitions :

- `norme(x)` : `inv = 1.0 / racine(somme(x_i * x_i) / dim + EPSILON_NORME)`, puis `y_i = x_i * inv`.
- `relu(u)` : `u if u > 0.0 else 0.0`.
- Perte totale : `somme(pertes dans l'ordre) / nombre`.
- Gradient des logits : `(softmax - unité de la cible) / nombre`.

La passe arrière s'écrit à la main, dans l'ordre inverse exact. Le TS la recopie ligne à ligne.

**Contenu de la clé `modele` des attendus :**

- `config`, `graine` (1234), `nb_parametres` ;
- après `initialiser(c, Hasard(1234))` : `init_empreinte` et `init_premiers` (8 motifs) ;
- `lot` : les 8 premières séquences d'entraînement ;
- `perte_lot`, `gradient_empreinte` et `gradient_premiers` (8 motifs) ;
- `perte_validation_256` : la perte sur les 256 premiers prénoms de validation ;
- `generes` : 8 prénoms générés avec `Hasard(1236)`.

- [ ] **Étape 1 : écrire les tests qui échouent.**

```python
def test_nombre_de_parametres():
    assert nombre_parametres(ConfigMini(taille_vocabulaire=27)) == 4192

def test_softmax_et_masque():
    assert poids_attention([0.0, 0.0], [[1.0, 2.0], [3.0, 4.0]], 0.5) == [0.5, 0.5]
    p = poids_attention([1.0, -2.0], [[0.3, 0.1], [2.0, -1.0], [-0.5, 0.5]], 0.5)
    assert abs(somme(p) - 1.0) <= 1e-15

def test_gradient_par_differences_finies():
    c = ConfigMini(taille_vocabulaire=5, dim=4, tetes=2, contexte=4, largeur_mlp=8)
    h = Hasard(3); params = [h.gaussienne(0.5) for _ in range(nombre_parametres(c))]
    seqs = [(0, 1, 2, 0), (0, 3, 0)]
    g = [0.0] * len(params); perte_et_gradient(c, params, seqs, g)
    for i in range(len(params)):
        plus = params.copy(); plus[i] += 1e-6
        moins = params.copy(); moins[i] -= 1e-6
        numerique = (perte(c, plus, seqs) - perte(c, moins, seqs)) / 2e-6
        assert abs(g[i] - numerique) <= 1e-5, i

def test_perte_de_depart_au_niveau_du_hasard():
    d = donnees_par_defaut(); c = ConfigMini(taille_vocabulaire=len(d.vocabulaire))
    p = initialiser(c, Hasard(1234))
    assert abs(perte(c, p, d.validation[:256]) - log(float(len(d.vocabulaire)))) < 0.15
```

`modele.test.ts` et `attention.test.ts` comparent tous les champs de la clé `modele` des attendus. Ils redisent aussi 4 192 paramètres pour V = 27, et l'égalité des poids pour des scores égaux.

- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire `attention.py` et `modele.py`,** régénérer les attendus, puis écrire `attention.ts` et `modele.ts` en face.
- [ ] **Étape 4 : vérifier que tout passe** (pytest en moins d'une minute, Vitest).
- [ ] **Étape 5 : commit**, message « Mini-transformer jumeau : attention, passe avant et passe arrière ».

### Tâche 4 : l'entraînement et la génération

**Fichiers :**

- Créer : `projets/mini-modele/mini_modele/entrainement.py`, `mini_modele/__main__.py`
- Test : `tests/test_entrainement.py`, `tests/test_cli.py`, clé `entrainement` dans `tests/attendus-modele.json`
- Modifier : `mini_modele/attendus.py`, `README.md` (commande `entrainer`)
- Créer : `site/src/lib/mini-modele/reglages.ts`, `site/src/lib/mini-modele/entrainement.ts`
- Test : `site/src/lib/mini-modele/entrainement.test.ts`, `entrainement-long.test.ts`

**Interfaces :**

- Consomme : tâches 1 à 3.
- `TAUX_PROPOSES = (0.001, 0.003, 0.01, 0.03, 0.1, 0.3)`.
- `@dataclass(frozen=True) class ReglagesMini`. En TS, une `interface` avec les mêmes champs en camelCase.
  - Champs obligatoires : `pas_total: int`, `echauffement: int`.
  - Champs par défaut : `taux_max: float = 0.01`, `lot: int = 8`, `ratio_min: float = 0.1`, `beta1: float = 0.9`, `beta2: float = 0.95`, `epsilon: float = 1e-8`, `poids_decroissance: float = 0.1`, `ecretage: float = 1.0`, `graine: int = 1234`, `validation_tous: int = 100`, `nb_validation: int = 256`, `nb_echantillons: int = 8`.
- `PRESETS_MINI = {"complet": ReglagesMini(pas_total=3000, echauffement=100), "avant-gout": ReglagesMini(pas_total=600, echauffement=50)}`.
- En TS, `TAUX_PROPOSES`, `ReglagesMini` et `PRESETS_MINI` vivent dans `reglages.ts`, qui n'importe rien, et `entrainement.ts` les réexporte. Ainsi la page peut lire les taux sans embarquer le moteur ni les prénoms : seul le Worker les charge.
- `taux(pas, pas_total, taux_max, echauffement, ratio_min=0.1) -> float` : même code que `forge/entrainement/planning.py` (montée linéaire, puis cosinus jusqu'à `ratio_min × taux_max`), avec le `cos` et le `PI` de `calcul`, et le même ordre des opérations.
- `class Entraineur(reglages, donnees=None)` :
  - attributs : `config`, `donnees`, `params`, `pas` (0 au départ ; le premier pas porte le numéro 1), `diverge` ;
  - `faire_un_pas() -> float`, `perte_validation() -> float` (sur les `nb_validation` premiers prénoms de validation), `echantillons() -> list[str]`, `taux_courant() -> float`.
  - Les hasards sont séparés :
    - poids : `Hasard(graine)`, tiré dans `__init__` ;
    - ordre des données : `Hasard(graine + 1)`. Au départ, puis chaque fois que `position + lot > n`, on mélange `list(range(n))` et on repart de 0 ;
    - échantillons au pas `p` : un `Hasard(graine + 2 + p)` neuf.
  - `diverge` passe à vrai si la perte du lot n'est pas finie ou dépasse `3.0 * log(float(V))`. Une fois vrai, `faire_un_pas` ne fait plus rien et renvoie la dernière perte.
  - Régions : `lot`, `ecretage`, `adamw`.

**Pas d'optimisation imposé** (après `perte_et_gradient` sur le lot) :

```python
# region: ecretage
carres = 0.0
for g in gradient:
    carres += g * g
norme = racine(carres)
if norme > r.ecretage:
    facteur = r.ecretage / norme
    for i in range(n):
        gradient[i] = gradient[i] * facteur
# region: adamw   (t = taux(self.pas, …) ; self._b1t et self._b2t partent de 1.0)
self._b1t = self._b1t * r.beta1
self._b2t = self._b2t * r.beta2
for i in range(n):
    g = gradient[i]
    self._m[i] = r.beta1 * self._m[i] + (1.0 - r.beta1) * g
    self._v[i] = r.beta2 * self._v[i] + (1.0 - r.beta2) * (g * g)
    m_chapeau = self._m[i] / (1.0 - self._b1t)
    v_chapeau = self._v[i] / (1.0 - self._b2t)
    p = self.params[i] * (1.0 - t * r.poids_decroissance)
    self.params[i] = p - t * m_chapeau / (racine(v_chapeau) + r.epsilon)
```

- `__main__.py` : `python -m mini_modele entrainer [--preset complet|avant-gout] [--pas N] [--taux X]`.
  - Il affiche `pas 50 : erreur 2,734` tous les 50 pas, avec une virgule décimale.
  - À la fin, il affiche l'erreur de validation et 8 prénoms.
- **Clé `entrainement` des attendus** (préréglage `complet`, 20 pas) :
  - `pertes` et `taux` : 20 motifs chacun ;
  - `validation_0`, `validation_20`, `params_empreinte_20` ;
  - `echantillons_0` et `echantillons_20`.

- [ ] **Étape 1 : écrire les tests qui échouent.**

```python
def test_taux_comme_forge():
    assert taux(50, 1000, 1e-3, 100) == pytest.approx(5e-4)
    assert taux(100, 1000, 1e-3, 100) == pytest.approx(1e-3)
    assert taux(550, 1000, 1e-3, 100) == pytest.approx(5.5e-4)
    assert taux(1000, 1000, 1e-3, 100) == pytest.approx(1e-4)

def test_vingt_pas():
    e = Entraineur(PRESETS_MINI["complet"])
    pertes = [e.faire_un_pas() for _ in range(20)]
    assert e.pas == 20 and not e.diverge
    assert somme(pertes[-5:]) / 5 < somme(pertes[:5]) / 5
    assert all(set(p) <= set(e.donnees.vocabulaire[1:]) and len(p) <= 15 for p in e.echantillons())

def test_cli(capsys):
    main(["entrainer", "--pas", "2"])
    assert "pas 2" in capsys.readouterr().out
```

```ts
// entrainement.test.ts : parité sur 20 pas, vitesse, divergence
const e = new Entraineur(PRESETS_MINI.complet);
expect(versHex(e.perteValidation())).toBe(attendus.entrainement.validation_0);
const pertes = Array.from({ length: 20 }, () => versHex(e.faireUnPas()));
expect(pertes).toEqual(attendus.entrainement.pertes);
// … taux, validation_20, params_empreinte_20, echantillons_0 et _20
const t0 = performance.now(); const v = new Entraineur(PRESETS_MINI.complet);
for (let i = 0; i < 100; i++) v.faireUnPas();
expect(performance.now() - t0).toBeLessThan(3000);
const fou = new Entraineur({ ...PRESETS_MINI.complet, tauxMax: 1000 });
for (let i = 0; i < 50 && !fou.diverge; i++) fou.faireUnPas();
expect(fou.diverge).toBe(true);
```

```ts
// entrainement-long.test.ts (délai de 180 s) : l'entraînement complet apprend vraiment
const e = new Entraineur(PRESETS_MINI.complet); const depart = e.perteValidation();
while (e.pas < 3000) e.faireUnPas();
const fin = e.perteValidation();
console.log(`perte de validation : ${depart} au départ, ${fin} au pas 3 000`);
expect(e.diverge).toBe(false); expect(fin).toBeLessThanOrEqual(2.45); expect(depart - fin).toBeGreaterThanOrEqual(1.0);
```

- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire `entrainement.py` et `__main__.py`,** régénérer les attendus, puis écrire `entrainement.ts`.
  - **Si le test long échoue sur le seuil de 2,45 :** essayer `taux_max` à 0,03, puis à 0,003 (dans `TAUX_PROPOSES`), puis `pas_total` à 4 000. Garder le plus petit réglage qui passe, et le noter dans le message de commit et dans le README.
- [ ] **Étape 4 : vérifier que tout passe,** et noter la perte finale affichée par le test long.
- [ ] **Étape 5 : commit**, message « Entraînement jumeau du mini-modèle : AdamW, écrêtage, cosinus, prénoms générés ».

### Tâche 5 : l'exemple d'attention

**Fichiers :**

- Créer : `projets/mini-modele/donnees/exemple-attention.json`, `mini_modele/exemple_attention.py`
- Test : `tests/test_exemple_attention.py`, `tests/attendus-attention.json`
- Modifier : `mini_modele/attendus.py`
- Créer : `site/src/lib/choix.ts`, `site/src/lib/mini-modele/exemple-attention.ts`, `paris-attention.ts`
- Test : `site/src/lib/mini-modele/exemple-attention.test.ts`, `paris-attention.test.ts`

**Interfaces :**

- Consomme : `scores_attention`, `softmax`, `melanger_valeurs` (tâche 3), `racine` (tâche 1).
- **Format de `exemple-attention.json`.** Il ne contient aucun score ni aucun poids : seulement les vecteurs et les matrices.

```json
{"phrase": "Le forgeron chauffe le fer puis il le tord",
 "jetons": ["Le", "forgeron", "chauffe", "le", "fer", "puis", "il", "le", "tord"],
 "traits": ["déterminant", "nom", "verbe", "pronom", "sujet", "objet", "personne", "chose"],
 "x": [[1,0,0,0,0,0,0,0], …],
 "tetes": [{"nom": "qui agit", "description": "…", "wq": [[…4 nombres…] × 8], "wk": …, "wv": …},
           {"nom": "de qui on parle", …}]}
```

- **Les vecteurs `x` :** des 0 et des 1, selon les traits.
  - « Le » : déterminant.
  - « forgeron » : nom, sujet, personne.
  - « chauffe » : verbe.
  - « le », 4e mot : déterminant.
  - « fer » : nom, objet, chose.
  - « puis » : aucun trait.
  - « il » : pronom, sujet, personne.
  - « le », 8e mot : pronom, objet, chose.
  - « tord » : verbe.
- **Les matrices** (8×4) ont des entiers de −5 à 5. L'exécutant les construit pour satisfaire les critères ci-dessous. La « description » de chaque tête dit en une phrase ce qu'elle cherche.
- `exemple_attention.py` (et le TS, avec les mêmes noms) :
  - `charger_exemple(chemin=None) -> dict` ;
  - `detailler_tete(x, wq, wk, wv) -> DetailTete` : `requetes`, `cles` et `valeurs` (n×4) ; `scores` et `scores_echelles` (n×n, `None` pour j > i) ; `poids` (n×n, 0,0 pour j > i) ; `sorties` (n×4). L'échelle vaut `1.0 / racine(4)` = 0,5, et les poids sont exactement ceux de `softmax(scores_attention(…))` ;
  - `detailler_exemple(exemple) -> list[DetailTete]`.
- `paris-attention.ts` :
  - `motLePlusRegarde(tete: number, requete: number): number` ;
  - `choixRegardDeIl(): Choix[]`, pour la tête 1, « de qui on parle », et la requête « il » (indice 6) :
    - la bonne réponse est le mot de plus grand poids ;
    - les leurres sont le mot juste avant « il » (« puis ») et le mot visible de deuxième plus grand poids (ou du troisième, s'il y a collision) ;
    - les choix sont rangés dans l'ordre de la phrase ;
    - garde-fou : si le mot de plus grand poids n'est pas « forgeron », une erreur est levée (« Exemple devenu faux : … ») ;
  - `choixMasque(): Choix[]` : textes `0`, `environ la moitié`, `presque tout`. « 0 » est juste si et seulement si le poids de « forgeron » (1) vers « il » (6) vaut exactement 0 ; sinon, erreur.
  - `Choix` vient de `site/src/lib/choix.ts`, créé ici : `export interface Choix { texte: string; juste?: boolean }`, la forme des choix de `Pari.astro`. Les paris des tâches 6 et 10 l'importent aussi.
- **Attendus `attendus-attention.json` :** pour chaque tête, toutes les matrices du détail, en motifs (`null` pour les cases masquées).

- [ ] **Étape 1 : écrire les tests qui échouent.** Ces critères sont la définition de l'exemple :

```python
def test_criteres_de_l_exemple():
    ex = charger_exemple(); agit, reprise = detailler_exemple(ex)
    assert agit.poids[2][1] >= 0.7                          # « chauffe » regarde « forgeron »
    assert agit.poids[8][1] + agit.poids[8][6] >= 0.7       # « tord » regarde ses sujets
    assert reprise.poids[6][1] >= 0.6                       # « il » regarde « forgeron »
    assert reprise.poids[7][4] >= 0.6                       # le second « le » regarde « fer »
    for d in (agit, reprise):
        for i in range(9):
            assert all(d.poids[i][j] == 0.0 for j in range(i + 1, 9))
            assert abs(somme(d.poids[i][: i + 1]) - 1.0) <= 1e-15
    assert all(v in (0, 1) for ligne in ex["x"] for v in ligne)
    assert all(-5 <= v <= 5 and v == int(v) for t in ex["tetes"] for m in ("wq", "wk", "wv") for l in t[m] for v in l)
```

`exemple-attention.test.ts` compare tout le détail aux attendus. `paris-attention.test.ts` vérifie que :

- `choixRegardDeIl()` a trois choix, dont un seul juste, `forgeron` ;
- `choixMasque()` met la bonne réponse sur `0`.

- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire le JSON, `exemple_attention.py`, puis le TS.**
- [ ] **Étape 4 : vérifier que tout passe.**
- [ ] **Étape 5 : commit**, message « Exemple d'attention écrit à la main, calculé par le moteur jumeau ».

### Tâche 6 : le pilotage de l'entraînement, l'aperçu et les paris

**Fichiers :**

- Créer : `site/src/lib/nombres.ts`, `site/src/lib/mini-modele/boucle-travailleur.ts`, `travailleur.ts`, `pilote.ts`, `apercu.ts`, `paris.ts`
- Test : `site/src/lib/nombres.test.ts`, `site/src/lib/mini-modele/boucle-travailleur.test.ts`, `pilote.test.ts`, `paris.test.ts`

**Interfaces :**

- Consomme : `Entraineur`, `PRESETS_MINI`, `TAUX_PROPOSES` (tâche 4) ; `donneesParDefaut` (tâche 2) ; `log` (tâche 1).
- `nombres.ts` :
  - `nombre(x: number, decimales = 0): string` : `Intl.NumberFormat('fr-FR')`, avec exactement `decimales` décimales ;
  - `pourcent(fraction: number, decimales = 0): string`, qui donne par exemple `52,8\u202F%`.
- `apercu.ts` :
  - `interface EtatInitialMini { preset: 'complet' | 'avant-gout'; pasTotal: number; tailleVocabulaire: number; nbParametres: number; nbEntrainement: number; perteHasard: number; perteValidation: number; echantillons: { texte: string; existe: boolean }[] }` ;
  - `etatInitial(preset): EtatInitialMini`, calculé une fois par préréglage (au pas 0, avec `perteHasard = log(V)`). Il est sérialisable, pour passer d'Astro à l'îlot.
- **Messages du Worker** (`boucle-travailleur.ts`) :

```ts
type Vitesse = 'normale' | 'rapide';
interface ReglagesLancement { preset: 'complet' | 'avant-gout'; tauxMax: number; vitesse: Vitesse }
type MessageVersTravailleur =
  | { type: 'lancer'; generation: number; reglages: ReglagesLancement }   // nouvelle génération : repart de zéro ; même génération : reprend
  | { type: 'pause'; generation: number }
  | { type: 'vitesse'; generation: number; vitesse: Vitesse };
type Prenom = { texte: string; existe: boolean };
type MessageDuTravailleur =
  | { type: 'progres'; generation: number; pas: number; pasTotal: number; pertes: number[]; dureeMs: number;
      pasParSeconde: number; validation?: { pas: number; perte: number }; echantillons?: { pas: number; prenoms: Prenom[] } }
  | { type: 'etat'; generation: number; etat: 'en-pause' | 'termine' | 'diverge' }
  | { type: 'erreur'; generation: number; message: string };
```

- `class BoucleTravailleur(envoyer, horloge: () => number, creerEntraineur = (r: ReglagesMini) => new Entraineur(r))` :
  - `recevoir(m: MessageVersTravailleur): void` et `tranche(): boolean`. `tranche` renvoie vrai s'il faut une autre tranche.
  - Constantes : `PAS_PAR_SECONDE_NORMAL = 150`, `DUREE_TRANCHE_MS = 50`, `INTERVALLE_MESSAGES_MS = 100`.
  - **Rythme.** Une tranche enchaîne des pas entiers, jusqu'à 50 ms. En vitesse normale, elle s'arrête aussi dès que `pasFaits ≥ 150 × (maintenant − debutFenetre) / 1000`.
  - **Pas de rattrapage.** La fenêtre repart à zéro à chaque lancement, reprise ou changement de vitesse.
  - **Validation.** Aux multiples de `validation_tous` et au dernier pas, on calcule la validation et les échantillons (`existe` = `donnees.connus.has(texte)`), et on envoie tout de suite.
  - **Fin d'une tranche.** Un message `progres` part si 100 ms ont passé depuis le précédent. `pertes` contient les pertes des pas faits depuis.
  - **Divergence ou dernier pas.** On envoie `progres`, puis `etat` (`diverge` ou `termine`), et on s'arrête.
  - **Erreur du moteur.** On envoie `erreur`.
  - **Réglages.** Un `lancer` d'une nouvelle génération crée l'entraîneur avec `{ ...PRESETS_MINI[preset], tauxMax }`.
  - **Messages périmés.** Un message `pause` ou `vitesse` d'une autre génération est ignoré.
- `travailleur.ts` :
  - relie `self.onmessage` à `boucle.recevoir` ;
  - enchaîne les tranches par `setTimeout(…, 0)`, une seule planifiée à la fois ;
  - avec `horloge = () => performance.now()`.
- `pilote.ts` :

```ts
type Phase = 'pret' | 'en-cours' | 'en-pause' | 'termine' | 'diverge' | 'erreur';
interface Courbe { pertes: number[]; validations: { pas: number; perte: number }[] }
interface EtatDemo extends Courbe {
  generation: number; phase: Phase; raisonPause: 'lecteur' | 'onglet' | null; tauxIndex: number; vitesse: Vitesse;
  pas: number; pasTotal: number; echantillons: { pas: number; prenoms: Prenom[] }[]; fantome: (Courbe & { tauxIndex: number }) | null;
  pasParSeconde: number; dureeMs: number; message: string | null }
type Evenement = { type: 'lancer' } | { type: 'pause'; raison: 'lecteur' | 'onglet' } | { type: 'recommencer' }
  | { type: 'changer-taux'; tauxIndex: number } | { type: 'vitesse'; vitesse: Vitesse } | { type: 'message'; message: MessageDuTravailleur };
function etatDeDepart(initial: EtatInitialMini, tauxIndex: number): EtatDemo;
function reduire(etat: EtatDemo, ev: Evenement, preset: 'complet' | 'avant-gout'): { etat: EtatDemo; envoi: MessageVersTravailleur | null };
```

**Règles de `reduire`** (textes exacts) :

- **`lancer`.** Depuis `pret` ou `en-pause` : passe à `en-cours` et envoie `lancer`. Ignoré ailleurs ; après `termine`, il faut recommencer.
- **`pause`.** Depuis `en-cours` : passe à `en-pause` et envoie `pause`. Ignoré ailleurs.
  - Raison `onglet` : message « En pause : l'onglet était caché. Reprends quand tu veux. »
- **`recommencer`.**
  - Envoie `pause` à l'ancienne génération, puis incrémente `generation`.
  - Si `pas > 0`, la courbe en cours devient le `fantome`.
  - Retour à `etatDeDepart` (pas 0, validation et prénoms du pas 0 tirés de `initial`).
- **`changer-taux`.** Comme `recommencer`, avec le nouveau taux, et le message « Nouveau taux : l'entraînement repart de zéro. »
- **`vitesse`.** Envoie `vitesse` seulement en cours.
- **`message` d'une autre génération :** ignoré entièrement.
- **`progres` :** ajoute les pertes, la validation et les prénoms.
- **`etat` :**
  - `termine` donne « Terminé : 3 000 pas en 21 s. », avec les nombres réels : `nombre(pasTotal)` et `nombre(Math.round(dureeMs / 1000))` ;
  - `diverge` donne « L'erreur a explosé : ce taux est trop grand. Recommence avec un taux plus petit. »
- **`erreur` :** « La démo s'est arrêtée : … ».

**`paris.ts` :**

- `formaterPerte(x): string`, avec 3 décimales (`3,742`).
- `choixErreurDeDepart(): Choix[]` : `0`, la perte de validation du pas 0 formatée (la bonne) et `String(V)`, rangés par ordre croissant.
  - Garde-fou : |perte − ln V| < 0,15.
- `resultatTauxTropGrand(): { normal: number; grand: number; verdict: 'plus-vite' | 'pareil' | 'moins-bien' }`.
  - On fait 200 pas du préréglage `complet`, au taux 0,01 puis au taux 0,3.
  - On compare la validation au pas 200 avec un seuil de 0,05.
  - Le résultat est calculé une fois et gardé.
- `choixTauxTropGrand(): Choix[]` : « Il apprend plus vite », « À peu près pareil », « Il apprend moins bien, ou plus du tout ». Le choix juste suit `verdict`.

- [ ] **Étape 1 : écrire les tests qui échouent,** avec un faux entraîneur et une fausse horloge.

```ts
// boucle-travailleur.test.ts
it('vitesse normale : au plus 150 pas par seconde, sans rattrapage après une pause', () => {
  const { boucle, envois, horloge } = monter();          // faux entraîneur : 1 pas = 0 ms
  boucle.recevoir({ type: 'lancer', generation: 1, reglages: { preset: 'complet', tauxMax: 0.01, vitesse: 'normale' } });
  for (let t = 0; t <= 1000; t += 10) { horloge.t = t; boucle.tranche(); }
  expect(pasFaits()).toBeLessThanOrEqual(151);
  boucle.recevoir({ type: 'pause', generation: 1 }); horloge.t = 11_000; boucle.tranche();
  const avant = pasFaits();
  boucle.recevoir({ type: 'lancer', generation: 1, reglages: … }); horloge.t = 11_100; boucle.tranche();
  expect(pasFaits() - avant).toBeLessThanOrEqual(16);
});
it('validation et prénoms aux multiples de 100, puis « termine »', …);
it('divergence : progres, puis etat diverge, puis plus rien', …);
it('une erreur du moteur devient un message erreur', …);
it('une pause d\u2019une autre génération est ignorée', …);
// pilote.test.ts
it('un message d\u2019une ancienne génération ne change rien', …);
it('recommencer garde la courbe en fantôme et repart du pas 0', …);
it('changer le taux repart de zéro, en pause, avec son message', …);
it('pause « onglet » : phase en-pause et message exact', …);
it('lancer après « termine » est ignoré', …);
// paris.test.ts
const depart = etatInitial('complet');
expect(choixErreurDeDepart().map((c) => c.texte)).toEqual(['0', formaterPerte(depart.perteValidation), String(depart.tailleVocabulaire)]);
expect(choixErreurDeDepart().filter((c) => c.juste)).toHaveLength(1);
const r = resultatTauxTropGrand();
expect(choixTauxTropGrand().find((c) => c.juste)?.texte).toBe({ 'plus-vite': 'Il apprend plus vite', pareil: 'À peu près pareil',
  'moins-bien': 'Il apprend moins bien, ou plus du tout' }[r.verdict]);
// nombres.test.ts
expect(nombre(12345.678, 1)).toBe('12\u202F345,7'); expect(pourcent(0.528, 1)).toBe('52,8\u202F%');
```

- [ ] **Étape 2 : vérifier l'échec.** Commande : `npx vitest run src/lib/nombres.test.ts src/lib/mini-modele`.
- [ ] **Étape 3 : écrire les six modules.**
- [ ] **Étape 4 : vérifier que tout passe.**
- [ ] **Étape 5 : commit**, message « Pilotage du mini-modèle : boucle du Worker, réducteur, aperçu et paris ».

### Tâche 7 : le composant MiniModele, sa courbe et sa page d'essai

**Fichiers :**

- Créer : `site/src/lib/courbe.ts`, test `site/src/lib/courbe.test.ts`
- Créer : `site/src/components/demos/CourbePerte.svelte`, `MiniModele.svelte`, `DemoMiniModele.astro`
- Modifier : `site/src/components/interactif/NombreManipulable.svelte` (prop `texte`)
- Créer : `site/src/essais/mini-modele.mdx`, test `site/e2e/mini-modele.spec.ts`
- Modifier : `site/e2e/outils.ts`, pour ajouter `attendreHydratation(page)` et `verifierTypographie(zone: Locator)`. `attendreHydratation` est reprise de `site/e2e/atelier.spec.ts`, qu'on modifie pour l'importer.
- Modifier : `site/playwright.config.ts`, pour ajouter `launchOptions: { args: ['--disable-gpu'] }` aux projets `ordinateur` et `mobile`

**Interfaces :**

- Consomme : la tâche 6 entière, `canal`/`ouverture` (plan 1), et `chapitresParus`/`hrefChapitre` (plan 1). Ces deux-là ne servent que dans `DemoMiniModele.astro`, car un îlot Svelte ne peut pas lire la collection.
- `NombreManipulable` : prop facultative `texte?: (v: number) => string`.
  - Quand elle est donnée, elle fixe le texte affiché et `aria-valuetext`.
  - La largeur réservée est celle du plus long `texte(v)` de `min` à `max`, si `max − min ≤ 200`.
  - Sans elle, rien ne change : les parcours de l'atelier de 1.3 doivent toujours passer.
- `courbe.ts` :
  - `interface Echelle { largeur: number; hauteur: number; xMax: number; yMin: number; yMax: number }` ;
  - `echelleCourbe(pasTotal, perteHasard, largeur = 640, hauteur = 280): Echelle`, avec `yMin = 0` et `yMax = 1,25 × perteHasard` ;
  - `reduirePoints(pertes: number[], maxPoints = 600): { pas: number; perte: number }[]` : moyennes par paquets égaux. Les valeurs non finies sont ignorées ; un paquet entièrement non fini donne `NaN` ;
  - `cheminCourbe(points, e): { d: string; horsEchelle: boolean }` : un point non fini coupe le tracé (le suivant recommence par `M`), et une perte au-dessus de `yMax` est ramenée à `yMax` avec `horsEchelle = true`. Coordonnées à une décimale.
- `CourbePerte.svelte` :
  - props `{ pertes: number[]; validations: {pas, perte}[]; pasTotal: number; perteHasard: number; fantome: Courbe | null; etiquette: string }` ;
  - SVG `viewBox="0 0 640 280"`, à 100 % de largeur, `role="img"`, `aria-label` = « Courbe de l'erreur : 3,742 au pas 0, 2,316 au pas 3 000. » (valeurs réelles) ;
  - `data-test="courbe"` ; `data-test="courbe-fantome"` sur le tracé fantôme ; repère « hors échelle » quand c'est le cas.
- `DemoMiniModele.astro` :
  - props `{ preset?: 'complet' | 'avant-gout'; nom?: string; verrou?: string; acquis?: string }` (défauts `'complet'` et `'mini'`) ;
  - il rend `<MiniModele client:load … initial={etatInitial(preset)} lien15={…} />` ;
  - `lien15` vaut `hrefChapitre('1.5')` si `chapitresParus()` contient 1.5, sinon `null`.
- `MiniModele.svelte` : props `{ preset; nom; verrou?; acquis?; initial: EtatInitialMini; lien15: string | null }`.
  - **Rien de lourd dans la page.** `MiniModele.svelte` et `pilote.ts` n'importent que des types d'`apercu.ts` et de `boucle-travailleur.ts` (`import type`), et les valeurs de `reglages.ts`, `nombres.ts` et `courbe.ts`. Le moteur et `prenoms.txt` n'entrent que dans le paquet du Worker.
  - Un parcours le vérifie (« la page ne charge pas les prénoms avant le lancement »). Il note le corps de chaque script `.js` reçu par la page d'essai jusqu'au pari compris, sans cliquer sur « Lancer ». Aucun ne doit contenir la ligne de `prenoms.txt` du milieu de la liste, lue dans le test.
  - La racine est `<div class="mini-modele" data-mini={nom}>` : les parcours visent une instance par `data-mini`, car la page d'essai en a deux.
  - Le Worker est créé au premier « Lancer », par `await import('../../lib/mini-modele/travailleur.ts?worker')`. Si Vite le refuse, régler `vite.worker.format = 'es'` dans `astro.config.mjs`.
  - Il écoute `document.visibilitychange` : caché pendant l'entraînement, c'est `reduire(…, { type: 'pause', raison: 'onglet' })`.
  - Il émet `forge:acquis` avec `{ cle: acquis }` la première fois que la phase devient `termine`, une seule fois par chargement.

**Contenu et textes exacts de `MiniModele`, de haut en bas :**

- **Préréglage `complet`.** La phrase « Entraîne-le sur {nbEntrainement} prénoms pendant {pasTotal} pas, avec un taux d'apprentissage de [taux]. ».
  - [taux] est un `NombreManipulable` sur les indices de `TAUX_PROPOSES` : canal `${nom}:taux`, `texte` = `nombre(taux, décimales utiles)`, `testId="taux"`, `verrou`.
  - **Préréglage `avant-gout`** : « Il va s'entraîner pendant 600 pas. », sans réglage.
- **Les boutons :**
  - l'action principale, `data-test="mini-action"` : « Lancer l'entraînement », « Pause », « Reprendre », ou « Terminé » (désactivé) ;
  - « Recommencer », `data-test="mini-recommencer"` ;
  - une bascule de vitesse, `data-test="mini-vitesse"` : « Aller plus vite » ou « Revenir au rythme normal ». Elle n'existe pas dans l'avant-goût, qui va toujours vite.
- **La ligne d'état** (`role="status"`, `data-test="mini-etat"`, `data-pas={pas}`) :
  - « Pas 1 200 sur 3 000 : erreur 2,412, 148 pas par seconde. » ;
  - ou le message du réducteur s'il y en a un.

  Elle est annoncée au plus à chaque validation, pause ou fin, pas à chaque image.
- **La courbe.**
- **La liste des erreurs de validation** (`data-test="mini-validations"`, un `li` par point : « au pas 100 : 2,812 »).
- **Les prénoms inventés** au dernier point (`data-test="mini-echantillons"`, 8 `li`) : la capitale est mise après le début et après chaque trait d'union, et un prénom connu est suivi de « (existe déjà) » en encre douce. Un prénom vide (le modèle a tiré la fin tout de suite) s'affiche « (aucune lettre) ». Les points précédents sont dans un `<details>` « Les prénoms des étapes d'avant ».
- **Le crédit :** « Prénoms : Insee, Fichier des prénoms 1900–2025, Licence Ouverte 2.0 », avec le lien.
- **L'avant-goût** finit par « Tu le fabriqueras au chapitre 1.5. », avec un lien seulement si `lien15` n'est pas `null`.
- **Sans JavaScript** (`@media (scripting: none)`) : les boutons sont cachés et le paragraphe « Cette démo calcule dans ton navigateur : elle a besoin de JavaScript. » s'affiche. Les valeurs et les prénoms du pas 0 restent visibles, rendus par Astro.

**Allure :**

- les boutons reprennent les choix des paris (bord indigo, ombre décalée, soleil au survol) ; la bascule reprend `.bascule` de la maquette 10 ;
- la courbe d'entraînement est indigo en 2 px, les points de validation indigo avec un rayon de 3 ;
- le fantôme et la ligne du hasard sont en lavande pointillée, avec l'étiquette « hasard » ;
- les axes « pas » et « erreur » sont en Gabarito 13 px, encre douce ;
- pas de fond de carte autour de la démo.

**`mini-modele.mdx`.** Frontmatter d'un chapitre `1.5`, avec les acquis `depart`, `taux` et `entraine`.

1. Étape 1, « Avant de lancer » : le pari `depart` (« Avant tout entraînement, quelle erreur le modèle fera-t-il sur des prénoms qu'il n'a jamais vus ? », `choix={choixErreurDeDepart()}`, `acquis="depart"`, `ouvre="mini"`).
2. Étape 2, « L'entraînement » : `<Verrou nom="mini">` autour de `<DemoMiniModele verrou="mini" acquis="entraine" />`, puis le pari `taux` (« Avec un taux trente fois plus grand (0,3), que se passe-t-il pendant les 200 premiers pas ? », `choix={choixTauxTropGrand()}`, `acquis="taux"`).
3. Étape 3, « L'avant-goût du chapitre 0.5 » : `<DemoMiniModele preset="avant-gout" nom="avant-gout" />`.

Les explications des paris citent les nombres calculés (`resultatTauxTropGrand()`).

- [ ] **Étape 1 : écrire les tests qui échouent.**

```ts
// courbe.test.ts
const e = echelleCourbe(3000, 3.7);
expect(cheminCourbe([{ pas: 0, perte: 1 }, { pas: 1, perte: NaN }, { pas: 2, perte: 1 }], e).d.match(/M/g)).toHaveLength(2);
expect(cheminCourbe([{ pas: 0, perte: 99 }], e)).toMatchObject({ horsEchelle: true });
expect(cheminCourbe([{ pas: 0, perte: Infinity }], e).d).not.toMatch(/NaN|Infinity/);
expect(reduirePoints(Array(3000).fill(2), 600)).toHaveLength(600);
```

```ts
// e2e/mini-modele.spec.ts (ordinateur et mobile)
const PAGE = '/forge-ia/essais/mini-modele/';
const etat = (p: Page) => p.locator('[data-mini="mini"] [data-test="mini-etat"]');   // l'avant-goût se vise par [data-mini="avant-gout"]
const pas = async (p: Page) => Number(await etat(p).getAttribute('data-pas'));
async function ouvrir(p: Page) { await p.goto(PAGE); await attendreHydratation(p); await p.locator('[data-pari="depart"] [data-juste]').click(); }
test('avant le pari, le taux est désactivé ; après, ça apprend', async ({ page }) => {
  await page.goto(PAGE); await attendreHydratation(page);
  await expect(page.locator('[data-test="taux"]')).toHaveAttribute('aria-disabled', 'true');
  await ouvrir(page); await page.locator('[data-test="mini-action"]').first().click();
  await expect.poll(() => pas(page)).toBeGreaterThan(0);
});
test('pause et reprise au même pas', …);           // vitesse rapide ; ≥ 200 ; Pause ; 1 s plus tard, même pas ; Reprendre ; ça repart
test('onglet caché : pause automatique', async ({ page }) => {
  // … lancer, puis :
  await page.evaluate(() => { Object.defineProperty(document, 'hidden', { value: true, configurable: true });
    Object.defineProperty(document, 'visibilityState', { value: 'hidden', configurable: true });
    document.dispatchEvent(new Event('visibilitychange')); });
  await expect(etat(page)).toContainText('En pause\u202F: l\u2019onglet était caché.');
  const n = await pas(page); await page.waitForTimeout(1000); expect(await pas(page)).toBe(n);
});
test('recommencer : courbe fantôme, et le même réglage redonne les mêmes erreurs', …); // compare les 3 premiers li de mini-validations avant et après
test('changer le taux repart de zéro', …);   // flèche droite sur [data-test="taux"] → aria-valuetext « 0,03 », data-pas 0, message exact
test('entraînement complet : erreur finale ≤ 2,45 et acquis gagné', …);   // rapide, délai de 120 s, recap [data-acquis="entraine"] data-gagne oui
test('avant-goût : 600 pas, sans réglage de taux', …);
test('sans JavaScript : message et valeurs du départ', …);   // contexte javaScriptEnabled: false
test('accessibilité, largeur, typographie', async ({ page }) => {
  await ouvrir(page); /* … quelques pas, puis : */
  await verifierAxe(page); await verifierSansDebordement(page); await verifierTypographie(page.locator('.mini-modele').first());
});
```

`verifierTypographie(zone)` échoue si `innerText` contient une espace (U+0020 ou U+00A0) devant `; : ! ? % »`, une espace après `«`, ou un nombre de milliers séparé par une espace ordinaire (`/\d \d{3}\b/`).

- [ ] **Étape 2 : vérifier l'échec.** Commandes : `npx vitest run src/lib/courbe.test.ts`, puis `npx playwright test e2e/mini-modele.spec.ts --workers=4`.
- [ ] **Étape 3 : écrire `courbe.ts`, les composants, le changement de `NombreManipulable`, la page d'essai et les aides de test.** On peut s'aider du skill `dataviz` pour les marques et les axes, mais avec la palette du site.
- [ ] **Étape 4 : vérifier que tout passe,** y compris `e2e/atelier.spec.ts` et `e2e/gabarit.spec.ts`.
- [ ] **Étape 5 : captures et relecture.** Prendre des captures ordinateur et mobile de la page d'essai :
  - au départ ;
  - en cours ;
  - à la fin, avec le fantôme.

  Les relire avec l'outil de lecture d'images face à la maquette 10, et corriger tout ce qui fait « tableau de bord » ou « fait par IA ».
- [ ] **Étape 6 : commit**, message « Démo du mini-modèle qui apprend dans le navigateur, et son avant-goût ».

### Tâche 8 : l'animation de l'attention

**Fichiers :**

- Créer : `site/src/components/demos/AnimationAttention.svelte`, `site/src/essais/attention.mdx`
- Test : `site/e2e/attention.spec.ts`

**Interfaces :**

- Consomme : `exempleAttention`, `detaillerExemple` (tâche 5), `choixRegardDeIl`, `choixMasque` (tâche 5), `nombre` et `pourcent` (tâche 6).
- Props : `{ exemple?: ExempleAttention; verrou?: string; acquis?: string; requeteInitiale?: number /* 6, « il » */; teteInitiale?: number /* 1 */ }`. L'exemple vaut celui de la tâche 5 par défaut.
- Émet `forge:acquis` avec `{ cle: acquis }` la première fois que la septième étape est atteinte.

**Contenu et textes exacts :**

- **Les sept étapes**, dans l'ordre :
  1. « Les mots et leurs traits » ;
  2. « Requête, clé, valeur » ;
  3. « Les scores : requête · clé » ;
  4. « Divisés par √4 = 2 » ;
  5. « Le masque : pas de regard vers la suite » ;
  6. « Softmax : des poids qui font 1 » ;
  7. « Le mélange des valeurs ».
- **Le compteur** « Étape 3 sur 7 » et les boutons « Étape précédente » / « Étape suivante » (désactivés aux bouts), `data-test="att-precedente"` et `att-suivante`.
- **Le choix du mot** : un groupe de boutons à bascule, intitulé « Le mot qui pose la question », avec `aria-pressed` et `data-test="att-mot"` sur chacun. Le mot choisi est en soleil.
- **Le choix de la tête** : deux boutons à bascule, « Tête 1 : qui agit » et « Tête 2 : de qui on parle » (`data-test="att-tete"`).
- **La vue principale**, pour le mot choisi : une ligne par mot de la phrase, avec le mot, une barre (`data-test="att-barre"`, `data-mot={i}`, `data-cible={pourcentage final de la largeur}`) et le nombre.
  - Étape 1 : un tableau des traits de tous les mots.
  - Étape 2 : q, k et v du mot choisi, et k de chaque mot.
  - Étapes 3 et 4 : les barres partent d'un axe central (scores négatifs à gauche).
  - Étape 5 : les mots suivants affichent « masqué », sans barre.
  - Étape 6 : les poids de 0 à 1, en pourcentage.
  - Étape 7 : la sortie (4 nombres) et la phrase calculée « Sa nouvelle valeur vient surtout de « forgeron » (74 %). ».
- **Aux étapes 6 et 7, la carte complète de la tête :** un `<table>` de 9 × 9 (lignes : le mot qui demande, colonnes : le mot regardé), `data-test="att-carte"`.
  - Chaque case affiche son pourcentage ; son fond indigo a une opacité proportionnelle au poids, et le texte passe en papier au-delà de 0,5.
  - Les cases masquées montrent « — », avec « masqué » pour les lecteurs d'écran.
  - Le tableau est dans un conteneur `role="region"`, `aria-label="Carte complète de la tête, défilable"`, `tabindex="0"`, `overflow-x: auto`.
- **La ligne d'état** `role="status"` : « Étape 6 sur 7 : softmax. « il » donne 74 % de son attention à « forgeron ». » (valeurs calculées).
- **La légende** (`figcaption`) : « Ces vecteurs sont écrits à la main, comme si les couches précédentes avaient déjà reconnu le rôle de chaque mot. Dans un vrai modèle, ils sont appris, et les têtes sont rarement aussi nettes. La carte montre où le calcul lit, pas pourquoi le modèle répond. Une ligne par mot qui demande, une colonne par mot regardé ; score = requête · clé. »
- **Mouvement.**
  - Les largeurs des barres glissent en 300 ms (`Tween` de `svelte/motion`), seulement après une action du lecteur.
  - Si `prefersReducedMotion.current` est vrai, la durée est de 0. La racine porte alors `data-mouvement="reduit"` (sinon `"normal"`).
- **Sans JavaScript :** l'étape 1 et la carte complète de la tête 2 sont rendues par Astro, et les commandes sont cachées.

**`attention.mdx`.** Frontmatter d'un chapitre `1.4`, avec les acquis `regard`, `masque` et `attention`.

- Le pari `regard` (« Dans la tête « de qui on parle », vers quel mot « il » regarde-t-il le plus ? », `choix={choixRegardDeIl()}`, `ouvre="attention"`).
- `<Verrou nom="attention">` autour de `<AnimationAttention client:load verrou="attention" acquis="attention" />`.
- Le pari `masque` (« Combien vaut le poids de « forgeron » vers « il » ? », `choix={choixMasque()}`).

- [ ] **Étape 1 : écrire les tests qui échouent** (ordinateur et mobile).

```ts
test('au clavier seul, jusqu\u2019à la dernière étape', async ({ page }) => {
  await ouvrir(page);   // pari « regard » joué
  const suivante = page.locator('[data-test="att-suivante"]');
  await suivante.focus(); for (let i = 0; i < 6; i++) await page.keyboard.press('Enter');
  await expect(page.getByRole('status').filter({ hasText: 'Étape 7 sur 7' })).toBeVisible();
  await expect(suivante).toBeDisabled();
  await expect(page.locator('#recap [data-acquis="attention"]')).toHaveAttribute('data-gagne', 'oui');
});
test('« il » regarde « forgeron » dans la tête 2', …);   // étape 6 ; la barre du mot 1 a data-cible ≥ 60 et le nombre affiché est le même
test('le masque : à l\u2019étape 5, les mots après « forgeron » sont masqués', …);
test('la carte complète : 9 lignes, 9 cases, cases masquées au-dessus de la diagonale', …);
test('mouvement réduit : les barres prennent leur valeur tout de suite', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' }); await ouvrir(page);
  await expect(page.locator('[data-mouvement]')).toHaveAttribute('data-mouvement', 'reduit');
  // aller à l'étape 6, puis, sans attendre :
  const barre = page.locator('[data-test="att-barre"][data-mot="1"]');
  const { cible, largeur } = await barre.evaluate((b) => ({ cible: b.dataset.cible, largeur: (b as HTMLElement).style.width }));
  expect(largeur).toBe(`${cible}%`);
});
test('sans JavaScript : la carte est lisible', …);
test('accessibilité, largeur, typographie aux étapes 6 et 7', …);
```

- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire le composant et la page d'essai.**
- [ ] **Étape 4 : vérifier que tout passe.**
- [ ] **Étape 5 : captures et relecture,** à l'étape 3 puis à l'étape 6, sur ordinateur et sur mobile, face à la maquette 10.
- [ ] **Étape 6 : commit**, message « Animation de l'attention pilotée par le lecteur ».

### Tâche 9 : la parité dans les navigateurs

**Fichiers :**

- Créer : `site/src/lib/mini-modele/parite.ts`, test `site/src/lib/mini-modele/parite.test.ts`
- Créer : `site/src/components/demos/ControleParite.svelte`, `site/src/essais/parite.mdx`, test `site/e2e/parite.spec.ts`
- Modifier : `site/playwright.config.ts`, `.github/workflows/site.yml`

**Interfaces :**

- Consomme : les tâches 1 à 5.
- `parite.ts` fait en TypeScript ce que fait `attendus.py` :
  - `attendusCalcul()`, `attendusDonnees()`, `attendusModele()` (clés `modele` et `entrainement`), `attendusAttention()` ;
  - chacune renvoie un objet de la même forme que le fichier JSON correspondant. Les entrées tirées au hasard sont retirées avec `Hasard`.
- `ControleParite.svelte` :
  - calcule les quatre objets dans la page ;
  - les écrit en JSON dans `<pre data-test="parite-calcul">`, `parite-donnees`, `parite-modele` et `parite-attention` ;
  - puis pose `data-pret="oui"` sur la racine `data-test="parite"`.
- `parite.mdx` : frontmatter d'un chapitre `1.1`, sans acquis, et un texte d'une ligne qui dit à quoi sert la page.
- `playwright.config.ts` : si `FORGE_TOUS_NAVIGATEURS=1`, on ajoute les projets `parite-firefox` (`browserName: 'firefox'`, `channel: undefined`) et `parite-webkit` (`browserName: 'webkit'`, `channel: undefined`), tous deux limités à `testMatch: /parite\.spec\.ts/`.
- `site.yml`, tâche `tests` : `npx playwright install --with-deps chromium firefox webkit`, et `FORGE_TOUS_NAVIGATEURS: '1'` à l'étape des parcours.

- [ ] **Étape 1 : écrire les tests qui échouent.**

```ts
// parite.test.ts
for (const [nom, calcul] of [['calcul', attendusCalcul], ['donnees', attendusDonnees], ['modele', attendusModele], ['attention', attendusAttention]] as const)
  expect(calcul()).toEqual(JSON.parse(readFileSync(`../projets/mini-modele/tests/attendus-${nom}.json`, 'utf8')));
// e2e/parite.spec.ts
test('le navigateur calcule exactement comme le Python', async ({ page }) => {
  await page.goto('/forge-ia/essais/parite/');
  await expect(page.locator('[data-test="parite"]')).toHaveAttribute('data-pret', 'oui', { timeout: 60_000 });
  for (const nom of ['calcul', 'donnees', 'modele', 'attention'])
    expect(JSON.parse(await page.locator(`[data-test="parite-${nom}"]`).innerText()), nom).toEqual(lireAttendus(nom));
});
```

- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire `parite.ts`, le composant, la page, la configuration et le workflow.**
- [ ] **Étape 4 : vérifier que tout passe.**
  - Avec Chrome : `npx playwright test e2e/parite.spec.ts --workers=4`.
  - Puis Firefox et WebKit, qui se téléchargent dans le cache de Playwright : `npx playwright install firefox webkit`, puis `$env:FORGE_TOUS_NAVIGATEURS='1'; npx playwright test e2e/parite.spec.ts --workers=4`. Attendu : identique dans les quatre projets.
  - **Si un moteur s'écarte, ne pas desserrer le test :** trouver l'opération en cause, la remplacer par une suite de `+ − × ÷` dans les deux langages, et régénérer les attendus.
- [ ] **Étape 5 : commit**, message « Parité exacte vérifiée dans Chrome, Firefox et WebKit ». Le workflow ne sera vérifié qu'au prochain push, que décide l'utilisateur.

### Tâche 10 : le calculateur (formules, données sourcées, jumeau de forge)

**Fichiers :**

- Créer : `site/src/lib/calculateur/formules.ts`, `donnees.ts`, `ton-ia.ts`, `formats.ts`, `paris.ts`
- Test : `formules.test.ts`, `donnees.test.ts`, `ton-ia.test.ts`, `formats.test.ts`, `paris.test.ts`, dans le même dossier

**Interfaces :**

- Consomme : `nombre` (tâche 6).
- `formules.ts`. On note N les paramètres, D les jetons, s le contexte, b le micro-lot, h la dimension, L les couches et a les têtes.

```ts
interface Forme { parametres: number; couches: number; dim: number; tetes: number; tetesKv: number; contexte: number; vocabulaire: number }
operationsEntrainement(parametres: number, jetons: number): number              // 6·N·D (Kaplan, Chinchilla)
operationsParJetonAvecAttention(f: Forme): number                               // 6N + 12·L·h·s (PaLM, nanoGPT)
dureeSecondes(operations, creteTflops, efficacite, cartes): number               // operations / (crete·1e12·efficacite·cartes)
efficaciteMesuree(parametres, jetonsParSeconde, creteTflops): number             // 6·N·débit / (crete·1e12)
memoireEntrainementOctets(f: Forme, microLot = 1): { etats: number; activations: number; total: number }  // 16·N ; 34·s·b·h·L
activationsSansFlashOctets(f: Forme, microLot = 1): number                        // s·b·h·L·(34 + 5·a·s/h)
memoirePoidsOctets(parametres, octetsParPoids): number
cacheKvOctets(f: Forme, jetons: number, lot = 1): number                          // 2·2·L·tetesKv·(h/a)·jetons·lot
plafondGenerationJetonsParSeconde(parametres, octetsParPoids, bandePassanteGoS): number  // bande·1e9 / (N·octets)
cartesMinimum(octets, memoireGo): number                                          // ceil(octets / (memoireGo·1024³))
energieKwh(puissanceW, cartes, secondes): number
coutElectriciteEur(kwh, eurParKwh): number
coutLocationUsd(secondes, cartes, usdParHeure): number
usdEnEur(usd, usdPourUnEur): number
```

- `donnees.ts`. Chaque entrée porte une `source: { titre: string; url: string; releveLe: 'AAAA-MM-JJ'; statut: 'primaire' }`.
  - `interface Materiel { id; nom; categorie: 'grand-public' | 'colab' | 'centre-de-donnees'; creteTflops: number /* bf16 dense, sans sparsité */; memoireGo: number; bandePassanteGoS: number | null; puissanceW: number | null; note?: string; source }`.
  - `MATERIELS` (relevés le 2026-11-03).
    - Whitepaper RTX Blackwell : https://images.nvidia.com/aem-dam/Solutions/geforce/blackwell/nvidia-rtx-blackwell-gpu-architecture.pdf

| id | nom | catégorie | TFLOPS | Go | Go/s | W | source |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| `rtx-5070-ti` | RTX 5070 Ti | grand-public | 87,9 | 16 | 896 | 300 | whitepaper, tableau 5 |
| `rtx-5080` | RTX 5080 | grand-public | 112,6 | 16 | 960 | 360 | whitepaper, tableau 4 |
| `rtx-5090` | RTX 5090 | grand-public | 209,5 | 32 | 1 792 | 575 | whitepaper, tableau 3 |
| `rtx-4090` | RTX 4090 | grand-public | 165,2 | 24 | 1 008 | 450 | whitepaper, tableau 3 |
| `t4` | T4 (Colab gratuit) | colab | 65 (FP16 mixte, pas de bf16 : le dire en `note`) | 16 | 320 | 70 | https://www.nvidia.com/en-us/data-center/tesla-t4/ |
| `l4` | L4 (Colab) | colab | 121 | 24 | 300 | 72 | https://www.nvidia.com/en-us/data-center/l4/ |
| `a100-80` | A100 80 Go SXM | centre-de-donnees | 312 | 80 | 2 039 | 400 | https://www.nvidia.com/en-us/data-center/a100/ |
| `h100-sxm` | H100 SXM | centre-de-donnees | 989 (1 979 « avec sparsité » ÷ 2) | 80 | 3 350 | 700 | https://www.nvidia.com/en-us/data-center/h100/ |
| `h200` | H200 SXM | centre-de-donnees | 989 | 141 | 4 800 | 700 | https://www.nvidia.com/en-us/data-center/h200/ |
| `b200` | B200 | centre-de-donnees | 2 250 (36 PFLOPS pour 8, en sparse, ÷ 8 ÷ 2) | 180 | `null` | `null` | https://www.nvidia.com/en-us/data-center/hgx/ et /dgx-b200/ |

  - `PRIX_LOCATION: { materiel: string; fournisseur: string; offre: string; usdParHeure: number; source }[]` (par carte et par heure, hors taxes).
    - RunPod, https://www.runpod.io/pricing (« Updated » 2026-10-28, relevé le 2026-11-03), offres « Community » et « Secure » : `rtx-4090` 0,34 et 0,89 ; `rtx-5090` 0,69 et 1,19 ; `a100-80` 1,39 et 1,79 ; `h100-sxm` 2,69 et 3,99 ; `h200` 3,59 et 5,29 ; `b200` 5,98 et 7,99.
    - Lambda, https://lambda.ai/pricing (relevé le 2026-11-03) : `b200` 6,69 (8 cartes) et 6,99 (1 carte) ; `h100-sxm` 3,99 (8 cartes) et 4,29 (1 carte) ; `a100-80` 2,79 (8 cartes).
    - Azure, ND96isr H100 v5, East US, API https://prices.azure.com/api/retail/prices (relevé le 2026-11-03) : `h100-sxm` 12,29 (98,32 $/h ÷ 8).
  - `TAUX_DE_CHANGE = { usdPourUnEur: 1.1179, source: BCE https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml, 2026-11-03 }`.
  - `ELECTRICITE = { eurParKwh: 0.2001, libelle: 'EDF, Tarif Bleu, option Base, 6 kVA, TTC, applicable au 1er août 2026', source: https://particulier.edf.fr/content/dam/2-Actifs/Documents/Offres/Grille_prix_Tarif_Bleu.pdf, 2026-11-03 }`.
  - `EFFICACITE_PAR_DEFAUT = { 'grand-public': 0.5, colab: 0.4, 'centre-de-donnees': 0.4 }`.
  - `REPERES_EFFICACITE` : PaLM 540B 46,2 % (arXiv 2204.02311) ; Llama 3 405B de 38 à 43 % (arXiv 2407.21783).
  - `MODELES_PUBLICS: (Forme & { id; nom; jetonsOrigine: number; source })[]` :
    - GPT-3 175B : 96 couches, dim 12 288, 96 têtes (96 têtes KV), contexte 2 048, vocabulaire 50 257, 300 milliards de jetons (arXiv 2005.14165, tableaux 2.1 et D.1) ;
    - Llama 3 8B : 32 couches, dim 4 096, 32 têtes, 8 têtes KV ;
    - Llama 3 70B : 80 couches, dim 8 192, 64 têtes, 8 têtes KV ;
    - Llama 3 405B : 126 couches, dim 16 384, 128 têtes, 8 têtes KV.

    Pour les trois Llama 3 : contexte 8 192, vocabulaire 128 000, et paramètres nominaux 8, 70 et 405 milliards (arXiv 2407.21783, tableau 3 et section 3). Jetons d'origine : 15,6 billions pour 405B, et ce que dit l'article pour 8B et 70B.

    Ces formes ne sont pas dans la recherche du plan : **les vérifier dans les sources à l'étape 3**, avec la date du jour comme `releveLe`.
- `ton-ia.ts` :
  - `PAS_LARGEUR_CACHEE = 64`, `JETONS_PAR_PARAMETRE = 20` ;
  - `largeurCachee(dim)` : `max(1, floor((dim + 12) / 24)) × 64`, calcul entier comme forge ;
  - `nombreParametres(c: { tailleVocabulaire; dim; couches; tetes; longueurContexte })` : la formule de `forge.modele.config.nombre_parametres` ;
  - `PRESETS_FORGE` : les 5 formes de forge, avec un vocabulaire de 32 768 et `tetesKv = tetes` ;
  - `dureeHeures(jetons, jetonsParSeconde)` = `jetons / jetonsParSeconde / 3600`, comme `forge.mesure.estimer`, avec une erreur si le débit n'est pas plus grand que 0 ;
  - `MESURES_TON_IA` (source `docs/mesures/entrainement-2026-11.md` et `projets/forge/configs/mini.toml`, mesuré le 2026-11-03) :
    - sur la carte : `mini` 231 934 jetons/s (micro-lot 16) ; `petit` 138 433 (micro-lot 4, 5,5 Go) ; `moyen` 62 368 (micro-lot 2, 5,4 Go) ; `grand` 32 704 (micro-lot 2, 9,1 Go) ; `tres_grand` 17 855 (micro-lot 1, 10,9 Go) ;
    - sur le processeur : `mini` 2 707, `petit` 1 749, `moyen` 776, `grand` 404, `tres_grand` 235.
- `formats.ts`. Toute entrée non finie ou négative lève une erreur : l'interface ne doit jamais en produire.
  - `formaterDuree(s)` :
    - moins de 60 s : « n s » ;
    - moins d'une heure : « n min » ;
    - moins de 48 h : « x h », avec une décimale sous 10 h ;
    - moins de 365,25 jours : « x jours », avec une décimale sous 10 ;
    - au-delà : « x an » si x < 2, sinon « x ans », avec une décimale sous 10. Une année vaut 31 557 600 s.
  - `formaterQuantite(n)` :
    - moins d'un million : un entier ;
    - en millions, avec une décimale (« million » au singulier si x < 2) ;
    - en milliards, à 3 chiffres significatifs ;
    - au-delà de 10¹², « 15 600 milliards ».
  - `formaterPuissanceDeDix(x)` : « 2,26 × 10¹⁹ », avec U+202F autour de ×.
  - `formaterOctets(o)` : en Go (1024³), avec une décimale sous 100 ; en To au-delà de 1 024 Go.
  - `formaterEuros(x)` :
    - « moins d’un euro » ;
    - 2 décimales sous 10 € ;
    - un entier sous 1 000 € ;
    - 3 chiffres significatifs sous un million ;
    - « 1,2 million d’euros » ou « 33 millions d’euros » ;
    - puis les milliards de la même façon.
  - `formaterPrix(usd)` : « 2,69 $ ».
- `paris.ts` :
  - `choixOperationsTonIA()` : « 10¹³ opérations », « 10¹⁶ opérations » et « 10¹⁹ opérations ». L'exposant juste e est lu par `toExponential()` sur 6·N·20N de `tres_grand` ; les autres valent e − 6 et e − 3.
  - `choixCoutH100()` : « Quelques euros », « Des dizaines à des centaines d’euros » ou « Des dizaines de milliers d’euros ».
    - Le coût est celui de ton IA sur une H100 SXM à 40 %, de son prix primaire le plus bas au plus haut, converti en euros.
    - Juste : 0 si la fourchette tient entre 1 et 10 € ; 1 entre 10 et 1 000 € ; 2 à partir de 10 000 €. Sinon, une erreur « Exemple devenu faux ».
  - `choixMemoireTonIA()` : « Moins de 16 Go » ou « Plus de 16 Go », d'après `memoireEntrainementOctets(tres_grand).total`.
    - Garde-fou : le verdict doit concorder avec le pic mesuré de 10,9 Go.

- [ ] **Étape 1 : écrire les tests qui échouent.**

```ts
// formules.test.ts : les exemples des sources
expect(operationsEntrainement(400e6, 8.0e9)).toBeCloseTo(1.92e19, -16);                 // Chinchilla, tableau 3
// formeAvec(partiel) : aide du test qui complète une Forme avec des valeurs sans effet sur la formule testée
expect(memoireEntrainementOctets(formeAvec({ parametres: 1.5e9 })).etats).toBe(24e9);   // ZeRO : « au moins 24 Go »
expect(activationsSansFlashOctets(formeAvec({ contexte: 2048, dim: 1024, couches: 24, tetes: 16 }))).toBe(9_764_339_712); // Korthikanti, éq. 1
expect(cacheKvOctets(formeAvec({ couches: 32, tetesKv: 32, dim: 4096, tetes: 32 }), 4096)).toBe(2_147_483_648);
expect(Math.abs(operationsEntrainement(175e9, 300e9) / 3.14e23 - 1)).toBeLessThan(0.01); // GPT-3, tableau D.1
expect(Math.abs(operationsEntrainement(405e9, 15.6e12) / 3.8e25 - 1)).toBeLessThan(0.01); // Llama 3 405B
// ton-ia.test.ts : jumeau de forge, sans importer forge
const config = readFileSync('../projets/forge/forge/modele/config.py', 'utf8');
const formes = [...config.matchAll(/"(\w+)": ConfigModele\(dim=(\d+), couches=(\d+), tetes=(\d+), longueur_contexte=(\d+)\)/g)];
expect(formes.map(([, n, d, c, t, l]) => [n, +d, +c, +t, +l])).toEqual(Object.entries(PRESETS_FORGE).map(([n, f]) => [n, f.dim, f.couches, f.tetes, f.contexte]));
expect(config).toContain('PAS_LARGEUR_CACHEE = 64');
expect(readFileSync('../projets/forge/forge/mesure.py', 'utf8')).toContain('JETONS_PAR_PARAMETRE = 20');
for (const [d, h] of [[384, 1024], [512, 1344], [768, 2048], [1024, 2752], [1280, 3392], [36, 128], [12, 64]]) expect(largeurCachee(d)).toBe(h); // forge/tests/test_modele.py
expect(PRESETS_FORGE.mini.parametres).toBe(23_204_736);          // docs/mesures/ton-ia-mini.md
expect(PRESETS_FORGE.tres_grand.parametres).toBe(433_573_120);   // configs/principal.toml
expect(dureeHeures(20 * 433_573_120, 17_855)).toBeCloseTo(134.9, 1);
expect(efficaciteMesuree(433_573_120, 17_855, 87.9)).toBeCloseTo(0.528, 3);
expect(17_855 * operationsParJetonAvecAttention(PRESETS_FORGE.tres_grand) / 87.9e12).toBeCloseTo(0.656, 3);
const rapport = readFileSync('../docs/mesures/entrainement-2026-11.md', 'utf8').replace(/[\u00A0\u202F]/g, ' ');
for (const v of ['138 433', '62 368', '32 704', '17 855', '1 749', '776', '404', '235', '10,9 Go']) expect(rapport).toContain(v);
// formats.test.ts
expect(formaterDuree(57_022)).toBe('16 h'); expect(formaterDuree(3_600)).toBe('1,0 h');
expect(formaterDuree(513_265)).toBe('5,9 jours'); expect(formaterDuree(36_846_000)).toBe('1,2 an');
expect(formaterDuree(31_557_600 * 27_315)).toBe('27\u202F315 ans');
expect(formaterQuantite(433_573_120)).toBe('433,6 millions'); expect(formaterQuantite(8_671_462_400)).toBe('8,67 milliards');
expect(formaterQuantite(15.6e12)).toBe('15\u202F600 milliards'); expect(formaterPuissanceDeDix(2.2558e19)).toBe('2,26\u202F×\u202F10¹⁹');
expect(formaterOctets(8.72e9)).toBe('8,1 Go'); expect(formaterEuros(8.5587)).toBe('8,56 €'); expect(formaterEuros(0.4)).toBe('moins d\u2019un euro');
expect(formaterEuros(33.4e6)).toBe('33 millions d\u2019euros'); expect(() => formaterDuree(NaN)).toThrow();
// donnees.test.ts
for (const m of MATERIELS) expect(m.source.url).toMatch(/^https:\/\//);
for (const p of PRIX_LOCATION) { expect(p.source.statut).toBe('primaire'); expect(MATERIELS.some((m) => m.id === p.materiel)).toBe(true); }
// paris.test.ts : un seul choix juste par pari, et les bonnes réponses attendues aujourd'hui
expect(choixOperationsTonIA().find((c) => c.juste)?.texte).toBe('10¹⁹ opérations');
expect(choixCoutH100().find((c) => c.juste)?.texte).toBe('Des dizaines à des centaines d\u2019euros');
expect(choixMemoireTonIA().find((c) => c.juste)?.texte).toBe('Moins de 16 Go');
```

- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : vérifier les formes et les jetons de GPT-3 et de Llama 3 dans leurs articles.** Si une valeur diffère de ce plan, la corriger dans les données (jamais dans la formule), et le dire dans le message de commit. Écrire ensuite les cinq modules.
- [ ] **Étape 4 : vérifier que tout passe.**
- [ ] **Étape 5 : commit**, message « Calculateur : formules sourcées, matériel et prix datés, jumeau de forge ».

### Tâche 11 : le composant Calculateur et sa page d'essai

**Fichiers :**

- Créer : `site/src/components/demos/Calculateur.svelte`, `site/src/essais/calculateur.mdx`
- Test : `site/e2e/calculateur.spec.ts`

**Interfaces :**

- Consomme : la tâche 10 entière, et `NombreManipulable` avec `texte` (tâche 7).
- Props : `{ nom?: string /* 'calc' */; verrou?: string; acquis?: string; initial?: { modele?: string; materiel?: string; cartes?: number; jetonsParParametre?: number; efficacite?: number } }`.
  - Défauts : `tres_grand`, `rtx-5070-ti`, 1 carte, 20 jetons par paramètre, et l'efficacité par défaut de la catégorie.
  - Le plan 5 s'en servira pour ouvrir le calculateur déjà réglé, depuis 1.5 et depuis les encadrés « labo ».
- Émet `forge:acquis` à la première modification du modèle ou du matériel.

**Contenu et textes exacts :**

- **La phrase :** « Entraîner [modèle] en lui faisant lire [20] jetons par paramètre, soit {8,67 milliards} de jetons, avec [1] × [carte], à [50 %] d'efficacité. »
  - [modèle] et [carte] sont des `<select>` natifs, stylés comme le champ de l'atelier (fond soleil pâle, souligné soleil). Leurs `optgroup` sont « Ton IA » / « Modèles publics » pour le modèle, « Chez toi » / « Colab » / « En location » pour la carte.
  - Le nombre de jetons par paramètre se règle parmi 1, 2, 5, 10, 20, 50, 100, 200, 500, 1 000 et 2 000.
  - Le nombre de cartes se règle parmi 1, 2, 4, …, 16 384.
  - L'efficacité va de 10 à 70 %, de 1 en 1.
  - Ces trois nombres sont des `NombreManipulable` avec `texte`, et `testId` : `calc-jetons`, `calc-cartes` et `calc-efficacite`.
  - Les sélecteurs portent `data-test="calc-modele"` et `calc-materiel`.
- **Le relevé** : un tableau typographié à deux colonnes, chiffres en Gabarito tabulaires. Lignes :
  - « Calcul » ;
  - « Durée » (`calc-duree`) ;
  - « Mémoire pour l'entraîner » (`calc-memoire`), avec « ça tient sur une carte de 16 Go » ou « il faut au moins N cartes de 16 Go » ;
  - « Mémoire pour s'en servir » (bf16, int8, int4, plus le cache de 4 096 jetons) ;
  - « Génération, au plus » (si la bande passante est connue) ;
  - « Électricité » (cartes grand public seulement) : « 42,8 kWh, environ 8,56 € » ;
  - « Location » (`calc-cout`) : la fourchette en euros, puis en dollars, ou « pas de prix relevé pour cette carte ».
- **« Voir le calcul »** est une bascule (`.bascule`). Elle déplie chaque formule avec ses nombres :
  - « 6 × 433,6 millions × 8,67 milliards = 2,26 × 10¹⁹ opérations » ;
  - les deux efficacités (6N, et en comptant l'attention), quand le modèle est une taille de ton IA.
- **« Repère mesuré : ton IA sur ce PC »** (`calc-reperes`) : un tableau des 5 tailles, avec le débit sur la carte, la durée pour 20 jetons par paramètre (`dureeHeures`), l'efficacité implicite et le débit sur le processeur.
  - Quand le réglage est une taille de ton IA sur 1 × RTX 5070 Ti, une phrase compare : « Calcul : 5,9 jours. Mesuré : 5,6 jours (135 h). L'écart vient de l'efficacité : 52,8 % mesurés contre 50 % supposés. »
- **Les sources :** pour la carte et chaque prix affiché, le lien et « relevé le 3 novembre 2026 ». Les prix de location varient de 20 à 50 % en quelques mois : une phrase le dit.

**`calculateur.mdx`.** Frontmatter d'un chapitre `1.6`, avec les acquis `operations`, `cout` et `calcul`.

- Le pari `operations` (« Combien d'opérations faut-il pour entraîner ton IA (433,6 millions de paramètres, 20 jetons par paramètre) ? », `ouvre="calculateur"`).
- Le pari `cout` (« Louer des H100 pour entraîner ton IA coûterait plutôt… »).
- `<Verrou nom="calculateur">` autour de `<Calculateur client:load verrou="calculateur" acquis="calcul" />`.

- [ ] **Étape 1 : écrire les tests qui échouent.** Les valeurs attendues sont calculées dans le test par les modules de la tâche 10, importés directement : ils sont en TypeScript pur, sans import propre à Vite.

```ts
test('réglage de départ : ton IA sur la RTX 5070 Ti', async ({ page }) => {
  await ouvrir(page);
  const s = dureeSecondes(operationsEntrainement(N, 20 * N), 87.9, 0.5, 1);
  await expect(page.locator('[data-test="calc-duree"]')).toContainText(formaterDuree(s));
  await expect(page.locator('[data-test="calc-memoire"]')).toContainText('ça tient sur une carte');
  await expect(page.locator('[data-test="calc-reperes"]')).toContainText(`${nombre(17_855)} jetons`);
  await expect(page.locator('[data-test="calc-reperes"]')).toContainText(pourcent(efficaciteMesuree(N, 17_855, 87.9), 1));
});
test('valeurs extrêmes : 405 milliards sur une seule carte, puis 16 384 H100', async ({ page }) => {
  await ouvrir(page);
  await page.locator('[data-test="calc-modele"]').selectOption('llama-3-405b');
  await expect(page.locator('[data-test="calc-duree"]')).toContainText('ans');
  await expect(page.locator('[data-test="calc-memoire"]')).toContainText('il faut au moins');
  await page.locator('[data-test="calc-materiel"]').selectOption('h100-sxm');
  await page.locator('[data-test="calc-cartes"]').focus(); await page.keyboard.press('End');
  await expect(page.locator('[data-test="calc-cartes"]')).toHaveAttribute('aria-valuetext', '16\u202F384');
  await expect(page.locator('[data-test="calc-cout"]')).toContainText('millions d\u2019euros');
  const texte = await page.locator('.calculateur').innerText();
  expect(texte).not.toMatch(/NaN|Infinity|e\+/);
  await verifierSansDebordement(page);
});
test('au clavier : tous les réglages', …);          // Tab jusqu'à chaque réglage ; flèches ; select au clavier
test('chaque prix affiché a sa source et sa date', …);
test('« Voir le calcul » déplie les formules', …);
test('acquis gagné au premier changement de carte', …);
test('accessibilité, largeur, typographie', …);
```

- [ ] **Étape 2 : vérifier l'échec.**
- [ ] **Étape 3 : écrire le composant et la page d'essai.**
- [ ] **Étape 4 : vérifier que tout passe,** puis la suite entière : `npx vitest run`, puis `npx playwright test --workers=4`.
- [ ] **Étape 5 : captures et relecture,** sur ordinateur et sur mobile, avec le réglage de départ puis avec 405 milliards sur 16 384 H100. Corriger tout ce qui fait « tableau de bord ».
- [ ] **Étape 6 : commit**, message « Calculateur de coût, sourcé et daté, avec le repère mesuré de ton IA ».

### Tâche 12 : clôture du plan 3

**Fichiers :**

- Modifier : `projets/mini-modele/README.md` (version finale)

- [ ] **Étape 1 : lancer toutes les vérifications.**
  - `cd projets/mini-modele; uv run pytest -q` ;
  - `cd site; npx vitest run` ;
  - `npx playwright test --workers=4` ;
  - `npm run build`, puis vérifier que `dist/` ne contient aucune page `essais/`.

  Attendu : tout passe. Noter les durées de pytest et de Vitest, dont le test long.
- [ ] **Étape 2 : finir le README du jumeau.**
  - Ce qu'il calcule, et pourquoi il donne au bit près les nombres de la page.
  - Les commandes : tests, `entrainer`, régénérer les prénoms, régénérer les attendus.
  - La source et la licence des prénoms.
  - Les régions balisées, pour les plans 4 et 5 : `exp`, `log`, `scores`, `softmax`, `melange`, `avant`, `perte`, `lot`, `ecretage`, `adamw`.
- [ ] **Étape 3 : écrire le jalon dans la mémoire partagée,** si elle répond. Texte : « Projet forge-ia (La Forge IA) : les trois démos restantes de la vague 1 sont construites et testées (mini-modèle qui apprend dans le navigateur, animation de l'attention, calculateur de coût), avec un jumeau Python exact dans projets/mini-modele ». Si elle ne répond pas, le dire dans le compte rendu.
- [ ] **Étape 4 : montrer les démos à l'utilisateur.**
  - Lancer `npm run build:essais` puis `npm run preview` (port 8530).
  - Donner les trois adresses `/forge-ia/essais/mini-modele/`, `/attention/` et `/calculateur/`, avec des captures ordinateur et mobile.
  - Demander avec AskUserQuestion si elles conviennent, puis arrêter le serveur.
  - Si l'utilisateur demande des changements, les faire dans la tâche concernée, puis redemander.
  - Proposer ensuite le plan 4 (Partie 0).
- [ ] **Étape 5 : commit**, message « Jumeau des démos : documentation finale ».
