// L'adresse du dépôt public du site, pour les liens vers le code.
export const DEPOT = 'https://github.com/chipat-neko/forge-ia';
/** Le même dépôt sous la forme « propriétaire/nom », pour les liens Colab. */
export const NOM_DU_DEPOT = new URL(DEPOT).pathname.replace(/^\/|\/$/g, '');
