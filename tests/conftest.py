import pytest
from src.common.paths import repo_root


@pytest.fixture
def artifact_dirs():
    mock_dir = repo_root() / "artifacts_mock"
    real_dir = repo_root() / "artifacts"
    dirs = [mock_dir]
    if real_dir.exists() and any(
        item for item in real_dir.iterdir() if item.is_file() and not item.name.startswith(".")
    ):
        dirs.append(real_dir)
    return dirs
