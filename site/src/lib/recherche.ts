// La recherche du site : une enveloppe de l'API JavaScript de Pagefind, et
// la recherche dans les titres du parcours (chapitres parus ou à venir).
//
// Pagefind indexe le site construit (npm run build lance `pagefind --site
// dist`) : seules les pages marquées `data-pagefind-body`, c'est-à-dire les
// chapitres publiés, le glossaire et l'annuaire des données, sont dans l'index. Son script est chargé à la demande,
// à la première recherche ; en développement (astro dev), il n'existe pas et
// `chercher` lève une erreur que la page affiche simplement.
import type { Chapitre } from './parcours';

/** Un passage trouvé dans une page : une étape d'un chapitre, le plus souvent. */
export interface Passage {
  titre: string;
  url: string;
  /** Extrait au format de Pagefind : du texte, les mots trouvés entre <mark>. */
  extrait: string;
  /** Numéro de l'étape, si le passage en est une. */
  etape?: number;
}

/** Une page trouvée. */
export interface Resultat {
  titre: string;
  url: string;
  extrait: string;
  /** Numéro du chapitre (« 1.3 »), donné par la page à Pagefind. */
  numero?: string;
  /** Les passages de la page, dans l'ordre de lecture. */
  passages: Passage[];
}

// Ce que l'on utilise de l'API de Pagefind (pagefind.js).
interface SousResultatPagefind {
  title: string;
  url: string;
  excerpt: string;
}

export interface DonneesPagefind {
  url: string;
  excerpt: string;
  meta: Record<string, string | undefined>;
  sub_results?: SousResultatPagefind[];
}

interface Pagefind {
  options(options: Record<string, unknown>): Promise<void>;
  search(requete: string): Promise<{ results: { data(): Promise<DonneesPagefind> }[] } | null>;
}

/** Nombre maximal de pages montrées. */
const MAX_PAGES = 10;

let chargement: Promise<Pagefind> | null = null;

// La base du site sans barre oblique finale : « /forge-ia ».
function base(): string {
  return import.meta.env.BASE_URL.replace(/\/+$/, '');
}

function charger(): Promise<Pagefind> {
  chargement ??= (async () => {
    const pagefind = (await import(/* @vite-ignore */ `${base()}/pagefind/pagefind.js`)) as Pagefind;
    // Le site est servi sous /forge-ia/ : les liens des résultats aussi.
    await pagefind.options({ baseUrl: `${base()}/`, excerptLength: 28, excerptEllipsis: '…' });
    return pagefind;
  })().catch((erreur: unknown) => {
    // Échec (hors ligne, index absent) : on réessaiera à la prochaine recherche.
    chargement = null;
    throw erreur;
  });
  return chargement;
}

/**
 * Cherche dans le texte des chapitres publiés. Charge `pagefind.js` à la
 * première demande. Une requête vide ne donne rien, sans rien charger.
 */
export async function chercher(requete: string): Promise<Resultat[]> {
  const q = requete.trim();
  if (q === '') return [];
  const pagefind = await charger();
  const reponse = await pagefind.search(q);
  if (!reponse) return [];
  const donnees = await Promise.all(reponse.results.slice(0, MAX_PAGES).map((r) => r.data()));
  return garderPertinents(donnees.map(versResultat), q);
}

/**
 * Vrai si l'extrait surligne au moins un mot qui ressemble à la requête : un
 * mot surligné commence comme un mot de la requête, sur quatre lettres au
 * plus et une de moins que ce mot. « mots » garde donc « mot » et « jeux »
 * garde « jeu », que le racinisateur français de Pagefind trouve à juste titre.
 *
 * Quand un mot est absent de l'index, Pagefind le cherche en morceaux : pour
 * « gabarit », il surligne « g » ; pour « enclume », « en ». Ces résultats-là
 * ne parlent pas de ce que le lecteur cherche, on les écarte.
 */
export function extraitPertinent(extrait: string, requete: string): boolean {
  const debuts = (requete.match(MOT) ?? [])
    .map(aplatir)
    .filter((mot) => mot.length > 1)
    .map((mot) => mot.slice(0, Math.min(4, mot.length - 1)));
  if (debuts.length === 0) return true;
  return morceauxExtrait(extrait)
    .filter((m) => m.marque)
    .flatMap((m) => (m.texte.match(MOT) ?? []).map(aplatir))
    .some((mot) => debuts.some((debut) => mot.startsWith(debut)));
}

/** Les résultats sans les passages hors sujet ; une page sans passage pertinent disparaît. */
export function garderPertinents(resultats: Resultat[], requete: string): Resultat[] {
  return resultats.flatMap((resultat) => {
    const passages = resultat.passages.filter((p) => extraitPertinent(p.extrait, requete));
    if (passages.length > 0) return [{ ...resultat, passages }];
    // Seule l'ouverture de la page (avant la première étape) en parle, peut-être.
    return extraitPertinent(resultat.extrait, requete) ? [{ ...resultat, passages: [] }] : [];
  });
}

/** Un passage de Pagefind. Les titres d'étape ont pour id « titre-etape-N » : on vise la section « etape-N ». */
export function versPassage(sous: SousResultatPagefind): Passage {
  const etape = /#titre-etape-(\d+)$/.exec(sous.url);
  if (!etape) return { titre: sous.title, url: sous.url, extrait: sous.excerpt };
  return {
    titre: sous.title,
    url: sous.url.replace(/#titre-etape-\d+$/, `#etape-${etape[1]}`),
    extrait: sous.excerpt,
    etape: Number(etape[1]),
  };
}

/**
 * Un résultat de Pagefind. On ne garde comme passages que les parties de
 * page qui ont une ancre (les étapes, le récapitulatif…), rangées dans
 * l'ordre des étapes.
 */
export function versResultat(donnees: DonneesPagefind): Resultat {
  const passages = (donnees.sub_results ?? [])
    .filter((sous) => sous.url.includes('#'))
    .map(versPassage)
    .sort((a, b) => (a.etape ?? Infinity) - (b.etape ?? Infinity));
  return {
    titre: donnees.meta.title ?? donnees.url,
    url: donnees.url,
    extrait: donnees.excerpt,
    numero: donnees.meta.numero,
    passages,
  };
}

const ENTITES: Record<string, string> = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ' };

function decoder(texte: string): string {
  return texte.replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (tout, nom: string) => {
    if (nom[0] === '#') {
      const code = nom[1].toLowerCase() === 'x' ? parseInt(nom.slice(2), 16) : parseInt(nom.slice(1), 10);
      return Number.isFinite(code) && code >= 0 && code <= 0x10ffff ? String.fromCodePoint(code) : tout;
    }
    return ENTITES[nom.toLowerCase()] ?? tout;
  });
}

/**
 * Un extrait de Pagefind en morceaux de texte simple, marqués ou non. La
 * page les pose avec textContent : aucun HTML de l'index n'est interprété.
 */
export function morceauxExtrait(extrait: string): { texte: string; marque: boolean }[] {
  const morceaux: { texte: string; marque: boolean }[] = [];
  let marque = false;
  for (const bout of extrait.split(/(<\/?mark>)/)) {
    if (bout === '<mark>') marque = true;
    else if (bout === '</mark>') marque = false;
    else if (bout !== '') morceaux.push({ texte: decoder(bout), marque });
  }
  return morceaux;
}

// ---------- Les titres du parcours ----------

/** Sans accents ni majuscules : « Évaluer » devient « evaluer ». */
export function aplatir(texte: string): string {
  return texte.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase();
}

const MOT = /[\p{L}\p{N}]+/gu;

/**
 * Les racines d'une requête : ses mots aplatis, sans le « s » ou le « x » final
 * des mots de plus de quatre lettres (« images » trouve « image »). Les mots
 * d'une seule lettre sont ignorés.
 */
export function racines(requete: string): string[] {
  return (requete.match(MOT) ?? [])
    .map(aplatir)
    .map((mot) => (mot.length > 4 ? mot.replace(/[sx]$/, '') : mot))
    .filter((mot) => mot.length > 1);
}

/** Le numéro de chapitre que forme la requête (« 1.4 », « 1,4 »), sinon null. */
export function numeroDeChapitre(requete: string): string | null {
  const m = /^(\d)[.,](\d{1,2})$/.exec(requete.trim());
  return m ? `${m[1]}.${m[2]}` : null;
}

/**
 * Les chapitres du parcours dont le titre contient tous les mots de la
 * requête (chaque mot du titre peut commencer par une racine), ou celui qui
 * porte le numéro demandé.
 */
export function chercherDansLesTitres(requete: string, chapitres: Chapitre[]): Chapitre[] {
  const numero = numeroDeChapitre(requete);
  if (numero) return chapitres.filter((c) => c.numero === numero);
  const cherchees = racines(requete);
  if (cherchees.length === 0) return [];
  return chapitres.filter((chapitre) => {
    const mots = (chapitre.titre.match(MOT) ?? []).map(aplatir);
    return cherchees.every((racine) => mots.some((mot) => mot.startsWith(racine)));
  });
}
