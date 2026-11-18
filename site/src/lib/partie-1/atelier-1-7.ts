// Ce que les îlots du chapitre 1.7, « Apprendre à converser », calculent dans le navigateur : l'atelier
// du masque (AtelierConversation.svelte) et la phrase de la figure de l'empaquetage
// (FigureEmpaquetage.svelte).
//
// L'atelier part des six conversations de référence du projet 1.7 (projets/1.7-conversation/tests/
// attendus.json, section « conversations »), dont le Python a encodé chaque texte. Le lecteur en choisit
// une, et deux bascules lui ajoutent ou lui retirent un message système et un deuxième tour (une autre
// question, et sa réponse). Les tours ainsi composés passent par le jumeau d'encoder_conversation
// (assemblerConversation, conversation.ts) : la page montre ses jetons, son masque et son compte. Le
// navigateur n'a pas le tokenizer : il n'encode aucun texte, il assemble des textes déjà encodés.
//
// Le jumeau ne refait pas `texte.strip()` de Python : il ne voit que des ids, et refuse seulement un texte
// sans jeton. Avant de lui passer des tours, la page refuse donc elle-même un texte vide ou fait de blancs
// (les blancs de str.isspace(), BLANCS_PYTHON), avec le message de verifier_conversation
// (refuserLesTextesBlancs). Les textes de l'atelier sont ceux des attendus ; si un jour le lecteur en
// tape un, la règle de Python tient déjà.
//
// Ce module n'importe que des modules sans node:fs, ni .json, ni astro:* : les îlots, dans le navigateur, et
// les parcours Playwright peuvent l'importer. Les fichiers sont lus par paris-1-7.ts, à la construction.

import { nombre, pourcent } from '../nombres';
import { assemblerConversation, PREMIER_SPECIAL, type Role, type TourEncode } from './conversation';
import { BLANCS_PYTHON } from './nettoyeur';

const FINE = '\u202F';

// ---------- Les conversations de référence (attendus du projet 1.7) ----------

/** Un tour d'une conversation de référence : son texte, et les ids que le tokenizer de ton IA en a tirés. */
export interface TourDeReference {
  role: Role;
  texte: string;
  ids: number[];
  pensee?: string;
  pensee_ids?: number[];
}

/** Une conversation de référence, telle que le Python l'a écrite : ses tours, et ce que forge en a fait. */
export interface ConversationDeReference {
  nom: string;
  tours: TourDeReference[];
  /** Les ids assemblés par encoder_conversation, ou null si forge refuse la conversation. */
  ids: number[] | null;
  appris: boolean[] | null;
  /** Le message de l'erreur de forge, ou null. */
  erreur: string | null;
}

/** Les six conversations de l'atelier, dans l'ordre des attendus. */
export const NOMS_DE_L_ATELIER = Object.freeze([
  'avec-systeme',
  'sans-systeme',
  'deux-tours',
  'faux-special',
  'pensee',
  'reponse-vide',
] as const);

export type NomDeConversation = (typeof NOMS_DE_L_ATELIER)[number];

/** Le nom de chaque conversation dans la phrase de l'atelier : « La conversation : … ». */
export const LIBELLES_DE_L_ATELIER: Readonly<Record<NomDeConversation, string>> = Object.freeze({
  'avec-systeme': 'la capitale',
  'sans-systeme': 'un bonjour',
  'deux-tours': 'deux calculs',
  'faux-special': 'un faux jeton spécial',
  pensee: 'une pensée',
  'reponse-vide': 'une réponse vide',
});

/**
 * Le deuxième tour que la bascule ajoute à chaque conversation : une autre question et sa réponse, prises dans
 * une conversation de référence (son nom, et le rang de l'échange, à partir de 0, hors message système). « deux
 * calculs » a déjà le sien ; les autres reçoivent une question qui peut suivre la leur.
 */
export const DEUXIEMES_TOURS: Readonly<Record<NomDeConversation, readonly [NomDeConversation, number]>> = Object.freeze({
  'avec-systeme': ['deux-tours', 0],
  'sans-systeme': ['avec-systeme', 0],
  'deux-tours': ['deux-tours', 1],
  'faux-special': ['sans-systeme', 0],
  pensee: ['deux-tours', 1],
  'reponse-vide': ['sans-systeme', 0],
});

/** Le message système que la bascule ajoute : celui de la conversation « avec-systeme », la seule qui en a un. */
export const CONVERSATION_DU_SYSTEME: NomDeConversation = 'avec-systeme';

/** Ce que le lecteur a réglé : la conversation, et ses deux bascules. */
export interface ReglageDeLAtelier {
  nom: NomDeConversation;
  systeme: boolean;
  deuxieme: boolean;
}

function trouver(conversations: readonly ConversationDeReference[], nom: string): ConversationDeReference {
  const c = conversations.find((x) => x.nom === nom);
  if (c === undefined) {
    throw new Error(
      `La conversation de référence « ${nom} » manque dans les attendus du projet 1.7 : régénère-les ` +
        '(uv run --extra cpu python -m conversation_pas_a_pas.attendus, dans projets/1.7-conversation).',
    );
  }
  return c;
}

/** Les échanges d'une conversation (une question, puis sa réponse), sans son message système. */
function echanges(c: ConversationDeReference): TourDeReference[][] {
  const tours = c.tours.filter((t) => t.role !== 'systeme');
  const liste: TourDeReference[][] = [];
  for (let i = 0; i < tours.length; i += 2) liste.push(tours.slice(i, i + 2));
  return liste;
}

/** Le réglage qui redonne la conversation de référence telle quelle : ses bascules sont celles de ses tours. */
export function reglageDeReference(conversations: readonly ConversationDeReference[], nom: NomDeConversation): ReglageDeLAtelier {
  const c = trouver(conversations, nom);
  return { nom, systeme: c.tours.some((t) => t.role === 'systeme'), deuxieme: echanges(c).length > 1 };
}

/** Les tours d'un réglage : le message système s'il est demandé, le premier échange, puis le deuxième s'il est demandé. */
export function toursDeLAtelier(conversations: readonly ConversationDeReference[], reglage: ReglageDeLAtelier): TourDeReference[] {
  const c = trouver(conversations, reglage.nom);
  const systeme = trouver(conversations, CONVERSATION_DU_SYSTEME).tours.find((t) => t.role === 'systeme');
  if (systeme === undefined) throw new Error(`La conversation « ${CONVERSATION_DU_SYSTEME} » des attendus n’a plus de message système.`);
  const [source, rang] = DEUXIEMES_TOURS[reglage.nom];
  const deuxieme = echanges(trouver(conversations, source))[rang];
  if (deuxieme === undefined) throw new Error(`La conversation « ${source} » des attendus n’a plus d’échange ${rang + 1}.`);
  return [...(reglage.systeme ? [systeme] : []), ...echanges(c)[0], ...(reglage.deuxieme ? deuxieme : [])];
}

// ---------- La règle des textes vides, celle de Python ----------

const BLANCS: ReadonlySet<number> = new Set(BLANCS_PYTHON);

/**
 * Vrai si `texte` est vide ou fait seulement de blancs, au sens de str.isspace() de Python : ce que
 * `not texte.strip()` refuse. Les points de code sont lus un à un (Array.from), sans \s ni trim, dont les
 * blancs ne sont pas ceux de Python.
 */
export function texteFaitDeBlancs(texte: string): boolean {
  return Array.from(texte).every((c) => BLANCS.has(c.codePointAt(0) as number));
}

/**
 * Lève l'erreur de verifier_conversation pour le premier tour vide ou fait de blancs, avec ses mots. Dans
 * l'atelier, les rôles et leur ordre sont toujours justes : la première erreur de Python est donc celle-là.
 */
export function refuserLesTextesBlancs(tours: readonly { role: Role; texte: string }[]): void {
  tours.forEach((tour, i) => {
    if (texteFaitDeBlancs(tour.texte)) {
      throw new Error(`Le texte du tour ${i + 1} (${tour.role}) est vide. Écris un texte ou retire ce tour.`);
    }
  });
}

/** Les tours, tels que le jumeau les reçoit : des ids. */
export function enToursEncodes(tours: readonly TourDeReference[]): TourEncode[] {
  return tours.map((t) => ({ role: t.role, ids: t.ids, ...(t.pensee_ids === undefined ? {} : { penseeIds: t.pensee_ids }) }));
}

// ---------- Ce que montre l'atelier ----------

/** Un jeton de la conversation : son id, s'il est appris, et s'il est spécial. */
export interface JetonDeLAtelier {
  id: number;
  appris: boolean;
  special: boolean;
}

/** Une ligne de la conversation montrée : le premier jeton seul, puis un tour par ligne. */
export interface LigneDeLAtelier {
  role: Role | 'debut';
  jetons: JetonDeLAtelier[];
}

export type EtatDeLAtelier =
  | { erreur: null; lignes: LigneDeLAtelier[]; jetons: number; appris: number }
  | { erreur: string; lignes: []; jetons: 0; appris: 0 };

const ROLE_DU_JETON: Readonly<Record<number, Role>> = Object.freeze({
  [PREMIER_SPECIAL + 3]: 'systeme',
  [PREMIER_SPECIAL + 4]: 'utilisateur',
  [PREMIER_SPECIAL + 5]: 'assistant',
});

/**
 * L'état de l'atelier pour un réglage : les jetons de la conversation, rangés par tour, leur masque et leur
 * compte, calculés par le jumeau ; ou l'erreur que forge lève (une réponse vide), avec ses mots.
 */
export function etatDeLAtelier(conversations: readonly ConversationDeReference[], reglage: ReglageDeLAtelier): EtatDeLAtelier {
  const tours = toursDeLAtelier(conversations, reglage);
  try {
    refuserLesTextesBlancs(tours);
    const { ids, appris } = assemblerConversation(enToursEncodes(tours));
    const lignes: LigneDeLAtelier[] = [];
    ids.forEach((id, i) => {
      const role = ROLE_DU_JETON[id];
      if (i === 0 || role !== undefined) lignes.push({ role: i === 0 ? 'debut' : role, jetons: [] });
      lignes[lignes.length - 1].jetons.push({ id, appris: appris[i], special: id >= PREMIER_SPECIAL });
    });
    return { erreur: null, lignes, jetons: ids.length, appris: appris.filter(Boolean).length };
  } catch (e) {
    return { erreur: e instanceof Error ? e.message : String(e), lignes: [], jetons: 0, appris: 0 };
  }
}

/** « 30 jetons, dont 9 appris. » */
export function texteDuCompte(jetons: number, appris: number): string {
  return `${nombre(jetons)} ${jetons > 1 ? 'jetons' : 'jeton'}, dont ${nombre(appris)} appris.`;
}

/**
 * Le défi : avec un message système et un deuxième tour, plus de la moitié des jetons de la conversation sont
 * appris. Les deux ajoutent des jetons lus : il faut une conversation où l'assistant parle beaucoup.
 */
export function defiReussi(etat: EtatDeLAtelier, reglage: ReglageDeLAtelier): boolean {
  return etat.erreur === null && reglage.systeme && reglage.deuxieme && 2 * etat.appris > etat.jetons;
}

/** La ligne du défi sous l'atelier : la part apprise de la conversation montrée, et ce qu'il manque au défi. */
export function texteDuDefi(etat: EtatDeLAtelier, reglage: ReglageDeLAtelier): string {
  if (etat.erreur !== null) return `Cette conversation n’a aucun jeton${FINE}: forge la refuse.`;
  const part = pourcent(etat.appris / etat.jetons, 0);
  if (defiReussi(etat, reglage)) return `Défi réussi${FINE}: ${part} des jetons sont appris.`;
  if (!reglage.systeme || !reglage.deuxieme) return `Ici, ${part} sont appris${FINE}; le défi veut aussi les deux ajouts.`;
  return `Ici, ${part} des jetons sont appris${FINE}: pas encore la moitié.`;
}

/** Un morceau du texte d'un jeton : les espaces se voient (« ␣ »), plus discrètement que les lettres. */
export interface MorceauDeJeton {
  texte: string;
  blanc: boolean;
}

/** Le texte d'un jeton en morceaux : chaque suite d'espaces devient des « ␣ », marqués `blanc`. */
export function morceauxDuJeton(texte: string): MorceauDeJeton[] {
  const morceaux: MorceauDeJeton[] = [];
  for (const c of Array.from(texte)) {
    const blanc = c === ' ';
    const dernier = morceaux[morceaux.length - 1];
    if (dernier !== undefined && dernier.blanc === blanc) dernier.texte += blanc ? '␣' : c;
    else morceaux.push({ texte: blanc ? '␣' : c, blanc });
  }
  return morceaux;
}

// ---------- La figure de l'empaquetage ----------

/** Les longueurs de rangée que la figure propose. 2 048, celle de ton IA, est la troisième. */
export const LONGUEURS_DE_RANGEE: readonly number[] = Object.freeze([512, 1024, 2048, 4096]);

/** La longueur de rangée de ton IA : celle de la figure à l'arrivée. */
export const LONGUEUR_DE_TON_IA = 2048;

/** Une rangée de la figure : la longueur de chacun de ses exemples, dans l'ordre où BFD les y a placés. */
export type RangeeDessinee = number[];

/** Ce que la figure montre d'un empaquetage, pour une longueur de rangée. */
export interface EmpaquetageDeLaFigure {
  /** La longueur d'une rangée (forge range des rangées de longueur + 1 positions). */
  longueur: number;
  /** Les positions d'une rangée : longueur + 1. */
  places: number;
  rangees: number;
  /** Les positions occupées par un exemple, toutes rangées comprises. */
  occupees: number;
  ecartes: number;
  /** Les premières rangées, dessinées. */
  premieres: RangeeDessinee[];
}

/** « Avec des rangées de [L] jetons, BFD remplit {r} des places, et écarte {e} exemples trop longs » : la suite, après le nombre. */
export function phraseDeLEmpaquetage(e: EmpaquetageDeLaFigure): string {
  if (e.rangees === 0) return `jetons, BFD n’a rien à ranger${FINE}: tous les exemples sont trop longs.`;
  const remplies = pourcent(e.occupees / (e.rangees * e.places), 1);
  const ecartes =
    e.ecartes === 0
      ? 'et n’écarte aucun exemple'
      : `et écarte ${nombre(e.ecartes)} ${e.ecartes > 1 ? 'exemples trop longs' : 'exemple trop long'}`;
  return `jetons, BFD remplit ${remplies} des places, ${ecartes}.`;
}
