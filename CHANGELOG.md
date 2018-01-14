# Change Log
All notable changes to this project will be documented in this file.
Format of this file follows [these](http://keepachangelog.com/) guidelines.
This project adheres to [Semantic Versioning](http://semver.org/).

## [%RELEASE_VERSION%] - [%RELEASE_DATE%]

### Added

- Nothing

### Changed

- Nothing

### Removed

- Nothing

## [1.13.1] - [2018-01-13]

### Added

- tornado 4.0.0 is a min pre-req
- AsyncAction ctr now sets property id to a unique identifier for each
AsyncAction instance - this will be useful for logging and debugging
create_log_msg_for_http_client_response
- AsyncAction.create_log_msg_for_http_client_response()
replaces write_http_client_response_to_log()
- added ExponentialBackoffRetryStrategy() utility class

### Changed

- pep8 -> pycodestyle
- async state

### Removed

- write_http_client_response_to_log() removed and replaced
with AsyncAction.create_log_msg_for_http_client_response()

## [1.13.0] - [2016-01-29]
### Changed
- python-keyczar 0.715 -> 0.716

## [1.12.0] - [2016-02-23]
### Added
- added tor_async_util.generate_version_response()

## [1.11.0] - [2016-02-03]
### Changed
- simplified tor_async_util.AsyncHealthCheck's callback signature
  and responsibilities

## [1.10.0] - [2016-01-24]
### Added
- added tor_async_util.write_http_client_response_to_log()
- added tor_async_util_nosetests.py and tor_async_util.FileCapture
- added tor_async_util.AsyncAction

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
