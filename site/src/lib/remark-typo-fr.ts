// Plugin remark : applique la typographie française aux textes des pages
// Markdown et MDX. Il ne regarde que les nœuds « text » : les blocs de code
// (« code ») et le code en ligne (« inlineCode ») restent tels quels, de même
// que les adresses des liens et les attributs.

import type { Root } from 'mdast';
import { visit } from 'unist-util-visit';
import { typographier } from './typo.ts';

export function remarkTypoFr() {
  return (arbre: Root): void => {
    visit(arbre, 'text', (noeud) => {
      noeud.value = typographier(noeud.value);
    });
  };
}
