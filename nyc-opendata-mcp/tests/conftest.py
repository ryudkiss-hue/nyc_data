"""Live tests: every test reads the real NYC Open Data and DOT ArcGIS services. Nothing is mocked.

Parity tests compare against the make-safe-batch skill's own msb.py. It is not published in this repository; point
MSB_REFERENCE at a local copy (the skill's assets/msb.py) to run them. Its AST fingerprint is checked first."""
import ast
import hashlib
import importlib.util
import os
import sys
import tempfile

import pytest

HERE = os.path.dirname(__file__)
MSB_FINGERPRINT = '32b7fd0c267a2749afb3df866a4e89e4'

# separate caches so the two implementations never share an answer
os.environ.setdefault('NYCOD_CACHE', tempfile.mkdtemp(prefix='nycod_test_'))
os.environ['MSB_CACHE'] = tempfile.mkdtemp(prefix='msb_test_')
sys.path.insert(0, os.path.join(HERE, '..', 'src'))


def _fingerprint(path):
    t = ast.parse(open(path, encoding='utf-8').read())
    for n in ast.walk(t):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)) and n.body and isinstance(n.body[0], ast.Expr) \
                and isinstance(n.body[0].value, ast.Constant) and isinstance(n.body[0].value.value, str):
            n.body = n.body[1:] or [ast.Pass()]
    return hashlib.md5(ast.dump(t).encode()).hexdigest()


@pytest.fixture(scope='session')
def msb():
    path = os.environ.get('MSB_REFERENCE', '')
    if not path or not os.path.exists(path):
        pytest.skip('MSB_REFERENCE not set: parity tests need a local copy of the skill\'s msb.py')
    assert _fingerprint(path) == MSB_FINGERPRINT, f'{path} is not the skill copy (fingerprint differs)'
    spec = importlib.util.spec_from_file_location('msb_reference', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
