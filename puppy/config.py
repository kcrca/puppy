from pathlib import Path
from typing import Any

import yaml
from puppy.renderer import _resolve_config_strings

from puppy.core import project_source
from puppy.sites import SITES


def _deep_merge(base: dict, override: dict) -> dict:
    """Merge override into base: dicts merge additively, scalars overwrite."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open() as f:
        return yaml.safe_load(f) or {}


_PATH_KEYS = {'icon', 'zip'}


def _resolve_layer_paths(config: dict, base: Path) -> dict:
    """Resolve relative path values to absolute, anchored to the containing YAML file."""
    result = dict(config)
    for key in _PATH_KEYS:
        val = result.get(key)
        if val and isinstance(val, str) and '{{' not in val and not Path(val).is_absolute():
            result[key] = str((base / val).resolve())
    return result


class ConfigSynthesizer:
    def __init__(self, puppy_home: Path, project_root: Path, site=None):
        self.puppy_home = Path(puppy_home)
        self.project_root = Path(project_root)
        self.site = str(site) if site is not None else None

    def get_running_config(self) -> dict[str, Any]:
        project_puppy = project_source(self.project_root)

        layers: list[Path] = [self.puppy_home / 'puppy.yaml']
        if self.site:
            layers.append(self.puppy_home / self.site / 'puppy.yaml')
        layers.append(project_puppy / 'puppy.yaml')
        if self.site:
            layers.append(project_puppy / self.site / 'puppy.yaml')

        config: dict = {}
        for layer in layers:
            config = _deep_merge(config, _resolve_layer_paths(_load_yaml(layer), layer.parent))

        config['puppy'] = str(self.puppy_home)
        config['top'] = str(self.puppy_home.parent)
        config['project'] = str(project_puppy)

        images_path = project_puppy / 'images'
        if images_path.exists() and not images_path.is_dir():
            raise SystemExit(f'{images_path} exists but is not a directory')
        top_level = project_puppy / 'images.yaml'
        in_dir = images_path / 'images.yaml'
        if top_level.exists() and in_dir.exists():
            raise SystemExit(
                f'Ambiguous images config: both {top_level} and {in_dir} exist'
            )
        images_yaml = (
            top_level if top_level.exists() else in_dir if in_dir.exists() else None
        )
        if images_yaml is None and (self.puppy_home / 'images.yaml').exists():
            images_yaml = self.puppy_home / 'images.yaml'
        if images_yaml:
            images_base = images_yaml.parent
            raw = yaml.safe_load(images_yaml.read_text()) or []
            if isinstance(raw, list):
                images, images_source = raw, None
            else:
                images = raw.get('images', [])
                images_source = raw.get('source')
            if images:
                config['images'] = images
            if images_source:
                src = _resolve_config_strings({**config, '_s': images_source}, strict=False)['_s']
                p = Path(src) if Path(src).is_absolute() else (images_base / src).resolve()
                config['images_source'] = str(p)

        config = _resolve_config_strings(config, strict=False)
        return _apply_neutral_metadata(config)


def _apply_neutral_metadata(config: dict) -> dict:
    """Expand top-level neutral keys into per-site fields; per-site values win."""
    config = dict(config)
    links = config.get('links') or {}
    if isinstance(links, dict) and links.get('source'):
        config.setdefault('github', links['source'])
    for site in SITES:
        site.apply_neutral(config)
    return config


def _inject_urls(cfg: dict) -> dict:
    default_slug = cfg.get('slug')
    pack = cfg.get('pack')
    unconfigured = pack and not any(cfg.get(s.name) for s in SITES)
    top_type = cfg.get('type')
    for site in SITES:
        site_cfg = cfg.get(site.name, {})
        if default_slug and 'slug' not in site_cfg:
            site_cfg = dict(site_cfg, slug=default_slug)
        if top_type and 'type' not in site_cfg:
            site_cfg = dict(site_cfg, type=top_type)
        url = site.url_for(site_cfg)
        if not url and unconfigured:
            url = site.url_for({'slug': pack})
        if url:
            cfg.setdefault(site.name, {})['url'] = url
    return cfg


def build_projects_context(puppy_home: Path) -> dict:
    """Scan sibling projects and return a {pack: {site: {url: ...}}} dict."""
    global_cfg = _load_yaml(puppy_home / 'puppy.yaml')
    projects: dict = {}
    for candidate in puppy_home.iterdir():
        if not candidate.is_dir():
            continue
        yaml_path = project_source(candidate) / 'puppy.yaml'
        if not yaml_path.exists():
            continue
        cfg = _deep_merge(global_cfg, _load_yaml(yaml_path))
        pack = cfg.get('pack') or candidate.name.lower()
        projects[pack] = _inject_urls(cfg)
    for pack, cfg in global_cfg.get('linked_projects', {}).items():
        projects[pack] = _inject_urls(dict(cfg))
    return projects
