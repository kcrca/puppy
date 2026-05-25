import pytest
from jinja2 import UndefinedError

from puppy.renderer import render


def test_unrecognized_variable_raises():
    with pytest.raises(UndefinedError, match='typo_var'):
        render('Hello {{ typo_var }}', {})


def test_circular_config_reference_raises():
    # a: 'prefix-{{ a }}' grows each iteration, never stabilizes
    with pytest.raises(SystemExit, match='circular'):
        render('{{ a }}', {'a': 'prefix-{{ a }}'})
