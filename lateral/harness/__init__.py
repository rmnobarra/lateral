"""Instaladores por harness. Gitea é só o laboratório; o produto vive no repo."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from lateral.harness import agy, claude, codex, cursor, kiro

HARNESSES: dict[str, Callable[[], dict[str, str]]] = {
    "cursor": cursor.files,
    "claude": claude.files,
    "kiro": kiro.files,
    "codex": codex.files,
    "agy": agy.files,
}

MARKERS = {
    ".cursor": "cursor",
    ".claude": "claude",
    "CLAUDE.md": "claude",
    ".kiro": "kiro",
    ".codex": "codex",
    ".agents": "agy",
}


def detect(root: Path) -> list[str]:
    found: list[str] = []
    for marker, name in MARKERS.items():
        if (root / marker).exists() and name not in found:
            found.append(name)
    return found


def parse_harnesses(raw: str | None, root: Path) -> list[str]:
    if raw:
        names = [part.strip().lower() for part in raw.split(",") if part.strip()]
        if names == ["all"]:
            names = list(HARNESSES)
    else:
        names = detect(root) or ["cursor"]
    unknown = [n for n in names if n not in HARNESSES]
    if unknown:
        raise SystemExit(f"harness desconhecido: {', '.join(unknown)}. Use: {', '.join(HARNESSES)}")
    return names
