# L'évaluation

Évaluer une IA, c'est lui poser des questions dont on connaît la réponse, et compter. Ce projet refait,
pas à pas et à la main, les mesures que fait forge (le paquet `forge`, dans `projets/forge`), le moteur de
« ton IA », puis il en lit les résultats :

- il refait **la perte, la perplexité et les bits par octet**, comme forge les calcule sur des textes que le
  modèle n'a jamais lus ;
- il **note un QCM sans que le modèle écrive un mot** : il lui fait lire la question suivie de chaque réponse
  possible, et compte laquelle lui paraît la plus vraisemblable ;
- il refait **la marge et le verdict** : l'exactitude mesurée dépasse-t-elle le hasard de plus que la
  marge d'erreur ?
- il **résume le rapport d'évaluation** de la version d'une heure de « ton IA » (le modèle « mini »,
  `mesures/evaluation-mini.json`) ;
- il **note quelques questions de MMMLU**, un jeu de questions que le rapport de forge ne mesure pas
  (`mesures/qcm-mini.json`) ;
- il **regarde dans le modèle** : les cartes d'attention d'une phrase, et les jetons que le modèle juge les
  plus probables pour la suite.

C'est le projet du chapitre 1.6 de La Forge IA, « L'évaluation ». Comme les projets 0.3 à 0.5, 1.4 et 1.5, il
utilise PyTorch, en deux versions au choix : celle pour carte NVIDIA (extra `gpu`, CUDA 13.2) et celle pour le
processeur seul (extra `cpu`). Les commandes ci-dessous prennent le processeur, qui suffit à tout ce que ce
projet calcule.

Il dépend de forge par chemin (`forge-ia = { path = "../forge", editable = true }` dans `pyproject.toml`) : il
faut donc le dépôt entier, pas seulement ce dossier.

## Installer uv

`uv` installe Python et les bibliothèques de chaque projet. Le fichier `.python-version` demande Python 3.12 :
uv le télécharge lui-même s'il manque. Pour installer uv, voir le README du projet 0.3 (`projets/0.3-poste`),
ou <https://docs.astral.sh/uv/getting-started/installation/>.

## Lancer

Récupère le dépôt, puis va dans le dossier du projet. Les commandes sont les mêmes dans PowerShell (Windows)
et dans un terminal (Linux, Mac) :

```bash
git clone https://github.com/chipat-neko/forge-ia
cd forge-ia/projets/1.6-evaluation
```

Si tu as déjà récupéré le dépôt, mets-le à jour (`git -C forge-ia pull`) avant de revenir dans ce dossier.

```bash
uv run --extra cpu python -m evaluation_pas_a_pas resumer --rapport D:\forge-ia-donnees\entrainements\ton-ia-mini\evaluation\etape-0006370\rapport.json --json mesures/evaluation-mini.json
uv run --extra cpu python -m evaluation_pas_a_pas qcm-exemples --sauvegarde D:\forge-ia-donnees\entrainements\ton-ia-mini\sauvegardes\etape-0006370.pt --appareil cpu --json mesures/qcm-mini.json
uv run --extra cpu python -m evaluation_pas_a_pas cartes --sauvegarde <etape.pt> --phrase "Le forgeron dit qu'il frappe le fer" --couche 3 --tete 0 --appareil cpu --json cartes.json
uv run --extra cpu python -m evaluation_pas_a_pas suivants --sauvegarde <etape.pt> --phrase "Il était une fois" --appareil cpu --json suivants.json
```

- `resumer` lit le `rapport.json` que `python -m forge evaluer` écrit, et en tire le relevé que le site lit
  (voir « Les relevés »). Rien n'est recalculé. Les sauvegardes et les rapports de « mini » sont hors du dépôt
  (sous `FORGE_DONNEES`, `D:\forge-ia-donnees` sur le PC de l'auteur) : sans eux, les commandes ne se rejouent
  pas, mais les fichiers relevés sont dans le dépôt.
- `qcm-exemples` lit `--n` questions de MMMLU (6 par défaut, tirées avec `--graine`, 0 par défaut) **en flux**
  sur Hugging Face, sans les copier dans le dépôt, et les note avec le modèle de la sauvegarde. Il lui faut le
  réseau : si `HF_HUB_OFFLINE` vaut 1, la commande la lève pour son processus seulement, comme
  `python -m forge evaluer` pour FrenchBench.
- `cartes` écrit les poids d'attention d'une phrase pour une couche (`--couche`, à partir de 0) et une tête
  (`--tete`, à partir de 0). `suivants` écrit les `--k` jetons (10 par défaut) que le modèle juge les plus
  probables après la phrase.
- `--sauvegarde` est une sauvegarde de forge (`etape-*.pt`, `meilleur.pt`). `--tokenizer` donne un autre
  tokenizer que le tokenizer figé de « ton IA » (`forge/ressources/tokenizer-ton-ia-v1.json`).
- Sans `--appareil`, le projet prend la carte si PyTorch la voit, sinon le processeur (ou ce que dit la
  variable `FORGE_APPAREIL`). `--appareil cuda` sans carte dit quoi faire, sans trace Python, et rend le
  code 2 ; de même avec une carte que PyTorch voit sans savoir calculer dessus.

## Les mesures refaites à la main

Tout est dans `evaluation_pas_a_pas/pas_a_pas.py`, une région par étape du chapitre :

| Région | Fonction | Ce qu'elle fait |
| --- | --- | --- |
| `perte` | `perte_a_la_main(logits, cibles)` | la moyenne de `-ln(probabilité du vrai jeton suivant)`, sans `F.cross_entropy` : égale à celle de PyTorch à 10⁻¹² près en float64 |
| `perplexite` | `perplexite_a_la_main(perte)` | `exp(perte)` |
| `bits` | `bits_par_octet_a_la_main(perte, octets_par_jeton)` | `perte / ln 2 / octets_par_jeton` |
| `qcm` | `scores_a_la_main(modele, tokenizer, qcm)` | la log-vraisemblance de chaque choix, une séquence à la fois ; égale à `forge.evaluation.qcm.scores_qcm` à 10⁻⁵ près en relatif (forge arrondit les scores en float32) |
| `qcm` | `scores_par_octet(qcm, scores)`, `choix_prefere(scores)` | les scores divisés par les octets du choix, et le choix qui gagne |
| `marge` | `marge_95(exactitude, n)` | la marge de la mesure, `1,96 × √(p (1 − p) / n)` : la formule de forge, vérifiée par un test |
| `marge` | `marge_hasard(n, choix)` | la marge d'un tirage au sort sur `n` questions de `choix` choix |
| `marge` | `verdict(exactitude, hasard, marge)` | `"au-dessus"`, `"pas-different"` ou `"en-dessous"` |

`verdict` est la règle du rapport de forge (`forge.evaluation.rapport.verdict`) : l'exactitude
**normalisée** moins le hasard, comparée à la marge du **hasard** (`marge_hasard`), pas à celle de la mesure.
La marge de la mesure s'annule à 0 % ou 100 % de bonnes réponses : elle affirmerait « en dessous du hasard »
sur 0 bonne réponse sur 5, ce qui arrive une fois sur quatre au hasard avec quatre choix. Il n'y a qu'une seule
règle de jugement, et le site (`site/src/lib/partie-1/evaluation.ts`) la refait.

Les autres fichiers du paquet :

| Fichier | Région | Ce qu'il fait |
| --- | --- | --- |
| `sauvegarde.py` | `sauvegarde` | `charger_sauvegarde(chemin, appareil="cpu")` rend `(modele, config)` : il passe par `forge.entrainement.sauvegarde.charger` et reconstruit le modèle comme l'évaluation de forge |
| `resumer.py` | `resumer` | `resumer(rapport_json)` rend le relevé d'un rapport d'évaluation |
| `qcm_exemples.py` | `noter-exemples` | `exemples_mmmlu(n, graine)` lit des questions de MMMLU ; `noter_exemples(modele, tokenizer, qcms)` les note |
| `regarder.py` | `cartes`, `suivants` | `cartes_attention(modele, ids, couche)` et `suivants(modele, tokenizer, phrase, k)` |
| `attendus.py` | | écrit `tests/attendus.json`, la grille des marges et des verdicts que le site vérifie |

## Les relevés

- `mesures/evaluation-mini.json` : le rapport d'évaluation de la version d'une heure de « ton IA » (le
  modèle « mini », pas 6 370), écrit par `resumer`. Les chiffres sont ceux de `docs/mesures/ton-ia-mini.md` :
  perplexité 30,8, 1,133 bit par octet, HellaSwag 27,2 % (au-dessus du hasard), ARC 23,6 % (pas différent du
  hasard). Il a `nom`, `releve_le` (la date du rapport), `pas`, `perte_val`, `perplexite`, `bits_par_octet`,
  `qcm` et `echantillons` (les dix textes). Chaque test de `qcm` (`hellaswag`, `arc`) garde les clés du rapport
  de forge (`exactitude`, `exactitude_normalisee`, `hasard`, `n`, `marge_95`, `marge_95_normalisee`,
  `marge_hasard`, `total_du_test`) et reçoit son `verdict`.
- `mesures/qcm-mini.json` : six questions de MMMLU en français, notées par « mini » sur le processeur, écrit
  par `qcm-exemples`. Il a `nom`, `releve_le`, `appareil`, `jeu` (`nom`, `configuration`, `partie`,
  `adresse`, `licence`, `licence_verifiee_le`, `lu_le`), `n`, `justes`, `hasard`, et `questions` : pour
  chacune, `contexte`, `choix`, `scores` (les log-vraisemblances), `scores_normalises`, `prefere`, `bonne`
  et `juste`. Les lignes de MMMLU dont deux réponses sont identiques ou vides sont ignorées au tirage.

Le site lit ces fichiers à la construction (`site/src/lib/partie-1/evaluation.ts`) et les vérifie : un champ
qui manque arrête la construction.

### MMMLU

MMMLU (`openai/MMMLU`, configuration `FR_FR`, partie `test`) est MMLU traduit en français par des traducteurs
humains : des questions à quatre choix, sur 57 matières. Page du jeu : <https://huggingface.co/datasets/openai/MMMLU>.
Sa licence est **MIT**, lue sur cette page le 10/11/2026 et recopiée dans `mesures/qcm-mini.json`. Le jeu est
lu en flux : rien n'en est copié dans le dépôt, sauf les six questions du relevé. Le texte des questions garde
les espaces insécables du jeu.

Ces questions sont difficiles pour un modèle de 23 millions de paramètres : les noter montre comment un QCM
se lit, pas ce que « mini » sait. La mesure de référence de forge reste celle de FrenchBench
(HellaSwag et ARC, 9 338 et 1 169 questions), dans `mesures/evaluation-mini.json`.

## Les cartes d'attention du site

Le site ne montrera que des poids d'attention **calculés par forge sur le processeur**, pour **une phrase,
une couche et une tête**, écrits dans un fichier lu à la construction (voir la « Note pour le plan 5 : les
cartes de ton IA » dans `projets/mini-modele/README.md` : les cartes de ton IA ne se laissent pas refaire par
le composant d'animation du chapitre 1.4, à cause de RoPE et de la profondeur). Ce fichier, c'est la sortie de
`cartes --json` :

```json
{
 "nom": "ton-ia-mini",
 "releve_le": "2026-11-10",
 "appareil": "cpu",
 "phrase": "Le forgeron dit qu'il frappe le fer",
 "jetons": ["<|fin_texte|>", "Le", " forgeron", "…"],
 "couche": 3,
 "couches": 6,
 "tete": 0,
 "tetes": 6,
 "poids": [[1.0, 0.0, "…"], ["…"]]
}
```

- `jetons` : le texte de chaque jeton, **en commençant par `<|fin_texte|>`**, le « début de document » que le
  modèle a vu avant chaque texte pendant son entraînement ; `n` est leur nombre.
- `poids` : un tableau `n × n` de nombres entre 0 et 1, arrondis à 6 décimales. `poids[i][j]` est la part de
  l'attention que la position `i` donne à la position `j` ; elle vaut 0 pour `j > i` (le modèle ne regarde
  jamais en avant), et chaque ligne totalise 1 (à 10⁻⁴ près après l'arrondi).
- `couche` et `tete` commencent à 0 ; `couches` et `tetes` disent combien le modèle en a.
- `appareil` : le site n'accepte que `"cpu"` (les nombres de la carte graphique diffèrent un peu : un test
  marqué `gpu` les compare à ceux du processeur, à 10⁻⁵ près).

`cartes_attention` prend l'entrée normée de la couche par un crochet sur `norme_attention`, puis applique
`proj_qkv`, `rope_cos_sin`, `appliquer_rope`, la mise à l'échelle par √dim_tete et le masque, et la softmax :
le test `test_cartes_redonnent_la_sortie_de_l_attention` vérifie qu'en les multipliant par les valeurs v puis par
`proj_sortie`, on retrouve la sortie de l'attention de forge, en float64, à 10⁻¹² près.

`suivants --json` écrit `{nom, releve_le, appareil, phrase, suivants}`, où `suivants` est la liste ordonnée
des `{jeton, probabilite}`.

## Les copies

- `evaluation_pas_a_pas/appareil.py` est une copie, octet pour octet, de
  `projets/0.3-poste/poste/appareil.py` ;
- `carte_inutilisable`, dans `__main__.py`, est la copie, mot pour mot, de celle de
  `projets/0.5-reseau/premier_reseau/__main__.py` et de celle de `projets/1.5-pre-entrainement` (le message
  quand PyTorch voit la carte sans pouvoir calculer dessus).

Des tests le vérifient quand l'original est là (ils sont sautés sinon). Une correction se fait dans 0.3 ou 0.5,
puis se recopie ici.

## Tester

```bash
uv run --extra cpu pytest -q
```

Le test `test_cartes_redonnent_la_sortie_de_l_attention` est encadré par `# region: test-cartes` /
`# fin: test-cartes`, pour que le chapitre le montre. Les autres tests comparent chaque fonction à forge,
vérifient le résumé sur un rapport factice au format de forge (`VERSION_DU_RAPPORT = 1`), le tirage et la
notation des questions de MMMLU (sans réseau), les messages d'erreur en français, les copies exactes, les
régions du paquet, les relevés enregistrés, la grille `tests/attendus.json` et le notebook.

`tests/attendus.json` se régénère avec `uv run --extra cpu python -m evaluation_pas_a_pas.attendus`.

Le test marqué `gpu` (`test_cartes_sur_la_carte_egales_a_celles_du_processeur_a_1e_5`) refait les cartes sur la
carte graphique ; sans CUDA, il est sauté. Tous les autres tournent sur le processeur.

## Le notebook

`notebooks/1.6-evaluation.ipynb` refait l'évaluation pas à pas : la perte et la perplexité à la main, les bits
par octet, un QCM noté sans que le modèle écrive un mot, la marge et le verdict, puis la lecture d'échantillons.
Le modèle est celui de l'essai du chapitre 1.5, entraîné dans le notebook (60 pas, quelques secondes) : il est
donc très mauvais, et c'est ce qui rend les mesures instructives. Le notebook ajoute `projets/1.5-pre-entrainement`
à `sys.path` pour le fabriquer (`preparer_essai` et `essai_pause_reprise`). Il calcule toujours sur le processeur :
le modèle est minuscule, et le processeur donne partout les mêmes nombres. Il n'installe que la petite
bibliothèque `regex`. Le test `tests/test_notebook.py` l'exécute de bout en bout, sans carte.
