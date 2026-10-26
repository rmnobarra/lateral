Grave a intenção explícita de uma feature branch.

Peça a branch e o texto da tarefa se o usuário não passou. A intenção é o objetivo do autor, não a descrição do diff.

```bash
python -m lateral axi intent --branch $BRANCH --text "a tarefa, inalterada"
```

Não rode o check a menos que o usuário peça. Transcript não substitui este texto.
