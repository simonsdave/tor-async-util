import logging

try:
    import pycurl
except ImportError:
    pass


__version__ = "1.0.1"


_logger = logging.getLogger("tor_async_util.%s" % __name__)


def is_libcurl_compiled_with_async_dns_resolver():
    """Per this (http://tornado.readthedocs.org/en/latest/httpclient.html),
    if you've configured Tornado to use async curl_httpclient, you'll want
    to make sure that libcurl has been compiled with async DNS resolver.
    The programmatic approach to checking for libcurl being compiled
    with async DNS resolve is a mess of gory details. It was this mess
    that drove the need for function. Specifically, this function implements
    all the gory details so the caller doesn't have to worry about them!
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
