"""This module contains unit tests for __init__.py."""

import logging
import json
import httplib
import os
import re
import shutil
import signal
import tempfile
import unittest
import uuid

import jsonschema
from keyczar import keyczar
from keyczar import keyczart
import mock
import tornado.testing
import tornado.web

import tor_async_util


class Patcher(object):
    """An abstract base class for all patcher context managers."""

    def __init__(self, patcher):
        object.__init__(self)
        self._patcher = patcher

    def __enter__(self):
        self._patcher.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._patcher.stop()


class PyCurlVersionInfoExceptionPatcher(Patcher):

    def __init__(self):

        self.id = uuid.uuid4().hex

        def patch():
            raise Exception(self.id)

        patcher = mock.patch(
            __name__ + '.tor_async_util.pycurl.version_info',
            patch)

        Patcher.__init__(self, patcher)


class PyCurlVersionInfoPatcher(Patcher):

    def __init__(self, value):

        def patch():
            return value

        patcher = mock.patch(
            __name__ + '.tor_async_util.pycurl.version_info',
            patch)

        Patcher.__init__(self, patcher)


class IsLibCurlCompiledWithAsyncDNSResolverTestCase(unittest.TestCase):
    """Unit tests for is_libcurl_compiled_with_async_dns_resolver()."""

    def test_pycurl_import_not_available(self):
        with PyCurlVersionInfoExceptionPatcher() as version_info_patcher:
            with mock.patch(__name__ + '.tor_async_util._logger') as logger_patch:
                self.assertFalse(tor_async_util.is_libcurl_compiled_with_async_dns_resolver())

                self.assertEqual(
                    logger_patch.error.call_args_list,
                    [])

                self.assertEqual(
                    logger_patch.info.call_args_list,
                    [])

                expected_debug_message_fmt = (
                    'Error trying to figure out if libcurl is complied with '
                    'async DNS resolver - %s'
                )
                expected_debug_message = expected_debug_message_fmt % version_info_patcher.id

                self.assertEqual(
                    logger_patch.debug.call_args_list,
                    [mock.call(expected_debug_message)])

    def test_happy_version_info_array_does_not_contain_features(self):
        with PyCurlVersionInfoPatcher([]):
            with mock.patch(__name__ + '.tor_async_util._logger') as logger_patch:
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
        with PyCurlVersionInfoPatcher([0, 0, 0, 0, 1 << 7]):
            with mock.patch(__name__ + '.tor_async_util._logger') as logger_patch:
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
                r"^\s*application/json;\s+charset\=utf-{0,1}8\s*$",
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


class WriteAndVerifyPatcher(Patcher):
    """This context manager provides an easy way to install a
    patch allowing the caller to determine the return value of
    RequestHandler.write_and_verify().
    """

    def __init__(self, is_ok):

        def write_and_verify_patch(request_handler, body, schema):
            return is_ok

        patcher = mock.patch(
            (
                "tor_async_util.RequestHandler.write_and_verify"
            ),
            write_and_verify_patch)

        Patcher.__init__(self, patcher)


class RequestHandlerTestCase(tornado.testing.AsyncHTTPTestCase):
    """Abstract base class for all handler unit test cases."""

    _json_utf8_content_type_reg_ex = re.compile(
        r"^\s*application/json;\s+charset\=utf-{0,1}8\s*$",
        re.IGNORECASE)

    def fetch(self, path, **kwargs):
        if kwargs.get('method') in {'POST', 'PUT'}:
            kwargs.setdefault(
                'headers',
                tornado.httputil.HTTPHeaders({
                    'content-type': 'application/json; charset=utf-8'
                })
            )
        json_body = kwargs.pop('json', None)
        if json_body:
            kwargs['body'] = json.dumps(json_body)
        return super(RequestHandlerTestCase, self).fetch(path, **kwargs)

    def assertDebugDetail(self, response, expected_value):
        """Assert a debug failure detail HTTP header appears in
        ```response``` with a value equal to ```expected_value```."""
        value = response.headers.get(
            tor_async_util.debug_details_header_name,
            None)
        self.assertIsNotNone(value)
        self.assertTrue(value.startswith("0x"))
        self.assertEqual(int(value, 16), expected_value)

    def assertNoDebugDetail(self, response):
        """Assert *no* debug failure detail HTTP header appears
        in ```response```."""
        value = response.headers.get(
            tor_async_util.debug_details_header_name,
            None)
        self.assertIsNone(value)

    def assertJsonContentTypeInResponse(self, response):
        content_type = response.headers.get("Content-Type", None)
        self.assertIsNotNone(content_type)
        self.assertTrue(self._json_utf8_content_type_reg_ex.match(content_type))


class TestGetBasicAuthCredsRequestHandler(tor_async_util.RequestHandler):

    url_spec = r"/dave"

    @tornado.web.asynchronous
    def get(self):
        (username, password, error_code) = self.get_basic_auth_creds()

        response = {
            "error_code": error_code,
        }
        if username is not None:
            response["username"] = username
        if password is not None:
            response["password"] = password

        self.write(response)
        self.set_status(httplib.OK)
        self.finish()


class GetBasicAuthCredsRequestHandlerTestCase(tornado.testing.AsyncHTTPTestCase):
    """A collection of unit tests for
    RequestHandler.get_basic_auth_creds"""

    def get_app(self):
        handlers = [
            (
                TestGetBasicAuthCredsRequestHandler.url_spec,
                TestGetBasicAuthCredsRequestHandler
            ),
        ]
        return tornado.web.Application(handlers=handlers)

    def test_get_basic_auth_creds_all_good(self):
        username = uuid.uuid4().hex
        password = uuid.uuid4().hex

        response = self.fetch(
            "/dave",
            method="GET",
            auth_mode="basic",
            auth_username=username,
            auth_password=password)

        self.assertEqual(response.code, httplib.OK)

        response_body = json.loads(response.body)

        self.assertTrue("username" in response_body)
        self.assertEqual(response_body["username"], username)

        self.assertTrue("password" in response_body)
        self.assertEqual(response_body["password"], password)

        self.assertTrue("error_code" in response_body)
        self.assertEqual(
            response_body["error_code"],
            tor_async_util.RequestHandler.GBAC_OK)

    def test_get_basic_auth_creds_no_authorization_header(self):
        response = self.fetch(
            "/dave",
            method="GET")

        self.assertEqual(response.code, httplib.OK)

        response_body = json.loads(response.body)

        self.assertTrue("username" not in response_body)

        self.assertTrue("password" not in response_body)

        self.assertTrue("error_code" in response_body)
        self.assertEqual(
            response_body["error_code"],
            tor_async_util.RequestHandler.GBAC_NO_AUTHORIZATION_HEADER)

    def test_get_basic_auth_creds_invalid_authorization_header(self):
        headers = {
            "Authorization": "bindle",
        }

        response = self.fetch(
            "/dave",
            method="GET",
            headers=tornado.httputil.HTTPHeaders(headers))

        self.assertEqual(response.code, httplib.OK)

        response_body = json.loads(response.body)

        self.assertTrue("username" not in response_body)
        self.assertTrue("password" not in response_body)

        self.assertTrue("error_code" in response_body)
        self.assertEqual(
            response_body["error_code"],
            tor_async_util.RequestHandler.GBAC_INVALID_AUTHORIZATION_HEADER_VALUE)

    def test_get_basic_auth_creds_bad_base64_encoding(self):
        headers = {
            "Authorization": "BASIC a",
        }

        response = self.fetch(
            "/dave",
            method="GET",
            headers=tornado.httputil.HTTPHeaders(headers))

        self.assertEqual(response.code, httplib.OK)

        response_body = json.loads(response.body)

        self.assertTrue("username" not in response_body)
        self.assertTrue("password" not in response_body)

        self.assertTrue("error_code" in response_body)
        self.assertEqual(
            response_body["error_code"],
            tor_async_util.RequestHandler.GBAC_BAD_B64_ENCODING)

    def test_get_basic_auth_creds_invalid_username_password(self):
        headers = {
            "Authorization": "BASIC dada",
        }

        response = self.fetch(
            "/dave",
            method="GET",
            headers=tornado.httputil.HTTPHeaders(headers))

        self.assertEqual(response.code, httplib.OK)

        response_body = json.loads(response.body)

        self.assertTrue("username" not in response_body)
        self.assertTrue("password" not in response_body)

        self.assertTrue("error_code" in response_body)
        self.assertEqual(
            response_body["error_code"],
            tor_async_util.RequestHandler.GBAC_INVALID_USERNAME_PASSWORD)


class TestGetJsonRequestBodyRequestHandler(tor_async_util.RequestHandler):
    """This class is used by ```GetJsonRequestBodyTestCase```."""

    url_spec = r"/dave"

    @tornado.web.asynchronous
    def post(self):
        schema = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "type": "object",
            "properties": {
                "lp": {
                    "type": "string",
                },
            },
            "required": [
                "lp",
            ],
            "additionalProperties": False
        }
        body = self.get_json_request_body(schema)
        self.set_status(httplib.BAD_REQUEST if body is None else httplib.OK)
        self.finish()


class GetJsonRequestBodyTestCase(tornado.testing.AsyncHTTPTestCase):
    """A collection of unit tests for
    RequestHandler.get_json_request_body()"""

    def get_app(self):
        handlers = [
            (
                TestGetJsonRequestBodyRequestHandler.url_spec,
                TestGetJsonRequestBodyRequestHandler
            ),
        ]
        return tornado.web.Application(handlers=handlers)

    def test_all_good(self):
        body = {
            "lp": "dave was here",
        }
        headers = {
            "content-type": "application/json",
        }
        response = self.fetch(
            "/dave",
            method="POST",
            headers=tornado.httputil.HTTPHeaders(headers),
            body=json.dumps(body))
        self.assertEqual(response.code, httplib.OK)

    def test_no_body(self):
        headers = {
            "content-type": "application/json; charset=utf-8",
        }
        response = self.fetch(
            "/dave",
            method="POST",
            headers=tornado.httputil.HTTPHeaders(headers),
            body="")
        self.assertEqual(response.code, httplib.BAD_REQUEST)

    def test_bad_content_type(self):
        #
        # first some good cases ...
        #
        body = {
            "lp": "dave was here",
        }
        headers = {
            "content-type": "application/json; charset=utf-8",
        }
        response = self.fetch(
            "/dave",
            method="POST",
            headers=tornado.httputil.HTTPHeaders(headers),
            body=json.dumps(body))
        self.assertEqual(response.code, httplib.OK)

        headers["content-type"] = "application/json; charset=utf-8"
        response = self.fetch(
            "/dave",
            method="POST",
            headers=tornado.httputil.HTTPHeaders(headers),
            body=json.dumps(body))
        self.assertEqual(response.code, httplib.OK)

        headers["content-type"] = "  application/json; charset=utf-8  "
        response = self.fetch(
            "/dave",
            method="POST",
            headers=tornado.httputil.HTTPHeaders(headers),
            body=json.dumps(body))
        self.assertEqual(response.code, httplib.OK)

        #
        # now some bad cases ...
        #
        headers["content-type"] = "bindle"
        response = self.fetch(
            "/dave",
            method="POST",
            headers=tornado.httputil.HTTPHeaders(headers),
            body=json.dumps(body))
        self.assertEqual(response.code, httplib.BAD_REQUEST)

        headers["content-type"] = "application/json;"
        response = self.fetch(
            "/dave",
            method="POST",
            headers=tornado.httputil.HTTPHeaders(headers),
            body=json.dumps(body))
        self.assertEqual(response.code, httplib.BAD_REQUEST)

    def test_no_content_type(self):
        #
        # first the good case ...
        #
        body = {
            "lp": "dave was here",
        }
        headers = {
            "content-type": "application/json; charset=utf-8",
        }
        response = self.fetch(
            "/dave",
            method="POST",
            headers=tornado.httputil.HTTPHeaders(headers),
            body=json.dumps(body))
        self.assertEqual(response.code, httplib.OK)

        #
        # now the good case ...
        #

        # :TODO: content type header is added back in by self.fetch()
        # & I don't know how to defeat this so this test actually
        # doesn't currently do what it's supposed to do:-(

        del headers["content-type"]
        response = self.fetch(
            "/dave",
            method="POST",
            headers=tornado.httputil.HTTPHeaders(headers),
            body=json.dumps(body))
        self.assertEqual(response.code, httplib.BAD_REQUEST)

    def test_fail_schema_validation(self):
        #
        # first the good case ...
        #
        body = {
            "lp": "dave was here",
        }
        headers = {
            "content-type": "application/json; charset=utf-8",
        }
        response = self.fetch(
            "/dave",
            method="POST",
            headers=tornado.httputil.HTTPHeaders(headers),
            body=json.dumps(body))
        self.assertEqual(response.code, httplib.OK)

        #
        # now the good case ...
        #
        body["dave"] = "was here"
        response = self.fetch(
            "/dave",
            method="POST",
            headers=tornado.httputil.HTTPHeaders(headers),
            body=json.dumps(body))
        self.assertEqual(response.code, httplib.BAD_REQUEST)


class TornadoRequestHandlerCtrPatcher(object):
    """This context manager is used to simplify the implementation of
    ```RequestHandlerTestEdgeCases```."""

    def __init__(self, request):
        object.__init__(self)

        def init_patch(rh, *args, **kwargs):
            rh.request = request

        self._patcher = mock.patch(
            "tornado.web.RequestHandler.__init__",
            init_patch)

    def __enter__(self):
        self._patcher.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._patcher.stop()


class RequestHandlerTestEdgeCases(unittest.TestCase):
    """```GetJsonRequestBodyTestCase``` does the "regular"
    unit testing for ```RequestHandler```. This
    class validates a collection of edge cases
    that are hard to explore using using the standard
    Tornado unit testing framework."""

    schema = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "properties": {
            "msg": {
                "type": "string",
            },
        },
        "required": [
            "msg",
        ],
        "additionalProperties": False
    }

    def test_content_length_and_transfer_encoding(self):
        the_body = {
            "msg": "dave was here!!!",
        }
        jsonschema.validate(the_body, self.schema)
        the_body_as_json = json.dumps(the_body)
        the_request = mock.Mock(
            headers={
                "Content-Length": len(the_body_as_json),
                "Content-Type": "application/json; charset=utf-8",
            },
            body=the_body_as_json,
        )

        # start with all good scenario
        with TornadoRequestHandlerCtrPatcher(the_request):
            the_request_handler = tor_async_util.RequestHandler()
            body = the_request_handler.get_json_request_body(self.schema)
            self.assertIsNotNone(body)
            self.assertEqual(body, the_body)

        # remove the content length which should cause specific failure
        del the_request.headers["Content-Length"]

        with TornadoRequestHandlerCtrPatcher(the_request):
            the_request_handler = tor_async_util.RequestHandler()
            body = the_request_handler.get_json_request_body(self.schema)
            self.assertIsNone(body)

    def test_body_is_none(self):
        the_body = {
            "msg": "dave was here!!!",
        }
        jsonschema.validate(the_body, self.schema)
        the_body_as_json = json.dumps(the_body)
        the_request = mock.Mock(
            headers={
                "Content-Length": len(the_body_as_json),
                "Content-Type": "application/json; charset=utf-8",
            },
            body=the_body_as_json,
        )

        # start with all good scenario
        with TornadoRequestHandlerCtrPatcher(the_request):
            the_request_handler = tor_async_util.RequestHandler()
            body = the_request_handler.get_json_request_body(self.schema)
            self.assertIsNotNone(body)
            self.assertEqual(body, the_body)

        # set body to None which should cause specific failure
        the_request.body = None

        with TornadoRequestHandlerCtrPatcher(the_request):
            the_request_handler = tor_async_util.RequestHandler()
            body = the_request_handler.get_json_request_body(self.schema)
            self.assertIsNone(body)

    def test_no_content_type(self):
        the_body = {
            "msg": "dave was here!!!",
        }
        jsonschema.validate(the_body, self.schema)
        the_body_as_json = json.dumps(the_body)
        the_request = mock.Mock(
            headers={
                "Content-Length": len(the_body_as_json),
                "Content-Type": "application/json; charset=utf-8",
            },
            body=the_body_as_json,
        )

        # start with all good scenario
        with TornadoRequestHandlerCtrPatcher(the_request):
            the_request_handler = tor_async_util.RequestHandler()
            body = the_request_handler.get_json_request_body(self.schema)
            self.assertIsNotNone(body)
            self.assertEqual(body, the_body)

        # remove the content type which should cause specific failure
        del the_request.headers["Content-Type"]

        with TornadoRequestHandlerCtrPatcher(the_request):
            the_request_handler = tor_async_util.RequestHandler()
            body = the_request_handler.get_json_request_body(self.schema)
            self.assertIsNone(body)

    def test_all_good(self):
        the_body = {
            "msg": "dave was here!!!",
        }
        jsonschema.validate(the_body, self.schema)
        the_body_as_json = json.dumps(the_body)
        the_request = mock.Mock(
            headers={
                "Content-Length": len(the_body_as_json),
                "Content-Type": "application/json; charset=utf-8",
            },
            body=the_body_as_json,
        )
        with TornadoRequestHandlerCtrPatcher(the_request):
            the_request_handler = tor_async_util.RequestHandler()
            body = the_request_handler.get_json_request_body(self.schema)
            self.assertIsNotNone(body)
            self.assertEqual(body, the_body)


class TestWriteAndVerifyRequestHandler(tor_async_util.RequestHandler):
    """This class is only used by ```WriteAndVerifyTestCase```."""

    url_spec = r"/dave"

    @tornado.web.asynchronous
    def get(self):
        response_schema = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "type": "object",
            "properties": {
                "msg": {
                    "type": "string",
                },
            },
            "required": [
                "msg",
            ],
            "additionalProperties": False
        }
        good_response = self.get_argument("good_response") == "yes"
        if good_response:
            response_body = {
                "msg": "all good",
            }
        else:
            response_body = {
                "msg": "all bad",
                "unwanted": "property",
            }
        write_ok = self.write_and_verify(response_body, response_schema)
        self.set_status(httplib.OK if write_ok else httplib.BAD_REQUEST)
        self.finish()


class WriteAndVerifyTestCase(tornado.testing.AsyncHTTPTestCase):
    """A collection of unit tests for
    RequestHandler.write_and_verify."""

    def get_app(self):
        handlers = [
            (
                TestWriteAndVerifyRequestHandler.url_spec,
                TestWriteAndVerifyRequestHandler
            ),
        ]
        return tornado.web.Application(handlers=handlers)

    def test_good(self):
        response = self.fetch(
            "/dave?good_response=yes",
            method="GET")
        self.assertEqual(response.code, httplib.OK)

    def test_bad(self):
        response = self.fetch(
            "/dave?good_response=no",
            method="GET")
        self.assertEqual(response.code, httplib.BAD_REQUEST)


class TestWriteBadRequestResponseRequestHandler(tor_async_util.RequestHandler):
    """This class is only used by ```WriteBadRequestResponseTestCase```."""

    url_spec = r'/dave'

    @tornado.web.asynchronous
    def get(self):
        debug_details = self.get_argument('debug_details', None)
        if debug_details is None:
            self.write_bad_request_response()
        else:
            self.write_bad_request_response(int(debug_details))
        self.finish()


class WriteBadRequestResponseTestCase(RequestHandlerTestCase):
    """A collection of unit tests for RequestHandler.write_and_verify."""

    def get_app(self):
        handlers = [
            (
                TestWriteBadRequestResponseRequestHandler.url_spec,
                TestWriteBadRequestResponseRequestHandler
            ),
        ]
        return tornado.web.Application(handlers=handlers)

    def test_no_debug_detail(self):
        response = self.fetch(
            TestWriteBadRequestResponseRequestHandler.url_spec,
            method='GET')
        self.assertEqual(response.code, httplib.BAD_REQUEST)
        self.assertNoDebugDetail(response)

    def test_with_debug_detail(self):
        debug_detail = 42
        response = self.fetch(
            '%s?debug_details=%d' % (TestWriteBadRequestResponseRequestHandler.url_spec, debug_detail),
            method='GET')
        self.assertEqual(response.code, httplib.BAD_REQUEST)
        self.assertDebugDetail(response, debug_detail)


class TestSetStatusRequestHandler(tor_async_util.RequestHandler):
    """This class is used by ```SetStatusTestCase```."""

    url_spec = r"/set-status"

    @tornado.web.asynchronous
    def post(self):
        code = int(self.get_argument('code'))
        reason = self.get_argument('reason', None)
        self.set_status(code, reason)
        self.finish()


class SetStatusTestCase(tornado.testing.AsyncHTTPTestCase):
    """A collection of unit tests for RequestHandler.set_status()"""

    def get_app(self):
        handlers = [
            (
                TestSetStatusRequestHandler.url_spec,
                TestSetStatusRequestHandler
            ),
        ]
        return tornado.web.Application(handlers=handlers)

    def test_set_status_code_supports_all_webdav_code(self):
        webdav_codes = {
            # 102: 'Processing',  # Not supported by tornado http_client
            207: 'Multi-Status',
            226: 'IM Used',
            422: 'Unprocessable Entity',
            423: 'Locked',
            424: 'Failed Dependency',
            426: 'Upgrade Required',
            507: 'Insufficient Storage',
            510: 'Not Extended',
        }
        for code, reason in webdav_codes.items():
            response = self.fetch(
                "/set-status?code=" + str(code), method="POST", body='{}')
            self.assertEqual(response.code, code)
            self.assertEqual(response.reason, webdav_codes[code])

    def test_set_status_code_preserves_reason(self):
        response = self.fetch(
            "/set-status?code=200&reason=foo", method="POST", body='{}')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.reason, 'foo')

    def test_set_status_code_raises_value_error_on_unknown_status(self):
        with self.assertRaises(ValueError):
            tor_async_util.RequestHandler(
                self.get_app(), mock.Mock()).set_status(1)


class WriteErrorRequestHandler(tor_async_util.RequestHandler):
    """This class is used by ```WriteErrorTestCase```."""

    url_spec = r"/something"

    @tornado.web.asynchronous
    def get(self):
        self.set_status(httplib.OK)
        self.finish()


class WriteErrorTestCase(tornado.testing.AsyncHTTPTestCase):
    """A collection of unit tests for RequestHandler.write_error()"""

    def get_app(self):
        handlers = [
            (
                WriteErrorRequestHandler.url_spec,
                WriteErrorRequestHandler
            ),
        ]
        return tornado.web.Application(handlers=handlers)

    def test_write_error(self):
        response = self.fetch(WriteErrorRequestHandler.url_spec, method="GET")
        self.assertEqual(response.code, httplib.OK)
        self.assertEqual(response.body, '')

        response = self.fetch(WriteErrorRequestHandler.url_spec, method="POST", body='{}')
        self.assertEqual(response.code, httplib.METHOD_NOT_ALLOWED)
        content_type = response.headers.get("Content-Type")
        self.assertIsNotNone(content_type)
        self.assertEqual(content_type, 'application/json; charset=UTF-8')
        self.assertEqual(response.body, '{}')

        response = self.fetch(WriteErrorRequestHandler.url_spec, method="HEAD")
        self.assertEqual(response.code, httplib.METHOD_NOT_ALLOWED)
        self.assertEqual(response.body, '')


class TempConfigFile(object):

    def __init__(self, option=None, value=None, values=None):
        object.__init__(self)

        self.section = uuid.uuid4().hex

        ntf = tempfile.NamedTemporaryFile(delete=False)
        self.filename = ntf.name
        ntf.write("[%s]\n" % self.section)

        if option is not None and value is not None:
            self._write(ntf, option, value)

        if values is not None:
            for (option, value) in values:
                self._write(ntf, option, value)

        ntf.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        os.remove(self.filename)

    def _write(self, ntf, option, value):
        ntf.write("%s=%s\n" % (option, value))


class TempDirectory(object):

    def __init__(self):
        object.__init__(self)
        self._dir_name = None

    def __enter__(self):
        self._dir_name = tempfile.mkdtemp()
        return self._dir_name

    def __exit__(self, exc_type, exc_value, traceback):
        if self._dir_name:
            shutil.rmtree(self._dir_name, ignore_errors=True)


class ConfigTestCase(unittest.TestCase):
    """A collection of unit tests for Config."""

    def test_ctr_with_config_file_that_does_not_exist(self):
        filename_that_does_not_exist = uuid.uuid4().hex
        config = tor_async_util.Config(filename_that_does_not_exist)

        section_name = uuid.uuid4().hex
        option_name = uuid.uuid4().hex
        value_if_not_found = uuid.uuid4().hex
        self.assertEqual(
            value_if_not_found,
            config.get(section_name, option_name, value_if_not_found))

    def test_get(self):
        option = uuid.uuid4().hex
        value = uuid.uuid4().hex
        with TempConfigFile(option, value) as tcf:
            config = tor_async_util.Config(tcf.filename)
            value_if_not_found = uuid.uuid4().hex
            read_value = config.get(tcf.section, option, value_if_not_found)
            self.assertEqual(read_value, value)

    def test_get_not_found(self):
        with TempConfigFile() as tcf:
            config = tor_async_util.Config(tcf.filename)
            option = uuid.uuid4().hex
            value_if_not_found = uuid.uuid4().hex
            read_value = config.get(tcf.section, option, value_if_not_found)
            self.assertEqual(read_value, value_if_not_found)

    def test_get_expanduser_working(self):
        option = uuid.uuid4().hex
        value_postfix = uuid.uuid4().hex
        value = "~/" + value_postfix
        with TempConfigFile(option, value) as tcf:
            config = tor_async_util.Config(tcf.filename)
            value_if_not_found = uuid.uuid4().hex
            read_value = config.get(tcf.section, option, value_if_not_found)
            self.assertFalse(read_value.startswith("~"))
            self.assertTrue(read_value.endswith(value_postfix))

    def test_get_all_values_for_missing_section(self):
        with TempConfigFile() as tcf:
            config = tor_async_util.Config(tcf.filename)
            non_existent_section = uuid.uuid4().hex
            values_if_not_found = uuid.uuid4().hex
            read_values = config.get_all_values(non_existent_section, values_if_not_found)
            self.assertEqual(read_values, values_if_not_found)

    def test_get_all_values_happy_path(self):
        values = [
            ('dave', 'was'),
            ('here', 'to'),
            ('help', 'or not:-)'),
        ]
        with TempConfigFile(values=values) as tcf:
            config = tor_async_util.Config(tcf.filename)
            values_if_not_found = uuid.uuid4().hex
            read_values = config.get_all_values(tcf.section, values_if_not_found)
            self.assertEqual(read_values, values)

    def test_get_int_positive(self):
        option = uuid.uuid4().hex
        value = "342"
        with TempConfigFile(option, value) as tcf:
            config = tor_async_util.Config(tcf.filename)
            value_if_not_found = uuid.uuid4().hex
            read_value = config.get_int(tcf.section, option, value_if_not_found)
            self.assertEqual(read_value, int(value))

    def test_get_int_zero(self):
        option = uuid.uuid4().hex
        value = "0"
        with TempConfigFile(option, value) as tcf:
            config = tor_async_util.Config(tcf.filename)
            value_if_not_found = uuid.uuid4().hex
            read_value = config.get_int(tcf.section, option, value_if_not_found)
            self.assertEqual(read_value, int(value))

    def test_get_int_negative(self):
        option = uuid.uuid4().hex
        value = "-8713"
        with TempConfigFile(option, value) as tcf:
            config = tor_async_util.Config(tcf.filename)
            value_if_not_found = uuid.uuid4().hex
            read_value = config.get_int(tcf.section, option, value_if_not_found)
            self.assertEqual(read_value, int(value))

    def test_get_int_not_found(self):
        with TempConfigFile() as tcf:
            config = tor_async_util.Config(tcf.filename)
            option = uuid.uuid4().hex
            value_if_not_found = uuid.uuid4().hex
            read_value = config.get_int(tcf.section, option, value_if_not_found)
            self.assertEqual(read_value, value_if_not_found)

    def test_get_int_not_an_int(self):
        option = uuid.uuid4().hex
        value = uuid.uuid4().hex
        with TempConfigFile(option, value) as tcf:
            config = tor_async_util.Config(tcf.filename)
            value_if_not_found = uuid.uuid4().hex
            read_value = config.get_int(tcf.section, option, value_if_not_found)
            self.assertEqual(read_value, value_if_not_found)

    def test_get_boolean(self):
        test_data = {
            "true": True,
            "True": True,
            "1": True,
            "y": True,
            "false": False,
            "False": False,
            "0": False,
            "n": False,
        }
        for (value, expected_value) in test_data.iteritems():
            option = uuid.uuid4().hex
            with TempConfigFile(option, value) as tcf:
                config = tor_async_util.Config(tcf.filename)
                value_if_not_found = uuid.uuid4().hex
                read_value = config.get_boolean(tcf.section, option, value_if_not_found)
                self.assertEqual(read_value, expected_value)

    def test_get_boolean_not_found(self):
        with TempConfigFile() as tcf:
            config = tor_async_util.Config(tcf.filename)
            option = uuid.uuid4().hex
            value_if_not_found = uuid.uuid4().hex
            read_value = config.get_boolean(tcf.section, option, value_if_not_found)
            self.assertEqual(read_value, value_if_not_found)

    def test_get_boolean_not_a_boolean(self):
        option = uuid.uuid4().hex
        value = uuid.uuid4().hex
        with TempConfigFile(option, value) as tcf:
            config = tor_async_util.Config(tcf.filename)
            value_if_not_found = uuid.uuid4().hex
            read_value = config.get_boolean(tcf.section, option, value_if_not_found)
            self.assertEqual(read_value, value_if_not_found)

    def test_get_logging_level(self):
        test_data = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "Info": logging.INFO,
            "InFo": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "critical": logging.CRITICAL,
            "fatal": logging.FATAL,
        }
        for (value, expected_value) in test_data.iteritems():
            option = uuid.uuid4().hex
            with TempConfigFile(option, value) as tcf:
                config = tor_async_util.Config(tcf.filename)
                value_if_not_found = uuid.uuid4().hex
                read_value = config.get_logging_level(tcf.section, option, value_if_not_found)
                self.assertEqual(read_value, expected_value)

    def test_get_logging_level_not_found(self):
        with TempConfigFile() as tcf:
            config = tor_async_util.Config(tcf.filename)
            option = uuid.uuid4().hex
            value_if_not_found = uuid.uuid4().hex
            read_value = config.get_logging_level(tcf.section, option, value_if_not_found)
            self.assertEqual(read_value, value_if_not_found)

    def test_get_logging_level_not_a_logging_level(self):
        option = uuid.uuid4().hex
        value = uuid.uuid4().hex
        with TempConfigFile(option, value) as tcf:
            config = tor_async_util.Config(tcf.filename)
            value_if_not_found = uuid.uuid4().hex
            read_value = config.get_logging_level(tcf.section, option, value_if_not_found)
            self.assertEqual(read_value, value_if_not_found)

    def test_get_keyczar_crypter_happy_path(self):
        with TempDirectory() as dir_name:
            keyczart.Create(dir_name, "some purpose", keyczart.keyinfo.DECRYPT_AND_ENCRYPT)

            option = uuid.uuid4().hex
            with TempConfigFile(option, dir_name) as tcf:
                config = tor_async_util.Config(tcf.filename)
                value_if_not_found = uuid.uuid4().hex
                crypter = config.get_keyczar_crypter(tcf.section, option, value_if_not_found)
                self.assertEqual(type(crypter), keyczar.Crypter)

    def test_get_keyczar_crypter_option_not_in_config_file(self):
        with TempConfigFile() as tcf:
            config = tor_async_util.Config(tcf.filename)
            option = uuid.uuid4().hex
            value_if_not_found = uuid.uuid4().hex
            crypter = config.get_keyczar_crypter(tcf.section, option, value_if_not_found)
            self.assertEqual(crypter, value_if_not_found)

    def test_get_keyczar_crypter_empty_directory(self):
        with TempDirectory() as dir_name:
            option = uuid.uuid4().hex
            with TempConfigFile(option, dir_name) as tcf:
                config = tor_async_util.Config(tcf.filename)
                value_if_not_found = uuid.uuid4().hex
                crypter = config.get_keyczar_crypter(tcf.section, option, value_if_not_found)
                self.assertEqual(crypter, value_if_not_found)

    def test_get_keyczar_signer_happy_path(self):
        with TempDirectory() as dir_name:
            keyczart.Create(dir_name, "some purpose", keyczart.keyinfo.SIGN_AND_VERIFY)

            option = uuid.uuid4().hex
            with TempConfigFile(option, dir_name) as tcf:
                config = tor_async_util.Config(tcf.filename)
                value_if_not_found = uuid.uuid4().hex
                signer = config.get_keyczar_signer(tcf.section, option, value_if_not_found)
                self.assertEqual(type(signer), keyczar.Signer)

    def test_get_keyczar_signer_option_not_in_config_file(self):
        with TempConfigFile() as tcf:
            config = tor_async_util.Config(tcf.filename)
            option = uuid.uuid4().hex
            value_if_not_found = uuid.uuid4().hex
            signer = config.get_keyczar_signer(tcf.section, option, value_if_not_found)
            self.assertEqual(signer, value_if_not_found)

    def test_get_keyczar_signer_empty_directory(self):
        with TempDirectory() as dir_name:
            option = uuid.uuid4().hex
            with TempConfigFile(option, dir_name) as tcf:
                config = tor_async_util.Config(tcf.filename)
                value_if_not_found = uuid.uuid4().hex
                signer = config.get_keyczar_signer(tcf.section, option, value_if_not_found)
                self.assertEqual(signer, value_if_not_found)


class LoggerIsEnabledForPatcher(Patcher):
    """This context manager provides an easy way to install a
    patch allowing the caller to determine the return value of
    tor_async_util._logger.isEnabledFor().
    """

    def __init__(self, is_enabled):

        def is_enabled_for_patch(*args, **kwargs):
            return is_enabled

        patcher = mock.patch(
            (
                'tor_async_util._logger.isEnabledFor'
            ),
            is_enabled_for_patch)

        Patcher.__init__(self, patcher)


class TestAddDebugDetailsRequestHandler(tor_async_util.RequestHandler):
    """This class is only used by ```AddDebugDetailsTestCase```."""

    url_spec = r"/dave"

    @tornado.web.asynchronous
    def get(self):
        value = int(self.get_argument('value', 0))
        self.add_debug_details(value)
        self.write({})
        self.set_status(httplib.OK)
        self.finish()


class AddDebugDetailsTestCase(RequestHandlerTestCase):
    """A collection of unit tests for
    RequestHandler.add_debug_details."""

    def get_app(self):
        handlers = [
            (
                TestAddDebugDetailsRequestHandler.url_spec,
                TestAddDebugDetailsRequestHandler
            ),
        ]
        return tornado.web.Application(handlers=handlers)

    def _test_debug_details(self, is_enabled):
        with LoggerIsEnabledForPatcher(is_enabled):
            debug_detail = 99
            response = self.fetch(
                '%s?value=%d' % (TestAddDebugDetailsRequestHandler.url_spec, debug_detail),
                method='GET')
            self.assertEqual(response.code, httplib.OK)
            if is_enabled:
                self.assertDebugDetail(response, debug_detail)
            else:
                self.assertNoDebugDetail(response)

    def test_debug_details_enabled(self):
        self._test_debug_details(True)

    def test_no_debug_details_enabled(self):
        self._test_debug_details(False)


class TestVersionRequestHandler(tor_async_util.RequestHandler):

    url_spec = r'/_version'

    @tornado.web.asynchronous
    def get(self):
        version = self.get_argument('version', None)
        tor_async_util.generate_version_response(self, version)


class VersionTestCase(RequestHandlerTestCase):
    """Unit tests for generate_version_response()."""

    def get_app(self):
        handlers = [
            (
                TestVersionRequestHandler.url_spec,
                TestVersionRequestHandler
            ),
        ]
        return tornado.web.Application(handlers=handlers)

    def test_bad_response_body(self):
        with WriteAndVerifyPatcher(is_ok=False):
            url = '%s?version=%s' % (TestVersionRequestHandler.url_spec, '0.1.0')
            response = self.fetch(url, method='GET')
            self.assertEqual(response.code, httplib.INTERNAL_SERVER_ERROR)
            self.assertDebugDetail(response, tor_async_util.GVR_INVALID_RESPONSE_BODY)

    def test_happy_path(self):
        url = '%s?version=%s' % (TestVersionRequestHandler.url_spec, '0.1.0')
        response = self.fetch(url, method='GET')
        self.assertEqual(response.code, httplib.OK)
        self.assertNoDebugDetail(response)


class TestNoOpRequestHandler(tor_async_util.RequestHandler):

    url_spec = r'/_noop'

    @tornado.web.asynchronous
    def get(self):
        tor_async_util.generate_noop_response(self)


class NoOpTestCase(RequestHandlerTestCase):
    """Unit tests for generate_noop_response()."""

    def get_app(self):
        handlers = [
            (
                TestNoOpRequestHandler.url_spec,
                TestNoOpRequestHandler
            ),
        ]
        return tornado.web.Application(handlers=handlers)

    def test_bad_response_body(self):
        with WriteAndVerifyPatcher(is_ok=False):
            response = self.fetch(TestNoOpRequestHandler.url_spec, method='GET')
            self.assertEqual(response.code, httplib.INTERNAL_SERVER_ERROR)
            self.assertDebugDetail(response, tor_async_util.GNR_INVALID_RESPONSE_BODY)

    def test_happy_path(self):
        response = self.fetch(TestNoOpRequestHandler.url_spec, method='GET')
        self.assertEqual(response.code, httplib.OK)
        self.assertNoDebugDetail(response)


class AsyncActionTestCase(unittest.TestCase):

    def test_ctr_generates_id(self):
        aa = tor_async_util.AsyncAction()
        self.assertIsNotNone(aa.id)

    def test_ctr_without_async_state(self):
        aa = tor_async_util.AsyncAction()
        self.assertIsNone(aa.async_state)

    def test_ctr_with_async_state(self):
        async_state = mock.Mock()
        aa = tor_async_util.AsyncAction(async_state)
        self.assertTrue(aa.async_state is async_state)

    def test_create_log_msg_for_http_client_response_with_time_info(self):
        async_action = tor_async_util.AsyncAction()

        response = mock.Mock(
            code=httplib.OK,
            error=None,
            body=json.dumps({}),
            time_info={
                "queue": 1,
                "namelookup": 2,
                "connect": 3,
                "pretransfer": 4,
                "starttransfer": 5,
                "total": 6,
                "redirect": 7,
            },
            request_time=0.042,
            effective_url="http://172.17.42.1:4001/v2/keys/key-value",
            request=mock.Mock(method="GET"))

        service = 'my service'

        message = async_action.create_log_msg_for_http_client_response(
            response,
            service)

        expected_message_fmt = (
            "%s took %.2f ms to respond with "
            "%d to %s against >>>%s<<< - "
            "timing detail: "
            "q=%.2f ms n=%.2f ms c=%.2f ms p=%.2f ms s=%.2f ms t=%.2f ms r=%.2f ms"
        )
        expected_message = expected_message_fmt % (
            service,
            response.request_time * 1000,
            response.code,
            response.request.method,
            response.effective_url,
            response.time_info["queue"] * 1000,
            response.time_info["namelookup"] * 1000,
            response.time_info["connect"] * 1000,
            response.time_info["pretransfer"] * 1000,
            response.time_info["starttransfer"] * 1000,
            response.time_info["total"] * 1000,
            response.time_info["redirect"] * 1000)

        self.assertEqual(message, expected_message)

    def test_with_no_time_info(self):
        async_action = tor_async_util.AsyncAction()

        response = mock.Mock(
            code=httplib.OK,
            error=None,
            body=json.dumps({}),
            time_info={},
            request_time=0.042,
            effective_url="http://172.17.42.1:4001/v2/keys/key-value",
            request=mock.Mock(method="GET"))

        service = 'my service'

        message = async_action.create_log_msg_for_http_client_response(
            response,
            service)

        expected_message_fmt = (
            "%s took %.2f ms to respond with "
            "%d to %s against >>>%s<<< - "
            "timing detail: "
            "q=0.00 ms n=0.00 ms c=0.00 ms p=0.00 ms s=0.00 ms t=0.00 ms r=0.00 ms"
        )
        expected_message = expected_message_fmt % (
            service,
            response.request_time * 1000,
            response.code,
            response.request.method,
            response.effective_url)

        self.assertEqual(message, expected_message)


class AspectHealthTestCase(unittest.TestCase):

    def test_ctr(self):
        name = uuid.uuid4().hex
        is_ok = uuid.uuid4().hex

        aspect = tor_async_util.AspectHealth(name, is_ok)

        self.assertEqual(aspect.name, name)
        self.assertEqual(aspect.is_ok, is_ok)

    def test_health_color(self):
        aspect = tor_async_util.AspectHealth(uuid.uuid4().hex, True)
        self.assertEqual(aspect.health_color, 'green')

        aspect = tor_async_util.AspectHealth(uuid.uuid4().hex, False)
        self.assertEqual(aspect.health_color, 'red')


class ComponentHealthTestCase(unittest.TestCase):

    def test_ctr_aspects_not_none(self):
        name = uuid.uuid4().hex
        aspects = uuid.uuid4().hex
        is_ok = None

        component = tor_async_util.ComponentHealth(name, aspects=aspects, is_ok=is_ok)

        self.assertEqual(component.name, name)
        self.assertEqual(component.is_ok, is_ok)
        self.assertEqual(component.aspects, aspects)

    def test_ctr_is_ok_not_none(self):
        name = uuid.uuid4().hex
        aspects = None
        is_ok = uuid.uuid4().hex

        component = tor_async_util.ComponentHealth(name, aspects=aspects, is_ok=is_ok)

        self.assertEqual(component.name, name)
        self.assertEqual(component.is_ok, is_ok)
        self.assertEqual(component.aspects, aspects)

    def test_health_color_from_is_ok_true(self):
        component = tor_async_util.ComponentHealth(uuid.uuid4().hex, is_ok=True)
        self.assertEqual(component.health_color, 'green')

    def test_health_color_from_is_ok_false(self):
        component = tor_async_util.ComponentHealth(uuid.uuid4().hex, is_ok=False)
        self.assertEqual(component.health_color, 'red')

    def test_health_color_from_aspects_all_ok(self):
        aspects = [
            tor_async_util.AspectHealth(uuid.uuid4().hex, True),
            tor_async_util.AspectHealth(uuid.uuid4().hex, True),
            tor_async_util.AspectHealth(uuid.uuid4().hex, True),
        ]
        component = tor_async_util.ComponentHealth(uuid.uuid4().hex, aspects=aspects)
        self.assertEqual(component.health_color, 'green')

    def test_health_color_from_aspects_one_bad(self):
        aspects = [
            tor_async_util.AspectHealth(uuid.uuid4().hex, True),
            tor_async_util.AspectHealth(uuid.uuid4().hex, False),
            tor_async_util.AspectHealth(uuid.uuid4().hex, True),
        ]
        component = tor_async_util.ComponentHealth(uuid.uuid4().hex, aspects=aspects)
        self.assertEqual(component.health_color, 'red')


class HealthCheckRequestHandler(tor_async_util.RequestHandler):

    url_spec = r'/_health'

    @tornado.web.asynchronous
    def get(self):
        tor_async_util.generate_health_check_response(self, tor_async_util.AsyncHealthCheck)


class HealthCheckTestCase(RequestHandlerTestCase):
    """Unit tests for generate_health_check_response()."""

    def get_app(self):
        handlers = [
            (
                HealthCheckRequestHandler.url_spec,
                HealthCheckRequestHandler
            ),
        ]
        return tornado.web.Application(handlers=handlers)

    def test_happy_path_with_details_all_ok(self):
        def check_patch(ahc, callback):
            details = {
                tor_async_util.ComponentHealth('dave', is_ok=True),
                tor_async_util.ComponentHealth('here', is_ok=True),
                tor_async_util.ComponentHealth('and', is_ok=True),
            }
            callback(details, ahc)

        with mock.patch(__name__ + '.tor_async_util.AsyncHealthCheck.check', check_patch):
            response = self.fetch(HealthCheckRequestHandler.url_spec, method='GET')
            self.assertEqual(response.code, httplib.OK)
            self.assertNoDebugDetail(response)
            expected_response_body = {
                'status': 'green',
                'details': {
                    'dave': 'green',
                    'here': 'green',
                    'and': 'green',
                },
                'links': {
                    'self': {
                        'href': response.effective_url,
                    }
                }
            }
            self.assertEqual(json.loads(response.body), expected_response_body)

    def test_happy_path_with_multi_level_details_all_ok(self):
        def check_patch(ahc, callback):
            component2_aspects = [
                tor_async_util.AspectHealth('subcomponent1', True),
                tor_async_util.AspectHealth('subcomponent2', True),
                tor_async_util.AspectHealth('subcomponent3', True),
            ]
            details = {
                tor_async_util.ComponentHealth('component1', is_ok=True),
                tor_async_util.ComponentHealth('component2', aspects=component2_aspects),
                tor_async_util.ComponentHealth('component3', is_ok=True),
            }

            callback(details, ahc)

        with mock.patch(__name__ + '.tor_async_util.AsyncHealthCheck.check', check_patch):
            response = self.fetch(HealthCheckRequestHandler.url_spec, method='GET')
            self.assertEqual(response.code, httplib.OK)
            self.assertNoDebugDetail(response)
            expected_response_body = {
                'status': 'green',
                'details': {
                    'component1': 'green',
                    'component2': {
                        'status': 'green',
                        'details': {
                            'subcomponent1': 'green',
                            'subcomponent2': 'green',
                            'subcomponent3': 'green',
                        },
                    },
                    'component3': 'green',
                },
                'links': {
                    'self': {
                        'href': response.effective_url,
                    }
                }
            }
            self.assertEqual(json.loads(response.body), expected_response_body)

    def test_happy_path_with_details_one_component_in_error(self):
        def check_patch(ahc, callback):
            details = {
                tor_async_util.ComponentHealth('dave', is_ok=True),
                tor_async_util.ComponentHealth('here', is_ok=False),
                tor_async_util.ComponentHealth('and', is_ok=True),
            }

            callback(details, ahc)

        with mock.patch(__name__ + '.tor_async_util.AsyncHealthCheck.check', check_patch):
            response = self.fetch(HealthCheckRequestHandler.url_spec, method='GET')
            self.assertEqual(response.code, httplib.SERVICE_UNAVAILABLE)
            self.assertNoDebugDetail(response)
            expected_response_body = {
                'status': 'red',
                'details': {
                    'dave': 'green',
                    'here': 'red',
                    'and': 'green',
                },
                'links': {
                    'self': {
                        'href': response.effective_url,
                    }
                }
            }
            self.assertEqual(json.loads(response.body), expected_response_body)

    def test_happy_path_with_multi_level_details_with_error_leaf_components(self):
        def check_patch(ahc, callback):
            component2_aspects = [
                tor_async_util.AspectHealth('subcomponent1', True),
                tor_async_util.AspectHealth('subcomponent2', False),
                tor_async_util.AspectHealth('subcomponent3', True),
            ]
            details = {
                tor_async_util.ComponentHealth('component1', is_ok=True),
                tor_async_util.ComponentHealth('component2', aspects=component2_aspects),
                tor_async_util.ComponentHealth('component3', is_ok=True),
            }

            callback(details, ahc)

        with mock.patch(__name__ + '.tor_async_util.AsyncHealthCheck.check', check_patch):
            response = self.fetch(HealthCheckRequestHandler.url_spec, method='GET')
            self.assertEqual(response.code, httplib.SERVICE_UNAVAILABLE)
            self.assertNoDebugDetail(response)
            expected_response_body = {
                'status': 'red',
                'details': {
                    'component1': 'green',
                    'component2': {
                        'status': 'red',
                        'details': {
                            'subcomponent1': 'green',
                            'subcomponent2': 'red',
                            'subcomponent3': 'green',
                        },
                    },
                    'component3': 'green',
                },
                'links': {
                    'self': {
                        'href': response.effective_url,
                    }
                }
            }
            self.assertEqual(json.loads(response.body), expected_response_body)

    def test_happy_path_with_service_unavailable(self):
        def check_patch(ahc, callback):
            details = {
                tor_async_util.ComponentHealth('some component', is_ok=False),
            }
            callback(details, ahc)

        with mock.patch(__name__ + '.tor_async_util.AsyncHealthCheck.check', check_patch):
            response = self.fetch(HealthCheckRequestHandler.url_spec, method='GET')
            self.assertEqual(response.code, httplib.SERVICE_UNAVAILABLE)
            self.assertNoDebugDetail(response)

    def test_happy_path_no_is_quick(self):
        response = self.fetch(HealthCheckRequestHandler.url_spec, method='GET')
        self.assertEqual(response.code, httplib.OK)
        self.assertNoDebugDetail(response)

    def test_happy_path_is_quick_equals_true(self):
        response = self.fetch('%s?quick=true' % HealthCheckRequestHandler.url_spec, method='GET')
        self.assertEqual(response.code, httplib.OK)
        self.assertNoDebugDetail(response)

    def test_happy_path_is_quick_equals_false(self):
        response = self.fetch('%s?quick=false' % HealthCheckRequestHandler.url_spec, method='GET')
        self.assertEqual(response.code, httplib.OK)
        self.assertNoDebugDetail(response)

    def test_is_quick_equals_invalid_value(self):
        response = self.fetch('%s?quick=davewashere' % HealthCheckRequestHandler.url_spec, method='GET')
        self.assertEqual(response.code, httplib.BAD_REQUEST)
        self.assertDebugDetail(response, tor_async_util.HEALTH_CHECK_GDD_INVALID_QUICK_ARGUMENT)

    def test_bad_response_body(self):
        with WriteAndVerifyPatcher(is_ok=False):
            response = self.fetch(HealthCheckRequestHandler.url_spec, method='GET')
            self.assertEqual(response.code, httplib.INTERNAL_SERVER_ERROR)
            self.assertDebugDetail(response, tor_async_util.HEALTH_CHECK_GDD_INVALID_RESPONSE_BODY)


class ExponentialBackoffRetryStrategyTestCase(unittest.TestCase):
    """A collection of unit tests for the ExponentialBackoffRetryStrategy class."""

    def test_ctr(self):
        rs = tor_async_util.ExponentialBackoffRetryStrategy()
        self.assertEqual(0, rs.num_retries)
        self.assertTrue(0 < rs.max_num_retries)

        the_max_num_retries = 45
        rs = tor_async_util.ExponentialBackoffRetryStrategy(the_max_num_retries)
        self.assertEqual(0, rs.num_retries)
        self.assertEqual(the_max_num_retries, rs.max_num_retries)

    def test_next_attempt(self):
        the_max_num_retries = 45
        rs = tor_async_util.ExponentialBackoffRetryStrategy(the_max_num_retries)
        self.assertEqual(0, rs.num_retries)

        self.assertTrue(rs.next_attempt())
        self.assertEqual(1, rs.num_retries)
        self.assertTrue(0 < rs.max_num_retries)

    def test_wait(self):
        the_max_num_retries = 45
        rs = tor_async_util.ExponentialBackoffRetryStrategy(the_max_num_retries)
        while True:
            add_timeout_patch = mock.Mock()
            with mock.patch('tornado.ioloop.IOLoop.add_timeout', add_timeout_patch):
                wait_callback = mock.Mock()
                delay_in_ms = rs.wait(wait_callback)
                if delay_in_ms:
                    self.assertEqual(1, add_timeout_patch.call_count)
                    self.assertEqual(0, wait_callback.call_count)
                    self.assertTrue(0 < delay_in_ms)
                else:
                    self.assertEqual(0, add_timeout_patch.call_count)
                    self.assertEqual(1, wait_callback.call_count)
                    self.assertEqual(the_max_num_retries, rs.num_retries)
                    return

        self.assertTure(False)
