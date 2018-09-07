#!/usr/bin/env bash

docker run --rm --volume ~/tor-async-util:/app simonsdave/tor-async-util-dev-env:latest nosetests --with-coverage --cover-branches --cover-erase --cover-package tor_async_util
exit $?
