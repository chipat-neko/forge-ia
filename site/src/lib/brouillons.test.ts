import { describe, expect, it } from 'vitest';
import { verifierBrouillons } from './brouillons';

describe('verifierBrouillons', () => {
  it('accepte un brouillon bien nommé dont le numéro n’est pas paru', () => {
    expect(() => verifierBrouillons(['1.3'], [{ numero: '0.1', fichier: '0-1.mdx' }])).not.toThrow();
    expect(() => verifierBrouillons(['1.3'], [])).not.toThrow();
  });

  it('refuse un chapitre à la fois paru et en brouillon, et dit quoi supprimer', () => {
    expect(() => verifierBrouillons(['0.1'], [{ numero: '0.1', fichier: '0-1.mdx' }])).toThrow('à la fois paru');
    expect(() => verifierBrouillons(['1.3', '0.1'], [{ numero: '0.1', fichier: '0-1.mdx' }])).toThrow(
      'Le chapitre 0.1 est à la fois paru (src/content/chapitres/0-1.mdx) et en brouillon ' +
        '(src/brouillons/chapitres/0-1.mdx) : supprime le brouillon.',
    );
  });

  it('refuse un brouillon mal nommé, et donne le bon nom', () => {
    expect(() => verifierBrouillons([], [{ numero: '0.1', fichier: '01.mdx' }])).toThrow("doit s'appeler 0-1.mdx");
    expect(() => verifierBrouillons([], [{ numero: '1.10', fichier: '1-1.mdx' }])).toThrow(
      "Le brouillon du chapitre 1.10 doit s'appeler 1-10.mdx (trouvé : 1-1.mdx).",
    );
  });
});
