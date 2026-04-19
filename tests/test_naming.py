import yaml

def test_naming_derivation_logic(project_env, run_puppy):
    yaml_path = project_env["source"] / "puppy.yaml"
    yaml_path.write_text(yaml.dump({}))
    
    run_puppy("push", "-n")
    
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    
    assert data["pack"] == "neonglow"
    assert data["name"] == "NeonGlow"
