PYTHON ?= python3
RULES ?= data/rules.json
TAXONOMY ?= data/taxonomy.json
KNOWLEDGE ?=
PORT ?= 8000
COUNT ?= 100
SEED ?= 42
REQUESTS ?= 1000
WORKERS ?= 1

DATA_ARGS = --rules "$(RULES)" --taxonomy "$(TAXONOMY)" $(if $(KNOWLEDGE),--knowledge "$(KNOWLEDGE)",)

.PHONY: serve predict evaluate audit review benchmark test

serve:
	$(PYTHON) -m support_copilot.server $(DATA_ARGS) --host 0.0.0.0 --port $(PORT)

predict:
	@test -n "$(IN)" || (echo 'Укажите IN=путь/к/tickets.jsonl' >&2; exit 2)
	@test -n "$(OUT)" || (echo 'Укажите OUT=путь/к/pred.jsonl' >&2; exit 2)
	$(PYTHON) -m support_copilot.batch $(DATA_ARGS) --in "$(IN)" --out "$(OUT)"

evaluate:
	@test -n "$(IN)" || (echo 'Укажите IN=путь/к/tickets_valid.jsonl' >&2; exit 2)
	$(PYTHON) -m support_copilot.evaluate $(DATA_ARGS) --in "$(IN)" $(if $(LABELS),--labels "$(LABELS)",) $(if $(REVIEWS),--reviews "$(REVIEWS)",)

audit:
	@test -n "$(IN)" || (echo 'Укажите IN=путь/к/приватным-обращениям' >&2; exit 2)
	$(PYTHON) -m support_copilot.audit $(DATA_ARGS) --in "$(IN)"

review:
	@test -n "$(IN)" || (echo 'Укажите IN=путь/к/tickets_valid.jsonl' >&2; exit 2)
	@test -n "$(OUT)" || (echo 'Укажите OUT=приватный-файл.jsonl' >&2; exit 2)
	$(PYTHON) -m support_copilot.review_pack $(DATA_ARGS) --in "$(IN)" --out "$(OUT)" --count $(COUNT) --seed $(SEED) $(if $(filter 1,$(BLIND)),--blind-labels,) $(if $(REVIEW_LANG),--language "$(REVIEW_LANG)",)

benchmark:
	@test -n "$(IN)" || (echo 'Укажите IN=путь/к/tickets_valid.jsonl' >&2; exit 2)
	$(PYTHON) -m support_copilot.benchmark $(DATA_ARGS) --in "$(IN)" --requests $(REQUESTS) --workers $(WORKERS)

test:
	$(PYTHON) -m unittest discover -s tests -v
