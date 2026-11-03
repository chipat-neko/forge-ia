"""Les 64 jetons spéciaux de « ton IA » et la taille de son vocabulaire.

Un jeton spécial n'est pas un morceau de texte : c'est un signal pour le modèle
(« ici commence un texte », « ici parle l'utilisateur »…). Le tokenizer ne les
produit jamais en lisant du texte, même si le texte contient la chaîne
`<|fin_texte|>` : on les ajoute à la main, par leur identifiant.

Ils occupent toujours les 64 derniers identifiants du vocabulaire. Pour la
taille complète (32 768 jetons) :

- 0 à 255 : les 256 octets ;
- 256 à 32 703 : les 32 448 fusions apprises ;
- 32 704 à 32 767 : les 64 jetons spéciaux, dans l'ordre de `SPECIAUX`.

Cet ordre est figé avec le tokenizer : changer un nom ou sa place changerait le
sens des identifiants pour tous les modèles déjà entraînés.
"""

TAILLE_VOCABULAIRE = 32768
NOMBRE_SPECIAUX = 64
PREMIER_SPECIAL = TAILLE_VOCABULAIRE - NOMBRE_SPECIAUX  # 32 704

_SPECIAUX_NOMMES = (
    "<|debut_texte|>",  # début d'un document
    "<|fin_texte|>",  # fin d'un document (sépare les documents à l'entraînement)
    "<|bourrage|>",  # remplissage, pour mettre des lots à la même longueur
    "<|systeme|>",  # consignes générales d'une conversation
    "<|utilisateur|>",  # ce qu'écrit la personne
    "<|assistant|>",  # ce que répond ton IA
    "<|fin_tour|>",  # fin d'une prise de parole
    "<|appel_outil|>",  # ton IA demande à lancer un outil…
    "<|fin_appel_outil|>",
    "<|resultat_outil|>",  # … et lit ce que l'outil a renvoyé
    "<|fin_resultat_outil|>",
    "<|pensee|>",  # brouillon de raisonnement, avant la réponse
    "<|fin_pensee|>",
    "<|image|>",  # place d'une image (pour plus tard)
    "<|fin_image|>",
    "<|trou_prefixe|>",  # remplir un trou dans du code : ce qui précède,
    "<|trou_suffixe|>",  # ce qui suit,
    "<|trou_milieu|>",  # puis le morceau à écrire
)

# Les places qui restent sont réservées pour des usages futurs, sans changer
# les identifiants de ceux qui existent déjà.
SPECIAUX: tuple[str, ...] = _SPECIAUX_NOMMES + tuple(
    f"<|reserve_{numero:02d}|>" for numero in range(NOMBRE_SPECIAUX - len(_SPECIAUX_NOMMES))
)
