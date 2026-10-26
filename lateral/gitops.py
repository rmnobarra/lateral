"""Operações git usadas pelo motor: merge-base, merge-tree, worktrees."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

GIT_IDENT = {
    "GIT_AUTHOR_NAME": "lateral",
    "GIT_AUTHOR_EMAIL": "lateral@lab.local",
    "GIT_COMMITTER_NAME": "lateral",
    "GIT_COMMITTER_EMAIL": "lateral@lab.local",
}


def run(*args: str, cwd: str | Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, **GIT_IDENT}
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, env=env)
    if check and result.returncode != 0:
        raise RuntimeError(f"{' '.join(args)}: {result.stderr.strip() or result.stdout.strip()}")
    return result


@dataclass(frozen=True)
class Quad:
    """As quatro versões de um par (SAM / Crystal)."""

    base: str
    left: str
    right: str
    merge: str | None
    merge_tree: str
    textual_conflict: bool
    conflict_files: list[str]


def merge_base(repo: Path, left: str, right: str) -> str:
    return run("git", "merge-base", left, right, cwd=repo).stdout.strip()


def changed_files(repo: Path, base: str, head: str) -> list[str]:
    out = run("git", "diff", "--name-only", f"{base}...{head}", cwd=repo).stdout
    return [line for line in out.splitlines() if line]


def file_at(repo: Path, rev: str, path: str) -> str | None:
    result = run("git", "show", f"{rev}:{path}", cwd=repo, check=False)
    if result.returncode != 0:
        return None
    return result.stdout


def speculative_merge(repo: Path, left: str, right: str) -> Quad:
    base = merge_base(repo, left, right)
    mt = run("git", "merge-tree", "--write-tree", left, right, cwd=repo, check=False)
    textual = mt.returncode != 0
    lines = [line for line in mt.stdout.splitlines() if line]
    tree = lines[0].split()[0] if lines else ""
    conflict_files: list[str] = []
    if textual:
        names = run("git", "merge-tree", "-z", left, right, cwd=repo, check=False)
        # fallback: parse classic conflict markers from stdout
        for line in mt.stdout.splitlines():
            if line.startswith("CONFLICT") or "Merge conflict in" in line:
                conflict_files.append(line)
        if not conflict_files:
            conflict_files = [line for line in names.stdout.splitlines() if line and not line.startswith(tree)]
        return Quad(base, left, right, None, mt.stdout, True, conflict_files[:40])

    merge = run(
        "git",
        "commit-tree",
        tree,
        "-p",
        left,
        "-p",
        right,
        "-m",
        "lateral synthetic merge",
        cwd=repo,
    ).stdout.strip()
    return Quad(base, left, right, merge, mt.stdout, False, [])


def add_worktree(repo: Path, dest: Path, sha: str) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    run("git", "worktree", "add", "-q", "--detach", str(dest), sha, cwd=repo)
    return dest


def remove_worktree(repo: Path, dest: Path) -> None:
    run("git", "worktree", "remove", "--force", str(dest), cwd=repo, check=False)
