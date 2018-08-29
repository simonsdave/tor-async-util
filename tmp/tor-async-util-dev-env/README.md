```bash
(env) ~/tor-async-util/tmp/tor-async-util-dev-env> docker run --rm -it simonsdave/tor-async-util-dev-env:latest bash
root@0953a6d39c66:/app# echo 'hello'
hello
root@0953a6d39c66:/app# exit
exit
(env) ~/tor-async-util/tmp/tor-async-util-dev-env>
```

```bash
docker run --rm --volume ~/tor-async-util:/app simonsdave/tor-async-util-dev-env:latest nosetests --with-coverage --cover-branches --cover-erase --cover-package tor_async_util
Coverage.py warning: --include is ignored because --source is set (include-ignored)
................................................................EEE................
======================================================================
ERROR: test_happy_path (tor_async_util.tests.unit_tests.IsLibCurlCompiledWithAsyncDNSResolverTestCase)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/tor_async_util/tests/unit_tests.py", line 49, in setUp
    self.assertTrue("pycurl" not in sys.modules)
AssertionError: False is not true

======================================================================
ERROR: test_happy_version_info_array_does_not_contain_features (tor_async_util.tests.unit_tests.IsLibCurlCompiledWithAsyncDNSResolverTestCase)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/tor_async_util/tests/unit_tests.py", line 49, in setUp
    self.assertTrue("pycurl" not in sys.modules)
AssertionError: False is not true

======================================================================
ERROR: test_pycurl_import_not_available (tor_async_util.tests.unit_tests.IsLibCurlCompiledWithAsyncDNSResolverTestCase)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/tor_async_util/tests/unit_tests.py", line 49, in setUp
    self.assertTrue("pycurl" not in sys.modules)
AssertionError: False is not true

Name                            Stmts   Miss Branch BrPart  Cover
-----------------------------------------------------------------
tor_async_util/__init__.py        345     12     74      0    97%
tor_async_util/jsonschemas.py       9      0      0      0   100%
-----------------------------------------------------------------
TOTAL                             354     12     74      0    97%
----------------------------------------------------------------------
Ran 83 tests in 1.066s

FAILED (errors=3)
```
