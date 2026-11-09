// Les paris du chapitre 1.5 et ce qu'il lit autour d'eux : leurs bonnes réponses viennent des
// relevés du projet 1.5 (la version d'une heure de ton IA, l'essai de pause et de reprise), lus
// sur le disque, et les réglages viennent des configurations de forge, lues elles aussi.

import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterAll, describe, expect, it } from 'vitest';
import type { Choix } from '../choix';
import { PRESETS_FORGE, VOCABULAIRE_FORGE } from '../calculateur/ton-ia';
import { nombre } from '../nombres';
import { lireEntrainement, type Entrainement, type SessionEntrainement } from './journal';
import { MESURES_PARTIE_1 } from './mesures';
import {
  analyserReglages,
  arretsDeLaCourbe,
  choixDebitCourte,
  choixPerteDepartTonIA,
  choixReprise,
  dureeDeCalcul,
  ECART_DEPART_MAX,
  ECART_DU_DEFI,
  faitsDuPariDebit,
  faitsDuPariDepart,
  lignesDeLaCourbe,
  lignesDesSessions,
  lireEssaiDeReprise,
  lirePertesRecentes,
  lireReglages,
  pasTotalDesReglages,
  reponseDuDefi,
  TEXTES_REPRISE,
  trancheDuDebit,
  trancheDeLaPerte,
  TRANCHES_DEBIT,
  TRANCHES_DEPART,
  verifierEssai,
  type EssaiDeReprise,
} from './paris-1-5';

const FINE = '\u202F';

// Vitest est lancé depuis site/ : le dépôt est un dossier plus haut.
const MINI = lireEntrainement('ton-ia-mini') as Entrainement;
const ESSAI = JSON.parse(readFileSync(`../${MESURES_PARTIE_1.essaiProcesseur}`, 'utf8')) as EssaiDeReprise;

/** Le texte du seul choix juste ; échoue s'il n'y en a pas exactement un. */
function juste(choix: Choix[]): string {
  const justes = choix.filter((c) => c.juste === true);
  expect(justes, JSON.stringify(choix)).toHaveLength(1);
  return justes[0].texte;
}

/** Une copie modifiable du relevé de mini. */
const copieMini = (): Entrainement => structuredClone(MINI);

describe('le relevé de la version d’une heure', () => {
  it('existe : le chapitre le lit à la construction', () => {
    expect(MINI).not.toBeNull();
    expect(MINI.nom).toBe('ton-ia-mini');
  });
});

describe('le pari « depart » : la perte du premier pas de ton IA', () => {
  it('la bonne tranche est celle de la perte du premier pas de mini, tout près de ln 32 768', () => {
    const choix = choixPerteDepartTonIA(MINI);
    expect(choix.map((c) => c.texte)).toStrictEqual(TRANCHES_DEPART.map((t) => t.texte));
    expect(juste(choix)).toBe(TRANCHES_DEPART[trancheDeLaPerte(MINI.resume.perte_premier_pas)].texte);
    expect(juste(choix)).toBe('Plus de 5');
  });

  it('les tranches se suivent sans trou : moins de 1, de 1 à 5, plus de 5', () => {
    expect([0, 0.999, 1, 4.999, 5, 10.4, 1000].map(trancheDeLaPerte)).toStrictEqual([0, 0, 1, 1, 2, 2, 2]);
  });

  it('garde : une perte de départ à 0,2 ou plus de ln V arrête la construction', () => {
    expect(ECART_DEPART_MAX).toBe(0.2);
    for (const ecart of [0.21, -0.21, 0.5]) {
      const m = copieMini();
      m.resume.perte_premier_pas = m.courbe.hasard + ecart;
      expect(() => choixPerteDepartTonIA(m), String(ecart)).toThrow(/Exemple devenu faux/);
    }
    const m = copieMini();
    m.resume.perte_premier_pas = m.courbe.hasard + 0.19;
    expect(() => choixPerteDepartTonIA(m)).not.toThrow();
  });

  it('ses faits : la perte du premier pas, et le hasard ln V du vocabulaire de forge', () => {
    const f = faitsDuPariDepart(MINI);
    expect(f.premier).toBe(MINI.resume.perte_premier_pas);
    expect(f.hasard).toBe(MINI.courbe.hasard);
    expect(f.vocabulaire).toBe(VOCABULAIRE_FORGE);
    expect(Math.abs(f.hasard - Math.log(VOCABULAIRE_FORGE))).toBeLessThan(1e-12);
    expect(f.ecart).toBeCloseTo(MINI.resume.perte_premier_pas - MINI.courbe.hasard, 12);
  });

  it('garde : un hasard qui n’est plus ln 32 768 arrête la construction', () => {
    const m = copieMini();
    m.courbe.hasard = Math.log(50_000);
    m.resume.perte_premier_pas = m.courbe.hasard;
    expect(() => faitsDuPariDepart(m)).toThrow(/Exemple devenu faux/);
  });
});

describe('le pari « reprise » : la perte du pas repris', () => {
  it('l’essai du processeur : un écart nul, et « continue la courbe, au même nombre près » est juste', () => {
    expect(ESSAI.ecart).toBe(0);
    const choix = choixReprise(ESSAI);
    expect(choix.map((c) => c.texte)).toStrictEqual([...TEXTES_REPRISE]);
    expect(juste(choix)).toBe('continue la courbe, au même nombre près');
  });

  it('les trois choix, tels que la fiche les donne', () => {
    expect([...TEXTES_REPRISE]).toStrictEqual(['continue la courbe, au même nombre près', 'repart du hasard', 'fait un saut puis rattrape']);
  });

  it('garde : un écart non nul, ou des pertes qui diffèrent pas à pas, arrête la construction', () => {
    expect(() => choixReprise({ ...ESSAI, ecart: 1e-7, perte_reprise: ESSAI.perte_un_trait + 1e-7 })).toThrow(/Exemple devenu faux/);
    expect(() => choixReprise({ ...ESSAI, pertes_identiques: false })).toThrow(/Exemple devenu faux/);
  });

  it('lireEssaiDeReprise lit le relevé du projet, tel quel', () => {
    expect(lireEssaiDeReprise()).toStrictEqual(ESSAI);
  });

  it('verifierEssai refuse un relevé incomplet ou faux, en disant quoi faire', () => {
    expect(verifierEssai(ESSAI, 'essai.json')).toBe(ESSAI);
    const sans = { ...ESSAI } as Record<string, unknown>;
    delete sans.ecart;
    expect(() => verifierEssai(sans, 'essai.json')).toThrow(/essai\.json.*ecart.*pre_entrainement essai/);
    expect(() => verifierEssai({ ...ESSAI, pas_de_la_pause: ESSAI.pas_total }, 'essai.json')).toThrow(/pas_de_la_pause/);
    expect(() => verifierEssai({ ...ESSAI, ecart: 0.5 }, 'essai.json')).toThrow(/ecart/);
    expect(() => verifierEssai([], 'essai.json')).toThrow(/objet JSON/);
  });
});

describe('le pari « courte » : le débit de la version d’une heure', () => {
  it('la bonne tranche est celle du débit moyen de mini', () => {
    const choix = choixDebitCourte(MINI);
    expect(choix.map((c) => c.texte)).toStrictEqual(TRANCHES_DEBIT.map((t) => t.texte));
    expect(juste(choix)).toBe(TRANCHES_DEBIT[trancheDuDebit(MINI.resume.debit_moyen)].texte);
    expect(juste(choix)).toBe(`De 10${FINE}000 à un million`);
  });

  it('les tranches : moins de 10 000, de 10 000 à un million, plus d’un million', () => {
    expect(TRANCHES_DEBIT.map((t) => t.jusqua)).toStrictEqual([10_000, 1_000_000, Infinity]);
    expect(TRANCHES_DEBIT.map((t) => t.texte)).toStrictEqual([`Moins de 10${FINE}000`, `De 10${FINE}000 à un million`, 'Plus d’un million']);
    expect([9_999, 10_000, 999_999, 1_000_000].map(trancheDuDebit)).toStrictEqual([0, 1, 1, 2]);
  });

  it('ses faits : le débit est celui des jetons lus en tout, divisés par les secondes de calcul', () => {
    const f = faitsDuPariDebit(MINI);
    expect(f.debit).toBe(MINI.resume.debit_moyen);
    expect(Math.abs(f.debit - MINI.resume.jetons_vus / MINI.resume.secondes_de_calcul)).toBeLessThan(1e-6);
    expect(f.jetonsParParametre).toBeCloseTo(MINI.resume.jetons_vus / MINI.resume.parametres, 12);
    expect(f.lot).toBe(MINI.resume.jetons_vus / MINI.resume.pas_faits);
    expect(Number.isInteger(f.lot)).toBe(true);
  });

  it('garde : un débit qui n’est plus celui des jetons et des secondes arrête la construction', () => {
    const m = copieMini();
    m.resume.debit_moyen *= 2;
    expect(() => faitsDuPariDebit(m)).toThrow(/Exemple devenu faux/);
  });
});

describe('les réglages des configurations de forge', () => {
  it('mini : ceux de configs/mini.toml, et le même nombre de pas que le relevé', () => {
    const r = lireReglages('mini');
    expect(r).toStrictEqual({
      preset: 'mini',
      jetons_total: 834_928_640,
      taille_lot_jetons: 131_072,
      micro_lot: 16,
      taux_max: 1e-3,
      echauffement: 100,
      poids_decroissance: 0.1,
      betas: [0.9, 0.95],
      ecretage: 1,
      evaluation_tous_pas: 100,
      ratio_min: 0.1,
    });
    expect(pasTotalDesReglages(r)).toBe(MINI.resume.pas_total);
    expect(r.jetons_total).toBe(MINI.resume.jetons_vus);
    // Le lot est fait de micro-lots entiers de lignes de 512 jetons.
    expect(r.taille_lot_jetons % (r.micro_lot * PRESETS_FORGE.mini.contexte)).toBe(0);
  });

  it('principal : ceux de configs/principal.toml (la taille « très grand »)', () => {
    const r = lireReglages('principal');
    expect(r.preset).toBe('tres_grand');
    expect(pasTotalDesReglages(r)).toBe(16_540);
    expect(r.taille_lot_jetons % (r.micro_lot * PRESETS_FORGE.tres_grand.contexte)).toBe(0);
  });

  it('ratio_min est la valeur par défaut de taux() dans planning.py, que la boucle de forge ne change pas', () => {
    const planning = readFileSync('../projets/forge/forge/entrainement/planning.py', 'utf8');
    expect(planning).toContain('def taux(pas: int, pas_total: int, taux_max: float, echauffement: int, ratio_min: float = 0.1) -> float:');
    const boucle = readFileSync('../projets/forge/forge/entrainement/boucle.py', 'utf8');
    expect(boucle).toContain('taux(pas, pas_total, config.taux_max, config.echauffement)');
  });

  it('analyserReglages lit les nombres, les tableaux et les textes, et ignore les commentaires', () => {
    const texte = [
      '# un commentaire',
      'preset = "mini"  # la taille',
      'jetons_total = 1_000',
      'taille_lot_jetons = 512',
      'micro_lot = 1',
      'taux_max = 4e-4',
      'echauffement = 5',
      'poids_decroissance = 0.1',
      'betas = [0.9, 0.95]',
      'ecretage = 1.0',
      'evaluation_tous_pas = 10',
      'sortie = "essai"',
    ].join('\n');
    expect(analyserReglages(texte, 'essai.toml', 0.1)).toStrictEqual({
      preset: 'mini',
      jetons_total: 1000,
      taille_lot_jetons: 512,
      micro_lot: 1,
      taux_max: 4e-4,
      echauffement: 5,
      poids_decroissance: 0.1,
      betas: [0.9, 0.95],
      ecretage: 1,
      evaluation_tous_pas: 10,
      ratio_min: 0.1,
    });
    expect(pasTotalDesReglages(analyserReglages(texte, 'essai.toml', 0.1))).toBe(2);
  });

  it('un réglage manquant ou illisible arrête la lecture, en disant quoi faire', () => {
    expect(() => analyserReglages('preset = "mini"\n', 'essai.toml', 0.1)).toThrow(/essai\.toml.*jetons_total.*configs/);
    const faux = readFileSync('../projets/forge/configs/mini.toml', 'utf8').replace('micro_lot = 16', 'micro_lot = seize');
    expect(() => analyserReglages(faux, 'mini.toml', 0.1)).toThrow(/mini\.toml.*micro_lot/);
  });

  it('lireReglages refuse une racine qui n’a pas forge', () => {
    const vide = mkdtempSync(join(tmpdir(), 'forge-reglages-'));
    try {
      expect(() => lireReglages('mini', vide)).toThrow(/racine du dépôt/);
    } finally {
      rmSync(vide, { recursive: true, force: true });
    }
  });
});

describe('la fenêtre de la perte finale', () => {
  it('PERTES_RECENTES de forge/suivi.py, celle que le relevé du projet 1.5 utilise pour perte_finale', () => {
    expect(lirePertesRecentes()).toBe(20);
    const journal = readFileSync('../projets/1.5-pre-entrainement/pre_entrainement/journal.py', 'utf8');
    expect(journal).toContain('from forge.suivi import _FINS_DE_SESSION, PERTES_RECENTES, lire_journal');
    expect(journal).toContain('PERTES_RECENTES');
  });

  it('une racine sans forge est une erreur qui dit quoi donner', () => {
    const vide = mkdtempSync(join(tmpdir(), 'forge-suivi-'));
    try {
      expect(() => lirePertesRecentes(vide)).toThrow(/racine du dépôt/);
    } finally {
      rmSync(vide, { recursive: true, force: true });
    }
  });
});

describe('les sessions', () => {
  it('dureeDeCalcul : des secondes, des minutes et des secondes, puis des heures et des minutes', () => {
    // Une espace fine insécable lie chaque nombre à son unité.
    expect(dureeDeCalcul(0.4)).toBe(`0${FINE}s`);
    expect(dureeDeCalcul(42.4)).toBe(`42${FINE}s`);
    expect(dureeDeCalcul(59.6)).toBe(`1${FINE}min 0${FINE}s`);
    expect(dureeDeCalcul(3617.312)).toBe(`60${FINE}min 17${FINE}s`);
    expect(dureeDeCalcul(7199.4)).toBe(`119${FINE}min 59${FINE}s`);
    expect(dureeDeCalcul(7200)).toBe(`2${FINE}h 0${FINE}min`);
    expect(dureeDeCalcul(486_123)).toBe(`135${FINE}h 2${FINE}min`);
    expect(dureeDeCalcul(3_600_000)).toBe(`1${FINE}000${FINE}h 0${FINE}min`);
    expect(() => dureeDeCalcul(-1)).toThrow(RangeError);
    expect(() => dureeDeCalcul(Number.NaN)).toThrow(RangeError);
  });

  it('mini : une seule session, du départ à la fin, sans pause', () => {
    expect(lignesDesSessions(MINI.sessions)).toStrictEqual([
      { numero: 1, debut: 'départ', fin: 'fin', pas: `1 à 6${FINE}370`, duree: `60${FINE}min 17${FINE}s` },
    ]);
    expect(arretsDeLaCourbe(MINI.sessions)).toStrictEqual([]);
  });

  it('une session plantée avant son premier pas (premier et dernier pas à null) n’a aucun pas', () => {
    const sessions: SessionEntrainement[] = [
      { depart: 'debut', premier_pas: 1, dernier_pas: 500, secondes: 1200.4, fin: 'pause' },
      { depart: 'reprise', premier_pas: null, dernier_pas: null, secondes: 0, fin: 'coupée' },
      { depart: 'reprise', premier_pas: 501, dernier_pas: 900, secondes: 950, fin: 'perte_non_finie' },
      { depart: 'reprise', premier_pas: 901, dernier_pas: 1000, secondes: 230, fin: 'fin' },
    ];
    expect(lignesDesSessions(sessions)).toStrictEqual([
      { numero: 1, debut: 'départ', fin: 'pause', pas: '1 à 500', duree: `20${FINE}min 0${FINE}s` },
      { numero: 2, debut: 'reprise', fin: 'coupée', pas: 'aucun', duree: `0${FINE}s` },
      { numero: 3, debut: 'reprise', fin: 'perte non finie', pas: '501 à 900', duree: `15${FINE}min 50${FINE}s` },
      { numero: 4, debut: 'reprise', fin: 'fin', pas: `901 à 1${FINE}000`, duree: `3${FINE}min 50${FINE}s` },
    ]);
    // Les arrêts : la fin de chaque session, sauf la dernière, au dernier pas fait jusque-là.
    expect(arretsDeLaCourbe(sessions)).toStrictEqual([
      { pas: 500, fin: 'pause' },
      { pas: 500, fin: 'coupée' },
      { pas: 900, fin: 'perte_non_finie' },
    ]);
  });

  it('une première session plantée avant son premier pas ne fait pas d’arrêt sur la courbe', () => {
    const sessions: SessionEntrainement[] = [
      { depart: 'debut', premier_pas: null, dernier_pas: null, secondes: 0, fin: 'coupée' },
      { depart: 'reprise', premier_pas: 1, dernier_pas: 10, secondes: 3, fin: 'fin' },
    ];
    expect(arretsDeLaCourbe(sessions)).toStrictEqual([]);
    expect(lignesDesSessions(sessions)[0].pas).toBe('aucun');
  });
});

describe('la courbe en tableau', () => {
  it('une ligne par validation, avec la perte d’entraînement du paquet qui contient ce pas', () => {
    const lignes = lignesDeLaCourbe(MINI.courbe);
    expect(lignes).toHaveLength(MINI.courbe.validations.length);
    const t = MINI.courbe.taille_paquet;
    for (const [i, [pas, validation]] of MINI.courbe.validations.entries()) {
      expect(lignes[i].pas).toBe(pas);
      expect(lignes[i].validation).toBe(validation);
      expect(lignes[i].entrainement).toBe(MINI.courbe.pertes[Math.floor((pas - 1) / t)][1]);
    }
  });

  it('un pas hors de la courbe des pertes, ou un paquet sans perte, donne null', () => {
    const courbe = { taille_paquet: 2, hasard: 10, pertes: [[1.5, 9] as [number, number | null], [3.5, null] as [number, number | null]], validations: [[2, 8] as [number, number | null], [4, 7] as [number, number | null], [9, 6] as [number, number | null]] };
    expect(lignesDeLaCourbe(courbe)).toStrictEqual([
      { pas: 2, entrainement: 9, validation: 8 },
      { pas: 4, entrainement: null, validation: 7 },
      { pas: 9, entrainement: null, validation: 6 },
    ]);
  });
});

describe('la réponse du défi', () => {
  const fin = (taux: number, f: number) => ({ taux, fin: f });

  it('le plus grand taux dont l’erreur finit à 0,05 près de celle du taux par défaut, et le suivant', () => {
    expect(ECART_DU_DEFI).toBe(0.05);
    const r = reponseDuDefi(fin(0.01, 2.158), [fin(0.03, 2.186), fin(0.1, 2.281), fin(0.3, 2.451)]);
    expect(r).toStrictEqual({ defaut: fin(0.01, 2.158), reponse: fin(0.03, 2.186), suivant: fin(0.1, 2.281) });
  });

  it('un taux plus grand qui finit plus bas que le défaut compte aussi ; un taux qui explose, jamais', () => {
    const r = reponseDuDefi(fin(0.01, 2.2), [fin(0.03, 2.1), fin(0.1, 2.24), fin(0.3, Infinity)]);
    expect(r.reponse).toStrictEqual(fin(0.1, 2.24));
    expect(r.suivant).toStrictEqual(fin(0.3, Infinity));
  });

  it('les taux sont rangés du plus petit au plus grand, et tous au-dessus du défaut', () => {
    const r = reponseDuDefi(fin(0.01, 2.2), [fin(0.1, 2.5), fin(0.03, 2.21)]);
    expect(r.reponse).toStrictEqual(fin(0.03, 2.21));
    expect(r.suivant).toStrictEqual(fin(0.1, 2.5));
    expect(() => reponseDuDefi(fin(0.01, 2.2), [fin(0.003, 2.1)])).toThrow(/plus grand/);
  });

  it('garde : sans réponse au-dessus du défaut, ou sans taux au-delà de la réponse, le défi n’a plus de sens', () => {
    expect(() => reponseDuDefi(fin(0.01, 2.2), [fin(0.03, 2.3), fin(0.1, 2.4)])).toThrow(/Exemple devenu faux/);
    expect(() => reponseDuDefi(fin(0.01, 2.2), [fin(0.03, 2.21), fin(0.1, 2.22)])).toThrow(/Exemple devenu faux/);
    expect(() => reponseDuDefi(fin(0.01, Infinity), [fin(0.03, 2.21)])).toThrow(/Exemple devenu faux/);
  });
});

// Les dossiers temporaires des tests sont supprimés à la fin.
const TEMPORAIRES: string[] = [];
afterAll(() => {
  for (const d of TEMPORAIRES) rmSync(d, { recursive: true, force: true });
});

describe('lireEssaiDeReprise, sur un dépôt factice', () => {
  it('un relevé absent est une erreur qui dit quelle commande le refait', () => {
    const racine = mkdtempSync(join(tmpdir(), 'forge-essai-'));
    TEMPORAIRES.push(racine);
    mkdirSync(join(racine, 'projets/1.5-pre-entrainement/mesures'), { recursive: true });
    expect(() => lireEssaiDeReprise(racine)).toThrow(/essai-processeur\.json.*pre_entrainement essai/);
    writeFileSync(join(racine, MESURES_PARTIE_1.essaiProcesseur), '{ pas du json', 'utf8');
    expect(() => lireEssaiDeReprise(racine)).toThrow(/JSON illisible/);
    writeFileSync(join(racine, MESURES_PARTIE_1.essaiProcesseur), JSON.stringify(ESSAI), 'utf8');
    expect(lireEssaiDeReprise(racine)).toStrictEqual(ESSAI);
    expect(nombre(ESSAI.pas_total)).toBe('60');
  });
});
