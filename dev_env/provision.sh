#!/usr/bin/env bash
#
# this script provisions the project's development environment
#

apt-get build-dep -y python-crypto
apt-get install -y libcurl4-openssl-dev
apt-get install -y libffi-dev
apt-get build-dep -y python-pycurl

exit 0
