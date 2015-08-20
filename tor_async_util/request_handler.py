"""This module contains a set of utilities for implementing Tornado
request handlers.
"""

import base64
import httplib
import json
import logging
import re
import uuid

import jsonschema
import tornado.web


_logger = logging.getLogger("tor_async_util.%s" % __name__)

"""If a debug details header is included in a response,
```debug_details_header_name``` is the name of the HTTP
header.
"""
debug_details_header_name = "X-Debug-Detail"


def include_debug_details():
    """If ```include_debug_details()``` returns True, RequestHandler
    will include a debug details HTTP header whenever an error
    is encountered.
    """
    return _logger.isEnabledFor(logging.DEBUG)


class RequestHandler(tornado.web.RequestHandler):
    """An abstract base class for request handlers."""

    _json_utf8_content_type_reg_ex = re.compile(
        "^\s*application/json;\s+charset\=utf-{0,1}8\s*$",
        re.IGNORECASE)

    def initialize(self):
        self.correlation_id = uuid.uuid4().hex

    def add_debug_details(self, value):
        """Include debug details in a response. Specifically, include
        an HTTP header in the response with the corresponding value
        of ```value```.
        """
        if include_debug_details():
            self.set_header(
                debug_details_header_name,
                "0x{:04x}".format(value))

    def set_default_headers(self):
        """The less a potential threat knows about security infrastructre
        the better. With that in mind, this method attempts to remove the
        Server HTTP header if it appears in a response.
        """
        self.clear_header("Server")

    def compute_etag(self):
        """Disable auto etag generation."""
        return None

    def get_json_request_body(self, schema):
        """Get the request's JSON body and convert it into a dict
        and validate it against ```schema```.
        If there's no body, the body isn't JSON, etc then return
        ```None``  otherwise return the dict."""
        content_length = self.request.headers.get("Content-Length", None)
        if content_length is None:
            transfer_encoding = self.request.headers.get("Transfer-Encoding", None)
            if transfer_encoding is None:
                return None

        if self.request.body is None:
            return None

        content_type = self.request.headers.get("Content-Type", None)
        if content_type is None:
            return None

        if not self._json_utf8_content_type_reg_ex.match(content_type):
            return None

        try:
            json_body = json.loads(self.request.body)
            jsonschema.validate(json_body, schema)
        except Exception as ex:
            msg_fmt = "Error parsing/validating JSON request body - %s"
            _logger.debug(msg_fmt, ex)
            return None

        return json_body

    def write_and_verify(self, json_body, schema):
        """Request handlers would typically do a self.write()
        with the response body and can still do so. This method
        is a replacement for self.write(). This method calls
        self.write() after validating the response body against
        a jsonschema."""
        try:
            jsonschema.validate(json_body, schema)
        except Exception as ex:
            msg = "Error validating json body before calling 'write()' - %s"
            _logger.error(msg, ex)
            return False

        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.set_header("PTS-IDS-CID", self.correlation_id)
        self.write(json.dumps(json_body, indent=2))

        return True

    # GBAC = Get Basic Auth Creds
    GBAC_OK = 0x0000
    GBAC_NO_AUTHORIZATION_HEADER = 0x0001
    GBAC_INVALID_AUTHORIZATION_HEADER_VALUE = 0x0002
    GBAC_BAD_B64_ENCODING = 0x0003
    GBAC_INVALID_USERNAME_PASSWORD = 0x0004

    def get_basic_auth_creds(self):
        """Assuming BASIC auth is being used, returns the username
        and password (as a pair) after extracting and decoding
        them from the request's Authorization header. If any
        kind of error is detected a pair of None's is returned."""

        auth_hdr_val = self.request.headers.get("Authorization", None)
        if auth_hdr_val is None:
            return (None, None, self.GBAC_NO_AUTHORIZATION_HEADER)

        pattern = "^\s*BASIC\s+(?P<auth_hdr_val>[^\s]+)\s*$"
        reg_ex = re.compile(pattern, re.IGNORECASE)
        match = reg_ex.match(auth_hdr_val)
        if not match:
            return (None, None, self.GBAC_INVALID_AUTHORIZATION_HEADER_VALUE)

        auth_hdr_val = match.group("auth_hdr_val")

        try:
            auth_hdr_val = base64.b64decode(auth_hdr_val)
        except:
            return (None, None, self.GBAC_BAD_B64_ENCODING)

        pattern = "^\s*(?P<username>[^:]+):(?P<password>[^\s]+)\s*$"
        reg_ex = re.compile(pattern, re.IGNORECASE)
        match = reg_ex.match(auth_hdr_val)
        if not match:
            return (None, None, self.GBAC_INVALID_USERNAME_PASSWORD)

        return (match.group("username"), match.group("password"), self.GBAC_OK)

    def set_status(self, status_code, reason=None):
        # Python 2.7.3 doesn't support webdav status codes such as 422.
        # See http://bugs.python.org/issue15025
        responses = dict(httplib.responses)
        responses.update({
            102: 'Processing',
            207: 'Multi-Status',
            226: 'IM Used',
            422: 'Unprocessable Entity',
            423: 'Locked',
            424: 'Failed Dependency',
            426: 'Upgrade Required',
            507: 'Insufficient Storage',
            510: 'Not Extended',
        })
        if not reason:
            try:
                reason = responses[status_code]
            except KeyError:
                raise ValueError("unknown status code %d", status_code)
        return super(RequestHandler, self).set_status(status_code, reason)

    def prepare(self):
        """Overwritten to log requests."""
        request = ["%s %s" % (self.request.method, self.request.full_url())]
        for key, value in self.request.headers.items():
            request.append("%s: %s" % (key, value))
        request.append(self.request.body)
        request = "\n".join(request)
        _logger.debug("Received Request:\n%s", request)

    def flush(self, include_footers=False, callback=None):
        """Overwritten to log responses."""
        headers = "\n" + "\n".join(
            ["%s: %s" % (key, value) for key, value in self._headers.items()])
        body = "".join(self._write_buffer)
        _logger.debug("Sending Response:%s%s", headers, body)
        return super(RequestHandler, self).flush(include_footers, callback)
