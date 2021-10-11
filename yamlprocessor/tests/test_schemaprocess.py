import json

from ..schemaprocess import INCLUDE_SCHEMA, main


def test_main_1(monkeypatch, tmp_path):
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
        'schema-0.json': '',
        'schema-1.json': 'properties.testing.items',
    }
    config_filename = tmp_path / 'config.json'
    with config_filename.open('w') as config_file:
        json.dump(config, config_file)
    monkeypatch.chdir(tmp_path)
    main([str(schema_filename), str(config_filename)])
    with (tmp_path / 'schema-0.json').open() as schema_0_file:
        assert json.load(schema_0_file) == {
            'additionalProperties': False,
            'properties': {
                'testing': {
                    'items': {
                        'oneOf': [{'$ref': 'schema-1.json'}, INCLUDE_SCHEMA],
                    },
                    'type': 'array',
                },
            },
            'required': ['testing'],
            'type': 'object',
        }
    with (tmp_path / 'schema-1.json').open() as schema_1_file:
        assert json.load(schema_1_file) == {'type': 'integer'}


def test_main_3(monkeypatch, tmp_path):
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
        'schema-0.json': '',
        'schema-1.json': 'properties.testing.items',
        'schema-2.json': 'properties.examining.items',
        'schema-3.json': 'properties.examining.items.properties.name',
    }
    config_filename = tmp_path / 'config.json'
    with config_filename.open('w') as config_file:
        json.dump(config, config_file)
    monkeypatch.chdir(tmp_path)
    main([str(schema_filename), str(config_filename)])
    with (tmp_path / 'schema-0.json').open() as schema_0_file:
        assert json.load(schema_0_file) == {
            'additionalProperties': False,
            'properties': {
                'testing': {
                    'items': {
                        'oneOf': [{'$ref': 'schema-1.json'}, INCLUDE_SCHEMA],
                    },
                    'type': 'array',
                },
                'examining': {
                    'items': {
                        'oneOf': [{'$ref': 'schema-2.json'}, INCLUDE_SCHEMA],
                    },
                    'type': 'array',
                },
            },
            'required': ['testing', 'examining'],
            'type': 'object',
        }
    with (tmp_path / 'schema-1.json').open() as schema_1_file:
        assert json.load(schema_1_file) == {'type': 'integer'}
    with (tmp_path / 'schema-2.json').open() as schema_2_file:
        assert json.load(schema_2_file) == {
            'properties': {
                'batch': {
                    'type': 'integer',
                },
                'name': {
                    'oneOf': [{'$ref': 'schema-3.json'}, INCLUDE_SCHEMA],
                },
            },
            'type': 'object',
            'required': ['batch', 'name'],
        }
    with (tmp_path / 'schema-3.json').open() as schema_3_file:
        assert json.load(schema_3_file) == {'type': 'string'}
