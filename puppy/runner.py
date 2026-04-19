import subprocess
import tempfile
from pathlib import Path

from puppy.checks import check_auth, check_preflight
from puppy.config import ConfigSynthesizer
from puppy.core import Project


WORKER_DIR = Path.home() / "PackUpdate"


def _resolve_projects(directory: Path, puppy_home: Path) -> list[Path]:
    """
    Return explicit project roots listed under projects: in global puppy.yaml.
    Each entry is a directory name relative to puppy_home.
    """
    from puppy.config import _load_yaml
    config = _load_yaml(puppy_home / "puppy.yaml")
    names = config.get("projects", [])
    if not names:
        raise SystemExit(
            f"No projects: list found in {puppy_home / 'puppy.yaml'} — "
            "add a projects: key to run in batch mode"
        )
    roots = []
    for name in names:
        root = puppy_home / name
        if not root.is_dir():
            raise SystemExit(f"Project directory not found: {root}")
        roots.append(root)
    return roots


def _determine_roots(directory: Path) -> tuple[Path, list[Path]]:
    """Return (puppy_home, [project_roots])."""
    project_puppy = directory / "puppy"
    if project_puppy.is_dir():
        # directory is a single project root; puppy_home is its parent
        return directory.parent, [directory]
    # directory is the puppy_home — batch mode via explicit projects: list
    return directory, _resolve_projects(directory, directory)


def _worker_prep(pack: str, verbosity: int) -> None:
    pack_dir = WORKER_DIR / pack
    if not pack_dir.exists():
        raise SystemExit(f"Worker pack directory not found: {pack_dir}")

    def run(cmd: list[str]) -> None:
        kwargs = {} if verbosity >= 2 else {"capture_output": True}
        result = subprocess.run(cmd, cwd=pack_dir, **kwargs)
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
) -> None:
    check_preflight()

    puppy_home, projects = _determine_roots(directory)

    auth = check_auth(puppy_home)

    for project_root in projects:
        project = Project(project_root)
        config = ConfigSynthesizer(puppy_home, project_root, site=site).get_running_config()

        resolved_version = version or config.get("version")
        if action == "publish" and not resolved_version:
            raise SystemExit(f"[{project.name}] publish requires --version or version: in puppy.yaml")

        if verbosity >= 1:
            print(f"[{project.name}] {action}" + (f" v{resolved_version}" if resolved_version else ""))

        if dry_run:
            _run_dry(action, project, config, resolved_version, site, verbosity)
        else:
            _worker_prep(project.pack, verbosity)
            _dispatch(action, project, config, resolved_version, auth, puppy_home, site, verbosity)


def _run_dry(action, project, config, version, site, verbosity):
    import json
    debug_dir = Path(tempfile.gettempdir()) / "puppy" / project.pack
    debug_dir.mkdir(parents=True, exist_ok=True)
    payload = {"action": action, "version": version, "config": config}
    out = debug_dir / f"{action}.json"
    out.write_text(json.dumps(payload, indent=2))
    if verbosity >= 1:
        print(f"[{project.name}] dry-run payload written to {out}")


def _dispatch(action, project, config, version, auth, puppy_home, site, verbosity):
    raise NotImplementedError(f"action '{action}' not yet implemented")
