// Aides communes aux parcours de test.
import { expect, type Locator, type Page } from '@playwright/test';
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
 * Rapport de contraste WCAG entre deux couleurs calculées par le navigateur
 * (« rgb(35, 32, 87) »), de 1 (aucun contraste) à 21.
 */
export function contraste(couleurA: string, couleurB: string): number {
  const luminance = (couleur: string) => {
    const [r, g, b] = (couleur.match(/[\d.]+/g) ?? []).slice(0, 3).map((v) => {
      const c = Number(v) / 255;
      return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  };
  const [claire, foncee] = [luminance(couleurA), luminance(couleurB)].sort((x, y) => y - x);
  return (claire + 0.05) / (foncee + 0.05);
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
        // Un texte réservé aux lecteurs d'écran (une boîte d'un pixel) ne
        // se lit pas à l'écran : il ne compte pas dans la longueur des lignes.
        if ((noeud.parentElement?.getBoundingClientRect().width ?? 2) <= 1) continue;
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
        // Les blancs du code source (retour à la ligne et retrait d'un gabarit)
        // s'affichent comme une seule espace : on les compte comme tels.
        const affichee = ligne.replace(/\s+/g, ' ').trim();
        if (affichee.length > plusLongue.length) plusLongue = affichee;
      }
    }
    return { longueur: plusLongue.length, ligne: plusLongue };
  });
}

/**
 * Attend que tous les îlots Svelte de la page soient hydratés : tant qu'ils
 * ne le sont pas, la saisie, les boutons et le clavier ne font rien. Astro
 * retire l'attribut ssr d'un îlot une fois hydraté.
 */
export async function attendreHydratation(page: Page): Promise<void> {
  await expect(page.locator('astro-island[ssr]')).toHaveCount(0);
}

/**
 * Vérifie la typographie française du texte affiché d'une zone (innerText) :
 * aucune espace ordinaire ni insécable (U+0020, U+00A0) devant ; : ! ? % »,
 * aucune après «, aucun nombre dont les milliers sont séparés par une
 * espace ordinaire ou insécable (« 3 000 » doit s'écrire avec une espace
 * fine, U+202F), et aucune apostrophe droite entre deux lettres. Les motifs
 * des espaces et de l'apostrophe sont ceux du parcours du chapitre 1.3.
 */
export async function verifierTypographie(zone: Locator): Promise<void> {
  const texte = await zone.innerText();
  expect(texte.length, 'la zone à vérifier est vide').toBeGreaterThan(0);
  expect(texte.match(/.{0,30}[ \u00A0][;:!?%].{0,10}/g) ?? []).toEqual([]);
  expect(texte.match(/.{0,10}«[ \u00A0].{0,30}|.{0,30}[ \u00A0]».{0,10}/g) ?? []).toEqual([]);
  expect(texte.match(/.{0,20}\d[ \u00A0]\d{3}\b.{0,20}/g) ?? []).toEqual([]);
  // Apostrophe courbe (U+2019) entre deux lettres, jamais droite.
  expect(texte.match(/.{0,20}\p{L}'\p{L}.{0,20}/gu) ?? []).toEqual([]);
}

/**
 * Vérifie que la page ne déborde pas en largeur : pas de défilement horizontal.
 * On compare à la largeur visible de la page (clientWidth de html, sans la
 * barre de défilement), pas à innerWidth : sur mobile, une page qui déborde
 * élargit la fenêtre de mise en page, et innerWidth grandit avec elle (441 px
 * pour un écran de 390 px).
 */
export async function verifierSansDebordement(page: Page): Promise<void> {
  // On mesure la page telle qu'elle sera peinte : document lu en entier
  // (readyState « complete », l'événement load), CSS et polices chargées. Juste
  // après un clic, le document peut être encore à moitié analysé, sans ses CSS :
  // un état que le navigateur ne peint jamais, mais que scrollWidth mesurerait.
  await page.waitForLoadState('load');
  await page.evaluate(() => document.fonts.ready.then(() => undefined));
  const { largeur, fenetre } = await page.evaluate(() => ({
    largeur: document.documentElement.scrollWidth,
    fenetre: document.documentElement.clientWidth,
  }));
  expect(largeur, 'la page déborde en largeur').toBeLessThanOrEqual(fenetre);
}

/**
 * Termine le chapitre 1.3 comme un lecteur : ouvre la page, fait les 4 paris
 * (bonnes réponses) et pousse l'atelier de 20 à 60 fusions au clavier. Tous
 * les acquis du chapitre sont alors gagnés (« 5 sur 5 »). Sert aussi aux
 * parcours de l'accueil (progression d'un chapitre fait).
 */
export async function terminerChapitre13(page: Page): Promise<void> {
  await page.goto('/forge-ia/partie-1/1-3/');
  // L'atelier est un îlot Svelte : il répond au clavier une fois hydraté
  // (Astro retire alors l'attribut ssr).
  await expect(page.locator('astro-island[ssr]')).toHaveCount(0);
  await page.locator('[data-pari="nombres"] [data-juste]').click();
  await page.locator('[data-pari="prediction"] [data-juste]').click();
  const fusions = page.locator('[data-test="fusions"]');
  await expect(fusions).not.toHaveAttribute('aria-disabled', 'true');
  await fusions.focus();
  await page.keyboard.press('Home');
  for (let i = 0; i < 60; i++) await page.keyboard.press('ArrowRight');
  await expect(fusions).toHaveAttribute('aria-valuenow', '60');
  await page.locator('[data-pari="rare"] [data-juste]').click();
  await page.locator('[data-pari="zip"] [data-juste]').click();
  await expect(page.locator('#recap [data-total]')).toContainText('5 sur 5');
}
