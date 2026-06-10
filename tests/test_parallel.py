import sys
import threading
from unittest.mock import MagicMock, patch

import pytest

import puppy.parallel as parallel
from puppy.parallel import _TLSStdout, run_sites_parallel


# --- path: empty ---

def test_empty_tasks():
    run_sites_parallel([])


# --- path: single task (direct call, no proxy) ---

def test_single_task_runs_without_proxy():
    orig = sys.stdout
    seen = []
    run_sites_parallel([('X', lambda: seen.append(sys.stdout))])
    assert seen[0] is orig


def test_single_task_runs():
    called = []
    run_sites_parallel([('X', lambda: called.append(1))])
    assert called == [1]


# --- path: multiple tasks, non-TTY ---

def test_multiple_tasks_stdout_proxied():
    seen = []
    run_sites_parallel([
        ('A', lambda: seen.append(sys.stdout)),
        ('B', lambda: seen.append(sys.stdout)),
    ])
    assert all(isinstance(s, _TLSStdout) for s in seen)


def test_tasks_run_concurrently():
    barrier = threading.Barrier(2, timeout=2)
    results = []

    def task_a():
        barrier.wait()
        results.append('a')

    def task_b():
        barrier.wait()
        results.append('b')

    run_sites_parallel([('A', task_a), ('B', task_b)])
    assert sorted(results) == ['a', 'b']


def test_stdout_restored_after_parallel():
    orig = sys.stdout
    run_sites_parallel([('A', lambda: None), ('B', lambda: None)])
    assert sys.stdout is orig


# --- error propagation ---

def test_single_task_error_propagated():
    def fail():
        raise ValueError('boom')
    with pytest.raises(ValueError, match='boom'):
        run_sites_parallel([('X', fail)])


def test_multiple_tasks_all_error_raises_system_exit():
    def fail_a():
        raise ValueError('a')
    def fail_b():
        raise ValueError('b')
    with pytest.raises(SystemExit):
        run_sites_parallel([('A', fail_a), ('B', fail_b)])


# --- path: multiple tasks, TTY (rich) ---

def test_tty_path_uses_rich_live(monkeypatch):
    mock_out = MagicMock()
    mock_out.isatty.return_value = True
    monkeypatch.setattr(parallel, '_orig_stdout', mock_out)

    called = []
    with patch('rich.console.Console') as mock_console_cls, \
         patch('rich.live.Live') as mock_live_cls, \
         patch('rich.columns.Columns'), \
         patch('rich.panel.Panel'):

        run_sites_parallel([
            ('A', lambda: called.append('a')),
            ('B', lambda: called.append('b')),
        ])

    mock_console_cls.assert_called_once_with(file=mock_out, highlight=False)
    mock_live_cls.assert_called_once()
    live_kwargs = mock_live_cls.call_args.kwargs
    assert live_kwargs.get('redirect_stdout') is False
    assert live_kwargs.get('redirect_stderr') is False
    mock_live_cls.return_value.__enter__.assert_called_once()
    mock_live_cls.return_value.__enter__.return_value.update.assert_called()
    assert sorted(called) == ['a', 'b']


def test_tty_all_labels_adds_empty_panels(monkeypatch):
    mock_out = MagicMock()
    mock_out.isatty.return_value = True
    monkeypatch.setattr(parallel, '_orig_stdout', mock_out)

    panel_titles = []

    def mock_panel(content, title=None):
        panel_titles.append(title)
        return MagicMock()

    with patch('rich.console.Console'), \
         patch('rich.live.Live'), \
         patch('rich.columns.Columns'), \
         patch('rich.panel.Panel', side_effect=mock_panel):

        run_sites_parallel(
            [('B', lambda: None)],
            all_labels=['A', 'B', 'C'],
        )

    assert len(panel_titles) % 3 == 0 and panel_titles[:3] == ['A', 'B', 'C']
