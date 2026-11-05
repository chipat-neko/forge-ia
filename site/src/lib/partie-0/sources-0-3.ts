// Les faits de la recherche que cite le chapitre 0.3, « Installer son poste »,
// avec leurs sources : chaque lien a été relu le 5 novembre 2026, et chaque
// nombre du chapitre qui ne vient ni des attendus du projet, ni des mesures, ni
// des données du calculateur est ici, à côté de sa source.
//
// Relevé du 5 novembre 2026 :
// - Colab a changé d'image le 4 novembre 2026 (commit « Update PyTorch to 2.14.1
//   for CPU and GPU » du dépôt googlecolab/backend-info) : avec carte, Python
//   3.13.16 (os-info-gpu.txt) et torch==2.14.1+cu130 (pip-freeze.gpu.txt) ;
//   sans carte, Python 3.13.18 (os-info.txt) et torch 2.14.1+cpu
//   (pip-freeze.txt). Le dépôt ne donne ni le pilote ni la carte.
// - PyPI, torch 2.15.0 : la roue Windows cp312 pèse 126 738 207 octets, sans
//   CUDA ; pour macOS, il n'y a qu'une roue macosx_14_0_arm64 (puce Apple,
//   macOS 14 ou plus récent).
// - L'index cu132 de PyTorch : la roue torch-2.15.0+cu132-cp312-cp312-win_amd64
//   pèse 2 108 273 925 octets (en-tête Content-Length).
// - Les index pour CUDA 12 s'arrêtent avant 2.15 : la dernière roue Windows
//   cp312 de cu126 est 2.14.1, celle de cu128 2.11.0, de cu121 2.5.1, de
//   cu118 2.7.1.
//
// - Les pages de NVIDIA des cartes de l'encadré (T4, H100, livre blanc RTX
//   Blackwell, tableau 5) donnent toujours les chiffres de MATERIELS : 16 Go et
//   65 TFLOPS en FP16 pour la T4, 80 Go et 1 979 TFLOPS en bf16 avec sparsité
//   pour la H100 SXM, 16 Go et 87,9 TFLOPS en bf16 (175,8 avec sparsité) pour
//   la RTX 5070 Ti.
//
// Ce module n'importe ni ?raw, ni .json, ni astro:* (B1) : le parcours du
// chapitre l'importe pour vérifier que chaque source a son lien sur la page.

import { materiel } from '../calculateur/donnees';
import { nombre } from '../nombres';

/** Une source relue : son titre, son adresse et la date de la vérification (AAAA-MM-JJ). */
export interface SourceVerifiee {
  titre: string;
  url: string;
  verifieLe: string;
}

const VERIFIE = '2026-11-05';
/** L'espace insécable (U+00A0) entre un nombre et son unité : « 2,1 Go » ne se coupe pas en fin de ligne. */
const INSECABLE = '\u00A0';

function source(titre: string, url: string): SourceVerifiee {
  return Object.freeze({ titre, url, verifieLe: VERIFIE });
}

const PYPI_TORCH = source('PyPI, les fichiers de torch 2.15.0', 'https://pypi.org/pypi/torch/2.15.0/json');

/** Les sources du chapitre, par fait. Le chapitre les cite toutes, chacune près de son fait. */
export const SOURCES_0_3 = Object.freeze({
  /** Les versions de PyTorch pour la carte embarquent leur CUDA : le CUDA Toolkit est inutile pour s'en servir. */
  toolkit: Object.freeze([
    source(
      'Forum de PyTorch, « Is it required to set up CUDA on PC before installing CUDA enabled pytorch? », réponse 15',
      'https://discuss.pytorch.org/t/is-it-required-to-set-up-cuda-on-pc-before-installing-cuda-enabled-pytorch/60181/15',
    ),
    source(
      'Forum de PyTorch, « What is the interplay between the NVIDIA driver and CUDA? »',
      'https://discuss.pytorch.org/t/what-is-the-interplay-between-the-nvidia-driver-and-cuda/217811',
    ),
  ]),
  /** Un pilote 580 ou plus accepte toutes les versions 13 de CUDA. */
  pilote: Object.freeze([
    source(
      'NVIDIA, notes de version de CUDA 13.5, tableau 3 (compatibilité de version mineure)',
      'https://docs.nvidia.com/cuda/cuda-toolkit-release-notes/index.html',
    ),
  ]),
  /** Les capacités de calcul des cartes. */
  capacites: Object.freeze([source('NVIDIA, capacités de calcul des cartes (CUDA GPUs)', 'https://developer.nvidia.com/cuda-gpus')]),
  /** Ce qui rend faux d'anciens tutoriels : conda, les versions pour CUDA 11 et 12. */
  tutoriels: Object.freeze([
    source(
      'PyTorch, « Deprecating PyTorch’s official Anaconda channel » (issue 138506)',
      'https://github.com/pytorch/pytorch/issues/138506',
    ),
    source(
      'PyTorch, « Deprecation of Conda nightly builds » (forum des développeurs)',
      'https://dev-discuss.pytorch.org/t/pytorch-deprecation-of-conda-nightly-builds/2590',
    ),
    source('PyTorch, annonce de la version 2.7 (cartes Blackwell, CUDA 12.8)', 'https://pytorch.org/blog/pytorch-2-7/'),
    source(
      'PyTorch, annonce de la 2.15 RC1 (versions pour CUDA 13.2 et 13.4)',
      'https://dev-discuss.pytorch.org/t/pytorch-2-15-rc1-produced-for-pytorch-torchvision-torchaudio/3464',
    ),
    source('Index de PyTorch pour CUDA 12.6 (dernière version : 2.14.1)', 'https://download.pytorch.org/whl/cu126/torch/'),
  ]),
  /** Installer uv, et uv qui installe Python lui-même. */
  uv: Object.freeze([
    source('uv, installation', 'https://docs.astral.sh/uv/getting-started/installation/'),
    source('uv, installer Python', 'https://docs.astral.sh/uv/guides/install-python/'),
  ]),
  /** PyPI ne sert sous Windows que la version pour processeur ; les tailles des deux versions. */
  pypi: Object.freeze([
    source('uv, guide de PyTorch', 'https://docs.astral.sh/uv/guides/integration/pytorch/'),
    PYPI_TORCH,
    source('Index de PyTorch pour CUDA 13.2', 'https://download.pytorch.org/whl/cu132/torch/'),
  ]),
  /** Colab : son image, sa FAQ, et la carte que rapportent ses utilisateurs. */
  colab: Object.freeze([
    source('Google, image de Colab avec carte, os-info-gpu.txt', 'https://github.com/googlecolab/backend-info/blob/main/os-info-gpu.txt'),
    source('Google, image de Colab avec carte, pip-freeze.gpu.txt', 'https://github.com/googlecolab/backend-info/blob/main/pip-freeze.gpu.txt'),
    source('Google, image de Colab sans carte, pip-freeze.txt', 'https://github.com/googlecolab/backend-info/blob/main/pip-freeze.txt'),
    source('Google, FAQ de Colab', 'https://research.google.com/colaboratory/faq.html'),
    source(
      'gpuperhour, « Google Colab alternatives » (source secondaire : la T4 rapportée par les utilisateurs)',
      'https://gpuperhour.com/blog/google-colab-alternatives',
    ),
  ]),
  /** Mac : PyTorch 2.15 n'a de version que pour les puces Apple, sous macOS 14 ou plus récent. */
  mac: Object.freeze([PYPI_TORCH]),
  /** Les cartes de l'encadré : les sources de MATERIELS (calculateur/donnees.ts), relues ce jour. */
  cartes: Object.freeze(['t4', 'rtx-5070-ti', 'h100-sxm'].map((id) => source(materiel(id).source.titre, materiel(id).source.url))),
  /** Llama 3 405B, entraîné sur jusqu'à 16 384 H100. */
  llama: Object.freeze([
    source(
      'Llama Team (Meta), « The Llama 3 Herd of Models » (arXiv 2407.21783), section 3.3, tableau 4',
      'https://arxiv.org/abs/2407.21783',
    ),
  ]),
});

/** La plus ancienne série de pilotes NVIDIA qui accepte toutes les versions 13 de CUDA (SOURCES_0_3.pilote). */
export const PILOTE_MINIMUM_CUDA_13 = 580;

/** La taille de torch-2.15.0-cp312-cp312-win_amd64.whl sur PyPI, sans CUDA, en octets (SOURCES_0_3.pypi). */
export const OCTETS_ROUE_PYPI_WINDOWS = 126_738_207;

/** La taille de torch-2.15.0+cu132-cp312-cp312-win_amd64.whl, CUDA 13.2 compris, en octets (SOURCES_0_3.pypi). */
export const OCTETS_ROUE_CU132_WINDOWS = 2_108_273_925;

/** Des octets en Mo décimaux (10⁶ octets, comme PyPI), une décimale, l'unité insécable : « 126,7 Mo ». */
export function enMo(octets: number): string {
  return `${nombre(octets / 1e6, 1)}${INSECABLE}Mo`;
}

/** Des octets en Go décimaux (10⁹ octets), une décimale : « 2,1 Go ». */
export function enGo(octets: number): string {
  return `${nombre(octets / 1e9, 1)}${INSECABLE}Go`;
}

/** Les capacités de calcul que le chapitre cite, d'après NVIDIA (SOURCES_0_3.capacites). */
export const CAPACITES: Readonly<Record<'RTX 5070 Ti' | 'T4' | 'RTX 4070' | 'H100', readonly [number, number]>> = Object.freeze({
  'RTX 5070 Ti': Object.freeze([12, 0] as const),
  T4: Object.freeze([7, 5] as const),
  'RTX 4070': Object.freeze([8, 9] as const),
  H100: Object.freeze([9, 0] as const),
});

/** Colab au 5 novembre 2026 : ses deux images, et la durée la plus longue d'une session (SOURCES_0_3.colab). */
export const COLAB = Object.freeze({
  avecCarte: Object.freeze({ python: '3.13.16', torch: '2.14.1+cu130' }),
  sansCarte: Object.freeze({ python: '3.13.18', torch: '2.14.1+cpu' }),
  /** « at most 12 hours », d'après la FAQ. */
  heuresMax: 12,
});

/** La plus ancienne version de macOS pour laquelle PyTorch 2.15 publie une version, sur puce Apple (SOURCES_0_3.mac). */
export const MACOS_MINIMUM = '14';

/** Le plus grand nombre de cartes H100 de l'entraînement de Llama 3 405B (SOURCES_0_3.llama, tableau 4). */
export const CARTES_LLAMA_3_405B = 16_384;
