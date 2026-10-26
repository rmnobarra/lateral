from lateral.harness.common import SKILL_BODY


def files() -> dict[str, str]:
    return {
        ".kiro/skills/lateral/SKILL.md": (
            "---\n"
            "name: lateral\n"
            "description: Roda o Lateral neste repositório. Use quando o usuário pedir /lateral, check cruzado ou conflito semântico entre branches.\n"
            "---\n\n"
            + SKILL_BODY
        ),
        ".kiro/steering/40-lateral.md": (
            "# Lateral\n\n"
            "Este repositório tem Lateral instalado. Antes de integrar feature branches "
            "paralelas, rode `python -m lateral axi check` e respeite `awaiting: human`. "
            "O Lateral acusa; não mescla.\n"
        ),
        ".kiro/agents/lateral.json": (
            "{\n"
            '  "name": "lateral",\n'
            '  "description": "Roda o verificador cruzado Lateral e resume o relatório. Não mescla.",\n'
            '  "prompt": "Você opera o Lateral neste repositório. Rode `python -m lateral axi check`, parseie o JSON e resuma os pares. Se awaiting for human, pare. Não mescle, não apague teste vermelho, não invente prevalência.",\n'
            '  "tools": ["read", "shell"],\n'
            '  "welcomeMessage": "Lateral pronto. Qual par ou check completo?"\n'
            "}\n"
        ),
    }
