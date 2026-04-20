from pathlib import Path
from typing import Any

import yaml


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


class ConfigSynthesizer:
    def __init__(self, puppy_home: Path, project_root: Path, site: str | None = None):
        self.puppy_home = Path(puppy_home)
        self.project_root = Path(project_root)
        self.site = site

    def get_running_config(self) -> dict[str, Any]:
        project_puppy = self.project_root / "puppy"

        layers: list[Path] = [
            self.puppy_home / "puppy.yaml",
        ]
        if self.site:
            layers.append(self.puppy_home / self.site / "puppy.yaml")
        layers.append(project_puppy / "puppy.yaml")
        if self.site:
            layers.append(project_puppy / self.site / "puppy.yaml")

        config: dict = {}
        for layer in layers:
            config = _deep_merge(config, _load_yaml(layer))

        images_path = project_puppy / "images"
        if images_path.exists() and not images_path.is_dir():
            raise SystemExit(f"{images_path} exists but is not a directory")
        top_level = project_puppy / "images.yaml"
        in_dir = images_path / "images.yaml"
        if top_level.exists() and in_dir.exists():
            raise SystemExit(f"Ambiguous images config: both {top_level} and {in_dir} exist")
        images_yaml = top_level if top_level.exists() else in_dir if in_dir.exists() else None
        if images_yaml:
            raw = yaml.safe_load(images_yaml.read_text()) or []
            if isinstance(raw, list):
                images, images_source = raw, None
            else:
                images = raw.get("images", [])
                images_source = raw.get("source")
            if images:
                config["images"] = images
            if images_source:
                config["images_source"] = str((project_puppy / images_source).resolve())

        return config


_SITE_URL = {
    "modrinth": "https://modrinth.com/mod/{ref}",
    "curseforge": "https://www.curseforge.com/minecraft/texture-packs/{ref}",
    "planetminecraft": "https://www.planetminecraft.com/texture-pack/{ref}/",
}


def build_projects_context(puppy_home: Path) -> dict:
    """Scan sibling projects and return a {pack: {site: {url: ...}}} dict."""
    projects: dict = {}
    for candidate in puppy_home.iterdir():
        if not candidate.is_dir():
            continue
        yaml_path = candidate / "puppy" / "puppy.yaml"
        if not yaml_path.exists():
            continue
        cfg = _load_yaml(yaml_path)
        pack = cfg.get("pack") or candidate.name.lower()
        site_urls: dict = {}
        for site, template in _SITE_URL.items():
            sc = cfg.get(site, {})
            ref = sc.get("slug") or sc.get("id")
            if ref:
                site_urls[site] = {"url": template.format(ref=ref)}
        if site_urls:
            projects[pack] = site_urls
    return projects
