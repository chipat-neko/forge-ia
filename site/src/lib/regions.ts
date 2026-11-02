// Extraction des régions de code : les extraits montrés dans les chapitres
// sont tirés des fichiers testés des projets, jamais recopiés. Une région est
// un bloc de lignes encadré par deux commentaires, dans le fichier Python :
//
//   # region: choisir
//   def paire_la_plus_frequente(...): ...
//   # fin: choisir
//
// Les marqueurs peuvent être au début de la ligne ou indentés.

const MARQUEUR = /^\s*#\s*(?:region|fin):\s*\S+\s*$/;

/** Le motif d'un marqueur donné, `region` ou `fin`, pour une région donnée. */
function marqueur(sorte: 'region' | 'fin', nom: string): RegExp {
  // Le nom est pris tel quel : « . » ne veut pas dire « n'importe quel nom ».
  const nomLitteral = nom.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return new RegExp(`^\\s*#\\s*${sorte}:\\s*${nomLitteral}\\s*$`);
}

/** Nombre d'espaces ou de tabulations au début de la ligne. */
function indentation(ligne: string): number {
  return ligne.length - ligne.trimStart().length;
}

/**
 * Renvoie les lignes du fichier entre `# region: <nom>` et `# fin: <nom>`.
 *
 * - Les lignes de marqueurs sont retirées, y compris celles des régions
 *   imbriquées (leur code reste).
 * - L'indentation commune est enlevée : le code part du bord gauche. Les
 *   lignes vides ne comptent pas pour la calculer, et restent vides.
 * - Les fins de ligne Windows sont acceptées ; le résultat n'a que des `\n`.
 *
 * Si la région est introuvable ou n'est pas fermée, la fonction lève
 * `Région introuvable : <nom> dans <fichier>` : une page ne doit jamais
 * être construite avec un extrait manquant.
 */
export function extraireRegion(source: string, nom: string, fichier = '?'): string {
  const lignes = source.split(/\r?\n/);
  const ouverture = marqueur('region', nom);
  const fermeture = marqueur('fin', nom);

  const debut = lignes.findIndex((ligne) => ouverture.test(ligne));
  const fin = debut === -1 ? -1 : lignes.findIndex((ligne, i) => i > debut && fermeture.test(ligne));
  if (debut === -1 || fin === -1) {
    throw new Error(`Région introuvable : ${nom} dans ${fichier}`);
  }

  const code = lignes.slice(debut + 1, fin).filter((ligne) => !MARQUEUR.test(ligne));
  const pleines = code.filter((ligne) => ligne.trim() !== '');
  const commune = pleines.length === 0 ? 0 : Math.min(...pleines.map(indentation));
  return code.map((ligne) => (ligne.trim() === '' ? '' : ligne.slice(commune))).join('\n');
}
