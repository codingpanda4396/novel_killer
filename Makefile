.PHONY: help init-project index serve check status review-chapter review-range publish-check plan-next generate scout test

PROJECT ?= life_balance
PYTHON = python3.10

help:
	@$(PYTHON) -m novelops.cli --help

init-project:
	@if [ -z "$(ID)" ] || [ -z "$(NAME)" ] || [ -z "$(GENRE)" ]; then \
		echo 'Usage: make init-project ID=demo NAME=测试 GENRE=仙侠升级流'; \
		exit 1; \
	fi
	@$(PYTHON) -m novelops.cli init-project "$(ID)" --name "$(NAME)" --genre "$(GENRE)"

index:
	@$(PYTHON) -m novelops.cli index --project "$(PROJECT)"

serve:
	@$(PYTHON) -m novelops.cli serve

check:
	@$(PYTHON) -m novelops.cli --project "$(PROJECT)" check
	@$(PYTHON) -m unittest discover -s tests

status:
	@$(PYTHON) -m novelops.cli --project "$(PROJECT)" status

review-chapter:
	@if [ -z "$(CH)" ]; then \
		echo 'Usage: make review-chapter PROJECT=life_balance CH=1'; \
		exit 1; \
	fi
	@$(PYTHON) -m novelops.cli --project "$(PROJECT)" review-chapter "$(CH)"

review-range:
	@if [ -z "$(START)" ] || [ -z "$(END)" ]; then \
		echo 'Usage: make review-range PROJECT=life_balance START=1 END=50'; \
		exit 1; \
	fi
	@$(PYTHON) -m novelops.cli --project "$(PROJECT)" review-range "$(START)" "$(END)"

publish-check:
	@if [ -z "$(START)" ] || [ -z "$(END)" ]; then \
		echo 'Usage: make publish-check PROJECT=life_balance START=1 END=50'; \
		exit 1; \
	fi
	@$(PYTHON) -m novelops.cli --project "$(PROJECT)" publish-check "$(START)" "$(END)"

plan-next:
	@if [ -z "$(CH)" ]; then \
		echo 'Usage: make plan-next PROJECT=life_balance CH=51'; \
		exit 1; \
	fi
	@$(PYTHON) -m novelops.cli --project "$(PROJECT)" plan-next "$(CH)"

generate:
	@if [ -z "$(CH)" ]; then \
		echo 'Usage: make generate PROJECT=life_balance CH=51'; \
		exit 1; \
	fi
	@if [ "$(NO_LLM)" = "1" ]; then \
		$(PYTHON) -m novelops.cli --project "$(PROJECT)" generate "$(CH)" --no-llm; \
	else \
		$(PYTHON) -m novelops.cli --project "$(PROJECT)" generate "$(CH)"; \
	fi

scout:
	@$(PYTHON) -m novelops.cli --project "$(PROJECT)" scout

test:
	@$(PYTHON) -m unittest discover -s tests
