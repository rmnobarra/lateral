from lateral.harness.common import COMMAND_LATERAL, COMMAND_INTENT, COMMAND_SCAN, COMMAND_STATUS, SKILL_BODY


def files() -> dict[str, str]:
    return {
        ".claude/skills/lateral/SKILL.md": (
            "---\n"
            "name: lateral\n"
            "description: Roda o Lateral neste repositório — verificação cruzada entre feature branches. Use when the user says /lateral or asks about semantic/cross-branch conflicts.\n"
            "---\n\n"
            + SKILL_BODY
        ),
        ".claude/commands/lateral.md": COMMAND_LATERAL,
        ".claude/commands/lateral-scan.md": COMMAND_SCAN,
        ".claude/commands/lateral-status.md": COMMAND_STATUS,
        ".claude/commands/lateral-intent.md": COMMAND_INTENT,
    }
