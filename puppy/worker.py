import json
import subprocess
from pathlib import Path

from puppy.core import Project
from puppy.sites import SITES


def worker_prep(worker_dir: Path, verbosity: int) -> None:
    if not worker_dir.exists():
        raise SystemExit(f'Worker directory not found: {worker_dir}')

    def run(cmd: list[str]) -> None:
        kwargs = {} if verbosity >= 2 else {'capture_output': True}
        result = subprocess.run(cmd, cwd=worker_dir, **kwargs)
        if result.returncode != 0:
            raise SystemExit(f'Worker prep failed: {" ".join(cmd)}')

    run(['git', 'reset', '--hard', '-q', 'HEAD'])
    run(['git', 'clean', '-fd', '-q'])

    if not (worker_dir / 'node_modules').exists():
        run(['npm', 'install'])


def write_auth(worker_dir: Path, auth: dict) -> None:
    (worker_dir / 'auth.json').write_text(json.dumps(auth, indent=2))


def patch_settings(worker_dir: Path, config: dict) -> None:
    settings_path = worker_dir / 'settings.json'
    settings = json.loads(settings_path.read_text())
    settings['ewan'] = False
    settings['templateDefaults'] = {}
    for site in SITES:
        site.apply_settings(settings, config.get(site.name, {}))
    settings_path.write_text(json.dumps(settings, indent=2))


def run_worker(script: str, worker_dir: Path, verbosity: int, *, stream: bool = False) -> None:
    cmd = ['node', '--no-warnings', script]
    if stream:
        proc = subprocess.Popen(
            cmd, cwd=worker_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        stdout_lines: list[str] = []
        for line in proc.stdout:
            stdout_lines.append(line)
            if verbosity >= 1:
                print(line, end='', flush=True)
        stderr = proc.stderr.read()
        proc.wait()
        if proc.returncode != 0:
            raise SystemExit(f'Worker failed\n{stderr}'.strip())
        failures = [line for line in stdout_lines if 'failed' in line.lower()]
        if failures:
            if verbosity < 1:
                print('WARNING: worker reported failures:')
                for line in failures:
                    print(f'  {line}', end='')
            else:
                print(f'WARNING: {len(failures)} failure(s) in worker output (see above)')
    else:
        kwargs: dict = {'cwd': worker_dir}
        if verbosity < 2:
            kwargs['capture_output'] = True
        result = subprocess.run(cmd, **kwargs)
        if result.returncode != 0:
            detail = result.stderr.decode() if verbosity < 2 else ''
            raise SystemExit(f'Worker failed\n{detail}'.strip())


def read_output(project: Project, worker_dir: Path) -> dict:
    project_json = worker_dir / 'projects' / project.pack / 'project.json'
    if not project_json.exists():
        raise SystemExit(
            f'[{project.name}] expected output not found: {project_json}\n'
            'Check that the platform IDs/slugs in puppy.yaml are correct.'
        )
    return json.loads(project_json.read_text())
