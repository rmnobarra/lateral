"""AXI: envelope JSON, exit 2 se dirty, intenção explícita no check."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from lateral.axi import envelope, exit_code, status
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


def test_status_vazio(tmp_path: Path) -> None:
    env = status(tmp_path)
    assert env["schema"] == "lateral.axi/v1"
    assert env["state"] == "empty"
    assert env["awaiting"] is None
    assert exit_code(env) == 0


def test_envelope_sam_gerado() -> None:
    env = envelope(
        command="check",
        report={"pares": [{
            "left": {"ref": "a"},
            "right": {"ref": "b"},
            "status": "candidato_semantico",
            "generate": {"status": "accepted", "teste": "test_lateral_contrato_limiar"},
        }]},
    )
    kinds = [f["kind"] for f in env["pares"][0]["findings"]]
    assert "sam_gerado" in kinds
    assert env["pares"][0]["generate"] == "accepted"
    assert env["awaiting"] == "human"


def test_envelope_ask_user() -> None:
    env = envelope(
        command="status",
        report={"pares": [{"left": {"ref": "a"}, "right": {"ref": "b"}, "status": "candidato_semantico",
                           "semantic": {"candidatos_estritos": ["test_frete"]}}]},
    )
    assert env["state"] == "dirty"
    assert env["awaiting"] == "human"
    assert env["pares"][0]["action"] == "ask-user"
    assert env["pares"][0]["findings"][0]["text"] == "test_frete"
    assert exit_code(env) == 2


def test_cli_axi_c01(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _branch(repo, "dev-a", "c01-centavos-frete", "a")
    _branch(repo, "dev-b", "c01-centavos-frete", "b")
    assert main(["axi", "intent", "--repo", str(repo), "--branch", "dev-a", "--text", "cobrar em centavos"]) == 0
    assert main(["axi", "intent", "--repo", str(repo), "--branch", "dev-b", "--text", "frete grátis abaixo de 100"]) == 0
    capsys.readouterr()
    code = main(["--no-intent", "axi", "check", "--repo", str(repo), "--local"])
    env = json.loads(capsys.readouterr().out)
    assert code == 2
    assert env["state"] == "dirty"
    assert env["awaiting"] == "human"
    assert env["pares"][0]["status"] == "candidato_semantico"
    assert env["intents"]["dev-a"]["source"] == "explicit"
    assert env["intents"]["dev-b"]["text"] == "frete grátis abaixo de 100"
    assert main(["axi", "status", "--repo", str(repo)]) == 2
