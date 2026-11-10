// Parcours du chapitre 1.6, « Évaluer son modèle » : un brouillon (src/brouillons/chapitres/1-6.mdx)
// tant qu'il n'a pas paru, construit à son adresse définitive avec FORGE_ESSAIS=1.
//
// Les attendus viennent des relevés du projet 1.6, lus sur le disque (evaluation.ts), des paris et de
// l'atelier (paris-1-6.ts), des commandes (commandes.ts), des sources (sources-1-6.ts) et du code
// montré, relu dans les fichiers du projet tels qu'ils sont aujourd'hui. Un parcours, chargé par Node
// sans Vite, n'importe ni ?raw, ni .json, ni astro:* (P8).
//
// Tant que ton IA, la vraie, n'est pas évaluée (evaluation-1.5.json, tâche 15 du plan 5), l'étape 8
// est « à mesurer ».
import { readFileSync } from 'node:fs';
import { test, expect, type Page } from '@playwright/test';
import type { Choix } from '../src/lib/choix';
import { VOCABULAIRE_FORGE } from '../src/lib/calculateur/ton-ia';
import { formaterPerte, nombre, pourcent } from '../src/lib/nombres';
import { trouverChapitre } from '../src/lib/parcours';
import { CLONER_DEPOT, METTRE_A_JOUR_DEPOT } from '../src/lib/partie-0/commandes';
import * as commandes from '../src/lib/partie-1/commandes';
import { lireEvaluation, lireQcm, margeHasard } from '../src/lib/partie-1/evaluation';
import {
  analyseDuDefi,
  choixAuDessusDuHasard,
  choixBits,
  choixLangueFrenchBench,
  choixPerplexiteHasard,
  compteDuQcm,
  etatDuDefi,
  faitsDesBits,
  faitsDuPariHasard,
  largeursDesBarres,
  phrasesDuDefi,
  texteDuCompte,
  verdictEnPhrase,
} from '../src/lib/partie-1/paris-1-6';
import { FRENCHBENCH, LLAMA_3_BANCS, LLAMA_31_405B_BASE, SOURCES_LABO_1_6 } from '../src/lib/partie-1/sources-1-6';
import { extraireRegion } from '../src/lib/regions';
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

const PAGE = '/forge-ia/partie-1/1-6/';
const FINE = '\u202F';

// Playwright tourne dans site/ : evaluation.ts lit le dépôt, un dossier plus haut.
const MINI = lireEvaluation('ton-ia-mini')!;
const QCM = lireQcm('ton-ia-mini')!;
const TON_IA_15 = lireEvaluation('ton-ia-1.5');
const PAS_A_PAS = 'projets/1.6-evaluation/evaluation_pas_a_pas/pas_a_pas.py';

// Ce qui n'est pas du texte du chapitre mais des données brutes : les questions de MMMLU telles que ton
// IA les a lues, leurs réponses, et les textes qu'elle a écrits.
const BRUT = '[data-atelier-qcm] [data-pagefind-ignore], [data-echantillons] [data-pagefind-ignore]';

/** Les commandes que les blocs « À taper » du chapitre montrent, dans l'ordre de la page. */
const COMMANDES_DES_BLOCS = [
  [METTRE_A_JOUR_DEPOT, commandes.ALLER_AU_PROJET_1_6],
  [CLONER_DEPOT, commandes.ALLER_AU_PROJET_1_6],
  [commandes.EVALUATION_TESTS],
  [commandes.EVALUATION_RESUMER, commandes.EVALUATION_QCM],
];

/** Le texte d'un choix tel qu'un bouton l'affiche : le code tel quel, le reste typographié. */
function affiche(choix: Choix): string {
  return choix.texte
    .split('`')
    .map((morceau, i) => (i % 2 === 1 ? morceau : typographier(morceau)))
    .join('');
}

/** Attend la fin des animations en cours (fondu des verrous, verdict des paris) : axe mesure alors les vraies couleurs. */
async function attendreAnimations(page: Page): Promise<void> {
  await page.evaluate(() => Promise.all(document.getAnimations().map((a) => a.finished)).then(() => undefined));
}

/** Ouvre le chapitre, hydraté, et ouvre l'atelier par le pari de l'étape 3. */
async function ouvrirLAtelier(page: Page): Promise<void> {
  await page.goto(PAGE);
  await attendreHydratation(page);
  await page.locator('[data-pari="bits"] [data-juste]').click();
  await expect(page.locator('[data-verrou="atelier"]')).not.toHaveAttribute('inert', '');
  await expect(page.locator('[data-atelier-qcm]')).toHaveAttribute('data-pret', 'oui');
}

test('chapitre 1.6 complet', async ({ page }, info) => {
  // Les six questions de l'atelier, puis axe et les contrôles de toute la page : plus que les 30 s par défaut sur un PC chargé.
  test.setTimeout(90_000);
  const reponse = await page.goto(PAGE);
  expect(reponse?.status()).toBe(200);
  await attendreHydratation(page);
  const { total } = trouverChapitre('1.6');
  await expect(page.locator('header')).toContainText(`Partie 1, chapitre 1.6 sur ${total}`);
  if (info.project.name === 'mobile') expect(page.viewportSize()?.width).toBe(390);
  await expect(page.locator('.pari[data-pari]')).toHaveCount(4);
  await page.locator('[data-pari="hasard"] [data-juste]').click();
  await page.locator('[data-pari="bits"] [data-juste]').click();
  await expect(page.locator('[data-verrou="atelier"]')).not.toHaveAttribute('inert', '');
  // L'acquis de l'atelier se gagne au compte final, une fois les six questions pariées.
  const atelier = page.locator('[data-atelier-qcm]');
  await expect(page.locator('#recap [data-acquis="qcm"]')).toHaveAttribute('data-gagne', 'non');
  for (let i = 0; i < QCM.n; i++) {
    await expect(atelier).toHaveAttribute('data-question', String(i));
    await atelier.locator('[data-test="qcm-choix"]').first().click();
    if (i < QCM.n - 1) await atelier.locator('[data-test="qcm-suivante"]').click();
  }
  await expect(atelier.locator('[data-test="qcm-compte"]')).toHaveText(texteDuCompte(compteDuQcm(QCM)));
  await expect(page.locator('#recap [data-acquis="qcm"]')).toHaveAttribute('data-gagne', 'oui');
  await page.locator('[data-pari="marge"] [data-juste]').click();
  await page.locator('[data-pari="limites"] [data-juste]').click();
  await expect(page.locator('#recap [data-total]')).toContainText('5 sur 5');
  // Le pied suit les fichiers : 1.5 et 1.7 sont « à venir » tant qu'ils n'ont pas paru.
  await verifierVoisin(page, 'precedent', '1-5.mdx', '/forge-ia/partie-1/1-5/');
  await verifierVoisin(page, 'suivant', '1-7.mdx', '/forge-ia/partie-1/1-7/');
  await verifierLiensVersParus(page.locator('main'), PAGE);
  await attendreAnimations(page);
  await verifierAxe(page);
  await verifierSansDebordement(page);
  await verifierTypographieHorsCode(page.locator('main'), BRUT);
  // Aucune expression du MDX restée en texte (une accolade tombée dans un passage de code, par exemple).
  expect(await texteHorsCode(page.locator('main'))).not.toMatch(/[{}]/);
  expect(await page.locator('main :not(pre) > code').allTextContents()).not.toContainEqual(expect.stringMatching(/[{}]/));
  expect(await page.locator('main').innerText()).not.toMatch(/NaN|Infinity|undefined|\de\+/);
  // Le verdict de forge n'est jamais affiché brut (« au-dessus » est aussi du français : seuls les deux autres se voient).
  expect(await texteHorsCode(page.locator('main'))).not.toMatch(/pas-different|en-dessous/);
  const { longueur, ligne } = await plusLongueLigne(page);
  expect(longueur, `ligne la plus longue : « ${ligne} »`).toBeLessThanOrEqual(80);
});

test('l’atelier : le pari avant les barres, les barres floues tant qu’on n’a pas parié, puis le compte', async ({ page }) => {
  // Six questions, chacune vérifiée avant et après le pari.
  test.setTimeout(90_000);
  await ouvrirLAtelier(page);
  const atelier = page.locator('[data-atelier-qcm]');
  const vues: number[] = [];
  for (const [i, q] of QCM.questions.entries()) {
    await expect(atelier.locator('[data-test="qcm-position"]')).toHaveText(`Question ${i + 1} sur ${QCM.n}`);
    await expect(atelier.locator('[data-test="qcm-contexte"]')).toHaveText(q.contexte);
    const lignes = atelier.locator('tr[data-reponse]');
    await expect(lignes).toHaveCount(q.choix.length);
    // Avant le pari : des barres floues, toutes pareilles, sans score, sans préférence ni bonne réponse.
    const barres = atelier.locator('[data-test="qcm-barres"]');
    for (let j = 0; j < q.choix.length; j++) {
      await expect(barres.nth(j)).toHaveClass(/floues/);
      await expect(barres.nth(j)).toHaveAttribute('inert', '');
      await expect(barres.nth(j).locator('[data-test="qcm-score"]')).toHaveText('?');
    }
    await expect(barres.nth(0)).toHaveCSS('filter', /blur/);
    await expect(atelier.locator('[data-test="qcm-prefere"], [data-test="qcm-bonne"], [data-test="qcm-verdict"]')).toHaveCount(0);
    await expect(atelier.locator('[data-test="qcm-suivante"]')).toHaveCount(0);
    // Les réponses : celles du relevé, sans leur espace de tête.
    expect(await atelier.locator('[data-test="qcm-choix"] .texte').allTextContents()).toStrictEqual(q.choix.map((c) => c.trim()));
    // Le pari : une réponse au hasard du parcours, la dernière.
    const pari = q.choix.length - 1;
    await atelier.locator('[data-test="qcm-choix"]').nth(pari).click();
    vues.push(i);
    // Après : les scores normalisés, les longueurs de largeursDesBarres, la préférence et la bonne réponse.
    const largeurs = largeursDesBarres(q.scores_normalises);
    for (let j = 0; j < q.choix.length; j++) {
      await expect(barres.nth(j)).not.toHaveClass(/floues/);
      await expect(barres.nth(j).locator('[data-test="qcm-score"]')).toHaveText(nombre(q.scores_normalises[j], 2));
      const style = (await barres.nth(j).locator('.barre').getAttribute('style')) ?? '';
      const largeur = Number(/width:\s*([\d.]+)%/.exec(style)?.[1]);
      expect(largeur, `question ${i + 1}, réponse ${j} : ${style}`).toBe(Number((largeurs[j] * 100).toFixed(1)));
    }
    await expect(lignes.nth(q.prefere).locator('[data-test="qcm-prefere"]')).toHaveText('préférée par ton IA');
    const bonne = lignes.nth(q.bonne).locator('[data-test="qcm-bonne"]');
    await expect(bonne).toHaveText('bonne réponse');
    // Menthe si ton IA a trouvé la bonne réponse, corail sinon.
    const couleur = q.juste ? 'rgb(28, 110, 88)' : 'rgb(184, 52, 45)';
    await expect(bonne).toHaveCSS('color', couleur);
    await expect(atelier.locator('[data-test="qcm-verdict"]')).toHaveCSS('color', couleur);
    await expect(atelier.locator('[data-test="qcm-pari"]')).toContainText(pari === q.prefere ? 'Ton pari est juste' : 'Ton pari est raté');
    // Le défi compte les questions trouvées où ton IA a juste.
    await expect(atelier.locator('[data-test="qcm-defi"]')).toHaveText(etatDuDefi(vues, QCM).texte);
    if (i < QCM.n - 1) {
      await expect(atelier.locator('[data-test="qcm-compte"]')).toHaveCount(0);
      await atelier.locator('[data-test="qcm-suivante"]').click();
      // Le focus passe sur la question suivante.
      await expect(atelier.locator('[data-test="qcm-contexte"]')).toBeFocused();
    }
  }
  // À la fin, le compte calculé : « Ton IA : 2 sur 6, le hasard : 1,5 en moyenne. »
  const compte = compteDuQcm(QCM);
  await expect(atelier.locator('[data-test="qcm-compte"]')).toHaveText(texteDuCompte(compte));
  expect(texteDuCompte(compte)).toBe(`Ton IA${FINE}: ${compte.justes} sur ${QCM.n}, le hasard${FINE}: ${nombre(compte.hasard, 1)} en moyenne.`);
  await expect(atelier.locator('[data-test="qcm-suivante"]')).toHaveCount(0);
  await verifierAxe(page);
});

test('la réponse du défi : ce que disent les scores, et le compte face à la marge du hasard', async ({ page }) => {
  await page.goto(PAGE);
  const reponse = page.locator('details.reponse-defi');
  await reponse.locator('summary').click();
  // Les blancs du balisage deviennent une espace ; les espaces fines insécables restent.
  const texte = ((await reponse.textContent()) ?? '').replace(/[ \t\n]+/g, ' ');
  for (const phrase of phrasesDuDefi(analyseDuDefi(QCM))) expect(texte).toContain(typographier(phrase));
  expect(analyseDuDefi(QCM).verdict).toBe('pas-different');
  await expect(reponse).toContainText(`${nombre(compteDuQcm(QCM).justes)} justes sur ${nombre(QCM.n)}`);
  // L'énoncé du défi est dans l'atelier.
  await expect(page.locator('[data-atelier-qcm] .defi')).toContainText('Trouve une question où ton IA préfère la bonne réponse');
});

test('ton IA, la vraie : « à mesurer » tant qu’elle n’est pas évaluée', async ({ page }) => {
  await page.goto(PAGE);
  const etape8 = page.locator('#etape-8');
  if (TON_IA_15 === null) {
    expect(await etape8.locator('[data-a-mesurer]').count()).toBeGreaterThanOrEqual(1);
    await expect(etape8.locator('[data-evaluation-absente="ton-ia-1.5"]')).toBeVisible();
    await expect(etape8.locator('[data-echantillons-absents="ton-ia-1.5"]')).toBeVisible();
    await expect(etape8.locator('[data-evaluation="ton-ia-1.5"]')).toHaveCount(0);
  } else {
    await expect(etape8.locator('[data-a-mesurer]')).toHaveCount(0);
    await expect(etape8.locator('[data-evaluation="ton-ia-1.5"]')).toBeVisible();
  }
  // Ailleurs, la version d'une heure est mesurée : rien « à mesurer » hors de l'étape 8.
  await expect(page.locator('main [data-a-mesurer]:not(#etape-8 *)')).toHaveCount(0);
});

test('l’ouverture et le tableau de la version d’une heure disent ce que dit son rapport', async ({ page }) => {
  await page.goto(PAGE);
  const ouverture = page.locator('[data-test="ouverture"]');
  await expect(ouverture.locator('[data-test="perplexite-mini"]')).toHaveText(nombre(MINI.perplexite, 1));
  await expect(ouverture.locator('[data-test="sens-perplexite"]')).toContainText(`entre ${faitsDuPariHasard(MINI).hesitation} jetons`);
  // L'ouverture ne donne pas la réponse du pari « hasard » : ni le vocabulaire, ni sa perte.
  await expect(ouverture).not.toContainText(nombre(VOCABULAIRE_FORGE));
  const tableau = page.locator('[data-evaluation="ton-ia-mini"]');
  const mesures = tableau.locator('[data-test="evaluation-mesures"] tbody tr td');
  expect(await mesures.allTextContents()).toStrictEqual([
    nombre(MINI.perte_val, 3),
    nombre(MINI.perplexite, 1),
    nombre(MINI.bits_par_octet, 3),
  ]);
  for (const test of ['hellaswag', 'arc'] as const) {
    const m = MINI.qcm[test];
    const ligne = tableau.locator(`tr[data-test-qcm="${test}"]`);
    await expect(ligne).toHaveAttribute('data-verdict', m.verdict);
    // L'exactitude normalisée et la précision de la mesure ; le hasard et sa marge.
    await expect(ligne.locator('td').nth(0)).toContainText(pourcent(m.exactitude_normalisee, 1));
    await expect(ligne.locator('td').nth(0).locator('small')).toHaveText(`±${FINE}${nombre(100 * m.marge_95_normalisee, 1)}`);
    await expect(ligne.locator('td').nth(1)).toContainText(pourcent(m.hasard, 1));
    await expect(ligne.locator('td').nth(1).locator('small')).toHaveText(`±${FINE}${nombre(100 * m.marge_hasard, 1)}`);
    await expect(ligne.locator('td').nth(2)).toHaveText(verdictEnPhrase(m.verdict));
    await expect(ligne.locator('th')).toContainText(`${nombre(m.n)} questions`);
  }
});

test('les échantillons : les dix textes du rapport, tels quels', async ({ page }) => {
  await page.goto(PAGE);
  const textes = page.locator('[data-echantillons="ton-ia-mini"] [data-echantillon]');
  await expect(textes).toHaveCount(MINI.echantillons.length);
  for (const [i, e] of MINI.echantillons.entries()) {
    expect(await textes.nth(i).textContent()).toBe(e.invite + e.suite);
    await expect(textes.nth(i).locator('.debut')).toHaveText(e.invite);
  }
  await expect(page.locator('[data-echantillons="ton-ia-mini"] pre')).toHaveCount(MINI.echantillons.filter((e) => e.invite.startsWith('def ')).length);
});

test('les choix des paris viennent des relevés, des sources et de la règle de forge', async ({ page }) => {
  await page.goto(PAGE);
  const paris: [string, Choix[]][] = [
    ['hasard', choixPerplexiteHasard()],
    ['bits', choixBits(MINI)],
    ['marge', choixAuDessusDuHasard(MINI)],
    ['limites', choixLangueFrenchBench()],
  ];
  for (const [id, choix] of paris) {
    expect(await page.locator(`[data-pari="${id}"] button[data-choix]`).allTextContents(), id).toEqual(choix.map(affiche));
    expect(await page.locator(`[data-pari="${id}"] [data-juste]`).textContent(), id).toBe(affiche(choix.find((c) => c.juste)!));
  }
  // Le chapeau, lu avant tout pari, ne donne aucune bonne réponse.
  const chapeau = ((await page.locator('.chapeau').textContent()) ?? '').replace(/\s+/g, ' ').toLowerCase();
  expect(chapeau.length).toBeGreaterThan(50);
  for (const juste of await page.locator('.pari[data-pari] [data-juste]').allTextContents()) {
    for (const morceau of juste.split(/[,:;]/).map((m) => m.replace(/\s+/g, ' ').trim().toLowerCase())) {
      if (morceau.split(' ').length >= 3) expect(chapeau, morceau).not.toContain(morceau);
    }
  }
  // La question du pari « hasard », telle que la fiche la donne.
  await expect(page.locator('[data-pari="hasard"] .q')).toContainText(`Un modèle qui tire chaque jeton au hasard parmi les ${nombre(VOCABULAIRE_FORGE)} a une perplexité de…`);
  // Les explications donnent les nombres des relevés.
  const f = faitsDuPariHasard(MINI);
  await expect(page.locator('[data-pari="hasard"]')).toContainText(formaterPerte(f.perteHasard));
  await expect(page.locator('[data-pari="hasard"]')).toContainText(nombre(f.perplexite, 1));
  const b = faitsDesBits(MINI);
  await expect(page.locator('[data-pari="bits"]')).toContainText(nombre(b.bits, 3));
  await expect(page.locator('[data-pari="bits"]')).toContainText(nombre(b.octetsParJeton, 1));
  const h = MINI.qcm.hellaswag;
  await expect(page.locator('[data-pari="marge"]')).toContainText(nombre(100 * h.marge_hasard, 1));
  await expect(page.locator('[data-pari="limites"]')).toContainText(FRENCHBENCH.traducteur.valeur);
  // La marge de l'atelier : celle du hasard sur ses six questions.
  await expect(page.locator('#etape-5')).toContainText(`${nombre(100 * margeHasard(QCM.n), 1)} points`);
});

test('le code affiché est celui des régions du projet, tel qu’il est aujourd’hui', async ({ page }) => {
  await page.goto(PAGE);
  const source = readFileSync(`../${PAS_A_PAS}`, 'utf8');
  const regions = ['perte', 'perplexite', 'bits', 'qcm', 'marge'];
  const codes = page.locator('.code-explique');
  await expect(codes).toHaveCount(regions.length);
  for (const [i, nom] of regions.entries()) {
    expect(await codes.nth(i).locator('pre').evaluate((pre) => pre.textContent), nom).toBe(extraireRegion(source, nom, PAS_A_PAS));
    await expect(codes.nth(i).locator('figcaption a')).toHaveAttribute('href', `https://github.com/chipat-neko/forge-ia/blob/main/${PAS_A_PAS}`);
  }
});

test('les commandes affichées sont celles de commandes.ts, et les chemins de l’auteur sont signalés', async ({ page }) => {
  await page.goto(PAGE);
  const blocs = await page
    .locator('.bloc-commande pre code')
    .evaluateAll((codes) => codes.map((c) => (c.textContent ?? '').split('\n')));
  expect(blocs).toEqual(COMMANDES_DES_BLOCS);
  // Le bloc qui contient des chemins D:\ est suivi d'une phrase qui dit de les remplacer.
  expect(commandes.EVALUATION_RESUMER).toContain('D:\\');
  const figure = page.locator('.bloc-commande').filter({ hasText: commandes.EVALUATION_RESUMER });
  const suite = figure.locator('xpath=following-sibling::p[1]');
  await expect(suite).toContainText('PC de l’auteur');
  await expect(suite).toContainText('remplace');
  await expect(page.getByRole('link', { name: 'Le projet complet' })).toHaveAttribute(
    'href',
    'https://github.com/chipat-neko/forge-ia/tree/main/projets/1.6-evaluation',
  );
  // « À suivre » : 1.7 n'a pas paru, son titre n'est pas un lien.
  await expect(page.locator('#etape-10')).toContainText('Apprendre à converser');
  await expect(page.locator('#etape-10 a[href*="/partie-1/1-7/"]')).toHaveCount(0);
});

test('l’encadré du labo : les chiffres de sources-1-6, et leurs sources', async ({ page }) => {
  await page.goto(PAGE);
  const labo = page.locator('#etape-9 .labo');
  const l = LLAMA_31_405B_BASE;
  await expect(labo).toContainText(`${nombre(l.mmlu.valeur, 1)}${FINE}%`);
  await expect(labo).toContainText(`${nombre(l.arc.valeur, 1)}${FINE}%`);
  await expect(labo).toContainText(`${nombre(l.mmluExemples.valeur)} exemples`);
  await expect(labo).toContainText(`${nombre(l.arcExemples.valeur)}`);
  await expect(labo).toContainText(`${nombre(LLAMA_3_BANCS.categories.valeur.length)} familles`);
  for (const c of LLAMA_3_BANCS.categories.valeur) await expect(labo).toContainText(c.francais);
  for (const s of SOURCES_LABO_1_6) await expect(labo.locator(`a[href="${s.url}"]`)).toHaveCount(1);
  // Étape 7 : la contamination de HellaSwag chez Llama 3, en 8-grammes.
  const etape7 = page.locator('#etape-7');
  await expect(etape7).toContainText(`${nombre(LLAMA_3_BANCS.ngramme.valeur)} jetons`);
  await expect(etape7).toContainText(`${nombre(LLAMA_3_BANCS.hellaswagContamine.valeur)}${FINE}%`);
  await expect(etape7).toContainText(nombre(LLAMA_3_BANCS.gainHellaswag405B.valeur, 1));
});

test('sans JavaScript, tout se lit : les explications, la première question dévoilée, les tableaux', async ({ browser, baseURL }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false, baseURL });
  const page = await ctx.newPage();
  await page.goto(PAGE);
  for (const id of ['hasard', 'bits', 'marge', 'limites']) {
    await expect(page.locator(`[data-pari="${id}"] .verdict`)).toBeVisible();
  }
  const atelier = page.locator('[data-atelier-qcm]');
  const q = QCM.questions[0];
  await expect(atelier.locator('[data-test="qcm-contexte"]')).toHaveText(q.contexte);
  await expect(atelier.locator('[data-test="qcm-barres"]').first()).not.toHaveClass(/floues/);
  await expect(atelier.locator('[data-test="qcm-score"]').first()).toHaveText(nombre(q.scores_normalises[0], 2));
  await expect(atelier.locator('[data-test="qcm-verdict"]')).toBeVisible();
  await expect(page.locator('[data-evaluation="ton-ia-mini"]')).toBeVisible();
  await expect(page.locator('[data-echantillons="ton-ia-mini"]')).toBeVisible();
  await verifierSansDebordement(page);
  await ctx.close();
});
