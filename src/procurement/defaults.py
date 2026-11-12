import json
from pathlib import Path

from src.common.config import load_config
from src.common.paths import artifacts_dir


def generate_procurement_defaults() -> dict:
    cfg = load_config()
    proc_cfg = cfg.get("procurement", {})
    return {
        "tariff": {
            "da_price_inr_per_mwh": float(proc_cfg.get("da", 5000)),
            "under_price_inr_per_mwh": float(proc_cfg.get("under", 12000)),
            "resale_price_inr_per_mwh": float(proc_cfg.get("resale", 2500)),
        },
        "disclaimer": "Illustrative placeholder values, not actual DISCOM tariffs. See docs/ASSUMPTIONS.md.",
        "default_risk_quantile": 0.9,
    }


def write_procurement_defaults(out_dir: Path | None = None) -> Path:
    target_dir = out_dir if out_dir is not None else artifacts_dir()
    data = generate_procurement_defaults()
    out_path = target_dir / "procurement_defaults.json"
    target_dir.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return out_path


def main() -> None:
    write_procurement_defaults()


if __name__ == "__main__":
    main()
