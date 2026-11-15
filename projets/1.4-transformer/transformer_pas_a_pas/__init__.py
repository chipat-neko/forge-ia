"""Le transformer de « ton IA » refait pièce par pièce, en fonctions pures, et comparé à celui de forge.

- `pieces` : chaque pièce du transformer (RMSNorm, RoPE, attention, SwiGLU, bloc, modèle), avec PyTorch ;
- `comparer` : chaque pièce face au module correspondant de forge ;
- `compter` : les paramètres d'une taille de forge, famille par famille ;
- `attendus` : écrire tests/attendus.json, que lit le chapitre.

Ce fichier n'importe rien : sans PyTorch, `python -m transformer_pas_a_pas` le dit en français,
sans trace Python (voir `__main__.py`). On importe chaque module par son nom :
`from transformer_pas_a_pas import pieces`.
"""
