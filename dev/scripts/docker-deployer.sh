docker run --rm \
    -v $(pwd):/build \
    -it \
    --user $(id -u):$(id -g) \
    -w /build \
    --entrypoint /bin/bash \
    docker-deployer:local
