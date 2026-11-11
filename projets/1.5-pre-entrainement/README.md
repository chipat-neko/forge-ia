# Le pré-entraînement

Le pré-entraînement est l'étape où « ton IA » lit des quantités énormes de texte pour apprendre à
prédire le jeton suivant. Ce projet fait deux choses autour de lui, avec le vrai code de forge (le
paquet `forge`, dans `projets/forge`) :

- il **lit le journal** d'un entraînement : les sessions (un entraînement mis en pause puis repris en
  a plusieurs), la courbe de perte réduite en paquets de pas, et un résumé en quelques nombres. Il a
  relevé celui de la version d'une heure de « ton IA » (le modèle « mini », `mesures/ton-ia-mini.json`) ;
- il fait un **petit essai de pause et de reprise exacte** sur le processeur : un entraînement de
  60 pas, fait d'un trait, puis refait en l'arrêtant à mi-chemin et en le reprenant. Sur le processeur,
  les deux finissent sur la même perte, au bit près.

C'est le projet du chapitre 1.5 de La Forge IA, « Le pré-entraînement sur ton
GPU ». Ce chapitre n'est pas encore en ligne : il paraîtra après la fin de
l'entraînement de « ton IA », avec ses vrais chiffres, et son adresse
(`partie-1/1-5/` sur le site) n'existe pas encore. Les mots techniques sont
expliqués dans le glossaire :
<https://chipat-neko.github.io/forge-ia/annexes/glossaire/>. Comme les projets 0.3 à 0.5
et 1.4, il utilise PyTorch, en deux versions au choix : celle pour carte NVIDIA (extra `gpu`, CUDA
13.2) et celle pour le processeur seul (extra `cpu`). Les commandes ci-dessous prennent le processeur,
qui suffit à tout ce qu'il calcule ; l'essai peut aussi tourner sur la carte (`--appareil cuda` avec
l'extra `gpu`).

Il dépend de forge par chemin (`forge-ia = { path = "../forge", editable = true }` dans
`pyproject.toml`) : il faut donc le dépôt entier, pas seulement ce dossier. L'essai lit aussi le texte
du chapitre 1.1 (`projets/1.1-modele-de-langage/donnees/texte-du-site.txt`).

## Ce qu'il prend à forge

Le vrai code d'entraînement et de lecture du journal, rien n'est réécrit :

- `forge.entrainement` : `ConfigEntrainement`, `entrainer` (avec son option
  `arreter_apres`, qui sert à l'essai de pause) et `lire_config` (le fichier
  TOML d'un entraînement) ;
- `forge.modele` : `ConfigModele` et `nombre_parametres` ;
- `forge.tokenizer` : `TokenizerOctets`, qui charge le tokenizer figé de
  « ton IA » (`forge/ressources/tokenizer-ton-ia-v1.json`, qui ne se modifie
  jamais) ;
- `forge.suivi` : `lire_journal`, `PERTES_RECENTES` et `_FINS_DE_SESSION`
  (comment forge lit son propre journal et finit une session).

Ses tests importent aussi `forge.entrainement.ChargeurJetons` (lire les fragments de jetons
de l'essai), `ConfigEntrainement`, `ConfigModele` et `nombre_parametres`, et `TokenizerOctets`.

Il lit aussi le texte du chapitre 1.1
(`projets/1.1-modele-de-langage/donnees/texte-du-site.txt`) pour préparer les
données de l'essai.

## Installer uv

`uv` installe Python et les bibliothèques de chaque projet. Le fichier `.python-version` demande
Python 3.12 : uv le télécharge lui-même s'il manque. Pour installer uv, voir le README du projet 0.3
(`projets/0.3-poste`), ou <https://docs.astral.sh/uv/getting-started/installation/>.

## Lancer

Récupère le dépôt, puis va dans le dossier du projet. Les commandes sont les mêmes dans PowerShell
(Windows) et dans un terminal (Linux, Mac) :

```bash
git clone https://github.com/chipat-neko/forge-ia
cd forge-ia/projets/1.5-pre-entrainement
```

Si tu as déjà récupéré le dépôt, mets-le à jour (`git -C forge-ia pull`) avant de revenir dans ce
dossier.

```bash
uv run --extra cpu python -m pre_entrainement essai --appareil cpu --enregistrer sorties/essai-processeur.txt --json mesures/essai-processeur.json
uv run --extra cpu python -m pre_entrainement courbe --journal D:\forge-ia-donnees\entrainements\ton-ia-mini\journal.jsonl --config ..\forge\configs\mini.toml --json mesures/ton-ia-mini.json
```

- `essai` prépare les données de l'essai (le texte du site, encodé par le tokenizer figé de « ton
  IA », dans un dossier temporaire), puis entraîne un petit modèle (2 couches, des vecteurs de 64
  nombres, 60 pas de 1 024 jetons) trois fois en tout : d'un trait, arrêté au pas 30, puis repris
  jusqu'au pas 60. Il affiche les deux pertes finales, leur écart, et « la reprise est exacte : oui »
  si cet écart est nul. Sur le processeur, un écart non nul fait rendre le code de sortie 1. Avec
  `--enregistrer FICHIER`, il écrit aussi sa sortie dans FICHIER (UTF-8), précédée de la date du
  relevé ; avec `--json FICHIER`, son résultat. Sans `--appareil`, il prend la carte si PyTorch la
  voit, sinon le processeur (ou ce que dit la variable `FORGE_APPAREIL`). `--appareil cuda` sans
  carte dit quoi faire, sans trace Python, et rend le code 2.
- `courbe` lit le journal d'un entraînement de forge (`journal.jsonl`) et le fichier TOML qui l'a
  lancé, et affiche son résumé et ses sessions. Avec `--json FICHIER`, il écrit aussi
  `{"nom", "releve_le", "resume", "sessions", "courbe"}` : c'est ainsi que
  `mesures/ton-ia-mini.json` a été écrit. Le journal de « mini » est hors du dépôt (sous
  `FORGE_DONNEES`, `D:\forge-ia-donnees` sur le PC de l'auteur) : sans lui, la commande ne se
  rejoue pas, mais le fichier relevé est dans le dépôt. Sous Linux ou Mac, la
  commande a la même forme, avec des `/` dans les chemins (par exemple
  `--config ../forge/configs/mini.toml`) et le journal sous ton propre
  `FORGE_DONNEES`.

## Le journal

Une ligne de pas du journal de forge a `pas`, `jetons_vus`, `perte`, `taux`, `jetons_par_seconde` et
`secondes` (le temps de calcul cumulé de tout l'entraînement, sans les pauses), plus `perte_val` tous
les `evaluation_tous_pas`. Les autres lignes sont des évènements : `debut` ou `reprise` quand une
session commence ; `sauvegarde` ; `pause` ou `fin` quand elle finit. Le journal n'a pas de dates.

Tout est dans `pre_entrainement/journal.py`, avec trois fonctions, plus `lire(journal)`, qui lit le
fichier avec `forge.suivi.lire_journal` :

| Région | Fonction | Ce qu'elle rend |
| --- | --- | --- |
| `sessions` | `sessions(lignes)` | une session par `debut` ou `reprise` : son départ, son premier et son dernier pas, ses secondes de calcul, et sa fin (`pause`, `fin`, `perte_non_finie`, ou `coupée` quand le journal n'a pas de ligne de fin) |
| `courbe` | `courbe(lignes, points, pas_total)` | `pertes` en `[pas, moyenne]` par paquets de pas, `validations` en `[pas, perte]`, et `hasard` = ln 32 768 |
| (hors région) | `resume(lignes, config)` | `parametres`, `pas_total`, `pas_faits`, `jetons_vus`, `secondes_de_calcul`, `pauses`, `debit_moyen`, `perte_finale`, `validation_finale`, `perte_premier_pas`, `perte_dernier_pas` |

- Le temps d'une session est la différence entre les `secondes` cumulées de son dernier pas et celles de
  l'état d'où elle part : 0 pour `debut`, et pour une `reprise` le cumul du pas de sa ligne `reprise`.
  Il ne compte pas la sauvegarde qui suit le dernier pas de la session, et n'est jamais négatif.
- **Après un plantage**, forge reprend à la dernière sauvegarde : les pas d'après (ceux de la session
  `coupée`) sont refaits. `resume.secondes_de_calcul` reste la somme des sessions, c'est-à-dire le temps
  réellement passé à calculer, pas refaits compris ; `pas_faits` compte les pas distincts ; `courbe` garde la
  dernière occurrence de chaque pas (et de chaque validation), pour que la perte du pas p reste à l'indice p - 1.
  (forge coupe d'ordinaire lui-même le journal à la reprise ; le projet lit aussi un journal qui ne l'a pas été.)
  `tests/journal-factice-plantage.jsonl` en est un exemple.
- `courbe` découpe comme le site (`site/src/lib/courbe.ts`, `taillePaquet` et `moyennesParPaquets`) :
  `ceil(pas_total / 600)` pas par paquet, chaque point au milieu de son paquet, le dernier paquet
  éventuellement incomplet. `pas_total`, le troisième paramètre (la ligne de commande donne celui de la configuration), fixe la taille ; sans lui, c'est le nombre de pas du journal. Avec le total de la
  configuration, le lissage ne change pas pendant l'entraînement. Les sommes sont des boucles, pas `sum()` : le
  TypeScript additionne dans le même ordre.
- `perte_finale` est la moyenne des 20 derniers pas, comme le tableau de `docs/mesures/ton-ia-mini.md`.
  Le journal n'ayant pas de dates, `resume` donne les pertes du premier et du dernier pas plutôt que
  des dates : elles disent d'où l'on part et où l'on arrive.

## L'essai

Tout est dans `pre_entrainement/essai.py` :

| Région | Fonction | Ce qu'elle fait |
| --- | --- | --- |
| `essai-donnees` | `preparer_essai(racine, texte)` | écrit `racine/jetons` au format de `forge encoder` : `train/fragment-00000.bin` et `val/fragment-00000.bin` (`uint16` petit-boutiste), `index.json` et `.complet` |
| `essai-reprise` | `config_essai(appareil, racine, pas)` | la configuration : dim 64, 2 couches, 4 têtes, contexte 64 ; lot de 1 024 jetons, micro-lot 16, taux max 0,001, échauffement 6, validation tous les 20 pas, sans compilation |
| `essai-reprise` | `essai_pause_reprise(appareil, racine)` | les trois entraînements, et leurs deux pertes finales, leur écart, les secondes et l'appareil |

`preparer_essai` est un raccourci de la chaîne de données du chapitre 1.2 : un seul texte, encodé par
le tokenizer figé, suivi de `<|fin_texte|>`, dont les 90 premiers % des jetons vont à l'entraînement
et le reste à la validation. Il ne passe pas par `est_validation` : sur quelques centaines de
documents, 0,5 % pourrait n'en laisser aucun.

Arrêter l'essai à mi-chemin (`arreter_apres` de `forge.entrainement.entrainer`) fait comme Ctrl+C :
forge finit le pas en cours et sauvegarde tout. La seule différence est la ligne `pause` du journal,
que Ctrl+C écrit en plus.

## Les copies

- `pre_entrainement/appareil.py` est une copie, octet pour octet, de
  `projets/0.3-poste/poste/appareil.py` ;
- `carte_inutilisable`, dans `__main__.py`, est la copie, mot pour mot, de celle de
  `projets/0.5-reseau/premier_reseau/__main__.py` (le message quand PyTorch voit la carte sans
  pouvoir calculer dessus).

Des tests le vérifient quand l'original est là (ils sont sautés sinon). Une correction se fait dans 0.3 ou 0.5, puis se
recopie ici.

## Tester

```bash
uv run --extra cpu pytest -q
```

Le test de reprise (`test_reprise_exacte_sur_le_processeur`) est encadré par
`# region: test-reprise` / `# fin: test-reprise`, pour que le chapitre le montre. Les autres tests
vérifient les sessions, la courbe et le résumé sur `tests/journal-factice.jsonl` (un journal écrit à
la main : début, 5 pas, pause, reprise, 5 pas, fin), le format des données de l'essai, les messages
d'erreur en français, les copies exactes, les régions du paquet, les relevés enregistrés et le notebook.

Le test marqué `gpu` (`test_essai_sur_la_carte`) refait l'essai sur la carte graphique ; sans CUDA, il
est sauté. Tous les autres tournent sur le processeur.

## Ce que montre le chapitre

Le chapitre 1.5 montre :

| Fichier | Ce que le chapitre en montre |
| --- | --- |
| `tests/test_essai.py` | la région `test-reprise` |
| `forge/entrainement/planning.py` (dans forge) | `taux` |
| `forge/entrainement/boucle.py` (dans forge) | `_creer_optimiseur` et `_pas_d_optimisation` |

Les régions de `pre_entrainement/journal.py` (`sessions`, `courbe`) et
`pre_entrainement/essai.py` (`essai-donnees`, `essai-reprise`), ainsi que
`appareil` (`pre_entrainement/appareil.py`), ne sont pas
montrées en code : le chapitre en montre les résultats, par les relevés
ci-dessous.

## Les mesures et les sorties

Chaque fichier porte sa date de relevé (champ `releve_le`, ou première ligne
`# relevé le AAAA-MM-JJ`). Le site les lit à la construction
(`site/src/lib/partie-1/journal.ts`) et les vérifie : un champ qui manque
arrête la construction.

| Fichier | D'où il vient | Relevé le |
| --- | --- | --- |
| `mesures/ton-ia-mini.json` | le journal de la version d'une heure de « ton IA » (le modèle « mini », entraîné le 03/11/2026), lu par `courbe` ; 6 370 pas, 60 min 17 s de calcul, sans pause | 09/11/2026 |
| `mesures/essai-processeur.json` | l'essai de pause et de reprise sur le processeur, écrit par `essai --json` | 09/11/2026 |
| `sorties/essai-processeur.txt` | la sortie du même essai, écrite par `essai --enregistrer` | 09/11/2026 |

L'essai a tourné sur le processeur de l'auteur (16 cœurs logiques). Sa durée
change d'une machine à l'autre ; ses pertes aussi, à la dernière décimale, selon
le nombre de fils du processeur. L'égalité des deux pertes, elle, ne change pas.

### Ce qui viendra de ton IA

Les relevés de la vraie « ton IA » (`mesures/ton-ia-1.5.json`, et l'essai sur la
carte graphique) seront versés après la fin de son entraînement, avant la
parution du chapitre ; jusque-là, rien n'en est inventé ici.

## Le notebook

`notebooks/1.5-pre-entrainement.ipynb` refait l'essai pas à pas : la perte d'un modèle neuf (ln V), le
planning du taux, 60 pas d'entraînement, la pause et la reprise (même perte), puis ce qu'il faut pour
la version d'une heure. Il se termine par un exercice : retrouver le pas de la pause dans un journal.
Il tourne sur la carte graphique si Colab en donne une, sinon sur le processeur, et dit sur quoi il a
tourné. Il n'installe que la petite bibliothèque `regex` (ni PyTorch, déjà là, ni forge, qui vient du
dépôt cloné). Le test `tests/test_notebook.py` l'exécute de bout en bout, sans carte.
