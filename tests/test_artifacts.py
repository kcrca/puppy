import pytest

from puppy.artifacts import ArtifactFinder


def test_version_boundary_matching(tmp_path):
    """Checks that '1.2' does not match '1.2.4'."""

    pack_dir = tmp_path / 'packs'
    pack_dir.mkdir()

    # Target files
    (pack_dir / 'neon-1.2.zip').touch()
    (pack_dir / 'neon-1.2.4.zip').touch()

    finder = ArtifactFinder(pack_dir)

    # Correct match
    match = finder.find(project='neon', version='1.2')
    assert match.name == 'neon-1.2.zip'

    # Failure case for missing version
    with pytest.raises(FileNotFoundError):
        finder.find(project='neon', version='1.3')
