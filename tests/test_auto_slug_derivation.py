import yaml

from puppy.core import Project


def test_name_to_slug_derivation_and_writeback(tmp_path):
    """If only 'name' is provided, 'pack' is derived and written back on non-dry-run."""
    root = tmp_path / 'mypack'
    root.mkdir()
    yaml_path = root / 'puppy.yaml'
    yaml_path.write_text(yaml.dump({'name': 'Super Pack!'}))

    config = {'name': 'Super Pack!'}
    project = Project.from_config(root, config, dry_run=False)

    assert project.name == 'Super Pack!'
    assert project.pack == 'superpack'
    data = yaml.safe_load(yaml_path.read_text())
    assert data['name'] == 'Super Pack!'
    assert data['pack'] == 'superpack'


def test_slug_derivation_no_writeback_on_dry_run(tmp_path):
    """dry_run=True: pack derived in-memory but yaml not modified."""
    root = tmp_path / 'mypack'
    root.mkdir()
    yaml_path = root / 'puppy.yaml'
    yaml_path.write_text(yaml.dump({'name': 'Super Pack!'}))

    config = {'name': 'Super Pack!'}
    project = Project.from_config(root, config, dry_run=True)

    assert project.pack == 'superpack'
    assert config['pack'] == 'superpack'
    data = yaml.safe_load(yaml_path.read_text())
    assert 'pack' not in data
