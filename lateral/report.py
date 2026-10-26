"""Relatórios em JSON e Markdown para PRs e apresentação."""

from __future__ import annotations


def pair_markdown(pair: dict) -> str:
    left = pair["left"]
    right = pair["right"]
    lines = [
        f"## Lateral: {left.get('ref', left)} × {right.get('ref', right)}",
        "",
        f"**Status:** `{pair['status']}`",
        f"**Overlap:** `{pair.get('overlap', {}).get('severity', '?')}`",
        "",
    ]
    overlap = pair.get("overlap") or {}
    if overlap.get("shared_files"):
        lines.append("Arquivos tocados pelos dois lados:")
        for path in overlap["shared_files"]:
            lines.append(f"- `{path}`")
        lines.append("")
    if pair.get("textual_conflict"):
        lines.append("Conflito textual no `git merge-tree`.")
        for item in pair.get("conflict_files") or []:
            lines.append(f"- {item}")
        lines.append("")
    semantic = pair.get("semantic") or {}
    if semantic.get("candidatos_estritos") or semantic.get("candidatos_estendidos"):
        lines.append("Candidatos semânticos (teste passa nos pais e falha no Merge):")
        for teste in semantic.get("candidatos_estritos") or []:
            lines.append(f"- estrito: `{teste}`")
        for item in semantic.get("candidatos_estendidos") or []:
            lines.append(f"- estendido: `{item['teste']}` (adicionado por {item['adicionado_por']})")
        lines.append("")
    for side, label in ((left, "left"), (right, "right")):
        meta = side.get("intent_meta") if isinstance(side, dict) else None
        if meta and meta.get("text"):
            lines.append(
                f"Intenção {label} ({meta.get('source', '?')}, {meta.get('confidence', '?')}): "
                f"{meta['text'].splitlines()[0][:160]}"
            )
    intent = pair.get("intent") or {}
    if intent and not intent.get("skipped"):
        lines.append(f"Intenção ({intent.get('severity', '?')}): {intent.get('summary', '')}")
        for assumption in intent.get("assumptions") or []:
            lines.append(f"- {assumption}")
        lines.append("")
    generate = pair.get("generate") or {}
    if generate.get("status") == "accepted":
        lines.append(f"Teste gerado (SAM): `{generate.get('teste', '?')}`")
        lines.append("")
    elif generate.get("status") == "discarded":
        lines.append(f"Teste gerado descartado: {generate.get('reason', '?')}")
        lines.append("")
    lines.append("_O Lateral propõe; um humano decide o que fazer._")
    return "\n".join(lines)


def summary_markdown(report: dict) -> str:
    lines = ["# Relatório Lateral", "", f"Repositório: `{report.get('repo', '')}`", ""]
    for pair in report.get("pares") or []:
        left = pair["left"]
        right = pair["right"]
        lref = left.get("ref", left) if isinstance(left, dict) else left
        rref = right.get("ref", right) if isinstance(right, dict) else right
        lines.append(f"- `{lref}` × `{rref}` → **{pair['status']}**")
    if not report.get("pares"):
        lines.append("Nenhum par de branches ativas.")
    lines.append("")
    return "\n".join(lines)
