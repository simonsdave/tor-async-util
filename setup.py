#
# to build the distrubution @ tor_async_util-*.*.*.tar.gz
#
#   >git clone https://github.com/simonsdave/tor-async-util.git
#   >cd tor-async-util
#   >source cfg4dev
#   >python setup.py sdist --formats=gztar
#
import re

from setuptools import setup

#
# this approach used below to determine ```version``` was inspired by
# https://github.com/kennethreitz/requests/blob/master/setup.py#L31
#
# why this complexity? wanted version number to be available in the
# a runtime.
#
# the code below assumes the distribution is being built with the
# current directory being the directory in which setup.py is stored
# which should be totally fine 99.9% of the time. not going to add
# the coode complexity to deal with other scenarios
#
reg_ex_pattern = r"__version__\s*=\s*['\"](?P<version>[^'\"]*)['\"]"
reg_ex = re.compile(reg_ex_pattern)
version = ""
with open("tor_async_util/__init__.py", "r") as fd:
    for line in fd:
        match = reg_ex.match(line)
        if match:
            version = match.group("version")
            break
if not version:
    raise Exception("Can't locate tor_async_util's version number")

setup(
    name="tor_async_util",
    packages=[
        "tor_async_util",
    ],
    scripts=[
        "bin/tor_async_util_nosetests.py",
    ],
    install_requires=[
        "jsonschema>=2.5.0",
        "python-keyczar==0.716",
    ],
    version=version,
    include_package_data=True,
    description="Tornado Async Utilities",
    author="Dave Simons",
    author_email="simonsdave@gmail.com",
    url="https://github.com/simonsdave/tor-async-util"
)
