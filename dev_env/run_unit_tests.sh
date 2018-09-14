#!/usr/bin/env bash

set -e
set -x

if [ $# != 2 ]; then
    echo "usage: $(basename "$0") <user> <group>" >&2
    exit 1
fi

USER=${1:-}
GROUP=${2:-}

nosetests \
    --with-coverage \
    --cover-erase \
    --cover-branches \
    --cover-package=tor_async_util

chown "$USER.$GROUP" /app/.coverage

exit 0
