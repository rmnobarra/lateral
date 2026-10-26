"""Varre feature branches do próprio repositório — sem Gitea."""

from __future__ import annotations

from pathlib import Path

from lateral.engine import scan_heads, write_report
from lateral.gitops import run
from lateral.intents import attach as attach_intents


def _sha(repo: Path, ref: str) -> str:
    return run("git", "rev-parse", ref, cwd=repo).stdout.strip()


def _subject(repo: Path, ref: str) -> str:
    return run("git", "log", "-1", "--pretty=%s", ref, cwd=repo).stdout.strip()


def discover_heads(repo: Path, base: str = "main", remotes: bool = True) -> list[dict]:
    heads: list[dict] = []
    seen: set[str] = set()

    def add(ref: str, name: str) -> None:
        if name in seen or name == base:
            return
        seen.add(name)
        heads.append({
            "ref": name,
            "sha": _sha(repo, ref),
            "title": _subject(repo, ref),
            "body": "",
        })

    local = run("git", "for-each-ref", "--format=%(refname:short)", "refs/heads", cwd=repo)
    for name in local.stdout.splitlines():
        add(name, name)

    if remotes:
        remote = run("git", "for-each-ref", "--format=%(refname:short)", "refs/remotes", cwd=repo)
        for full in remote.stdout.splitlines():
            if full.endswith("/HEAD"):
                continue
            name = full.split("/", 1)[-1]
            add(full, name)
    return heads


def check_repo(
    repo: Path,
    *,
    base: str = "main",
    saida: Path | None = None,
    remotes: bool = True,
    n_exec: int = 1,
    with_intent: bool = False,
    model: str | None = None,
    transcripts: bool = True,
) -> dict:
    dest = saida or (repo / ".lateral" / "last")
    heads = attach_intents(
        repo,
        discover_heads(repo, base=base, remotes=remotes),
        base=base,
        transcripts=transcripts,
    )
    intents = {h["ref"]: h.get("intent_meta") for h in heads}
    if len(heads) < 2:
        report = {
            "repo": str(repo),
            "heads": heads,
            "intents": intents,
            "pares": [],
            "markdown": f"# Relatório Lateral\n\nPoucas feature branches ({len(heads)}). Nada a cruzar.\n",
        }
        write_report(report, dest)
        return report
    report = scan_heads(repo, heads, n_exec=n_exec, with_intent=with_intent, model=model)
    report["intents"] = intents
    write_report(report, dest)
    return report
