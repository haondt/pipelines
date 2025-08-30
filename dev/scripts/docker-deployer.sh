SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
PIPELINES_DIR="$SCRIPT_DIR/../.."

docker run --rm \
    -v $(pwd):/build \
    -v "$PIPELINES_DIR":/build/pipelines \
    -it \
    --user $(id -u):$(id -g) \
    -w /build \
    --env-file="$ENV_FILE" \
    --entrypoint /bin/bash \
    docker-deployer:local
