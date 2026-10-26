"""Camada de intenção: Haiku compara as tarefas das branches.

Detecta trabalho duplicado e risco de conflito de contrato que os testes
podem não cobrir. Só roda se ANTHROPIC_API_KEY estiver definida.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from lateral.gitops import changed_files, file_at


SYSTEM = """Você é o revisor de intenção do Lateral (Lateral).
Compare duas feature branches ativas. Responda APENAS JSON válido com as chaves:
{
  "duplicate_work": true/false,
  "contract_risk": true/false,
  "severity": "green"|"yellow"|"red",
  "summary": "uma frase",
  "assumptions": ["suposição de A que B pode invalidar", "..."]
}
duplicate_work = as duas tarefas implementam a mesma capacidade.
contract_risk = uma branch muda unidade, assinatura, invariante ou cache
que a outra branch assume. Não invente arquivos que não existam."""


def analyze(
    repo: Path,
    base: str,
    left: str,
    right: str,
    left_intent: str,
    right_intent: str,
    model: str | None = None,
) -> dict:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return {"skipped": True, "reason": "ANTHROPIC_API_KEY ausente"}

    try:
        import anthropic
    except ImportError:
        return {"skipped": True, "reason": "pacote anthropic não instalado"}

    left_files = changed_files(repo, base, left)
    right_files = changed_files(repo, base, right)
    snippets = []
    for label, rev, files in (("left", left, left_files), ("right", right, right_files)):
        for path in files[:8]:
            text = file_at(repo, rev, path) or ""
            snippets.append(f"### {label} {path}\n```\n{text[:2500]}\n```")

    user = (
        f"Intenção left:\n{left_intent}\n\n"
        f"Intenção right:\n{right_intent}\n\n"
        f"Arquivos left: {left_files}\nArquivos right: {right_files}\n\n"
        + "\n\n".join(snippets)
    )
    client = anthropic.Anthropic(api_key=key)
    message = client.messages.create(
        model=model or os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5"),
        max_tokens=600,
        system=SYSTEM,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(block.text for block in message.content if getattr(block, "type", "") == "text")
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        return {"skipped": False, "raw": text, "parse_error": True}
    parsed = json.loads(text[start : end + 1])
    parsed["model"] = message.model
    parsed["usage"] = {
        "input": message.usage.input_tokens,
        "output": message.usage.output_tokens,
    }
    return parsed
