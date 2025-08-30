docker run --rm \
    -v $(pwd):/build \
    -v $(pwd)/../pipelines:/build/pipelines \
    -it \
    --user $(id -u):$(id -g) \
    -w /build \
    --entrypoint /bin/bash \
    docker-deployer:local
