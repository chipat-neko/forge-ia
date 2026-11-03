// Le réducteur de la démo : un état et un événement donnent un nouvel état,
// et au plus un message pour le Worker. Aucun moteur ici : l'état de départ
// est écrit à la main (le vrai vient d'apercu.ts, calculé par Astro).

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import type { EtatInitialMini } from './apercu';
import type { MessageDuTravailleur } from './boucle-travailleur';
import {
  actionPrincipale,
  etatDeDepart,
  MESSAGE_DIVERGENCE,
  MESSAGE_NOUVEAU_TAUX,
  MESSAGE_ONGLET,
  messageErreur,
  messageTermine,
  prenomAffiche,
  reduire,
  tauxIndexParDefaut,
  type EtatDemo,
  type Evenement,
} from './pilote';
import { PRESETS_MINI, TAUX_PROPOSES } from './reglages';

const FINE = '\u202F';
const INDEX_001 = TAUX_PROPOSES.indexOf(0.01);

// Un départ écrit à la main. Le réducteur n'en lit que preset, pasTotal,
// perteValidation et echantillons : les autres valeurs sont quelconques.
const INITIAL: EtatInitialMini = {
  preset: 'complet',
  pasTotal: 3000,
  tailleVocabulaire: 12,
  nbParametres: 100,
  nbEntrainement: 50,
  perteHasard: 2.5,
  perteValidation: 3.7,
  echantillons: [
    { texte: 'xqz', existe: false },
    { texte: '', existe: false },
    { texte: 'léa', existe: true },
  ],
};

/** Gèle l'état en profondeur : un réducteur qui le modifierait lèverait une erreur (mode strict). */
function geler<T>(x: T): T {
  if (x !== null && typeof x === 'object' && !Object.isFrozen(x)) {
    Object.freeze(x);
    for (const v of Object.values(x)) geler(v);
  }
  return x;
}

/** Applique les événements un à un, et garde les envois. */
function jouer(etat: EtatDemo, evenements: Evenement[], preset: 'complet' | 'avant-gout' = 'complet') {
  const envois: unknown[] = [];
  for (const ev of evenements) {
    const r = reduire(geler(etat), ev, preset);
    etat = r.etat;
    if (r.envoi !== null) envois.push(r.envoi);
  }
  return { etat, envois };
}

const progres = (generation: number, pas: number, extra: Partial<Extract<MessageDuTravailleur, { type: 'progres' }>> = {}): Evenement => ({
  type: 'message',
  message: { type: 'progres', generation, pas, pasTotal: 3000, pertes: [3.1, 3.0], dureeMs: 1000, pasParSeconde: 148, ...extra },
});
const etatW = (generation: number, etat: 'en-pause' | 'termine' | 'diverge'): Evenement => ({
  type: 'message',
  message: { type: 'etat', generation, etat },
});

describe('etatDeDepart', () => {
  it('pas 0, prêt, avec la validation et les prénoms du départ', () => {
    const e = etatDeDepart(INITIAL, INDEX_001);
    expect(e).toEqual({
      generation: 1,
      phase: 'pret',
      raisonPause: null,
      tauxIndex: INDEX_001,
      vitesse: 'normale',
      pas: 0,
      pasTotal: 3000,
      pertes: [],
      validations: [{ pas: 0, perte: 3.7 }],
      echantillons: [{ pas: 0, prenoms: INITIAL.echantillons }],
      fantome: null,
      pasParSeconde: 0,
      dureeMs: 0,
      message: null,
      travailleur: 'arrete',
    });
    // Une copie : l'état ne partage rien avec initial.
    expect(e.echantillons[0].prenoms).not.toBe(INITIAL.echantillons);
  });

  it('l’avant-goût va toujours vite', () => {
    const e = etatDeDepart({ ...INITIAL, preset: 'avant-gout', pasTotal: 600 }, tauxIndexParDefaut('avant-gout'));
    expect(e.vitesse).toBe('rapide');
    expect(e.pasTotal).toBe(600);
  });

  it('refuse un taux hors de la liste', () => {
    expect(() => etatDeDepart(INITIAL, TAUX_PROPOSES.length)).toThrow(/de 0 à 5/);
    expect(() => etatDeDepart(INITIAL, -1)).toThrow(RangeError);
    expect(() => etatDeDepart(INITIAL, 1.5)).toThrow(RangeError);
  });

  it('le taux par défaut de chaque préréglage est dans la liste', () => {
    expect(TAUX_PROPOSES[tauxIndexParDefaut('complet')]).toBe(PRESETS_MINI.complet.tauxMax);
    expect(TAUX_PROPOSES[tauxIndexParDefaut('avant-gout')]).toBe(PRESETS_MINI['avant-gout'].tauxMax);
  });
});

describe('lancer, pause, reprise', () => {
  it('lancer depuis « pret » : en cours, et le message lancer avec le taux et la vitesse', () => {
    const { etat, envois } = jouer(etatDeDepart(INITIAL, INDEX_001), [{ type: 'lancer' }]);
    expect(etat.phase).toBe('en-cours');
    expect(etat.travailleur).toBe('en-cours');
    expect(envois).toEqual([{ type: 'lancer', generation: 1, reglages: { preset: 'complet', tauxMax: 0.01, vitesse: 'normale' } }]);
  });

  it('pause « lecteur », puis reprise : la même génération, sans message', () => {
    const { etat, envois } = jouer(etatDeDepart(INITIAL, INDEX_001), [
      { type: 'lancer' },
      { type: 'pause', raison: 'lecteur' },
    ]);
    expect(etat.phase).toBe('en-pause');
    expect(etat.raisonPause).toBe('lecteur');
    expect(etat.message).toBeNull();
    expect(envois.at(-1)).toEqual({ type: 'pause', generation: 1 });
    const repris = jouer(etat, [{ type: 'lancer' }]);
    expect(repris.etat.phase).toBe('en-cours');
    expect(repris.etat.raisonPause).toBeNull();
    expect(repris.envois).toEqual([{ type: 'lancer', generation: 1, reglages: { preset: 'complet', tauxMax: 0.01, vitesse: 'normale' } }]);
  });

  it('pause « onglet » : phase en-pause et message exact', () => {
    const { etat, envois } = jouer(etatDeDepart(INITIAL, INDEX_001), [
      { type: 'lancer' },
      { type: 'pause', raison: 'onglet' },
    ]);
    expect(etat.phase).toBe('en-pause');
    expect(etat.raisonPause).toBe('onglet');
    expect(etat.message).toBe(`En pause${FINE}: l’onglet était caché. Reprends quand tu veux.`);
    expect(MESSAGE_ONGLET).toBe(etat.message);
    expect(envois.at(-1)).toEqual({ type: 'pause', generation: 1 });
    // La reprise efface le message.
    expect(jouer(etat, [{ type: 'lancer' }]).etat.message).toBeNull();
  });

  it('une pause hors de « en-cours » est ignorée', () => {
    const depart = etatDeDepart(INITIAL, INDEX_001);
    expect(reduire(depart, { type: 'pause', raison: 'onglet' }, 'complet')).toEqual({ etat: depart, envoi: null });
    const enPause = jouer(depart, [{ type: 'lancer' }, { type: 'pause', raison: 'lecteur' }]).etat;
    expect(reduire(enPause, { type: 'pause', raison: 'onglet' }, 'complet')).toEqual({ etat: enPause, envoi: null });
  });

  it('pendant la pause, les progres de la même génération s’ajoutent encore, puis le Worker confirme', () => {
    const { etat } = jouer(etatDeDepart(INITIAL, INDEX_001), [
      { type: 'lancer' },
      { type: 'pause', raison: 'lecteur' },
      progres(1, 120),
    ]);
    expect(etat.phase).toBe('en-pause');
    expect(etat.pas).toBe(120);
    expect(etat.pertes).toEqual([3.1, 3.0]);
    expect(etat.travailleur).toBe('en-cours'); // pas encore confirmé
    const confirme = jouer(etat, [etatW(1, 'en-pause')]).etat;
    expect(confirme.travailleur).toBe('en-pause');
    expect(confirme.phase).toBe('en-pause');
  });

  it('une confirmation de pause arrivée après la reprise ne change rien', () => {
    const { etat } = jouer(etatDeDepart(INITIAL, INDEX_001), [
      { type: 'lancer' },
      { type: 'pause', raison: 'lecteur' },
      { type: 'lancer' },
      etatW(1, 'en-pause'),
    ]);
    expect(etat.phase).toBe('en-cours');
    expect(etat.travailleur).toBe('en-cours');
  });

  it('lancer après « termine » est ignoré', () => {
    const fini = jouer(etatDeDepart(INITIAL, INDEX_001), [{ type: 'lancer' }, progres(1, 3000), etatW(1, 'termine')]).etat;
    expect(fini.phase).toBe('termine');
    expect(reduire(fini, { type: 'lancer' }, 'complet')).toEqual({ etat: fini, envoi: null });
    expect(reduire(fini, { type: 'pause', raison: 'lecteur' }, 'complet')).toEqual({ etat: fini, envoi: null });
  });

  it('lancer pendant « en-cours » est ignoré (double clic)', () => {
    const enCours = jouer(etatDeDepart(INITIAL, INDEX_001), [{ type: 'lancer' }]).etat;
    expect(reduire(enCours, { type: 'lancer' }, 'complet')).toEqual({ etat: enCours, envoi: null });
  });
});

describe('les messages du Worker', () => {
  it('progres : ajoute les pertes, la validation et les prénoms', () => {
    const prenoms = [{ texte: 'léa', existe: true }];
    const { etat } = jouer(etatDeDepart(INITIAL, INDEX_001), [
      { type: 'lancer' },
      progres(1, 98, { pertes: [3.5, 3.4], dureeMs: 650, pasParSeconde: 150 }),
      progres(1, 100, {
        pertes: [3.3, 3.2],
        dureeMs: 670,
        pasParSeconde: 149,
        validation: { pas: 100, perte: 3.25 },
        echantillons: { pas: 100, prenoms },
      }),
    ]);
    expect(etat.pertes).toEqual([3.5, 3.4, 3.3, 3.2]);
    expect(etat.validations).toEqual([
      { pas: 0, perte: 3.7 },
      { pas: 100, perte: 3.25 },
    ]);
    expect(etat.echantillons).toEqual([
      { pas: 0, prenoms: INITIAL.echantillons },
      { pas: 100, prenoms },
    ]);
    expect(etat.pas).toBe(100);
    expect(etat.dureeMs).toBe(670);
    expect(etat.pasParSeconde).toBe(149);
  });

  it('un message d’une ancienne génération ne change rien', () => {
    const avant = jouer(etatDeDepart(INITIAL, INDEX_001), [{ type: 'lancer' }, { type: 'recommencer' }, { type: 'lancer' }]).etat;
    expect(avant.generation).toBe(2);
    for (const ev of [
      progres(1, 500, { validation: { pas: 500, perte: 1 }, echantillons: { pas: 500, prenoms: [] } }),
      etatW(1, 'termine'),
      etatW(1, 'diverge'),
      etatW(1, 'en-pause'),
      { type: 'message', message: { type: 'erreur', generation: 1, message: 'vieux' } } as Evenement,
    ]) {
      const r = reduire(avant, ev, 'complet');
      expect(r.etat).toBe(avant);
      expect(r.envoi).toBeNull();
    }
  });

  it('termine : « Terminé : 3 000 pas en 21 s. », avec les nombres réels', () => {
    const { etat } = jouer(etatDeDepart(INITIAL, INDEX_001), [
      { type: 'lancer' },
      progres(1, 3000, { dureeMs: 20_600 }),
      etatW(1, 'termine'),
    ]);
    expect(etat.phase).toBe('termine');
    expect(etat.travailleur).toBe('arrete');
    expect(etat.message).toBe(`Terminé${FINE}: 3${FINE}000 pas en 21 s.`);
    expect(messageTermine(600, 1_234_567)).toBe(`Terminé${FINE}: 600 pas en 1${FINE}235 s.`);
  });

  it('diverge : le message exact', () => {
    const { etat } = jouer(etatDeDepart(INITIAL, INDEX_001), [{ type: 'lancer' }, progres(1, 40), etatW(1, 'diverge')]);
    expect(etat.phase).toBe('diverge');
    expect(etat.travailleur).toBe('arrete');
    expect(etat.message).toBe(`L’erreur a explosé${FINE}: ce taux est trop grand. Recommence avec un taux plus petit.`);
    expect(MESSAGE_DIVERGENCE).toBe(etat.message);
    expect(reduire(etat, { type: 'lancer' }, 'complet').envoi).toBeNull();
  });

  it('erreur : « La démo s’est arrêtée : … »', () => {
    const { etat } = jouer(etatDeDepart(INITIAL, INDEX_001), [
      { type: 'lancer' },
      { type: 'message', message: { type: 'erreur', generation: 1, message: 'mémoire pleine' } },
    ]);
    expect(etat.phase).toBe('erreur');
    expect(etat.travailleur).toBe('arrete');
    expect(etat.message).toBe(`La démo s’est arrêtée${FINE}: mémoire pleine`);
    expect(messageErreur('panne')).toBe(`La démo s’est arrêtée${FINE}: panne`);
  });
});

describe('recommencer et changer le taux', () => {
  const enCours = (): EtatDemo =>
    jouer(etatDeDepart(INITIAL, INDEX_001), [
      { type: 'lancer' },
      progres(1, 100, { validation: { pas: 100, perte: 3.2 }, echantillons: { pas: 100, prenoms: [{ texte: 'ana', existe: true }] } }),
    ]).etat;

  it('recommencer garde la courbe en fantôme et repart du pas 0', () => {
    const avant = enCours();
    const { etat, envoi } = reduire(geler(avant), { type: 'recommencer' }, 'complet');
    expect(envoi).toEqual({ type: 'pause', generation: 1 }); // l'ancienne génération
    expect(etat).toEqual({
      ...etatDeDepart(INITIAL, INDEX_001),
      generation: 2,
      fantome: { pertes: avant.pertes, validations: avant.validations, tauxIndex: INDEX_001 },
    });
  });

  it('recommencer au pas 0 garde le fantôme d’avant', () => {
    const une = reduire(enCours(), { type: 'recommencer' }, 'complet').etat;
    const deux = reduire(une, { type: 'recommencer' }, 'complet');
    expect(deux.etat.generation).toBe(3);
    expect(deux.etat.fantome).toEqual(une.fantome);
    expect(deux.envoi).toEqual({ type: 'pause', generation: 2 });
  });

  it('recommencer garde la vitesse choisie', () => {
    const rapide = jouer(enCours(), [{ type: 'vitesse', vitesse: 'rapide' }, { type: 'recommencer' }]).etat;
    expect(rapide.vitesse).toBe('rapide');
    expect(rapide.phase).toBe('pret');
  });

  it('recommencer après une divergence : de nouveau prêt', () => {
    const diverge = jouer(enCours(), [etatW(1, 'diverge'), { type: 'recommencer' }]).etat;
    expect(diverge.phase).toBe('pret');
    expect(diverge.message).toBeNull();
    expect(jouer(diverge, [{ type: 'lancer' }]).envois).toEqual([
      { type: 'lancer', generation: 2, reglages: { preset: 'complet', tauxMax: 0.01, vitesse: 'normale' } },
    ]);
  });

  it('changer le taux repart de zéro, prêt, avec son message', () => {
    const avant = enCours();
    const nouveau = INDEX_001 + 1;
    const { etat, envoi } = reduire(geler(avant), { type: 'changer-taux', tauxIndex: nouveau }, 'complet');
    expect(envoi).toEqual({ type: 'pause', generation: 1 });
    expect(etat).toEqual({
      ...etatDeDepart(INITIAL, nouveau),
      generation: 2,
      fantome: { pertes: avant.pertes, validations: avant.validations, tauxIndex: INDEX_001 },
      message: `Nouveau taux${FINE}: l’entraînement repart de zéro.`,
    });
    expect(MESSAGE_NOUVEAU_TAUX).toBe(etat.message);
    // Prêt (et non en pause) : le bouton dit « Lancer l'entraînement ».
    expect(etat.phase).toBe('pret');
    expect(actionPrincipale(etat)).toEqual({ texte: 'Lancer l’entraînement', evenement: { type: 'lancer' } });
    // Le lancement suivant prend le nouveau taux, et efface le message.
    const lance = reduire(etat, { type: 'lancer' }, 'complet');
    expect(lance.envoi).toEqual({
      type: 'lancer',
      generation: 2,
      reglages: { preset: 'complet', tauxMax: TAUX_PROPOSES[nouveau], vitesse: 'normale' },
    });
    expect(lance.etat.message).toBeNull();
  });

  it('le même taux ne change rien ; un taux hors de la liste est refusé', () => {
    const avant = enCours();
    expect(reduire(avant, { type: 'changer-taux', tauxIndex: INDEX_001 }, 'complet')).toEqual({ etat: avant, envoi: null });
    expect(() => reduire(avant, { type: 'changer-taux', tauxIndex: 99 }, 'complet')).toThrow(RangeError);
  });
});

describe('la vitesse', () => {
  it('envoyée seulement en cours ; retenue sinon pour le prochain lancement', () => {
    const depart = etatDeDepart(INITIAL, INDEX_001);
    const pret = reduire(depart, { type: 'vitesse', vitesse: 'rapide' }, 'complet');
    expect(pret.envoi).toBeNull();
    expect(pret.etat.vitesse).toBe('rapide');
    expect(reduire(pret.etat, { type: 'lancer' }, 'complet').envoi).toMatchObject({ reglages: { vitesse: 'rapide' } });

    const enCours = jouer(depart, [{ type: 'lancer' }]).etat;
    const change = reduire(enCours, { type: 'vitesse', vitesse: 'rapide' }, 'complet');
    expect(change.envoi).toEqual({ type: 'vitesse', generation: 1, vitesse: 'rapide' });
    expect(change.etat.vitesse).toBe('rapide');
    expect(reduire(change.etat, { type: 'vitesse', vitesse: 'rapide' }, 'complet')).toEqual({ etat: change.etat, envoi: null });
  });
});

describe('reduire est pur', () => {
  it('ne modifie jamais l’état reçu (gelé en profondeur), et rejoue à l’identique', () => {
    const suite: Evenement[] = [
      { type: 'vitesse', vitesse: 'rapide' },
      { type: 'lancer' },
      progres(1, 100, { validation: { pas: 100, perte: 3.2 }, echantillons: { pas: 100, prenoms: [] } }),
      { type: 'pause', raison: 'onglet' },
      etatW(1, 'en-pause'),
      { type: 'lancer' },
      { type: 'vitesse', vitesse: 'normale' },
      progres(1, 200),
      { type: 'changer-taux', tauxIndex: 0 },
      { type: 'lancer' },
      progres(2, 50),
      etatW(2, 'diverge'),
      { type: 'recommencer' },
      { type: 'lancer' },
      progres(3, 3000),
      etatW(3, 'termine'),
    ];
    const a = jouer(etatDeDepart(INITIAL, INDEX_001), suite);
    const b = jouer(etatDeDepart(INITIAL, INDEX_001), suite);
    expect(a).toEqual(b);
    expect(a.etat.phase).toBe('termine');
    expect(a.etat.generation).toBe(3);
  });
});

describe('les aides d’affichage', () => {
  it('actionPrincipale : le texte du bouton et son événement', () => {
    const depart = etatDeDepart(INITIAL, INDEX_001);
    const enCours = jouer(depart, [{ type: 'lancer' }]).etat;
    const enPause = jouer(enCours, [{ type: 'pause', raison: 'lecteur' }]).etat;
    const fini = jouer(enCours, [etatW(1, 'termine')]).etat;
    expect(actionPrincipale(depart)).toEqual({ texte: 'Lancer l’entraînement', evenement: { type: 'lancer' } });
    expect(actionPrincipale(enCours)).toEqual({ texte: 'Pause', evenement: { type: 'pause', raison: 'lecteur' } });
    expect(actionPrincipale(enPause)).toEqual({ texte: 'Reprendre', evenement: { type: 'lancer' } });
    expect(actionPrincipale(fini)).toEqual({ texte: 'Terminé', evenement: null });
    expect(actionPrincipale(jouer(enCours, [etatW(1, 'diverge')]).etat).evenement).toBeNull();
  });

  it('prenomAffiche : une capitale au début et après chaque trait d’union ; un prénom vide se voit', () => {
    expect(prenomAffiche('jean-pierre')).toBe('Jean-Pierre');
    expect(prenomAffiche('élodie')).toBe('Élodie');
    expect(prenomAffiche('ïa-ëlle')).toBe('Ïa-Ëlle');
    expect(prenomAffiche('a')).toBe('A');
    expect(prenomAffiche('')).toBe('(aucune lettre)');
  });
});

describe('ce que pilote.ts importe (rien de lourd dans la page)', () => {
  it('des valeurs de reglages.ts et nombres.ts seulement ; des types d’apercu.ts et de boucle-travailleur.ts', () => {
    const source = readFileSync(new URL('./pilote.ts', import.meta.url), 'utf8');
    expect(source, 'pas d’import dynamique ni de require').not.toMatch(/\bimport\s*\(|\brequire\s*\(/);
    // Les « import … from » et les « export … from » (une réexportation importe aussi).
    const liens = [...source.matchAll(/^(?:import|export)\s+(type\s+)?[^;]*?from\s+'([^']+)';/gms)];
    expect(liens.length).toBeGreaterThan(0);
    // Toutes les lignes qui commencent par « import » ou « export … from » sont bien lues par le motif.
    expect(liens).toHaveLength(source.match(/^import\s|^export\s[^;]*?\sfrom\s/gms)?.length ?? 0);
    const VALEURS = new Set(['./reglages', '../nombres', '../courbe']);
    const TYPES = new Set(['./apercu', './boucle-travailleur']);
    for (const [, estType, chemin] of liens) {
      if (estType) {
        expect(VALEURS.has(chemin) || TYPES.has(chemin), chemin).toBe(true);
      } else {
        expect(VALEURS.has(chemin), `pilote.ts importe des valeurs de ${chemin} : seulement ${[...VALEURS].join(', ')}`).toBe(true);
      }
    }
  });
});
