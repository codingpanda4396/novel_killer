.PHONY: help check status review-chapter review-range publish-check plan-next generate scout test

PROJECT ?= life_balance

help:
	@python3 -m novelops.cli --help

check:
	@python3 -m novelops.cli --project "$(PROJECT)" check
	@python3 -m unittest discover -s tests

status:
	@python3 -m novelops.cli --project "$(PROJECT)" status

review-chapter:
	@if [ -z "$(CH)" ]; then \
		echo 'Usage: make review-chapter PROJECT=life_balance CH=1'; \
		exit 1; \
	fi
	@python3 -m novelops.cli --project "$(PROJECT)" review-chapter "$(CH)"

review-range:
	@if [ -z "$(START)" ] || [ -z "$(END)" ]; then \
		echo 'Usage: make review-range PROJECT=life_balance START=1 END=50'; \
		exit 1; \
	fi
	@python3 -m novelops.cli --project "$(PROJECT)" review-range "$(START)" "$(END)"

publish-check:
	@if [ -z "$(START)" ] || [ -z "$(END)" ]; then \
		echo 'Usage: make publish-check PROJECT=life_balance START=1 END=50'; \
		exit 1; \
	fi
	@python3 -m novelops.cli --project "$(PROJECT)" publish-check "$(START)" "$(END)"

plan-next:
	@if [ -z "$(CH)" ]; then \
		echo 'Usage: make plan-next PROJECT=life_balance CH=51'; \
		exit 1; \
	fi
	@python3 -m novelops.cli --project "$(PROJECT)" plan-next "$(CH)"

generate:
	@if [ -z "$(CH)" ]; then \
		echo 'Usage: make generate PROJECT=life_balance CH=51'; \
		exit 1; \
	fi
	@if [ "$(NO_LLM)" = "1" ]; then \
		python3 -m novelops.cli --project "$(PROJECT)" generate "$(CH)" --no-llm; \
	else \
		python3 -m novelops.cli --project "$(PROJECT)" generate "$(CH)"; \
	fi

scout:
	@python3 -m novelops.cli --project "$(PROJECT)" scout

test:
	@python3 -m unittest discover -s tests
