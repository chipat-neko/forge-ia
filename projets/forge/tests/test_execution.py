"""Tests de l'exécution du code généré dans un sous-processus limité (`forge.code.execution`).

Chaque test qui lance un sous-processus prend un délai d'au plus 2 s. Ce qui est propre à Windows (l'objet
Job qui refuse un second processus) est signalé dans le test.
"""

import ast
import os
import shutil
import stat
import sys
import textwrap
import time
import warnings
from pathlib import Path

import psutil
import pytest

from forge.code import execution
from forge.code.execution import ResultatExecution, executer, executer_tous

DELAI = 2.0


def test_un_programme_juste_reussit():
    resultat = executer("print(1+1)", delai=DELAI)
    assert isinstance(resultat, ResultatExecution)
    assert resultat.reussi
    assert resultat.raison == "reussi"
    assert resultat.sortie == "2\n"
    assert 0 <= resultat.secondes < DELAI


def test_une_assertion_fausse_echoue():
    resultat = executer("assert False", delai=DELAI)
    assert not resultat.reussi
    assert resultat.raison == "echec"
    assert "AssertionError" in resultat.sortie


def test_une_boucle_sans_fin_est_arretee_au_delai():
    debut = time.monotonic()
    resultat = executer("while True: pass", delai=1.0)
    duree = time.monotonic() - debut
    assert resultat.raison == "delai"
    assert not resultat.reussi
    assert duree < 1.0 + 2


def test_deux_gigaoctets_sont_refuses_sans_bloquer():
    """La limite de mémoire refuse l'allocation : `memoire` (ou `echec`), jamais un blocage."""
    debut = time.monotonic()
    resultat = executer("donnees = bytearray(2 * 1024**3)\nprint(len(donnees))", delai=DELAI)
    duree = time.monotonic() - debut
    assert resultat.raison in ("memoire", "echec")
    assert not resultat.reussi
    assert duree < DELAI + 2


def test_une_memory_error_donne_la_raison_memoire():
    resultat = executer("raise MemoryError", delai=DELAI)
    assert resultat.raison == "memoire"
    assert not resultat.reussi
    assert "MemoryError" in resultat.sortie


def test_la_sortie_est_tronquee_a_sortie_max_caracteres():
    resultat = executer("print('x' * 1_000_000)", delai=DELAI)
    assert resultat.reussi
    assert len(resultat.sortie) == 10_000
    assert resultat.sortie == "x" * 10_000
    # Des caractères de plusieurs octets : la limite compte des caractères, pas des octets.
    court = executer("print('\u00e9' * 1_000)", delai=DELAI, sortie_max=100)
    assert court.sortie == "\u00e9" * 100


def test_la_sortie_reunit_sorties_et_erreurs_en_utf8():
    programme = "import sys\nprint('\u00e9t\u00e9 \u2192 1\u202f000')\nprint('erreur', file=sys.stderr)"
    resultat = executer(programme, delai=DELAI)
    assert resultat.reussi
    assert "\u00e9t\u00e9 \u2192 1\u202f000\n" in resultat.sortie
    assert "erreur\n" in resultat.sortie


def test_le_dossier_jetable_est_le_dossier_courant_et_disparait_apres_l_appel():
    programme = textwrap.dedent(
        """
        import os, stat, tempfile
        # realpath : un même chemin écrit pareil (liens symboliques, noms courts « RUNNER~1 » sous Windows).
        print(os.path.realpath(os.getcwd()))
        print(os.path.realpath(tempfile.gettempdir()))
        os.mkdir("sous-dossier")
        fichier = os.path.join("sous-dossier", "lecture-seule.txt")
        with open(fichier, "w") as f:
            f.write("ce fichier en lecture seule doit partir aussi")
        os.chmod(fichier, stat.S_IREAD)
        """
    )
    resultat = executer(programme, delai=DELAI)
    assert resultat.reussi, resultat.sortie
    dossier, temporaire = resultat.sortie.splitlines()
    assert Path(dossier).name.startswith("forge-code-")
    assert os.path.normcase(dossier) == os.path.normcase(temporaire)
    assert not Path(dossier).exists()


def test_le_dossier_jetable_disparait_aussi_apres_un_delai():
    resultat = executer("import os\nprint(os.getcwd(), flush=True)\nwhile True: pass", delai=1.0)
    assert resultat.raison == "delai"
    assert not Path(resultat.sortie.strip()).exists()


def test_l_environnement_du_programme_est_reduit(monkeypatch):
    monkeypatch.setenv("FORGE_SECRET_DE_TEST", "ne doit pas passer")
    resultat = executer("import os\nprint(sorted(os.environ))", delai=DELAI)
    assert resultat.reussi, resultat.sortie
    noms = {nom.upper() for nom in ast.literal_eval(resultat.sortie)}
    assert "FORGE_SECRET_DE_TEST" not in noms
    assert {"PATH", "TEMP", "TMP", "PYTHONIOENCODING"} <= noms


# Le programme relève son PID, puis celui de l'enfant qu'il lance (ou le refus), dans un fichier de son
# dossier jetable. L'enfant porte une marque (`forge-test-enfant`), visible dans sa ligne de commande.
PROGRAMME_ENFANT = textwrap.dedent(
    """
    import os, subprocess, sys
    with open("pids.txt", "w", encoding="utf-8") as releve:
        releve.write(f"parent {{os.getpid()}}\\n")
    try:
        enfant = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)  # forge-test-enfant"])
    except OSError as erreur:
        with open("pids.txt", "a", encoding="utf-8") as releve:
            releve.write(f"refus {{erreur!r}}\\n")
        raise
    with open("pids.txt", "a", encoding="utf-8") as releve:
        releve.write(f"enfant {{enfant.pid}}\\n")
    if {attendre}:
        enfant.wait()
    """
)


def _processus_du_test(pid: int, marques: tuple[str, ...]) -> psutil.Process | None:
    """Le processus `pid` s'il vit encore et vient de ce test (une marque dans sa ligne de commande), sinon None.

    La marque écarte un autre programme qui aurait reçu le même numéro : seul un processus de ce test est
    compté, et tué au nettoyage. Un zombie (fini, pas encore ramassé par son parent) ne vit plus.
    """
    try:
        processus = psutil.Process(pid)
        if processus.status() == psutil.STATUS_ZOMBIE:
            return None
        ligne = " ".join(processus.cmdline())
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return None
    return processus if any(marque in ligne for marque in marques) else None


@pytest.mark.parametrize("attendre", [True, False], ids=["parent-qui-attend", "parent-qui-part"])
def test_aucun_processus_ne_du_programme_ne_survit(monkeypatch, attendre):
    """Point à surveiller 4 : un programme qui lance un enfant qui dort 60 s ne laisse aucun processus.

    Le relevé des PID est lu dans le dossier jetable juste avant son effacement. Sous Linux, SIGKILL agit un
    instant après son envoi : on laisse 2 s aux processus visés pour disparaître.
    """
    releves: list[tuple[str, str]] = []
    effacer = execution._effacer

    def relever_puis_effacer(dossier):
        fichier = Path(dossier) / "pids.txt"
        if fichier.exists():
            releves.append((Path(dossier).name, fichier.read_text(encoding="utf-8")))
        effacer(dossier)

    monkeypatch.setattr(execution, "_effacer", relever_puis_effacer)
    resultat = executer(PROGRAMME_ENFANT.format(attendre=attendre), delai=DELAI)

    assert len(releves) == 1, resultat.sortie
    nom_du_dossier, releve = releves[0]
    lignes = releve.splitlines()
    pids = [int(ligne.split()[1]) for ligne in lignes if ligne.split()[0] in ("parent", "enfant")]
    assert pids, releve
    # Le parent porte le dossier jetable dans sa ligne de commande (le chemin du programme), l'enfant sa marque.
    marques = (nom_du_dossier, "forge-test-enfant")
    vivants = [p for pid in pids if (p := _processus_du_test(pid, marques)) is not None]
    _, vivants = psutil.wait_procs(vivants, timeout=2)
    survivants = [p for p in vivants if _processus_du_test(p.pid, marques) is not None]
    for processus in survivants:  # nettoyage : seulement les processus nés de ce test
        processus.kill()
    assert not survivants, f"processus survivants : {survivants}"

    if sys.platform == "win32":
        # L'objet Job n'admet qu'un processus : la création de l'enfant échoue, et le programme avec.
        assert lignes[-1].startswith("refus "), releve
        assert resultat.raison == "echec"
    elif attendre:
        assert resultat.raison == "delai"
    else:
        assert resultat.raison == "reussi"


def test_un_interpreteur_introuvable_donne_erreur_systeme(monkeypatch):
    monkeypatch.setattr(execution, "_interpreteur", lambda: str(Path("introuvable") / "python-absent"))
    resultat = executer("print(1)", delai=DELAI)
    assert resultat.raison == "erreur_systeme"
    assert not resultat.reussi
    assert resultat.sortie


def test_sans_interpreteur_de_base_un_environnement_virtuel_est_refuse(monkeypatch):
    """Pas de repli silencieux sur le lanceur du `.venv` : il ferait tourner les programmes hors du Job."""
    monkeypatch.setattr(sys, "_base_executable", str(Path("introuvable") / "python-absent"), raising=False)
    monkeypatch.setattr(sys, "base_prefix", sys.prefix + "-base")  # un environnement virtuel
    with pytest.raises(RuntimeError, match="interpréteur Python de base"):
        executer("print(1)", delai=DELAI)
    monkeypatch.setattr(sys, "base_prefix", sys.prefix)  # pas d'environnement virtuel : l'interpréteur lui-même
    assert execution._interpreteur() == sys.executable


@pytest.mark.parametrize("envoye", [b"", b"x"], ids=["tube-ferme-sans-octet", "mauvais-octet"])
def test_sans_octet_de_depart_le_programme_n_est_jamais_execute(monkeypatch, tmp_path, envoye):
    """Si la forge meurt avant le rangement dans le Job, l'amorce lit la fin du tube : elle n'exécute rien.

    Le programme écrirait un fichier témoin hors du dossier jetable ; il ne doit pas exister.
    """
    temoin = tmp_path / "temoin.txt"
    programme = f"open({str(temoin)!r}, 'w').write('exécuté')"
    assert executer(programme, delai=DELAI).reussi  # avec le départ, le témoin est bien écrit
    assert temoin.exists()
    temoin.unlink()

    def depart_manque(processus):
        processus.stdin.write(envoye)
        processus.stdin.close()

    monkeypatch.setattr(execution, "_donner_le_depart", depart_manque)
    resultat = executer(programme, delai=DELAI)
    assert resultat.raison == "erreur_systeme"
    assert not resultat.reussi
    assert "départ" in resultat.sortie
    assert not temoin.exists()


def test_des_dossiers_sans_droit_d_ecriture_sont_effaces_quand_meme():
    """Le cas de Linux : un dossier sans droit d'écriture, ou sans aucun droit, empêche d'effacer ce qu'il
    contient. Sous Windows, `chmod` ne pose que l'attribut « lecture seule », et le test passe aussi."""
    programme = textwrap.dedent(
        """
        import os
        for nom, mode in (("sans-ecriture", 0o500), ("sans-droits", 0o000)):
            os.mkdir(nom)
            with open(os.path.join(nom, "fichier.txt"), "w") as f:
                f.write("x")
            os.chmod(nom, mode)
        print(os.path.realpath(os.getcwd()))
        """
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error", execution.DossierJetableNonEfface)
        resultat = executer(programme, delai=DELAI)
    assert resultat.reussi, resultat.sortie
    assert not Path(resultat.sortie.strip()).exists()


@pytest.mark.skipif(sys.platform != "win32", reason="sous Linux, un fichier ouvert n'empêche pas de l'effacer")
def test_un_fichier_tenu_ouvert_ne_fait_pas_perdre_le_resultat(monkeypatch):
    """Windows : un fichier du dossier jetable tenu ouvert (un antivirus, un indexeur) empêche de l'effacer
    (WinError 32). Le résultat est rendu quand même, et un avertissement nomme le dossier resté."""
    ouverts = []
    lancer = execution._lancer

    def lancer_puis_garder_ouvert(interpreteur, fichier, *reste):
        resultat = lancer(interpreteur, fichier, *reste)
        ouverts.append(open(fichier, "rb"))
        return resultat

    monkeypatch.setattr(execution, "_lancer", lancer_puis_garder_ouvert)
    try:
        with pytest.warns(execution.DossierJetableNonEfface) as avertissements:
            resultat = executer("print(1)", delai=DELAI)
    finally:
        for ouvert in ouverts:
            ouvert.close()
            shutil.rmtree(Path(ouvert.name).parent, ignore_errors=True)
    assert resultat.reussi and resultat.sortie == "1\n"
    message = str(avertissements[0].message)
    assert str(Path(ouverts[0].name).parent) in message
    assert "WinError 32" in message


def test_un_effacement_impossible_n_arrete_pas_executer_tous(monkeypatch):
    """Sur tous les systèmes : l'effacement échoue à chaque fois. Chaque résultat est rendu, dans l'ordre, et un
    avertissement nomme chaque dossier resté (effacé ensuite par le test)."""
    effacer_pour_de_vrai = shutil.rmtree
    restes: set[str] = set()

    def rmtree_refuse(chemin, **options):
        restes.add(str(chemin))
        raise PermissionError(13, "effacement refusé (essai)", str(chemin))

    monkeypatch.setattr(shutil, "rmtree", rmtree_refuse)
    try:
        with pytest.warns(execution.DossierJetableNonEfface) as avertissements:
            resultats = executer_tous(["print(0)", "assert False", "print(2)"], processus=3, delai=DELAI)
    finally:
        monkeypatch.undo()
        for dossier in restes:
            effacer_pour_de_vrai(dossier, ignore_errors=True)
    assert [r.raison for r in resultats] == ["reussi", "echec", "reussi"]
    assert len(restes) == 3
    messages = " ".join(str(a.message) for a in avertissements)
    assert all(dossier in messages for dossier in restes)


def test_l_effacement_ne_touche_rien_hors_du_dossier_jetable(monkeypatch, tmp_path):
    """Quand l'effacement échoue sur le dossier jetable lui-même, son parent (le `TEMP` de l'utilisateur, `/tmp`
    en 1777 sous Linux) ne reçoit aucun `chmod` : `os.chmod`, espionné, ne voit que des chemins du dossier."""
    dossier = tmp_path / "forge-code-essai"
    (dossier / "sous-dossier").mkdir(parents=True)
    (dossier / "sous-dossier" / "fichier.txt").write_text("x", encoding="utf-8")
    vrai_rmdir, vrai_chmod = os.rmdir, os.chmod
    touches: list[str] = []

    def rmdir_qui_refuse_la_racine(chemin, *arguments, **options):
        if options.get("dir_fd") is None and os.path.abspath(chemin) == str(dossier):
            raise PermissionError(13, "effacement refusé (essai)", str(chemin))
        return vrai_rmdir(chemin, *arguments, **options)

    def chmod_espion(chemin, mode, *arguments, **options):
        touches.append(os.path.abspath(chemin))
        return vrai_chmod(chemin, mode, *arguments, **options)

    monkeypatch.setattr(os, "rmdir", rmdir_qui_refuse_la_racine)
    monkeypatch.setattr(os, "chmod", chmod_espion)
    with pytest.warns(execution.DossierJetableNonEfface):
        execution._effacer(dossier)
    monkeypatch.undo()
    assert touches, "l'effacement n'a rien eu à rendre inscriptible : l'essai ne montre rien"
    assert str(tmp_path) not in touches
    assert all(execution._dans_le_dossier(chemin, dossier) for chemin in touches), touches


@pytest.mark.skipif(sys.platform == "win32", reason="un lien symbolique demande des droits particuliers sous Windows")
def test_l_effacement_ne_suit_pas_un_lien_symbolique(tmp_path):
    """Linux : un lien vers un fichier de l'utilisateur, dans un dossier sans droit d'écriture. `os.chmod` suivrait
    le lien et changerait les droits du fichier visé : il est sauté."""
    cible = tmp_path / "fichier-de-l-utilisateur.txt"
    cible.write_text("à garder", encoding="utf-8")
    os.chmod(cible, 0o600)
    programme = textwrap.dedent(
        f"""
        import os
        os.mkdir("d")
        os.symlink({str(cible)!r}, os.path.join("d", "lien"))
        os.chmod("d", 0o500)
        print(os.path.realpath(os.getcwd()))
        """
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error", execution.DossierJetableNonEfface)
        resultat = executer(programme, delai=DELAI)
    assert resultat.reussi, resultat.sortie
    assert not Path(resultat.sortie.strip()).exists()
    assert stat.S_IMODE(os.stat(cible).st_mode) == 0o600
    assert cible.read_text(encoding="utf-8") == "à garder"


def test_sous_w_error_l_avertissement_ne_remplace_pas_le_resultat(monkeypatch, capsys):
    """`-W error` change les avertissements en exceptions : le dossier resté est alors nommé sur la sortie
    d'erreur, et le résultat est rendu."""
    effacer_pour_de_vrai = shutil.rmtree
    restes: set[str] = set()

    def rmtree_refuse(chemin, **options):
        restes.add(str(chemin))
        raise PermissionError(13, "effacement refusé (essai)", str(chemin))

    monkeypatch.setattr(shutil, "rmtree", rmtree_refuse)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", execution.DossierJetableNonEfface)
            resultat = executer("print(1)", delai=DELAI)
    finally:
        monkeypatch.undo()
        for dossier in restes:
            effacer_pour_de_vrai(dossier, ignore_errors=True)
    assert resultat.reussi and resultat.sortie == "1\n"
    assert len(restes) == 1
    assert next(iter(restes)) in capsys.readouterr().err


def test_un_programme_qui_renvoie_le_code_de_l_amorce_reste_un_echec():
    """Après le départ, un code 198 vient du programme, pas de l'amorce : `echec`, pas `erreur_systeme`."""
    resultat = executer(f"import sys\nsys.exit({execution._CODE_SANS_DEPART})", delai=DELAI)
    assert resultat.raison == "echec"
    assert not resultat.reussi


def test_des_reglages_impossibles_sont_refuses():
    with pytest.raises(ValueError, match="delai"):
        executer("print(1)", delai=0)
    for delai in (float("inf"), float("nan")):
        with pytest.raises(ValueError, match="delai"):
            executer("print(1)", delai=delai)
    with pytest.raises(ValueError, match="memoire_mo"):
        executer("print(1)", memoire_mo=0)
    with pytest.raises(ValueError, match="sortie_max"):
        executer("print(1)", sortie_max=-1)


def test_executer_tous_garde_l_ordre():
    programmes = [
        "import time\ntime.sleep(0.5)\nprint(0)",
        "print(1)",
        "assert False",
        "import time\ntime.sleep(0.2)\nprint(3)",
    ]
    resultats = executer_tous(programmes, processus=4, delai=DELAI)
    assert [r.raison for r in resultats] == ["reussi", "reussi", "echec", "reussi"]
    assert resultats[0].sortie == "0\n"
    assert resultats[1].sortie == "1\n"
    assert resultats[3].sortie == "3\n"


def test_executer_tous_prend_par_defaut_les_fils_disponibles(monkeypatch):
    fils_demandes = []
    pool = execution.ThreadPoolExecutor

    def pool_espionne(max_workers):
        fils_demandes.append(max_workers)
        return pool(max_workers=max_workers)

    monkeypatch.setattr(execution, "fils_disponibles", lambda: 3)
    monkeypatch.setattr(execution, "ThreadPoolExecutor", pool_espionne)
    resultats = executer_tous(["print('a')", "print('b')"], delai=DELAI, sortie_max=1)
    assert fils_demandes == [3]
    assert [r.sortie for r in resultats] == ["a", "b"]


def test_executer_tous_refuse_zero_processus():
    with pytest.raises(ValueError, match="processus"):
        executer_tous(["print(1)"], processus=0)
