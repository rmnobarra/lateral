"""check: descobre feature branches locais e escreve o relatório no repo."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from lateral.check import check_repo, discover_heads
from lateral.cli import main
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


def _branch(repo: Path, name: str, scenario: str, side: str) -> None:
    _git(repo, "checkout", "-b", name, "main")
    apply(repo, scenario, side)
    _commit(repo, name)
    _git(repo, "checkout", "main")


def test_discover_ignora_base(repo: Path) -> None:
    _branch(repo, "dev-a", "c01-centavos-frete", "a")
    names = {h["ref"] for h in discover_heads(repo, remotes=False)}
    assert names == {"dev-a"}


def test_check_c01_escreve_relatorio(repo: Path) -> None:
    _branch(repo, "dev-a", "c01-centavos-frete", "a")
    _branch(repo, "dev-b", "c01-centavos-frete", "b")
    report = check_repo(repo, remotes=False)
    assert report["pares"][0]["status"] == "candidato_semantico"
    assert (repo / ".lateral" / "last" / "lateral.md").exists()


def test_cli_check_poucas_branches(tmp_path: Path) -> None:
    repo = tmp_path / "vazio"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    (repo / "a.txt").write_text("x")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-m", "s"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    assert main(["check", "--repo", str(repo), "--local"]) == 0
    assert "Poucas feature branches" in (repo / ".lateral" / "last" / "lateral.md").read_text()
