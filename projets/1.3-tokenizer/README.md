# Tokenizer pédagogique (BPE)

Un tokenizer minuscule, écrit pour comprendre comment une intelligence
artificielle découpe un texte en morceaux (des « jetons »). Il apprend sur un
petit corpus français (`donnees/corpus.txt`) et repose sur l'algorithme BPE
(Byte Pair Encoding, « codage par paires d'octets ») : on part des lettres,
puis on colle à chaque tour la paire de symboles voisins la plus fréquente.

C'est le projet du chapitre 1.3 de La Forge IA, « Le tokenizer », en ligne à
l'adresse <https://chipat-neko.github.io/forge-ia/partie-1/1-3/> (les mots
techniques sont expliqués dans le glossaire :
<https://chipat-neko.github.io/forge-ia/annexes/glossaire/>). Le site en
propose un jumeau en TypeScript qui doit donner exactement les mêmes résultats.

## Ce qu'il prend à forge

Rien. Ce projet n'importe pas `forge`, le moteur de « ton IA »
(`projets/forge`) : le tokenizer de ton IA, appris par forge, est un autre
programme (un BPE sur les octets, bien plus gros). Celui-ci est écrit pour être
lu : sa seule dépendance est la bibliothèque `regex`, qui comprend `\p{L}`
(« une lettre ») là où `re` de Python ne le comprend pas.

## Lancer

Il faut `uv` et Python 3.12 ou plus. Dans PowerShell :

```powershell
cd projets/1.3-tokenizer
uv run python -m tokenizer_pedagogique "Les forgerons" --fusions 30
```

Le programme affiche les jetons séparés par `|` (une espace est affichée
`␣`, un retour à la ligne `↵`), puis leurs numéros. Un numéro `?` veut dire
que le caractère n'existe pas dans le corpus.

## Tester

```powershell
cd projets/1.3-tokenizer
uv run pytest -q
```

## Les règles à connaître

- Le texte est d'abord découpé en mots (`pre_decouper`). Un mot garde
  l'espace qui le précède, comme dans GPT.
- À chaque tour, on choisit la paire la plus fréquente. En cas d'égalité, on
  prend la plus petite paire dans l'ordre des points de code. On s'arrête
  quand aucune paire n'apparaît au moins 2 fois.
- Numéros des jetons : un caractère du corpus a pour numéro sa place dans la
  liste triée `base`. Le symbole créé par la fusion numéro `j` a pour numéro
  `len(base) + j`. Un caractère inconnu n'a pas de numéro (`None`).

## Les attendus de référence

Le fichier `tests/attendus.json` contient les fusions apprises et le
découpage de plusieurs textes avec plusieurs nombres de fusions. Le jumeau
TypeScript doit retrouver ces valeurs à l'identique. Pour le régénérer :

```powershell
cd projets/1.3-tokenizer
uv run python -m tokenizer_pedagogique.attendus
```

Un test vérifie que le fichier est à jour : si le code change, il échoue
tant que le fichier n'est pas régénéré.

## Ce que montre le chapitre

Le chapitre 1.3 montre deux régions de `tokenizer_pedagogique/bpe.py`, tirées
des repères `# region: <nom>` et `# fin: <nom>` : `compter` (compter les paires
de symboles voisins) et `choisir` (choisir la paire à fusionner, avec la règle
d'égalité ci-dessus).

## Les mesures et les sorties

Ce projet n'a ni dossier `mesures/` ni dossier `sorties/` : aucun relevé n'est
fait à une date donnée. Le corpus d'apprentissage est `donnees/corpus.txt`, et
les nombres du chapitre viennent de `tests/attendus.json`, que le Python écrit.
