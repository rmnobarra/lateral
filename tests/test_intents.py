"""Intenção explícita vence transcript e subject."""

from __future__ import annotations

from pathlib import Path

import pytest

from lateral.intents import INTENT_MAX, get, normalize_text, put, resolve


def test_put_get_roundtrip(tmp_path: Path) -> None:
    record = put(tmp_path, "feature/foo", "  Cobrar em centavos\n")
    assert record["source"] == "explicit"
    assert record["confidence"] == "high"
    assert get(tmp_path, "feature/foo")["text"] == "Cobrar em centavos"


def test_normalize_rejeita_vazio_e_grande() -> None:
    with pytest.raises(ValueError):
        normalize_text("  \n")
    with pytest.raises(ValueError):
        normalize_text("x" * (INTENT_MAX + 1))


def test_resolve_explicita_vence_body(tmp_path: Path) -> None:
    put(tmp_path, "dev-a", "tarefa A")
    got = resolve(tmp_path, branch="dev-a", body="corpo do PR", title="subject", transcripts=False)
    assert got["source"] == "explicit"
    assert got["text"] == "tarefa A"


def test_resolve_cai_no_subject(tmp_path: Path) -> None:
    got = resolve(tmp_path, branch="dev-a", title="frete grátis", transcripts=False)
    assert got["source"] == "commit"
    assert got["confidence"] == "low"
    assert got["text"] == "frete grátis"
