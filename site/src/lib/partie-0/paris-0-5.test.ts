// Les paris du chapitre 0.5 et ce que le chapitre écrit de l'entraînement :
// leurs bonnes réponses viennent du jumeau du neurone (neurone.ts) et des
// attendus du Python (projets/0.5-reseau/tests/attendus.json), jamais écrites à
// la main. Les fonctions qui lisent les attendus les reçoivent en argument :
// elles sont essayées ici sur le vrai fichier, puis sur de faux attendus qui
// font tomber chaque garde.

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import type { Choix } from '../choix';
import { bienClasses, GRILLE, meilleurReglage, POINTS, PORTES } from './neurone';
import {
  bornesPredictions,
  choixCoince,
  choixExact,
  choixGradientSortie,
  choixXor,
  ecartsDeLaSortie,
  ecrireValeur,
  etiquetteCourbe,
  lignesPredictions,
  nbCoinces,
  P_DU_PARI,
  questionCoince,
  questionExact,
  questionGradient,
  type AttenduGraine,
  type AttendusEntrainement,
  Y_DU_PARI,
} from './paris-0-5';

const FINE = '\u202F';
const INSECABLE = '\u00A0';
const MOINS = '−';

// Vitest tourne dans site/ : le dépôt est un dossier plus haut.
const ATTENDUS = JSON.parse(readFileSync('../projets/0.5-reseau/tests/attendus.json', 'utf8')) as {
  entrainement: AttendusEntrainement;
  graines: AttenduGraine[];
};
const E = ATTENDUS.entrainement;
const SORTIE = readFileSync('../projets/0.5-reseau/sorties/processeur.txt', 'utf8');

/** Le texte du choix juste (et vérifie qu'il est seul). */
function juste(choix: Choix[]): string {
  const justes = choix.filter((c) => c.juste);
  expect(justes).toHaveLength(1);
  return justes[0].texte;
}

/** De faux attendus d'entraînement, à partir des vrais. */
function entrainement(autres: Partial<AttendusEntrainement>): AttendusEntrainement {
  return { ...E, ...autres };
}

describe('pari « xor » : un seul neurone et le OU exclusif', () => {
  it('le juste est le meilleur compte de la grille', () => {
    // Recalculé ici, sans meilleurReglage : le plus grand compte sur les 729 réglages.
    let meilleur = 0;
    for (const w1 of GRILLE) for (const w2 of GRILLE) for (const b of GRILLE) meilleur = Math.max(meilleur, bienClasses([w1, w2], b, 'ou_exclusif'));
    expect(meilleurReglage('ou_exclusif')[0]).toBe(meilleur);
    const n = POINTS.length;
    expect(choixXor().map((c) => c.texte)).toEqual([
      'Oui, avec les bons poids',
      `Non${FINE}: au mieux ${n - 1} points sur ${n}`,
      `Non${FINE}: au mieux ${n - 2} points sur ${n}`,
    ]);
    expect(juste(choixXor())).toBe(meilleur === n ? 'Oui, avec les bons poids' : `Non${FINE}: au mieux ${meilleur} points sur ${n}`);
  });
});

describe('pari « gradient » : p − y à la sortie', () => {
  it('la question et les choix du brief, le juste calculé', () => {
    expect(questionGradient()).toBe(`La sortie vaut 0,9, la bonne réponse 0${FINE}: que vaut p ${MOINS} y${FINE}?`);
    expect(choixGradientSortie().map((c) => c.texte)).toEqual([`${MOINS}0,9`, '0,9', '0,1']);
    expect(P_DU_PARI - Y_DU_PARI).toBe(0.9);
    expect(juste(choixGradientSortie())).toBe('0,9');
  });
});

describe('pari « exact » : après l’entraînement, le réseau répond-il exactement 0 et 1 ?', () => {
  it('sur les attendus : non, et les bornes sont celles des prédictions, à 3 décimales', () => {
    expect(E.predictions.some((p) => p === 0 || p === 1)).toBe(false);
    const { min, max } = bornesPredictions(E);
    expect(min).toBe(Math.min(...E.predictions));
    expect(max).toBe(Math.max(...E.predictions));
    expect(questionExact(E)).toBe(`Après 3${FINE}000 pas, le réseau répond-il exactement 0 et 1${FINE}?`);
    const textes = choixExact(E).map((c) => c.texte);
    expect(textes).toEqual([
      'Oui, exactement',
      `Non${FINE}: il s’en approche, de ${ecrireValeur(min)} à ${ecrireValeur(max)}`,
    ]);
    expect(juste(choixExact(E))).toBe(textes[1]);
    expect(ecrireValeur(min)).toBe('0,003');
    expect(ecrireValeur(max)).toBe('0,997');
  });

  it('des réponses toutes exactes rendent « Oui » juste ; un mélange fait tomber la garde', () => {
    expect(juste(choixExact(entrainement({ predictions: [0, 1, 1, 0] })))).toBe('Oui, exactement');
    expect(() => choixExact(entrainement({ predictions: [0, 0.99, 0.98, 0.01] }))).toThrow(/Exemple devenu faux/);
  });

  it('des bornes qui s’écriraient 0,000 ou 1,000 font tomber la garde', () => {
    expect(() => choixExact(entrainement({ predictions: [0.0001, 0.99, 0.98, 0.01] }))).toThrow(/Exemple devenu faux/);
    expect(() => choixExact(entrainement({ predictions: [0.01, 0.9999, 0.98, 0.01] }))).toThrow(/Exemple devenu faux/);
  });
});

describe('pari « coince » : combien de départs restent coincés', () => {
  it('le juste est compté dans les graines des attendus', () => {
    const k = ATTENDUS.graines.filter((g) => !g.reussit).length;
    expect(nbCoinces(ATTENDUS.graines)).toBe(k);
    expect(questionCoince(ATTENDUS.graines)).toBe(
      `Sur ${ATTENDUS.graines.length} départs au hasard, combien de fois le réseau reste-t-il coincé${FINE}?`,
    );
    expect(choixCoince(ATTENDUS.graines).map((c) => c.texte)).toEqual(['Jamais', `${k} fois`, 'À chaque départ']);
    expect(juste(choixCoince(ATTENDUS.graines))).toBe(`${k} fois`);
  });

  it('garde : au moins un départ coincé, et pas tous', () => {
    const toutes = ATTENDUS.graines.map((g) => ({ ...g, reussit: true }));
    const aucune = ATTENDUS.graines.map((g) => ({ ...g, reussit: false }));
    expect(() => choixCoince(toutes)).toThrow(/Exemple devenu faux/);
    expect(() => choixCoince(aucune)).toThrow(/Exemple devenu faux/);
    expect(juste(choixCoince([{ graine: 1, reussit: true }, { graine: 2, reussit: false }]))).toBe('1 fois');
  });
});

describe('la courbe et le tableau des prédictions', () => {
  it('l’étiquette de la courbe : les vraies pertes du départ et de la fin, à 3 décimales', () => {
    expect(E.pertes).toHaveLength(E.nb_pas + 1);
    expect(etiquetteCourbe(E.pertes)).toBe(
      `Erreur du réseau${FINE}: ${ecrireValeur(E.pertes[0])} au pas 0, ${ecrireValeur(E.pertes[E.nb_pas])} au pas 3${FINE}000.`,
    );
    expect(etiquetteCourbe(E.pertes)).toBe(`Erreur du réseau${FINE}: 0,844 au pas 0, 0,004 au pas 3${FINE}000.`);
    expect(() => etiquetteCourbe([0.5])).toThrow();
    expect(() => etiquetteCourbe([0.5, Number.NaN])).toThrow();
  });

  it('les lignes du tableau : le point, la bonne réponse, la réponse et son arrondi', () => {
    const lignes = lignesPredictions(E);
    expect(lignes).toHaveLength(POINTS.length);
    // Le point du tableau garde son espace après la virgule, insécable : la case ne se coupe pas.
    expect(lignes.map((l) => l[0])).toEqual(['(0, 0)', '(0, 1)', '(1, 0)', '(1, 1)'].map((p) => p.replace(' ', INSECABLE)));
    expect(lignes.map((l) => l[1])).toEqual(PORTES.ou_exclusif.map(String));
    expect(lignes.map((l) => l[2])).toEqual(E.predictions.map(ecrireValeur));
    expect(lignes.map((l) => l[3])).toEqual(E.predictions.map((p) => String(Math.round(p))));
    expect(() => lignesPredictions(entrainement({ predictions: [0.1, 0.9, 0.9] }))).toThrow();
  });

  it('ecrireValeur : 3 décimales, virgule, signe moins U+2212', () => {
    expect(ecrireValeur(0.8435673960632979)).toBe('0,844');
    expect(ecrireValeur(-0.25)).toBe(`${MOINS}0,250`);
    expect(() => ecrireValeur(Number.NaN)).toThrow();
  });
});

describe('les écarts de la sortie enregistrée (sorties/processeur.txt)', () => {
  it('lit les deux écarts tels que le script les écrit, et leur valeur', () => {
    const e = ecartsDeLaSortie(SORTIE);
    expect(SORTIE).toContain(`plus grand écart ${e.gradients}.`);
    expect(SORTIE).toContain(`avec la main${FINE}: ${e.poids}.`);
    expect(e.valeurGradients).toBeGreaterThanOrEqual(0);
    expect(e.valeurGradients).toBeLessThan(1e-12);
    expect(e.valeurPoids).toBeGreaterThanOrEqual(0);
  });

  it('lit « 2,8 × 10⁻¹⁷ » et « 0 », et dit quoi faire si une ligne manque', () => {
    const texte = (g: string, p: string) =>
      `Gradients de départ, à la main et par autograd${FINE}: plus grand écart ${g}.\n` +
      `  Perte finale 0,00370, et plus grand écart des poids finaux avec la main${FINE}: ${p}.\n`;
    expect(ecartsDeLaSortie(texte('2,8 × 10⁻¹⁷', '0'))).toEqual({
      gradients: '2,8 × 10⁻¹⁷',
      valeurGradients: 2.8e-17,
      poids: '0',
      valeurPoids: 0,
    });
    expect(ecartsDeLaSortie(texte('1,5 × 10⁻¹³', '5,3 × 10⁻¹⁵')).valeurPoids).toBe(5.3e-15);
    expect(() => ecartsDeLaSortie('rien')).toThrow(/premier_reseau entrainer/);
  });
});
