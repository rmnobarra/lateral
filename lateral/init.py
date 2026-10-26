"""Instala o Lateral num repositório: config + skills/commands do harness."""

from __future__ import annotations

import tomllib
from pathlib import Path

from lateral.harness import HARNESSES, parse_harnesses

BEGIN = "<!-- BEGIN LATERAL -->"
END = "<!-- END LATERAL -->"

AGENTS_BLOCK = """<!-- BEGIN LATERAL -->
## Lateral

Este repositório tem Lateral instalado.

- Check (humano): `python -m lateral check`
- Check (harness): `python -m lateral axi check`
- Status: `python -m lateral axi status`
- Intenção: `python -m lateral axi intent --branch NOME --text "…"`
- Relatório: `.lateral/last/lateral.md` · envelope AXI no stdout

O Lateral acusa. Não mescla. Não apaga teste que falhou no Merge.
<!-- END LATERAL -->
"""


def _write(path: Path, text: str, force: bool) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force and path.read_text() == text:
        return "igual"
    if path.exists() and not force:
        return "existe"
    path.write_text(text)
    return "escreveu"


def _write_config(root: Path, harnesses: list[str], base: str, intent: bool) -> None:
    dest = root / ".lateral" / "config.toml"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        "harnesses = [" + ", ".join(f'"{h}"' for h in harnesses) + "]\n"
        f'base_branch = "{base}"\n'
        f"intent = {'true' if intent else 'false'}\n"
        "intent_transcripts = true\n"
    )


IGNORE_LINES = (".lateral/last/", ".lateral/intents.json")


def _ensure_gitignore(root: Path) -> str:
    path = root / ".gitignore"
    if not path.exists():
        path.write_text("\n".join(IGNORE_LINES) + "\n")
        return "criou"
    text = path.read_text()
    missing = [line for line in IGNORE_LINES if line not in text]
    if not missing:
        return "igual"
    path.write_text(text.rstrip() + "\n" + "\n".join(missing) + "\n")
    return "anexou"


CLAUDE_BLOCK = """<!-- BEGIN LATERAL -->
## Lateral

Verificador cruzado entre feature branches. Harness: `python -m lateral axi check`. Humano: leia `.lateral/last/lateral.md`.
Intenção: `python -m lateral axi intent --branch NOME --text "…"`. O Lateral acusa; não mescla.
<!-- END LATERAL -->
"""


def _upsert_named(root: Path, name: str, block: str) -> str:
    path = root / name
    if not path.exists():
        path.write_text(f"# {name}\n\n" + block)
        return "criou"
    text = path.read_text()
    if BEGIN in text and END in text:
        pre, rest = text.split(BEGIN, 1)
        _, post = rest.split(END, 1)
        path.write_text(pre.rstrip() + "\n\n" + block + post.lstrip("\n"))
        return "atualizou"
    path.write_text(text.rstrip() + "\n\n" + block)
    return "anexou"


def load_config(root: Path) -> dict:
    path = root / ".lateral" / "config.toml"
    if not path.exists():
        return {"harnesses": [], "base_branch": "main", "intent": True, "intent_transcripts": True}
    data = tomllib.loads(path.read_text())
    return {
        "harnesses": list(data.get("harnesses") or []),
        "base_branch": str(data.get("base_branch") or "main"),
        "intent": bool(data.get("intent")),
        "intent_transcripts": bool(data.get("intent_transcripts", True)),
    }


def install(
    root: Path,
    *,
    harnesses: list[str] | None = None,
    raw: str | None = None,
    base: str = "main",
    intent: bool = True,
    force: bool = True,
) -> dict:
    names = harnesses or parse_harnesses(raw, root)
    written: list[str] = []
    skipped: list[str] = []
    for name in names:
        for rel, content in HARNESSES[name]().items():
            status = _write(root / rel, content, force=force)
            (written if status == "escreveu" else skipped).append(rel)
    extras = {
        "AGENTS.md": _upsert_named(root, "AGENTS.md", AGENTS_BLOCK),
        ".gitignore": _ensure_gitignore(root),
    }
    if "claude" in names:
        extras["CLAUDE.md"] = _upsert_named(root, "CLAUDE.md", CLAUDE_BLOCK)
    _write_config(root, names, base, intent)
    return {
        "harnesses": names,
        "wrote": written,
        "skipped": skipped,
        "extras": extras,
        "agents_md": extras["AGENTS.md"],
        "config": str(root / ".lateral" / "config.toml"),
    }
