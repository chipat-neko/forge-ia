"""Les problèmes de raisonnement de la vague 2 : générés par programme, avec leur vérification.

- `problemes` : des problèmes de calcul en français, plus faciles que GSM8K, justes par construction ;
- `verification` : lit la réponse d'une sortie de ton IA et la compare à la bonne réponse ;
- `grpo` : le mini-GRPO à la nanochat, qui apprend de ses réponses récompensées si elles sont justes.

Le SFT de raisonnement s'appuie sur les deux premiers, le mini-GRPO de la partie 1.9 sur les trois (sa méthode
d'entraînement, `grpo`, est enregistrée dans `forge.entrainement.methodes`).
"""
