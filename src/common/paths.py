import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def repo_root() -> Path:
    return REPO_ROOT


def is_mock() -> bool:
    return os.getenv("MOCK") == "1"


def artifacts_dir() -> Path:
    env_dir = os.getenv("ARTIFACTS_DIR")
    if env_dir:
        path = Path(env_dir)
        return path.resolve() if path.is_absolute() else (REPO_ROOT / path).resolve()
    target = "artifacts_mock" if is_mock() else "artifacts"
    return (REPO_ROOT / target).resolve()


def processed_dir() -> Path:
    target = "data/processed_mock" if is_mock() else "data/processed"
    return (REPO_ROOT / target).resolve()


def raw_dir() -> Path:
    return (REPO_ROOT / "data/raw").resolve()


def external_dir() -> Path:
    return (REPO_ROOT / "data/external").resolve()
