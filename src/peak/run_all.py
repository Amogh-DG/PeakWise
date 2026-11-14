from __future__ import annotations

from src.peak.classifier import main as run_classifier
from src.peak.peak_hour import main as run_peak_hour
from src.peak.meta import main as run_meta


def main() -> None:
    print("Running peak event classifier...")
    run_classifier()
    print("Running peak hour and error metrics...")
    run_peak_hour()
    print("Running meta generation...")
    run_meta()
    print("Peak pipeline completed successfully.")


if __name__ == "__main__":
    main()
