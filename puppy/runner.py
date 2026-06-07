import shutil
import tempfile
import webbrowser
from pathlib import Path

from puppy.checks import check_auth, check_preflight
from puppy.config import ConfigSynthesizer, _load_yaml, build_projects_context
from puppy.core import Project
from puppy.puller import run_pull
from puppy.init import run_init
from puppy.preview import generate as generate_preview
from puppy.publisher import _resolve_zip
from puppy.renderer import render
from puppy.searcher import ContentDiscovery
from puppy.sites import SITES, SiteVisitor, _ALIASES
from puppy.creator import run_create
from puppy.syncer import run_push


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
    if config.get('pack') or config.get('name'):
        # Flat single-project: puppy_home is the project source, parent is the project root
        return [puppy_home.parent]
    raise SystemExit(
        f'Cannot find projects in {puppy_home / "puppy.yaml"} — '
        'add a projects: list or a pack:/name: key'
    )


def _determine_roots(directory: Path) -> tuple[Path, list[Path]]:
    """Return (puppy_home, [project_roots]).

    Finds the puppy home by locating auth.yaml: either one level down
    (global root) or by walking up from the current directory.
    Works from the global root, the puppy home, or anywhere beneath it.
    """
    # Global root: auth.yaml is inside a puppy/ subdir
    if (directory / 'puppy' / 'auth.yaml').exists():
        puppy_home = directory / 'puppy'
        return puppy_home, _resolve_projects(puppy_home)

    # Walk up to find the puppy home
    for candidate in [directory, *directory.parents]:
        if (candidate / 'auth.yaml').exists() and (candidate / 'puppy.yaml').exists():
            puppy_home = candidate
            if directory == puppy_home:
                return puppy_home, _resolve_projects(puppy_home)
            rel = directory.relative_to(puppy_home)
            project_root = puppy_home / rel.parts[0]
            return puppy_home, [project_root]

    raise SystemExit(
        f'Cannot determine project structure from {directory}\n'
        'Run from the global root, puppy home, or anywhere beneath it.'
    )




def run(
    *,
    action: str,
    directory: Path,
    dry_run: bool,
    verbosity: int,
    site: str | None,
    version: str | None,
    pack: bool = False,
    pack_filter: list[str] | None = None,
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

    dry_run_projects: list = []
    after_push_messages: list = []
    ran_any = False
    for project_root in projects:
        config = ConfigSynthesizer(
            puppy_home, project_root, site=site
        ).get_running_config()
        project = Project.from_config(project_root, config, dry_run=dry_run)

        if pack_filter and project.pack not in pack_filter:
            continue
        ran_any = True

        resolved_version = version or config.get('version')
        if action == 'push' and pack and not resolved_version:
            raise SystemExit(
                f'[{project.name}] push --pack requires --version or version: in puppy.yaml'
            )

        if verbosity >= 1:
            label = action + (' --pack' if action == 'push' and pack else '')
            print(
                f'[{project.name}] {label}'
                + (f' v{resolved_version}' if resolved_version else '')
            )

        if dry_run:
            single = len(projects) == 1 or pack_filter is not None
            _run_dry(
                action,
                project,
                config,
                resolved_version,
                verbosity,
                puppy_home,
                site,
                pack=pack,
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
                pack,
                force,
                images,
                verbosity,
            )
            after_push_messages += _collect_after_push(config, site)


    if pack_filter and not ran_any:
        raise SystemExit(f'No projects matching {pack_filter!r} found in {puppy_home}')

    if len(dry_run_projects) > 1:
        _write_batch_index(dry_run_projects, open_browser=open_browser)

    for msg in after_push_messages:
        print(msg)


def _write_batch_index(projects: list, open_browser: bool = False) -> None:
    base = Path(tempfile.gettempdir()) / 'puppy'
    tabs = ''.join(
        f'<button class="tab" onclick="show(\'{p.pack}\', this)">{p.name}</button>'
        for p in projects
    )
    frames = ''.join(
        f'<iframe id="{p.pack}" src="{p.pack}/index.html" style="display:none"></iframe>'
        for p in projects
    )
    first = projects[0].pack
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


def _run_dry(action, project, config, version, verbosity, puppy_home, site, pack=False, print_url=True, open_browser=True):
    debug_dir = Path(tempfile.gettempdir()) / 'puppy' / project.pack
    if debug_dir.exists():
        shutil.rmtree(debug_dir)
    debug_dir.mkdir(parents=True)

    zip_name: str = None
    if action in ('push',):
        config = dict(config)
        config['projects'] = build_projects_context(puppy_home)
        discovery = ContentDiscovery(puppy_home, project.root)
        project_type = config.get('project_type', 'pack')
        sites = list(SiteVisitor(site, project_type=project_type))
        if verbosity >= 1 and not site:
            for s in SITES:
                if s not in sites:
                    print(f'  [{s.label}] skipping — project_type "{project_type}" not supported')
        source_exts: dict[str, str] = {}
        for s in sites:
            body, source_path = discovery.find_description(site=s)
            if body:
                site_config = ConfigSynthesizer(
                    puppy_home, project.root, site=s
                ).get_running_config()
                site_config.setdefault('name', project.name)
                site_config.setdefault('pack', project.pack)
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

        if pack:
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
    for s in SiteVisitor(site, project_type=config.get('project_type', 'pack')):
        msg = config.get(s.name, {}).get('after_push')
        if msg:
            messages.append(f'[{s.label}] {msg}')
    return messages


def _dispatch(
    action, project, config, version, auth, puppy_home, site, pack, force, images, verbosity
):
    if action == 'create':
        run_create(
            project=project,
            config=config,
            puppy_home=puppy_home,
            auth=auth,
            site=site,
            images=images,
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
            pack=pack,
            force=force,
            images=images,
            verbosity=verbosity,
            auth=auth,
        )
    else:
        raise NotImplementedError(f'{action}: unknown action')
