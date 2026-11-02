import { describe, expect, it } from 'vitest';

// Les tests des tâches suivantes comptent sur cette valeur pour construire
// des liens : elle doit être celle de la base d'Astro, pas la valeur par
// défaut de Vite (« / »).
describe('base du site dans Vitest', () => {
  it('commence par /forge-ia', () => {
    expect(import.meta.env.BASE_URL.startsWith('/forge-ia')).toBe(true);
  });

  it('se termine par une barre oblique, comme dans le site construit', () => {
    expect(import.meta.env.BASE_URL.endsWith('/')).toBe(true);
  });
});
