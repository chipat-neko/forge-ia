# L'aligner : les préférences et la DPO

Après l'affinage du chapitre 1.7, « ton IA » répond. Mais deux réponses à la même question ne se valent pas : l'une
finit son tour, l'autre est coupée ; l'une respecte la consigne, l'autre l'oublie. Ce projet refait, pas à pas et à la
main, les pièces que le chapitre 1.8 explique, puis les compare à forge (le paquet `forge`, dans `projets/forge`), le
moteur de « ton IA » :

- il **note une réponse** par les contrôles programmés de forge (`forge.preferences.noter`), critère par critère, avec
  la raison de chacun : « 3 consignes sur 3 », « en français », « 47 mots ». La note rendue est celle de forge ;
- il refait **la perte DPO** d'une paire : `z = β ((pc − qc) − (pr − qr))`, `perte = −ln σ(z)`, en nombres Python
  (float64), égale à `perte_dpo` de forge à 10⁻¹² près quand `normaliser_longueur` vaut `false` (la forme non normalisée : forge
  divise sinon les gains par le nombre de jetons de chaque réponse), avec le terme SFT à part ;
- il fait **quelques pas de DPO sur une seule paire**, avec un modèle minuscule et le vrai code de forge, pour voir ce
  que la perte pousse : la réponse choisie vers le haut, ou la rejetée vers le bas ;
- il **résume** ce que le plan 7 construit et mesure sur ton IA 1.8 (le rapport d'étape de `forge evaluer-etape`, les
  premières paires de préférences, le balayage de la DPO, les courbes de l'entraînement) en fichiers que le chapitre
  lit.

C'est le projet du chapitre 1.8 de La Forge IA, « L'aligner : préférences et récompenses », en ligne à l'adresse
<https://chipat-neko.github.io/forge-ia/partie-1/1-8/>. Les mots techniques sont expliqués dans le glossaire :
<https://chipat-neko.github.io/forge-ia/annexes/glossaire/>. Comme les projets 0.3 à 0.5 et 1.4 à 1.7, il utilise
PyTorch, en deux versions au choix : celle pour carte NVIDIA (extra `gpu`, CUDA 13.2) et celle pour le processeur
seul (extra `cpu`). Les commandes ci-dessous prennent le processeur, qui suffit à tout ce que ce projet calcule.

Il dépend de forge et du projet 1.5 par chemin (`forge-ia = { path = "../forge", editable = true }` et
`pre-entrainement = { path = "../1.5-pre-entrainement", editable = true }` dans `pyproject.toml`) : il faut donc le
dépôt entier, pas seulement ce dossier. Il ne modifie aucun fichier de forge.

## Ce qu'il prend à forge

- `forge.preferences.noter` : `Note`, `noter`, `choisir_paire`, `sans_paire`, `raison_de_la_paire` (les cinq critères
  et leur ordre) ; `forge.preferences.invites` : `InvitePreference` (une invite avec ses consignes et, pour un
  problème, sa réponse attendue) ; `forge.preferences.construction` : les noms du dossier des paires ;
- `forge.evaluation.consignes` : `CONTRAINTES`, les huit consignes (`mots_max`, `phrases_max`, `minuscules`,
  `sans_virgule`, `mot_obligatoire`, `puces`, `fin_imposee`, `titre`) ; `forge.evaluation.langue` : `langue` et `mots` ;
  `forge.raisonnement.verification` : `est_juste` et `extraire_nombre` ;
- `forge.affinage.dpo` : `perte_dpo` (la perte de forge, terme SFT compris) et `logps_des_rangees` ;
  `forge.entrainement.boucle` : `ReglagesDPO` (β, `normaliser_longueur`, `poids_sft`) ;
  `forge.affinage.jeu` : `lire_index`, `LotAffinage` ; `forge.fragments` : `lire_elements` (les paires écrites par
  fragments) ;
- `forge.evaluation.etape` : `VERSION_DU_RAPPORT_D_ETAPE` (le format du `rapport.json` que `resumer` lit) ;
- `forge.modele` : `Transformer` et `ConfigModele` ; `forge.tokenizer` : `TokenizerOctets` (le tokenizer figé de « ton
  IA »).

Et au projet 1.5 : `pre_entrainement.journal` (`lire`, `serie`) pour les courbes.

## Installer uv

`uv` installe Python et les bibliothèques de chaque projet. Le fichier `.python-version` demande Python 3.12 : uv le
télécharge lui-même s'il manque. Pour installer uv, voir le README du projet 0.3 (`projets/0.3-poste`), ou
<https://docs.astral.sh/uv/getting-started/installation/>.

## Lancer

Récupère le dépôt, puis va dans le dossier du projet. Les commandes sont les mêmes dans PowerShell (Windows) et dans
un terminal (Linux, Mac) :

```bash
git clone https://github.com/chipat-neko/forge-ia
cd forge-ia/projets/1.8-alignement
```

```bash
uv run --extra cpu python -m alignement_pas_a_pas noter "paris est la capitale." --consigne minuscules --consigne mots_max:n=20
uv run --extra cpu python -m alignement_pas_a_pas dpo --pc -12 --pr -20 --qc -14 --qr -18 --beta 0.1
uv run --extra cpu python -m alignement_pas_a_pas pousser --pas 40
```

- `noter` donne la note d'une réponse critère par critère, avec la raison de chacun, puis chaque consigne et si elle est
  respectée. `--coupee` dit que la réponse a été coupée par la limite de jetons, `--attendu` donne la réponse d'un
  problème, `--consigne` (répétable) une consigne de l'invite : `minuscules`, `mots_max:n=20`,
  `fin_imposee:phrase=Merci.`…
- `dpo` calcule la perte d'une paire à la main et dans forge, avec le terme SFT, et dit si elles sont égales à
  10⁻¹² près (le code de sortie est 1 si elles ne le sont pas).
- `pousser` fait quelques pas de DPO sur une paire et un modèle minuscule (2 couches, des vecteurs de 32 nombres, des
  poids tirés au hasard), et écrit, à chaque étape, la log-probabilité moyenne par jeton de la choisie et de la
  rejetée. La paire est la première de `mesures/paires-exemples.json` quand ce fichier existe, sinon une paire
  fabriquée, et la commande le dit.

## Ce que ton IA 1.8 ajoute

Ces commandes lisent ce que le plan 7 construit et mesure sur ton IA, sans rien recalculer et sans rien écrire dans les
données de l'auteur (ce sont des fichiers qu'on lit) :

```bash
uv run --extra cpu python -m alignement_pas_a_pas resumer --rapport <rapport.json> --json mesures/etape-ton-ia-1.8.json
uv run --extra cpu python -m alignement_pas_a_pas paires --jeu <FORGE_DONNEES>/affinage/preferences-1.8 --json mesures/paires-exemples.json
uv run --extra cpu python -m alignement_pas_a_pas balayage <essai> <essai> … --json mesures/balayage-1.8.json
uv run --extra cpu python -m alignement_pas_a_pas courbes --journal <journal.jsonl> --json mesures/entrainement-dpo-1.8.json
```

- `resumer` lit le `rapport.json` de `python -m forge evaluer-etape --etape 1.8` et en tire
  `{version, etape, releve_le, mesures, echantillons}` : les mesures du rapport (`perte_conversation`, `ifeval_fr`,
  `tenue`, `oubli`, `victoire`), telles quelles, une mesure dont les données manquaient restant
  `{"absente": "<raison>"}`, et les dix échantillons, tels quels. Avec `--reference`, c'est la version de référence du
  rapport qui est résumée.
- `paires` garde les `--n` premières paires d'entraînement du jeu de préférences (6 par défaut), pas les plus belles :
  l'invite, les deux réponses telles que ton IA les a écrites, leurs notes critère par critère, les log-probabilités de
  référence (`train/reference.bin`, que la DPO calcule avant son premier pas) et la source de l'invite avec sa licence
  (Luth-2, CC BY 4.0, ou un problème généré par le code du dépôt, MIT). Les réponses de ton IA sont les siennes ; seules
  les invites de Luth-2 sont citées, avec leur licence, comme le plan 8 l'a prévu : six paires au plus.
- `balayage` résume les essais du balayage de la DPO. **Convention** : chaque essai est rangé dans un dossier qui
  contient `journal.jsonl` (la sortie de `forge entrainer`), `config.toml` (la configuration de l'essai, copiée à la
  main : forge ne la recopie pas) et `rapport.json` (celui de
  `forge evaluer-etape --etape 1.8 --reference … --invites … --sortie <ce dossier>`). Le relevé : les réglages (`taux_max`, `beta`,
  `normaliser_longueur`, `poids_sft`), la victoire (`taux`, `victoires`, `egalites`, `defaites`, `n`), la longueur
  (mots moyens du modèle et de la référence) et `logps_choisie` au début et à la fin (la moyenne du premier et du dernier
  dixième des pas).
- `courbes` réduit `logps_choisie`, `logps_rejetee` et `exactitude` du journal d'une DPO en paquets de pas, par
  `pre_entrainement.journal.serie`, avec le découpage du site. Si la log-probabilité de la choisie baisse, la courbe le
  montre : c'est le piège connu de la DPO.

## Les pièces à la main

Les régions de `alignement_pas_a_pas`, tirées des repères `# region: <nom>` et `# fin: <nom>` :

| Fichier | Région | Ce qu'il fait |
| --- | --- | --- |
| `noter.py` | `noter` | `expliquer_note(reponse_texte, terminee, invite)` : les cinq critères de forge, chacun avec sa valeur, son maximum, son verdict et sa raison en français ; la `note` rendue est celle de `forge.preferences.noter` (un test, sur cinquante réponses) |
| `perte_dpo.py` | `perte-dpo` | `perte_dpo_a_la_main(pc, pr, qc, qr, beta)`, `terme_sft_a_la_main(pc, lc)` et `derivee_a_la_main` : en float64, égales à `perte_dpo` de forge à 10⁻¹² près |
| `poussee.py` | `poussee` | `paire_du_notebook`, `lot_de_la_paire`, `pousser` : quelques pas de DPO sur une paire |
| `courbes.py` | `courbes` | `courbes_dpo(journal)` |
| `resumer.py` | `resumer`, `paires`, `balayage` | `resumer_etape`, `paires_exemples`, `balayage` |
| `attendus.py` | | écrit `tests/attendus.json`, que les jumeaux TypeScript du site vérifient |

La région `test-dpo` est dans `tests/test_perte_dpo.py` : le test qui compare la perte à la main à celle de forge. Au-delà
de |z| = 20, le `softplus` de PyTorch rend z tel quel et s'écarte de la formule d'environ 10⁻⁹ : la grille des
attendus et ce test restent en deçà (un autre test le montre).

## Les jumeaux TypeScript

Le site refait deux calculs en TypeScript, avec les mêmes fonctions et le même ordre d'opérations, et les compare au
fichier `tests/attendus.json` (écrit par `python -m alignement_pas_a_pas.attendus`) :

- `site/src/lib/partie-1/notes.ts` : `mots`, `langue`, `VERIFICATEURS_CONTRAINTES` (les huit consignes de forge) et
  `noteSansJustesse(texte, terminee, contraintes)`, traductions exactes de `forge.evaluation.langue` et
  `forge.evaluation.consignes`, listes de mots outils comprises (le test relit `langue.py` pour le vérifier). Pas de
  `\w`, de `\b` ni de `trim()` : les blancs de Python, la lecture en points de code, les catégories Unicode sont
  explicites. Sans tolérance, dans Node (Vitest) puis dans Chrome, Firefox et WebKit (la page d'essai de parité,
  `e2e/parite.spec.ts`) ;
- `site/src/lib/partie-1/dpo.ts` : `perteDpo(beta, ecartChoisie, ecartRejetee)` et sa dérivée, comparées à 10⁻¹² près
  (`Math.exp` et `Math.log1p` ne sont pas exacts d'un moteur à l'autre) ; hors de la page de parité.

`tests/attendus.json` a trois sections : `consignes` (les huit consignes de forge avec leurs réglages de référence),
`textes` (quarante textes de référence, dont les pièges de l'atelier : accent combinant, apostrophe courbe, espace fine
insécable, espace insécable, emoji, lettre hors du premier plan d'Unicode, blancs que Python et JavaScript ne comptent
pas pareil, texte vide, chiffres seuls, dix mille caractères, avec le verdict de chaque consigne, la langue, la
longueur et la note) et `grille_dpo` (27 points : β, écart de la choisie, écart de la rejetée).

## Les mesures et les sorties

Chaque fichier de mesures est écrit en UTF-8, fins de ligne LF, par le projet ; le site les lit à la construction.

| Fichier | D'où il vient |
| --- | --- |
| `mesures/etape-ton-ia-1.8.json`, `mesures/etape-ton-ia-1.8-court.json` | `resumer` sur le rapport de `forge evaluer-etape --etape 1.8` (à relever quand ton-ia-1.8 est publiée) |
| `mesures/paires-exemples.json` | `paires` sur le jeu de préférences (à relever après la DPO : la référence en fait partie) |
| `mesures/balayage-1.8.json` | `balayage` sur les essais de la DPO |
| `mesures/entrainement-dpo-1.8.json` | `courbes` sur le journal de la DPO |

Tant qu'un de ces fichiers n'existe pas, le chapitre affiche « à mesurer » à sa place, et le notebook travaille sur une
paire fabriquée, en le disant.

## Tester

```bash
uv run --extra cpu pytest -q
```

`test_notebook.py` exécute le notebook du chapitre (`notebooks/1.8-alignement.ipynb`) de bout en bout, sur le processeur.
