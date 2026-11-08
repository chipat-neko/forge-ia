"""Extraire la prose d'un chapitre MDX : le texte sur lequel le modèle apprend."""

from modele_de_langage.extraire import extraire_prose

MDX = """---
partie: 0
titre: "Un titre"
---

import Figure from '../Figure.svelte';
import {
  un,
  deux,
} from '../lib.ts';

export const X = (() => {
  // Il n'y a pas de prose ici : l'apostrophe ne doit rien casser.
  const a = { b: 1 };
  return a;
})();

export const Y = nombre(3);

## Une étape

Un texte avec {nombre(x)} dedans et un 50&#8239;%.

<Etape numero={1}
  titre="Deux lignes"
  autre={`gabarit ${x > 2} <b>`}>

Le texte <code class="insecable">{VALEUR}</code> reste, et <Auto a="b" /> part.

```python
def f():
    return "pas de prose"
```

<Pari
  id="p"
  question={`Que vaut ${A} ?`}
>

Après le pari, 2 < 3 restent.

</Pari>

</Etape>
"""


def test_extraire_prose():
    prose = extraire_prose(MDX)
    assert prose == (
        "## Une étape\n\n"
        "Un texte avec dedans et un 50\u202f%.\n\n"
        "Le texte reste, et part.\n\n"
        "Après le pari, 2 < 3 restent.\n"
    )


def test_rien_ne_reste_du_code():
    prose = extraire_prose(MDX)
    for reste in ("import", "export", "{", "}", "```", "<Etape", "pas de prose", "partie:"):
        assert reste not in prose


def test_texte_sans_balise_ni_code():
    assert extraire_prose("Bonjour.\n\nAu revoir.\n") == "Bonjour.\n\nAu revoir.\n"
    assert extraire_prose("") == ""
