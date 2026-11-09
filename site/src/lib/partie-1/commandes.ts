// Les commandes d'une ligne que les chapitres de la Partie 1 font taper au
// lecteur, sur le modèle de partie-0/commandes.ts : un chapitre ne les écrit
// jamais lui-même, il les importe d'ici et les montre avec BlocCommande (ou
// RecupererProjet pour l'entrée dans le projet). commandes.test.ts les vérifie
// contre le dépôt : chaque dossier visé par un cd existe, chaque module lancé
// par python -m a son __main__.py dans un projet de la Partie 1 ou dans forge.
//
// Le téléchargement et la mise à jour du dépôt, et le lancement des tests
// (uv run pytest), sont ceux de la Partie 0 : partie-0/commandes.ts.

// ---------- Chapitre 1.1 : le modèle de langage à n-grammes ----------
// La sous-commande suite et ses options sont celles de
// projets/1.1-modele-de-langage/modele_de_langage/__main__.py, et ces deux
// commandes sont celles du README du projet : commandes.test.ts le vérifie.

/** Entrer dans le projet du chapitre 1.1, depuis le dossier où le dépôt a été cloné. */
export const ALLER_AU_PROJET_1_1 = 'cd forge-ia/projets/1.1-modele-de-langage';
/** Écrire 200 caractères à la suite de « Le forgeron », avec 4 caractères de contexte, à la température 1. */
export const MODELE_SUITE = 'uv run python -m modele_de_langage suite --n 4 --temperature 1 --graine 0 "Le forgeron "';

// ---------- Chapitre 1.2 : les données pas à pas ----------
// Les sous-commandes trier et apercu, et leurs options, sont celles de
// projets/1.2-donnees/donnees_pas_a_pas/__main__.py ; ces trois commandes sont
// celles du README du projet, et l'aperçu écrit les fichiers de MESURES_PARTIE_1 :
// commandes.test.ts le vérifie.

/** Entrer dans le projet du chapitre 1.2, depuis le dossier où le dépôt a été cloné. */
export const ALLER_AU_PROJET_1_2 = 'cd forge-ia/projets/1.2-donnees';
/** Un verdict par document des exemples du web : gardé, trop court ou doublon. */
export const DONNEES_TRIER = 'uv run python -m donnees_pas_a_pas trier exemples/web.jsonl';
/** L'aperçu des trois sources, lu en flux sur Hugging Face : la commande qui a écrit la sortie montrée par le chapitre. */
export const DONNEES_APERCU =
  'uv run python -m donnees_pas_a_pas apercu --octets 5M --enregistrer sorties/apercu.txt --json mesures/apercu.json';

// ---------- Chapitre 1.4 : le transformer pièce par pièce ----------
// Les sous-commandes comparer et compter, et leurs options, sont celles de
// projets/1.4-transformer/transformer_pas_a_pas/__main__.py ; ces commandes sont
// celles du README du projet, et comparer écrit la sortie de MESURES_PARTIE_1 :
// commandes.test.ts le vérifie. Le projet utilise PyTorch : ses commandes
// prennent la version pour le processeur (--extra cpu), qui suffit à tous ses
// calculs.

/** Entrer dans le projet du chapitre 1.4, depuis le dossier où le dépôt a été cloné. */
export const ALLER_AU_PROJET_1_4 = 'cd forge-ia/projets/1.4-transformer';
/** Comparer chaque pièce refaite à forge, et enregistrer la sortie : la commande qui a écrit la sortie montrée par le chapitre. */
export const TRANSFORMER_COMPARER = 'uv run --extra cpu python -m transformer_pas_a_pas comparer --enregistrer sorties/comparaison.txt';
/** Les paramètres de ton IA dans sa plus grande taille, famille par famille. */
export const TRANSFORMER_COMPTER = 'uv run --extra cpu python -m transformer_pas_a_pas compter --preset tres_grand';
/** Lancer les tests du projet 1.4, avec la version de PyTorch pour le processeur. */
export const TRANSFORMER_TESTS = 'uv run --extra cpu pytest -q';

// ---------- Chapitre 1.5 : le pré-entraînement, avec la version d'une heure ----------
// Les sous-commandes courbe et essai, et leurs options, sont celles de
// projets/1.5-pre-entrainement/pre_entrainement/__main__.py ; ces commandes sont celles
// du README du projet, et elles écrivent les fichiers de MESURES_PARTIE_1 : commandes.test.ts
// le vérifie. Le projet utilise PyTorch : ses commandes prennent la version pour le processeur
// (--extra cpu), qui suffit à tout ce qu'il calcule, y compris l'essai.

/** Entrer dans le projet du chapitre 1.5, depuis le dossier où le dépôt a été cloné. */
export const ALLER_AU_PROJET_1_5 = 'cd forge-ia/projets/1.5-pre-entrainement';
/** L'essai de pause et de reprise exacte sur le processeur : la commande qui a écrit la sortie montrée par le chapitre. */
export const PRE_ENTRAINEMENT_ESSAI =
  'uv run --extra cpu python -m pre_entrainement essai --appareil cpu --enregistrer sorties/essai-processeur.txt --json mesures/essai-processeur.json';
/** Les courbes et les sessions du journal de la version d'une heure : la commande qui a écrit mesures/ton-ia-mini.json. */
export const PRE_ENTRAINEMENT_COURBE =
  'uv run --extra cpu python -m pre_entrainement courbe --journal D:\\forge-ia-donnees\\entrainements\\ton-ia-mini\\journal.jsonl --config ..\\forge\\configs\\mini.toml --json mesures/ton-ia-mini.json';
/** Lancer les tests du projet 1.5, avec la version de PyTorch pour le processeur. */
export const PRE_ENTRAINEMENT_TESTS = 'uv run --extra cpu pytest -q';

// La version d'une heure de ton IA (le modèle « mini ») : les lignes `python -m forge …` de
// docs/mesures/ton-ia-mini.md, « Les commandes, dans l'ordre », avec le préfixe que le README de forge
// leur met (`uv run --extra gpu `, la carte graphique). Elles se lancent depuis projets/forge, après
// `. .\outils\env-forge.ps1` à la racine du dépôt. commandes.test.ts les cherche telles quelles dans ces
// deux documents. Les tableaux ne sont pas des commandes d'une ligne : chaque élément l'est.

/** Télécharger 1 000 Mo de texte (75 % de français du web, 10 % de Wikipédia, 15 % de code Python). */
export const COURT_DONNEES = 'uv run --extra gpu python -m forge donnees --octets 1000M --dossier court';
/** Encoder ces textes avec le tokenizer figé de ton IA. */
export const COURT_ENCODER =
  'uv run --extra gpu python -m forge encoder --donnees court --tokenizer forge\\ressources\\tokenizer-ton-ia-v1.json';
/** Entraîner « mini » pendant environ une heure sur la carte graphique. */
export const COURT_ENTRAINER = 'uv run --extra gpu python -m forge entrainer --config configs/mini.toml';
/** Évaluer la sauvegarde du dernier pas (6 370). */
export const COURT_EVALUER =
  'uv run --extra gpu python -m forge evaluer --sauvegarde D:\\forge-ia-donnees\\entrainements\\ton-ia-mini\\sauvegardes\\etape-0006370.pt --donnees court';
/** La suite des commandes de la version courte, dans l'ordre : donnees, encoder, entrainer, evaluer. */
export const ENTRAINER_COURT: readonly string[] = Object.freeze([COURT_DONNEES, COURT_ENCODER, COURT_ENTRAINER, COURT_EVALUER]);

/** Ce que fait Ctrl+C pendant l'entraînement : le pas en cours se termine, puis tout est sauvegardé. */
export const PAUSE = 'Ctrl+C met en pause';
/** Reprendre exactement là où la pause s'est arrêtée : la commande d'entraînement, avec `--reprendre`. */
export const REPRENDRE = 'uv run --extra gpu python -m forge entrainer --config configs/mini.toml --reprendre';
