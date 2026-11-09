// Les paris du chapitre 1.5, « Le pré-entraînement sur ton GPU », et ce que le chapitre lit autour
// d'eux : les réglages des entraînements de forge (configs/*.toml), l'essai de pause et de reprise
// du projet 1.5, les lignes du tableau des sessions et de la courbe, et la réponse du défi de
// l'atelier.
//
// Leurs bonnes réponses sont calculées sur des mesures : la perte du premier pas et le débit de la
// version d'une heure (mesures/ton-ia-mini.json, lu par journal.ts), l'écart de l'essai de reprise
// (mesures/essai-processeur.json). Si une mesure change et qu'une phrase du chapitre devient
// fausse, la construction s'arrête (« Exemple devenu faux : … »).
//
// Ce module lit des fichiers avec node:fs (l'essai, les configurations), mais n'importe ni ?raw,
// ni .json, ni astro:*, ni le moteur du mini-modèle (qui lit ses prénoms en ?raw) : un parcours
// Playwright peut l'importer. Les pertes du défi, qui font tourner ce moteur, sont calculées par
// defi-1-5.ts ; la réponse se choisit ici, sur ces pertes.

import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import type { Choix } from '../choix';
import { VOCABULAIRE_FORGE } from '../calculateur/ton-ia';
import { exigeur } from '../exiger';
import { nombre } from '../nombres';
import type { CourbeEntrainement, Entrainement, FinDeSession, SessionEntrainement } from './journal';
import { MESURES_PARTIE_1 } from './mesures';

const FINE = '\u202F';

const exiger = exigeur('src/lib/partie-1/paris-1-5.ts et le texte des paris du chapitre 1.5');

/** Un chemin, une URL file: ou une chaîne file:, rendu en chemin (comme lireEntrainement). */
function enChemin(racineDepot: string | URL): string {
  return typeof racineDepot === 'string' && !racineDepot.startsWith('file:') ? racineDepot : fileURLToPath(racineDepot);
}

// ---------- Étape 2 : le pari « depart » ----------

/** La perte du premier pas doit être à moins de 0,2 de ln V, la perte du hasard. */
export const ECART_DEPART_MAX = 0.2;

/** Une tranche d'un pari : son texte, et la valeur sous laquelle elle s'arrête (non comprise). */
export interface Tranche {
  texte: string;
  jusqua: number;
}

/** Les trois tranches du pari « depart », de la perte la plus petite à la plus grande. */
export const TRANCHES_DEPART: readonly Tranche[] = Object.freeze([
  Object.freeze({ texte: 'Moins de 1', jusqua: 1 }),
  Object.freeze({ texte: 'Entre 1 et 5', jusqua: 5 }),
  Object.freeze({ texte: 'Plus de 5', jusqua: Infinity }),
]);

/** Le rang de la tranche qui contient `x` : la première dont la borne est au-dessus. */
function rangDeTranche(tranches: readonly Tranche[], x: number): number {
  const rang = tranches.findIndex((t) => x < t.jusqua);
  exiger(rang >= 0, `${String(x)} ne tombe dans aucune tranche`);
  return rang;
}

/** La tranche d'une perte : 0 sous 1, 1 de 1 (compris) à 5, 2 à partir de 5. */
export function trancheDeLaPerte(perte: number): number {
  return rangDeTranche(TRANCHES_DEPART, perte);
}

/**
 * Les faits de l'explication du pari « depart » : la perte du premier pas de mini, le hasard
 * (ln V, écrit par le projet dans la courbe) et le vocabulaire de forge. Garde : ce hasard est bien
 * ln 32 768, le nombre que le texte écrit.
 */
export function faitsDuPariDepart(mini: Entrainement): { premier: number; hasard: number; vocabulaire: number; ecart: number } {
  const premier = mini.resume.perte_premier_pas;
  const hasard = mini.courbe.hasard;
  exiger(
    Math.abs(hasard - Math.log(VOCABULAIRE_FORGE)) < 1e-12,
    `le hasard du relevé (${String(hasard)}) n’est plus ln ${VOCABULAIRE_FORGE}, le vocabulaire de forge`,
  );
  return { premier, hasard, vocabulaire: VOCABULAIRE_FORGE, ecart: premier - hasard };
}

/**
 * Le pari « Avant d'avoir rien appris, quelle perte a ton IA au premier pas ? », en trois tranches.
 * La bonne vient de la perte réelle du premier pas de mini. Garde : cette perte est à moins de 0,2
 * de ln 32 768, sinon ton IA ne partait pas du hasard, et l'explication serait fausse.
 */
export function choixPerteDepartTonIA(mini: Entrainement): Choix[] {
  const { premier, hasard, ecart } = faitsDuPariDepart(mini);
  exiger(
    Math.abs(ecart) < ECART_DEPART_MAX,
    `la perte du premier pas (${String(premier)}) s’écarte de ln V (${String(hasard)}) de ${ECART_DEPART_MAX} ou plus : ` +
      'ton IA ne partait plus du hasard',
  );
  const juste = trancheDeLaPerte(premier);
  return TRANCHES_DEPART.map((t, i) => ({ texte: t.texte, juste: i === juste }));
}

// ---------- Étape 6 : l'essai de pause et de reprise, et le pari « reprise » ----------

/** Le relevé de l'essai de pause et de reprise (mesures/essai-processeur.json du projet 1.5). */
export interface EssaiDeReprise {
  releve_le: string;
  appareil: string;
  pas_total: number;
  pas_de_la_pause: number;
  perte_un_trait: number;
  perte_reprise: number;
  ecart: number;
  pertes_identiques: boolean;
  secondes: number;
}

const REFAIRE_ESSAI =
  'Relance l’essai avec « python -m pre_entrainement essai --appareil cpu --enregistrer sorties/essai-processeur.txt ' +
  '--json mesures/essai-processeur.json » (voir le README de projets/1.5-pre-entrainement), ou corrige le fichier.';

/**
 * Vérifie qu'une valeur lue a le format du relevé de l'essai, et la rend telle quelle. Un écart
 * lève une erreur qui nomme le fichier et le champ, et dit comment refaire le relevé.
 */
export function verifierEssai(valeur: unknown, fichier: string): EssaiDeReprise {
  const faute = (quoi: string): Error => new Error(`${fichier}${FINE}: ${quoi}. ${REFAIRE_ESSAI}`);
  if (typeof valeur !== 'object' || valeur === null || Array.isArray(valeur)) throw faute('ce n’est pas un objet JSON');
  const v = valeur as Record<string, unknown>;
  if (typeof v.releve_le !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(v.releve_le)) throw faute('releve_le doit être une date AAAA-MM-JJ');
  if (typeof v.appareil !== 'string' || v.appareil === '') throw faute('appareil est vide');
  for (const cle of ['pas_total', 'pas_de_la_pause'] as const) {
    if (typeof v[cle] !== 'number' || !Number.isInteger(v[cle]) || (v[cle] as number) < 1) throw faute(`${cle} doit être un entier d’au moins 1`);
  }
  if ((v.pas_de_la_pause as number) >= (v.pas_total as number)) throw faute('pas_de_la_pause doit venir avant pas_total');
  for (const cle of ['perte_un_trait', 'perte_reprise', 'ecart', 'secondes'] as const) {
    if (typeof v[cle] !== 'number' || !Number.isFinite(v[cle]) || (v[cle] as number) < 0) throw faute(`${cle} doit être un nombre positif ou nul`);
  }
  if (v.ecart !== Math.abs((v.perte_un_trait as number) - (v.perte_reprise as number))) {
    throw faute('ecart n’est pas l’écart des deux pertes finales');
  }
  if (typeof v.pertes_identiques !== 'boolean') throw faute('pertes_identiques doit valoir true ou false');
  return valeur as EssaiDeReprise;
}

/**
 * Le relevé de l'essai sur le processeur, lu dans le dépôt dont on donne la racine (par défaut le
 * dossier au-dessus de site/, comme lireEntrainement). Il est versionné depuis le projet 1.5 : un
 * fichier absent est une erreur, pas une mesure « à faire ».
 */
export function lireEssaiDeReprise(racineDepot: string | URL = '..'): EssaiDeReprise {
  const fichier = MESURES_PARTIE_1.essaiProcesseur;
  const chemin = join(enChemin(racineDepot), fichier);
  if (!existsSync(chemin)) throw new Error(`${fichier}${FINE}: le fichier manque. ${REFAIRE_ESSAI}`);
  let valeur: unknown;
  try {
    valeur = JSON.parse(readFileSync(chemin, 'utf8'));
  } catch (erreur) {
    const raison = erreur instanceof Error ? erreur.message : String(erreur);
    throw new Error(`${fichier}${FINE}: JSON illisible (${raison}). ${REFAIRE_ESSAI}`);
  }
  return verifierEssai(valeur, fichier);
}

/** Les trois choix du pari « reprise », qui complètent « Après une pause, la perte du pas repris… ». */
export const TEXTES_REPRISE: readonly string[] = Object.freeze([
  'continue la courbe, au même nombre près',
  'repart du hasard',
  'fait un saut puis rattrape',
]);

/**
 * Le pari « Après une pause, la perte du pas repris… ». « continue la courbe, au même nombre près »
 * est juste si l'essai du processeur finit sur un écart nul. Garde : l'explication dit « au bit
 * près », pas à pas : un écart non nul, ou des pertes qui diffèrent en route, arrête la construction.
 */
export function choixReprise(essai: EssaiDeReprise): Choix[] {
  exiger(essai.ecart === 0, `l’essai de reprise finit sur un écart de ${String(essai.ecart)}, et non 0`);
  exiger(essai.pertes_identiques, 'les pertes de l’essai repris ne sont plus celles d’un trait, pas à pas');
  return TEXTES_REPRISE.map((texte, i) => ({ texte, juste: i === 0 && essai.ecart === 0 }));
}

// ---------- Étape 7 : le pari « courte », sur le débit de la version d'une heure ----------

/** Les trois tranches du pari « courte », en jetons par seconde. */
export const TRANCHES_DEBIT: readonly Tranche[] = Object.freeze([
  Object.freeze({ texte: `Moins de ${nombre(10_000)}`, jusqua: 10_000 }),
  Object.freeze({ texte: `De ${nombre(10_000)} à un million`, jusqua: 1_000_000 }),
  Object.freeze({ texte: 'Plus d’un million', jusqua: Infinity }),
]);

/** La tranche d'un débit : 0 sous 10 000 jetons par seconde, 1 jusqu'à un million, 2 au-delà. */
export function trancheDuDebit(debit: number): number {
  return rangDeTranche(TRANCHES_DEBIT, debit);
}

/**
 * Les faits de l'explication du pari « courte » : le débit moyen, les jetons lus par paramètre et
 * le lot d'un pas. Garde : le débit est bien celui des jetons lus divisés par les secondes de
 * calcul, et chaque pas a lu le même nombre de jetons.
 */
export function faitsDuPariDebit(mini: Entrainement): { debit: number; jetonsParParametre: number; lot: number } {
  const r = mini.resume;
  exiger(
    Math.abs(r.debit_moyen - r.jetons_vus / r.secondes_de_calcul) < 1e-6 * r.debit_moyen,
    'le débit moyen du relevé n’est plus les jetons lus divisés par les secondes de calcul',
  );
  const lot = r.jetons_vus / r.pas_faits;
  exiger(Number.isInteger(lot), 'les pas de la version d’une heure n’ont plus tous lu le même nombre de jetons');
  return { debit: r.debit_moyen, jetonsParParametre: r.jetons_vus / r.parametres, lot };
}

/**
 * Le pari « En moyenne, combien de jetons la version d'une heure lit-elle par seconde ? ». La bonne
 * tranche est celle du débit moyen de mini (le relevé de son journal).
 */
export function choixDebitCourte(mini: Entrainement): Choix[] {
  const { debit } = faitsDuPariDebit(mini);
  const juste = trancheDuDebit(debit);
  return TRANCHES_DEBIT.map((t, i) => ({ texte: t.texte, juste: i === juste }));
}

// ---------- Étapes 3, 5 et 8 : les réglages des entraînements de forge ----------

/** Les réglages d'un entraînement de forge que le chapitre cite, lus dans son fichier TOML. */
export interface ReglagesEntrainement {
  preset: string;
  jetons_total: number;
  taille_lot_jetons: number;
  micro_lot: number;
  taux_max: number;
  echauffement: number;
  poids_decroissance: number;
  betas: [number, number];
  ecretage: number;
  evaluation_tous_pas: number;
  /** La fin de la descente du taux, en fraction de taux_max : le défaut de taux() dans planning.py. */
  ratio_min: number;
}

/** Les configurations de forge que le chapitre lit, en chemins depuis la racine du dépôt. */
export const FICHIERS_REGLAGES = Object.freeze({
  mini: 'projets/forge/configs/mini.toml',
  principal: 'projets/forge/configs/principal.toml',
} as const);

const PLANNING = 'projets/forge/forge/entrainement/planning.py';
const ENTIERS = ['jetons_total', 'taille_lot_jetons', 'micro_lot', 'echauffement', 'evaluation_tous_pas'] as const;
const FLOTTANTS = ['taux_max', 'poids_decroissance', 'ecretage'] as const;

/**
 * Les réglages d'un fichier TOML de forge (`texte`), avec `ratioMin`, celui de planning.py. Ne lit
 * que les lignes « clé = valeur » de premier niveau : des nombres (avec ou sans « _ »), des textes
 * entre guillemets et des tableaux de nombres, comme les configurations de forge. Un réglage qui
 * manque ou ne se lit pas lève une erreur qui nomme le fichier.
 */
export function analyserReglages(texte: string, fichier: string, ratioMin: number): ReglagesEntrainement {
  const faute = (quoi: string): Error =>
    new Error(`${fichier}${FINE}: ${quoi}. Corrige le fichier : les configurations de forge sont dans projets/forge/configs/.`);
  const brut = new Map<string, string>();
  for (const ligne of texte.replace(/\r\n?/g, '\n').split('\n')) {
    const m = /^([a-z_]+)\s*=\s*([^#]*?)\s*(#.*)?$/.exec(ligne);
    if (m !== null) brut.set(m[1], m[2]);
  }
  const lire = (cle: string): string => {
    const v = brut.get(cle);
    if (v === undefined) throw faute(`le réglage ${cle} manque`);
    return v;
  };
  const nombreLu = (cle: string): number => {
    const v = lire(cle);
    const x = /^[-+]?[\d_]+(\.[\d_]+)?([eE][-+]?\d+)?$/.test(v) ? Number(v.replace(/_/g, '')) : Number.NaN;
    if (!Number.isFinite(x)) throw faute(`${cle} = ${v} n’est pas un nombre`);
    return x;
  };
  const entiers = Object.fromEntries(
    ENTIERS.map((cle) => {
      const x = nombreLu(cle);
      if (!Number.isInteger(x)) throw faute(`${cle} doit être un entier`);
      return [cle, x];
    }),
  ) as Record<(typeof ENTIERS)[number], number>;
  const flottants = Object.fromEntries(FLOTTANTS.map((cle) => [cle, nombreLu(cle)])) as Record<(typeof FLOTTANTS)[number], number>;
  const preset = /^"([^"]+)"$/.exec(lire('preset'));
  if (preset === null) throw faute('preset doit être un nom entre guillemets');
  const betas = /^\[\s*([\d.]+)\s*,\s*([\d.]+)\s*\]$/.exec(lire('betas'));
  if (betas === null) throw faute('betas doit être un tableau de deux nombres');
  return {
    preset: preset[1],
    jetons_total: entiers.jetons_total,
    taille_lot_jetons: entiers.taille_lot_jetons,
    micro_lot: entiers.micro_lot,
    taux_max: flottants.taux_max,
    echauffement: entiers.echauffement,
    poids_decroissance: flottants.poids_decroissance,
    betas: [Number(betas[1]), Number(betas[2])],
    ecretage: flottants.ecretage,
    evaluation_tous_pas: entiers.evaluation_tous_pas,
    ratio_min: ratioMin,
  };
}

/**
 * Les réglages de configs/<nom>.toml, lus dans le dépôt dont on donne la racine (par défaut le
 * dossier au-dessus de site/), avec le ratio_min par défaut de taux() (planning.py), que la boucle
 * de forge ne change pas.
 */
export function lireReglages(nom: keyof typeof FICHIERS_REGLAGES, racineDepot: string | URL = '..'): ReglagesEntrainement {
  const racine = enChemin(racineDepot);
  const fichier = FICHIERS_REGLAGES[nom];
  if (!existsSync(join(racine, fichier)) || !existsSync(join(racine, PLANNING))) {
    throw new Error(
      `La racine du dépôt donnée à lireReglages (${racine}) n’a pas ${fichier} ni ${PLANNING}. ` +
        'Donne la racine du dépôt, le dossier au-dessus de site/.',
    );
  }
  const planning = readFileSync(join(racine, PLANNING), 'utf8');
  const ratio = /def taux\([^)]*ratio_min: float = ([\d.]+)\)/.exec(planning);
  if (ratio === null) throw new Error(`${PLANNING}${FINE}: la valeur par défaut de ratio_min ne se lit plus dans taux(). Revois lireReglages.`);
  return analyserReglages(readFileSync(join(racine, fichier), 'utf8'), fichier, Number(ratio[1]));
}

/** Le module de forge qui fixe la fenêtre de la perte finale (PERTES_RECENTES), depuis la racine du dépôt. */
const SUIVI = 'projets/forge/forge/suivi.py';

/**
 * Le nombre de derniers pas dont `perte_finale` fait la moyenne : PERTES_RECENTES de forge/suivi.py, que le
 * relevé du projet 1.5 (journal.py) importe. Lu dans le dépôt dont on donne la racine, comme ratio_min dans
 * planning.py : le chapitre ne l'écrit pas à la main.
 */
export function lirePertesRecentes(racineDepot: string | URL = '..'): number {
  const chemin = join(enChemin(racineDepot), SUIVI);
  if (!existsSync(chemin)) {
    throw new Error(`La racine du dépôt donnée à lirePertesRecentes n’a pas ${SUIVI}. Donne la racine du dépôt, le dossier au-dessus de site/.`);
  }
  const m = /^PERTES_RECENTES = (\d+)$/m.exec(readFileSync(chemin, 'utf8').replace(/\r\n?/g, '\n'));
  if (m === null) throw new Error(`${SUIVI}${FINE}: PERTES_RECENTES = … ne se lit plus. Revois lirePertesRecentes.`);
  return Number(m[1]);
}

/** Le nombre de pas d'un entraînement : jetons_total divisé par le lot, arrondi au-dessus (pas_total de forge). */
export function pasTotalDesReglages(r: ReglagesEntrainement): number {
  return Math.ceil(r.jetons_total / r.taille_lot_jetons);
}

// ---------- Étapes 7 et 8 : les sessions, la courbe en tableau ----------

/**
 * Une durée de calcul : « 42 s », « 60 min 17 s » sous deux heures, puis « 135 h 2 min ». Une espace fine
 * insécable lie chaque nombre à son unité : « 60 » et « min » ne se séparent jamais en fin de ligne.
 */
export function dureeDeCalcul(secondes: number): string {
  if (!Number.isFinite(secondes) || secondes < 0) {
    throw new RangeError(`dureeDeCalcul : ${String(secondes)} n’est pas une durée. Vérifie les secondes du relevé.`);
  }
  const s = Math.round(secondes);
  if (s < 60) return `${s}${FINE}s`;
  if (s < 2 * 3600) return `${Math.floor(s / 60)}${FINE}min ${s % 60}${FINE}s`;
  return `${nombre(Math.floor(s / 3600))}${FINE}h ${Math.floor((s % 3600) / 60)}${FINE}min`;
}

/** Une ligne du tableau des sessions. */
export interface LigneDeSession {
  numero: number;
  debut: string;
  fin: string;
  pas: string;
  duree: string;
}

const DEBUTS: Readonly<Record<SessionEntrainement['depart'], string>> = Object.freeze({ debut: 'départ', reprise: 'reprise' });
const FINS: Readonly<Record<FinDeSession, string>> = Object.freeze({
  pause: 'pause',
  fin: 'fin',
  perte_non_finie: 'perte non finie',
  coupée: 'coupée',
});

/** Les lignes du tableau des sessions : une par session, dans l'ordre du journal. */
export function lignesDesSessions(sessions: readonly SessionEntrainement[]): LigneDeSession[] {
  return sessions.map((s, i) => ({
    numero: i + 1,
    debut: DEBUTS[s.depart],
    fin: FINS[s.fin],
    // Une session plantée avant son premier pas n'en a fait aucun.
    pas: s.premier_pas === null || s.dernier_pas === null ? 'aucun' : `${nombre(s.premier_pas)} à ${nombre(s.dernier_pas)}`,
    duree: dureeDeCalcul(s.secondes),
  }));
}

/**
 * Les arrêts de la courbe : la fin de chaque session sauf la dernière, au dernier pas fait jusque-là
 * (une session sans pas s'arrête là où la précédente s'était arrêtée). Rien avant le premier pas.
 */
export function arretsDeLaCourbe(sessions: readonly SessionEntrainement[]): { pas: number; fin: FinDeSession }[] {
  const arrets: { pas: number; fin: FinDeSession }[] = [];
  let dernier: number | null = null;
  sessions.forEach((s, i) => {
    if (s.dernier_pas !== null) dernier = s.dernier_pas;
    if (i < sessions.length - 1 && dernier !== null) arrets.push({ pas: dernier, fin: s.fin });
  });
  return arrets;
}

/** Une ligne du tableau qui double la courbe pour les lecteurs d'écran. */
export interface LigneDeCourbe {
  pas: number;
  /** La perte d'entraînement du paquet de pas qui contient ce pas, ou null. */
  entrainement: number | null;
  validation: number | null;
}

/**
 * Les lignes du tableau de la courbe : une par point de validation, avec la perte d'entraînement
 * du paquet qui contient son pas (les pas de 1 à taille_paquet sont dans le premier paquet).
 */
export function lignesDeLaCourbe(courbe: CourbeEntrainement): LigneDeCourbe[] {
  return courbe.validations.map(([pas, validation]) => {
    const paquet = courbe.pertes[Math.floor((pas - 1) / courbe.taille_paquet)];
    return { pas, entrainement: paquet === undefined ? null : paquet[1], validation };
  });
}

// ---------- Étape 4 : la réponse du défi de l'atelier ----------

/** Le défi : l'erreur de validation finale peut dépasser celle du taux par défaut de 0,05 au plus. */
export const ECART_DU_DEFI = 0.05;

/** L'erreur de validation au dernier pas d'un entraînement du mini-modèle, à un taux (Infinity s'il a explosé). */
export interface FinAuTaux {
  taux: number;
  fin: number;
}

/** La réponse du défi : le taux par défaut, le plus grand taux qui réussit, et le taux juste au-dessus. */
export interface ReponseDuDefi {
  defaut: FinAuTaux;
  reponse: FinAuTaux;
  suivant: FinAuTaux | null;
}

/**
 * Le plus grand taux dont l'erreur de validation finale ne dépasse pas celle du taux par défaut de
 * plus de 0,05, parmi des taux tous plus grands que lui, et le taux qui le suit. Garde : le défi
 * a une réponse au-dessus du défaut, et un taux au-delà de cette réponse, qui échoue.
 */
export function reponseDuDefi(defaut: FinAuTaux, plusGrands: readonly FinAuTaux[]): ReponseDuDefi {
  for (const f of plusGrands) {
    if (!(f.taux > defaut.taux)) {
      throw new RangeError(`reponseDuDefi : le taux ${String(f.taux)} n’est pas plus grand que celui par défaut (${String(defaut.taux)}).`);
    }
  }
  exiger(Number.isFinite(defaut.fin), 'au taux par défaut, l’erreur du mini-modèle explose');
  const ranges = [...plusGrands].sort((a, b) => a.taux - b.taux);
  let rang = -1;
  ranges.forEach((f, i) => {
    if (Number.isFinite(f.fin) && f.fin <= defaut.fin + ECART_DU_DEFI) rang = i;
  });
  exiger(rang >= 0, `aucun taux plus grand que ${String(defaut.taux)} ne finit à ${nombre(ECART_DU_DEFI, 2)} près : le défi n’a plus de réponse`);
  const suivant = ranges[rang + 1] ?? null;
  exiger(suivant !== null, `même le plus grand taux finit à ${nombre(ECART_DU_DEFI, 2)} près du défaut : le défi n’a plus de taux qui échoue`);
  return { defaut, reponse: ranges[rang], suivant };
}
