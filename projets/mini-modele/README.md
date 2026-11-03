# Le mini-modèle qui apprend (jumeau Python des démos)

Ce projet est le jumeau exact des démos du site : le mini-modèle qui apprend
à inventer des prénoms, et l'animation de l'attention. Le site les fait
tourner en TypeScript dans le navigateur (`site/src/lib/mini-modele/`). Ce
paquet Python (`mini_modele`) refait les mêmes calculs, avec les mêmes
opérations dans le même ordre, et les deux langages doivent trouver les mêmes
nombres, au bit près.

Il n'a pas de numéro de chapitre, comme `projets/forge` : il sert plusieurs
chapitres (l'avant-goût de 0.5, puis 1.5).

## Tester

Il faut `uv` et Python 3.12 ou plus. Depuis le dossier `projets/mini-modele` :

```powershell
uv run pytest -q
```

Côté site, depuis le dossier `site` :

```powershell
npx vitest run src/lib/mini-modele
```

## Les attendus partagés

Le Python écrit des fichiers de référence, `tests/attendus-<nom>.json`. Chaque
nombre à virgule y est écrit en 16 chiffres hexadécimaux : ce sont ses 8
octets, du plus fort au plus faible (`3ff0000000000000` pour 1,0). Vitest
relit ces fichiers et compare les motifs du TypeScript à ceux du Python : un
seul bit de différence fait échouer le test. Pour les régénérer, depuis
`projets/mini-modele` :

```powershell
uv run python -m mini_modele.attendus
```

Un test vérifie que les fichiers sont à jour : si le code change, il échoue
tant qu'ils ne sont pas régénérés.

## Pourquoi on n'utilise ni `math.exp` ni `sum`

Pour trouver les mêmes bits partout, il faut des opérations dont le résultat
est fixé par la norme IEEE 754, sur toutes les machines et dans tous les
navigateurs.

- `math.exp`, `math.log` et `math.cos` appellent la bibliothèque mathématique
  de la machine. En JavaScript, `Math.exp` et ses voisines sont « approchées
  selon l'implémentation » : Chrome, Firefox et Safari ne donnent pas toujours
  le même dernier bit. Le paquet écrit donc ses propres `exp`, `log` et `cos`
  (dans `mini_modele/calcul.py`) avec seulement des + − × ÷.
- `sum()` fait une somme compensée depuis Python 3.12 : plus précise, mais
  différente d'une simple boucle. Toute somme est donc une boucle `s += v`,
  dans l'ordre des indices.
- `max()` et `Math.max` traitent −0 différemment : un maximum est une boucle
  `if v > m`. Les fonctions intégrées `pow`, `max`, `min`, `round` et
  `divmod` sont refusées dans les fichiers vérifiés. Une puissance devient une
  boucle de produits (`p = p * b` à chaque pas), et un arrondi un
  `math.floor(x + 0.5)` écrit de la même façon des deux côtés.
- Les divisions entières suivent une règle qu'aucun test ne peut vérifier
  (le signe d'une variable ne se lit pas dans le code) : les indices sont
  toujours positifs, et `%` et `//` ne servent que sur des entiers positifs.
  Là, les deux langages donnent le même résultat : `a % b` des deux côtés, et
  `a // b` en Python face à `Math.floor(a / b)` en TypeScript. Sur un nombre
  négatif ou à virgule, le `%` de Python prend le signe du diviseur et celui
  de JavaScript le signe du dividende ; on écrit alors `floor` explicitement,
  des deux côtés : `math.floor(a / b)`, et `a - b * math.floor(a / b)`.
- Le hasard vient de `Hasard` (SplitMix32), jamais de `random` : Python ne
  garantit pas ses tirages d'une version à l'autre.

Les fichiers vérifiés sont `calcul.py`, `donnees.py`, `attention.py`,
`modele.py`, `entrainement.py` et `exemple_attention.py`. On n'y permet que
les + − × ÷, `math.sqrt` (arrondi correct, partout), `math.floor` et les
opérations entières. S'y ajoutent `math.ldexp` et `math.frexp`, permis parce
qu'ils sont exacts : ils ne changent que l'exposant, sans arrondi. Le test
`tests/test_sources.py` cherche les fonctions interdites dans ces fichiers,
commentaires compris ; `site/src/lib/mini-modele/sources.test.ts` fait de même
pour le TypeScript.
