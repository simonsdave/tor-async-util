# tor-async-util
![Maintained](https://img.shields.io/maintenance/no/2018.svg?style=flat)
![license](https://img.shields.io/pypi/l/tor-async-util.svg?style=flat)
![PythonVersions](https://img.shields.io/pypi/pyversions/tor-async-util.svg?style=flat)
![status](https://img.shields.io/pypi/status/tor-async-util.svg?style=flat)
[![PyPI](https://img.shields.io/pypi/v/tor-async-util.svg?style=flat)](https://pypi.python.org/pypi/tor-async-util)

```
Repo Status = as of EO '18 this repo is no longer being maintained.
```

tor-async-util is a set of utilities that are useful
when implementing RESTful APIs using [Tornado's](http://www.tornadoweb.org/en/stable/)
[Asynchronous and non-Blocking I/O](http://tornado.readthedocs.org/en/latest/guide/async.html).

## Features

* when async curl httpclient is used, it's useful to know if libcurl
  was compiled with an async dns resolver - see ```is_libcurl_compiled_with_async_dns_resolver()```

* instead of CTRL+C generating an unfriendly stack trace install
  a signal handler - see ```install_sigint_handler()```

* a default request handler which generates a RESTful API friendly
  not found response - see ```DefaultRequestHandler()```

* an abstract base class from which all request handler classes can be
  derived to provide

  - read and write json requests and responses optionally verifying
    each against a jsonschema - see ```RequestHandler.get_json_request_body()```
    and ```RequestHandler.write_and_verify()```

  - accessing decoded BASIC auth credentials - see ```RequestHandler.get_basic_auth_creds()```

  - augment Tornado's default ```set_status()``` with support for additional
    status codes - see ```RequestHandler.set_status()```

  - override Tornado's default ```write_error()``` so a json response body is
    generated rather than the default HTML response body - see ```RequestHandler.write_error()```


- thin wrapper around ```ConfigParser.ConfigParser``` to parse ini files
  for things settings such as logging levels, keyczar crypters and keyczar
  signers - see ```Config```

- core implementations of ```/_version```, ```/_noop``` and ```/_health``` endpoints
  include async health checkers - see ```generate_version_response()```, ```generate_noop_response()```,
  ```generate_health_check_response()``` and ```AsyncHealthCheck```

- [this](http://tornado.readthedocs.org/en/latest/httpclient.html#response-objects)
  explains that the time_info attribute of a tornado response
  object contains timing details of the phases of a request which
  is available when using the cURL http client. a description
  of these timing details can be found at
  [here](http://curl.haxx.se/libcurl/c/curl_easy_getinfo.html#TIMES).
  these timings are very, very helpful in understanding latencies from
  interactions between microservices - see ```write_http_client_response_to_log()```.
  an example of what the logs look like is below

```
2016-01-23T03:45:53.362+00:00 INFO async_docker_remote_api 'Remote Docker API' took 3.42 ms to
respond with 200 to 'GET' against >>>http://127.0.0.1:4243/containers/cid/logs?stdout=1<<< - timing
detail: q=0.13 ms n=0.03 ms c=0.04 ms p=1.65 ms s=1.66 ms t=1.83 ms r=0.00 ms
```
