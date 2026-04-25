import tempfile
import yaml
from pathlib import Path


def test_site_neutral_url_shorthand(project_env, run_puppy):
    """{{ projects.other.url }} resolves to the current site's URL."""
    other_proj = project_env['home'] / 'OtherMod'
    other_proj.mkdir()
    (other_proj / 'puppy.yaml').write_text(
        yaml.dump({
            'pack': 'other',
            'modrinth': {'id': 'abc'},
            'curseforge': {'slug': 'other-cf'},
        })
    )

    (project_env['project'] / 'description.md').write_text(
        'Link: {{ projects.other.url }}'
    )
    (project_env['project'] / 'puppy.yaml').write_text(
        yaml.dump({'name': 'NeonGlow', 'pack': 'neonglow'})
    )

    run_puppy('push', '-n', '-s', 'modrinth')
    mr_out = (
        Path(tempfile.gettempdir()) / 'puppy' / 'neonglow' / 'modrinth' / 'description.md'
    )
    assert 'https://modrinth.com/mod/abc' in mr_out.read_text()

    run_puppy('push', '-n', '-s', 'curseforge')
    cf_out = (
        Path(tempfile.gettempdir()) / 'puppy' / 'neonglow' / 'curseforge' / 'description.html'
    )
    assert 'other-cf' in cf_out.read_text()


def test_site_neutral_missing_returns_empty(project_env, run_puppy):
    """{{ projects.other.url }} is empty string when the site has no entry."""
    other_proj = project_env['home'] / 'OtherMod'
    other_proj.mkdir()
    (other_proj / 'puppy.yaml').write_text(
        yaml.dump({'pack': 'other', 'modrinth': {'id': 'abc'}})
    )

    (project_env['project'] / 'description.md').write_text(
        '[{{ projects.other.url }}]'
    )
    (project_env['project'] / 'puppy.yaml').write_text(
        yaml.dump({'name': 'NeonGlow', 'pack': 'neonglow'})
    )

    run_puppy('push', '-n', '-s', 'planetminecraft')
    pmc_out = (
        Path(tempfile.gettempdir()) / 'puppy' / 'neonglow' / 'planetminecraft' / 'description.bbcode'
    )
    assert '[]' in pmc_out.read_text()


def test_cross_project_url_resolution(project_env, run_puppy):
    """Test {{ projects.[other].url }} resolution."""
    other_proj = project_env['home'] / 'OtherMod'
    other_proj.mkdir()
    (other_proj / 'puppy.yaml').write_text(
        yaml.dump({'pack': 'other', 'modrinth': {'id': 'abc'}})
    )

    (project_env['project'] / 'description.md').write_text(
        'Link: {{ projects.other.modrinth.url }}'
    )

    run_puppy('push', '-n', '-s', 'modrinth')

    debug_file = (
        Path(tempfile.gettempdir()) / 'puppy' / 'neonglow' / 'modrinth' / 'description.md'
    )
    assert 'https://modrinth.com/mod/abc' in debug_file.read_text()


def test_linked_projects_top_level_slug(project_env, run_puppy):
    """linked_projects with a top-level slug generates URLs for all sites."""
    (project_env['home'] / 'puppy.yaml').write_text(
        yaml.dump({
            'linked_projects': {
                'external': {'slug': 'my-pack'},
            }
        })
    )
    (project_env['project'] / 'description.md').write_text(
        'MR: {{ projects.external.modrinth.url }} CF: {{ projects.external.curseforge.url }}'
    )

    run_puppy('push', '-n', '-s', 'modrinth')
    mr_out = Path(tempfile.gettempdir()) / 'puppy' / 'neonglow' / 'modrinth' / 'description.md'
    assert 'https://modrinth.com/mod/my-pack' in mr_out.read_text()
    assert 'https://www.curseforge.com/minecraft/texture-packs/my-pack' in mr_out.read_text()


def test_linked_projects_site_slug_overrides_default(project_env, run_puppy):
    """A per-site slug in linked_projects overrides the top-level default."""
    (project_env['home'] / 'puppy.yaml').write_text(
        yaml.dump({
            'linked_projects': {
                'external': {
                    'slug': 'default-slug',
                    'modrinth': {'slug': 'modrinth-specific'},
                },
            }
        })
    )
    (project_env['project'] / 'description.md').write_text(
        'MR: {{ projects.external.modrinth.url }} CF: {{ projects.external.curseforge.url }}'
    )

    run_puppy('push', '-n', '-s', 'modrinth')
    mr_out = Path(tempfile.gettempdir()) / 'puppy' / 'neonglow' / 'modrinth' / 'description.md'
    assert 'https://modrinth.com/mod/modrinth-specific' in mr_out.read_text()
    assert 'https://www.curseforge.com/minecraft/texture-packs/default-slug' in mr_out.read_text()
