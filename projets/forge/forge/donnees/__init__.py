"""Les données de « ton IA » : sources, nettoyage, téléchargement en flux avec reprise, mélange.

Les textes sont lus en flux depuis Hugging Face, sans télécharger les jeux entiers, puis
nettoyés, dédoublonnés et écrits hors du dépôt, sous `FORGE_DONNEES/textes/<dossier>/<source>/`.
"""
