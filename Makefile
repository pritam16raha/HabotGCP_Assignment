# Author: Pritam Raha <rahapritam32@gmail.com>
SHELL := /bin/bash
.DEFAULT_GOAL := validate

.PHONY: install install-artifacts format lint test audit contracts terraform policy demo-fail-closed demo-data-validation generate-cloud-test-events artifacts validate

install:
	python3 -m venv .venv
	.venv/bin/python -m pip install --upgrade pip
	.venv/bin/python -m pip install -r requirements-dev.txt

install-artifacts:
	.venv/bin/python -m pip install -r requirements-artifacts.txt

format:
	.venv/bin/ruff format .
	terraform fmt -recursive infrastructure

lint:
	.venv/bin/ruff format --check .
	.venv/bin/ruff check .
	.venv/bin/bandit -c pyproject.toml -r backend scripts
	.venv/bin/python backend/manage.py check --deploy --fail-level WARNING

test:
	.venv/bin/python backend/manage.py test onboarding.tests --verbosity 2
	.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v

audit:
	.venv/bin/pip-audit --strict --requirement requirements.txt

contracts:
	.venv/bin/python scripts/validate_contracts.py
	.venv/bin/python scripts/detect_secrets.py --output build/reports/secret-scan.json

terraform:
	terraform -chdir=infrastructure fmt -check -recursive
	terraform -chdir=infrastructure init -backend=false
	terraform -chdir=infrastructure validate
	terraform -chdir=infrastructure test

policy:
	.venv/bin/checkov --config-file .checkov.yml --output cli

demo-fail-closed:
	.venv/bin/python scripts/demo_fail_closed.py

demo-data-validation:
	.venv/bin/python scripts/manual_serializer_demo.py

generate-cloud-test-events:
	@test -n "$(RAW_BUCKET)" || (echo "Set RAW_BUCKET to the deployed bucket name." && exit 2)
	.venv/bin/python scripts/generate_cloud_test_events.py --bucket "$(RAW_BUCKET)"

artifacts:
	.venv/bin/python scripts/build_submission_artifacts.py

validate: lint test audit contracts terraform policy demo-fail-closed
