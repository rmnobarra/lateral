"""Sobe o usuário do Gitea, o token e publica o seed."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOKEN_FILE = ROOT / ".lab-token"
USUARIO = "lab"
SENHA = "lab-local-123"
EMAIL = "lab@lab.local"


def porta() -> int:
    return int(os.environ.get("LAB_PORTA", "3310"))


def api() -> str:
    return f"http://127.0.0.1:{porta()}/api/v1"


def wait_gitea(timeout: float = 90) -> None:
    deadline = time.time() + timeout
    url = f"http://127.0.0.1:{porta()}/api/healthz"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(1)
    raise RuntimeError(f"Gitea não respondeu em {url}")


def _compose(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "compose", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=check,
    )


def ensure_token() -> str:
    if TOKEN_FILE.exists() and TOKEN_FILE.read_text().strip():
        return TOKEN_FILE.read_text().strip()
    _compose(
        "exec", "-T", "-u", "git", "gitea",
        "gitea", "admin", "user", "create", "--admin",
        "--username", USUARIO, "--password", SENHA, "--email", EMAIL,
        "--must-change-password=false",
        check=False,
    )
    raw = _compose(
        "exec", "-T", "-u", "git", "gitea",
        "gitea", "admin", "user", "generate-access-token",
        "--username", USUARIO, "--token-name", "lateral", "--scopes", "all", "--raw",
    )
    token = raw.stdout.strip().splitlines()[-1]
    TOKEN_FILE.write_text(token + "\n")
    return token


def _git(tmp: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=tmp, check=True, capture_output=True)


def publish_seed(token: str, repo: str = "loja") -> None:
    import json

    def req(method: str, path: str, payload: dict | None = None) -> None:
        data = None if payload is None else json.dumps(payload).encode()
        request = urllib.request.Request(
            f"{api()}{path}",
            data=data,
            method=method,
            headers={"Authorization": f"token {token}", "Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(request)
        except urllib.error.HTTPError as exc:
            if exc.code not in {404, 409, 422}:
                raise

    req("DELETE", f"/repos/{USUARIO}/{repo}")
    time.sleep(0.4)
    req("POST", "/user/repos", {"name": repo, "default_branch": "main"})
    tmp = Path(f"/tmp/lateral-seed-{os.getpid()}")
    if tmp.exists():
        shutil.rmtree(tmp)
    shutil.copytree(ROOT / "seed", tmp, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    _git(tmp, "init", "-b", "main")
    _git(tmp, "add", "-A")
    _git(tmp, "-c", "user.name=lab", "-c", "user.email=lab@lab.local", "commit", "-m", "seed")
    remote = f"http://{USUARIO}:{token}@127.0.0.1:{porta()}/{USUARIO}/{repo}.git"
    _git(tmp, "remote", "add", "origin", remote)
    _git(tmp, "push", "-u", "origin", "main")
    shutil.rmtree(tmp)


def clone_for_agent(token: str, dest: Path, repo: str = "loja") -> str:
    if dest.exists():
        shutil.rmtree(dest)
    remote = f"http://{USUARIO}:{token}@127.0.0.1:{porta()}/{USUARIO}/{repo}.git"
    subprocess.run(["git", "clone", remote, str(dest)], check=True, capture_output=True)
    return remote


def subir() -> str:
    _compose("up", "-d", "--wait")
    wait_gitea()
    token = ensure_token()
    publish_seed(token)
    print(f"Gitea em http://localhost:{porta()} ({USUARIO} / {SENHA})")
    return token


def descer() -> None:
    subprocess.run(["docker", "compose", "down", "-v"], cwd=ROOT, check=False)
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
