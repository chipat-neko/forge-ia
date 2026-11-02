import { get } from 'svelte/store';
import { describe, expect, it } from 'vitest';
import { canal, ouverture } from './canal';

describe('canal', () => {
  it('renvoie la même instance pour le même nom, la première valeur initiale gagne', () => {
    expect(canal('x', 1)).toBe(canal('x', 2));
    expect(canal('x', 2).get()).toBe(1);
  });

  it('renvoie des instances différentes pour des noms différents', () => {
    expect(canal('a1', 0)).not.toBe(canal('a2', 0));
  });

  it("appelle les abonnés tout de suite puis à chaque changement, jusqu'au désabonnement", () => {
    const vus: number[] = [];
    const stop = canal('y', 0).subscribe((v) => vus.push(v));
    canal('y', 0).set(5);
    stop();
    canal('y', 0).set(6);
    expect(vus).toEqual([0, 5]);
  });

  it('get rend la dernière valeur posée', () => {
    const c = canal('z', 'a');
    c.set('b');
    expect(c.get()).toBe('b');
    expect(canal('z', 'autre').get()).toBe('b');
  });

  it('ne prévient pas les abonnés quand une valeur simple ne change pas', () => {
    const vus: number[] = [];
    const c = canal('mm', 1);
    c.subscribe((v) => vus.push(v));
    c.set(1);
    c.set(2);
    c.set(2);
    expect(vus).toEqual([1, 2]);
  });

  it("prévient les abonnés quand on repose un objet (il a pu être modifié)", () => {
    const objet = { n: 0 };
    const c = canal('obj', objet);
    const vus: number[] = [];
    c.subscribe((v) => vus.push(v.n));
    objet.n = 1;
    c.set(objet);
    expect(vus).toEqual([0, 1]);
  });

  it("prévient tous les abonnés, même celui qui se désabonne pendant l'envoi", () => {
    const c = canal('multi', 0);
    const a: number[] = [];
    const b: number[] = [];
    const stopA = c.subscribe((v) => {
      a.push(v);
      if (v === 1) stopA();
    });
    c.subscribe((v) => b.push(v));
    c.set(1);
    c.set(2);
    expect(a).toEqual([0, 1]);
    expect(b).toEqual([0, 1, 2]);
  });

  it('compte deux abonnements de la même fonction comme deux abonnements', () => {
    const c = canal('doublon', 0);
    const vus: number[] = [];
    const fn = (v: number) => vus.push(v);
    const stop1 = c.subscribe(fn);
    c.subscribe(fn);
    stop1();
    c.set(3);
    expect(vus).toEqual([0, 0, 3]);
  });

  it('respecte le contrat des magasins Svelte', () => {
    const c = canal('svelte', 10);
    expect(get(c)).toBe(10);
    c.set(11);
    expect(get(c)).toBe(11);
  });
});

describe('ouverture', () => {
  it('vaut faux au départ', () => {
    expect(ouverture('atelier').get()).toBe(false);
  });

  it('est le canal « ouvert:nom »', () => {
    expect(ouverture('demo')).toBe(canal('ouvert:demo', false));
    ouverture('demo').set(true);
    expect(canal('ouvert:demo', false).get()).toBe(true);
  });

  it('garde un état par nom', () => {
    ouverture('un').set(true);
    expect(ouverture('deux').get()).toBe(false);
  });
});
