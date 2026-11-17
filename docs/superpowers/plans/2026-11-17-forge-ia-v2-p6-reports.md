# La Forge IA, vague 2, plan 6 : les reports de la vague 1

> **Pour les agents qui exécutent ce plan :** SOUS-SKILL REQUIS : utiliser superpowers:subagent-driven-development (recommandé) ou superpowers:executing-plans pour réaliser ce plan tâche par tâche. Les étapes utilisent des cases à cocher (`- [ ]`).

**But :** solder ce que les revues finales des plans 2 et 5 ont reporté, avant que la vague 2 ne construise sur `forge` :

1. reprendre un téléchargement au fragment près ;
2. calculer les bits par octet exacts, puis réévaluer ton-ia-1.5 et « mini » avec ce calcul ;
3. vérifier, à l'export, que la sauvegarde a été entraînée avec le tokenizer figé ;
4. regrouper le code en double de `forge` ;
5. quelques restes.

**Architecture :** tout se passe dans `projets/forge`. S'y ajoutent les rapports de `docs/mesures/`, les fichiers de mesures du projet 1.6 et la Release `ton-ia-1.5` (notes et documents seulement). Aucun format publié ne change :
- les fichiers de poids, `config.json` et le tokenizer figé de la Release restent identiques à l'octet près ;
- les sauvegardes d'entraînement peuvent changer, puisque l'entraînement est fini.

**Pile technique :** celle de la vague 1. Python 3.12, uv, pytest, PyTorch 2.15.0 (roues `cpu` et `cu132`), `datasets` 5.1 ou plus récent.

**Spécification :** `docs/superpowers/specs/2026-11-02-forge-ia-design.md`, sections 8 (pause et reprise, code qui marche) et 9 (honnêteté).

**Sources des reports :**
- `.superpowers/sdd/2026-11-03-forge-ia-v1-p2-moteur/final-review.md` : I3, M4, M5, M8 et M9 ;
- les lignes « Parked » du ledger du plan 2 ;
- les lignes « Parked for wave 2 » du ledger du plan 5.

## Recherche faite avant ce plan (le 17/11/2026)

Source : `docs/superpowers/recherche/2026-11-17-vague-2-methodes.md`, section 6.

- Avec `datasets` 5.x, `IterableDataset.state_dict()` et `load_state_dict()` reprennent un flux au fragment près, puis à l'exemple près. Le tampon de `.shuffle()` est perdu à la reprise : il faut mélanger avant `skip` et `take`. Le flux de forge n'est pas mélangé, donc rien ne se perd.
- `datasets` 5.1 corrige plusieurs bogues de reprise. Les verrous de forge, 1.2, 1.4 et 1.5 sont en 5.1.0, celui de 1.6 en 5.2.0.

## Choix de ce plan

- **Le brouillon d'essai permanent** (m8 du plan 5) n'est pas fait. Les brouillons de 1.7 à 1.10, au plan 8, refont tourner le mécanisme dès le début de la vague 2.
- **Les bits par octet** : les nombres publiés de la Release restent tels quels, puisque `rapport.json` est un relevé daté. Un rapport corrigé s'y ajoute, et les notes de la Release ainsi que les documents du dépôt disent l'erratum. Le site affiche la valeur corrigée, pour que 1.7 et les suivants se comparent à 1.5 avec le même calcul.
- **Un téléchargement d'avant ce plan**, dont `etat.json` n'a pas l'état du flux, reprend comme avant : relecture et saut. Le message le dit.

## Contraintes globales

- **À ne jamais modifier :**
  - le tokenizer figé `projets/forge/forge/ressources/tokenizer-ton-ia-v1.json` ;
  - ce que `forge exporter` écrit pour une sauvegarde donnée : noms, formats et contenu des fichiers.
- **Langue :** noms, commentaires et messages en français. Un message d'erreur dit ce qui se passe et quoi faire ensuite.
- **Les tests d'abord :** chaque changement de comportement commence par un test rouge.
- **Commandes :**
  - dans `projets/forge`, `uv run --extra gpu pytest -q -m "not gpu"` (jamais `--extra cpu` en local : le `.venv` garde PyTorch pour la carte), et `uv run --extra gpu pytest -q -m gpu` quand la carte est libre (`nvidia-smi` sous 10 %) ;
  - avant toute commande forge : `. .\outils\env-forge.ps1` (PowerShell), ou les mêmes variables exportées sous Git Bash.
- **La carte graphique ne sert que quand elle est libre.** Au « stop » de l'utilisateur, la commande en cours finit et aucune autre ne part sur la carte avant son « go ».
- **Fichiers interdits en écriture :**
  - `D:\forge-ia-donnees\entrainements\` (hors des nouveaux dossiers d'évaluation de la tâche 2) ;
  - tout `D:\forge-ia-donnees`, sauf `cache\` et ces dossiers.
- **Commits :**
  - adresse `268342383+chipat-neko@users.noreply.github.com` ;
  - message en français qui se termine par `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` ;
  - fins de ligne LF ;
  - `git add <fichiers>` puis `git commit -m "…" -- <fichiers>`.

  Seul le contrôleur pousse.

## Points à surveiller à la relecture

1. **Reprise du flux avec un `etat.json` ancien** (sans état du flux), corrompu, ou écrit pour une autre source : l'ancienne voie se prend, ou un message clair s'affiche. Jamais de doublon ni de trou dans les fragments.
2. **Reprise d'une source épuisée** ou arrivée au plafond d'octets : rien n'est relu.
3. **Écriture atomique regroupée sous Windows** : un fichier ouvert ailleurs (antivirus, Explorateur) donne des réessais, puis un message. Un `.tmp` n'est jamais pris pour bon.
4. **Les chiffres corrigés** (bits par octet) sont les mêmes partout : rapports, fichiers du projet 1.6, chapitres 1.5 et 1.6, notes de la Release.
5. **L'export d'une sauvegarde dont le dossier de données est absent** : un avertissement s'affiche, l'export a lieu, et le message dit ce qui n'a pas pu être vérifié.

## Fichiers

- Modifier : `projets/forge/forge/donnees/telechargement.py`, `forge/__main__.py`, `forge/evaluation/perte.py`, `forge/evaluation/rapport.py`, `forge/exporter.py`, `forge/entrainement/boucle.py`, `forge/entrainement/sauvegarde.py`, `forge/entrainement/chargeur.py`, `forge/suivi.py`, `forge/mesure.py`, `forge/modele/generation.py`, `forge/tokenizer/apprentissage.py`, `forge/tokenizer/bpe_octets.py`, `forge/donnees/jetons.py`, `projets/forge/README.md`, `docs/donnees.md`
- Créer : `projets/forge/forge/fichiers.py`, `projets/forge/forge/erreurs.py`, et leurs tests
- Modifier : `docs/mesures/ton-ia-1.5.md`, `ton-ia-1.5-LISEZMOI.md`, `ton-ia-mini.md`, `projets/1.6-evaluation/mesures/*.json` (régénérés), `projets/1.4-transformer/README.md`, `projets/1.4-transformer/**/attendus.py`

---

### Tâche 1 : reprendre un téléchargement au fragment près

**Fichiers :** `forge/donnees/telechargement.py`, `tests/test_telechargement.py`, `forge/__main__.py` (message de Ctrl+C), `projets/forge/README.md`, `docs/donnees.md`.

**Interfaces :**
- `_Etat` gagne `etat_du_flux: dict | None = None` : le `state_dict()` du flux pris juste après le dernier document du dernier fragment écrit. Il est écrit dans `etat.json` en même temps que les compteurs.
- `lecteur_hugging_face(source, etat_du_flux: dict | None = None, ignorer: int = 0) -> LecteurDeFlux`. Avec `etat_du_flux`, il appelle `jeu.load_state_dict(etat_du_flux)`. Sinon, il fait `jeu.skip(ignorer)`, l'ancienne voie.
- `LecteurDeFlux` : un itérable de documents, avec `etat() -> dict | None`, qui renvoie le `state_dict()` courant, ou `None` si le jeu ne le permet pas.

- [ ] **Étape 1 : tests rouges.**
  - Un vrai flux `datasets`, sans réseau : `load_dataset("parquet", data_files=[3 petits fichiers écrits dans tmp_path], streaming=True)`. On télécharge jusqu'à un plafond, on « coupe », puis on relance. La relance ne relit aucun document déjà compté (compteur sur un lecteur espion), et les fragments sont identiques à ceux d'un téléchargement d'une traite.
  - Un `etat.json` sans `etat_du_flux` reprend par `skip`, avec le message « ancien état : le flux est relu depuis le début ».
  - Un `etat_du_flux` refusé par `load_state_dict` (autre source, autre version) : message français qui dit d'effacer `etat.json` et les fragments au-delà du dernier compté, ou de relancer en ancienne voie, sans rien écrire de faux.
- [ ] **Étape 2 : implémenter.** Le `state_dict()` se prend au moment de `valider()`, après le dernier document gardé du fragment. Les documents lus et écartés (trop courts, doublons) sont comptés comme avant.
- [ ] **Étape 3 : les textes.** Le README, `docs/donnees.md` et le message de Ctrl+C disent le vrai. La reprise repart du fichier et du groupe de lignes où le flux s'était arrêté. Un téléchargement commencé avant cette version relit le flux depuis le début (18 min pour 15,6 millions de documents, mesuré dans `docs/mesures/entrainement-2026-11.md`). `projets/forge/tests/test_donnees.py` relit `docs/donnees.md` : il doit rester vert.
- [ ] **Étape 4 : vérifier**, avec `uv run --extra gpu pytest -q -m "not gpu"`, puis committer « Forge : reprise du téléchargement au fragment près ».

### Tâche 2 : les bits par octet exacts, et la réévaluation de ton IA

**Fichiers :** `forge/evaluation/perte.py`, `forge/evaluation/rapport.py`, `tests/test_evaluation_perte.py` (ou le fichier de test existant), `docs/mesures/ton-ia-1.5.md`, `ton-ia-1.5-LISEZMOI.md`, `ton-ia-mini.md`, `projets/1.6-evaluation/mesures/` et ce qui les relit.

**Interfaces :** `lire_octets_par_jeton(dossier)` divise les octets par **tous** les jetons du corpus, `<|fin_texte|>` compris (`octets / (jetons_train + jetons_val)` dans `index.json`). La perte moyenne compte en effet aussi les positions qui prédisent `<|fin_texte|>`. La docstring et le texte de `perte.py` disent pourquoi. `octets_par_jeton` de `forge encoder`, qui mesure la compression du tokenizer, ne change pas de sens.

- [ ] **Étape 1 : test rouge.** Sur un `index.json` fabriqué, la valeur vaut `octets / (jetons_train + jetons_val)`. Sur les chiffres publiés de `docs/mesures/entrainement-2026-11.md` (38 619 056 781 octets, 8 885 708 358 jetons), les bits par octet de ton IA valent 0,803 à 10⁻³ près. Le contrôle doit se recalculer depuis ces nombres, pas être tapé en dur.
- [ ] **Étape 2 : implémenter**, puis lancer les tests.
- [ ] **Étape 3 : réévaluer, carte libre.**
  - `python -m forge evaluer --sauvegarde D:\forge-ia-donnees\entrainements\ton-ia\sauvegardes\meilleur.pt --donnees principal --sortie D:\forge-ia-donnees\entrainements\ton-ia\evaluation\meilleur-2026-11-17`.
  - La même commande pour « mini », avec ses chemins de `configs/mini.toml`, dans `evaluation\meilleur-2026-11-17`, à côté de son dossier.
  - Seuls les bits par octet doivent changer. Si un autre nombre bouge (perte, QCM, échantillons), s'arrêter et le dire.
- [ ] **Étape 4 : les documents.**
  - `docs/mesures/ton-ia-1.5.md`, `ton-ia-1.5-LISEZMOI.md` et `ton-ia-mini.md` donnent la valeur corrigée, avec une ligne « Corrigé le 17/11/2026 » qui dit l'ancienne valeur et pourquoi.
  - Les fichiers du projet 1.6 (`evaluation-1.5.json` et celui de mini) sont régénérés par leur commande (`resumer`) depuis les nouveaux rapports.
  - Les gardes `exiger` des chapitres 1.5 et 1.6 restent vertes. Si une phrase change de sens, on la récrit.
- [ ] **Étape 5 : vérifier**, avec pytest dans forge, 1.5 et 1.6, puis `npx vitest run`, `npm run build` et les parcours 1-5 et 1-6. Committer « Bits par octet exacts : réévaluation de ton IA 1.5 et de mini ».
- [ ] **Étape 6 (contrôleur) : la Release.**
  - `gh release upload ton-ia-1.5 rapport-2026-11-17.json` : le nouveau rapport, sous ce nom.
  - `gh release upload --clobber` de `LISEZMOI.md` et de `ton-ia-1.5.md`, mis à jour.
  - `gh release edit ton-ia-1.5 --notes-file LISEZMOI.md`.
  - Les fichiers de poids, `config.json`, le tokenizer et `rapport.json` ne bougent pas. Vérifier leurs empreintes avant et après.

### Tâche 3 : l'export vérifie le tokenizer de la sauvegarde

**Fichiers :** `forge/exporter.py`, `forge/entrainement/boucle.py` (ce que la sauvegarde retient), `tests/test_exporter.py`.

**Interfaces :**
- Une sauvegarde nouvelle retient `empreinte_du_tokenizer`, calculée comme `_empreinte_du_tokenizer` de `forge/donnees/jetons.py` (la même empreinte que celle d'`index.json`).
- `exporter()` compare cette empreinte à celle du tokenizer figé. Pour une ancienne sauvegarde qui ne l'a pas, il lit l'`index.json` des données de la sauvegarde (`config["donnees"]`).
- Si l'empreinte diffère, l'export refuse, avec un message qui le dit.
- Si aucune empreinte ne se trouve (dossier de données absent), l'export a lieu, avec un avertissement qui dit ce qui n'a pas été vérifié.

- [ ] **Étape 1 : tests rouges** pour les trois cas : même tokenizer ; un autre tokenizer (refus) ; aucune empreinte (avertissement, puis export). Plus un test qui vérifie que l'export de la sauvegarde d'un petit modèle reste identique à l'octet près à celui d'avant ce plan.
- [ ] **Étape 2 : implémenter, vérifier, commit** « Forge : l'export vérifie le tokenizer de la sauvegarde ».

### Tâche 4 : regrouper le code en double

**Fichiers :** `forge/fichiers.py` (nouveau), `forge/erreurs.py` (nouveau), `forge/chemins.py`, et les modules cités dans M8 et M9 de la revue finale du plan 2.

**Interfaces :**
- `forge.fichiers` :
  - `ecrire_atomique(chemin: Path, ecrire: Callable[[BinaryIO], None]) -> None` : `.tmp`, `fsync`, `remplacer`, et le `.tmp` retiré en cas d'erreur ;
  - `remplacer(source: Path, cible: Path) -> None` : les réessais de Windows ;
  - `duree(secondes: float) -> str` ;
  - `nombre(x) -> str` : les formats à la française.
- `forge.chemins.sous_forge_donnees(nom_ou_chemin: str | Path, sorte: str) -> Path` : la règle « un nom va sous `FORGE_DONNEES/<sorte>` », écrite une seule fois.
- `forge.erreurs.DonneesManquantes`, réexportée depuis `forge.tokenizer.apprentissage` pour la compatibilité.
- `forge.entrainement.sauvegarde.lire_sauvegarde`, publique. Elle remplace l'import de `_lire_sauvegarde` par `exporter.py` et l'import paresseux de `VERSION_DE_LA_SAUVEGARDE`.
- Le chargeur vérifie `VERSION_DE_L_INDEX` à la lecture, avec un message qui dit de réencoder.

- [ ] **Étape 1 : des tests qui fixent le comportement**, avant tout déplacement : écriture atomique (erreur au milieu, fichier verrouillé simulé), formats, chemins, version d'index refusée.
- [ ] **Étape 2 : déplacer**, un module à la fois. Tous les tests restent verts après chaque déplacement. Les projets 1.x importent `forge.modele`, `forge.tokenizer`, `forge.exporter`, `forge.evaluation.*` et `forge.entrainement.*` : aucun de ces imports ne casse. Vérifier avec pytest dans 1.2, 1.4, 1.5 et 1.6.
- [ ] **Étape 3 : vérifier**, avec pytest dans forge et dans les projets 1.x, et les tests `gpu` quand la carte est libre. Commit « Forge : un seul endroit pour les écritures atomiques, les chemins et les erreurs ».

### Tâche 5 : les restes

- `projets/1.4-transformer/README.md` et `attendus.py` disent « passent par », comme le chapitre 1.4, au lieu de « traversent ».
- `forge/mesure.py` : la ligne vide en trop.
- `forge encoder` : un `FileNotFoundError` sur un fragment de textes dit de relancer `forge donnees` (qui refait le fragment manquant), puis `forge encoder`.

- [ ] **Étape unique :** corriger, ajouter le test du message, vérifier, commit « Restes de la vague 1 ».

---

## Exécution

- **Modèles :**
  - tâches 1 et 4 : un modèle standard, car il faut juger sur plusieurs modules ;
  - tâches 2, 3 et 5 : le moins cher qui suffit.
- **Revue :** une relecture par tâche, et une revue finale du plan.
- **Poussée :** le contrôleur pousse après chaque tâche relue. La CI doit être verte.
