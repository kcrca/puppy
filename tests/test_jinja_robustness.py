import tempfile
from pathlib import Path

def test_unrecognized_variables_render_raw(project_env, run_puppy):
    """
    Spec 5.4: Unrecognized variables produce a warning 
    and are left as-is in the final output.
    """
    # Setup: Use a typo in the variable name
    (project_env["source"] / "description.md").write_text("Hello {{ typo_var }}")
    
    # Execution
    run_puppy("push", "-n", "-s", "modrinth")
    
    # Validation: The string should remain in the staged output
    debug_file = Path(tempfile.gettempdir()) / "puppy" / "neonglow" / "modrinth" / "description.md"
    content = debug_file.read_text()
    
    assert "{{ typo_var }}" in content
