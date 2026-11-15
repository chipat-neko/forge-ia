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
  `mesures/evaluation-mini.json`) et celui de la version publiée, `ton-ia-1.5`
  (`mesures/evaluation-1.5.json`) ;
- il **note quelques questions de MMMLU**, un jeu de questions que le rapport de forge ne mesure pas
  (`mesures/qcm-mini.json`, `mesures/qcm-1.5.json`) ;
- il **regarde dans le modèle** : les cartes d'attention d'une phrase, et les jetons que le modèle juge les
  plus probables pour la suite (`sorties/cartes-ton-ia.json`, `sorties/ton-ia-suivants.json`).

C'est le projet du chapitre 1.6 de La Forge IA, « Évaluer son modèle ». Ce
chapitre n'est pas encore en ligne : il paraîtra après la fin de l'entraînement
de « ton IA », avec ses vrais chiffres, et son adresse (`partie-1/1-6/` sur le
site) n'existe pas encore. Les mots techniques sont expliqués dans le glossaire :
<https://chipat-neko.github.io/forge-ia/annexes/glossaire/>. Comme les projets 0.3 à 0.5, 1.4 et 1.5, il
utilise PyTorch, en deux versions au choix : celle pour carte NVIDIA (extra `gpu`, CUDA 13.2) et celle pour le
processeur seul (extra `cpu`). Les commandes ci-dessous prennent le processeur, qui suffit à tout ce que ce
projet calcule.

Il dépend de forge par chemin (`forge-ia = { path = "../forge", editable = true }` dans `pyproject.toml`) : il
faut donc le dépôt entier, pas seulement ce dossier.

## Ce qu'il prend à forge

Les mesures de forge, qu'il refait à la main puis compare, et la façon dont
forge charge un modèle :

- `forge.evaluation.qcm` : `QCM`, `JETON_DE_DEBUT` et `scores_qcm` (la notation
  d'un QCM par log-vraisemblance, à laquelle les scores refaits à la main sont
  comparés) ;
- `forge.evaluation.rapport` : `VERSION_DU_RAPPORT` (le format du
  `rapport.json` que `resumer` lit) ; la règle du verdict est celle de
  `forge.evaluation.rapport.verdict` ;
- `forge.entrainement.sauvegarde` : `charger` et `charger_derniere`, et
  `forge.entrainement.boucle.VERSION_DE_LA_SAUVEGARDE` (charger une sauvegarde
  `etape-*.pt` ou `meilleur.pt`) ;
- `forge.modele` : `ConfigModele`, `Transformer`, et, de
  `forge.modele.transformer`, `rope_cos_sin` et `appliquer_rope` (les cartes
  d'attention refont le calcul de l'attention de forge pour en montrer les
  poids) ;
- `forge.tokenizer.bpe_octets` : `TokenizerOctets`, qui charge le tokenizer figé
  de « ton IA » ;
- `forge.exporter` : les noms des fichiers publiés (`NOM_DES_POIDS`,
  `NOM_DE_LA_CONFIG`, `PLONGEMENT`, `SORTIE`), `empreinte_sha256` et
  `EMPREINTE_DU_TOKENIZER` (relire la version publiée de « ton IA » comme
  forge l'a écrite), et, par forge, `safetensors` (lire ses poids).

Ses tests importent aussi `forge.evaluation.perte` (`perplexite` et `bits_par_octet`, la
référence des mesures refaites à la main), `forge.evaluation.qcm` (`_marge_95` et
`_marge_hasard`) et `forge.evaluation.rapport.verdict`, `forge.exporter.exporter` (écrire un petit modèle au
format de la version publiée), et `import forge`.

Il ne modifie aucun fichier de forge. Il reprend aussi, par copie, le choix
de l'appareil du projet 0.3 (voir « Les copies »).

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

Pour la version publiée de « ton IA » (`ton-ia-1.5`), les commandes prennent `--modele` et le dossier de ses
fichiers, téléchargés une fois (avec l'outil `gh` de GitHub, ou à la main depuis la page des versions du dépôt) :

```bash
gh release download ton-ia-1.5 --dir D:\forge-ia-donnees\cache\ton-ia-1.5
uv run --extra cpu python -m evaluation_pas_a_pas resumer --rapport D:\forge-ia-donnees\cache\ton-ia-1.5\rapport.json --nom ton-ia-1.5 --json mesures/evaluation-1.5.json
uv run --extra cpu python -m evaluation_pas_a_pas qcm-exemples --modele D:\forge-ia-donnees\cache\ton-ia-1.5 --appareil cpu --json mesures/qcm-1.5.json
uv run --extra cpu python -m evaluation_pas_a_pas cartes --modele D:\forge-ia-donnees\cache\ton-ia-1.5 --phrase "Le forgeron chauffe le fer puis il le tord." --choisir --appareil cpu --json sorties/cartes-ton-ia.json
uv run --extra cpu python -m evaluation_pas_a_pas suivants --modele D:\forge-ia-donnees\cache\ton-ia-1.5 --phrase "Le forgeron frappe le" --appareil cpu --json sorties/ton-ia-suivants.json
```

- `resumer` lit le `rapport.json` que `python -m forge evaluer` écrit, et en tire le relevé que le site lit
  (voir « Les mesures et les sorties »). Rien n'est recalculé. Les sauvegardes et les rapports de « mini » sont hors du dépôt
  (sous `FORGE_DONNEES`, `D:\forge-ia-donnees` sur le PC de l'auteur) : sans eux, les commandes ne se rejouent
  pas, mais les fichiers relevés sont dans le dépôt.
- `qcm-exemples` lit `--n` questions de MMMLU (6 par défaut, tirées avec `--graine`, 0 par défaut) **en flux**
  sur Hugging Face, sans les copier dans le dépôt, et les note avec le modèle de la sauvegarde. Il lui faut le
  réseau : si `HF_HUB_OFFLINE` vaut 1, la commande la lève pour son processus seulement, comme
  `python -m forge evaluer` pour FrenchBench.
- `cartes` écrit les poids d'attention d'une phrase pour une couche (`--couche`, à partir de 0) et une tête
  (`--tete`, à partir de 0). `suivants` écrit les `--k` jetons (10 par défaut) que le modèle juge les plus
  probables après la phrase.
- Sous Linux ou Mac, les commandes ont la même forme, avec des `/` dans les
  chemins et les sauvegardes et rapports sous ton propre `FORGE_DONNEES`.
- `--sauvegarde` est une sauvegarde de forge (`etape-*.pt`, `meilleur.pt`). `--tokenizer` donne un autre
  tokenizer que le tokenizer figé de « ton IA » (`forge/ressources/tokenizer-ton-ia-v1.json`).
- `--modele` est le dossier des fichiers publiés de « ton IA » (`config.json`, `ton-ia-1.5.safetensors`,
  `tokenizer-ton-ia-v1.json`), lus par `charger_ton_ia` (voir plus bas) ; il prend la place de `--sauvegarde`,
  et son tokenizer celle de `--tokenizer`. Le relevé porte alors le nom `ton-ia-1.5`. `resumer` prend le
  `rapport.json` publié avec les poids, et `--nom ton-ia-1.5` : sans `--nom`, le relevé prendrait le nom du
  dossier de l'entraînement (`ton-ia`).
- `cartes --choisir` choisit lui-même la couche et deux têtes à montrer (voir « Les cartes d'attention du
  site ») ; il ne prend alors ni `--couche` ni `--tete`.
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
| `ton_ia.py` | | `charger_ton_ia(dossier, appareil="cpu")` rend `(modele, tokenizer)` : il lit les fichiers publiés de « ton IA » (`config.json`, les poids en bf16 sans `sortie.weight`, qu'il reprend de `plongement.weight`, et le tokenizer, refusé si son empreinte SHA-256 n'est pas celle du tokenizer figé), et passe les poids en float32 |
| `resumer.py` | `resumer` | `resumer(rapport_json)` rend le relevé d'un rapport d'évaluation |
| `qcm_exemples.py` | `noter-exemples` | `exemples_mmmlu(n, graine)` lit des questions de MMMLU ; `noter_exemples(modele, tokenizer, qcms)` les note |
| `regarder.py` | `cartes`, `suivants` | `cartes_attention(modele, ids, couche)` et `suivants(modele, tokenizer, phrase, k)` ; hors région, `regard_des_tetes(cartes)` et `choisir_couche_et_tetes(modele, ids)`, pour `cartes --choisir` |
| `attendus.py` | | écrit `tests/attendus.json`, la grille des marges et des verdicts que le site vérifie |

## Ce que montre le chapitre

Le chapitre 1.6 montre cinq régions de `evaluation_pas_a_pas/pas_a_pas.py`,
tirées des repères `# region: <nom>` et `# fin: <nom>` : `perte`, `perplexite`,
`bits`, `qcm` et `marge`. Les autres régions (`sauvegarde`, `resumer`,
`noter-exemples`, `cartes`, `suivants`, `appareil` et `test-cartes`) ne sont pas
montrées en code : le chapitre en montre les résultats, par les relevés
ci-dessous. `ton_ia.py` n'a pas de région.

## Les mesures et les sorties

Chaque fichier porte sa date (champ `releve_le`). Le site les lit à la
construction (`site/src/lib/partie-1/evaluation.ts`) et les vérifie : un champ
qui manque arrête la construction.

| Fichier | D'où il vient | Date du champ `releve_le` |
| --- | --- | --- |
| `mesures/evaluation-mini.json` | le rapport d'évaluation de la version d'une heure de « ton IA » (le modèle « mini », pas 6 370), écrit par `resumer` | 03/11/2026, la date du rapport de forge ; le fichier est entré dans le dépôt le 10/11/2026 |
| `mesures/qcm-mini.json` | six questions de MMMLU en français, notées par « mini » sur le processeur, écrit par `qcm-exemples` | 10/11/2026 |
| `mesures/evaluation-1.5.json` | le rapport d'évaluation de la version publiée de « ton IA » (`ton-ia-1.5`, pas 16 540, le `rapport.json` publié avec ses poids), écrit par `resumer --nom ton-ia-1.5` | 14/11/2026, la date du rapport de forge ; le fichier est entré dans le dépôt le 15/11/2026 |
| `mesures/qcm-1.5.json` | les six mêmes questions de MMMLU, notées par `ton-ia-1.5` sur le processeur, écrit par `qcm-exemples --modele` | 15/11/2026 |
| `sorties/cartes-ton-ia.json` | les cartes d'attention de `ton-ia-1.5` pour la phrase « Le forgeron chauffe le fer puis il le tord. », sur le processeur : la couche et les deux têtes choisies par `cartes --choisir`, et les chiffres du choix | 15/11/2026 |
| `sorties/ton-ia-suivants.json` | les dix jetons que `ton-ia-1.5` juge les plus probables après « Le forgeron frappe le », sur le processeur, écrit par `suivants --modele` | 15/11/2026 |

Les chiffres de `mesures/evaluation-mini.json` sont ceux de
`docs/mesures/ton-ia-mini.md` : perplexité 30,8, 1,133 bit par octet, HellaSwag
27,2 % d'exactitude normalisée (au-dessus du hasard), ARC 23,6 % d'exactitude normalisée
(pas différent du hasard). Le fichier a
`nom`, `releve_le`, `pas`, `perte_val`, `perplexite`, `bits_par_octet`, `qcm` et
`echantillons` (les dix textes). Chaque test de `qcm` (`hellaswag`, `arc`) garde
les clés du rapport de forge (`exactitude`, `exactitude_normalisee`, `hasard`,
`n`, `marge_95`, `marge_95_normalisee`, `marge_hasard`, `total_du_test`) et
reçoit son `verdict`.

`mesures/qcm-mini.json` a `nom`, `releve_le`, `appareil`, `jeu` (`nom`,
`configuration`, `partie`, `adresse`, `licence`, `licence_verifiee_le`, `lu_le`),
`n`, `justes`, `hasard`, et `questions` : pour chacune, `contexte`, `choix`,
`scores` (les log-vraisemblances), `scores_normalises`, `prefere`, `bonne` et
`juste`. Les lignes de MMMLU dont deux réponses sont identiques ou vides sont
ignorées au tirage.

Les chiffres de `mesures/evaluation-1.5.json` sont ceux de
`docs/mesures/ton-ia-1.5.md` : perplexité 11,2, 0,802 bit par octet, HellaSwag
34,8 % d'exactitude normalisée (au-dessus du hasard), ARC 25,1 % d'exactitude
normalisée (pas différent du hasard). `mesures/qcm-1.5.json` note les six
questions de `mesures/qcm-mini.json`, tirées de la même façon (graine 0).

Les sauvegardes et les rapports de « mini » ne sont pas dans le dépôt : les
relevés ont été faits sur le PC de l'auteur. Les fichiers de `ton-ia-1.5`
(poids, configuration, tokenizer, rapport) sont publiés sur la page des
versions du dépôt : <https://github.com/chipat-neko/forge-ia/releases/tag/ton-ia-1.5>.

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

Avec `--choisir` (c'est ainsi que `sorties/cartes-ton-ia.json` a été écrit), la commande choisit la couche et
deux de ses têtes, et le fichier a `{nom, releve_le, appareil, phrase, jetons, couche, couches, tetes, cartes,
choix}` :

- le regard d'une tête se mesure par trois nombres (`regard_des_tetes`), en moyenne sur les jetons qui ont un
  jeton de la phrase juste avant eux (du deuxième jeton de la phrase au dernier) : `jeton_d_avant`, la part
  de l'attention donnée au jeton juste avant ; `distance`, combien de jetons en arrière la tête regarde, sur
  les mots de la phrase (la somme des `poids[i][j] × (i − j)` pour j ≥ 1) ; `debut`, la part posée sur
  `<|fin_texte|>`. Le jeton de
  début ne compte pas dans la distance : beaucoup de têtes y reposent quand rien ne les intéresse, et il
  ferait passer leur regard pour lointain ;
- `couche` est celle de la tête qui regarde le plus le jeton d'avant, dans tout le modèle ;
- `cartes` a deux entrées, `{tete, role, jeton_d_avant, distance, debut, poids}` : la tête `jeton-d-avant`
  (le plus grand `jeton_d_avant` de la couche), puis la tête `loin` (la plus grande `distance` des autres
  têtes de la couche) ; `poids` est leur tableau `n × n`, comme plus haut ;
- `choix` justifie ce choix par les chiffres : `jeton_d_avant_par_couche` donne, pour chaque couche, sa
  tête qui regarde le plus le jeton d'avant et sa part ; `regards_de_la_couche`, le regard de chaque tête de
  la couche choisie.

Les nombres sont arrondis à 6 décimales. Pour la phrase de `sorties/cartes-ton-ia.json`, découpée par le
tokenizer de « ton IA », c'est la couche 12 : sa tête 10 regarde le jeton d'avant, et sa tête 4 regarde le
plus loin.

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
`# fin: test-cartes` (le chapitre ne le montre pas encore). Les autres tests comparent chaque fonction à forge,
vérifient le résumé sur un rapport factice au format de forge (`VERSION_DU_RAPPORT = 1`), le tirage et la
notation des questions de MMMLU (sans réseau), les messages d'erreur en français, les copies exactes, les
régions du paquet, les relevés enregistrés, la grille `tests/attendus.json` et le notebook.

`tests/attendus.json` se régénère avec `uv run --extra cpu python -m evaluation_pas_a_pas.attendus`.

`tests/test_ton_ia.py` exporte le petit modèle des tests avec `forge.exporter.exporter`, la fonction qui a écrit
les fichiers publiés, puis vérifie que `charger_ton_ia` redonne ses logits au bit près, et qu'il refuse un
fichier manquant, abîmé, ou un tokenizer modifié. D'autres tests relisent les relevés de `ton-ia-1.5`
(`mesures/`, `sorties/`) et refont le choix des têtes sur les chiffres du fichier.

Les tests marqués `gpu` (`test_cartes_sur_la_carte_egales_a_celles_du_processeur_a_1e_5`, et
`test_charger_ton_ia_sur_la_carte`) refont les cartes et le chargement sur la carte graphique ; sans CUDA, ils
sont sautés. Tous les autres tournent sur le processeur.

## Le notebook

`notebooks/1.6-evaluation.ipynb` refait l'évaluation pas à pas : la perte et la perplexité à la main, les bits
par octet, un QCM noté sans que le modèle écrive un mot, la marge et le verdict, puis la lecture d'échantillons.
Le modèle est celui de l'essai du chapitre 1.5, entraîné dans le notebook (60 pas, quelques secondes) : il est
donc très mauvais, et c'est ce qui rend les mesures instructives. Le notebook ajoute `projets/1.5-pre-entrainement`
à `sys.path` pour le fabriquer (`preparer_essai` et `essai_pause_reprise`). Il calcule toujours sur le processeur :
le modèle est minuscule, et le processeur donne partout les mêmes nombres. Il n'installe que la petite
bibliothèque `regex`. Le test `tests/test_notebook.py` l'exécute de bout en bout, sans carte.
