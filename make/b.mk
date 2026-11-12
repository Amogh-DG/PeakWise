.PHONY: peak analysis api ui

peak:
	@echo not implemented yet

analysis:
	@echo not implemented yet

api:
	python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

ui:
	@echo not implemented yet
