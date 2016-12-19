"""This module loads all of the jsonschemas for validating
request and response bodies.
"""

import json
import os


def _load_jsonschema(schema_name):
    filename = os.path.join(
        os.path.dirname(__file__), 'jsonschemas', '%s.json' % schema_name)
    with open(filename) as fp:
        return json.load(fp)


get_noop_response = _load_jsonschema('get_noop_response')

get_health_response = _load_jsonschema('get_health_response')

get_version_response = _load_jsonschema('get_version_response')
