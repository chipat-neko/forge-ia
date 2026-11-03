"""Tests de `forge suivi` : l'état d'un entraînement, lu dans un journal factice.

Les journaux sont écrits à la main, ligne par ligne, comme `forge entrainer` les écrit : une
ligne JSON par pas ({"pas", "jetons_vus", "perte", "taux", "jetons_par_seconde", "secondes"},
plus "perte_val" de temps en temps) et une ligne par évènement ({"evenement", "pas", …}).
Aucun de ces tests n'a besoin de PyTorch, sauf celui qui compare la lecture de la
configuration à celle de l'entraînement.

Le suivi regarde aussi si un processus `forge entrainer` tourne pour la configuration (sans
lui, un journal qui ne finit ni par une pause ni par la fin veut dire « arrêté sans pause »).
Sauf dans le test de cette recherche, elle est remplacée par la fixture `processus`.
"""

import io
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from forge.__main__ import main
from forge.suivi import PAS_RECENTS, PERTES_RECENTES, afficher, entrainement_actif, lire_reglages

RACINE_DU_PROJET = Path(__file__).resolve().parents[1]
FINE = "\u202f"  # l'espace fine insécable, avant « : » et « % » et entre les milliers

TAILLE_LOT = 524_288


def ecrire_config(dossier: Path, pas_total: int = 100) -> Path:
    """Une configuration comme `configs/principal.toml`, dont la sortie est `dossier/essai`."""
    fichier = dossier / "essai.toml"
    fichier.write_text(
        "\n".join(
            [
                'preset = "tres_grand"',
                'donnees = "principal"',
                f"jetons_total = {pas_total * TAILLE_LOT}",
                f"taille_lot_jetons = {TAILLE_LOT}",
                "micro_lot = 1",
                "taux_max = 4e-4",
                "echauffement = 500",
                "evaluation_tous_pas = 200",
                f"sortie = '{dossier / 'essai'}'",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return fichier


def pas_(pas: int, secondes: float, perte: float | None = None, **autres) -> dict:
    """La ligne de journal d'un pas, avec une perte qui baisse doucement par défaut."""
    return {
        "pas": pas,
        "jetons_vus": pas * TAILLE_LOT,
        "perte": 10.4 - 0.01 * pas if perte is None else perte,
        "taux": 1e-4,
        "jetons_par_seconde": 17_000.0,
        "secondes": secondes,
        **autres,
    }


def ecrire_journal(dossier: Path, lignes: list, fin_coupee: str | None = None) -> Path:
    """Écrit `dossier/essai/journal.jsonl`."""
    chemin = dossier / "essai" / "journal.jsonl"
    chemin.parent.mkdir(parents=True, exist_ok=True)
    texte = "".join(json.dumps(ligne, ensure_ascii=False) + "\n" for ligne in lignes)
    chemin.write_text(texte + (fin_coupee or ""), encoding="utf-8")
    return chemin


@pytest.fixture(autouse=True)
def processus(monkeypatch):
    """Par défaut, l'entraînement « tourne » ; `processus["actif"] = False` l'arrête."""
    etat = {"actif": True}
    monkeypatch.setattr("forge.suivi.entrainement_actif", lambda reglages: etat["actif"])
    return etat


def suivi(capsys, config: Path) -> str:
    assert main(["suivi", "--config", str(config)]) == 0
    sortie = capsys.readouterr()
    assert sortie.err == ""
    return sortie.out


def debut_du_journal() -> list[dict]:
    return [
        {"evenement": "debut", "pas": 0, "message": "Début de l'entraînement : 100 pas."},
        {"evenement": "compilation", "pas": 0, "message": "torch.compile indisponible (…) : mode immédiat."},
    ]


# --- Les états -------------------------------------------------------------------------


def test_jamais_lance_sans_journal(tmp_path, capsys):
    config = ecrire_config(tmp_path)
    texte = suivi(capsys, config)
    assert f"Entraînement « essai »{FINE}: jamais lancé" in texte
    assert str(tmp_path / "essai" / "journal.jsonl") in texte
    assert f"python -m forge entrainer --config {config}" in texte
    assert "--reprendre" not in texte


def test_jamais_lance_avec_un_journal_vide(tmp_path, capsys):
    config = ecrire_config(tmp_path)
    ecrire_journal(tmp_path, [])
    assert f"{FINE}: jamais lancé" in suivi(capsys, config)


def test_en_cours(tmp_path, capsys):
    config = ecrire_config(tmp_path, pas_total=100)
    lignes = debut_du_journal()
    for pas in range(1, 31):
        ligne = pas_(pas, 30.0 * pas)
        if pas == 20:
            ligne["perte_val"] = 9.75
        lignes.append(ligne)
        if pas == 20:
            lignes.append({"evenement": "sauvegarde", "pas": 20, "fichier": "etape-0000020.pt"})
    ecrire_journal(tmp_path, lignes)

    texte = suivi(capsys, config)
    assert f"Entraînement « essai »{FINE}: en cours" in texte
    assert f"Pas{FINE}: 30 sur 100 (30{FINE}%)" in texte
    assert f"Jetons vus{FINE}: 15{FINE}728{FINE}640 sur 52{FINE}428{FINE}800" in texte
    # Dernière perte 10,4 − 0,30 = 10,100 ; moyenne des 20 derniers pas (11 à 30) : 10,4 − 0,205.
    assert f"Dernière perte{FINE}: 10,100 (moyenne des {PERTES_RECENTES} derniers pas{FINE}: 10,195)" in texte
    assert f"Dernière validation{FINE}: 9,750 (pas 20)" in texte
    # 524 288 jetons toutes les 30 secondes : 17 476 jetons/s ; il reste 70 pas de 30 s.
    assert f"Débit récent{FINE}: 17{FINE}476 jetons/s" in texte
    assert f"Temps restant estimé{FINE}: 35 min 00 s" in texte
    assert f"Dernière sauvegarde{FINE}: etape-0000020.pt (pas 20)" in texte


def test_en_pause(tmp_path, capsys, processus):
    processus["actif"] = False
    config = ecrire_config(tmp_path, pas_total=100)
    lignes = debut_du_journal() + [pas_(pas, 30.0 * pas) for pas in range(1, 13)]
    lignes += [
        {"evenement": "sauvegarde", "pas": 12, "fichier": "etape-0000012.pt"},
        {"evenement": "pause", "pas": 12},
    ]
    ecrire_journal(tmp_path, lignes)

    texte = suivi(capsys, config)
    assert f"Entraînement « essai »{FINE}: en pause au pas 12" in texte
    assert f"Pas{FINE}: 12 sur 100" in texte
    assert f"Dernière validation{FINE}: aucune pour l'instant" in texte
    assert f"Dernière sauvegarde{FINE}: etape-0000012.pt (pas 12)" in texte
    assert f"Temps restant estimé{FINE}: 44 min 00 s" in texte  # 88 pas de 30 s
    assert f"Pour reprendre{FINE}: python -m forge entrainer --config {config} --reprendre" in texte
    assert "planté" not in texte


def test_fini(tmp_path, capsys, processus):
    processus["actif"] = False
    config = ecrire_config(tmp_path, pas_total=100)
    lignes = debut_du_journal() + [pas_(pas, 30.0 * pas) for pas in range(1, 101)]
    lignes[-1]["perte_val"] = 3.5
    lignes += [
        {"evenement": "sauvegarde", "pas": 100, "fichier": "etape-0000100.pt"},
        {"evenement": "fin", "pas": 100},
    ]
    ecrire_journal(tmp_path, lignes)

    texte = suivi(capsys, config)
    assert f"Entraînement « essai »{FINE}: fini" in texte
    assert f"Pas{FINE}: 100 sur 100 (100{FINE}%)" in texte
    assert f"Dernière validation{FINE}: 3,500 (pas 100)" in texte
    assert f"Dernière sauvegarde{FINE}: etape-0000100.pt (pas 100)" in texte
    assert "Temps restant" not in texte
    assert "--reprendre" not in texte


def test_derniere_ligne_a_moitie_ecrite(tmp_path, capsys):
    """La ligne en cours d'écriture (coupée au milieu) est ignorée : on lit celle d'avant."""
    config = ecrire_config(tmp_path)
    lignes = debut_du_journal() + [pas_(pas, 30.0 * pas) for pas in range(1, 6)]
    ecrire_journal(tmp_path, lignes, fin_coupee='{"pas": 6, "jetons_vus": 31457')

    texte = suivi(capsys, config)
    assert f"{FINE}: en cours" in texte
    assert f"Pas{FINE}: 5 sur 100" in texte
    assert f"Dernière perte{FINE}: 10,350" in texte


def test_premier_pas_pas_encore_fait(tmp_path, capsys):
    config = ecrire_config(tmp_path)
    ecrire_journal(tmp_path, debut_du_journal())

    texte = suivi(capsys, config)
    assert f"{FINE}: en cours" in texte
    assert f"Pas{FINE}: 0 sur 100" in texte
    assert f"Dernière perte{FINE}: aucun pas fini pour l'instant" in texte
    assert f"Dernière sauvegarde{FINE}: aucune pour l'instant" in texte
    assert f"Temps restant estimé{FINE}: inconnu" in texte


def test_arrete_sans_pause(tmp_path, capsys, processus):
    """Ni pause ni fin au bout du journal, et plus aucun processus : plantage ou coupure."""
    processus["actif"] = False
    config = ecrire_config(tmp_path)
    lignes = debut_du_journal() + [pas_(pas, 30.0 * pas) for pas in range(1, 6)]
    ecrire_journal(tmp_path, lignes)

    texte = suivi(capsys, config)
    assert f"Entraînement « essai »{FINE}: arrêté sans pause au pas 5" in texte
    assert "planté" in texte
    assert f"python -m forge entrainer --config {config} --reprendre" in texte
    assert f"Pas{FINE}: 5 sur 100" in texte


def test_en_cours_tant_que_le_processus_tourne(tmp_path, capsys, processus):
    """Le journal seul ne dit pas si l'entraînement tourne encore : c'est le processus qui le dit.

    (Sur un disque exFAT, la date de modification du journal reste celle de son ouverture tant
    que l'entraînement le garde ouvert : elle ne peut pas servir.)
    """
    config = ecrire_config(tmp_path)
    ecrire_journal(tmp_path, debut_du_journal() + [pas_(pas, 30.0 * pas) for pas in range(1, 6)])
    assert f"{FINE}: en cours" in suivi(capsys, config)
    processus["actif"] = False
    assert f"{FINE}: arrêté sans pause" in suivi(capsys, config)


def test_perte_infinie(tmp_path, capsys, processus):
    processus["actif"] = False
    config = ecrire_config(tmp_path)
    lignes = debut_du_journal() + [pas_(pas, 30.0 * pas) for pas in range(1, 6)]
    lignes.append({"evenement": "perte_non_finie", "pas": 6, "message": "perte nan, norme des gradients nan"})
    ecrire_journal(tmp_path, lignes)

    texte = suivi(capsys, config)
    assert f"Entraînement « essai »{FINE}: arrêté, la perte est devenue infinie au pas 6" in texte
    assert "taux_max" in texte


# --- Le débit et le temps restant ------------------------------------------------------


def test_temps_restant_au_debit_recent(tmp_path, capsys):
    """Les premiers pas lents (chauffe) ne comptent plus : seuls les PAS_RECENTS derniers pas."""
    config = ecrire_config(tmp_path, pas_total=200)
    lents = 50
    lignes = debut_du_journal() + [pas_(pas, 60.0 * pas) for pas in range(1, lents + 1)]
    lignes += [pas_(pas, 60.0 * lents + 30.0 * (pas - lents)) for pas in range(lents + 1, lents + PAS_RECENTS + 1)]
    ecrire_journal(tmp_path, lignes)

    texte = suivi(capsys, config)
    assert f"Pas{FINE}: 150 sur 200" in texte
    assert f"Débit récent{FINE}: 17{FINE}476 jetons/s (sur les {PAS_RECENTS} derniers pas" in texte
    assert f"Temps restant estimé{FINE}: 25 min 00 s" in texte  # 50 pas de 30 s


def test_temps_restant_sans_compter_les_pauses(tmp_path, capsys):
    """`secondes` ne compte pas le temps passé en pause : une pause de 10 heures ne change rien."""
    config = ecrire_config(tmp_path, pas_total=100)
    lignes = debut_du_journal() + [pas_(pas, 30.0 * pas) for pas in range(1, 11)]
    lignes += [
        {"evenement": "sauvegarde", "pas": 10, "fichier": "etape-0000010.pt"},
        {"evenement": "pause", "pas": 10},
        {"evenement": "reprise", "pas": 10, "message": "Reprise au pas 10 sur 100."},
        {"evenement": "compilation", "pas": 10, "message": "mode immédiat"},
    ]
    lignes += [pas_(pas, 300.0 + 30.0 * (pas - 10)) for pas in range(11, 21)]
    ecrire_journal(tmp_path, lignes)

    texte = suivi(capsys, config)
    assert f"{FINE}: en cours" in texte
    assert f"Temps restant estimé{FINE}: 40 min 00 s" in texte  # 80 pas de 30 s
    assert f"Dernière sauvegarde{FINE}: etape-0000010.pt (pas 10)" in texte


def test_un_seul_pas_donne_son_propre_debit(tmp_path, capsys):
    config = ecrire_config(tmp_path, pas_total=100)
    ecrire_journal(tmp_path, debut_du_journal() + [pas_(1, 31.0, jetons_par_seconde=17_476.3)])

    texte = suivi(capsys, config)
    assert f"Débit récent{FINE}: 17{FINE}476 jetons/s (sur le dernier pas)" in texte
    assert f"Temps restant estimé{FINE}: 49 min 30 s" in texte  # 99 × 524 288 / 17 476,3 ≈ 2 970 s


def test_temps_restant_en_jours(tmp_path, capsys):
    config = ecrire_config(tmp_path, pas_total=16_540)
    ecrire_journal(tmp_path, debut_du_journal() + [pas_(pas, 29.0 * pas) for pas in range(1, 41)])
    # 16 500 pas de 29 s : 478 500 s, soit 5 j 12 h 55 min.
    assert f"Temps restant estimé{FINE}: 5 j 12 h" in suivi(capsys, config)


# --- La configuration -----------------------------------------------------------------


def test_configuration_introuvable(tmp_path, capsys):
    assert main(["suivi", "--config", str(tmp_path / "absente.toml")]) == 1
    erreur = capsys.readouterr().err
    assert "introuvable" in erreur
    assert str(tmp_path / "absente.toml") in erreur


def test_configuration_incomplete(tmp_path, capsys):
    fichier = tmp_path / "incomplete.toml"
    fichier.write_text('preset = "mini"\n', encoding="utf-8")
    assert main(["suivi", "--config", str(fichier)]) == 1
    erreur = capsys.readouterr().err
    assert "jetons_total" in erreur and "taille_lot_jetons" in erreur and "sortie" in erreur


@pytest.mark.parametrize("nom", ["principal.toml", "mini.toml"])
def test_reglages_lus_comme_l_entrainement(nom, tmp_path, monkeypatch):
    """Le suivi lit la configuration sans PyTorch : il doit trouver la même sortie et le même nombre de pas."""
    from forge.entrainement import lire_config  # importe PyTorch : seulement dans ce test

    monkeypatch.setenv("FORGE_DONNEES", str(tmp_path))
    fichier = RACINE_DU_PROJET / "configs" / nom
    reglages, config = lire_reglages(fichier), lire_config(fichier)
    assert reglages.dossier_sortie == config.dossier_sortie
    assert reglages.pas_total == config.pas_total
    assert reglages.taille_lot_jetons == config.taille_lot_jetons


def test_suivi_n_importe_pas_pytorch(tmp_path):
    """Le suivi tourne toutes les quelques minutes pendant l'entraînement : il reste léger."""
    config = ecrire_config(tmp_path)
    ecrire_journal(tmp_path, debut_du_journal() + [pas_(1, 30.0)])
    code = (
        "import sys\n"
        "from forge.__main__ import main\n"
        f"assert main(['suivi', '--config', {str(config)!r}]) == 0\n"
        "print('torch importé :', 'torch' in sys.modules)\n"
    )
    resultat = subprocess.run(
        [sys.executable, "-c", code],
        cwd=RACINE_DU_PROJET,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONUTF8": "1"},
        timeout=120,
    )
    assert resultat.returncode == 0, resultat.stderr
    assert resultat.stdout.strip().endswith("torch importé : False")


def test_affichage_sur_une_sortie_sans_espace_fine():
    """Sans PYTHONUTF8, une sortie redirigée sous Windows est en cp1252, qui n'a pas l'espace fine."""
    flux = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", newline="\n")
    afficher(f"Pas{FINE}: 1{FINE}234 sur 16{FINE}540 (7,4{FINE}%) « été »", flux)
    flux.flush()
    assert flux.buffer.getvalue().decode("cp1252") == "Pas : 1 234 sur 16 540 (7,4 %) « été »\n"


def _attendre(condition, secondes: float = 15) -> bool:
    limite = time.monotonic() + secondes
    while time.monotonic() < limite:
        if condition():
            return True
        time.sleep(0.2)
    return condition()


def test_entrainement_actif_reconnait_le_processus(tmp_path):
    """Un vrai processus dont la ligne de commande est « … -m forge entrainer --config <fichier> »."""
    config = ecrire_config(tmp_path)
    (tmp_path / "autre").mkdir()
    autre = ecrire_config(tmp_path / "autre")  # le même nom de fichier, dans un autre dossier
    reglages, reglages_autres = lire_reglages(config), lire_reglages(autre)
    assert entrainement_actif(reglages) is False

    # `python -c` laisse le reste de la ligne de commande sans le lire : un faux entraînement.
    faux = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(120)", "-m", "forge", "entrainer", "--config", str(config)]
    )
    try:
        assert _attendre(lambda: entrainement_actif(reglages))
        assert entrainement_actif(reglages_autres) is False
    finally:
        faux.kill()
        faux.wait()
    assert _attendre(lambda: entrainement_actif(reglages) is False)


def test_entrainement_actif_avec_un_chemin_relatif(tmp_path, monkeypatch):
    """« --config configs\\principal.toml » se lit depuis le dossier où l'entraînement a été lancé."""
    (tmp_path / "configs").mkdir()
    config = ecrire_config(tmp_path / "configs")
    commande = ["-m", "forge", "entrainer", "--config", "configs/essai.toml"]
    faux = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)", *commande], cwd=tmp_path)
    try:
        monkeypatch.chdir(tmp_path)
        assert _attendre(lambda: entrainement_actif(lire_reglages("configs/essai.toml")))
        assert entrainement_actif(lire_reglages(config)) is True  # le même fichier, en chemin absolu
    finally:
        faux.kill()
        faux.wait()
