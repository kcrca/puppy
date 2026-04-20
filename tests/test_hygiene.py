import json
from pathlib import Path

def test_worker_settings_patch(tmp_path):
    from puppy.runner import _patch_settings
    import puppy.runner as runner_mod

    worker_dir = tmp_path / "PackUploader"
    worker_dir.mkdir()
    settings = worker_dir / "settings.json"
    settings.write_text(json.dumps({"ewan": True}))

    orig = runner_mod.WORKER_DIR
    runner_mod.WORKER_DIR = worker_dir
    try:
        _patch_settings()
    finally:
        runner_mod.WORKER_DIR = orig

    assert json.loads(settings.read_text())["ewan"] is False
