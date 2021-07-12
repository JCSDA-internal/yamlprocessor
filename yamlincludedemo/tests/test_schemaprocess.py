import json

from ..schemaprocess import main


def test_main_0(monkeypatch, tmp_path):
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
                        'oneOf': [
                            {'$ref': 'schema-1.json'},
                            {
                                'properties': {
                                    '!include': {
                                        'type': 'string',
                                        'format': 'uri',
                                    },
                                },
                                'required': ['INCLUDE'],
                                'type': 'object',
                            },
                        ],
                    },
                    'type': 'array',
                },
            },
            'required': ['testing'],
            'type': 'object',
        }
    with (tmp_path / 'schema-1.json').open() as schema_1_file:
        assert json.load(schema_1_file) == {'type': 'integer'}
