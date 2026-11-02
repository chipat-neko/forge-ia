# Tokenizer pédagogique (BPE)

Un tokenizer minuscule, écrit pour comprendre comment une intelligence
artificielle découpe un texte en morceaux (des « jetons »). Il apprend sur un
petit corpus français (`donnees/corpus.txt`) et repose sur l'algorithme BPE
(Byte Pair Encoding, « codage par paires d'octets ») : on part des lettres,
puis on colle à chaque tour la paire de symboles voisins la plus fréquente.

C'est le projet de l'étape 1.3 de La Forge IA. Le site en propose un jumeau
en TypeScript qui doit donner exactement les mêmes résultats.

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
