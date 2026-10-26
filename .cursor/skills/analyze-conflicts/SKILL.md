---
name: analyze-conflicts
description: Classifica um par de branches Lateral (textual, build, semântico, intenção) e separa defeito de produto de quebra de teste. Use when reading lateral.json, diffs, or lab runs.
---

# Analisar um par

1. Abra `lateral.json` e o `esperado.txt` da rodada.
2. Se `conflito_textual`, pare — as outras camadas não rodaram no Merge.
3. Se `candidato_semantico`, leia o teste. Pergunte: o Merge viola um requisito de alguma tarefa (**defeito de produto**) ou só uma asserção rígida (**quebra de teste**)?
4. Overlap amarelo sem falha de teste não é conflito; é risco.
5. Intenção `red` com testes verdes é o caso que a suíte não cobre — proponha, não afirme prevalência.
6. Se mudar o que sabemos, diga no chat. Não invente pasta de handoff.
