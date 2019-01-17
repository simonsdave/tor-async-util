#!/usr/bin/env bash
#
# This script builds a docker image which packages up the
# development environment and associated tooling.
#

set -e

SCRIPT_DIR_NAME="$( cd "$( dirname "$0" )" && pwd )"

if [ $# != 1 ]; then
    echo "usage: $(basename "$0") <docker image name>" >&2
    exit 1
fi

DOCKER_IMAGE=${1:-}

CONTEXT_DIR=$(mktemp -d 2> /dev/null || mktemp -d -t DAS)
PROJECT_HOME_DIR="$SCRIPT_DIR_NAME/.."
cp "$PROJECT_HOME_DIR/requirements.txt" "$CONTEXT_DIR/."
cp "$PROJECT_HOME_DIR/setup.py" "$CONTEXT_DIR/."
mkdir "$CONTEXT_DIR/tor_async_util"
cp "$PROJECT_HOME_DIR/tor_async_util/__init__.py" "$CONTEXT_DIR/tor_async_util/."

DEV_ENV_VERSION=$(cat "$SCRIPT_DIR_NAME/dev-env-version.txt")
if [ "${DEV_ENV_VERSION:-}" == "master" ]; then
    DEV_ENV_VERSION=latest
fi

TEMP_DOCKERFILE=$CONTEXT_DIR/Dockerfile
cp "$SCRIPT_DIR_NAME/Dockerfile.template" "$TEMP_DOCKERFILE"
sed \
    -i \
    -e "s|%DEV_ENV_VERSION%|$DEV_ENV_VERSION|g" \
    "$TEMP_DOCKERFILE"

docker build \
    -t "$DOCKER_IMAGE" \
    --file "$TEMP_DOCKERFILE" \
    "$CONTEXT_DIR"

rm -rf "$CONTEXT_DIR"

exit 0
