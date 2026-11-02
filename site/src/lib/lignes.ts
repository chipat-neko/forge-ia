// Les lignes qu'une explication vise, écrites dans `data-lignes` :
// « 7 », « 2-6 » (de la ligne 2 à la ligne 6), « 1 5 » ou « 1, 3-4 ».
// Les numéros comptent à partir de 1, dans l'extrait affiché (et non dans le
// fichier d'origine). Utilisé à la construction (pour refuser une ligne qui
// n'existe pas) et par le script du composant CodeExplique (pour les allumer).

const MORCEAU = /^(\d+)(?:-(\d+))?$/;

function morceaux(spec: string): string[] {
  return spec.split(/[\s,]+/).filter((m) => m !== '');
}

/** Les numéros de ligne visés, dans l'ordre, sans doublon. */
export function lignesVisees(spec: string): number[] {
  const liste = morceaux(spec);
  if (liste.length === 0) throw new Error(`Lignes invalides : « ${spec} »`);
  const numeros = new Set<number>();
  for (const morceau of liste) {
    const m = MORCEAU.exec(morceau);
    const debut = m ? Number(m[1]) : 0;
    const fin = m?.[2] === undefined ? debut : Number(m[2]);
    if (!m || debut < 1 || fin < debut) throw new Error(`Lignes invalides : « ${spec} »`);
    for (let n = debut; n <= fin; n++) numeros.add(n);
  }
  return [...numeros];
}

/** Le texte lu aux lecteurs d'écran : « Ligne 7 », « Lignes 2 à 6 », « Lignes 1 et 5 ». */
export function libelleDesLignes(spec: string): string {
  const liste = morceaux(spec).map((m) => m.replace('-', ' à '));
  if (liste.length === 1 && !liste[0].includes(' à ')) return `Ligne ${liste[0]}`;
  const dernier = liste.pop();
  return `Lignes ${liste.length > 0 ? `${liste.join(', ')} et ` : ''}${dernier}`;
}
