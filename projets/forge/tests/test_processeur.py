"""Tests du nombre de fils de calcul : celui que ce processus a le droit d'utiliser (`forge.processeur`)."""

import os

from forge.processeur import fils_disponibles


def test_fils_disponibles_prend_d_abord_process_cpu_count(monkeypatch):
    """Python 3.13 et plus : `os.process_cpu_count()` tient compte de l'affinité du processus."""
    monkeypatch.setattr(os, "process_cpu_count", lambda: 6, raising=False)
    monkeypatch.setattr(os, "sched_getaffinity", lambda pid: {0, 1, 2}, raising=False)
    monkeypatch.setattr(os, "cpu_count", lambda: 16)
    assert fils_disponibles() == 6


def test_fils_disponibles_sinon_l_affinite(monkeypatch):
    """Python 3.12 sous Linux : les cœurs que l'affinité laisse (`taskset`, un conteneur…)."""
    monkeypatch.delattr(os, "process_cpu_count", raising=False)
    monkeypatch.setattr(os, "sched_getaffinity", lambda pid: {0, 1, 2}, raising=False)
    monkeypatch.setattr(os, "cpu_count", lambda: 16)
    assert fils_disponibles() == 3


def test_fils_disponibles_sinon_tous_les_coeurs(monkeypatch):
    """Python 3.12 sous Windows : ni l'un ni l'autre, on prend tous les cœurs logiques."""
    monkeypatch.delattr(os, "process_cpu_count", raising=False)
    monkeypatch.delattr(os, "sched_getaffinity", raising=False)
    monkeypatch.setattr(os, "cpu_count", lambda: 16)
    assert fils_disponibles() == 16
    monkeypatch.setattr(os, "cpu_count", lambda: None)  # nombre inconnu : au moins un fil
    assert fils_disponibles() == 1
