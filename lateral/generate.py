"""Gera um pytest candidato quando a suíte herdada é cega (fatia LUCIA).

O LLM só propõe o teste. O oráculo é pytest nas quatro versões:
passa nos pais onde coleta, falha no Merge. Caso contrário, descarta.
O arquivo nunca entra no working tree do usuário.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from lateral.gitops import Quad, add_worktree, changed_files, file_at, remove_worktree, run

REL = Path("tests") / "test_lateral_gerado.py"

SYSTEM = """Você gera UM teste pytest que detectaria conflito semântico entre
duas feature branches. O teste deve passar em cada lado sozinho e falhar
quando as duas mudanças se combinam (unidades, limiar, contrato).

Responda APENAS com um bloco ```python contendo:
- imports do código existente
- exatamente uma função `def test_...`

Não invente módulos. Não explique. Não use fixtures externas."""

_FENCE = re.compile(r"```(?:python)?\n(.*?)```", re.S)
_TEST_FN = re.compile(r"^def (test_\w+)\s*\(", re.M)


def extract_source(text: str) -> str | None:
    fences = _FENCE.findall(text or "")
    body = (fences[-1] if fences else text or "").strip()
    names = _TEST_FN.findall(body)
    if len(names) != 1:
        return None
    return body + "\n"


def complete(system: str, user: str, model: str | None = None) -> dict:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return {"skipped": True, "reason": "ANTHROPIC_API_KEY ausente"}
    try:
        import anthropic
    except ImportError:
        return {"skipped": True, "reason": "pacote anthropic não instalado"}
    client = anthropic.Anthropic(api_key=key)
    message = client.messages.create(
        model=model or os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5"),
        max_tokens=700,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(block.text for block in message.content if getattr(block, "type", "") == "text")
    return {
        "skipped": False,
        "text": text,
        "model": message.model,
        "usage": {
            "input": message.usage.input_tokens,
            "output": message.usage.output_tokens,
        },
    }


def propose(
    repo: Path,
    base: str,
    left: str,
    right: str,
    left_intent: str,
    right_intent: str,
    model: str | None = None,
) -> dict:
    result = complete(SYSTEM, _user(repo, base, left, right, left_intent, right_intent), model)
    if result.get("skipped"):
        return {"status": "skipped", "reason": result.get("reason")}
    source = extract_source(str(result.get("text") or ""))
    if not source:
        return {
            "status": "discarded",
            "reason": "resposta sem exatamente um def test_",
            "raw": result.get("text"),
            "model": result.get("model"),
        }
    return {
        "status": "proposed",
        "source": source,
        "teste": _TEST_FN.findall(source)[0],
        "model": result.get("model"),
        "usage": result.get("usage"),
    }


def _user(
    repo: Path,
    base: str,
    left: str,
    right: str,
    left_intent: str,
    right_intent: str,
) -> str:
    left_files = changed_files(repo, base, left)
    right_files = changed_files(repo, base, right)
    snippets = []
    for label, rev, files in (("left", left, left_files), ("right", right, right_files)):
        for path in files[:8]:
            text = file_at(repo, rev, path) or ""
            snippets.append(f"### {label} {path}\n```\n{text[:2500]}\n```")
    return (
        f"Intenção left:\n{left_intent}\n\n"
        f"Intenção right:\n{right_intent}\n\n"
        f"Arquivos left: {left_files}\nArquivos right: {right_files}\n\n"
        + "\n\n".join(snippets)
    )


def _run(worktree: Path) -> dict[str, str]:
    xml = worktree / "lateral-gerado.xml"
    run(
        "python3", "-m", "pytest", str(REL), "-q", "-p", "no:cacheprovider",
        f"--junitxml={xml}", cwd=worktree, check=False,
    )
    if not xml.exists():
        return {}
    import xml.etree.ElementTree as ET

    result: dict[str, str] = {}
    for tc in ET.parse(xml).iter("testcase"):
        name = f"{tc.get('classname')}::{tc.get('name')}"
        kids = {c.tag for c in tc}
        if "failure" in kids:
            result[name] = "fail"
        elif "error" in kids:
            result[name] = "error"
        elif "skipped" in kids:
            result[name] = "skip"
        else:
            result[name] = "pass"
    return result


def _version_status(execs: list[dict[str, str]]) -> str:
    if not any(execs):
        return "missing"
    values = {status for exec in execs for status in exec.values()}
    if not values:
        return "missing"
    if values == {"pass"}:
        return "pass"
    if values == {"fail"}:
        return "fail"
    if "error" in values:
        return "error"
    return "unstable"


def evaluate(repo: Path, quad: Quad, source: str, n_exec: int = 1) -> dict:
    if quad.textual_conflict or not quad.merge:
        return {"status": "skipped", "reason": "conflito_textual"}
    shas = {"B": quad.base, "L": quad.left, "R": quad.right, "M": quad.merge}
    trees: dict[str, Path] = {}
    with tempfile.TemporaryDirectory(prefix="lateral-gen-") as tmp:
        try:
            root = Path(tmp)
            for key, sha in shas.items():
                trees[key] = add_worktree(repo, root / f"{key}-{sha[:8]}", sha)
                dest = trees[key] / REL
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(source if source.endswith("\n") else source + "\n")
            runs = {key: [_run(path) for _ in range(n_exec)] for key, path in trees.items()}
        finally:
            for path in trees.values():
                remove_worktree(repo, path)

    versions = {key: _version_status(execs) for key, execs in runs.items()}
    names = sorted({name for execs in runs.get("M", []) for name in execs})
    teste = names[0] if names else (_TEST_FN.findall(source) or ["test_?"])[0]
    if versions["M"] not in {"fail", "error"}:
        return {"status": "discarded", "reason": f"Merge {versions['M']}", "versions": versions, "teste": teste}
    for parent in ("B", "L", "R"):
        if versions[parent] in {"fail", "unstable"}:
            return {
                "status": "discarded",
                "reason": f"{parent} {versions[parent]}",
                "versions": versions,
                "teste": teste,
            }
    if versions["L"] != "pass" and versions["R"] != "pass":
        return {
            "status": "discarded",
            "reason": "nenhum pai passou",
            "versions": versions,
            "teste": teste,
        }
    return {"status": "accepted", "teste": teste, "versions": versions, "source": source}


def analyze(
    repo: Path,
    quad: Quad,
    left_intent: str,
    right_intent: str,
    model: str | None = None,
    n_exec: int = 1,
) -> dict:
    proposed = propose(repo, quad.base, quad.left, quad.right, left_intent, right_intent, model)
    if proposed.get("status") != "proposed":
        return proposed
    verdict = evaluate(repo, quad, proposed["source"], n_exec=n_exec)
    for key in ("model", "usage", "source", "teste"):
        if key in proposed and key not in verdict:
            verdict[key] = proposed[key]
    return verdict
