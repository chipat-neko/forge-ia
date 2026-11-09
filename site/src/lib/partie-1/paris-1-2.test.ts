// Les paris du chapitre 1.2 et son atelier : leurs bonnes réponses viennent du jumeau du
// nettoyage (nettoyeur.ts), appliqué aux exemples du projet 1.2 et à son aperçu, lus sur le
// disque. Les attendus du Python (FICHIERS_PARTIE_1.nettoyeur) servent de témoin.

import { existsSync, readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { PART_VALIDATION } from './donnees';
import { FICHIERS_PARTIE_1 } from './fichiers';
import { MESURES_PARTIE_1 } from './mesures';
import {
  decoderTexte,
  empreinte,
  estValidation,
  garderPythonPermissif,
  LONGUEUR_MINIMALE,
  longueurPointsDeCode,
  nettoyer,
  normaliser,
  trier,
} from './nettoyeur';
import {
  choixCourt,
  choixDoublon,
  choixLicence,
  choixPartGardee,
  choixValidation,
  coteDuTexte,
  CONTROLE_RETIRE,
  COTE_SANS_EMPREINTE,
  DEFI_SANS_EMPREINTE,
  DOUBLON_SANS_EMPREINTE,
  EMPREINTE_IMPOSSIBLE,
  etatDuDefi,
  etatDuNettoyage,
  faitsDuPariCourt,
  faitsDuPariDoublon,
  faitsDuPariValidation,
  lireJsonl,
  messageDoublon,
  messagesDeLAtelier,
  morceauxDuNettoyage,
  phraseLongueur,
  RETOUR_CHARIOT,
  texteDeValidation,
  trancheDeLaPartGardee,
  TRANCHES_PART,
  verdictDuTexte,
  versWindows,
  type Apercu,
} from './paris-1-2';

const FINE = '\u202F';

// Vitest est lancé depuis site/ : le dépôt est un dossier plus haut.
const PROJET = '../projets/1.2-donnees';
const WEB = lireJsonl(readFileSync(`${PROJET}/exemples/web.jsonl`, 'utf8'));
const CODE = lireJsonl(readFileSync(`${PROJET}/exemples/code.jsonl`, 'utf8'));
const APERCU = JSON.parse(readFileSync(`../${MESURES_PARTIE_1.apercu}`, 'utf8')) as Apercu;
const ATTENDUS = JSON.parse(readFileSync(`../${FICHIERS_PARTIE_1.nettoyeur}`, 'utf8')) as {
  textes: { nom: string; entree: unknown; longueur: number; empreinte: string; validation: boolean }[];
};
const attendu = (nom: string) => {
  const t = ATTENDUS.textes.find((x) => x.nom === nom);
  if (!t) throw new Error(`texte de référence introuvable : ${nom}`);
  return { ...t, texte: decoderTexte(t.entree) as string };
};
const texteDe = (i: number): string => WEB[i].text as string;

/** Le texte nettoyé que montre l'atelier : les morceaux gardés, sans les retraits. */
const gardes = (brut: string): string =>
  morceauxDuNettoyage(brut)
    .filter((m) => !m.retire)
    .map((m) => m.texte)
    .join('');

describe('les exemples du projet', () => {
  it('se lisent comme lire_jsonl du Python : une ligne JSON par ligne non vide', () => {
    expect(WEB).toHaveLength(18);
    expect(CODE).toHaveLength(3);
    expect(texteDe(0)).toBe(attendu('web.jsonl, ligne 1').texte);
    expect(lireJsonl('{"a": 1}\n\n  \n{"a": 2}\n')).toStrictEqual([{ a: 1 }, { a: 2 }]);
  });
});

describe('le pari « court »', () => {
  it('la bonne réponse vient de nettoyer : 150 caractères, écarté', () => {
    const f = faitsDuPariCourt(texteDe(0));
    expect(f.longueur).toBe(attendu('web.jsonl, ligne 1').longueur);
    expect(f.longueur).toBe(150);
    expect(f.garde).toBe(nettoyer(texteDe(0)) !== null);
    expect(choixCourt(texteDe(0)).find((c) => c.juste)?.texte).toBe(`Non${FINE}: il est trop court`);
    expect(choixCourt(texteDe(0)).map((c) => c.texte)).toStrictEqual([
      `Oui${FINE}: il est propre`,
      `Non${FINE}: il est trop court`,
      'Oui, une fois sa typographie corrigée',
    ]);
  });

  it('un texte assez long est gardé ; un texte que le nettoyage change arrête la construction', () => {
    expect(choixCourt(texteDe(1)).find((c) => c.juste)?.texte).toBe(`Oui${FINE}: il est propre`);
    expect(() => faitsDuPariCourt(`${texteDe(0)}  `)).toThrow(/Exemple devenu faux/);
  });
});

describe('le pari « licence »', () => {
  it('la bonne réponse vient de garderPythonPermissif : le fichier GPL-3.0 est écarté', () => {
    expect(CODE[1].license).toBe('gpl-3.0');
    expect(garderPythonPermissif(CODE[1])).toBe(false);
    expect(choixLicence(CODE[1]).find((c) => c.juste)?.texte).toBe(`Non${FINE}: sa licence n’est pas dans la liste`);
    expect(choixLicence(CODE[0]).find((c) => c.juste)?.texte).toBe(`Oui${FINE}: c’est du Python`);
  });

  it('un fichier qui n’est pas du Python arrête la construction', () => {
    expect(() => choixLicence(CODE[2])).toThrow(/Exemple devenu faux/);
  });
});

describe('le pari « doublon »', () => {
  it('la bonne réponse vient des deux empreintes', async () => {
    const unix = texteDe(1);
    const windows = texteDe(2);
    expect(windows).toBe(versWindows(unix));
    const f = await faitsDuPariDoublon(unix, windows);
    expect(f.meme).toBe((await empreinte(unix)) === (await empreinte(windows)));
    expect(f.meme).toBe(true);
    expect(f.empreinte).toBe(attendu('web.jsonl, ligne 2').empreinte);
    const choix = await choixDoublon(unix, windows);
    expect(choix.find((c) => c.juste)?.texte).toBe(`Oui${FINE}: une fois nettoyés, ils sont identiques`);
  });

  it('un « texte de Windows » qui n’en est pas un arrête la construction', async () => {
    await expect(faitsDuPariDoublon(texteDe(1), texteDe(1))).rejects.toThrow(/Exemple devenu faux/);
    await expect(faitsDuPariDoublon(texteDe(0), versWindows(texteDe(0)))).rejects.toThrow(/Exemple devenu faux/);
  });
});

describe('le pari « validation »', () => {
  it('le texte de l’essai est le premier que est_validation met de côté', async () => {
    const { texte, essai } = await texteDeValidation();
    expect(estValidation(await empreinte(texte))).toBe(true);
    expect(nettoyer(texte)).not.toBeNull();
    expect(texte).toContain(`essai numéro ${essai}`);
  });

  it('la bonne réponse vient du tri, dans un sens puis dans l’autre', async () => {
    const f = await faitsDuPariValidation(WEB);
    const lignes = [...WEB, { text: f.texte }];
    const aller = await trier(lignes, 'web_fr');
    const retour = await trier([...lignes].reverse(), 'web_fr');
    expect(f.aller).toBe(aller.at(-1)!.validation);
    expect(f.retour).toBe(retour[0].validation);
    expect(f.uneSur).toBe(Math.round(1 / PART_VALIDATION));
    const choix = await choixValidation(WEB);
    expect(choix.find((c) => c.juste)?.texte).toBe('Encore dans la validation');
    expect(choix.map((c) => c.texte)).toStrictEqual([
      'Encore dans la validation',
      `Au hasard${FINE}: une fois sur 200`,
      'Dans l’entraînement, cette fois',
    ]);
  });
});

describe('le pari « part »', () => {
  it('la tranche juste est celle de la part des documents du web gardés dans l’aperçu', () => {
    const web = APERCU.sources.web_fr;
    const choix = choixPartGardee(APERCU);
    expect(choix.map((c) => c.texte)).toStrictEqual([...TRANCHES_PART]);
    expect(choix.findIndex((c) => c.juste)).toBe(trancheDeLaPartGardee(web.gardes / web.lus));
    expect(choix.find((c) => c.juste)?.texte).toBe('Tous');
  });

  it('les bornes des tranches', () => {
    expect(trancheDeLaPartGardee(0)).toBe(0);
    expect(trancheDeLaPartGardee(0.4999)).toBe(0);
    expect(trancheDeLaPartGardee(0.5)).toBe(1);
    expect(trancheDeLaPartGardee(0.9999)).toBe(1);
    expect(trancheDeLaPartGardee(1)).toBe(2);
  });

  it('un aperçu sans document lu arrête la construction', () => {
    const vide = structuredClone(APERCU);
    vide.sources.web_fr.lus = 0;
    vide.sources.web_fr.gardes = 0;
    expect(() => choixPartGardee(vide)).toThrow(/Exemple devenu faux/);
  });
});

describe('chaque pari a exactement un choix juste', () => {
  it('court, licence, doublon, validation, part', async () => {
    for (const choix of [
      choixCourt(texteDe(0)),
      choixLicence(CODE[1]),
      await choixDoublon(texteDe(1), texteDe(2)),
      await choixValidation(WEB),
      choixPartGardee(APERCU),
    ]) {
      expect(choix.filter((c) => c.juste)).toHaveLength(1);
    }
  });
});

describe('l’atelier : les retraits rendus visibles', () => {
  it('les morceaux gardés font exactement le texte normalisé, pour chaque texte de référence', () => {
    for (const t of ATTENDUS.textes) {
      const brut = decoderTexte(t.entree) as string;
      if (brut.length > 1000) continue;
      expect(gardes(brut), t.nom).toBe(normaliser(brut));
    }
  });

  it('un ␍ par retour chariot retiré, un · par autre caractère invisible retiré', () => {
    for (const t of ATTENDUS.textes) {
      const brut = decoderTexte(t.entree) as string;
      if (brut.length > 1000) continue;
      const morceaux = morceauxDuNettoyage(brut);
      const compte = (signe: string) =>
        morceaux.reduce((n, m) => (m.retire && m.texte.startsWith(signe) ? n + m.nombre : n), 0);
      expect(compte(RETOUR_CHARIOT), t.nom).toBe((brut.match(/\r/g) ?? []).length);
      // Les autres contrôles et les moitiés de paire, puis les blancs de fin.
      const controles = (brut.match(/[\u{0}-\u{8}\u{b}\u{c}\u{e}-\u{1f}\u{7f}-\u{9f}\u{d800}-\u{dfff}]/gu) ?? []).length;
      const sansControles = brut.replace(/\r\n/g, '\n').replace(/[\u{0}-\u{8}\u{b}-\u{1f}\u{7f}-\u{9f}\u{d800}-\u{dfff}]/gu, '');
      const blancsDeFin = longueurPointsDeCode(sansControles.normalize('NFC')) - longueurPointsDeCode(normaliser(brut));
      expect(compte(CONTROLE_RETIRE), t.nom).toBe(controles + blancsDeFin);
    }
  });

  it('\\r\\n devient ␍ puis le retour à la ligne, gardé ; un emoji reste entier', () => {
    expect(morceauxDuNettoyage('a\r\nb')).toStrictEqual([
      { texte: 'a', retire: false },
      { texte: RETOUR_CHARIOT, retire: true, nombre: 1 },
      { texte: '\nb', retire: false },
    ]);
    expect(morceauxDuNettoyage('un 😀 et 👍')).toStrictEqual([{ texte: 'un 😀 et 👍', retire: false }]);
    // Des retraits voisins de même sorte font un seul morceau.
    expect(morceauxDuNettoyage('a\u0000\u0007b  ')).toStrictEqual([
      { texte: 'a', retire: false },
      { texte: `${CONTROLE_RETIRE}${CONTROLE_RETIRE}`, retire: true, nombre: 2 },
      { texte: 'b', retire: false },
      { texte: `${CONTROLE_RETIRE}${CONTROLE_RETIRE}`, retire: true, nombre: 2 },
    ]);
  });

  it('un contrôle entre une lettre et son accent : la lettre et l’accent se rejoignent, le · passe après', () => {
    const brut = 'e\u0000́ fin';
    expect(gardes(brut)).toBe(normaliser(brut));
    expect(gardes(brut)).toBe('é fin');
  });

  it('199 caractères : écarté ; 200 : gardé', () => {
    const court = attendu('web.jsonl, ligne 10');
    const juste = attendu('web.jsonl, ligne 9');
    expect(court.longueur).toBe(199);
    expect(juste.longueur).toBe(200);
    expect(etatDuNettoyage(court.texte)).toMatchObject({ longueur: 199, garde: false });
    expect(etatDuNettoyage(juste.texte)).toMatchObject({ longueur: 200, garde: true });
    expect(phraseLongueur(199)).toBe('199 caractères sur les 200 qu’il faut');
    expect(phraseLongueur(1)).toBe('1 caractère sur les 200 qu’il faut');
    expect(verdictDuTexte(etatDuNettoyage(court.texte))).toBe(`Écarté${FINE}: trop court, il manque 1 caractère.`);
    expect(verdictDuTexte(etatDuNettoyage('abc'))).toBe(`Écarté${FINE}: trop court, il manque 197 caractères.`);
    expect(verdictDuTexte(etatDuNettoyage(juste.texte))).toBe(`Gardé${FINE}: il a au moins ${LONGUEUR_MINIMALE} caractères.`);
  });

  it('le côté du texte suit son empreinte', async () => {
    const valide = await texteDeValidation();
    const e = await empreinte(valide.texte);
    expect(coteDuTexte(etatDuNettoyage(valide.texte), e)).toBe('Ce texte servira à la validation.');
    const autre = texteDe(1);
    expect(coteDuTexte(etatDuNettoyage(autre), await empreinte(autre))).toBe('Ce texte servira à l’entraînement.');
    expect(coteDuTexte(etatDuNettoyage('abc'), await empreinte('abc'))).toBe(
      'Écarté, ce texte ne servira ni à l’entraînement, ni à la validation.',
    );
  });

  it('les doublons et le défi', async () => {
    const unix = texteDe(1);
    const e1 = await empreinte(versWindows(unix));
    const e2 = await empreinte(unix);
    expect(messageDoublon(etatDuNettoyage(unix), '', e1, null)).toBe('Écris un autre texte pour comparer les empreintes.');
    expect(messageDoublon(etatDuNettoyage(unix), unix, e1, e2)).toBe(`Même empreinte${FINE}: c’est un doublon.`);
    expect(messageDoublon(etatDuNettoyage('abc'), 'abc ', await empreinte('abc'), await empreinte('abc '))).toBe(
      `Même empreinte${FINE}: ce serait un doublon, mais ce texte est déjà écarté, trop court.`,
    );
    const e3 = await empreinte(texteDe(0));
    expect(messageDoublon(etatDuNettoyage(unix), texteDe(0), e1, e3)).toBe(
      `Empreinte différente${FINE}: ce n’est pas un doublon.`,
    );
    // Le défi : deux textes différents à l'écran, une seule empreinte.
    expect(etatDuDefi(unix, unix, e2, e2)).toEqual({ reussi: false, texte: `Pas encore${FINE}: les deux textes sont les mêmes.` });
    expect(etatDuDefi(unix, '', e2, null)).toEqual({ reussi: false, texte: `Pas encore${FINE}: écris un autre texte.` });
    expect(etatDuDefi(unix, texteDe(0), e2, e3)).toEqual({ reussi: false, texte: `Pas encore${FINE}: les empreintes diffèrent.` });
    const avecEspaces = `${unix}   `;
    expect(etatDuDefi(unix, avecEspaces, e2, await empreinte(avecEspaces))).toEqual({
      reussi: true,
      texte: `Défi réussi${FINE}: deux textes différents, une seule empreinte. Une fois nettoyés, ils sont identiques.`,
    });
  });

  it('100 000 caractères se nettoient et se montrent en moins de 200 ms (médiane de 5 essais)', () => {
    const ligne = `${'Le forgeron frappe le fer. '.repeat(3)}\n`;
    const brut = versWindows(ligne.repeat(Math.ceil(100_000 / ligne.length))).slice(0, 100_000);
    const durees: number[] = [];
    for (let essai = 0; essai < 5; essai++) {
      const debut = performance.now();
      etatDuNettoyage(brut);
      durees.push(performance.now() - debut);
    }
    durees.sort((a, b) => a - b);
    expect(durees[2], durees.map((d) => d.toFixed(1)).join(', ')).toBeLessThan(200);
  });
});

describe('le frontmatter du chapitre 1.2', () => {
  it('l’acquis « court » dit le seuil de nettoyeur.ts', () => {
    // Le chapitre est un brouillon, puis paraît dans content/ : on le lit là où il est.
    const chemin = ['src/brouillons/chapitres/1-2.mdx', 'src/content/chapitres/1-2.mdx'].find((c) => existsSync(c));
    expect(chemin, 'le chapitre 1.2 est introuvable').toBeDefined();
    const mdx = readFileSync(chemin!, 'utf8');
    const court = /- cle: court\n\s+texte: "([^"]*)"/.exec(mdx)?.[1];
    expect(court).toBe(`Sous ${LONGUEUR_MINIMALE} caractères, un texte est écarté, même sans faute.`);
  });
});

describe('l’atelier : des messages seulement avec des empreintes à jour', () => {
  const calculee = async (pour: string) => ({ pour, empreinte: await empreinte(pour), erreur: false });

  it('une empreinte calculée pour un autre texte : aucun message (l’atelier garde ceux d’avant)', async () => {
    const texte = texteDe(1);
    const brut = versWindows(texte);
    const a = await calculee(brut);
    const b = await calculee(texte);
    // Le cas de la relecture : le même texte dans les deux champs, puis une lettre tapée dans le second.
    const avant = messagesDeLAtelier(etatDuNettoyage(brut), brut, texte, texte, a, b)!;
    expect(avant.defi).toEqual({ reussi: false, texte: `Pas encore${FINE}: les deux textes sont les mêmes.` });
    expect(messagesDeLAtelier(etatDuNettoyage(brut), brut, texte, `${texte}x`, a, b)).toBeNull();
    // Une lettre dans le premier : son empreinte est celle de l'ancien texte.
    const nouveau = versWindows(`${texte}y`);
    expect(messagesDeLAtelier(etatDuNettoyage(nouveau), nouveau, `${texte}y`, texte, a, b)).toBeNull();
    // Pas encore d'empreinte du tout.
    expect(messagesDeLAtelier(etatDuNettoyage(brut), brut, texte, texte, null, b)).toBeNull();
    expect(messagesDeLAtelier(etatDuNettoyage(brut), brut, texte, texte, a, null)).toBeNull();
  });

  it('à jour : les messages du côté, du doublon et du défi', async () => {
    const texte = texteDe(1);
    const brut = versWindows(texte);
    const a = await calculee(brut);
    const etat = etatDuNettoyage(brut);
    expect(messagesDeLAtelier(etat, brut, texte, '', a, null)).toEqual({
      cote: coteDuTexte(etat, a.empreinte),
      doublon: 'Écris un autre texte pour comparer les empreintes.',
      defi: { reussi: false, texte: `Pas encore${FINE}: écris un autre texte.` },
    });
    const autre = `${texte}   `;
    const b = await calculee(autre);
    expect(messagesDeLAtelier(etat, brut, texte, autre, a, b)).toEqual({
      cote: coteDuTexte(etat, a.empreinte),
      doublon: `Même empreinte${FINE}: c’est un doublon.`,
      defi: etatDuDefi(texte, autre, a.empreinte, b.empreinte),
    });
    expect(etatDuDefi(texte, autre, a.empreinte, b.empreinte).reussi).toBe(true);
  });

  it('sans crypto.subtle : l’atelier dit qu’il ne peut ni situer ni comparer', () => {
    const texte = texteDe(1);
    const etat = etatDuNettoyage(texte);
    const a = { pour: texte, empreinte: null, erreur: true };
    expect(coteDuTexte(etat, null)).toBe(COTE_SANS_EMPREINTE);
    expect(coteDuTexte(etatDuNettoyage('abc'), null)).toBe('Écarté, ce texte ne servira ni à l’entraînement, ni à la validation.');
    expect(messagesDeLAtelier(etat, texte, texte, 'autre', a, { pour: 'autre', empreinte: null, erreur: true })).toEqual({
      cote: COTE_SANS_EMPREINTE,
      doublon: DOUBLON_SANS_EMPREINTE,
      defi: { reussi: false, texte: DEFI_SANS_EMPREINTE },
    });
    expect(EMPREINTE_IMPOSSIBLE).toBe('impossible à calculer dans ce navigateur');
  });
});
