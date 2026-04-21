import json
import subprocess
from pathlib import Path

from puppy.core import Project


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
        failures = [l for l in stdout_lines if 'failed' in l.lower()]
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
