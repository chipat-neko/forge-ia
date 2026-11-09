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
