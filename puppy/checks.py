import shutil
from pathlib import Path


REQUIRED_TOOLS = ["git", "node", "npm"]


def check_preflight() -> None:
    missing = [t for t in REQUIRED_TOOLS if shutil.which(t) is None]
    if missing:
        raise SystemExit(f"Missing required tools: {', '.join(missing)}")


def check_auth(puppy_home: Path) -> dict:
    gitignore = puppy_home / ".gitignore"
    auth_file = puppy_home / "auth.yaml"

    if not auth_file.exists():
        raise SystemExit(f"auth.yaml not found in {puppy_home}")

    if not gitignore.exists() or "auth.yaml" not in gitignore.read_text().splitlines():
        raise SystemExit(f"auth.yaml must be listed in {gitignore} — refusing to run")

    import yaml
    with auth_file.open() as f:
        return yaml.safe_load(f) or {}
