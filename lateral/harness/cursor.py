from lateral.harness.common import COMMAND_LATERAL, COMMAND_INTENT, COMMAND_SCAN, COMMAND_STATUS, SKILL_BODY


def files() -> dict[str, str]:
    return {
        ".cursor/skills/lateral/SKILL.md": (
            "---\n"
            "name: lateral\n"
            "description: Roda o Lateral neste repositório — verificação cruzada entre feature branches (textual, build, SAM, intenção). Use when the user mentions /lateral, cross integration, conflito semântico, overlap de branches, or before merging a PR while other feature branches are open.\n"
            "---\n\n"
            + SKILL_BODY
        ),
        ".cursor/commands/lateral.md": COMMAND_LATERAL,
        ".cursor/commands/lateral-scan.md": COMMAND_SCAN,
        ".cursor/commands/lateral-status.md": COMMAND_STATUS,
        ".cursor/commands/lateral-intent.md": COMMAND_INTENT,
        ".cursor/rules/lateral-repo.mdc": (
            "---\n"
            "description: Lateral instalado neste repositório\n"
            "alwaysApply: true\n"
            "---\n\n"
            "# Lateral\n\n"
            "- Antes de mergear com outras feature branches abertas, rode `python -m lateral axi check`.\n"
            "- Leia o JSON do AXI (ou `.lateral/last/lateral.md`). Não mescle e não apague teste vermelho.\n"
            "- Commands: `/lateral`, `/lateral-scan`, `/lateral-status`, `/lateral-intent`.\n"
        ),
    }
