// Le lecteur des rapports d'étape (etapes.ts) : un rapport fabriqué est lu, une mesure absente est rendue
// telle quelle, un fichier faux est refusé avec un message qui dit quel relevé refaire, et un fichier qui
// manque donne null (la page pose alors data-a-mesurer).

import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { afterAll, describe, expect, it } from 'vitest';
import {
  celluleDeMesure,
  estAbsente,
  FICHIERS_ETAPES,
  LIGNES_DES_MESURES,
  lireRapportEtape,
  lireSeries,
  MESURES_DE_L_ETAPE,
  nomDeVersion,
  refaire,
  verifierRapportEtape,
} from './etapes';
import type { Mesure, RapportEtape } from './etapes';

/** Les mesures d'une étape, fabriquées : des nombres partout, sauf `absente` pour les mesures dont les données manquent. */
function mesuresDe(etape: keyof typeof MESURES_DE_L_ETAPE, absentes: string[] = []): RapportEtape['mesures'] {
  return Object.fromEntries(
    MESURES_DE_L_ETAPE[etape].map((nom): [string, Mesure] => [
      nom,
      absentes.includes(nom)
        ? { absente: 'les problèmes traduits ne sont pas téléchargés' }
        : { exactitude: 0.25, n: 400, par_famille: { addition: { exactitude: 0.5, n: 100 } } },
    ]),
  );
}

function rapport(etape: keyof typeof MESURES_DE_L_ETAPE = '1.9', absentes: string[] = []): RapportEtape {
  return {
    version: 'ton-ia-1.9',
    etape,
    releve_le: '2026-12-01',
    mesures: mesuresDe(etape, absentes),
    echantillons: [
      { invite: 'Dis bonjour.', texte: 'Bonjour !', pensee: null, terminee: true },
      { invite: 'Combien font 2 + 2 ?', texte: '4' },
    ],
  };
}

function abime(abimer: (r: any) => void): unknown {
  const r = JSON.parse(JSON.stringify(rapport()));
  abimer(r);
  return r;
}

describe('FICHIERS_ETAPES', () => {
  it('range chaque rapport dans le projet de son étape, sous le nom « version@étape »', () => {
    expect(FICHIERS_ETAPES['1.5@1.7']).toBe('projets/1.7-conversation/mesures/etape-ton-ia-1.5.json');
    expect(FICHIERS_ETAPES['1.7-court@1.7']).toBe('projets/1.7-conversation/mesures/etape-ton-ia-1.7-court.json');
    expect(FICHIERS_ETAPES['1.8-court@1.8']).toBe('projets/1.8-alignement/mesures/etape-ton-ia-1.8-court.json');
    expect(FICHIERS_ETAPES['1.5@1.9']).toBe('projets/1.9-raisonnement/mesures/etape-ton-ia-1.5.json');
    // L'étape 1.10 est dans le projet 1.10, pas dans le projet 1.1 : « 1.10 » n'est pas pris pour « 1.1 » plus un zéro.
    expect(FICHIERS_ETAPES['1.10@1.10']).toBe('projets/1.10-code/mesures/etape-ton-ia-1.10.json');
    expect(FICHIERS_ETAPES['1.5@1.10']).toBe('projets/1.10-code/mesures/etape-ton-ia-1.5.json');
    for (const [nom, fichier] of Object.entries(FICHIERS_ETAPES)) {
      const etape = nom.slice(nom.indexOf('@') + 1);
      expect(fichier, nom).toMatch(new RegExp(`^projets/${etape.replace('.', '\\.')}-[a-z-]+/mesures/etape-ton-ia-[0-9.]+(-court)?\\.json$`));
    }
  });

  it('chaque étape a ses mesures, sans echantillons (rangés à part)', () => {
    expect(Object.keys(MESURES_DE_L_ETAPE)).toEqual(['1.7', '1.8', '1.9', '1.10']);
    for (const mesures of Object.values(MESURES_DE_L_ETAPE)) expect(mesures).not.toContain('echantillons');
  });
});

describe('les mesures de chaque étape sont celles de forge', () => {
  /** Le tableau MESURES_PAR_ETAPE de forge (etape.py) : étape vers noms de mesures, sans les échantillons. */
  function mesuresDeForge(): Record<string, string[]> {
    const source = readFileSync('../projets/forge/forge/evaluation/etape.py', 'utf8');
    const de17 = /_MESURES_DE_1_7 = \(([^)]*)\)/.exec(source);
    const tableau = /MESURES_PAR_ETAPE: [^=]*= \{([\s\S]*?)\n\}/.exec(source);
    if (de17 === null || tableau === null) throw new Error('MESURES_PAR_ETAPE n’est plus où ce test le cherche (etape.py) : revois-le.');
    const noms = (liste: string): string[] => [...liste.matchAll(/"([a-z_0-9]+)"/g)].map((m) => m[1]);
    const resultat: Record<string, string[]> = {};
    // Chaque étape est « _MESURES_DE_1_7 » seul, ou un tuple qui peut le déplier (« *_MESURES_DE_1_7 »).
    for (const [, etape, liste] of tableau[1].matchAll(/"([0-9.]+)": (_MESURES_DE_1_7|\([^)]*\))/g)) {
      const reprend = liste === '_MESURES_DE_1_7' || liste.includes('*_MESURES_DE_1_7');
      resultat[etape] = [...(reprend ? noms(de17[1]) : []), ...(liste === '_MESURES_DE_1_7' ? [] : noms(liste))].filter((nom) => nom !== 'echantillons');
    }
    return resultat;
  }

  it('1.7, 1.8 et 1.9 : mêmes mesures que forge, dans le même ordre (« victoire » est celle de 1.8)', () => {
    const forge = mesuresDeForge();
    for (const etape of ['1.7', '1.8', '1.9'] as const) {
      expect(forge[etape], `forge n'a pas l'étape ${etape}`).toBeDefined();
      expect(MESURES_DE_L_ETAPE[etape], etape).toStrictEqual(forge[etape]);
    }
    expect(forge['1.8']).toContain('victoire');
  });

  it('1.10 : dès que forge a l’étape (tâche 21 du plan 7), ses mesures sont celles d’ici', () => {
    const forge = mesuresDeForge();
    // Les clés attendues par le plan 7 : humaneval, humaneval_fr et fim_ligne s'ajoutent à celles de 1.9 sans mgsm.
    expect(MESURES_DE_L_ETAPE['1.10']).toStrictEqual(['ifeval_fr', 'tenue', 'oubli', 'problemes', 'humaneval', 'humaneval_fr', 'fim_ligne']);
    if (forge['1.10'] !== undefined) expect(MESURES_DE_L_ETAPE['1.10']).toStrictEqual(forge['1.10']);
  });
});

describe('refaire : la commande du projet qui écrit le relevé', () => {
  it('cite le paquet de 1.8 pour un fichier de 1.8, et celui de 1.7 pour un fichier de 1.7', () => {
    expect(refaire(FICHIERS_ETAPES['1.8@1.8'])).toBe(
      'Relance le relevé, depuis projets/1.8-alignement, avec « uv run --extra cpu python -m alignement_pas_a_pas resumer --rapport <rapport.json> --json mesures/etape-ton-ia-1.8.json », ou corrige le fichier.',
    );
    expect(refaire(FICHIERS_ETAPES['1.8-court@1.8'])).toContain('--json mesures/etape-ton-ia-1.8-court.json');
    expect(refaire(FICHIERS_ETAPES['1.7@1.7'])).toContain('python -m conversation_pas_a_pas resumer');
    expect(refaire(FICHIERS_ETAPES['1.5@1.7'])).toContain('resumer --rapport <rapport.json> --reference --json mesures/etape-ton-ia-1.5.json');
    expect(refaire(FICHIERS_ETAPES['1.8@1.8'])).not.toContain('conversation_pas_a_pas');
  });

  it('dit « courbes », « paires » ou « balayage » pour les autres relevés de 1.8', () => {
    expect(refaire('projets/1.8-alignement/mesures/entrainement-dpo-1.8.json')).toContain('alignement_pas_a_pas courbes --journal <journal.jsonl> --json mesures/entrainement-dpo-1.8.json');
    expect(refaire('projets/1.8-alignement/mesures/paires-exemples.json')).toContain('alignement_pas_a_pas paires --jeu');
    expect(refaire('projets/1.8-alignement/mesures/balayage-1.8.json')).toContain('alignement_pas_a_pas balayage');
  });

  it('garde le message général pour un projet qui n’a pas encore son paquet', () => {
    expect(refaire(FICHIERS_ETAPES['1.9@1.9'])).toContain('python -m <paquet du projet> resumer');
    expect(refaire('projets/essai.json')).toContain('python -m <paquet du projet> resumer');
  });

  it('est le message d’une erreur de lecture, avec la commande du bon projet', () => {
    const faux = { version: ' ', etape: '1.8', releve_le: '2026-12-01', mesures: {}, echantillons: [] };
    expect(() => verifierRapportEtape(faux, FICHIERS_ETAPES['1.8@1.8'])).toThrow(/version est vide.*alignement_pas_a_pas resumer/s);
  });
});

describe('verifierRapportEtape', () => {
  it('rend tel quel un rapport valide, pour chaque étape', () => {
    for (const etape of ['1.7', '1.8', '1.9', '1.10'] as const) {
      const r = rapport(etape);
      expect(verifierRapportEtape(r, 'x.json')).toBe(r);
    }
  });

  it('rend une mesure absente telle quelle, avec sa raison', () => {
    const r = verifierRapportEtape(rapport('1.9', ['mgsm_fr']), 'x.json');
    const m = r.mesures.mgsm_fr;
    expect(estAbsente(m)).toBe(true);
    expect(m).toStrictEqual({ absente: 'les problèmes traduits ne sont pas téléchargés' });
    expect(estAbsente(r.mesures.ifeval_fr)).toBe(false);
  });

  it('refuse un fichier faux, en nommant le fichier et le champ, et en disant quel relevé refaire', () => {
    const fautes: [string, unknown, RegExp][] = [
      ['pas un objet', [], /pas un objet JSON/],
      ['version vide', abime((r) => (r.version = ' ')), /version est vide/],
      ['étape inconnue', abime((r) => (r.etape = '1.11')), /etape doit être l’une de 1\.7, 1\.8, 1\.9, 1\.10/],
      ['date fausse', abime((r) => (r.releve_le = '1/12/2026')), /releve_le doit être une date/],
      ['mesures manque', abime((r) => delete r.mesures), /mesures manque/],
      ['mesure manquante', abime((r) => delete r.mesures.oubli), /mesures\.oubli manque/],
      ['mesure d’une autre étape', abime((r) => (r.mesures.humaneval = { n: 1 })), /mesures\.humaneval n’est pas une mesure de l’étape 1\.9/],
      ['nombre qui n’en est pas un', abime((r) => (r.mesures.tenue.fr = '0,5')), /mesures\.tenue\.fr doit être un nombre fini/],
      ['nombre imbriqué faux', abime((r) => (r.mesures.problemes.par_famille.addition.n = null)), /mesures\.problemes\.par_famille\.addition\.n/],
      ['absente sans raison', abime((r) => (r.mesures.oubli = { absente: '' })), /une mesure absente s’écrit/],
      ['absente avec autre chose', abime((r) => (r.mesures.oubli = { absente: 'x', n: 1 })), /une mesure absente s’écrit/],
      ['échantillons absents', abime((r) => delete r.echantillons), /echantillons doit être une liste/],
      ['échantillon sans texte', abime((r) => delete r.echantillons[1].texte), /echantillons\[1\]/],
    ];
    for (const [quoi, valeur, motif] of fautes) {
      expect(() => verifierRapportEtape(valeur, 'projets/1.9-raisonnement/mesures/etape-ton-ia-1.9.json'), quoi).toThrow(motif);
    }
    expect(() => verifierRapportEtape([], 'projets/essai.json')).toThrow(/projets\/essai\.json.*python -m <paquet du projet> resumer/s);
  });
});

describe('lireRapportEtape et lireSeries', () => {
  const dossiers: string[] = [];
  afterAll(() => dossiers.forEach((d) => rmSync(d, { recursive: true, force: true })));

  /** Un dépôt fabriqué, avec ses fichiers (chemin depuis la racine vers contenu). */
  function depot(fichiers: Record<string, string> = {}): string {
    const racine = mkdtempSync(join(tmpdir(), 'etapes-'));
    dossiers.push(racine);
    mkdirSync(join(racine, 'projets/1.5-pre-entrainement'), { recursive: true });
    for (const [chemin, contenu] of Object.entries(fichiers)) {
      mkdirSync(dirname(join(racine, chemin)), { recursive: true });
      writeFileSync(join(racine, chemin), contenu);
    }
    return racine;
  }

  it('rend null quand le fichier manque : la page pose data-a-mesurer', () => {
    expect(lireRapportEtape('1.9@1.9', depot())).toBeNull();
    expect(lireSeries('projets/1.8-alignement/mesures/entrainement-dpo-1.8.json', depot())).toBeNull();
  });

  it('lit un rapport fabriqué, par un chemin ou par une URL file:', () => {
    const racine = depot({ [FICHIERS_ETAPES['1.10@1.10']]: JSON.stringify(rapport('1.10', ['fim_ligne'])) });
    const lu = lireRapportEtape('1.10@1.10', racine);
    expect(lu).toStrictEqual(rapport('1.10', ['fim_ligne']));
    expect(estAbsente(lu!.mesures.fim_ligne)).toBe(true);
    expect(lireRapportEtape('1.10@1.10', new URL(`file:///${racine.replace(/\\/g, '/')}/`))).toStrictEqual(lu);
  });

  it('refuse un JSON illisible et un fichier faux, en nommant le fichier', () => {
    const nom = FICHIERS_ETAPES['1.9@1.9'];
    expect(() => lireRapportEtape('1.9@1.9', depot({ [nom]: '{' }))).toThrow(/etape-ton-ia-1\.9\.json.*JSON illisible/s);
    expect(() => lireRapportEtape('1.9@1.9', depot({ [nom]: '{"version": "x"}' }))).toThrow(/etape-ton-ia-1\.9\.json/);
  });

  it('refuse le rapport d’une autre étape que celle du nom', () => {
    const racine = depot({ [FICHIERS_ETAPES['1.9@1.9']]: JSON.stringify(rapport('1.7')) });
    expect(() => lireRapportEtape('1.9@1.9', racine)).toThrow(/rapport est celui de l’étape 1\.7.*attend l’étape 1\.9/s);
  });

  it('refuse une racine qui n’est pas celle du dépôt, au lieu de dire « à mesurer »', () => {
    expect(() => lireRapportEtape('1.7@1.7', tmpdir())).toThrow(/n’a pas de dossier projets\/1\.5-pre-entrainement/);
    expect(() => lireSeries('x.json', tmpdir())).toThrow(/n’a pas de dossier projets\/1\.5-pre-entrainement/);
  });

  it('lit les séries d’un fichier de courbes, et laisse de côté ce qui n’en est pas une', () => {
    const fichier = 'projets/1.9-raisonnement/mesures/entrainement-grpo-1.9.json';
    const series = {
      recompense_moyenne: [[1, 0.25], [2, 0.5]],
      groupes_sans_signal: [[1, 0.8], [2, 0.7]],
      lance: true,
    };
    expect(lireSeries(fichier, depot({ [fichier]: JSON.stringify(series) }))).toStrictEqual({
      recompense_moyenne: [[1, 0.25], [2, 0.5]],
      groupes_sans_signal: [[1, 0.8], [2, 0.7]],
    });
    // Un RL qui n'a pas été lancé : aucune série, et ce n'est pas une erreur.
    expect(lireSeries(fichier, depot({ [fichier]: '{"lance": false}' }))).toStrictEqual({});
  });

  it('refuse une série dont un point est faux', () => {
    const fichier = 'projets/1.8-alignement/mesures/entrainement-dpo-1.8.json';
    for (const mauvais of [[[1, null]], [[2, 1], [1, 1]], [[1]], [['1', 2]]]) {
      expect(() => lireSeries(fichier, depot({ [fichier]: JSON.stringify({ logps_choisie: mauvais }) }))).toThrow(
        /entrainement-dpo-1\.8\.json.*logps_choisie\[\d\] doit être \[pas, valeur\]/s,
      );
    }
  });
});

// Ce que TableauEtape.astro montre de chaque mesure (chapitres 1.7 à 1.10) : un nombre lisible, et « à
// mesurer » pour un rapport qui manque ou une mesure absente.
describe('les lignes du tableau d’une étape', () => {
  const FINE = '\u202F';
  const r: RapportEtape = {
    version: 'ton-ia-1.7',
    etape: '1.7',
    releve_le: '2026-11-20',
    mesures: {
      perte_conversation: { perte: 1.2345, n: 64 },
      ifeval_fr: { invite_stricte: 0.2170212765957447, consigne_stricte: 0.3130434782608696, n: 235 },
      tenue: { terminee: 0, fr: 0.9276595744680851, autre: 0, indetermine: 0.07, mots_moyens: 347.06, n: 235 },
      oubli: { absente: 'pas de jetons de validation' },
    },
    echantillons: [],
  };

  it('chaque mesure de l’étape 1.7 a sa ligne : un libellé, une précision, et sa valeur mise en forme', () => {
    for (const nom of MESURES_DE_L_ETAPE['1.7']) {
      expect(LIGNES_DES_MESURES[nom], nom).toBeDefined();
      expect(LIGNES_DES_MESURES[nom].libelle.length).toBeGreaterThan(3);
    }
    expect(celluleDeMesure(r, 'perte_conversation')).toStrictEqual({ valeur: '1,235', detail: `sur 64 rangées` });
    expect(celluleDeMesure(r, 'ifeval_fr')).toStrictEqual({ valeur: `21,7${FINE}%`, detail: `consignes${FINE}: 31,3${FINE}%` });
    expect(celluleDeMesure(r, 'tenue')).toStrictEqual({ valeur: `0,0${FINE}%`, detail: `sur 235 réponses` });
  });

  it('un rapport qui manque, ou une mesure absente : null, la page pose « à mesurer »', () => {
    expect(celluleDeMesure(null, 'ifeval_fr')).toBeNull();
    expect(celluleDeMesure(r, 'oubli')).toBeNull();
    expect(() => celluleDeMesure(r, 'victoire')).toThrow(/victoire.*LIGNES_DES_MESURES/s);
  });

  it('le nom de chaque version, en tête de colonne', () => {
    expect(nomDeVersion('1.5@1.7')).toBe('Ton IA 1.5');
    expect(nomDeVersion('1.7@1.7')).toBe('Ton IA 1.7');
    expect(nomDeVersion('1.7-court@1.7')).toBe('Version courte');
    expect(nomDeVersion('1.10@1.10')).toBe('Ton IA 1.10');
  });
});
