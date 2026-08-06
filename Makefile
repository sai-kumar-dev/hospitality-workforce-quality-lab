PYTHON ?= python
UV ?= uv
NPM ?= npm
COMPOSE ?= docker compose
ARTIFACTS_DIR ?= artifacts

.PHONY: setup app-up app-down app-reset lint format typecheck test-unit test-api
.PHONY: test-contract test-smoke test-ui test-e2e test-accessibility test-reliability
.PHONY: test-all test-cross-browser perf-smoke report clean quality docker-config

setup:
	$(UV) sync --locked
	$(NPM) --prefix apps/web ci
	$(UV) run playwright install chromium

app-up:
	$(COMPOSE) up -d --build
	$(UV) run python scripts/wait_for_stack.py

app-down:
	$(COMPOSE) down --remove-orphans

app-reset:
	$(COMPOSE) run --rm api shiftbridge-seed --reset

format:
	$(UV) run ruff format .
	$(UV) run ruff check --fix .
	$(NPM) --prefix apps/web run format

lint:
	$(UV) run ruff format --check .
	$(UV) run ruff check .
	$(NPM) --prefix apps/web run format:check
	$(NPM) --prefix apps/web run lint

typecheck:
	$(UV) run mypy --strict apps/api/src qa/src
	$(NPM) --prefix apps/web run typecheck

test-unit:
	$(UV) run pytest apps/api/tests qa/tests/unit -m unit \
		--cov=shiftbridge_api --cov=shiftbridge_qa --cov-branch \
		--cov-report=term-missing --cov-report=xml --cov-report=html
	$(NPM) --prefix apps/web run test

test-api:
	$(UV) run pytest qa/tests/api -m api --junitxml=$(ARTIFACTS_DIR)/junit/api.xml

test-contract:
	SCHEMATHESIS_PROFILE=ci $(UV) run pytest qa/tests/contract -m contract \
		--junitxml=$(ARTIFACTS_DIR)/junit/contract.xml

test-smoke:
	$(UV) run pytest qa/tests/ui -m smoke --browser chromium \
		--tracing retain-on-failure --video retain-on-failure \
		--screenshot only-on-failure \
		--junitxml=$(ARTIFACTS_DIR)/junit/ui-smoke.xml \
		--html=$(ARTIFACTS_DIR)/pytest/ui-smoke.html --self-contained-html

test-ui:
	$(UV) run pytest qa/tests/ui -m ui --browser chromium \
		--tracing retain-on-failure --video retain-on-failure \
		--screenshot only-on-failure

test-e2e:
	$(UV) run pytest qa/tests/e2e -m e2e --browser chromium \
		--tracing retain-on-failure --video retain-on-failure \
		--screenshot only-on-failure

test-accessibility:
	$(UV) run pytest qa/tests/accessibility -m accessibility --browser chromium

test-reliability:
	$(UV) run pytest qa/tests/reliability -m reliability --browser chromium

test-all: lint typecheck test-unit test-api test-contract test-ui test-e2e test-accessibility test-reliability

test-cross-browser:
	$(UV) run pytest qa/tests/ui -m smoke \
		--browser chromium --browser firefox --browser webkit \
		--tracing retain-on-failure --screenshot only-on-failure

perf-smoke:
	$(UV) run locust -f qa/performance/locustfile.py --headless \
		--host http://localhost:8000 --users 5 --spawn-rate 2 --run-time 30s \
		--csv $(ARTIFACTS_DIR)/performance/locust \
		--html $(ARTIFACTS_DIR)/performance/report.html
	$(UV) run shiftbridge-performance-thresholds \
		--stats $(ARTIFACTS_DIR)/performance/locust_stats.csv

report:
	$(UV) run shiftbridge-triage \
		--junit $(ARTIFACTS_DIR)/junit \
		--console $(ARTIFACTS_DIR)/browser \
		--http $(ARTIFACTS_DIR)/http \
		--output $(ARTIFACTS_DIR)/triage

docker-config:
	$(COMPOSE) config

quality: lint typecheck test-unit

clean:
	$(PYTHON) scripts/clean.py

