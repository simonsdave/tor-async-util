"""This module contains unit testings for __init__.py."""

import unittest
import sys

import mock

import tor_async_util


class MockPycurlInstaller(object):

    def __init__(self, ut, version_info_return_value):
        object.__init__(self)

        pycurl_mock = mock.Mock()
        pycurl_mock.version_info.return_value = version_info_return_value
        self._pycurl_patch = mock.patch(
            __name__ + ".tor_async_util.pycurl",
            pycurl_mock,
            create=True)    # :TRICKY: 'create' important since pycurl doesn't exist

    def __enter__(self):
        self._pycurl_patch.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._pycurl_patch.stop()


class TestCase(unittest.TestCase):
    """Abstract base class for all TestCase's in this file."""

    def setUp(self):
        self.assertTrue("pycurl" not in sys.modules)
        with self.assertRaises(ImportError):
            import pycurl
            pycurl.never_get_here_but_fixes_flake8_error()

    def test_pycurl_import_not_available(self):
        with mock.patch(__name__ + ".tor_async_util._logger") as logger_patch:
            self.assertFalse(tor_async_util.is_libcurl_compiled_with_async_dns_resolver())

            self.assertEqual(
                logger_patch.error.call_args_list,
                [])

            self.assertEqual(
                logger_patch.info.call_args_list,
                [])

            expected_debug_message = (
                "Error trying to figure out if libcurl is complied with "
                "async DNS resolver - global name 'pycurl' is not defined"
            )
            self.assertEqual(
                logger_patch.debug.call_args_list,
                [mock.call(expected_debug_message)])

    def test_happy_version_info_array_does_not_contain_features(self):
        with MockPycurlInstaller(self, []):
            with mock.patch(__name__ + ".tor_async_util._logger") as logger_patch:
                self.assertFalse(tor_async_util.is_libcurl_compiled_with_async_dns_resolver())

                self.assertEqual(
                    logger_patch.error.call_args_list,
                    [])

                self.assertEqual(
                    logger_patch.info.call_args_list,
                    [])

                expected_debug_message = (
                    "Error trying to figure out if libcurl is complied with "
                    "async DNS resolver - list index out of range"
                )
                self.assertEqual(
                    logger_patch.debug.call_args_list,
                    [mock.call(expected_debug_message)])

    def test_happy_path(self):
        with MockPycurlInstaller(self, [0, 0, 0, 0, 1 << 7]):
            with mock.patch(__name__ + ".tor_async_util._logger") as logger_patch:
                self.assertTrue(tor_async_util.is_libcurl_compiled_with_async_dns_resolver())

                self.assertEqual(
                    logger_patch.error.call_args_list,
                    [])

                self.assertEqual(
                    logger_patch.info.call_args_list,
                    [])

                self.assertEqual(
                    logger_patch.debug.call_args_list,
                    [])
