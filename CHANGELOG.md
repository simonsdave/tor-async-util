# Change Log
All notable changes to this project will be documented in this file.
Format of this file follows [these](http://keepachangelog.com/) guidelines.
This project adheres to [Semantic Versioning](http://semver.org/).

## [1.9.0] - [2016-01-20]
### Added
- added AsyncHealthCheck

## [1.8.0] - [2016-01-19]
### Added
- added generate_noop_response() for generating noop responses
- added generate_health_check_response() for generating health check responses
- added RequestHandler.write_bad_request_response()

## [1.7.0] - [2016-01-06]
### Changed
- **WARNING** - breaking change = rename get_crypter() to get_keyczar_crypter()
- **WARNING** - breaking change = rename get_signer() to get_keyczar_signer()
- added tor_async_util.Config.get_all_values()

## [1.6.0] - [2016-01-05]
### Changed
- relax constraints on supported versions of jsonschema, tornado and requests

## [1.5.0] - [2015-11-08]
### Removed
- support for Transfer-Encoding http header removed
- removed PTS-IDS-CID http header

### Changed
- write_and_verify() no longer "pretty prints" json response

## [1.4.0] - [2015-10-19]
### Added
- added Config utility

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
