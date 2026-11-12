.PHONY: mock data features backtest

mock:
	python -m scripts.make_mock_data
	python -m scripts.make_mock_artifacts

data:
	@echo not implemented yet

features:
	@echo not implemented yet

backtest:
	python -m src.backtest.runner
	python -m src.metrics.accuracy_table
