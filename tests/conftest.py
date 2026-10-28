import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gateway import config, store  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path):
    """Each test gets its own data dir, so the SQLite file and secret key are fresh."""
    config.override(config.Settings(data_dir=tmp_path / "data", rate_limit_per_min=1000, demo_seed=True))
    store.reset_cache()
    yield config.get_settings()
    config.override(None)
    store.reset_cache()
