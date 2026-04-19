import yaml
import tempfile
from pathlib import Path

def test_all_yaml_vars_available_to_jinja(project_env, run_puppy):
    config = {
        "minecraft": "1.20.1",
        "custom": {"val": "hello"}
    }
    (project_env["source"] / "puppy.yaml").write_text(yaml.dump(config))
    (project_env["source"] / "description.md").write_text("MC: {{ minecraft }}, Val: {{ custom.val }}")
    
    run_puppy("push", "-n")
    
    debug_file = Path(tempfile.gettempdir()) / "puppy" / "neonglow" / "modrinth" / "description.md"
    content = debug_file.read_text()
    
    assert "MC: 1.20.1" in content
    assert "Val: hello" in content
