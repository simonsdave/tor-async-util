FROM simonsdave/dev-env:latest

MAINTAINER Dave Simons

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get install -y build-essential
RUN apt-get install -y libffi-dev
RUN apt-get install -y python-crypto
RUN apt-get install -y libcurl4-openssl-dev
RUN apt-get install -y python-pycurl

COPY requirements.txt /tmp/requirements.txt
COPY setup.py /tmp/setup.py
RUN mkdir /tmp/tor_async_util
COPY tor_async_util/__init__.py /tmp/tor_async_util/__init__.py
RUN mkdir /tmp/bin
COPY bin/tor_async_util_nosetests.py /tmp/bin/tor_async_util_nosetests.py

RUN cd /tmp && pip install --requirement "/tmp/requirements.txt"

ENV DEBIAN_FRONTEND newt
