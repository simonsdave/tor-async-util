"""This module contains unit testings for __init__.py."""

import json
import httplib
import re
import signal
import sys
import unittest

import mock
import tornado.testing
import tornado.web

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


class IsLibCurlCompiledWithAsyncDNSResolverTestCase(unittest.TestCase):
    """Unit tests for is_libcurl_compiled_with_async_dns_resolver()."""

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


class InstallSigIntHandlerTestCase(unittest.TestCase):
    """Unit tests for install_sigint_handler()."""

    def test_install_sigint_handler_installs_sigint_handler(self):
        signal_dot_signal_patch = mock.Mock()
        with mock.patch("signal.signal", signal_dot_signal_patch):
            tor_async_util.install_sigint_handler()
        self.assertEquals(
            signal_dot_signal_patch.call_args_list,
            [mock.call(signal.SIGINT, tor_async_util._sigint_handler)])

    def test_sigint_handler_calls_sys_dot_exit_with_zero(self):
        sys_dot_exit_patch = mock.Mock()
        with mock.patch("sys.exit", sys_dot_exit_patch):
            frame = "what should this be?"
            tor_async_util._sigint_handler(signal.SIGINT, frame)
        self.assertEquals(
            sys_dot_exit_patch.call_args_list,
            [mock.call(0)])


class SomethingHandler(tornado.web.RequestHandler):
    """Used by DefaultHandlerTestCase."""

    url_spec = r"/something"

    def head(self, *args, **kwargs):
        pass

    def get(self, *args, **kwargs):
        pass

    def post(self, *args, **kwargs):
        pass

    def delete(self, *args, **kwargs):
        pass

    def patch(self, *args, **kwargs):
        pass

    def put(self, *args, **kwargs):
        pass

    def options(self, *args, **kwargs):
        pass

    def prepare(self):
        self.set_status(httplib.OK)
        self.finish()


class DefaultHandlerTestCase(tornado.testing.AsyncHTTPTestCase):
    """Unit tests for DefaultRequestHandler."""

    other_url = "/else"

    def get_app(self):
        settings = {
            "default_handler_class": tor_async_util.DefaultRequestHandler,
        }

        handlers = [
            (SomethingHandler.url_spec, SomethingHandler),
        ]

        return tornado.web.Application(handlers=handlers, **settings)

    def _test(self, method):
        body = "" if method in ["POST", "PUT", "PATCH"] else None

        response = self.fetch(SomethingHandler.url_spec, method=method, body=body)
        self.assertEqual(response.code, httplib.OK)

        self.assertNotEqual(type(self).other_url, SomethingHandler.url_spec)

        response = self.fetch(type(self).other_url, method=method, body=body)
        self.assertEqual(response.code, httplib.NOT_FOUND)
        # since HEAD request never has a body
        if method != "HEAD":
            content_type = response.headers.get("Content-Type", None)
            self.assertIsNotNone(content_type)
            json_utf8_content_type_reg_ex = re.compile(
                "^\s*application/json;\s+charset\=utf-{0,1}8\s*$",
                re.IGNORECASE)
            self.assertTrue(json_utf8_content_type_reg_ex.match(content_type))

            self.assertEqual({}, json.loads(response.body))

    def test_all_good(self):
        self._test("GET")
        self._test("POST")
        self._test("DELETE")
        self._test("PATCH")
        self._test("PUT")
        self._test("OPTIONS")
        self._test("HEAD")
