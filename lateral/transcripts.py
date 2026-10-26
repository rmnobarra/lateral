"""Fallback de intenção: transcripts locais, sem gravar o texto cru."""

from __future__ import annotations

import json
import re
from pathlib import Path

SECRETS = (
    re.compile(r"sk-ant-[A-Za-z0-9_-]+"),
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"(?:api[_-]?key|token|secret)\s*[:=]\s*\S+", re.I),
)
USER_QUERY = re.compile(r"<user_query>\s*(.*?)\s*</user_query>", re.S)
CLAMP = 4000


def redact(text: str) -> str:
    for pattern in SECRETS:
        text = pattern.sub("[redacted]", text)
    return text


def clamp(text: str, limit: int = CLAMP) -> str:
    if len(text) <= limit:
        return text
    keep = (limit - 5) // 2
    return text[:keep] + "\n…\n" + text[-keep:]


def _user_blob(obj: object) -> str:
    if not isinstance(obj, dict):
        return ""
    role = obj.get("role") or obj.get("type") or ""
    if str(role).lower() not in {"user", "human"}:
        return ""
    message = obj.get("message") if isinstance(obj.get("message"), dict) else obj
    content = message.get("content") if isinstance(message, dict) else None
    parts: list[str] = []
    if isinstance(content, str):
        parts.append(content)
    elif isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") in {None, "text"}:
                parts.append(str(item.get("text") or ""))
            elif isinstance(item, str):
                parts.append(item)
    raw = "\n".join(p for p in parts if p)
    match = USER_QUERY.search(raw)
    return (match.group(1) if match else raw).strip()


def _iter_jsonl(path: Path) -> list[str]:
    texts: list[str] = []
    try:
        for line in path.read_text(errors="replace").splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            blob = _user_blob(obj)
            if blob:
                texts.append(blob)
    except OSError:
        return []
    return texts


def default_roots(repo: Path | None, home: Path | None = None) -> list[Path]:
    home = home or Path.home()
    roots: list[Path] = []
    if repo is None:
        return roots
    slug = str(repo.resolve()).lstrip("/").replace("/", "-")
    cursor = home / ".cursor" / "projects" / slug / "agent-transcripts"
    if cursor.is_dir():
        roots.append(cursor)
    claude = home / ".claude" / "projects"
    if claude.is_dir():
        for child in claude.iterdir():
            if child.is_dir() and (repo.name in child.name or slug in child.name):
                roots.append(child)
    return roots


def infer(
    files: list[str],
    *,
    repo: Path | None = None,
    roots: list[Path] | None = None,
    home: Path | None = None,
) -> dict:
    search = roots if roots is not None else default_roots(repo, home)
    needles = [path for path in files if path]
    names = {Path(path).name for path in needles}
    best_text = ""
    best_score = 0
    source_path = ""
    for root in search:
        for jsonl in root.rglob("*.jsonl"):
            users = _iter_jsonl(jsonl)
            if not users:
                continue
            blob = "\n".join(users)
            score = sum(blob.count(path) for path in needles) + sum(blob.count(name) for name in names)
            if needles and score == 0:
                continue
            if not needles:
                score = len(users)
            if score > best_score:
                best_score = score
                best_text = blob
                source_path = str(jsonl)
    if not best_text:
        return {"text": "", "source": "transcript", "confidence": "none", "skipped": True, "reason": "sem transcript"}
    return {
        "text": clamp(redact(best_text)),
        "source": "transcript",
        "confidence": "low",
        "skipped": False,
        "reason": source_path,
    }
