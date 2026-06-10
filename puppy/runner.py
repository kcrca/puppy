import shutil
import tempfile
import webbrowser
from pathlib import Path

from puppy.checks import check_auth, check_preflight
from puppy.config import ConfigSynthesizer, _load_yaml, build_projects_context
from puppy.core import Project, find_puppy_home
from puppy.puller import run_pull
from puppy.init import run_init
from puppy.preview import generate as generate_preview
from puppy.publisher import _resolve_zip
from puppy.renderer import render
from puppy.searcher import ContentDiscovery
from puppy.sites import CURSEFORGE, MODRINTH, PMC, SITES, SiteVisitor, _ALIASES
from puppy.creator import run_create
from puppy.syncer import run_push, apply_env_sides


def _resolve_projects(puppy_home: Path) -> list[Path]:
    config = _load_yaml(puppy_home / 'puppy.yaml')
    names = config.get('projects')
    if names:
        roots = []
        for name in names:
            root = puppy_home / name
            if not root.is_dir():
                raise SystemExit(f'Project directory not found: {root}')
            roots.append(root)
        return roots
    if config.get('handle') or config.get('name'):
        # Flat single-project: puppy_home is the project source, parent is the project root
        return [puppy_home.parent]
    raise SystemExit(
        f'Cannot find projects in {puppy_home / "puppy.yaml"} — '
        'add a projects: list or a handle:/name: key'
    )


def _determine_roots(directory: Path) -> tuple[Path, list[Path]]:
    puppy_home = find_puppy_home(directory)
    if not puppy_home:
        raise SystemExit(
            f'Cannot determine project structure from {directory}\n'
            'Run from the global root, puppy home, or anywhere beneath it.'
        )
    if directory == puppy_home or directory == puppy_home.parent:
        return puppy_home, _resolve_projects(puppy_home)
    rel = directory.relative_to(puppy_home)
    project_root = puppy_home / rel.parts[0]
    return puppy_home, [project_root]




def run(
    *,
    action: str,
    directory: Path,
    dry_run: bool,
    verbosity: int,
    site: str | None,
    version: str | None,
    upload_file: bool = False,
    handle_filter: list[str] | None = None,
    force: bool = False,
    images: bool = False,
    open_browser: bool = True,
) -> None:
    if action == 'init':
        run_init(directory)
        return

    if site:
        site = ','.join(_ALIASES.get(s.strip(), s.strip()) for s in site.split(','))
    puppy_home, projects = _determine_roots(directory)
    if not site:
        home_config = _load_yaml(puppy_home / 'puppy.yaml') or {}
        declared = home_config.get('sites')
        if declared:
            site = ','.join(_ALIASES.get(str(s).strip(), str(s).strip()) for s in declared)
    auth = check_auth(puppy_home, site)

    project_entries = []
    for project_root in projects:
        config = ConfigSynthesizer(puppy_home, project_root, site=site).get_running_config()
        project = Project.from_config(project_root, config, dry_run=dry_run)
        if handle_filter and project.handle not in handle_filter:
            continue
        project_entries.append((project_root, config, project))

    all_labels = None
    if action == 'push' and len(project_entries) > 1:
        visitor = SiteVisitor(site)
        _site_order = [(CURSEFORGE, 'curseforge'), (MODRINTH, 'modrinth'), (PMC, 'planetminecraft')]
        seen: set[str] = set()
        for _, cfg, _ in project_entries:
            for s, key in _site_order:
                if s in visitor and cfg.get(key, {}).get('id'):
                    seen.add(s.label)
        ordered = [s.label for s, _ in _site_order if s.label in seen]
        if len(ordered) > 1:
            all_labels = ordered

    dry_run_projects: list = []
    after_push_messages: list = []
    ran_any = False
    for project_root, config, project in project_entries:
        ran_any = True

        if 'type' not in config:
            raise SystemExit(
                f'[{project.name}] type is required in puppy.yaml (pack, mod, or world)'
            )

        resolved_version = version or config.get('version')
        if action == 'push' and upload_file and not resolved_version:
            raise SystemExit(
                f'[{project.name}] push --file requires --version or version: in puppy.yaml'
            )

        if verbosity >= 1:
            label = action + (' --file' if action == 'push' and upload_file else '')
            print(
                f'[{project.name}] {label}'
                + (f' v{resolved_version}' if resolved_version else '')
            )

        if dry_run:
            single = len(project_entries) == 1
            _run_dry(
                action,
                project,
                config,
                resolved_version,
                verbosity,
                puppy_home,
                site,
                upload_file=upload_file,
                print_url=single,
                open_browser=open_browser and single,
            )
            dry_run_projects.append(project)
        else:
            check_preflight()
            _dispatch(
                action,
                project,
                config,
                resolved_version,
                auth,
                puppy_home,
                site,
                upload_file,
                force,
                images,
                verbosity,
                all_labels=all_labels,
            )
            after_push_messages += _collect_after_push(config, site)


    if handle_filter and not ran_any:
        raise SystemExit(f'No projects matching {handle_filter!r} found in {puppy_home}')

    if len(dry_run_projects) > 1:
        _write_batch_index(dry_run_projects, open_browser=open_browser)

    for msg in after_push_messages:
        print(msg)


def _write_batch_index(projects: list, open_browser: bool = False) -> None:
    base = Path(tempfile.gettempdir()) / 'puppy'
    tabs = ''.join(
        f'<button class="tab" onclick="show(\'{p.handle}\', this)">{p.name}</button>'
        for p in projects
    )
    frames = ''.join(
        f'<iframe id="{p.handle}" src="{p.handle}/index.html" style="display:none"></iframe>'
        for p in projects
    )
    first = projects[0].handle
    html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Puppy Preview</title>
<style>
  body {{ margin: 0; font-family: sans-serif; }}
  #tabs {{ display: flex; align-items: center; gap: 6px; padding: 10px 12px; background: #111; border-bottom: 3px solid #0af; }}
  #tabs-label {{ color: #0af; font-size: 13px; font-weight: bold;
                 letter-spacing: 1px; margin-right: 8px; white-space: nowrap; }}
  #folder-link {{ color: #888; font-size: 10px; white-space: nowrap; }}
  .tab {{ padding: 10px 28px; border: 2px solid #555; border-radius: 6px; cursor: pointer;
          background: #333; color: #aaa; font-size: 16px; font-weight: bold; }}
  .tab:hover {{ background: #444; color: #fff; border-color: #888; }}
  .tab.active {{ background: #0af; color: #000; border-color: #0af; }}
  iframe {{ display: block; width: 100%; height: calc(100vh - 61px); border: none; }}
</style>
</head>
<body>
<div id="tabs"><span id="tabs-label">Projects:</span>{tabs}<a id="folder-link" href="#">open folder</a></div>
{frames}
<script>
  document.getElementById('folder-link').href = window.location.href.replace(/index\\.html$/, '');
  function show(id, btn) {{
    document.querySelectorAll('iframe').forEach(f => f.style.display = 'none');
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.getElementById(id).style.display = 'block';
    if (btn) btn.classList.add('active');
  }}
  show('{first}', document.querySelector('.tab'));
</script>
</body>
</html>"""
    index = base / 'index.html'
    index.write_text(html)
    print(f'file://{index}')
    if open_browser:
        webbrowser.open(index.as_uri())


def _run_dry(action, project, config, version, verbosity, puppy_home, site, upload_file=False, print_url=True, open_browser=True):
    debug_dir = Path(tempfile.gettempdir()) / 'puppy' / project.handle
    if debug_dir.exists():
        shutil.rmtree(debug_dir)
    debug_dir.mkdir(parents=True)

    zip_name: str = None
    if action in ('push',):
        config = dict(config)
        config['projects'] = build_projects_context(puppy_home)
        config = apply_env_sides(config)
        discovery = ContentDiscovery(puppy_home, project.root)
        project_type = config.get('type', 'pack')
        sites = list(SiteVisitor(site, project_type=project_type))
        if verbosity >= 1 and not site:
            for s in SITES:
                if s not in sites:
                    print(f'  [{s.label}] skipping — type "{project_type}" not supported')
        source_exts: dict[str, str] = {}
        for s in sites:
            body, source_path = discovery.find_description(site=s)
            if body:
                site_config = ConfigSynthesizer(
                    puppy_home, project.root, site=s
                ).get_running_config()
                site_config.setdefault('name', project.name)
                site_config.setdefault('handle', project.handle)
                site_config['projects'] = config['projects']
                rendered = render(body, site_config, source=str(source_path), site=s)
                staged_ext = source_path.suffix if source_path else s.template_ext
                if source_path and source_path.suffix == '.md':
                    md_out = debug_dir / s.name / 'description.md'
                    md_out.parent.mkdir(parents=True, exist_ok=True)
                    md_out.write_text(rendered)
                    rendered = s.convert_md(rendered)
                    staged_ext = s.template_ext
                ext = s.template_ext
                out = debug_dir / s.name / f'description{ext}'
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(rendered)
                source_exts[s.name] = staged_ext

        if upload_file:
            zip_src = _resolve_zip(config, project.puppy_dir, version, project)
            shutil.copy(zip_src, debug_dir / zip_src.name)
            zip_name = zip_src.name

        generate_preview(
            project, config, debug_dir, sites, source_exts, zip_name=zip_name
        )

    preview_path = debug_dir / 'index.html'
    if print_url:
        print(f'file://{preview_path}')
    if open_browser and preview_path.exists():
        webbrowser.open(preview_path.as_uri())


def _collect_after_push(config: dict, site: str | None) -> list:
    messages = []
    if config.get('after_push'):
        messages.append(config['after_push'])
    for s in SiteVisitor(site, project_type=config.get('type', 'pack')):
        msg = config.get(s.name, {}).get('after_push')
        if msg:
            messages.append(f'[{s.label}] {msg}')
    return messages


def _dispatch(
    action, project, config, version, auth, puppy_home, site, upload_file, force, images, verbosity,
    all_labels=None,
):
    if action == 'create':
        run_create(
            project=project,
            config=config,
            puppy_home=puppy_home,
            auth=auth,
            site=site,
            verbosity=verbosity,
        )
    elif action == 'pull':
        run_pull(
            project=project,
            config=config,
            auth=auth,
            site=site,
            images=images,
            verbosity=verbosity,
        )
    elif action == 'push':
        run_push(
            project=project,
            config=config,
            puppy_home=puppy_home,
            site=site,
            version=version,
            upload_file=upload_file,
            force=force,
            images=images,
            verbosity=verbosity,
            auth=auth,
            all_labels=all_labels,
        )
    else:
        raise NotImplementedError(f'{action}: unknown action')
