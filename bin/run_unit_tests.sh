#!/usr/bin/env bash

set -e

SCRIPT_DIR_NAME="$( cd "$( dirname "$0" )" && pwd )"

if [ $# != 0 ]; then
    echo "usage: $(basename "$0")" >&2
    exit 1
fi

USER=$(stat -c "%u" "$0")
GROUP=$(stat -c "%g" "$0")

docker run --rm --volume "$SCRIPT_DIR_NAME/..:/app" simonsdave/tor-async-util-dev-env:latest run_unit_tests.sh "$USER" "$GROUP"

exit 0
