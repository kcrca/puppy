import yaml
import tempfile
from pathlib import Path

def test_additive_dict_merge(project_env, run_puppy):
    """Dicts in puppy.yaml should merge additively across layers."""
    # Global Site Override
    mr_global_dir = project_env["home"] / "modrinth"
    mr_global_dir.mkdir()
    (mr_global_dir / "puppy.yaml").write_text("modrinth:\n  tags:\n    tag1: true")
    
    # Project Site Override
    mr_proj_dir = project_env["source"] / "modrinth"
    mr_proj_dir.mkdir()
    (mr_proj_dir / "puppy.yaml").write_text("modrinth:\n  tags:\n    tag2: true")
    
    run_puppy("push", "-n", "-s", "modrinth")
    
    debug_meta = Path(tempfile.gettempdir()) / "puppy" / "neonglow" / "modrinth" / "metadata.yaml"
    meta = yaml.safe_load(debug_meta.read_text())
    
    assert meta['tags']['tag1'] is True
    assert meta['tags']['tag2'] is True
