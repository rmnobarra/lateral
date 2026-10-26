"""Transcript: casa arquivo, redige segredo, ignora tool output."""

from __future__ import annotations

import json
from pathlib import Path

from lateral.transcripts import infer, redact


def _jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def test_redact_chave() -> None:
    assert "[redacted]" in redact("ANTHROPIC_API_KEY=sk-ant-secretvalue123")


def test_infer_casa_arquivo_e_user_query(tmp_path: Path) -> None:
    _jsonl(
        tmp_path / "chat.jsonl",
        [
            {
                "role": "user",
                "message": {
                    "content": [{
                        "type": "text",
                        "text": "<user_query>mude loja/precos.py para centavos</user_query>",
                    }],
                },
            },
            {
                "role": "assistant",
                "message": {"content": [{"type": "text", "text": "ok"}]},
            },
        ],
    )
    got = infer(["loja/precos.py"], roots=[tmp_path])
    assert got["skipped"] is False
    assert got["source"] == "transcript"
    assert got["confidence"] == "low"
    assert "centavos" in got["text"]
    assert "ok" not in got["text"]


def test_infer_sem_match(tmp_path: Path) -> None:
    _jsonl(
        tmp_path / "chat.jsonl",
        [{"role": "user", "message": {"content": [{"type": "text", "text": "outra coisa"}]}}],
    )
    got = infer(["loja/precos.py"], roots=[tmp_path])
    assert got["skipped"] is True
    assert got["text"] == ""
