# Ton IA 1.5

Ton IA est un petit modèle de langage, créé de zéro pour le site « La Forge IA ». Un modèle de langage
est un programme qui a appris à deviner la suite d'un texte, morceau par morceau. Ton IA lit et écrit
le français et le code Python. Cette version est celle du chapitre 1.5 : elle a été entraînée du 3 au
14 novembre 2026, sur un seul PC.

## En chiffres

- **433 573 120 paramètres.** Ce sont les nombres que le modèle a réglés en apprenant.
- **20 couches** empilées. Dans chaque couche, un jeton est représenté par 1 280 nombres.
- **Des jetons.** Un jeton est un morceau de texte : un mot court ou un bout de mot. Le vocabulaire en
  compte 32 768. Ton IA lit au plus 2 048 jetons d'un coup.
- **8 671 723 520 jetons lus**, soit 20 par paramètre. Chaque texte n'a été lu qu'une fois.
- **139 h 06 min de calcul** sur une carte graphique RTX 5070 Ti, en 13 sessions. Avec les pauses,
  l'entraînement a duré 11 j 3 h 43 min.
- **Une perplexité de 11,2.** Pour deviner le jeton suivant, ton IA hésite en moyenne comme entre 11
  choix également probables. Au hasard, ce serait 32 768.
- **0,802 bit par octet.** C'est l'erreur de prédiction, ramenée à un octet de texte : plus c'est
  bas, mieux le modèle prédit.
- **Des QCM en français.** Un QCM est un questionnaire à choix multiples : pour chaque question, il
  faut choisir la bonne réponse parmi plusieurs. Ceux-ci viennent de FrenchBench, des traductions
  automatiques en français :
  - HellaSwag (choisir la bonne fin d'une histoire, parmi 4) : 34,8 % de bonnes réponses, contre
    25,0 % au hasard. C'est mieux que le hasard. Ce score corrige l'avantage des réponses courtes ;
    sans cette correction, il est de 29,7 %.
  - ARC-Challenge (des questions de sciences) : 25,1 %, contre 25,0 % au hasard. Ce n'est pas mieux
    que le hasard.

Ces mesures viennent de `rapport.json`, joint. Le récit complet est dans `ton-ia-1.5.md`, joint aussi.

## Ce que ton IA sait faire

- Écrire des phrases en français, le plus souvent correctes, mais pas toujours sensées.
- Prendre le ton du début donné : récit, article de presse, message de forum.
- Garder le sujet, mais seulement une fois sur deux : dans 5 des 10 textes de l'évaluation. Dans les
  5 autres, elle se contredit ou change de sujet.
- Retrouver quelques faits très connus. Exemple : « La capitale de la France est Paris ».
- Écrire du texte qui a la forme du code Python : des lignes bien décalées, un `return`.

## Ce qu'elle ne sait pas faire

- **Répondre à une question ou suivre une consigne.** Elle n'a jamais appris à dialoguer. Si tu lui
  poses une question, elle écrit la suite d'un texte qui commence par ta question.
- **Dire des choses vraies à coup sûr.** Elle invente des chiffres, des faits et des recettes. Ce
  qu'elle écrit a l'air vrai, mais rien n'est vérifié.
- **Rester cohérente longtemps.** Après quelques phrases, elle se contredit ou change de sujet.
- **Écrire du code qui marche.** Dans les deux essais de code de l'évaluation, la fonction écrite est
  fausse.
- **Répondre à des questions de sciences** mieux que le hasard.
- **Lire un long texte.** Au-delà de 2 048 jetons (environ 8 900 octets de texte), elle oublie le
  début.
- **Parler anglais.** Ce n'était pas le but : elle a lu du français et du code Python.

## Les fichiers

| Fichier | Taille | Empreinte SHA-256 | Ce qu'il contient |
| --- | ---: | --- | --- |
| `ton-ia-1.5.safetensors` | 867 161 248 octets (827,0 Mo) | `0e89f94133ea47a65e2cd19c111beb24f3ae210c9e332f92c6538a2e22b0d6ea` | les poids du modèle |
| `config.json` | 134 octets | `ae0207b367080a6577c2d95ef81ba5fb84c6bf2be11d03a07eedd8a9fe598621` | les dimensions du modèle |
| `tokenizer-ton-ia-v1.json` | 546 692 octets | `3001e7ab40630739c4dec807c7a92c0d4fb469cc0fc4afa368704395391f21ba` | le tokenizer |
| `rapport.json` | 5 800 octets | `059355969c2eab459b9d19b20c6540450fa4f3e52b361bbcd343e86321a140bc` | les mesures de l'évaluation |
| `ton-ia-1.5.md` | — | — | le récit complet de l'entraînement et de l'évaluation |
| `LISEZMOI.md` | — | — | cette fiche |

- **Les poids** sont les paramètres appris. Ils sont rangés en bf16 : 16 bits par nombre, deux fois
  moins lourd qu'en 32 bits. Le format safetensors ne contient que des nombres, pas de code : ouvrir
  le fichier ne peut rien exécuter.
- **Le tokenizer** découpe le texte en jetons, et recolle les jetons en texte.
- **L'empreinte SHA-256** permet de vérifier un fichier téléchargé : si un seul octet change, elle
  change. Sous Windows : `Get-FileHash ton-ia-1.5.safetensors`.

Il manque exprès un poids, `sortie.weight`. Dans ton IA, la dernière couche (la sortie) réutilise la
même matrice que la toute première (le plongement) : on dit que les poids sont « liés ». Le fichier ne
la range qu'une fois, sous le nom `plongement.weight`.

## Charger ton IA

Il te faut le code du modèle : le paquet `forge` du dépôt
[chipat-neko/forge-ia](https://github.com/chipat-neko/forge-ia), dans `projets/forge`. Il te faut aussi
PyTorch, la bibliothèque Python qui fait les calculs du modèle, et safetensors, qui lit le fichier des
poids. L'outil `uv` installe tout cela pour toi : depuis `projets/forge`,
`uv run --extra cpu python ton_script.py` installe ce qu'il faut, puis lance ton script (avec une
carte NVIDIA : `--extra gpu`).

1. Mets les trois fichiers du modèle dans un même dossier, et écris son chemin dans `dossier` (ici
   `ton-ia-1.5`, dans le dossier d'où tu lances le script).
2. Lis la configuration, puis crée le modèle vide qu'elle décrit.
3. Charge les poids, et reprends la sortie du plongement.
4. Charge le tokenizer.

```python
import json
from pathlib import Path

from safetensors.torch import load_file

from forge.modele import ConfigModele, Transformer, generer
from forge.tokenizer import TokenizerOctets

dossier = Path("ton-ia-1.5")
config = ConfigModele(**json.loads((dossier / "config.json").read_text(encoding="utf-8")))
poids = load_file(dossier / "ton-ia-1.5.safetensors")
poids.setdefault("sortie.weight", poids["plongement.weight"])  # les poids liés
modele = Transformer(config)
modele.load_state_dict(poids)
tokenizer = TokenizerOctets.charger(dossier / "tokenizer-ton-ia-v1.json")

# Faire écrire ton IA : elle prolonge le début donné.
fin = tokenizer.id_special("<|fin_texte|>")  # pour ton IA, ce jeton marque aussi le début d'un texte
debut = [fin, *tokenizer.encoder("Il était une fois")]
suite = generer(modele, debut, 40, temperature=0.8, top_k=50, graine=0, arret=fin)
print("Il était une fois" + tokenizer.decoder([jeton for jeton in suite if jeton != fin]))
```

`generer` tire les jetons un par un. La `temperature` règle le hasard (0 : toujours le jeton le plus
probable), `top_k` ne garde que les 50 jetons les plus probables, et la `graine` fixe le tirage : même
graine, même texte (sur un même appareil).

## Licences

- **Les poids** (`ton-ia-1.5.safetensors`) sont sous **licence MIT**, comme le code du dépôt (voir le
  fichier `LICENSE` du dépôt). La configuration et le tokenizer aussi. La licence MIT te permet de les
  utiliser, de les copier, de les modifier et de les partager, même pour vendre, à condition de garder
  la mention du droit d'auteur et le texte de la licence. Elle ne donne aucune garantie.
- **Les données d'entraînement** gardent leurs propres licences :
  - le français du web : `HuggingFaceFW/fineweb-2` (partie `fra_Latn`), sous **ODC-By 1.0** ;
  - Wikipédia en français : `wikimedia/wikipedia`, version `20231101.fr`, sous **CC BY-SA 3.0** et
    **GFDL** ;
  - le code Python : `codeparrot/github-code-clean`. La compilation est sous **Apache-2.0**. Seuls les
    fichiers sous l'une de ces licences ont été gardés : `mit`, `apache-2.0`, `bsd-2-clause`,
    `bsd-3-clause`, `isc`, `unlicense` ou `cc0-1.0`.

**Attention :** les textes que ton IA écrit peuvent reprendre des bouts de ces données, mot pour mot.
Avant de publier un texte qu'elle a écrit, vérifie que ce n'est pas une copie.
