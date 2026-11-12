.PHONY: peak analysis api ui

peak:
	@echo not implemented yet

analysis:
	python -m src.analysis.error_decomposition

api:
	python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

ui:
	cd ui && npm install && npm run dev -- --host --port 5173
