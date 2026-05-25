import yaml
from pathlib import Path

from puppy.core import Project


def test_naming_derivation_writes_yaml(tmp_path):
    root = tmp_path / 'NeonGlow'
    root.mkdir()
    yaml_path = root / 'puppy.yaml'
    yaml_path.write_text(yaml.dump({}))

    config = {}
    project = Project.from_config(root, config, dry_run=False)

    assert project.pack == 'neonglow'
    assert project.name == 'NeonGlow'
    data = yaml.safe_load(yaml_path.read_text())
    assert data['pack'] == 'neonglow'
    assert data['name'] == 'NeonGlow'


def test_naming_derivation_dry_run_no_yaml_write(tmp_path):
    root = tmp_path / 'NeonGlow'
    root.mkdir()
    yaml_path = root / 'puppy.yaml'
    yaml_path.write_text(yaml.dump({}))

    config = {}
    project = Project.from_config(root, config, dry_run=True)

    assert project.pack == 'neonglow'
    assert project.name == 'NeonGlow'
    assert config['name'] == 'NeonGlow'
    assert config['pack'] == 'neonglow'
    data = yaml.safe_load(yaml_path.read_text())
    assert 'pack' not in data
    assert 'name' not in data
