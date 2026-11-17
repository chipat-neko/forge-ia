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
// (--extra cpu), qui suffit à tout ce qu'il calcule, y compris l'essai. Seul le même essai sur la
// carte graphique de l'auteur prend la version pour la carte (--extra gpu).

/** Entrer dans le projet du chapitre 1.5, depuis le dossier où le dépôt a été cloné. */
export const ALLER_AU_PROJET_1_5 = 'cd forge-ia/projets/1.5-pre-entrainement';
/** L'essai de pause et de reprise exacte sur le processeur : la commande qui a écrit la sortie montrée par le chapitre. */
export const PRE_ENTRAINEMENT_ESSAI =
  'uv run --extra cpu python -m pre_entrainement essai --appareil cpu --enregistrer sorties/essai-processeur.txt --json mesures/essai-processeur.json';
/** Le même essai sur la carte graphique (NVIDIA) : la commande qui a écrit la sortie de la carte de l'auteur. */
export const PRE_ENTRAINEMENT_ESSAI_CARTE =
  'uv run --extra gpu python -m pre_entrainement essai --appareil cuda --enregistrer sorties/essai-rtx-5070-ti.txt --json mesures/essai-rtx-5070-ti.json';
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

// ---------- Chapitre 1.6 : l'évaluation, avec la version d'une heure ----------
// Les sous-commandes resumer et qcm-exemples, et leurs options, sont celles de
// projets/1.6-evaluation/evaluation_pas_a_pas/__main__.py ; ces commandes sont celles du README
// du projet, et elles écrivent les relevés que lit le chapitre (FICHIERS_EVALUATION, FICHIERS_QCM
// d'evaluation.ts) : commandes.test.ts le vérifie. Les deux premières visent le rapport et la
// sauvegarde du dernier pas de la version d'une heure, sur le PC de l'auteur (chemins D:\). Le
// rapport est celui de la réévaluation du 17/11/2026, aux bits par octet exacts : son dossier
// s'appelle meilleur-2026-11-17, mais il évalue bien etape-0006370.pt, le dernier pas.

/** Entrer dans le projet du chapitre 1.6, depuis le dossier où le dépôt a été cloné. */
export const ALLER_AU_PROJET_1_6 = 'cd forge-ia/projets/1.6-evaluation';
/** Le relevé du rapport d'évaluation de la version d'une heure : la commande qui a écrit mesures/evaluation-mini.json. */
export const EVALUATION_RESUMER =
  'uv run --extra cpu python -m evaluation_pas_a_pas resumer --rapport D:\\forge-ia-donnees\\entrainements\\ton-ia-mini\\evaluation\\meilleur-2026-11-17\\rapport.json --json mesures/evaluation-mini.json';
/** Six questions de MMMLU notées par la version d'une heure, sur le processeur : la commande qui a écrit mesures/qcm-mini.json. */
export const EVALUATION_QCM =
  'uv run --extra cpu python -m evaluation_pas_a_pas qcm-exemples --sauvegarde D:\\forge-ia-donnees\\entrainements\\ton-ia-mini\\sauvegardes\\etape-0006370.pt --appareil cpu --json mesures/qcm-mini.json';
/** Lancer les tests du projet 1.6, avec la version de PyTorch pour le processeur. */
export const EVALUATION_TESTS = 'uv run --extra cpu pytest -q';

// ---------- Ton IA, la vraie (la version publiée ton-ia-1.5), dans le projet 1.6 ----------
// Le téléchargement de la version publiée sur GitHub (avec l'outil gh), puis les commandes qui ont écrit
// ses relevés : son rapport d'évaluation et ses six questions de MMMLU (chapitre 1.6, étape 8), ses
// cartes d'attention (chapitre 1.4, étape 5) et ses jetons suivants (chapitre 1.1, étape 9). Ce sont
// celles du README du projet 1.6, et elles écrivent les fichiers que lisent ces chapitres
// (FICHIERS_EVALUATION, FICHIERS_QCM et FICHIERS_SORTIES_TON_IA d'evaluation.ts) : commandes.test.ts le
// vérifie. Le dossier D:\forge-ia-donnees\cache\ton-ia-1.5 est celui du PC de l'auteur. Le chapitre 1.6
// les montre à son étape 10 ; les chapitres 1.1 et 1.4 y renvoient.

/** Télécharger tous les fichiers de la version publiée (dont les poids, leur configuration, le tokenizer et les rapports d'évaluation) dans un dossier. */
export const TELECHARGER_TON_IA = 'gh release download ton-ia-1.5 --dir D:\\forge-ia-donnees\\cache\\ton-ia-1.5';
/** Le relevé du rapport d'évaluation corrigé du 17/11/2026 (bits par octet exacts), joint à la version, sous le nom de la version : mesures/evaluation-1.5.json. */
export const EVALUATION_RESUMER_TON_IA =
  'uv run --extra cpu python -m evaluation_pas_a_pas resumer --rapport D:\\forge-ia-donnees\\cache\\ton-ia-1.5\\rapport-2026-11-17.json --nom ton-ia-1.5 --json mesures/evaluation-1.5.json';
/** Les six mêmes questions de MMMLU, notées par ton IA sur le processeur : mesures/qcm-1.5.json. */
export const EVALUATION_QCM_TON_IA =
  'uv run --extra cpu python -m evaluation_pas_a_pas qcm-exemples --modele D:\\forge-ia-donnees\\cache\\ton-ia-1.5 --appareil cpu --json mesures/qcm-1.5.json';
/** Ses cartes d'attention pour la phrase de l'exemple du chapitre 1.4, le bloc et les deux têtes choisis par --choisir. */
export const EVALUATION_CARTES_TON_IA =
  'uv run --extra cpu python -m evaluation_pas_a_pas cartes --modele D:\\forge-ia-donnees\\cache\\ton-ia-1.5 --phrase "Le forgeron chauffe le fer puis il le tord." --choisir --appareil cpu --json sorties/cartes-ton-ia.json';
/** Les dix jetons qu'elle juge les plus probables après le départ de l'atelier du chapitre 1.1, suivi de « le ». */
export const EVALUATION_SUIVANTS_TON_IA =
  'uv run --extra cpu python -m evaluation_pas_a_pas suivants --modele D:\\forge-ia-donnees\\cache\\ton-ia-1.5 --phrase "Le forgeron frappe le" --appareil cpu --json sorties/ton-ia-suivants.json';
