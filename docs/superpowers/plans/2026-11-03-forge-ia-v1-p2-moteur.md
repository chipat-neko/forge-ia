# La Forge IA, vague 1, plan 2 : le moteur de ton IA

> **Pour les agents qui exécutent ce plan :** SOUS-SKILL REQUIS : utiliser superpowers:subagent-driven-development (recommandé) ou superpowers:executing-plans pour réaliser ce plan tâche par tâche. Les étapes utilisent des cases à cocher (`- [ ]`).

**But :** construire et faire tourner sur la RTX 5070 Ti de l'utilisateur la chaîne complète de « ton IA ».

- Les données en français et en code.
- Le vrai tokenizer sur les octets, avec ses jetons spéciaux.
- Le transformer.
- Le pré-entraînement, qu'on peut mettre en pause et reprendre.
- L'évaluation.

Le tout est un paquet Python `forge` testé, qui donne une version courte (environ une heure) et une version principale, dont l'utilisateur choisit la taille d'après des mesures.

**Architecture :**

- Un projet uv `projets/forge/` contient le paquet `forge`, organisé en sous-paquets par étape : `donnees`, `tokenizer`, `modele`, `entrainement`, `evaluation`.
- Une interface en ligne de commande unique (`python -m forge …`) lance chaque étape.
- Toutes les données lourdes vivent hors du dépôt, sous `FORGE_DONNEES`.
- Chaque étape longue écrit de façon atomique et sait reprendre là où elle s'est arrêtée.
- Les projets des chapitres et leurs notebooks (1.2, 1.4, 1.5, 1.6) viennent au plan 5. Ils s'appuieront sur ce paquet.

**Pile technique :**

- Python 3.12 ou plus, uv 0.12.
- PyTorch 2.15.0 : roues CUDA 13.2 (`cu132`) sur le PC, roues CPU en intégration continue.
- `datasets` (Hugging Face, lecture en flux), `regex`, `numpy`, `safetensors`, `psutil`, pytest.

**Spécification :** `docs/superpowers/specs/2026-11-02-forge-ia-design.md`. Plan précédent, livré : `docs/superpowers/plans/2026-11-02-forge-ia-v1-p1-fondations.md`.

## Recherche faite avant ce plan (le 03/11/2026)

- **PyTorch.** La version stable est 2.15.0 (PyPI). Les roues Windows cp312 existent sur `https://download.pytorch.org/whl/cu132` (2.15.0). Le pilote du PC est 621.01 et prend en charge CUDA 13.5, donc `cu132` convient à la RTX 5070 Ti (architecture sm_120).
- **Français du web.** `HuggingFaceFW/fineweb-2`, dossier `data/fra_Latn/train` : 135 fichiers parquet d'environ 4,85 Go, licence ODC-By 1.0, sans formulaire d'accès.
- **Wikipédia en français.** `wikimedia/wikipedia`, configuration `20231101.fr` : 17 fichiers, 4,61 Go, licences CC BY-SA 3.0 et GFDL, sans formulaire.
- **Code.** `codeparrot/github-code-clean` contient le code lui-même, avec un champ `language` et un champ `license` par fichier. Il est sans formulaire, et la licence de la compilation est Apache-2.0. Écartés : `bigcode/the-stack-v2` et `the-stack-dedup`, qui demandent une acceptation de conditions, et `HuggingFaceTB/stack-edu`, qui ne contient que des identifiants à télécharger chez Software Heritage.
- **Évaluation en français.** `manu/french_bench_hellaswag` (validation) et `manu/french_bench_arc_challenge` (test), sans formulaire. Ce sont des traductions automatiques, introduites avec CroissantLLM (arXiv 2402.00786).

## Contraintes globales

- **Ton IA lit et écrit le français et le code**, sans anglais visé. Mélange par défaut : 75 % de web français, 10 % de Wikipédia française, 15 % de code Python sous licence permissive.
- **Licences de code gardées :** `mit`, `apache-2.0`, `bsd-2-clause`, `bsd-3-clause`, `isc`, `unlicense`, `cc0-1.0`.
- **Tokenizer de ton IA :**
  - BPE sur les octets, 32 768 jetons en tout : 256 octets, puis 32 448 fusions (identifiants 256 à 32 703), puis 64 jetons spéciaux (identifiants 32 704 à 32 767).
  - En cas d'égalité à l'apprentissage, il prend la paire `(octets(a), octets(b))` la plus petite dans l'ordre lexicographique.
  - Il est figé à la fin de la vague 1. Son motif et le format de son fichier restent compatibles avec JavaScript (pas de quantificateur possessif), pour qu'un jumeau TypeScript soit possible.
- **Motif de pré-découpage, exact :**
  `[^\r\n\p{L}\p{N}]?\p{L}+(?:['’](?=\p{L}))?|\p{N}{1,3}| ?[^\p{White_Space}\p{L}\p{N}]+[\r\n]*|\p{White_Space}*[\r\n]+|\p{White_Space}+(?!\P{White_Space})|\p{White_Space}+`
- **Jetons spéciaux,** dans cet ordre, à partir de l'identifiant 32 704 :
  `<|debut_texte|>`, `<|fin_texte|>`, `<|bourrage|>`, `<|systeme|>`, `<|utilisateur|>`, `<|assistant|>`, `<|fin_tour|>`, `<|appel_outil|>`, `<|fin_appel_outil|>`, `<|resultat_outil|>`, `<|fin_resultat_outil|>`, `<|pensee|>`, `<|fin_pensee|>`, `<|image|>`, `<|fin_image|>`, `<|trou_prefixe|>`, `<|trou_suffixe|>`, `<|trou_milieu|>`, puis `<|reserve_00|>` à `<|reserve_45|>`.
- **Données hors du dépôt,** sous `FORGE_DONNEES` :
  - par défaut `~/forge-ia-donnees` ; sur le PC de l'utilisateur `D:\forge-ia-donnees` ;
  - caches `UV_CACHE_DIR` et `HF_HOME` placés dedans par `outils/env-forge.ps1`.
- **Ce qui entre dans git :** aucune donnée ni aucun poids, sauf le fichier du tokenizer (`projets/forge/forge/ressources/tokenizer-ton-ia-v1.json`, quelques Mo).
- **PyTorch :** extras uv en conflit, `gpu` (index `cu132`) et `cpu` (index `cpu`). En local : `uv run --extra gpu …` ; en intégration continue : `--extra cpu`.
- **Tout travail long** (téléchargement, encodage, entraînement) est atomique et reprenable. Un fichier n'est jamais tenu pour complet sans son marqueur `.complet`.
- **Règle de l'utilisateur** pour tout travail estimé à plus de 30 minutes :
  1. faire un essai chronométré sur GPU et sur CPU, avec les 16 fils du Ryzen sur CPU ;
  2. montrer les chiffres à l'utilisateur et lui demander lequel utiliser ;
  3. pendant le travail, vérifier que les cœurs prévus sont bien utilisés.
- **Langue du code :** noms et commentaires en français, messages d'erreur en français et utiles (quoi faire ensuite).
- **Commits :** sur `main`, chaque message se termine par `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Le dépôt utilise déjà l'adresse masquée de l'utilisateur. Rien n'est poussé sans accord de l'utilisateur.

## Points à surveiller à la relecture

1. **Interruption** (Ctrl+C, plantage, coupure de courant, mise en veille de Windows) pendant l'entraînement ou pendant l'écriture d'une sauvegarde : la reprise repart du dernier point sûr, et un fichier à moitié écrit n'est jamais pris pour bon. Test en tâche 7.
2. **Disque plein** (D: est juste) pendant le téléchargement, l'encodage ou une sauvegarde : arrêt propre avec un message français qui dit combien de place il manque. Aucun fichier partiel n'est marqué complet. Tests en tâches 4, 5 et 7.
3. **Réseau coupé** ou Hugging Face indisponible au milieu d'un téléchargement : la relance reprend sans doublon ni trou. Test en tâche 4.
4. **Mémoire du GPU déjà occupée** (2,3 Go pris au repos sous Windows, davantage si un jeu ou Unreal tourne) : un manque de mémoire donne un message clair, avec la marche à suivre (réduire le micro-lot), au lieu d'une trace brute. Test en tâche 7.
5. **Texte inhabituel** (fins de ligne Windows, emojis, octets UTF-8 coupés, tabulations, lignes de 100 000 caractères, chaînes qui ressemblent à `<|fin_texte|>`) : l'aller-retour du tokenizer est exact et aucun jeton spécial n'est émis. Test en tâche 3.

---

### Tâche 1 : place sur D: et dossier des données (porte)

**Fichiers :**

- Créer : `outils/env-forge.ps1`

**Interfaces :**

- Produit : la variable `FORGE_DONNEES`, que les tâches suivantes lisent via `forge.chemins`, et le script de session `outils/env-forge.ps1`.

- [ ] **Étape 1 : mesurer la place libre** avec `[math]::Round((Get-PSDrive D).Free/1GB,1)`. S'il y a moins de 35 Go, s'arrêter et prévenir le contrôleur, qui demande à l'utilisateur de libérer de la place. Ne rien supprimer soi-même.
- [ ] **Étape 2 : écrire `outils/env-forge.ps1`,** à charger par `. .\outils\env-forge.ps1`. Pour la session seulement, il fixe :
  - `FORGE_DONNEES = D:\forge-ia-donnees` (si la variable n'est pas déjà définie) ;
  - `UV_CACHE_DIR = $env:FORGE_DONNEES\cache\uv` ;
  - `HF_HOME = $env:FORGE_DONNEES\cache\huggingface`.

  Il crée ces dossiers, puis affiche les trois valeurs et la place libre.
- [ ] **Étape 3 : vérifier.** Commande : `. .\outils\env-forge.ps1`. Attendu : les dossiers existent, et la place affichée est d'au moins 35 Go.
- [ ] **Étape 4 : commit**, message « Environnement de session pour les données de ton IA ».

### Tâche 2 : projet `forge`, PyTorch et chemins

**Fichiers :**

- Créer : `projets/forge/pyproject.toml`, `projets/forge/README.md`, `projets/forge/forge/__init__.py`, `projets/forge/forge/__main__.py`, `projets/forge/forge/chemins.py`
- Test : `projets/forge/tests/test_chemins.py`, `projets/forge/tests/test_torch.py`
- Modifier : `.github/workflows/python.yml`

**Interfaces :**

- Produit, dans `forge/chemins.py` :
  - `racine_donnees() -> Path` : la valeur de `FORGE_DONNEES`, sinon `Path.home() / "forge-ia-donnees"` ;
  - `dossier(*parties: str) -> Path` : crée le dossier au besoin et le renvoie ;
  - `class PlaceInsuffisante(Exception)` ;
  - `verifier_place(octets_requis: int, chemin: Path | None = None) -> None` : lève `PlaceInsuffisante` avec le message « Il manque X Go sur `<lecteur>` : Y Go libres, Z Go nécessaires. Libère de la place, puis relance la même commande : elle reprendra là où elle s'est arrêtée. »
- Produit, dans `forge/__main__.py` : un `argparse` à sous-commandes. Les tâches suivantes y ajoutent `donnees`, `tokenizer`, `encoder`, `mesurer`, `entrainer` et `evaluer`.
- Produit, dans `pyproject.toml` :
  - nom `forge-ia`, paquet `forge` ;
  - dépendances `datasets`, `regex`, `numpy`, `safetensors`, `psutil`, `tomli-w` ;
  - extras `gpu` (`torch==2.15.0` depuis l'index `https://download.pytorch.org/whl/cu132`) et `cpu` (`torch==2.15.0` depuis l'index `https://download.pytorch.org/whl/cpu`), déclarés en conflit selon le motif « extras » de la documentation uv ;
  - groupe de développement `pytest` ;
  - marqueur pytest `gpu`, sauté quand CUDA est absent.

- [ ] **Étape 1 : écrire les tests qui échouent.**

```python
def test_racine_par_defaut(monkeypatch, tmp_path):
    monkeypatch.delenv("FORGE_DONNEES", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert racine_donnees() == tmp_path / "forge-ia-donnees"

def test_racine_variable(monkeypatch, tmp_path):
    monkeypatch.setenv("FORGE_DONNEES", str(tmp_path / "x"))
    assert dossier("tokens", "train") == tmp_path / "x" / "tokens" / "train"
    assert (tmp_path / "x" / "tokens" / "train").is_dir()

def test_place_insuffisante(tmp_path):
    with pytest.raises(PlaceInsuffisante, match="Il manque"):
        verifier_place(10**18, tmp_path)

@pytest.mark.gpu
def test_cuda_sm120():
    assert torch.cuda.is_available()
    assert torch.cuda.get_device_capability(0) == (12, 0)
    x = torch.randn(256, 256, device="cuda", dtype=torch.bfloat16)
    assert torch.isfinite(x @ x).all()
```

- [ ] **Étape 2 : lancer les tests et vérifier qu'ils échouent.** Commande : `. .\outils\env-forge.ps1; cd projets/forge; uv run --extra gpu pytest -q`. Attendu : échec à l'import.
- [ ] **Étape 3 : écrire le projet, `chemins.py` et `__main__.py`,** puis adapter `python.yml`. Pour un projet dont le `pyproject.toml` déclare l'extra `cpu`, le workflow lance `uv run --locked --extra cpu pytest -q` ; les autres projets gardent `uv run --locked pytest -q`.
- [ ] **Étape 4 : lancer les tests et vérifier qu'ils passent.**
  - Commande : `uv run --extra gpu pytest -q`. Attendu : 4 tests passent, dont le test GPU.
  - Commande : `uv run --extra cpu pytest -q`. Attendu : le test GPU est sauté.
- [ ] **Étape 5 : commit**, message « Paquet forge : projet, PyTorch 2.15 cu132/CPU, chemins des données ».

### Tâche 3 : le tokenizer de ton IA (BPE sur les octets)

**Fichiers :**

- Créer : `projets/forge/forge/tokenizer/__init__.py`, `predecoupage.py`, `speciaux.py`, `bpe_octets.py`
- Test : `projets/forge/tests/test_tokenizer.py`

**Interfaces :**

- Produit, dans `predecoupage.py` : `MOTIF_TON_IA: str`, le motif exact des contraintes globales, compilé avec `regex` ; et `pre_decouper(texte: str) -> list[str]`.
- Produit, dans `speciaux.py` : `SPECIAUX: tuple[str, ...]` (les 64 noms, dans l'ordre), `TAILLE_VOCABULAIRE = 32768` et `PREMIER_SPECIAL = 32704`.
- Produit, dans `bpe_octets.py` :
  - `class TokenizerOctets` :
    - attributs `fusions: list[tuple[int, int]]`, `speciaux: dict[str, int]`, `taille_vocabulaire: int` et `premier_special: int` ;
    - `encoder(texte: str) -> list[int]` : n'émet jamais de jeton spécial ;
    - `decoder(ids: Sequence[int]) -> str` : `errors="replace"` uniquement sur une suite d'octets incomplète ;
    - `id_special(nom: str) -> int` ;
    - `octets_du_jeton(i: int) -> bytes` ;
    - `enregistrer(chemin: Path) -> None` et `@classmethod charger(chemin: Path) -> TokenizerOctets`.
  - `entrainer_tokenizer(textes: Iterable[str], taille_vocabulaire: int = 32768, journal: Callable[[str], None] | None = None) -> TokenizerOctets`.
- **Format du fichier :** JSON UTF-8 avec les clés `version` (1), `nom`, `motif`, `fusions` (liste de paires d'identifiants), `speciaux` (nom vers identifiant) et `taille_vocabulaire`.
- **Algorithme imposé :**
  - **Apprentissage :** on compte les pré-mots ; à chaque pas, on fusionne la paire la plus fréquente. En cas d'égalité, on prend la plus petite `(octets(a), octets(b))`. Mise à jour incrémentale, avec un index paire vers mots et un tas à suppression paresseuse ; aucun recomptage complet à chaque fusion.
  - **Encodage :** standard « GPT-2 », en fusionnant d'abord la paire de rang le plus bas, avec un cache par pré-mot.
- Sous-commande : `python -m forge tokenizer --donnees <nom> --taille 32768 --nom ton-ia-v1 --sortie <chemin.json> [--octets-max 300M]`. Elle lit les fragments des trois sources du dossier `<nom>` dans les proportions du mélange, et affiche la progression toutes les 1 000 fusions.

- [ ] **Étape 1 : écrire les tests qui échouent.**

```python
def test_predecoupage():
    assert pre_decouper("L'atelier, c'est 2026 !") == ["L'", "atelier", ",", " c'", "est", " ", "202", "6", " !"]
    assert pre_decouper(" jusqu'à aujourd’hui") == [" jusqu'", "à", " aujourd’", "hui"]
    assert pre_decouper("def f(x):\n    return x**2\n") == ["def", " f", "(x", "):\n", "   ", " return", " x", "**", "2", "\n"]
    assert pre_decouper("Bonjour\r\n\r\nÇa va ? 🙂") == ["Bonjour", "\r\n\r\n", "Ça", " va", " ?", " 🙂"]

def test_speciaux():
    assert len(SPECIAUX) == 64 and SPECIAUX[1] == "<|fin_texte|>" and SPECIAUX[-1] == "<|reserve_45|>"

def test_premiere_fusion_et_departage():
    tok = entrainer_tokenizer(["abab abab"], taille_vocabulaire=256 + 64 + 1)
    assert tok.fusions == [(97, 98)]
    tok2 = entrainer_tokenizer(["ba\nab"], taille_vocabulaire=256 + 64 + 1)  # égalité : (a,b) avant (b,a)
    assert tok2.fusions == [(97, 98)]

TEXTES_BIZARRES = ["Ligne\r\nWindows", "🙂👍🏽 é è ê", "\tdef f():\n\t\treturn 1", "x" * 100_000,
                   "texte <|fin_texte|> au milieu", "", " ", "日本語", "\x00\x01"]

def test_aller_retour_exact_et_aucun_special():
    tok = entrainer_tokenizer(CORPUS_DE_TEST, taille_vocabulaire=1024)
    for t in TEXTES_BIZARRES:
        ids = tok.encoder(t)
        assert tok.decoder(ids) == t
        assert all(i < tok.premier_special for i in ids)

def test_determinisme_et_fichier(tmp_path):
    a = entrainer_tokenizer(CORPUS_DE_TEST, taille_vocabulaire=1024)
    b = entrainer_tokenizer(CORPUS_DE_TEST, taille_vocabulaire=1024)
    assert a.fusions == b.fusions
    a.enregistrer(tmp_path / "t.json")
    c = TokenizerOctets.charger(tmp_path / "t.json")
    assert c.encoder("Le forgeron frappe le métal.") == a.encoder("Le forgeron frappe le métal.")
    assert c.id_special("<|fin_texte|>") == a.id_special("<|fin_texte|>") == a.premier_special + 1

def test_vitesse_apprentissage():
    t0 = time.perf_counter(); entrainer_tokenizer(CORPUS_5_MO, taille_vocabulaire=256 + 64 + 2000)
    assert time.perf_counter() - t0 < 120
```

`CORPUS_DE_TEST` est un petit texte français et Python d'environ 20 Ko, écrit dans `tests/donnees/corpus_test.txt`. `CORPUS_5_MO` est ce texte répété jusqu'à 5 Mo, en variant un mot par ligne pour éviter un seul pré-mot.

Les 64 jetons spéciaux occupent toujours les 64 derniers identifiants : `premier_special = taille_vocabulaire − 64`. Pour la taille complète de 32 768, cela donne 32 704, et 32 705 pour `<|fin_texte|>`, ce que vérifie la tâche 9.

- [ ] **Étape 2 : lancer les tests et vérifier qu'ils échouent.** Commande : `uv run --extra gpu pytest -q tests/test_tokenizer.py`.
- [ ] **Étape 3 : écrire les trois modules.**
- [ ] **Étape 4 : lancer les tests et vérifier qu'ils passent.** Commande : `uv run --extra gpu pytest -q tests/test_tokenizer.py`.
- [ ] **Étape 5 : commit**, message « Tokenizer de ton IA : BPE sur les octets, jetons spéciaux ».

### Tâche 4 : les données (sources, nettoyage, téléchargement en flux avec reprise)

**Fichiers :**

- Créer : `projets/forge/forge/donnees/__init__.py`, `sources.py`, `nettoyage.py`, `telechargement.py`, `melange.py`
- Créer : `docs/donnees.md` (sources, licences et liens, en français)
- Test : `projets/forge/tests/test_donnees.py`

**Interfaces :**

- Consomme : `forge.chemins` (tâche 2).
- Produit, dans `sources.py` :
  - `@dataclass(frozen=True) class Source`, avec les champs `nom`, `depot`, `configuration: str | None`, `dossier_donnees: str | None`, `colonne`, `licence`, `url_licence` et `garder: Callable[[dict], bool]` ;
  - `SOURCES: dict[str, Source]` avec trois entrées :
    - `"web_fr"` : `HuggingFaceFW/fineweb-2`, dossier `data/fra_Latn/train`, colonne `text`, licence ODC-By 1.0 ;
    - `"wikipedia_fr"` : `wikimedia/wikipedia`, configuration `20231101.fr`, colonne `text`, licence CC BY-SA 3.0 ;
    - `"code_python"` : `codeparrot/github-code-clean`, colonne `code`, ne garde que `language == "Python"` et une licence de `LICENCES_PERMISSIVES` ;
  - `LICENCES_PERMISSIVES: frozenset[str]` : les 7 licences des contraintes globales.
- Produit, dans `nettoyage.py` :
  - `nettoyer(texte: str) -> str | None` : forme NFC, `\r\n` devenu `\n`, caractères de contrôle retirés sauf `\n` et `\t`, espaces de fin de texte retirées ; renvoie `None` sous 200 caractères ;
  - `empreinte(texte: str) -> str` : SHA-1 en hexadécimal du texte nettoyé.
- Produit, dans `telechargement.py` : `telecharger(source: Source, octets_max: int, dossier: Path, lecteur: Callable[[Source], Iterator[dict]] | None = None) -> Path`.
  - **Lecteur :** par défaut, `datasets.load_dataset(..., streaming=True)`.
  - **Écriture :** des fragments `fragment-00000.jsonl.gz` d'environ 100 Mo de texte, au format `{"texte": …}`.
  - **Atomicité :** écriture dans un `.tmp`, puis `os.replace`.
  - **État :** `etat.json` contient `documents_lus` et `octets_ecrits`.
  - **Reprise :** à la relance, les `documents_lus` déjà comptés sont sautés, et les empreintes déjà vues ne sont pas réécrites.
  - **Fin :** un fichier `.complet` est écrit quand `octets_max` est atteint ou la source épuisée.
  - **Place :** `verifier_place` est appelé avant chaque fragment, avec une marge de 2 Go.
- Produit, dans `melange.py` :
  - `MELANGE_PAR_DEFAUT = {"web_fr": 0.75, "wikipedia_fr": 0.10, "code_python": 0.15}` ;
  - `repartir(octets_total: int, melange: dict[str, float] = MELANGE_PAR_DEFAUT) -> dict[str, int]` ;
  - `est_validation(empreinte: str, part: float = 0.005) -> bool`, déterministe : il compare l'entier des 8 premiers chiffres hexadécimaux à `part`.
- Sous-commande : `python -m forge donnees --octets 300M --dossier <nom>` télécharge les trois sources selon le mélange.

- [ ] **Étape 1 : écrire les tests qui échouent.** Ils utilisent tous un `lecteur` factice, sans réseau.

```python
def test_filtre_code():
    g = SOURCES["code_python"].garder
    assert g({"language": "Python", "license": "mit"}) and not g({"language": "Python", "license": "gpl-3.0"})
    assert not g({"language": "JavaScript", "license": "mit"})

def test_nettoyage():
    assert nettoyer("court") is None
    t = nettoyer("é\r\n" + "a" * 300 + "\x07")
    assert t.startswith("é\n") and "\x07" not in t and "\r" not in t

def test_reprise_apres_coupure_reseau(tmp_path):
    docs = [{"text": f"document {i} " + "x" * 300} for i in range(50)]
    def lecteur_qui_coupe(_):
        for i, d in enumerate(docs):
            if i == 20: raise ConnectionError("réseau coupé")
            yield d
    with pytest.raises(ConnectionError):
        telecharger(SOURCE_FACTICE, 10**9, tmp_path, lecteur_qui_coupe)
    assert not (tmp_path / ".complet").exists()
    telecharger(SOURCE_FACTICE, 10**9, tmp_path, lambda _: iter(docs))
    textes = lire_tous_les_textes(tmp_path)
    assert len(textes) == 50 and len(set(textes)) == 50
    assert (tmp_path / ".complet").exists()

def test_disque_plein(tmp_path, monkeypatch):
    monkeypatch.setattr("forge.donnees.telechargement.verifier_place",
                        lambda *a, **k: (_ for _ in ()).throw(PlaceInsuffisante("Il manque 3 Go sur D:")))
    with pytest.raises(PlaceInsuffisante):
        telecharger(SOURCE_FACTICE, 10**9, tmp_path, lambda _: iter(DOCS))
    assert not (tmp_path / ".complet").exists() and not list(tmp_path.glob("*.tmp"))

def test_melange_et_validation():
    assert repartir(1000) == {"web_fr": 750, "wikipedia_fr": 100, "code_python": 150}
    parts = [est_validation(f"{i:040x}") for i in range(0, 2**32, 2**20)]
    assert 0 < sum(parts) < len(parts) * 0.02
```

`lire_tous_les_textes(dossier)` est une petite aide de test qui relit tous les fragments. `SOURCE_FACTICE` est une `Source` de colonne `text`, sans filtre.

- [ ] **Étape 2 : lancer les tests et vérifier qu'ils échouent.**
- [ ] **Étape 3 : écrire les modules et `docs/donnees.md`.** Le document donne, pour chaque source, son dépôt, sa licence avec un lien, ce qui est gardé, et la phrase : « Les données ne sont jamais copiées dans ce dépôt ; seuls les modèles entraînés sont publiés. »
- [ ] **Étape 4 : lancer les tests et vérifier qu'ils passent.**
- [ ] **Étape 5 : faire un essai réel sur le réseau.** Commande : `python -m forge donnees --octets 5M --dossier essai`. Attendu : trois sous-dossiers contenant chacun un fichier `.complet`, et des volumes proches du mélange.
- [ ] **Étape 6 : commit**, message « Données : sources françaises et code, téléchargement en flux avec reprise ».

### Tâche 5 : encodage du corpus en jetons

**Fichiers :**

- Créer : `projets/forge/forge/donnees/jetons.py`
- Test : `projets/forge/tests/test_jetons.py`

**Interfaces :**

- Consomme : `TokenizerOctets` (tâche 3), les fragments et `est_validation` (tâche 4).
- Produit : `encoder_corpus(dossiers: list[Path], tokenizer: TokenizerOctets, sortie: Path, processus: int | None = None) -> dict`.
  - **Parallélisme :** `processus` vaut par défaut `os.cpu_count()` ; l'encodage est réparti fragment par fragment.
  - **Sortie :** des fichiers `train/fragment-00000.bin` et `val/fragment-00000.bin` en `uint16`. Chaque document est suivi de `<|fin_texte|>`, et le répertoire de validation reçoit les documents pour lesquels `est_validation(empreinte)` est vrai.
  - **Index et marqueurs :** `index.json` donne le nombre de jetons par fichier. La reprise se fait fragment par fragment : un fragment déjà encodé a son marqueur `<nom>.fait`. Le fichier `.complet` est écrit à la fin.
  - **Valeur renvoyée :** `{"jetons_train", "jetons_val", "octets_par_jeton"}`.
- Produit : `lire_jetons(fichier: Path) -> np.memmap`.
- Sous-commande : `python -m forge encoder --donnees <nom> --tokenizer <chemin>`.

- [ ] **Étape 1 : écrire les tests qui échouent.**

```python
def test_encodage_et_fin_de_texte(tmp_path):
    resume = encoder_corpus([DOSSIER_FRAGMENTS_TEST], TOK_TEST, tmp_path, processus=2)
    train = np.concatenate([lire_jetons(f) for f in sorted((tmp_path / "train").glob("*.bin"))])
    assert train.dtype == np.uint16
    fin = TOK_TEST.id_special("<|fin_texte|>")
    docs = TOK_TEST.decoder([int(i) for i in train if i != fin])
    assert "document 0" in docs
    assert (train == fin).sum() + sum((lire_jetons(f) == fin).sum() for f in (tmp_path / "val").glob("*.bin")) == NB_DOCS_TEST
    assert (tmp_path / ".complet").exists() and resume["octets_par_jeton"] > 1

def test_reprise_sans_doublon(tmp_path):
    encoder_corpus([DOSSIER_FRAGMENTS_TEST], TOK_TEST, tmp_path, processus=2)
    avant = (tmp_path / "index.json").read_text()
    encoder_corpus([DOSSIER_FRAGMENTS_TEST], TOK_TEST, tmp_path, processus=2)
    assert (tmp_path / "index.json").read_text() == avant
```

- [ ] **Étape 2 : lancer les tests et vérifier qu'ils échouent.**
- [ ] **Étape 3 : écrire `jetons.py`,** avec écriture atomique et `verifier_place` avant chaque fichier.
- [ ] **Étape 4 : lancer les tests et vérifier qu'ils passent.**
- [ ] **Étape 5 : commit**, message « Encodage du corpus en fragments de jetons ».

### Tâche 6 : le transformer et la génération

**Fichiers :**

- Créer : `projets/forge/forge/modele/__init__.py`, `config.py`, `transformer.py`, `generation.py`
- Test : `projets/forge/tests/test_modele.py`

**Interfaces :**

- Produit, dans `config.py` :
  - `@dataclass(frozen=True) class ConfigModele`, avec les champs `taille_vocabulaire: int = 32768`, `dim: int`, `couches: int`, `tetes: int`, `longueur_contexte: int` et `base_rope: float = 10000.0` ;
  - `PRESETS: dict[str, ConfigModele]` :

    | Nom | dim | couches | têtes | contexte |
    | --- | --- | --- | --- | --- |
    | `mini` | 384 | 6 | 6 | 512 |
    | `petit` | 512 | 8 | 8 | 2048 |
    | `moyen` | 768 | 12 | 12 | 2048 |
    | `grand` | 1024 | 16 | 16 | 2048 |
    | `tres_grand` | 1280 | 20 | 20 | 2048 |

  - `nombre_parametres(c: ConfigModele) -> int` : la formule exacte du modèle ci-dessous, sans double comptage des plongements liés.
- Produit, dans `transformer.py` : `class Transformer(nn.Module)`, avec `forward(ids: LongTensor[B, T], cibles: LongTensor | None = None) -> tuple[Tensor, Tensor | None]`, qui renvoie les logits et la perte d'entropie croisée moyenne.
  - **Architecture imposée :**
    - pré-normalisation RMSNorm (epsilon 1e-5) ;
    - attention multi-têtes causale via `F.scaled_dot_product_attention(is_causal=True)` ;
    - RoPE sur q et k ;
    - MLP SwiGLU de largeur cachée égale au multiple de 64 le plus proche de 8/3 × dim ;
    - aucun biais ;
    - plongement d'entrée et projection de sortie liés ;
    - RMSNorm finale.
  - **Initialisation :** loi normale d'écart-type 0,02, et 0,02/√(2 × couches) pour les projections qui reviennent dans le résidu.
- Produit, dans `generation.py` : `generer(modele, ids: list[int], n_nouveaux: int, temperature: float = 0.8, top_k: int = 50, graine: int = 0, arret: int | None = None) -> list[int]`. Il renvoie seulement les nouveaux jetons, s'arrête après le jeton `arret`, et ne garde que les `longueur_contexte` derniers jetons.

- [ ] **Étape 1 : écrire les tests qui échouent** (sur CPU, configuration minuscule : vocabulaire 512, dim 64, 2 couches, 4 têtes, contexte 32).

```python
def test_formes_et_parametres():
    m = Transformer(PETITE)
    logits, perte = m(torch.randint(0, 512, (2, 32)), torch.randint(0, 512, (2, 32)))
    assert logits.shape == (2, 32, 512)
    assert abs(perte.item() - math.log(512)) < 0.5
    assert sum(p.numel() for p in m.parameters()) == nombre_parametres(PETITE)
    assert m.plongement.weight is m.sortie.weight

def test_causalite():
    m = Transformer(PETITE).eval(); x = torch.randint(0, 512, (1, 32)); y = x.clone(); y[0, 20:] = 7
    assert torch.allclose(m(x)[0][0, :20], m(y)[0][0, :20], atol=1e-5)

def test_surapprentissage():
    torch.manual_seed(0); m = Transformer(PETITE); opt = torch.optim.AdamW(m.parameters(), 3e-3)
    x = torch.randint(0, 512, (4, 32)); y = torch.roll(x, -1, 1)
    for _ in range(300): opt.zero_grad(); m(x, y)[1].backward(); opt.step()
    assert m(x, y)[1].item() < 0.5

def test_generation_deterministe():
    m = Transformer(PETITE).eval()
    a = generer(m, [1, 2, 3], 10, graine=5); b = generer(m, [1, 2, 3], 10, graine=5)
    assert a == b and len(a) == 10
    assert generer(m, [1, 2, 3], 50, graine=5, arret=a[0]) == [a[0]]

def test_presets():
    assert 100e6 < nombre_parametres(PRESETS["moyen"]) < 140e6
```

- [ ] **Étape 2 : lancer les tests et vérifier qu'ils échouent.**
- [ ] **Étape 3 : écrire les trois modules.**
- [ ] **Étape 4 : lancer les tests et vérifier qu'ils passent.**
- [ ] **Étape 5 : commit**, message « Transformer de ton IA et génération ».

### Tâche 7 : l'entraînement, avec pause et reprise exactes

**Fichiers :**

- Créer : `projets/forge/forge/entrainement/__init__.py`, `chargeur.py`, `planning.py`, `sauvegarde.py`, `boucle.py`
- Créer : `projets/forge/configs/mini.toml`
- Test : `projets/forge/tests/test_entrainement.py`

**Interfaces :**

- Consomme : `Transformer` et `PRESETS` (tâche 6), `lire_jetons` (tâche 5), `verifier_place` (tâche 2).
- Produit, dans `chargeur.py` : `class ChargeurJetons`.
  - Constructeur : `(dossier: Path, longueur: int, taille_lot: int, graine: int)`.
  - Méthodes : `lot() -> tuple[LongTensor, LongTensor]`, `etat() -> dict` et `restaurer(etat: dict) -> None`.
  - Lecture séquentielle dans les fragments, avec un ordre des fragments tiré de la graine à chaque époque.
- Produit, dans `planning.py` : `taux(pas: int, pas_total: int, taux_max: float, echauffement: int, ratio_min: float = 0.1) -> float`. Montée linéaire, puis cosinus jusqu'à `ratio_min × taux_max`.
- Produit, dans `sauvegarde.py` :
  - `sauvegarder(dossier: Path, etat: dict, nom: str) -> Path` : écriture dans `nom.tmp`, `os.fsync`, puis `os.replace`. On garde les 2 dernières `etape-*.pt` et `meilleur.pt`. Avant d'écrire : `verifier_place(estimation × 2)`.
  - `charger_derniere(dossier: Path) -> dict | None` : ignore les `.tmp`.
- Produit, dans `boucle.py` :
  - `@dataclass class ConfigEntrainement`, lue depuis un TOML. Champs : `preset`, `donnees`, `jetons_total`, `taille_lot_jetons`, `micro_lot`, `taux_max`, `echauffement`, `poids_decroissance = 0.1`, `betas = (0.9, 0.95)`, `ecretage = 1.0`, `graine = 1234`, `evaluation_tous_pas`, `sauvegarde_minutes = 30`, `appareil` (`"cuda"` ou `"cpu"`), `compiler` (`"auto"`, `"oui"` ou `"non"`) et `sortie`.
  - `entrainer(config: ConfigEntrainement, reprendre: bool = False, arreter_apres: int | None = None) -> dict`.
    - `arreter_apres` sert aux tests : l'appel s'arrête quand le pas global atteint cette valeur, et sauvegarde.
    - Le dictionnaire renvoyé contient `pertes`, la liste des pertes des seuls pas exécutés pendant cet appel.
    - En cas de manque de mémoire GPU, la fonction quitte avec `SystemExit(2)` après le message.
  - **Comportement imposé :**
    - précision bf16 sous autocast sur CUDA ;
    - accumulation de gradient pour atteindre `taille_lot_jetons` ;
    - écrêtage ;
    - `torch.compile` si `compiler` le permet, avec un retour silencieux en mode immédiat s'il échoue et `"auto"`, et un message dans le journal ;
    - journal `journal.jsonl` (`pas`, `jetons_vus`, `perte`, `taux`, `jetons_par_seconde`, `secondes`), plus `perte_val` tous les `evaluation_tous_pas` ;
    - sauvegarde tous les `sauvegarde_minutes` et à la fin.
  - **Ctrl+C :** la boucle finit le pas en cours, sauvegarde, puis affiche « Entraînement mis en pause au pas N. Pour reprendre : python -m forge entrainer --config <fichier> --reprendre », et quitte avec le code 0.
  - **Manque de mémoire GPU :** l'erreur est rattrapée, et le message dit la mémoire libre, puis « Réduis micro_lot dans <fichier>, ferme les jeux ou logiciels 3D ouverts, puis relance avec --reprendre. »
  - **État sauvegardé :** le modèle, l'optimiseur, le pas, l'état du chargeur, les états aléatoires de Python, NumPy, torch et CUDA, et la configuration.
- Sous-commande : `python -m forge entrainer --config <toml> [--reprendre]`.
- `configs/mini.toml` : preset `mini`, `appareil = "cuda"`. Ses autres valeurs sont fixées en tâche 11 d'après les mesures, pour viser environ 1 heure.

- [ ] **Étape 1 : écrire les tests qui échouent** (sur CPU, configuration minuscule, petit corpus de jetons écrit par le test).

```python
def test_reprise_exacte(tmp_path):
    a = entrainer(config_test(tmp_path / "a"), arreter_apres=20)["pertes"]
    entrainer(config_test(tmp_path / "b"), arreter_apres=10)
    b = entrainer(config_test(tmp_path / "b"), reprendre=True, arreter_apres=20)["pertes"]
    assert a[10:20] == pytest.approx(b, abs=1e-6)

def test_sauvegarde_coupee(tmp_path):
    entrainer(config_test(tmp_path), arreter_apres=10)
    (tmp_path / "sauvegardes" / "etape-0000020.pt.tmp").write_bytes(b"\x00" * 100)  # écriture interrompue
    assert charger_derniere(tmp_path / "sauvegardes")["pas"] == 10

def test_disque_plein_avant_sauvegarde(tmp_path, monkeypatch):
    monkeypatch.setattr("forge.entrainement.sauvegarde.verifier_place",
                        lambda *a, **k: (_ for _ in ()).throw(PlaceInsuffisante("Il manque 1 Go sur D:")))
    with pytest.raises(PlaceInsuffisante): sauvegarder(tmp_path, {"pas": 1}, "etape-0000001.pt")
    assert not list(tmp_path.iterdir())

def test_memoire_gpu_message(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("forge.entrainement.boucle._pas_d_optimisation",
                        lambda *a, **k: (_ for _ in ()).throw(torch.cuda.OutOfMemoryError("CUDA out of memory")))
    with pytest.raises(SystemExit): entrainer(config_test(tmp_path), arreter_apres=1)
    assert "Réduis micro_lot" in capsys.readouterr().err

def test_planning():
    assert taux(0, 1000, 1e-3, 100) == 0 and taux(100, 1000, 1e-3, 100) == pytest.approx(1e-3)
    assert taux(1000, 1000, 1e-3, 100) == pytest.approx(1e-4)

@pytest.mark.gpu
def test_entrainement_gpu_court(tmp_path):
    r = entrainer(config_test(tmp_path, appareil="cuda"), arreter_apres=30)
    assert r["pertes"][-1] < r["pertes"][0]
```

`config_test` écrit un corpus de jetons répétitifs et une configuration minuscule.

- [ ] **Étape 2 : lancer les tests et vérifier qu'ils échouent.**
- [ ] **Étape 3 : écrire les cinq modules.** La boucle sépare le pas d'optimisation dans `_pas_d_optimisation`, pour que le test puisse simuler un manque de mémoire.
- [ ] **Étape 4 : lancer les tests et vérifier qu'ils passent.** Commandes : `--extra cpu` et `--extra gpu`.
- [ ] **Étape 5 : faire une pause réelle.** Lancer un entraînement minuscule sur GPU, appuyer sur Ctrl+C, vérifier le message, puis reprendre avec `--reprendre`. Coller la sortie dans le rapport.
- [ ] **Étape 6 : commit**, message « Entraînement : bf16, accumulation, sauvegardes atomiques, pause et reprise exactes ».

### Tâche 8 : l'évaluation

**Fichiers :**

- Créer : `projets/forge/forge/evaluation/__init__.py`, `perte.py`, `qcm.py`, `echantillons.py`, `rapport.py`
- Test : `projets/forge/tests/test_evaluation.py`

**Interfaces :**

- Consomme : le modèle, `generer`, le tokenizer et `ChargeurJetons`.
- Produit, dans `perte.py` :
  - `perte_validation(modele, chargeur: ChargeurJetons, n_lots: int) -> float` (en nats par jeton) ;
  - `bits_par_octet(perte: float, octets_par_jeton: float) -> float`, qui vaut `perte / ln 2 / octets_par_jeton`.
- Produit, dans `qcm.py` :
  - `@dataclass class QCM` : `contexte: str`, `choix: list[str]`, `bonne: int` ;
  - `charger_frenchbench(nom: Literal["hellaswag", "arc"], n_max: int | None = None) -> list[QCM]`, à partir de `manu/french_bench_hellaswag` (validation) et `manu/french_bench_arc_challenge` (test) ;
  - `evaluer_qcm(modele, tokenizer, qcms: list[QCM]) -> dict` : renvoie `exactitude`, `exactitude_normalisee` (log-vraisemblance divisée par le nombre d'octets de la réponse), `hasard` (1/nombre de choix) et `n`.
- Produit, dans `echantillons.py` :
  - `INVITES` : 8 débuts de phrase en français et 2 débuts de fonction Python ;
  - `echantillons(modele, tokenizer, graine: int = 0, n_nouveaux: int = 60) -> list[dict]`.
- Produit, dans `rapport.py` : `evaluer(sauvegarde: Path, donnees: Path, tokenizer: Path, sortie: Path, n_qcm: int | None = None) -> dict`. Il écrit `rapport.json` et `rapport.md` (en français : perte, perplexité, bits par octet, QCM comparés au hasard, échantillons).
- Sous-commande : `python -m forge evaluer --sauvegarde <pt> --donnees <nom>`.

- [ ] **Étape 1 : écrire les tests qui échouent.**

```python
def test_bits_par_octet():
    assert bits_par_octet(math.log(2) * 3, 3.0) == pytest.approx(1.0)

def test_qcm_choisit_la_vraisemblance():
    q = [QCM("Le ciel est", [" bleu.", " xqzv."], 0)]
    r = evaluer_qcm(MODELE_QUI_PREFERE(" bleu."), TOK_TEST, q)
    assert r["exactitude"] == 1.0 and r["hasard"] == 0.5 and r["n"] == 1

def test_rapport(tmp_path):
    r = evaluer(SAUVEGARDE_MINUSCULE, DONNEES_TEST, TOK_FICHIER_TEST, tmp_path, n_qcm=0)
    assert {"perte_val", "perplexite", "bits_par_octet", "echantillons"} <= r.keys()
    assert "Perplexité" in (tmp_path / "rapport.md").read_text(encoding="utf-8")
```

`MODELE_QUI_PREFERE(texte)` est un faux modèle de test, dont les logits favorisent les octets de `texte`.

- [ ] **Étape 2 : lancer les tests et vérifier qu'ils échouent.**
- [ ] **Étape 3 : écrire les quatre modules.**
- [ ] **Étape 4 : lancer les tests et vérifier qu'ils passent,** puis faire un essai réel de `charger_frenchbench("hellaswag", 5)` sur le réseau.
- [ ] **Étape 5 : commit**, message « Évaluation : perte, bits par octet, QCM français, échantillons, rapport ».

### Tâche 9 : échantillon réel et tokenizer définitif de ton IA

**Fichiers :**

- Créer : `projets/forge/forge/ressources/tokenizer-ton-ia-v1.json`
- Créer : `projets/forge/tests/test_tokenizer_ton_ia.py`
- Créer : `docs/mesures/tokenizer-ton-ia-v1.md`

- [ ] **Étape 1 : télécharger l'échantillon d'apprentissage.** Commande : `python -m forge donnees --octets 300M --dossier echantillon-tokenizer`. Il suit le mélange par défaut.
- [ ] **Étape 2 : faire un essai chronométré.** Entraîner sur 10 Mo de l'échantillon pour 2 000 fusions, puis extrapoler la durée pour 300 Mo et 32 448 fusions. Cet apprentissage ne tourne que sur CPU et sur un seul fil.
  - Si l'estimation dépasse 30 minutes, s'arrêter : le contrôleur montre la durée à l'utilisateur et lui demande s'il faut réduire l'échantillon (100 Mo) ou attendre.
  - Sinon, continuer.
- [ ] **Étape 3 : apprendre le tokenizer et l'enregistrer.** Le nom est `ton-ia-v1`, la taille 32 768.
- [ ] **Étape 4 : écrire les tests qui fixent le tokenizer.**

```python
TOK = TokenizerOctets.charger(RESSOURCE_TON_IA)
def test_taille_et_speciaux():
    assert len(TOK.fusions) == 32448 and TOK.id_special("<|fin_texte|>") == 32705
    assert TOK.id_special("<|reserve_45|>") == 32767
def test_compression_francais_et_code():
    assert len("Le forgeron frappe le métal sur l’enclume.".encode()) / len(TOK.encoder("Le forgeron frappe le métal sur l’enclume.")) > 3.0
    assert len(TOK.encoder("def fusionner(mots, paire):\n    return mots\n")) < 20
```

- [ ] **Étape 5 : mesurer la compression** (octets par jeton) sur 1 Mo de validation de chaque source, et l'écrire dans `docs/mesures/tokenizer-ton-ia-v1.md` avec la date et la durée d'apprentissage.
- [ ] **Étape 6 : commit,** sans les données, message « Tokenizer de ton IA, version 1, appris sur 300 Mo de français et de code ».

### Tâche 10 : essai chronométré GPU et CPU, et choix de la taille (porte)

**Fichiers :**

- Créer : `projets/forge/forge/mesure.py`, `projets/forge/tests/test_mesure.py`
- Créer : `docs/mesures/entrainement-2026-11.md`

**Interfaces :**

- Produit : `mesurer(config: ConfigModele, appareil: str, micro_lot: int, pas: int = 20, fils: int | None = None) -> dict`.
  - Valeur renvoyée : `jetons_par_seconde`, `memoire_max_go`, `fils_utilises` et `charge_par_coeur` (moyenne psutil par cœur pendant la mesure, sur CPU).
  - Sur CPU, `torch.set_num_threads(fils or os.cpu_count())`.
- Produit : `estimer(config: ConfigModele, jetons_par_seconde: float, jetons: int) -> float`, qui renvoie des heures.
- Sous-commande : `python -m forge mesurer`. Elle écrit un tableau pour les presets `petit`, `moyen`, `grand` et `tres_grand`, avec pour chacun :
  - le nombre de paramètres ;
  - le débit et la mémoire sur GPU ;
  - le débit sur CPU avec 16 fils, et la charge par cœur ;
  - la durée estimée pour 20 jetons par paramètre, sur GPU et sur CPU ;
  - la place disque des données correspondantes (2 octets par jeton).

- [ ] **Étape 1 : écrire le test qui échoue.** Sur CPU, en configuration minuscule, `mesurer` renvoie un débit positif, et `fils_utilises == os.cpu_count()`.
- [ ] **Étape 2 : écrire `mesure.py` et lancer le test jusqu'à ce qu'il passe.**
- [ ] **Étape 3 : lancer `python -m forge mesurer`,** avec le micro-lot le plus grand qui tient en mémoire pour chaque preset. Écrire le tableau dans `docs/mesures/entrainement-2026-11.md`.
- [ ] **Étape 4 (porte, tenue par le contrôleur) :** montrer le tableau à l'utilisateur et lui demander, avec AskUserQuestion :
  1. GPU ou CPU, en rappelant les chiffres et le nombre de cœurs utilisés ;
  2. la taille de ton IA, avec la durée et la place disque de chaque choix, et en rappelant que l'entraînement se met en pause et se reprend.

  Tant que l'utilisateur n'a pas répondu, ne pas lancer les tâches 12 et 13.
- [ ] **Étape 5 : écrire `configs/principal.toml`** d'après le choix (preset, `jetons_total`, appareil), puis commit, message « Mesures GPU et CPU, configuration principale choisie ».

### Tâche 11 : version courte de bout en bout (environ une heure)

- [ ] **Étape 1 : préparer les données courtes.** Commandes : `python -m forge donnees --octets 600M --dossier court` puis `python -m forge encoder --donnees court --tokenizer <ressource>`. Pendant l'encodage, vérifier avec psutil que les 16 fils travaillent, et noter la charge.
- [ ] **Étape 2 : régler `configs/mini.toml`** d'après la mesure de la tâche 10 : preset `mini`, et `jetons_total` pour une durée d'environ 1 heure sur GPU. Puis lancer l'entraînement.
- [ ] **Étape 3 : évaluer** avec `python -m forge evaluer`. Écrire le rapport dans `docs/mesures/ton-ia-mini.md` : durée réelle, courbe (pas et perte, tous les 10 % de l'entraînement), perplexité, échantillons.
- [ ] **Étape 4 : commit,** message « Version courte de ton IA : entraînement d'une heure et rapport ».

### Tâche 12 : corpus principal

- [ ] **Étape 1 : estimer la place puis vérifier.** Calculer la place nécessaire d'après la configuration choisie : texte brut, plus jetons, plus 3 sauvegardes. Lancer `verifier_place`. S'il manque de la place, s'arrêter et prévenir le contrôleur.
- [ ] **Étape 2 : télécharger puis encoder.** Lancer en arrière-plan le téléchargement, puis l'encodage. Les deux reprennent s'ils sont interrompus. Pendant l'encodage, vérifier que les 16 fils travaillent.
- [ ] **Étape 3 : libérer la place du texte brut.** Une fois le marqueur `.complet` des jetons présent, supprimer le texte brut téléchargé. Les jetons suffisent pour la suite, et le tokenizer est figé.
- [ ] **Étape 4 : commit** de `docs/mesures/entrainement-2026-11.md`, complété par les volumes réels.

### Tâche 13 : entraînement principal

- [ ] **Étape 1 : lancer l'entraînement en arrière-plan.** Commande : `python -m forge entrainer --config configs/principal.toml`. Vérifier les 200 premiers pas : la perte baisse, le débit est proche de la mesure et aucune erreur n'apparaît.
- [ ] **Étape 2 : faire une vraie pause.** Ctrl+C après la première sauvegarde, puis reprise avec `--reprendre`. La perte du premier pas repris doit suivre la courbe, sans saut.
- [ ] **Étape 3 : écrire le suivi.** `python -m forge suivi --config configs/principal.toml` affiche le pas, les jetons vus, la dernière perte, le débit, le temps restant estimé et la dernière sauvegarde. Il s'ajoute à `__main__.py` et a un test sur un journal factice.
- [ ] **Étape 4 : commit** de la sous-commande de suivi.
- [ ] **Étape 5 :** le contrôleur dit à l'utilisateur comment mettre en pause et reprendre, avec les commandes PowerShell exactes, et combien de temps il reste. Le plan attend ensuite la fin de l'entraînement. Il ne bloque pas le PC : l'utilisateur peut mettre en pause à tout moment.

### Tâche 14 : fin de l'entraînement, évaluation et publication (porte)

- [ ] **Étape 1 : évaluer `meilleur.pt`.** Commande : `python -m forge evaluer`, avec les QCM complets. Écrire `docs/mesures/ton-ia-1.5.md` en français : courbe, perplexité, bits par octet, QCM comparés au hasard, échantillons, durée totale réelle.
- [ ] **Étape 2 : préparer les fichiers à publier.**
  - Poids : `ton-ia-1.5.safetensors`, en bf16.
  - Configuration : `config.json`.
  - Tokenizer : `tokenizer-ton-ia-v1.json`.
  - Le rapport.
  - Une fiche `LISEZMOI.md` qui dit ce que le modèle sait faire et ne sait pas faire, et donne les licences des données.
- [ ] **Étape 3 (porte, tenue par le contrôleur) :** demander à l'utilisateur l'accord pour publier une version GitHub `ton-ia-1.5` avec ces fichiers. Sans accord, ne rien publier.
- [ ] **Étape 4 : publier.** Commande : `gh release create ton-ia-1.5 <fichiers> --title "Ton IA, chapitre 1.5" --notes-file LISEZMOI.md`. Vérifier que chaque fichier fait moins de 2 Go et se télécharge.
- [ ] **Étape 5 : écrire le jalon** dans la mémoire partagée, si elle répond. Puis commit et poussée avec l'accord de l'utilisateur, message « Ton IA 1.5 : évaluation finale et publication ».
