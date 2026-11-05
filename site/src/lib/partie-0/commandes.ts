// Les commandes d'une ligne que les chapitres de la Partie 0 font taper au
// lecteur. Un chapitre ne les écrit jamais lui-même : il les importe d'ici et
// les montre avec BlocCommande. commandes.test.ts les vérifie contre le dépôt
// (adresse, dossiers, modules lancés par python -m).
//
// Sources des commandes d'installation d'uv, relevées le 04/11/2026 :
// https://docs.astral.sh/uv/getting-started/installation/

import { DEPOT } from '../depot';

/** Installer uv sous Windows, dans PowerShell. */
export const INSTALLER_UV_WINDOWS = 'powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"';
/** Installer uv sous Windows avec winget. */
export const INSTALLER_UV_WINGET = 'winget install --id=astral-sh.uv -e';
/** Installer uv sous Linux ou macOS, dans un terminal. */
export const INSTALLER_UV_LINUX_MAC = 'curl -LsSf https://astral.sh/uv/install.sh | sh';
/** Vérifier qu'uv répond : il affiche sa version. */
export const VERIFIER_UV = 'uv --version';

/** Télécharger le dépôt du site, avec tous ses projets. */
export const CLONER_DEPOT = `git clone ${DEPOT}`;

/** Entrer dans le projet du chapitre 0.1, depuis le dossier où le dépôt a été cloné. */
export const ALLER_AU_PROJET_0_1 = 'cd forge-ia/projets/0.1-python';
/** Lancer le programme du mot suivant, en partant de « le ». */
export const LANCER_MOT_SUIVANT = 'uv run python -m mot_suivant le';
/** Lancer les tests d'un projet, depuis son dossier. */
export const LANCER_TESTS = 'uv run pytest';
