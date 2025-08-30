docker run --rm \
    -v $(pwd):/build \
    -v $(pwd)/../pipelines:/build/pipelines \
    -it \
    --user $(id -u):$(id -g) \
    -w /build \
    --entrypoint /bin/bash \
    -e GITLAB_CR_REGISTRY=registry.gitlab.com/haondt/cicd/registry \
    -e DOCKER_HUB_REPOSITORY=haumea \
    -e CI_COMMIT_BRANCH=main \
    -e ROOT_PIPELINE_SOURCE=push \
    -e CI_PIPELINE_SOURCE=push \
    -e CI_COMMIT_SHORT_SHA=6a47b57f \
    -e DEFAULT_ARTIFACT_EXPIRY="1 day" \
    hephaestus:local
