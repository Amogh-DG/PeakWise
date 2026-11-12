include make/a.mk
include make/b.mk

.PHONY: test all

test:
	python -m pytest -q

all: data features backtest peak analysis
