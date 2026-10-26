---
name: run-lateral
description: Executa o motor Lateral sobre um clone local ou sobre PRs abertos no Gitea. Use when scanning branches, checking PRs for semantic conflicts, or generating a lateral.json report.
---

# Rodar o motor

No próprio repositório (produto):

```bash
python3 -m lateral init --harness cursor   # uma vez
python3 -m lateral axi intent --branch NOME --text "a tarefa"
python3 -m lateral axi check               # JSON para o harness
python3 -m lateral axi status              # último relatório
```

Par local:

```bash
python3 -m lateral scan --repo PATH --left SHA_OU_REF --right SHA_OU_REF
```

PRs do Gitea (só o laboratório):

```bash
python3 -m lateral gitea --url http://localhost:3310 --repository lab/loja --token "$GITEA_TOKEN"
```

Haiku (intenção + teste gerado) liga por padrão. `--no-intent` pula. Sem `ANTHROPIC_API_KEY` a camada é pulada.

Interprete `status` com `docs/solucao.md`. Não mescle a correção sem humano.
