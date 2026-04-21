import html as _html
import re
import shutil
from pathlib import Path

import markdown
import yaml

from puppy.transformers import PMCTransformer

_pmc = PMCTransformer()

from puppy.core import Project
from puppy.creator import _expand_versions, _find_icon, _resolve_asset
from puppy.images import find_image, stage_image
from puppy.renderer import DEFAULT_SHIELD_TAGS
from puppy.sites import Site


def generate(
    project: Project,
    config: dict,
    debug_dir: Path,
    sites: list[str],
    source_exts: dict[str, str],
    zip_name: str = None,
) -> None:
    puppy_dir = project.root / 'puppy'

    icon_rel = None
    try:
        icon_src = _resolve_asset(config.get('icon'), puppy_dir, _find_icon)
        stage_image(icon_src, debug_dir / 'icon.png')
        icon_rel = 'icon.png'
    except SystemExit:
        pass

    image_entries: list[tuple[str, str, str]] = []
    images_src = (
        Path(config['images_source'])
        if config.get('images_source')
        else puppy_dir / 'images'
    )
    images_dest = debug_dir / 'images'
    for img in config.get('images', []):
        stem = Path(img['file']).stem
        fname = stem + '.png'
        try:
            src = find_image(img['file'], images_src)
            stage_image(src, images_dest / fname)
            image_entries.append(
                (fname, img.get('name', ''), img.get('description', ''))
            )
        except SystemExit as e:
            print(f'WARNING: {e}')

    shield_tags = config.get('md_html_tags', DEFAULT_SHIELD_TAGS)

    per_site_html: dict[str, str] = {}
    for s in sites:
        ext = s.template_ext
        site_dir = debug_dir / s.name
        site_dir.mkdir(parents=True, exist_ok=True)
        desc_file = site_dir / f'description{ext}'
        src_ext = source_exts.get(s.name, ext)
        body_html = (
            _to_html(desc_file.read_text(), src_ext, shield_tags)
            if desc_file.exists()
            else '<em>(no description)</em>'
        )
        per_site_html[s.name] = (
            (_icon_html(icon_rel) if icon_rel else '')
            + f'<div class="description">{body_html}</div>\n'
            + _images_html(image_entries)
        )
        _write_metadata(site_dir, project, config, s)

    (debug_dir / 'index.html').write_text(
        _page(project, config, sites, per_site_html, zip_name=zip_name)
    )


# ── conversion ───────────────────────────────────────────────────────────────


def _to_html(text: str, ext: str, shield_tags: list[str] = None) -> str:
    if ext == '.html':
        return text
    if ext == '.md':
        tags = shield_tags or []
        placeholders = {tag: f'\x00{tag}\x00' for tag in tags}
        for tag in tags:
            text = text.replace(f'<{tag}>', placeholders[tag])
            text = text.replace(f'</{tag}>', f'\x00/{tag}\x00')
        result = markdown.markdown(text, extensions=['extra'])
        for tag in tags:
            result = result.replace(placeholders[tag], f'<{tag}>')
            result = result.replace(f'\x00/{tag}\x00', f'</{tag}>')
        return result
    if ext == '.bbcode':
        return _pmc.bbcode_to_html(text)
    return f'<pre>{_html.escape(text)}</pre>'


# ── metadata table ────────────────────────────────────────────────────────────


def _combined_metadata_table(project: Project, config: dict, sites: list[str]) -> str:
    # Build per-site field dicts, preserving insertion order
    site_fields: dict[str, dict[str, str]] = {
        s.name: dict(_site_rows(s, project, config)) for s in sites
    }

    # Ordered union of all field names: common fields first, then site-specific
    seen: set[str] = set()
    order: list[str] = []
    for fields in site_fields.values():
        for k in fields:
            if k not in seen:
                seen.add(k)
                order.append(k)

    labels = [s.label for s in sites]
    header = '<tr><th></th>' + ''.join(f'<th>{l}</th>' for l in labels) + '</tr>'
    rows = ''
    for field in order:
        cells = ''.join(
            f'<td>{site_fields[s.name][field]}</td>'
            if field in site_fields[s.name]
            else "<td class='na'>—</td>"
            for s in sites
        )
        rows += f'<tr><th>{_html.escape(field)}</th>{cells}</tr>'

    return f'<table class="meta">{header}{rows}</table>\n'


def _site_rows(site: Site, project: Project, config: dict) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []

    rows.append(('Name', _e(project.name)))
    rows.append(('Pack', _e(project.pack)))
    if config.get('version'):
        rows.append(('Version', _e(str(config['version']))))

    versions = _expand_versions(config)
    v = versions.get(site.name)
    if v:
        if isinstance(v, dict):
            vstr = _e(str(v.get('version', '?')))
            vtype = v.get('type', 'exact')
            rows.append(
                (
                    'Minecraft',
                    f"{vstr} <span class='gloss'>[{_e(vtype)}]</span>"
                    if vtype != 'exact'
                    else vstr,
                )
            )
        else:
            rows.append(('Minecraft', _e(str(v))))

    if config.get('summary'):
        rows.append(('Summary', _e(config['summary'])))

    sc = config.get(site.name, {})
    if sc.get('id'):
        rows.append(('ID', _e(str(sc['id']))))
    if sc.get('slug'):
        rows.append(('Slug', _e(str(sc['slug']))))

    for label, value in site.preview_rows(sc):
        rows.append((label, _e(value)))

    return rows


def _write_metadata(site_dir: Path, project: Project, config: dict, site: Site) -> None:
    # The submission contract: what Puppy will actually send to the platform.
    # preview.html lets you validate visuals; metadata.yaml lets tests (and you)
    # validate the contract — slugs, IDs, and site-specific fields — before upload.
    meta = {'name': project.name, 'pack': project.pack}
    if config.get('version'):
        meta['version'] = str(config['version'])
    sc = config.get(site.name, {})
    meta.update(sc)
    (site_dir / 'metadata.yaml').write_text(
        yaml.dump(meta, default_flow_style=False, allow_unicode=True, sort_keys=False)
    )


def _e(s: str) -> str:
    return _html.escape(s)


# ── HTML fragments ────────────────────────────────────────────────────────────


def _icon_html(icon_rel: str) -> str:
    return f'<div class="icon"><img src="{icon_rel}" alt="icon"></div>\n'


def _images_html(images: list[tuple[str, str, str]]) -> str:
    if not images:
        return ''
    items = ''
    for fname, title, desc in images:
        caption = ''
        if title:
            caption = f'<figcaption><strong>{_e(title)}</strong>'
            if desc:
                caption += f': {_e(desc)}'
            caption += '</figcaption>'
        items += f'<figure><a href="images/{fname}" target="_blank"><img src="images/{fname}" alt="{_e(title)}"></a>{caption}</figure>\n'
    return f'<div class="images">{items}</div>\n'


# ── page shell ────────────────────────────────────────────────────────────────


def _page(
    project: Project,
    config: dict,
    sites: list[str],
    per_site_html: dict[str, str],
    zip_name: str = None,
) -> str:
    meta_table = _combined_metadata_table(project, config, sites)

    tab_buttons = ''
    tab_panes = ''
    for i, s in enumerate(sites):
        active_cls = ' active' if i == 0 else ''
        display = 'block' if i == 0 else 'none'
        label = s.label
        tab_buttons += f'<button class="tab-btn{active_cls}" onclick="showTab(\'{s}\')" id="btn-{s}">{label}</button>\n'
        tab_panes += f'<div class="tab-pane" id="pane-{s}" style="display:{display}">{per_site_html.get(s.name, "")}</div>\n'

    zip_line = (
        f'<p class="zip">Pack: <a href="{_e(zip_name)}">{_e(zip_name)}</a></p>\n'
        if zip_name
        else ''
    )
    title = _e(project.name)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title} \u2014 puppy dry-run</title>
<style>
  body {{ font-family: sans-serif; max-width: 960px; margin: 2rem auto; padding: 0 1rem; color: #222; }}
  h1 {{ margin-bottom: 1rem; }}
  table.meta {{ border-collapse: collapse; margin-bottom: 1.5rem; width: 100%; font-size: 0.9rem; }}
  table.meta th, table.meta td {{ padding: 0.35rem 0.6rem; border: 1px solid #ddd; text-align: left; vertical-align: top; }}
  table.meta th {{ background: #f8f8f8; font-weight: 600; }}
  table.meta thead th {{ text-align: center; }}
  table.meta tbody th {{ width: 10rem; }}
  .gloss {{ color: #888; font-size: 0.85em; }}
  td.na {{ color: #999; text-align: center; background: #f8f8f8; }}
  .tabs {{ display: flex; gap: 0.5rem; margin: 1.5rem 0 1rem; }}
  .tab-btn {{ padding: 0.4rem 1.1rem; border: 1px solid #bbb; border-radius: 4px; background: #f5f5f5; cursor: pointer; font-size: 0.95rem; }}
  .tab-btn.active {{ background: #222; color: #fff; border-color: #222; }}
  .icon {{ margin-bottom: 1rem; }}
  .icon img {{ width: 128px; height: 128px; image-rendering: pixelated; border: 1px solid #eee; }}
  .description {{ border: 1px solid #e8e8e8; border-radius: 4px; padding: 1rem 1.25rem; margin-bottom: 1.5rem; line-height: 1.6; }}
  .images {{ display: flex; flex-wrap: wrap; gap: 1rem; margin-top: 0.5rem; }}
  .images figure {{ margin: 0; max-width: 290px; }}
  .images img {{ max-width: 100%; border: 1px solid #eee; }}
  .images figcaption {{ font-size: 0.82rem; color: #666; margin-top: 0.3rem; }}
</style>
</head>
<body>
<h1>{title}</h1>
{zip_line}{meta_table}<div class="tabs">
{tab_buttons}</div>
{tab_panes}<script>
function showTab(id) {{
  document.querySelectorAll('.tab-pane').forEach(p => p.style.display = 'none');
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('pane-' + id).style.display = 'block';
  document.getElementById('btn-' + id).classList.add('active');
}}
</script>
</body>
</html>"""
