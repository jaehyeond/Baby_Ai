"""Catch the clean-PC dependency leak masked by the large research venv."""
import subprocess
import sys
from pathlib import Path


def test_baby_api_import_does_not_require_claude_agent_sdk_or_torch():
    code = """
import sys, importlib.abc
class BlockLegacy(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'claude_agent_sdk', 'torch'}:
            raise ModuleNotFoundError(fullname)
sys.meta_path.insert(0, BlockLegacy())
import neural.baby.api_server
from neural import NeuralLayer
assert NeuralLayer.__name__ == 'NeuralLayer'
assert 'neural.substrate' not in sys.modules
print('ISOLATED_BABY_IMPORT_OK')
"""
    result = subprocess.run([sys.executable, "-B", "-c", code],
                            cwd=Path(__file__).resolve().parents[1],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert "ISOLATED_BABY_IMPORT_OK" in result.stdout
