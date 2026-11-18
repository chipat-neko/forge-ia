// Le jumeau du format de conversation retrouve exactement les attendus du Python
// (FICHIERS_PARTIE_1.conversation, projets/1.7-conversation/tests/attendus.json) : les jetons spéciaux de
// ton IA, les six conversations de référence (ids et masque de perte, ou l'erreur de la conversation refusée),
// et, par la page de parité, le fichier tout entier (toStrictEqual).

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import {
  assemblerConversation,
  NOMS_SPECIAUX,
  PREMIER_SPECIAL,
  SPECIAUX_TON_IA,
  verifierConversation,
  type Role,
  type TourEncode,
} from './conversation';
import { FICHIERS_PARTIE_1 } from './fichiers';
import { CALCULS_PARTIE_1, refaireConversation, type EntreesConversation } from './parite';

interface TourAttendu {
  role: Role;
  texte: string;
  ids: number[];
  pensee?: string;
  pensee_ids?: number[];
}

interface Attendus extends EntreesConversation {
  speciaux: [string, number][];
  conversations: {
    nom: string;
    tours: TourAttendu[];
    ids: number[] | null;
    appris: boolean[] | null;
    erreur: string | null;
  }[];
}

const ATTENDUS = JSON.parse(readFileSync(`../${FICHIERS_PARTIE_1.conversation}`, 'utf8')) as Attendus;

/** Les tours encodés d'un cas, tels que le jumeau les reçoit. */
function toursDe(tours: TourAttendu[]): TourEncode[] {
  return tours.map((t) => ({ role: t.role, ids: t.ids, ...(t.pensee_ids === undefined ? {} : { penseeIds: t.pensee_ids }) }));
}

/** Un tour encodé à la main : un seul jeton ordinaire, l'id 7 (le texte n'a pas d'importance pour l'assemblage). */
const tour = (role: Role, penseeIds?: number[]): TourEncode => ({ role, ids: [7], ...(penseeIds === undefined ? {} : { penseeIds }) });

describe('les jetons spéciaux de ton IA', () => {
  it('sont les 64 du Python, dans le même ordre, avec les mêmes ids', () => {
    expect(Object.entries(SPECIAUX_TON_IA)).toStrictEqual(ATTENDUS.speciaux);
    expect(NOMS_SPECIAUX).toStrictEqual(ATTENDUS.speciaux.map(([nom]) => nom));
  });

  it('occupent les 64 derniers ids du vocabulaire de 32 768 jetons', () => {
    expect(PREMIER_SPECIAL).toBe(32704);
    expect(Object.values(SPECIAUX_TON_IA)).toStrictEqual(Array.from({ length: 64 }, (_, i) => 32704 + i));
    expect(SPECIAUX_TON_IA['<|assistant|>']).toBe(32709);
    expect(SPECIAUX_TON_IA['<|fin_tour|>']).toBe(32710);
  });
});

describe('assemblerConversation', () => {
  it('lit six conversations de référence', () => {
    expect(ATTENDUS.conversations.map((c) => c.nom)).toStrictEqual([
      'avec-systeme',
      'sans-systeme',
      'deux-tours',
      'faux-special',
      'pensee',
      'reponse-vide',
    ]);
  });

  it.each(ATTENDUS.conversations.filter((c) => c.erreur === null).map((c) => [c.nom, c] as const))(
    'retrouve les ids et le masque de %s',
    (_nom, cas) => {
      expect(assemblerConversation(toursDe(cas.tours))).toStrictEqual({ ids: cas.ids, appris: cas.appris });
    },
  );

  it('refuse la réponse vide avec les mots du Python', () => {
    const vide = ATTENDUS.conversations.find((c) => c.nom === 'reponse-vide');
    expect(vide?.erreur).toBeTypeOf('string');
    expect(() => assemblerConversation(toursDe(vide?.tours ?? []))).toThrow(vide?.erreur ?? '');
  });

  it('assemble une conversation à la main : seul ce que dit l’assistant est appris', () => {
    const { ids, appris } = assemblerConversation([tour('utilisateur'), tour('assistant')]);
    const S = SPECIAUX_TON_IA;
    expect(ids).toStrictEqual([S['<|fin_texte|>'], S['<|utilisateur|>'], 7, S['<|fin_tour|>'], S['<|assistant|>'], 7, S['<|fin_tour|>']]);
    expect(appris).toStrictEqual([false, false, false, false, false, true, true]);
  });

  it('apprend la pensée avec la réponse, mais pas le jeton <|assistant|>', () => {
    const { ids, appris } = assemblerConversation([tour('utilisateur'), tour('assistant', [8, 9])]);
    const S = SPECIAUX_TON_IA;
    expect(ids.slice(4)).toStrictEqual([S['<|assistant|>'], S['<|pensee|>'], 8, 9, S['<|fin_pensee|>'], 7, S['<|fin_tour|>']]);
    expect(appris.slice(4)).toStrictEqual([false, true, true, true, true, true, true]);
  });

  it('n’apprend ni le système, ni l’utilisateur, ni les jetons du début', () => {
    const { appris, ids } = assemblerConversation([tour('systeme'), tour('utilisateur'), tour('assistant')]);
    expect(ids).toHaveLength(1 + 3 * 3);
    expect(appris.slice(0, 7)).toStrictEqual(Array(7).fill(false));
  });

  it('ne change pas les tours qu’on lui donne, et ne dépasse pas la pile sur de longs textes', () => {
    const long = Array.from({ length: 200_000 }, (_, i) => i % 1000);
    const entree: TourEncode[] = [{ role: 'utilisateur', ids: long }, tour('assistant')];
    const { ids, appris } = assemblerConversation(entree);
    expect(ids).toHaveLength(1 + 1 + 200_000 + 1 + 3);
    expect(appris).toHaveLength(ids.length);
    expect(entree[0].ids).toHaveLength(200_000);
  });
});

describe('verifierConversation, avec les mots du Python', () => {
  const rejette = (tours: TourEncode[], message: string) => expect(() => verifierConversation(tours)).toThrow(message);

  it('refuse une conversation vide', () => {
    rejette([], 'La conversation est vide : il faut au moins un tour de l\'utilisateur.');
  });

  it('refuse un texte sans jeton, en nommant le tour', () => {
    rejette([tour('utilisateur'), { role: 'assistant', ids: [] }], 'Le texte du tour 2 (assistant) est vide. Écris un texte ou retire ce tour.');
    rejette([{ role: 'utilisateur', ids: [] }, tour('assistant')], 'Le texte du tour 1 (utilisateur) est vide.');
  });

  it('refuse une pensée qui n’est pas celle de l’assistant', () => {
    rejette(
      [{ role: 'utilisateur', ids: [7], penseeIds: [8] }, tour('assistant')],
      'Le tour 1 (utilisateur) porte une pensée : seul l\'assistant en a une. Retire la pensée.',
    );
  });

  it('refuse un deuxième message système, ou un système qui n’est pas le premier', () => {
    rejette([tour('systeme'), tour('systeme'), tour('utilisateur'), tour('assistant')], 'Le tour 2 est un deuxième message système : il n\'y en a qu\'un.');
    rejette([tour('utilisateur'), tour('systeme'), tour('assistant')], 'Le tour 2 est un message système : il doit être le premier tour');
  });

  it('refuse des tours qui n’alternent pas', () => {
    rejette(
      [tour('assistant'), tour('utilisateur')],
      'Le tour 1 est de rôle « assistant » mais on attendait « utilisateur » : les tours alternent utilisateur, assistant, en commençant par l\'utilisateur.',
    );
    rejette([tour('utilisateur'), tour('utilisateur'), tour('assistant')], 'Le tour 2 est de rôle « utilisateur » mais on attendait « assistant »');
  });

  it('refuse un dernier tour qui n’est pas celui de l’assistant', () => {
    rejette(
      [tour('utilisateur')],
      'Le dernier tour (tour 1) est de rôle « utilisateur » : pour apprendre, la conversation doit finir par un tour de l\'assistant',
    );
    rejette([tour('systeme')], 'Le dernier tour (tour 1) est de rôle « systeme »');
  });

  it('refuse un rôle inconnu', () => {
    rejette([{ role: 'robot' as Role, ids: [7] }], 'Le tour 1 a un rôle inconnu : \'robot\'. Les rôles possibles sont « systeme », « utilisateur » et « assistant ».');
  });

  it('accepte un système suivi de plusieurs échanges', () => {
    expect(() => verifierConversation([tour('systeme'), tour('utilisateur'), tour('assistant'), tour('utilisateur'), tour('assistant')])).not.toThrow();
  });
});

describe('la page de parité', () => {
  it('refait tout le fichier d’attendus, sous le même nom', () => {
    expect(Object.keys(CALCULS_PARTIE_1)).toContain('conversation');
    expect(CALCULS_PARTIE_1.conversation()).toStrictEqual(ATTENDUS);
    expect(refaireConversation(ATTENDUS)).toStrictEqual(ATTENDUS);
  });
});
