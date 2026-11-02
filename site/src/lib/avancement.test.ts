import { describe, expect, it } from 'vitest';
import { avancement } from './avancement';
import { noterAcquis } from './progression';

const CLE = 'forge-ia:progression:v1';
const ACQUIS = ['nombres', 'prediction', 'fusions', 'rare', 'zip'];

// Faux stockage en mémoire, avec la même interface que localStorage.
function fauxStockage(): Storage {
  const donnees = new Map<string, string>();
  return {
    get length() {
      return donnees.size;
    },
    clear: () => donnees.clear(),
    getItem: (cle: string) => donnees.get(cle) ?? null,
    key: (i: number) => [...donnees.keys()][i] ?? null,
    removeItem: (cle: string) => void donnees.delete(cle),
    setItem: (cle: string, valeur: string) => void donnees.set(cle, String(valeur)),
  };
}

describe('avancement', () => {
  it('dit « disponible » sans aucun acquis gagné', () => {
    expect(avancement('1.3', ACQUIS, fauxStockage())).toEqual({ gagnes: 0, total: 5, etat: 'disponible' });
  });

  it('dit « commencé » avec une partie des acquis', () => {
    const s = fauxStockage();
    noterAcquis('1.3', 'nombres', s);
    noterAcquis('1.3', 'zip', s);
    expect(avancement('1.3', ACQUIS, s)).toEqual({ gagnes: 2, total: 5, etat: 'commence' });
  });

  it('dit « fait » quand tous les acquis sont gagnés', () => {
    const s = fauxStockage();
    for (const cle of ACQUIS) noterAcquis('1.3', cle, s);
    expect(avancement('1.3', ACQUIS, s)).toEqual({ gagnes: 5, total: 5, etat: 'fait' });
  });

  it('ignore un acquis gardé qui n’existe plus dans le chapitre', () => {
    const s = fauxStockage();
    noterAcquis('1.3', 'ancien', s);
    noterAcquis('1.3', 'nombres', s);
    expect(avancement('1.3', ACQUIS, s)).toEqual({ gagnes: 1, total: 5, etat: 'commence' });
  });

  it('ne compte que les acquis du bon chapitre', () => {
    const s = fauxStockage();
    for (const cle of ACQUIS) noterAcquis('essai', cle, s);
    expect(avancement('1.3', ACQUIS, s).etat).toBe('disponible');
  });

  it('ne dit jamais « fait » pour un chapitre sans acquis', () => {
    expect(avancement('1.3', [], fauxStockage())).toEqual({ gagnes: 0, total: 0, etat: 'disponible' });
  });

  it('reste sans erreur avec une progression abîmée ou un stockage absent', () => {
    const s = fauxStockage();
    s.setItem(CLE, '{pas du json');
    expect(avancement('1.3', ACQUIS, s).etat).toBe('disponible');
    expect(avancement('1.3', ACQUIS, null).etat).toBe('disponible');
  });
});
