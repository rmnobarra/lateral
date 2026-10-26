"""Superfície máquina do Lateral. JSON no stdout; o harness não parseia markdown."""

from __future__ import annotations

import json
from pathlib import Path

from lateral.intents import load as load_intents

SCHEMA = "lateral.axi/v1"

_ACTIONS = {
    "limpo": ("no-op", "info"),
    "conflito_textual": ("ask-user", "error"),
    "pais_nao_buildam": ("ask-user", "error"),
    "conflito_build": ("ask-user", "error"),
    "base_nao_builda": ("ask-user", "error"),
    "candidato_semantico": ("ask-user", "error"),
    "risco_intencao": ("ask-user", "warning"),
}


def _ref(side: object) -> str:
    if isinstance(side, dict):
        return str(side.get("ref") or side.get("sha") or "")
    return str(side)


def _finding_id(pair_id: str, index: int) -> str:
    return f"F{index}"


def pair_record(pair: dict, *, start: int = 1) -> dict:
    status = str(pair.get("status") or "limpo")
    action, severity = _ACTIONS.get(status, ("ask-user", "warning"))
    left, right = _ref(pair.get("left")), _ref(pair.get("right"))
    pair_id = f"{left}|{right}"
    findings: list[dict] = []
    n = start
    semantic = pair.get("semantic") or {}
    for teste in semantic.get("candidatos_estritos") or []:
        findings.append({"id": _finding_id(pair_id, n), "kind": "sam", "text": str(teste)})
        n += 1
    for item in semantic.get("candidatos_estendidos") or []:
        nome = item.get("teste") if isinstance(item, dict) else item
        findings.append({"id": _finding_id(pair_id, n), "kind": "sam", "text": str(nome)})
        n += 1
    if pair.get("textual_conflict"):
        for item in pair.get("conflict_files") or ["git merge-tree"]:
            findings.append({"id": _finding_id(pair_id, n), "kind": "textual", "text": str(item)})
            n += 1
    intent = pair.get("intent") or {}
    if intent and not intent.get("skipped") and intent.get("severity") in {"red", "yellow"}:
        findings.append({
            "id": _finding_id(pair_id, n),
            "kind": "intent",
            "text": str(intent.get("summary") or "risco de intenção"),
        })
        n += 1
    generate = pair.get("generate") or {}
    if generate.get("status") == "accepted":
        findings.append({
            "id": _finding_id(pair_id, n),
            "kind": "sam_gerado",
            "text": str(generate.get("teste") or "teste gerado"),
        })
        n += 1
    if status != "limpo" and not findings:
        findings.append({"id": _finding_id(pair_id, n), "kind": status, "text": status})
    return {
        "id": pair_id,
        "left": left,
        "right": right,
        "status": status,
        "action": action,
        "severity": severity,
        "findings": findings,
        "generate": generate.get("status"),
    }


def _intents_from(report: dict, root: Path | None) -> dict:
    found = dict(report.get("intents") or {})
    if not found and root is not None:
        stored = load_intents(root)
        for head in report.get("heads") or []:
            name = _ref(head)
            meta = (head.get("intent_meta") if isinstance(head, dict) else None) or stored.get(name)
            if meta:
                found[name] = meta
    return found


def envelope(
    *,
    command: str,
    report: dict | None,
    dest: Path | None = None,
    root: Path | None = None,
    extra: dict | None = None,
) -> dict:
    pares = [pair_record(p) for p in (report or {}).get("pares") or []]
    dirty = [p for p in pares if p["status"] != "limpo"]
    if report is None:
        state = "empty"
    elif not pares:
        state = "empty"
    elif dirty:
        state = "dirty"
    else:
        state = "ready"
    awaiting = "human" if any(p["action"] == "ask-user" for p in pares) else None
    env = {
        "schema": SCHEMA,
        "command": command,
        "state": state,
        "awaiting": awaiting,
        "report_path": str(dest / "lateral.json") if dest else None,
        "pares": pares,
        "intents": _intents_from(report or {}, root),
        "help": (
            "rode `python -m lateral axi check`"
            if state == "empty" and command == "status"
            else "o Lateral acusa; não mescle; não apague teste vermelho"
        ),
    }
    if extra:
        env.update(extra)
    return env


def load_last(root: Path) -> dict | None:
    path = root / ".lateral" / "last" / "lateral.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def status(root: Path) -> dict:
    dest = root / ".lateral" / "last"
    report = load_last(root)
    return envelope(command="status", report=report, dest=dest if report else None, root=root)


def from_report(report: dict, *, dest: Path, root: Path | None = None) -> dict:
    return envelope(command="check", report=report, dest=dest, root=root)


def dump(env: dict) -> str:
    return json.dumps(env, ensure_ascii=False, indent=2)


def exit_code(env: dict) -> int:
    if env.get("state") == "dirty":
        return 2
    return 0
