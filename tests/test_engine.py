"""Testa o motor Lateral num repositório sintético, sem Gitea e sem API."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from lateral.engine import scan_pair
from lab.fixtures import apply

SEED = Path(__file__).resolve().parents[1] / "lab" / "seed"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _commit(repo: Path, message: str) -> None:
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-m", message)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    seed = tmp_path / "loja"
    shutil.copytree(SEED, seed, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    _git(seed, "init", "-b", "main")
    _commit(seed, "seed")
    return seed


def _branch(repo: Path, name: str, scenario: str, side: str) -> str:
    _git(repo, "checkout", "-b", name, "main")
    apply(repo, scenario, side)
    _commit(repo, name)
    sha = _git(repo, "rev-parse", "HEAD").stdout.strip()
    _git(repo, "checkout", "main")
    return sha


def test_c01_detecta_semantico(repo: Path) -> None:
    left = _branch(repo, "dev-a", "c01-centavos-frete", "a")
    right = _branch(repo, "dev-b", "c01-centavos-frete", "b")
    pair = scan_pair(repo, left, right)
    assert pair["textual_conflict"] is False
    assert pair["status"] == "candidato_semantico"
    tests = [pair["semantic"]["candidatos_estritos"], pair["semantic"]["candidatos_estendidos"]]
    assert any(tests)


def test_c02_limpo(repo: Path) -> None:
    left = _branch(repo, "dev-a", "c02-inocuo-frete", "a")
    right = _branch(repo, "dev-b", "c02-inocuo-frete", "b")
    pair = scan_pair(repo, left, right)
    assert pair["status"] == "limpo"
    assert pair["overlap"]["severity"] == "green"


def test_c04_overlap_ou_textual(repo: Path) -> None:
    left = _branch(repo, "dev-a", "c04-duplicata-frete", "a")
    right = _branch(repo, "dev-b", "c04-duplicata-frete", "b")
    pair = scan_pair(repo, left, right)
    assert pair["overlap"]["shared_files"]
    assert pair["status"] in {"conflito_textual", "candidato_semantico", "limpo"}
    if pair["status"] != "conflito_textual":
        assert pair["overlap"]["severity"] in {"yellow", "red"}
