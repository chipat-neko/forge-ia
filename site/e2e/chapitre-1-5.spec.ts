// Parcours du chapitre 1.5, « Le pré-entraînement sur ton GPU » : un brouillon
// (src/brouillons/chapitres/1-5.mdx) tant qu'il n'a pas paru, construit à son adresse
// définitive avec FORGE_ESSAIS=1.
//
// Les attendus viennent des relevés du projet 1.5, lus sur le disque (journal.ts, paris-1-5.ts),
// des commandes (commandes.ts), des sources (sources-1-5.ts) et du code montré, relu dans les
// fichiers du projet et de forge, tels qu'ils sont aujourd'hui. Un parcours, chargé par Node sans
// Vite, n'importe ni ?raw, ni .json, ni astro:* (P8) : il ne passe donc ni par le moteur du
// mini-modèle (ses prénoms sont en ?raw), ni par defi-1-5.ts. Le pari du taux et le défi se
// vérifient sur ce que la page affiche ; leurs nombres viennent du moteur, vérifié par Vitest.
//
// Tant que l'entraînement principal de ton IA n'est pas relevé (ton-ia-1.5.json, tâche 16),
// l'étape 8 est « à mesurer ».
import { readFileSync } from 'node:fs';
import { test, expect, type Page } from '@playwright/test';
import type { Choix } from '../src/lib/choix';
import { formaterPerte, nombre } from '../src/lib/nombres';
import { trouverChapitre } from '../src/lib/parcours';
import { CLONER_DEPOT, METTRE_A_JOUR_DEPOT } from '../src/lib/partie-0/commandes';
import * as commandes from '../src/lib/partie-1/commandes';
import { lireEchantillon } from '../src/lib/partie-1/evaluation';
import { lireEntrainement } from '../src/lib/partie-1/journal';
import { MESURES_PARTIE_1 } from '../src/lib/partie-1/mesures';
import {
  choixDebitCourte,
  choixPerteDepartTonIA,
  choixReprise,
  ECART_DU_DEFI,
  lignesDeLaCourbe,
  lignesDesSessions,
  lireEssaiDeReprise,
} from '../src/lib/partie-1/paris-1-5';
import { LLAMA_31_405B, SOURCES_LABO_1_5 } from '../src/lib/partie-1/sources-1-5';
import { PRESETS_MINI, TAUX_PROPOSES } from '../src/lib/mini-modele/reglages';
import { extraireRegion } from '../src/lib/regions';
import { lireSortie } from '../src/lib/sorties';
import { extraireSymbole } from '../src/lib/symboles';
import { typographier } from '../src/lib/typo';
import {
  attendreHydratation,
  plusLongueLigne,
  texteHorsCode,
  verifierAxe,
  verifierLiensVersParus,
  verifierSansDebordement,
  verifierTypographieHorsCode,
  verifierVoisin,
} from './outils';

const PAGE = '/forge-ia/partie-1/1-5/';
const FINE = '\u202F';

// Playwright tourne dans site/ : lireEntrainement et lireEssaiDeReprise lisent le dépôt, un dossier plus haut.
const MINI = lireEntrainement('ton-ia-mini')!;
const TON_IA_15 = lireEntrainement('ton-ia-1.5');
// Le texte que mini écrit dans l'ouverture : la suite d'un début fixe de son rapport d'évaluation (null si le relevé manque).
const INVITE_DE_L_OUVERTURE = 'La capitale de la France est';
const ECRIT_PAR_MINI = lireEchantillon('ton-ia-mini', INVITE_DE_L_OUVERTURE);
const ESSAI = lireEssaiDeReprise();
const COMPLET = PRESETS_MINI.complet;

// Ce qui n'est pas du texte du chapitre mais des données brutes : les prénoms inventés par la démo.
const BRUT = '[data-mini] .prenoms, [data-mini] .avant';

/** Les commandes que les blocs « À taper » du chapitre montrent, dans l'ordre de la page. */
const COMMANDES_DES_BLOCS = [
  [commandes.REPRENDRE],
  [...commandes.ENTRAINER_COURT],
  [METTRE_A_JOUR_DEPOT, commandes.ALLER_AU_PROJET_1_5],
  [CLONER_DEPOT, commandes.ALLER_AU_PROJET_1_5],
  [commandes.PRE_ENTRAINEMENT_ESSAI],
  [commandes.PRE_ENTRAINEMENT_COURBE],
  [commandes.PRE_ENTRAINEMENT_TESTS],
];

/** Le texte d'un choix tel qu'un bouton l'affiche : le code tel quel, le reste typographié. */
function affiche(choix: Choix): string {
  return choix.texte
    .split('`')
    .map((morceau, i) => (i % 2 === 1 ? morceau : typographier(morceau)))
    .join('');
}

/** Un nombre affiché à la française (« 2,186 ») relu en nombre. */
function relire(texte: string): number {
  return Number(texte.replace(/[\s\u202F\u00A0]/g, '').replace(',', '.'));
}

/** Attend la fin des animations en cours (fondu des verrous, verdict des paris) : axe mesure alors les vraies couleurs. */
async function attendreAnimations(page: Page): Promise<void> {
  await page.evaluate(() => Promise.all(document.getAnimations().map((a) => a.finished)).then(() => undefined));
}

test('chapitre 1.5 complet', async ({ page }, info) => {
  // Un entraînement complet du petit modèle, dans le navigateur, en vitesse rapide.
  test.setTimeout(180_000);
  const reponse = await page.goto(PAGE);
  expect(reponse?.status()).toBe(200);
  await attendreHydratation(page);
  const { total } = trouverChapitre('1.5');
  await expect(page.locator('header')).toContainText(`Partie 1, chapitre 1.5 sur ${total}`);
  if (info.project.name === 'mobile') expect(page.viewportSize()?.width).toBe(390);
  await expect(page.locator('.pari[data-pari]')).toHaveCount(4);
  await page.locator('[data-pari="depart"] [data-juste]').click();
  await page.locator('[data-pari="taux"] [data-juste]').click();
  await expect(page.locator('[data-verrou="atelier"]')).not.toHaveAttribute('inert', '');
  // L'acquis de l'atelier se gagne au bout d'un entraînement complet du petit modèle.
  const demo = page.locator('[data-mini="mini"]');
  await expect(page.locator('#recap [data-acquis="atelier"]')).toHaveAttribute('data-gagne', 'non');
  await demo.locator('[data-test="mini-vitesse"]').click();
  await demo.locator('[data-test="mini-action"]').click();
  await expect(demo).toHaveAttribute('data-phase', 'termine', { timeout: 150_000 });
  await expect(page.locator('#recap [data-acquis="atelier"]')).toHaveAttribute('data-gagne', 'oui');
  await page.locator('[data-pari="reprise"] [data-juste]').click();
  await page.locator('[data-pari="courte"] [data-juste]').click();
  await expect(page.locator('#recap [data-total]')).toContainText('5 sur 5');
  // Le pied suit les fichiers : 1.4 a paru, 1.6 est « à venir » tant qu'il n'a pas paru.
  await verifierVoisin(page, 'precedent', '1-4.mdx', '/forge-ia/partie-1/1-4/');
  await verifierVoisin(page, 'suivant', '1-6.mdx', '/forge-ia/partie-1/1-6/');
  await verifierLiensVersParus(page.locator('main'), PAGE);
  await attendreAnimations(page);
  await verifierAxe(page);
  await verifierSansDebordement(page);
  await verifierTypographieHorsCode(page.locator('main'), BRUT);
  // Aucune expression du MDX restée en texte (une accolade tombée dans un passage de code, par exemple).
  expect(await texteHorsCode(page.locator('main'))).not.toMatch(/[{}]/);
  // Le code en ligne seulement : le Python montré a ses propres accolades (des dictionnaires).
  expect(await page.locator('main :not(pre) > code').allTextContents()).not.toContainEqual(expect.stringMatching(/[{}]/));
  expect(await page.locator('main').innerText()).not.toMatch(/NaN|Infinity|undefined|\de\+/);
  const { longueur, ligne } = await plusLongueLigne(page);
  expect(longueur, `ligne la plus longue : « ${ligne} »`).toBeLessThanOrEqual(80);
});

test('la courbe de la version d’une heure se dessine, et ses tableaux disent la même chose', async ({ page }) => {
  await page.goto(PAGE);
  const figure = page.locator('[data-courbe="ton-ia-mini"]');
  await expect(figure).toBeVisible();
  // La perte d'entraînement, les points de validation, le hasard.
  const trace = (await figure.locator('[data-test="courbe-entrainement"]').getAttribute('d')) ?? '';
  expect(trace).toMatch(/^M[\d.]+,[\d.]+(L[\d.]+,[\d.]+)+$/);
  expect(trace.split('L')).toHaveLength(MINI.courbe.pertes.length);
  const points = (await figure.locator('[data-test="courbe-validation"]').getAttribute('d')) ?? '';
  expect(points.match(/h0/g)).toHaveLength(MINI.courbe.validations.length);
  const svg = figure.locator('[data-test="courbe-svg"]');
  await expect(svg.locator('line.hasard')).toHaveCount(1);
  // Une seule session, sans pause : aucun arrêt sur la courbe, ni dans sa légende.
  await expect(figure.locator('line.arret')).toHaveCount(0);
  const boite = await figure.locator('[data-test="courbe-svg"]').boundingBox();
  expect(boite!.width).toBeGreaterThan(300);
  expect(boite!.height).toBeGreaterThan(150);
  // Le tableau caché : une ligne par validation, aux valeurs du relevé.
  const lignes = figure.locator('[data-test="courbe-tableau"] tbody tr');
  const attendues = lignesDeLaCourbe(MINI.courbe);
  await expect(lignes).toHaveCount(attendues.length);
  for (const i of [0, Math.floor(attendues.length / 2), attendues.length - 1]) {
    const cases = await lignes.nth(i).locator('th, td').allTextContents();
    const l = attendues[i];
    expect(cases).toStrictEqual([nombre(l.pas), formaterPerte(l.entrainement!), formaterPerte(l.validation!)]);
  }
  // Le tableau des sessions : celles du relevé.
  const sessions = page.locator('[data-sessions="ton-ia-mini"] [data-test="sessions"]');
  const attenduesSessions = lignesDesSessions(MINI.sessions);
  await expect(sessions.locator('tbody tr')).toHaveCount(attenduesSessions.length);
  for (const [i, l] of attenduesSessions.entries()) {
    expect(await sessions.locator('tbody tr').nth(i).locator('th, td').allTextContents()).toStrictEqual([
      nombre(l.numero),
      l.debut,
      l.fin,
      l.pas,
      l.duree,
    ]);
  }
  await expect(sessions.locator('tfoot')).toContainText(`${nombre(MINI.resume.pas_faits)} pas`);
});

test('ton IA, la vraie : « à mesurer » tant que son entraînement n’est pas relevé', async ({ page }) => {
  await page.goto(PAGE);
  const etape8 = page.locator('#etape-8');
  if (TON_IA_15 === null) {
    expect(await etape8.locator('[data-a-mesurer]').count()).toBeGreaterThanOrEqual(1);
    await expect(etape8.locator('[data-courbe-absente="ton-ia-1.5"]')).toBeVisible();
    await expect(etape8.locator('[data-sessions-absentes="ton-ia-1.5"]')).toBeVisible();
    await expect(etape8.locator('[data-courbe="ton-ia-1.5"]')).toHaveCount(0);
    await expect(etape8.locator('p[data-a-mesurer]')).toHaveCount(3);
  } else {
    await expect(etape8.locator('[data-a-mesurer]')).toHaveCount(0);
    await expect(etape8.locator('[data-courbe="ton-ia-1.5"]')).toBeVisible();
  }
  // L'échantillon de l'ouverture vient du relevé du rapport d'évaluation de mini (projet 1.6, evaluation.ts) : « à mesurer » seulement s'il manque.
  const echantillon = page.locator('#etape-1 [data-echantillon="dernier"]');
  if (ECRIT_PAR_MINI === null) {
    await expect(echantillon.and(page.locator('[data-a-mesurer]'))).toBeVisible();
  } else {
    await expect(echantillon).toBeVisible();
    await expect(echantillon).not.toHaveAttribute('data-a-mesurer', /.*/);
    await expect(echantillon.locator('[data-test="echantillon-dernier"]')).toHaveText(INVITE_DE_L_OUVERTURE + ECRIT_PAR_MINI.suite);
  }
  // Le texte de l'étape 8 ne donne aucun nombre de l'entraînement principal, seulement sa configuration.
  await expect(etape8).toContainText('Quand le PC servait à autre chose');
});

test('les commandes affichées sont celles de commandes.ts, et les chemins de l’auteur sont signalés', async ({ page }) => {
  await page.goto(PAGE);
  const blocs = await page
    .locator('.bloc-commande pre code')
    .evaluateAll((codes) => codes.map((c) => (c.textContent ?? '').split('\n')));
  expect(blocs).toEqual(COMMANDES_DES_BLOCS);
  // La sortie de l'essai : celle du fichier enregistré par le projet, après sa commande.
  const sortie = lireSortie(readFileSync(`../${MESURES_PARTIE_1.sortieEssaiProcesseur}`, 'utf8'), MESURES_PARTIE_1.sortieEssaiProcesseur);
  expect(sortie).not.toBeNull();
  const bloc = page.locator(`[data-sortie="${MESURES_PARTIE_1.sortieEssaiProcesseur}"]`);
  expect(await bloc.locator('[data-contenu]').textContent()).toBe(sortie!.contenu);
  expect(await bloc.locator('.commande').textContent()).toBe(commandes.PRE_ENTRAINEMENT_ESSAI);
  // Ctrl+C met en pause : la phrase de commandes.ts.
  await expect(page.locator('#etape-6')).toContainText(commandes.PAUSE);
  // Les blocs qui contiennent un chemin D:\ sont suivis d'une phrase qui dit de le remplacer.
  for (const commande of [commandes.COURT_EVALUER, commandes.PRE_ENTRAINEMENT_COURBE]) {
    expect(commande).toContain('D:\\');
    const figure = page.locator('.bloc-commande').filter({ hasText: commande });
    const suite = figure.locator('xpath=following-sibling::p[1]');
    await expect(suite, commande).toContainText('PC de l’auteur');
    await expect(suite, commande).toContainText('remplace');
  }
  await expect(page.getByRole('link', { name: 'Le projet complet' })).toHaveAttribute(
    'href',
    'https://github.com/chipat-neko/forge-ia/tree/main/projets/1.5-pre-entrainement',
  );
});

test('les choix des paris viennent des relevés du projet', async ({ page }) => {
  await page.goto(PAGE);
  const paris: [string, Choix[]][] = [
    ['depart', choixPerteDepartTonIA(MINI)],
    ['reprise', choixReprise(ESSAI)],
    ['courte', choixDebitCourte(MINI)],
  ];
  for (const [id, choix] of paris) {
    expect(await page.locator(`[data-pari="${id}"] button[data-choix]`).allTextContents(), id).toEqual(choix.map(affiche));
    expect(await page.locator(`[data-pari="${id}"] [data-juste]`).textContent(), id).toBe(affiche(choix.find((c) => c.juste)!));
  }
  // Le chapeau, lu avant tout pari, ne donne aucune bonne réponse : aucun morceau de trois mots ou plus d'un
  // choix juste (« au même nombre près », par exemple) ne s'y retrouve.
  const chapeau = ((await page.locator('.chapeau').textContent()) ?? '').replace(/\s+/g, ' ').toLowerCase();
  expect(chapeau.length).toBeGreaterThan(50);
  for (const juste of await page.locator('.pari[data-pari] [data-juste]').allTextContents()) {
    for (const morceau of juste.split(/[,:;]/).map((m) => m.replace(/\s+/g, ' ').trim().toLowerCase())) {
      if (morceau.split(' ').length >= 3) expect(chapeau, morceau).not.toContain(morceau);
    }
  }
  // Les questions, telles que la fiche les donne.
  await expect(page.locator('[data-pari="depart"] .q')).toContainText(typographier('Avant d’avoir rien appris, quelle perte a ton IA au premier pas ?'));
  await expect(page.locator('[data-pari="reprise"] .q')).toContainText('Après une pause, la perte du pas repris…');
  // Le pari du taux : celui du mini-modèle, dont la bonne réponse vient de son moteur.
  await expect(page.locator('[data-pari="taux"] [data-juste]')).toHaveText('Il apprend moins bien, ou plus du tout');
  // Les explications donnent les nombres des relevés.
  await expect(page.locator('[data-pari="depart"]')).toContainText(formaterPerte(MINI.resume.perte_premier_pas));
  await expect(page.locator('[data-pari="depart"]')).toContainText(formaterPerte(MINI.courbe.hasard));
  await expect(page.locator('[data-pari="reprise"]')).toContainText(nombre(ESSAI.perte_un_trait, 6));
  await expect(page.locator('[data-pari="courte"]')).toContainText(`${nombre(MINI.resume.debit_moyen)} jetons par seconde`);
});

test('le code affiché est celui des symboles de forge et de la région du projet, tels qu’ils sont aujourd’hui', async ({ page }) => {
  await page.goto(PAGE);
  const planning = 'projets/forge/forge/entrainement/planning.py';
  const boucle = 'projets/forge/forge/entrainement/boucle.py';
  const blocs: [string, 'symbole' | 'region', string][] = [
    [planning, 'symbole', 'taux'],
    [boucle, 'symbole', '_creer_optimiseur'],
    [boucle, 'symbole', '_pas_d_optimisation'],
    ['projets/1.5-pre-entrainement/tests/test_essai.py', 'region', 'test-reprise'],
  ];
  const codes = page.locator('.code-explique');
  await expect(codes).toHaveCount(blocs.length);
  for (const [i, [fichier, sorte, nom]] of blocs.entries()) {
    const source = readFileSync(`../${fichier}`, 'utf8');
    const attendu = sorte === 'region' ? extraireRegion(source, nom, fichier) : extraireSymbole(source, nom, fichier, { docstring: false });
    expect(await codes.nth(i).locator('pre').evaluate((pre) => pre.textContent), nom).toBe(attendu);
    await expect(codes.nth(i).locator('figcaption a')).toHaveAttribute('href', `https://github.com/chipat-neko/forge-ia/blob/main/${fichier}`);
  }
  // Moins de 30 lignes pour un pas entier : il se montre en entier (fiche, étape 5).
  expect(extraireSymbole(readFileSync(`../${boucle}`, 'utf8'), '_pas_d_optimisation', boucle).split('\n').length).toBeLessThan(30);
  expect(await codes.nth(2).locator('pre').textContent()).toContain('clip_grad_norm_');
});

test('l’ouverture : la perte du premier pas reste sous verrou jusqu’au pari « depart »', async ({ page }) => {
  await page.goto(PAGE);
  await attendreHydratation(page);
  const ouverture = page.locator('[data-test="ouverture"]');
  await expect(ouverture.locator('[data-test="perte-premier-pas"]')).toHaveText(formaterPerte(MINI.resume.perte_premier_pas));
  await expect(ouverture.locator('[data-test="perte-dernier-pas"]')).toHaveText(formaterPerte(MINI.resume.perte_dernier_pas));
  await expect(ouverture).toContainText(`Au pas ${nombre(MINI.resume.pas_faits)}`);
  const verrou = ouverture.locator('[data-verrou="depart"]');
  await expect(verrou).toHaveAttribute('inert', '');
  await verifierAxe(page);
  await page.locator('[data-pari="depart"] [data-juste]').click();
  await expect(verrou).not.toHaveAttribute('inert', '');
  await expect(verrou).toHaveCSS('opacity', '1');
});

test('le défi : la réponse affichée est le plus grand taux à 0,05 près, et le suivant échoue', async ({ page }) => {
  await page.goto(PAGE);
  const reponse = page.locator('details.reponse-defi');
  await reponse.locator('summary').click();
  const texte = (await reponse.textContent()) ?? '';
  // « 0,03 : au pas 3 000, son erreur de validation vaut 2,186, contre 2,158 au taux habituel, … À 0,1, elle finit à 2,281, … »
  const m = new RegExp(
    `^\\s*La réponse du défi\\s*([\\d,]+)${FINE}: au pas ${nombre(COMPLET.pasTotal)}, son erreur de validation vaut ([\\d,]+), contre ([\\d,]+) au taux habituel, .*À ([\\d,]+), elle finit à ([\\d,]+), `,
    's',
  ).exec(texte);
  expect(m, texte).not.toBeNull();
  const [, tauxReponse, finReponse, finDefaut, tauxSuivant, finSuivant] = m!.map((x, i) => (i === 0 ? 0 : relire(x)));
  expect(TAUX_PROPOSES).toContain(tauxReponse);
  expect(TAUX_PROPOSES).toContain(tauxSuivant);
  expect(tauxReponse).toBeGreaterThan(COMPLET.tauxMax);
  // Le suivant est le taux proposé juste au-dessus de la réponse.
  expect(TAUX_PROPOSES[TAUX_PROPOSES.indexOf(tauxReponse) + 1]).toBe(tauxSuivant);
  expect(finReponse - finDefaut).toBeLessThanOrEqual(ECART_DU_DEFI + 0.0005);
  expect(finSuivant - finDefaut).toBeGreaterThan(ECART_DU_DEFI - 0.0005);
  // Le rapport de la réponse au taux habituel est dit en mots : trois fois.
  expect(texte).toContain('fois le taux habituel apprend presque aussi bien');
  // L'énoncé : le taux habituel, l'écart permis.
  await expect(page.locator('#etape-4')).toContainText(`ne dépasse pas de plus de ${nombre(ECART_DU_DEFI, 2)} celle du taux habituel`);
});

test('l’encadré du labo et sa note : les chiffres de sources-1-5, leurs sources, et le lien vers le calculateur', async ({ page }) => {
  await page.goto(PAGE);
  const labo = page.locator('#etape-9 .labo');
  const l = LLAMA_31_405B;
  for (const n of [nombre(l.cartesMax.valeur), nombre(l.joursObserves.valeur), nombre(l.interruptions.valeur), nombre(l.interruptionsPrevues.valeur), nombre(l.interruptionsImprevues.valeur)]) {
    await expect(labo).toContainText(n);
  }
  await expect(labo).toContainText(`${nombre(l.heuresH100.valeur / 1e6, 2)} millions d’heures`);
  await expect(labo).toContainText(`3,8${FINE}×${FINE}10²⁵ opérations`);
  for (const s of SOURCES_LABO_1_5) await expect(labo.locator(`a[href="${s.url}"]`)).toHaveCount(1);
  await expect(labo.locator('a[href="/forge-ia/annexes/calculateur/"]')).toHaveText('calculateur de coût');
  // La note de l'étape, hors de l'encadré : ses seuls nombres, en dehors des noms des modèles, viennent de sources-1-5.
  const note = (await page.locator('#etape-9 .note').textContent()) ?? '';
  expect(note).toContain(`Les ${nombre(l.joursObserves.valeur)} jours`);
  const horsNoms = note.replace(/Llama 3(\.1)?( 405B)?/g, '');
  expect(horsNoms.match(/\d[\d\u202F,]*/g)).toStrictEqual([nombre(l.joursObserves.valeur)]);
  // Et le texte de l'étape, hors de l'encadré, n'en tape aucun.
  const avant = (await page.locator('#etape-9 .texte > p').first().textContent()) ?? '';
  expect(avant).not.toMatch(/\d/);
});

test('sans JavaScript, tout se lit : les explications, la perte du premier pas, les courbes', async ({ browser, baseURL }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false, baseURL });
  const page = await ctx.newPage();
  await page.goto(PAGE);
  for (const id of ['depart', 'taux', 'reprise', 'courte']) {
    await expect(page.locator(`[data-pari="${id}"] .verdict`)).toBeVisible();
  }
  await expect(page.locator('[data-verrou="depart"]')).not.toHaveAttribute('inert', '');
  await expect(page.locator('[data-test="perte-premier-pas"]')).toBeVisible();
  await expect(page.locator('[data-courbe="ton-ia-mini"] [data-test="courbe-svg"]')).toBeVisible();
  await expect(page.locator('[data-sessions="ton-ia-mini"]')).toBeVisible();
  await verifierSansDebordement(page);
  await ctx.close();
});
