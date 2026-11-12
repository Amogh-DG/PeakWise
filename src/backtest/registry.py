from typing import Any

REGISTRY: dict[str, type] = {}


def register(name: str):
    def decorator(cls: type) -> type:
        REGISTRY[name] = cls
        return cls

    return decorator


def get_forecaster(name: str, cfg: dict[str, Any]):
    if name not in REGISTRY:
        raise ValueError(f"Unknown forecaster: {name}")
    return REGISTRY[name](cfg)
