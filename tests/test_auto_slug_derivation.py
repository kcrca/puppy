import yaml

from puppy.core import Project


def test_name_to_slug_derivation_and_writeback(tmp_path):
    """If only 'name' is provided, 'handle' is derived and written back on non-dry-run."""
    root = tmp_path / 'mypack'
    root.mkdir()
    yaml_path = root / 'puppy.yaml'
    yaml_path.write_text(yaml.dump({'name': 'Super Pack!'}))

    config = {'name': 'Super Pack!'}
    project = Project.from_config(root, config, dry_run=False)

    assert project.name == 'Super Pack!'
    assert project.handle == 'superpack'
    data = yaml.safe_load(yaml_path.read_text())
    assert data['name'] == 'Super Pack!'
    assert data['handle'] == 'superpack'


def test_slug_derivation_no_writeback_on_dry_run(tmp_path):
    """dry_run=True: handle derived in-memory but yaml not modified."""
    root = tmp_path / 'mypack'
    root.mkdir()
    yaml_path = root / 'puppy.yaml'
    yaml_path.write_text(yaml.dump({'name': 'Super Pack!'}))

    config = {'name': 'Super Pack!'}
    project = Project.from_config(root, config, dry_run=True)

    assert project.handle == 'superpack'
    assert config['handle'] == 'superpack'
    data = yaml.safe_load(yaml_path.read_text())
    assert 'handle' not in data
