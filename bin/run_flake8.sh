#!/usr/bin/env bash

set -e

if [ $# != 0 ]; then
    echo "usage: $(basename "$0")" >&2
    exit 1
fi

docker run --rm --volume ~/tor-async-util:/app simonsdave/tor-async-util-dev-env:latest flake8

exit 0
