"""Instalador: skills/commands do harness + config no repositório alvo."""

from __future__ import annotations

from pathlib import Path

import pytest

from lateral.cli import main
from lateral.harness import HARNESSES, detect, parse_harnesses
from lateral.init import install, load_config


def test_parse_all_e_desconhecido(tmp_path: Path) -> None:
    assert parse_harnesses("all", tmp_path) == list(HARNESSES)
    with pytest.raises(SystemExit):
        parse_harnesses("vscode", tmp_path)


def test_detect_por_marcador(tmp_path: Path) -> None:
    (tmp_path / ".kiro").mkdir()
    (tmp_path / "CLAUDE.md").write_text("# x\n")
    assert detect(tmp_path) == ["claude", "kiro"]


def test_install_escreve_harness_e_config(tmp_path: Path) -> None:
    result = install(tmp_path, harnesses=["cursor", "claude"], base="develop")
    assert result["harnesses"] == ["cursor", "claude"]
    assert (tmp_path / ".cursor/skills/lateral/SKILL.md").exists()
    assert (tmp_path / ".cursor/commands/lateral.md").exists()
    assert (tmp_path / ".claude/commands/lateral-scan.md").exists()
    assert "BEGIN LATERAL" in (tmp_path / "AGENTS.md").read_text()
    assert "BEGIN LATERAL" in (tmp_path / "CLAUDE.md").read_text()
    assert ".lateral/last/" in (tmp_path / ".gitignore").read_text()
    cfg = load_config(tmp_path)
    assert cfg["base_branch"] == "develop"
    assert cfg["intent"] is True
    assert cfg["harnesses"] == ["cursor", "claude"]


def test_install_keep_nao_sobrescreve(tmp_path: Path) -> None:
    skill = tmp_path / ".cursor/skills/lateral/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("custom")
    result = install(tmp_path, harnesses=["cursor"], force=False)
    assert skill.read_text() == "custom"
    assert ".cursor/skills/lateral/SKILL.md" in result["skipped"]


def test_cli_init_all(tmp_path: Path) -> None:
    assert main(["init", "--repo", str(tmp_path), "--harness", "all"]) == 0
    for factory in HARNESSES.values():
        for rel in factory():
            assert (tmp_path / rel).exists(), rel
    assert load_config(tmp_path)["intent"] is True


def test_cli_init_sem_intent(tmp_path: Path) -> None:
    assert main(["init", "--repo", str(tmp_path), "--harness", "cursor", "--sem-intent"]) == 0
    assert load_config(tmp_path)["intent"] is False
