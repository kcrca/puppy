import json
import subprocess
import tempfile
from pathlib import Path

from puppy.checks import check_auth, check_preflight
from puppy.config import ConfigSynthesizer
from puppy.core import Project
from puppy.sites import _ALIASES


WORKER_DIR = Path.home() / "PackUploader"


def _resolve_projects(puppy_home: Path) -> list[Path]:
    from puppy.config import _load_yaml
    config = _load_yaml(puppy_home / "puppy.yaml")
    names = config.get("projects")
    if names:
        roots = []
        for name in names:
            root = puppy_home / name
            if not root.is_dir():
                raise SystemExit(f"Project directory not found: {root}")
            roots.append(root)
        return roots
    if config.get("pack") or config.get("name"):
        # Flat single-project: puppy_home is the project source, parent is the project root
        return [puppy_home.parent]
    raise SystemExit(
        f"Cannot find projects in {puppy_home / 'puppy.yaml'} — "
        "add a projects: list or a pack:/name: key"
    )


def _determine_roots(directory: Path) -> tuple[Path, list[Path]]:
    """Return (puppy_home, [project_roots]).

    Three valid starting points:
      Global Root  (e.g. ~/clean)          — has puppy/auth.yaml
      Puppy Home   (e.g. ~/clean/puppy)    — has auth.yaml directly
      Project Root (e.g. ~/clean/puppy/Clean) — has puppy/ subdir, no auth.yaml
    """
    # Global Root: auth.yaml lives inside the puppy/ subdir
    if (directory / "puppy" / "auth.yaml").exists():
        puppy_home = directory / "puppy"
        return puppy_home, _resolve_projects(puppy_home)

    # Puppy Home itself
    if (directory / "auth.yaml").exists():
        return directory, _resolve_projects(directory)

    # Project Root: has a puppy/ subdir (the project source)
    if (directory / "puppy").is_dir():
        return directory.parent, [directory]

    raise SystemExit(
        f"Cannot determine project structure from {directory}\n"
        "Run from the global root, puppy home, or a project root."
    )


def _deep_clear(existing: dict, blank: dict) -> dict:
    """Apply blank over existing: blank keys win, extra existing keys are preserved."""
    result = dict(existing)
    for k, v in blank.items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = _deep_clear(result[k], v)
        else:
            result[k] = v
    return result


def _write_auth(auth: dict) -> None:
    (WORKER_DIR / "auth.json").write_text(json.dumps(auth, indent=2))


_SETTINGS_BLANK = {
    "ewan": False,
    "curseforge": {
        "donation": {"type": None, "value": None},
        "socials": {k: None for k in [
            "bluesky", "discord", "facebook", "github", "instagram",
            "mastodon", "patreon", "pinterest", "reddit", "tiktok",
            "twitch", "twitter", "website", "youtube",
        ]},
    },
    "planetminecraft": {
        "website": {"link": None, "title": None},
    },
    "modrinth": {
        "discord": None,
        "donation": {k: None for k in [
            "buyMeACoffee", "github", "kofi", "other", "patreon", "paypal",
        ]},
    },
    "templateDefaults": {},
}


def _patch_settings(config: dict) -> None:
    settings_path = WORKER_DIR / "settings.json"
    settings = json.loads(settings_path.read_text())

    # Clear all personal defaults (blank wins over existing values)
    for key, blank in _SETTINGS_BLANK.items():
        if blank == {}:
            settings[key] = {}
        elif isinstance(blank, dict) and isinstance(settings.get(key), dict):
            settings[key] = _deep_clear(settings[key], blank)
        else:
            settings[key] = blank

    # Overlay values from merged puppy config
    cf = config.get("curseforge", {})
    if cf.get("socials"):
        settings["curseforge"]["socials"].update(cf["socials"])
    if cf.get("donation"):
        settings["curseforge"]["donation"].update(cf["donation"])

    mr = config.get("modrinth", {})
    if mr.get("discord"):
        settings["modrinth"]["discord"] = mr["discord"]
    if mr.get("donation"):
        settings["modrinth"]["donation"].update(mr["donation"])

    pmc = config.get("planetminecraft", {})
    if pmc.get("website"):
        settings["planetminecraft"]["website"].update(pmc["website"])

    settings_path.write_text(json.dumps(settings, indent=2))


def _worker_prep(verbosity: int) -> None:
    if not WORKER_DIR.exists():
        raise SystemExit(f"Worker directory not found: {WORKER_DIR}")

    def run(cmd: list[str]) -> None:
        kwargs = {} if verbosity >= 2 else {"capture_output": True}
        result = subprocess.run(cmd, cwd=WORKER_DIR, **kwargs)
        if result.returncode != 0:
            raise SystemExit(f"Worker prep failed: {' '.join(cmd)}")

    run(["git", "reset", "--hard", "HEAD"])
    run(["git", "clean", "-fd"])

    if not (WORKER_DIR / "node_modules").exists():
        run(["npm", "install"])


def run(
    *,
    action: str,
    directory: Path,
    dry_run: bool,
    verbosity: int,
    site: str | None,
    version: str | None,
    pack: bool = False,
    force: bool = False,
) -> None:
    if action == "init":
        from puppy.init import run_init
        run_init(directory)
        return

    if site:
        site = ",".join(_ALIASES.get(s.strip(), s.strip()) for s in site.split(","))
    puppy_home, projects = _determine_roots(directory)
    auth = check_auth(puppy_home)

    for project_root in projects:
        config = ConfigSynthesizer(puppy_home, project_root, site=site).get_running_config()
        project = Project.from_config(project_root, config)

        resolved_version = version or config.get("version")
        if action == "push" and pack and not resolved_version:
            raise SystemExit(f"[{project.name}] push --pack requires --version or version: in puppy.yaml")

        if verbosity >= 1:
            label = action + (" --pack" if action == "push" and pack else "")
            print(f"[{project.name}] {label}" + (f" v{resolved_version}" if resolved_version else ""))

        if dry_run:
            _run_dry(action, project, config, resolved_version, verbosity, puppy_home, site, pack=pack)
        else:
            check_preflight()
            _worker_prep(verbosity)
            _write_auth(auth)
            _patch_settings(config)
            _dispatch(action, project, config, resolved_version, auth, puppy_home, site, pack, force, verbosity)


def _run_dry(action, project, config, version, verbosity, puppy_home, site, pack=False):
    import shutil
    from puppy.preview import generate as generate_preview
    from puppy.renderer import md_to_bbcode, md_to_html, render
    from puppy.searcher import ContentDiscovery
    from puppy.syncer import _TEMPLATE_EXT

    debug_dir = Path(tempfile.gettempdir()) / "puppy" / project.pack
    if debug_dir.exists():
        shutil.rmtree(debug_dir)
    debug_dir.mkdir(parents=True)

    zip_name: str | None = None
    if action in ("push",):
        from puppy.config import build_projects_context
        from puppy.sites import SiteVisitor
        config = dict(config)
        config["projects"] = build_projects_context(puppy_home)
        discovery = ContentDiscovery(puppy_home, project.root)
        sites = list(SiteVisitor(site))
        source_exts: dict[str, str] = {}
        for s in sites:
            body, source_path = discovery.find_description(site=s)
            if body:
                site_config = ConfigSynthesizer(puppy_home, project.root, site=s).get_running_config()
                site_config["projects"] = config["projects"]
                rendered = render(body, site_config, source=str(source_path), site=s)
                staged_ext = source_path.suffix if source_path else _TEMPLATE_EXT[s]
                if source_path and source_path.suffix == ".md":
                    if s == "curseforge":
                        rendered = md_to_html(rendered)
                        staged_ext = ".html"
                    elif s == "planetminecraft":
                        rendered = md_to_bbcode(rendered)
                        staged_ext = ".bbcode"
                ext = _TEMPLATE_EXT[s]
                out = debug_dir / s / f"description{ext}"
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(rendered)
                source_exts[s] = staged_ext

        if pack:
            from puppy.publisher import _resolve_zip
            puppy_dir = project.root / "puppy"
            zip_src = _resolve_zip(config, puppy_dir, version, project)
            shutil.copy(zip_src, debug_dir / zip_src.name)
            zip_name = zip_src.name

        generate_preview(project, config, debug_dir, sites, source_exts, zip_name=zip_name)

    preview_path = debug_dir / "index.html"
    print(f"file://{preview_path}")


def _dispatch(action, project, config, version, auth, puppy_home, site, pack, force, verbosity):
    if action == "import":
        from puppy.importer import run_import
        run_import(project=project, config=config, auth=auth, worker_dir=WORKER_DIR, site=site, verbosity=verbosity)
    elif action == "create":
        from puppy.creator import run_create
        run_create(project=project, config=config, worker_dir=WORKER_DIR, site=site, verbosity=verbosity)
    elif action == "push":
        from puppy.syncer import run_push
        run_push(project=project, config=config, worker_dir=WORKER_DIR, puppy_home=puppy_home, site=site, version=version, pack=pack, force=force, verbosity=verbosity)
    else:
        raise NotImplementedError(f"action '{action}' not yet implemented")
