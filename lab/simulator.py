"""Simula um desenvolvedor com a API da Anthropic (Haiku) ou aplica fixture."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from lab.fixtures import apply as apply_fixture

ROOT = Path(__file__).resolve().parent
TOOLS = [
    {
        "name": "list_dir",
        "description": "Lista arquivos do repositório, relativos à raiz.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Diretório relativo, default ."}},
        },
    },
    {
        "name": "read_file",
        "description": "Lê um arquivo de texto do repositório.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Escreve (cria ou sobrescreve) um arquivo de texto.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"],
        },
    },
    {
        "name": "run_pytest",
        "description": "Roda pytest no repositório.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


def sh(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=True)


def _tool(worktree: Path, name: str, args: dict) -> str:
    if name == "list_dir":
        rel = args.get("path") or "."
        base = (worktree / rel).resolve()
        if not str(base).startswith(str(worktree.resolve())):
            return "caminho fora do repositório"
        lines = []
        for path in sorted(base.rglob("*")):
            if any(part in {".git", "__pycache__", ".pytest_cache"} for part in path.parts):
                continue
            lines.append(str(path.relative_to(worktree)))
        return "\n".join(lines) or "(vazio)"
    if name == "read_file":
        path = worktree / args["path"]
        if not path.exists():
            return f"não existe: {args['path']}"
        return path.read_text()
    if name == "write_file":
        path = worktree / args["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(args["content"])
        return f"escrito {args['path']} ({len(args['content'])} bytes)"
    if name == "run_pytest":
        r = subprocess.run(
            ["python3", "-m", "pytest", "-q", "-p", "no:cacheprovider"],
            cwd=worktree, capture_output=True, text=True,
        )
        return (r.stdout + r.stderr)[-4000:]
    return f"ferramenta desconhecida: {name}"


def run_agent(worktree: Path, tarefa: str, model: str) -> dict:
    import anthropic

    client = anthropic.Anthropic()
    system = (
        "Você é um desenvolvedor. Implemente a tarefa no repositório local. "
        "Use as ferramentas. Escreva testes. Não commit. Não invente dependências. "
        "Não grave __pycache__ nem arquivos binários. Quando terminar, responda DONE."
    )
    messages = [{"role": "user", "content": f"Tarefa:\n{tarefa}"}]
    usage = {"input": 0, "output": 0}
    for step in range(18):
        resp = client.messages.create(
            model=model,
            max_tokens=4096,
            system=system,
            tools=TOOLS,
            messages=messages,
        )
        usage["input"] += resp.usage.input_tokens
        usage["output"] += resp.usage.output_tokens
        tool_uses = [b for b in resp.content if b.type == "tool_use"]
        text = "".join(b.text for b in resp.content if b.type == "text")
        messages.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason == "end_turn" and not tool_uses:
            return {"steps": step + 1, "final": text, "usage": usage, "model": resp.model}
        results = []
        for block in tool_uses:
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": _tool(worktree, block.name, block.input),
            })
        messages.append({"role": "user", "content": results})
    return {"steps": 18, "final": "max steps", "usage": usage, "model": model}


def publish(worktree: Path, remote: str, branch: str, title: str, body: str, gitea_url: str, token: str, repo: str) -> None:
    sh("git", "checkout", "-B", branch, cwd=worktree)
    sh("git", "add", "-A", cwd=worktree)
    status = subprocess.run(["git", "status", "--porcelain"], cwd=worktree, capture_output=True, text=True)
    if not status.stdout.strip():
        raise RuntimeError("agente não alterou nenhum arquivo")
    sh("git", "-c", "user.name=lab", "-c", "user.email=lab@lab.local", "commit", "-m", title, cwd=worktree)
    sh("git", "push", "-u", remote, branch, cwd=worktree)
    from lateral.gitea import Gitea

    owner, name = repo.split("/", 1)
    for attempt in range(5):
        try:
            Gitea(gitea_url, token).create_pull(owner, name, title, branch, "main", body)
            return
        except RuntimeError:
            if attempt == 4:
                raise
            time.sleep(1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--side", required=True, choices=["a", "b"])
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--clone", required=True)
    parser.add_argument("--remote-url", required=True)
    parser.add_argument("--gitea", default=os.environ.get("GITEA_URL", "http://localhost:3310"))
    parser.add_argument("--token", default=os.environ.get("GITEA_TOKEN", ""))
    parser.add_argument("--repo", default="lab/loja")
    parser.add_argument("--fixture", action="store_true")
    parser.add_argument("--saida", default=".")
    parser.add_argument("--model", default=os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5"))
    args = parser.parse_args()

    scenario_dir = ROOT / "scenarios" / args.scenario
    tarefa = (scenario_dir / f"tarefa-{args.side}.md").read_text()
    worktree = Path(args.clone)
    branch = f"dev-{args.side}"
    title = f"[{args.side}] {args.scenario}"

    if args.fixture:
        apply_fixture(worktree, args.scenario, args.side)
        meta = {"mode": "fixture", "scenario": args.scenario, "side": args.side}
    else:
        meta = run_agent(worktree, tarefa, args.model)
        meta.update({"mode": "haiku", "scenario": args.scenario, "side": args.side})

    publish(worktree, args.remote_url, branch, title, tarefa, args.gitea, args.token, args.repo)
    dest = Path(args.saida)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / f"agente-{args.side}.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print(json.dumps(meta, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
