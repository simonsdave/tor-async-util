"""This module contains a framework for unit testing request handlers."""

import httplib
import json
import re
import uuid
import unittest

import jsonschema
import mock
import tornado.testing

from .. import request_handler


class Patcher(object):

    def __init__(self, patcher):
        object.__init__(self)
        self._patcher = patcher

    def __enter__(self):
        self._patcher.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._patcher.stop()


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
                "request_handler.RequestHandler.write_and_verify"
            ),
            write_and_verify_patch)

        Patcher.__init__(self, patcher)


class RequestHandlerTestCase(tornado.testing.AsyncHTTPTestCase):
    """Abstract base class for all handler unit test cases."""

    _json_utf8_content_type_reg_ex = re.compile(
        "^\s*application/json;\s+charset\=utf-{0,1}8\s*$",
        re.IGNORECASE)

    @classmethod
    def setUpClass(cls):
        cls._debug_details_patcher = mock.patch(
            "request_handler.include_debug_details",
            mock.Mock(return_value=True))
        cls._debug_details_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls._debug_details_patcher.stop()

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
            request_handler.debug_details_header_name,
            None)
        self.assertIsNotNone(value)
        self.assertTrue(value.startswith("0x"))
        self.assertEqual(int(value, 16), expected_value)

    def assertNoDebugDetail(self, response):
        """Assert *no* debug failure detail HTTP header appears
        in ```response```."""
        value = response.headers.get(
            request_handler.debug_details_header_name,
            None)
        self.assertIsNone(value)

    def assertJsonContentTypeInResponse(self, response):
        content_type = response.headers.get("Content-Type", None)
        self.assertIsNotNone(content_type)
        self.assertTrue(self._json_utf8_content_type_reg_ex.match(content_type))


class TestGetBasicAuthCredsRequestHandler(request_handler.RequestHandler):

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
    tornado_util.RequestHandler.get_basic_auth_creds"""

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
            request_handler.RequestHandler.GBAC_OK)

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
            request_handler.RequestHandler.GBAC_NO_AUTHORIZATION_HEADER)

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
            request_handler.RequestHandler.GBAC_INVALID_AUTHORIZATION_HEADER_VALUE)

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
            request_handler.RequestHandler.GBAC_BAD_B64_ENCODING)

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
            request_handler.RequestHandler.GBAC_INVALID_USERNAME_PASSWORD)


class TestGetJsonRequestBodyRequestHandler(request_handler.RequestHandler):
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
    tornado_util.RequestHandler.get_json_request_body()"""

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
            "content-type": "application/json; charset=utf-8",
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
        headers["content-type"] = "bindle"
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
    unit testing for ```tornado_util.RequestHandler```. This
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
            the_request_handler = request_handler.RequestHandler()
            body = the_request_handler.get_json_request_body(self.schema)
            self.assertIsNotNone(body)
            self.assertEqual(body, the_body)

        # remove the content length which should cause specific failure
        del the_request.headers["Content-Length"]

        with TornadoRequestHandlerCtrPatcher(the_request):
            the_request_handler = request_handler.RequestHandler()
            body = the_request_handler.get_json_request_body(self.schema)
            self.assertIsNone(body)

        # makes things work by adding an alternative content type
        the_request.headers["Transfer-Encoding"] = "anything"

        with TornadoRequestHandlerCtrPatcher(the_request):
            the_request_handler = request_handler.RequestHandler()
            body = the_request_handler.get_json_request_body(self.schema)
            self.assertIsNotNone(body)
            self.assertEqual(body, the_body)

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
            the_request_handler = request_handler.RequestHandler()
            body = the_request_handler.get_json_request_body(self.schema)
            self.assertIsNotNone(body)
            self.assertEqual(body, the_body)

        # set body to None which should cause specific failure
        the_request.body = None

        with TornadoRequestHandlerCtrPatcher(the_request):
            the_request_handler = request_handler.RequestHandler()
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
            the_request_handler = request_handler.RequestHandler()
            body = the_request_handler.get_json_request_body(self.schema)
            self.assertIsNotNone(body)
            self.assertEqual(body, the_body)

        # remove the content type which should cause specific failure
        del the_request.headers["Content-Type"]

        with TornadoRequestHandlerCtrPatcher(the_request):
            the_request_handler = request_handler.RequestHandler()
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
            the_request_handler = request_handler.RequestHandler()
            body = the_request_handler.get_json_request_body(self.schema)
            self.assertIsNotNone(body)
            self.assertEqual(body, the_body)


class TestWriteAndVerifyRequestHandler(request_handler.RequestHandler):
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
    tornado_util.RequestHandler.write_and_verify."""

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


class TestSetStatusRequestHandler(request_handler.RequestHandler):
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
            request_handler.RequestHandler(
                self.get_app(), mock.Mock()).set_status(1)


class WriteErrorRequestHandler(request_handler.RequestHandler):
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
