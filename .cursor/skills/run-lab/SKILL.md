---
name: run-lab
description: Sobe o Gitea do Lateral, publica o seed e roda um cenário (fixture ou Haiku). Use when the user asks to run the lab, demo a scenario, start Gitea, or simulate developers.
---

# Rodar o laboratório

1. Confirme `.env` na raiz (chave Anthropic só é obrigatória sem `--fixture`).
2. `cd lab && ./lab.sh subir`
3. Demonstração sem token: `./lab.sh demo c01-centavos-frete`
4. Agentes Haiku: `./lab.sh rodar c01-centavos-frete`
5. Leia `lab/runs/<cenario>/<timestamp>/lateral.json` e o `esperado.txt`.
6. Gitea em http://localhost:3310 (`lab` / `lab-local-123`).
7. Encerrar: `./lab.sh descer`

Cenários: `c01-centavos-frete`, `c02-inocuo-frete`, `c03-aliquota-frete`, `c04-duplicata-frete`.
