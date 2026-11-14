.PHONY: peak analysis api ui

peak:
	python -m src.peak.run_all

analysis:
	python -m src.analysis.error_decomposition
	python -m src.analysis.missed_peaks

api:
	python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

ui:
	cd ui && npm install && npm run dev -- --host --port 5173
