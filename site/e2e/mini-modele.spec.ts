// Parcours de la démo du mini-modèle qui apprend, sur la page d'essai
// /forge-ia/essais/mini-modele/ (construite seulement avec FORGE_ESSAIS=1,
// voir src/essais/mini-modele.mdx). La page a deux démos : l'entraînement
// complet (data-mini="mini"), derrière le verrou « mini » ouvert par le pari
// « depart », et l'avant-goût du chapitre 0.5 (data-mini="avant-gout").
//
// Le Worker entraîne vraiment le modèle, sur le processeur : un entraînement
// complet en vitesse rapide prend quelques secondes.
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { test, expect, type Page } from '@playwright/test';
import { decimalesUtiles, nombre } from '../src/lib/nombres';
import { MESSAGE_DIVERGENCE, MESSAGE_NOUVEAU_TAUX, MESSAGE_ONGLET } from '../src/lib/mini-modele/pilote';
import { PRESETS_MINI, TAUX_PROPOSES } from '../src/lib/mini-modele/reglages';
import { attendreHydratation, verifierAxe, verifierSansDebordement, verifierTypographie } from './outils';

const PAGE = '/forge-ia/essais/mini-modele/';
const FINE = '\u202F';
const COMPLET = PRESETS_MINI.complet;
const AVANT_GOUT = PRESETS_MINI['avant-gout'];
// Le premier progrès d'un Worker neuf peut tarder : le PC fait tourner l'entraînement
// de la carte graphique en même temps, et les parcours vont par quatre.
const ATTENTE_TRAVAILLEUR = { timeout: 20_000 };

const demo = (p: Page, nom = 'mini') => p.locator(`[data-mini="${nom}"]`);
// La ligne d'état visible (elle change à chaque validation), et la zone lue par les lecteurs
// d'écran (role="status", cachée à l'œil), qui ne la reprend qu'aux moments qui comptent.
const etat = (p: Page, nom = 'mini') => demo(p, nom).locator('[data-test="mini-etat"]');
const annonce = (p: Page, nom = 'mini') => demo(p, nom).locator('[data-test="mini-annonce"]');
const pas = async (p: Page, nom = 'mini') => Number(await etat(p, nom).getAttribute('data-pas'));
const action = (p: Page, nom = 'mini') => demo(p, nom).locator('[data-test="mini-action"]');
const validations = (p: Page, nom = 'mini') => demo(p, nom).locator('[data-test="mini-validations"] li');
const echantillons = (p: Page, nom = 'mini') => demo(p, nom).locator('[data-test="mini-echantillons"] li');
const taux = (p: Page) => demo(p).locator('[data-test="taux"]');

/** Un taux tel que la démo l'écrit : « 0,01 », « 0,3 ». */
const texteTaux = (t: number) => nombre(t, decimalesUtiles(t));

/** L'erreur d'une ligne de la liste des validations (« au pas 3 000 : 2,158 »). */
function erreurDe(ligne: string): number {
  const valeur = ligne.split(':').at(-1)!.trim();
  return Number(valeur.replace(',', '.'));
}

/** Le texte brut (textContent : Playwright ramène U+202F à une espace dans toHaveText). */
const brut = async (p: Page, nom = 'mini') => ((await etat(p, nom).textContent()) ?? '').trim();
/** Le texte brut de la zone lue par les lecteurs d'écran. */
const brutAnnonce = async (p: Page, nom = 'mini') => ((await annonce(p, nom).textContent()) ?? '').trim();

async function ouvrir(p: Page): Promise<void> {
  await p.goto(PAGE);
  await attendreHydratation(p);
  await p.locator('[data-pari="depart"] [data-juste]').click();
  // Fin du fondu d'ouverture (0,35 s) : sinon axe mesurerait un contraste à mi-chemin.
  await expect(p.locator('[data-verrou="mini"]')).toHaveCSS('opacity', '1');
}

async function allerVite(p: Page): Promise<void> {
  const bascule = demo(p).locator('[data-test="mini-vitesse"]');
  await expect(bascule).toHaveText('Aller plus vite');
  await bascule.click();
  await expect(bascule).toHaveText('Revenir au rythme normal');
}

/** Lance l'entraînement complet en vitesse rapide et attend sa fin ; renvoie l'erreur de validation finale. */
async function entrainerJusquauBout(p: Page): Promise<number> {
  await expect(action(p)).toHaveText('Lancer l’entraînement');
  await action(p).click();
  await expect(demo(p)).toHaveAttribute('data-phase', /^(termine|diverge)$/, { timeout: 120_000 });
  return erreurDe((await validations(p).allTextContents()).at(-1)!);
}

/** Les fichiers .js du site construit (dist/), le Worker compris. */
function fichiersJs(dossier: string): string[] {
  return readdirSync(dossier).flatMap((nom) => {
    const chemin = join(dossier, nom);
    if (statSync(chemin).isDirectory()) return nom === 'pagefind' ? [] : fichiersJs(chemin);
    return nom.endsWith('.js') ? [chemin] : [];
  });
}

test('avant le pari, le taux est désactivé ; après, ça apprend', async ({ page }) => {
  await page.goto(PAGE);
  await attendreHydratation(page);
  await expect(taux(page)).toHaveAttribute('aria-disabled', 'true');
  await ouvrir(page);
  await expect(taux(page)).not.toHaveAttribute('aria-disabled', 'true');
  await expect(taux(page)).toHaveAttribute('aria-valuetext', texteTaux(COMPLET.tauxMax));
  await page.locator('[data-test="mini-action"]').first().click();
  await expect.poll(() => pas(page), ATTENTE_TRAVAILLEUR).toBeGreaterThan(0);
  await expect(action(page)).toHaveText('Pause');
});

test('la page ne charge pas les prénoms avant le lancement', async ({ page }) => {
  // La ligne du milieu de la liste versionnée (Playwright tourne dans site/).
  const prenoms = readFileSync('../projets/mini-modele/donnees/prenoms.txt', 'utf8').split('\n').filter((l) => l !== '');
  // Un prénom distinctif : le premier d'au moins 7 lettres à partir du milieu (un nom
  // court pourrait se trouver par hasard dans un script sans rapport).
  const milieu = prenoms.slice(Math.floor(prenoms.length / 2)).find((p) => p.length >= 7)!;
  expect(milieu.length).toBeGreaterThanOrEqual(6);

  const scripts: { url: string; corps: string }[] = [];
  const lectures: Promise<void>[] = [];
  page.on('response', (reponse) => {
    const type = reponse.headers()['content-type'] ?? '';
    if (!/javascript/.test(type) && !/\.m?js$/.test(new URL(reponse.url()).pathname)) return;
    lectures.push(
      reponse.text().then(
        (corps) => void scripts.push({ url: reponse.url(), corps }),
        () => undefined,
      ),
    );
  });
  await page.goto(PAGE);
  await attendreHydratation(page);
  await page.locator('[data-pari="depart"] [data-juste]').click();
  await expect(taux(page)).not.toHaveAttribute('aria-disabled', 'true');
  await Promise.all(lectures);

  // Les scripts lus comprennent bien celui de l'îlot (sinon le test ne prouverait rien)…
  expect(scripts.some((s) => s.corps.includes('mini-etat')), 'le script de l’îlot MiniModele').toBe(true);
  // … et aucun ne contient le prénom du milieu de la liste.
  for (const s of scripts) expect(s.corps.includes(milieu), `${s.url} contient « ${milieu} »`).toBe(false);

  // La recherche marche : le paquet du Worker, dans dist/, contient bien ce prénom, et la page ne l'a pas chargé.
  const avecPrenoms = fichiersJs('dist').filter((f) => readFileSync(f, 'utf8').includes(milieu));
  expect(avecPrenoms.length, 'un fichier .js de dist/ contient la liste (le Worker)').toBeGreaterThan(0);
  const charges = scripts.map((s) => new URL(s.url).pathname);
  for (const f of avecPrenoms) {
    const nom = f.split(/[\\/]/).at(-1)!;
    expect(charges.some((c) => c.endsWith(`/${nom}`)), `${nom} chargé avant le lancement`).toBe(false);
  }
});

test('pause et reprise au même pas', async ({ page }) => {
  await ouvrir(page);
  await allerVite(page);
  await action(page).click();
  await expect.poll(() => pas(page), ATTENTE_TRAVAILLEUR).toBeGreaterThanOrEqual(200);
  await expect(action(page)).toHaveText('Pause');
  await action(page).click();
  // La pause est confirmée par le Worker : plus aucun progrès n'arrivera ensuite.
  await expect(demo(page)).toHaveAttribute('data-travailleur', 'en-pause');
  const n = await pas(page);
  expect(n).toBeLessThan(COMPLET.pasTotal);
  await page.waitForTimeout(1000);
  expect(await pas(page)).toBe(n);
  expect(await brut(page)).toBe(`En pause au pas ${nombre(n)} sur ${nombre(COMPLET.pasTotal)}.`);
  // Les lecteurs d'écran l'entendent, une fois la pause confirmée : la même phrase.
  expect(await brutAnnonce(page)).toBe(`En pause au pas ${nombre(n)} sur ${nombre(COMPLET.pasTotal)}.`);
  await expect(action(page)).toHaveText('Reprendre');
  await action(page).click();
  await expect.poll(() => brutAnnonce(page)).toBe(`Entraînement repris au pas ${nombre(n)}.`);
  await expect.poll(() => pas(page), ATTENTE_TRAVAILLEUR).toBeGreaterThan(n);
});

test('onglet caché : pause automatique', async ({ page }) => {
  await ouvrir(page);
  await action(page).click();
  await expect.poll(() => pas(page), ATTENTE_TRAVAILLEUR).toBeGreaterThan(0);
  await page.evaluate(() => {
    Object.defineProperty(document, 'hidden', { value: true, configurable: true });
    Object.defineProperty(document, 'visibilityState', { value: 'hidden', configurable: true });
    document.dispatchEvent(new Event('visibilitychange'));
  });
  await expect(etat(page)).toContainText('En pause\u202F: l’onglet était caché.');
  expect(await brut(page)).toBe(MESSAGE_ONGLET);
  expect(await brutAnnonce(page)).toBe(MESSAGE_ONGLET);
  await expect(demo(page)).toHaveAttribute('data-travailleur', 'en-pause');
  const n = await pas(page);
  await page.waitForTimeout(1000);
  expect(await pas(page)).toBe(n);
  // À la reprise, pas de rafale de rattrapage : au rythme normal, au plus 150 pas par seconde.
  await action(page).click();
  await page.waitForTimeout(1000);
  const apres = await pas(page);
  expect(apres).toBeGreaterThan(n);
  expect(apres - n).toBeLessThanOrEqual(230);
});

test('recommencer : courbe fantôme, et le même réglage redonne les mêmes erreurs', async ({ page }) => {
  await ouvrir(page);
  await expect(demo(page).locator('[data-test="mini-recommencer"]')).toBeDisabled(); // rien à recommencer
  await allerVite(page);
  await action(page).click();
  await expect.poll(() => validations(page).count(), ATTENTE_TRAVAILLEUR).toBeGreaterThanOrEqual(4);
  const avant = (await validations(page).allTextContents()).slice(0, 3);
  await expect(demo(page).locator('[data-test="courbe-fantome"]')).toHaveCount(0);

  await demo(page).locator('[data-test="mini-recommencer"]').click();
  await expect(etat(page)).toHaveAttribute('data-pas', '0');
  // Rien n'est dit, et l'annonce de l'essai d'avant ne reste pas.
  expect(await brutAnnonce(page)).toBe('');
  await expect(validations(page)).toHaveCount(1);
  await expect(demo(page).locator('[data-test="courbe-fantome"]')).toHaveAttribute('d', /^M[\d.]+,[\d.]+L/);
  await expect(demo(page).locator('figcaption')).toContainText(`l’essai d’avant, au taux de ${texteTaux(COMPLET.tauxMax)}`);
  // Les messages de l'ancien essai sont ignorés : rien ne bouge avant le nouveau lancement.
  await page.waitForTimeout(500);
  expect(await pas(page)).toBe(0);

  await expect(action(page)).toHaveText('Lancer l’entraînement');
  await action(page).click();
  await expect.poll(() => validations(page).count(), ATTENTE_TRAVAILLEUR).toBeGreaterThanOrEqual(4);
  expect((await validations(page).allTextContents()).slice(0, 3)).toEqual(avant);
});

test('changer le taux repart de zéro', async ({ page }) => {
  await ouvrir(page);
  await action(page).click();
  await expect.poll(() => pas(page), ATTENTE_TRAVAILLEUR).toBeGreaterThan(0);
  const suivant = TAUX_PROPOSES[TAUX_PROPOSES.indexOf(COMPLET.tauxMax) + 1];
  await taux(page).focus();
  await page.keyboard.press('ArrowRight');
  await expect(taux(page)).toHaveAttribute('aria-valuetext', texteTaux(suivant));
  await expect(taux(page)).toHaveText(texteTaux(suivant));
  await expect(etat(page)).toHaveAttribute('data-pas', '0');
  expect(await brut(page)).toBe(MESSAGE_NOUVEAU_TAUX);
  expect(await brutAnnonce(page)).toBe(MESSAGE_NOUVEAU_TAUX);
  await expect(demo(page)).toHaveAttribute('data-phase', 'pret');
  await expect(action(page)).toHaveText('Lancer l’entraînement');
  await expect(demo(page).locator('[data-test="courbe-fantome"]')).toHaveCount(1);
  // L'ancien essai ne revient pas.
  await page.waitForTimeout(500);
  expect(await pas(page)).toBe(0);
  // Le nouveau part au nouveau taux.
  await action(page).click();
  await expect.poll(() => pas(page), ATTENTE_TRAVAILLEUR).toBeGreaterThan(0);
});

test('entraînement complet : erreur finale ≤ 2,45 et acquis gagné', async ({ page }) => {
  test.setTimeout(150_000);
  await ouvrir(page);
  await expect(page.locator('#recap [data-acquis="entraine"]')).toHaveAttribute('data-gagne', 'non');
  await allerVite(page);
  // Le focus du clavier sur le bouton principal pendant l'entraînement : il y reste à la fin.
  await expect(action(page)).toHaveText('Lancer l’entraînement');
  await action(page).focus();
  await page.keyboard.press('Enter');
  await expect(action(page)).toHaveText('Pause');
  await expect(demo(page)).toHaveAttribute('data-phase', 'termine', { timeout: 120_000 });
  const finale = erreurDe((await validations(page).allTextContents()).at(-1)!);
  expect(finale).toBeLessThanOrEqual(2.45);
  await expect(validations(page)).toHaveCount(COMPLET.pasTotal / COMPLET.validationTous + 1);
  await expect(validations(page).last()).toContainText(`au pas ${nombre(COMPLET.pasTotal)}`);
  await expect(etat(page)).toHaveAttribute('data-pas', String(COMPLET.pasTotal));
  expect(await brut(page)).toMatch(new RegExp(`^Terminé${FINE}: ${nombre(COMPLET.pasTotal)} pas en \\d+ s\\.$`));
  expect(await brutAnnonce(page)).toBe(await brut(page));
  await expect(action(page)).toHaveText('Terminé');
  // Désactivé (aria-disabled), mais toujours focalisé, et il ne fait plus rien.
  await expect(action(page)).toBeDisabled();
  await expect(action(page)).toHaveAttribute('aria-disabled', 'true');
  await expect(action(page)).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(demo(page)).toHaveAttribute('data-phase', 'termine');
  await expect(action(page)).toHaveText('Terminé');
  await expect(page.locator('#recap [data-acquis="entraine"]')).toHaveAttribute('data-gagne', 'oui');
  await expect(echantillons(page)).toHaveCount(COMPLET.nbEchantillons);
  await expect(demo(page)).toContainText(`Les prénoms qu’il invente au pas ${nombre(COMPLET.pasTotal)}`);
  await expect(demo(page).locator('[data-test="courbe"]')).toHaveAttribute(
    'aria-label',
    new RegExp(`au pas 0, .* au pas ${nombre(COMPLET.pasTotal)}\\.`),
  );
});

test('taux trop grand (0,3) : la courbe reste lisible, et l’erreur finale est moins bonne qu’à 0,01', async ({ page }) => {
  test.setTimeout(270_000);
  await ouvrir(page);
  await allerVite(page);
  const normale = await entrainerJusquauBout(page);
  await taux(page).focus();
  await page.keyboard.press('End');
  await expect(taux(page)).toHaveAttribute('aria-valuetext', texteTaux(TAUX_PROPOSES.at(-1)!));
  await entrainerJusquauBout(page);
  const chemins = await demo(page)
    .locator('[data-test="courbe"] path')
    .evaluateAll((ps) => ps.map((p) => p.getAttribute('d') ?? ''));
  expect(chemins.length).toBeGreaterThanOrEqual(3); // le fantôme, l'entraînement, les points de validation
  for (const d of chemins) expect(d).not.toMatch(/NaN|Infinity/);
  if ((await demo(page).getAttribute('data-phase')) === 'diverge') {
    expect(await brut(page)).toBe(MESSAGE_DIVERGENCE);
    await expect(demo(page).locator('[data-test="hors-echelle"]')).toBeVisible();
    await expect(action(page)).toHaveText('Entraînement arrêté');
  } else {
    const finale = erreurDe((await validations(page).allTextContents()).at(-1)!);
    expect(finale).toBeGreaterThan(normale);
  }
});

// Aucun taux proposé ne fait exploser l'erreur : pour voir le rendu d'une
// explosion, le parcours remplace le Worker par un faux, servi à la place du
// vrai fichier (page.route). Il suit le même protocole de messages, et passe
// donc par le vrai réducteur et le vrai composant ; rien de cela n'entre dans
// le site. Au lancement, il envoie 38 pas ordinaires ; quand la page lui
// envoie la vitesse, il envoie le pas 39 (au-dessus du cadre, mais noyé dans
// la moyenne de son paquet de 25 pas), le pas 40 (NaN, que les moyennes
// ignorent), puis « diverge », comme la vraie boucle.
const FAUX_TRAVAILLEUR = `
let generation = null;
self.onmessage = (evenement) => {
  const m = evenement.data;
  if (m.type === 'lancer') {
    generation = m.generation;
    const pertes = [];
    for (let i = 0; i < 38; i++) pertes.push(3.6 - i * 0.03);
    self.postMessage({ type: 'progres', generation, pas: 38, pasTotal: 3000, pertes, dureeMs: 300, pasParSeconde: 127 });
  } else if (m.type === 'vitesse' && m.generation === generation) {
    self.postMessage({ type: 'progres', generation, pas: 40, pasTotal: 3000, pertes: [12.5, NaN], dureeMs: 320, pasParSeconde: 125 });
    self.postMessage({ type: 'etat', generation, etat: 'diverge' });
  }
};
`;

test('explosion de l’erreur : message exact, repère « hors échelle », aucun NaN dans la courbe', async ({ page }) => {
  let servi = false;
  await page.route(/\/_astro\/travailleur-[^/]*\.js$/, (route) => {
    servi = true;
    return route.fulfill({ contentType: 'text/javascript', body: FAUX_TRAVAILLEUR });
  });
  await ouvrir(page);
  const repere = demo(page).locator('[data-test="hors-echelle"]');
  await action(page).click();
  // Le lancement s'annonce tout de suite, avant la première validation.
  await expect.poll(() => brut(page)).toBe('Entraînement lancé.');
  expect(await brutAnnonce(page)).toBe('Entraînement lancé.');
  await expect(etat(page)).toHaveAttribute('data-pas', '38', ATTENTE_TRAVAILLEUR);
  expect(servi, 'le faux Worker a bien été servi').toBe(true);
  await expect(repere).toHaveCount(0);

  // La vitesse change par un clic qui ne déplace pas le focus : il reste sur le bouton principal.
  await action(page).focus();
  await demo(page).locator('[data-test="mini-vitesse"]').dispatchEvent('click');
  await expect(demo(page)).toHaveAttribute('data-phase', 'diverge');
  expect(await brut(page)).toBe(MESSAGE_DIVERGENCE);
  expect(await brutAnnonce(page)).toBe(MESSAGE_DIVERGENCE);
  await expect(action(page)).toHaveText('Entraînement arrêté');
  await expect(action(page)).toBeDisabled();
  await expect(action(page)).toBeFocused();
  // Le repère, avec son texte exact (la flèche est un décor CSS).
  await expect(repere).toBeVisible();
  expect(await repere.textContent()).toBe('hors échelle');
  const courbe = demo(page).locator('[data-test="courbe"]');
  await expect(courbe).toHaveAttribute('aria-label', /La courbe sort du cadre par le haut\.$/);
  const chemins = await courbe.locator('path').evaluateAll((ps) => ps.map((p) => p.getAttribute('d') ?? ''));
  for (const d of chemins) expect(d).not.toMatch(/NaN|Infinity/);
  // Le chemin de l'entraînement lui-même : tracé (au moins un point), sans NaN ni Infinity.
  const entrainement = (await courbe.locator('[data-test="courbe-entrainement"]').getAttribute('d')) ?? '';
  expect(entrainement).toMatch(/^M[\d.]+,[\d.]+/);
  expect(entrainement).not.toMatch(/NaN|Infinity/);
  // La sortie est près du pas 0 : le repère ne chevauche pas le titre « erreur ».
  const titre = (await demo(page).locator('.titre-y').boundingBox())!;
  const boite = (await repere.boundingBox())!;
  const chevauche =
    boite.x < titre.x + titre.width && titre.x < boite.x + boite.width && boite.y < titre.y + titre.height && titre.y < boite.y + boite.height;
  expect(chevauche, 'le repère chevauche le titre de l’axe').toBe(false);
  await verifierAxe(page);
  await verifierSansDebordement(page);
});

// Un faux Worker pas à pas, pour la zone lue par les lecteurs d'écran : au lancement, il fait
// les pas 1 à 900, avec une validation tous les 100 pas (neuf messages) ; puis, chaque fois que
// la page lui envoie la vitesse, les 100 pas suivants (1 000, 1 100, 1 200), et enfin d'un coup
// jusqu'à 2 000. Le parcours avance donc d'une validation à la fois, sans course contre l'horloge.
const TRAVAILLEUR_PAS_A_PAS = `
let generation = null;
let pas = 0;
function avancer(jusqua) {
  while (pas < jusqua) {
    const debut = pas;
    pas += 100;
    const pertes = [];
    for (let i = debut; i < pas; i++) pertes.push(3.5 - i * 0.0004);
    self.postMessage({
      type: 'progres', generation, pas, pasTotal: 3000, pertes, dureeMs: pas * 7, pasParSeconde: 140,
      validation: { pas, perte: 3.4 - pas * 0.0004 },
    });
  }
}
self.onmessage = (evenement) => {
  const m = evenement.data;
  if (m.type === 'lancer') {
    generation = m.generation;
    avancer(900);
  } else if (m.type === 'vitesse' && m.generation === generation) {
    avancer(pas < 1200 ? pas + 100 : 2000);
  }
};
`;

test('la zone lue ne change pas entre deux validations sous un palier de 1 000 pas', async ({ page }) => {
  await page.route(/\/_astro\/travailleur-[^/]*\.js$/, (route) =>
    route.fulfill({ contentType: 'text/javascript', body: TRAVAILLEUR_PAS_A_PAS }),
  );
  await ouvrir(page);
  const vitesse = demo(page).locator('[data-test="mini-vitesse"]');
  await action(page).click();
  // Neuf validations, de 100 à 900 : la ligne visible les suit, la zone lue garde l'annonce du lancement.
  await expect(etat(page)).toHaveAttribute('data-pas', '900', ATTENTE_TRAVAILLEUR);
  await expect(validations(page)).toHaveCount(10);
  expect(await brut(page)).toMatch(/^Pas 900 sur /);
  expect(await brutAnnonce(page)).toBe('Entraînement lancé.');
  // 1 000 : annoncé, avec la ligne visible de ce moment.
  await vitesse.click();
  await expect(etat(page)).toHaveAttribute('data-pas', '1000');
  const palier = await brut(page);
  expect(palier).toMatch(new RegExp(`^Pas ${nombre(1000)} sur ${nombre(3000)}${FINE}: erreur `));
  expect(await brutAnnonce(page)).toBe(palier);
  // À partir d'ici, on compte chaque changement de la zone lue.
  await annonce(page).evaluate((el) => {
    const w = window as unknown as { changementsAnnonce: number };
    w.changementsAnnonce = 0;
    new MutationObserver((ms) => (w.changementsAnnonce += ms.length)).observe(el, {
      childList: true,
      characterData: true,
      subtree: true,
    });
  });
  const changements = () => page.evaluate(() => (window as unknown as { changementsAnnonce: number }).changementsAnnonce);
  // 1 100 puis 1 200 : deux validations de suite sous 2 000. La ligne visible change, la zone lue non.
  await vitesse.click();
  await expect(etat(page)).toHaveAttribute('data-pas', '1100');
  const ligne1100 = await brut(page);
  expect(ligne1100).not.toBe(palier);
  await vitesse.click();
  await expect(etat(page)).toHaveAttribute('data-pas', '1200');
  expect(await brut(page)).not.toBe(ligne1100);
  expect(await brutAnnonce(page)).toBe(palier);
  expect(await changements()).toBe(0);
  // 2 000 : annoncé de nouveau.
  await vitesse.click();
  await expect(etat(page)).toHaveAttribute('data-pas', '2000');
  expect(await brutAnnonce(page)).toBe(await brut(page));
  expect(await brutAnnonce(page)).toMatch(new RegExp(`^Pas ${nombre(2000)} sur `));
  expect(await changements()).toBeGreaterThan(0);
});

test('le taux se règle au glissé, un cran tous les 24 px', async ({ page }) => {
  await ouvrir(page);
  const t = taux(page);
  await t.scrollIntoViewIfNeeded();
  const depart = TAUX_PROPOSES.indexOf(COMPLET.tauxMax);
  expect(depart).toBeGreaterThanOrEqual(2);
  expect(depart).toBeLessThanOrEqual(TAUX_PROPOSES.length - 3);
  const boite = (await t.boundingBox())!;
  const x = boite.x + boite.width / 2;
  const y = boite.y + boite.height / 2;
  await page.mouse.move(x, y);
  await page.mouse.down();
  // 30 px : un seul cran (à 6 px par cran, comme le nombre de l'atelier, ce serait cinq).
  await page.mouse.move(x + 30, y, { steps: 5 });
  await expect(t).toHaveAttribute('aria-valuenow', String(depart + 1));
  await page.mouse.move(x + 50, y, { steps: 3 });
  await expect(t).toHaveAttribute('aria-valuenow', String(depart + 2));
  await page.mouse.move(x - 30, y, { steps: 6 });
  await expect(t).toHaveAttribute('aria-valuenow', String(depart - 1));
  await page.mouse.up();
  await expect(t).toHaveAttribute('aria-valuetext', texteTaux(TAUX_PROPOSES[depart - 1]));
});

test('au doigt, le taux avance d’un cran pour 30 px', async ({ page, isMobile }) => {
  test.skip(!isMobile, 'le toucher se teste sur le projet mobile');
  await ouvrir(page);
  const t = taux(page);
  await t.scrollIntoViewIfNeeded();
  const depart = TAUX_PROPOSES.indexOf(COMPLET.tauxMax);
  const boite = (await t.boundingBox())!;
  const x = Math.round(boite.x + boite.width / 2);
  const y = Math.round(boite.y + boite.height / 2);
  // Playwright n'a pas de geste de glissé au doigt : on passe par Chrome directement.
  const cdp = await page.context().newCDPSession(page);
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x, y }] });
  for (let i = 1; i <= 10; i++) {
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: x + i * 3, y }] });
  }
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
  await expect(t).toHaveAttribute('aria-valuenow', String(depart + 1));
});

test('avant-goût : 600 pas, sans réglage de taux', async ({ page }) => {
  test.setTimeout(90_000);
  await page.goto(PAGE);
  await attendreHydratation(page);
  const ag = demo(page, 'avant-gout');
  await expect(ag.locator('[data-test="taux"]')).toHaveCount(0);
  await expect(ag.locator('[data-test="mini-vitesse"]')).toHaveCount(0);
  await expect(ag).toContainText(`Il va s’entraîner pendant ${AVANT_GOUT.pasTotal} pas.`);
  // Pas de verrou : il se lance sans pari.
  await action(page, 'avant-gout').click();
  await expect(ag).toHaveAttribute('data-phase', 'termine', { timeout: 60_000 });
  await expect(etat(page, 'avant-gout')).toHaveAttribute('data-pas', String(AVANT_GOUT.pasTotal));
  expect(await brut(page, 'avant-gout')).toMatch(new RegExp(`^Terminé${FINE}: ${AVANT_GOUT.pasTotal} pas en \\d+ s\\.$`));
  await expect(validations(page, 'avant-gout')).toHaveCount(AVANT_GOUT.pasTotal / AVANT_GOUT.validationTous + 1);
  await expect(echantillons(page, 'avant-gout')).toHaveCount(AVANT_GOUT.nbEchantillons);
  // Les prénoms du départ restent là, dans les étapes d'avant.
  const avant = ag.locator('details.avant');
  await avant.locator('summary').click();
  await expect(avant).toContainText('au pas 0');
  // Le lien vers le chapitre 1.5, seulement s'il est paru.
  await expect(ag).toContainText('Tu le fabriqueras au chapitre 1.5.');
  const paru = existsSync('src/content/chapitres/1-5.mdx');
  await expect(ag.getByRole('link', { name: 'chapitre 1.5' })).toHaveCount(paru ? 1 : 0);
  // L'entraînement complet n'a pas bougé, ni son acquis.
  expect(await pas(page)).toBe(0);
  await expect(page.locator('#recap [data-acquis="entraine"]')).toHaveAttribute('data-gagne', 'non');
});

test('sans JavaScript : message et valeurs du départ', async ({ browser, baseURL }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false, baseURL });
  const page = await ctx.newPage();
  await page.goto(PAGE);
  // La bonne réponse du pari « depart » est l'erreur du pas 0, calculée à la construction.
  const depart = ((await page.locator('[data-pari="depart"] [data-juste]').textContent()) ?? '').trim();
  expect(depart).toMatch(/^\d,\d{3}$/);
  for (const nom of ['mini', 'avant-gout']) {
    const d = demo(page, nom);
    await expect(d.getByText('Cette démo calcule dans ton navigateur')).toBeVisible();
    await expect(d.locator('[data-test="mini-action"]')).toBeHidden();
    await expect(d.locator('[data-test="mini-recommencer"]')).toBeHidden();
    await expect(validations(page, nom)).toHaveText([`au pas 0${FINE}: ${depart}`]);
    await expect(echantillons(page, nom)).toHaveCount(8);
    await expect(echantillons(page, nom).first()).toBeVisible();
    await expect(d.locator('[data-test="courbe"]')).toBeVisible();
    await expect(d.locator('[data-test="courbe"]')).toHaveAttribute('aria-label', `Courbe de l’erreur${FINE}: ${depart} au pas 0.`);
  }
  const pasTotal = nombre(COMPLET.pasTotal);
  expect(((await etat(page).textContent()) ?? '').trim()).toBe(`Pas 0 sur ${pasTotal}${FINE}: erreur ${depart}.`);
  await ctx.close();
});

test('accessibilité, largeur, typographie', async ({ page }) => {
  await ouvrir(page);
  // Au départ, avant tout entraînement.
  await verifierAxe(page);
  await verifierSansDebordement(page);
  await verifierTypographie(demo(page));
  // En cours, puis en pause, avec les prénoms des étapes d'avant ouverts.
  await allerVite(page);
  await action(page).click();
  await expect.poll(() => validations(page).count(), ATTENTE_TRAVAILLEUR).toBeGreaterThanOrEqual(4);
  await action(page).click();
  await expect(demo(page)).toHaveAttribute('data-travailleur', 'en-pause');
  await demo(page).locator('details.avant summary').click();
  await verifierAxe(page);
  await verifierSansDebordement(page);
  await verifierTypographie(demo(page));
  await verifierTypographie(demo(page, 'avant-gout'));
  await verifierTypographie(page.locator('main'));
  // Des cibles d'au moins 24 px sur 24 px.
  for (const bouton of await page.locator('.mini-modele button, .mini-modele summary').all()) {
    if (!(await bouton.isVisible())) continue;
    const boite = (await bouton.boundingBox())!;
    expect(boite.height, await bouton.innerText()).toBeGreaterThanOrEqual(24);
    expect(boite.width, await bouton.innerText()).toBeGreaterThanOrEqual(24);
  }
  // La ligne d'état n'a jamais pris le focus.
  await expect(etat(page)).not.toBeFocused();
  // Une seule zone lue d'office par démo : la zone cachée, pas la ligne visible.
  for (const nom of ['mini', 'avant-gout']) {
    await expect(demo(page, nom).getByRole('status')).toHaveCount(1);
    await expect(demo(page, nom).getByRole('status')).toHaveAttribute('data-test', 'mini-annonce');
    await expect(demo(page, nom).getByRole('status')).toHaveClass(/\bvh\b/);
    await expect(etat(page, nom)).not.toHaveAttribute('role', /.*/);
  }
});
