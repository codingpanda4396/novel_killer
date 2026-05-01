.PHONY: help check status init-config new-chapter context-pack run-stage run-full

help:
	@python3 scripts/novel_workflow.py --help

check:
	@python3 scripts/novel_workflow.py check

status:
	@python3 scripts/novel_workflow.py status

init-config:
	@python3 scripts/novel_workflow.py init-config

new-chapter:
	@if [ -z "$(N)" ] || [ -z "$(TITLE)" ]; then \
		echo 'Usage: make new-chapter N=31 TITLE=章节标题'; \
		exit 1; \
	fi
	@python3 scripts/novel_workflow.py new-chapter "$(N)" "$(TITLE)"

context-pack:
	@if [ -z "$(N)" ]; then \
		echo 'Usage: make context-pack N=31'; \
		exit 1; \
	fi
	@python3 scripts/novel_workflow.py context-pack "$(N)"

run-stage:
	@if [ -z "$(STAGE)" ]; then \
		echo 'Usage: make run-stage STAGE=draft N=31 TITLE=章节标题'; \
		exit 1; \
	fi
	@python3 scripts/novel_workflow.py run-stage "$(STAGE)" $(if $(N),--number "$(N)") $(if $(TITLE),--title "$(TITLE)")

run-full:
	@if [ -z "$(N)" ] || [ -z "$(TITLE)" ]; then \
		echo 'Usage: make run-full N=31 TITLE=章节标题'; \
		exit 1; \
	fi
	@python3 scripts/novel_workflow.py run-full --number "$(N)" --title "$(TITLE)"
