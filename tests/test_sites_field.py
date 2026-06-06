"""Tests for the sites: field in puppy.yaml controlling default site selection."""
import tempfile
import yaml
from pathlib import Path


def test_sites_field_limits_push_dry_run(project_env, run_puppy):
    (project_env['home'] / 'puppy.yaml').write_text(
        yaml.dump({'projects': ['NeonGlow'], 'sites': ['modrinth']})
    )
    run_puppy('push', '-n', '-d', str(project_env['home']))

    temp_root = Path(tempfile.gettempdir()) / 'puppy' / 'neonglow'
    index = (temp_root / 'index.html').read_text()
    assert 'Modrinth' in index
    assert 'CurseForge' not in index
    assert 'Planet Minecraft' not in index


def test_sites_field_with_abbreviations(project_env, run_puppy):
    (project_env['home'] / 'puppy.yaml').write_text(
        yaml.dump({'projects': ['NeonGlow'], 'sites': ['cf']})
    )
    run_puppy('push', '-n', '-d', str(project_env['home']))

    temp_root = Path(tempfile.gettempdir()) / 'puppy' / 'neonglow'
    index = (temp_root / 'index.html').read_text()
    assert 'CurseForge' in index
    assert 'Modrinth' not in index


def test_explicit_site_arg_overrides_sites_field(project_env, run_puppy):
    (project_env['home'] / 'puppy.yaml').write_text(
        yaml.dump({'projects': ['NeonGlow'], 'sites': ['cf']})
    )
    run_puppy('push', '-n', '-s', 'modrinth', '-d', str(project_env['home']))

    temp_root = Path(tempfile.gettempdir()) / 'puppy' / 'neonglow'
    index = (temp_root / 'index.html').read_text()
    assert 'Modrinth' in index
    assert 'CurseForge' not in index


def test_absent_sites_field_uses_all_sites(project_env, run_puppy):
    run_puppy('push', '-n', '-d', str(project_env['home']))

    temp_root = Path(tempfile.gettempdir()) / 'puppy' / 'neonglow'
    index = (temp_root / 'index.html').read_text()
    assert 'Modrinth' in index
    assert 'CurseForge' in index
    assert 'planetminecraft' in index
