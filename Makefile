PYTHON ?= python3
RULES ?= data/rules.json
TAXONOMY ?= data/taxonomy.json
KNOWLEDGE ?=
PORT ?= 8000

DATA_ARGS = --rules "$(RULES)" --taxonomy "$(TAXONOMY)" $(if $(KNOWLEDGE),--knowledge "$(KNOWLEDGE)",)

.PHONY: serve predict evaluate test

serve:
	$(PYTHON) -m support_copilot.server $(DATA_ARGS) --host 0.0.0.0 --port $(PORT)

predict:
	@test -n "$(IN)" || (echo 'Укажите IN=путь/к/tickets.jsonl' >&2; exit 2)
	@test -n "$(OUT)" || (echo 'Укажите OUT=путь/к/pred.jsonl' >&2; exit 2)
	$(PYTHON) -m support_copilot.batch $(DATA_ARGS) --in "$(IN)" --out "$(OUT)"

evaluate:
	@test -n "$(IN)" || (echo 'Укажите IN=путь/к/tickets_valid.jsonl' >&2; exit 2)
	$(PYTHON) -m support_copilot.evaluate $(DATA_ARGS) --in "$(IN)"

test:
	$(PYTHON) -m unittest discover -s tests -v
