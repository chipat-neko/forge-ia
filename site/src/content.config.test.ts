import { describe, expect, it } from 'vitest';
import { schemaChapitre } from './content.config';

// Un frontmatter de chapitre valable, à décliner dans chaque test.
const chapitre = {
  partie: 1,
  numero: '1.3',
  titre: 'Le tokenizer',
  chapeau: 'Un chapeau.',
  programme: '2 étapes, 1 pari, environ 5 minutes.',
  acquis: [
    { cle: 'a1', texte: 'Un premier acquis.', ou: 'à l’étape 1' },
    { cle: 'a2', texte: 'Un second acquis.', ou: 'à l’étape 2' },
  ],
};

describe('schemaChapitre', () => {
  it('accepte un chapitre aux clés d’acquis toutes différentes', () => {
    expect(schemaChapitre.safeParse(chapitre).success).toBe(true);
  });

  it('refuse deux acquis qui ont la même clé, et dit laquelle', () => {
    const doublon = {
      ...chapitre,
      acquis: [...chapitre.acquis, { cle: 'a1', texte: 'Un troisième acquis.', ou: 'à l’étape 3' }],
    };
    const resultat = schemaChapitre.safeParse(doublon);
    expect(resultat.success).toBe(false);
    expect(resultat.error?.issues.map((i) => i.message).join('\n')).toContain('« a1 »');
  });
});
