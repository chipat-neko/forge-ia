# Ton IA 1.7

Ton IA est un petit modèle de langage, créé de zéro pour le site « La Forge IA ». Un modèle de langage
est un programme qui a appris à deviner la suite d'un texte, morceau par morceau. Cette version est celle
du chapitre 1.7 : c'est ton IA 1.5, affinée le 19 novembre 2026 sur des conversations en français, pour
qu'elle réponde à une question au lieu de prolonger un texte.

## En chiffres

- **433 573 120 paramètres**, comme 1.5 : l'affinage change leurs valeurs, pas leur nombre. 20 couches,
  32 768 jetons de vocabulaire, 2 048 jetons lus au plus d'un coup.
- **Un affinage supervisé** (en anglais, SFT) : ton IA relit des conversations, et elle n'apprend que les
  réponses de l'assistant. 135 471 conversations (111 497 280 jetons, dont 85 483 056 appris), lues deux
  fois : 3 338 pas, au taux d'apprentissage 1e-4.
- **4 h 44 min 51 s de calcul** sur une carte graphique RTX 5070 Ti, en une session, le 19 novembre 2026
  de 10:11 à 15:04.
- **Elle finit ses réponses** : 51,0 % de ses réponses se terminent, contre 0,0 % pour 1.5. Elles sont en
  français dans 99,4 % des cas (87,2 % pour 1.5).
- **Elle suit moins bien les consignes que 1.5** : sur IFEval-FR (235 demandes en français, avec des
  consignes vérifiables, comme « sans virgule »), 14,5 % des demandes sont respectées en entier, contre
  21,7 % pour 1.5.
- **Elle prédit moins bien que 1.5 le texte libre** : sur le texte qu'elle avait lu en 1.5, son erreur
  monte de 0,779 à 0,972 bit par octet (plus c'est bas, mieux elle prédit).
- **Calcul :** elle résout 1 problème de calcul simple sur 400, aucun des 250
  problèmes de MGSM et 10 des 1 196 de GSM8K-Platinum : presque rien, mais 1.5 n'en résolvait aucun.

Ces mesures viennent de `rapport.json`, joint. Le récit complet est dans `ton-ia-1.7.md`, joint aussi.

## Ce que ton IA sait faire

- Répondre à une question, puis s'arrêter, une fois sur deux à peu près.
- Répondre en français.
- Donner un fait très connu : « La capitale de la France est Paris. »
- Écrire une définition juste quand elle est très courante (la photosynthèse, dans l'évaluation).
- Dire qu'elle est ton IA : « Je suis ton IA, une petite intelligence artificielle… », mais en se
  répétant.

## Ce qu'elle ne sait pas faire

- **Calculer.** À « Combien font 12 fois 7 ? », elle répète la question sans répondre.
- **Dire des choses vraies à coup sûr.** Elle écrit des choses fausses : le ciel serait bleu « parce que
  les nuages sont blancs », virus et bactéries se reproduiraient par « transformation ».
- **Respecter une consigne de forme** (« tout en minuscules », « sans virgule ») : elle le fait moins
  souvent que 1.5.
- **Écrire du code.** À la demande d'une fonction Python, elle déroule des étapes de calcul, sans code.
- **S'arrêter à coup sûr.** 49 % de ses réponses vont jusqu'à la limite de longueur sans finir ; dans les
  échantillons, elle y répète souvent une même phrase.
- **Prolonger un texte libre aussi bien que 1.5.** Son erreur sur ce texte a monté (voir plus haut).
- **Lire un long texte.** Au-delà de 2 048 jetons, elle oublie le début.

## Une autre version, non publiée

Un premier entraînement complet, au taux 3e-4, apprenait un peu mieux les conversations, mais il
prédisait nettement moins bien le texte libre : 3,766 nats par jeton sur le texte du pré-entraînement,
contre 2,928 pour cette version et 2,347 pour 1.5. Il est gardé en local pour comparer, et n'est pas
publié. Le récit est dans `ton-ia-1.7.md`.

## Les fichiers

| Fichier | Taille | Empreinte SHA-256 | Ce qu'il contient |
| --- | ---: | --- | --- |
| `ton-ia-1.7.safetensors` | 867 161 248 octets (827,0 Mo) | `6a6d2c08e15d4dc22fa3205d11e28ad3eb82d6944c649788836a125c25758d32` | les poids du modèle |
| `config.json` | 134 octets | `ae0207b367080a6577c2d95ef81ba5fb84c6bf2be11d03a07eedd8a9fe598621` | les dimensions du modèle |
| `tokenizer-ton-ia-v1.json` | 546 692 octets | `3001e7ab40630739c4dec807c7a92c0d4fb469cc0fc4afa368704395391f21ba` | le tokenizer |
| `rapport.json` | 17 660 octets | `8e7d291ab2fda4681229d872f9f3f97047500963db739cd20bd736c4de3767b5` | les mesures de l'évaluation, avec celles de 1.5 en regard |
| `ton-ia-1.7.md` | — | — | le récit complet de l'affinage et de l'évaluation |
| `LISEZMOI.md` | — | — | cette fiche |

- **Les poids** sont en bf16 (16 bits par nombre). Le format safetensors ne contient que des nombres, pas
  de code : ouvrir le fichier ne peut rien exécuter.
- **Le tokenizer et `config.json`** sont ceux de 1.5, à l'octet près.
- **L'empreinte SHA-256** permet de vérifier un fichier téléchargé. Sous Windows :
  `Get-FileHash ton-ia-1.7.safetensors`.

Comme pour 1.5, il manque exprès le poids `sortie.weight` : la sortie réutilise la matrice du plongement
(les poids sont « liés »), rangée une seule fois sous le nom `plongement.weight`.

## Parler avec ton IA

Il te faut le paquet `forge` du dépôt [chipat-neko/forge-ia](https://github.com/chipat-neko/forge-ia),
dans `projets/forge`, et l'outil `uv`, qui installe PyTorch et safetensors pour toi. Depuis
`projets/forge`, mets les trois fichiers du modèle dans un dossier `ton-ia-1.7`, puis :

```powershell
uv run --extra cpu python -m forge discuter --modele ton-ia-1.7 --temperature 0.7
```

(avec une carte NVIDIA : `--extra gpu`). Chaque ligne que tu écris est un tour ; `/nouveau` repart de
zéro, `/quitter` sort. Depuis Python :

```python
from pathlib import Path

from forge.conversation import Tour, invite_de_reponse, lire_reponse
from forge.modele import generer
from forge.publication import charger_publication

pub = charger_publication(Path("ton-ia-1.7"))  # poids, config.json et tokenizer, vérifiés
modele, tokenizer = pub.modele, pub.tokenizer

tours = [Tour("utilisateur", "Quelle est la capitale de la France ?")]
invite = invite_de_reponse(tokenizer, tours)  # la conversation, puis <|assistant|>
fin_tour = tokenizer.id_special("<|fin_tour|>")  # le jeton qui termine une réponse
suite = generer(modele, invite, 200, temperature=0.0, arret=fin_tour)
print(lire_reponse(tokenizer, suite).texte)
```

Une conversation commence par `<|fin_texte|>`, et chaque tour s'écrit `<|utilisateur|>` (ou
`<|assistant|>`, `<|systeme|>`) + texte + `<|fin_tour|>`. `invite_de_reponse` et `lire_reponse` le font
pour toi. Avec `temperature=0.0`, ton IA prend toujours le jeton le plus probable : même question, même
réponse.

## Licences

- **Les poids** (`ton-ia-1.7.safetensors`) sont sous **licence MIT**, comme le code du dépôt et comme
  1.5. La configuration et le tokenizer aussi. La licence MIT te permet de les utiliser, de les copier,
  de les modifier et de les partager, même pour vendre, à condition de garder la mention du droit
  d'auteur et le texte de la licence. Elle ne donne aucune garantie.
- **Le pré-entraînement** (celui de 1.5) garde ses licences : voir la fiche de `ton-ia-1.5`.
- **Les conversations de l'affinage** gardent leurs propres licences :
  - `kurakurai/Luth-2-Post-Training-SFT`, sous **CC BY 4.0**. On n'en garde que les lignes dont les
    réponses viennent de Qwen (Apache-2.0), en écartant les sources dont les fiches disent que les
    questions viennent de Llama ou d'OpenAI : toutes les lignes gardées viennent de
    `nvidia/Nemotron-Post-Training-Dataset-v2`. D'après la fiche de Luth-2, les
    lignes que Nemotron a tirées de StackOverflow restent sous **CC BY-SA 4.0**. Elles ne sont pas
    marquées : on ne peut pas les retirer, et elles restent dans les données, en nombre inconnu. Elles
    sont traitées comme Wikipédia (CC BY-SA) dans le pré-entraînement de 1.5 : les poids restent sous
    licence MIT, et cette fiche le dit ;
  - `CohereLabs/aya_dataset` (partie française) et `OpenAssistant/oasst2` (arbres en français), sous
    **Apache-2.0** ;
  - des conversations écrites par le code du dépôt (messages système, identité de ton IA), sous
    **licence MIT** ; les réponses des messages système viennent de Luth-2 (CC BY 4.0).
- **Les jeux d'évaluation** (IFEval-FR, MGSM-rev2, GSM8K-Platinum-fr, HumanEval) n'ont servi qu'à
  mesurer, jamais à apprendre.

**Attention :** les textes que ton IA écrit peuvent reprendre des bouts de ces données, mot pour mot.
Avant de publier un texte qu'elle a écrit, vérifie que ce n'est pas une copie.
