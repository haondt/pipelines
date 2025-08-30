PYTHON := python3

REPOSITORY := $(shell pwd)
SCRIPT_DIR := $(realpath $(dir $(firstword $(MAKEFILE_LIST)))/..)

.PHONY: validate-deployment-args
validate-deployment-args:
	$(foreach var,$(DEPLOYMENT_ARGS),$(if $(value $(var)),,$(error $(var) is required)))

.PHONY: render-template
render-template:
	@[ -n "$(TASK_INDEX)" ] || (echo "TASK_INDEX is required"; exit 1)
	@[ -n "$(TEMPLATE_NAME)" ] || (echo "TEMPLATE_NAME is required"; exit 1)
	@PYTHONPATH="${SCRIPT_DIR}:$$PYTHONPATH" \
		${PYTHON} -m hephaestus.render_template --templates ${SCRIPT_DIR}/../templates ${TASK_INDEX} ${TEMPLATE_NAME} $(EXTRA_ARGS)
