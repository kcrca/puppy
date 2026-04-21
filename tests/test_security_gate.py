import pytest

def test_auth_not_in_gitignore_fails(project_env, run_puppy):
    """
    Spec 6.1: Puppy must exit immediately if auth.yaml exists 
    but is NOT listed in the puppy/.gitignore file.
    """
    # Setup: Create auth.yaml
    (project_env["home"] / "auth.yaml").write_text("modrinth: token123")
    
    # Create a gitignore that is missing auth.yaml
    (project_env["home"] / ".gitignore").write_text("*.log\nnode_modules/")
    
    # Execution: Run any command
    exit_code = run_puppy("push", "-n")
    
    # Validation: Must fail (non-zero exit code)
    assert exit_code != 0
