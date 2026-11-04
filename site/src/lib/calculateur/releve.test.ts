// Le relevé du calculateur : les nombres et les phrases que le composant
// affiche, calculés par les formules, sur les données relevées. Les attendus
// écrits en toutes lettres sont ceux du plan ; les autres sont recalculés par
// les formules (rien n'est recopié deux fois).

import { describe, expect, it } from 'vitest';
import { pourcent } from '../nombres';
import { fourchettePrix, MATERIELS, materiel } from './donnees';
import { formaterDuree, formaterPuissanceDeDix, formaterQuantite } from './formats';
import { dureeSecondes, efficaciteMesuree, operationsEntrainement } from './formules';
import {
  annonce,
  calculerReleve,
  CARTES_PROPOSEES,
  formulesDuCalcul,
  fourchette,
  GROUPES_MATERIELS,
  GROUPES_MODELES,
  JETONS_DU_CACHE,
  JETONS_PAR_PARAMETRE_PROPOSES,
  lignesReperes,
  MODELES_DU_CALCULATEUR,
  modeleDuCalculateur,
  phraseCommeLesGrands,
  phraseRepere,
  reglageDeDepart,
  texteCalcul,
  texteDuree,
  texteElectricite,
  texteGeneration,
  texteJetons,
  texteLocation,
  texteMemoire,
  texteService,
  type Reglage,
  type Releve,
} from './releve';
import { PRESETS_FORGE } from './ton-ia';

const FINE = '\u202F';
const INSECABLE = '\u00A0';
/** Les espaces insécables ramenées à des espaces ordinaires, pour comparer au texte du plan. */
const n = (t: string | null) => (t ?? '').replace(/\u00A0/g, ' ');
const N = PRESETS_FORGE.tres_grand.parametres;
const INTERDIT = /NaN|Infinity|undefined|null|e\+|e-\d/;

const releve = (r: Partial<Reglage> = {}): Releve => calculerReleve({ ...reglageDeDepart(), ...r });

/** Tous les textes d'un relevé, ceux du « Voir le calcul » compris. */
function textes(rel: Releve): string[] {
  return [
    texteJetons(rel),
    texteCalcul(rel),
    texteDuree(rel),
    texteMemoire(rel),
    texteService(rel),
    texteGeneration(rel) ?? '',
    texteElectricite(rel) ?? '',
    texteLocation(rel),
    phraseRepere(rel) ?? '',
    phraseCommeLesGrands(rel),
    annonce(rel),
    ...formulesDuCalcul(rel).flatMap((f) => [f.titre, f.formule, f.explication]),
  ];
}

describe('les réglages proposés', () => {
  it('les jetons par paramètre, les cartes (1 à 16 384) et les bornes de l’efficacité', () => {
    expect(JETONS_PAR_PARAMETRE_PROPOSES).toEqual([1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000]);
    expect(CARTES_PROPOSEES).toHaveLength(15);
    expect(CARTES_PROPOSEES[0]).toBe(1);
    expect(CARTES_PROPOSEES.at(-1)).toBe(16_384);
    for (let i = 1; i < CARTES_PROPOSEES.length; i++) expect(CARTES_PROPOSEES[i]).toBe(2 * CARTES_PROPOSEES[i - 1]);
    expect(JETONS_DU_CACHE).toBe(4096);
  });

  it('les modèles : les 5 tailles de ton IA (clés de forge), puis les modèles publics (identifiants du plan 5)', () => {
    expect(MODELES_DU_CALCULATEUR.map((m) => m.id)).toEqual([
      'mini',
      'petit',
      'moyen',
      'grand',
      'tres_grand',
      'gpt-3-175b',
      'llama-3-8b',
      'llama-3-70b',
      'llama-3-405b',
    ]);
    expect(modeleDuCalculateur('tres_grand').nom).toBe(`ton IA «${FINE}très grand${FINE}»`);
    expect(modeleDuCalculateur('tres_grand').forme).toBe(PRESETS_FORGE.tres_grand);
    expect(modeleDuCalculateur('llama-3-405b').nom).toBe('Llama 3 405B');
    expect(() => modeleDuCalculateur('gpt-5')).toThrow(/gpt-5.*tres_grand/);
  });

  it('les groupes des sélecteurs : « Ton IA » et « Modèles publics » ; « Chez toi », « Colab » et « En location »', () => {
    expect(GROUPES_MODELES.map((g) => [g.titre, g.modeles.length])).toEqual([
      ['Ton IA', 5],
      ['Modèles publics', 4],
    ]);
    expect(GROUPES_MATERIELS.map((g) => [g.titre, g.materiels.map((m) => m.id)])).toEqual([
      ['Chez toi', ['rtx-5070-ti', 'rtx-5080', 'rtx-5090', 'rtx-4090']],
      ['Colab', ['t4', 'l4']],
      ['En location', ['a100-80', 'h100-sxm', 'h200', 'b200']],
    ]);
  });

  it('le réglage de départ : ton IA « très grand », une RTX 5070 Ti, 20 jetons par paramètre, l’efficacité de la catégorie', () => {
    expect(reglageDeDepart()).toEqual({
      modele: 'tres_grand',
      materiel: 'rtx-5070-ti',
      cartes: 1,
      jetonsParParametre: 20,
      efficacitePourcent: 50,
    });
    // Une carte de centre de données part de 40 %, sauf efficacité donnée (en fraction, comme EFFICACITE_PAR_DEFAUT).
    expect(reglageDeDepart({ materiel: 'h100-sxm' }).efficacitePourcent).toBe(40);
    expect(reglageDeDepart({ materiel: 't4' }).efficacitePourcent).toBe(40);
    expect(reglageDeDepart({ materiel: 'h100-sxm', efficacite: 0.55, cartes: 8, jetonsParParametre: 200 })).toEqual({
      modele: 'tres_grand',
      materiel: 'h100-sxm',
      cartes: 8,
      jetonsParParametre: 200,
      efficacitePourcent: 55,
    });
  });

  it('un réglage impossible est refusé, avec les valeurs permises', () => {
    expect(() => reglageDeDepart({ modele: 'gpt-5' })).toThrow(/gpt-5/);
    expect(() => reglageDeDepart({ materiel: 'rtx-9090' })).toThrow(/rtx-9090/);
    expect(() => reglageDeDepart({ cartes: 3 })).toThrow(/1, 2, 4/);
    expect(() => reglageDeDepart({ jetonsParParametre: 30 })).toThrow(/20, 50/);
    expect(() => reglageDeDepart({ efficacite: 0.05 })).toThrow(/10.*70/);
    expect(() => reglageDeDepart({ efficacite: 50 })).toThrow(/fraction/);
    expect(() => reglageDeDepart({ efficacite: 0.555 })).toThrow(/1 en 1/);
  });
});

describe('le relevé du réglage de départ : ton IA sur la RTX 5070 Ti', () => {
  const rel = releve();

  it('les nombres viennent des formules', () => {
    expect(rel.jetons).toBe(20 * N);
    expect(rel.operations).toBe(operationsEntrainement(N, 20 * N));
    expect(rel.secondes).toBe(dureeSecondes(operationsEntrainement(N, 20 * N), 87.9, 0.5, 1));
  });

  it('les textes du plan : 8,67 milliards de jetons, 2,26 × 10¹⁹ opérations, 5,9 jours, 42,8 kWh pour environ 8,56 €', () => {
    expect(n(texteJetons(rel))).toBe('8,67 milliards');
    expect(texteCalcul(rel)).toBe(`2,26${FINE}×${FINE}10¹⁹${INSECABLE}opérations`);
    expect(n(texteDuree(rel))).toBe('5,9 jours');
    expect(n(texteMemoire(rel))).toBe(`8,1 Go${FINE}: ça tient sur une carte de 16 Go`);
    expect(n(texteElectricite(rel))).toBe('42,8 kWh, environ 8,56 €');
    expect(texteLocation(rel)).toBe('pas de prix relevé pour cette carte');
  });

  it('la mémoire pour s’en servir : bf16, int8, int4, et le cache de tout son contexte (2 048 jetons, moins que 4 096)', () => {
    expect(n(texteService(rel))).toBe(
      `827 Mo en bf16, 413 Mo en int8 ou 207 Mo en int4, plus 200 Mo de cache pour 2${FINE}048 jetons (tout son contexte)`,
    );
    expect(rel.service.jetonsDuCache).toBe(2048);
    // Llama 3 a un contexte de 8 192 jetons : le cache est celui de 4 096.
    expect(releve({ modele: 'llama-3-8b' }).service.jetonsDuCache).toBe(4096);
    expect(n(texteService(releve({ modele: 'llama-3-8b' })))).toMatch(/de cache pour 4\u202F096 jetons$/);
  });

  it('le plafond de génération, si les poids tiennent sur une carte', () => {
    expect(n(texteGeneration(rel))).toBe(`1${FINE}033 jetons par seconde en bf16, sur une carte`);
  });

  it('la phrase qui compare au repère mesuré', () => {
    expect(n(phraseRepere(rel))).toBe(
      `Calcul${FINE}: 5,9 jours. Mesuré${FINE}: 5,6 jours (135 h). ` +
        `L’écart vient de l’efficacité${FINE}: 52,8${FINE}% mesurés contre 50${FINE}% supposés.`,
    );
    expect(rel.repere?.efficacite).toBe(efficaciteMesuree(N, 17_855, 87.9));
  });

  it('chaque quantité garde son nombre et son unité ensemble (espace insécable)', () => {
    expect(texteDuree(rel)).toBe(`5,9${INSECABLE}jours`);
    expect(texteJetons(rel)).toBe(`8,67${INSECABLE}milliards`);
    expect(texteMemoire(rel)).toBe(`8,1${INSECABLE}Go${FINE}: ça tient sur une carte de 16${INSECABLE}Go`);
    expect(texteElectricite(rel)).toBe(`42,8${INSECABLE}kWh, environ 8,56${INSECABLE}€`);
    expect(phraseRepere(rel)).toContain(`5,6${INSECABLE}jours (135${INSECABLE}h)`);
  });

  it('l’annonce aux lecteurs d’écran : la durée et la location', () => {
    expect(n(annonce(rel))).toBe(`Durée${FINE}: 5,9 jours. Location${FINE}: pas de prix relevé pour cette carte.`);
  });
});

describe('la phrase de repère ne compare que ce qui a été mesuré', () => {
  it('une taille de ton IA sur une seule RTX 5070 Ti, quel que soit le nombre de jetons', () => {
    expect(phraseRepere(releve({ modele: 'mini' }))).not.toBeNull();
    // Une durée déjà en heures n'est pas répétée entre parenthèses.
    expect(n(phraseRepere(releve({ jetonsParParametre: 1 })))).toMatch(/^Calcul\u202F: 7,1 h\. Mesuré\u202F: 6,7 h\. L’écart/);
    expect(n(phraseRepere(releve({ modele: 'mini' })))).toMatch(/^Calcul\u202F: 25 min\. Mesuré\u202F: 33 min \(0,6 h\)\./);
    expect(phraseRepere(releve({ cartes: 2 }))).toBeNull();
    expect(phraseRepere(releve({ materiel: 'rtx-5090' }))).toBeNull();
    expect(phraseRepere(releve({ modele: 'llama-3-8b' }))).toBeNull();
  });
});

describe('les valeurs extrêmes (point à surveiller 4 du plan)', () => {
  it('405 milliards sur une seule RTX 5070 Ti : des années, « il faut au moins N cartes », des GWh', () => {
    const rel = releve({ modele: 'llama-3-405b' });
    expect(n(texteDuree(rel))).toBe(`14${FINE}192 ans`);
    expect(n(texteMemoire(rel))).toBe(`6,4 To${FINE}: il faut au moins 411 cartes de 16 Go`);
    expect(n(texteElectricite(rel))).toBe('37,3 GWh, environ 7,5 millions d’euros');
    expect(n(texteGeneration(rel))).toBe(
      `1,1 jeton par seconde en bf16 sur une carte, mais les poids n’y tiennent pas${FINE}: ` +
        'il faut au moins 48 cartes de 16 Go pour les loger',
    );
  });

  it('puis 16 384 H100 à 40 % : 35 jours, des millions d’euros, et la carte de 80 Go (jamais un « 16 Go » écrit en dur)', () => {
    const rel = releve({ modele: 'llama-3-405b', materiel: 'h100-sxm', cartes: 16_384, efficacitePourcent: 40 });
    expect(n(texteDuree(rel))).toBe('35 jours');
    expect(n(texteMemoire(rel))).toBe(`6,4 To${FINE}: il faut au moins 83 cartes de 80 Go`);
    expect(n(texteLocation(rel))).toBe('de 33 à 152 millions d’euros (de 37 à 170 millions de dollars), selon le loueur');
    expect(texteElectricite(rel)).toBeNull();
  });

  it('tous les réglages aux bouts : jamais NaN, Infinity ni « e+ », et une typographie française', () => {
    const modeles = MODELES_DU_CALCULATEUR.map((m) => m.id);
    let compte = 0;
    for (const modele of modeles) {
      for (const m of MATERIELS) {
        for (const cartes of [1, 16_384]) {
          for (const jetonsParParametre of [1, 2000]) {
            for (const efficacitePourcent of [10, 70]) {
              const rel = calculerReleve({ modele, materiel: m.id, cartes, jetonsParParametre, efficacitePourcent });
              for (const t of textes(rel)) {
                expect(t, `${modele} ${m.id} ${cartes} ${jetonsParParametre} ${efficacitePourcent}`).not.toMatch(INTERDIT);
                expect(t.match(/.{0,30}[ \u00A0][;:!?%].{0,10}/g) ?? []).toEqual([]);
                expect(t.match(/.{0,20}\d[ \u00A0]\d{3}\b.{0,20}/g) ?? []).toEqual([]);
                expect(t.match(/.{0,20}\p{L}'\p{L}.{0,20}/gu) ?? []).toEqual([]);
              }
              compte++;
            }
          }
        }
      }
    }
    expect(compte).toBe(9 * 10 * 8);
  });
});

describe('la location', () => {
  it('le pari « coût » : ton IA sur une H100 à 40 %, de 38 à 174 € (de 43 à 195 $)', () => {
    const rel = releve({ materiel: 'h100-sxm', efficacitePourcent: 40 });
    expect(n(texteLocation(rel))).toBe('de 38 à 174 € (de 43 à 195 $), selon le loueur');
    expect(rel.location?.prix).toEqual(fourchettePrix('h100-sxm')?.prix);
    // Deux fois plus de cartes, c'est deux fois moins longtemps, pour le même prix.
    expect(texteLocation(releve({ materiel: 'h100-sxm', efficacitePourcent: 40, cartes: 8 }))).toBe(texteLocation(rel));
  });

  it('une carte sans prix relevé le dit', () => {
    for (const id of ['rtx-5070-ti', 'rtx-5080', 't4', 'l4']) {
      expect(texteLocation(releve({ materiel: id })), id).toBe('pas de prix relevé pour cette carte');
      expect(releve({ materiel: id }).location, id).toBeNull();
    }
  });

  it('fourchette : une seule unité quand les deux bouts la partagent', () => {
    expect(n(fourchette('38 €', '174 €'))).toBe('de 38 à 174 €');
    expect(n(fourchette('33 millions d’euros', '152 millions d’euros'))).toBe('de 33 à 152 millions d’euros');
    expect(n(fourchette('1,2 million d’euros', '5,4 millions d’euros'))).toBe('de 1,2 à 5,4 millions d’euros');
    expect(n(fourchette('8,56 €', '1,2 million d’euros'))).toBe('de 8,56 € à 1,2 million d’euros');
    expect(n(fourchette('moins d’un euro', '3,20 €'))).toBe('jusqu’à 3,20 €');
    expect(n(fourchette('38 €', '38 €'))).toBe('38 €');
    expect(n(fourchette(`999 €`, `1${FINE}230 €`))).toBe(`de 999 à 1${FINE}230 €`);
    expect(fourchette('38 €', '174 €')).toBe(`de 38 à 174${INSECABLE}€`);
  });
});

describe('les cartes grand public seulement ont une ligne « Électricité »', () => {
  it('au Tarif Bleu d’EDF, avec la puissance maximale de la carte', () => {
    for (const m of MATERIELS) {
      const e = texteElectricite(releve({ materiel: m.id }));
      if (m.categorie === 'grand-public') expect(e, m.id).toMatch(/kWh/);
      else expect(e, m.id).toBeNull();
    }
  });

  it('un entraînement minuscule : moins de 0,1 kWh, moins d’un euro', () => {
    const rel = releve({ modele: 'mini', materiel: 'rtx-5090', cartes: 16_384, jetonsParParametre: 1, efficacitePourcent: 70 });
    expect(n(texteElectricite(rel))).toBe('moins de 0,1 kWh, moins d’un euro');
    expect(n(texteDuree(rel))).toBe('moins d’une seconde');
  });
});

describe('« Voir le calcul » : chaque formule avec ses nombres et ses sources', () => {
  it('le calcul, tel que le plan l’écrit', () => {
    const f = formulesDuCalcul(releve());
    const calcul = f.find((x) => x.cle === 'calcul');
    expect(n(calcul?.formule ?? '')).toBe('6 × 433,6 millions × 8,67 milliards = 2,26\u202F×\u202F10¹⁹ opérations');
    expect(n(calcul?.formule ?? '')).toBe(
      `6 × ${formaterQuantite(N)} × ${formaterQuantite(20 * N)} = ${formaterPuissanceDeDix(operationsEntrainement(N, 20 * N))} opérations`,
    );
    for (const x of f) {
      expect(x.sources.length, x.cle).toBeGreaterThan(0);
      for (const s of x.sources) expect(s.url, x.cle).toMatch(/^https:\/\//);
    }
  });

  it('les formules de la durée, de la mémoire, du service, de la génération, de l’électricité', () => {
    const f = formulesDuCalcul(releve());
    expect(f.map((x) => x.cle)).toEqual(['calcul', 'duree', 'memoire', 'service', 'generation', 'electricite', 'efficacites']);
    const formule = (cle: string) => n(f.find((x) => x.cle === cle)?.formule ?? '');
    expect(formule('duree')).toBe(
      `2,26${FINE}×${FINE}10¹⁹ ÷ (1 carte × 87,9${FINE}×${FINE}10¹² opérations par seconde × 50${FINE}%) = 5,9 jours`,
    );
    expect(formule('memoire')).toBe(
      `16 octets × 433,6 millions = 6,5 Go, plus 34 × 2${FINE}048 × 1${FINE}280 × 20 octets = 1,7 Go${FINE}: 8,1 Go en tout`,
    );
    expect(formule('service')).toBe(
      `433,6 millions × 2 octets = 827 Mo en bf16, × 1 = 413 Mo en int8, × 0,5 = 207 Mo en int4${FINE}; ` +
        `cache${FINE}: 2 × 2 × 20 couches × 20 têtes × 64 × 2${FINE}048 jetons = 200 Mo`,
    );
    expect(formule('generation')).toBe(`896${FINE}×${FINE}10⁹ octets par seconde ÷ 867,1 millions d’octets = 1${FINE}033 jetons par seconde`);
    expect(formule('electricite')).toBe(`300 W × 1 carte × 5,9 jours = 42,8 kWh${FINE}; × 0,2001 € le kWh = 8,56 €`);
  });

  it('les deux efficacités de ton IA : 52,8 % avec 6N, 65,6 % en comptant l’attention', () => {
    const e = formulesDuCalcul(releve()).find((x) => x.cle === 'efficacites');
    expect(n(e?.formule ?? '')).toBe(
      `6 × 433,6 millions × 17${FINE}855 jetons par seconde ÷ 87,9${FINE}×${FINE}10¹² = 52,8${FINE}%${FINE}; ` +
        `en comptant l’attention${FINE}: (6 × 433,6 millions + 12 × 20 × 1${FINE}280 × 2${FINE}048) × 17${FINE}855 ÷ 87,9${FINE}×${FINE}10¹² = 65,6${FINE}%`,
    );
    // Seulement pour ton IA, mais sur n'importe quelle carte (les mesures sont celles de ce PC).
    expect(formulesDuCalcul(releve({ materiel: 'h100-sxm' })).some((x) => x.cle === 'efficacites')).toBe(true);
    expect(formulesDuCalcul(releve({ modele: 'gpt-3-175b' })).some((x) => x.cle === 'efficacites')).toBe(false);
  });

  it('la location sur une carte qui a des prix, avec le taux de la BCE', () => {
    const f = formulesDuCalcul(releve({ materiel: 'h100-sxm', efficacitePourcent: 40 }));
    expect(f.map((x) => x.cle)).toEqual(['calcul', 'duree', 'memoire', 'service', 'generation', 'location', 'efficacites']);
    expect(n(f.find((x) => x.cle === 'location')?.formule ?? '')).toBe(
      `16 h × 1 carte × de 2,69 à 12,29 $ = de 43 à 195 $${FINE}; ÷ 1,1179 = de 38 à 174 €`,
    );
  });
});

describe('le repère mesuré : ton IA sur ce PC', () => {
  it('les 5 tailles : débits, durée pour 20 jetons par paramètre, efficacité implicite, processeur', () => {
    const lignes = lignesReperes();
    expect(lignes.map((l) => l.cle)).toEqual(['mini', 'petit', 'moyen', 'grand', 'tres_grand']);
    const tg = lignes[4];
    expect(n(tg.nom)).toBe('très grand');
    expect(n(tg.parametres)).toBe('433,6 millions');
    expect(n(tg.carteDebit)).toBe(`17${FINE}855 jetons`);
    expect(n(tg.carteDuree)).toBe(formaterDuree(134.906 * 3600));
    expect(n(tg.carteDuree)).toBe('5,6 jours');
    expect(tg.efficacite).toBe(pourcent(efficaciteMesuree(N, 17_855, materiel('rtx-5070-ti').creteTflops), 1));
    expect(n(tg.processeurDebit)).toBe('235 jetons');
    expect(n(tg.processeurDuree)).toBe('1,2 an');
  });

  it('comparer comme les grands : ton IA compte l’attention comme PaLM et Llama 3 (65,6 %), et 52,8 % avec 6N seulement', () => {
    expect(n(phraseCommeLesGrands(releve()))).toBe(
      'Pour comparer avec les grands entraînements, il faut compter les opérations comme eux. ' +
        `PaLM 540B (46,2${FINE}%) et Llama 3 405B (de 38${FINE}% à 43${FINE}%) comptent aussi l’attention${FINE}: ` +
        `ton IA «${FINE}très grand${FINE}» fait alors 65,6${FINE}% sur ce PC. ` +
        `Avec 6N seulement, comme le calculateur, elle fait 52,8${FINE}%.`,
    );
    // La taille choisie, si c'est une taille de ton IA.
    expect(n(phraseCommeLesGrands(releve({ modele: 'mini' })))).toContain(`ton IA «${FINE}mini${FINE}» fait alors`);
    expect(n(phraseCommeLesGrands(releve({ modele: 'gpt-3-175b' })))).toContain(`ton IA «${FINE}très grand${FINE}» fait alors`);
  });
});
