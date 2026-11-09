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
