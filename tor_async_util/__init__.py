import logging

try:
    import pycurl
except ImportError:
    pass


__version__ = "1.0.0"


_logger = logging.getLogger("tor_async_util.%s" % __name__)


def is_libcurl_compiled_with_async_dns_resolver():
    """If you've configured Tornado to use the async curl_httpclient,
    per this (http://tornado.readthedocs.org/en/latest/httpclient.html)
    warning, you'll want to make sure that libcurl has been compiled
    with async DNS resolver. This function wraps up all the gory details
    for answering this question and returns True if libcurl has been
    compiled with async DNS resolver otherwise returns False.
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
        _logger.debug(fmt, ex)
        return False
