PYTHON := python3
SCRIPT_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))/scripts

build-dockers:
	docker build -t docker-deployer:local ./images/docker-deployer
	docker build -t hephaestus:local ./images/hephaestus

clean:
	docker rmi docker-deployer:local || true

generate:
	ROOT_PIPELINE_SOURCE=$$CI_PIPELINE_SOURCE \
		PYTHONPATH="${SCRIPT_DIR}:$$PYTHONPATH" \
		${PYTHON} -m hephaestus.generate --templates pipelines/templates  -f pipeline.yml  > "generated_pipeline.yml"
