// Le lecteur des relevés d'entraînement (journal.ts) : le format est vérifié champ par champ, un
// fichier absent donne null, et le relevé de la version d'une heure dit ce que dit
// docs/mesures/ton-ia-mini.md.

import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterAll, describe, expect, it } from 'vitest';
import { taillePaquet } from '../courbe';
import { FICHIERS_ENTRAINEMENT, lireEntrainement, verifierEntrainement } from './journal';
import type { Entrainement } from './journal';

// Vitest est lancé depuis site/ : le dépôt est un dossier plus haut.
const RACINE = '..';

/** Un relevé valide : deux sessions (une pause, puis la fin) de 10 pas. */
function releve(): Entrainement {
  return {
    nom: 'ton-ia-essai',
    releve_le: '2026-11-09',
    resume: {
      parametres: 2_000_000,
      pas_total: 10,
      pas_faits: 10,
      jetons_vus: 10240,
      secondes_de_calcul: 5.1,
      pauses: 1,
      debit_moyen: 2007.8,
      perte_finale: 9.2,
      validation_finale: 9.1,
      perte_premier_pas: 10.4,
      perte_dernier_pas: 8.6,
    },
    sessions: [
      { depart: 'debut', premier_pas: 1, dernier_pas: 5, secondes: 2.5, fin: 'pause' },
      { depart: 'reprise', premier_pas: 6, dernier_pas: 10, secondes: 2.6, fin: 'fin' },
    ],
    courbe: {
      taille_paquet: 1,
      pertes: [
        [1, 10.4],
        [2, 10.3],
        [3, null],
      ],
      validations: [[5, 10.0]],
      hasard: Math.log(32768),
    },
  };
}

/** Un relevé valide, copié, puis abîmé par `abimer`. */
function abime(abimer: (r: any) => void): unknown {
  const r = JSON.parse(JSON.stringify(releve()));
  abimer(r);
  return r;
}

describe('verifierEntrainement', () => {
  it('rend tel quel un relevé valide', () => {
    const r = releve();
    expect(verifierEntrainement(r, 'essai.json')).toBe(r);
  });

  it('accepte une session plantée avant son premier pas', () => {
    const r = releve();
    r.sessions.splice(1, 0, { depart: 'reprise', premier_pas: null, dernier_pas: null, secondes: 0, fin: 'coupée' });
    expect(() => verifierEntrainement(r, 'essai.json')).not.toThrow();
  });

  it('refuse ce qui n’est pas un objet', () => {
    expect(() => verifierEntrainement([], 'projets/essai.json')).toThrow(/projets\/essai\.json.*ce n’est pas un objet JSON/s);
  });

  const refus: [string, (r: any) => void, RegExp][] = [
    ['un nom vide', (r) => (r.nom = ' '), /nom est vide/],
    ['sans date', (r) => (r.releve_le = '9 novembre'), /releve_le doit être une date AAAA-MM-JJ/],
    ['un nombre du résumé manquant', (r) => delete r.resume.debit_moyen, /resume\.debit_moyen doit être un nombre/],
    ['un nombre du résumé non fini', (r) => (r.resume.perte_finale = null), /resume\.perte_finale doit être un nombre/],
    ['des pas faits non entiers', (r) => (r.resume.pas_faits = 9.5), /resume\.pas_faits doit être un entier/],
    ['un journal vide', (r) => (r.resume.pas_faits = 0), /resume\.pas_faits vaut 0/],
    ['plus de pas faits que prévus', (r) => (r.resume.pas_total = 8), /dépasse resume\.pas_total/],
    ['aucune session', (r) => (r.sessions = []), /sessions est vide/],
    ['une fin inconnue', (r) => (r.sessions[0].fin = 'arrêtée'), /la session 1 n’a pas le format attendu/],
    ['des sessions qui se chevauchent', (r) => (r.sessions[1].premier_pas = 5), /commence au pas 5, avant la fin de la précédente/],
    ['une session qui finit avant de commencer', (r) => (r.sessions[0].dernier_pas = 0), /la session 1 n’a pas le format/],
    ['une reprise en première session', (r) => (r.sessions[0].depart = 'reprise'), /seule la première session part de « debut »/],
    ['deux débuts', (r) => (r.sessions[1].depart = 'debut'), /seule la première session part de « debut »/],
    ['une dernière session qui ne finit pas aux pas faits', (r) => (r.sessions[1].dernier_pas = 9), /finit au pas 9/],
    ['un nombre de pauses faux', (r) => (r.resume.pauses = 2), /1 session\(s\) finissent en pause/],
    ['des secondes qui ne s’additionnent pas', (r) => (r.sessions[1].secondes = 9), /les sessions font 11\.500 s/],
    ['une courbe sans paquet', (r) => (r.courbe.taille_paquet = 0), /courbe\.taille_paquet/],
    ['un hasard nul', (r) => (r.courbe.hasard = 0), /courbe\.hasard/],
    ['une courbe vide', (r) => (r.courbe.pertes = []), /courbe\.pertes est vide/],
    ['des pas qui reculent', (r) => (r.courbe.pertes[1][0] = 0.5), /courbe\.pertes\[1\] doit être \[pas, perte\]/],
    ['une validation négative', (r) => (r.courbe.validations[0][1] = -1), /courbe\.validations\[0\]/],
  ];
  it.each(refus)('refuse %s, en nommant le fichier et la commande à relancer', (_nom, abimer, attendu) => {
    const valeur = abime(abimer);
    expect(() => verifierEntrainement(valeur, 'projets/essai.json')).toThrow(attendu);
    expect(() => verifierEntrainement(valeur, 'projets/essai.json')).toThrow(/projets\/essai\.json/);
    expect(() => verifierEntrainement(valeur, 'projets/essai.json')).toThrow(/python -m pre_entrainement courbe/);
  });
});

describe('lireEntrainement', () => {
  const dossiers: string[] = [];
  afterAll(() => dossiers.forEach((d) => rmSync(d, { recursive: true, force: true })));

  function depot(contenu: string | null): string {
    const racine = mkdtempSync(join(tmpdir(), 'journal-'));
    dossiers.push(racine);
    mkdirSync(join(racine, 'projets/1.5-pre-entrainement/mesures'), { recursive: true });
    if (contenu !== null) writeFileSync(join(racine, FICHIERS_ENTRAINEMENT['ton-ia-1.5']), contenu);
    return racine;
  }

  it('rend null quand le fichier manque : la page pose data-a-mesurer', () => {
    expect(lireEntrainement('ton-ia-1.5', depot(null))).toBeNull();
  });

  it('lit un relevé valide, par un chemin ou par une URL file:', () => {
    const racine = depot(JSON.stringify(releve()));
    expect(lireEntrainement('ton-ia-1.5', racine)).toStrictEqual(releve());
    expect(lireEntrainement('ton-ia-1.5', new URL(`file:///${racine.replace(/\\/g, '/')}/`))).toStrictEqual(releve());
  });

  it('refuse un JSON illisible, en nommant le fichier', () => {
    expect(() => lireEntrainement('ton-ia-1.5', depot('{'))).toThrow(/ton-ia-1\.5\.json.*JSON illisible/s);
  });

  it('refuse une racine qui n’est pas celle du dépôt, au lieu de dire « à mesurer »', () => {
    expect(() => lireEntrainement('ton-ia-1.5', tmpdir())).toThrow(/n’a pas de dossier projets\/1\.5-pre-entrainement/);
  });

  it('refuse un relevé qui a le mauvais format', () => {
    expect(() => lireEntrainement('ton-ia-1.5', depot('{"nom": "x"}'))).toThrow(/ton-ia-1\.5\.json/);
  });
});

describe('le relevé de la version d’une heure (ton-ia-mini)', () => {
  const mini = lireEntrainement('ton-ia-mini', RACINE);

  it('existe, et passe la vérification', () => {
    expect(mini).not.toBeNull();
    expect(mini!.nom).toBe('ton-ia-mini');
  });

  it('dit ce que dit docs/mesures/ton-ia-mini.md', () => {
    const r = mini!.resume;
    // 6 370 pas de 131 072 jetons, 23 204 736 paramètres, 60 min 17 s de boucle (3 617,3 s), sans pause.
    expect(r.pas_total).toBe(6370);
    expect(r.pas_faits).toBe(6370);
    expect(r.jetons_vus).toBe(834928640);
    expect(r.parametres).toBe(23204736);
    expect(r.pauses).toBe(0);
    expect(Math.round(r.secondes_de_calcul)).toBe(3617);
    expect(Math.round(r.debit_moyen)).toBe(230815);
    expect(mini!.sessions).toHaveLength(1);
    expect(mini!.sessions[0]).toMatchObject({ depart: 'debut', premier_pas: 1, dernier_pas: 6370, fin: 'fin' });
    expect(r.perte_premier_pas.toFixed(3)).toBe('10.477');
    expect(r.validation_finale.toFixed(3)).toBe('3.455');
  });

  it('a le découpage du site : taillePaquet(pas_total, 600)', () => {
    const c = mini!.courbe;
    expect(c.taille_paquet).toBe(taillePaquet(mini!.resume.pas_total, 600));
    expect(c.pertes.length).toBe(Math.ceil(mini!.resume.pas_faits / c.taille_paquet));
    expect(c.pertes.length).toBeLessThanOrEqual(600);
    expect(c.validations).toHaveLength(64);
    expect(c.hasard).toBe(Math.log(32768));
  });
});
