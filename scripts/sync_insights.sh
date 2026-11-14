#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="${ROOT_DIR}/ui/public/insights"

mkdir -p "${TARGET_DIR}"

if [ -f "${ROOT_DIR}/docs/WHY_PEAKS_ARE_HARD.md" ]; then
  cp "${ROOT_DIR}/docs/WHY_PEAKS_ARE_HARD.md" "${TARGET_DIR}/"
fi

if [ -f "${ROOT_DIR}/docs/MODEL_CARD.md" ]; then
  cp "${ROOT_DIR}/docs/MODEL_CARD.md" "${TARGET_DIR}/"
fi

mkdir -p "${ROOT_DIR}/docs/figures"
cp "${ROOT_DIR}"/docs/figures/*.png "${TARGET_DIR}/" 2>/dev/null || true

exit 0
