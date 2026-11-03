// Le Worker lui-même (travailleur.ts), avec le vrai entraîneur : self est
// simulé, et setTimeout est une fausse minuterie. L'horloge reste la vraie
// (performance.now) : les tranches durent vraiment 50 ms au plus.

import { afterEach, describe, expect, it, vi } from 'vitest';
import type { MessageDuTravailleur, MessageVersTravailleur } from './boucle-travailleur';
import { donneesParDefaut } from './donnees';
import { Entraineur, PRESETS_MINI } from './entrainement';

type Progres = Extract<MessageDuTravailleur, { type: 'progres' }>;

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.resetModules();
});

/** Charge travailleur.ts sur un faux self, et renvoie de quoi lui parler. */
async function demarrer() {
  const recus: MessageDuTravailleur[] = [];
  const portee: { onmessage: ((e: { data: MessageVersTravailleur }) => void) | null; postMessage(m: unknown): void } = {
    onmessage: null,
    postMessage: (m) => recus.push(structuredClone(m) as MessageDuTravailleur), // copié, comme un vrai postMessage
  };
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
  vi.stubGlobal('self', portee);
  await import('./travailleur');
  const envoyer = (data: MessageVersTravailleur): void => {
    if (portee.onmessage === null) throw new Error('travailleur.ts n’écoute pas self.onmessage');
    portee.onmessage({ data });
  };
  return { recus, envoyer };
}

describe('travailleur.ts', () => {
  it('l’avant-goût va au bout avec le vrai entraîneur, une seule tranche planifiée à la fois', { timeout: 60_000 }, async () => {
    const { recus, envoyer } = await demarrer();
    const r = PRESETS_MINI['avant-gout'];
    envoyer({ type: 'lancer', generation: 1, reglages: { preset: 'avant-gout', tauxMax: r.tauxMax, vitesse: 'rapide' } });
    // Des messages en rafale ne planifient pas plus d'une tranche.
    envoyer({ type: 'vitesse', generation: 1, vitesse: 'rapide' });
    envoyer({ type: 'vitesse', generation: 1, vitesse: 'rapide' });
    expect(vi.getTimerCount()).toBe(1);
    for (let i = 0; i < 10_000 && recus.at(-1)?.type !== 'etat'; i++) {
      expect(vi.getTimerCount()).toBeLessThanOrEqual(1);
      vi.runOnlyPendingTimers();
    }
    expect(recus.at(-1)).toEqual({ type: 'etat', generation: 1, etat: 'termine' });
    expect(vi.getTimerCount()).toBe(0); // fini : plus rien de planifié

    const progres = recus.filter((m): m is Progres => m.type === 'progres');
    const pertes = progres.flatMap((m) => m.pertes);
    expect(pertes).toHaveLength(r.pasTotal);
    expect(progres.at(-1)?.pas).toBe(r.pasTotal);
    expect(progres.flatMap((m) => (m.validation ? [m.validation.pas] : []))).toEqual([100, 200, 300, 400, 500, 600]);

    // Les mêmes nombres qu'un Entraineur du même préréglage, sans la boucle.
    const temoin = new Entraineur({ ...r });
    for (let p = 0; p < 100; p++) expect(pertes[p], `pas ${p + 1}`).toBe(temoin.faireUnPas());
    expect(progres.find((m) => m.validation?.pas === 100)?.validation?.perte).toBe(temoin.perteValidation());

    // « existe » vient de la liste des prénoms.
    const connus = donneesParDefaut().connus;
    const derniers = progres.at(-1)?.echantillons;
    expect(derniers?.pas).toBe(r.pasTotal);
    expect(derniers?.prenoms).toHaveLength(r.nbEchantillons);
    for (const p of derniers?.prenoms ?? []) expect(p.existe, p.texte).toBe(connus.has(p.texte));
    for (const m of progres) {
      expect(m.dureeMs).toBeGreaterThanOrEqual(0);
      expect(Number.isFinite(m.pasParSeconde)).toBe(true);
    }
  });

  it('pause : confirmée, et plus aucune tranche planifiée', { timeout: 60_000 }, async () => {
    const { recus, envoyer } = await demarrer();
    envoyer({ type: 'lancer', generation: 1, reglages: { preset: 'complet', tauxMax: 0.01, vitesse: 'rapide' } });
    vi.runOnlyPendingTimers(); // une tranche de 50 ms au plus
    envoyer({ type: 'pause', generation: 1 });
    expect(recus.at(-1)).toEqual({ type: 'etat', generation: 1, etat: 'en-pause' });
    vi.runOnlyPendingTimers(); // la tranche déjà planifiée ne fait rien
    expect(vi.getTimerCount()).toBe(0);
    expect(recus.at(-1)).toEqual({ type: 'etat', generation: 1, etat: 'en-pause' });
  });
});
