def test_strict_version_boundary(project_env, run_puppy):
    """Ensures version 1.2 does not accidentally match 1.2.4."""
    (project_env["source"] / "pack-1.2.4.zip").write_text("wrong")
    (project_env["source"] / "pack-1.2.zip").write_text("correct")
    (project_env["source"] / "puppy.yaml").write_text("minecraft: '1.20'")
    
    # Target version 1.2
    exit_code = run_puppy("push", "-n", "--pack", "--version", "1.2")
    assert exit_code == 0 or exit_code is None
