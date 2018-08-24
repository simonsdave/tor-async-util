FROM simonsdave/dev-env:latest

MAINTAINER Dave Simons

ENV DEBIAN_FRONTEND noninteractive

RUN pip --version
RUN pip install -U pip
RUN pip --version
RUN apt-get build-dep -y python-crypto
# RUN apt-get install -y libcurl4-openssl-dev
# RUN apt-get install -y libffi-dev
# RUN apt-get build-dep -y python-pycurl

ENV DEBIAN_FRONTEND newt
