# yaml-include-demo

Demonstrate how to modularise YAML files using a controlled include file
mechanism, backed by dividing the original JSON schema file into a set of
subschema files.

Consider a YAML file `hello.yaml`:

```yaml
hello:
  - location: earth
    targets:
      - human
      - cat
      - dog
  - location: mars
    targets:
      - martian
# And so on
```

And its associated JSON schema file:

```json
{
    "properties": {
        "hello": {
            "items": {
                "properties": {
                    "location": {
                        "type": "string"
                    },
                    "targets": {
                        "items": {
                            "type": "string"
                        },
                        "minItems": 1,
                        "type": "array",
                        "uniqueItems": true
                    }
                },
                "required": ["location", "targets"],
                "type": "object"
            },
            "type": "array"
        }
    },
    "required": ["hello"],
    "type": "object"
}
```

We want to modularise the YAML file in this way.
Let's call this `hello-root.yaml`:

```yaml
hello:
  - yaml::earth.yaml
  - yaml::mars.yaml
```

Where `earth.yaml` contains:

```yaml
location: earth
targets:
  - human
  - cat
  - dog
```

And `mars.yaml` contains:

```yaml
location: mars
targets:
  - martian
```

At runtime, we can run the `demo-app-conf-process INFILE OUTFILE`
command to process and recombine the YAML files.

To split the schema to support these YAML files, however, we'll
use the `demo-schema-process SCHEMA-FILE CONFIG-FILE` command.
For this command to work, we need to supply it with some settings
to tell it where to split up the schema in the syntax:

```json
{
    "OUTPUT-ROOT-SCHEMA-FILENAME": "",
    "OUTPUT-SUB-SCHEMA-FILENAME-1": "JMESPATH-1",
    /* and so on */
}
```

Obviously, we must have a root schema output file name.
The rest of the entries are output file names for the subschemas.
The [https://jmespath.org/](JMESPath) syntax tells the
`demo-schema-process` command where to split JSON schema into
subschemas. In the example above, we can give use the setting:

```json
{
    "hello.schema.json": "",
    "hello-location.schema.json": "properties.hello.items"
}
```

The resulting `hello.schema.json` will look like this,
which can be used to validate both `hello.yaml` and `hello-root.yaml`:

```json
{
    "properties": {
        "hello": {
            "items": {
                "oneOf": [
                    {"$ref": "hello-location.schema.json"},
                    {
                        "pattern": "^yaml::",
                        "type": "string"
                    }
                ]
            },
            "type": "array"
        }
    },
    "required": ["hello"],
    "type": "object"
}
```

The resulting `hello-location.schema.json` will look like this
which can be used to validate `earth.yaml` and `mars.yaml`:

```json
{
    "properties": {
        "location": {
            "type": "string"
        },
        "targets": {
            "items": {
                "type": "string"
            },
            "minItems": 1,
            "type": "array",
            "uniqueItems": true
        }
    },
    "required": ["location", "targets"],
    "type": "object"
}
```
