.PHONY: mock data features backtest

mock:
	python -m scripts.make_mock_data
	python -m scripts.make_mock_artifacts

data:
	python -m src.data.ingest_load
	python -m src.data.ingest_weather
	python -m src.data.clean

features:
	@echo not implemented yet

backtest:
	@echo not implemented yet
