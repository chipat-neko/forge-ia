import { describe, expect, it } from 'vitest';
import { exigeur } from './exiger';

describe('exigeur', () => {
  it('ne dit rien tant que l’exemple est juste, et nomme le fichier à revoir sinon', () => {
    const exiger = exigeur('src/lib/exemples.ts');
    expect(() => exiger(true, 'x')).not.toThrow();
    expect(() => exiger(false, '« z » apparaît dans le corpus')).toThrow(
      'Exemple devenu faux : « z » apparaît dans le corpus. Revoir src/lib/exemples.ts.',
    );
  });
});
