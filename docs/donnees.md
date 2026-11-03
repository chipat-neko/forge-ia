# Les données de « ton IA »

« ton IA » lit et écrit le français et le code. Elle apprend sur trois sources
publiques, lues en flux depuis Hugging Face (jamais téléchargées en entier), nettoyées,
dédoublonnées, puis rangées hors du dépôt. Le code qui fait tout cela est dans
`projets/forge/forge/donnees/`.

Les données ne sont jamais copiées dans ce dépôt ; seuls les modèles entraînés sont publiés.

## Le mélange

| Source | Nom dans le code | Part |
| --- | --- | --- |
| Français du web | `web_fr` | 75 % |
| Wikipédia en français | `wikipedia_fr` | 10 % |
| Code Python sous licence permissive | `code_python` | 15 % |

Les parts sont définies une seule fois, dans `forge.donnees.melange.MELANGE_PAR_DEFAUT`.
Le téléchargement et l'apprentissage du tokenizer les lisent là ; l'encodage
(`python -m forge encoder`) les lit aussi, pour savoir quelles sources encoder.

## Français du web (`web_fr`)

- **Dépôt :** [HuggingFaceFW/fineweb-2](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2),
  dossier `data/fra_Latn/train` (135 fichiers parquet, environ 4,85 Go en tout, sans
  formulaire d'accès).
- **Licence :** [ODC-By 1.0](https://opendatacommons.org/licenses/by/1-0/) (Open Data Commons
  Attribution). Les pages viennent de Common Crawl, dont les
  [conditions d'utilisation](https://commoncrawl.org/terms-of-use) s'appliquent aussi.
- **Ce qui est gardé :** la colonne `text` de toutes les pages du dossier. Les autres colonnes
  (adresse, date, score de langue…) ne sont pas conservées.

## Wikipédia en français (`wikipedia_fr`)

- **Dépôt :** [wikimedia/wikipedia](https://huggingface.co/datasets/wikimedia/wikipedia),
  configuration `20231101.fr` (17 fichiers, environ 4,61 Go, sans formulaire d'accès).
- **Licence :** [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/deed.fr) (le jeu
  est aussi publié sous GFDL).
- **Ce qui est gardé :** la colonne `text` de tous les articles (le texte seul, sans le titre
  ni l'adresse).

## Code Python (`code_python`)

- **Dépôt :** [codeparrot/github-code-clean](https://huggingface.co/datasets/codeparrot/github-code-clean)
  (880 fichiers parquet, environ 314 Go en tout, sans formulaire d'accès). On lit ses fichiers
  parquet directement, car son script de chargement n'est plus accepté par les versions
  récentes de `datasets`.
- **Licence :** la compilation est sous [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0),
  mais chaque fichier garde la licence de son dépôt d'origine (colonne `license`). On ne garde
  que les fichiers sous une de ces sept licences permissives :
  [MIT](https://spdx.org/licenses/MIT.html),
  [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html),
  [BSD-2-Clause](https://spdx.org/licenses/BSD-2-Clause.html),
  [BSD-3-Clause](https://spdx.org/licenses/BSD-3-Clause.html),
  [ISC](https://spdx.org/licenses/ISC.html),
  [Unlicense](https://spdx.org/licenses/Unlicense.html) et
  [CC0-1.0](https://spdx.org/licenses/CC0-1.0.html).
- **Ce qui est gardé :** la colonne `code` des fichiers dont le langage (`language`) est
  `Python` et dont la licence est dans la liste ci-dessus. Le dépôt d'origine et le chemin du
  fichier ne sont pas conservés dans nos fragments ; on les retrouve dans la source.
- **Combien il faut lire :** le Python permissif ne fait que 4,1 % des fichiers et 3,9 % des
  octets de code (mesuré le 03/11/2026 sur 7 fichiers parquet répartis dans tout le jeu).
  Garder 1 Mo de code demande donc de lire environ 26 Mo de code, soit environ 9 Mo de parquet
  compressé. Les fichiers Python sont répartis partout, dans chaque groupe de lignes de chaque
  fichier parquet : aucun fichier ni groupe de lignes ne peut être sauté, et la colonne `code`
  fait 98 % du poids (garder seulement quelques colonnes n'économise presque rien).

## Ce que fait le téléchargement

- **Nettoyage :** forme Unicode NFC, fins de ligne `\n`, caractères de contrôle retirés (sauf
  `\n` et `\t`), espaces de fin de texte retirées. Un texte de moins de 200 caractères une fois
  nettoyé est écarté.
- **Doublons :** l'empreinte SHA-1 du texte nettoyé sert à ne jamais écrire deux fois le même
  texte, y compris après une reprise.
- **Fragments :** des fichiers `fragment-00000.jsonl.gz` d'environ 100 Mo de texte, une ligne
  `{"texte": …}` par document. Chaque fichier est écrit sous un nom `.tmp`, puis renommé d'un
  coup. L'état (`etat.json`) n'est mis à jour qu'après le fragment qu'il compte.
- **Reprise :** après une coupure (réseau, courant, disque plein), on relance la même commande.
  Les documents déjà comptés sont sautés et rien n'est écrit deux fois ; seul le fragment en cours
  (jusqu'à 100 Mo) est relu. Le marqueur `.complet` n'est posé qu'à la fin ; sans lui, une source
  n'est jamais tenue pour terminée.
- **Place :** avant chaque fragment, on vérifie qu'il reste de la place pour lui et 2 Go de
  marge. Sinon, la commande s'arrête avec un message qui dit combien de Go libérer.
- **Où :** `FORGE_DONNEES/textes/<dossier>/<source>/` (par défaut `D:\forge-ia-donnees` sur
  ce PC), un sous-dossier par source.
- **Validation :** le téléchargement ne met rien de côté : la séparation entre entraînement et
  validation se fait à l'encodage (voir plus bas), avec `est_validation`, qui met de côté 0,5 % des
  documents d'après les 8 premiers chiffres de leur empreinte (le même document tombe toujours du
  même côté).

```powershell
. .\outils\env-forge.ps1
cd projets/forge
uv run --extra gpu python -m forge donnees --octets 300M --dossier echantillon
```

La commande lève `HF_HUB_OFFLINE=1`, s'il est posé dans la session, pour ce téléchargement
seulement : elle a besoin du réseau.

## Ce que fait l'encodage

L'encodage lit les fragments de texte et les écrit en jetons, avec le tokenizer de ton IA. Il
travaille hors du dépôt, sous `FORGE_DONNEES/jetons/<dossier>/`.

- **Fichiers :** `train/fragment-00000.bin` et `val/fragment-00000.bin`, en `uint16`
  (petit-boutiste), lisibles avec `forge.donnees.jetons.lire_jetons`. Chaque document est suivi
  du jeton `<|fin_texte|>`. Un document va dans `val/` quand `est_validation` le dit (0,5 % des
  documents) ; un fichier qui n'aurait aucun jeton n'est pas écrit.
- **Numéros :** le fragment de sortie `k` vient du `k`-ième fragment d'entrée, quand on range les
  sources par nom, puis les fragments par nom. `index.json` donne le nombre de jetons de chaque
  fichier et d'où il vient.
- **Parallélisme :** un fragment à la fois par processus, tous les cœurs par défaut
  (`--processus N` pour en changer). Le résultat est le même quel que soit le nombre de processus.
- **Reprise :** chaque fragment encodé a son marqueur `fragment-00000.fait`, posé après ses
  fichiers de jetons. Après une coupure, on relance la même commande : les fragments dont le
  marqueur correspond encore au fragment de texte et au tokenizer sont sautés, les autres sont
  refaits. `.complet` n'est posé qu'à la fin.
- **Place :** avant chaque fichier, on vérifie qu'il reste de la place pour lui et 2 Go de marge.
- **Refus :** une source sans `.complet` n'est jamais encodée, et un dossier de sortie déjà
  rempli avec un autre tokenizer n'est jamais réécrit sans que tu le décides (supprime-le, ou
  choisis-en un autre).

```powershell
uv run --extra gpu python -m forge encoder --donnees echantillon --tokenizer forge/ressources/tokenizer-ton-ia-v1.json
```
