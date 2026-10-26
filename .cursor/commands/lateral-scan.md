Compare duas refs com o Lateral.

Peça left e right se o usuário não passou. Se ele descreveu as tarefas, grave:

```bash
python -m lateral axi intent --branch $LEFT --text "…"
python -m lateral axi intent --branch $RIGHT --text "…"
```

Depois:

```bash
python -m lateral scan --repo . --left $LEFT --right $RIGHT
```

Leia a saída e `.lateral/last/lateral.md`. Não mescle.
