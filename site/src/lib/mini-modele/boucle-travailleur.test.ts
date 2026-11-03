// La boucle du Worker, sans Worker : un faux entraîneur et une fausse horloge.
//
// Le faux entraîneur fait un pas en 0 ms (ou en coutPasMs, s'il avance
// l'horloge lui-même) : seul le rythme de la boucle compte ici. Le vrai
// entraîneur passe dans travailleur.test.ts.

import { describe, expect, it } from 'vitest';
import {
  BoucleTravailleur,
  DUREE_TRANCHE_MS,
  INTERVALLE_MESSAGES_MS,
  PAS_PAR_SECONDE_NORMAL,
  type EntraineurPilote,
  type MessageDuTravailleur,
  type ReglagesLancement,
} from './boucle-travailleur';
import { PRESETS_MINI, type ReglagesMini } from './reglages';

type Progres = Extract<MessageDuTravailleur, { type: 'progres' }>;

interface Options {
  /** Le pas où l'erreur explose (le faux entraîneur renvoie Infinity et s'arrête). */
  divergeAu?: number;
  /** Le pas où le moteur lève une erreur. */
  panneAu?: number;
  /** Une erreur dès la création de l'entraîneur. */
  panneALaCreation?: boolean;
  /** Remplace le nombre de pas du préréglage. */
  pasTotal?: number;
}

const CONNUS = new Set(['ana', 'léa']);
const ECHANTILLONS = ['ana', 'zxq', ''];

/** La perte du faux entraîneur au pas p : une suite facile à reconnaître. */
const perteDuPas = (p: number): number => 4 - p / 1000;

class FauxEntraineur implements EntraineurPilote {
  readonly reglages: ReglagesMini;
  readonly donnees = { connus: CONNUS as ReadonlySet<string> };
  pas = 0;
  diverge = false;
  validations = 0;

  constructor(
    reglages: ReglagesMini,
    private readonly options: Options,
    private readonly horloge: { t: number; coutPasMs: number },
  ) {
    this.reglages = options.pasTotal === undefined ? reglages : { ...reglages, pasTotal: options.pasTotal };
  }

  faireUnPas(): number {
    if (this.diverge) return Infinity;
    this.pas += 1;
    this.horloge.t += this.horloge.coutPasMs;
    if (this.pas === this.options.panneAu) throw new Error('panne simulée du moteur');
    if (this.pas === this.options.divergeAu) {
      this.diverge = true;
      return Infinity;
    }
    return perteDuPas(this.pas);
  }

  perteValidation(): number {
    this.validations += 1;
    return 5 - this.pas / 1000;
  }

  echantillons(): string[] {
    return [...ECHANTILLONS];
  }
}

function monter(options: Options = {}) {
  const horloge = { t: 0, coutPasMs: 0 };
  const envois: { t: number; m: MessageDuTravailleur }[] = [];
  const crees: { reglages: ReglagesMini; entraineur: FauxEntraineur }[] = [];
  const boucle = new BoucleTravailleur(
    (m) => envois.push({ t: horloge.t, m }),
    () => horloge.t,
    (r) => {
      if (options.panneALaCreation) throw new Error('création impossible');
      const entraineur = new FauxEntraineur(r, options, horloge);
      crees.push({ reglages: r, entraineur });
      return entraineur;
    },
  );
  /** Les pas faits par l'entraîneur courant. */
  const pasFaits = (): number => crees[crees.length - 1]?.entraineur.pas ?? 0;
  const messages = (): MessageDuTravailleur[] => envois.map((e) => e.m);
  const progres = (): Progres[] => messages().filter((m): m is Progres => m.type === 'progres');
  /** Fait des tranches jusqu'à ce que la boucle n'en demande plus (en avançant l'horloge de pas en pas). */
  const jusquAuBout = (pasMs = 10, limite = 100_000): void => {
    for (let i = 0; i < limite; i++) {
      if (!boucle.tranche()) return;
      horloge.t += pasMs;
    }
    throw new Error('la boucle ne s’arrête pas');
  };
  return { boucle, envois, horloge, crees, pasFaits, messages, progres, jusquAuBout };
}

const NORMALE: ReglagesLancement = { preset: 'complet', tauxMax: 0.01, vitesse: 'normale' };
const RAPIDE: ReglagesLancement = { preset: 'complet', tauxMax: 0.01, vitesse: 'rapide' };

describe('les constantes du rythme', () => {
  it('150 pas par seconde, des tranches de 50 ms, un message toutes les 100 ms', () => {
    expect(PAS_PAR_SECONDE_NORMAL).toBe(150);
    expect(DUREE_TRANCHE_MS).toBe(50);
    expect(INTERVALLE_MESSAGES_MS).toBe(100);
  });
});

describe('le rythme', () => {
  it('vitesse normale : au plus 150 pas par seconde, sans rattrapage après une pause', () => {
    const { boucle, horloge, pasFaits } = monter(); // faux entraîneur : 1 pas = 0 ms
    boucle.recevoir({ type: 'lancer', generation: 1, reglages: NORMALE });
    for (let t = 0; t <= 1000; t += 10) {
      horloge.t = t;
      boucle.tranche();
    }
    expect(pasFaits()).toBeGreaterThanOrEqual(149);
    expect(pasFaits()).toBeLessThanOrEqual(151);
    boucle.recevoir({ type: 'pause', generation: 1 });
    horloge.t = 11_000;
    expect(boucle.tranche()).toBe(false);
    const avant = pasFaits();
    boucle.recevoir({ type: 'lancer', generation: 1, reglages: NORMALE });
    horloge.t = 11_100;
    boucle.tranche();
    expect(pasFaits() - avant).toBeGreaterThan(0);
    expect(pasFaits() - avant).toBeLessThanOrEqual(16);
  });

  it('pas de rafale non plus après un long trou sans pause (portable en veille)', () => {
    const { boucle, horloge, pasFaits, progres } = monter();
    boucle.recevoir({ type: 'lancer', generation: 1, reglages: NORMALE });
    for (let t = 0; t <= 1000; t += 10) {
      horloge.t = t;
      boucle.tranche();
    }
    const avant = pasFaits();
    horloge.t = 60_000; // une minute sans aucune tranche
    boucle.tranche();
    expect(pasFaits() - avant).toBeLessThanOrEqual(16);
    const ensuite = pasFaits();
    for (let t = 60_010; t <= 61_000; t += 10) {
      horloge.t = t;
      boucle.tranche();
    }
    expect(pasFaits() - ensuite).toBeLessThanOrEqual(151);
    // Le trou ne compte pas dans la durée, ni dans les pas par seconde.
    boucle.recevoir({ type: 'pause', generation: 1 });
    const fin = progres().at(-1);
    expect(fin?.dureeMs).toBe(2000);
    expect(fin?.pasParSeconde).toBeGreaterThan(140);
    expect(fin?.pasParSeconde).toBeLessThanOrEqual(150);
  });

  it('vitesse rapide : une tranche enchaîne les pas jusqu’à 50 ms', () => {
    const { boucle, horloge, pasFaits } = monter();
    horloge.coutPasMs = 1;
    boucle.recevoir({ type: 'lancer', generation: 1, reglages: RAPIDE });
    expect(boucle.tranche()).toBe(true);
    expect(pasFaits()).toBe(50);
    expect(horloge.t).toBe(50);
  });

  it('vitesse normale avec des pas lents : la tranche s’arrête aussi à 50 ms', () => {
    const { boucle, horloge, pasFaits } = monter();
    horloge.coutPasMs = 20; // 50 pas par seconde au mieux : moins que 150
    boucle.recevoir({ type: 'lancer', generation: 1, reglages: NORMALE });
    horloge.t = 10;
    boucle.tranche();
    // Des pas entiers : le troisième commence à 50 ms (40 ms de tranche) et finit à 70 ms.
    expect(pasFaits()).toBe(3);
    expect(horloge.t).toBe(70);
  });

  it('changer de vitesse repart d’une fenêtre neuve', () => {
    const { boucle, horloge, pasFaits } = monter();
    boucle.recevoir({ type: 'lancer', generation: 1, reglages: RAPIDE });
    horloge.coutPasMs = 1;
    boucle.tranche(); // 50 pas, jusqu'à t = 50
    horloge.coutPasMs = 0;
    boucle.recevoir({ type: 'vitesse', generation: 1, vitesse: 'normale' });
    const avant = pasFaits();
    horloge.t = 150;
    boucle.tranche();
    expect(pasFaits() - avant).toBe(15); // 150 × 100 ms / 1 000, depuis le changement
    boucle.recevoir({ type: 'vitesse', generation: 1, vitesse: 'rapide' });
    boucle.tranche(); // l'horloge ne bouge plus : la tranche va jusqu'au bout
    expect(pasFaits()).toBe(PRESETS_MINI.complet.pasTotal);
  });
});

describe('les messages', () => {
  it('un lancer d’une nouvelle génération crée l’entraîneur avec { ...PRESETS_MINI[preset], tauxMax }', () => {
    const { boucle, crees, horloge, messages } = monter();
    boucle.recevoir({ type: 'lancer', generation: 1, reglages: RAPIDE });
    horloge.coutPasMs = 1;
    boucle.tranche();
    boucle.recevoir({ type: 'lancer', generation: 2, reglages: { preset: 'avant-gout', tauxMax: 0.3, vitesse: 'rapide' } });
    expect(crees.map((c) => c.reglages)).toEqual([
      { ...PRESETS_MINI.complet, tauxMax: 0.01 },
      { ...PRESETS_MINI['avant-gout'], tauxMax: 0.3 },
    ]);
    // La nouvelle génération repart de zéro, et ses messages portent son numéro.
    horloge.coutPasMs = 0;
    boucle.tranche();
    expect(crees[1].entraineur.pas).toBe(PRESETS_MINI['avant-gout'].pasTotal);
    const deLaDeux = messages().filter((m) => m.generation === 2);
    expect(deLaDeux.at(-1)).toEqual({ type: 'etat', generation: 2, etat: 'termine' });
    const premier = deLaDeux.find((m): m is Progres => m.type === 'progres');
    expect(premier?.pertes[0]).toBe(perteDuPas(1));
  });

  it('progres toutes les 100 ms au plus, avec les pertes des pas faits depuis le précédent', () => {
    const { boucle, envois, horloge, progres, pasFaits } = monter();
    boucle.recevoir({ type: 'lancer', generation: 1, reglages: NORMALE });
    for (let t = 0; t <= 2000; t += 7) {
      horloge.t = t;
      boucle.tranche();
    }
    const temps = envois.filter((e) => e.m.type === 'progres' && e.m.validation === undefined).map((e) => e.t);
    expect(temps.length).toBeGreaterThan(10);
    for (let i = 1; i < temps.length; i++) {
      expect(temps[i] - temps[i - 1]).toBeGreaterThanOrEqual(INTERVALLE_MESSAGES_MS);
    }
    // Les pertes, mises bout à bout, sont celles des pas 1, 2, 3… sans trou ni doublon.
    const toutes = progres().flatMap((m) => m.pertes);
    expect(toutes).toEqual(Array.from({ length: toutes.length }, (_, i) => perteDuPas(i + 1)));
    expect(progres().at(-1)?.pas).toBe(toutes.length);
    expect(pasFaits() - toutes.length).toBeLessThanOrEqual(15); // le reste attend le prochain message
    for (const m of progres()) {
      expect(m.pasTotal).toBe(PRESETS_MINI.complet.pasTotal);
      expect(m.generation).toBe(1);
      expect(m.pertes.length).toBeGreaterThan(0); // jamais de message vide
    }
  });

  it('validation et prénoms aux multiples de 100, puis « termine »', () => {
    const { boucle, crees, messages, progres, jusquAuBout } = monter();
    boucle.recevoir({ type: 'lancer', generation: 1, reglages: RAPIDE });
    jusquAuBout();
    const r = PRESETS_MINI.complet;
    const avecValidation = progres().filter((m) => m.validation !== undefined);
    const attendus = Array.from({ length: r.pasTotal / r.validationTous }, (_, i) => (i + 1) * r.validationTous);
    expect(avecValidation.map((m) => m.validation?.pas)).toEqual(attendus);
    for (const m of avecValidation) {
      expect(m.pas).toBe(m.validation?.pas);
      expect(m.validation?.perte).toBe(5 - m.pas / 1000);
      expect(m.echantillons).toEqual({
        pas: m.pas,
        prenoms: [
          { texte: 'ana', existe: true },
          { texte: 'zxq', existe: false },
          { texte: '', existe: false },
        ],
      });
    }
    expect(progres().filter((m) => m.echantillons !== undefined)).toHaveLength(attendus.length);
    expect(crees[0].entraineur.validations).toBe(attendus.length);
    expect(progres().flatMap((m) => m.pertes)).toHaveLength(r.pasTotal);
    const fin = messages().slice(-2);
    expect(fin[0]).toMatchObject({ type: 'progres', pas: r.pasTotal, validation: { pas: r.pasTotal } });
    expect(fin[1]).toEqual({ type: 'etat', generation: 1, etat: 'termine' });
    // Ensuite, plus rien : ni tranche, ni reprise.
    const n = messages().length;
    boucle.recevoir({ type: 'lancer', generation: 1, reglages: RAPIDE });
    boucle.recevoir({ type: 'pause', generation: 1 });
    expect(boucle.tranche()).toBe(false);
    expect(messages()).toHaveLength(n);
  });

  it('la validation et les prénoms aussi au dernier pas, s’il ne tombe pas sur un multiple', () => {
    const { boucle, progres, messages, jusquAuBout } = monter({ pasTotal: 250 });
    boucle.recevoir({ type: 'lancer', generation: 1, reglages: RAPIDE });
    jusquAuBout();
    expect(progres().flatMap((m) => (m.validation ? [m.validation.pas] : []))).toEqual([100, 200, 250]);
    expect(progres().flatMap((m) => (m.echantillons ? [m.echantillons.pas] : []))).toEqual([100, 200, 250]);
    expect(messages().at(-1)).toEqual({ type: 'etat', generation: 1, etat: 'termine' });
  });

  it('pause : les pertes en attente, puis etat en-pause, puis plus rien', () => {
    const { boucle, horloge, messages, progres, pasFaits } = monter();
    boucle.recevoir({ type: 'lancer', generation: 1, reglages: NORMALE });
    for (let t = 0; t <= 150; t += 10) {
      horloge.t = t;
      boucle.tranche();
    }
    const n = messages().length;
    const envoyes = progres().flatMap((m) => m.pertes).length;
    expect(pasFaits()).toBeGreaterThan(envoyes); // des pertes attendent le prochain message
    boucle.recevoir({ type: 'pause', generation: 1 });
    const apres = messages().slice(n);
    expect(apres.map((m) => m.type)).toEqual(['progres', 'etat']);
    expect(apres[0]).toMatchObject({ type: 'progres', generation: 1, pas: pasFaits() });
    expect(apres[1]).toEqual({ type: 'etat', generation: 1, etat: 'en-pause' });
    expect(progres().flatMap((m) => m.pertes)).toHaveLength(pasFaits());
    // Plus rien, même longtemps après.
    for (let t = 200; t <= 5000; t += 100) {
      horloge.t = t;
      expect(boucle.tranche()).toBe(false);
    }
    expect(messages()).toHaveLength(n + 2);
  });

  it('pause sans pertes en attente : seulement etat en-pause', () => {
    const { boucle, messages } = monter();
    boucle.recevoir({ type: 'lancer', generation: 1, reglages: NORMALE });
    boucle.recevoir({ type: 'pause', generation: 1 });
    expect(messages()).toEqual([{ type: 'etat', generation: 1, etat: 'en-pause' }]);
    boucle.recevoir({ type: 'pause', generation: 1 }); // déjà en pause : rien de plus
    expect(messages()).toHaveLength(1);
  });

  it('une pause d’une autre génération est ignorée, une vitesse aussi', () => {
    const { boucle, horloge, messages, pasFaits } = monter();
    boucle.recevoir({ type: 'lancer', generation: 2, reglages: NORMALE });
    horloge.t = 100;
    boucle.tranche();
    const avant = pasFaits();
    boucle.recevoir({ type: 'pause', generation: 1 });
    boucle.recevoir({ type: 'vitesse', generation: 1, vitesse: 'rapide' });
    expect(messages().some((m) => m.type === 'etat')).toBe(false);
    horloge.t = 200;
    expect(boucle.tranche()).toBe(true);
    expect(pasFaits() - avant).toBe(15); // toujours au rythme normal
  });

  it('une pause ou une vitesse avant tout lancement est ignorée', () => {
    const { boucle, messages } = monter();
    boucle.recevoir({ type: 'pause', generation: 1 });
    boucle.recevoir({ type: 'vitesse', generation: 1, vitesse: 'rapide' });
    expect(boucle.tranche()).toBe(false);
    expect(messages()).toEqual([]);
  });

  it('pas par seconde et durée : mesurés sur l’horloge, sans compter les pauses', () => {
    const { boucle, horloge, progres } = monter();
    boucle.recevoir({ type: 'lancer', generation: 1, reglages: NORMALE });
    for (let t = 0; t <= 1000; t += 10) {
      horloge.t = t;
      boucle.tranche();
    }
    boucle.recevoir({ type: 'pause', generation: 1 });
    const enPause = progres().at(-1);
    expect(enPause?.dureeMs).toBe(1000);
    expect(enPause?.pasParSeconde).toBe(150);
    horloge.t = 60_000;
    boucle.recevoir({ type: 'lancer', generation: 1, reglages: NORMALE });
    for (let t = 60_010; t <= 60_500; t += 10) {
      horloge.t = t;
      boucle.tranche();
    }
    boucle.recevoir({ type: 'pause', generation: 1 });
    const fin = progres().at(-1);
    expect(fin?.dureeMs).toBe(1500); // et pas 60 500 : la minute de pause ne compte pas
    expect(fin?.pasParSeconde).toBe(150);
  });
});

describe('la fin', () => {
  it('divergence : progres, puis etat diverge, puis plus rien', () => {
    const { boucle, crees, messages, jusquAuBout } = monter({ divergeAu: 150 });
    boucle.recevoir({ type: 'lancer', generation: 1, reglages: RAPIDE });
    jusquAuBout();
    const fin = messages().slice(-2);
    expect(fin[0]).toMatchObject({ type: 'progres', pas: 150 });
    expect(fin[0].type === 'progres' && fin[0].pertes.at(-1)).toBe(Infinity);
    expect(fin[0].type === 'progres' && fin[0].validation).toBeUndefined();
    expect(fin[1]).toEqual({ type: 'etat', generation: 1, etat: 'diverge' });
    expect(crees[0].entraineur.pas).toBe(150);
    const n = messages().length;
    boucle.recevoir({ type: 'lancer', generation: 1, reglages: RAPIDE });
    expect(boucle.tranche()).toBe(false);
    expect(messages()).toHaveLength(n);
  });

  it('une erreur du moteur devient un message erreur', () => {
    const { boucle, messages, progres, jusquAuBout } = monter({ panneAu: 42 });
    boucle.recevoir({ type: 'lancer', generation: 3, reglages: RAPIDE });
    jusquAuBout();
    expect(messages().at(-1)).toEqual({ type: 'erreur', generation: 3, message: 'panne simulée du moteur' });
    // Les 41 pas faits avant la panne sont envoyés d'abord.
    expect(progres().flatMap((m) => m.pertes)).toHaveLength(41);
    const n = messages().length;
    boucle.recevoir({ type: 'lancer', generation: 3, reglages: RAPIDE });
    expect(boucle.tranche()).toBe(false);
    expect(messages()).toHaveLength(n);
  });

  it('une erreur à la création de l’entraîneur aussi', () => {
    const { boucle, messages } = monter({ panneALaCreation: true });
    boucle.recevoir({ type: 'lancer', generation: 1, reglages: RAPIDE });
    expect(messages()).toEqual([{ type: 'erreur', generation: 1, message: 'création impossible' }]);
    expect(boucle.tranche()).toBe(false);
  });

  it('un préréglage inconnu devient un message erreur qui dit quoi faire', () => {
    const { boucle, messages } = monter();
    const reglages = { ...RAPIDE, preset: 'geant' } as unknown as ReglagesLancement;
    boucle.recevoir({ type: 'lancer', generation: 1, reglages });
    expect(messages()).toHaveLength(1);
    expect(messages()[0]).toMatchObject({ type: 'erreur', generation: 1, message: expect.stringMatching(/« complet »/) });
  });
});
