import base64
import ConfigParser
import httplib
import json
import logging
import os
import re
import signal
import sys
import uuid

import jsonschema
try:
    import pycurl
except ImportError:
    pass
from keyczar import keyczar
import tornado.web


__version__ = "1.4.0"

_logger = logging.getLogger("tor_async_util.%s" % __name__)

"""If a debug details header is included in a response,
```debug_details_header_name``` is the name of the HTTP
header.
"""
debug_details_header_name = "X-Debug-Detail"


def is_libcurl_compiled_with_async_dns_resolver():
    """Per this (http://tornado.readthedocs.org/en/latest/httpclient.html),
    if you've configured Tornado to use async curl_httpclient, you'll want
    to make sure that libcurl has been compiled with async DNS resolver.
    The programmatic approach to checking for libcurl being compiled
    with async DNS resolve is a mess of gory details. It was this mess
    that drove the need for this function. Specifically, this function implements
    all the gory details so the caller doesn't have to worry about them!

    This function is intended to be used in an application's mainline
    in the following manner:

        #!/usr/bin/env python

        import logging

        from tor_async_util import is_libcurl_compiled_with_async_dns_resolver

        _logger = logging.getLogger(__name__)

        if __name__ == "__main__":

            if not is_libcurl_compiled_with_async_dns_resolver():
                msg = (
                    "libcurl does not appear to have been "
                    "compiled with aysnc dns resolve which "
                    "may result in timeouts on async requests"
                )
                _logger.warning(msg)

    If you really want to understand the details start with the following
    article:

        http://stackoverflow.com/questions/25998063/how-can-i-tell-if-the-libcurl-installed-has-asynchronous-dns-enabled

    Other references that you'll find useful on your question for understanding:

        http://curl.haxx.se/libcurl/
        https://github.com/bagder/curl/blob/master/include/curl/curl.h#L2286

    If you don't care about the implementation details just know that
    this function returns True if libcurl has been compiled with async DNS
    resolver otherwise this functions returns False.
    """
    try:
        version_info = pycurl.version_info()
        features = version_info[4]
        # to understand CURL_VERSION_ASYNCHDNS see
        # https://github.com/bagder/curl/blob/master/include/curl/curl.h#L2286
        CURL_VERSION_ASYNCHDNS = 1 << 7
        return (features & CURL_VERSION_ASYNCHDNS) == CURL_VERSION_ASYNCHDNS
    except Exception as ex:
        fmt = (
            "Error trying to figure out if libcurl is complied with "
            "async DNS resolver - %s"
        )
        msg = fmt % ex
        _logger.debug(msg)
        return False


def _sigint_handler(signal_number, frame):
    assert signal_number == signal.SIGINT
    _logger.info("Shutting down ...")
    sys.exit(0)


def install_sigint_handler():
    """This is a fit and finish type function. install_sigint_handler()
    installs a handler that catches SIGINT signals and generates a
    "nice" log message rather than the default handling of generating
    and ugly/verbose stack trace.

    This function is intended to be used in an application's mainline
    in the following manner:

        #!/usr/bin/env python

        from tor_async_util import install_sigint_handler

        if __name__ == "__main__":
            install_sigint_handler()
    """
    signal.signal(signal.SIGINT, _sigint_handler)


class DefaultRequestHandler(tornado.web.RequestHandler):
    """This is the request handler that gets called when no other
    request handler's url spec is matched for HEAD, GET, POST,
    DELETE, PATCH, PUT & OPTIONS HTTP methods. This handler always
    responds with a 404 (not found) status code, empty JSON
    document and a JSON Content-Type for all methods except HEAD
    when only a 404 is returned.

    DefaultRequestHandler is expected to be used in the following
    manner:

        #!/usr/bin/env python

        import tornado.web
        from tor_async_util import DefaultRequestHandler

        .
        .
        .

        if __name__ == "__main__":

            settings = {
                "default_handler_class": DefaultRequestHandler,
            }

            handlers = [
                ...
            ]

            app = tornado.web.Application(handlers=handlers, **settings)

            .
            .
            .

    :TODO: what about 'none standard' HTTP methods? is there a way
    to consider leveraging use of RequestHandler.SUPPORTED_METHODS?
    """

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
        if self.request.method == "HEAD":
            self.set_status(httplib.NOT_FOUND)
            return

        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write({})
        self.set_status(httplib.NOT_FOUND)


def include_debug_details():
    """If ```include_debug_details()``` returns True, RequestHandler
    will include a debug details HTTP header whenever an error
    is encountered.
    """
    return _logger.isEnabledFor(logging.DEBUG)


class RequestHandler(tornado.web.RequestHandler):
    """An abstract base class for request handlers."""

    _json_utf8_content_type_reg_ex = re.compile(
        "^\s*application/json(;\s+charset\=utf-{0,1}8){0,1}\s*$",
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

    def write_error(self, status_code, **kwargs):
        """Override write_error() to generate a json rather than html
        response on error.
        """
        if self.request.method != "HEAD":
            self.set_header("Content-Type", "application/json; charset=UTF-8")
            self.write({})
        self.set_status(status_code)


class Config(object):
    """```Config``` is a thin wrapper around
    ```ConfigParser.ConfigParser```.
    """

    """```instance``` is intended to enable implementation
    of the Singleton pattern for an instance of ```Config```.
    The following illustrates how ```instance``` was intended
    to be used:

        .
        .
        .

        if __name__ == "__main__":
            clp = CommandLineParser()
            (clo, cla) = clp.parse_args()

            Config.instance = Config(clo.config)
            config_section = "some_section"

            .
            .
            .
    """
    instance = None

    """Used to determine if a string represents an integer value."""
    _int_reg_ex = re.compile(
        "^\-{0,1}\d+$",
        re.IGNORECASE)

    """Used to determine if a string represents a "true" boolean value."""
    _true_reg_ex = re.compile(
        "^(true|t|y|yes|1)$",
        re.IGNORECASE)

    """Used to determine if a string represents a "false" boolean value."""
    _false_reg_ex = re.compile(
        "^(false|f|n|no|0)$",
        re.IGNORECASE)

    """Used to turn a logging level string into a logging level."""
    _logging_level_reg_ex = re.compile(
        "^(DEBUG|INFO|WARNING|ERROR|CRITICAL|FATAL)$",
        re.IGNORECASE)

    def __init__(self, config_file):
        """Create an instance of ```Config``` by reading the
        contents of the ini file ```config_file```.
        ```os.path.expanduser``` is used to transform ```config_file```
        and deal with things like leading ~ **before** the contents
        of the ini file are read.
        """
        object.__init__(self)

        expanded_config_file = os.path.expanduser(config_file)

        self._config = ConfigParser.ConfigParser()
        self._config.read(expanded_config_file)

    def get(self, section, option, value_if_not_found=None):
        value = self._config.get(section, option) if self._config.has_option(section, option) else value_if_not_found
        return os.path.expanduser(value) if value else value

    def get_int(self, section, option, value_if_not_found=0):
        value = self.get(section, option, None)
        if value is None:
            return value_if_not_found
        if not type(self)._int_reg_ex.match(value):
            return value_if_not_found
        return int(value)

    def get_boolean(self, section, option, value_if_not_found=False):
        value = self.get(section, option, None)
        if value is None:
            return value_if_not_found
        if type(self)._true_reg_ex.match(value):
            return True
        if type(self)._false_reg_ex.match(value):
            return False
        return value_if_not_found

    def get_logging_level(self, section, option, value_if_not_found=logging.INFO):
        logging_level_as_str = self.get(section, option, None)
        if logging_level_as_str is None:
            return value_if_not_found

        if not type(self)._logging_level_reg_ex.match(logging_level_as_str):
            return value_if_not_found

        return getattr(logging, logging_level_as_str.upper())

    def get_crypter(self, section, option, value_if_not_found=None):
        """Creates and returns the keyczar crypter who's key store is in the
        directory pointed to by section & option. If something doesn't
        get found or an error occurs during crypter creation, then
        ```value_if_not_found``` is returned.
        """
        dir_name = self.get(section, option, None)
        if not dir_name:
            return value_if_not_found
        try:
            return keyczar.Crypter.Read(dir_name)
        except Exception:
            return value_if_not_found

    def get_signer(self, section, option, value_if_not_found=None):
        """Creates and returns the keyczar signer who's key store is in the
        directory pointed to by section & option. If something doesn't
        get found or an error occurs during signer creation, then
        ```value_if_not_found``` is returned.
        """
        dir_name = self.get(section, option, None)
        if not dir_name:
            return value_if_not_found
        try:
            return keyczar.Signer.Read(dir_name)
        except Exception:
            return value_if_not_found
