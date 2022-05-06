import json

import jsonschema

from ..schemaprocess import INCLUDE_SCHEMA, INCLUDE_SCHEMA_FILENAME, main


SAMPLE_TESTING = [-1, 0, 1]
SAMPLE_MAIN_ONE = {'testing': SAMPLE_TESTING}
SAMPLE_MAIN_ONE_INC = {'testing': {'INCLUDE': 'test-data.yaml'}}
SAMPLE_EXAMINING_NAME_ONE = 'one'
SAMPLE_EXAMINING = [
    {'name': {'INCLUDE': 'batch-xxx-name.txt'}, 'batch': 1234},
    {'name': 'two', 'batch': 5678},
]
SAMPLE_MAIN_THREE = {'testing': SAMPLE_TESTING, 'examining': SAMPLE_EXAMINING}
SAMPLE_MAIN_THREE_INC = {
    'testing': SAMPLE_TESTING,
    'examining': {'INCLUDE': 'exam-data.yaml'},
}


def test_main_one(monkeypatch, tmp_path):
    """Test with one include entry."""
    schema = {
        'additionalProperties': False,
        'properties': {
            'testing': {
                'items': {
                    'type': 'integer',
                },
                'type': 'array',
            },
        },
        'required': ['testing'],
        'type': 'object',
    }
    schema_filename = tmp_path / 'schema.json'
    with schema_filename.open('w') as schema_file:
        json.dump(schema, schema_file)
    config = {
        '': 'schema-root.json',
        'properties.testing': 'schema-a.json',
    }
    config_filename = tmp_path / 'config.json'
    with config_filename.open('w') as config_file:
        json.dump(config, config_file)
    monkeypatch.chdir(tmp_path)
    main([str(schema_filename), str(config_filename)])
    with (tmp_path / 'schema-root.json').open() as schema_root_file:
        assert json.load(schema_root_file) == {
            'additionalProperties': False,
            'properties': {
                'testing': {
                    'oneOf': [
                        {'$ref': 'schema-a.json'},
                        {'$ref': INCLUDE_SCHEMA_FILENAME},
                    ],
                },
            },
            'required': ['testing'],
            'type': 'object',
        }
    with (tmp_path / 'schema-a.json').open() as schema_a_file:
        assert json.load(schema_a_file) == {
            'items': {'type': 'integer'},
            'type': 'array',
        }
    with (tmp_path / INCLUDE_SCHEMA_FILENAME).open() as include_schema_file:
        assert json.load(include_schema_file) == INCLUDE_SCHEMA

    # See if schemas can validate data or not
    for schema_filename, sample_data in (
        ('schema-root.json', SAMPLE_MAIN_ONE),
        ('schema-root.json', SAMPLE_MAIN_ONE_INC),
        ('schema-a.json', SAMPLE_TESTING),
    ):
        try:
            jsonschema.validate(
                schema={
                    '$ref': (tmp_path / schema_filename).absolute().as_uri()
                },
                instance=sample_data,
            )
        except jsonschema.exceptions.ValidationError as exc:
            assert False, f"{schema_filename} does not validate data:\n{exc}"
        else:
            assert True, f"{schema_filename} works OK with data"


def test_main_three(monkeypatch, tmp_path):
    """Test with three include entries, nested."""
    schema = {
        'additionalProperties': False,
        'properties': {
            'testing': {
                'items': {
                    'type': 'integer',
                },
                'type': 'array',
            },
            'examining': {
                'items': {
                    'properties': {
                        'batch': {
                            'type': 'integer',
                        },
                        'name': {
                            'type': 'string',
                        },
                    },
                    'type': 'object',
                    'required': ['batch', 'name'],
                },
                'type': 'array',
            },
        },
        'required': ['testing', 'examining'],
        'type': 'object',
    }
    schema_filename = tmp_path / 'schema.json'
    with schema_filename.open('w') as schema_file:
        json.dump(schema, schema_file)
    config = {
        '': 'schema-root.json',
        'properties.testing': 'schema-a.json',
        'properties.examining': 'schema-b.json',
        'properties.examining.items.properties.name': 'schema-c.json',
    }
    config_filename = tmp_path / 'config.json'
    with config_filename.open('w') as config_file:
        json.dump(config, config_file)
    monkeypatch.chdir(tmp_path)
    main([str(schema_filename), str(config_filename)])
    with (tmp_path / 'schema-root.json').open() as schema_root_file:
        assert json.load(schema_root_file) == {
            'additionalProperties': False,
            'properties': {
                'testing': {
                    'oneOf': [
                        {'$ref': 'schema-a.json'},
                        {'$ref': INCLUDE_SCHEMA_FILENAME},
                    ],
                },
                'examining': {
                    'oneOf': [
                        {'$ref': 'schema-b.json'},
                        {'$ref': INCLUDE_SCHEMA_FILENAME},
                    ],
                },
            },
            'required': ['testing', 'examining'],
            'type': 'object',
        }
    with (tmp_path / 'schema-a.json').open() as schema_a_file:
        assert json.load(schema_a_file) == {
            'items': {'type': 'integer'},
            'type': 'array',
        }
    with (tmp_path / 'schema-b.json').open() as schema_b_file:
        assert json.load(schema_b_file) == {
            'items': {
                'properties': {
                    'batch': {
                        'type': 'integer',
                    },
                    'name': {
                        'oneOf': [
                            {'$ref': 'schema-c.json'},
                            {'$ref': INCLUDE_SCHEMA_FILENAME},
                        ],
                    },
                },
                'type': 'object',
                'required': ['batch', 'name'],
            },
            'type': 'array',
        }
    with (tmp_path / 'schema-c.json').open() as schema_c_file:
        assert json.load(schema_c_file) == {'type': 'string'}
    with (tmp_path / INCLUDE_SCHEMA_FILENAME).open() as include_schema_file:
        assert json.load(include_schema_file) == INCLUDE_SCHEMA

    # See if schemas can validate data or not
    for schema_filename, sample_data in (
        ('schema-root.json', SAMPLE_MAIN_THREE),
        ('schema-root.json', SAMPLE_MAIN_THREE_INC),
        ('schema-a.json', SAMPLE_TESTING),
        ('schema-b.json', SAMPLE_EXAMINING),
        ('schema-c.json', SAMPLE_EXAMINING_NAME_ONE),
    ):
        try:
            jsonschema.validate(
                schema={
                    '$ref': (tmp_path / schema_filename).absolute().as_uri()
                },
                instance=sample_data,
            )
        except jsonschema.exceptions.ValidationError as exc:
            assert False, f"{schema_filename} does not validate data:\n{exc}"
        else:
            assert True, f"{schema_filename} works OK with data"
