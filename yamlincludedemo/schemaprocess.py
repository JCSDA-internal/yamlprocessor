#!/usr/bin/env python3
"""Modularise a JSON schema

Modularise a JSON schema and allows it to accept a data structure that can be
composed of include files.
"""

from argparse import ArgumentParser
import json
import os

import jmespath


JSON_DUMP_CONFIG = {'indent': 2}


def main(argv=None):
    parser = ArgumentParser(description=__file__)
    parser.add_argument(
        'schema_filename',
        metavar='SCHEMA-FILE',
        help='Name of the JSON schema file to modularise')
    parser.add_argument(
        'config_filename',
        metavar='CONFIG-FILE',
        help='Name of the configuration file')
    args = parser.parse_args(argv)

    # Get subschemas, detect any duplicates
    schema = json.load(open(args.schema_filename))
    subschemas = {}  # {filerelname: subschema, ...}
    schema_filebasename = '0-{}'.format(os.path.basename(args.schema_filename))
    for filerelname, pathstr in json.load(open(args.config_filename)).items():
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
                {
                    "properties": {
                        "!include": {"type": "string", "format": "uri"},
                    },
                    "required": ["INCLUDE"],
                    "type": "object",
                },
            ],
        })

    # Dump subschemas from copies, because original has been modified in place.
    for filerelname, subschema in subschema_copies.items():
        with open(filerelname, 'w') as subschema_file:
            json.dump(subschema, subschema_file, **JSON_DUMP_CONFIG)
    with open(schema_filebasename, 'w') as schema_file:
        json.dump(schema, schema_file, **JSON_DUMP_CONFIG)


if __name__ == '__main__':
    main(sys.argv)
