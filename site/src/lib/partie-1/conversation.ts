// Le format de conversation de ton IA, chapitre 1.7 : le jumeau TypeScript de `encoder_conversation`
// (projets/forge/forge/conversation/format.py), une fois les textes encodés.
//
// Une conversation s'écrit en jetons ainsi :
//
//   <|fin_texte|>
//   <|systeme|> consignes <|fin_tour|>             (facultatif, au plus un, en premier)
//   <|utilisateur|> question <|fin_tour|>
//   <|assistant|> [<|pensee|> brouillon <|fin_pensee|>] réponse <|fin_tour|>
//   …
//
// et chaque jeton porte un booléen « appris » : seul ce que dit l'assistant, du jeton qui suit
// <|assistant|> jusqu'à son <|fin_tour|> compris, est une cible de la perte.
//
// Le navigateur n'a pas le tokenizer : le jumeau ne refait donc que l'assemblage. Les textes arrivent déjà
// encodés (les `ids` de chaque tour, et `penseeIds` pour la pensée de l'assistant), tels que le Python les
// a encodés (projets/1.7-conversation/tests/attendus.json, section « conversations »). Une fonction pour
// chaque fonction du Python, les mêmes opérations dans le même ordre : `verifierConversation`
// (verifier_conversation, pour apprendre) et `assemblerConversation` (encoder_conversation).
//
// Un seul écart, dit ici : le Python refuse un texte vide ou fait seulement de blancs (`texte.strip()`).
// Le jumeau ne voit que des ids : il refuse un texte sans aucun jeton, c'est-à-dire un texte vide. Un texte
// fait seulement de blancs a des jetons, et passe : la règle des blancs de Python n'est pas refaite ici.
//
// Ce module n'importe rien : une page ou un parcours le charge sans rien embarquer d'autre.

export type Role = 'systeme' | 'utilisateur' | 'assistant';

/** Un tour de parole, encodé : `ids` pour son texte, `penseeIds` pour la pensée de l'assistant (s'il en a une). */
export interface TourEncode {
  role: Role;
  ids: number[];
  penseeIds?: number[];
}

/** Les ids d'une conversation et, pour chacun, `true` si c'est une cible apprise. */
export interface ExempleMasque {
  ids: number[];
  appris: boolean[];
}

/** Le premier jeton spécial de ton IA : le vocabulaire a 32 768 jetons, dont les 64 derniers sont spéciaux. */
export const PREMIER_SPECIAL = 32768 - 64;

const SPECIAUX_NOMMES = [
  '<|debut_texte|>', // début d'un document
  '<|fin_texte|>', // fin d'un document (sépare les documents à l'entraînement)
  '<|bourrage|>', // remplissage, pour mettre des lots à la même longueur
  '<|systeme|>', // consignes générales d'une conversation
  '<|utilisateur|>', // ce qu'écrit la personne
  '<|assistant|>', // ce que répond ton IA
  '<|fin_tour|>', // fin d'une prise de parole
  '<|appel_outil|>',
  '<|fin_appel_outil|>',
  '<|resultat_outil|>',
  '<|fin_resultat_outil|>',
  '<|pensee|>', // brouillon de raisonnement, avant la réponse
  '<|fin_pensee|>',
  '<|image|>',
  '<|fin_image|>',
  '<|trou_prefixe|>', // remplir un trou dans du code : ce qui précède,
  '<|trou_suffixe|>', // ce qui suit,
  '<|trou_milieu|>', // puis le morceau à écrire
];

/** Les 64 noms des jetons spéciaux, dans l'ordre figé du tokenizer : les 18 nommés, puis `<|reserve_00|>`… */
export const NOMS_SPECIAUX: readonly string[] = Object.freeze([
  ...SPECIAUX_NOMMES,
  ...Array.from({ length: 64 - SPECIAUX_NOMMES.length }, (_, numero) => `<|reserve_${String(numero).padStart(2, '0')}|>`),
]);

/** Les jetons spéciaux de ton IA : le nom, et l'id qu'il occupe (les 64 derniers du vocabulaire, dans l'ordre). */
export const SPECIAUX_TON_IA: Readonly<Record<string, number>> = Object.freeze(
  Object.fromEntries(NOMS_SPECIAUX.map((nom, place) => [nom, PREMIER_SPECIAL + place])),
);

const ROLES: readonly string[] = ['systeme', 'utilisateur', 'assistant'];

/** L'id d'un jeton spécial ; un nom inconnu est une erreur, comme `id_special` du Python. */
function idSpecial(nom: string): number {
  const id = SPECIAUX_TON_IA[nom];
  if (id === undefined) {
    throw new Error(`Jeton spécial inconnu : '${nom}'. Les noms possibles sont ceux de NOMS_SPECIAUX, par exemple « <|fin_texte|> ».`);
  }
  return id;
}

/**
 * Lève une `Error` (qui nomme le tour fautif, à partir de 1) si la conversation est mal formée, avec les
 * mots de `verifier_conversation` du Python, pour une conversation à apprendre (elle finit par l'assistant).
 */
export function verifierConversation(tours: readonly TourEncode[]): void {
  if (tours.length === 0) throw new Error("La conversation est vide : il faut au moins un tour de l'utilisateur.");
  let attendu: Role = 'utilisateur'; // le rôle qui doit venir ensuite, hors système
  tours.forEach((tour, i) => {
    const rang = i + 1;
    if (!ROLES.includes(tour.role)) {
      throw new Error(
        `Le tour ${rang} a un rôle inconnu : '${String(tour.role)}'. ` +
          'Les rôles possibles sont « systeme », « utilisateur » et « assistant ».',
      );
    }
    if (tour.ids.length === 0) {
      throw new Error(`Le texte du tour ${rang} (${tour.role}) est vide. Écris un texte ou retire ce tour.`);
    }
    if (tour.penseeIds !== undefined && tour.role !== 'assistant') {
      throw new Error(`Le tour ${rang} (${tour.role}) porte une pensée : seul l'assistant en a une. Retire la pensée.`);
    }
    if (tour.role === 'systeme') {
      if (rang === 2 && tours[0].role === 'systeme') {
        throw new Error(`Le tour ${rang} est un deuxième message système : il n'y en a qu'un. Fusionne-le avec le premier.`);
      }
      if (rang !== 1) {
        throw new Error(`Le tour ${rang} est un message système : il doit être le premier tour, et il n'y en a qu'un.`);
      }
      return;
    }
    if (tour.role !== attendu) {
      throw new Error(
        `Le tour ${rang} est de rôle « ${tour.role} » mais on attendait « ${attendu} » : ` +
          'les tours alternent utilisateur, assistant, en commençant par l\'utilisateur.',
      );
    }
    attendu = tour.role === 'utilisateur' ? 'assistant' : 'utilisateur';
  });
  const dernier = tours[tours.length - 1];
  if (dernier.role !== 'assistant') {
    throw new Error(
      `Le dernier tour (tour ${tours.length}) est de rôle « ${dernier.role} » : pour apprendre, ` +
        'la conversation doit finir par un tour de l\'assistant (pas d\'assistant à apprendre ici).',
    );
  }
}

/** Les jetons d'un tour, et le nombre de jetons du début qui ne sont pas appris (`_jetons_du_tour`). */
function jetonsDuTour(tour: TourEncode): [number[], number] {
  const ids = [idSpecial(`<|${tour.role}|>`)];
  const debutAppris = ids.length;
  if (tour.role === 'assistant' && tour.penseeIds !== undefined) {
    ids.push(idSpecial('<|pensee|>'));
    for (const id of tour.penseeIds) ids.push(id);
    ids.push(idSpecial('<|fin_pensee|>'));
  }
  for (const id of tour.ids) ids.push(id);
  ids.push(idSpecial('<|fin_tour|>'));
  return [ids, debutAppris];
}

/**
 * Assemble une conversation complète (qui finit par l'assistant) avec son masque de perte : la traduction
 * exacte d'`encoder_conversation`, une fois les textes encodés. `appris` vaut `true` pour les jetons de
 * l'assistant à partir du jeton qui suit `<|assistant|>`, son `<|fin_tour|>` compris, et `false` ailleurs.
 */
export function assemblerConversation(tours: readonly TourEncode[]): ExempleMasque {
  verifierConversation(tours);
  const ids = [idSpecial('<|fin_texte|>')];
  const appris = [false];
  for (const tour of tours) {
    const [jetons, debutAppris] = jetonsDuTour(tour);
    jetons.forEach((id, i) => {
      ids.push(id);
      appris.push(tour.role === 'assistant' && i >= debutAppris);
    });
  }
  return { ids, appris };
}
