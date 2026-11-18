# La conversation

Un modèle de langage ne sait que prolonger un texte. Pour qu'il réponde, on l'affine sur des conversations,
écrites dans un format fixe, et on ne lui fait apprendre que ce que dit l'assistant. Ce projet refait, pas à pas
et à la main, la pièce que le chapitre 1.7 explique, puis la compare à forge (le paquet `forge`, dans
`projets/forge`), le moteur de « ton IA » :

- il **écrit une conversation en jetons** : `<|fin_texte|>`, puis chaque tour entre son jeton de rôle
  (`<|systeme|>`, `<|utilisateur|>`, `<|assistant|>`) et `<|fin_tour|>`, avec, pour chaque jeton, un booléen
  « appris » : le **masque de perte** ;
- il refait **la perte masquée** : la moyenne des pertes des seules cibles apprises, égale à celle de l'affinage
  de forge (`pas_sft`) ;
- il **range plusieurs conversations dans une rangée** (l'empaquetage BFD de forge) et mesure **la fuite** quand on
  oublie le masque par document : la deuxième conversation d'une rangée voit alors la première ;
- il fait **un tout petit affinage** : un modèle minuscule, pré-entraîné 40 pas, puis affiné 80 pas sur 24
  conversations par `forge entrainer` (méthode `sft`), apprend à finir son tour de parole ;
- il **résume** ce que le plan 7 mesure sur ton IA (le rapport d'étape de `forge evaluer-etape`, les longueurs
  des exemples du jeu d'affinage) en fichiers que le chapitre lit.

C'est le projet du chapitre 1.7 de La Forge IA, « Apprendre à converser », en ligne à l'adresse
<https://chipat-neko.github.io/forge-ia/partie-1/1-7/>. Les mots techniques sont expliqués dans le glossaire :
<https://chipat-neko.github.io/forge-ia/annexes/glossaire/>. Comme les projets 0.3 à 0.5, 1.4, 1.5 et 1.6, il utilise
PyTorch, en deux versions au choix : celle pour carte NVIDIA (extra `gpu`, CUDA 13.2) et celle pour le processeur
seul (extra `cpu`). Les commandes ci-dessous prennent le processeur, qui suffit à tout ce que ce projet calcule : le
petit affinage dure quelques minutes.

Il dépend de forge par chemin (`forge-ia = { path = "../forge", editable = true }` dans `pyproject.toml`) : il faut
donc le dépôt entier, pas seulement ce dossier. Il ne modifie aucun fichier de forge.

## Ce qu'il prend à forge

- `forge.conversation.format` : `Tour`, `ExempleMasque` et `encoder_conversation` (le gabarit et le masque, que
  `montrer` détaille jeton par jeton) ;
- `forge.affinage.empaquetage` : `empaqueter` (l'empaquetage BFD) ; `forge.affinage.jeu` : `ecrire_jeu`,
  `ChargeurAffinage`, `IGNORE` (le jeu d'affinage sur disque et ses lots, la cible `-100`) ;
- `forge.modele` : `Transformer`, `ConfigModele`, `nombre_parametres` (et son argument `documents`, le masque par
  document de la fuite) ;
- `forge.entrainement` : `entrainer` et `ConfigEntrainement` (la même boucle que `python -m forge entrainer`),
  `forge.entrainement.methodes.pas_sft` (la référence de la perte masquée, dans les tests) ;
- `forge.exporter` : `exporter` (publier le départ de l'essai comme une vraie version) ;
  `forge.publication` : `charger_publication`, `nom_des_poids` ;
- `forge.evaluation.reponses` : `repondre_lot` (faire répondre le modèle) ; `forge.evaluation.etape` :
  `VERSION_DU_RAPPORT_D_ETAPE` (le format du `rapport.json` que `resumer` lit) ;
- `forge.tokenizer` : `TokenizerOctets` et `SPECIAUX` (le tokenizer figé de « ton IA » et ses 64 jetons spéciaux).

Il reprend aussi, par copie, le choix de l'appareil du projet 0.3 (`conversation_pas_a_pas/appareil.py`).

## Installer uv

`uv` installe Python et les bibliothèques de chaque projet. Le fichier `.python-version` demande Python 3.12 : uv le
télécharge lui-même s'il manque. Pour installer uv, voir le README du projet 0.3 (`projets/0.3-poste`), ou
<https://docs.astral.sh/uv/getting-started/installation/>.

## Lancer

Récupère le dépôt, puis va dans le dossier du projet. Les commandes sont les mêmes dans PowerShell (Windows) et dans
un terminal (Linux, Mac) :

```bash
git clone https://github.com/chipat-neko/forge-ia
cd forge-ia/projets/1.7-conversation
```

```bash
uv run --extra cpu python -m conversation_pas_a_pas montrer "Quelle est la capitale de la France ?" --reponse "Paris."
uv run --extra cpu python -m conversation_pas_a_pas fuite --enregistrer sorties/fuite.txt --json mesures/fuite.json
uv run --extra cpu python -m conversation_pas_a_pas essai --appareil cpu --enregistrer sorties/essai-processeur.txt --json mesures/essai-processeur.json
```

- `montrer` écrit la conversation jeton par jeton : l'identifiant, le texte (`␊` pour un saut de ligne, le nom pour
  un jeton spécial), le rôle de celui qui parle, et une étoile pour les jetons appris. `--systeme` ajoute un message
  système, `--reponse` donne la réponse de l'assistant.
- `fuite` tire un modèle minuscule (2 couches, des vecteurs de 32 nombres, des poids tirés au hasard) et lit deux conversations, A puis B, dans une même rangée. Il écrit l'écart maximal entre les logits
  de B dans la rangée et ceux de B lue seule, avec le masque par document (de l'ordre de 10⁻⁷ : l'arrondi des
  nombres) et sans (plus de 10⁻³ : B a regardé A). Le code de sortie est 1 si l'une des deux attentes n'est pas
  tenue.
- `essai` pré-entraîne un modèle minuscule (dim 64, 2 couches, 4 têtes, contexte 128) 40 pas sur
  `texte-du-site.txt` (du projet 1.1), le publie avec `forge.exporter`, puis l'affine 80 pas, par
  `forge.entrainement.entrainer` (méthode `sft`), sur 24 conversations écrites dans `petit_affinage.py`. Il fait
  répondre le modèle à huit questions qu'il n'a jamais vues, avant et après, et compte les réponses qui finissent
  par `<|fin_tour|>`. Rien n'est écrit ailleurs que dans un dossier temporaire. `--pas` change le nombre de pas
  d'affinage. Sans carte graphique, `--appareil cuda` dit quoi faire, sans trace Python, et rend le code 2.

## Ce que ton IA 1.7 ajoute

Ces trois commandes lisent ce que le plan 7 a mesuré sur ton IA, sans rien recalculer et sans rien écrire dans les
données de l'auteur (ce sont des fichiers qu'on lit) :

```bash
uv run --extra cpu python -m conversation_pas_a_pas resumer --rapport <rapport.json> --json mesures/etape-ton-ia-1.7.json
uv run --extra cpu python -m conversation_pas_a_pas resumer --rapport <rapport.json> --reference --json mesures/etape-ton-ia-1.5.json
uv run --extra cpu python -m conversation_pas_a_pas longueurs --jeu <FORGE_DONNEES>/affinage/sft-1.7 --json mesures/longueurs-sft-1.7.json
```

- `resumer` lit le `rapport.json` de `python -m forge evaluer-etape --etape 1.7` et en tire
  `{version, etape, releve_le, mesures, echantillons}` : les mesures du rapport (`perte_conversation`, `ifeval_fr`,
  `tenue`, `oubli`), telles quelles, une mesure dont les données manquaient restant `{"absente": "<raison>"}`, et les
  dix échantillons, tels quels, sans choisir les meilleurs. Avec `--reference`, c'est `ton-ia-1.5`, qui passe les mêmes
  mesures dans le même rapport, qui est résumée.
- `longueurs` lit `train/documents.bin` du jeu (en lecture seule) : la longueur de chaque exemple, rangée en histogramme
  `[longueur, nombre d'exemples]`. Deux exemples de même longueur se rangent de la même façon : l'histogramme suffit
  à refaire l'empaquetage à n'importe quelle longueur de rangée.
- La courbe d'entraînement et ses sessions passent par le projet 1.5 :
  `uv run --extra cpu python -m pre_entrainement courbe --journal <journal.jsonl> --config <sft-1.7.toml> --json mesures/entrainement-sft-1.7.json`
  (dans `projets/1.5-pre-entrainement`).

## La perte masquée à la main

Les régions de `conversation_pas_a_pas`, tirées des repères `# region: <nom>` et `# fin: <nom>` :

| Fichier | Région | Ce qu'il fait |
| --- | --- | --- |
| `gabarit.py` | `gabarit` | `montrer(tok, tours)` rend, par jeton, `id`, `texte` (visible), `role` et `appris`, depuis `encoder_conversation` |
| `gabarit.py` | `masque` | `perte_masquee_a_la_main(logits, cibles)` : la somme des pertes des cibles différentes de -100, divisée par leur nombre, en float64 ; égale à celle de PyTorch à 10⁻¹² près, et à celle de `pas_sft` au float32 près (un test) |
| `fuite.py` | `fuite` | `ecarts_de_fuite(graine)` : l'écart des logits de B, dans la rangée « A puis B », face à B seule, avec et sans `documents` |
| `petit_affinage.py` | `essai-conversations`, `essai-donnees`, `essai` | les 24 conversations, la préparation des données, `essai_affinage(appareil, pas)` |
| `resumer.py` | `resumer`, `longueurs` | `resumer_etape(rapport, reference)` et `longueurs(jeu)` |
| `attendus.py` | | écrit `tests/attendus.json`, que les jumeaux TypeScript du site vérifient |

La région `test-perte` est dans `tests/test_gabarit.py` : le test qui compare la perte à la main à celle de forge.

## Les jumeaux TypeScript

Le site refait deux calculs en TypeScript, avec les mêmes fonctions et le même ordre d'opérations, et les compare au
fichier `tests/attendus.json` (écrit par `python -m conversation_pas_a_pas.attendus`) sans tolérance, dans Node
(Vitest) puis dans Chrome, Firefox et WebKit (la page d'essai de parité, `e2e/parite.spec.ts`) :

- `site/src/lib/partie-1/conversation.ts` : `assemblerConversation`, la traduction exacte d'`encoder_conversation` une
  fois les textes encodés, et `SPECIAUX_TON_IA`, les 64 jetons spéciaux avec leurs identifiants. Seul écart : le
  Python refuse un texte vide ou fait de blancs, le jumeau, qui ne voit que des identifiants, refuse un texte sans
  aucun jeton ;
- `site/src/lib/partie-1/bfd.ts` : `empaqueterLongueurs`, la traduction exacte du placement d'`empaqueter` (les mêmes
  égalités, le même ordre).

`tests/attendus.json` a trois sections : `speciaux` (les 64 jetons spéciaux), `conversations` (six conversations de
référence : avec système, sans, deux tours, un texte qui imite un jeton spécial, une pensée, une réponse vide
refusée) et `empaquetages` (cinq listes de longueurs, quatre capacités de rangée). La cinquième liste est un
échantillon de `mesures/longueurs-sft-1.7.json` quand ce fichier existe ; relance alors
`uv run --extra cpu python -m conversation_pas_a_pas.attendus`.

## Les mesures et les sorties

Chaque fichier porte sa date (champ `releve_le`, ou première ligne `# relevé le AAAA-MM-JJ` d'un fichier de sortie).
Le site les lit à la construction.

| Fichier | D'où il vient |
| --- | --- |
| `sorties/fuite.txt`, `mesures/fuite.json` | `fuite`, sur le processeur : la fuite de B vers A, avec et sans masque |
| `sorties/essai-processeur.txt`, `mesures/essai-processeur.json` | `essai --appareil cpu` : le tout petit affinage, ses pertes et la part des réponses qui finissent leur tour |
| `mesures/etape-ton-ia-1.7.json`, `mesures/etape-ton-ia-1.5.json` | `resumer` sur le rapport de `forge evaluer-etape --etape 1.7` : ton IA 1.7, et ton IA 1.5 sur les mêmes mesures (à relever quand ton-ia-1.7 est publiée) |
| `mesures/longueurs-sft-1.7.json` | `longueurs` sur le jeu d'affinage `sft-1.7` (à relever avec l'étape précédente) |
| `mesures/entrainement-sft-1.7.json` | `pre_entrainement courbe` sur le journal de l'affinage (à relever de même) |

Tant qu'un des trois derniers fichiers n'existe pas, le chapitre affiche « à mesurer » à sa place.

## Tester

```bash
uv run --extra cpu pytest -q
```

Les tests importent aussi `forge.affinage` (`ChargeurAffinage`, `ecrire_jeu`, `empaqueter`),
`forge.entrainement.methodes.pas_sft`, `forge.exporter.exporter` et `forge.publication` (publier un petit modèle comme
une version de ton IA, et le charger). `test_notebook.py` exécute le notebook du chapitre
(`notebooks/1.7-conversation.ipynb`) de bout en bout, sur le processeur.
