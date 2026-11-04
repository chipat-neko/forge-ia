# Le mot suivant

Un petit programme qui lit un texte, compte quel mot suit quel autre, puis
devine le mot suivant. En partant d'un mot, il enchaîne à chaque fois le mot
qui le suit le plus souvent dans le texte : il écrit ainsi une suite de mots.

C'est le projet de l'étape 0.1 de La Forge IA, « Python pour l'IA ». Il
n'utilise que la bibliothèque standard de Python : texte, listes, tranches,
`zip`, dictionnaires et `Counter`. Le site en propose un jumeau en TypeScript
qui doit donner exactement les mêmes résultats.

## Lancer

Il faut `uv` et Python 3.12 ou plus. Dans PowerShell :

```powershell
cd projets/0.1-python
uv run python -m mot_suivant le --longueur 12
```

Le programme affiche les mots qui suivent « le » dans le texte, avec leur
nombre d'apparitions, puis une suite de 12 mots qui commence par « le ». Avec
`--fichier mon-texte.txt`, il lit un autre texte (en UTF-8).

## Tester

```powershell
cd projets/0.1-python
uv run pytest -q
```

## Les règles à connaître

- Le texte est mis en minuscules, puis découpé en mots (`decouper_mots`). Un
  mot est une suite de lettres du français, d'apostrophes (`'` ou `’`) et de
  traits d'union. Le point, le point d'exclamation et le point
  d'interrogation sont des mots à part : ils marquent la fin d'une phrase.
  Tout le reste sépare les mots : espaces, virgules, chiffres, emojis…
- Pour chaque mot, le programme compte les mots qui le suivent
  (`compter_suivants`).
- Le mot suivant prédit est le plus fréquent. En cas d'égalité, on prend le
  plus petit dans l'ordre des points de code, comme au chapitre 1.3
  (`predire`).
- La suite s'arrête quand rien ne suit le dernier mot, ou quand le mot de
  départ n'est pas dans le texte (`generer`). Comme le choix est toujours le
  même, la suite finit par revenir sur un mot déjà vu, et tourne alors en
  rond (`premiere_reprise`).

## Le texte

`donnees/texte.txt` est une copie exacte du corpus du chapitre 1.3
(`projets/1.3-tokenizer/donnees/corpus.txt`). Dans le dépôt, un test vérifie
que les deux fichiers restent identiques.

## Les attendus de référence

Le fichier `tests/attendus.json` contient, pour plusieurs textes, les mots
découpés, les suivants de chaque mot, les prédictions et des suites de 1, 2,
12 et 30 mots. Le jumeau TypeScript doit retrouver ces valeurs à l'identique.
Pour le régénérer :

```powershell
cd projets/0.1-python
uv run python -m mot_suivant.attendus
```

Un test vérifie que le fichier est à jour : si le code change, il échoue
tant que le fichier n'est pas régénéré.
