"""CLI: `python -m lateral` ou `lateral`."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from lateral.axi import dump, exit_code, from_report, status as axi_status
from lateral.check import check_repo
from lateral.engine import scan_pair, scan_heads, write_report
from lateral.gitea import Gitea
from lateral.init import install, load_config
from lateral.intents import current_branch, put as put_intent, resolve


def cmd_init(args: argparse.Namespace) -> int:
    root = Path(args.repo).resolve()
    result = install(
        root,
        raw=args.harness,
        base=args.base,
        intent=not args.sem_intent,
        force=not args.keep,
    )
    print(f"harnesses: {', '.join(result['harnesses'])}")
    for name, status in result["extras"].items():
        print(f"{name}: {status}")
    print(f"config: {result['config']}")
    for path in result["wrote"]:
        print(f"  + {path}")
    if result["skipped"]:
        print("já existiam (use sem --keep para sobrescrever):")
        for path in result["skipped"]:
            print(f"  · {path}")
    print("Pronto. No harness: /lateral")
    return 0


def _check_kwargs(args: argparse.Namespace, root: Path) -> dict:
    cfg = load_config(root)
    return {
        "base": args.base or cfg["base_branch"],
        "saida": Path(args.saida) if args.saida else root / ".lateral" / "last",
        "remotes": not args.local,
        "n_exec": args.execucoes,
        "with_intent": _with_intent(args, cfg["intent"]),
        "model": args.model,
        "transcripts": cfg.get("intent_transcripts", True),
    }


def _with_intent(args: argparse.Namespace, cfg_intent: bool | None = None) -> bool:
    if getattr(args, "no_intent", False):
        return False
    if getattr(args, "intent", False):
        return True
    return True if cfg_intent is None else bool(cfg_intent)


def cmd_check(args: argparse.Namespace) -> int:
    root = Path(args.repo).resolve()
    report = check_repo(root, **_check_kwargs(args, root))
    print(report["markdown"])
    return 2 if any(p["status"] != "limpo" for p in report["pares"]) else 0


def _read_intent_arg(args: argparse.Namespace) -> str:
    if args.file == "-" or args.text == "-":
        return sys.stdin.read()
    if args.file:
        path = Path(args.file)
        if not path.is_file():
            raise SystemExit(f"arquivo de intenção ausente: {path}")
        return path.read_text()
    return args.text


def cmd_axi_status(args: argparse.Namespace) -> int:
    env = axi_status(Path(args.repo).resolve())
    print(dump(env))
    return exit_code(env)


def cmd_axi_check(args: argparse.Namespace) -> int:
    root = Path(args.repo).resolve()
    kwargs = _check_kwargs(args, root)
    report = check_repo(root, **kwargs)
    env = from_report(report, dest=kwargs["saida"], root=root)
    print(dump(env))
    return exit_code(env)


def cmd_axi_intent(args: argparse.Namespace) -> int:
    root = Path(args.repo).resolve()
    if not args.text and not args.file:
        print("passe --text ou --file", file=sys.stderr)
        return 2
    try:
        branch = args.branch or current_branch(root)
        record = put_intent(root, branch, _read_intent_arg(args))
    except ValueError as exc:
        print(dump({
            "schema": "lateral.axi/v1",
            "command": "intent",
            "state": "error",
            "awaiting": None,
            "help": str(exc),
        }), file=sys.stderr)
        return 2
    print(dump({
        "schema": "lateral.axi/v1",
        "command": "intent",
        "state": "ready",
        "awaiting": None,
        "intents": {record["branch"]: record},
        "help": "intenção explícita gravada; rode `python -m lateral axi check`",
    }))
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    left_intent = args.left_intent or resolve(repo, branch=args.left, sha=args.left)["text"]
    right_intent = args.right_intent or resolve(repo, branch=args.right, sha=args.right)["text"]
    pair = scan_pair(
        repo,
        args.left,
        args.right,
        left_intent=left_intent,
        right_intent=right_intent,
        n_exec=args.execucoes,
        with_intent=_with_intent(args),
        model=args.model,
    )
    dest = Path(args.saida) if args.saida else repo / ".lateral" / "last"
    write_report({"repo": str(repo), "pares": [pair], "markdown": pair["markdown"]}, dest)
    print(pair["markdown"])
    print(f"JSON: {dest / 'lateral.json'}")
    return 0 if pair["status"] == "limpo" else 2


def _fetch_heads(clone: Path, pulls) -> list[dict]:
    heads = []
    for pull in pulls:
        subprocess.run(["git", "fetch", "-q", "origin", pull.ref], cwd=clone, check=True)
        heads.append({
            "ref": pull.ref,
            "sha": pull.sha,
            "title": pull.title,
            "body": pull.body,
            "number": pull.number,
            "user": pull.user,
        })
    return heads


def cmd_gitea(args: argparse.Namespace) -> int:
    token = args.token or os.environ.get("GITEA_TOKEN")
    if not token:
        raise SystemExit("GITEA_TOKEN ausente")
    owner, repo = args.repository.split("/", 1)
    client = Gitea(args.url, token)
    pulls = client.open_pulls(owner, repo)
    if len(pulls) < 2:
        print(f"{len(pulls)} PR(s) aberto(s); precisa de pelo menos 2.")
        return 0

    with tempfile.TemporaryDirectory() as tmp:
        clone = Path(tmp) / "repo"
        host = args.url.removeprefix("http://").removeprefix("https://")
        scheme = "https" if args.url.startswith("https") else "http"
        url = f"{scheme}://x-token:{token}@{host}/{owner}/{repo}.git"
        subprocess.run(["git", "clone", "-q", url, str(clone)], check=True)
        heads = _fetch_heads(clone, pulls)
        report = scan_heads(
            clone,
            heads,
            n_exec=args.execucoes,
            with_intent=_with_intent(args),
            model=args.model,
        )
        dest = Path(args.saida) if args.saida else Path(".lateral") / "last"
        write_report(report, dest)
        print(report["markdown"])
        if args.comment:
            for pair in report["pares"]:
                for side in (pair["left"], pair["right"]):
                    if "number" in side:
                        client.comment(owner, repo, side["number"], pair["markdown"])
        print(f"JSON: {dest / 'lateral.json'}")
        dirty = [p for p in report["pares"] if p["status"] != "limpo"]
        return 2 if dirty else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lateral",
        description="Lateral — instala no repo e verifica pares de branches",
    )
    parser.add_argument("--execucoes", type=int, default=1)
    intent_flags = parser.add_mutually_exclusive_group()
    intent_flags.add_argument("--intent", action="store_true", help="liga Haiku (intenção e geração)")
    intent_flags.add_argument("--no-intent", action="store_true", help="pula Haiku")
    parser.add_argument("--model", default=os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5"))
    parser.add_argument("--saida", default="")
    sub = parser.add_subparsers(dest="cmd", required=True)

    init = sub.add_parser("init", help="instala skills e commands do harness neste repositório")
    init.add_argument("--repo", default=".")
    init.add_argument(
        "--harness",
        default="",
        help="cursor,claude,kiro,codex,agy ou all. Vazio = detecta o que já existe",
    )
    init.add_argument("--base", default="main")
    init.add_argument("--sem-intent", action="store_true", help="grava intent = false no config")
    init.add_argument("--keep", action="store_true", help="não sobrescrever arquivos existentes")
    init.set_defaults(func=cmd_init)

    check = sub.add_parser("check", help="cruza as feature branches deste repositório")
    check.add_argument("--repo", default=".")
    check.add_argument("--base", default="")
    check.add_argument("--local", action="store_true", help="só branches locais")
    check.set_defaults(func=cmd_check)

    scan = sub.add_parser("scan", help="varre um par de refs")
    scan.add_argument("--repo", default=".")
    scan.add_argument("--left", required=True)
    scan.add_argument("--right", required=True)
    scan.add_argument("--left-intent", default="")
    scan.add_argument("--right-intent", default="")
    scan.set_defaults(func=cmd_scan)

    gitea = sub.add_parser("gitea", help="(lab) varre PRs abertos num Gitea")
    gitea.add_argument("--url", default=os.environ.get("GITEA_URL", "http://localhost:3310"))
    gitea.add_argument("--repository", default="lab/loja")
    gitea.add_argument("--token", default="")
    gitea.add_argument("--comment", action="store_true")
    gitea.set_defaults(func=cmd_gitea)

    axi = sub.add_parser("axi", help="superfície máquina (JSON) para o harness")
    axi_sub = axi.add_subparsers(dest="axi_cmd", required=True)

    axi_status = axi_sub.add_parser("status", help="último relatório, sem rodar de novo")
    axi_status.add_argument("--repo", default=".")
    axi_status.set_defaults(func=cmd_axi_status)

    axi_check = axi_sub.add_parser("check", help="cruza branches e imprime o envelope AXI")
    axi_check.add_argument("--repo", default=".")
    axi_check.add_argument("--base", default="")
    axi_check.add_argument("--local", action="store_true")
    axi_check.set_defaults(func=cmd_axi_check)

    axi_intent = axi_sub.add_parser("intent", help="grava a intenção explícita de uma branch")
    axi_intent.add_argument("--repo", default=".")
    axi_intent.add_argument("--branch", default="", help="vazio = branch atual")
    axi_intent.add_argument("--text", default="")
    axi_intent.add_argument("--file", default="", help="arquivo, ou - para stdin")
    axi_intent.set_defaults(func=cmd_axi_intent)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
