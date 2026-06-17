from __future__ import annotations

from pathlib import Path


class Site:
    name: str
    aliases: list[str]
    label: str
    template_ext: str
    desc_exts: list[str]

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f'Site({self.name!r})'

    def convert_md(self, text: str) -> str:
        return text

    def shield_tags(self, tags: list[str]) -> tuple[dict, dict]:
        return {}, {}

    def apply_neutral(self, config: dict) -> None:
        pass

    def preview_rows(self, sc: dict) -> list[tuple[str, str]]:
        return []

    def resolve_id(self, config: dict, auth: dict, verbosity: int) -> dict:
        return config

    def post_upload(self, puppy_dir: Path, version: str) -> None:
        pass

    def apply_settings(self, settings: dict, sc: dict) -> None:
        pass

    def spdx_license(self, value: str) -> str | None:
        return value

    def auth_yaml_entry(self) -> str:
        return ''

    def puppy_yaml_entry(self, pack: str) -> str:
        return f'{self.name}:\n  id: null\n  slug: {pack}\n'

    def init_template(self) -> tuple[str, str]:
        raise NotImplementedError

    def img_tag(self, url: str, name: str) -> str:
        return f'<img src="{url}" alt="{name}">'

    def img_tag_md(self, url: str, name: str) -> str:
        return self.img_tag(url, name)

    def upload_images(
        self,
        project_id,
        auth: dict,
        image_list: list,
        images_dir: Path,
        verbosity: int,
        project_type: str = 'pack',
    ) -> dict[str, str]:
        return {}

    def url_for(self, site_config: dict) -> str | None:
        raise NotImplementedError
