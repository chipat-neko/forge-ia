"""Le code de la vague 2 : exécuter le code que ton IA écrit, et compter ses réussites.

- `execution` : exécute un programme Python généré dans un sous-processus limité (délai, mémoire, un seul
  processus sous Windows, dossier jetable), et dit s'il a réussi ;
- `passk` : l'estimateur sans biais de pass@k de l'article Codex, la chance qu'une de k réponses passe les tests.

L'évaluation du code du chapitre 1.10 (HumanEval et sa version française) s'appuie sur les deux.
"""
