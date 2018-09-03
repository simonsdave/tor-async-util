import base64
import ConfigParser
import datetime
import httplib
import json
import logging
import os
import re
import random
import signal
import sys
import uuid

from tornado.ioloop import IOLoop
import jsonschema
from keyczar import keyczar
import pycurl
import tornado.web

import jsonschemas

__version__ = '1.15.0'


_logger = logging.getLogger('tor_async_util')


"""If a debug details header is included in a response,
```debug_details_header_name``` is the name of the HTTP
header.
"""
debug_details_header_name = 'X-Debug-Detail'


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


class RequestHandler(tornado.web.RequestHandler):
    """An abstract base class for request handlers."""

    _json_utf8_content_type_reg_ex = re.compile(
        r"^\s*application/json(;\s+charset\=utf-{0,1}8){0,1}\s*$",
        re.IGNORECASE)

    def add_debug_details(self, value):
        """Include debug details in a response. Specifically, include
        an HTTP header in the response with the corresponding value
        of ```value```.
        """
        if _logger.isEnabledFor(logging.DEBUG):
            self.set_header(
                debug_details_header_name,
                "0x{:04x}".format(value))

    def set_default_headers(self):
        """The less a potential threat knows about infrastructre
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
        ```None``  otherwise return the dict.
        """
        content_length = self.request.headers.get("Content-Length", None)
        if content_length is None:
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
        a jsonschema.
        """
        try:
            jsonschema.validate(json_body, schema)
        except Exception as ex:
            msg = "Error validating json body before calling 'write()' - %s"
            _logger.error(msg, ex)
            return False

        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(json_body))

        return True

    def write_bad_request_response(self, debug_details=None):
        """```write_bad_request_response()``` implements a common response
        pattern when responding to some form of bad input:

            1/ write empty json doc in response body
            2/ set content type to json
            3/ set status to bad request
            4/ possibily set the debug details header
        """
        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        self.write({})
        self.set_status(httplib.BAD_REQUEST)
        if debug_details is not None:
            self.add_debug_details(debug_details)

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
        kind of error is detected a pair of None's is returned.
        """
        auth_hdr_val = self.request.headers.get("Authorization", None)
        if auth_hdr_val is None:
            return (None, None, self.GBAC_NO_AUTHORIZATION_HEADER)

        pattern = r"^\s*BASIC\s+(?P<auth_hdr_val>[^\s]+)\s*$"
        reg_ex = re.compile(pattern, re.IGNORECASE)
        match = reg_ex.match(auth_hdr_val)
        if not match:
            return (None, None, self.GBAC_INVALID_AUTHORIZATION_HEADER_VALUE)

        auth_hdr_val = match.group("auth_hdr_val")

        try:
            auth_hdr_val = base64.b64decode(auth_hdr_val)
        except Exception:
            return (None, None, self.GBAC_BAD_B64_ENCODING)

        pattern = r"^\s*(?P<username>[^:]+):(?P<password>[^\s]+)\s*$"
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
        r"^\-{0,1}\d+$",
        re.IGNORECASE)

    """Used to determine if a string represents a "true" boolean value."""
    _true_reg_ex = re.compile(
        r"^(true|t|y|yes|1)$",
        re.IGNORECASE)

    """Used to determine if a string represents a "false" boolean value."""
    _false_reg_ex = re.compile(
        r"^(false|f|n|no|0)$",
        re.IGNORECASE)

    """Used to turn a logging level string into a logging level."""
    _logging_level_reg_ex = re.compile(
        r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL|FATAL)$",
        re.IGNORECASE)

    def __init__(self, config_file):
        """Create an instance of ```Config``` by reading the
        contents of the ini file ```config_file```.
        ```os.path.expanduser``` is used to transform ```config_file```
        and deal with things like leading ~ **before** the contents
        of the ini file are read.
        """
        object.__init__(self)

        self.config_file = os.path.expanduser(config_file)

        self._config = ConfigParser.ConfigParser()
        self._config.read(self.config_file)

    def get_all_values(self, section, values_if_not_found=None):
        return self._config.items(section) if self._config.has_section(section) else values_if_not_found

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

    def get_keyczar_crypter(self, section, option, value_if_not_found=None):
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

    def get_keyczar_signer(self, section, option, value_if_not_found=None):
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


"""```GVR_INVALID_RESPONSE_BODY``` is used in ```generate_version_response()```
to indicate that an invalid response body has been generated. This should
never happen!
"""
GVR_INVALID_RESPONSE_BODY = 0x0001


def generate_version_response(request_handler, version):
    """This function encapsulates all the functionality required
    to generate a response to a version request.

        import tor_async_util

        class ServiceVersionRequestHandler(tor_async_util.RequestHandler):

            url_spec = r'/v1.0/service/_version'

            @tornado.web.asynchronous
            def get(self):
                tor_async_util.generate_version_response(self, '1.0.56')
    """
    location = '%s://%s%s' % (
        request_handler.request.protocol,
        request_handler.request.host,
        request_handler.request.path,
    )

    body = {
        'version': version,
        'links': {
            'self': {
                'href': location,
            },
        },
    }

    if not request_handler.write_and_verify(body, jsonschemas.get_version_response):
        request_handler.add_debug_details(GVR_INVALID_RESPONSE_BODY)
        request_handler.set_status(httplib.INTERNAL_SERVER_ERROR)
        request_handler.finish()
        return

    request_handler.set_header('Location', location)

    request_handler.set_status(httplib.OK)
    request_handler.finish()


"""```GNR_INVALID_RESPONSE_BODY``` is used in ```generate_noop_response()```
to indicate that an invalid response body has been generated. This should
never happen!
"""
GNR_INVALID_RESPONSE_BODY = 0x0001


def generate_noop_response(request_handler):
    """This function encapsulates all the functionality required
    to generate a response to a no-op request.

        import tor_async_util

        class ServiceNoOpRequestHandler(tor_async_util.RequestHandler):

            url_spec = r'/v1.0/service/_noop'

            @tornado.web.asynchronous
            def get(self):
                tor_async_util.generate_noop_response(self)
    """
    location = '%s://%s%s' % (
        request_handler.request.protocol,
        request_handler.request.host,
        request_handler.request.path,
    )

    body = {
        'links': {
            'self': {
                'href': location,
            },
        },
    }

    if not request_handler.write_and_verify(body, jsonschemas.get_noop_response):
        request_handler.add_debug_details(GNR_INVALID_RESPONSE_BODY)
        request_handler.set_status(httplib.INTERNAL_SERVER_ERROR)
        request_handler.finish()
        return

    request_handler.set_header('Location', location)

    request_handler.set_status(httplib.OK)
    request_handler.finish()


def _health_check_color(is_ok):
    """Used by ```generate_health_check_response()``` to turn
    a boolean into a color.
    """
    return 'green' if is_ok else 'red'


def _health_check_is_quick(request_handler):
    """Used by ```generate_health_check_response()``` to extract
    and parse the 'quick' argument from a request's query string.
    """
    arg_value = request_handler.get_argument('quick', 'y')

    if re.match(r'^(true|t|y|yes|1)$', arg_value, re.IGNORECASE):
        return True

    if re.match(r'^(false|f|n|no|0)$', arg_value, re.IGNORECASE):
        return False

    return None


"""Used by ```generate_health_check_response()``` to indicate
in a debug details HTTP header that processing the request failed
because the ```is_quick``` query string argument was invalid.
"""
HEALTH_CHECK_GDD_INVALID_QUICK_ARGUMENT = 0x0001


"""Used by ```generate_health_check_response()``` to indicate
in a debug details HTTP header that processing the request failed
because the generated response body was invalid which should really
never happen.
"""
HEALTH_CHECK_GDD_INVALID_RESPONSE_BODY = 0x0002


def generate_health_check_response(request_handler, async_health_check_class):
    """Every service should have a health check endpoint. For a more
    complete exploration of what the health check endpoint should do
    see the microservice architectural guidance.
    ```generate_health_check_response()``` is intended to make it
    super easy to implement a health check endpoint.

    Expected usage

        import tor_async_util
        from async_actions import AsyncHealthCheck

        .
        .
        .

        class UsersHealthRequestHandler(HealthRequestHandler):

            url_spec = r'/v1.0/something/_health'

            @tornado.web.asynchronous
            def get(self):
                tor_async_util.generate_health_check_response(self, AsyncHealthCheck)

    A minimal AsyncHealthCheck implementation

        class AsyncHealthCheck(tor_async_util.AsyncAction):

            def __init__(self, is_quick, async_state=None):
                tor_async_util.AsyncAction.__init__(self, async_state)

                self.is_quick = is_quick

            def check(self, callback):
                if self.is_quick:
                    details = None
                else:
                    aspects = [
                        tor_async_util.AspectHealth('configured', True),
                        tor_async_util.AspectHealth('working', False),
                    ]
                    details = {
                        tor_async_util.ComponentHealth('component 1', is_ok=True),
                        tor_async_util.ComponentHealth('component 2', aspects=aspects),
                    }

                callback(details, self)
    """
    is_quick = _health_check_is_quick(request_handler)
    if is_quick is None:
        request_handler.write_bad_request_response(HEALTH_CHECK_GDD_INVALID_QUICK_ARGUMENT)
        request_handler.finish()
        return

    ahc = async_health_check_class(is_quick, async_state=request_handler)
    ahc.check(_health_check_on_ahc_check_done)


def _health_check_on_ahc_check_done(details, ahc):
    """```_health_check_on_ahc_check_done()``` is an async callback used
    by ```generate_health_check_response()``` to finish processing of an
    async health check request.
    """
    request_handler = ahc.async_state

    location = '%s://%s%s' % (
        request_handler.request.protocol,
        request_handler.request.host,
        request_handler.request.path,
    )

    body = {
        'links': {
            'self': {
                'href': location,
            },
        },
    }
    body.update(_health_check_gen_response_body(details))

    if not request_handler.write_and_verify(body, jsonschemas.get_health_response):
        request_handler.add_debug_details(HEALTH_CHECK_GDD_INVALID_RESPONSE_BODY)
        request_handler.set_status(httplib.INTERNAL_SERVER_ERROR)
        request_handler.finish()
        return

    request_handler.set_header('location', location)

    status = httplib.OK if body['status'] == _health_check_color(True) else httplib.SERVICE_UNAVAILABLE
    request_handler.set_status(status)

    request_handler.finish()


class AspectHealth(object):
    """See ```ComponentHealth``` and ```generate_health_check_response()```
    for details.
    """

    def __init__(self, name, is_ok):
        object.__init__(self)

        self.name = name
        self.is_ok = is_ok

    @property
    def health_color(self):
        return _health_check_color(self.is_ok)


class ComponentHealth(object):
    """Health of a service is determined by the health of each component
    within a service. An instance of ```ComponentHealth``` represents the
    health of a service's component. A component's health can either be
    determined by a simple boolean (True = healthy, False=unhealthy) or
    the aggregation of a number of aspects of the component. A component
    aspect is represented by an instance of ```AspectHealth``` which has
    a simple boolean representation of health. If any aspect of a component
    is unhealthy the component is unhealthy. For more details see the docs
    for ```generate_health_check_response()```.
    """

    def __init__(self, name, aspects=None, is_ok=None):
        object.__init__(self)

        assert aspects is None or is_ok is None

        self.name = name
        self.aspects = aspects
        self.is_ok = is_ok

    @property
    def health_color(self):
        if self.is_ok is not None:
            return _health_check_color(self.is_ok)

        for aspect in self.aspects:
            if not aspect.is_ok:
                return _health_check_color(False)

        return _health_check_color(True)


def _health_check_gen_response_body(details):
    """A private function only used by ```_health_check_on_ahc_check_done()```
    to recursively generate. The "status" portion of the health endpoint's
    response. ```details``` is expected to be produced by an AsyncHealthCheck
    implementation.
    """
    rv = {
        'status': _health_check_color(True),
    }
    if not details:
        return rv

    rv['details'] = {}

    for component in details:
        if component.health_color == _health_check_color(False):
            rv['status'] = _health_check_color(False)

        if not component.aspects:
            rv['details'][component.name] = component.health_color
            continue

        rv['details'][component.name] = {
            'status': component.health_color,
            'details': {
            }
        }

        for aspect in component.aspects:
            rv['details'][component.name]['details'][aspect.name] = aspect.health_color

    return rv


class AsyncAction(object):
    """Abstract base class for any async actions."""

    def __init__(self, async_state=None):
        object.__init__(self)

        self.id = uuid.uuid4().hex

        self.async_state = async_state

    def create_log_msg_for_http_client_response(self, response, service):
        """Create a message that the caller can write to a logger
        containing timing details of the response to an async
        ```tornado.httpclient.HTTPRequest```. The message should be
        be easy to parse by performance analysis tools and used to understand
        performance bottlenecks.

        http://tornado.readthedocs.org/en/latest/httpclient.html#response-objects
        explains that the time_info attribute of a tornado response
        object contains timing details of the phases of a request which
        is available when using the cURL http client. a description
        of these timing details can be found at
        http://curl.haxx.se/libcurl/c/curl_easy_getinfo.html#TIMES
        and it is these detailed timings which are written to ```logger```
        """
        fmt = (
            '{service} took {request_time:.2f} ms to respond '
            'with {http_response_code:d} to {http_method} '
            'against >>>{url}<<< - timing detail: '
            'q={queue:.2f} ms n={namelookup:.2f} ms '
            'c={connect:.2f} ms p={pretransfer:.2f} ms '
            's={starttransfer:.2f} ms t={total:.2f} ms r={redirect:.2f} ms'
        )
        msg_format_args = {
            'service': service,
            'request_time': response.request_time * 1000,
            'http_response_code': response.code,
            'http_method': response.request.method,
            'url': response.effective_url,
        }

        def add_time_info_to_msg_format_args(key):
            msg_format_args[key] = response.time_info.get(key, 0) * 1000

        add_time_info_to_msg_format_args('queue')
        add_time_info_to_msg_format_args('namelookup')
        add_time_info_to_msg_format_args('connect')
        add_time_info_to_msg_format_args('pretransfer')
        add_time_info_to_msg_format_args('starttransfer')
        add_time_info_to_msg_format_args('total')
        add_time_info_to_msg_format_args('redirect')

        return fmt.format(**msg_format_args)


class AsyncHealthCheck(AsyncAction):
    """When a service uses ```generate_health_check_response()``` to implement
    a health check endpoint, it's entirely possible that an async class will
    not be required however ```generate_health_check_response()``` still
    requires an async class. Hence the creation of this super simple class.
    """

    def __init__(self, is_quick, async_state=None):
        AsyncAction.__init__(self, async_state)

        self.is_quick = is_quick

    def check(self, callback):
        callback(None, self)


class ExponentialBackoffRetryStrategy(object):
    """```ExponentialBackoffRetryStrategy``` implements a retry strategy
    that, as the name suggests, waits exponentially longer time as the
    number of retry attempts increases. The specific time waited is calculated
    with the formula:

        (2 ** retry_number) * 25 +/- random # between -10 & 10

    To get a general sense of wait times:

        for retry in range(1, 20): print (2**retry) * 100

    References

        * https://developers.google.com/google-apps/documents-list/?csw=1#implementing_exponential_backoff
        * http://googleappsdeveloper.blogspot.ca/2011/12/documents-list-api-best-practices.html
        * http://docs.aws.amazon.com/general/latest/gr/api-retries.html
    """

    def __init__(self, max_num_retries=20):
        object.__init__(self)

        self.num_retries = 0
        self.max_num_retries = max_num_retries

    def next_attempt(self):
        self.num_retries += 1
        return self.num_retries < self.max_num_retries

    def wait(self, callback, *callback_args, **callback_kwargs):

        if not self.next_attempt():
            callback(0, *callback_args, **callback_kwargs)
            return

        delay_in_ms = (2 ** self.num_retries) * 25 + random.randint(-10, 10)

        IOLoop.current().add_timeout(
            datetime.timedelta(0, delay_in_ms / 1000.0, 0),
            callback,
            delay_in_ms,
            *callback_args,
            **callback_kwargs)

        return delay_in_ms
