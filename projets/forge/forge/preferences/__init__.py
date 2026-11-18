"""Les préférences de 1.8 : des paires (réponse choisie, réponse rejetée) tirées de ton IA elle-même.

- `invites` : les invites, questions d'entraînement avec des consignes vérifiables, et problèmes de calcul ;
- `noter` : les contrôles programmés qui classent deux réponses (terminée, juste, consignes, français, longueur),
  sans juge ;
- `construction` : deux réponses de ton IA par invite, classées, écrites par paquets repris après une coupure,
  puis le jeu `dpo` que la DPO de 1.8 apprend.

Aucun jeu réservé à l'évaluation n'entre dans une invite : les questions viennent d'une source d'entraînement,
passent la décontamination de `forge.affinage.recettes`, et les problèmes viennent de graines d'entraînement.
"""
