// Les garde-fous des exemples : ce qu'un texte affirme d'un exemple calculé
// (un pari, sa bonne réponse, son explication) est vérifié au moment de la
// construction. Si les données ou le moteur changent et qu'une phrase devient
// fausse, la construction s'arrête avec un message qui dit quoi revoir.

/**
 * La fonction `exiger` d'un module : `exiger(condition, message)` lève
 * « Exemple devenu faux : <message>. Revoir <aRevoir>. » si la condition est
 * fausse. `aRevoir` nomme les fichiers (et les textes) à revoir.
 */
export function exigeur(aRevoir: string): (condition: boolean, message: string) => void {
  return (condition, message) => {
    if (!condition) throw new Error(`Exemple devenu faux : ${message}. Revoir ${aRevoir}.`);
  };
}
