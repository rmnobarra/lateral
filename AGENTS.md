# AGENTS.md — Lateral

Solução agentica para achar conflito textual, de build, semântico e trabalho duplicado **entre feature branches ativas**, antes da integração.

Responda e escreva em **português (pt-BR)**.

## Mapa

| Caminho | O que é |
|---|---|
| `lateral/` | Motor (overlap, merge-tree, build, testes, intenção) |
| `lab/` | Gitea + seed `loja` + cenários + simulador Haiku |
| `tests/` | Testes do motor |
| `README.md` | Instalar, lab, o que o CLI faz |
| `.lateral/` | Config local (`config.toml`; `last/` e `intents.json` não versionar) |

## Agentes

| Agente | Use para |
|---|---|
| `pesquisador` | Web e `README.md`. Não edita `lateral/` nem o lab |
| `implementador` | Motor, lab, testes |
| `operador-lab` | Subir Gitea, rodar cenário, ler `lab/runs/` |
| `apresentador` | Demo do lab |

Definições em `.cursor/agents/`. Skills em `.cursor/skills/`.

## Regras

1. Não versione `.env` nem `.lab-token`.
2. O Lateral acusa; não mescla e não apaga teste vermelho.
3. Porta do Gitea deste projeto é **3310**.
4. Fixture primeiro (`./lab.sh demo`), Haiku depois (`./lab.sh rodar`).
5. O lab controlado mede o detector, não a frequência em campo.

## Comandos

```bash
python3 -m lateral init --harness cursor,claude,kiro,codex,agy
python3 -m lateral axi intent --branch NOME --text "a tarefa"
python3 -m lateral axi check
python3 -m lateral axi status
python3 -m lateral scan --repo . --left REF_A --right REF_B
python3 -m pytest -q
cd lab && ./lab.sh subir
cd lab && ./lab.sh demo c01-centavos-frete
cd lab && ./lab.sh rodar c01-centavos-frete
python3 -m lateral gitea --url http://localhost:3310 --repository lab/loja
```

<!-- BEGIN LATERAL -->
## Lateral

Este repositório tem Lateral instalado.

- Check (humano): `python -m lateral check`
- Check (harness): `python -m lateral axi check`
- Status: `python -m lateral axi status`
- Intenção: `python -m lateral axi intent --branch NOME --text "…"`
- Relatório: `.lateral/last/lateral.md` · envelope AXI no stdout

O Lateral acusa. Não mescla. Não apaga teste que falhou no Merge.
<!-- END LATERAL -->
