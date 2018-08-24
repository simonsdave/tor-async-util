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

TAG=latest
IMAGE_NAME="simonsdave/dev-env:$TAG"

docker build -t "$IMAGE_NAME" "$SCRIPT_DIR_NAME/."

exit 0
