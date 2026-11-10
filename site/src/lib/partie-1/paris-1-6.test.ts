// Les paris du chapitre 1.6, l'atelier des QCM et son défi : leurs bonnes réponses viennent des
// relevés du projet 1.6 (le rapport d'évaluation de la version d'une heure de ton IA, les QCM de
// MMMLU qu'elle a notés), lus sur le disque, de la règle de forge (verdictQcm) et des sources
// relevées (sources-1-6.ts).

import { describe, expect, it } from 'vitest';
import type { Choix } from '../choix';
import { VOCABULAIRE_FORGE } from '../calculateur/ton-ia';
import { nombre } from '../nombres';
import { lireEvaluation, lireQcm, type Evaluation, type QcmExemples } from './evaluation';
import { margeHasard, verdictQcm } from './marge';
import {
  analyseDuDefi,
  BITS_PAR_OCTET_D_UN_FICHIER,
  choixAuDessusDuHasard,
  choixBits,
  choixLangueFrenchBench,
  choixPerplexiteHasard,
  choixPrefere,
  compteDuQcm,
  etatDuDefi,
  faitsDesBits,
  faitsDesEchantillons,
  faitsDuPariHasard,
  largeursDesBarres,
  ORIGINES_FRENCHBENCH,
  perplexiteDuHasard,
  phrasesDuDefi,
  premierMax,
  questionsJustes,
  texteDuCompte,
  trancheDesBits,
  TRANCHES_BITS,
  verdictEnPhrase,
} from './paris-1-6';
import { FRENCHBENCH } from './sources-1-6';

const FINE = '\u202F';

// Vitest est lancé depuis site/ : le dépôt est un dossier plus haut.
const MINI = lireEvaluation('ton-ia-mini') as Evaluation;
const QCM = lireQcm('ton-ia-mini') as QcmExemples;

/** Le texte du seul choix juste ; échoue s'il n'y en a pas exactement un. */
function juste(choix: Choix[]): string {
  const justes = choix.filter((c) => c.juste === true);
  expect(justes, JSON.stringify(choix)).toHaveLength(1);
  return justes[0].texte;
}

const copie = <T>(x: T): T => structuredClone(x);

describe('les relevés que lit le chapitre', () => {
  it('existent : le rapport d’évaluation et les QCM de la version d’une heure', () => {
    expect(MINI).not.toBeNull();
    expect(MINI.nom).toBe('ton-ia-mini');
    expect(QCM).not.toBeNull();
    expect(QCM.n).toBe(6);
  });

  it('ton IA, la vraie, n’est pas encore relevée : le chapitre la dit « à mesurer »', () => {
    // La tâche 15 du plan 5 écrira ces fichiers ; d'ici là, rien ne doit les remplacer.
    expect(lireEvaluation('ton-ia-1.5')).toBeNull();
    expect(lireQcm('ton-ia-1.5')).toBeNull();
  });
});

describe('étape 2 : le pari « hasard »', () => {
  it('la perplexité du hasard est la taille du vocabulaire', () => {
    expect(perplexiteDuHasard(VOCABULAIRE_FORGE)).toBeCloseTo(VOCABULAIRE_FORGE, 6);
    expect(perplexiteDuHasard(2)).toBeCloseTo(2, 12);
    expect(perplexiteDuHasard(1)).toBe(1);
    expect(() => perplexiteDuHasard(0)).toThrow(/taille de vocabulaire/);
    expect(() => perplexiteDuHasard(2.5)).toThrow(/taille de vocabulaire/);
  });

  it('les choix : 2, 100 et 32 768, et le juste est le vocabulaire de forge', () => {
    const choix = choixPerplexiteHasard();
    expect(choix.map((c) => c.texte)).toStrictEqual(['2', '100', `32${FINE}768`]);
    expect(juste(choix)).toBe(nombre(VOCABULAIRE_FORGE));
  });

  it('les faits de l’explication : ton IA hésite comme entre 31 jetons, plus de mille fois moins que le hasard', () => {
    const f = faitsDuPariHasard(MINI);
    expect(f.vocabulaire).toBe(VOCABULAIRE_FORGE);
    expect(f.perteHasard).toBe(Math.log(VOCABULAIRE_FORGE));
    expect(f.perplexite).toBe(MINI.perplexite);
    expect(f.hesitation).toBe(31);
    expect(f.fois).toBeGreaterThan(1000);
    expect(Math.round(f.fois)).toBe(1063);
  });

  it('refuse une perplexité qui n’est plus entre 1 et celle du hasard', () => {
    const e = copie(MINI);
    e.perplexite = 40_000;
    expect(() => faitsDuPariHasard(e)).toThrow(/Exemple devenu faux/);
  });
});

describe('étape 3 : le pari « bits »', () => {
  it('les tranches : moins de 2, de 2 à 8, au moins 8', () => {
    expect(TRANCHES_BITS.map((t) => t.texte)).toStrictEqual(['Moins de 2', 'De 2 à 8', 'Au moins 8']);
    expect([1.99, 2, 7.99, 8, 12].map(trancheDesBits)).toStrictEqual([0, 1, 1, 2, 2]);
    expect(BITS_PAR_OCTET_D_UN_FICHIER).toBe(8);
  });

  it('le juste vient des bits par octet du rapport : moins de 2', () => {
    expect(juste(choixBits(MINI))).toBe('Moins de 2');
    const e = copie(MINI);
    e.bits_par_octet = 3;
    expect(juste(choixBits(e))).toBe('De 2 à 8');
  });

  it('les faits : bits par jeton, octets par jeton, et le modèle qui lirait octet par octet', () => {
    const f = faitsDesBits(MINI);
    expect(f.bits).toBe(MINI.bits_par_octet);
    expect(f.bitsParJeton).toBeCloseTo(MINI.perte_val / Math.LN2, 12);
    // Forge a divisé par les octets par jeton : on les retrouve, environ 4,4 octets par jeton.
    expect(f.bitsParJeton / f.octetsParJeton).toBeCloseTo(MINI.bits_par_octet, 12);
    expect(nombre(f.octetsParJeton, 1)).toBe('4,4');
    expect(f.perteParOctet).toBeCloseTo(MINI.bits_par_octet * Math.LN2, 12);
    expect(f.perplexiteParOctet).toBeCloseTo(2 ** MINI.bits_par_octet, 12);
    expect(nombre(f.perplexiteParOctet, 1)).toBe('2,2');
    expect(Math.round(f.foisPlusPetit)).toBe(7);
  });
});

describe('étape 4 : l’atelier des QCM', () => {
  it('premierMax : le plus grand, le premier à égalité', () => {
    expect(premierMax([-3, -1, -2])).toBe(1);
    expect(premierMax([-1, -1, -2])).toBe(0);
    expect(() => premierMax([])).toThrow(/au moins un score/);
  });

  it('choixPrefere : les réponses sans leur espace, et juste celle que ton IA préfère', () => {
    QCM.questions.forEach((q, i) => {
      const choix = choixPrefere(QCM, i);
      expect(choix.map((c) => c.texte)).toStrictEqual(q.choix.map((c) => c.trim()));
      expect(juste(choix)).toBe(q.choix[q.prefere].trim());
      // La préférence est le plus grand score normalisé (divisé par les octets), pas le plus grand score brut.
      expect(q.prefere).toBe(premierMax(q.scores_normalises));
    });
    expect(() => choixPrefere(QCM, 6)).toThrow(/La question 6 n’existe pas/);
  });

  it('choixPrefere refuse une préférence qui n’est plus le plus grand score normalisé', () => {
    const qcm = copie(QCM);
    qcm.questions[0].prefere = (qcm.questions[0].prefere + 1) % 4;
    expect(() => choixPrefere(qcm, 0)).toThrow(/Exemple devenu faux/);
  });

  it('les barres : 1 pour la préférée, exp(score − meilleur) pour les autres', () => {
    expect(largeursDesBarres([-1, -2, -1])).toStrictEqual([1, Math.exp(-1), 1]);
    for (const q of QCM.questions) {
      const l = largeursDesBarres(q.scores_normalises);
      expect(l[q.prefere]).toBe(1);
      for (const x of l) expect(x > 0 && x <= 1).toBe(true);
    }
  });

  it('le compte final : ton IA 2 sur 6, le hasard 1,5 en moyenne', () => {
    const c = compteDuQcm(QCM);
    expect(c).toStrictEqual({ justes: QCM.justes, n: 6, hasard: 1.5 });
    expect(c.justes).toBe(2);
    expect(texteDuCompte(c)).toBe(`Ton IA${FINE}: 2 sur 6, le hasard${FINE}: 1,5 en moyenne.`);
    expect(texteDuCompte({ justes: 3, n: 8, hasard: 2 })).toBe(`Ton IA${FINE}: 3 sur 8, le hasard${FINE}: 2 en moyenne.`);
    const faux = copie(QCM);
    faux.hasard = 0.3;
    expect(() => compteDuQcm(faux)).toThrow(/Exemple devenu faux/);
  });

  it('le défi compte les questions trouvées où ton IA a juste', () => {
    expect(questionsJustes(QCM)).toStrictEqual([3, 4]);
    expect(etatDuDefi([], QCM)).toStrictEqual({
      reussi: false,
      trouvees: 0,
      texte: `Pas encore${FINE}: aucune question trouvée où ton IA a juste.`,
    });
    // Une question où ton IA se trompe ne compte pas.
    expect(etatDuDefi([0, 1, 2], QCM).reussi).toBe(false);
    expect(etatDuDefi([0, 3], QCM)).toStrictEqual({
      reussi: true,
      trouvees: 1,
      texte: `Défi réussi${FINE}: 1 question trouvée sur 2 où ton IA a juste.`,
    });
    expect(etatDuDefi([0, 1, 2, 3, 4, 5], QCM).texte).toBe(`Défi réussi${FINE}: 2 questions trouvées sur 2 où ton IA a juste.`);
  });

  it('la réponse du défi : ce que disent les scores des deux questions justes', () => {
    const a = analyseDuDefi(QCM);
    expect(a.n).toBe(6);
    expect(a.questions.map((q) => q.indice)).toStrictEqual([3, 4]);
    const [q4, q5] = a.questions;
    // Question 4 : une avance minuscule, et le plus grand score brut est la réponse la plus courte, qui est fausse.
    expect(q4.avance).toBeCloseTo(0.0455, 4);
    expect(q4.rang).toBe(5);
    expect(q4.prefere).toBe(1);
    expect(q4.sansNormaliser).toBe(0);
    expect(q4.plusCourte).toBe(0);
    // Question 5 : l'avance la plus nette des six, et le même choix sans diviser par les octets.
    expect(q5.avance).toBeCloseTo(0.7114, 4);
    expect(q5.rang).toBe(1);
    expect(q5.sansNormaliser).toBe(q5.prefere);
    // Deux justes sur six : dans la marge du hasard.
    expect(a.verdict).toBe('pas-different');
    expect(a.verdict).toBe(verdictQcm(2 / 6, 0.25, margeHasard(6)));
    expect(phrasesDuDefi(a)).toStrictEqual([
      `À la question 4, la bonne réponse devance la suivante de 0,05 nat par octet${FINE}: ` +
        'c’est la deuxième avance la plus mince des 6 questions. ' +
        'Sans diviser par les octets, elle aurait choisi la réponse la plus courte, et se serait trompée.',
      `À la question 5, la bonne réponse devance la suivante de 0,71 nat par octet${FINE}: ` +
        'c’est l’avance la plus nette des 6 questions.',
    ]);
  });

  it('la réponse du défi refuse un relevé sans question juste', () => {
    const qcm = copie(QCM);
    for (const q of qcm.questions) q.juste = false;
    expect(() => analyseDuDefi(qcm)).toThrow(/le défi n’a plus de réponse/);
  });
});

describe('étape 5 : le pari « marge »', () => {
  it('le juste vient de la règle de forge : HellaSwag est au-dessus du hasard', () => {
    const choix = choixAuDessusDuHasard(MINI);
    expect(choix.map((c) => c.texte)).toStrictEqual(['Au-dessus du hasard', 'Pas différent du hasard', 'En dessous du hasard']);
    expect(juste(choix)).toBe('Au-dessus du hasard');
  });

  it('suit la règle sur d’autres nombres, et refuse un verdict noté qui la contredit', () => {
    const e = copie(MINI);
    const m = e.qcm.hellaswag;
    m.exactitude_normalisee = m.hasard + m.marge_hasard / 2;
    m.verdict = 'pas-different';
    expect(juste(choixAuDessusDuHasard(e))).toBe('Pas différent du hasard');
    m.exactitude_normalisee = m.hasard - 2 * m.marge_hasard;
    m.verdict = 'en-dessous';
    expect(juste(choixAuDessusDuHasard(e))).toBe('En dessous du hasard');
    m.verdict = 'au-dessus';
    expect(() => choixAuDessusDuHasard(e)).toThrow(/Exemple devenu faux/);
  });

  it('les verdicts en phrase', () => {
    expect(verdictEnPhrase('au-dessus')).toBe('au-dessus du hasard');
    expect(verdictEnPhrase('pas-different')).toBe('pas différent du hasard');
    expect(verdictEnPhrase('en-dessous')).toBe('en dessous du hasard');
  });

  it('la marge du hasard du projet est celle du rapport de forge pour HellaSwag, à 10⁻¹² près', () => {
    const m = MINI.qcm.hellaswag;
    expect(Math.abs(margeHasard(m.n) - m.marge_hasard)).toBeLessThanOrEqual(1e-12 * m.marge_hasard);
    // ARC : des questions qui n'ont pas toutes quatre choix, d'où un hasard qui n'est pas tout à fait un quart.
    expect(MINI.qcm.arc.hasard).not.toBe(0.25);
  });
});

describe('étape 6 : les échantillons', () => {
  it('les faits que le chapitre en dit', () => {
    expect(faitsDesEchantillons(MINI)).toStrictEqual({
      nombre: 10,
      jetons: 60,
      aucunNeSArrete: true,
      debutsDeCode: 2,
      codeIndente: true,
      codeSansSuite: true,
      docstringEnAnglais: true,
      prosePonctuee: true,
      capitaleSansParis: true,
      photosyntheseHorsSujet: true,
      soleilRepete: 2,
      villageDate: true,
    });
  });

  it('refuse un rapport qui n’a plus l’un des débuts de forge', () => {
    const e = copie(MINI);
    e.echantillons = e.echantillons.filter((x) => x.invite !== 'La capitale de la France est');
    expect(() => faitsDesEchantillons(e)).toThrow(/La capitale de la France est/);
  });
});

describe('étape 7 : le pari « limites »', () => {
  it('le juste est l’origine relevée de FrenchBench : traduit de l’anglais par une machine', () => {
    const choix = choixLangueFrenchBench();
    expect(choix.map((c) => c.texte)).toStrictEqual(ORIGINES_FRENCHBENCH.map((o) => o.texte));
    expect(juste(choix)).toBe('ont été traduites de l’anglais par une machine');
    expect(FRENCHBENCH.traduction.valeur).toBe('automatique');
  });
});
