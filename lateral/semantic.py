"""Camada semântica: build + testes nas quatro versões (Crystal / SAM).

Critério estrito (SAM): o teste existe em Base, Left, Right e Merge;
passa nas três primeiras e falha no Merge.

Critério estendido: o teste foi adicionado por um dos lados, passa onde
existe entre os pais e falha no Merge.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path

from lateral.gitops import Quad, add_worktree, remove_worktree, run


@dataclass
class SemanticResult:
    status: str
    build: dict
    candidatos_estritos: list[str]
    candidatos_estendidos: list[dict]
    instaveis: list[str]
    testes_segundos: float | None = None

    def as_dict(self) -> dict:
        return asdict(self)


def _build(worktree: Path) -> dict:
    packages = [p.name for p in worktree.iterdir() if (p / "__init__.py").exists()]
    if not packages:
        packages = ["."]
    compile_r = run("python3", "-m", "compileall", "-q", *packages, cwd=worktree, check=False)
    collect_r = run(
        "python3", "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider",
        cwd=worktree, check=False,
    )
    ok = compile_r.returncode == 0 and collect_r.returncode in (0, 5)
    erro = "" if ok else (compile_r.stdout + compile_r.stderr + collect_r.stdout)[-1500:]
    return {"ok": ok, "erro": erro}


def _testes(worktree: Path, xml: Path) -> dict[str, str]:
    run(
        "python3", "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={xml}",
        cwd=worktree, check=False,
    )
    if not xml.exists():
        return {}
    result: dict[str, str] = {}
    for tc in ET.parse(xml).iter("testcase"):
        name = f"{tc.get('classname')}::{tc.get('name')}"
        kids = {c.tag for c in tc}
        if "failure" in kids:
            result[name] = "fail"
        elif "error" in kids:
            result[name] = "error"
        elif "skipped" in kids:
            result[name] = "skip"
        else:
            result[name] = "pass"
    return result


def _estavel(execs: list[dict[str, str]], teste: str, status: str) -> bool:
    return all(e.get(teste) == status for e in execs)


def _candidatos(runs: dict[str, list[dict[str, str]]]) -> tuple[list[str], list[dict]]:
    presentes = {v: set().union(*map(set, execs)) if execs else set() for v, execs in runs.items()}
    estrito: list[str] = []
    estendido: list[dict] = []
    for teste in sorted(presentes.get("M", set())):
        if not _estavel(runs["M"], teste, "fail"):
            continue
        if all(teste in presentes[v] for v in "BLR"):
            if all(_estavel(runs[v], teste, "pass") for v in "BLR"):
                estrito.append(teste)
        elif teste not in presentes.get("B", set()):
            pais = [v for v in "LR" if teste in presentes[v]]
            if pais and all(_estavel(runs[v], teste, "pass") for v in pais):
                estendido.append({"teste": teste, "adicionado_por": pais})
    return estrito, estendido


def analyze(repo: Path, quad: Quad, tmp: Path, n_exec: int = 1) -> SemanticResult:
    if quad.textual_conflict or not quad.merge:
        return SemanticResult("conflito_textual", {}, [], [], [])

    shas = {"B": quad.base, "L": quad.left, "R": quad.right, "M": quad.merge}
    trees: dict[str, Path] = {}
    try:
        for key, sha in shas.items():
            trees[key] = add_worktree(repo, tmp / f"{key}-{sha[:8]}", sha)
        build = {key: _build(path) for key, path in trees.items()}
        if not (build["L"]["ok"] and build["R"]["ok"]):
            return SemanticResult("pais_nao_buildam", build, [], [], [])
        if not build["M"]["ok"]:
            return SemanticResult("conflito_build", build, [], [], [])
        if not build["B"]["ok"]:
            return SemanticResult("base_nao_builda", build, [], [], [])

        runs = {
            key: [_testes(path, path / f"lateral-{i}.xml") for i in range(n_exec)]
            for key, path in trees.items()
        }
        estrito, estendido = _candidatos(runs)
        instaveis = sorted({
            teste
            for execs in runs.values()
            for teste in set().union(*map(set, execs))
            if len({e.get(teste) for e in execs}) > 1
        })
        status = "candidato_semantico" if estrito or estendido else "limpo"
        return SemanticResult(status, build, estrito, estendido, instaveis)
    finally:
        for path in trees.values():
            remove_worktree(repo, path)
