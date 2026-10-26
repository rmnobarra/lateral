from lateral.harness.common import SKILL_BODY


def files() -> dict[str, str]:
    return {
        ".agents/skills/lateral/SKILL.md": (
            "---\n"
            "name: lateral\n"
            "description: Roda o Lateral neste repositório. Use when the user says /lateral or asks about cross-branch semantic conflicts.\n"
            "---\n\n"
            + SKILL_BODY
        ),
        ".agents/rules/40-lateral.md": (
            "# Lateral\n\n"
            "Antes de integrar feature branches paralelas, rode `python -m lateral axi check` "
            "e leia `.lateral/last/lateral.md`. O Lateral acusa; não mescla.\n"
        ),
    }
