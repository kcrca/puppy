import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from puppy.checks import check_auth, check_preflight
from puppy.config import ConfigSynthesizer, _load_yaml, build_projects_context
from puppy.core import Project
from puppy.creator import run_create
from puppy.importer import run_import
from puppy.init import run_init
from puppy.preview import generate as generate_preview
from puppy.publisher import _resolve_zip
from puppy.renderer import render
from puppy.searcher import ContentDiscovery
from puppy.sites import SITES, SiteVisitor, _ALIASES
from puppy.syncer import run_push


WORKER_DIR = Path.home() / 'PackUploader'


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

    Three valid starting points:
      Global Root  (~/neon)               — has puppy/auth.yaml
      Puppy Home   (~/neon/puppy)         — has auth.yaml directly
      Project Root (~/neon/puppy/NeonGlow) — has puppy/ subdir, no auth.yaml
    """
    # Global Root: auth.yaml lives inside the puppy/ subdir
    if (directory / 'puppy' / 'auth.yaml').exists():
        puppy_home = directory / 'puppy'
        return puppy_home, _resolve_projects(puppy_home)

    # Puppy Home itself
    if (directory / 'auth.yaml').exists():
        return directory, _resolve_projects(directory)

    # Project Root: has a puppy/ subdir (the project source)
    if (directory / 'puppy').is_dir():
        return directory.parent, [directory]

    raise SystemExit(
        f'Cannot determine project structure from {directory}\n'
        'Run from the global root, puppy home, or a project root.'
    )


def _write_auth(worker_dir: Path, auth: dict) -> None:
    (worker_dir / 'auth.json').write_text(json.dumps(auth, indent=2))


def _patch_settings(worker_dir: Path, config: dict) -> None:
    settings_path = worker_dir / 'settings.json'
    settings = json.loads(settings_path.read_text())
    settings['ewan'] = False
    settings['templateDefaults'] = {}
    for site in SITES:
        site.apply_settings(settings, config.get(site.name, {}))
    settings_path.write_text(json.dumps(settings, indent=2))


def _worker_prep(worker_dir: Path, verbosity: int) -> None:
    if not worker_dir.exists():
        raise SystemExit(f'Worker directory not found: {worker_dir}')

    def run(cmd: list[str]) -> None:
        kwargs = {} if verbosity >= 2 else {'capture_output': True}
        result = subprocess.run(cmd, cwd=worker_dir, **kwargs)
        if result.returncode != 0:
            raise SystemExit(f'Worker prep failed: {" ".join(cmd)}')

    run(['git', 'reset', '--hard', 'HEAD'])
    run(['git', 'clean', '-fd'])

    if not (worker_dir / 'node_modules').exists():
        run(['npm', 'install'])


def run(
    *,
    action: str,
    directory: Path,
    dry_run: bool,
    verbosity: int,
    site: str | None,
    version: str | None,
    pack: bool = False,
    pack_filter: str | None = None,
    force: bool = False,
    worker: Path = None,
) -> None:
    if action == 'init':
        run_init(directory)
        return

    worker_dir = worker or WORKER_DIR

    if action == 'clean':
        check_preflight()
        _worker_prep(worker_dir, verbosity)
        return

    if site:
        site = ','.join(_ALIASES.get(s.strip(), s.strip()) for s in site.split(','))
    puppy_home, projects = _determine_roots(directory)
    auth = check_auth(puppy_home, site)

    dry_run_projects: list = []
    ran_any = False
    for project_root in projects:
        config = ConfigSynthesizer(
            puppy_home, project_root, site=site
        ).get_running_config()
        project = Project.from_config(project_root, config)

        if pack_filter and project.pack != pack_filter:
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
            _run_dry(
                action,
                project,
                config,
                resolved_version,
                verbosity,
                puppy_home,
                site,
                pack=pack,
                print_url=len(projects) == 1,
            )
            dry_run_projects.append(project)
        else:
            check_preflight()
            _worker_prep(worker_dir, verbosity)
            _write_auth(worker_dir, auth)
            _patch_settings(worker_dir, config)
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
                verbosity,
                worker_dir,
            )


    if pack_filter and not ran_any:
        raise SystemExit(f'No project with pack slug {pack_filter!r} found in {puppy_home}')

    if len(dry_run_projects) > 1:
        _write_batch_index(dry_run_projects)


def _write_batch_index(projects: list) -> None:
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
  .tab {{ padding: 10px 28px; border: 2px solid #555; border-radius: 6px; cursor: pointer;
          background: #333; color: #aaa; font-size: 16px; font-weight: bold; }}
  .tab:hover {{ background: #444; color: #fff; border-color: #888; }}
  .tab.active {{ background: #0af; color: #000; border-color: #0af; }}
  iframe {{ display: block; width: 100%; height: calc(100vh - 61px); border: none; }}
</style>
</head>
<body>
<div id="tabs"><span id="tabs-label">Projects:</span>{tabs}</div>
{frames}
<script>
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


def _run_dry(action, project, config, version, verbosity, puppy_home, site, pack=False, print_url=True):
    debug_dir = Path(tempfile.gettempdir()) / 'puppy' / project.pack
    if debug_dir.exists():
        shutil.rmtree(debug_dir)
    debug_dir.mkdir(parents=True)

    zip_name: str = None
    if action in ('push',):
        config = dict(config)
        config['projects'] = build_projects_context(puppy_home)
        discovery = ContentDiscovery(puppy_home, project.root)
        sites = list(SiteVisitor(site))
        source_exts: dict[str, str] = {}
        for s in sites:
            body, source_path = discovery.find_description(site=s)
            if body:
                site_config = ConfigSynthesizer(
                    puppy_home, project.root, site=s
                ).get_running_config()
                site_config['projects'] = config['projects']
                rendered = render(body, site_config, source=str(source_path), site=s)
                staged_ext = source_path.suffix if source_path else s.template_ext
                if source_path and source_path.suffix == '.md':
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


def _dispatch(
    action, project, config, version, auth, puppy_home, site, pack, force, verbosity, worker_dir
):
    if action == 'import':
        run_import(
            project=project,
            config=config,
            auth=auth,
            worker_dir=worker_dir,
            site=site,
            verbosity=verbosity,
        )
    elif action == 'create':
        run_create(
            project=project,
            config=config,
            auth=auth,
            worker_dir=worker_dir,
            site=site,
            verbosity=verbosity,
        )
    elif action == 'push':
        run_push(
            project=project,
            config=config,
            worker_dir=worker_dir,
            puppy_home=puppy_home,
            site=site,
            version=version,
            pack=pack,
            force=force,
            verbosity=verbosity,
        )
    else:
        raise NotImplementedError(f"action '{action}' not yet implemented")
