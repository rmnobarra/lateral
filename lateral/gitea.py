"""Cliente mínimo da API do Gitea."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass
class Pull:
    number: int
    title: str
    body: str
    ref: str
    sha: str
    user: str


class Gitea:
    def __init__(self, url: str, token: str) -> None:
        self.url = url.rstrip("/")
        self.token = token

    def _req(self, method: str, path: str, payload: dict | None = None) -> object:
        data = None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{self.url}{path}",
            data=data,
            method=method,
            headers={
                "Authorization": f"token {self.token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"{method} {path} -> {exc.code}: {body[:400]}") from exc

    def open_pulls(self, owner: str, repo: str) -> list[Pull]:
        items = self._req("GET", f"/api/v1/repos/{owner}/{repo}/pulls?state=open&limit=50")
        assert isinstance(items, list)
        return [
            Pull(
                number=p["number"],
                title=p.get("title") or "",
                body=p.get("body") or "",
                ref=p["head"]["ref"],
                sha=p["head"]["sha"],
                user=p.get("user", {}).get("login", ""),
            )
            for p in items
        ]

    def comment(self, owner: str, repo: str, number: int, body: str) -> None:
        self._req("POST", f"/api/v1/repos/{owner}/{repo}/issues/{number}/comments", {"body": body})

    def create_pull(self, owner: str, repo: str, title: str, head: str, base: str, body: str) -> dict:
        result = self._req(
            "POST",
            f"/api/v1/repos/{owner}/{repo}/pulls",
            {"title": title, "head": head, "base": base, "body": body},
        )
        assert isinstance(result, dict)
        return result
