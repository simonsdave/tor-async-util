#!/usr/bin/env bash

docker run --rm --volume ~/tor-async-util:/app simonsdave/tor-async-util-dev-env:latest flake8
exit $?
