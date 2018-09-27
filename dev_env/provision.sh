#!/usr/bin/env bash
#
# this script provisions the project's development environment
#

SCRIPT_DIR_NAME="$( cd "$( dirname "$0" )" && pwd )"

apt-get build-dep -y python-crypto
apt-get install -y libcurl4-openssl-dev
apt-get install -y libffi-dev
apt-get build-dep -y python-pycurl

"$SCRIPT_DIR_NAME/build-docker-image.sh"

exit 0
