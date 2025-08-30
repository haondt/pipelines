PYTHON := python3

REPOSITORY := $(shell pwd)
SCRIPT_DIR := $(realpath $(dir $(firstword $(MAKEFILE_LIST)))/..)

DEPLOYMENT_ARGS := PROJECT SERVICE
BUILD_ARGS := 

.PHONY: validate-deployment-args
validate-deployment-args:
	$(foreach var,$(DEPLOYMENT_ARGS),$(if $(value $(var)),,$(error $(var) is required)))

.PHONY: changes
changes:
	@PYTHONPATH="${SCRIPT_DIR}:$$PYTHONPATH" \
		${PYTHON} -m docker-deployer.get_changes ${REPOSITORY}

.PHONY: pruned-changes
pruned-changes:
	@[ -n "$(CHANGES)" ] || (echo "CHANGES is required"; exit 1)
	@cat ${CHANGES} | yq 'del(.. | select(has("status") and .status == "unchanged"))'

.PHONY: build
build: validate-deployment-args
	@echo "Building ${PROJECT}/${SERVICE}"

.PHONY: deploy
deploy: validate-deployment-args
	@echo "Deploying ${PROJECT}/${SERVICE}"

