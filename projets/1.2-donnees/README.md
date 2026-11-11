# Les données pas à pas

Comment « ton IA » prépare ses textes, avec le vrai code de forge, le moteur de
« ton IA » : trier les documents d'une source (trop courts, doublons, code dont
la licence ne permet pas de le réutiliser), mettre de côté ceux de la
validation, et compter ce qui reste. Le projet n'écrit aucun nettoyage de son
cru : il appelle `forge.donnees` (`nettoyer`, `empreinte_du_texte_nettoye`,
`est_validation`, `SOURCES`), dans l'ordre où le téléchargement de forge les
appelle.

C'est le projet du chapitre 1.2 de La Forge IA, « Les données », en ligne à
l'adresse <https://chipat-neko.github.io/forge-ia/partie-1/1-2/> (les mots
techniques sont expliqués dans le glossaire,
<https://chipat-neko.github.io/forge-ia/annexes/glossaire/>, et les sources de
données dans l'annuaire, <https://chipat-neko.github.io/forge-ia/annexes/annuaire/>).
Le site en propose un jumeau en TypeScript pour le nettoyage et le tri
(`site/src/lib/partie-1/nettoyeur.ts`), qui doit donner exactement les mêmes
textes nettoyés, les mêmes empreintes et les mêmes verdicts.

Le projet dépend de forge (`../forge`), mais il n'installe pas PyTorch : c'est
un extra de forge, que ce projet ne demande pas. Aucun `--extra` n'est
nécessaire, ni pour lancer le projet ni pour le tester.

## Ce qu'il prend à forge

Tout le nettoyage, rien n'est réécrit. Le projet importe, de `forge.donnees` :

- `nettoyage` : `nettoyer` et `empreinte_du_texte_nettoye` (le nettoyage et
  l'empreinte SHA-1 d'un texte), plus `_normaliser` et `empreinte` pour les
  valeurs de référence du site ;
- `melange` : `est_validation` (le tri entre entraînement et validation) et
  `MELANGE_PAR_DEFAUT` (le mélange par défaut des sources) ;
- `sources` : `SOURCES` et `Source` (les trois sources de ton IA : le web
  français, Wikipédia en français et du code Python permissif) ;
- `telechargement` : `lecteur_hugging_face`, le lecteur en flux de l'aperçu.

Il prend aussi `forge.chemins.racine_donnees` (le dossier `FORGE_DONNEES`).
Ce que le projet ajoute lui-même est petit : `trier` (un verdict par document),
`apercu` (les comptes par source) et `volumes` (les volumes d'un corpus encodé).

## Lancer

Il faut `uv` : pour l'installer, voir le README du projet 0.1
(`projets/0.1-python`), ou
<https://docs.astral.sh/uv/getting-started/installation/>. Le projet demande
Python 3.12 ou plus récent : uv en télécharge un lui-même s'il n'en trouve
pas.

Récupère le dépôt avec git (si tu l'as déjà fait, `git -C forge-ia pull` le met
à jour), puis va dans le dossier du projet. Les commandes sont les mêmes dans
PowerShell (Windows) et dans un terminal (Linux, Mac) :

```bash
git clone https://github.com/chipat-neko/forge-ia
cd forge-ia/projets/1.2-donnees
uv run python -m donnees_pas_a_pas trier exemples/web.jsonl
```

Sans git, le bouton « Code » de la page GitHub du dépôt donne aussi un fichier
zip : son dossier s'appelle `forge-ia-main`, à écrire à la place de `forge-ia`
dans la commande `cd`.

La première ligne de chaque sortie est `# relevé le AAAA-MM-JJ`.

### `trier` : un verdict par ligne

```bash
uv run python -m donnees_pas_a_pas trier exemples/web.jsonl
uv run python -m donnees_pas_a_pas trier exemples/code.jsonl --source code_python
```

Chaque ligne du fichier `.jsonl` est un document : `{"text": …}` pour le web,
`{"code": …, "language": …, "license": …}` pour le code. Le verdict est l'un de
`gardé`, `trop court`, `doublon`, `licence` ou `langage`. Les exemples
(`exemples/`) sont une vingtaine de documents écrits à la main : un texte de 150
caractères, un texte de plus de 200, ce même texte avec des fins de ligne
Windows, une copie exacte, puis des caractères de contrôle, un accent écrit en
deux morceaux, un emoji, des moitiés de paires de substitution, des textes de 199
et 200 caractères. Dans `web.jsonl`, les moitiés de paires s'écrivent en
échappements (`\ud800`) : elles ne s'écriraient pas en UTF-8.

### `apercu` : lire les trois sources en flux

```bash
uv run python -m donnees_pas_a_pas apercu --octets 5M --enregistrer sorties/apercu.txt --json mesures/apercu.json
```

Il lit chaque source de `forge.donnees.sources` en flux sur Hugging Face, avec
le lecteur de forge, jusqu'à ce que `--octets` octets de texte aient été gardés
(un Mio vaut 1024² octets). Il compte, par source, les documents lus, gardés,
écartés (et pourquoi), les octets gardés et les documents mis de côté pour la
validation. Il ne garde que des comptes, jamais un texte. Il lui faut Internet,
et un peu de temps : le code Python permissif ne fait que 4 % des octets du
dépôt de code, il faut en lire beaucoup pour en garder 5 Mio. Hugging Face
écrit son cache dans `HF_HOME`. Si `HF_HUB_OFFLINE=1` est posé dans ta session,
la commande le lève pour elle seule, comme `python -m forge donnees`.

### `volumes` : les volumes d'un corpus déjà encodé

```bash
uv run python -m donnees_pas_a_pas volumes --donnees principal --json mesures/corpus-principal.json
```

Il lit `.complet` et `index.json` de `FORGE_DONNEES/jetons/principal/`, sans
ouvrir aucun fichier de jetons et sans rien écrire : les jetons d'entraînement et
de validation, les documents, les octets par jeton, et les fragments par source.
Il ne marche que sur ta machine, après `python -m forge encoder`.

## Tester

Dans le dossier du projet :

```bash
uv run pytest
```

Avec `-q`, pytest n'affiche qu'un point par test réussi et le bilan. Les tests
n'ont pas besoin du réseau : l'aperçu y est essayé avec un lecteur factice, et
`trier` est comparé à `forge.donnees.telechargement.telecharger` sur les
exemples.

## Ce que montre le chapitre

Le chapitre 1.2 montre, tirées des repères `# region: <nom>` et
`# fin: <nom>` ou des fonctions elles-mêmes (`symbole=`) :

| Fichier | Ce que le chapitre en montre |
| --- | --- |
| `donnees_pas_a_pas/trier.py` | la région `doublons` |
| `forge/donnees/nettoyage.py` (dans forge) | `_normaliser`, `nettoyer`, `empreinte_du_texte_nettoye` |
| `forge/donnees/sources.py` (dans forge) | `_garder_python_permissif` |
| `forge/donnees/melange.py` (dans forge) | `est_validation` |

Les autres régions de `trier.py` (`nettoyer`, `licence`, `validation`, `trier`
et `compter`) ne sont pas montrées par le chapitre : elles servent au notebook.

## Ce que contient le paquet

- `trier.py` : `Verdict`, `trier` (un verdict par document, dans l'ordre :
  licence et langage, longueur, doublon, puis gardé) et `compter_raisons`. Pour
  une source qui refuse une ligne, la raison est `langage` si `language` n'est
  pas `Python`, sinon `licence`. Un texte absent ou qui n'est pas du texte est
  `trop court`. Les doublons se reconnaissent aux 16 premiers chiffres de
  l'empreinte, comme dans le téléchargement de forge.
- `apercu.py` : la lecture en flux et les comptes.
- `volumes.py` : les volumes d'un dossier de jetons. Il relit `index.json` lui-même, car
  `forge.evaluation.perte` sait lire l'octet par jeton aussi, mais importe PyTorch.
- `attendus.py` : les valeurs de référence pour le site.

## Les attendus de référence

Le fichier `tests/attendus.json` contient les résultats du Python :

- `blancs_python` : les points de code où `chr(i).isspace()` est vrai, ce que
  `str.rstrip()` retire. Le jumeau ne peut pas s'en remettre à `trimEnd()` de
  JavaScript, qui retire aussi U+FEFF ;
- `textes` : pour chaque texte de référence (les exemples, puis des pièges :
  U+3000, U+2028, U+00A0 et U+FEFF en fin de texte, 199 et 200 caractères, cent
  mille `x`…), le texte nettoyé (ou `null`), la longueur en points de code,
  l'empreinte SHA-1 et la place (entraînement ou validation) ;
- `licences` : des lignes de code, et ce que le filtre en dit ;
- `tris` : les lignes des exemples et le verdict sur chacune.

Le jumeau est exact, sauf pour un cas : deux moitiés de paire de substitution collées, haute
puis basse. En JavaScript, elles forment une paire valide, donc un seul caractère (un emoji) que
le jumeau garde, alors que Python les retire. Aucun fichier JSON ne peut les produire : le
décodeur de `json` recolle `\ud83d\ude00` en un seul point de code, en Python comme en
JavaScript. Seule une chaîne fabriquée à la main dans un programme Python l'atteint. Les
moitiés seules sont retirées des deux côtés.

Un texte avec une moitié de paire de substitution s'écrit dans le fichier en liste
de points de code (`[97, 55357, 98]`), un très long texte d'un seul caractère en
`{"repete": "x", "fois": 100000}`. Le jumeau TypeScript doit tout retrouver à
l'identique. Pour régénérer le fichier :

```powershell
cd projets/1.2-donnees
uv run python -m donnees_pas_a_pas.attendus
```

## Les mesures et les sorties

Chacun de ces fichiers porte sa date de relevé (champ `releve_le`, ou première
ligne `# relevé le AAAA-MM-JJ`). Le chapitre les lit tels quels : rien n'est
recopié à la main.

| Fichier | D'où il vient | Relevé le |
| --- | --- | --- |
| `sorties/apercu.txt` | la sortie de `apercu --octets 5M --enregistrer`, lue en flux sur Hugging Face | 09/11/2026 |
| `mesures/apercu.json` | le même relevé, écrit par `apercu --json` | 09/11/2026 |
| `mesures/corpus-principal.json` | ce que `volumes --donnees principal` a lu dans `.complet` et `index.json` des jetons de « ton IA » (`FORGE_DONNEES/jetons/principal/`) | 09/11/2026 |

Les trois ont été relevés sur le PC de l'auteur : l'aperçu a besoin d'Internet,
et les volumes du corpus encodé de « ton IA », qui ne se trouve pas dans le dépôt.
Sans eux, les commandes ne se rejouent pas, mais les fichiers relevés sont dans
le dépôt.
