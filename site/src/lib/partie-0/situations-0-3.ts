// Ce que le chapitre 0.3, « Installer son poste », lit du diagnostic de son
// projet : les situations nommées de projets/0.3-poste (SITUATIONS, dans
// poste/diagnostic.py), avec leurs faits et leurs constats, telles que le
// Python les écrit dans tests/attendus.json. Le chapitre ne refait pas le
// diagnostic (choix 9 et 12 du plan) : il lit ces constats et les met en page.
//
// Ce module n'importe ni ?raw, ni .json, ni astro:* (B1) : ses fonctions
// reçoivent les attendus en argument. poste.ts les lie au fichier du projet
// pour le chapitre et pour Vitest ; le parcours du chapitre lit le fichier sur
// le disque.

import { typographier } from '../typo';
import { PIP_INSTALL_TORCH } from './commandes';

const FINE = '\u202F';

/** Le fichier d'attendus du diagnostic, depuis la racine du dépôt. */
export const FICHIER_ATTENDUS_POSTE = 'projets/0.3-poste/tests/attendus.json';

/** Le niveau d'un constat, tel que le Python l'écrit dans les attendus (Niveau, dans diagnostic.py). */
export type Niveau = 'bon' | 'attention' | 'probleme';

/** Les faits d'un poste (Faits, dans poste/faits.py). `null` veut dire « absent ». */
export interface FaitsPoste {
  systeme: string;
  python: string;
  torch: string | null;
  cuda_compilee: string | null;
  cuda_disponible: boolean;
  carte: string | null;
  capacite: [number, number] | null;
  architectures: string[];
  pilote: string | null;
  cuda_max_pilote: string | null;
  fils_processeur: number;
  fils_torch: number;
}

/** Un constat du diagnostic (Constat, dans diagnostic.py). */
export interface Constat {
  niveau: Niveau;
  cle: string;
  message: string;
  a_faire: string | null;
}

/** Une situation : ses faits, et les constats que le diagnostic en tire. */
export interface Situation {
  faits: FaitsPoste;
  constats: Constat[];
}

/** Le fichier d'attendus : les situations dans l'ordre de SITUATIONS, en paires [nom, situation]. */
export interface AttendusPoste {
  situations: [string, Situation][];
}

/** Les situations du chapitre, dans l'ordre de SITUATIONS (poste/diagnostic.py) et des attendus. */
export const NOMS_DES_SITUATIONS = Object.freeze([
  'windows_cu132_rtx5070ti',
  'windows_pypi_rtx5070ti',
  'windows_cu126_rtx5070ti',
  'pilote_ancien',
  'sans_carte',
  'colab_t4',
  'fils_par_defaut',
] as const);

/**
 * La situation `nom` des attendus. Un nom absent lève une erreur qui donne
 * les noms présents et dit quoi faire.
 */
export function trouverSituation(attendus: AttendusPoste, nom: string): Situation {
  const trouvee = attendus.situations.find(([n]) => n === nom);
  if (trouvee === undefined) {
    const noms = attendus.situations.map(([n]) => n).join(', ') || '(aucune)';
    throw new Error(
      `La situation «${FINE}${nom}${FINE}» n’est pas dans ${FICHIER_ATTENDUS_POSTE}. Les situations sont${FINE}: ${noms}. ` +
        'Vérifie le nom, ou ajoute la situation à SITUATIONS (projets/0.3-poste/poste/diagnostic.py), puis régénère ' +
        `les attendus${FINE}: uv run --extra cpu python -m poste.attendus, dans projets/0.3-poste.`,
    );
  }
  return trouvee[1];
}

/** Le niveau tel que le rapport l'affiche (LIBELLES, dans diagnostic.py). */
export const LIBELLES_NIVEAUX: Readonly<Record<Niveau, string>> = Object.freeze({
  bon: 'bon',
  attention: 'attention',
  probleme: 'problème',
});

/**
 * La ligne du rapport de `python -m poste` pour un constat, comme l'écrit
 * decrire_constat (diagnostic.py) : « ··bon : PyTorch … ». Vitest vérifie
 * qu'une ligne ainsi écrite est bien dans la sortie enregistrée sur ce PC.
 */
export function ligneDuRapport(c: Constat): string {
  return `  ${LIBELLES_NIVEAUX[c.niveau]}${FINE}: ${c.message}`;
}

/**
 * Toutes les lignes du rapport pour un constat, comme decrire_constat : la
 * ligne du constat, puis « À faire : … » quand il y a quelque chose à faire.
 * Les commandes gardent leurs accents graves, comme dans le terminal.
 */
export function lignesDuRapport(c: Constat): string[] {
  return c.a_faire ? [ligneDuRapport(c), `    À faire${FINE}: ${c.a_faire}`] : [ligneDuRapport(c)];
}

/**
 * Les constats du diagnostic qu'aucune situation du tableau ne montre, dans
 * l'ordre de diagnostiquer, avec ce que la note de l'étape 6 en dit. Vitest
 * vérifie qu'avec les constats du tableau, ils font exactement ceux de
 * diagnostic.py.
 */
export const CONSTATS_HORS_TABLEAU: readonly { cle: string; description: string }[] = Object.freeze([
  { cle: 'torch_absent', description: "un PyTorch qui ne s'importe pas" },
  { cle: 'pilote_absent', description: 'une version pour la carte sans pilote' },
  { cle: 'carte_trop_ancienne', description: 'une carte trop ancienne pour la version du projet' },
  { cle: 'carte_invisible', description: 'une carte que PyTorch ne voit pas' },
]);

// ---------- Le texte et le code ----------

/** Un morceau de texte : du code (entre accents graves dans la source), ou du texte typographié. */
export interface Morceau {
  texte: string;
  code: boolean;
}

/**
 * Un texte découpé en morceaux : ce qui est entre accents graves est du code,
 * gardé tel quel ; le reste est typographié (typographier). Les morceaux vides
 * sont retirés.
 */
export function morceaux(texte: string): Morceau[] {
  return texte
    .split('`')
    .map((t, i) => ({ texte: i % 2 === 1 ? t : typographier(t), code: i % 2 === 1 }))
    .filter((m) => m.texte !== '');
}

/** Le texte affiché par des morceaux, code compris, sans les accents graves. */
export function texteDesMorceaux(m: readonly Morceau[]): string {
  return m.map((x) => x.texte).join('');
}

// ---------- Le tableau des situations ----------

/** Ce que la colonne « Ce qu'il faut faire » écrit pour un constat sans rien à faire. */
export const RIEN_A_FAIRE = 'Rien à faire.';

/** Le nom de la carte sans la marque : « NVIDIA GeForce RTX 5070 Ti » donne « RTX 5070 Ti ». */
function nomCourt(carte: string | null): string {
  return (carte ?? 'carte').replace(/^NVIDIA\s+/, '').replace(/^GeForce\s+/, '');
}

/**
 * Comment le tableau décrit chaque situation, d'après ses faits : les versions
 * et les cartes sont lues dans les faits, jamais recopiées. La situation de
 * Colab ne nomme ni le pilote ni les fils : ce sont des exemples, que le dépôt
 * de l'image de Colab ne donne pas (voir colab_t4 dans diagnostic.py). Sa
 * carte, la T4, est celle que rapportent ses utilisateurs : Google ne la nomme
 * pas, et la ligne le dit.
 */
const DESCRIPTIONS: Readonly<Record<string, (f: FaitsPoste) => string>> = Object.freeze({
  windows_cu132_rtx5070ti: (f) => `${f.systeme}, ${nomCourt(f.carte)}, PyTorch ${f.torch} (la version du projet)`,
  windows_pypi_rtx5070ti: (f) => `La même carte, avec \`${PIP_INSTALL_TORCH}\`, qui donne PyTorch ${f.torch}`,
  windows_cu126_rtx5070ti: (f) => `La même carte, avec PyTorch ${f.torch}, d'un ancien tutoriel`,
  pilote_ancien: (f) => `Un pilote ${f.pilote}, qui va jusqu'à CUDA ${f.cuda_max_pilote}`,
  sans_carte: (f) => `Un PC sans carte NVIDIA, avec PyTorch ${f.torch}`,
  colab_t4: (f) => `Colab, avec la ${f.carte} que rapportent ses utilisateurs, et son PyTorch ${f.torch}`,
  fils_par_defaut: (f) => `La ${nomCourt(f.carte)} prête, mais PyTorch réglé par défaut`,
});

/** La description d'une situation pour le tableau, en morceaux. Un nom sans description lève une erreur. */
export function decrireSituation(nom: string, faits: FaitsPoste): Morceau[] {
  const decrire = DESCRIPTIONS[nom];
  if (decrire === undefined) {
    throw new Error(
      `La situation «${FINE}${nom}${FINE}» n’a pas de description pour le tableau du chapitre 0.3${FINE}: ` +
        'ajoute-la dans DESCRIPTIONS (src/lib/partie-0/situations-0-3.ts).',
    );
  }
  return morceaux(decrire(faits));
}

/** Un constat tel que le tableau le montre. */
export interface ConstatAffiche {
  cle: string;
  /** Le niveau, tel que le rapport l'écrit : « bon », « attention », « problème ». */
  niveau: string;
  message: Morceau[];
  /** Ce qu'il faut faire, ou RIEN_A_FAIRE. */
  aFaire: Morceau[];
}

/** Une ligne du tableau des situations. */
export interface LigneSituation {
  nom: string;
  situation: Morceau[];
  constats: ConstatAffiche[];
}

/** Les lignes du tableau des situations, dans l'ordre des attendus : rien n'est recalculé. */
export function lignesDesSituations(attendus: AttendusPoste): LigneSituation[] {
  return attendus.situations.map(([nom, { faits, constats }]) => ({
    nom,
    situation: decrireSituation(nom, faits),
    constats: constats.map((c) => ({
      cle: c.cle,
      niveau: LIBELLES_NIVEAUX[c.niveau],
      message: morceaux(c.message),
      aFaire: morceaux(c.a_faire ?? RIEN_A_FAIRE),
    })),
  }));
}

// ---------- Les générations de cartes ----------

/** Le nom d'architecture d'une capacité de calcul : (12, 0) donne « sm_120 », (7, 5) « sm_75 ». */
export function nomArchitecture([majeure, mineure]: readonly [number, number]): string {
  return `sm_${majeure}${mineure}`;
}

/** « sm_86 » donne ["sm", 8, 6] ; « sm_90a » ["sm", 9, 0] ; null pour un nom illisible (architecture, dans diagnostic.py). */
function lireArchitecture(nom: string): [string, number, number] | null {
  const [genre, ...reste] = nom.split('_');
  const chiffres = reste.join('_').replace(/a$/, '').replace(/f$/, '');
  if ((genre !== 'sm' && genre !== 'compute') || !/^\d+$/.test(chiffres)) return null;
  const n = Number(chiffres);
  return [genre, Math.floor(n / 10), n % 10];
}

/** La capacité d'une architecture « sm_XY » ou « compute_XY » : « sm_90 » donne (9, 0) ; null pour un nom illisible. */
export function capaciteArchitecture(nom: string): [number, number] | null {
  const lue = lireArchitecture(nom);
  return lue === null ? null : [lue[1], lue[2]];
}

/**
 * L'architecture de la liste qui sert une carte de cette capacité, ou null : un
 * « sm_XY » de la même génération X et de mineure Y plus petite ou égale (le
 * plus proche), sinon un « compute_XY » de capacité plus petite ou égale. C'est
 * la règle de carte_connue (diagnostic.py), qui sert ici à écrire l'exemple du
 * chapitre ; Vitest vérifie qu'elle dit la même chose que les attendus.
 */
export function architectureQuiSert(capacite: readonly [number, number], architectures: readonly string[]): string | null {
  const [generation, mineure] = capacite;
  let meilleure: { nom: string; mineure: number } | null = null;
  for (const nom of architectures) {
    const lue = lireArchitecture(nom);
    if (lue === null || lue[0] !== 'sm' || lue[1] !== generation || lue[2] > mineure) continue;
    if (meilleure === null || lue[2] > meilleure.mineure) meilleure = { nom, mineure: lue[2] };
  }
  if (meilleure !== null) return meilleure.nom;
  for (const nom of architectures) {
    const lue = lireArchitecture(nom);
    if (lue !== null && lue[0] === 'compute' && (lue[1] < generation || (lue[1] === generation && lue[2] <= mineure))) return nom;
  }
  return null;
}
