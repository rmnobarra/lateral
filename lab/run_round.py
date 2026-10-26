"""Uma rodada do laboratório: dois desenvolvedores + Lateral."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from lab.bootstrap import TOKEN_FILE, clone_for_agent, porta, publish_seed, subir

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
PYTHON = PROJECT / ".venv" / "bin" / "python"
if not PYTHON.exists():
    PYTHON = Path(sys.executable)


def _run_side(side: str, args: argparse.Namespace, token: str, saida: Path) -> subprocess.CompletedProcess[str]:
    dest = saida / f"clone-{side}"
    remote = clone_for_agent(token, dest)
    cmd = [
        str(PYTHON), "-m", "lab.simulator",
        "--side", side,
        "--scenario", args.scenario,
        "--clone", str(dest),
        "--remote-url", remote,
        "--gitea", f"http://127.0.0.1:{porta()}",
        "--token", token,
        "--repo", "lab/loja",
        "--saida", str(saida),
        "--model", args.model,
    ]
    if args.fixture:
        cmd.append("--fixture")
    env = {**os.environ, "GITEA_TOKEN": token, "PYTHONPATH": str(PROJECT)}
    return subprocess.run(cmd, cwd=PROJECT, env=env)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario")
    parser.add_argument("--fixture", action="store_true")
    parser.add_argument("--intent", action="store_true")
    parser.add_argument("--model", default=os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5"))
    parser.add_argument("--subir", action="store_true", help="sobe o Gitea se ainda não estiver no ar")
    args = parser.parse_args()

    if args.subir or not TOKEN_FILE.exists():
        token = subir()
    else:
        token = TOKEN_FILE.read_text().strip()
        publish_seed(token)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    saida = ROOT / "runs" / args.scenario / stamp
    saida.mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "scenarios" / args.scenario / "esperado.txt", saida / "esperado.txt")

    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=2) as pool:
        fa = pool.submit(_run_side, "a", args, token, saida)
        fb = pool.submit(_run_side, "b", args, token, saida)
        ra, rb = fa.result(), fb.result()
    (saida / "log-a.txt").write_text((ra.stdout or "") + (ra.stderr or ""))
    (saida / "log-b.txt").write_text((rb.stdout or "") + (rb.stderr or ""))
    if ra.returncode != 0:
        print(f"agente A falhou ({ra.returncode})", file=sys.stderr)
    if rb.returncode != 0:
        print(f"agente B falhou ({rb.returncode})", file=sys.stderr)

    lateral = [
        str(PYTHON), "-m", "lateral",
        "--saida", str(saida),
        "--execucoes", "1",
        "--model", args.model,
    ]
    if args.intent:
        lateral.append("--intent")
    lateral += [
        "gitea",
        "--url", f"http://127.0.0.1:{porta()}",
        "--repository", "lab/loja",
        "--token", token,
        "--comment",
    ]
    env = {**os.environ, "GITEA_TOKEN": token, "PYTHONPATH": str(PROJECT)}
    scan = subprocess.run(lateral, cwd=PROJECT, env=env)
    print(f"saída em {saida}")
    return 0 if ra.returncode == 0 and rb.returncode == 0 and scan.returncode in {0, 2} else 1


if __name__ == "__main__":
    raise SystemExit(main())
