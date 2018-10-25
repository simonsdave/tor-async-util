#
# to build the distrubution @ tor_async_util-*.*.*.tar.gz
#
#   >git clone https://github.com/simonsdave/tor-async-util.git
#   >cd tor-async-util
#   >source cfg4dev
#   >python setup.py bdist_wheel sdist --formats=gztar
#
# update pypitest with both meta data and source distribution (FYI ...
# use of pandoc is as per https://github.com/pypa/pypi-legacy/issues/148#issuecomment-226939424
# since PyPI requires long description in RST but the repo's readme is in
# markdown)
#
#   >pandoc README.md -o README.rst
#   >twine upload dist/* -r testpypi
#
# you will be able to find the packaage at
#
#   https://test.pypi.org/project/tor-async-util
#
# use the package uploaded to pypitest
#
#   >pip install -i https://testpypi.python.org/pypi tor-async-util
#
import re
from setuptools import setup

#
# this approach used below to determine ```version``` was inspired by
# https://github.com/kennethreitz/requests/blob/master/setup.py#L31
#
# why the complexity? wanted a single spot for the version number
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


def _long_description():
    try:
        with open('README.rst', 'r') as f:
            return f.read()
    except IOError:
        # simple fix to avoid failure on 'source cfg4dev'
        return "a long description"


_author = "Dave Simons"
_author_email = "simonsdave@gmail.com"


_keywords = [
    'tornado',
]


# list of valid classifiers @ https://pypi.python.org/pypi?%3Aaction=list_classifiers
_classifiers = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "Natural Language :: English",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Python :: Implementation :: CPython",
    "Topic :: Software Development :: Libraries :: Python Modules",
]


setup(
    name="tor_async_util",
    packages=[
        "tor_async_util",
    ],
    install_requires=[
        "jsonschema>=2.5.0",
        "python-keyczar==0.716",
        "pycurl>=7.43",
    ],
    include_package_data=True,
    version=version,
    description="Tornado Async Utilities",
    long_description=_long_description(),
    author=_author,
    author_email=_author_email,
    maintainer=_author,
    maintainer_email=_author_email,
    license="MIT",
    url="https://github.com/simonsdave/tor-async-util",
    download_url="https://github.com/simonsdave/tor-async-util/tarball/v%s" % version,
    keywords=_keywords,
    classifiers=_classifiers,
)
