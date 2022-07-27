#!/usr/bin/env python3
"""Modularise a JSON schema

Modularise a JSON schema and allows it to accept a data structure that can be
composed of include files.

Two positional arguments are expected:

 1. The file name of the JSON schema file.
 2. The file name of a configuration file in JSON format.

The configuration file expects a mapping, where the keys are the file names
(relative paths to current working directory) of the output sub-schema files,
and the values are sub-schema break point locations (expressed as
`JMESPath <https://jmespath.org/>`_ format) in the input JSON schema document.
"""

from argparse import ArgumentParser
import json
import os
import sys

import jmespath

from .dataprocess import DataProcessor


JSON_DUMP_CONFIG = {'indent': 2}
INCLUDE_SCHEMA = DataProcessor.INCLUDE_SCHEMA
INCLUDE_SCHEMA_FILENAME = 'yp-include.schema.json'


def schema_process(schema_filename: str, config_filename: str) -> None:
    """Process schema to handle includes according to configuration.

    :param schema_filename: schema file name.
    :param config_filename: configuration file name.
    """
    # Get subschemas, detect any duplicates
    schema = json.load(open(schema_filename))
    subschemas = {}  # {filerelname: subschema, ...}
    schema_filebasename = '0-{}'.format(os.path.basename(schema_filename))
    config = json.load(open(config_filename))
    # Special entry for include schema filename
    include_schema_filename = config.pop(
        '$ref:yp-include.schema.json', INCLUDE_SCHEMA_FILENAME)
    for pathstr, filerelname in config.items():
        pathstr = pathstr.strip()
        if not pathstr:
            schema_filebasename = filerelname
            continue
        subschema = jmespath.search(pathstr, schema)
        for o_filebasename, o_subschema in subschemas.items():
            if subschema is o_subschema:
                raise ValueError(
                    '{}: {} and {}: {} point to the same location.'.format(
                        filerelname, pathstr, o_filebasename, o_subschema,
                    )
                )
        subschemas[filerelname] = subschema

    # Take a shallow copy of the subschemas before modifying.
    # Dump later in case there are sub-subschemas.
    subschema_copies = (
        {f: subschema.copy() for f, subschema in subschemas.items()}
    )
    for filerelname, subschema in subschemas.items():
        subschema.clear()
        subschema.update({
            'oneOf': [
                {'$ref': filerelname},
                {'$ref': include_schema_filename},
            ],
        })

    # Dump subschemas from copies, because original has been modified in place.
    for filerelname, subschema in subschema_copies.items():
        with open(filerelname, 'w') as subschema_file:
            json.dump(subschema, subschema_file, **JSON_DUMP_CONFIG)
    with open(include_schema_filename, 'w') as include_schema_file:
        json.dump(INCLUDE_SCHEMA, include_schema_file, **JSON_DUMP_CONFIG)
    with open(schema_filebasename, 'w') as schema_file:
        json.dump(schema, schema_file, **JSON_DUMP_CONFIG)


def main(argv=None):
    parser = ArgumentParser(description=__doc__)
    parser.add_argument(
        'schema_filename',
        metavar='SCHEMA-FILE',
        help='Name of the JSON schema file to modularise')
    parser.add_argument(
        'config_filename',
        metavar='CONFIG-FILE',
        help='Name of the configuration file')
    args = parser.parse_args(argv)
    schema_process(args.schema_filename, args.config_filename)


if __name__ == '__main__':
    main(sys.argv)
