def test_security_block_missing_gitignore(project_env, run_puppy):
    (project_env["home"] / ".gitignore").unlink()
    assert run_puppy("push", "-n") != 0

def test_security_block_missing_auth(project_env, run_puppy):
    (project_env["home"] / "auth.yaml").unlink()
    assert run_puppy("push", "-n") != 0
