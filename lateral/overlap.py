"""Camada de consciência de workspace (Palantír / Grove).

Não executa merge. Compara os diffs de cada branch contra a base comum
e classifica sobreposição de arquivo e hunk.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path

from lateral.gitops import changed_files, run


@dataclass
class Overlap:
    files_left: list[str]
    files_right: list[str]
    shared_files: list[str]
    hunk_overlaps: list[dict]
    severity: str  # green | yellow | red

    def as_dict(self) -> dict:
        return asdict(self)


_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def _hunks(repo: Path, base: str, head: str, path: str) -> list[tuple[int, int]]:
    diff = run("git", "diff", "-U0", f"{base}...{head}", "--", path, cwd=repo).stdout
    ranges: list[tuple[int, int]] = []
    for line in diff.splitlines():
        m = _HUNK.match(line)
        if not m:
            continue
        start = int(m.group(3))
        count = int(m.group(4) or "1")
        ranges.append((start, start + max(count, 1)))
    return ranges


def _intersect(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def analyze(repo: Path, base: str, left: str, right: str) -> Overlap:
    left_files = changed_files(repo, base, left)
    right_files = changed_files(repo, base, right)
    shared = sorted(set(left_files) & set(right_files))
    hunks: list[dict] = []
    for path in shared:
        lh = _hunks(repo, base, left, path)
        rh = _hunks(repo, base, right, path)
        hits = [
            {"file": path, "left": list(a), "right": list(b)}
            for a in lh
            for b in rh
            if _intersect(a, b)
        ]
        hunks.extend(hits)

    if hunks:
        severity = "red"
    elif shared:
        severity = "yellow"
    else:
        severity = "green"
    return Overlap(left_files, right_files, shared, hunks, severity)
