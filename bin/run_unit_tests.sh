#!/usr/bin/env bash

set -e
set -x

if [ $# != 0 ]; then
    echo "usage: $(basename "$0")" >&2
    exit 1
fi

USER=$(stat -c "%u" "$0")
GROUP=$(stat -c "%g" "$0")

docker run --rm --volume ~/tor-async-util:/app simonsdave/tor-async-util-dev-env:latest run_unit_tests.sh "$USER" "$GROUP"

exit 0
