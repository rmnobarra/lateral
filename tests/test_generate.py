"""Geração de teste: Haiku propõe; pytest nas quatro versões aceita ou descarta."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from lateral.engine import scan_pair
from lateral.generate import analyze, evaluate, extract_source
from lateral.gitops import speculative_merge
from lab.fixtures import apply

SEED = Path(__file__).resolve().parents[1] / "lab" / "seed"

VALID = '''from pack.mod import g


def test_lateral_contrato_limiar():
    assert g() is True
'''

JUNK = "isto não é um teste python\n"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _commit(repo: Path, message: str) -> None:
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-m", message)


@pytest.fixture
def mini(tmp_path: Path) -> Path:
    repo = tmp_path / "mini"
    repo.mkdir()
    (repo / "pack").mkdir()
    (repo / "pack" / "__init__.py").write_text("")
    (repo / "pack" / "mod.py").write_text("X = 1\n\ndef f():\n    return X\n")
    (repo / "tests").mkdir()
    (repo / "tests" / "test_mod.py").write_text(
        "from pack.mod import f\n\ndef test_f():\n    assert f() == 1\n"
    )
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "mini"\nversion = "0"\nrequires-python = ">=3.11"\n\n'
        "[tool.pytest.ini_options]\npythonpath = [\".\"]\ntestpaths = [\"tests\"]\n"
    )
    _git(repo, "init", "-b", "main")
    _commit(repo, "seed")

    _git(repo, "checkout", "-b", "dev-a", "main")
    (repo / "pack" / "mod.py").write_text("X = 100\n\ndef f():\n    return X\n")
    _commit(repo, "centavos")
    _git(repo, "checkout", "main")

    _git(repo, "checkout", "-b", "dev-b", "main")
    (repo / "pack" / "mod.py").write_text(
        "X = 1\n\ndef f():\n    return X\n\ndef g():\n    return f() < 50\n"
    )
    _commit(repo, "limiar")
    _git(repo, "checkout", "main")
    return repo


def test_extract_um_teste() -> None:
    src = extract_source("```python\nfrom x import y\n\ndef test_ok():\n    assert y\n```")
    assert src is not None
    assert "def test_ok" in src


def test_extract_rejeita_lixo() -> None:
    assert extract_source(JUNK) is None
    assert extract_source("def foo():\n    return 1\n") is None


def test_evaluate_aceita(mini: Path) -> None:
    left = _git(mini, "rev-parse", "dev-a").stdout.strip()
    right = _git(mini, "rev-parse", "dev-b").stdout.strip()
    quad = speculative_merge(mini, left, right)
    verdict = evaluate(mini, quad, VALID)
    assert verdict["status"] == "accepted"
    assert "test_lateral_contrato_limiar" in str(verdict.get("teste"))


def test_evaluate_descarta_lixo(mini: Path) -> None:
    left = _git(mini, "rev-parse", "dev-a").stdout.strip()
    right = _git(mini, "rev-parse", "dev-b").stdout.strip()
    quad = speculative_merge(mini, left, right)
    verdict = evaluate(mini, quad, "def test_quebrado():\n    raise SyntaxError\n")
    assert verdict["status"] == "discarded"


def test_analyze_pula_sem_chave(mini: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    left = _git(mini, "rev-parse", "dev-a").stdout.strip()
    right = _git(mini, "rev-parse", "dev-b").stdout.strip()
    quad = speculative_merge(mini, left, right)
    out = analyze(mini, quad, "a", "b")
    assert out["status"] == "skipped"


def test_scan_pair_promove_sam_gerado(mini: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "lateral.intent.analyze",
        lambda *a, **k: {"skipped": True, "reason": "teste"},
    )
    monkeypatch.setattr(
        "lateral.generate.analyze",
        lambda *a, **k: {"status": "accepted", "teste": "test_lateral_contrato_limiar"},
    )
    left = _git(mini, "rev-parse", "dev-a").stdout.strip()
    right = _git(mini, "rev-parse", "dev-b").stdout.strip()
    pair = scan_pair(mini, left, right, with_intent=True)
    assert pair["status"] == "candidato_semantico"
    assert pair["generate"]["status"] == "accepted"


def test_scan_pair_nao_gera_se_sam_herdado(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import shutil

    seed = tmp_path / "loja"
    shutil.copytree(SEED, seed, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    _git(seed, "init", "-b", "main")
    _commit(seed, "seed")

    def _branch(name: str, side: str) -> str:
        _git(seed, "checkout", "-b", name, "main")
        apply(seed, "c01-centavos-frete", side)
        _commit(seed, name)
        sha = _git(seed, "rev-parse", "HEAD").stdout.strip()
        _git(seed, "checkout", "main")
        return sha

    called = {"n": 0}

    def boom(*a, **k):
        called["n"] += 1
        raise AssertionError("generate não deveria rodar")

    monkeypatch.setattr("lateral.generate.analyze", boom)
    monkeypatch.setattr("lateral.intent.analyze", lambda *a, **k: {"skipped": True})
    left = _branch("dev-a", "a")
    right = _branch("dev-b", "b")
    pair = scan_pair(seed, left, right, with_intent=True)
    assert pair["status"] == "candidato_semantico"
    assert called["n"] == 0
    assert "generate" not in pair
