from functools import lru_cache
from typing import Any
import yaml
from src.common.paths import repo_root


@lru_cache(maxsize=1)
def load_config() -> dict[str, Any]:
    config_path = repo_root() / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    return data or {}
