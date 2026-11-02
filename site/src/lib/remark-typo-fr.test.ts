import type { Code, InlineCode, Paragraph, Root, Text } from 'mdast';
import remarkParse from 'remark-parse';
import { unified } from 'unified';
import { describe, expect, it } from 'vitest';
import { remarkTypoFr } from './remark-typo-fr';

const FINE = ' ';

function texte(value: string): Text {
  return { type: 'text', value };
}

function appliquer(arbre: Root): Root {
  remarkTypoFr()(arbre);
  return arbre;
}

describe('remarkTypoFr', () => {
  it('typographie les nœuds text', () => {
    const arbre: Root = {
      type: 'root',
      children: [{ type: 'paragraph', children: [texte('Pourquoi découper ?')] }],
    };
    appliquer(arbre);
    const paragraphe = arbre.children[0] as Paragraph;
    expect((paragraphe.children[0] as Text).value).toBe(`Pourquoi découper${FINE}?`);
  });

  it('ne touche jamais aux nœuds code ni inlineCode', () => {
    const bloc: Code = { type: 'code', lang: 'python', value: 'x = a if b else c ? d : e ;' };
    const enLigne: InlineCode = { type: 'inlineCode', value: 'a ? b : c' };
    const arbre: Root = {
      type: 'root',
      children: [
        { type: 'paragraph', children: [texte('Voir '), enLigne, texte(' : fini !')] },
        bloc,
      ],
    };
    appliquer(arbre);
    const paragraphe = arbre.children[0] as Paragraph;
    expect((paragraphe.children[0] as Text).value).toBe('Voir ');
    expect((paragraphe.children[1] as InlineCode).value).toBe('a ? b : c');
    expect((paragraphe.children[2] as Text).value).toBe(`${FINE}: fini${FINE}!`);
    expect(bloc.value).toBe('x = a if b else c ? d : e ;');
  });

  it('descend dans les liens, les emphases et les listes', () => {
    const arbre: Root = {
      type: 'root',
      children: [
        {
          type: 'list',
          ordered: false,
          spread: false,
          children: [
            {
              type: 'listItem',
              spread: false,
              children: [
                {
                  type: 'paragraph',
                  children: [
                    { type: 'emphasis', children: [texte('Vraiment ?')] },
                    { type: 'link', url: 'https://exemple.fr/?a :b', children: [texte('Lien !')] },
                  ],
                },
              ],
            },
          ],
        },
      ],
    };
    appliquer(arbre);
    const json = JSON.stringify(arbre);
    expect(json).toContain(`Vraiment${FINE}?`);
    expect(json).toContain(`Lien${FINE}!`);
    // L'adresse du lien n'est pas du texte : elle reste telle quelle.
    expect(json).toContain('https://exemple.fr/?a :b');
  });

  it('fonctionne sur un vrai arbre produit par remark-parse', () => {
    const source = [
      'Pourquoi découper ? Il dit : « les forgerons ».',
      '',
      'Avec `a ? b : c` en ligne et https://exemple.fr à 16:9.',
      '',
      '```python',
      'resultat = a if b else c  # pourquoi ?',
      '```',
      '',
    ].join('\n');
    const processeur = unified().use(remarkParse).use(remarkTypoFr);
    const arbre = processeur.runSync(processeur.parse(source)) as Root;
    const json = JSON.stringify(arbre);
    expect(json).toContain(`Pourquoi découper${FINE}? Il dit${FINE}: «${FINE}les forgerons${FINE}».`);
    expect(json).toContain('a ? b : c');
    expect(json).toContain('https://exemple.fr à 16:9.');
    expect(json).toContain('resultat = a if b else c  # pourquoi ?');
    expect(json).not.toContain(`pourquoi${FINE}?`);
  });
});
