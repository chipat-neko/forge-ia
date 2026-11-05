"""Un premier réseau de neurones : le Python du chapitre 0.5.

- `neurone` : un neurone à seuil, et le meilleur réglage qu'il trouve pour les portes ET, OU et OU exclusif ;
- `a_la_main` : un réseau 2-2-1 à sigmoïdes, entraîné sur le OU exclusif en Python pur ;
- `avec_pytorch` : le même réseau dans PyTorch, en float64, avec les mêmes poids de départ ;
- `appareil` : choisir où calculer (copie exacte de celui du projet 0.3) ;
- `nombres` : écrire les nombres à la française, dont « 3,1 × 10⁻¹⁷ » ;
- `attendus` : écrire tests/attendus.json, que lit le chapitre.

Ce fichier n'importe rien : PyTorch n'est chargé que par `avec_pytorch` et `appareil`.
"""
