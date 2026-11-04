// Le relevé du calculateur : les nombres et les phrases que le composant
// affiche, calculés par les formules, sur les données relevées. Les attendus
// écrits en toutes lettres sont ceux du plan ; les autres sont recalculés par
// les formules (rien n'est recopié deux fois).

import { describe, expect, it } from 'vitest';
import { pourcent } from '../nombres';
import { EFFICACITE_PAR_DEFAUT, fourchettePrix, MATERIELS, materiel, REPERES_EFFICACITE, TAUX_DE_CHANGE } from './donnees';
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
  sourcesDesReperes,
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
    // Les poids en bf16 ne tiennent pas sur une carte : pas de débit, seulement les cartes qu'il faudrait.
    expect(n(texteGeneration(rel))).toBe(
      `pas sur une seule carte${FINE}: les poids en bf16 n’y tiennent pas, il faut au moins 48 cartes de 16 Go pour les loger`,
    );
    expect(n(formulesDuCalcul(rel).find((f) => f.cle === 'generation')?.formule ?? '')).toBe('754 Go ÷ 16 Go = au moins 48 cartes');
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
    // Le diviseur est dans l'unité de la ligne « mémoire pour s'en servir » (827 Mo en bf16).
    expect(formule('generation')).toBe(`896${FINE}×${FINE}10⁹ octets par seconde ÷ 827 Mo = 1${FINE}033 jetons par seconde`);
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
        `PaLM 540B (46,2${FINE}%) et Llama 3 405B (de 38${FINE}% à 43${FINE}%, avec la définition de PaLM) comptent aussi l’attention${FINE}: ` +
        `ton IA «${FINE}très grand${FINE}» fait alors 65,6${FINE}% sur ce PC. ` +
        `Avec 6N seulement, comme le calculateur, elle fait 52,8${FINE}%.`,
    );
    // La taille choisie, si c'est une taille de ton IA.
    expect(n(phraseCommeLesGrands(releve({ modele: 'mini' })))).toContain(`ton IA «${FINE}mini${FINE}» fait alors`);
    expect(n(phraseCommeLesGrands(releve({ modele: 'gpt-3-175b' })))).toContain(`ton IA «${FINE}très grand${FINE}» fait alors`);
  });
});

describe('les repères publiés : leurs sources et leurs dates', () => {
  it('PaLM et Llama 3, chacun avec ses efficacités, sa définition et sa source', () => {
    const r = sourcesDesReperes();
    expect(r.map((x) => n(x.texte))).toEqual([
      `PaLM 540B, 46,2${FINE}% (6${FINE}144 puces TPU v4)`,
      `Llama 3 405B, de 38${FINE}% à 43${FINE}% (de 8${FINE}192 à 16${FINE}384 H100)`,
    ]);
    expect(r.map((x) => x.source)).toEqual(REPERES_EFFICACITE.map((x) => x.source));
    expect(r.map((x) => x.definition)).toEqual(REPERES_EFFICACITE.map((x) => x.definition));
  });
});

describe('l’efficacité qui suit la carte se voit', () => {
  it('l’annonce le dit quand elle vient de changer avec la carte', () => {
    const h100 = releve({ materiel: 'h100-sxm', efficacitePourcent: 40 });
    expect(n(annonce(h100, true))).toBe(
      `Efficacité${FINE}: 40${FINE}%, celle d’une carte de centre de données. Durée${FINE}: 16 h. ` +
        `Location${FINE}: de 38 à 174 € (de 43 à 195 $), selon le loueur.`,
    );
    expect(n(annonce(releve({ materiel: 't4', efficacitePourcent: 40 }), true))).toMatch(/^Efficacité\u202F: 40\u202F%, celle d’une carte de Colab\. /);
    expect(n(annonce(releve({ materiel: 'rtx-5090' }), true))).toMatch(/^Efficacité\u202F: 50\u202F%, celle d’une carte grand public\. /);
    expect(annonce(h100)).not.toMatch(/Efficacité/);
  });

  it('l’explication de la durée donne les valeurs par défaut et leur base, calculées', () => {
    const duree = formulesDuCalcul(releve()).find((f) => f.cle === 'duree');
    const p = (x: number) => pourcent(x, Number.isInteger(x * 100) ? 0 : 1);
    expect(n(duree?.explication ?? '')).toContain(
      `Par défaut, le calculateur suppose ${p(EFFICACITE_PAR_DEFAUT['grand-public'])} sur une carte grand public ` +
        `(ton IA en tient ${pourcent(efficaciteMesuree(N, 17_855, 87.9), 1)} sur ce PC), ${p(EFFICACITE_PAR_DEFAUT.colab)} sur Colab et ` +
        `${p(EFFICACITE_PAR_DEFAUT['centre-de-donnees'])} en centre de données, dans la fourchette des grands entraînements publiés ` +
        `(de 38${FINE}% à 46,2${FINE}%).`,
    );
    // Les sources de la durée comprennent celles des repères publiés.
    for (const r of REPERES_EFFICACITE) expect(duree?.sources).toContain(r.source);
  });
});

describe('« Voir le calcul » dit ses unités et ne laisse jamais un opérateur en fin de ligne', () => {
  it('les explications de la mémoire disent que 1 Go vaut 1 024³ octets', () => {
    for (const cle of ['memoire', 'service'] as const) {
      const f = formulesDuCalcul(releve()).find((x) => x.cle === cle);
      expect(n(f?.explication ?? ''), cle).toContain(`Ici, 1 Go vaut 1${FINE}024³ octets, comme la mémoire des cartes`);
    }
    expect(n(formulesDuCalcul(releve()).find((x) => x.cle === 'generation')?.explication ?? '')).toContain('en octets décimaux');
  });

  it('l’énergie reste en kWh dans la formule, même pour 405 milliards sur une seule carte', () => {
    const f = formulesDuCalcul(releve({ modele: 'llama-3-405b', jetonsParParametre: 2000, efficacitePourcent: 10 }));
    expect(plat(f.find((x) => x.cle === 'electricite')?.formule ?? '')).toMatch(/= 18,7 milliards de kWh ; × 0,2001 € le kWh = /);
  });

  it('après ×, ÷, + et =, une espace insécable : l’opérateur reste avec le nombre qui suit', () => {
    for (const modele of MODELES_DU_CALCULATEUR.map((m) => m.id)) {
      for (const m of MATERIELS) {
        for (const f of formulesDuCalcul(releve({ modele, materiel: m.id }))) {
          expect(f.formule.match(/.{0,15}[×÷+=](?![\u00A0\u202F]).{0,15}/g) ?? [], `${modele} ${m.id} ${f.cle}`).toEqual([]);
          expect(f.formule, `${modele} ${m.id} ${f.cle}`).not.toMatch(/[×÷+=]$/);
        }
      }
    }
  });
});

// ---------- Refaire chaque étape à la main ----------
//
// Chaque formule affichée est relue comme un lecteur la lirait : les nombres
// affichés (arrondis) sont repris, l'opération refaite, et le résultat doit
// tomber sur le résultat affiché, à l'arrondi près. L'arrondi possible d'un
// nombre est la moitié de son dernier chiffre ; il se propage au premier ordre.

/** Un nombre lu : sa valeur et l'erreur d'arrondi possible. */
interface Lu {
  v: number;
  e: number;
}

const exact = (v: number): Lu => ({ v, e: 0 });
const sansErreur = (x: Lu): Lu => ({ v: x.v, e: 0 });
const SUPERIEURS = '⁰¹²³⁴⁵⁶⁷⁸⁹';

/** Les espaces insécables deviennent ordinaires ; les fines aussi, sauf entre deux chiffres (les milliers). */
const plat = (t: string) => t.replace(/\u00A0/g, ' ').replace(/(?<!\d)\u202F|\u202F(?!\d)/g, ' ');

/** Un nombre écrit en français (« 433,6 », « 17 855 ») ; l'erreur vaut la moitié de son dernier chiffre. */
function lireNombre(t: string): Lu {
  const m = /^(\d[\d\u202F]*)(?:,(\d+))?$/.exec(t);
  if (m === null) throw new Error(`nombre illisible : « ${t} »`);
  const decimales = m[2]?.length ?? 0;
  return { v: Number(`${m[1].replace(/\u202F/g, '')}.${m[2] ?? '0'}`), e: 0.5 / 10 ** decimales };
}

/** Un entier exact (cartes, couches, dimensions, jetons du cache). */
const entier = (t: string): Lu => sansErreur(lireNombre(t));

const UNITES: Record<string, number> = {
  opérations: 1,
  million: 1e6,
  millions: 1e6,
  milliard: 1e9,
  milliards: 1e9,
  Mo: 1024 ** 2,
  Go: 1024 ** 3,
  To: 1024 ** 4,
  s: 1,
  min: 60,
  h: 3600,
  jours: 86_400,
  an: 31_557_600,
  ans: 31_557_600,
  kWh: 1,
  'million de kWh': 1e6,
  'millions de kWh': 1e6,
  'milliard de kWh': 1e9,
  'milliards de kWh': 1e9,
  '€': 1,
  'million d’euros': 1e6,
  'millions d’euros': 1e6,
  'milliard d’euros': 1e9,
  'milliards d’euros': 1e9,
  $: 1,
  'million de dollars': 1e6,
  'millions de dollars': 1e6,
  'milliard de dollars': 1e9,
  'milliards de dollars': 1e9,
  'million d’heures': 3600e6,
  'millions d’heures': 3600e6,
  'milliard d’heures': 3600e9,
  'milliards d’heures': 3600e9,
  jeton: 1,
  jetons: 1,
  '%': 0.01,
};

const TROIS_CHIFFRES = new Set(['€', '$', 'milliard', 'milliards']);

/** Une quantité affichée : « 433,6 millions », « 2,26 × 10¹⁹ », « 5,9 jours » (en secondes), « 827 Mo » (en octets), « 52,8 % ». */
function lire(texte: string): Lu {
  const t = plat(texte).trim();
  if (t === 'moins d’une seconde') return { v: 0.25, e: 0.25 };
  if (/^moins de 0,1 (kWh|h)$/.test(t)) return { v: 0.05 * (t.endsWith('h') && !t.endsWith('kWh') ? 3600 : 1), e: 0.05 * (t.endsWith('h') && !t.endsWith('kWh') ? 3600 : 1) };
  if (/^moins d’un (euro|dollar)$/.test(t)) return { v: 0.5, e: 0.5 };
  const p = /^([\d\u202F,]+) × 10(⁻?[⁰¹²³⁴⁵⁶⁷⁸⁹]+)(?: opérations)?$/.exec(t);
  if (p !== null) {
    const exposant = Number(Array.from(p[2]).map((c) => (c === '⁻' ? '-' : String(SUPERIEURS.indexOf(c)))).join(''));
    const mantisse = lireNombre(p[1]);
    return { v: mantisse.v * 10 ** exposant, e: mantisse.e * 10 ** exposant };
  }
  const m = /^(\d[\d\u202F]*(?:,\d+)?) (.+)$/.exec(t);
  if (m === null || !(m[2] in UNITES)) throw new Error(`quantité illisible : « ${t} »`);
  let x = lireNombre(m[1]);
  // Les montants de 1 000 € (ou $) et plus, et les milliards de formaterQuantite, n'ont que trois chiffres significatifs.
  if (TROIS_CHIFFRES.has(m[2]) && x.v >= 1000 && Number.isInteger(x.v)) x = { v: x.v, e: 0.5 * 10 ** (String(x.v).length - 3) };
  return { v: x.v * UNITES[m[2]], e: x.e * UNITES[m[2]] };
}

/** Une fourchette affichée : « de 38 à 174 € », « de 8,56 € à 1,2 million d’euros », « jusqu’à 3,20 € », « 38 € ». */
function lireFourchette(texte: string): [Lu, Lu] {
  const t = plat(texte).trim();
  const jusqua = /^jusqu’à (.+)$/.exec(t);
  if (jusqua !== null) return [lire('moins d’un euro'), lire(jusqua[1])];
  const de = /^de (.+?) à (.+)$/.exec(t);
  if (de === null) return [lire(t), lire(t)];
  const haut = lire(de[2]);
  if (/^[\d\u202F,]+$/.test(de[1])) {
    const unite = /^[\d\u202F,]+ (.+)$/.exec(de[2])?.[1] ?? '';
    return [lire(`${de[1]} ${unite}`), haut];
  }
  return [lire(de[1]), haut];
}

const fois = (...xs: Lu[]): Lu => {
  let v = 1;
  let relatif = 0;
  for (const x of xs) {
    v *= x.v;
    relatif += x.e / Math.abs(x.v);
  }
  return { v, e: Math.abs(v) * relatif };
};
const divise = (a: Lu, b: Lu): Lu => {
  const v = a.v / b.v;
  return { v, e: Math.abs(v) * (a.e / Math.abs(a.v) + b.e / Math.abs(b.v)) };
};
const plus = (a: Lu, b: Lu): Lu => ({ v: a.v + b.v, e: a.e + b.e });

function proche(refait: Lu, affiche: Lu, quoi: string): void {
  const ecart = Math.abs(refait.v - affiche.v);
  expect(ecart, `${quoi} : refait ${refait.v}, affiché ${affiche.v}`).toBeLessThanOrEqual(refait.e + affiche.e + 1e-9 * Math.abs(affiche.v));
}

/** « au moins N cartes » de `memoire` pour loger `total` : N est le plus petit entier qui suffit, à l'arrondi de `total` près. */
function cartesSuffisent(total: Lu, memoire: Lu, cartes: Lu, quoi: string): void {
  expect(cartes.v * memoire.v, `${quoi} : ${cartes.v} cartes suffisent`).toBeGreaterThanOrEqual(total.v - total.e);
  expect((cartes.v - 1) * memoire.v, `${quoi} : il en faut ${cartes.v}`).toBeLessThan(total.v + total.e);
}

function verifierALaMain(rel: Releve, quoi: string): number {
  let etapes = 0;
  const RE: Record<string, RegExp> = {
    calcul: /^6 × (.+?) × (.+?) = (.+) opérations$/,
    duree: /^(.+?) ÷ \(([\d\u202F]+) cartes? × (.+?) opérations par seconde × (\d+) %\) = (.+)$/,
    memoire: /^16 octets × (.+?) = (.+?), plus 34 × ([\d\u202F]+) × ([\d\u202F]+) × ([\d\u202F]+) octets = (.+?) : (.+?) en tout(?: ; (.+?) ÷ (.+?) = au moins ([\d\u202F]+) cartes)?$/,
    service:
      /^(.+?) × 2 octets = (.+?) en bf16, × 1 = (.+?) en int8, × 0,5 = (.+?) en int4 ; cache : 2 × 2 × ([\d\u202F]+) couches × ([\d\u202F]+) têtes × ([\d\u202F]+) × ([\d\u202F]+) jetons = (.+)$/,
    generation: /^([\d\u202F]+) × 10⁹ octets par seconde ÷ (.+?) = (.+) par seconde$|^(.+?) ÷ (.+?) = au moins ([\d\u202F]+) cartes$/,
    electricite: /^([\d\u202F]+) W × ([\d\u202F]+) cartes? × (.+?) = (.+?) ; × (.+?) € le kWh = (.+)$/,
    location: /^(.+?) × ([\d\u202F]+) cartes? × (.+?) = (.+?) ; ÷ ([\d,]+) = (.+)$/,
    efficacites:
      /^6 × (.+?) × ([\d\u202F]+) jetons par seconde ÷ (.+?) = (.+?) ; en comptant l’attention : \(6 × (.+?) \+ 12 × ([\d\u202F]+) × ([\d\u202F]+) × ([\d\u202F]+)\) × ([\d\u202F]+) ÷ (.+?) = (.+)$/,
  };
  for (const f of formulesDuCalcul(rel)) {
    const t = plat(f.formule);
    const m = RE[f.cle].exec(t);
    expect(m, `${quoi}, ${f.cle} : formule inattendue « ${t} »`).not.toBeNull();
    if (m === null) continue;
    const q = `${quoi}, ${f.cle}`;
    if (f.cle === 'calcul') {
      proche(fois(exact(6), lire(m[1]), lire(m[2])), lire(m[3]), q);
    } else if (f.cle === 'duree') {
      proche(divise(lire(m[1]), fois(entier(m[2]), sansErreur(lire(m[3])), exact(Number(m[4]) / 100))), lire(m[5]), q);
    } else if (f.cle === 'memoire') {
      const etats = lire(m[2]);
      const activations = lire(m[6]);
      proche(fois(exact(16), lire(m[1])), etats, `${q} (états)`);
      proche(fois(exact(34), entier(m[3]), entier(m[4]), entier(m[5])), activations, `${q} (activations)`);
      proche(plus(etats, activations), lire(m[7]), `${q} (total)`);
      if (m[8] !== undefined) cartesSuffisent(lire(m[8]), sansErreur(lire(m[9])), entier(m[10]), `${q} (cartes)`);
    } else if (f.cle === 'service') {
      const N = lire(m[1]);
      proche(fois(N, exact(2)), lire(m[2]), `${q} (bf16)`);
      proche(N, lire(m[3]), `${q} (int8)`);
      proche(fois(N, exact(0.5)), lire(m[4]), `${q} (int4)`);
      proche(fois(exact(4), entier(m[5]), entier(m[6]), entier(m[7]), entier(m[8])), lire(m[9]), `${q} (cache)`);
    } else if (f.cle === 'generation') {
      if (m[1] !== undefined) proche(divise(exact(entier(m[1]).v * 1e9), lire(m[2])), lire(m[3]), q);
      else cartesSuffisent(lire(m[4]), sansErreur(lire(m[5])), entier(m[6]), q);
    } else if (f.cle === 'electricite') {
      const kwh = lire(m[4]);
      proche(divise(fois(entier(m[1]), entier(m[2]), lire(m[3])), exact(3_600_000)), kwh, `${q} (kWh)`);
      proche(fois(kwh, sansErreur(lireNombre(m[5]))), lire(m[6]), `${q} (euros)`);
    } else if (f.cle === 'location') {
      const heures = divise(lire(m[1]), exact(3600));
      const prix = lireFourchette(m[3]).map(sansErreur);
      const dollars = lireFourchette(m[4]);
      const euros = lireFourchette(m[6]);
      const taux = sansErreur(lireNombre(m[5]));
      expect(taux.v).toBe(TAUX_DE_CHANGE.usdPourUnEur);
      for (const i of [0, 1]) {
        proche(fois(heures, entier(m[2]), prix[i]), dollars[i], `${q} (dollars ${i})`);
        proche(divise(dollars[i], taux), euros[i], `${q} (euros ${i})`);
      }
    } else if (f.cle === 'efficacites') {
      const crete = sansErreur(lire(m[3]));
      proche(divise(fois(exact(6), lire(m[1]), entier(m[2])), crete), lire(m[4]), `${q} (6N)`);
      const parJeton = plus(fois(exact(6), lire(m[5])), exact(12 * entier(m[6]).v * entier(m[7]).v * entier(m[8]).v));
      proche(divise(fois(parJeton, entier(m[9])), sansErreur(lire(m[10]))), lire(m[11]), `${q} (avec l’attention)`);
    }
    etapes++;
  }
  return etapes;
}

describe('« Voir le calcul » se refait à la main, à partir des nombres affichés', () => {
  it('le réglage de départ : chaque étape retombe sur le résultat affiché', () => {
    expect(verifierALaMain(releve(), 'départ')).toBe(7);
    expect(verifierALaMain(releve({ materiel: 'h100-sxm', efficacitePourcent: 40 }), 'H100')).toBe(7);
  });

  it('tous les modèles, toutes les cartes, aux bouts des réglages', () => {
    let etapes = 0;
    for (const modele of MODELES_DU_CALCULATEUR.map((m) => m.id)) {
      for (const m of MATERIELS) {
        for (const cartes of [1, 16_384]) {
          for (const jetonsParParametre of [1, 20, 2000]) {
            for (const efficacitePourcent of [10, 50, 70]) {
              const rel = calculerReleve({ modele, materiel: m.id, cartes, jetonsParParametre, efficacitePourcent });
              etapes += verifierALaMain(rel, `${modele} ${m.id} ${cartes} ${jetonsParParametre} ${efficacitePourcent}`);
            }
          }
        }
      }
    }
    expect(etapes).toBeGreaterThan(9000);
  });
});
