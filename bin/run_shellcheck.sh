#!/usr/bin/env bash

set -e

VERBOSE=0

while true
do
    case "${1,,}" in
        -v)
            shift
            VERBOSE=1
            ;;
        *)
            break
            ;;
    esac
done

if [ $# != 0 ]; then
    echo "usage: $(basename "$0") [-v]" >&2
    exit 1
fi

find . -name \*.sh | grep -v ./env | while IFS='' read -r FILENAME
do
    if [ "1" -eq "${VERBOSE:-0}" ]; then
        echo "$FILENAME"
    fi
    docker run -v "$PWD:/mnt" koalaman/shellcheck:latest "$FILENAME"
done

exit 0
