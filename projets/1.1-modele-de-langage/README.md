# Un modèle de langage à n-grammes de caractères

Le plus petit modèle de langage qui existe : il compte, dans un texte, quel
caractère suit chaque groupe de n caractères, puis s'en sert pour deviner la
suite d'un texte, et pour en écrire une. Il apprend sur le texte du site
lui-même, les chapitres 0.1 à 0.5 et 1.3 de La Forge IA.

C'est le projet du chapitre 1.1 de La Forge IA, « Ce qu'est vraiment un modèle
de langage ». Il n'utilise que la bibliothèque standard de Python. Le site en
propose un jumeau en TypeScript, pour sa figure, qui doit donner exactement les
mêmes nombres et les mêmes textes.

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
cd forge-ia/projets/1.1-modele-de-langage
uv run python -m modele_de_langage suite --n 4 --temperature 1 --graine 0 "Le forgeron "
```

Sans git, le bouton « Code » de la page GitHub du dépôt donne aussi un fichier
zip : son dossier s'appelle `forge-ia-main`, à écrire à la place de `forge-ia`
dans la commande `cd`.

La commande `suite` apprend les comptes sur les 90 premiers % du texte du site,
puis écrit 200 caractères à la suite du départ. Il ne tire que parmi les
caractères déjà vus après le contexte, et, si le contexte est inconnu, il
recule : il regarde un caractère de moins, jusqu'à zéro. Les options :

- `--n` : combien de caractères précédents le modèle regarde, de 0 à 6 (4 par défaut) ;
- `--temperature` : 0 (toujours le plus compté), 0.5, 1 (les comptes du
  modèle) ou 2 (plus de hasard) ;
- `--graine` : la graine du hasard. La même graine donne toujours le même texte,
  ici comme dans la page du site ;
- `--longueur` : combien de caractères écrire (200 par défaut).

## Tester

Dans le dossier du projet :

```bash
uv run pytest
```

Avec `-q`, pytest n'affiche qu'un point par test réussi et le bilan.

## Le texte du site

Le fichier `donnees/texte-du-site.txt` est la prose des chapitres du site.
Sont retirés (`modele_de_langage/extraire.py`) : le frontmatter, les imports
et les calculs, les blocs de code, les balises des composants, les `**` du gras,
les `#` des titres et les adresses des liens (leur texte reste). Dans le code
en ligne, seuls les accents graves sont retirés : son contenu reste tel quel.
Il reste les puces des listes. Le fichier est tiré des chapitres tels qu'ils
étaient au commit `ae8d9a4`, pour que le texte
ne change pas quand les chapitres changent. Pour le refaire :

```bash
uv run python -m modele_de_langage extraire --commit ae8d9a4 --sortie donnees/texte-du-site.txt
```

Il faut le dépôt complet, avec son historique : la commande relit les chapitres
par `git show`.

## Ce que montre le chapitre

Le chapitre 1.1 montre le code du projet, tiré des régions balisées par
`# region: <nom>` et `# fin: <nom>`.

| Fichier | Région |
| --- | --- |
| `modele_de_langage/ngrammes.py` | `compter`, `distribution`, `poids`, `tirer`, `generer`, `perplexite` |
| `tests/test_ngrammes.py` | `test-uniforme` |

## Ce que contient le paquet

- `ngrammes.py` : couper le texte (90 % pour apprendre, 10 % pour vérifier),
  `compter` ce qui suit chaque contexte (`compter_par_ordre` pour tous les
  ordres de 0 à n), la `distribution` des probabilités avec le lissage de
  Laplace (pour mesurer, jamais pour tirer), les `poids` de chaque température
  (des comptes bruts : un caractère jamais vu a un poids nul), `tirer` au sort,
  `generer` du texte (il recule d'un ordre quand le contexte est inconnu), la
  part de contextes jamais vus, et la `perplexite`.
- `extraire.py` : la prose d'un chapitre MDX, et la lecture des chapitres du dépôt.
- `hasard.py` : un hasard reproductible (SplitMix32).
- `attendus.py` : les valeurs de référence pour le site.

## Le hasard

`Hasard` est une copie exacte de celui du projet 0.2
(`projets/0.2-maths/maths_utiles/tirage.py`), lui-même repris du mini-modèle :
une même graine donne la même suite de nombres en Python et en TypeScript, sur
toutes les machines. Dans le dépôt, un test vérifie que la copie reste
identique à l'original.

## Les attendus de référence

Le fichier `tests/attendus.json` contient les résultats du Python : l'alphabet
du texte, pour chaque n de 0 à 6 les perplexités, la part de contextes jamais
vus et les dix caractères les plus probables après des contextes de référence,
des suites écrites à chaque température et avec deux graines, et des cas
limites (texte vide, un seul caractère, un emoji, un contexte jamais vu).
Le jumeau TypeScript doit retrouver à l'identique tout ce qui n'est pas une
perplexité. Pour le régénérer :

```powershell
cd projets/1.1-modele-de-langage
uv run python -m modele_de_langage.attendus
```

Un test vérifie que le fichier est à jour : si le code ou le texte change, il
échoue tant que le fichier n'est pas régénéré. La perplexité passe par `exp` et
`log`, dont le dernier chiffre peut changer d'un système à l'autre (Linux et
Windows n'ont pas la même bibliothèque mathématique) : elle est comparée à
10⁻⁹ près, tout le reste au bit près. Le site ne recalcule pas la perplexité :
il lit les valeurs du Python.
