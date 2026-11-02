// Aides communes aux parcours de test.
import { expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

/** Échoue sur toute violation des règles WCAG 2 de niveaux A et AA. */
export async function verifierAxe(page: Page): Promise<void> {
  const resultat = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
  // On compare une version courte (règle et éléments fautifs) pour que le
  // message d'échec dise tout de suite quoi corriger.
  const violations = resultat.violations.map((v) => ({
    regle: v.id,
    elements: v.nodes.map((n) => n.target.join(' ')),
  }));
  expect(violations).toEqual([]);
}

/**
 * Longueur, en caractères, de la plus longue ligne affichée dans les
 * paragraphes de la colonne de lecture. Le plancher de qualité demande des
 * lignes de moins de 80 caractères environ.
 */
export async function plusLongueLigne(page: Page): Promise<{ longueur: number; ligne: string }> {
  return page.evaluate(() => {
    let plusLongue = '';
    for (const bloc of document.querySelectorAll('.chapitre .texte p, .chapitre .texte li')) {
      // On regroupe les caractères par ligne, d'après leur position verticale.
      const lignes = new Map<number, string>();
      const marcheur = document.createTreeWalker(bloc, NodeFilter.SHOW_TEXT);
      for (let noeud = marcheur.nextNode() as Text | null; noeud; noeud = marcheur.nextNode() as Text | null) {
        for (let i = 0; i < noeud.length; i++) {
          const portion = document.createRange();
          portion.setStart(noeud, i);
          portion.setEnd(noeud, i + 1);
          const rect = portion.getClientRects()[0];
          if (!rect) continue;
          const haut = Math.round(rect.top / 4);
          lignes.set(haut, (lignes.get(haut) ?? '') + noeud.data[i]);
        }
      }
      for (const ligne of lignes.values()) {
        if (ligne.trim().length > plusLongue.length) plusLongue = ligne.trim();
      }
    }
    return { longueur: plusLongue.length, ligne: plusLongue };
  });
}

/** Vérifie que la page ne déborde pas en largeur : pas de défilement horizontal. */
export async function verifierSansDebordement(page: Page): Promise<void> {
  const { largeur, fenetre } = await page.evaluate(() => ({
    largeur: document.documentElement.scrollWidth,
    fenetre: window.innerWidth,
  }));
  expect(largeur).toBeLessThanOrEqual(fenetre);
}
