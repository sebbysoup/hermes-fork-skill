import importlib.util
from pathlib import Path


MODULE_PATH = Path("/home/main/hermes-fork-skill/skills/fork/scripts/generate_local_machine_guide.py")
spec = importlib.util.spec_from_file_location("generate_local_machine_guide", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_resolve_runtime_skill_dir_prefers_active_hermes_home_over_staged_prompt_source(tmp_path):
    hermes_home = tmp_path / "hermes-home"
    runtime_skill_dir = hermes_home / "skills" / "fork"
    runtime_skill_dir.mkdir(parents=True)
    staged_prompt_dir = tmp_path / "tmp-run" / ".agents" / "skills" / "fork"
    staged_prompt_dir.mkdir(parents=True)

    resolved = mod.resolve_runtime_skill_dir(staged_prompt_dir, hermes_home=hermes_home)

    assert resolved == runtime_skill_dir


def test_generate_local_machine_guide_writes_ready_file_into_runtime_skill_dir(tmp_path):
    hermes_home = tmp_path / "hermes-home"
    runtime_skill_dir = hermes_home / "skills" / "fork"
    templates_dir = runtime_skill_dir / "templates"
    scripts_dir = runtime_skill_dir / "scripts"
    templates_dir.mkdir(parents=True)
    scripts_dir.mkdir(parents=True)

    template_src = Path("/home/main/hermes-fork-skill/skills/fork/templates/local-machine-guide.template.md")
    (templates_dir / "local-machine-guide.template.md").write_text(template_src.read_text())
    (scripts_dir / "fork_session.py").write_text("#!/usr/bin/env python3\n")
    (scripts_dir / "collect_fork_facts.py").write_text("#!/usr/bin/env python3\n")

    result = mod.generate_local_machine_guide(
        runtime_skill_dir=runtime_skill_dir,
        hermes_home=hermes_home,
        facts={
            "generated_at": "2026-04-03T00:00:00+00:00",
            "skill_dir": str(runtime_skill_dir),
            "fork_helper": str(scripts_dir / "fork_session.py"),
            "fact_collector": str(scripts_dir / "collect_fork_facts.py"),
            "hermes_home": str(hermes_home),
            "state_db": str(hermes_home / "state.db"),
            "hermes_binary": "/usr/bin/hermes",
            "python3": "/usr/bin/python3",
            "available_now": ["print"],
            "conditional_methods": [],
            "recommended_method_now": "print",
            "env": {"DISPLAY": None, "WAYLAND_DISPLAY": None, "TMUX": None},
        },
    )

    guide_path = Path(result["guide_path"])
    content = guide_path.read_text()

    assert guide_path == runtime_skill_dir / "references" / "local-machine-guide.md"
    assert "SETUP_STATUS: ready" in content
    assert f"Skill dir: {runtime_skill_dir}" in content
    assert f"- HERMES_HOME default when unset: {hermes_home}" in content
    assert result["runtime_skill_dir"] == str(runtime_skill_dir)
