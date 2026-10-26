"""Orquestra as camadas do Lateral sobre um par de commits."""

from __future__ import annotations

import itertools
import json
import tempfile
from pathlib import Path

from lateral.gitops import Quad, speculative_merge
from lateral.overlap import analyze as analyze_overlap
from lateral.report import pair_markdown, summary_markdown
from lateral.semantic import analyze as analyze_semantic


def scan_pair(
    repo: Path,
    left: str,
    right: str,
    *,
    left_meta: dict | None = None,
    right_meta: dict | None = None,
    left_intent: str = "",
    right_intent: str = "",
    n_exec: int = 1,
    with_intent: bool = False,
    model: str | None = None,
) -> dict:
    quad: Quad = speculative_merge(repo, left, right)
    overlap = analyze_overlap(repo, quad.base, left, right)
    pair: dict = {
        "left": left_meta or {"ref": left, "sha": left},
        "right": right_meta or {"ref": right, "sha": right},
        "base": quad.base,
        "textual_conflict": quad.textual_conflict,
        "conflict_files": quad.conflict_files,
        "overlap": overlap.as_dict(),
    }

    if quad.textual_conflict:
        pair["status"] = "conflito_textual"
        pair["semantic"] = {"status": "conflito_textual"}
    else:
        with tempfile.TemporaryDirectory() as tmp:
            semantic = analyze_semantic(repo, quad, Path(tmp), n_exec=n_exec)
        pair["semantic"] = semantic.as_dict()
        pair["status"] = semantic.status

    if with_intent:
        from lateral.intent import analyze as analyze_intent

        pair["intent"] = analyze_intent(
            repo, quad.base, left, right, left_intent, right_intent, model=model,
        )
        intent = pair["intent"]
        if (
            pair["status"] == "limpo"
            and not intent.get("skipped")
            and intent.get("severity") == "red"
        ):
            pair["status"] = "risco_intencao"

        sem_status = (pair.get("semantic") or {}).get("status")
        if (
            not quad.textual_conflict
            and sem_status == "limpo"
            and pair["status"] in {"limpo", "risco_intencao"}
        ):
            from lateral.generate import analyze as analyze_generate

            pair["generate"] = analyze_generate(
                repo, quad, left_intent, right_intent, model=model, n_exec=n_exec,
            )
            if pair["generate"].get("status") == "accepted":
                pair["status"] = "candidato_semantico"

    pair["markdown"] = pair_markdown(pair)
    return pair


def scan_heads(
    repo: Path,
    heads: list[dict],
    *,
    n_exec: int = 1,
    with_intent: bool = False,
    model: str | None = None,
) -> dict:
    """heads: [{ref, sha, title?, body?}, ...]"""
    pares = []
    for a, b in itertools.combinations(sorted(heads, key=lambda h: h["ref"]), 2):
        pares.append(
            scan_pair(
                repo,
                a["sha"],
                b["sha"],
                left_meta=a,
                right_meta=b,
                left_intent=a.get("body") or a.get("title") or "",
                right_intent=b.get("body") or b.get("title") or "",
                n_exec=n_exec,
                with_intent=with_intent,
                model=model,
            )
        )
    report = {"repo": str(repo), "heads": heads, "pares": pares}
    report["markdown"] = summary_markdown(report)
    return report


def write_report(report: dict, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    json_path = dest / "lateral.json"
    md_path = dest / "lateral.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    parts = [report.get("markdown", "")]
    for pair in report.get("pares") or []:
        parts.append(pair.get("markdown", ""))
    md_path.write_text("\n".join(parts))
    return json_path
