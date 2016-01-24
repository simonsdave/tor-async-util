#!/usr/bin/env python
"""Integration tests often run database installer(s),
start up service(s) and then direct various requests at the
service(s). When the tests fail it's very useful to output the
logs associated with the installers and services. The nose
plug-in nose_plugins.FileCapture is used in integration tests
to identify the files that should be displayed on test failure.
In order for nose_plugins.FileCapture to work as desired it must be
registered prior to running tests. This script is responsible
for registering the plug-in. This script is used as a replacement
for ```nosetests``` as per the instructions documented in
http://nose.readthedocs.org/en/latest/api/core.html#nose.core.TestProgram
"""

import nose

from tor_async_util import nose_plugins

if __name__ == '__main__':
    nose.main(addplugins=[nose_plugins.FileCapture()])
