# La Forge IA : document de conception

Date : 02/11/2026. Dossier local : `D:\creation-ia`. Dépôt GitHub à créer : `chipat-neko/forge-ia`, publié sur `https://chipat-neko.github.io/forge-ia/`.

Ce document distingue trois choses :

- **Décidé par l'utilisateur** : ne pas changer sans lui redemander.
- **Mon choix** : décidé par l'assistant pendant le cadrage, contestable.
- **Laissé au constructeur** : à régler pendant la réalisation.

## 1. Intention

Un site web en français qui explique **comment faire, concrètement**, pour créer une IA de zéro. On construit le cœur (un modèle de langage), on trouve et prépare les données, on entraîne, puis on ajoute une à une les capacités : conversation, raisonnement, code, images, vidéo, outils, agents, gestion de projets en autonomie.

Le site est d'abord le guide de l'utilisateur lui-même, et il doit rester lisible par un débutant. Il ne s'agit pas d'une encyclopédie mais d'un **parcours** : on comprend chaque brique en la fabricant.

**Ce qui doit en ressortir** (décidé) : la compréhension, et le « comment faire quoi » pour créer une IA de zéro.

**La réussite**, dans les mots de l'utilisateur : « ça c'est vraiment bien fait, ça me donne envie d'y retourner, car on voit bien que c'est fait pour apprendre ».

## 2. Public (décidé)

1. L'utilisateur, qui veut vraiment construire son IA.
2. Des débutants : on ne suppose rien, d'où la Partie 0 complète.

## 3. Objectifs, non-objectifs, anti-objectifs

**Objectifs**

- Un parcours complet, des bases jusqu'à une IA qui converse, code, crée des images et des vidéos, utilise des outils et mène des projets.
- Tout se fait **pour de vrai, en petit**, sur le PC de l'utilisateur. Chaque étape montre aussi la version à grande échelle.
- Un code complet et **qui marche** : jamais de pseudo-code, jamais d'exemple qui plante.
- Des pages qui font participer le lecteur : paris, manipulations, démos.

**Non-objectifs**

- Rivaliser avec les grands modèles. Le site dit honnêtement ce qu'un PC permet et ce qu'il faudrait pour aller plus loin.
- Un site multilingue : il est en français seulement.
- Des comptes utilisateurs, des commentaires ou des statistiques de visite (mon choix).

**Anti-objectifs**, qui feraient échouer le projet même si tout fonctionne :

- Un site qui a l'air « fait par IA » : gabarit de documentation générique, dégradés « tech », emojis décoratifs, encadrés à bordure colorée, cartes arrondies identiques.
- Du code publié sans avoir tourné, ou des extraits qui diffèrent du code testé.
- Des affirmations fausses ou dépassées sur les modèles, les données, les prix ou le matériel.
- Faire croire qu'un modèle entraîné sur un PC atteint le niveau d'un grand labo.

## 4. Contenu : le plan validé (décidé)

L'utilisateur a validé ce plan le 02/11/2026. Il pourra s'enrichir plus tard.

**Partie 0, Les bases**

- 0.1 Python pour l'IA
- 0.2 Les maths utiles (vecteurs, matrices, dérivées, probabilités)
- 0.3 Installer son poste : GPU, CUDA, PyTorch
- 0.4 Tenseurs et calcul sur GPU
- 0.5 Premier réseau de neurones, à la main puis avec PyTorch

**Partie 1, Créer son IA de zéro** (mise en avant : c'est la partie principale du site)

- *Le cœur : un modèle de langage*
  - 1.1 Ce qu'est vraiment un modèle de langage
  - 1.2 Les données : où les trouver, les nettoyer, les licences
  - 1.3 Le tokenizer (BPE)
  - 1.4 Le transformer, pièce par pièce
  - 1.5 Le pré-entraînement sur ton GPU
  - 1.6 Évaluer son modèle
- *Le rendre utile*
  - 1.7 Apprendre à converser (instructions, format chat)
  - 1.8 L'aligner : préférences et récompenses
  - 1.9 Le faire raisonner
  - 1.10 Le faire coder
- *Voir et créer des images*
  - 1.11 Compresser les images (autoencodeur)
  - 1.12 Générer des images par diffusion
  - 1.13 Guider l'image par le texte
  - 1.14 Passer à la vidéo
  - 1.15 Comprendre les images (vision)
- *Agir seul*
  - 1.16 Les outils (appeler des fonctions)
  - 1.17 La boucle d'agent et la mémoire
  - 1.18 Plusieurs agents qui coopèrent
  - 1.19 Gérer un projet de A à Z en autonomie
- *Le mettre en service*
  - 1.20 Accélérer, compresser, servir le modèle
  - 1.21 Sécurité et garde-fous

**Partie 2, Hybride**

- 2.1 Choisir un modèle ouvert
- 2.2 L'affiner sur 16 Go (LoRA, QLoRA)
- 2.3 Affiner un générateur d'images
- 2.4 La vidéo à partir de modèles ouverts

**Partie 3, Assemblage**

- 3.1 Faire tourner des modèles en local
- 3.2 Brancher texte, image et vidéo
- 3.3 Agents et outils (MCP…)
- 3.4 Un système qui mène des projets seul

**Annexes** : glossaire ; annuaire des données, modèles et outils (avec licences) ; calculateur de coût ; matériel (quoi acheter, quoi louer).

**Les trois approches** (décidé) : de zéro, hybride et assemblage ont chacune leur partie bien délimitée, et la Partie 1 est mise en avant.

**Une seule IA qui grandit** (décidé le 02/11/2026) : la Partie 1 fabrique **une seule IA**, « ton IA », reprise de chapitre en chapitre, et non un modèle séparé par chapitre. Conséquences pour la construction :

- **Un seul modèle de langage tout au long du parcours** : il naît en 1.5 avec le tokenizer de 1.3, puis il est affiné de 1.7 à 1.10 (conversation, alignement, raisonnement, code). C'est encore lui qui sert d'agent de 1.16 à 1.19, puis qui est accéléré et servi en 1.20.
- **Langue de ton IA** (décidé le 03/11/2026) : **français uniquement, plus du code**. Le tokenizer de ton IA et les données de pré-entraînement sont donc du français et du code, sans anglais visé.
- **Le tokenizer de 1.3 prévoit dès le départ toute la suite** : les jetons spéciaux du format de conversation, des appels d'outils et des messages système, et une réserve de jetons libres pour plus tard. Les données de pré-entraînement contiennent du code, pour préparer 1.10.
- **Images et vidéo** (1.11 à 1.14) : elles ont leurs propres petits modèles, entraînés de zéro. En 1.15 et dans « agir seul », ils sont branchés à ton IA : elle sait les appeler comme des outils, et la vision lui donne des yeux. Mon choix, qui découle de la recommandation acceptée.
- **Un paquet Python commun** (`forge`) regroupe les briques partagées : tokenizer, modèle, chargement des données, sauvegarde et reprise. Chaque projet de chapitre s'appuie dessus et ajoute sa propre étape.
- **Les modèles s'enchaînent dans les versions GitHub**. Chaque version du modèle (`ton-ia-1.5`, `ton-ia-1.7`…) est publiée avec ses réglages. Un chapitre peut repartir de la version publiée, et le lecteur n'a pas besoin d'avoir tout refait.
- **Le format du tokenizer et l'architecture sont figés à la fin de la vague 1**, une fois validés. Avant de les figer, le constructeur vérifie qu'ils couvrent les besoins connus des vagues 2 à 4.

**Ce que peut faire un modèle maison** (mon hypothèse, présentée à l'utilisateur sans objection) : un modèle entraîné de zéro sur 16 Go ne pourra pas mener seul un vrai projet. Dans la Partie 1, les étapes 1.16 à 1.19 construisent donc toute la mécanique (outils, boucle d'agent, coopération, gestion de projet) et la montrent sur des tâches simples. La version vraiment capable se fait dans les Parties 2 et 3, avec des modèles ouverts. Le site le dit clairement.

## 5. Le gabarit d'un chapitre

Ce gabarit vient de la maquette retenue, la fusion B « plus d'énergie » (`docs/maquettes/maquette-10-fusion-energie.html`). Il mélange la maquette 1, « Texte vivant », et la maquette 6, « Prédis d'abord » (décidé). Chaque chapitre le suit, en l'adaptant à son sujet.

1. **Barre du haut, fixe et opaque** (corriger la transparence de la maquette) : nom du site, position (« Partie 1, chapitre 1.3 sur 21 »), barre des étapes du chapitre, pastilles « Ce que tu sais ».
2. **Ouverture** : titre, chapeau, puis l'objet du chapitre montré tout de suite. Pour le tokenizer, c'est la phrase déjà découpée, avec ses numéros.
3. **Étapes numérotées** : un grand numéro dans la marge de gauche, coché une fois l'étape faite. Le texte courant tient dans une colonne de lecture confortable.
4. **Notes dans la marge de droite** sur grand écran. Sur mobile, elles passent sous le paragraphe.
5. **Paris avant chaque résultat clé** : une question bien visible et des choix francs. Les bonnes réponses sont **calculées par le même code que la démo**, jamais écrites à la main. La révélation dit juste ou faux (menthe ou corail) et explique pourquoi. La manipulation concernée reste floue et inerte tant qu'on n'a pas parié.
6. **Nombres manipulables dans les phrases** : on les fait glisser à la souris, au doigt ou au clavier, et tout ce qui en dépend se recalcule.
7. **L'atelier** : la démo du chapitre.
8. **Le code** : extraits expliqués ligne par ligne, puis un lien vers le projet complet du dépôt et vers le notebook Colab.
9. **L'encadré « Et chez un grand labo ? »** : la même étape à grande échelle (matériel, données, durée, coût), avec des chiffres sourcés et datés.
10. **Un défi facultatif.**
11. **« Ce que tu sais maintenant »** : la liste complète des acquis, qui se remplit au fil des paris.
12. **Chapitre précédent et chapitre suivant.**

**Progression** (mon choix) : les paris faits, les acquis et les chapitres terminés sont gardés dans le navigateur (`localStorage`), sans compte, et on peut les effacer.

## 6. Allure

La direction est décidée : la fusion B. Les valeurs ci-dessous sont reprises de la maquette.

**Couleurs**

| Rôle | Valeur |
| --- | --- |
| Papier | `#FFFFFF` |
| Encre | indigo `#232057` |
| Encre douce | `#5B5888` |
| Lavande | `#8F8CB8` |
| Brume | `#E6E5F0` / `#F5F4FA` |
| Soleil (ce qui se manipule) | `#FFC93C`, vif `#FFB800`, pâle `#FFF4D6` |
| Juste, pour le texte | menthe `#1C6E58`, fond `#E2F5EF` |
| Faux, pour le texte | corail `#B8342D`, fond `#FDECEA` |
| Teintes alternées des jetons | `#E4E2F4` / `#F2E9D8` |

**Règle** : le jaune soleil est réservé à ce qui se manipule.

**Typographie** :

- Gabarito pour les titres et les chiffres ;
- Newsreader pour le texte courant ;
- une police à chasse fixe pour le code, au choix du constructeur dans le même esprit.

Les polices sont auto-hébergées (mon choix), sans appel à Google Fonts sur le site publié.

**Interdits** : voir les anti-objectifs (section 3). S'y ajoutent :

- les étiquettes en capitales espacées au-dessus des titres ;
- les méta-informations séparées par des points médians ;
- les « → » collés aux boutons ;
- les animations d'entrée sur chaque section.

Le mouvement est réservé aux réponses à une action du lecteur.

**Plancher de qualité** :

- lisible dès 390 px de large, sans débordement horizontal ;
- focus clavier visible, `prefers-reduced-motion` respecté ;
- contraste AA ;
- typographie française (espaces fines insécables devant `; : ! ?` et dans les guillemets).

**Pages encore à maquetter** (laissé au constructeur, mais à montrer à l'utilisateur avant de les construire, dans la même direction) :

- la page d'accueil, avec le plan du parcours et la progression ;
- les pages de partie ;
- les annexes ;
- la recherche ;
- la page 404.

Les 8 premières maquettes restent des références d'idées. On peut leur emprunter un élément si on le fond dans la direction B : la carte du parcours de la maquette 7 pour l'accueil, par exemple.

## 7. Démos interactives (décidé)

Elles tournent toutes dans le navigateur, sans serveur, car GitHub Pages ne sert que des fichiers.

| Démo | Chapitre | Contenu |
| --- | --- | --- |
| Tokenizer en direct | 1.3 | Taper une phrase, régler le nombre de fusions, voir les jetons, leurs numéros et les fusions apprises. |
| Mini-modèle qui apprend | 1.5 (avec un avant-goût en 0.5) | Un tout petit modèle s'entraîne dans le navigateur : on voit l'erreur baisser et le texte généré devenir cohérent. |
| Animations des mécanismes | 1.4 attention, 1.12 diffusion, 1.17 boucle d'agent, et d'autres où c'est utile | Visualisations animées pilotées par le lecteur. |
| Calculateur de coût | Annexes, et lié depuis 1.5 et les encadrés « labo » | Choisir une taille de modèle, une quantité de données et un matériel ; il estime la mémoire, la durée et le prix. Les formules et les prix sont sourcés et datés. |

**Cohérence des moteurs** (exigence) : quand une démo du navigateur refait ce que fait un projet Python, les deux donnent **exactement** le même résultat sur les mêmes entrées. Des tests le vérifient.

Par exemple, en cas d'égalité de fréquence, le BPE doit départager les paires de la même façon en JS et en Python. Ce n'est pas encore le cas dans les maquettes : en cas d'égalité, `bpe.js` prend la première paire dans l'ordre alphabétique, alors que l'exemple Python garde la première rencontrée.

Cette exigence d'égalité exacte vaut pour les calculs déterministes : découpage du texte, numéros des jetons, calcul des réponses aux paris, et tirage à partir des mêmes probabilités avec la même graine. Pour un **entraînement**, comme le mini-modèle qui apprend dans le navigateur, une égalité au bit près entre navigateur et PyTorch est impossible. On demande seulement que la courbe d'erreur ait la même allure, avec une tolérance annoncée (mon choix).

La technique du mini-modèle dans le navigateur (WebGPU, TensorFlow.js ou une petite différentiation automatique maison) est laissée au constructeur. Contraintes : fluide sur un PC ordinaire, avec un repli si WebGPU est absent.

## 8. Le code (décidé : tout ce qui peut être expliqué, et fonctionnel)

Le code se présente sous trois formes, toutes demandées par l'utilisateur :

- **Extraits expliqués ligne par ligne** dans les pages.
- **Un projet complet par étape** dans le dépôt (`projets/<numéro>-<nom>/`), pour tout refaire de bout en bout sur son PC.
- **Un notebook Colab par étape** (`notebooks/`), qui s'ouvre depuis le site.

**Règles** :

- **Une seule source** (mon choix) : les extraits du site sont tirés au moment de la construction des fichiers du projet testé. On ne les recopie pas à la main. Le mécanisme (régions balisées dans les fichiers, par exemple) est laissé au constructeur.
- **Rien n'est publié sans avoir tourné** :
  - chaque projet a des tests rapides (pytest, quelques minutes au plus sur CPU) ;
  - il a été lancé en entier sur la RTX 5070 Ti ;
  - son notebook a été exécuté de bout en bout sur l'offre gratuite de Colab.
- **Les notebooks Colab** (décidé) :
  - **l'utilisateur les lance lui-même**, tous, sur Colab avec son compte Google, à chaque vague et avant la publication ;
  - le constructeur les prépare et les teste d'abord en local ;
  - il remet à l'utilisateur une liste : quel notebook, durée attendue, résultat attendu ;
  - la publication d'une vague attend ce retour.
- **Pause et reprise des entraînements** (décidé) : tout entraînement long peut être arrêté à tout moment, puis repris plus tard au même point.
  - On sauvegarde régulièrement le modèle, l'optimiseur, le planning du taux d'apprentissage, la position dans les données et l'état du hasard.
  - Une commande de reprise est montrée aux lecteurs.
  - Le site apprend aussi cette technique dans le chapitre 1.5.
- **Les vrais résultats sont montrés** : courbes d'erreur, textes et images générés, durées mesurées sur la RTX 5070 Ti.
- Le code pédagogique a des noms et des commentaires en français, comme dans les maquettes (mon choix).
- Les environnements Python sont reproductibles, avec des versions figées (outil au choix du constructeur, `uv` conseillé). PyTorch doit être compilé pour CUDA 12.8 ou plus, car la RTX 5070 Ti est un GPU Blackwell.
- **Modèles entraînés** (décidé) : ils sont publiés en pièces jointes des versions GitHub (GitHub Releases) du dépôt, jusqu'à 2 Go par fichier. Les notebooks Colab les téléchargent pour éviter de tout réentraîner.
- **Données** : elles sont téléchargées par des scripts, jamais versionnées dans le dépôt. Leur licence est indiquée pour chaque jeu, et la taille de l'échantillon est adaptée au matériel.

## 9. Honnêteté sur l'échelle et l'actualité

- Chaque étape de la Partie 1 se fait en petit sur le PC. L'encadré « Et chez un grand labo ? » donne l'ordre de grandeur réel, avec ses sources.
- **Recherche web avant chaque partie** (décidé) : on vérifie les modèles, les jeux de données, les outils, les prix et le matériel actuels. Les sources sont citées dans les pages, avec une date « vérifié le ».

## 10. Fabrication technique (mes choix, sauf mention)

- **Le générateur de site** : Astro en sortie statique, avec les chapitres en MDX.
  - Pas de Starlight ni d'autre thème de documentation : leur gabarit « menu à gauche + contenu » est précisément ce que l'utilisateur a rejeté.
  - La mise en page est entièrement propre au site.
- **Les démos** : îlots interactifs en TypeScript, en Svelte ou en JS natif selon le choix du constructeur. La logique est testée à part de l'affichage (Vitest).
- **La recherche** : Pagefind, un index statique qui ne demande aucun serveur.
- **La coloration du code** : Shiki (intégré à Astro), avec un thème accordé à la direction B.
- **La publication** : GitHub Actions construit le site et le publie sur GitHub Pages à chaque poussée sur la branche principale.
- **Les tests du site** : des parcours Playwright avec le Chrome installé (`channel: 'chrome'`). Ils couvrent chaque démo, les paris, l'affichage mobile à 390 px et l'accessibilité avec axe. Les tests rapides des projets Python tournent aussi en intégration continue, sur CPU.
- **Les ports locaux** :
  - 8530 pour le serveur Astro (développement et aperçu) ;
  - 8531 pour le serveur lancé par les parcours Playwright.

  Ils sont choisis parce qu'ils sont libres dans `~/.claude/PORTS.md`. Il faut les inscrire dans `PORTS.md` du projet et dans `~/.claude/PORTS.md`, et ajouter dans la mémoire partagée une entrée « ports » au format demandé, si le serveur mémoire répond.
- **Le dépôt** : il est public, car GitHub Pages est gratuit seulement pour un dépôt public.
  - L'assistant crée `chipat-neko/forge-ia` (décidé).
  - Le dossier `.superpowers/` est ignoré par git.
  - Les maquettes sont versées dans `docs/maquettes/`, car l'utilisateur veut toutes les garder.
- **Les licences** (décidé) : MIT pour le code, CC BY 4.0 pour les textes.

## 11. Contraintes de la machine et de l'environnement

- Le PC a une RTX 5070 Ti de 16 Go, un Ryzen 7 9800X3D (8 cœurs, 16 fils), 62 Go de mémoire vive et Windows 11.
- **Espace disque au 02/11/2026** : 8 Go libres sur D:, 49 Go sur E:, 171 Go sur C:.
  - **L'utilisateur libère de la place sur D:** (décidé). Les données, les points de sauvegarde, les environnements Python et les caches (uv, Hugging Face, pip) vont sur D:, **hors du dépôt**, dans `D:\forge-ia-donnees` (mon choix du nom). Le chemin est réglable par une seule variable d'environnement, `FORGE_DONNEES`.
  - **Première étape de la vague 1** : vérifier qu'il y a assez de place sur D:. Estimation : 30 à 40 Go pour la vague 1, à affiner avec le plan. S'il n'y en a pas assez, s'arrêter et le dire à l'utilisateur.
- **Système** (mon choix) :
  - les projets tournent d'abord **sous Windows natif**, comme le PC de l'utilisateur ; les commandes sont données pour PowerShell ;
  - WSL2 n'est introduit qu'au chapitre où un outil l'exige (par exemple vLLM, pour servir le modèle en 1.20 ou en Partie 3), avec son installation expliquée à ce moment-là ;
  - Linux et macOS sont signalés quand une commande diffère.
- **Durée d'entraînement** (décidé) : **pas de limite de durée** pour l'entraînement principal de ton IA (1.5), à condition de pouvoir l'arrêter et le reprendre plus tard (voir la section 8).
  - Avant de lancer, le constructeur propose à l'utilisateur la taille du modèle, la quantité de données et la durée estimée, chiffres mesurés à l'appui. C'est la règle des travaux de plus de 30 minutes ci-dessous.
  - Pour les lecteurs, chaque entraînement long existe aussi en version courte (environ une heure), et en version téléchargeable depuis les versions GitHub.
- Règle de l'utilisateur pour tout travail estimé à plus de 30 minutes :
  1. faire d'abord un essai chronométré sur GPU et sur CPU, en utilisant tous les cœurs sur CPU ;
  2. montrer les chiffres à l'utilisateur et lui demander lequel utiliser ;
  3. pendant le travail, vérifier que les cœurs prévus sont bien utilisés.
- La mémoire partagée (mcp-memory-service) reçoit les jalons livrés et les décisions durables, pas l'avancement au jour le jour.

## 12. Livraison par vagues (décidé : par vagues, chacune validée avant la suivante)

| Vague | Contenu |
| --- | --- |
| 1 | Le site en ligne (gabarit, accueil, navigation, recherche, progression), les 4 démos, la Partie 0 entière, les chapitres 1.1 à 1.6 avec leurs projets et notebooks, la première version de l'annuaire des données et du glossaire. Les maquettes d'accueil et des pages de partie sont validées avant d'être construites. |
| 2 | 1.7 à 1.10 (le rendre utile) |
| 3 | 1.11 à 1.15 (images, vidéo, vision) |
| 4 | 1.16 à 1.21 (agir seul, mettre en service) |
| 5 | Partie 2 (hybride) |
| 6 | Partie 3 (assemblage) et le reste des annexes |

Chaque vague commence par sa recherche web. Elle se termine sur des tests verts, une publication sur GitHub Pages, et la validation de l'utilisateur.

## 13. Points ouverts

Aucun point bloquant. La relecture par un constructeur a soulevé six questions, toutes tranchées :

- **Par l'utilisateur** : une seule IA qui grandit, le stockage sur D: après libération de place, les notebooks Colab lancés par l'utilisateur, la durée d'entraînement sans limite avec pause et reprise.
- **Par moi** : la tolérance pour les entraînements dans le navigateur, et Windows natif d'abord, WSL2 ensuite.

À trancher pendant le plan, par le constructeur : la taille exacte de ton IA et de ses données, à proposer à l'utilisateur avec des chiffres mesurés.

## 14. Références

- La maquette retenue : `docs/maquettes/maquette-10-fusion-energie.html`, avec le moteur `bpe.js`.
- Les autres maquettes, gardées pour leurs idées :
  - 1, Texte vivant ;
  - 2, Couleurs liées ;
  - 3, L'établi ;
  - 4, Planches ;
  - 5, Carnet d'atelier ;
  - 6, Prédis d'abord ;
  - 7, Plan de métro ;
  - 8, Manuel rétro ;
  - 9, fusion A « lecture d'abord ».
- Les inspirations :
  - les articles interactifs de Bartosz Ciechanowski ;
  - Distill ;
  - Red Blob Games ;
  - les « reactive documents » de Bret Victor ;
  - Brilliant ;
  - Transformer Explainer (Georgia Tech).
