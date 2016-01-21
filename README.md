# tor-async-util
[![MIT license](http://img.shields.io/badge/license-MIT-brightgreen.svg)](http://opensource.org/licenses/MIT) ![Python 2.7](https://img.shields.io/badge/python-2.7-FFC100.svg?style=flat) [![Requirements Status](https://requires.io/github/simonsdave/tor-async-util/requirements.svg?branch=master)](https://requires.io/github/simonsdave/tor-async-util/requirements/?branch=master) [![Build Status](https://travis-ci.org/simonsdave/tor-async-util.svg?branch=master)](https://travis-ci.org/simonsdave/tor-async-util) [![Coverage Status](https://coveralls.io/repos/simonsdave/tor-async-util/badge.svg?branch=master&service=github)](https://coveralls.io/github/simonsdave/tor-async-util?branch=master) [![Code Health](https://landscape.io/github/simonsdave/tor-async-util/master/landscape.svg?style=flat)](https://landscape.io/github/simonsdave/tor-async-util/master)

tor-async-util is a set of utilities that are useful
when implementing RESTful APIs using [Tornado's](http://www.tornadoweb.org/en/stable/)
[Asynchronous and non-Blocking I/O](http://tornado.readthedocs.org/en/latest/guide/async.html).

Capability highlights:

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

- core implementations of ```/_noop``` and ```/_health``` endpoints
  include async health checkers - see ```generate_noop_response()```,
  ```generate_health_check_response()``` and ```AsyncHealthCheck```
