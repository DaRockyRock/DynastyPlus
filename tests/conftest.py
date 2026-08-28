"""Test bootstrap: make `backend` importable and isolate the data dir.

Set CFBMOD_DATA_DIR to a throwaway location before any backend import so tests
never touch real dynasty saves or editor settings.
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))  # tests dir for helper modules
os.environ.setdefault("CFBMOD_DATA_DIR", tempfile.mkdtemp(prefix="cfb_test_"))


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "slow: end-to-end tests that drive a real save (need a fixture)")
