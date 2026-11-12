.PHONY: peak analysis api ui

peak:
	python -m src.peak.classifier

analysis:
	python -m src.analysis.error_decomposition
	python -m src.analysis.missed_peaks

api:
	python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

ui:
	@echo not implemented yet
