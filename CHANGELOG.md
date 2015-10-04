# Change Log
All notable changes to this project will be documented in this file.
Format of this file follows [these](http://keepachangelog.com/) guidelines.
This project adheres to [Semantic Versioning](http://semver.org/).

## [1.3.0] - [2015-10-04]
### Changed
- RequestHandler.get_json_request_body() now accepts
both application/json;charset=utf-8
and application/json
as valid content types

## [1.2.0] - [2015-09-06]
### Added
- added RequestHandler.write_error() to respond with JSON
instead of HTML

### Changed
- **WARNING** - breaking change = tor_async_util.request_handler now
in tor_async_util

## [1.1.0] - [2015-09-03]
### Added
- added install_sigint_handler()
- added DefaultRequestHandler

## [1.0.0] - [2015-08-20]
### Added
- added is_libcurl_compiled_with_async_dns_resolver() - see
[this](http://tornado.readthedocs.org/en/latest/httpclient.html)
for why this is useful

### Changed
- log statements are now prefixed with tor_async_util

## [0.9.0] - [2015-07-10]
- initial release
