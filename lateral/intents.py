"""Intenção por branch: explícita vence; transcript e subject são fallback."""

from __future__ import annotations

import json
from pathlib import Path

from lateral.gitops import changed_files, run

INTENT_MAX = 16_384
STORE = Path(".lateral") / "intents.json"


def store_path(root: Path) -> Path:
    return root / STORE


def load(root: Path) -> dict[str, dict]:
    path = store_path(root)
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        return {}
    return {str(k): dict(v) for k, v in data.items() if isinstance(v, dict)}


def save(root: Path, data: dict[str, dict]) -> Path:
    path = store_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return path


def normalize_text(raw: str) -> str:
    text = raw.replace("\r\n", "\n")
    if len(text.encode()) > INTENT_MAX:
        raise ValueError(f"intenção maior que {INTENT_MAX} bytes")
    stripped = text.strip()
    if not stripped:
        raise ValueError("intenção vazia")
    return stripped


def put(root: Path, branch: str, text: str, *, source: str = "explicit") -> dict:
    branch = branch.strip()
    if not branch or branch in {".", "HEAD"}:
        branch = current_branch(root)
    record = {
        "text": normalize_text(text),
        "source": source,
        "confidence": "high" if source == "explicit" else "low",
    }
    data = load(root)
    data[branch] = record
    save(root, data)
    return {"branch": branch, **record}


def get(root: Path, branch: str) -> dict | None:
    return load(root).get(branch)


def current_branch(repo: Path) -> str:
    name = run("git", "rev-parse", "--abbrev-ref", "HEAD", cwd=repo).stdout.strip()
    if not name or name == "HEAD":
        raise ValueError("HEAD destacado: passe --branch")
    return name


def _commit_subject(repo: Path, ref: str) -> str:
    return run("git", "log", "-1", "--pretty=%s", ref, cwd=repo, check=False).stdout.strip()


def resolve(
    root: Path,
    *,
    branch: str,
    sha: str | None = None,
    base: str = "main",
    body: str = "",
    title: str = "",
    transcripts: bool = True,
) -> dict:
    """explicit > transcript > body/PR > subject do commit > vazio."""
    explicit = get(root, branch)
    if explicit and explicit.get("text"):
        return {
            "text": explicit["text"],
            "source": "explicit",
            "confidence": "high",
            "skipped": False,
        }

    if transcripts:
        try:
            from lateral.transcripts import infer

            files = changed_files(root, base, sha or branch) if sha or branch else []
            guessed = infer(files, repo=root)
            if guessed.get("text"):
                return guessed
        except Exception as exc:  # noqa: BLE001 — fallback nunca derruba o check
            guessed = {"skipped": True, "reason": str(exc)}
    else:
        guessed = {"skipped": True, "reason": "transcripts desligados"}

    if body.strip():
        return {"text": body.strip(), "source": "pr", "confidence": "low", "skipped": False}
    subject = title.strip() or _commit_subject(root, sha or branch)
    if subject:
        return {"text": subject, "source": "commit", "confidence": "low", "skipped": False}
    return {
        "text": "",
        "source": "missing",
        "confidence": "none",
        "skipped": True,
        "reason": guessed.get("reason") or "sem intenção",
    }


def attach(root: Path, heads: list[dict], *, base: str = "main", transcripts: bool = True) -> list[dict]:
    for head in heads:
        resolved = resolve(
            root,
            branch=str(head.get("ref") or ""),
            sha=str(head.get("sha") or ""),
            base=base,
            body=str(head.get("body") or ""),
            title=str(head.get("title") or ""),
            transcripts=transcripts,
        )
        head["body"] = resolved["text"]
        head["intent_meta"] = resolved
    return heads
