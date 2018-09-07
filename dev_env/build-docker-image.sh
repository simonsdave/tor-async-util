#!/usr/bin/env bash
#
# This script ...
#

set -e

SCRIPT_DIR_NAME="$( cd "$( dirname "$0" )" && pwd )"

if [ $# != 0 ]; then
    echo "usage: $(basename "$0")" >&2
    exit 1
fi

CONTEXT_DIR=$(mktemp -d 2> /dev/null || mktemp -d -t DAS)
PROJECT_HOME_DIR="$SCRIPT_DIR_NAME/.."
cp "$PROJECT_HOME_DIR/requirements.txt" "$CONTEXT_DIR/."
cp "$PROJECT_HOME_DIR/setup.py" "$CONTEXT_DIR/."
mkdir "$CONTEXT_DIR/tor_async_util"
cp "$PROJECT_HOME_DIR/tor_async_util/__init__.py" "$CONTEXT_DIR/tor_async_util/."

TAG=latest
IMAGE_NAME="simonsdave/tor-async-util-dev-env:$TAG"

docker build \
    -t "$IMAGE_NAME" \
    --file "$SCRIPT_DIR_NAME/Dockerfile" \
    "$CONTEXT_DIR"

rm -rf "$CONTEXT_DIR"

exit 0
