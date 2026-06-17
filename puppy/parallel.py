import sys
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

from puppy.errors import prefix_site_error

_orig_stdout = sys.stdout
_tls = threading.local()
_write_lock = threading.Lock()


class _TLSStdout:
    def write(self, s: str) -> int:
        cap = getattr(_tls, 'cap', None)
        if cap is not None:
            cap._receive(s)
        else:
            _orig_stdout.write(s)
        return len(s)

    def flush(self) -> None:
        if getattr(_tls, 'cap', None) is None:
            _orig_stdout.flush()

    def isatty(self) -> bool:
        return _orig_stdout.isatty()


class _SiteCapture:
    def __init__(self, is_tty: bool):
        self.is_tty = is_tty
        self.lines: list[str] = []
        self._buf = ''

    def _receive(self, s: str) -> None:
        self._buf += s
        while '\n' in self._buf:
            line, self._buf = self._buf.split('\n', 1)
            self.lines.append(line)
            if not self.is_tty:
                with _write_lock:
                    _orig_stdout.write(line + '\n')
                    _orig_stdout.flush()

    def _flush_remaining(self) -> None:
        if self._buf:
            line = self._buf
            self._buf = ''
            self.lines.append(line)
            if not self.is_tty:
                with _write_lock:
                    _orig_stdout.write(line + '\n')
                    _orig_stdout.flush()


def run_sites_parallel(tasks: list[tuple[str, callable]], all_labels: list[str] | None = None, verbosity: int = 0) -> None:
    if not tasks:
        return
    if len(tasks) == 1 and not all_labels:
        tasks[0][1]()
        return

    is_tty = _orig_stdout.isatty()
    captures = {label: _SiteCapture(is_tty) for label, _ in tasks}
    errors: list[BaseException] = []

    def _run_one(label: str, fn) -> None:
        _tls.cap = captures[label]
        try:
            fn()
        except SystemExit as e:
            errors.append(prefix_site_error(label, e))
        except KeyboardInterrupt:
            raise
        except BaseException as e:
            if verbosity >= 1:
                traceback.print_exc()
            errors.append(SystemExit(f'{label}: unexpected error: {e}'))
        finally:
            captures[label]._flush_remaining()
            _tls.cap = None

    prev = sys.stdout
    sys.stdout = _TLSStdout()
    try:
        if is_tty:
            _run_tty(tasks, captures, _run_one, all_labels=all_labels)
        else:
            _run_plain(tasks, _run_one)
    finally:
        sys.stdout = prev

    if len(errors) == 1:
        raise errors[0]
    if errors:
        raise SystemExit('\n'.join(str(e) for e in errors))


def _run_plain(tasks: list, run_one) -> None:
    with ThreadPoolExecutor(max_workers=len(tasks)) as ex:
        for label, fn in tasks:
            ex.submit(run_one, label, fn)


def _run_tty(tasks: list, captures: dict, run_one, all_labels: list[str] | None = None) -> None:
    from rich.console import Console
    from rich.live import Live
    from rich.columns import Columns
    from rich.panel import Panel

    console = Console(file=_orig_stdout, highlight=False)
    display_labels = all_labels if all_labels else [label for label, _ in tasks]

    def make_display():
        panels = []
        for label in display_labels:
            cap = captures.get(label)
            panels.append(Panel('\n'.join(cap.lines) if cap else '', title=label))
        return Columns(panels, equal=True, expand=True)

    with Live(make_display(), console=console, refresh_per_second=4, redirect_stdout=False, redirect_stderr=False) as live:
        with ThreadPoolExecutor(max_workers=len(tasks)) as ex:
            futures = [ex.submit(run_one, label, fn) for label, fn in tasks]
            for _ in as_completed(futures):
                live.update(make_display())
