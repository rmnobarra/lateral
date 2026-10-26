from lateral.harness.common import COMMAND_LATERAL, COMMAND_INTENT, SKILL_BODY


def files() -> dict[str, str]:
    return {
        ".codex/skills/lateral/SKILL.md": (
            "---\n"
            "name: lateral\n"
            "description: Roda o Lateral neste repositório. Use when the user says /lateral or asks to check sibling feature branches.\n"
            "---\n\n"
            + SKILL_BODY
        ),
        ".codex/commands/lateral.md": COMMAND_LATERAL,
        ".codex/commands/lateral-intent.md": COMMAND_INTENT,
    }
