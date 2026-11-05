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

// ---------- Chapitre 0.3 : le poste, PyTorch et la carte graphique ----------
// Les extras gpu et cpu sont ceux de projets/0.3-poste/pyproject.toml :
// commandes.test.ts le vérifie.

/** Voir le pilote NVIDIA, sa version, et la plus haute version de CUDA qu'il accepte. */
export const NVIDIA_SMI = 'nvidia-smi';
/**
 * Mettre à jour le dépôt déjà cloné (au chapitre 0.1, par exemple), depuis le dossier où il a été
 * cloné : il reçoit les projets parus depuis. Le dossier visé par -C est celui que crée CLONER_DEPOT.
 */
export const METTRE_A_JOUR_DEPOT = 'git -C forge-ia pull';
/** Entrer dans le projet du chapitre 0.3, depuis le dossier où le dépôt a été cloné. */
export const ALLER_AU_PROJET_0_3 = 'cd forge-ia/projets/0.3-poste';
/** Installer la version de PyTorch pour la carte NVIDIA (CUDA 13.2), sans rien lancer. */
export const SYNC_GPU = 'uv sync --extra gpu';
/** Installer la version de PyTorch pour le processeur seul, sans rien lancer. */
export const SYNC_CPU = 'uv sync --extra cpu';
/** Vérifier son poste avec la version de PyTorch pour la carte. */
export const VERIFIER_POSTE_GPU = 'uv run --extra gpu python -m poste';
/** Vérifier son poste avec la version de PyTorch pour le processeur seul. */
export const VERIFIER_POSTE_CPU = 'uv run --extra cpu python -m poste';
/** Faire calculer les projets sur le processeur (FORGE_APPAREIL, lue par poste/appareil.py), dans PowerShell. */
export const FORCER_PROCESSEUR_POWERSHELL = '$env:FORGE_APPAREIL = "cpu"';
/** La même chose dans un terminal Linux ou macOS (bash, zsh). */
export const FORCER_PROCESSEUR_BASH = 'export FORGE_APPAREIL=cpu';

// ---------- Chapitre 0.4 : les tenseurs ----------
// Les sous-commandes formes et mesurer sont celles de
// projets/0.4-tenseurs/tenseurs/__main__.py, et les formes de TENSEURS_FORMES
// celles du départ de l'atelier : commandes.test.ts le vérifie.

/** Entrer dans le projet du chapitre 0.4, depuis le dossier où le dépôt a été cloné. */
export const ALLER_AU_PROJET_0_4 = 'cd forge-ia/projets/0.4-tenseurs';
/** Demander au script la forme de A + B et de A @ B, pour les formes du départ de l'atelier. */
export const TENSEURS_FORMES = 'uv run --extra cpu python -m tenseurs formes "(3, 1)" "(4,)"';
/**
 * Chronométrer un produit de matrices avec la version de PyTorch pour le processeur. Sans
 * --appareil, le script suit FORGE_APPAREIL, sinon « auto » : la carte si PyTorch la voit (jamais
 * avec cette version), sinon le processeur.
 */
export const TENSEURS_MESURER_CPU = 'uv run --extra cpu python -m tenseurs mesurer';
/** La même mesure avec la version pour la carte : la carte, si PyTorch la voit. */
export const TENSEURS_MESURER_GPU = 'uv run --extra gpu python -m tenseurs mesurer';

// Ce que d'anciens tutoriels font taper, et que le chapitre 0.3 cite pour dire
// pourquoi ne pas le faire. À ne pas taper : ces commandes ne sont pas
// vérifiées contre le dépôt, seulement citées.

/** Sous Windows, PyPI ne sert que la version de PyTorch pour le processeur. */
export const PIP_INSTALL_TORCH = 'pip install torch';
/** Le canal pytorch d'Anaconda s'est arrêté à PyTorch 2.5. */
export const CONDA_INSTALL_PYTORCH = 'conda install pytorch -c pytorch';
