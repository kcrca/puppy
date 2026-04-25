import pytest
from jinja2 import UndefinedError

from puppy.renderer import render


def test_unrecognized_variable_raises():
    with pytest.raises(UndefinedError, match='typo_var'):
        render('Hello {{ typo_var }}', {})
