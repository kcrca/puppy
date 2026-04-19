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

        images_yaml = project_puppy / "images" / "images.yaml"
        if images_yaml.exists():
            images = yaml.safe_load(images_yaml.read_text()) or []
            if images:
                config["images"] = images

        return config
