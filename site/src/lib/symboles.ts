// Extraction de code Python par symbole : les extraits montrés dans les
// chapitres sont tirés des fichiers de forge sans y poser de marqueurs
// (forge est en lecture seule). Un symbole est `nom` (une fonction ou une
// classe au niveau du module) ou `Classe.methode`.
//
// Le bloc va de la ligne `def`, `async def` ou `class`, avec les décorateurs
// juste au-dessus, jusqu'à la dernière ligne plus indentée que lui. La
// signature peut tenir sur plusieurs lignes : elle finit au premier `:` hors
// parenthèses et crochets. Les chaînes sur plusieurs lignes (docstrings)
// n'arrêtent jamais le bloc.

const DEFINITION = /^(\s*)(?:async\s+def|def|class)\s+([A-Za-z_]\w*)/;

/** Nombre d'espaces ou de tabulations au début de la ligne. */
function indentation(ligne: string): number {
  return ligne.length - ligne.trimStart().length;
}

interface Etat {
  profondeur: number;
  triple: string | null;
}

/**
 * Lit une ligne à partir de l'état `etat` (modifié : parenthèses ouvertes et
 * guillemets triples ouverts). Renvoie vrai si la ligne, commentaire retiré,
 * finit par `:` hors de toute parenthèse et de toute chaîne.
 */
function lire(ligne: string, etat: Etat): boolean {
  let dernier = '';
  let simple: string | null = null;
  for (let i = 0; i < ligne.length; i++) {
    const c = ligne[i];
    if (etat.triple) {
      if (ligne.startsWith(etat.triple, i)) {
        etat.triple = null;
        i += 2;
        dernier = '"';
      }
      continue;
    }
    if (simple) {
      if (c === '\\') i++;
      else if (c === simple) {
        simple = null;
        dernier = '"';
      }
      continue;
    }
    if (c === '#') break;
    if (c === '"' || c === "'") {
      if (ligne.startsWith(c.repeat(3), i)) {
        etat.triple = c.repeat(3);
        i += 2;
      } else simple = c;
      continue;
    }
    if ('([{'.includes(c)) etat.profondeur++;
    else if (')]}'.includes(c)) etat.profondeur--;
    if (c.trim() !== '') dernier = c;
  }
  return dernier === ':' && etat.profondeur === 0 && etat.triple === null;
}

/** L'indice de la ligne qui ferme la signature commencée à `debut`. */
function finDeSignature(lignes: string[], debut: number, symbole: string, fichier: string): number {
  const etat: Etat = { profondeur: 0, triple: null };
  for (let i = debut; i < lignes.length; i++) {
    if (lire(lignes[i], etat)) return i;
  }
  throw new Error(`Signature de ${symbole} sans « : » dans ${fichier}. Le code a changé : revois le chapitre.`);
}

/** L'indice de la dernière ligne du bloc dont la signature finit à `finSignature`. */
function finDeBloc(lignes: string[], finSignature: number, indentDef: number): number {
  const etat: Etat = { profondeur: 0, triple: null };
  let dernier = finSignature;
  for (let i = finSignature + 1; i < lignes.length; i++) {
    const ligne = lignes[i];
    // Dans une chaîne sur plusieurs lignes, l'indentation ne dit rien.
    const dansUneChaine = etat.triple !== null;
    lire(ligne, etat);
    if (dansUneChaine) {
      dernier = i;
      continue;
    }
    if (ligne.trim() === '') continue;
    if (indentation(ligne) <= indentDef) break;
    dernier = i;
  }
  return dernier;
}

/**
 * Retire la docstring qui ouvre le corps du bloc (le corps commence à la
 * ligne `corps`), et les lignes vides qui la suivent.
 */
function sansDocstring(bloc: string[], corps: number): string[] {
  let i = corps;
  while (i < bloc.length && bloc[i].trim() === '') i++;
  const ouverture = /^\s*[rRuU]?("""|''')/.exec(bloc[i] ?? '');
  if (!ouverture) return bloc;
  const triple = ouverture[1];
  let fin = i;
  let depart = ouverture[0].length;
  while (fin < bloc.length && !bloc[fin].includes(triple, depart)) {
    fin++;
    depart = 0;
  }
  if (fin >= bloc.length) return bloc;
  // Rien d'autre que la fin de la chaîne sur sa dernière ligne, sinon ce n'est pas une docstring seule.
  const reste = bloc[fin].slice(bloc[fin].indexOf(triple, depart) + 3).trim();
  if (reste !== '' && !reste.startsWith('#')) return bloc;
  let suite = fin + 1;
  while (suite < bloc.length && bloc[suite].trim() === '') suite++;
  return [...bloc.slice(0, corps), ...bloc.slice(suite)];
}

/**
 * Renvoie le code du symbole, sans l'indentation commune, avec des `\n`.
 * Sans `docstring: true`, la docstring qui ouvre le corps est retirée.
 *
 * Si le symbole manque, la fonction lève `Symbole introuvable : <symbole> dans
 * <fichier>. Le code a changé : revois le chapitre.` : une page ne doit jamais
 * être construite avec un extrait manquant.
 */
export function extraireSymbole(
  source: string,
  symbole: string,
  fichier = '?',
  options: { docstring?: boolean } = {},
): string {
  const lignes = source.split(/\r?\n/);
  const introuvable = () =>
    new Error(`Symbole introuvable : ${symbole} dans ${fichier}. Le code a changé : revois le chapitre.`);

  const noms = symbole.split('.');
  if (noms.length > 2) throw introuvable();

  // Premier nom : au niveau du module. Second nom : dans le corps de cette classe.
  let debut = -1;
  let borne = lignes.length;
  for (const [rang, nom] of noms.entries()) {
    let trouve = -1;
    for (let i = rang === 0 ? 0 : debut + 1; i < borne; i++) {
      const m = DEFINITION.exec(lignes[i]);
      if (m && m[2] === nom && (rang === 0 ? m[1].length === 0 : m[1].length > 0)) {
        trouve = i;
        break;
      }
    }
    if (trouve === -1) throw introuvable();
    if (rang === 0 && noms.length === 2) {
      borne = finDeBloc(lignes, finDeSignature(lignes, trouve, symbole, fichier), 0) + 1;
    }
    debut = trouve;
  }

  const indentDef = indentation(lignes[debut]);
  const finSig = finDeSignature(lignes, debut, symbole, fichier);
  const fin = finDeBloc(lignes, finSig, indentDef);

  // Les décorateurs juste au-dessus.
  let premiere = debut;
  while (
    premiere > 0 &&
    indentation(lignes[premiere - 1]) === indentDef &&
    lignes[premiere - 1].trimStart().startsWith('@')
  ) {
    premiere--;
  }

  let bloc = lignes.slice(premiere, fin + 1);
  if (!options.docstring) bloc = sansDocstring(bloc, finSig - premiere + 1);
  return bloc.map((ligne) => (ligne.trim() === '' ? '' : ligne.slice(indentDef))).join('\n');
}
