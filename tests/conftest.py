import lightgbm
import pytest

import src.models
from src.common.paths import repo_root


@pytest.fixture
def artifact_dirs():
    mock_dir = repo_root() / "artifacts_mock"
    real_dir = repo_root() / "artifacts"
    dirs = [mock_dir]
    if real_dir.exists() and (real_dir / "meta.json").exists():
        dirs.append(real_dir)
    return dirs
