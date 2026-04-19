#!/bin/zsh

# Create the tests directory
mkdir -p tests

# 1. Create conftest.py (The Environment Engine)
cat << 'EOF' > tests/conftest.py
import pytest
import os
import yaml
from pathlib import Path

@pytest.fixture
def project_env(tmp_path, monkeypatch):
    """Creates the 'Global > Home > Project' structure from the spec."""
    root = tmp_path / "neon"
    home = root / "puppy"
    project = home / "NeonGlow"
    source = project / "puppy"
    
    for d in [home, project, source]:
        d.mkdir(parents=True)
        
    # Security Requirement: auth.yaml must be gitignored
    (home / ".gitignore").write_text("auth.yaml")
    (home / "auth.yaml").write_text("modrinth: token123\ncurseforge: {token: cf456}")
    
    # Change CWD to the project root for execution
    monkeypatch.chdir(project)
    
    return {"root": root, "home": home, "project": project, "source": source}

@pytest.fixture
def run_puppy(monkeypatch):
    """Invokes the CLI directly via the entry point."""
    def _run(*args):
        import puppy.__main__
        monkeypatch.setattr("sys.argv", ["puppy"] + list(args))
        try:
            return puppy.__main__.main()
        except SystemExit as e:
            return e.code
    return _run
EOF

# 2. Create test_cascade.py (Deep Search Logic)
cat << 'EOF' > tests/test_cascade.py
import tempfile
from pathlib import Path

def test_content_discovery_cascade(project_env, run_puppy):
    """Tests the 5-layer cascade defined in section 5.2 of the spec."""
    # 1. Global General Fragment (Level 5)
    (project_env["home"] / "footer.md").write_text("Global Footer")
    
    # 2. Project General Fragment (Level 3)
    (project_env["source"] / "header.md").write_text("Project Header")
    
    # 3. Project Site Override (Level 2)
    mr_dir = project_env["source"] / "modrinth"
    mr_dir.mkdir()
    (mr_dir / "header.md").write_text("Modrinth-Only Header")
    
    (project_env["source"] / "description.md").write_text(
        "{{ snippet:header }}\nBody Content\n{{ snippet:footer }}"
    )
    
    run_puppy("push", "-n", "-s", "modrinth")
    
    debug_file = Path(tempfile.gettempdir()) / "puppy" / "neonglow" / "modrinth" / "description.md"
    content = debug_file.read_text()
    
    assert "Modrinth-Only Header" in content
    assert "Global Footer" in content
    assert "Project Header" not in content
EOF

# 3. Create test_security.py (Hard Blocks)
cat << 'EOF' > tests/test_security.py
def test_security_block_missing_gitignore(project_env, run_puppy):
    (project_env["home"] / ".gitignore").unlink()
    assert run_puppy("push", "-n") != 0

def test_security_block_missing_auth(project_env, run_puppy):
    (project_env["home"] / "auth.yaml").unlink()
    assert run_puppy("push", "-n") != 0
EOF

# 4. Create test_naming.py (Auto-derivation)
cat << 'EOF' > tests/test_naming.py
import yaml

def test_naming_derivation_logic(project_env, run_puppy):
    yaml_path = project_env["source"] / "puppy.yaml"
    yaml_path.write_text("{}")
    
    run_puppy("push", "-n")
    
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    
    assert data["pack"] == "neonglow"
    assert data["name"] == "NeonGlow"
EOF

# 5. Create test_jinja.py (Variable injection)
cat << 'EOF' > tests/test_jinja.py
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
EOF

echo "✅ Tests generated in ./tests/"
echo "👉 Run them with: pytest"