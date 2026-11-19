# Le faire raisonner : les traces et le GRPO

Un problème de calcul ne se devine pas : il faut le poser, le décomposer, puis donner un nombre, et ce nombre est juste
ou faux. Ce projet refait, pas à pas et à la main, les pièces que le chapitre 1.9 explique, puis les compare à forge (le
paquet `forge`, dans `projets/forge`), le moteur de « ton IA » :

- il **montre un problème** généré par programme (`forge.raisonnement.problemes`) avec sa trace, une étape de calcul par
  ligne, et la conversation que ton IA lit au SFT de raisonnement, encodée par le tokenizer figé, avec son masque de
  perte (jamais l'énoncé) ;
- il **vérifie une réponse** avec la règle de forge (`forge.raisonnement.verification`) : le dernier nombre du texte, et
  une réponse coupée n'est jamais juste ;
- il refait **l'avantage d'une réponse dans son groupe** du GRPO : `r − moyenne(r)` sur son groupe, égal à
  `forge.raisonnement.grpo.avantages` à 10⁻¹² près, et **la chance qu'un groupe n'apprenne rien** : `pⁿ + (1 − p)ⁿ` ;
- il fait un **tout petit GRPO** sur le processeur : un modèle minuscule, d'abord affiné à répéter un chiffre
  (« Répète : 7 » → « 7 »), puis des pas de GRPO de forge sur cette tâche (`pas_grpo`, sans réécrire la boucle) ;
- il **résume** ce que le plan 7 construit et mesure sur ton IA 1.9 (le rapport d'étape de `forge evaluer-etape`, le
  contrôle de départ du GRPO, les courbes de l'entraînement) en fichiers que le chapitre lit.

C'est le projet du chapitre 1.9 de La Forge IA, « Le faire raisonner », en ligne à l'adresse
<https://chipat-neko.github.io/forge-ia/partie-1/1-9/>. Les mots techniques sont expliqués dans le glossaire :
<https://chipat-neko.github.io/forge-ia/annexes/glossaire/>. Comme les projets 0.3 à 0.5 et 1.4 à 1.8, il utilise
PyTorch, en deux versions au choix : celle pour carte NVIDIA (extra `gpu`, CUDA 13.2) et celle pour le processeur
seul (extra `cpu`). Les commandes ci-dessous prennent le processeur, qui suffit à tout ce que ce projet calcule.

Il dépend de forge et du projet 1.5 par chemin (`forge-ia = { path = "../forge", editable = true }` et
`pre-entrainement = { path = "../1.5-pre-entrainement", editable = true }` dans `pyproject.toml`) : il faut donc le
dépôt entier, pas seulement ce dossier. Il ne modifie aucun fichier de forge.

## Ce qu'il prend à forge

- `forge.raisonnement.problemes` : `generer_probleme`, `conversation_de_probleme`, `Probleme` (le générateur, tel quel :
  ce projet le montre, il ne le refait pas) ; `forge.raisonnement.verification` : `est_juste` et `extraire_nombre` ;
- `forge.conversation.format` : `encoder_conversation`, `Tour`, `Reponse` ; `forge.tokenizer` : `TokenizerOctets` (le
  tokenizer figé de « ton IA ») ;
- `forge.raisonnement.grpo` : `avantages` (la pièce refaite à la main), `tirer`, `apprendre`, `reussite`, `recompense`,
  `NOM_DU_CONTROLE` (le nom du fichier de contrôle) ; `forge.entrainement.methodes` : `pas_grpo` (un pas de GRPO) ;
  `forge.entrainement.boucle` : `ReglagesGRPO` ;
- `forge.evaluation.etape` : `VERSION_DU_RAPPORT_D_ETAPE` (le format du `rapport.json` que `resumer` lit) ;
- `forge.modele` : `Transformer` et `ConfigModele` ; `forge.affinage.jeu` : `IGNORE`.

Et au projet 1.5 : `pre_entrainement.journal` (`lire`, `serie`) pour les courbes.

## Installer uv

`uv` installe Python et les bibliothèques de chaque projet. Le fichier `.python-version` demande Python 3.12 : uv le
télécharge lui-même s'il manque. Pour installer uv, voir le README du projet 0.3 (`projets/0.3-poste`), ou
<https://docs.astral.sh/uv/getting-started/installation/>.

## Lancer

Récupère le dépôt, puis va dans le dossier du projet. Les commandes sont les mêmes dans PowerShell (Windows) et dans
un terminal (Linux, Mac) :

```bash
git clone https://github.com/chipat-neko/forge-ia
cd forge-ia/projets/1.9-raisonnement
```

```bash
uv run --extra cpu python -m raisonnement_pas_a_pas probleme achats 2 7
uv run --extra cpu python -m raisonnement_pas_a_pas verifier "12 fois 7 font 84." --attendu 84
uv run --extra cpu python -m raisonnement_pas_a_pas avantages 1,0,0,1 0,0,0,0
uv run --extra cpu python -m raisonnement_pas_a_pas signal --p 0.2 --n 8
uv run --extra cpu python -m raisonnement_pas_a_pas essai --pas 20
```

- `probleme` montre un problème (famille, difficulté, graine : la même graine, le même problème), sa trace et le nombre
  de jetons de sa conversation, dont ceux que la perte apprend. Les familles sont `addition`, `soustraction`,
  `multiplication`, `partage`, `achats` et `ages`, chacune avec ses difficultés (le nombre d'étapes de calcul).
- `verifier` dit le nombre lu dans une réponse et si elle est juste. `--coupee` dit qu'elle a été coupée par la limite de
  jetons (jamais juste). Le code de sortie est 1 si la réponse n'est pas juste.
- `avantages` calcule l'avantage de chaque réponse de chaque groupe (les récompenses d'un groupe, séparées par des
  virgules) à la main, et le compare à forge (le code de sortie est 1 s'ils diffèrent de plus de 10⁻¹²).
- `signal` donne la chance qu'un groupe de `--n` réponses n'apprenne rien quand chacune est juste avec la chance `--p`.
- `essai` fait le petit GRPO et écrit, à chaque pas, la récompense moyenne et la part de groupes sans signal. La
  récompense ne monte pas forcément, et rien ne triche pour qu'elle monte.

## Ce que ton IA 1.9 ajoute

Ces commandes lisent ce que le plan 7 construit et mesure sur ton IA, sans rien recalculer et sans rien écrire dans les
données de l'auteur (ce sont des fichiers qu'on lit) :

```bash
uv run --extra cpu python -m raisonnement_pas_a_pas resumer --rapport <rapport.json> --json mesures/etape-ton-ia-1.9.json
uv run --extra cpu python -m raisonnement_pas_a_pas resumer --rapport <rapport.json> --reference --json mesures/etape-ton-ia-1.5.json
uv run --extra cpu python -m raisonnement_pas_a_pas controle --sortie <FORGE_DONNEES>/entrainements/<sortie du grpo> --json mesures/controle-1.9.json
uv run --extra cpu python -m raisonnement_pas_a_pas courbes --journal <journal.jsonl> --json mesures/entrainement-grpo-1.9.json
```

- `resumer` lit le `rapport.json` de `python -m forge evaluer-etape --etape 1.9` et en tire
  `{version, etape, releve_le, mesures, echantillons}` : les mesures du rapport (`ifeval_fr`, `tenue`, `oubli`,
  `problemes`, `mgsm_fr`, `gsm8k_platinum_fr`), telles quelles, une mesure dont les données manquaient restant
  `{"absente": "<raison>"}`, et les échantillons, tels quels. Avec `--reference`, c'est la version de référence du
  rapport qui est résumée.
- `controle` lit `controle.json`, que `forge entrainer` (méthode `grpo`) écrit dans sa sortie avant le premier pas : le
  **contrôle de départ**. Forge tire `controle_reponses` réponses à chacun des `controle_invites` premiers problèmes, et
  compte les justes. Le relevé garde `{depart, invites, reponses, justes, taux, lance, secondes}`. **Sans aucune réponse
  juste, le RL n'aurait aucun signal** : forge n'en lance pas, écrit le contrôle avec `lance: false` et sort avec le
  **code 6**. Le relevé de ce refus est un résultat, pas une erreur : le chapitre le montre et l'explique.
- `courbes` réduit `recompense_moyenne` et `groupes_sans_signal` du journal d'un GRPO en paquets de pas, par
  `pre_entrainement.journal.serie`, avec le découpage du site ; un paquet sans aucune valeur finie (un RL qui diverge)
  reste `null`, et le site le montre comme absent. `reussite_val` garde chaque mesure de validation à son pas. Si le
  journal n'a aucun pas de GRPO (le contrôle de départ a refusé), le relevé est `{"lance": false}`.

## Les pièces à la main

Les régions de `raisonnement_pas_a_pas`, tirées des repères `# region: <nom>` et `# fin: <nom>` :

| Fichier | Région | Ce qu'il fait |
| --- | --- | --- |
| `problemes.py` | `probleme`, `verifier` | `montrer_probleme(famille, difficulte, graine)` : l'énoncé, la trace, la réponse et la conversation encodée, tels que forge les génère (un test, sur les 14 couples et vingt graines) ; `verifier_reponse` |
| `avantages.py` | `avantages` | `avantages_a_la_main(recompenses)` : égal à `forge.raisonnement.grpo.avantages` à 10⁻¹² près ; `sans_signal(p, n)` : `pⁿ + (1 − p)ⁿ`, par deux produits en boucle |
| `petit_grpo.py` | `pas-grpo` | `essai_grpo(appareil, pas)` : un modèle minuscule affiné à répéter un chiffre, puis `pas` pas de GRPO de forge |
| `resumer.py` | `resumer`, `controle`, `courbes` | `resumer_etape`, `controle`, `courbes_grpo` |
| `attendus.py` | | écrit `tests/attendus.json`, que les jumeaux TypeScript du site vérifient |

La région `test-grpo` est dans `tests/test_petit_grpo.py` : le test qui fait l'essai et vérifie qu'un groupe sans signal
ne laisse aucun gradient. La région `test-avantages` est dans `tests/test_avantages.py`.

## Les jumeaux TypeScript

Le site refait deux calculs en TypeScript, avec les mêmes fonctions et le même ordre d'opérations, et les compare au
fichier `tests/attendus.json` (écrit par `python -m raisonnement_pas_a_pas.attendus`) :

- `site/src/lib/partie-1/problemes.ts` : `genererProbleme(famille, difficulte, graine)` et `extraireNombre(texte)`
  (avec `estJuste`), traductions exactes de `forge.raisonnement.problemes` et `forge.raisonnement.verification`, listes
  de prénoms et d'objets comprises (le test relit `problemes.py` pour les comparer). Le tirage d'un entier de a à b est
  celui de forge (`a + suivant32() % (b − a + 1)`), le nombre lu est une fraction exacte (des `BigInt`), l'expression
  régulière n'emploie ni `\w` ni `\d` mais `\p{L}`, `\p{N}` et `[0-9]` ;
- `site/src/lib/partie-1/avantages.ts` : `avantages` et `sansSignal`, la moyenne par une boucle et les puissances par
  deux produits en boucle, donc les mêmes flottants que Python.

Sans tolérance, dans Node (Vitest) puis dans Chrome, Firefox et WebKit (la page d'essai de parité,
`e2e/parite.spec.ts`).

`tests/attendus.json` a cinq sections : `problemes` (chaque couple famille et difficulté, graines 0 à 4),
`problemes_reserves` (les mêmes couples aux graines des plages d'évaluation et de validation du RL, dont les prénoms
ne sont pas ceux de l'entraînement), `nombres` (des textes de réponse et leurs pièges : milliers séparés par une
espace ordinaire, insécable ou fine, virgule décimale, signe moins collé ou non, chiffres hors de 0 à 9, nombre plus
grand que les entiers sûrs de JavaScript, avec le nombre lu et le verdict de chaque réponse), `avantages` (dix
groupes) et `sans_signal` (une grille de p et de n).

## Les mesures et les sorties

Chaque fichier de mesures est écrit en UTF-8, fins de ligne LF, par le projet ; le site les lit à la construction.

| Fichier | D'où il vient |
| --- | --- |
| `mesures/etape-ton-ia-1.9.json`, `mesures/etape-ton-ia-1.5.json` | `resumer` sur le rapport de `forge evaluer-etape --etape 1.9` (à relever quand ton-ia-1.9 est publiée) |
| `mesures/controle-1.9.json` | `controle` sur la sortie du GRPO (à relever au démarrage du GRPO, avant son premier pas) |
| `mesures/entrainement-grpo-1.9.json` | `courbes` sur le journal du GRPO |

Tant qu'un de ces fichiers n'existe pas, le chapitre affiche « à mesurer » à sa place.

## Tester

```bash
uv run --extra cpu pytest -q
```

`test_notebook.py` exécute le notebook du chapitre (`notebooks/1.9-raisonnement.ipynb`) de bout en bout, sur le processeur.
