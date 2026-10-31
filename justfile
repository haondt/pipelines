python := "python3"
script_dir := justfile_directory() / "scripts"

build-dockers:
    docker build -t docker-deployer:local ./images/docker-deployer
    docker build -t hephaestus:local ./images/hephaestus
    docker build -t docs-builder:local ./images/docs-builder

clean:
    docker rmi docker-deployer:local || true

generate:
    ROOT_PIPELINE_SOURCE="$CI_PIPELINE_SOURCE" \
        PYTHONPATH="{{script_dir}}:$PYTHONPATH" \
        {{python}} -m hephaestus.generate --templates pipelines/templates -f pipeline.yml > generated_pipeline.yml
