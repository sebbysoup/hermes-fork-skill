from pathlib import Path


def test_fork_skill_contains_control_marker_and_bootstrap_helper_reference():
    skill_md = Path("/home/main/hermes-fork-skill/skills/fork/SKILL.md").read_text()

    assert "__HERMES_FORK_CONTROL_MESSAGE_DO_NOT_CLONE__" in skill_md
    assert "generate_local_machine_guide.py" in skill_md
    assert "local-machine-guide.md" in skill_md
