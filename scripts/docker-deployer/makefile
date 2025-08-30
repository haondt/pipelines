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
	@PYTHONPATH="${SCRIPT_DIR}:$$PYTHONPATH" \
		${PYTHON} -m docker-deployer.get_pruned_changes ${CHANGES} | yq


.PHONY: changed-containers
changed-containers:
	@[ -n "$(CHANGES)" ] || (echo "CHANGES is required"; exit 1)
	@[ -n "$(PROJECT)" ] || (echo "PROJECT is required"; exit 1)
	@cat ${CHANGES} | \
		PYTHONPATH="${SCRIPT_DIR}:$$PYTHONPATH" \
		${PYTHON} -m docker-deployer.get_containers ${PROJECT}

.PHONY: build
build:
	@[ -n "$(PROJECT)" ] || (echo "PROJECT is required"; exit 1)
	@[ -n "$(CHANGES)" ] || (echo "CHANGES is required"; exit 1)
		PYTHONPATH="${SCRIPT_DIR}:$$PYTHONPATH" \
		${PYTHON} -m docker-deployer.build ${CHANGES} ${PROJECT} 
