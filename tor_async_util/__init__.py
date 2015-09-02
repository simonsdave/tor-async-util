import logging
import signal
import sys

try:
    import pycurl
except ImportError:
    pass


__version__ = "1.1.0"


_logger = logging.getLogger("tor_async_util.%s" % __name__)


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
