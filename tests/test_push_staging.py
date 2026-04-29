import json
import pytest


def _details(push_env):
    return json.loads((push_env['worker'] / 'data' / 'details.json').read_text())


def test_push_without_images_flag(push_env, run_puppy):
    run_puppy('push')
    assert _details(push_env)['images'] is False


def test_push_with_images_flag(push_env, run_puppy):
    run_puppy('push', '-I')
    assert _details(push_env)['images'] is True
