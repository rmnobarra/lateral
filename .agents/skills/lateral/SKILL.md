---
name: lateral
description: Roda o Lateral neste repositório. Use when the user says /lateral or asks about cross-branch semantic conflicts.
---

# Lateral

O Lateral é o verificador de integração cruzada deste repositório. Não é um agent.
É um CLI que monta o merge especulativo entre feature branches ativas e acusa
conflito textual, de build, semântico (oráculo SAM), de intenção ou de teste
gerado (Haiku propõe; pytest nas quatro versões aceita ou descarta).

Gitea/GitHub/GitLab são só forjas. O Lateral atua **a partir deste repo**.

O harness fala com `lateral axi` (JSON no stdout). O humano lê `.lateral/last/lateral.md`.

## Quando usar

- Antes de abrir ou mergear um PR
- Quando outro desenvolvedor ou agent publicou uma feature branch
- Quando o usuário diz `/lateral`, `lateral check`, conflito cruzado, overlap, SAM

## O que fazer

1. Se o usuário declarou a tarefa de uma branch, grave a intenção **antes** do check:

```bash
python -m lateral axi intent --branch NOME --text "a tarefa, inalterada"
```

Intenção explícita é o critério de aceitação. Transcript local só entra se ninguém gravou texto, e vale como palpite (`confidence: low`).

2. Rode o envelope máquina, não improvise `git merge` no working tree:

```bash
python -m lateral axi check
```

3. Parseie o JSON. Campos que importam: `state`, `awaiting`, `pares[].status`, `pares[].action`, `pares[].findings`, `intents`.
4. Se `awaiting` for `human` ou `action` for `ask-user`, resuma os findings e **pare**. Não mescle. Não apague teste vermelho. Não invente prevalência.
5. `action: auto-fix` não existe. O Lateral acusa.

## Status sem rodar de novo

```bash
python -m lateral axi status
```

`state: empty` → peça `/lateral`. `state: dirty` → liste os pares. `state: ready` → todos `limpo`.

## Par específico

```bash
python -m lateral scan --repo . --left REF_A --right REF_B
```

## Status de um par

`conflito_textual` · `conflito_build` · `candidato_semantico` · `risco_intencao` · `limpo`

Candidato semântico (SAM): o teste passa nos pais e falha no Merge sintético.
