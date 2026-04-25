import tempfile
import yaml
from pathlib import Path


def test_cf_description_is_html(project_env, run_puppy):
    (project_env['project'] / 'puppy.yaml').write_text(yaml.dump({'version': '1.0'}))
    (project_env['project'] / 'description.md').write_text(
        '# Hello\n\nA **bold** word.\n'
    )
    run_puppy('push', '-n')

    content = (
        Path(tempfile.gettempdir())
        / 'puppy'
        / 'neonglow'
        / 'curseforge'
        / 'description.html'
    ).read_text()
    assert '<h1>' in content
    assert '<strong>' in content
    assert '**' not in content


def test_pmc_description_is_bbcode(project_env, run_puppy):
    (project_env['project'] / 'puppy.yaml').write_text(yaml.dump({'version': '1.0'}))
    (project_env['project'] / 'description.md').write_text(
        '# Hello\n\nA **bold** word.\n'
    )
    run_puppy('push', '-n')

    content = (
        Path(tempfile.gettempdir())
        / 'puppy'
        / 'neonglow'
        / 'planetminecraft'
        / 'description.bbcode'
    ).read_text()
    assert '[h1]' in content
    assert '[b]' in content
    assert '**' not in content


def test_modrinth_description_stays_md(project_env, run_puppy):
    (project_env['project'] / 'puppy.yaml').write_text(yaml.dump({'version': '1.0'}))
    (project_env['project'] / 'description.md').write_text(
        '# Hello\n\nA **bold** word.\n'
    )
    run_puppy('push', '-n')

    content = (
        Path(tempfile.gettempdir())
        / 'puppy'
        / 'neonglow'
        / 'modrinth'
        / 'description.md'
    ).read_text()
    assert '# Hello' in content
    assert '**bold**' in content


def test_pmc_soft_wraps_preserved(project_env, run_puppy):
    (project_env['project'] / 'puppy.yaml').write_text(yaml.dump({'version': '1.0'}))
    (project_env['project'] / 'description.md').write_text(
        'Word one\nword two on next line.\n'
    )
    run_puppy('push', '-n')

    content = (
        Path(tempfile.gettempdir())
        / 'puppy'
        / 'neonglow'
        / 'planetminecraft'
        / 'description.bbcode'
    ).read_text()
    assert 'one word' in content or 'one\nword' not in content
    assert 'oneword' not in content


def test_pmc_bbcode_renders_in_preview(project_env, run_puppy):
    (project_env['project'] / 'puppy.yaml').write_text(yaml.dump({'version': '1.0'}))
    (project_env['project'] / 'description.md').write_text(
        '# Big Heading\n\nSome text.\n'
    )
    run_puppy('push', '-n')

    index = (
        Path(tempfile.gettempdir()) / 'puppy' / 'neonglow' / 'index.html'
    ).read_text()
    assert '<h1>' in index
    assert '[h1]' not in index


def test_site_specific_yaml_var_in_rendering(project_env, run_puppy):
    (project_env['project'] / 'puppy.yaml').write_text(yaml.dump({'version': '1.0'}))
    pmc_dir = project_env['project'] / 'planetminecraft'
    pmc_dir.mkdir()
    (pmc_dir / 'puppy.yaml').write_text(yaml.dump({'pmc_extra': 'pmc-only-value'}))
    (project_env['project'] / 'description.md').write_text('Value: {{ pmc_extra }}\n')
    run_puppy('push', '-n', '-s', 'planetminecraft')

    content = (
        Path(tempfile.gettempdir())
        / 'puppy'
        / 'neonglow'
        / 'planetminecraft'
        / 'description.bbcode'
    ).read_text()
    assert 'pmc-only-value' in content


def test_site_alias_loads_correct_yaml(project_env, run_puppy):
    (project_env['project'] / 'puppy.yaml').write_text(yaml.dump({'version': '1.0'}))
    pmc_dir = project_env['project'] / 'planetminecraft'
    pmc_dir.mkdir()
    (pmc_dir / 'puppy.yaml').write_text(yaml.dump({'pmc_extra': 'alias-test-value'}))
    (project_env['project'] / 'description.md').write_text('Value: {{ pmc_extra }}\n')
    run_puppy('push', '-n', '-s', 'pmc')

    content = (
        Path(tempfile.gettempdir())
        / 'puppy'
        / 'neonglow'
        / 'planetminecraft'
        / 'description.bbcode'
    ).read_text()
    assert 'alias-test-value' in content
